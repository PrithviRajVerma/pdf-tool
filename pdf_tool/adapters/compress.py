"""Multi-format compression adapter — PDF, Images, and Office Documents."""

from __future__ import annotations

import io
import shutil
import subprocess
import time
import warnings
import zipfile
from pathlib import Path

import pymupdf as fitz
from PIL import Image
from pypdf import PdfReader, PdfWriter

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError

_IMAGE_EXTS = {"jpg", "jpeg", "png", "webp", "tiff", "tif", "bmp", "heic", "heif"}
_OFFICE_EXTS = {"docx", "pptx", "xlsx", "odt", "odp", "ods"}

# Ghostscript PDF settings map
_GS_SETTINGS = {
    "high": "/screen",
    "medium": "/ebook",
    "low": "/printer",
}

_LEVEL_PRESETS = {
    "high": {
        "pdf_target_dpi": 96,
        "pdf_image_max_dim": 1280,
        "pdf_image_quality": 60,
        "image_quality": 60,
        "image_max_dim": 1280,
        "quantize_png": True,
    },
    "medium": {
        "pdf_target_dpi": 150,
        "pdf_image_max_dim": 1920,
        "pdf_image_quality": 75,
        "image_quality": 75,
        "image_max_dim": 1920,
        "quantize_png": False,
    },
    "low": {
        "pdf_target_dpi": 200,
        "pdf_image_max_dim": 2560,
        "pdf_image_quality": 85,
        "image_quality": 85,
        "image_max_dim": 2560,
        "quantize_png": False,
    },
}


