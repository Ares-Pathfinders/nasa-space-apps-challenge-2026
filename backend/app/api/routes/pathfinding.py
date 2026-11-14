from fastapi import APIRouter, HTTPException
from app.models.pathfinding import PathfindingRequest, PathfindingResponse
from app.services.pathfinding_service import pathfinding_service
try:
    from backend.data.terrain_errors import TerrainDataError
except ModuleNotFoundError:
    from data.terrain_errors import TerrainDataError

router = APIRouter(prefix="/pathfinding", tags=["Tactical Route Planning"])

@router.post("/simulate", response_model=PathfindingResponse)
async def simulate_route(request: PathfindingRequest):
    """
    Simulate a safety-optimized Marswalk (EVA) route between start and target coordinates.
    Computes elevation profile, slope limits, metabolic energy cost, and life-support margin of return.
    """
    try:
        return pathfinding_service.simulate_eva_route(request)
    except TerrainDataError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
