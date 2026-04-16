"""Analiza strukturalna utworu: frazy i sloty harmoniczne."""

from __future__ import annotations

from typing import List

from config import HarmonizationConfig
from models import (
    HarmonicSlot,
    MeasureInfo,
    NoteInfo,
    PhraseInfo,
    PieceModel,
    get_beat_offsets,
    get_strong_beat_offsets,
)


def detect_phrases(piece: PieceModel) -> List[PhraseInfo]:
    melody = piece.melody_notes
    if not melody:
        piece.phrases = []
        return []

    boundaries: List[int] = []
    max_phrase_measures = 8

    for i, note in enumerate(melody[:-1]):
        score = 0.0
        next_note = melody[i + 1]

        if next_note.measure_number > note.measure_number and note.duration_ql >= 1.0:
            score += 1.5
        if note.offset_in_measure + note.duration_ql >= (piece.measure_duration_ql - 0.0001):
            score += 0.5
        if next_note.global_offset - (note.global_offset + note.duration_ql) >= 0.5:
            score += 2.0
        if note.pitch_class in {piece.key_tonic_pc, (piece.key_tonic_pc + 7) % 12}:
            score += 1.0

        phrase_start_measure = melody[(boundaries[-1] + 1) if boundaries else 0].measure_number
        if next_note.measure_number - phrase_start_measure >= max_phrase_measures:
            score += 1.0

        if score >= 2.0:
            boundaries.append(i)

    if not boundaries or boundaries[-1] != len(melody) - 1:
        boundaries.append(len(melody) - 1)

    phrases: List[PhraseInfo] = []
    start_idx = 0
    for phrase_id, end_idx in enumerate(boundaries):
        start_note = melody[start_idx]
        end_note = melody[end_idx]
        phrases.append(
            PhraseInfo(
                phrase_id=phrase_id,
                start_measure=start_note.measure_number,
                end_measure=end_note.measure_number,
                start_note_idx=piece.note_index_of(start_note) or 0,
                end_note_idx=piece.note_index_of(end_note) or 0,
                boundary_score=0.0,
                shape=_detect_shape(melody[start_idx:end_idx + 1]),
            )
        )
        start_idx = end_idx + 1
        if start_idx >= len(melody):
            break

    piece.phrases = phrases
    return phrases


def create_harmonic_slots(piece: PieceModel, config: HarmonizationConfig) -> List[HarmonicSlot]:
    slots: List[HarmonicSlot] = []
    auto_density = _infer_auto_density(piece) if config.harmonic_density == "auto" else None

    for measure in piece.measures:
        if measure.is_pickup:
            continue
        measure_length = measure.actual_duration_ql or measure.expected_duration_ql or piece.measure_duration_ql
        density = auto_density or config.harmonic_density

        if density == "per_measure":
            offsets = [0.0]
        elif density == "per_beat":
            offsets = get_beat_offsets(measure.time_sig_numerator, measure.time_sig_denominator)
        elif density == "per_strong_beat":
            offsets = get_strong_beat_offsets(measure.time_sig_numerator, measure.time_sig_denominator, measure_length)
        else:
            offsets = _auto_offsets_for_measure(measure, piece.measure_duration_ql)

        slots.extend(_offsets_to_slots(measure.number, offsets, measure_length))

    trim_slots_to_last_note(slots, piece)
    _attach_melody_to_slots(slots, piece)
    _annotate_slot_structure(piece, slots)
    piece.harmonic_slots = slots
    return slots


def analyze_phrases_and_slots(piece: PieceModel, config: HarmonizationConfig) -> None:
    detect_phrases(piece)
    create_harmonic_slots(piece, config)


def _auto_offsets_for_measure(measure: MeasureInfo, default_measure_ql: float) -> List[float]:
    measure_length = measure.actual_duration_ql or measure.expected_duration_ql or default_measure_ql
    ts_num = measure.time_sig_numerator
    ts_den = measure.time_sig_denominator
    beat_len = 4.0 / ts_den
    pitched = [n for n in measure.notes if not n.is_rest]

    if not pitched:
        return [0.0]

    longest = max(n.duration_ql for n in pitched)
    strong_offsets = get_strong_beat_offsets(ts_num, ts_den, measure_length)
    beat_offsets = get_beat_offsets(ts_num, ts_den)
    onset_offsets = {round(n.offset_in_measure, 4) for n in pitched}
    short_count = sum(1 for n in pitched if n.duration_ql <= beat_len)

    if longest >= 0.75 * measure_length:
        return [0.0]
    if any(so > 0 and any(abs(so - no) < 0.0001 for no in onset_offsets) for so in strong_offsets):
        return strong_offsets
    if short_count >= ts_num:
        return beat_offsets
    return [0.0]


