import asyncio

from playwright.async_api import BrowserContext, Page

from .cache import Cache
from .constants import PLATZI_URL
from .models import Chapter, Resource, TypeUnit, Unit, Video
from .utils import download_styles, get_m3u8_url, get_subtitles_url, slugify


@Cache.cache_async
async def get_learning_path_title(page: Page) -> str:
    """Get the title of a learning path from the page."""
    SELECTORS = [
        ".LearningPathHero_LearningPathHero__FEDlM h1",  # Layout antiguo
        'h2[class*="HeaderTitle"][data-qa="path_title"]',  # Nuevo layout con data-qa
        'h2[class*="HeaderTitle__text"]',  # Alternativa
        "h1",  # Fallback genérico
    ]
    EXCEPTION = Exception("No learning path title found")
    
    title = None
    for selector in SELECTORS:
        try:
            title = await page.locator(selector).first.text_content(timeout=5000)
            if title and title.strip():
                return title.strip()
        except Exception:
            continue
    
    await page.close()
    raise EXCEPTION


@Cache.cache_async
async def get_learning_path_courses(page: Page) -> list[str]:
    """Extract all course URLs from a learning path page."""
    SELECTORS = [
        ".CoursesList_CoursesList__TfADh a.Course_Course__NKjCs",  # Layout antiguo
        'ul[class*="CourseList"][data-qa="courses_list"] a',  # Nuevo layout
        'ul[class*="CourseList__PwyEa"] a[href*="/cursos/"]',  # Alternativa
        'a[href*="/cursos/"]',  # Fallback genérico
    ]
    EXCEPTION = Exception("No courses found in learning path")
    
    course_urls: list[str] = []
    
    for selector in SELECTORS:
        try:
            locator = page.locator(selector)
            count = await locator.count()
            
            if count == 0:
                continue
            
            for i in range(count):
                href = await locator.nth(i).get_attribute("href")
                if href and "/cursos/" in href:
                    # Filtrar URLs no deseadas
                    if "/opiniones/" in href or "#reviews" in href:
                        continue
                    
                    # Complete the URL with the base domain
                    full_url = PLATZI_URL + href if href.startswith("/") else href
                    
                    # Evitar duplicados
                    if full_url not in course_urls:
                        course_urls.append(full_url)
            
            if course_urls:
                return course_urls
                
        except Exception:
            continue
    
    await page.close()
    raise EXCEPTION


@Cache.cache_async
async def get_course_title(page: Page) -> str:
    SELECTORS = [
        ".CourseHeader_CourseHeader__Title__yhjgH",  # Layout antiguo
        'h1[class*="CourseHeader"]',  # Más flexible
        "main h1",  # Fallback genérico
        "h1",  # Último recurso
    ]
    EXCEPTION = Exception("No course title found")
    
    for selector in SELECTORS:
        try:
            title = await page.locator(selector).first.text_content(timeout=5000)
            if title and title.strip() and len(title.strip()) > 3:
                return title.strip()
        except Exception:
            continue
    
    await page.close()
    raise EXCEPTION


