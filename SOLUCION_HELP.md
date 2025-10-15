# Solución al Problema: `platzi --help` No Funcionaba

## 🐛 Problema
El comando `platzi --help` fallaba con el siguiente error:
```
TypeError: Parameter.make_metavar() missing 1 required positional argument: 'ctx'
```

## 🔍 Causa Raíz
El problema fue causado por una **incompatibilidad entre versiones**:
- **Typer 0.13.1** + **Click 8.3.0** = ❌ Error
- La versión Click 8.3.0 introdujo un cambio incompatible con el código de Typer que genera la ayuda visual (rich formatting)

## ✅ Solución
Se bajó la versión de Click a **8.1.7**, que es compatible con Typer 0.13.1:
- **Typer 0.13.1** + **Click 8.1.7** = ✅ Funciona

### Cambios Realizados
1. **Instalación de Click 8.1.7**:
   ```powershell
   .\.venv\Scripts\pip.exe install click==8.1.7
   ```

2. **Actualización de pyproject.toml**:
   Se agregó una restricción de versión para Click:
   ```toml
   [tool.poetry.dependencies]
   typer = "^0.13.0"
   click = "^8.1.7"  # <- NUEVO: Previene la actualización a 8.3.0
   ```

## 🎯 Cómo Usar el Comando Ahora

### Activar el Entorno Virtual
```powershell
.\.venv\Scripts\Activate.ps1
```

### Ver Ayuda General
```powershell
platzi --help
```

### Ver Ayuda de Comandos Específicos
```powershell
platzi login --help
platzi download --help
platzi batch-download --help
platzi retry-failed --help
platzi clear-cache --help
platzi clean-tracking --help
```

## 📚 Comandos Disponibles

| Comando | Descripción |
|---------|-------------|
| `login` | Abre el navegador para iniciar sesión en Platzi |
| `logout` | Elimina la sesión de Platzi del almacenamiento local |
| `download <url>` | Descarga un curso específico de Platzi |
| `batch-download [archivo]` | Descarga múltiples cursos desde un archivo de texto |
| `retry-failed` | Reintenta descargar todos los cursos/unidades que fallaron |
| `clear-cache` | Limpia el caché de Platzi CLI |
| `clean-tracking` | Limpia datos de seguimiento de archivos no existentes |

## 🔄 Para Evitar Este Problema en el Futuro

Si reinstalas las dependencias, asegúrate de que el archivo `pyproject.toml` tenga la restricción de versión de Click:

```toml
click = "^8.1.7"
```

Esto evitará que pip/poetry instale versiones incompatibles automáticamente.

## ✨ Estado Actual
- ✅ `platzi --help` funciona correctamente
- ✅ Todos los subcomandos funcionan correctamente
- ✅ La ayuda visual (rich formatting) se muestra sin errores
- ✅ El archivo `pyproject.toml` está actualizado para prevenir el problema

---
**Fecha de solución**: 2025-10-14