def _offsets_to_slots(measure_number: int, offsets: List[float], measure_length: float) -> List[HarmonicSlot]:
    points = sorted({round(float(o), 4) for o in offsets if 0.0 <= o < measure_length}) or [0.0]
    edges = points + [round(measure_length, 4)]
    result: List[HarmonicSlot] = []
    for i in range(len(edges) - 1):
        start = edges[i]
        duration = round(edges[i + 1] - edges[i], 4)
        if duration <= 0.0:
            continue
        result.append(HarmonicSlot(measure_number=measure_number, offset_in_measure=start, duration_ql=duration))
    return result


def trim_slots_to_last_note(slots: List[HarmonicSlot], piece: PieceModel) -> None:
    pitched = piece.melody_notes
    if not pitched:
        return
    last_note = max(pitched, key=lambda n: (n.measure_number, n.offset_in_measure + n.duration_ql))
    last_measure = last_note.measure_number
    last_end = round(last_note.offset_in_measure + last_note.duration_ql, 4)

    kept: List[HarmonicSlot] = []
    for slot in slots:
        if slot.measure_number < last_measure:
            kept.append(slot)
        elif slot.measure_number == last_measure and slot.offset_in_measure < last_end:
            slot.duration_ql = min(slot.duration_ql, max(0.25, round(last_end - slot.offset_in_measure, 4)))
            kept.append(slot)
    slots[:] = kept


def _attach_melody_to_slots(slots: List[HarmonicSlot], piece: PieceModel) -> None:
    by_measure: dict[int, List[NoteInfo]] = {}
    for note in piece.all_notes:
        by_measure.setdefault(note.measure_number, []).append(note)

    for slot in slots:
        start = slot.offset_in_measure
        end = round(slot.offset_in_measure + slot.duration_ql, 4)
        notes = []
        for note in by_measure.get(slot.measure_number, []):
            note_start = round(note.offset_in_measure, 4)
            note_end = round(note.offset_in_measure + note.duration_ql, 4)
            if start <= note_start < end or (note_start <= start < note_end):
                notes.append(note)
        slot.melody_notes = notes


def _annotate_slot_structure(piece: PieceModel, slots: List[HarmonicSlot]) -> None:
    for idx, slot in enumerate(slots):
        slot.global_slot_idx = idx
        slot.is_piece_start = idx == 0
        slot.is_piece_end = idx == len(slots) - 1

    for phrase in piece.phrases:
        phrase_slots = [s for s in slots if phrase.start_measure <= s.measure_number <= phrase.end_measure]
        if not phrase_slots:
            continue
        phrase.start_slot_idx = phrase_slots[0].global_slot_idx
        phrase.end_slot_idx = phrase_slots[-1].global_slot_idx
        phrase.length_slots = len(phrase_slots)

        for i, slot in enumerate(phrase_slots):
            slot.phrase_id = phrase.phrase_id
            slot.slot_in_phrase = i
            slot.phrase_length_slots = len(phrase_slots)
            slot.slots_from_phrase_start = i
            slot.slots_to_phrase_end = len(phrase_slots) - 1 - i
            slot.is_phrase_start = i == 0
            slot.is_phrase_end = i == len(phrase_slots) - 1
            slot.formal_label = _formal_label(i, len(phrase_slots))


def _formal_label(slot_in_phrase: int, phrase_len: int) -> str:
    if phrase_len <= 1:
        return "end"
    if slot_in_phrase == 0:
        return "start"
    if slot_in_phrase == phrase_len - 1:
        return "end"
    if slot_in_phrase >= max(phrase_len - 2, 1):
        return "pre_end"
    return "middle"


def _infer_auto_density(piece: PieceModel) -> str:
    pitched = piece.melody_notes
    if not pitched:
        return "per_measure"
    avg_duration = sum(n.duration_ql for n in pitched) / len(pitched)
    if avg_duration <= 0.75:
        return "per_beat"
    if avg_duration <= 1.5:
        return "per_strong_beat"
    return "per_measure"


def _detect_shape(notes: List[NoteInfo]) -> str:
    pitched = [n for n in notes if not n.is_rest]
    if len(pitched) < 2:
        return "flat"
    midis = [n.midi_number for n in pitched]
    first_avg = sum(midis[: max(len(midis) // 3, 1)]) / max(len(midis) // 3, 1)
    last_avg = sum(midis[-max(len(midis) // 3, 1):]) / max(len(midis) // 3, 1)
    peak = max(midis)
    peak_pos = midis.index(peak) / max(len(midis) - 1, 1)

    if 0.2 < peak_pos < 0.8 and last_avg < first_avg + (peak - min(midis)) * 0.3:
        return "arch"
    if last_avg - first_avg > 3:
        return "ascending"
    if first_avg - last_avg > 3:
        return "descending"
    return "wave"
