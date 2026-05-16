---
document: "Thesis — Chapter 4 draft only"
merge_note: "Paste this after your Chapter 3 (Research Methodology / Field Work). Chapters 1–3 and 5 stay in your main thesis file. Renumber figures/tables to your college format."
student: "[NAME]"
institution: "[UNIVERSITY]"
date: "May 2026"
---

# CHAPTER 4

## PRESENTATION, ANALYSIS, AND INTERPRETATION OF DATA *(or: Simulation Results and Discussion — use your official chapter title)*

This chapter presents the **UXsim mesoscopic simulation** of bus operations on the **Robinsons–Waltermart** segment of **Emilio Aguinaldo Highway**, **Dasmariñas City, Cavite**. It incorporates **(i)** how field spreadsheet data were processed, **(ii)** how the corridor was represented in the model, **(iii)** the **twelve** scenario runs, **(iv)** quantitative results, and **(v)** interpretation and limitations. Implementation is documented in the project files **`bus_calibration.py`**, **`simulation.py`**, and **`visualize_results.py`**, with primary input **`Data_Collection.xlsx`**.

---

### 4.1 Rationale and scope of the simulation block

Field observation sheets capture **when** and **where** buses were recorded, **who** operated them, **route** text, **passenger movements**, **dwell**, and **traffic descriptors**. Those columns support **documentation and calibration** of a **repeatable** corridor model. The simulation answers a **counterfactual policy question** under controlled assumptions: *If informal curbside stopping on the approach to a modeled signalized junction were removed while retaining a **formal post-intersection stop** and **Waltermart** terminal behavior, how would **system-level** performance indicators change for the same directional trip counts?* A second contrast uses **Waltermart-location** rows to define the **time window** and subset summaries, and applies an additional **dwell-scaling** factor in the optimized variant to represent **shorter** modeled stop times.

---

### 4.2 Study corridor as represented in UXsim

The coded abstraction links **Robinsons Place Dasmariñas** and **Waltermart Dasmariñas** with:

- **Robinsons** and **Waltermart** **terminal bays** (short dedicated links whose traversal time reflects **mean surveyed dwell** at each mall, aggregated at the sheet level);
- a **signalized node** on the corridor;
- a **formal bus stop immediately downstream of the signal**, separated from the signal by **290 m** of cruise (field chainage used in code);
- an **informal curbside segment** on the **Robinsons → Waltermart** direction **only in baseline scenarios**, placed **before** the signal, with dwell proxied from survey statistics;
- a **3.3 km** interior cruise budget between the **Robinsons road node** and the **Waltermart road node**, consistent with the implemented constant `TOTAL_CRUISE_RB_ROAD_TO_WM_ROAD_M` (post-intersection bay links are counted inside that budget as coded).

**Signal control** is modeled as a **90 s** cycle with **45 s** of green for eastbound (toward Waltermart) and **45 s** for westbound. **Mainline cruise** free-flow speed is approximately **60 km/h** (`FREE_FLOW_MPS = 16.67 m/s`). The **Waltermart → Robinsons** direction uses the **post-intersection stop** and **signal** but **does not** include the informal curb chain, matching the narrative that informal loading was specified on the **Robinsons-to-Waltermart** approach.

---

### 4.3 Data source, columns, and processing logic

Primary data are in **`Data_Collection.xlsx`**, sheets **Morning Session**, **Lunch**, and **Afternoon Session**. The processing pipeline reads the following columns (exact headers may vary slightly; the code resolves them flexibly):

| Column | Use in the simulation workflow |
|--------|--------------------------------|
| **Time** | Timestamps for each row; the **demand injection window** for a run equals the span of times in the **calibration subset** (relative to the earliest time in that subset). |
| **Bus (Company Name)** | Frequency summary within the subset (exported to results for traceability). |
| **Route** | Frequency summary within the subset (exported). |
| **Location** | **Stratification key.** Rows whose location text maps to **Robinsons** define the **`robinsons_location`** calibration stream; rows mapped to **Waltermart** define **`waltermart_location`**. |
| **No. of Passenger Boarding / Alighting / Arrival Rate** | Subset **means** computed and written to **`results_summary.csv`**; they **do not** currently drive endogenous crowding or variable dwell inside UXsim. |
| **Dwell Time** | Parsed to seconds; **sheet-level** mean dwells at Robinsons and at Waltermart parameterize **terminal** stop links and inform **proxy dwells** (e.g., informal curb, post-intersection stop). |
| **Traffic Crowding Level / Traffic Condition** | Subset frequency summaries (documentation in results). |

