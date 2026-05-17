"""
Field corridor: Robinsons Pala-Pala — Waltermart Dasmariñas (Emilio Aguinaldo Hwy).

Chainage and GPS from field notes (May 2026). Formal vs informal classification follows
the survey legend: formal = Robinsons, Waltermart, Vista Mall; informal = 7-Eleven,
Villa Verde, RCBC Bank (informal curbside loading).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

# --- Highway physics (shared) ---
FREE_FLOW_MPS = 16.67  # ~60 km/h
LANES_MAIN = 2
STOP_LINK_LENGTH_M = 25.0
STOP_LANES = 1
DEFAULT_DWELL_S = 40.0

# Total corridor length (terminal to terminal along mainline chainage).
CORRIDOR_LENGTH_M = 3049.0

# Signal cycle 180 s (90 s eastbound + 90 s westbound per intersection).
SIGNAL_CYCLE_S = 180.0
SIGNAL_GREEN_EB_S = 90.0
SIGNAL_GREEN_WB_S = 90.0

# Legacy alias (mid-corridor Aguinaldo signal chainage).
SIGNAL_CHAINAGE_M = 2495.0


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    r = 6371000.0
    p1, p2 = radians(lat1), radians(lat2)
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(p1) * cos(p2) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


# GPS reference (field / Maps).
GPS_ORIGIN_RB = (14.3002, 120.9529)
GPS_STOPS = {
    "robinsons": GPS_ORIGIN_RB,
    "informal_robinsons": GPS_ORIGIN_RB,
    "seven_eleven": (14.3019, 120.9523),
    "villa_verde": (14.3149, 120.9450),
    "vista_mall": (14.31687, 120.94415),
    "rcbc": (14.3236, 120.9415),
    "waltermart": (14.3250, 120.9410),
}


@dataclass(frozen=True)
class CorridorSignal:
    key: str
    label: str
    chainage_m: float
    gps: tuple[float, float]
    green_eb_s: float = SIGNAL_GREEN_EB_S
    green_wb_s: float = SIGNAL_GREEN_WB_S

    @property
    def cycle_s(self) -> float:
        return self.green_eb_s + self.green_wb_s


# Three signalized intersections (180 s cycle each); chainage from Robinsons origin.
# Pala-Pala / Waltermart positions from GPS; mid corridor retained at 2495 m.
_CHAIN_PALA = round(_haversine_m(*GPS_ORIGIN_RB, 14.30245, 120.95427))
_CHAIN_WM_INT = CORRIDOR_LENGTH_M - round(_haversine_m(14.3250, 120.9410, 14.32556, 120.94083))

CORRIDOR_SIGNALS: tuple[CorridorSignal, ...] = (
    CorridorSignal("pala_pala", "Pala-Pala Intersection Signal", float(_CHAIN_PALA), (14.30245, 120.95427)),
    CorridorSignal("aguinaldo_mid", "Aguinaldo mid-corridor Signal", SIGNAL_CHAINAGE_M, (14.31687, 120.94415)),
    CorridorSignal(
        "waltermart_int",
        "Waltermart Dasmariñas Intersection Signal",
        float(_CHAIN_WM_INT),
        (14.32556, 120.94083),
    ),
)

# Round-trip: one pass per signal per direction (see signal_scenarios.py).
SIGNAL_ENCOUNTERS_PER_ROUND_TRIP = len(CORRIDOR_SIGNALS) * 2

StopKind = Literal["terminal_formal", "formal", "informal", "signal"]


@dataclass(frozen=True)
class CorridorStop:
    chainage_m: float
    key: str
    label: str
    kind: StopKind
    direction: Literal["rb_to_wm", "wm_to_rb", "both"]


# Forward (Robinsons → Waltermart): chainage from Robinsons terminal origin.
STOPS_RB_TO_WM: tuple[CorridorStop, ...] = (
    CorridorStop(0, "robinsons", "Robinsons terminal", "terminal_formal", "both"),
    CorridorStop(50, "informal_robinsons", "In front of Robinsons [pre-signal]", "informal", "rb_to_wm"),
    CorridorStop(200, "seven_eleven", "7-Eleven Pala Pala", "informal", "rb_to_wm"),
    CorridorStop(1845, "villa_verde", "Villa Verde", "informal", "rb_to_wm"),
    CorridorStop(2083, "vista_mall", "Vista Mall", "formal", "rb_to_wm"),
    CorridorStop(2884, "rcbc", "RCBC Bank [post-signal]", "informal", "rb_to_wm"),
    CorridorStop(CORRIDOR_LENGTH_M, "waltermart", "Waltermart terminal", "terminal_formal", "both"),
)

# Reverse (Waltermart → Robinsons): chainage from Waltermart terminal origin.
STOPS_WM_TO_RB: tuple[CorridorStop, ...] = (
    CorridorStop(0, "waltermart", "Waltermart terminal", "terminal_formal", "both"),
    CorridorStop(165, "rcbc", "RCBC Bank", "informal", "wm_to_rb"),
    CorridorStop(966, "vista_mall", "Vista Mall", "formal", "wm_to_rb"),
    CorridorStop(1203, "villa_verde", "Villa Verde", "informal", "wm_to_rb"),
    CorridorStop(CORRIDOR_LENGTH_M, "robinsons", "Robinsons terminal", "terminal_formal", "both"),
)

# Signal encounter scenarios: see signal_scenarios.py (2^N patterns for N encounters).

# --- Session terminal dwell means (from Data_Collection.xlsx; same as bus_calibration) ---
SESSION_DWELL: dict[str, dict[str, float]] = {
    "Morning Session": {"robinsons": 46.6, "waltermart": 35.1},
    "Lunch": {"robinsons": 59.4, "waltermart": 35.0},
    "Afternoon Session": {"robinsons": 52.3, "waltermart": 41.3},
}

SESSIONS: tuple[str, ...] = ("Morning Session", "Lunch", "Afternoon Session")
ORIGINS: tuple[str, ...] = ("robinsons_location", "waltermart_location")

# 3 sessions x 4 policies x 2^6 signal patterns = 768 runs (>= 320).
MIN_FULL_MATRIX_RUNS = len(SESSIONS) * 4 * (2**SIGNAL_ENCOUNTERS_PER_ROUND_TRIP)

# Notebook exploratory flows (veh/s); simulation_extended.py uses Excel row volumes instead.
SESSION_DEMAND: dict[str, dict[str, float]] = {
    "Morning Session": {"bus": 0.008, "car": 0.05, "jeepney": 0.020},
    "Lunch": {"bus": 0.005, "car": 0.03, "jeepney": 0.015},
    "Afternoon Session": {"bus": 0.007, "car": 0.04, "jeepney": 0.018},
}

# Notebook / sensitivity: optional fixed headways (veh/s = 1/headway when set).
HEADWAYS: dict[str, int | None] = {
    "headway_observed": None,
    "headway_10min": 600,
    "headway_15min": 900,
    "headway_20min": 1200,
}

# Stop policies (shared by simulation_extended naming + notebook 120-run grid).
# Formal mid-route = Vista Mall only (forward + reverse). 7-Eleven & Villa Verde = informal.
STOP_CONFIGS: dict[str, dict[str, bool | float]] = {
    "baseline_all_stops": {"use_formal": True, "use_informal": True, "dwell_scale": 1.00},
    "baseline_all_informal": {"use_formal": False, "use_informal": True, "dwell_scale": 1.00},
    "baseline_mixed": {"use_formal": True, "use_informal": True, "dwell_scale": 1.00},
    "optimized_formal_only": {"use_formal": True, "use_informal": False, "dwell_scale": 1.00},
    "optimized_short_dwell": {"use_formal": True, "use_informal": False, "dwell_scale": 0.55},
    "optimized_two_formal": {"use_formal": True, "use_informal": False, "dwell_scale": 0.75},
}

# Aliases for notebooks
TOTAL_LENGTH_M = CORRIDOR_LENGTH_M
FREE_FLOW_SPEED = FREE_FLOW_MPS
NUM_LANES = LANES_MAIN
SIGNAL_POS = SIGNAL_CHAINAGE_M
TMAX = 3600


def _stop_dict_entry(stop: CorridorStop) -> dict[str, float | str]:
    return {"pos": stop.chainage_m, "kind": stop.kind, "label": stop.label}


def stops_by_kind(
    stops: tuple[CorridorStop, ...],
    *,
    direction: Literal["rb_to_wm", "wm_to_rb"],
    kinds: tuple[StopKind, ...],
) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for s in stops:
        if s.direction not in (direction, "both"):
            continue
        if s.kind not in kinds or s.kind == "signal":
            continue
        if s.key in ("robinsons", "waltermart"):
            continue
        out[s.key] = _stop_dict_entry(s)
    return out


def formal_stops_fwd() -> dict[str, dict]:
    return stops_by_kind(STOPS_RB_TO_WM, direction="rb_to_wm", kinds=("formal",))


def informal_stops_fwd() -> dict[str, dict]:
    return stops_by_kind(STOPS_RB_TO_WM, direction="rb_to_wm", kinds=("informal",))


def formal_stops_rev() -> dict[str, dict]:
    return stops_by_kind(STOPS_WM_TO_RB, direction="wm_to_rb", kinds=("formal",))


def informal_stops_rev() -> dict[str, dict]:
    return stops_by_kind(STOPS_WM_TO_RB, direction="wm_to_rb", kinds=("informal",))


def dwell_for_stop(session: str, stop_key: str, dwell_scale: float = 1.0) -> float:
    """Session-based dwell (seconds) aligned with corridor_network.py logic."""
    sess = SESSION_DWELL[session]
    rb, wm = sess["robinsons"], sess["waltermart"]
    stop = next((s for s in STOPS_RB_TO_WM + STOPS_WM_TO_RB if s.key == stop_key), None)
    if stop is None:
        return DEFAULT_DWELL_S
    kind = stop.kind
    if kind == "terminal_formal":
        base = (rb + wm) / 2.0
    elif kind == "formal":
        base = max(rb, wm) * 0.85
    elif kind == "informal":
        base = max(rb * 1.12, 45.0)
        if stop_key == "rcbc" or "rcbc" in stop_key:
            base = max(wm * 1.05, 35.0)
        if stop_key == "informal_robinsons":
            base = max(rb * 1.12, 45.0)
    else:
        base = DEFAULT_DWELL_S
    if dwell_scale < 1.0:
        return max(8.0, base * dwell_scale)
    return base


def active_stops_for_config(
    session: str,
    stop_cfg: dict,
) -> tuple[dict[str, dict], dict[str, dict]]:
    """Build forward/reverse stop dicts with pos + dwell for notebook or tools."""
    scale = float(stop_cfg.get("dwell_scale", 1.0))
    use_formal = bool(stop_cfg.get("use_formal", True))
    use_informal = bool(stop_cfg.get("use_informal", True))
    fwd: dict[str, dict] = {}
    rev: dict[str, dict] = {}
    if use_informal:
        for k, v in informal_stops_fwd().items():
            fwd[k] = {"pos": v["pos"], "dwell": dwell_for_stop(session, k, scale)}
        for k, v in informal_stops_rev().items():
            rev[k] = {"pos": v["pos"], "dwell": dwell_for_stop(session, k, scale)}
    if use_formal:
        for k, v in formal_stops_fwd().items():
            fwd[k] = {"pos": v["pos"], "dwell": dwell_for_stop(session, k, scale)}
        for k, v in formal_stops_rev().items():
            rev[k] = {"pos": v["pos"], "dwell": dwell_for_stop(session, k, scale)}
    return fwd, rev


# Legacy notebook names (import as FORMAL_STOPS_FWD = formal_stops_fwd() after load).
FORMAL_STOPS_FWD = formal_stops_fwd()
INFORMAL_STOPS_FWD = informal_stops_fwd()
FORMAL_STOPS_REV = formal_stops_rev()
INFORMAL_STOPS_REV = informal_stops_rev()


def print_corridor_legend() -> None:
    print("Signals (180 s cycle, 90 s EB + 90 s WB each):")
    for sig in CORRIDOR_SIGNALS:
        print(f"  {sig.chainage_m:4.0f}m  {sig.label}  GPS {sig.gps}")
    print("Forward (Robinsons -> Waltermart) stops:")
    for s in STOPS_RB_TO_WM:
        if s.kind != "signal":
            print(f"  {s.chainage_m:4.0f}m  [{s.kind:16s}]  {s.label}")
    print("Reverse (Waltermart -> Robinsons) stops:")
    for s in STOPS_WM_TO_RB:
        if s.kind != "signal":
            print(f"  {s.chainage_m:4.0f}m  [{s.kind:16s}]  {s.label}")


# Mixed traffic: relative demand multipliers vs bus sheet row-count volume (tune as needed).
@dataclass(frozen=True)
class VehicleClass:
    key: str
    label: str
    volume_multiplier: float
    uses_bus_stops: bool


VEHICLE_CLASSES: tuple[VehicleClass, ...] = (
    VehicleClass("bus", "Bus", 1.0, True),
    VehicleClass("private_car", "Private car", 2.5, False),
    VehicleClass("jeepney", "Jeepney", 1.8, False),
    VehicleClass("truck", "Truck", 0.6, False),
    VehicleClass("motorcycle", "Motorcycle", 1.2, False),
    VehicleClass("van", "Van", 0.9, False),
)

POLICY_BASELINE = "baseline_all_stops"
POLICY_OPTIMIZED = "optimized_formal_only"

OPTIMIZED_SHORT_DWELL_SCALE = 0.55
