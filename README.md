# PlantaOS — Digital Twin MVP

The operating system for physical spaces. This MVP is a Digital Twin for the HORSE/Renault CFT training building in Aveiro, Portugal (2 floors, ~1000 users).

PlantaOS observes building conditions, learns baselines, detects deviations, and generates actionable AI insights.

## Architecture

```
Synthetic Data → Pipeline → Spatial Kernel → Digital Twin UI
                              ↓
                    Baselines + Anomaly Detection
                              ↓
                    Claude API → Natural Language Insights
```

## Quick Start

```bash
# Requirements
Python 3.12+

# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Open in browser
http://localhost:8050
```

## Demo Mode

Run with accelerated time, frequent anomalies, and pre-seeded AI insights:

```bash
DEMO_MODE=true python app.py
```

Demo mode features:
- 5-second refresh interval (vs 30s normal)
- Random anomaly injection (2-3 zones per tick)
- 3 pre-seeded AI insights on first load
- Time acceleration: 1 real second = 5 simulated minutes

## Pages

| Page | Description |
|------|-------------|
| **Overview** | Floorplan + top KPIs + alerts |
| **Energy** | Consumption breakdown, baselines, anomalies |
| **Comfort** | Temperature, humidity, CO2, illuminance |
| **Occupancy** | Flow patterns, utilization rates |
| **Insights** | AI insight feed + chat with Claude |
| **3D View** | Interactive Three.js building model |

## Tech Stack

- **Dash 2.18+** with Dash Mantine Components — UI framework
- **Plotly 5.24+** — Charts and 2D floorplan
- **Three.js r128** — 3D building view (embedded iframe)
- **Pandas + NumPy** — Data processing
- **SciPy + scikit-learn** — Baselines, anomaly detection
- **Anthropic SDK** — Claude API for natural language insights
- **Pydantic 2.x** — Data models and validation

## Project Structure

```
plantaos-mvp/
├── app.py                  # Entry point
├── config/                 # Settings, theme, building zones, thresholds
├── core/                   # Spatial kernel, baselines, anomaly detection, insights
├── data/                   # Synthetic data generators, pipeline, store
├── views/
│   ├── layout.py           # App shell (sidebar + header + content)
│   ├── components/         # KPI cards, sidebar, header, alerts, insights
│   ├── pages/              # Overview, energy, comfort, occupancy, insights, 3D
│   ├── callbacks/          # All Dash callback registrations
│   └── floorplan/          # 2D renderer, 3D renderer, zone geometry
├── assets/style.css        # Global CSS
├── utils/                  # Colors, formatters, time utilities
└── tests/                  # Test suite
```

## Configuration

Environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_HOST` | `0.0.0.0` | Bind address |
| `APP_PORT` | `8050` | HTTP port |
| `DEBUG` | `true` | Enable hot-reload |
| `DATA_REFRESH_INTERVAL` | `30` | Dashboard refresh (seconds) |
| `ANTHROPIC_API_KEY` | — | Claude API key for AI insights |
| `DEMO_MODE` | `false` | Enable demo mode |
| `DEMO_TIME_FACTOR` | `5` | Time acceleration factor |

## Development

```bash
# Format and lint
ruff check --fix . && ruff format .

# Run tests
pytest tests/ -v

# Verify all imports
python -c "from app import app; print('OK')"
```
