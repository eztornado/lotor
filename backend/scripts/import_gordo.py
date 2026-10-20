#!/usr/bin/env python3
"""
Importa el histórico completo de El Gordo de la Primitiva desde la hoja
pública de Lotoideas (resultados oficiales de SELAE).

El formato actual (5 números + clave) comenzó el 6 de febrero de 2005.

El script descarga la hoja, valida cada sorteo y genera:
  backend/data/raw/gordo_historical.csv

Uso:
  python backend/scripts/import_gordo.py
  python backend/scripts/import_gordo.py --offline /ruta/gordo.csv
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import sys
import urllib.request
from pathlib import Path

SHEET = (
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vRR678qNlN_3p2dAxRG0LULS6EYmBbEmpfVhCEmsYky6eiuEH3o_mCRc4c2_EevPru_3BJfSV0QwpG8"
    "/pub?output=csv"
)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "raw" / "gordo_historical.csv"
POOL_SIZE = 54
PICK_SIZE = 5

# Sorteos que aún no aparecen en la hoja pública pero ya son oficiales.
# Se pueden añadir aquí y el script los conserva al regenerar el CSV.
MANUAL_DRAWS = [
    # 2026-10-18: 11 14 29 31 34, clave 8
    {"date": dt.date(2026, 10, 18), "numbers": (11, 14, 29, 31, 34), "key": 8},
]


def download(url: str, timeout: int = 60) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8-sig")


def parse_csv(text: str) -> list[dict]:
    """Convierte la hoja de Lotoideas en sorteos validados."""
    draws: list[dict] = []
    reader = csv.reader(io.StringIO(text))
    next(reader, None)  # cabecera

    for raw in reader:
        if not raw or not raw[0].strip():
            continue

        try:
            date = dt.datetime.strptime(raw[0].strip(), "%d/%m/%Y").date()
            numbers = tuple(sorted(int(value) for value in raw[1:6]))
            key = int(raw[6]) if len(raw) > 6 and raw[6].strip() else None
        except (ValueError, IndexError):
            continue

        if len(numbers) != PICK_SIZE or len(set(numbers)) != PICK_SIZE:
            continue
        if any(number < 1 or number > POOL_SIZE for number in numbers):
            continue
        if key is not None and not 0 <= key <= 9:
            continue

        draws.append({"date": date, "numbers": numbers, "key": key})

    return draws


def merge(*groups: list[dict]) -> list[dict]:
    by_date: dict[dt.date, dict] = {}
    for group in groups:
        for draw in group:
            previous = by_date.get(draw["date"])
            if previous is None or (previous.get("key") is None and draw.get("key") is not None):
                by_date[draw["date"]] = draw
    return sorted(by_date.values(), key=lambda item: item["date"])


def write(draws: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["date", "n1", "n2", "n3", "n4", "n5", "key_number", "source"]
        )
        for draw in draws:
            writer.writerow(
                [
                    draw["date"].isoformat(),
                    *draw["numbers"],
                    draw["key"] if draw.get("key") is not None else "",
                    draw.get("source", "lotoideas_selae"),
                ]
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Importa el histórico de El Gordo")
    parser.add_argument(
        "--offline",
        nargs="+",
        metavar="CSV",
        help="Archivos CSV locales en lugar de descargar la hoja",
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT),
        help="Ruta del CSV de salida",
    )
    args = parser.parse_args()

    downloaded: list[dict] = []
    if args.offline:
        for path in args.offline:
            text = Path(path).read_text(encoding="utf-8-sig")
            downloaded.extend(parse_csv(text))
    else:
        print("Descargando hoja de Lotoideas...")
        downloaded = parse_csv(download(SHEET))

    manual = [
        {
            "date": item["date"],
            "numbers": item["numbers"],
            "key": item["key"],
            "source": "manual_selae",
        }
        for item in MANUAL_DRAWS
    ]

    output = Path(args.output)
    existing: list[dict] = []
    if output.exists():
        # Conservamos los sorteos locales que ya tuviéramos (por ejemplo, el
        # último sorteo añadido a mano antes de que se actualice la hoja).
        with output.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                try:
                    existing.append(
                        {
                            "date": dt.datetime.strptime(row["date"], "%Y-%m-%d").date(),
                            "numbers": tuple(
                                sorted(int(row[f"n{index}"]) for index in range(1, PICK_SIZE + 1))
                            ),
                            "key": int(row["key_number"]) if row.get("key_number") else None,
                            "source": row.get("source", "local"),
                        }
                    )
                except (ValueError, KeyError):
                    continue

    draws = merge(downloaded, existing, manual)
    write(draws, output)

    print(f"Guardados {len(draws)} sorteos en {output}")
    if draws:
        print(f"Rango: {draws[0]['date']} → {draws[-1]['date']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
