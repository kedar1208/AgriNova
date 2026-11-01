# AGRINOVA — Predict the Risk. Optimize the Farm. Protect the Harvest.
HackVerse 2026 · College Track · Round 2. Team: **[TEAM NAME]** · **[COLLEGE]** · Members: **[NAMES]**

Two independent solutions to climate-unreliable farming calendars (small-scale Indian farmers):

| | AgroCast (predictive) | FarmOptimizer (decision optimisation) |
|---|---|---|
| Question | Which climate risks hit my existing crop in the next 7 days? | Which crop mix is most resilient over uncertain seasons? |
| Core methods | Weather cleaning/imputation, stage-weighted threshold scores, FAO-56 soil-water bucket | Monte-Carlo rainfall scenarios, FAO-33 yield response, CVaR linear programming (SciPy/HiGHS) |
| Files | `engine/climate_risk.py`, `irrigation_engine.py`, `weather_engine.py` | `engine/scenario_generator.py`, `optimization_engine.py` |

They do not import each other; they share only `engine/crop_database.py` + `data/crops.csv`.

## Run
```bash
pip install -r requirements.txt
streamlit run app.py          # tick "Offline demonstration mode" in the sidebar to run without internet
python -m unittest discover -s tests -t .      # or: pytest
```
`views/` (not `pages/`) holds UI modules so Streamlit doesn't create a duplicate auto-navigation.

## New in this version: landing page and redesigned dashboards
* The app now opens on a landing page with two immersive 3D worlds - **AgroCast** (canvas weather scene: sky, parallax clouds, swaying crop rows, a storm cloud that follows the pointer) and **FarmOptimizer** (CSS-3D isometric farm: canals with flowing water, centre-pivot irrigator, tractor, barn, silo, floating indicators). Both are dependency-free HTML in `assets/scenes/`, shown with `st.components.v1.html`; they respect `prefers-reduced-motion`.
* `ENTER AGROCAST` / `ENTER FARMOPTIMIZER` open that solution's pages. From the sidebar use **All solutions** to return to the landing page or **Switch to ...** to jump to the other solution. Your sidebar inputs are kept.
* AgroCast pages: Field overview, Risk and irrigation, Weather, Report, About. FarmOptimizer pages: Crop planner, Crop comparison, Field overview, Report, About. No page, calculation or API call was changed.
* Styling lives in `assets/styles.css` (dashboards) and `assets/landing.css` (landing); per-solution colours are set in `utils/ui.py` (`THEMES`). The scenes load two Google Fonts and fall back to system fonts when offline. No new Python packages are required.

## Verification status (be honest with judges)
* `python tests/ui_smoke.py` runs every page's Python through a *stand-in* for Streamlit/Plotly (catches crashes, wrong variables, broken button callbacks). It does not prove real rendering - click through the real app once.
* `.streamlit/config.toml` forces a light theme (dark system themes made text unreadable before).
* **Executed & passing in the build environment:** 42 unit tests covering engines, missing-data handling, irrigation, scenarios, optimiser constraints/budget/water/invalid input, SQLite, PDF generation.
* **Compile-checked only, NOT executed there:** Streamlit UI (`app.py`, `views/`), Plotly charts (`utils/charts.py`), live Open-Meteo calls (no network/packages in that environment). Run the app once and fix any UI typo before recording videos.

## Data honesty
* Weather: Open-Meteo when online; otherwise `data/sample_weather.csv` = **synthetic** demo data (labelled in UI/PDF; contains a deliberate hot spell, heavy rain and two gaps to demonstrate alerts/imputation).
* `data/crops.csv`: illustrative planning defaults (FAO-56 Kc, FAO-33 Ky style, approximate price/cost levels). **Verify against ICAR/state agriculture department/CACP before claiming accuracy.** Edit in the UI (Crop Comparison) or CSV; add crops by adding a row.
* Risk scores are transparent heuristics, not validated loss probabilities. No ML model is trained (no suitable labelled data), so no accuracy is claimed. Scenarios are simulations, not forecasts.

## Farm assistant (English / Hindi / Marathi)

The **Farm assistant** page explains numbers the app has already calculated (weather, risks, irrigation, growth stage, plan, budget, optimisation, report).
It works fully offline with fixed rules and never claims a language model is connected unless one is configured.

Optional language-model provider (any OpenAI-compatible endpoint, including a local Ollama server). Set environment variables - never put keys in code:

| Variable | Purpose |
|---|---|
| `AGRINOVA_LLM_MODEL` | model name (required to enable the provider) |
| `AGRINOVA_LLM_API_KEY` | API key (optional for a local server) |
| `AGRINOVA_LLM_BASE_URL` | default `https://api.openai.com/v1`; e.g. `http://localhost:11434/v1` |
| `AGRINOVA_LLM_NAME` | optional display name |

Only after the user ticks the consent box, a redacted summary (no state/district, rounded area/budget/water, no alert text) is sent. Code lives in `assistant/`, separate from `engine/`.

## Final polish (Phase 9)
Consistent chart toolbar/legend and rounded tables (`utils/ui.py`), ARIA roles and labels for alerts and risk rings, a per-page error guard in `app.py`, report-page loading state and input checks, and a mobile/typography/accessibility block at the end of `assets/styles.css`.
