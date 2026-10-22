#!/usr/bin/env python3
"""
Importador de datos para La Quiniela.

Genera dos datasets reproducibles en ``backend/data/raw``:

1. ``quiniela_matches.csv``
   Resultados históricos de fútbol (LaLiga, LaLiga Hypermotion y las cinco
   grandes ligas europeas) usados para estimar la fuerza de cada equipo.

   Fuente: Football-Data.co.uk. En entornos donde el dominio no es accesible
   directamente se usa el proxy de lectura de Jina.

2. ``quiniela_fixtures.csv``
   Composición de las próximas jornadas de La Quiniela (15 partidos: 14
   normales + pleno al 15).

   Fuente: Eduardo Losilla (calendario público de SELAE).

Uso:
    python backend/scripts/import_quiniela.py
    python backend/scripts/import_quiniela.py --skip-matches
    python backend/scripts/import_quiniela.py --skip-fixtures
    python backend/scripts/import_quiniela.py --seasons 6
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import datetime as dt
import io
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable, Optional

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "backend" / "data" / "raw"
MATCHES_PATH = RAW_DIR / "quiniela_matches.csv"
FIXTURES_PATH = RAW_DIR / "quiniela_fixtures.csv"

# Temporadas con formato YYZZ. La 2026/27 es la temporada en curso.
SPANISH_SEASONS = [
    "1415",
    "1516",
    "1617",
    "1718",
    "1819",
    "1920",
    "2021",
    "2122",
    "2223",
    "2324",
    "2425",
    "2526",
    "2627",
]
EUROPEAN_SEASONS = ["2122", "2223", "2324", "2425", "2526", "2627"]

LEAGUES = {
    "SP1": {
        "name": "LaLiga",
        "country": "España",
        "tier": 1,
        "seasons": SPANISH_SEASONS,
    },
    "SP2": {
        "name": "LaLiga Hypermotion",
        "country": "España",
        "tier": 2,
        "seasons": SPANISH_SEASONS,
    },
    "E0": {
        "name": "Premier League",
        "country": "Inglaterra",
        "tier": 1,
        "seasons": EUROPEAN_SEASONS,
    },
    "D1": {
        "name": "Bundesliga",
        "country": "Alemania",
        "tier": 1,
        "seasons": EUROPEAN_SEASONS,
    },
    "I1": {
        "name": "Serie A",
        "country": "Italia",
        "tier": 1,
        "seasons": EUROPEAN_SEASONS,
    },
    "F1": {
        "name": "Ligue 1",
        "country": "Francia",
        "tier": 1,
        "seasons": EUROPEAN_SEASONS,
    },
    "N1": {
        "name": "Eredivisie",
        "country": "Países Bajos",
        "tier": 1,
        "seasons": EUROPEAN_SEASONS,
    },
    "P1": {
        "name": "Primeira Liga",
        "country": "Portugal",
        "tier": 1,
        "seasons": EUROPEAN_SEASONS,
    },
}

MATCH_FIELDS = [
    "date",
    "season",
    "league",
    "league_name",
    "country",
    "tier",
    "home_team",
    "away_team",
    "home_goals",
    "away_goals",
    "result",
    "home_odds",
    "draw_odds",
    "away_odds",
    "source",
]

FIXTURE_FIELDS = [
    "season",
    "jornada",
    "start_date",
    "match_number",
    "home_team",
    "away_team",
    "kickoff_day",
    "kickoff_time",
    "kickoff_date",
    "competition",
    "is_pleno",
    "source",
]

WEEKDAYS = {
    "LUN": 0,
    "MAR": 1,
    "MIE": 2,
    "MIÉ": 2,
    "JUE": 3,
    "VIE": 4,
    "SAB": 5,
    "SÁB": 5,
    "DOM": 6,
}


def _fetch(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _fetch_football_data(season: str, league: str) -> Optional[str]:
    """Descarga un CSV de Football-Data.co.uk (directo o vía Jina)."""
    direct = (
        f"https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"
    )
    proxy = f"https://r.jina.ai/http://www.football-data.co.uk/mmz4281/{season}/{league}.csv"

    for url, timeout in ((direct, 10), (proxy, 45)):
        try:
            payload = _fetch(url, timeout=timeout)
            if not payload:
                continue
            text = payload.decode("utf-8-sig", errors="ignore")
            if "Div," in text and "HomeTeam" in text:
                return text
        except Exception as exc:  # pragma: no cover - red
            print(f"  · {url.split('/')[2]} no disponible: {exc}", file=sys.stderr)
    return None


def _clean_football_data(text: str) -> str:
    """Elimina la cabecera que añade el proxy de Jina."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("Div,"):
            return "\n".join(lines[index:])
    return text


