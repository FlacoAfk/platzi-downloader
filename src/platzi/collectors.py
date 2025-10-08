import asyncio

from playwright.async_api import BrowserContext, Page

from .cache import Cache
from .constants import PLATZI_URL
from .models import Chapter, Resource, TypeUnit, Unit, Video
from .utils import download_styles, get_m3u8_url, get_subtitles_url, slugify


@Cache.cache_async
async def get_learning_path_title(page: Page) -> str:
    """Get the title of a learning path from the page."""
    SELECTOR = ".LearningPathHero_LearningPathHero__FEDlM h1"
    EXCEPTION = Exception("No learning path title found")
    try:
        title = await page.locator(SELECTOR).first.text_content()
        if not title:
            raise EXCEPTION
    except Exception:
        await page.close()
        raise EXCEPTION

    return title


@Cache.cache_async
async def get_learning_path_courses(page: Page) -> list[str]:
    """Extract all course URLs from a learning path page."""
    SELECTOR = ".CoursesList_CoursesList__TfADh a.Course_Course__NKjCs"
    EXCEPTION = Exception("No courses found in learning path")
    
    try:
        locator = page.locator(SELECTOR)
        course_urls: list[str] = []
        
        count = await locator.count()
        if count == 0:
            raise EXCEPTION
        
        for i in range(count):
            href = await locator.nth(i).get_attribute("href")
            if href:
                # Complete the URL with the base domain
                full_url = PLATZI_URL + href if href.startswith("/") else href
                course_urls.append(full_url)
        
        if not course_urls:
            raise EXCEPTION
            
    except Exception as e:
        await page.close()
        raise EXCEPTION from e
    
    return course_urls


@Cache.cache_async
async def get_course_title(page: Page) -> str:
    SELECTOR = ".CourseHeader_CourseHeader__Title__yhjgH"
    EXCEPTION = Exception("No course title found")
    try:
        title = await page.locator(SELECTOR).first.text_content()
        if not title:
            raise EXCEPTION
    except Exception:
        await page.close()
        raise EXCEPTION

    return title


@Cache.cache_async
async def get_draft_chapters(page: Page) -> list[Chapter]:
    SELECTOR = ".Syllabus_Syllabus__bVYL_ article"
    EXCEPTION = Exception("No sections found")
    try:
        locator = page.locator(SELECTOR)

        chapters: list[Chapter] = []
        for i in range(await locator.count()):
            chapter_name = await locator.nth(i).locator("h2").first.text_content()

            if not chapter_name:
                raise EXCEPTION

            block_list_locator = locator.nth(i).locator(
                ".SyllabusSection_SyllabusSection__Materials__C2hlu a"
            )

            units: list[Unit] = []
            for j in range(await block_list_locator.count()):
                ITEM_LOCATOR = block_list_locator.nth(j)

                unit_url = await ITEM_LOCATOR.get_attribute("href")
                unit_title = await ITEM_LOCATOR.locator("h3").first.text_content()

                if not unit_url or not unit_title:
                    raise EXCEPTION

                units.append(
                    Unit(
                        type=TypeUnit.VIDEO,
                        title=unit_title,
                        url=PLATZI_URL + unit_url,
                        slug=slugify(unit_title),
                    )
                )

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

    return chapters


@Cache.cache_async
async def get_unit(context: BrowserContext, url: str) -> Unit:
    TYPE_SELECTOR = ".VideoPlayer"
    # Try multiple possible selectors for the title (Platzi may change their class names)
    TITLE_SELECTORS = [
        "h1.MaterialHeading_MaterialHeading__title__sDUKY",
        "h1[class*='MaterialHeading']",  # More flexible - matches any class containing MaterialHeading
        "main h1",  # Generic fallback
        "h1",  # Last resort
    ]
    EXCEPTION = Exception("Could not collect unit data")

    # --- NEW CONSTANTS ----
    SECTION_FILES = '//h4[normalize-space(text())="Archivos de la clase"]'
    SECTION_READING = '//h4[normalize-space(text())="Lecturas recomendadas"]'
    SECTION_LINKS = 'a.FilesAndLinks_Item__fR7g4'
    BUTTON_DOWNLOAD_ALL = 'a.Button.FilesTree_FilesTree__Download__nGUsL[href][download]'
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
        await page.goto(url, wait_until="domcontentloaded")

        await asyncio.sleep(5)  # delay to avoid rate limiting

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
            # If all selectors failed, log the page content for debugging
            print(f"ERROR: Could not find title for URL: {url}")
            print("Available h1 elements:")
            h1_elements = await page.locator("h1").all()
            for i, h1 in enumerate(h1_elements):
                h1_text = await h1.text_content()
                print(f"  h1[{i}]: {h1_text}")
            raise Exception(f"Could not find title on page: {url}")

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
            url=get_m3u8_url(content),
            subtitles_url=get_subtitles_url(content),
        )

        # --- Get resources and summary---
        html_summary = None

        files_section = page.locator(SECTION_FILES)
        next_sibling_files = files_section.locator(SIBLINGS)

        reading_section = page.locator(SECTION_READING)
        next_sibling_reading = reading_section.locator(SIBLINGS)

        download_all_button = page.locator(BUTTON_DOWNLOAD_ALL)

        file_links: list[str] = []
        readings_links: list[str] = []

        # Get "Archivos de la clase" if the section exists
        if await next_sibling_files.count() > 0:
            enlaces = next_sibling_files.locator(SECTION_LINKS)
            for i in range(await enlaces.count()):
                link = await enlaces.nth(i).get_attribute("href")
                if link:
                    file_links.append(link)

        # Get link of the download all button if it exists
        if await download_all_button.count() > 0:
            link = await download_all_button.first.get_attribute("href")
            if link:
                file_links.append(link)
        else:
            # Try alternative selector for download button
            alt_download_button = page.locator('a[download][target="_blank"]').filter(has_text="Descargar")
            if await alt_download_button.count() > 0:
                link = await alt_download_button.first.get_attribute("href")
                if link:
                    file_links.append(link)

        # Get "Lecturas recomendadas" if the section exists
        if await next_sibling_reading.count() > 0:
            enlaces = next_sibling_reading.locator(SECTION_LINKS)
            for i in range(await enlaces.count()):
                link = await enlaces.nth(i).get_attribute("href")
                if link:
                    readings_links.append(link)

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
        raise EXCEPTION from e

    finally:
        if page:
            await page.close()