@Cache.cache_async
async def get_draft_chapters(page: Page) -> list[Chapter]:
    CHAPTER_SELECTORS = [
        ".Syllabus_Syllabus__bVYL_ article",  # Layout antiguo
        'article[class*="Syllabus"]',  # Más flexible
        "article",  # Fallback genérico
    ]
    
    CHAPTER_NAME_SELECTORS = ["h2", 'h2[class*="Syllabus"]', "h3"]
    
    UNIT_LINK_SELECTORS = [
        ".SyllabusSection_SyllabusSection__Materials__C2hlu a",  # Antiguo
        'a[class*="ItemLink"]',  # ⭐ NUEVO (encontrado en análisis)
        'a[class*="SyllabusSection"]',
        'a[href*="/clases/"]',
    ]
    
    TITLE_SELECTORS = [
        'h3[class*="SyllabusSection_Item__Title"]',  # ⭐ MÁS ESPECÍFICO
        'h3[class*="Item__Title"]',  # Flexible
        'h3',  # Genérico
        'h4', 'span', 'p'  # Fallbacks
    ]
    
    EXCEPTION = Exception("No sections found")
    
    chapters: list[Chapter] = []
    chapter_locator = None
    
    # Intentar encontrar capítulos con diferentes selectores
    for chapter_selector in CHAPTER_SELECTORS:
        try:
            locator = page.locator(chapter_selector)
            count = await locator.count()
            if count > 0:
                chapter_locator = locator
                break
        except Exception:
            continue
    
    if not chapter_locator:
        await page.close()
        raise EXCEPTION
    
    try:
        for i in range(await chapter_locator.count()):
            chapter_element = chapter_locator.nth(i)
            
            # Intentar obtener el nombre del capítulo con diferentes selectores
            chapter_name = None
            for name_selector in CHAPTER_NAME_SELECTORS:
                try:
                    chapter_name = await chapter_element.locator(name_selector).first.text_content(timeout=5000)
                    if chapter_name and chapter_name.strip():
                        chapter_name = chapter_name.strip()
                        break
                except Exception:
                    continue
            
            if not chapter_name:
                continue
            
            # Intentar obtener unidades con diferentes selectores
            units: list[Unit] = []
            unit_urls_seen: set[str] = set()
            
            for link_selector in UNIT_LINK_SELECTORS:
                try:
                    block_list_locator = chapter_element.locator(link_selector)
                    count = await block_list_locator.count()
                    
                    if count == 0:
                        continue
                    
                    for j in range(count):
                        ITEM_LOCATOR = block_list_locator.nth(j)
                        
                        unit_url = await ITEM_LOCATOR.get_attribute("href")
                        
                        # Filtrar URLs no válidas
                        if not unit_url or "/opiniones/" in unit_url or "#reviews" in unit_url:
                            continue
                        
                        # Validar que sea una URL de curso o clase
                        if "/cursos/" not in unit_url and "/clases/" not in unit_url:
                            continue
                        
                        # Evitar duplicados
                        if unit_url in unit_urls_seen:
                            continue
                        
                        # Intentar obtener el título con diferentes selectores
                        unit_title = None
                        for title_selector in TITLE_SELECTORS:
                            try:
                                unit_title = await ITEM_LOCATOR.locator(title_selector).first.text_content(timeout=3000)
                                if unit_title and unit_title.strip() and len(unit_title.strip()) >= 3:
                                    unit_title = unit_title.strip()
                                    break
                            except Exception:
                                continue
                        
                        if not unit_title:
                            continue
                        
                        unit_urls_seen.add(unit_url)
                        
                        units.append(
                            Unit(
                                type=TypeUnit.VIDEO,
                                title=unit_title,
                                url=PLATZI_URL + unit_url if unit_url.startswith("/") else unit_url,
                                slug=slugify(unit_title),
                            )
                        )
                    
                    # Si encontramos unidades, salir del loop de selectores
                    if units:
                        break
                        
                except Exception:
                    continue
            
            # Solo agregar capítulos que tengan unidades
            if units:
                chapters.append(
                    Chapter(
                        name=chapter_name,
                        slug=slugify(chapter_name),
                        units=units,
                    )
                )
    
    except Exception as e:
        await page.close()
        raise EXCEPTION from e
    
    if not chapters:
        await page.close()
        raise EXCEPTION
    
    return chapters


