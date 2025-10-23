# Guía de Contribución

## 📝 Convenciones de Commits

Este proyecto utiliza **[Conventional Commits](https://www.conventionalcommits.org/)** para el versionado automático.

### Formato del Commit

```
<tipo>(<scope>): <descripción breve>

[cuerpo opcional]

[footer opcional]
```

### Tipos de Commit

| Tipo | Descripción | Versión |
|------|-------------|---------|
| `feat` | Nueva funcionalidad | MINOR (0.x.0) |
| `fix` | Corrección de bug | PATCH (0.0.x) |
| `perf` | Mejora de rendimiento | PATCH (0.0.x) |
| `docs` | Cambios en documentación | No genera release |
| `style` | Formato de código (no afecta lógica) | No genera release |
| `refactor` | Refactorización de código | No genera release |
| `test` | Agregar o modificar tests | No genera release |
| `build` | Cambios en build o dependencias | No genera release |
| `ci` | Cambios en CI/CD | No genera release |
| `chore` | Tareas de mantenimiento | No genera release |

### Breaking Changes

Para generar una versión MAJOR (x.0.0), agrega `BREAKING CHANGE:` en el footer o usa `!` después del tipo:

```bash
feat!: cambio que rompe compatibilidad
```

o

```bash
feat: nueva función

BREAKING CHANGE: descripción del cambio que rompe compatibilidad
```

## 📌 Ejemplos

### Agregar nueva funcionalidad
```bash
feat(downloader): agregar soporte para descargar múltiples calidades

Implementa la opción para seleccionar entre 720p y 1080p
```

### Corregir un bug
```bash
fix(auth): corregir error de timeout en autenticación

Aumenta el timeout de 30s a 60s para conexiones lentas
```

### Mejora de rendimiento
```bash
perf(m3u8): reducir batch size para evitar rate limiting

Cambia de 5 a 2 fragmentos paralelos para evitar HTTP 429
```

### Actualizar documentación
```bash
docs(readme): agregar ejemplos de uso de batch download
```

### Refactorización
```bash
refactor(api): simplificar lógica de retry con decorador
```

## 🔄 Flujo de Trabajo

1. **Crear una rama feature**
   ```bash
   git checkout -b feat/nueva-funcionalidad
   ```

2. **Hacer commits siguiendo las convenciones**
   ```bash
   git add .
   git commit -m "feat(api): agregar nueva funcionalidad"
   ```

3. **Push y crear Pull Request**
   ```bash
   git push origin feat/nueva-funcionalidad
   ```

4. **Merge a master**
   - Al hacer merge a `master`, GitHub Actions automáticamente:
     - Analiza los commits
     - Determina el tipo de versión (major/minor/patch)
     - Actualiza la versión en `pyproject.toml` y `__init__.py`
     - Crea un tag (ej: `v0.8.0`)
     - Genera el CHANGELOG
     - Publica a PyPI
     - Crea un GitHub Release

## 🚀 Versionado Automático

El sistema analiza los commits desde el último release:

- **Commits tipo `feat`** → Incrementa versión MINOR (0.7.0 → 0.8.0)
- **Commits tipo `fix` o `perf`** → Incrementa versión PATCH (0.7.0 → 0.7.1)
- **Breaking changes** → Incrementa versión MAJOR (0.7.0 → 1.0.0)
- **Sin cambios significativos** → No genera release

## 🔧 Configuración Local

### Instalar pre-commit hooks (opcional)

```bash
poetry add --group dev pre-commit
pre-commit install
```

### Validar mensajes de commit localmente

```bash
poetry add --group dev commitizen
cz commit  # Usa asistente interactivo para commits
```

## 📦 Testing antes de Push

```bash
# Lint
poetry run ruff check .

# Type checking
poetry run mypy src/platzi

# Tests (si existen)
poetry run pytest
```

## ⚙️ Configuración de Secrets

Para que funcione el versionado automático, configura en GitHub:

1. Ve a **Settings** → **Secrets and variables** → **Actions**
2. Agrega los siguientes secrets:
   - `PLATZI_GITHUB_TOKEN`: Personal Access Token con permisos de `repo` y `workflow`
   - PyPI token (si quieres publicar automáticamente)

## 📚 Recursos

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Semantic Versioning](https://semver.org/)
- [Python Semantic Release](https://python-semantic-release.readthedocs.io/)
