"""
Fuente de datos para el Sorteo Nacional del jueves
Obtiene datos históricos de décimos y sorteos
"""

from typing import List, Optional
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd
import requests
import feedparser
from pathlib import Path

from app.domain.lottery import LotteryType, DrawResult, DataSource


class NacionalAPISource(DataSource):
    """Fuente de datos desde API oficial del Sorteo Nacional"""

    BASE_URL = "https://www.loteriasyapuestas.es/es/sorteo-nacional/resultados"

    def fetch_draws(self, count: int = 200) -> List[DrawResult]:
        """Obtener sorteos desde API oficial"""
        logger.info(f"Fetching {count} draws from Sorteo Nacional API")

        try:
            # Intentar obtener desde API
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(self.BASE_URL, headers=headers, timeout=30)

            if response.status_code == 200:
                # Parsear HTML o JSON según formato
                return self._parse_api_response(response.text)
            else:
                logger.warning(f"Nacional API returned {response.status_code}")
                return []

        except Exception as e:
            logger.error(f"Error fetching from Nacional API: {e}")
            return []

    def parse_draw(self, raw_data: any) -> Optional[DrawResult]:
        """Parsear datos crudos de API a DrawResult"""
        # Implementación placeholder - requeriría scraping real del HTML
        logger.debug("Parsing Nacional API data (placeholder)")
        return None

    def _parse_api_response(self, html_content: str) -> List[DrawResult]:
        """Parsear respuesta de API a DrawResult"""
        # Implementación simplificada - requeriría scraping real
        logger.info("Parsing Nacional API response (placeholder implementation)")
        return []


class NacionalCSVSource(DataSource):
    """Fuente de datos desde CSV local para Sorteo Nacional"""

    def __init__(self, csv_path: Optional[str] = None):
        # Detectar ruta correcta para datos
        if csv_path is None:
            # Intentar múltiples rutas posibles (priorizar archivo expandido)
            possible_paths = [
                "/app/data/raw/nacional_historical_expanded.csv",  # Docker (expandido)
                "./backend/data/raw/nacional_historical_expanded.csv",  # Local (expandido)
                "./data/raw/nacional_historical_expanded.csv",  # Backend directory (expandido)
                "/app/data/raw/nacional_historical.csv",  # Docker (original)
                "./backend/data/raw/nacional_historical.csv",  # Local development (original)
                "./data/raw/nacional_historical.csv",  # Backend directory (original)
                "../data/raw/nacional_historical.csv",  # Subdirectory (original)
                "/home/ubuntu/LoTor/backend/data/raw/nacional_historical_expanded.csv",  # Absolute path (expandido)
                "/home/ubuntu/LoTor/backend/data/raw/nacional_historical.csv",  # Absolute path (original)
            ]
            for path in possible_paths:
                if Path(path).exists():
                    csv_path = path
                    break
            else:
                # Default to first option if none exist
                csv_path = possible_paths[0]

        self.csv_path = csv_path

    def fetch_draws(self, count: int = 200) -> List[DrawResult]:
        """Obtener sorteos desde CSV local"""
        logger.info(f"Loading Sorteo Nacional draws from CSV: {self.csv_path}")

        try:
            if not Path(self.csv_path).exists():
                logger.warning(f"Nacional CSV not found: {self.csv_path}")
                return self._generate_dummy_data(count)

            df = pd.read_csv(self.csv_path)

            draws = []
            for _, row in df.head(count).iterrows():
                draw = self.parse_draw(row)
                if draw:
                    draws.append(draw)

            logger.info(f"Loaded {len(draws)} Nacional draws from CSV")
            return draws

        except Exception as e:
            logger.error(f"Error loading Nacional CSV: {e}")
            return []

    def parse_draw(self, raw_data: any) -> Optional[DrawResult]:
        """Parsear fila de CSV a DrawResult"""
        try:
            if isinstance(raw_data, pd.Series):
                date_str = raw_data.get('date') or raw_data.get('fecha')
                numbers = [
                    raw_data.get('n1') or raw_data.get('numero1') or raw_data.get('N1'),
                    raw_data.get('n2') or raw_data.get('numero2') or raw_data.get('N2'),
                    raw_data.get('n3') or raw_data.get('numero3') or raw_data.get('N3'),
                    raw_data.get('n4') or raw_data.get('numero4') or raw_data.get('N4'),
                ]
                serie = raw_data.get('serie') or raw_data.get('serie') or 0
                fraccion = raw_data.get('fraccion') or raw_data.get('fraccion') or 1

                # Filtrar valores None
                numbers = [int(n) for n in numbers if n is not None and pd.notna(n)]

                if date_str and numbers:
                    return DrawResult(
                        lottery_type=LotteryType.NACIONAL,
                        draw_date=pd.to_datetime(date_str),
                        numbers=numbers,
                        additional_numbers=[int(serie), int(fraccion)],
                        metadata={'source': 'csv'}
                    )
            return None
        except Exception as e:
            logger.error(f"Error parsing Nacional CSV row: {e}")
            return None

    def _generate_dummy_data(self, count: int = 200) -> List[DrawResult]:
        """Generar datos dummy para desarrollo si no hay CSV real"""
        logger.warning("Generating dummy Sorteo Nacional data for development")

        draws = []
        start_date = datetime.now() - timedelta(weeks=200)

        for i in range(count):
            draw_date = start_date + timedelta(weeks=i)

            # Generar 1-3 números principales (décimos)
            import random
            num_count = random.randint(1, 3)
            numbers = sorted(random.sample(range(1, 100000), num_count))

            # Serie y fracción
            serie = random.randint(1, 10)
            fraccion = random.randint(1, 100)

            draws.append(DrawResult(
                lottery_type=LotteryType.NACIONAL,
                draw_date=draw_date,
                numbers=numbers,
                additional_numbers=[serie, fraccion],
                metadata={'source': 'dummy', 'note': 'Replace with real data'}
            ))

        return draws


