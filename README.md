

***

<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

<div align="center">

<h1 style="color: #1E90FF; font-size: 3em; margin-bottom: 0px;"><i class="fa-solid fa-plane-up"></i> AeroForgeX</h1>
<p style="color: #708090; font-size: 1.3em; font-style: italic; font-weight: bold; margin-top: 5px;">Enterprise-Grade Multidisciplinary Airfoil Optimization & Analysis Suite</p>

<!-- FLEXBOX BADGES (Perfectly Spaced & Formatted) -->
<div style="display: flex; justify-content: center; gap: 12px; margin-top: 15px; margin-bottom: 25px; flex-wrap: wrap;">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9+"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-F7DF1E?style=for-the-badge&logo=opensourceinitiative&logoColor=black" alt="License: MIT"></a>
  <a href="https://numba.pydata.org/"><img src="https://img.shields.io/badge/Numba-Accelerated-00A3E0?style=for-the-badge&logo=numba&logoColor=white" alt="Numba"></a>
  <a href="https://pymoo.org/"><img src="https://img.shields.io/badge/Optimization-PyMoo-FF8C00?style=for-the-badge&logo=python&logoColor=white" alt="PyMoo"></a>
  <a href="https://streamlit.io/"><img src="https://img.shields.io/badge/UI-Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit"></a>
</div>

```text
========================================================================================
   █████╗ ███████╗██████╗  ██████╗ ███████╗ ██████╗ ██████╗  ██████╗ ███████╗██╗  ██╗
  ██╔══██╗██╔════╝██╔══██╗██╔═══██╗██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝╚██╗██╔╝
  ███████║█████╗  ██████╔╝██║   ██║█████╗  ██║   ██║██████╔╝██║  ███╗█████╗   ╚███╔╝ 
  ██╔══██║██╔══╝  ██╔══██╗██║   ██║██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝   ██╔██╗ 
  ██║  ██║███████╗██║  ██║╚██████╔╝██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗██╔╝ ██╗
  ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝
========================================================================================
                          AeroForgeX v4.0 Pro | Memetic AI | Surrogate CFD | HPC Parallel
                        Advanced Airfoil Optimization Suite | v4.0 Numba/PyMoo
                         DEVELOPER: Gamil Abdullah Al-Sharif & Yhya Abdullah Al-Wazir
                               Contact: mely104haja@gmail.com
========================================================================================
```
</div>

---

## <span style="color: #00BFFF;"><i class="fa-solid fa-book-open"></i> 1. Executive Summary</span>

**AeroForgeX** is a state-of-the-art, high-fidelity Multidisciplinary Design Optimization (MDO) suite engineered specifically for the automated generation, refinement, and analysis of 2D aerodynamic profiles. 

Built upon the robust fluid-mechanics foundation of the acclaimed *Xoptfoil2* (Fortran), AeroForgeX completely re-architects the optimization workflow in Python. It bridges the critical and historically fragile gap between abstract artificial intelligence, rigid non-linear fluid mechanics, and strict structural engineering constraints.

<div style="background-color: #f8f9fa; border-left: 4px solid #1E90FF; padding: 15px; border-radius: 4px; color: #333; margin-top: 15px;">
  <strong><i class="fa-solid fa-industry" style="color: #4682B4;"></i> Industrial Application:</strong> Whether you are designing a low-Reynolds-number UAV wing, a heavily cambered wind turbine root designed to house massive carbon-fiber spars, or a shock-mitigating transonic airfoil, AeroForgeX automates the highly complex, non-linear process of fluid-dynamic shape optimization. It translates human engineering intent into a highly parallelized, C-speed computational pipeline.
</div>

---

## <span style="color: #00BFFF;"><i class="fa-solid fa-star"></i> 2. Key Features of AeroForgeX</span>

AeroForgeX is not just a script; it is a full-stack engineering ecosystem combining UI, machine learning, and raw physics.

*   🌐 **<span style="color: #FF4B4B;">The Streamlit Web Ecosystem:</span>** A beautiful, 4-tab interactive web GUI running locally. Visually configure hyper-parameters, live-plot seed airfoils, deploy multiprocessing optimization swarms, and view interactive HTML reports directly in your browser.
*   🧠 **<span style="color: #9370DB;">Dual Aerodynamic Physics Engines:</span>** 
    *   **XFOIL:** Thread-safe Fortran subprocess wrapping with infinite-loop assassins and regex parsing.
    *   **NeuralFoil (AI Surrogate):** A CNN evaluating aerodynamic tensors in milliseconds, featuring an Implicit Secant Root-Finder for exact $C_L$ targeting.
*   🧬 **<span style="color: #32CD32;">Hybrid Memetic Algorithms (PyMoo):</span>** Employs an aggressive two-stage solver. Stage 1 utilizes Global Evolutionary algorithms (**jDE** and **SHADE**) to map hyperspace. Stage 2 engages a gradient-free **Nelder-Mead Simplex** for absolute mathematical topological refinement.
*   🛡️ **<span style="color: #FF8C00;">Surrogate-Assisted Pre-Screening (SAP):</span>** The AI acts as an aerodynamic "bouncer." If the AI predicts boundary-layer separation or poor performance on a mutated shape, it is instantly rejected—preventing Fortran matrix crashes.
*   📐 **<span style="color: #1E90FF;">Advanced Shape Sculpting:</span>** Features four Numba-accelerated engines: **Kulfan CST**, **Bezier Curves**, **Hicks-Henne Sine Bumps**, and **Camb-Thick Scaling**.
*   ⚙️ **<span style="color: #708090;">Kinematic Trailing Edge Flaps:</span>** Pure Python Cartesian Rotation Matrices allow the AI to co-optimize physical wing shape and mechanical flap deployment simultaneously.
*   ⚖️ **<span style="color: #DAA520;">The Dynamic Weighting Engine:</span>** An intelligent "Lag Detector" that exponentially inflates mathematical penalties on lagging targets mid-run, preventing "objective collapse."
*   📊 **<span style="color: #20B2AA;">Next-Gen Interactive Reporting:</span>** Serializes NumPy arrays into offline, 60 FPS **Plotly HTML Dashboards** (Convergence Time-Machines and Multi-Trace Drag Polars).

---

## <span style="color: #00BFFF;"><i class="fa-solid fa-triangle-exclamation"></i> 3. The Engineering Paradigm: Why AeroForgeX?</span>

