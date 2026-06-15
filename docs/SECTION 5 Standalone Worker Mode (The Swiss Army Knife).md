
***

<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

## <span style="color: #00BFFF;"><i class="fa-solid fa-toolbox"></i> SECTION 5: Standalone Worker Mode (The Swiss Army Knife)</span>

<!-- FLEXBOX BADGES (Perfectly Spaced & Formatted) -->
<div style="display: flex; gap: 12px; margin-top: 10px; margin-bottom: 25px; flex-wrap: wrap;">
  <img src="https://img.shields.io/badge/Mode-CLI_Worker-000000?style=for-the-badge&logo=gnometerminal&logoColor=white" alt="CLI Worker">
  <img src="https://img.shields.io/badge/Compute-Numba_JIT-00A6D6?style=for-the-badge&logo=python&logoColor=white" alt="Numba JIT">
  <img src="https://img.shields.io/badge/Concurrency-Multi--Processing-28A745?style=for-the-badge&logo=linux&logoColor=white" alt="Multi-Processing">
  <img src="https://img.shields.io/badge/Math-Deterministic-6F42C1?style=for-the-badge&logo=jupyter&logoColor=white" alt="Deterministic">
</div>

### <span style="color: #4682B4;"><i class="fa-solid fa-terminal"></i> 5.1 Introduction to the Deterministic Toolkit</span>

While AeroForgeX v4.0 is primarily an AI-driven Multidisciplinary Design Optimization (MDO) suite, booting up a multi-core PyMoo swarm is computational overkill for basic geometry tasks. 

If you simply want to scale an airfoil to 15% thickness, mathematically blend a root and tip shape together, or generate a quick aerodynamic Drag Polar, you use **Worker Mode**. By invoking the Command Line Interface (CLI) with the `-w` flag, you bypass the Artificial Intelligence entirely. The software transforms into a high-speed, deterministic aerospace geometry toolkit, executing raw Numba-accelerated calculus and Fortran fluid dynamics directly on your provided coordinate files.

<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin-bottom: 24px;">
  <h4 style="color: #1A1A1A; font-size: 1.1em; font-weight: 600; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;">
    <i class="fa-solid fa-terminal" style="color: #666666;"></i> 5.1.1 Base Command Syntax
  </h4>
  <div style="background-color: #FFFFFF; padding: 16px 20px; border-radius: 8px; border: 1px solid #EAEAEA; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
    <pre style="margin: 0px; color: #333333; font-family: 'SFMono-Regular', 'Consolas', 'Liberation Mono', Menlo, monospace; font-size: 0.9em; line-height: 1.5; overflow-x: auto;">
<span style="color: #A1A1AA; user-select: none;">$ </span><span style="color: #005CC5; font-weight: 600;">python</span> AeroForgeX_scr/aeroforgex_cli.py <span style="color: #22863A;">-w</span> &lt;action&gt; <span style="color: #22863A;">-a</span> &lt;airfoil_or_directory&gt; <span style="color: #6A737D;">[options]</span></pre>
  </div>
</div>

#### <span style="color: #1E90FF; font-weight: bold;"><i class="fa-solid fa-book"></i> 5.1.2 Exhaustive Worker Mode Arguments Glossary</span>

