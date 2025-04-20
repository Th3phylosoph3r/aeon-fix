
# Semantic Map: AEON PC Fixer (`aeon_fix.py`)

## 1. System Overview

-   **Project Classification**: Local command-line PC diagnostic and troubleshooting assistant.
-   **Domain-Specific Patterns**:
    -   Interactive Assistant: Engages user via prompts and feedback.
    -   Diagnosis Engine: Uses system information and logs, potentially augmented by an LLM, to identify issues.
    -   Command Executor: Executes system commands based on analysis or user input.
    -   Stateful Interaction: Maintains memory of past issues and commands.
-   **System Boundaries**:
    -   **Inputs**:
        -   User text descriptions of problems.
        -   User confirmations (Y/N).
        -   User selections from lists (e.g., LLM model).
        -   User commands in interactive mode.
        -   System information gathered via OS commands.
        -   System logs.
        -   Ollama LLM responses (optional).
        -   Configuration constants (`CONFIG`).
    -   **Outputs**:
        -   Text output to console (diagnostic messages, analysis, command output, errors, informational messages - potentially formatted with `rich`).
        -   System commands executed via `subprocess`.
        -   Data written to `assistant_memory.json` and `pc_fix_logs.json`.
        -   API calls to Ollama server (optional).
        -   Opening URLs in a web browser.
    -   **External Interfaces**:
        -   Operating System (via `subprocess`, `os`, `platform`, `shutil`).
        -   File System (reading/writing memory and log files).
        -   Ollama HTTP API (`http://localhost:11434` by default, optional).
        -   Web Browser (via `webbrowser`).
-   **Deployment Environment**: Local user machine (Windows, Linux supported).
-   **Technology Stack**:
    -   Language: Python 3
    -   Core Libraries: `subprocess`, `json`, `re`, `os`, `platform`, `datetime`, `sys`, `time`, `shutil`, `typing`, `traceback`, `shlex`, `webbrowser`.
    -   Optional Libraries: `ollama` (for LLM interaction), `rich` (for enhanced terminal UI).

## 2. Component Registry

---

**@ComponentID `CONFIG` [L32-46]**
-   **Purpose**: Global configuration dictionary holding file paths, Ollama settings, and command safety lists.
-   **Signature**: `Dict[str, Union[str, List[str]]]` → `(Immutable)`
-   **Statefulness**: `stateless` (constants)
-   **Dependencies**: None
-   **Role in Domain**: Configuration provider.

---

**@ComponentID `Console/Print Helpers` [L49-60]**
-   **Purpose**: Provide stylized console output (Info, Success, Warning, Error, Markdown) using `rich` if available, otherwise basic `print`.
-   **Signature**: `(message: str) -> None`
-   **Statefulness**: `stateless` (depends on `RICH_AVAILABLE` flag set at startup)
-   **Dependencies**: External: `rich` (optional)
-   **Role in Domain**: User Interface Output.

---

**@ComponentID `LLM Client Initialization` [L63-69]**
-   **Purpose**: Initialize the Ollama client (`ollama.Client`) if the library is available and the host is configured. Handles potential initialization errors.
-   **Signature**: `() -> Optional[ollama.Client]`
-   **Statefulness**: `stateful:{llm_client, OLLAMA_AVAILABLE}` (global variables)
-   **Dependencies**: External: `ollama` (optional), `CONFIG`. Internal: `print_error`.
-   **Role in Domain**: LLM Interface Setup.

---

**@ComponentID `load_memory` [L75-89]**
-   **Purpose**: Load the assistant's persistent state (previous issues, system info, command history) from the JSON file specified in `CONFIG`. If the file doesn't exist or fails to load, initializes a default structure.
-   **Signature**: `() -> Dict[str, Any]`
-   **Statefulness**: `stateless` (reads external state)
-   **Dependencies**: External: `os`, `json`, `CONFIG`. Internal: `print_error`.
-   **Role in Domain**: State Management (Load).

---

**@ComponentID `save_memory` [L91-97]**
-   **Purpose**: Save the provided memory dictionary to the JSON file specified in `CONFIG`.
-   **Signature**: `(memory: Dict[str, Any]) -> None`
-   **Statefulness**: `stateless` (writes external state)
-   **Dependencies**: External: `json`, `CONFIG`. Internal: `print_error`.
-   **Role in Domain**: State Management (Save).

---

**@ComponentID `update_memory` [L99-104]**
-   **Purpose**: Update a specific key-value pair in the memory dictionary and save the entire structure.
-   **Signature**: `(memory: Dict[str, Any], key: str, value: Any) -> Dict[str, Any]`
-   **Statefulness**: `stateless` (modifies and saves external state via `save_memory`)
-   **Dependencies**: Internal: `save_memory`.
-   **Role in Domain**: State Management (Update).

---

**@ComponentID `add_to_memory_list` [L106-119]**
-   **Purpose**: Add an item to the beginning of a list stored in memory under a specific key, ensuring the list does not exceed a maximum size. Saves the updated memory.
-   **Signature**: `(memory: Dict[str, Any], key: str, value: Any, max_items: int = 20) -> Dict[str, Any]`
-   **Statefulness**: `stateless` (modifies and saves external state via `save_memory`)
-   **Dependencies**: Internal: `save_memory`.
-   **Role in Domain**: State Management (Append to List).

---

**@ComponentID `log_action` [L125-145]**
-   **Purpose**: Append a structured log entry (timestamp, action type, success status, details) to the JSON log file specified in `CONFIG`. Handles file reading/writing errors.
-   **Signature**: `(action_type: str, details: Dict[str, Any], success: bool = True) -> None`
-   **Statefulness**: `stateless` (appends to external log file)
-   **Dependencies**: External: `datetime`, `json`, `os`, `CONFIG`. Internal: `print_error`.
-   **Role in Domain**: Auditing/Logging.

---

**@ComponentID `get_os_info` [L151-198]**
-   **Purpose**: Gather basic operating system information (System, Version, Release, Architecture) and augment with platform-specific details (OS Name, Memory, Distribution for Linux) using system commands.
-   **Signature**: `() -> Dict[str, str]`
-   **Statefulness**: `stateless` (reads system state via commands)
-   **Dependencies**: External: `platform`, `os`. Internal: `run_command`, `print_warning`, `print_error`.
-   **Design Pattern**: Platform-specific Strategy.
-   **Role in Domain**: System Information Gathering.

---

**@ComponentID `get_hardware_info` [L200-273]**
-   **Purpose**: Gather hardware information (CPU, Disks, Motherboard) using platform-specific commands (`wmic` on Windows, `/proc/cpuinfo`, `lsblk` on Linux).
-   **Signature**: `() -> Dict[str, Any]`
-   **Statefulness**: `stateless` (reads system state via commands)
-   **Dependencies**: External: `platform`, `json`, `os`. Internal: `run_command`, `print_warning`, `print_error`.
-   **Design Pattern**: Platform-specific Strategy.
-   **Role in Domain**: System Information Gathering.

---

