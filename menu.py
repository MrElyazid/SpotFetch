"""This is the main TUI file, core logic and functions is in functions.py"""

import functions
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.align import Align
from rich import box


console = Console()

settings = {
    'format': 'mp3',
    'output_path': '.',
    'cookie_file': None,
    'platform': 'ytmusic'
}

art = r"""
                        ____              _   _____    _       _     
                      / ___| _ __   ___ | |_|  ___|__| |_ ___| |__  
                      \___ \| '_ \ / _ \| __| |_ / _ \ __/ __| '_ \ 
                        ___)| |_) | (_) | |_|  _|  __/ || (__| | | |
                      |____/| .__/ \___/ \__|_|  \___|\__\___|_| |_|
                            |_|                                     
                                                                                            
"""

def show_banner():
    """Display the application banner"""
    banner_text = Text(art, style="bold cyan")
    panel = Panel(
        Align.center(banner_text),
        title="Welcome to SpotFetch!",
        title_align="center",
        border_style="bright_cyan",
        box=box.DOUBLE_EDGE
    )
    console.print(panel)
    console.print()

def show_current_settings():
    """Display current settings"""
    settings_text = Text.assemble(
        ("Current Settings:\n\n", "bold yellow"),
        ("Audio Format: ", "white"), (settings['format'].upper(), "cyan"), ("\n"),
        ("Output Directory: ", "white"), (settings['output_path'], "cyan"), ("\n"),
        ("Cookie File: ", "white"), (settings['cookie_file'] or "None", "cyan"), ("\n"),
        ("Download Platform: ", "white"), (f"{'YouTube Music' if settings['platform'] == 'ytmusic' else 'YouTube'}", "cyan")
    )
    
    panel = Panel(
        settings_text,
        title="Current Configuration",
        border_style="bright_green",
        box=box.ROUNDED
    )
    console.print(panel)

def configure_settings():
    """Configure application settings"""
    console.clear()
    show_banner()
    show_current_settings()
    
    console.print(Panel("Settings Configuration", style="bold blue"))
    
    settings_options = [
        ("1", "Set Audio Format", f"Currently: {settings['format'].upper()}"),
        ("2", "Set Output Directory", f"Currently: {settings['output_path']}"),
        ("3", "Set Cookie File", f"Currently: {settings['cookie_file'] or 'None'}"),
        ("4", "Set Download Platform", f"Currently: {settings['platform'].title()}"),
        ("5", "Reset to Defaults", "Reset all settings"),
        ("6", "Back to Main Menu", "Return to main menu")
    ]
    
    table = Table(title="Settings Menu", box=box.ROUNDED, title_style="bold cyan")
    table.add_column("Option", style="cyan", justify="center", width=8)
    table.add_column("Setting", style="yellow", width=25)
    table.add_column("Current Value", style="white")
    
    for option, setting, current in settings_options:
        table.add_row(option, setting, current)
    
    console.print(table)
    console.print()
    
    choice = Prompt.ask(
        "Select setting to configure",
        choices=["1", "2", "3", "4", "5", "6"],
        default="6"
    )
    
    if choice == "1":
        set_audio_format()
    elif choice == "2":
        set_output_directory()
    elif choice == "3":
        set_cookie_file()
    elif choice == "4":
        set_download_platform()
    elif choice == "5":
        reset_settings()
    elif choice == "6":
        return
    
    if choice != "6":
        console.print()
        show_current_settings()
        if Confirm.ask("\nConfigure another setting?", default=False):
            configure_settings()

def set_audio_format():
    """Set the audio format"""
    console.print(Panel("Set Audio Format", style="bold yellow"))
    formats = ["mp3", "m4a", "flac"]
    
    table = Table(box=box.SIMPLE)
    table.add_column("Option", style="cyan", justify="center")
    table.add_column("Format", style="green")
    table.add_column("Description", style="white")
    
    table.add_row("1", "MP3", "Most compatible format")
    table.add_row("2", "M4A", "Great balance between quality and compression")
    table.add_row("3", "FLAC", "Lossless, huge in size")
    
    console.print(table)
    
    choice = Prompt.ask("Choose format", choices=["1", "2", "3"], default="1")
    settings['format'] = formats[int(choice) - 1]
    console.print(f"Audio format set to: {settings['format'].upper()}", style="green")

