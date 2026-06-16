

***

<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">

## <span style="color: #00BFFF;"><i class="fa-solid fa-microchip"></i> SECTION 12: Hidden Logic & Auto-Overrides</span>

<!-- FLEXBOX BADGES (Perfectly Spaced & Formatted) -->
<div style="display: flex; gap: 12px; margin-top: 10px; margin-bottom: 25px; flex-wrap: wrap;">
  <img src="https://img.shields.io/badge/Algorithm-Dynamic_Weighting-000000?style=for-the-badge&logo=polkadot&logoColor=white" alt="Dynamic Weighting">
  <img src="https://img.shields.io/badge/Logic-PyMoo_Overrides-00A6D6?style=for-the-badge&logo=python&logoColor=white" alt="PyMoo Overrides">
  <img src="https://img.shields.io/badge/Safety-Math_Clamping-28A745?style=for-the-badge&logo=shield&logoColor=white" alt="Math Clamping">
  <img src="https://img.shields.io/badge/Normalization-1.0_Scaling-6F42C1?style=for-the-badge&logo=supersede&logoColor=white" alt="1.0 Scaling">
</div>

### <span style="color: #4682B4;"><i class="fa-solid fa-scale-unbalanced-flip"></i> 12.1 Deep Dive: The Dynamic Weighting Engine</span>

In multi-point Multidisciplinary Design Optimization (MDO), Evolutionary Algorithms often suffer from "Objective Collapse." If you ask the AI to minimize Cruise Drag (OP1) while maximizing Climb Lift (OP2), the AI evaluates the mathematical gradients. If dropping Drag is mathematically "easier," it takes the lazy route, completely ignoring the Lift requirement because doing so yields a slightly better total average score.

The Dynamic Weighting Engine acts as an intelligent **"Lag Detector."** It actively monitors the swarm, detects if a specific engineering goal is being ignored, and mathematically punishes the swarm by exponentially inflating the weight of the lagging target.

#### <span style="color: #1E90FF; font-weight: bold;"><i class="fa-solid fa-cogs"></i> 1. Core Objects & JSON Parameters</span>
Under the hood, AeroForgeX parses your JSON into a strict Python object called `DynamicWeightingSpecType`.

<div style="background-color: #1E1E1E; padding: 15px; border-radius: 6px; margin-bottom: 15px; border: 1px solid #333;">
  <pre style="margin: 0px; background-color: #1E1E1E; color: #D4D4D4; border: none; font-family: monospace; font-size: 0.85em; line-height: 1.5; white-space: pre-wrap;">"dynamic_weighting": true,
"dynamic_weighting_spec": {
  <span style="color: #C586C0; font-weight: bold;">"min_w": 0.5, "max_w": 10.0</span>,
  <span style="color: #4EC9B0; font-weight: bold;">"extra_punch": 2.0</span>,
  "frequency": 20,
  "start_with_design": 10
}</pre>
</div>

<ul style="margin-bottom: 25px; padding-left: 20px; font-size: 0.9em; color: #444; line-height: 1.7;">
  <li><strong style="color: #D97706;">min_w / max_w (Floats):</strong> Absolute boundaries. If a target succeeds perfectly, its weight drops toward <code>min_w</code>. If it is failing, it inflates toward <code>max_w</code>.</li>
  <li><strong style="color: #D97706;">frequency (Integer):</strong> The engine halts the optimizer and recalculates the lag multipliers every $X$ generations.</li>
  <li><strong style="color: #D97706;">start_with_design (Burn-In):</strong> Delays activation. Gen 0 is totally chaotic. If the engine activated immediately, it would apply massive punishments based on random noise. This allows the swarm to settle into a "valley" first.</li>
  <li><strong style="color: #10B981;">extra_punch (Violation Multiplier):</strong> If a target fails catastrophically compared to the rest of the matrix, the engine squares this number and multiplies the penalty weight, violently forcing the swarm to correct.</li>
</ul>

#### <span style="color: #1E90FF; font-weight: bold;"><i class="fa-solid fa-square-root-variable"></i> 2. Deviation Math: How "Failure" is Calculated</span>
How the engine calculates "Deviation" (`dev`) depends entirely on the Objective Type you selected.

