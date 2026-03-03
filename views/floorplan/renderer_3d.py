"""Three.js HTML generator for 3D interactive building view.

Generates a self-contained HTML page with an inline Three.js r128 scene
that renders the CFT building in 3D with interactive zone selection,
metric overlays, and OrbitControls. Embedded via Dash html.Iframe srcdoc.
"""

from __future__ import annotations

import json
from typing import Any

from config.building import get_zone_by_id
from config.theme import (
    BORDER_DEFAULT,
    STATUS_CRITICAL,
    STATUS_HEALTHY,
    STATUS_WARNING,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from utils.colors import interpolate_color, zone_health_to_color
from views.floorplan.zones_geometry import (
    FLOOR_0_ZONES,
    FLOOR_1_ZONES,
    FLOOR_HEIGHT_M,
    FLOOR_WIDTH_M,
)

# Abbreviated names for compact 3D labels (mirrors renderer_2d.py)
_NAME_SHORT: dict[str, str] = {
    "Sala Multiusos": "Multiusos",
    "Biblioteca / Espolio HORSE": "Biblioteca",
    "Zona Social / Copa": "Copa",
    "Sala Formacao 1": "Form. 1",
    "Sala Formacao 2": "Form. 2",
    "Sala Formacao 3": "Form. 3",
    "Sala Reuniao": "Reuniao",
    "Sala Informatica": "Informatica",
    "Exibicao Armazem": "Armazem",
    "Sala Dojo Seguranca": "Dojo",
    "Sala Grande": "Sala Grande",
    "Sala Pequena": "Sala Peq.",
}

# Extrusion heights per floor (meters)
_FLOOR_0_Y_BASE = 0.0
_FLOOR_0_Y_TOP = 3.0
_FLOOR_1_Y_BASE = 3.2  # 0.2m slab between floors
_FLOOR_1_Y_TOP = 6.2
_WALL_HEIGHT_0 = _FLOOR_0_Y_TOP - _FLOOR_0_Y_BASE  # 3.0m
_WALL_HEIGHT_1 = _FLOOR_1_Y_TOP - _FLOOR_1_Y_BASE  # 3.0m

# Inset from polygon bounds so adjacent rooms have a visible gap
_ZONE_PADDING = 0.05

# Default zone material opacity
_ZONE_OPACITY = 0.85


def generate_3d_html(
    building_data: dict[str, dict[str, Any]] | None = None,
    metric: str = "freedom_index",
    visible_floors: str = "all",
    afi_data: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Generate a complete HTML page with an embedded Three.js 3D building.

    Args:
        building_data: Dict mapping zone_id to metric values dict.
        metric: Which metric to color zones by
            ('freedom_index', 'temperature_c', 'occupant_count', 'total_energy_kwh').
        visible_floors: Which floors to show ('all', '0', '1').
        afi_data: Optional dict mapping zone_id to financial overlay data
            with keys: financial_bleed_eur_hr, freedom, perception, distortion.

    Returns:
        Self-contained HTML string for use as Iframe srcDoc.
    """
    building_data = building_data or {}
    zone_js = _build_zone_meshes_js(building_data, metric, visible_floors, afi_data)

    # Camera target at building center, vertically between both floors
    cam_target_x = FLOOR_WIDTH_M / 2
    cam_target_z = FLOOR_HEIGHT_M / 2
    cam_target_y = (_FLOOR_0_Y_TOP + _FLOOR_1_Y_BASE) / 2

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  html, body {{ width: 100%; height: 100%; overflow: hidden; background: #f8fafc; }}
  canvas {{ display: block; }}
  #tooltip {{
    position: absolute;
    pointer-events: none;
    display: none;
    background: rgba(255,255,255,0.96);
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 12px;
    padding: 12px 16px;
    font-family: 'Inter', -apple-system, sans-serif;
    font-size: 12px;
    color: {TEXT_PRIMARY};
    line-height: 1.5;
    box-shadow: 0 4px 20px rgba(0,0,0,0.12);
    max-width: 240px;
    z-index: 100;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
  }}
  #tooltip .tt-title {{
    font-weight: 600;
    font-size: 13px;
    margin-bottom: 6px;
    color: {TEXT_PRIMARY};
  }}
  #tooltip .tt-row {{
    display: flex;
    justify-content: space-between;
    gap: 16px;
    padding: 2px 0;
  }}
  #tooltip .tt-label {{
    color: {TEXT_SECONDARY};
  }}
  #tooltip .tt-value {{
    font-family: 'JetBrains Mono', monospace;
    font-weight: 500;
    text-align: right;
  }}
  #tooltip .tt-divider {{
    border-top: 1px solid #E5E5EA;
    margin: 6px 0;
  }}
</style>
</head>
<body>
<div id="tooltip"></div>
<div id="mode-toggle" style="position:absolute;top:16px;left:16px;z-index:100;
  background:rgba(255,255,255,0.92);backdrop-filter:blur(8px);
  border-radius:12px;padding:8px 16px;cursor:pointer;
  font-family:'Inter',sans-serif;font-size:13px;font-weight:500;
  color:#1D1D1F;box-shadow:0 2px 12px rgba(0,0,0,0.1);
  border:1px solid #E5E5EA;user-select:none;">
  &#x1F3AE; First Person
</div>
<div id="fps-instructions" style="position:absolute;bottom:16px;left:50%;transform:translateX(-50%);
  z-index:100;display:none;background:rgba(0,0,0,0.7);color:#fff;
  border-radius:12px;padding:12px 24px;font-family:'Inter',sans-serif;font-size:13px;
  text-align:center;">
  WASD to move &middot; Mouse to look &middot; ESC to exit
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
<script src="https://unpkg.com/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
<script src="https://unpkg.com/three@0.128.0/examples/js/controls/PointerLockControls.js"></script>
<script>
(function() {{
  "use strict";

  // -- Scene setup -----------------------------------------
  var scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0xf8fafc, 80, 180);

  var camera = new THREE.PerspectiveCamera(
    40, window.innerWidth / window.innerHeight, 0.5, 250
  );
  camera.position.set(45, 35, 45);

  var renderer = new THREE.WebGLRenderer({{
    antialias: true,
    alpha: true,
    powerPreference: "high-performance"
  }});
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setClearColor(0xf8fafc, 1);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputEncoding = THREE.sRGBEncoding;
  document.body.appendChild(renderer.domElement);

  // -- Controls --------------------------------------------
  var controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 15;
  controls.maxDistance = 100;
  controls.maxPolarAngle = Math.PI / 2.2;
  controls.target.set({cam_target_x:.1f}, {cam_target_y:.1f}, {cam_target_z:.1f});
  controls.update();

  // -- First Person Controls ---------------------------------
  var fpControls = new THREE.PointerLockControls(camera, document.body);
  var isFPS = false;
  var moveForward = false, moveBackward = false, moveLeft = false, moveRight = false;
  var velocity = new THREE.Vector3();
  var direction = new THREE.Vector3();
  var prevTime = performance.now();
  var modeBtn = document.getElementById("mode-toggle");
  var fpsInstructions = document.getElementById("fps-instructions");

  modeBtn.addEventListener("click", function() {{
    if (!isFPS) {{
      // Enter FPS mode
      camera.position.set(5, 1.6, 7.5); // eye level floor 0
      fpControls.lock();
    }} else {{
      // Exit FPS mode
      fpControls.unlock();
    }}
  }});

  fpControls.addEventListener("lock", function() {{
    isFPS = true;
    controls.enabled = false;
    modeBtn.innerHTML = "&#x1F3AE; Exit First Person";
    fpsInstructions.style.display = "block";
  }});

  fpControls.addEventListener("unlock", function() {{
    isFPS = false;
    controls.enabled = true;
    modeBtn.innerHTML = "&#x1F3AE; First Person";
    fpsInstructions.style.display = "none";
    velocity.set(0, 0, 0);
  }});

  document.addEventListener("keydown", function(e) {{
    if (!isFPS) return;
    switch(e.code) {{
      case "KeyW": case "ArrowUp": moveForward = true; break;
      case "KeyS": case "ArrowDown": moveBackward = true; break;
      case "KeyA": case "ArrowLeft": moveLeft = true; break;
      case "KeyD": case "ArrowRight": moveRight = true; break;
    }}
  }});

  document.addEventListener("keyup", function(e) {{
    switch(e.code) {{
      case "KeyW": case "ArrowUp": moveForward = false; break;
      case "KeyS": case "ArrowDown": moveBackward = false; break;
      case "KeyA": case "ArrowLeft": moveLeft = false; break;
      case "KeyD": case "ArrowRight": moveRight = false; break;
    }}
  }});

  // -- Lighting --------------------------------------------
  var ambient = new THREE.AmbientLight(0xffffff, 0.55);
  scene.add(ambient);

  var dirLight = new THREE.DirectionalLight(0xffffff, 0.75);
  dirLight.position.set(35, 45, 40);
  dirLight.castShadow = true;
  dirLight.shadow.mapSize.set(2048, 2048);
  dirLight.shadow.camera.left = -55;
  dirLight.shadow.camera.right = 55;
  dirLight.shadow.camera.top = 30;
  dirLight.shadow.camera.bottom = -30;
  dirLight.shadow.camera.near = 1;
  dirLight.shadow.camera.far = 120;
  dirLight.shadow.bias = -0.001;
  dirLight.shadow.radius = 4;
  scene.add(dirLight);

  var hemiLight = new THREE.HemisphereLight(0xddeeff, 0xffeedd, 0.25);
  scene.add(hemiLight);

  // -- Ground plane ----------------------------------------
  var groundGeo = new THREE.PlaneGeometry(70, 40);
  var groundMat = new THREE.MeshStandardMaterial({{
    color: 0xeef1f5,
    roughness: 0.95,
    metalness: 0.0
  }});
  var ground = new THREE.Mesh(groundGeo, groundMat);
  ground.rotation.x = -Math.PI / 2;
  ground.position.set({cam_target_x:.1f}, -0.05, {cam_target_z:.1f});
  ground.receiveShadow = true;
  scene.add(ground);

  // -- Grid lines ------------------------------------------
  var gridHelper = new THREE.GridHelper(65, 13, 0xd0d5dd, 0xe0e4ea);
  gridHelper.position.set({cam_target_x:.1f}, -0.04, {cam_target_z:.1f});
  scene.add(gridHelper);

  // -- Floor slabs -----------------------------------------
  function addFloorSlab(yPos) {{
    var geo = new THREE.BoxGeometry(
      {FLOOR_WIDTH_M + 2:.1f}, 0.12, {FLOOR_HEIGHT_M + 2:.1f}
    );
    var mat = new THREE.MeshStandardMaterial({{
      color: 0xf0f2f5,
      roughness: 0.8,
      metalness: 0.02,
      transparent: true,
      opacity: 0.9
    }});
    var slab = new THREE.Mesh(geo, mat);
    slab.position.set({cam_target_x:.1f}, yPos, {cam_target_z:.1f});
    slab.receiveShadow = true;
    scene.add(slab);
  }}
  addFloorSlab({_FLOOR_0_Y_BASE});
  addFloorSlab({_FLOOR_1_Y_BASE});

  // -- Zone meshes container -------------------------------
  var zoneMeshes = [];
  var labelSprites = [];

  function hexToThreeColor(hex) {{
    return new THREE.Color(hex);
  }}

  function addZone(id, name, cx, yBase, cz, w, h, d, colorHex, metricsJson, opacity) {{
    var color = hexToThreeColor(colorHex);
    var geo = new THREE.BoxGeometry(w, h, d);
    var mat = new THREE.MeshStandardMaterial({{
      color: color,
      roughness: 0.6,
      metalness: 0.05,
      transparent: true,
      opacity: opacity
    }});
    var mesh = new THREE.Mesh(geo, mat);
    mesh.position.set(cx, yBase + h / 2, cz);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    mesh.userData = {{
      zoneId: id,
      zoneName: name,
      metrics: metricsJson,
      baseColor: color.clone(),
      baseOpacity: opacity
    }};
    scene.add(mesh);
    zoneMeshes.push(mesh);

    // -- Edges --
    var edgeGeo = new THREE.EdgesGeometry(geo);
    var edgeMat = new THREE.LineBasicMaterial({{
      color: 0x999999,
      transparent: true,
      opacity: 0.3
    }});
    var edges = new THREE.LineSegments(edgeGeo, edgeMat);
    edges.position.copy(mesh.position);
    scene.add(edges);

    // -- Label sprite --
    if (name && name !== "") {{
      var canvas = document.createElement("canvas");
      canvas.width = 256;
      canvas.height = 64;
      var ctx = canvas.getContext("2d");

      ctx.fillStyle = "rgba(255,255,255,0.85)";
      var radius = 10;
      ctx.beginPath();
      ctx.moveTo(radius, 2);
      ctx.lineTo(254 - radius, 2);
      ctx.quadraticCurveTo(254, 2, 254, 2 + radius);
      ctx.lineTo(254, 62 - radius);
      ctx.quadraticCurveTo(254, 62, 254 - radius, 62);
      ctx.lineTo(radius, 62);
      ctx.quadraticCurveTo(2, 62, 2, 62 - radius);
      ctx.lineTo(2, 2 + radius);
      ctx.quadraticCurveTo(2, 2, radius, 2);
      ctx.closePath();
      ctx.fill();

      ctx.font = "bold 22px Inter, -apple-system, sans-serif";
      ctx.fillStyle = "#1D1D1F";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(name, 128, 32);

      var tex = new THREE.CanvasTexture(canvas);
      tex.minFilter = THREE.LinearFilter;
      var spriteMat = new THREE.SpriteMaterial({{
        map: tex,
        transparent: true,
        depthTest: false
      }});
      var sprite = new THREE.Sprite(spriteMat);
      sprite.position.set(cx, yBase + h + 0.6, cz);
      sprite.scale.set(3.5, 0.875, 1);
      scene.add(sprite);
      labelSprites.push(sprite);
    }}
  }}

  // -- Add zone meshes (generated from Python) -------------
  {zone_js}

  // -- Raycaster (hover) -----------------------------------
  var raycaster = new THREE.Raycaster();
  var mouse = new THREE.Vector2();
  var tooltip = document.getElementById("tooltip");
  var hoveredMesh = null;

  function onMouseMove(event) {{
    mouse.x = (event.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(event.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    var intersects = raycaster.intersectObjects(zoneMeshes);

    if (intersects.length > 0) {{
      var hit = intersects[0].object;
      if (hoveredMesh !== hit) {{
        resetHover();
        hoveredMesh = hit;
        hit.material.emissive.setHex(0x222222);
        hit.material.emissiveIntensity = 0.15;
      }}
      var ud = hit.userData;
      var m = ud.metrics || {{}};
      var html = '<div class="tt-title">' + ud.zoneName + '</div>';
      html += '<div class="tt-divider"></div>';
      if (m.temperature_c != null)
        html += '<div class="tt-row"><span class="tt-label">Temperature</span>'
          + '<span class="tt-value">' + m.temperature_c.toFixed(1) + ' C</span></div>';
      if (m.humidity_pct != null)
        html += '<div class="tt-row"><span class="tt-label">Humidity</span>'
          + '<span class="tt-value">' + m.humidity_pct.toFixed(0) + '%</span></div>';
      if (m.co2_ppm != null)
        html += '<div class="tt-row"><span class="tt-label">CO2</span>'
          + '<span class="tt-value">' + m.co2_ppm.toFixed(0) + ' ppm</span></div>';
      if (m.occupant_count != null)
        html += '<div class="tt-row"><span class="tt-label">Occupancy</span>'
          + '<span class="tt-value">' + m.occupant_count + '</span></div>';
      if (m.total_energy_kwh != null)
        html += '<div class="tt-row"><span class="tt-label">Energy</span>'
          + '<span class="tt-value">' + m.total_energy_kwh.toFixed(2) + ' kWh</span></div>';
      if (m.freedom_index != null) {{
        html += '<div class="tt-divider"></div>';
        html += '<div class="tt-row"><span class="tt-label">Freedom Index</span>'
          + '<span class="tt-value" style="font-weight:600">'
          + m.freedom_index.toFixed(0) + '/100</span></div>';
      }}

      tooltip.innerHTML = html;
      tooltip.style.display = "block";
      var tx = event.clientX + 16;
      var ty = event.clientY - 10;
      if (tx + 260 > window.innerWidth) tx = event.clientX - 260;
      if (ty + 200 > window.innerHeight) ty = event.clientY - 200;
      tooltip.style.left = tx + "px";
      tooltip.style.top = ty + "px";
    }} else {{
      resetHover();
      tooltip.style.display = "none";
    }}
  }}

  function resetHover() {{
    if (hoveredMesh) {{
      hoveredMesh.material.emissive.setHex(0x000000);
      hoveredMesh.material.emissiveIntensity = 0;
      hoveredMesh = null;
    }}
  }}

  window.addEventListener("mousemove", onMouseMove, false);

  // -- Window resize ---------------------------------------
  window.addEventListener("resize", function() {{
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }});

  // -- Animation loop --------------------------------------
  function animate() {{
    requestAnimationFrame(animate);
    if (isFPS && fpControls.isLocked) {{
      var time = performance.now();
      var delta = (time - prevTime) / 1000;
      velocity.x -= velocity.x * 8.0 * delta;
      velocity.z -= velocity.z * 8.0 * delta;
      direction.z = Number(moveForward) - Number(moveBackward);
      direction.x = Number(moveRight) - Number(moveLeft);
      direction.normalize();
      if (moveForward || moveBackward) velocity.z -= direction.z * 25.0 * delta;
      if (moveLeft || moveRight) velocity.x -= direction.x * 25.0 * delta;
      fpControls.moveRight(-velocity.x * delta);
      fpControls.moveForward(-velocity.z * delta);
      // Clamp Y to eye level
      camera.position.y = 1.6;
      // Clamp to building bounds
      camera.position.x = Math.max(0, Math.min(camera.position.x, 48.4));
      camera.position.z = Math.max(0, Math.min(camera.position.z, 15));
      prevTime = time;
    }} else {{
      controls.update();
    }}
    renderer.render(scene, camera);
  }}
  animate();

  // -- Public API for reset camera -------------------------
  window.resetCamera = function() {{
    camera.position.set(45, 35, 45);
    controls.target.set({cam_target_x:.1f}, {cam_target_y:.1f}, {cam_target_z:.1f});
    controls.update();
  }};

}})();
</script>
</body>
</html>"""


def _build_zone_meshes_js(
    building_data: dict[str, dict[str, Any]],
    metric: str,
    visible_floors: str,
    afi_data: dict[str, dict[str, Any]] | None = None,
) -> str:
    """Generate JavaScript addZone() calls for all visible zones.

    Args:
        building_data: Zone metric data keyed by zone_id.
        metric: Which metric to use for coloring.
        visible_floors: Which floors to render ('all', '0', '1').
        afi_data: Optional dict mapping zone_id to financial overlay data
            with keys: financial_bleed_eur_hr, freedom, perception, distortion.

    Returns:
        JavaScript code string with addZone() calls.
    """
    lines: list[str] = []

    floor_zones: list[tuple[int, str, list[tuple[float, float]]]] = []

    if visible_floors in ("all", "0"):
        for zone_id, polygon in FLOOR_0_ZONES.items():
            floor_zones.append((0, zone_id, polygon))

    if visible_floors in ("all", "1"):
        for zone_id, polygon in FLOOR_1_ZONES.items():
            floor_zones.append((1, zone_id, polygon))

    for floor_num, zone_id, polygon in floor_zones:
        zone_info = get_zone_by_id(zone_id)
        name = zone_info.name if zone_info else zone_id
        short_name = _NAME_SHORT.get(name, name)
        capacity = zone_info.capacity if zone_info else 0

        # Bounding box
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        x_min, x_max = min(xs) + _ZONE_PADDING, max(xs) - _ZONE_PADDING
        y_min, y_max = min(ys) + _ZONE_PADDING, max(ys) - _ZONE_PADDING
        w = x_max - x_min
        d = y_max - y_min
        cx = (x_min + x_max) / 2
        cz = (y_min + y_max) / 2

        # Y offset and wall height based on floor
        if floor_num == 0:
            y_base = _FLOOR_0_Y_BASE + 0.06
            wall_h = _WALL_HEIGHT_0 - 0.06
        else:
            y_base = _FLOOR_1_Y_BASE + 0.06
            wall_h = _WALL_HEIGHT_1 - 0.06

        # Get metrics and compute color
        zd = building_data.get(zone_id, {})
        color = _get_zone_color(zd, metric)

        # Material opacity
        opacity = _ZONE_OPACITY

        # Metrics JSON for tooltip
        metrics_json = json.dumps(zd) if zd else "{}"

        # Only show labels for zones with capacity > 0
        label = short_name if capacity > 0 else ""

        lines.append(
            f'  addZone("{zone_id}", "{label}", '
            f"{cx:.2f}, {y_base:.2f}, {cz:.2f}, "
            f"{w:.2f}, {wall_h:.2f}, {d:.2f}, "
            f'"{color}", {metrics_json}, {opacity});'
        )

        # Add financial overlay sprite if afi_data is provided for this zone
        if afi_data and zone_id in afi_data:
            zafi = afi_data[zone_id]
            bleed = float(zafi.get("financial_bleed_eur_hr", 0.0))
            freedom = float(zafi.get("freedom", 50.0))
            # Color freedom value: green if high, red if low
            if freedom >= 70:
                freedom_color = STATUS_HEALTHY
            elif freedom >= 40:
                freedom_color = STATUS_WARNING
            else:
                freedom_color = STATUS_CRITICAL
            sprite_y = y_base + wall_h + 1.5
            lines.append(
                f"  (function() {{\n"
                f'    var canvas = document.createElement("canvas");\n'
                f"    canvas.width = 256;\n"
                f"    canvas.height = 96;\n"
                f'    var ctx = canvas.getContext("2d");\n'
                f'    ctx.fillStyle = "rgba(0,0,0,0.75)";\n'
                f"    ctx.beginPath();\n"
                f"    ctx.roundRect(4, 4, 248, 88, 10);\n"
                f"    ctx.fill();\n"
                f"    ctx.font = \"bold 20px 'JetBrains Mono', monospace\";\n"
                f'    ctx.fillStyle = "#FFD60A";\n'
                f'    ctx.textAlign = "center";\n'
                f'    ctx.fillText("\\u20AC{bleed:.2f}/hr", 128, 40);\n'
                f"    ctx.font = \"16px 'Inter', sans-serif\";\n"
                f'    ctx.fillStyle = "{freedom_color}";\n'
                f'    ctx.fillText("F: {freedom:.0f}", 128, 70);\n'
                f"    var tex = new THREE.CanvasTexture(canvas);\n"
                f"    tex.minFilter = THREE.LinearFilter;\n"
                f"    var spriteMat = new THREE.SpriteMaterial({{ map: tex,"
                f" transparent: true, depthTest: false }});\n"
                f"    var sprite = new THREE.Sprite(spriteMat);\n"
                f"    sprite.position.set({cx:.2f}, {sprite_y:.2f}, {cz:.2f});\n"
                f"    sprite.scale.set(3, 1.125, 1);\n"
                f"    scene.add(sprite);\n"
                f"  }})();"
            )

    return "\n".join(lines)


def _get_zone_color(
    zone_data: dict[str, Any],
    metric: str,
) -> str:
    """Determine the hex color for a zone based on metric value.

    Args:
        zone_data: Metric values dict for the zone.
        metric: Which metric to color by.

    Returns:
        Hex color string.
    """
    if not zone_data:
        return "#C8CCD0"

    if metric == "freedom_index":
        score = zone_data.get("freedom_index", 50.0)
        return zone_health_to_color(float(score))

    if metric == "temperature_c":
        temp = zone_data.get("temperature_c")
        if temp is None:
            return "#C8CCD0"
        return interpolate_color(
            float(temp),
            16.0,
            30.0,
            [STATUS_CRITICAL, STATUS_WARNING, STATUS_HEALTHY],
        )

    if metric == "occupant_count":
        occ = zone_data.get("occupant_count", 0)
        return interpolate_color(
            float(occ),
            0.0,
            50.0,
            [STATUS_HEALTHY, STATUS_WARNING, STATUS_CRITICAL],
        )

    if metric == "total_energy_kwh":
        energy = zone_data.get("total_energy_kwh", 0)
        return interpolate_color(
            float(energy),
            0.0,
            15.0,
            [STATUS_HEALTHY, STATUS_WARNING, STATUS_CRITICAL],
        )

    return zone_health_to_color(zone_data.get("freedom_index", 50.0))
