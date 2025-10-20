# 🛠️ Guía de Herramientas - Platzi Downloader

## 📌 Herramienta Principal: `platzi_manager.py`

**Herramienta consolidada** que reemplaza y mejora las herramientas antiguas:
- ✅ Compatible con el sistema de trazabilidad v2.0
- ✅ Interfaz clara y consistente
- ✅ Múltiples funcionalidades integradas
- ✅ Soporte para dry-run (vista previa)

---

## 🚀 Uso Rápido

### Ver Estado de Descargas
```bash
python platzi_manager.py --status
```
Muestra:
- Estadísticas completas (cursos/unidades completadas, fallidas, pendientes)
- Cursos con trabajo pendiente
- Errores recientes
- Recomendaciones

### Ver Estado Detallado
```bash
python platzi_manager.py --status --verbose
```

### Listar Todos los Cursos
```bash
python platzi_manager.py --list-courses
```

### Listar Solo Cursos Fallidos
```bash
python platzi_manager.py --list-courses --filter-status failed
```

### Reintentar Descargas Fallidas
```bash
python platzi_manager.py --retry-failed
```
Marca todas las unidades fallidas como "pending" para que se reintenten en la próxima descarga.

### Resetear un Curso Para Re-descargarlo
```bash
# Encuentra el curso por nombre (búsqueda parcial)
python platzi_manager.py --reset-course "python"

# Vista previa (sin cambios)
python platzi_manager.py --reset-course "python" --dry-run
```

**Casos de uso:**
- Eliminaste accidentalmente una carpeta de curso
- Quieres descargar el curso con mejor calidad
- El curso fue actualizado en Platzi

### Limpiar Tracking de Archivos Borrados
```bash
# Vista previa (no hace cambios)
python platzi_manager.py --clean-tracking --dry-run

# Limpiar realmente
python platzi_manager.py --clean-tracking
```

**Qué hace:**
- Busca cursos marcados como "completed" en el JSON
- Verifica si las carpetas existen en disco
- Elimina del JSON los que no tienen archivos
- Así puedes re-descargarlos

---

## 📋 Tabla de Opciones

| Opción | Descripción | Ejemplo |
|--------|-------------|---------|
| `--status` | Muestra estado actual | `python platzi_manager.py --status` |
| `--verbose, -v` | Modo detallado | `python platzi_manager.py --status -v` |
| `--retry-failed` | Reintenta fallidas | `python platzi_manager.py --retry-failed` |
| `--reset-course PATRÓN` | Resetea curso | `python platzi_manager.py --reset-course "javascript"` |
| `--clean-tracking` | Limpia tracking | `python platzi_manager.py --clean-tracking` |
| `--list-courses` | Lista cursos | `python platzi_manager.py --list-courses` |
| `--filter-status STATUS` | Filtra por estado | `python platzi_manager.py --list-courses --filter-status failed` |
| `--dry-run` | Vista previa | `python platzi_manager.py --clean-tracking --dry-run` |
| `--checkpoint FILE` | Archivo custom | `python platzi_manager.py --status --checkpoint my_progress.json` |

---

## 🎯 Casos de Uso Comunes

### 1. Eliminaste una Carpeta de Curso Accidentalmente

**Problema:** Borraste `Courses/Curso de Python` pero el JSON dice que está completado.

**Solución:**
```bash
# Opción A: Limpiar tracking (elimina del JSON)
python platzi_manager.py --clean-tracking

# Opción B: Resetear el curso específico
python platzi_manager.py --reset-course "python"

# Luego re-descarga
platzi download https://platzi.com/cursos/python/
```

### 2. Verificar Qué Falta Por Descargar

```bash
# Ver estado general
python platzi_manager.py --status

# Ver solo cursos con problemas
python platzi_manager.py --list-courses --filter-status failed
python platzi_manager.py --list-courses --filter-status in_progress
```

### 3. Muchas Unidades Fallaron (403, 500, etc.)

```bash
# Reintentar todas
python platzi_manager.py --retry-failed

# Luego continuar descarga
platzi download https://platzi.com/cursos/tu-curso/
```

### 4. Quieres Re-descargar un Curso Actualizado

```bash
# Resetear curso
python platzi_manager.py --reset-course "react"

# Re-descargar
platzi download https://platzi.com/cursos/react/
```

### 5. Sincronizar JSON con Archivos Reales

**Escenario:** Has movido/borrado archivos manualmente y el JSON está desactualizado.

```bash
# Ver qué se limpiaría
python platzi_manager.py --clean-tracking --dry-run

# Limpiar
python platzi_manager.py --clean-tracking
```

---

## 🔄 Flujo de Trabajo Típico

### Continuar Descarga Interrumpida

