# 📊 Fuentes de datos - LoTor

## 🎯 Situación

**SELAE no ofrece una API histórica oficial**. Los generadores de carteras de
LoTor funcionan con **datasets CSV completos** y un importador reproducible
desde las hojas públicas de [Lotoideas](https://www.lotoideas.com/), que publican
los resultados oficiales de SELAE. Los endpoints legacy de predicción conservan
un sistema de fuentes con fallback.

## 📁 Datasets de los generadores

### El Gordo de la Primitiva

- **Fichero**: `backend/data/raw/gordo_historical.csv`
- **Formato**:

  ```csv
  date,n1,n2,n3,n4,n5,key_number,source
  2026-10-18,11,14,29,31,34,8,manual_selae
  2026-10-11,3,15,27,38,49,7,lotoideas_selae
  ```

- **Cobertura**: desde el **06/02/2005** (inicio del formato actual de 5 números
  + clave) hasta la última actualización. A fecha de esta documentación: **1.123
  sorteos** (18/10/2026).
- **Fuentes**: `manual_selae` para resultados añadidos a mano y
  `lotoideas_selae` para los importados.
- **Carga**: `app/services/gordo_data.py` valida cada sorteo (5 números únicos
  entre 1 y 54, clave entre 0 y 9, fecha única) y cachea el histórico en memoria.
- **Actualización**:

  ```bash
  # Importar desde la hoja pública y fusionar con el CSV local
  python backend/scripts/import_gordo.py

  # Solo validar/leer el CSV sin salir a la red
  python backend/scripts/import_gordo.py --offline
  ```

  También por API: `GET|POST /api/v1/gordo/refresh`.

### Bonoloto

- **Fichero**: `backend/data/raw/bonoloto_historical.csv`
- **Formato**:

  ```csv
  date,n1,n2,n3,n4,n5,n6,complementario,reintegro,source
  ```

- **Cobertura**: desde el **28/02/1988** (≈ 9.420 sorteos).
- **Carga**: `app/services/bonoloto_data.py`, con validación y caché en memoria.
- **Actualización**:

  ```bash
  python backend/scripts/import_bonoloto.py
  python backend/scripts/import_bonoloto.py --offline
  ```

  También por API: `GET|POST /api/v1/bonoloto/refresh`.

### Próximo sorteo

- **El Gordo**: `next_gordo_date()` avanza al siguiente **domingo** con corte de
  venta a las 21:00.
- **Bonoloto**: `next_bonoloto_date()` avanza al siguiente día natural saltando
  el domingo.

## 🔄 Flujo de actualización

```
Script / endpoint de refresh
    ↓
Descarga la hoja pública de Lotoideas
    ↓
Parsea y valida fechas, números y clave/reintegro
    ↓
Fusiona con el CSV local sin duplicar sorteos
    ↓
Guarda el CSV y limpia la caché en memoria
    ↓
La siguiente generación usa el histórico actualizado
```

Si la descarga falla, el CSV local sigue siendo la fuente de verdad y la API
responde con el error sin dejar el dataset a medias.

## 🧪 Validación

Los tests de cada juego comprueban:

- que todas las filas tienen el número correcto de columnas y rangos válidos,
- que no hay fechas duplicadas ni números repetidos dentro de un sorteo,
- que el dataset tiene cobertura suficiente para generar carteras,
- que el próximo sorteo se calcula correctamente.

```bash
cd backend
PYTHONPATH=. python -m pytest tests/test_gordo.py tests/test_bonoloto.py -q
```

## 🔌 Endpoints legacy de datos

La página de predicción IA usa los endpoints antiguos:

```bash
GET /api/v1/history/recent?limit=52
GET /api/v1/history/date/{date}
GET /api/v1/history/range
GET|POST /api/v1/history/refresh
GET /api/v1/stats/general
GET /api/v1/stats/number/{num}
GET /api/v1/stats/patterns
```

Estos endpoints mantienen la cadena de fallback (RSS/API de terceros/CSV) para
no romper la predicción legacy.

## 🔗 Fuentes

- [Lotoideas - El Gordo de la Primitiva](https://www.lotoideas.com/el-gordo-de-la-primitiva-resultados-historicos-de-todos-los-sorteos/)
- [Lotoideas - Bonoloto](https://www.lotoideas.com/bonoloto-resultados-historicos-de-todos-los-sorteos/)
- [SELAE](https://www.loteriasyapuestas.es/)
