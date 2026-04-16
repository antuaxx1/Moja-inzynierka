#!/usr/bin/env python3
"""Główny pipeline harmonizacji melodii z MusicXML."""

from __future__ import annotations

import argparse
import os
import sys
import time

from config import DEFAULT_PRESET, HarmonizationConfig, clone_preset
from exporter import export_harmonized
from harmonizer import harmonize
from models import HarmonizationSettings
from parser import parse_musicxml
from phrases import analyze_phrases_and_slots
from planner import build_phrase_plans
from theory import generate_candidate_pool, resolve_key


def _settings_from_config(config: HarmonizationConfig) -> HarmonizationSettings:
    return HarmonizationSettings(
        preset_name=config.preset_name,
        harmonic_density=config.harmonic_density,
        complexity=config.complexity,
        melody_profile=config.melody_profile,
        cadence_profile=config.cadence_profile,
        color_profile=config.color_profile,
        variety_profile=config.variety_profile,
        cadence_strategy=config.cadence_strategy,
        force_pre_cadence=config.force_pre_cadence,
        allow_borrowed_chords=config.allow_borrowed_chords,
        key_mode=config.key_mode,
        manual_tonic=config.manual_tonic,
        manual_mode=config.manual_mode,
        generate_voices=config.generate_voices,
        add_chord_symbols=config.add_chord_symbols,
        export_pdf=config.export_pdf,
        export_musicxml=config.export_musicxml,
    )


def run_pipeline(input_path: str, config: HarmonizationConfig, output_dir: str = "") -> dict:
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(input_path), "output")

    print("=" * 50)
    print("  HARMONIZER — automatyczna harmonizacja melodii")
    print("=" * 50)

    print("\n[1/6] Parsowanie MusicXML...")
    piece = parse_musicxml(input_path)
    piece.settings = _settings_from_config(config)
    print(f"      {piece.title} | {piece.total_measures} taktów | {piece.time_sig[0]}/{piece.time_sig[1]}")

    print("[2/6] Analiza fraz i slotów...")
    analyze_phrases_and_slots(piece, config)
    print(f"      Frazy: {len(piece.phrases)} | sloty: {len(piece.harmonic_slots)}")

    print("[3/6] Tonacja i baza wiedzy teoretycznej...")
    key_info = resolve_key(piece, config)
    piece.candidate_pool = generate_candidate_pool(key_info, config)
    print(f"      -> {piece.key_tonic} {piece.key_mode} | kandydaci: {len(piece.candidate_pool)}")

    print("[4/6] Planowanie frazowe i kadencyjne...")
    build_phrase_plans(piece, config)
    print(f"      Plany fraz: {len(piece.phrase_plans)}")

    print(f"[5/6] Harmonizacja ({config.harmonic_density})...")
    t0 = time.time()
    harmonize(piece, config)
    print(f"      {len(piece.harmonic_slots)} slotów | {time.time() - t0:.2f}s")

    print("[6/6] Eksport...")
    result = export_harmonized(
        piece=piece,
        original_filepath=input_path,
        output_dir=output_dir,
        add_chord_symbols=config.add_chord_symbols,
        generate_voices=config.generate_voices,
        export_pdf=config.export_pdf,
        export_musicxml=config.export_musicxml,
    )
    if result.get("musicxml"):
        print(f"      MusicXML: {result['musicxml']}")
    if result.get("pdf"):
        print(f"      PDF: {result['pdf']}")
    print("\nGotowe!")

    result["piece"] = piece
    return result


def main():
    p = argparse.ArgumentParser(description="Automatyczna harmonizacja melodii (MusicXML)")
    p.add_argument("input", help="Plik MusicXML (.mxl / .musicxml)")
    p.add_argument(
        "--preset",
        choices=["auto", "classical", "song", "color", "triad", "standard", "rich"],
        default=None,
    )
    p.add_argument(
        "--density",
        choices=["per_measure", "per_strong_beat", "per_beat", "auto"],
        default=None,
    )
    p.add_argument("--voices", action="store_true")
    p.add_argument("--no-pdf", action="store_true")
    p.add_argument("--output-dir", default="")
    args = p.parse_args()

    config = clone_preset(args.preset or DEFAULT_PRESET)
    if args.density:
        config.harmonic_density = args.density
    if args.voices:
        config.generate_voices = True
    if args.no_pdf:
        config.export_pdf = False

    if not os.path.isfile(args.input):
        print(f"Błąd: plik nie istnieje: {args.input}")
        sys.exit(1)

    run_pipeline(args.input, config, args.output_dir)


if __name__ == "__main__":
    main()