**@ComponentID `get_network_info` [L275-312]**
-   **Purpose**: Gather network configuration information (`ipconfig /all` on Windows, `ip addr`, `ip route`, `/etc/resolv.conf` on Linux).
-   **Signature**: `() -> Dict[str, Any]`
-   **Statefulness**: `stateless` (reads system state via commands)
-   **Dependencies**: External: `platform`, `os`. Internal: `run_command`, `print_warning`, `print_error`.
-   **Design Pattern**: Platform-specific Strategy.
-   **Role in Domain**: System Information Gathering.

---

**@ComponentID `collect_system_logs` [L314-426]**
-   **Purpose**: Collect recent system event logs (Windows Event Logs via PowerShell, Linux journalctl or common log files), focusing on errors and warnings, and standardize the format.
-   **Signature**: `(max_logs: int = 50) -> List[Dict[str, Any]]`
-   **Statefulness**: `stateless` (reads system state via commands/files)
-   **Dependencies**: External: `platform`, `shutil`, `subprocess`, `json`, `datetime`, `traceback`, `os`. Internal: `run_command`, `print_error`, `print_warning`.
-   **Design Pattern**: Platform-specific Strategy, Fallback Mechanism (journalctl -> log files).
-   **Complexity**: Potentially high I/O depending on log access method. PowerShell/journalctl command execution time varies. Log parsing complexity is moderate.
-   **Critical Path**: Yes, crucial for diagnosis.
-   **Role in Domain**: System Information Gathering, Diagnosis Data Source.

---

**@ComponentID `analyze_logs_for_patterns` [L428-499]**
-   **Purpose**: Analyze a list of collected log entries to identify common patterns like application crashes, service failures, driver issues, permission errors, disk errors, frequent error sources, and potentially problematic applications based on keywords and source names.
-   **Signature**: `(logs: List[Dict[str, Any]]) -> Dict[str, Any]`
-   **Statefulness**: `stateless`
-   **Dependencies**: External: `datetime`. Internal: `find_time_clusters`.
-   **Complexity**: O(N * M) where N is number of logs and M is average number of keywords/apps to check.
-   **Role in Domain**: Diagnosis Engine (Log Analysis).

---

**@ComponentID `find_time_clusters` [L501-542]**
-   **Purpose**: Identify time periods where errors occurred frequently based on hourly timestamps, grouping events within a maximum gap.
-   **Signature**: `(timestamps: Dict[str, int], min_cluster_size: int = 3, max_gap_hours: int = 1) -> List[Dict[str, Any]]`
-   **Statefulness**: `stateless`
-   **Dependencies**: External: `datetime`. Internal: `print_warning`.
-   **Complexity**: O(N log N) due to sorting, where N is the number of unique timestamps.
-   **Role in Domain**: Log Analysis Helper.

---

**@ComponentID `generate_system_report` [L545-561]**
-   **Purpose**: Consolidate information from OS, hardware, network, and log gathering functions into a single comprehensive report dictionary.
-   **Signature**: `() -> Dict[str, Any]`
-   **Statefulness**: `stateless` (orchestrates state reading)
-   **Dependencies**: External: `datetime`, `sys`, `json`. Internal: `print_info`, `get_os_info`, `get_hardware_info`, `get_network_info`, `collect_system_logs`, `log_action`.
-   **Critical Path**: Yes, provides context for LLM analysis.
-   **Role in Domain**: System Information Aggregation.

---

**@ComponentID `is_dangerous_command` [L567-588]**
-   **Purpose**: Check if a given command string matches predefined patterns of potentially dangerous commands or is explicitly listed as a safe diagnostic command. Leans towards caution.
-   **Signature**: `(cmd_str: str) -> bool`
-   **Statefulness**: `stateless`
-   **Dependencies**: Internal: `CONFIG`.
-   **Role in Domain**: Safety Check.

---

**@ComponentID `run_command` [L591-710]**
-   **Purpose**: Execute a system command securely and robustly. Handles list vs. string commands (`shell=False` vs `shell=True`), optional user confirmation (mandatory for dangerous commands), output capturing, platform-specific encoding, error reporting, and logging.
-   **Signature**: `(command: Union[List[str], str], capture_output: bool = True, shell: bool = False, require_confirmation: bool = True, explanation: str = None) -> Dict[str, Any]`
-   **Statefulness**: `stateless` (interacts with OS and user)
-   **Dependencies**: External: `subprocess`, `platform`, `time`, `shlex`, `traceback`, `rich` (optional for Confirm). Internal: `is_dangerous_command`, `print_info`, `print_warning`, `print_error`, `print_success`, `log_action`, `Confirm`.
-   **Critical Path**: Yes, core function for executing diagnostics and fixes.
-   **Role in Domain**: Command Execution Engine, Safety Enforcement.

---

**@ComponentID `_list_ollama_models_cli` [L716-750]**
-   **Purpose**: Helper function to list available Ollama models by executing the `ollama list` command via `run_command`. Used as a fallback if the API method fails.
-   **Signature**: `() -> List[str]`
-   **Statefulness**: `stateless` (interacts with OS)
-   **Dependencies**: External: `traceback`. Internal: `run_command`, `print_info`, `print_warning`, `print_error`.
-   **Role in Domain**: LLM Setup Helper.

---

**@ComponentID `list_ollama_models` [L769-827]**
-   **Purpose**: List available Ollama models, preferably using the Ollama Python client API. Includes robust error checking and falls back to the CLI helper (`_list_ollama_models_cli`) if the API fails or returns unexpected data.
-   **Signature**: `() -> List[str]`
-   **Statefulness**: `stateless` (interacts with Ollama API or CLI)
-   **Dependencies**: External: `traceback`. Internal: `OLLAMA_AVAILABLE`, `llm_client`, `print_info`, `print_error`, `print_warning`, `_list_ollama_models_cli`.
-   **Critical Path**: Yes, for enabling LLM features.
-   **Role in Domain**: LLM Setup.

---

**@ComponentID `select_model` [L829-861]**
-   **Purpose**: Prompt the user to select an Ollama model from a provided list using numbered choices. Handles invalid input.
-   **Signature**: `(models: List[str]) -> Optional[str]`
-   **Statefulness**: `stateless` (interacts with user)
-   **Dependencies**: External: `rich` (optional for Prompt). Internal: `print_info`, `print_error`, `print_success`, `print_warning`, `Prompt`.
-   **Role in Domain**: LLM Setup, User Interaction.

---

**@ComponentID `ask_llm` [L864-896]**
-   **Purpose**: Send a prompt (optionally with a system message) to the selected Ollama model using the client API. Handles API errors and returns the LLM's response content.
-   **Signature**: `(prompt: str, model: str, system_message: str = None) -> Optional[str]`
-   **Statefulness**: `stateless` (interacts with Ollama API)
-   **Dependencies**: External: `traceback`. Internal: `OLLAMA_AVAILABLE`, `llm_client`, `print_info`, `print_error`, `log_action`.
-   **Critical Path**: Yes, for LLM-driven analysis and suggestions.
-   **Role in Domain**: LLM Interaction.

---

