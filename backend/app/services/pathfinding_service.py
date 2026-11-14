import math
import numpy as np
from typing import List
from app.models.pathfinding import PathfindingRequest, PathfindingResponse, PathWaypoint

MARS_RADIUS_KM = 3389.5

def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points on Mars in meters."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return (MARS_RADIUS_KM * 1000.0) * c

class PathfindingService:
    @staticmethod
    def simulate_eva_route(req: PathfindingRequest) -> PathfindingResponse:
        start_lat, start_lon = req.start.latitude, req.start.longitude
        end_lat, end_lon = req.target.latitude, req.target.longitude
        
        base_dist_m = haversine_distance_m(start_lat, start_lon, end_lat, end_lon)
        # Ensure at least 10 waypoints, or 1 every ~50m
        num_waypoints = max(10, min(60, int(base_dist_m / 40.0) + 1))
        
        lats = np.linspace(start_lat, end_lat, num_waypoints)
        lons = np.linspace(start_lon, end_lon, num_waypoints)
        
        start_elev = req.start.elevation_m if req.start.elevation_m is not None else -4500.0
        target_elev = req.target.elevation_m if req.target.elevation_m is not None else -4350.0
        
        # Synthetic undulating microtopography based on sinusoidal Martian dunes and crater slopes
        t = np.linspace(0, 1, num_waypoints)
        macro_slope = (1 - t) * start_elev + t * target_elev
        micro_relief = 18.0 * np.sin(t * 3 * np.pi) + 8.0 * np.cos(t * 7 * np.pi)
        elevations = macro_slope + micro_relief
        
        waypoints: List[PathWaypoint] = []
        cumulative_dist = 0.0
        total_elev_gain = 0.0
        total_elev_loss = 0.0
        max_slope = 0.0
        slopes: List[float] = []
        
        for i in range(num_waypoints):
            if i == 0:
                step_dist = 0.0
                slope_deg = 0.0
            else:
                step_dist = haversine_distance_m(lats[i-1], lons[i-1], lats[i], lons[i])
                cumulative_dist += step_dist
                delta_h = elevations[i] - elevations[i-1]
                if delta_h > 0:
                    total_elev_gain += delta_h
                else:
                    total_elev_loss += abs(delta_h)
                
                # Slope in degrees
                run = max(step_dist, 0.1)
                slope_rad = math.atan(abs(delta_h) / run)
                slope_deg = round(math.degrees(slope_rad), 2)
            
            slopes.append(slope_deg)
            if slope_deg > max_slope:
                max_slope = slope_deg
                
            hazard_warning = None
            if slope_deg > req.max_slope_limit_deg:
                hazard_warning = f"SLOPE EXCEEDED ({slope_deg}° > {req.max_slope_limit_deg}°)"
            elif slope_deg > 14.0:
                hazard_warning = f"MODERATE SLOPE WARNING ({slope_deg}°)"
                
            # Base Mars radiation at surface: ~25 uGy/h, modulated slightly by elevation
            rad_rate = round(24.5 + (elevations[i] / 1000.0) * -1.2, 2)
            
            # Metabolic cost: ~250 kcal/km on flat Mars 0.38g, extra for slope
            step_energy = (step_dist / 1000.0) * (240.0 + (slope_deg * 12.0))
            
            waypoints.append(
                PathWaypoint(
                    index=i,
                    latitude=round(float(lats[i]), 6),
                    longitude=round(float(lons[i]), 6),
                    elevation_m=round(float(elevations[i]), 2),
                    slope_deg=slope_deg,
                    cumulative_distance_m=round(cumulative_dist, 2),
                    hazard_warning=hazard_warning,
                    radiation_rate_ugy_h=max(18.0, rad_rate),
                    estimated_energy_kcal=round(step_energy, 2)
                )
            )

        avg_slope = round(float(np.mean(slopes)), 2)
        
        # Human Mars walking speed: ~2.8 km/h on suit, penalized by slope
        avg_speed_kmh = max(1.2, 3.2 - (avg_slope * 0.08))
        est_duration_min = round((cumulative_dist / 1000.0) / avg_speed_kmh * 60.0, 1)
        
        # O2 consumption: ~0.8 to 1.2 Liters/minute for active EVA
        est_o2_liters = round(est_duration_min * 0.95, 1)
        
        # Radiation accumulated: (rate in uGy/h) * hours
        total_rad_usv = round((24.5 * (est_duration_min / 60.0)), 2)
        
        # Risk assessment
        if max_slope > req.max_slope_limit_deg or est_duration_min > req.eva_time_limit_minutes:
            risk_level = "CRITICAL"
        elif max_slope > 15.0 or est_duration_min > (req.eva_time_limit_minutes * 0.75):
            risk_level = "HIGH"
        elif max_slope > 10.0:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"
            
        return PathfindingResponse(
            site_id=req.site_id,
            total_distance_m=round(cumulative_dist, 1),
            estimated_duration_min=est_duration_min,
            max_slope_deg=max_slope,
            average_slope_deg=avg_slope,
            total_elevation_gain_m=round(total_elev_gain, 1),
            total_elevation_loss_m=round(total_elev_loss, 1),
            estimated_o2_consumed_liters=est_o2_liters,
            total_radiation_dose_usv=total_rad_usv,
            risk_level=risk_level,
            safety_margins={
                "o2_reserve_remaining_percent": max(0.0, round(100.0 - (est_o2_liters / 300.0 * 100.0), 1)),
                "safe_return_time_buffer_min": round(max(0.0, req.eva_time_limit_minutes - est_duration_min), 1),
                "point_of_no_return_distance_m": round(cumulative_dist * 0.5, 1)
            },
            waypoints=waypoints
        )

pathfinding_service = PathfindingService()
