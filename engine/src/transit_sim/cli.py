"""Interface en ligne de commande de transit_sim.

Exemple (depuis engine/) :
    uv run python -m transit_sim.cli build-network --gtfs ../data/raw/twisto --date 2026-10-06
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from transit_sim.export.network_geojson import write_network_geojson
from transit_sim.gtfs.loader import filter_by_date, load_gtfs
from transit_sim.gtfs.validation import format_report, validation_report

WEEKDAYS_FR = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
TUESDAY = 1


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"date invalide (attendu AAAA-MM-JJ) : {value}") from exc


def build_network(args: argparse.Namespace) -> int:
    weekday = WEEKDAYS_FR[args.date.weekday()]
    print(f"Date de référence : {args.date.isoformat()} ({weekday})")
    if args.date.weekday() != TUESDAY:
        print(
            f"Erreur : la date de référence doit être un mardi, pas un {weekday}.", file=sys.stderr
        )
        return 2
    print("Vérification : c'est bien un mardi.")

    print(f"Chargement du GTFS : {args.gtfs.resolve()}")
    gtfs = filter_by_date(load_gtfs(args.gtfs), args.date)
    print()
    print(format_report(validation_report(gtfs)))
    print()

    warnings = write_network_geojson(gtfs, args.output)
    for warning in warnings:
        print(f"Avertissement export : {warning}")
    size_kb = args.output.stat().st_size / 1024
    print(f"GeoJSON écrit : {args.output.resolve()} ({size_kb:.1f} Ko)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="transit_sim")
    commands = parser.add_subparsers(dest="command", required=True)

    network = commands.add_parser(
        "build-network", help="Filtre le GTFS sur une date et exporte le réseau en GeoJSON."
    )
    network.add_argument("--gtfs", type=Path, required=True, help="Dossier du GTFS.")
    network.add_argument("--date", type=_parse_date, required=True, help="Date AAAA-MM-JJ (mardi).")
    network.add_argument(
        "--output",
        type=Path,
        default=Path("../data/processed/network.geojson"),
        help="Fichier GeoJSON de sortie (défaut : ../data/processed/network.geojson).",
    )
    network.set_defaults(func=build_network)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
