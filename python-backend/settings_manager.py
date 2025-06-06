import json
import os
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)
SETTINGS_FILE = 'python-backend/app_settings.json' # Path relative to project root

class SettingsManager:
    def __init__(self, settings_file: str = SETTINGS_FILE):
        self.settings_file = settings_file
        self.settings: Dict[str, Any] = {}
        self.load_settings()

    def _get_default_settings(self) -> Dict[str, Any]:
        """Returns the default application settings."""
        return {
            "theme": "light",
            "llm_model_preference": "default_mock_llm",
            "notifications_enabled": True,
            "default_download_path": "~/Downloads" # Example of another setting
        }

    def load_settings(self) -> None:
        """Loads settings from the JSON file. If not found or corrupt, uses defaults."""
        defaults = self._get_default_settings()
        if not os.path.exists(self.settings_file):
            logger.info(f"Settings file '{self.settings_file}' not found. Initializing with default settings.")
            self.settings = defaults
            self.save_settings() # Save defaults if file doesn't exist
            return

        try:
            with open(self.settings_file, 'r') as f:
                loaded_settings = json.load(f)
                # Merge loaded settings with defaults to ensure all keys are present
                self.settings = {**defaults, **loaded_settings}
                # Save back if loaded settings were missing some defaults
                if len(self.settings) > len(loaded_settings):
                    self.save_settings()
            logger.info(f"Loaded settings from '{self.settings_file}'.")
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from '{self.settings_file}'. File might be corrupted. Using default settings.")
            self.settings = defaults
            self.save_settings() # Attempt to save defaults over corrupted file
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading settings: {e}. Using default settings.")
            self.settings = defaults
            # Optionally, attempt to save defaults here too, or handle more gracefully.

    def save_settings(self) -> None:
        """Saves the current settings to the JSON file."""
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.settings_file), exist_ok=True)
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            logger.info(f"Saved settings to '{self.settings_file}'.")
        except IOError as e:
            logger.error(f"IOError saving settings to '{self.settings_file}': {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred while saving settings: {e}")

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Retrieves a setting value by key, returning a default if not found."""
        return self.settings.get(key, default)

    def update_setting(self, key: str, value: Any) -> None:
        """Updates a single setting and saves all settings."""
        self.settings[key] = value
        self.save_settings()
        logger.info(f"Updated setting '{key}' to '{value}'.")

    def get_all_settings(self) -> Dict[str, Any]:
        """Returns a copy of all current settings."""
        return self.settings.copy()

if __name__ == '__main__':
    # Configure basic logging for the test
    if not logging.getLogger().hasHandlers():
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    TEST_SETTINGS_FILE = 'python-backend/test_app_settings.json'
    if os.path.exists(TEST_SETTINGS_FILE):
        os.remove(TEST_SETTINGS_FILE)

    logger.info("--- SettingsManager Test ---")

    # 1. Initialize and check default settings
    manager = SettingsManager(settings_file=TEST_SETTINGS_FILE)
    logger.info(f"Initial settings (defaults): {manager.get_all_settings()}")
    assert manager.get_setting("theme") == "light"

    # 2. Update a setting
    manager.update_setting("theme", "dark")
    logger.info(f"After update 'theme': {manager.get_setting('theme')}")
    assert manager.get_setting("theme") == "dark"

    manager.update_setting("notifications_enabled", False)
    logger.info(f"After update 'notifications_enabled': {manager.get_setting('notifications_enabled')}")
    assert manager.get_setting("notifications_enabled") is False

    # 3. Add a new setting
    manager.update_setting("user_name", "Test User")
    logger.info(f"After adding 'user_name': {manager.get_setting('user_name')}")
    assert manager.get_setting("user_name") == "Test User"

    # 4. Check persistence by creating a new manager instance
    logger.info("Creating new SettingsManager instance to test loading from file...")
    manager2 = SettingsManager(settings_file=TEST_SETTINGS_FILE)
    logger.info(f"Settings loaded by manager2: {manager2.get_all_settings()}")
    assert manager2.get_setting("theme") == "dark"
    assert manager2.get_setting("notifications_enabled") is False
    assert manager2.get_setting("user_name") == "Test User"
    assert manager2.get_setting("llm_model_preference") == "default_mock_llm" # Check default is still there

    # 5. Test loading with a corrupted file (manual step usually, here we simulate)
    logger.info("Simulating corrupted settings file...")
    with open(TEST_SETTINGS_FILE, 'w') as f:
        f.write("{corrupted_json_data: ")

    manager3 = SettingsManager(settings_file=TEST_SETTINGS_FILE)
    logger.info(f"Settings after loading corrupted file: {manager3.get_all_settings()}")
    # Should revert to defaults and save them
    assert manager3.get_setting("theme") == "light"
    assert os.path.exists(TEST_SETTINGS_FILE) # Check if file was re-saved with defaults

    # Check if defaults were correctly saved over corrupted file
    manager4 = SettingsManager(settings_file=TEST_SETTINGS_FILE)
    assert manager4.get_setting("theme") == "light"
    logger.info(f"Settings after loading file saved over corruption: {manager4.get_all_settings()}")


    logger.info("--- SettingsManager Test Complete ---")
    # Clean up test file
    if os.path.exists(TEST_SETTINGS_FILE):
        os.remove(TEST_SETTINGS_FILE)
        logger.info(f"Cleaned up '{TEST_SETTINGS_FILE}'.")
```
