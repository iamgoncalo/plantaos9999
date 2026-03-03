# PlantaOS MVP -- Audit Findings

**Date:** 2026-03-03
**Auditor:** Automated code audit
**Scope:** Full codebase review of callback architecture, layout stores,
chart resilience, sensor wiring, and admin integrity.

---

## 1. Findings

### 1.1 Monolithic Callback File (HIGH)

**File:** `views/callbacks/__init__.py`
**Issue:** Single file contained ~1027 lines mixing routing, building state,
navigation, search, notifications, and language callbacks. This made the file
difficult to maintain and increased merge conflict risk.

**Fix:** Extracted building-state callbacks into `views/callbacks/state_cb.py`
and navigation callbacks into `views/callbacks/nav_cb.py`. The `__init__.py`
now contains only routing logic, imports, and the `register_callbacks()` entry
point (~230 lines).

### 1.2 Missing Layout Stores (MEDIUM)

**File:** `views/layout.py`
**Issue:** Several `dcc.Store` components referenced by callbacks were not
declared in the layout: `notifications-store`, `active-floor-store`,
`auth-store`. The `bookings-store` used `memory` storage, losing data on
page reload.

**Fix:**
- Added `notifications-store` (session)
- Added `active-floor-store` (memory, default 0)
- Added `auth-store` (session)
- Changed `bookings-store` from `memory` to `session`

### 1.3 Chart Callbacks Lack Data Guards (MEDIUM)

**File:** `views/callbacks/reports_cb.py`
**Issue:** Chart callbacks did not check for required column existence before
accessing DataFrame columns. Missing columns would cause unhandled KeyError
exceptions. Error fallback returned generic English messages.

**Fix:**
- Added `if "column_name" not in df.columns` guards for `timestamp` and
  `total_kwh` in trend line and savings chart callbacks
- Wrapped zone ranking bleed computation in try/except
- Changed error fallback messages to `"Aguardando dados..."` for consistency

### 1.4 Dead Sensor Action Callbacks (HIGH)

**File:** `views/callbacks/sensors_cb.py`
**Issue:** The sensors page UI had Add, Commission, and Remove buttons but
no corresponding callbacks were registered. Clicking these buttons had no
effect.

**Fix:** Added three new callback functions:
- `_register_add_device`: Appends a new sensor to the store
- `_register_commission_device`: Sets device status to online
- `_register_remove_device`: Removes a device from the store

### 1.5 No SBOM or Smoke Tests (LOW)

**Issue:** No automated way to inventory dependencies or verify basic
application health after deployments.

**Fix:**
- Created `scripts/audit_sbom.py` -- generates JSON SBOM with packages,
  local modules, JS assets, and Python runtime info
- Created `scripts/smoke_test.py` -- imports core modules, runs key
  functions, asserts no exceptions

### 1.6 No Admin Integrity View (LOW)

**File:** `views/pages/admin.py`, `views/callbacks/admin_cb.py`
**Issue:** Admin page had no visibility into runtime stack versions,
dependency counts, or architecture metadata.

**Fix:** Added an Architecture and Integrity card to the admin page with
a callback that populates runtime Python version, Dash version, package
count, module count, and platform info.

---

## 2. Risk Assessment

| Finding | Severity | Status |
|---------|----------|--------|
| Monolithic callback file | HIGH | Fixed |
| Missing layout stores | MEDIUM | Fixed |
| Chart data guards | MEDIUM | Fixed |
| Dead sensor callbacks | HIGH | Fixed |
| No SBOM/smoke tests | LOW | Fixed |
| No admin integrity view | LOW | Fixed |

---

## 3. Recommendations

1. **Callback file size policy:** Keep individual callback modules under
   300 lines. Extract when approaching this limit.
2. **Store declaration audit:** Run periodic checks that all `dcc.Store`
   IDs referenced in callbacks have matching declarations in `layout.py`.
3. **Chart defensive coding:** Always check `df is None or df.empty` and
   verify required columns before accessing data.
4. **CI smoke tests:** Add `scripts/smoke_test.py` to the CI pipeline to
   catch import and runtime errors early.
5. **SBOM in releases:** Generate `sbom.json` as part of each release for
   supply chain visibility.
