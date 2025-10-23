# 🔖 Versionado Automático

Este proyecto utiliza **Semantic Versioning** con versionado automático basado en los mensajes de commit.

## 🚀 Cómo Funciona

Cada vez que haces push a la rama `master`, GitHub Actions:

1. **Analiza** todos los commits desde el último release
2. **Determina** el tipo de versión según los commits:
   - `feat:` → versión MINOR (0.7.0 → **0.8.0**)
   - `fix:` o `perf:` → versión PATCH (0.7.0 → **0.7.1**)
   - `BREAKING CHANGE:` → versión MAJOR (0.7.0 → **1.0.0**)
3. **Actualiza** automáticamente:
   - `pyproject.toml` - versión de Poetry
   - `src/platzi/__init__.py` - variable `__version__`
4. **Crea** un tag git (ej: `v0.8.0`)
5. **Genera** el CHANGELOG automáticamente
6. **Publica** el paquete a PyPI
7. **Crea** un GitHub Release con notas

## 📝 Formato de Commits

Usa **Conventional Commits**:

```
<tipo>(<scope>): <descripción>

[cuerpo opcional]
[footer opcional]
```

### Ejemplos Prácticos

```bash
# Nueva funcionalidad (MINOR bump)
git commit -m "feat(downloader): agregar soporte para 1080p"

# Corrección de bug (PATCH bump)  
git commit -m "fix(auth): resolver timeout en login"

# Mejora de rendimiento (PATCH bump)
git commit -m "perf(m3u8): optimizar descarga de fragmentos"

# Breaking change (MAJOR bump)
git commit -m "feat!: cambiar API de configuración

BREAKING CHANGE: el archivo de config ahora es YAML en lugar de JSON"

# Sin release (documentación)
git commit -m "docs: actualizar README con ejemplos"
```

## 📊 Tipos de Commits

| Tipo | Bump | Genera Release | Ejemplo |
|------|------|----------------|---------|
| `feat` | MINOR | ✅ | Nueva funcionalidad |
| `fix` | PATCH | ✅ | Corrección de bug |
| `perf` | PATCH | ✅ | Optimización |
| `docs` | - | ❌ | Documentación |
| `style` | - | ❌ | Formato código |
| `refactor` | - | ❌ | Refactorización |
| `test` | - | ❌ | Tests |
| `build` | - | ❌ | Build system |
| `ci` | - | ❌ | CI/CD |
| `chore` | - | ❌ | Mantenimiento |

## 🎯 Casos de Uso

### Caso 1: Agregar nueva funcionalidad

```bash
git checkout -b feat/descargar-subtitulos
# ... hacer cambios ...
git add .
git commit -m "feat(subtitles): agregar descarga de subtítulos en múltiples idiomas"
git push origin feat/descargar-subtitulos
# Crear PR y merge a master
# → Resultado: v0.7.0 → v0.8.0
```

### Caso 2: Corregir bug urgente

```bash
git checkout -b fix/rate-limiting
# ... hacer cambios ...
git add .
git commit -m "fix(m3u8): resolver HTTP 429 reduciendo batch size"
git push origin fix/rate-limiting
# Merge a master
# → Resultado: v0.7.0 → v0.7.1
```

### Caso 3: Breaking change

```bash
git checkout -b feat/nueva-api
# ... hacer cambios incompatibles ...
git add .
git commit -m "feat!: rediseñar API de AsyncPlatzi

BREAKING CHANGE: AsyncPlatzi.download() ahora requiere parámetro 'output_dir'"
git push origin feat/nueva-api
# Merge a master
# → Resultado: v0.7.0 → v1.0.0
```

### Caso 4: Múltiples cambios en un PR

```bash
# Si un PR tiene múltiples commits, el bump será el mayor:
git commit -m "fix: corregir bug en login"        # PATCH
git commit -m "feat: agregar modo offline"       # MINOR
git commit -m "docs: actualizar guía"            # -
# → Resultado: MINOR bump (feat tiene prioridad)
```

## 🔍 Ver la Versión Actual

### Desde Python
```python
import platzi
print(platzi.__version__)  # "0.7.0"
```

### Desde CLI
```bash
platzi --version
```

### Desde Git
```bash
git describe --tags --abbrev=0  # v0.7.0
```

## 🛠️ Configuración para Desarrolladores

### Instalar pre-commit hooks (recomendado)

```bash
poetry add --group dev pre-commit commitizen
poetry install
pre-commit install
```

Esto validará automáticamente tus mensajes de commit.

### Usar commitizen para commits interactivos

```bash
cz commit
```

Te guiará paso a paso para crear un commit válido.

## 🚦 Estado del Release

Puedes ver el estado del último release en:
- **GitHub Actions**: `.github/workflows/release.yml`
- **GitHub Releases**: https://github.com/ivansaul/platzi-downloader/releases
- **PyPI**: https://pypi.org/project/platzi/

## 📋 CHANGELOG

El CHANGELOG se genera automáticamente en cada release basado en los commits:
- https://github.com/ivansaul/platzi-downloader/blob/master/CHANGELOG.md

## ⚙️ Saltar CI

Si necesitas hacer un commit sin trigger CI:

```bash
git commit -m "docs: actualizar README [skip ci]"
```

## 🔒 Revertir un Release

Si necesitas revertir:

```bash
# Revertir commit
git revert <commit-sha>
git push

# Borrar tag (no recomendado si ya se publicó)
git tag -d v0.8.0
git push origin :refs/tags/v0.8.0
```

## 📚 Referencias

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Python Semantic Release Docs](https://python-semantic-release.readthedocs.io/)
- [Guía de Contribución](./CONTRIBUTING.md)
