"""Planowanie harmoniczne na poziomie fraz."""

from __future__ import annotations

from typing import Dict, List

from config import HarmonizationConfig
from models import PhrasePlan, PieceModel, SlotPlanExpectation
from theory import cadence_templates_for


def build_phrase_plans(piece: PieceModel, config: HarmonizationConfig) -> List[PhrasePlan]:
    if piece.key_info is None:
        raise ValueError("Planner wymaga wcześniej ustalonej tonacji.")
    if not piece.phrases or not piece.harmonic_slots:
        raise ValueError("Planner wymaga wcześniej policzonych fraz i slotów.")

    templates = cadence_templates_for(piece.key_info)
    plans: List[PhrasePlan] = []
    slot_plan_map: Dict[int, SlotPlanExpectation] = {}

    for phrase in piece.phrases:
        cadence_kind = _choose_cadence_kind(piece, phrase, config)
        cadence_span = _choose_cadence_span(phrase.length_slots)
        cadence_degrees = templates[cadence_kind][cadence_span]

        phrase.cadence_kind = cadence_kind
        phrase.cadence_span = cadence_span

        expectations: List[SlotPlanExpectation] = []
        phrase_slot_indices = list(range(phrase.start_slot_idx or 0, (phrase.end_slot_idx or -1) + 1))
        n = len(phrase_slot_indices)
        if n == 0:
            continue

        first_idx = phrase_slot_indices[0]
        exp_start = SlotPlanExpectation(
            phrase_id=phrase.phrase_id,
            slot_global_idx=first_idx,
            expected_functions=["T"],
            expected_degrees=[1],
            weight=4.0,
            label="phrase_start",
        )
        expectations.append(exp_start)
        slot_plan_map[first_idx] = exp_start

        cadence_indices = phrase_slot_indices[-cadence_span:]
        for idx, degree in zip(cadence_indices, cadence_degrees):
            function = piece.key_info.degree_functions.get(degree, "T")
            weight = 8.0 if idx == cadence_indices[-1] else 6.0
            exp = SlotPlanExpectation(
                phrase_id=phrase.phrase_id,
                slot_global_idx=idx,
                expected_functions=[function],
                expected_degrees=[degree],
                weight=weight,
                label=f"cadence_{cadence_kind}",
            )
            expectations.append(exp)
            slot_plan_map[idx] = exp

        plans.append(
            PhrasePlan(
                phrase_id=phrase.phrase_id,
                cadence_kind=cadence_kind,
                cadence_span=cadence_span,
                cadence_degrees=list(cadence_degrees),
                slot_expectations=expectations,
            )
        )

    piece.phrase_plans = plans
    piece.slot_plan_map = slot_plan_map
    return plans


def _choose_cadence_kind(piece: PieceModel, phrase, config: HarmonizationConfig) -> str:
    is_last = phrase.phrase_id == len(piece.phrases) - 1
    if config.cadence_strategy == "strict":
        return "authentic" if is_last else "half"
    if config.cadence_strategy == "relaxed":
        return "authentic"
    return "authentic" if is_last else "half"


def _choose_cadence_span(length_slots: int) -> int:
    if length_slots >= 4:
        return 4
    if length_slots == 3:
        return 3
    return 2
