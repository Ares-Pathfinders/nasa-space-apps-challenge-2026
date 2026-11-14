from typing import List
from fastapi import APIRouter
from app.models.sites import ExplorationSite, Coordinates, EnvironmentalParams, GeologicalHazard, ScientificObjective

router = APIRouter(prefix="/sites", tags=["Exploration Sites"])

EXPLORATION_SITES: List[ExplorationSite] = [
    ExplorationSite(
        id="mount-sharp-boxwork",
        name="Mount Sharp - Boxwork Formations",
        region="Aeolis Mons, Gale Crater",
        coordinates=Coordinates(
            latitude=-4.589,
            longitude=137.441,
            elevation_m=-4450.0
        ),
        rover_mission="Curiosity (MSL)",
        landing_year=2012,
        summary="A prominent 5.5-km high sedimentary mound in Gale Crater. The upper slopes feature rare 'boxwork' mineral ridge networks formed by ancient warm groundwater percolating through fractures.",
        objectives=[
            ScientificObjective(
                id="obj-boxwork-1",
                title="Subsurface Hydrothermal Vein Sampling",
                category="Mineralogy",
                priority="PRIMARY",
                description="Sample boxwork crystalline ridges to determine groundwater temperature, salinity, and pH during Mars' transition from wet to arid."
            ),
            ScientificObjective(
                id="obj-boxwork-2",
                title="Clay-to-Sulfate Transition Layer Profiling",
                category="Paleoclimate",
                priority="PRIMARY",
                description="Inspect the stratigraphic contact point between smectite clay beds and hydrated magnesium sulfates."
            ),
            ScientificObjective(
                id="obj-boxwork-3",
                title="Micro-organics Biosignature Detection",
                category="Astrobiology",
                priority="SECONDARY",
                description="Search for preservation of complex organic macromolecules within dense vein cements."
            )
        ],
        hazards=[
            GeologicalHazard(
                hazard_type="Steep Grade Scarps",
                severity="HIGH",
                description="Terraced cliff edges with slopes exceeding 24° prone to scree destabilization under foot pressure.",
                mitigation="Route traversal along lateral topographic contour lines; maintain 5m buffer from scarp edges."
            ),
            GeologicalHazard(
                hazard_type="Sharp Ventifact Ridges",
                severity="MODERATE",
                description="Wind-carved basalt stones ('ventifacts') capable of puncturing pressurized spacesuit boots and gloves.",
                mitigation="Use reinforced titanium-mesh gaiters and avoid direct kneel-down contacts."
            ),
            GeologicalHazard(
                hazard_type="Active Dust Devil Corridors",
                severity="LOW",
                description="Frequent thermal vortex plumes during mid-sol heating causing sudden solar panel/visor deposition.",
                mitigation="Stow exposed optical instrumentation when ambient static charge sensors detect vortex passage."
            )
        ],
        environment=EnvironmentalParams(
            avg_temp_c=-48.0,
            min_temp_c=-88.0,
            max_temp_c=-12.0,
            radiation_mgy_day=0.23,
            atmospheric_pressure_pa=780.0,
            dust_opacity_tau=0.65
        ),
        default_sol=1000,
        recommended_cameras=["MAST", "NAV_LEFT_B", "CHEMCAM"],
        available_layers=["optical", "elevation", "thermal", "radiation"]
    ),
    ExplorationSite(
        id="jezero-crater-delta",
        name="Jezero Crater Delta",
        region="Syrtis Major Quadrangle",
        coordinates=Coordinates(
            latitude=18.38,
            longitude=77.58,
            elevation_m=-2500.0
        ),
        rover_mission="Perseverance (Mars 2020)",
        landing_year=2021,
        summary="A preserved river-lake delta system rich in carbonates, smectites, and mudstones with exceptional biosignature preservation potential. Features steep erosional fronts and ancient braided channels.",
        objectives=[
            ScientificObjective(
                id="obj-jezero-1",
                title="Delta Front Siltstone Sampling",
                category="Astrobiology",
                priority="PRIMARY",
                description="Examine fine-grained bottomset beds at the base of the delta for potential microbial fossil structures."
            ),
            ScientificObjective(
                id="obj-jezero-2",
                title="Carbonate Rim Stratigraphy",
                category="Geology",
                priority="PRIMARY",
                description="Analyze precipitated magnesium carbonates along the paleolake shoreline to date the lacustrine era."
            ),
            ScientificObjective(
                id="obj-jezero-3",
                title="Igneous Floor Contact Analysis",
                category="Mineralogy",
                priority="SECONDARY",
                description="Evaluate the volcanic crater floor rock baseline prior to sediment inundation."
            )
        ],
        hazards=[
            GeologicalHazard(
                hazard_type="Fine-Grained Sand Dune Traps",
                severity="HIGH",
                description="Transverse Aeolian Ridges (TARs) with loose silty sand causing high foot sinkage (>20cm) and rover immobilization.",
                mitigation="Bypass ripples wider than 2 meters; utilize designated bedrock causeways mapped by orbital DTM."
            ),
            GeologicalHazard(
                hazard_type="Delta Scarp Rockfalls",
                severity="HIGH",
                description="Unconsolidated boulder scree along the 40m delta cliff face liable to slide under gravitational stress.",
                mitigation="Maintain minimum 15m standoff distance from vertical cliff overhangs."
            ),
            GeologicalHazard(
                hazard_type="Thermal Shock Cracking",
                severity="MODERATE",
                description="Extreme diurnal delta temperature variance (>75°C) inducing material stress in tools and suit joints.",
                mitigation="Schedule EVAs strictly during solar zenith thermal stability window (11:00 - 15:30 LMST)."
            )
        ],
        environment=EnvironmentalParams(
            avg_temp_c=-54.0,
            min_temp_c=-92.0,
            max_temp_c=-15.0,
            radiation_mgy_day=0.25,
            atmospheric_pressure_pa=720.0,
            dust_opacity_tau=0.55
        ),
        default_sol=100,
        recommended_cameras=["NAVCAM_LEFT", "MCZ_RIGHT", "SUPERCAM"],
        available_layers=["optical", "elevation", "thermal", "radiation"]
    ),
    ExplorationSite(
        id="candor-chasma-valles-marineris",
        name="Candor Chasma - Valles Marineris",
        region="Coprates Quadrangle",
        coordinates=Coordinates(
            latitude=-6.5,
            longitude=-75.5,
            elevation_m=-3800.0
        ),
        rover_mission="Orbital Science / Proposed Crew Landing",
        landing_year=2028,
        summary="One of the deepest and most spectrally diverse troughs in the 4,000-km Valles Marineris canyon system, exposing kilometers of sedimentary bedrock layers and vast interior layered deposits.",
        objectives=[
            ScientificObjective(
                id="obj-candor-1",
                title="Deep Crustal Bedrock Stratigraphy",
                category="Geology",
                priority="PRIMARY",
                description="Sample layered sulfate stacks exposed in canyon walls representing hundreds of millions of years of Martian climate evolution."
            ),
            ScientificObjective(
                id="obj-candor-2",
                title="Mass Wasting and Landslide Dynamics",
                category="Geology",
                priority="SECONDARY",
                description="Investigate gigantic debris aprons to model planetary mega-landslides."
            )
        ],
        hazards=[
            GeologicalHazard(
                hazard_type="Extreme Vertical Relief & Shadows",
                severity="CRITICAL",
                description="Canyon wall drop-offs of up to 4,000 meters causing severe line-of-sight communication blackouts and rapid thermal shadows.",
                mitigation="Deploy orbital relay repeaters on canyon rims; avoid shadows where temperatures drop below -100°C."
            )
        ],
        environment=EnvironmentalParams(
            avg_temp_c=-42.0,
            min_temp_c=-80.0,
            max_temp_c=-5.0,
            radiation_mgy_day=0.21,
            atmospheric_pressure_pa=890.0,
            dust_opacity_tau=0.70
        ),
        default_sol=1,
        recommended_cameras=["ORBITAL_HIRISE"],
        available_layers=["optical", "elevation", "thermal", "radiation"]
    )
]

@router.get("", response_model=List[ExplorationSite])
async def list_exploration_sites():
    """Retrieve all high-priority Martian exploration zones with coordinates, scientific goals, and hazards."""
    return EXPLORATION_SITES

@router.get("/{site_id}", response_model=ExplorationSite)
async def get_site_by_id(site_id: str):
    """Retrieve a single exploration zone by identifier."""
    for site in EXPLORATION_SITES:
        if site.id == site_id:
            return site
    return EXPLORATION_SITES[0]
