"""
Fractal Renderer — Property 9: Self-recursive distinction.

The distinction operator applied to its own output creates fractal structure:
  Level 0: 1 region (the whole)
  Level 1: 3 regions (thing, complement, boundary) — boundary absorbed
  Level 2: 9 sub-regions (3 × live only) → 4 live + boundary grid
  Level n: 3^n regions, (2/3)^n live fraction

This IS the Cantor set construction in 2D (Sierpinski-like).
Fractal dimension = log(2)/log(3) ≈ 0.631 (forced, not chosen).

Every parameter derived:
  - Subdivision factor: 3 (from Z₃)
  - Survival rate: 2/3 (spectral gap)
  - Colors: Z₃ × Z₂ → U(1) hue wheel
  - Scale factor per level: 1/3 (Z₃ lattice spacing)

Usage:
    python demos/fractal_renderer.py          # generates fractal_output.html
    python demos/fractal_renderer.py --depth 8  # deeper recursion
"""

import sys
import os
import json
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from algebra.sensory_manifold import DistinctionState


def generate_fractal_data(max_depth: int = 7) -> dict:
    """Generate the recursive distinction fractal.

    At each level, a square is divided into a 3×3 grid (Z₃ × Z₃).
    The center cell is the "boundary" — it gets absorbed (removed).
    The 8 remaining cells are "live" — they recurse.

    But this isn't arbitrary Sierpinski. The absorption pattern follows
    the Z₃ algebra: position 2 (boundary) is absorbed. The remaining
    positions 0 (thing) and 1 (complement) survive.

    In 2D: Z₃ × Z₃ grid, boundary cells are those where EITHER
    coordinate is 2 (boundary). This gives 4 live cells out of 9.
    Live fraction = 4/9 = (2/3)² — exactly (2/3)^d for d=2.
    """
    # Precompute which cells survive at each level
    # In Z₃×Z₃: cell (i,j) survives if neither i nor j is the boundary (2)
    live_cells = []
    for i in range(3):
        for j in range(3):
            if i != 2 and j != 2:  # boundary absorption
                live_cells.append((i, j))
    # live_cells = [(0,0), (0,1), (1,0), (1,1)] — 4 cells, live fraction = 4/9

    # Generate all live rectangles at given depth
    rectangles = []

    def recurse(x, y, size, depth, z3_major, z3_minor):
        if depth >= max_depth:
            # Leaf node — record rectangle with color
            state = DistinctionState(
                position=z3_major % 3,
                color=(z3_major + z3_minor) % 2,
                alpha=0.5
            )
            r, g, b = state.rgb()
            rectangles.append({
                "x": x, "y": y, "w": size, "h": size,
                "depth": depth,
                "z3": z3_major % 3,
                "r": r, "g": g, "b": b,
                "alive": state.is_alive(),
            })
            return

        cell_size = size / 3
        for i, j in live_cells:
            recurse(
                x + i * cell_size,
                y + j * cell_size,
                cell_size,
                depth + 1,
                z3_major=(z3_major * 3 + i) % 3,
                z3_minor=(z3_minor * 3 + j) % 3,
            )

    recurse(0, 0, 1.0, 0, 0, 0)

    # Compute statistics
    total_cells = len(rectangles)
    live_fraction = (2.0 / 3.0) ** (2 * max_depth)  # (2/3)^(2d) in 2D
    fractal_dim = np.log(4) / np.log(3)  # log(live_cells)/log(subdivision) in 2D

    return {
        "rectangles": rectangles,
        "max_depth": max_depth,
        "total_cells": total_cells,
        "live_fraction_theoretical": live_fraction,
        "fractal_dimension": fractal_dim,
        "live_cells_per_level": len(live_cells),
        "subdivision_factor": 3,
        "spectral_gap": 2.0 / 3.0,
    }


def generate_html(max_depth: int = 7) -> str:
    """Generate self-contained HTML with interactive fractal zoom."""
    data = generate_fractal_data(max_depth)

    # For deep fractals, only send leaf-level rects (the rest are implied)
    rects_json = json.dumps(data["rectangles"])

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Distinction Fractal — Property 9: Self-Recursive</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ background: #060610; color: #ccc; font-family: 'Courier New', monospace; overflow: hidden; }}
canvas {{ display: block; cursor: crosshair; }}

