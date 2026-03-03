# PlantaOS Manual QA Walkthrough

## Pre-requisites
- Run `python app.py` and open http://localhost:8050
- Ensure data pipeline completes (check console for "Data pipeline complete")
- Use a modern browser (Chrome, Firefox, Safari)

## Page Load Tests

1. **Overview** (`/`) — KPI cards (Total Energy, Operating Cost, Occupancy, Active Alerts, Zone Performance), 2D floorplan with zone overlays, alert feed, zone detail panel on click
2. **Energy** (`/energy`) — Energy breakdown charts, HVAC/lighting/equipment split, time series with baselines
3. **Comfort** (`/comfort`) — Temperature, humidity, CO2, illuminance heatmaps per zone
4. **Occupancy** (`/occupancy`) — Occupancy patterns, utilization rates, flow data by zone
5. **Insights** (`/insights`) — AI insight feed with natural language explanations
6. **3D Building** (`/building_3d`) — Three.js 3D interactive building view in iframe
7. **3D Walk** (`/building_3d_walk`) — First-person 3D walkthrough mode
8. **2D Map** (`/view_2d`) — Interactive 2D exploration with avatar movement
9. **4D Explorer** (`/view_4d`) — Time-lapse 4D data visualization
10. **Sensor Coverage** (`/view_sensors`) — Sensor placement and coverage overlay
11. **Emergency Mode** (`/view_emergency`) — Emergency evacuation view with exits
12. **Data Explorer** (`/view_data`) — Raw data table browser with filters
13. **Flow** (`/view_flow`) — People flow visualization between zones
14. **Heatmap** (`/view_heatmap`) — Metric heatmap overlay on floorplan
15. **Simulation** (`/simulation`) — What-if scenario runner
16. **Reports** (`/reports`) — Report generation with charts and PDF export
17. **Sensors** (`/sensors`) — Device inventory table, health panel, KPI strip
18. **Smart Booking** (`/booking`) — Room booking with conflict detection
19. **Settings** (`/admin`) — Pricing, API keys, data regeneration, audit log
20. **Deployment** (`/deployment`) — Deployment pipeline status

## Interactive Feature Tests

### Navigation
1. **Sidebar** — Click each nav item; verify page loads and sidebar item highlights
2. **View Submenu** — Click "View" parent item; submenu expands showing sub-pages
3. **Mobile Sidebar** — Resize browser below 768px; toggle hamburger button; overlay appears
4. **URL Routing** — Type `/energy` directly in address bar; correct page loads
5. **404 Page** — Navigate to `/nonexistent`; see styled 404 with "Go to Overview" link

### Tenant Switch
1. Click tenant dropdown in header
2. Select a different tenant (e.g., "FAL A320")
3. Confirmation dialog appears: "Switching tenant will change all building data..."
4. Click OK — KPIs update with scaled values, header building name changes
5. Click Cancel on another switch — selector reverts to current tenant

### Search
1. Click the search input in the header
2. Type "Sala" — zone results appear with green "Zone" badges
3. Type "Energy" — page result appears with blue "Page" badge
4. Click a result — navigates to the correct page/zone
5. Type fewer than 2 characters — dropdown hides

### Notifications
1. Click the bell icon in the header
2. Dropdown appears showing recent alerts with severity dots (red/orange)
3. Click an alert — navigates to overview page
4. If no alerts, "No active alerts" with green checkmark shown
5. Click bell again — dropdown closes

### Floor Tabs (Overview)
1. Click "Piso 0" tab — ground floor floorplan renders
2. Click "Piso 1" tab — first floor floorplan renders
3. Active tab has highlighted styling

### Zone Detail (Overview)
1. Click a zone on the floorplan
2. Zone detail panel appears with temperature, humidity, CO2, occupancy, freedom index
3. Click a different zone — panel updates

### 2D Explore
1. Navigate to `/view_2d`
2. Arrow keys move avatar on floorplan
3. Avatar cannot pass through walls (collision detection)
4. Zone info updates as avatar enters different zones

### 3D Building
1. Navigate to `/building_3d`
2. Three.js scene loads in iframe
3. Mouse drag rotates view, scroll zooms
4. Zones colored by selected metric (freedom index default)
5. Floor visibility toggles work

### Booking
1. Navigate to `/booking`
2. Select a zone, date, and time range
3. Click "Book" — booking appears in the table
4. Try booking same slot — conflict detection triggers
5. Calendar view shows booked slots

### Reports
1. Navigate to `/reports`
2. Charts load with building data
3. Click PDF export — file downloads

### Sensors
1. Navigate to `/sensors`
2. Device inventory table shows 12 sensors with ID, name, type, protocol, zone, status, battery, last seen, firmware
3. KPI strip shows Total/Online/Warning/Critical counts
4. Health panel shows devices needing attention
5. Click "Add Device" — add device workflow triggers
6. Remove device — confirmation dialog appears

### Admin Settings
1. Navigate to `/admin`
2. Change energy cost value and click "Save Settings"
3. Confirmation dialog appears — confirm — "Settings saved successfully" shown
4. Click "Regenerate Data" — confirmation dialog — data regenerates
5. Click "Clear Bookings" — confirmation dialog — bookings cleared
6. Audit log shows recent actions
7. Click "Clear Audit Log" — confirmation dialog — log cleared

### Language Selector
1. Click language dropdown in header
2. Select a language — lang-store updates

## Expected Failures
- None. All features should work without errors.
- Console should show no JavaScript errors.
- All pages should render within 3 seconds.
- No blank screens or unhandled exceptions.
