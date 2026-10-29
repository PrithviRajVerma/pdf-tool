"""LibreOffice headless subprocess handler for document conversions."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from pdf_tool.exceptions import ConversionFailedError, MissingDependencyError
from pdf_tool.utils.dependency_checker import _INSTALL_HINTS


def find_libreoffice_binary() -> str | None:
    """Find the LibreOffice executable in system PATH.

    Checks ``soffice`` first, then ``libreoffice``.

    Returns:
        Path to the binary as string, or ``None`` if not found.
    """
    for binary in ("soffice", "libreoffice"):
        path = shutil.which(binary)
        if path:
            return path
    return None


def run_libreoffice_convert(
    input_path: Path,
    output_path: Path,
    timeout: float = 60.0,
) -> Path:
    """Convert an office document to PDF using headless LibreOffice.

    Uses an isolated user installation profile (``-env:UserInstallation``)
    to prevent lock conflicts with concurrently running instances.

    Args:
        input_path: Path to the input document (DOCX, PPTX, XLSX, etc.).
        output_path: Path where the converted PDF will be saved.
        timeout: Maximum duration in seconds to wait for conversion.

    Returns:
        The ``output_path`` of the created PDF.

    Raises:
        MissingDependencyError: If neither ``soffice`` nor ``libreoffice`` is installed.
        ConversionFailedError: If LibreOffice returns a non-zero exit code or fails to generate the PDF.
    """
    lo_bin = find_libreoffice_binary()
    if not lo_bin:
        hints = _INSTALL_HINTS.get("soffice", {})
        raise MissingDependencyError(dep_name="soffice", install_hints=hints)

    if not input_path.exists():
        raise ConversionFailedError(f"Input file not found: '{input_path}'")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with (
        tempfile.TemporaryDirectory(prefix="pdf_tool_lo_profile_") as profile_dir,
        tempfile.TemporaryDirectory(prefix="pdf_tool_lo_out_") as out_dir,
    ):
        profile_uri = Path(profile_dir).as_uri()
        cmd = [
            lo_bin,
            "--headless",
            "--invisible",
            "--nologo",
            "--nodefault",
            f"-env:UserInstallation={profile_uri}",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(input_path.resolve()),
        ]

        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ConversionFailedError(
                f"LibreOffice conversion timed out after {timeout} seconds for '{input_path.name}'."
            ) from exc
        except Exception as exc:
            raise ConversionFailedError(f"Failed to execute LibreOffice subprocess: {exc}") from exc

        if process.returncode != 0:
            stderr = process.stderr.strip()
            stdout = process.stdout.strip()
            err_msg = stderr or stdout or f"Exit code {process.returncode}"
            raise ConversionFailedError(
                f"LibreOffice conversion failed for '{input_path.name}': {err_msg}"
            )

        # Expected output file in out_dir has the same stem as input_path with .pdf suffix
        generated_pdf = Path(out_dir) / f"{input_path.stem}.pdf"
        if not generated_pdf.exists():
            # If stem matching failed, look for any .pdf generated in out_dir
            pdf_candidates = list(Path(out_dir).glob("*.pdf"))
            if pdf_candidates:
                generated_pdf = pdf_candidates[0]
            else:
                raise ConversionFailedError(
                    f"LibreOffice completed without errors, but no PDF was generated for '{input_path.name}'."
                )

        shutil.move(str(generated_pdf), str(output_path))

    return output_path
