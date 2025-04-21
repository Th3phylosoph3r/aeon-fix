import subprocess
import json
import re
import os
import platform
import datetime
import sys
import time
import shutil
from typing import List, Dict, Any, Optional, Tuple, Union # Ensure typing imports are present
import traceback
import shlex # Ensure shlex is imported
import webbrowser # Ensure webbrowser is imported
from PIL import ImageGrab

# Optional imports - will be checked at runtime
try:
    from ollama import Client
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.text import Text
    from rich.markdown import Markdown
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Confirm = None # Define Confirm as None if rich is not available

# Configuration
CONFIG = {
    "memory_file": "assistant_memory.json",
    "log_file": "pc_fix_logs.json",
    "ollama_host": "http://localhost:11434",
    "dangerous_commands": [
        "rm -rf", "deltree", "format", "dd if=", "mkfs",
        "del /", "rd /s", "rmdir /s", ":(){:|:&};:"
    ],
    "safe_diagnostic_commands": [
        "wmic", "systeminfo", "ipconfig", "netstat", "tasklist",
        "sfc", "dism", "chkdsk", "dir", "powercfg", "msinfo32",
        "driverquery", "where", "regsvr32", "mdsched.exe" # Added some more
    ]
}

# Initialize console
if RICH_AVAILABLE:
    console = Console()
    def print_info(message): console.print(f"[bold blue]INFO:[/bold blue] {message}")
    def print_success(message): console.print(f"[bold green]SUCCESS:[/bold green] {message}")
    def print_warning(message): console.print(f"[bold yellow]WARNING:[/bold yellow] {message}")
    def print_error(message): console.print(f"[bold red]ERROR:[/bold red] {message}")
    def print_md(md_text): console.print(Markdown(md_text))
else:
    # Basic print functions if rich is not available
    def print_info(message): print(f"INFO: {message}")
    def print_success(message): print(f"SUCCESS: {message}")
    def print_warning(message): print(f"WARNING: {message}")
    def print_error(message): print(f"ERROR: {message}")
    def print_md(md_text): print(md_text) # Basic print for markdown text

# Initialize LLM client if available
llm_client = None # Initialize to None
if OLLAMA_AVAILABLE:
    try:
        llm_client = Client(host=CONFIG["ollama_host"])
    except Exception as e:
        print_error(f"Failed to initialize Ollama client: {e}")
        OLLAMA_AVAILABLE = False

# =============================================================================
# Enhanced Rich UI/UX Utilities (with Emojis & Animation)
# =============================================================================

if RICH_AVAILABLE:
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.live import Live
    import time

    # Consistent, professional emoji usage
    EMOJI_INFO = "⚡"
    EMOJI_SUCCESS = "✔️"
    EMOJI_WARNING = "⚠️"
    EMOJI_ERROR = "❌"
    EMOJI_STEP = "🔁"
    EMOJI_INPUT = "📝"
    EMOJI_LLM = "🤖"

    def print_info(message):
        console.print(Panel(f"{EMOJI_INFO} [bold blue]INFO:[/bold blue]\n{message}", border_style="blue", expand=False, padding=(0,2)))
    def print_success(message):
        console.print(Panel(f"{EMOJI_SUCCESS} [bold green]SUCCESS:[/bold green]\n{message}", border_style="green", expand=False, padding=(0,2)))
    def print_warning(message):
        console.print(Panel(f"{EMOJI_WARNING} [bold yellow]WARNING:[/bold yellow]\n{message}", border_style="yellow", expand=False, padding=(0,2)))
    def print_error(message):
        console.print(Panel(f"{EMOJI_ERROR} [bold red]ERROR:[/bold red]\n{message}", border_style="red", expand=False, padding=(0,2)))
    def print_md(md_text):
        console.print(Panel(Markdown(md_text), border_style="magenta", expand=False, padding=(0,2)))

    def print_user_input(prompt: str) -> str:
        return Prompt.ask(Panel(f"{EMOJI_INPUT} [bold cyan]{prompt}[/bold cyan]", border_style="cyan", expand=False, padding=(0,2)))

    def print_choices(title: str, choices: list) -> int:
        table = Table(title=title, show_header=True, header_style="bold magenta", box=None, expand=False)
        table.add_column("#", justify="right", style="cyan", no_wrap=True)
        table.add_column("Option", style="white")
        for i, choice in enumerate(choices, 1):
            table.add_row(str(i), str(choice))
        console.print(table)
        return int(Prompt.ask("Select an option", choices=[str(i) for i in range(1, len(choices)+1)])) - 1

    def print_step(title: str, step: str, number: int = None, total: int = None):
        label = f"{EMOJI_STEP} Step {number}/{total}" if number and total else f"{EMOJI_STEP} Step"
        console.print(Panel(f"[bold yellow]{label}: {title}[/bold yellow]\n{step}", border_style="yellow", expand=False, padding=(0,2)))

    def print_section(title: str, content: str):
        console.print(Panel(f"[bold white]{title}[/bold white]\n{content}", border_style="white", expand=False, padding=(0,2)))

    def show_spinner(message: str, duration: float = 2.0):
        # Use a spinner for LLM calls or long operations
        with Progress(
            SpinnerColumn(style="bold magenta"),
            TextColumn(f"[bold magenta]{EMOJI_LLM}[/bold magenta] {{task.description}}"),
            transient=True,
            console=console
        ) as progress:
            task = progress.add_task(f"{message}", total=None)
            time.sleep(duration)
            progress.remove_task(task)
else:
    def print_info(message): print(f"\nINFO: {message}\n" + "-"*60)
    def print_success(message): print(f"\nSUCCESS: {message}\n" + "-"*60)
    def print_warning(message): print(f"\nWARNING: {message}\n" + "-"*60)
    def print_error(message): print(f"\nERROR: {message}\n" + "-"*60)
    def print_md(md_text): print("\n" + md_text + "\n" + "-"*60)
    def print_user_input(prompt: str) -> str:
        return input(f"{prompt}\n> ")
    def print_choices(title: str, choices: list) -> int:
        print(f"{title}")
        for i, choice in enumerate(choices, 1):
            print(f"  {i}. {choice}")
        while True:
            try:
                idx = int(input("Select an option: ")) - 1
                if 0 <= idx < len(choices):
                    return idx
            except Exception:
                pass
            print("Invalid choice. Try again.")
    def print_step(title: str, step: str, number: int = None, total: int = None):
        label = f"Step {number}/{total}" if number and total else "Step"
        print(f"\n[{label}] {title}\n{step}\n" + "-"*60)
    def print_section(title: str, content: str):
        print(f"\n--- {title} ---\n{content}\n" + "-"*60)
    def show_spinner(message: str, duration: float = 2.0):
        print(f"...{message}...")
        time.sleep(duration)

# =============================================================================
# Clipboard Image Capture for Vision LLM
# =============================================================================

def save_clipboard_image():
    """Check clipboard for image, save to ./screenshots, return path or None."""
    img = ImageGrab.grabclipboard()
    if img is not None:
        folder = os.path.join(os.getcwd(), "screenshots")
        os.makedirs(folder, exist_ok=True)
        filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = os.path.join(folder, filename)
        img.save(path, 'PNG')
        print_success(f"Screenshot saved: {path}")
        return path
    else:
        print_warning("No image found in clipboard. Use Win+Shift+S to take a screenshot, then Ctrl+C.")
        return None



# =============================================================================
# Memory Management Functions
# =============================================================================

def load_memory() -> Dict[str, Any]:
    """Load persistent memory from file or initialize if it doesn't exist."""
    try:
        if os.path.exists(CONFIG["memory_file"]):
            with open(CONFIG["memory_file"], "r", encoding='utf-8') as f: # Added encoding
                return json.load(f)
    except Exception as e:
        print_error(f"Error loading memory: {e}")

    # Initialize default memory structure
    return {
        "last_session": None,
        "previous_issues": [],
        "system_info": {},
        "command_history": []
    }

def save_memory(memory: Dict[str, Any]) -> None:
    """Save persistent memory to file."""
    try:
        with open(CONFIG["memory_file"], "w", encoding='utf-8') as f: # Added encoding
            json.dump(memory, f, indent=2, ensure_ascii=False) # Added ensure_ascii=False
    except Exception as e:
        print_error(f"Error saving memory: {e}")

def update_memory(memory: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]:
    """Update a specific key in memory."""
    memory[key] = value
    save_memory(memory)
    return memory

def add_to_memory_list(memory: Dict[str, Any], key: str, value: Any,
                       max_items: int = 20) -> Dict[str, Any]: # Increased max_items slightly
    """Add an item to a list in memory with a maximum size limit."""
    if key not in memory or not isinstance(memory[key], list):
        memory[key] = []

    # Add new item at the beginning
    memory[key].insert(0, value)

    # Trim list if it exceeds max size
    if len(memory[key]) > max_items:
        memory[key] = memory[key][:max_items]

    save_memory(memory)
    return memory

# =============================================================================
# Logging Functions
# =============================================================================

def log_action(action_type: str, details: Dict[str, Any], success: bool = True) -> None:
    """Log an action to the structured log file."""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "action_type": action_type,
        "success": success,
        "details": details
    }

    # Load existing logs or create empty list
    logs = []
    try:
        if os.path.exists(CONFIG["log_file"]):
            with open(CONFIG["log_file"], "r", encoding='utf-8') as f: # Added encoding
                logs = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError): # More specific error handling
        pass # Ignore if file not found or empty/corrupt
    except Exception as e:
        print_error(f"Error reading log file (will overwrite if saving succeeds): {e}")


    # Add new entry and save
    logs.append(log_entry)
    try:
        with open(CONFIG["log_file"], "w", encoding='utf-8') as f: # Added encoding
            json.dump(logs, f, indent=2, ensure_ascii=False) # Added ensure_ascii=False
    except Exception as e:
        print_error(f"Error writing to log file: {e}")

# =============================================================================
# System Information Functions
# =============================================================================

def get_os_info() -> Dict[str, str]:
    """Get basic operating system information."""
    info = {
        "system": platform.system(),
        "version": platform.version(),
        "release": platform.release(),
        "architecture": platform.machine()
    }

    # Add more Windows-specific information
    if platform.system() == "Windows":
        try:
            # Using windows-specific commands
            # Note: run_command should be defined before this is called
            result = run_command(["systeminfo", "/FO", "LIST"], capture_output=True, shell=False,
                                 require_confirmation=False)
            if result["success"] and result["output"]:
                output = result["output"]
                # Extract OS Name, Version, etc. from systeminfo output
                for line in output.splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        key = key.strip()
                        value = value.strip()

                        if key in ["OS Name", "OS Version", "System Manufacturer",
                                   "System Model", "System Type", "Total Physical Memory", "System Locale"]: # Added locale
                            info[key] = value
            else:
                print_warning(f"systeminfo command failed or produced no output. Error: {result.get('error','')}")
        except Exception as e:
            print_error(f"Error getting Windows-specific info via systeminfo: {e}")

    # Add more Linux-specific information
    elif platform.system() == "Linux":
        try:
            # Getting Linux distribution info
            # Use platform.freedesktop_os_release() if available
            if hasattr(platform, "freedesktop_os_release"):
                distro_info = platform.freedesktop_os_release()
                info["distribution"] = distro_info.get("PRETTY_NAME", distro_info.get("NAME", "Unknown"))
                info["distribution_version"] = distro_info.get("VERSION_ID", "Unknown")
            # Fallback using os-release file
            elif os.path.exists("/etc/os-release"):
                 with open("/etc/os-release", "r") as f:
                     for line in f:
                         if line.startswith("PRETTY_NAME="):
                             info["distribution"] = line.split("=",1)[1].strip().strip('"')
                         elif line.startswith("VERSION_ID="):
                             info["distribution_version"] = line.split("=",1)[1].strip().strip('"')

            # Getting memory info from /proc/meminfo
            if os.path.exists("/proc/meminfo"):
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        if "MemTotal" in line:
                            info["Total Physical Memory"] = line.split(":", 1)[1].strip()
                            break
        except Exception as e:
            print_error(f"Error getting Linux-specific info: {e}")

    return info

