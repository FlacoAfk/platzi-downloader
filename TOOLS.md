# 🛠️ Herramientas de Gestión

Scripts para gestionar tus descargas de Platzi.

---

## ⭐ manage_downloads.py (RECOMENDADO)

Gestor interactivo con todas las funciones.

**Uso:**
```powershell
python manage_downloads.py
```

**Funciones:**
1. 📊 Ver estado actual
2. 🔄 Reintentar errores  
3. 🔍 Ver cursos con unidades pendientes
4. ▶️ Continuar/Iniciar descargas
5. 📝 Ver últimos errores
6. 🗑️ Limpiar historial de errores

---

## 📊 check_status.py

Muestra estado detallado de descargas con estadísticas completas.

**Uso:**
```powershell
python check_status.py
```

**Muestra:**
- Estadísticas generales (completadas/pendientes/errores)
- Rutas de aprendizaje en progreso
- Items pendientes y con error
- Recomendaciones automáticas

---

## � check_pending_units.py

Lista cursos con unidades pendientes (incluso si están marcados como "completed").

**Uso:**
```powershell
python check_pending_units.py
```

**Útil para:**
- Ver qué cursos se re-procesarán
- Identificar unidades que faltan
- Diagnóstico de pendientes

---

## 🔄 retry_failed.py

Resetea errores a "pending" para reintentarlos.

**Uso:**
```powershell
python retry_failed.py
platzi batch-download
```

**Hace:**
- Busca cursos/unidades con estado "failed"
- Cambia estado a "pending"
- Limpia mensajes de error
- Limpia historial de errores

**Cuándo usar:**
- Después de detener con Ctrl + C
- Cuando hay errores de conexión
- Para reintentar clases con Error 500

---

## ❓ help.py

Muestra ayuda rápida con comandos comunes.

**Uso:**
```powershell
python help.py           # Ayuda completa
python help.py --quick   # Inicio rápido
```

---

## � Más Información

- **README.md** - Documentación principal
- **GUIA.md** - Guía práctica de uso
- **FIX_UNIDADES_PENDIENTES.md** - Fix técnico importante
- **BATCH_DOWNLOAD.md** - Descarga por lotes

---

## � Flujo Recomendado

```powershell
# 1. Ver estado
python check_status.py

# 2. Si hay errores, reintentar
python retry_failed.py

# 3. Si hay pendientes, verificar
python check_pending_units.py

# 4. Continuar descargas
platzi batch-download
```

**O simplemente:**
```powershell
python manage_downloads.py
```
Y usa el menú interactivo. 🚀