<div style="overflow-x: auto; border: 1px solid #E2E8F0; border-radius: 6px; margin-bottom: 25px;">
  <table style="width: 100%; border-collapse: collapse; margin: 0; font-size: 0.9em; background-color: #FFFFFF;">
    <thead>
      <tr style="background-color: #F8F9FA; color: #475569; text-align: left; border-bottom: 2px solid #E2E8F0;">
        <th style="padding: 12px; font-weight: bold;">Flag</th>
        <th style="padding: 12px; font-weight: bold;">Argument</th>
        <th style="padding: 12px; font-weight: bold;">Requirement</th>
        <th style="padding: 12px; font-weight: bold;">Description</th>
      </tr>
    </thead>
    <tbody style="color: #334155;">
      <tr style="border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 12px; font-family: monospace; font-weight: bold; color: #D97706;">-w</td>
        <td style="padding: 12px; font-family: monospace;">&lt;action&gt;</td>
        <td style="padding: 12px;"><span style="background-color: #FEE2E2; color: #991B1B; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; font-weight: bold;">Mandatory</span></td>
        <td style="padding: 12px;">The specific tool to execute (e.g., <code>norm</code>, <code>polar</code>, <code>bezier</code>, <code>generate</code>).</td>
      </tr>
      <tr style="border-bottom: 1px solid #E2E8F0; background-color: #F8FAFC;">
        <td style="padding: 12px; font-family: monospace; font-weight: bold; color: #D97706;">-a</td>
        <td style="padding: 12px; font-family: monospace;">&lt;filepath&gt;</td>
        <td style="padding: 12px;"><span style="background-color: #FEE2E2; color: #991B1B; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; font-weight: bold;">Mandatory</span></td>
        <td style="padding: 12px;">The primary Target Airfoil. <em>Passing a Directory triggers the Batch Pipeline.</em></td>
      </tr>
      <tr style="border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 12px; font-family: monospace; font-weight: bold; color: #D97706;">-a2</td>
        <td style="padding: 12px; font-family: monospace;">&lt;filepath&gt;</td>
        <td style="padding: 12px;"><span style="background-color: #FEF3C7; color: #92400E; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; font-weight: bold;">Conditional</span></td>
        <td style="padding: 12px;">The secondary Target Airfoil. <em>Required exclusively for the <code>blend</code> action.</em></td>
      </tr>
      <tr style="border-bottom: 1px solid #E2E8F0; background-color: #F8FAFC;">
        <td style="padding: 12px; font-family: monospace; font-weight: bold; color: #D97706;">-i</td>
        <td style="padding: 12px; font-family: monospace;">&lt;filepath.json&gt;</td>
        <td style="padding: 12px;"><span style="background-color: #FEF3C7; color: #92400E; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; font-weight: bold;">Conditional</span></td>
        <td style="padding: 12px;">Config file. <em>Required for <code>flap</code>, <code>polar</code>, and <code>check</code> to import parameters.</em></td>
      </tr>
      <tr style="border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 12px; font-family: monospace; font-weight: bold; color: #D97706;">-o</td>
        <td style="padding: 12px; font-family: monospace;">&lt;string&gt;</td>
        <td style="padding: 12px;"><span style="background-color: #E0E7FF; color: #3730A3; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; font-weight: bold;">Optional</span></td>
        <td style="padding: 12px;">Filename prefix for the output. If omitted, appends a default suffix (e.g., <code>_norm</code>).</td>
      </tr>
      <tr style="border-bottom: 1px solid #E2E8F0; background-color: #F8FAFC;">
        <td style="padding: 12px; font-family: monospace; font-weight: bold; color: #D97706;">-r</td>
        <td style="padding: 12px; font-family: monospace;">&lt;float&gt;</td>
        <td style="padding: 12px;"><span style="background-color: #E0E7FF; color: #3730A3; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; font-weight: bold;">Optional</span></td>
        <td style="padding: 12px;">Reynolds override specifically for <code>polar</code> actions if a JSON file is not provided.</td>
      </tr>
      <tr style="border-bottom: 1px solid #E2E8F0;">
        <td style="padding: 12px; font-family: monospace; font-weight: bold; color: #D97706;">-ar</td>
        <td style="padding: 12px; font-family: monospace;">&lt;string&gt;</td>
        <td style="padding: 12px;"><span style="background-color: #E0E7FF; color: #3730A3; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; font-weight: bold;">Optional</span></td>
        <td style="padding: 12px;">Alpha Range Override. Format: <code>min:max:step</code> (e.g., <code>-5:15:0.5</code>).</td>
      </tr>
      <tr>
        <td style="padding: 12px; font-family: monospace; font-weight: bold; color: #D97706;">[val]</td>
        <td style="padding: 12px; font-family: monospace;">&lt;string&gt;</td>
        <td style="padding: 12px;"><span style="background-color: #FEF3C7; color: #92400E; padding: 2px 6px; border-radius: 4px; font-size: 0.85em; font-weight: bold;">Conditional</span></td>
        <td style="padding: 12px;">Trailing positional argument used strictly by <code>set</code>, <code>blend</code>, <code>smooth</code>, and <code>generate</code>.</td>
      </tr>
    </tbody>
  </table>