def get_hardware_info() -> Dict[str, Any]:
    """Get hardware information using platform-specific commands."""
    info = {}

    if platform.system() == "Windows":
        try:
            # Using wmic to get CPU information
            result = run_command(["wmic", "cpu", "get", "Name,NumberOfCores,NumberOfLogicalProcessors", "/format:list"],
                                capture_output=True, shell=False, require_confirmation=False)
            if result["success"] and result["output"]:
                cpu_info = {}
                for line in result["output"].splitlines():
                    if "=" in line:
                        key, value = line.split("=", 1)
                        # Standardize keys slightly
                        key_std = key.strip().replace("NumberOf", "Num")
                        cpu_info[key_std] = value.strip()
                info["CPU"] = cpu_info # Nest under CPU key
            else:
                 print_warning(f"WMIC CPU query failed or produced no output. Error: {result.get('error','')}")

            # Using wmic to get disk information
            result = run_command(["wmic", "diskdrive", "get", "Model,Size,Status,InterfaceType", "/format:list"], # Added InterfaceType
                                capture_output=True, shell=False, require_confirmation=False)
            if result["success"] and result["output"]:
                disks = []
                disk = {}
                for line in result["output"].splitlines():
                    line = line.strip()
                    if not line: # Check for blank line separator
                        if disk: # Append disk info if we collected any
                            disks.append(disk)
                        disk = {} # Reset for next disk
                    elif "=" in line:
                        key, value = line.split("=", 1)
                        disk[key.strip()] = value.strip()
                if disk: # Append the last disk if any info was found
                    disks.append(disk)
                info["Disks"] = disks
            else:
                print_warning(f"WMIC DiskDrive query failed or produced no output. Error: {result.get('error','')}")

            # Using wmic to get Baseboard (Motherboard) info
            result = run_command(["wmic", "baseboard", "get", "Product,Manufacturer,Version", "/format:list"],
                                capture_output=True, shell=False, require_confirmation=False)
            if result["success"] and result["output"]:
                 mb_info = {}
                 for line in result["output"].splitlines():
                    if "=" in line:
                        key, value = line.split("=", 1)
                        mb_info[key.strip()] = value.strip()
                 info["Motherboard"] = mb_info
            else:
                print_warning(f"WMIC Baseboard query failed. Error: {result.get('error','')}")

        except Exception as e:
            print_error(f"Error getting Windows hardware info via WMIC: {e}")

    elif platform.system() == "Linux":
        try:
            # Get CPU info from /proc/cpuinfo (simplified)
            result = run_command(["grep", "-E", "^(model name|cpu cores)", "/proc/cpuinfo"],
                                capture_output=True, shell=False, require_confirmation=False)
            if result["success"] and result["output"]:
                cpu_info = {}
                model_name = ""
                cores = 0
                for line in result["output"].splitlines():
                     key_val = line.split(":", 1)
                     if len(key_val) == 2:
                         key = key_val[0].strip()
                         val = key_val[1].strip()
                         if key == "model name" and not model_name: # Take first model name
                             model_name = val
                         elif key == "cpu cores":
                             try:
                                 cores += int(val) # Sum cores across potentially multiple entries
                             except ValueError:
                                 pass
                cpu_info["Name"] = model_name
                cpu_info["NumCores"] = cores # Total physical cores reported
                info["CPU"] = cpu_info
            else:
                 print_warning(f"Could not get CPU info from /proc/cpuinfo. Error: {result.get('error','')}")

            # Get disk info using lsblk
            result = run_command(["lsblk", "-d", "-b", "-o", "NAME,SIZE,MODEL,TYPE,TRAN", "--json"], # Added TYPE, TRAN (transport), -b (bytes)
                                capture_output=True, shell=False, require_confirmation=False)
            if result["success"] and result["output"]:
                try:
                    disk_data = json.loads(result["output"])
                    # Format slightly for consistency
                    disks = []
                    for bd in disk_data.get("blockdevices", []):
                        if bd.get("type") == "disk": # Only include physical disks
                            disks.append({
                                "Model": bd.get("model", "N/A"),
                                "Size": bd.get("size", 0), # Size in bytes
                                "Status": "OK", # lsblk doesn't easily give health status like wmic
                                "InterfaceType": bd.get("tran", "N/A") # e.g., sata, nvme
                            })
                    info["Disks"] = disks
                except json.JSONDecodeError:
                    print_error("Error parsing lsblk JSON output")
            else:
                print_warning(f"lsblk command failed or produced no output. Error: {result.get('error','')}")

        except Exception as e:
            print_error(f"Error getting Linux hardware info: {e}")

    return info

def get_network_info() -> Dict[str, Any]:
    """Get network configuration information."""
    info = {}

    if platform.system() == "Windows":
        try:
            result = run_command(["ipconfig", "/all"],
                                capture_output=True, shell=False, require_confirmation=False)
            if result["success"]:
                info["ipconfig_all"] = result["output"] # Changed key slightly
            else:
                 print_warning(f"ipconfig /all failed. Error: {result.get('error','')}")
        except Exception as e:
            print_error(f"Error getting Windows network info (ipconfig): {e}")

    elif platform.system() == "Linux":
        try:
            result = run_command(["ip", "-br", "-c", "addr"], # Brief, colorized address view
                                capture_output=True, shell=False, require_confirmation=False)
            if result["success"]:
                info["ip_addr_brief"] = result["output"]
            else:
                print_warning(f"ip addr failed. Error: {result.get('error','')}")

            result = run_command(["ip", "route"], # Routing table
                                 capture_output=True, shell=False, require_confirmation=False)
            if result["success"]:
                info["ip_route"] = result["output"]
            else:
                 print_warning(f"ip route failed. Error: {result.get('error','')}")

            if os.path.exists("/etc/resolv.conf"):
                try:
                    with open("/etc/resolv.conf", "r") as f:
                        info["dns_config"] = f.read()
                except Exception as e_dns:
                    print_error(f"Error reading /etc/resolv.conf: {e_dns}")
            else:
                 print_warning("/etc/resolv.conf not found.")

        except Exception as e:
            print_error(f"Error getting Linux network info: {e}")

    return info

def collect_system_logs(max_logs: int = 50) -> List[Dict[str, Any]]:
    """Collect recent system logs (Windows Event logs or Linux system logs)."""
    logs = []

    if platform.system() == "Windows":
        try:
            # Use f-string - it handles doubled {{ }} correctly for PowerShell's literal braces
            powershell_script = f"""
            $ErrorActionPreference = 'SilentlyContinue' # Suppress PS errors if logs are inaccessible
            # Select properties needed, including the necessary calculated properties for JSON
            $logs = Get-WinEvent -LogName System, Application -FilterXPath "*[System[(Level=1 or Level=2 or Level=3)]]" -MaxEvents {max_logs} |
                Select-Object @{{Name='TimeCreated'; Expression={{$_.TimeCreated.ToString("o")}}}}, `
                              ProviderName, Id, LevelDisplayName, Message, `
                              @{{Name='Source'; Expression={{$_.ProviderName}}}} |
                Sort-Object TimeCreated -Descending

            # Directly convert the selected objects to JSON - PowerShell handles message cleaning better this way
            # Use -Depth 5 to handle potentially nested messages
            $logs | ConvertTo-Json -Compress -Depth 5
            """
            # Removed the manual JSON building loop - ConvertTo-Json on the selected objects is cleaner

            # Execute the PowerShell script
            result = run_command(["powershell", "-NoProfile", "-Command", powershell_script],
                                capture_output=True, shell=False, require_confirmation=False)

            if result["success"] and result["output"]:
                try:
                    # Attempt to parse the JSON output directly
                    logs_data = json.loads(result["output"])
                    # Ensure logs is always a list
                    if isinstance(logs_data, list):
                        logs = logs_data
                    elif isinstance(logs_data, dict): # Handle case where only one log is returned
                         logs = [logs_data]
                    else:
                         print_warning(f"Unexpected data type from PowerShell JSON: {type(logs_data)}")
                         logs = [] # Assign empty list if parsing gives unexpected type

                except json.JSONDecodeError as json_err:
                    print_error(f"Error parsing PowerShell JSON output for logs: {json_err}")
                    print_warning(f"Raw PS output (first 500 chars): {result.get('output', '')[:500]}") # Log raw output on error
                    logs = [] # Assign empty list on JSON error
                except Exception as parse_e:
                    print_error(f"Unexpected error processing PowerShell log output: {parse_e}")
                    logs = []
            else:
                 # Log failure details if PS command failed
                 error_details = result.get('error', '') or result.get('output', '(No output)') # Show stderr or stdout
                 print_warning(f"PowerShell Get-WinEvent command failed or produced no output. Error/Output: {error_details[:500]}...")

        except Exception as e:
            # Catch-all for other errors during this block
            print_error(f"Error collecting Windows event logs: {e}")
            print_error(traceback.format_exc()) # Provide full traceback
   # --- End of NEW/Corrected Block ---

    elif platform.system() == "Linux":
        try:
            # Use journalctl for systemd systems, fallback to common log files
            if shutil.which("journalctl"):
                # Get recent errors (priority 0-3), no pager, JSON format if possible, limit count
                # Try JSON output first
                cmd = ["journalctl", "-p", "0..3", "--no-pager", "-n", str(max_logs), "-o", "json"]
                result = run_command(cmd, capture_output=True, shell=False, require_confirmation=False)

                if result["success"] and result["output"]:
                    try:
                        # journalctl json output is one JSON object per line
                        log_lines = result["output"].strip().split('\n')
                        for line in log_lines:
                            try:
                                log_entry = json.loads(line)
                                # Extract relevant fields, map to consistent names
                                logs.append({
                                    "TimeCreated": datetime.datetime.fromtimestamp(int(log_entry.get("__REALTIME_TIMESTAMP", 0)) / 1000000).isoformat() if log_entry.get("__REALTIME_TIMESTAMP") else "N/A",
                                    "ProviderName": log_entry.get("SYSLOG_IDENTIFIER", log_entry.get("_SYSTEMD_UNIT", "unknown")),
                                    "Id": log_entry.get("_PID", "N/A"), # Use PID as an identifier if available
                                    "Level": log_entry.get("PRIORITY", "N/A"), # Lower number is higher priority
                                    "Message": log_entry.get("MESSAGE", "").strip(),
                                    "Source": log_entry.get("_HOSTNAME", "N/A")
                                })
                            except json.JSONDecodeError:
                                print_warning(f"Skipping malformed JSON line from journalctl: {line[:100]}...")
                            except Exception as parse_exc:
                                 print_warning(f"Error processing journalctl JSON entry: {parse_exc}")
                    except Exception as outer_exc:
                         print_error(f"Error processing journalctl JSON output: {outer_exc}")

                # If JSON failed, try plain text parsing
                elif not result["success"] or not result["output"]:
                    print_warning("journalctl JSON output failed, trying plain text.")
                    cmd = ["journalctl", "-p", "0..3", "--no-pager", "-n", str(max_logs)]
                    result = run_command(cmd, capture_output=True, shell=False, require_confirmation=False)
                    if result["success"] and result["output"]:
                        # Simple text parsing (less reliable)
                        for line in result["output"].strip().splitlines():
                             # Basic split - might need refinement based on actual journalctl format
                             parts = line.split(" ", 4)
                             if len(parts) >= 5:
                                 logs.append({
                                    "TimeCreated": " ".join(parts[0:3]), # Approximate timestamp
                                    "ProviderName": parts[3],
                                    "Id": "N/A",
                                    "Level": "N/A", # Can't easily get level from default text
                                    "Message": parts[4],
                                    "Source": parts[3] # Use hostname/identifier as source
                                })
                    else:
                        print_warning(f"journalctl plain text command failed. Error: {result.get('error','')}")

            else:
                # Fallback for non-systemd systems (basic check of common logs)
                print_warning("journalctl not found, checking common log files (limited view).")
                common_logs = ["/var/log/syslog", "/var/log/messages"]
                log_count = 0
                for log_file in common_logs:
                    if log_count >= max_logs: break
                    if os.path.exists(log_file):
                        try:
                            # Read last N lines (approximate) - inefficient for large files
                             proc = subprocess.run(['tail', '-n', str(max_logs * 2), log_file], capture_output=True, text=True, check=False)
                             if proc.stdout:
                                 lines = proc.stdout.strip().splitlines()
                                 # Filter for error/warning keywords (very basic)
                                 for line in reversed(lines): # Read from end
                                     if log_count >= max_logs: break
                                     line_lower = line.lower()
                                     if "error" in line_lower or "warning" in line_lower or "critical" in line_lower or "failed" in line_lower:
                                         logs.append({
                                             "TimeCreated": line[:15], # Extract first 15 chars as timestamp guess
                                             "ProviderName": log_file.split('/')[-1], # Use filename as provider
                                             "Id": "N/A",
                                             "Level": "Warning/Error", # Guess
                                             "Message": line,
                                             "Source": log_file
                                         })
                                         log_count += 1
                        except Exception as file_read_e:
                            print_error(f"Error reading log file {log_file}: {file_read_e}")
        except Exception as e:
            print_error(f"Error collecting Linux logs: {e}")
            print_error(traceback.format_exc())

    # Sort logs by timestamp if possible before returning
    try:
        # Attempt to parse ISO format or handle fallback strings
        def sort_key(log_entry):
            ts_str = log_entry.get("TimeCreated", "0")
            try:
                return datetime.datetime.fromisoformat(ts_str)
            except ValueError:
                 # Fallback for non-ISO, try to get hour
                 try:
                     # Example: Try parsing "Month Day HH:MM:SS" like from journalctl text
                     return datetime.datetime.strptime(ts_str, '%b %d %H:%M:%S').replace(year=datetime.datetime.now().year)
                 except ValueError:
                     return datetime.datetime.min # Put unparseable dates first

        logs.sort(key=sort_key, reverse=True)
    except Exception as sort_e:
        print_warning(f"Could not reliably sort logs by time: {sort_e}")


    return logs

