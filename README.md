# 🚀 ARES-Nav: Tactical Martian Surface Navigator & Survival Guide

[![NASA Space Apps Challenge 2026](https://img.shields.io/badge/NASA%20Space%20Apps-2026-blue.svg)](https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/)
[![Challenge](https://img.shields.io/badge/Challenge-Interplanetary%20Survival%20Guide%3A%20Martian%20Map-red.svg)](https://www.spaceappschallenge.org/2026/challenges/interplanetary-survival-guide-martian-map/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Hyperlocalized, multi-layered tactical navigation and hazard-aware EVA (Extravehicular Activity) route planning for the first human explorers on Mars.**

---

## 📌 Table of Contents
- [Project Overview](#-project-overview)
- [The Challenge](#-the-challenge)
- [Target Exploration Site](#-target-exploration-site)
- [Key Features & Data Layers](#-key-features--data-layers)
- [Safety & Autonomous Pathfinding](#-safety--autonomous-pathfinding)
- [Visualization & Interface](#-visualization--interface)
- [Data Sources & NASA Missions](#-data-sources--nasa-missions)
- [System Architecture](#-system-architecture)
- [Team Members](#-team-members)
- [Getting Started](#-getting-started)
- [License](#-license)

---

## 🌌 Project Overview

When the first astronauts take their historic steps on Mars, they will face unprecedented environmental extremes: steep crater slopes, treacherous boulder fields, ionizing space radiation, severe temperature swings, and thin atmosphere. Unlike robotic rovers that can pause and wait for Earth commands over a 20-minute signal delay, human crews require real-time, hyperlocalized tactical intelligence.

Existing planetary visualization tools (such as NASA/JPL Mars Trek or USGS Planetary Geologic Mapping) are engineered for regional or global orbital surveys. **ARES-Nav** bridges the gap between global orbital telemetry and boots-on-the-ground human exploration. It provides a mission control tactical console and astronaut visor/tablet interface that layers multi-mission scientific datasets into a human-scale, route-planning and survival engine.

---

## 🎯 The Challenge

- **Event:** [2026 NASA Space Apps Challenge](https://www.spaceappschallenge.org/)
- **Category:** Human Exploration / Mars / Space Exploration / Software
- **Challenge Title:** *Interplanetary Survival Guide: Martian Map*
- **Objective:** Create a layered, integrated view of a location or route on the Martian surface that pulls together data from multiple NASA science missions, enabling human astronauts to plan and conduct safe, high-yield scientific Marswalks.

---

## 📍 Target Exploration Site: Jezero Crater & Mount Sharp Corridors

To maximize data density and scientific impact, **ARES-Nav** models high-priority human exploration corridors:
1. **Jezero Crater Delta (`18.38° N, 77.58° E`)**: Ancient river-lake system explored by the *Perseverance* rover, offering high astrobiological value (clay, carbonate deposits) along with rugged delta scarps.
2. **Gale Crater & Mount Sharp (`4.589° S, 137.441° E`)**: Stratified sedimentary layers and boxwork formations studied by the *Curiosity* rover, presenting challenging slope gradients and rich mineralogical transitions.

---

## 🛰️ Key Features & Data Layers

**ARES-Nav** synthesizes at least **five distinct scientific layers** into a single contextual 3D coordinate system:

1. **📐 Topography & Terrain Hazards**
   - Procedural elevation grids support demonstration routes; they are not measured 1 m DEMs.
   - Jezero slope cells shown on the 2D map and used for route calculations come from the supplied HiRISE slope raster at approximately 20.2 m/pixel. The raster is resampled to the displayed route grid; the original raster is not rendered directly.
2. **🔬 Spectral & Mineralogical Stratigraphy**
   - Compact Reconnaissance Imaging Spectrometer for Mars (CRISM) and rover instruments (SuperCam, Mastcam-Z).
   - Highlighting scientific targets of interest: hydrated sulfates, clay minerals, and silica veins.
3. **🌡️ Thermal & Surface Roughness**
   - Thermal Emission Imaging System (THEMIS) thermal inertia maps.
   - Distinguishes solid bedrock vs. soft, fine-grained drift sand (rover wheel trap / astronaut foot sinkage hazard).
4. **☢️ Space Weather & Radiation Environment**
   - Surface dose-rate telemetry derived from Mars Science Laboratory (MSL) Radiation Assessment Detector (RAD).
   - Real-time exposure budgeting during solar particle events (SPE) and galactic cosmic ray (GCR) background.
5. **💨 Atmospheric & Meteorological Telemetry**
   - Temperature, pressure, wind velocity, and dust optical depth ($\tau$) from Perseverance MEDA and Curiosity REMS.
   - Storm detection and visibility degradation alerts.
6. **📷 Point-of-View Imagery & Ground Truth**
   - Rover Navcam/Mastcam panoramic ground captures aligned with satellite orthophotos, preparing astronauts with visual landmarks before arrival.

---

## 🛡️ Safety & Autonomous Pathfinding

Astronaut safety is the primary operational constraint. **ARES-Nav** builds a directed graph from the selected terrain grid and uses A* to minimize estimated traversal time. Steep cells and transitions above the configured slope limit are excluded; uphill transitions cost more time than downhill transitions, and slopes increase the traversal cost:

$$t(u \to v) = \frac{d(u,v)\,[1+3.5(s/s_{\max})^2]}{0.8\,e^{-2|g|- \max(g,0)}} \quad \text{where } g=\frac{\Delta h}{d(u,v)} \text{ and } s \text{ is the edge slope}$$

- **Slope Thresholds:** Flagging surfaces $> 15^\circ$ as hazardous for spacesuits and $> 25^\circ$ as impassable.
- **Interactive route planning:** Select an origin and destination on the Gale or Jezero tactical map. A* returns the fastest estimated safe route, while the interface reports its ground distance, slope, and estimated EVA time. “Start navigation” zooms to the route and identifies the next waypoint; live position tracking is not available without astronaut/rover telemetry.
- **Diagonal safety:** The cell graph disallows diagonal transitions between two blocked orthogonal cells, preventing routes from cutting through the corner of a mapped hazard.
- **Slope data and limitations:** Jezero's 2D map and route calculations use the supplied HiRISE slope raster (`J03_045994_1986_J03_046060_1986_20m_slope_20m.tif`, approximately 20.2 m pixels); each route-grid cell uses the maximum measured slope in its footprint, and cells without full raster coverage are treated as impassable. The original raster is resampled into map cells rather than rendered directly. Jezero elevation changes still come from the procedural demonstration terrain, so estimated travel times and elevation gains are not measured mission data. The coarse route grid can miss hazards smaller than its cells, and this is not a mission-certified safety assessment.
- **Life Support & Consumables Budgeting:** Real-time calculation of $O_2$ consumption, battery levels, cooling water, and a strict 50% "point-of-no-return" safe abort buffer.
- **Science Maximization Factor:** Route optimization that balances hazard minimization with high-value scientific sampling points.

---

## 🖥️ Visualization & Interface

- **Habitat / Base Station Tactical Map:** Interactive 3D terrain viewer with togglable data layers, heatmaps, elevation cross-sections, and waypoint markers.
- **Astronaut Heads-Up Display (HUD) / Mobile Tablet View:** High-contrast, glanceable interface showing:
  - Bearing, compass heading, and distance to next science waypoint.
  - Active hazard warnings (slope alert, radiation spike, high thermal inertia).
  - Life support countdown (safe return window).
  - Landmark comparison view (satellite vs. rover ground perspective).

---

## 📚 Data Sources & NASA Missions

- **Mars Reconnaissance Orbiter (MRO):** HiRISE (High Resolution Imaging Science Experiment) & CRISM.
- **Mars Science Laboratory (MSL Curiosity):** RAD (Radiation Assessment Detector), REMS (Rover Environmental Monitoring Station).
- **Mars 2020 (Perseverance):** MEDA (Mars Environmental Dynamics Analyzer), Mastcam-Z, SuperCam.
- **Mars Global Surveyor (MGS):** MOLA (Mars Orbiter Laser Altimeter).
- **NASA Planetary Data System (PDS) & JPL Mars Trek:** Open-access science cartography and orbital products.
- **Tactical map backgrounds:** [NASA MSL location-map tiles](https://mars.nasa.gov/maps/location/api/configure/get?mission=MSL) and [NASA Mars 2020 location-map tiles](https://mars.nasa.gov/maps/location/api/configure/get?mission=M20); HiRISE imagery is overlaid on regional basemaps where available.

---

## 🏗️ System Architecture

```text
├── data/                  # NASA PDS datasets, DTM tiles, and geo-referenced layers
├── backend/               # Python API & data processing pipeline
│   ├── terrain/           # Elevation parsing, slope calculation & cost surface generation
│   ├── pathfinding/       # Multi-criteria A* hazard routing engine
│   └── telemetry/         # Atmospheric & radiation simulation models
├── frontend/              # Interactive 3D Web UI / Tactical Console
│   ├── components/        # Map controls, layer toggles, HUD overlay
│   ├── shaders/           # 3D terrain rendering & topographic shaders
│   └── views/             # Tactical Map View & Astronaut Visor HUD
└── docs/                  # Project documentation, scientific rationale & user guide
```

---

## 👥 Team Members

We are a multidisciplinary team combining mathematics, computer science, and telecommunications engineering:

| Name | Role / Area | Degree & Academic Year |
| :--- | :--- | :--- |
| **Guillermo García** | Team Lead & Algorithms / Full-Stack | 3rd Year, Double Degree in Mathematics & Computer Science |
| **Francisco Lillo** | Mathematical Modeling & Pathfinding | 3rd Year, Double Degree in Mathematics & Computer Science |
| **Sergio Rodríguez** | Data Science & Spatial Analytics | 3rd Year, Double Degree in Mathematics & Computer Science |
| **María Hidalgo** | Telecommunications & Network Telemetry | 1st Year, Telecommunications Engineering |
| **María Ruiz** | Systems Engineering & UI/UX Design | 1st Year, Telecommunications Engineering |
| **Mario Romero** | Software Development & Integration | 1st Year, Computer Science |

---

## ⚡ Getting Started

### Prerequisites
- Node.js (v18+)
- Python 3.11+
- Git

### Setup & Run
```bash
# Clone the repository
git clone https://github.com/Guillermo-GJ/nasa-space-apps-challenge-2026.git
cd nasa-space-apps-challenge-2026

# Backend installation and API
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (run in a second terminal)
cd ../frontend
npm install
npm run dev
```

The API is available at `http://localhost:8000` and its interactive documentation at
`http://localhost:8000/docs`. The Vite application is available at
`http://localhost:5173`.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
All Martian satellite imagery and scientific datasets are courtesy of NASA, JPL-Caltech, and USGS.