</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-server"></i> 5.2 The Batch Pipeline Interceptor</span>

Historically, aerodynamicists working with databases (like the UIUC Airfoil Data Site) had to write custom shell scripts to process multiple airfoils sequentially. AeroForgeX v4.0 introduces the **Batch Pipeline Interceptor**. If you pass a **Directory Path** to the `-a` argument instead of a single `.dat` file, the orchestrator automatically engages Batch Mode.

<div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 18px; border-radius: 6px; margin-top: 15px; margin-bottom: 25px;">
  <p style="margin-top: 0px; margin-bottom: 10px; color: #475569; font-weight: bold;"><i class="fa-solid fa-microchip"></i> Under the Hood:</p>
  <p style="margin-top: 0px; margin-bottom: 15px; font-size: 0.95em; color: #444; line-height: 1.6;">The Python script uses <code>glob</code> to map every <code>.dat</code>, <code>.bez</code>, and <code>.hicks</code> file in the target folder. It deep-copies your command-line arguments, queries your OS for available CPU cores, and spawns a massive multiprocessing pool (<code>pool.map</code>). It processes dozens of airfoils simultaneously and safely deposits them into a newly generated <code>Worker_Batch_Output/</code> subfolder, ensuring your raw files are never corrupted.</p>

  <h5 style="margin-top: 0px; margin-bottom: 5px; color: #0F172A;"><i class="fa-solid fa-folder-tree"></i> Example 1: Batch Database Normalization</h5>
  <p style="margin-top: 0px; margin-bottom: 8px; font-size: 0.9em; color: #64748B;">You downloaded an entire folder of 300 raw, un-normalized historical airfoils from the UIUC database.</p>
  <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px 0px 15px 0px; border: 1px solid #333; line-height: 1.5;">python AeroForgeX_scr/aeroforgex_cli.py -w norm -a Airfoils/Raw_Database/</pre>

  <h5 style="margin-top: 0px; margin-bottom: 5px; color: #0F172A;"><i class="fa-solid fa-chart-line"></i> Example 2: Batch Polar Generation (Data Science Mining)</h5>
  <p style="margin-top: 0px; margin-bottom: 8px; font-size: 0.9em; color: #64748B;">You want to evaluate 50 different airfoils at $Re = 500k$ to train an ML model, outputting directly to CSV.</p>
  <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px; border: 1px solid #333; line-height: 1.5;">python AeroForgeX_scr/aeroforgex_cli.py -w polar-csv -i Json_Input/Worker_Mode/sweep.json -a Airfoils/Raw_Database/</pre>
</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-broom"></i> 5.3 Topological Sanitization & Mesh Control</span>

Raw airfoil coordinate files—especially those digitized from historical wind-tunnel reports or CAD—are notoriously dirty. Feeding an irregularly spaced mesh into a Navier-Stokes solver will cause the mathematical pressure gradients to explode.

