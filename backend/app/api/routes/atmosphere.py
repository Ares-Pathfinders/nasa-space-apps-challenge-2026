from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.atmosphere import (
    PSAAtmosphericResponse,
    ZoneAtmosphericAnalysis,
)
from app.services.psa_service import (
    PSAService,
    ESA_PSA_PORTAL_URL,
    ESA_PSA_TAP_URL
)

router = APIRouter(prefix="/atmosphere", tags=["Martian Atmospheric Gases (ESA PSA)"])

@router.get(
    "/zones",
    response_model=PSAAtmosphericResponse,
    summary="Get atmospheric gas analysis by zone (ESA Planetary Science Archive)",
    description="Returns the atmospheric gas composition detected in different Mars zones from ESA Planetary Science Archive (PSA) data (ExoMars TGO NOMAD/ACS and Mars Express PFS/SPICAM)."
)
def get_all_atmospheric_zones():
    return PSAService.get_all_zones()

@router.get(
    "/zones/{zone_id}",
    response_model=ZoneAtmosphericAnalysis,
    summary="Get the atmospheric gases of a specific zone",
    description="Returns the spectroscopic gas detail, isotopic ratios and astronaut assessment for a specific Martian zone."
)
def get_zone_by_id(zone_id: str):
    zone = PSAService.get_zone_by_id(zone_id)
    if not zone:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zone_id}' not found. Available zones: jezero-crater-delta, mount-sharp-gale-crater, valles-marineris-canyon, olympus-mons-caldera, planum-boreum-north-polar, hellas-planitia-basin"
        )
    return zone

@router.get(
    "/query",
    summary="Find gases in the zone closest to Martian coordinates",
    description="Given a latitude and longitude on Mars, finds the closest analysed spectrometry zone and reports its atmospheric composition and gases."
)
def query_atmosphere_by_coordinates(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Martian latitude (-90 to +90)"),
    longitude: float = Query(..., ge=-180.0, le=360.0, description="Martian longitude (-180 to +360)")
):
    # Normalize longitude to [-180, 180] if provided in [0, 360]
    norm_lon = longitude
    if norm_lon > 180.0:
        norm_lon -= 360.0
    return PSAService.find_nearest_zone(latitude, norm_lon)

@router.get(
    "/summary",
    summary="Global summary of Martian gases and impact on astronauts",
    description="Provides a global balance of chemical species in the Martian atmosphere, the ESA missions involved and EVA life-support considerations."
)
def get_gas_summary():
    return PSAService.get_gas_summary()

@router.get(
    "/portal-link",
    summary="Generate a direct search link to the Planetary Science Archive (PSA)",
    description="Builds the URL with search parameters to inspect the datasets in the official ESA PSA web interface."
)
def get_psa_portal_link(
    mission: str = Query(default="ExoMars2016", description="Mission (ExoMars2016, MarsExpress)"),
    instrument: str = Query(default="NOMAD,ACS", description="Instruments (NOMAD, ACS, PFS, SPICAM)"),
    target: str = Query(default="Mars", description="Target body"),
    zone_id: Optional[str] = Query(default=None, description="Optional zone identifier to filter by coordinates")
):
    base_url = f"{ESA_PSA_PORTAL_URL}?mission={mission}&instrument={instrument}&target={target}"
    if zone_id:
        zone = PSAService.get_zone_by_id(zone_id)
        if zone:
            base_url += f"&lat={zone.coordinates.latitude}&lon={zone.coordinates.longitude}"
    return {
        "portal_name": "ESA Planetary Science Archive",
        "search_url": base_url,
        "tap_endpoint": ESA_PSA_TAP_URL
    }

@router.get(
    "/tap-query",
    summary="Run an ADQL query via the ESA Table Access Protocol (TAP)",
    description="Sends an ADQL query to the ESA PSA archive TAP endpoint (or returns the status when running offline)."
)
async def run_tap_query(
    adql: str = Query(
        default="SELECT TOP 5 obs_id, instrument_name, target_name FROM psa.epn_core WHERE instrument_name LIKE '%NOMAD%'",
        description="ADQL statement for the ESA psa.epn_core table"
    )
):
    return await PSAService.query_esa_psa_tap(adql_query=adql)
