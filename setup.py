#!/usr/bin/env python3
"""
Setup script for Recipe Automation System
Helps install dependencies and configure the system
"""

import os
import sys
import subprocess
import platform

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        return False
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    return True

def install_python_dependencies():
    """Install Python dependencies"""
    print("📦 Installing Python dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Python dependencies installed")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to install Python dependencies")
        return False

def check_tesseract():
    """Check if Tesseract OCR is installed"""
    print("🔍 Checking Tesseract OCR...")
    try:
        result = subprocess.run(["tesseract", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Tesseract OCR found")
            return True
        else:
            print("❌ Tesseract OCR not found")
            return False
    except FileNotFoundError:
        print("❌ Tesseract OCR not found")
        return False

def install_tesseract():
    """Install Tesseract OCR based on platform"""
    system = platform.system().lower()
    
    print(f"🔧 Installing Tesseract OCR for {system}...")
    
    if system == "darwin":  # macOS
        try:
            subprocess.check_call(["brew", "install", "tesseract"])
            print("✅ Tesseract OCR installed via Homebrew")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Homebrew not found. Please install Homebrew first:")
            print("   /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            return False
    
    elif system == "linux":
        try:
            subprocess.check_call(["sudo", "apt-get", "update"])
            subprocess.check_call(["sudo", "apt-get", "install", "-y", "tesseract-ocr"])
            print("✅ Tesseract OCR installed via apt")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install Tesseract OCR")
            print("   Please install manually: sudo apt-get install tesseract-ocr")
            return False
    
    elif system == "windows":
        print("❌ Please install Tesseract OCR manually for Windows:")
        print("   Download from: https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    
    else:
        print(f"❌ Unsupported platform: {system}")
        return False

def check_api_key():
    """Check if API key file exists"""
    if os.path.exists("API_KEY.txt"):
        print("✅ API key file found")
        return True
    else:
        print("❌ API key file not found")
        print("   Please create API_KEY.txt with your OpenAI API key")
        return False

def create_directories():
    """Create necessary directories"""
    directories = ["./Original-Images", "./Products"]
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 Created directory: {directory}")
        else:
            print(f"✅ Directory exists: {directory}")

def run_test():
    """Run system test"""
    print("🧪 Running system test...")
    try:
        result = subprocess.run([sys.executable, "test_system.py"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ System test passed")
            return True
        else:
            print("❌ System test failed")
            print(result.stdout)
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Failed to run system test: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Recipe Automation System - Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        return False
    
    # Install Python dependencies
    if not install_python_dependencies():
        return False
    
    # Check/install Tesseract
    if not check_tesseract():
        if not install_tesseract():
            print("⚠️  Tesseract installation failed. Please install manually.")
            print("   You can still run the system, but OCR may not work.")
    
    # Check API key
    if not check_api_key():
        print("⚠️  Please add your OpenAI API key to API_KEY.txt")
        print("   You can still run the system, but content generation won't work.")
    
    # Create directories
    create_directories()
    
    # Run test
    print("\n" + "=" * 50)
    print("🎯 Setup Summary:")
    
    if check_tesseract():
        print("✅ Tesseract OCR: Ready")
    else:
        print("❌ Tesseract OCR: Not installed")
    
    if check_api_key():
        print("✅ API Key: Ready")
    else:
        print("❌ API Key: Missing")
    
    print("✅ Python Dependencies: Installed")
    print("✅ Directories: Created")
    
    # Final instructions
    print("\n📋 Next Steps:")
    print("1. Add your OpenAI API key to API_KEY.txt")
    print("2. Place recipe images in the Original-Images/ directory")
    print("3. Run: python test_system.py")
    print("4. If tests pass, run: python recipe_automation_v2.py")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 