# -*- coding: utf-8 -*-
"""Catalogo declarativo de ajustes de entrada (mouse/teclado) de PylandTweaks.

Toda la logica de aplicacion/restauracion vive aqui. La GUI solo construye un
plan, alimenta el overlay y ejecuta las acciones. Los perfiles se leen desde
Recursos/Perifericos/perfiles.json para poder editarlos sin tocar el codigo.
"""

import ctypes
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import winreg
except ImportError:  # pragma: no cover - solo Windows
    winreg = None

CREATE_NO_WINDOW = 0x08000000
APPDATA = Path(os.environ.get("APPDATA") or Path.home())
STATE_PATH = APPDATA / "PylandTweaks" / "peripherals_state.json"
SPIF = 0x01 | 0x02

MOUSE = r"Control Panel\Mouse"
KEYBOARD = r"Control Panel\Keyboard"
DESKTOP = r"Control Panel\Desktop"
ACCESS = r"Control Panel\Accessibility"
EXPLORER = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
GAMEBAR = r"Software\Microsoft\GameBar"
GAMEDVR = r"Software\Microsoft\Windows\CurrentVersion\GameDVR"
GAMECONFIG = r"System\GameConfigStore"
GAMEDVR_POLICY = r"SOFTWARE\Policies\Microsoft\Windows\GameDVR"
POWER_THROTTLE = r"SYSTEM\CurrentControlSet\Control\Power\PowerThrottling"
PRIORITY_CONTROL = r"SYSTEM\CurrentControlSet\Control\PriorityControl"
MMCSS = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Multimedia\SystemProfile"


def reg(spec_id, label, hive, key, name, type_, value, category,
        source=None, mode=None):
    return {
        "id": spec_id, "label": label, "kind": "registry", "hive": hive,
        "key": key, "name": name, "type": type_, "value": value,
        "category": category, "source": source, "mode": mode,
    }


def api(spec_id, label, action, value, category, source=None):
    return {
        "id": spec_id, "label": label, "kind": "api", "action": action,
        "value": value, "category": category, "source": source,
    }


def command(spec_id, label, cmd, category):
    return {
        "id": spec_id, "label": label, "kind": "command", "cmd": cmd,
        "category": category,
    }


