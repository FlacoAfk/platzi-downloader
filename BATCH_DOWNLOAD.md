# 📥 Guía de Descarga por Lotes (Batch Download)

## 🎯 Descripción

La funcionalidad de descarga por lotes te permite descargar múltiples cursos y rutas de Platzi de forma automática y secuencial desde un archivo de texto.

## ✨ Características

- ✅ **Descarga múltiples URLs** en orden desde un archivo de texto
- ✅ **Limpieza automática de caché** después de cada descarga (opcional)
- ✅ **Manejo robusto de errores** - si una descarga falla, continúa con la siguiente
- ✅ **Soporte para comentarios** en el archivo de URLs (líneas que empiezan con `#`)
- ✅ **Informe detallado** al finalizar con estadísticas de éxito/error
- ✅ **Compatible con rutas y cursos** individuales

## 📝 Formato del archivo de URLs

Crea un archivo de texto (por ejemplo, `urls.txt`) con las siguientes reglas:

1. **Una URL por línea**
2. **Líneas que comienzan con `#` son comentarios** y se ignoran
3. **Líneas vacías** se ignoran
4. **URLs deben empezar con** `http://` o `https://`

### Ejemplo de `urls.txt`:

```txt
# Lista de cursos y rutas de Platzi para descargar
# Líneas que comienzan con # son comentarios y serán ignoradas

# === Desarrollo Frontend ===
https://platzi.com/ruta/desarrollo-frontend-angular/
https://platzi.com/ruta/desarrollo-frontend-react-js/
https://platzi.com/ruta/desarrollo-frontend-vuejs/

# === Desarrollo Backend ===
https://platzi.com/ruta/desarrollo-backend-con-nodejs/
https://platzi.com/ruta/desarrollo-backend-con-python/
https://platzi.com/ruta/desarrollo-backend-con-java/

# === Cursos individuales ===
https://platzi.com/cursos/python/
https://platzi.com/cursos/javascript-basico/

# === Cloud & DevOps ===
https://platzi.com/ruta/fundamentos-de-cloud-y-devops/
https://platzi.com/ruta/plataforma-cloud-aws/
```

## 🚀 Uso

### Uso básico (archivo por defecto `urls.txt`):

```bash
platzi batch-download
```

### Especificar un archivo personalizado:

```bash
platzi batch-download mi_lista_cursos.txt
```

### Con opciones adicionales:

```bash
# Especificar calidad de video
platzi batch-download urls.txt --quality 720

# Sobrescribir archivos existentes
platzi batch-download urls.txt --overwrite

# NO limpiar el caché después de cada descarga
platzi batch-download urls.txt --no-clear-cache

# Combinando opciones
platzi batch-download urls.txt --quality 1080 --overwrite --clear-cache
```

## ⚙️ Opciones disponibles

| Opción | Atajo | Descripción | Por defecto |
|--------|-------|-------------|-------------|
| `--quality` | `-q` | Calidad del video a descargar | Auto |
| `--overwrite` | `-w` | Sobrescribir archivos si existen | `False` |
| `--clear-cache` | `-c` | Limpiar caché después de cada descarga | `True` |
| `--no-clear-cache` | | Deshabilitar limpieza de caché | |

## 📊 Proceso de descarga

1. **Lee el archivo** de URLs y filtra líneas válidas
2. **Valida las URLs** e ignora líneas inválidas con un warning
3. **Descarga secuencialmente** cada curso/ruta
4. **Limpia el caché** después de cada descarga (si está habilitado)
5. **Continúa automáticamente** si hay errores
6. **Muestra un resumen final** con estadísticas

## 📈 Ejemplo de salida

```
====================================================================================================
🚀 Starting batch download of 45 items
====================================================================================================

ℹ️  Cache will be cleared after each download

====================================================================================================
📥 Processing item 1/45
URL: https://platzi.com/ruta/desarrollo-frontend-angular/
====================================================================================================

Learning Path: Desarrollo Frontend con Angular
...

✅ Successfully downloaded item 1/45: https://platzi.com/ruta/desarrollo-frontend-angular/
🗑️  Cache cleared

====================================================================================================
📥 Processing item 2/45
URL: https://platzi.com/ruta/desarrollo-frontend-react-js/
====================================================================================================

...

====================================================================================================
📊 BATCH DOWNLOAD SUMMARY
====================================================================================================
Total items: 45
✅ Successful: 43
❌ Failed: 2

Failed URLs:
  • https://platzi.com/cursos/curso-no-existe/
    Error: 404 Not Found

====================================================================================================
⚠️  Completed with 2 error(s)
====================================================================================================
```

## 💡 Consejos y mejores prácticas

### 1. **Organiza tu archivo de URLs**
   - Usa comentarios para agrupar cursos por categoría
   - Mantén un orden lógico (por ejemplo, por ruta de aprendizaje)

### 2. **Gestión de caché**
   - Usa `--clear-cache` (por defecto) para evitar que la caché crezca demasiado
   - Usa `--no-clear-cache` solo si necesitas debug o desarrollo

### 3. **Manejo de interrupciones**
   - Puedes detener el proceso con `Ctrl+C`
   - Los cursos ya descargados permanecerán en el disco
   - Elimina las URLs ya descargadas del archivo y vuelve a ejecutar

### 4. **URLs grandes**
   - Para listas muy grandes, considera dividirlas en múltiples archivos
   - Ejemplo: `urls_frontend.txt`, `urls_backend.txt`, etc.

### 5. **Verificación de espacio en disco**
   - Asegúrate de tener suficiente espacio antes de descargas masivas
   - Cada ruta puede ocupar varios GB

## 🔧 Solución de problemas

### El archivo no se encuentra
```
Error: File 'urls.txt' not found!
```
**Solución:** Verifica que el archivo exista en el directorio actual o proporciona la ruta completa.

### Ninguna URL válida encontrada
```
Warning: No valid URLs found in the file.
```
**Solución:** Verifica que las URLs comiencen con `http://` o `https://` y no estén todas comentadas.

### Descarga falla por falta de login
```
Error: Login first!
```
**Solución:** Ejecuta `platzi login` antes de usar batch-download.

### Error de memoria con muchas descargas
**Solución:** Usa `--clear-cache` (habilitado por defecto) o divide el archivo en partes más pequeñas.

## 📂 Estructura de archivos descargados

Los cursos y rutas se organizarán en la carpeta `Courses/`:

```
Courses/
├── Desarrollo Frontend con Angular/
│   ├── 1. Curso de Fundamentos de Angular/
│   ├── 2. Curso de Componentes y Servicios en Angular/
│   └── ...
├── Desarrollo Frontend con React JS/
│   ├── 1. Curso de React.js/
│   ├── 2. Curso de React Router/
│   └── ...
└── Curso de Python/
    ├── 1. Introducción/
    ├── 2. Variables y Operadores/
    └── ...
```

## 🎓 Ejemplos de uso práctico

### Descargar todas las rutas de desarrollo web:
```bash
# Crear archivo web_development.txt
platzi batch-download web_development.txt --quality 1080
```

### Descargar solo cursos específicos:
```bash
# Crear archivo my_courses.txt con cursos individuales
platzi batch-download my_courses.txt --overwrite
```

### Descarga nocturna automatizada:
```bash
# Windows Task Scheduler o cron job
platzi batch-download all_courses.txt --quality 720 --clear-cache
```

## 🆘 Ayuda

Para ver todas las opciones disponibles:

```bash
platzi batch-download --help
```

Para ver todos los comandos disponibles:

```bash
platzi --help
```

---

**¡Disfruta descargando tus cursos de Platzi! 🎉**
