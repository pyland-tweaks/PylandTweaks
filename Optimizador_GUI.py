# -*- coding: utf-8 -*-
"""
PylandTweaks V5.8 - Interfaz grafica (Tkinter)
Optimizador de rendimiento para equipos de gama baja.
"""

import os
import sys
import ctypes
import subprocess
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox


def _app_base():
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "Recursos").exists() or (exe_dir / "Apariencia").exists():
            return exe_dir
        return Path(getattr(sys, "_MEIPASS", exe_dir))
    return Path(__file__).resolve().parent


BASE = _app_base()
APARIENCIA = BASE / "Apariencia"
RECURSOS = BASE / "Recursos"
ASSETS = BASE / "assets"

BG = "#0e1017"
PANEL = "#181b26"
PANEL2 = "#0a0c12"
PANEL3 = "#202434"
BORDER = "#2a3048"
FG = "#e8ecf8"
MUTED = "#8b93ab"
ACCENT = "#7c5cff"
ACCENT_DARK = "#5b3fd6"
ACCENT2 = "#4cc9f0"
GREEN = "#3ddc97"
RED = "#ff5c7a"
RED_DARK = "#3a1a26"
YELLOW = "#ffd166"

FONT = "Segoe UI"
FONT_BOLD = "Segoe UI Semibold"

CREATE_NO_WINDOW = 0x08000000


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def set_app_user_model_id():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "PylandTweaks.PylandTweaks.5.8")
    except Exception:
        pass


def run_as_admin():
    if getattr(sys, "frozen", False):
        params = ""
    else:
        params = f'"{Path(sys.argv[0]).resolve()}"'
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)


