import configparser
import os

class ConfigLoader:
    """Singleton class to load and manage config parameters from multiple files."""
    _instances = {}  # Dictionary to manage instances per file
    _config = {}
    _loaded_successfully = False

    def __new__(cls, config_file='config.ini', preserve_case=False):
        if config_file not in cls._instances:
            instance = super(ConfigLoader, cls).__new__(cls)
            instance._load_config(config_file, preserve_case)
            cls._instances[config_file] = instance
        return cls._instances[config_file]

    def _load_config(self, config_file, preserve_case):
        self._config = {}
        self._loaded_successfully = False

        if not os.path.exists(config_file):
            print(f"Warning: Config file '{config_file}' not found.")
            return

        config = configparser.ConfigParser()
        if preserve_case:
            config.optionxform = str

        # Read and escape % characters in the config file
        with open(config_file, 'r') as file:
            content = file.read()
            content = content.replace('%', '%%')  # Escape % characters
            config.read_string(content)

        # Convert the configuration into a dictionary
        self._config = {
            section: {key: value for key, value in config[section].items()}
            for section in config.sections()
        }
        self._loaded_successfully = True

    @property
    def config(self):
        """Access the loaded configuration."""
        return self._config

    @property
    def is_loaded(self):
        """Check if the config file was loaded successfully."""
        return self._loaded_successfully

    def get(self, section, key, default=None):
        """Get a specific value from the config."""
        return self._config.get(section, {}).get(key, default)