To understand AeroForgeX, one must understand the inherent flaws in traditional aerodynamic optimization. The greatest bottleneck is not fluid simulation, but **geometric breakdown**.

<div style="display: flex; flex-direction: column; gap: 15px;">

<div style="background-color: #FFF3CD; border-left: 5px solid #FFC107; padding: 15px; border-radius: 6px; color: #856404;">
  <h4 style="margin-top: 0px; margin-bottom: 5px; color: #B8860B;"><i class="fa-solid fa-chart-area"></i> The "Noisy" Aerodynamic Landscape</h4>
  Traditional optimization relies on Gradient Descent. In viscous fluids, microscopic geometric changes can cause the boundary layer to jump suddenly from laminar to turbulent. This creates a mathematically "noisy" landscape filled with cliffs. Gradient solvers explode or stagnate here.
</div>

<div style="background-color: #F8D7DA; border-left: 5px solid #DC3545; padding: 15px; border-radius: 6px; color: #721C24;">
  <h4 style="margin-top: 0px; margin-bottom: 5px; color: #A52A2A;"><i class="fa-solid fa-bomb"></i> Solver Fragility</h4>
  Evolutionary Algorithms randomly mutate variables to avoid these cliffs but lack aerodynamic intuition. They generate jagged spikes or self-intersecting meshes. When fed into boundary layer solvers (like XFOIL), the underlying Newton-Raphson mathematics violently destabilize, resulting in crashes.
</div>

<div style="background-color: #D4EDDA; border-left: 5px solid #28A745; padding: 15px; border-radius: 6px; color: #155724;">
  <h4 style="margin-top: 0px; margin-bottom: 5px; color: #228B22;"><i class="fa-solid fa-shield-check"></i> The AeroForgeX Solution</h4>
  AeroForgeX is <strong>Gradient-Free and Fault-Tolerant</strong>. It uses stochastic AI to bypass gradient noise, and a rigorous <strong>Topological Constraint Engine</strong> (Numba-accelerated calculus) to analyze 2nd-derivative curvature. Unnatural spikes face a "Death Penalty" and are discarded before ever risking a solver crash.
</div>

</div>

---

## <span style="color: #00BFFF;"><i class="fa-solid fa-network-wired"></i> 4. Core Architecture (The Deep Dive)</span>

### <span style="color: #4682B4;"><i class="fa-solid fa-compress"></i> 4.1 "Curse of Dimensionality" & Parameterization</span>
A `.dat` file has ~161 to 250 coordinate pairs. Allowing AI to move every $Y$-coordinate creates a **161-dimensional hyperspace**, resulting in jagged surfaces and infinite compute times. **Shape Parameterization** compresses the airfoil into 6 to 35 mathematical variables. The AI mutates these core variables to guarantee infinitely continuous, smooth surfaces.

### <span style="color: #4682B4;"><i class="fa-solid fa-display"></i> 4.2 The Dual-Interface Ecosystem</span>
*   **<i class="fa-brands fa-chrome" style="color: #4285F4;"></i> Streamlit Web GUI (`AeroForgeX_GUI.py`):** Visual prototyping, live plotting, and interactive reporting for local machines.
*   **<i class="fa-solid fa-terminal" style="color: #555;"></i> Headless CLI (`aeroforgex_cli.py`):** JSON-driven orchestration designed for remote Linux clusters and HPC automation.

### <span style="color: #4682B4;"><i class="fa-solid fa-box-archive"></i> 4.3 Multiprocessing & Sandbox Isolation</span>
AeroForgeX boots up instances matching your CPU core count. To prevent OS file-locking collisions, it generates **cryptographically unique filenames** (e.g., `_temp_foil_1402_1684_a1b2.dat`) using Process IDs and UUIDs, ensuring absolute sandbox isolation and 100% core utilization.

---

## <span style="color: #00BFFF;"><i class="fa-solid fa-toolbox"></i> 5. Standalone Worker Mode (The Swiss Army Knife)</span>

Beyond optimization, invoking Worker Mode (`-w`) bypasses the AI, transforming AeroForgeX into a high-speed geometry toolkit.

| Tool | Capability | Description |
| :--- | :--- | :--- |
| <i class="fa-solid fa-layer-group" style="color: #9370DB;"></i> | **Batch Pipeline** | Pass a directory path to execute Numba operations on hundreds of airfoils simultaneously across all cores. |
| <i class="fa-solid fa-broom" style="color: #32CD32;"></i> | **Sanitization** | Repanel messy CAD files (Arc-Cosine) or shrink-wrap a Bezier polynomial over jagged wind-tunnel scans. |
| <i class="fa-solid fa-object-group" style="color: #FF8C00;"></i> | **Morphing** | Instantly scale thickness, mathematically blend two independent airfoils, or auto-generate parametric families. |
| <i class="fa-solid fa-map-location-dot" style="color: #1E90FF;"></i> | **Envelope Mapper** | Automatically construct massive combinatorial matrices (Flaps $\times$ Reynolds $\times$ Mach) into a single Data-Science CSV. |

---

## <span style="color: #00BFFF;"><i class="fa-solid fa-chart-pie"></i> 6. Interactive Dashboards & Data Telemetry</span>

AeroForgeX abandons legacy text-based plotting in favor of **Standalone Interactive Plotly Dashboards**.

*   <i class="fa-solid fa-clock-rotate-left" style="color: #DC143C;"></i> **The Convergence Time-Machine:** Drag the generation slider to physically watch the airfoil morph from the Seed shape to the Optimized design.
*   <i class="fa-solid fa-chart-line" style="color: #4682B4;"></i> **The Polar Analyzer:** Multi-trace interactive plots for $C_L$ vs $\alpha$ and Drag Polars. Hover to read exact drag values at stall points.
*   <i class="fa-solid fa-file-csv" style="color: #2E8B57;"></i> **The "Black Box" CSVs:** Every microsecond is logged into Pandas-compatible CSVs. If power is lost at Generation 199/200, your optimal shape is securely backed up.

---

## <span style="color: #00BFFF;"><i class="fa-solid fa-laptop-code"></i> 7. Installation & Setup</span>

AeroForgeX is highly scalable and fully cross-platform (Requires **Python 3.9+**).

## <span style="color: #4682B4;"><i class="fa-solid fa-download"></i> 7.1 Initialization & Environment Setup</span>

AeroForgeX v4.0 is a Python-based ecosystem, but it relies heavily on external C-compiled math libraries and Fortran binaries. A strict environment setup is required to prevent execution faults.

