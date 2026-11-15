import {
  ExplorationSite,
  PathfindingRequest,
  PathfindingResponse,
  RoverPhotosResponse,
  PSAAtmosphericResponse,
  ZoneAtmosphericAnalysis
} from '../types/mars';

// Same-origin by default: works with the backend serving dist on any port and with the Vite dev proxy.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    if (!res.ok) throw new Error('Health check failed');
    return await res.json();
  } catch (error) {
    console.warn('API Health check warning:', error);
    return { status: 'offline', error: String(error) };
  }
}

export async function fetchSites(): Promise<ExplorationSite[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/sites`);
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (error) {
    console.error('Failed to fetch sites from backend, using fallback sites:', error);
    // Reliable fallback sites
    return [
      {
        id: "mount-sharp-boxwork",
        name: "Mount Sharp - Boxwork Formations",
        region: "Aeolis Mons, Gale Crater",
        coordinates: { latitude: -4.589, longitude: 137.441, elevation_m: -4450.0 },
        rover_mission: "Curiosity (MSL)",
        landing_year: 2012,
        summary: "A prominent 5.5-km high sedimentary mound in Gale Crater with boxwork mineral ridges formed by ancient groundwater.",
        objectives: [
          { id: "1", title: "Subsurface Hydrothermal Vein Sampling", category: "Mineralogy", priority: "PRIMARY", description: "Sample boxwork crystalline ridges." },
          { id: "2", title: "Clay-to-Sulfate Transition Layer Profiling", category: "Paleoclimate", priority: "PRIMARY", description: "Inspect contact beds." }
        ],
        hazards: [
          { hazard_type: "Steep Grade Scarps", severity: "HIGH", description: "Terraced cliff edges with slopes > 24°.", mitigation: "Maintain 5m standoff from scarp edge." }
        ],
        environment: {
          avg_temp_c: -48.0,
          min_temp_c: -88.0,
          max_temp_c: -12.0,
          radiation_mgy_day: 0.23,
          atmospheric_pressure_pa: 780.0,
          dust_opacity_tau: 0.65
        },
        default_sol: 1000,
        recommended_cameras: ["MAST", "NAV_LEFT_B", "CHEMCAM"],
        available_layers: ["optical", "elevation", "thermal", "radiation"]
      },
      {
        id: "jezero-crater-delta",
        name: "Jezero Crater Delta",
        region: "Syrtis Major Quadrangle",
        coordinates: { latitude: 18.38, longitude: 77.58, elevation_m: -2500.0 },
        rover_mission: "Perseverance (Mars 2020)",
        landing_year: 2021,
        summary: "Ancient river-lake delta system rich in carbonates, clays, and mudstones with high biosignature preservation potential.",
        objectives: [
          { id: "3", title: "Delta Front Siltstone Sampling", category: "Astrobiology", priority: "PRIMARY", description: "Bottomset siltstone beds for microbial fossils." }
        ],
        hazards: [
          { hazard_type: "Fine-Grained Sand Dune Traps", severity: "HIGH", description: "Transverse Aeolian Ridges (TARs) with loose silty sand.", mitigation: "Bypass ripples wider than 2 meters." }
        ],
        environment: {
          avg_temp_c: -54.0,
          min_temp_c: -92.0,
          max_temp_c: -15.0,
          radiation_mgy_day: 0.25,
          atmospheric_pressure_pa: 720.0,
          dust_opacity_tau: 0.55
        },
        default_sol: 100,
        recommended_cameras: ["NAVCAM_LEFT", "MCZ_RIGHT", "SUPERCAM"],
        available_layers: ["optical", "elevation", "thermal", "radiation"]
      }
    ];
  }
}

export async function fetchRoverPhotos(rover = 'curiosity', sol = 1000, camera?: string): Promise<RoverPhotosResponse> {
  const url = new URL(`${API_BASE_URL}/rover-photos`, window.location.origin);
  url.searchParams.set('rover', rover);
  url.searchParams.set('sol', String(sol));
  if (camera) {
    url.searchParams.set('camera', camera);
  }

  try {
    const res = await fetch(url.toString());
    if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
    return await res.json();
  } catch (error) {
    console.warn('Failed to fetch rover photos, using fallback:', error);
    return {
      rover,
      sol,
      camera,
      total_photos: 1,
      source: 'curated_fallback',
      photos: [
        {
          id: 1026858,
          sol,
          camera: { name: "MAST", full_name: "Mast Camera" },
          img_src: "https://mars.nasa.gov/msl-raw-images/msss/01000/mcam/1000MR0044631300503690E01_DXXX.jpg",
          earth_date: "2015-05-31"
        }
      ]
    };
  }
}

export async function simulateRoute(req: PathfindingRequest): Promise<PathfindingResponse> {
  const res = await fetch(`${API_BASE_URL}/pathfinding/simulate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req)
  });
  if (!res.ok) {
    throw new Error(`Failed to simulate route: ${res.statusText}`);
  }
  return await res.json();
}

export async function fetchAtmosphericZones(): Promise<PSAAtmosphericResponse> {
  const res = await fetch(`${API_BASE_URL}/atmosphere/zones`);
  if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
  return await res.json();
}

export async function fetchAtmosphereZone(zoneId: string): Promise<ZoneAtmosphericAnalysis> {
  const res = await fetch(`${API_BASE_URL}/atmosphere/zones/${zoneId}`);
  if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
  return await res.json();
}

export async function queryAtmosphereByCoords(latitude: number, longitude: number) {
  const res = await fetch(`${API_BASE_URL}/atmosphere/query?latitude=${latitude}&longitude=${longitude}`);
  if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
  return await res.json();
}
