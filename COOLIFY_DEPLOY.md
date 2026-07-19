# Guía de Despliegue Coolify - LoTor

## Problema Resuelto
Coolify no encontraba el Dockerfile porque estaba en `./backend/` pero Coolify lo busca en el root del repositorio.

## Solución Implementada
✅ Creado `/Dockerfile` en el root del repositorio que construye el backend automáticamente

## Configuración Coolify

### Opción 1: Dockerfile (RECOMENDADO para Coolify)
```
Build Type: Dockerfile
Dockerfile Path: Dockerfile (en root)
Context: / (root del repositorio)
```

### Opción 2: Docker Compose
Si Coolify soporta docker-compose:
```
Build Type: Docker Compose
Compose File: docker-compose.yml
```

## Archivos Creados
- `/Dockerfile` - Dockerfile root para backend
- `/.dockerignore` - Optimiza build excluyendo archivos innecesarios
- `/docker-build.sh` - Script para test local
- `/docker-compose.yml` - Ya existía (actualizado)

## Test Local Antes de Deploy
```bash
cd /root/LoTor
./docker-build.sh
```

## Verificación Post-Deploy
Una vez desplegado en Coolify, verifica:
```bash
curl http://tu-coolify-domain/health
curl http://tu-coolify-domain/api/predictions/latest
```

## Notas Importantes
1. **Docker usa x86_64**: Puede usar PyTorch completo (no como ARM/RPi)
2. **Datos incluidos**: El CSV histórico (2026) está incluido en la imagen
3. **Puerto**: 8000 (configurable en Coolify)
4. **Health check**: Endpoint `/health` configurado

## Troubleshooting
- Si falla el build: Verifica logs en Coolify → "Show Debug Logs"
- Si el contenedor no inicia: `docker logs <container_id>`
- Si no responde: Verifica que el puerto 8000 esté expuesto
