from locust import HttpUser, task
from string import Template
import re
import random
from locust.exception import StopUser
import time
import json

class SimpleLocustUser(HttpUser):
    # Override in subclass with list of request configs
    requests = []
    # Override with global variables dict
    variables = {}
    # Override with pacing time in seconds
    pacing = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processed_requests = self.requests  # no pre-processing now
        self.session_vars = {}

    def prepare_body(self, req):
        if 'body' not in req:
            return None, {}
        body = req['body']
        headers = {}
        if 'content_type' in req:
            headers['Content-Type'] = req['content_type']
        if isinstance(body, dict):
            data = json.dumps(body)
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'application/json'
        else:
            data = body
        return data, headers

    def get_value(self, var_name):
        if var_name in self.variables:
            config = self.variables[var_name]
            values = config['values']
            typ = config['type']
            if typ == 'sequential':
                index = self.var_states[var_name]['index']
                value = values[index % len(values)]
                self.var_states[var_name]['index'] = (index + 1) % len(values)
                return value
            elif typ == 'random':
                return random.choice(values)
            elif typ == 'unique':
                used = self.var_states[var_name]['used']
                available = [v for v in values if v not in used]
                if not available:
                    raise StopUser(f"All unique values for {var_name} used")
                value = available[0]  # take first available
                used.add(value)
                return value
        else:
            # session variable
            return self.session_vars.get(var_name, '')

    def initialize_var_states(self):
        self.var_states = {}
        for var_name, config in self.variables.items():
            typ = config['type']
            if typ == 'sequential':
                self.var_states[var_name] = {'index': 0}
            elif typ == 'random':
                pass  # no state
            elif typ == 'unique':
                self.var_states[var_name] = {'used': set()}

    @task
    def perform_requests(self):
        if not hasattr(self, 'var_states'):
            self.initialize_var_states()
        start_time = time.time()
        for req in self.processed_requests:
            method = req.get('method', 'GET').upper()
            host = req.get('host', self.host)
            path = req['path']
            # Substitute variables in path
            path = re.sub(r'\$\{([^}]+)\}', lambda m: self.get_value(m.group(1)), path)
            check = req.get('checks', {})
            allow_redirects = req.get('allow_redirects', True)
            transaction_name = req.get('transaction_name', f"{method} {path}")
            url = f"https://{host}{path}"
            if method.upper() == 'GET':
                with self.client.get(url, name=transaction_name, allow_redirects=allow_redirects, catch_response=True) as response:
                    if isinstance(check, dict):
                        if 'status' in check:
                            expected_status = check['status']
                            if response.status_code != expected_status:
                                response.failure(f"Expected status {expected_status}, got {response.status_code}")
                        if 'content' in check:
                            content_check = check['content']
                            if content_check not in response.text:
                                response.failure(f"'{content_check}' not found in response")
                    elif str(check).isdigit():
                        expected_status = int(check)
                        if response.status_code != expected_status:
                            response.failure(f"Expected status {expected_status}, got {response.status_code}")
                    else:
                        if check not in response.text:
                            response.failure(f"'{check}' not found in response")
                    # Capture values for session
                    for var_name, corr in req.get('correlations', {}).items():
                        source = corr['from']  # 'request' or 'response'
                        typ = corr['type']  # 'header', 'body', 'url'
                        key = corr.get('key')
                        extract = corr.get('extract', {})
                        extract_type = extract.get('type', 'direct')
                        value = None
                        if source == 'response':
                            if typ == 'header':
                                value = response.headers.get(key)
                            elif typ == 'body':
                                if extract_type == 'json':
                                    path = extract.get('path', key)
                                    try:
                                        data = response.json()
                                        value = self.get_json_value(data, path)
                                    except:
                                        value = None
                                elif extract_type == 'regex':
                                    pattern = extract.get('pattern')
                                    occurrence = extract.get('occurrence', 1)
                                    if occurrence == 'all':
                                        matches = re.findall(pattern, response.text)
                                        value = ' '.join(matches)
                                    else:
                                        matches = list(re.finditer(pattern, response.text))
                                        if len(matches) >= occurrence:
                                            match = matches[occurrence - 1]
                                            value = match.group(1) if match.groups() else match.group(0)
                                        else:
                                            value = None
                                else:
                                    value = response.text
                            elif typ == 'url':
                                value = url
                        elif source == 'request':
                            if typ == 'url':
                                value = url
                        if value is not None:
                            self.session_vars[var_name] = value
                    # Think time
                    if 'think_time' in req:
                        time.sleep(req['think_time'])
            elif method.upper() == 'POST':
                data, headers = self.prepare_body(req)
                with self.client.post(url, name=transaction_name, allow_redirects=allow_redirects, data=data, headers=headers, catch_response=True) as response:
                    if isinstance(check, dict):
                        if 'status' in check:
                            expected_status = check['status']
                            if response.status_code != expected_status:
                                response.failure(f"Expected status {expected_status}, got {response.status_code}")
                        if 'content' in check:
                            content_check = check['content']
                            if content_check not in response.text:
                                response.failure(f"'{content_check}' not found in response")
                    elif str(check).isdigit():
                        expected_status = int(check)
                        if response.status_code != expected_status:
                            response.failure(f"Expected status {expected_status}, got {response.status_code}")
                    else:
                        if check not in response.text:
                            response.failure(f"'{check}' not found in response")
                    # Capture values for session
                    for var_name, corr in req.get('correlations', {}).items():
                        source = corr['from']  # 'request' or 'response'
                        typ = corr['type']  # 'header', 'body', 'url'
                        key = corr.get('key')
                        extract = corr.get('extract', {})
                        extract_type = extract.get('type', 'direct')
                        value = None
                        if source == 'response':
                            if typ == 'header':
                                value = response.headers.get(key)
                            elif typ == 'body':
                                if extract_type == 'json':
                                    path = extract.get('path', key)
                                    try:
                                        data = response.json()
                                        value = self.get_json_value(data, path)
                                    except:
                                        value = None
                                elif extract_type == 'regex':
                                    pattern = extract.get('pattern')
                                    occurrence = extract.get('occurrence', 1)
                                    if occurrence == 'all':
                                        matches = re.findall(pattern, response.text)
                                        value = ' '.join(matches)
                                    else:
                                        matches = list(re.finditer(pattern, response.text))
                                        if len(matches) >= occurrence:
                                            match = matches[occurrence - 1]
                                            value = match.group(1) if match.groups() else match.group(0)
                                        else:
                                            value = None
                                else:
                                    value = response.text
                            elif typ == 'url':
                                value = url
                        elif source == 'request':
                            if typ == 'url':
                                value = url
                        if value is not None:
                            self.session_vars[var_name] = value
                    # Think time
                    if 'think_time' in req:
                        time.sleep(req['think_time'])
            else:
                with self.client.request(method, url, allow_redirects=allow_redirects, catch_response=True) as response:
                    if isinstance(check, dict):
                        if 'status' in check:
                            expected_status = check['status']
                            if response.status_code != expected_status:
                                response.failure(f"Expected status {expected_status}, got {response.status_code}")
                        if 'content' in check:
                            content_check = check['content']
                            if content_check not in response.text:
                                response.failure(f"'{content_check}' not found in response")
                    elif str(check).isdigit():
                        expected_status = int(check)
                        if response.status_code != expected_status:
                            response.failure(f"Expected status {expected_status}, got {response.status_code}")
                    else:
                        if check not in response.text:
                            response.failure(f"'{check}' not found in response")
                    # Capture values for session
                    for var_name, corr in req.get('correlations', {}).items():
                        source = corr['from']  # 'request' or 'response'
                        typ = corr['type']  # 'header', 'body', 'url'
                        key = corr.get('key')
                        extract = corr.get('extract', {})
                        extract_type = extract.get('type', 'direct')
                        value = None
                        if source == 'response':
                            if typ == 'header':
                                value = response.headers.get(key)
                            elif typ == 'body':
                                if extract_type == 'json':
                                    path = extract.get('path', key)
                                    try:
                                        data = response.json()
                                        value = self.get_json_value(data, path)
                                    except:
                                        value = None
                                elif extract_type == 'regex':
                                    pattern = extract.get('pattern')
                                    occurrence = extract.get('occurrence', 1)
                                    if occurrence == 'all':
                                        matches = re.findall(pattern, response.text)
                                        value = ' '.join(matches)
                                    else:
                                        matches = list(re.finditer(pattern, response.text))
                                        if len(matches) >= occurrence:
                                            match = matches[occurrence - 1]
                                            value = match.group(1) if match.groups() else match.group(0)
                                        else:
                                            value = None
                                else:
                                    value = response.text
                            elif typ == 'url':
                                value = url
                        elif source == 'request':
                            if typ == 'url':
                                value = url
                        if value is not None:
                            self.session_vars[var_name] = value
                    # Think time
                    if 'think_time' in req:
                        time.sleep(req['think_time'])
        # Pacing
        if self.pacing:
            elapsed = time.time() - start_time
            if elapsed < self.pacing:
                time.sleep(self.pacing - elapsed)