def set_output_directory():
    """Set the output directory"""
    console.print(Panel("Set Output Directory", style="bold yellow"))
    console.print(f"Current directory: {settings['output_path']}")
    
    path = Prompt.ask("Enter new output directory", default=settings['output_path'])
    
    if not os.path.exists(path):
        if Confirm.ask(f"Directory '{path}' doesn't exist. Create it?"):
            try:
                os.makedirs(path, exist_ok=True)
                console.print(f"Created directory: {path}", style="green")
                settings['output_path'] = path
            except Exception as e:
                console.print(f"Error creating directory: {e}", style="red")
        else:
            console.print("Output directory unchanged", style="yellow")
    else:
        settings['output_path'] = path
        console.print(f"Output directory set to: {settings['output_path']}", style="green")

def set_cookie_file():
    """Set the cookie file"""
    console.print(Panel("Set Cookie File", style="bold yellow"))
    console.print(f"Current cookie file: {settings['cookie_file'] or 'None'}")
    
    if Confirm.ask("Do you want to use a cookie file?", default=settings['cookie_file'] is not None):
        cookie_path = Prompt.ask("Enter cookie file path", default=settings['cookie_file'] or "")
        if os.path.exists(cookie_path):
            settings['cookie_file'] = cookie_path
            console.print(f"Cookie file set to: {settings['cookie_file']}", style="green")
        else:
            console.print("Cookie file not found", style="red")
    else:
        settings['cookie_file'] = None
        console.print("Cookie file disabled", style="yellow")

def set_download_platform():
    """Set the download platform"""
    console.print(Panel("Set Download Platform", style="bold yellow"))
    console.print(Text("Youtube works best for niche and lesser known songs and artists\nYoutube music works best for popular songs and if you dont want to download video clips audio", style="italic white"))
    
    platforms = ["ytmusic", "youtube"]
    
    table = Table(box=box.SIMPLE)
    table.add_column("Option", style="cyan", justify="center")
    table.add_column("Platform", style="green")
    table.add_column("Description", style="white")
    
    table.add_row("1", "YouTube Music", "Best for popular songs, avoids video clips (default)")
    table.add_row("2", "YouTube", "Best for niche/lesser known songs and artists")
    
    console.print(table)
    
    choice = Prompt.ask("Choose platform", choices=["1", "2"], default="1")
    settings['platform'] = platforms[int(choice) - 1]
    console.print(f"Download platform set to: {settings['platform'].title()}", style="green")


def reset_settings():
    """Reset all settings to defaults"""
    console.print(Panel("Reset Settings", style="bold yellow"))
    settings['format'] = 'mp3'
    settings['output_path'] = '.'
    settings['cookie_file'] = None
    settings['platform'] = 'ytmusic'
    console.print("All settings reset to defaults", style="green")


def download_single_url():
    """Download audio from a single URL"""
    console.clear()
    show_banner()
    show_current_settings()
    
    console.print(Panel("Download from Single URL", style="bold blue"))
    
    url = Prompt.ask("Enter URL")
    
    console.print("Downloading...", style="yellow")
    try:
        functions.download_from_url(url, settings['format'], settings['output_path'], settings['cookie_file'])
        console.print("Successfully downloaded!", style="green bold")
    except Exception as e:
        console.print(f"Error: {e}", style="red")
    
    Prompt.ask("\nPress Enter to continue...")

