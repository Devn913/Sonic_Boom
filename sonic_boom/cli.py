import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from .discovery import scan_speakers, register_master_service, Zeroconf
from .streamer import AudioMaster, AudioSlave, MULTICAST_GROUP, PORT

console = Console()

@click.group()
def main():
    """Sonic Boom: Discover and monitor speaker group sync status."""
    pass

@main.command()
@click.option('--group', default='SonicBoomGroup', help='Group name to broadcast.')
@click.option('--name', default='MasterNode', help='Display name of the master.')
def master(group: str, name: str):
    """Start as an audio broadcaster (Master)."""
    mode = click.prompt(
        "Choose broadcast mode",
        type=click.Choice(['mic', 'system'], case_sensitive=False),
        default='mic'
    )

    device_index = None
    capture_mode = "pyaudio"

    if mode == 'mic':
        try:
            devices = AudioMaster.list_devices()
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] Failed to initialize audio system: {e}")
            console.print("[yellow]Tip:[/yellow] Make sure PyAudio is properly installed and audio drivers are working.")
            return

        if not devices:
            console.print("[bold red]Error:[/bold red] No audio input devices found.")
            console.print("[yellow]Tip:[/yellow] Please connect a microphone or audio input device.")
            return

        table = Table(title="Available Audio Input Devices")
        table.add_column("Index", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Channels", style="green")

        for d in devices:
            table.add_row(str(d['index']), d['name'], str(d['channels']))

        console.print(table)
        device_index = click.prompt("Select device index", type=int, default=devices[0]['index'])

        # Validate device index
        valid_indices = [d['index'] for d in devices]
        if device_index not in valid_indices:
            console.print(f"[bold red]Error:[/bold red] Invalid device index {device_index}.")
            console.print(f"[yellow]Valid indices:[/yellow] {', '.join(map(str, valid_indices))}")
            return
    else:
        capture_mode = "system"
        console.print("[yellow]System audio mode requires Screen Recording permissions.[/yellow]")
        console.print("[yellow]On macOS: System Settings → Privacy & Security → Screen Recording[/yellow]")

    console.print(f"\n[cyan]Configuration:[/cyan]")
    console.print(f"  Group: {group}")
    console.print(f"  Multicast: {MULTICAST_GROUP}:{PORT}")
    console.print(f"  Mode: {mode}")

    try:
        zc = Zeroconf()
        register_master_service(zc, name, 10000, group)

        master_node = AudioMaster(group, device_index=device_index, capture_mode=capture_mode)
        master_node.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping master...[/yellow]")
    except OSError as e:
        console.print(f"[bold red]Network Error:[/bold red] {e}")
        console.print("[yellow]Tip:[/yellow] Check firewall settings or network connectivity.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print("[yellow]Tip:[/yellow] If using system audio, ensure Screen Recording permissions are granted.")
    finally:
        try:
            zc.close()
        except:
            pass

@main.command()
@click.option('--timeout', default=5, help='Scanning timeout in seconds.')
def slave(timeout: int):
    """Scan for masters and start as an audio receiver (Slave)."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Scanning for Sonic Boom Masters...", total=None)
            speakers = scan_speakers(timeout)
    except Exception as e:
        console.print(f"[bold red]Discovery Error:[/bold red] {e}")
        console.print("[yellow]Tip:[/yellow] Check network connectivity and firewall settings.")
        return

    masters = [s for s in speakers if s.get('service_type') == 'sonic-boom-master']

    multicast_group = MULTICAST_GROUP  # Default
    port = PORT  # Default

    if masters:
        table = Table(title="Available Sonic Boom Masters")
        table.add_column("Index", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Group", style="green")
        table.add_column("Address", style="yellow")

        for i, m in enumerate(masters):
            table.add_row(str(i), m['name'], m['group_id'], f"{m['address']}:{m['port']}")

        console.print(table)

        choice = click.prompt(
            "Select master index to connect to (or 'm' for manual)",
            default='0'
        )

        if choice != 'm':
            try:
                selected_master = masters[int(choice)]
                console.print(f"[green]Connecting to {selected_master['name']}...[/green]")
            except (ValueError, IndexError):
                console.print("[red]Invalid selection, using defaults.[/red]")
    else:
        console.print("[yellow]No Sonic Boom Masters found. Proceeding with default multicast group.[/yellow]")

    console.print(f"\n[cyan]Configuration:[/cyan]")
    console.print(f"  Multicast: {multicast_group}:{port}")

    try:
        slave_node = AudioSlave(multicast_group=multicast_group, port=port)
        slave_node.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping slave...[/yellow]")
    except OSError as e:
        console.print(f"[bold red]Network Error:[/bold red] {e}")
        console.print("[yellow]Tip:[/yellow] Multicast may not be supported on this network. Check router/firewall settings.")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        console.print("[yellow]Tip:[/yellow] Make sure PyAudio is installed and audio output devices are available.")

@main.command()
@click.option('--timeout', default=5, help='Scanning timeout in seconds.')
def scan(timeout: int):
    """Scan for local network speaker broadcasters."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Scanning for speakers...", total=None)
            speakers = scan_speakers(timeout)
    except Exception as e:
        console.print(f"[bold red]Discovery Error:[/bold red] {e}")
        console.print("[yellow]Tip:[/yellow] Check network connectivity and ensure mDNS/Zeroconf is available.")
        return

    if not speakers:
        console.print("[yellow]No speaker broadcasters found.[/yellow]")
        console.print("[yellow]Tip:[/yellow] Make sure devices are on the same network and mDNS/Bonjour is enabled.")
        return

    # Filter out duplicates (often mDNS returns multiple for the same device)
    unique_speakers = {}
    for s in speakers:
        unique_speakers[s['name']] = s
    speakers = list(unique_speakers.values())

    # Create table
    table = Table(title="Discovered Speaker Broadcasters")
    table.add_column("Name", style="cyan")
    table.add_column("Address", style="magenta")
    table.add_column("Group ID", style="green")
    table.add_column("Status", style="yellow")

    # Group speakers by ID
    groups = {}
    for s in speakers:
        gid = s['group_id']
        if gid not in groups:
            groups[gid] = []
        groups[gid].append(s)

    for gid, members in groups.items():
        is_synced = len(members) > 1 and gid != "None"
        status = "[bold green]Synced[/bold green]" if is_synced else "[bold red]Not Synced[/bold red]"
        
        for i, speaker in enumerate(members):
            table.add_row(
                speaker['name'],
                speaker['address'],
                gid,
                status if i == 0 else "" # Only show status for the group
            )

    console.print()
    if any(len(m) > 1 and g != "None" for g, m in groups.items()):
        console.print("[bold green]Success:[/bold green] Some speakers are currently in sync groups.")
    else:
        console.print("[bold yellow]Note:[/bold yellow] No active sync groups detected.")

if __name__ == "__main__":
    main()