**@ComponentID `analyze_problem` [L899-1042]**
-   **Purpose**: Construct a detailed prompt for the LLM to analyze a user-reported problem. The prompt includes the problem description, formatted system information, log analysis patterns, recent logs, previous issues from memory, and specific instructions for the LLM on how to structure its response (diagnosis, sequential commands using `[[*** ... ***]]` format).
-   **Signature**: `(problem_description: str, system_report: Dict[str, Any], memory: Dict[str, Any], model: str) -> Optional[str]`
-   **Statefulness**: `stateless` (reads state from inputs)
-   **Dependencies**: Internal: `analyze_logs_for_patterns`, `log_action`, `ask_llm`.
-   **Role in Domain**: Diagnosis Engine (LLM Query Formulation).

---

**@ComponentID `extract_commands_from_llm_response` [L1045-1133]** (Note: Duplicated definition in source, using the second one L1345-1422)
-   **Purpose**: Parse the LLM's text response to find and extract actionable items marked with special syntax: commands (`[[*** command ***]]`) and URLs (`[[URL: url]]`). Determines command type (valid, invalid_command, error) and extracts context.
-   **Signature**: `(response: str) -> List[Dict[str, Any]]`
-   **Statefulness**: `stateless`
-   **Dependencies**: External: `re`, `shlex`, `platform`. Internal: `print_warning`, `print_error`.
-   **Role in Domain**: LLM Response Parsing.

---

**@ComponentID `handle_llm_response` [L1136-1338]**
-   **Purpose**: Orchestrates the interaction following an LLM analysis. It displays the LLM response, extracts actionable items, handles non-command items (like opening URLs), and then enters an *interactive loop* to execute suggested commands one by one. After each command execution, it can optionally trigger an *intermediate LLM analysis* to decide whether to proceed, suggest a new command, or stop the sequence. Handles pre-execution checks (`where`), command parsing (`shlex`), determines `shell=True/False`, calls `run_command`, updates memory, and manages the execution flow based on command success and LLM feedback.
-   **Signature**: `(response: str, problem_description: str, model: str) -> None`
-   **Statefulness**: `stateful:{session_command_history}` (local state during execution), interacts with global `memory`.
-   **Dependencies**: External: `webbrowser`, `platform`, `shlex`, `datetime`, `rich` (optional for Confirm). Internal: `print_md`, `extract_commands_from_llm_response`, `print_info`, `print_warning`, `print_error`, `print_success`, `log_action`, `Confirm`, `run_command`, `load_memory`, `add_to_memory_list`, `save_memory`, `ask_llm`.
-   **Design Pattern**: Interactive Loop, State Machine (Implicit: Execute -> Analyze -> Decide -> Execute/Stop).
-   **Critical Path**: Yes, implements the core interactive diagnostic/fix loop.
-   **Role in Domain**: Interaction Controller, Execution Orchestrator, LLM Feedback Loop.

---

**@ComponentID `handle_problem_description` [L1341-1389]**
-   **Purpose**: Prompts the user for a problem description, stores it in memory, and (if LLM is available) triggers the `analyze_problem` function, subsequently calling `handle_llm_response` to process the analysis and initiate interaction.
-   **Signature**: `(memory: Dict[str, Any], system_report: Dict[str, Any], model: Optional[str]) -> Optional[str]`
-   **Statefulness**: `stateless` (reads user input, orchestrates state changes via other functions)
-   **Dependencies**: External: `datetime`, `rich` (optional for Prompt). Internal: `print_info`, `print_warning`, `print_error`, `Prompt`, `add_to_memory_list`, `OLLAMA_AVAILABLE`, `analyze_problem`, `handle_llm_response`.
-   **Critical Path**: Yes, entry point for LLM-driven workflow.
-   **Role in Domain**: User Interaction, Workflow Initiation.

---

**@ComponentID `interactive_mode` [L1391-1500]** (Note: Contains call to a missing `handle_suggestions` and uses `run:` prefix not fully handled elsewhere)
-   **Purpose**: Provides a loop for the user to interact after the initial analysis (or if no analysis was performed). Allows asking follow-up questions (sent to LLM), requesting a new system scan, running manual commands (`run: ...` or `execute ...`), or exiting. Intends to offer command suggestions (via missing `handle_suggestions`).
-   **Signature**: `(memory: Dict[str, Any], system_report: Dict[str, Any], model: str) -> None`
-   **Statefulness**: `stateful:{problem_description}` (local state), interacts with global `memory`, `system_report`.
-   **Dependencies**: External: `rich` (optional for Prompt), `shlex`, `os`. Internal: `print_info`, `print_success`, `print_warning`, `print_error`, `Prompt`, `handle_system_scan`, `save_memory`, `run_command`, `add_to_memory_list`, `ask_llm`, `handle_llm_response`.
-   **Design Pattern**: REPL (Read-Eval-Print Loop).
-   **Role in Domain**: User Interaction, Manual Control.
-   **Note**: Logic for `suggest` relies on a non-existent `handle_suggestions`. Logic for `run:` uses `shlex` and `run_command`. Logic for `execute` uses `os.system(start ...)` for specific GUI tools.

---

**@ComponentID `display_welcome` [L1428-1440]**
-   **Purpose**: Display a welcome banner and application information, using `rich` formatting if available.
-   **Signature**: `() -> None`
-   **Statefulness**: `stateless`
-   **Dependencies**: External: `rich` (optional). Internal: `RICH_AVAILABLE`, `console`.
-   **Role in Domain**: User Interface (Startup).

---

**@ComponentID `handle_system_scan` [L1442-1447]**
-   **Purpose**: Wrapper function to initiate a system scan and display start/completion messages.
-   **Signature**: `() -> Dict[str, Any]`
-   **Statefulness**: `stateless` (orchestrates state reading)
-   **Dependencies**: Internal: `print_info`, `generate_system_report`, `print_success`.
-   **Role in Domain**: Workflow Step (Scan).

---

**@ComponentID `main` [L1453-1490]**
-   **Purpose**: Main application entry point. Handles initialization (welcome message, dependency checks, memory loading), LLM setup (model listing and selection), initial system scan, triggers the problem description/analysis flow, and finally enters the interactive mode.
-   **Signature**: `() -> None`
-   **Statefulness**: `stateful:{memory, system_report, model}` (manages top-level state)
-   **Dependencies**: Internal: `display_welcome`, `OLLAMA_AVAILABLE`, `RICH_AVAILABLE`, `Confirm`, `print_error`, `print_warning`, `print_info`, `print_success`, `load_memory`, `save_memory`, `datetime`, `list_ollama_models`, `select_model`, `llm_client`, `handle_system_scan`, `handle_problem_description`, `interactive_mode`.
-   **Role in Domain**: Application Orchestrator.

---

**@ComponentID `main_entry_guard` [L1493-1502]**
-   **Purpose**: Standard Python entry guard (`if __name__ == "__main__":`). Calls `main()` and includes top-level exception handling (KeyboardInterrupt, general Exception) with traceback printing.
-   **Signature**: `() -> None`
-   **Statefulness**: `stateless`
-   **Dependencies**: External: `sys`, `traceback`. Internal: `main`, `print_success`, `print_error`, `print_info`.
-   **Role in Domain**: Application Entry Point.

