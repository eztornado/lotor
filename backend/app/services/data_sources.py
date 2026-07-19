import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Optional
from loguru import logger
import pandas as pd
from pathlib import Path


class DataSourceStrategy:
    """Strategy pattern para diferentes fuentes de datos"""

    def fetch_draws(self, count: int = 200) -> List[dict]:
        """Obtener últimos N sorteos"""
        raise NotImplementedError


class RSSFeedSource(DataSourceStrategy):
    """Fuente RSS oficial de SELAE"""

    RSS_URL = "https://www.loteriasyapuestas.es/es/feed/gordo-primitiva"

    def __init__(self):
        self.session = requests.Session()

    def fetch_draws(self, count: int = 200) -> List[dict]:
        """Obtener sorteos desde RSS feed"""
        logger.info(f"Fetching {count} draws from RSS feed")

        try:
            feed = feedparser.parse(self.RSS_URL)
            draws = []

            for entry in feed.entries[:count]:
                # Parsear fecha del título o contenido
                published = datetime(*entry.published_parsed[:6])

                # Extraer números del contenido/description
                numbers = self._parse_rss_content(entry.description)

                if numbers:
                    draws.append({
                        'date': published,
                        'numbers': numbers['main'][:5],
                        'key_number': numbers.get('key', 0),
                        'source': 'selae_rss'
                    })

            logger.info(f"Fetched {len(draws)} draws from RSS")
            return draws

        except Exception as e:
            logger.error(f"Error fetching RSS: {e}")
            return []

    def _parse_rss_content(self, content: str) -> Optional[dict]:
        """Parsear contenido RSS para extraer números"""
        import re

        try:
            # Buscar patrones de números en el texto
            numbers = re.findall(r'\b(\d{1,2})\b', content)

            if len(numbers) >= 6:
                return {
                    'main': [int(n) for n in numbers[:5]],
                    'key': int(numbers[5]) if len(numbers) > 5 else 0
                }
            return None

        except Exception as e:
            logger.error(f"Error parsing RSS content: {e}")
            return None


class LoteriaAPISource(DataSourceStrategy):
    """API de terceros: LoteriaAPI.com"""

    BASE_URL = "https://api.loteriasapi.com"

    def fetch_draws(self, count: int = 200) -> List[dict]:
        """Obtener sorteos desde LoteriaAPI"""
        logger.info(f"Fetching {count} draws from LoteriaAPI")

        try:
            # Endpoint para El Gordo de la Primitiva
            url = f"{self.BASE_URL}/gordo-primitiva"
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            data = response.json()
            draws = []

            # Procesar según formato de la API
            if 'sorteos' in data or 'draws' in data:
                results = data.get('sorteos', data.get('draws', []))

                for result in results[:count]:
                    draw = self._parse_api_result(result)
                    if draw:
                        draws.append(draw)

            logger.info(f"Fetched {len(draws)} draws from LoteriaAPI")
            return draws

        except Exception as e:
            logger.error(f"Error fetching from LoteriaAPI: {e}")
            return []

    def _parse_api_result(self, result: dict) -> Optional[dict]:
        """Parsear resultado de la API"""
        try:
            # Ajustar según el formato real de LoteriaAPI
            date_str = result.get('fecha') or result.get('date')
            numbers = result.get('numeros') or result.get('numbers', [])
            key = result.get('clave') or result.get('key') or result.get('reintegro', 0)

            if date_str and numbers:
                return {
                    'date': datetime.fromisoformat(date_str.replace('Z', '+00:00')),
                    'numbers': numbers[:5],
                    'key_number': key,
                    'source': 'loteriaapi'
                }
            return None

        except Exception as e:
            logger.error(f"Error parsing API result: {e}")
            return None


