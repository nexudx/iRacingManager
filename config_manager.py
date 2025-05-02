#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration manager for the iRacing Manager.

This module is responsible for:
1. Loading and parsing the JSON configuration file
2. Validating the structure and required parameters
3. Checking program paths and providing warnings for non-existent paths
4. Identifying the main program (is_main=true)
5. Providing access methods for the configuration data

The ConfigManager ensures a clean separation between configuration management
and the other components of the system.
"""

import json
import os
import sys
import logging
from typing import Dict, List, Any, Optional

# Set up logger - Configuration should be done in the main entry point
logger = logging.getLogger("ConfigManager")

# Custom Exception for Configuration Errors
class ConfigError(Exception):
    """Custom exception for configuration related errors."""
    pass


class ConfigManager:
    """
    Manages the configuration data for the iRacing Manager.
    
    This class serves as the central point for accessing all
    configuration settings. It ensures:
    
    - Loading the configuration file with error-tolerant processing
    - Validation of the structure and required fields
    - Preparation of the program list with special handling of the main program
    - Convenient access methods for other components
    
    The class separates configuration logic from business logic and
    thus simplifies the maintenance and extension of the system.
    """

    def __init__(self, config_path: str = "config.json"):
        """
        Initializes the ConfigManager with the path to the configuration file.

        Args:
            config_path (str): Path to the JSON configuration file. Default is 'config.json'.
        """
        self.config_path = config_path
        self.config = None
        self.programs = []
        self.main_program = None
        self._load_config()

    def _load_config(self) -> None:
        """
        Loads the configuration file and initiates validation.
        
        This method:
        1. Checks if the specified configuration file exists.
        2. Reads and parses the JSON content.
        3. Initiates the validation of the loaded configuration.
        4. Handles file not found, JSON parse errors, and other exceptions.

        In case of errors, a meaningful error message is logged and a
        ConfigError or FileNotFoundError is raised, as meaningful operation
        is not possible without a valid configuration.
        """
        try:
            if not os.path.exists(self.config_path):
                msg = f"Configuration file not found: {self.config_path}"
                logger.error(msg)
                raise FileNotFoundError(msg) # Raise specific error

            with open(self.config_path, "r", encoding="utf-8") as config_file:
                self.config = json.load(config_file)

            self._validate_config()

        except FileNotFoundError: # Re-raise FileNotFoundError directly
             raise
        except json.JSONDecodeError as e:
            msg = f"Error parsing the configuration file '{self.config_path}': {e}"
            logger.error(msg)
            raise ConfigError(msg) from e
        except ConfigError: # Re-raise ConfigError from _validate_config
            raise
        except Exception as e:
            # Catch other potential errors during file reading or validation setup
            msg = f"Unexpected error while loading configuration '{self.config_path}': {e}"
            logger.error(msg, exc_info=True) # Log traceback for unexpected errors
            raise ConfigError(msg) from e

    def _validate_config(self) -> None:
        """
        Validates the structure and contents of the loaded configuration.

        Raises:
            ConfigError: If the configuration is invalid.
        """
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

            # Validate required fields
            required_fields = ["name", "path"]
            for field in required_fields:
                if field not in program:
                    raise ConfigError(f"Configuration error: Required field '{field}' is missing in program '{program.get('name', f'at index {idx}')}'.")

            # Check path existence (Warning only)
            if not os.path.exists(program["path"]):
                logger.warning(f"Warning: Program path does not exist: {program['path']} for '{program['name']}'")

            # Check for main program flag
            if program.get("is_main", False):
                if temp_main_program:
                    logger.warning(f"Warning: Multiple main programs defined. '{temp_main_program['name']}' "
                                   f"and '{program['name']}'. Using '{program['name']}' as the main program.")
                temp_main_program = program

            validated_programs.append(program)

        self.programs = validated_programs
        self.main_program = temp_main_program # Store potentially identified main program

    def _identify_main_program(self) -> None:
        """Ensures exactly one main program is identified, defaulting to the last if necessary."""
        if not self.programs: # Should be caught by _validate_basic_structure, but defensive check
             raise ConfigError("Internal Error: No programs validated.")

        if not self.main_program:
            logger.warning("Warning: No main program (is_main=true) defined. "
                           "Using the last program ('%s') as the main program.", self.programs[-1]['name'])
            self.main_program = self.programs[-1]
        # If self.main_program is already set (from _validate_programs_list), we use that one.

    def get_programs(self) -> List[Dict[str, Any]]:
        """
        Provides the complete list of all validated programs.
        
        This method offers simple access to all configured programs without
        filtering or modification, as defined in the configuration file.
        It is typically used by the iRacingManager to determine the
        programs to start.

        Returns:
            List[Dict[str, Any]]: List of all program configurations as dictionaries
                                with all parameters from the configuration file
        """
        return self.programs

    def get_main_program(self) -> Dict[str, Any]:
        """
        Returns the configuration of the entry marked as the main program.
        
        The main program is either:
        - Explicitly marked with "is_main": true
        - Or the last program in the list if none is marked
        
        This method is used by the iRacingManager to identify iRacing
        and monitor it. The main program has a special meaning as its
        termination status triggers the termination of all other programs.

        Returns:
            Dict[str, Any]: Configuration of the main program with all parameters
        """
        return self.main_program

    def get_program_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Searches for a program with the exact specified name.
        
        This helper method searches the list of all programs for an
        entry with the requested name. The search is case-sensitive and
        requires an exact match. If no program with the specified name
        is found, None is returned.

        Args:
            name (str): Exact name of the program to search for

        Returns:
            Optional[Dict[str, Any]]: Complete configuration of the program
                                    or None if no program with this name exists
        """
        for program in self.programs:
            if program["name"] == name:
                return program
        return None
