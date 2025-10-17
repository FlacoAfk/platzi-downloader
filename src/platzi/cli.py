import asyncio

import typer
from rich import print
from typing_extensions import Annotated

from platzi import AsyncPlatzi, Cache

app = typer.Typer(rich_markup_mode="rich")


@app.command()
def login(
    browser: Annotated[
        str,
        typer.Option(
            "--browser",
            "-b",
            help="Browser to use: firefox or chromium.",
            show_default=True,
        ),
    ] = "firefox",
    headless: Annotated[
        bool,
        typer.Option(
            "--headless/--no-headless",
            "-h",
            help="Hide browser window (Firefox: headless, Chromium: 1x1px off-screen).",
            show_default=True,
        ),
    ] = False,
):
    """
    Open a browser window to Login to Platzi.

    Usage:
        platzi login                              # Visible window (default for login)
        platzi login --browser chromium
        platzi login --no-headless                # Visible window
        platzi login --headless                   # Hidden (Firefox: headless, Chromium: 1x1px)
    """
    asyncio.run(_login(browser=browser, headless=headless))


@app.command()
def logout():
    """
    Delete the Platzi session from the local storage.

    Usage:
        platzi logout
    """
    asyncio.run(_logout())


@app.command()
def download(
    url: Annotated[
        str,
        typer.Argument(
            help="The URL of the course to download",
            show_default=False,
        ),
    ],
    quality: Annotated[
        str,
        typer.Option(
            "--quality",
            "-q",
            help="The quality of the video to download.",
            show_default=True,
        ),
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            "-w",
            help="Overwrite files if exist.",
            show_default=True,
        ),
    ] = False,
    browser: Annotated[
        str,
        typer.Option(
            "--browser",
            "-b",
            help="Browser to use: firefox or chromium.",
            show_default=True,
        ),
    ] = "firefox",
    headless: Annotated[
        bool,
        typer.Option(
            "--headless/--no-headless",
            help="Hide browser window (Firefox: headless, Chromium: 1x1px off-screen).",
            show_default=True,
        ),
    ] = True,
):
    """
    Download a Platzi course from the given URL.

    Arguments:
        url: str - The URL of the course to download.

    Usage:
        platzi download <url>                                # Hidden (default)
        platzi download <url> --no-headless                  # Visible window
        platzi download <url> --browser chromium

    Example:
        platzi download https://platzi.com/cursos/python/
        platzi download https://platzi.com/cursos/python/ --no-headless  # Visible
    """
    asyncio.run(_download(url, quality=quality, overwrite=overwrite, browser=browser, headless=headless))


@app.command()
def clear_cache():
    """
    Clear the Platzi CLI cache.

    Usage:
        platzi clear-cache
    """
    Cache.clear()
    print("[green]Cache cleared successfully 🗑️[/green]")


@app.command()
def batch_download(
    file_path: Annotated[
        str,
        typer.Argument(
            help="Path to the text file containing URLs (one per line)",
            show_default=False,
        ),
    ] = "urls.txt",
    quality: Annotated[
        str,
        typer.Option(
            "--quality",
            "-q",
            help="The quality of the video to download.",
            show_default=True,
        ),
    ] = False,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            "-w",
            help="Overwrite files if exist.",
            show_default=True,
        ),
    ] = False,
    clear_cache_after_each: Annotated[
        bool,
        typer.Option(
            "--clear-cache",
            "-c",
            help="Clear cache after each course/path download.",
            show_default=True,
        ),
    ] = True,
    browser: Annotated[
        str,
        typer.Option(
            "--browser",
            "-b",
            help="Browser to use: firefox or chromium.",
            show_default=True,
        ),
    ] = "firefox",
    headless: Annotated[
        bool,
        typer.Option(
            "--headless/--no-headless",
            help="Hide browser window (Firefox: headless, Chromium: 1x1px off-screen).",
            show_default=True,
        ),
    ] = True,
):
    """
    Download multiple Platzi courses/paths from a text file.
    
    The file should contain one URL per line.
    Lines starting with # are treated as comments and ignored.
    Empty lines are also ignored.

    Arguments:
        file_path: str - Path to the text file with URLs (default: urls.txt)

    Usage:
        platzi batch-download                                # Hidden (default)
        platzi batch-download urls.txt --no-headless         # Visible window
        platzi batch-download custom_urls.txt --quality 720 --no-clear-cache

    Example urls.txt:
        # My courses
        https://platzi.com/cursos/python/
        https://platzi.com/ruta/desarrollo-frontend-angular/
    """
    asyncio.run(_batch_download(file_path, quality=quality, overwrite=overwrite, clear_cache_after_each=clear_cache_after_each, browser=browser, headless=headless))


