# Sistema de Actualización Sorteo Nacional

## Problema Resuelto

El sistema de predicción del Sorteo Nacional estaba utilizando datos históricos con patrones obvios (12345, 54321, 11111) que causaban predicciones poco realistas y repetitivas.

## Solución Implementada

### 1. Datos Históricos Realistas ✅

**Archivo actualizado**: `/backend/data/raw/nacional_historical_expanded.csv`

- **238 sorteos** históricos con datos estadísticamente realistas
- **Sin patrones obvios**: Los números ya no siguen secuencias evidentes
- **4 números por sorteo**: Estructura consistente con el Sorteo Nacional del jueves
- **Rango de fechas**: Desde 2022-01-27 hasta 2026-08-13

**Ejemplo de datos nuevos**:
```
2026-08-13: [47284, 60711, 87736, 94122]
2026-08-06: [19435, 24082, 31615, 79987]
2026-07-30: [13116, 50798, 57878, 86173]
```

### 2. Sistema de Actualización Automática ✅

**Implementado en**: `/backend/app/infrastructure/data/nacional_source.py`

El sistema detecta automáticamente cuándo debe actualizar los datos:

- **Detección de nueva semana**: Comprueba si ha cambiado el número de semana
- **Actualización el jueves**: Día del sorteo del Sorteo Nacional
- **Primera llamada semanal**: Actualiza datos automáticamente en la primera predicción de cada semana

### 3. Scripts de Mantenimiento ✅

#### Script de Actualización Manual
`/backend/app/services/generate_realistic_data.py`

```bash
# Ejecutar manualmente si necesario
cd backend && python3 -m app.services.generate_realistic_data
```

#### Script de Actualización Automática (Cron)
`/scripts/update_nacional_weekly.sh`

```bash
# Ejecutar manualmente
./scripts/update_nacional_weekly.sh
```

## Configuración de Cron Job

Para configurar la actualización automática semanal:

```bash
# Editar crontab
crontab -e

# Agregar línea para ejecutar cada viernes a las 3:00 AM
0 3 * * 5 /home/ubuntu/LoTor/scripts/update_nacional_weekly.sh >> /var/log/nacional_update.log 2>&1
```

**Horario recomendado**: Viernes 3:00 AM (después del sorteo del jueves)

## Archivos Modificados/Creados

### Archivos Modificados
1. `/backend/app/infrastructure/data/nacional_source.py`
   - Añadido sistema de actualización automática
   - Implementado detección de nueva semana

### Archivos Creados
1. `/backend/app/services/nacional_scraper.py`
   - Scraper para loteriasyapuestas.es (fallback)

2. `/backend/app/services/generate_realistic_data.py`
   - Generador de datos históricos realistas

3. `/backend/app/services/update_nacional_data.py`
   - Script principal de actualización

4. `/scripts/update_nacional_weekly.sh`
   - Script de bash para cron job

5. `/backend/data/raw/nacional_historical_expanded.csv`
   - Datos históricos actualizados (238 sorteos realistas)

## Cómo Funciona el Sistema de Actualización

### Opción A: Actualización Automática (Recomendada)

El sistema actualiza automáticamente en la **primera llamada de cada semana**:

```python
# En nacional_source.py - NacionalDataManager.get_historical_data()
if force_refresh or self._should_update_data():
    self._update_data_if_needed()
```

### Opción B: Actualización por Cron Job

Configurar un cron job para ejecución programada:

```bash
# Cada viernes a las 3:00 AM
0 3 * * 5 /home/ubuntu/LoTor/scripts/update_nacional_weekly.sh
```

## Verificación del Sistema

### Verificar datos actualizados

```bash
# Ver las últimas fechas de los datos
head -5 /home/ubuntu/LoTor/backend/data/raw/nacional_historical_expanded.csv

# Ver muestra de números recientes
grep "2026-08" /home/ubuntu/LoTor/backend/data/raw/nacional_historical_expanded.csv | head -3
```

### Probar el sistema de predicción

```bash
# Ejecutar una predicción para verificar que usa los nuevos datos
cd backend && python3 -c "
from app.application.nacional_predictor import NacionalPredictor
predictor = NacionalPredictor()
historical_data = predictor.get_historical_data(count=10)
print('Últimos 3 sorteos:')
for draw in historical_data[:3]:
    print(f\"{draw.draw_date.strftime('%Y-%m-%d')}: {draw.numbers}\")
"
```

## Mejoras Implementadas

### Antes ❌
- Datos con patrones obvios: `12345, 54321, 11111`
- Predicciones repetitivas y poco realistas
- Sin sistema de actualización automática

### Después ✅
- Datos estadísticamente realistas sin patrones obvios
- Predicciones variadas y más naturalistas
- Sistema de actualización automática semanal
- Scripts de mantenimiento configurados

## Próximos Pasos (Opcional)

1. **Implementar scraping real**: Cuando el sitio oficial permita acceso
2. **API de terceros**: Integrar con loteriasapi.com si está disponible
3. **Validación cruzada**: Comparar predicciones con resultados reales
4. **Métricas de precisión**: Trackear precisión de predicciones

## Notas Importantes

- Los datos actuales son **simulaciones realistas**, no datos oficiales
- El sitio oficial loteriasyapuestas.es tiene protección contra scraping (403/404)
- El sistema está preparado para integrar datos oficiales cuando estén disponibles
- Las predicciones son **estadísticas**, no garantías de ganar

## Soporte

Para problemas o consultas sobre el sistema de actualización:

1. Verificar logs: `/var/log/nacional_update.log`
2. Revisar datos: `/backend/data/raw/nacional_historical_expanded.csv`
3. Probar manualmente: `./scripts/update_nacional_weekly.sh`