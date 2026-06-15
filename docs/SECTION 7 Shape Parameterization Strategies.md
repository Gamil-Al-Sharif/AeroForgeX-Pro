
***

<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

## <span style="color: #00BFFF;"><i class="fa-solid fa-shapes"></i> SECTION 7: Shape Parameterization Strategies</span>

<!-- FLEXBOX BADGES (Perfectly Spaced & Formatted) -->
<div style="display: flex; gap: 12px; margin-top: 10px; margin-bottom: 25px; flex-wrap: wrap;">
  <img src="https://img.shields.io/badge/Math-Topology-000000?style=for-the-badge&logo=mathworks&logoColor=white" alt="Topology">
  <img src="https://img.shields.io/badge/Polynomials-Bernstein-00A6D6?style=for-the-badge&logo=python&logoColor=white" alt="Bernstein">
  <img src="https://img.shields.io/badge/Calculus-Numba_JIT-28A745?style=for-the-badge&logo=numba&logoColor=white" alt="Numba">
  <img src="https://img.shields.io/badge/Optimization-Hyperspace-6F42C1?style=for-the-badge&logo=polkadot&logoColor=white" alt="Hyperspace">
</div>

### <span style="color: #4682B4;"><i class="fa-solid fa-cube"></i> 7.1 The "Curse of Dimensionality"</span>

Before an Artificial Intelligence can optimize an airfoil, it must have a way to mathematically describe it. A standard `.dat` file consists of roughly 161 to 250 discrete $(X, Y)$ coordinate pairs. If the PyMoo AI tried to move every single $Y$-coordinate up and down independently, the optimization would be searching a **161-dimensional hyperspace**.

<div style="background-color: #FEF2F2; border-left: 5px solid #EF4444; padding: 15px; border-radius: 4px; color: #991B1B; margin-top: 15px; margin-bottom: 20px;">
  <strong><i class="fa-solid fa-triangle-exclamation"></i> The Physical Impossibility:</strong> To adequately explore 161 dimensions, the AI would require millions of generations. More importantly, if it randomly moved coordinate 32 up and coordinate 33 down, it would create a microscopic "sawtooth." In a Navier-Stokes CFD simulator, this jagged edge creates a mathematical singularity, causing the pressure gradients to explode and violently crashing the fluid solver.
</div>

**Shape Parameterization** solves this. It compresses the entire airfoil into a small handful of mathematical variables. By mutating these core variables, the AI can generate an infinite variety of shapes while mathematically guaranteeing the resulting surface remains smooth, continuous, and aerodynamically viable.

---

### <span style="color: #4682B4;"><i class="fa-solid fa-dna"></i> 7.2 Kulfan CST (Class Shape Transformation)</span>
**JSON Key:** `<span style="background-color: #E2E8F0; color: #334155; padding: 2px 6px; border-radius: 4px; font-family: monospace;">"shape_func": "cst"

Developed by Boeing aerodynamicist Brenda Kulfan, CST is the undisputed modern gold standard for aerospace topology. It is highly robust, mathematically elegant, and capable of representing almost any aerodynamic body using very few variables.

<div style="display: flex; flex-direction: column; gap: 15px; margin-top: 15px; margin-bottom: 25px;">

  <!-- Core Math Card -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #475569;"><i class="fa-solid fa-calculator" style="color: #3B82F6;"></i> 7.2.1 The Core Mathematics</h4>
    <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.95em; color: #444; line-height: 1.6;">The CST method separates the geometry into two distinct mathematical functions:</p>
    <ul style="margin-bottom: 0px; padding-left: 20px; font-size: 0.9em; color: #555; line-height: 1.6;">
      <li><strong style="color: #1E3A8A;">The Class Function $C(x)$:</strong> Defines the macro-geometry. By locking exponents to $N_1 = 0.5$ and $N_2 = 1.0$, the math elegantly guarantees a perfectly round leading edge (square root of $x$) and a sharp trailing edge (linear decay).</li>
      <li><strong style="color: #1E3A8A;">The Shape Function $S(x)$:</strong> A combination of Bernstein polynomials multiplied by "Weights." The PyMoo AI mutates these weights to inflate, deflate, or warp the base tear-drop shape.</li>
    </ul>
  </div>

  <!-- AeroForgeX Enhancements Card -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #475569;"><i class="fa-solid fa-bolt" style="color: #F59E0B;"></i> 7.2.2 AeroForgeX Specific Enhancements</h4>
    <ul style="margin-bottom: 0px; padding-left: 20px; font-size: 0.9em; color: #444; line-height: 1.6;">
      <li><strong style="color: #D97706;">The LE Modifier ($W_{LE}$):</strong> AeroForgeX isolates an independent weight explicitly tied to the leading edge radius. The AI can tune the Critical Mach number ($C_{p,min}$) without inadvertently thickening the main structural spar.</li>
      <li><strong style="color: #D97706;">Trailing Edge Wedge ($\Delta z_{TE}$):</strong> The TE gap is mathematically decoupled from the Bernstein weights. If you request a 0.5% blunt wedge for 3D printing, the AI is physically incapable of tapering it to a razor-sharp point.</li>
      <li><strong style="color: #D97706;">Cascade-Fit Filter:</strong> Reverse-engineering high-order CST weights from a `.dat` file often triggers <em>Runge's Phenomenon</em> (wild polynomial oscillations). AeroForgeX applies a Level-5 Cascade-Fit filter, stripping away wind-tunnel noise by fitting a low-order baseline first, ensuring flawless starting blueprints.</li>
    </ul>
  </div>

</div>

<div style="background-color: #ECFDF5; border: 1px solid #A7F3D0; padding: 15px; border-radius: 6px; margin-bottom: 25px;">
  <h4 style="margin-top: 0px; margin-bottom: 8px; color: #065F46;"><i class="fa-solid fa-book-open"></i> Engineering Guidelines</h4>
  <p style="margin-top: 0px; margin-bottom: 5px; font-size: 0.9em; color: #047857;"><strong>When to use:</strong> Clean-Sheet Design. Ideal for high-performance Transonic Envelopes as it naturally prevents high-frequency surface noise.</p>
  <p style="margin-top: 0px; margin-bottom: 5px; font-size: 0.9em; color: #047857;"><strong>The Optimizer Trap:</strong> CST variables are highly coupled (Weight #2 drastically alters Weight #3). Standard DE struggles to untangle this math. <strong>Always pair CST with the <code>shade</code> or <code>lshade</code> optimizer algorithms.</strong></p>
  <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.9em; color: #047857;"><strong>Sizing:</strong> Use 6 to 8 weights per side (12-16 variables). Going higher than 8 causes diminishing returns as the AI enters a 20+ dimensional hyperspace.</p>
</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-bezier-curve"></i> 7.3 Bezier Polygons (Bernstein Parameterization)</span>
**JSON Key:** `<span style="background-color: #E2E8F0; color: #334155; padding: 2px 6px; border-radius: 4px; font-family: monospace;">"shape_func": "bezier"

