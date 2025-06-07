import json
import os
import time
from pathlib import Path
from typing import Optional

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text

console = Console()


def translate_directory_guild_files_to_single(
        directory_path: Path,
        output_file_path: Path
) -> None:
    """
    Translates all guild configuration files in a directory into a single JSON file.
    
    Args:
        directory_path (str): Path to the directory containing guild config files.
        output_file_path (str): Path to the output JSON file.
    """
    combined_data = {}
    json_files = [f for f in os.listdir(str(directory_path)) if f.endswith(".json")]

    if not json_files:
        console.print(Panel(
            "[red]No JSON files found in the selected directory![/red]",
            title="[red]Error[/red]",
            border_style="red"
        ))
        return

    with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=console,
            transient=False
    ) as progress:

        task = progress.add_task("Processing files...", total=len(json_files))

        for filename in json_files:
            progress.update(task, description=f"Processing {filename}")
            file_path = os.path.join(directory_path, filename)

            with open(file_path, 'r') as file:
                try:
                    data = json.load(file)

                    # Use filename (without extension) as guild ID key for all data types
                    guild_id = Path(filename).stem
                    combined_data[guild_id] = data

                except json.JSONDecodeError as e:
                    console.print(Panel(
                        f"[red]Error decoding JSON from {file_path}:\n{e}[/red]",
                        title="[red]JSON Error[/red]",
                        border_style="red"
                    ))

            progress.advance(task)
            time.sleep(0.1)  # Small delay to show progress

    # Write output file with progress
    with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
    ) as progress:
        task = progress.add_task("Writing output file...", total=None)

        with open(output_file_path, 'w') as output_file:
            json.dump(combined_data, output_file, indent=4)

        progress.update(task, description="File written successfully!")
        time.sleep(0.5)

    console.print(Panel(
        f"[green]✓ Successfully combined {len(json_files)} files\n"
        f"📁 Output saved to: [bold]{output_file_path}[/bold]\n"
        f"📊 Total entries: {len(combined_data)}[/green]",
        title="[green]Success[/green]",
        border_style="green"
    ))


def select_file(parent_path: Path) -> Optional[Path]:
    while True:
        # Create a table for file listing
        table = Table(title=f"📁 Contents of {parent_path.name}", show_header=True, header_style="bold blue")
        table.add_column("Index", style="cyan", width=6)
        table.add_column("Type", style="magenta", width=8)
        table.add_column("Name", style="green")
        table.add_column("Size", style="yellow", width=10)

        items = list(parent_path.iterdir())
        for i, child in enumerate(items):
            file_type = "📁 DIR" if child.is_dir() else "📄 FILE"
            size = ""
            if child.is_file():
                try:
                    size = f"{child.stat().st_size:,} B"
                except:
                    size = "N/A"

            table.add_row(str(i), file_type, child.name, size)

        table.add_row("*", "🔄 ACTION", "Select whole directory to translate", "")

        console.print(Panel(table, border_style="blue"))

        try:
            selection = Prompt.ask(
                "[yellow]Select a directory to open, or file to translate[/yellow]",
                default="*"
            )

            if selection == "*":
                return parent_path

            selection = int(selection)

            if selection < 0 or selection >= len(items):
                raise ValueError("Selection out of range.")
            else:
                break
        except ValueError:
            if not Confirm.ask("[red]Invalid selection.[/red] Would you like to try again?"):
                return None
            continue

    selected_item = items[selection]

    if selected_item.is_dir():
        console.print(Panel(
            f"[blue]Entering directory: [bold]{selected_item.name}[/bold][/blue]",
            border_style="blue"
        ))
        return select_file(selected_item)
    else:
        console.print(Panel(
            f"[green]Selected file: [bold]{selected_item.name}[/bold][/green]",
            border_style="green"
        ))
        return selected_item


def display_welcome():
    welcome_content = Text()
    welcome_content.append("Guild Configuration File Translator", style="bold cyan")
    welcome_content.append("\n\n")
    welcome_content.append(
        "This tool combines multiple JSON guild config files into a single file.\n"
        "Perfect for consolidating distributed configuration data!",
        style="white"
    )

    console.print(Panel(
        Align.center(welcome_content),
        title="[bold cyan]🛠️  Welcome[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    ))


def display_file_contents(file_path: Path):
    try:
        content = file_path.read_text()

        # Try to parse as JSON for pretty display
        try:
            json_data = json.loads(content)
            pretty_content = json.dumps(json_data, indent=2)
        except:
            pretty_content = content

        # Truncate if too long
        if len(pretty_content) > 2000:
            pretty_content = pretty_content[:2000] + "\n... (truncated)"

        console.print(Panel(
            pretty_content,
            title=f"[bold green]📄 {file_path.name}[/bold green]",
            border_style="green",
            expand=False
        ))

    except Exception as e:
        console.print(Panel(
            f"[red]Error reading output file: {e}[/red]",
            title="[red]File Error[/red]",
            border_style="red"
        ))


if __name__ == "__main__":
    display_welcome()

    while True:
        data_directory_input = Prompt.ask(
            "[cyan]Enter data directory path[/cyan]",
            default="exit"
        )

        if data_directory_input.lower() == "exit":
            console.print(Panel(
                "[yellow]👋 Thanks for using the Guild Config Translator![/yellow]",
                title="[yellow]Goodbye[/yellow]",
                border_style="yellow"
            ))
            break

        data_directory = Path(data_directory_input)

        if not data_directory.exists():
            console.print(Panel(
                f"[red]Directory '{data_directory}' does not exist. Please try again.[/red]",
                title="[red]Directory Not Found[/red]",
                border_style="red"
            ))
            continue

        path = select_file(data_directory)
        if path is None:
            console.print(Panel(
                "[yellow]Operation cancelled by user.[/yellow]",
                title="[yellow]Cancelled[/yellow]",
                border_style="yellow"
            ))
            break

        output_path_input = Prompt.ask(
            "[cyan]Enter output file path[/cyan]",
            default="combined_guild_config.json"
        )

        if not output_path_input:
            console.print(Panel(
                "[red]No output path provided. Operation cancelled.[/red]",
                title="[red]Missing Output Path[/red]",
                border_style="red"
            ))
            break

        output_path = Path(output_path_input)

        # Confirm before processing
        if not Confirm.ask(f"[yellow]Process files in '{path}' and save to '{output_path}'?[/yellow]"):
            console.print("[yellow]Operation cancelled.[/yellow]")
            continue

        translate_directory_guild_files_to_single(path, output_path)

        if output_path.exists():
            if Confirm.ask("[cyan]Would you like to view the output file contents?[/cyan]"):
                display_file_contents(output_path)

        if not Confirm.ask("[cyan]Would you like to process another directory?[/cyan]"):
            console.print(Panel(
                "[green]✨ All done! Have a great day![/green]",
                title="[green]Complete[/green]",
                border_style="green"
            ))
            break