class DowntackAPISource(DataSourceStrategy):
    """API de terceros: Downtack"""

    BASE_URL = "https://api.downtack.com/loteria"

    def fetch_draws(self, count: int = 200) -> List[dict]:
        """Obtener sorteos desde Downtack API"""
        logger.info(f"Fetching {count} draws from Downtack")

        try:
            url = f"{self.BASE_URL}/gordo-primitiva"
            params = {
                'limit': count,
                'format': 'json'
            }

            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()
            draws = []

            for result in data.get('results', data.get('sorteos', []))[:count]:
                draw = self._parse_api_result(result)
                if draw:
                    draws.append(draw)

            logger.info(f"Fetched {len(draws)} draws from Downtack")
            return draws

        except Exception as e:
            logger.error(f"Error fetching from Downtack: {e}")
            return []

    def _parse_api_result(self, result: dict) -> Optional[dict]:
        """Parsear resultado de Downtack"""
        try:
            date_str = result.get('fecha') or result.get('date')
            numbers = result.get('combinacion') or result.get('numbers', [])
            key = result.get('numeroClave') or result.get('key', 0)

            if date_str and numbers:
                return {
                    'date': datetime.fromisoformat(date_str.replace('Z', '+00:00')),
                    'numbers': numbers[:5] if isinstance(numbers, list) else list(numbers)[:5],
                    'key_number': key,
                    'source': 'downtack'
                }
            return None

        except Exception as e:
            logger.error(f"Error parsing Downtack result: {e}")
            return None


class CSVSource(DataSourceStrategy):
    """Fuente CSV local o remota"""

    def __init__(self, csv_path: Optional[str] = None, csv_url: Optional[str] = None):
        self.csv_path = csv_path
        self.csv_url = csv_url

    def fetch_draws(self, count: int = 200) -> List[dict]:
        """Cargar sorteos desde CSV"""
        logger.info(f"Loading draws from CSV")

        try:
            if self.csv_url:
                # Descargar CSV remoto
                response = requests.get(self.csv_url, timeout=30)
                response.raise_for_status()
                df = pd.read_csv(pd.io.common.StringIO(response.text))
            elif self.csv_path:
                # Cargar CSV local
                df = pd.read_csv(self.csv_path)
            else:
                logger.error("No CSV path or URL provided")
                return []

            draws = []
            for _, row in df.head(count).iterrows():
                draw = self._parse_csv_row(row)
                if draw:
                    draws.append(draw)

            logger.info(f"Loaded {len(draws)} draws from CSV")
            return draws

        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            return []

    def _parse_csv_row(self, row: pd.Series) -> Optional[dict]:
        """Parsear fila de CSV"""
        try:
            # Soportar múltiples formatos de CSV
            date = row.get('date') or row.get('fecha') or row.get('DATE')
            numbers = [
                row.get('n1') or row.get('numero1') or row.get('N1'),
                row.get('n2') or row.get('numero2') or row.get('N2'),
                row.get('n3') or row.get('numero3') or row.get('N3'),
                row.get('n4') or row.get('numero4') or row.get('N4'),
                row.get('n5') or row.get('numero5') or row.get('N5'),
            ]
            key = row.get('key_number') or row.get('clave') or row.get('KEY') or 0

            if date and all(numbers):
                return {
                    'date': pd.to_datetime(date),
                    'numbers': [int(n) for n in numbers],
                    'key_number': int(key),
                    'source': 'csv'
                }
            return None

        except Exception as e:
            logger.error(f"Error parsing CSV row: {e}")
            return None


