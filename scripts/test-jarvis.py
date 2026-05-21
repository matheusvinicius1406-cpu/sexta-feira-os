#!/usr/bin/env python3
"""
Jarvis API Test Script
Tests all Jarvis endpoints and integration
"""

import requests
import json
import sys
from typing import Dict, Any


BASE_URL = "http://localhost:8000"


class JarvisClient:
    """Simple Jarvis API client"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.user_id = None
        self.token = None
    
    def register(self, email: str, password: str, name: str) -> bool:
        """Register user"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/register",
                json={"email": email, "password": password, "name": name}
            )
            if response.status_code == 200:
                data = response.json()
                self.user_id = data["id"]
                print(f"✅ User registered: {data['id']}")
                return True
            else:
                print(f"❌ Registration failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def login(self, email: str, password: str) -> bool:
        """Login and get token"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": email, "password": password}
            )
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.user_id = data["user_id"]
                print(f"✅ Logged in successfully")
                return True
            else:
                print(f"❌ Login failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with auth"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    def get_jarvis_status(self) -> Dict[str, Any]:
        """Get Jarvis system status"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/jarvis/status",
                headers=self._get_headers()
            )
            if response.status_code == 200:
                data = response.json()
                print("✅ Jarvis Status:")
                print(f"   Status: {data.get('status')}")
                print(f"   Providers: {data.get('providers')}")
                print(f"   Default: {data.get('default_provider')}")
                return data
            else:
                print(f"❌ Error getting status: {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Error: {e}")
            return {}
    
    def chat_with_jarvis(self, message: str) -> Dict[str, Any]:
        """Send message to Jarvis"""
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/jarvis/chat",
                headers=self._get_headers(),
                json={"message": message, "provider": "gemini"}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Jarvis Response:")
                print(f"   Message: {data.get('response')[:200]}...")
                print(f"   Provider: {data.get('provider')}")
                print(f"   Confidence: {data.get('confidence')}")
                return data
            else:
                print(f"❌ Error: {response.status_code}")
                print(f"   {response.text}")
                return {}
        except Exception as e:
            print(f"❌ Error: {e}")
            return {}
    
    def test_memory(self) -> bool:
        """Test memory features"""
        try:
            # Store
            print("\n📝 Testing Memory Storage...")
            response = requests.post(
                f"{self.base_url}/api/v1/jarvis/memory/store",
                headers=self._get_headers(),
                params={"key": "test_key", "value": "test_value"}
            )
            if response.status_code == 200:
                print("✅ Memory stored successfully")
            else:
                print(f"❌ Storage failed: {response.text}")
                return False
            
            # Recall
            print("📖 Testing Memory Recall...")
            response = requests.get(
                f"{self.base_url}/api/v1/jarvis/memory/recall",
                headers=self._get_headers(),
                params={"key": "test_key"}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Memory recalled: {data.get('value')}")
                return True
            else:
                print(f"❌ Recall failed: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False


def main():
    """Run tests"""
    print("\n" + "=" * 60)
    print("  🤖 Jarvis AI System - API Test")
    print("=" * 60)
    
    # Check if server is running
    print("\n🔍 Checking server...")
    try:
        response = requests.get(f"{BASE_URL}/api/v1/health")
        print("✅ Server is running!")
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running!")
        print("\nStart the server with:")
        print("  cd backend-core")
        print("  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
        sys.exit(1)
    
    # Initialize client
    client = JarvisClient()
    
    # Test registration and login
    print("\n" + "=" * 60)
    print("🔑 Authentication Tests")
    print("=" * 60)
    
    test_email = "jarvis@test.com"
    test_password = "testpass123"
    test_name = "Jarvis Test"
    
    # Try to register
    client.register(test_email, test_password, test_name)
    
    # Login
    if not client.login(test_email, test_password):
        # Try with existing user
        test_email = "teste@sextafeira.com"
        test_password = "senha12345"
        client.login(test_email, test_password)
    
    # Test Jarvis endpoints
    print("\n" + "=" * 60)
    print("🤖 Jarvis System Tests")
    print("=" * 60)
    
    # Get status
    print("\n📊 Getting Jarvis Status...")
    client.get_jarvis_status()
    
    # Test memory
    print("\n💾 Testing Memory System...")
    client.test_memory()
    
    # Chat with Jarvis
    print("\n💬 Testing Chat with Jarvis...")
    messages = [
        "Hello Jarvis, what can you do?",
        "Can you tell me about yourself?",
        "What is 2+2?",
    ]
    
    for msg in messages:
        print(f"\n👤 User: {msg}")
        client.chat_with_jarvis(msg)
    
    print("\n" + "=" * 60)
    print("✅ Tests Complete!")
    print("=" * 60)
    print("\n📚 API Documentation: http://localhost:8000/docs")
    print("🤖 Jarvis Status: http://localhost:8000/api/v1/jarvis/status")
    print("")


if __name__ == "__main__":
    main()
