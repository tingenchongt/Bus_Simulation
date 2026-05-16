"""
Build the 3049 m Robinsons–Waltermart corridor in UXsim (chainage-aligned stops + bypass for non-bus traffic).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from corridor_config import (
    CORRIDOR_LENGTH_M,
    DEFAULT_DWELL_S,
    FREE_FLOW_MPS,
    LANES_MAIN,
    SIGNAL_CHAINAGE_M,
    SIGNAL_GREEN_EB_S,
    SIGNAL_GREEN_WB_S,
    STOP_LANES,
    STOP_LINK_LENGTH_M,
    STOPS_RB_TO_WM,
    StopKind,
)

if TYPE_CHECKING:
    from uxsim import World

    from bus_calibration import SessionCalibration


def _apply_dwell_scale(seconds: float, scale: float) -> float:
    if scale >= 1.0:
        return seconds
    return max(8.0, seconds * scale)


def _dwell_seconds(kind: StopKind, cal: SessionCalibration, short_dwell_scale: float) -> float:
    base_rb = float(cal.mean_dwell_rb_s or DEFAULT_DWELL_S)
    base_wm = float(cal.mean_dwell_wm_s or DEFAULT_DWELL_S)
    if kind == "terminal_formal":
        return _apply_dwell_scale((base_rb + base_wm) / 2.0, short_dwell_scale)
    if kind == "formal":
        return _apply_dwell_scale(max(base_wm, base_rb) * 0.85, short_dwell_scale)
    if kind == "informal":
        return _apply_dwell_scale(max(base_rb * 1.12, 45.0), short_dwell_scale)
    return DEFAULT_DWELL_S


def _speed_from_dwell(dwell_s: float) -> float:
    return max(STOP_LINK_LENGTH_M / max(dwell_s, 5.0), 0.12)


def _cruise_len(chain_a: float, chain_b: float) -> float:
    return max(chain_b - chain_a - 2.0 * STOP_LINK_LENGTH_M, 50.0)


def build_corridor_network(
    W: World,
    cal: SessionCalibration,
    *,
    include_informal_stops: bool,
    short_dwell_scale: float = 1.0,
    signal_offset_s: float = 0.0,
) -> dict[str, object]:
    """Returns rb_bus_stop, wm_bus_stop, rb_road, wm_road for demand injection."""
    u = FREE_FLOW_MPS
    road_nodes: list[object] = []
    chainages: list[float] = []

    def add_road(name: str, x: float) -> object:
        n = W.addNode(name, x, 0.0)
        road_nodes.append(n)
        return n

    def link_cruise(name: str, a: object, b: object, length: float, group: int) -> None:
        W.addLink(name, a, b, length, u, number_of_lanes=LANES_MAIN, signal_group=[group])
        W.addLink(f"{name}_rev", b, a, length, u, number_of_lanes=LANES_MAIN, signal_group=[1 - group])

    # Terminals
    rb_stop = W.addNode("Robinsons_BusStop", 0.0, 0.0)
    rb_road = add_road("Robinsons_Road", STOP_LINK_LENGTH_M)
    dwell_rb = _dwell_seconds("terminal_formal", cal, short_dwell_scale)
    u_rb = _speed_from_dwell(dwell_rb)
    W.addLink("RB_Stop_in", rb_road, rb_stop, STOP_LINK_LENGTH_M, u_rb, number_of_lanes=STOP_LANES)
    W.addLink("RB_Stop_out", rb_stop, rb_road, STOP_LINK_LENGTH_M, u_rb, number_of_lanes=STOP_LANES)
    chainages.append(0.0)

    prev = rb_road
    prev_chain = 0.0
    stop_nodes: dict[str, object] = {}

    # Eastbound chain RB → WM (skip terminal rows; signal and WM handled separately)
    eb_stops = [s for s in STOPS_RB_TO_WM if s.key not in ("robinsons", "waltermart", "signal")]
    for stop in eb_stops:
        cruise = _cruise_len(prev_chain, stop.chainage_m)
        if stop.kind == "informal" and not include_informal_stops:
            next_road = W.addNode(f"Road_{stop.key}", prev.x + cruise, 0.0)
            link_cruise(f"skip_{stop.key}", prev, next_road, cruise, 0)
            prev = next_road
            prev_chain = stop.chainage_m
            continue
        entry = W.addNode(f"{stop.key}_Entry", prev.x + cruise, 0.0)
        stop_n = W.addNode(f"{stop.key}_Stop", entry.x + STOP_LINK_LENGTH_M, 0.0)
        exit_n = W.addNode(f"{stop.key}_Exit", stop_n.x + STOP_LINK_LENGTH_M, 0.0)
        dwell = _dwell_seconds(stop.kind, cal, short_dwell_scale)
        us = _speed_from_dwell(dwell)
        W.addLink(f"{stop.key}_bay_in", entry, stop_n, STOP_LINK_LENGTH_M, us, number_of_lanes=STOP_LANES)
        W.addLink(f"{stop.key}_bay_out", stop_n, exit_n, STOP_LINK_LENGTH_M, us, number_of_lanes=STOP_LANES)
        link_cruise(f"to_{stop.key}", prev, entry, cruise, 0)
        W.addLink(f"bypass_{stop.key}", prev, exit_n, cruise + 2.0 * STOP_LINK_LENGTH_M, u, number_of_lanes=LANES_MAIN, signal_group=[0])
        W.addLink(f"bypass_{stop.key}_rev", exit_n, prev, cruise + 2.0 * STOP_LINK_LENGTH_M, u, number_of_lanes=LANES_MAIN, signal_group=[1])
        stop_nodes[stop.key] = stop_n
        prev = exit_n
        prev_chain = stop.chainage_m
        chainages.append(stop.chainage_m)

    # Signal
    cruise_sig = _cruise_len(prev_chain, SIGNAL_CHAINAGE_M)
    signal = W.addNode(
        "Aguinaldo_Signal",
        prev.x + cruise_sig,
        0.0,
        signal=[SIGNAL_GREEN_EB_S, SIGNAL_GREEN_WB_S],
        signal_offset=signal_offset_s,
    )
    link_cruise("to_signal", prev, signal, cruise_sig, 0)
    prev = signal
    prev_chain = SIGNAL_CHAINAGE_M

    # Waltermart
    cruise_wm = _cruise_len(prev_chain, CORRIDOR_LENGTH_M)
    wm_road = add_road("Waltermart_Road", prev.x + cruise_wm)
    link_cruise("to_wm_road", prev, wm_road, cruise_wm, 0)
    wm_stop = W.addNode("Waltermart_BusStop", wm_road.x + STOP_LINK_LENGTH_M, 0.0)
    dwell_wm = _dwell_seconds("terminal_formal", cal, short_dwell_scale)
    u_wm = _speed_from_dwell(dwell_wm)
    W.addLink("WM_Stop_in", wm_road, wm_stop, STOP_LINK_LENGTH_M, u_wm, number_of_lanes=STOP_LANES)
    W.addLink("WM_Stop_out", wm_stop, wm_road, STOP_LINK_LENGTH_M, u_wm, number_of_lanes=STOP_LANES)

    policy = "baseline (formal + informal)" if include_informal_stops else "optimized (formal + Vista only; informal removed)"
    print(f"  Extended corridor: {policy}")
    print(f"  Length {CORRIDOR_LENGTH_M:.0f} m | signal @ {SIGNAL_CHAINAGE_M:.0f} m | offset {signal_offset_s:.0f} s")

    return {
        "rb_bus_stop": rb_stop,
        "wm_bus_stop": wm_stop,
        "rb_road": rb_road,
        "wm_road": wm_road,
        "signal": signal,
    }
