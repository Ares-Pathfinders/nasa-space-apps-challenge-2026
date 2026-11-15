/**
 * "3D relief" view of the tactical viewer (tactical.html), Google Earth style.
 *
 * Uses public/models/gale_crater.stl as terrain and drapes the Gale MMGIS
 * imagery over it: colour comes from the 6 m CTX mosaic with the 2D map tint and,
 * over the Curiosity corridor, CTX/HiRISE detail is applied as luminance only so
 * there are no abrupt colour changes. Routes and waypoints from the map are drawn
 * on top.
 *
 * The STL has no coordinates. Its position was obtained by fitting it to the
 * 200 m MOLA/HRSC blended DEM (correlation 0.9998): it is a 513×513 height grid,
 * north towards +Y, covering the STL_BOUNDS box. Its Z follows
 * z = ELEV_SCALE · elevation(m) + ELEV_OFFSET (≈2.9× built-in vertical exaggeration).
 */
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

// ---- Globals from the classic tactical.html script (Leaflet) ---------------
type LatLng = { lat: number; lng: number };
type LeafletLayer = {
  getLatLngs?: () => LatLng[] | LatLng[][];
  getLatLng?: () => LatLng;
  options?: { color?: string; fillColor?: string; weight?: number; opacity?: number };
  eachLayer?: (fn: (layer: LeafletLayer) => void) => void;
};
type LeafletBounds = {
  getCenter: () => LatLng;
  getNorth: () => number;
  getSouth: () => number;
};
type LeafletMap = {
  getBounds: () => LeafletBounds;
  getCenter: () => LatLng;
  getZoom: () => number;
  getSize: () => { x: number; y: number };
  setView: (center: [number, number], zoom: number, options?: object) => void;
  hasLayer: (layer: LeafletLayer) => boolean;
  invalidateSize: () => void;
};
declare const map: LeafletMap;
declare const layers: Record<'route' | 'customRoute' | 'returnRoute' | 'wps', LeafletLayer>;

// ---- STL georeferencing -----------------------------------------------------
const MODEL_URL = `${import.meta.env.BASE_URL}models/gale_crater.stl`;
const STL_BOUNDS = { west: 135.97957, east: 139.49492, south: -7.84402, north: -3.21708 };
// Only the part of the STL with map imagery is drawn (MSL CTX mosaic ends at ~-3.40° N).
// Same bounds as the tactical grid (GALE_MIN/MAX_* in backend/data/gale_crater_topography.py).
const IMAGERY_BOUNDS = { west: 135.99, east: 139.476, south: -7.834, north: -3.41 };
const ELEV_SCALE = 0.00147483; // STL units per metre
const ELEV_OFFSET = 8.426;
const GRID = 513;

const MARS_RADIUS_KM = 3396.19;
const KM_PER_DEG = (MARS_RADIUS_KM * Math.PI) / 180;
const CENTER_LAT = (STL_BOUNDS.north + STL_BOUNDS.south) / 2;
const CENTER_LON = (STL_BOUNDS.west + STL_BOUNDS.east) / 2;
const COS_LAT = Math.cos((CENTER_LAT * Math.PI) / 180);

// High-resolution area (Curiosity corridor / tactical grid).
const DETAIL_BOUNDS = { west: 137.25, east: 137.61, south: -4.84, north: -4.47 };
const OVERVIEW_ZOOM = 10; // ≈80 m/px over the whole STL
const DETAIL_ZOOM = 13; // ≈10 m/px over the corridor

const GALE_LAYERS = {
  ctx: 'https://mars.nasa.gov/mmgis-maps/MSL/Layers/MSL_CTX_ortho_mosaic_6m/{z}/{x}/{y}.png',
  hirise: 'https://mars.nasa.gov/mmgis-maps/MSL/Layers/MSL_Gale_HiRISE-LRGB_78quads/{z}/{x}/{y}.png',
};

function lonLatToScene(lon: number, lat: number): [number, number] {
  return [(lon - CENTER_LON) * KM_PER_DEG * COS_LAT, -(lat - CENTER_LAT) * KM_PER_DEG];
}

function sceneToLonLat(x: number, z: number): [number, number] {
  return [CENTER_LON + x / (KM_PER_DEG * COS_LAT), CENTER_LAT - z / KM_PER_DEG];
}

