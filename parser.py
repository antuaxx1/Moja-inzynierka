"""Parser MusicXML.

Ten moduł robi pierwszy, absolutnie podstawowy etap całego projektu:
zamienia plik MusicXML na naszą własną, prostszą reprezentację danych.

Najważniejsza idea:
- wejściem jest plik `.mxl/.musicxml/.xml`,
- `music21` wczytuje partyturę,
- my wyciągamy z niej tylko te informacje, które są naprawdę potrzebne
  dalszym etapom harmonizacji,
- wynik zapisujemy do `PieceModel`.

Dlaczego to jest ważne?
Bo dalsza część projektu nie operuje bezpośrednio na dużych obiektach `music21`,
tylko na własnych, prostych strukturach danych z `models.py`.
"""

import os
from pathlib import Path

from music21 import converter, meter, key as m21key, note as m21note, stream

from models import MeasureInfo, NoteInfo, PieceModel, get_accent_weight
from theory import NAME_TO_PC, get_key_options, normalize_tonic_name


class ParsingError(Exception):
    """Własny wyjątek parsera.

    Dzięki temu wyżej w pipeline możemy łatwo odróżnić:
    - błąd pliku wejściowego,
    - błąd parsowania,
    - brak wymaganych danych w partyturze.
    """


def parse_musicxml(filepath: str) -> PieceModel:
    """Wczytuje plik MusicXML i buduje `PieceModel`.

    W skrócie dzieje się tu pięć rzeczy:
    1. walidacja ścieżki i rozszerzenia,
    2. parsowanie pliku przez `music21`,
    3. odczyt metrum i tonacji zapisanej w pliku,
    4. przejście takt po takcie i nuta po nucie,
    5. zbudowanie naszej wewnętrznej reprezentacji utworu.
    """
    # Najpierw sprawdzamy, czy użytkownik faktycznie podał istniejący plik.
    if not filepath or not os.path.isfile(filepath):
        raise ParsingError(f"Plik nie istnieje: {filepath}")

    # Dopuszczamy tylko formaty, które ten projekt realnie obsługuje.
    ext = Path(filepath).suffix.lower()
    if ext not in (".mxl", ".musicxml", ".xml"):
        raise ParsingError(f"Nieznane rozszerzenie: {ext}")

    # `music21` robi ciężką pracę parsowania składni MusicXML.
    try:
        score = converter.parse(filepath)
    except Exception as e:
        raise ParsingError(f"Nie można sparsować pliku: {e}")

    # Tworzymy pusty kontener na cały utwór.
    piece = PieceModel()

    # Tytuł próbujemy odczytać z metadanych; jeśli go nie ma,
    # używamy nazwy pliku.
    piece.title = (
        score.metadata.title if score.metadata and score.metadata.title
        else Path(filepath).stem
    )

    # Projekt zakłada melodię jednogłosową, więc bierzemy pierwszą partię.
    parts = score.parts
    if not parts:
        raise ParsingError("Plik nie zawiera żadnych partii")
    melody_part = parts[0]

    # =========================
    # 1. Odczyt metrum
    # =========================
    # Jeśli plik zawiera jawne metrum, zapisujemy je jako bazowe metrum utworu.
    # Jeśli nie, przyjmujemy bezpieczne domyślne 4/4.
    ts_list = melody_part.recurse().getElementsByClass(meter.TimeSignature)
    if ts_list:
        piece.time_sig = (ts_list[0].numerator, ts_list[0].denominator)
    else:
        piece.time_sig = (4, 4)

    # =========================
    # 2. Odczyt tonacji z pliku
    # =========================
    # Najpierw próbujemy znaleźć pełny obiekt `Key`.
    # Jeśli go nie ma, spadamy do `KeySignature`.
    # To jeszcze nie jest ostateczna analiza tonalna — później
    # `tonality.detect_key()` może skorygować tryb dur/moll.
    key_objs = melody_part.recurse().getElementsByClass(m21key.Key)
    if key_objs:
        k = key_objs[0]
        piece.key_tonic = normalize_tonic_name(k.tonic.name)
        piece.key_tonic_pc = k.tonic.pitchClass
        piece.key_mode = k.mode if k.mode in ("major", "minor") else "major"
    else:
        ks = melody_part.recurse().getElementsByClass(m21key.KeySignature)
        fifths = ks[0].sharps if ks else 0
        major_name, _ = get_key_options(fifths)
        piece.key_tonic = major_name
        piece.key_tonic_pc = NAME_TO_PC.get(major_name, 0)
        piece.key_mode = "major"

    # =========================
    # 3. Przetwarzanie taktów
    # =========================
    # Z punktu widzenia projektu takt jest podstawową jednostką organizacyjną.
    measures_stream = melody_part.getElementsByClass(stream.Measure)
    if not measures_stream:
        raise ParsingError("Brak taktów w partii")

    # `expected_ql` = ile ćwierćnut powinien mieć takt według metrum.
    # To później przyda się np. do rozpoznania przedtaktu.
    expected_ql = piece.time_sig[0] * (4.0 / piece.time_sig[1])

    # `global_offset` to pozycja czasu liczona przez cały utwór,
    # a nie tylko w obrębie taktu.
    global_offset = 0.0

    # `cur_num/cur_den` śledzą aktualne metrum, bo w utworze
    # mogą pojawiać się zmiany sygnatury taktowej.
    cur_num, cur_den = piece.time_sig

    for m in measures_stream:
        m_number = m.number if m.number is not None else 0

        # Jeśli wewnątrz utworu pojawia się nowe metrum,
        # od tego taktu używamy już nowych wartości.
        local_ts = m.getElementsByClass(meter.TimeSignature)
        if local_ts:
            cur_num, cur_den = local_ts[0].numerator, local_ts[0].denominator
            expected_ql = cur_num * (4.0 / cur_den)

        # Tworzymy nasz własny opis taktu.
        mi = MeasureInfo(
            number=m_number,
            time_sig_numerator=cur_num,
            time_sig_denominator=cur_den,
            expected_duration_ql=expected_ql,
        )
        total_dur = 0.0

        # `notesAndRests` daje i nuty, i pauzy — i to jest dobre,
        # bo pauzy też są ważne np. dla detekcji fraz.
        for el in m.notesAndRests:
            try:
                dur_ql = float(el.quarterLength)
                off = float(el.offset)
            except (AttributeError, ValueError):
                # Jeśli element nie ma sensownych danych rytmicznych, pomijamy go.
                continue

            # Tu liczymy siłę metryczną pozycji nuty/pauzy.
            # To potem jest bardzo ważne dla scoringu harmonii.
            beat_str = get_accent_weight(off, cur_num, cur_den)

            # Rozróżniamy trzy przypadki:
            # - pauza,
            # - zwykła nuta,
            # - obiekt złożony (np. akord), z którego bierzemy najwyższy dźwięk.
            if isinstance(el, m21note.Rest):
                pname, midi, pc, is_rest, tied = "rest", 0, -1, True, False
            elif isinstance(el, m21note.Note):
                pname = el.nameWithOctave
                midi, pc = el.pitch.midi, el.pitch.pitchClass
                is_rest = False
                tied = bool(el.tie and el.tie.type in ("start", "continue"))
            else:
                try:
                    # W projekcie melodycznym, jeśli trafimy na obiekt wielodźwiękowy,
                    # traktujemy jego najwyższy składnik jako "głos melodyczny".
                    top = max(el.pitches, key=lambda p: p.midi)
                    pname, midi, pc = top.nameWithOctave, top.midi, top.pitchClass
                    is_rest, tied = False, False
                except (AttributeError, ValueError):
                    continue

            # Tworzymy rekord pojedynczego zdarzenia muzycznego.
            ni = NoteInfo(
                pitch_name=pname,
                midi_number=midi,
                pitch_class=pc,
                duration_ql=dur_ql,
                offset_in_measure=off,
                measure_number=m_number,
                is_rest=is_rest,
                is_tied_forward=tied,
                beat_strength=beat_str,
                global_offset=global_offset + off,
            )

            # Każdą nutę/pauzę zapisujemy jednocześnie:
            # - w obrębie taktu,
            # - oraz w globalnej liście nut utworu.
            mi.notes.append(ni)
            piece.all_notes.append(ni)

            # `total_dur` śledzi rzeczywistą długość zawartości taktu.
            total_dur = max(total_dur, off + dur_ql)

        # `actual_duration_ql` to rzeczywista długość taktu odczytana z partytury.
        mi.total_duration_ql = total_dur
        mi.actual_duration_ql = float(m.duration.quarterLength or total_dur or expected_ql)
        piece.measures.append(mi)

        # Po zakończeniu taktu przesuwamy globalny zegar dalej.
        global_offset += mi.actual_duration_ql

    if not piece.measures or not piece.all_notes:
        raise ParsingError("Plik nie zawiera nut")

    # =========================
    # 4. Detekcja przedtaktu
    # =========================
    # Jeśli pierwszy takt jest wyraźnie krótszy niż "powinien",
    # traktujemy go jako pickup / przedtakt.
    first = piece.measures[0]
    exp = float(first.expected_duration_ql or 0)
    if exp > 0 and float(first.actual_duration_ql) < exp * 0.9:
        first.is_pickup = True
        piece.has_pickup = True

    return piece
