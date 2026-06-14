import sys
import os
import subprocess

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align
    from rich.text import Text
    from rich import box
    from rich.table import Table
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
    from rich.console import Console
    from rich.panel import Panel
    from rich.align import Align
    from rich.text import Text
    from rich import box
    from rich.table import Table

try:
    import pyfiglet
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyfiglet"])
    import pyfiglet

console = Console()

COLOR_BORDER = "#D4C4A8"
COLOR_TITLE = "#C4A96A"
COLOR_ACCENT = "#A68A56"
COLOR_TEXT = "#F5EBD9"
COLOR_DIM = "#8B7A5B"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    clear_screen()

    banner = pyfiglet.figlet_format("OFFLINE", font="standard")
    console.print(Align.center(Text(banner, style=f"bold {COLOR_TITLE}")))
    console.print(Align.center(Text("══════════════════════════════════════════", style=COLOR_BORDER)))
    console.print(Align.center(Text("◆ Δ LOADER STATUS Δ ◆", style=f"bold {COLOR_ACCENT}")))
    console.print(Align.center(Text("──────────────────────────────────────────", style=COLOR_DIM)))
    console.print()

    steps_lines = [
        Text("◆ LOADER IS OFFLINE ◆", style=f"bold {COLOR_TITLE}"),
        Text(""),
        Text("The CODM loader is currently unavailable.", style=f"italic {COLOR_TEXT}"),
        Text("Please wait for RIEL to bring it back online.", style=f"italic {COLOR_TEXT}"),
        Text(""),
        Text("   ▸ No estimated time of return", style=COLOR_ACCENT),
        Text("   ▸ This is a temporary shutdown", style=COLOR_ACCENT),
        Text("   ▸ All other loaders remain operational", style=COLOR_ACCENT),
        Text("   ▸ Your data and credentials are safe", style=COLOR_ACCENT),
        Text("   ▸ Check back later or contact support", style=COLOR_ACCENT),
        Text(""),
        Text("◈ Instructions:", style=f"bold {COLOR_TITLE}"),
        Text("   • Do not spam the loader", style=COLOR_TEXT),
        Text("   • Wait for an announcement from RIEL", style=COLOR_TEXT),
        Text("   • Use other tools from the main menu", style=COLOR_TEXT),
        Text("   • Join the Telegram channel for updates", style=COLOR_TEXT),
        Text(""),
        Text("⌛ No ETA – RIEL will notify when online.", style=f"italic {COLOR_DIM}")
    ]

    combined_top = Text("\n").join(steps_lines)

    panel_top = Panel(
        Align.center(combined_top, vertical="middle"),
        title=Text(" LOADER STATUS ", style=f"bold {COLOR_TITLE}"),
        border_style=COLOR_BORDER,
        box=box.HEAVY,
        width=80,
        padding=(2, 4)
    )
    console.print(Align.center(panel_top))
    console.print()

    maintenance_lines = [
        Text("◆ Δ WAIT FOR RIEL Δ ◆", style=f"bold {COLOR_ACCENT}"),
        Text(""),
        Text("Δ CODM LOADER IS CURRENTLY OFFLINE Δ", style=f"bold {COLOR_TITLE}"),
        Text(""),
        Text("• Reason:", style=COLOR_ACCENT) + Text(" Temporary shutdown by RIEL", style=COLOR_TEXT),
        Text("• Status:", style=COLOR_ACCENT) + Text(" Offline – awaiting restart", style="yellow"),
        Text("• Scope:", style=COLOR_ACCENT) + Text(" Only this loader is affected", style="green"),
        Text(""),
        Text("Δ IMPORTANT Δ", style=f"bold {COLOR_TITLE}"),
        Text("Your account, device, and all other loaders remain fully operational.", style=COLOR_TEXT),
        Text("You are not banned. Only this CODM loader is offline.", style=COLOR_TEXT),
        Text(""),
        Text("⌛ No restoration ETA – wait for RIEL to turn it on.", style=f"italic {COLOR_DIM}"),
        Text("💡 Please use other loaders from the main menu while you wait.", style=COLOR_ACCENT),
        Text(""),
        Text("✘ LOADER OFFLINE ✘", style=f"bold {COLOR_ACCENT}")
    ]

    combined_bottom = Text("\n").join(maintenance_lines)

    panel_bottom = Panel(
        Align.center(combined_bottom, vertical="middle"),
        title=Text(" WAIT FOR RIEL ", style=f"bold {COLOR_TITLE}"),
        border_style=COLOR_BORDER,
        box=box.HEAVY,
        width=80,
        padding=(2, 4)
    )
    console.print(Align.center(panel_bottom))
    console.print()

    contact_table = Table(box=box.SIMPLE, border_style=COLOR_BORDER, show_header=False, padding=(0,1), width=76)
    contact_table.add_column(style=COLOR_ACCENT, width=20)
    contact_table.add_column(style=COLOR_TEXT, width=54)
    contacts = [
        ("Telegram Username", "@rrielqt"),
        ("Telegram Channel", "@celestecutiee"),
        ("GitHub", "Mr.Spect3e"),
        ("Pinterest", "RYA")
    ]
    for plat, cont in contacts:
        contact_table.add_row(plat, cont)

    contact_panel = Panel(
        Align.center(contact_table),
        title=Text(" CONTACT RIEL ", style=f"bold {COLOR_TITLE}"),
        border_style=COLOR_BORDER,
        box=box.HEAVY,
        width=80,
        padding=(1,2)
    )
    console.print(Align.center(contact_panel))
    console.print()

    info_line = Panel(
        Align.center(Text("— WAITING FOR RIEL TO TURN ON THE LOADER —", style=f"bold {COLOR_ACCENT}")),
        border_style=COLOR_BORDER,
        box=box.SQUARE,
        width=60,
        padding=(0,1)
    )
    console.print(Align.center(info_line))
    console.print()

    sys.exit(0)

if __name__ == "__main__":
    main()