// ---- DOM ------------------------------------------------------------------
function $(id: string): HTMLElement {
  const el = document.getElementById(id);
  if (!el) throw new Error(`[terrain3d] Missing element #${id}`);
  return el;
}

const toggleButton = $('terrain3dToggle') as HTMLButtonElement;
const container = $('terrain3d');
const status = $('terrain3dStatus');
const exaggeration = $('terrain3dExaggeration') as HTMLInputElement;
const exaggerationValue = $('terrain3dExaggerationValue');
const zoneSelect = $('zone') as HTMLSelectElement;
const basemapSelect = $('basemap') as HTMLSelectElement;
const mapElement = $('map');

// ---- State ----------------------------------------------------------------
let renderer: THREE.WebGLRenderer | null = null;
let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let controls: OrbitControls;
let terrain: THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial> | null = null;
let heights: Float32Array | null = null; // elevation in km, row 0 = north
let overlayGroup = new THREE.Group();
let overlaySignature = '';
let active = false;
let animationId = 0;
let loadPromise: Promise<void> | null = null;

const detailUniforms = {
  detailMap: { value: null as THREE.Texture | null },
  detailRect: { value: new THREE.Vector4(0, 0, 1, 1) },
  detailReady: { value: 0 },
};

function setStatus(text: string) {
  status.textContent = text;
  status.hidden = !text;
}

// ---- Terrain from the STL --------------------------------------------------
async function loadHeights(): Promise<Float32Array> {
  setStatus('Downloading Gale Crater terrain model…');
  const geometry = await new STLLoader().loadAsync(MODEL_URL, (event) => {
    if (event.lengthComputable) {
      setStatus(`Downloading Gale Crater terrain model… ${Math.round((event.loaded / event.total) * 100)}%`);
    }
  });
  const pos = geometry.getAttribute('position');
  let xMin = Infinity, xMax = -Infinity, yMin = Infinity, yMax = -Infinity;
  for (let i = 0; i < pos.count; i += 1) {
    if (pos.getZ(i) <= 0) continue; // base of the solid
    const x = pos.getX(i), y = pos.getY(i);
    if (x < xMin) xMin = x;
    if (x > xMax) xMax = x;
    if (y < yMin) yMin = y;
    if (y > yMax) yMax = y;
  }
  const grid = new Float32Array(GRID * GRID).fill(NaN);
  for (let i = 0; i < pos.count; i += 1) {
    const z = pos.getZ(i);
    if (z <= 0) continue;
    const col = Math.round(((pos.getX(i) - xMin) / (xMax - xMin)) * (GRID - 1));
    const rowFromSouth = Math.round(((pos.getY(i) - yMin) / (yMax - yMin)) * (GRID - 1));
    grid[(GRID - 1 - rowFromSouth) * GRID + col] = (z - ELEV_OFFSET) / ELEV_SCALE / 1000;
  }
  geometry.dispose();
  return grid;
}

/** Elevation (km) at a coordinate, bilinearly interpolated. */
function elevationAt(lon: number, lat: number): number {
  if (!heights) return 0;
  const fx = Math.min(GRID - 1, Math.max(0, ((lon - STL_BOUNDS.west) / (STL_BOUNDS.east - STL_BOUNDS.west)) * (GRID - 1)));
  const fy = Math.min(GRID - 1, Math.max(0, ((STL_BOUNDS.north - lat) / (STL_BOUNDS.north - STL_BOUNDS.south)) * (GRID - 1)));
  const x0 = Math.floor(fx), y0 = Math.floor(fy);
  const x1 = Math.min(GRID - 1, x0 + 1), y1 = Math.min(GRID - 1, y0 + 1);
  const tx = fx - x0, ty = fy - y0;
  const h = (x: number, y: number) => heights![y * GRID + x];
  return (h(x0, y0) * (1 - tx) + h(x1, y0) * tx) * (1 - ty) + (h(x0, y1) * (1 - tx) + h(x1, y1) * tx) * ty;
}