## 3. Algorithmic Abstractions

**@AlgoID `LogPatternAnalysis` [L428-499]**
-   **Intent**: Identify recurring issues or significant event types within system logs.
-   **Approach**:
    1. Initialize counters/lists for various patterns (crashes, services, drivers, permissions, disks, frequent sources, suspicious apps).
    2. Define keyword lists associated with each pattern type.
    3. Iterate through each log entry.
    4. Convert log message and source to lowercase for case-insensitive matching.
    5. Increment count for the log source.
    6. Record the hour timestamp of the log entry.
    7. Check if log message contains keywords for each pattern type; if match, add log entry to corresponding list.
    8. Check if message or source contains names of known problematic applications; if match, add app name to a set.
    9. Sort frequent sources by count.
    10. Call `find_time_clusters` to group errors by time.
-   **Edge Cases**: Logs with missing message/source/timestamp; variations in log message phrasing.
-   **Invariants**: Output structure contains keys for all defined patterns.
-   **Performance**: Primarily O(N * K) where N is log count and K is total number of keywords/apps checked.

**@AlgoID `TimeClusterDetection` [L501-542]**
-   **Intent**: Group log events that occur close together in time.
-   **Approach**:
    1. Parse timestamp strings (expecting "%Y-%m-%d %H" format) into datetime objects. Skip unparseable ones.
    2. Sort timestamp-count pairs chronologically.
    3. Iterate through sorted timestamps:
        - If no active cluster, start a new one with the current event.
        - If an active cluster exists, check the time difference between the current event and the cluster's end time.
        - If the difference is within `max_gap_hours`, extend the current cluster (update end time, add count).
        - If the difference exceeds the gap, finalize the previous cluster (if its count >= `min_cluster_size`) and start a new cluster with the current event.
    4. Finalize the last active cluster if it meets the size requirement.
    5. Sort resulting clusters by count (descending).
-   **Edge Cases**: Empty input; timestamps not in expected format; all events too far apart; all events within one cluster.
-   **Invariants**: Output is a list of clusters, each with start/end times and count. Clusters are sorted by count.
-   **Performance**: Dominated by sorting, O(N log N) where N is number of unique timestamps.

**@AlgoID `CommandExtraction` [L1045-1133]** (using L1345-1422 definition)
-   **Intent**: Extract specially formatted commands and URLs from LLM text response.
-   **Approach**:
    1. Use regex (`url_pattern`) to find all `[[URL: ...]]` matches first. Store URL, context (preceding text), and position. Mark matched indices as processed.
    2. Use regex (`command_pattern`) to find all `[[*** ... ***]]` matches.
    3. For each command match, check if its position overlaps with an already processed URL region; skip if it does.
    4. Extract the command text, trim whitespace.
    5. Extract context (preceding text).
    6. Determine command type:
        - Default to `command`.
        - If first word (parsed with `shlex`) matches common Linux commands on Windows, set type to `invalid_command`.
        - If command maps to a known executable (e.g., "memory diagnostic" -> "mdsched.exe"), update command text and ensure type is `command`.
        - If extracted command is empty, set type to `error`.
    7. Store type, value, context, and position for each valid command/URL item.
    8. Perform final safety check to ensure all items have a 'type'.
    9. Sort all extracted items by their original position in the text.
-   **Edge Cases**: Nested or malformed `[[***` / `[[URL:` markers; commands/URLs spanning multiple lines (regex might handle some cases); empty extracted command string; `shlex.split` errors.
-   **Invariants**: Output is a list of dictionaries, each having `type`, `value`, `context`, `original_match_position`, sorted by position.
-   **Performance**: Depends on regex efficiency and response length, generally linear O(L) where L is response length.

**@AlgoID `InteractiveCommandLoop` [L1136-1338]** (within `handle_llm_response`)
-   **Intent**: Execute a sequence of LLM-suggested commands interactively, allowing for intermediate analysis and plan adjustment.
-   **Approach**:
    1. Extract initial command sequence from LLM response.
    2. Present sequence to user.
    3. Loop through executable commands (using an index `current_command_index`):
        a. Display current command and its purpose.
        b. (Windows) Pre-check: Use `where` to verify command existence if it's not a known built-in. Ask user whether to proceed if not found. Skip command if user declines.
        c. Determine `shell=True/False` based on command syntax (pipes, redirection, etc.) or `shlex` parsing success. Use `shlex.split` if possible.
        d. Execute command using `run_command` (which handles confirmation).
        e. Record execution result in session history and persistent memory (`command_history`).
        f. If command executed:
            i. Display success/failure and output/error (truncated).
            ii. If command failed OR it's not the last command in the sequence:
                - Prepare context (history, last result, next planned command).
                - Call `ask_llm` for intermediate analysis (Prompt asks LLM to recommend PROCEED, SUGGEST_NEW, or STOP).
                - Parse LLM recommendation.
                - If `PROCEED`: Increment `current_command_index`.
                - If `SUGGEST_NEW`: Extract new command, confirm with user, insert it into the sequence after the current index, increment `current_command_index`.
                - If `STOP` (or LLM error/unclear): Break the loop.
            iii. Else (last command succeeded): Print final success message, break loop.
        g. Else (command not executed, e.g., user cancelled confirmation): Break the loop.
    4. Indicate if loop finished early or completed.
-   **Edge Cases**: LLM provides no commands; `run_command` fails unexpectedly; LLM intermediate analysis fails or provides invalid recommendation; user cancels confirmations repeatedly; `shlex` fails parsing.
-   **Invariants**: Commands are executed sequentially unless the LLM analysis or user action alters the flow. State (`memory`, `session_command_history`) is updated accordingly.
-   **Performance**: Dominated by command execution times and LLM response times. Loop iterations depend on initial plan length and LLM adjustments.

## 4. Data Flow Model

**@DataFlow_SystemScan**
-   **Source**: OS (Hardware, Network, OS Info, Logs)
-   **Transformations**:
    -   `get_os_info`, `get_hardware_info`, `get_network_info`, `collect_system_logs` execute platform-specific commands/read files via `run_command`.
    -   Output from commands/files is parsed into structured dictionaries/lists.
    -   `generate_system_report` aggregates results into a single report dictionary.
-   **Sink**: `system_report` variable in memory, `memory["system_info"]` in `assistant_memory.json`.
-   **Trigger**: `handle_system_scan()` call (initially in `main`, or user request 'scan' in `interactive_mode`).

**@DataFlow_InitialProblemAnalysis**
-   **Source**: User input (problem description), `system_report`, `memory` (previous issues, command history).
-   **Transformations**:
    -   `analyze_logs_for_patterns` processes `system_report["recent_logs"]`.
    -   `analyze_problem` formats a detailed prompt string incorporating user input, system info, log patterns, sample logs, and history.
    -   `ask_llm` sends the prompt to the Ollama API.
    -   Ollama API generates a response text.
-   **Sink**: `analysis` string variable passed to `handle_llm_response`.
-   **Trigger**: User providing problem description in `handle_problem_description` when LLM is available.

