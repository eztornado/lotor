"""
Datos históricos de Bonoloto.

Fuente principal: hojas públicas de Lotoideas (resultados oficiales de SELAE).
El CSV incluido en `backend/data/raw/bonoloto_historical.csv` contiene todos
los sorteos desde 1988 y se puede actualizar con `refresh()`.

Reglas del juego:
  - 6 números del 1 al 49.
  - 1 número complementario (solo interviene en la 2ª categoría).
  - 1 reintegro del 0 al 9.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from loguru import logger

POOL_SIZE = 49
PICK_SIZE = 6
REINTEGRO_SIZE = 10

GOOGLE_SHEETS = (
    # Sorteos desde 2013 hasta hoy.
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vQALTRaLDFfhXOAQmeONPqmFKm9yOiQ4W97rhWgR41BZ7czFsjK5YktD6fnETKHGB9YUnyQ4XBSbhZx"
    "/pub?gid=0&single=true&output=csv",
    # Sorteos desde 1988 hasta 2012.
    "https://docs.google.com/spreadsheets/d/e/"
    "2PACX-1vQALTRaLDFfhXOAQmeONPqmFKm9yOiQ4W97rhWgR41BZ7czFsjK5YktD6fnETKHGB9YUnyQ4XBSbhZx"
    "/pub?gid=1&single=true&output=csv",
)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)

DRAW_CUTOFF_HOUR = 21  # Bonoloto se sortea por la noche (21:30 aprox.)


@dataclass(frozen=True, slots=True)
class Draw:
    date: dt.date
    numbers: tuple[int, ...]
    complementario: Optional[int]
    reintegro: Optional[int]
    source: str = "local"

    @property
    def is_valid(self) -> bool:
        return (
            len(self.numbers) == PICK_SIZE
            and len(set(self.numbers)) == PICK_SIZE
            and all(1 <= number <= POOL_SIZE for number in self.numbers)
            and (
                self.complementario is None
                or 1 <= self.complementario <= POOL_SIZE
            )
            and (
                self.reintegro is None
                or 0 <= self.reintegro < REINTEGRO_SIZE
            )
        )


def _candidate_data_dirs() -> list[Path]:
    """Posibles ubicaciones del directorio de datos (local y Docker)."""
    service_file = Path(__file__).resolve()
    return [
        service_file.parents[2] / "data",  # backend/data
        Path.cwd() / "data",               # /app/data en Docker
        Path.cwd() / "backend" / "data",   # ejecutando desde la raíz del repo
    ]


def _default_data_dir() -> Path:
    for directory in _candidate_data_dirs():
        if (directory / "raw" / "bonoloto_historical.csv").exists():
            return directory
    return _candidate_data_dirs()[0]


def _parse_date(raw: str) -> dt.date:
    value = raw.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return dt.date.fromisoformat(value)


def _parse_optional_int(raw: str) -> Optional[int]:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def _row_to_draw(row: dict[str, str], source: str = "local") -> Optional[Draw]:
    """Convierte una fila CSV en un sorteo validado."""
    try:
        date = _parse_date(row.get("date") or row.get("fecha") or "")
        numbers = [
            int(row.get(f"n{index}") or row.get(f"numero{index}") or 0)
            for index in range(1, PICK_SIZE + 1)
        ]
        complementario = _parse_optional_int(
            row.get("complementario") or row.get("comp") or ""
        )
        reintegro = _parse_optional_int(
            row.get("reintegro") or row.get("r") or row.get("key_number") or ""
        )
    except (TypeError, ValueError):
        return None

    draw = Draw(
        date=date,
        numbers=tuple(sorted(numbers)),
        complementario=complementario,
        reintegro=reintegro,
        source=source,
    )
    return draw if draw.is_valid else None


def parse_lotoideas_csv(text: str) -> list[Draw]:
    """Parsea una de las hojas CSV publicadas por Lotoideas."""
    draws: list[Draw] = []
    reader = csv.reader(io.StringIO(text))
    next(reader, None)  # cabecera

    for raw in reader:
        if not raw or not raw[0].strip():
            continue
        try:
            date = dt.datetime.strptime(raw[0].strip(), "%d/%m/%Y").date()
            numbers = tuple(sorted(int(value) for value in raw[1:7]))
            complementario = int(raw[7]) if len(raw) > 7 and raw[7].strip() else None
            reintegro = int(raw[8]) if len(raw) > 8 and raw[8].strip() else None
        except (ValueError, IndexError):
            continue

        draw = Draw(
            date=date,
            numbers=numbers,
            complementario=complementario,
            reintegro=reintegro,
            source="lotoideas_selae",
        )
        if draw.is_valid:
            draws.append(draw)

    return draws


def merge_draws(*groups: Iterable[Draw]) -> list[Draw]:
    """Une sorteos, elimina duplicados y ordena del más reciente al más antiguo."""
    by_date: dict[dt.date, Draw] = {}
    for group in groups:
        for draw in group:
            previous = by_date.get(draw.date)
            if previous is None or (
                previous.reintegro is None and draw.reintegro is not None
            ):
                by_date[draw.date] = draw
    return sorted(by_date.values(), key=lambda item: item.date, reverse=True)


def next_bonoloto_date(
    last_draw: Optional[dt.date] = None,
    now: Optional[dt.datetime] = None,
) -> dt.date:
    """
    Calcula la fecha del próximo sorteo de Bonoloto.

    Bonoloto se sortea de lunes a sábado. Si el último sorteo del dataset es
    de hoy, el siguiente es el próximo día no domingo. Si aún no se ha
    celebrado el sorteo de hoy, se devuelve hoy.
    """
    now = now or dt.datetime.now()
    today = now.date()

    if last_draw is not None and last_draw >= today:
        candidate = last_draw + dt.timedelta(days=1)
    elif last_draw is not None and last_draw == today - dt.timedelta(days=1):
        # El último dato es de ayer: hoy puede ser el próximo sorteo.
        candidate = today
    elif last_draw is not None and last_draw < today - dt.timedelta(days=1):
        # Dataset desactualizado: usamos hoy como referencia.
        candidate = today
    else:
        candidate = today

    # Si es hoy y ya ha pasado la hora habitual del sorteo, pasamos a mañana.
    if candidate == today and now.hour >= DRAW_CUTOFF_HOUR:
        candidate += dt.timedelta(days=1)

    while candidate.weekday() == 6:  # domingo: no hay Bonoloto
        candidate += dt.timedelta(days=1)

    return candidate


class BonolotoDataManager:
    """Carga, valida y actualiza el histórico de Bonoloto."""

    def __init__(self, data_dir: Optional[str | Path] = None):
        self.data_dir = Path(data_dir) if data_dir else _default_data_dir()
        self.csv_path = self.data_dir / "raw" / "bonoloto_historical.csv"
        self._draws: Optional[list[Draw]] = None
        self._lock = threading.Lock()

    def load(self, force: bool = False) -> list[Draw]:
        """Carga los sorteos desde el CSV local (cacheado en memoria)."""
        if self._draws is not None and not force:
            return self._draws

        with self._lock:
            if self._draws is not None and not force:
                return self._draws

            if not self.csv_path.exists():
                logger.error(f"No existe el dataset de Bonoloto: {self.csv_path}")
                self._draws = []
                return self._draws

            draws: list[Draw] = []
            try:
                with self.csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                    for row in csv.DictReader(handle):
                        draw = _row_to_draw(row)
                        if draw is not None:
                            draws.append(draw)
            except Exception as exc:  # pragma: no cover - defensivo
                logger.error(f"Error leyendo el dataset de Bonoloto: {exc}")
                draws = []

            self._draws = merge_draws(draws)
            logger.info(
                f"Bonoloto: {len(self._draws)} sorteos cargados "
                f"({self._draws[-1].date if self._draws else 'sin datos'} → "
                f"{self._draws[0].date if self._draws else 'sin datos'})"
            )
            return self._draws

    def refresh(self, timeout: int = 60) -> dict:
        """Descarga las hojas públicas y actualiza el CSV local."""
        downloaded: list[Draw] = []
        errors: list[str] = []

        for url in GOOGLE_SHEETS:
            try:
                request = urllib.request.Request(
                    url, headers={"User-Agent": USER_AGENT}
                )
                with urllib.request.urlopen(request, timeout=timeout) as response:
                    text = response.read().decode("utf-8-sig")
                downloaded.extend(parse_lotoideas_csv(text))
            except Exception as exc:  # pragma: no cover - red
                errors.append(str(exc))
                logger.warning(f"No se pudo descargar una hoja de Bonoloto: {exc}")

        if not downloaded:
            logger.error("No se pudo actualizar Bonoloto desde ninguna fuente")
            return {
                "status": "error",
                "errors": errors,
                "total_draws": len(self.load()),
            }

        merged = merge_draws(downloaded, self.load())
        self._write(merged)
        self._draws = merged
        logger.info(
            f"Bonoloto actualizado: {len(merged)} sorteos "
            f"({merged[-1].date} → {merged[0].date})"
        )
        return {
            "status": "success",
            "downloaded": len(downloaded),
            "total_draws": len(merged),
            "date_range": {
                "from": merged[-1].date.isoformat(),
                "to": merged[0].date.isoformat(),
            },
            "errors": errors,
        }

    def _write(self, draws: list[Draw]) -> None:
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.csv_path.with_suffix(".csv.tmp")
        with temporary.open("w", encoding="utf-8", newline="") as handle:
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
                        draw.date.isoformat(),
                        *draw.numbers,
                        draw.complementario if draw.complementario is not None else "",
                        draw.reintegro if draw.reintegro is not None else "",
                        draw.source,
                    ]
                )
        temporary.replace(self.csv_path)

    def summary(self) -> dict:
        draws = self.load()
        if not draws:
            return {"total_draws": 0, "date_range": None, "next_draw": None}

        return {
            "total_draws": len(draws),
            "date_range": {
                "from": draws[-1].date.isoformat(),
                "to": draws[0].date.isoformat(),
            },
            "last_draw": {
                "date": draws[0].date.isoformat(),
                "numbers": list(draws[0].numbers),
                "complementario": draws[0].complementario,
                "reintegro": draws[0].reintegro,
            },
            "next_draw": next_bonoloto_date(draws[0].date).isoformat(),
            "source": draws[0].source,
        }


_manager: Optional[BonolotoDataManager] = None
_manager_lock = threading.Lock()


def get_bonoloto_data_manager() -> BonolotoDataManager:
    """Singleton del gestor de datos de Bonoloto."""
    global _manager
    if _manager is None:
        with _manager_lock:
            if _manager is None:
                _manager = BonolotoDataManager()
    return _manager