function buildTerrainGeometry(grid: Float32Array): THREE.BufferGeometry {
  // Sub-grid of STL samples inside IMAGERY_BOUNDS; UVs stay relative to the full STL
  // so the overview texture (which covers STL_BOUNDS) stays aligned.
  const toCol = (lon: number) => ((lon - STL_BOUNDS.west) / (STL_BOUNDS.east - STL_BOUNDS.west)) * (GRID - 1);
  const toRow = (lat: number) => ((STL_BOUNDS.north - lat) / (STL_BOUNDS.north - STL_BOUNDS.south)) * (GRID - 1);
  const colStart = Math.max(0, Math.ceil(toCol(IMAGERY_BOUNDS.west)));
  const colEnd = Math.min(GRID - 1, Math.floor(toCol(IMAGERY_BOUNDS.east)));
  const rowStart = Math.max(0, Math.ceil(toRow(IMAGERY_BOUNDS.north)));
  const rowEnd = Math.min(GRID - 1, Math.floor(toRow(IMAGERY_BOUNDS.south)));
  const cols = colEnd - colStart + 1;
  const rows = rowEnd - rowStart + 1;

  const [x0, z0] = lonLatToScene(STL_BOUNDS.west, STL_BOUNDS.north);
  const [x1, z1] = lonLatToScene(STL_BOUNDS.east, STL_BOUNDS.south);
  const positions = new Float32Array(rows * cols * 3);
  const uvs = new Float32Array(rows * cols * 2);
  for (let r = 0; r < rows; r += 1) {
    for (let c = 0; c < cols; c += 1) {
      const i = r * cols + c;
      const row = rowStart + r, col = colStart + c;
      const u = col / (GRID - 1), v = row / (GRID - 1);
      positions[i * 3] = x0 + (x1 - x0) * u;
      positions[i * 3 + 1] = grid[row * GRID + col];
      positions[i * 3 + 2] = z0 + (z1 - z0) * v;
      uvs[i * 2] = u;
      uvs[i * 2 + 1] = 1 - v;
    }
  }
  const indices = new Uint32Array((rows - 1) * (cols - 1) * 6);
  let k = 0;
  for (let r = 0; r < rows - 1; r += 1) {
    for (let c = 0; c < cols - 1; c += 1) {
      const a = r * cols + c, b = a + 1, cc = a + cols, d = cc + 1;
      indices.set([a, cc, b, b, cc, d], k);
      k += 6;
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.BufferAttribute(uvs, 2));
  geometry.setIndex(new THREE.BufferAttribute(indices, 1));
  geometry.computeVertexNormals();
  return geometry;
}

// ---- Imagery: MMGIS tiles (TMS Mercator) composited on a canvas ------------
type Bounds = { west: number; east: number; south: number; north: number };

function loadImage(url: string): Promise<HTMLImageElement | null> {
  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = url;
  });
}

async function runLimited<T>(tasks: Array<() => Promise<T>>, limit = 10): Promise<void> {
  let next = 0;
  const worker = async () => {
    while (next < tasks.length) await tasks[next++]();
  };
  await Promise.all(Array.from({ length: limit }, worker));
}

const mercatorRow = (lat: number, n: number) =>
  Math.floor(((1 - Math.asinh(Math.tan((lat * Math.PI) / 180)) / Math.PI) / 2) * n);
const rowToLat = (row: number, n: number) => (Math.atan(Math.sinh(Math.PI * (1 - (2 * row) / n))) * 180) / Math.PI;

type ImageryLayer = { url: string; alpha: number; filter: string };

// Colour: CTX with the same tint as the 2D map (see galeImageryLayer in tactical.html).
// No HiRISE or labels, so the whole crater has a uniform, realistic tone.
const OVERVIEW_STACK: ImageryLayer[] = [
  { url: GALE_LAYERS.ctx, alpha: 0.72, filter: 'sepia(.72) saturate(1.55) hue-rotate(326deg) brightness(.92)' },
];
// Detail: only contributes light and shade (luminance). Colour comes from the overview
// texture, so HiRISE grey strips and colour quads do not cause tone jumps.
const DETAIL_STACK: ImageryLayer[] = [
  { url: GALE_LAYERS.ctx, alpha: 1, filter: 'grayscale(1)' },
  { url: GALE_LAYERS.hirise, alpha: 1, filter: 'grayscale(1)' },
];

