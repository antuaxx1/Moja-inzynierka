"""Baza wiedzy teoretycznej harmonizera.

Ten moduł zawiera:
- wiedzę o tonacjach,
- logikę wyboru tonacji ręcznej i automatycznej,
- wzorce kadencji,
- generowanie kandydatów akordowych.
"""

from __future__ import annotations

from typing import Dict, List, Tuple

from config import HarmonizationConfig
from models import ChordCandidate, KeyInfo, PieceModel

SHARP_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
FLAT_NAMES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]

NAME_TO_PC: Dict[str, int] = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4, "E#": 5, "F": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11, "B#": 0,
}

FLAT_MAJOR_TONICS = {"F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"}
FLAT_MINOR_TONICS = {"D", "G", "C", "F", "Bb", "Eb", "Ab"}

MAJOR_SCALE = (0, 2, 4, 5, 7, 9, 11)
NATURAL_MINOR = (0, 2, 3, 5, 7, 8, 10)
HARMONIC_MINOR = (0, 2, 3, 5, 7, 8, 11)

MAJOR_TRIAD = (0, 4, 7)
MINOR_TRIAD = (0, 3, 7)
DIMINISHED_TRIAD = (0, 3, 6)
DOMINANT_7TH = (0, 4, 7, 10)

QUALITY_SYMBOL = {
    "major": "",
    "minor": "m",
    "diminished": "dim",
    "dominant7": "7",
}

MAJOR_DEGREE_FUNC = {1: "T", 2: "S", 3: "T", 4: "S", 5: "D", 6: "T", 7: "D"}
MAJOR_DEGREE_QUAL = {1: "major", 2: "minor", 3: "minor", 4: "major", 5: "major", 6: "minor", 7: "diminished"}
MINOR_DEGREE_FUNC = {1: "T", 2: "S", 3: "T", 4: "S", 5: "D", 6: "S", 7: "D"}
MINOR_DEGREE_QUAL = {1: "minor", 2: "diminished", 3: "major", 4: "minor", 5: "major", 6: "major", 7: "diminished"}

KEY_SIG_MAP = {
    0: ("C", "A"), 1: ("G", "E"), 2: ("D", "B"), 3: ("A", "F#"),
    4: ("E", "C#"), 5: ("B", "G#"), 6: ("F#", "D#"), 7: ("C#", "A#"),
    -1: ("F", "D"), -2: ("Bb", "G"), -3: ("Eb", "C"), -4: ("Ab", "F"),
    -5: ("Db", "Bb"), -6: ("Gb", "Eb"), -7: ("Cb", "Ab"),
}

CADENCE_LIBRARY: Dict[str, Dict[str, Dict[int, List[int]]]] = {
    "major": {
        "authentic": {2: [5, 1], 3: [2, 5, 1], 4: [1, 4, 5, 1]},
        "half": {2: [4, 5], 3: [1, 4, 5], 4: [1, 2, 4, 5]},
    },
    "minor": {
        "authentic": {2: [5, 1], 3: [4, 5, 1], 4: [1, 4, 5, 1]},
        "half": {2: [4, 5], 3: [1, 4, 5], 4: [1, 6, 4, 5]},
    },
}


def normalize_tonic_name(name: str) -> str:
    if not name:
        return name
    return name.strip().replace("\u266d", "b").replace("\u266f", "#").replace("-", "b")


def should_use_flats(tonic: str, mode: str = "major") -> bool:
    tonic = normalize_tonic_name(tonic)
    return tonic in (FLAT_MINOR_TONICS if mode == "minor" else FLAT_MAJOR_TONICS)


def pc_name(pc: int, use_flats: bool = False) -> str:
    return (FLAT_NAMES if use_flats else SHARP_NAMES)[pc % 12]


def get_key_options(fifths: int) -> Tuple[str, str]:
    return KEY_SIG_MAP.get(fifths, ("C", "A"))


def build_scale(tonic_pc: int, mode: str) -> Tuple[int, ...]:
    intervals = MAJOR_SCALE if mode == "major" else NATURAL_MINOR
    return tuple((tonic_pc + i) % 12 for i in intervals)


def build_triad(root_pc: int, quality: str) -> Tuple[int, ...]:
    intervals = {"major": MAJOR_TRIAD, "minor": MINOR_TRIAD, "diminished": DIMINISHED_TRIAD}[quality]
    return tuple((root_pc + i) % 12 for i in intervals)


def build_dominant_seventh(root_pc: int) -> Tuple[int, ...]:
    return tuple((root_pc + i) % 12 for i in DOMINANT_7TH)


