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
            title = await page.locator(selector).first.text_content(timeout=15000)  # Increased for Firefox headless
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
        'h1[class*="CourseHeader"]',  # Selector flexible (upstream)
        ".CourseHeader_CourseHeader__Title__yhjgH",  # Layout antiguo (fallback)
        "main h1",  # Fallback genérico
        "h1",  # Último recurso
    ]
    EXCEPTION = Exception("No course title found")
    
    for selector in SELECTORS:
        try:
            title = await page.locator(selector).first.text_content(timeout=15000)  # Increased for Firefox headless
            if title and title.strip() and len(title.strip()) > 3:
                return title.strip()
        except Exception:
            continue
    
    await page.close()
    raise EXCEPTION


@Cache.cache_async
async def get_draft_chapters(page: Page) -> list[Chapter]:
    CHAPTER_SELECTORS = [
        'section[class*="Syllabus"] article',  # Selector flexible (upstream)
        ".Syllabus_Syllabus__bVYL_ article",  # Layout antiguo (fallback)
        'article[class*="Syllabus"]',  # Flexible alternativo
        "article",  # Fallback genérico
    ]
    
    CHAPTER_NAME_SELECTORS = ["h2", 'h2[class*="Syllabus"]', "h3"]
    
    UNIT_LINK_SELECTORS = [
        'a[class*="ItemLink"]',  # Selector flexible (upstream)
        ".SyllabusSection_SyllabusSection__Materials__C2hlu a",  # Antiguo (fallback)
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
                    chapter_name = await chapter_element.locator(name_selector).first.text_content(timeout=15000)  # Increased for Firefox headless
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
                                unit_title = await ITEM_LOCATOR.locator(title_selector).first.text_content(timeout=15000)  # Increased for Firefox headless
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
async def get_unit(context: BrowserContext, url: str, browser_type: str = "firefox") -> Unit:
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
    
    # Selectores para detectar página de error 500 REAL del servidor
    # Muy específicos para evitar falsos positivos con títulos de clases
    # que mencionen "Error 500" como parte del contenido educativo
    ERROR_500_SELECTORS = [
        # Buscar solo h1 que sea EXACTAMENTE "Error 500" sin texto adicional
        'main h1:text-is("Error 500")',
        'body > h1:text-is("Error 500")',
        # O un h1 que tenga "Error 500" pero SIN otros elementos dentro (como links)
        'main > h1:has-text("Error 500"):not(:has(a))',
        'body > div > h1:has-text("Error 500"):not(:has(a))',
        # Div de error con clase específica de error de Platzi
        'div[class*="error-page"] h1',
        'div[class*="ErrorPage"] h1',
    ]
    
    # Selector para detectar reproductor de video sin fuente
    VIDEO_ERROR_SELECTOR = 'text=/no compatible source was found/i'
    
    EXCEPTION = Exception("Could not collect unit data")

    # Debug mode - Set to True to see detailed logs during video detection
    DEBUG_MODE = False    # --- NEW CONSTANTS ----
    SECTION_FILES = '//h4[normalize-space(text())="Archivos de la clase"]'
    SECTION_READING = '//h4[normalize-space(text())="Lecturas recomendadas"]'
    
    # Selectores de enlaces de sección - Múltiples opciones
    SECTION_LINK_SELECTORS = [
        'a[class*="FilesAndLinks_Item"]',  # Selector flexible (upstream)
        'a.FilesAndLinks_Item__fR7g4',  # Clase antigua (fallback)
        'a.FilesAndLinks_Item__tXA4W',  # NUEVA clase encontrada (fallback)
    ]
    
    # Selectores de botones de descarga - Múltiples opciones
    DOWNLOAD_BUTTON_SELECTORS = [
        'a[class*="FilesTree__Download"][href][download]',  # Selector flexible (upstream)
        'a.Button.FilesTree_FilesTree__Download__nGUsL[href][download]',  # Antiguo (fallback)
        'a.Button.FilesTree_FilesTree__Download__pvaHL[href][download]',  # NUEVO (fallback)
        'a[download][target="_blank"]',  # Fallback con filtro "Descargar"
    ]
    
    # Updated selector to be more flexible - matches any class containing Resources__Articlass
    SUMMARY_CONTENT_SELECTOR = 'div[class*="Resources_Resources__Articlass"]'
    SIBLINGS = '//following-sibling::ul[1]'

    # Only skip actual quiz exams, not regular classes with "quiz" in their URL
    # Quiz exams follow the pattern: /clases/quiz/NUMBER/
    if "/clases/quiz/" in url:
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
        
        # Intentar cargar la página con reintentos y timeouts progresivos
        max_retries = 3
        retry_delay = 2  # Base delay in seconds
        
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    # Backoff: 2s, 4s, 6s
                    wait_time = retry_delay * attempt
                    if DEBUG_MODE:
                        print(f"[DEBUG] Retry attempt {attempt + 1}/{max_retries} after {wait_time}s wait...")
                    await asyncio.sleep(wait_time)
                
                # Shorter timeout without wait_until - more reliable than waiting for events
                timeout = 30000  # 30s is enough for navigation itself
                
                if DEBUG_MODE:
                    print(f"[DEBUG] Attempt {attempt + 1}/{max_retries} - Using timeout: {timeout}ms ({timeout/1000}s)")
                
                # Navigate WITHOUT wait_until - don't wait for events that may never fire
                await page.goto(url, timeout=timeout)
                
                # Fixed delay for JavaScript to execute (more reliable than waiting for events)
                await asyncio.sleep(5)  # 5s fixed delay for page to stabilize
                
                # Verificar si es una página de error 500 con múltiples selectores
                error_500_exists = False
                for selector in ERROR_500_SELECTORS:
                    try:
                        if await page.locator(selector).count() > 0:
                            error_500_exists = True
                            if DEBUG_MODE:
                                print(f"[DEBUG] Error 500 detected with selector: {selector}")
                            break
                    except Exception:
                        continue
                
                if error_500_exists:
                    if attempt < max_retries - 1:
                        if DEBUG_MODE:
                            print(f"[DEBUG] Error 500 detected, retrying...")
                        continue
                    else:
                        raise Exception(f"Server returned Error 500 after {max_retries} attempts: {url}")
                
                # Si llegamos aquí, la página cargó correctamente
                if DEBUG_MODE:
                    print(f"[DEBUG] ✅ Page loaded successfully on attempt {attempt + 1}")
                break
                
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                
                if DEBUG_MODE:
                    print(f"[DEBUG] {error_type} during page load: {error_msg[:150]}")
                
                # If it's a timeout but page is not blank, it might have loaded enough
                if "Timeout" in error_type:
                    try:
                        current_url = page.url
                        if current_url and current_url != "about:blank" and url in current_url:
                            if DEBUG_MODE:
                                print(f"[DEBUG] ⚠️  Navigation timeout but page loaded: {current_url}")
                            # Page navigated successfully despite timeout, continue with fixed delay
                            await asyncio.sleep(5)
                            break  # Exit retry loop - success!
                    except:
                        pass
                
                # List of retryable errors
                is_retryable = (
                    "Timeout" in error_type or
                    "TimeoutError" in error_type or
                    "net::ERR_CONNECTION_CLOSED" in error_msg or
                    "ERR_CONNECTION_RESET" in error_msg or
                    "NS_BINDING_ABORTED" in error_msg or
                    "Navigation failed" in error_msg
                )
                
                if is_retryable:
                    if attempt < max_retries - 1:
                        if DEBUG_MODE:
                            print(f"[DEBUG] ⚠️  Retryable error detected, will retry...")
                        continue
                    else:
                        # Last attempt failed
                        error_hint = ""
                        if "Timeout" in error_type:
                            error_hint = " | TIP: Page took too long to load. Try using --no-headless for better stability."
                        raise Exception(f"Failed to load page after {max_retries} attempts: {error_msg}{error_hint}")
                elif "Server returned Error 500" in error_msg:
                    # Este error ya fue manejado arriba, re-lanzarlo
                    raise
                else:
                    # Non-retryable error
                    if DEBUG_MODE:
                        print(f"[DEBUG] ❌ Non-retryable error: {error_msg[:200]}")
                    raise
        
        if DEBUG_MODE:
            print(f"[DEBUG] Page loaded successfully, extracting data")

        # Try multiple selectors with short timeout (10s per selector)
        title = None
        for selector in TITLE_SELECTORS:
            try:
                title = await page.locator(selector).first.text_content(timeout=10000)  # Short timeout per selector
            except Exception:
                continue
        
            if title and title.strip():
                break
        
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
            
            # Check if video has an error (no compatible source)
            video_error = False
            try:
                video_error = await page.locator(VIDEO_ERROR_SELECTOR).count() > 0
                if video_error and DEBUG_MODE:
                    print(f"[DEBUG] ⚠️  Video player has no compatible source")
            except Exception:
                pass
            
            # Set up network request interceptor to capture m3u8/mpd URLs
            captured_m3u8_url = None
            captured_mpd_url = None
            
            def capture_request(request):
                nonlocal captured_m3u8_url, captured_mpd_url
                url = request.url
                # Capture both HLS (.m3u8) and DASH (.mpd) formats separately
                if '.m3u8' in url and not captured_m3u8_url:
                    captured_m3u8_url = url
                    if DEBUG_MODE:
                        print(f"[DEBUG] 🎯 Captured HLS (.m3u8) from network: {url[:80]}...")
                elif '.mpd' in url and not captured_mpd_url:
                    captured_mpd_url = url
                    if DEBUG_MODE:
                        print(f"[DEBUG] 🎯 Captured DASH (.mpd) from network: {url[:80]}...")
            
            # Listen for network requests
            page.on("request", capture_request)
            
            # Reload the page to capture network requests
            if DEBUG_MODE:
                print(f"[DEBUG] Reloading page to capture network requests...")
            
            # Reload WITHOUT wait_until - just reload and wait fixed time
            reload_success = False
            try:
                if DEBUG_MODE:
                    print(f"[DEBUG] Reloading without wait_until...")
                await page.reload(timeout=20000)  # 20s timeout, no wait_until
                reload_success = True
            except Exception as reload_error:
                if DEBUG_MODE:
                    print(f"[DEBUG] Reload failed: {str(reload_error)[:100]}")
                # Continue anyway, we might have captured data before the error
                reload_success = False
            
            # Fixed delay for network requests to be captured
            await asyncio.sleep(3)  # 3s for video player to load and make requests
            
            try:
                content = await page.content()
            except Exception as content_error:
                if DEBUG_MODE:
                    print(f"[DEBUG] ⚠️  Could not get page content: {str(content_error)[:100]}")
                content = ""
            
            # Remove the listener
            try:
                page.remove_listener("request", capture_request)
            except Exception:
                pass
            
            # Try to find m3u8 URL with retries (skip if video has error)
            m3u8_found = False
            m3u8_url = None
            
            # FIRST: Check if we captured URLs from network requests
            # For Chromium: Prioritize m3u8 over mpd to avoid 403 errors
            # For Firefox: Use whichever is available (both work fine)
            video_url = None
            
            if browser_type == "chromium":
                # Chromium: ONLY use m3u8, reject mpd-only videos
                if captured_m3u8_url:
                    video_url = captured_m3u8_url
                    if DEBUG_MODE:
                        print(f"[DEBUG] ✅ Using m3u8 (compatible with Chromium)")
                    # Set mpd as fallback if available (won't be used due to 403)
                    # Keeping it for logging purposes only
                elif captured_mpd_url:
                    # DON'T use mpd as primary URL for Chromium
                    # It will fail with 403 Forbidden
                    if DEBUG_MODE:
                        print(f"[DEBUG] ⚠️  Only DASH (.mpd) available - incompatible with Chromium")
                        print(f"[DEBUG] This video will be skipped to avoid 403 error")
                    # Don't set video_url - let it remain None
            else:
                # Firefox: Use whichever is available (prefer m3u8 but mpd also works)
                if captured_m3u8_url:
                    video_url = captured_m3u8_url
                    if DEBUG_MODE:
                        print(f"[DEBUG] ✅ Using m3u8 from network")
                elif captured_mpd_url:
                    video_url = captured_mpd_url
                    if DEBUG_MODE:
                        print(f"[DEBUG] ✅ Using mpd from network")
            
            if video_url:
                m3u8_url = video_url
                unit_type = TypeUnit.VIDEO
                
                # For Chromium: Only set fallback if we have m3u8 as primary
                # (never use mpd as primary for Chromium)
                fallback = None
                if browser_type == "chromium":
                    # If using m3u8 (preferred), don't set mpd as fallback
                    # because mpd will fail with 403 anyway
                    pass
                
                video = Video(
                    url=m3u8_url,
                    fallback_url=fallback,
                    subtitles_url=get_subtitles_url(content),
                )
                m3u8_found = True
            elif browser_type == "chromium" and captured_mpd_url and not captured_m3u8_url:
                # Chromium with only DASH available - treat as non-video unit
                if DEBUG_MODE:
                    print(f"[DEBUG] ❌ Video incompatible with Chromium (DASH only)")
                # Don't create video object - will be treated as LECTURE
            
            # SECOND: If not captured, try finding in HTML content
            if not m3u8_found:
                max_retries = 5 if not video_error else 1  # Reduce retries if video has error
                
                for attempt in range(max_retries):
                    try:
                        if DEBUG_MODE:
                            print(f"[DEBUG] Attempt {attempt + 1}/{max_retries} to find m3u8 in HTML...")
                        
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
                            await asyncio.sleep(1)  # Reduced from 2+attempt to 1s
                            try:
                                content = await page.content()
                            except Exception as content_err:
                                if DEBUG_MODE:
                                    print(f"[DEBUG] ⚠️  Could not get page content: {str(content_err)[:100]}")
                                content = ""
                        else:
                            # Last attempt - check for video indicators
                            try:
                                has_video_controls = await page.locator('.vjs-control-bar, [data-vjs-player]').count() > 0
                                if DEBUG_MODE:
                                    print(f"[DEBUG] Video controls detected: {has_video_controls}")
                                
                                if has_video_controls:
                                    if DEBUG_MODE:
                                        print(f"[DEBUG] Waiting extra time for video...")
                                    await asyncio.sleep(2)  # Reduced from 3s to 2s
                                    try:
                                        content = await page.content()
                                    except Exception as content_err:
                                        if DEBUG_MODE:
                                            print(f"[DEBUG] ⚠️  Could not get page content: {str(content_err)[:100]}")
                                        content = ""
                                    
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
                    if video_error:
                        print(f"[DEBUG] ⚠️  Video not available (no compatible source), treating as LECTURE")
                    elif browser_type == "chromium" and captured_mpd_url:
                        print(f"[DEBUG] ⚠️  Video only available in DASH (.mpd), incompatible with Chromium")
                        print(f"[DEBUG] Treating as LECTURE to avoid 403 error")
                    else:
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

            # Get dynamic class names for layout (upstream improvement)
            layout_container = await page.query_selector('div[class*="Layout_Layout__"]')
            class_container = await layout_container.get_attribute("class") if layout_container else "Layout_Layout__s8xxr"

            main_layout = await page.query_selector('main[class*="Layout_Layout-main"]')
            class_main = await main_layout.get_attribute("class") if main_layout else "Layout_Layout-main__FbmEd"

            # Get the HTML structure of the summary (using .first to avoid strict mode violation)
            summary_section = await summary.evaluate("el => el.outerHTML")

            # Find all CSS selectors to include in the html_summary template
            stylesheet_links = page.locator("link[rel=stylesheet]")
            count = await stylesheet_links.count()
            for i in range(count):
                # Increased timeout for Firefox headless mode
                href = await stylesheet_links.nth(i).get_attribute("href", timeout=60000)  # 60s timeout
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
                <div class="{class_container}">
                    <main class="{class_main}">
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
        error_str = str(e)
        error_type = type(e).__name__
        
        if "Error 500" in error_str:
            error_msg += " - Server returned Error 500 (Internal Server Error). This may be a temporary issue with Platzi's servers."
        elif "ERR_CONNECTION_CLOSED" in error_str or "ERR_CONNECTION_RESET" in error_str:
            error_msg += " - Connection was closed by the server. This may indicate rate limiting or temporary server issues."
        elif "Could not find title" in error_str:
            error_msg += " - Could not extract the class title from the page."
        elif "NS_BINDING_ABORTED" in error_str or "frame was detached" in error_str:
            error_msg += " - Firefox page reload failed (frame detached). This is a known Firefox headless issue. Try using --no-headless flag."
        elif "Timeout" in error_type or "Timeout" in error_str:
            error_msg += " - Page timed out during loading. Firefox headless can be unstable. TIP: Use --no-headless for better reliability."
        elif "Page.reload" in error_str or "Page.goto" in error_str:
            error_msg += " - Page navigation/reload failed. This may be due to Firefox headless instability. Consider using --no-headless."
        elif "Failed to load page after" in error_str:
            # This is our custom error from the retry loop
            pass  # Error message already has details
        
        raise Exception(error_msg) from e

    finally:
        if page:
            await page.close()