def download_from_search():
    """Download audio from search query"""
    console.clear()
    show_banner()
    show_current_settings()
    
    console.print(Panel("Download from Search Query", style="bold blue"))
    
    track_name = Prompt.ask("Enter track name")
    artist_name = Prompt.ask("Enter artist name")
    
    song = {
        'track_name': track_name,
        'artist_name': artist_name
    }
    
    console.print("Searching and downloading...", style="yellow")
    try:
        functions.download_from_query(song, settings['format'], settings['output_path'], settings['cookie_file'], settings['platform'])
        console.print("Successfully downloaded!", style="green bold")
    except Exception as e:
        console.print(f"Error: {e}", style="red")
    
    Prompt.ask("\nPress Enter to continue...")

def download_from_urls_file():
    """Download from URLs text file"""
    console.clear()
    show_banner()
    show_current_settings()
    
    console.print(Panel("Download from URLs File", style="bold blue"))
    
    file_path = Prompt.ask("Enter path to text file with URLs")
    
    if not os.path.exists(file_path):
        console.print("File not found!", style="red")
        Prompt.ask("\nPress Enter to continue...")
        return
    
    console.print("Downloading from URLs file...", style="yellow")
    try:
        functions.read_download_urls_txt(file_path, settings['format'], settings['output_path'], settings['cookie_file'])
        console.print("Successfully Downloaded all URLs!", style="green bold")
    except Exception as e:
        console.print(f"Error: {e}", style="red")
    
    Prompt.ask("\nPress Enter to continue...")

def download_from_custom_csv():
    """Download from custom CSV file"""
    console.clear()
    show_banner()
    show_current_settings()
    
    console.print(Panel("Download from Custom CSV", style="bold blue"))
    console.print("Expected CSV format: name,artist", style="italic")
    
    file_path = Prompt.ask("Enter path to CSV file")
    
    if not os.path.exists(file_path):
        console.print("File not found!", style="red")
        Prompt.ask("\nPress Enter to continue...")
        return
    
    console.print("Processing CSV file...", style="yellow")
    try:
        functions.read_download_custom_csv(file_path, settings['format'], settings['output_path'], settings['cookie_file'], settings['platform'])
        console.print("Successfully processed CSV file!", style="green bold")
    except Exception as e:
        console.print(f"Error: {e}", style="red")
    
    Prompt.ask("\nPress Enter to continue...")

def process_tunemymusic_csv():
    """Download using TuneMyMusic CSV file"""
    console.clear()
    show_banner()
    show_current_settings()
    
    console.print(Panel("Download suing TuneMyMusic CSV", style="bold blue"))
    
    file_path = Prompt.ask("Enter path to TuneMyMusic CSV file")
    
    if not os.path.exists(file_path):
        console.print("File not found!", style="red")
        Prompt.ask("\nPress Enter to continue...")
        return
    
    console.print("Reading CSV file...", style="yellow")
    try:
        songs = functions.read_tunemymusic_csv_file(file_path)
        console.print("Processing songs...", style="yellow")
        
        if songs:
            download_songs_from_list(songs, settings['platform'])
        else:
            console.print("No songs found in the CSV file", style="yellow")
        
    except Exception as e:
        console.print(f"Error: {e}", style="red")
    
    Prompt.ask("\nPress Enter to continue...")

def process_exportify_csv():
    """Download using Exportify CSV file"""
    console.clear()
    show_banner()
    show_current_settings()
    
    console.print(Panel("Download using Exportify CSV", style="bold blue"))
    
    file_path = Prompt.ask("Enter path to Exportify CSV file")
    
    if not os.path.exists(file_path):
        console.print("File not found!", style="red")
        Prompt.ask("\nPress Enter to continue...")
        return
    
    console.print("Reading CSV file...", style="yellow")
    try:
        songs = functions.read_exportify_csv_file(file_path)
        console.print("Processing songs...", style="yellow")
        
        if songs:
            download_spotify_songs_from_list(songs, settings['platform'])
        else:
            console.print("No songs found in the CSV file", style="yellow")
        
    except Exception as e:
        console.print(f"Error: {e}", style="red")
    
    Prompt.ask("\nPress Enter to continue...")