@Cache.cache_async
async def get_unit(context: BrowserContext, url: str) -> Unit:
    # Multiple selectors for video player - Platzi may use different class names
    VIDEO_PLAYER_SELECTORS = [
        ".VideoPlayer",
        'div[class*="VideoPlayer"]',
        '[data-vjs-player]',
        'div.VideoWithChallenges_VideoWithChallenges__cgfF7',
    ]
    
    TITLE_SELECTORS = [
        "h1[class*='MaterialHeading']",
        "main h1",
        "h1",
    ]
    
    # Selector para detectar página de error 500
    ERROR_500_SELECTOR = 'h1:has-text("Error 500")'
    EXCEPTION = Exception("Could not collect unit data")
    
    # Debug mode - Set to True to see detailed logs during video detection
    DEBUG_MODE = False

    # --- NEW CONSTANTS ----
    SECTION_FILES = '//h4[normalize-space(text())="Archivos de la clase"]'
    SECTION_READING = '//h4[normalize-space(text())="Lecturas recomendadas"]'
    
    # Selectores de enlaces de sección - Múltiples opciones
    SECTION_LINK_SELECTORS = [
        'a.FilesAndLinks_Item__fR7g4',  # Clase antigua
        'a.FilesAndLinks_Item__tXA4W',  # ⭐ NUEVA clase encontrada
        'a[class*="FilesAndLinks_Item"]',  # Flexible
    ]
    
    # Selectores de botones de descarga - Múltiples opciones
    DOWNLOAD_BUTTON_SELECTORS = [
        'a.Button.FilesTree_FilesTree__Download__nGUsL[href][download]',  # Antiguo
        'a.Button.FilesTree_FilesTree__Download__pvaHL[href][download]',  # ⭐ NUEVO
        'a[class*="FilesTree__Download"][href][download]',  # Flexible
        'a[download][target="_blank"]',  # Fallback con filtro "Descargar"
    ]
    
    # Updated selector to be more flexible - matches any class containing Resources__Articlass
    SUMMARY_CONTENT_SELECTOR = 'div[class*="Resources_Resources__Articlass"]'
    SIBLINGS = '//following-sibling::ul[1]'

    if "/quiz/" in url:
        return Unit(
            url=url,
            title="Quiz",
            type=TypeUnit.QUIZ,
            slug="Quiz",
        )

    page = None
    try:
        page = await context.new_page()
        
        if DEBUG_MODE:
            print(f"[DEBUG] Opening URL: {url}")
        
        # Intentar cargar la página con reintentos
        max_retries = 3
        retry_delay = 10  # segundos entre reintentos
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    if DEBUG_MODE:
                        print(f"[DEBUG] Retry attempt {attempt + 1}/{max_retries}")
                    await asyncio.sleep(retry_delay * attempt)  # Delay incremental
                
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                
                # Esperar un poco para que la página cargue
                await asyncio.sleep(5)
                
                # Verificar si es una página de error 500
                error_500_exists = await page.locator(ERROR_500_SELECTOR).count() > 0
                
                if error_500_exists:
                    if attempt < max_retries - 1:
                        if DEBUG_MODE:
                            print(f"[DEBUG] Error 500 detected, retrying...")
                        continue
                    else:
                        raise Exception(f"Server returned Error 500 after {max_retries} attempts: {url}")
                
                # Si llegamos aquí, la página cargó correctamente
                break
                
            except Exception as e:
                if "net::ERR_CONNECTION_CLOSED" in str(e) or "ERR_CONNECTION_RESET" in str(e):
                    if attempt < max_retries - 1:
                        if DEBUG_MODE:
                            print(f"[DEBUG] Connection error, retrying... ({str(e)})")
                        continue
                    else:
                        raise Exception(f"Connection failed after {max_retries} attempts: {str(e)}")
                else:
                    # Otro tipo de error, no reintentar
                    raise
        
        if DEBUG_MODE:
            print(f"[DEBUG] Page loaded successfully, extracting data")

        # Try multiple selectors with increased timeout
        title = None
        for selector in TITLE_SELECTORS:
            try:
                title = await page.locator(selector).first.text_content(timeout=15000)
                if title and title.strip():
                    break
            except Exception:
                continue
        
        if not title:
            raise Exception(f"Could not find title on page: {url}")

        # Try to determine if it's a video or lecture
        unit_type = TypeUnit.LECTURE
        video = None
        
        if DEBUG_MODE:
            print(f"[DEBUG] Starting video player detection for: {title}")
        
        # Try multiple video player selectors
        video_player_found = False
        for selector in VIDEO_PLAYER_SELECTORS:
            try:
                count = await page.locator(selector).count()
                if DEBUG_MODE:
                    print(f"[DEBUG] Checking selector '{selector}': found {count} elements")
                
                if count > 0:
                    video_player_found = True
                    if DEBUG_MODE:
                        print(f"[DEBUG] ✅ Video player found with: {selector}")
                    break
            except Exception as e:
                if DEBUG_MODE:
                    print(f"[DEBUG] ❌ Selector '{selector}' failed: {str(e)[:50]}")
                continue
        
        if video_player_found:
            if DEBUG_MODE:
                print(f"[DEBUG] Video player found, checking for m3u8...")
            
            # VideoPlayer found, wait for video content to load
            await asyncio.sleep(3)
            content = await page.content()
            
            # Try to find m3u8 URL with retries
            m3u8_found = False
            max_retries = 5
            
            for attempt in range(max_retries):
                try:
                    if DEBUG_MODE:
                        print(f"[DEBUG] Attempt {attempt + 1}/{max_retries} to find m3u8...")
                    
                    m3u8_url = get_m3u8_url(content)
                    
                    if DEBUG_MODE:
                        print(f"[DEBUG] ✅ m3u8 found: {m3u8_url[:80]}...")
                    
                    unit_type = TypeUnit.VIDEO
                    video = Video(
                        url=m3u8_url,
                        subtitles_url=get_subtitles_url(content),
                    )
                    m3u8_found = True
                    break
                except Exception as e:
                    if DEBUG_MODE:
                        print(f"[DEBUG] Attempt {attempt + 1} failed: {str(e)[:80]}")
                    
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 + attempt)
                        content = await page.content()
                    else:
                        # Last attempt - check for video indicators
                        try:
                            has_video_controls = await page.locator('.vjs-control-bar, [data-vjs-player]').count() > 0
                            if DEBUG_MODE:
                                print(f"[DEBUG] Video controls detected: {has_video_controls}")
                            
                            if has_video_controls:
                                if DEBUG_MODE:
                                    print(f"[DEBUG] Waiting extra time for video...")
                                await asyncio.sleep(3)
                                content = await page.content()
                                try:
                                    m3u8_url = get_m3u8_url(content)
                                    unit_type = TypeUnit.VIDEO
                                    video = Video(
                                        url=m3u8_url,
                                        subtitles_url=get_subtitles_url(content),
                                    )
                                    m3u8_found = True
                                    if DEBUG_MODE:
                                        print(f"[DEBUG] ✅ m3u8 found after extra wait")
                                except Exception:
                                    if DEBUG_MODE:
                                        print(f"[DEBUG] ❌ Still no m3u8 found")
                                    pass
                        except Exception:
                            pass
            
            if not m3u8_found:
                unit_type = TypeUnit.LECTURE
                video = None
                if DEBUG_MODE:
                    print(f"[DEBUG] ❌ No m3u8 found, marking as LECTURE")
        else:
            # No VideoPlayer element, it's a lecture
            content = await page.content()
            if DEBUG_MODE:
                print(f"[DEBUG] ❌ No video player found, it's a LECTURE")

        # --- Get resources and summary---
        html_summary = None

        files_section = page.locator(SECTION_FILES)
        next_sibling_files = files_section.locator(SIBLINGS)

        reading_section = page.locator(SECTION_READING)
        next_sibling_reading = reading_section.locator(SIBLINGS)

        file_links: list[str] = []
        readings_links: list[str] = []

        # Get "Archivos de la clase" if the section exists
        if await next_sibling_files.count() > 0:
            # Intentar diferentes selectores de enlaces
            for selector in SECTION_LINK_SELECTORS:
                try:
                    enlaces = next_sibling_files.locator(selector)
                    count = await enlaces.count()
                    if count > 0:
                        for i in range(count):
                            link = await enlaces.nth(i).get_attribute("href")
                            if link and link not in file_links:
                                file_links.append(link)
                        break
                except Exception:
                    continue

        # Get link of the download all button if it exists
        download_link_found = False
        for selector in DOWNLOAD_BUTTON_SELECTORS:
            try:
                download_button = page.locator(selector)
                if await download_button.count() > 0:
                    # Filtro adicional para el selector genérico
                    if selector == 'a[download][target="_blank"]':
                        download_button = download_button.filter(has_text="Descargar")
                    
                    link = await download_button.first.get_attribute("href")
                    if link and link not in file_links:
                        file_links.append(link)
                        download_link_found = True
                        break
            except Exception:
                continue

        # Get "Lecturas recomendadas" if the section exists
        if await next_sibling_reading.count() > 0:
            # Intentar diferentes selectores de enlaces
            for selector in SECTION_LINK_SELECTORS:
                try:
                    enlaces = next_sibling_reading.locator(selector)
                    count = await enlaces.count()
                    if count > 0:
                        for i in range(count):
                            link = await enlaces.nth(i).get_attribute("href")
                            if link and link not in readings_links:
                                readings_links.append(link)
                        break
                except Exception:
                    continue

        # Get summary if it exists
        summary = page.locator(SUMMARY_CONTENT_SELECTOR).first
        if await summary.count() > 0:
            all_css_styles: list[str] = []

            # Get the HTML structure of the summary (using .first to avoid strict mode violation)
            summary_section = await summary.evaluate("el => el.outerHTML")

            # Find all CSS selectors to include in the html_summary template
            stylesheet_links = page.locator("link[rel=stylesheet]")
            count = await stylesheet_links.count()
            for i in range(count):
                href = await stylesheet_links.nth(i).get_attribute("href")
                if href:
                    stylesheet = await download_styles(href)
                    all_css_styles.append(stylesheet)

            # Get the content of the <style>
            style_blocks = await page.query_selector_all("style")
            for style in style_blocks:
                content = await style.inner_text()
                all_css_styles.append(content)

            # Combine all styles
            styles = "\n".join(filter(None, all_css_styles))

            # HTML template for the summary
            html_summary = f"""
           <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{title}</title>
                <style>{styles}</style>
            </head>
            <body>
                <div class="Layout_Layout__s8xxr">
                    <main class="Layout_Layout-main__FbmEd">
                        {summary_section}
                    </main>
                </div>
            </body>
            </html>"""

        return Unit(
            url=url,
            title=title,
            type=unit_type,
            video=video,
            slug=slugify(title),
            resources=Resource(
                files_url=file_links,
                readings_url=readings_links,
                summary=html_summary,
            ),
        )

    except Exception as e:
        # Log the specific error for debugging
        import traceback
        error_details = traceback.format_exc()
        print(f"Error details: {error_details}")
        
        # Crear mensaje de error más detallado
        error_msg = f"Could not collect unit data for '{title if 'title' in locals() else 'Unknown'}'"
        
        # Añadir contexto adicional según el tipo de error
        if "Error 500" in str(e):
            error_msg += " - Server returned Error 500 (Internal Server Error). This may be a temporary issue with Platzi's servers."
        elif "ERR_CONNECTION_CLOSED" in str(e) or "ERR_CONNECTION_RESET" in str(e):
            error_msg += " - Connection was closed by the server. This may indicate rate limiting or temporary server issues."
        elif "Could not find title" in str(e):
            error_msg += " - Could not extract the class title from the page."
        
        raise Exception(error_msg) from e

    finally:
        if page:
            await page.close()
