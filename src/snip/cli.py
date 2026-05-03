import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pyperclip
import typer
from pygments.lexers import guess_lexer
from pygments.util import ClassNotFound
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.syntax import Syntax
from rich.table import Table

from . import __version__
from .ai import (
    AIError,
    AIUnavailable,
    annotate,
    list_providers,
    select_provider,
    test_connection,
)
from .db import Database
from .models import Snippet


app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Local code snippet manager with AI tagging.",
)
console = Console()
err = Console(stderr=True)


def _db() -> Database:
    return Database()


def _detect_language(code: str) -> str:
    try:
        lexer = guess_lexer(code)
        if lexer.aliases:
            return lexer.aliases[0]
        return lexer.name.lower()
    except ClassNotFound:
        return "text"
    except Exception:
        return "text"


def _read_pasted_code() -> str:
    eof_hint = "Ctrl-Z then Enter" if os.name == "nt" else "Ctrl-D"
    console.print(f"[dim]Paste code, then press {eof_hint} to finish:[/dim]")
    data = sys.stdin.read()
    return data.rstrip("\n")


def _print_snippet(s: Snippet, show_code: bool = True) -> None:
    when = s.created_at.strftime("%Y-%m-%d %H:%M")
    header = f"[bold]#{s.id}[/bold]  [cyan]{s.language or 'text'}[/cyan]  [dim]{when}[/dim]"
    if s.description:
        header += f"\n{s.description}"
    if s.tags:
        header += "\n[yellow]" + " ".join("#" + t for t in s.tags) + "[/yellow]"
    console.print(Panel(header, expand=False))
    if show_code:
        try:
            syntax = Syntax(s.code, s.language or "text", theme="monokai", line_numbers=True)
        except Exception:
            syntax = Syntax(s.code, "text", theme="monokai", line_numbers=True)
        console.print(syntax)


def _resolve(snippet_id: int) -> Snippet:
    s = _db().get(snippet_id)
    if not s:
        err.print(f"[red]No snippet with id {snippet_id}.[/red]")
        raise typer.Exit(1)
    return s


@app.command()
def add(
    provider: str = typer.Option(None, "--provider", "-p", help="Override AI provider"),
    no_ai: bool = typer.Option(False, "--no-ai", help="Skip AI tagging"),
):
    """Save a new snippet pasted from stdin."""
    code = _read_pasted_code()
    if not code.strip():
        err.print("[yellow]No code provided, aborting.[/yellow]")
        raise typer.Exit(1)

    language = _detect_language(code)
    description = ""
    tags: list[str] = []

    if not no_ai:
        try:
            info = select_provider(provider)
            with console.status(f"[dim]Tagging via {info.name}…[/dim]"):
                tags, description = annotate(code, language, info)
        except AIUnavailable:
            console.print("[dim]No AI provider available — saving without tags.[/dim]")
        except AIError as e:
            console.print(f"[yellow]AI tagging failed: {e}. Saving without tags.[/yellow]")

    snippet_id = _db().add(code, language, description, tags)
    console.print(f"[green]Saved snippet #{snippet_id}[/green] [dim]({language})[/dim]")
    if tags:
        console.print("[yellow]" + " ".join("#" + t for t in tags) + "[/yellow]")


