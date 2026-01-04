# -*- coding: utf-8 -*-
"""
Load Testing Script for VortexDB API.
Uses Locust for distributed load testing.

Usage:
    locust -f tests/load/locustfile.py --host=http://localhost:8000
    
Then open http://localhost:8089 in your browser.
"""
from locust import HttpUser, task, between
import json
import os


class VortexDBUser(HttpUser):
    """Simulated user for VortexDB load testing."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Set up headers on user start."""
        self.api_key = os.getenv("VECTOR_API_KEY", "load-test-key")
        self.client.headers.update({
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        })
    
    @task(10)
    def health_check(self):
        """Check health endpoint - lightweight."""
        self.client.get("/health")
    
    @task(5)
    def hybrid_search(self):
        """Perform hybrid search - medium weight."""
        payload = {
            "query_text": "machine learning research",
            "top_k": 10,
            "collections": []
        }
        self.client.post(
            "/query/hybrid",
            data=json.dumps(payload)
        )
    
    @task(3)
    def keyword_search(self):
        """Perform keyword search - light weight."""
        payload = {
            "query": "KAIST computer science",
            "top_k": 5
        }
        self.client.post(
            "/query/keyword",
            data=json.dumps(payload)
        )
    
    @task(1)
    def metrics_check(self):
        """Check Prometheus metrics - lightweight."""
        self.client.get("/metrics")


class AdminUser(HttpUser):
    """Simulated admin user for testing admin endpoints."""
    
    wait_time = between(5, 10)  # Admins make fewer requests
    weight = 1  # Fewer admin users
    
    def on_start(self):
        """Set up admin headers."""
        self.api_key = os.getenv("VECTOR_API_KEY", "admin-test-key")
        self.client.headers.update({
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        })
    
    @task(3)
    def system_stats(self):
        """Check system statistics."""
        self.client.get("/admin/stats")
    
    @task(1)
    def list_collections(self):
        """List all collections."""
        self.client.get("/admin/collections")


# Load test configuration
if __name__ == "__main__":
    import subprocess
    subprocess.run([
        "locust",
        "-f", __file__,
        "--host", "http://localhost:8000",
        "--users", "10",
        "--spawn-rate", "2",
        "--run-time", "60s",
        "--headless"
    ])
