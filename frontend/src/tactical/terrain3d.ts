/**
 * Vista "Relieve 3D" del visor táctico (tactical.html), estilo Google Earth.
 *
 * Usa el modelo public/models/gale_crater.stl como relieve y le superpone las
 * imágenes MMGIS de Gale: el color sale del CTX 6 m con el tinte del mapa 2D y,
 * en el corredor de Curiosity, el detalle de CTX/HiRISE se aplica sólo como
 * luminancia para que no haya cambios bruscos de color. Encima van las rutas y
 * los hitos que haya en el mapa.
 *
 * El STL no trae coordenadas. Su posición se obtuvo ajustándolo al DEM
 * MOLA/HRSC blend de 200 m (correlación 0,9998): es una rejilla de 513×513 alturas,
 * con el norte hacia +Y, que cubre la caja STL_BOUNDS. Su Z sigue
 * z = ELEV_SCALE · elevación(m) + ELEV_OFFSET (≈2,9× de exageración de fábrica).
 */
import * as THREE from 'three';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

// ---- Globales del script clásico de tactical.html (Leaflet) ----------------
type LatLng = { lat: number; lng: number };
type LeafletLayer = {
  getLatLngs?: () => LatLng[] | LatLng[][];
  getLatLng?: () => LatLng;
  options?: { color?: string; fillColor?: string; weight?: number; opacity?: number };
  eachLayer?: (fn: (layer: LeafletLayer) => void) => void;
};
type LeafletMap = {
  getCenter: () => LatLng;
  getZoom: () => number;
  getSize: () => { x: number; y: number };
  setView: (center: [number, number], zoom: number, options?: object) => void;
  hasLayer: (layer: LeafletLayer) => boolean;
  invalidateSize: () => void;
};
declare const map: LeafletMap;
declare const layers: Record<'route' | 'customRoute' | 'returnRoute' | 'wps', LeafletLayer>;

// ---- Georreferenciación del STL --------------------------------------------
const MODEL_URL = `${import.meta.env.BASE_URL}models/gale_crater.stl`;
const STL_BOUNDS = { west: 135.97957, east: 139.49492, south: -7.84402, north: -3.21708 };
const ELEV_SCALE = 0.00147483; // unidades STL por metro
const ELEV_OFFSET = 8.426;
const GRID = 513;

const MARS_RADIUS_KM = 3396.19;
const KM_PER_DEG = (MARS_RADIUS_KM * Math.PI) / 180;
const CENTER_LAT = (STL_BOUNDS.north + STL_BOUNDS.south) / 2;
const CENTER_LON = (STL_BOUNDS.west + STL_BOUNDS.east) / 2;
const COS_LAT = Math.cos((CENTER_LAT * Math.PI) / 180);

// Zona de alta resolución (corredor de Curiosity / cuadrícula táctica).
const DETAIL_BOUNDS = { west: 137.25, east: 137.61, south: -4.84, north: -4.47 };
const OVERVIEW_ZOOM = 10; // ≈80 m/px sobre todo el STL
const DETAIL_ZOOM = 13; // ≈10 m/px en el corredor

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
  if (!el) throw new Error(`[terrain3d] Falta el elemento #${id}`);
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

// ---- Estado ---------------------------------------------------------------
let renderer: THREE.WebGLRenderer | null = null;
let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let controls: OrbitControls;
let terrain: THREE.Mesh<THREE.BufferGeometry, THREE.MeshStandardMaterial> | null = null;
let heights: Float32Array | null = null; // elevación en km, fila 0 = norte
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