@app.command("list")
def list_cmd():
    """List all snippets."""
    snippets = _db().all()
    if not snippets:
        console.print("[dim]No snippets yet. Use `snip add` to create one.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("ID", justify="right", style="cyan")
    table.add_column("Language")
    table.add_column("Description")
    table.add_column("Tags", style="yellow")
    table.add_column("Created", style="dim")

    for s in snippets:
        table.add_row(
            str(s.id),
            s.language or "-",
            (s.description or "")[:60],
            " ".join("#" + t for t in s.tags),
            s.created_at.strftime("%Y-%m-%d"),
        )
    console.print(table)


@app.command()
def search(query: str = typer.Argument(..., help="Words to search for")):
    """Search across descriptions, tags, code, and language."""
    results = _db().search(query)
    if not results:
        console.print(f"[dim]No snippets match: {query}[/dim]")
        return
    console.print(f"[dim]{len(results)} match(es):[/dim]\n")
    for s in results:
        _print_snippet(s, show_code=False)


@app.command()
def show(snippet_id: int = typer.Argument(..., help="Snippet ID")):
    """Show a single snippet with syntax highlighting."""
    _print_snippet(_resolve(snippet_id))


@app.command()
def copy(snippet_id: int = typer.Argument(..., help="Snippet ID")):
    """Copy a snippet to the clipboard."""
    s = _resolve(snippet_id)
    try:
        pyperclip.copy(s.code)
    except pyperclip.PyperclipException as e:
        err.print(f"[red]Could not access clipboard: {e}[/red]")
        raise typer.Exit(1)
    console.print(f"[green]Copied snippet #{s.id} to clipboard.[/green]")


@app.command()
def delete(
    snippet_id: int = typer.Argument(..., help="Snippet ID"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Delete a snippet."""
    s = _resolve(snippet_id)
    if not yes and not Confirm.ask(f"Delete snippet #{s.id}?", default=False):
        console.print("[dim]Cancelled.[/dim]")
        return
    _db().delete(s.id)
    console.print(f"[green]Deleted snippet #{s.id}.[/green]")


@app.command()
def edit(snippet_id: int = typer.Argument(..., help="Snippet ID")):
    """Open a snippet in $EDITOR."""
    db = _db()
    s = _resolve(snippet_id)

    editor = os.environ.get("EDITOR") or ("notepad" if os.name == "nt" else "nano")
    suffix = f".{s.language}" if s.language and s.language.replace("+", "").isalnum() else ".txt"

    with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as f:
        f.write(s.code)
        tmp = Path(f.name)

    try:
        # shell=False is the default; passing as a list keeps it that way.
        subprocess.run([editor, str(tmp)], check=False)
        new_code = tmp.read_text(encoding="utf-8")
    except FileNotFoundError:
        err.print(f"[red]Editor not found: {editor}[/red]")
        raise typer.Exit(1)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass

    if new_code == s.code:
        console.print("[dim]No changes.[/dim]")
        return
    db.update_code(s.id, new_code)
    console.print(f"[green]Updated snippet #{s.id}.[/green]")


@app.command()
def config():
    """Show AI provider status, dependencies, and database info."""
    db = _db()

    info_table = Table(show_header=False, box=None)
    info_table.add_row("[bold]snip[/bold]", __version__)
    info_table.add_row("Database", str(db.path))
    info_table.add_row("Snippets", str(db.count()))
    info_table.add_row("Size", f"{db.size_bytes()} bytes")
    console.print(info_table)
    console.print()

    providers_table = Table(title="AI providers", show_header=True, header_style="bold")
    providers_table.add_column("Provider")
    providers_table.add_column("Env var")
    providers_table.add_column("Key set")
    providers_table.add_column("Package")
    providers_table.add_column("Model")

    for name, env, model in list_providers():
        if env:
            key_set = "[green]yes[/green]" if os.environ.get(env) else "no"
        else:
            key_set = "[dim]n/a[/dim]"
        providers_table.add_row(name, env or "-", key_set, _package_status(name), model)

    console.print(providers_table)
    console.print()

    try:
        active = select_provider()
    except AIUnavailable:
        console.print(
            "Active provider: [yellow]none[/yellow] "
            "[dim](no key set and Ollama not running on localhost:11434)[/dim]"
        )
        return

    console.print(f"Active provider: [green]{active.name}[/green] [dim]({active.reason})[/dim]")
    with console.status("[dim]Testing connection…[/dim]"):
        ok, msg = test_connection(active)
    if ok:
        console.print("Connection: [green]ok[/green]")
    else:
        console.print(f"Connection: [red]failed[/red] [dim]({msg})[/dim]")


def _package_status(provider: str) -> str:
    pkg = {
        "anthropic": "anthropic",
        "openai": "openai",
        "google": "google.generativeai",
        "ollama": None,
    }.get(provider)
    if pkg is None:
        return "[dim]built-in[/dim]"
    try:
        __import__(pkg)
        return "[green]installed[/green]"
    except ImportError:
        return "missing"


if __name__ == "__main__":
    app()
