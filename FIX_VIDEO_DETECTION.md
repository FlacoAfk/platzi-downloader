# Fix: Detección incorrecta de LECTURE cuando debería ser VIDEO

## Problema
El descargador guardaba archivos `.mhtml` en lugar de descargar videos porque detectaba incorrectamente algunas clases de video como "lecture" (lecturas/artículos).

### Causa raíz
1. El elemento `.VideoPlayer` existe en el DOM tanto para videos como para lectures
2. En las lectures, el VideoPlayer está vacío (sin contenido de video)
3. El código original solo verificaba si `.VideoPlayer` era visible, no si tenía contenido real

### Escenarios problemáticos
- Cuando la página se carga lentamente
- Cuando el video player tarda en inicializarse
- Cuando se captura el DOM antes de que el video se cargue completamente

## Solución implementada

### Cambios en `src/platzi/collectors.py` - función `get_unit()`

**Antes:**
```python
if not await page.locator(TYPE_SELECTOR).is_visible():
    return Unit(
        url=url,
        title=title,
        type=TypeUnit.LECTURE,
        slug=slugify(title),
    )

# It's a video unit
content = await page.content()
unit_type = TypeUnit.VIDEO
video = Video(
    url=get_m3u8_url(content),  # Podía fallar aquí
    subtitles_url=get_subtitles_url(content),
)
```

**Después:**
```python
unit_type = TypeUnit.LECTURE
video = None

if await page.locator(TYPE_SELECTOR).is_visible():
    # Esperar a que el video player se inicialice
    await asyncio.sleep(3)
    content = await page.content()
    
    try:
        m3u8_url = get_m3u8_url(content)
        # Si encuentra m3u8, ES un video
        unit_type = TypeUnit.VIDEO
        video = Video(url=m3u8_url, subtitles_url=get_subtitles_url(content))
    except Exception:
        # No m3u8, verificar nuevamente después de esperar más
        await asyncio.sleep(2)
        content = await page.content()
        try:
            m3u8_url = get_m3u8_url(content)
            unit_type = TypeUnit.VIDEO
            video = Video(url=m3u8_url, subtitles_url=get_subtitles_url(content))
        except Exception:
            # Definitivamente es una lecture
            unit_type = TypeUnit.LECTURE
            video = None
else:
    # No hay VideoPlayer, es una lecture
    content = await page.content()
```

### Mejoras implementadas

1. **Detección basada en contenido real**: Ya no asume que la presencia de `.VideoPlayer` significa que es un video
2. **Tiempo de espera para carga**: Espera 3 segundos iniciales para que el video player se inicialice
3. **Retry inteligente**: Si no encuentra m3u8 la primera vez, espera 2 segundos más y lo intenta nuevamente
4. **Manejo robusto de excepciones**: Captura fallos en `get_m3u8_url()` en lugar de propagarlos
5. **Clasificación correcta**: Solo marca como VIDEO si puede extraer exitosamente la URL del m3u8

## Validación

### Archivos de prueba verificados:
- `clases_desde_chromium/1.html` → VIDEO (tiene m3u8) ✅
- `Configuración de VSCode.../sin_abrir_inspeccionar.html` → LECTURE (sin m3u8) ✅
- `Configuración de VSCode.../inspeccionar_abierto.html` → VIDEO (tiene m3u8) ✅
- `Checkbox y select.../sin_abrir_inspeccionar.html` → LECTURE (sin m3u8) ✅
- `Checkbox y select.../inspeccionar_abierto.html` → VIDEO (tiene m3u8) ✅

## Resultado esperado

Ahora el descargador:
- ✅ Descarga videos como `.mp4` cuando hay contenido de video real
- ✅ Guarda lectures como `.mhtml` solo cuando no hay video
- ✅ Maneja correctamente páginas que cargan lentamente
- ✅ Evita falsos positivos en la detección de lectures

## Archivos modificados
- `src/platzi/collectors.py` - función `get_unit()` (líneas ~315-355)
