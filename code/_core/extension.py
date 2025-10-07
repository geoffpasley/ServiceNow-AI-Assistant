from email.mime import message
import _core.globe as globe
import requests
import time
from datetime import datetime, timezone
import json

class RestAPI:
    def __init__(self, max_retries=5, retry_delay=60, timeout=15, ignore_repo = False):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        if globe.ignore_repo:
            self.ignore_repo = True
        else:
            self.ignore_repo = ignore_repo
        self.logger = Log(ignore_repo=self.ignore_repo)

        self.success = False

    def make_request(self, method, url, auth=None, headers=None, data=None, params=None, timeout=None, return_error=False, return_json=True):
        if not timeout:
            timeout = self.timeout
        for attempt in range(self.max_retries):
            try:
                response = requests.request(method, url, auth=auth, headers=headers, data=data, params=params, timeout=timeout)
                if not return_error:
                    response.raise_for_status()

                if response.ok:
                    self.success = True
                    try:
                        if not return_json:
                            return response.content
                        else:
                            return response.json()
                    except:
                        return True
                else:
                    if not return_error:
                        self.logger.entry(message = f"Error: {response.status_code}, {response.text}", type="warning", state="run")
                    if return_error:
                        return response.json()
            except Exception as e:
                self.logger.entry(message = f"Error: {e}", type="warning", state="run")
            
            if attempt < self.max_retries - 1:
                Output().print_log(message = f"Retrying in {self.retry_delay} seconds...", type="warning")
                time.sleep(self.retry_delay)

        # If we reach this point, we've exhausted our retries
        self.logger.entry(message = f"Error: Maximum retries reached", type="error", state="run")
        return None

class Log:
    def __init__(self, ignore_repo=False):
        self.ignore_repo = ignore_repo

    def entry(self, message, type="info", state="run", subprocess_id = None):
        if not self.ignore_repo:
            if type in globe.variable.get('runtime', 'log_level'):
                self._send_to_repo(message=message, type=type, state=state, subprocess_id=subprocess_id)
        Output().print_log(message=message, type=type)
    
    def start_msg(self):
        if not self.ignore_repo:
            message = f"Started Process ID: {globe.process_id}"
            self._send_to_repo(message=message, type="success", state="start")
        Output().print_log(message=message, type="success")
        if globe.variable.get('settings', 'application_type').lower() == 'servicenow':
            message = f"SerivceNow Instance: {globe.variable.get('servicenow', 'instance')}"
            Output().print_log(message=message, type="info")
        
        # Add a 1 second delay
        time.sleep(1)
    
    def end_msg(self):
        # Add a 1 second delay
        time.sleep(1)
        
        if globe.error:
            if not self.ignore_repo:
                message = f"Finished Process ID: {globe.process_id}"
                self._send_to_repo(message=message, type="error", state="end")
            Output().print_log(message=message, type="error")
        else:
            if not self.ignore_repo:
                message = f"Finished Process ID: {globe.process_id}"
                self._send_to_repo(message=message, type="success", state="end")
            Output().print_log(message=message, type="success")
    
    def _log_level(self, level):
        if level == "debug":
            return ["debug", "info", "warning", "error", "success"]
        elif level == "info":
            return ["info", "warning", "error", "success"]
        elif level == "warning":
            return ["warning", "error", "success"]
        elif level == "error":
            return ["error", "success"]
        else:
            return ["info", "warning", "error", "success"]
            
    def _send_to_repo(self, message, type, state, subprocess_id = None):
        if not self.ignore_repo:
            if globe.variable.get('settings', 'log_type').lower() == 'servicenow':
                self._repo_servicenow(message=message, type=type, state=state, subprocess_id=subprocess_id)
            
    def _repo_servicenow(self, message, type, state, subprocess_id):
        data = { 
            'message': message,
            'type': type,
            'state': state,
            'process_id': globe.process_id,
            'subprocess_id': subprocess_id,
            'application': globe.variable.get('runtime', 'application_name'),
            'scope': globe.variable.get('servicenow', 'application_scope'),
            'source': "python"
        }
        sn = RestAPI(ignore_repo=True)
        url = f"https://{globe.variable.get('servicenow', 'instance')}/api/x_esrie_cmdb_integ/integration/log"
        headers = {"Content-Type": "application/json"}
        sn.make_request("POST", url, auth=(globe.variable.get('servicenow', 'username'), globe.variable.get('servicenow', 'password')), headers=headers, data=json.dumps(data), timeout=15)

class Application:
    def _servicenow(self, name):
        application_name = None
        log_level = None
        ignore_repo_temp = globe.ignore_repo
        globe.ignore_repo = True
        sn = RestAPI(ignore_repo = True)

        # Get the application name
        url = f"https://{globe.variable.get('servicenow', 'instance')}/api/now/table/sys_scope?sysparm_query=scope={name}"
        headers = {"Content-Type": "application/json"}
        r = sn.make_request("GET", url, auth=(globe.variable.get('servicenow', 'username'), globe.variable.get('servicenow', 'password')), headers=headers, timeout=15)
        if r and r.get('result'):
            application_name = r.get('result', [])[0].get('name')
        else:
            application_name = "Not Found in ServiceNow"
        
        # Get the log level
        url = f"https://{globe.variable.get('servicenow', 'instance')}/api/now/table/sys_properties?sysparm_query=name={name}.LogLevel"
        r = sn.make_request("GET", url, auth=(globe.variable.get('servicenow', 'username'), globe.variable.get('servicenow', 'password')), headers=headers, timeout=15)
        if r and r.get('result'):
            log_level = r.get('result', [])[0].get('value')
        else:
            log_level = "info"
            
        globe.ignore_repo = ignore_repo_temp
        return application_name, Log(ignore_repo=True)._log_level(log_level)
        
class Output:     
    def print_log(self, message, type):
        current_time = datetime.now().strftime("%m-%d %H:%M:%S")
        message = f"[{current_time}] | {message}"
        if type == "warning":
            self.print_yellow(message=message)
        elif type == "error":
            self.print_red(message=message)
        elif type == "success":
            self.print_green(message=message)
        else:
            self.print_white(message=message)

    # https://www.geeksforgeeks.org/print-colors-python-terminal/
    def print_red(self, message): 
        print("\033[91m {}\033[00m" .format(message))

    def print_green(self, message): 
        print("\033[92m {}\033[00m" .format(message))

    def print_yellow(self, message): 
        print("\033[93m {}\033[00m" .format(message))

    def print_white(self, message): 
        print("\033[97m {}\033[00m" .format(message))

class Common:
    def check_for_success(array):
        for element in array:
            if not element:
                return False
        return True

    @staticmethod
    def sleep(seconds):
        import time
        time.sleep(seconds)
        return True

    @staticmethod
    def epoch_to_time_array(epoch_seconds, milliseconds=False):
        """
        Converts epoch time to [year, month, day, hour, minute, second] in UTC.

        Args:
            epoch_seconds (int | float): Epoch time in seconds or milliseconds.
            milliseconds (bool): Set to True if the input is in milliseconds.

        Returns:
            list: [year, month, day, hour, minute, second] in UTC
        """
        if milliseconds:
            epoch_seconds = epoch_seconds / 1000.0
        dt = datetime.fromtimestamp(epoch_seconds, tz=timezone.utc)
        return [dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second]
    