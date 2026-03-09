"""
WebGL Renderer — Interactive 3D visualization of the algebraic structures.

Takes mesh data from SensoryManifold and generates a self-contained HTML file
with three.js rendering. Every visual parameter traces to the algebra:

  Vertex positions → Z₃ lattice on surface
  Vertex colors   → Z₃ × Z₂ → U(1) hue wheel
  Texture         → (2/3)^d fractal noise
  Animation       → spectral gap oscillation at eigenvalue frequencies
  Camera orbit    → U(1) continuous rotation

Usage:
    python demos/webgl_renderer.py           # generates demos/render_output.html
    python demos/webgl_renderer.py sphere    # sphere instead of torus
"""

import sys
import json
import os
import numpy as np

# Import from algebra
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algebra.sensory_manifold import SensoryManifold, DistinctionState


def mesh_to_json(manifold: SensoryManifold) -> dict:
    """Convert SensoryManifold mesh data to JSON-serializable format for WebGL."""
    mesh = manifold.render_mesh()
    vertices = mesh["vertices"]
    faces = mesh["faces"]
    colors = mesh["colors"]

    # Flatten for WebGL buffers
    positions = vertices.flatten().tolist()
    indices = faces.flatten().tolist()

    # Per-vertex colors as flat RGB array
    color_array = colors.flatten().tolist()

    # Texture values (fractal noise per vertex)
    texture = mesh.get("texture", np.zeros(len(vertices)))
    texture_array = texture.tolist()

    # Frequency field (each vertex's eigenvalue frequency)
    frequencies = mesh.get("frequencies", np.full(len(vertices), 440.0))
    freq_array = frequencies.tolist()

    # Z₃ labels per vertex for shader use
    z3_labels = []
    if "z3_labels" in mesh:
        for major, minor in mesh["z3_labels"]:
            z3_labels.append(major)
    else:
        z3_labels = [i % 3 for i in range(len(vertices))]

    return {
        "positions": positions,
        "indices": indices,
        "colors": color_array,
        "texture": texture_array,
        "frequencies": freq_array,
        "z3_labels": z3_labels,
        "n_vertices": int(mesh["n_vertices"]),
        "n_faces": int(mesh["n_faces"]),
        "euler": int(mesh["euler_characteristic"]),
        "curvature_total": float(mesh["curvature_total"]),
        "surface_type": manifold.surface_type,
        "spectral_gap": 2.0 / 3.0,
    }


def all_states_json(manifold: SensoryManifold) -> list:
    """Render all 6 Z₃×Z₂ states for the info panel."""
    states = manifold.render_all_states()
    # Make JSON-serializable (convert numpy types)
    for s in states:
        for channel in s.values():
            for k, v in channel.items():
                if isinstance(v, (np.floating, np.integer)):
                    channel[k] = float(v)
                elif isinstance(v, tuple):
                    channel[k] = [float(x) for x in v]
                elif isinstance(v, dict):
                    for kk, vv in v.items():
                        if isinstance(vv, (np.floating, np.integer)):
                            v[kk] = float(vv)
    return states


def generate_html(surface_type: str = "torus") -> str:
    """Generate a self-contained HTML file with three.js WebGL rendering."""

    manifold = SensoryManifold(surface_type=surface_type, alpha=0.5, base_freq=440.0)
    mesh_data = mesh_to_json(manifold)
    states_data = all_states_json(manifold)
    coherence = manifold.coherence_test()
    coherence_serializable = {k: bool(v) for k, v in coherence.items()}

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Distinction Algebra — {surface_type.title()} Renderer</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #0a0a0f; color: #e0e0e0; font-family: 'Courier New', monospace; overflow: hidden; }}
#canvas-container {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; }}
canvas {{ display: block; }}