**@DataFlow_LLMResponseHandling**
-   **Source**: `analysis` string (LLM response).
-   **Transformations**:
    -   `extract_commands_from_llm_response` parses the string for `[[*** ... ***]]` and `[[URL: ...]]`.
    -   `handle_llm_response` loop iterates through extracted commands.
    -   `run_command` executes a command.
    -   Command output/error is captured.
    -   (Optional) `ask_llm` performs intermediate analysis based on command result and history.
    -   (Optional) `extract_commands_from_llm_response` parses intermediate analysis for new commands.
-   **Sink**:
    -   Commands executed on OS via `run_command`.
    -   URLs opened in browser via `webbrowser`.
    -   Console output (LLM text, command results, messages).
    -   Updates to `memory["command_history"]`.
-   **Trigger**: Receiving a non-empty `analysis` string in `handle_llm_response`.

**@DataFlow_InteractiveModeQuery**
-   **Source**: User input text in interactive mode.
-   **Transformations**:
    -   Input compared against keywords ('scan', 'suggest', 'execute', 'exit', 'run:').
    -   If question: Format prompt for `ask_llm` including context (`problem_description`).
    -   If `run:`: Parse command using `shlex`, execute via `run_command`.
    -   If `execute`: Use `os.system(start ...)` for specific tools.
    -   If 'scan': Trigger `@DataFlow_SystemScan`.
    -   LLM response (if applicable) processed by `handle_llm_response`.
-   **Sink**: Console output, OS commands/processes, updates to `memory`.
-   **Trigger**: User input within the `interactive_mode` loop.

**@DataFlow_Logging**
-   **Source**: Various functions (e.g., `generate_system_report`, `run_command`, `ask_llm`, `handle_llm_response`).
-   **Transformations**: `log_action` formats action details into a JSON object with timestamp and success status.
-   **Sink**: Appends JSON entry to `pc_fix_logs.json`.
-   **Trigger**: Calls to `log_action`.

**@DataFlow_MemoryPersistence**
-   **Source**: In-memory `memory` dictionary.
-   **Transformations**: `save_memory` serializes the dictionary to JSON. `load_memory` deserializes JSON from file.
-   **Sink**: `assistant_memory.json` file.
-   **Trigger**: Calls to `save_memory` (within `update_memory`, `add_to_memory_list`, `main`, `handle_system_scan`, `handle_problem_description`, `handle_llm_response`). Call to `load_memory` at startup in `main`.

## 5. Control Flow Graph (CFG)

(High-level Mermaid representation)


graph TD
    Start[Start Application] --> MainGuard{if __name__ == "__main__"};
    MainGuard -- Yes --> Main[main];
    MainGuard -- No --> End[Exit];

    Main --> Welcome[display_welcome];
    Welcome --> DepCheck{Check Ollama/Rich};
    DepCheck --> LoadMem[load_memory];
    LoadMem --> OllamaSetup{Ollama Available?};

    OllamaSetup -- Yes --> ListModels[list_ollama_models];
    ListModels --> SelectModel[select_model];
    SelectModel --> ModelSelected{Model Chosen?};
    ModelSelected -- Yes --> LLMAvailable[llm_available = True];
    ModelSelected -- No --> LLMNotAvailable[llm_available = False];
    OllamaSetup -- No --> LLMNotAvailable;

    LLMAvailable --> SysScan1[handle_system_scan];
    LLMNotAvailable --> SysScan2[handle_system_scan];

    SysScan1 --> ProblemDesc[handle_problem_description];
    ProblemDesc --> ProblemEntered{Desc Provided?};
    ProblemEntered -- Yes --> Analyze[analyze_problem];
    Analyze --> AnalysisResult{Analysis Received?};
    AnalysisResult -- Yes --> HandleResp[handle_llm_response];
    AnalysisResult -- No --> WarnNoAnalysis1[Warn: No Analysis];

    ProblemEntered -- No --> WarnNoDesc[Warn: No Description];


    SysScan2 --> InfoCollected[Info: SysInfo Collected];
    InfoCollected --> WarnNoAnalysis2[Warn: LLM Not Available];

    HandleResp --> Interactive[interactive_mode];
    WarnNoAnalysis1 --> Interactive;
    WarnNoDesc --> Interactive;
    WarnNoAnalysis2 --> Interactive;

    Interactive --> UserInput{Get Input};
    UserInput -- exit --> End;
    UserInput -- scan --> SysScan3[handle_system_scan];
    SysScan3 --> Interactive;
    UserInput -- suggest --> SuggestCmd[Suggest Commands]; %% Missing handle_suggestions logic
    SuggestCmd --> ExecSuggestion{Execute Suggested?};
    ExecSuggestion -- Yes --> RunSuggested[run_command];
    RunSuggested --> AnalyzeOutput[ask_llm (analyze output)];
    AnalyzeOutput --> HandleRespSuggest[handle_llm_response];
    HandleRespSuggest --> Interactive;
    ExecSuggestion -- No --> Interactive;

    UserInput -- run: cmd --> ParseRunCmd[shlex.split];
    ParseRunCmd --> RunDirect[run_command];
    RunDirect --> Interactive;

    UserInput -- execute tool --> StartTool[os.system(start tool)];
    StartTool --> Interactive;

    UserInput -- other --> AskLLMFollowup[ask_llm];
    AskLLMFollowup --> HandleRespFollowup[handle_llm_response];
    HandleRespFollowup --> Interactive;


    subgraph handle_llm_response
        direction LR
        StartHandle[Start] --> ExtractItems[extract_commands...];
        ExtractItems --> NonCmd{Handle URLs etc.};
        NonCmd --> ExecLoop{Interactive Cmd Loop};
        ExecLoop -- Command Exists --> PreCheck{where check (Win)};
        PreCheck -- Found/Skip --> ParseCmd[shlex.split / Use shell];
        ParseCmd --> RunCmd[run_command];
        RunCmd --> Executed{Executed?};
        Executed -- Yes --> Result{Success?};
        Result -- Yes --> IsLast{Last Cmd?};
        IsLast -- Yes --> EndLoop[End Loop];
        IsLast -- No --> IntermediateAnalysis{Ask LLM (Intermediate)};
        Result -- No --> IntermediateAnalysis;

        IntermediateAnalysis --> LLMDecision{PROCEED/SUGGEST_NEW/STOP};
        LLMDecision -- PROCEED --> ExecLoop;
        LLMDecision -- SUGGEST_NEW --> InjectCmd[Inject New Command];
        InjectCmd --> ExecLoop;
        LLMDecision -- STOP --> EndLoop;

        Executed -- No (User Cancelled) --> EndLoop;
        PreCheck -- Not Found & User Skip --> ExecLoop; %% Skips current command
    end

    Main --> EndOnException[Catch Exception];
    EndOnException --> PrintTraceback[Print Traceback];
    PrintTraceback --> ExitError[Exit(1)];
    Main --> End;


## 6. State Transition Models

**@StateMap_Memory (`assistant_memory.json`)**

