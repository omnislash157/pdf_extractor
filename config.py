# config.py
"""
Bulldozer Configuration File
Simple Python config - no fancy parsers, just variables.
Corporate firewall workaround paths are here.
"""

import os
import platform

# CORPORATE FIREWALL WORKAROUND:
# Manual install paths due to IT restrictions blocking package managers.
# These paths work for mhartigan's Windows setup.
# TODO: Move to auto-detection in v2.3+ when firewall restrictions lifted.

# Detect OS for future portability
IS_WINDOWS = platform.system() == 'Windows'
IS_MAC = platform.system() == 'Darwin'
IS_LINUX = platform.system() == 'Linux'

# User-specific paths (change these if needed)
USER_NAME = os.environ.get('USERNAME', 'mhartigan')  # Windows USERNAME

# Tesseract paths
TESSERACT_PATHS = {
    'mhartigan': r"C:\Users\mhartigan\tools\tesseract\tesseract.exe",
    'default_windows': r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    'default_mac': "/usr/local/bin/tesseract",
    'default_linux': "/usr/bin/tesseract"
}

# Poppler paths
POPPLER_PATHS = {
    'mhartigan': r"C:\Users\mhartigan\tools\poppler-24.08.0\Library\bin",
    'default_windows': r"C:\Program Files\poppler\bin",
    'default_mac': "/usr/local/bin",
    'default_linux': "/usr/bin"
}

def get_tesseract_path():
    """
    Get Tesseract path with loud failures.
    Bulldozer approach: Try user-specific first, then defaults.
    """
    # Try user-specific first
    if USER_NAME in TESSERACT_PATHS:
        path = TESSERACT_PATHS[USER_NAME]
        if os.path.exists(path):
            print(f"✅ Using Tesseract: {path}")
            return path
        print(f"⚠️ User path not found: {path}")
    
    # Try OS defaults
    if IS_WINDOWS and os.path.exists(TESSERACT_PATHS['default_windows']):
        return TESSERACT_PATHS['default_windows']
    elif IS_MAC and os.path.exists(TESSERACT_PATHS['default_mac']):
        return TESSERACT_PATHS['default_mac']
    elif IS_LINUX and os.path.exists(TESSERACT_PATHS['default_linux']):
        return TESSERACT_PATHS['default_linux']
    
    # Bulldozer: Return user path even if not found - let it fail loudly later
    print("❌ WARNING: Tesseract not found! Using hardcoded path anyway...")
    return TESSERACT_PATHS.get(USER_NAME, TESSERACT_PATHS['default_windows'])

def get_poppler_path():
    """
    Get Poppler path with loud failures.
    Returns None if not found (lets pdf2image try system PATH).
    """
    # Try user-specific first
    if USER_NAME in POPPLER_PATHS:
        path = POPPLER_PATHS[USER_NAME]
        if os.path.exists(path):
            print(f"✅ Using Poppler: {path}")
            return path
        print(f"⚠️ User Poppler path not found: {path}")
    
    # Try OS defaults
    if IS_WINDOWS and os.path.exists(POPPLER_PATHS['default_windows']):
        return POPPLER_PATHS['default_windows']
    elif IS_MAC and os.path.exists(POPPLER_PATHS['default_mac']):
        return POPPLER_PATHS['default_mac']
    elif IS_LINUX and os.path.exists(POPPLER_PATHS['default_linux']):
        return POPPLER_PATHS['default_linux']
    
    # Let pdf2image try system PATH
    print("⚠️ No Poppler path found, trying system PATH...")
    return None

# Export the paths
TESSERACT_CMD = get_tesseract_path()
POPPLER_PATH = get_poppler_path()