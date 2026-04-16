"""Web UI dla Harmonizera (Flask).

Ten plik jest warstwą prezentacji projektu.

To NIE jest główny silnik harmonizacji.
Silnik jest w modułach parser/theory/phrases/planner/rules/harmonizer/exporter.

Tutaj dzieją się rzeczy "użytkowe":
- przyjęcie pliku od użytkownika,
- pokazanie kontrolek i presetów,
- zbudowanie konfiguracji,
- uruchomienie pipeline'u,
- przygotowanie danych do podglądu w HTML.
"""

import io
import time
from contextlib import redirect_stdout
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)

from config import (
    DEFAULT_PRESET,
    PRESETS,
    HarmonizationConfig,
    clone_preset,
    resolve_preset_name,
)
from main import run_pipeline


# ═══════════════════════════════════════════════════════════════════════════
# UI CONFIG — metadane presetów i kontrolek
# ═══════════════════════════════════════════════════════════════════════════

# Te słowniki nie wykonują logiki algorytmu.
# One tylko opisują, jak pokazać użytkownikowi opcje w interfejsie.
PRESET_INFO = {
    "auto": {"name": "Auto", "description": "Adaptacyjny styl (rekomendowany)"},
    "classical": {"name": "Klasyczny", "description": "Tradycyjna harmonizacja"},
    "song": {"name": "Piosenka", "description": "Popularna muzyka"},
    "color": {"name": "Kolorowo", "description": "Bogata harmonizacja z chromatyką"},
}


CORE_CONTROL_INFO = {
    "harmonic_rhythm": {
        "label": "Rytm harmoniczny",
        "hint": "Jak gęsto umieszczać decyzje akordowe.",
        "options": [
            {"label": "Jeden akord/takt", "value": "per_measure", "description": "Standardowy szablon"},
            {"label": "Mocne beaty", "value": "per_strong_beat", "description": "Na silnych pozycjach"},
            {"label": "Każdy beat", "value": "per_beat", "description": "Maksimum szczegółu"},
            {"label": "Adaptacyjny", "value": "auto", "description": "Inteligentnie wybrany"},
        ],
    },
    "melody_priority": {
        "label": "Priorytet melodii",
        "hint": "Jak ściśle harmonizacja musi obsługiwać noty melodii.",
        "options": [
            {"label": "Ścisły", "value": "strict", "description": "Mocna ochrona nuty melodii"},
            {"label": "Równoważony", "value": "balanced", "description": "Dobra równowaga"},
            {"label": "Elastyczny", "value": "flexible", "description": "Więcej swobody"},
        ],
    },
}


EXPERT_CONTROL_INFO = {
    "harmonic_color": {
        "label": "Kolor harmoniczny",
        "hint": "Ile pożyczonych akordów z innych tonacji.",
        "options": [
            {"label": "Diatoniczny", "value": "diatonic", "description": "Tylko z tonacji"},
            {"label": "Klasyczny", "value": "classic", "description": "Miękko pożyczane"},
            {"label": "Bogaty", "value": "rich", "description": "Wiele kolorów"},
        ],
    },
    "cadence_pull": {
        "label": "Siła kadencji",
        "hint": "Jak silnie wrażliwe kadencje (V-I, V-vi itd.).",
        "options": [
            {"label": "Lekka", "value": "light"},
            {"label": "Równoważona", "value": "balanced"},
            {"label": "Silna", "value": "strong"},
        ],
    },
    "voice_motion": {
        "label": "Ruch głosów",
        "hint": "Preferencja dla zmienności/stabilności harmonii.",
        "options": [
            {"label": "Stabilna", "value": "stable"},
            {"label": "Równoważona", "value": "balanced"},
            {"label": "Aktywna", "value": "active"},
        ],
    },
    "adv_complexity": {
        "label": "Złożoność harmonii",
        "hint": "Czy dodawać akord dominanty V7 poza kadencjami?",
        "options": [
            {"label": "Triady", "value": "triads"},
            {"label": "Triady + V7", "value": "triads_v7"},
        ],
    },
}


