# Video 2 — FARMOPTIMIZER: "Optimize the farm" (target 4:30)

**Look of this solution:** earth-amber banner with a scenario-bars icon (it appears when you open the FarmOptimizer page). Everything — buttons, tabs, headings — turns amber, so Video 2 looks different from Video 1.

## Set-up before recording (5 minutes)
1. `streamlit run app.py`, browser 110% zoom, 1920×1080.
2. Sidebar: Maharashtra / Pune, area **10 acres**, budget **₹2,50,000**, water **3000 m³**. (Weather is not used by FarmOptimizer, so offline mode does not matter.)
3. Click **FarmOptimizer**. Crops to compare: **Maize, Soybean, Groundnut, Rice**. "What matters most?" = **Balanced**. Open **What-ifs and scenario settings** once and confirm: 1000 simulations, seed 42.
4. Do a dry run first so you know which mix the optimiser gives; read the real numbers on screen when you record.

## Script

| Time | On screen (what to click) | Narration |
|---|---|---|
| 0:00 | Dashboard, then click **FarmOptimizer** (amber banner appears) | "A forecast covers one week. A farmer choosing crops for a whole season needs something else. This is Solution 2: **FarmOptimizer** — which crop mix still pays off in good *and* bad seasons?" |
| 0:25 | Point at the amber banner and the two solution names | "It is a separate engine from AgroCast with its own look. The only thing they share is the crop table." |
| 0:45 | Inputs row: crops, priority, land, budget, water | "The farmer picks the crops to compare, what matters most — highest profit, least water, lowest risk or balanced — and the land, budget and water they really have." |
| 1:15 | Open **What-ifs and scenario settings** | "We simulate a thousand seasons: normal, drought and excess rain, with editable probabilities and severity. They are simulations, not forecasts, and the random seed is fixed so anyone can reproduce the result." |
| 1:50 | **Math & assumptions** tab | "Yield uses the FAO-33 water-production function with a penalty for waterlogging. The optimiser is a linear programme that maximises expected profit plus CVaR — the average of the worst ten percent of seasons — subject to land, budget and water." |
| 2:30 | **Recommended strategy** tab | "Balanced priority gives this mix of acres. Here are expected profit, profit in the worst ten percent of seasons, chance of loss, extra water needed and a 0–100 resilience score." Point at the allocation chart and the profit-by-scenario chart. |
| 3:00 | Switch **What matters most?** to Highest profit → Lowest risk → Least water | "Change the priority and watch the mix change. Describe what you actually see: which crops gain or lose acres, and how profit, risk and water move." |
| 3:35 | **Strategy comparison** tab | "Our optimised plans against simple baselines — an even split and each single crop — on the same thousand seasons. The benefit is measured, not claimed." |
| 3:55 | Open **What-ifs**: rainfall −30%, cost +15%; set **Budget** to 20000; water slider 50% | "Everything recalculates. If the constraints are impossible, the app says so instead of showing a wrong plan." |
| 4:15 | **Report** page → Download PDF | "The plan goes into the same PDF report." |
| 4:25 | Amber banner | "FarmOptimizer: robust, constraint-aware crop planning with open assumptions. Estimates, not guarantees." |

## Closing line for both videos (optional 10-second outro)
"Agri-Shield AI: Predict the risk with AgroCast. Optimize the farm with FarmOptimizer. Protect the harvest."