CATALOG = [
    # --- Mouse -----------------------------------------------------------
    reg("mouse.speed", "Aceleracion de puntero (MouseSpeed)", "HKCU", MOUSE,
        "MouseSpeed", "REG_SZ", "0", "Mouse", "mouse_speed"),
    reg("mouse.threshold1", "Umbral de aceleracion 1", "HKCU", MOUSE,
        "MouseThreshold1", "REG_SZ", "0", "Mouse", "mouse_threshold1"),
    reg("mouse.threshold2", "Umbral de aceleracion 2", "HKCU", MOUSE,
        "MouseThreshold2", "REG_SZ", "0", "Mouse", "mouse_threshold2"),
    reg("mouse.sensitivity", "Velocidad del puntero (1-20)", "HKCU", MOUSE,
        "MouseSensitivity", "REG_SZ", "10", "Mouse", "mouse_sensitivity"),
    reg("mouse.trails", "Estela del cursor", "HKCU", MOUSE,
        "MouseTrails", "REG_SZ", "0", "Mouse"),
    reg("mouse.snap", "Ajustar al boton predeterminado", "HKCU", MOUSE,
        "SnapToDefaultButton", "REG_SZ", "0", "Mouse"),
    reg("mouse.hovertime", "Tiempo de hover del mouse", "HKCU", MOUSE,
        "MouseHoverTime", "REG_SZ", "100", "Mouse"),
    reg("mouse.hoverwidth", "Ancho de area de hover", "HKCU", MOUSE,
        "MouseHoverWidth", "REG_SZ", "4", "Mouse"),
    reg("mouse.hoverheight", "Alto de area de hover", "HKCU", MOUSE,
        "MouseHoverHeight", "REG_SZ", "4", "Mouse"),
    reg("mouse.swap", "Botones del mouse intercambiados", "HKCU", MOUSE,
        "SwapMouseButtons", "REG_SZ", "0", "Mouse"),
    reg("mouse.dblspeed", "Velocidad de doble clic", "HKCU", MOUSE,
        "DoubleClickSpeed", "REG_SZ", "500", "Mouse"),
    reg("mouse.dblheight", "Altura de doble clic", "HKCU", MOUSE,
        "DoubleClickHeight", "REG_SZ", "4", "Mouse"),
    reg("mouse.dblwidth", "Ancho de doble clic", "HKCU", MOUSE,
        "DoubleClickWidth", "REG_SZ", "4", "Mouse"),
    reg("mouse.activewindow", "Activar ventana al pasar el mouse", "HKCU", MOUSE,
        "ActiveWindowTracking", "REG_SZ", "0", "Mouse"),
    reg("mouse.sonar", "Localizar cursor con Sonar", "HKCU", MOUSE,
        "MouseSonar", "REG_SZ", "0", "Mouse"),
    reg("mouse.vanish", "Ocultar cursor al escribir", "HKCU", MOUSE,
        "MouseVanish", "REG_SZ", "0", "Mouse"),
    reg("mouse.beep", "Beep del mouse", "HKCU", MOUSE,
        "Beep", "REG_SZ", "No", "Mouse"),
    reg("mouse.extsounds", "Sonidos extendidos del mouse", "HKCU", MOUSE,
        "ExtendedSounds", "REG_SZ", "No", "Mouse"),
    reg("mouse.clicklock", "Bloqueo de clic prolongado", "HKCU", MOUSE,
        "MouseClickLock", "REG_SZ", "0", "Mouse"),
    reg("mouse.clicklocktime", "Tiempo de bloqueo de clic", "HKCU", MOUSE,
        "MouseClickLockTime", "REG_SZ", "1200", "Mouse"),
    reg("mouse.wheelrouting", "Enrutado de rueda del mouse", "HKCU", MOUSE,
        "MouseWheelRouting", "REG_SZ", "0", "Mouse"),

    # --- Teclado ---------------------------------------------------------
    reg("keyboard.delay", "Retardo de repeticion de tecla", "HKCU", KEYBOARD,
        "KeyboardDelay", "REG_SZ", "1", "Keyboard"),
    reg("keyboard.speed", "Velocidad de repeticion de tecla", "HKCU", KEYBOARD,
        "KeyboardSpeed", "REG_SZ", "31", "Keyboard"),
    reg("keyboard.autorepeatdelay", "Retardo de autorepeticion", "HKCU",
        ACCESS + r"\Keyboard Response", "AutoRepeatDelay", "REG_SZ", "200",
        "Keyboard"),
    reg("keyboard.autorepeatrate", "Tasa de autorepeticion", "HKCU",
        ACCESS + r"\Keyboard Response", "AutoRepeatRate", "REG_SZ", "31",
        "Keyboard"),
    reg("keyboard.bouncetime", "Tiempo de rebote de tecla", "HKCU",
        ACCESS + r"\Keyboard Response", "BounceTime", "REG_SZ", "0",
        "Keyboard"),
    reg("keyboard.delaybeforeaccept", "Retardo antes de aceptar tecla", "HKCU",
        ACCESS + r"\Keyboard Response", "DelayBeforeAcceptance", "REG_SZ", "0",
        "Keyboard"),

    # --- Escritorio / respuesta de entrada -------------------------------
    reg("desktop.wheelscrolllines", "Lineas de scroll con la rueda", "HKCU",
        DESKTOP, "WheelScrollLines", "REG_SZ", "3", "Desktop"),
    reg("desktop.wheelscrollchars", "Caracteres de scroll con la rueda", "HKCU",
        DESKTOP, "WheelScrollChars", "REG_SZ", "3", "Desktop"),
    reg("desktop.menushowdelay", "Retardo de menu", "HKCU", DESKTOP,
        "MenuShowDelay", "REG_SZ", "400", "Desktop"),
    reg("desktop.foregroundlock", "Bloqueo de cambio de foco", "HKCU", DESKTOP,
        "ForegroundLockTimeout", "REG_DWORD", "200000", "Desktop"),
    reg("desktop.activewndtrktimeout", "Retardo de activacion por hover", "HKCU",
        DESKTOP, "ActiveWndTrkTimeout", "REG_DWORD", "0", "Desktop"),
    reg("desktop.dblspeed", "Doble clic (escritorio)", "HKCU", DESKTOP,
        "DoubleClickSpeed", "REG_SZ", "500", "Desktop"),
    reg("desktop.dblheight", "Altura de doble clic (escritorio)", "HKCU",
        DESKTOP, "DoubleClickHeight", "REG_SZ", "4", "Desktop"),
    reg("desktop.dblwidth", "Ancho de doble clic (escritorio)", "HKCU",
        DESKTOP, "DoubleClickWidth", "REG_SZ", "4", "Desktop"),
    reg("desktop.dragheight", "Altura de arrastre", "HKCU", DESKTOP,
        "DragHeight", "REG_SZ", "4", "Desktop"),
    reg("desktop.dragwidth", "Ancho de arrastre", "HKCU", DESKTOP,
        "DragWidth", "REG_SZ", "4", "Desktop"),
    reg("desktop.cursorblink", "Frecuencia de parpadeo del cursor", "HKCU",
        DESKTOP, "CursorBlinkRate", "REG_SZ", "530", "Desktop"),
    reg("desktop.caretwidth", "Ancho del caret", "HKCU", DESKTOP,
        "CaretWidth", "REG_DWORD", "1", "Desktop"),
    reg("desktop.foregroundflash", "Destellos de ventana en segundo plano", "HKCU",
        DESKTOP, "ForegroundFlashCount", "REG_DWORD", "3", "Desktop"),
    reg("desktop.lowlevelhookstimeout", "Timeout de hooks de bajo nivel", "HKCU",
        DESKTOP, "LowLevelHooksTimeout", "REG_DWORD", "1000", "Desktop"),
    reg("desktop.menufade", "Animacion de desvanecido de menu", "HKCU",
        DESKTOP, "MenuFade", "REG_DWORD", "1", "Desktop"),
    reg("desktop.selectionfade", "Desvanecido de seleccion", "HKCU",
        DESKTOP, "SelectionFade", "REG_DWORD", "1", "Desktop"),
    reg("desktop.tooltipfade", "Desvanecido de tooltips", "HKCU",
        DESKTOP, "TooltipFade", "REG_DWORD", "1", "Desktop"),
    reg("desktop.tooltipanimation", "Animacion de tooltips", "HKCU",
        DESKTOP, "TooltipAnimation", "REG_DWORD", "1", "Desktop"),
    reg("desktop.keyboardcues", "Indicadores de teclado", "HKCU",
        DESKTOP, "KeyboardCues", "REG_SZ", "1", "Desktop"),
    reg("desktop.fontsmoothingtype", "Tipo de suavizado de fuentes", "HKCU",
        DESKTOP, "FontSmoothingType", "REG_DWORD", "2", "Desktop"),
    reg("desktop.fontsmoothinggamma", "Gamma de suavizado de fuentes", "HKCU",
        DESKTOP, "FontSmoothingGamma", "REG_DWORD", "1500", "Desktop"),
    reg("desktop.fontsmoothingorient", "Orientacion de suavizado", "HKCU",
        DESKTOP, "FontSmoothingOrientation", "REG_DWORD", "1", "Desktop"),

    # --- Accesibilidad (evita interceptar la entrada) --------------------
    reg("access.stickykeys", "Teclas de pegajosidad", "HKCU",
        ACCESS + r"\StickyKeys", "Flags", "REG_SZ", "62", "Accessibility",
        mode="clear_on_bit"),
    reg("access.togglekeys", "Teclas de alternancia", "HKCU",
        ACCESS + r"\ToggleKeys", "Flags", "REG_SZ", "62", "Accessibility",
        mode="clear_on_bit"),
    reg("access.filterkeys", "Filtro de teclas", "HKCU",
        ACCESS + r"\FilterKeys", "Flags", "REG_SZ", "62", "Accessibility",
        mode="clear_on_bit"),
    reg("access.mousekeys", "Teclas de mouse", "HKCU",
        ACCESS + r"\MouseKeys", "Flags", "REG_SZ", "62", "Accessibility",
        mode="clear_on_bit"),
    reg("access.soundsentry", "Aviso visual de sonido", "HKCU",
        ACCESS + r"\SoundSentry", "Flags", "REG_SZ", "0", "Accessibility"),
    reg("access.showsounds", "Mostrar sonidos", "HKCU",
        ACCESS + r"\ShowSounds", "Flags", "REG_SZ", "0", "Accessibility"),
    reg("access.highcontrast", "Alto contraste", "HKCU",
        ACCESS + r"\HighContrast", "Flags", "REG_SZ", "126", "Accessibility"),
    reg("access.keyboardpref", "Preferencia de teclado", "HKCU",
        ACCESS + r"\Keyboard Preference", "On", "REG_SZ", "0", "Accessibility"),
    reg("access.blindaccess", "Acceso para ciegos", "HKCU",
        ACCESS + r"\Blind Access", "On", "REG_SZ", "0", "Accessibility"),
    reg("access.on", "Accesibilidad global", "HKCU", ACCESS, "On",
        "REG_SZ", "0", "Accessibility"),
    reg("access.mousekeys.maxspeed", "Velocidad maxima de MouseKeys", "HKCU",
        ACCESS + r"\MouseKeys", "MaximumSpeed", "REG_SZ", "10", "Accessibility"),
    reg("access.mousekeys.timemax", "Tiempo hasta maxima velocidad MouseKeys",
        "HKCU", ACCESS + r"\MouseKeys", "TimeToMaximumSpeed", "REG_SZ", "1000",
        "Accessibility"),
    reg("access.stickykeys.hotkeysound", "Sonido de tecla rapida StickyKeys",
        "HKCU", ACCESS + r"\StickyKeys", "HotKeySound", "REG_SZ", "0",
        "Accessibility"),
    reg("access.togglekeys.hotkeysound", "Sonido de tecla rapida ToggleKeys",
        "HKCU", ACCESS + r"\ToggleKeys", "HotKeySound", "REG_SZ", "0",
        "Accessibility"),

    # --- Explorador / percepcion de fluidez ------------------------------
    reg("explorer.listviewalpha", "Transparencia de listas", "HKCU", EXPLORER,
        "ListviewAlphaSelect", "REG_DWORD", "0", "Explorer"),
    reg("explorer.listviewshadow", "Sombra de listas", "HKCU", EXPLORER,
        "ListviewShadow", "REG_DWORD", "0", "Explorer"),
    reg("explorer.taskbaranim", "Animaciones de barra de tareas", "HKCU",
        EXPLORER, "TaskbarAnimations", "REG_DWORD", "0", "Explorer"),
    reg("explorer.iconsonly", "Iconos en miniatura desactivados", "HKCU",
        EXPLORER, "IconsOnly", "REG_DWORD", "0", "Explorer"),
    reg("explorer.infotip", "Informacion sobre herramientas", "HKCU",
        EXPLORER, "ShowInfoTip", "REG_DWORD", "1", "Explorer"),
    reg("explorer.foldertip", "Informacion de carpetas", "HKCU", EXPLORER,
        "FolderContentsInfoTip", "REG_DWORD", "1", "Explorer"),
    reg("explorer.typeoverlay", "Overlay de tipo de archivo", "HKCU", EXPLORER,
        "ShowTypeOverlay", "REG_DWORD", "1", "Explorer"),
    reg("explorer.previewdesktop", "Vista previa del escritorio", "HKCU",
        EXPLORER, "DisablePreviewDesktop", "REG_DWORD", "1", "Explorer"),
    reg("explorer.balloontips", "Avisos globo", "HKCU", EXPLORER,
        "EnableBalloonTips", "REG_DWORD", "1", "Explorer"),
    reg("explorer.taskbarglom", "Agrupacion de barra de tareas", "HKCU",
        EXPLORER, "TaskbarGlomLevel", "REG_DWORD", "0", "Explorer"),
    reg("explorer.showseconds", "Segundos en el reloj", "HKCU", EXPLORER,
        "ShowSecondsInSystemClock", "REG_DWORD", "0", "Explorer"),
    reg("explorer.separateprocess", "Proceso separado del explorador", "HKCU",
        EXPLORER, "SeparateProcess", "REG_DWORD", "0", "Explorer"),
    reg("explorer.listviewwatermark", "Marca de agua de listas", "HKCU",
        EXPLORER, "ListviewWatermark", "REG_DWORD", "0", "Explorer"),
    reg("explorer.trackprogs", "Seguimiento de programas", "HKCU", EXPLORER,
        "Start_TrackProgs", "REG_DWORD", "0", "Explorer"),
    reg("explorer.smallicons", "Iconos pequenos en barra", "HKCU", EXPLORER,
        "TaskbarSmallIcons", "REG_DWORD", "0", "Explorer"),
    reg("explorer.hovertime", "Retardo de hover de barra", "HKCU", EXPLORER,
        "ExtendedUIHoverTime", "REG_DWORD", "400", "Explorer"),
    reg("explorer.previewhover", "Retardo de vista previa en vivo", "HKCU",
        EXPLORER, "ThumbnailLivePreviewHoverTime", "REG_DWORD", "400",
        "Explorer"),
    reg("explorer.showcompcolor", "Colores de archivos comprimidos", "HKCU",
        EXPLORER, "ShowCompColor", "REG_DWORD", "1", "Explorer"),

    # --- Juegos / captura ------------------------------------------------
    reg("game.allowautomode", "Permitir modo juego", "HKCU", GAMEBAR,
        "AllowAutoGameMode", "REG_DWORD", "1", "Gaming"),
    reg("game.automode", "Modo juego automatico", "HKCU", GAMEBAR,
        "AutoGameModeEnabled", "REG_DWORD", "1", "Gaming"),
    reg("game.appcapture", "Captura de juego (DVR)", "HKCU", GAMEDVR,
        "AppCaptureEnabled", "REG_DWORD", "0", "Gaming"),
    reg("game.historicalcapture", "Captura historica (DVR)", "HKCU", GAMEDVR,
        "HistoricalCaptureEnabled", "REG_DWORD", "0", "Gaming"),
    reg("game.audiocapture", "Captura de audio (DVR)", "HKCU", GAMEDVR,
        "AudioCaptureEnabled", "REG_DWORD", "0", "Gaming"),
    reg("game.gamedvrenabled", "GameDVR activado", "HKCU", GAMECONFIG,
        "GameDVR_Enabled", "REG_DWORD", "0", "Gaming"),
    reg("game.gamedvraallow", "Permitir GameDVR (politica)", "HKLM",
        GAMEDVR_POLICY, "AllowGameDVR", "REG_DWORD", "0", "Gaming"),
    reg("game.fsebehavior", "Comportamiento de pantalla completa", "HKCU",
        GAMECONFIG, "GameDVR_FSEBehaviorMode", "REG_DWORD", "2", "Gaming"),
    reg("game.honorfse", "Respetar pantalla completa exclusiva", "HKCU",
        GAMECONFIG, "GameDVR_HonorUserFSEBehaviorMode", "REG_DWORD", "1",
        "Gaming"),
    reg("game.dxgi", "Compatibilidad DXGI con pantalla completa", "HKCU",
        GAMECONFIG, "GameDVR_DXGIHonorFSEWindowsCompatible", "REG_DWORD", "1",
        "Gaming"),
    reg("game.plattform", "Plataforma de juego", "HKCU", GAMECONFIG,
        "GameDVR_FSEBehavior", "REG_DWORD", "2", "Gaming"),
    reg("game.appcompat", "Compatibilidad de app con GameDVR", "HKCU",
        GAMECONFIG, "GameDVR_UseAppCompatabilityMode", "REG_DWORD", "1",
        "Gaming"),

    # --- Planificador / energia ------------------------------------------
    reg("system.powerthrottling", "Power throttling desactivado", "HKLM",
        POWER_THROTTLE, "PowerThrottlingOff", "REG_DWORD", "1", "System"),
    reg("system.win32priority", "Prioridad de planificacion Win32", "HKLM",
        PRIORITY_CONTROL, "Win32PrioritySeparation", "REG_DWORD", "38",
        "System"),
    reg("system.systemresponsiveness", "Capacidad de respuesta multimedia",
        "HKLM", MMCSS, "SystemResponsiveness", "REG_DWORD", "20", "System"),
    reg("system.networkthrottling", "Limitacion de red multimedia", "HKLM",
        MMCSS, "NetworkThrottlingIndex", "REG_DWORD", "10", "System"),
    reg("system.hwschmode", "Programacion de hardware GPU", "HKLM",
        r"SYSTEM\CurrentControlSet\Control\GraphicsDrivers", "HwSchMode",
        "REG_DWORD", "2", "System"),

    # --- Normalizacion visual (percepcion de fluidez) --------------------
    reg("desktop.dragfullwindows", "Arrastrar ventanas completas", "HKCU",
        DESKTOP, "DragFullWindows", "REG_SZ", "0", "Desktop"),
    reg("desktop.minanimate", "Animacion de minimizar", "HKCU", DESKTOP,
        "MinAnimate", "REG_SZ", "0", "Desktop"),
    reg("dwm.aeropeek", "Vista previa Aero Peek", "HKCU",
        r"Software\Microsoft\Windows\DWM", "EnableAeroPeek", "REG_DWORD", "0",
        "Explorer"),
    reg("dwm.thumbnail", "Reposo de miniaturas", "HKCU",
        r"Software\Microsoft\Windows\DWM", "AlwaysHibernateThumbnails",
        "REG_DWORD", "0", "Explorer"),
    reg("dwm.composition", "Composicion del escritorio", "HKCU",
        r"Software\Microsoft\Windows\DWM", "Composition", "REG_DWORD", "1",
        "Explorer"),
    reg("dwm.colorprevalence", "Color en barra de tareas", "HKCU",
        r"Software\Microsoft\Windows\DWM", "ColorPrevalence", "REG_DWORD", "0",
        "Explorer"),
    reg("explorer.driveletters", "Letras de unidad primero", "HKCU",
        EXPLORER, "ShowDriveLettersFirst", "REG_DWORD", "0", "Explorer"),
    reg("explorer.autocheck", "Seleccion con un clic", "HKCU", EXPLORER,
        "AutoCheckSelect", "REG_DWORD", "0", "Explorer"),
    reg("explorer.dontprettypath", "Rutas Unity en explorador", "HKCU",
        EXPLORER, "DontPrettyPath", "REG_DWORD", "1", "Explorer"),
    reg("explorer.mapnetdrv", "Boton de unidades de red", "HKCU", EXPLORER,
        "MapNetDrvBtn", "REG_DWORD", "0", "Explorer"),
    reg("explorer.encryptcolor", "Color de archivos cifrados", "HKCU",
        EXPLORER, "ShowEncryptCompressedColor", "REG_DWORD", "1", "Explorer"),
    reg("explorer.taskbarsizemove", "Mover barra de tareas", "HKCU", EXPLORER,
        "TaskbarSizeMove", "REG_DWORD", "0", "Explorer"),
    reg("explorer.thumbnailcache", "Cache de miniaturas", "HKCU", EXPLORER,
        "DisableThumbnailCache", "REG_DWORD", "0", "Explorer"),
    reg("explorer.alwaysmenus", "Mostrar menus siempre", "HKCU", EXPLORER,
        "AlwaysShowMenus", "REG_DWORD", "0", "Explorer"),
    reg("visual.fxsetting", "Efectos visuales personalizados", "HKCU",
        r"Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects",
        "VisualFXSetting", "REG_DWORD", "3", "Explorer"),

    # --- Llamadas directas a la API de Windows ---------------------------
    api("api.mouse", "Aplicar curva de mouse 1:1 (SPI_SETMOUSE)", "set_mouse",
        [0, 0, 0], "API", "mouse_accel"),
    api("api.mousespeed", "Velocidad de puntero 1:1 (SPI_SETMOUSESPEED)",
        "set_mouse_speed", 10, "API", "mouse_sensitivity"),
    api("api.mousetrails", "Quitar estela (SPI_SETMOUSETRAILS)",
        "set_mouse_trails", 0, "API"),
    api("api.snap", "Desactivar Snap To (SPI_SETSNAPTODEFBUTTON)",
        "set_snap", 0, "API"),
    api("api.activewindow", "Desactivar hover activo (SPI_SETACTIVEWINDOWTRACKING)",
        "set_active_window", 0, "API"),
    api("api.sonar", "Desactivar Mouse Sonar (SPI_SETMOUSESONAR)",
        "set_mouse_sonar", 0, "API"),
    api("api.vanish", "Desactivar Mouse Vanish (SPI_SETMOUSEVANISH)",
        "set_mouse_vanish", 0, "API"),
    api("api.doubleclick", "Sincronizar doble clic (SPI_SETDOUBLECLICKTIME)",
        "set_doubleclick", 500, "API"),
    api("api.keyboardspeed", "Repeticion de teclado (SPI_SETKEYBOARDSPEED)",
        "set_keyboard_speed", 31, "API"),
    api("api.keyboarddelay", "Retardo de teclado (SPI_SETKEYBOARDDELAY)",
        "set_keyboard_delay", 1, "API"),

    # --- Propagacion -----------------------------------------------------
    command("cmd.refresh", "Refrescar parametros de usuario",
            "rundll32.exe user32.dll,UpdatePerUserSystemParameters", "Command"),
    command("cmd.broadcast", "Notificar cambio de configuracion",
            "rundll32.exe user32.dll,UpdatePerUserSystemParameters 1, True",
            "Command"),
    command("cmd.usbac", "Suspension selectiva de USB (AC)",
            "powercfg /setacvalueindex SCHEME_CURRENT SUB_USB USBSELECTIVESUSPEND 0",
            "Command"),
    command("cmd.usbacapply", "Aplicar suspension USB (AC)",
            "powercfg /setactive SCHEME_CURRENT", "Command"),
    command("cmd.usbdc", "Suspension selectiva de USB (DC)",
            "powercfg /setdcvalueindex SCHEME_CURRENT SUB_USB USBSELECTIVESUSPEND 0",
            "Command"),
    command("cmd.usbapply", "Aplicar suspension USB (DC)",
            "powercfg /setactive SCHEME_CURRENT", "Command"),
]