1. **Ver estado:**
   ```bash
   python platzi_manager.py --status
   ```

2. **Si hay fallidas, reintentarlas:**
   ```bash
   python platzi_manager.py --retry-failed
   ```

3. **Continuar descarga:**
   ```bash
   platzi download <URL>
   ```

### Limpiar y Reorganizar

1. **Listar todo:**
   ```bash
   python platzi_manager.py --list-courses
   ```

2. **Limpiar entradas inválidas:**
   ```bash
   python platzi_manager.py --clean-tracking
   ```

3. **Resetear cursos específicos:**
   ```bash
   python platzi_manager.py --reset-course "curso-viejo"
   ```

---

## 📊 Interpretando el Estado

### Estados de Cursos/Unidades

| Estado | Significado | Acción Automática |
|--------|-------------|-------------------|
| `completed` | ✅ Descargado exitosamente | Se omite |
| `failed` | ❌ Falló la descarga | Se reintenta si usas `--retry-failed` |
| `in_progress` | 🔄 Se interrumpió | Se marca como `pending` al inicio y se reintenta |
| `pending` | ⏸️ Pendiente de descarga | Se descarga |

### Salida del Estado

```
📊 DOWNLOAD STATUS - Platzi Downloader
================================================================================

📅 Session Info:
   Started: 2025-10-13 18:00:00
   Last updated: 2025-10-13 19:30:00
   Tracker version: 2.0
   Last validation: 2025-10-13 19:00:00

📈 Statistics:
   📚 Courses: 8/10 completed
      ❌ Failed: 1
      🔄 In progress: 1
   📝 Units: 95/100 completed
      ❌ Failed: 3
      🔄 In progress: 2

⏳ Courses with Pending Work (2):
   • Curso de Python: 3 units pending
   • Curso de JavaScript: 2 units pending

❌ Recent Errors (5 total, showing last 5):
   • [UNIT] Decoradores avanzados
     Error downloading video: 403 Forbidden...

💡 Recommendations:
   • Run with --retry-failed to retry failed downloads
   • Run 'platzi download <URL>' to continue incomplete courses
```

---

## ⚠️ Archivos Antiguos (Deprecados)

Los siguientes archivos son **antiguos y no se actualizan**. Usa `platzi_manager.py` en su lugar:

| Archivo Antiguo | Reemplazo en platzi_manager.py |
|----------------|-------------------------------|
| `compare_html.py` | ❌ Ya no necesario (sistema mejorado) |
| `check_status.py` | `--status` |
| `check_pending_units.py` | `--status` + `--list-courses` |
| `clean_tracking.py` | `--clean-tracking` |
| `manage_downloads.py` | Herramienta completa |

**Los archivos antiguos se mantendrán por compatibilidad pero no recibirán mejoras.**

---

## 💡 Tips

### Usar con Custom Checkpoint
```bash
python platzi_manager.py --status --checkpoint backup_progress.json
```

### Dry-Run (Vista Previa) para Operaciones Destructivas
Siempre usa `--dry-run` primero:
```bash
# Ver qué se resetearía
python platzi_manager.py --reset-course "python" --dry-run

# Ver qué se limpiaría
python platzi_manager.py --clean-tracking --dry-run
```

### Combinar con Otros Comandos
```bash
# Ver estado y listar fallidos
python platzi_manager.py --status
python platzi_manager.py --list-courses --filter-status failed

# Reintentar y descargar
python platzi_manager.py --retry-failed
platzi download URL
```

---

## 🔐 Seguridad

- ✅ **Siempre crea backup** antes de modificar el checkpoint
- ✅ Backup se guarda como: `download_progress.json.backup`
- ✅ Usa `--dry-run` para ver cambios antes de aplicarlos

---

## 🆘 Solución de Problemas

### "Checkpoint file not found"
**Causa:** No has ejecutado ninguna descarga aún.
**Solución:** Ejecuta `platzi download <URL>` primero.

### "No courses matching 'pattern' found"
**Causa:** El patrón de búsqueda no coincide.
**Solución:** Usa `--list-courses` para ver nombres exactos, luego busca con parte del nombre.

### "Could not create backup"
**Causa:** Permisos de escritura o disco lleno.
**Solución:** Verifica permisos y espacio en disco.

---

## 📖 Más Información

- Ver: [PROGRESS_TRACKING.md](./PROGRESS_TRACKING.md) - Sistema de trazabilidad
- Ver: [MEJORAS_TRAZABILIDAD.md](./MEJORAS_TRAZABILIDAD.md) - Mejoras implementadas
- Ver: [README.md](./README.md) - Documentación principal

---

**🎉 ¡Disfruta de una gestión de descargas más eficiente!**