@app.command()
def retry_failed(
    quality: Annotated[
        str,
        typer.Option(
            "--quality",
            "-q",
            help="The quality of the video to download.",
            show_default=True,
        ),
    ] = False,
    checkpoint_file: Annotated[
        str,
        typer.Option(
            "--checkpoint",
            "-f",
            help="Path to the checkpoint file.",
            show_default=True,
        ),
    ] = "download_progress.json",
    browser: Annotated[
        str,
        typer.Option(
            "--browser",
            "-b",
            help="Browser to use: firefox or chromium.",
            show_default=True,
        ),
    ] = "firefox",
    headless: Annotated[
        bool,
        typer.Option(
            "--headless/--no-headless",
            help="Hide browser window (Firefox: headless, Chromium: 1x1px off-screen).",
            show_default=True,
        ),
    ] = True,
):
    """
    Retry downloading all failed courses and units from the checkpoint file.
    
    This command reads the download_progress.json file and attempts to
    re-download all items that previously failed.

    Usage:
        platzi retry-failed                          # Hidden (default)
        platzi retry-failed --no-headless            # Visible window
        platzi retry-failed --quality 720
        platzi retry-failed --checkpoint custom_progress.json

    Example:
        platzi retry-failed
    """
    asyncio.run(_retry_failed(quality=quality, checkpoint_file=checkpoint_file, browser=browser, headless=headless))


async def _login(browser: str = "firefox", headless: bool = False):
    # Login typically requires a visible browser for manual authentication
    # headless=False means visible window
    # headless=True means hidden (Firefox: headless, Chromium: 1x1px off-screen)
    async with AsyncPlatzi(browser_type=browser, headless=headless) as platzi:
        await platzi.login()


async def _logout():
    async with AsyncPlatzi() as platzi:
        await platzi.logout()


async def _download(url: str, **kwargs):
    browser = kwargs.pop('browser', 'firefox')
    headless = kwargs.pop('headless', True)
    async with AsyncPlatzi(browser_type=browser, headless=headless) as platzi:
        await platzi.download(url, **kwargs)


async def _batch_download(file_path: str, **kwargs):
    from pathlib import Path
    
    clear_cache_after_each = kwargs.pop('clear_cache_after_each', True)
    
    # Read and parse URLs from file
    urls_file = Path(file_path)
    
    if not urls_file.exists():
        print(f"[red]Error: File '{file_path}' not found![/red]")
        return
    
    try:
        with open(urls_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"[red]Error reading file: {e}[/red]")
        return
    
    # Filter valid URLs (ignore comments and empty lines)
    urls = []
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        # Ignore empty lines and comments
        if not line or line.startswith('#'):
            continue
        # Basic URL validation
        if line.startswith('http://') or line.startswith('https://'):
            urls.append(line)
        else:
            print(f"[yellow]Warning: Line {line_num} is not a valid URL, skipping: {line}[/yellow]")
    
    if not urls:
        print("[yellow]No valid URLs found in the file.[/yellow]")
        return
    
    print(f"\n[bold green]{'='*100}[/bold green]")
    print(f"[bold green]🚀 Starting batch download of {len(urls)} items[/bold green]")
    print(f"[bold green]{'='*100}[/bold green]\n")
    
    if clear_cache_after_each:
        print("[cyan]ℹ️  Cache will be cleared after each download[/cyan]\n")
    
    # Track statistics
    successful = 0
    failed = 0
    failed_urls = []
    
    # Extract browser and headless from kwargs
    browser = kwargs.pop('browser', 'firefox')
    headless = kwargs.pop('headless', True)
    
    # Process each URL
    async with AsyncPlatzi(browser_type=browser, headless=headless) as platzi:
        for idx, url in enumerate(urls, 1):
            print(f"\n[bold blue]{'='*100}[/bold blue]")
            print(f"[bold blue]📥 Processing item {idx}/{len(urls)}[/bold blue]")
            print(f"[bold blue]URL: {url}[/bold blue]")
            print(f"[bold blue]{'='*100}[/bold blue]\n")
            
            try:
                await platzi.download(url, **kwargs)
                successful += 1
                print(f"\n[green]✅ Successfully downloaded item {idx}/{len(urls)}: {url}[/green]")
                
                # Clear cache after each successful download if enabled
                if clear_cache_after_each:
                    Cache.clear()
                    print("[green]🗑️  Cache cleared[/green]")
                
            except Exception as e:
                failed += 1
                failed_urls.append((url, str(e)))
                print(f"\n[red]❌ Failed to download item {idx}/{len(urls)}: {url}[/red]")
                print(f"[red]Error: {e}[/red]")
                print("[yellow]⏭️  Continuing with next item...[/yellow]")
    
    # Summary
    print(f"\n[bold green]{'='*100}[/bold green]")
    print(f"[bold green]📊 BATCH DOWNLOAD SUMMARY[/bold green]")
    print(f"[bold green]{'='*100}[/bold green]")
    print(f"[green]Total items: {len(urls)}[/green]")
    print(f"[green]✅ Successful: {successful}[/green]")
    print(f"[red]❌ Failed: {failed}[/red]")
    
    if failed_urls:
        print(f"\n[bold red]Failed URLs:[/bold red]")
        for url, error in failed_urls:
            print(f"[red]  • {url}[/red]")
            print(f"[red]    Error: {error}[/red]")
    
    print(f"\n[bold green]{'='*100}[/bold green]")
    
    if successful == len(urls):
        print("[bold green]🎉 All downloads completed successfully![/bold green]")
    elif successful > 0:
        print(f"[bold yellow]⚠️  Completed with {failed} error(s)[/bold yellow]")
    else:
        print("[bold red]❌ All downloads failed[/bold red]")
    
    print(f"[bold green]{'='*100}[/bold green]\n")