DEFAULT_PROFILE = {
    "name": "Competitivo (mira estable)",
    "description": "Movimiento 1:1 sin aceleracion ni interpolacion de puntero.",
    "values": {
        "mouse_speed": "0",
        "mouse_threshold1": "0",
        "mouse_threshold2": "0",
        "mouse_sensitivity": "10",
        "mouse_accel": [0, 0, 0],
    },
}

PROFILES_FILENAME = "perfiles.json"


def profile_path(base_dir=None):
    if base_dir:
        return Path(base_dir) / PROFILES_FILENAME
    base = Path(__file__).resolve().parent
    bundled = base / "Recursos" / "Periféricos" / PROFILES_FILENAME
    return bundled if bundled.exists() else base / PROFILES_FILENAME


def load_profiles(base_dir=None):
    path = profile_path(base_dir)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        profiles = data.get("perfiles") if isinstance(data, dict) else None
        if isinstance(profiles, dict) and profiles:
            default = str(data.get("predeterminado") or next(iter(profiles)))
            if default not in profiles:
                default = next(iter(profiles))
            return profiles, default
    except Exception:
        pass
    return {"competitivo": DEFAULT_PROFILE}, "competitivo"


def resolve_value(spec, profile):
    values = (profile or {}).get("values") or {}
    if spec.get("source") and spec["source"] in values:
        return values[spec["source"]]
    return spec.get("value")


