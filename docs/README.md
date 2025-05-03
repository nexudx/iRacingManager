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