async def _retry_failed(quality: str = False, checkpoint_file: str = "download_progress.json", browser: str = "firefox", headless: bool = True):
    """Retry all failed downloads from the checkpoint file."""
    from pathlib import Path
    from platzi.progress_tracker import ProgressTracker
    
    checkpoint_path = Path(checkpoint_file)
    
    if not checkpoint_path.exists():
        print(f"[red]Error: Checkpoint file '{checkpoint_file}' not found![/red]")
        print(f"[yellow]No failed downloads to retry.[/yellow]")
        return
    
    # Load progress tracker
    tracker = ProgressTracker(checkpoint_file)
    
    # Get failed items
    failed_courses = tracker.get_failed_courses()
    failed_units = tracker.get_failed_units()
    
    total_failed = len(failed_courses) + len(failed_units)
    
    if total_failed == 0:
        print("[green]✅ No failed downloads found! All items completed successfully.[/green]")
        return
    
    print(f"\n[bold yellow]{'='*100}[/bold yellow]")
    print(f"[bold yellow]🔄 Retrying {total_failed} failed downloads[/bold yellow]")
    print(f"[bold yellow]   - {len(failed_courses)} failed courses[/bold yellow]")
    print(f"[bold yellow]   - {len(failed_units)} failed units[/bold yellow]")
    print(f"[bold yellow]{'='*100}[/bold yellow]\n")
    
    successful = 0
    still_failed = 0
    
    async with AsyncPlatzi(browser_type=browser, headless=headless) as platzi:
        # Retry failed courses
        if failed_courses:
            print(f"[bold cyan]📚 Retrying {len(failed_courses)} failed courses...[/bold cyan]\n")
            
            for idx, (course_id, course_data) in enumerate(failed_courses.items(), 1):
                title = course_data.get('title', 'Unknown')
                error = course_data.get('error', 'Unknown error')
                
                print(f"\n[bold blue]{'='*100}[/bold blue]")
                print(f"[bold blue]🔄 Retrying course {idx}/{len(failed_courses)}: {title}[/bold blue]")
                print(f"[yellow]Previous error: {error}[/yellow]")
                print(f"[bold blue]{'='*100}[/bold blue]\n")
                
                # Construct URL from course_id (assuming pattern)
                url = f"https://platzi.com/cursos/{course_id}/"
                
                try:
                    # Reset the course status before retrying
                    tracker.reset_course(course_id)
                    
                    await platzi.download(url, quality=quality, overwrite=True)
                    successful += 1
                    print(f"\n[green]✅ Successfully retried course: {title}[/green]")
                    
                except Exception as e:
                    still_failed += 1
                    print(f"\n[red]❌ Still failed: {title}[/red]")
                    print(f"[red]Error: {e}[/red]")
        
        # Note: For failed units, we would need more context about which course they belong to
        # For now, we'll focus on failed courses
        if failed_units:
            print(f"\n[yellow]ℹ️  {len(failed_units)} failed units detected.[/yellow]")
            print(f"[yellow]These will be retried when their parent courses are re-downloaded.[/yellow]")
    
    # Summary
    print(f"\n[bold green]{'='*100}[/bold green]")
    print(f"[bold green]📊 RETRY SUMMARY[/bold green]")
    print(f"[bold green]{'='*100}[/bold green]")
    print(f"[green]Total retried: {len(failed_courses)}[/green]")
    print(f"[green]✅ Successful: {successful}[/green]")
    print(f"[red]❌ Still failed: {still_failed}[/red]")
    print(f"[bold green]{'='*100}[/bold green]\n")
    
    if successful == len(failed_courses):
        print("[bold green]🎉 All failed items successfully retried![/bold green]")
    elif successful > 0:
        print(f"[bold yellow]⚠️  Completed with {still_failed} item(s) still failing[/bold yellow]")
    else:
        print("[bold red]❌ All retries failed[/bold red]")