### <span style="color: #2E8B57;"><i class="fa-solid fa-folder-tree"></i> Step 1: Cloning the Repository</span>
Download or clone the AeroForgeX directory to your local workstation.
> ⚠️ **Hardware Recommendation:** We highly recommend placing the folder on an **NVMe Solid State Drive (SSD)** or a **RAM Disk**. The XFOIL subprocess writes tens of thousands of temporary files during an optimization run. Mechanical Hard Drives (HDDs) will severely bottleneck the optimizer.

### <span style="color: #2E8B57;"><i class="fa-solid fa-microchip"></i> Step 2: Positioning the XFOIL Fortran Binary</span>
AeroForgeX does not compile XFOIL from scratch; it acts as an asynchronous subprocess wrapper.
1. Download the pre-compiled `xfoil.exe` (Windows) or `xfoil` binary (Linux/macOS) from the official MIT aerodynamics repository.
2. Place the executable **directly into the `AeroForgeX_scr` folder** *(in the exact same folder as `aeroforgex_cli.py`)*.

---

## <span style="color: #4682B4;"><i class="fa-brands fa-python"></i> 7.2 Modular Dependency Installation Strategy</span>

AeroForgeX v4.0 is highly modular. To prevent environment bloat, the software allows you to install dependencies in **"Tiers"** based entirely on your intended workflow. Choose the installation tier that matches your engineering needs.

<div style="display: flex; flex-direction: column; gap: 15px; margin-top: 15px; margin-bottom: 20px;">

<!-- TIER 1 -->
<div style="background-color: #F0F8FF; border-left: 5px solid #4682B4; padding: 15px; border-radius: 6px; color: #333;">
  <h4 style="margin-top: 0px; margin-bottom: 8px; color: #27408B;"><i class="fa-solid fa-terminal"></i> Tier 1: The Core Foundation (CLI + XFOIL Only)</h4>
  <p style="margin-bottom: 8px; font-size: 0.95em;"><em>Recommended for: Headless Linux HPC clusters, automated bash-scripting, and traditional aerodynamicists who only trust Navier-Stokes/Panel-Method physics.</em></p>
  <p style="margin-bottom: 8px; font-size: 0.95em;">This tier provides the absolute minimum packages required to run the <code>aeroforgex_cli.py</code> Master Orchestrator, the Numba C-speed calculus engine, the PyMoo AI, and generate standalone HTML/PDF reports.</p>
  <code style="display: block; background-color: #1E1E1E; color: #D4D4D4; padding: 10px; border-radius: 4px; margin-bottom: 10px;">pip install numpy scipy numba pymoo pandas matplotlib plotly colorama tqdm psutil</code>
  <ul style="margin-bottom: 0px; font-size: 0.9em; color: #555;">
    <li><strong>numba:</strong> Critical. Compiles the Python geometric splines into C-machine code.</li>
    <li><strong>pymoo:</strong> Powers the Memetic Evolutionary algorithms.</li>
    <li><strong>psutil:</strong> Manages OS-level thread priorities and limits XFOIL memory bleeding.</li>
    <li><strong>pandas & plotly:</strong> Required by the CLI to write <code>.csv</code> ledgers and generate the offline HTML Convergence & Polar Dashboards.</li>
  </ul>
</div>

<!-- TIER 2 -->
<div style="background-color: #FFF3E0; border-left: 5px solid #FF8C00; padding: 15px; border-radius: 6px; color: #333;">
  <h4 style="margin-top: 0px; margin-bottom: 8px; color: #E65100;"><i class="fa-solid fa-brain"></i> Tier 2: The Deep Learning Upgrade (+ NeuralFoil)</h4>
  <p style="margin-bottom: 8px; font-size: 0.95em;"><em>Recommended for: Massive multi-point optimization sweeps, Kinematic Flap co-optimization, and rapid concept exploration where XFOIL is too slow.</em></p>
  <p style="margin-bottom: 8px; font-size: 0.95em;">To bypass the Fortran engine and use the lightning-fast CNN surrogate, you must install the <code>neuralfoil</code> library. (Ensure Tier 1 is installed first).</p>
  <code style="display: block; background-color: #1E1E1E; color: #D4D4D4; padding: 10px; border-radius: 4px; margin-bottom: 10px;">pip install neuralfoil</code>
  <div style="background-color: #FFEBEE; border: 1px solid #EF5350; padding: 8px; border-radius: 4px; color: #C62828; font-size: 0.85em;">
    <strong>⚠️ ENGINEERING NOTE (The Tensor Backend):</strong> <code>neuralfoil</code> maybe requires a heavy machine-learning backend to process its tensors. Installing via pip will usually auto-install requirements. Be aware this will increase the size of your virtual environment.
  </div>
</div>

<!-- TIER 3 -->
<div style="background-color: #FFF0F2; border-left: 5px solid #FF4B4B; padding: 15px; border-radius: 6px; color: #333;">
  <h4 style="margin-top: 0px; margin-bottom: 8px; color: #B22222;"><i class="fa-brands fa-chrome"></i> Tier 3: The Full Pro Web Ecosystem (+ GUI)</h4>
  <p style="margin-bottom: 8px; font-size: 0.95em;"><em>Recommended for: Commercial engineers, daily desktop use, and visual rapid prototyping.</em></p>
  <p style="margin-bottom: 8px; font-size: 0.95em;">If you want to abandon the command line entirely and use the beautiful, 4-tab interactive AeroForgeX Pro Web Dashboard, you must install the Streamlit framework. (Ensure Tier 1 is installed first).</p>
  <code style="display: block; background-color: #1E1E1E; color: #D4D4D4; padding: 10px; border-radius: 4px; margin-bottom: 10px;">pip install streamlit streamlit-autorefresh</code>
  <ul style="margin-bottom: 0px; font-size: 0.9em; color: #555;">
    <li><strong>streamlit:</strong> The core web framework that renders the UI natively in your browser.</li>
    <li><strong>streamlit-autorefresh:</strong> A critical background component allowing the Deployment Console to continuously poll live Fortran telemetry logs without manual web-page refreshes.</li>
  </ul>
</div>

</div>

### <span style="color: #32CD32;"><i class="fa-solid fa-box-archive"></i> 📦 The "All-In-One" Master `requirements.txt`</span>
If you are setting up a high-end desktop workstation and want access to *every* feature AeroForgeX offers, create a `requirements.txt` file in your root directory and paste the following heavily annotated blueprint. Then simply execute `pip install -r requirements.txt`.

