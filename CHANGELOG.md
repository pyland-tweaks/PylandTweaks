# Changelog

## 5.9 - 2026-11-20

- Edición rápida de macro con tecla configurable (G por defecto): un toque edita la pieza que miras en Fortnite sin afectar la F normal.
- Nuevo onboarding al iniciar: selector de Modo Guiado/Avanzado, asistente de 15 preguntas con progreso 1/15, resumen editable, ejecución con log en tiempo real y botón de reinicio.
- Nueva pestaña Periféricos: optimizador de mouse y teclado con 129 ajustes declarativos y reversibles.
- Perfiles editables en `Recursos/Periféricos/perfiles.json`: competitivo (0 delay / mira 1:1), clásico 2/120 y valores Windows.
- Botón OPTIMIZAR PERIFÉRICOS AHORA con la misma animación de la sección Inicio y opción de restauración completa.
- Motor `perifericos.py`: registros, SystemParametersInfo, propagación y detección de dispositivos; backup antes de cada cambio.
- Versión de consola `Recursos/Periféricos/Optimizar perifericos.cmd` para aplicar o restaurar sin la GUI.
- Opción de juego en Periféricos: fija resolución de Fortnite (1680x1050 por defecto, editable en `perfiles.json`), escribe las 12 claves de resolución/pantalla completa, crea copia de seguridad y permite restaurarla. El ini queda protegido como solo lectura por defecto, se exige cerrar Fortnite y Epic Launcher antes de aplicar y se añade un botón Comprobar para detectar si el juego reescribió la resolución. Incluye guía de escalado GPU para estirado real.

- Nueva pestaña Gráficos: Potato Graphics Studio con perfiles de juego estilo NVIDIA Profile Inspector (Fortnite, CS2, GTA V, Minecraft y .exe personalizado).
- Detección automática de GPU, CPU, RAM, resolución y refresco para recomendar el nivel Potato ideal.
- Tres niveles de Potato Graphics (Ligero, Potato, Ultra Potato) con ajustes específicos por juego.
- Botón OPTIMIZAR FORTNITE AHORA con la misma animación de la sección Inicio.
- Copia de seguridad automática y restauración de archivos de configuración y claves de registro.
- Ajustes de GPU dedicada, pantalla completa exclusiva y prioridad alta de CPU por ejecutable.

## 5.8 - 2026-11-03

- Branding PylandTweaks en la aplicación, el menú por consola y el instalador.
- Nuevo logo e iconos en la ventana, la barra de tareas y el ejecutable.
- Modo temporal seguro para pausar Windows Defender y Windows Update.
- Nueva pestaña Macro: truco FF + clic automático (la segunda F queda mantenida) y modo manual de mantener F física para clicar hasta soltarla, ambos con tiempos y número de clics configurables. Incluye grabadora de teclas y clics, edición del retardo de cada paso, reproducción en bucle y parada con F8/END/SUPR. F9 termina la grabación.
- Aviso de reinicio al terminar de aplicar o revertir optimizaciones.
- Rediseño visual de la interfaz con tema oscuro.
- Build reproducible del ejecutable y del instalador.
- Documentación, licencia MIT y avisos de terceros.
