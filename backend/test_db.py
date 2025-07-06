#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine, text
from app.models import Base
from app.database import DATABASE_URL

def test_db():
    """Test database connection and initialization."""
    print(f"Database URL: {DATABASE_URL}")
    
    try:
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("Database connection successful!")
        
        # Create tables
        Base.metadata.create_all(bind=engine)
        print("Database tables created successfully!")
        
    except Exception as e:
        print(f"Database error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_db() 