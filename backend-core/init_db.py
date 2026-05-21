"""
Initialize the database with tables
"""
import sys
import os

# Add the backend-core directory to the path
sys.path.insert(0, '/workspaces/sexta-feira-os/backend-core')

from app.db.database import Base, engine
from app.models.models import User, ChatMessage, MemoryEntry, AutomationTask

# Create all tables
print("Creating database tables...")
Base.metadata.create_all(bind=engine)
print("✅ Database tables created successfully!")