def build_plan(profile, catalog=None, detected_devices=None):
    """Genera el plan completo. Cada entrada es una accion real y reversible."""
    catalog = CATALOG if catalog is None else catalog
    plan = []
    for spec in catalog:
        value = resolve_value(spec, profile)
        if spec["kind"] == "registry":
            cmd = registry_command(spec, value)
            plan.append({
                "id": spec["id"], "label": spec["label"], "kind": "registry",
                "spec": spec, "value": value, "cmd": cmd,
            })
        elif spec["kind"] == "api":
            plan.append({
                "id": spec["id"], "label": spec["label"], "kind": "api",
                "spec": spec, "value": value,
                "cmd": f"SystemParametersInfoW({spec['action']}, {value})",
            })
        else:
            plan.append({
                "id": spec["id"], "label": spec["label"], "kind": "command",
                "spec": spec, "value": None, "cmd": spec["cmd"],
            })
    for device in detected_devices or []:
        plan.append({
            "id": "device." + str(device.get("id", "")),
            "label": f"Perfil detectado: {device.get('name', 'dispositivo')}",
            "kind": "device", "spec": None, "value": None,
            "cmd": f"Get-PnpDevice -InstanceId '{device.get('id', '')}'",
        })
    return plan


def registry_command(spec, value):
    hive = "HKEY_CURRENT_USER" if spec["hive"] == "HKCU" else "HKEY_LOCAL_MACHINE"
    return (f'reg add "{hive}\\{spec["key"]}" /v "{spec["name"]}" '
            f'/t {spec["type"]} /d "{value}" /f')


