@echo off
:: Change directory to the location of this script
cd /d "%~dp0"
:: AeonFix Ultimate Diagnostics Script - Windows Edition
:: Gathers extensive system data to assist LLM-based diagnosis
:: Must be run with administrator privileges

color 0B
cls
echo =============================
echo  AeonFix - System Diagnostic
echo =============================
echo Running complete system scans...
echo.

:: Check Admin Privileges
whoami /groups | find "S-1-16-12288" >nul || (
    echo [!] Please run this script as Administrator.
    pause
    exit /b
)

:: Normalize time values and remove invalid characters like ':' and space
set hour=%time:~0,2%
if "%hour:~0,1%"==" " set hour=0%hour:~1,1%
set "folder=aeonfix_report_%date:~-4%%date:~4,2%%date:~7,2%_%hour%%time:~3,2%%time:~6,2%"
set "folder=%folder: =0%"
mkdir "%folder%"

:: Save OS Info
echo [+] Capturing OS and basic system info...
systeminfo > "%folder%\systeminfo.txt"
ver >> "%folder%\systeminfo.txt"

:: Check CPU/Memory/Drives with WMIC
echo [+] Capturing CPU, memory, disk data...
wmic cpu get Name,NumberOfCores,NumberOfLogicalProcessors > "%folder%\cpu.txt"
wmic MEMORYCHIP get BankLabel,Capacity,Speed > "%folder%\memory.txt"
wmic diskdrive get Name,Model,Size,Status > "%folder%\disks.txt"

:: Event Logs (Application + System Errors)
echo [+] Capturing system logs...
wevtutil qe System /q:"*[System[(Level=2)]]" /f:text /c:30 > "%folder%\errors_system.log"
wevtutil qe Application /q:"*[System[(Level=2)]]" /f:text /c:30 > "%folder%\errors_application.log"

:: Driver Status
echo [+] Dumping driver list...
driverquery /v > "%folder%\drivers.txt"

:: Disk Health & SMART Status (Basic)
echo [+] Capturing disk SMART status...
powershell "Get-PhysicalDisk | Select FriendlyName, OperationalStatus, HealthStatus" > "%folder%\smart_status.txt"

:: Device Manager Summary
echo [+] Gathering device manager info...
powershell "Get-PnpDevice -Status 'Error'" > "%folder%\device_issues.txt"

:: Check Startup Apps
echo [+] Listing startup programs...
powershell "Get-CimInstance Win32_StartupCommand | Select Name, Command, Location" > "%folder%\startup_apps.txt"

:: Installed Software
echo [+] Listing installed applications...
powershell "Get-WmiObject -Class Win32_Product | Select Name, Version" > "%folder%\installed_apps.txt"

:: System File Check (Offline)
echo [+] Starting System File Check (SFC)...
sfc /scannow > "%folder%\sfc_scan.txt"

:: DISM Scan (Deployment Imaging)
echo [+] Running DISM health check...
DISM /Online /Cleanup-Image /ScanHealth > "%folder%\dism_health.txt"

:: IP & Network Info
echo [+] Checking network configuration...
ipconfig /all > "%folder%\network.txt"
netstat -anob > "%folder%\ports.txt"

:: GPU Info (if available)
echo [+] Checking GPU status...
powershell "Get-WmiObject win32_VideoController | Select Name, DriverVersion, AdapterRAM" > "%folder%\gpu_info.txt"

:: USB issues
echo [+] Checking USB devices for problems...
powershell "Get-WmiObject Win32_USBControllerDevice | ForEach-Object { ([wmi]($_.Dependent)).DeviceID }" > "%folder%\usb_devices.txt"

:: Final echo
cls
color 0A
echo =====================================
echo AeonFix Diagnostics Complete 
echo Output saved in folder: %folder%
echo =====================================
echo.
pause