<div style="display: flex; flex-direction: column; gap: 15px; margin-bottom: 25px;">

  <!-- Target Objectives -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; border-left: 4px solid #3B82F6;">
    <h5 style="margin-top: 0px; margin-bottom: 8px; color: #1E3A8A;">A. The "Target" Objectives (<code>target-drag</code>, <code>target-moment</code>)</h5>
    <p style="margin-top: 0px; margin-bottom: 8px; font-size: 0.9em; color: #444;">Calculates the absolute distance between current performance and your <code>tgt_val</code>. However, the <code>allow_improved_target</code> rule dictates how over-achievement is handled:</p>
    <ul style="margin-bottom: 8px; padding-left: 20px; font-size: 0.9em; color: #444; line-height: 1.6;">
      <li><strong>If <code>true</code>:</strong> The AI is not penalized for overachieving. If target drag is 0.015, and the AI discovers 0.012, deviation is clamped to <code>0.0</code>. Target satisfied.</li>
      <li><strong>If <code>false</code>:</strong> (Critical for exact Pitching Moment trim). Overshooting the target generates a massive deviation penalty, forcing the AI to perfectly hit the exact number.</li>
    </ul>
    <div style="background-color: #E2E8F0; padding: 8px; border-radius: 4px; font-size: 0.85em; color: #334155;">
      <strong>Micro-Tolerance Catchers:</strong> To prevent the AI from infinitely chasing microscopic floating-point errors, hardcoded deadbands exist: If <code>target-drag</code> deviation is $<0.000004$, deviation is forced to <code>0.0</code>. If <code>target-glide</code> deviation is $<0.01$, deviation is <code>0.0</code>.
    </div>
  </div>

  <!-- Min/Max Objectives -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; border-left: 4px solid #10B981;">
    <h5 style="margin-top: 0px; margin-bottom: 8px; color: #065F46;">B. The "Min/Max" Objectives (<code>min-drag</code>, <code>max-glide</code>)</h5>
    <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.9em; color: #444; line-height: 1.6;">Unlike explicit targets, these are open-ended. To track deviation, AeroForgeX runs an <strong>Initial Seed Calibration</strong>. It evaluates your baseline <code>.dat</code> seed airfoil and locks its scores as the baseline target. Deviation is then calculated continuously as a percentage improvement (or failure) compared to the original Seed.</p>
  </div>

  <!-- Geometric Targets -->
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; border-left: 4px solid #F59E0B;">
    <h5 style="margin-top: 0px; margin-bottom: 8px; color: #92400E;">C. Geometric Soft-Targets (<code>thickness</code>, <code>camber</code>)</h5>
    <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.9em; color: #444;">Structural targets are treated identically to aerodynamic points. <br><strong>Deviation Math:</strong> <code>dev = ((current_thick - target_thick) / target_thick) * 100.0</code></p>
  </div>

</div>

#### <span style="color: #1E90FF; font-weight: bold;"><i class="fa-solid fa-bolt"></i> 3. The Mathematical Execution Engine</span>
When the frequency triggers, the algorithm executes the <code>do_dynamic_weighting</code> restructure:

<div style="display: flex; flex-direction: column; gap: 12px; margin-bottom: 25px;">
  
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 12px; border-radius: 6px;">
    <p style="margin: 0px; font-size: 0.9em; color: #444;"><strong>Step 1: Calculate System Averages.</strong> Calculates the absolute deviation (<code>abs(t.dev)</code>) of every active target, establishing the System Average Deviation (<code>avg_d</code>) and Median Deviation (<code>med_d</code>).</p>
  </div>
  
  <div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 12px; border-radius: 6px;">
    <p style="margin: 0px; font-size: 0.9em; color: #444;"><strong>Step 2: Normalize Weights.</strong> New weight = <code>abs(t.dev) / avg_d</code>. If a target's deviation is exactly average, its weight becomes 1.0. If failing twice as bad as average, weight becomes 2.0.</p>
  </div>

  <div style="background-color: #FEF2F2; border: 1px solid #FECACA; padding: 15px; border-radius: 6px; border-left: 4px solid #EF4444;">
    <h5 style="margin-top: 0px; margin-bottom: 8px; color: #991B1B;">Step 3: Trigger the "Extra Punch" (The Punishment Phase)</h5>
    <ul style="margin-bottom: 0px; padding-left: 20px; font-size: 0.9em; color: #7F1D1D; line-height: 1.6;">
      <li><strong>Level 1 (Lagging):</strong> If deviation is $>1.5\times$ Average (and Average $> 0.1$), weight is multiplied by <code>extra_punch</code> (e.g., $1.0 \times 2.0 = 2.0$).</li>
      <li><strong>Level 2 (Catastrophic):</strong> If deviation is $>3.0\times$ Average (and Average $> 0.3$), weight is multiplied by <code>extra_punch</code> <strong>squared</strong> (e.g., $1.0 \times 2.0^2 = 4.0$).</li>
      <li><strong>Geometric Note:</strong> Geometric physical deviations use the System <em>Median</em>, because physical $Y/C$ deviations are vastly different in numerical scale than aerodynamic $C_D$ deviations.</li>
    </ul>
  </div>

  <div style="background-color: #ECFDF5; border: 1px solid #A7F3D0; padding: 15px; border-radius: 6px; border-left: 4px solid #10B981;">
    <h5 style="margin-top: 0px; margin-bottom: 8px; color: #065F46;">Step 4: The PyMoo Normalization Lock ($sf$)</h5>
    <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.9em; color: #047857; line-height: 1.6;">If AeroForgeX simply multiplied weights, the total objective score would jump from <code>0.85</code> to <code>45.0</code> in a single generation, destroying the PyMoo gradient descent. AeroForgeX calculates a Global Scaling Factor ($sf$), dividing the old objective score by the new weighted score, scaling all weights down proportionally. Internal target relationships shift radically, but the Total Final Objective Score remains perfectly continuous.</p>
  </div>

