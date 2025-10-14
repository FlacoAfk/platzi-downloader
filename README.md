<!-- markdownlint-disable MD033 MD036 MD041 MD045 MD046 -->

![Repo Banner](https://i.imgur.com/I6zFXds.png)

<div align="center">

<h1 style="border-bottom: none">
    <b><a href="#">Platzi Downloader</a></b>
</h1>

Es una herramienta de línea de comandos para descargar cursos directamente desde la terminal. Utiliza  ***`Python`*** y ***`Playwright`*** para automatizar el proceso de descarga y proporciona una interfaz de usuario amigable.

## ✨ Características Principales

- 📥 **Descarga completa de cursos**: Videos (HLS/DASH), lecturas, quizzes, recursos y más
- 🎯 **Rutas de aprendizaje**: Descarga rutas completas con todos sus cursos organizados
- 🔄 **Reanudación automática**: Si se interrumpe la descarga, continúa desde donde quedó
- 📊 **Seguimiento de progreso**: Control completo de qué se descargó y qué falló
- 💾 **Reportes detallados**: Genera reportes con estadísticas completas
- 🔁 **Sistema de reintentos**: Hasta 3 intentos automáticos por clase con errores de conexión
- ⚡ **Descarga por lotes**: Descarga múltiples cursos desde un archivo de texto
- 🎨 **Resúmenes con estilo**: Los resúmenes se guardan con formato HTML profesional
- 🛠️ **Herramientas de gestión**: Scripts para ver estadísticas y reintentar clases fallidas
- 🦊 **Firefox/Chromium**: Soporte para ambos navegadores en modo headless
- 🎥 **Detección mejorada**: Intercepta videos HLS (.m3u8) y DASH (.mpd) desde requests de red
- 🧹 **Limpieza de tracking**: Elimina entradas de archivos borrados manualmente

![GitHub repo size](https://img.shields.io/github/repo-size/ivansaul/platzi-downloader)
![GitHub stars](https://img.shields.io/github/stars/ivansaul/platzi-downloader)
![GitHub forks](https://img.shields.io/github/forks/ivansaul/platzi-downloader)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Discord](https://img.shields.io/badge/-Discord-424549?style=social&logo=discord)](https://discord.gg/tDvybtJ7y9)

</div>

---

## Instalación | Actualización

Para [`instalar` | `actualizar` ], ejecuta el siguiente comando en tu terminal:

```console
pip install -U platzi
```

Instala las dependencias de `playwright` (elige uno o ambos):

```console
# Firefox (recomendado por defecto)
playwright install firefox

# Chromium (alternativa)
playwright install chromium
```

> [!IMPORTANT]
> El script utiliza ***`ffmpeg`***, como un subproceso, así que asegúrate de tener instalado y actualizado.

<details>

<summary>Tips & Tricks</summary>

## FFmpeg Instalación

### Ubuntu / Debian

```console
sudo apt install ffmpeg -y
```

### Arch Linux

```console
sudo pacman -S ffmpeg
```

### Windows [[Tutorial]][ffmpeg-youtube]

Puedes descargar la versión de `ffmpeg` para Windows desde [aquí][ffmpeg]. o algún gestor de paquetes como [`Scoop`][scoop] o [`Chocolatey`][chocolatey].

```console
scoop install ffmpeg
```

</details>

## Guía de uso

### Iniciar Sesión

Para iniciar sesión en Platzi, usa el comando login. Esto abrirá una ventana de navegador para autenticarte e iniciar sesión en Platzi.

```console
platzi login
```

### Cerrar Sesión

Para cerrar sesión en Platzi y borrar tu sesión del almacenamiento local, usa el comando `logout`.

```console
platzi logout
```

### Descargar un Curso

Para descargar un curso de Platzi, usa el comando download seguido de la URL del curso que deseas descargar. La URL puede encontrarse en la barra de direcciones al visualizar la página del curso en Platzi.

```console
platzi download URL [OPTIONS]

OPTIONS:
  --quality / -q    Specifies the video quality (default: max). Options: [1080|720].
  --overwrite / -w  Overwrite files if exist.
  --browser / -b    Browser to use: firefox (default) or chromium.
```

Ejemplos:

```console
# Usando Firefox (por defecto, RECOMENDADO)
platzi download https://platzi.com/cursos/python
```

```console
# Usando Chromium (solo soporta HLS/m3u8, algunos videos DASH/mpd pueden fallar)
platzi download https://platzi.com/cursos/python --browser chromium
```

```console
# Con opciones adicionales
platzi download https://platzi.com/cursos/python/ -q 720 -w --browser firefox
```

> [!WARNING]
> **Chromium**: Solo soporta videos HLS (`.m3u8`). Videos DASH (`.mpd`) generan error 403 Forbidden.
> **Firefox**: Soporta ambos formatos (HLS y DASH) sin problemas. **Se recomienda usar Firefox.**

### Descarga por Lotes (Batch Download) 🆕

Para descargar múltiples cursos y rutas automáticamente desde un archivo de texto, usa el comando `batch-download`. Esta es la forma más eficiente de descargar múltiples contenidos.

```console
platzi batch-download [FILE] [OPTIONS]

FILE: Path to text file with URLs (default: urls.txt)

OPTIONS:
  --quality / -q      Specifies the video quality. Options: [1080|720].
  --overwrite / -w    Overwrite files if exist.
  --clear-cache / -c  Clear cache after each download (default: enabled).
  --no-clear-cache    Disable cache clearing after each download.
```

**Formato del archivo de URLs (`urls.txt`):**

```txt
# Comentarios empiezan con #
# Una URL por línea

https://platzi.com/ruta/desarrollo-frontend-angular/
https://platzi.com/ruta/desarrollo-backend-con-python/
https://platzi.com/cursos/python/
```

**Ejemplos:**

```console
# Usar archivo por defecto (urls.txt)
platzi batch-download
```

```console
# Especificar archivo personalizado
platzi batch-download my_courses.txt
```

```console
# Con opciones adicionales
platzi batch-download urls.txt --quality 1080 --overwrite
```

**Características:**
- ✅ Descarga múltiples URLs en orden secuencial
- ✅ Limpieza automática de caché después de cada descarga
- ✅ Manejo robusto de errores (continúa si una descarga falla)
- ✅ Soporte para comentarios en el archivo
- ✅ Informe detallado al finalizar

### Reintentar Descargas Fallidas

Para reintentar automáticamente todos los cursos/unidades que fallaron:

```console
platzi retry-failed
```

Este comando:
- Lee el tracking de descargas
- Identifica automáticamente lo que falló
- Reintenta descargar solo el contenido fallido

### Limpiar Tracking

Si borraste archivos manualmente pero el sistema aún cree que están descargados:

```console
# Vista previa (no modifica nada)
platzi clean-tracking --dry-run

# Limpiar tracking
platzi clean-tracking
```

Este comando elimina del tracking las entradas de cursos/unidades completadas cuyos archivos ya no existen en disco.

### Borrar Caché

Para borrar la caché de Platzi, usa el comando `clear-cache`.

```console
platzi clear-cache
```

## 🛠️ Herramientas de Gestión

El proyecto incluye herramientas para gestión avanzada de descargas:

### Ver Estadísticas (`show_stats.py`)

```console
python show_stats.py
```

Muestra estadísticas detalladas del tracking de descargas.

### Más Herramientas

Ver la [Guía de Herramientas](TOOLS_GUIDE.md) para gestión avanzada y comandos adicionales.

> [!IMPORTANT]
> Asegúrate de estar logueado antes de intentar descargar los cursos.

<br>

> [!TIP]
> Si por algún motivo se cancela la descarga, vuelve a ejecutar `platzi download <url-del-curso>` para retomar la descarga.

<br>

> [!TIP]
> Si algunas clases fallan por errores de conexión (ERR_CONNECTION_CLOSED), el sistema reintentará automáticamente hasta 3 veces por clase. Si persisten los errores, usa `platzi retry-failed` para reintentar.

<br>

> [!TIP]
> Luego de actualizar el script u obtener algún error inesperado se recomienda limpiar la caché antes de volver a intentar descargar el curso. Puedes hacerlo ejecutando el comando `platzi clear-cache`.

<br>

> [!TIP]
> Para solución de problemas comunes (errores 403, carpetas vacías, etc.), consulta la [Guía de Troubleshooting](TROUBLESHOOTING.md).

## 📚 Documentación Adicional

- **[PROGRESS_TRACKING.md](PROGRESS_TRACKING.md)** - Sistema de trazabilidad y continuación de descargas
- **[TOOLS_GUIDE.md](TOOLS_GUIDE.md)** - Guía completa de herramientas de gestión
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Solución de problemas comunes
- **[CHANGELOG.md](CHANGELOG.md)** - Historial de cambios del proyecto

---

## **Aviso de Uso**

Este proyecto se realiza con fines exclusivamente educativos y de aprendizaje. El código proporcionado se ofrece "tal cual", sin ninguna garantía de su funcionamiento o idoneidad para ningún propósito específico.

No me hago responsable por cualquier mal uso, daño o consecuencia que pueda surgir del uso de este proyecto. Es responsabilidad del usuario utilizarlo de manera adecuada y dentro de los límites legales y éticos.

[ffmpeg]: https://ffmpeg.org
[chocolatey]: https://community.chocolatey.org
[scoop]: https://scoop.sh
[ffmpeg-youtube]: https://youtu.be/JR36oH35Fgg?si=Gerco7SP8WlZVaKM