If the raw time span within a subset is **unrealistically long** (e.g., sparse rows across many hours), the active demand window is **capped at five hours** (`MAX_DEMAND_WINDOW_CAP_S`); the cap is flagged in outputs (`demand_window_capped`).

**Directional volumes** for `adddemand` use **whole-sheet counts**: **Robinsons-location row count** → **RB→WM** volume; **Waltermart-location row count** → **WM→RB** volume (with a minimum of one to avoid degenerate runs). **Terminal mean dwells** pool **all** valid dwell observations at each mall **on that sheet** so both terminals remain defined for every scenario.

---

### 4.4 Software and outputs

**UXsim** (Python) provides the simulation `World`, network construction, demand loading, and **post-run analyzer** statistics. **openpyxl** reads Excel; **matplotlib** produces **network-average** maps and supplementary **bar charts**.

Each completed run appends one row to **`results_summary.csv`** (metrics plus `data_origin`, policy tags, informal-curb flag, short-dwell scale when applicable, volumes, subset survey summaries). Paired **baseline versus optimized** summaries are written to **`results_baseline_vs_optimized.csv`** with one row per **session × data_origin** pairing (six rows total). **Figure outputs** include, per scenario, **`figures_output/..._network_average.png`**, and aggregated charts under **`figures_output/analysis/`** (travel time by period for each `data_origin`, percent improvement, Robinsons-subset delay comparison, and an overview of all twelve runs).

---

### 4.5 Experimental design: twelve scenarios

For **each** of the three session sheets, **four** runs are executed:

1. **`robinsons_location` + baseline** — informal curb **on** (RB→WM), post-intersection formal stop, Waltermart; dwell scale **1.0**.  
2. **`robinsons_location` + optimized** — informal curb **off**; dwell scale **1.0**.  
3. **`waltermart_location` + baseline** — same network topology as (1); time window and subset statistics from **Waltermart** rows.  
4. **`waltermart_location` + optimized** — informal curb **off**; modeled dwell seconds multiplied by **0.55** before mapping to link speeds (**short-stop policy proxy**).

Thus **3 × 4 = 12** simulations. **Performance metrics** recorded include **average travel time**, **average delay**, **delay ratio**, **average speed**, and **completed trips**, as reported by the UXsim analyzer.

---

### 4.6 Presentation of results

#### 4.6.1 Paired comparison of average travel time

**Table 4.1** reproduces the paired export **`results_baseline_vs_optimized.csv`**. Values are **simulator-reported mean travel time per completed trip** (seconds) and **percent reduction** when moving from **baseline** to **optimized** within the same **session** and **`data_origin`**.

**Table 4.1.** Baseline versus optimized average travel time (s) and percent improvement.

| Session | data_origin | Baseline (s) | Optimized (s) | Time saved (s) | Improvement (%) |
|---------|-------------|-------------:|--------------:|-----------------:|------------------:|
| Morning Session | robinsons_location | 404.61 | 333.55 | 71.06 | 17.56 |
| Morning Session | waltermart_location | 407.50 | 279.34 | 128.16 | 31.45 |
| Lunch | robinsons_location | 404.58 | 361.88 | 42.70 | 10.55 |
| Lunch | waltermart_location | 404.79 | 292.92 | 111.87 | 27.64 |
| Afternoon Session | robinsons_location | 412.93 | 352.93 | 60.00 | 14.53 |
| Afternoon Session | waltermart_location | 413.05 | 285.12 | 127.93 | 30.97 |

Across **all six** pairings, **optimized** mean travel time is **lower** than **baseline**. Relative improvements are **smallest** for **Lunch / robinsons_location** (**10.55%**) and **largest** for **Morning / waltermart_location** (**31.45%**). The **waltermart_location** stream combines **removal of the informal segment** with **dwell scaling** in optimized runs, which contributes to **larger** percentage changes than most **robinsons_location** pairs.

#### 4.6.2 Delay, speed, and auxiliary outputs

