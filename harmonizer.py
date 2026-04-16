"""Końcowy wybór akordów dla slotów.

Ten moduł jest orkiestratorem i korzysta wyłącznie z danych przygotowanych
wcześniej w pipeline.
"""

from __future__ import annotations

from typing import Optional

from config import HarmonizationConfig
from models import ChordCandidate, PieceModel
from rules import score_candidate


class HarmonizationPrerequisiteError(RuntimeError):
    pass


def harmonize(piece: PieceModel, config: HarmonizationConfig) -> None:
    _validate_ready_piece(piece)

    prev1: Optional[ChordCandidate] = None
    prev2: Optional[ChordCandidate] = None

    for slot in piece.harmonic_slots:
        slot.candidates = [candidate_copy(c) for c in piece.candidate_pool]
        plan = piece.slot_plan_map.get(slot.global_slot_idx)

        best: Optional[ChordCandidate] = None
        best_score = float("-inf")
        for candidate in slot.candidates:
            candidate.score = score_candidate(piece, slot, candidate, plan, config, prev1, prev2)
            if candidate.score > best_score:
                best = candidate
                best_score = candidate.score

        slot.chosen_chord = best
        prev2 = prev1
        prev1 = best


def _validate_ready_piece(piece: PieceModel) -> None:
    if piece.settings is None:
        raise HarmonizationPrerequisiteError("Brak settings w PieceModel.")
    if piece.key_info is None:
        raise HarmonizationPrerequisiteError("Brak key_info. Najpierw theory.py.")
    if not piece.phrases:
        raise HarmonizationPrerequisiteError("Brak fraz. Najpierw phrases.py.")
    if not piece.harmonic_slots:
        raise HarmonizationPrerequisiteError("Brak slotów. Najpierw phrases.py.")
    if not piece.candidate_pool:
        raise HarmonizationPrerequisiteError("Brak kandydatów. Najpierw theory.py.")
    if not piece.phrase_plans:
        raise HarmonizationPrerequisiteError("Brak planu frazowego. Najpierw planner.py.")


def candidate_copy(candidate: ChordCandidate) -> ChordCandidate:
    return ChordCandidate(
        root_pc=candidate.root_pc,
        root_name=candidate.root_name,
        quality=candidate.quality,
        symbol=candidate.symbol,
        pitch_classes=tuple(candidate.pitch_classes),
        degree=candidate.degree,
        function=candidate.function,
        color_role=candidate.color_role,
        score=0.0,
    )