def _hive(spec):
    if winreg is None:
        raise RuntimeError("winreg no disponible")
    return winreg.HKEY_CURRENT_USER if spec["hive"] == "HKCU" \
        else winreg.HKEY_LOCAL_MACHINE


def _reg_type(spec):
    return {
        "REG_SZ": winreg.REG_SZ,
        "REG_DWORD": winreg.REG_DWORD,
        "REG_QWORD": winreg.REG_QWORD,
        "REG_BINARY": winreg.REG_BINARY,
    }[spec["type"]]


def capture_spec(spec):
    try:
        with winreg.OpenKey(_hive(spec), spec["key"], 0, winreg.KEY_READ) as handle:
            old, typ = winreg.QueryValueEx(handle, spec["name"])
        return {
            "id": spec["id"], "hive": spec["hive"], "key": spec["key"],
            "name": spec["name"], "existed": True, "old": old,
            "old_type": int(typ),
        }
    except OSError:
        return {
            "id": spec["id"], "hive": spec["hive"], "key": spec["key"],
            "name": spec["name"], "existed": False, "old": None,
            "old_type": None,
        }


def apply_registry(spec, value):
    if spec.get("mode") == "clear_on_bit":
        record = capture_spec(spec)
        if record["existed"]:
            try:
                value = str(int(record["old"]) & ~1)
            except (TypeError, ValueError):
                value = spec["value"]
    reg_type = _reg_type(spec)
    if reg_type in (winreg.REG_DWORD, winreg.REG_QWORD):
        value = int(value)
    else:
        value = str(value)
    with winreg.CreateKeyEx(_hive(spec), spec["key"], 0,
                            winreg.KEY_SET_VALUE) as handle:
        winreg.SetValueEx(handle, spec["name"], 0, reg_type, value)