def build_key_info(tonic_name: str, mode: str) -> KeyInfo:
    tonic_name = normalize_tonic_name(tonic_name)
    tonic_pc = NAME_TO_PC[tonic_name]
    use_flats = should_use_flats(tonic_name, mode)
    scale = build_scale(tonic_pc, mode)
    harmonic_scale = tuple((tonic_pc + i) % 12 for i in HARMONIC_MINOR) if mode == "minor" else scale
    degree_functions = MAJOR_DEGREE_FUNC if mode == "major" else MINOR_DEGREE_FUNC
    degree_qualities = MAJOR_DEGREE_QUAL if mode == "major" else MINOR_DEGREE_QUAL

    degree_roots: Dict[int, int] = {}
    degree_symbols: Dict[int, str] = {}
    for degree in range(1, 8):
        root_pc = scale[degree - 1]
        if mode == "minor" and degree in (5, 7):
            root_pc = harmonic_scale[degree - 1]
        degree_roots[degree] = root_pc
        degree_symbols[degree] = pc_name(root_pc, use_flats) + QUALITY_SYMBOL[degree_qualities[degree]]

    return KeyInfo(
        tonic_name=tonic_name,
        tonic_pc=tonic_pc,
        mode=mode,
        use_flats=use_flats,
        scale=scale,
        harmonic_scale=harmonic_scale,
        degree_functions=dict(degree_functions),
        degree_qualities=dict(degree_qualities),
        degree_roots=degree_roots,
        degree_symbols=degree_symbols,
    )


def _estimate_fifths(piece: PieceModel) -> int:
    if piece.key_tonic and piece.key_mode:
        target = normalize_tonic_name(piece.key_tonic)
        idx = 0 if piece.key_mode == "major" else 1
        for fifths, pair in KEY_SIG_MAP.items():
            if pair[idx] == target:
                return fifths
    return 0


def detect_key(piece: PieceModel) -> KeyInfo:
    melody = piece.melody_notes
    if not melody:
        key_info = build_key_info(piece.key_tonic or "C", piece.key_mode or "major")
        piece.key_info = key_info
        return key_info

    fifths = _estimate_fifths(piece)
    major_name, minor_name = get_key_options(fifths)
    major_pc = NAME_TO_PC.get(major_name, 0)
    minor_pc = NAME_TO_PC.get(minor_name, 9)

    pcs = [n.pitch_class for n in melody]

    # Zbiory skal
    major_scale = set(build_scale(major_pc, "major"))
    minor_nat_scale = set(build_scale(minor_pc, "minor"))
    harmonic_minor_scale = set((minor_pc + i) % 12 for i in HARMONIC_MINOR)

    # Triady toniczne — bardzo ważne do odróżniania relative major/minor
    major_tonic_triad = {major_pc, (major_pc + 4) % 12, (major_pc + 7) % 12}
    minor_tonic_triad = {minor_pc, (minor_pc + 3) % 12, (minor_pc + 7) % 12}

    # Dominanty
    major_dominant = {(major_pc + 7) % 12, (major_pc + 11) % 12, (major_pc + 2) % 12}
    minor_dominant = {(minor_pc + 7) % 12, (minor_pc + 11) % 12, (minor_pc + 2) % 12}

    sc_maj = 0.0
    sc_min = 0.0

    n_notes = len(melody)
    tail_start = max(0, int(n_notes * 0.7))  # końcówka melodii

    def note_weight(note, idx: int) -> float:
        beat = getattr(note, "beat_strength", 0.0) or 0.0
        dur = getattr(note, "duration_ql", 1.0) or 1.0

        # bazowa waga nuty
        w = 1.0 + 0.8 * beat + 0.35 * min(dur, 4.0)

        # końcówka melodii jest ważniejsza
        if idx >= tail_start:
            w *= 1.35

        return w

    # 1. Punktacja ogólna: skala + triady + dominanta
    for idx, note in enumerate(melody):
        pc = note.pitch_class
        w = note_weight(note, idx)

        # Sama skala ma niewielką wagę, bo relative major/minor dzieli materiał dźwiękowy
        if pc in major_scale:
            sc_maj += 0.35 * w
        else:
            sc_maj -= 0.15 * w

        if pc in minor_nat_scale:
            sc_min += 0.30 * w
        else:
            sc_min -= 0.15 * w

        # Podwyższony VII stopień w moll jest bardzo ważny
        if pc in harmonic_minor_scale and pc not in minor_nat_scale:
            sc_min += 1.25 * w

        # Triada toniczna jest kluczowa dla rozróżnienia dur/moll
        if pc in major_tonic_triad:
            sc_maj += 1.10 * w
        if pc in minor_tonic_triad:
            sc_min += 1.10 * w

        # Dominanta też pomaga ustalić centrum tonalne
        if pc in major_dominant:
            sc_maj += 0.40 * w
        if pc in minor_dominant:
            sc_min += 0.55 * w

    # 2. Początek i koniec melodii
    first_pc = pcs[0]
    last_pc = pcs[-1]

    if first_pc == major_pc:
        sc_maj += 4.0
    if first_pc == minor_pc:
        sc_min += 4.0

    if last_pc == major_pc:
        sc_maj += 14.0
    if last_pc == minor_pc:
        sc_min += 14.0

    # Jeśli kończy się na tercji toniki, dajemy małą premię, ale dużo mniejszą niż za prymę
    if last_pc == (major_pc + 4) % 12:
        sc_maj += 2.0
    if last_pc == (minor_pc + 3) % 12:
        sc_min += 2.0

    # 3. Końcówka melodii — dźwięki akordowe toniki są bardzo ważne
    tail = melody[tail_start:]
    for note in tail:
        pc = note.pitch_class
        beat = getattr(note, "beat_strength", 0.0) or 0.0
        tail_w = 1.0 + beat

        if pc in major_tonic_triad:
            sc_maj += 0.90 * tail_w
        if pc in minor_tonic_triad:
            sc_min += 0.90 * tail_w

    # 4. Nuta prowadząca
    major_leading = (major_pc + 11) % 12
    minor_leading = (minor_pc + 11) % 12

    sc_maj += 0.80 * sum(1 for p in pcs if p == major_leading)
    sc_min += 1.40 * sum(1 for p in pcs if p == minor_leading)

    # 5. Bardzo lekka preferencja dla toniki częściej eksponowanej na mocnych/długich nutach
    maj_tonic_presence = 0.0
    min_tonic_presence = 0.0
    for idx, note in enumerate(melody):
        pc = note.pitch_class
        w = note_weight(note, idx)
        if pc == major_pc:
            maj_tonic_presence += w
        if pc == minor_pc:
            min_tonic_presence += w

    sc_maj += 0.20 * maj_tonic_presence
    sc_min += 0.20 * min_tonic_presence

    # Wybór końcowy
    tonic_name, mode = (major_name, "major") if sc_maj >= sc_min else (minor_name, "minor")
    key_info = build_key_info(tonic_name, mode)
    piece.key_tonic = key_info.tonic_name
    piece.key_tonic_pc = key_info.tonic_pc
    piece.key_mode = key_info.mode
    piece.key_info = key_info
    return key_info


