import httpx
import logging
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.models.rover import RoverPhoto, RoverCamera, RoverInfo, RoverPhotosResponse

logger = logging.getLogger(__name__)

# Curated fallback library with genuine NASA Mars imagery in case of API rate limits or network issues
CURATED_FALLBACK_PHOTOS: Dict[str, List[Dict[str, Any]]] = {
    "curiosity": [
        {
            "id": 1026858,
            "sol": 1000,
            "camera": {"id": 20, "name": "MAST", "rover_id": 5, "full_name": "Mast Camera"},
            "img_src": "https://mars.nasa.gov/msl-raw-images/msss/01000/mcam/1000MR0044631300503690E01_DXXX.jpg",
            "earth_date": "2015-05-31",
            "rover": {"id": 5, "name": "Curiosity", "landing_date": "2012-08-06", "launch_date": "2011-11-26", "status": "active"}
        },
        {
            "id": 1026859,
            "sol": 1000,
            "camera": {"id": 20, "name": "MAST", "rover_id": 5, "full_name": "Mast Camera"},
            "img_src": "https://mars.nasa.gov/msl-raw-images/msss/01000/mcam/1000ML0044631290305226E01_DXXX.jpg",
            "earth_date": "2015-05-31",
            "rover": {"id": 5, "name": "Curiosity", "landing_date": "2012-08-06", "launch_date": "2011-11-26", "status": "active"}
        },
        {
            "id": 1026860,
            "sol": 1000,
            "camera": {"id": 22, "name": "NAV_LEFT_B", "rover_id": 5, "full_name": "Navigation Camera"},
            "img_src": "https://mars.nasa.gov/msl-raw-images/proj/msl/redops/ods/surface/sol/01000/opgs/edr/ncam/NLB_486377759EDR_F0481570NCAM00323M_.JPG",
            "earth_date": "2015-05-31",
            "rover": {"id": 5, "name": "Curiosity", "landing_date": "2012-08-06", "launch_date": "2011-11-26", "status": "active"}
        }
    ],
    "perseverance": [
        {
            "id": 104231,
            "sol": 100,
            "camera": {"id": 35, "name": "NAVCAM_LEFT", "rover_id": 8, "full_name": "Navigation Camera - Left"},
            "img_src": "https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00100/ids/edr/browse/NLF_0100_0675713429_636ECM_N0050000AUT_04096_00_285J01.png",
            "earth_date": "2021-06-01",
            "rover": {"id": 8, "name": "Perseverance", "landing_date": "2021-02-18", "launch_date": "2020-07-30", "status": "active"}
        },
        {
            "id": 104232,
            "sol": 100,
            "camera": {"id": 36, "name": "MCZ_RIGHT", "rover_id": 8, "full_name": "Mastcam-Z Right"},
            "img_src": "https://mars.nasa.gov/mars2020-raw-images/pub/ods/surface/sol/00100/ids/edr/browse/ZRF_0100_0675713292_644ECM_N0050000AUT_04096_00_285J01.png",
            "earth_date": "2021-06-01",
            "rover": {"id": 8, "name": "Perseverance", "landing_date": "2021-02-18", "launch_date": "2020-07-30", "status": "active"}
        }
    ]
}

class NasaService:
    @staticmethod
    async def get_rover_photos(
        rover: str = "curiosity",
        sol: int = 1000,
        camera: Optional[str] = None,
        page: int = 1
    ) -> RoverPhotosResponse:
        rover_clean = rover.strip().lower()
        url = f"{settings.NASA_API_BASE_URL}/mars-photos/api/v1/rovers/{rover_clean}/photos"
        params: Dict[str, Any] = {
            "sol": sol,
            "api_key": settings.NASA_API_KEY,
            "page": page
        }
        if camera:
            params["camera"] = camera.upper()

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    photos_raw = data.get("photos", [])
                    
                    if photos_raw:
                        photos = [RoverPhoto(**p) for p in photos_raw]
                        return RoverPhotosResponse(
                            rover=rover_clean,
                            sol=sol,
                            camera=camera,
                            total_photos=len(photos),
                            source="nasa_api",
                            photos=photos
                        )
                    logger.info(f"NASA API returned 0 photos for rover={rover_clean}, sol={sol}. Falling back to curated data.")
                else:
                    logger.warning(f"NASA API returned status {response.status_code}: {response.text}")

        except Exception as e:
            logger.error(f"Error fetching from NASA API: {str(e)}. Utilizing curated offline telemetry fallback.")

        # Fallback to curated cache
        cached_list = CURATED_FALLBACK_PHOTOS.get(rover_clean, CURATED_FALLBACK_PHOTOS["curiosity"])
        filtered_photos = [
            RoverPhoto(**p) for p in cached_list
            if not camera or p["camera"]["name"].upper() == camera.upper()
        ]
        if not filtered_photos and cached_list:
            filtered_photos = [RoverPhoto(**p) for p in cached_list]

        return RoverPhotosResponse(
            rover=rover_clean,
            sol=sol,
            camera=camera,
            total_photos=len(filtered_photos),
            source="curated_fallback",
            photos=filtered_photos
        )

nasa_service = NasaService()
