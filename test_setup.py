#!/usr/bin/env python3
"""
Test script to verify the Issues & Insights Tracker setup
"""
import requests
import time
import sys
import os

def test_backend():
    """Test backend API endpoints"""
    print("Testing backend...")
    
    try:
        # Test health endpoint
        response = requests.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("✓ Backend health check passed")
        else:
            print("✗ Backend health check failed")
            return False
        
        # Test API docs
        response = requests.get("http://localhost:8000/api/docs")
        if response.status_code == 200:
            print("✓ API docs accessible")
        else:
            print("✗ API docs not accessible")
            return False
            
        return True
        
    except requests.exceptions.ConnectionError:
        print("✗ Backend not running on localhost:8000")
        return False
    except Exception as e:
        print(f"✗ Backend test error: {e}")
        return False

def test_frontend():
    """Test frontend"""
    print("Testing frontend...")
    
    try:
        # Test frontend
        response = requests.get("http://localhost:5173")
        if response.status_code == 200:
            print("✓ Frontend accessible")
            return True
        else:
            print("✗ Frontend not accessible")
            return False
            
    except requests.exceptions.ConnectionError:
        print("✗ Frontend not running on localhost:5173")
        return False
    except Exception as e:
        print(f"✗ Frontend test error: {e}")
        return False

def test_database():
    """Test database connection"""
    print("Testing database...")
    
    try:
        # Import and test database
        sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
        from app.database import SessionLocal
        from app.models import User
        
        db = SessionLocal()
        # Try to query users table
        users = db.query(User).limit(1).all()
        print("✓ Database connection successful")
        db.close()
        return True
        
    except Exception as e:
        print(f"✗ Database test error: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Issues & Insights Tracker Setup Test ===\n")
    
    tests = [
        ("Database", test_database),
        ("Backend", test_backend),
        ("Frontend", test_frontend),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        if test_func():
            passed += 1
        time.sleep(1)  # Small delay between tests
    
    print(f"\n=== Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! The application is ready to use.")
        print("\nAccess the application:")
        print("- Frontend: http://localhost:5173")
        print("- Backend API: http://localhost:8000")
        print("- API Docs: http://localhost:8000/api/docs")
    else:
        print("❌ Some tests failed. Please check the setup.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 