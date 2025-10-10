import asyncio
import re
from pathlib import Path

import aiofiles
import rnet
from playwright.async_api import Page
from unidecode import unidecode

from .helpers import retry
from .logger import Logger


def safe_path(path: Path, max_total_length: int = 240) -> Path:
    """
    Ensure a path doesn't exceed Windows' path length limit.
    If it does, truncate the filename while preserving the extension.
    
    :param path(Path): The path to validate
    :param max_total_length(int): Maximum allowed path length (default: 240, leaving buffer for 260 limit)
    :return Path: Safe path that won't exceed the limit
    """
    path_str = str(path.resolve())
    
    if len(path_str) <= max_total_length:
        return path
    
    # Calculate how much we need to reduce
    excess = len(path_str) - max_total_length
    
    # Get the filename and extension
    name = path.stem
    ext = path.suffix
    parent = path.parent
    
    # Truncate the filename (not the extension)
    if len(name) > excess:
        new_name = name[:len(name) - excess - 3] + "..."  # Add ellipsis
        return parent / f"{new_name}{ext}"
    
    # If truncating filename isn't enough, just use a short name
    return parent / f"file{ext}"


async def progressive_scroll(
    page: Page, time: float = 3, delay: float = 0.1, steps: int = 250
):
    await asyncio.sleep(3)  # delay to avoid rate limiting
    delta, total_time = 0.0, 0.0
    while total_time < time:
        await asyncio.sleep(delay)
        await page.mouse.wheel(0, steps)
        delta += steps
        total_time += delay


def get_course_slug(url: str) -> str:
    """
    Extracts the course slug from a Platzi course URL.

    :param url(str): The Platzi course URL.
    :return str: The course slug.
    :raises Exception: If the URL is not a valid Platzi course URL.

    Example
    -------
    >>> get_course_slug("https://platzi.com/cursos/fastapi-2023/")
    "fastapi-2023"
    """
    pattern = r"https://platzi\.com/cursos/([^/]+)/?"
    match = re.search(pattern, url)
    if not match:
        raise Exception("Invalid course url")
    return match.group(1)


def clean_string(text: str, max_length: int = 100) -> str:
    """
    Remove special characters from a string and strip it.
    Truncates the result if it exceeds max_length to avoid Windows path length issues.

    :param text(str): string to clean
    :param max_length(int): maximum length for the resulting string (default: 100)
    :return str: cleaned string

    Example
    -------
    >>> clean_string("   Hi:;<>?{}|"")
    "Hi"
    """
    result = re.sub(r"[ºª\n\r]|[^\w\s]", "", text)
    result = re.sub(r"\s+", " ", result).strip()
    
    # Truncate if too long (Windows has 260 char path limit)
    if len(result) > max_length:
        result = result[:max_length].strip()
    
    return result


def slugify(text: str) -> str:
    """
    Slugify a string, removing special characters and replacing
    spaces with hyphens.

    :param text(str): string to convert
    :return str: slugified string

    Example
    -------
    >>> slugify(""Café! Frío?"")
    "cafe-frio"
    """
    return unidecode(clean_string(text)).lower().replace(" ", "-")


def get_m3u8_url(content: str) -> str:
    """
    Extract m3u8 URL from HTML content.
    
    Tries multiple methods:
    1. JSON extraction from Next.js data (serverC.hls or serverM.hls) - PREFERRED
    2. Direct URL pattern matching in HTML
    """
    import json
    
    # Method 1: Extract from Next.js JSON data FIRST (more reliable)
    # Handle both escaped (\") and regular (") quotes in JSON
    # Look for patterns like: "serverC":{"id":"serverC","hls":"https://...m3u8"
    # Or escaped: \"serverC\":{\"id\":\"serverC\",\"hls\":\"https://...m3u8\"
    try:
        # Pattern 1: Try with escaped quotes (common in Next.js __NEXT_DATA__)
        json_pattern = r'\\?"(?:serverC|serverM)\\?":\s*\{[^}]*\\?"hls\\?"\s*:\s*\\?"([^\\?"]+\.m3u8[^\\?"]*)'
        json_matches = re.findall(json_pattern, content)
        
        if json_matches:
            # Unescape JSON escaping (\/)
            clean_urls = []
            for match in json_matches:
                url = match.replace(r'\/', '/')
                if "fallback=origin" not in url:
                    clean_urls.append(url)
            
            if clean_urls:
                return clean_urls[0]
            # If all have fallback, use first one
            return json_matches[0].replace(r'\/', '/')
        
        # Pattern 2: Try finding in unescaped JSON (backup)
        json_pattern2 = r'"(?:serverC|serverM)":\s*\{[^}]*"hls"\s*:\s*"([^"]+\.m3u8[^"]*)"'
        json_matches2 = re.findall(json_pattern2, content)
        
        if json_matches2:
            clean_urls = [url for url in json_matches2 if "fallback=origin" not in url]
            if clean_urls:
                return clean_urls[0]
            return json_matches2[0]
            
    except Exception as e:
        pass
    
    # Method 2: Direct pattern matching in HTML (fallback)
    pattern = r"https?://[^\s\"'}\\]+\.m3u8(?:\?[^\s\"'}\\]*)?"
    matches = re.findall(pattern, content)
    
    if matches:
        # Filter out URLs with "fallback=origin" and prefer clean URLs
        clean_matches = [m for m in matches if "fallback=origin" not in m]
        return clean_matches[0] if clean_matches else matches[0]
    
    raise Exception("No m3u8 urls found")


def get_subtitles_url(content: str) -> list[str] | None:
    pattern = r"https?://[^\s\"'}]+\.vtt"
    matches = list(set(re.findall(pattern, content)))

    if not matches:
        return None

    return matches  # returns a list of all found subtitles without repeating


@retry()
async def download(url: str, path: Path, **kwargs):
    overwrite = kwargs.get("overwrite", False)

    if not overwrite and path.exists():
        return

    try:
        path.unlink(missing_ok=True)
        path.parent.mkdir(parents=True, exist_ok=True)

        client = rnet.Client(impersonate=rnet.Impersonate.Firefox139)
        response: rnet.Response = await client.get(url, allow_redirects=True, **kwargs)

        if not response.ok:
            raise Exception(f"[Bad Response: {response.status}]")

        async with aiofiles.open(path, "wb") as file:
            async with response.stream() as streamer:
                async for chunk in streamer:
                    await file.write(chunk)

    except Exception as e:
        Logger.error(f"Downloading file {url} -> {path.name} | {e}")

        return

    finally:
        await response.close()


@retry()
async def download_styles(url: str, **kwargs):

    client = rnet.Client(impersonate=rnet.Impersonate.Firefox139)
    response: rnet.Response = await client.get(url, allow_redirects=True, **kwargs)

    content = await response.text()  # Save content before closing

    await response.close()

    return content
