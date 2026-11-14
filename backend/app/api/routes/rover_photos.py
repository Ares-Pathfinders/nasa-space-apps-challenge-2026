from typing import Optional
from fastapi import APIRouter, Query
from app.services.nasa_service import nasa_service
from app.models.rover import RoverPhotosResponse

router = APIRouter(prefix="/rover-photos", tags=["NASA Rover Telemetry"])

@router.get("", response_model=RoverPhotosResponse)
async def get_rover_photos(
    rover: str = Query("curiosity", description="NASA Rover name: 'curiosity', 'perseverance', 'opportunity'"),
    sol: int = Query(1000, description="Martian solar day (sol) since landing", ge=0),
    camera: Optional[str] = Query(None, description="Optional camera filter, e.g. 'MAST', 'NAVCAM_LEFT', 'MCZ_RIGHT'"),
    page: int = Query(1, description="Result page index", ge=1)
):
    """
    Fetch genuine rover POV imagery from the NASA Mars Photos API with automatic fallback cache.
    Provides astronauts with point-of-view visual reference of the Martian surface terrain.
    """
    return await nasa_service.get_rover_photos(rover=rover, sol=sol, camera=camera, page=page)
