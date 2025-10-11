# 🛠️ Guía de Uso - Platzi Downloader

Guía rápida y práctica para gestionar tus descargas.

---

## 🚀 Inicio Rápido

```powershell
# Todo en uno: Activar entorno + Abrir gestor
.\.venv\Scripts\Activate.ps1; python manage_downloads.py
```

---

## 📋 Herramientas

| Script | Función | Uso |
|--------|---------|-----|
| `manage_downloads.py` | ⭐ Gestor interactivo | Todo en uno |
| `check_status.py` | Ver estado detallado | Estadísticas |
| `check_pending_units.py` | Ver cursos con pendientes | Diagnóstico |
| `retry_failed.py` | Reintentar errores | Antes de continuar |
| `help.py` | Ayuda rápida | Referencia |

---

## 🎯 Flujos Comunes

### Nueva Descarga
```powershell
.\.venv\Scripts\Activate.ps1
platzi batch-download
```

### Detener y Continuar
```
1. [Ctrl + C] para detener
2. python retry_failed.py
3. platzi batch-download
```

### Ver Progreso
```powershell
python check_status.py
```

---

## 💡 Tips

- El progreso se guarda automáticamente
- No re-descarga lo completado
- Detecta pendientes automáticamente
- `Ctrl + C` es seguro

---

Ver **README.md** para documentación completa.
