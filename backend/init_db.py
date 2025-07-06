#!/usr/bin/env python3
import os
import sys
from sqlalchemy import create_engine
from app.models import Base
from app.database import DATABASE_URL

def init_db():
    """Initialize the database with all tables."""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db() 