KEY_CONTROL_INFO = {
    "key_mode": {
        "label": "Tonacja",
        "hint": "Możesz pozostawić automatyczne rozpoznanie albo wybrać tonację ręcznie.",
        "options": [
            {"label": "Nie wiem (auto-detect)", "value": "auto"},
            {"label": "Wybiorę ręcznie", "value": "manual"},
        ],
    },
    "manual_mode": {
        "label": "Tryb",
        "hint": "Dotyczy tylko ręcznego wyboru tonacji.",
        "options": [
            {"label": "Dur", "value": "major"},
            {"label": "Moll", "value": "minor"},
        ],
    },
}


# Lista pól formularza, które mapujemy na konfigurację silnika.
FORM_CONTROL_FIELDS = [
    "harmonic_rhythm",
    "melody_priority",
    "harmonic_color",
    "cadence_pull",
    "voice_motion",
    "adv_complexity",
]


def _form_defaults_from_preset(cfg: HarmonizationConfig) -> dict:
    """Zamienia preset silnika na domyślne wartości dla formularza."""
    return {
        "harmonic_rhythm": cfg.harmonic_density,
        "melody_priority": cfg.melody_profile,
        "harmonic_color": cfg.color_profile,
        "cadence_pull": cfg.cadence_profile,
        "voice_motion": cfg.variety_profile,
        "adv_complexity": cfg.complexity,
        "key_mode": getattr(cfg, "key_mode", "auto"),
        "manual_tonic": getattr(cfg, "manual_tonic", ""),
        "manual_mode": getattr(cfg, "manual_mode", "major"),
    }


# Dzięki temu możemy szybko odtworzyć stan formularza po wybraniu presetu.
PRESET_FORM_DEFAULTS = {name: _form_defaults_from_preset(p) for name, p in PRESETS.items()}


def get_option_label(field_name: str, value: str) -> str:
    """Zwraca czytelną etykietę dla danej wartości formularza."""
    info = (
        CORE_CONTROL_INFO.get(field_name)
        or EXPERT_CONTROL_INFO.get(field_name)
        or KEY_CONTROL_INFO.get(field_name)
        or {}
    )
    for opt in info.get("options", []):
        if opt.get("value") == value:
            return opt.get("label", value)
    return value


def apply_form_controls(config: HarmonizationConfig, form_state: dict) -> None:
    """Przenosi stan formularza do obiektu konfiguracji silnika."""
    config.harmonic_density = form_state.get("harmonic_rhythm", config.harmonic_density)
    config.melody_profile = form_state.get("melody_priority", config.melody_profile)
    config.color_profile = form_state.get("harmonic_color", config.color_profile)
    config.cadence_profile = form_state.get("cadence_pull", config.cadence_profile)
    config.variety_profile = form_state.get("voice_motion", config.variety_profile)
    config.complexity = form_state.get("adv_complexity", config.complexity)

    # Obsługa tonacji z UI.
    config.key_mode = form_state.get("key_mode", getattr(config, "key_mode", "auto"))
    config.manual_tonic = form_state.get("manual_tonic", getattr(config, "manual_tonic", "")).strip()
    config.manual_mode = form_state.get("manual_mode", getattr(config, "manual_mode", "major"))

    if config.key_mode != "manual":
        config.manual_tonic = ""
        config.manual_mode = "major"


def get_preset_form_defaults(preset_name: str) -> dict:
    """Zwraca stan formularza odpowiadający danemu presetowi."""
    return PRESET_FORM_DEFAULTS.get(resolve_preset_name(preset_name), {})


# ═══════════════════════════════════════════════════════════════════════════
# FLASK APP
# ═══════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)
app.secret_key = "harmonizer-dev-key-2026"


# Bazowe wartości formularza, gdy użytkownik dopiero otwiera stronę.
BASE_FORM_DEFAULTS = {
    "preset": DEFAULT_PRESET,
    "voices": False,
    "chords": True,
    "pdf": True,
    "existing_upload": "",
    "current_filename": "",
    "has_server_state": False,
    "key_mode": "auto",
    "manual_tonic": "",
    "manual_mode": "major",
}


