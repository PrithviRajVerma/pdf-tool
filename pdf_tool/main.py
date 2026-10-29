"""pdf — universal document conversion and PDF manipulation CLI."""

from __future__ import annotations

import typer
import typer.core

from pdf_tool.cli.compress import compress
from pdf_tool.cli.config import app as config_app
from pdf_tool.cli.convert import convert
from pdf_tool.cli.doctor import doctor
from pdf_tool.cli.merge import merge
from pdf_tool.cli.ocr import ocr
from pdf_tool.cli.split import split


class DefaultGroup(typer.core.TyperGroup):
    """Custom Typer group that automatically routes direct file arguments to 'convert'."""

    def resolve_command(self, ctx, args):
        if not args:
            return super().resolve_command(ctx, args)
        cmd_name = args[0]
        # Let root options like --help or --install-completion pass through
        if cmd_name.startswith("-"):
            return super().resolve_command(ctx, args)
        cmd = self.get_command(ctx, cmd_name)
        if cmd is None:
            # If not a registered command or alias, default to 'convert'
            cmd = self.get_command(ctx, "convert")
            return "convert", cmd, args
        return super().resolve_command(ctx, args)


app = typer.Typer(
    cls=DefaultGroup,
    name="pdf",
    help="Universal document conversion CLI.\n\n"
    "Direct usage (no subcommand needed):\n"
    "  pdf photo.jpg               → Convert to photo.pdf\n"
    "  pdf photo.jpg doc.pdf       → Convert photo.jpg to doc.pdf\n"
    "  pdf img1.jpg img2.png o.pdf → Merge images into o.pdf\n"
    "  pdf doc.pdf page.png        → Convert doc.pdf to page images",
    add_completion=True,
)

# Primary commands
app.command("convert", help="Convert files between formats (default action).")(convert)
app.command("merge", help="Merge multiple PDFs into one.")(merge)
app.command("split", help="Split a PDF by page range or chunk size.")(split)
app.command("compress", help="Compress a PDF to reduce its file size.")(compress)
app.command("ocr", help="Run OCR to make a scanned PDF searchable.")(ocr)
app.command("doctor", help="Check system dependencies and diagnostics.")(doctor)
app.add_typer(config_app, name="config", help="Manage user configuration.")

# 1-letter / short aliases
app.command("c", hidden=True)(convert)
app.command("m", hidden=True)(merge)
app.command("s", hidden=True)(split)
app.command("z", hidden=True)(compress)
app.command("o", hidden=True)(ocr)
app.command("doc", hidden=True)(doctor)
app.add_typer(config_app, name="cfg", hidden=True)


if __name__ == "__main__":
    app()
