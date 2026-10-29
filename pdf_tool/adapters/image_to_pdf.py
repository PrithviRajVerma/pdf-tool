"""Image → PDF adapter using Pillow (+ pillow-heif for HEIC/HEIF)."""

from __future__ import annotations

import time
from pathlib import Path

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError
from pdf_tool.router.registry import registry

_HEIC_EXTENSIONS = {"heic", "heif"}

_SUPPORTED_INPUT_FMTS = [
    "jpeg",
    "jpg",
    "png",
    "webp",
    "tiff",
    "tif",
    "bmp",
    "gif",
    "heic",
    "heif",
]


@registry.register(input_fmts=_SUPPORTED_INPUT_FMTS, output_fmt="pdf")
class ImageToPdfAdapter(BaseAdapter):
    """Convert one or more raster images to a single PDF.

    Supports JPEG, PNG, WEBP, TIFF, BMP, GIF, HEIC, and HEIF formats.
    HEIC/HEIF requires ``pillow-heif`` which is registered automatically.
    """

    @property
    def required_system_deps(self) -> list[str]:
        return []  # Pure Python

    @property
    def engine_name(self) -> str:
        return "Pillow"

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Convert image(s) to a PDF.

        Args:
            input_path: Primary image file.
            output_path: Destination PDF path.
            **options:
                extra_inputs (list[Path]): Additional image paths to merge into the PDF.

        Returns:
            :class:`ConversionResult` metadata.

        Raises:
            InvalidInputError: If an image file cannot be opened.
            ConversionFailedError: If the PDF cannot be saved.
        """
        from PIL import Image, ImageOps  # noqa: PLC0415

        start = time.monotonic()

        extra_inputs: list[Path] = options.get("extra_inputs", [])
        all_paths = [input_path] + list(extra_inputs)

        # Register HEIF opener if any file is HEIC/HEIF
        if any(p.suffix.lstrip(".").lower() in _HEIC_EXTENSIONS for p in all_paths):
            try:
                import pillow_heif  # noqa: PLC0415

                pillow_heif.register_heif_opener()
            except ImportError as exc:
                raise InvalidInputError(
                    "pillow-heif is required for HEIC/HEIF conversion. "
                    "Install it with: pip install pillow-heif"
                ) from exc

        images: list[Image.Image] = []
        for p in all_paths:
            try:
                img = Image.open(str(p))
                img.load()
            except Exception as exc:
                raise InvalidInputError(f"Cannot open image '{p}': {exc}") from exc

            # Auto-rotate based on EXIF orientation
            img = ImageOps.exif_transpose(img) or img

            # Convert RGBA/P/etc. to RGB with white background
            img = _to_rgb(img)
            images.append(img)

        if not images:
            raise InvalidInputError("No images provided for conversion.")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            first = images[0]
            rest = images[1:]
            if rest:
                first.save(
                    str(output_path),
                    format="PDF",
                    save_all=True,
                    append_images=rest,
                )
            else:
                first.save(str(output_path), format="PDF")
        except Exception as exc:
            raise ConversionFailedError(f"Failed to save PDF '{output_path}': {exc}") from exc
        finally:
            for img in images:
                img.close()

        return ConversionResult(
            input_path=input_path,
            output_path=output_path,
            input_size_bytes=sum(p.stat().st_size for p in all_paths if p.exists()),
            output_size_bytes=output_path.stat().st_size if output_path.exists() else 0,
            duration_seconds=time.monotonic() - start,
            engine=self.engine_name,
        )


def _to_rgb(img) -> object:
    """Convert a PIL image to RGB, compositing against a white background if needed."""
    from PIL import Image  # noqa: PLC0415

    if img.mode == "RGB":
        return img
    if img.mode in ("RGBA", "LA", "PA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "PA":
            img = img.convert("RGBA")
        if img.mode == "LA":
            img = img.convert("RGBA")
        background.paste(img, mask=img.split()[-1])
        return background
    return img.convert("RGB")