def _build_form_state(form=None, *, existing_upload="", current_filename="",
                      has_server_state=False):
    """Buduje pełny stan formularza do renderowania w HTML.

    To jest wygodne, bo:
    - możemy łatwo odtwarzać wybory użytkownika po POST,
    - możemy łączyć wartości z presetu i z aktualnego formularza,
    - template dostaje już gotowy, spójny obiekt stanu.
    """
    preset_name = resolve_preset_name(form.get("preset") if form is not None else None)
    state = {**BASE_FORM_DEFAULTS, **get_preset_form_defaults(preset_name)}
    state["preset"] = preset_name

    if form is not None:
        for key in FORM_CONTROL_FIELDS:
            v = form.get(key)
            if v is not None:
                state[key] = v

        for key in ("key_mode", "manual_tonic", "manual_mode"):
            v = form.get(key)
            if v is not None:
                state[key] = v

        for key in ("voices", "chords", "pdf"):
            state[key] = bool(form.get(key))

        state["existing_upload"] = Path(form.get("existing_upload", "")).name
        state["current_filename"] = form.get("current_filename", "")

    if existing_upload:
        state["existing_upload"] = Path(existing_upload).name
    if current_filename:
        state["current_filename"] = current_filename

    state["has_server_state"] = has_server_state
    return state


def _resolve_input_file():
    """Rozstrzyga, z jakiego pliku mamy uruchomić harmonizację.

    Mamy dwa warianty:
    - użytkownik wrzucił nowy plik,
    - użytkownik chce użyć już wcześniej wgranego pliku.
    """
    f = request.files.get("musicxml")
    if f and f.filename:
        ts = time.strftime("%Y%m%d-%H%M%S")
        safe = f.filename.replace(" ", "_")
        path = UPLOAD_DIR / f"{ts}_{safe}"
        f.save(path)
        return path, safe, path.name

    eu = Path(request.form.get("existing_upload", "")).name
    if eu:
        path = UPLOAD_DIR / eu
        if path.exists():
            return path, request.form.get("current_filename", "") or eu, eu

    return None, "", ""


def _extract_piece_data(piece):
    """Wyciąga z `PieceModel` uproszczone dane do pokazania w UI.

    Template HTML nie powinien znać całej logiki klas domenowych.
    Dlatego tutaj budujemy prosty słownik gotowy do renderowania.
    """
    if piece is None:
        return None

    data = {
        "title": getattr(piece, "title", "Untitled"),
        "key": f"{piece.key_tonic} {piece.key_mode}",
        "time_sig": (
            f"{piece.measures[0].time_sig_numerator}/{piece.measures[0].time_sig_denominator}"
            if piece.measures else "?"
        ),
        "n_measures": len(piece.measures),
        "has_pickup": getattr(piece, "has_pickup", False),
        "phrases": [],
        "chords": [],
        "chord_summary": {},
        "chord_duration_summary": {},
    }

    # Frazy do tabeli / podsumowania.
    for i, ph in enumerate(getattr(piece, "phrases", [])):
        data["phrases"].append({
            "index": i + 1,
            "start": ph.start_measure,
            "end": ph.end_measure,
            "shape": getattr(ph, "shape", "unknown"),
        })

    # Akordy wybrane przez harmonizer.
    for slot in getattr(piece, "harmonic_slots", []):
        ch = slot.chosen_chord
        if ch is None:
            continue
        sym = ch.symbol
        entry = {
            "measure": slot.measure_number,
            "offset": slot.offset_in_measure,
            "duration": slot.duration_ql,
            "symbol": sym,
            "degree": ch.degree,
            "function": ch.function,
            "score": round(ch.score, 2),
            "flags": [],
        }
        if slot.is_phrase_end:
            entry["flags"].append("phrase_end")
        if slot.is_piece_end:
            entry["flags"].append("piece_end")
        data["chords"].append(entry)
        data["chord_summary"][sym] = data["chord_summary"].get(sym, 0) + 1
        data["chord_duration_summary"][sym] = round(
            data["chord_duration_summary"].get(sym, 0.0) + slot.duration_ql,
            2,
        )

    # Statystyki rytmu harmonicznego.
    slots = getattr(piece, "harmonic_slots", [])
    if slots:
        from collections import Counter

        bars = Counter(s.measure_number for s in slots)
        bd = Counter(bars.values())
        data["rhythm_stats"] = {
            "total_slots": len(slots),
            "n_measures": len(bars),
            "avg_per_bar": round(len(slots) / max(len(bars), 1), 2),
            "bar_distribution": dict(sorted(bd.items())),
        }
    else:
        data["rhythm_stats"] = None

    return data


