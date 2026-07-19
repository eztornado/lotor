# 🔧 ACTUALIZACIÓN DE PRODUCCIÓN - Sorteos Históricos

## Problema Identificado

El frontend en `https://lotor.tornadocore.es/history` sigue mostrando solo 52 sorteos porque el contenedor en producción está usando una imagen anterior sin los cambios actualizados.

## Solución Implementada

✅ **Código actualizado localmente**:
- Backend: MAX_HISTORY_LENGTH = 200
- Frontend: HistoryPage actualizado a 200 sorteos  
- Datos: Archivo combinado con 211 sorteos (2022-2026)
- Imagen Docker: `lotor:updated-history` creada

## 🚀 Pasos para Actualizar Producción

### Opción 1: Coolify Auto-Deploy (RECOMENDADO)

1. **Verificar que Coolify detecte los cambios**:
   - Los archivos han sido actualizados en el repositorio
   - Coolify debería hacer un auto-deploy si está configurado

2. **Trigger manual en Coolify**:
   - Accede a tu panel de Coolify
   - Busca el proyecto "LoTor"
   - Click en "Deploy" o "Rebuild"
   - Espera a que termine el despliegue

### Opción 2: Verificación Post-Deploy

Una vez actualizado, verifica:

```bash
# Test de API
curl https://lotor.tornadocore.es/api/v1/history/recent
# Debería mostrar ~200 sorteos

# Test frontend
# Abre https://lotor.tornadocore.es/history
# Debería mostrar 200 sorteos en lugar de 52
```

## ✅ Validación Esperada

**ANTES** (versión actual en producción):
```json
{
  "sorteos_mostrados": 52,
  "rango": "2025-07-12 hasta 2026-07-12"
}
```

**DESPUÉS** (versión actualizada):
```json
{
  "sorteos_mostrados": 200,
  "rango": "2022-09-25 hasta 2026-07-19"
}
```

## 🔍 Debug si persiste el problema

Si después del deploy sigue mostrando 52 sorteos:

1. **Verificar logs del contenedor**:
   ```bash
   docker logs <container_id>
   # Buscar MAX_HISTORY_LENGTH o errores de carga
   ```

2. **Verificar archivos dentro del contenedor**:
   ```bash
   docker exec <container_id> ls -la /app/data/raw/
   # Debería mostrar primitiva_historical_complete.csv
   docker exec <container_id> wc -l /app/data/raw/primitiva_historical_complete.csv
   # Debería mostrar 212 líneas (211 sorteos + header)
   ```

3. **Test directo de la API**:
   ```bash
   curl https://lotor.tornadocore.es/api/v1/history/recent?limit=250
   ```

## 📊 Resumen de Cambios

**Archivos modificados**:
- `backend/app/core/config.py` - MAX_HISTORY_LENGTH: 52 → 200
- `backend/app/services/data_sources.py` - count: 52 → 200
- `backend/app/api/history.py` - limit: 52 → 200
- `frontend/src/components/HistoryPage.tsx` - getRecent(52) → getRecent(200)
- `backend/data/raw/primitiva_historical_complete.csv` - NUEVO archivo con 211 sorteos

**Nueva imagen Docker**: `lotor:updated-history`
- Incluye todos los cambios
- Lista para producción

## ⚡ Acción Inmediata

**Necesitas hacer un nuevo deploy en Coolify** para que los cambios se reflejen en `https://lotor.tornadocore.es/history`.

El código está listo y validado localmente, solo falta el despliegue en producción.