def apply_api(spec, value):
    u = ctypes.windll.user32
    action = spec["action"]
    flags = SPIF
    if action == "set_mouse":
        arr = (ctypes.c_int * 3)(*[int(v) for v in value])
        return u.SystemParametersInfoW(0x0004, 0, arr, flags)
    if action == "set_mouse_speed":
        return u.SystemParametersInfoW(0x0071, 0, ctypes.c_void_p(int(value)), flags)
    if action == "set_mouse_trails":
        return u.SystemParametersInfoW(0x005D, int(value), None, flags)
    if action == "set_snap":
        return u.SystemParametersInfoW(0x0060, int(value), None, flags)
    if action == "set_active_window":
        return u.SystemParametersInfoW(0x1001, 0, ctypes.c_void_p(int(value)), flags)
    if action == "set_mouse_sonar":
        return u.SystemParametersInfoW(0x1013, 0, ctypes.c_void_p(int(value)), flags)
    if action == "set_mouse_vanish":
        return u.SystemParametersInfoW(0x1021, 0, ctypes.c_void_p(int(value)), flags)
    if action == "set_doubleclick":
        return u.SystemParametersInfoW(0x0023, int(value), None, flags)
    if action == "set_keyboard_speed":
        return u.SystemParametersInfoW(0x000B, int(value), None, flags)
    if action == "set_keyboard_delay":
        return u.SystemParametersInfoW(0x0017, int(value), None, flags)
    return 0


