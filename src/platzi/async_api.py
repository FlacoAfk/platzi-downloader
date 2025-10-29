import asyncio
import functools
import json
import os
import shutil
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import aiofiles
from playwright.async_api import BrowserContext, Page, async_playwright
from rich import box, print
from rich.live import Live
from rich.table import Table
from tqdm import tqdm

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
                Logger.error(str(e), exception=e)
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
            extra_http_headers={
                'Referer': 'https://platzi.com/',
            },
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
        await self._goto_with_retry(page, LOGIN_URL, max_retries=3)
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

    async def _copy_course_to_path(self, course_id: str, course_title: str, learning_path_id: str, **kwargs):
        """Copy an already downloaded course to a new learning path folder.
        
        Returns:
            bool: True if copy was successful, False otherwise
        """
        # Get the learning path info
        path_title = kwargs.get("learning_path_title")
        course_index = kwargs.get("course_index")
        
        if not path_title or course_index is None:
            Logger.warning("Cannot copy course without learning path context")
            return False
        
        # Find the original course directory
        course_data = self.progress.data["courses"].get(course_id)
        if not course_data:
            Logger.warning(f"Course {course_id} not found in progress tracker, will re-download")
            return False
        
        # Get original learning path IDs
        original_path_ids = course_data.get("learning_path_ids", [])
        if not original_path_ids:
            # Fallback to old format
            old_path_id = course_data.get("learning_path_id")
            if old_path_id:
                original_path_ids = [old_path_id]
        
        if not original_path_ids:
            Logger.warning("Cannot find original learning path for course, will re-download")
            return False
        
        # Find the source directory from the first learning path
        original_path_id = original_path_ids[0]
        original_path_data = self.progress.data["learning_paths"].get(original_path_id)
        
        if not original_path_data:
            Logger.warning(f"Original learning path {original_path_id} not found, will re-download")
            return False
        
        original_path_title = original_path_data["title"]
        
        # Find which index the course has in the original path (this is tricky, we'll search)
        # For now, we'll search for the course folder in the Courses directory
        courses_base = Path("Courses")
        source_dir = None
        
        # Search in learning path structure
        original_path_folder = courses_base / clean_string(original_path_title, max_length=35)
        if original_path_folder.exists():
            for item in original_path_folder.iterdir():
                if item.is_dir() and clean_string(course_title, max_length=30) in item.name:
                    source_dir = item
                    break
        
        # If not found in learning path, check if it's a standalone course
        if not source_dir:
            standalone_folder = courses_base / clean_string(course_title, max_length=80)
            if standalone_folder.exists():
                source_dir = standalone_folder
        
        if not source_dir or not source_dir.exists():
            Logger.warning(f"Cannot find source directory for course: {course_title}, will re-download")
            return False
        
        # Create destination directory
        dest_dir = courses_base / clean_string(path_title, max_length=35) / f"{course_index}. {clean_string(course_title, max_length=30)}"
        
        try:
            if dest_dir.exists():
                Logger.info(f"Destination already exists: {dest_dir}")
            else:
                Logger.info(f"Copying course from {source_dir} to {dest_dir}")
                shutil.copytree(source_dir, dest_dir)
                Logger.info(f"✅ Course copied successfully to {path_title}")
            
            # Update progress tracker to add this learning path ID
            self.progress.start_course(course_id, course_title, learning_path_id)
            self.progress.complete_course(course_id)
            return True
            
        except Exception as e:
            Logger.warning(f"Error copying course: {e}, will re-download", exception=e)
            return False

    async def _goto_with_retry(self, page: Page, url: str, max_retries: int = 3) -> None:
        """Navigate to URL with retry logic for better reliability.
        
        Uses a very aggressive approach: waits only for 'commit' event (earliest possible),
        then continues immediately with fixed delays instead of waiting for full page load.
        Uses increasing timeouts for better resilience on slow connections.
        """
        original_page = page
        for attempt in range(max_retries):
            try:
                # Check if page is closed or context is dead
                if page.is_closed():
                    Logger.warning("⚠️  Page is closed, creating new page...")
                    page = await self._context.new_page()
                    if self.browser_type == "chromium":
                        await self._minimize_page(page)
                    
                # Check if stuck on about:blank on retry - create fresh page
                current_url = page.url
                if attempt > 0 and current_url == "about:blank":
                    Logger.warning("⚠️  Page stuck on about:blank, creating fresh page...")
                    try:
                        # Close old page and create completely fresh one
                        if not original_page.is_closed():
                            await page.close()
                        page = await self._context.new_page()
                        if self.browser_type == "chromium":
                            await self._minimize_page(page)
                        Logger.debug("✅ Created fresh page for retry")
                    except Exception as page_error:
                        Logger.debug(f"Could not create fresh page: {page_error}")
                
                # Use increasing timeout: 30s, 45s, 60s
                timeout = 30000 + (attempt * 15000)
                Logger.debug(f"Attempting navigation (timeout: {timeout}ms)...")
                
                # Use 'commit' wait_until - earliest navigation event possible
                # This fires as soon as navigation is committed, before any loading
                # Much more reliable than 'load' or 'domcontentloaded' which may never fire
                await page.goto(url, timeout=timeout, wait_until='commit')
                Logger.debug(f"✅ Navigation succeeded on attempt {attempt + 1}")
                # Fixed delay for JavaScript to execute (more reliable than waiting for events)
                await asyncio.sleep(5)
                return  # Success
            except Exception as e:
                error_str = str(e)
                # If it's a timeout but page is not blank, it might have loaded enough
                if "Timeout" in error_str:
                    try:
                        current_url = page.url
                        if current_url and current_url != "about:blank" and url in current_url:
                            Logger.warning(f"⚠️  Navigation timeout but page loaded: {current_url}")
                            await asyncio.sleep(5)  # Fixed delay for JS to execute
                            return  # Continue despite timeout
                        elif current_url == "about:blank":
                            Logger.warning(f"⚠️  Page stuck on about:blank after timeout")
                    except:
                        pass
                
                if attempt < max_retries - 1:
                    wait_time = 3 + (attempt * 2)  # Progressive backoff: 3s, 5s
                    Logger.warning(f"⚠️  Navigation failed (attempt {attempt + 1}/{max_retries}): {error_str[:100]}")
                    Logger.info(f"🔄 Retrying in {wait_time} seconds with longer timeout...")
                    await asyncio.sleep(wait_time)
                else:
                    # Last attempt failed - check if it's a network/browser issue
                    if page.url == "about:blank":
                        Logger.error("❌ Page never loaded (stuck on about:blank)")
                        Logger.error("💡 This usually indicates one of these issues:")
                        Logger.error("   1. Network connectivity problems")
                        Logger.error("   2. Website is blocking the browser/bot detection")
                        Logger.error("   3. Session expired - try: --login")
                        if self.browser_type == "firefox":
                            Logger.error("   4. Firefox headless is often detected - try:")
                            Logger.error("      • --no-headless (run with visible browser)")
                            Logger.error("      • --browser chromium (Chromium is more reliable)")
                        else:
                            Logger.error("   4. Try: --no-headless (run with visible browser)")
                        Logger.error("\n🔍 Recommended solutions:")
                        Logger.error("   • Check your internet connection")
                        Logger.error("   • Re-authenticate: platzi-downloader --login")
                        Logger.error("   • Use Chromium: platzi-downloader --browser chromium")
                        Logger.error("   • Use visible mode: platzi-downloader --no-headless")
                    raise Exception(f"Failed to load page after {max_retries} attempts: {error_str}")

    async def _download_with_browser_interception(self, m3u8_url: str, output_path: Path, unit_url: str = None) -> bool:
        """Download video by intercepting browser network requests.
        
        This method bypasses HTTP client detection and CORS by navigating to the actual
        class page where the video is already playing, then intercepting the fragments.
        
        Args:
            m3u8_url: URL of the m3u8 manifest (not used, kept for compatibility)
            output_path: Path where to save the final merged video
            unit_url: URL of the specific class/unit page where video is playing
            
        Returns:
            True if download succeeded, False otherwise
        """
        Logger.info("🌐 Intercepting browser requests to download video...")
        Logger.info("💡 This method works by loading the actual class page (like Stream Recorder)")
        
        # Create temporary directory for fragments
        temp_dir = Path('.tmp') / f"browser_intercept_{int(time.time())}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage for captured fragments
        captured_fragments = []
        fragment_lock = asyncio.Lock()
        fragment_urls_seen = set()  # Avoid duplicates
        
        try:
            # Create new page for interception
            page = await self._context.new_page()
            
            # Track maximum video timestamp captured to resume after reload
            max_captured_timestamp = 0
            
            # Setup response interception to capture .ts fragments
            async def handle_response(response):
                nonlocal max_captured_timestamp
                try:
                    # Capture .ts video fragments and .m3u8 playlists
                    if (('.ts' in response.url or '.m3u8' in response.url) and 
                        response.status == 200 and 
                        response.url not in fragment_urls_seen):
                        
                        # Avoid duplicate downloads
                        fragment_urls_seen.add(response.url)
                        
                        # Silently capture manifests (shown in debug mode only if needed)
                        # Avoid logging to prevent interference with tqdm progress bar
                        
                        content = await response.body()
                        
                        # Only save .ts fragments (actual video data)
                        if '.ts' in response.url:
                            async with fragment_lock:
                                fragment_index = len(captured_fragments)
                                fragment_path = temp_dir / f"fragment_{fragment_index:05d}.ts"
                                
                                # Write fragment to disk immediately
                                async with aiofiles.open(fragment_path, 'wb') as f:
                                    await f.write(content)
                                
                                # Try to extract sequence/timestamp from URL for deduplication
                                # Example: ...media_123.ts or ...seg-45-v1-a1.ts
                                fragment_url = response.url
                                import re
                                seq_match = re.search(r'(?:media[-_]|seg[-_]|frag[-_]|chunk[-_])(\d+)', fragment_url)
                                sequence_num = int(seq_match.group(1)) if seq_match else fragment_index
                                
                                captured_fragments.append({
                                    'path': fragment_path,
                                    'index': fragment_index,
                                    'size': len(content),
                                    'url': fragment_url,
                                    'sequence': sequence_num
                                })
                                
                                # Update max captured position (approximate: sequence * 10 seconds per fragment)
                                estimated_timestamp = sequence_num * 10
                                if estimated_timestamp > max_captured_timestamp:
                                    max_captured_timestamp = estimated_timestamp
                                
                                # Progress is shown by tqdm bar, no need for debug logs here
                                pass
                
                except Exception as e:
                    # Ignore errors in individual fragments to avoid stopping the capture
                    Logger.debug(f"Error capturing fragment: {e}")
            
            # Attach response listener BEFORE navigation
            page.on('response', handle_response)
            
            # Navigate directly to the class page where video is already playing
            if not unit_url:
                Logger.error("❌ No unit URL provided. Cannot load class page.")
                return False
                
            Logger.info(f"🎬 Loading class page where video is playing...")
            Logger.debug(f"Unit URL: {unit_url}")
            
            try:
                # Navigate to the actual class page with retry logic
                await self._goto_with_retry(page, unit_url, max_retries=3)
                
                # Try to extract duration from DOM with active waiting
                duration_from_dom = None
                Logger.info("⏳ Waiting for video player to load duration...")
                max_dom_wait = 15  # Wait up to 15 seconds for DOM duration
                
                for wait_attempt in range(max_dom_wait):
                    await asyncio.sleep(1)
                    
                    try:
                        duration_text = await page.evaluate("""
                            (() => {
                                // Try to get duration from video player display
                                const durationDisplay = document.querySelector('.vjs-duration-display');
                                if (durationDisplay) {
                                    return durationDisplay.textContent.trim();
                                }
                                return null;
                            })()
                        """)
                        
                        if duration_text and duration_text != "0:00" and duration_text != "00:00":
                            # Parse duration text (e.g., "10:35" -> 635 seconds)
                            parts = duration_text.split(':')
                            if len(parts) == 2:  # MM:SS
                                minutes, seconds = int(parts[0]), int(parts[1])
                                duration_from_dom = minutes * 60 + seconds
                                if duration_from_dom > 0:  # Valid duration
                                    Logger.info(f"📹 Video duration from DOM: {minutes}:{seconds:02d} ({duration_from_dom}s)")
                                    break
                            elif len(parts) == 3:  # HH:MM:SS
                                hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
                                duration_from_dom = hours * 3600 + minutes * 60 + seconds
                                if duration_from_dom > 0:  # Valid duration
                                    Logger.info(f"📹 Video duration from DOM: {hours}:{minutes:02d}:{seconds:02d} ({duration_from_dom}s)")
                                    break
                    except Exception as dom_error:
                        Logger.debug(f"Error extracting duration from DOM (attempt {wait_attempt + 1}): {dom_error}")
                        continue
                
                if not duration_from_dom:
                    Logger.debug("Could not extract valid duration from DOM after 15 seconds")
                
                # Try to find and configure video for fast download
                video_info = None
                try:
                    video_info = await page.evaluate("""
                        (() => {
                            const video = document.querySelector('video');
                            if (video) {
                                // Mute to allow autoplay
                                video.muted = true;
                                
                                // Set playback rate to 4x (balanced speed and accuracy)
                                video.playbackRate = 4.0;
                                
                                // Try to play
                                video.play().catch(e => console.log('Play failed:', e));
                                
                                console.log('🎬 Video playback started at 4x speed');
                                
                                // Return video info
                                // Check if duration is valid (not NaN or Infinity)
                                const duration = (video.duration && isFinite(video.duration)) ? video.duration : null;
                                
                                return {
                                    duration: duration,
                                    paused: video.paused,
                                    currentTime: video.currentTime
                                };
                            } else {
                                console.log('⚠️ No video element found');
                                return null;
                            }
                        })()
                    """)
                    
                    # If we got duration from DOM but not from video element, use DOM duration
                    if duration_from_dom and (not video_info or not video_info.get('duration')):
                        if video_info is None:
                            video_info = {}
                        video_info['duration'] = duration_from_dom
                        Logger.info(f"✅ Using duration from DOM: {duration_from_dom}s")
                    
                    if video_info and video_info.get('duration') is not None:
                        try:
                            duration = float(video_info['duration'])
                            # Validate that duration is a finite number (not NaN or Infinity)
                            if duration > 0 and duration < float('inf'):
                                duration_minutes = duration / 60
                                Logger.info(f"📹 Video duration: {duration_minutes:.1f} minutes")
                                Logger.info(f"⚡ Playback speed set to 4x for accurate capture")
                            else:
                                Logger.warning(f"⚠️ Video duration is invalid: {duration}")
                                video_info = None  # Mark as invalid to avoid using later
                        except (ValueError, TypeError) as e:
                            Logger.warning(f"⚠️ Could not parse video duration: {e}")
                            video_info = None
                    else:
                        Logger.warning(f"⚠️ Could not get video duration")
                        video_info = None
                        
                except Exception as play_error:
                    Logger.debug(f"Could not start video playback: {play_error}")
                    Logger.info(f"💡 Will attempt to capture fragments even without video control")
                
                # If we don't have duration yet (neither from DOM nor video element), wait for it
                # This ensures progress bar will work correctly
                if video_info is None or video_info.get('duration') is None:
                    Logger.info("⏳ Waiting for video.duration to load...")
                    max_duration_wait = 15  # Reduced since we already waited for DOM
                    
                    for wait_second in range(max_duration_wait):
                        await asyncio.sleep(1)
                        
                        try:
                            check_info = await page.evaluate("""
                                (() => {
                                    const video = document.querySelector('video');
                                    if (video && video.duration && isFinite(video.duration)) {
                                        return {
                                            duration: video.duration,
                                            currentTime: video.currentTime,
                                            paused: video.paused
                                        };
                                    }
                                    return null;
                                })()
                            """)
                            
                            if check_info and check_info.get('duration'):
                                duration = float(check_info['duration'])
                                if duration > 0 and duration < float('inf'):
                                    video_info = check_info
                                    duration_minutes = duration / 60
                                    Logger.info(f"✅ Video duration obtained: {duration_minutes:.1f} minutes ({duration:.0f}s)")
                                    Logger.info(f"⚡ Playback speed set to 4x for accurate capture")
                                    break
                        except Exception as e:
                            Logger.debug(f"Error checking duration: {e}")
                            continue
                    
                    # If still no duration after waiting, warn but continue
                    if video_info is None or video_info.get('duration') is None:
                        Logger.warning("⚠️ Could not obtain video duration after 30s")
                        Logger.info("💡 Will continue without duration estimate (progress bar may not show total)")
                else:
                    # We already have duration, just wait a bit for fragments to start
                    await asyncio.sleep(3)
                
            except Exception as nav_error:
                Logger.error(f"❌ Failed to load class page: {nav_error}")
                return False
            
            # Estimate expected fragments based on video duration
            expected_fragments = None
            initial_video_duration = None
            
            if video_info and video_info.get('duration') is not None:
                try:
                    duration = float(video_info['duration'])
                    if duration > 0 and duration < float('inf'):
                        initial_video_duration = duration  # Set initial duration here
                        # Typical fragment is 10 seconds, so duration/10 gives rough estimate
                        expected_fragments = int(duration / 10) + 10  # Add buffer
                        Logger.info(f"🎯 Starting capture: ~{expected_fragments} fragments expected ({duration:.0f}s video)")
                except (ValueError, TypeError):
                    Logger.debug("Could not estimate fragments from duration")
                    expected_fragments = None
            
            if expected_fragments is None:
                Logger.info("⏳ Starting fragment capture (unknown duration)...")
            
            Logger.info("💡 Video will play at 4x speed and skip ahead to load all fragments")
            
            # Monitor fragment collection with timeout and progress bar
            # Dynamic timeout: video_duration / 4 (playback speed) * 3 (buffer) + 120s base
            if initial_video_duration and initial_video_duration > 0:
                # For known duration: allow 3x the theoretical capture time + 2 min buffer
                max_wait_time = int((initial_video_duration / 4) * 3) + 120
                max_wait_time = max(600, min(max_wait_time, 1800))  # Between 10-30 minutes
            else:
                max_wait_time = 900  # 15 minutes for unknown duration
            last_fragment_count = 0
            no_progress_seconds = 0
            seek_interval = 15  # Seek forward every 15 seconds
            seconds_since_seek = 0
            # initial_video_duration already set above if we have duration
            video_ended = False
            last_video_position = 0  # Track if video is stuck
            video_stuck_seconds = 0  # Count how long video hasn't moved
            last_dom_time = None  # Track DOM time display
            reload_count = 0  # Track page reloads
            max_reloads = 2  # Maximum page reloads allowed
            
            # Use tqdm progress bar similar to m3u8 download
            bar_format = "{desc} |{bar}| {n} fragments [{elapsed}, {rate_fmt}{postfix}]"
            with tqdm(desc="Capturing", colour='cyan', bar_format=bar_format, ascii='░█', unit=' frags', total=expected_fragments) as progress_bar:
                for second in range(max_wait_time):
                    await asyncio.sleep(1)
                    current_count = len(captured_fragments)
                    seconds_since_seek += 1
                    
                    # Update progress bar if we have new fragments
                    if current_count > last_fragment_count:
                        new_fragments = current_count - last_fragment_count
                        total_mb = sum(f['size'] for f in captured_fragments) / 1024 / 1024
                        progress_bar.update(new_fragments)
                        progress_bar.set_postfix_str(f"{total_mb:.1f} MB")
                        last_fragment_count = current_count
                        no_progress_seconds = 0
                    else:
                        no_progress_seconds += 1
                    
                    # Periodically seek forward to force loading more fragments
                    if seconds_since_seek >= seek_interval:
                        seconds_since_seek = 0
                        try:
                            video_state = await page.evaluate("""
                                (() => {
                                    const video = document.querySelector('video');
                                    if (video) {
                                        // If paused, play it
                                        if (video.paused) {
                                            video.play().catch(e => console.log('Play failed:', e));
                                        }
                                        
                                        // Ensure playback rate is still at 4x
                                        if (video.playbackRate < 4) {
                                            video.playbackRate = 4.0;
                                        }
                                        
                                        // Jump forward 60 seconds to force loading more fragments
                                        // Only if duration is valid (not NaN)
                                        if (isFinite(video.duration) && isFinite(video.currentTime)) {
                                            // If we're near the end (last 15 seconds), pause to prevent autoplay to next class
                                            if (video.currentTime >= video.duration - 15) {
                                                video.pause();
                                                console.log('⏸️ Video near end - paused to prevent next class');
                                            } else {
                                                const jumpTo = Math.min(video.currentTime + 60, video.duration - 15);
                                                if (jumpTo > video.currentTime && jumpTo < video.duration) {
                                                    video.currentTime = jumpTo;
                                                }
                                            }
                                        }
                                        
                                        // Get DOM time display for better stuck detection
                                        const currentTimeDisplay = document.querySelector('.vjs-current-time-display');
                                        const durationDisplay = document.querySelector('.vjs-duration-display');
                                        
                                        return {
                                            currentTime: isFinite(video.currentTime) ? video.currentTime : null,
                                            duration: isFinite(video.duration) ? video.duration : null,
                                            paused: video.paused,
                                            rate: video.playbackRate,
                                            domCurrentTime: currentTimeDisplay ? currentTimeDisplay.textContent.trim() : null,
                                            domDuration: durationDisplay ? durationDisplay.textContent.trim() : null
                                        };
                                    }
                                    return null;
                                })()
                            """)
                            
                            if video_state:
                                current_time = video_state.get('currentTime', 0) or 0
                                duration = video_state.get('duration', 0) or 0
                                rate = video_state.get('rate', 1) or 1
                                dom_current = video_state.get('domCurrentTime')
                                dom_duration = video_state.get('domDuration')
                                
                                # Only log every 60 seconds to avoid cluttering tqdm
                                if seconds_since_seek == 0 and second % 60 == 0:
                                    progress_bar.write(f"⏱️  Video: {current_time:.0f}s / {duration:.0f}s | Fragments: {current_count} | Size: {sum(f['size'] for f in captured_fragments) / 1024 / 1024:.1f} MB")
                                
                                # Track initial duration to detect class changes
                                if initial_video_duration is None and duration > 0:
                                    initial_video_duration = duration
                                    Logger.debug(f"Initial video duration set to: {initial_video_duration:.0f}s")
                                
                                # Detect if video is stuck (not advancing) - check both DOM and video element
                                dom_stuck = False
                                if dom_current and dom_current == last_dom_time:
                                    dom_stuck = True
                                
                                element_stuck = abs(current_time - last_video_position) < 2  # Less than 2 seconds movement
                                
                                if element_stuck or dom_stuck:
                                    video_stuck_seconds += seek_interval
                                    
                                    # Special case: If stuck at very beginning (0-5s), reload faster
                                    if current_time <= 5 and video_stuck_seconds >= 30 and reload_count < max_reloads:
                                        progress_bar.write(f"🔄 Video stuck at start ({current_time:.0f}s) - reloading immediately")
                                        try:
                                            await page.reload(timeout=30000)
                                            await asyncio.sleep(5)
                                            
                                            # Start fresh from beginning
                                            await page.evaluate("""
                                                (() => {
                                                    const video = document.querySelector('video');
                                                    if (video) {
                                                        video.muted = true;
                                                        video.playbackRate = 4.0;
                                                        video.currentTime = 0;
                                                        video.play().catch(e => console.log('Play failed:', e));
                                                        console.log('🎬 Video restarted from beginning at 4x speed');
                                                    }
                                                })()
                                            """)
                                            
                                            reload_count += 1
                                            video_stuck_seconds = 0
                                            last_video_position = 0
                                            progress_bar.write(f"✅ Page reloaded due to start position freeze")
                                        except Exception as e:
                                            progress_bar.write(f"⚠️  Reload failed: {str(e)[:100]}")
                                    
                                    # First level: Try aggressive seek after 30s stuck (mid-video)
                                    elif video_stuck_seconds >= 30 and video_stuck_seconds < 60 and current_time > 5:
                                        progress_bar.write(f"⚠️  Video stuck at {current_time:.0f}s - attempting aggressive seek")
                                        try:
                                            if duration > 0 and current_time < duration - 60:
                                                target = min(current_time + 120, duration - 20)  # Jump 2 minutes or near end
                                                await page.evaluate(f"""
                                                    (() => {{
                                                        const video = document.querySelector('video');
                                                        if (video) {{
                                                            video.currentTime = {target};
                                                            video.play().catch(e => console.log('Play failed:', e));
                                                            console.log('⚡ Forced aggressive seek to {target}s');
                                                        }}
                                                    }})()
                                                """)
                                                progress_bar.write(f"⚡ Forced jump to {target:.0f}s to unstuck video")
                                                video_stuck_seconds = 0
                                        except Exception as e:
                                            Logger.debug(f"Error in aggressive seek: {e}")
                                    
                                    # Second level: Reload page after 60s stuck
                                    elif video_stuck_seconds >= 60 and reload_count < max_reloads:
                                        progress_bar.write(f"🔄 Video stuck for 60s+ - reloading page to continue capture (reload {reload_count + 1}/{max_reloads})")
                                        try:
                                            # Calculate resume position based on captured fragments
                                            resume_position = max(current_time, max_captured_timestamp)
                                            if resume_position < 10:  # If too early, use current video time
                                                resume_position = current_time
                                            
                                            progress_bar.write(f"📍 Will resume from ~{resume_position:.0f}s to avoid duplicates")
                                            
                                            # Reload the page to restart video
                                            await page.reload(timeout=30000)
                                            await asyncio.sleep(5)  # Wait for page to stabilize
                                            
                                            # Resume video from last position at 4x speed
                                            await page.evaluate(f"""
                                                (() => {{
                                                    const video = document.querySelector('video');
                                                    if (video) {{
                                                        video.muted = true;
                                                        video.playbackRate = 4.0;
                                                        // Seek to last captured position to avoid duplicates
                                                        video.currentTime = {resume_position};
                                                        video.play().catch(e => console.log('Play failed:', e));
                                                        console.log('🎬 Video resumed from {resume_position:.0f}s at 4x speed after reload');
                                                    }}
                                                }})()
                                            """)
                                            
                                            reload_count += 1
                                            video_stuck_seconds = 0
                                            last_video_position = resume_position  # Update tracking
                                            progress_bar.write(f"✅ Page reloaded, resumed from {resume_position:.0f}s")
                                        except Exception as e:
                                            progress_bar.write(f"⚠️  Reload failed: {str(e)[:100]}")
                                    
                                    # Third level: Give up after max reloads and stuck time
                                    elif video_stuck_seconds >= 90 and reload_count >= max_reloads:
                                        if expected_fragments and current_count >= expected_fragments * 0.85:
                                            progress_bar.close()
                                            Logger.warning(f"⚠️ Video permanently stuck after {reload_count} reloads")
                                            Logger.info(f"✅ Have {current_count}/{expected_fragments} fragments (85%+) - stopping capture")
                                            video_ended = True
                                            break
                                else:
                                    video_stuck_seconds = 0  # Reset if video is moving
                                
                                last_dom_time = dom_current
                                
                                last_video_position = current_time
                                
                                # Detect if duration changed (Platzi loaded next class)
                                if initial_video_duration and duration > 0:
                                    duration_change = abs(duration - initial_video_duration)
                                    if duration_change > 30:  # More than 30 seconds difference
                                        progress_bar.close()
                                        Logger.warning(f"⚠️ Video duration changed from {initial_video_duration:.0f}s to {duration:.0f}s")
                                        Logger.info(f"🛑 Detected next class loading - stopping capture to avoid mixing videos")
                                        video_ended = True
                                        break
                                
                                # Detect if current video ended (near the end)
                                if duration > 0 and current_time >= duration - 10:
                                    progress_bar.close()
                                    Logger.info(f"✅ Video reached end ({current_time:.0f}s / {duration:.0f}s)")
                                    Logger.info(f"🛑 Stopping capture to avoid next class")
                                    video_ended = True
                                    break
                                
                        except Exception as seek_error:
                            Logger.debug(f"Could not seek video: {seek_error}")
                    
                    # Break outer loop if video ended
                    if video_ended:
                        break
                    
                    # Stop conditions - more intelligent
                    if current_count > 0:
                        # Check if we likely have all fragments
                        # IMPORTANT: Also verify video is near the end (not just fragment count)
                        if expected_fragments and current_count >= expected_fragments * 0.95:
                            # Got 95% of expected fragments, but verify video is also near end
                            # Get current video state to confirm
                            try:
                                final_check = await page.evaluate("""
                                    (() => {
                                        const video = document.querySelector('video');
                                        if (video) {
                                            return {
                                                currentTime: isFinite(video.currentTime) ? video.currentTime : 0,
                                                duration: isFinite(video.duration) ? video.duration : 0
                                            };
                                        }
                                        return null;
                                    })()
                                """)
                                
                                if final_check:
                                    video_current = final_check.get('currentTime', 0) or 0
                                    video_duration = final_check.get('duration', 0) or 0
                                    
                                    # Only stop if video is at least 97% complete (within last 15 seconds)
                                    if video_duration > 0:
                                        video_progress = video_current / video_duration
                                        seconds_remaining = video_duration - video_current
                                        
                                        # Stop if very close to end (97%+ or ≤15 seconds remaining)
                                        if video_progress >= 1 or seconds_remaining <= 15:
                                            progress_bar.close()
                                            Logger.info(f"✅ Captured expected fragments ({current_count}/{expected_fragments}) and video at {video_progress*100:.0f}% ({seconds_remaining:.0f}s remaining)")
                                            break
                                        else:
                                            # Only log every 5 checks to avoid spam
                                            if second % 5 == 0:
                                                progress_bar.write(f"⏳ Fragments: {current_count}/{expected_fragments} | Video: {video_progress*100:.0f}% ({seconds_remaining:.0f}s remaining)")
                                    else:
                                        # No duration info, trust fragment count
                                        progress_bar.close()
                                        Logger.info(f"✅ Captured expected number of fragments ({current_count}/{expected_fragments})")
                                        break
                            except Exception as e:
                                Logger.debug(f"Error checking final video state: {e}")
                                # If can't check, trust the fragment count
                                progress_bar.close()
                                Logger.info(f"✅ Captured expected number of fragments ({current_count}/{expected_fragments})")
                                break
                                
                        elif no_progress_seconds >= 60:
                            # No new fragments for 60 seconds
                            # But check if we have enough - don't stop if clearly incomplete
                            if expected_fragments and current_count < expected_fragments * 0.7:
                                # We have less than 70% of expected fragments
                                progress_bar.write(f"⚠️  Only {current_count}/{expected_fragments} fragments ({current_count/expected_fragments*100:.0f}%) - video may be incomplete")
                                progress_bar.write(f"⏳ Waiting longer for remaining fragments...")
                                no_progress_seconds = 0  # Reset and keep waiting
                                
                                # Try to unstick the video by seeking
                                try:
                                    await page.evaluate("""
                                        (() => {
                                            const video = document.querySelector('video');
                                            if (video && video.duration > 0) {
                                                const jumpTo = Math.min(video.currentTime + 60, video.duration - 10);
                                                video.currentTime = jumpTo;
                                                video.play().catch(e => console.log('Play error:', e));
                                                console.log('Seeking forward to load more fragments...');
                                            }
                                        })()
                                    """)
                                except:
                                    pass
                            else:
                                # We have most fragments (70%+) or no expected count
                                progress_bar.close()
                                if expected_fragments:
                                    Logger.info(f"✅ No new fragments for 60s with {current_count}/{expected_fragments} captured ({current_count/expected_fragments*100:.0f}%)")
                                else:
                                    Logger.info(f"✅ No new fragments for 60s, assuming download complete")
                                break
                    
                    if current_count >= 3000:
                        # Safety limit - very long video (increased from 2000)
                        progress_bar.close()
                        Logger.warning(f"⚠️  Reached fragment limit (3000), stopping capture")
                        break
            
            await page.close()
            
            # Check if we captured anything
            if len(captured_fragments) == 0:
                Logger.error("❌ No video fragments were captured")
                return False
            
            Logger.info(f"✅ Captured {len(captured_fragments)} video fragments")
            total_size = sum(f['size'] for f in captured_fragments) / 1024 / 1024
            Logger.info(f"📦 Total size: {total_size:.1f} MB")
            
            # Check if capture appears complete
            if expected_fragments:
                completion_rate = len(captured_fragments) / expected_fragments
                if completion_rate < 0.7:
                    Logger.warning(f"⚠️  Video may be INCOMPLETE: {len(captured_fragments)}/{expected_fragments} fragments ({completion_rate*100:.0f}%)")
                    Logger.warning(f"⚠️  Expected ~{expected_fragments} fragments but only captured {len(captured_fragments)}")
                    Logger.warning(f"💡 The video might have gotten stuck. You may need to re-download this unit.")
                elif completion_rate < 0.9:
                    Logger.warning(f"⚠️  Video might be slightly incomplete: {len(captured_fragments)}/{expected_fragments} fragments ({completion_rate*100:.0f}%)")
                else:
                    Logger.info(f"✅ Capture appears complete: {len(captured_fragments)}/{expected_fragments} fragments ({completion_rate*100:.0f}%)")
            
            # Merge fragments with ffmpeg
            Logger.info("🔧 Merging fragments with ffmpeg...")
            
            # Create concat list file
            concat_file = temp_dir / "concat.txt"
            async with aiofiles.open(concat_file, 'w') as f:
                for fragment in sorted(captured_fragments, key=lambda x: x['index']):
                    # Use relative paths for better compatibility
                    await f.write(f"file '{fragment['path'].name}'\n")
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Run ffmpeg to merge
            # Use only filename since we're setting cwd to temp_dir
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', 'concat.txt',  # Just filename, not full path
                '-c', 'copy',  # Copy without re-encoding for speed
                '-y',  # Overwrite output
                str(output_path.resolve())  # Use absolute path for output
            ]
            
            Logger.debug(f"Running ffmpeg from directory: {temp_dir}")
            Logger.debug(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(temp_dir)  # Run in temp dir for relative paths
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_output = stderr.decode('utf-8', errors='ignore')
                Logger.error(f"❌ FFmpeg failed: {error_output[-500:]}")
                return False
            
            # Verify output file was created and has reasonable size
            if not output_path.exists():
                Logger.error("❌ Output file was not created")
                return False
            
            final_size = output_path.stat().st_size / 1024 / 1024
            if final_size < 0.1:  # Less than 100KB is suspicious
                Logger.error(f"❌ Output file too small ({final_size:.1f} MB)")
                return False
            
            Logger.info(f"✅ Video merged successfully ({final_size:.1f} MB)")
            Logger.info(f"💾 Saved to: {output_path}")
            
            return True
            
        except Exception as e:
            Logger.error(f"❌ Browser interception failed: {e}", exception=e)
            return False
            
        finally:
            # Cleanup temporary directory
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    Logger.debug(f"🧹 Cleaned up temporary directory: {temp_dir}")
            except Exception as cleanup_error:
                Logger.debug(f"Could not cleanup temp dir: {cleanup_error}")

    async def _validate_session(self) -> bool:
        """Check if the current session is still valid."""
        try:
            # If we're marked as logged in and have cookies, assume session is valid
            # The _set_profile() method already validated authentication
            if self.loggedin and self.user and self.user.is_authenticated:
                Logger.debug("Session valid: User is authenticated")
                return True
            
            cookies = await self._context.cookies()
            if not cookies:
                Logger.debug("Session invalid: No cookies found")
                return False
            
            # Quick check: try to load a simple API endpoint
            try:
                test_page = await self._context.new_page()
                try:
                    # Try to access user profile API - more reliable than DOM selectors
                    await test_page.goto(LOGIN_DETAILS_URL, timeout=15000, wait_until='commit')
                    await asyncio.sleep(1)
                    
                    # Check if we got valid JSON (not redirect to login)
                    content = await test_page.content()
                    # If we see actual user data, we're logged in
                    is_logged_in = '"is_authenticated":true' in content or '"isAuthenticated":true' in content
                    
                    await test_page.close()
                    Logger.debug(f"Session validation result: {is_logged_in}")
                    return is_logged_in
                except Exception as e:
                    Logger.debug(f"Session validation error: {e}")
                    if not test_page.is_closed():
                        await test_page.close()
                    return False
            except Exception as e:
                Logger.debug(f"Could not create test page: {e}")
                # If we can't test but user object exists, assume valid
                return self.loggedin and self.user is not None
        except Exception as e:
            Logger.debug(f"Session validation exception: {e}")
            return False
    
    @try_except_request
    @login_required
    async def download(self, url: str, **kwargs):
        # Validate session only on first download (not for every URL in batch)
        if not hasattr(self, '_session_validated'):
            Logger.debug("Validating session...")
            if not await self._validate_session():
                Logger.error("❌ Session expired or invalid!")
                Logger.error("💡 Please run with --login to authenticate again")
                raise Exception("Session expired. Please login again with --login flag")
            self._session_validated = True
            Logger.debug("✅ Session is valid")
        
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
            Logger.error(f"Error downloading learning path: {e}", exception=e)
            Logger.debug(f"Learning path download failed for URL: {url}")
            await page.close()
            raise

    @try_except_request
    @login_required
    async def _download_course(self, url: str, **kwargs):
        """Download a single course."""
        course_id = urlparse(url).path
        
        # Get course data from progress tracker
        course_data = self.progress.data["courses"].get(course_id)
        learning_path_id = kwargs.get("learning_path_id")
        
        # Check if course was already completed AND has no pending units
        if self.progress.should_skip_course(course_id):
            # Course is complete but might belong to another learning path
            if learning_path_id and course_data:
                existing_path_ids = course_data.get("learning_path_ids", [])
                if learning_path_id not in existing_path_ids:
                    # Course is complete and belongs to a different path - try to copy it
                    Logger.info(f"📋 Course already downloaded in another learning path. Attempting to copy...")
                    copy_success = await self._copy_course_to_path(course_id, course_data["title"], learning_path_id, **kwargs)
                    
                    if copy_success:
                        # Copy was successful, skip download
                        return
                    else:
                        # Copy failed, continue with normal download
                        Logger.info(f"🔄 Copy failed, re-downloading course: {url}")
                        # Don't return here, let it continue to download
                else:
                    Logger.info(f"⏭️  Course already completed (no pending units), skipping: {url}")
                    return
            else:
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
            
            # Check if user has access to the course
            if course_title == "No tienes acceso a este contenido" or "no tienes acceso" in course_title.lower():
                Logger.warning(f"⚠️  Access denied to course: {url}")
                Logger.warning(f"Course title: {course_title}")
                Logger.info("This course is not available in your subscription. Skipping...")
                
                # Mark as failed with descriptive reason
                self.progress.fail_course(
                    course_id,
                    "Access denied - Course not available in your subscription"
                )
                return
            
            # Register course start (will add to learning_path_ids list if already exists)
            self.progress.start_course(course_id, course_title, learning_path_id)

            # Check if this is part of a learning path
            learning_path_title = kwargs.get("learning_path_title")
            course_index = kwargs.get("course_index")
            
            # download directory
            # Apply aggressive length limits to avoid Windows 260 char path limit
            # Max path calculation: Courses(8) + LPath(35) + Course(30) + Chapter(35) + File(40) + extras(~30) = ~178 chars
            if learning_path_title and course_index is not None:
                # Structure: [Learning Path]/[N. Course]/
                DL_DIR = Path("Courses") / clean_string(learning_path_title, max_length=35) / f"{course_index}. {clean_string(course_title, max_length=30)}"
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

                CHAP_DIR = DL_DIR / f"{idx}. {clean_string(draft_chapter.name, max_length=35)}"
                try:
                    CHAP_DIR.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    Logger.error(f"Failed to create chapter directory: {e}", exception=e)
                    Logger.error(f"Path: {CHAP_DIR}")
                    Logger.error(f"Path length: {len(str(CHAP_DIR))} characters")
                    if len(str(CHAP_DIR)) > 240:
                        Logger.error("⚠️  Path is too long for Windows (>240 chars). Consider using shorter names.")
                    raise

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
                        Logger.error(f"{error_msg} for '{draft_unit.title}'", exception=e)
                        Logger.debug(f"Failed unit URL: {draft_unit.url}")
                        Logger.warning("Skipping this unit and continuing with the next one...")
                        self.progress.fail_unit(course_id, unit_id, error_msg)
                        continue
                    
                    try:
                        file_name = f"{jdx}. {clean_string(unit.title, max_length=35)}"

                        # download video
                        if unit.video:
                            # Ensure directory exists before downloading video
                            if not CHAP_DIR.exists():
                                Logger.warning(f"Chapter directory does not exist, creating: {CHAP_DIR}")
                                try:
                                    CHAP_DIR.mkdir(parents=True, exist_ok=True)
                                except Exception as mkdir_err:
                                    Logger.error(f"Failed to create directory: {mkdir_err}")
                                    Logger.error(f"Path length: {len(str(CHAP_DIR))} chars")
                                    raise
                                
                                # Verify directory was actually created
                                if not CHAP_DIR.exists():
                                    error_msg = f"Directory creation failed (path too long?): {CHAP_DIR}"
                                    Logger.error(error_msg)
                                    Logger.error(f"Path length: {len(str(CHAP_DIR))} characters (Windows limit: ~248)")
                                    raise FileNotFoundError(error_msg)
                            
                            dst = CHAP_DIR / f"{file_name}.mp4"
                            Logger.print(f"[{dst.name}]", "[DOWNLOADING-VIDEO]")
                            
                            # Get cookies from browser context for authentication
                            cookies = await self.context.cookies()
                            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
                            
                            # Build headers with cookies and proper referer
                            # Use the unit URL as referer (full course page URL)
                            HEADERS = {
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:141.0) Gecko/20100101 Firefox/141.0",
                                "Accept": "*/*",
                                "Accept-Language": "en-US,en;q=0.5",
                                "Accept-Encoding": "gzip, deflate, br, zstd",
                                "Origin": "https://platzi.com",
                                "Connection": "keep-alive",
                                "Sec-Fetch-Dest": "empty",
                                "Sec-Fetch-Mode": "cors",
                                "Sec-Fetch-Site": "same-site",
                                "Referer": unit.url,  # Full course URL as referer
                                "Cookie": cookie_str
                            }
                            Logger.debug(f"Using {len(cookies)} cookies for authentication")
                            
                            # For Chromium: Try primary URL (m3u8 preferred), fallback to DASH if needed
                            # For Firefox: Both formats work fine, no fallback needed
                            video_downloaded = False
                            
                            # Try standard download methods first, fallback to browser interception on HTTP 403
                            primary_download_error = None
                            
                            try:
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
                                                try:
                                                    await m3u8_dl(unit.video.url, dst, headers=HEADERS, **kwargs)
                                                    video_downloaded = True
                                                    Logger.info(f"✅ Video downloaded successfully using primary URL")
                                                except Exception as m3u8_error:
                                                    error_str = str(m3u8_error)
                                                    # Check if it's HTTP 403 - immediately try browser interception
                                                    if "403" in error_str or "HTTP 403" in error_str or "Forbidden" in error_str:
                                                        Logger.warning(f"⚠️  HTTP 403 in m3u8. Trying browser interception...")
                                                        Logger.info(f"💡 This bypasses HTTP client detection by using the browser")
                                                        success = await self._download_with_browser_interception(
                                                            unit.video.url, 
                                                            dst,
                                                            unit_url=unit.url
                                                        )
                                                        if success:
                                                            video_downloaded = True
                                                            Logger.info(f"✅ Video downloaded with browser interception!")
                                                        else:
                                                            raise m3u8_error
                                                    else:
                                                        raise m3u8_error
                                        except Exception as primary_error:
                                            Logger.warning(f"⚠️  Primary URL failed: {str(primary_error)[:100]}")
                                            Logger.info(f"🔄 Trying fallback URL (DASH)...")
                                            try:
                                                await dash_dl(unit.video.fallback_url, dst, headers=HEADERS, **kwargs)
                                                video_downloaded = True
                                                Logger.info(f"✅ Video downloaded successfully using fallback URL")
                                            except Exception as fallback_error:
                                                Logger.error(f"❌ Fallback URL also failed: {str(fallback_error)[:100]}", exception=fallback_error)
                                                Logger.debug(f"Primary URL: {unit.video.url}")
                                                Logger.debug(f"Fallback URL: {unit.video.fallback_url}")
                                                # Save error for potential browser interception fallback
                                                primary_download_error = Exception(f"Both primary and fallback download failed. Primary: {str(primary_error)[:100]}, Fallback: {str(fallback_error)[:100]}")
                                                raise primary_download_error
                                    else:
                                        # Chromium without fallback but has m3u8
                                        try:
                                            await m3u8_dl(unit.video.url, dst, headers=HEADERS, **kwargs)
                                            video_downloaded = True
                                        except Exception as m3u8_error:
                                            error_str = str(m3u8_error)
                                            # Check if it's HTTP 403 - immediately try browser interception
                                            if "403" in error_str or "HTTP 403" in error_str or "Forbidden" in error_str:
                                                Logger.warning(f"⚠️  HTTP 403 in m3u8. Trying browser interception...")
                                                Logger.info(f"💡 This bypasses HTTP client detection using the browser")
                                                success = await self._download_with_browser_interception(
                                                    unit.video.url, 
                                                    dst,
                                                    unit_url=unit.url
                                                )
                                                if success:
                                                    video_downloaded = True
                                                    Logger.info(f"✅ Video downloaded with browser interception!")
                                                else:
                                                    raise m3u8_error
                                            else:
                                                raise m3u8_error
                                else:
                                    # Firefox: Both formats work fine
                                    if '.mpd' in unit.video.url:
                                        await dash_dl(unit.video.url, dst, headers=HEADERS, **kwargs)
                                    else:
                                        try:
                                            await m3u8_dl(unit.video.url, dst, headers=HEADERS, **kwargs)
                                            video_downloaded = True
                                        except Exception as m3u8_error:
                                            error_str = str(m3u8_error)
                                            # Check if it's HTTP 403 - immediately try browser interception
                                            if "403" in error_str or "HTTP 403" in error_str or "Forbidden" in error_str:
                                                Logger.warning(f"⚠️  HTTP 403 error in m3u8 download. Trying browser interception method...")
                                                Logger.info(f"💡 This method bypasses HTTP client detection by using the browser directly")
                                                success = await self._download_with_browser_interception(
                                                    unit.video.url, 
                                                    dst,
                                                    unit_url=unit.url  # Pass unit URL to load class page with video
                                                )
                                                if success:
                                                    video_downloaded = True
                                                    Logger.info(f"✅ Video downloaded successfully using browser interception!")
                                                else:
                                                    raise m3u8_error
                                            else:
                                                raise m3u8_error
                                    
                            except Exception as download_error:
                                primary_download_error = download_error
                                error_str = str(download_error)
                                
                                # Check if it's an HTTP 403 error
                                if "403" in error_str or "HTTP 403" in error_str or "Forbidden" in error_str:
                                    Logger.warning(f"⚠️  HTTP 403 error detected. Trying browser interception method...")
                                    Logger.info(f"💡 This method bypasses HTTP client detection by using the browser directly")
                                    
                                    # Only attempt browser interception for m3u8 videos
                                    video_url_for_interception = unit.video.url
                                    if '.mpd' in video_url_for_interception:
                                        # Try fallback URL if it's m3u8
                                        if unit.video.fallback_url and '.m3u8' in unit.video.fallback_url:
                                            Logger.info(f"🔄 Using fallback m3u8 URL for browser interception")
                                            video_url_for_interception = unit.video.fallback_url
                                        else:
                                            Logger.error(f"❌ Browser interception only supports m3u8 videos, not DASH (.mpd)")
                                            raise download_error
                                    
                                    try:
                                        # Attempt browser interception download
                                        # Pass the unit URL (class page) to load the actual video player
                                        success = await self._download_with_browser_interception(
                                            video_url_for_interception, 
                                            dst,
                                            unit_url=unit.url  # Pass unit URL to load class page with video
                                        )
                                        
                                        if success:
                                            video_downloaded = True
                                            Logger.info(f"✅ Video downloaded successfully using browser interception!")
                                        else:
                                            Logger.error(f"❌ Browser interception method failed")
                                            raise download_error
                                            
                                    except Exception as interception_error:
                                        Logger.error(f"❌ Browser interception also failed: {str(interception_error)[:100]}", exception=interception_error)
                                        # Re-raise original error
                                        raise download_error
                                else:
                                    # Not an HTTP 403 error, re-raise original error
                                    raise download_error

                            # download subtitles
                            subs = unit.video.subtitles_url
                            if subs:
                                # Ensure directory exists before downloading subtitles
                                if not CHAP_DIR.exists():
                                    Logger.warning(f"Chapter directory does not exist, creating: {CHAP_DIR}")
                                    CHAP_DIR.mkdir(parents=True, exist_ok=True)
                                
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
                                    # Ensure directory exists before writing
                                    if not CHAP_DIR.exists():
                                        Logger.warning(f"Chapter directory does not exist, creating: {CHAP_DIR}")
                                        try:
                                            CHAP_DIR.mkdir(parents=True, exist_ok=True)
                                        except Exception as mkdir_err:
                                            Logger.error(f"Failed to create directory: {mkdir_err}")
                                            Logger.error(f"Path length: {len(str(CHAP_DIR))} chars")
                                            raise
                                        
                                        # Verify directory was actually created
                                        if not CHAP_DIR.exists():
                                            error_msg = f"Directory creation failed (path too long?): {CHAP_DIR}"
                                            Logger.error(error_msg)
                                            Logger.error(f"Path length: {len(str(CHAP_DIR))} characters (Windows limit: ~248)")
                                            raise FileNotFoundError(error_msg)
                                    
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
                                    # Ensure directory exists before downloading files
                                    if not CHAP_DIR.exists():
                                        Logger.warning(f"Chapter directory does not exist, creating: {CHAP_DIR}")
                                        CHAP_DIR.mkdir(parents=True, exist_ok=True)
                                    
                                    for archive in files:
                                        file_name_archive = unquote(os.path.basename(archive))
                                        # Separate name and extension before cleaning
                                        name_part = os.path.splitext(file_name_archive)[0]
                                        ext_part = os.path.splitext(file_name_archive)[1]
                                        # Clean only the name, not the extension
                                        name_part = clean_string(name_part, max_length=35)
                                        file_name_archive = f"{name_part}{ext_part}"
                                        dst = CHAP_DIR / f"{jdx}. {file_name_archive}"
                                        Logger.print(f"[{dst.name}]", "[DOWNLOADING-FILES]")
                                        await download(archive, dst)

                                # download readings
                                readings = unit.resources.readings_url
                                if readings:
                                    # Ensure directory exists before saving readings
                                    if not CHAP_DIR.exists():
                                        Logger.warning(f"Chapter directory does not exist, creating: {CHAP_DIR}")
                                        CHAP_DIR.mkdir(parents=True, exist_ok=True)
                                    
                                    dst = CHAP_DIR / f"{jdx}. Lecturas recomendadas.txt"
                                    Logger.print(f"[{dst.name}]", "[SAVING-READINGS]")
                                    with open(dst, 'w', encoding='utf-8') as f:
                                        for lecture in readings:
                                            f.write(lecture + "\n")

                        # download lecture
                        if unit.type == TypeUnit.LECTURE:
                            # Ensure directory exists before downloading lecture
                            if not CHAP_DIR.exists():
                                Logger.warning(f"Chapter directory does not exist, creating: {CHAP_DIR}")
                                CHAP_DIR.mkdir(parents=True, exist_ok=True)
                            
                            # Ensure filename isn't too long
                            safe_file_name = clean_string(unit.title, max_length=35)
                            dst = CHAP_DIR / f"{jdx}. {safe_file_name}.mhtml"
                            Logger.print(f"[{dst.name}]", "[DOWNLOADING-LECTURE]")
                            await self.save_page(unit.url, path=dst, wait_for_images=True, **kwargs)
                        
                        # Mark unit as completed
                        self.progress.complete_unit(course_id, unit_id)
                        
                    except Exception as e:
                        error_msg = f"Error downloading unit: {str(e)}"
                        Logger.error(f"{error_msg} for '{unit.title}'", exception=e)
                        Logger.debug(f"Unit type: {unit.type}, Unit ID: {unit_id}")
                        if hasattr(unit, 'video') and unit.video:
                            Logger.debug(f"Video URL: {unit.video.url}")
                        self.progress.fail_unit(course_id, unit_id, error_msg)
                        # Continue with next unit instead of stopping

            # Mark course as completed
            self.progress.complete_course(course_id)
            print("=" * 100)
            
        except Exception as e:
            error_msg = f"Error downloading course: {str(e)}"
            Logger.error(error_msg, exception=e)
            Logger.debug(f"Course URL: {url}")
            Logger.debug(f"Course ID: {course_id}")
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
            # Navigate with retry logic for better reliability
            await self._goto_with_retry(page, src, max_retries=3)
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
        /* Estilos especiales para iframes con sandbox (funciones interactivas) */
        iframe[sandbox],
        iframe[src*="jshero.platzi.com"],
        iframe[src*="codesandbox"],
        iframe[src*="stackblitz"],
        iframe[src*="codepen"] {{
            width: 100% !important;
            height: 100vh !important;
            min-height: 600px;
            margin: 0;
            border: none;
            border-radius: 0;
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
            Logger.error(f"Error saving page: {str(e)}", exception=e)
            Logger.debug(f"Page URL: {page.url}")
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
        await self._goto_with_retry(page, url, max_retries=3)
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
