"""pdf-tool CLI — config command."""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from pdf_tool.utils.config import get_config

console = Console()
app = typer.Typer(
    help="Manage user configuration (~/.pdf-tool/config.toml).",
    invoke_without_command=True,
)


@app.callback()
def main(ctx: typer.Context) -> None:
    """Config manager. Run without subcommand to show current configuration."""
    if ctx.invoked_subcommand is None:
        show()


@app.command("show")
def show() -> None:
    """Display the active configuration table."""
    config = get_config()
    table = Table(
        title="⚙️  Active Configuration",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Section", style="bold green")
    table.add_column("Key", style="bold")
    table.add_column("Value")
    table.add_column("Default")

    all_conf = config.all()
    for section, values in sorted(all_conf.items()):
        if isinstance(values, dict):
            for k, val in sorted(values.items()):
                full_key = f"{section}.{k}"
                default_val = config.get_default(full_key)
                val_str = str(val) if val != "" else "[dim](empty)[/dim]"
                def_str = str(default_val) if default_val != "" else "[dim](empty)[/dim]"
                is_custom = val != default_val
                status_val = f"[yellow]{val_str}[/yellow]" if is_custom else str(val_str)
                table.add_row(section, k, status_val, str(def_str))
        else:
            default_val = config.get_default(section)
            table.add_row("", section, str(values), str(default_val))

    console.print(table)
    console.print(f"[dim]Config file: {config.config_file}[/dim]\n")


@app.command("get")
def get_key(
    key: Annotated[
        str, typer.Argument(help="Configuration key in dot notation (e.g. 'defaults.image_dpi').")
    ],
) -> None:
    """Get the current value for a configuration key."""
    config = get_config()
    val = config.get(key)
    if val is None and config.get_default(key) is None:
        console.print(f"[red]Error:[/red] Key '{key}' not found in configuration.")
        raise typer.Exit(1)
    console.print(f"{key} = [bold cyan]{val}[/bold cyan]")


@app.command("set")
def set_key(
    key: Annotated[
        str, typer.Argument(help="Configuration key in dot notation (e.g. 'defaults.image_dpi').")
    ],
    value: Annotated[str, typer.Argument(help="New value to set.")],
) -> None:
    """Set a configuration key and persist to ~/.pdf-tool/config.toml."""
    config = get_config()
    config.set(key, value)
    config.save()
    updated_val = config.get(key)
    console.print(f"[green]✅ Updated:[/green] {key} = [bold cyan]{updated_val}[/bold cyan]")


@app.command("reset")
def reset_config(
    key: Annotated[
        str | None,
        typer.Option(
            "--key", "-k", help="Specific key to reset. Omit to reset all settings to defaults."
        ),
    ] = None,
) -> None:
    """Reset configuration (or a specific key) to default settings."""
    config = get_config()
    config.reset(key)
    config.save()
    if key:
        default_val = config.get(key)
        console.print(f"[green]✅ Reset key:[/green] {key} → [bold cyan]{default_val}[/bold cyan]")
    else:
        console.print("[green]✅ Configuration reset to factory defaults.[/green]")


@app.command("path")
def print_path() -> None:
    """Print the path to the configuration file."""
    config = get_config()
    console.print(str(config.config_file))
