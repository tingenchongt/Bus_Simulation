"""
Build all Green/Red traffic-signal encounter patterns for UXsim runs.

Each encounter is one passage through Aguinaldo_Signal:
  encounter 1, 3, 5, ...  -> eastbound (Robinsons -> Waltermart), signal group 0
  encounter 2, 4, 6, ...  -> westbound (Waltermart -> Robinsons), signal group 1

For N encounters there are 2^N scenarios (e.g. N=2 -> G/G, G/R, R/G, R/R).

Timing uses representative arrival times + demand shifts so the modeled phase at
arrival matches the label (sensitivity analysis; not field-logged signal phases).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from corridor_config import (
    CORRIDOR_LENGTH_M,
    FREE_FLOW_MPS,
    SIGNAL_CHAINAGE_M,
    SIGNAL_CYCLE_S,
    SIGNAL_GREEN_EB_S,
    SIGNAL_GREEN_WB_S,
)

# Representative seconds from demand start to signal (no queue), for phase targeting.
EST_RB_DEPART_TO_SIGNAL_S = SIGNAL_CHAINAGE_M / FREE_FLOW_MPS
EST_WM_DEPART_TO_SIGNAL_S = (CORRIDOR_LENGTH_M - SIGNAL_CHAINAGE_M) / FREE_FLOW_MPS
EST_RB_WM_LEG_BEFORE_RETURN_S = EST_RB_DEPART_TO_SIGNAL_S + (CORRIDOR_LENGTH_M - SIGNAL_CHAINAGE_M) / FREE_FLOW_MPS + 50.0


def _group_is_green(t: float, group: int, offset_s: float) -> bool:
    t_mod = (t + offset_s) % SIGNAL_CYCLE_S
    if group == 0:
        return t_mod < SIGNAL_GREEN_EB_S
    return t_mod >= SIGNAL_GREEN_EB_S


def _offset_for_group_at_time(want_green: bool, group: int, arrival_t: float) -> float:
    """Pick offset in {0, green_other} so phase at arrival_t matches want_green for group."""
    candidates = (0.0, SIGNAL_GREEN_EB_S) if group == 0 else (0.0, SIGNAL_GREEN_WB_S)
    for off in candidates:
        if _group_is_green(arrival_t, group, off) == want_green:
            return off
    return candidates[0] if want_green else candidates[1]


def _shift_for_group_at_time(
    want_green: bool,
    group: int,
    offset_s: float,
    base_arrival_t: float,
) -> float:
    """Seconds to add to that leg's demand start so arrival hits desired phase."""
    step = 5.0
    for shift in range(0, int(SIGNAL_CYCLE_S), int(step)):
        t_arr = base_arrival_t + float(shift)
        if _group_is_green(t_arr, group, offset_s) == want_green:
            return float(shift)
    return 0.0 if want_green else (SIGNAL_GREEN_WB_S if group == 1 else SIGNAL_GREEN_EB_S)


@dataclass(frozen=True)
class SignalEncounterScenario:
    scenario_id: str
    encounter_greens: tuple[bool, ...]
    signal_offset_s: float
    wm_to_rb_demand_shift_s: float
    extra_rb_to_wm_shifts: tuple[float, ...]

    @property
    def n_encounters(self) -> int:
        return len(self.encounter_greens)

    @property
    def encounter_pattern(self) -> str:
        return "-".join("G" if g else "R" for g in self.encounter_greens)


def _scenario_id(pattern: tuple[bool, ...]) -> str:
    return "enc_" + "_".join("G" if g else "R" for g in pattern)


def build_signal_scenario(pattern: tuple[bool, ...]) -> SignalEncounterScenario:
    if not pattern:
        raise ValueError("pattern must have at least one encounter")
    offset = _offset_for_group_at_time(pattern[0], 0, EST_RB_DEPART_TO_SIGNAL_S)
    wm_shift = 0.0
    extra_rb: list[float] = []

    if len(pattern) >= 2:
        base_wm = EST_RB_WM_LEG_BEFORE_RETURN_S
        wm_shift = _shift_for_group_at_time(pattern[1], 1, offset, base_wm)

    for i in range(2, len(pattern)):
        group = 0 if i % 2 == 0 else 1
        if group == 0:
            base = EST_RB_WM_LEG_BEFORE_RETURN_S * (i // 2) + EST_RB_DEPART_TO_SIGNAL_S
            extra_rb.append(_shift_for_group_at_time(pattern[i], 0, offset, base))
        else:
            wm_shift = _shift_for_group_at_time(
                pattern[i], 1, offset, EST_RB_WM_LEG_BEFORE_RETURN_S * ((i + 1) // 2)
            )

    return SignalEncounterScenario(
        scenario_id=_scenario_id(pattern),
        encounter_greens=pattern,
        signal_offset_s=offset,
        wm_to_rb_demand_shift_s=wm_shift,
        extra_rb_to_wm_shifts=tuple(extra_rb),
    )


def all_signal_scenarios(n_encounters: int) -> tuple[SignalEncounterScenario, ...]:
    if n_encounters < 1 or n_encounters > 6:
        raise ValueError("n_encounters must be between 1 and 6 (2^N runs grows fast)")
    patterns = list(itertools.product((True, False), repeat=n_encounters))
    return tuple(build_signal_scenario(p) for p in patterns)


# Backward-compatible 2-encounter set (round-trip bus: first EB, second WB).
SIGNAL_ENCOUNTER_SCENARIOS: tuple[SignalEncounterScenario, ...] = all_signal_scenarios(2)