@app.command()
def clean_tracking(
    checkpoint: Annotated[
        str,
        typer.Option(
            "--checkpoint",
            "-c",
            help="Path to checkpoint file",
            show_default=True,
        ),
    ] = "download_progress.json",
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Preview changes without modifying the checkpoint",
        ),
    ] = False,
):
    """
    Clean tracking data by removing entries for non-existent files.
    
    This removes completed courses/units from the tracker if their files
    are no longer on disk. Useful after manually deleting files.
    
    Usage:
        platzi clean-tracking --dry-run     # Preview changes
        platzi clean-tracking                # Apply changes
    """
    asyncio.run(_clean_tracking(checkpoint=checkpoint, dry_run=dry_run))


async def _clean_tracking(checkpoint: str = "download_progress.json", dry_run: bool = False):
    """Clean tracking implementation."""
    import json
    import shutil
    from datetime import datetime
    from pathlib import Path
    from platzi.utils import clean_string
    
    def find_course_directory(course_title: str) -> Path:
        """Try to find the course directory."""
        courses_base = Path("Courses")
        if not courses_base.exists():
            return None
        
        clean_title = clean_string(course_title, max_length=80)
        
        # Try direct path
        direct_path = courses_base / clean_title
        if direct_path.exists():
            return direct_path
        
        # Try to find in learning paths
        for learning_path in courses_base.iterdir():
            if learning_path.is_dir():
                for course_dir in learning_path.iterdir():
                    if course_dir.is_dir() and clean_title in course_dir.name:
                        return course_dir
        
        return None
    
    def find_unit_files(course_dir: Path, unit_index: int, unit_title: str) -> list:
        """Find files for a specific unit."""
        if not course_dir or not course_dir.exists():
            return []
        
        # Clean and normalize the title for comparison
        clean_title = clean_string(unit_title, max_length=50).lower()
        # Remove common punctuation that gets stripped in filenames
        clean_title_normalized = clean_title.replace(':', '').replace('?', '').replace('¿', '').strip()
        
        possible_files = set()  # Use set to avoid duplicates
        
        # Search in all chapter directories
        for chapter_dir in course_dir.iterdir():
            if not chapter_dir.is_dir():
                continue
                
            # Search by title pattern (more flexible than by index)
            for file_path in chapter_dir.iterdir():
                if not file_path.is_file():
                    continue
                    
                # Check if filename contains the unit title
                # Format: "N. Title.ext" so we check after the first "."
                filename = file_path.stem  # filename without extension
                
                # Extract title part after "N. " if it exists
                if '. ' in filename:
                    parts = filename.split('. ', 1)
                    if len(parts) == 2:
                        title_part = parts[1].lower()
                        title_part_normalized = title_part.replace(':', '').replace('?', '').replace('¿', '').strip()
                        
                        # Match using both original and normalized titles
                        # This handles cases like "Quiz: Title" vs "Quiz Title"
                        if (title_part.startswith(clean_title) or 
                            clean_title in title_part or 
                            title_part_normalized.startswith(clean_title_normalized) or
                            clean_title_normalized in title_part_normalized or
                            (len(title_part) > 10 and title_part in clean_title) or
                            (len(title_part_normalized) > 10 and title_part_normalized in clean_title_normalized)):
                            possible_files.add(file_path)
        
        return list(possible_files)
    
    # Main logic
    checkpoint_path = Path(checkpoint)
    
    if not checkpoint_path.exists():
        print(f"[red]❌ Checkpoint file not found: {checkpoint}[/red]")
        return
    
    print("[bold green]🧹 TRACKING CLEANER[/bold green]")
    print(f"[bold green]{'='*100}[/bold green]")
    
    if dry_run:
        print("[yellow]⚠️  DRY-RUN MODE: No changes will be made[/yellow]\n")
    
    # Load checkpoint
    print(f"[cyan]📂 Loading checkpoint: {checkpoint}[/cyan]")
    with open(checkpoint_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Backup
    if not dry_run:
        backup_path = checkpoint_path.with_suffix('.json.backup')
        shutil.copy2(checkpoint_path, backup_path)
        print(f"[cyan]💾 Backup created: {backup_path}[/cyan]")
    
    courses_removed = 0
    units_removed = 0
    
    # Check courses
    print("\n[bold cyan]🔍 Checking courses...[/bold cyan]")
    courses_to_remove = []
    
    for course_id, course_data in data.get("courses", {}).items():
        course_title = course_data.get("title", "Unknown")
        course_status = course_data.get("status", "")
        
        if course_status != "completed":
            continue
        
        course_dir = find_course_directory(course_title)
        
        if not course_dir or not course_dir.exists():
            print(f"  [red]❌ Course directory not found: {course_title}[/red]")
            print(f"     [dim]Course ID: {course_id}[/dim]")
            courses_to_remove.append(course_id)
            courses_removed += 1
            continue
        
        print(f"  [green]✅ Course found: {course_title}[/green]")
        
        # Check units
        units = course_data.get("units", {})
        units_to_remove = []
        
        for unit_index, (unit_id, unit_data) in enumerate(units.items(), 1):
            unit_title = unit_data.get("title", "Unknown")
            unit_status = unit_data.get("status", "")
            
            if unit_status != "completed":
                continue
            
            unit_files = find_unit_files(course_dir, unit_index, unit_title)
            
            if not unit_files:
                print(f"    [red]❌ Unit files not found: [{unit_index}] {unit_title}[/red]")
                units_to_remove.append(unit_id)
                units_removed += 1
            else:
                print(f"    [green]✅ Unit found: [{unit_index}] {unit_title}[/green] [dim]({len(unit_files)} files)[/dim]")
        
        # Remove units
        if units_to_remove and not dry_run:
            for unit_id in units_to_remove:
                del course_data["units"][unit_id]
            
            remaining_completed = sum(1 for u in course_data["units"].values() if u.get("status") == "completed")
            if remaining_completed == 0:
                course_data["status"] = "failed"
                course_data["error"] = "All units were removed (files not found)"
        elif units_to_remove and dry_run:
            print(f"    [yellow][DRY-RUN] Would remove {len(units_to_remove)} units[/yellow]")
    
    # Remove courses
    if courses_to_remove and not dry_run:
        for course_id in courses_to_remove:
            del data["courses"][course_id]
    elif courses_to_remove and dry_run:
        print(f"\n[yellow][DRY-RUN] Would remove {len(courses_to_remove)} courses[/yellow]")
    
    # Update statistics
    if not dry_run and (courses_removed > 0 or units_removed > 0):
        stats = data.get("statistics", {})
        stats["completed_courses"] = max(0, stats.get("completed_courses", 0) - courses_removed)
        stats["completed_units"] = max(0, stats.get("completed_units", 0) - units_removed)
        data["last_cleaned"] = datetime.now().isoformat()
        data["last_updated"] = datetime.now().isoformat()
        
        with open(checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"\n[green]✅ Checkpoint updated: {checkpoint}[/green]")
    
    # Summary
    print(f"\n[bold green]{'='*100}[/bold green]")
    print("[bold green]📊 SUMMARY[/bold green]")
    print(f"[bold green]{'='*100}[/bold green]")
    print(f"  [cyan]Courses removed: {courses_removed}[/cyan]")
    print(f"  [cyan]Units removed: {units_removed}[/cyan]")
    
    if dry_run and (courses_removed > 0 or units_removed > 0):
        print("\n[yellow]💡 Run without --dry-run to apply changes[/yellow]")
    elif courses_removed == 0 and units_removed == 0:
        print("\n[green]✨ No cleaning needed - all tracking entries have matching files![/green]")
    else:
        print("\n[green]✅ Tracking cleaned successfully![/green]")
        print("\n[cyan]💡 You can now re-download the removed content:[/cyan]")
        print("   [dim]platzi download <URL>[/dim]")
    
    print(f"[bold green]{'='*100}[/bold green]\n")