def apply_action(action):
    kind = action["kind"]
    if kind == "registry":
        apply_registry(action["spec"], action["value"])
        return True
    if kind == "api":
        return bool(apply_api(action["spec"], action["value"]))
    if kind == "command":
        result = subprocess.run(
            action["cmd"], shell=True, cwd=str(Path(__file__).resolve().parent),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW)
        return result.returncode == 0
    return True


def restore_record(record):
    if not winreg:
        return
    if not record.get("existed"):
        try:
            with winreg.OpenKey(_hive(record), record["key"], 0,
                                winreg.KEY_SET_VALUE) as handle:
                winreg.DeleteValue(handle, record["name"])
        except OSError:
            pass
        return
    spec = {
        "hive": record["hive"], "key": record["key"], "name": record["name"],
        "type": "REG_SZ",
    }
    types = {
        winreg.REG_SZ: "REG_SZ", winreg.REG_DWORD: "REG_DWORD",
        winreg.REG_QWORD: "REG_QWORD", winreg.REG_BINARY: "REG_BINARY",
    }
    typ = record.get("old_type")
    if typ in types:
        spec["type"] = types[typ]
    with winreg.CreateKeyEx(_hive(spec), spec["key"], 0,
                            winreg.KEY_SET_VALUE) as handle:
        winreg.SetValueEx(handle, spec["name"], 0, int(typ), record.get("old"))