#panel {{
    position: absolute; top: 12px; right: 12px; width: 320px;
    background: rgba(6,6,16,0.92); border: 1px solid #2a2a3a;
    border-radius: 6px; padding: 14px; font-size: 11px;
}}
#panel h2 {{ color: #f7a; font-size: 13px; margin-bottom: 8px; }}
.metric {{ display: flex; justify-content: space-between; padding: 2px 0; }}
.label {{ color: #777; }}
.value {{ color: #adf; font-weight: bold; }}
.section {{ border-top: 1px solid #1a1a2a; margin-top: 8px; padding-top: 8px; }}
.section-title {{ color: #888; font-size: 10px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }}

#zoom-bar {{
    width: 100%; height: 6px; background: #111;
    border-radius: 3px; overflow: hidden; margin: 4px 0;
}}
#zoom-fill {{
    height: 100%; background: linear-gradient(90deg, #a4f, #4af);
    width: 10%; transition: width 0.2s;
}}

#legend {{
    position: absolute; bottom: 12px; left: 12px;
    background: rgba(6,6,16,0.9); border: 1px solid #2a2a3a;
    border-radius: 6px; padding: 10px 14px; font-size: 11px;
}}
.legend-row {{ display: flex; align-items: center; gap: 6px; padding: 2px 0; }}
.legend-swatch {{ width: 14px; height: 14px; border-radius: 2px; border: 1px solid #333; }}

#instructions {{
    position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%);
    background: rgba(6,6,16,0.85); border: 1px solid #2a2a3a;
    border-radius: 6px; padding: 6px 14px; font-size: 10px; color: #555;
}}
</style>
</head>
<body>
<canvas id="canvas"></canvas>

<div id="panel">
    <h2>Property 9: Self-Recursive Fractal</h2>
    <div style="color:#888; margin-bottom:6px; font-size:10px;">
        Distinction operator applied to its own output
    </div>

    <div class="metric">
        <span class="label">Recursion depth</span>
        <span class="value">{data['max_depth']}</span>
    </div>
    <div class="metric">
        <span class="label">Total cells</span>
        <span class="value" id="cell-count">{data['total_cells']}</span>
    </div>
    <div class="metric">
        <span class="label">Fractal dimension</span>
        <span class="value">log(4)/log(3) = {data['fractal_dimension']:.4f}</span>
    </div>
    <div class="metric">
        <span class="label">Live fraction (2/3)^2d</span>
        <span class="value">{data['live_fraction_theoretical']:.2e}</span>
    </div>
    <div class="metric">
        <span class="label">Subdivision</span>
        <span class="value">3 (Z3 lattice)</span>
    </div>
    <div class="metric">
        <span class="label">Survival per level</span>
        <span class="value">4/9 = (2/3)^2</span>
    </div>

    <div class="section">
        <div class="section-title">Zoom</div>
        <div class="metric">
            <span class="label">Level</span>
            <span class="value" id="zoom-level">1.0x</span>
        </div>
        <div id="zoom-bar"><div id="zoom-fill"></div></div>
        <div style="color:#555; font-size:9px;">Scroll to zoom, drag to pan</div>
    </div>

    <div class="section">
        <div class="section-title">Why This Fractal is Forced</div>
        <div style="color:#666; font-size:10px; line-height:1.5;">
            O1: Distinction creates 3 (Z3) &rarr; 3x3 grid<br>
            O3: Boundary absorbs &rarr; center column/row removed<br>
            (2/3)^d: Live fraction at dimension d<br>
            Self-application: each live cell IS another distinction<br>
            dim = log(4)/log(3) &asymp; 1.26 (Hausdorff, 2D)<br>
            <br>
            The fractal IS the algebra looking at itself.
        </div>
    </div>
</div>

<div id="legend">
    <div style="color:#888; font-size:10px; margin-bottom:4px;">Z3 x Z2 COLORING</div>
    <div class="legend-row">
        <div class="legend-swatch" style="background:rgb(170,0,0);"></div>
        <span>+thing (Z3=0, Z2=+)</span>
    </div>
    <div class="legend-row">
        <div class="legend-swatch" style="background:rgb(0,170,0);"></div>
        <span>+complement (Z3=1, Z2=+)</span>
    </div>
    <div class="legend-row">
        <div class="legend-swatch" style="background:rgb(0,0,170);"></div>
        <span>-thing (Z3=0, Z2=-)</span>
    </div>
    <div class="legend-row">
        <div class="legend-swatch" style="background:rgb(170,170,0);"></div>
        <span>-complement (Z3=1, Z2=-)</span>
    </div>
    <div class="legend-row">
        <div class="legend-swatch" style="background:rgb(0,0,0);"></div>
        <span>boundary (absorbed)</span>
    </div>
</div>

<div id="instructions">
    Scroll: zoom into self-similar structure | Drag: pan | Every level is the same distinction
</div>

<script>
const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');

// Fractal data
const rects = {rects_json};
const DEPTH = {data['max_depth']};
const GAP = 2.0 / 3.0;

// Viewport
let viewX = 0, viewY = 0, viewScale = 1.0;
let canvasW, canvasH;

function resize() {{
    canvasW = window.innerWidth;
    canvasH = window.innerHeight;
    canvas.width = canvasW;
    canvas.height = canvasH;
    draw();
}}

function worldToScreen(wx, wy) {{
    const size = Math.min(canvasW, canvasH) * 0.85;
    const ox = (canvasW - size) / 2;
    const oy = (canvasH - size) / 2;
    return [
        ox + (wx - viewX) * size * viewScale,
        oy + (wy - viewY) * size * viewScale
    ];
}}

function draw() {{
    ctx.fillStyle = '#060610';
    ctx.fillRect(0, 0, canvasW, canvasH);

    const size = Math.min(canvasW, canvasH) * 0.85;
    let rendered = 0;

    for (const rect of rects) {{
        const [sx, sy] = worldToScreen(rect.x, rect.y);
        const sw = rect.w * size * viewScale;
        const sh = rect.h * size * viewScale;

        // Culling: skip if off-screen
        if (sx + sw < 0 || sy + sh < 0 || sx > canvasW || sy > canvasH) continue;
        // Skip sub-pixel rectangles
        if (sw < 0.5 && sh < 0.5) continue;

        const r = Math.round(rect.r * 255);
        const g = Math.round(rect.g * 255);
        const b = Math.round(rect.b * 255);

        if (rect.alive) {{
            ctx.fillStyle = `rgb(${{r}},${{g}},${{b}})`;
        }} else {{
            ctx.fillStyle = '#000';
        }}
        ctx.fillRect(sx, sy, Math.max(sw, 0.5), Math.max(sh, 0.5));

        // Border at larger sizes
        if (sw > 4) {{
            ctx.strokeStyle = 'rgba(255,255,255,0.08)';
            ctx.lineWidth = 0.5;
            ctx.strokeRect(sx, sy, sw, sh);
        }}

        rendered++;
    }}

    // Zoom info
    document.getElementById('zoom-level').textContent = viewScale.toFixed(1) + 'x';
    const maxZoom = Math.pow(3, DEPTH);
    const pct = Math.log(viewScale) / Math.log(maxZoom) * 100;
    document.getElementById('zoom-fill').style.width = Math.max(pct, 2) + '%';
}}

// --- Zoom ---
canvas.addEventListener('wheel', (e) => {{
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 1 / 1.15 : 1.15;

    // Zoom toward mouse position
    const size = Math.min(canvasW, canvasH) * 0.85;
    const ox = (canvasW - size) / 2;
    const oy = (canvasH - size) / 2;

    const mouseWX = (e.clientX - ox) / (size * viewScale) + viewX;
    const mouseWY = (e.clientY - oy) / (size * viewScale) + viewY;

    viewScale *= zoomFactor;
    viewScale = Math.max(0.5, Math.min(viewScale, Math.pow(3, DEPTH + 1)));

    viewX = mouseWX - (e.clientX - ox) / (size * viewScale);
    viewY = mouseWY - (e.clientY - oy) / (size * viewScale);

    draw();
}});

// --- Pan ---
let isPanning = false, panStartX, panStartY, panViewX, panViewY;

canvas.addEventListener('mousedown', (e) => {{
    isPanning = true;
    panStartX = e.clientX;
    panStartY = e.clientY;
    panViewX = viewX;
    panViewY = viewY;
}});

canvas.addEventListener('mousemove', (e) => {{
    if (!isPanning) return;
    const size = Math.min(canvasW, canvasH) * 0.85;
    const dx = (e.clientX - panStartX) / (size * viewScale);
    const dy = (e.clientY - panStartY) / (size * viewScale);
    viewX = panViewX - dx;
    viewY = panViewY - dy;
    draw();
}});

canvas.addEventListener('mouseup', () => {{ isPanning = false; }});
canvas.addEventListener('mouseleave', () => {{ isPanning = false; }});

// --- Init ---
window.addEventListener('resize', resize);
resize();
</script>
</body>
</html>"""


def main():
    max_depth = 7
    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--depth" and i + 2 < len(sys.argv):
            max_depth = int(sys.argv[i + 2])

    html = generate_html(max_depth)
    out_path = os.path.join(os.path.dirname(__file__), "fractal_output.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    data = generate_fractal_data(max_depth)
    print(f"Fractal renderer: {out_path}")
    print(f"Depth: {max_depth}")
    print(f"Total cells: {data['total_cells']}")
    print(f"Fractal dimension: log(4)/log(3) = {data['fractal_dimension']:.4f}")
    print(f"Live fraction: (2/3)^{2*max_depth} = {data['live_fraction_theoretical']:.2e}")
    print()
    print("Self-recursion structure:")
    print(f"  Level 0: 1 region (the whole space)")
    for d in range(1, min(max_depth + 1, 6)):
        cells = 4 ** d
        fraction = (4.0 / 9.0) ** d
        print(f"  Level {d}: {cells} live cells, fraction = {fraction:.6f}")
    if max_depth > 5:
        cells = 4 ** max_depth
        fraction = (4.0 / 9.0) ** max_depth
        print(f"  ...")
        print(f"  Level {max_depth}: {cells} live cells, fraction = {fraction:.2e}")
    print()
    print("Every level is the SAME operation: distinguish → absorb boundary → recurse.")
    print("The fractal IS the algebra's self-portrait.")


if __name__ == "__main__":
    main()
