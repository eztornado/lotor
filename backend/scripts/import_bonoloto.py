#!/usr/bin/env python3
"""
Importa el histórico completo de Bonoloto desde las hojas públicas de Lotoideas.

Fuente:
  https://www.lotoideas.com/bonoloto-resultados-historicos-de-todos-los-sorteos/

La web publica dos hojas de cálculo de Google:
  - gid=0: sorteos desde 2013 hasta la actualidad.
  - gid=1: sorteos desde 1988 hasta 2012.

El script descarga ambas, valida cada sorteo y genera:
  backend/data/raw/bonoloto_historical.csv

Uso:
  python backend/scripts/import_bonoloto.py
  python backend/scripts/import_bonoloto.py --offline /ruta/gid0.csv /ruta/gid1.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import sys
import urllib.request
from pathlib import Path

SHEETS = {
    "recent": (
        "https://docs.google.com/spreadsheets/d/e/"
        "2PACX-1vQALTRaLDFfhXOAQmeONPqmFKm9yOiQ4W97rhWgR41BZ7czFsjK5YktD6fnETKHGB9YUnyQ4XBSbhZx"
        "/pub?gid=0&single=true&output=csv"
    ),
    "historical": (
        "https://docs.google.com/spreadsheets/d/e/"
        "2PACX-1vQALTRaLDFfhXOAQmeONPqmFKm9yOiQ4W97rhWgR41BZ7czFsjK5YktD6fnETKHGB9YUnyQ4XBSbhZx"
        "/pub?gid=1&single=true&output=csv"
    ),
}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "bonoloto_historical.csv"


def download(url: str, timeout: int = 60) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8-sig")


def parse_csv(text: str) -> list[dict]:
    """Convierte una hoja de Lotoideas en sorteos validados."""
    draws: list[dict] = []
    reader = csv.reader(io.StringIO(text))
    next(reader, None)  # cabecera

    for raw in reader:
        if not raw or not raw[0].strip():
            continue

        try:
            date = dt.datetime.strptime(raw[0].strip(), "%d/%m/%Y").date()
            numbers = [int(value) for value in raw[1:7]]
            complementario = int(raw[7]) if len(raw) > 7 and raw[7].strip() else None
            reintegro = int(raw[8]) if len(raw) > 8 and raw[8].strip() else None
        except (ValueError, IndexError):
            continue

        if len(numbers) != 6 or len(set(numbers)) != 6:
            continue
        if any(number < 1 or number > 49 for number in numbers):
            continue
        if complementario is not None and not 1 <= complementario <= 49:
            continue
        if reintegro is not None and not 0 <= reintegro <= 9:
            continue

        draws.append(
            {
                "date": date,
                "numbers": tuple(sorted(numbers)),
                "complementario": complementario,
                "reintegro": reintegro,
            }
        )

    return draws


def merge(*groups: list[dict]) -> list[dict]:
    """Une sorteos, elimina duplicados y ordena del más reciente al más antiguo."""
    by_date: dict[dt.date, dict] = {}
    for group in groups:
        for draw in group:
            # Si hay duplicado, conservamos el registro con reintegro.
            previous = by_date.get(draw["date"])
            if previous is None or (
                previous.get("reintegro") is None and draw.get("reintegro") is not None
            ):
                by_date[draw["date"]] = draw
    return sorted(by_date.values(), key=lambda item: item["date"], reverse=True)


def write_csv(draws: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "date",
                "n1",
                "n2",
                "n3",
                "n4",
                "n5",
                "n6",
                "complementario",
                "reintegro",
                "source",
            ]
        )
        for draw in draws:
            writer.writerow(
                [
                    draw["date"].isoformat(),
                    *draw["numbers"],
                    draw["complementario"] if draw["complementario"] is not None else "",
                    draw["reintegro"] if draw["reintegro"] is not None else "",
                    "lotoideas_selae",
                ]
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa el histórico de Bonoloto")
    parser.add_argument(
        "--offline",
        nargs=2,
        metavar=("RECENT_CSV", "HISTORICAL_CSV"),
        help="Usa dos CSV locales en lugar de descargar las hojas de Google",
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    if args.offline:
        texts = [Path(path).read_text(encoding="utf-8-sig") for path in args.offline]
    else:
        texts = [download(url) for url in SHEETS.values()]

    draws = merge(*[parse_csv(text) for text in texts])
    if not draws:
        print("No se ha podido importar ningún sorteo.", file=sys.stderr)
        return 1

    write_csv(draws, args.output)
    print(
        f"Importados {len(draws)} sorteos "
        f"({draws[-1]['date']} → {draws[0]['date']}) en {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
