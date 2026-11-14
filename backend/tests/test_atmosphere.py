import sys
import math
import unittest
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.psa_service import PSAService, haversine_km, MARTIAN_ATMOSPHERIC_ZONES
from app.api.routes.atmosphere import (
    get_all_atmospheric_zones,
    get_zone_by_id,
    query_atmosphere_by_coordinates,
    get_gas_summary,
    get_psa_portal_link
)
from fastapi import HTTPException

class TestAtmosphericGasesPSA(unittest.TestCase):
    def test_get_all_zones(self):
        """Verify that all Martian atmospheric zones from ESA PSA are returned."""
        result = get_all_atmospheric_zones()
        self.assertEqual(result.archive, "ESA Planetary Science Archive (PSA)")
        self.assertGreaterEqual(result.total_zones, 6)
        self.assertEqual(len(result.zones), result.total_zones)

        # Check first zone integrity
        zone = result.zones[0]
        self.assertTrue(zone.zone_id)
        self.assertTrue(zone.zone_name)
        self.assertGreater(len(zone.gases), 0)
        self.assertTrue(zone.eva_assessment)

    def test_zone_jezero_crater(self):
        """Verify atmospheric telemetry for Jezero Crater."""
        zone = get_zone_by_id("jezero-crater-delta")
        self.assertEqual(zone.zone_id, "jezero-crater-delta")
        self.assertEqual(zone.coordinates.latitude, 18.38)
        self.assertEqual(zone.coordinates.longitude, 77.58)

        gas_formulas = [g.formula for g in zone.gases]
        self.assertIn("CO2", gas_formulas)
        self.assertIn("H2O", gas_formulas)
        self.assertIn("CH4", gas_formulas)
        self.assertIn("O3", gas_formulas)

        # Confirm ESA instruments
        instruments = [g.instrument for g in zone.gases]
        self.assertTrue(any("NOMAD" in inst for inst in instruments))

    def test_zone_mount_sharp_gale(self):
        """Verify Mount Sharp / Gale Crater data including ExoMars TGO HCl detection."""
        zone = get_zone_by_id("mount-sharp-gale-crater")
        self.assertEqual(zone.zone_id, "mount-sharp-gale-crater")

        gas_formulas = [g.formula for g in zone.gases]
        self.assertIn("HCl", gas_formulas)
        self.assertIn("CH4", gas_formulas)

        # Verify isotopic ratios
        self.assertGreater(len(zone.isotopic_ratios), 0)
        self.assertTrue(any("D/H" in iso.ratio for iso in zone.isotopic_ratios))

    def test_zone_not_found_raises_404(self):
        """Verify that requesting an invalid zone ID raises HTTPException 404."""
        with self.assertRaises(HTTPException) as ctx:
            get_zone_by_id("unknown-martian-zone-xyz")
        self.assertEqual(ctx.exception.status_code, 404)

    def test_query_atmosphere_by_coordinates(self):
        """Verify spatial lookup by latitude and longitude."""
        # Query near Jezero coordinates (lat=18.0, lon=77.0)
        result = query_atmosphere_by_coordinates(latitude=18.0, longitude=77.0)
        self.assertIn("nearest_zone", result)
        self.assertEqual(result["nearest_zone"].zone_id, "jezero-crater-delta")
        self.assertLess(result["distance_km"], 50.0)

        # Query near South Pole (lat=-80.0, lon=0.0)
        result_south = query_atmosphere_by_coordinates(latitude=-40.0, longitude=70.0)
        self.assertEqual(result_south["nearest_zone"].zone_id, "hellas-planitia-basin")

    def test_global_gas_summary(self):
        """Verify global composition and mission summary."""
        summary = get_gas_summary()
        self.assertIn("archive", summary)
        self.assertIn("global_composition", summary)
        self.assertIn("missions", summary)
        self.assertIn("human_survivability_note", summary)

    def test_psa_portal_link_generation(self):
        """Verify dynamic deep-link creation to official ESA PSA portal."""
        link_info = get_psa_portal_link(
            mission="ExoMars2016",
            instrument="NOMAD,ACS",
            zone_id="jezero-crater-delta"
        )
        self.assertIn("https://psa.esa.int/psa/#/pages/search", link_info["search_url"])
        self.assertIn("lat=18.38", link_info["search_url"])
        self.assertIn("lon=77.58", link_info["search_url"])

    def test_haversine_calculation(self):
        """Verify spherical distance calculation on Mars."""
        # 90 degrees on Mars meridian = (pi/2) * 3389.5 km ~ 5324.28 km
        distance = haversine_km(0.0, 0.0, 90.0, 0.0)
        expected = (math.pi / 2.0) * 3389.5
        self.assertAlmostEqual(distance, expected, delta=0.5)

if __name__ == "__main__":
    unittest.main()
