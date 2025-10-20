"""
DASH (.mpd) video downloader using FFmpeg.
"""

import asyncio
import functools
import shutil
from pathlib import Path
from .helpers import retry
from .logger import Logger


def ffmpeg_required(func):
    """Decorator to check if FFmpeg is installed."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if not shutil.which("ffmpeg"):
            raise Exception("FFmpeg is required but not found in PATH")
        return await func(*args, **kwargs)
    return wrapper


@ffmpeg_required
@retry()
async def dash_dl(
    url: str,
    path: str | Path,
    **kwargs,
) -> None:
    """
    Download a DASH (.mpd) file and convert it to mp4 using FFmpeg.
    
    DASH (Dynamic Adaptive Streaming over HTTP) is similar to HLS but uses
    a different manifest format (.mpd instead of .m3u8).
    
    :param url(str): The URL of the .mpd file to download.
    :param path(str | Path): The path to save the converted mp4 file.
    :param kwargs: Additional keyword arguments (overwrite, quality, etc).
    :return: None
    """
    
    overwrite = kwargs.get("overwrite", False)
    path = path if isinstance(path, Path) else Path(path)
    
    if not overwrite and path.exists():
        return
    
    # FFmpeg can directly download and convert DASH streams
    # -allowed_extensions ALL: allows all extensions (mpd, m4s, etc)
    # -protocol_whitelist: allows file,http,https,tcp,tls protocols
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-protocol_whitelist", "file,http,https,tcp,tls,crypto",
        "-allowed_extensions", "ALL",
        "-i", url,
        "-c", "copy",  # Copy streams without re-encoding
        "-y",  # Overwrite output file
        str(path)
    ]
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error_msg = stderr.decode() if stderr else "Unknown error"
            Logger.debug(f"FFmpeg DASH download failed for URL: {url}")
            Logger.debug(f"FFmpeg return code: {process.returncode}")
            Logger.debug(f"FFmpeg error output: {error_msg[:500]}")
            raise Exception(f"Error downloading DASH video: {error_msg}")
            
    except Exception as e:
        # Clean up partial file if it exists
        if path.exists():
            path.unlink()
        Logger.debug(f"DASH download error for URL: {url}")
        Logger.debug(f"Target path: {path}")
        raise Exception(f"Error converting DASH to mp4: {str(e)}")