def _tpl_ctx(**extra):
    """Buduje wspólny kontekst przekazywany do template'u."""
    return dict(
        core_control_info=CORE_CONTROL_INFO,
        expert_control_info=EXPERT_CONTROL_INFO,
        key_control_info=KEY_CONTROL_INFO,
        preset_info=PRESET_INFO,
        preset_form_defaults=PRESET_FORM_DEFAULTS,
        **extra,
    )


@app.route("/", methods=["GET", "POST"])
def index():
    """Główny widok aplikacji.

    GET:
    - pokazuje pusty formularz.

    POST:
    - pobiera plik i parametry,
    - buduje konfigurację,
    - uruchamia pipeline,
    - renderuje wynik.
    """
    if request.method == "POST":
        upload_path, current_filename, existing_upload = _resolve_input_file()
        form_state = _build_form_state(
            request.form,
            existing_upload=existing_upload,
            current_filename=current_filename,
            has_server_state=True,
        )

        if upload_path is None:
            flash("Wybierz plik albo użyj już wgranego utworu.", "error")
            return render_template("index.html", **_tpl_ctx(form_state=form_state))

        # Budujemy konfigurację od presetu, a potem nadpisujemy ją formularzem.
        preset_name = resolve_preset_name(form_state["preset"])
        config = clone_preset(preset_name)
        config.generate_voices = form_state["voices"]
        config.add_chord_symbols = form_state["chords"]
        config.export_pdf = form_state["pdf"]
        apply_form_controls(config, form_state)

        # Zbieramy tekstowy log pipeline'u, żeby można było go pokazać w UI.
        log_buf = io.StringIO()
        try:
            with redirect_stdout(log_buf):
                result = run_pipeline(str(upload_path), config, output_dir=str(OUTPUT_DIR))
            log_text = log_buf.getvalue()
        except Exception as ex:
            log_text = log_buf.getvalue()
            flash(f"Błąd: {ex}", "error")
            return render_template(
                "index.html",
                log_text=log_text,
                **_tpl_ctx(form_state=form_state),
            )

        # Przygotowujemy dane pomocnicze do prezentacji w HTML.
        piece_data = _extract_piece_data(result.get("piece"))

        if config.key_mode == "manual" and config.manual_tonic:
            key_choice = f"{config.manual_tonic} {'dur' if config.manual_mode == 'major' else 'moll'}"
        else:
            key_choice = "Nie wiem (auto-detect)"

        config_used = {
            "preset": PRESET_INFO[preset_name]["name"],
            "voices": config.generate_voices,
            "harmonic_rhythm": get_option_label("harmonic_rhythm", form_state["harmonic_rhythm"]),
            "melody_priority": get_option_label("melody_priority", form_state["melody_priority"]),
            "harmonic_color": get_option_label("harmonic_color", form_state["harmonic_color"]),
            "cadence_pull": get_option_label("cadence_pull", form_state["cadence_pull"]),
            "voice_motion": get_option_label("voice_motion", form_state["voice_motion"]),
            "complexity": get_option_label("adv_complexity", form_state["adv_complexity"]),
            "key_choice": key_choice,
        }

        return render_template(
            "index.html",
            result=result,
            log_text=log_text,
            piece_data=piece_data,
            config_used=config_used,
            **_tpl_ctx(form_state=form_state),
        )

    return render_template("index.html", **_tpl_ctx(form_state=_build_form_state()))


@app.route("/preview/<filename>")
def preview(filename):
    """Serwuje plik do podglądu w przeglądarce."""
    fp = OUTPUT_DIR / Path(filename).name
    if fp.exists():
        return send_from_directory(fp.parent, fp.name)
    flash("Plik nie znaleziony.", "error")
    return redirect(url_for("index"))


@app.route("/download/<path:filename>")
def download(filename):
    """Serwuje plik do pobrania jako załącznik."""
    fp = OUTPUT_DIR / Path(filename).name
    if fp.exists():
        return send_from_directory(OUTPUT_DIR, fp.name, as_attachment=True)
    flash("Plik nie znaleziony.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Tryb produkcyjny/debug minimalny — aplikacja ma być prostym demo projektu.
    app.run(debug=False, port=4500)