async function composeImagery(
  bounds: Bounds,
  zoom: number,
  stack: ImageryLayer[],
  onProgress: (done: number, total: number) => void,
) {
  const n = 2 ** zoom;
  const degPerPx = 360 / (n * 256);
  const canvas = document.createElement('canvas');
  canvas.width = Math.ceil((bounds.east - bounds.west) / degPerPx);
  canvas.height = Math.ceil((bounds.north - bounds.south) / degPerPx);
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = '#70463d'; // same background as #map
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const colStart = Math.floor(((bounds.west + 180) / 360) * n);
  const colEnd = Math.floor(((bounds.east + 180) / 360) * n);
  const rowStart = mercatorRow(bounds.north, n);
  const rowEnd = mercatorRow(bounds.south, n);
  const tiles: Array<{ col: number; row: number }> = [];
  for (let col = colStart; col <= colEnd; col += 1) for (let row = rowStart; row <= rowEnd; row += 1) tiles.push({ col, row });

  const total = tiles.length * stack.length;
  let done = 0;
  for (const layer of stack) {
    const images = new Map<string, HTMLImageElement | null>();
    await runLimited(
      tiles.map(({ col, row }) => async () => {
        // "?cors" gives these CORS requests their own cache entry: the 2D map loads the same tiles
        // without CORS, and Chrome would otherwise reuse that response and block the WebGL texture.
        const url = `${layer.url.replace('{z}', String(zoom)).replace('{x}', String(col)).replace('{y}', String(n - 1 - row))}?cors`;
        images.set(`${col}/${row}`, await loadImage(url));
        onProgress(++done, total);
      }),
    );
    ctx.save();
    ctx.globalAlpha = layer.alpha;
    ctx.filter = layer.filter;
    for (const { col, row } of tiles) {
      const img = images.get(`${col}/${row}`);
      if (!img) continue;
      const west = (col / n) * 360 - 180, east = ((col + 1) / n) * 360 - 180;
      const north = rowToLat(row, n), south = rowToLat(row + 1, n);
      const x = (west - bounds.west) / degPerPx, y = (bounds.north - north) / degPerPx;
      ctx.drawImage(img, x, y, (east - west) / degPerPx, (north - south) / degPerPx);
    }
    ctx.restore();
  }
  return canvas;
}

function canvasTexture(canvas: HTMLCanvasElement): THREE.Texture {
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = renderer?.capabilities.getMaxAnisotropy() ?? 1;
  texture.generateMipmaps = true;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  return texture;
}