```text
# ==============================================================================
# AeroForgeX v4.0 Pro - Master Dependencies
# Python 3.9+ Recommended
# ==============================================================================

# --- 1. CORE MATHEMATICS & JIT COMPILATION (Mandatory) ---
numpy>=1.21.0
scipy>=1.7.0
numba>=0.56.0

# --- 2. MEMETIC OPTIMIZATION ENGINE (Mandatory) ---
pymoo>=0.6.0.1

# --- 3. DATA HANDLING, LOGGING, & OS MANAGEMENT (Mandatory) ---
pandas>=1.3.0
colorama>=0.4.5
tqdm>=4.64.0
psutil>=5.9.0

# --- 4. VISUALIZATION & REPORTING (Mandatory for HTML/PDF outputs) ---
matplotlib>=3.5.0
plotly>=5.10.0

# ==============================================================================
# OPTIONAL MODULES (Comment out if not required)
# ==============================================================================

# --- 5. THE WEB ECOSYSTEM (Required for AeroForgeX_GUI.py) ---
streamlit>=1.20.0
streamlit-autorefresh>=1.0.0

# --- 6. DEEP LEARNING SURROGATE (Required for "solver": "neuralfoil") ---

neuralfoil>=0.3.1
```

---

## <span style="color: #00BFFF;"><i class="fa-solid fa-rocket"></i> 8. Quick Start</span>

### <span style="color: #FF4B4B;"><i class="fa-brands fa-chrome"></i> Method A: The Web Ecosystem (Streamlit)</span>
```bash
streamlit run AeroForgeX_GUI.py
```
*(Your browser will open automatically. Visually configure your run and deploy!)*


<p align="center">
  <img src="docs/images/readme1.jpg" alt="AeroForgeX Pro Screenshot" width="100%" style="max-width: 800px;">
</p>



### <span style="color: #1E90FF;"><i class="fa-solid fa-terminal"></i> Method B: The Command Line Orchestrator</span>
```bash
python AeroForgeX_scr/aeroforgex_cli.py -i json_Input/quickstart.json -a Airfoils/NACA0012.dat -o Outputs/MyOptimizedFoil
```

### <span style="color: #32CD32;"><i class="fa-solid fa-screwdriver-wrench"></i> Method C: The Worker Toolkit (e.g., Drag Polar CSV)</span>
```bash
python AeroForgeX_scr/aeroforgex_cli.py -w polar-csv -i json_Input/sweep.json -a Airfoils/naca0012.dat
```

***

<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

## <span style="color: #00BFFF;"><i class="fa-solid fa-sitemap"></i> 9 Workspace Architecture & Execution Workflows</span>

<!-- FLEXBOX BADGES (Perfectly Spaced & Formatted) -->
<div style="display: flex; gap: 12px; margin-top: 10px; margin-bottom: 25px; flex-wrap: wrap;">
  <img src="https://img.shields.io/badge/Architecture-Modular_Ecosystem-000000?style=for-the-badge&logo=codeproject&logoColor=white" alt="Architecture">
  <img src="https://img.shields.io/badge/Execution-Batch_Scripts-00A6D6?style=for-the-badge&logo=windows&logoColor=white" alt="Batch">
  <img src="https://img.shields.io/badge/Safety-OS_Kill_Switch-DC3545?style=for-the-badge&logo=shield&logoColor=white" alt="Kill Switch">
  <img src="https://img.shields.io/badge/Workflow-Zero_Friction-28A745?style=for-the-badge&logo=fastlane&logoColor=white" alt="Workflow">
</div>

<p style="font-size: 0.95em; line-height: 1.6; color: var(--fgColor-default, #333);">To master AeroForgeX v4.0 Pro, an engineer must first understand its foundational ecosystem. AeroForgeX is not a single script; it is a highly structured, modular environment designed to maintain a clean workspace, prevent data collision during High-Performance Computing (HPC) runs, and streamline daily aerodynamic operations.</p>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-folder-tree"></i> 9.1 The Anatomy of the Workspace (Repository Architecture)</span>

Before launching an optimization run, familiarize yourself with the strict directory architecture required by the orchestrator. **Warning: Modifying or moving these core folders may cause critical I/O routing failures and crash the fluid dynamics solvers.**

<div style="background-color: #1E1E1E; padding: 15px; border-radius: 8px; border: 1px solid #333; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.2);">
  <pre style="margin: 0px; background-color: #1E1E1E; color: #D4D4D4; border: none; font-family: 'Consolas', monospace; font-size: 0.85em; line-height: 1.4; white-space: pre-wrap;"><span style="color: #9CDCFE; font-weight: bold;">AeroForgeX/</span>
