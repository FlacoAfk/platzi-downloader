# Sistema de Trazabilidad - Platzi Downloader

> **Versión 2.0** - Sistema robusto de seguimiento de descargas con continuación inteligente

## 📋 Tabla de Contenidos

- [Características Principales](#-características-principales)
- [Uso Básico](#-uso-básico)
- [Funcionamiento](#-funcionamiento)
- [Estados de Unidades](#-estados-de-unidades)
- [Estructura del JSON](#-estructura-del-json)
- [Herramientas de Gestión](#-herramientas-de-gestión)
- [Troubleshooting](#-troubleshooting)
- [Compatibilidad](#-compatibilidad)

---

## ✨ Características Principales

### 🔄 Continuación Inteligente
- **Detección automática de descargas interrumpidas**: El sistema detecta unidades que estaban "en progreso" y las marca como "pendientes" para reintentar
- **Preservación de datos existentes**: Los datos del JSON son completamente retrocompatibles. No se pierden registros anteriores
- **Sincronización al inicio**: Cada vez que inicias una descarga, el sistema valida el estado y ajusta las unidades interrumpidas
- **Sistema de reintentos**: Hasta 3 intentos automáticos por clase con errores de conexión

### 📊 Manejo de Estados
El sistema maneja cuatro estados:
1. **COMPLETED** ✅: Unidad descargada exitosamente (se omite)
2. **FAILED** ❌: Unidad que falló (se reintenta automáticamente)
3. **IN_PROGRESS** 🔄: Unidad interrumpida (se marca como PENDING y se reintenta)
4. **PENDING** ⏸️: Pendiente de descarga

### 📈 Estadísticas Precisas
- **Contadores inteligentes**: No se duplican contadores cuando se reintenta una unidad/curso
- **Resumen al inicio**: Muestra cuántas unidades/cursos están completados, en progreso y fallidos
- **Reporte detallado**: Genera un reporte final con:
  - Cursos con unidades pendientes
  - Lista de unidades fallidas con errores
  - Estadísticas completas de la sesión
- **Validación automática**: Al iniciar, detecta unidades interrumpidas y las marca para reintento

## Funcionamiento

### Al Iniciar una Descarga

```
📂 Checkpoint loaded from download_progress.json
📊 Progress: 5/10 courses completed, 2 in progress, 1 failed
📊 Units: 45/98 completed, 3 in progress, 2 failed
🔍 Validating downloaded files...
🔄 Found interrupted unit: Introducción a Python
✅ Validation complete: 3 interrupted units will be retried
```

### Durante la Descarga

El sistema automáticamente:
- ✅ **Omite unidades completadas**
- 🔄 **Reintenta unidades fallidas** (con mensaje de advertencia del error anterior)
- 🔄 **Reintenta unidades interrumpidas** (marcadas como PENDING)
- 💾 **Guarda progreso después de cada unidad**

### Al Finalizar

Genera un reporte completo:
```
📊 DOWNLOAD PROGRESS REPORT
================================================================================
Session started: 2025-10-13T18:00:00
Last updated: 2025-10-13T19:30:00

📈 STATISTICS:
  Courses: 8/10 completed, 2 failed
  Units: 95/98 completed, 3 failed

❌ FAILED UNITS:
  - Curso de Python / Decoradores avanzados
    Error: Error downloading video: 403 Forbidden
  - Curso de JavaScript / Async/Await
    Error: Error collecting unit data: Server returned Error 500

⏳ COURSES WITH PENDING UNITS:
  - Curso de Python: 15/18 completed, 3 failed
```

## Estructura del JSON

### Metadata (Nueva)
```json
{
  "_metadata": {
    "version": "2.0",
    "last_validation": "2025-10-13T18:00:00"
  }
}
```

### Cursos y Unidades
```json
{
  "courses": {
    "/ruta/curso-python": {
      "title": "Curso de Python",
      "status": "in_progress",
      "started_at": "2025-10-13T18:00:00",
      "units": {
        "/clase/intro": {
          "title": "Introducción",
          "status": "completed",
          "completed_at": "2025-10-13T18:05:00"
        },
        "/clase/decoradores": {
          "title": "Decoradores",
          "status": "failed",
          "error": "Error downloading video: 403 Forbidden",
          "completed_at": "2025-10-13T18:10:00"
        }
      }
    }
  }
}
```

## Nuevas Funciones Disponibles

### `get_course_progress(course_id)`
Obtiene el progreso detallado de un curso:
```python
progress = tracker.get_course_progress("/cursos/python")
# {
#   "exists": True,
#   "status": "in_progress",
#   "total_units": 20,
#   "completed_units": 15,
#   "failed_units": 3,
#   "pending_units": 2,
#   "title": "Curso de Python"
# }
```

### `get_failed_units(course_id=None)`
Obtiene lista de unidades fallidas:
```python
failed = tracker.get_failed_units()
# [
#   {
#     "course_id": "/cursos/python",
#     "course_title": "Curso de Python",
#     "unit_id": "/clase/decoradores",
#     "unit_title": "Decoradores",
#     "error": "Error downloading video: 403 Forbidden",
#     "timestamp": "2025-10-13T18:10:00"
#   }
# ]
```

### `retry_failed_units(course_id=None)`
Marca unidades fallidas como pendientes para reintentar:
```python
# Reintentar todas las unidades fallidas
count = tracker.retry_failed_units()
# 🔄 Marked 5 failed units for retry

# Reintentar solo de un curso específico
count = tracker.retry_failed_units("/cursos/python")
# 🔄 Marked 3 failed units for retry
```

## Compatibilidad

✅ **100% Retrocompatible**: 
- Los JSON existentes se cargan sin problemas
- Los datos antiguos se preservan
- Los nuevos campos se agregan automáticamente
- No se pierden registros previos

✅ **Sin cambios disruptivos**:
- El flujo de descarga funciona igual que antes
- Las funciones existentes siguen funcionando
- Solo se agregan mejoras sin romper lo anterior

## 🚀 Uso Básico

### Descarga Normal
```bash
platzi download https://platzi.com/cursos/python/
```

**El sistema automáticamente:**
1. Carga el checkpoint anterior (si existe)
2. Muestra el progreso previo
3. Valida unidades interrumpidas
4. Omite lo ya completado
5. Reintenta lo fallido/interrumpido

### Continuar una Descarga Interrumpida
**No necesitas hacer nada especial.** Simplemente vuelve a ejecutar el comando:

```bash
platzi download https://platzi.com/ruta/desarrollo-web/
```

El sistema detectará:
- ✅ 45 unidades completadas → Se omiten
- 🔄 3 unidades interrumpidas → Se reintentan
- ❌ 2 unidades fallidas → Se reintentan

### Reintentar Descargas Fallidas
```bash
platzi retry-failed
```

### Ver Progreso
```bash
python show_stats.py
```

---

## 🎯 Estados de Unidades

| Estado | Icono | Descripción | Acción |
|--------|-------|-------------|--------|
| `completed` | ✅ | Descarga exitosa | Se omite |
| `in_progress` | 🔄 | Descarga interrumpida | Se marca como `pending` y se reintenta |
| `failed` | ❌ | Descarga falló | Se reintenta con advertencia del error anterior |
| `pending` | ⏸️ | Marcada para reintentar | Se descarga |

---

## 💡 Beneficios

1. **Resiliencia**: Continúa desde donde se quedó si se interrumpe
2. **Transparencia**: Sabes exactamente qué falló y por qué
3. **Eficiencia**: No re-descarga lo que ya está completo
4. **Trazabilidad**: Historial completo de intentos y errores
5. **Flexibilidad**: Puedes reintentar solo lo que falló
6. **Retrocompatible**: Funciona con tus datos existentes

---

## 🔧 Herramientas de Gestión

### `show_stats.py`
Muestra estadísticas detalladas del tracking.

```bash
python show_stats.py
```

### Otras Herramientas
Ver [TOOLS_GUIDE.md](TOOLS_GUIDE.md) para más herramientas de gestión avanzada.

---

## 🐛 Troubleshooting

### "Quiero reintentar solo las unidades fallidas"
**Ya está implementado.** El sistema automáticamente reintenta las unidades fallidas cuando vuelves a ejecutar la descarga.

### "¿Cómo sé qué falló?"
1. Revisa `download_report.txt` al finalizar
2. Busca la sección **"❌ FAILED UNITS"**
3. Cada error incluye el mensaje detallado

### "Quiero empezar desde cero"
```bash
# Respalda el progreso actual (opcional)
copy download_progress.json download_progress.json.backup

# Borra el checkpoint
del download_progress.json

# Ejecuta de nuevo
platzi download URL
```

### "¿Los archivos descargados se verifican?"
No. El sistema confía en el JSON. Si una unidad está marcada como `completed` en el JSON, se omite. Esto evita falsos negativos por cambios en nombres de archivos o estructura de carpetas.

Para más problemas comunes, ver [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## ✅ Compatibilidad

✅ **100% Retrocompatible**: 
- Los JSON existentes se cargan sin problemas
- Los datos antiguos se preservan
- Los nuevos campos se agregan automáticamente
- No se pierden registros previos

✅ **Sin cambios disruptivos**:
- El flujo de descarga funciona igual que antes
- Las funciones existentes siguen funcionando
- Solo se agregan mejoras sin romper lo anterior

---

## 📚 Más Información

- **[TOOLS_GUIDE.md](TOOLS_GUIDE.md)** - Guía completa de herramientas de gestión
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Solución de problemas comunes
- **[README.md](README.md)** - Documentación principal del proyecto