-   **States**: Represents the persistent knowledge of the assistant between runs. Not a state machine in the typical sense, but evolves over time.
-   **Data**:
    -   `last_session`: ISO timestamp of the last run.
    -   `previous_issues`: List of dictionaries, each containing `timestamp`, `description`, `resolved` (boolean). Max 20 items, newest first.
    -   `system_info`: Dictionary containing the last collected system report (`os_info`, `hardware_info`, `network_info`, `recent_logs`).
    -   `command_history`: List of dictionaries, each containing `timestamp`, `command` (string), `success` (boolean), `return_code`. Max 20 items, newest first.
-   **Transitions**:
    -   `Load`: On startup (`main`), `load_memory` reads the file into the `memory` variable. Initializes default if fails.
    -   `Update Last Session`: In `main`, `last_session` is updated.
    -   `Update System Info`: In `main` and `interactive_mode ('scan')`, `handle_system_scan` generates a report which overwrites `memory["system_info"]`.
    -   `Add Issue`: In `handle_problem_description`, a new issue dict is added to `memory["previous_issues"]` via `add_to_memory_list`.
    -   `Add Command History`: In `handle_llm_response` and `interactive_mode`, successfully executed commands are added to `memory["command_history"]` via `add_to_memory_list`.
-   **Persisted Data**: Entire `memory` dictionary is saved via `save_memory` after most transitions.
-   **Restoration/Recovery**: On load error (`load_memory`), initializes to a default empty state. No complex recovery.

## 7. Interface Contracts

**@Interface_OSCommandExecutor**
-   **Provider**: `run_command` function.
-   **Methods**:
    -   `run_command(command: Union[List[str], str], ..., require_confirmation: bool = True)`
        -   **Parameters**: Command (list or string), capture_output, shell, require_confirmation, explanation.
        -   **Returns**: Dict with `success`, `output`, `error`, `return_code`, `executed`, `confirmed`, `execution_time`.
        -   **Pre-conditions**: Command string/list provided. `shlex` available if parsing needed. Confirmation mechanism available (rich or input).
        -   **Post-conditions**: Command attempted execution (if confirmed). Result dictionary returned. Action logged via `log_action`. Memory updated if executed.
-   **Consumers**: `get_os_info`, `get_hardware_info`, `get_network_info`, `collect_system_logs`, `_list_ollama_models_cli`, `handle_llm_response`, `interactive_mode`.
-   **Protocol**: `subprocess.run`.

**@Interface_FileSystem**
-   **Provider**: `load_memory`, `save_memory`, `log_action`, `get_os_info` (Linux), `get_network_info` (Linux).
-   **Methods**:
    -   Read JSON (`load_memory`, `log_action` - read existing).
    -   Write JSON (`save_memory`, `log_action` - write updated).
    -   Read Text Files (`/etc/os-release`, `/proc/meminfo`, `/proc/cpuinfo`, `/etc/resolv.conf`, `/var/log/*`).
    -   Check File Existence (`os.path.exists`).
-   **Consumers**: `main`, `update_memory`, `add_to_memory_list`, System Info functions, Logging function.
-   **Protocol**: Standard file I/O (`open`, `json.load`, `json.dump`, `os.path.exists`).

**@Interface_OllamaAPI**
-   **Provider**: `ollama.Client` instance (`llm_client`).
-   **Methods**:
    -   `llm_client.list()`: Lists available models.
    -   `llm_client.chat(model, messages)`: Sends chat completion request.
-   **Consumers**: `list_ollama_models`, `ask_llm`.
-   **Protocol**: HTTP requests to Ollama server endpoint (e.g., `http://localhost:11434/api/tags`, `http://localhost:11434/api/chat`).
-   **Message Structures**: JSON request/response bodies defined by Ollama API.

**@Interface_UserConsole**
-   **Provider**: `print_*` functions, `rich.Console`, `rich.Prompt`, `rich.Confirm`, `input()`.
-   **Methods**:
    -   Display Formatted Text/Markdown (`print_info`, `print_md`, etc.).
    -   Request Text Input (`Prompt.ask`, `input`).
    -   Request Confirmation (`Confirm.ask`, `input`).
-   **Consumers**: Most functions interacting with the user (`display_welcome`, `select_model`, `run_command`, `handle_problem_description`, `interactive_mode`).
-   **Protocol**: Standard Input/Output streams, potentially enhanced by `rich`.

**@Interface_WebBrowser**
-   **Provider**: `webbrowser` module.
-   **Methods**: `webbrowser.open(url)`.
-   **Consumers**: `handle_llm_response` (when URL extracted).
-   **Protocol**: OS-level mechanism to open default web browser.

## 8. Critical Functions

**@TradingFunction_RunCommand (`run_command`) [L591-710]** (Using domain label loosely for "critical function")
-   **Purpose**: Executes system commands, forming the basis for diagnostics and potential fixes.
-   **Impact**: High - Directly interacts with the OS, can gather info or make changes.
-   **Failure Modes**: Command not found (`FileNotFoundError`), execution error (non-zero exit code), timeout (`subprocess.TimeoutExpired`), permission errors, decoding errors, unexpected exceptions. User cancellation during confirmation.
-   **Reliability Concerns**: Depends on correct command syntax, PATH environment variable, OS permissions, stability of the executed command. Encoding detection (`chcp`) might fail. `shell=True` poses security risks if not used carefully.
-   **Semantics**: Validates input type based on `shell` flag, performs safety check (`is_dangerous_command`), requests confirmation if needed, executes using `subprocess.run`, captures/decodes output/error, logs result, returns structured status.
-   **Recovery**: Catches specific exceptions (`FileNotFoundError`, `TimeoutExpired`) and general `Exception`, logs errors, returns failure status in dictionary. Does not automatically retry.

**@TradingFunction_AskLLM (`ask_llm`) [L864-896]**
-   **Purpose**: Queries the Ollama LLM for analysis or suggestions.
-   **Impact**: High - LLM responses drive the diagnostic process and command suggestions.
-   **Failure Modes**: Ollama server unreachable, API errors (invalid model, rate limits, server errors), network issues, `ollama` library exceptions, LLM produces unhelpful or incorrect response.
-   **Reliability Concerns**: Depends on Ollama server availability and performance, quality of the selected model, and clarity of the prompt.
-   **Semantics**: Checks prerequisites (`OLLAMA_AVAILABLE`, `llm_client`, `model`), constructs message list, calls `llm_client.chat`, extracts content from response, handles exceptions, logs action/error.
-   **Recovery**: Catches general `Exception`, logs error, returns `None`. No retry logic.

**@TradingFunction_HandleLLMResponse (`handle_llm_response`) [L1136-1338]**
-   **Purpose**: Orchestrates the core interactive loop based on LLM analysis, managing command execution and intermediate feedback.
-   **Impact**: High - Controls the flow of diagnosis and repair attempts.
-   **Failure Modes**: Errors in `extract_commands_from_llm_response`, errors during `run_command`, errors during intermediate `ask_llm` call, user repeatedly cancelling commands, LLM providing non-actionable advice or incorrect commands.
-   **Reliability Concerns**: Complexity of the state management (tracking command sequence, handling LLM feedback). Robustness depends heavily on the quality of LLM responses and the reliability of `run_command`. `where` check is Windows-only. `shlex.split` can fail.
-   **Semantics**: Displays initial response, extracts items, handles URLs, loops through commands: pre-checks, executes (`run_command`), analyzes result (optionally via LLM), decides next step (proceed, inject, stop) based on analysis/result, updates history.
-   **Recovery**: Catches exceptions within `run_command` and `ask_llm`. If intermediate analysis fails or recommends stop, the loop terminates. If command execution is cancelled by user, loop terminates.

