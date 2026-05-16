# Thesis alignment: your draft vs. the implemented UXsim work

**Audience:** Cabanlig, Fernandez, Nafora, Orzame, Ting — *Data-Driven Transit Solutions…* (match title page date to defense; **Chapter 4** = simulation results; **Chapter 3** = methods that match the code.)

**Index — use these files together**

| File | Use for |
|------|---------|
| `RUN_GUIDE.txt` | How to run; outputs; tunable constants; thesis checklist |
| `THESIS_CHAPTER1_SNIPPET.txt` | Paste-ready **objectives + scope** aligned with UXsim |
| `THESIS_REVISION_GUIDE_AND_CHAPTER3.md` | **This file**: truth table + **replacement Chapter 3** (Part C) |
| `THESIS_DRAFT.md` | **Chapter 4** draft (results + interpretation) |

---

## Part A — What the project **actually** implements (single source of truth)

| Topic | Implemented in code? | Where |
|--------|----------------------|--------|
| **UXsim** mesoscopic corridor simulation in Python | Yes | `simulation.py` |
| **Excel** `Data_Collection.xlsx` (Morning / Lunch / Afternoon) | Yes | `bus_calibration.py` |
| Columns: Time, Bus, Route, Location, boarding, alighting, arrival rate, dwell, crowding, traffic | Read & summarized | `bus_calibration.py` |
| **Location** = Robinsons vs Waltermart splits **calibration streams** | Yes | `data_origin` |
| **12 runs** = 3 sheets × (Robinsons baseline, Robinsons optimized, Waltermart baseline, Waltermart optimized) | Yes | `simulation.py` `main()` |
| Network: Robinsons bay, **informal curb RB→WM before signal (baseline only)**, signal (90 s, 45/45), **formal post-intersection stop (290 m)**, Waltermart bay; WM→RB without informal | Yes | `simulation.py` `build_network` |
| **3.3 km** interior cruise (RB road–WM road) per coded constants | Yes | `TOTAL_CRUISE_RB_ROAD_TO_WM_ROAD_M` |
| Volumes: RB→WM = count of **Robinsons-location** rows; WM→RB = **Waltermart-location** rows (per sheet) | Yes | `bus_calibration.py` |
| Dwell → stop link speeds (not microscopic boarding queues) | Yes | `build_network` |
| Waltermart-stream **optimized** = shorter dwell (**0.55** scale) | Yes | `OPTIMIZED_SHORT_DWELL_SCALE` |
| Outputs: `results_summary.csv`, `results_baseline_vs_optimized.csv`, PNG maps, `figures_output/analysis/` charts | Yes | `simulation.py`, `visualize_results.py` |
| **70/15/15** train/val/test, **ML** models, **one-hot encoding** for UXsim inputs | **No** | Remove or move to “future work” |
| **MAE / RMSE / ETA / ECDF** for predictions | **No** | Remove unless you run a **separate** ML chapter |
| **NHPP**, **agent-based** passenger agents inside UXsim | **No** | Remove or rephrase as *planned* vs *delivered* |
| **Headway-based dispatch** in the simulator | **No** | Demand is **volume over a window**, not headway control |
| **Multiple random seeds** per scenario | **Not** in current `main()` | Remove or add as future robustness test |
| **Passenger waiting time** as a UXsim output | **No** | Use **travel time / delay / speed / completed trips**; waiting time only if you **compute** from field video separately |
| **Model validation** vs field with **% error** on travel time | **Not** automated in repo | Say “descriptive comparison” or add one validation subsection if you collect GPS |

---

## Part B — Quick edits to your **Chapter 1** (optional but important)

- **Objectives** currently say “Apply optimization strategies to **scheduling**” and “**commuter waiting times**, **overcrowding**.” The built system compares **stop-use / dwell** scenarios on a **fixed OD table**, not dispatch scheduling or waiting-time simulation. **Rewrite objectives** to: mesoscopic corridor model; baseline vs optimized stop policy; corridor KPIs (travel time, delay, speed); policy recommendations *conditional on model assumptions*.
- **Scope** mentions “**arrival prediction accuracy**,” “**KPI** meeting,” “real-time tracking approximated” — either **remove** or tie each phrase to a **concrete output you actually produce** (e.g., CSV + charts only).