def resolve_key(piece: PieceModel, config: HarmonizationConfig) -> KeyInfo:
    if config.key_mode == "manual" and config.manual_tonic:
        key_info = build_key_info(config.manual_tonic, config.manual_mode)
        piece.key_tonic = key_info.tonic_name
        piece.key_tonic_pc = key_info.tonic_pc
        piece.key_mode = key_info.mode
        piece.key_info = key_info
        return key_info
    return detect_key(piece)


def cadence_templates_for(key_info: KeyInfo) -> Dict[str, Dict[int, List[int]]]:
    return CADENCE_LIBRARY[key_info.mode]


def generate_candidate_pool(key_info: KeyInfo, config: HarmonizationConfig) -> List[ChordCandidate]:
    pool: List[ChordCandidate] = []
    for degree in range(1, 8):
        root_pc = key_info.degree_roots[degree]
        root_name = pc_name(root_pc, key_info.use_flats)
        quality = key_info.degree_qualities[degree]
        pool.append(
            ChordCandidate(
                root_pc=root_pc,
                root_name=root_name,
                quality=quality,
                symbol=key_info.degree_symbols[degree],
                pitch_classes=build_triad(root_pc, quality),
                degree=degree,
                function=key_info.degree_functions[degree],
                color_role="diatonic",
            )
        )

    if config.complexity == "triads_v7":
        dominant_root = key_info.degree_roots[5]
        root_name = pc_name(dominant_root, key_info.use_flats)
        pool.append(
            ChordCandidate(
                root_pc=dominant_root,
                root_name=root_name,
                quality="dominant7",
                symbol=root_name + QUALITY_SYMBOL["dominant7"],
                pitch_classes=build_dominant_seventh(dominant_root),
                degree=5,
                function="D",
                color_role="diatonic",
            )
        )

    if config.allow_borrowed_chords or config.color_profile in {"classic", "rich"}:
        pool.extend(_borrowed_candidates(key_info))
    return pool


def _borrowed_candidates(key_info: KeyInfo) -> List[ChordCandidate]:
    borrowed: List[ChordCandidate] = []
    tonic_pc = key_info.tonic_pc
    use_flats = key_info.use_flats
    if key_info.mode == "major":
        borrowed_specs = [(4, (tonic_pc + 5) % 12, "minor", "S"), (7, (tonic_pc + 10) % 12, "major", "D")]
    else:
        borrowed_specs = [(4, (tonic_pc + 5) % 12, "major", "S")]

    for degree, root_pc, quality, function in borrowed_specs:
        root_name = pc_name(root_pc, use_flats)
        borrowed.append(
            ChordCandidate(
                root_pc=root_pc,
                root_name=root_name,
                quality=quality,
                symbol=root_name + QUALITY_SYMBOL[quality],
                pitch_classes=build_triad(root_pc, quality),
                degree=degree,
                function=function,
                color_role="borrowed",
            )
        )
    return borrowed