def _parse_float(value: str) -> Optional[float]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _parse_date(value: str) -> Optional[dt.date]:
    value = (value or "").strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_football_data(
    text: str, season: str, league: str
) -> list[dict[str, object]]:
    """Convierte un CSV de Football-Data en filas normalizadas."""
    cleaned = _clean_football_data(text)
    if not cleaned.strip():
        return []

    info = LEAGUES[league]
    matches: list[dict[str, object]] = []
    reader = csv.DictReader(io.StringIO(cleaned))
    for row in reader:
        date = _parse_date(row.get("Date") or row.get("date") or "")
        home = (row.get("HomeTeam") or "").strip()
        away = (row.get("AwayTeam") or "").strip()
        home_goals = _parse_float(row.get("FTHG") or "")
        away_goals = _parse_float(row.get("FTAG") or "")
        if date is None or not home or not away or home_goals is None or away_goals is None:
            continue

        result = (row.get("FTR") or "").strip().upper()
        if result not in {"H", "D", "A"}:
            if home_goals > away_goals:
                result = "H"
            elif home_goals < away_goals:
                result = "A"
            else:
                result = "D"

        matches.append(
            {
                "date": date.isoformat(),
                "season": season,
                "league": league,
                "league_name": info["name"],
                "country": info["country"],
                "tier": info["tier"],
                "home_team": home,
                "away_team": away,
                "home_goals": int(home_goals),
                "away_goals": int(away_goals),
                "result": result,
                "home_odds": _parse_float(row.get("AvgH") or row.get("B365H") or ""),
                "draw_odds": _parse_float(row.get("AvgD") or row.get("B365D") or ""),
                "away_odds": _parse_float(row.get("AvgA") or row.get("B365A") or ""),
                "source": "football-data.co.uk",
            }
        )
    return matches


def _merge_matches(*groups: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    by_key: dict[tuple[str, str, str, str], dict[str, object]] = {}
    for group in groups:
        for match in group:
            key = (
                str(match["date"]),
                str(match["league"]),
                str(match["home_team"]),
                str(match["away_team"]),
            )
            by_key[key] = match
    return sorted(
        by_key.values(),
        key=lambda item: (str(item["date"]), str(item["league"])),
    )


def _write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    temporary.replace(path)


def import_matches(
    limit_seasons: Optional[int] = None, workers: int = 6
) -> list[dict[str, object]]:
    tasks: list[tuple[str, str]] = []
    for league, info in LEAGUES.items():
        seasons = info["seasons"][-limit_seasons:] if limit_seasons else info["seasons"]
        tasks.extend((league, season) for season in seasons)

    downloaded: list[dict[str, object]] = []

    def _task(task: tuple[str, str]) -> list[dict[str, object]]:
        league, season = task
        text = _fetch_football_data(season, league)
        if text is None:
            print(f"  · sin datos para {league} {season}", file=sys.stderr)
            return []
        parsed = parse_football_data(text, season, league)
        print(f"  · {league} {season}: {len(parsed)} partidos", file=sys.stderr)
        return parsed

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_task, task): task for task in tasks}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            task = futures[future]
            try:
                downloaded.extend(future.result())
            except Exception as exc:  # pragma: no cover - red
                print(f"  · error en {task}: {exc}", file=sys.stderr)
            print(f"[{index}/{len(tasks)}] completado", file=sys.stderr)

    existing: list[dict[str, object]] = []
    if MATCHES_PATH.exists():
        with MATCHES_PATH.open("r", encoding="utf-8", newline="") as handle:
            existing = list(csv.DictReader(handle))

    merged = _merge_matches(existing, downloaded)
    _write_csv(MATCHES_PATH, MATCH_FIELDS, merged)
    print(
        f"✔ {MATCHES_PATH} ({len(merged)} partidos, "
        f"{merged[0]['date'] if merged else 'sin datos'} → "
        f"{merged[-1]['date'] if merged else 'sin datos'})",
        file=sys.stderr,
    )
    return merged


