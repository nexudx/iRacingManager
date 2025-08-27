[English](#english) | [Deutsch](#deutsch) | [Español](#español) | [中文 (简体)](#chinese-simplified) | [Français](#français) | [Русский](#russian)

---
## English {#english}

# iRacing Manager

A utility for automatically starting and stopping programs for the iRacing environment. When iRacing is closed, all associated programs are automatically closed as well.

## Overview

The iRacing Manager is a tool to simplify the workflow when starting and stopping iRacing and its helper applications. The program:

- Starts all helper applications defined in the configuration file (automatically minimized)
- Detects programs that start directly in the system tray and skips unnecessary minimization attempts
- Provides special handling for programs with splash screens or complex startup sequences
- Starts iRacing as the last program (not minimized)
- Continuously monitors the iRacing process
- Automatically terminates all helper applications when iRacing is closed

## Requirements

- Windows operating system
- Python 3.6 or higher
- The following Python libraries:
  - psutil (for process monitoring)
  - pywin32 (for Windows-specific functions like window minimization)

## Installation

1. Make sure Python 3.6 or higher is installed.
2. Install the required libraries:

```
py -m pip install psutil pywin32
```

3. Download all files of the iRacing Manager and place them in a directory.
4. Adjust the `config.json` according to your needs (copy from `config/example_config.json`).
5. Create a desktop shortcut with the following target:

```
pythonw <path_to_directory>\src\core\iracing_manager.py
```
or
```
py -m pythonw <path_to_directory>\src\core\iracing_manager.py
```

> **Note:** Use `pythonw` instead of `python` to hide the command line window.

## Configuration

The configuration is done via the `config.json` file. Here you can define the programs to start, their paths, startup parameters, and special behavior options.

### Configuration Example:

```json
{
  "programs": [
    {
      "name": "Oculus Client",
      "path": "C:\\Program Files\\Oculus\\Support\\oculus-client\\OculusClient.exe",
      "arguments": "",
      "has_splash_screen": true
    },
    {
      "name": "SimHub",
      "path": "C:\\Program Files (x86)\\SimHub\\SimHubWPF.exe",
      "arguments": "",
      "systray_only": true
    },
    {
      "name": "Garage61",
      "path": "C:\\Users\\username\\AppData\\Roaming\\garage61-install\\garage61-agent.exe",
      "arguments": "",
      "systray_only": true
    },
    {
      "name": "iRacing",
      "path": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\iRacing\\ui\\iRacingUI.exe",
      "arguments": "",
      "is_main": true
    }
  ]
}
```

### Configuration Parameters:

- `name`: Name of the program (used for logging)
- `path`: Full path to the executable
- `arguments`: Command line parameters for the program (optional)
- `is_main`: `true` for iRacing, `false` or not present for helper applications
- `systray_only`: `true` for programs that only start in the system tray (like SimHub)
- `has_splash_screen`: `true` for programs with a splash screen (like Oculus Client)

> **Important:** One program should be marked with `"is_main": true`. This is typically iRacing. This program is monitored, and when it is terminated, all other programs will also be terminated.

### Special Handling for Specific Programs

The iRacing Manager provides special handling for certain program types:

- **System Tray Programs** (`"systray_only": true`): Programs like SimHub or Garage61 that start directly in the system tray are detected and not unnecessarily minimized.

- **Programs with Splash Screen** (`"has_splash_screen": true`): Programs like the Oculus Client that have a splash screen and then open a main window are handled with special monitoring logic that ensures both the splash screen and the main window are minimized.

- **Oculus Client**: The Oculus Client has particularly aggressive handling since it sometimes opens multiple windows or the main window may appear with a delay. The iRacing Manager uses a special monitoring thread to find and minimize all windows of the Oculus Client.

## Usage

1. Double-click the desktop shortcut to start the iRacing Manager.
2. The iRacing Manager automatically starts all configured programs.
3. When you're done, simply close iRacing, and all other programs will be automatically terminated.

## Troubleshooting

### Common Problems

#### Programs Not Being Minimized

- **General**: Make sure you have installed the `pywin32` library:
  ```
  pip install pywin32
  ```

- **System Tray Programs**: If programs like SimHub should not be minimized, set `"systray_only": true` in the configuration.

- **Programs with Splash Screen**: If programs open a new window after startup, set `"has_splash_screen": true` in the configuration.

- **Oculus Client**: The Oculus Client has special handling. If problems occur, start the iRacing Manager with `py src/core/iracing_manager.py` from the command line to see debugging information.

#### iRacing Not Being Detected or Monitored

Check if the correct path to iRacing is specified in the `config.json` and if `"is_main": true` is set for iRacing.

#### Helper Applications Not Being Terminated

When iRacing is closed, you can check the log to see if the monitoring worked properly. Start the iRacing Manager from the command line:

```
py src/core/iracing_manager.py
```

This will show detailed log messages that can help with diagnosis.

## Development

The iRacing Manager consists of several modules organized in directories:

### Directory Structure
```
iRacingManager/
├── src/              # Source code
│   ├── core/         # Core functionality
│   │   ├── iracing_manager.py
│   │   ├── iracing_watcher.py
│   │   └── process_manager.py
│   ├── ui/           # User interface
│   │   └── console_ui.py
│   ├── utils/        # Utility functions
│   │   ├── process_utils.py
│   │   ├── config_manager.py
│   │   └── window_manager.py
│   └── vr/           # VR/Oculus-specific code
│       └── oculus_handler.py
├── config/           # Configuration files
│   └── example_config.json
└── docs/             # Documentation
    └── README.md
```

#### Module Responsibilities:

- **src/core/iracing_manager.py**: Coordinates the entire process, starts programs in the correct order, and responds to the termination of iRacing.
- **src/core/iracing_watcher.py**: Continuously monitors the iRacing process and notifies the manager when iRacing is terminated.
- **src/core/process_manager.py**: Takes care of starting, minimizing, and terminating programs, with special handling for certain program types.
- **src/ui/console_ui.py**: Provides the console user interface with framed logging display.
- **src/utils/config_manager.py**: Reads and validates the configuration file, provides helper functions for retrieving program configurations.
- **src/utils/process_utils.py**: Common utilities for process management across modules.
- **src/utils/window_manager.py**: Handles finding and manipulating application windows.
- **src/vr/oculus_handler.py**: Specialized handling for Oculus/VR processes.
- **tests/mock_process.py**: Provides mock subprocess and psutil implementations.
- **tests/mock_windows.py**: Provides mock Windows API implementations.
- **tests/test_runner.py**: Contains test cases for the iRacing Manager.
- **tests/mock_main.py**: Runs the iRacing Manager with mock components.

If you want to make changes or extensions, you can adapt the corresponding modules.

## License

This project is released under the MIT license.

---
## Deutsch {#deutsch}

# iRacing Manager

Ein Dienstprogramm zum automatischen Starten und Stoppen von Programmen für die iRacing-Umgebung. Wenn iRacing geschlossen wird, werden auch alle zugehörigen Programme automatisch geschlossen.

## Übersicht

Der iRacing Manager ist ein Werkzeug zur Vereinfachung des Workflows beim Starten und Stoppen von iRacing und seinen Hilfsanwendungen. Das Programm:

- Startet alle in der Konfigurationsdatei definierten Hilfsanwendungen (automatisch minimiert)
- Erkennt Programme, die direkt im System-Tray starten, und überspringt unnötige Minimierungsversuche
- Bietet spezielle Behandlung für Programme mit Splash-Screens oder komplexen Startsequenzen
- Startet iRacing als letztes Programm (nicht minimiert)
- Überwacht kontinuierlich den iRacing-Prozess
- Beendet automatisch alle Hilfsanwendungen, wenn iRacing geschlossen wird

## Anforderungen

- Windows-Betriebssystem
- Python 3.6 oder höher
- Die folgenden Python-Bibliotheken:
  - psutil (zur Prozessüberwachung)
  - pywin32 (für Windows-spezifische Funktionen wie Fensterminimierung)

## Installation

1. Stellen Sie sicher, dass Python 3.6 oder höher installiert ist.
2. Installieren Sie die erforderlichen Bibliotheken:

```
py -m pip install psutil pywin32
```

3. Laden Sie alle Dateien des iRacing Managers herunter und legen Sie sie in einem Verzeichnis ab.
4. Passen Sie die `config.json` Ihren Bedürfnissen an (kopieren Sie von `config/example_config.json`).
5. Erstellen Sie eine Desktop-Verknüpfung mit folgendem Ziel:

```
pythonw <Pfad_zum_Verzeichnis>\src\core\iracing_manager.py
```
oder
```
py -m pythonw <Pfad_zum_Verzeichnis>\src\core\iracing_manager.py
```

> **Hinweis:** Verwenden Sie `pythonw` anstelle von `python`, um das Kommandozeilenfenster auszublenden.

## Konfiguration

Die Konfiguration erfolgt über die Datei `config.json`. Hier können Sie die zu startenden Programme, deren Pfade, Startparameter und spezielle Verhaltensoptionen definieren.

### Konfigurationsbeispiel:

```json
{
  "programs": [
    {
      "name": "Oculus Client",
      "path": "C:\\Program Files\\Oculus\\Support\\oculus-client\\OculusClient.exe",
      "arguments": "",
      "has_splash_screen": true
    },
    {
      "name": "SimHub",
      "path": "C:\\Program Files (x86)\\SimHub\\SimHubWPF.exe",
      "arguments": "",
      "systray_only": true
    },
    {
      "name": "Garage61",
      "path": "C:\\Users\\username\\AppData\\Roaming\\garage61-install\\garage61-agent.exe",
      "arguments": "",
      "systray_only": true
    },
    {
      "name": "iRacing",
      "path": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\iRacing\\ui\\iRacingUI.exe",
      "arguments": "",
      "is_main": true
    }
  ]
}
```

### Konfigurationsparameter:

- `name`: Name des Programms (wird für die Protokollierung verwendet)
- `path`: Vollständiger Pfad zur ausführbaren Datei
- `arguments`: Kommandozeilenparameter für das Programm (optional)
- `is_main`: `true` für iRacing, `false` oder nicht vorhanden für Hilfsanwendungen
- `systray_only`: `true` für Programme, die nur im System-Tray starten (wie SimHub)
- `has_splash_screen`: `true` für Programme mit einem Splash-Screen (wie Oculus Client)

> **Wichtig:** Ein Programm sollte mit `"is_main": true` gekennzeichnet sein. Dies ist typischerweise iRacing. Dieses Programm wird überwacht, und wenn es beendet wird, werden auch alle anderen Programme beendet.

### Spezielle Behandlung für bestimmte Programme

Der iRacing Manager bietet eine spezielle Behandlung für bestimmte Programmtypen:

- **System-Tray-Programme** (`"systray_only": true`): Programme wie SimHub oder Garage61, die direkt im System-Tray starten, werden erkannt und nicht unnötig minimiert.

- **Programme mit Splash-Screen** (`"has_splash_screen": true`): Programme wie der Oculus Client, die einen Splash-Screen haben und dann ein Hauptfenster öffnen, werden mit einer speziellen Überwachungslogik behandelt, die sicherstellt, dass sowohl der Splash-Screen als auch das Hauptfenster minimiert werden.

- **Oculus Client**: Der Oculus Client hat eine besonders aggressive Behandlung, da er manchmal mehrere Fenster öffnet oder das Hauptfenster mit Verzögerung erscheinen kann. Der iRacing Manager verwendet einen speziellen Überwachungsthread, um alle Fenster des Oculus Clients zu finden und zu minimieren.

## Verwendung

1. Doppelklicken Sie auf die Desktop-Verknüpfung, um den iRacing Manager zu starten.
2. Der iRacing Manager startet automatisch alle konfigurierten Programme.
3. Wenn Sie fertig sind, schließen Sie einfach iRacing, und alle anderen Programme werden automatisch beendet.

## Fehlerbehebung

### Häufige Probleme

#### Programme werden nicht minimiert

- **Allgemein**: Stellen Sie sicher, dass Sie die `pywin32`-Bibliothek installiert haben:
  ```
  pip install pywin32
  ```

- **System-Tray-Programme**: Wenn Programme wie SimHub nicht minimiert werden sollen, setzen Sie `"systray_only": true` in der Konfiguration.

- **Programme mit Splash-Screen**: Wenn Programme nach dem Start ein neues Fenster öffnen, setzen Sie `"has_splash_screen": true` in der Konfiguration.

- **Oculus Client**: Der Oculus Client hat eine spezielle Behandlung. Bei Problemen starten Sie den iRacing Manager mit `py src/core/iracing_manager.py` von der Kommandozeile, um Debugging-Informationen anzuzeigen.

#### iRacing wird nicht erkannt oder überwacht

Überprüfen Sie, ob der korrekte Pfad zu iRacing in der `config.json` angegeben ist und ob `"is_main": true` für iRacing gesetzt ist.

#### Hilfsanwendungen werden nicht beendet

Wenn iRacing geschlossen wird, können Sie das Protokoll überprüfen, um festzustellen, ob die Überwachung ordnungsgemäß funktioniert hat. Starten Sie den iRacing Manager von der Kommandozeile:

```
py src/core/iracing_manager.py
```

Dies zeigt detaillierte Protokollmeldungen an, die bei der Diagnose helfen können.

## Entwicklung

Der iRacing Manager besteht aus mehreren Modulen, die in Verzeichnissen organisiert sind:

### Verzeichnisstruktur
```
iRacingManager/
├── src/              # Quellcode
│   ├── core/         # Kernfunktionalität
│   │   ├── iracing_manager.py
│   │   ├── iracing_watcher.py
│   │   └── process_manager.py
│   ├── ui/           # Benutzeroberfläche
│   │   └── console_ui.py
│   ├── utils/        # Dienstprogrammfunktionen
│   │   ├── process_utils.py
│   │   ├── config_manager.py
│   │   └── window_manager.py
│   └── vr/           # VR/Oculus-spezifischer Code
│       └── oculus_handler.py
├── config/           # Konfigurationsdateien
│   └── example_config.json
└── docs/             # Dokumentation
    └── README.md
```

#### Modulverantwortlichkeiten:

- **src/core/iracing_manager.py**: Koordiniert den gesamten Prozess, startet Programme in der richtigen Reihenfolge und reagiert auf die Beendigung von iRacing.
- **src/core/iracing_watcher.py**: Überwacht kontinuierlich den iRacing-Prozess und benachrichtigt den Manager, wenn iRacing beendet wird.
- **src/core/process_manager.py**: Kümmert sich um das Starten, Minimieren und Beenden von Programmen, mit spezieller Behandlung für bestimmte Programmtypen.
- **src/ui/console_ui.py**: Stellt die Konsolenbenutzeroberfläche mit gerahmter Protokollanzeige bereit.
- **src/utils/config_manager.py**: Liest und validiert die Konfigurationsdatei, stellt Hilfsfunktionen zum Abrufen von Programmkonfigurationen bereit.
- **src/utils/process_utils.py**: Allgemeine Dienstprogramme für die Prozessverwaltung über Module hinweg.
- **src/utils/window_manager.py**: Behandelt das Suchen und Manipulieren von Anwendungsfenstern.
- **src/vr/oculus_handler.py**: Spezialisierte Behandlung für Oculus/VR-Prozesse.
- **tests/mock_process.py**: Stellt Mock-Subprozess- und psutil-Implementierungen bereit.
- **tests/mock_windows.py**: Stellt Mock-Windows-API-Implementierungen bereit.
- **tests/test_runner.py**: Enthält Testfälle für den iRacing Manager.
- **tests/mock_main.py**: Führt den iRacing Manager mit Mock-Komponenten aus.

Wenn Sie Änderungen oder Erweiterungen vornehmen möchten, können Sie die entsprechenden Module anpassen.

## Lizenz

Dieses Projekt wird unter der MIT-Lizenz veröffentlicht.

---
## Español {#español}

# iRacing Manager

Una utilidad para iniciar y detener automáticamente programas para el entorno de iRacing. Cuando iRacing se cierra, todos los programas asociados también se cierran automáticamente.

## Resumen

El iRacing Manager es una herramienta para simplificar el flujo de trabajo al iniciar y detener iRacing y sus aplicaciones auxiliares. El programa:

- Inicia todas las aplicaciones auxiliares definidas en el archivo de configuración (minimizadas automáticamente)
- Detecta programas que se inician directamente en la bandeja del sistema y omite intentos innecesarios de minimización
- Proporciona un manejo especial para programas con pantallas de bienvenida o secuencias de inicio complejas
- Inicia iRacing como último programa (no minimizado)
- Supervisa continuamente el proceso de iRacing
- Termina automáticamente todas las aplicaciones auxiliares cuando se cierra iRacing

## Requisitos

- Sistema operativo Windows
- Python 3.6 o superior
- Las siguientes bibliotecas de Python:
  - psutil (para la supervisión de procesos)
  - pywin32 (para funciones específicas de Windows como la minimización de ventanas)

## Instalación

1. Asegúrese de que Python 3.6 o superior esté instalado.
2. Instale las bibliotecas requeridas:

```
py -m pip install psutil pywin32
```

3. Descargue todos los archivos del iRacing Manager y colóquelos en un directorio.
4. Ajuste el archivo `config.json` según sus necesidades (copie de `config/example_config.json`).
5. Cree un acceso directo en el escritorio con el siguiente destino:

```
pythonw <ruta_al_directorio>\src\core\iracing_manager.py
```
o
```
py -m pythonw <ruta_al_directorio>\src\core\iracing_manager.py
```

> **Nota:** Use `pythonw` en lugar de `python` para ocultar la ventana de la línea de comandos.

## Configuración

La configuración se realiza a través del archivo `config.json`. Aquí puede definir los programas a iniciar, sus rutas, parámetros de inicio y opciones de comportamiento especiales.

### Ejemplo de Configuración:

```json
{
  "programs": [
    {
      "name": "Oculus Client",
      "path": "C:\\Program Files\\Oculus\\Support\\oculus-client\\OculusClient.exe",
      "arguments": "",
      "has_splash_screen": true
    },
    {
      "name": "SimHub",
      "path": "C:\\Program Files (x86)\\SimHub\\SimHubWPF.exe",
      "arguments": "",
      "systray_only": true
    },
    {
      "name": "Garage61",
      "path": "C:\\Users\\username\\AppData\\Roaming\\garage61-install\\garage61-agent.exe",
      "arguments": "",
      "systray_only": true
    },
    {
      "name": "iRacing",
      "path": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\iRacing\\ui\\iRacingUI.exe",
      "arguments": "",
      "is_main": true
    }
  ]
}
```

### Parámetros de Configuración:

- `name`: Nombre del programa (utilizado para el registro)
- `path`: Ruta completa al ejecutable
- `arguments`: Parámetros de línea de comandos para el programa (opcional)
- `is_main`: `true` para iRacing, `false` o no presente para aplicaciones auxiliares
- `systray_only`: `true` para programas que solo se inician en la bandeja del sistema (como SimHub)
- `has_splash_screen`: `true` para programas con pantalla de bienvenida (como Oculus Client)

> **Importante:** Un programa debe estar marcado con `"is_main": true`. Este es típicamente iRacing. Este programa se supervisa y, cuando se termina, todos los demás programas también se terminarán.

### Manejo Especial para Programas Específicos

El iRacing Manager proporciona un manejo especial para ciertos tipos de programas:

- **Programas de la Bandeja del Sistema** (`"systray_only": true`): Programas como SimHub o Garage61 que se inician directamente en la bandeja del sistema son detectados y no se minimizan innecesariamente.

- **Programas con Pantalla de Bienvenida** (`"has_splash_screen": true`): Programas como el Cliente Oculus que tienen una pantalla de bienvenida y luego abren una ventana principal se manejan con una lógica de supervisión especial que asegura que tanto la pantalla de bienvenida como la ventana principal se minimicen.

- **Cliente Oculus**: El Cliente Oculus tiene un manejo particularmente agresivo ya que a veces abre múltiples ventanas o la ventana principal puede aparecer con retraso. El iRacing Manager utiliza un hilo de supervisión especial para encontrar y minimizar todas las ventanas del Cliente Oculus.

## Uso

1. Haga doble clic en el acceso directo del escritorio para iniciar el iRacing Manager.
2. El iRacing Manager inicia automáticamente todos los programas configurados.
3. Cuando haya terminado, simplemente cierre iRacing y todos los demás programas se terminarán automáticamente.

## Solución de Problemas

### Problemas Comunes

#### Programas que no se minimizan

- **General**: Asegúrese de haber instalado la biblioteca `pywin32`:
  ```
  pip install pywin32
  ```

- **Programas de la Bandeja del Sistema**: Si programas como SimHub no deben minimizarse, establezca `"systray_only": true` en la configuración.

- **Programas con Pantalla de Bienvenida**: Si los programas abren una nueva ventana después del inicio, establezca `"has_splash_screen": true` en la configuración.

- **Cliente Oculus**: El Cliente Oculus tiene un manejo especial. Si ocurren problemas, inicie el iRacing Manager con `py src/core/iracing_manager.py` desde la línea de comandos para ver información de depuración.

#### iRacing no se detecta o supervisa

Compruebe si la ruta correcta a iRacing está especificada en `config.json` y si `"is_main": true` está configurado para iRacing.

#### Aplicaciones auxiliares que no se terminan

Cuando iRacing se cierra, puede verificar el registro para ver si la supervisión funcionó correctamente. Inicie el iRacing Manager desde la línea de comandos:

```
py src/core/iracing_manager.py
```

Esto mostrará mensajes de registro detallados que pueden ayudar con el diagnóstico.

## Desarrollo

El iRacing Manager consta de varios módulos organizados en directorios:

### Estructura de Directorios
```
iRacingManager/
├── src/              # Código fuente
│   ├── core/         # Funcionalidad principal
│   │   ├── iracing_manager.py
│   │   ├── iracing_watcher.py
│   │   └── process_manager.py
│   ├── ui/           # Interfaz de usuario
│   │   └── console_ui.py
│   ├── utils/        # Funciones de utilidad
│   │   ├── process_utils.py
│   │   ├── config_manager.py
│   │   └── window_manager.py
│   └── vr/           # Código específico de VR/Oculus
│       └── oculus_handler.py
├── config/           # Archivos de configuración
│   └── example_config.json
└── docs/             # Documentación
    └── README.md
```

#### Responsabilidades del Módulo:

- **src/core/iracing_manager.py**: Coordina todo el proceso, inicia los programas en el orden correcto y responde a la terminación de iRacing.
- **src/core/iracing_watcher.py**: Supervisa continuamente el proceso de iRacing y notifica al administrador cuando iRacing se termina.
- **src/core/process_manager.py**: Se encarga de iniciar, minimizar y terminar programas, con un manejo especial para ciertos tipos de programas.
- **src/ui/console_ui.py**: Proporciona la interfaz de usuario de la consola con visualización de registro enmarcada.
- **src/utils/config_manager.py**: Lee y valida el archivo de configuración, proporciona funciones auxiliares para recuperar configuraciones de programas.
- **src/utils/process_utils.py**: Utilidades comunes para la gestión de procesos en todos los módulos.
- **src/utils/window_manager.py**: Maneja la búsqueda y manipulación de ventanas de aplicaciones.
- **src/vr/oculus_handler.py**: Manejo especializado para procesos de Oculus/VR.
- **tests/mock_process.py**: Proporciona implementaciones simuladas de subprocesos y psutil.
- **tests/mock_windows.py**: Proporciona implementaciones simuladas de la API de Windows.
- **tests/test_runner.py**: Contiene casos de prueba para el iRacing Manager.
- **tests/mock_main.py**: Ejecuta el iRacing Manager con componentes simulados.

Si desea realizar cambios o extensiones, puede adaptar los módulos correspondientes.

## Licencia

Este proyecto se publica bajo la licencia MIT.

---
## 中文 (简体) {#chinese-simplified}

# iRacing Manager

一个用于自动启动和停止 iRacing 环境程序的实用工具。当 iRacing 关闭时，所有相关程序也会自动关闭。

## 概述

iRacing Manager 是一个简化启动和停止 iRacing 及其辅助应用程序工作流程的工具。该程序：

- 启动配置文件中定义的所有辅助应用程序（自动最小化）
- 检测直接在系统托盘中启动的程序，并跳过不必要的最小化尝试
- 为带有启动画面或复杂启动序列的程序提供特殊处理
- 最后启动 iRacing 程序（不最小化）
- 持续监控 iRacing 进程
- 当 iRacing 关闭时自动终止所有辅助应用程序

## 要求

- Windows 操作系统
- Python 3.6 或更高版本
- 以下 Python 库：
  - psutil (用于进程监控)
  - pywin32 (用于 Windows 特定功能，如窗口最小化)

## 安装

1. 确保已安装 Python 3.6 或更高版本。
2. 安装所需的库：

```
py -m pip install psutil pywin32
```

3. 下载 iRacing Manager 的所有文件并将它们放在一个目录中。
4. 根据您的需求调整 `config.json` (从 `config/example_config.json` 复制)。
5. 创建一个桌面快捷方式，其目标如下：

```
pythonw <目录路径>\src\core\iracing_manager.py
```
或
```
py -m pythonw <目录路径>\src\core\iracing_manager.py
```

> **注意：** 使用 `pythonw` 而不是 `python` 来隐藏命令行窗口。

## 配置

通过 `config.json` 文件进行配置。您可以在此处定义要启动的程序、它们的路径、启动参数和特殊行为选项。

### 配置示例：

```json
{
  "programs": [
    {
      "name": "Oculus Client",
      "path": "C:\\Program Files\\Oculus\\Support\\oculus-client\\OculusClient.exe",
      "arguments": "",
      "has_splash_screen": true
    },
    {
      "name": "SimHub",
      "path": "C:\\Program Files (x86)\\SimHub\\SimHubWPF.exe",
      "arguments": "",
      "systray_only": true
    },
    {
      "name": "Garage61",
      "path": "C:\\Users\\username\\AppData\\Roaming\\garage61-install\\garage61-agent.exe",
      "arguments": "",
      "systray_only": true
    },
    {
      "name": "iRacing",
      "path": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\iRacing\\ui\\iRacingUI.exe",
      "arguments": "",
      "is_main": true
    }
  ]
}
```

### 配置参数：

- `name`: 程序名称 (用于日志记录)
- `path`: 可执行文件的完整路径
- `arguments`: 程序的命令行参数 (可选)
- `is_main`: 对于 iRacing 为 `true`，对于辅助应用程序为 `false` 或不存在
- `systray_only`: `true` 适用于仅在系统托盘中启动的程序 (如 SimHub)
- `has_splash_screen`: `true` 适用于带有启动画面的程序 (如 Oculus Client)

> **重要提示：** 应将一个程序标记为 `"is_main": true`。这通常是 iRacing。此程序受到监控，当它终止时，所有其他程序也将终止。

### 特定程序的特殊处理

iRacing Manager 为某些类型的程序提供特殊处理：

- **系统托盘程序** (`"systray_only": true`): 像 SimHub 或 Garage61 这样直接在系统托盘中启动的程序会被检测到，并且不会不必要地最小化。

- **带有启动画面的程序** (`"has_splash_screen": true`): 像 Oculus Client 这样具有启动画面然后打开主窗口的程序，会使用特殊的监控逻辑进行处理，以确保启动画面和主窗口都被最小化。

- **Oculus Client**: Oculus Client 的处理特别积极，因为它有时会打开多个窗口，或者主窗口可能会延迟出现。iRacing Manager 使用一个特殊的监控线程来查找并最小化 Oculus Client 的所有窗口。

## 使用方法

1. 双击桌面快捷方式以启动 iRacing Manager。
2. iRacing Manager 会自动启动所有已配置的程序。
3. 完成后，只需关闭 iRacing，所有其他程序将自动终止。

## 故障排除

### 常见问题

#### 程序未最小化

- **常规**: 确保已安装 `pywin32` 库：
  ```
  pip install pywin32
  ```

- **系统托盘程序**: 如果像 SimHub 这样的程序不应最小化，请在配置中设置 `"systray_only": true`。

- **带有启动画面的程序**: 如果程序在启动后打开一个新窗口，请在配置中设置 `"has_splash_screen": true`。

- **Oculus Client**: Oculus Client 有特殊处理。如果出现问题，请从命令行使用 `py src/core/iracing_manager.py` 启动 iRacing Manager 以查看调试信息。

#### 未检测到或监控 iRacing

检查 `config.json` 中是否指定了正确的 iRacing 路径，以及是否为 iRacing 设置了 `"is_main": true`。

#### 辅助应用程序未终止

当 iRacing 关闭时，您可以检查日志以查看监控是否正常工作。从命令行启动 iRacing Manager：

```
py src/core/iracing_manager.py
```

这将显示详细的日志消息，有助于诊断。

## 开发

iRacing Manager 由多个模块组成，这些模块组织在目录中：

### 目录结构
```
iRacingManager/
├── src/              # 源代码
│   ├── core/         #核心功能
│   │   ├── iracing_manager.py
│   │   ├── iracing_watcher.py
│   │   └── process_manager.py
│   ├── ui/           # 用户界面
│   │   └── console_ui.py
│   ├── utils/        # 实用功能
│   │   ├── process_utils.py
│   │   ├── config_manager.py
│   │   └── window_manager.py
│   └── vr/           # VR/Oculus特定代码
│       └── oculus_handler.py
├── config/           # 配置文件
│   └── example_config.json
└── docs/             # 文档
    └── README.md
```

#### 模块职责：

- **src/core/iracing_manager.py**: 协调整个过程，按正确顺序启动程序，并响应 iRacing 的终止。
- **src/core/iracing_watcher.py**: 持续监控 iRacing 进程，并在 iRacing 终止时通知管理器。
- **src/core/process_manager.py**: 负责启动、最小化和终止程序，并对某些类型的程序进行特殊处理。
- **src/ui/console_ui.py**: 提供带有框架日志显示的控制台用户界面。
- **src/utils/config_manager.py**: 读取并验证配置文件，提供用于检索程序配置的辅助函数。
- **src/utils/process_utils.py**:跨模块的进程管理通用实用程序。
- **src/utils/window_manager.py**: 处理查找和操作应用程序窗口。
- **src/vr/oculus_handler.py**: Oculus/VR 进程的专门处理。
- **tests/mock_process.py**: 提供模拟子进程和 psutil 实现。
- **tests/mock_windows.py**: 提供模拟 Windows API 实现。
- **tests/test_runner.py**: 包含 iRacing Manager 的测试用例。
- **tests/mock_main.py**: 使用模拟组件运行 iRacing Manager。

如果您想进行更改或扩展，可以调整相应的模块。

## 许可证

本项目根据 MIT 许可证发布。

---
## Français {#français}

# iRacing Manager

Un utilitaire pour démarrer et arrêter automatiquement des programmes pour l'environnement iRacing. Lorsque iRacing est fermé, tous les programmes associés sont également fermés automatiquement.

## Aperçu

L'iRacing Manager est un outil pour simplifier le flux de travail lors du démarrage et de l'arrêt d'iRacing et de ses applications auxiliaires. Le programme :

- Démarre toutes les applications auxiliaires définies dans le fichier de configuration (automatiquement minimisées)
- Détecte les programmes qui démarrent directement dans la barre d'état système et ignore les tentatives de minimisation inutiles
- Fournit un traitement spécial pour les programmes avec des écrans de démarrage ou des séquences de démarrage complexes
- Démarre iRacing en dernier programme (non minimisé)
- Surveille en continu le processus iRacing
- Termine automatiquement toutes les applications auxiliaires lorsque iRacing est fermé

## Prérequis

- Système d'exploitation Windows
- Python 3.6 ou supérieur
- Les bibliothèques Python suivantes :
  - psutil (pour la surveillance des processus)
  - pywin32 (pour les fonctions spécifiques à Windows comme la minimisation des fenêtres)

## Installation

1. Assurez-vous que Python 3.6 ou supérieur est installé.
2. Installez les bibliothèques requises :

```
py -m pip install psutil pywin32
```

3. Téléchargez tous les fichiers de l'iRacing Manager et placez-les dans un répertoire.
4. Ajustez le fichier `config.json` selon vos besoins (copiez depuis `config/example_config.json`).
5. Créez un raccourci sur le bureau avec la cible suivante :

```
pythonw <chemin_vers_le_répertoire>\src\core\iracing_manager.py
```
ou
```
py -m pythonw <chemin_vers_le_répertoire>\src\core\iracing_manager.py
```

> **Note :** Utilisez `pythonw` au lieu de `python` pour masquer la fenêtre de ligne de commande.

## Configuration

La configuration se fait via le fichier `config.json`. Ici, vous pouvez définir les programmes à démarrer, leurs chemins, les paramètres de démarrage et les options de comportement spéciales.

### Exemple de Configuration :

```json
{
  "programs": [
    {
      "name": "Oculus Client",
      "path": "C:\\Program Files\\Oculus\\Support\\oculus-client\\OculusClient.exe",
      "arguments": "",
      "has_splash_screen": true
    },
    {
      "name": "SimHub",
      "path": "C:\\Program Files (x86)\\SimHub\\SimHubWPF.exe",
      "arguments": "",
      "systray_only": true
    },
    {
      "name": "Garage61",
      "path": "C:\\Users\\username\\AppData\\Roaming\\garage61-install\\garage61-agent.exe",
      "arguments": "",
      "systray_only": true
    },
    {
      "name": "iRacing",
      "path": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\iRacing\\ui\\iRacingUI.exe",
      "arguments": "",
      "is_main": true
    }
  ]
}
```

### Paramètres de Configuration :

- `name` : Nom du programme (utilisé pour la journalisation)
- `path` : Chemin complet vers l'exécutable
- `arguments` : Paramètres de ligne de commande pour le programme (facultatif)
- `is_main` : `true` pour iRacing, `false` ou non présent pour les applications auxiliaires
- `systray_only` : `true` pour les programmes qui ne démarrent que dans la barre d'état système (comme SimHub)
- `has_splash_screen` : `true` pour les programmes avec un écran de démarrage (comme Oculus Client)

> **Important :** Un programme doit être marqué avec `"is_main": true`. C'est généralement iRacing. Ce programme est surveillé, et lorsqu'il est terminé, tous les autres programmes seront également terminés.

### Traitement Spécial pour des Programmes Spécifiques

L'iRacing Manager fournit un traitement spécial pour certains types de programmes :

- **Programmes de la Barre d'État Système** (`"systray_only": true`) : Les programmes comme SimHub ou Garage61 qui démarrent directement dans la barre d'état système sont détectés et ne sont pas inutilement minimisés.

- **Programmes avec Écran de Démarrage** (`"has_splash_screen": true`) : Les programmes comme le client Oculus qui ont un écran de démarrage puis ouvrent une fenêtre principale sont gérés avec une logique de surveillance spéciale qui garantit que l'écran de démarrage et la fenêtre principale sont minimisés.

- **Client Oculus** : Le client Oculus a un traitement particulièrement agressif car il ouvre parfois plusieurs fenêtres ou la fenêtre principale peut apparaître avec un délai. L'iRacing Manager utilise un thread de surveillance spécial pour trouver et minimiser toutes les fenêtres du client Oculus.

## Utilisation

1. Double-cliquez sur le raccourci du bureau pour démarrer l'iRacing Manager.
2. L'iRacing Manager démarre automatiquement tous les programmes configurés.
3. Lorsque vous avez terminé, fermez simplement iRacing, et tous les autres programmes seront automatiquement terminés.

## Dépannage

### Problèmes Courants

#### Programmes non minimisés

- **Général** : Assurez-vous d'avoir installé la bibliothèque `pywin32` :
  ```
  pip install pywin32
  ```

- **Programmes de la Barre d'État Système** : Si des programmes comme SimHub ne doivent pas être minimisés, définissez `"systray_only": true` dans la configuration.

- **Programmes avec Écran de Démarrage** : Si les programmes ouvrent une nouvelle fenêtre après le démarrage, définissez `"has_splash_screen": true` dans la configuration.

- **Client Oculus** : Le client Oculus a un traitement spécial. En cas de problèmes, démarrez l'iRacing Manager avec `py src/core/iracing_manager.py` depuis la ligne de commande pour voir les informations de débogage.

#### iRacing non détecté ou surveillé

Vérifiez si le chemin correct vers iRacing est spécifié dans `config.json` et si `"is_main": true` est défini pour iRacing.

#### Applications auxiliaires non terminées

Lorsque iRacing est fermé, vous pouvez vérifier le journal pour voir si la surveillance a fonctionné correctement. Démarrez l'iRacing Manager depuis la ligne de commande :

```
py src/core/iracing_manager.py
```

Cela affichera des messages de journal détaillés qui peuvent aider au diagnostic.

## Développement

L'iRacing Manager se compose de plusieurs modules organisés en répertoires :

### Structure des Répertoires
```
iRacingManager/
├── src/              # Code source
│   ├── core/         # Fonctionnalité principale
│   │   ├── iracing_manager.py
│   │   ├── iracing_watcher.py
│   │   └── process_manager.py
│   ├── ui/           # Interface utilisateur
│   │   └── console_ui.py
│   ├── utils/        # Fonctions utilitaires
│   │   ├── process_utils.py
│   │   ├── config_manager.py
│   │   └── window_manager.py
│   └── vr/           # Code spécifique à la VR/Oculus
│       └── oculus_handler.py
├── config/           # Fichiers de configuration
│   └── example_config.json
└── docs/             # Documentation
    └── README.md
```

#### Responsabilités des Modules :

- **src/core/iracing_manager.py** : Coordonne l'ensemble du processus, démarre les programmes dans le bon ordre et répond à la fin d'iRacing.
- **src/core/iracing_watcher.py** : Surveille en continu le processus iRacing et avertit le gestionnaire lorsque iRacing est terminé.
- **src/core/process_manager.py** : S'occupe du démarrage, de la minimisation et de la fin des programmes, avec un traitement spécial pour certains types de programmes.
- **src/ui/console_ui.py** : Fournit l'interface utilisateur de la console avec affichage des journaux encadré.
- **src/utils/config_manager.py** : Lit et valide le fichier de configuration, fournit des fonctions d'assistance pour récupérer les configurations des programmes.
- **src/utils/process_utils.py** : Utilitaires communs pour la gestion des processus entre les modules.
- **src/utils/window_manager.py** : Gère la recherche et la manipulation des fenêtres d'application.
- **src/vr/oculus_handler.py** : Traitement spécialisé pour les processus Oculus/VR.
- **tests/mock_process.py** : Fournit des implémentations factices de sous-processus et de psutil.
- **tests/mock_windows.py** : Fournit des implémentations factices de l'API Windows.
- **tests/test_runner.py** : Contient des cas de test pour l'iRacing Manager.
- **tests/mock_main.py** : Exécute l'iRacing Manager avec des composants factices.

Si vous souhaitez apporter des modifications ou des extensions, vous pouvez adapter les modules correspondants.

## Licence

Ce projet est publié sous la licence MIT.

---
## Русский {#russian}

# iRacing Manager

Утилита для автоматического запуска и остановки программ для среды iRacing. Когда iRacing закрывается, все связанные программы также автоматически закрываются.

## Обзор

iRacing Manager — это инструмент для упрощения рабочего процесса при запуске и остановке iRacing и его вспомогательных приложений. Программа:

- Запускает все вспомогательные приложения, определенные в файле конфигурации (автоматически свернутые)
- Обнаруживает программы, которые запускаются непосредственно в системном трее, и пропускает ненужные попытки сворачивания
- Обеспечивает специальную обработку для программ с заставками или сложными последовательностями запуска
- Запускает iRacing как последнюю программу (не свернутую)
- Постоянно отслеживает процесс iRacing
- Автоматически завершает все вспомогательные приложения при закрытии iRacing

## Требования

- Операционная система Windows
- Python 3.6 или выше
- Следующие библиотеки Python:
  - psutil (для мониторинга процессов)
  - pywin32 (для специфичных для Windows функций, таких как сворачивание окон)

## Установка

1. Убедитесь, что установлен Python 3.6 или выше.
2. Установите необходимые библиотеки:

```
py -m pip install psutil pywin32
```

3. Загрузите все файлы iRacing Manager и поместите их в каталог.
4. Настройте `config.json` в соответствии с вашими потребностями (скопируйте из `config/example_config.json`).
5. Создайте ярлык на рабочем столе со следующей целью:

```
pythonw <путь_к_каталогу>\src\core\iracing_manager.py
```
или
```
py -m pythonw <путь_к_каталогу>\src\core\iracing_manager.py
```

> **Примечание:** Используйте `pythonw` вместо `python`, чтобы скрыть окно командной строки.

## Конфигурация

Конфигурация выполняется через файл `config.json`. Здесь вы можете определить программы для запуска, их пути, параметры запуска и специальные параметры поведения.

### Пример конфигурации:

```json
{
  "programs": [
    {
      "name": "Oculus Client",
      "path": "C:\\Program Files\\Oculus\\Support\\oculus-client\\OculusClient.exe",
      "arguments": "",
      "has_splash_screen": true
    },
    {
      "name": "SimHub",
      "path": "C:\\Program Files (x86)\\SimHub\\SimHubWPF.exe",
      "arguments": "",
      "systray_only": true
    },
    {
      "name": "Garage61",
      "path": "C:\\Users\\username\\AppData\\Roaming\\garage61-install\\garage61-agent.exe",
      "arguments": "",
      "systray_only": true
    },
    {
      "name": "iRacing",
      "path": "C:\\Program Files (x86)\\Steam\\steamapps\\common\\iRacing\\ui\\iRacingUI.exe",
      "arguments": "",
      "is_main": true
    }
  ]
}
```

### Параметры конфигурации:

- `name`: Имя программы (используется для журналирования)
- `path`: Полный путь к исполняемому файлу
- `arguments`: Параметры командной строки для программы (необязательно)
- `is_main`: `true` для iRacing, `false` или отсутствует для вспомогательных приложений
- `systray_only`: `true` для программ, которые запускаются только в системном трее (например, SimHub)
- `has_splash_screen`: `true` для программ с заставкой (например, Oculus Client)

> **Важно:** Одна программа должна быть помечена как `"is_main": true`. Обычно это iRacing. Эта программа отслеживается, и когда она завершается, все остальные программы также будут завершены.

### Специальная обработка для конкретных программ

iRacing Manager обеспечивает специальную обработку для определенных типов программ:

- **Программы системного трея** (`"systray_only": true`): Программы, такие как SimHub или Garage61, которые запускаются непосредственно в системном трее, обнаруживаются и не сворачиваются без необходимости.

- **Программы с заставкой** (`"has_splash_screen": true`): Программы, такие как Oculus Client, у которых есть заставка, а затем открывается главное окно, обрабатываются с помощью специальной логики мониторинга, которая гарантирует, что и заставка, и главное окно будут свернуты.

- **Oculus Client**: Oculus Client имеет особенно агрессивную обработку, поскольку иногда открывает несколько окон, или главное окно может появляться с задержкой. iRacing Manager использует специальный поток мониторинга для поиска и сворачивания всех окон Oculus Client.

## Использование

1. Дважды щелкните ярлык на рабочем столе, чтобы запустить iRacing Manager.
2. iRacing Manager автоматически запускает все настроенные программы.
3. Когда вы закончите, просто закройте iRacing, и все остальные программы будут автоматически завершены.

## Устранение неполадок

### Распространенные проблемы

#### Программы не сворачиваются

- **Общие**: Убедитесь, что вы установили библиотеку `pywin32`:
  ```
  pip install pywin32
  ```

- **Программы системного трея**: Если программы, такие как SimHub, не должны сворачиваться, установите `"systray_only": true` в конфигурации.

- **Программы с заставкой**: Если программы открывают новое окно после запуска, установите `"has_splash_screen": true` в конфигурации.

- **Oculus Client**: Oculus Client имеет специальную обработку. Если возникают проблемы, запустите iRacing Manager с помощью `py src/core/iracing_manager.py` из командной строки, чтобы увидеть отладочную информацию.

#### iRacing не обнаруживается или не отслеживается

Проверьте, указан ли правильный путь к iRacing в `config.json` и установлен ли `"is_main": true` для iRacing.

#### Вспомогательные приложения не завершаются

Когда iRacing закрыт, вы можете проверить журнал, чтобы увидеть, правильно ли работал мониторинг. Запустите iRacing Manager из командной строки:

```
py src/core/iracing_manager.py
```

Это покажет подробные сообщения журнала, которые могут помочь в диагностике.

## Разработка

iRacing Manager состоит из нескольких модулей, организованных в каталоги:

### Структура каталогов
```
iRacingManager/
├── src/              # Исходный код
│   ├── core/         # Основная функциональность
│   │   ├── iracing_manager.py
│   │   ├── iracing_watcher.py
│   │   └── process_manager.py
│   ├── ui/           # Пользовательский интерфейс
│   │   └── console_ui.py
│   ├── utils/        # Вспомогательные функции
│   │   ├── process_utils.py
│   │   ├── config_manager.py
│   │   └── window_manager.py
│   └── vr/           # Код, специфичный для VR/Oculus
│       └── oculus_handler.py
├── config/           # Файлы конфигурации
│   └── example_config.json
└── docs/             # Документация
    └── README.md
```

#### Обязанности модулей:

- **src/core/iracing_manager.py**: Координирует весь процесс, запускает программы в правильном порядке и реагирует на завершение iRacing.
- **src/core/iracing_watcher.py**: Постоянно отслеживает процесс iRacing и уведомляет менеджера о завершении iRacing.
- **src/core/process_manager.py**: Заботится о запуске, сворачивании и завершении программ со специальной обработкой для определенных типов программ.
- **src/ui/console_ui.py**: Предоставляет консольный пользовательский интерфейс с отображением журнала в рамке.
- **src/utils/config_manager.py**: Читает и проверяет файл конфигурации, предоставляет вспомогательные функции для получения конфигураций программ.
- **src/utils/process_utils.py**: Общие утилиты для управления процессами между модулями.
- **src/utils/window_manager.py**: Обрабатывает поиск и управление окнами приложений.
- **src/vr/oculus_handler.py**: Специализированная обработка для процессов Oculus/VR.
- **tests/mock_process.py**: Предоставляет фиктивные реализации подпроцессов и psutil.
- **tests/mock_windows.py**: Предоставляет фиктивные реализации Windows API.
- **tests/test_runner.py**: Содержит тестовые случаи для iRacing Manager.
- **tests/mock_main.py**: Запускает iRacing Manager с фиктивными компонентами.

Если вы хотите внести изменения или расширения, вы можете адаптировать соответствующие модули.

## Лицензия

Этот проект выпущен под лицензией MIT.