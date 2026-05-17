"""
Build the 3049 m Robinsons–Waltermart corridor in UXsim (stops + three 180 s signals).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from corridor_config import (
    CORRIDOR_LENGTH_M,
    CORRIDOR_SIGNALS,
    DEFAULT_DWELL_S,
    FREE_FLOW_MPS,
    LANES_MAIN,
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
    """Returns rb_bus_stop, wm_bus_stop, rb_road, wm_road, and signal nodes keyed by name."""
    u = FREE_FLOW_MPS
    signal_nodes: dict[str, object] = {}

    def link_cruise(name: str, a: object, b: object, length: float, group: int) -> None:
        W.addLink(name, a, b, length, u, number_of_lanes=LANES_MAIN, signal_group=[group])
        W.addLink(f"{name}_rev", b, a, length, u, number_of_lanes=LANES_MAIN, signal_group=[1 - group])

    rb_stop = W.addNode("Robinsons_BusStop", 0.0, 0.0)
    rb_road = W.addNode("Robinsons_Road", STOP_LINK_LENGTH_M, 0.0)
    dwell_rb = _dwell_seconds("terminal_formal", cal, short_dwell_scale)
    u_rb = _speed_from_dwell(dwell_rb)
    W.addLink("RB_Stop_in", rb_road, rb_stop, STOP_LINK_LENGTH_M, u_rb, number_of_lanes=STOP_LANES)
    W.addLink("RB_Stop_out", rb_stop, rb_road, STOP_LINK_LENGTH_M, u_rb, number_of_lanes=STOP_LANES)

    prev = rb_road
    prev_chain = 0.0

    eb_stops = [s for s in STOPS_RB_TO_WM if s.key not in ("robinsons", "waltermart")]
    stop_by_chain = {s.chainage_m: s for s in eb_stops}
    sig_by_chain = {s.chainage_m: s for s in CORRIDOR_SIGNALS}
    milestones = sorted(set(stop_by_chain) | set(sig_by_chain))

    for chain in milestones:
        cruise = _cruise_len(prev_chain, chain)
        if chain in sig_by_chain:
            sig = sig_by_chain[chain]
            node = W.addNode(
                sig.key,
                prev.x + cruise,
                0.0,
                signal=[sig.green_eb_s, sig.green_wb_s],
                signal_offset=signal_offset_s,
            )
            link_cruise(f"to_{sig.key}", prev, node, cruise, 0)
            signal_nodes[sig.key] = node
            prev = node
        else:
            stop = stop_by_chain[chain]
            if stop.kind == "informal" and not include_informal_stops:
                next_road = W.addNode(f"Road_{stop.key}", prev.x + cruise, 0.0)
                link_cruise(f"skip_{stop.key}", prev, next_road, cruise, 0)
                prev = next_road
            else:
                entry = W.addNode(f"{stop.key}_Entry", prev.x + cruise, 0.0)
                stop_n = W.addNode(f"{stop.key}_Stop", entry.x + STOP_LINK_LENGTH_M, 0.0)
                exit_n = W.addNode(f"{stop.key}_Exit", stop_n.x + STOP_LINK_LENGTH_M, 0.0)
                dwell = _dwell_seconds(stop.kind, cal, short_dwell_scale)
                us = _speed_from_dwell(dwell)
                W.addLink(f"{stop.key}_bay_in", entry, stop_n, STOP_LINK_LENGTH_M, us, number_of_lanes=STOP_LANES)
                W.addLink(f"{stop.key}_bay_out", stop_n, exit_n, STOP_LINK_LENGTH_M, us, number_of_lanes=STOP_LANES)
                link_cruise(f"to_{stop.key}", prev, entry, cruise, 0)
                W.addLink(
                    f"bypass_{stop.key}",
                    prev,
                    exit_n,
                    cruise + 2.0 * STOP_LINK_LENGTH_M,
                    u,
                    number_of_lanes=LANES_MAIN,
                    signal_group=[0],
                )
                W.addLink(
                    f"bypass_{stop.key}_rev",
                    exit_n,
                    prev,
                    cruise + 2.0 * STOP_LINK_LENGTH_M,
                    u,
                    number_of_lanes=LANES_MAIN,
                    signal_group=[1],
                )
                prev = exit_n
        prev_chain = chain

    cruise_wm = _cruise_len(prev_chain, CORRIDOR_LENGTH_M)
    wm_road = W.addNode("Waltermart_Road", prev.x + cruise_wm, 0.0)
    link_cruise("to_wm_road", prev, wm_road, cruise_wm, 0)
    wm_stop = W.addNode("Waltermart_BusStop", wm_road.x + STOP_LINK_LENGTH_M, 0.0)
    dwell_wm = _dwell_seconds("terminal_formal", cal, short_dwell_scale)
    u_wm = _speed_from_dwell(dwell_wm)
    W.addLink("WM_Stop_in", wm_road, wm_stop, STOP_LINK_LENGTH_M, u_wm, number_of_lanes=STOP_LANES)
    W.addLink("WM_Stop_out", wm_stop, wm_road, STOP_LINK_LENGTH_M, u_wm, number_of_lanes=STOP_LANES)

    policy = "baseline (formal + informal)" if include_informal_stops else "optimized (formal + Vista; informal removed)"
    sig_line = ", ".join(f"{s.key}@{s.chainage_m:.0f}m" for s in CORRIDOR_SIGNALS)
    print(f"  Extended corridor: {policy}")
    print(f"  Length {CORRIDOR_LENGTH_M:.0f} m | signals (180s): {sig_line}")
    print(f"  Synchronized offset {signal_offset_s:.0f} s on all signals")

    return {
        "rb_bus_stop": rb_stop,
        "wm_bus_stop": wm_stop,
        "rb_road": rb_road,
        "wm_road": wm_road,
        "signal": signal_nodes.get("aguinaldo_mid"),
        "signals": signal_nodes,
    }
