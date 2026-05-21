"""
Jarvis AI Setup Helper
Assists with configuration and first-time setup
"""

import os
import sys
from pathlib import Path


def setup_gemini():
    """Setup Gemini API key"""
    print("\n🔑 Gemini API Setup")
    print("==================")
    print("1. Go to https://makersuite.google.com/app/apikey")
    print("2. Click 'Create API Key'")
    print("3. Copy your API key")
    print("")
    
    key = input("Paste your Gemini API key (or press Enter to skip): ").strip()
    
    if key:
        # Update .env file
        env_file = Path(".env")
        if env_file.exists():
            content = env_file.read_text()
            content = content.replace(
                "GEMINI_API_KEY=your-gemini-api-key-here",
                f"GEMINI_API_KEY={key}"
            )
            env_file.write_text(content)
            print("✅ Gemini API key saved to .env")
            os.environ["GEMINI_API_KEY"] = key
            return True
        else:
            print("⚠️ .env file not found. Setting environment variable...")
            os.environ["GEMINI_API_KEY"] = key
            return True
    else:
        print("⏭️  Skipping Gemini setup. System will use mock responses.")
        return False


def test_gemini_connection():
    """Test Gemini connection"""
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("\n⚠️  Gemini API key not configured")
        print("   The system will use mock AI responses for demonstration")
        return False
    
    print("\n🧪 Testing Gemini Connection...")
    try:
        # Try to import and initialize
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        
        # Simple test
        response = model.generate_content("Say 'Jarvis initialized successfully'")
        if response.text:
            print(f"✅ Gemini connection successful!")
            print(f"   Response: {response.text[:100]}...")
            return True
        else:
            print("❌ Gemini returned empty response")
            return False
    
    except Exception as e:
        print(f"❌ Error testing Gemini: {e}")
        print("   System will use mock responses")
        return False


def show_status():
    """Show system status"""
    print("\n📊 Jarvis System Status")
    print("======================")
    
    # Check components
    checks = {
        "Backend Code": Path("app/main.py").exists(),
        "Jarvis Module": Path("app/jarvis/__init__.py").exists(),
        "Database": Path("data/sexta_feira_os.db").exists(),
        "Gemini Key": bool(os.getenv("GEMINI_API_KEY")),
    }
    
    for component, status in checks.items():
        status_str = "✅" if status else "❌"
        print(f"{status_str} {component}")
    
    return all(checks.values())


def main():
    """Run setup"""
    print("\n" + "=" * 50)
    print("  🤖 Jarvis AI System - Setup Helper")
    print("=" * 50)
    
    # Show current status
    show_status()
    
    # Setup Gemini
    print("\n")
    setup_gemini()
    
    # Test connection
    test_gemini_connection()
    
    print("\n" + "=" * 50)
    print("✅ Setup complete!")
    print("=" * 50)
    print("\nTo start the system:")
    print("  cd backend-core")
    print("  uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload")
    print("\nThen visit:")
    print("  http://localhost:8000/docs")
    print("  http://localhost:8000/api/v1/jarvis/status")
    print("")


if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent / "backend-core")
    main()
