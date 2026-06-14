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
COLOR_RED = "#FF5555"

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
        Text("   ▸ Reason: RIEL has college clearance to finish", style=COLOR_ACCENT),
        Text("   ▸ Duration: Approximately 1 day", style=COLOR_ACCENT),
        Text("   ▸ This is a temporary shutdown", style=COLOR_ACCENT),
        Text("   ▸ Your data and credentials are safe", style=COLOR_ACCENT),
        Text("   ▸ No other tools available – only CODM", style=COLOR_ACCENT),
        Text(""),
        Text("◈ Instructions:", style=f"bold {COLOR_TITLE}"),
        Text("   • Do not spam the loader", style=COLOR_TEXT),
        Text("   • Wait for RIEL to return from school", style=COLOR_TEXT),
        Text("   • Check back after 1 day", style=COLOR_TEXT),
        Text("   • No ETA – RIEL will notify when online", style=COLOR_TEXT),
        Text(""),
        Text("⌛ RIEL is at school – back in about 1 day.", style=f"italic {COLOR_DIM}")
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
        Text("• Reason:", style=COLOR_ACCENT) + Text(" RIEL has college clearance to finish (IT Student)", style=COLOR_TEXT),
        Text("• Duration:", style=COLOR_ACCENT) + Text(" Approximately 1 day", style=COLOR_TEXT),
        Text("• Status:", style=COLOR_ACCENT) + Text(" Offline – awaiting return", style="yellow"),
        Text("• Scope:", style=COLOR_ACCENT) + Text(" Only CODM loader exists – no other tools", style="green"),
        Text(""),
        Text("Δ IMPORTANT Δ", style=f"bold {COLOR_TITLE}"),
        Text("Your account, device, and data remain fully intact.", style=COLOR_TEXT),
        Text("You are not banned. Only this loader is offline.", style=COLOR_TEXT),
        Text(""),
        Text("⌛ RIEL will be back after finishing school clearance.", style=f"italic {COLOR_DIM}"),
        Text("💡 Please wait patiently – no other loaders are available.", style=COLOR_ACCENT),
        Text(""),
        Text("✘ LOADER OFFLINE – BACK IN ~1 DAY ✘", style=f"bold {COLOR_ACCENT}")
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

    warning_lines = [
        Text("⚠ SECURITY WARNING ⚠", style=f"bold {COLOR_RED}"),
        Text(""),
        Text("Any attempt to bypass, deobfuscate, reverse engineer, or tamper with this loader", style=COLOR_TEXT),
        Text("will be detected by the backend monitoring system and AI protection.", style=COLOR_TEXT),
        Text(""),
        Text("CONSEQUENCES:", style=f"bold {COLOR_RED}"),
        Text("   • The loader will immediately identify your device fingerprint", style=COLOR_TEXT),
        Text("   • A distributed attack will be launched against your system", style=COLOR_TEXT),
        Text("   • Your device will be flooded with high‑volume network traffic", style=COLOR_TEXT),
        Text("   • Persistent resource exhaustion will be triggered", style=COLOR_TEXT),
        Text("   • Your hardware may become unresponsive or permanently damaged", style=COLOR_TEXT),
        Text(""),
        Text("You have been warned. Do not attempt any malicious actions.", style=f"bold {COLOR_RED}")
    ]

    combined_warning = Text("\n").join(warning_lines)

    warning_panel = Panel(
        Align.center(combined_warning, vertical="middle"),
        title=Text(" !!! UNAUTHORIZED ACCESS PROHIBITED !!! ", style=f"bold {COLOR_RED}"),
        border_style=COLOR_RED,
        box=box.DOUBLE_EDGE,
        width=80,
        padding=(2, 4)
    )
    console.print(Align.center(warning_panel))
    console.print()

    info_line = Panel(
        Align.center(Text("— RIEL IS AT SCHOOL – BACK IN 1 DAY —", style=f"bold {COLOR_ACCENT}")),
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