</div>

---

### <span style="color: #4682B4;"><i class="fa-solid fa-mask"></i> 12.2 Hidden Logic, Variable Math & Auto-Overrides</span>

#### <span style="color: #1E90FF; font-weight: bold;"><i class="fa-solid fa-users"></i> 12.2.1 The Population Size Override (The 10×NDV Rule)</span>
You configured your JSON to use `"population_size": 30`. However, the terminal reports `Population Matrix: 140`. Why?
<div style="background-color: #FFFBEB; border-left: 4px solid #F59E0B; padding: 12px; border-radius: 4px; color: #92400E; font-size: 0.9em; margin-bottom: 20px;">
  <strong>Code Logic:</strong> <code>Final_pop = max(requested_pop, NDV * 10)</code><br>
  <strong>Engineering Reason:</strong> Evolutionary Algorithms suffer from "Genetic Stagnation" if they lack particles to explore the hyperspace. AeroForgeX strictly enforces the golden rule of machine learning: Population must be at least $10 \times$ the Number of Design Variables (NDV). The software overrides your JSON to save the run from failing.
</div>

#### <span style="color: #1E90FF; font-weight: bold;"><i class="fa-solid fa-square-root-variable"></i> 12.2.2 How Design Variables (NDV) are Calculated</span>
The AI does not optimize $X/Y$ coordinates; it optimizes Design Variables. How many variables is the AI actually controlling?

<div style="display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 25px;">
  
  <!-- CST -->
  <div style="flex: 1 1 45%; background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h5 style="margin-top: 0px; margin-bottom: 8px; color: #1E3A8A;">1. Kulfan CST</h5>
    <div style="background-color: #1E1E1E; padding: 6px; border-radius: 4px; font-family: monospace; font-size: 0.85em; color: #9CDCFE; margin-bottom: 8px;">NDV = n_weights_top + n_weights_bot + 2</div>
    <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.9em; color: #444; line-height: 1.5;">If 6 top / 6 bottom, NDV is 14. Why the extra 2? AeroForgeX permanently injects hidden variables: +1 for Leading Edge Radius, +1 for Trailing Edge wedge thickness.</p>
  </div>

  <!-- Bezier -->
  <div style="flex: 1 1 45%; background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h5 style="margin-top: 0px; margin-bottom: 8px; color: #1E3A8A;">2. Bezier Polygons</h5>
    <div style="background-color: #1E1E1E; padding: 6px; border-radius: 4px; font-family: monospace; font-size: 0.85em; color: #9CDCFE; margin-bottom: 8px;">NDV_Side = (ncp - 3) * 2 + 2</div>
    <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.9em; color: #444; line-height: 1.5;">If 6 Control Points (CPs) per side, NDV is 8. P0 (LE) is locked to $(0,0)$. P_end (TE) is locked to $X=1.0$ (leaving its Y height). P1 is locked to $X=0.0$ (leaving its Y height). The 3 middle CPs have freedom in both X and Y ($3 \times 2 = 6$).</p>
  </div>

  <!-- Hicks -->
  <div style="flex: 1 1 45%; background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h5 style="margin-top: 0px; margin-bottom: 8px; color: #1E3A8A;">3. Hicks-Henne Sine Bumps</h5>
    <div style="background-color: #1E1E1E; padding: 6px; border-radius: 4px; font-family: monospace; font-size: 0.85em; color: #9CDCFE; margin-bottom: 8px;">NDV = (n_top * 3) + (n_bot * 3)</div>
    <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.9em; color: #444; line-height: 1.5;">Every single bump adds exactly 3 variables: Strength (Amplitude), Location (X-axis), and Width. 5 bumps = 15 variables.</p>
  </div>

  <!-- Misc -->
  <div style="flex: 1 1 45%; background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px;">
    <h5 style="margin-top: 0px; margin-bottom: 8px; color: #1E3A8A;">4. Camb-Thick & Flaps</h5>
    <p style="margin-top: 0px; margin-bottom: 8px; font-size: 0.9em; color: #444; line-height: 1.5;"><strong>Camb-Thick:</strong> NDV = Sum of active boolean toggles. (Max 6).</p>
    <p style="margin-top: 0px; margin-bottom: 0px; font-size: 0.9em; color: #444; line-height: 1.5;"><strong>Flaps:</strong> NDV = Sum of <code>true</code> items in <code>flap_opt</code> array. If <code>[false, true, false, true, true]</code>, it adds 3 independent flap angles.</p>
  </div>