// ---- Scene ----------------------------------------------------------------
function initScene() {
  renderer = new THREE.WebGLRenderer({ antialias: true, logarithmicDepthBuffer: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  container.prepend(renderer.domElement);

  scene = new THREE.Scene();
  const sky = new THREE.Color('#1a1210');
  scene.background = sky;
  scene.fog = new THREE.Fog('#3a2418', 900, 2600);

  camera = new THREE.PerspectiveCamera(45, 1, 0.01, 3000);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.screenSpacePanning = false; // pan along the ground plane, like Google Earth
  controls.maxPolarAngle = Math.PI * 0.47;
  controls.minDistance = 0.4;
  controls.maxDistance = 700;
  controls.zoomSpeed = 1.4;
  // Like Google Earth: drag pans; right-click (or Ctrl+drag) rotates and tilts.
  controls.mouseButtons = { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE };
  controls.touches = { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE };

  // The imagery already has shading: strong ambient light and a soft sun.
  scene.add(new THREE.HemisphereLight('#fff4e6', '#4a2a1a', 1.7));
  const sun = new THREE.DirectionalLight('#fff1dc', 1.1);
  sun.position.set(-300, 400, -200);
  scene.add(sun);
  scene.add(overlayGroup);

  new ResizeObserver(resize).observe(container);
  resize();
}

function resize() {
  if (!renderer) return;
  const { clientWidth: w, clientHeight: h } = container;
  if (!w || !h) return;
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

function createTerrainMaterial(): THREE.MeshStandardMaterial {
  const material = new THREE.MeshStandardMaterial({ color: '#8a5a44', roughness: 1, metalness: 0 });
  material.onBeforeCompile = (shader) => {
    Object.assign(shader.uniforms, detailUniforms);
    shader.fragmentShader = shader.fragmentShader
      .replace(
        '#include <common>',
        '#include <common>\nuniform sampler2D detailMap;\nuniform vec4 detailRect;\nuniform float detailReady;',
      )
      .replace(
        '#include <map_fragment>',
        `#include <map_fragment>
        #ifdef USE_MAP
        vec2 detailUv = (vMapUv - detailRect.xy) / (detailRect.zw - detailRect.xy);
        if (detailReady > 0.5 && all(greaterThanEqual(detailUv, vec2(0.0))) && all(lessThanEqual(detailUv, vec2(1.0)))) {
          // Blend the edge of the detail patch into the overview texture.
          vec2 edge = smoothstep(vec2(0.0), vec2(0.15), detailUv) * smoothstep(vec2(0.0), vec2(0.15), 1.0 - detailUv);
          // Detail transfer: overview colour × (local detail luminance /
          // its ~300 m mean, read from a blurred mipmap).
          const vec3 LUMA = vec3(0.2126, 0.7152, 0.0722);
          float detailLuma = dot(texture2D(detailMap, detailUv).rgb, LUMA);
          float detailMean = max(dot(texture2D(detailMap, detailUv, 5.0).rgb, LUMA), 0.002);
          vec3 harmonized = diffuseColor.rgb * mix(1.0, clamp(detailLuma / detailMean, 0.5, 1.7), 0.8);
          diffuseColor.rgb = mix(diffuseColor.rgb, harmonized, edge.x * edge.y);
        }
        #endif`,
      );
  };
  return material;
}

async function loadEverything() {
  heights = await loadHeights();
  setStatus('Building terrain…');
  const material = createTerrainMaterial();
  terrain = new THREE.Mesh(buildTerrainGeometry(heights), material);
  applyExaggeration();
  scene.add(terrain);
  refreshOverlays(true);
  flyToMapView();

  const overview = await composeImagery(STL_BOUNDS, OVERVIEW_ZOOM, OVERVIEW_STACK, (d, t) =>
    setStatus(`Draping CTX/HiRISE imagery over the terrain… ${Math.round((d / t) * 100)}%`),
  );
  material.map = canvasTexture(overview);
  material.color.set('#ffffff');
  material.needsUpdate = true;
  setStatus('Loading Curiosity corridor detail…');

  const detail = await composeImagery(DETAIL_BOUNDS, DETAIL_ZOOM, DETAIL_STACK, (d, t) =>
    setStatus(`Loading Curiosity corridor detail… ${Math.round((d / t) * 100)}%`),
  );
  const lonSpan = STL_BOUNDS.east - STL_BOUNDS.west, latSpan = STL_BOUNDS.north - STL_BOUNDS.south;
  detailUniforms.detailMap.value = canvasTexture(detail);
  detailUniforms.detailRect.value.set(
    (DETAIL_BOUNDS.west - STL_BOUNDS.west) / lonSpan,
    (DETAIL_BOUNDS.south - STL_BOUNDS.south) / latSpan,
    (DETAIL_BOUNDS.east - STL_BOUNDS.west) / lonSpan,
    (DETAIL_BOUNDS.north - STL_BOUNDS.south) / latSpan,
  );
  detailUniforms.detailReady.value = 1;
  setStatus('');
}

function applyExaggeration() {
  const factor = Number(exaggeration.value);
  exaggerationValue.textContent = `${factor.toFixed(1)}×`;
  if (terrain) terrain.scale.y = factor;
  overlayGroup.scale.y = factor;
}

// ---- 2D map routes and waypoints on the terrain -----------------------------
function collect(layer: LeafletLayer, out: LeafletLayer[]) {
  if (layer.eachLayer) layer.eachLayer((child) => collect(child, out));
  else out.push(layer);
}

function overlaySources(): LeafletLayer[] {
  const out: LeafletLayer[] = [];
  if (typeof layers === 'undefined') return out;
  for (const key of ['route', 'customRoute', 'returnRoute', 'wps'] as const) {
    if (map.hasLayer(layers[key])) collect(layers[key], out);
  }
  return out;
}

function refreshOverlays(force = false) {
  if (!heights) return;
  const sources = overlaySources();
  const signature = sources
    .map((l) => JSON.stringify(l.getLatLngs ? l.getLatLngs() : l.getLatLng?.()) + (l.options?.color ?? ''))
    .join('|');
  if (!force && signature === overlaySignature) return;
  overlaySignature = signature;

  overlayGroup.children.forEach((child) => {
    const mesh = child as THREE.Mesh;
    mesh.geometry?.dispose();
    (mesh.material as THREE.Material)?.dispose();
  });
  overlayGroup.clear();

  // Height above the terrain in km (before exaggeration) so they do not sink.
  const lift = 0.025;
  for (const layer of sources) {
    const color = new THREE.Color(layer.options?.color ?? '#45f3ff');
    if (layer.getLatLngs) {
      const flat = (layer.getLatLngs() as Array<LatLng | LatLng[]>).flat() as LatLng[];
      if (flat.length < 2) continue;
      // Skip the wide semi-transparent halos; the main stroke is enough in 3D.
      if ((layer.options?.opacity ?? 1) < 0.5) continue;
      const points = flat.map(({ lat, lng }) => {
        const [x, z] = lonLatToScene(lng, lat);
        return new THREE.Vector3(x, elevationAt(lng, lat) + lift, z);
      });
      const curve = new THREE.CatmullRomCurve3(points, false, 'centripetal');
      const geometry = new THREE.TubeGeometry(curve, Math.min(600, points.length * 6), 0.035, 6, false);
      overlayGroup.add(new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({ color, depthTest: true })));
    } else if (layer.getLatLng) {
      const { lat, lng } = layer.getLatLng();
      const [x, z] = lonLatToScene(lng, lat);
      const marker = new THREE.Mesh(
        new THREE.SphereGeometry(0.09, 16, 12),
        new THREE.MeshBasicMaterial({ color: layer.options?.color ?? '#45f3ff' }),
      );
      marker.position.set(x, elevationAt(lng, lat) + lift * 3, z);
      overlayGroup.add(marker);
    }
  }
}

// ---- Camera synced with the 2D map -----------------------------------------
function flyToMapView() {
  // Top-down camera, north up, framing exactly the area visible in the 2D map.
  const view = map.getBounds();
  const center = view.getCenter();
  const lon = Math.min(IMAGERY_BOUNDS.east, Math.max(IMAGERY_BOUNDS.west, center.lng));
  const lat = Math.min(IMAGERY_BOUNDS.north, Math.max(IMAGERY_BOUNDS.south, center.lat));
  // EPSG:4326 map: the vertical span in degrees maps directly to kilometres on the ground.
  const heightKm = (view.getNorth() - view.getSouth()) * KM_PER_DEG;
  const [x, z] = lonLatToScene(lon, lat);
  const y = elevationAt(lon, lat) * Number(exaggeration.value);
  const distance = Math.min(
    controls.maxDistance,
    Math.max(controls.minDistance, heightKm / 2 / Math.tan((camera.fov * Math.PI) / 360)),
  );
  controls.target.set(x, y, z);
  // A tiny southward offset keeps OrbitControls' orientation defined: screen up = north.
  camera.position.set(x, y + distance, z + distance * 1e-4);
  controls.update();
}

function syncMapToCamera() {
  const [lon, lat] = sceneToLonLat(controls.target.x, controls.target.z);
  map.setView([lat, lon], map.getZoom(), { animate: false });
}

// ---- Render loop and activation --------------------------------------------
let lastOverlayCheck = 0;
function animate(time: number) {
  animationId = requestAnimationFrame(animate);
  controls.update();
  if (time - lastOverlayCheck > 1000) {
    lastOverlayCheck = time;
    refreshOverlays();
  }
  renderer!.render(scene, camera);
}

function setActive(next: boolean) {
  active = next;
  container.hidden = !next;
  document.body.classList.toggle('terrain3d-active', next);
  mapElement.style.visibility = next ? 'hidden' : '';
  toggleButton.textContent = next ? '🗺️ 2D MAP' : '🏔️ 3D RELIEF';
  toggleButton.setAttribute('aria-pressed', String(next));
  cancelAnimationFrame(animationId);
  if (next) {
    if (!renderer) initScene();
    resize();
    if (!loadPromise) {
      loadPromise = loadEverything().catch((error) => {
        console.error('[terrain3d]', error);
        setStatus('Could not load the 3D relief. Press "3D relief" again to retry.');
        loadPromise = null;
      });
    } else if (terrain) {
      flyToMapView();
      refreshOverlays(true);
    }
    animate(performance.now());
  } else {
    if (terrain) syncMapToCamera();
    map.invalidateSize();
  }
}

function syncAvailability() {
  // The relief only exists for Gale and uses the default map imagery.
  const available = zoneSelect.value === 'gale';
  toggleButton.disabled = !available;
  toggleButton.title = available ? 'View Gale Crater in 3D with satellite imagery' : '3D relief is only available for Gale Crater';
  toggleButton.style.opacity = available ? '' : '0.45';
  if (!available && active) setActive(false);
}

toggleButton.addEventListener('click', () => setActive(!active));
zoneSelect.addEventListener('change', syncAvailability);
basemapSelect.addEventListener('change', syncAvailability);
exaggeration.addEventListener('input', applyExaggeration);
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && active) setActive(false);
});
syncAvailability();