│
├── <span style="color: #9CDCFE;">AeroForgeX_scr/</span>                 <span style="color: #6A9955;"># Core Python Math & Logic Modules</span>
│   ├── <span style="color: #CE9178;">aeroforgex_cli.py</span>           <span style="color: #6A9955;"># Master CLI Orchestrator & UI Router</span>
│   ├── <span style="color: #CE9178;">aero_polars.py</span>              <span style="color: #6A9955;"># Worker Mode execution & Sweep Engine</span>
│   ├── <span style="color: #CE9178;">config_manager.py</span>           <span style="color: #6A9955;"># JSON/Namelist Parser & Constraint Sanitizer</span>
│   ├── <span style="color: #CE9178;">geom_builder.py</span>             <span style="color: #6A9955;"># Airfoil preparation, Shape Parameterizations</span>
│   ├── <span style="color: #CE9178;">geom_core.py</span>                <span style="color: #6A9955;"># Numba-accelerated splines & mesh clustering</span>
│   ├── <span style="color: #CE9178;">math_accelerator.py</span>         <span style="color: #6A9955;"># C-speed matrix solvers & calculus operations</span>
│   ├── <span style="color: #CE9178;">obj_evaluator.py</span>            <span style="color: #6A9955;"># Master Objective Function & Penalty Engine</span>
│   ├── <span style="color: #CE9178;">obj_utils.py</span>                <span style="color: #6A9955;"># CSV Exporters, Matplotlib graphing, File I/O</span>
│   ├── <span style="color: #CE9178;">opt_engine.py</span>               <span style="color: #6A9955;"># PyMoo Differential Evolution & Simplex</span>
│   ├── <span style="color: #CE9178;">opt_engine_jDE.py</span>           <span style="color: #6A9955;"># Self-Adaptive jDE Engine</span>
│   ├── <span style="color: #CE9178;">opt_engine_SHADE.py</span>         <span style="color: #6A9955;"># SHADE Evolutionary Engine</span>
│   ├── <span style="color: #CE9178;">opt_utils.py</span>                <span style="color: #6A9955;"># Local search algorithms (Nelder-Mead)</span>
│   ├── <span style="color: #CE9178;">report_generator.py</span>         <span style="color: #6A9955;"># Interactive HTML/PDF Dashboard Engine</span>
│   ├── <span style="color: #CE9178;">shape_functions_param.py</span>    <span style="color: #6A9955;"># CST/Bezier/Hicks-Henne mathematical mapping</span>
│   ├── <span style="color: #CE9178;">solver_neuralfoil.py</span>        <span style="color: #6A9955;"># Machine Learning Surrogate routing</span>
│   ├── <span style="color: #CE9178;">solver_router.py</span>            <span style="color: #6A9955;"># Traffic Controller (XFOIL vs. NeuralFoil)</span>
│   ├── <span style="color: #CE9178;">solver_xfoil.py</span>             <span style="color: #6A9955;"># Fortran subprocess execution & Regex parsing</span>
│   ├── <span style="color: #CE9178;">utils_logger.py</span>             <span style="color: #6A9955;"># Colorama-based ANSI terminal UI engine</span>
│   └── <span style="color: #4EC9B0; font-weight: bold;">xfoil.exe</span>                   <span style="color: #6A9955;"># The MIT Fortran aerodynamic binary</span>
│
├── <span style="color: #9CDCFE;">Airfoils/</span>                       <span style="color: #6A9955;"># Starting Seed Geometries (e.g., NACA0012.dat)</span>
├── <span style="color: #9CDCFE;">json_Input/</span>                     <span style="color: #6A9955;"># Configuration Matrices (Engineering blueprints)</span>
├── <span style="color: #9CDCFE;">Outputs/</span>                        <span style="color: #6A9955;"># Auto-generated sandbox folders for optimization</span>
│── <span style="color: #CE9178;">AeroForgeX_GUI.py</span>               <span style="color: #6A9955;"># Streamlit Web Ecosystem</span>
├── <span style="color: #DCDCAA;">Run_AeroForgeX.bat</span>              <span style="color: #6A9955;"># One-click execution for Input_template.json</span>
├── <span style="color: #DCDCAA;">Run_quickstart.bat</span>              <span style="color: #6A9955;"># One-click execution for the Hello World tutorial</span>
├── <span style="color: #C586C0;">Stop_AeroForgeX.bat</span>             <span style="color: #6A9955;"># Graceful OS-Level AI kill switch (preserves data)</span>
├── <span style="color: #CE9178;">run_control</span>                     <span style="color: #6A9955;"># Dynamic interrupt listener tracking file</span>
│
├── <span style="color: #CE9178;">test_aeroforgex_full.py</span>         <span style="color: #6A9955;"># Exhaustive Test Orchestrator (Validates Math/PyMoo)</span>
└── <span style="color: #CE9178;">test_aeroforgex_work.py</span>         <span style="color: #6A9955;"># Exhaustive Test Orchestrator for Worker Mode (-w)</span></pre>
</div>

#### <span style="color: #1E90FF; font-weight: bold;"><i class="fa-solid fa-magnifying-glass"></i> Deep Dive: Core Directories</span>
<div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; margin-bottom: 25px;">
  <ul style="margin-bottom: 0px; padding-left: 20px; font-size: 0.95em; color: #444; line-height: 1.7;">
    <li><strong style="color: #2563EB;"><code>AeroForgeX_scr/</code></strong>: The "engine room." Contains all Python math engines, the AI orchestrators, the Master CLI, and the pre-compiled <code>xfoil.exe</code> binary. You rarely edit these unless modifying core physics.</li>
    <li><strong style="color: #2563EB;"><code>Airfoils/</code></strong>: Your local geometry database. Place your starting "Seed" geometries here. <strong>Strict Requirement:</strong> These must be standard Selig-formatted <code>.dat</code> coordinate files.</li>
    <li><strong style="color: #2563EB;"><code>json_Input/</code></strong>: The command deck. AeroForgeX reads <code>.json</code> matrices from here to understand your targets, flight envelopes, and structural constraints.</li>
    <li><strong style="color: #2563EB;"><code>Outputs/</code></strong>: The automated data repository. The system dynamically builds isolated, cryptographically secure sandbox directories here to completely prevent data corruption and file-lock collisions.</li>
    <li><strong style="color: #2563EB;"><code>test_aeroforgex_*</code></strong>: Auto-generated scripts used to validate your Python/Fortran environment. <em>Always run these after a fresh installation to verify Numba JIT compilation.</em></li>
  </ul>
</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-gears"></i> 9.2 The Universal Batch Execution Workflow</span>

While AeroForgeX provides a highly robust CLI for automated bash scripting, typing long execution strings in a terminal can be tedious for daily tasks. Aerodynamicists need a **"zero-friction"** method to swap geometries, tweak flight conditions, and launch the AI instantly.

To achieve this, AeroForgeX ships with a pre-configured ecosystem utilizing two interconnected files: `Input_template.json` and `Run_AeroForgeX.bat`. This bypasses the command prompt entirely.

