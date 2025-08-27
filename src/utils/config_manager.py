#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ConfigManager: Loads, validates, and provides access to config.json.
Identifies main program, checks paths.
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional

# Logger
logger = logging.getLogger("ConfigManager")

# Config Error Exception
class ConfigError(Exception):
    """Custom exception for configuration related errors."""
    pass


class ConfigManager:
    """Manages iRacing Manager config. Loads, validates, provides access."""

    def __init__(self, config_path: str = "config.json"):
        """Init. Args: config_path (str, default 'config.json')."""
        self.config_path = config_path
        self.config = None
        self.programs = []
        self.main_program = None
        self._load_config()

    def _load_config(self) -> None:
        """Loads and validates config file. Raises FileNotFoundError or ConfigError."""
        try:
            if not os.path.exists(self.config_path):
                msg = f"Configuration file not found: {self.config_path}"
                logger.error(msg)
                logger.error(msg)
                raise FileNotFoundError(msg)

            with open(self.config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)

            self._validate_config()

        except FileNotFoundError:
             raise
        except json.JSONDecodeError as e:
            msg = f"Error parsing '{self.config_path}': {e}"
            logger.error(msg)
            raise ConfigError(msg) from e
        except ConfigError:
            raise
        except Exception as e:
            msg = f"Unexpected error loading '{self.config_path}': {e}"
            logger.error(msg, exc_info=True)
            raise ConfigError(msg) from e
    def _validate_config(self) -> None:
        """Validates config structure. Raises ConfigError if invalid."""
        self._validate_basic_structure()
        self._validate_programs_list()
        self._identify_main_program()

    def _validate_basic_structure(self) -> None:
        """Validates the root object and the presence/type of 'programs' key."""
        if not isinstance(self.config, dict):
            raise ConfigError("Invalid configuration format: Must be a JSON object.")

        if "programs" not in self.config:
            raise ConfigError("Configuration error: 'programs' key not found.")

        if not isinstance(self.config["programs"], list):
            raise ConfigError("Configuration error: 'programs' must be a list.")

        if not self.config["programs"]:
            raise ConfigError("Configuration error: 'programs' list cannot be empty.")

    def _validate_programs_list(self) -> None:
        """Validates each program entry in the 'programs' list."""
        validated_programs = []
        temp_main_program = None

        for idx, program in enumerate(self.config["programs"]):
            if not isinstance(program, dict):
                raise ConfigError(f"Configuration error: Program at index {idx} must be a JSON object.")

            # Required fields
            required_fields = ["name", "path"]
            for field in required_fields:
                if field not in program:
                    raise ConfigError(f"Configuration error: Required field '{field}' is missing in program '{program.get('name', f'at index {idx}')}'.")

            # Check path existence (Warning only)
            if not os.path.exists(program["path"]): # Path check (warn only)
                logger.warning(f"Path not found: {program['path']} for '{program['name']}'")

            if program.get("is_main", False):
                if temp_main_program:
                    logger.warning(f"Multiple main programs. Using '{program['name']}'.")
                temp_main_program = program

            # Old keys removed. PM handles minimization.
            # New keys via .get().

            if "window_management" in program:
                del program["window_management"]
            
            old_strategy_keys = ["has_splash_screen", "systray_only", "window_titles"]
            for key in old_strategy_keys:
                if key in program: del program[key]
            
            program['starts_in_tray'] = program.get('starts_in_tray', False)
            
            validated_programs.append(program)
        self.programs = validated_programs
        self.main_program = temp_main_program

    def _identify_main_program(self) -> None:
        """Ensures exactly one main program is identified, defaulting to the last if necessary."""
        if not self.programs:
             raise ConfigError("Internal: No programs validated.")

        if not self.main_program:
            last_program = self.programs[-1]
            logger.warning(f"No main program defined. Using last: '{last_program['name']}'.")
            self.main_program = last_program
            if not self.main_program.get("is_main"):
                 self.main_program["is_main"] = True
        # Use main_program if "is_main": true.
        # window_management removed.


    def get_programs(self) -> List[Dict[str, Any]]:
        """Returns list of all validated program configurations."""
        return self.programs

    def get_main_program(self) -> Dict[str, Any]:
        """Returns main program config (explicitly "is_main":true or last in list)."""
        return self.main_program

    def get_program_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Finds program by exact name (case-sensitive). Returns config or None."""
        for program in self.programs:
            if program["name"] == name:
                return program
        return None