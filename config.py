"""Konfiguracja i presety harmonizera.

Ten moduł przechowuje tylko konfigurację działania systemu.
Nie zawiera scoringu ani wiedzy teoretycznej.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, Optional

DEFAULT_PRESET = "auto"

PRESET_ALIASES = {
    "standard": "auto",
    "triad": "classical",
    "rich": "color",
    "crazy": "color",
}


@dataclass
class HarmonizationConfig:
    harmonic_density: str = "auto"
    complexity: str = "triads_v7"
    melody_profile: str = "balanced"
    cadence_profile: str = "balanced"
    color_profile: str = "diatonic"
    variety_profile: str = "balanced"
    cadence_strategy: str = "balanced"
    force_pre_cadence: bool = False
    allow_borrowed_chords: bool = False
    preset_name: str = DEFAULT_PRESET
    key_mode: str = "auto"
    manual_tonic: str = ""
    manual_mode: str = "major"
    generate_voices: bool = False
    add_chord_symbols: bool = True
    export_pdf: bool = True
    export_musicxml: bool = True


PRESETS: Dict[str, HarmonizationConfig] = {
    "auto": HarmonizationConfig(
        preset_name="auto",
        harmonic_density="auto",
        complexity="triads_v7",
        melody_profile="balanced",
        cadence_profile="balanced",
        color_profile="diatonic",
        variety_profile="balanced",
        cadence_strategy="balanced",
    ),
    "classical": HarmonizationConfig(
        preset_name="classical",
        harmonic_density="per_measure",
        complexity="triads_v7",
        melody_profile="strict",
        cadence_profile="strong",
        color_profile="diatonic",
        variety_profile="stable",
        cadence_strategy="strict",
        force_pre_cadence=True,
    ),
    "song": HarmonizationConfig(
        preset_name="song",
        harmonic_density="per_strong_beat",
        complexity="triads_v7",
        melody_profile="balanced",
        cadence_profile="balanced",
        color_profile="classic",
        variety_profile="balanced",
        cadence_strategy="balanced",
    ),
    "color": HarmonizationConfig(
        preset_name="color",
        harmonic_density="auto",
        complexity="triads_v7",
        melody_profile="flexible",
        cadence_profile="light",
        color_profile="rich",
        variety_profile="active",
        cadence_strategy="relaxed",
        allow_borrowed_chords=True,
    ),
}


def resolve_preset_name(name: Optional[str]) -> str:
    if name in PRESET_ALIASES:
        return PRESET_ALIASES[name]
    if name and name in PRESETS:
        return name
    return DEFAULT_PRESET


def clone_preset(name: Optional[str]) -> HarmonizationConfig:
    return deepcopy(PRESETS[resolve_preset_name(name)])
