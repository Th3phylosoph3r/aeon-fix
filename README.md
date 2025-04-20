# 🔧 AeonFix: AI-Powered Computer Recovery Assistant

AeonFix is your semi-autonomous, private, offline assistant that helps you diagnose, troubleshoot, and repair your Windows and Linux PC issues. Powered by local LLMs via [Ollama](https://ollama.com), AeonFix combines system log parsing, real-time command execution, AI analysis, and structured memory logging to assist you like a professional support engineer — right from your terminal.

## ⚙️ Features

- 💡 Conversational assistant powered by **local LLMs** (no cloud, 100% offline)
- 🧠 Structured problem diagnosis with context-aware recommendations
- 🔍 Log analysis from Windows Event Viewer or Linux logs
- ⚡ Safe execution of AI-suggested system commands with confirmation
- 📎 Persistent memory: remembers the last issue and resolution
- 📄 Rich Markdown formatting in terminal with `rich`
- (WIP) 📷 Multimodal ready (supports screenshots, OCR and vision models)

---

## 📦 Installation

### 1. Download & Install Python 3.10+

[Download Python](https://www.python.org/downloads/)

### 2. Install Required Dependencies

Run this in your terminal (or use the `install_aeonfix.bat` provided):

```bash
pip install rich psutil ollama
```

### 3. Install Windows Terminal (if not installed)

AeonFix works best with [Windows Terminal](https://apps.microsoft.com/detail/9n0dx20hk701?hl=pt-BR\&gl=BR). If not installed, you’ll be prompted to download it. CMD is not supported.

---

## 🤖 LLM Model Setup

AeonFix uses models via **Ollama**. Install Ollama first:

### Install Ollama:

- 👉 [https://ollama.com/download](https://ollama.com/download)

### Then pull a recommended model:

```bash
ollama run gemma3:12b
```

### Alternative Models :

```bash
ollama run gemma3:27b
ollama run llama3.3
```

These models are downloaded automatically after the first run.

---

## 🚀 Usage

### Method 1: From Terminal

```bash
python aeon_fix.py
```

### Method 2: Use `launch_aeonfix.bat`

Double-click the `launch_aeonfix.bat` file to open AeonFix in Windows Terminal.

---

## 🧠 How It Works

1. You describe the problem (e.g. "PC freezes when idle").
2. AeonFix fetches your system/application logs (Windows Event Viewer / Linux journal).
3. The selected LLM analyzes the logs and symptoms, returning:
   - Detailed diagnosis
   - Suggestions (in markdown)
   - [[\*\*\* executable commands \*\*\*]] formatted safely
4. You confirm any command before it runs.
5. It keeps memory logs so you can follow up later.

---

## 🔐 Privacy & Security

- No data leaves your machine.
- Commands are never run without your confirmation.
- Logs are saved locally for transparency.

---

## 💬 Example

```
Symptom: Black screen on boot
Response: Suspected GPU driver failure
Suggested command:
[[*** sfc /scannow ***]]
[[*** dism /online /cleanup-image /restorehealth ***]]
[[*** where nvlddmkm.sys ***]]
```

---

## 📁 File Structure

```
AeonFix/
├── aeon_fix.py                 # Main script
├── launch_aeonfix.bat        # Launcher (runs in Windows Terminal)
├── install_aeonfix.bat       # One-click installer
├── aeon_memory.json     # Persistent memory
├── aeonfix_actions.log     # Structured action logs
└── README.md                 # This file
```

---

## ✨ Future Features
- Working / Test linux version
- Screenshot OCR and Vision Model diagnostics
- Auto-correction using Ansible-like structured tasks
- Timeline of historical problems solved

---

## 🙏 Credits

Created with AI by Th3Philosoph3r, powered by local open-source AI. No cloud. No telemetry. Just local intelligence.

---

## 📜 License

MIT — Use freely, modify responsibly.