---

## Part C — **REPLACEMENT CHAPTER 3** (Methodology) — paste under your “Chapter 3 Methodology” heading

*Retain your institutional headings (Research Design, Data, etc.) if required; sub-numbering can follow your template.*

### Chapter 3  
### METHODOLOGY  

#### 3.1 Research Design  

This study employs a **quasi-experimental, scenario-based research design** implemented through **repeatable computer simulation**. The object of inquiry is **corridor-level bus trip performance** on the **Robinsons Pala-Pala–Waltermart Dasmariñas** segment of **Emilio Aguinaldo Highway**, Cavite. **Independent variables** are **policy-coded network treatments** (presence or absence of an **informal curbside stop** on the Robinsons-to-Waltermart approach before a modeled signalized junction; optional **dwell scaling** in one optimized variant) while holding **directional trip counts** and **session-specific demand windows** tied to field spreadsheets. **Dependent variables** are **simulator-reported system metrics**: principally **average travel time per completed trip**, **average delay**, **delay ratio**, **average speed**, and **completed trips**, augmented by **link-level** summaries and **network maps** exported from UXsim.  

The design does **not** constitute a machine-learning train–validation–test pipeline for the UXsim stage; **no** neural ETA model is trained inside the simulation repository described here. Any **predictive analytics** or **passenger waiting-time models** belong in a **separate** methodology subsection only if the group delivers them with comparable documentation.  

#### 3.2 Study setting and corridor abstraction  

The empirical anchor is the **Robinsons–Waltermart** bus corridor in **Dasmariñas City**, consistent with the locale described in Chapter 1. The **simulation abstraction** is a **directed node–link network** with: (1) a **Robinsons terminal** represented by short bay links; (2) on **Robinsons → Waltermart**, an optional **informal curb** segment **before** a **signal node** in baseline scenarios; (3) a **formal bus stop immediately after the intersection**, separated from the signal by **290 m** of cruise distance per field chainage; (4) a **Waltermart terminal**; and (5) **Waltermart → Robinsons** movement using the **post-intersection stop** and **signal** without the informal segment. The **interior cruise distance** between the Robinsons-side and Waltermart-side **road nodes** is set to **3.3 km** in code, with bay and post-intersection links additional to that budget as implemented. **Free-flow cruise speed** is approximately **60 km/h**. The **signal cycle** is **90 s** with **45 s** green per approach in the coded scenario.  

#### 3.3 Data sources and instruments  

**Primary structured observations** are recorded in **Microsoft Excel** (`Data_Collection.xlsx`) on sheets **Morning Session**, **Lunch**, and **Afternoon Session**. Each row includes **Time**; **Bus (Company Name)**; **Route**; **Location** (whether the enumerator recorded the event starting from **Robinsons** or **Waltermart**); **No. of Passenger Boarding**; **No. of Passenger Alighting**; **No. of Passenger Arrival Rate**; **Dwell Time**; **Traffic Crowding Level**; and **Traffic Condition**.  

**Secondary context** (e.g., CTTMO fleet lists, route lists, letters of permission) supports thesis ethics and scope narrative in Chapters 1–2 but is **not** re-imported as a separate database inside the UXsim scripts unless explicitly added.  

#### 3.4 Data processing pipeline  

A Python module **`bus_calibration.py`** reads each sheet, normalizes **Location** into **Robinsons** versus **Waltermart**, and builds **two calibration streams per sheet**:  

- **`robinsons_location`:** all rows whose location resolves to Robinsons; **time span** of this subset defines the **demand injection window** (relative to the earliest observation time in the subset). **Subset means** for boarding, alighting, and arrival rate, and **frequency summaries** for crowding, traffic, operator, and route, are computed for **documentation** in results tables.  
- **`waltermart_location`:** analogous processing for Waltermart rows.  

**Directional volumes** for UXsim `adddemand` are the **sheet-wide** counts: **Robinsons-location rows** → **Robinsons-to-Waltermart** volume; **Waltermart-location rows** → **Waltermart-to-Robinsons** volume (minimum one per direction to avoid degeneracy). **Mean dwell times** at Robinsons and at Waltermart are computed from **all valid dwell samples on that sheet** (by location), so terminal parameters exist for **every** run. **Dwell times** in cells are parsed from mixed string formats (e.g., minutes and seconds) into seconds. If a subset’s raw clock span is **implausibly long**, the active demand window is **capped** (five hours in code) and flagged.  