Bezier curves are heavily utilized in CAD software. Instead of passing <em>through</em> points, the curve is "pulled" toward floating Control Points, creating a localized gravity effect. The AI manipulates the $(X,Y)$ locations of these points.

<div style="display: flex; flex-direction: column; gap: 15px; margin-top: 15px; margin-bottom: 25px;">

  <!-- Inverse Problem Card -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #475569;"><i class="fa-solid fa-microchip" style="color: #8B5CF6;"></i> 7.3.1 The Parametric Inversion Problem</h4>
    <p style="margin-top: 0px; margin-bottom: 10px; font-size: 0.95em; color: #444; line-height: 1.6;">Fluid dynamics solvers cannot process parametric time-sweeps ($u$); they demand to know the exact $Y$ coordinate at a specific $X$ location. AeroForgeX solves this "Inverse Problem" using a highly optimized, Numba C-speed <strong>Newton-Raphson Root Finder</strong>. Millions of times per second, the software iteratively updates the derivative until $X(u)$ perfectly matches the requested coordinate, extracting $Y(u)$ with 64-bit precision.</p>
  </div>

  <!-- Rigid Boxes Card -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #475569;"><i class="fa-solid fa-border-all" style="color: #10B981;"></i> 7.3.2 Rigid Bounding Boxes</h4>
    <p style="margin-top: 0px; margin-bottom: 8px; font-size: 0.95em; color: #444; line-height: 1.6;">If the AI moves Control Point 3 physically in front of Point 2 on the X-axis, the surface loops backward over itself into a knot, crashing Fortran. AeroForgeX implements <strong>Rigid Bounding Boxes</strong>. The AI's mutations are mathematically confined so points can never cross each other, guaranteeing a 100% valid, non-intersecting mesh every generation.</p>
  </div>

</div>

<div style="background-color: #ECFDF5; border: 1px solid #A7F3D0; padding: 15px; border-radius: 6px; margin-bottom: 25px;">
  <h4 style="margin-top: 0px; margin-bottom: 8px; color: #065F46;"><i class="fa-solid fa-book-open"></i> Engineering Guidelines</h4>
  <p style="margin-top: 0px; margin-bottom: 5px; font-size: 0.9em; color: #047857;"><strong>When to use:</strong> Thick Structural Roots. Bezier curves easily form smooth, balloon-like structures for wind turbine blades, whereas CST often struggles with massive thickness.</p>
  <p style="margin-top: 0px; margin-bottom: 5px; font-size: 0.9em; color: #047857;"><strong>Optimizer Pairing:</strong> Because Bezier variables are highly localized, the highly stable <strong><code>jde</code> (Self-Adaptive DE)</strong> algorithm is the perfect pairing.</p>