def download_songs_from_list(songs, platform):
    """Download songs from a list using search queries"""
    
    total_songs = len(songs)
    console.print(f"Starting download of {total_songs} songs...", style="bold blue")
    
    for i, song in enumerate(songs):
        try:
            track_name = song.get('track_name', 'Unknown')
            artist_name = song.get('artist_name', 'Unknown')
            console.print(f"[{i+1}/{total_songs}] Downloading: {track_name} by {artist_name}", style="cyan")
            
            functions.download_from_query(song, settings['format'], settings['output_path'], settings['cookie_file'], platform)
            console.print(f"✓ Successfully downloaded: {track_name}", style="green")
            
        except Exception as e:
            console.print(f"✗ Failed to download {track_name}: {e}", style="red")
            continue
    
    console.print("All downloads complete!", style="green bold")

def download_spotify_songs_from_list(songs, platform):
    """Download Spotify songs with full metadata"""
    
    total_songs = len(songs)
    console.print(f"Starting download of {total_songs} Spotify songs with metadata...", style="bold blue")
    
    for i, song in enumerate(songs):
        try:
            track_name = song.get('track_name', 'Unknown')
            artists = ', '.join(song.get('artist_names', ['Unknown']))
            console.print(f"[{i+1}/{total_songs}] Downloading: {track_name} by {artists}", style="cyan")
            
            functions.download_spotify_song(settings['format'], song, settings['output_path'], settings['cookie_file'], platform)
            console.print(f"✓ Successfully downloaded: {track_name}", style="green")
            
        except Exception as e:
            console.print(f"✗ Failed to download {track_name}: {e}", style="red")
            continue
    
    console.print("All Spotify downloads complete!", style="green bold")

def main_menu():
    """Main application menu"""
    while True:
        console.clear()
        show_banner()
        show_current_settings()
        console.print()
        
        menu_options = [
            ("1", "Download using Exportify CSV", "Export your playlist csv here : https://exportify.app/"),
            ("2", "Download using TuneMyMusic CSV", "Export your playlist csv here : https://www.tunemymusic.com/transfer (make sure you export to a file!)"),
            ("3", "Download from URLs File", "Batch download from text file with YouTube URLs one by line."),
            ("4", "Download from Custom CSV", "Download from CSV with name,artist as headers"),
            ("5", "Download from Single URL", "Download audio from a direct URL ( can be a YT video url or playlist )"),
            ("6", "Download from Search", "Search and download by track/artist name"),
            ("7", "Settings", "Configure format (MP3/FLAC/M4A), output directory, and cookies"),
            ("8", "Exit", "Exit the application")
        ]
        
        table = Table(title="SpotFetch Main Menu", box=box.ROUNDED, title_style="bold cyan")
        table.add_column("Option", style="cyan", justify="center", width=8)
        table.add_column("Feature", style="yellow", width=30)
        table.add_column("Description", style="white")
        
        for option, feature, description in menu_options:
            table.add_row(option, feature, description)
        
        console.print(table)
        console.print()
        
        choice = Prompt.ask(
            "Select an option",
            choices=[str(i) for i in range(1, 9)],
            default="1"
        )
        
        if choice == "1":
            process_exportify_csv()
        elif choice == "2":
            process_tunemymusic_csv()
        elif choice == "3":
            download_from_urls_file()
        elif choice == "4":
            download_from_custom_csv()
        elif choice == "5":
            download_single_url()
        elif choice == "6":
            download_from_search()
        elif choice == "7":
            configure_settings()
        elif choice == "8":
            console.print("\nThank you for using SpotFetch!", style="bold cyan")
            console.print("Bye Bye!!", style="bold yellow")
            sys.exit(0)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n\nGoodbye!", style="bold cyan")
        sys.exit(0)
    except Exception as e:
        console.print(f"\nAn unexpected error occurred: {e}", style="bold red")
        sys.exit(1)
