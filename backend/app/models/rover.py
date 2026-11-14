from typing import List, Optional
from pydantic import BaseModel, Field

class RoverCamera(BaseModel):
    id: Optional[int] = None
    name: str
    rover_id: Optional[int] = None
    full_name: str

class RoverInfo(BaseModel):
    id: Optional[int] = None
    name: str
    landing_date: Optional[str] = None
    launch_date: Optional[str] = None
    status: Optional[str] = None

class RoverPhoto(BaseModel):
    id: int
    sol: int
    camera: RoverCamera
    img_src: str
    earth_date: str
    rover: RoverInfo

class RoverPhotosResponse(BaseModel):
    rover: str
    sol: int
    camera: Optional[str] = None
    total_photos: int
    source: str = Field(default="nasa_api", description="'nasa_api' or 'curated_fallback'")
    photos: List[RoverPhoto]
