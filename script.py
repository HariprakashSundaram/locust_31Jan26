from framework import SimpleLocustUser
from locust import LoadTestShape

# Load pattern: Step-up ramp
class StepUpLoadShape(LoadTestShape):
    stages = [
        {"duration": 60, "users": 5},  # 1 min: 5 users
        {"duration": 120, "users": 10, "request_per_sec": 2},  # next min: 10 users at 2/sec
        {"duration": 180, "users": 20},  # next min: 20 users
        {"duration": 240, "users": 50, "request_per_sec": 10},  # next min: 50 users at 10/sec
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                users = stage["users"]
                request_per_sec = stage.get("request_per_sec", 1)  # default 1/sec
                return (users, request_per_sec)
        return None  # Stop the test

variables = {
    "OrderId": {"type": "sequential", "values": ["123", "124", "125"]},
    "UserId": {"type": "random", "values": ["u1", "u2", "u3"]},
    "ProductId": {"type": "unique", "values": ["p1", "p2"]}
}

default_host = "www.google.com"

class MyLocustUser(SimpleLocustUser):
    pacing = 10  # seconds per iteration
    requests = [
        {
            "transaction_name": "Home Page",
            "method": "GET",
            "path": "/home/${OrderId}",
            "checks": {"status": 200},
            "think_time": 2.0
        },
        {
            "method": "GET",
            "path": "/search",
            "checks": {"content": "Google"},
            "think_time": 1.5
        },
        {
            "transaction_name": "Get Request",
            "method": "GET",
            "path": "/get",
            "checks": {"status": 200}
        },
        {
            "transaction_name": "Post Request",
            "method": "POST",
            "path": "/post",
            "body": {"key": "value", "user": "${UserId}"},
            "checks": {"content": "accepted"}
        },
        {
            "transaction_name": "Get JSON Data",
            "method": "GET",
            "path": "/json",
            "checks": {"status": 200},
            "correlations": {
                "token": {"from": "response", "type": "body", "extract": {"type": "regex", "pattern": r'"title":\s*"([^"]+)"', "occurrence": 1}}
            }
        },
        {
            "transaction_name": "Redirect Test",
            "method": "GET",
            "path": "/redirect/1",
            "checks": {"status": 200},
            "allow_redirects": False
        },
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.variables = variables
        self.host = default_host