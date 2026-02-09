import click
import os
from rich.console import Console
from rich.table import Table
from vision_lint.core.auditor import IntegrityAuditor

console = Console()

@click.group()
def cli():
    """VisionLint: Automated Quality Assurance for Computer Vision Datasets."""
    pass

@cli.command()
@click.argument('path', type=click.Path(exists=True))
def audit(path):
    """
    Audit a dataset for integrity issues.
    """
    console.print(f"[bold blue]Starting audit for path:[/bold blue] {path}")
    
    auditor = IntegrityAuditor()
    issues = auditor.audit_dataset(path)

    if not issues:
        console.print("[bold green]No integrity issues found! Dataset is clean.[/bold green]")
        return

    table = Table(title="Dataset Integrity Issues")
    table.add_column("File Path", style="cyan", no_wrap=True)
    table.add_column("Issue Type", style="magenta")
    table.add_column("Description", style="white")

    for issue in issues:
        table.add_row(issue.file_path, issue.issue_type, issue.description)

    console.print(table)
    console.print(f"\n[bold red]Found {len(issues)} issues.[/bold red]")

if __name__ == '__main__':
    cli()