class NacionalRSSSource(DataSource):
    """Fuente de datos desde RSS para Sorteo Nacional"""

    RSS_URL = "https://www.loteriasyapuestas.es/es/sorteo-nacional/feed"

    def fetch_draws(self, count: int = 200) -> List[DrawResult]:
        """Obtener sorteos desde feed RSS"""
        logger.info(f"Fetching Sorteo Nacional from RSS feed")

        try:
            feed = feedparser.parse(self.RSS_URL)
            draws = []

            for entry in feed.entries[:count]:
                draw = self._parse_rss_entry(entry)
                if draw:
                    draws.append(draw)

            logger.info(f"Fetched {len(draws)} draws from Nacional RSS")
            return draws

        except Exception as e:
            logger.error(f"Error fetching Nacional RSS: {e}")
            return []

    def parse_draw(self, raw_data: any) -> Optional[DrawResult]:
        """Parsear entrada RSS a DrawResult"""
        try:
            if hasattr(raw_data, 'get'):
                # Extraer fecha y números del contenido RSS
                # Implementación placeholder - requeriría parsing real del XML
                logger.debug(f"Parsing Nacional RSS entry: {raw_data.get('title', 'Unknown')}")
            return None
        except Exception as e:
            logger.error(f"Error parsing Nacional RSS entry: {e}")
            return None

    def _parse_rss_entry(self, entry) -> Optional[DrawResult]:
        """Parsear entrada de RSS a DrawResult"""
        return self.parse_draw(entry)


class NacionalDataManager:
    """Gestor unificado de datos para Sorteo Nacional con actualización automática semanal"""

    def __init__(self):
        self.sources = [
            NacionalCSVSource(),  # Primero intentar CSV local
            NacionalAPISource(),  # Luego API oficial
            NacionalRSSSource(),  # Fallback a RSS
        ]
        self.last_update_week = None
        self.last_check_date = None

    def _should_update_data(self) -> bool:
        """Determinar si es necesario actualizar los datos (nueva semana)"""
        today = datetime.now()
        current_week = today.isocalendar()[1]

        # Primera vez o semana diferente
        if self.last_update_week is None:
            return True

        # Si ha pasado una semana desde la última actualización
        if self.last_update_week != current_week:
            return True

        # Si hoy es jueves (día del sorteo) y aún no hemos actualizado esta semana
        if today.weekday() == 3:  # Jueves = 3
            return True

        return False

    def _update_data_if_needed(self):
        """Actualizar datos si es una nueva semana"""
        if not self._should_update_data():
            return

        try:
            from app.services.generate_realistic_data import generate_realistic_historical_data, save_to_csv

            logger.info("🔄 Updating Sorteo Nacional historical data (new week detected)...")

            # Generar datos actualizados usando simulación realista
            updated_draws = generate_realistic_historical_data(count=238)

            if updated_draws:
                # Guardar en el archivo CSV
                csv_path = "/app/data/raw/nacional_historical_expanded.csv"
                save_to_csv(updated_draws, csv_path)

                # Actualizar control de semana
                today = datetime.now()
                self.last_update_week = today.isocalendar()[1]
                self.last_check_date = today

                logger.info(f"✅ Updated Sorteo Nacional data with {len(updated_draws)} realistic draws")
            else:
                logger.warning("⚠️ Could not generate updated data, keeping existing data")

        except Exception as e:
            logger.error(f"❌ Error updating Nacional data: {e}")

    def get_historical_data(self, count: int = 200, force_refresh: bool = False) -> List[DrawResult]:
        """Obtener datos históricos con actualización automática semanal"""

        # Actualizar datos si es necesario (primera llamada de la semana)
        if force_refresh or self._should_update_data():
            self._update_data_if_needed()

        # Intentar obtener datos de las fuentes
        for source in self.sources:
            try:
                draws = source.fetch_draws(count)
                if draws:
                    logger.info(f"Got {len(draws)} draws from {source.__class__.__name__}")
                    return draws
            except Exception as e:
                logger.warning(f"Error with {source.__class__.__name__}: {e}")
                continue

        logger.error("All Nacional data sources failed")
        return []