**@TradingFunction_CollectSystemLogs (`collect_system_logs`) [L314-426]**
-   **Purpose**: Gathers potentially crucial diagnostic information from system logs.
-   **Impact**: High - Provides key context for identifying root causes.
-   **Failure Modes**: Required commands unavailable (PowerShell, journalctl, tail), insufficient permissions to read logs, errors parsing command output (JSON, text), log files non-existent or corrupt.
-   **Reliability Concerns**: Platform differences require separate logic. PowerShell script complexity. `journalctl` output format variations. Fallback log parsing (`tail` + keyword search) is imprecise. Log sorting depends on parseable timestamps.
-   **Semantics**: Uses platform-specific commands (PowerShell `Get-WinEvent`, `journalctl`, `tail`) via `run_command` to fetch recent error/warning logs. Parses output (JSON preferred) into a standardized list of dictionaries. Attempts to sort by time.
-   **Recovery**: Catches exceptions during command execution and parsing. Uses fallbacks (e.g., journalctl text if JSON fails, common log files if journalctl unavailable). Logs errors/warnings. Returns partial or empty list on failure.

## 9. Reconstruction Blueprint

1.  **Scaffold & Config**:
    -   Set up project structure (`pc_fix.py`).
    -   Define `CONFIG` dictionary.
    -   Implement basic `print_*` helpers (checking `RICH_AVAILABLE`).
    -   Implement `main` entry point (`if __name__ == "__main__":`) with basic exception handling.
    -   Implement `display_welcome`.
2.  **Core Utilities**:
    -   Implement Memory Management: `load_memory`, `save_memory`, `update_memory`, `add_to_memory_list`.
    -   Implement Logging: `log_action`.
    -   Implement Command Safety: `is_dangerous_command`.
    -   Implement Command Execution: `run_command` (crucial, handle shell, confirmation, output, errors, encoding).
3.  **System Information Gathering**:
    -   Implement `get_os_info` (with platform specifics).
    -   Implement `get_hardware_info` (with platform specifics).
    -   Implement `get_network_info` (with platform specifics).
    -   Implement `collect_system_logs` (with platform specifics and fallbacks).
    -   Implement `generate_system_report` to aggregate info.
    -   Implement `handle_system_scan` wrapper.
4.  **Log Analysis**:
    -   Implement `find_time_clusters`.
    -   Implement `analyze_logs_for_patterns`.
5.  **LLM Integration (Conditional)**:
    -   Add optional `ollama` and `rich` dependencies.
    -   Implement `LLM Client Initialization`.
    -   Implement `_list_ollama_models_cli`.
    -   Implement `list_ollama_models` (API primary, CLI fallback).
    -   Implement `select_model`.
    -   Implement `ask_llm`.
    -   Implement `analyze_problem` (constructs the detailed prompt).
    -   Implement `extract_commands_from_llm_response`.
6.  **Core Interaction Logic**:
    -   Implement `handle_llm_response` (displays response, extracts items, handles URLs, implements the interactive command execution loop with intermediate analysis).
    -   Implement `handle_problem_description` (gets user input, saves issue, triggers analysis and response handling).
    -   Implement `interactive_mode` (REPL for follow-up, manual commands, scan trigger - Note: requires fixing/implementing `handle_suggestions`).
7.  **Integration & Finalization**:
    -   Integrate all parts in `main`: Welcome -> Deps Check -> Load Mem -> Ollama Setup -> Scan -> Problem Desc -> Interactive Mode.
    -   Refine error handling and user feedback messages.
    -   Add unit/integration tests (consider mocking `subprocess`, `ollama`, `rich`).
    -   Provide sample `assistant_memory.json` structure.
    -   Document usage and dependencies.

**Reusable Modules/Ideas**: `run_command` is highly reusable. The system info gathering functions could be refactored into a platform-specific class/module. Log analysis logic is self-contained.

**Test Cases/Mock Data**:
-   Mock `subprocess.run` results (success, failure, specific output/error, timeouts).
-   Mock `ollama.Client` responses (valid analysis, responses without commands, responses with malformed commands, API errors).
-   Sample `assistant_memory.json` files (empty, populated).
-   Sample log snippets (Windows Event Log format, journalctl JSON/text, syslog format) containing various error patterns.
-   Mock user input/confirmations.

## 10. Semantic Indexing Metadata

-   **System Overall**: `pc-diagnostics`, `troubleshooting`, `cli-tool`, `local-ai`, `ollama-integration`, `system-scanner`, `command-executor`, `python`
-   **`run_command`**: `command-execution`, `subprocess`, `safety-check`, `user-confirmation`, `output-capture`, `error-handling`, `platform-encoding`, `critical-function`
-   **`collect_system_logs`**: `log-collection`, `event-log`, `journalctl`, `powershell`, `platform-specific`, `diagnosis-data`, `error-parsing`, `critical-function`
-   **`analyze_problem`**: `llm-prompting`, `problem-analysis`, `context-assembly`, `log-analysis`, `system-info`, `ollama`
-   **`handle_llm_response`**: `llm-interaction`, `command-extraction`, `interactive-loop`, `intermediate-analysis`, `workflow-orchestration`, `critical-function`, `state-machine`
-   **`analyze_logs_for_patterns`**: `log-analysis`, `pattern-matching`, `keyword-search`, `diagnosis-engine`, `error-correlation`
-   **Memory Functions (`load_memory`, `save_memory`, ...)**: `state-management`, `persistence`, `json`, `file-io`
-   **System Info Functions (`get_os_info`, ...)**: `system-information`, `hardware-info`, `os-info`, `network-info`, `platform-specific`, `wmic`, `lsblk`
-   **`interactive_mode`**: `repl`, `user-interface`, `manual-control`, `follow-up-query`

**Query Aliases**:
-   "How are commands executed?" -> `run_command`, `handle_llm_response`
-   "Where is system information stored?" -> `memory["system_info"]`, `generate_system_report`
-   "How does it analyze logs?" -> `analyze_logs_for_patterns`, `collect_system_logs`, `find_time_clusters`
-   "What talks to the LLM?" -> `ask_llm`, `analyze_problem`, `handle_llm_response`
-   "How does it suggest fixes?" -> `analyze_problem`, `handle_llm_response`, `extract_commands_from_llm_response`
-   "Is it safe?" -> `is_dangerous_command`, `run_command` (confirmation)
-   "How does it remember past problems?" -> `load_memory`, `save_memory`, `memory["previous_issues"]`
-   "Where is Ollama configured?" -> `CONFIG["ollama_host"]`, `LLM Client Initialization`
-   "How does it handle different OS?" -> `platform.system()`, `get_os_info`, `get_hardware_info`, `get_network_info`, `collect_system_logs`