<div style="display: flex; flex-direction: column; gap: 15px; margin-top: 15px; margin-bottom: 25px;">

  <!-- NORM CARD -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 12px; color: #475569;"><i class="fa-solid fa-ruler-combined"></i> Absolute Boundary Normalization (<code>-w norm</code>)</h4>
    <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.95em; color: #444; line-height: 1.6;">
      <strong><i class="fa-solid fa-microchip"></i> Under the Hood:</strong> Applies a translation matrix to move the absolute minimum $X$ to exactly $(0,0)$, and a rotational matrix to lock the trailing edge to $(1,0)$. It then uses <strong>NASA Arc-Cosine Clustering</strong> to map the discrete points onto a continuous spline, packing 40% of the mesh points into the first 10% of the chord to resolve the leading-edge suction peak.
    </p>
    <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px; border: 1px solid #333; line-height: 1.5; white-space: pre-wrap;"><span style="color: #6A9955;">&#35; Fix a wonky CAD export</span>
python AeroForgeX_scr/aeroforgex_cli.py -w norm -a Airfoils/CAD_Export.dat -o CAD_Clean
<br><span style="color: #6A9955;">&#35; Dense CFD Repaneling (e.g. 250 points defined in JSON)</span>
python AeroForgeX_scr/aeroforgex_cli.py -w norm -i  json_Input/Worker_Mode/config.json -a Airfoils/NACA0012.dat</pre>
  </div>

  <!-- SMOOTH CARD -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 12px; color: #475569;"><i class="fa-solid fa-wave-square"></i> Savitzky-Golay Mathematical Filter (<code>-w smooth</code>)</h4>
    <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.95em; color: #444; line-height: 1.6;">
      <strong><i class="fa-solid fa-microchip"></i> Under the Hood:</strong> Applies a discrete <code>scipy.signal.savgol_filter</code>. It fits a 3rd-degree polynomial to adjacent data points in a sliding window, mathematically stripping away high-frequency numerical noise while perfectly preserving the macroscopic aerodynamic shape.
    </p>
    <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px; border: 1px solid #333; line-height: 1.5; white-space: pre-wrap;"><span style="color: #6A9955;">&#35; Light Smoothing (Window=7) for clean wind tunnel scans</span>
python AeroForgeX_scr/aeroforgex_cli.py -w smooth 7 -a Airfoils/WindTunnel_Scan.dat
<br><span style="color: #6A9955;">&#35; Heavy Smoothing (Window=21) for jagged, optically-scanned 1940s PDFs</span>
python AeroForgeX_scr/aeroforgex_cli.py -w smooth 21 -a Airfoils/Old_PDF_Scan.dat</pre>
  </div>

</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-stethoscope"></i> 5.4 High-Fidelity Diagnostics & Restoration</span>

Before running aerodynamics, you must know if the shape is mathematically sound.

<div style="display: flex; flex-direction: column; gap: 15px; margin-top: 15px; margin-bottom: 25px;">

  <!-- CHECK CARD -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #475569;"><i class="fa-solid fa-magnifying-glass-chart"></i> Topological Terminal Diagnostics (<code>-w check</code>)</h4>
    <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.9em; color: #444;">Converts coordinates into a 2D B-Spline, calculates exact 2nd-derivative curvature, and prints a terminal report counting <strong>Macro-Reversals</strong> and <strong>Micro-Spikes</strong>.</p>
    <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px; border: 1px solid #333; line-height: 1.5;">python AeroForgeX_scr/aeroforgex_cli.py -w check -i json_Input/Worker_Mode/config.json -a Airfoils/MyFoil.dat</pre>
  </div>

  <!-- REPORT CARD -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #475569;"><i class="fa-solid fa-file-pdf"></i> Dual PDF/HTML Reporting (<code>-w report</code>)</h4>
    <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.9em; color: #444;">Generates an interactive Plotly HTML dashboard and a high-resolution Matplotlib PDF perfectly formatted for inclusion in IEEE academic research papers.</p>
    <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px; border: 1px solid #333; line-height: 1.5;">python AeroForgeX_scr/aeroforgex_cli.py -w report -a Airfoils/MyFoil.dat</pre>
  </div>

  <!-- BEZIER CARD -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #475569;"><i class="fa-solid fa-bezier-curve"></i> Nelder-Mead "Shrink-Wrap" (<code>-w bezier</code>)</h4>
    <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.9em; color: #444;">A salvage operation. Drops a blank Bezier curve over corrupted coordinates, using the Nelder-Mead Simplex Algorithm to warp the control points until $L^2$ deviation is minimized.</p>
    <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px; border: 1px solid #333; line-height: 1.5; white-space: pre-wrap;"><span style="color: #6A9955;">&#35; Salvaging a complex Supercritical foil (requires 12 control points)</span>