class CompressAdapter(BaseAdapter):
    """Compress a PDF, image, or office document to reduce its file size."""

    @property
    def required_system_deps(self) -> list[str]:
        return []

    @property
    def engine_name(self) -> str:
        return "UniversalCompressor"

    def compress(
        self,
        input_path: Path,
        output_path: Path,
        level: str = "medium",
        **options,
    ) -> ConversionResult:
        """Compress *input_path* and write to *output_path*.

        Args:
            input_path: Source file path.
            output_path: Destination compressed path.
            level: Compression level — ``"high"``, ``"medium"``, or ``"low"``.
            **options:
                max_dim (int | None): Optional max pixel dimension override.
                target_size_bytes (int | None): Optional target max file size in bytes.

        Returns:
            :class:`ConversionResult` metadata.

        Raises:
            InvalidInputError: If the source file cannot be read.
            ConversionFailedError: If compression fails.
        """
        start = time.monotonic()

        if not input_path.exists():
            raise InvalidInputError(f"Input file not found: '{input_path}'")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        ext = input_path.suffix.lower().lstrip(".")
        max_dim = options.get("max_dim")
        target_size_bytes = options.get("target_size_bytes")

        if ext == "pdf":
            engine = self._compress_pdf(
                input_path,
                output_path,
                level=level,
                max_dim=max_dim,
                target_size_bytes=target_size_bytes,
            )
        elif ext in _IMAGE_EXTS:
            engine = self._compress_image(
                input_path,
                output_path,
                level=level,
                max_dim=max_dim,
                target_size_bytes=target_size_bytes,
            )
        elif ext in _OFFICE_EXTS:
            engine = self._compress_office(
                input_path,
                output_path,
                level=level,
                max_dim=max_dim,
                target_size_bytes=target_size_bytes,
            )
        else:
            raise InvalidInputError(f"Compression not supported for format: '{ext}'")

        return ConversionResult(
            input_path=input_path,
            output_path=output_path,
            input_size_bytes=input_path.stat().st_size,
            output_size_bytes=output_path.stat().st_size if output_path.exists() else 0,
            duration_seconds=time.monotonic() - start,
            engine=engine,
        )

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Delegate to :meth:`compress`."""
        level = options.get("level", "medium")
        return self.compress(input_path, output_path, level=level, **options)

    # ------------------------------------------------------------------
    # PDF Compression
    # ------------------------------------------------------------------

    def _compress_pdf(
        self,
        input_path: Path,
        output_path: Path,
        level: str,
        max_dim: int | None = None,
        target_size_bytes: int | None = None,
    ) -> str:
        gs_path = shutil.which("gs")
        if gs_path and not target_size_bytes:
            try:
                pdf_setting = _GS_SETTINGS.get(level.lower(), "/ebook")
                self._compress_gs(gs_path, input_path, output_path, pdf_setting)
                return "Ghostscript"
            except Exception as exc:
                warnings.warn(
                    f"Ghostscript compression failed ({exc}), falling back to PyMuPDF.",
                    UserWarning,
                    stacklevel=2,
                )

        warnings.warn(
            "Ghostscript ('gs') not found in PATH. Using PyMuPDF compression.",
            UserWarning,
            stacklevel=2,
        )

        try:
            self._compress_pymupdf(
                input_path,
                output_path,
                level=level,
                max_dim=max_dim,
                target_size_bytes=target_size_bytes,
            )
            return "PyMuPDF"
        except Exception as exc:
            warnings.warn(
                f"PyMuPDF compression failed ({exc}), falling back to pypdf.",
                UserWarning,
                stacklevel=2,
            )
            self._compress_pypdf(input_path, output_path)
            return "pypdf"

    def _compress_gs(
        self,
        gs_bin: str,
        input_path: Path,
        output_path: Path,
        pdf_setting: str,
    ) -> None:
        cmd = [
            gs_bin,
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.4",
            f"-dPDFSETTINGS={pdf_setting}",
            "-dNOPAUSE",
            "-dQUIET",
            "-dBATCH",
            f"-sOutputFile={output_path}",
            str(input_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ConversionFailedError(
                f"Ghostscript failed (exit {result.returncode}): {result.stderr}"
            )

    def _compress_pymupdf(
        self,
        input_path: Path,
        output_path: Path,
        level: str,
        max_dim: int | None = None,
        target_size_bytes: int | None = None,
    ) -> None:
        try:
            doc = fitz.open(str(input_path))
        except Exception as exc:
            raise InvalidInputError(f"Cannot read PDF '{input_path}': {exc}") from exc

        preset = _LEVEL_PRESETS.get(level.lower(), _LEVEL_PRESETS["medium"])
        target_max_dim = max_dim or preset["pdf_image_max_dim"]
        target_quality = preset["pdf_image_quality"]
        target_dpi = preset["pdf_target_dpi"]

        # Step 1: Collect all image occurrences and display bounding boxes
        xref_rects: dict[int, list[fitz.Rect]] = {}
        for page in doc:
            try:
                images = page.get_images(full=True)
            except Exception:
                images = []
            for img_info in images:
                xref = img_info[0]
                if xref not in xref_rects:
                    xref_rects[xref] = []
                try:
                    rects = page.get_image_rects(xref)
                    if rects:
                        xref_rects[xref].extend(rects)
                except Exception:
                    pass

        # Step 2: Downsample and recompress embedded images based on display DPI
        for xref, rects in xref_rects.items():
            try:
                extracted = doc.extract_image(xref)
                raw_bytes = extracted.get("image")
                if not raw_bytes or len(raw_bytes) < 8192:  # Skip tiny icons / decorative glyphs
                    continue

                pil_img = Image.open(io.BytesIO(raw_bytes))
                orig_w, orig_h = pil_img.size

                # Calculate display dimensions in inches
                if rects:
                    max_disp_w_inches = max(r.width / 72.0 for r in rects)
                    max_disp_h_inches = max(r.height / 72.0 for r in rects)
                    target_pixel_w = max(64, int(max_disp_w_inches * target_dpi))
                    target_pixel_h = max(64, int(max_disp_h_inches * target_dpi))
                else:
                    target_pixel_w = target_max_dim
                    target_pixel_h = target_max_dim

                if target_max_dim:
                    target_pixel_w = min(target_pixel_w, target_max_dim)
                    target_pixel_h = min(target_pixel_h, target_max_dim)

                # Downsample if image exceeds display bounds by > 10%
                if orig_w > target_pixel_w * 1.1 or orig_h > target_pixel_h * 1.1:
                    pil_img.thumbnail((target_pixel_w, target_pixel_h), Image.Resampling.LANCZOS)

                out_buf = io.BytesIO()
                if pil_img.mode in ("RGBA", "LA") or (
                    pil_img.mode == "P" and "transparency" in pil_img.info
                ):
                    pil_img.save(out_buf, format="PNG", optimize=True)
                else:
                    if pil_img.mode != "RGB":
                        pil_img = pil_img.convert("RGB")
                    pil_img.save(out_buf, format="JPEG", quality=target_quality, optimize=True)

                new_bytes = out_buf.getvalue()
                if len(new_bytes) < len(raw_bytes):
                    # Replace image stream on the document
                    for page in doc:
                        try:
                            page.replace_image(xref, stream=new_bytes)
                        except Exception:
                            pass
            except Exception:
                pass

        try:
            doc.save(str(output_path), garbage=4, deflate=True, clean=True)
        except Exception as exc:
            raise ConversionFailedError(f"Failed to save compressed PDF: {exc}") from exc
        finally:
            doc.close()

    def _compress_pypdf(self, input_path: Path, output_path: Path) -> None:
        try:
            reader = PdfReader(str(input_path))
        except Exception as exc:
            raise InvalidInputError(f"Cannot read PDF '{input_path}': {exc}") from exc

        writer = PdfWriter()
        for page in reader.pages:
            page.compress_content_streams()
            writer.add_page(page)

        try:
            with output_path.open("wb") as fh:
                writer.write(fh)
        except Exception as exc:
            raise ConversionFailedError(
                f"Failed to write compressed PDF '{output_path}': {exc}"
            ) from exc

    # ------------------------------------------------------------------
    # Image Compression
    # ------------------------------------------------------------------

    def _compress_image(
        self,
        input_path: Path,
        output_path: Path,
        level: str,
        max_dim: int | None = None,
        target_size_bytes: int | None = None,
    ) -> str:
        try:
            pil_img = Image.open(input_path)
        except Exception as exc:
            raise InvalidInputError(f"Cannot read image '{input_path}': {exc}") from exc

        preset = _LEVEL_PRESETS.get(level.lower(), _LEVEL_PRESETS["medium"])
        target_max_dim = max_dim or preset["image_max_dim"]
        target_quality = preset["image_quality"]

        w, h = pil_img.size
        if target_max_dim and (w > target_max_dim or h > target_max_dim):
            pil_img.thumbnail((target_max_dim, target_max_dim), Image.Resampling.LANCZOS)

        out_ext = output_path.suffix.lower().lstrip(".")
        try:
            if target_size_bytes and input_path.stat().st_size > target_size_bytes:
                # Target-size driven iterative compression
                best_bytes: bytes | None = None
                img_copy = pil_img.copy()
                for q in (85, 75, 65, 50, 35):
                    buf = io.BytesIO()
                    if out_ext in ("jpg", "jpeg"):
                        if img_copy.mode != "RGB":
                            img_copy = img_copy.convert("RGB")
                        img_copy.save(
                            buf,
                            format="JPEG",
                            quality=q,
                            optimize=True,
                            progressive=True,
                            subsampling="4:2:0",
                        )
                    elif out_ext == "webp":
                        img_copy.save(buf, format="WEBP", quality=q, method=6)
                    else:
                        img_copy.save(buf, format=out_ext.upper(), optimize=True)

                    data = buf.getvalue()
                    if len(data) <= target_size_bytes:
                        best_bytes = data
                        break
                    # Scale down if quality reduction alone wasn't enough
                    new_w = max(64, int(img_copy.width * 0.85))
                    new_h = max(64, int(img_copy.height * 0.85))
                    img_copy.thumbnail((new_w, new_h), Image.Resampling.LANCZOS)

                if best_bytes:
                    output_path.write_bytes(best_bytes)
                    return "Pillow (Target Size)"

            # Standard preset-based compression
            if out_ext in ("jpg", "jpeg"):
                if pil_img.mode != "RGB":
                    pil_img = pil_img.convert("RGB")
                pil_img.save(
                    output_path,
                    format="JPEG",
                    quality=target_quality,
                    optimize=True,
                    progressive=True,
                    subsampling="4:2:0",
                )
            elif out_ext == "png":
                if preset["quantize_png"] and pil_img.mode in ("RGB", "RGBA"):
                    try:
                        q_img = pil_img.quantize(colors=256, method=Image.Resampling.MEDIANCUT)
                        q_img.save(output_path, format="PNG", optimize=True)
                    except Exception:
                        pil_img.save(output_path, format="PNG", optimize=True)
                else:
                    pil_img.save(output_path, format="PNG", optimize=True)
            elif out_ext == "webp":
                pil_img.save(output_path, format="WEBP", quality=target_quality, method=6)
            else:
                pil_img.save(output_path, optimize=True)
        except Exception as exc:
            raise ConversionFailedError(f"Failed to compress image '{input_path}': {exc}") from exc

        # Ensure output is not larger than original
        if output_path.exists() and output_path.stat().st_size > input_path.stat().st_size:
            shutil.copy2(input_path, output_path)

        return "Pillow"

    # ------------------------------------------------------------------
    # Office Document Compression
    # ------------------------------------------------------------------

    def _compress_office(
        self,
        input_path: Path,
        output_path: Path,
        level: str,
        max_dim: int | None = None,
        target_size_bytes: int | None = None,
    ) -> str:
        preset = _LEVEL_PRESETS.get(level.lower(), _LEVEL_PRESETS["medium"])
        target_max_dim = max_dim or preset["image_max_dim"]
        target_quality = preset["image_quality"]

        try:
            in_zip = zipfile.ZipFile(str(input_path), "r")
        except Exception as exc:
            raise InvalidInputError(f"Cannot read office document '{input_path}': {exc}") from exc

        try:
            with zipfile.ZipFile(
                str(output_path), "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
            ) as out_zip:
                for item in in_zip.infolist():
                    data = in_zip.read(item.filename)
                    if "/media/" in item.filename.lower() and any(
                        item.filename.lower().endswith(f".{ext}")
                        for ext in ("png", "jpg", "jpeg", "tif", "tiff", "bmp")
                    ):
                        try:
                            pil_img = Image.open(io.BytesIO(data))
                            w, h = pil_img.size
                            if target_max_dim and (w > target_max_dim or h > target_max_dim):
                                pil_img.thumbnail(
                                    (target_max_dim, target_max_dim), Image.Resampling.LANCZOS
                                )

                            buf = io.BytesIO()
                            if item.filename.lower().endswith(".png"):
                                if preset["quantize_png"] and pil_img.mode in ("RGB", "RGBA"):
                                    q = pil_img.quantize(
                                        colors=256, method=Image.Resampling.MEDIANCUT
                                    )
                                    q.save(buf, format="PNG", optimize=True)
                                else:
                                    pil_img.save(buf, format="PNG", optimize=True)
                            else:
                                if pil_img.mode != "RGB":
                                    pil_img = pil_img.convert("RGB")
                                pil_img.save(
                                    buf,
                                    format="JPEG",
                                    quality=target_quality,
                                    optimize=True,
                                    progressive=True,
                                )

                            new_data = buf.getvalue()
                            if len(new_data) < len(data):
                                data = new_data
                        except Exception:
                            pass

                    out_zip.writestr(item, data)
            in_zip.close()
        except Exception as exc:
            raise ConversionFailedError(
                f"Failed to compress office document '{input_path}': {exc}"
            ) from exc

        if output_path.exists() and output_path.stat().st_size > input_path.stat().st_size:
            shutil.copy2(input_path, output_path)

        return "ZipDeflate + Pillow"
