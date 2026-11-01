# AGRI-SHIELD AI — Project Report (HackVerse 2026, College Track, Round 2)
**Team:** [TEAM NAME] | **Institution:** [COLLEGE] | **Members & contributions:** [NAME – contribution] ×N

## 1. Problem statement
Unpredictable weather makes traditional farming calendars unreliable and causes crop loss. Build a technology system giving small-scale Indian farmers data-driven foresight to reduce climate-related losses.

## 2. Objectives
(1) Warn farmers early about crop-specific hazards; (2) advise irrigation timing/volume; (3) compare farming strategies under uncertainty within land, budget and water limits; (4) explain every output in plain language; (5) stay usable offline and be transparent about data quality.

## 3. Architecture
Streamlit UI (`app.py`, `views/`) → engines (`engine/`) → data (`data/`, Open-Meteo) + SQLite (`database/`) + PDF (`utils/`).
Data flow AgroCast: farm config → weather (Open-Meteo or labelled sample) → clean/impute → stage detection → hazard scores + soil-water bucket → irrigation advice → alerts → PDF.
Data flow FarmOptimizer: crops + constraints + rainfall assumptions → Monte-Carlo scenarios (seeded) → per-crop yield/profit matrix → CVaR LP → strategy table → PDF.
The two flows share only the crop table.

## 4. Solution One — AgroCast (explanation)
Hazards: heat, cold, drought/moisture stress, excess rainfall, flooding/waterlogging indicator, fungal-favourable weather. Each = 100 × stage sensitivity × Σ(weight × normalised feature); features: days beyond crop thresholds, exceedance size, forecast/past rain, max daily rain, wet-day runs, soil drainage, projected root-zone water. Output per hazard: score, category (Low <25, Moderate <50, High <75, Severe), contributing factors in points, plain-language action. Overall = highest hazard (weakest link).

## 5. Solution Two — FarmOptimizer (explanation)
Simulates S ≥ 1000 seasonal rainfall multipliers from a Normal/Drought/Excess mixture (editable probabilities, severity, global rainfall shift). For each crop and scenario computes yield and profit; the LP chooses acres to maximise (1−λ)·E[profit] + λ·CVaR₁₀%. Priorities: profit (λ=0), balanced (0.5), risk (0.85), water (min expected irrigation s.t. ≥70% of best expected profit). Climate Resilience Score defined in §6.

## 6. Mathematical methodology
* Soil water: AW_{t+1} = clip(AW_t + 0.8·P_t − ET0_t·Kc, 0, TAW); TAW = AWC(soil)·root depth·stage factor; stress when AW < (1−p)·TAW (FAO-56).
* Missing ET0: Hargreaves, ET0 = 0.0023(T̄+17.8)√(Tmax−Tmin)·Ra.
* Yield: Y = Ym·[1 − Ky(1 − ETa/ETm)]·[1 − W·clip((m−1.3)/0.7,0,1)] (FAO-33 form + waterlogging term); ETa = min(ETm, η·Rn·m + I_plan).
* CVaR LP (Rockafellar–Uryasev): max (1−λ)·ā·x + λ(z − 1/(αS)Σu_s) s.t. u_s ≥ z − a_s·x, u_s ≥ 0, Σx ≤ area, cost·x ≤ budget, water_plan·x ≤ water, lo ≤ x ≤ hi.
* Resilience score = 100·[0.35(1−P_loss) + 0.30·min(CVaR/mean,1) + 0.20(1−min(CV_yield,1)) + 0.15(1−E[water]/available)]. Weights are our design choice, stated openly.

## 7. Algorithms / modules
`weather_engine` (fetch, clean, impute) · `climate_risk` · `irrigation_engine` · `scenario_generator` · `optimization_engine` (HiGHS via SciPy `linprog`) · `recommendation_engine` · `database` · `pdf_generator`.

## 8. Technology stack
Python, Streamlit, Plotly, Pandas, NumPy, SciPy, ReportLab, SQLite, Open-Meteo (free, keyless).

## 9. Data sources
Open-Meteo forecast API (live); synthetic sample weather (offline demo, labelled); crop parameters from FAO-56/FAO-33-style literature and approximate public MSP/FRP levels — **to be verified and cited by the team** [add exact table/edition and year]; IMD all-India monsoon long-period average ≈ 87 cm used as default kharif normal.

## 10. Unique contributions
Two methodologically different engines on one crop model; transparent point-contribution explanations; measured-vs-estimated moisture labelling; CVaR-based robust crop planning with what-if controls; data-provenance labels; offline mode; PDF report.

## 11. Results and demonstrations
[Insert screenshots after running the app. Sample reproducible run (10 acres, ₹2.5 lakh, 3000 m³, Rice/Maize/Soybean/Cotton/Groundnut, seed 42, 1000 sims): optimiser outputs differ by priority; baselines (even split, single crop) are evaluated on the same scenarios. Re-run and paste your own numbers.]

## 12. Limitations
Heuristic scores not validated against yield-loss data; no trained ML; fungal indicator is not a disease model; illustrative crop economics; fixed price (no volatility); no sowing-date or pest modelling; district-level rainfall normals are user-entered; forecast skill is that of Open-Meteo.

## 13. Future scope
Calibrate thresholds with ICAR/IMD district data; validated disease models; price-volatility scenarios; SMS/WhatsApp/regional-language alerts; sowing-date optimisation; satellite soil-moisture; pilot with a KVK.

## 14. References (verify before submission)
Allen et al., FAO Irrigation & Drainage Paper 56 (1998); Doorenbos & Kassam, FAO Paper 33 (1979); Rockafellar & Uryasev, "Optimization of Conditional Value-at-Risk", J. Risk 2000; Open-Meteo documentation; IMD; CACP/Govt of India MSP/FRP notifications.

## 15. AI tools and models used
[List: e.g., Claude (Anthropic) used for code generation/drafting, reviewed and tested by team; no trained ML model inside the product.]
