from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.sites import Coordinates

class GasMeasurement(BaseModel):
    name: str = Field(..., description="Common gas name in Spanish / English")
    formula: str = Field(..., description="Chemical formula (e.g., CO2, H2O, CH4, O3, HCl)")
    concentration: str = Field(..., description="Human-readable formatted concentration (e.g., '95.32%', '180 ppm', '0.45 ppb')")
    concentration_value: float = Field(..., description="Numerical concentration value")
    concentration_unit: str = Field(..., description="Measurement unit ('%', 'ppm', 'ppb')")
    percentage: Optional[float] = Field(None, description="Volume percentage if applicable (0-100%)")
    instrument: str = Field(..., description="ESA instrument (e.g., NOMAD, ACS, PFS, SPICAM)")
    mission: str = Field(..., description="ESA mission (e.g., ExoMars 2016 TGO, Mars Express)")
    observation_technique: str = Field(..., description="Technique: Solar Occultation, Nadir Spectroscopy, Limb Sounding")
    variability: str = Field(..., description="Temporal/seasonal variability pattern")
    status: str = Field(..., description="Detection status: 'DETECTED', 'TRACE', 'SEASONAL VARIATION', 'LOCAL PLUME', 'UPPER LIMIT'")
    scientific_significance: str = Field(..., description="Scientific, astrobiological or geochemical context")

class IsotopicRatio(BaseModel):
    ratio: str = Field(..., description="Isotope pair (e.g., D/H (Deuterium/Hydrogen), 13C/12C, 18O/16O)")
    value: str = Field(..., description="Measured ratio relative to Earth VSMOW or Mars standard")
    significance: str = Field(..., description="Climatological / escape history interpretation")
    instrument: str = Field(..., description="Measuring instrument from ESA PSA")

class EVAAtmosphericAssessment(BaseModel):
    breathability: str = Field(..., description="Direct breathing status for human crew")
    asphyxiation_hazard: str = Field(..., description="Hazard from CO2 levels and low atmospheric pressure")
    suit_pressure_delta_kpa: float = Field(..., description="Pressure differential between EVA suit (~30 kPa) and ambient surface pressure")
    isru_potential: str = Field(..., description="In-Situ Resource Utilization viability (e.g. MOXIE O2 extraction, Sabatier fuel synthesis)")
    toxicity_warnings: List[str] = Field(default_factory=list, description="Specific atmospheric toxin or oxidant alerts")

class ZoneAtmosphericAnalysis(BaseModel):
    zone_id: str = Field(..., description="Unique zone identifier")
    zone_name: str = Field(..., description="Geographical / scientific zone name")
    region: str = Field(..., description="Martian quadrangle or region")
    coordinates: Coordinates = Field(..., description="Latitude, longitude and MOLA elevation")
    surface_pressure_pa: float = Field(..., description="Average surface atmospheric pressure in Pascals")
    mean_surface_temp_c: float = Field(..., description="Average ambient temperature in Celsius")
    dominant_gas: str = Field(default="CO2 (Carbon Dioxide)", description="Primary atmospheric constituent")
    total_detected_gases: int = Field(..., description="Total count of monitored chemical species")
    gases: List[GasMeasurement] = Field(..., description="Detailed breakdown of detected and trace gases")
    isotopic_ratios: List[IsotopicRatio] = Field(default_factory=list, description="Isotopic ratio telemetry")
    eva_assessment: EVAAtmosphericAssessment = Field(..., description="Astronaut EVA and life support impact assessment")
    data_source: str = Field(
        default="ESA Planetary Science Archive (PSA) - ExoMars TGO & Mars Express",
        description="Originating scientific archive"
    )
    psa_search_url: str = Field(..., description="Direct URL to ESA Planetary Science Archive query portal")
    last_observation_orbit: Optional[str] = Field(None, description="Recent orbit or dataset observation ID")

class PSAAtmosphericResponse(BaseModel):
    archive: str = Field(default="ESA Planetary Science Archive (PSA)", description="Archive name")
    archive_portal: str = Field(default="https://psa.esa.int/psa/#/pages/search", description="Official portal URL")
    tap_endpoint: str = Field(default="https://psa.esa.int/psa-tap/tap/", description="Table Access Protocol endpoint")
    total_zones: int = Field(..., description="Number of analyzed zones")
    monitored_missions: List[str] = Field(
        default=["ExoMars 2016 Trace Gas Orbiter (TGO)", "Mars Express (MEX)"],
        description="Missions analyzed"
    )
    monitored_instruments: List[str] = Field(
        default=["NOMAD (Nadir and Occultation for MArs Discovery)", "ACS (Atmospheric Chemistry Suite)", "PFS (Planetary Fourier Spectrometer)", "SPICAM"],
        description="Instruments analyzed"
    )
    zones: List[ZoneAtmosphericAnalysis] = Field(..., description="Detailed zone-by-zone atmospheric records")
