import _core.globe as globe 
import _core.extension as extension
import json
from datetime import datetime

class API:
    def __init__(self, max_retries=5, timeout=15):
        self.max_retries = max_retries
        self.timeout = timeout

        self.base_url = f"https://{globe.variable.get('servicenow', 'instance')}/api/"

    def GET_all_table_records(self, table, encoded_query=None, fields=None, display_value=False, limit=1000):
        offset = 0
        records = []

        while True:
            fetched_records = self.GET_table_records(table=table, encoded_query=encoded_query, fields=fields, display_value=display_value, limit=limit, offset=offset)
            if not fetched_records:
                break  # No more records to fetch
            records.extend(fetched_records)
            offset += limit
            
        return records

    # Function to perform a GET request to retrieve records
    def GET_table_records(self, table, encoded_query=None, fields=None, display_value=False, limit=100, offset=0): 
        url = self.base_url + "now/table/" + table
        
        # Build the params dictionary
        params = {
            "sysparm_limit": limit, 
            "sysparm_offset": offset
        }
        
        if encoded_query:
            params["sysparm_query"] = encoded_query

        if fields:
            params["sysparm_fields"] = ",".join(fields) if isinstance(fields, list) else fields
        if display_value:
            params["sysparm_display_value"] = True

        # Make the API request
        response_data = extension.RestAPI(max_retries=self.max_retries, timeout=self.timeout).make_request(
            method="GET", 
            url=url, 
            auth=(globe.variable.get('servicenow', 'username'), globe.variable.get('servicenow', 'password')), 
            params=params
        )

        # Return the results if available
        return response_data.get('result', []) if response_data else None

        
    # Function to create a new record
    def POST_table_record(self, table, data):
        url = self.base_url + "now/table/" + table
        headers = {"Content-Type": "application/json"}
        response_data = extension.RestAPI(max_retries=self.max_retries, timeout=self.timeout).make_request(
            method="POST", 
            url=url, 
            auth=(globe.variable.get('servicenow', 'username'), globe.variable.get('servicenow', 'password')), 
            headers=headers, 
            data=json.dumps(data)
        )

        if response_data:
            return response_data.get('result', [])
        else:
            return None   
    
    # Function to update an existing record by sys_id
    def PUT_table_record(self, table, sys_id, data):
        url = self.base_url + "now/table/" + table + "/" + sys_id
        headers = {"Content-Type": "application/json"}
        response_data = extension.RestAPI(max_retries=self.max_retries, timeout=self.timeout).make_request(
            method="PUT", 
            url=url, 
            auth=(globe.variable.get('servicenow', 'username'), globe.variable.get('servicenow', 'password')), 
            headers=headers, 
            data=json.dumps(data)
        )

        if response_data:
            return response_data.get('result', [])
        else:
            return None 
    
    def DELETE_table_record(self, table, sys_id):
        url = self.base_url + "now/table/" + table + "/" + sys_id
        response_data = extension.RestAPI(max_retries=self.max_retries, timeout=self.timeout).make_request(
            method="DELETE", 
            url=url, 
            auth=(globe.variable.get('servicenow', 'username'), globe.variable.get('servicenow', 'password'))
        )
        
        return response_data
    
    # Function to update an existing record by sys_id
    def GET_scripted_api(self, api, data=None, params=None):
        url = self.base_url + api
        headers = {"Content-Type": "application/json"}
        response_data = extension.RestAPI(max_retries=self.max_retries, timeout=self.timeout).make_request(
            method="GET", 
            url=url, 
            auth=(globe.variable.get('servicenow', 'username'), globe.variable.get('servicenow', 'password')), 
            headers=headers, 
            data=json.dumps(data), 
            params=params
        )

        if response_data:
            try:
                return response_data.get('result', [])
            except:
                return None
        else:
            return None
        
    # Function to update an existing record by sys_id
    def POST_scripted_api(self, api, data=None, params=None):
        url = self.base_url + api
        headers = {"Content-Type": "application/json"}
        response_data = extension.RestAPI(max_retries=self.max_retries, timeout=self.timeout).make_request(
            method="POST", 
            url=url, 
            auth=(globe.variable.get('servicenow', 'username'), globe.variable.get('servicenow', 'password')), 
            headers=headers, 
            data=json.dumps(data), 
            params=params
        )

        if response_data:
            return response_data.get('result', [])
        else:
            return None
        
    def DELETE_scripted_api(self, api, params=None):
        url = self.base_url + api
        headers = {"Content-Type": "application/json"}
        response_data = extension.RestAPI(max_retries=self.max_retries, timeout=self.timeout).make_request(
            method="DELETE", 
            url=url, 
            auth=(globe.variable.get('servicenow', 'username'), globe.variable.get('servicenow', 'password')), 
            headers=headers, 
            params=params
        )
        
        return response_data
    
    def GET_Application_Version(self, name):
        app_records = self.GET_table_records(table="sys_app")
        for r in app_records:
            if r.get('name').lower() == name:
                return r.get('version')
        store_records = self.GET_scripted_api(api="x_esrie_cmdb_integ/integration/store_app_list")
        for r in store_records:
            if r.get('name').lower() == name:
                return r.get('version')
        
        return None
        
    def IRE_computer(self, name, serial_number, mac_address):
        t_max_retries = self.max_retries
        self.max_retries = 1
        data = {}
        if name:
            data["name"] = name
        if serial_number:
            data["serial_number"] = serial_number
        if mac_address:
            data["mac_address"] = mac_address
        response = self.POST_scripted_api(api="x_esrie_cmdb_integ/ire/computer", data=data)
        self.max_retries = t_max_retries

        if response:
            return response
        else:    
            return None
    
    def get_current_glide_date(self):
        # Current time in the required GlideDateTime format
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')