**Average delay** and **delay ratio** vary by run; they are **not** redundant with travel time because the simulator’s delay construct reflects **excess time relative to modeled free-flow movement** and **queueing**, which can **relocate** when the informal segment is removed. **Average speed** generally moves in the direction consistent with shorter mean travel time over the same completed distance. Full numeric detail for every run appears in **`results_summary.csv`**; **Figure 4.x** (your numbering) may reproduce the **`figures_output/analysis/delay_robinsons.png`** and related charts.

#### 4.6.3 Illustrative calibration facts (documentation)

For example, the **Morning Session** sheet contains **138** Robinsons-location rows and **57** Waltermart-location rows in the processed export; **mean dwell** inputs reflect pooled sheet means (e.g., **Robinsons ≈ 46.6 s**, **Waltermart ≈ 35.1 s** for that sheet in the calibration log). **Lunch** Waltermart-location runs use a **capped** demand window (**18,000 s**) because the raw clock span across sparse rows exceeded the modeling cap.

---

### 4.7 Analysis and interpretation

The **directional trip table** is held fixed across paired runs; therefore, differences in **mean travel time** arise from **network treatment of stops** and **dwell parameterization**, not from changed trip generation totals. **Removing the informal curb** on **RB→WM** eliminates a **slow, high-dwell** chain before the signal in optimized runs, which **shortens** modeled trips **in every pairing** in Table 4.1.

**Interpretation of delay.** It is **not** inconsistent for **average delay** to **increase** in some periods while **travel time decreases**: without the informal segment, **arrivals** at the **signal** and **post-intersection formal stop** can become **tighter**, increasing **queue delay** even as **total** trip time falls. Chapter conclusions should discuss **travel time and delay together** rather than treating delay alone as a simple “better/worse” index.

**Strengths of the block.** The workflow is **transparent** (CSV exports, Python scripts), **repeatable**, and anchored to **your spreadsheet columns**, including **Location-aware** calibration streams.

**Limitations.** The model is **not** a geometric digital twin of the intersection; **other modes** are not explicitly simulated; **boarding and crowding** are **documented** but **not** feedback into dwell or capacity; **row counts** are **operational proxies** for directional demand, not a full **O–D matrix** from APC or GPS; **290 m** and **3.3 km** should be **verified** against **independent chainage** (e.g., mapping software) in the final document.

---

### 4.8 Chapter summary

This chapter presented the **data-to-simulation pipeline**, the **UXsim corridor specification**, the **twelve-scenario design**, and **quantitative results**. Under the coded assumptions, **optimized** layouts yielded **lower mean travel time** than **baseline** for **all** session–origin pairings in Table 4.1. **Policy implications** and **recommendations** are reserved for **Chapter 5**, together with a concise restatement of limitations appropriate for closing the thesis.

### 4.9 Completeness: what this chapter contains vs. what you add elsewhere

**Contained in Sections 4.1–4.8:** narrative for the UXsim study block—rationale, corridor and signal specification, Excel processing, software and outputs, twelve-run design, Table 4.1 and discussion, delay vs. travel time, limitations, chapter summary.

**You add in the bound thesis (standard, not a “missing” part of the research):** embedded **Figure** plates from `figures_output/` and `figures_output/analysis/` with captions; your college’s **figure/table numbering**; **Chapter 5** (summary, conclusions, recommendations); **Chapters 1–3** aligned with the code (see `THESIS_CHAPTER1_SNIPPET.txt` and `THESIS_REVISION_GUIDE_AND_CHAPTER3.md`). Optional: **hypothesis tests** or **GPS validation** only if your panel requires them and you have data.

**Formatting note:** In Word, keep §4.2 as a **bulleted list** so the five corridor elements stay separate; keep the **3.3 km** sentence and the code constant name `TOTAL_CRUISE_RB_ROAD_TO_WM_ROAD_M` on **one line** so the constant is not orphaned.

---

## Appendix to Chapter 4 (optional in thesis: move to main Appendix)

| Artifact | Description |
|----------|-------------|
| `results_summary.csv` | One row per simulation run (12 rows). |
| `results_baseline_vs_optimized.csv` | Six paired comparisons. |
| `figures_output/` | UXsim `network_average.png` per run. |
| `figures_output/analysis/` | Bar charts from `visualize_results.py`. |

**Reproducibility.** From the project folder: `python simulation.py` (runs simulations and attempts chart generation); `python visualize_results.py` regenerates analysis charts from existing CSVs.

---

*End of Chapter 4 draft. (Repository: see RUN_GUIDE.txt for file map.)*
