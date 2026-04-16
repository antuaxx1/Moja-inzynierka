"""Centralne struktury danych dla harmonizera.

Ten plik jest wspólną warstwą danych całego pipeline'u. Każdy etap:
- parser,
- analiza fraz i slotów,
- teoria,
- planner,
- harmonizer,
- eksport,
pracuje na tych samych obiektach.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

from music21 import meter


@lru_cache(maxsize=None)
def _time_sig(ts_num: int, ts_den: int) -> meter.TimeSignature:
    return meter.TimeSignature(f"{ts_num}/{ts_den}")


def get_accent_weight(offset_ql: float, ts_num: int, ts_den: int) -> float:
    return float(_time_sig(ts_num, ts_den).getAccentWeight(round(offset_ql, 4)))


def get_beat_offsets(ts_num: int, ts_den: int) -> List[float]:
    return [round(float(o), 4) for o in _time_sig(ts_num, ts_den).getBeatOffsets()]


def get_strong_beat_offsets(ts_num: int, ts_den: int, measure_ql: float) -> List[float]:
    offsets = get_beat_offsets(ts_num, ts_den)
    if len(offsets) <= 1:
        return [0.0]

    non_zero = [o for o in offsets if o > 0]
    weights = {o: get_accent_weight(o, ts_num, ts_den) for o in non_zero}
    if not weights:
        return [0.0]
    max_w = max(weights.values())
    min_w = min(weights.values())
    if len(non_zero) > 1 and max_w <= min_w:
        return [0.0]

    half = measure_ql / 2.0
    secondary = max(non_zero, key=lambda o: (weights[o], -abs(o - half)))
    return [0.0, secondary]


@dataclass
class NoteInfo:
    pitch_name: str
    midi_number: int
    pitch_class: int
    duration_ql: float
    offset_in_measure: float
    measure_number: int
    is_rest: bool
    is_tied_forward: bool = False
    beat_strength: float = 0.0
    global_offset: float = 0.0


@dataclass
class MeasureInfo:
    number: int
    time_sig_numerator: int = 4
    time_sig_denominator: int = 4
    notes: List[NoteInfo] = field(default_factory=list)
    total_duration_ql: float = 0.0
    actual_duration_ql: float = 0.0
    expected_duration_ql: float = 0.0
    is_pickup: bool = False


@dataclass
class HarmonizationSettings:
    preset_name: str = "auto"
    harmonic_density: str = "auto"
    complexity: str = "triads_v7"
    melody_profile: str = "balanced"
    cadence_profile: str = "balanced"
    color_profile: str = "diatonic"
    variety_profile: str = "balanced"
    cadence_strategy: str = "balanced"
    force_pre_cadence: bool = False
    allow_borrowed_chords: bool = False
    key_mode: str = "auto"
    manual_tonic: str = ""
    manual_mode: str = "major"
    generate_voices: bool = False
    add_chord_symbols: bool = True
    export_pdf: bool = True
    export_musicxml: bool = True


@dataclass
class PhraseInfo:
    phrase_id: int
    start_measure: int
    end_measure: int
    start_note_idx: int
    end_note_idx: int
    boundary_score: float = 0.0
    shape: str = "unknown"
    start_slot_idx: Optional[int] = None
    end_slot_idx: Optional[int] = None
    length_slots: int = 0
    cadence_kind: str = ""
    cadence_span: int = 0

    @property
    def length_measures(self) -> int:
        return self.end_measure - self.start_measure + 1


@dataclass
class HarmonicSlot:
    measure_number: int
    offset_in_measure: float
    duration_ql: float
    melody_notes: List[NoteInfo] = field(default_factory=list)
    candidates: List["ChordCandidate"] = field(default_factory=list)
    chosen_chord: Optional["ChordCandidate"] = None
    global_slot_idx: int = -1
    phrase_id: int = -1
    slot_in_phrase: int = -1
    phrase_length_slots: int = 0
    slots_to_phrase_end: int = 0
    slots_from_phrase_start: int = 0
    formal_label: str = "middle"
    is_phrase_start: bool = False
    is_phrase_end: bool = False
    is_piece_start: bool = False
    is_piece_end: bool = False

    @property
    def global_position(self) -> Tuple[int, float]:
        return (self.measure_number, self.offset_in_measure)


@dataclass
class KeyInfo:
    tonic_name: str
    tonic_pc: int
    mode: str
    use_flats: bool
    scale: Tuple[int, ...]
    harmonic_scale: Tuple[int, ...]
    degree_functions: Dict[int, str]
    degree_qualities: Dict[int, str]
    degree_roots: Dict[int, int]
    degree_symbols: Dict[int, str]


@dataclass
class ChordCandidate:
    root_pc: int
    root_name: str
    quality: str
    symbol: str
    pitch_classes: Tuple[int, ...]
    degree: int
    function: str
    color_role: str = "diatonic"
    score: float = 0.0

    def contains_pc(self, pc: int) -> bool:
        return pc % 12 in self.pitch_classes


@dataclass
class SlotPlanExpectation:
    phrase_id: int
    slot_global_idx: int
    expected_functions: List[str] = field(default_factory=list)
    expected_degrees: List[int] = field(default_factory=list)
    weight: float = 0.0
    label: str = "neutral"


@dataclass
class PhrasePlan:
    phrase_id: int
    cadence_kind: str
    cadence_span: int
    cadence_degrees: List[int] = field(default_factory=list)
    slot_expectations: List[SlotPlanExpectation] = field(default_factory=list)


@dataclass
class PieceModel:
    title: str = ""
    measures: List[MeasureInfo] = field(default_factory=list)
    all_notes: List[NoteInfo] = field(default_factory=list)
    key_tonic: str = "C"
    key_tonic_pc: int = 0
    key_mode: str = "major"
    key_info: Optional[KeyInfo] = None
    time_sig: Tuple[int, int] = (4, 4)
    has_pickup: bool = False
    settings: Optional[HarmonizationSettings] = None
    phrases: List[PhraseInfo] = field(default_factory=list)
    harmonic_slots: List[HarmonicSlot] = field(default_factory=list)
    candidate_pool: List[ChordCandidate] = field(default_factory=list)
    phrase_plans: List[PhrasePlan] = field(default_factory=list)
    slot_plan_map: Dict[int, SlotPlanExpectation] = field(default_factory=dict)
    _measure_map: Dict[int, MeasureInfo] = field(default_factory=dict, repr=False)
    _note_index_map: Dict[int, int] = field(default_factory=dict, repr=False)

    @property
    def melody_notes(self) -> List[NoteInfo]:
        return [n for n in self.all_notes if not n.is_rest]

    @property
    def total_measures(self) -> int:
        return len(self.measures)

    @property
    def measure_duration_ql(self) -> float:
        num, den = self.time_sig
        return num * (4.0 / den)

    def measure_by_number(self, mn: int) -> Optional[MeasureInfo]:
        if len(self._measure_map) != len(self.measures):
            self._measure_map = {m.number: m for m in self.measures}
        return self._measure_map.get(mn)

    def note_index_of(self, note: NoteInfo) -> Optional[int]:
        if len(self._note_index_map) != len(self.all_notes):
            self._note_index_map = {id(n): i for i, n in enumerate(self.all_notes)}
        return self._note_index_map.get(id(note))

    def phrase_for_measure(self, mn: int) -> Optional[PhraseInfo]:
        for phrase in self.phrases:
            if phrase.start_measure <= mn <= phrase.end_measure:
                return phrase
        return None

    def phrase_by_id(self, phrase_id: int) -> Optional[PhraseInfo]:
        for phrase in self.phrases:
            if phrase.phrase_id == phrase_id:
                return phrase
        return None

    def prev_pitched_note(self, idx: int) -> Optional[NoteInfo]:
        for i in range(idx - 1, -1, -1):
            if not self.all_notes[i].is_rest:
                return self.all_notes[i]
        return None

    def next_pitched_note(self, idx: int) -> Optional[NoteInfo]:
        for i in range(idx + 1, len(self.all_notes)):
            if not self.all_notes[i].is_rest:
                return self.all_notes[i]
        return None