python AeroForgeX_scr/aeroforgex_cli.py -w bezier -i json_Input/Worker_Mode/complex.json -a Airfoils/Corrupted_Jet.dat</pre>
  </div>

</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-cubes"></i> 5.5 Parametric Geometry Morphing (CAD-less Editing)</span>

Perform complex geometric scaling directly in the terminal in fractions of a second, entirely eliminating the need for SolidWorks or CATIA for basic operations.

<div style="display: flex; flex-direction: column; gap: 15px; margin-top: 15px; margin-bottom: 25px;">

  <!-- SET CARD -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 12px; color: #475569;"><i class="fa-solid fa-compress"></i> Direct Geometric Scaling (<code>-w set</code>)</h4>
    <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.95em; color: #444; line-height: 1.6;">
      <strong><i class="fa-solid fa-microchip"></i> Under the Hood:</strong> Uses a localized natural cubic spline and a <strong>strictly monotonic enforcement algorithm</strong> to elastically stretch coordinates. This prevents the leading-edge radius from distorting and prevents meshes from crossing over.
    </p>
    <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px; border: 1px solid #333; line-height: 1.5; white-space: pre-wrap;"><span style="color: #6A9955;">&#35; Scale absolute thickness to 18.5%</span>
python AeroForgeX_scr/aeroforgex_cli.py -w set t=18.5 -a Airfoils/NACA0012.dat
<br><span style="color: #6A9955;">&#35; Shift maximum camber aft to 45% of the chord</span>
python AeroForgeX_scr/aeroforgex_cli.py -w set xc=45 -a Airfoils/Glider_Wing.dat
<br><span style="color: #6A9955;">&#35; Force a 0.5% blunt wedge at the Trailing Edge for 3D printing</span>
python AeroForgeX_scr/aeroforgex_cli.py -w set te=0.5 -a Airfoils/UAV_Wing.dat</pre>
  </div>

  <!-- GENERATE CARD -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #475569;"><i class="fa-solid fa-layer-group"></i> Automated Family Generation (<code>-w generate</code>)</h4>
    <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.9em; color: #444;">Instantly generates a Parametric Family for 3D lofting by looping the <code>set</code> logic. Syntax: <code>[property]=[min]:[max]:[steps]</code>.</p>
    <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px; border: 1px solid #333; line-height: 1.5; white-space: pre-wrap;"><span style="color: #6A9955;">&#35; Generate 5 lofting stations scaling from 10% to 20% thickness</span>
python AeroForgeX_scr/aeroforgex_cli.py -w generate t=10:20:5 -a Airfoils/BaseWing.dat</pre>
  </div>

  <!-- BLEND CARD -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #475569;"><i class="fa-solid fa-object-group"></i> Mesh Interpolation & Fusing (<code>-w blend</code>)</h4>
    <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.9em; color: #444;">Uses a 1D linear interpolation matrix to map Foil B onto the exact grid of Foil A, then applies a weighted morphing algorithm.</p>
    <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px; border: 1px solid #333; line-height: 1.5; white-space: pre-wrap;"><span style="color: #6A9955;">&#35; Creates an 80% Root / 20% Tip blended airfoil</span>
python AeroForgeX_scr/aeroforgex_cli.py -w blend 20 -a Airfoils/Root.dat -a2 Airfoils/Tip.dat</pre>
  </div>

</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-plane-tail"></i> 5.6 Kinematic Trailing Edge Deflection (<code>-w flap</code>)</span>

