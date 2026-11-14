from typing import List, Optional
from pydantic import BaseModel, Field

class LatLonPoint(BaseModel):
    latitude: float
    longitude: float
    elevation_m: Optional[float] = None

class PathWaypoint(BaseModel):
    index: int
    latitude: float
    longitude: float
    elevation_m: float
    slope_deg: float
    cumulative_distance_m: float
    hazard_warning: Optional[str] = None
    radiation_rate_ugy_h: float
    estimated_energy_kcal: float

class PathfindingRequest(BaseModel):
    site_id: str
    start: LatLonPoint
    target: LatLonPoint
    max_slope_limit_deg: float = Field(
        default=15.0,
        ge=8.0,
        le=25.0,
        description="Maximum slope allowed in the route graph",
    )
    suit_payload_kg: float = Field(default=120.0, description="Astronaut + suit total mass in kg")
    eva_time_limit_minutes: float = Field(
        default=360.0, gt=0.0, description="Max EVA duration limit (6 hours)"
    )
    science_priority_weight: float = Field(default=0.4, description="Weight (0-1) prioritizing science POIs")

class PathfindingResponse(BaseModel):
    site_id: str
    total_distance_m: float
    estimated_duration_min: float
    max_slope_deg: float
    average_slope_deg: float
    total_elevation_gain_m: float
    total_elevation_loss_m: float
    estimated_o2_consumed_liters: float
    total_radiation_dose_usv: float
    risk_level: str = Field(description="LOW, MODERATE, HIGH, CRITICAL")
    safety_margins: dict
    waypoints: List[PathWaypoint]
