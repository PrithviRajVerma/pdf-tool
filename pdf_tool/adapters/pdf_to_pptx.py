"""PDF to PowerPoint presentation (.pptx) adapter using python-pptx and PyMuPDF."""

from __future__ import annotations

import io
import re
import time
from pathlib import Path

import pymupdf as fitz
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Pt
from rich.console import Console

from pdf_tool.adapters.base import BaseAdapter, ConversionResult
from pdf_tool.adapters.pdf_to_image import _parse_page_range
from pdf_tool.exceptions import ConversionFailedError, InvalidInputError
from pdf_tool.router.registry import registry

console = Console()

# Remove control characters that are illegal in OpenXML / PowerPoint
_XML_ILLEGAL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]")


@registry.register(input_fmts=["pdf"], output_fmt="pptx")
@registry.register(input_fmts=["pdf"], output_fmt="ppt")
class PdfToPptxAdapter(BaseAdapter):
    """Converts PDF documents into Microsoft PowerPoint (.pptx) presentation slides."""

    @property
    def required_system_deps(self) -> list[str]:
        return []

    @property
    def engine_name(self) -> str:
        return "python-pptx + PyMuPDF"

    def convert(self, input_path: Path, output_path: Path, **options) -> ConversionResult:
        """Convert PDF to PowerPoint presentation (.pptx).

        Args:
            input_path: Source PDF path.
            output_path: Target PPTX path.
            **options:
                pages (str | None): Optional page range spec (e.g. "1-3,5").
                page (int | None): Optional single page number (1-based).
                mode (str | None): 'editable' (default) for native shapes & text,
                                   or 'visual' for 100% pixel-perfect slide images.
                dpi (int | None): DPI for raster image extraction/rendering (default: 150).

        Returns:
            ConversionResult with metadata.

        Raises:
            InvalidInputError: If the PDF cannot be opened or pages are invalid.
            ConversionFailedError: If the conversion process fails.
        """
        start = time.monotonic()

        if not input_path.exists():
            raise InvalidInputError(f"File not found: '{input_path}'")

        try:
            doc = fitz.open(str(input_path))
            total_pages = doc.page_count
            if total_pages == 0:
                doc.close()
                raise InvalidInputError(f"PDF '{input_path.name}' has no pages.")
        except Exception as exc:
            if isinstance(exc, InvalidInputError):
                raise
            raise InvalidInputError(f"Cannot open PDF '{input_path}': {exc}") from exc

        page_spec = options.get("pages")
        page_num = options.get("page")
        if page_num is not None:
            if not (1 <= page_num <= total_pages):
                doc.close()
                raise InvalidInputError(f"Page {page_num} out of range (1-{total_pages}).")
            page_indices = [page_num - 1]
        elif page_spec:
            page_indices = _parse_page_range(str(page_spec), total_pages)
            if not page_indices:
                doc.close()
                raise InvalidInputError(
                    f"No valid pages in range '{page_spec}' (total: {total_pages})."
                )
        else:
            page_indices = list(range(total_pages))

        mode = str(options.get("mode") or "editable").lower()
        dpi = int(options.get("dpi") or 150)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            prs = Presentation()
            first_page = doc[page_indices[0]]
            prs.slide_width = Pt(first_page.rect.width)
            prs.slide_height = Pt(first_page.rect.height)
            blank_layout = prs.slide_layouts[6]

            has_warned_scanned = False

            for idx in page_indices:
                page = doc[idx]
                slide = prs.slides.add_slide(blank_layout)

                # Coordinate scaling if page size differs from initial slide dimensions
                scale_x = prs.slide_width.pt / page.rect.width if page.rect.width > 0 else 1.0
                scale_y = prs.slide_height.pt / page.rect.height if page.rect.height > 0 else 1.0

                if mode == "visual":
                    pix = page.get_pixmap(dpi=dpi)
                    img_bytes = pix.tobytes("png")
                    slide.shapes.add_picture(
                        io.BytesIO(img_bytes),
                        0,
                        0,
                        width=prs.slide_width,
                        height=prs.slide_height,
                    )
                    continue

                # Editable mode
                page_text = page.get_text().strip()
                if not page_text:
                    # Page is empty, purely vector graphics, or scanned
                    if not has_warned_scanned:
                        console.print(
                            "[yellow]Note:[/yellow] PDF contains pages with no selectable text. "
                            "Rendering high-resolution visual slide for those pages."
                        )
                        has_warned_scanned = True
                    pix = page.get_pixmap(dpi=dpi)
                    slide.shapes.add_picture(
                        io.BytesIO(pix.tobytes("png")),
                        0,
                        0,
                        width=prs.slide_width,
                        height=prs.slide_height,
                    )
                    continue

                # 1. Place embedded raster images
                for img_info in page.get_images(full=True):
                    xref = img_info[0]
                    try:
                        rects = page.get_image_rects(xref)
                        if not rects:
                            continue
                        extracted = doc.extract_image(xref)
                        raw_bytes = extracted.get("image")
                        if not raw_bytes:
                            continue

                        ext = extracted.get("ext", "").lower()
                        if ext in ("png", "jpeg", "jpg", "bmp"):
                            img_stream = io.BytesIO(raw_bytes)
                        else:
                            pil_img = Image.open(io.BytesIO(raw_bytes))
                            if pil_img.mode in ("RGBA", "LA") or (
                                pil_img.mode == "P" and "transparency" in pil_img.info
                            ):
                                out_mode, out_fmt = "RGBA", "PNG"
                            else:
                                out_mode, out_fmt = "RGB", "JPEG"
                            buf = io.BytesIO()
                            pil_img.convert(out_mode).save(buf, format=out_fmt)
                            buf.seek(0)
                            img_stream = buf

                        for r in rects:
                            if r.width > 0 and r.height > 0:
                                slide.shapes.add_picture(
                                    img_stream,
                                    Pt(r.x0 * scale_x),
                                    Pt(r.y0 * scale_y),
                                    width=Pt(r.width * scale_x),
                                    height=Pt(r.height * scale_y),
                                )
                                img_stream.seek(0)
                    except Exception:
                        pass

                # 2. Place text blocks and spans
                blocks = page.get_text("dict").get("blocks", [])
                for b in blocks:
                    if b.get("type") == 0:  # text block
                        x0, y0, x1, y1 = b["bbox"]
                        w = max(1.0, (x1 - x0) * scale_x)
                        h = max(1.0, (y1 - y0) * scale_y)
                        tx_box = slide.shapes.add_textbox(
                            Pt(x0 * scale_x),
                            Pt(y0 * scale_y),
                            Pt(w),
                            Pt(h),
                        )
                        tf = tx_box.text_frame
                        tf.word_wrap = True
                        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

                        lines = b.get("lines", [])
                        for line_idx, line in enumerate(lines):
                            p = tf.paragraphs[0] if line_idx == 0 else tf.add_paragraph()
                            for span in line.get("spans", []):
                                raw_text = span.get("text", "")
                                text = _XML_ILLEGAL_CHARS_RE.sub("", raw_text)
                                if not text:
                                    continue
                                run = p.add_run()
                                run.text = text
                                size = span.get("size")
                                if size and size > 0:
                                    run.font.size = Pt(size * scale_y)
                                color_int = span.get("color")
                                if color_int is not None:
                                    r = (color_int >> 16) & 255
                                    g = (color_int >> 8) & 255
                                    b = color_int & 255
                                    run.font.color.rgb = RGBColor(r, g, b)
                                font_name = span.get("font", "")
                                if font_name:
                                    if "+" in font_name:
                                        font_name = font_name.split("+", 1)[1]
                                    run.font.name = font_name
                                flags = span.get("flags", 0)
                                if (flags & 16) or "bold" in font_name.lower():
                                    run.font.bold = True
                                if (
                                    (flags & 2)
                                    or "italic" in font_name.lower()
                                    or "oblique" in font_name.lower()
                                ):
                                    run.font.italic = True

            prs.save(str(output_path))
        except Exception as exc:
            if isinstance(exc, (InvalidInputError, ConversionFailedError)):
                raise
            raise ConversionFailedError(f"Failed to convert PDF to PPTX: {exc}") from exc
        finally:
            doc.close()

        return self._make_result(input_path, output_path, start)
