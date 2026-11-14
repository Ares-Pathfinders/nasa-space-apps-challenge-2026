from typing import List, Optional
from pydantic import BaseModel, Field

class Coordinates(BaseModel):
    latitude: float = Field(..., description="Latitude in Martian degrees (-90 to +90)")
    longitude: float = Field(..., description="Longitude in Martian degrees (-180 to +180)")
    elevation_m: float = Field(..., description="Elevation in meters relative to Mars MOLA areoid datum")

class EnvironmentalParams(BaseModel):
    avg_temp_c: float = Field(..., description="Average surface temperature in Celsius")
    min_temp_c: float = Field(..., description="Minimum surface temperature in Celsius")
    max_temp_c: float = Field(..., description="Maximum surface temperature in Celsius")
    radiation_mgy_day: float = Field(..., description="Estimated cosmic radiation in mGy/day")
    atmospheric_pressure_pa: float = Field(..., description="Surface atmospheric pressure in Pascals")
    dust_opacity_tau: float = Field(..., description="Atmospheric dust optical depth index (tau)")

class GeologicalHazard(BaseModel):
    hazard_type: str = Field(..., description="Category of hazard (e.g. Steep Slope, Sand Trap, Boulder Field)")
    severity: str = Field(..., description="LOW, MODERATE, HIGH, CRITICAL")
    description: str
    mitigation: str

class ScientificObjective(BaseModel):
    id: str
    title: str
    category: str = Field(..., description="Geology, Astrobiology, Paleoclimate, Mineralogy")
    priority: str = Field(..., description="PRIMARY, SECONDARY, OPPORTUNISTIC")
    description: str

class ExplorationSite(BaseModel):
    id: str
    name: str
    region: str
    coordinates: Coordinates
    rover_mission: str = Field(..., description="Associated NASA robotic mission (e.g. Curiosity, Perseverance)")
    landing_year: int
    summary: str
    objectives: List[ScientificObjective]
    hazards: List[GeologicalHazard]
    environment: EnvironmentalParams
    default_sol: int = Field(default=1000, description="Recommended sol with rich POV image catalogue")
    recommended_cameras: List[str] = Field(default_factory=list)
    available_layers: List[str] = Field(
        default=["optical", "elevation", "thermal", "radiation"],
        description="Available data overlays for this site"
    )
