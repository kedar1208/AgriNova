# Video 1 — AGROCAST: "Predict the risk" (target 4:30)

**Look of this solution:** sky-teal banner with a sun-and-rain icon (it appears when you open the AgroCast page).
Shot with the teal banner on screen as much as possible so viewers see it is a different solution from Video 2.

## Set-up before recording (5 minutes)
1. `streamlit run app.py`, browser at 110% zoom, 1920×1080, hide bookmarks bar.
2. Sidebar: **Maharashtra → Pune**, crop **Wheat**, sowing date **60 days ago**, soil **Loam**, irrigation **Drip**, water **3000 m³**, budget **₹1,00,000**.
3. Open **Advanced** in the sidebar and tick **Offline demo mode** (guaranteed hot spell + heavy rain, so the demo is dramatic and repeatable). Do one take with it off if you have internet, to show the "Live weather · Open-Meteo" pill.
4. Start on **Dashboard**. Rehearse once; screen-record with any recorder and voice over live or afterwards.

## Script

| Time | On screen (what to click) | Narration |
|---|---|---|
| 0:00 | Dashboard, hero card in view | "Weather no longer follows the farming calendar, and a small farmer pays for every wrong guess. Agri-Shield AI answers with two separate solutions. This video is Solution 1: **AgroCast** — what will this week's weather do to the crop already in my field?" |
| 0:25 | Slowly point at hero: crop, growth-stage bar, risk ring | "A farmer tells us the district, crop, sowing date, soil and irrigation. We work out the growth stage — this wheat is on day 60, flowering — and give one overall risk score out of 100, with the biggest threat named in plain words." |
| 0:55 | Click the **District** dropdown, then change **State** to Karnataka | "Location is a pick-list of real districts for each state, so a typo can never become a fake place. Weather is fetched for that exact district, and the pill says whether it is live or sample data." Switch back to Maharashtra / Pune. |
| 1:20 | Scroll the 7-day strip and the four cards | "Next seven days at a glance: hot days are tinted, heavy-rain days are blue. The cards show today's weather, the week's rain, the irrigation decision and the lowest soil-water level." |
| 1:50 | Click **AgroCast** in the sidebar (teal banner appears) | "Now the AgroCast engine. Notice the sky-teal theme — each solution has its own identity." |
| 2:05 | **Risks** tab → open *Heat stress* and *Drought* expanders | "Six hazards: heat, cold, drought, excess rain, waterlogging and fungal-favourable weather. Each score is stage sensitivity times weighted weather features. Heat stress here: read out how many forecast days are above wheat's 32 °C limit, as shown in the card. Each card says what is predicted, why it matters, which factors added how many points, and what to do. It is a transparent rule-based model, so we claim no accuracy figure." |
| 3:00 | **Irrigation** tab | "A FAO-56 soil-water bucket projects root-zone water day by day. It is labelled ESTIMATED because nobody measured it." Then in the sidebar open **Advanced**, tick **I measured soil moisture**, set 35%. "Now it says MEASURED and the advice updates — read out the new date, depth in millimetres and volume in cubic metres shown on screen. If big rain is coming within 48 hours it says postpone instead." |
| 3:45 | Back to **Dashboard** → Alerts and Risk breakdown | "Alerts are generated only from the data, in plain language." |
| 4:05 | **Report** → click **Download PDF report** | "Everything goes into a PDF the farmer can take to the agriculture office." |
| 4:20 | Back to AgroCast banner | "AgroCast: crop- and stage-specific, explainable early warning that is honest about its data. Next, FarmOptimizer plans the whole season." |

## Extra shots (use if time allows)
- Change sowing date to **5 days ago**: scores shift because young wheat is less sensitive to heat.
- Change sowing date to **5 days ahead**: headline says "Sowing in 5 days" and no irrigation is advised.