<div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; margin-top: 15px; margin-bottom: 25px;">
  <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.95em; color: #444; line-height: 1.6;">
    <strong><i class="fa-solid fa-microchip"></i> Under the Hood:</strong> Uses a pure Python <strong>Cartesian Rotation Matrix</strong>. It isolates coordinates aft of the hinge, translates them to the origin $(0,0)$, rotates them via $[x\cos\theta - y\sin\theta]$ and $[x\sin\theta + y\cos\theta]$, and translates them back to their physical location.
  </p>
  <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px; border: 1px solid #333; line-height: 1.5; white-space: pre-wrap;"><span style="color: #6A9955;">&#35; If JSON has "flap_angle": [-5.0, 0.0, 5.0, 15.0], it auto-exports all 4 for CAD</span>
python AeroForgeX_scr/aeroforgex_cli.py -w flap -i  json_Input/Worker_Mode/config.json -a Airfoils/NACA0012.dat</pre>
</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-wind"></i> 5.7 The Flight Envelope Mapper</span>

Automatically execute massive, multi-dimensional Aerodynamic Sweeps, cross-multiplying your requested **Flap Angles $\times$ Reynolds Numbers $\times$ Mach Numbers**.

<div style="display: flex; flex-direction: column; gap: 15px; margin-top: 15px; margin-bottom: 25px;">

  <!-- POLAR CARD -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #475569;"><i class="fa-solid fa-file-lines"></i> The 3D Lifting-Line Standard (<code>-w polar</code>)</h4>
    <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.9em; color: #444;">Outputs individual <code>.dat</code> text files formatted with strict space-delimiters. Perfect for dragging-and-dropping directly into XFLR5 or Flow5.</p>
    <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px; border: 1px solid #333; line-height: 1.5;">python AeroForgeX_scr/aeroforgex_cli.py -w polar -i json_Input/Worker_Mode/sweep.json -a Airfoils/MyFoil.dat</pre>
  </div>

  <!-- POLAR CSV CARD -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #475569;"><i class="fa-solid fa-table"></i> The Data Science Standard (<code>-w polar-csv</code>)</h4>
    <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.9em; color: #444;">Appends all data across all flight regimes into a massive, semicolon-delimited <code>master_polar.csv</code>, and triggers the Interactive HTML Dashboard generation. Perfect for Excel/Pandas.</p>
    <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px; border: 1px solid #333; line-height: 1.5; white-space: pre-wrap;"><span style="color: #6A9955;">&#35; Execute with an Alpha Range (-ar) override from -5 to 25 degrees</span>
python AeroForgeX_scr/aeroforgex_cli.py -w polar-csv -i sweep.json -a Airfoils/MyFoil.dat -ar -5:25:0.5</pre>
  </div>

</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-shield-halved"></i> 5.8 Configuration Validation (<code>-w check-input</code>)</span>

<div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; margin-top: 15px; margin-bottom: 25px;">
  <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.95em; color: #444; line-height: 1.6;">
    <strong><i class="fa-solid fa-microchip"></i> Under the Hood:</strong> A highly effective dry-run parser. Reads your JSON file, validates syntax, checks for missing commas, ensures array lengths perfectly match (e.g., 3 Reynolds numbers for 3 Operating Points), and verifies constraints do not conflict with fluid dynamics laws.
  </p>
  <pre style="background-color: #1E1E1E; color: #D4D4D4; padding: 12px; border-radius: 4px; font-family: monospace; font-size: 0.85em; margin: 0px; border: 1px solid #333; line-height: 1.5; white-space: pre-wrap;"><span style="color: #6A9955;">&#35; ALWAYS run this before launching a 12-hour HPC optimization</span>
python AeroForgeX_scr/aeroforgex_cli.py -w check-input -i json_Input/Worker_Mode/massive_matrix.json -a Airfoils/NACA0012.dat</pre>
</div>