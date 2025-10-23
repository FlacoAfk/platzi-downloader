# 🚀 Configuración de Release Automático

## Paso 1: Configurar GitHub Token

1. Ve a GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)**
2. Click en **Generate new token (classic)**
3. Nombre: `PLATZI_RELEASE_TOKEN`
4. Selecciona permisos:
   - ✅ `repo` (todos los sub-permisos)
   - ✅ `workflow`
5. Click **Generate token** y copia el token

## Paso 2: Agregar Secret al Repositorio

1. Ve al repositorio → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Nombre: `PLATZI_GITHUB_TOKEN`
4. Valor: Pega el token que copiaste
5. Click **Add secret**

## Paso 3: Configurar PyPI (opcional)

Si quieres publicar automáticamente a PyPI:

1. Ve a [PyPI Account Settings](https://pypi.org/manage/account/)
2. Crea un API token específico para el proyecto
3. En GitHub: **Settings** → **Secrets** → **New repository secret**
4. Nombre: `PYPI_TOKEN`
5. Valor: El token de PyPI (comienza con `pypi-...`)

**Nota:** El workflow ya usa la nueva autenticación "trusted publishing" de PyPI, así que esto es opcional.

## Paso 4: Instalar Herramientas de Desarrollo (Local)

```bash
# Instalar dependencias de desarrollo
poetry install --with dev

# Instalar pre-commit hooks
poetry run pre-commit install

# Verificar instalación
poetry run commitizen version
```

## Paso 5: Probar el Sistema

```bash
# Hacer un commit de prueba (sin push todavía)
git checkout -b test/versioning
echo "test" >> test.txt
git add test.txt
git commit -m "feat(test): probar versionado automático"

# El pre-commit hook validará el mensaje
# Si es válido, el commit se realizará

# Push y crear PR
git push origin test/versioning

# Merge a master → El workflow se ejecutará automáticamente
```

## 🎯 Verificar que Funciona

Después del merge a master, verifica:

1. **GitHub Actions**: Ve a la pestaña "Actions" y verifica que el workflow "Continuous Delivery" se ejecutó
2. **Tags**: Ve a la pestaña "Tags" y verifica que se creó un nuevo tag (ej: `v0.8.0`)
3. **Releases**: Ve a "Releases" y verifica que se creó un release con CHANGELOG
4. **PyPI**: Ve a https://pypi.org/project/platzi/ y verifica la nueva versión
5. **Archivos actualizados**: Verifica que `pyproject.toml` y `__init__.py` tienen la nueva versión

## 🔧 Troubleshooting

### El workflow no se ejecuta

- ✅ Verifica que el secret `PLATZI_GITHUB_TOKEN` existe
- ✅ Verifica que el commit no tiene `[skip ci]` en el mensaje
- ✅ Verifica que estás en la rama `master` o `main`

### No se crea un release

- ✅ Verifica que los commits siguen Conventional Commits
- ✅ Verifica que hay al menos un commit tipo `feat` o `fix` desde el último release
- ✅ Revisa los logs del workflow en GitHub Actions

### Error de permisos en PyPI

- ✅ Verifica que el token de PyPI es válido
- ✅ Verifica que el proyecto existe en PyPI
- ✅ Considera usar "trusted publishing" en lugar de tokens

### Pre-commit hooks fallan

```bash
# Reinstalar hooks
poetry run pre-commit uninstall
poetry run pre-commit install

# Ejecutar manualmente
poetry run pre-commit run --all-files
```

## 📚 Documentación Completa

- [VERSIONING.md](../../VERSIONING.md) - Guía completa de versionado
- [CONTRIBUTING.md](../../CONTRIBUTING.md) - Guía de contribución
- [Python Semantic Release Docs](https://python-semantic-release.readthedocs.io/)

## 💡 Tips

- **Commits pequeños y frecuentes**: Mejor que commits grandes
- **Un commit = un cambio**: Facilita el versionado automático
- **Usa scopes**: `feat(downloader):` es más claro que solo `feat:`
- **Lee el CHANGELOG**: Se genera automáticamente, revísalo después de cada release
- **No edites manualmente** las versiones en `pyproject.toml` o `__init__.py`
