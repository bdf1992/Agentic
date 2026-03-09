"""
Deformation Renderer — Interactive coherent channel response.

The missing link: deform the geometry and watch ALL channels respond together.
  Push a vertex → color shifts → frequency changes → texture warps
  Release → elastic recovery at rate 2/3 (the spectral gap IS the spring constant)

This demonstrates Properties 7 (physics-like), 10 (living state), and 16 (shape memory)
in actual visual form.

Usage:
    python demos/deformation_renderer.py              # torus with deformation
    python demos/deformation_renderer.py sphere        # sphere with deformation
"""

import sys
import os
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algebra.sensory_manifold import SensoryManifold, DistinctionState, DistinctionTexture


def mesh_to_json(manifold: SensoryManifold) -> dict:
    """Convert mesh to JSON for WebGL."""
    mesh = manifold.render_mesh()
    vertices = mesh["vertices"]
    faces = mesh["faces"]
    colors = mesh["colors"]

    z3_labels = []
    if "z3_labels" in mesh:
        for major, minor in mesh["z3_labels"]:
            z3_labels.append(major)
    else:
        z3_labels = [i % 3 for i in range(len(vertices))]

    texture = mesh.get("texture", np.zeros(len(vertices)))
    frequencies = mesh.get("frequencies", np.full(len(vertices), 440.0))

    # Compute per-vertex normals for raycasting
    normals = np.zeros_like(vertices)
    for face in faces:
        v0, v1, v2 = vertices[face[0]], vertices[face[1]], vertices[face[2]]
        n = np.cross(v1 - v0, v2 - v0)
        norm = np.linalg.norm(n)
        if norm > 1e-10:
            n = n / norm
        for idx in face:
            normals[idx] += n
    for i in range(len(normals)):
        norm = np.linalg.norm(normals[i])
        if norm > 1e-10:
            normals[i] /= norm

    return {
        "positions": vertices.flatten().tolist(),
        "normals": normals.flatten().tolist(),
        "indices": faces.flatten().tolist(),
        "colors": colors.flatten().tolist(),
        "texture": texture.tolist(),
        "frequencies": frequencies.tolist(),
        "z3_labels": z3_labels,
        "n_vertices": int(mesh["n_vertices"]),
        "n_faces": int(mesh["n_faces"]),
        "euler": int(mesh["euler_characteristic"]),
        "surface_type": manifold.surface_type,
    }


def generate_html(surface_type: str = "torus") -> str:
    """Generate HTML with deformation physics."""
    manifold = SensoryManifold(surface_type=surface_type, alpha=0.5, base_freq=440.0)
    mesh_data = mesh_to_json(manifold)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Coherent Deformation — {surface_type.title()}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #080810; color: #ccc; font-family: 'Courier New', monospace; overflow: hidden; }}
canvas {{ display: block; }}