## 11. Architectural Visualization (Mermaid)


graph LR
    subgraph User Interface
        CLI[Console (Rich/Basic)]
        UserInput[User Input/Prompts]
    end

    subgraph Core Logic
        Main[main]
        ProblemHandler[handle_problem_description]
        ResponseHandler[handle_llm_response]
        InteractiveMode[interactive_mode]
        CmdExtractor[extract_commands...]
        CmdRunner[run_command]
        SafetyCheck[is_dangerous_command]
    end

    subgraph Data Processing
        SysReportGen[generate_system_report]
        LogCollector[collect_system_logs]
        LogAnalyzer[analyze_logs_for_patterns]
        TimeCluster[find_time_clusters]
        SysInfoFuncs[get_os/hw/net_info]
    end

    subgraph State Management
        MemFuncs[load/save/update_memory]
        LogFunc[log_action]
        MemoryFile[(assistant_memory.json)]
        LogFile[(pc_fix_logs.json)]
    end

    subgraph External Interfaces
        OS[Operating System]
        Ollama[Ollama API]
        Browser[Web Browser]
    end

    %% Connections
    UserInput --> Main;
    UserInput --> ProblemHandler;
    UserInput --> InteractiveMode;
    UserInput --> CmdRunner; %% Confirmation

    CLI -- Displays Output --> UserInput; %% User sees output, provides input

    Main --> ProblemHandler;
    Main --> InteractiveMode;
    Main --> SysReportGen;
    Main --> MemFuncs;

    ProblemHandler --> LogAnalyzer; %% Uses analyze_logs_for_patterns internally for prompt
    ProblemHandler -- Triggers Analysis --> Ollama;
    Ollama -- Analysis Response --> ResponseHandler;
    ProblemHandler --> MemFuncs; %% Saves issue

    ResponseHandler --> CLI; %% Displays response
    ResponseHandler --> CmdExtractor;
    ResponseHandler --> CmdRunner;
    ResponseHandler -- Opens URLs --> Browser;
    ResponseHandler -- Intermediate Analysis --> Ollama;
    ResponseHandler --> MemFuncs; %% Saves cmd history

    InteractiveMode --> CLI;
    InteractiveMode --> SysReportGen;
    InteractiveMode --> CmdRunner;
    InteractiveMode -- Follow-up Query --> Ollama;
    InteractiveMode --> OS; %% execute command via os.system

    CmdExtractor --> ResponseHandler;

    CmdRunner --> SafetyCheck;
    CmdRunner --> OS; %% Executes command
    CmdRunner --> LogFunc;
    CmdRunner --> MemFuncs;

    SysReportGen --> SysInfoFuncs;
    SysReportGen --> LogCollector;
    SysReportGen --> LogFunc;

    LogCollector --> CmdRunner; %% Runs commands to get logs
    LogCollector --> OS; %% Reads log files
    LogCollector --> LogAnalyzer; %% Used by LogAnalyzer

    SysInfoFuncs --> CmdRunner; %% Run commands for info

    LogAnalyzer --> TimeCluster;
    LogAnalyzer --> SysReportGen; %% Included in report context

    MemFuncs --> MemoryFile;
    LogFunc --> LogFile;

    Main -- Initializes Ollama --> Ollama;




sequenceDiagram
    participant User
    participant PCFixerApp as Main Logic
    participant CmdRunner as run_command
    participant SysInfo as Info Gathering
    participant Analyzer as Log/Problem Analysis
    participant Ollama as Ollama Service
    participant Memory as State (memory.json)
    participant OS as Operating System

    User->>PCFixerApp: Start pc_fix.py
    PCFixerApp->>Memory: load_memory()
    Memory-->>PCFixerApp: Past state
    PCFixerApp->>SysInfo: handle_system_scan()
    SysInfo->>CmdRunner: Execute info commands (wmic, ipconfig, etc.)
    CmdRunner->>OS: Run commands
    OS-->>CmdRunner: Command Output
    CmdRunner-->>SysInfo: Parsed Info
    SysInfo->>PCFixerApp: System Report
    PCFixerApp->>Memory: save_memory(system_info)

    alt Ollama Available
        PCFixerApp->>User: Describe problem
        User->>PCFixerApp: Problem Description
        PCFixerApp->>Memory: add_to_memory_list(issue)
        PCFixerApp->>Analyzer: analyze_problem(desc, report, memory)
        Analyzer->>Ollama: ask_llm(prompt)
        Ollama-->>Analyzer: LLM Response Text
        Analyzer-->>PCFixerApp: Analysis String
        PCFixerApp->>PCFixerApp: handle_llm_response(analysis)
        PCFixerApp->>User: Display Analysis & Actions
        loop Interactive Command Execution
            PCFixerApp->>CmdRunner: Execute next command (with confirm)
            CmdRunner->>User: Confirm Execution?
            User->>CmdRunner: Yes/No
            opt User Confirms Yes
                CmdRunner->>OS: Run command
                OS-->>CmdRunner: Output/Error
                CmdRunner-->>PCFixerApp: Result (Success/Fail, Output)
                PCFixerApp->>Memory: add_to_memory_list(command_history)
                PCFixerApp->>User: Display Result
                alt Command Failed or Not Last
                    PCFixerApp->>Analyzer: ask_llm(intermediate analysis prompt)
                    Analyzer->>Ollama: ask_llm()
                    Ollama-->>Analyzer: Recommendation (PROCEED/SUGGEST/STOP)
                    Analyzer-->>PCFixerApp: Action
                    PCFixerApp->>PCFixerApp: Adjust execution plan or Stop
                end
            end
        end
    else LLM Not Available
        PCFixerApp->>User: Info collected, Analysis unavailable
    end

    PCFixerApp->>PCFixerApp: Enter interactive_mode()
    loop Interactive Loop
        User->>PCFixerApp: Input (question, 'scan', 'run:', 'execute', 'exit')
        alt Input is Question
             PCFixerApp->>Analyzer: ask_llm(follow-up prompt)
             Analyzer->>Ollama: ask_llm()
             Ollama-->>Analyzer: Response
             Analyzer-->>PCFixerApp: Response Text
             PCFixerApp->>PCFixerApp: handle_llm_response()
        alt Input is 'scan'
             PCFixerApp->>SysInfo: handle_system_scan()
             SysInfo-->>PCFixerApp: Updated Report
             PCFixerApp->>Memory: save_memory(system_info)
        alt Input is 'run: cmd'
             PCFixerApp->>CmdRunner: run_command(cmd)
             CmdRunner->>OS: Run command
             OS-->>CmdRunner: Output
             CmdRunner-->>PCFixerApp: Result
             PCFixerApp->>Memory: add_to_memory_list(command_history)
        alt Input is 'execute tool'
             PCFixerApp->>OS: os.system(start tool)
             PCFixerApp->>Memory: add_to_memory_list(command_history)
        alt Input is 'exit'
            PCFixerApp->>User: Goodbye!
            break
        end
    end