</div>

#### <span style="color: #1E90FF; font-weight: bold;"><i class="fa-solid fa-shield-halved"></i> 12.2.3 Weight Normalization & Dynamic Safety Locks</span>

<div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 18px; border-radius: 6px; margin-bottom: 25px;">
  <ul style="margin-bottom: 0px; padding-left: 20px; font-size: 0.9em; color: #444; line-height: 1.7;">
    <li style="margin-bottom: 10px;"><strong style="color: #2563EB;">1. The Sum-to-One Normalizer:</strong> If OP1 weight is 2.0 and OP2 is 8.0, AeroForgeX divides by the sum (10.0). OP1 becomes 0.2 (20% importance) and OP2 becomes 0.8 (80%). This normalizes the PyMoo objective score calculation.</li>  <li style="margin-bottom: 10px;"><strong style="color: #2563EB;">2. The Negative Weight Override (Static Lock):</strong> If you set <code>"weight": -5.0</code>, it converts to positive 5.0, but <strong>permanently disables Dynamic Weighting</strong> for that specific target. This allows you to apply a massive, unyielding gravitational pull to a critical structural target that the engine is not allowed to touch.</li>  <li><strong style="color: #DC2626;">3. The Minimum-3 Dynamic Shutdown:</strong> If the sum of targets with Dynamic Weighting active is $<3$, the system prints <code>[ NOTE ] Dynamic weighting deactivated (Math constraint)</code> and shuts the engine off. <em>Reason:</em> Calculating an "average deviation" with only 2 targets is mathematically volatile, causing penalty multipliers to wildly oscillate and destroying PyMoo gradients.</li>  </ul>
</div>

#### <span style="color: #1E90FF; font-weight: bold;"><i class="fa-solid fa-wrench"></i> 12.2.4 Geometry & Target Auto-Corrections</span>

<div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; margin-bottom: 25px;">
  <ul style="margin-bottom: 0px; padding-left: 20px; font-size: 0.9em; color: #444; line-height: 1.7;">
    <li style="margin-bottom: 10px;"><strong style="color: #D97706;">The Negative Target Multiplier:</strong> If you use <code>"target-drag"</code> and set <code>"tgt_val": -0.5</code>, AeroForgeX treats it as a percentage of the seed! It extracts the baseline Drag (e.g., 0.020) and multiplies by the absolute value ($0.020 \times 0.5 = 0.010$). You commanded: <em>"Target 50% of baseline."</em></li> <li style="margin-bottom: 10px;"><strong style="color: #D97706;">Flap Angle Bounding Clamp:</strong> If your starting guess is $35^\circ$, but constraints limit flaps to $15^\circ$, the system intercepts the array, permanently overrides your guess to 15.0, and prints <code>[ WARN ] Flap viol OP. Confining to max bound.</code></li>    <li style="margin-bottom: 10px;"><strong style="color: #D97706;">The Re Type 2 Imaginary Root Fix:</strong> In XFOIL, Type 2 Reynolds means $Re \propto 1/\sqrt{C_L}$. If you ask for negative $C_L$, XFOIL attempts the square root of a negative number, generating <code>NaN</code> and crashing. AeroForgeX detects this, downgrades to a Type 1 constant Reynolds, and proceeds safely.</li>
    
    <li><strong style="color: #D97706;">Shape-Specific Overrides:</strong> 
      <ul style="margin-top: 4px; margin-bottom: 0px; color: #555;">
        <li><strong>Camb-Thick:</strong> Forces <code>"check_curvature": false</code> (affine scaling cannot introduce spikes). Forces <code>"max_retries": 0</code> to strip bounds-checking overhead and execute at max speed.</li>
        <li><strong>Bezier:</strong> Forces <code>"check_curvature_bumps": false</code> (Bernstein polynomials are analytically continuous; they cannot generate jagged micro-spikes).</li>
      </ul>
    </li>  </ul> </div>