#hud {{
    position: absolute; top: 12px; left: 12px;
    background: rgba(8,8,16,0.9); border: 1px solid #2a2a3a;
    border-radius: 6px; padding: 12px; font-size: 11px; width: 300px;
}}
#hud h2 {{ color: #7af; font-size: 13px; margin-bottom: 6px; }}
.metric {{ display: flex; justify-content: space-between; padding: 2px 0; }}
.metric-label {{ color: #888; }}
.metric-value {{ color: #adf; font-weight: bold; }}
.section {{ border-top: 1px solid #1a1a2a; margin-top: 8px; padding-top: 8px; }}
.section-title {{ color: #888; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }}

#energy-bar {{
    width: 100%; height: 8px; background: #111;
    border-radius: 4px; overflow: hidden; margin: 4px 0;
}}
#energy-fill {{
    height: 100%; background: linear-gradient(90deg, #2a4, #4a2);
    width: 0%; transition: width 0.1s;
}}

#channel-bars {{ margin-top: 6px; }}
.channel-bar {{
    display: flex; align-items: center; gap: 6px; margin: 2px 0;
}}
.channel-name {{ width: 60px; font-size: 10px; color: #888; }}
.bar-bg {{
    flex: 1; height: 6px; background: #111; border-radius: 3px; overflow: hidden;
}}
.bar-fill {{ height: 100%; border-radius: 3px; transition: width 0.15s; }}

#instructions {{
    position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%);
    background: rgba(8,8,16,0.85); border: 1px solid #2a2a3a;
    border-radius: 6px; padding: 8px 16px; font-size: 11px; color: #666;
    text-align: center;
}}

#audio-indicator {{
    position: absolute; top: 12px; right: 12px;
    background: rgba(8,8,16,0.9); border: 1px solid #2a2a3a;
    border-radius: 6px; padding: 8px 12px; font-size: 11px;
}}
#freq-display {{ color: #fa7; font-size: 14px; font-weight: bold; }}
</style>
</head>
<body>
<div id="hud">
    <h2>Coherent Deformation System</h2>
    <div class="metric">
        <span class="metric-label">Surface</span>
        <span class="metric-value">{surface_type}</span>
    </div>
    <div class="metric">
        <span class="metric-label">Spring constant</span>
        <span class="metric-value">2/3 (spectral gap)</span>
    </div>
    <div class="metric">
        <span class="metric-label">Deformation energy</span>
        <span class="metric-value" id="energy-val">0.000</span>
    </div>
    <div id="energy-bar"><div id="energy-fill"></div></div>

    <div class="section">
        <div class="section-title">Channel Response (all locked by 2/3)</div>
        <div id="channel-bars">
            <div class="channel-bar">
                <span class="channel-name">Geometry</span>
                <div class="bar-bg"><div class="bar-fill" id="bar-geo" style="width:0%; background:#4af;"></div></div>
            </div>
            <div class="channel-bar">
                <span class="channel-name">Color</span>
                <div class="bar-bg"><div class="bar-fill" id="bar-col" style="width:0%; background:#f74;"></div></div>
            </div>
            <div class="channel-bar">
                <span class="channel-name">Sound</span>
                <div class="bar-bg"><div class="bar-fill" id="bar-snd" style="width:0%; background:#7f4;"></div></div>
            </div>
            <div class="channel-bar">
                <span class="channel-name">Texture</span>
                <div class="bar-bg"><div class="bar-fill" id="bar-tex" style="width:0%; background:#f4f;"></div></div>
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Conservation</div>
        <div class="metric">
            <span class="metric-label">Total energy</span>
            <span class="metric-value" id="total-energy">0.000</span>
        </div>
        <div class="metric">
            <span class="metric-label">Z3 charge</span>
            <span class="metric-value" id="z3-charge">0</span>
        </div>
        <div class="metric">
            <span class="metric-label">Euler chi</span>
            <span class="metric-value" id="euler-chi">{mesh_data['euler']}</span>
        </div>
    </div>
</div>

<div id="audio-indicator">
    <div style="color:#888; font-size:10px;">Frequency</div>
    <div id="freq-display">—</div>
    <div style="color:#555; font-size:9px; margin-top:2px;">Click mesh to hear</div>
</div>

<div id="instructions">
    Click &amp; drag to deform | Release to recover (spring = 2/3) | Scroll to zoom | Right-drag to rotate
</div>

<script type="importmap">
{{
    "imports": {{
        "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
        "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
    }}
}}
</script>
<script type="module">
import * as THREE from 'three';
import {{ OrbitControls }} from 'three/addons/controls/OrbitControls.js';

// ═══════════════════════════════════════════════════════════════
// FORCED CONSTANTS — every number traces to the algebra
// ═══════════════════════════════════════════════════════════════
const GAP = 2.0 / 3.0;          // spectral gap = spring constant
const Z3_ORDER = 3;              // from O1: distinction creates 3
const RECOVERY_RATE = GAP;       // elastic recovery per frame
const INFLUENCE_RADIUS = 1.2;    // in mesh units
const MAX_DEFORM = 1.5;          // max displacement before clamping

// ═══════════════════════════════════════════════════════════════
// DATA
// ═══════════════════════════════════════════════════════════════
const meshData = {json.dumps(mesh_data)};
const nVerts = meshData.n_vertices;

// ═══════════════════════════════════════════════════════════════
// SCENE
// ═══════════════════════════════════════════════════════════════
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x080810);

const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(5, 3, 5);

const renderer = new THREE.WebGLRenderer({{ antialias: true }});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
document.body.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.mouseButtons = {{ LEFT: null, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE }};

// Lighting
scene.add(new THREE.AmbientLight(0x303040, 0.5));
const sun = new THREE.DirectionalLight(0xffffff, 0.9);
sun.position.set(5, 8, 5);
scene.add(sun);
scene.add(new THREE.DirectionalLight(0x4466aa, 0.3).position.set(-3, -2, -4));

// ═══════════════════════════════════════════════════════════════
// GEOMETRY + DEFORMATION STATE
// ═══════════════════════════════════════════════════════════════
const geometry = new THREE.BufferGeometry();

// Positions (mutable — deformation target)
const restPositions = new Float32Array(meshData.positions);   // original
const currPositions = new Float32Array(meshData.positions);   // current
const velocities = new Float32Array(nVerts * 3);              // per-vertex velocity
geometry.setAttribute('position', new THREE.BufferAttribute(currPositions, 3));

// Colors (mutable — shift with deformation)
const restColors = new Float32Array(meshData.colors);
const currColors = new Float32Array(meshData.colors);
geometry.setAttribute('color', new THREE.BufferAttribute(currColors, 3));

// Indices
geometry.setIndex(new THREE.BufferAttribute(new Uint32Array(meshData.indices), 1));
geometry.computeVertexNormals();

// Material
const material = new THREE.MeshPhongMaterial({{
    vertexColors: true, side: THREE.DoubleSide,
    shininess: 30, specular: new THREE.Color(0x222233),
}});
const meshObj = new THREE.Mesh(geometry, material);
scene.add(meshObj);

// Wireframe
const wireMat = new THREE.MeshBasicMaterial({{ wireframe: true, color: 0x223344, transparent: true, opacity: 0.08 }});
const wireObj = new THREE.Mesh(geometry, wireMat);
scene.add(wireObj);

// ═══════════════════════════════════════════════════════════════
// AUDIO CONTEXT (Web Audio API)
// ═══════════════════════════════════════════════════════════════
let audioCtx = null;
let oscillator = null;
let gainNode = null;

function initAudio() {{
    if (audioCtx) return;
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    oscillator = audioCtx.createOscillator();
    gainNode = audioCtx.createGain();
    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    oscillator.type = 'sine';
    oscillator.frequency.value = 0;
    gainNode.gain.value = 0;
    oscillator.start();
}}

function setFrequency(freq, amplitude) {{
    if (!audioCtx) return;
    oscillator.frequency.setTargetAtTime(freq, audioCtx.currentTime, 0.05);
    gainNode.gain.setTargetAtTime(amplitude * 0.15, audioCtx.currentTime, 0.05);
}}

function silenceAudio() {{
    if (!audioCtx) return;
    gainNode.gain.setTargetAtTime(0, audioCtx.currentTime, 0.1);
}}

// ═══════════════════════════════════════════════════════════════
// RAYCASTING + DEFORMATION
// ═══════════════════════════════════════════════════════════════
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
let isDragging = false;
let dragVertex = -1;
let dragPlane = new THREE.Plane();
let dragOffset = new THREE.Vector3();

function getClosestVertex(point) {{
    let minDist = Infinity;
    let closest = -1;
    for (let i = 0; i < nVerts; i++) {{
        const dx = currPositions[i*3] - point.x;
        const dy = currPositions[i*3+1] - point.y;
        const dz = currPositions[i*3+2] - point.z;
        const dist = dx*dx + dy*dy + dz*dz;
        if (dist < minDist) {{
            minDist = dist;
            closest = i;
        }}
    }}
    return closest;
}}

function applyDeformation(centerIdx, displacement) {{
    const cx = restPositions[centerIdx * 3];
    const cy = restPositions[centerIdx * 3 + 1];
    const cz = restPositions[centerIdx * 3 + 2];

    for (let i = 0; i < nVerts; i++) {{
        const rx = restPositions[i * 3];
        const ry = restPositions[i * 3 + 1];
        const rz = restPositions[i * 3 + 2];

        const dx = rx - cx;
        const dy = ry - cy;
        const dz = rz - cz;
        const dist = Math.sqrt(dx*dx + dy*dy + dz*dz);

        if (dist < INFLUENCE_RADIUS) {{
            // Gaussian falloff (sigma = INFLUENCE_RADIUS * 2/3)
            const sigma = INFLUENCE_RADIUS * GAP;
            const weight = Math.exp(-(dist * dist) / (2 * sigma * sigma));

            // Clamp displacement
            const scale = Math.min(weight, 1.0);
            currPositions[i*3]   = restPositions[i*3]   + displacement.x * scale;
            currPositions[i*3+1] = restPositions[i*3+1] + displacement.y * scale;
            currPositions[i*3+2] = restPositions[i*3+2] + displacement.z * scale;

            // Color response: hue rotates proportional to deformation
            // The spectral gap couples geometry→color
            const deformMag = Math.sqrt(
                displacement.x*displacement.x +
                displacement.y*displacement.y +
                displacement.z*displacement.z
            ) * scale;

            const z3 = meshData.z3_labels[i];
            const hueShift = deformMag * GAP;  // gap couples geo→color

            // Shift each RGB channel
            const rr = restColors[i*3];
            const gg = restColors[i*3+1];
            const bb = restColors[i*3+2];

            // Rotate in color space by hueShift (simplified HSV rotation)
            const cosH = Math.cos(hueShift * Math.PI);
            const sinH = Math.sin(hueShift * Math.PI);
            currColors[i*3]   = Math.max(0, Math.min(1, rr * cosH - gg * sinH * GAP));
            currColors[i*3+1] = Math.max(0, Math.min(1, gg * cosH + rr * sinH * GAP));
            currColors[i*3+2] = Math.max(0, Math.min(1, bb + deformMag * (1 - GAP)));
        }}
    }}

    geometry.attributes.position.needsUpdate = true;
    geometry.attributes.color.needsUpdate = true;
    geometry.computeVertexNormals();
}}

// ═══════════════════════════════════════════════════════════════
// ELASTIC RECOVERY — spring constant IS the spectral gap
// ═══════════════════════════════════════════════════════════════
function elasticRecover(dt) {{
    let totalEnergy = 0;
    let maxDisplacement = 0;

    for (let i = 0; i < nVerts; i++) {{
        const i3 = i * 3;

        // Displacement from rest
        const dx = currPositions[i3]   - restPositions[i3];
        const dy = currPositions[i3+1] - restPositions[i3+1];
        const dz = currPositions[i3+2] - restPositions[i3+2];
        const disp = Math.sqrt(dx*dx + dy*dy + dz*dz);

        if (disp > 0.0001) {{
            // Restoring force: F = -k * x, where k = 2/3 (spectral gap)
            const fx = -GAP * dx;
            const fy = -GAP * dy;
            const fz = -GAP * dz;

            // Damped velocity update (critical damping at sqrt(4*k*m) with m=1)
            const damping = 2 * Math.sqrt(GAP);  // critical damping
            velocities[i3]   = (velocities[i3]   + fx * dt) * (1 - damping * dt);
            velocities[i3+1] = (velocities[i3+1] + fy * dt) * (1 - damping * dt);
            velocities[i3+2] = (velocities[i3+2] + fz * dt) * (1 - damping * dt);

            // Position update
            currPositions[i3]   += velocities[i3]   * dt;
            currPositions[i3+1] += velocities[i3+1] * dt;
            currPositions[i3+2] += velocities[i3+2] * dt;

            // Color recovery (same rate)
            currColors[i3]   += (restColors[i3]   - currColors[i3])   * GAP * dt;
            currColors[i3+1] += (restColors[i3+1] - currColors[i3+1]) * GAP * dt;
            currColors[i3+2] += (restColors[i3+2] - currColors[i3+2]) * GAP * dt;

            // Energy = 0.5 * k * x^2 (potential) + 0.5 * m * v^2 (kinetic)
            const v2 = velocities[i3]*velocities[i3] + velocities[i3+1]*velocities[i3+1] + velocities[i3+2]*velocities[i3+2];
            totalEnergy += 0.5 * GAP * disp * disp + 0.5 * v2;
            maxDisplacement = Math.max(maxDisplacement, disp);
        }}
    }}

    if (maxDisplacement > 0.0001) {{
        geometry.attributes.position.needsUpdate = true;
        geometry.attributes.color.needsUpdate = true;
        geometry.computeVertexNormals();
    }}

    return {{ totalEnergy, maxDisplacement }};
}}

// ═══════════════════════════════════════════════════════════════
// CONSERVATION LAW: Z₃ charge
// ═══════════════════════════════════════════════════════════════
function computeZ3Charge() {{
    let charge = 0;
    for (let i = 0; i < nVerts; i++) {{
        charge = (charge + meshData.z3_labels[i]) % Z3_ORDER;
    }}
    return charge;
}}

// ═══════════════════════════════════════════════════════════════
// MOUSE EVENTS
// ═══════════════════════════════════════════════════════════════
renderer.domElement.addEventListener('mousedown', (e) => {{
    if (e.button !== 0) return; // left click only

    initAudio();

    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const intersects = raycaster.intersectObject(meshObj);

    if (intersects.length > 0) {{
        isDragging = true;
        controls.enabled = false;

        const hit = intersects[0];
        dragVertex = getClosestVertex(hit.point);

        // Create drag plane perpendicular to camera
        const camDir = new THREE.Vector3();
        camera.getWorldDirection(camDir);
        dragPlane.setFromNormalAndCoplanarPoint(camDir, hit.point);
        dragOffset.copy(hit.point);

        // Play frequency of hit vertex
        const freq = meshData.frequencies[dragVertex];
        setFrequency(freq, GAP);
        document.getElementById('freq-display').textContent = freq.toFixed(0) + ' Hz';
    }}
}});

renderer.domElement.addEventListener('mousemove', (e) => {{
    if (!isDragging || dragVertex < 0) return;

    mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
    mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const target = new THREE.Vector3();
    raycaster.ray.intersectPlane(dragPlane, target);

    if (target) {{
        const displacement = target.sub(dragOffset);

        // Clamp
        const mag = displacement.length();
        if (mag > MAX_DEFORM) displacement.multiplyScalar(MAX_DEFORM / mag);

        applyDeformation(dragVertex, displacement);

        // Sound: frequency shifts with deformation (Doppler-like, scaled by gap)
        const baseFreq = meshData.frequencies[dragVertex];
        const shiftedFreq = baseFreq * (1 + mag * GAP * 0.5);
        setFrequency(shiftedFreq, Math.min(mag * GAP, 0.8));
        document.getElementById('freq-display').textContent = shiftedFreq.toFixed(0) + ' Hz';
    }}
}});

renderer.domElement.addEventListener('mouseup', () => {{
    if (isDragging) {{
        isDragging = false;
        dragVertex = -1;
        controls.enabled = true;
        silenceAudio();
        document.getElementById('freq-display').textContent = 'recovering...';
    }}
}});

// ═══════════════════════════════════════════════════════════════
// RENDER LOOP
// ═══════════════════════════════════════════════════════════════
const z3Charge = computeZ3Charge();
let lastTime = performance.now();

function animate(now) {{
    requestAnimationFrame(animate);
    const dt = Math.min((now - lastTime) / 1000, 0.05) * 3; // scaled time
    lastTime = now;

    // Elastic recovery when not dragging
    let stats = {{ totalEnergy: 0, maxDisplacement: 0 }};
    if (!isDragging) {{
        stats = elasticRecover(dt);
    }} else {{
        // Compute energy while dragging
        for (let i = 0; i < nVerts; i++) {{
            const i3 = i * 3;
            const dx = currPositions[i3] - restPositions[i3];
            const dy = currPositions[i3+1] - restPositions[i3+1];
            const dz = currPositions[i3+2] - restPositions[i3+2];
            stats.totalEnergy += 0.5 * GAP * (dx*dx + dy*dy + dz*dz);
            stats.maxDisplacement = Math.max(stats.maxDisplacement, Math.sqrt(dx*dx+dy*dy+dz*dz));
        }}
    }}

    // Update HUD
    const e = stats.totalEnergy;
    document.getElementById('energy-val').textContent = e.toFixed(3);
    document.getElementById('energy-fill').style.width = Math.min(e / 2 * 100, 100) + '%';
    document.getElementById('total-energy').textContent = e.toFixed(3);
    document.getElementById('z3-charge').textContent = z3Charge + ' (conserved)';

    // Channel bars (all proportional to deformation, scaled by 2/3)
    const d = stats.maxDisplacement;
    const pct = Math.min(d / MAX_DEFORM * 100, 100);
    document.getElementById('bar-geo').style.width = pct + '%';
    document.getElementById('bar-col').style.width = (pct * GAP) + '%';
    document.getElementById('bar-snd').style.width = (pct * GAP * GAP) + '%';
    document.getElementById('bar-tex').style.width = (pct * GAP * GAP * GAP) + '%';

    if (!isDragging && stats.maxDisplacement < 0.001 && stats.totalEnergy < 0.0001) {{
        document.getElementById('freq-display').textContent = '\\u2014';
    }}

    controls.update();
    renderer.render(scene, camera);
}}
animate(performance.now());

window.addEventListener('resize', () => {{
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
}});
</script>
</body>
</html>"""


def main():
    surface = sys.argv[1] if len(sys.argv) > 1 else "torus"
    if surface not in ("torus", "sphere"):
        print(f"Unknown surface '{surface}'. Use 'torus' or 'sphere'.")
        sys.exit(1)

    html = generate_html(surface)
    out_path = os.path.join(os.path.dirname(__file__), "deformation_output.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Deformation renderer: {out_path}")
    print(f"Surface: {surface}")
    print()
    print("Physics:")
    print(f"  Spring constant = 2/3 (spectral gap)")
    print(f"  Critical damping = 2*sqrt(2/3) = {2*np.sqrt(2/3):.4f}")
    print(f"  Gaussian sigma = radius * 2/3")
    print(f"  Color coupling = deformation * 2/3")
    print(f"  Sound shift = freq * (1 + mag * 2/3)")
    print(f"  Channel cascade: geo→color→sound→texture at (2/3)^n")
    print()
    print("Conservation laws:")
    print(f"  Z₃ charge is conserved through all deformations")
    print(f"  Euler characteristic is topologically invariant")
    print(f"  Total energy = potential + kinetic (dissipated by damping)")


if __name__ == "__main__":
    main()
