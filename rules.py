"""Reguły scoringowe harmonizera.

To jedyne miejsce, gdzie istnieją:
- wagi,
- reguły,
- łączenie wyniku punktowego.
"""

from __future__ import annotations

from typing import Dict, Optional

from config import HarmonizationConfig
from models import ChordCandidate, HarmonicSlot, PieceModel, SlotPlanExpectation

BASE_WEIGHTS = {
    "melody_fit_strong": 16.0,
    "melody_fit_weak": 6.0,
    "melody_nonfit_strong": -16.0,
    "melody_nonfit_weak": -3.0,
    "plan_match_function": 4.0,
    "plan_match_degree": 6.0,
    "phrase_start_tonic": 4.0,
    "phrase_end_tonic": 8.0,
    "piece_end_tonic": 15.0,
    "pre_end_dominant": 7.0,
    "repeat_same_chord": -3.0,
    "same_function_repeat": -1.0,
    "transition_good": 3.0,
    "transition_bad": -4.0,
    "two_step_direction": 1.5,
    "borrowed_penalty": -3.0,
    "borrowed_bonus": 1.0,
}

PROFILE_OVERRIDES: Dict[str, Dict[str, float]] = {
    "melody_strict": {
        "melody_fit_strong": 19.0,
        "melody_nonfit_strong": -20.0,
        "melody_nonfit_weak": -5.0,
    },
    "melody_flexible": {
        "melody_fit_strong": 13.0,
        "melody_nonfit_strong": -11.0,
        "melody_nonfit_weak": -2.0,
    },
    "cadence_light": {
        "phrase_end_tonic": 6.0,
        "piece_end_tonic": 12.0,
        "pre_end_dominant": 5.0,
    },
    "cadence_strong": {
        "phrase_end_tonic": 10.0,
        "piece_end_tonic": 18.0,
        "pre_end_dominant": 9.0,
    },
    "variety_stable": {
        "repeat_same_chord": -1.5,
        "same_function_repeat": -0.5,
    },
    "variety_active": {
        "repeat_same_chord": -5.0,
        "same_function_repeat": -2.0,
    },
    "color_classic": {
        "borrowed_penalty": -2.0,
    },
    "color_rich": {
        "borrowed_penalty": -1.0,
        "borrowed_bonus": 2.0,
    },
}

GOOD_TRANSITIONS = {
    ("T", "S"), ("T", "D"), ("S", "D"), ("D", "T"), ("S", "T")
}
BAD_TRANSITIONS = {
    ("D", "S")
}


def build_weights(config: HarmonizationConfig) -> Dict[str, float]:
    weights = dict(BASE_WEIGHTS)
    for key in [
        f"melody_{config.melody_profile}",
        f"cadence_{config.cadence_profile}",
        f"variety_{config.variety_profile}",
        f"color_{config.color_profile}",
    ]:
        if key in PROFILE_OVERRIDES:
            weights.update(PROFILE_OVERRIDES[key])
    return weights


def score_candidate(
    piece: PieceModel,
    slot: HarmonicSlot,
    candidate: ChordCandidate,
    plan: Optional[SlotPlanExpectation],
    config: HarmonizationConfig,
    prev1: Optional[ChordCandidate],
    prev2: Optional[ChordCandidate],
) -> float:
    weights = build_weights(config)
    score = 0.0
    score += _score_melody_membership(slot, candidate, weights)
    score += _score_plan(candidate, plan, weights)
    score += _score_formal_position(slot, candidate, weights)
    score += _score_transition(candidate, prev1, prev2, weights)
    score += _score_variety(candidate, prev1, weights)
    score += _score_color(candidate, config, weights)
    return score


def _score_melody_membership(slot: HarmonicSlot, candidate: ChordCandidate, weights: Dict[str, float]) -> float:
    score = 0.0
    for note in slot.melody_notes:
        if note.is_rest:
            continue
        in_chord = candidate.contains_pc(note.pitch_class)
        strong = note.beat_strength >= 0.5
        if in_chord and strong:
            score += weights["melody_fit_strong"]
        elif in_chord:
            score += weights["melody_fit_weak"]
        elif strong:
            score += weights["melody_nonfit_strong"]
        else:
            score += weights["melody_nonfit_weak"]
    return score


def _score_plan(candidate: ChordCandidate, plan: Optional[SlotPlanExpectation], weights: Dict[str, float]) -> float:
    if plan is None:
        return 0.0
    score = 0.0
    if candidate.function in plan.expected_functions:
        score += weights["plan_match_function"] * plan.weight / 4.0
    if candidate.degree in plan.expected_degrees:
        score += weights["plan_match_degree"] * plan.weight / 4.0
    return score


def _score_formal_position(slot: HarmonicSlot, candidate: ChordCandidate, weights: Dict[str, float]) -> float:
    score = 0.0
    if slot.is_phrase_start and candidate.degree == 1:
        score += weights["phrase_start_tonic"]
    if slot.is_phrase_end and candidate.degree == 1:
        score += weights["phrase_end_tonic"]
    if slot.is_piece_end and candidate.degree == 1:
        score += weights["piece_end_tonic"]
    if slot.formal_label == "pre_end" and candidate.function == "D":
        score += weights["pre_end_dominant"]
    return score


def _score_transition(candidate: ChordCandidate, prev1: Optional[ChordCandidate], prev2: Optional[ChordCandidate], weights: Dict[str, float]) -> float:
    if prev1 is None:
        return 0.0
    score = 0.0
    pair = (prev1.function, candidate.function)
    if pair in GOOD_TRANSITIONS:
        score += weights["transition_good"]
    if pair in BAD_TRANSITIONS:
        score += weights["transition_bad"]
    if prev2 is not None and prev2.function == "T" and prev1.function == "S" and candidate.function == "D":
        score += weights["two_step_direction"]
    if prev2 is not None and prev2.function == "S" and prev1.function == "D" and candidate.function == "T":
        score += weights["two_step_direction"]
    return score


def _score_variety(candidate: ChordCandidate, prev1: Optional[ChordCandidate], weights: Dict[str, float]) -> float:
    if prev1 is None:
        return 0.0
    if candidate.symbol == prev1.symbol:
        return weights["repeat_same_chord"]
    if candidate.function == prev1.function:
        return weights["same_function_repeat"]
    return 0.0


def _score_color(candidate: ChordCandidate, config: HarmonizationConfig, weights: Dict[str, float]) -> float:
    if candidate.color_role == "diatonic":
        return 0.0
    if config.allow_borrowed_chords or config.color_profile in {"classic", "rich"}:
        return weights["borrowed_bonus"]
    return weights["borrowed_penalty"]
