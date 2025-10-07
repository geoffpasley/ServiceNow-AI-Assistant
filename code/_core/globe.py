import uuid
import _core.extension as extension
import _core.configloader as configloader

# Global variables can be changed here (useful for debugging)

# Set this to True if you want to ignore logging to the repository set in the config file
ignore_repo = False
# Set this to True if you want to check the application dependencies
check_dependency = True
# Set this to True if you want the process to show as failed if an application dependency check fails, otherwise it will show as a warning
check_dependency_fail_on_error = False

#############################################################################################
    #### Do not change anything below this line. It will not persist to the next run ####
#############################################################################################

class Variable:
    def __init__(self):
        self.variables = []
    def get(self, section, key):
        """Retrieve a variable by section and key."""
        for var in self.variables:
            if var["section"] == section and var["key"] == key:
                return var["value"]
        return None

    def add(self, section, key, value):
        """Add a new variable."""
        self.variables.append({"section": section, "key": key, "value": value})

    def update(self, section, key, value):
        """Update an existing variable."""
        for var in self.variables:
            if var["section"] == section and var["key"] == key:
                var["value"] = value
                return True
        return False
    
#### Global variables set during runtime ####

# Create a global variable object
variable = Variable()
# logger is an instance of the Log class
logger = None

# process_id is a unique identifier for the current process
process_id = None
# error is a flag to determine if an error has occurred
error = False
# check_dependency_complete is a flag to determine if the application dependencies have been checked
check_dependency_complete = False

## Constants ##
# Set the log types that are allowed
log_types = ["servicenow"]

class Globe:
    def __init__(self):
        global process_id, logger

        # Initialize the config loaders
        self.config_loader = configloader.ConfigLoader('config.ini')  # Load main config file
        self.dependency_loader = configloader.ConfigLoader('dependency.ini', preserve_case=True)  # Load dependency config file
        # Ensure the main config file is loaded
        if not self.config_loader.is_loaded:
            logger.entry("Main config file not loaded. Cannot proceed without required settings.", type="error")
            raise Exception("Program Terminated")
        # Load settings
        self._load_main_settings()
        self._load_dependencies()
        self._load_runtime_settings()

        # Initialize process ID
        process_id = str(uuid.uuid4())  # Generate unique process ID
        # Initialize logger
        logger = extension.Log(ignore_repo=ignore_repo) 

        self._validate_settings()

    def _load_main_settings(self):
        """Load all settings from the main configuration file."""
        for section, keys in self.config_loader.config.items():
            if isinstance(keys, dict):
                for key, value in keys.items():
                    variable.add(section, key, value)
            else:
                if logger:
                    logger.entry(f"Invalid section format: {section}", type="error")

    def _load_dependencies(self):
        """Load dependencies from the dependency configuration file."""
        if self.dependency_loader.is_loaded:
            dependencies = self.dependency_loader.config.get("applications", {})
            for app_name, version in dependencies.items():
                # Explicitly preserve case while adding to the variable store
                variable.add("dependency", app_name, version)


    def _load_runtime_settings(self):
        """Load runtime settings into the global variable list."""
        application_type = variable.get("settings", "application_type")
        if application_type:
            application_type = application_type.lower()
            if application_type == "servicenow":
                application_scope = variable.get("servicenow", "application_scope")
                if application_scope:
                    application_name, log_level = extension.Application()._servicenow(name=application_scope)
                    variable.add("runtime", "application_name", application_name)
                    variable.add("runtime", "log_level", log_level)
                else:
                    variable.add("runtime", "application_name", "unknown_missing")
                    variable.add("runtime", "log_level", "info")
    
    def _validate_settings(self):
        """Validate that all required settings are present."""
        required_settings = [
            ('settings', 'application_type'),
            ('settings', 'log_type'),
            ('servicenow', 'application_scope'),
            ('servicenow', 'instance'),
            ('servicenow', 'username'),
            ('servicenow', 'password'),
        ]

        missing_settings = [
            f"{section}.{key}" for section, key in required_settings
            if not variable.get(section, key)
        ]

        if missing_settings:
            error_message = f"Missing required settings: {', '.join(missing_settings)}"
            logger.entry(error_message, type="error")
            raise Exception(error_message)

        