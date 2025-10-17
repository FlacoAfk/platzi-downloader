import asyncio
import functools
import json
import os
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import aiofiles
from playwright.async_api import BrowserContext, Page, async_playwright
from rich import box, print
from rich.live import Live
from rich.table import Table

from .collectors import (
    get_course_title,
    get_draft_chapters,
    get_learning_path_courses,
    get_learning_path_title,
    get_unit,
)
from .constants import HEADERS, LOGIN_DETAILS_URL, LOGIN_URL, SESSION_FILE
from .dash import dash_dl
from .helpers import read_json, write_json
from .logger import Logger
from .m3u8 import m3u8_dl
from .models import TypeUnit, User
from .progress_tracker import ProgressTracker
from .utils import clean_string, download, progressive_scroll, safe_path


def login_required(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        self = args[0]
        if not isinstance(self, AsyncPlatzi):
            Logger.error(f"{login_required.__name__} can only decorate Platzi class.")
            return
        if not self.loggedin:
            Logger.error("Login first!")
            return
        return await func(*args, **kwargs)

    return wrapper


def try_except_request(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        self = args[0]
        if not isinstance(self, AsyncPlatzi):
            Logger.error(
                f"{try_except_request.__name__} can only decorate Platzi class."
            )
            return

        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if str(e):
                Logger.error(e)
        return

    return wrapper



class AsyncPlatzi:
    def __init__(self, headless=True, browser_type="firefox"):
        self.loggedin = False
        self.browser_type = browser_type.lower()  # 'firefox' or 'chromium'
        self.headless = headless  # Respect user's headless preference for all browsers
        self.user = None
        self.progress = ProgressTracker()

    async def __aenter__(self):
        from .constants import USER_AGENT
        
        self._playwright = await async_playwright().start()
        
        # Launch browser based on browser_type
        if self.browser_type == "chromium":
            if self.headless:
                mode_text = "minimized mode (1x1px off-screen)"
                Logger.info(f"🌐 Using Chromium browser ({mode_text})")
            else:
                mode_text = "visible mode"
                Logger.info(f"🌐 Using Chromium browser ({mode_text})")
            
            Logger.warning("⚠️  IMPORTANT: Chromium only supports HLS videos (.m3u8)")
            Logger.warning("⚠️  Videos only available in DASH (.mpd) will be SKIPPED with 403 error")
            Logger.info("✅ Recommended: Use Firefox for full compatibility: --browser firefox")
            
            launch_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
            ]
            
            # Minimized mode: window off-screen at 1x1px
            if self.headless:
                launch_args.extend([
                    '--window-position=-2000,-2000',  # Move off-screen
                    '--window-size=1,1',  # Minimal window (1x1px)
                ])
            
            # Always use headless=False to have a physical window
            self._browser = await self._playwright.chromium.launch(
                headless=False,
                args=launch_args
            )
        else:  # firefox (default)
            if self.headless:
                mode_text = "headless mode"
                Logger.info(f"🦊 Using Firefox browser ({mode_text})")
                Logger.info("💡 Firefox headless mode works perfectly and avoids detection issues")
            else:
                mode_text = "visible mode"
                Logger.info(f"🦊 Using Firefox browser ({mode_text})")
            
            # Firefox: Use true headless mode for "minimized" (works great in Firefox)
            # Unlike Chromium, Firefox headless doesn't have detection issues
            self._browser = await self._playwright.firefox.launch(
                headless=self.headless,  # True headless works perfectly in Firefox
                firefox_user_prefs={
                    # Network settings
                    'network.proxy.type': 0,
                    'network.dns.disablePrefetch': True,
                    
                    # Disable ALL security blocks that interfere with page loading
                    'security.mixed_content.block_active_content': False,  # Allow mixed HTTP/HTTPS
                    'security.mixed_content.block_display_content': False,
                    'security.mixed_content.upgrade_display_content': False,
                    'security.insecure_connection_text.enabled': False,
                    'security.certerrors.permanentOverride': True,
                    'security.enterprise_roots.enabled': True,
                    
                    # Disable tracking protection (causes blocks)
                    'privacy.trackingprotection.enabled': False,
                    'privacy.trackingprotection.pbmode.enabled': False,
                    'privacy.trackingprotection.cryptomining.enabled': False,
                    'privacy.trackingprotection.fingerprinting.enabled': False,
                    'privacy.trackingprotection.socialtracking.enabled': False,
                    
                    # Disable safe browsing (can block pages)
                    'browser.safebrowsing.malware.enabled': False,
                    'browser.safebrowsing.phishing.enabled': False,
                    'browser.safebrowsing.downloads.enabled': False,
                    
                    # Performance and stability
                    'browser.cache.disk.enable': True,
                    'browser.cache.memory.enable': True,
                    'media.volume_scale': '0.0',  # Mute audio
                    'dom.webdriver.enabled': False,  # Hide webdriver flag
                    
                    # Disable popup blockers
                    'dom.disable_open_during_load': False,
                    'privacy.popups.showBrowserMessage': False,
                }
            )
        
        # Create browser context with optimized settings
        self._context = await self._browser.new_context(
            user_agent=USER_AGENT,
            viewport={'width': 1920, 'height': 1080},
            locale='es-ES',
            timezone_id='America/Mexico_City',
            bypass_csp=True,
            ignore_https_errors=True,
        )
        
        # Set default timeout to 60 seconds for all operations (better for Firefox headless)
        self._context.set_default_timeout(60000)
        
        # Add anti-detection script
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.navigator.chrome = {runtime: {}};
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['es-ES', 'es', 'en-US', 'en']
            });
        """)

        try:
            await self._load_state()
        except Exception:
            pass

        await self._set_profile()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Generate and save final report
        print("\n")
        print(self.progress.generate_report())
        self.progress.save_final_report()
        
        await self._context.close()
        await self._browser.close()
        await self._playwright.stop()

    @property
    async def page(self) -> Page:
        new_page = await self._context.new_page()
        # Minimize Chromium pages immediately after creation
        if self.browser_type == "chromium":
            await self._minimize_page(new_page)
        return new_page

    @property
    def context(self) -> BrowserContext:
        return self._context

    @try_except_request
    async def _set_profile(self) -> None:
        try:
            data = await self.get_json(LOGIN_DETAILS_URL)
            self.user = User(**data)
        except Exception:
            return

        if self.user.is_authenticated:
            self.loggedin = True
            Logger.info(f"Hi, {self.user.username}!\n")

    async def _minimize_page(self, page: Page) -> None:
        """Minimize Chromium page on Windows to avoid being a nuisance."""
        try:
            import platform
            if platform.system() == "Windows":
                try:
                    import ctypes
                    import time
                    
                    # Small delay to let window appear
                    time.sleep(0.3)
                    
                    # Get foreground window (most recently created)
                    hwnd = ctypes.windll.user32.GetForegroundWindow()
                    if hwnd:
                        # SW_MINIMIZE = 6, minimize to taskbar
                        SW_MINIMIZE = 6
                        ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)
                except Exception:
                    pass
        except Exception:
            pass

    @try_except_request
    async def login(self) -> None:
        Logger.info("Please login, in the opened browser")
        Logger.info("You have to login manually, you have 2 minutes to do it")

        page = await self.page
        await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)  # 60s for Firefox headless
        try:
            avatar = await page.wait_for_selector(
                ".styles-module_Menu__Avatar__FTuh-",
                timeout=2 * 60 * 1000,
            )
            if avatar:
                self.loggedin = True
                await self._save_state()
                Logger.info("Logged in successfully")
        except Exception:
            raise Exception("Login failed")
        finally:
            await page.close()

    @try_except_request
    async def logout(self):
        SESSION_FILE.unlink(missing_ok=True)
        Logger.info("Logged out successfully")

    async def _goto_with_retry(self, page: Page, url: str, max_retries: int = 2) -> None:
        """Navigate to URL with retry logic for better reliability."""
        for attempt in range(max_retries):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)  # 60s for Firefox headless
                return  # Success
            except Exception as e:
                if attempt < max_retries - 1:
                    Logger.warning(f"⚠️  Navigation failed (attempt {attempt + 1}/{max_retries}): {str(e)[:100]}")
                    Logger.info(f"🔄 Retrying in 1 second...")
                    await asyncio.sleep(1)  # Reduced from 2s to 1s
                else:
                    # Last attempt failed
                    raise Exception(f"Failed to load page after {max_retries} attempts: {str(e)}")

    @try_except_request
    @login_required
    async def download(self, url: str, **kwargs):
        # Start progress tracking session
        self.progress.start_session()
        
        page = await self.page
        # Use retry logic for more reliable navigation
        await self._goto_with_retry(page, url)

        # Check if it's a learning path
        if "/ruta/" in url:
            await self._download_learning_path(page, url, **kwargs)
            return

        # Close page and use the _download_course method
        await page.close()
        await self._download_course(url, **kwargs)

    @try_except_request
    @login_required
    async def _download_learning_path(self, page: Page, url: str, **kwargs):
        """Download all courses from a learning path."""
        try:
            # Get learning path title
            path_title = await get_learning_path_title(page)
            path_id = urlparse(url).path  # Use URL path as unique ID
            
            Logger.info(f"\n{'='*100}")
            Logger.info(f"Learning Path: {path_title}")
            Logger.info(f"{'='*100}\n")

            # Get all course URLs from the learning path
            course_urls = await get_learning_path_courses(page)
            Logger.info(f"Found {len(course_urls)} courses in this learning path\n")
            
            # Register learning path
            self.progress.start_learning_path(path_id, path_title, len(course_urls))

            # Close the initial page
            await page.close()

            # Download each course with learning path context
            for idx, course_url in enumerate(course_urls, 1):
                course_id = urlparse(course_url).path
                
                # Check if course was already completed AND has no pending units
                if self.progress.should_skip_course(course_id):
                    Logger.info(f"⏭️  Skipping course {idx}/{len(course_urls)} (already completed, no pending units): {course_url}")
                    continue
                
                # Check if course has pending units
                if self.progress.has_pending_units(course_id):
                    Logger.info(f"🔄 Re-processing course {idx}/{len(course_urls)} (has pending units): {course_url}")
                
                Logger.info(f"\n{'='*100}")
                Logger.info(f"Downloading course {idx}/{len(course_urls)}: {course_url}")
                Logger.info(f"{'='*100}\n")
                
                # Download individual course with learning path context
                await self._download_course(
                    course_url, 
                    learning_path_title=path_title,
                    learning_path_id=path_id,
                    course_index=idx,
                    **kwargs
                )

            # Mark learning path as completed
            self.progress.complete_learning_path(path_id)
            
            Logger.info(f"\n{'='*100}")
            Logger.info(f"✅ Learning Path '{path_title}' completed! All {len(course_urls)} courses downloaded.")
            Logger.info(f"{'='*100}\n")

        except Exception as e:
            Logger.error(f"Error downloading learning path: {e}")
            await page.close()
            raise

    @try_except_request
    @login_required
    async def _download_course(self, url: str, **kwargs):
        """Download a single course."""
        course_id = urlparse(url).path
        
        # Check if course was already completed AND has no pending units
        if self.progress.should_skip_course(course_id):
            Logger.info(f"⏭️  Course already completed (no pending units), skipping: {url}")
            return
        
        # Check if course has pending units
        if self.progress.has_pending_units(course_id):
            Logger.info(f"🔄 Re-processing course (has pending units): {url}")
        
        page = await self.page
        
        try:
            # Use retry logic for more reliable navigation
            await self._goto_with_retry(page, url)

            # course title
            course_title = await get_course_title(page)
            
            # Register course start
            learning_path_id = kwargs.get("learning_path_id")
            self.progress.start_course(course_id, course_title, learning_path_id)

            # Check if this is part of a learning path
            learning_path_title = kwargs.get("learning_path_title")
            course_index = kwargs.get("course_index")
            
            # download directory
            # Apply length limits to avoid Windows 260 char path limit
            if learning_path_title and course_index is not None:
                # Structure: [Learning Path]/[N. Course]/
                DL_DIR = Path("Courses") / clean_string(learning_path_title, max_length=60) / f"{course_index}. {clean_string(course_title, max_length=60)}"
            else:
                # Original structure for individual courses
                DL_DIR = Path("Courses") / clean_string(course_title, max_length=80)
            
            DL_DIR.mkdir(parents=True, exist_ok=True)

            # save page as mhtml
            presentation_path = DL_DIR / "presentation.mhtml"
            await self.save_page(page, path=presentation_path, **kwargs)

            # iterate over chapters
            draft_chapters = await get_draft_chapters(page)

            # --- Course Details Table ---
            table = Table(title=course_title, caption="processing...", caption_style="green", title_style="green", header_style="green", footer_style="green", show_footer=True, box=box.SQUARE_DOUBLE_HEAD)
            table.add_column("Sections", style="green", footer="Total", no_wrap=True)
            table.add_column("Lessons", style="green", footer="0", justify="center")

            total_units = 0

            with Live(table, refresh_per_second=4):  # update 4 times a second to feel fluid
                for idx, section in enumerate(draft_chapters, 1):
                    time.sleep(0.3)  # arbitrary delay
                    num_units = len(section.units)
                    total_units += num_units
                    table.add_row(f"{idx}-{section.name}", str(len(section.units)))
                    table.columns[1].footer = str(total_units)  # Update footer dynamically

            for idx, draft_chapter in enumerate(draft_chapters, 1):
                Logger.info(f"Creating directory: {draft_chapter.name}")

                CHAP_DIR = DL_DIR / f"{idx}. {clean_string(draft_chapter.name, max_length=60)}"
                CHAP_DIR.mkdir(parents=True, exist_ok=True)

                # iterate over units
                for jdx, draft_unit in enumerate(draft_chapter.units, 1):
                    unit_id = urlparse(draft_unit.url).path
                    
                    # Check if unit was already completed
                    if self.progress.should_skip_unit(course_id, unit_id):
                        Logger.info(f"⏭️  Skipping unit (already completed): {draft_unit.title}")
                        continue
                    
                    # Check if unit exists in checkpoint with special status
                    existing_unit = None
                    if course_id in self.progress.data["courses"]:
                        existing_unit = self.progress.data["courses"][course_id].get("units", {}).get(unit_id)
                    
                    if existing_unit:
                        if existing_unit["status"] == "pending":
                            Logger.info(f"🔄 Retrying pending unit: {draft_unit.title}")
                        elif existing_unit["status"] == "failed":
                            Logger.warning(f"⚠️  Retrying previously failed unit: {draft_unit.title}")
                            Logger.warning(f"    Previous error: {existing_unit.get('error', 'Unknown')}")
                    
                    # Add small delay between units to avoid overwhelming the server
                    # This helps prevent timeouts and rate limiting
                    if jdx > 1:  # Skip delay for first unit
                        await asyncio.sleep(1.5)  # Reduced to 1s for faster processing
                    
                    # Register unit start (or restart)
                    self.progress.start_unit(course_id, unit_id, draft_unit.title)
                    
                    try:
                        unit = await get_unit(self.context, draft_unit.url, browser_type=self.browser_type)
                    except Exception as e:
                        error_msg = f"Error collecting unit data: {str(e)}"
                        Logger.error(f"{error_msg} for '{draft_unit.title}'")
                        Logger.warning("Skipping this unit and continuing with the next one...")
                        self.progress.fail_unit(course_id, unit_id, error_msg)
                        continue
                    
                    try:
                        file_name = f"{jdx}. {clean_string(unit.title, max_length=50)}"

                        # download video
                        if unit.video:
                            dst = CHAP_DIR / f"{file_name}.mp4"
                            Logger.print(f"[{dst.name}]", "[DOWNLOADING-VIDEO]")
                            
                            # For Chromium: Try primary URL (m3u8 preferred), fallback to DASH if needed
                            # For Firefox: Both formats work fine, no fallback needed
                            video_downloaded = False
                            
                            # Special handling for Chromium
                            if self.browser_type == "chromium":
                                # Check if primary URL is DASH without m3u8 alternative
                                if '.mpd' in unit.video.url and not unit.video.fallback_url:
                                    # Chromium + DASH only = guaranteed 403 error
                                    error_msg = "Video only available in DASH format (.mpd) which is incompatible with Chromium (403 Forbidden)"
                                    Logger.error(f"❌ {error_msg}")
                                    Logger.error(f"💡 Solution: Use Firefox instead: platzi download {url} --browser firefox")
                                    raise Exception(error_msg)
                                
                                # If we have fallback, try primary first
                                if unit.video.fallback_url:
                                    try:
                                        if '.mpd' in unit.video.url:
                                            Logger.warning(f"⚠️  Downloading DASH (.mpd) with Chromium (may fail)")
                                            await dash_dl(unit.video.url, dst, headers=HEADERS, **kwargs)
                                        else:
                                            await m3u8_dl(unit.video.url, dst, headers=HEADERS, **kwargs)
                                        video_downloaded = True
                                        Logger.info(f"✅ Video downloaded successfully using primary URL")
                                    except Exception as primary_error:
                                        Logger.warning(f"⚠️  Primary URL failed: {str(primary_error)[:100]}")
                                        Logger.info(f"🔄 Trying fallback URL (DASH)...")
                                        try:
                                            await dash_dl(unit.video.fallback_url, dst, headers=HEADERS, **kwargs)
                                            video_downloaded = True
                                            Logger.info(f"✅ Video downloaded successfully using fallback URL")
                                        except Exception as fallback_error:
                                            Logger.error(f"❌ Fallback URL also failed: {str(fallback_error)[:100]}")
                                            raise Exception(f"Both primary and fallback download failed. Primary: {str(primary_error)[:100]}, Fallback: {str(fallback_error)[:100]}")
                                else:
                                    # Chromium without fallback but has m3u8
                                    await m3u8_dl(unit.video.url, dst, headers=HEADERS, **kwargs)
                                    video_downloaded = True
                            else:
                                # Firefox: Both formats work fine
                                if '.mpd' in unit.video.url:
                                    await dash_dl(unit.video.url, dst, headers=HEADERS, **kwargs)
                                else:
                                    await m3u8_dl(unit.video.url, dst, headers=HEADERS, **kwargs)
                                video_downloaded = True

                            # download subtitles
                            subs = unit.video.subtitles_url
                            if subs:
                                for sub in subs:
                                    lang = "_es" if "ES" in sub else "_en" if "EN" in sub else "_pt" if "PT" in sub else ""

                                    dst = CHAP_DIR / f"{file_name}{lang}.vtt"
                                    Logger.print(f"[{dst.name}]", "[DOWNLOADING-SUBS]")
                                    await download(sub, dst, **kwargs)

                            # download resources
                            if unit.resources:
                                # download summary
                                summary = unit.resources.summary
                                if summary:
                                    dst = CHAP_DIR / f"{file_name}_summary.html"
                                    Logger.print(f"[{dst.name}]", "[SAVING-SUMMARY]")
                                    # Add beautiful styling to summary
                                    styled_summary = f"""<!DOCTYPE html>
                                    <html lang="es">
                                    <head>
                                        <meta charset="UTF-8">
                                        <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                        <title>{unit.title} - Resumen</title>
                                        <style>
                                            body {{
                                                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                                                line-height: 1.8;
                                                max-width: 900px;
                                                margin: 0 auto;
                                                padding: 40px 20px;
                                                background-color: #f5f5f5;
                                                color: #2c3e50;
                                            }}
                                            .container {{
                                                background-color: #ffffff;
                                                padding: 40px;
                                                border-radius: 8px;
                                                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                                            }}
                                            h1, h2, h3, h4, h5, h6 {{
                                                color: #1a1a1a;
                                                margin-top: 1.5em;
                                                margin-bottom: 0.5em;
                                                font-weight: 600;
                                            }}
                                            h1 {{
                                                border-bottom: 3px solid #3498db;
                                                padding-bottom: 10px;
                                                font-size: 2em;
                                            }}
                                            h2 {{
                                                border-bottom: 2px solid #95a5a6;
                                                padding-bottom: 8px;
                                                font-size: 1.5em;
                                            }}
                                            p {{
                                                margin-bottom: 1em;
                                                color: #34495e;
                                            }}
                                            code {{
                                                background-color: #ecf0f1;
                                                padding: 2px 6px;
                                                border-radius: 3px;
                                                font-family: 'Courier New', monospace;
                                                color: #e74c3c;
                                                font-size: 0.9em;
                                            }}
                                            pre {{
                                                background-color: #2c3e50;
                                                color: #ecf0f1;
                                                padding: 20px;
                                                border-radius: 5px;
                                                overflow-x: auto;
                                                line-height: 1.5;
                                            }}
                                            pre code {{
                                                background-color: transparent;
                                                color: #ecf0f1;
                                                padding: 0;
                                            }}
                                            ul, ol {{
                                                margin-bottom: 1em;
                                                padding-left: 30px;
                                                color: #34495e;
                                            }}
                                            li {{
                                                margin-bottom: 0.5em;
                                            }}
                                            blockquote {{
                                                border-left: 4px solid #3498db;
                                                padding-left: 20px;
                                                margin: 20px 0;
                                                color: #555;
                                                font-style: italic;
                                                background-color: #f8f9fa;
                                                padding: 15px 20px;
                                                border-radius: 0 4px 4px 0;
                                            }}
                                            a {{
                                                color: #3498db;
                                                text-decoration: none;
                                                border-bottom: 1px solid transparent;
                                                transition: border-bottom 0.3s;
                                            }}
                                            a:hover {{
                                                border-bottom: 1px solid #3498db;
                                            }}
                                            img {{
                                                max-width: 100%;
                                                height: auto;
                                                border-radius: 5px;
                                                margin: 20px 0;
                                                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                                            }}
                                            table {{
                                                border-collapse: collapse;
                                                width: 100%;
                                                margin: 20px 0;
                                            }}
                                            th, td {{
                                                border: 1px solid #ddd;
                                                padding: 12px;
                                                text-align: left;
                                            }}
                                            th {{
                                                background-color: #34495e;
                                                color: white;
                                                font-weight: 600;
                                            }}
                                            tr:nth-child(even) {{
                                                background-color: #f8f9fa;
                                            }}
                                            .header {{
                                                text-align: center;
                                                margin-bottom: 30px;
                                            }}
                                            .header h1 {{
                                                border: none;
                                                margin-bottom: 10px;
                                            }}
                                            .date {{
                                                color: #7f8c8d;
                                                font-size: 0.9em;
                                            }}
                                        </style>
                                    </head>
                                    <body>
                                        <div class="container">
                                            <div class="header">
                                                <h1>{unit.title}</h1>
                                                <p class="date">Resumen del curso</p>
                                            </div>
                                            {summary}
                                        </div>
                                    </body>
                                    </html>"""
                                    with open(dst, 'w', encoding='utf-8') as f:
                                        f.write(styled_summary)
                                
                                # download files
                                files = unit.resources.files_url
                                if files:
                                    for archive in files:
                                        file_name_archive = unquote(os.path.basename(archive))
                                        # Separate name and extension before cleaning
                                        name_part = os.path.splitext(file_name_archive)[0]
                                        ext_part = os.path.splitext(file_name_archive)[1]
                                        # Clean only the name, not the extension
                                        name_part = clean_string(name_part, max_length=50)
                                        file_name_archive = f"{name_part}{ext_part}"
                                        dst = CHAP_DIR / f"{jdx}. {file_name_archive}"
                                        Logger.print(f"[{dst.name}]", "[DOWNLOADING-FILES]")
                                        await download(archive, dst)

                                # download readings
                                readings = unit.resources.readings_url
                                if readings:
                                    dst = CHAP_DIR / f"{jdx}. Lecturas recomendadas.txt"
                                    Logger.print(f"[{dst.name}]", "[SAVING-READINGS]")
                                    with open(dst, 'w', encoding='utf-8') as f:
                                        for lecture in readings:
                                            f.write(lecture + "\n")

                        # download lecture
                        if unit.type == TypeUnit.LECTURE:
                            # Ensure filename isn't too long
                            safe_file_name = clean_string(unit.title, max_length=50)
                            dst = CHAP_DIR / f"{jdx}. {safe_file_name}.mhtml"
                            Logger.print(f"[{dst.name}]", "[DOWNLOADING-LECTURE]")
                            await self.save_page(unit.url, path=dst, wait_for_images=True, **kwargs)
                        
                        # Mark unit as completed
                        self.progress.complete_unit(course_id, unit_id)
                        
                    except Exception as e:
                        error_msg = f"Error downloading unit: {str(e)}"
                        Logger.error(f"{error_msg} for '{unit.title}'")
                        self.progress.fail_unit(course_id, unit_id, error_msg)
                        # Continue with next unit instead of stopping

            # Mark course as completed
            self.progress.complete_course(course_id)
            print("=" * 100)
            
        except Exception as e:
            error_msg = f"Error downloading course: {str(e)}"
            Logger.error(error_msg)
            self.progress.fail_course(course_id, error_msg)
            raise
        finally:
            await page.close()
    @try_except_request
    async def save_page(
        self,
        src: str | Page,
        path: str | Path = "source.mhtml",
        **kwargs,
    ):
        overwrite: bool = kwargs.get("overwrite", False)
        wait_for_images: bool = kwargs.get("wait_for_images", False)
        
        # Ensure path doesn't exceed Windows limit
        path = safe_path(Path(path))

        if not overwrite and path.exists():
            return

        if isinstance(src, str):
            page = await self.page
            try:
                # Try with networkidle first, but with timeout handling
                await page.goto(src, wait_until="domcontentloaded", timeout=60000)  # 60s for Firefox headless
                # Wait for the page to be mostly ready
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    # If networkidle times out, just continue with domcontentloaded
                    await page.wait_for_load_state("domcontentloaded")
            except Exception:
                # If still fails, try with basic load
                await page.goto(src, wait_until="load", timeout=60000)  # 60s for Firefox headless
        else:
            page = src

        await progressive_scroll(page)

        try:
            # Try to wait for additional content, but don't fail if timeout
            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass  # Continue anyway
            
            await asyncio.sleep(1)  # Brief wait for dynamic content
            
            # Wait for all images to load completely (only for lectures)
            if wait_for_images:
                Logger.info("Waiting for all images to load...")
                images_loaded = await page.evaluate("""
                    async () => {
                        // Function to process images in a document or shadowRoot
                        const processImages = (root) => {
                            const images = Array.from(root.querySelectorAll('img'));
                            
                            images.forEach(img => {
                                // Force lazy-loaded images to load
                                if (img.loading === 'lazy') {
                                    img.loading = 'eager';
                                }
                                
                                // Handle data-src attributes
                                if (img.dataset.src && !img.src) {
                                    img.src = img.dataset.src;
                                }
                                if (img.dataset.srcset && !img.srcset) {
                                    img.srcset = img.dataset.srcset;
                                }
                                
                                // Handle other lazy load attributes
                                ['data-lazy-src', 'data-original', 'data-lazy'].forEach(attr => {
                                    const value = img.getAttribute(attr);
                                    if (value && !img.src) {
                                        img.src = value;
                                    }
                                });
                            });
                            
                            return images;
                        };
                        
                        // Collect all images from main document
                        let allImages = processImages(document);
                        
                        // Process iframes (try to access if same-origin)
                        const iframes = Array.from(document.querySelectorAll('iframe'));
                        for (const iframe of iframes) {
                            try {
                                if (iframe.contentDocument) {
                                    const iframeImages = processImages(iframe.contentDocument);
                                    allImages = allImages.concat(iframeImages);
                                }
                            } catch (e) {
                                // Cross-origin iframe, skip
                                console.warn('Cannot access iframe:', e);
                            }
                        }
                        
                        // Process shadow DOMs
                        const shadowHosts = document.querySelectorAll('*');
                        shadowHosts.forEach(host => {
                            if (host.shadowRoot) {
                                const shadowImages = processImages(host.shadowRoot);
                                allImages = allImages.concat(shadowImages);
                            }
                        });
                        
                        // Wait for all images to load
                        const imagePromises = allImages.map(img => {
                            if (img.complete && img.naturalHeight !== 0) {
                                return Promise.resolve();
                            }
                            
                            return new Promise((resolve) => {
                                const timeout = setTimeout(() => {
                                    console.warn('Image load timeout:', img.src);
                                    resolve();
                                }, 45000); // 45 second timeout per image
                                
                                img.onload = () => {
                                    clearTimeout(timeout);
                                    resolve();
                                };
                                img.onerror = () => {
                                    clearTimeout(timeout);
                                    console.warn('Image load error:', img.src);
                                    resolve();
                                };
                                
                                // Trigger reload if needed
                                if (!img.complete && img.src) {
                                    const src = img.src;
                                    img.src = '';
                                    img.src = src;
                                }
                            });
                        });
                        
                        await Promise.all(imagePromises);
                        
                        return {
                            totalImages: allImages.length,
                            loadedImages: allImages.filter(img => img.complete && img.naturalHeight !== 0).length
                        };
                    }
                """)
                
                Logger.info(f"Images loaded: {images_loaded['loadedImages']}/{images_loaded['totalImages']}")
                
                # Additional wait to ensure images are in browser cache and fully rendered
                await asyncio.sleep(3)
            
            # Fix image sizes in Viewer_Viewer__BrpuP divs before capturing
            await page.evaluate("""
                () => {
                    const viewerDivs = document.querySelectorAll('.Viewer_Viewer__BrpuP');
                    viewerDivs.forEach(div => {
                        const images = div.querySelectorAll('img');
                        images.forEach(img => {
                            img.style.width = '100%';
                            img.style.height = 'auto';
                            img.removeAttribute('height');
                            img.setAttribute('width', '80%');
                        });
                    });
                }
            """)
            
            # Convert images to base64 data URLs to ensure they're included in MHTML
            if wait_for_images:
                Logger.info("Converting images to base64 for MHTML...")
                await page.evaluate("""
                    async () => {
                        const convertImageToDataURL = async (img) => {
                            if (!img.src || img.src.startsWith('data:')) {
                                return; // Already a data URL or no source
                            }
                            
                            try {
                                const canvas = document.createElement('canvas');
                                const ctx = canvas.getContext('2d');
                                
                                // Wait for image to be fully loaded
                                if (!img.complete) {
                                    await new Promise((resolve) => {
                                        img.onload = resolve;
                                        img.onerror = resolve;
                                        setTimeout(resolve, 5000);
                                    });
                                }
                                
                                canvas.width = img.naturalWidth || img.width;
                                canvas.height = img.naturalHeight || img.height;
                                
                                if (canvas.width > 0 && canvas.height > 0) {
                                    ctx.drawImage(img, 0, 0);
                                    try {
                                        const dataURL = canvas.toDataURL('image/png');
                                        img.src = dataURL;
                                    } catch (e) {
                                        // CORS error, skip this image
                                        console.warn('CORS error converting image:', img.src, e);
                                    }
                                }
                            } catch (e) {
                                console.warn('Error converting image to base64:', img.src, e);
                            }
                        };
                        
                        const allImages = Array.from(document.querySelectorAll('img'));
                        
                        // Process images in batches to avoid overwhelming the browser
                        const batchSize = 10;
                        for (let i = 0; i < allImages.length; i += batchSize) {
                            const batch = allImages.slice(i, i + batchSize);
                            await Promise.all(batch.map(img => convertImageToDataURL(img)));
                        }
                        
                        return { converted: allImages.length };
                    }
                """)
                Logger.info("Image conversion complete")
                
                # Additional wait to ensure conversion is fully processed
                await asyncio.sleep(2)
            
            # Extract ONLY the educational content (Viewer_Viewer section)
            content_extraction = await page.evaluate("""
                () => {
                    // Find the main educational content
                    const mainContent = document.querySelector('.page_Classes__main__g6m_Q');
                    const viewerContent = document.querySelector('.Viewer_Viewer__pn_05') || 
                                        document.querySelector('[class*="Viewer_Viewer"]');
                    
                    if (!viewerContent && !mainContent) {
                        return {
                            content: document.body.innerHTML,
                            hasContent: false,
                            hasInteractive: false
                        };
                    }
                    
                    // Use viewer content if available, otherwise main content
                    const contentToExtract = viewerContent || mainContent;
                    
                    // Check for interactive content
                    const codeBlocks = contentToExtract.querySelectorAll('pre code, [class*="language-"], .highlight, .codehilite');
                    const sandboxes = contentToExtract.querySelectorAll('iframe[src*="codesandbox"], iframe[src*="stackblitz"], iframe[src*="codepen"], iframe[sandbox]');
                    const hasInteractive = codeBlocks.length > 0 || sandboxes.length > 0;
                    
                    return {
                        content: contentToExtract.innerHTML,
                        hasContent: true,
                        hasInteractive: hasInteractive,
                        title: document.querySelector('h1')?.textContent || 'Clase'
                    };
                }
            """)
            
            # If we extracted content successfully, create a clean HTML file
            if content_extraction['hasContent'] and wait_for_images:
                Logger.info(f"Extracting educational content - Interactive: {content_extraction['hasInteractive']}")
                
                # Create a clean HTML with only the educational content
                clean_html = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{content_extraction['title']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1, h2, h3, h4, h5, h6 {{
            margin: 1.5em 0 0.5em;
            color: #2c3e50;
        }}
        p {{
            margin: 1em 0;
        }}
        img {{
            width: 80%;
            height: auto;
            display: block;
            margin: 1em auto;
            border-radius: 4px;
        }}
        pre {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 20px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 1.5em 0;
            line-height: 1.5;
        }}
        code {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.9em;
        }}
        pre code {{
            background: none;
            padding: 0;
        }}
        ul, ol {{
            margin: 1em 0 1em 2em;
        }}
        li {{
            margin: 0.5em 0;
        }}
        a {{
            color: #0066cc;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        blockquote {{
            border-left: 4px solid #0066cc;
            padding-left: 20px;
            margin: 1.5em 0;
            color: #666;
            font-style: italic;
        }}
        iframe {{
            max-width: 100%;
            margin: 1.5em 0;
            border: 1px solid #ddd;
            border-radius: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 1.5em 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border: 1px solid #ddd;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
        }}
        /* Preserve code syntax highlighting classes */
        .token {{ font-family: 'Courier New', Courier, monospace; }}
        .token.comment {{ color: #6a9955; }}
        .token.keyword {{ color: #569cd6; }}
        .token.string {{ color: #ce9178; }}
        .token.function {{ color: #dcdcaa; }}
        .token.operator {{ color: #d4d4d4; }}
        .token.number {{ color: #b5cea8; }}
    </style>
</head>
<body>
    <div class="container">
        {content_extraction['content']}
    </div>
</body>
</html>
"""
                
                # Save the clean HTML
                if path.suffix.lower() == '.mhtml':
                    path = path.with_suffix('.html')
                
                async with aiofiles.open(path, "w", encoding="utf-8") as file:
                    await file.write(clean_html)
                
                Logger.info(f"Page saved as clean HTML: {path.name}")
            
            # Fallback: If content extraction failed, use the old method
            elif wait_for_images:
                Logger.warning("Content extraction failed, using fallback method...")
                
                # Embed all external CSS and JS inline
                await page.evaluate("""
                    async () => {
                        // Inline all external stylesheets
                        const styleSheets = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
                        for (const link of styleSheets) {
                            try {
                                const href = link.href;
                                if (href && !href.startsWith('data:') && !href.startsWith('blob:')) {
                                    const response = await fetch(href);
                                    const cssText = await response.text();
                                    const style = document.createElement('style');
                                    style.setAttribute('data-original-href', href);
                                    style.textContent = cssText;
                                    link.parentNode.insertBefore(style, link);
                                    link.remove();
                                }
                            } catch (e) {
                                console.warn('Could not inline stylesheet:', link.href, e);
                            }
                        }
                        
                        // Try to inline external scripts (non-async, non-module)
                        const scripts = Array.from(document.querySelectorAll('script[src]'));
                        for (const script of scripts) {
                            try {
                                const src = script.src;
                                if (src && !src.startsWith('data:') && !src.startsWith('blob:') && !script.hasAttribute('async') && !script.type.includes('module')) {
                                    // Only inline if same-origin or CORS allows
                                    const response = await fetch(src);
                                    const jsText = await response.text();
                                    const inlineScript = document.createElement('script');
                                    inlineScript.setAttribute('data-original-src', src);
                                    inlineScript.textContent = jsText;
                                    script.parentNode.insertBefore(inlineScript, script);
                                    script.remove();
                                }
                            } catch (e) {
                                // Keep external script if we can't inline it (CORS, etc.)
                                console.warn('Could not inline script:', script.src, e);
                            }
                        }
                    }
                """)
                
                await asyncio.sleep(1);
                
                # Get the complete HTML with all resources embedded
                content = await page.content()
                
                # Change extension to .html if it was .mhtml
                if path.suffix.lower() == '.mhtml':
                    path = path.with_suffix('.html')
                
                async with aiofiles.open(path, "w", encoding="utf-8") as file:
                    await file.write(content)
                
                Logger.info(f"Page saved as interactive HTML with embedded resources: {path.name}")
            
            # Use different save methods depending on browser type
            elif self.browser_type == "chromium":
                # Chromium supports CDP and MHTML
                try:
                    client = await page.context.new_cdp_session(page)
                    
                    # Enable necessary domains for better resource capture
                    await client.send("Network.enable")
                    await client.send("Page.enable")
                    
                    # Wait a bit more to ensure all resources are ready
                    await asyncio.sleep(1)
                    
                    response = await client.send("Page.captureSnapshot", {"format": "mhtml"})
                    async with aiofiles.open(path, "w", encoding="utf-8", newline="\n") as file:
                        await file.write(response["data"])
                    
                    if wait_for_images:
                        Logger.info(f"Page saved successfully with all images (MHTML): {path.name}")
                    else:
                        Logger.info(f"Page saved successfully (MHTML): {path.name}")
                except Exception as cdp_error:
                    Logger.warning(f"CDP/MHTML failed, falling back to HTML: {str(cdp_error)}")
                    # Fallback to HTML with embedded images
                    content = await page.content()
                    # Change extension to .html if it was .mhtml
                    if path.suffix.lower() == '.mhtml':
                        path = path.with_suffix('.html')
                    async with aiofiles.open(path, "w", encoding="utf-8") as file:
                        await file.write(content)
                    Logger.info(f"Page saved as HTML with embedded images: {path.name}")
            else:
                # Firefox doesn't support CDP/MHTML, save as HTML
                content = await page.content()
                # Change extension to .html if it was .mhtml
                if path.suffix.lower() == '.mhtml':
                    path = path.with_suffix('.html')
                async with aiofiles.open(path, "w", encoding="utf-8") as file:
                    await file.write(content)
                
                if wait_for_images:
                    Logger.info(f"Page saved successfully with all images (HTML): {path.name}")
                else:
                    Logger.info(f"Page saved successfully (HTML): {path.name}")
                    
        except Exception as e:
            Logger.error(f"Error saving page: {str(e)}")
            # Try alternative method: save as HTML
            try:
                content = await page.content()
                # Change extension to .html if it was .mhtml
                if path.suffix.lower() == '.mhtml':
                    path = path.with_suffix('.html')
                async with aiofiles.open(path, "w", encoding="utf-8") as file:
                    await file.write(content)
                Logger.info(f"Page saved as HTML (fallback): {path.name}")
            except Exception:
                raise Exception(f"Error saving page: {str(e)}")

        if isinstance(src, str):
            await page.close()

    @try_except_request
    async def get_json(self, url: str) -> dict:
        page = await self.page
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)  # 60s for Firefox headless
        content = await page.locator("pre").first.text_content()
        await page.close()
        return json.loads(content or "{}")

    async def _save_state(self):
        cookies = await self.context.cookies()
        write_json(SESSION_FILE, cookies)

    async def _load_state(self):
        SESSION_FILE.touch()
        cookies = read_json(SESSION_FILE)
        await self.context.add_cookies(cookies)
