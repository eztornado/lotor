"""
Datos de La Quiniela.

Dos fuentes, ambas cacheadas en memoria:

* ``quiniela_matches.csv``: resultados históricos de fútbol (LaLiga,
  LaLiga Hypermotion y las cinco grandes ligas europeas) desde 2014.
  Se usan para estimar la fuerza de cada equipo.
* ``quiniela_fixtures.csv``: composición de las próximas jornadas de
  La Quiniela (15 partidos: 14 signos + pleno al 15).

El módulo también incluye utilidades de normalización de nombres de equipo:
las fuentes públicas usan abreviaturas distintas (``R.MADRID``,
``Real Madrid``, ``R MADRID``...) y el modelo necesita una identidad única.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import re
import threading
import unicodedata
import urllib.request
from dataclasses import dataclass, field, replace
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable, Optional

from loguru import logger

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)

SIGNS = ("1", "X", "2")
MATCHES_PER_TICKET = 14
TOTAL_MATCHES = 15
PLENO_MATCH = 15
TICKET_PRICE_EUR = 0.75

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

LEAGUE_LABELS = {
    "SP1": "LaLiga",
    "SP2": "LaLiga Hypermotion",
    "E0": "Premier League",
    "D1": "Bundesliga",
    "I1": "Serie A",
    "F1": "Ligue 1",
    "N1": "Eredivisie",
    "P1": "Primeira Liga",
    "LIGA_F": "Liga F",
    "LOWER": "Divisiones inferiores",
    "EUROPE": "Competición europea",
}

# Diferencia media de fuerza (en log-goles) entre una liga y la media global.
# Se usa cuando dos equipos de ligas distintas se enfrentan (Copa, Europa).
LEAGUE_OFFSETS = {
    "SP1": 0.20,
    "SP2": 0.00,
    "E0": 0.25,
    "D1": 0.20,
    "I1": 0.18,
    "F1": 0.15,
    "N1": 0.06,
    "P1": 0.05,
    "LIGA_F": 0.00,
    "LOWER": -0.55,
    "EUROPE": 0.10,
}

# Ligas europeas (no españolas) presentes en el histórico. Se usan para
# distinguir una eliminatoria española (Copa) de una competición europea.
EUROPEAN_LEAGUES = {"E0", "D1", "I1", "F1", "N1", "P1"}
SPANISH_LEAGUES = {"SP1", "SP2"}

# Clubes europeos que no están en los datasets de las cinco grandes ligas pero
# que sí aparecen en La Quiniela. Evitan que se les trate como un equipo de
# división inferior cuando se enfrentan a un club español.
EUROPEAN_CLUBS = {
    "UNION SAINT GILLOISE",
    "BODO GLIMT",
    "SLAVIA PRAGUE",
    "FENERBAHCE",
    "AEK ATHENS",
    "CELTIC",
    "RANGERS",
    "BENFICA",
    "SPORTING CP",
    "BRAGA",
    "GALATASARAY",
    "BESIKTAS",
    "OLYMPIACOS",
    "PANATHINAIKOS",
    "COPENHAGUE",
    "COPPENHAGUE",
    "SALZBURGO",
    "STURM GRAZ",
    "CLUB BRUGGE",
    "ANDERLECHT",
    "PSV",
    "FEYENOORD",
    "AZ ALKMAAR",
    "TWENTE",
    "LILLE",
    "MONACO",
    "MARSELLA",
    "NIZA",
    "RENNES",
    "LEVERKUSEN",
    "FRANKFURT",
    "STUTTGART",
    "WOLFSBURGO",
    "ATALANTA",
    "JUVENTUS",
    "MILAN",
    "INTER",
    "LAZIO",
    "FIORENTINA",
    "BOLOGNA",
}

# Alias normalizados. La clave es el nombre ya normalizado (mayúsculas, sin
# acentos ni puntuación) y el valor el nombre canónico que usa el dataset.
TEAM_ALIASES: dict[str, str] = {
    # LaLiga / LaLiga Hypermotion
    "ATH MADRID": "ATLETICO MADRID",
    "AT MADRID": "ATLETICO MADRID",
    "ATL MADRID": "ATLETICO MADRID",
    "ATLETICO DE MADRID": "ATLETICO MADRID",
    "ATLETICO": "ATLETICO MADRID",
    "ATH BILBAO": "ATHLETIC CLUB",
    "ATHLETIC BILBAO": "ATHLETIC CLUB",
    "ATH CLUB": "ATHLETIC CLUB",
    # ``_normalize`` elimina el sufijo CLUB, así que estas formas abreviadas
    # de la fuente de calendarios deben apuntar al nombre canónico del dataset.
    "ATH": "ATHLETIC CLUB",
    "ATHLETIC": "ATHLETIC CLUB",
    "ATHLETIC CLUB": "ATHLETIC CLUB",
    "BILBAO": "ATHLETIC CLUB",
    "BARCELONA": "BARCELONA",
    "FC BARCELONA": "BARCELONA",
    "BARCA": "BARCELONA",
    "REAL MADRID": "REAL MADRID",
    "R MADRID": "REAL MADRID",
    "MADRID": "REAL MADRID",
    "SOCIEDAD": "REAL SOCIEDAD",
    "R SOCIEDAD": "REAL SOCIEDAD",
    "REAL SOCIEDAD": "REAL SOCIEDAD",
    "BETIS": "REAL BETIS",
    "REAL BETIS": "REAL BETIS",
    "CELTA": "CELTA VIGO",
    "CELTA VIGO": "CELTA VIGO",
    "DEPORTIVO": "DEPORTIVO LA CORUNA",
    "LA CORUNA": "DEPORTIVO LA CORUNA",
    "RC DEPORTIVO": "DEPORTIVO LA CORUNA",
    "DEPORTIVO LA CORUNA": "DEPORTIVO LA CORUNA",
    "ALAVES": "DEPORTIVO ALAVES",
    "DEPORTIVO ALAVES": "DEPORTIVO ALAVES",
    "VALENCIA": "VALENCIA",
    "VILLARREAL": "VILLARREAL",
    "ELCHE": "ELCHE",
    "GETAFE": "GETAFE",
    "OSASUNA": "OSASUNA",
    "SEVILLA": "SEVILLA",
    "MALLORCA": "MALLORCA",
    "LAS PALMAS": "LAS PALMAS",
    "LEVANTE": "LEVANTE",
    "RAYO": "RAYO VALLECANO",
    "VALLECANO": "RAYO VALLECANO",
    "RAYO VALLECANO": "RAYO VALLECANO",
    "RACING S": "RACING SANTANDER",
    "RACING SANTANDER": "RACING SANTANDER",
    "SANTANDER": "RACING SANTANDER",
    "R OVIEDO": "REAL OVIEDO",
    "OVIEDO": "REAL OVIEDO",
    "REAL OVIEDO": "REAL OVIEDO",
    "R ZARAGOZA": "REAL ZARAGOZA",
    "ZARAGOZA": "REAL ZARAGOZA",
    "REAL ZARAGOZA": "REAL ZARAGOZA",
    "CADIZ": "CADIZ",
    "MALAGA": "MALAGA",
    "GRANADA": "GRANADA",
    "EIBAR": "EIBAR",
    "ALMERIA": "ALMERIA",
    "ELDENSE": "ELDENSE",
    "BURGOS": "BURGOS",
    "CASTELLON": "CASTELLON",
    "TENERIFE": "TENERIFE",
    "SABADELL": "SABADELL",
    "HUESCA": "HUESCA",
    "LEGANES": "LEGANES",
    "MIRANDES": "MIRANDES",
    "SPORTING": "SPORTING GIJON",
    "SPORTING GIJON": "SPORTING GIJON",
    "GIJON": "SPORTING GIJON",
    "REC HUELVA": "RECREATIVO HUELVA",
    "RECREATIVO": "RECREATIVO HUELVA",
    "RECREATIVO HUELVA": "RECREATIVO HUELVA",
    "XEREZ": "XEREZ",
    "NUMANCIA": "NUMANCIA",
    "PONTEVEDRA": "PONTEVEDRA",
    "ALCOYANO": "ALCOYANO",
    "BADAJOZ": "BADAJOZ",
    "CONQUENSE": "CONQUENSE",
    "AROSA": "AROSA",
    "AROSA SC": "AROSA",
    "CARTAGENA": "CARTAGENA",
    "VALLADOLID": "VALLADOLID",
    "R VALLADOLID": "VALLADOLID",
    "REAL VALLADOLID": "VALLADOLID",
    # Europa
    "B MUNICH": "BAYERN MUNICH",
    "BAYERN": "BAYERN MUNICH",
    "BAYERN MUNICH": "BAYERN MUNICH",
    "MAN CITY": "MANCHESTER CITY",
    "MANCHESTER CITY": "MANCHESTER CITY",
    "MAN UNITED": "MANCHESTER UNITED",
    "MANCHESTER UNITED": "MANCHESTER UNITED",
    "PSG": "PARIS SAINT GERMAIN",
    "PARIS SG": "PARIS SAINT GERMAIN",
    "PARIS SAINT GERMAIN": "PARIS SAINT GERMAIN",
    "B DORTMUND": "BORUSSIA DORTMUND",
    "BORUSSIA DORTMUND": "BORUSSIA DORTMUND",
    "DORTMUND": "BORUSSIA DORTMUND",
    "RB LEIPZIG": "RB LEIPZIG",
    "LEIPZIG": "RB LEIPZIG",
    "OPORTO": "PORTO",
    "PORTO": "PORTO",
    "NAPOLI": "NAPOLI",
    "LENS": "LENS",
    "COMO 1907": "COMO",
    "COMO": "COMO",
    "SLAVIA PRAGA": "SLAVIA PRAGUE",
    "SLAVIA PRAGUE": "SLAVIA PRAGUE",
    "ARSENAL": "ARSENAL",
    "LIVERPOOL": "LIVERPOOL",
    "ROMA": "ROMA",
    "FENERBAHCE": "FENERBAHCE",
    "AEK ATENAS": "AEK ATHENS",
    "AEK ATHENS": "AEK ATHENS",
    "OL LYON": "LYON",
    "LYON": "LYON",
    "R UNION SG": "UNION SAINT GILLOISE",
    "UNION SAINT GILLOISE": "UNION SAINT GILLOISE",
    "BRIGHTON": "BRIGHTON",
    "ASTON VILLA": "ASTON VILLA",
    "BODO GLIMT": "BODO GLIMT",
    "LOSC LILLE": "LILLE",
    "LILLE": "LILLE",
}


def _normalize(value: str) -> str:
    """Mayúsculas, sin acentos, sin puntuación y sin sufijos societarios."""
    text = unicodedata.normalize("NFKD", value or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.upper()
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"[^A-Z0-9 ]", " ", text)
    text = re.sub(
        r"\b(CF|FC|UD|CD|SD|RCD|RC|SC|AC|AS|SS|SSC|BC|BK|IF|FF|CLUB|DE|FUTBOL)\b",
        " ",
        text,
    )
    return re.sub(r"\s+", " ", text).strip()


def is_women_team(name: str) -> bool:
    upper = (name or "").upper()
    return "(F)" in upper or " W." in upper or upper.endswith(" (F)")


def canonical_team(name: str) -> str:
    """Nombre canónico para un equipo (sin resolver contra el dataset)."""
    if is_women_team(name):
        return f"F|{_normalize(name)}"
    normalized = _normalize(name)
    return TEAM_ALIASES.get(normalized, normalized)


def _parse_date(value: str) -> Optional[dt.date]:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _parse_int(value: str) -> Optional[int]:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _parse_float(value: str) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class Match:
    date: dt.date
    season: str
    league: str
    league_name: str
    country: str
    tier: int
    home_team: str
    away_team: str
    home_goals: int
    away_goals: int
    result: str
    home_odds: Optional[float] = None
    draw_odds: Optional[float] = None
    away_odds: Optional[float] = None
    source: str = "local"

    @property
    def is_valid(self) -> bool:
        return (
            self.home_team != self.away_team
            and 0 <= self.home_goals <= 20
            and 0 <= self.away_goals <= 20
            and self.result in {"H", "D", "A"}
        )


@dataclass(frozen=True, slots=True)
class Fixture:
    season: str
    jornada: int
    start_date: dt.date
    match_number: int
    home_team: str
    away_team: str
    kickoff_day: str = ""
    kickoff_time: str = ""
    kickoff_date: Optional[dt.date] = None
    competition: str = "La Quiniela"
    is_pleno: bool = False
    source: str = "local"

    @property
    def is_women(self) -> bool:
        return is_women_team(self.home_team) or is_women_team(self.away_team)

    @property
    def home(self) -> str:
        return canonical_team(self.home_team)

    @property
    def away(self) -> str:
        return canonical_team(self.away_team)


@dataclass(slots=True)
class Jornada:
    season: str
    jornada: int
    start_date: dt.date
    fixtures: list[Fixture]
    competition: str = "La Quiniela"

    @property
    def label(self) -> str:
        return f"Jornada {self.jornada} · {self.season}"

    @property
    def pleno(self) -> Optional[Fixture]:
        return next((fixture for fixture in self.fixtures if fixture.is_pleno), None)

    @property
    def competitions(self) -> list[str]:
        """Competiciones realmente presentes en la jornada (puede ser mixta)."""
        return sorted({fixture.competition for fixture in self.fixtures})

    @property
    def is_complete(self) -> bool:
        return len(self.fixtures) == TOTAL_MATCHES


def _candidate_data_dirs() -> list[Path]:
    service_file = Path(__file__).resolve()
    return [
        service_file.parents[2] / "data",
        Path.cwd() / "data",
        Path.cwd() / "backend" / "data",
    ]


def _default_data_dir() -> Path:
    for directory in _candidate_data_dirs():
        if (directory / "raw" / "quiniela_matches.csv").exists():
            return directory
    return _candidate_data_dirs()[0]


class TeamResolver:
    """Resuelve abreviaturas de La Quiniela contra los equipos del dataset."""

    def __init__(self, known_teams: Iterable[str]):
        self.known = sorted({canonical_team(team) for team in known_teams})
        self.normalized = {_normalize(team): team for team in self.known}

    def resolve(self, name: str) -> tuple[str, bool]:
        """Devuelve (equipo_canónico, encontrado_en_el_dataset)."""
        if is_women_team(name):
            return canonical_team(name), False

        normalized = _normalize(name)
        alias = TEAM_ALIASES.get(normalized)
        candidate = canonical_team(alias or name)

        if candidate in self.known:
            return candidate, True
        if normalized in self.normalized:
            return self.normalized[normalized], True

        # Búsqueda difusa conservadora. Evita confundir equipos distintos.
        best_name = ""
        best_score = 0.0
        for known_normalized, canonical in self.normalized.items():
            score = SequenceMatcher(None, normalized, known_normalized).ratio()
            if score > best_score:
                best_score, best_name = score, canonical
        if best_score >= 0.86:
            return best_name, True
        return candidate, False


class QuinielaDataManager:
    """Carga, valida y actualiza los datasets de La Quiniela."""

    def __init__(self, data_dir: Optional[str | Path] = None):
        self.data_dir = Path(data_dir) if data_dir else _default_data_dir()
        self.matches_path = self.data_dir / "raw" / "quiniela_matches.csv"
        self.fixtures_path = self.data_dir / "raw" / "quiniela_fixtures.csv"
        self._matches: Optional[list[Match]] = None
        self._fixtures: Optional[list[Fixture]] = None
        self._jornadas: Optional[list[Jornada]] = None
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Carga
    # ------------------------------------------------------------------
    def load_matches(self, force: bool = False) -> list[Match]:
        if self._matches is not None and not force:
            return self._matches
        with self._lock:
            if self._matches is not None and not force:
                return self._matches
            matches: list[Match] = []
            if not self.matches_path.exists():
                logger.error(f"No existe el dataset de La Quiniela: {self.matches_path}")
                self._matches = []
                return self._matches
            try:
                with self.matches_path.open(
                    "r", encoding="utf-8-sig", newline=""
                ) as handle:
                    for row in csv.DictReader(handle):
                        match = self._row_to_match(row)
                        if match is not None:
                            matches.append(match)
            except Exception as exc:  # pragma: no cover - defensivo
                logger.error(f"Error leyendo el dataset de La Quiniela: {exc}")
                matches = []
            self._matches = sorted(matches, key=lambda item: item.date)
            logger.info(
                f"Quiniela: {len(self._matches)} partidos cargados "
                f"({self._matches[0].date if self._matches else 'sin datos'} → "
                f"{self._matches[-1].date if self._matches else 'sin datos'})"
            )
            return self._matches

    def _row_to_match(self, row: dict[str, str]) -> Optional[Match]:
        date = _parse_date(row.get("date") or "")
        home_goals = _parse_int(row.get("home_goals") or "")
        away_goals = _parse_int(row.get("away_goals") or "")
        if date is None or home_goals is None or away_goals is None:
            return None
        home = canonical_team(row.get("home_team") or "")
        away = canonical_team(row.get("away_team") or "")
        if not home or not away or home == away:
            return None
        result = (row.get("result") or "").strip().upper()
        if result not in {"H", "D", "A"}:
            result = "H" if home_goals > away_goals else "A" if home_goals < away_goals else "D"
        match = Match(
            date=date,
            season=(row.get("season") or "").strip(),
            league=(row.get("league") or "").strip(),
            league_name=(row.get("league_name") or "").strip(),
            country=(row.get("country") or "").strip(),
            tier=_parse_int(row.get("tier") or "") or 1,
            home_team=home,
            away_team=away,
            home_goals=home_goals,
            away_goals=away_goals,
            result=result,
            home_odds=_parse_float(row.get("home_odds") or ""),
            draw_odds=_parse_float(row.get("draw_odds") or ""),
            away_odds=_parse_float(row.get("away_odds") or ""),
            source=(row.get("source") or "local").strip(),
        )
        return match if match.is_valid else None

    def load_fixtures(self, force: bool = False) -> list[Fixture]:
        if self._fixtures is not None and not force:
            return self._fixtures
        with self._lock:
            if self._fixtures is not None and not force:
                return self._fixtures
            fixtures: list[Fixture] = []
            if not self.fixtures_path.exists():
                logger.error(f"No existe el calendario de La Quiniela: {self.fixtures_path}")
                self._fixtures = []
                return self._fixtures
            try:
                with self.fixtures_path.open(
                    "r", encoding="utf-8-sig", newline=""
                ) as handle:
                    for row in csv.DictReader(handle):
                        fixture = self._row_to_fixture(row)
                        if fixture is not None:
                            fixtures.append(fixture)
            except Exception as exc:  # pragma: no cover - defensivo
                logger.error(f"Error leyendo el calendario de La Quiniela: {exc}")
                fixtures = []

            team_league = self._team_league_map()
            fixtures = [
                replace(
                    fixture,
                    competition=self._infer_competition(fixture, team_league),
                )
                for fixture in fixtures
            ]
            self._fixtures = sorted(
                fixtures,
                key=lambda item: (item.start_date, item.jornada, item.match_number),
            )
            return self._fixtures

    def _team_league_map(self) -> dict[str, tuple[str, str]]:
        mapping: dict[str, tuple[str, str]] = {}
        for match in self.load_matches():
            mapping[match.home_team] = (match.league, match.league_name)
            mapping[match.away_team] = (match.league, match.league_name)
        return mapping

    def _infer_competition(
        self, fixture: Fixture, team_league: dict[str, tuple[str, str]]
    ) -> str:
        if fixture.is_women:
            return "Liga F"
        resolver = self.resolver()
        home, home_known = resolver.resolve(fixture.home_team)
        away, away_known = resolver.resolve(fixture.away_team)
        home_league = team_league.get(home, ("", ""))[0]
        away_league = team_league.get(away, ("", ""))[0]

        if home_known and away_known:
            if home_league == away_league:
                return team_league.get(home, ("", "La Quiniela"))[1] or "La Quiniela"
            if home_league in SPANISH_LEAGUES and away_league in SPANISH_LEAGUES:
                # Un Primera/Segunda contra otro equipo español fuera de liga
                # es una eliminatoria (Copa del Rey), no una competición europea.
                return "Copa del Rey"
            if home_league in EUROPEAN_LEAGUES or away_league in EUROPEAN_LEAGUES:
                return "Europea"
            return "Copa del Rey"

        # Solo uno de los dos equipos está en el histórico. Si el conocido es
        # español, el desconocido es casi siempre un club de división inferior
        # en Copa; si es extranjero, se trata de una competición europea.
        unknown = away if home_known else home
        known_league = home_league if home_known else away_league
        if unknown in EUROPEAN_CLUBS:
            return "Europea"
        if known_league in SPANISH_LEAGUES:
            return "Copa del Rey"
        if known_league in EUROPEAN_LEAGUES:
            return "Europea"
        return "Copa del Rey"

    def _row_to_fixture(self, row: dict[str, str]) -> Optional[Fixture]:
        start_date = _parse_date(row.get("start_date") or "")
        if start_date is None:
            return None
        match_number = _parse_int(row.get("match_number") or "")
        jornada = _parse_int(row.get("jornada") or "")
        if match_number is None or jornada is None:
            return None
        home = (row.get("home_team") or "").strip()
        away = (row.get("away_team") or "").strip()
        if not home or not away:
            return None
        kickoff_date = _parse_date(row.get("kickoff_date") or "")
        return Fixture(
            season=(row.get("season") or "").strip(),
            jornada=jornada,
            start_date=start_date,
            match_number=match_number,
            home_team=home,
            away_team=away,
            kickoff_day=(row.get("kickoff_day") or "").strip(),
            kickoff_time=(row.get("kickoff_time") or "").strip(),
            kickoff_date=kickoff_date,
            competition=(row.get("competition") or "La Quiniela").strip(),
            is_pleno=(row.get("is_pleno") or "").strip().lower() in {"true", "1", "si", "sí"},
            source=(row.get("source") or "local").strip(),
        )

    def jornadas(self, force: bool = False) -> list[Jornada]:
        if self._jornadas is not None and not force:
            return self._jornadas
        grouped: dict[tuple[str, int], list[Fixture]] = {}
        for fixture in self.load_fixtures(force=force):
            grouped.setdefault((fixture.season, fixture.jornada), []).append(fixture)
        jornadas = []
        for (season, jornada), items in grouped.items():
            competitions = sorted({item.competition for item in items})
            jornadas.append(
                Jornada(
                    season=season,
                    jornada=jornada,
                    start_date=min(item.start_date for item in items),
                    fixtures=sorted(items, key=lambda item: item.match_number),
                    competition=(
                        competitions[0]
                        if len(competitions) == 1
                        else "Mixta"
                        if competitions
                        else "La Quiniela"
                    ),
                )
            )
        self._jornadas = sorted(
            jornadas, key=lambda item: (item.start_date, item.jornada), reverse=False
        )
        return self._jornadas

    def next_jornada(self, now: Optional[dt.date] = None) -> Optional[Jornada]:
        now = now or dt.date.today()
        available = self.jornadas()
        if not available:
            return None
        future = [item for item in available if item.start_date >= now and item.is_complete]
        if future:
            return min(future, key=lambda item: item.start_date)
        complete = [item for item in available if item.is_complete]
        return max(complete, key=lambda item: item.start_date) if complete else available[-1]

    def find_jornada(
        self, jornada: int, season: Optional[str] = None
    ) -> Optional[Jornada]:
        for item in self.jornadas():
            if item.jornada == jornada and (season is None or item.season == season):
                return item
        return None

    def resolver(self) -> TeamResolver:
        matches = self.load_matches()
        teams = {match.home_team for match in matches} | {
            match.away_team for match in matches
        }
        return TeamResolver(teams)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    def summary(self) -> dict:
        matches = self.load_matches()
        fixtures = self.load_fixtures()
        jornadas = self.jornadas()
        next_jornada = self.next_jornada()
        leagues = sorted({match.league for match in matches})
        teams = {match.home_team for match in matches} | {
            match.away_team for match in matches
        }
        return {
            "total_matches": len(matches),
            "date_range": (
                {
                    "from": matches[0].date.isoformat(),
                    "to": matches[-1].date.isoformat(),
                }
                if matches
                else None
            ),
            "leagues": [
                {
                    "code": league,
                    "name": LEAGUE_LABELS.get(league, league),
                    "matches": sum(1 for match in matches if match.league == league),
                }
                for league in leagues
            ],
            "total_teams": len(teams),
            "total_jornadas": len(jornadas),
            "next_jornada": (
                {
                    "season": next_jornada.season,
                    "jornada": next_jornada.jornada,
                    "start_date": next_jornada.start_date.isoformat(),
                    "matches": len(next_jornada.fixtures),
                    "competition": next_jornada.competition,
                    "competitions": next_jornada.competitions,
                }
                if next_jornada
                else None
            ),
            "fixtures": len(fixtures),
            "source": matches[-1].source if matches else "local",
        }

    def history(self, limit: int = 50) -> list[dict]:
        matches = self.load_matches()
        recent = sorted(matches, key=lambda item: item.date, reverse=True)[:limit]
        return [
            {
                "date": match.date.isoformat(),
                "league": match.league,
                "league_name": match.league_name,
                "home_team": match.home_team,
                "away_team": match.away_team,
                "home_goals": match.home_goals,
                "away_goals": match.away_goals,
                "result": match.result,
                "odds": {
                    "home": match.home_odds,
                    "draw": match.draw_odds,
                    "away": match.away_odds,
                },
            }
            for match in recent
        ]

    # ------------------------------------------------------------------
    # Actualización
    # ------------------------------------------------------------------
    def refresh_fixtures(self, timeout: int = 60) -> dict:
        """Descarga las próximas jornadas de la web pública de Eduardo Losilla."""
        url = "https://www.eduardolosilla.es/quiniela/ayudas/proximas"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                html = response.read().decode("utf-8", errors="ignore")
            fixtures = parse_fixtures_html(html)
            if not fixtures:
                raise ValueError("No se han encontrado jornadas en la página")
            jornadas = sorted({fixture.jornada for fixture in fixtures})[:3]
            selected = [item for item in fixtures if item.jornada in jornadas]
            # La fuente no indica la competición: se infiere igual que al cargar
            # el CSV para no perder los priors de Copa/Europa tras un refresco.
            team_league = self._team_league_map()
            selected = sorted(
                (
                    replace(
                        fixture,
                        competition=self._infer_competition(fixture, team_league),
                    )
                    for fixture in selected
                ),
                key=lambda item: (item.jornada, item.match_number),
            )
            self._write_fixtures(selected)
            self._fixtures = selected
            self._jornadas = None
            return {
                "status": "success",
                "jornadas": jornadas,
                "fixtures": len(selected),
            }
        except Exception as exc:
            logger.warning(f"No se pudo actualizar el calendario de La Quiniela: {exc}")
            return {"status": "error", "error": str(exc), "fixtures": len(self.load_fixtures())}

    def refresh_matches(self, timeout: int = 60) -> dict:
        """
        Actualiza los resultados de la temporada actual (LaLiga y Segunda).

        No descarga las 13 temporadas completas: el histórico ya está incluido
        en el repositorio y esta operación solo incorpora los partidos nuevos.
        """
        season = _current_season()
        downloaded: list[Match] = []
        errors: list[str] = []
        for league in ("SP1", "SP2"):
            try:
                text = _download_football_data(league, season, timeout=timeout)
                if text:
                    downloaded.extend(parse_football_data_csv(text, season, league))
            except Exception as exc:  # pragma: no cover - red
                errors.append(f"{league}: {exc}")
                logger.warning(f"No se pudo actualizar {league}: {exc}")

        if not downloaded:
            return {
                "status": "error",
                "errors": errors,
                "total_matches": len(self.load_matches()),
            }

        merged = _merge_matches(self.load_matches(), downloaded)
        self._write_matches(merged)
        self._matches = merged
        return {
            "status": "success",
            "downloaded": len(downloaded),
            "total_matches": len(merged),
            "errors": errors,
        }

    def _write_matches(self, matches: list[Match]) -> None:
        fields = [
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
        self.matches_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.matches_path.with_suffix(".csv.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for match in matches:
                writer.writerow(
                    {
                        "date": match.date.isoformat(),
                        "season": match.season,
                        "league": match.league,
                        "league_name": match.league_name,
                        "country": match.country,
                        "tier": match.tier,
                        "home_team": match.home_team,
                        "away_team": match.away_team,
                        "home_goals": match.home_goals,
                        "away_goals": match.away_goals,
                        "result": match.result,
                        "home_odds": match.home_odds or "",
                        "draw_odds": match.draw_odds or "",
                        "away_odds": match.away_odds or "",
                        "source": match.source,
                    }
                )
        temporary.replace(self.matches_path)

    def _write_fixtures(self, fixtures: list[Fixture]) -> None:
        fields = [
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
        self.fixtures_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.fixtures_path.with_suffix(".csv.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for fixture in sorted(
                fixtures, key=lambda item: (item.jornada, item.match_number)
            ):
                writer.writerow(
                    {
                        "season": fixture.season,
                        "jornada": fixture.jornada,
                        "start_date": fixture.start_date.isoformat(),
                        "match_number": fixture.match_number,
                        "home_team": fixture.home_team,
                        "away_team": fixture.away_team,
                        "kickoff_day": fixture.kickoff_day,
                        "kickoff_time": fixture.kickoff_time,
                        "kickoff_date": (
                            fixture.kickoff_date.isoformat() if fixture.kickoff_date else ""
                        ),
                        "competition": fixture.competition,
                        "is_pleno": fixture.is_pleno,
                        "source": fixture.source,
                    }
                )
        temporary.replace(self.fixtures_path)


# ----------------------------------------------------------------------
# Parseo de fuentes
# ----------------------------------------------------------------------
def parse_football_data_csv(text: str, season: str, league: str) -> list[Match]:
    """Convierte un CSV de Football-Data.co.uk en partidos normalizados."""
    lines = text.splitlines()
    header_index = next(
        (index for index, line in enumerate(lines) if line.startswith("Div,")), None
    )
    if header_index is None:
        return []
    cleaned = "\n".join(lines[header_index:])
    info = {
        "SP1": ("LaLiga", "España", 1),
        "SP2": ("LaLiga Hypermotion", "España", 2),
        "E0": ("Premier League", "Inglaterra", 1),
        "D1": ("Bundesliga", "Alemania", 1),
        "I1": ("Serie A", "Italia", 1),
        "F1": ("Ligue 1", "Francia", 1),
        "N1": ("Eredivisie", "Países Bajos", 1),
        "P1": ("Primeira Liga", "Portugal", 1),
    }.get(league, (league, "", 1))

    matches: list[Match] = []
    for row in csv.DictReader(io.StringIO(cleaned)):
        date = _parse_date(row.get("Date") or "")
        home_goals = _parse_int(row.get("FTHG") or "")
        away_goals = _parse_int(row.get("FTAG") or "")
        home = canonical_team(row.get("HomeTeam") or "")
        away = canonical_team(row.get("AwayTeam") or "")
        if date is None or home_goals is None or away_goals is None or not home or not away:
            continue
        result = (row.get("FTR") or "").upper()
        if result not in {"H", "D", "A"}:
            result = "H" if home_goals > away_goals else "A" if home_goals < away_goals else "D"
        matches.append(
            Match(
                date=date,
                season=season,
                league=league,
                league_name=info[0],
                country=info[1],
                tier=info[2],
                home_team=home,
                away_team=away,
                home_goals=home_goals,
                away_goals=away_goals,
                result=result,
                home_odds=_parse_float(row.get("AvgH") or row.get("B365H") or ""),
                draw_odds=_parse_float(row.get("AvgD") or row.get("B365D") or ""),
                away_odds=_parse_float(row.get("AvgA") or row.get("B365A") or ""),
                source="football-data.co.uk",
            )
        )
    return [match for match in matches if match.is_valid]


def _strip_tags(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", value).strip()


def _competition_for(home: str, away: str) -> str:
    if is_women_team(home) or is_women_team(away):
        return "Liga F"
    return "La Quiniela"


def _season_from_date(date: dt.date) -> str:
    start = date.year if date.month >= 7 else date.year - 1
    return f"{start}/{str(start + 1)[-2:]}"


def parse_fixtures_html(html: str) -> list[Fixture]:
    """Extrae las próximas jornadas de la página pública de Eduardo Losilla."""
    html = re.sub(r"<script.*?</script>", "", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?</style>", "", html, flags=re.S | re.I)
    headers = [
        (match.start(), match.group(1), match.group(2))
        for match in re.finditer(
            r"JORNADA\s+(\d+)\s*-\s*(\d{2}/\d{2}/\d{4})", html
        )
    ]
    fixtures: list[Fixture] = []
    for index, (position, jornada, raw_date) in enumerate(headers):
        end = headers[index + 1][0] if index + 1 < len(headers) else len(html)
        section = html[position:end]
        start_date = dt.datetime.strptime(raw_date, "%d/%m/%Y").date()
        for block in re.split(r'(?=aria-label="Partido número)', section)[1:]:
            number_match = re.search(r'aria-label="Partido número (\d+)"', block)
            teams_match = re.search(r'aria-label="([^"]+) contra ([^"]+)"', block)
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
            kickoff_date = None
            if day in WEEKDAYS:
                offset = (WEEKDAYS[day] - start_date.weekday()) % 7
                kickoff_date = start_date + dt.timedelta(days=offset)
            fixtures.append(
                Fixture(
                    season=_season_from_date(start_date),
                    jornada=int(jornada),
                    start_date=start_date,
                    match_number=match_number,
                    home_team=home,
                    away_team=away,
                    kickoff_day=day,
                    kickoff_time=time_value,
                    kickoff_date=kickoff_date,
                    competition=_competition_for(home, away),
                    is_pleno=match_number == PLENO_MATCH,
                    source="eduardolosilla.es",
                )
            )
    return fixtures


def _merge_matches(
    existing: Iterable[Match], downloaded: Iterable[Match]
) -> list[Match]:
    by_key: dict[tuple[dt.date, str, str, str], Match] = {}
    for match in existing:
        by_key[(match.date, match.league, match.home_team, match.away_team)] = match
    for match in downloaded:
        by_key[(match.date, match.league, match.home_team, match.away_team)] = match
    return sorted(by_key.values(), key=lambda item: item.date)


def _current_season(now: Optional[dt.date] = None) -> str:
    now = now or dt.date.today()
    start = now.year if now.month >= 7 else now.year - 1
    return f"{start % 100:02d}{(start + 1) % 100:02d}"


def _download_football_data(league: str, season: str, timeout: int = 60) -> Optional[str]:
    direct = f"https://www.football-data.co.uk/mmz4281/{season}/{league}.csv"
    proxy = (
        "https://r.jina.ai/http://www.football-data.co.uk/mmz4281/"
        f"{season}/{league}.csv"
    )
    for url, attempt_timeout in ((direct, min(timeout, 12)), (proxy, timeout)):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=attempt_timeout) as response:
                text = response.read().decode("utf-8-sig", errors="ignore")
            if "Div," in text and "HomeTeam" in text:
                return text
        except Exception:
            continue
    return None


_manager: Optional[QuinielaDataManager] = None
_manager_lock = threading.Lock()


def get_quiniela_data_manager() -> QuinielaDataManager:
    """Singleton del gestor de datos de La Quiniela."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = QuinielaDataManager()
    return _manager
