"""Eksport zharmonizowanego utworu do MusicXML i PDF.

To jest ostatni etap pipeline'u.

Tu bierzemy:
- oryginalną partyturę,
- wynik harmonizacji zapisany w `PieceModel`,

i zamieniamy to na:
- plik MusicXML z dopisanymi symbolami akordowymi,
- opcjonalnie PDF,
- opcjonalnie dodatkowe głosy.

Ważne:
ten moduł nie "wymyśla" harmonii od nowa.
On tylko przekłada wynik algorytmu na notację muzyczną.
"""

import copy
import os
from typing import List, Optional

from music21 import (
    converter,
    expressions,
    harmony as m21harmony,
    instrument,
    meter,
    note as m21note,
    pitch as m21pitch,
    stream,
    clef,
    key as m21key,
)

from models import ChordCandidate, HarmonicSlot, PieceModel


def export_harmonized(piece: PieceModel, original_filepath: str, output_dir: str,
                      add_chord_symbols: bool = True, generate_voices: bool = False,
                      export_pdf: bool = True, export_musicxml: bool = True) -> dict:
    """Eksportuje wynik harmonizacji do plików wyjściowych.

    Parametry sterują:
    - czy dopisywać symbole akordowe,
    - czy generować dodatkowe głosy,
    - czy zapisywać MusicXML,
    - czy próbować wygenerować PDF.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Wczytujemy oryginalny zapis jeszcze raz, bo to na nim osadzamy wynik.
    score = converter.parse(original_filepath)
    melody_part = score.parts[0]

    # 1. Dopisanie symboli akordowych nad melodią.
    if add_chord_symbols:
        _add_symbols(melody_part, piece)

    # 2. Opcjonalne dorobienie dwóch dodatkowych głosów.
    if generate_voices:
        for vp in _gen_voices(piece, score):
            score.insert(0, vp)

    base = (piece.title.replace(" ", "_").replace("/", "_") or "harmonized")
    xml_path = os.path.join(output_dir, f"{base}_harmonized.musicxml")
    result = {"musicxml": None, "pdf": None}

    # 3. Zapis MusicXML — podstawowy i najważniejszy format wyjścia.
    if export_musicxml:
        score.write("musicxml", fp=xml_path)
        result["musicxml"] = xml_path

    # 4. Zapis PDF — opcjonalny i zależny od dostępnych narzędzi zewnętrznych.
    if export_pdf:
        pdf_score = _prepare_pdf(score)
        pdf_stem = os.path.join(output_dir, f"{base}_harmonized")
        pdf_path = pdf_stem + ".pdf"
        try:
            pdf_score.write("lily.pdf", fp=pdf_stem)
            if os.path.isfile(pdf_path):
                result["pdf"] = pdf_path
            elif os.path.isfile(pdf_stem + ".pdf.pdf"):
                os.rename(pdf_stem + ".pdf.pdf", pdf_path)
                result["pdf"] = pdf_path
        except Exception:
            # Awaryjna próba przez alternatywny backend.
            try:
                score.write("musicxml.pdf", fp=pdf_path)
                result["pdf"] = pdf_path
            except Exception:
                print("  [INFO] Nie udało się wygenerować PDF (wymaga MuseScore/LilyPond)")
    return result


def _add_symbols(melody_part, piece):
    """Dopisuje symbole akordowe nad melodią.

    Dla każdego slotu bierzemy wybrany akord i próbujemy zapisać go jako:
    - `ChordSymbol` z `music21`,
    - a jeśli to się nie uda, jako zwykły tekst nad pięciolinią.
    """
    slots_by_m = {}
    for s in piece.harmonic_slots:
        if s.chosen_chord:
            slots_by_m.setdefault(s.measure_number, []).append(s)

    for m in melody_part.getElementsByClass(stream.Measure):
        mn = m.number if m.number is not None else 0
        if mn not in slots_by_m:
            continue
        mql = float(m.duration.quarterLength or 0.0)
        for slot in slots_by_m[mn]:
            ch = slot.chosen_chord
            if ch is None or (mql and slot.offset_in_measure > mql - 0.0001):
                continue
            try:
                kind_map = {
                    "major": "major",
                    "minor": "minor",
                    "diminished": "diminished",
                    "dominant7": "dominant-seventh",
                }
                kind = kind_map[ch.quality]
                kind_str = ch.symbol[len(ch.root_name):] if ch.symbol.startswith(ch.root_name) else ""
                cs = m21harmony.ChordSymbol(root=ch.root_name, kind=kind, kindStr=kind_str)
                cs.harmonizer_symbol = ch.symbol
                m.insert(slot.offset_in_measure, cs)
            except Exception:
                # Fallback: zwykły napis nad pięciolinią.
                try:
                    te = expressions.TextExpression(ch.symbol)
                    te.placement = "above"
                    m.insert(slot.offset_in_measure, te)
                except Exception:
                    pass


def _prepare_pdf(score):
    """Przygotowuje wersję partytury wygodniejszą do eksportu PDF.

    Część backendów gorzej radzi sobie z `ChordSymbol`,
    więc zamieniamy je na prostsze `TextExpression`.
    """
    s = copy.deepcopy(score)
    for part in s.parts:
        for m in part.getElementsByClass(stream.Measure):
            cs_list = list(m.getElementsByClass(m21harmony.ChordSymbol))
            for cs in cs_list:
                te = expressions.TextExpression(getattr(cs, "harmonizer_symbol", cs.figure))
                te.offset = cs.offset
                te.placement = "above"
                m.remove(cs)
                m.insert(te.offset, te)
    return s


def _gen_voices(piece, original_score) -> List[stream.Part]:
    """Generuje dwie uproszczone linie akompaniujące pod melodią.

    To nie jest pełny system voice leadingu.
    To jest demonstracyjna, czytelna realizacja dwóch dodatkowych głosów.
    """
    mid_part = stream.Part()
    mid_part.partName = "Harmony (middle)"
    mid_part.insert(0, instrument.Piano())

    low_part = stream.Part()
    low_part.partName = "Harmony (lower)"
    low_part.insert(0, instrument.Piano())

    if piece.time_sig:
        mid_part.insert(0, meter.TimeSignature(f"{piece.time_sig[0]}/{piece.time_sig[1]}"))
        low_part.insert(0, meter.TimeSignature(f"{piece.time_sig[0]}/{piece.time_sig[1]}"))

    slots_by_m = {}
    for s in piece.harmonic_slots:
        slots_by_m.setdefault(s.measure_number, []).append(s)

    for orig_m in original_score.parts[0].getElementsByClass(stream.Measure):
        mn = orig_m.number if orig_m.number is not None else 0
        mql = float(orig_m.duration.quarterLength or piece.measure_duration_ql)
        mm = stream.Measure(number=mn)
        lm = stream.Measure(number=mn)

        # Jeśli w takcie nie ma harmonii, oba głosy milczą.
        if mn not in slots_by_m:
            mm.append(m21note.Rest(quarterLength=mql))
            lm.append(m21note.Rest(quarterLength=mql))
        else:
            for slot in slots_by_m[mn]:
                ch = slot.chosen_chord
                if slot.offset_in_measure > mql - 0.0001:
                    continue
                if ch is None:
                    mm.append(m21note.Rest(quarterLength=slot.duration_ql))
                    lm.append(m21note.Rest(quarterLength=slot.duration_ql))
                    continue

                # Szukamy najwyższej nuty melodycznej w slocie.
                mel_midi = max(
                    (n.midi_number for n in slot.melody_notes if not n.is_rest),
                    default=None,
                )
                if mel_midi is None:
                    mm.append(m21note.Rest(quarterLength=slot.duration_ql))
                    lm.append(m21note.Rest(quarterLength=slot.duration_ql))
                    continue

                # Dobieramy dwa składniki akordu poniżej melodii.
                mp, lp = _voices_below(ch, mel_midi)
                mn_note = m21note.Note(midi=mp, quarterLength=slot.duration_ql)
                ln_note = m21note.Note(midi=lp, quarterLength=slot.duration_ql)
                mm.insert(slot.offset_in_measure, mn_note)
                lm.insert(slot.offset_in_measure, ln_note)

        mid_part.append(mm)
        low_part.append(lm)
    return [mid_part, low_part]


def _voices_below(chord, mel_midi):
    """Dobiera dwa dźwięki akordu poniżej melodii.

    To bardzo prosty algorytm:
    - bierzemy składniki trójdźwięku,
    - szukamy ich możliwie blisko pod melodią,
    - wybieramy dwa najwyższe sensowne warianty.
    """
    pcs = list(chord.pitch_classes[:3])
    cands = []
    for pc in pcs:
        for midi in range(mel_midi - 1, mel_midi - 25, -1):
            if midi % 12 == pc and midi > 0:
                cands.append(midi)
                break
    cands = sorted([c for c in cands if c < mel_midi], reverse=True)
    if len(cands) >= 2:
        return cands[0], cands[1]
    if len(cands) == 1:
        return cands[0], cands[0] - 12
    return mel_midi - 4, mel_midi - 7
