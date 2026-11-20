# -*- coding: utf-8 -*-
"""
PylandTweaks V5.9 - Interfaz grafica (Tkinter)
Optimizador de rendimiento para equipos de gama baja.
"""

import os
import re
import sys
import json
import time
import ctypes
import queue
import subprocess
import threading
from pathlib import Path
import tkinter as tk

import perifericos
import onboarding_gui
from tkinter import ttk, messagebox, simpledialog, filedialog

try:
    import winreg
except ImportError:  # pragma: no cover - solo Windows
    winreg = None


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
            "PylandTweaks.PylandTweaks.5.9")
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
# Utilidades de archivos de configuracion (INI / XML / propiedades)
# ---------------------------------------------------------------------------
def read_text_meta(path):
    """Lee un archivo de texto conservando su codificacion original."""
    path = Path(path)
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        return data.decode("utf-16", errors="replace"), "utf-16"
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig", errors="replace"), "utf-8-sig"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("mbcs", errors="replace"), "mbcs"


def write_text_meta(path, text, encoding):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if encoding not in ("utf-8", "utf-8-sig", "utf-16", "mbcs"):
        encoding = "utf-8"
    path.write_bytes(text.encode(encoding, errors="replace"))


def ini_set(text, section, values):
    """Actualiza claves dentro de una seccion INI conservando el resto."""
    lines = (text or "").splitlines()
    sec_re = re.compile(r"^\s*\[" + re.escape(section) + r"\]\s*$", re.I)
    start = None
    for i, line in enumerate(lines):
        if sec_re.match(line):
            start = i
            break
    if start is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append(f"[{section}]")
        lines.extend(f"{k}={v}" for k, v in values.items())
        return "\n".join(lines) + "\n"

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^\s*\[.+\]\s*$", lines[j]):
            end = j
            break

    seen = set()
    for j in range(start + 1, end):
        m = re.match(r"^(\s*)([^=;#\s][^=]*?)\s*=\s*(.*)$", lines[j])
        if not m:
            continue
        key = m.group(2).strip()
        for wanted, value in values.items():
            if key.lower() == wanted.lower():
                lines[j] = f"{m.group(1)}{wanted}={value}"
                seen.add(wanted.lower())
                break

    extra = [f"{k}={v}" for k, v in values.items() if k.lower() not in seen]
    if extra:
        lines[end:end] = extra
    return "\n".join(lines) + "\n"


def quoted_kv_set(text, values):
    """Actualiza pares "clave" "valor" (formato de configuracion de CS2)."""
    text = text or ""
    for key, value in values.items():
        pattern = re.compile(r'("' + re.escape(key) + r'"\s*)"[^"]*"', re.I)
        if pattern.search(text):
            text = pattern.sub(
                lambda m, v=str(value): m.group(1) + '"' + v + '"',
                text, count=1)
            continue
        idx = text.rfind("}")
        line = f'\t"{key}"\t\t"{value}"\n'
        if idx == -1:
            text = text + ("\n" if text and not text.endswith("\n") else "") + line
        else:
            text = text[:idx] + line + text[idx:]
    return text


def xml_set_values(text, values, parent_tag="graphics"):
    """Cambia atributos value="..." de un XML (formato de GTA V)."""
    text = text or ""
    for tag, value in values.items():
        pattern = re.compile(
            r'(<' + re.escape(tag) + r'\b[^>]*\bvalue\s*=\s*")[^"]*(")',
            re.I)
        if pattern.search(text):
            text = pattern.sub(
                lambda m, v=str(value): m.group(1) + v + m.group(2),
                text, count=1)
            continue
        close = re.search(r"</" + re.escape(parent_tag) + r"\s*>", text, re.I)
        if not close:
            continue
        line = f'\t\t<{tag} value="{value}" />\n'
        text = text[:close.start()] + line + text[close.start():]
    return text


def props_set(text, values):
    """Actualiza un archivo clave:valor (formato de Minecraft options.txt)."""
    lines = (text or "").splitlines()
    seen = set()
    for i, line in enumerate(lines):
        if ":" not in line or line.lstrip().startswith("#"):
            continue
        key = line.split(":", 1)[0].strip()
        for wanted, value in values.items():
            if key == wanted:
                lines[i] = f"{wanted}:{value}"
                seen.add(wanted)
                break
    lines.extend(f"{k}:{v}" for k, v in values.items() if k not in seen)
    return "\n".join(lines) + "\n"


def process_running(exe_name):
    if not exe_name:
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe_name}", "/NH"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            creationflags=CREATE_NO_WINDOW)
        out = result.stdout.decode("mbcs", errors="replace").lower()
        return exe_name.lower() in out and "no hay tareas" not in out
    except Exception:  # noqa: BLE001
        return False


def classify_gpu(name, vram=0):
    text = (name or "").lower()
    integrated = (
        "intel(r) uhd", "intel(r) hd", "intel(r) iris", "hd graphics",
        "radeon(tm) graphics", "radeon graphics", "vega 8", "vega 11",
        "microsoft basic display", "llvmpipe",
    )
    if any(token in text for token in integrated):
        return "integrada"
    if any(token in text for token in ("nvidia", "geforce", "rtx", "gtx", "quadro")):
        return "dedicada"
    if any(token in text for token in ("radeon rx", "radeon pro", "arc a", "arc b")):
        return "dedicada"
    return "dedicada" if (vram or 0) >= 2 else "integrada"


def parse_ps_json(text):
    for line in reversed((text or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                if isinstance(data, dict):
                    return data
            except Exception:  # noqa: BLE001
                continue
    return {}


# ---------------------------------------------------------------------------
# Macro: entrada sintetica de baja latencia (sin dependencias externas)
# ---------------------------------------------------------------------------
VK_F = 0x46
VK_LBUTTON = 0x01
VK_F4 = 0x73
VK_F8 = 0x77
VK_F9 = 0x78
VK_END = 0x23
VK_DELETE = 0x2E

KEY_ALIASES = {
    "espacio": 0x20, "space": 0x20, "enter": 0x0D, "intro": 0x0D,
    "tab": 0x09, "shift": 0x10, "ctrl": 0x11, "control": 0x11,
    "alt": 0x12, "supr": VK_DELETE, "delete": VK_DELETE, "end": VK_END,
}


def vk_from_text(text):
    """Convierte 'f', 'q', 'shift'... en un codigo virtual de Windows."""
    text = (text or "").strip()
    if not text:
        return None
    if text.lower() in KEY_ALIASES:
        return KEY_ALIASES[text.lower()]
    if len(text) == 1:
        result = ctypes.windll.user32.VkKeyScanW(ord(text))
        if result != -1:
            return result & 0xFF
    return None

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

WH_KEYBOARD_LL = 13
WH_MOUSE_LL = 14
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
LLKHF_INJECTED = 0x10
LLMHF_INJECTED = 0x01
PM_REMOVE = 0x0001

EXTENDED_VKS = {
    0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28,
    0x2D, 0x2E, 0x90, 0x6F, 0xA3, 0xA5,
}


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_uint),
        ("time", ctypes.c_uint),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_uint),
        ("dwFlags", ctypes.c_uint),
        ("time", ctypes.c_uint),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_uint), ("u", _INPUTUNION)]


def _send_input(inp):
    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def send_key(vk, key_up=False):
    inp = _INPUT()
    inp.type = INPUT_KEYBOARD
    inp.u.ki.wVk = 0
    inp.u.ki.wScan = ctypes.windll.user32.MapVirtualKeyW(vk, 0)
    flags = KEYEVENTF_SCANCODE
    if vk in EXTENDED_VKS:
        flags |= KEYEVENTF_EXTENDEDKEY
    if key_up:
        flags |= KEYEVENTF_KEYUP
    inp.u.ki.dwFlags = flags
    _send_input(inp)


def send_left_click(down=True):
    inp = _INPUT()
    inp.type = INPUT_MOUSE
    inp.u.mi.dwFlags = MOUSEEVENTF_LEFTDOWN if down else MOUSEEVENTF_LEFTUP
    _send_input(inp)


def key_is_down(vk):
    try:
        return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
    except Exception:  # noqa: BLE001
        return False


def fortnite_is_active():
    try:
        user32 = ctypes.windll.user32
        user32.GetForegroundWindow.restype = ctypes.c_void_p
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        user32.GetWindowTextLengthW.argtypes = [ctypes.c_void_p]
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW.argtypes = [
            ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
        user32.GetWindowTextW(hwnd, buf, length + 1)
        return "fortnite" in buf.value.lower()
    except Exception:  # noqa: BLE001
        return False


def vk_name(vk):
    try:
        user32 = ctypes.windll.user32
        scan = user32.MapVirtualKeyW(vk, 0)
        buf = ctypes.create_unicode_buffer(64)
        if user32.GetKeyNameTextW(scan << 16, buf, 64) and buf.value:
            return buf.value
    except Exception:  # noqa: BLE001
        pass
    return f"VK {vk:#04x}"


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.c_uint),
        ("scanCode", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("time", ctypes.c_uint),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _MSLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("pt", _POINT),
        ("mouseData", ctypes.c_uint),
        ("flags", ctypes.c_uint),
        ("time", ctypes.c_uint),
        ("dwExtraInfo", ctypes.c_void_p),
    ]


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", ctypes.c_void_p),
        ("message", ctypes.c_uint),
        ("wParam", ctypes.c_size_t),
        ("lParam", ctypes.c_ssize_t),
        ("time", ctypes.c_uint),
        ("pt", _POINT),
        ("lPrivate", ctypes.c_uint),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, ctypes.c_int,
                              ctypes.c_size_t, ctypes.c_ssize_t)


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

# --- Planes de energia (todos reversibles) ---
PLAN_BALANCED = "381b4222-f694-41f0-9685-ff5bb260df2e"
PLAN_HIGH = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
PLAN_ULTIMATE = "e9a42b02-d5df-448d-aa00-03f14749eb61"

PLAN_NAMES = {
    "balanced": "Equilibrado (Windows)",
    "high": "Alto rendimiento",
    "ultimate": "Maximo rendimiento (Ultimate)",
    "gaming": "Pyland Gaming (baja latencia)",
}

# --- Delay / latencia extra para Fortnite (todo reversible) ---
FORTNITE_EXE = (r"C:\Program Files\Epic Games\Fortnite\FortniteGame\Binaries\Win64"
                r"\FortniteClient-Win64-Shipping.exe")

LATENCY_EXTRA_REGS = [
    (r"HKCU\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers",
     FORTNITE_EXE, "REG_SZ", "~ DISABLEDXMAXIMIZEDWINDOWEDMODE"),
    (r"HKCU\Software\Microsoft\DirectX\UserGpuPreferences",
     FORTNITE_EXE, "REG_SZ", "GpuPreference=2;"),
]

LATENCY_EXTRA_DELETE = [
    (r"HKCU\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers", FORTNITE_EXE),
    (r"HKCU\Software\Microsoft\DirectX\UserGpuPreferences", FORTNITE_EXE),
]

# Apps de segundo plano que se pueden cerrar de forma temporal (no se desinstalan)
BACKGROUND_PROCESSES = [
    "EpicGamesLauncher.exe",
    "EOSOverlayRenderer-Win64-Shipping.exe",
    "EOSOverlayRenderer.exe",
    "OneDrive.exe",
    "PhoneExperienceHost.exe",
    "SearchApp.exe",
    "msedge.exe",
    "GameBar.exe",
    "GameBarFTServer.exe",
    "XboxGameBar.exe",
]

# ---------------------------------------------------------------------------
# Potato Graphics Studio (perfiles de juego estilo NVIDIA Profile Inspector)
# ---------------------------------------------------------------------------
FORTNITE_GUS_SECTION = "/Script/FortniteGame.FortGameUserSettings"

POTATO_ORDER = ["auto", "nivel1", "nivel2", "nivel3"]

POTATO_LEVELS = {
    "auto": {
        "name": "Automatico",
        "short": "AUTO",
        "tag": "SEGUN TU PC",
        "desc": "Analiza GPU, RAM, CPU y resolucion para elegir el nivel ideal.",
        "impact": "Inteligente",
    },
    "nivel1": {
        "name": "Nivel 1 - Potato Ligero",
        "short": "LVL 1",
        "tag": "SUAVE",
        "desc": "Sombras y efectos al minimo. Buena imagen y un salto de FPS seguro.",
        "impact": "+20-40% FPS",
        "res": 85.0,
        "fortnite": {
            "sg.ResolutionQuality": "85.000000",
            "sg.ViewDistanceQuality": "2",
            "sg.AntiAliasingQuality": "1",
            "sg.ShadowQuality": "0",
            "sg.PostProcessQuality": "1",
            "sg.TextureQuality": "1",
            "sg.EffectsQuality": "1",
            "sg.FoliageQuality": "0",
            "sg.ShadingQuality": "1",
            "sg.LandscapeQuality": "1",
            "sg.MotionBlurQuality": "0",
        },
        "engine": {
            "r.MotionBlurQuality": "0",
            "r.BloomQuality": "0",
            "r.AmbientOcclusionLevels": "0",
            "r.DepthOfFieldQuality": "0",
            "r.LightShafts": "0",
            "r.SSR.Quality": "0",
            "r.MaxAnisotropy": "4",
        },
        "cs2": {
            "setting.fullscreen": "1",
            "setting.nowindowborder": "0",
            "setting.mat_vsync": "0",
            "setting.mat_triplebuffered": "0",
            "setting.mat_antialias": "0",
            "setting.mat_software_aa_strength": "0",
            "setting.mat_motion_blur_enabled": "0",
            "setting.shaderquality": "0",
            "setting.gpu_mem_level": "0",
            "setting.gpu_level": "0",
            "setting.cpu_level": "0",
            "setting.r_lod_switch_scale": "0.50",
            "setting.mat_queue_mode": "-1",
        },
        "gta5": {
            "Windowed": "2",
            "VSync": "0",
            "MSAA": "0",
            "MSAA_Level": "0",
            "ShadowQuality": "0",
            "ReflectionQuality": "0",
            "ReflectionMSAA": "0",
            "SSAO": "0",
            "AnisotropicFiltering": "4",
            "TextureQuality": "0",
            "ParticleQuality": "0",
            "WaterQuality": "0",
            "GrassQuality": "0",
            "ShaderQuality": "0",
            "PostFX": "0",
            "DoF": "0",
            "MotionBlurStrength": "0",
            "DynamicShadows": "false",
        },
        "minecraft": {
            "renderDistance": "6",
            "simulationDistance": "6",
            "maxFps": "120",
            "enableVsync": "false",
            "graphicsMode": "0",
            "ao": "false",
            "entityShadows": "false",
            "particles": "1",
            "mipmapLevels": "0",
            "biomeBlendRadius": "0",
            "entityDistanceScaling": "0.75",
            "screenEffectScale": "0.5",
            "cloudStatus": "1",
            "fullscreen": "true",
        },
    },
    "nivel2": {
        "name": "Nivel 2 - Potato",
        "short": "LVL 2",
        "tag": "COMPETITIVO",
        "desc": "3D al 67%, todo en bajo, sin AA ni sombras. El equilibrio ideal.",
        "impact": "+40-80% FPS",
        "res": 67.0,
        "fortnite": {
            "sg.ResolutionQuality": "67.000000",
            "sg.ViewDistanceQuality": "1",
            "sg.AntiAliasingQuality": "0",
            "sg.ShadowQuality": "0",
            "sg.PostProcessQuality": "0",
            "sg.TextureQuality": "0",
            "sg.EffectsQuality": "0",
            "sg.FoliageQuality": "0",
            "sg.ShadingQuality": "0",
            "sg.LandscapeQuality": "0",
            "sg.MotionBlurQuality": "0",
        },
        "engine": {
            "r.MotionBlurQuality": "0",
            "r.BloomQuality": "0",
            "r.AmbientOcclusionLevels": "0",
            "r.DepthOfFieldQuality": "0",
            "r.LightShafts": "0",
            "r.SSR.Quality": "0",
            "r.MaxAnisotropy": "0",
            "r.Shadow.MaxResolution": "512",
            "r.Shadow.CSM.MaxCascades": "1",
            "r.ShadowQuality": "0",
            "r.ViewDistanceScale": "0.7",
            "r.SkeletalMeshLODBias": "1",
            "r.ParticleLODBias": "1",
        },
        "cs2": {
            "setting.fullscreen": "1",
            "setting.nowindowborder": "0",
            "setting.mat_vsync": "0",
            "setting.mat_triplebuffered": "0",
            "setting.mat_antialias": "0",
            "setting.mat_software_aa_strength": "0",
            "setting.mat_motion_blur_enabled": "0",
            "setting.shaderquality": "0",
            "setting.gpu_mem_level": "0",
            "setting.gpu_level": "0",
            "setting.cpu_level": "0",
            "setting.r_lod_switch_scale": "0.35",
            "setting.mat_queue_mode": "-1",
        },
        "gta5": {
            "Windowed": "2",
            "VSync": "0",
            "MSAA": "0",
            "MSAA_Level": "0",
            "ShadowQuality": "0",
            "ReflectionQuality": "0",
            "ReflectionMSAA": "0",
            "SSAO": "0",
            "AnisotropicFiltering": "0",
            "TextureQuality": "0",
            "ParticleQuality": "0",
            "WaterQuality": "0",
            "GrassQuality": "0",
            "ShaderQuality": "0",
            "PostFX": "0",
            "DoF": "0",
            "MotionBlurStrength": "0",
            "DynamicShadows": "false",
        },
        "minecraft": {
            "renderDistance": "4",
            "simulationDistance": "5",
            "maxFps": "0",
            "enableVsync": "false",
            "graphicsMode": "0",
            "ao": "false",
            "entityShadows": "false",
            "particles": "2",
            "mipmapLevels": "0",
            "biomeBlendRadius": "0",
            "entityDistanceScaling": "0.5",
            "screenEffectScale": "0.0",
            "cloudStatus": "0",
            "fullscreen": "true",
        },
    },
    "nivel3": {
        "name": "Nivel 3 - Ultra Potato",
        "short": "LVL 3",
        "tag": "TOSTADORA",
        "desc": "3D al 50%, todo al minimo y sin postprocesado. Maximo FPS posible.",
        "impact": "+80-150% FPS",
        "res": 50.0,
        "fortnite": {
            "sg.ResolutionQuality": "50.000000",
            "sg.ViewDistanceQuality": "0",
            "sg.AntiAliasingQuality": "0",
            "sg.ShadowQuality": "0",
            "sg.PostProcessQuality": "0",
            "sg.TextureQuality": "0",
            "sg.EffectsQuality": "0",
            "sg.FoliageQuality": "0",
            "sg.ShadingQuality": "0",
            "sg.LandscapeQuality": "0",
            "sg.MotionBlurQuality": "0",
        },
        "engine": {
            "r.MotionBlurQuality": "0",
            "r.BloomQuality": "0",
            "r.AmbientOcclusionLevels": "0",
            "r.DepthOfFieldQuality": "0",
            "r.LightShafts": "0",
            "r.SSR.Quality": "0",
            "r.MaxAnisotropy": "0",
            "r.Shadow.MaxResolution": "256",
            "r.Shadow.CSM.MaxCascades": "1",
            "r.ShadowQuality": "0",
            "r.ViewDistanceScale": "0.5",
            "r.SkeletalMeshLODBias": "2",
            "r.ParticleLODBias": "2",
            "r.FoliageQuality": "0",
        },
        "cs2": {
            "setting.fullscreen": "1",
            "setting.nowindowborder": "0",
            "setting.mat_vsync": "0",
            "setting.mat_triplebuffered": "0",
            "setting.mat_antialias": "0",
            "setting.mat_software_aa_strength": "0",
            "setting.mat_motion_blur_enabled": "0",
            "setting.shaderquality": "0",
            "setting.gpu_mem_level": "0",
            "setting.gpu_level": "0",
            "setting.cpu_level": "0",
            "setting.r_lod_switch_scale": "0.25",
            "setting.mat_queue_mode": "-1",
        },
        "gta5": {
            "Windowed": "2",
            "VSync": "0",
            "MSAA": "0",
            "MSAA_Level": "0",
            "ShadowQuality": "0",
            "ReflectionQuality": "0",
            "ReflectionMSAA": "0",
            "SSAO": "0",
            "AnisotropicFiltering": "0",
            "TextureQuality": "0",
            "ParticleQuality": "0",
            "WaterQuality": "0",
            "GrassQuality": "0",
            "ShaderQuality": "0",
            "PostFX": "0",
            "DoF": "0",
            "MotionBlurStrength": "0",
            "DynamicShadows": "false",
        },
        "minecraft": {
            "renderDistance": "2",
            "simulationDistance": "4",
            "maxFps": "0",
            "enableVsync": "false",
            "graphicsMode": "0",
            "ao": "false",
            "entityShadows": "false",
            "particles": "2",
            "mipmapLevels": "0",
            "biomeBlendRadius": "0",
            "entityDistanceScaling": "0.5",
            "screenEffectScale": "0.0",
            "cloudStatus": "0",
            "fullscreen": "true",
        },
    },
}

GAME_PROFILES = [
    {
        "id": "fortnite",
        "name": "Fortnite",
        "exe": "FortniteClient-Win64-Shipping.exe",
        "note": "GameUserSettings.ini + Engine.ini: 3D, sombras, AA, efectos y LOD.",
    },
    {
        "id": "cs2",
        "name": "Counter-Strike 2",
        "exe": "cs2.exe",
        "note": "video.txt: resolucion, MSAA, sombras, LOD y sincronizacion.",
    },
    {
        "id": "gta5",
        "name": "GTA V",
        "exe": "GTA5.exe",
        "note": "settings.xml: sombras, reflejos, texturas, agua y poblacion.",
    },
    {
        "id": "minecraft",
        "name": "Minecraft Java",
        "exe": None,
        "note": "options.txt: distancia de render, particulas, V-Sync y nubes.",
    },
    {
        "id": "generic",
        "name": "Personalizado (.exe)",
        "exe": None,
        "note": "Aplica GPU dedicada, prioridad alta y fullscreen optimizations al .exe elegido.",
    },
]

GAME_PROFILES_IDS = [profile["id"] for profile in GAME_PROFILES]

HW_SCAN_PS = r'''
$ErrorActionPreference = "SilentlyContinue"
$gpu = Get-CimInstance Win32_VideoController | Sort-Object AdapterRAM -Descending | Select-Object -First 1
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$cs = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
$vram = 0
try {
  $keys = Get-ChildItem 'HKLM:\SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}' -ErrorAction Stop | Where-Object { $_.PSChildName -match '^\d{4}$' }
  $best = 0
  foreach ($k in $keys) {
    $p = Get-ItemProperty $k.PSPath
    if ($p.'HardwareInformation.qwMemorySize' -and $p.'HardwareInformation.qwMemorySize' -gt $best) {
      $best = $p.'HardwareInformation.qwMemorySize'
    }
  }
  if ($best -gt 0) { $vram = [math]::Round($best / 1GB, 1) }
  elseif ($gpu.AdapterRAM -and $gpu.AdapterRAM -gt 0) { $vram = [math]::Round($gpu.AdapterRAM / 1GB, 1) }
} catch {
  if ($gpu.AdapterRAM -and $gpu.AdapterRAM -gt 0) { $vram = [math]::Round($gpu.AdapterRAM / 1GB, 1) }
}
[pscustomobject]@{
  gpu = [string]$gpu.Name
  vram = [double]$vram
  cpu = [string]$cpu.Name
  cores = [int]$cpu.NumberOfCores
  threads = [int]$cpu.NumberOfLogicalProcessors
  ram = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
  resx = [int]$gpu.CurrentHorizontalResolution
  resy = [int]$gpu.CurrentVerticalResolution
  hz = [int]$gpu.CurrentRefreshRate
  os = [string]$os.Caption
} | ConvertTo-Json -Compress
'''

# ---------------------------------------------------------------------------
# Optimizador de inicio
# ---------------------------------------------------------------------------
STARTUP_BOOT_REGS = [
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize",
     "StartupDelayInMSec", "REG_DWORD", "0"),
    (r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Serialize",
     "StartupDelayInMSec", "REG_DWORD", "0"),
    (r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power",
     "HiberbootEnabled", "REG_DWORD", "1"),
    (r"HKLM\SYSTEM\CurrentControlSet\Control", "WaitToKillServiceTimeout", "REG_DWORD", "2000"),
    (r"HKLM\SYSTEM\CurrentControlSet\Control", "HungAppTimeout", "REG_DWORD", "2000"),
    (r"HKCU\Control Panel\Desktop", "HungAppTimeout", "REG_SZ", "2000"),
    (r"HKCU\Control Panel\Desktop", "WaitToKillAppTimeout", "REG_SZ", "2000"),
    (r"HKCU\Control Panel\Desktop", "AutoEndTasks", "REG_SZ", "1"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications",
     "GlobalUserDisabled", "REG_DWORD", "1"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search",
     "BackgroundAppGlobalToggle", "REG_DWORD", "0"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
     "ShowSyncProviderNotifications", "REG_DWORD", "0"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "SubscribedContent-338388Enabled", "REG_DWORD", "0"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "SubscribedContent-338389Enabled", "REG_DWORD", "0"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "SilentInstalledAppsEnabled", "REG_DWORD", "0"),
]

STARTUP_BOOT_REGS_REVERT = [
    (r"HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Power",
     "HiberbootEnabled", "REG_DWORD", "1"),
    (r"HKLM\SYSTEM\CurrentControlSet\Control", "WaitToKillServiceTimeout", "REG_DWORD", "5000"),
    (r"HKLM\SYSTEM\CurrentControlSet\Control", "HungAppTimeout", "REG_DWORD", "5000"),
    (r"HKCU\Control Panel\Desktop", "HungAppTimeout", "REG_SZ", "5000"),
    (r"HKCU\Control Panel\Desktop", "WaitToKillAppTimeout", "REG_SZ", "5000"),
    (r"HKCU\Control Panel\Desktop", "AutoEndTasks", "REG_SZ", "0"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications",
     "GlobalUserDisabled", "REG_DWORD", "0"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search",
     "BackgroundAppGlobalToggle", "REG_DWORD", "1"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
     "ShowSyncProviderNotifications", "REG_DWORD", "1"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "SubscribedContent-338388Enabled", "REG_DWORD", "1"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "SubscribedContent-338389Enabled", "REG_DWORD", "1"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager",
     "SilentInstalledAppsEnabled", "REG_DWORD", "1"),
]

