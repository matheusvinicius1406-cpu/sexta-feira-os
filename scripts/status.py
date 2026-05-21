#!/usr/bin/env python3
"""
Sexta-Feira OS + Jarvis System Status Dashboard
Shows current system status and configuration
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime


class StatusDashboard:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent  # Go up from scripts/ to root
        self.backend_path = self.base_path / "backend-core"
    
    def check_backend(self):
        """Check backend components"""
        print("\n🔧 Backend Status")
        print("-" * 50)
        
        checks = {
            "FastAPI Main": self.backend_path / "app/main.py",
            "Jarvis Core": self.backend_path / "app/jarvis/core.py",
            "Gemini Provider": self.backend_path / "app/jarvis/gemini.py",
            "AI Orchestrator": self.backend_path / "app/ai/orchestrator.py",
            "Jarvis Router": self.backend_path / "app/api/routers/jarvis.py",
            "Database Models": self.backend_path / "app/models/models.py",
            "Auth Module": self.backend_path / "app/auth/jwt.py",
        }
        
        for name, path in checks.items():
            status = "✅" if path.exists() else "❌"
            print(f"{status} {name:<25} {path.name}")
        
        return all(p.exists() for p in checks.values())
    
    def check_database(self):
        """Check database"""
        print("\n💾 Database Status")
        print("-" * 50)
        
        db_path = self.backend_path / "data/sexta_feira_os.db"
        
        if db_path.exists():
            size = db_path.stat().st_size / 1024  # KB
            print(f"✅ Database File: {db_path.name}")
            print(f"   Size: {size:.2f} KB")
            print(f"   Location: {db_path}")
            return True
        else:
            print(f"❌ Database File: Not found")
            print(f"   Expected: {db_path}")
            return False
    
    def check_environment(self):
        """Check environment variables"""
        print("\n🔐 Environment Configuration")
        print("-" * 50)
        
        config = {
            "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", "NOT SET"),
            "DEFAULT_AI_PROVIDER": os.getenv("DEFAULT_AI_PROVIDER", "gemini"),
            "BACKEND_HOST": os.getenv("BACKEND_HOST", "0.0.0.0"),
            "BACKEND_PORT": os.getenv("BACKEND_PORT", "8000"),
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        }
        
        for key, value in config.items():
            if "KEY" in key or "SECRET" in key:
                display = "SET" if value != "NOT SET" else "❌ NOT SET"
                status = "✅" if value != "NOT SET" else "⚠️ "
            else:
                display = value
                status = "✅"
            
            print(f"{status} {key:<25} {display}")
        
        return os.getenv("GEMINI_API_KEY") is not None
    
    def check_dependencies(self):
        """Check Python dependencies"""
        print("\n📦 Dependencies")
        print("-" * 50)
        
        required = [
            "fastapi",
            "uvicorn",
            "sqlalchemy",
            "pydantic",
            "google.generativeai",
            "passlib",
            "argon2",
        ]
        
        try:
            import pkg_resources
            installed = {pkg.key for pkg in pkg_resources.working_set}
            
            for package in required:
                short_name = package.split(".")[0]
                status = "✅" if short_name in installed else "❌"
                print(f"{status} {package}")
            
            return all(p.split(".")[0] in installed for p in required)
        except:
            print("⚠️  Could not check dependencies")
            return False
    
    def check_mobile(self):
        """Check mobile app"""
        print("\n📱 Android App Status")
        print("-" * 50)
        
        checks = {
            "MainActivity": self.base_path / "mobile-android/app/src/main/kotlin/com/sextafeira/os/MainActivity.kt",
            "Chat Screen": self.base_path / "mobile-android/app/src/main/kotlin/com/sextafeira/os/ui/screens/ChatAssistantScreen.kt",
            "API Client": self.base_path / "mobile-android/app/src/main/kotlin/com/sextafeira/os/data/api/SextaFeiraApi.kt",
            "Gradle Config": self.base_path / "mobile-android/app/build.gradle.kts",
        }
        
        for name, path in checks.items():
            status = "✅" if path.exists() else "❌"
            print(f"{status} {name:<25} {'READY' if path.exists() else 'MISSING'}")
        
        return all(p.exists() for p in checks.values())
    
    def show_quick_start(self):
        """Show quick start commands"""
        print("\n🚀 Quick Start")
        print("-" * 50)
        
        print("1. Configure Gemini API Key:")
        print("   export GEMINI_API_KEY=your-key-here")
        print()
        print("2. Start Backend:")
        print("   cd backend-core")
        print("   pip install -r requirements.txt")
        print("   python init_db.py")
        print("   uvicorn app.main:app --reload")
        print()
        print("3. Test System:")
        print("   python scripts/test-jarvis.py")
        print()
        print("4. Browse API:")
        print("   http://localhost:8000/docs")
        print()
        print("5. Get Jarvis Status:")
        print("   curl http://localhost:8000/api/v1/jarvis/status")
    
    def show_endpoints(self):
        """Show available endpoints"""
        print("\n📡 Available Endpoints")
        print("-" * 50)
        
        endpoints = {
            "Health Check": "GET /api/v1/health",
            "Register": "POST /api/v1/auth/register",
            "Login": "POST /api/v1/auth/login",
            "Chat": "POST /api/v1/chat/",
            "Chat History": "GET /api/v1/chat/history",
            "Jarvis Status": "GET /api/v1/jarvis/status",
            "Jarvis Chat": "POST /api/v1/jarvis/chat",
            "Jarvis Analyze": "POST /api/v1/jarvis/analyze",
            "Memory Store": "POST /api/v1/jarvis/memory/store",
            "Memory Recall": "GET /api/v1/jarvis/memory/recall",
            "API Docs": "GET /docs",
            "ReDoc": "GET /redoc",
        }
        
        for name, endpoint in endpoints.items():
            print(f"  {endpoint:<35} {name}")
    
    def run_full_check(self):
        """Run complete system check"""
        print("\n" + "=" * 60)
        print("  🤖 Sexta-Feira OS + Jarvis System Status")
        print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("=" * 60)
        
        results = {
            "Backend": self.check_backend(),
            "Database": self.check_database(),
            "Environment": self.check_environment(),
            "Dependencies": self.check_dependencies(),
            "Mobile": self.check_mobile(),
        }
        
        self.show_endpoints()
        self.show_quick_start()
        
        print("\n" + "=" * 60)
        print("📊 Overall Status")
        print("=" * 60)
        
        for component, status in results.items():
            status_str = "✅ READY" if status else "⚠️  INCOMPLETE"
            print(f"{status_str:<15} {component}")
        
        all_ready = all(results.values())
        
        print("\n" + "=" * 60)
        if all_ready:
            print("✅ System is READY! Start backend and run tests.")
        else:
            print("⚠️  System has INCOMPLETE components. See above for details.")
        print("=" * 60 + "\n")
        
        return all_ready


def main():
    """Run dashboard"""
    try:
        os.chdir(Path(__file__).parent)
        dashboard = StatusDashboard()
        ready = dashboard.run_full_check()
        sys.exit(0 if ready else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