</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-wave-square"></i> 7.4 Hicks-Henne Sine Bumps</span>
**JSON Key:** `<span style="background-color: #E2E8F0; color: #334155; padding: 2px 6px; border-radius: 4px; font-family: monospace;">"shape_func": "hicks-henne"

Unlike CST and Bezier (which delete the Seed and rebuild it from scratch), Hicks-Henne **keeps your original Seed airfoil intact** and mathematically superimposes localized Sine-Wave bumps over the top of it.

<div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 18px; border-radius: 6px; margin-top: 15px; margin-bottom: 25px;">
  <p style="margin-top: 0px; margin-bottom: 10px; color: #475569; font-weight: bold;"><i class="fa-solid fa-calculator"></i> The Mathematical DNA:</p>
  <p style="margin-top: 0px; margin-bottom: 12px; font-size: 0.95em; color: #444; line-height: 1.6;">The AI manipulates three independent variables for every single bump: <strong>Strength ($S$)</strong>, <strong>Location ($L$)</strong>, and <strong>Width ($W$)</strong>. If you request 5 bumps on top and 3 on bottom, the AI controls $8 \times 3 = \mathbf{24}$ variables.</p>

  <h5 style="margin-top: 0px; margin-bottom: 5px; color: #0F172A;"><i class="fa-solid fa-broom"></i> The <code>smooth_seed</code> Integration</h5>
  <p style="margin-top: 0px; margin-bottom: 12px; font-size: 0.9em; color: #64748B; line-height: 1.5;">If you apply a pristine Hicks-Henne bump to a noisy, digitized coordinate file, the fluid solver crashes. Setting <code>"smooth_seed": true</code> secretly runs the Seed through a Nelder-Mead filter to "shrink-wrap" it into a flawless polynomial <em>before</em> bumps are applied.</p>
  
  <h5 style="margin-top: 0px; margin-bottom: 5px; color: #0F172A;"><i class="fa-solid fa-fighter-jet"></i> Primary Engineering Use-Case: Transonic Shock Mitigation</h5>
  <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.9em; color: #64748B; line-height: 1.5;">In high-subsonic flight, supersonic shockwaves cause massive wave drag. Applying a subtle, negative Hicks-Henne bump exactly at the shock location creates a "flattened rooftop" on the pressure distribution. This encourages the flow to compress <em>isentropically</em> (gradually) rather than violently shocking, slashing drag without ruining the rest of your proprietary corporate design.</p>
</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-up-right-and-down-left-from-center"></i> 7.5 Camb-Thick (Global Affine Scaling)</span>
**JSON Key:** `<span style="background-color: #E2E8F0; color: #334155; padding: 2px 6px; border-radius: 4px; font-family: monospace;">"shape_func": "camb-thick"

This is not a curve-generator; it is a **Global Morphing Engine**. It subjects the entire airfoil to rigid affine transformations using only 6 highly restricted scalar variables (e.g., Max Thickness Multiplier, Max Camber X-Shift).

<div style="display: flex; flex-direction: column; gap: 15px; margin-top: 15px; margin-bottom: 25px;">

  <!-- Affine Card -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #475569;"><i class="fa-solid fa-compress" style="color: #10B981;"></i> 7.5.1 The Monotonic Enforcement Algorithm</h4>
    <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.95em; color: #444; line-height: 1.6;">AeroForgeX does not just multiply the $Y$-coordinates by a flat scalar (which would distort the leading-edge radius). It uses a localized natural cubic spline to isolate the exact sub-panel peak of the thickness distribution. When shifting the X-location, it uses an arccosine stretching algorithm to ensure surrounding coordinates stretch elastically like a rubber band, preventing the mesh from tearing.</p>
  </div>

  <!-- Use-Case Card -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h4 style="margin-top: 0px; margin-bottom: 10px; color: #475569;"><i class="fa-solid fa-building-user" style="color: #3B82F6;"></i> 7.5.2 Structural Engineering Conflicts</h4>
    <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.95em; color: #444; line-height: 1.6;">If aerodynamics designed a perfect 12% thick airfoil, but structures needs 15% to fit the carbon-fiber spar, you use Camb-Thick. It perfectly scales to 15% while preserving the exact aerodynamic "character" and pressure distribution shape of the original baseline.</p>
  </div>

</div>

<div style="background-color: #FFFBEB; border: 1px solid #FCD34D; border-left: 5px solid #F59E0B; padding: 15px; border-radius: 6px; margin-bottom: 25px;">
  <h4 style="margin-top: 0px; margin-bottom: 10px; color: #92400E;"><i class="fa-solid fa-lightbulb"></i> PRO-TIP: Curvature Check Override</h4>
  <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.95em; color: #78350F; line-height: 1.6;">Because Camb-Thick scaling physically cannot introduce high-frequency "spikes" to a surface (it only stretches what is already there), AeroForgeX automatically disables the <code>"check_curvature"</code> constraint during a Camb-Thick run. This saves massive amounts of CPU time, allowing the PyMoo AI to optimize rapid-prototyping concepts in less than 30 generations using Standard <code>de</code>.</p>
</div>