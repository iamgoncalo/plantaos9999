# PlantaOS — MVP Digital Twin CFT/HORSE

## Identity
PlantaOS is the operating system for physical spaces. This MVP is a Digital Twin for the HORSE/Renault CFT training building in Aveiro (2 floors, ~1000 users). The system observes, learns baselines, detects deviations, and generates actionable insights. Demo deadline: end of March 2026. Go/no-go decision: April 2026.

## Architecture
```
Synthetic Data → Pipeline → Spatial Kernel → Digital Twin UI
                              ↓
                    Baselines + Anomaly Detection
                              ↓
                    Claude API → Natural Language Insights
```

## Stack (LOCKED — do not change)
- **Python 3.12+** — everything is Python
- **Dash 2.18+** with **Dash Mantine Components 0.14+** — UI framework
- **Plotly 5.24+** — all charts and 2D floorplan rendering
- **Three.js r128** (embedded via Dash html.Iframe) — 3D building view only
- **Pandas + NumPy** — data processing
- **SciPy + scikit-learn** — baselines, anomaly detection, correlation
- **Anthropic SDK** — Claude API for natural language insights
- **Pydantic 2.x** — data models and validation
- **Loguru** — logging

## Design System (MANDATORY — Apple-inspired light UI)
- **Background:** `#FAFAFA` (app), `#FFFFFF` (cards)
- **Text:** `#1D1D1F` (primary), `#6E6E73` (secondary), `#86868B` (tertiary)
- **Accent:** `#0071E3` (Planta blue), `#34C759` (healthy), `#FF9500` (warning), `#FF3B30` (critical)
- **Surfaces:** White cards with `border-radius: 16px`, `box-shadow: 0 2px 12px rgba(0,0,0,0.08)`
- **Typography:** Inter (primary), JetBrains Mono (data/numbers), weight 400/500/600
- **Spacing:** 8px grid. Padding 24px cards, 16px between elements
- **Charts:** Clean, no gridlines by default, thin lines, large readable labels
- **Animation:** Smooth transitions 300ms ease, no jarring updates
- **NEVER:** Dark mode, neon colors, cluttered layouts, tiny fonts, 3D chart effects

## Project Structure
```
plantaos-mvp/
├── app.py                          # Entry: Dash app init + server
├── config/
│   ├── settings.py                 # Ports, debug, API keys
│   ├── theme.py                    # Design tokens (colors, fonts, spacing)
│   ├── building.py                 # CFT zone definitions (rooms, areas, capacities)
│   └── thresholds.py               # Comfort bands, energy limits, safety rules
├── core/
│   ├── spatial_kernel.py           # Zone state aggregation + path computation
│   ├── baseline.py                 # Rolling statistical baselines (mean, σ, percentiles)
│   ├── anomaly.py                  # Z-score + isolation forest anomaly detection
│   ├── correlation.py              # Energy↔occupancy, comfort↔weather correlation
│   ├── freedom_index.py            # Per-zone health score (0-100)
│   └── insights.py                 # Claude API: anomaly context → natural language
├── data/
│   ├── synthetic/
│   │   ├── generator.py            # Master generator (orchestrates all profiles)
│   │   ├── energy.py               # kWh profiles (HVAC, lighting, equipment)
│   │   ├── comfort.py              # Temp, humidity, CO2, lux by zone
│   │   ├── occupancy.py            # Presence patterns (shifts, meetings, breaks)
│   │   └── events.py               # Weather, shift schedules, holidays
│   ├── pipeline.py                 # Ingest → clean → normalize → store
│   └── store.py                    # In-memory DataStore (dict of DataFrames)
├── views/
│   ├── layout.py                   # App shell (sidebar + header + content area)
│   ├── components/
│   │   ├── sidebar.py              # Left nav with icons
│   │   ├── header.py               # Building status bar
│   │   ├── kpi_card.py             # Single KPI with trend arrow
│   │   ├── zone_panel.py           # Zone detail overlay
│   │   ├── alert_feed.py           # Scrolling alert list
│   │   └── insight_card.py         # AI insight with explanation
│   ├── pages/
│   │   ├── overview.py             # Floorplan + top KPIs + alerts
│   │   ├── energy.py               # Energy breakdown, baselines, anomalies
│   │   ├── comfort.py              # Thermal/air quality heatmaps
│   │   ├── occupancy.py            # Flow patterns, utilization rates
│   │   ├── insights_page.py        # AI insight feed + chat
│   │   └── building_3d.py          # 3D interactive view
│   └── floorplan/
│       ├── renderer_2d.py          # Plotly SVG floorplan with zone overlays
│       ├── renderer_3d.py          # Three.js HTML generator for 3D view
│       └── zones_geometry.py       # Zone polygons for both floors
├── assets/
│   └── style.css                   # Global Dash CSS overrides
├── utils/
│   ├── colors.py                   # Color interpolation, zone→color mapping
│   ├── formatters.py               # Numbers, dates, units
│   └── time_utils.py               # Timezone, shift detection, period helpers
├── tests/
│   ├── test_generator.py
│   ├── test_baseline.py
│   └── test_anomaly.py
└── requirements.txt
```