<div style="display: flex; flex-direction: column; gap: 15px; margin-top: 15px; margin-bottom: 25px;">

  <!-- Blueprint Card -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; border-left: 4px solid #3B82F6;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #1E3A8A;"><i class="fa-solid fa-file-code"></i> 9.2.1 The Master Blueprint: <code>Input_template.json</code></h4>
    <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.95em; color: #444; line-height: 1.6;">Located in <code>json_Input/</code>, this is the ultimate "superset" matrix, pre-loaded with every possible parameter and constraint the software supports. Instead of writing new JSON files from scratch, you use this as your permanent control deck for <strong>Seamless Parameter Swapping:</strong></p>
    <ul style="margin-bottom: 0px; padding-left: 20px; font-size: 0.9em; color: #555; line-height: 1.6;">
      <li><strong>Swapping Engines:</strong> Change <code>"aero_solver": "xfoil"</code> to <code>"neuralfoil"</code> to instantly evaluate geometry using the Deep Learning Surrogate.</li>
      <li><strong>Swapping Topology:</strong> Change <code>"shape_func": "cst"</code> to <code>"bezier"</code> to fundamentally alter how the AI mutates the surface.</li>
      <li><strong>Swapping Seeds:</strong> Redirect <code>"foil_file": "Airfoils/NACA0012.dat"</code> to any other <code>.dat</code> file to begin evolving a completely different wing.</li>
    </ul>
  </div>

  <!-- Array Truncation Card -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; border-left: 4px solid #10B981;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #065F46;"><i class="fa-solid fa-scissors"></i> 9.2.2 The Array Truncation Protocol (The 25-Point Rule)</h4>
    <p style="margin-top: 0px; margin-bottom: 8px; font-size: 0.95em; color: #444; line-height: 1.6;">The template comes pre-configured with massive arrays defining <strong>25 distinct flight conditions</strong>. However, you rarely need to optimize for 25 points simultaneously. AeroForgeX utilizes a brilliant workflow trick:</p>
    <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.95em; color: #444; line-height: 1.6;">The software strictly obeys the <code>"num_operating_points"</code> integer. If set to <code>3</code>, AeroForgeX reads points (1), (2), and (3), and <strong>safely ignores</strong> data for points 4 through 25 without throwing an error.</p>
  </div>

</div>

<div style="background-color: #FFFBEB; border: 1px solid #FCD34D; border-left: 5px solid #F59E0B; padding: 15px; border-radius: 6px; margin-bottom: 25px;">
  <h4 style="margin-top: 0px; margin-bottom: 8px; color: #92400E;"><i class="fa-solid fa-lightbulb"></i> WHY IS THIS REVOLUTIONARY?</h4>
  <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.95em; color: #78350F; line-height: 1.6;">You never have to delete or re-type complex arrays. You can leave your massive, 25-point Master Flight Envelope permanently saved. When you arrive at work, dial <code>"num_operating_points"</code> down to <code>1</code> to run a rapid 3-minute feasibility test. Once satisfied, simply dial the integer back up to <code>25</code>, double-click the <code>.bat</code> file, and leave for an overnight HPC run.</p>
</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-desktop"></i> 9.3 The OS-Level Execution Wrapper (<code>Run_AeroForgeX.bat</code>)</span>

Once your `Input_template.json` is configured, you execute the optimization by double-clicking `Run_AeroForgeX.bat`. This is not a simple shortcut; it is a sophisticated OS-level execution wrapper designed to ensure environmental stability and trap fatal errors before they crash the terminal.

<div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 18px; border-radius: 6px; margin-top: 15px; margin-bottom: 25px;">
  <p style="margin-top: 0px; margin-bottom: 12px; color: #475569; font-weight: bold;"><i class="fa-solid fa-microchip"></i> Inside the <code>.bat</code> Architecture:</p>
  <ol style="margin-bottom: 0px; padding-left: 20px; font-size: 0.95em; color: #444; line-height: 1.7;">
    <li style="margin-bottom: 8px;"><strong>Directory Anchoring:</strong> The script executes <code>cd /d "%~dp0"</code> to forcefully lock the Current Working Directory (CWD). This ensures AeroForgeX never loses track of the <code>Airfoils/</code> or <code>Outputs/</code> paths, regardless of how it is launched.</li>
    <li style="margin-bottom: 8px;"><strong>Python Runtime Verification:</strong> It queries the OS System PATH (<code>python --version >nul</code>) to guarantee Python 3 is installed. If missing, it catches the <code>%errorlevel%</code>, prints a <code>[ FATAL ]</code> warning, and pauses the screen so the user can read the error rather than the window instantly flashing shut.</li>
    <li style="margin-bottom: 8px;"><strong>The Master Invocation:</strong> It automatically invokes the CLI, passing the exact relative path: <br>
      <code style="background-color: #1E1E1E; color: #D4D4D4; padding: 2px 6px; border-radius: 4px; border: 1px solid #333;">python AeroForgeX_scr\aeroforgex_cli.py -i json_Input/Input_template.json</code>
    </li>
    <li><strong>Graceful Termination Catchers:</strong> When the PyMoo algorithm concludes (or is safely killed), the script evaluates the final exit code, prints a PASS/FATAL status, and pauses the terminal so you can review the final metrics.</li>
  </ol>
</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-power-off"></i> 9.4 Safely Stopping a Run (The OS-Level Kill Switch)</span>

Optimization runs with 10+ operating points and massive populations can take multiple hours. If you decide that a 15% improvement at Generation 150 is "good enough" and you want to stop the run early to extract the coordinates, **DO NOT press `Ctrl+C` or close the terminal window.**

<div style="background-color: #FEF2F2; border: 1px solid #FECACA; border-left: 5px solid #EF4444; padding: 15px; border-radius: 6px; margin-top: 15px; margin-bottom: 15px;">
  <h4 style="margin-top: 0px; margin-bottom: 8px; color: #991B1B;"><i class="fa-solid fa-skull-crossbones"></i> ⚠️ THE ZOMBIE PROCESS TRAP</h4>
  <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.95em; color: #7F1D1D; line-height: 1.6;">Killing the Python process violently via <code>Ctrl+C</code> will instantly corrupt the CSV tracking matrices. Worse, it will leave hidden <code>xfoil.exe</code> "zombie" processes permanently running in your computer's RAM. These orphaned Fortran binaries will max out your CPU in the background, requiring a full system reboot to clear.</p>
</div>

<div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; margin-bottom: 25px;">
  <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.95em; color: #444; line-height: 1.6;">Instead, AeroForgeX features a graceful OS-level Kill Switch:</p>
  <ol style="margin-bottom: 12px; padding-left: 20px; font-size: 0.95em; color: #444; line-height: 1.6;">
    <li>Open the root folder of AeroForgeX in your file explorer.</li>
    <li>Locate and double-click the <strong><code>Stop_AeroForgeX.bat</code></strong> file.</li>
    <li>This script instantly injects the word <code>STOP</code> into the <code>run_control</code> tracking file (You can do it manually also: 1) Open run_control in Notepad 2) Delete all text inside, type the word stop, and save the file.).</li>
  </ol>
  <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.9em; color: #065F46; font-style: italic;"><i class="fa-solid fa-check"></i> <strong>What happens next?</strong> At the end of the current generation, the PyMoo <code>ProgressCallback</code> engine detects the stop command. It gracefully terminates the multi-core CPU pool, compiles final CSV/PNG reports, saves your <code>.dat</code> geometries, and exits safely, leaving your environment clean.</p>