def _strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", value).strip()


def _competition_for(home: str, away: str) -> str:
    if "(F)" in home or "(F)" in away or " W." in home or " W." in away:
        return "Liga F"
    return "La Quiniela"


def parse_fixtures(html: str) -> list[dict[str, object]]:
    """Extrae las próximas jornadas de la página pública de Eduardo Losilla."""
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?</style>", "", html, flags=re.S | re.I)

    headers = [
        (match.start(), match.group(1), match.group(2))
        for match in re.finditer(
            r"JORNADA\s+(\d+)\s*-\s*(\d{2}/\d{2}/\d{4})", html
        )
    ]
    fixtures: list[dict[str, object]] = []

    for index, (position, jornada, raw_date) in enumerate(headers):
        end = headers[index + 1][0] if index + 1 < len(headers) else len(html)
        section = html[position:end]
        start_date = dt.datetime.strptime(raw_date, "%d/%m/%Y").date()

        blocks = re.split(r'(?=aria-label="Partido número)', section)
        for block in blocks[1:]:
            number_match = re.search(r'aria-label="Partido número (\d+)"', block)
            teams_match = re.search(
                r'aria-label="([^"]+) contra ([^"]+)"', block
            )
            if not number_match or not teams_match:
                continue
            match_number = int(number_match.group(1))
            home = _strip_tags(teams_match.group(1))
            away = _strip_tags(teams_match.group(2))

            flat = _strip_tags(block)
            kickoff = re.search(
                r"\b(LUN|MAR|MIE|MIÉ|JUE|VIE|SAB|SÁB|DOM)\s+(\d{1,2}:\d{2})",
                flat,
            )
            day = kickoff.group(1) if kickoff else ""
            time_value = kickoff.group(2) if kickoff else ""
            kickoff_date = ""
            if day and day in WEEKDAYS:
                offset = (WEEKDAYS[day] - start_date.weekday()) % 7
                kickoff_date = (start_date + dt.timedelta(days=offset)).isoformat()

            fixtures.append(
                {
                    "season": _season_from_date(start_date),
                    "jornada": int(jornada),
                    "start_date": start_date.isoformat(),
                    "match_number": match_number,
                    "home_team": home,
                    "away_team": away,
                    "kickoff_day": day,
                    "kickoff_time": time_value,
                    "kickoff_date": kickoff_date,
                    "competition": _competition_for(home, away),
                    "is_pleno": match_number == 15,
                    "source": "eduardolosilla.es",
                }
            )

    return fixtures


def _season_from_date(date: dt.date) -> str:
    start = date.year if date.month >= 7 else date.year - 1
    return f"{start}/{str(start + 1)[-2:]}"


def import_fixtures() -> list[dict[str, object]]:
    url = "https://www.eduardolosilla.es/quiniela/ayudas/proximas"
    print(f"Descargando {url}...", file=sys.stderr)
    html = _fetch(url, timeout=60).decode("utf-8", errors="ignore")
    fixtures = parse_fixtures(html)
    if not fixtures:
        raise RuntimeError("No se han podido extraer jornadas de La Quiniela")

    # Nos quedamos con las tres próximas jornadas (15 partidos cada una).
    jornadas = sorted({int(item["jornada"]) for item in fixtures})[:3]
    selected = [item for item in fixtures if int(item["jornada"]) in jornadas]
    _write_csv(FIXTURES_PATH, FIXTURE_FIELDS, selected)
    print(
        f"✔ {FIXTURES_PATH} ({len(selected)} partidos, "
        f"jornadas {', '.join(str(j) for j in jornadas)})",
        file=sys.stderr,
    )
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-matches", action="store_true", help="No descargar resultados")
    parser.add_argument("--skip-fixtures", action="store_true", help="No descargar jornadas")
    parser.add_argument(
        "--seasons",
        type=int,
        default=None,
        help="Limita el número de temporadas por liga (para pruebas)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Descargas concurrentes de Football-Data (por defecto 6)",
    )
    args = parser.parse_args()

    if not args.skip_matches:
        import_matches(limit_seasons=args.seasons, workers=args.workers)
    if not args.skip_fixtures:
        import_fixtures()


if __name__ == "__main__":
    main()
