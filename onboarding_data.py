"""Datos y ejecucion del asistente inicial de PylandTweaks."""

import os
import re
import subprocess
from pathlib import Path

CREATE_NO_WINDOW = 0x08000000

BG = "#0F1115"
CARD = "#1A1D24"
CARD2 = "#14171E"
BORDER = "#2A2F3A"
FG = "#FFFFFF"
MUTED = "#A0AAB8"
ACCENT = "#3B82F6"
ACCENT_DARK = "#2563EB"
SUCCESS = "#10B981"
WARN = "#F59E0B"
DANGER = "#EF4444"
FONT = "Segoe UI"
FONT_BOLD = "Segoe UI Semibold"


def q(path):
    return f'"{path}"'


def reg_add(key, value, typ, data):
    return f'reg add "{key}" /v "{value}" /t {typ} /d "{data}" /f'


def reg_add_default(key, data=""):
    return f'reg add "{key}" /ve /t REG_SZ /d "{data}" /f'


def reg_del(key, value):
    return f'reg delete "{key}" /v "{value}" /f'


def regs(items):
    return [reg_add(*item) for item in items]


def _ps(script):
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW,
        )
        return result.stdout.decode("mbcs", errors="replace").strip()
    except Exception:
        return ""


RESTORE_POINT_CMDS = [
    'powershell.exe -NoProfile -Command "Enable-ComputerRestore -Drive \'%SystemDrive%\'"',
    'powershell.exe -NoProfile -Command "Checkpoint-Computer -Description \'PylandTweaks Onboarding\'"',
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

TELEMETRY_REGS = [
    (r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\DataCollection", "AllowTelemetry", "REG_DWORD", "0"),
    (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection", "AllowTelemetry", "REG_DWORD", "0"),
    (r"HKCU\SOFTWARE\Microsoft\Siuf\Rules", "NumberOfSIUFInPeriod", "REG_DWORD", "0"),
    (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\DataCollection", "DoNotShowFeedbackNotifications", "REG_DWORD", "1"),
    (r"HKCU\SOFTWARE\Policies\Microsoft\Windows\CloudContent", "DisableTailoredExperiencesWithDiagnosticData", "REG_DWORD", "1"),
    (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\AdvertisingInfo", "DisabledByGroupPolicy", "REG_DWORD", "1"),
    (r"HKLM\SOFTWARE\Microsoft\Windows\Windows Error Reporting", "Disabled", "REG_DWORD", "1"),
]

WIFI_REGS = [
    ("HKLM\\Software\\Microsoft\\PolicyManager\\default\\WiFi", "AllowWiFiHotSpotReporting", "REG_DWORD", "0"),
    ("HKLM\\Software\\Microsoft\\PolicyManager\\default\\WiFi", "AllowAutoConnectToWiFiSenseHotspots", "REG_DWORD", "0"),
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

PROMO_REGS = [
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-338388Enabled", "REG_DWORD", "0"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SubscribedContent-338389Enabled", "REG_DWORD", "0"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\ContentDeliveryManager", "SilentInstalledAppsEnabled", "REG_DWORD", "0"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "ShowSyncProviderNotifications", "REG_DWORD", "0"),
    (r"HKCU\SOFTWARE\Policies\Microsoft\Windows\Windows Feeds", "EnableFeeds", "REG_DWORD", "0"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Feeds", "ShellFeedsTaskbarViewMode", "REG_DWORD", "2"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", "HideSCAMeetNow", "REG_DWORD", "1"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\UserProfileEngagement", "ScoobeSystemSettingEnabled", "REG_DWORD", "0"),
]

BACKGROUND_GLOBAL_REGS = [
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications", "GlobalUserDisabled", "REG_DWORD", "1"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search", "BackgroundAppGlobalToggle", "REG_DWORD", "0"),
]

GAMEDVR_REGS = [
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR", "AppCaptureEnabled", "REG_DWORD", "0"),
    (r"HKCU\Software\Microsoft\Windows\CurrentVersion\GameDVR", "HistoricalCaptureEnabled", "REG_DWORD", "0"),
    (r"HKCU\System\GameConfigStore", "GameDVR_Enabled", "REG_DWORD", "0"),
    (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\GameDVR", "AllowGameDVR", "REG_DWORD", "0"),
    (r"HKCU\System\GameConfigStore", "GameDVR_FSEBehaviorMode", "REG_DWORD", "2"),
    (r"HKCU\System\GameConfigStore", "GameDVR_HonorUserFSEBehaviorMode", "REG_DWORD", "1"),
    (r"HKCU\System\GameConfigStore", "GameDVR_DXGIHonorFSEWindowsCompatible", "REG_DWORD", "1"),
]

MULTIMEDIA_GAMES_REGS = [
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Affinity", "REG_DWORD", "0"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Background Only", "REG_SZ", "False"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Clock Rate", "REG_DWORD", "10000"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "GPU Priority", "REG_DWORD", "8"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Priority", "REG_DWORD", "6"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "Scheduling Category", "REG_SZ", "High"),
    (r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile\Tasks\Games", "SFIO Priority", "REG_SZ", "High"),
    (r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "SystemResponsiveness", "REG_DWORD", "0"),
    (r"HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile", "NetworkThrottlingIndex", "REG_DWORD", "4294967295"),
]

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

PLAN_BALANCED = "381b4222-f694-41f0-9685-ff5bb260df2e"
PLAN_HIGH = "8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
PLAN_ULTIMATE = "e9a42b02-d5df-448d-aa00-03f14749eb61"

TEMP_CMDS = [
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
]

UPDATE_LEFTovers_CMDS = [
    'net stop wuauserv',
    'net stop UsoSvc',
    'del /S /F /Q "%WINDIR%\\SoftwareDistribution"',
    'rd /S /Q "%WINDIR%\\SoftwareDistribution"',
]

PAUSE_UPDATE_CMDS = [
    'net stop wuauserv',
    'net stop UsoSvc',
    'net stop WaaSMedicSvc',
    'sc config wuauserv start= disabled',
    'sc config UsoSvc start= disabled',
    reg_add(r"HKLM\SYSTEM\CurrentControlSet\Services\WaaSMedicSvc", "Start", "REG_DWORD", "4"),
    reg_add(r"HKLM\Software\Policies\Microsoft\Windows\WindowsUpdate\AU", "NoAutoUpdate", "REG_DWORD", "1"),
    reg_add(r"HKLM\SOFTWARE\Microsoft\Windows\WindowsUpdate", "PauseUpdatesExpirationTime", "REG_SZ", "2099-12-31T23:59:59Z"),
    reg_add(r"HKLM\SOFTWARE\Microsoft\Windows\WindowsUpdate", "PauseUpdatesFeatureExpirationTime", "REG_SZ", "2099-12-31T23:59:59Z"),
    reg_add(r"HKLM\SOFTWARE\Microsoft\Windows\WindowsUpdate", "PauseUpdatesDeadline", "REG_SZ", "2099-12-31T23:59:59Z"),
] + [f'schtasks /Change /TN "{t}" /Disable' for t in UPDATE_TASKS]

UWP_PATTERN = (
    r"(Netflix|Camera|Teams|Clipchamp|News|Weather|Xbox|GetHelp|Solitaire|"
    r"Paint|Bing|Copilot|OfficeHub|People|Phone|Maps|Music|Video|StickyNotes|"
    r"Photos|Clock|Mail|Calendar|YourPhone|GameBar|WebExperience|Painted|"
    r"WindowsMaps|Microsoft3DViewer|SketchPad|MixedReality)"
)

BAD_DRIVERS = ("security", "defender", "antivirus", "audio", "realtek", "nvidia",
               "amd", "intel", "igfx", "synaptics", "touchpad", "bthserv")


def _startup_detect_script():
    return r'''
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
'''


def _folder_startup():
    appdata = os.environ.get("APPDATA") or ""
    programdata = os.environ.get("PROGRAMDATA") or r"C:\ProgramData"
    folders = [
        ("HKCU", Path(appdata) / "Microsoft/Windows/Start Menu/Programs/Startup"),
        ("HKLM", Path(programdata) / "Microsoft/Windows/Start Menu/Programs/Startup"),
    ]
    items = []
    for scope, folder in folders:
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


def detect_startup():
    items = []
    out = _ps(_startup_detect_script())
    for line in out.splitlines():
        parts = line.split("|", 3)
        if len(parts) == 4 and parts[2].strip():
            items.append({"type": "run", "scope": parts[0], "kind": parts[1],
                          "name": parts[2].strip(), "cmd": parts[3]})
    return items + _folder_startup()


def detect_uwp(pattern=UWP_PATTERN, family=False):
    field = "PackageFamilyName" if family else "PackageFullName"
    script = (
        '$ErrorActionPreference="SilentlyContinue"\n'
        f'Get-AppxPackage | Where-Object {{ $_.Name -match \'{pattern}\' }} | '
        f'ForEach-Object {{ "$($_.Name)|$($_.{field})" }}'
    )
    out = _ps(script)
    items = []
    seen = set()
    for line in out.splitlines():
        parts = line.split("|", 1)
        if len(parts) == 2 and parts[0].strip() and parts[0].lower() not in seen:
            seen.add(parts[0].lower())
            items.append({"name": parts[0].strip(), "package": parts[1].strip()})
    return items


def detect_all():
    return {
        "startup": detect_startup(),
        "uwp": detect_uwp(),
        "uwp_background": detect_uwp(family=True),
    }


def startup_commands(item):
    if item["type"] == "folder":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or ""
        folder = str(Path(base) / "PylandTweaks" / "StartupBackup" / item["scope"])
        return [f'if not exist "{folder}" mkdir "{folder}"',
                f'move /Y "{item["cmd"]}" "{folder}\\{item["name"]}"']
    if item["type"] == "task":
        return [f'schtasks /Change /TN "{item["cmd"]}" /Disable']
    hive = "HKCU" if item["scope"] == "HKCU" else "HKLM"
    key = (f'{hive}\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\'
           f'StartupApproved\\{item["kind"]}')
    return [reg_add(key, item["name"], "REG_BINARY", "030000000000000000000000")]


def _is_critical_startup(item):
    text = f'{item.get("name", "")} {item.get("cmd", "")}'.lower()
    return any(marker in text for marker in BAD_DRIVERS)


def _option(oid, label, desc, badge="", default=False, commands=None,
            recommended=False, noop=False):
    return {
        "id": oid,
        "label": label,
        "desc": desc,
        "badge": badge,
        "default": default,
        "recommended": recommended or default,
        "noop": noop,
        "commands": list(commands or []),
    }


def _yes_no(oid, yes_desc, no_desc="No aplicar este cambio", yes_default=True,
            yes_badge="Recomendado", yes_commands=None):
    return [
        _option(oid + "_yes", "Sí, aplicarlo", yes_desc, yes_badge, yes_default,
                yes_commands, recommended=yes_default),
        _option(oid + "_no", "No, dejarlo como está", no_desc, "Seguro", not yes_default,
                [], recommended=not yes_default, noop=True),
    ]


def build_questions(detected=None):
    detected = detected or {}
    startup = detected.get("startup", [])
    uwp = detected.get("uwp", [])
    uwp_bg = detected.get("uwp_background", [])

    q2_options = []
    for index, item in enumerate(startup):
        critical = _is_critical_startup(item)
        q2_options.append(_option(
            f"startup_{index}",
            item["name"],
            f'{item["kind"]} · {item["scope"]} · {item["cmd"][:70]}',
            "Precaución" if critical else "Seguro",
            not critical,
            startup_commands(item),
            recommended=not critical,
        ))
    if not q2_options:
        q2_options.append(_option("startup_none", "No se detectaron apps de inicio",
                                  "No hay entradas Run ni accesos en la carpeta Inicio.",
                                  "Seguro", True, [], noop=True))

    q3_options = []
    for index, item in enumerate(uwp):
        q3_options.append(_option(
            f"uwp_{index}",
            item["name"],
            f'Paquete: {item["package"][:70]}',
            "Precaución",
            False,
            [f'powershell.exe -NoProfile -Command "Get-AppxPackage -Name \'{item["name"]}\' | Remove-AppxPackage"'],
        ))
    if not q3_options:
        q3_options.append(_option("uwp_none", "No se detectaron apps desinstalables",
                                  "No se encontraron apps de la Store de la lista sugerida.",
                                  "Seguro", True, [], noop=True))

    q5_options = [
        _option("bg_global", "Bloquear todas las apps en segundo plano",
                "Ajuste global de Windows para que las apps de la Store no se ejecuten de fondo.",
                "Ahorra RAM", True, regs(BACKGROUND_GLOBAL_REGS), recommended=True),
    ]
    for index, item in enumerate(uwp_bg):
        base = r"HKCU\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications"
        key = f'{base}\\{item["package"]}'
        q5_options.append(_option(
            f"bg_{index}",
            item["name"],
            f'Permiso en segundo plano de {item["package"][:55]}',
            "Ahorra RAM", False,
            [reg_add(key, "Disabled", "REG_DWORD", "1"),
             reg_add(key, "DisabledByUser", "REG_DWORD", "1")],
        ))

    questions = [
        {
            "id": "restore",
            "title": "¿Crear un punto de restauración?",
            "subtitle": "Antes de tocar el registro, Windows guarda una copia del sistema. Así puedes volver atrás si algo no te gusta. Recomendado siempre.",
            "multi": False,
            "options": _yes_no(
                "restore",
                "Windows guardará un punto llamado «PylandTweaks Onboarding». Puede tardar un poco.",
                "Solo recomendado en pruebas, VMs o equipos que vas a formatear.",
                True, "Recomendado", RESTORE_POINT_CMDS,
            ),
        },
        {
            "id": "startup",
            "title": "¿Qué apps quieres iniciar con Windows?",
            "subtitle": "Desmarca las que no necesitas al encender el PC para llegar antes al escritorio. Las marcadas se desactivarán; nada se desinstala.",
            "multi": True,
            "options": q2_options,
        },
        {
            "id": "uwp",
            "title": "¿Qué apps preinstaladas quieres quitar?",
            "subtitle": "Elimina apps de Microsoft Store que normalmente no se usan. Es reversible reinstalándolas desde la Store.",
            "multi": True,
            "options": q3_options,
        },
        {
            "id": "telemetry",
            "title": "¿Cortar telemetría y promociones de Windows?",
            "subtitle": "Menos recopilación de datos, menos avisos y menos contenido patrocinado. Windows seguirá funcionando igual.",
            "multi": True,
            "options": [
                _option("telemetry_regs", "Bloquear recopilación de datos",
                        "Claves AllowTelemetry, Siuf, AdvertisingInfo y Windows Error Reporting.",
                        "Recomendado", True, regs(TELEMETRY_REGS), recommended=True),
                _option("telemetry_tasks", "Desactivar tareas de telemetría",
                        "Tareas programadas de compatibilidad, CEIP, feedback y QueueReporting.",
                        "Ahorra RAM", True,
                        [f'schtasks /Change /TN "{t}" /Disable' for t in TELEMETRY_TASKS],
                        recommended=True),
                _option("telemetry_wifi", "Desactivar WiFi Sense",
                        "Evita compartir redes Wi-Fi y conectarse a hotspots automáticos.",
                        "Seguro", True, regs(WIFI_REGS), recommended=True),
                _option("telemetry_promos", "Quitar promociones y feeds",
                        "Content Delivery Manager, Feeds, Scoobe y notificaciones de sincronización.",
                        "Recomendado", True, regs(PROMO_REGS), recommended=True),
            ],
        },
        {
            "id": "background",
            "title": "¿Impedir que las apps funcionen en segundo plano?",
            "subtitle": "Clima, Correo u otras apps pueden seguir activas sin abrirlas. Bloquearlas ahorra RAM y batería.",
            "multi": True,
            "options": q5_options,
        },
        {
            "id": "visual",
            "title": "¿Ajustar efectos visuales para más rendimiento?",
            "subtitle": "Quita animaciones, sombras y transparencia. Muy útil en HDD y PCs con poca RAM.",
            "multi": True,
            "options": [
                _option("visual_regs", "Desactivar animaciones y sombras",
                        "DragFullWindows, MinAnimate, TaskbarAnimations, VisualFXSetting y más.",
                        "Recomendado", True, regs(VISUAL_REGS), recommended=True),
                _option("visual_transparency", "Quitar transparencia",
                        "EnableTransparency=0 en personalización de Windows.",
                        "Ahorra RAM", True,
                        [reg_add(r"HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Themes\Personalize",
                                 "EnableTransparency", "REG_DWORD", "0")],
                        recommended=True),
            ],
        },
        {
            "id": "services",
            "title": "¿Qué servicios de Windows ajustamos?",
            "subtitle": "Servicios en segundo plano que puedes desactivar o poner en manual. La indexación hace las búsquedas un poco más lentas.",
            "multi": True,
            "options": [
                _option("svc_diag", "Desactivar telemetría y diagnóstico",
                        "DiagTrack, dmwappushservice, diagsvc, DPS, WdiServiceHost y similares.",
                        "Recomendado", True,
                        [f'sc config "{s}" start= disabled' for s in (
                            "DiagTrack", "dmwappushservice", "diagsvc", "DPS",
                            "diagnosticshub.standardcollector.service", "WdiServiceHost",
                            "WdiSystemHost", "PcaSvc", "WerSvc")], recommended=True),
                _option("svc_search", "Desactivar Windows Search",
                        "WSearch deja de indexar; el buscador responderá más lento.",
                        "Ahorra RAM", True, ['sc config "WSearch" start= disabled'],
                        recommended=True),
                _option("svc_manual", "Poner servicios secundarios en manual",
                        "La lista completa de la pestaña Sistema pasa a arranque manual.",
                        "Seguro", True,
                        [f'sc config "{s}" start= demand' for s in SERVICES_MANUAL],
                        recommended=True),
                _option("svc_ucpd", "Deshabilitar UCPD",
                        "El driver UCPD bloquea cambiar apps predeterminadas y consume recursos.",
                        "Precaución", False,
                        ['sc config "UCPD" start= disabled',
                         reg_add(r"HKLM\SYSTEM\CurrentControlSet\Services\UCPD",
                                 "Start", "REG_DWORD", "4")]),
            ],
        },
        {
            "id": "web",
            "title": "¿Qué componentes web e IA sacamos?",
            "subtitle": "Widgets, Bing, WebView, Edge y Copilot pueden consumir cientos de MB aunque no los abras.",
            "multi": True,
            "options": [
                _option("web_widgets", "Quitar Widgets de la barra",
                        "TaskbarDa=0 en el Explorador de Windows 11.",
                        "Ahorra RAM", True,
                        [reg_add(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                                 "TaskbarDa", "REG_DWORD", "0")], recommended=True),
                _option("web_bing", "Quitar búsqueda web de la barra",
                        "SearchboxTaskbarMode=0; el buscador local sigue disponible.",
                        "Seguro", True,
                        [reg_add(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search",
                                 "SearchboxTaskbarMode", "REG_DWORD", "0")], recommended=True),
                _option("web_teams", "Cerrar WebView de Teams",
                        "Termina el proceso ms-teams_webview2.exe y evita su inicio automático.",
                        "Ahorra RAM", False,
                        ['taskkill /F /IM "ms-teams_webview2.exe" /T',
                         reg_add(r"HKCU\Software\Microsoft\Office\Teams",
                                 "StartUpHomePage", "REG_DWORD", "0")]),
                _option("web_edge", "Evitar que Edge arranque en segundo plano",
                        "Políticas BackgroundModeEnabled y StartupBoostEnabled + servicios edgeupdate.",
                        "Ahorra RAM", True,
                        [reg_add(r"HKLM\SOFTWARE\Policies\Microsoft\Edge",
                                 "BackgroundModeEnabled", "REG_DWORD", "0"),
                         reg_add(r"HKLM\SOFTWARE\Policies\Microsoft\Edge",
                                 "StartupBoostEnabled", "REG_DWORD", "0"),
                         'sc config "edgeupdate" start= demand',
                         'sc config "edgeupdatem" start= demand'], recommended=True),
                _option("web_copilot", "Desactivar Copilot",
                        "TurnOffWindowsCopilot=1 y oculta el botón de Copilot.",
                        "Recomendado", True,
                        [reg_add(r"HKLM\SOFTWARE\Policies\Microsoft\Windows\WindowsCopilot",
                                 "TurnOffWindowsCopilot", "REG_DWORD", "1"),
                         reg_add(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                                 "ShowCopilotButton", "REG_DWORD", "0")], recommended=True),
            ],
        },
        {
            "id": "comfort",
            "title": "Ajustes de comodidad de Windows 10/11",
            "subtitle": "Opciones clásicas para hacer el sistema más cómodo y transparente.",
            "multi": True,
            "options": [
                _option("ui_taskbar", "Ocultar botones innecesarios de la barra",
                        "Vista de tareas, búsqueda y widgets.",
                        "Seguro", True,
                        [reg_add(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                                 "ShowTaskViewButton", "REG_DWORD", "0"),
                         reg_add(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Search",
                                 "SearchboxTaskbarMode", "REG_DWORD", "0"),
                         reg_add(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                                 "TaskbarDa", "REG_DWORD", "0")], recommended=True),
                _option("ui_hidden", "Mostrar carpetas y archivos ocultos",
                        "Podrás ver AppData y archivos de sistema protegidos.",
                        "Seguro", True,
                        [reg_add(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                                 "Hidden", "REG_DWORD", "1"),
                         reg_add(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                                 "ShowSuperHidden", "REG_DWORD", "1")], recommended=True),
                _option("ui_ext", "Mostrar extensiones de archivo",
                        "Ver .exe, .txt, .jpg en lugar de solo el nombre.",
                        "Seguro", True,
                        [reg_add(r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced",
                                 "HideFileExt", "REG_DWORD", "0")], recommended=True),
                _option("ui_classic_menu", "Menú contextual clásico en Windows 11",
                        "Recupera el menú derecho completo de Windows 10.",
                        "Seguro", False,
                        [reg_add_default(
                            r"HKCU\Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32",
                            "")]),
            ],
        },
        {
            "id": "gamedvr",
            "title": "¿Desactivar la grabación en segundo plano?",
            "subtitle": "Xbox Game Bar y Game DVR capturan clips continuamente y consumen RAM y GPU.",
            "multi": False,
            "options": _yes_no("gamedvr",
                               "Desactiva AppCaptureEnabled, GameDVR_Enabled y AllowGameDVR.",
                               "Si usas Game Bar para grabar, elige esta opción.",
                               True, "Recomendado", regs(GAMEDVR_REGS)),
        },
        {
            "id": "multimedia",
            "title": "¿Usar el perfil multimedia para juegos?",
            "subtitle": "Da prioridad alta al proceso de juegos en el subsistema multimedia. El impacto real en FPS suele ser mínimo o marginal.",
            "multi": False,
            "options": _yes_no("multimedia",
                               "Claves MMCSS de Tasks\\Games y SystemResponsiveness.",
                               "No cambia nada del perfil multimedia.",
                               True, "Seguro", regs(MULTIMEDIA_GAMES_REGS)),
        },
        {
            "id": "power",
            "title": "¿Activar el plan de máximo rendimiento?",
            "subtitle": "El CPU trabajará sin límites de ahorro. En portátiles agota la batería mucho más rápido.",
            "multi": False,
            "options": [
                _option("power_high", "Alto rendimiento",
                        "Plan clásico de Windows para escritorio.",
                        "Recomendado en escritorio", True,
                        [f'powercfg -setactive {PLAN_HIGH}'], recommended=True),
                _option("power_ultimate", "Máximo rendimiento (Ultimate)",
                        "Plan oculto de Windows con CPU al 100%.",
                        "Precaución", False,
                        [f'powercfg -setactive {PLAN_ULTIMATE}']),
                _option("power_gaming", "Pyland Gaming (baja latencia)",
                        "CPU al 100%, ASPM off, disk idle off y USB suspend off.",
                        "Precaución", False,
                        [f'powercfg -setactive {PLAN_HIGH}',
                         'powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMIN 100',
                         'powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PROCTHROTTLEMAX 100',
                         'powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR CPMINCORES 100',
                         'powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR CPMAXCORES 100',
                         'powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR PERFBOOSTMODE 2',
                         'powercfg -setacvalueindex SCHEME_CURRENT SUB_PROCESSOR IDLEDISABLE 1',
                         'powercfg -setacvalueindex SCHEME_CURRENT SUB_PCIEXPRESS ASPM 0',
                         'powercfg -setacvalueindex SCHEME_CURRENT SUB_DISK DISKIDLE 0',
                         'powercfg -setactive SCHEME_CURRENT']),
                _option("power_none", "Mantener el plan actual",
                        "No se modifica ningún plan de energía.",
                        "Seguro", False, [], noop=True),
            ],
        },
        {
            "id": "usbpci",
            "title": "¿Desactivar ahorro de energía de USB y PCI?",
            "subtitle": "Evita que Windows suspenda puertos o buses, causando micro-tirones o desconexiones de periféricos.",
            "multi": True,
            "options": [
                _option("usb_suspend", "Desactivar suspensión selectiva USB",
                        "USBSELECTIVESUSPEND=0 en AC y DC.",
                        "Recomendado", True,
                        ['powercfg -setacvalueindex SCHEME_CURRENT SUB_USB USBSELECTIVESUSPEND 0',
                         'powercfg -setdcvalueindex SCHEME_CURRENT SUB_USB USBSELECTIVESUSPEND 0',
                         'powercfg -setactive SCHEME_CURRENT'], recommended=True),
                _option("pci_aspm", "Desactivar ASPM de PCI Express",
                        "ASPM=0 en AC y DC para reducir latencia.",
                        "Recomendado", True,
                        ['powercfg -setacvalueindex SCHEME_CURRENT SUB_PCIEXPRESS ASPM 0',
                         'powercfg -setdcvalueindex SCHEME_CURRENT SUB_PCIEXPRESS ASPM 0',
                         'powercfg -setactive SCHEME_CURRENT'], recommended=True),
            ],
        },
        {
            "id": "cleanup",
            "title": "¿Borrar temporales y restos de actualizaciones?",
            "subtitle": "Libera espacio eliminando caché, Prefetch y logs. No borra archivos personales.",
            "multi": True,
            "options": [
                _option("clean_temp", "Borrar %temp%, Prefetch y logs",
                        "Carpetas temporales de Windows y del usuario.",
                        "Recomendado", True, TEMP_CMDS, recommended=True),
                _option("clean_updates", "Limpiar restos de Windows Update",
                        "Carpeta SoftwareDistribution y servicios de Update.",
                        "Recomendado", True, UPDATE_LEFTovers_CMDS, recommended=True),
                _option("clean_dns", "Limpiar caché DNS",
                        "Resuelve problemas de red y conexión.",
                        "Seguro", True, ["ipconfig /flushdns"], recommended=True),
            ],
        },
        {
            "id": "update",
            "title": "¿Pausar Windows Update hasta 2099?",
            "subtitle": "Evita picos del 100% de CPU por actualizaciones en equipos muy limitados. ATENCIÓN: detiene las actualizaciones de seguridad del sistema.",
            "multi": False,
            "options": [
                _option("update_pause", "Sí, pausar hasta 2099",
                        "Servicios, tareas y caducidad de pausa fijada al 2099.",
                        "Precaución", False, PAUSE_UPDATE_CMDS),
                _option("update_keep", "No, mantener actualizaciones",
                        "Windows Update seguirá funcionando con normalidad.",
                        "Recomendado", True, [], noop=True, recommended=True),
            ],
        },
    ]
    return questions


def default_answers(questions, recommended=False):
    answers = {}
    for question in questions:
        answers[question["id"]] = [
            option["id"] for option in question["options"]
            if option["id"] and ((option["recommended"] if recommended else option["default"]))
        ]
    return answers


def build_plan(questions, answers):
    steps = []
    for index, question in enumerate(questions, 1):
        selected = set(answers.get(question["id"], []))
        for option in question["options"]:
            if option["id"] in selected and option["commands"]:
                steps.append((f'{index}. {question["title"]} · {option["label"]}',
                              list(option["commands"])))
    return steps


def summary_rows(questions, answers):
    rows = []
    for index, question in enumerate(questions, 1):
        selected = set(answers.get(question["id"], []))
        labels = [option["label"] for option in question["options"]
                  if option["id"] in selected and not option["noop"]]
        if not labels:
            labels = ["Sin cambios"]
        rows.append((index - 1, question["title"], ", ".join(labels)))
    return rows


def count_commands(steps):
    return sum(len(commands) for _, commands in steps)