class RobustDataManager:
    """Gestor robusto de datos con múltiples fuentes y fallback"""

    def __init__(self, data_dir: str = "./backend/data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Inicializar fuentes en orden de preferencia
        self.sources = [
            RSSFeedSource(),           # 1. RSS oficial (más fiable)
            LoteriaAPISource(),        # 2. API LoteriaAPI
            DowntackAPISource(),       # 3. API Downtack
        ]

        # CSV fallback con dataset completo actualizado (2022-2026)
        self.csv_source = CSVSource(
            csv_path=f"{data_dir}/raw/primitiva_historical_complete.csv",
            csv_url="https://raw.githubusercontent.com/loterias-data/primitiva-historica/main/sorteos.csv"
        )

    def get_historical_data(self, force_refresh: bool = False, count: int = 200) -> List[dict]:
        """Obtener datos históricos con estrategia de fallback"""

        # Intentar cargar del cache primero
        if not force_refresh:
            cached = self._load_from_cache()
            if cached:
                logger.info(f"Loaded {len(cached)} draws from cache")
                return cached

        # Intentar cada fuente en orden
        all_draws = []

        for source in self.sources:
            try:
                draws = source.fetch_draws(count=count)
                if draws:
                    all_draws.extend(draws)
                    logger.info(f"Successfully fetched from {source.__class__.__name__}")

                    # Guardar en cache
                    self._save_to_cache(all_draws)
                    return all_draws

            except Exception as e:
                logger.warning(f"Failed to fetch from {source.__class__.__name__}: {e}")
                continue

        # Si todas las fuentes fallan, intentar CSV
        if not all_draws:
            logger.warning("All sources failed, trying CSV fallback")
            all_draws = self.csv_source.fetch_draws(count=count)

            if all_draws:
                self._save_to_cache(all_draws)
                return all_draws

        # Si todo falla, generar datos dummy para desarrollo
        if not all_draws:
            logger.error("All data sources failed, generating dummy data for development")
            all_draws = self._generate_dummy_data(count)

        return all_draws

    def _load_from_cache(self) -> Optional[List[dict]]:
        """Cargar desde cache local"""
        cache_file = self.data_dir / "raw" / "primitiva_historical.csv"

        if cache_file.exists():
            try:
                df = pd.read_csv(cache_file)
                draws = []

                for _, row in df.iterrows():
                    draws.append({
                        'date': pd.to_datetime(row['date']),
                        'numbers': [row['n1'], row['n2'], row['n3'], row['n4'], row['n5']],
                        'key_number': row['key_number'],
                        'source': row.get('source', 'cache')
                    })

                return draws

            except Exception as e:
                logger.error(f"Error loading cache: {e}")

        return None

    def _save_to_cache(self, draws: List[dict]):
        """Guardar en cache local"""
        cache_file = self.data_dir / "raw" / "primitiva_historical.csv"

        try:
            df_data = []
            for draw in draws:
                df_data.append({
                    'date': draw['date'].strftime('%Y-%m-%d'),
                    'n1': draw['numbers'][0],
                    'n2': draw['numbers'][1],
                    'n3': draw['numbers'][2],
                    'n4': draw['numbers'][3],
                    'n5': draw['numbers'][4],
                    'key_number': draw['key_number'],
                    'source': draw.get('source', 'unknown')
                })

            df = pd.DataFrame(df_data)
            df = df.sort_values('date', ascending=False)
            df.to_csv(cache_file, index=False)

            logger.info(f"Saved {len(draws)} draws to cache")

        except Exception as e:
            logger.error(f"Error saving cache: {e}")

    def _generate_dummy_data(self, count: int) -> List[dict]:
        """Generar datos dummy para desarrollo"""
        import random

        draws = []
        current_date = datetime.now()

        for i in range(count):
            date = current_date - timedelta(weeks=i)
            # Ajustar al domingo
            days_since_sunday = (date.weekday() - 6) % 7
            date = date - timedelta(days=days_since_sunday)

            numbers = sorted(random.sample(range(1, 55), 5))
            key = random.randint(0, 9)

            draws.append({
                'date': date,
                'numbers': numbers,
                'key_number': key,
                'source': 'dummy_data'
            })

        return draws


# Factory function
def create_data_manager(data_dir: str = "./backend/data") -> RobustDataManager:
    """Crear gestor de datos"""
    return RobustDataManager(data_dir=data_dir)
