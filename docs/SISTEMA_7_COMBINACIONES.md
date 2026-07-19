# 🎯 Sistema de 7 Combinaciones Semanales

## 🎱 Funcionalidad Implementada

**Sistema completo para generar 7 combinaciones estratégicas diferentes** para cada sorteo semanal de El Gordo de la Primitiva.

## 🚀 Características Principales

### 1. **7 Estrategias Diferentes**
Cada combinación usa un enfoque distinto:

1. **Ensemble** - Predicción principal del ensemble ML
2. **Conservadora** - Números calientes (históricamente más frecuentes)
3. **Equilibrada** - Mezcla de números calientes y fríos
4. **Arriesgada** - Números fríos (históricamente menos frecuentes)
5. **Patrones** - Basada en análisis de patrones históricos
6. **Aleatoria Optimizada** - Aleatoria con pesos probabilísticos
7. **Diversificada** - Mínimo solapamiento con otras combinaciones

### 2. **Sistema Interactivo**
- ✅ Seleccionar/deseleccionar combinaciones
- ✅ Ver coste total en tiempo real (1.50€ por apuesta)
- ✅ Análisis de cobertura y solapamiento
- ✅ Recomendaciones personalizadas

### 3. **Métricas Avanzadas**
- **Cobertura de números**: Porcentaje de números únicos cubiertos
- **Solapamiento promedio**: Números compartidos entre combinaciones
- **Distribución de riesgo**: Análisis conservativo/equilibrado/arriesgado
- **Presupuesto optimizado**: Asignación por niveles de confianza

## 📊 API Endpoints

### Obtener Combinaciones Semanales
```http
GET /api/v1/combinations/weekly?num_combinations=7
```

**Respuesta:**
```json
{
  "draw_date": "2026-07-19",
  "combinations": [
    {
      "numbers": [6, 14, 28, 46, 53],
      "key_number": 6,
      "strategy": "ensemble",
      "confidence": 0.68,
      "description": "Predicción principal del ensemble ML",
      "risk_level": "balanced"
    },
    // ... 6 combinaciones más
  ],
  "coverage_metrics": {
    "unique_numbers_coverage": 75.9,
    "avg_combination_overlap": 1.2,
    "risk_distribution": {
      "conservative": 1,
      "balanced": 5,
      "risky": 1
    }
  },
  "recommendations": {
    "play_strategy": "balanced",
    "budget_allocation": {
      "high_confidence": 3,
      "medium_confidence": 3,
      "low_confidence": 1
    },
    "best_combinations": [...],
    "warnings": []
  }
}
```

### Optimizar Combinaciones Existentes
```http
POST /api/v1/combinations/optimize
{
  "existing_combinations": [[1,2,3,4,5], [6,7,8,9,10]],
  "key_numbers": [0, 1],
  "num_new_combinations": 3
}
```

### Comparar Estrategias
```http
GET /api/v1/combinations/compare
```

## 💡 Estrategias Explicadas

### 1. **Ensemble** (Predicción Principal)
- **Fuente**: Ensemble de modelos Transformer + LSTM
- **Enfoque**: Mejor predicción general del sistema
- **Confianza**: Alta (0.60-0.75)
- **Ideal para**: Jugadores que quieren la predicción más sólida

### 2. **Conservadora** (Números Calientes)
- **Fuente**: Análisis de frecuencias históricas
- **Enfoque**: Números que más han salido históricamente
- **Confianza**: Media-Alta (0.60-0.70)
- **Ideal para**: Perfiles prudentes que prefieren estadística

### 3. **Equilibrada** (Mezcla)
- **Fuente**: Combinación de frecuencias + probabilidades
- **Enfoque**: 2 calientes + 2 medios + 1 frío
- **Confianza**: Media (0.50-0.60)
- **Ideal para**: Jugadores que quieren diversificación

### 4. **Arriesgada** (Números Fríos)
- **Fuente**: Análisis de números menos frecuentes
- **Enfoque**: Números "dueños" que tocan salir
- **Confianza**: Media-Baja (0.30-0.45)
- **Ideal para**: Perfiles arriesgados buscando grandes premios

### 5. **Patrones** (Pattern-Based)
- **Fuente**: Análisis de patrones históricos
- **Enfoque**: Rangos, consecutivos, tendencias
- **Confianza**: Media (0.45-0.55)
- **Ideal para**: Jugadores que creen en patrones

### 6. **Aleatoria Optimizada** (Random Optimized)
- **Fuente**: Aleatoriedad con pesos probabilísticos
- **Enfoque**: Random pero influenciado por ML
- **Confianza**: Media (0.40-0.50)
- **Ideal para**: Quienes quieren suerte con inteligencia

### 7. **Diversificada** (Min Overlap)
- **Fuente**: Optimización de cobertura
- **Enfoque**: Mínimo solapamiento con otras combinaciones
- **Confianza**: Media-Baja (0.35-0.45)
- **Ideal para**: Maximizar cobertura de números

## 🎮 Cómo Usar el Sistema

### 1. **Obtener Combinaciones**
```
POST /api/v1/combinations/weekly?num_combinations=7
```

### 2. **Seleccionar tus Favoritas**
- Haz clic en las tarjetas para seleccionar/deseleccionar
- El sistema muestra el coste total en tiempo real
- Recomendación: Selecciona 4-5 combinaciones

### 3. **Copiar y Jugar**
- Usa el botón "Copiar Combinaciones"
- Juega tus combinaciones seleccionadas
- Coste: 1.50€ por combinación

## 📈 Métricas de Calidad

### Cobertura de Números
- **Bueno**: >60% de números únicos cubiertos
- **Excelente**: >75% de cobertura
- **Perfecto**: >85% de cobertura

### Solapamiento
- **Óptimo**: 0.8-1.5 números promedio
- **Alto**: >2 números (demasiado similar)
- **Bajo**: <0.5 (demasiado disperso)

### Distribución de Riesgo
- **Conservador**: 3+ combinaciones conservadoras
- **Equilibrado**: Mix de todos los tipos
- **Arriesgado**: 2+ combinaciones arriesgadas

## 💰 Estrategia de Presupuesto

### Recomendación por Nivel de Juego

**Nivel Bajo (1-3 combinaciones):**
- 1 Ensemble (principal)
- 1 Conservadora (seguridad)
- 1 Equilibrada (diversificación)
- **Coste**: 4.50€

**Nivel Medio (4-5 combinaciones):**
- 1 Ensemble
- 1 Conservadora
- 1 Equilibrada
- 1 Patrones
- 1 Aleatoria Optimizada
- **Coste**: 7.50€

**Nivel Alto (6-7 combinaciones):**
- Todas las estrategias
- Máxima diversificación
- **Coste**: 10.50€

## 🎯 Ventajas del Sistema

1. **Diversificación**: 7 enfoques diferentes
2. **Optimización**: Balance entre riesgo y recompensa
3. **Transparencia**: Sabes exactamente qué estrategia usa cada combinación
4. **Flexibilidad**: Selecciona las que prefieras
5. **Economía**: Control total del presupuesto
6. **Análisis**: Métricas de cobertura y solapamiento
7. **Recomendaciones**: Consejos personalizados

## 🚀 Próximas Mejoras

- [ ] Sistema de apuestas recurrentes
- [ ] Análisis de resultados históricos de combinaciones
- [ ] Optimización de presupuesto por temporada
- [ ] Integración con sistemas de_notificación
- [ ] Comparación con resultados reales

---

**Sistema completo y listo para usar en `/weekly-combinations`** ✅

**Coste total de 7 combinaciones: 10.50€ por sorteo semanal**