Boarding, alighting, crowding, and traffic fields are **stored in `results_summary.csv`** for traceability; they **do not** currently feed back into **endogenous crowding** or **variable dwell** inside UXsim.  

#### 3.5 Simulation method, platform, and procedure  

**Platform.** **UXsim** (Python) provides the `World`, node/link construction, **time-varying origin–destination demand**, signal groups, and **post-run analyzer** statistics. **openpyxl** reads Excel. **matplotlib** renders **network-average** diagrams and supplementary bar charts.  

**Procedure.** For each session sheet, **four** worlds are executed in sequence:  

1. Robinsons-location calibration — **baseline** (`informal` curb on RB→WM).  
2. Robinsons-location calibration — **optimized** (informal removed; dwell scale 1.0).  
3. Waltermart-location calibration — **baseline** (same topology; window and subset stats from Waltermart rows).  
4. Waltermart-location calibration — **optimized** (informal removed; **dwell scale 0.55** on modeled stop dwells).  

Each run writes one row to **`results_summary.csv`**. **Paired** baseline–optimized comparisons by **session** and **`data_origin`** are written to **`results_baseline_vs_optimized.csv`** (six rows). **`visualize_results.py`** (invoked after the batch when dependencies succeed) reads those CSVs and saves charts under **`figures_output/analysis/`**.  

**Reproducibility.** From the project directory: `python simulation.py`.  

#### 3.6 Evaluation metrics (aligned with actual outputs)  

**Primary:** **Average travel time** (s) per completed trip; **paired percent reduction** baseline → optimized from **`results_baseline_vs_optimized.csv`**.  

**Secondary:** **Average delay** (s), **delay ratio**, **average speed** (m/s), **completed trips**, **total distance traveled**; **link-average travel times** from UXsim’s coarse link analysis; **network-average PNG** for visual corridor diagnosis.  

**Not reported by this pipeline unless added elsewhere:** MAE/RMSE of ETA, ECDF of prediction error, on-board **crowding** time series, or **stop-level waiting time** distributions from UXsim.  

#### 3.7 Validity, reliability, and limitations (honest framing)  

**Internal validity (model logic):** Network topology, signal parameters, volumes, and dwell mapping are **deterministic given inputs**; scripts are version-controlled.  

**External validity (real world):** The model is a **schematic corridor**, not a **lane-resolved digital twin**; **other modes** (jeepney, tricycle, etc.) are excluded; **intersection geometry** is abstracted. **Calibration** uses **observation counts as OD proxies**, not a full **RTC** origin–destination matrix. **Claims about commuter waiting** or **ETA accuracy** require **separate** field or ML analysis—not the current UXsim export set.  

**Reliability:** Re-running `simulation.py` on the same Excel file and code revision yields the **same** numerical outputs (stochastic seeding is not part of the documented `main()` loop). **Sensitivity analysis** (e.g., varying dwell scale or chainage) can be reported as future work.  

#### 3.8 Ethical considerations  

Observations should avoid **personally identifiable** commuter data; operator names appear as in public branding. Data handling follows **Data Privacy Act of 2012** principles (minimization, purpose limitation). **Mayor’s letter / CTTMO permission** remains in the thesis appendices as evidence of authorization.  

---

## Part D — What to put in **Chapter 4** (pointer)

Use your existing **`THESIS_DRAFT.md`** in this folder as the **Chapter 4** draft: **presentation of CSV tables**, **figures** (`figures_output/`, `figures_output/analysis/`), and **interpretation** (including **delay vs. travel time**). **Chapter 5** summarizes findings, conclusions, recommendations, and limitations—**without** reintroducing MAE/ETA numbers unless you compute them in another study component.

---

## Part E — Title page consistency checklist

- **Date:** “May 2025” vs actual defense — fix.  
- **Degree line:** matches registrar wording.  
- **“Chapter ”** at the end of your paste — complete with **Chapter 4** (and 5) from your outline.

---

*End of alignment guide.*
