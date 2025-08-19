#!/usr/bin/env python3
"""
Test script to validate bot functionality and dependencies.
Run this before deploying to Railway to catch any issues.
"""

import sys
import importlib
import logging
from typing import List, Tuple

def test_imports() -> List[Tuple[str, bool, str]]:
    """Test all required imports."""
    results = []
    
    # Core dependencies
    test_modules = [
        ('telegram', 'python-telegram-bot'),
        ('telegram.ext', 'python-telegram-bot extensions'),
        ('requests', 'HTTP requests'),
        ('bs4', 'BeautifulSoup4'),
        ('PIL', 'Pillow'),
        ('dotenv', 'python-dotenv'),
        ('lxml', 'lxml parser')
    ]
    
    for module, description in test_modules:
        try:
            importlib.import_module(module)
            results.append((description, True, "OK"))
        except ImportError as e:
            results.append((description, False, str(e)))
    
    return results

def test_telegram_version() -> Tuple[bool, str]:
    """Test telegram library version compatibility."""
    try:
        import telegram
        version = telegram.__version__
        major_version = int(version.split('.')[0])
        
        if major_version >= 20:
            return True, f"Version {version} - Compatible"
        else:
            return False, f"Version {version} - Needs upgrade to v20+"
    except Exception as e:
        return False, f"Error checking version: {str(e)}"

def test_bot_modules() -> List[Tuple[str, bool, str]]:
    """Test custom bot modules."""
    results = []
    
    bot_modules = [
        'config',
        'utils', 
        'scraper',
        'cache',
        'image_handler'
    ]
    
    for module in bot_modules:
        try:
            importlib.import_module(module)
            results.append((f"{module}.py", True, "OK"))
        except ImportError as e:
            results.append((f"{module}.py", False, str(e)))
    
    return results

def test_config_values() -> List[Tuple[str, bool, str]]:
    """Test configuration values."""
    results = []
    
    try:
        from config import BOT_TOKEN, BOT_USERNAME
        
        # Test bot token
        if BOT_TOKEN and BOT_TOKEN != "YOUR_BOT_TOKEN_HERE":
            results.append(("BOT_TOKEN", True, "Configured"))
        else:
            results.append(("BOT_TOKEN", False, "Not configured"))
        
        # Test bot username
        if BOT_USERNAME and BOT_USERNAME.startswith("@"):
            results.append(("BOT_USERNAME", True, f"Set to {BOT_USERNAME}"))
        else:
            results.append(("BOT_USERNAME", False, "Invalid format"))
            
    except ImportError as e:
        results.append(("Config import", False, str(e)))
    
    return results

def test_async_compatibility() -> Tuple[bool, str]:
    """Test async/await compatibility."""
    try:
        import asyncio
        
        async def test_async():
            return "async works"
        
        # Test if we can run async code
        result = asyncio.run(test_async())
        return True, "Async/await compatible"
    except Exception as e:
        return False, f"Async error: {str(e)}"

def main():
    """Run all tests and display results."""
    print("🤖 ReviewCheckk Bot - Validation Tests")
    print("=" * 50)
    
    all_passed = True
    
    # Test imports
    print("\n📦 Testing Dependencies:")
    import_results = test_imports()
    for desc, passed, msg in import_results:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}: {msg}")
        if not passed:
            all_passed = False
    
    # Test telegram version
    print("\n📡 Testing Telegram Library:")
    version_passed, version_msg = test_telegram_version()
    status = "✅" if version_passed else "❌"
    print(f"  {status} python-telegram-bot: {version_msg}")
    if not version_passed:
        all_passed = False
    
    # Test bot modules
    print("\n🔧 Testing Bot Modules:")
    module_results = test_bot_modules()
    for desc, passed, msg in module_results:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}: {msg}")
        if not passed:
            all_passed = False
    
    # Test config
    print("\n⚙️ Testing Configuration:")
    config_results = test_config_values()
    for desc, passed, msg in config_results:
        status = "✅" if passed else "❌"
        print(f"  {status} {desc}: {msg}")
        if not passed:
            all_passed = False
    
    # Test async
    print("\n🔄 Testing Async Compatibility:")
    async_passed, async_msg = test_async_compatibility()
    status = "✅" if async_passed else "❌"
    print(f"  {status} Async/await: {async_msg}")
    if not async_passed:
        all_passed = False
    
    # Final result
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Bot is ready for Railway deployment.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please fix the issues before deploying.")
        sys.exit(1)

if __name__ == "__main__":
    main()
