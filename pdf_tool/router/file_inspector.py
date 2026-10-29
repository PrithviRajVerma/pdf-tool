"""File MIME type and extension detection with content-based fallback."""

from __future__ import annotations

import mimetypes
from pathlib import Path

# Extension aliases — normalize to canonical form
_ALIASES: dict[str, str] = {
    "jpg": "jpeg",
    "tif": "tiff",
    "htm": "html",
    "jpe": "jpeg",
    "jfif": "jpeg",
    "markdown": "md",
    "text": "txt",
}

# Header magic byte signatures for rapid binary file identification
_MAGIC_SIGNATURES: list[tuple[bytes, str]] = [
    (b"%PDF", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
    (b"BM", "bmp"),
    (b"II*\x00", "tiff"),
    (b"MM\x00*", "tiff"),
]

# MIME to canonical extension mapping
_MIME_TO_EXT: dict[str, str] = {
    "application/pdf": "pdf",
    "image/jpeg": "jpeg",
    "image/pjpeg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
    "image/tiff": "tiff",
    "image/x-tiff": "tiff",
    "image/bmp": "bmp",
    "image/x-ms-bmp": "bmp",
    "image/gif": "gif",
    "image/heic": "heic",
    "image/heif": "heif",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-powerpoint": "ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "text/markdown": "md",
    "text/html": "html",
    "text/plain": "txt",
}


class FileInspector:
    """Detects the MIME type and normalized extension of a file.

    Inspects both file extension and actual file content (via magic bytes & MIME),
    allowing files without extensions (e.g. ``scan_12345``) or with misleading extensions
    to be accurately identified and processed.
    """

    def detect_mime(self, path: Path) -> str:
        """Detect the true MIME type of *path*.

        Uses ``python-magic`` (libmagic) for content-based detection,
        falls back to stdlib ``mimetypes`` module if magic is unavailable or file doesn't exist.

        Args:
            path: Path to the file.

        Returns:
            MIME type string, e.g. ``"application/pdf"``.
        """
        if path.exists() and path.is_file():
            try:
                import magic  # type: ignore[import-untyped]

                return magic.from_file(str(path), mime=True)
            except Exception:
                pass

        mime, _ = mimetypes.guess_type(str(path))
        return mime or "application/octet-stream"

    def detect_content_extension(self, path: Path) -> str | None:
        """Inspect the raw file content to identify format without relying on extension.

        Checks magic byte signatures first, then uses ``python-magic`` MIME detection.

        Args:
            path: Path to existing file.

        Returns:
            Canonical extension string (e.g. ``"pdf"``, ``"jpeg"``) or ``None``.
        """
        if not path.exists() or not path.is_file():
            return None

        # 1. Read first 32 bytes for magic signatures
        try:
            with path.open("rb") as f:
                header = f.read(32)
        except OSError:
            header = b""

        for sig, ext in _MAGIC_SIGNATURES:
            if header.startswith(sig):
                return ext

        # WEBP signature: RIFF....WEBP
        if len(header) >= 12 and header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return "webp"

        # HEIC / HEIF signature: ftypheic / ftypmif1 / ftypheix
        if (
            len(header) >= 12
            and header[4:8] == b"ftyp"
            and header[8:12]
            in (
                b"heic",
                b"mif1",
                b"heix",
                b"hevc",
                b"msf1",
            )
        ):
            return "heic"

        # 2. Check python-magic MIME type mapping
        mime = self.detect_mime(path)
        if mime in _MIME_TO_EXT:
            return _MIME_TO_EXT[mime]

        return None

    def detect_extension(self, path: Path) -> str:
        """Return the lowercase, canonical extension of *path* (without dot).

        If the file exists on disk, inspects actual content if the extension
        is missing, empty, or unknown. If the file does not exist, uses the filename extension.

        Applies extension aliases so that ``"jpg"`` becomes ``"jpeg"``, etc.

        Args:
            path: Path to the file.

        Returns:
            Canonical extension string, e.g. ``"jpeg"``, ``"pdf"``, ``"docx"``.
        """
        # If the file exists, inspect content when extension is missing or ambiguous
        if path.exists() and path.is_file():
            ext = path.suffix.lstrip(".").lower()
            canonical_ext = _ALIASES.get(ext, ext)
            content_ext = self.detect_content_extension(path)

            if content_ext is not None:
                # If no extension or extension does not match known formats, use content
                if not canonical_ext or canonical_ext in ("tmp", "bin", "dat"):
                    return content_ext
                # If content extension is a recognized match or alias, use it
                return canonical_ext or content_ext

        ext = path.suffix.lstrip(".").lower()
        return _ALIASES.get(ext, ext)

    def detect(self, path: Path) -> tuple[str, str]:
        """Detect both MIME type and normalized extension.

        Args:
            path: Path to the file.

        Returns:
            Tuple of ``(mime_type, extension)``.
        """
        return self.detect_mime(path), self.detect_extension(path)
