import _core.globe as globe
import _core.extension as extension
import _core.servicenow as servicenow

class Dependency:
    def Check(self):
        process_success = []
        for application in globe.variable.variables:
            if application["section"] == "dependency":
                try:
                    a = self._version_check(application["key"], application["value"])
                    process_success.append(a)
                except Exception as e:
                    globe.logger.entry(message = str(e), type="error")
                    process_success.append(False)
        if globe.check_dependency_fail_on_error:
            return extension.Common.check_for_success(process_success)
        else:
            return True
        
    def _version_check(self, application, minimum_version):
        if globe.variable.get('settings', 'application_type').lower() == 'servicenow':
            return self._servicenow(application, minimum_version)
    
    def _servicenow(self, application, minimum_version):
        installed_version = servicenow.API().GET_Application_Version(application.lower())

        if installed_version is None:
            globe.logger.entry(f"Application {application} not installed", type="warning")
            return False
        
        def parse_version(version):
            return list(map(int, version.split('.')))
        
        installed_version_parts = parse_version(installed_version)
        minimum_version_parts = parse_version(minimum_version)
        
        # Compare versions
        for installed, minimum in zip(installed_version_parts, minimum_version_parts):
            if installed > minimum:
                return True
            if installed < minimum:
                globe.logger.entry(f"Application {application} installed version {installed_version} is less than the required minimum version {minimum_version}", type="warning")
                return False
        
        # Handle case where installed and minimum versions are of different lengths
        if len(installed_version_parts) > len(minimum_version_parts):
            return True
        elif len(installed_version_parts) < len(minimum_version_parts):
            globe.logger.entry(f"Application {application} installed version {installed_version} is less than the required minimum version {minimum_version}", type="warning")
            return False
        
        # If all parts are equal, return True
        return True