</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-list-check"></i> 9.5 Summary: The Standard Daily Workflow</span>

By combining the JSON superset and the OS-level wrappers, your daily engineering workflow is reduced to three frictionless steps:

<div style="display: flex; flex-direction: column; gap: 15px; margin-top: 15px; margin-bottom: 25px;">

  <!-- Step 1 -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; display: flex; align-items: center; gap: 15px;">
    <div style="background-color: #3B82F6; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 1.2em; flex-shrink: 0;">1</div>
    <div>
      <h4 style="margin-top: 0px; margin-bottom: 5px; color: #1E3A8A;">Edit</h4>
      <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.9em; color: #444;">Open <code>json_Input/Input_template.json</code> in a text editor (like VS Code or Notepad++). Adjust your target constraints and save the file (<code>Ctrl+S</code>).</p>
    </div>
  </div>

  <!-- Step 2 -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; display: flex; align-items: center; gap: 15px;">
    <div style="background-color: #10B981; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 1.2em; flex-shrink: 0;">2</div>
    <div>
      <h4 style="margin-top: 0px; margin-bottom: 5px; color: #065F46;">Execute</h4>
      <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.9em; color: #444;">Navigate to the AeroForgeX root folder and double-click <code>Run_AeroForgeX.bat</code> to launch the terminal UI and instantiate the Memetic AI.</p>
    </div>
  </div>

  <!-- Step 3 -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; display: flex; align-items: center; gap: 15px;">
    <div style="background-color: #F59E0B; color: white; width: 40px; height: 40px; border-radius: 50%; display: flex; justify-content: center; align-items: center; font-weight: bold; font-size: 1.2em; flex-shrink: 0;">3</div>
    <div>
      <h4 style="margin-top: 0px; margin-bottom: 5px; color: #92400E;">Review</h4>
      <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.9em; color: #444;">Once the run completes, navigate to your <code>Outputs/</code> folder to retrieve your finalized <code>.dat</code> coordinates, CSV aerodynamic ledgers, and Interactive HTML Dashboards.</p>
    </div>
  </div>

</div>

---
---
## <span style="color: #00BFFF;"><i class="fa-solid fa-book"></i> 10. Documentation & Tutorials</span>

For a deep dive into configuring objective matrices, constraints, and shape functions, refer to the `docs/` folder:

1. <i class="fa-solid fa-file-lines" style="color: #888;"></i> [**SECTION 1: Introduction & Comprehensive Overview**](docs/SECTION%201%20Introduction%20&%20Comprehensive%20Overview.md)
2. <i class="fa-solid fa-file-lines" style="color: #888;"></i> [**SECTION 2: Installation & The Hello World Quick Start Guide**](docs/SECTION%202%20Installation%20&%20The%20Hello%20World%20Quick%20Start%20Guide.md)
3. <i class="fa-solid fa-file-lines" style="color: #888;"></i> [**SECTION 3: The AeroForgeX Pro Web Ecosystem (GUI)**](docs/SECTION%203%20The%20AeroForgeX%20Pro%20Web%20Ecosystem%20(GUI).md)
4. <i class="fa-solid fa-file-lines" style="color: #888;"></i> [**SECTION 4: The Master Configuration File (JSON Guide)**](docs/SECTION%204%20The%20Master%20Configuration%20File%20(JSON%20Guide).md)
5. <i class="fa-solid fa-file-lines" style="color: #888;"></i> [**SECTION 5: Standalone Worker Mode (The Swiss Army Knife)**](docs/SECTION%205%20Standalone%20Worker%20Mode%20(The%20Swiss%20Army%20Knife).md)
6. <i class="fa-solid fa-file-lines" style="color: #888;"></i> [**SECTION 6: The Aerodynamic Engines (XFOIL vs. NeuralFoil)**](docs/SECTION%206%20The%20Aerodynamic%20Engines%20(XFOIL%20vs.%20NeuralFoil).md)
7. <i class="fa-solid fa-file-lines" style="color: #888;"></i> [**SECTION 7: Shape Parameterization Strategies**](docs/SECTION%207%20Shape%20Parameterization%20Strategies.md)
8. <i class="fa-solid fa-file-lines" style="color: #888;"></i> [**SECTION 8: The Memetic Optimization Algorithms (PyMoo)**](docs/SECTION%208%20The%20Memetic%20Optimization%20Algorithms%20(PyMoo).md)
9. <i class="fa-solid fa-file-lines" style="color: #888;"></i> [**SECTION 9: Data Outputs & Interactive Dashboards**](docs/SECTION%209%20Data%20Outputs%20&%20Interactive%20Dashboards.md)
10. <i class="fa-solid fa-file-lines" style="color: #888;"></i> [**SECTION 10: Worker Mode Outputs & Dashboards**](docs/SECTION%2010%20Worker%20Mode%20Outputs%20&%20Dashboards.md)
11. <i class="fa-solid fa-file-lines" style="color: #888;"></i> [**SECTION 11: Conceptual Tutorials & Engineering Case Studies**](docs/SECTION%2011%20Conceptual%20Tutorials%20&%20Engineering%20Case%20Studies.md)
12. <i class="fa-solid fa-file-lines" style="color: #888;"></i> [**SECTION 12: Hidden Logic & Auto-Overrides**](docs/SECTION%2012%20Hidden%20Logic%20&%20Auto-Overrides.md)
13. <i class="fa-solid fa-file-lines" style="color: #888;"></i> [**SECTION 13: Appendices & Technical Reference**](docs/SECTION%2013%20Appendices%20&%20Technical%20Reference.md)

---
## 11 🗺️ Architectural Roadmap (Upcoming in Next Release)

AeroForgeX is in a state of continuous, aggressive evolution. The next major release will introduce unprecedented capabilities in physics-informed Artificial Intelligence, currently in active development:

*   🧠 **Integration of N.A.S.T. (Neural Aerodynamic Shape Transformation):** A revolutionary 32-Dimensional generative AI parameterization engine. NAST utilizes 20 explicit physical features and 12 abstract latent ($Z$) variables, allowing the optimizer to explore latent spaces and generate highly complex geometries that traditional CST/Bezier curves cannot represent.
*   🤖 **Live Online Machine Learning Surrogate:** Introduction of a live-training Random Forest regressor. The optimizer will continuously train an ML model *during* the run using XFOIL cache data. It will perform millisecond pre-screening, predicting aerodynamic failure and dynamically steering the swarm away from bad designs before ever booting up the Fortran solver.
*   📈 **Hierarchical CST Resolution Scaling:** Defeating the "Curse of Dimensionality." The AI will begin the optimization using a low-order CST space  to rapidly locate the global optimum basin. Mid-way through the run, it will automatically project the airfoil into a high-order CST space and restart the swarm for high-fidelity local refinement.
*   🔄 **Multi-Fidelity Solver Phasing:** The ability to configure the Memetic engine to run the first 80% of generations using the ultra-fast `NeuralFoil` CNN surrogate, and seamlessly hand off the final 20% of generations to the high-fidelity `XFOIL` Fortran engine for absolute physical validation.
*   🧬 **Asymmetric Genetic Block Crossover:** A custom crossover operator for the PyMoo Differential Evolution engines. Instead of blindly mixing random variables (which creates jagged, "wiggly" offspring), the engine will treat the Upper Surface and Lower Surface as unified genetic blocks, preserving $C^2$ continuity during mutation.
*   🛡️ **Adaptive Penalty Methods (APM):** Simulated annealing for physical constraints. The software will apply "soft" geometrical penalties in early generations to encourage wide exploration, and geometrically scale them into hard, unforgiving walls as the generations progress to force strict convergence.
*   📐 **$C^2$ Curvature Smoothness Filter:** A 2-microsecond pure-NumPy filter that evaluates the 2nd derivative of the airfoil surfaces. It instantly detects curvature spikes (kinks) and applies proportional penalties, guiding the swarm away from boundary-layer-tripping shapes before CFD execution.
---
## <span style="color: #00BFFF;"><i class="fa-solid fa-user-astronaut"></i> 12. About the Developer</span>

<div style="background-color: #ffffff; border: 1px solid #e2e8f0; padding: 25px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
  
  <!-- Developer 1 Section -->
  <div style="margin-bottom: 25px; border-bottom: 1px dashed #e2e8f0; padding-bottom: 20px;">
    <h3 style="margin: 0 0 5px 0; color: #2c3e50;"><i class="fa-solid fa-id-badge" style="color: #1E90FF;"></i> Gamil Abdullah Al-Sharif</h3>
    <p style="color: #7f8c8d; font-style: italic; margin: 0 0 15px 0; font-size: 0.95rem;">Mechanical Engineer & R&D Specialist | Sana'a, Yemen</p>
    <p style="margin: 0; color: #34495e; line-height: 1.6;">
      <i class="fa-solid fa-envelope" style="color: #7f8c8d; width: 20px;"></i> <strong>Email:</strong> <a href="mailto:mely104haja@gmail.com" style="color: #1E90FF; text-decoration: none;">mely104haja@gmail.com</a><br>
      <i class="fa-brands fa-linkedin" style="color: #0077B5; width: 20px;"></i> <strong>LinkedIn:</strong> <a href="https://linkedin.com/in/gamil-alsharif" target="_blank" style="color: #0077B5; text-decoration: none;">linkedin.com/in/gamil-alsharif</a>
    </p>
  </div>

  <!-- Developer 2 Section -->
  <div style="margin-bottom: 25px; border-bottom: 1px dashed #e2e8f0; padding-bottom: 20px;">
    <h3 style="margin: 0 0 5px 0; color: #2c3e50;"><i class="fa-solid fa-id-badge" style="color: #00BFFF;"></i> Yhya Abdullah Al-Wazir</h3>
    <p style="color: #7f8c8d; font-style: italic; margin: 0 0 15px 0; font-size: 0.95rem;">Mechanical Engineer & R&D Specialist | Sana'a, Yemen</p>
    <p style="margin: 0; color: #34495e; line-height: 1.6;">
      <i class="fa-solid fa-envelope" style="color: #7f8c8d; width: 20px;"></i> <strong>Email:</strong> <a href="mailto:abdullahyhya141@gmail.com" style="color: #00BFFF; text-decoration: none;">abdullahyhya141@gmail.com</a><br>
      <i class="fa-brands fa-researchgate" style="color: #00CCBB; width: 20px;"></i> <strong>ResearchGate:</strong> <a href="https://researchgate.net" target="_blank" style="color: #00CCBB; text-decoration: none;">researchgate.net/profile/Yhya-Abdullah-Al-Wazer</a>
    </p>
  </div>

  <!-- Publications Section -->
  <div>
    <h4 style="margin: 0 0 15px 0; color: #2c3e50; font-size: 1.1rem;"><i class="fa-solid fa-graduation-cap" style="color: #2c3e50; margin-right: 5px;"></i> Related Publications:</h4>
    <ol style="color: #4a5568; line-height: 1.7; margin: 0; padding-left: 20px;">
      <li style="margin-bottom: 12px;"> <strong>Al-Wazer, Y.A. and Al-Sharif, G.A.</strong>, <em>"Designing, Optimizing, and Manufacturing of Horizontal Wind Turbine Blades Using Available Resources,"</em> In Proceedings of the 4th International Conference on Emerging Smart Technologies and Applications (eSmarTA), Sana'a, Yemen, 2024.
      </li>
      <li style="margin-bottom: 0;">
         <strong>Al-Wazer, Y.A. and Al-Sharif, G.A.</strong>, <em>"Designing and Simulating an MPPT Solar Charger Using Machine Learning,"</em> In Proceedings of the 5th International Conference on Emerging Smart Technologies and Applications (eSmarTA), Ibb, Yemen, 2025.
      </li>
    </ol>
  </div>

</div>


---

## <span style="color: #00BFFF;"><i class="fa-solid fa-scale-balanced"></i> 13. Credits & License</span>

AeroForgeX is released under the **MIT License**.

This project is a sophisticated Python port and architectural expansion of *Xoptfoil2* (written in Fortran).
*   <i class="fa-solid fa-code-branch" style="color: #708090;"></i> **Based on Xoptfoil2** by Jochen Guenzel (MIT License).
*   <i class="fa-solid fa-lightbulb" style="color: #FDB813;"></i> Original **Xoptfoil** concept and physics engine developed by Daniel Prosser.
*   <i class="fa-solid fa-wind" style="color: #87CEEB;"></i> **XFOIL** developed by Dr. Mark Drela (MIT).
*   <i class="fa-solid fa-brain" style="color: #FF69B4;"></i> **NeuralFoil** developed by Peter Sharpe.

<div align="center" style="margin-top: 30px; color: #888; font-style: italic;">
  If you find AeroForgeX useful, please consider giving it a star! ⭐.


