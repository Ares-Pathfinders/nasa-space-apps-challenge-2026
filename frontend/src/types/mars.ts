export interface Coordinates {
  latitude: number;
  longitude: number;
  elevation_m: number;
}

export interface EnvironmentalParams {
  avg_temp_c: number;
  min_temp_c: number;
  max_temp_c: number;
  radiation_mgy_day: number;
  atmospheric_pressure_pa: number;
  dust_opacity_tau: number;
}

export interface GeologicalHazard {
  hazard_type: string;
  severity: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  description: string;
  mitigation: string;
}

export interface ScientificObjective {
  id: string;
  title: string;
  category: string;
  priority: 'PRIMARY' | 'SECONDARY' | 'OPPORTUNISTIC';
  description: string;
}

export interface ExplorationSite {
  id: string;
  name: string;
  region: string;
  coordinates: Coordinates;
  rover_mission: string;
  landing_year: number;
  summary: string;
  objectives: ScientificObjective[];
  hazards: GeologicalHazard[];
  environment: EnvironmentalParams;
  default_sol: number;
  recommended_cameras: string[];
  available_layers: string[];
}

export interface RoverCamera {
  id?: number;
  name: string;
  rover_id?: number;
  full_name: string;
}

export interface RoverPhoto {
  id: number;
  sol: number;
  camera: RoverCamera;
  img_src: string;
  earth_date: string;
}

export interface RoverPhotosResponse {
  rover: string;
  sol: number;
  camera?: string;
  total_photos: number;
  source: 'nasa_api' | 'curated_fallback';
  photos: RoverPhoto[];
}

export interface PathWaypoint {
  index: number;
  latitude: number;
  longitude: number;
  elevation_m: number;
  slope_deg: number;
  cumulative_distance_m: number;
  hazard_warning?: string | null;
  radiation_rate_ugy_h: number;
  estimated_energy_kcal: number;
}

export interface PathfindingRequest {
  site_id: string;
  start: Coordinates;
  target: Coordinates;
  max_slope_limit_deg?: number;
  suit_payload_kg?: number;
  eva_time_limit_minutes?: number;
}

export interface PathfindingResponse {
  site_id: string;
  total_distance_m: number;
  estimated_duration_min: number;
  max_slope_deg: number;
  average_slope_deg: number;
  total_elevation_gain_m: number;
  total_elevation_loss_m: number;
  estimated_o2_consumed_liters: number;
  total_radiation_dose_usv: number;
  risk_level: 'LOW' | 'MODERATE' | 'HIGH' | 'CRITICAL';
  safety_margins: {
    o2_reserve_remaining_percent: number;
    safe_return_time_buffer_min: number;
    point_of_no_return_distance_m: number;
  };
  waypoints: PathWaypoint[];
}

export type LayerMode = 'optical' | 'elevation' | 'thermal' | 'radiation';