STARTUP_BOOT_DELETE = [
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Serialize", "StartupDelayInMSec"),
    (r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Serialize", "StartupDelayInMSec"),
]

STARTUP_LOGON_TASKS = [
    r"\Microsoft\Windows\Application Experience\StartupAppTask",
    r"\Microsoft\Windows\Application Experience\ProgramDataUpdater",
    r"\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser",
    r"\Microsoft\Windows\Application Experience\MareBackup",
    r"\Microsoft\Windows\Autochk\Proxy",
    r"\Microsoft\Windows\Customer Experience Improvement Program\Consolidator",
    r"\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip",
    r"\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector",
    r"\Microsoft\Windows\Feedback\Siuf\DmClient",
    r"\Microsoft\Windows\Feedback\Siuf\DmClientOnScenarioDownload",
    r"\Microsoft\Windows\Windows Error Reporting\QueueReporting",
    r"\Microsoft\Windows\Maps\MapsUpdateTask",
    r"\Microsoft\Windows\Windows Media Sharing\UpdateLibrary",
    r"\Microsoft\Windows\Maintenance\WinSAT",
    r"\Microsoft\Windows\Sysmain\HybridDriveCachePrepopulate",
    r"\Microsoft\Windows\Sysmain\ResPriStaticDbSync",
    r"\Microsoft\Windows\Sysmain\WsSwapAssessmentTask",
    r"\Microsoft\Windows\Speech\SpeechModelDownloadTask",
    r"\Microsoft\Windows\CloudExperienceHost\CreateObjectTask",
    r"\Microsoft\Windows\Device Information\Device",
    r"\Microsoft\Windows\Diagnosis\Scheduled",
    r"\Microsoft\Windows\DiskFootprint\Diagnostics",
    r"\Microsoft\Windows\SpacePort\SpaceAgentTask",
    r"\Microsoft\Windows\Storage Tiers Management\Storage Tiers Management Initialization",
    r"\Microsoft\Windows\UpdateOrchestrator\Schedule Scan",
    r"\Microsoft\Windows\UpdateOrchestrator\Schedule Scan Static Task",
    r"\Microsoft\Windows\WaaSMedic\PerformRemediation",
    r"\Microsoft\Windows\InstallService\ScanForUpdatesAtBoot",
    r"\Microsoft\Windows\InstallService\SmartRetry",
]

STARTUP_BOOT_SERVICES = [
    "DiagTrack", "dmwappushservice", "MapsBroker", "RetailDemo", "RemoteRegistry",
    "lfsvc", "PcaSvc", "WerSvc", "Fax", "WSearch", "SysMain", "WMPNetworkSvc",
    "XblAuthManager", "XblGameSave", "XboxGipSvc", "XboxNetApiSvc", "WiaRpc",
    "SEMgrSvc", "SensorService", "SensrSvc", "SensorDataService", "PhoneSvc",
    "TabletInputService", "WpcMonSvc", "WbioSrvc", "SCardSvr", "ScDeviceEnum",
    "PrintNotify", "AssignedAccessManagerSvc", "DsmSvc", "InstallService",
    "InventorySvc", "NaturalAuthentication", "NgcCtnrSvc", "NgcSvc",
    "PimIndexMaintenanceSvc", "UnistoreSvc", "UserDataSvc", "WManSvc",
    "workfolderssvc", "WalletService", "WSService", "SmsRouter",
    "TroubleshootingSvc", "SharedRealitySvc", "MixedRealityOpenXRSvc",
    "bthserv", "BTAGService", "BluetoothUserService",
    "FrameServer", "FrameServerMonitor", "GraphicsPerfSvc", "DsSvc",
]

DEFAULT_STARTUP_EXCLUSIONS = [
    "audiosrv", "audioendpointbuilder", "realtek", "nvidia", "amd", "intel",
    "igfx", "synaptics", "touchpad", "security", "defender", "antivirus",
    "bthserv", "bluetooth", "btagservice", "bluetoothuserservice",
]


def regs(cmds):
    return [reg_add(*c) for c in cmds]


# ---------------------------------------------------------------------------
# Overlay de animacion del optimizador de inicio
# ---------------------------------------------------------------------------
class StartupOverlay:
    WIDTH = 720
    HEIGHT = 500

    def __init__(self, app, title="OPTIMIZADOR DE INICIO",
                 subtitle="Preparando la optimizacion..."):
        self.app = app
        self.existing = True
        self.cancelled = False
        self.finished = False
        self.success = True
        self.total = 0
        self.done = 0
        self.target = 0.0
        self.anim = 0.0
        self.stage = subtitle
        self.events = queue.Queue()

        top = tk.Toplevel(app.root)
        self.top = top
        top.withdraw()
        top.title("PylandTweaks")
        top.transient(app.root)
        top.overrideredirect(True)
        top.configure(bg=ACCENT)

        self.body = tk.Frame(top, bg=PANEL2)
        self.body.pack(fill="both", expand=True, padx=2, pady=2)

        head = tk.Frame(self.body, bg=PANEL2)
        head.pack(fill="x", padx=20, pady=(16, 0))
        self.dot = tk.Canvas(head, width=12, height=12, bg=PANEL2, highlightthickness=0)
        self.dot.pack(side="left", padx=(0, 9))
        self.dot_shape = self.dot.create_oval(1, 1, 11, 11, fill=ACCENT, outline="")
        tk.Label(head, text=title, bg=PANEL2, fg=FG,
                 font=(FONT_BOLD, 13)).pack(side="left")
        self.cancel_btn = ttk.Button(head, text="Cancelar", style="Danger.TButton",
                                     command=self.request_cancel, cursor="hand2")
        self.cancel_btn.pack(side="right")

        self.ring = tk.Canvas(self.body, width=230, height=230, bg=PANEL2,
                              highlightthickness=0)
        self.ring.pack(pady=(2, 0))

        self.current_lbl = tk.Label(self.body, text=subtitle, bg=PANEL2, fg=FG,
                                    font=("Consolas", 9), wraplength=660, justify="center")
        self.current_lbl.pack(fill="x", padx=20, pady=(0, 4))

        box = tk.Frame(self.body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        box.pack(fill="both", expand=True, padx=20, pady=(4, 6))
        self.log_text = tk.Text(box, height=7, bg=PANEL, fg=MUTED, insertbackground=FG,
                                selectbackground=ACCENT, relief="flat", bd=0,
                                font=("Consolas", 8), wrap="none", padx=10, pady=8)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.log_text.yview)
        scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scroll.set, state="disabled")
        self.log_text.tag_configure("idx", foreground=ACCENT2)
        self.log_text.tag_configure("cmd", foreground=FG)
        self.log_text.tag_configure("done", foreground=GREEN)

        self.bar = tk.Canvas(self.body, height=6, bg=PANEL2, highlightthickness=0)
        self.bar.pack(fill="x", padx=20, pady=(0, 16))

        self._draw()
        self._place()

        top.deiconify()
        top.lift()
        try:
            top.attributes("-topmost", True)
        except tk.TclError:
            pass
        top.grab_set()
        top.bind("<Escape>", lambda _e: self.request_cancel())
        self._poll()

    # ----------------------------------------------------------- geometry
    def _place(self):
        self.top.update_idletasks()
        w, h = self.WIDTH, self.HEIGHT
        rx = self.app.root.winfo_rootx()
        ry = self.app.root.winfo_rooty()
        rw = self.app.root.winfo_width()
        rh = self.app.root.winfo_height()
        sw = self.app.root.winfo_screenwidth()
        sh = self.app.root.winfo_screenheight()
        x = rx + max(0, (rw - w) // 2)
        y = ry + max(0, (rh - h) // 2)
        x = max(0, min(x, sw - w))
        y = max(0, min(y, sh - h))
        self.top.geometry(f"{w}x{h}+{x}+{y}")

    # ----------------------------------------------------------- drawing
    def _draw(self):
        c = self.ring
        c.delete("all")
        size = 230
        pad = 20
        frac = max(0.0, min(1.0, self.anim))
        c.create_oval(pad, pad, size - pad, size - pad, outline=PANEL3, width=11)
        if frac > 0.001:
            extent = -359.999 * frac
            c.create_arc(pad, pad, size - pad, size - pad, start=90, extent=extent,
                         style="arc", outline=ACCENT, width=11)
            c.create_arc(pad + 5, pad + 5, size - pad - 5, size - pad - 5, start=90,
                         extent=extent, style="arc", outline=ACCENT2, width=2)
        total = self.total if self.total else "--"
        c.create_text(size / 2, size / 2 - 10, text=f"{self.done}/{total}",
                      fill=FG, font=(FONT_BOLD, 26))
        c.create_text(size / 2, size / 2 + 22, text=f"{int(frac * 100)}%",
                      fill=ACCENT2, font=(FONT_BOLD, 12))
        if self.finished:
            c.create_text(size / 2, size / 2 + 44,
                          text="COMPLETADO" if self.success else "DETENIDO",
                          fill=GREEN if self.success else RED, font=(FONT_BOLD, 8))

        self.bar.delete("all")
        width = max(self.bar.winfo_width(), 2)
        self.bar.create_rectangle(0, 0, width, 6, fill=PANEL3, outline="")
        self.bar.create_rectangle(0, 0, max(2, width * frac), 6, fill=ACCENT, outline="")

    # ------------------------------------------------------------- queue
    def push(self, index, label, cmd, error=False):
        self.events.put({"index": index, "label": label, "cmd": cmd, "error": error})

    def set_total(self, total):
        self.app.root.after(0, self._set_total, total)

    def _set_total(self, total):
        if self.existing:
            self.total = max(0, int(total))
            self._draw()

    def set_stage(self, text):
        self.app.root.after(0, self._set_stage, text)

    def _set_stage(self, text):
        if self.existing and not self.finished:
            self.stage = text
            self.current_lbl.configure(text=self._clip(text, 100), fg=FG)

    def finish(self, success=True, message="Optimizacion completada"):
        self.app.root.after(0, self._finish_ui, success, message)

    def _finish_ui(self, success, message):
        if not self.existing:
            return
        self.finished = True
        self.success = success
        self.stage = message
        if success:
            self.target = 1.0
        self.current_lbl.configure(text=message, fg=GREEN if success else RED)
        if success:
            self.cancel_btn.configure(state="disabled", text="Listo")
        else:
            self.cancel_btn.configure(state="normal", text="Cerrar",
                                      command=self.close)
        self._draw()
        self.app.root.after(1800 if success else 3500, self.close)

    def request_cancel(self):
        if self.finished:
            self.close()
            return
        self.cancelled = True
        self.cancel_btn.configure(state="disabled", text="Cancelando...")
        self.current_lbl.configure(text="Cancelando, espera a que termine el comando actual...",
                                   fg=YELLOW)

    def close(self):
        if not self.existing:
            return
        self.existing = False
        self.cancelled = True
        try:
            self.top.grab_release()
        except tk.TclError:
            pass
        try:
            self.top.destroy()
        except tk.TclError:
            pass
        if getattr(self.app, "startup_overlay", None) is self:
            self.app.startup_overlay = None

    # -------------------------------------------------------------- loop
    @staticmethod
    def _clip(text, limit):
        text = str(text)
        return text if len(text) <= limit else text[: limit - 1] + "..."

    def _handle(self, ev):
        self.done = max(self.done, int(ev["index"]))
        self.current_lbl.configure(text=self._clip(ev["cmd"], 104),
                                   fg=RED if ev["error"] else FG)
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{ev['index']:>3}/{self.total or '?'}  ", "idx")
        self.log_text.insert("end", self._clip(ev["cmd"], 130) + "\n", "cmd")
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 220:
            self.log_text.delete("1.0", "40.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _drain(self):
        limit = 1
        pending = self.events.qsize()
        if pending > 30:
            limit = 6
        elif pending > 12:
            limit = 3
        elif pending > 5:
            limit = 2
        for _ in range(limit):
            try:
                ev = self.events.get_nowait()
            except queue.Empty:
                break
            self._handle(ev)

    def _poll(self):
        if not self.existing:
            return
        self._drain()
        if self.total:
            target = self.done / self.total
        else:
            target = 0.0
        if self.finished and self.success:
            target = 1.0
        self.target = max(0.0, min(1.0, target))
        self.anim += (self.target - self.anim) * 0.30
        if abs(self.target - self.anim) < 0.002:
            self.anim = self.target
        self._draw()
        self.app.root.after(40, self._poll)


# ---------------------------------------------------------------------------
# Aplicacion
# ---------------------------------------------------------------------------
class OptimizadorApp:
    def __init__(self, root):
        self.root = root
        self.busy = False
        self.root.title("PylandTweaks V5.9")
        self.root.geometry("1120x860")
        self.root.minsize(960, 700)
        self.root.configure(bg=BG)

        self.macro_events = []
        self.macro_recording = False
        self.macro_record_stop = threading.Event()
        self.macro_record_thread = None
        self.macro_record_last = None
        self.macro_record_keys = set()
        self.macro_playing = False
        self.macro_play_stop = threading.Event()
        self.macro_play_thread = None
        self.macro_hold_armed = False
        self.macro_hold_stop = threading.Event()
        self.macro_hold_key_event = threading.Event()
        self.macro_hold_ui_queue = queue.Queue()
        self.macro_hold_hook_thread = None
        self.macro_hold_click_thread = None
        self.macro_hold_sequence = False
        self.macro_hold_trigger_vk = VK_F
        self.macro_hold_edit_vk = VK_F
        self.macro_hold_press = 0.020
        self.macro_hold_click = 0.025
        self.macro_hold_confirm = 0.030
        self.macro_hold_autoconfirm = True
        self.macro_extra_delay = 0.0
        self.macro_loop_pause = 0.1
        self.macro_repeat = 0
        self.macro_extra_delay_var = tk.IntVar(value=0)
        self.macro_loop_pause_var = tk.IntVar(value=100)
        self.macro_repeat_var = tk.IntVar(value=0)
        self.macro_preset_gap_var = tk.IntVar(value=50)
        self.macro_preset_hold_var = tk.IntVar(value=25)
        self.macro_trick_clicks_var = tk.IntVar(value=0)
        self.macro_trick_double_f_var = tk.BooleanVar(value=True)
        self.macro_hold_keep_var = tk.BooleanVar(value=False)
        self.macro_seq_key_var = tk.StringVar(value="g")
        self.macro_seq_edit_var = tk.StringVar(value="f")
        self.macro_seq_press_var = tk.IntVar(value=20)
        self.macro_seq_click_var = tk.IntVar(value=25)
        self.macro_seq_confirm_var = tk.IntVar(value=30)
        self.macro_seq_autoconfirm_var = tk.BooleanVar(value=True)
        self.macro_selected_delay_var = tk.IntVar(value=0)

        self.startup_items = []
        self.blocked_items = []
        self.startup_overlay = None

        self.graphics_profile = "fortnite"
        self.potato_level = "auto"
        self.hw_info = {}
        self.custom_exe = ""
        self.graphics_level_widgets = {}
        self.graphics_profile_items = {}
        self.graphics_profile_refreshing = False

        self._setup_style()
        self._set_window_icon()
        self._build_header()

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=16, pady=(4, 8))

        self._build_tab_recomendado()
        self._build_tab_graficos()
        self._build_tab_latencia()
        self._build_tab_perifericos()
        self._build_tab_reversion()
        self._build_tab_sistema()
        self._build_tab_apariencia()
        self._build_tab_recursos()
        self._build_tab_herramientas()
        self._build_tab_inicio()
        self._build_tab_macro()
        self._build_tab_energia()
        self._build_tab_diagnostico()
        self._build_tab_acerca()

        self._build_log()
        self._build_status()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.log("PylandTweaks V5.9 listo.")
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
                        padding=(9, 8), borderwidth=0, font=(FONT_BOLD, 8))
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

        style.configure("TSpinbox", fieldbackground=PANEL2, foreground=FG,
                        background=PANEL3, bordercolor=BORDER, arrowcolor=MUTED,
                        insertcolor=FG, borderwidth=1, padding=(6, 5))
        style.map("TSpinbox",
                  fieldbackground=[("disabled", "#151824")],
                  foreground=[("disabled", "#5a6178")])

        style.configure("Horizontal.TProgressbar", background=ACCENT, troughcolor=PANEL3,
                        borderwidth=0, lightcolor=ACCENT, darkcolor=ACCENT)

        style.configure("Vertical.TScrollbar", background=PANEL3, troughcolor=PANEL2,
                        bordercolor=PANEL2, arrowcolor=MUTED, borderwidth=0)
        style.map("Vertical.TScrollbar", background=[("active", ACCENT)])

        style.configure("Graphics.Treeview", background=PANEL2, fieldbackground=PANEL2,
                        foreground=FG, borderwidth=0, rowheight=30, font=(FONT, 9))
        style.configure("Graphics.Treeview.Heading", background=PANEL3, foreground=MUTED,
                        borderwidth=0, font=(FONT_BOLD, 8), padding=(8, 6))
        style.map("Graphics.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#ffffff")])
        style.map("Graphics.Treeview.Heading", background=[("active", PANEL3)])

        style.configure("Graphics.TCombobox", fieldbackground=PANEL, foreground=FG,
                        background=PANEL3, arrowcolor=MUTED, bordercolor=BORDER,
                        padding=(8, 6), font=(FONT, 9))
        style.map("Graphics.TCombobox",
                  fieldbackground=[("readonly", PANEL)],
                  foreground=[("readonly", FG)],
                  selectbackground=[("readonly", PANEL)],
                  selectforeground=[("readonly", FG)])

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
        tk.Label(title_row, text="V5.9", bg=BG, fg=ACCENT2,
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

    # ------------------------------------------------------------- perifericos
    def _peripheral_config_dir(self):
        return RECURSOS / "Periféricos"

    def _build_tab_perifericos(self):
        tab = self._new_tab("  Periféricos  ")

        ttk.Label(tab, text="Ajustes de mouse y teclado para reducir el delay de entrada y dejar la mira estable (movimiento 1:1).",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        hero = tk.Frame(tab, bg=PANEL, highlightbackground=ACCENT, highlightthickness=1)
        hero.pack(fill="x", pady=(0, 10))
        hi = tk.Frame(hero, bg=PANEL)
        hi.pack(fill="x", padx=16, pady=12)

        top_row = tk.Frame(hi, bg=PANEL)
        top_row.pack(fill="x")
        tk.Label(top_row, text="OPTIMIZADOR DE PERIFÉRICOS", bg=PANEL, fg=FG,
                 font=(FONT_BOLD, 14)).pack(side="left")
        self.peripheral_summary = tk.Label(top_row, text="Listo para optimizar",
                                           bg=PANEL, fg=ACCENT2,
                                           font=(FONT_BOLD, 9))
        self.peripheral_summary.pack(side="right")

        tk.Label(hi, text="Aplica mas de 120 ajustes declarativos de mouse, teclado, escritorio y juegos. "
                          "Cada valor se guarda antes de cambiarlo y se puede devolver con RESTAURAR PERIFÉRICOS.",
                 bg=PANEL, fg=MUTED, font=(FONT, 9), justify="left",
                 wraplength=900).pack(anchor="w", pady=(4, 10))

        row = tk.Frame(hi, bg=PANEL)
        row.pack(fill="x")
        ttk.Button(row, text="OPTIMIZAR PERIFÉRICOS AHORA", style="Accent.TButton",
                   command=self.do_optimize_peripherals,
                   cursor="hand2").pack(side="left")
        ttk.Button(row, text="Restaurar periféricos", style="Danger.TButton",
                   command=self.do_restore_peripherals,
                   cursor="hand2").pack(side="left", padx=8)

        profiles, default = perifericos.load_profiles(self._peripheral_config_dir())
        self.peripheral_profiles = profiles
        self.peripheral_profile_ids = list(profiles)
        self.peripheral_profile_var = tk.StringVar(
            value=str(profiles.get(default, {}).get("name") or default))
        combo = ttk.Combobox(row, textvariable=self.peripheral_profile_var,
                             values=[profiles[p].get("name", p)
                                     for p in self.peripheral_profile_ids],
                             state="readonly", style="Graphics.TCombobox", width=38)
        combo.pack(side="right")
        combo.bind("<<ComboboxSelected>>", self._on_peripheral_profile_change)

        grid = ttk.Frame(tab)
        grid.pack(fill="both", expand=True, pady=(6, 0))
        for i in range(2):
            grid.columnconfigure(i, weight=1)
        cards = [
            ("Mira estable", [
                ("Aceleración OFF, umbrales 0/0 y velocidad neutra", self.do_optimize_peripherals),
                ("Perfil 2/120 disponible en el selector", self._show_peripheral_profiles),
            ]),
            ("Delay del mouse", [
                ("Aplicar SPI_SETMOUSE y propagar cambios", self.do_optimize_peripherals),
                ("Actualizar estado", self._refresh_peripherals_ui),
            ]),
            ("Perfiles", [
                ("Editar perfiles.json", self.open_peripheral_profiles),
                ("Abrir versión de consola (.cmd)", self.open_peripheral_console),
            ]),
            ("Seguridad", [
                ("Restaurar todos los valores guardados", self.do_restore_peripherals),
            ]),
        ]
        for idx, (title, actions) in enumerate(cards):
            self._card(grid, title, actions).grid(
                row=idx // 2, column=idx % 2, sticky="nsew", padx=6, pady=6)

        game_cfg = self._fortnite_game_config()
        game = tk.Frame(grid, bg=PANEL, highlightbackground=ACCENT, highlightthickness=1)
        game.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=6, pady=6)
        gi = tk.Frame(game, bg=PANEL)
        gi.pack(fill="both", expand=True, padx=14, pady=12)
        gh = tk.Frame(gi, bg=PANEL)
        gh.pack(fill="x")
        gbar = tk.Frame(gh, bg=ACCENT, width=4, height=16)
        gbar.pack_propagate(False)
        gbar.pack(side="left", padx=(0, 9))
        tk.Label(gh, text="Juego - resolucion de Fortnite", bg=PANEL, fg=ACCENT2,
                 font=(FONT_BOLD, 10)).pack(side="left")
        self.fortnite_status = tk.Label(gh, text="", bg=PANEL, fg=MUTED,
                                        font=(FONT, 8))
        self.fortnite_status.pack(side="right")
        tk.Label(gi, text="Fortnite abre al iniciar con esta resolucion en pantalla completa. "
                          "El estirado real depende de la escala de tu GPU (guia mas abajo).",
                 bg=PANEL, fg=MUTED, font=(FONT, 9), justify="left",
                 wraplength=880).pack(anchor="w", pady=(6, 6))

        inputs = tk.Frame(gi, bg=PANEL)
        inputs.pack(fill="x")
        self.fortnite_width_var = tk.StringVar(value=str(game_cfg.get("ancho", 1680)))
        self.fortnite_height_var = tk.StringVar(value=str(game_cfg.get("alto", 1050)))
        self.fortnite_readonly_var = tk.BooleanVar(
            value=bool(game_cfg.get("solo_lectura", True)))
        for text, var, col in (("Ancho", self.fortnite_width_var, 0),
                               ("Alto", self.fortnite_height_var, 2)):
            tk.Label(inputs, text=text, bg=PANEL, fg=MUTED, font=(FONT, 9)).grid(
                row=0, column=col, sticky="w", padx=(0, 6))
            tk.Entry(inputs, textvariable=var, width=7, bg=PANEL2, fg=FG,
                     insertbackground=FG, relief="flat", bd=0, font=(FONT, 9),
                     highlightthickness=1, highlightbackground=BORDER,
                     highlightcolor=ACCENT).grid(row=0, column=col + 1, padx=(0, 14))
        tk.Checkbutton(inputs, text="Proteger ini (solo lectura)",
                       variable=self.fortnite_readonly_var, bg=PANEL, fg=FG,
                       activebackground=PANEL, activeforeground=FG,
                       selectcolor=PANEL3, font=(FONT, 9), anchor="w", bd=0,
                       highlightthickness=0).grid(row=0, column=4, sticky="w")

        grows = tk.Frame(gi, bg=PANEL)
        grows.pack(fill="x", pady=(9, 0))
        ttk.Button(grows, text="APLICAR RESOLUCION AL ENTRAR", style="Accent.TButton",
                   command=self.do_apply_fortnite_resolution,
                   cursor="hand2").pack(side="left")
        ttk.Button(grows, text="Restaurar resolucion", style="Danger.TButton",
                   command=self.do_restore_fortnite_resolution,
                   cursor="hand2").pack(side="left", padx=8)
        ttk.Button(grows, text="Comprobar", style="Card.TButton",
                   command=self.check_fortnite_resolution, cursor="hand2").pack(side="left")
        ttk.Button(grows, text="Abrir GameUserSettings.ini", style="Card.TButton",
                   command=self.open_fortnite_ini, cursor="hand2").pack(side="left", padx=8)
        ttk.Button(grows, text="Guia de estirado", style="Card.TButton",
                   command=self.show_stretch_guide, cursor="hand2").pack(side="left", padx=8)

        self._notice(tab, "El temblor de la mira no se corrige con registros: Fortnite usa Raw Input. "
                          "Esta sección elimina la aceleración del puntero de Windows, que es lo que "
                          "sí puede hacer que el movimiento se sienta pesado o irregular.")
        self.root.after(150, self._refresh_peripherals_ui)

    def _on_peripheral_profile_change(self, _event=None):
        self._refresh_peripherals_ui()

    def _peripheral_profile_id(self):
        name = self.peripheral_profile_var.get() if hasattr(
            self, "peripheral_profile_var") else ""
        for profile_id, profile in (self.peripheral_profiles or {}).items():
            if profile.get("name") == name:
                return profile_id
        profiles, default = perifericos.load_profiles(self._peripheral_config_dir())
        self.peripheral_profiles = profiles
        return default

    def _show_peripheral_profiles(self):
        profiles, default = perifericos.load_profiles(self._peripheral_config_dir())
        text = "\n\n".join(
            f"{p.get('name', pid)}\n{p.get('description', '')}"
            for pid, p in profiles.items())
        messagebox.showinfo("Perfiles de periféricos",
                            f"Perfil activo: {default}\n\n{text}")

    def open_peripheral_profiles(self):
        path = self._peripheral_config_dir() / "perfiles.json"
        if not path.exists():
            messagebox.showerror("No encontrado", f"No existe:\n{path}")
            return
        try:
            subprocess.Popen(["notepad.exe", str(path)])
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc))

    def open_peripheral_console(self):
        path = self._peripheral_config_dir() / "Optimizar perifericos.cmd"
        if not path.exists():
            messagebox.showerror("No encontrado", f"No existe:\n{path}")
            return
        try:
            subprocess.Popen(["cmd.exe", "/c", "start", "", str(path)], shell=True)
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc))

    def _refresh_peripherals_ui(self):
        if not hasattr(self, "peripheral_summary"):
            return
        state = perifericos.load_state()
        if state.get("active"):
            text = (f"{state.get('count', len(state.get('records') or []))} ajustes · "
                    f"perfil {state.get('profile', '?')} · "
                    f"{time.strftime('%H:%M', time.localtime())}")
        else:
            text = f"Sin optimizar · {len(perifericos.CATALOG)} ajustes disponibles"
        self.peripheral_summary.configure(text=text)
        self._refresh_fortnite_resolution_ui()

    # -------------------------------------------------- resolucion de juego
    def _fortnite_game_config(self):
        path = self._peripheral_config_dir() / "perfiles.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            juego = data.get("juego") or {}
            if isinstance(juego, dict):
                return juego.get("fortnite") or {}
        except Exception:  # noqa: BLE001
            pass
        return {}

    def _fortnite_resolution_path(self):
        return self._fortnite_config_dir() / "GameUserSettings.ini"

    def _fortnite_backup_path(self):
        base = Path(os.environ.get("APPDATA") or Path.home())
        return (base / "PylandTweaks" / "PeripheralsBackup"
                / "GameUserSettings.resolution.ini")

    @staticmethod
    def _file_attributes(path):
        try:
            return int(ctypes.windll.kernel32.GetFileAttributesW(str(path)))
        except Exception:  # noqa: BLE001
            return -1

    @staticmethod
    def _set_file_attributes(path, attrs):
        try:
            return bool(ctypes.windll.kernel32.SetFileAttributesW(str(path), attrs))
        except Exception:  # noqa: BLE001
            return False

    def _refresh_fortnite_resolution_ui(self):
        if not hasattr(self, "fortnite_status"):
            return
        path = self._fortnite_resolution_path()
        if not path.exists():
            self.fortnite_status.configure(
                text="GameUserSettings.ini no encontrado", fg=YELLOW)
            return
        try:
            text, _encoding = read_text_meta(path)
            def value(key):
                match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*(\S+)", text)
                return match.group(1) if match else "?"
            self.fortnite_status.configure(
                text=f"Actual: {value('ResolutionSizeX')}x{value('ResolutionSizeY')} "
                     f"· modo {value('FullscreenMode')}", fg=MUTED)
        except Exception:  # noqa: BLE001
            self.fortnite_status.configure(text="No se pudo leer el ini", fg=RED)

    def _fortnite_resolution_values(self, width, height, fullscreen):
        return {
            "ResolutionSizeX": str(width),
            "ResolutionSizeY": str(height),
            "LastUserConfirmedResolutionSizeX": str(width),
            "LastUserConfirmedResolutionSizeY": str(height),
            "DesiredScreenWidth": str(width),
            "DesiredScreenHeight": str(height),
            "LastUserConfirmedDesiredScreenWidth": str(width),
            "LastUserConfirmedDesiredScreenHeight": str(height),
            "FullscreenMode": str(fullscreen),
            "LastConfirmedFullscreenMode": str(fullscreen),
            "PreferredFullscreenMode": str(fullscreen),
            "bUseDynamicResolution": "False",
        }

    def check_fortnite_resolution(self):
        path = self._fortnite_resolution_path()
        if not path.exists():
            messagebox.showerror("No encontrado", f"No existe:\n{path}")
            return
        try:
            text, _encoding = read_text_meta(path)

            def value(key):
                match = re.search(rf"(?m)^\s*{re.escape(key)}\s*=\s*(\S+)", text)
                return match.group(1) if match else "?"

            actual = f"{value('ResolutionSizeX')}x{value('ResolutionSizeY')}"
            attrs = self._file_attributes(path)
            readonly = "si" if attrs >= 0 and attrs & 0x1 else "no"
            record = (perifericos.load_state().get("resolution") or {})
            expected = (f"{record.get('width', '?')}x{record.get('height', '?')}"
                        if record else "sin aplicar")
            detail = (f"Esperado por PylandTweaks: {expected}\n"
                      f"Valor actual del ini: {actual}\n"
                      f"Archivo protegido: {readonly}")
            if record and actual == expected:
                messagebox.showinfo(
                    "Resolucion verificada",
                    detail + "\n\nSi dentro de Fortnite no se ve estirada, "
                    "revisa la guia de estirado de tu GPU.")
            else:
                messagebox.showwarning(
                    "Resolucion sobrescrita",
                    detail + "\n\nFortnite o el launcher han reescrito el archivo.\n"
                    "Cierra Fortnite y Epic Launcher y vuelve a pulsar "
                    "APLICAR RESOLUCION AL ENTRAR con 'Proteger ini' activado.")
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", f"No se pudo comprobar:\n{exc}")
        self._refresh_fortnite_resolution_ui()

    def do_apply_fortnite_resolution(self):
        if self.busy:
            messagebox.showinfo("En curso", "Espera a que termine la tarea actual.")
            return
        try:
            width = int(self.fortnite_width_var.get())
            height = int(self.fortnite_height_var.get())
        except (ValueError, tk.TclError):
            messagebox.showerror("Resolucion invalida", "Ancho y alto deben ser numeros.")
            return
        if not (640 <= width <= 4096 and 480 <= height <= 2160):
            messagebox.showerror("Resolucion invalida",
                                 "Usa un ancho entre 640 y 4096 y un alto entre 480 y 2160.")
            return
        path = self._fortnite_resolution_path()
        if not path.exists():
            messagebox.showerror(
                "Fortnite no configurado",
                "No existe GameUserSettings.ini.\n\nAbre Fortnite una vez, cierra el juego "
                "y vuelve a intentar.\n\nRuta esperada:\n" + str(path))
            return
        if process_running("FortniteClient-Win64-Shipping.exe"):
            messagebox.showerror("Fortnite abierto",
                                 "Cierra Fortnite antes de cambiar la resolucion.")
            return
        if process_running("EpicGamesLauncher.exe"):
            messagebox.showerror(
                "Epic Games Launcher abierto",
                "Cierra Epic Games Launcher antes de aplicar la resolucion.\n\n"
                "El launcher puede sobrescribir GameUserSettings.ini al cerrarse.")
            return
        cfg = self._fortnite_game_config()
        fullscreen = int(cfg.get("modo_pantalla_completa", 0))
        if fullscreen not in (0, 1, 2):
            fullscreen = 0
        readonly = bool(self.fortnite_readonly_var.get())
        if not messagebox.askyesno(
                "Resolucion de Fortnite",
                f"Fortnite usara {width}x{height} en pantalla completa al iniciar.\n\n"
                "Se guardara una copia de GameUserSettings.ini antes de cambiarlo.\n"
                f"Proteger archivo como solo lectura: {'SI' if readonly else 'NO'}\n\n"
                "Continuar?"):
            return

        overlay = StartupOverlay(self, "CONFIGURANDO FORTNITE",
                                 f"Preparando resolucion {width}x{height}...")
        self.startup_overlay = overlay

        def worker():
            try:
                state = perifericos.load_state()
                record = state.get("resolution") or {}
                backup = Path(record.get("backup") or self._fortnite_backup_path())
                overlay.set_total(3)
                overlay.set_stage("Copia de seguridad de GameUserSettings.ini")
                if not backup.exists():
                    backup.parent.mkdir(parents=True, exist_ok=True)
                    backup.write_bytes(path.read_bytes())
                record = {
                    "backup": str(backup),
                    "attrs": self._file_attributes(path),
                    "width": width,
                    "height": height,
                }
                overlay.push(1, "Copia de seguridad", f"copy {path.name} -> {backup.name}")

                overlay.set_stage(f"Escribiendo resolucion {width}x{height}")
                current_attrs = self._file_attributes(path)
                if current_attrs >= 0 and current_attrs & 0x1:
                    self._set_file_attributes(path,
                                              (current_attrs & ~0x1) | 0x80)
                text, encoding = read_text_meta(path)
                values = self._fortnite_resolution_values(width, height, fullscreen)
                write_text_meta(path, ini_set(text, FORTNITE_GUS_SECTION, values),
                                encoding)
                overlay.push(2, "Resolucion aplicada",
                             f"{FORTNITE_GUS_SECTION}: {len(values)} claves")

                overlay.set_stage("Protegiendo archivo" if readonly else "Sin proteccion")
                attrs = self._file_attributes(path)
                if readonly and attrs >= 0:
                    self._set_file_attributes(path, (attrs | 0x1) & ~0x80)
                elif not readonly and attrs >= 0 and attrs & 0x1:
                    self._set_file_attributes(path, (attrs & ~0x1) | 0x80)
                overlay.push(3, "Atributos del archivo",
                             f"read-only={readonly}")

                state["resolution"] = record
                perifericos.save_state(state)
                self.log(f"Fortnite configurado a {width}x{height} (modo {fullscreen}).")
                overlay.finish(True, f"Fortnite usara {width}x{height} al entrar")
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR al configurar resolucion de Fortnite: {exc}")
                overlay.finish(False, f"Error: {exc}")

        self.start_task("Resolucion de Fortnite", worker,
                        on_done=self._refresh_fortnite_resolution_ui)

    def do_restore_fortnite_resolution(self):
        if self.busy:
            messagebox.showinfo("En curso", "Espera a que termine la tarea actual.")
            return
        state = perifericos.load_state()
        record = state.get("resolution") or {}
        backup = Path(record.get("backup") or self._fortnite_backup_path())
        if not backup.exists():
            messagebox.showinfo("Sin cambios",
                                "No hay copia de seguridad de la resolucion de Fortnite.")
            return
        path = self._fortnite_resolution_path()
        if process_running("FortniteClient-Win64-Shipping.exe"):
            messagebox.showerror("Fortnite abierto",
                                 "Cierra Fortnite antes de restaurar la resolucion.")
            return
        if not messagebox.askyesno(
                "Restaurar resolucion de Fortnite",
                "Se restaurara GameUserSettings.ini tal como estaba antes.\n\nContinuar?"):
            return

        overlay = StartupOverlay(self, "RESTAURANDO FORTNITE",
                                 "Leyendo la copia de seguridad...")
        self.startup_overlay = overlay

        def worker():
            try:
                overlay.set_total(2)
                overlay.set_stage("Restaurando GameUserSettings.ini")
                attrs = int(record.get("attrs", -1))
                if attrs >= 0:
                    self._set_file_attributes(path, (attrs & ~0x1) | 0x80)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(backup.read_bytes())
                overlay.push(1, "Archivo restaurado", f"copy {backup.name} -> {path.name}")
                overlay.set_stage("Restaurando atributos")
                if attrs >= 0:
                    self._set_file_attributes(path, attrs)
                overlay.push(2, "Atributos restaurados", f"attrs={attrs}")
                state.pop("resolution", None)
                perifericos.save_state(state)
                self.log("Resolucion de Fortnite restaurada.")
                overlay.finish(True, "Resolucion de Fortnite restaurada")
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR al restaurar resolucion de Fortnite: {exc}")
                overlay.finish(False, f"Error: {exc}")

        self.start_task("Restaurar resolucion de Fortnite", worker,
                        on_done=self._refresh_fortnite_resolution_ui)

    def open_fortnite_ini(self):
        path = self._fortnite_resolution_path()
        if not path.exists():
            messagebox.showerror("No encontrado", f"No existe:\n{path}")
            return
        try:
            subprocess.Popen(["notepad.exe", str(path)])
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Error", str(exc))

    def show_stretch_guide(self):
        cfg = self._fortnite_game_config()
        width = cfg.get("ancho", 1680)
        height = cfg.get("alto", 1050)
        messagebox.showinfo(
            "Guia de resolucion estirada",
            f"La app ya deja Fortnite en {width}x{height} y pantalla completa.\n\n"
            "Para que se vea estirado y no con barras negras:\n\n"
            "1) NVIDIA: Panel de control > Ajustar tamano y posicion del escritorio > "
            "Escala = Pantalla completa y Realizar escalado en = GPU.\n"
            "2) AMD: Adrenalin > Pantalla > Escalado GPU activado + Modo de escalado "
            "= Estirar/Completo.\n"
            "3) Si tu monitor no acepta esa señal, crea la resolucion personalizada "
            f"{width}x{height} en el panel de la GPU.\n\n"
            "Cierra Fortnite y el launcher antes de aplicar el cambio.",
        )

    def do_optimize_peripherals(self):
        if self.busy:
            messagebox.showinfo("En curso", "Espera a que termine la tarea actual.")
            return
        profiles, default = perifericos.load_profiles(self._peripheral_config_dir())
        self.peripheral_profiles = profiles
        profile_id = self._peripheral_profile_id()
        profile = profiles.get(profile_id) or perifericos.DEFAULT_PROFILE
        if not messagebox.askyesno(
                "Optimizador de periféricos",
                f"Perfil: {profile.get('name', profile_id)}\n\n"
                f"Se aplicaran {len(perifericos.CATALOG)} ajustes de mouse, teclado y juegos.\n"
                "Cada valor se guarda antes de modificarse y se puede restaurar.\n\n"
                "Continuar?"):
            return

        overlay = StartupOverlay(self, "OPTIMIZANDO PERIFÉRICOS",
                                 "Detectando dispositivos y preparando ajustes...")
        self.startup_overlay = overlay

        def worker():
            try:
                devices = perifericos.detect_devices()
                overlay.set_stage(f"Dispositivos detectados: {len(devices)}")
                plan = perifericos.build_plan(profile, detected_devices=devices)
                overlay.set_total(len(plan))
                state = perifericos.load_state()
                records = state.get("records") or []
                seen = {r.get("id") for r in records}
                applied = 0
                cancelled = False
                for index, action in enumerate(plan, 1):
                    if overlay.cancelled:
                        cancelled = True
                        break
                    overlay.set_stage(action["label"])
                    if action["kind"] == "registry" and action["id"] not in seen:
                        records.append(perifericos.capture_spec(action["spec"]))
                        seen.add(action["id"])
                    perifericos.apply_action(action)
                    applied += 1
                    overlay.push(index, action["label"], action["cmd"])
                state.update({
                    "active": not cancelled or applied > 0,
                    "profile": profile_id,
                    "records": records,
                    "count": len(plan),
                    "devices": devices,
                    "updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                })
                perifericos.save_state(state)
                if cancelled:
                    overlay.finish(False, f"Cancelado: {applied} ajustes aplicados")
                else:
                    self.log(f"Periféricos optimizados: {applied} ajustes "
                             f"({profile.get('name', profile_id)}).")
                    overlay.finish(True, f"Listo: {applied} ajustes aplicados")
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR Periféricos: {exc}")
                overlay.finish(False, f"Error: {exc}")

        self.start_task("Optimizar periféricos", worker,
                        on_done=self._refresh_peripherals_ui)

    def do_restore_peripherals(self):
        if self.busy:
            messagebox.showinfo("En curso", "Espera a que termine la tarea actual.")
            return
        state = perifericos.load_state()
        records = state.get("records") or []
        if not records:
            messagebox.showinfo("Sin cambios",
                                "No hay valores guardados por el optimizador de periféricos.")
            return
        if not messagebox.askyesno(
                "Restaurar periféricos",
                f"Se restauraran {len(records)} valores originales de mouse y teclado.\n\n"
                "Continuar?"):
            return

        overlay = StartupOverlay(self, "RESTAURANDO PERIFÉRICOS",
                                 "Leyendo la copia de seguridad...")
        self.startup_overlay = overlay

        def worker():
            try:
                todos = list(reversed(records))
                refresh = {
                    "kind": "command", "id": "restore.refresh",
                    "cmd": "rundll32.exe user32.dll,UpdatePerUserSystemParameters 1, True",
                }
                overlay.set_total(len(todos) + 1)
                cancelled = False
                for index, record in enumerate(todos, 1):
                    if overlay.cancelled:
                        cancelled = True
                        break
                    label = f"Restaurar {record.get('name', 'valor')}"
                    overlay.set_stage(label)
                    perifericos.restore_record(record)
                    overlay.push(index, label, label)
                if not cancelled:
                    overlay.set_stage("Refrescar parametros de entrada")
                    perifericos.apply_action(refresh)
                    overlay.push(len(todos) + 1, refresh["id"], refresh["cmd"])
                if cancelled:
                    perifericos.save_state(state)
                    overlay.finish(False, "Cancelado: algunos valores no se restauraron")
                else:
                    perifericos.save_state({})
                    self.log("Periféricos restaurados a sus valores originales.")
                    overlay.finish(True, "Periféricos restaurados correctamente")
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR al restaurar periféricos: {exc}")
                overlay.finish(False, f"Error: {exc}")

        self.start_task("Restaurar periféricos", worker,
                        on_done=self._refresh_peripherals_ui)

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

    def _build_tab_macro(self):
        tab = self._new_tab("  Macro  ")
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)
        tab.rowconfigure(4, weight=1)

        ttk.Label(tab, text="Edición rápida: pulsa G para editar al instante la pieza que miras. "
                            "F sigue funcionando como tu edición normal. Lo demás está en Opciones avanzadas.",
                  style="Sub.TLabel", justify="left", wraplength=940).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        status_card = tk.Frame(tab, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        status_card.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        status_inner = tk.Frame(status_card, bg=PANEL)
        status_inner.pack(fill="x", padx=16, pady=12)

        self.macro_status_dot = tk.Canvas(status_inner, width=16, height=16,
                                          bg=PANEL, highlightthickness=0)
        self.macro_status_dot.pack(side="left", padx=(0, 12))
        self._macro_dot_item = self.macro_status_dot.create_oval(
            2, 2, 14, 14, fill=MUTED, outline=MUTED)

        status_text = tk.Frame(status_inner, bg=PANEL)
        status_text.pack(side="left", anchor="w")
        self.macro_status_label = tk.Label(status_text, text="MACRO LISTA", bg=PANEL,
                                           fg=MUTED, font=(FONT_BOLD, 13))
        self.macro_status_label.pack(anchor="w")
        self.macro_status_hint = tk.Label(
            status_text, text="Graba una secuencia nueva o reproduce la que ya tengas.",
            bg=PANEL, fg=MUTED, font=(FONT, 9))
        self.macro_status_hint.pack(anchor="w", pady=(2, 0))

        keys = tk.Frame(status_inner, bg=PANEL)
        keys.pack(side="right")
        tk.Label(keys, text="F4 / END / SUPR  =  parada de emergencia",
                 bg=PANEL, fg=YELLOW, font=(FONT, 9)).pack(anchor="e")

        simple = tk.Frame(tab, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        simple.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        sm = tk.Frame(simple, bg=PANEL)
        sm.pack(fill="x", padx=16, pady=14)
        tk.Label(sm, text="EDICIÓN RÁPIDA (UN TOQUE)", bg=PANEL, fg=ACCENT2,
                 font=(FONT_BOLD, 12)).pack(anchor="w")
        tk.Label(sm, text="Pulsa G (tecla rápida) para editar al instante la pieza que estás mirando.\n"
                          "Tu F normal sigue intacta: mantén, arrastra y confirma como siempre.",
                 bg=PANEL, fg=FG, font=(FONT, 10), justify="left").pack(
            anchor="w", pady=(4, 10))
        self.macro_seq_btn = ttk.Button(
            sm, text="ACTIVAR EDICIÓN RÁPIDA", style="Accent.TButton",
            command=self.toggle_macro_sequence_mode, cursor="hand2")
        self.macro_seq_btn.pack(fill="x")
        tk.Label(sm, text="Funciona con Fortnite en primer plano. La tecla rápida y los tiempos se cambian en Opciones avanzadas.",
                 bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(6, 0))

        self.macro_adv_btn = ttk.Button(
            tab, text="Mostrar opciones avanzadas", style="Card.TButton",
            command=self._toggle_macro_advanced, cursor="hand2")
        self.macro_adv_btn.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        self.macro_adv = tk.Frame(tab, bg=BG)
        self.macro_adv.grid(row=4, column=0, sticky="nsew")
        self.macro_adv.columnconfigure(0, weight=1)
        self.macro_adv.columnconfigure(1, weight=1)
        self.macro_adv.rowconfigure(1, weight=1)

        trick = tk.Frame(self.macro_adv, bg=PANEL, highlightbackground=BORDER,
                         highlightthickness=1)
        trick.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=(0, 8))
        ti = tk.Frame(trick, bg=PANEL)
        ti.pack(fill="both", expand=True, padx=14, pady=12)

        tk.Label(ti, text="TRUCO FF + CLIC (AUTOMÁTICO)", bg=PANEL, fg=ACCENT2,
                 font=(FONT_BOLD, 10)).pack(anchor="w")
        tk.Label(ti, text="Hace doble F y mantiene la segunda. Solo si quieres el truco automático.",
                 bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(2, 6))

        trick_times = tk.Frame(ti, bg=PANEL)
        trick_times.pack(fill="x", pady=(0, 4))
        tk.Label(trick_times, text="Pausa", bg=PANEL, fg=FG,
                 font=(FONT, 9)).grid(row=0, column=0, sticky="w")
        ttk.Spinbox(trick_times, from_=0, to=60000, increment=5, width=6,
                    textvariable=self.macro_preset_gap_var).grid(
            row=0, column=1, sticky="w", padx=(5, 2))
        tk.Label(trick_times, text="ms", bg=PANEL, fg=MUTED,
                 font=(FONT, 9)).grid(row=0, column=2, sticky="w", padx=(0, 10))
        tk.Label(trick_times, text="Clic", bg=PANEL, fg=FG,
                 font=(FONT, 9)).grid(row=0, column=3, sticky="w")
        ttk.Spinbox(trick_times, from_=0, to=60000, increment=5, width=6,
                    textvariable=self.macro_preset_hold_var).grid(
            row=0, column=4, sticky="w", padx=(5, 2))
        tk.Label(trick_times, text="ms", bg=PANEL, fg=MUTED,
                 font=(FONT, 9)).grid(row=0, column=5, sticky="w", padx=(0, 10))
        tk.Label(trick_times, text="Nº clics", bg=PANEL, fg=FG,
                 font=(FONT, 9)).grid(row=0, column=6, sticky="w")
        ttk.Spinbox(trick_times, from_=0, to=1000000, increment=1, width=6,
                    textvariable=self.macro_trick_clicks_var).grid(
            row=0, column=7, sticky="w", padx=(5, 2))
        tk.Label(trick_times, text="(0=todos)", bg=PANEL, fg=MUTED,
                 font=(FONT, 9)).grid(row=0, column=8, sticky="w")

        tk.Checkbutton(ti, text="Hacer doble F y mantener la segunda",
                       variable=self.macro_trick_double_f_var,
                       bg=PANEL, fg=FG, activebackground=PANEL,
                       activeforeground=FG, selectcolor=PANEL2,
                       highlightthickness=0, bd=0, font=(FONT, 9)).pack(
            anchor="w", pady=(0, 2))

        tk.Checkbutton(ti, text="Seguir activo al soltar F",
                       variable=self.macro_hold_keep_var,
                       bg=PANEL, fg=FG, activebackground=PANEL,
                       activeforeground=FG, selectcolor=PANEL2,
                       highlightthickness=0, bd=0, font=(FONT, 9)).pack(
            anchor="w", pady=(0, 6))

        tk.Frame(ti, bg=BORDER, height=1).pack(fill="x", pady=(0, 6))
        tk.Label(ti, text="EDICIÓN RÁPIDA: TECLAS Y TIEMPOS", bg=PANEL, fg=ACCENT2,
                 font=(FONT_BOLD, 9)).pack(anchor="w")
        tk.Label(ti, text="La tecla rápida debe ser una tecla libre (no F). F se usa para editar normal.",
                 bg=PANEL, fg=MUTED, font=(FONT, 8), wraplength=430,
                 justify="left").pack(anchor="w", pady=(1, 4))

        seq_times = tk.Frame(ti, bg=PANEL)
        seq_times.pack(fill="x", pady=(0, 4))
        tk.Label(seq_times, text="Tecla rápida", bg=PANEL, fg=FG,
                 font=(FONT, 9)).grid(row=0, column=0, sticky="w")
        ttk.Entry(seq_times, width=5, textvariable=self.macro_seq_key_var).grid(
            row=0, column=1, sticky="w", padx=(5, 10))
        tk.Label(seq_times, text="Editar (Fortnite)", bg=PANEL, fg=FG,
                 font=(FONT, 9)).grid(row=0, column=2, sticky="w")
        ttk.Entry(seq_times, width=5, textvariable=self.macro_seq_edit_var).grid(
            row=0, column=3, sticky="w", padx=(5, 10))

        tk.Label(seq_times, text="Entrar", bg=PANEL, fg=FG,
                 font=(FONT, 9)).grid(row=1, column=0, sticky="w", pady=(3, 0))
        ttk.Spinbox(seq_times, from_=0, to=2000, increment=1, width=5,
                    textvariable=self.macro_seq_press_var).grid(
            row=1, column=1, sticky="w", padx=(5, 2), pady=(3, 0))
        tk.Label(seq_times, text="ms", bg=PANEL, fg=MUTED,
                 font=(FONT, 9)).grid(row=1, column=2, sticky="w", pady=(3, 0))
        tk.Label(seq_times, text="Clic", bg=PANEL, fg=FG,
                 font=(FONT, 9)).grid(row=1, column=3, sticky="w", pady=(3, 0))
        ttk.Spinbox(seq_times, from_=0, to=2000, increment=1, width=5,
                    textvariable=self.macro_seq_click_var).grid(
            row=1, column=4, sticky="w", padx=(5, 2), pady=(3, 0))
        tk.Label(seq_times, text="ms", bg=PANEL, fg=MUTED,
                 font=(FONT, 9)).grid(row=1, column=5, sticky="w", pady=(3, 0))

        tk.Label(seq_times, text="Confirmar", bg=PANEL, fg=FG,
                 font=(FONT, 9)).grid(row=2, column=0, sticky="w", pady=(3, 0))
        ttk.Spinbox(seq_times, from_=0, to=2000, increment=1, width=5,
                    textvariable=self.macro_seq_confirm_var).grid(
            row=2, column=1, sticky="w", padx=(5, 2), pady=(3, 0))
        tk.Label(seq_times, text="ms (solo sin Auto-Confirm)", bg=PANEL, fg=MUTED,
                 font=(FONT, 8)).grid(row=2, column=2, columnspan=4,
                                      sticky="w", pady=(3, 0))

        tk.Checkbutton(ti, text="Fortnite con Auto-Confirm Edits (Edit o Both)",
                       variable=self.macro_seq_autoconfirm_var,
                       bg=PANEL, fg=FG, activebackground=PANEL,
                       activeforeground=FG, selectcolor=PANEL2,
                       highlightthickness=0, bd=0, font=(FONT, 9)).pack(
            anchor="w", pady=(0, 4))

        self.macro_hold_btn = ttk.Button(
            ti, text="MODO SOLO CLICS CON F", style="Card.TButton",
            command=self.toggle_macro_hold_mode, cursor="hand2")
        self.macro_hold_btn.pack(fill="x", pady=(4, 3))

        self.macro_trick_start_btn = ttk.Button(
            ti, text="INICIAR TRUCO FF", style="Accent.TButton",
            command=self.start_macro_trick, cursor="hand2")
        self.macro_trick_start_btn.pack(fill="x", pady=3)

        self.macro_trick_stop_btn = ttk.Button(
            ti, text="DETENER TRUCO", style="Danger.TButton",
            command=self.stop_macro_playback, cursor="hand2")
        self.macro_trick_stop_btn.pack(fill="x", pady=3)
        self.macro_trick_stop_btn.state(["disabled"])

        play = tk.Frame(self.macro_adv, bg=PANEL, highlightbackground=BORDER,
                        highlightthickness=1)
        play.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=(0, 8))
        pi = tk.Frame(play, bg=PANEL)
        pi.pack(fill="both", expand=True, padx=14, pady=12)

        tk.Label(pi, text="GRABAR / REPRODUCIR", bg=PANEL, fg=ACCENT2,
                 font=(FONT_BOLD, 10)).pack(anchor="w")
        tk.Label(pi, text="Graba tus teclas y clics y reprodúcelos las veces que quieras.",
                 bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(2, 6))

        timing = tk.Frame(pi, bg=PANEL)
        timing.pack(fill="x", pady=(0, 6))
        timing.columnconfigure(1, weight=1)

        tk.Label(timing, text="Retardo extra (ms)", bg=PANEL, fg=FG,
                 font=(FONT, 9)).grid(row=0, column=0, sticky="w", pady=2)
        ttk.Spinbox(timing, from_=0, to=60000, increment=1, width=8,
                    textvariable=self.macro_extra_delay_var).grid(
            row=0, column=1, sticky="e", pady=2)

        tk.Label(timing, text="Pausa entre vueltas (ms)", bg=PANEL, fg=FG,
                 font=(FONT, 9)).grid(row=1, column=0, sticky="w", pady=2)
        ttk.Spinbox(timing, from_=0, to=60000, increment=10, width=8,
                    textvariable=self.macro_loop_pause_var).grid(
            row=1, column=1, sticky="e", pady=2)

        tk.Label(timing, text="Repeticiones (0 = infinito)", bg=PANEL, fg=FG,
                 font=(FONT, 9)).grid(row=2, column=0, sticky="w", pady=2)
        ttk.Spinbox(timing, from_=0, to=1000000, increment=1, width=8,
                    textvariable=self.macro_repeat_var).grid(
            row=2, column=1, sticky="e", pady=2)

        self.macro_play_btn = ttk.Button(pi, text="REPRODUCIR",
                                         style="Accent.TButton",
                                         command=self.start_macro_playback,
                                         cursor="hand2")
        self.macro_play_btn.pack(fill="x", pady=3)

        self.macro_stop_play_btn = ttk.Button(pi, text="DETENER",
                                              style="Danger.TButton",
                                              command=self.stop_macro_playback,
                                              cursor="hand2")
        self.macro_stop_play_btn.pack(fill="x", pady=3)
        self.macro_stop_play_btn.state(["disabled"])

        seq = tk.Frame(self.macro_adv, bg=PANEL, highlightbackground=BORDER,
                       highlightthickness=1)
        seq.grid(row=1, column=0, columnspan=2, sticky="nsew")
        si = tk.Frame(seq, bg=PANEL)
        si.pack(fill="both", expand=True, padx=14, pady=12)

        head = tk.Frame(si, bg=PANEL)
        head.pack(fill="x")
        tk.Label(head, text="PASOS GRABADOS", bg=PANEL, fg=ACCENT2,
                 font=(FONT_BOLD, 10)).pack(side="left")
        self.macro_count_label = tk.Label(head, text="0 pasos", bg=PANEL, fg=MUTED,
                                          font=(FONT_BOLD, 9))
        self.macro_count_label.pack(side="right")

        rec_tools = tk.Frame(si, bg=PANEL)
        rec_tools.pack(fill="x", pady=(4, 4))
        self.macro_record_btn = ttk.Button(
            rec_tools, text="GRABAR SECUENCIA", style="Card.TButton",
            command=self.start_macro_recording, cursor="hand2")
        self.macro_record_btn.pack(side="left")
        self.macro_stop_record_btn = ttk.Button(
            rec_tools, text="DETENER GRAB. (F9)", style="Danger.TButton",
            command=self.stop_macro_recording, cursor="hand2")
        self.macro_stop_record_btn.pack(side="left", padx=(6, 0))
        self.macro_stop_record_btn.state(["disabled"])
        self.macro_clear_btn = ttk.Button(
            rec_tools, text="LIMPIAR", style="Card.TButton",
            command=self.clear_macro_steps, cursor="hand2")
        self.macro_clear_btn.pack(side="left", padx=(6, 0))
        tk.Label(rec_tools, text="Grabacion manual: cuenta atras de 3 s.",
                 bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(side="right")

        tk.Label(si, text="Selecciona un paso y cambia sus ms abajo. "
                          "Tambien puedes hacer doble clic sobre un paso.",
                 bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(anchor="w", pady=(2, 6))

        list_box = tk.Frame(si, bg=PANEL2, highlightbackground=BORDER, highlightthickness=1)
        list_box.pack(fill="both", expand=True)
        self.macro_listbox = tk.Listbox(
            list_box, bg=PANEL2, fg=FG, selectbackground=ACCENT,
            selectforeground="#ffffff", relief="flat", bd=0,
            font=("Consolas", 9), activestyle="none", highlightthickness=0)
        self.macro_listbox.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=6)
        scroll = ttk.Scrollbar(list_box, orient="vertical", command=self.macro_listbox.yview)
        scroll.pack(side="right", fill="y")
        self.macro_listbox.configure(yscrollcommand=scroll.set)
        self.macro_listbox.bind("<<ListboxSelect>>", self._macro_on_select)
        self.macro_listbox.bind("<Double-Button-1>", self._macro_edit_delay)

        bottom = tk.Frame(si, bg=PANEL)
        bottom.pack(fill="x", pady=(6, 0))
        tk.Label(bottom, text="Retardo del paso (ms):", bg=PANEL, fg=FG,
                 font=(FONT, 9)).pack(side="left")
        ttk.Spinbox(bottom, from_=0, to=60000, increment=5, width=7,
                    textvariable=self.macro_selected_delay_var).pack(
            side="left", padx=(5, 5))
        ttk.Button(bottom, text="APLICAR", style="Card.TButton",
                   command=self.apply_macro_step_delay, cursor="hand2").pack(side="left")
        ttk.Button(bottom, text="SUBIR", style="Card.TButton",
                   command=lambda: self.move_macro_step(-1), cursor="hand2").pack(
            side="left", padx=(6, 0))
        ttk.Button(bottom, text="BAJAR", style="Card.TButton",
                   command=lambda: self.move_macro_step(1), cursor="hand2").pack(
            side="left", padx=(4, 0))
        ttk.Button(bottom, text="ELIMINAR", style="Card.TButton",
                   command=self.delete_macro_step, cursor="hand2").pack(
            side="left", padx=(6, 0))
        tk.Label(bottom, text="F8 / END / SUPR paran la reproducción.",
                 bg=PANEL, fg=YELLOW, font=(FONT, 9)).pack(side="right")

        self.macro_advanced_visible = False
        self.macro_adv.grid_remove()
        self._macro_update_status("idle")

    def _build_tab_energia(self):
        tab = self._new_tab("  Energia y Delay  ")

        ttk.Label(tab, text="Varios planes de energia seguros y ajustes de delay para Fortnite. "
                            "Todo es reversible.",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        grid = ttk.Frame(tab)
        grid.pack(fill="both", expand=True, pady=(6, 0))
        for i in range(2):
            grid.columnconfigure(i, weight=1)

        cards = [
            ("Planes de energia", [
                ("Equilibrado (Windows)", lambda: self.apply_plan("balanced")),
                ("Alto rendimiento", lambda: self.apply_plan("high")),
                ("Maximo rendimiento (Ultimate)", lambda: self.apply_plan("ultimate")),
                ("Pyland Gaming (baja latencia)", lambda: self.apply_plan("gaming")),
                ("Restaurar plan anterior", self.do_restore_prev_plan),
            ]),
            ("Delay / latencia extra", [
                ("Ajustes Fortnite (pantalla completa + GPU)", self.do_fortnite_tweaks),
                ("Baja latencia de red (TCPNoDelay)", lambda: self.run_steps(
                    "Latencia de red", [("Aplicando TCPNoDelay", self.cmds_tcp_nodelay())])),
                ("Revertir delay / latencia extra", lambda: self.run_steps(
                    "Revertir latencia extra", [("Restaurando ajustes", self.cmds_latency_extra_revert())])),
            ]),
            ("Segundo plano", [
                ("Modo juego: cerrar apps de fondo", self.do_close_background),
            ]),
        ]

        for idx, (title, actions) in enumerate(cards):
            self._card(grid, title, actions).grid(
                row=idx // 2, column=idx % 2, sticky="nsew", padx=6, pady=6)

        self._notice(tab, "El plan se aplica al instante. «Restaurar plan anterior» vuelve al que tenias.\n"
                          "El modo juego solo cierra apps: no desinstala ni desactiva nada.")

    # ------------------------------------------------- potato graphics UI
    def _build_tab_graficos(self):
        tab = self._new_tab("  Graficos  ", padding=0)

        bottom = tk.Frame(tab, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=14, pady=(0, 14))

        canvas = tk.Canvas(tab, bg=BG, highlightthickness=0, bd=0)
        scroll = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        content = tk.Frame(canvas, bg=BG)
        window = canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>",
                     lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfigure(window, width=e.width))
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True, padx=14, pady=14)
        scroll.pack(side="right", fill="y", pady=14)

        def _wheel(event):
            canvas.yview_scroll(int(-event.delta / 120), "units")

        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _wheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))

        ttk.Label(content, text="Perfiles de rendimiento por juego, estilo NVIDIA Profile Inspector. "
                                "Aplica Potato Graphics y quitalo cuando quieras.",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        hero = tk.Frame(content, bg=PANEL, highlightbackground=ACCENT, highlightthickness=1)
        hero.pack(fill="x", pady=(0, 8))
        hi = tk.Frame(hero, bg=PANEL)
        hi.pack(fill="x", padx=16, pady=12)

        left = tk.Frame(hi, bg=PANEL)
        left.pack(side="left", fill="x", expand=True)
        title_row = tk.Frame(left, bg=PANEL)
        title_row.pack(anchor="w")
        tk.Label(title_row, text="POTATO GRAPHICS STUDIO", bg=PANEL, fg=FG,
                 font=(FONT_BOLD, 15)).pack(side="left")
        tk.Label(title_row, text="PRO", bg=PANEL, fg=ACCENT2,
                 font=(FONT_BOLD, 8)).pack(side="left", padx=(8, 0), pady=(4, 0))
        tk.Label(left, text="Optimiza Fortnite y otros juegos segun tu hardware real. "
                            "Cada perfil guarda una copia de seguridad automatica.",
                 bg=PANEL, fg=MUTED, font=(FONT, 9), justify="left",
                 wraplength=590).pack(anchor="w", pady=(4, 8))

        chips = tk.Frame(left, bg=PANEL)
        chips.pack(anchor="w")
        self.graphics_hw_labels = {}
        for key, label in (("gpu", "GPU"), ("cpu", "CPU"), ("ram", "RAM"), ("res", "Pantalla")):
            chip = tk.Frame(chips, bg=PANEL2, highlightbackground=BORDER, highlightthickness=1)
            chip.pack(side="left", padx=(0, 6))
            tk.Label(chip, text=label, bg=PANEL2, fg=MUTED,
                     font=(FONT_BOLD, 7)).pack(side="left", padx=(8, 4), pady=5)
            value = tk.Label(chip, text="--", bg=PANEL2, fg=FG, font=(FONT, 8))
            value.pack(side="left", padx=(0, 8), pady=5)
            self.graphics_hw_labels[key] = value

        right = tk.Frame(hi, bg=PANEL)
        right.pack(side="right", padx=(10, 0))
        ttk.Button(right, text="OPTIMIZAR FORTNITE AHORA", style="Accent.TButton",
                   command=self.do_optimize_fortnite_potato, cursor="hand2").pack(fill="x")
        ttk.Button(right, text="Analizar mi PC", style="Card.TButton",
                   command=self.scan_graphics_hardware, cursor="hand2").pack(
            fill="x", pady=(6, 0))

        body = ttk.Frame(content)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=2, uniform="graphics")
        body.columnconfigure(1, weight=3, uniform="graphics")
        body.rowconfigure(0, weight=1)

        prof_card = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        prof_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        pi = tk.Frame(prof_card, bg=PANEL)
        pi.pack(fill="both", expand=True, padx=12, pady=10)

        head = tk.Frame(pi, bg=PANEL)
        head.pack(fill="x")
        bar = tk.Frame(head, bg=ACCENT, width=4, height=16)
        bar.pack_propagate(False)
        bar.pack(side="left", padx=(0, 8))
        tk.Label(head, text="PERFIL DE JUEGO", bg=PANEL, fg=ACCENT2,
                 font=(FONT_BOLD, 10)).pack(side="left")
        tk.Label(head, text="NVIDIA-style", bg=PANEL, fg=MUTED,
                 font=(FONT, 8)).pack(side="right")
        tk.Frame(pi, bg=BORDER, height=1).pack(fill="x", pady=(8, 8))

        tree_box = tk.Frame(pi, bg=PANEL2, highlightbackground=BORDER, highlightthickness=1)
        tree_box.pack(fill="both", expand=True)
        self.graphics_tree = ttk.Treeview(
            tree_box, columns=("juego", "estado"), show="headings",
            style="Graphics.Treeview", height=6, selectmode="browse")
        self.graphics_tree.heading("juego", text="Juego")
        self.graphics_tree.heading("estado", text="Estado")
        self.graphics_tree.column("juego", width=205, anchor="w")
        self.graphics_tree.column("estado", width=95, anchor="center")
        self.graphics_tree.pack(fill="both", expand=True)
        self.graphics_tree.tag_configure("activo", foreground=GREEN)
        self.graphics_tree.tag_configure("listo", foreground=FG)
        self.graphics_tree.tag_configure("falta", foreground=YELLOW)
        self.graphics_tree.tag_configure("custom", foreground=ACCENT2)
        self.graphics_tree.bind("<<TreeviewSelect>>", self._on_graphics_profile_select)

        row = tk.Frame(pi, bg=PANEL)
        row.pack(fill="x", pady=(8, 0))
        ttk.Button(row, text="Elegir .exe", style="Card.TButton",
                   command=self.choose_custom_exe, cursor="hand2").pack(side="left")
        ttk.Button(row, text="Actualizar", style="Card.TButton",
                   command=self._refresh_graphics_ui, cursor="hand2").pack(
            side="left", padx=6)

        self.graphics_profile_info = tk.Label(
            pi, text="", bg=PANEL, fg=MUTED, font=(FONT, 8),
            justify="left", anchor="w", wraplength=360)
        self.graphics_profile_info.pack(fill="x", pady=(8, 0))

        lvl_card = tk.Frame(body, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        lvl_card.grid(row=0, column=1, sticky="nsew")
        li = tk.Frame(lvl_card, bg=PANEL)
        li.pack(fill="both", expand=True, padx=12, pady=10)

        head2 = tk.Frame(li, bg=PANEL)
        head2.pack(fill="x")
        bar2 = tk.Frame(head2, bg=ACCENT, width=4, height=16)
        bar2.pack_propagate(False)
        bar2.pack(side="left", padx=(0, 8))
        tk.Label(head2, text="NIVEL DE POTATO GRAPHICS", bg=PANEL, fg=ACCENT2,
                 font=(FONT_BOLD, 10)).pack(side="left")
        self.graphics_auto_reco = tk.Label(head2, text="", bg=PANEL, fg=GREEN,
                                           font=(FONT_BOLD, 8))
        self.graphics_auto_reco.pack(side="right")
        tk.Frame(li, bg=BORDER, height=1).pack(fill="x", pady=(8, 8))

        levels = tk.Frame(li, bg=PANEL)
        levels.pack(fill="both", expand=True)
        for level_id in POTATO_ORDER:
            self._build_graphics_level_card(levels, level_id)

        self.graphics_level_detail = tk.Label(
            li, text="", bg=PANEL, fg=MUTED, font=(FONT, 8),
            justify="left", anchor="w", wraplength=520)
        self.graphics_level_detail.pack(fill="x", pady=(6, 0))

        actions = tk.Frame(bottom, bg=BG)
        actions.pack(fill="x")
        ttk.Button(actions, text="APLICAR POTATO GRAPHICS", style="Accent.TButton",
                   command=self.do_apply_potato_graphics, cursor="hand2").pack(
            side="left", fill="x", expand=True)
        ttk.Button(actions, text="QUITAR POTATO GRAPHICS", style="Danger.TButton",
                   command=self.do_remove_potato_graphics, cursor="hand2").pack(
            side="left", fill="x", expand=True, padx=(8, 0))
        ttk.Button(actions, text="RESTAURAR TODO", style="Danger.TButton",
                   command=self.do_remove_all_potato_graphics, cursor="hand2").pack(
            side="left", padx=(8, 0))

        self.graphics_status = tk.Label(
            bottom, text="Listo. Analiza tu PC y elige un nivel.",
            bg=BG, fg=MUTED, font=(FONT, 8), anchor="w")
        self.graphics_status.pack(fill="x", pady=(6, 0))

        self._notice(
            bottom,
            "Cierra el juego antes de aplicar. PylandTweaks guarda una copia de "
            "seguridad de cada archivo y la restaura con QUITAR POTATO GRAPHICS. "
            "No se modifica el driver de la GPU.")

        self.root.after(200, self._refresh_graphics_ui)

    def _build_graphics_level_card(self, parent, level_id):
        data = POTATO_LEVELS[level_id]
        card = tk.Frame(parent, bg=PANEL2, highlightbackground=BORDER,
                        highlightthickness=1, cursor="hand2")
        card.pack(fill="x", pady=2)
        inner = tk.Frame(card, bg=PANEL2)
        inner.pack(fill="x", padx=10, pady=7)

        dot = tk.Canvas(inner, width=14, height=14, bg=PANEL2, highlightthickness=0)
        dot.pack(side="left", padx=(0, 8))
        circle = dot.create_oval(2, 2, 12, 12, outline=MUTED, width=2)

        text = tk.Frame(inner, bg=PANEL2)
        text.pack(side="left", fill="x", expand=True)
        name = tk.Label(text, text=data["name"], bg=PANEL2, fg=FG,
                        font=(FONT_BOLD, 9), anchor="w")
        name.pack(fill="x")
        desc = tk.Label(text, text=data["desc"], bg=PANEL2, fg=MUTED,
                        font=(FONT, 8), anchor="w", justify="left", wraplength=360)
        desc.pack(fill="x")

        right = tk.Frame(inner, bg=PANEL2)
        right.pack(side="right")
        badge = tk.Label(right, text=data["impact"], bg=PANEL2, fg=GREEN,
                         font=(FONT_BOLD, 8))
        badge.pack(anchor="e")
        tag = tk.Label(right, text=data["tag"], bg=PANEL2, fg=ACCENT2,
                       font=(FONT_BOLD, 7))
        tag.pack(anchor="e")

        widgets = [card, inner, text, name, desc, right, badge, tag, dot]
        for widget in widgets:
            widget.bind("<Button-1>",
                        lambda _e, lid=level_id: self._select_potato_level(lid))
            try:
                widget.configure(cursor="hand2")
            except tk.TclError:
                pass

        self.graphics_level_widgets[level_id] = {
            "frame": card, "inner": inner, "dot": dot, "circle": circle,
            "text": text, "name": name, "desc": desc, "right": right,
            "badge": badge, "tag": tag,
        }

    def _paint_graphics_widget(self, widget, bg):
        try:
            widget.configure(bg=bg)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self._paint_graphics_widget(child, bg)

    def _refresh_graphics_level_cards(self):
        for level_id, widgets in self.graphics_level_widgets.items():
            selected = level_id == self.potato_level
            bg = PANEL3 if selected else PANEL2
            self._paint_graphics_widget(widgets["frame"], bg)
            widgets["frame"].configure(
                highlightbackground=ACCENT if selected else BORDER)
            widgets["dot"].configure(bg=bg)
            try:
                widgets["dot"].itemconfigure(
                    widgets["circle"], outline=ACCENT2 if selected else MUTED,
                    fill=ACCENT if selected else bg, width=2)
            except tk.TclError:
                pass

    def _select_potato_level(self, level_id):
        if level_id not in POTATO_LEVELS:
            return
        self.potato_level = level_id
        self._refresh_graphics_level_cards()
        self._update_graphics_level_detail()

    def _on_graphics_profile_select(self, _event=None):
        if self.graphics_profile_refreshing:
            return
        selection = self.graphics_tree.selection()
        if not selection:
            return
        self.graphics_profile = selection[0]
        self._update_graphics_profile_info()

    def _update_graphics_level_detail(self):
        level_id = self.potato_level
        if level_id == "auto":
            resolved = self._auto_level_for_hw(self.hw_info)
            data = POTATO_LEVELS[resolved]
            text = (f"Automatico: se aplicara {data['name']} "
                    f"(3D al {int(data['res'])}%, impacto {data['impact']}).")
            if not self.hw_info:
                text = ("Automatico: pulsa Analizar mi PC para calcular el nivel "
                        "ideal. Si aplicas sin analizar, se detecta al momento.")
        else:
            data = POTATO_LEVELS[level_id]
            text = (f"{data['name']}: resolucion 3D al {int(data['res'])}% | "
                    f"calidad general al minimo | {data['impact']}.")
        self.graphics_level_detail.configure(text=text)
        reco = ""
        if self.hw_info:
            resolved = self._auto_level_for_hw(self.hw_info)
            reco = "AUTO: " + POTATO_LEVELS[resolved]["short"]
        self.graphics_auto_reco.configure(text=reco)

    def _apply_hardware_to_ui(self):
        hw = self.hw_info or {}
        gpu = hw.get("gpu") or "--"
        cpu = hw.get("cpu") or "--"
        ram = hw.get("ram")
        resx = hw.get("resx") or 0
        resy = hw.get("resy") or 0
        hz = hw.get("hz") or 0
        vram = hw.get("vram") or 0
        gpu_text = gpu if len(gpu) <= 34 else gpu[:31] + "..."
        cpu_text = cpu if len(cpu) <= 30 else cpu[:27] + "..."
        if gpu_text and vram:
            gpu_text = f"{gpu_text} ({vram:g} GB)"
        self.graphics_hw_labels["gpu"].configure(text=gpu_text or "--")
        self.graphics_hw_labels["cpu"].configure(
            text=f"{cpu_text} ({hw.get('cores', '?')}C/{hw.get('threads', '?')}T)"
            if cpu != "--" else "--")
        self.graphics_hw_labels["ram"].configure(
            text=f"{ram:g} GB" if isinstance(ram, (int, float)) else "--")
        self.graphics_hw_labels["res"].configure(
            text=f"{resx}x{resy} @ {hz} Hz" if resx and resy else "--")
        self._update_graphics_level_detail()

    def _refresh_graphics_ui(self):
        self.graphics_profile_refreshing = True
        try:
            state = self._load_graphics_state()
            self.graphics_tree.delete(*self.graphics_tree.get_children())
            for profile in GAME_PROFILES:
                pid = profile["id"]
                pstate = state.get(pid) or {}
                active = bool(pstate.get("active"))
                if pid == "generic":
                    status = "ACTIVO" if active else "Elegir .exe"
                    tag = "activo" if active else "custom"
                elif self._graphics_config_paths(pid):
                    status = "ACTIVO" if active else "Listo"
                    tag = "activo" if active else "listo"
                else:
                    status = "Abrir juego"
                    tag = "falta"
                self.graphics_tree.insert(
                    "", "end", iid=pid, values=(profile["name"], status), tags=(tag,))
            if self.graphics_profile in GAME_PROFILES_IDS:
                self.graphics_tree.selection_set(self.graphics_profile)
            else:
                self.graphics_profile = "fortnite"
                self.graphics_tree.selection_set("fortnite")
        finally:
            self.graphics_profile_refreshing = False
        active_names = [self._graphics_profile(pid)["name"]
                        for pid, pstate in state.items()
                        if isinstance(pstate, dict) and pstate.get("active")]
        if active_names:
            self.graphics_status.configure(
                text="Potato activo en: " + ", ".join(active_names))
        else:
            self.graphics_status.configure(
                text="Listo. Analiza tu PC y elige un nivel.")
        self._update_graphics_profile_info()
        self._update_graphics_level_detail()
        self._refresh_graphics_level_cards()

    def _update_graphics_profile_info(self):
        profile = self._graphics_profile(self.graphics_profile)
        paths = self._graphics_config_paths(self.graphics_profile)
        exe = self._graphics_exe_path(self.graphics_profile)
        lines = [profile["note"]]
        if self.graphics_profile == "generic":
            lines.append(f"EXE: {self.custom_exe or 'sin seleccionar'}")
        elif paths:
            lines.append(f"Config: {paths[0]}")
        else:
            lines.append("Config: no encontrada. Abre el juego una vez para crearla.")
        if exe:
            lines.append(f"EXE: {exe}")
        state = self._load_graphics_state().get(self.graphics_profile) or {}
        if state.get("active"):
            level = state.get("level", "auto")
            name = POTATO_LEVELS.get(level, {}).get("name", level)
            lines.append(f"Potato activo: {name}")
        self.graphics_profile_info.configure(text="\n".join(lines))

    def _graphics_profile(self, profile_id):
        for profile in GAME_PROFILES:
            if profile["id"] == profile_id:
                return profile
        return GAME_PROFILES[0]

    def choose_custom_exe(self):
        path = filedialog.askopenfilename(
            title="Elige el ejecutable del juego",
            filetypes=[("Ejecutables", "*.exe"), ("Todos", "*.*")],
            parent=self.root)
        if not path:
            return
        self.custom_exe = path
        self.graphics_profile = "generic"
        self._refresh_graphics_ui()

    def _graphics_config_paths(self, profile_id):
        try:
            if profile_id == "fortnite":
                cfg = self._fortnite_config_dir()
                paths = [cfg / "GameUserSettings.ini", cfg / "Engine.ini"]
                return [p for p in paths if p.exists()]
            if profile_id == "cs2":
                path = self._find_cs2_video()
                return [path] if path else []
            if profile_id == "gta5":
                path = self._find_gta5_settings()
                return [path] if path and path.exists() else []
            if profile_id == "minecraft":
                path = self._find_minecraft_options()
                return [path] if path and path.exists() else []
            if profile_id == "generic":
                return [Path(self.custom_exe)] if self.custom_exe else []
        except Exception:  # noqa: BLE001
            return []
        return []

    # ----------------------------------------------- potato graphics logic
    def _fortnite_config_dir(self):
        base = os.environ.get("LOCALAPPDATA") or str(Path.home())
        return Path(base) / "FortniteGame" / "Saved" / "Config" / "WindowsClient"

    def _steam_path(self):
        if winreg is not None:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam") as key:
                    path = winreg.QueryValueEx(key, "SteamPath")[0]
                    candidate = Path(str(path))
                    if candidate.exists():
                        return candidate
            except OSError:
                pass
        for raw in (r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam",
                    r"D:\Steam", r"D:\SteamLibrary", r"E:\Steam", r"E:\SteamLibrary"):
            candidate = Path(raw)
            if candidate.exists():
                return candidate
        return None

    def _find_cs2_video(self):
        steam = self._steam_path()
        if not steam:
            return None
        matches = list((steam / "userdata").glob("*/730/local/cfg/video.txt"))
        if not matches:
            return None
        return max(matches, key=lambda p: p.stat().st_mtime)

    def _find_gta5_settings(self):
        home = Path(os.environ.get("USERPROFILE") or Path.home())
        candidates = [
            home / "Documents" / "Rockstar Games" / "GTA V" / "settings.xml",
            home / "OneDrive" / "Documents" / "Rockstar Games" / "GTA V" / "settings.xml",
        ]
        onedrive = os.environ.get("OneDrive")
        if onedrive:
            candidates.insert(
                1, Path(onedrive) / "Documents" / "Rockstar Games" / "GTA V" / "settings.xml")
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0]

    def _find_minecraft_options(self):
        base = os.environ.get("APPDATA")
        if not base:
            return None
        return Path(base) / ".minecraft" / "options.txt"

    def _graphics_exe_path(self, profile_id):
        if profile_id == "fortnite":
            candidate = Path(FORTNITE_EXE)
            return str(candidate) if candidate.exists() else None
        if profile_id == "cs2":
            steam = self._steam_path()
            if steam:
                candidate = (steam / "steamapps" / "common" /
                             "Counter-Strike Global Offensive" / "game" /
                             "bin" / "win64" / "cs2.exe")
                if candidate.exists():
                    return str(candidate)
            return None
        if profile_id == "gta5":
            steam = self._steam_path()
            candidates = []
            if steam:
                candidates.append(steam / "steamapps" / "common" /
                                  "Grand Theft Auto V" / "GTA5.exe")
            candidates.extend([
                Path(r"C:\Program Files\Rockstar Games\Grand Theft Auto V\GTA5.exe"),
                Path(r"C:\Program Files\Epic Games\GTAV\GTA5.exe"),
                Path(r"D:\SteamLibrary\steamapps\common\Grand Theft Auto V\GTA5.exe"),
            ])
            for candidate in candidates:
                if candidate.exists():
                    return str(candidate)
            return None
        if profile_id == "generic":
            return self.custom_exe or None
        return None

    def _detect_hardware_blocking(self):
        data = parse_ps_json(self._ps(HW_SCAN_PS))

        def number(key, default=0):
            try:
                return float(data.get(key) or default)
            except (TypeError, ValueError):
                return default

        hw = {
            "gpu": str(data.get("gpu") or ""),
            "vram": number("vram"),
            "cpu": str(data.get("cpu") or ""),
            "cores": int(number("cores")),
            "threads": int(number("threads")),
            "ram": number("ram"),
            "resx": int(number("resx")),
            "resy": int(number("resy")),
            "hz": int(number("hz")),
            "os": str(data.get("os") or ""),
        }
        hw["gpu_type"] = classify_gpu(hw["gpu"], hw["vram"])
        return hw

    def scan_graphics_hardware(self):
        if self.busy:
            messagebox.showinfo("En curso", "Espera a que termine la tarea actual.")
            return

        def worker():
            self.log("### Potato Graphics: analizando hardware ###")
            hw = self._detect_hardware_blocking()
            self.hw_info = hw
            self.root.after(0, self._apply_hardware_to_ui)
            self.log("Hardware: {} | {} GB RAM | {}x{} @ {} Hz | GPU {}".format(
                hw.get("gpu") or "desconocida", hw.get("ram"), hw.get("resx"),
                hw.get("resy"), hw.get("hz"), hw.get("gpu_type")))

        self.start_task("Analizar PC", worker)

    def _auto_level_for_hw(self, hw):
        if not hw:
            return "nivel2"
        score = 0
        gpu_type = hw.get("gpu_type") or classify_gpu(
            hw.get("gpu", ""), hw.get("vram", 0))
        vram = hw.get("vram") or 0
        if gpu_type == "integrada":
            score -= 2
            vram = 0
        if vram:
            if vram < 2:
                score -= 2
            elif vram < 4:
                score -= 1
            elif vram >= 8:
                score += 1
        ram = hw.get("ram") or 0
        if ram:
            if ram < 6:
                score -= 2
            elif ram < 8:
                score -= 1
            elif ram >= 16:
                score += 1
        cores = hw.get("cores") or 0
        if cores:
            if cores <= 2:
                score -= 1
            elif cores >= 8:
                score += 1
        if (hw.get("resx") or 0) >= 2560:
            score -= 1
        if score <= -3:
            return "nivel3"
        if score <= 0:
            return "nivel2"
        return "nivel1"

    def _resolve_level(self, level_choice, hw):
        level_id = level_choice
        if level_id == "auto":
            level_id = self._auto_level_for_hw(hw)
        return level_id, POTATO_LEVELS[level_id]

    # --------------------------------------------------- graphics state
    def _graphics_state_path(self):
        base = Path(os.environ.get("APPDATA") or Path.home())
        return base / "PylandTweaks" / "graphics_state.json"

    def _graphics_backup_root(self):
        base = Path(os.environ.get("APPDATA") or Path.home())
        return base / "PylandTweaks" / "GraphicsBackup"

    def _load_graphics_state(self):
        try:
            path = self._graphics_state_path()
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except Exception as exc:  # noqa: BLE001
            self.log(f"No se pudo leer el estado de Graficos: {exc}")
        return {}

    def _save_graphics_state(self, state):
        path = self._graphics_state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                        encoding="utf-8")

    # -------------------------------------------------------- registro
    def _reg_root(self, hive):
        if winreg is None:
            raise RuntimeError("winreg no disponible")
        return winreg.HKEY_CURRENT_USER if hive == "HKCU" else winreg.HKEY_LOCAL_MACHINE

    def _reg_read(self, hive, key, name):
        if winreg is None:
            return None, None
        try:
            with winreg.OpenKey(self._reg_root(hive), key, 0, winreg.KEY_READ) as handle:
                data, typ = winreg.QueryValueEx(handle, name)
                return typ, data
        except OSError:
            return None, None

    def _reg_set(self, hive, key, name, typ, data):
        if winreg is None:
            raise RuntimeError("winreg no disponible")
        with winreg.CreateKeyEx(self._reg_root(hive), key, 0,
                                winreg.KEY_SET_VALUE) as handle:
            winreg.SetValueEx(handle, name, 0, typ, data)

    def _reg_delete(self, hive, key, name):
        if winreg is None:
            return
        try:
            with winreg.OpenKey(self._reg_root(hive), key, 0,
                                winreg.KEY_SET_VALUE) as handle:
                winreg.DeleteValue(handle, name)
        except OSError:
            pass

    def _registry_specs_for_exe(self, exe_path, exe_name):
        if not exe_name or winreg is None:
            return []
        specs = []
        if exe_path:
            specs.append({
                "hive": "HKCU",
                "key": r"Software\Microsoft\DirectX\UserGpuPreferences",
                "name": exe_path,
                "type": winreg.REG_SZ,
                "data": "GpuPreference=2;",
                "label": "GPU de alto rendimiento",
            })
            specs.append({
                "hive": "HKCU",
                "key": r"Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers",
                "name": exe_path,
                "type": winreg.REG_SZ,
                "data": "~ DISABLEDXMAXIMIZEDWINDOWEDMODE",
                "label": "Pantalla completa exclusiva",
            })
        specs.append({
            "hive": "HKLM",
            "key": (r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
                    rf"\Image File Execution Options\{exe_name}\PerfOptions"),
            "name": "CpuPriorityClass",
            "type": winreg.REG_DWORD,
            "data": 6,
            "label": "Prioridad alta de CPU",
        })
        return specs

    # --------------------------------------------------- valores por juego
    def _scaled_resolution(self, hw, percent):
        resx = int(hw.get("resx") or 0)
        resy = int(hw.get("resy") or 0)
        if resx <= 0 or resy <= 0:
            resx, resy = 1920, 1080
        scale = max(0.35, min(1.0, float(percent) / 100.0))
        width = max(960, min(int(resx * scale) // 2 * 2, resx))
        height = max(540, min(int(resy * scale) // 2 * 2, resy))
        return width, height

    def _fortnite_gus_values(self, level, hw):
        values = dict(level["fortnite"])
        hz = int(hw.get("hz") or 60) or 60
        if level["res"] >= 80:
            fps = max(60, hz)
        elif level["res"] >= 60:
            fps = min(240, max(120, hz * 2))
        else:
            fps = 0
        values.update({
            "bUseVSync": "False",
            "bUseDynamicResolution": "False",
            "bEnableMotionBlur": "False",
            "bEnableRayTracing": "False",
            "bUseGPUSkinCache": "True",
            "PreferredFullscreenMode": "0",
            "LastConfirmedFullscreenMode": "0",
            "FullscreenMode": "0",
            "FrameRateLimit": f"{fps:.6f}",
        })
        return values

    def _fortnite_engine_values(self, level, hw):
        return dict(level["engine"])

    def _cs2_values(self, level, hw):
        values = dict(level["cs2"])
        width, height = self._scaled_resolution(hw, level["res"])
        values["setting.defaultres"] = str(width)
        values["setting.defaultresheight"] = str(height)
        return values

    def _gta5_values(self, level, hw):
        values = dict(level["gta5"])
        width, height = self._scaled_resolution(hw, level["res"])
        values["ScreenWidth"] = str(width)
        values["ScreenHeight"] = str(height)
        return values

    def _minecraft_values(self, level, hw):
        return dict(level["minecraft"])

    def _graphics_file_specs(self, profile_id, level, hw):
        specs = []
        if profile_id == "fortnite":
            cfg = self._fortnite_config_dir()
            gus = cfg / "GameUserSettings.ini"
            engine = cfg / "Engine.ini"
            if not gus.exists():
                raise RuntimeError(
                    "No se encontro GameUserSettings.ini.\n\n"
                    "Abre Fortnite una vez, cierra el juego y vuelve a intentar.\n"
                    f"Ruta esperada: {gus}")
            specs.append({
                "path": gus,
                "label": "GameUserSettings.ini",
                "transform": lambda text: ini_set(
                    text, FORTNITE_GUS_SECTION,
                    self._fortnite_gus_values(level, hw)),
            })
            if engine.exists():
                specs.append({
                    "path": engine,
                    "label": "Engine.ini",
                    "transform": lambda text: ini_set(
                        text, "SystemSettings",
                        self._fortnite_engine_values(level, hw)),
                })
            return specs
        if profile_id == "cs2":
            path = self._find_cs2_video()
            if not path:
                raise RuntimeError(
                    "No se encontro video.txt de CS2.\n\n"
                    "Abre CS2 una vez y revisa que Steam este instalado.")
            specs.append({
                "path": path,
                "label": "CS2 video.txt",
                "transform": lambda text: quoted_kv_set(
                    text, self._cs2_values(level, hw)),
            })
            return specs
        if profile_id == "gta5":
            path = self._find_gta5_settings()
            if not path or not path.exists():
                raise RuntimeError(
                    "No se encontro settings.xml de GTA V.\n\n"
                    "Abre GTA V una vez y vuelve a intentar.")
            specs.append({
                "path": path,
                "label": "GTA V settings.xml",
                "transform": lambda text: xml_set_values(
                    text, self._gta5_values(level, hw)),
            })
            return specs
        if profile_id == "minecraft":
            path = self._find_minecraft_options()
            if not path or not path.exists():
                raise RuntimeError(
                    "No se encontro options.txt de Minecraft.\n\n"
                    "Abre Minecraft Java una vez y vuelve a intentar.")
            specs.append({
                "path": path,
                "label": "Minecraft options.txt",
                "transform": lambda text: props_set(
                    text, self._minecraft_values(level, hw)),
            })
            return specs
        if profile_id == "generic" and self.custom_exe:
            return specs
        raise RuntimeError("Perfil de juego no valido.")

    def _apply_graphics_file(self, profile_id, spec, files_state):
        path = Path(spec["path"])
        if not path.exists():
            raise RuntimeError(f"No existe el archivo: {path}")
        if not any(Path(rec.get("path", "")) == path for rec in files_state):
            backup_dir = self._graphics_backup_root() / profile_id
            backup_dir.mkdir(parents=True, exist_ok=True)
            backup = backup_dir / f"{len(files_state) + 1:02d}_{path.name}"
            backup.write_bytes(path.read_bytes())
            files_state.append({
                "path": str(path),
                "backup": str(backup),
                "existed": True,
            })
        text, encoding = read_text_meta(path)
        new_text = spec["transform"](text)
        write_text_meta(path, new_text, encoding)

    def _apply_graphics_registry(self, specs, reg_state):
        for spec in specs:
            existing = None
            for record in reg_state:
                if (record.get("hive") == spec["hive"]
                        and str(record.get("key", "")).lower() == spec["key"].lower()
                        and str(record.get("name", "")).lower() == spec["name"].lower()):
                    existing = record
                    break
            if existing is None:
                typ, old = self._reg_read(spec["hive"], spec["key"], spec["name"])
                existing = {
                    "hive": spec["hive"],
                    "key": spec["key"],
                    "name": spec["name"],
                    "existed": typ is not None,
                    "old": old,
                    "old_type": typ,
                }
                reg_state.append(existing)
            self._reg_set(spec["hive"], spec["key"], spec["name"],
                          spec["type"], spec["data"])

    def _restore_graphics_file(self, record):
        path = Path(record.get("path", ""))
        if record.get("existed"):
            backup = Path(record.get("backup", ""))
            if backup.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(backup.read_bytes())

    def _restore_graphics_registry(self, records):
        for record in records:
            if record.get("existed"):
                typ = record.get("old_type")
                if typ is None and winreg is not None:
                    typ = winreg.REG_SZ
                if typ is not None:
                    self._reg_set(record["hive"], record["key"], record["name"],
                                  int(typ), record.get("old"))
            else:
                self._reg_delete(record.get("hive", "HKCU"),
                                 record.get("key", ""), record.get("name", ""))

    # -------------------------------------------------------- acciones
    def do_apply_potato_graphics(self):
        self._run_graphics_action(self.graphics_profile, self.potato_level)

    def do_optimize_fortnite_potato(self):
        self.graphics_profile = "fortnite"
        self.potato_level = "auto"
        self.root.after(0, self._refresh_graphics_ui)
        self._run_graphics_action("fortnite", "auto", quick=True)

    def do_remove_potato_graphics(self):
        self._run_restore_graphics([self.graphics_profile])

    def do_remove_all_potato_graphics(self):
        state = self._load_graphics_state()
        active = [pid for pid, pstate in state.items()
                  if isinstance(pstate, dict) and pstate.get("active")]
        self._run_restore_graphics(active)

    def _run_graphics_action(self, profile_id, level_choice, quick=False):
        if self.busy:
            messagebox.showinfo("En curso", "Espera a que termine la tarea actual.")
            return
        profile = self._graphics_profile(profile_id)
        exe_path = self._graphics_exe_path(profile_id)
        exe_name = Path(exe_path).name if exe_path else profile.get("exe")
        if profile_id == "generic" and not (exe_path and Path(exe_path).exists()):
            messagebox.showwarning(
                "Perfil personalizado",
                "Elige un .exe valido con el boton 'Elegir .exe'.")
            return
        if profile_id != "generic" and exe_name and process_running(exe_name):
            if not messagebox.askyesno(
                    "Juego abierto",
                    f"{profile['name']} esta abierto.\n\n"
                    "Cierra el juego para que no sobrescriba los cambios. "
                    "Si continuas, la configuracion puede perderse al salir "
                    "del juego.\n\nContinuar de todos modos?"):
                return
        try:
            probe = (POTATO_LEVELS["nivel2"] if level_choice == "auto"
                     else POTATO_LEVELS[level_choice])
            self._graphics_file_specs(profile_id, probe, self.hw_info or {})
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Configuracion no encontrada", str(exc))
            return

        level_name = ("Automatico (segun tu PC)" if level_choice == "auto"
                      else POTATO_LEVELS[level_choice]["name"])
        if not messagebox.askyesno(
            "Aplicar Potato Graphics",
            f"Perfil: {profile['name']}\nNivel: {level_name}\n\n"
            "Se guardara una copia de seguridad de los archivos y ajustes "
            "de registro modificados.\n\n"
            "Puedes revertirlo con QUITAR POTATO GRAPHICS.\n\nContinuar?"):
            return

        title = "OPTIMIZANDO FORTNITE" if quick else "POTATO GRAPHICS"
        overlay = StartupOverlay(self, title, "Analizando hardware y preparando cambios...")
        self.startup_overlay = overlay

        def worker():
            try:
                hw = self.hw_info or self._detect_hardware_blocking()
                if hw and not self.hw_info:
                    self.hw_info = hw
                    self.root.after(0, self._apply_hardware_to_ui)
                resolved_id, level = self._resolve_level(level_choice, hw)
                overlay.set_stage(f"Nivel seleccionado: {level['name']}")
                specs = self._graphics_file_specs(profile_id, level, hw)
                reg_specs = []
                if profile_id != "minecraft":
                    reg_specs = self._registry_specs_for_exe(exe_path, exe_name)
                state = self._load_graphics_state()
                pstate = state.get(profile_id) or {}
                files_state = pstate.get("files") or []
                reg_state = pstate.get("registry") or []

                plan = []
                for spec in specs:
                    plan.append((
                        f"{spec['label']}: {level['short']}",
                        lambda s=spec: self._apply_graphics_file(
                            profile_id, s, files_state)))
                if reg_specs:
                    plan.append((
                        "Registro: GPU dedicada, fullscreen y prioridad",
                        lambda: self._apply_graphics_registry(reg_specs, reg_state)))

                overlay.set_total(max(1, len(plan)))
                cancelled = False
                for index, (label, func) in enumerate(plan, 1):
                    if overlay.cancelled:
                        cancelled = True
                        break
                    overlay.set_stage(label)
                    func()
                    overlay.push(index, label, label)

                pstate["active"] = True
                pstate["level"] = resolved_id
                pstate["profile"] = profile_id
                pstate["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
                pstate["files"] = files_state
                pstate["registry"] = reg_state
                state[profile_id] = pstate
                self._save_graphics_state(state)

                if cancelled:
                    overlay.finish(
                        False, "Cancelado: algunos cambios quedaron aplicados")
                else:
                    self.log(f"Potato Graphics aplicado a {profile['name']} "
                             f"({level['name']}).")
                    overlay.finish(
                        True, f"{profile['name']}: {level['name']} aplicado")
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR Potato Graphics: {exc}")
                overlay.finish(False, f"Error: {exc}")

        self.start_task("Potato Graphics", worker,
                        on_done=self._refresh_graphics_ui)

    def _run_restore_graphics(self, profile_ids):
        if self.busy:
            messagebox.showinfo("En curso", "Espera a que termine la tarea actual.")
            return
        state = self._load_graphics_state()
        todo = {pid: state[pid] for pid in profile_ids
                if isinstance(state.get(pid), dict) and state[pid].get("active")}
        if not todo:
            messagebox.showinfo(
                "Sin cambios",
                "No hay copias de seguridad de Potato Graphics para restaurar.")
            return

        running = []
        for pid in todo:
            exe_path = self._graphics_exe_path(pid)
            exe_name = Path(exe_path).name if exe_path else self._graphics_profile(pid).get("exe")
            if exe_name and process_running(exe_name):
                running.append(self._graphics_profile(pid)["name"])
        if running:
            if not messagebox.askyesno(
                    "Juego abierto",
                    "Cierra estos juegos antes de restaurar:\n\n- "
                    + "\n- ".join(running)
                    + "\n\nSi continuas, el juego puede sobrescribir los "
                      "archivos restaurados.\n\nContinuar de todos modos?"):
                return

        if not messagebox.askyesno(
                "Quitar Potato Graphics",
                "Se restauraran los archivos y ajustes originales de:\n\n- "
                + "\n- ".join(self._graphics_profile(pid)["name"] for pid in todo)
                + "\n\nContinuar?"):
            return

        overlay = StartupOverlay(self, "RESTAURANDO GRAFICOS",
                                 "Leyendo copias de seguridad...")
        self.startup_overlay = overlay

        def worker():
            try:
                steps = []
                for pid, pstate in todo.items():
                    for record in pstate.get("files") or []:
                        steps.append((
                            f"Restaurar {Path(record.get('path', '')).name}",
                            lambda r=record: self._restore_graphics_file(r)))
                    if pstate.get("registry"):
                        steps.append((
                            f"Registro de {self._graphics_profile(pid)['name']}",
                            lambda records=pstate.get("registry"): self._restore_graphics_registry(records)))
                overlay.set_total(max(1, len(steps)))
                cancelled = False
                for index, (label, func) in enumerate(steps, 1):
                    if overlay.cancelled:
                        cancelled = True
                        break
                    overlay.set_stage(label)
                    func()
                    overlay.push(index, label, label)

                state2 = self._load_graphics_state()
                if not cancelled:
                    for pid in todo:
                        state2.pop(pid, None)
                self._save_graphics_state(state2)
                if cancelled:
                    overlay.finish(False, "Cancelado: algunos cambios no se restauraron")
                else:
                    self.log("Potato Graphics quitado y archivos restaurados.")
                    overlay.finish(True, "Potato Graphics quitado correctamente")
            except Exception as exc:  # noqa: BLE001
                self.log(f"ERROR al restaurar graficos: {exc}")
                overlay.finish(False, f"Error: {exc}")

        self.start_task("Restaurar graficos", worker,
                        on_done=self._refresh_graphics_ui)

    def _build_tab_diagnostico(self):
        tab = self._new_tab("  Diagnostico  ")

        ttk.Label(tab, text="Analisis de cuellos de botella de tu PC (solo lectura, no cambia nada).",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        ttk.Button(tab, text="ANALIZAR MI PC", style="Accent.TButton",
                   command=self.run_diagnostics).pack(fill="x", pady=6)

        box = tk.Frame(tab, bg=PANEL2, highlightbackground=BORDER, highlightthickness=1)
        box.pack(fill="both", expand=True, pady=(8, 0))
        self.diag_text = tk.Text(box, bg=PANEL2, fg=FG, relief="flat", bd=0,
                                 font=("Consolas", 9), wrap="word", padx=12, pady=10)
        self.diag_text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(box, orient="vertical", command=self.diag_text.yview)
        scroll.pack(side="right", fill="y")
        self.diag_text.configure(yscrollcommand=scroll.set, state="disabled")
        self._set_diag_text(
            "Pulsa «ANALIZAR MI PC» para detectar el plan de energia, la RAM,\n"
            "el disco donde estan Windows/Fortnite, la pantalla y los procesos.\n")

    def _set_diag_text(self, text):
        def apply():
            self.diag_text.configure(state="normal")
            self.diag_text.delete("1.0", "end")
            self.diag_text.insert("end", text)
            self.diag_text.configure(state="disabled")
        self.root.after(0, apply)

    def run_diagnostics(self):
        script = r'''
$ErrorActionPreference = "SilentlyContinue"
function Line($t) { "`n=== $t ===" }
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$gpu = Get-CimInstance Win32_VideoController | Select-Object -First 1
Line "SISTEMA"
"Windows: $($os.Caption) $($os.Version) build $($os.BuildNumber)"
"Equipo: $($cs.Manufacturer) $($cs.Model)"
"CPU: $($cpu.Name) ($($cpu.NumberOfCores)C/$($cpu.NumberOfLogicalProcessors)T)"
"GPU: $($gpu.Name) - driver $($gpu.DriverVersion)"
"RAM total: {0:N1} GB" -f ($cs.TotalPhysicalMemory / 1GB)
Line "PLAN DE ENERGIA"
powercfg /getactivescheme
Line "PANTALLA"
"Resolucion: $($gpu.CurrentHorizontalResolution)x$($gpu.CurrentVerticalResolution) @ $($gpu.CurrentRefreshRate) Hz (max $($gpu.MaxRefreshRate) Hz)"
Line "RAM (modulos)"
Get-CimInstance Win32_PhysicalMemory | ForEach-Object {
  "{0}: {1} GB - {2} MHz (config {3}) - {4}" -f $_.DeviceLocator, [math]::Round($_.Capacity/1GB), $_.Speed, $_.ConfiguredClockSpeed, $_.PartNumber
}
Line "DISCO DEL SISTEMA (C:)"
$p = Get-Partition -DriveLetter C
$d = Get-PhysicalDisk -DeviceNumber $p.DiskNumber
$dtype = $d.MediaType
if (-not $dtype) { $dtype = "Desconocido" }
"C: esta en: $($d.FriendlyName) - tipo: $dtype"
Line "GRAFICOS / JUEGO"
"Game Mode: $((Get-ItemProperty 'HKCU:\Software\Microsoft\GameBar').AutoGameModeEnabled)"
"HAGS (GPU scheduling): $((Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\GraphicsDrivers').HwSchMode)"
"GameDVR: $((Get-ItemProperty 'HKCU:\System\GameConfigStore').GameDVR_Enabled)"
"Win32PrioritySeparation: $((Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\PriorityControl').Win32PrioritySeparation)"
Line "FORTNITE"
$fi = "$env:LOCALAPPDATA\FortniteGame\Saved\Config\WindowsClient\GameUserSettings.ini"
if (Test-Path $fi) {
  Select-String -Path $fi -Pattern 'FrameRateLimit=|bUseVSync=|PreferredFullscreenMode=|FrontendFrameRateLimit=|b120FpsMode=' | ForEach-Object { $_.Line }
} else { "No se encontro GameUserSettings.ini" }
Line "PROCESOS"
$procs = Get-Process
"Total de procesos: $($procs.Count)"
$procs | Sort-Object WorkingSet64 -Descending | Select-Object -First 12 Name, @{n="RAM_MB";e={[math]::Round($_.WorkingSet64/1MB)}} | Format-Table -AutoSize | Out-String
Line "AVISOS"
$warn = @()
$mem = Get-CimInstance Win32_PhysicalMemory
if (($mem | Measure-Object).Count -gt 1) {
  $sizes = $mem | ForEach-Object { [math]::Round($_.Capacity/1GB) } | Sort-Object
  if (($sizes | Select-Object -Unique).Count -gt 1) { $warn += "RAM desparejada ($($sizes -join ' + ') GB): parte corre en single-channel (modo Flex)." }
  $speeds = $mem | ForEach-Object { $_.ConfiguredClockSpeed } | Select-Object -Unique
  if (($speeds | Measure-Object).Count -gt 1) { $warn += "Modulos de RAM a distinta velocidad efectiva: $($speeds -join ', ') MHz." }
}
if ($dtype -ne "SSD") { $warn += "Windows/Fortnite estan en un disco $dtype. Mover el juego a un SSD reduce tirones y frame time." }
if ($warn.Count -eq 0) { "Sin avisos criticos." } else { $warn | ForEach-Object { "- $_" } }
'''

        def worker():
            self.log("### Diagnostico ###")
            result = self._capture_ps(script)
            self._set_diag_text(result)
            self.log("Diagnostico completado. Revisa la pestana Diagnostico.")

        self.start_task("Diagnostico", worker)

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


    # ------------------------------------------------------ inicio / startup
    STARTUP_RUN_KEYS = [
        (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run", "Usuario (HKCU)"),
        (r"HKLM\Software\Microsoft\Windows\CurrentVersion\Run", "Sistema (HKLM)"),
        (r"HKCU\Software\Microsoft\Windows\CurrentVersion\RunOnce", "Usuario RunOnce"),
        (r"HKLM\Software\Microsoft\Windows\CurrentVersion\RunOnce", "Sistema RunOnce"),
    ]
    STARTUP_BLOCK_STORE = r"HKCU\Software\PylandTweaks\BlockedStartup"
    STARTUP_APPROVED_KEYS = [
        (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run", "HKCU Run"),
        (r"HKLM\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run", "HKLM Run"),
    ]

    EXTRA_SERVICES = [
        ("SysMain", "SysMain (Superfetch)", "Precarga apps en RAM; en PCs con poco RAM o HDD lento puede ayudar desactivarlo. En SSD suele ser mejor dejarlo."),
        ("WSearch", "Windows Search", "Indexa archivos para busquedas rapidas; consume CPU/disco en segundo plano. Desactivalo si no usas la busqueda a menudo."),
        ("Spooler", "Cola de impresion (Spooler)", "Necesario solo si usas impresora. Si no imprimes, puedes desactivarlo para liberar recursos."),
        ("Fax", "Servicio de Fax", "Solo para envio/recepcion de fax. Casi nadie lo usa; seguro desactivar."),
        ("MapsBroker", "Administrador de mapas descargados", "Descarga y actualiza mapas sin conexion en segundo plano. Desactivalo si no usas Mapas."),
        ("RetailDemo", "Servicio de demostracion comercial", "Modo demo de tiendas. Innecesario en PCs personales; seguro desactivar."),
        ("RemoteRegistry", "Registro remoto", "Permite modificar el registro de forma remota. Riesgo innecesario en casa; recomendable desactivar."),
        ("lfsvc", "Servicio de geolocalizacion", "Ubicacion para apps. Desactivalo si no necesitas GPS/ubicacion en este equipo."),
        ("DiagTrack", "Experiencias de usuario y telemetria", "Envia datos de diagnostico/telemetria. Desactivarlo reduce actividad en segundo plano."),
        ("PcaSvc", "Servicio Asistente para compatibilidad de programas", "Monitoriza compatibilidad de apps; puede consumir recursos. Desactivalo si no lo necesitas."),
    ]

    def _ps(self, script):
        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW,
            )
            return result.stdout.decode("mbcs", errors="replace").strip()
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: {exc}"

    def _startup_run_list(self):
        script = r"""
$ErrorActionPreference="SilentlyContinue"
$keys = @(
  "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
  "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run",
  "HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce",
  "HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce"
)
foreach ($k in $keys) {
  if (Test-Path $k) {
    $p = Get-ItemProperty -Path $k
    $p.PSObject.Properties | Where-Object { $_.Name -notin @('PSPath','PSParentPath','PSChildName','PSDrive','PSProvider') } | ForEach-Object {
      $scope = if ($k -like 'HKCU:*') { 'HKCU' } else { 'HKLM' }
      $kind = if ($k -like '*RunOnce') { 'RunOnce' } else { 'Run' }
      "$scope|$kind|$($_.Name)|$($_.Value)"
    }
  }
}
"""
        out = self._ps(script)
        items = []
        if not out or out.startswith("ERROR:"):
            return items
        for line in out.splitlines():
            parts = line.split("|", 3)
            if len(parts) == 4:
                items.append({"type": "run", "scope": parts[0], "kind": parts[1],
                              "name": parts[2], "cmd": parts[3]})
        return items

    def _startup_folders(self):
        appdata = os.environ.get("APPDATA") or ""
        programdata = os.environ.get("PROGRAMDATA") or r"C:\ProgramData"
        return [
            ("HKCU", Path(appdata) / "Microsoft/Windows/Start Menu/Programs/Startup"),
            ("HKLM", Path(programdata) / "Microsoft/Windows/Start Menu/Programs/Startup"),
        ]

    def _startup_backup_root(self):
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or ""
        return Path(base) / "PylandTweaks" / "StartupBackup"

    def _startup_folder_backup_path(self, scope, name):
        return self._startup_backup_root() / scope / name

    def _startup_folder_list(self):
        items = []
        for scope, folder in self._startup_folders():
            if not folder.exists():
                continue
            try:
                files = sorted(p for p in folder.iterdir()
                               if p.is_file() and p.name.lower() != "desktop.ini")
            except OSError:
                continue
            for path in files:
                items.append({"type": "folder", "scope": scope, "kind": "Carpeta Inicio",
                              "name": path.name, "cmd": str(path)})
        return items

    def _startup_task_list(self):
        third_party = self._startup_logon_tasks()
        existing = getattr(self, "_existing_task_paths", None)
        tasks = []
        seen = set()
        for task in STARTUP_LOGON_TASKS:
            if existing is not None and task.lower() not in existing:
                continue
            if task.lower() not in seen:
                seen.add(task.lower())
                tasks.append(task)
        for task in third_party:
            if task.lower() not in seen:
                seen.add(task.lower())
                tasks.append(task)
        return [{"type": "task", "scope": "Sistema", "kind": "Tarea de inicio",
                 "name": task.rsplit("\\", 1)[-1], "cmd": task}
                for task in sorted(tasks)]

    def _startup_list(self):
        items = self._startup_run_list()
        items += self._startup_folder_list()
        items += self._startup_task_list()
        return items

    def _blocked_startup_list(self):
        script = r"""
$ErrorActionPreference="SilentlyContinue"
$k="HKCU:\Software\PylandTweaks\BlockedStartup"
if (Test-Path $k) {
  $p=Get-ItemProperty -Path $k
  $p.PSObject.Properties | Where-Object { $_.Name -notin @('PSPath','PSParentPath','PSChildName','PSDrive','PSProvider') } | ForEach-Object {
    "$($_.Name)|$($_.Value)"
  }
}
"""
        out = self._ps(script)
        items = []
        if out and not out.startswith("ERROR:"):
            for line in out.splitlines():
                if "|" in line:
                    name, val = line.split("|", 1)
                    items.append({"type": "run", "scope": "HKCU", "kind": "Run",
                                  "name": name, "cmd": val})
        man = self._load_startup_cfg().get("manifest") or {}
        for mv in man.get("moved", []) or []:
            src = str(mv.get("src", ""))
            if not src:
                continue
            items.append({"type": "folder", "scope": str(mv.get("scope", "HKCU")),
                          "kind": "Carpeta Inicio", "name": Path(src).name,
                          "cmd": src, "backup": str(mv.get("dst", ""))})
        for task in man.get("tasks", []) or []:
            items.append({"type": "task", "scope": "Sistema", "kind": "Tarea de inicio",
                          "name": str(task).rsplit("\\", 1)[-1], "cmd": str(task)})
        return items

    def _startup_label(self, it, blocked=False):
        typ = it.get("type", "run")
        if typ == "folder":
            tag = "Carpeta Inicio"
        elif typ == "task":
            tag = "Tarea de inicio"
        else:
            tag = f"{it.get('scope')} {it.get('kind')}"
        prefix = "BLOQUEADA " if blocked else ""
        return f"[{prefix}{tag}] {it.get('name')}  ->  {it.get('cmd')}"

    def _refresh_startup_lists(self):
        self.startup_listbox.delete(0, "end")
        self.startup_items = self._startup_list()
        if not self.startup_items:
            self.startup_listbox.insert(
                "end", "  (No se encontraron apps de inicio, accesos directos ni tareas)")
        for it in self.startup_items:
            self.startup_listbox.insert("end", self._startup_label(it))

        self.blocked_listbox.delete(0, "end")
        self.blocked_items = self._blocked_startup_list()
        if not self.blocked_items:
            self.blocked_listbox.insert("end", "  (No hay elementos bloqueados)")
        for it in self.blocked_items:
            self.blocked_listbox.insert("end", self._startup_label(it, blocked=True))
        self._update_startup_summary()
        self.log("Listas de inicio actualizadas.")

    def _selected_startup_item(self):
        sel = self.startup_listbox.curselection()
        if not sel or not getattr(self, "startup_items", None):
            return None
        idx = sel[0]
        if idx < 0 or idx >= len(self.startup_items):
            return None
        return self.startup_items[idx]

    def _selected_blocked_item(self):
        sel = self.blocked_listbox.curselection()
        if not sel or not getattr(self, "blocked_items", None):
            return None
        idx = sel[0]
        if idx < 0 or idx >= len(self.blocked_items):
            return None
        return self.blocked_items[idx]

    def _run_key_path(self, scope, kind):
        root = "HKCU" if scope == "HKCU" else "HKLM"
        return rf"{root}\Software\Microsoft\Windows\CurrentVersion\{kind}"

    def _approved_key_path(self, scope):
        return rf"{scope}\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"

    def _approved_folder_path(self, scope):
        return rf"{scope}\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\StartupFolder"

    # ------------------------------------------------ config optimizador inicio
    def _startup_cfg_path(self):
        base = Path(os.environ.get("APPDATA") or Path.home())
        return base / "PylandTweaks" / "startup_optimizer.json"

    def _load_startup_cfg(self):
        cfg = {"exclusions": list(DEFAULT_STARTUP_EXCLUSIONS), "manifest": {}}
        try:
            path = self._startup_cfg_path()
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    exclusions = data.get("exclusions")
                    if isinstance(exclusions, list):
                        cfg["exclusions"] = [str(x).strip().lower() for x in exclusions if str(x).strip()]
                    manifest = data.get("manifest")
                    if isinstance(manifest, dict):
                        cfg["manifest"] = manifest
        except Exception as exc:  # noqa: BLE001
            self.log(f"No se pudo leer la configuracion de inicio: {exc}")
        return cfg

    def _save_startup_cfg(self, cfg):
        try:
            path = self._startup_cfg_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            self.log(f"No se pudo guardar la configuracion de inicio: {exc}")

    def _startup_exclusions(self):
        cfg = self._load_startup_cfg()
        return [str(x).strip().lower() for x in cfg.get("exclusions", []) if str(x).strip()]

    def _is_excluded(self, exclusions, *texts):
        blob = " ".join(str(t or "") for t in texts).lower()
        return any(tok and tok in blob for tok in exclusions)

    def _startup_logon_tasks(self):
        script = r"""
$ErrorActionPreference="SilentlyContinue"
Get-ScheduledTask | ForEach-Object {
  $logon = 0
  if ($_.Triggers | Where-Object { $_.CimClass.CimClassName -match 'Logon|Boot' }) { $logon = 1 }
  "$($_.TaskPath)|$($_.TaskName)|$($_.State)|$logon"
}
"""
        out = self._ps(script)
        self._existing_task_paths = None
        tasks = []
        if not out or out.startswith("ERROR:"):
            return tasks
        existing = set()
        for line in out.splitlines():
            parts = line.split("|")
            if len(parts) != 4:
                continue
            path, name, state, logon = parts
            if not name:
                continue
            full = path + name if path.endswith("\\") else path + "\\" + name
            existing.add(full.lower())
            if (logon == "1" and state.lower() != "disabled"
                    and not full.lower().startswith("\\microsoft\\")):
                tasks.append(full)
        self._existing_task_paths = existing
        return tasks

    def _build_startup_optimize_plan(self, exclusions):
        plan = []
        manifest = {"blocked": [], "moved": [], "services": [], "tasks": [], "tweaks": True}

        def add(label, cmd):
            plan.append({"label": label, "cmd": cmd})

        for key, value, typ, data in STARTUP_BOOT_REGS:
            add("Ajustando el arranque de Windows", reg_add(key, value, typ, data))

        for item in self._startup_run_list():
            if self._is_excluded(exclusions, item.get("name"), item.get("cmd")):
                continue
            for cmd in self.cmds_block_startup_item(item):
                add(f"Bloqueando inicio: {item.get('name')}", cmd)
            manifest["blocked"].append(dict(item))

        for scope, folder in self._startup_folders():
            if not folder.exists():
                continue
            try:
                files = [p for p in folder.iterdir()
                         if p.is_file() and p.name.lower() != "desktop.ini"]
            except OSError:
                continue
            if not files:
                continue
            dst_dir = self._startup_backup_root() / scope
            add("Preparando copia de los accesos directos",
                f'if not exist "{dst_dir}" mkdir "{dst_dir}"')
            for src in files:
                if self._is_excluded(exclusions, src.name):
                    continue
                dst = self._startup_folder_backup_path(scope, src.name)
                add(f"Moviendo acceso directo: {src.name}", f'move /Y "{src}" "{dst}"')
                manifest["moved"].append({"src": str(src), "dst": str(dst), "scope": scope})
                add(f"Desactivando acceso directo: {src.name}",
                    f'reg add "{self._approved_folder_path(scope)}" /v "{src.name}" '
                    f'/t REG_BINARY /d 030000000000000000000000 /f')

        disabled_tasks = []
        seen_tasks = set()
        third_party = self._startup_logon_tasks()
        existing = getattr(self, "_existing_task_paths", None)
        for task in STARTUP_LOGON_TASKS:
            if existing is not None and task.lower() not in existing:
                continue
            if self._is_excluded(exclusions, task) or task.lower() in seen_tasks:
                continue
            seen_tasks.add(task.lower())
            disabled_tasks.append(task)
            add(f"Desactivando tarea: {task.rsplit(chr(92), 1)[-1]}",
                f'schtasks /Change /TN "{task}" /Disable')
        for task in third_party:
            if self._is_excluded(exclusions, task) or task.lower() in seen_tasks:
                continue
            seen_tasks.add(task.lower())
            disabled_tasks.append(task)
            add(f"Desactivando tarea de inicio: {task.rsplit(chr(92), 1)[-1]}",
                f'schtasks /Change /TN "{task}" /Disable')
        manifest["tasks"] = disabled_tasks

        disabled_services = []
        for svc in STARTUP_BOOT_SERVICES:
            if self._is_excluded(exclusions, svc):
                continue
            disabled_services.append(svc)
            add(f"Deteniendo servicio: {svc}", f'sc stop "{svc}"')
            add(f"Deshabilitando servicio: {svc}", f'sc config "{svc}" start= disabled')
        manifest["services"] = disabled_services

        return plan, manifest

    def _build_startup_restore_plan(self, manifest):
        plan = []

        def add(label, cmd):
            plan.append({"label": label, "cmd": cmd})

        for item in manifest.get("blocked", []) or []:
            name = str(item.get("name", ""))
            if not name:
                continue
            scope = str(item.get("scope", "HKCU"))
            kind = str(item.get("kind", "Run"))
            cmd_val = str(item.get("cmd", "")).replace('"', "")
            add(f"Restaurando app de inicio: {name}",
                f'reg add "{self._run_key_path(scope, kind)}" /v "{name}" '
                f'/t REG_SZ /d "{cmd_val}" /f')
            add(f"Quitando bloqueo: {name}", reg_del(self.STARTUP_BLOCK_STORE, name))
            if kind == "Run":
                add(f"Habilitando app: {name}",
                    f'reg add "{self._approved_key_path(scope)}" /v "{name}" '
                    f'/t REG_BINARY /d 020000000000000000000000 /f')

        for mv in manifest.get("moved", []) or []:
            src = str(mv.get("src", ""))
            dst = str(mv.get("dst", ""))
            if not src or not dst:
                continue
            scope = str(mv.get("scope") or ("HKLM" if "ProgramData" in dst else "HKCU"))
            add(f"Restaurando acceso directo: {Path(src).name}",
                f'if not exist "{Path(src).parent}" mkdir "{Path(src).parent}"')
            add(f"Devolviendo acceso directo: {Path(src).name}", f'move /Y "{dst}" "{src}"')
            add(f"Habilitando acceso directo: {Path(src).name}",
                f'reg add "{self._approved_folder_path(scope)}" /v "{Path(src).name}" '
                f'/t REG_BINARY /d 020000000000000000000000 /f')

        for svc in manifest.get("services", []) or []:
            add(f"Restaurando servicio: {svc}", f'sc config "{svc}" start= demand')

        for task in manifest.get("tasks", []) or []:
            add(f"Reactivando tarea: {task.rsplit(chr(92), 1)[-1]}",
                f'schtasks /Change /TN "{task}" /Enable')

        if manifest.get("tweaks", True):
            for key, value, typ, data in STARTUP_BOOT_REGS_REVERT:
                add("Restaurando ajuste de arranque", reg_add(key, value, typ, data))
            for key, value in STARTUP_BOOT_DELETE:
                add("Quitando ajuste de arranque", reg_del(key, value))

        return plan

    def _merge_startup_manifest(self, new_manifest):
        cfg = self._load_startup_cfg()
        man = cfg.get("manifest") or {}

        blocked = man.get("blocked", []) or []
        seen = {(b.get("scope"), b.get("kind"), b.get("name")) for b in blocked}
        for b in new_manifest.get("blocked", []) or []:
            key = (b.get("scope"), b.get("kind"), b.get("name"))
            if key not in seen:
                blocked.append(b)
                seen.add(key)
        man["blocked"] = blocked

        moved = man.get("moved", []) or []
        seen = {(m.get("src"), m.get("dst")) for m in moved}
        for m in new_manifest.get("moved", []) or []:
            key = (m.get("src"), m.get("dst"))
            if key not in seen:
                moved.append(m)
                seen.add(key)
        man["moved"] = moved

        man["services"] = list(dict.fromkeys((man.get("services") or [])
                                             + (new_manifest.get("services") or [])))
        man["tasks"] = list(dict.fromkeys((man.get("tasks") or [])
                                          + (new_manifest.get("tasks") or [])))
        man["tweaks"] = True
        cfg["manifest"] = man
        self._save_startup_cfg(cfg)

    def _has_startup_backup(self):
        man = self._load_startup_cfg().get("manifest") or {}
        return bool(man.get("tweaks")
                    or any(man.get(k) for k in ("blocked", "moved", "services", "tasks")))

    def _update_startup_summary(self):
        lbl = getattr(self, "startup_summary", None)
        if lbl is None:
            return
        try:
            exclusions = self._startup_exclusions()
            items = getattr(self, "startup_items", []) or []
            n_exc = sum(1 for it in items
                        if self._is_excluded(exclusions, it.get("name"), it.get("cmd")))
            n_svc = sum(1 for s in STARTUP_BOOT_SERVICES
                        if not self._is_excluded(exclusions, s))
            n_tasks = sum(1 for t in STARTUP_LOGON_TASKS
                          if not self._is_excluded(exclusions, t))
            lbl.configure(text=f"{len(items)} elementos  |  {n_exc} excluidos  |  "
                               f"{n_svc} servicios  |  {n_tasks} tareas")
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------- acciones optimizador inicio
    def do_optimize_startup(self):
        if self.busy:
            messagebox.showinfo("En curso", "Espera a que termine la tarea actual.")
            return
        exclusions = self._startup_exclusions()
        if not messagebox.askyesno(
                "Optimizador de inicio",
                "Se va a optimizar el arranque de Windows:\n\n"
                "- Bloquear apps de inicio (seguiran abriendose al ejecutarlas)\n"
                "- Mover accesos directos de la carpeta Inicio a una copia de seguridad\n"
                "- Desactivar tareas de logon y servicios innecesarios\n"
                "- Aplicar ajustes de arranque rapido\n\n"
                f"Apps/palabras excluidas: {len(exclusions)}\n\n"
                "Puedes revertir todo con 'Restaurar inicio'. Continuar?"):
            return
        self._run_startup_overlay("optimize", exclusions)

    def do_restore_startup(self):
        if self.busy:
            messagebox.showinfo("En curso", "Espera a que termine la tarea actual.")
            return
        if not self._has_startup_backup():
            messagebox.showinfo("Optimizador de inicio",
                                "No hay cambios guardados por el optimizador de inicio.")
            return
        if not messagebox.askyesno(
                "Restaurar inicio",
                "Se restauraran las apps de inicio, accesos directos, tareas y "
                "servicios que cambio el optimizador.\n\nContinuar?"):
            return
        self._run_startup_overlay("restore")

    def _run_startup_overlay(self, mode, exclusions=None):
        title = "OPTIMIZANDO INICIO" if mode == "optimize" else "RESTAURANDO INICIO"
        subtitle = ("Analizando apps, tareas y servicios..."
                    if mode == "optimize" else "Leyendo la copia de seguridad...")
        overlay = StartupOverlay(self, title, subtitle)
        self.startup_overlay = overlay

        def worker():
            try:
                if mode == "optimize":
                    plan, manifest = self._build_startup_optimize_plan(exclusions or [])
                else:
                    cfg = self._load_startup_cfg()
                    manifest = None
                    plan = self._build_startup_restore_plan(cfg.get("manifest") or {})
                overlay.set_total(len(plan))
                if not plan:
                    overlay.finish(True, "Nada que hacer")
                    return
                cancelled = False
                for index, step in enumerate(plan, 1):
                    if overlay.cancelled:
                        cancelled = True
                        break
                    if index % 4 == 1:
                        overlay.set_stage(step["label"])
                    self.exec_cmd(step["cmd"])
                    overlay.push(index, step["label"], step["cmd"])
                if cancelled:
                    overlay.finish(False, "Cancelado: algunos cambios quedaron aplicados")
                    if mode == "optimize" and manifest is not None:
                        self._merge_startup_manifest(manifest)
                    return
                if mode == "optimize":
                    self._merge_startup_manifest(manifest)
                    overlay.finish(True, f"Listo: {len(plan)} acciones aplicadas")
                else:
                    cfg = self._load_startup_cfg()
                    cfg["manifest"] = {}
                    self._save_startup_cfg(cfg)
                    overlay.finish(True, "Inicio restaurado correctamente")
            except Exception as exc:  # noqa: BLE001
                overlay.finish(False, f"Error: {exc}")

        self.start_task(title.capitalize(), worker, on_done=self._refresh_startup_lists)

    def open_startup_exclusions(self):
        if self.busy:
            messagebox.showinfo("En curso", "Espera a que termine la tarea actual.")
            return
        if not getattr(self, "startup_items", None):
            self.startup_items = self._startup_list()

        cfg = self._load_startup_cfg()
        tokens = list(dict.fromkeys(str(x).strip().lower()
                                    for x in cfg.get("exclusions", []) if str(x).strip()))
        token_set = set(tokens)

        win = tk.Toplevel(self.root)
        win.title("Exclusiones del optimizador de inicio")
        win.configure(bg=BG)
        win.geometry("700x620")
        win.transient(self.root)
        win.grab_set()

        head = tk.Frame(win, bg=BG)
        head.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(head, text="EXCLUSIONES", bg=BG, fg=ACCENT2,
                 font=(FONT_BOLD, 13)).pack(anchor="w")
        tk.Label(head, text="Marca las apps que NO quieres bloquear y agrega palabras clave "
                            "(servicios, tareas o procesos). Coincide por nombre o comando.",
                 bg=BG, fg=MUTED, font=(FONT, 9), justify="left",
                 wraplength=650).pack(anchor="w", pady=(3, 0))

        items_box = tk.Frame(win, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        items_box.pack(fill="both", expand=True, padx=16, pady=(8, 6))
        items_canvas = tk.Canvas(items_box, bg=PANEL, highlightthickness=0)
        items_scroll = ttk.Scrollbar(items_box, orient="vertical",
                                     command=items_canvas.yview)
        items_inner = tk.Frame(items_canvas, bg=PANEL)
        items_inner.bind("<Configure>",
                         lambda e: items_canvas.configure(scrollregion=items_canvas.bbox("all")))
        items_canvas.create_window((0, 0), window=items_inner, anchor="nw")
        items_canvas.configure(yscrollcommand=items_scroll.set)
        items_canvas.pack(side="left", fill="both", expand=True)
        items_scroll.pack(side="right", fill="y")

        if not self.startup_items:
            tk.Label(items_inner, text="No se detectaron apps en las claves Run/RunOnce.",
                     bg=PANEL, fg=MUTED, font=(FONT, 9)).pack(anchor="w", padx=10, pady=10)

        item_vars = []
        for it in self.startup_items:
            name = str(it.get("name", ""))
            token = name.strip().lower()
            var = tk.BooleanVar(master=win, value=token in token_set)
            row = tk.Frame(items_inner, bg=PANEL)
            row.pack(fill="x", padx=8, pady=1)
            tag = {"folder": "Carpeta Inicio", "task": "Tarea de inicio"}.get(
                it.get("type", "run"), f"{it.get('scope')} {it.get('kind')}")
            chk = tk.Checkbutton(row, text=f"{name}   [{tag}]",
                                 variable=var, bg=PANEL, fg=FG, activebackground=PANEL,
                                 activeforeground=FG, selectcolor=PANEL3,
                                 font=(FONT, 9), anchor="w", bd=0, highlightthickness=0)
            chk.pack(side="left", fill="x", expand=True)
            item_vars.append((token, var))

        custom_box = tk.Frame(win, bg=BG)
        custom_box.pack(fill="x", padx=16, pady=(4, 0))
        tk.Label(custom_box, text="PALABRAS CLAVE EXCLUIDAS (servicios, tareas, apps)",
                 bg=BG, fg=MUTED, font=(FONT_BOLD, 8)).pack(anchor="w", pady=(0, 4))
        list_row = tk.Frame(custom_box, bg=BG)
        list_row.pack(fill="x")
        token_list = tk.Listbox(list_row, height=5, bg=PANEL2, fg=FG,
                                selectbackground=ACCENT, selectforeground="#ffffff",
                                relief="flat", bd=0, font=("Consolas", 9),
                                activestyle="none", highlightthickness=0)
        token_list.pack(side="left", fill="x", expand=True)
        token_scroll = ttk.Scrollbar(list_row, orient="vertical",
                                     command=token_list.yview)
        token_scroll.pack(side="right", fill="y")
        token_list.configure(yscrollcommand=token_scroll.set)

        def refresh_tokens():
            token_list.delete(0, "end")
            for tok in sorted(token_set):
                token_list.insert("end", tok)

        def on_toggle():
            for token, var in item_vars:
                if var.get():
                    token_set.add(token)
                else:
                    token_set.discard(token)
            refresh_tokens()

        entry_row = tk.Frame(custom_box, bg=BG)
        entry_row.pack(fill="x", pady=(6, 0))
        entry = tk.Entry(entry_row, bg=PANEL2, fg=FG, insertbackground=FG,
                         relief="flat", bd=0, font=(FONT, 9),
                         highlightthickness=1, highlightbackground=BORDER,
                         highlightcolor=ACCENT)
        entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))

        def add_token(_event=None):
            tok = entry.get().strip().lower()
            if tok:
                token_set.add(tok)
                entry.delete(0, "end")
                refresh_tokens()

        def remove_token():
            sel = token_list.curselection()
            if sel:
                token_set.discard(token_list.get(sel[0]))
                refresh_tokens()

        ttk.Button(entry_row, text="Agregar", style="Card.TButton",
                   command=add_token, cursor="hand2").pack(side="left")
        ttk.Button(entry_row, text="Quitar", style="Danger.TButton",
                   command=remove_token, cursor="hand2").pack(side="left", padx=6)
        entry.bind("<Return>", add_token)

        for token, var in item_vars:
            var.trace_add("write", lambda *_a: on_toggle())
        refresh_tokens()

        bottom = tk.Frame(win, bg=BG)
        bottom.pack(fill="x", padx=16, pady=12)

        def reset_defaults():
            token_set.clear()
            token_set.update(DEFAULT_STARTUP_EXCLUSIONS)
            for token, var in item_vars:
                var.set(False)
            refresh_tokens()

        def save():
            cfg = self._load_startup_cfg()
            cfg["exclusions"] = sorted(t for t in token_set if t)
            self._save_startup_cfg(cfg)
            self._update_startup_summary()
            self.log(f"Exclusiones de inicio guardadas: {len(cfg['exclusions'])}")
            win.destroy()

        ttk.Button(bottom, text="Restaurar predeterminadas", style="Card.TButton",
                   command=reset_defaults, cursor="hand2").pack(side="left")
        ttk.Button(bottom, text="Cancelar", style="Card.TButton",
                   command=win.destroy, cursor="hand2").pack(side="right")
        ttk.Button(bottom, text="Guardar exclusiones", style="Accent.TButton",
                   command=save, cursor="hand2").pack(side="right", padx=8)

    def cmds_block_startup_item(self, item):
        typ = item.get("type", "run")
        if typ == "folder":
            scope = item.get("scope", "HKCU")
            src = Path(item.get("cmd", ""))
            dst = self._startup_folder_backup_path(scope, src.name)
            return [
                f'if not exist "{dst.parent}" mkdir "{dst.parent}"',
                f'move /Y "{src}" "{dst}"',
                f'reg add "{self._approved_folder_path(scope)}" /v "{src.name}" '
                f'/t REG_BINARY /d 030000000000000000000000 /f',
            ]
        if typ == "task":
            return [f'schtasks /Change /TN "{item.get("cmd", "")}" /Disable']
        key = self._run_key_path(item["scope"], item["kind"])
        cmd_val = item["cmd"].replace('"', "")
        cmds = [
            f'reg add "{self.STARTUP_BLOCK_STORE}" /v "{item["name"]}" /t REG_SZ /d "{cmd_val}" /f',
            reg_del(key, item["name"]),
        ]
        if item["kind"] == "Run":
            ak = self._approved_key_path(item["scope"])
            cmds.append(f'reg add "{ak}" /v "{item["name"]}" /t REG_BINARY /d 030000000000000000000000 /f')
        return cmds

    def _after_block_startup(self, item):
        typ = item.get("type", "run")
        if typ == "folder":
            scope = item.get("scope", "HKCU")
            src = str(item.get("cmd", ""))
            dst = str(self._startup_folder_backup_path(scope, Path(src).name))
            self._merge_startup_manifest({"blocked": [], "moved": [
                {"src": src, "dst": dst, "scope": scope}], "services": [], "tasks": []})
        elif typ == "task":
            self._merge_startup_manifest({"blocked": [], "moved": [], "services": [],
                                          "tasks": [str(item.get("cmd", ""))]})
        else:
            self._merge_startup_manifest({"blocked": [dict(item)], "moved": [],
                                          "services": [], "tasks": []})
        self._refresh_startup_lists()

    def _remove_manifest_entry(self, kind, item):
        cfg = self._load_startup_cfg()
        man = cfg.get("manifest") or {}
        if kind == "moved":
            src = str(item.get("cmd", ""))
            man["moved"] = [m for m in man.get("moved", []) or []
                            if str(m.get("src", "")) != src]
        elif kind == "tasks":
            task = str(item.get("cmd", "")).lower()
            man["tasks"] = [t for t in man.get("tasks", []) or []
                            if str(t).lower() != task]
        elif kind == "blocked":
            name = str(item.get("name", ""))
            man["blocked"] = [b for b in man.get("blocked", []) or []
                              if str(b.get("name", "")) != name]
        cfg["manifest"] = man
        self._save_startup_cfg(cfg)

    def do_block_selected_startup(self):
        item = self._selected_startup_item()
        if not item:
            messagebox.showinfo("Inicio", "Selecciona un elemento de la lista de inicio.")
            return
        typ = item.get("type", "run")
        tipo = {"folder": "el acceso directo", "task": "la tarea programada"}.get(
            typ, "la app")
        if not messagebox.askyesno(
                "Bloquear inicio",
                f"Se bloqueara {tipo} '{item['name']}'.\n\n"
                "Seguiras pudiendo abrirla manualmente cuando la necesites.\n"
                "Usa 'Reaplicar bloqueos' si vuelve a agregarse al iniciar.\n\nContinuar?"):
            return
        title = {"folder": "Bloquear acceso directo",
                 "task": "Bloquear tarea de inicio"}.get(typ, "Bloquear app de inicio")
        self.run_steps(title,
                       [("Bloqueando inicio", self.cmds_block_startup_item(item))],
                       on_done=lambda: self._after_block_startup(item))

    def _after_unblock_startup(self, item, manifest_key):
        self._remove_manifest_entry(manifest_key, item)
        self._refresh_startup_lists()

    def do_unblock_selected(self):
        item = self._selected_blocked_item()
        if not item:
            messagebox.showinfo("Inicio", "Selecciona un elemento bloqueado.")
            return
        typ = item.get("type", "run")
        if typ == "folder":
            scope = item.get("scope", "HKCU")
            src = str(item.get("cmd", ""))
            dst = str(item.get("backup", ""))
            if not dst:
                for mv in self._load_startup_cfg().get("manifest", {}).get("moved", []) or []:
                    if str(mv.get("src", "")) == src:
                        dst = str(mv.get("dst", ""))
                        break
            if not dst:
                messagebox.showerror("Inicio", "No se encontro la copia de seguridad del acceso directo.")
                return
            cmds = [
                f'if not exist "{Path(src).parent}" mkdir "{Path(src).parent}"',
                f'move /Y "{dst}" "{src}"',
                f'reg add "{self._approved_folder_path(scope)}" /v "{Path(src).name}" '
                f'/t REG_BINARY /d 020000000000000000000000 /f',
            ]
            self.run_steps("Desbloquear acceso directo", [("Restaurando inicio", cmds)],
                           on_done=lambda: self._after_unblock_startup(item, "moved"))
            return
        if typ == "task":
            cmds = [f'schtasks /Change /TN "{item.get("cmd", "")}" /Enable']
            self.run_steps("Reactivar tarea de inicio", [("Restaurando inicio", cmds)],
                           on_done=lambda: self._after_unblock_startup(item, "tasks"))
            return
        key = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run"
        cmd_val = item["cmd"].replace('"', "")
        cmds = [
            f'reg add "{key}" /v "{item["name"]}" /t REG_SZ /d "{cmd_val}" /f',
            reg_del(self.STARTUP_BLOCK_STORE, item["name"]),
            f'reg add "{self._approved_key_path("HKCU")}" /v "{item["name"]}" /t REG_BINARY /d 020000000000000000000000 /f',
        ]
        self.run_steps("Desbloquear app de inicio", [("Restaurando inicio", cmds)],
                       on_done=lambda: self._after_unblock_startup(item, "blocked"))

    def do_reapply_blocks(self):
        blocked = self._blocked_startup_list()
        if not blocked:
            messagebox.showinfo("Inicio", "No hay elementos bloqueados para reaplicar.")
            return
        cmds = []
        names = list(dict.fromkeys(str(b.get("name", "")) for b in blocked
                                   if b.get("type", "run") == "run" and b.get("name")))
        for scope, kind in [("HKCU", "Run"), ("HKLM", "Run"),
                            ("HKCU", "RunOnce"), ("HKLM", "RunOnce")]:
            key = self._run_key_path(scope, kind)
            for n in names:
                cmds.append(reg_del(key, n))
        for n in names:
            cmds.append(f'reg add "{self._approved_key_path("HKCU")}" /v "{n}" /t REG_BINARY /d 030000000000000000000000 /f')
            cmds.append(f'reg add "{self._approved_key_path("HKLM")}" /v "{n}" /t REG_BINARY /d 030000000000000000000000 /f')
        for it in blocked:
            typ = it.get("type", "run")
            if typ == "task":
                cmds.append(f'schtasks /Change /TN "{it.get("cmd", "")}" /Disable')
            elif typ == "folder":
                src = str(it.get("cmd", ""))
                dst = str(it.get("backup", ""))
                if src and dst:
                    cmds.append(f'if exist "{src}" move /Y "{src}" "{dst}"')
                    cmds.append(f'reg add "{self._approved_folder_path(it.get("scope", "HKCU"))}" '
                                f'/v "{Path(src).name}" /t REG_BINARY /d 030000000000000000000000 /f')
        self.run_steps("Reaplicar bloqueos de inicio",
                       [("Eliminando re-registros y forzando bloqueo", cmds)],
                       on_done=self._refresh_startup_lists)

    def do_disable_extra_service(self, name):
        self.run_steps(f"Deshabilitar servicio: {name}",
                       [(f"Deshabilitando {name}", [f'sc stop "{name}"', f'sc config "{name}" start= disabled'])])

    def do_enable_extra_service(self, name):
        self.run_steps(f"Habilitar servicio: {name}",
                       [(f"Habilitando {name}", [f'sc config "{name}" start= demand', f'sc start "{name}"'])])

    def _build_tab_inicio(self):
        tab = self._new_tab("  Inicio  ")

        ttk.Label(tab, text="Detecta apps, accesos directos y tareas que se ejecutan al iniciar Windows; bloquealos para que no vuelvan a activarse.",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 8))

        hero = tk.Frame(tab, bg=PANEL, highlightbackground=ACCENT, highlightthickness=1)
        hero.pack(fill="x", pady=(0, 10))
        hi = tk.Frame(hero, bg=PANEL)
        hi.pack(fill="x", padx=16, pady=12)

        top_row = tk.Frame(hi, bg=PANEL)
        top_row.pack(fill="x")
        tk.Label(top_row, text="OPTIMIZADOR DE INICIO", bg=PANEL, fg=FG,
                 font=(FONT_BOLD, 14)).pack(side="left")
        self.startup_summary = tk.Label(top_row, text="Analizando...", bg=PANEL,
                                        fg=ACCENT2, font=(FONT_BOLD, 9))
        self.startup_summary.pack(side="right")

        tk.Label(hi, text="Lista y bloquea apps de inicio (Run/RunOnce), accesos directos de la carpeta Inicio "
                          "y tareas programadas de logon. El optimizador ademas desactiva servicios innecesarios "
                          "para que Windows arranque mucho mas rapido. Todo se puede abrir manualmente y restaurar.",
                 bg=PANEL, fg=MUTED, font=(FONT, 9), justify="left",
                 wraplength=900).pack(anchor="w", pady=(4, 10))

        row = tk.Frame(hi, bg=PANEL)
        row.pack(fill="x")
        ttk.Button(row, text="OPTIMIZAR INICIO AHORA", style="Accent.TButton",
                   command=self.do_optimize_startup, cursor="hand2").pack(side="left")
        ttk.Button(row, text="Exclusiones de apps", style="Card.TButton",
                   command=self.open_startup_exclusions, cursor="hand2").pack(side="left", padx=8)
        ttk.Button(row, text="Reaplicar bloqueos", style="Card.TButton",
                   command=self.do_reapply_blocks, cursor="hand2").pack(side="left")
        ttk.Button(row, text="Restaurar inicio", style="Danger.TButton",
                   command=self.do_restore_startup, cursor="hand2").pack(side="right")

        lists = ttk.Frame(tab)
        lists.pack(fill="both", expand=True)
        lists.columnconfigure(0, weight=3)
        lists.columnconfigure(1, weight=2)
        lists.rowconfigure(1, weight=1)

        ttk.Label(lists, text="Apps en inicio (Run / RunOnce)", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 4))
        left_box = tk.Frame(lists, bg=PANEL2, highlightbackground=BORDER, highlightthickness=1)
        left_box.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        self.startup_listbox = tk.Listbox(left_box, bg=PANEL2, fg=FG, selectbackground=ACCENT,
                                          selectforeground="#ffffff", relief="flat", bd=0,
                                          font=("Consolas", 9), activestyle="none", highlightthickness=0)
        self.startup_listbox.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=6)
        sb1 = ttk.Scrollbar(left_box, orient="vertical", command=self.startup_listbox.yview)
        sb1.pack(side="right", fill="y")
        self.startup_listbox.configure(yscrollcommand=sb1.set)

        ttk.Label(lists, text="Bloqueadas por PylandTweaks", style="Section.TLabel").grid(
            row=0, column=1, sticky="w", pady=(0, 4))
        right_box = tk.Frame(lists, bg=PANEL2, highlightbackground=BORDER, highlightthickness=1)
        right_box.grid(row=1, column=1, sticky="nsew")
        self.blocked_listbox = tk.Listbox(right_box, bg=PANEL2, fg=FG, selectbackground=ACCENT,
                                          selectforeground="#ffffff", relief="flat", bd=0,
                                          font=("Consolas", 9), activestyle="none", highlightthickness=0)
        self.blocked_listbox.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=6)
        sb2 = ttk.Scrollbar(right_box, orient="vertical", command=self.blocked_listbox.yview)
        sb2.pack(side="right", fill="y")
        self.blocked_listbox.configure(yscrollcommand=sb2.set)

        btns = tk.Frame(tab, bg=BG)
        btns.pack(fill="x", pady=(8, 4))
        ttk.Button(btns, text="Actualizar listas", style="Card.TButton",
                   command=self._refresh_startup_lists, cursor="hand2").pack(side="left")
        ttk.Button(btns, text="Bloquear seleccionada", style="Danger.TButton",
                   command=self.do_block_selected_startup, cursor="hand2").pack(side="left", padx=6)
        ttk.Button(btns, text="Reaplicar bloqueos", style="Accent.TButton",
                   command=self.do_reapply_blocks, cursor="hand2").pack(side="left")
        ttk.Button(btns, text="Desbloquear seleccionada", style="Card.TButton",
                   command=self.do_unblock_selected, cursor="hand2").pack(side="left", padx=6)

        self._notice(tab, "Bloquear quita la app del inicio, la guarda en bloqueadas y la marca como deshabilitada. Si la app vuelve a agregarse al ejecutarla, usa 'Reaplicar bloqueos' para eliminarla de nuevo.")

        svc = tk.Frame(tab, bg=BG)
        svc.pack(fill="both", expand=False, pady=(10, 0))
        tk.Label(svc, text="Servicios adicionales (con explicacion)", bg=BG, fg=ACCENT2,
                 font=(FONT_BOLD, 10)).pack(anchor="w", pady=(0, 6))

        canvas = tk.Canvas(svc, bg=BG, highlightthickness=0, height=220)
        vs = ttk.Scrollbar(svc, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas, bg=BG)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vs.set)
        canvas.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y")

        for i in range(2):
            inner.columnconfigure(i, weight=1)
        for idx, (svc_name, title, desc) in enumerate(self.EXTRA_SERVICES):
            card = tk.Frame(inner, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
            card.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=5, pady=5)
            ci = tk.Frame(card, bg=PANEL)
            ci.pack(fill="both", expand=True, padx=10, pady=8)
            tk.Label(ci, text=title, bg=PANEL, fg=ACCENT2, font=(FONT_BOLD, 9)).pack(anchor="w")
            tk.Label(ci, text=desc, bg=PANEL, fg=MUTED, font=(FONT, 8), justify="left",
                     wraplength=360).pack(anchor="w", pady=(2, 6))
            rowb = tk.Frame(ci, bg=PANEL)
            rowb.pack(fill="x")
            ttk.Button(rowb, text="Deshabilitar", style="Danger.TButton",
                       command=lambda n=svc_name: self.do_disable_extra_service(n), cursor="hand2").pack(side="left")
            ttk.Button(rowb, text="Restaurar (Manual)", style="Card.TButton",
                       command=lambda n=svc_name: self.do_enable_extra_service(n), cursor="hand2").pack(side="left", padx=6)

        self.root.after(150, self._refresh_startup_lists)


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
        tk.Label(info, text="Version 5.9", bg=PANEL, fg=ACCENT2,
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
            "Optimizador de inicio con animacion, exclusiones y restauracion",
            "Potato Graphics Studio con perfiles tipo NVIDIA Profile Inspector",
            "Niveles Potato automaticos segun GPU, CPU, RAM y resolucion",
            "Modo temporal seguro (pausar y reactivar cuando quieras)",
            "Macro: truco FF + clic, modo mantener F y grabadora de teclas y clics",
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

    # ------------------------------------------------------------------ macro
    def _toggle_macro_advanced(self):
        self.macro_advanced_visible = not self.macro_advanced_visible
        if self.macro_advanced_visible:
            self.macro_adv.grid()
            self.macro_adv_btn.configure(text="Ocultar opciones avanzadas")
        else:
            self.macro_adv.grid_remove()
            self.macro_adv_btn.configure(text="Mostrar opciones avanzadas")

    def _macro_event_label(self, ev):
        kind = ev.get("kind")
        if kind == "down":
            return f"Tecla {vk_name(ev['vk'])} ABAJO"
        if kind == "up":
            return f"Tecla {vk_name(ev['vk'])} ARRIBA"
        if kind == "click_down":
            return "Clic izquierdo ABAJO"
        if kind == "click_up":
            return "Clic izquierdo ARRIBA"
        return str(kind)

    def _macro_refresh_list(self):
        selected = self.macro_listbox.curselection()
        selected = int(selected[0]) if selected else None
        self.macro_listbox.delete(0, "end")
        for idx, ev in enumerate(self.macro_events, 1):
            self.macro_listbox.insert(
                "end", f"{idx:02d}. {ev['delay']:8.1f} ms   {self._macro_event_label(ev)}")
        self.macro_count_label.configure(text=f"{len(self.macro_events)} pasos")
        if selected is not None and selected < len(self.macro_events):
            self.macro_listbox.selection_set(selected)
            self._macro_on_select()

    def _macro_update_status(self, mode):
        color = {"recording": RED, "playing": GREEN,
                 "armed": YELLOW, "holding": GREEN}.get(mode, MUTED)
        if mode == "recording":
            label, hint = "GRABANDO", "Pulsa F9 o «Detener» para terminar la grabacion."
        elif mode == "playing":
            label, hint = "REPRODUCIENDO", "F8, END o SUPR detienen la reproduccion."
        elif mode == "holding":
            if self.macro_hold_sequence:
                label = "EDITANDO"
                hint = "Aplicando la edición rápida..."
            else:
                label = "CLICS ACTIVOS"
                hint = "Suelta F para parar."
        elif mode == "armed":
            if self.macro_hold_sequence:
                label = "EDICIÓN RÁPIDA LISTA"
                hint = "Pulsa la tecla rápida para editar al instante. Tu F normal sigue intacta. F4/END/SUPR paran."
            else:
                label = "SOLO CLICS ACTIVO"
                hint = "Mantén F para clicar; suelta F para parar."
        else:
            label = "MACRO LISTA"
            hint = "Activa la edición rápida y pulsa la tecla configurada para editar al instante."
        self.macro_status_dot.itemconfigure(self._macro_dot_item, fill=color, outline=color)
        self.macro_status_label.configure(text=label, fg=color)
        self.macro_status_hint.configure(text=hint)

        busy_rec = mode == "recording"
        busy_play = mode == "playing"
        busy_hold = mode in ("armed", "holding")
        self.macro_record_btn.state(
            ["disabled"] if busy_rec or busy_play or busy_hold else ["!disabled"])
        self.macro_stop_record_btn.state(["!disabled"] if busy_rec else ["disabled"])
        self.macro_clear_btn.state(
            ["disabled"] if busy_rec or busy_play or busy_hold else ["!disabled"])
        self.macro_play_btn.state(
            ["disabled"] if busy_rec or busy_play or busy_hold
            or not self.macro_events else ["!disabled"])
        self.macro_stop_play_btn.state(["!disabled"] if busy_play else ["disabled"])
        self.macro_trick_start_btn.state(
            ["disabled"] if busy_rec or busy_play or busy_hold else ["!disabled"])
        self.macro_trick_stop_btn.state(["!disabled"] if busy_play else ["disabled"])
        seq_active = self.macro_hold_armed and self.macro_hold_sequence
        hold_active = self.macro_hold_armed and not self.macro_hold_sequence
        if hold_active:
            self.macro_hold_btn.configure(text="DETENER SOLO CLICS",
                                          style="Danger.TButton")
        else:
            self.macro_hold_btn.configure(text="MODO SOLO CLICS CON F",
                                          style="Card.TButton")
        if seq_active:
            self.macro_seq_btn.configure(text="DETENER EDICIÓN RÁPIDA",
                                         style="Danger.TButton")
        else:
            self.macro_seq_btn.configure(text="ACTIVAR EDICIÓN RÁPIDA",
                                         style="Card.TButton")
        self.macro_hold_btn.state(
            ["disabled"] if busy_rec or busy_play else ["!disabled"])
        self.macro_seq_btn.state(
            ["disabled"] if busy_rec or busy_play else ["!disabled"])

    def _macro_set_hint(self, text):
        self.macro_status_hint.configure(text=text)

    def _macro_on_select(self, _event=None):
        sel = self.macro_listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        if 0 <= idx < len(self.macro_events):
            self.macro_selected_delay_var.set(
                int(round(self.macro_events[idx]["delay"])))

    def apply_macro_step_delay(self):
        if self.macro_recording or self.macro_playing:
            return
        sel = self.macro_listbox.curselection()
        if not sel:
            messagebox.showinfo("Macro", "Selecciona primero un paso de la lista.")
            return
        try:
            value = int(self.macro_selected_delay_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Macro", "El retardo debe ser un numero entero (ms).")
            return
        if not 0 <= value <= 60000:
            messagebox.showerror("Macro", "El retardo debe estar entre 0 y 60000 ms.")
            return
        idx = int(sel[0])
        self.macro_events[idx]["delay"] = float(value)
        self._macro_refresh_list()
        self.macro_listbox.selection_set(idx)
        self._macro_on_select()
        self.log(f"Macro: paso {idx + 1} ajustado a {value} ms.")

    def move_macro_step(self, delta):
        if self.macro_recording or self.macro_playing:
            return
        sel = self.macro_listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        new_idx = idx + delta
        if not 0 <= new_idx < len(self.macro_events):
            return
        self.macro_events[idx], self.macro_events[new_idx] = (
            self.macro_events[new_idx], self.macro_events[idx])
        self._macro_refresh_list()
        self.macro_listbox.selection_set(new_idx)
        self.macro_listbox.see(new_idx)
        self._macro_on_select()

    def start_macro_trick(self):
        if self.macro_recording or self.macro_playing or self.macro_hold_armed:
            return
        try:
            gap = int(self.macro_preset_gap_var.get())
            hold = int(self.macro_preset_hold_var.get())
            clicks = int(self.macro_trick_clicks_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Macro", "Los tiempos del truco deben ser numeros enteros.")
            return
        if not (0 <= gap <= 60000 and 0 <= hold <= 60000 and 0 <= clicks <= 1000000):
            messagebox.showerror("Macro", "Revisa los tiempos del truco (0 a 60000 ms).")
            return

        self.macro_trick_gap = gap / 1000.0
        self.macro_trick_hold = hold / 1000.0
        self.macro_trick_clicks = clicks
        self.macro_trick_double = bool(self.macro_trick_double_f_var.get())
        self.macro_play_stop.clear()
        self.macro_playing = True
        self._macro_update_status("playing")
        self.log("### Macro ### Truco FF + CLIC iniciado (la segunda F queda pulsada).")
        self.log(f"Entre acciones: {gap} ms | Clic: {hold} ms | "
                 f"Clics: {'infinitos' if clicks == 0 else clicks} | "
                 f"Doble F: {'si' if self.macro_trick_double else 'no'}")
        self.macro_play_thread = threading.Thread(
            target=self._macro_trick_worker, daemon=True)
        self.macro_play_thread.start()

    def _macro_trick_worker(self):
        f_down = False
        click_down = False
        reason = "fin"
        sent = 0
        gap = max(0.001, self.macro_trick_gap)
        hold = max(0.001, self.macro_trick_hold)
        try:
            if self.macro_trick_double:
                send_key(VK_F, False)
                f_down = True
                if not self._macro_pause_playback(hold):
                    return
                send_key(VK_F, True)
                f_down = False
                if not self._macro_pause_playback(gap):
                    return

            send_key(VK_F, False)
            f_down = True
            if not self._macro_pause_playback(gap):
                return

            while not self.macro_play_stop.is_set():
                if self.macro_trick_clicks and sent >= self.macro_trick_clicks:
                    reason = "clics completados"
                    break
                send_left_click(True)
                click_down = True
                if not self._macro_pause_playback(hold):
                    break
                send_left_click(False)
                click_down = False
                sent += 1
                if not self._macro_pause_playback(gap):
                    break
        finally:
            if click_down:
                send_left_click(False)
            if f_down:
                send_key(VK_F, True)
            self.macro_playing = False
            if self.macro_play_stop.is_set() and reason == "fin":
                reason = "detenida por atajo"
            try:
                self.root.after(0, self._macro_play_finished, reason)
            except Exception:  # noqa: BLE001
                pass

    def toggle_macro_hold_mode(self):
        if self.macro_hold_armed and not self.macro_hold_sequence:
            self.stop_macro_hold_mode()
        else:
            if self.macro_hold_armed:
                self.stop_macro_hold_mode()
            self.start_macro_hold_mode(sequence=False)

    def toggle_macro_sequence_mode(self):
        if self.macro_hold_armed and self.macro_hold_sequence:
            self.stop_macro_hold_mode()
        else:
            if self.macro_hold_armed:
                self.stop_macro_hold_mode()
            self.start_macro_hold_mode(sequence=True)

    def start_macro_hold_mode(self, sequence=False):
        if self.macro_hold_armed or self.macro_recording or self.macro_playing:
            return
        try:
            gap = int(self.macro_preset_gap_var.get())
            hold = int(self.macro_preset_hold_var.get())
            clicks = int(self.macro_trick_clicks_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Macro", "Los tiempos del modo F deben ser numeros enteros.")
            return
        if not (0 <= gap <= 60000 and 0 <= hold <= 60000 and 0 <= clicks <= 1000000):
            messagebox.showerror("Macro", "Revisa los tiempos del modo F (0 a 60000 ms).")
            return

        trigger_vk = VK_F
        edit_vk = VK_F
        press = hold
        click_ms = hold
        confirm_ms = 30
        autoconfirm = True
        if sequence:
            try:
                press = int(self.macro_seq_press_var.get())
                click_ms = int(self.macro_seq_click_var.get())
                confirm_ms = int(self.macro_seq_confirm_var.get())
            except (tk.TclError, ValueError):
                messagebox.showerror("Macro", "Los tiempos de la edicion rapida deben ser enteros.")
                return
            if not (0 <= press <= 2000 and 0 <= click_ms <= 2000
                    and 0 <= confirm_ms <= 2000):
                messagebox.showerror("Macro", "Revisa los tiempos de la edicion rapida (0 a 2000 ms).")
                return
            trigger_vk = vk_from_text(self.macro_seq_key_var.get())
            edit_vk = vk_from_text(self.macro_seq_edit_var.get())
            if trigger_vk is None:
                messagebox.showerror("Macro", "Tecla rapida no valida. Usa una sola letra (por ejemplo g).")
                return
            if edit_vk is None:
                messagebox.showerror("Macro", "Tecla de edicion no valida. Usa una sola letra (por ejemplo f).")
                return
            if trigger_vk == edit_vk:
                messagebox.showerror("Macro", "La tecla rapida debe ser distinta de la tecla de edicion (F).")
                return
            autoconfirm = bool(self.macro_seq_autoconfirm_var.get())
            gap = 0

        self.macro_hold_sequence = bool(sequence)
        self.macro_hold_trigger_vk = trigger_vk
        self.macro_hold_edit_vk = edit_vk
        self.macro_trick_gap = gap / 1000.0
        self.macro_trick_hold = hold / 1000.0
        self.macro_trick_clicks = clicks
        self.macro_hold_press = max(0.001, press / 1000.0)
        self.macro_hold_click = max(0.001, click_ms / 1000.0)
        self.macro_hold_confirm = max(0.001, confirm_ms / 1000.0)
        self.macro_hold_autoconfirm = autoconfirm
        self.macro_hold_keep_active = True if sequence else bool(
            self.macro_hold_keep_var.get())
        self.macro_hold_armed = True
        self.macro_hold_stop.clear()
        self.macro_hold_key_event.clear()
        self.macro_hold_ui_queue = queue.Queue()
        self._macro_update_status("armed")
        if sequence:
            self.log("### Macro ### Edicion rapida activada (un toque = edicion instantanea).")
            self.log(f"Rapida {vk_name(trigger_vk)} | Editar {vk_name(edit_vk)} | "
                     f"Entrar {press} ms | Clic {click_ms} ms | Confirmar {confirm_ms} ms | "
                     f"Auto-Confirm {'SI' if autoconfirm else 'NO'} | F4/END/SUPR detienen.")
        else:
            self.log("### Macro ### Modo mantener F activado (solo clics; la F es tuya).")
            self.log(f"Mantén F para clicar | Entre {gap} ms | Clic {hold} ms | "
                     f"Clics por pulsacion: {'infinitos' if clicks == 0 else clicks}")
        self.macro_hold_click_thread = threading.Thread(
            target=self._macro_hold_click_worker, daemon=True)
        self.macro_hold_hook_thread = threading.Thread(
            target=self._macro_hold_hook_worker, daemon=True)
        self.macro_hold_click_thread.start()
        self.macro_hold_hook_thread.start()
        self.root.after(30, self._macro_hold_poll)

    def stop_macro_hold_mode(self):
        if not self.macro_hold_armed:
            return
        was_sequence = self.macro_hold_sequence
        self.macro_hold_armed = False
        self.macro_hold_stop.set()
        self.macro_hold_key_event.clear()
        self._macro_update_status("idle")
        self.log("Macro: macro de edicion desactivada." if was_sequence
                 else "Macro: modo mantener F desactivado.")
        for thread in (self.macro_hold_hook_thread, self.macro_hold_click_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=0.5)
        self.macro_hold_hook_thread = None
        self.macro_hold_click_thread = None
        self.macro_hold_sequence = False

    def _macro_hold_hook_failed(self):
        self.log("Macro: no se pudo instalar el gancho de teclado del modo F.")
        self.stop_macro_hold_mode()

    def _macro_hold_hook_worker(self):
        user32 = ctypes.windll.user32
        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int, HOOKPROC, ctypes.c_void_p, ctypes.c_uint]
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.CallNextHookEx.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t]
        user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        user32.PeekMessageW.argtypes = [
            ctypes.POINTER(_MSG), ctypes.c_void_p, ctypes.c_uint,
            ctypes.c_uint, ctypes.c_uint]
        user32.TranslateMessage.argtypes = [ctypes.POINTER(_MSG)]
        user32.DispatchMessageW.argtypes = [ctypes.POINTER(_MSG)]

        hooks = {}
        trigger_held = False
        edit_held = False
        fortnite_active = False
        sequence = self.macro_hold_sequence
        trigger_vk = self.macro_hold_trigger_vk
        edit_vk = self.macro_hold_edit_vk
        stop_vks = {VK_F4, VK_F8, VK_END, VK_DELETE} - {trigger_vk, edit_vk}

        def kb_proc(n_code, w_param, l_param):
            nonlocal trigger_held, edit_held
            if n_code == 0:
                data = ctypes.cast(
                    l_param, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
                if not (data.flags & LLKHF_INJECTED):
                    down = w_param in (WM_KEYDOWN, WM_SYSKEYDOWN)
                    up = w_param in (WM_KEYUP, WM_SYSKEYUP)
                    if data.vkCode in stop_vks and down:
                        self.macro_hold_ui_queue.put(("stop", None))
                        if fortnite_active:
                            return 1
                    if data.vkCode == edit_vk and fortnite_active:
                        if down:
                            edit_held = True
                        elif up:
                            edit_held = False
                    if data.vkCode == trigger_vk:
                        if not fortnite_active:
                            return user32.CallNextHookEx(
                                hooks.get("kb"), n_code, w_param, l_param)
                        if down:
                            if not trigger_held:
                                trigger_held = True
                                if not sequence or (
                                        not edit_held
                                        and not key_is_down(VK_LBUTTON)):
                                    self.macro_hold_key_event.set()
                            if sequence:
                                return 1
                        elif up:
                            trigger_held = False
                            if sequence:
                                return 1
                            self.macro_hold_key_event.clear()
            return user32.CallNextHookEx(hooks.get("kb"), n_code, w_param, l_param)

        kb_cb = HOOKPROC(kb_proc)
        hooks["kb"] = user32.SetWindowsHookExW(WH_KEYBOARD_LL, kb_cb, None, 0)
        if not hooks["kb"]:
            self.macro_hold_ui_queue.put(("failed", None))
            return

        msg = _MSG()
        try:
            while not self.macro_hold_stop.is_set():
                while user32.PeekMessageW(
                        ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                fortnite_active = fortnite_is_active()
                time.sleep(0.004)
        finally:
            self.macro_hold_key_event.clear()
            if hooks.get("kb"):
                user32.UnhookWindowsHookEx(hooks["kb"])

    def _macro_hold_click_worker(self):
        sequence = self.macro_hold_sequence
        edit_vk = self.macro_hold_edit_vk
        gap = max(0.001, self.macro_trick_gap)
        hold = max(0.001, self.macro_trick_hold)
        press = max(0.001, self.macro_hold_press)
        click_ms = max(0.001, self.macro_hold_click)
        confirm_ms = max(0.001, self.macro_hold_confirm)
        autoconfirm = self.macro_hold_autoconfirm
        limit = self.macro_trick_clicks
        active = False
        burst_done = False
        sent = 0
        click_down = False
        try:
            while not self.macro_hold_stop.is_set():
                if sequence:
                    if not self.macro_hold_key_event.is_set():
                        self.macro_hold_key_event.wait(0.01)
                        continue
                    self.macro_hold_key_event.clear()
                    self._macro_hold_notify(True)
                    try:
                        send_key(edit_vk, False)
                        time.sleep(0.01)
                        send_key(edit_vk, True)
                        if not self._macro_hold_sleep(press):
                            continue
                        send_left_click(True)
                        click_down = True
                        if not self._macro_hold_sleep(click_ms):
                            continue
                        send_left_click(False)
                        click_down = False
                        if not autoconfirm:
                            if not self._macro_hold_sleep(confirm_ms):
                                continue
                            send_key(edit_vk, False)
                            time.sleep(0.01)
                            send_key(edit_vk, True)
                    finally:
                        if click_down:
                            send_left_click(False)
                            click_down = False
                        self._macro_hold_notify(False)
                    continue
                if not self.macro_hold_key_event.is_set():
                    if active or burst_done:
                        active = False
                        burst_done = False
                        self._macro_hold_notify(False)
                        if not self.macro_hold_keep_active:
                            self.macro_hold_ui_queue.put(("released", None))
                    self.macro_hold_key_event.wait(0.01)
                    continue
                if not active and not burst_done:
                    active = True
                    sent = 0
                    self._macro_hold_notify(True)
                if burst_done:
                    self.macro_hold_key_event.wait(0.01)
                    continue
                if limit and sent >= limit:
                    burst_done = True
                    self._macro_hold_notify(False)
                    continue
                if not self.macro_hold_key_event.is_set():
                    continue
                send_left_click(True)
                try:
                    held_ok = self._macro_hold_pause(hold)
                finally:
                    send_left_click(False)
                if held_ok:
                    sent += 1
                    self._macro_hold_pause(gap)
        finally:
            if click_down:
                send_left_click(False)
            self._macro_hold_notify(False)

    def _macro_hold_pause(self, seconds):
        end = time.perf_counter() + max(0.0, seconds)
        while True:
            if (self.macro_hold_stop.is_set()
                    or not self.macro_hold_key_event.is_set()):
                return False
            remaining = end - time.perf_counter()
            if remaining <= 0:
                return True
            time.sleep(min(remaining, 0.005))

    def _macro_hold_sleep(self, seconds):
        end = time.perf_counter() + max(0.0, seconds)
        while not self.macro_hold_stop.is_set():
            remaining = end - time.perf_counter()
            if remaining <= 0:
                return True
            time.sleep(min(remaining, 0.005))
        return False

    def _macro_hold_notify(self, held):
        self.macro_hold_ui_queue.put(("held", held))

    def _macro_hold_state_changed(self, held):
        if not self.macro_hold_armed:
            return
        self._macro_update_status("holding" if held else "armed")

    def _macro_hold_poll(self):
        if not self.macro_hold_armed:
            return
        failed = False
        released = False
        stop_requested = False
        while True:
            try:
                kind, value = self.macro_hold_ui_queue.get_nowait()
            except queue.Empty:
                break
            if kind == "held":
                self._macro_hold_state_changed(value)
            elif kind == "released":
                released = True
            elif kind == "stop":
                stop_requested = True
            elif kind == "failed":
                failed = True
        if failed:
            self._macro_hold_hook_failed()
            return
        if stop_requested or released:
            if stop_requested:
                self.log("Macro: parada de emergencia (F4/END/SUPR/F8).")
            self.stop_macro_hold_mode()
            return
        if self.macro_hold_armed:
            self.root.after(30, self._macro_hold_poll)

    def _macro_record_event(self, kind, vk):
        if not self.macro_recording or self.macro_record_stop.is_set():
            return
        if kind == "down":
            if vk in self.macro_record_keys:
                return
            self.macro_record_keys.add(vk)
        elif kind == "up":
            if vk not in self.macro_record_keys:
                return
            self.macro_record_keys.discard(vk)
        now = time.perf_counter()
        if self.macro_record_last is None:
            delay = 0.0
        else:
            delay = min((now - self.macro_record_last) * 1000.0, 60000.0)
        self.macro_record_last = now
        self.macro_events.append({"kind": kind, "vk": vk, "delay": round(delay, 1)})

    def start_macro_recording(self):
        if self.macro_recording or self.macro_playing or self.macro_hold_armed:
            return
        self.macro_events = []
        self.macro_record_keys = set()
        self.macro_record_last = None
        self._macro_refresh_list()
        self.macro_record_stop.clear()
        self.macro_recording = True
        self._macro_update_status("recording")
        self.log("### Macro ### Grabacion solicitada (cuenta atras de 3 s).")
        self._macro_countdown(3)

    def _macro_countdown(self, n):
        if not self.macro_recording:
            return
        if self.macro_record_stop.is_set():
            self._macro_record_finished()
            return
        if n > 0:
            self._macro_set_hint(f"Preparado... la grabacion empieza en {n} s.")
            self.log(f"Macro: grabando en {n}...")
            self.root.after(1000, self._macro_countdown, n - 1)
            return
        self._macro_set_hint("GRABANDO... pulsa F9 o «Detener» para terminar.")
        self.log("Macro: grabando. Pulsa F9 para detener.")
        self.macro_record_thread = threading.Thread(
            target=self._macro_record_worker, daemon=True)
        self.macro_record_thread.start()

    def _macro_record_worker(self):
        user32 = ctypes.windll.user32
        user32.SetWindowsHookExW.restype = ctypes.c_void_p
        user32.SetWindowsHookExW.argtypes = [
            ctypes.c_int, HOOKPROC, ctypes.c_void_p, ctypes.c_uint]
        user32.CallNextHookEx.restype = ctypes.c_ssize_t
        user32.CallNextHookEx.argtypes = [
            ctypes.c_void_p, ctypes.c_int, ctypes.c_size_t, ctypes.c_ssize_t]
        user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
        user32.PeekMessageW.argtypes = [
            ctypes.POINTER(_MSG), ctypes.c_void_p, ctypes.c_uint,
            ctypes.c_uint, ctypes.c_uint]
        user32.TranslateMessage.argtypes = [ctypes.POINTER(_MSG)]
        user32.DispatchMessageW.argtypes = [ctypes.POINTER(_MSG)]

        hooks = {}

        def kb_proc(n_code, w_param, l_param):
            if n_code == 0:
                data = ctypes.cast(
                    l_param, ctypes.POINTER(_KBDLLHOOKSTRUCT)).contents
                if not (data.flags & LLKHF_INJECTED):
                    if w_param in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        if data.vkCode == VK_F9:
                            self.macro_record_stop.set()
                            return 1
                        self._macro_record_event("down", int(data.vkCode))
                    elif w_param in (WM_KEYUP, WM_SYSKEYUP):
                        self._macro_record_event("up", int(data.vkCode))
            return user32.CallNextHookEx(hooks.get("kb"), n_code, w_param, l_param)

        def ms_proc(n_code, w_param, l_param):
            if n_code == 0:
                data = ctypes.cast(
                    l_param, ctypes.POINTER(_MSLLHOOKSTRUCT)).contents
                if not (data.flags & LLMHF_INJECTED):
                    if w_param == WM_LBUTTONDOWN:
                        self._macro_record_event("click_down", 0)
                    elif w_param == WM_LBUTTONUP:
                        self._macro_record_event("click_up", 0)
            return user32.CallNextHookEx(hooks.get("ms"), n_code, w_param, l_param)

        kb_cb = HOOKPROC(kb_proc)
        ms_cb = HOOKPROC(ms_proc)
        hooks["kb"] = user32.SetWindowsHookExW(WH_KEYBOARD_LL, kb_cb, None, 0)
        hooks["ms"] = user32.SetWindowsHookExW(WH_MOUSE_LL, ms_cb, None, 0)

        msg = _MSG()
        try:
            while not self.macro_record_stop.is_set():
                while user32.PeekMessageW(
                        ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                time.sleep(0.004)
        finally:
            if hooks.get("kb"):
                user32.UnhookWindowsHookEx(hooks["kb"])
            if hooks.get("ms"):
                user32.UnhookWindowsHookEx(hooks["ms"])
            try:
                self.root.after(0, self._macro_record_finished)
            except Exception:  # noqa: BLE001
                pass

    def _macro_record_finished(self):
        if not self.macro_recording:
            return
        self.macro_recording = False
        self._macro_refresh_list()
        self._macro_update_status("idle")
        self.log(f"Macro: grabacion detenida. {len(self.macro_events)} pasos grabados.")

    def stop_macro_recording(self):
        if not self.macro_recording:
            return
        self.macro_record_stop.set()
        self._macro_set_hint("Deteniendo grabacion...")
        self.log("Macro: deteniendo grabacion.")
        if self.macro_record_thread is None or not self.macro_record_thread.is_alive():
            self._macro_record_finished()

    def _macro_edit_delay(self, _event=None):
        if self.macro_recording or self.macro_playing:
            return
        sel = self.macro_listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        value = simpledialog.askfloat(
            "Retardo del paso",
            f"Retardo antes del paso {idx + 1} (ms):",
            initialvalue=self.macro_events[idx]["delay"],
            minvalue=0, maxvalue=60000, parent=self.root)
        if value is None:
            return
        self.macro_events[idx]["delay"] = round(float(value), 1)
        self._macro_refresh_list()
        self.macro_listbox.selection_set(idx)
        self.log(f"Macro: paso {idx + 1} ajustado a {value:.1f} ms.")

    def delete_macro_step(self):
        if self.macro_recording or self.macro_playing:
            return
        sel = self.macro_listbox.curselection()
        if not sel:
            return
        idx = int(sel[0])
        del self.macro_events[idx]
        self._macro_refresh_list()
        self._macro_update_status("idle")
        self.log(f"Macro: paso {idx + 1} eliminado.")

    def clear_macro_steps(self):
        if self.macro_recording or self.macro_playing:
            return
        self.macro_events = []
        self._macro_refresh_list()
        self._macro_update_status("idle")
        self.log("Macro: secuencia borrada.")

    def _macro_pause_playback(self, seconds):
        end = time.perf_counter() + max(0.0, seconds)
        while not self.macro_play_stop.is_set():
            if (key_is_down(VK_F8) or key_is_down(VK_END)
                    or key_is_down(VK_DELETE)):
                self.macro_play_stop.set()
                return False
            remaining = end - time.perf_counter()
            if remaining <= 0:
                return True
            time.sleep(min(remaining, 0.01))
        return False

    def start_macro_playback(self):
        if self.macro_recording or self.macro_playing or self.macro_hold_armed:
            return
        if not self.macro_events:
            messagebox.showinfo("Macro", "Primero graba una secuencia.")
            return
        try:
            extra_ms = int(self.macro_extra_delay_var.get())
            pause_ms = int(self.macro_loop_pause_var.get())
            repeats = int(self.macro_repeat_var.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Macro", "Los tiempos deben ser numeros enteros.")
            return
        if extra_ms < 0 or pause_ms < 0 or repeats < 0:
            messagebox.showerror("Macro", "Los tiempos no pueden ser negativos.")
            return

        self.macro_extra_delay = extra_ms / 1000.0
        self.macro_loop_pause = pause_ms / 1000.0
        self.macro_repeat = repeats
        self.macro_play_stop.clear()
        self.macro_playing = True
        self._macro_update_status("playing")
        self.log("### Macro ### Reproduciendo secuencia.")
        self.log(f"Pasos: {len(self.macro_events)} | Extra: {extra_ms} ms | "
                 f"Pausa: {pause_ms} ms | Repeticiones: "
                 f"{'infinitas' if repeats == 0 else repeats}")
        self.macro_play_thread = threading.Thread(
            target=self._macro_play_worker, daemon=True)
        self.macro_play_thread.start()

    def _macro_play_worker(self):
        events = [dict(ev) for ev in self.macro_events]
        pressed = set()
        click_down = False
        reason = "fin"
        try:
            done = 0
            while not self.macro_play_stop.is_set():
                if self.macro_repeat and done >= self.macro_repeat:
                    reason = "repeticiones completadas"
                    break
                for ev in events:
                    if self.macro_play_stop.is_set():
                        break
                    wait = ev["delay"] / 1000.0 + self.macro_extra_delay
                    if not self._macro_pause_playback(wait):
                        break
                    kind = ev["kind"]
                    if kind == "down":
                        send_key(ev["vk"], False)
                        pressed.add(ev["vk"])
                    elif kind == "up":
                        send_key(ev["vk"], True)
                        pressed.discard(ev["vk"])
                    elif kind == "click_down":
                        send_left_click(True)
                        click_down = True
                    elif kind == "click_up":
                        send_left_click(False)
                        click_down = False
                done += 1
                if self.macro_play_stop.is_set():
                    break
                if self.macro_repeat and done >= self.macro_repeat:
                    reason = "repeticiones completadas"
                    break
                if not self._macro_pause_playback(self.macro_loop_pause):
                    break
        finally:
            for vk in pressed:
                send_key(vk, True)
            if click_down:
                send_left_click(False)
            self.macro_playing = False
            if self.macro_play_stop.is_set() and reason == "fin":
                reason = "detenida por atajo"
            try:
                self.root.after(0, self._macro_play_finished, reason)
            except Exception:  # noqa: BLE001
                pass

    def _macro_play_finished(self, reason):
        self._macro_update_status("idle")
        self.log(f"Macro: reproduccion finalizada ({reason}).")

    def stop_macro_playback(self):
        if not self.macro_playing:
            return
        self.macro_play_stop.set()
        self.log("Macro: deteniendo reproduccion.")

    def _on_close(self):
        overlay = getattr(self, "startup_overlay", None)
        if overlay is not None:
            overlay.cancelled = True
            try:
                overlay.close()
            except Exception:  # noqa: BLE001
                pass
        self.macro_record_stop.set()
        self.macro_play_stop.set()
        self.macro_hold_stop.set()
        self.macro_hold_key_event.clear()
        for thread in (self.macro_record_thread, self.macro_play_thread,
                       self.macro_hold_hook_thread, self.macro_hold_click_thread):
            if thread is not None and thread.is_alive():
                thread.join(timeout=0.6)
        self.root.destroy()

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

    # ------------------------------------------------------- planes energia
    def _capture(self, command):
        try:
            result = subprocess.run(
                command, shell=True, cwd=str(BASE),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW,
            )
            return result.stdout.decode("mbcs", errors="replace").strip()
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: {exc}"

    def _capture_ps(self, script):
        import tempfile
        path = None
        try:
            fd, path = tempfile.mkstemp(suffix=".ps1")
            os.close(fd)
            with open(path, "w", encoding="utf-8-sig") as fh:
                fh.write(script)
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", path],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW,
            )
            return result.stdout.decode("mbcs", errors="replace")
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: {exc}"
        finally:
            if path:
                try:
                    os.remove(path)
                except Exception:  # noqa: BLE001
                    pass

    def _plan_file(self, name):
        return RECURSOS / "Plan de Energia CPU" / name

    def _save_prev_plan(self):
        out = self._capture("powercfg /getactivescheme")
        match = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                          r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", out)
        if match:
            try:
                path = self._plan_file("prev_plan.txt")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(match.group(1), encoding="utf-8")
            except Exception:  # noqa: BLE001
                pass

    def _ensure_plan(self, source_guid, tag):
        path = self._plan_file(f"plan_{tag}_guid.txt")
        existing = ""
        try:
            if path.exists():
                existing = path.read_text(encoding="utf-8").strip()
        except Exception:  # noqa: BLE001
            existing = ""
        if existing and existing.lower() in self._capture("powercfg /list").lower():
            return existing
        out = self._capture(f"powercfg -duplicatescheme {source_guid}")
        self.log(out)
        match = re.search(r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
                          r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})", out)
        if not match:
            return ""
        guid = match.group(1)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(guid, encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
        return guid

    def cmds_tune_gaming_plan(self, guid):
        return [
            f"powercfg -setacvalueindex {guid} SUB_PROCESSOR PROCTHROTTLEMIN 100",
            f"powercfg -setacvalueindex {guid} SUB_PROCESSOR PROCTHROTTLEMAX 100",
            f"powercfg -setacvalueindex {guid} SUB_PROCESSOR CPMINCORES 100",
            f"powercfg -setacvalueindex {guid} SUB_PROCESSOR CPMAXCORES 100",
            f"powercfg -setacvalueindex {guid} SUB_PROCESSOR PERFBOOSTMODE 2",
            f"powercfg -setacvalueindex {guid} SUB_PROCESSOR IDLEDISABLE 1",
            f"powercfg -setacvalueindex {guid} SUB_PROCESSOR SYSCOOLPOL 1",
            f"powercfg -setacvalueindex {guid} SUB_PCIEXPRESS ASPM 0",
            f"powercfg -setacvalueindex {guid} SUB_DISK DISKIDLE 0",
            f"powercfg -setacvalueindex {guid} SUB_USB USBSELECTIVESUSPEND 0",
            f"powercfg -setactive {guid}",
        ]

    def apply_plan(self, tag):
        title = PLAN_NAMES.get(tag, tag)

        def worker():
            self.log(f"### Plan de energia: {title} ###")
            self._save_prev_plan()
            if tag in ("balanced", "high"):
                guid = PLAN_BALANCED if tag == "balanced" else PLAN_HIGH
                self.exec_cmd(f"powercfg -setactive {guid}")
            elif tag == "ultimate":
                guid = self._ensure_plan(PLAN_ULTIMATE, "ultimate")
                if not guid:
                    self.log("No se pudo crear el plan Ultimate. Usa 'Alto rendimiento'.")
                    return
                self.exec_cmd(f"powercfg -setactive {guid}")
            elif tag == "gaming":
                guid = self._ensure_plan(PLAN_HIGH, "gaming")
                if not guid:
                    self.log("No se pudo crear el plan Pyland Gaming.")
                    return
                for cmd in self.cmds_tune_gaming_plan(guid):
                    self.exec_cmd(cmd)
            self.log("Plan activo:")
            self.log(self._capture("powercfg /getactivescheme"))
            self.log("Tarea terminada. El plan queda activo al instante.")

        self.start_task(f"Plan {title}", worker)

    def do_restore_prev_plan(self):
        def worker():
            path = self._plan_file("prev_plan.txt")
            guid = ""
            try:
                if path.exists():
                    guid = path.read_text(encoding="utf-8").strip()
            except Exception:  # noqa: BLE001
                guid = ""
            if not guid:
                self.log("No hay plan anterior guardado. Se usa Equilibrado.")
                guid = PLAN_BALANCED
            self.exec_cmd(f"powercfg -setactive {guid}")
            self.log(self._capture("powercfg /getactivescheme"))

        self.start_task("Restaurar plan anterior", worker)

    # ------------------------------------------------------ delay/latencia
    def _tcp_interfaces(self):
        base = r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
        guids = []
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as key:
                index = 0
                while True:
                    try:
                        sub = winreg.EnumKey(key, index)
                    except OSError:
                        break
                    index += 1
                    try:
                        with winreg.OpenKey(key, sub) as sk:
                            ip = winreg.QueryValueEx(sk, "IPAddress")[0]
                    except OSError:
                        ip = None
                    if ip:
                        guids.append(sub)
        except Exception:  # noqa: BLE001
            pass
        return guids

    def cmds_tcp_nodelay(self):
        base = r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
        cmds = []
        for guid in self._tcp_interfaces():
            key = base + "\\" + guid
            cmds.append(reg_add(key, "TcpAckFrequency", "REG_DWORD", "1"))
            cmds.append(reg_add(key, "TCPNoDelay", "REG_DWORD", "1"))
            cmds.append(reg_add(key, "TcpDelAckTicks", "REG_DWORD", "0"))
        return cmds or ["echo No se encontraron interfaces de red activas."]

    def cmds_tcp_nodelay_revert(self):
        base = r"HKLM\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces"
        cmds = []
        for guid in self._tcp_interfaces():
            key = base + "\\" + guid
            cmds.append(reg_del(key, "TcpAckFrequency"))
            cmds.append(reg_del(key, "TCPNoDelay"))
            cmds.append(reg_del(key, "TcpDelAckTicks"))
        return cmds or ["echo No hay claves TCP que restaurar."]

    def cmds_latency_extra_revert(self):
        cmds = [reg_del(key, value) for key, value in LATENCY_EXTRA_DELETE]
        cmds += self.cmds_tcp_nodelay_revert()
        return cmds

    def do_fortnite_tweaks(self):
        cmds = regs(LATENCY_EXTRA_REGS)
        base = (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion"
                r"\Image File Execution Options")
        cmds.append(reg_add(base + r"\FortniteClient-Win64-Shipping.exe\PerfOptions",
                            "CpuPriorityClass", "REG_DWORD", "6"))
        self.run_steps("Ajustes Fortnite", [
            ("Pantalla completa, GPU de alto rendimiento y prioridad", cmds)
        ])

    def do_close_background(self):
        if not messagebox.askyesno(
                "Modo juego: cerrar segundo plano",
                "Se cerraran ahora las apps de fondo (Epic Launcher, overlay de Epic,\n"
                "OneDrive, Phone Link, Busqueda, Edge, Game Bar).\n\n"
                "No se desinstala ni se desactiva nada: solo se cierran hasta que\n"
                "las vuelvas a abrir.\n\n¿Continuar?"):
            return
        cmds = [f'taskkill /F /IM "{exe}" /T 2>nul' for exe in BACKGROUND_PROCESSES]
        self.run_steps("Modo juego", [("Cerrando aplicaciones de fondo", cmds)])

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


def _launch_advanced(root):
    for child in list(root.winfo_children()):
        child.destroy()
    app = OptimizadorApp(root)
    app.log("Consejo: crea un punto de restauracion antes de aplicar cambios.")
    return app


def main():
    set_app_user_model_id()
    if not is_admin():
        run_as_admin()
        sys.exit(0)

    root = tk.Tk()
    onboarding_gui.run(root, on_open_advanced=lambda: _launch_advanced(root))
    root.mainloop()


if __name__ == "__main__":
    main()