## CFT Building Definition (2 floors)
### Ground Floor (Piso 0)
- Sala Multiusos (93.10 m²) — cap 60
- Biblioteca/Espólio HORSE (46.50 m²) — cap 20
- Zona Social / Copa (35.10 m²) — cap 15
- Hall (41.50 m²) — cap 30
- Circulação (50.30 m²)
- Aula/Câmara (small room)
- Salas de formação × 3 (~31-51 m² each) — cap 20-30 each
- Sala Reunião (25.10 m²) — cap 12
- Sala Informática (41.70 m²) — cap 30 (computers) + 27 (auditorium)
- Arrumos (storage)
- Recepção
- WCs

### First Floor (Piso 1)
- Arquivo (57.50 m²)
- Sala grande (42.10 m²) — cap 25
- Sala pequena (25.00 m²) — cap 15
- Salas × 3 (~31-51 m² each)
- Circulação (46.70 m²)
- Produção/Exibição Armazém (25.80 m²)
- Sala Dojo Segurança (110.30 m²) — cap 50
- WCs + monitor areas

## Code Conventions
- **Type hints** on every function signature
- **Pydantic models** for all data structures (never raw dicts)
- **Docstrings** on all public functions (Google style, concise)
- **No classes** for pages/components — use plain functions returning Dash components
- **Callbacks** in separate files under `views/callbacks/`, registered in `app.py`
- **Constants** in UPPER_SNAKE_CASE in config files
- **f-strings** for formatting, never .format() or %
- Import order: stdlib → third-party → local (ruff handles this)
- Max line length: 100 chars
- Use `loguru.logger` not `print()` for any debug/info output

## Key Commands
```bash
# Run the app
python app.py

# Run tests
pytest tests/ -v

# Format
ruff check --fix . && ruff format .

# Generate fresh synthetic data
python -m data.synthetic.generator

# Check all imports resolve
python -c "from app import app; print('OK')"
```

## Build Order (follow this sequence)
1. `config/` — theme, building zones, thresholds
2. `data/synthetic/` — generator that produces realistic DataFrames
3. `data/pipeline.py` + `data/store.py` — ingestion and storage
4. `core/` — baseline, anomaly, correlation, freedom_index, spatial_kernel
5. `views/components/` — kpi_card, sidebar, header (design system)
6. `views/floorplan/renderer_2d.py` — 2D floorplan with zone overlays
7. `views/pages/overview.py` — main dashboard page
8. `views/pages/energy.py`, `comfort.py`, `occupancy.py` — detail pages
9. `core/insights.py` — Claude API integration
10. `views/pages/insights_page.py` — AI insights feed
11. `views/floorplan/renderer_3d.py` — 3D Three.js view
12. `views/pages/building_3d.py` — 3D page
13. Polish, test, demo script

## Synthetic Data Rules
- Generate 30 days of history + real-time simulation
- 15-minute intervals for energy, 5-minute for comfort, event-driven for occupancy
- Realistic Portuguese patterns: shifts 6h-14h / 14h-22h, lunch 12h-13h
- Weather: March in Aveiro (8-18°C, occasional rain, humidity 60-85%)
- Energy: HVAC 60%, lighting 20%, equipment 15%, other 5%
- Anomalies: inject 3-5 realistic anomalies per week (HVAC stuck, window left open, equipment spike)
- Weekends: minimal occupancy, base energy load only

## Anti-Patterns (NEVER DO)
- No dark backgrounds or neon accents
- No `dcc.Interval` faster than 5 seconds (performance)
- No inline styles — use CSS classes or Mantine props
- No global mutable state — use `dcc.Store` or the DataStore class
- No placeholder "Lorem ipsum" — every text must be realistic Portuguese/English
- No generic chart titles — every chart must have a specific, informative title
- No loading spinners without content — show skeleton placeholders instead