def total_phys_kb():
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    stat = MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(stat)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    return int(stat.ullTotalPhys // 1024)


def q(path):
    return f'"{path}"'


def reg_add(key, value, typ, data):
    return f'reg add "{key}" /v "{value}" /t {typ} /d "{data}" /f'


def reg_del(key, value):
    return f'reg delete "{key}" /v "{value}" /f'


# ---------------------------------------------------------------------------
# Datos de optimizacion
# ---------------------------------------------------------------------------
SERVICES_MANUAL = [
    "AJRouter", "ALG", "AppIDSvc", "AppMgmt", "AppReadiness", "AppXSvc", "Appinfo",
    "AssignedAccessManagerSvc", "AxInstSV", "BDESVC", "BTAGService",
    "BcastDVRUserService_*", "BluetoothUserService_*", "Browser", "CaptureService_*",
    "CertPropSvc", "ClipSVC", "ConsentUxUserSvc_*", "CredentialEnrollmentManagerUserSvc_*",
    "CscService", "DcpSvc", "DevQueryBroker", "DeviceAssociationBrokerSvc_*",
    "DeviceAssociationService", "DeviceInstall", "DevicePickerUserSvc_*",
    "DevicesFlowUserSvc_*", "DisplayEnhancementService", "DmEnrollmentSvc", "DsSvc",
    "DsmSvc", "EFS", "EapHost", "EntAppSvc", "FDResPub", "Fax", "FrameServer",
    "FrameServerMonitor", "GraphicsPerfSvc", "HomeGroupListener", "HomeGroupProvider",
    "HvHost", "IEEtwCollectorService", "IKEEXT", "InstallService", "InventorySvc",
    "IpxlatCfgSvc", "KtmRm", "LicenseManager", "LxpSvc", "MSDTC", "MSiSCSI",
    "McpManagementService", "MessagingService_*", "MicrosoftEdgeElevationService",
    "MixedRealityOpenXRSvc", "NPSMSvc_*", "NaturalAuthentication", "NcaSvc", "NcbService",
    "NcdAutoSetup", "NetSetupSvc", "Netman", "NgcCtnrSvc", "NgcSvc", "NlaSvc",
    "P9RdrService_*", "PNRPAutoReg", "PNRPsvc", "PeerDistSvc", "PenService_*", "PerfHost",
    "PhoneSvc", "PimIndexMaintenanceSvc_*", "PlugPlay", "PolicyAgent", "PrintNotify",
    "PrintWorkflowUserSvc_*", "PushToInstall", "QWAVE", "RasAuto", "RasMan", "RetailDemo",
    "RmSvc", "RpcLocator", "SCPolicySvc", "SCardSvr", "SDRSVC", "SEMgrSvc", "SNMPTRAP",
    "SNMPTrap", "SSDPSRV", "ScDeviceEnum", "SecurityHealthService", "Sense",
    "SensorDataService", "SensorService", "SensrSvc", "SessionEnv", "SharedAccess",
    "SharedRealitySvc", "SmsRouter", "SstpSvc", "StiSvc", "TabletInputService", "TapiSrv",
    "TieringEngineService", "TimeBroker", "TimeBrokerSvc", "TokenBroker",
    "TroubleshootingSvc", "TrustedInstaller", "UI0Detect", "UdkUserSvc_*", "UmRdpService",
    "UnistoreSvc_*", "UserDataSvc_*", "VSS", "VacSvc", "W32Time", "WEPHOSTSVC",
    "WFDSConMgrSvc", "WMPNetworkSvc", "WManSvc", "WPDBusEnum", "WSService", "WaaSMedicSvc",
    "WalletService", "WarpJITSvc", "WbioSrvc", "WcsPlugInService", "WdNisSvc",
    "WdiServiceHost", "WdiSystemHost", "WebClient", "Wecsvc", "WerSvc", "WiaRpc",
    "WinHttpAutoProxySvc", "WinRM", "WpcMonSvc", "XblAuthManager", "XblGameSave",
    "XboxGipSvc", "XboxNetApiSvc", "autotimesvc", "bthserv", "camsvc", "cloudidsvc",
    "dcsvc", "defragsvc", "diagnosticshub.standardcollector.service", "diagsvc",
    "dmwappushservice", "dot3svc", "edgeupdate", "edgeupdatem", "embeddedmode", "fdPHost",
    "fhsvc", "hidserv", "icssvc", "lfsvc", "lltdsvc", "lmhosts", "msiserver", "netprofm",
    "p2pimsvc", "p2psvc", "perceptionsimulation", "pla", "seclogon", "smphost", "spectrum",
    "svsvc", "swprv", "upnphost", "vds", "vmicguestinterface", "vmicheartbeat",
    "vmickvpexchange", "vmicrdv", "vmicshutdown", "vmictimesync", "vmicvmsession",
    "vmicvss", "vmvss", "wbengine", "wcncsvc", "webthreatdefsvc", "wercplsupport", "wisvc",
    "wlidsvc", "wlpasvc", "wmiApSrv", "workfolderssvc", "wuauserv", "wudfsvc",
]

SERVICES_DISABLED = [
    "diagnosticshub.standardcollector.service", "DiagTrack", "DPS", "FontCache",
    "FontCache3.0.0.0", "SystemUsageReportSvc_QUEENCREEK", "GpuEnergyDrv",
    "ShellHWDetection", "SgrmAgent", "SgrmBroker", "uhssvc", "TrkWks", "WdiServiceHost",
    "WdiSystemHost", "WSearch", "diagsvc",
]

TELEMETRY_TASKS = [
    r"Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser",
    r"Microsoft\Windows\Application Experience\ProgramDataUpdater",
    r"Microsoft\Windows\Autochk\Proxy",
    r"Microsoft\Windows\Customer Experience Improvement Program\Consolidator",
    r"Microsoft\Windows\Customer Experience Improvement Program\UsbCeip",
    r"Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector",
    r"Microsoft\Windows\Feedback\Siuf\DmClient",
    r"Microsoft\Windows\Feedback\Siuf\DmClientOnScenarioDownload",
    r"Microsoft\Windows\Windows Error Reporting\QueueReporting",
    r"Microsoft\Windows\Application Experience\MareBackup",
    r"Microsoft\Windows\Application Experience\StartupAppTask",
    r"Microsoft\Windows\Application Experience\PcaPatchDbTask",
    r"Microsoft\Windows\Maps\MapsUpdateTask",
]

UPDATE_TASKS = [
    r"\Microsoft\Windows\InstallService\*",
    r"\Microsoft\Windows\UpdateOrchestrator\*",
    r"\Microsoft\Windows\UpdateAssistant\*",
    r"\Microsoft\Windows\WaaSMedic\*",
    r"\Microsoft\Windows\WindowsUpdate\*",
    r"\Microsoft\WindowsUpdate\*",
]

VISUAL_REGS = [
    ("HKCU\\Control Panel\\Desktop", "DragFullWindows", "REG_SZ", "0"),
    ("HKCU\\Control Panel\\Desktop", "MenuShowDelay", "REG_SZ", "200"),
    ("HKCU\\Control Panel\\Desktop", "MinAnimate", "REG_SZ", "0"),
    ("HKCU\\Control Panel\\Desktop", "KeyboardDelay", "REG_DWORD", "0"),
    ("HKCU\\Control Panel\\Desktop", "ListviewAlphaSelect", "REG_DWORD", "0"),
    ("HKCU\\Control Panel\\Desktop", "ListviewShadow", "REG_DWORD", "0"),
    ("HKCU\\Control Panel\\Desktop", "TaskbarAnimations", "REG_DWORD", "0"),
    ("HKCU\\Control Panel\\Desktop", "VisualFXSetting", "REG_DWORD", "3"),
    ("HKCU\\Control Panel\\Desktop", "EnableAeroPeek", "REG_DWORD", "0"),
    ("HKCU\\Control Panel\\Desktop", "MenuShowDelay", "REG_DWORD", "1"),
    ("HKCU\\Control Panel\\Desktop", "AutoEndTasks", "REG_DWORD", "1"),
    ("HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", "EnableTransparency", "REG_DWORD", "0"),
]

TUNING_REGS = [
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Affinity", "REG_DWORD", "0"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Background Only", "REG_SZ", "False"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Clock Rate", "REG_DWORD", "10000"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "GPU Priority", "REG_DWORD", "8"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Priority", "REG_DWORD", "6"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Scheduling Category", "REG_SZ", "High"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "SFIO Priority", "REG_SZ", "High"),
    (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters", "MaxCmds", "REG_DWORD", "100"),
    (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters", "MaxThreads", "REG_DWORD", "100"),
    (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters", "MaxCollectionCount", "REG_DWORD", "32"),
    (r"HKLM\SYSTEM\CurrentControlSet\Control\FileSystem", "LongPathsEnabled", "REG_DWORD", "1"),
    (r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching", "SearchOrderConfig", "REG_DWORD", "1"),
    (r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "SystemResponsiveness", "REG_DWORD", "0"),
    (r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "NetworkThrottlingIndex", "REG_DWORD", "4294967295"),
    (r"HKLM\SYSTEM\ControlSet001\Services\Ndu", "Start", "REG_DWORD", "2"),
    (r"HKCU\Control Panel\Mouse", "MouseHoverTime", "REG_SZ", "400"),
    (r"HKLM\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters", "IRPStackSize", "REG_DWORD", "30"),
    (r"HKCU\SOFTWARE\Policies\Microsoft\Windows\Windows Feeds", "EnableFeeds", "REG_DWORD", "0"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Feeds", "ShellFeedsTaskbarViewMode", "REG_DWORD", "2"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "HideSCAMeetNow", "REG_DWORD", "1"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\UserProfileEngagement", "ScoobeSystemSettingEnabled", "REG_DWORD", "0"),
    (r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode", "REG_DWORD", "2"),
]

WIFI_REGS = [
    ("HKLM\\Software\\Microsoft\\PolicyManager\\default\\WiFi", "AllowWiFiHotSpotReporting", "REG_DWORD", "0"),
    ("HKLM\\Software\\Microsoft\\PolicyManager\\default\\WiFi", "AllowAutoConnectToWiFiSenseHotspots", "REG_DWORD", "0"),
]

TELEMETRY_REGS = [
    (r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection", "AllowTelemetry", "REG_DWORD", "0"),
    (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", "REG_DWORD", "0"),
    (r"HKCU\SOFTWARE\Microsoft\Siuf\Rules", "NumberOfSIUFInPeriod", "REG_DWORD", "0"),
    (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection", "DoNotShowFeedbackNotifications", "REG_DWORD", "1"),
    (r"HKCU\SOFTWARE\Policies\Microsoft\Windows\CloudContent", "DisableTailoredExperiencesWithDiagnosticData", "REG_DWORD", "1"),
    (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo", "DisabledByGroupPolicy", "REG_DWORD", "1"),
    (r"HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting", "Disabled", "REG_DWORD", "1"),
]

SERVICE_DEFAULT_START = {
    "NlaSvc": "auto",
    "DiagTrack": "auto",
    "DPS": "auto",
    "ShellHWDetection": "auto",
    "TrkWks": "auto",
    "SgrmBroker": "auto",
    "SgrmAgent": "boot",
    "WSearch": "delayed-auto",
}

VISUAL_REGS_REVERT = [
    ("HKCU\\Control Panel\\Desktop", "DragFullWindows", "REG_SZ", "1"),
    ("HKCU\\Control Panel\\Desktop", "MenuShowDelay", "REG_SZ", "400"),
    ("HKCU\\Control Panel\\Desktop", "MinAnimate", "REG_SZ", "1"),
    ("HKCU\\Control Panel\\Desktop", "KeyboardDelay", "REG_DWORD", "1"),
    ("HKCU\\Control Panel\\Desktop", "ListviewAlphaSelect", "REG_DWORD", "1"),
    ("HKCU\\Control Panel\\Desktop", "ListviewShadow", "REG_DWORD", "1"),
    ("HKCU\\Control Panel\\Desktop", "TaskbarAnimations", "REG_DWORD", "1"),
    ("HKCU\\Control Panel\\Desktop", "VisualFXSetting", "REG_DWORD", "0"),
    ("HKCU\\Control Panel\\Desktop", "EnableAeroPeek", "REG_DWORD", "1"),
    ("HKCU\\Control Panel\\Desktop", "AutoEndTasks", "REG_DWORD", "0"),
    ("HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", "EnableTransparency", "REG_DWORD", "1"),
]

TUNING_REGS_REVERT = [
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Affinity", "REG_DWORD", "0"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Background Only", "REG_SZ", "False"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Clock Rate", "REG_DWORD", "10000"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "GPU Priority", "REG_DWORD", "8"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Priority", "REG_DWORD", "2"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Scheduling Category", "REG_SZ", "Medium"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "SFIO Priority", "REG_SZ", "Normal"),
    (r"HKLM\SYSTEM\CurrentControlSet\Control\FileSystem", "LongPathsEnabled", "REG_DWORD", "0"),
    (r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\DriverSearching", "SearchOrderConfig", "REG_DWORD", "1"),
    (r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "SystemResponsiveness", "REG_DWORD", "20"),
    (r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "NetworkThrottlingIndex", "REG_DWORD", "10"),
    (r"HKLM\SYSTEM\ControlSet001\Services\Ndu", "Start", "REG_DWORD", "2"),
    (r"HKCU\Control Panel\Mouse", "MouseHoverTime", "REG_SZ", "400"),
    (r"HKLM\SYSTEM\CurrentControlSet\Services\LanmanServer\Parameters", "IRPStackSize", "REG_DWORD", "15"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\UserProfileEngagement", "ScoobeSystemSettingEnabled", "REG_DWORD", "1"),
]

TUNING_REGS_DELETE = [
    (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters", "MaxCmds"),
    (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters", "MaxThreads"),
    (r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\LanmanWorkstation\Parameters", "MaxCollectionCount"),
    (r"HKLM\SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode"),
    (r"HKCU\SOFTWARE\Policies\Microsoft\Windows\Windows Feeds", "EnableFeeds"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Feeds", "ShellFeedsTaskbarViewMode"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "HideSCAMeetNow"),
]

WIFI_REGS_REVERT = [
    ("HKLM\\Software\\Microsoft\\PolicyManager\\default\\WiFi", "AllowWiFiHotSpotReporting", "REG_DWORD", "1"),
    ("HKLM\\Software\\Microsoft\\PolicyManager\\default\\WiFi", "AllowAutoConnectToWiFiSenseHotspots", "REG_DWORD", "1"),
]

LATENCY_REGS = [
    (r"HKLM\SYSTEM\CurrentControlSet\Control\Power\PowerThrottling", "PowerThrottlingOff", "REG_DWORD", "1"),
    (r"HKLM\SYSTEM\CurrentControlSet\Control\PriorityControl", "Win32PrioritySeparation", "REG_DWORD", "38"),
    (r"HKCU\Software\Microsoft\GameBar", "AllowAutoGameMode", "REG_DWORD", "1"),
    (r"HKCU\Software\Microsoft\GameBar", "AutoGameModeEnabled", "REG_DWORD", "1"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", "REG_DWORD", "0"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR", "HistoricalCaptureEnabled", "REG_DWORD", "0"),
    (r"HKCU\System\GameConfigStore", "GameDVR_Enabled", "REG_DWORD", "0"),
    (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", "REG_DWORD", "0"),
    (r"HKCU\System\GameConfigStore", "GameDVR_FSEBehaviorMode", "REG_DWORD", "2"),
    (r"HKCU\System\GameConfigStore", "GameDVR_HonorUserFSEBehaviorMode", "REG_DWORD", "1"),
    (r"HKCU\System\GameConfigStore", "GameDVR_DXGIHonorFSEWindowsCompatible", "REG_DWORD", "1"),
    (r"HKCU\Control Panel\Mouse", "MouseSpeed", "REG_SZ", "0"),
    (r"HKCU\Control Panel\Mouse", "MouseThreshold1", "REG_SZ", "0"),
    (r"HKCU\Control Panel\Mouse", "MouseThreshold2", "REG_SZ", "0"),
]

LATENCY_REGS_REVERT = [
    (r"HKLM\SYSTEM\CurrentControlSet\Control\Power\PowerThrottling", "PowerThrottlingOff", "REG_DWORD", "0"),
    (r"HKLM\SYSTEM\CurrentControlSet\Control\PriorityControl", "Win32PrioritySeparation", "REG_DWORD", "2"),
    (r"HKCU\Software\Microsoft\GameBar", "AllowAutoGameMode", "REG_DWORD", "1"),
    (r"HKCU\Software\Microsoft\GameBar", "AutoGameModeEnabled", "REG_DWORD", "1"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", "REG_DWORD", "1"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR", "HistoricalCaptureEnabled", "REG_DWORD", "1"),
    (r"HKCU\System\GameConfigStore", "GameDVR_Enabled", "REG_DWORD", "1"),
    (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", "REG_DWORD", "1"),
    (r"HKCU\System\GameConfigStore", "GameDVR_FSEBehaviorMode", "REG_DWORD", "0"),
    (r"HKCU\System\GameConfigStore", "GameDVR_HonorUserFSEBehaviorMode", "REG_DWORD", "0"),
    (r"HKCU\System\GameConfigStore", "GameDVR_DXGIHonorFSEWindowsCompatible", "REG_DWORD", "0"),
    (r"HKCU\Control Panel\Mouse", "MouseSpeed", "REG_SZ", "1"),
    (r"HKCU\Control Panel\Mouse", "MouseThreshold1", "REG_SZ", "6"),
    (r"HKCU\Control Panel\Mouse", "MouseThreshold2", "REG_SZ", "10"),
]

GAME_PRIORITY = [
    "csgo.exe", "cs2.exe", "FortniteClient-Win64-Shipping.exe", "gta_3.exe", "gta_vc.exe",
    "gta_sa.exe", "GTAIV.exe", "GTA5.exe", "java.exe", "javaw.exe", "minecraft.exe",
    "Minecraft.Windows.exe", "obs32.exe", "obs64.exe", "OptiCraft.exe", "PPSSPP.exe",
]


def regs(cmds):
    return [reg_add(*c) for c in cmds]


# ---------------------------------------------------------------------------
# Aplicacion
# ---------------------------------------------------------------------------
class OptimizadorApp:
    def __init__(self, root):
        self.root = root
        self.busy = False
        self.root.title("PylandTweaks V5.8")
        self.root.geometry("1040x820")
        self.root.minsize(900, 680)
        self.root.configure(bg=BG)

        self._setup_style()
        self._set_window_icon()
        self._build_header()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(4, 8))

        self._build_tab_recomendado()
        self._build_tab_latencia()
        self._build_tab_reversion()
        self._build_tab_sistema()
        self._build_tab_apariencia()
        self._build_tab_recursos()
        self._build_tab_herramientas()
        self._build_tab_acerca()

        self._build_log()
        self._build_status()

        self.log("PylandTweaks V5.8 listo.")
        self.log("Ejecutando como administrador." if is_admin() else "ADVERTENCIA: sin permisos de administrador.")

    # ------------------------------------------------------------------ UI
    def _load_photo(self, filename):
        path = ASSETS / filename
        if not path.exists():
            return None
        try:
            return tk.PhotoImage(file=str(path))
        except tk.TclError:
            return None

    def _add_watermark(self, parent, relx=0.5, rely=0.5, anchor="center", subsample=2):
        img = self._load_photo("logo_bg.png")
        if img is None:
            return None
        if subsample > 1:
            img = img.subsample(subsample)
        canvas = tk.Canvas(parent, width=img.width(), height=img.height(),
                           bg=BG, highlightthickness=0, bd=0)
        canvas.place(relx=relx, rely=rely, anchor=anchor)
        canvas.create_image(0, 0, anchor="nw", image=img)
        canvas.image = img
        return canvas

    def _new_tab(self, title, padding=14):
        tab = ttk.Frame(self.notebook, padding=padding)
        self.notebook.add(tab, text=title)
        self._add_watermark(tab)
        return tab

    def _set_window_icon(self):
        ico = ASSETS / "app.ico"
        ico_ok = False
        if ico.exists():
            try:
                self.root.iconbitmap(default=str(ico))
                ico_ok = True
            except tk.TclError:
                pass
        if not ico_ok:
            self.icon_img = self._load_photo("logo_128.png") or self._load_photo("logo.png")
            if self.icon_img is not None:
                try:
                    self.root.iconphoto(True, self.icon_img)
                except tk.TclError:
                    pass

    def _setup_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(".", background=BG, foreground=FG, fieldbackground=PANEL,
                        bordercolor=BORDER, font=(FONT, 9))
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=PANEL)
        style.configure("TLabel", background=BG, foreground=FG, font=(FONT, 9))
        style.configure("Title.TLabel", background=BG, foreground=FG, font=(FONT_BOLD, 22))
        style.configure("Sub.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))
        style.configure("Hint.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))
        style.configure("Section.TLabel", background=PANEL, foreground=ACCENT2, font=(FONT_BOLD, 10))
        style.configure("Status.TLabel", background=PANEL2, foreground=MUTED, font=(FONT, 9))

        style.configure("TNotebook", background=BG, borderwidth=0, tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab", background=PANEL, foreground=MUTED,
                        padding=(17, 9), borderwidth=0, font=(FONT_BOLD, 9))
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT), ("active", PANEL3)],
                  foreground=[("selected", "#ffffff"), ("active", FG)])

        style.configure("TButton", background=PANEL3, foreground=FG, borderwidth=0,
                        focusthickness=0, padding=(12, 9), font=(FONT, 9))
        style.map("TButton",
                  background=[("active", "#2b3146"), ("pressed", ACCENT), ("disabled", "#151824")],
                  foreground=[("disabled", "#5a6178")])

        style.configure("Card.TButton", background=PANEL3, foreground=FG, borderwidth=0,
                        focusthickness=0, padding=(12, 9), font=(FONT, 9))
        style.map("Card.TButton",
                  background=[("active", "#2b3146"), ("pressed", ACCENT_DARK), ("disabled", "#151824")],
                  foreground=[("active", "#ffffff"), ("disabled", "#5a6178")])

        style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff",
                        borderwidth=0, focusthickness=0, font=(FONT_BOLD, 10), padding=(12, 12))
        style.map("Accent.TButton",
                  background=[("active", ACCENT_DARK), ("pressed", "#4a33b8")],
                  foreground=[("disabled", "#9aa0b5")])

        style.configure("Danger.TButton", background=RED_DARK, foreground="#ffa8b8",
                        borderwidth=0, focusthickness=0, padding=(12, 9), font=(FONT, 9))
        style.map("Danger.TButton",
                  background=[("active", RED), ("pressed", "#c93b57")],
                  foreground=[("active", "#ffffff")])

        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=PANEL3,
                        borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT)

        style.configure("Vertical.TScrollbar", background=PANEL3, troughcolor=PANEL2,
                        bordercolor=PANEL2, arrowcolor=MUTED, borderwidth=0)
        style.map("Vertical.TScrollbar", background=[("active", ACCENT)])

    def _build_header(self):
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=18, pady=(16, 8))

        self.header_logo = self._load_photo("logo_48.png")
        if self.header_logo is None:
            big = self._load_photo("logo_96.png")
            if big is not None:
                self.header_logo = big.subsample(2)
        if self.header_logo is not None:
            tk.Label(header, image=self.header_logo, bg=BG, bd=0).pack(
                side="left", padx=(0, 12))
        else:
            logo = tk.Canvas(header, width=46, height=46, bg=BG, highlightthickness=0)
            logo.pack(side="left", padx=(0, 12))
            r = 12
            logo.create_polygon(
                r, 0, 46 - r, 0, 46, 0, 46, r, 46, 46 - r, 46, 46,
                46 - r, 46, r, 46, 0, 46, 0, 46 - r, 0, r, 0, 0,
                smooth=True, fill=ACCENT, outline="")
            logo.create_polygon(
                26, 9, 15, 27, 22, 27, 18, 38, 32, 19, 24, 19, 28, 9,
                fill="#ffffff", outline="")

        left = tk.Frame(header, bg=BG)
        left.pack(side="left")

        title_row = tk.Frame(left, bg=BG)
        title_row.pack(anchor="w")
        tk.Label(title_row, text="PylandTweaks", bg=BG, fg=FG,
                 font=(FONT_BOLD, 22)).pack(side="left")
        tk.Label(title_row, text="V5.8", bg=BG, fg=ACCENT2,
                 font=(FONT_BOLD, 12)).pack(side="left", padx=(10, 0), pady=(6, 0))

        tk.Label(left, text="Rendimiento para equipos de gama baja",
                 bg=BG, fg=MUTED, font=(FONT, 9)).pack(anchor="w")

        chip = tk.Frame(header, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        chip.pack(side="right")
        dot_color = GREEN if is_admin() else RED
        dot = tk.Canvas(chip, width=10, height=10, bg=PANEL, highlightthickness=0)
        dot.create_oval(1, 1, 9, 9, fill=dot_color, outline=dot_color)
        dot.pack(side="left", padx=(12, 7), pady=9)
        tk.Label(chip, text="Administrador" if is_admin() else "Sin permisos",
                 bg=PANEL, fg=dot_color, font=(FONT_BOLD, 9)).pack(
            side="left", padx=(0, 12), pady=9)

        line = tk.Canvas(self.root, height=2, bg=BG, highlightthickness=0)
        line.pack(fill="x", padx=18, pady=(2, 0))
        line.bind("<Configure>", lambda e: self._draw_gradient(e.widget))

    def _draw_gradient(self, canvas):
        canvas.delete("all")
        width = max(canvas.winfo_width(), 2)
        steps = max(int(width / 4), 60)
        c1 = (int(ACCENT[1:3], 16), int(ACCENT[3:5], 16), int(ACCENT[5:7], 16))
        c2 = (int(ACCENT2[1:3], 16), int(ACCENT2[3:5], 16), int(ACCENT2[5:7], 16))
        for i in range(steps):
            t = i / (steps - 1)
            rgb = tuple(int(c1[j] * (1 - t) + c2[j] * t) for j in range(3))
            color = "#%02x%02x%02x" % rgb
            canvas.create_line(i * width / steps, 1, (i + 1) * width / steps + 1, 1,
                               fill=color, width=2)

    def _card(self, parent, title, actions, danger=False):
        accent_color = RED if danger else ACCENT
        outer = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER,
                         highlightthickness=1, bd=0)
        inner = tk.Frame(outer, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=14, pady=12)

        top = tk.Frame(inner, bg=PANEL)
        top.pack(fill="x")
        bar = tk.Frame(top, bg=accent_color, width=4, height=16)
        bar.pack_propagate(False)
        bar.pack(side="left", padx=(0, 9))
        tk.Label(top, text=title, bg=PANEL, fg=RED if danger else ACCENT2,
                 font=(FONT_BOLD, 10)).pack(side="left")

        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=(11, 11))

        for text, cmd in actions:
            style = "Danger.TButton" if danger else "Card.TButton"
            b = ttk.Button(inner, text=text, command=cmd, style=style, cursor="hand2")
            b.pack(fill="x", pady=3)
        return outer

    def _notice(self, parent, text, color=YELLOW):
        box = tk.Frame(parent, bg=PANEL, highlightbackground=color, highlightthickness=1)
        box.pack(fill="x", pady=(10, 0))
        tk.Label(box, text=text, bg=PANEL, fg=color, font=(FONT, 9),
                 justify="left", anchor="w", wraplength=880).pack(
            fill="x", padx=12, pady=9)
        return box

    def _build_tab_recomendado(self):
        tab = self._new_tab("  Recomendado  ")

        ttk.Label(tab, text="Aplicar el paquete completo de optimizaciones recomendadas.",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        ttk.Button(tab, text="APLICAR OPTIMIZACIONES RECOMENDADAS",
                   style="Accent.TButton", command=self.ask_recommended).pack(fill="x", pady=6)

        ttk.Button(tab, text="REVERTIR OPTIMIZACIONES (VOLVER A LA NORMALIDAD)",
                   style="Danger.TButton", command=self.ask_revert_all).pack(fill="x", pady=6)

        row = ttk.Frame(tab)
        row.pack(fill="x", pady=6)
        row.columnconfigure(0, weight=1)
        row.columnconfigure(1, weight=1)

        self._card(row, "Seguridad y respaldo", [
            ("Crear punto de restauracion (Recomendado)", self.do_restore_point),
        ]).grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        self._card(row, "Limpieza rapida", [
            ("Borrar archivos temporales", self.do_temp_files),
        ]).grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self._notice(
            tab,
            "IMPORTANTE: al terminar de aplicar las optimizaciones debes REINICIAR el equipo "
            "para que todos los cambios surtan efecto.\n"
            "Consejo: crea un punto de restauracion antes de empezar.")

    def _build_tab_latencia(self):
        tab = self._new_tab("  Latencia  ")

        ttk.Label(tab, text="Ajustes seguros para reducir latencia y mejorar la respuesta en juegos.",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        ttk.Button(tab, text="APLICAR OPTIMIZACIONES DE LATENCIA",
                   style="Accent.TButton", command=self.ask_latency).pack(fill="x", pady=6)

        grid = ttk.Frame(tab)
        grid.pack(fill="both", expand=True, pady=(6, 0))
        for i in range(2):
            grid.columnconfigure(i, weight=1)

        cards = [
            ("Energia y CPU", [
                ("Plan Ultimate + CPU al 100%", lambda: self.run_steps(
                    "Energia y CPU", [("Aplicando plan de energia", self.cmds_latency_power())])),
                ("Restaurar plan de energia", lambda: self.run_steps(
                    "Restaurar energia", [("Restaurando plan equilibrado", self.cmds_latency_power_revert())])),
            ]),
            ("Juegos y entrada", [
                ("Game Mode + quitar Game Bar y DVR", lambda: self.run_steps(
                    "Juegos y entrada", [("Aplicando ajustes de juegos", regs(LATENCY_REGS))])),
                ("Restaurar juegos y raton", lambda: self.run_steps(
                    "Restaurar juegos", [("Restaurando ajustes de juegos", regs(LATENCY_REGS_REVERT))])),
            ]),
            ("Revertir todo", [
                ("Deshacer optimizaciones de latencia", self.do_latency_revert),
            ]),
            ("Consejos", [
                ("Abrir ajustes de Modo juego", self.open_gamemode),
            ]),
        ]

        for idx, (title, actions) in enumerate(cards):
            self._card(grid, title, actions).grid(
                row=idx // 2, column=idx % 2, sticky="nsew", padx=6, pady=6)

        ttk.Label(tab, text="Ganancia tipica: 0.5 a 2 ms. Lo demas depende del juego, driver GPU y BIOS.\n"
                            "El plan al 100% aumenta consumo y temperatura; es normal y reversible.",
                  style="Sub.TLabel", justify="left").pack(anchor="w", pady=(12, 0))

        self._notice(tab, "IMPORTANTE: reinicia el equipo despues de aplicar los ajustes de "
                          "latencia para que se apliquen por completo.")

    def _build_tab_reversion(self):
        tab = self._new_tab("  Reversion  ")

        ttk.Label(tab, text="Deshace los cambios aplicados por el optimizador y vuelve a los valores de Windows.",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        ttk.Button(tab, text="REVERTIR TODAS LAS OPTIMIZACIONES",
                   style="Accent.TButton", command=self.ask_revert_all).pack(fill="x", pady=6)

        self._notice(tab, "IMPORTANTE: reinicia el equipo despues de revertir para volver "
                          "a los valores normales de Windows.")

        grid = ttk.Frame(tab)
        grid.pack(fill="both", expand=True, pady=(6, 0))
        for i in range(2):
            grid.columnconfigure(i, weight=1)

        cards = [
            ("Servicios", [
                ("Restaurar servicios predeterminados", lambda: self.run_steps(
                    "Restaurar servicios", [("Restaurando servicios", self.cmds_services_default())])),
            ]),
            ("Registro y rendimiento", [
                ("Revertir ajustes de registro", lambda: self.run_steps(
                    "Revertir registro", [("Restaurando ajustes", self.cmds_regs_revert())])),
            ]),
            ("Tareas programadas", [
                ("Reactivar telemetria y Windows Update", lambda: self.run_steps(
                    "Reactivar tareas", [
                        ("Reactivando telemetria", self.cmds_telemetry_tasks(True)),
                        ("Reactivando Windows Update", self.cmds_update_tasks(True)),
                    ])),
            ]),
            ("Juegos y red", [
                ("Revertir prioridad de juegos", lambda: self.run_steps(
                    "Prioridad de juegos", [("Restaurando prioridad", self.cmds_game_priority_revert())])),
                ("Revertir GameDVR y pantalla completa", lambda: self.run_steps(
                    "GameDVR", [("Restaurando GameDVR", [
                        reg_del(r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\GameDVR",
                                "GameDVR_DXGIHonorFSEWindowsCompatible")
                    ])])),
                ("Restaurar Teredo", lambda: self.run_steps(
                    "Teredo", [("Restaurando Teredo", ["netsh interface teredo set state default"])])),
            ]),
            ("Defender y Update", [
                ("Habilitar Windows Defender", self.do_enable_defender),
                ("Habilitar Windows Update", self.do_enable_update),
                ("Abrir Restaurar sistema", self.open_restore),
            ]),
        ]

        for idx, (title, actions) in enumerate(cards):
            span = 2 if idx == len(cards) - 1 and len(cards) % 2 else 1
            self._card(grid, title, actions).grid(
                row=idx // 2, column=idx % 2, columnspan=span,
                sticky="nsew", padx=6, pady=6)

    def _build_tab_sistema(self):
        tab = self._new_tab("  Sistema  ")
        for i in range(2):
            tab.columnconfigure(i, weight=1)

        cards = [
            ("Servicios", [
                ("Establecer servicios en Manual", lambda: self.run_steps(
                    "Servicios en manual", [("Estableciendo servicios en manual", self.cmds_services_manual())])),
                ("Deshabilitar servicios innecesarios", lambda: self.run_steps(
                    "Servicios innecesarios", [("Deshabilitando servicios", self.cmds_services_disabled())])),
            ], False),
            ("Telemetria", [
                ("Desactivar telemetria", lambda: self.run_steps(
                    "Telemetria", [
                        ("Deshabilitando tareas de telemetria", self.cmds_telemetry_tasks_disable()),
                        ("Deshabilitando telemetria (registro)", regs(TELEMETRY_REGS)),
                    ])),
            ], False),
            ("Rendimiento", [
                ("Reducir procesos svchost", lambda: self.run_steps(
                    "svchost", [("Reduciendo procesos svchost", self.cmds_svchost())])),
                ("Alta prioridad en juegos", self.do_game_priority),
                ("Desactivar GameDVR", lambda: self.run_steps(
                    "GameDVR", [("Desactivando GameDVR", [
                        'reg add "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR" /v GameDVR_DXGIHonorFSEWindowsCompatible /t REG_DWORD /d 1 /f'
                    ])])),
            ], False),
            ("Interfaz", [
                ("Deshabilitar optimizaciones de pantalla completa", lambda: self.run_steps(
                    "Pantalla completa", [("Deshabilitando optimizaciones fullscreen", [
                        'reg add "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR" /v GameDVR_DXGIHonorFSEWindowsCompatible /t REG_DWORD /d 1 /f'
                    ])])),
                ("Reducir calidad visual de Windows", lambda: self.run_steps(
                    "Calidad visual", [("Optimizando apartado visual", regs(VISUAL_REGS))])),
                ("Desactivar apps en segundo plano", lambda: self.run_steps(
                    "Segundo plano", [("Deshabilitando apps en segundo plano", [
                        'reg add "HKEY_LOCAL_MACHINE\\Software\\Microsoft\\Windows\\CurrentVersion\\Authentication\\LogonUI" /v GlobalUserDisabled /t REG_DWORD /d 1 /f'
                    ])])),
            ], False),
        ]

        for idx, (title, actions, danger) in enumerate(cards):
            self._card(tab, title, actions, danger).grid(
                row=idx // 2, column=idx % 2, sticky="nsew", padx=6, pady=6)

    def _build_tab_apariencia(self):
        tab = self._new_tab("  Apariencia  ")
        for i in range(2):
            tab.columnconfigure(i, weight=1)

        pairs = [
            ("Tema", [
                ("Tema Oscuro", lambda: self.import_reg(APARIENCIA / "Tema Oscuro.reg")),
                ("Tema Claro", lambda: self.import_reg(APARIENCIA / "Tema Claro.reg")),
            ]),
            ("Efectos visuales", [
                ("Deshabilitar transparencia", lambda: self.import_reg(APARIENCIA / "Deshabilitar Transparencia.reg")),
                ("Habilitar transparencia", lambda: self.import_reg(APARIENCIA / "Habilitar Transparencia.reg")),
            ]),
            ("Cortana", [
                ("Deshabilitar Cortana", lambda: self.import_reg(APARIENCIA / "Deshabilitar Cortana.reg")),
                ("Habilitar Cortana", lambda: self.import_reg(APARIENCIA / "Habilitar Cortana.reg")),
            ]),
            ("Action Center", [
                ("Deshabilitar Action Center", lambda: self.import_reg(APARIENCIA / "Deshabilitar Action Center.reg")),
                ("Habilitar Action Center", lambda: self.import_reg(APARIENCIA / "Habilitar Action Center.reg")),
            ]),
        ]

        for idx, (title, actions) in enumerate(pairs):
            self._card(tab, title, actions).grid(
                row=idx // 2, column=idx % 2, sticky="nsew", padx=6, pady=6)

    def _build_tab_recursos(self):
        tab = self._new_tab("  Recursos  ")
        for i in range(2):
            tab.columnconfigure(i, weight=1)

        cards = [
            ("Memoria RAM", [
                ("Abrir Mem Reduct", self.open_memreduct),
                ("Deshabilitar compresion de RAM", lambda: self.run_file(RECURSOS / "Compresion RAM" / "Deshabilitar Compresion.cmd")),
                ("Revertir compresion de RAM", lambda: self.run_file(RECURSOS / "Compresion RAM" / "Revertir Cambios.bat")),
            ]),
            ("CPU", [
                ("Aplicar plan de energia", lambda: self.run_file(RECURSOS / "Plan de Energia CPU" / "Aplicar.bat")),
                ("Abrir InSpectre (mitigaciones CPU)", self.open_inspectre),
                ("Prioridad alta: Juegos", lambda: self.import_reg(RECURSOS / "Prioridad CPU" / "Prioridad Juegos.reg")),
                ("Prioridad Windows", lambda: self.import_reg(RECURSOS / "Prioridad CPU" / "Prioridad Windows.reg")),
                ("Revertir prioridad CPU", lambda: self.import_reg(RECURSOS / "Prioridad CPU" / "Revertir Cambios.reg")),
            ]),
            ("Disco SSD", [
                ("Optimizar SSD", lambda: self.import_reg(RECURSOS / "Optimizar SSD" / "Optimizar SSD.reg")),
                ("Revertir cambios SSD", lambda: self.import_reg(RECURSOS / "Optimizar SSD" / "Revertir Cambios.reg")),
            ]),
            ("Servicios y telemetria", [
                ("Optimizar servicios", lambda: self.import_reg(RECURSOS / "Servicios" / "Optimizar Servicios.reg")),
                ("Revertir servicios", lambda: self.import_reg(RECURSOS / "Servicios" / "Revertir Cambios.reg")),
                ("Deshabilitar telemetria (.reg)", lambda: self.import_reg(RECURSOS / "Telemetria" / "Deshabilitar Telemetria.reg")),
                ("Revertir telemetria", lambda: self.import_reg(RECURSOS / "Telemetria" / "Revertir Cambios.reg")),
            ]),
        ]

        for idx, (title, actions) in enumerate(cards):
            self._card(tab, title, actions).grid(
                row=idx // 2, column=idx % 2, sticky="nsew", padx=6, pady=6)

    def _build_tab_herramientas(self):
        tab = self._new_tab("  Herramientas  ")
        for i in range(2):
            tab.columnconfigure(i, weight=1)

        cards = [
            ("Windows Defender", [
                ("Deshabilitar Defender", self.ask_disable_defender),
                ("Habilitar Defender", self.do_enable_defender),
            ], False),
            ("Windows Update", [
                ("Deshabilitar Windows Update", self.ask_disable_update),
                ("Habilitar Windows Update", self.do_enable_update),
            ], False),
            ("Modo temporal (seguro)", [
                ("Pausar Windows Defender (temporal)", self.do_pause_defender),
                ("Pausar Windows Update (temporal)", self.do_pause_update),
                ("Reactivar Defender + Update", self.do_resume_all),
            ], False),
            ("Mantenimiento", [
                ("Crear punto de restauracion", self.do_restore_point),
                ("Borrar archivos temporales", self.do_temp_files),
            ], False),
            ("Red", [
                ("Limpiar cache DNS", lambda: self.run_steps(
                    "Cache DNS", [("Limpiando cache DNS", ["ipconfig /flushdns"])])),
                ("Deshabilitar Teredo", lambda: self.run_steps(
                    "Teredo", [("Deshabilitando Teredo", ["netsh interface teredo set state disabled"])])),
            ], False),
        ]

        for idx, (title, actions, danger) in enumerate(cards):
            span = 2 if idx == len(cards) - 1 and len(cards) % 2 else 1
            self._card(tab, title, actions, danger).grid(
                row=idx // 2, column=idx % 2, columnspan=span,
                sticky="nsew", padx=6, pady=6)

    def _build_tab_acerca(self):
        tab = self._new_tab("  Acerca de  ", padding=18)

        card = tk.Frame(tab, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        card.pack(fill="x")
        inner = tk.Frame(card, bg=PANEL)
        inner.pack(fill="x", padx=22, pady=20)

        top_row = tk.Frame(inner, bg=PANEL)
        top_row.pack(fill="x", pady=(0, 10))
        self.about_logo = self._load_photo("logo_96.png") or self._load_photo("logo.png")
        if self.about_logo is not None:
            tk.Label(top_row, image=self.about_logo, bg=PANEL, bd=0).pack(
                side="left", padx=(0, 16))
        info = tk.Frame(top_row, bg=PANEL)
        info.pack(side="left", anchor="w")
        tk.Label(info, text="PylandTweaks", bg=PANEL, fg=FG,
                 font=(FONT_BOLD, 20)).pack(anchor="w")
        tk.Label(info, text="Version 5.8", bg=PANEL, fg=ACCENT2,
                 font=(FONT_BOLD, 10)).pack(anchor="w", pady=(2, 0))

        tk.Label(inner, text="Un optimizador de PC sencillo y eficiente para aumentar el "
                             "rendimiento en equipos de gama baja.",
                 bg=PANEL, fg=MUTED, justify="left", font=(FONT, 9),
                 wraplength=820).pack(anchor="w", pady=(0, 12))

        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=(0, 14))

        features = [
            "Optimizaciones recomendadas y del sistema",
            "Mem Reduct, compresion de RAM y plan de energia",
            "Ajustes de SSD, servicios y telemetria",
            "Control de Windows Defender y Windows Update",
            "Modo temporal seguro (pausar y reactivar cuando quieras)",
        ]
        for item in features:
            row = tk.Frame(inner, bg=PANEL)
            row.pack(fill="x", pady=2)
            dot = tk.Canvas(row, width=8, height=8, bg=PANEL, highlightthickness=0)
            dot.create_oval(1, 1, 7, 7, fill=ACCENT, outline=ACCENT)
            dot.pack(side="left", padx=(0, 9), pady=4)
            tk.Label(row, text=item, bg=PANEL, fg=FG, font=(FONT, 9)).pack(side="left")

        tk.Frame(inner, bg=BORDER, height=1).pack(fill="x", pady=(14, 14))

        tk.Label(inner, text="Creditos especiales a Chris Titus por las optimizaciones.",
                 bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(anchor="w")
        tk.Label(inner, text="Consejo: crea un punto de restauracion antes de aplicar cambios.",
                 bg=PANEL, fg=YELLOW, font=(FONT, 9)).pack(anchor="w", pady=(6, 0))

    def _build_log(self):
        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="both", expand=False, padx=16, pady=(0, 6))

        header = tk.Frame(frame, bg=BG)
        header.pack(fill="x", pady=(0, 4))
        tk.Label(header, text="REGISTRO", bg=BG, fg=MUTED,
                 font=(FONT_BOLD, 8)).pack(side="left")

        box = tk.Frame(frame, bg=PANEL2, highlightbackground=BORDER, highlightthickness=1)
        box.pack(fill="both", expand=True)
        self.log_text = tk.Text(box, height=8, bg=PANEL2, fg=FG, insertbackground=FG,
                                selectbackground=ACCENT, relief="flat", bd=0,
                                font=("Consolas", 9), wrap="word", padx=12, pady=10)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scroll.set, state="disabled")

    def _build_status(self):
        bar = tk.Frame(self.root, bg=PANEL2, highlightbackground=BORDER, highlightthickness=1)
        bar.pack(fill="x", side="bottom")
        self.status_dot = tk.Canvas(bar, width=8, height=8, bg=PANEL2, highlightthickness=0)
        self.status_dot.create_oval(1, 1, 7, 7, fill=GREEN, outline=GREEN)
        self.status_dot.pack(side="left", padx=(14, 7), pady=7)
        self.status = tk.Label(bar, text="Listo", bg=PANEL2, fg=MUTED, font=(FONT, 9))
        self.status.pack(side="left", pady=7)
        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=180,
                                        style="Horizontal.TProgressbar")
        self.progress.pack(side="right", padx=14, pady=7)

    # -------------------------------------------------------------- logging
    def log(self, msg):
        self.root.after(0, self._append_log, str(msg) + "\n")

    def _append_log(self, msg):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def set_status(self, text):
        self.root.after(0, lambda: self.status.configure(text=text))

    # ------------------------------------------------------------- execution
    def start_task(self, title, worker, on_done=None):
        if self.busy:
            messagebox.showinfo("En curso", "Espera a que termine la tarea actual.")
            return
        self.busy = True
        self.set_status("Ejecutando: " + title)
        self.root.after(0, self.progress.start, 12)

        def runner():
            try:
                worker()
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR: {exc}")
            finally:
                self.root.after(0, self._finish)
                if on_done:
                    self.root.after(0, on_done)

        threading.Thread(target=runner, daemon=True).start()

    def _finish(self):
        self.busy = False
        self.progress.stop()
        self.set_status("Listo")
        self.log("")

    def exec_cmd(self, command):
        self.log("> " + command)
        try:
            result = subprocess.run(
                command, shell=True, cwd=str(BASE),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW,
            )
            out = result.stdout.decode("mbcs", errors="replace").strip()
            if out:
                self.log(out)
        except Exception as exc:  # noqa: BLE001
            self.log(f"ERROR al ejecutar: {exc}")

    def run_steps(self, title, steps, confirm=None, on_done=None):
        if self.busy:
            messagebox.showinfo("En curso", "Espera a que termine la tarea actual.")
            return
        if confirm and not messagebox.askyesno("Confirmar", confirm):
            return

        def worker():
            self.log(f"### {title} ###")
            for label, cmds in steps:
                self.log(f"\n=== {label} ===")
                for cmd in cmds:
                    self.exec_cmd(cmd)
            self.log("\n--- Tarea terminada ---")

        self.start_task(title, worker, on_done=on_done)

    # ---------------------------------------------------------- reg / files
    def import_reg(self, path):
        path = Path(path)
        if not path.exists():
            messagebox.showerror("No encontrado", f"No existe el archivo:\n{path}")
            return
        name = path.stem
        if not messagebox.askyesno("Confirmar", f"¿Aplicar «{name}»?\n\n{path.name}"):
            return
        self.run_steps(name, [(name, [f'reg import {q(path)}'])])

    def run_file(self, path):
        path = Path(path)
        if not path.exists():
            messagebox.showerror("No encontrado", f"No existe el archivo:\n{path}")
            return
        if not messagebox.askyesno("Confirmar", f"¿Ejecutar «{path.name}»?"):
            return
        self.run_steps(path.name, [(path.name, [q(path)])])

    def open_program(self, path):
        path = Path(path)
        if not path.exists():
            messagebox.showerror("No encontrado", f"No existe:\n{path}")
            return
        try:
            subprocess.Popen([str(path)], cwd=str(path.parent))
            self.log(f"Abierto: {path.name}")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", f"No se pudo abrir:\n{exc}")

    def open_memreduct(self):
        self.open_program(RECURSOS / "Mem Reduct RAM" / "memreduct.exe")

    def open_inspectre(self):
        self.open_program(RECURSOS / "Mitigaciones CPU" / "InSpectre.exe")

    # -------------------------------------------------------------- commands
    def cmds_svchost(self):
        ram = total_phys_kb() + 1024000
        return [reg_add(r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control",
                        "SvcHostSplitThresholdInKB", "REG_DWORD", str(ram))]

    def cmds_services_manual(self):
        return [f'sc config "{s}" start= demand' for s in SERVICES_MANUAL]

    def cmds_services_disabled(self):
        return [f'sc config "{s}" start= disabled' for s in SERVICES_DISABLED]

    def cmds_update_tasks(self, enable=False):
        flag = "/Enable" if enable else "/Disable"
        return [f'schtasks /Change /TN "{t}" {flag}' for t in UPDATE_TASKS]

    def cmds_telemetry_tasks(self, enable=False):
        flag = "/Enable" if enable else "/Disable"
        return [f'schtasks /Change /TN "{t}" {flag}' for t in TELEMETRY_TASKS]

    def cmds_telemetry_tasks_disable(self):
        return self.cmds_telemetry_tasks(False)

    def cmds_game_priority(self):
        base = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"
        out = []
        for exe in GAME_PRIORITY:
            out.append(reg_add(base + "\\" + exe + "\\PerfOptions", "CpuPriorityClass", "REG_DWORD", "6"))
        out.append(reg_add(base + r"\MsMpEng.exe\PerfOptions", "CpuPriorityClass", "REG_DWORD", "1"))
        out.append(reg_add(base + r"\ShellExperienceHost.exe\PerfOptions", "CpuPriorityClass", "REG_DWORD", "5"))
        out.append(reg_add(base + r"\svchost.exe\PerfOptions", "CpuPriorityClass", "REG_DWORD", "5"))
        return out

    def cmds_services_default(self):
        out = []
        for s in SERVICES_MANUAL:
            out.append(f'sc config "{s}" start= {SERVICE_DEFAULT_START.get(s, "demand")}')
        for s in SERVICES_DISABLED:
            out.append(f'sc config "{s}" start= {SERVICE_DEFAULT_START.get(s, "demand")}')
        return out

    def cmds_regs_revert(self):
        cmds = regs(VISUAL_REGS_REVERT) + regs(TUNING_REGS_REVERT) + regs(WIFI_REGS_REVERT)
        cmds += [reg_del(key, value) for key, value in TUNING_REGS_DELETE]
        cmds += [reg_del(c[0], c[1]) for c in TELEMETRY_REGS]
        return cmds

    def cmds_game_priority_revert(self):
        base = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options"
        out = []
        for exe in GAME_PRIORITY:
            out.append(reg_del(base + "\\" + exe + "\\PerfOptions", "CpuPriorityClass"))
        for exe in ("MsMpEng.exe", "ShellExperienceHost.exe", "svchost.exe"):
            out.append(reg_del(base + "\\" + exe + "\\PerfOptions", "CpuPriorityClass"))
        return out

    def cmds_latency_power(self):
        return [
            'powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61',
            'powercfg -setactive e9a42b02-d5df-448d-aa00-03f14749eb61',
            'powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 100',
            'powercfg -setdcvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 100',
            'powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR CPMINCORES 100',
            'powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR CPMAXCORES 100',
            'powercfg -setacvalueindex SCHEME_CURRENT SUB_PCIEXPRESS ASPM 0',
            'powercfg -setacvalueindex SCHEME_CURRENT 2a737441-1930-4402-8d77-b2bebba308a3 48e6b7a6-50f5-4782-a5d4-53bb8f07e226 0',
            'powercfg -setacvalueindex SCHEME_CURRENT SUB_DISK DISKIDLE 0',
            'powercfg -setactive SCHEME_CURRENT',
        ]

    def cmds_latency_power_revert(self):
        return [
            'powercfg -setactive 381b4222-f694-41f0-9685-ff5bb260df2e',
            'powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 5',
            'powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR CPMINCORES 0',
            'powercfg -setactive SCHEME_CURRENT',
        ]

    # ------------------------------------------------------------- acciones
    def do_game_priority(self):
        self.run_steps("Prioridad de juegos", [("Alta prioridad en juegos", self.cmds_game_priority())])

    def ask_latency(self):
        self.run_steps("Optimizaciones de latencia", [
            ("Aplicando plan de energia", self.cmds_latency_power()),
            ("Aplicando ajustes de juegos y entrada", regs(LATENCY_REGS)),
        ], confirm="Se aplicaran ajustes seguros de latencia:\n"
                   "  - Plan Ultimate/High Performance y CPU al 100%\n"
                   "  - Game Mode ON y Game Bar/DVR OFF\n"
                   "  - Optimizaciones de pantalla completa OFF\n"
                   "  - Aceleracion del raton OFF\n\n"
                   "Al terminar deberas REINICIAR el equipo.\n\n"
                   "¿Continuar?", on_done=self.ask_restart)

    def do_latency_revert(self):
        self.run_steps("Revertir latencia", [
            ("Restaurando plan de energia", self.cmds_latency_power_revert()),
            ("Restaurando ajustes de juegos y entrada", regs(LATENCY_REGS_REVERT)),
        ], confirm="¿Deshacer las optimizaciones de latencia y volver a los valores normales?\n\n"
                   "Reinicia el equipo al terminar.", on_done=self.ask_restart)

    def open_gamemode(self):
        try:
            os.startfile("ms-settings:gaming-gamemode")
            self.log("Abriendo ajustes de Modo juego...")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", f"No se pudo abrir Ajustes:\n{exc}")

    def do_restore_point(self):
        self.run_steps("Punto de restauracion", [
            ("Creando punto de restauracion", [
                'powershell.exe -NoProfile -Command "Enable-ComputerRestore -Drive \'%SystemDrive%\'"',
                'powershell.exe -NoProfile -Command "Checkpoint-Computer -Description \'Script Optimizador\'"',
            ])
        ])

    def do_temp_files(self):
        if not messagebox.askyesno("Confirmar", "¿Borrar archivos temporales y de Prefetch?"):
            return
        self.run_steps("Archivos temporales", [
            ("Borrando archivos temporales", [
                'del /S /F /Q "%temp%"',
                'del /S /F /Q "%WINDIR%\\Temp\\*.*"',
                'del /S /F /Q "%WINDIR%\\Prefetch\\*.*"',
                'del /S /F /Q "%WINDIR%\\logs\\cbs\\*.log"',
                'del /S /F /Q "%WINDIR%\\Logs\\MoSetup\\*.log"',
                'del /S /F /Q "%WINDIR%\\Panther\\*.log"',
                'del /S /F /Q "%WINDIR%\\inf\\*.log"',
                'del /S /F /Q "%WINDIR%\\logs\\*.log"',
                'del /S /F /Q "%WINDIR%\\SoftwareDistribution\\*.log"',
                'del /S /F /Q "%WINDIR%\\Microsoft.NET\\*.log"',
                'net stop wuauserv',
                'net stop UsoSvc',
                'del /S /F /Q "%WINDIR%\\SoftwareDistribution"',
            ])
        ])

    def ask_restart(self):
        self.log("Recuerda: reinicia el equipo para aplicar todos los cambios.")
        if messagebox.askyesno(
                "Reiniciar para aplicar cambios",
                "Las optimizaciones se aplican por completo al reiniciar el equipo.\n\n"
                "¿Quieres reiniciar ahora? Se cerraran todos los programas abiertos."):
            try:
                subprocess.Popen(
                    'shutdown /r /t 15 /c "Reiniciando para aplicar las optimizaciones"',
                    shell=True, creationflags=CREATE_NO_WINDOW)
                self.log("Reinicio programado en 15 segundos. Guarda tu trabajo.")
            except Exception as exc:  # noqa: BLE001
                self.log(f"No se pudo programar el reinicio: {exc}")
        else:
            self.log("Puedes reiniciar mas tarde desde Inicio > Reiniciar.")

    def ask_recommended(self):
        if not messagebox.askyesno(
                "Optimizaciones recomendadas",
                "Se aplicaran muchas optimizaciones al sistema.\n\n"
                "Al terminar deberas REINICIAR el equipo para que se apliquen.\n\n"
                "¿Seguro que quieres continuar?"):
            return

        steps = [
            ("Reduciendo procesos svchost", self.cmds_svchost()),
            ("Deshabilitando WiFi Sense", regs(WIFI_REGS)),
            ("Deshabilitando tareas de Windows Update", self.cmds_update_tasks(False)),
            ("Optimizando apartado visual", regs(VISUAL_REGS)),
            ("Deshabilitando Teredo", ["netsh interface teredo set state disabled"]),
            ("Deshabilitando tareas de telemetria", self.cmds_telemetry_tasks_disable()),
            ("Deshabilitando telemetria (registro)", regs(TELEMETRY_REGS)),
            ("Aplicando ajustes de registro", regs(TUNING_REGS)),
            ("Estableciendo servicios en manual", self.cmds_services_manual()),
            ("Deshabilitando servicios", self.cmds_services_disabled()),
            ("Limpiando cache DNS", ["ipconfig /flushdns"]),
        ]
        self.run_steps("Optimizaciones recomendadas", steps, on_done=self.ask_restart)

    def ask_disable_defender(self):
        if not messagebox.askyesno(
                "Deshabilitar Defender",
                "Deshabilitar Windows Defender deja el equipo SIN proteccion antivirus.\n\n"
                "¿Continuar de todos modos?"):
            return
        base = r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows Defender"
        cmds = [
            reg_add(r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\WinDefend", "Start", "REG_DWORD", "4"),
            reg_add(r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\SecurityHealthService", "Start", "REG_DWORD", "4"),
            reg_add(r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\WdNisSvc", "Start", "REG_DWORD", "4"),
            reg_add(r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Sense", "Start", "REG_DWORD", "4"),
            reg_add(r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\wscsvc", "Start", "REG_DWORD", "4"),
            reg_add(base, "DisableAntiSpyware", "REG_DWORD", "1"),
            reg_add(base, "DisableRoutinelyTakingAction", "REG_DWORD", "1"),
            reg_add(base, "ServiceKeepAlive", "REG_DWORD", "0"),
            reg_add(base + r"\Real-Time Protection", "DisableBehaviorMonitoring", "REG_DWORD", "1"),
            reg_add(base + r"\Real-Time Protection", "DisableIOAVProtection", "REG_DWORD", "1"),
            reg_add(base + r"\Real-Time Protection", "DisableOnAccessProtection", "REG_DWORD", "1"),
            reg_add(base + r"\Real-Time Protection", "DisableRealtimeMonitoring", "REG_DWORD", "1"),
            reg_add(base + r"\Reporting", "DisableEnhancedNotifications", "REG_DWORD", "1"),
            reg_add(base + r"\Security Center\Notifications", "DisableNotifications", "REG_DWORD", "1"),
            reg_add(r"HKEY_CURRENT_USER\Software\Policies\Microsoft\Windows\CurrentVersion\PushNotifications", "NoToastApplicationNotification", "REG_DWORD", "1"),
            reg_add(r"HKEY_CURRENT_USER\Software\Policies\Microsoft\Windows\CurrentVersion\PushNotifications", "NoToastApplicationNotificationOnLockScreen", "REG_DWORD", "1"),
        ]
        self.run_steps("Deshabilitar Defender", [("Deshabilitando Windows Defender", cmds)])

    def cmds_enable_defender(self):
        return [
            reg_add(r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\WinDefend", "Start", "REG_DWORD", "2"),
            reg_add(r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\SecurityHealthService", "Start", "REG_DWORD", "2"),
            reg_add(r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\WdNisSvc", "Start", "REG_DWORD", "2"),
            reg_add(r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\Sense", "Start", "REG_DWORD", "2"),
            reg_add(r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Services\wscsvc", "Start", "REG_DWORD", "2"),
            reg_add(r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows Defender", "DisableAntiSpyware", "REG_DWORD", "0"),
            reg_add(r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows Defender", "DisableRoutinelyTakingAction", "REG_DWORD", "0"),
            reg_add(r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows Defender", "ServiceKeepAlive", "REG_DWORD", "1"),
            reg_add(r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection", "DisableBehaviorMonitoring", "REG_DWORD", "0"),
            reg_add(r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection", "DisableIOAVProtection", "REG_DWORD", "0"),
            reg_add(r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection", "DisableOnAccessProtection", "REG_DWORD", "0"),
            reg_add(r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection", "DisableRealtimeMonitoring", "REG_DWORD", "0"),
            reg_add(r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows Defender\Reporting", "DisableEnhancedNotifications", "REG_DWORD", "0"),
            reg_add(r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows Defender Security Center\Notifications", "DisableNotifications", "REG_DWORD", "0"),
            reg_add(r"HKEY_CURRENT_USER\Software\Policies\Microsoft\Windows\CurrentVersion\PushNotifications", "NoToastApplicationNotification", "REG_DWORD", "0"),
            reg_add(r"HKEY_CURRENT_USER\Software\Policies\Microsoft\Windows\CurrentVersion\PushNotifications", "NoToastApplicationNotificationOnLockScreen", "REG_DWORD", "0"),
        ]

    def do_enable_defender(self):
        self.run_steps("Habilitar Defender", [("Habilitando Windows Defender", self.cmds_enable_defender())])

    def ask_disable_update(self):
        if not messagebox.askyesno(
                "Deshabilitar Windows Update",
                "Esto detiene y deshabilita los servicios de actualizacion y renombra\n"
                "bibliotecas del sistema. ¿Continuar?"):
            return

        loops = (
            'for %i in (WaaSMedicSvc, wuaueng) do ('
            'takeown /f C:\\Windows\\System32\\%i.dll && '
            'icacls C:\\Windows\\System32\\%i.dll /grant *S-1-1-0:F && '
            'rename C:\\Windows\\System32\\%i.dll %i_BAK.dll && '
            'icacls C:\\Windows\\System32\\%i_BAK.dll /setowner "NT SERVICE\\TrustedInstaller" && '
            'icacls C:\\Windows\\System32\\%i_BAK.dll /remove *S-1-1-0)'
        )
        cmds = [
            'for %i in (wuauserv, UsoSvc, uhssvc, WaaSMedicSvc) do (net stop %i & sc config %i start= disabled & sc failure %i reset= 0 actions= "")',
            loops,
            reg_add(r"HKLM\SYSTEM\CurrentControlSet\Services\WaaSMedicSvc", "Start", "REG_DWORD", "4"),
            reg_add(r"HKLM\SYSTEM\CurrentControlSet\Services\WaaSMedicSvc", "FailureActions", "REG_BINARY",
                    "000000000000000000000000030000001400000000000000c0d4010000000000e09304000000000000000000"),
            reg_add(r"HKLM\Software\Policies\Microsoft\Windows\WindowsUpdate\AU", "NoAutoUpdate", "REG_DWORD", "1"),
            'erase /f /s /q c:\\windows\\softwaredistribution\\*.* & rmdir /s /q c:\\windows\\softwaredistribution',
        ] + self.cmds_update_tasks(False)
        self.run_steps("Deshabilitar Windows Update", [("Deshabilitando Windows Update", cmds)])

    def cmds_enable_update(self):
        loops = (
            'for %i in (WaaSMedicSvc, wuaueng) do ('
            'takeown /f C:\\Windows\\System32\\%i_BAK.dll && '
            'icacls C:\\Windows\\System32\\%i_BAK.dll /grant *S-1-1-0:F && '
            'rename C:\\Windows\\System32\\%i_BAK.dll %i.dll && '
            'icacls C:\\Windows\\System32\\%i.dll /setowner "NT SERVICE\\TrustedInstaller" && '
            'icacls C:\\Windows\\System32\\%i.dll /remove *S-1-1-0)'
        )
        return [
            'sc config wuauserv start= auto',
            'sc config UsoSvc start= auto',
            'sc config uhssvc start= delayed-auto',
            loops,
            reg_add(r"HKLM\SYSTEM\CurrentControlSet\Services\WaaSMedicSvc", "Start", "REG_DWORD", "3"),
            reg_add(r"HKLM\SYSTEM\CurrentControlSet\Services\WaaSMedicSvc", "FailureActions", "REG_BINARY",
                    "840300000000000000000000030000001400000001000000c0d4010001000000e09304000000000000000000"),
            'reg delete "HKLM\\Software\\Policies\\Microsoft\\Windows\\WindowsUpdate\\AU" /v "NoAutoUpdate" /f',
        ] + self.cmds_update_tasks(True)

    def do_enable_update(self):
        self.run_steps("Habilitar Windows Update", [("Habilitando Windows Update", self.cmds_enable_update())])

    # ------------------------------------------------ modo temporal seguro
    @staticmethod
    def _defender_ps(disabled):
        state = "$true" if disabled else "$false"
        return (
            'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command '
            f'"Set-MpPreference -DisableRealtimeMonitoring {state} '
            f'-DisableBehaviorMonitoring {state} -DisableIOAVProtection {state} '
            f'-DisableScriptScanning {state}"'
        )

    def cmds_pause_defender(self):
        base = r"HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Microsoft\Windows Defender"
        return [
            self._defender_ps(True),
            reg_add(base, "DisableAntiSpyware", "REG_DWORD", "1"),
            reg_add(base, "DisableRoutinelyTakingAction", "REG_DWORD", "1"),
            reg_add(base + r"\Real-Time Protection", "DisableBehaviorMonitoring", "REG_DWORD", "1"),
            reg_add(base + r"\Real-Time Protection", "DisableIOAVProtection", "REG_DWORD", "1"),
            reg_add(base + r"\Real-Time Protection", "DisableOnAccessProtection", "REG_DWORD", "1"),
            reg_add(base + r"\Real-Time Protection", "DisableRealtimeMonitoring", "REG_DWORD", "1"),
        ]

    def do_pause_defender(self):
        if not messagebox.askyesno(
                "Pausar Windows Defender (temporal)",
                "Se desactivara la proteccion en tiempo real de Windows Defender.\n"
                "Mientras este pausado el equipo quedara sin antivirus activo.\n\n"
                "Es temporal: usa «Reactivar Defender + Update» para volver a activarlo.\n\n"
                "¿Continuar?"):
            return
        self.run_steps("Pausar Defender (temporal)", [
            ("Pausando proteccion en tiempo real", self.cmds_pause_defender())
        ])

    def cmds_pause_update(self):
        return [
            'net stop wuauserv',
            'net stop UsoSvc',
            'net stop WaaSMedicSvc',
            'sc config wuauserv start= disabled',
            'sc config UsoSvc start= disabled',
            reg_add(r"HKLM\SYSTEM\CurrentControlSet\Services\WaaSMedicSvc", "Start", "REG_DWORD", "4"),
            reg_add(r"HKLM\Software\Policies\Microsoft\Windows\WindowsUpdate\AU", "NoAutoUpdate", "REG_DWORD", "1"),
        ] + self.cmds_update_tasks(False)

    def do_pause_update(self):
        if not messagebox.askyesno(
                "Pausar Windows Update (temporal)",
                "Se detendran y pausaran los servicios de actualizacion.\n"
                "No se borran archivos ni se renombran librerias del sistema.\n\n"
                "Es temporal: usa «Reactivar Defender + Update» para volver a activarlo.\n\n"
                "¿Continuar?"):
            return
        self.run_steps("Pausar Windows Update (temporal)", [
            ("Pausando Windows Update", self.cmds_pause_update())
        ])

    def do_resume_all(self):
        if not messagebox.askyesno(
                "Reactivar Defender + Update",
                "Se reactivaran Windows Defender y Windows Update con sus valores normales.\n\n"
                "¿Continuar?"):
            return
        steps = [
            ("Reactivando Windows Defender",
             self.cmds_enable_defender() + ['net start WinDefend', self._defender_ps(False)]),
            ("Reactivando Windows Update",
             self.cmds_enable_update() + ['net start wuauserv', 'net start UsoSvc']),
        ]
        self.run_steps("Reactivar Defender + Update", steps)

    def open_restore(self):
        try:
            subprocess.Popen(["rstrui.exe"])
            self.log("Abriendo Restaurar sistema...")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", f"No se pudo abrir Restaurar sistema:\n{exc}")

    def ask_revert_all(self):
        if self.busy:
            messagebox.showinfo("En curso", "Espera a que termine la tarea actual.")
            return
        if not messagebox.askyesno(
                "Revertir optimizaciones",
                "Se restauraran los valores predeterminados de Windows:\n"
                "  - Servicios\n"
                "  - Tareas de telemetria y Windows Update\n"
                "  - Ajustes de registro y rendimiento\n"
                "  - Prioridad de juegos, GameDVR y Teredo\n"
                "  - Windows Defender y Windows Update\n\n"
                "Se recomienda reiniciar el equipo al terminar.\n\n¿Continuar?"):
            return

        def worker():
            self.log("### REVIRTIENDO OPTIMIZACIONES ###")
            steps = [
                ("Restaurando servicios", self.cmds_services_default()),
                ("Restaurando ajustes de registro", self.cmds_regs_revert()),
                ("Restaurando prioridad de juegos", self.cmds_game_priority_revert()),
                ("Restaurando GameDVR", [
                    reg_del(r"HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\GameDVR",
                            "GameDVR_DXGIHonorFSEWindowsCompatible"),
                ]),
                ("Restaurando apps en segundo plano", [
                    reg_del(r"HKEY_LOCAL_MACHINE\Software\Microsoft\Windows\CurrentVersion\Authentication\LogonUI",
                            "GlobalUserDisabled"),
                ]),
                ("Restaurando umbral de svchost", [
                    reg_del(r"HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control", "SvcHostSplitThresholdInKB"),
                ]),
                ("Reactivando tareas de telemetria", self.cmds_telemetry_tasks(True)),
                ("Reactivando tareas de Windows Update", self.cmds_update_tasks(True)),
                ("Restaurando Teredo", ["netsh interface teredo set state default"]),
                ("Restaurando latencia",
                 self.cmds_latency_power_revert() + regs(LATENCY_REGS_REVERT)),
                ("Restaurando Windows Defender", self.cmds_enable_defender()),
                ("Restaurando Windows Update", self.cmds_enable_update()),
            ]
            for label, cmds in steps:
                self.log(f"\n=== {label} ===")
                for cmd in cmds:
                    self.exec_cmd(cmd)
            self.log("\n--- Reversion terminada. Reinicia el equipo para aplicar los cambios. ---")

        self.start_task("Revertir optimizaciones", worker, on_done=self.ask_restart)


def main():
    set_app_user_model_id()
    if not is_admin():
        run_as_admin()
        sys.exit(0)

    root = tk.Tk()
    app = OptimizadorApp(root)
    app.log("Consejo: crea un punto de restauracion antes de aplicar cambios.")
    root.mainloop()


if __name__ == "__main__":
    main()
