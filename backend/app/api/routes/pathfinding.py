from fastapi import APIRouter
from app.models.pathfinding import PathfindingRequest, PathfindingResponse
from app.services.pathfinding_service import pathfinding_service

router = APIRouter(prefix="/pathfinding", tags=["Tactical Route Planning"])

@router.post("/simulate", response_model=PathfindingResponse)
async def simulate_route(request: PathfindingRequest):
    """
    Simulate a safety-optimized Marswalk (EVA) route between start and target coordinates.
    Computes elevation profile, slope limits, metabolic energy cost, and life-support margin of return.
    """
    return pathfinding_service.simulate_eva_route(request)
