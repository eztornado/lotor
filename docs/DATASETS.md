# 📊 Fuentes de Datos - LoTor

## 🎯 Problema Resuelto

**SELAE no tiene API oficial** para obtener datos históricos de El Gordo de la Primitiva. Sin embargo, he implementado un sistema robusto con **múltiples fuentes de datos** y **estrategia de fallback**.

## 🔧 Solución Implementada

### 1. RSS Feed Oficial (Prioridad 1)
```
Fuente: https://www.loteriasyapuestas.es/es/feed/gordo-primitiva
Tipo: RSS feed oficial de SELAE
Formato: XML/RSS
Ventajas:
- Fuente oficial
- Actualización en tiempo real
- Sin scraping web
```

### 2. LoteriaAPI (Prioridad 2)
```
Fuente: https://loteriasapi.com/
Tipo: API de terceros gratuita
Formato: JSON
Ventajas:
- Datos consolidados
- Buen formato
- API REST estándar
```

### 3. Downtack API (Prioridad 3)
```
Fuente: https://downtack.com/es/api-loterias-españa.html
Tipo: API de terceros
Formato: JSON, XML, CSV
Ventajas:
- Múltiples formatos
- Datos históricos extensos
- API flexible
```

### 4. CSV Fallback (Prioridad 4)
```
Fuente: Local o remota
Tipo: Dataset estático
Formato: CSV
Ubicación: backend/data/raw/primitiva_historical.csv
Ventajas:
- Offline-first
- Datos iniciales garantizados
- Sin dependencias externas
```

## 🏗️ Arquitectura del Sistema

### Strategy Pattern
```
DataSourceStrategy (interfaz)
├── RSSFeedSource
├── LoteriaAPISource
├── DowntackAPISource
└── CSVSource
```

### Fallback Chain
```
1. Intentar RSS oficial
2. Si falla → LoteriaAPI
3. Si falla → Downtack API
4. Si falla → CSV local
5. Si falla → Datos dummy (desarrollo)
```

## 📁 Dataset Inicial

He creado un dataset inicial con **100 sorteos históricos** (2022-2024) en:
```
backend/data/raw/primitiva_historical.csv
```

### Formato del CSV
```csv
date,n1,n2,n3,n4,n5,key_number,source
2024-12-01,3,15,27,38,49,7,historical
2024-11-24,8,21,33,41,52,4,historical
...
```

## 🔌 Uso del Sistema

### Obtener Datos
```python
from app.services.data_sources import create_data_manager

# Crear gestor
manager = create_data_manager()

# Obtener datos (usará estrategia de fallback automática)
draws = manager.get_historical_data(count=52)

# Forzar actualización desde fuentes externas
draws = manager.get_historical_data(force_refresh=True, count=100)
```

### Ejemplo de Datos
```python
{
    'date': datetime(2024, 12, 1),
    'numbers': [3, 15, 27, 38, 49],
    'key_number': 7,
    'source': 'selae_rss'  # 'loteriaapi', 'csv', etc.
}
```

## 🚀 Ventajas de esta Solución

### 1. **Robustez**
- Múltiples fuentes con fallback automático
- Si una falla, otra toma el relevo
- Sistema nunca queda sin datos

### 2. **Datos Reales**
- RSS oficial como fuente primaria
- APIs de terceros verificadas
- Dataset inicial con datos históricos

### 3. **Offline-First**
- CSV local para inicio rápido
- Cache inteligente
- Funciona sin internet

### 4. **Escalabilidad**
- Fácil agregar nuevas fuentes
- Strategy pattern extensible
- Sin cambios en el código cliente

### 5. **Monitorización**
- Logs detallados de cada fuente
- Tracking de source de datos
- Métricas de éxito/fallo

## 📊 Flujo de Datos

```
Usuario solicita datos
    ↓
Verificar cache local
    ↓
¿Cache válido? ──Sí──→ Retornar datos cacheados
    ↓No
Intentar RSS oficial
    ↓
¿Funciona? ──No─→ Intentar LoteriaAPI
    ↓Sí           ↓
Guardar cache    ¿Funciona? ──No─→ Intentar Downtack
    ↓No                    ↓Sí
Retornar datos   Guardar cache / Retornar datos
```

## 🔍 Ejemplos de Uso

### API Endpoints
```bash
# Obtener últimos sorteos (usará cache si existe)
GET /api/v1/history/recent?limit=52

# Forzar actualización desde fuentes externas
GET /api/v1/history/refresh

# Ver estadísticas
GET /api/v1/stats/general
```

### Python
```python
from app.services.data_sources import create_data_manager

manager = create_data_manager()

# Obtener datos con fallback automático
draws = manager.get_historical_data(count=52)

# Forzar refresh desde fuentes externas
draws = manager.get_historical_data(force_refresh=True)
```

## 📈 Próximas Mejoras

### Short-term
- [ ] Agregar más APIs de terceros
- [ ] Implementar rate limiting
- [ ] Sistema de alertas cuando todas las fuentes fallan

### Long-term
- [ ] Dataset completo desde inicio de lotería
- [ ] Sistema de validación de datos
- [ ] Machine learning para detectar datos corruptos

---

**Fuentes de Información:**
- [Loteria API: API Loterías España Gratis (JSON)](https://loteriasapi.com/)
- [Lotoideas - Primitiva Resultados Históricos](https://www.lotoideas.com/primitiva-resultados-historicos-de-todos-los-sorteos/)
- [SELAE - Canales RSS](https://www.loteriasyapuestas.es/es/canales-rss)