// ---- Relieve desde el STL --------------------------------------------------
async function loadHeights(): Promise<Float32Array> {
  setStatus('Descargando modelo de relieve del cráter Gale…');
  const geometry = await new STLLoader().loadAsync(MODEL_URL, (event) => {
    if (event.lengthComputable) {
      setStatus(`Descargando modelo de relieve del cráter Gale… ${Math.round((event.loaded / event.total) * 100)}%`);
    }
  });
  const pos = geometry.getAttribute('position');
  let xMin = Infinity, xMax = -Infinity, yMin = Infinity, yMax = -Infinity;
  for (let i = 0; i < pos.count; i += 1) {
    if (pos.getZ(i) <= 0) continue; // base del sólido
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

/** Elevación (km) en una coordenada, interpolada bilinealmente. */
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
  const [x0, z0] = lonLatToScene(STL_BOUNDS.west, STL_BOUNDS.north);
  const [x1, z1] = lonLatToScene(STL_BOUNDS.east, STL_BOUNDS.south);
  const positions = new Float32Array(GRID * GRID * 3);
  const uvs = new Float32Array(GRID * GRID * 2);
  for (let row = 0; row < GRID; row += 1) {
    for (let col = 0; col < GRID; col += 1) {
      const i = row * GRID + col;
      const u = col / (GRID - 1), v = row / (GRID - 1);
      positions[i * 3] = x0 + (x1 - x0) * u;
      positions[i * 3 + 1] = grid[i];
      positions[i * 3 + 2] = z0 + (z1 - z0) * v;
      uvs[i * 2] = u;
      uvs[i * 2 + 1] = 1 - v;
    }
  }
  const indices = new Uint32Array((GRID - 1) * (GRID - 1) * 6);
  let k = 0;
  for (let row = 0; row < GRID - 1; row += 1) {
    for (let col = 0; col < GRID - 1; col += 1) {
      const a = row * GRID + col, b = a + 1, c = a + GRID, d = c + 1;
      indices.set([a, c, b, b, c, d], k);
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

// ---- Imágenes: tiles MMGIS (TMS Mercator) compuestos en un canvas -----------
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

// Color: CTX con el mismo tinte que el mapa 2D (ver galeImageryLayer en tactical.html).
// Sin HiRISE ni rótulos, para que todo el cráter tenga un tono uniforme y realista.
const OVERVIEW_STACK: ImageryLayer[] = [
  { url: GALE_LAYERS.ctx, alpha: 0.72, filter: 'sepia(.72) saturate(1.55) hue-rotate(326deg) brightness(.92)' },
];
// Detalle: sólo aporta luces y sombras (luminancia). El color lo pone la textura general,
// así las franjas grises y los quads en color de HiRISE no producen saltos de tono.
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
  ctx.fillStyle = '#70463d'; // mismo fondo que #map
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
        const url = layer.url.replace('{z}', String(zoom)).replace('{x}', String(col)).replace('{y}', String(n - 1 - row));
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

// ---- Escena ---------------------------------------------------------------
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
  controls.screenSpacePanning = false; // desplazar sobre el plano, como Google Earth
  controls.maxPolarAngle = Math.PI * 0.47;
  controls.minDistance = 0.4;
  controls.maxDistance = 700;
  controls.zoomSpeed = 1.4;
  // Como Google Earth: arrastrar desplaza; clic derecho (o Ctrl+arrastrar) gira e inclina.
  controls.mouseButtons = { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE };
  controls.touches = { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE };

  // Las imágenes ya traen sombreado: luz ambiente alta y un sol suave.
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
          // Funde el borde del parche de detalle con la textura general.
          vec2 edge = smoothstep(vec2(0.0), vec2(0.15), detailUv) * smoothstep(vec2(0.0), vec2(0.15), 1.0 - detailUv);
          // Transferencia de detalle: color de la textura general × (luminancia local del
          // detalle / su media en ~300 m, leída de un mipmap borroso).
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
  setStatus('Construyendo relieve…');
  const material = createTerrainMaterial();
  terrain = new THREE.Mesh(buildTerrainGeometry(heights), material);
  applyExaggeration();
  scene.add(terrain);
  refreshOverlays(true);
  flyToMapView();

  const overview = await composeImagery(STL_BOUNDS, OVERVIEW_ZOOM, OVERVIEW_STACK, (d, t) =>
    setStatus(`Proyectando imágenes CTX/HiRISE sobre el relieve… ${Math.round((d / t) * 100)}%`),
  );
  material.map = canvasTexture(overview);
  material.color.set('#ffffff');
  material.needsUpdate = true;
  setStatus('Cargando detalle del corredor de Curiosity…');

  const detail = await composeImagery(DETAIL_BOUNDS, DETAIL_ZOOM, DETAIL_STACK, (d, t) =>
    setStatus(`Cargando detalle del corredor de Curiosity… ${Math.round((d / t) * 100)}%`),
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

// ---- Rutas e hitos del mapa 2D sobre el relieve -------------------------------
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

  // Altura sobre el terreno en km (pre-exageración) para que no se hundan.
  const lift = 0.025;
  for (const layer of sources) {
    const color = new THREE.Color(layer.options?.color ?? '#45f3ff');
    if (layer.getLatLngs) {
      const flat = (layer.getLatLngs() as Array<LatLng | LatLng[]>).flat() as LatLng[];
      if (flat.length < 2) continue;
      // Ignora los halos anchos semitransparentes; el trazo principal basta en 3D.
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

// ---- Cámara sincronizada con el mapa 2D -----------------------------------
function flyToMapView() {
  const center = map.getCenter();
  const lon = Math.min(STL_BOUNDS.east, Math.max(STL_BOUNDS.west, center.lng));
  const lat = Math.min(STL_BOUNDS.north, Math.max(STL_BOUNDS.south, center.lat));
  // Ancho visible del mapa EPSG:4326 de Leaflet: 256·2^z px cada 180°.
  const widthKm = ((map.getSize().x * 180) / (256 * 2 ** map.getZoom())) * KM_PER_DEG * COS_LAT;
  const distance = Math.min(600, Math.max(1.5, widthKm / (2 * Math.tan((camera.fov * Math.PI) / 360) * camera.aspect)));
  const [x, z] = lonLatToScene(lon, lat);
  const y = elevationAt(lon, lat) * Number(exaggeration.value);
  controls.target.set(x, y, z);
  const tilt = (50 * Math.PI) / 180; // inclinación inicial desde la vertical
  camera.position.set(x, y + distance * Math.cos(tilt), z + distance * Math.sin(tilt));
  controls.update();
}

function syncMapToCamera() {
  const [lon, lat] = sceneToLonLat(controls.target.x, controls.target.z);
  map.setView([lat, lon], map.getZoom(), { animate: false });
}

// ---- Bucle y activación ---------------------------------------------------
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
  mapElement.style.visibility = next ? 'hidden' : '';
  toggleButton.textContent = next ? '🗺️ MAPA 2D' : '🏔️ RELIEVE 3D';
  toggleButton.setAttribute('aria-pressed', String(next));
  cancelAnimationFrame(animationId);
  if (next) {
    if (!renderer) initScene();
    resize();
    if (!loadPromise) {
      loadPromise = loadEverything().catch((error) => {
        console.error('[terrain3d]', error);
        setStatus('No se pudo cargar el relieve 3D. Vuelve a pulsar «Relieve 3D» para reintentar.');
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
  // El relieve sólo existe para Gale y usa las imágenes del mapa predeterminado.
  const available = zoneSelect.value === 'gale';
  toggleButton.disabled = !available;
  toggleButton.title = available ? 'Ver el cráter Gale en 3D con las imágenes del satélite' : 'Relieve 3D disponible sólo para el cráter Gale';
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