#### <span style="color: #1E90FF; font-weight: bold;"><i class="fa-solid fa-wave-square"></i> 12.2.5 The Auto-Curvature Mathematics</span>
If you set `"auto_curv": true`, how does the AI calculate the noise limits of your Seed Airfoil?
<div style="background-color: #F8F9FA; border: 1px solid #E2E8F0; padding: 15px; border-radius: 6px; margin-bottom: 25px;">
  <ol style="margin-bottom: 0px; padding-left: 20px; font-size: 0.9em; color: #444; line-height: 1.7;">
    <li><strong>Macro-Reversals:</strong> Runs the algorithm on the Seed's 2nd-derivative. Finds the exact amplitude that triggers the baseline's reversals, and sets the AI limit to <code>Threshold * 1.1</code> (allowing a 10% tolerance margin above the seed's noise floor).</li>
    <li><strong>Micro-Spikes:</strong> Runs the algorithm on the derivative of the curvature (3rd-derivative). Sets the limit to <code>max(Threshold * 1.1, Threshold + 0.03)</code>.</li>
    <li><strong>TE Curvature:</strong> Extracts maximum curvature at the trailing edge. Locks PyMoo limit to <code>max(TE_Curv * 1.1, TE_Curv + 0.05)</code>.</li>
  </ol>
</div>

#### <span style="color: #1E90FF; font-weight: bold;"><i class="fa-solid fa-percentage"></i> 12.2.6 The Aerodynamic Penalty Scaling (The 1.0 Logic)</span>
In PyMoo, all objective functions ($F_{obj}$) are summed into a single float. How do you add Drag (0.015) and L/D Ratio (45.5) together without L/D crushing Drag?
<div style="background-color: #ECFDF5; border: 1px solid #A7F3D0; padding: 15px; border-radius: 6px; color: #065F46; font-size: 0.9em; margin-bottom: 25px;">
  Before Gen 1, the software evaluates your Seed airfoil across all operating points.<br>
  • If OP1 returns Drag=0.015, it assigns a permanent scale factor of <code>(1.0 / 0.015)</code>.<br>
  • When the AI evaluates a new airfoil (e.g., Drag = 0.012), it multiplies: $0.012 \times (1.0/0.015) = 0.80$.<br>
  <strong>Explanation:</strong> Every aerodynamic point is normalized so the Seed equals exactly <code>1.000</code>. The final printed <code>Obj: 0.850</code> in the terminal means the new airfoil is performing exactly 15% better than the seed across the entire unified matrix!
</div>

#### <span style="color: #1E90FF; font-weight: bold;"><i class="fa-solid fa-seedling"></i> 12.2.7 The CST Micro-Seeding Protocol</span>
If you set `"init_pert": 0.10` (10% swarm scatter), CST exponents violently warp the airfoil. 
<div style="background-color: #FEF2F2; border-left: 4px solid #EF4444; padding: 15px; border-radius: 4px; color: #991B1B; font-size: 0.9em; margin-bottom: 25px;">
  AeroForgeX overrides this to 0.04 (4%) for main weights. More importantly, the Leading Edge Radius and Trailing Edge Thickness are <strong>Micro-Seeded</strong>. They are locked to a maximum <code>0.5% to 1.0%</code> scatter. Altering the stagnation point drastically causes immediate Newton-Raphson boundary layer crashes on Generation 0. Micro-seeding ensures the AI begins in a safe aerodynamic space before taking larger leaps in later generations.
</div>
