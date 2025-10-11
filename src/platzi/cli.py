import asyncio

import typer
from rich import print
from typing_extensions import Annotated

from platzi import AsyncPlatzi, Cache

app = typer.Typer(rich_markup_mode="rich")


@app.command()
def login():
    """
    Open a browser window to Login to Platzi.

    Usage:
        platzi login
    """
    asyncio.run(_login())


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
):
    """
    Download a Platzi course from the given URL.

    Arguments:
        url: str - The URL of the course to download.

    Usage:
        platzi download <url>

    Example:
        platzi download https://platzi.com/cursos/python/
    """
    asyncio.run(_download(url, quality=quality, overwrite=overwrite))


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
):
    """
    Download multiple Platzi courses/paths from a text file.
    
    The file should contain one URL per line.
    Lines starting with # are treated as comments and ignored.
    Empty lines are also ignored.

    Arguments:
        file_path: str - Path to the text file with URLs (default: urls.txt)

    Usage:
        platzi batch-download
        platzi batch-download urls.txt
        platzi batch-download custom_urls.txt --quality 720 --no-clear-cache

    Example urls.txt:
        # My courses
        https://platzi.com/cursos/python/
        https://platzi.com/ruta/desarrollo-frontend-angular/
    """
    asyncio.run(_batch_download(file_path, quality=quality, overwrite=overwrite, clear_cache_after_each=clear_cache_after_each))


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
):
    """
    Retry downloading all failed courses and units from the checkpoint file.
    
    This command reads the download_progress.json file and attempts to
    re-download all items that previously failed.

    Usage:
        platzi retry-failed
        platzi retry-failed --quality 720
        platzi retry-failed --checkpoint custom_progress.json

    Example:
        platzi retry-failed
    """
    asyncio.run(_retry_failed(quality=quality, checkpoint_file=checkpoint_file))


async def _login():
    async with AsyncPlatzi() as platzi:
        await platzi.login()


async def _logout():
    async with AsyncPlatzi() as platzi:
        await platzi.logout()


async def _download(url: str, **kwargs):
    async with AsyncPlatzi() as platzi:
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
    
    # Process each URL
    async with AsyncPlatzi() as platzi:
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


async def _retry_failed(quality: str = False, checkpoint_file: str = "download_progress.json"):
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
    
    async with AsyncPlatzi() as platzi:
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

