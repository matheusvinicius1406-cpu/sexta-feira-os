"""Copy .env from project root to backend-core/.env"""
import shutil, os

src = os.path.join(os.path.dirname(__file__), "..", ".env")
dst = os.path.join(os.path.dirname(__file__), "..", "backend-core", ".env")
src = os.path.normpath(src)
dst = os.path.normpath(dst)

shutil.copy2(src, dst)
print(f"Copied {src} -> {dst}")

# Verify
with open(dst) as f:
    content = f.read()
has_secret = "N8N_CALLBACK_SECRET" in content
print(f"Has N8N_CALLBACK_SECRET: {has_secret}")