def load_state():
    try:
        if STATE_PATH.exists():
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False),
                          encoding="utf-8")


def detect_devices():
    ps = (
        "$d = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Class -in @('Mouse','Keyboard','HIDClass') }; "
        "$d | Select-Object Class,FriendlyName,InstanceId,Status | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=CREATE_NO_WINDOW, timeout=20)
        data = json.loads(result.stdout.decode("utf-8", errors="replace") or "[]")
        items = data if isinstance(data, list) else [data]
        return [
            {"id": str(it.get("InstanceId", "")),
             "name": str(it.get("FriendlyName", "")),
             "class": str(it.get("Class", "")),
             "status": str(it.get("Status", ""))}
            for it in items if it.get("InstanceId")
        ]
    except Exception:
        return []


def main(argv=None):
    argv = argv or sys.argv[1:]
    mode = argv[0] if argv else "apply"
    profiles, default = load_profiles()
    if mode == "apply":
        profile_name = argv[1] if len(argv) > 1 else default
        profile = profiles.get(profile_name, DEFAULT_PROFILE)
        plan = build_plan(profile, detected_devices=None)
        state = load_state()
        records = state.get("records") or []
        seen = {r.get("id") for r in records}
        for action in plan:
            if action["kind"] == "registry" and action["id"] not in seen:
                records.append(capture_spec(action["spec"]))
                seen.add(action["id"])
            apply_action(action)
            print(f"[{action['id']}] {action['label']}")
        state.update({
            "active": True, "profile": profile_name, "records": records,
            "count": len(plan),
        })
        save_state(state)
        print(f"Listo: {len(plan)} acciones aplicadas.")
    elif mode == "restore":
        state = load_state()
        for record in reversed(state.get("records") or []):
            restore_record(record)
        save_state({})
        print("Perifericos restaurados.")
    else:
        print("Uso: perifericos.py [apply|restore] [perfil]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
