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
    summary="Obtener análisis de gases atmosféricos por zonas (ESA Planetary Science Archive)",
    description="Retorna la composición de gases atmosféricos detectados en distintas zonas de Marte a partir de datos del Planetary Science Archive (PSA) de la ESA (ExoMars TGO NOMAD/ACS y Mars Express PFS/SPICAM)."
)
def get_all_atmospheric_zones():
    return PSAService.get_all_zones()

@router.get(
    "/zones/{zone_id}",
    response_model=ZoneAtmosphericAnalysis,
    summary="Obtener gases atmosféricos de una zona específica",
    description="Retorna el detalle espectroscópico de gases, ratios isotópicos y evaluación para astronautas de una zona marciana específica."
)
def get_zone_by_id(zone_id: str):
    zone = PSAService.get_zone_by_id(zone_id)
    if not zone:
        raise HTTPException(
            status_code=404,
            detail=f"Zona '{zone_id}' no encontrada. Zonas disponibles: jezero-crater-delta, mount-sharp-gale-crater, valles-marineris-canyon, olympus-mons-caldera, planum-boreum-north-polar, hellas-planitia-basin"
        )
    return zone

@router.get(
    "/query",
    summary="Buscar gases en la zona más próxima a unas coordenadas marcianas",
    description="A partir de una latitud y longitud en Marte, localiza la zona espectrométrica analizada más cercana y reporta la composición atmosférica y los gases presentes."
)
def query_atmosphere_by_coordinates(
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitud marciana (-90 a +90)"),
    longitude: float = Query(..., ge=-180.0, le=360.0, description="Longitud marciana (-180 a +360)")
):
    # Normalize longitude to [-180, 180] if provided in [0, 360]
    norm_lon = longitude
    if norm_lon > 180.0:
        norm_lon -= 360.0
    return PSAService.find_nearest_zone(latitude, norm_lon)

@router.get(
    "/summary",
    summary="Resumen global de gases en Marte e impacto para astronautas",
    description="Proporciona un balance global de las especies químicas en la atmósfera marciana, misiones de la ESA involucradas y consideraciones para soporte vital EVA."
)
def get_gas_summary():
    return PSAService.get_gas_summary()

@router.get(
    "/portal-link",
    summary="Generar enlace de búsqueda directa al Planetary Science Archive (PSA)",
    description="Genera la URL con parámetros de búsqueda para inspeccionar los conjuntos de datos en la interfaz web oficial de la ESA PSA."
)
def get_psa_portal_link(
    mission: str = Query(default="ExoMars2016", description="Misión (ExoMars2016, MarsExpress)"),
    instrument: str = Query(default="NOMAD,ACS", description="Instrumentos (NOMAD, ACS, PFS, SPICAM)"),
    target: str = Query(default="Mars", description="Cuerpo celeste de destino"),
    zone_id: Optional[str] = Query(default=None, description="Identificador opcional de zona para filtrar por coordenadas")
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
    summary="Ejecutar consulta ADQL vía Table Access Protocol (TAP) de la ESA",
    description="Envía una consulta en lenguaje ADQL al protocolo TAP del archivo PSA de la ESA (o retorna el estado si se opera offline)."
)
async def run_tap_query(
    adql: str = Query(
        default="SELECT TOP 5 obs_id, instrument_name, target_name FROM psa.epn_core WHERE instrument_name LIKE '%NOMAD%'",
        description="Sentencia ADQL para la tabla psa.epn_core de la ESA"
    )
):
    return await PSAService.query_esa_psa_tap(adql_query=adql)
