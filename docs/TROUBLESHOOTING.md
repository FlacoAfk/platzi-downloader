# 🔧 Solución de Problemas - Platzi Downloader

## 📋 Tabla de Contenidos

- [Problemas con Videos](#-problemas-con-videos)
- [Carpetas Vacías](#-carpetas-vacías)
- [Errores de Descarga](#-errores-de-descarga)
- [Problemas con el Tracking](#-problemas-con-el-tracking)
- [Otros Problemas](#-otros-problemas)

---

## 🎥 Problemas con Videos

### Error 403 Forbidden con Chromium (Videos DASH)

**Síntoma:**
```
ERROR: Error converting DASH to mp4: Error downloading DASH video:
Server returned 403 Forbidden (access denied)
```

**Causa:** Chromium no puede descargar videos en formato DASH (.mpd). Solo soporta HLS (.m3u8).

**Solución:**

#### Opción 1: Usar Firefox (Recomendado)
```bash
platzi download https://platzi.com/cursos/... --browser firefox
```
✅ **Ventajas:**
- Descarga TODOS los videos (m3u8 y mpd)
- No hay errores 403
- Funciona en modo headless (más rápido)

#### Opción 2: Reintentar con Firefox después de usar Chromium
```bash
# 1. Ver qué falló
python show_stats.py

# 2. Reintentar con Firefox
platzi retry-failed
platzi download URL --browser firefox
```

**Detección automática:** El sistema ahora detecta videos DASH-only con Chromium y los omite limpiamente, tratándolos como LECTURE en lugar de generar errores.

### Errores de m3u8 o ts

**Síntoma:**
```
Error downloading from .ts url
Error downloading m3u8
```

**Solución:**
```bash
# Elimina la carpeta temporal
rmdir /s .tmp

# Vuelve a ejecutar el comando
platzi download URL
```

### Video no se descarga (queda como LECTURE)

**Causa:** El video solo está disponible en formato DASH y usas Chromium.

**Solución:**
```bash
platzi download URL --browser firefox
```

---

## 📁 Carpetas Vacías

### Learning Paths 0/X pero marcadas como completadas

**Síntoma:**
```
✅ Desarrollo Frontend con React.js: 0/8 courses completed
```

**Causa:** Desincronización entre el JSON (dice "completado") y el disco (carpetas vacías).

**Diagnóstico:**
```bash
# Ver qué cursos están afectados
python show_stats.py
```

**Solución:**

#### Opción 1: Limpiar tracking automáticamente
```bash
# Vista previa (no modifica nada)
platzi clean-tracking --dry-run

# Limpiar tracking
platzi clean-tracking
```

Este comando:
- Busca cursos marcados como "completed" en el JSON
- Verifica si las carpetas existen en disco
- Elimina del JSON los que no tienen archivos
- Así puedes re-descargarlos

#### Opción 2: Ver qué carpetas están vacías
El sistema ahora distingue entre:
- **📁 Empty directory**: La carpeta existe pero está vacía
- **❌ Missing directory**: La carpeta ni siquiera existe

**Mensajes actualizados:**
```
📁 Empty directory (no files): Curso de React.js
📁 Empty directory (no files): Curso de Node.js
❌ Missing directory: Curso de Python

💡 Note: 2 course(s) have empty directories (no files inside)
   These directories exist but contain no downloaded content
```

### Borraste archivos manualmente

**Problema:** Eliminaste carpetas de cursos pero el JSON aún dice que están completados.

**Solución:**
```bash
# Limpiar tracking
platzi clean-tracking

# Re-descargar
platzi download URL
```

**Prevención:** No borres carpetas manualmente. Usa las herramientas:
```bash
# Para resetear un curso específico
python show_stats.py  # Buscar nombre exacto
platzi download URL   # Re-descargar
```

---

## ❌ Errores de Descarga

### Descargas interrumpidas (Ctrl+C)

**Solución:** El sistema automáticamente detecta y reintenta unidades interrumpidas.

```bash
# Simplemente vuelve a ejecutar
platzi download URL
```

El sistema:
- ✅ Omite unidades completadas
- 🔄 Reintenta unidades interrumpidas
- ❌ Reintenta unidades fallidas

### Error de conexión (ERR_CONNECTION_CLOSED)

**Síntoma:**
```
ERR_CONNECTION_CLOSED
Failed to download unit
```

**Solución automática:** El sistema reintenta hasta 3 veces por clase.

**Si persiste:**
```bash
# Reintentar fallidas manualmente
platzi retry-failed
platzi download URL
```

### Error 500 del servidor

**Solución:**
```bash
# Espera un momento y reintenta
platzi retry-failed
platzi download URL
```

### Muchas unidades fallaron

```bash
# Ver cuántas fallaron
python show_stats.py

# Listar solo fallidas
python show_stats.py --filter failed

# Reintentar todas
platzi retry-failed
platzi download URL
```

---

## 📊 Problemas con el Tracking

### "Checkpoint not found"

**Causa:** No has ejecutado ninguna descarga aún.

**Solución:** Ejecuta `platzi download <URL>` primero.

### "El JSON dice que está completo pero no veo los archivos"

**Causa:** Archivos borrados manualmente o descarga que falló silenciosamente.

**Solución:**
```bash
# Limpiar tracking
platzi clean-tracking

# Re-descargar
platzi download URL
```

### "Quiero empezar desde cero"

```bash
# Respalda el progreso actual (opcional)
copy download_progress.json download_progress.json.backup

# Borra el checkpoint
del download_progress.json

# Ejecuta de nuevo
platzi download URL
```

### Estadísticas incorrectas

**Si los contadores no coinciden:**

```bash
# Limpiar tracking sincroniza con archivos reales
platzi clean-tracking

# Ver estadísticas actualizadas
python show_stats.py
```

---

## 🔐 Problemas de Sesión

### "Not logged in" o "Session expired"

**Solución:**
```bash
# Cerrar sesión
platzi logout

# Volver a iniciar sesión
platzi login
```

### Browser no abre

**Chromium:**
```bash
playwright install chromium
```

**Firefox:**
```bash
playwright install firefox
```

---

## 🐛 Otros Problemas

### FFmpeg no encontrado

**Windows:**
```powershell
scoop install ffmpeg
```

**Linux/Ubuntu:**
```bash
sudo apt install ffmpeg -y
```

### Errores después de actualizar

**Solución:**
```bash
# Limpiar caché
platzi clear-cache

# Actualizar dependencias
pip install -U platzi

# Reinstalar playwright
playwright install firefox
```

### Archivos con caracteres especiales en nombres

**El sistema automáticamente limpia caracteres especiales.** Si tienes problemas:

```bash
# Limpiar caché y reintentar
platzi clear-cache
platzi download URL
```

### Disco lleno

**Síntoma:**
```
No space left on device
Error writing file
```

**Solución:**
1. Verifica espacio disponible
2. Elimina descargas innecesarias
3. Reintenta descarga

---

## 📚 Recursos Adicionales

- **[README.md](README.md)** - Documentación principal
- **[PROGRESS_TRACKING.md](PROGRESS_TRACKING.md)** - Sistema de trazabilidad
- **[TOOLS_GUIDE.md](TOOLS_GUIDE.md)** - Herramientas de gestión

---

## 💡 Consejos Generales

1. **Usa Firefox** para mejor compatibilidad con todos los formatos de video
2. **No borres archivos manualmente** - usa las herramientas de gestión
3. **Revisa el reporte** `download_report.txt` para ver errores detallados
4. **Usa `--dry-run`** antes de operaciones destructivas
5. **Haz backups** del JSON antes de modificarlo manualmente

---

## 🆘 ¿Aún tienes problemas?

1. Revisa el archivo `download_report.txt` para errores detallados
2. Ejecuta `python show_stats.py` para ver el estado actual
3. Usa `platzi clear-cache` si los problemas persisten después de actualizaciones
4. Reporta el issue en el repositorio con el mensaje de error completo