def analyze_logs_for_patterns(logs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze logs for common patterns and correlate events."""
    patterns = {
        "app_crashes": [],
        "service_failures": [],
        "driver_issues": [],
        "permission_errors": [], # Added
        "disk_errors": [], # Added
        "error_timestamps": {},
        "frequent_sources": {},
        "suspicious_apps": set()
    }

    # Keywords for specific error types
    crash_keywords = ["stopped working", "crashed", "not responding", "faulting application", "hang", "freeze"]
    service_keywords = ["service", "failed to start", "stopped unexpectedly", "terminated with error"]
    driver_keywords = ["driver", "device", "\\driver\\", "nvlddmkm", "amdkmdag", "iaStor", "rtx"] # Added common driver names/paths
    permission_keywords = ["permission", "access denied", " EPERM ", " EACCES "]
    disk_keywords = ["disk", "volume", "ntfs", "ext4", " btrfs ", "harddisk", "error on device", "i/o error", "bad sector"]

    # Look for application names in log messages
    known_problematic_apps = [
        "CapCut", "CCleaner", "OneDrive", "Teams", "Discord",
        "Chrome", "Firefox", "Edge", "Skype", "Zoom", "Valorant", "Riot" # Added some games/launchers
    ]

    for log in logs:
        msg = log.get("Message", "").lower()
        source = log.get("ProviderName", "unknown").lower()
        timestamp = log.get("TimeCreated", "")
        # level = log.get("Level", "") # Level already filtered generally

        # Count errors by source more accurately
        source_key = source if source != "unknown" else log.get("Source", "unknown").lower() # Use Source field if ProviderName missing
        if source_key not in patterns["frequent_sources"]:
            patterns["frequent_sources"][source_key] = {"count": 0, "levels": set()}
        patterns["frequent_sources"][source_key]["count"] += 1
        if log.get("Level"): patterns["frequent_sources"][source_key]["levels"].add(str(log.get("Level")))


        # Group by timestamp (hour level for broader clustering)
        if timestamp and isinstance(timestamp, str):
            try:
                # Attempt ISO parsing first
                dt_obj = datetime.datetime.fromisoformat(timestamp.split('.')[0]) # Ignore ms/tz for grouping
                hour_timestamp = dt_obj.strftime("%Y-%m-%d %H")
            except ValueError:
                 # Fallback for non-ISO, try to get hour
                 parts = timestamp.split(":")
                 if len(parts) >= 2:
                      hour_timestamp = parts[0] # Use up to the first colon as hour key
                 else:
                      hour_timestamp = timestamp # Use the whole string if no colon
            except Exception:
                hour_timestamp = "unknown_time" # Catch any other parsing errors

            if hour_timestamp not in patterns["error_timestamps"]:
                patterns["error_timestamps"][hour_timestamp] = 0
            patterns["error_timestamps"][hour_timestamp] += 1

        # Check for patterns using keywords
        if any(keyword in msg for keyword in crash_keywords):
            patterns["app_crashes"].append(log)
        if any(keyword in msg for keyword in service_keywords):
             # Avoid double counting if already counted as crash
             if log not in patterns["app_crashes"]:
                patterns["service_failures"].append(log)
        if any(keyword in msg for keyword in driver_keywords):
            patterns["driver_issues"].append(log)
        if any(keyword in msg for keyword in permission_keywords):
            patterns["permission_errors"].append(log)
        if any(keyword in msg for keyword in disk_keywords):
            patterns["disk_errors"].append(log)


        # Look for known problematic applications
        for app in known_problematic_apps:
            # Check both message and source for app name
            if app.lower() in msg or app.lower() in source_key:
                patterns["suspicious_apps"].add(app)

    # Sort frequent sources by count (descending)
    patterns["frequent_sources"] = dict(
        sorted(patterns["frequent_sources"].items(), key=lambda item: item[1]["count"], reverse=True)
    )

    # Find time clusters of errors (events happening close to each other)
    patterns["error_clusters"] = find_time_clusters(patterns["error_timestamps"]) # Use hour-level clustering

    return patterns

def find_time_clusters(timestamps: Dict[str, int], min_cluster_size: int = 3, max_gap_hours: int = 1) -> List[Dict[str, Any]]:
    """Find clusters of errors happening close together in time (hour resolution)."""
    clusters = []
    if not timestamps:
        return clusters

    # Sort timestamps chronologically (requires parsing YYYY-MM-DD HH or similar)
    sorted_times = []
    for ts_str, count in timestamps.items():
        try:
            # Attempt parsing YYYY-MM-DD HH format
            dt_obj = datetime.datetime.strptime(ts_str, "%Y-%m-%d %H")
            sorted_times.append((dt_obj, count))
        except ValueError:
             # Skip timestamps that don't match the expected format for clustering
             print_warning(f"Skipping unparseable timestamp for clustering: {ts_str}")
             pass

    if not sorted_times:
        return clusters

    sorted_times.sort(key=lambda x: x[0])

    current_cluster = None

    for dt_obj, count in sorted_times:
        if current_cluster is None:
            # Start the first cluster
            current_cluster = {"start_dt": dt_obj, "end_dt": dt_obj, "count": count}
        else:
            # Check if the gap to the last event in the cluster is within the limit
            time_diff = dt_obj - current_cluster["end_dt"]
            if time_diff <= datetime.timedelta(hours=max_gap_hours):
                # Extend the current cluster
                current_cluster["end_dt"] = dt_obj
                current_cluster["count"] += count
            else:
                # Gap is too large, finalize the previous cluster (if large enough)
                if current_cluster["count"] >= min_cluster_size:
                     clusters.append({
                         "start": current_cluster["start_dt"].strftime("%Y-%m-%d %H:%M"),
                         "end": current_cluster["end_dt"].strftime("%Y-%m-%d %H:%M"),
                         "count": current_cluster["count"]
                     })
                # Start a new cluster
                current_cluster = {"start_dt": dt_obj, "end_dt": dt_obj, "count": count}

    # Add the last cluster if it meets the size requirement
    if current_cluster and current_cluster["count"] >= min_cluster_size:
        clusters.append({
            "start": current_cluster["start_dt"].strftime("%Y-%m-%d %H:%M"),
            "end": current_cluster["end_dt"].strftime("%Y-%m-%d %H:%M"),
            "count": current_cluster["count"]
        })

    # Sort clusters by count (most frequent first)
    return sorted(clusters, key=lambda x: x["count"], reverse=True)


def generate_system_report() -> Dict[str, Any]:
    """Generate a comprehensive system report."""
    print_info("Generating system report...")

    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "os_info": get_os_info(),
        "hardware_info": get_hardware_info(),
        "network_info": get_network_info(),
        "recent_logs": collect_system_logs(50) # Collect slightly more logs for better pattern analysis
    }

    # Calculate report size safely
    try:
        report_size = sys.getsizeof(json.dumps(report)) # Estimate size after JSON conversion
    except Exception:
        report_size = -1 # Indicate error

    log_action("system_report", {"report_size_bytes": report_size})
    return report

# =============================================================================
# Command Execution Functions
# =============================================================================

def is_dangerous_command(cmd_str: str) -> bool: # Takes string now
    """Check if a command string might be dangerous."""
    cmd_lower = cmd_str.lower()
    # Check against dangerous command patterns first
    if any(danger_cmd in cmd_lower for danger_cmd in CONFIG["dangerous_commands"]):
        # Double check it's not part of a safe command explanation or path
        # Example: avoid flagging "rm -rf /path/to/cache" if used carefully
        # This is hard, basic check is better than nothing. Add more specific exceptions if needed.
        # For now, any match is considered dangerous.
        return True

    # Check if it's a known safe diagnostic command (check the start)
    # This is less reliable if safe commands are used with dangerous flags,
    # but helps allow common diagnostics.
    first_word = cmd_lower.split()[0]
    if first_word in CONFIG["safe_diagnostic_commands"]:
        # Add checks for dangerous flags on safe commands if needed, e.g. chkdsk /f /r is okay, format C: is not
        if first_word == "chkdsk" and "/f" not in cmd_lower and "/r" not in cmd_lower:
             return False # Basic chkdsk without repair flags is safe
        elif first_word != "chkdsk": # Allow other safe commands more freely for now
             return False

    # Default to not dangerous if no patterns match and not explicitly safe
    # Or default to True for safety? Let's lean towards caution: if not explicitly safe, assume maybe dangerous.
    # Update: Let's refine. If no dangerous pattern matched, and not explicitly safe, assume NOT dangerous for now
    # to avoid over-flagging. User confirmation is still key.
    return False


def run_command(command: Union[List[str], str], # Allow string for shell=True
                capture_output: bool = True,
                shell: bool = False, # Default to False for security
                require_confirmation: bool = True,
                explanation: str = None) -> Dict[str, Any]:
    """
    Run a system command with optional user confirmation. Handles shell=True/False.
    """
    # --- Input Validation and String Representation ---
    cmd_str: str
    cmd_list: Optional[List[str]] = None
    if shell:
        if not isinstance(command, str):
            print_error("Shell=True requires command to be a string.")
            return {"command": repr(command), "success": False, "error": "Invalid command type for shell=True", "executed": False, "confirmed": False}
        cmd_str = command
    else:
        if not isinstance(command, list):
            print_error("Shell=False requires command to be a list of strings.")
            return {"command": repr(command), "success": False, "error": "Invalid command type for shell=False", "executed": False, "confirmed": False}
        cmd_list = command
        # Handle potential empty list
        if not cmd_list:
             print_error("Received empty command list.")
             return {"command": "[]", "success": False, "error": "Empty command list", "executed": False, "confirmed": False}
        cmd_str = " ".join(shlex.quote(str(arg)) for arg in cmd_list) # Create a safe string representation for logging/display

    result = {
        "command_str": cmd_str, # Log the string representation
        "command_executed_as": cmd_list if not shell else cmd_str, # How it was passed to subprocess
        "shell_mode": shell,
        "success": False,
        "output": "",
        "error": "",
        "return_code": None,
        "confirmed": False, # Default to False
        "executed": False,
        "execution_time": 0.0
    }

    # --- Safety Check ---
    # Use cmd_str for safety check regardless of shell mode
    dangerous = is_dangerous_command(cmd_str)

    # --- Confirmation ---
    # Always require confirmation if command is flagged as dangerous
    needs_confirmation = require_confirmation or dangerous
    user_confirmed = False

    if needs_confirmation:
        print_info(f"Proposed command: `{cmd_str}`") # Use markdown for clarity
        if explanation:
            print_info(f"Purpose: {explanation}")

        if dangerous:
            print_warning("⚠️ This command is potentially dangerous!")
            print_warning("   It might modify or delete important system files, or require a restart.")
            print_warning("   Please review carefully before proceeding.")

        # Ask for confirmation
        if RICH_AVAILABLE and Confirm:
            user_confirmed = Confirm.ask("Do you want to run this command?", default=False)
        else:
            confirm_input = input("Do you want to run this command? (y/N): ").lower().strip()
            user_confirmed = confirm_input == 'y'

        result["confirmed"] = user_confirmed
        if not user_confirmed:
            print_warning("Command execution cancelled by user.")
            log_action("command_cancelled", {"command": cmd_str, "reason": "user_declined"}, success=False) # Log cancellation
            return result # Return immediately if cancelled
    else:
        # If no confirmation was required (e.g., internal check like 'where')
        result["confirmed"] = True # Mark as implicitly confirmed
        user_confirmed = True

    # --- Execution ---
    if user_confirmed: # Proceed only if confirmed (implicitly or explicitly)
        try:
            print_info(f"Executing (`shell={shell}`): `{cmd_str}`")


            # Special handling for MSC files (Windows Management Console)
            if cmd_str.lower().endswith('.msc') and platform.system() == "Windows":
                # For MSC files, we need to use shell=True and prefix with 'start'
                print_info("Detected MSC file, using special handling...")
                modified_cmd = f"start {cmd_str}"
                run_arg = modified_cmd
                shell = True  # Force shell mode for MSC files
            else:
                # Use appropriate argument for subprocess.run based on shell mode
                run_arg = cmd_str if shell else cmd_list

            # Show spinner while command is running (if Rich is available)
            if RICH_AVAILABLE:
                with Progress(
                    SpinnerColumn(style="bold magenta"),
                    TextColumn(f"[bold magenta]{EMOJI_LLM}[/bold magenta] {{task.description}}"),
                    transient=True,
                    console=console
                ) as progress:
                    task = progress.add_task(f"Running: {cmd_str}", total=None)
                    start_time = time.time()
                    # Use appropriate argument for subprocess.run based on shell mode
                    run_arg = cmd_str if shell else cmd_list
                    # Set encoding based on platform for better text handling
                    stdout_encoding = 'utf-8'
                    stderr_encoding = 'utf-8'
                    if platform.system() == "Windows":
                        try:
                            oem_cp = f'cp{subprocess.check_output(["chcp"], shell=True, text=True).split(":")[-1].strip()}'
                            stdout_encoding = oem_cp
                            stderr_encoding = oem_cp
                        except Exception:
                            print_warning("Could not detect OEM codepage, using utf-8. Output might be garbled.")
                    process = subprocess.run(
                        run_arg,
                        capture_output=capture_output,
                        text=False, # Capture as bytes first
                        shell=shell,
                        check=False, # Don't raise exception on non-zero exit code
                    )
                    progress.remove_task(task)
                    execution_time = time.time() - start_time
            else:
                start_time = time.time()
                run_arg = cmd_str if shell else cmd_list
                stdout_encoding = 'utf-8'
                stderr_encoding = 'utf-8'
                if platform.system() == "Windows":
                    try:
                        oem_cp = f'cp{subprocess.check_output(["chcp"], shell=True, text=True).split(":")[-1].strip()}'
                        stdout_encoding = oem_cp
                        stderr_encoding = oem_cp
                    except Exception:
                        print_warning("Could not detect OEM codepage, using utf-8. Output might be garbled.")
                process = subprocess.run(
                    run_arg,
                    capture_output=capture_output,
                    text=False, # Capture as bytes first
                    shell=shell,
                    check=False, # Don't raise exception on non-zero exit code
                )
                execution_time = time.time() - start_time
            result["execution_time"] = round(execution_time, 2)
            result["return_code"] = process.returncode
            result["success"] = process.returncode == 0
            result["executed"] = True
            # Decode output and error streams carefully
            if capture_output:
                try:
                    result["output"] = process.stdout.decode(stdout_encoding, errors='replace') if process.stdout else ""
                except Exception as decode_e:
                    print_error(f"Error decoding stdout: {decode_e}")
                    result["output"] = repr(process.stdout) # Show raw bytes on decode error
                try:
                    result["error"] = process.stderr.decode(stderr_encoding, errors='replace') if process.stderr else ""
                except Exception as decode_e:
                    print_error(f"Error decoding stderr: {decode_e}")
                    result["error"] = repr(process.stderr)
            # Log the action
            log_details = {
                "command": cmd_str,
                "shell": shell,
                "return_code": process.returncode,
                "execution_time": result["execution_time"],
            }
            if result["success"]:
                print_success(f"Command completed successfully (Code: {process.returncode}, Time: {result['execution_time']}s)")
                log_action("command_executed", log_details, success=True)
            else:
                print_error(f"Command failed (Code: {process.returncode}, Time: {result['execution_time']}s)")
                # Always show stderr if command failed and stderr has content
                if result["error"]:
                    print_error(f"Stderr: {result['error'].strip()}")
                # Show stdout too if stderr is empty but command failed, as errors might go there
                elif result["output"]:
                     print_warning(f"Stdout (may contain error details): {result['output'].strip()}")
                log_action("command_executed", log_details, success=False)
        except FileNotFoundError as fnf_error:
            error_msg = f"Command or executable not found: {fnf_error}"
            print_error(error_msg)
            result["error"] = error_msg
            result["success"] = False
            result["executed"] = False # Mark as not executed because it wasn't found
            log_action("command_error", {"command": cmd_str, "error": error_msg}, success=False)
        except subprocess.TimeoutExpired:
            error_msg = "Command timed out."
            print_error(error_msg)
            result["error"] = error_msg
            result["success"] = False
            result["executed"] = True # It ran, but timed out
            log_action("command_error", {"command": cmd_str, "error": error_msg, "reason": "timeout"}, success=False)
        except Exception as e:
            error_msg = f"Error executing command: {e}"
            tb = traceback.format_exc()
            print_error(error_msg)
            print_error(f"Traceback:\n{tb}") # Print traceback for debugging
            result["error"] = error_msg
            result["traceback"] = tb # Store traceback
            result["success"] = False
            result["executed"] = False # Assume not fully executed if exception hit
            log_action("command_error", {
                "command": cmd_str,
                "error": error_msg,
                "traceback": tb
            }, success=False)
    return result


# =============================================================================
# LLM Interaction Functions
# =============================================================================



def _list_ollama_models_cli() -> List[str]:
    """Helper function to list models using the 'ollama list' command."""
    try:
        # Ensure run_command is available and works before this point
        result = run_command(["ollama", "list"], capture_output=True, shell=False, require_confirmation=False)
        if result["success"] and result["output"]:
             lines = result["output"].strip().split('\n')
             if len(lines) > 1: # Check if there's more than just the header
                 # Extract first column, skipping the header
                 # Handle potential variation in spacing using split(maxsplit=1) or similar if needed
                 models = []
                 for line in lines[1:]:
                     parts = line.split() # Simple split might suffice
                     if parts: # Ensure the line wasn't just whitespace
                         models.append(parts[0]) # Take the first part as model name

                 if models:
                      print_info(f"Found {len(models)} models via 'ollama list' command.")
                      return models
                 else:
                      print_warning("'ollama list' command output seems empty after header.")
                      return []
             else:
                 print_warning("'ollama list' command output format unexpected (no header or data?).")
                 return []
        else:
            # Log error if command failed or no output
            error_msg = result.get('error', 'No output received')
            print_error(f"Failed to run 'ollama list' command: {error_msg}")
            return []
    except FileNotFoundError:
         # Handle case where 'ollama' command itself is not found
         print_error("'ollama' command not found in PATH. Cannot list models via CLI.")
         return []
    except Exception as cli_e:
         # Catch any other exceptions during CLI execution
         print_error(f"Error executing 'ollama list' command: {cli_e}")
         print_error(traceback.format_exc()) # Show traceback for debugging
         return []


# THIS IS THE CORRECTED FUNCTION
def list_ollama_models() -> List[str]:
    """List available Ollama models, preferring API, falling back to CLI."""
    # Check if client is usable first
    if OLLAMA_AVAILABLE and llm_client:
        try:
            print_info("Attempting to list models via Ollama API...")
            models_info = llm_client.list()

            # --- Start Robust Checks ---
            if not isinstance(models_info, dict):
                print_error(f"Ollama API list() returned unexpected type: {type(models_info)}. Response: {models_info}")
                print_info("Falling back to 'ollama list' command...")
                return _list_ollama_models_cli() # Call helper for CLI

            models_list = models_info.get('models') # Safely get the list

            if models_list is None:
                print_error(f"Ollama API list() response missing 'models' key. Response: {models_info}")
                print_info("Falling back to 'ollama list' command...")
                return _list_ollama_models_cli() # Call helper for CLI
            if not isinstance(models_list, list):
                 print_error(f"Ollama API 'models' key is not a list. Type: {type(models_list)}. Response: {models_info}")
                 print_info("Falling back to 'ollama list' command...")
                 return _list_ollama_models_cli() # Call helper for CLI
            # --- End Robust Checks ---

            # Safely extract names, checking each model dictionary
            valid_model_names = []
            for model_data in models_list:
                if isinstance(model_data, dict):
                    model_name = model_data.get('name') # Safely get the name using .get()
                    if model_name and isinstance(model_name, str): # Check if name exists and is a string
                        valid_model_names.append(model_name)
                    else:
                        # Log if a model entry is missing a name or name is not a string
                        print_warning(f"Found model data with missing or invalid 'name' key: {model_data}")
                else:
                     # Log if an item in the 'models' list isn't a dictionary
                     print_warning(f"Found non-dictionary item in models list: {model_data}")

            if not valid_model_names:
                 print_warning("Ollama API returned model data, but no valid model names could be extracted.")
                 # Fallback even if API returned something, but no names found
                 print_info("Falling back to 'ollama list' command...")
                 return _list_ollama_models_cli()

            print_info(f"Found {len(valid_model_names)} models via Ollama API.")
            return valid_model_names

        except Exception as e:
            # Keep the general exception handler but log more context
            print_error(f"Error listing Ollama models via API: {e}")
            print_error(traceback.format_exc()) # Print traceback for detailed debugging
            # Fallback to CLI on *any* API exception
            print_info("Falling back to 'ollama list' command...")
            return _list_ollama_models_cli() # Call helper for CLI
    else:
        # If client wasn't available in the first place
        print_warning("Ollama client not available or not initialized. Attempting CLI fallback...")
        return _list_ollama_models_cli()

def select_model(models: List[str]) -> Optional[str]:
    """Let user select an Ollama model."""
    if not models:
        print_error("No Ollama models available to select.")
        return None

    print_info("Available Ollama models:")
    # Enumerate models starting from 1 for user selection
    for idx, model_name in enumerate(models, start=1):
        print(f"{idx}. {model_name}")

    # Loop for valid input
    while True:
        try:
            default_choice = "1"
            prompt_text = f"Choose a model number to use [{default_choice}]:"

            if RICH_AVAILABLE:
                selection_str = Prompt.ask(prompt_text, default=default_choice)
            else:
                selection_str = input(prompt_text) or default_choice

            selection_idx = int(selection_str) - 1 # Convert to 0-based index

            if 0 <= selection_idx < len(models):
                selected_model = models[selection_idx]
                print_success(f"Selected model: {selected_model}")
                return selected_model
            else:
                print_error("Invalid selection. Please enter a number from the list.")
        except ValueError:
            print_error("Invalid input. Please enter a number.")
        except EOFError: # Handle Ctrl+D or unexpected end of input
             print_warning("\nSelection cancelled.")
             return None


def ask_llm(prompt: str, model: str, system_message: str = None) -> Optional[str]:
    """Ask a question to the LLM, handling potential errors."""
    if not OLLAMA_AVAILABLE or not llm_client:
        print_error("Ollama is not available or client not initialized. Cannot query LLM.")
        return None
    if not model:
        print_error("No LLM model selected or provided. Cannot query LLM.")
        return None

    try:
        print_info(f"🧠 Asking LLM ({model})... (This may take a moment)") # Clearer indication

        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        # Log the prompt being sent (optional, for debugging)
        # log_action("llm_query", {"model": model, "prompt_start": prompt[:200] + "..."})

        # Make the API call
        response = llm_client.chat(model=model, messages=messages)

        # Extract content and log success
        content = response["message"]["content"]
        # log_action("llm_response", {"model": model, "response_length": len(content)}, success=True)
        print_info("LLM response received.") # Confirmation
        return content

    except Exception as e:
        # Log detailed error
        error_msg = f"Error querying LLM ({model}): {e}"
        tb = traceback.format_exc()
        print_error(error_msg)
        log_action("llm_error", {"model": model, "error": str(e), "traceback": tb}, success=False)
        return None


def analyze_problem(problem_description: str, system_report: Dict[str, Any],
                   memory: Dict[str, Any], model: str) -> Optional[str]:
    """Analyze a problem using the LLM and system information, providing detailed instructions."""
    # Extract logs from the system report
    logs = system_report.get("recent_logs", [])

    # Analyze logs for patterns
    log_patterns = analyze_logs_for_patterns(logs)

    # Format log patterns for LLM consumption
    patterns_text = ""
    if log_patterns.get("suspicious_apps"):
        patterns_text += f"- Suspicious applications mentioned: {', '.join(log_patterns['suspicious_apps'])}\n"
    if log_patterns.get("app_crashes"):
        patterns_text += f"- Application crash events detected: {len(log_patterns['app_crashes'])}\n"
    if log_patterns.get("service_failures"):
        patterns_text += f"- Service failure events detected: {len(log_patterns['service_failures'])}\n"
    if log_patterns.get("driver_issues"):
        patterns_text += f"- Potential driver issue events detected: {len(log_patterns['driver_issues'])}\n"
    if log_patterns.get("permission_errors"):
        patterns_text += f"- Permission error events detected: {len(log_patterns['permission_errors'])}\n"
    if log_patterns.get("disk_errors"):
        patterns_text += f"- Potential disk error events detected: {len(log_patterns['disk_errors'])}\n"

    if log_patterns.get("frequent_sources"):
        top_sources = list(log_patterns["frequent_sources"].items())[:5] # Show top 5
        patterns_text += "- Most frequent error/warning sources:\n"
        for source, data in top_sources:
             levels = ', '.join(data['levels'])
             patterns_text += f"  - {source}: {data['count']} occurrences (Levels: {levels})\n"

    if log_patterns.get("error_clusters"):
        patterns_text += "- Significant error clusters (time periods with high error counts):\n"
        for cluster in log_patterns["error_clusters"][:3]: # Show top 3 clusters
            patterns_text += f"  - {cluster['count']} errors between {cluster['start']} and {cluster['end']}\n"

    if not patterns_text: # Handle case where no patterns found
        patterns_text = "No specific error patterns detected in the analyzed logs."

    # Format a sample of logs for context
    logs_text = ""
    if logs:
        logs_text = "**Recent System Logs (up to 15 most recent errors/warnings/critical):**\n"
        logs_text += "\n".join(
            # Improved formatting for readability
            f"- [{log.get('TimeCreated', 'N/A')}] Lvl: {log.get('Level', 'N/A')} Src: {log.get('ProviderName', 'N/A')} ID: {log.get('Id','N/A')} | {log.get('Message', 'N/A')}"
            for log in logs[:15] # Use the already collected/sorted logs
        )
    else:
        logs_text = "**Recent System Logs:**\nNo recent system logs found or collected."

    # Previous issues from memory
    previous_issues_text = ""
    if memory.get("previous_issues") and memory["previous_issues"]:
        previous_issues_text = "**Previous Issues:**\n" + "\n".join(
            f"- {issue.get('timestamp', 'N/A')[:16]}: {issue.get('description', 'Unknown')} (Resolved: {issue.get('resolved', 'Unknown')})"
            for issue in memory.get("previous_issues", [])[:3] # Only last 3 issues
        )

    # OS information
    os_info = system_report.get("os_info", {})
    os_name = os_info.get('OS Name', os_info.get('system', 'Unknown'))
    os_version = os_info.get('OS Version', os_info.get('version', 'Unknown'))
    os_arch = os_info.get('System Type', os_info.get('architecture', 'Unknown'))
    os_info_text = f"OS: {os_name} {os_version} ({os_arch})"

    # Create prompt for LLM with enhanced log analysis and **NEW** detailed guidelines
    prompt = f"""
You are an expert PC troubleshooting assistant running locally on the user's machine.
Your goal is to diagnose the problem and provide clear, actionable steps, including specific commands the user can execute via this tool.

⚠️ **User reported this problem:**
>>> "{problem_description}"

---
📊 **System Information:**
{os_info_text}
{("Motherboard: "+ system_report.get("hardware_info", {}).get("Motherboard", {}).get("Manufacturer", "") + " " + system_report.get("hardware_info", {}).get("Motherboard", {}).get("Product", "")) if system_report.get("hardware_info", {}).get("Motherboard") else ""}
{("CPU: "+ system_report.get("hardware_info", {}).get("CPU", {}).get("Name", "N/A")) if system_report.get("hardware_info", {}).get("CPU") else ""}

---
📉 **Log Analysis Patterns:**
{patterns_text}

---
{logs_text}
---
{previous_issues_text}
---

🎯 **Your Task:**
1.  Thoroughly analyze the user's problem description in the context of the provided system info, log patterns, and recent logs.
2.  Prioritize potential causes based on the evidence (e.g., black screens + unresponsive buttons point towards hardware/driver issues over simple app errors).
3.  Provide a clear, structured diagnosis.
4.  Suggest a *sequence* of specific, step-by-step commands to investigate or fix the issue. Start with less invasive checks.
5.  For each step (especially commands), explain *why* it's being suggested.
6.  Format your response using Markdown.

---
‼️ **COMMAND AND ACTION FORMATTING RULES (VERY IMPORTANT!)** ‼️

When you suggest actions the user should take *through this tool*, use the following formats:

A.  **Executable Commands:** For commands that can be run directly in the Windows Command Prompt or PowerShell, use the `[[*** command ***]]` format.
    *   **Example:** To suggest running System File Checker: [[*** sfc /scannow ***]]
    *   **Example:** To suggest checking disk C: [[*** chkdsk C: /f ***]] (Note: This often requires a reboot)
    *   **Example:** To run Windows Memory Diagnostic: [[*** mdsched.exe ***]]
    *   **Example:** To get detailed driver info: [[*** driverquery /V /FO CSV ***]]

B.  **Checking Command Existence (Windows):** Before suggesting a command that might not be built-in (like `choco` or a third-party tool), suggest checking for it using `where`.
    *   **Example:** [[*** where choco.exe ***]]
    *   **Example:** [[*** where "Display Driver Uninstaller.exe" ***]] (Use quotes if name has spaces)

C.  **File Paths with Spaces:** If a command involves file paths containing spaces, **YOU MUST enclose the full path in double quotes.** Use standard Windows backslashes `\\`.
    *   **Correct:** [[*** ren "C:\\Program Files (x86)\\Bad App\\config.old" "config.bak" ***]]
    *   **Incorrect:** [[*** ren C:\\Program Files (x86)\\Bad App\\config.old config.bak ***]]

D.  **URLs:** Do **NOT** use the command format for URLs. Just write them normally.
    *   **Example:** Download the latest driver from NVIDIA: https://www.nvidia.com/drivers

E.  **GUI Actions / Information:** Do **NOT** use the command format for actions requiring the GUI or just providing info. Describe the action clearly. Suggest the `.msc` file or executable if applicable.
    *   **Example:** "Open Device Manager (run `devmgmt.msc`)" - *Don't* use [[*** Open Device Manager ***]]
    *   **Example:** "Check the temperatures in your BIOS/UEFI settings." - *Don't* use [[*** Check BIOS Temps ***]]
    *   **Example:** "Try booting into Safe Mode. (You can usually do this by holding Shift while clicking Restart)."

F.  **Sequence:** List commands in a logical troubleshooting order. The tool will execute them one by one and ask for intermediate analysis.

G.  **Caution:** Before suggesting potentially disruptive commands (like `chkdsk /f`, registry edits, deletions with `del`), add a warning note about potential data loss or system impact and suggest backups if appropriate.

**Your Goal:** Provide an accurate diagnosis and a safe, sequential plan of executable commands formatted correctly so the tool can assist the user effectively. Focus on the commands the *tool* should help execute.
---

Begin your analysis and provide your structured response now. Start with the diagnosis, then list the proposed command sequence.
"""

    # Log the analysis action with more detailed context summary
    log_action("problem_analysis", {
        "problem": problem_description,
        "model": model,
        "context_summary": {
             "os_info": os_info_text,
             "log_patterns_found": bool(patterns_text and "No specific error patterns" not in patterns_text),
             "log_count": len(logs),
             "previous_issues_count": len(memory.get("previous_issues", []))
        }
    })

    # Make the call to the LLM
    return ask_llm(prompt, model, system_message="You are a helpful and cautious PC diagnostic assistant providing structured troubleshooting plans.")


def extract_commands_from_llm_response(response: str) -> List[Dict[str, Any]]:
    """
    Extract commands and potentially other actionable items (like URLs)
    from LLM response using special formats. Now case-insensitive for URL tag.
    """
    items = []
    # Command format: [[*** command ***]]
    command_pattern = r"\[\[\*\*\*\s*(.*?)\s*\*\*\*\]\]" # Added optional space trimming
    # URL format suggestion: [[URL: url ]] (Case-insensitive)
    url_pattern = r"\[\[URL:\s*(https?://[^\s\]]+)\s*\]\]" # More specific URL pattern

    # --- Find URLs first ---
    url_matches = re.finditer(url_pattern, response, re.IGNORECASE)
    processed_indices = set() # Track processed parts of the string

    for match in url_matches:
        url_text = match.group(1).strip()
        start_pos, end_pos = match.span()

        # Mark this region as processed
        for i in range(start_pos, end_pos):
            processed_indices.add(i)

        # Basic context extraction (sentence before)
        context_start = max(0, start_pos - 200)
        context_text = response[context_start:start_pos].strip()
        sentences = re.split(r'[.!?]\s+', context_text)
        context = sentences[-1].strip() if sentences else context_text

        items.append({
            "type": "url",
            "value": url_text,
            "context": context if context else "No context found.",
            "original_match_position": start_pos
        })

    # --- Find Commands, avoiding already processed URL regions ---
    command_matches = re.finditer(command_pattern, response)

    for match in command_matches:
        start_pos, end_pos = match.span()

        # Check if this match overlaps with a processed URL region
        is_overlapped = False
        for i in range(start_pos, end_pos):
            if i in processed_indices:
                is_overlapped = True
                break
        if is_overlapped:
            continue # Skip if it's part of a URL tag we already handled

        cmd_text = match.group(1).strip()
        if not cmd_text:
            continue

        # Context extraction
        context_start = max(0, start_pos - 200)
        context_text = response[context_start:start_pos].strip()
        sentences = re.split(r'[.!?]\s+', context_text)
        context = sentences[-1].strip() if sentences else context_text

        item_type = "command"
        # Basic check for common *nix commands on Windows
        # Use shlex.split to handle quoted commands before checking first word
        try:
             cmd_first_word = shlex.split(cmd_text)[0].lower()
        except:
             cmd_first_word = cmd_text.split()[0].lower() # Fallback for simple split

        if platform.system() == "Windows" and cmd_first_word in ["which", "sudo", "apt", "yum", "dnf", "apt-get"]:
             item_type = "invalid_command" # Mark as potentially invalid
        # Map known tools that aren't direct commands but executables
        elif "memory diagnostic" in cmd_text.lower() or "mdsched" in cmd_text.lower():
             item_type = "command"
             cmd_text = "mdsched.exe" # Map to the actual executable

        items.append({
            "type": item_type,
            "value": cmd_text,
            "context": context if context else "No context found.",
            "original_match_position": start_pos
        })


    # Sort items based on their appearance order in the response
    items.sort(key=lambda x: x["original_match_position"])

    return items


# THIS IS THE CORRECTED FUNCTION
def handle_llm_response(response: str, problem_description: str, model: str) -> None:
    """
    Process LLM response, extract actionable items, display them,
    and execute commands *interactively*, analyzing after each step.

    Args:
        response: The LLM response text
        problem_description: The original problem description
        model: The LLM model name
    """
    # First, display the initial LLM response
    print_md(response)

    # Extract actionable items from the initial response
    items = extract_commands_from_llm_response(response) # Use the improved extractor
    executable_commands = [item for item in items if item["type"] == "command"]
    other_items = [item for item in items if item["type"] != "command"] # URLs, invalid etc.

    if not items:
        print_info("No actionable items detected in the response.")
        return

    print_info("\nDetected actionable items from initial analysis:")
    command_indices_map: Dict[int, int] = {} # Maps display number -> index in items list
    display_number = 0
    # Display all initially suggested items
    for i, item in enumerate(items):
        display_number += 1
        value = item["value"]
        desc = item.get("context", "No context available") # Use .get for safety
        item_type = item["type"]
        prefix = f"{display_number}. [{item_type.upper()}]"

        print(f"{prefix} {value}")
        if desc and desc != "No context available":
            print(f"   Context: {desc}")
        if item_type == "command":
            # We map display number to the index within the *original* items list
            command_indices_map[display_number] = i
        elif item_type == "invalid_command":
            print_warning("   (This command might not work on Windows)")

    # --- Handle Non-Command Items First (like URLs) ---
    urls_to_open = [item["value"] for item in other_items if item["type"] == "url"]

    if urls_to_open:
        if RICH_AVAILABLE and Confirm:
            open_urls = Confirm.ask(f"Open {len(urls_to_open)} detected URL(s) in your browser?", default=True)
        else:
            open_urls = input(f"Open {len(urls_to_open)} detected URL(s)? [Y/n]: ").lower().strip() != 'n'

        if open_urls:
            for url in urls_to_open:
                try:
                    webbrowser.open(url)
                    print_success(f"Attempted to open {url}")
                    log_action("url_opened", {"url": url}, success=True)
                except Exception as e:
                    print_error(f"Failed to open URL {url}: {e}")
                    log_action("url_open_failed", {"url": url, "error": str(e)}, success=False)

    # --- Interactive Command Execution ---
    if not executable_commands:
        print_info("No executable commands were suggested in the initial response.")
        return # Skip execution if no commands

    print_info("\n--- Starting Interactive Command Execution ---")
    if RICH_AVAILABLE and Confirm:
        proceed = Confirm.ask("Proceed with executing the suggested commands one by one?", default=True)
    else:
        proceed = input("Proceed with executing commands one by one? [Y/n]: ").lower().strip() != 'n'

    if not proceed:
        print_warning("Command execution skipped by user.")
        return

    memory = load_memory() # Load fresh memory for history context

    # Keep track of executed commands in this session for context
    session_command_history = []

    # We will iterate using an index to allow modification of the executable_commands list
    current_command_index = 0
    while current_command_index < len(executable_commands):
        # Get the current command info from the potentially modified list
        cmd_info = executable_commands[current_command_index]
        cmd_str = cmd_info["value"]
        cmd_context = cmd_info.get("context", "").strip()
        # 1. Prefer context from item itself if meaningful
        # 2. If context is missing, generic, or a placeholder, try to extract from initial LLM analysis
        if not cmd_context or cmd_context.lower() in ("no context provided.", "no context found.", "*", "", None):
            # Try to extract a relevant purpose from the initial LLM response (the analysis)
            # We'll look for the closest paragraph or sentence mentioning this command
            import re
            # Find all command blocks and their explanations in the LLM analysis
            pattern = re.compile(r"([^.\n]*?)(?:\n|\.)?\s*\u2022?\s*\\*\\*\\* ?" + re.escape(cmd_str) + r" ?\\*\\*\\*", re.IGNORECASE)
            match = pattern.search(response)
            if match and match.group(1).strip():
                cmd_context = match.group(1).strip()
            else:
                # Fallback: look for any paragraph mentioning the command
                para_pattern = re.compile(r"([^.\n]*?\b" + re.escape(cmd_str.split()[0]) + r"\b[^.\n]*[.\n])", re.IGNORECASE)
                para_match = para_pattern.search(response)
                if para_match and para_match.group(1).strip():
                    cmd_context = para_match.group(1).strip()
                else:
                    cmd_context = "No purpose provided by LLM."

        print_info(f"\n➡️ Executing Step {current_command_index + 1} / {len(executable_commands)}: `{cmd_str}`")
        print_info(f"   Purpose: {cmd_context}")

        # Prevent infinite loop: check if this command was already executed
        if cmd_str in session_command_history:
            print_warning(f"Command `{cmd_str}` has already been executed in this session. Stopping to prevent a loop.")
            break
        session_command_history.append(cmd_str)

        # --- Pre-execution check (Windows - Optional but Recommended) ---
        can_run = True
        if platform.system() == "Windows":
            # Extract first word as potential command name
            try:
                 # Use shlex to handle quoted first args correctly
                 potential_cmd_name = shlex.split(cmd_str)[0]
            except:
                 potential_cmd_name = cmd_str.split()[0] # Fallback

            # List of common built-ins or commands usually found directly
            known_builtins = ['cmd', 'powershell', 'ren', 'copy', 'del', 'dir', 'move', 'rd', 'md', 'echo', 'set', 'net', 'chkdsk', 'regsvr32', 'sfc', 'wmic', 'tasklist', 'ipconfig', 'systeminfo', 'driverquery', 'where', 'start', 'msinfo32', 'dxdiag', 'devmgmt.msc', 'eventvwr.msc', 'services.msc', 'taskmgr', 'perfmon', 'winver', 'control', 'mdsched.exe']
            # Check if it's not a known builtin and doesn't contain path separators
            if potential_cmd_name.lower() not in known_builtins and '\\' not in potential_cmd_name and '/' not in potential_cmd_name:
                print_info(f"Checking if '{potential_cmd_name}' exists using 'where'...")
                # Use run_command itself to check, suppress confirmation for this check
                where_result = run_command(['where', potential_cmd_name], capture_output=True, shell=False, require_confirmation=False)
                if not where_result["success"]:
                    print_warning(f"Command or executable '{potential_cmd_name}' not found via 'where'. It might be a typo, not in PATH, or require installation.")
                    if RICH_AVAILABLE and Confirm:
                        try_anyway = Confirm.ask("Attempt to run the command anyway (it might be a shell builtin or use a full path)?", default=False)
                    else:
                        try_anyway = input("Attempt to run anyway? [y/N]: ").lower().strip() == 'y'

                    if not try_anyway:
                         log_action("command_skipped", {"command": cmd_str, "reason": "Not found by 'where', user skipped"}, success=False)
                         can_run = False
                         # Skip this command and move to the next one in the list
                         current_command_index += 1
                         continue # Go to the next iteration of the while loop
                else:
                    found_path = where_result['output'].strip().splitlines()[0] if where_result.get('output') else 'Path not parsed'
                    print_info(f"'{potential_cmd_name}' found at: {found_path}")
        # --- End Pre-execution check ---

        # Determine shell usage
        use_shell = False
        cmd_list_or_str: Union[List[str], str]
        try:
            # If pipes, redirection, or complex shell ops are detected, consider shell=True
            # Also check for environment variables (%var%) which often need shell expansion on Windows
            if any(op in cmd_str for op in ['|', '>', '<', '&&', '||']) or ('%' in cmd_str and platform.system() == "Windows"):
                 use_shell = True
                 cmd_list_or_str = cmd_str # Pass raw string to shell
                 print_warning(f"Using shell=True for command: `{cmd_str}` (due to operators or '%')")
            else:
                # Use shlex for robust splitting, handling quotes etc.
                cmd_list_or_str = shlex.split(cmd_str)
                use_shell = False # Prefer shell=False if possible
        except ValueError as e:
            # shlex might fail on complex/malformed commands (e.g., unmatched quotes)
            print_warning(f"Could not parse command reliably using shlex ({e}). Check quotes. Falling back to shell=True.")
            use_shell = True
            cmd_list_or_str = cmd_str

        # Execute the command (run_command handles internal confirmation logic)
        result = run_command(
            cmd_list_or_str, # Pass list or string based on use_shell
            capture_output=True,
            shell=use_shell,
            require_confirmation=True, # Always require explicit confirmation for commands run in sequence
            explanation=cmd_context
        )

        # Log command execution attempt to session history *regardless* of execution status for context
        session_command_history.append({
             "command": cmd_str,
             "executed": result["executed"], # Track if it ran
             "confirmed": result["confirmed"], # Track if user confirmed
             "success": result["success"],
             "output": result.get("output", ""),
             "error": result.get("error", ""),
             "return_code": result.get("return_code")
        })

        # Update persistent memory only if it was actually executed
        if result["executed"]:
            memory = add_to_memory_list(memory, "command_history", {
                "timestamp": datetime.datetime.now().isoformat(),
                "command": cmd_str, # Log the original string
                "success": result["success"],
                "return_code": result.get("return_code", None)
            })
            save_memory(memory) # Save after each command

        # --- Intermediate Analysis ---
        if result["executed"]: # Only analyze if it actually ran
            if result["success"]:
                print_success(f"Command `{cmd_str}` completed successfully.")
                # Truncate output for display and LLM context
                output_display = (result.get("output", "")[:1000] + "..." if len(result.get("output", "")) > 1000 else result.get("output", "(No output)"))
                print_info("Output (truncated):")
                print(output_display if output_display.strip() else "(No output)")
            else:
                print_error(f"Command `{cmd_str}` failed (Return Code: {result.get('return_code', 'N/A')}).")
                error_display = ""
                # Prioritize showing stderr if it exists
                if result.get("error"):
                    error_display = result["error"][:1000] + ("..." if len(result["error"]) > 1000 else "")
                    print_error("Error Output (stderr, truncated):")
                    print(error_display if error_display.strip() else "(No stderr output)")
                # Show stdout if stderr is empty, as errors might go there
                elif result.get("output"):
                     output_display = result.get("output", "")[:1000] + ("..." if len(result.get("output", "")) > 1000 else "")
                     print_warning("Output (stdout, potentially contains error details, truncated):")
                     print(output_display if output_display.strip() else "(No stdout output)")
                     if not error_display.strip(): error_display = output_display # Use stdout for LLM context if stderr was empty


            # Decide if intermediate analysis is needed
            is_last_command = (current_command_index == len(executable_commands) - 1)

            # Analyze if command failed OR if it's not the last planned command
            # (No need to analyze after the very last command *succeeds* unless you want a final summary)
            if not result["success"] or not is_last_command:
                print_info("\n🧠 Asking LLM for analysis of the last step...")

                # Prepare context for the LLM
                history_summary = "\n".join([f"- `{cmd}`" for cmd in session_command_history])
                next_planned_command_str = "None (this was the last planned step)"
                if current_command_index + 1 < len(executable_commands):
                    next_planned_command_str = f"`{executable_commands[current_command_index + 1]['value']}`"

                # Limit context size passed to LLM
                output_context = result.get("output", "")[:500] + ('...' if len(result.get("output", "")) > 500 else '')
                error_context = result.get("error", "")[:500] + ('...' if len(result.get("error", "")) > 500 else '')


                # Construct the prompt for intermediate analysis
                intermediate_prompt = f"""
Context: We are troubleshooting the problem: "{problem_description}"

History of commands executed in *this session* so far:
{history_summary}

The *last* command attempted was:
`{cmd_str}`

Result:
- Executed: {result['executed']}
- Confirmed by user: {result['confirmed']}
- Success: {result['success']}
- Return Code: {result.get('return_code', 'N/A')}
- Output/Error (truncated to 500 chars):
Output: ```{output_context if output_context.strip() else '(empty)'}```
Error: ```{error_context if error_context.strip() else '(empty)'}```

Next *originally planned* command is: {next_planned_command_str}

**Your Task:**
1.  Analyze the outcome of the last command (`{cmd_str}`). What does this result tell us in the context of the problem and history? Consider both success/failure and the output/error content.
2.  Based *only* on this outcome and the history, decide the best next step:
    a.  **Proceed:** Continue with the next planned command ({next_planned_command_str}). Is it still relevant and safe given the last result?
    b.  **Suggest New:** The current plan seems flawed or a better step is indicated by the last result. Suggest the *single* next command to try using the format [[*** new_command_here ***]]. Explain why this new command is better than proceeding.
    c.  **Stop/Ask:** The plan needs rethinking, requires manual user action (like interpreting GUI output from msinfo32, checking BIOS), or the last error is critical and needs specific user attention. Recommend stopping the automated sequence.

Provide a *brief* explanation for your recommendation (1-2 sentences).
**Start your response clearly with ONE of the keywords:** `PROCEED`, `SUGGEST_NEW`, or `STOP`.

Example Response (Proceed):
PROCEED. The 'where' command found chkdsk, so running it is the correct next step.

Example Response (Suggest New):
SUGGEST_NEW. The chkdsk command failed with access denied. Let's try running sfc /scannow first to check system files before retrying chkdsk. [[*** sfc /scannow ***]]

Example Response (Stop):
STOP. The driverquery output shows very old drivers. The user should manually check the manufacturer website for updates before we continue.
"""
                # Call the LLM for intermediate analysis
                analysis_response = ask_llm(intermediate_prompt, model)

                next_action = "stop" # Default action if LLM fails or is unclear

                if analysis_response:
                    print_info("\nLLM Intermediate Analysis:")
                    print_md(analysis_response)

                    # Determine LLM's recommended action based on keywords at the start of the response
                    response_lower_strip = analysis_response.lower().strip()
                    if response_lower_strip.startswith("proceed"):
                        next_action = "proceed"
                        print_info("LLM recommends proceeding with the original plan.")
                    elif response_lower_strip.startswith("suggest_new"):
                        # Try extracting command only if action is SUGGEST_NEW
                        new_commands = extract_commands_from_llm_response(analysis_response)
                        if new_commands:
                            next_action = "suggest_new"
                            new_cmd_info = new_commands[0] # Take the first new command
                            print_warning(f"LLM suggests running `{new_cmd_info['value']}` instead of the next planned step.")
                        else:
                            print_warning("LLM said 'SUGGEST_NEW' but didn't provide a command like [[*** ... ***]]. Stopping.")
                            next_action = "stop"
                    elif response_lower_strip.startswith("stop"):
                         next_action = "stop"
                         print_warning("LLM recommends stopping the current automated sequence.")
                    else:
                         print_warning("LLM response didn't start clearly with PROCEED, SUGGEST_NEW, or STOP. Defaulting to STOP.")
                         next_action = "stop"

                else:
                    print_error("Failed to get intermediate analysis from LLM. Stopping execution sequence.")
                    next_action = "stop"


                # --- Act on LLM's Recommendation ---
                if next_action == "proceed":
                    current_command_index += 1 # Move to next planned command
                    continue # Continue the loop
                elif next_action == "suggest_new":
                    # Ask user to confirm the LLM's suggested new command
                    if RICH_AVAILABLE and Confirm:
                         run_new = Confirm.ask(f"Execute the LLM's suggested new command: `{new_cmd_info['value']}`?", default=True)
                    else:
                         run_new = input(f"Execute LLM's suggested new command: `{new_cmd_info['value']}`? [Y/n]: ").lower().strip() != 'n'

                    if run_new:
                         # Inject the new command *right after* the current one
                         # The rest of the original plan remains after the injected command
                         print_info(f"Inserting new step suggested by LLM: `{new_cmd_info['value']}`")
                         executable_commands.insert(current_command_index + 1, new_cmd_info)
                         # No need to update command_indices_map as we only care about the sequence now
                         current_command_index += 1 # Move index to the newly inserted command for next iteration
                         continue # Continue loop to run the new command
                    else:
                         print_info("User rejected LLM's suggested new command. Stopping execution sequence.")
                         break # Stop if user rejects suggestion
                elif next_action == "stop":
                     print_info("Stopping execution sequence based on LLM analysis or error.")
                     break # Exit the while loop

            elif is_last_command and result["success"]:
                 # Last command of the original (or modified) plan succeeded
                 print_success("\n✅ Final planned command executed successfully.")
                 # Optionally, add a final summary prompt here if needed
                 # final_summary_prompt = f"The troubleshooting sequence completed. History:\n{history_summary}\nProvide a brief summary and potential next steps if the issue isn't resolved."
                 # final_analysis = ask_llm(final_summary_prompt, model)
                 # if final_analysis: print_md(final_analysis)


        else: # Command was not executed (e.g., user cancelled confirmation in run_command)
            print_warning(f"Command `{cmd_str}` was not executed by user choice. Stopping execution sequence.")
            break # Exit the while loop

    # End of while loop
    print_info("\n--- Finished Interactive Command Execution ---")
    if current_command_index < len(executable_commands) and proceed: # Check if loop was broken early
        print_warning("Execution sequence was stopped before completing all planned steps.")

    # Print a summary of executed commands
    if session_command_history:
        print_info("\nSummary of executed commands:")
        for cmd in session_command_history:
            print_info(f"- `{cmd}`")


def handle_problem_description(memory: Dict[str, Any], system_report: Dict[str, Any],
                              model: Optional[str]) -> Optional[str]: # Allow model to be None, Return Optional[str]
    """
    Get problem description from user, trigger LLM analysis, store the issue,
    and initiate the interactive response handling.

    Args:
        memory: The current assistant memory.
        system_report: The collected system report.
        model: The selected LLM model name (or None if not available).

    Returns:
        The analysis string from the LLM, or None if analysis fails or is skipped.
    """
    problem = "" # Initialize

    # Get problem description input from user
    if RICH_AVAILABLE:
        try:
            problem = Prompt.ask("[bold yellow]Please describe the problem you're experiencing[/bold yellow]")
        except Exception as e: # Handle potential prompt errors (e.g., console issues)
             print_error(f"Error getting input via Rich prompt: {e}. Falling back to basic input.")
             # Fallback to basic input if Rich fails
             try:
                 problem = input("Please describe the problem you're experiencing: ")
             except EOFError:
                 print_warning("\nInput cancelled.")
                 return None # Exit if input is cancelled
    else:
        # Basic input if Rich is not available
        try:
            problem = input("Please describe the problem you're experiencing: ")
        except EOFError:
            print_warning("\nInput cancelled.")
            return None # Exit if input is cancelled

    # Check if user provided any input
    if not problem.strip():
        print_warning("No problem description provided. Skipping analysis.")
        return None # Return None if description is empty

    # Store the described issue in memory *before* analysis starts
    issue = {
        "timestamp": datetime.datetime.now().isoformat(),
        "description": problem,
        "resolved": False # Default to unresolved when first described
    }
    # Ensure memory is updated correctly
    try:
         memory = add_to_memory_list(memory, "previous_issues", issue)
         # save_memory(memory) # add_to_memory_list should handle saving
    except Exception as mem_e:
         print_error(f"Failed to save initial problem description to memory: {mem_e}")
         # Continue execution even if memory save fails for this step


    # Proceed with analysis only if an LLM model is available
    if model and OLLAMA_AVAILABLE:
        print_info("Analyzing problem, please wait...")
        # Call the analysis function (ensure it's defined before this point)
        analysis = analyze_problem(problem, system_report, memory, model)

        # Process the LLM response (display analysis, extract commands, start interactive execution)
        if analysis:
            # Call handler (ensure it's defined before this point)
            # handle_llm_response handles displaying the analysis and starting interaction
            handle_llm_response(analysis, problem, model)
            return analysis # Return the analysis string
        else:
            print_warning("LLM analysis did not return a result.")
            return None # Return None if analysis failed
    else:
        # Handle case where LLM is not available
        print_warning("LLM model not available. Cannot perform automated analysis.")
        print_info("You can still use the interactive mode to manually run commands ('run: your command') or tools ('execute toolname').")
        return None # No analysis performed

def interactive_mode(memory: Dict[str, Any], system_report: Dict[str, Any], model: str) -> None:
    """Start interactive mode for continued conversation and command execution."""
    print_info("Entering interactive mode. You can:")
    print("  - Ask follow-up questions")
    print("  - Request to run specific commands")
    print("  - Type 'scan' to perform a new system scan")
    print("  - Type 'suggest' to get command suggestions")
    print("  - Type 'execute' followed by a command name to run Windows tools")
    print("  - Type 'paste_image' to save a screenshot from clipboard and reference it")
    print("  - Type 'exit' to quit")
    
    # Store the problem description for suggestion context
    problem_description = ""
    if memory.get("previous_issues") and memory["previous_issues"]:
        problem_description = memory["previous_issues"][0].get("description", "")
    
    while True:
        if RICH_AVAILABLE:
            user_input = Prompt.ask("[bold yellow]What would you like to do?[/bold yellow]")
        else:
            user_input = input("\nWhat would you like to do? ")
        
        user_input = user_input.strip()
        user_input_lower = user_input.lower()
        
        if user_input_lower in ["exit", "quit"]:
            print_success("Exiting PC Fixer. Goodbye!")
            break
        
        elif user_input_lower == "scan":
            system_report = handle_system_scan()
            memory["system_info"] = system_report
            save_memory(memory)
        
        elif user_input_lower == "suggest":
            # Suggest commands based on the problem description
            if not problem_description:
                print_warning("No problem description available for suggestions.")
                continue
                
            print_info(f"Suggesting commands for: {problem_description}")
            suggestions = handle_suggestions(problem_description)
            
            if not suggestions:
                print_warning("No specific suggestions available for this problem type.")
                continue
                
            print_info("Here are some commands that might help diagnose the issue:")
            for i, suggestion in enumerate(suggestions, 1):
                cmd_str = " ".join(suggestion["command"])
                print(f"{i}. {cmd_str}")
                print(f"   Purpose: {suggestion['purpose']}")
                

        elif user_input_lower.startswith("analyze"):
            prompt = user_input[len("analyze"):].strip()
            if not prompt:
                prompt = print_user_input("Enter your question or context for the image:")
            image_paths = memory.get("image_paths", [])
            if image_paths:
                try:
                    response = llm_client.chat(
                        model=model,
                        messages=[{
                            'role': 'user',
                            'content': prompt,
                            'images': image_paths
                        }]
                    )
                    print_md(response['message']['content'])
                    memory["image_paths"] = []  # Clear after use
                except Exception as e:
                    print_error(f"Error sending image to LLM: {e}")
            else:
                print_warning("No image attached. Use 'paste_image' first.")



        # --- Clipboard Screenshot Paste Command ---
        elif user_input_lower == "paste_image":
            img_path = save_clipboard_image()
            if img_path:
                if "image_paths" not in memory:
                    memory["image_paths"] = []
                memory["image_paths"].append(img_path)
                print_info(f"Image ready for next LLM analysis: {img_path}")


            if RICH_AVAILABLE:
                selection = Prompt.ask("Enter the number of the command to run, or '0' to cancel", default="0")
            else:
                selection = input("Enter the number of the command to run, or '0' to cancel [0]: ") or "0"
                
            try:
                idx = int(selection) - 1
                if idx >= 0 and idx < len(suggestions):
                    cmd = suggestions[idx]["command"]
                    purpose = suggestions[idx]["purpose"]
                    
                    # Execute the selected command
                    result = run_command(
                        cmd,
                        capture_output=True,
                        shell=False,
                        require_confirmation=True,
                        explanation=purpose
                    )
                    
                    if result["executed"] and result["success"]:
                        print_info("Command output:")
                        print(result["output"])
                        
                        # Ask LLM to analyze the output
                        print_info("Analyzing command output...")
                        analysis_prompt = f"""
The user ran the command: {' '.join(cmd)}
For the problem: "{problem_description}"

Command output:
{result["output"]}

Please analyze this output and explain:
1. What does this output tell us about the problem?
2. Are there any concerning findings or anomalies?
3. What should the user do next based on this information?

IMPORTANT: If you need to suggest specific commands to run, please format them using [[*** command ***]] syntax.
For example: [[*** sfc /scannow ***]]

This special formatting helps the system identify commands that can be executed.
If multiple commands should be run in sequence, list them in order with the special formatting for each command.

Keep your analysis concise and focused on actionable insights.
"""
                        analysis = ask_llm(analysis_prompt, model)
                        if analysis:
                            # Process the analysis response for any new commands
                            handle_llm_response(analysis, problem_description or user_input, model)
                        
                    # Add to command history
                    if result["executed"]:
                        memory = add_to_memory_list(memory, "command_history", {
                            "timestamp": datetime.datetime.now().isoformat(),
                            "command": " ".join(cmd),
                            "success": result["success"]
                        })
            except ValueError:
                print_error("Please enter a valid number.")
        
        elif user_input_lower.startswith("run:"):
            # Direct command execution
            cmd = user_input[4:].strip()
            if not cmd:
                print_error("No command specified.")
                continue
            
            # Split command into list, respecting quotes
            import shlex
            try:
                cmd_list = shlex.split(cmd)
                # Execute with confirmation
                result = run_command(
                    cmd_list,
                    capture_output=True,
                    shell=False,
                    require_confirmation=True
                )
                
                if result["executed"] and result["success"]:
                    print_info("Command output:")
                    print(result["output"])
                
                # Add to command history
                if result["executed"]:
                    memory = add_to_memory_list(memory, "command_history", {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "command": cmd,
                        "success": result["success"]
                    })
            except Exception as e:
                print_error(f"Error parsing command: {e}")
        
        elif user_input_lower.startswith("execute "):
            # Execute Windows built-in tools
            cmd = user_input[8:].strip()
            if not cmd:
                print_error("No command specified.")
                continue
            
            # Windows commands that can be executed directly
            windows_commands = {
                "msinfo32": "System Information Tool",
                "dxdiag": "DirectX Diagnostic Tool",
                "devmgmt.msc": "Device Manager",
                "eventvwr.msc": "Event Viewer",
                "services.msc": "Services Manager",
                "taskmgr": "Task Manager",
                "perfmon": "Performance Monitor",
                "winver": "Windows Version Info",
                "control": "Control Panel"
            }
            
            if cmd.lower() in windows_commands:
                print_info(f"Executing {windows_commands[cmd.lower()]}...")
                try:
                    import os
                    os.system(f"start {cmd}")
                    print_success(f"Started {cmd}. Check for an open window.")
                    
                    # Add to command history
                    memory = add_to_memory_list(memory, "command_history", {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "command": f"start {cmd}",
                        "success": True
                    })
                except Exception as e:
                    print_error(f"Error starting {cmd}: {e}")
            else:
                print_error(f"Unknown or unsupported Windows command: {cmd}")
                print_info("Supported commands: " + ", ".join(windows_commands.keys()))
        
        else:
            # Treat as a follow-up question
            print_info("Analyzing your question...")
            
            # Create a follow-up prompt
            prompt = f"""
Previous user issue: "{problem_description}"

New question/request: "{user_input}"

Based on the system information and previous context, please respond to this follow-up. 
If the user is asking to run a specific command, explain what the command does and its purpose before recommending it.

IMPORTANT: If you need to suggest specific commands to run, please format them using [[*** command ***]] syntax.
For example: [[*** sfc /scannow ***]]

This special formatting helps the system identify commands that can be executed.
If multiple commands should be run in sequence, list them in order with the special formatting for each command.
"""
            response = ask_llm(prompt, model)
            if response:
                # Process the response, allowing command execution
                handle_llm_response(response, problem_description or user_input, model)




def extract_commands_from_llm_response(response: str) -> List[Dict[str, Any]]:
    """
    Extract commands and potentially other actionable items (like URLs)
    from LLM response using special formats. Ensures 'type' key is always present.
    """
    items = []
    # Command format: [[*** command ***]]
    command_pattern = r"\[\[\*\*\*\s*(.*?)\s*\*\*\*\]\]" # Added optional space trimming
    # URL format suggestion: [[URL: url ]] (Case-insensitive)
    url_pattern = r"\[\[URL:\s*(https?://[^\s\]]+)\s*\]\]" # More specific URL pattern

    # --- Find URLs first ---
    url_matches = re.finditer(url_pattern, response, re.IGNORECASE)
    processed_indices = set() # Track processed parts of the string

    for match in url_matches:
        url_text = match.group(1).strip()
        start_pos, end_pos = match.span()

        # Mark this region as processed
        for i in range(start_pos, end_pos):
            processed_indices.add(i)

        # Basic context extraction (sentence before)
        context_start = max(0, start_pos - 200)
        context_text = response[context_start:start_pos].strip()
        sentences = re.split(r'[.!?]\s+', context_text)
        context = sentences[-1].strip() if sentences else context_text

        # Ensure dictionary structure is complete
        items.append({
            "type": "url", # Explicitly set type
            "value": url_text,
            "context": context if context else "No context found.",
            "original_match_position": start_pos
        })

    # --- Find Commands, avoiding already processed URL regions ---
    command_matches = re.finditer(command_pattern, response)

    for match in command_matches:
        start_pos, end_pos = match.span()

        # Check if this match overlaps with a processed URL region
        is_overlapped = False
        for i in range(start_pos, end_pos):
            if i in processed_indices:
                is_overlapped = True
                break
        if is_overlapped:
            continue # Skip if it's part of a URL tag we already handled

        cmd_text = match.group(1).strip()
        if not cmd_text:
            continue

        # Context extraction
        context_start = max(0, start_pos - 200)
        context_text = response[context_start:start_pos].strip()
        sentences = re.split(r'[.!?]\s+', context_text)
        context = sentences[-1].strip() if sentences else context_text

        # --- Determine item type ---
        item_type = "command" # Default type
        try:
            # Use shlex.split to handle quoted commands before checking first word
            cmd_first_word = shlex.split(cmd_text)[0].lower()
        except Exception: # Catch shlex errors or empty strings
             cmd_first_word = cmd_text.split()[0].lower() if cmd_text.split() else "" # Fallback

        if platform.system() == "Windows" and cmd_first_word in ["which", "sudo", "apt", "yum", "dnf", "apt-get"]:
             item_type = "invalid_command" # Mark as potentially invalid
        # Map known tools that aren't direct commands but executables
        elif "memory diagnostic" in cmd_text.lower() or "mdsched" in cmd_text.lower():
             item_type = "command"
             cmd_text = "mdsched.exe" # Map to the actual executable
        elif not cmd_text: # Handle empty command after stripping
             item_type = "error" # Mark as an error if extraction resulted in empty command
             print_warning(f"Extracted empty command string at position {start_pos}.")
             cmd_text = "[EMPTY COMMAND]" # Assign placeholder value

        # Ensure dictionary structure is complete before appending
        items.append({
            "type": item_type, # Ensure type is always assigned
            "value": cmd_text,
            "context": context if context else "No context found.",
            "original_match_position": start_pos
        })

    # --- Final Safety Check ---
    # Although unlikely with the above logic, double-check if any item is missing 'type'
    for i, item in enumerate(items):
        if "type" not in item:
             print_error(f"CRITICAL ERROR: Item at index {i} is missing 'type' key after extraction! Item: {item}")
             # Assign a default error type to prevent crash downstream
             item["type"] = "error"
             item["value"] = item.get("value", "[UNKNOWN VALUE]")
             item["context"] = item.get("context", "Extraction error occurred.")
             item["original_match_position"] = item.get("original_match_position", -1)


    # Sort items based on their appearance order in the response
    items.sort(key=lambda x: x["original_match_position"])

    return items


# =============================================================================
# Main Application Functions
# =============================================================================

def display_welcome() -> None:
    """Display welcome message and application info."""
    title = "PC Fixer - Intelligent Technical Assistant"

    if RICH_AVAILABLE:
        console.print(Panel.fit(f"[bold green]{title}[/bold green]"))
        console.print("[bold cyan]A local AI-powered tool for diagnosing and fixing PC problems[/bold cyan]")
        console.print("[dim](Running locally and securely - your data stays on your machine)[/dim]")
    else:
        print("=" * 60)
        print(title.center(60))
        print("A local AI-powered tool for diagnosing and fixing PC problems".center(60))
        print("(Running locally and securely - your data stays on your machine)".center(60))
        print("=" * 60)

def handle_system_scan() -> Dict[str, Any]:
    """Perform a system scan and return the report."""
    print_info("Starting system scan. This will collect information about your system for diagnosis...")
    report = generate_system_report()
    print_success("System scan completed.")
    return report

# =============================================================================
# LLM Auto Health Report
# =============================================================================

def llm_auto_health_report(system_report: dict, model: str) -> None:
    """
    Generate and display a proactive LLM health report based on system and log status, before user input.
    """
    logs = system_report.get("recent_logs", [])
    log_patterns = analyze_logs_for_patterns(logs)

    # Format log patterns for LLM consumption
    patterns_text = ""
    if log_patterns.get("suspicious_apps"):
        patterns_text += f"- Suspicious applications mentioned: {', '.join(log_patterns['suspicious_apps'])}\n"
    if log_patterns.get("app_crashes"):
        patterns_text += f"- Application crash events detected: {len(log_patterns['app_crashes'])}\n"
    if log_patterns.get("service_failures"):
        patterns_text += f"- Service failure events detected: {len(log_patterns['service_failures'])}\n"
    if log_patterns.get("driver_issues"):
        patterns_text += f"- Potential driver issue events detected: {len(log_patterns['driver_issues'])}\n"
    if log_patterns.get("permission_errors"):
        patterns_text += f"- Permission error events detected: {len(log_patterns['permission_errors'])}\n"
    if log_patterns.get("disk_errors"):
        patterns_text += f"- Potential disk error events detected: {len(log_patterns['disk_errors'])}\n"
    if log_patterns.get("frequent_sources"):
        top_sources = list(log_patterns["frequent_sources"].items())[:5]
        patterns_text += "- Most frequent error/warning sources:\n"
        for source, data in top_sources:
            levels = ', '.join(data['levels'])
            patterns_text += f"  - {source}: {data['count']} occurrences (Levels: {levels})\n"
    if log_patterns.get("error_clusters"):
        patterns_text += "- Significant error clusters (time periods with high error counts):\n"
        for cluster in log_patterns["error_clusters"][:3]:
            patterns_text += f"  - {cluster['count']} errors between {cluster['start']} and {cluster['end']}\n"
    if not patterns_text:
        patterns_text = "No specific error patterns detected in the analyzed logs."

    # Format a sample of logs for context
    logs_text = ""
    if logs:
        logs_text = "**Recent System Logs (up to 15 most recent errors/warnings/critical):**\n"
        logs_text += "\n".join(
            f"- [{log.get('TimeCreated', 'N/A')}] Lvl: {log.get('Level', 'N/A')} Src: {log.get('ProviderName', 'N/A')} ID: {log.get('Id','N/A')} | {log.get('Message', 'N/A')}"
            for log in logs[:15]
        )
    else:
        logs_text = "**Recent System Logs:**\nNo recent system logs found or collected."

    # OS information
    os_info = system_report.get("os_info", {})
    os_name = os_info.get('OS Name', os_info.get('system', 'Unknown'))
    os_version = os_info.get('OS Version', os_info.get('version', 'Unknown'))
    os_arch = os_info.get('System Type', os_info.get('architecture', 'Unknown'))
    os_info_text = f"OS: {os_name} {os_version} ({os_arch})"

    # Compose the health report prompt
    prompt = f"""
You are an expert PC troubleshooting assistant running locally on the user's machine.

The following is a summary of the current system and log status. The user has NOT yet described any specific problem. Based on the information below, provide:
- An overall health assessment of the system
- Any warnings or risks you detect
- Any urgent or notable errors
- Suggestions for what the user should check, even if no problem is reported
- Format your response using Markdown.

---
📊 **System Information:**
{os_info_text}
{('Motherboard: '+ system_report.get('hardware_info', {}).get('Motherboard', {}).get('Manufacturer', '') + ' ' + system_report.get('hardware_info', {}).get('Motherboard', {}).get('Product', '')) if system_report.get('hardware_info', {}).get('Motherboard') else ''}
{('CPU: '+ system_report.get('hardware_info', {}).get('CPU', {}).get('Name', 'N/A')) if system_report.get('hardware_info', {}).get('CPU') else ''}

---
📉 **Log Analysis Patterns:**
{patterns_text}

---
{logs_text}
---

🎯 **Your Task:**
1. Analyze the system and logs above and provide a health report and any proactive recommendations.
2. If you detect urgent errors, highlight them clearly.
3. If the system appears healthy, say so, but mention any minor warnings.
4. Do NOT ask the user for a problem description yet. Just report your findings.
"""

    # Query the LLM and display the result
    print_info("\n[LLM] Analyzing system status and logs for a proactive health report...")
    analysis = ask_llm(prompt, model, system_message="You are a helpful and cautious PC diagnostic assistant providing a proactive health report.")
    if analysis:
        print_md("\n[LLM SYSTEM HEALTH REPORT]\n" + analysis)
    else:
        print_warning("LLM did not return a health report.")

# =============================================================================
# Stepwise LLM Health Report (Modular, Memory-based)
# =============================================================================
def stepwise_auto_health_report(system_report: dict, model: str, memory: dict) -> None:
    """
    Run each diagnostic step, summarize with LLM, store intermediate summaries, and then synthesize a final health report.
    """
    diagnostic_steps = [
        ("Operating System Info", lambda: system_report.get("os_info", {})),
        ("Hardware Info", lambda: system_report.get("hardware_info", {})),
        ("Network Info", lambda: system_report.get("network_info", {})),
        ("Event Logs", lambda: system_report.get("recent_logs", [])),
        ("Log Patterns", lambda: analyze_logs_for_patterns(system_report.get("recent_logs", []))),
    ]
    intermediate_summaries = []
    total_steps = len(diagnostic_steps)

    for idx, (title, func) in enumerate(diagnostic_steps, 1):
        print_step(f"Stepwise Diagnostic: {title}", f"Running {title}...", idx, total_steps)
        raw_data = func()
        # Format the prompt for the LLM for each step
        if title == "Event Logs":
            logs = raw_data
            logs_text = "\n".join(
                f"- [{log.get('TimeCreated', 'N/A')}] Lvl: {log.get('Level', 'N/A')} Src: {log.get('ProviderName', 'N/A')} ID: {log.get('Id','N/A')} | {log.get('Message', 'N/A')}"
                for log in logs[:15]
            ) if logs else "No recent logs."
            prompt = f"""
            You are a PC diagnostic assistant. Here are recent system event logs. Summarize any critical errors, warnings, or notable patterns. Be concise and actionable.\n\nLogs:\n{logs_text}"
            """
        elif title == "Log Patterns":
            patterns = raw_data
            patterns_text = ""
            if patterns.get("suspicious_apps"):
                patterns_text += f"- Suspicious applications: {', '.join(patterns['suspicious_apps'])}\n"
            if patterns.get("app_crashes"):
                patterns_text += f"- Application crashes: {len(patterns['app_crashes'])}\n"
            if patterns.get("service_failures"):
                patterns_text += f"- Service failures: {len(patterns['service_failures'])}\n"
            if patterns.get("driver_issues"):
                patterns_text += f"- Driver issues: {len(patterns['driver_issues'])}\n"
            if patterns.get("permission_errors"):
                patterns_text += f"- Permission errors: {len(patterns['permission_errors'])}\n"
            if patterns.get("disk_errors"):
                patterns_text += f"- Disk errors: {len(patterns['disk_errors'])}\n"
            if not patterns_text:
                patterns_text = "No notable log patterns."
            prompt = f"""
            You are a PC diagnostic assistant. Here are detected log patterns. Summarize their health significance and any urgent findings.\n\nPatterns:\n{patterns_text}"
            """
        else:
            prompt = f"""
            You are a PC diagnostic assistant. Here is {title} data. Summarize any health risks or important findings.\n\nData:\n{json.dumps(raw_data, indent=2)}"
            """
        step_summary = ask_llm(prompt, model, system_message=f"You are a helpful PC diagnostic assistant. Summarize {title} for a health report.")
        if step_summary:
            print_md(f"\n[LLM SUMMARY: {title}]\n" + step_summary)
            intermediate_summaries.append({"step": title, "summary": step_summary})
        else:
            print_warning(f"LLM did not return a summary for {title}.")
            intermediate_summaries.append({"step": title, "summary": "No summary returned."})
        # Save each intermediate summary to memory
        memory = add_to_memory_list(memory, "health_report_summaries", {"step": title, "summary": step_summary}, max_items=10)
        save_memory(memory)

    # Final synthesis step
    print_step("Final Synthesis", "Aggregating all stepwise summaries for a holistic health report.", None, None)
    all_summaries_text = "\n\n".join(f"[{item['step']}]\n{item['summary']}" for item in intermediate_summaries)
    final_prompt = f"""
    You are a PC troubleshooting assistant. Here are stepwise health summaries from different diagnostic checks. Synthesize them into a single, holistic health report. Highlight urgent issues, cross-reference findings, and provide clear recommendations.\n\n{all_summaries_text}\n\nRespond in Markdown."
    """
    final_report = ask_llm(final_prompt, model, system_message="You are a helpful PC diagnostic assistant. Synthesize all stepwise summaries into a final health report.")
    if final_report:
        print_md("\n[LLM FINAL HEALTH REPORT]\n" + final_report)
        memory = add_to_memory_list(memory, "health_report_summaries", {"step": "Final Synthesis", "summary": final_report}, max_items=10)
        save_memory(memory)
    else:
        print_warning("LLM did not return a final health report.")

# --- Integrate into main() ---
def main() -> None:
    """Main application entry point."""
    display_welcome()

    # Check dependencies
    if not OLLAMA_AVAILABLE:
        print_error("Ollama Python library not found. LLM features will be disabled.")
        print_info("Install with: pip install ollama")

    if not RICH_AVAILABLE:
        print_warning("Rich library not found. Using plain text interface.")
        print_info("For a better experience, install with: pip install rich")
    elif Confirm is None: # Specifically check if Confirm is missing even if rich is present
         print_warning("Rich library's Confirm prompt not available. Using basic input for confirmations.")


    # Load memory
    memory = load_memory()
    memory["last_session"] = datetime.datetime.now().isoformat()
    save_memory(memory)

    # Check if Ollama is available for LLM features
    llm_available = False
    model = None

    if OLLAMA_AVAILABLE:
        models = list_ollama_models()
        if models:
            model = select_model(models) # Let user select model
            if model and llm_client: # Check client also initialized
                llm_available = True
                print_success(f"Using model: {model}")
            elif model:
                print_error("Model selected, but Ollama client failed to initialize earlier.")
                llm_available = False
            else:
                print_warning("No model selected by user.")
                llm_available = False
        else:
            print_warning("No Ollama models found or could not be listed. LLM features will be disabled.")

    # Perform system scan *after* potentially initializing run_command dependencies
    system_report = handle_system_scan()
    memory["system_info"] = system_report
    save_memory(memory)

    # Generate proactive LLM health report
    if llm_available and model:
        stepwise_auto_health_report(system_report, model, memory)

    # If LLM is available, proceed with problem analysis
    if llm_available and model: # Ensure model is selected
        # Get problem description which then calls handle_llm_response
        handle_problem_description(memory, system_report, model)
        # Note: handle_problem_description now implicitly calls handle_llm_response
        # No need to print analysis separately here if handle_llm_response displays it.

    else:
        print_info("\nSystem information has been collected.")
        if not OLLAMA_AVAILABLE:
             print_warning("Automated analysis is not available because Ollama is not installed or configured.")
        elif not model:
             print_warning("Automated analysis is not available because no LLM model was selected or found.")
        print_info("You can still use the interactive mode to manually run commands ('run: your command') or tools ('execute toolname').")


    # Enter interactive mode regardless of initial analysis outcome
    # Pass the latest memory, report, and selected model (even if None)
    interactive_mode(memory, system_report, model)



if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_success("\nPC Fixer terminated by user. Goodbye!")
    except Exception as e:
        print_error(f"An unexpected error occurred in main execution: {e}")
        # Print detailed traceback
        print("--- TRACEBACK ---")
        traceback.print_exc()
        print("--- END TRACEBACK ---")
        print_info("Please report this issue with the above error details.")
        sys.exit(1) # Exit with error code
