import click
import os
import importlib.metadata
import logging
from rich.console import Console
from rich.table import Table
from rich.logging import RichHandler
from vision_lint.core.auditor import IntegrityLinter

# Configure nice logging output
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, markup=True)]
)
logger = logging.getLogger("vision_lint")
console = Console()

def get_version():
    try:
        return importlib.metadata.version('vision_lint')
    except importlib.metadata.PackageNotFoundError:
        return '0.1.0-dev' # Fallback for local dev without install

@click.group(invoke_without_command=True)
@click.option('--version', is_flag=True, help="Show the version and exit.")
@click.pass_context
def cli(ctx, version):
    """VisionLint: Automated Quality Assurance for Computer Vision Datasets."""
    if version:
        click.echo(f"VisionLint v{get_version()}")
        ctx.exit()
    elif ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())

@cli.command()
@click.argument('path', type=click.Path(exists=True))
@click.option('--verbose', '-v', is_flag=True, help="Enable verbose logging.")
def audit(path, verbose):
    """
    Audit a dataset for integrity issues.
    """
    if verbose:
        logger.setLevel(logging.DEBUG)
        
    console.print(f"[bold blue]Starting audit for path:[/bold blue] {path}")
    
    linter = IntegrityLinter()
    # IntegrityLinter internally logs skipped files at DEBUG level
    results = linter.check(path)

    if not results:
        console.print("[bold green]No integrity issues found! Dataset is clean.[/bold green]")
        return

    table = Table(title="Dataset Integrity Issues", show_lines=True)
    table.add_column("File Path (Relative)", style="cyan", no_wrap=True)
    table.add_column("Linter", style="green", no_wrap=True)
    table.add_column("Issue Type", style="magenta", no_wrap=True)
    table.add_column("Severity", style="red", no_wrap=True)
    table.add_column("Description", style="white", overflow="fold")

    # Use absolute path for relpath calculation base
    base_path = os.path.abspath(path)

    for result in results:
        # Calculate relative path for cleaner output
        try:
            display_path = os.path.relpath(result.file_path, base_path)
            # If path is outside base (e.g. symlink), fallback to absolute
            if display_path.startswith(".."): 
                display_path = result.file_path
        except ValueError:
            display_path = result.file_path
            
        table.add_row(
            display_path, 
            result.linter_name, 
            result.issue_type, 
            result.severity, 
            result.message
        )

    console.print(table)
    console.print(f"\n[bold red]Found {len(results)} issues.[/bold red]")

if __name__ == '__main__':
    cli()
