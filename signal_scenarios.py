"""
Green/Red encounter patterns for all signal passes on a round trip.

With 3 corridor signals (Pala-Pala, Aguinaldo mid, Waltermart intersection), a full
round trip has 6 encounters (3 eastbound + 3 westbound) -> 2^6 = 64 patterns.

3 sessions x 4 policies x 64 = 768 simulations (>= 320).
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from corridor_config import (
    CORRIDOR_LENGTH_M,
    CORRIDOR_SIGNALS,
    FREE_FLOW_MPS,
    SIGNAL_CYCLE_S,
    SIGNAL_ENCOUNTERS_PER_ROUND_TRIP,
    SIGNAL_GREEN_EB_S,
    SIGNAL_GREEN_WB_S,
)

N_SIGNALS = len(CORRIDOR_SIGNALS)


def _arrival_t_eb(signal_index: int) -> float:
    return CORRIDOR_SIGNALS[signal_index].chainage_m / FREE_FLOW_MPS


def _arrival_t_wb(signal_index: int) -> float:
    return (CORRIDOR_LENGTH_M - CORRIDOR_SIGNALS[signal_index].chainage_m) / FREE_FLOW_MPS


def _encounter_group_and_base_arrival(encounter_i: int) -> tuple[int, float]:
    """encounter 0..N-1: EB at signals 0..; encounter N..2N-1: WB at signals N-1..0."""
    if encounter_i < N_SIGNALS:
        return 0, _arrival_t_eb(encounter_i)
    j = 2 * N_SIGNALS - 1 - encounter_i
    return 1, _arrival_t_wb(j)


EST_RB_WM_LEG_BEFORE_RETURN_S = (
    CORRIDOR_LENGTH_M / FREE_FLOW_MPS + 50.0
)


def _group_is_green(t: float, group: int, offset_s: float) -> bool:
    t_mod = (t + offset_s) % SIGNAL_CYCLE_S
    if group == 0:
        return t_mod < SIGNAL_GREEN_EB_S
    return t_mod >= SIGNAL_GREEN_EB_S


def _offset_for_group_at_time(want_green: bool, group: int, arrival_t: float) -> float:
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
    step = 5.0
    for shift in range(0, int(SIGNAL_CYCLE_S), int(step)):
        if _group_is_green(base_arrival_t + float(shift), group, offset_s) == want_green:
            return float(shift)
    return 0.0 if want_green else (SIGNAL_GREEN_WB_S if group == 1 else SIGNAL_GREEN_EB_S)


@dataclass(frozen=True)
class SignalEncounterScenario:
    scenario_id: str
    encounter_greens: tuple[bool, ...]
    signal_offset_s: float
    wm_to_rb_demand_shift_s: float
    extra_rb_to_wm_shifts: tuple[float, ...]
    leg_shifts_s: tuple[float, ...]

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

    leg_shifts: list[float] = []
    group0, t0 = _encounter_group_and_base_arrival(0)
    offset = _offset_for_group_at_time(pattern[0], group0, t0)

    cumulative = 0.0
    for i in range(1, len(pattern)):
        group, base_t = _encounter_group_and_base_arrival(i)
        if i == N_SIGNALS:
            base_t = EST_RB_WM_LEG_BEFORE_RETURN_S
        elif i > N_SIGNALS:
            base_t = EST_RB_WM_LEG_BEFORE_RETURN_S + _arrival_t_wb(2 * N_SIGNALS - 1 - i)
        shift = _shift_for_group_at_time(pattern[i], group, offset, base_t + cumulative)
        leg_shifts.append(shift)
        cumulative += shift

    wm_shift = leg_shifts[N_SIGNALS - 1] if len(leg_shifts) >= N_SIGNALS else 0.0
    extra_rb = tuple(leg_shifts[N_SIGNALS:]) if len(leg_shifts) > N_SIGNALS else ()

    return SignalEncounterScenario(
        scenario_id=_scenario_id(pattern),
        encounter_greens=pattern,
        signal_offset_s=offset,
        wm_to_rb_demand_shift_s=wm_shift,
        extra_rb_to_wm_shifts=extra_rb,
        leg_shifts_s=tuple(leg_shifts),
    )


def all_signal_scenarios(n_encounters: int | None = None) -> tuple[SignalEncounterScenario, ...]:
    n = n_encounters if n_encounters is not None else SIGNAL_ENCOUNTERS_PER_ROUND_TRIP
    if n < 1 or n > 8:
        raise ValueError("n_encounters must be between 1 and 8")
    patterns = list(itertools.product((True, False), repeat=n))
    return tuple(build_signal_scenario(p) for p in patterns)


SIGNAL_ENCOUNTER_SCENARIOS: tuple[SignalEncounterScenario, ...] = all_signal_scenarios()