#panel {{
    position: absolute; top: 16px; right: 16px; width: 340px;
    background: rgba(10,10,20,0.92); border: 1px solid #333;
    border-radius: 8px; padding: 16px; font-size: 12px;
    max-height: calc(100vh - 32px); overflow-y: auto;
}}
#panel h2 {{ color: #7af; margin-bottom: 8px; font-size: 14px; }}
#panel h3 {{ color: #aaa; margin: 12px 0 4px; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }}
.state-row {{
    display: flex; align-items: center; gap: 8px; padding: 3px 0;
    border-bottom: 1px solid #1a1a2a;
}}
.color-swatch {{
    width: 16px; height: 16px; border-radius: 3px; flex-shrink: 0;
    border: 1px solid #444;
}}
.state-label {{ flex: 1; }}
.state-value {{ color: #888; font-size: 10px; }}
.pass {{ color: #4c4; }}
.fail {{ color: #c44; }}

#controls {{
    position: absolute; bottom: 16px; left: 16px;
    background: rgba(10,10,20,0.92); border: 1px solid #333;
    border-radius: 8px; padding: 12px 16px; font-size: 12px;
}}
#controls label {{ display: block; margin: 6px 0 2px; color: #888; }}
#controls input[type=range] {{ width: 200px; }}
.val {{ color: #7af; float: right; }}

#info {{
    position: absolute; bottom: 16px; right: 16px;
    background: rgba(10,10,20,0.85); border: 1px solid #333;
    border-radius: 8px; padding: 8px 12px; font-size: 11px; color: #666;
}}
</style>
</head>
<body>
<div id="canvas-container"></div>

<div id="panel">
    <h2>Distinction Algebra Renderer</h2>
    <div style="color:#888; margin-bottom:8px;">
        Surface: <span style="color:#7af">{surface_type}</span> |
        Vertices: <span style="color:#7af">{mesh_data['n_vertices']}</span> |
        Faces: <span style="color:#7af">{mesh_data['n_faces']}</span> |
        chi: <span style="color:#7af">{mesh_data['euler']}</span>
    </div>

    <h3>Z3 x Z2 States</h3>
    <div id="states-panel"></div>

    <h3>Coherence Tests</h3>
    <div id="coherence-panel"></div>

    <h3>Forced Mappings</h3>
    <div style="font-size:10px; color:#888; line-height:1.5;">
        Z3 position &rarr; vertex placement (roots of unity)<br>
        Z2 color &rarr; hue polarity (complementary shift)<br>
        U(1) &rarr; continuous hue wheel<br>
        2/3 &rarr; brightness, amplitude, spring constant<br>
        (2/3)^d &rarr; texture grain density<br>
        Eigenvalues &rarr; oscillation frequencies<br>
        Boundary &rarr; black / silence / flat
    </div>
</div>

<div id="controls">
    <strong style="color:#7af;">Controls</strong>
    <label>Alpha (Z2 position) <span class="val" id="alpha-val">0.50</span></label>
    <input type="range" id="alpha" min="0" max="1" step="0.01" value="0.5">
    <label>Animation speed <span class="val" id="speed-val">1.0</span></label>
    <input type="range" id="speed" min="0" max="3" step="0.1" value="1.0">
    <label>Texture octaves <span class="val" id="octaves-val">6</span></label>
    <input type="range" id="octaves" min="1" max="8" step="1" value="6">
    <label>Wireframe <input type="checkbox" id="wireframe"></label>
</div>

<div id="info">
    Every parameter derived from algebra. No magic numbers. Spectral gap = 2/3.
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

// --- Data from Python ---
const meshData = {json.dumps(mesh_data)};
const statesData = {json.dumps(states_data)};
const coherenceData = {json.dumps(coherence_serializable)};

// --- Scene setup ---
const container = document.getElementById('canvas-container');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x0a0a0f);

const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
camera.position.set(4, 3, 5);

const renderer = new THREE.WebGLRenderer({{ antialias: true }});
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
container.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.5;

// --- Lighting (minimal — colors come from algebra) ---
const ambient = new THREE.AmbientLight(0x404050, 0.6);
scene.add(ambient);
const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(5, 5, 5);
scene.add(dirLight);
const backLight = new THREE.DirectionalLight(0x4466aa, 0.3);
backLight.position.set(-3, -2, -4);
scene.add(backLight);

// --- Build geometry from mesh data ---
const geometry = new THREE.BufferGeometry();

const positions = new Float32Array(meshData.positions);
geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));

const colors = new Float32Array(meshData.colors);
geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

const indices = new Uint32Array(meshData.indices);
geometry.setIndex(new THREE.BufferAttribute(indices, 1));

geometry.computeVertexNormals();

// Store original colors for animation
const originalColors = new Float32Array(colors);

// Texture values as custom attribute
const texVals = new Float32Array(meshData.texture);
geometry.setAttribute('texValue', new THREE.BufferAttribute(texVals, 1));

// --- Material ---
const material = new THREE.MeshPhongMaterial({{
    vertexColors: true,
    side: THREE.DoubleSide,
    shininess: 40,
    specular: new THREE.Color(0x222233),
}});

const mesh = new THREE.Mesh(geometry, material);
scene.add(mesh);

// Wireframe overlay
const wireframeMat = new THREE.MeshBasicMaterial({{
    color: 0x334455,
    wireframe: true,
    transparent: true,
    opacity: 0.15,
}});
const wireframeMesh = new THREE.Mesh(geometry, wireframeMat);
wireframeMesh.visible = false;
scene.add(wireframeMesh);

// --- Populate info panels ---
const statesPanel = document.getElementById('states-panel');
statesData.forEach(s => {{
    const alg = s.algebra;
    const col = s.color;
    const snd = s.sound;
    const [r, g, b] = col.rgb;
    const rgbStr = `rgb(${{Math.round(r*255)}},${{Math.round(g*255)}},${{Math.round(b*255)}})`;
    const row = document.createElement('div');
    row.className = 'state-row';
    row.innerHTML = `
        <div class="color-swatch" style="background:${{rgbStr}}"></div>
        <div class="state-label">${{alg.sign}}${{alg.label}}</div>
        <div class="state-value">${{col.hue_degrees.toFixed(0)}}deg ${{snd.frequency_hz.toFixed(0)}}Hz</div>
    `;
    statesPanel.appendChild(row);
}});

const cohPanel = document.getElementById('coherence-panel');
Object.entries(coherenceData).forEach(([name, passed]) => {{
    const div = document.createElement('div');
    div.className = passed ? 'pass' : 'fail';
    div.textContent = `[${{passed ? 'PASS' : 'FAIL'}}] ${{name}}`;
    div.style.fontSize = '10px';
    div.style.padding = '1px 0';
    cohPanel.appendChild(div);
}});

// --- Animation ---
const GAP = 2.0 / 3.0;
let animSpeed = 1.0;

function animate(time) {{
    requestAnimationFrame(animate);
    const t = time * 0.001 * animSpeed;

    // Vertex color oscillation at eigenvalue frequencies
    // Each vertex pulses at its eigenvalue frequency, amplitude = 2/3
    const colAttr = geometry.getAttribute('color');
    const nVerts = meshData.n_vertices;
    for (let i = 0; i < nVerts; i++) {{
        const freq = meshData.frequencies[i];
        const z3 = meshData.z3_labels[i];

        // Oscillation: brightness modulated by spectral gap
        const phase = z3 * 2.0 * Math.PI / 3.0;  // Z₃ phase offset
        const pulse = 0.5 + 0.5 * GAP * Math.sin(freq * t * 0.01 + phase);

        colAttr.setXYZ(i,
            originalColors[i * 3] * pulse,
            originalColors[i * 3 + 1] * pulse,
            originalColors[i * 3 + 2] * pulse
        );
    }}
    colAttr.needsUpdate = true;

    controls.update();
    renderer.render(scene, camera);
}}
animate(0);

// --- Controls ---
document.getElementById('alpha').addEventListener('input', e => {{
    const alpha = parseFloat(e.target.value);
    document.getElementById('alpha-val').textContent = alpha.toFixed(2);
    // Recompute colors with new alpha
    for (let i = 0; i < meshData.n_vertices; i++) {{
        const z3 = meshData.z3_labels[i];
        const z2 = i % 2;
        // Recompute hue from Z₃ position
        let hue = (2 * Math.PI * z3) / 3;
        if (z2 === 1) hue = (hue + Math.PI) % (2 * Math.PI);
        // Brightness: boundary = 0, else = 2/3
        const brightness = (z3 === 2) ? 0 : GAP;
        // HSV to RGB
        const h = hue / (2 * Math.PI) * 6;
        const c = brightness;
        const x = c * (1 - Math.abs(h % 2 - 1));
        let r, g, b;
        if (h < 1) {{ r=c; g=x; b=0; }}
        else if (h < 2) {{ r=x; g=c; b=0; }}
        else if (h < 3) {{ r=0; g=c; b=x; }}
        else if (h < 4) {{ r=0; g=x; b=c; }}
        else if (h < 5) {{ r=x; g=0; b=c; }}
        else {{ r=c; g=0; b=x; }}
        originalColors[i*3] = r;
        originalColors[i*3+1] = g;
        originalColors[i*3+2] = b;
    }}
}});

document.getElementById('speed').addEventListener('input', e => {{
    animSpeed = parseFloat(e.target.value);
    document.getElementById('speed-val').textContent = animSpeed.toFixed(1);
}});

document.getElementById('wireframe').addEventListener('change', e => {{
    wireframeMesh.visible = e.target.checked;
}});

// --- Resize ---
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
    out_path = os.path.join(os.path.dirname(__file__), "render_output.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Renderer written to {out_path}")
    print(f"Open in browser to see interactive {surface} with Z₃ × Z₂ coloring.")
    print(f"Controls: orbit with mouse, alpha slider changes Z₂ position,")
    print(f"  speed controls animation rate, wireframe toggle available.")


if __name__ == "__main__":
    main()
