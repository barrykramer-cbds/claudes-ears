"""yt-dlp ingest: fetch a URL's best audio into a directory as an extracted m4a."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import yt_dlp

if TYPE_CHECKING:
    from collections.abc import Callable


class DownloadError(Exception):
    """A URL ingest failed — unsupported URL, network error, or extraction failure."""


def download_audio(
    url: str, dest_dir: Path, on_progress: Callable[[str], None] | None = None
) -> Path:
    """Download and extract the URL's audio into ``dest_dir``; blocking — run off the loop."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    last_percent = -1

    def hook(status: dict[str, object]) -> None:
        nonlocal last_percent
        if on_progress is None or status.get("status") != "downloading":
            return
        downloaded = status.get("downloaded_bytes")
        total = status.get("total_bytes") or status.get("total_bytes_estimate")
        if isinstance(downloaded, int | float) and isinstance(total, int | float) and total > 0:
            percent = int(downloaded * 100 / total)
            if percent != last_percent:
                last_percent = percent
                on_progress(f"{percent}%")

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(dest_dir / "%(title)s [%(id)s].%(ext)s"),
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}],
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as error:
        raise DownloadError(str(error)) from error
    if info is None:
        raise DownloadError(f"no downloadable audio at {url!r}")
    requested = info.get("requested_downloads") or []
    filepath = requested[0].get("filepath") if requested else None
    if not isinstance(filepath, str):
        raise DownloadError("yt-dlp did not report the downloaded file path")
    return Path(filepath)
