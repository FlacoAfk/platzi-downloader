# Fix: Detección de Video vs Lectura

## Problema Resuelto
El downloader detectaba algunas clases como "lectura" cuando en realidad eran videos, debido a que el contenido de video carga de forma asíncrona.

## Solución Implementada

### Mejoras en la Detección de Videos
El código ha sido optimizado para:
- **Múltiples selectores**: Usa varios selectores CSS para encontrar el reproductor de video
- **Sistema de reintentos**: Intenta hasta 5 veces encontrar el m3u8 URL
- **Espera progresiva**: Aumenta el tiempo de espera en cada intento (2, 3, 4, 5, 6 segundos)
- **Detección de indicadores**: Verifica elementos adicionales del reproductor de video
- **Configuración Desktop**: Usa modo escritorio con Chrome/Windows user-agent

### Modo Debug

Para ver logs detallados de qué está pasando durante la detección, edita `src/platzi/collectors.py`:

```python
# Busca esta línea (alrededor de la línea 265):
DEBUG_MODE = False

# Cámbiala a:
DEBUG_MODE = True
```

Con DEBUG_MODE activado verás mensajes como:
```
[DEBUG] Opening URL: https://...
[DEBUG] Page loaded, waiting completed
[DEBUG] Starting video player detection for: Configuración de VSCode...
[DEBUG] Checking selector '.VideoPlayer': found 1 elements
[DEBUG] ✅ Video player found with: .VideoPlayer
[DEBUG] Video player found, checking for m3u8...
[DEBUG] Attempt 1/5 to find m3u8...
[DEBUG] ✅ m3u8 found: https://api.platzi.com/mdstrm/v1/video/...
```

O si es una lectura:
```
[DEBUG] ❌ No video player found, it's a LECTURE
```

### Selectores de Video Player
```python
VIDEO_PLAYER_SELECTORS = [
    ".VideoPlayer",
    'div[class*="VideoPlayer"]',
    '[data-vjs-player]',
    'div.VideoWithChallenges_VideoWithChallenges__cgfF7',
]
```

### Tiempo de Espera Total
Con las mejoras implementadas, el sistema espera:
- 5 segundos iniciales de carga
- 3 segundos para inicializar el reproductor
- Hasta 5 reintentos × (2-6 segundos) = máx. 20 segundos
- 3 segundos extras si detecta indicadores de video
- **Total: hasta ~31 segundos por video**

## Configuración del Navegador

El downloader usa **modo escritorio** con la siguiente configuración:

```python
User-Agent: Chrome 120 on Windows
Viewport: 1920x1080
Locale: es-ES
Timezone: America/Mexico_City
```

## Archivos Modificados

### 1. `src/platzi/collectors.py`
- Mejorada lógica de detección con múltiples selectores
- Sistema de reintentos robusto
- Modo DEBUG configurable

## Notas Importantes

- **La sección "Resumen"** aparece tanto en videos como en lecturas, NO es un indicador confiable
- **El único indicador confiable** es la presencia del m3u8 URL en el contenido
- **Platzi usa React/Next.js** que carga contenido dinámicamente
- **Es necesario esperar** a que el contenido cargue completamente

## Uso

Simplemente ejecuta el downloader normalmente:

```powershell
platzi download <url>
```

El sistema detectará automáticamente si es video o lectura.

### Si necesitas diagnosticar problemas:

1. Activa DEBUG_MODE en `src/platzi/collectors.py`
2. Ejecuta el downloader
3. Observa los logs para ver qué está pasando
4. Desactiva DEBUG_MODE cuando termines (para mejor rendimiento)
