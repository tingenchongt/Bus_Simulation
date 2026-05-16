"""
Extended UXsim study: 3049 m corridor, formal/informal stops, mixed traffic, signal scenarios.

Default full matrix (with --all-signals):
  3 sessions × 4 calibration runs × 4 signal encounter scenarios = 48 UXsim worlds
  (each world loads bus + private car + jeepney + truck + motorcycle + van demand)

Legacy 12-run study remains in simulation.py.

Examples:
  python simulation_extended.py --quick          # 1 session, 1 signal scenario, 4 policies
  python simulation_extended.py                  # 48 runs (may take hours)
  python simulation_extended.py --no-mixed       # buses only
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
from pathlib import Path

from uxsim import World

from bus_calibration import (
    SESSION_SHEETS,
    DataOrigin,
    SessionCalibration,
    load_session_stats,
    print_calibration,
)
from corridor_config import (
    OPTIMIZED_SHORT_DWELL_SCALE,
    POLICY_BASELINE,
    POLICY_OPTIMIZED,
    SIGNAL_ENCOUNTER_SCENARIOS,
    VEHICLE_CLASSES,
    SignalEncounterScenario,
)
from corridor_network import build_corridor_network

_PROJECT_DIR = Path(__file__).resolve().parent
FIGURES_OUTPUT_DIR = _PROJECT_DIR / "figures_output"
RESULTS_SUMMARY_CSV = _PROJECT_DIR / "results_summary_extended.csv"
RESULTS_COMPARISON_CSV = _PROJECT_DIR / "results_baseline_vs_optimized_extended.csv"


def _collect_metrics_row(
    W: World,
    cal: SessionCalibration,
    sheet_name: str,
    policy_tag: str,
    *,
    include_informal: bool,
    short_dwell_scale: float,
    sig: SignalEncounterScenario,
    mixed_traffic: bool,
) -> dict[str, object]:
    a = W.analyzer
    att = float(getattr(a, "average_travel_time", -1.0))
    adel = float(getattr(a, "average_delay", -1.0))
    dr = (adel / att) if att > 0 and adel >= 0 else None
    tc = int(getattr(a, "trip_completed", 0))
    ta = int(getattr(a, "trip_all", 0))
    dist = float(getattr(a, "total_distance_traveled", -1.0))
    ttot = float(getattr(a, "total_travel_time", -1.0))
    vavg = (dist / ttot) if ttot > 0 and dist >= 0 else None
    return {
        "session": sheet_name,
        "data_origin": cal.data_origin,
        "policy": policy_tag,
        "informal_stops": include_informal,
        "short_dwell_scale": short_dwell_scale if short_dwell_scale < 1.0 else "",
        "signal_scenario": sig.scenario_id,
        "first_signal_green_eb": sig.first_signal_green_eb,
        "second_signal_green_wb": sig.second_signal_green_wb,
        "signal_offset_s": sig.signal_offset_s,
        "wm_to_rb_demand_shift_s": sig.wm_to_rb_demand_shift_s,
        "mixed_traffic": mixed_traffic,
        "vol_rb_to_wm": cal.vol_rb_to_wm,
        "vol_wm_to_rb": cal.vol_wm_to_rb,
        "n_rows_calibration_subset": cal.n_rows_calibration_subset,
        "demand_window_s": round(cal.demand_t1_s - cal.demand_t0_s, 1),
        "demand_window_capped": cal.demand_window_capped,
        "avg_travel_time_s": round(att, 2) if att >= 0 else "",
        "avg_delay_s": round(adel, 2) if adel >= 0 else "",
        "delay_ratio": round(dr, 4) if dr is not None else "",
        "completed_trips": tc,
        "total_trips": ta,
        "total_distance_m": round(dist, 1) if dist >= 0 else "",
        "avg_speed_mps": round(vavg, 3) if vavg is not None else "",
    }


def _write_results_csv(rows: list[dict[str, object]], path: Path) -> None:
    if not rows:
        return
    keys = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(f"\n  Results: {path}")


def _write_comparison_csv(rows: list[dict[str, object]], path: Path) -> None:
    by: dict[tuple[str, str, str], dict[str, dict]] = {}
    for r in rows:
        key = (str(r["session"]), str(r.get("data_origin", "")), str(r.get("signal_scenario", "")))
        pol = str(r["policy"])
        by.setdefault(key, {})[pol] = r
    out = []
    for (sess, origin, sig_id), pols in by.items():
        b = pols.get(POLICY_BASELINE)
        o = pols.get(POLICY_OPTIMIZED)
        if not b or not o:
            continue
        try:
            tt_bf = float(b["avg_travel_time_s"])
            tt_of = float(o["avg_travel_time_s"])
        except (TypeError, ValueError):
            continue
        save = tt_bf - tt_of
        pct = (save / tt_bf * 100.0) if tt_bf else None
        out.append(
            {
                "session": sess,
                "data_origin": origin,
                "signal_scenario": sig_id,
                "baseline_avg_travel_time_s": tt_bf,
                "optimized_avg_travel_time_s": tt_of,
                "time_saved_per_trip_s": round(save, 2),
                "pct_improvement_travel_time": round(pct, 2) if pct is not None else "",
            }
        )
    if not out:
        return
    keys = list(out[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(out)
    print(f"  Paired comparison: {path}")


def _add_demands(
    W: World,
    nodes: dict[str, object],
    cal: SessionCalibration,
    *,
    mixed_traffic: bool,
    sig: SignalEncounterScenario,
) -> None:
    rb_bus = nodes["rb_bus_stop"]
    wm_bus = nodes["wm_bus_stop"]
    rb_road = nodes["rb_road"]
    wm_road = nodes["wm_road"]
    t0 = cal.demand_t0_s
    t1 = cal.demand_t1_s
    t0_wm = t0 + sig.wm_to_rb_demand_shift_s

    classes = [VEHICLE_CLASSES[0]] if not mixed_traffic else VEHICLE_CLASSES
    for vc in classes:
        vol_rb = max(1, int(round(cal.vol_rb_to_wm * vc.volume_multiplier)))
        vol_wm = max(1, int(round(cal.vol_wm_to_rb * vc.volume_multiplier)))
        if vc.uses_bus_stops:
            W.adddemand(rb_bus, wm_bus, t0, t1, volume=float(vol_rb))
            W.adddemand(wm_bus, rb_bus, t0_wm, t1 + sig.wm_to_rb_demand_shift_s, volume=float(vol_wm))
        else:
            W.adddemand(rb_road, wm_road, t0, t1, volume=float(vol_rb))
            W.adddemand(wm_road, rb_road, t0_wm, t1 + sig.wm_to_rb_demand_shift_s, volume=float(vol_wm))


def run_one(
    sheet_name: str,
    *,
    data_origin: DataOrigin,
    include_informal: bool,
    policy_tag: str,
    short_dwell_scale: float,
    sig: SignalEncounterScenario,
    mixed_traffic: bool,
    results_rows: list[dict[str, object]] | None,
) -> World:
    cal = load_session_stats(sheet_name, data_origin=data_origin)
    print(f"\n{'='*60}")
    print(f"  {sheet_name} | {cal.data_origin} | {policy_tag} | {sig.scenario_id} | mixed={mixed_traffic}")
    print(f"{'='*60}")
    print_calibration(cal)

    safe = f"{sheet_name.replace(' ', '_')}_{cal.data_origin}_{policy_tag}_{sig.scenario_id}"
    if not mixed_traffic:
        safe += "_bus_only"

    W = World(name=safe, print_mode=1, tmax=cal.sim_tmax_s + sig.wm_to_rb_demand_shift_s, save_mode=1, show_mode=0)
    nodes = build_corridor_network(
        W,
        cal,
        include_informal_stops=include_informal,
        short_dwell_scale=short_dwell_scale,
        signal_offset_s=sig.signal_offset_s,
    )
    _add_demands(W, nodes, cal, mixed_traffic=mixed_traffic, sig=sig)
    W.exec_simulation()
    W.analyzer.print_simple_stats(force_print=True)

    if results_rows is not None:
        results_rows.append(
            _collect_metrics_row(
                W,
                cal,
                sheet_name,
                policy_tag,
                include_informal=include_informal,
                short_dwell_scale=short_dwell_scale,
                sig=sig,
                mixed_traffic=mixed_traffic,
            )
        )

    FIGURES_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        W.analyzer.network_average(left_handed=0, figsize=(12, 4), network_font_size=7)
        png = _PROJECT_DIR / f"out{safe}" / "network_average.png"
        if png.is_file():
            shutil.copy2(png, FIGURES_OUTPUT_DIR / f"{safe}_network_average.png")
    except Exception as exc:
        print(f"  Figure skipped: {exc}")

    return W


def _run_plan(quick: bool, all_signals: bool, sessions: list[str]) -> list[tuple]:
    sigs = list(SIGNAL_ENCOUNTER_SCENARIOS) if all_signals else [SIGNAL_ENCOUNTER_SCENARIOS[0]]
    plan: list[tuple] = []
    for sh in sessions:
        for origin, informal, dwell_scale, pol in [
            ("robinsons", True, 1.0, POLICY_BASELINE),
            ("robinsons", False, 1.0, POLICY_OPTIMIZED),
            ("waltermart", True, 1.0, POLICY_BASELINE),
            ("waltermart", False, OPTIMIZED_SHORT_DWELL_SCALE, POLICY_OPTIMIZED),
        ]:
            for sig in sigs:
                plan.append((sh, origin, informal, dwell_scale, pol, sig))
    return plan


def main() -> None:
    os.chdir(_PROJECT_DIR)
    p = argparse.ArgumentParser(description="Extended corridor UXsim (3049 m, mixed traffic, signal scenarios)")
    p.add_argument("--quick", action="store_true", help="Morning Session only, first signal scenario")
    p.add_argument("--all-signals", action="store_true", help="All 4 first/second signal encounter labels")
    p.add_argument("--no-mixed", action="store_true", help="Bus demand only (no cars/jeeps/etc.)")
    args = p.parse_args()

    sessions = [SESSION_SHEETS[0]] if args.quick else list(SESSION_SHEETS)
    all_signals = args.all_signals or not args.quick
    if args.quick:
        all_signals = False

    plan = _run_plan(args.quick, all_signals, sessions)
    n = len(plan)
    mixed = not args.no_mixed
    print(f"Planned runs: {n} (mixed_traffic={mixed})")

    rows: list[dict[str, object]] = []
    for sh, origin, informal, dwell_scale, pol, sig in plan:
        run_one(
            sh,
            data_origin=origin,  # type: ignore[arg-type]
            include_informal=informal,
            policy_tag=pol,
            short_dwell_scale=dwell_scale,
            sig=sig,
            mixed_traffic=mixed,
            results_rows=rows,
        )

    _write_results_csv(rows, RESULTS_SUMMARY_CSV)
    _write_comparison_csv(rows, RESULTS_COMPARISON_CSV)
    print(f"\nDone. {len(rows)} runs written. Figures under {FIGURES_OUTPUT_DIR}")


if __name__ == "__main__":
    main()
