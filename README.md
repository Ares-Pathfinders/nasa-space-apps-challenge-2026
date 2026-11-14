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

1. **📐 Topography & High-Resolution Elevation (DTM)**
   - Sub-meter digital elevation models from MRO HiRISE and HRSC (Mars Express).
   - Slope gradient maps that identify impassable cliffs and suit tipping hazards.
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

Astronaut safety is the primary operational constraint. **ARES-Nav** implements a multi-objective cost-surface pathfinding algorithm (weighted $A^*$ / Dijkstra with safety penalty functions):

$$\text{Cost}(u \to v) = d(u, v) \cdot \Big[ 1 + w_{\text{slope}} \cdot \mathcal{S}(v) + w_{\text{roughness}} \cdot \mathcal{R}(v) + w_{\text{radiation}} \cdot \Phi(v) \Big]$$

- **Slope Thresholds:** Flagging surfaces $> 15^\circ$ as hazardous for spacesuits and $> 25^\circ$ as impassable.
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
- Python 3.10+
- Git

### Setup & Run
```bash
# Clone the repository
git clone https://github.com/Guillermo-GJ/nasa-space-apps-challenge-2026.git
cd nasa-space-apps-challenge-2026

# Backend installation
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend installation
cd ../frontend
npm install
npm run dev
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
All Martian satellite imagery and scientific datasets are courtesy of NASA, JPL-Caltech, and USGS.
