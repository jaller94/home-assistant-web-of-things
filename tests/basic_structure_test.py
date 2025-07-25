#!/usr/bin/env python3
"""Basic structure test for WoT HTTP component without external dependencies."""

import sys
import os
import traceback

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_file_structure():
    """Test that all required files exist."""
    print("Testing file structure...")
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    required_files = [
        "manifest.json",
        "__init__.py",
        "const.py",
        "config_flow.py",
        "sensor.py",
        "actions.py",
        "strings.json",
        "services.yaml"
    ]
    
    missing_files = []
    for file in required_files:
        file_path = os.path.join(base_dir, file)
        if not os.path.exists(file_path):
            missing_files.append(file)
        else:
            print(f"✓ {file} exists")
    
    if missing_files:
        print(f"✗ Missing files: {missing_files}")
        return False
    
    print("✓ All required files exist!")
    return True

def test_manifest_structure():
    """Test manifest.json structure."""
    print("\nTesting manifest.json...")
    
    try:
        import json
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        manifest_path = os.path.join(base_dir, "manifest.json")
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        required_keys = ["domain", "name", "version", "requirements"]
        for key in required_keys:
            if key not in manifest:
                print(f"✗ Missing key in manifest: {key}")
                return False
            print(f"✓ Manifest has {key}: {manifest[key]}")
        
        print("✓ Manifest structure is valid!")
        return True
    except Exception as e:
        print(f"✗ Manifest test failed: {e}")
        return False

def test_constants():
    """Test constants file."""
    print("\nTesting constants...")
    
    try:
        import const
        
        if not hasattr(const, 'DOMAIN'):
            print("✗ DOMAIN constant not found")
            return False
        
        print(f"✓ DOMAIN constant: {const.DOMAIN}")
        
        if const.DOMAIN != "wot_http":
            print(f"✗ Expected DOMAIN 'wot_http', got '{const.DOMAIN}'")
            return False
        
        print("✓ Constants are valid!")
        return True
    except Exception as e:
        print(f"✗ Constants test failed: {e}")
        traceback.print_exc()
        return False

def test_strings_structure():
    """Test strings.json structure."""
    print("\nTesting strings.json...")
    
    try:
        import json
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        strings_path = os.path.join(base_dir, "strings.json")
        
        with open(strings_path, 'r') as f:
            strings = json.load(f)
        
        if "config" not in strings:
            print("✗ Missing 'config' section in strings.json")
            return False
        
        config = strings["config"]
        required_sections = ["step", "error", "abort"]
        for section in required_sections:
            if section not in config:
                print(f"✗ Missing '{section}' in config")
                return False
            print(f"✓ Config has {section}")
        
        print("✓ Strings structure is valid!")
        return True
    except Exception as e:
        print(f"✗ Strings test failed: {e}")
        return False

def test_code_structure():
    """Test basic code structure without importing."""
    print("\nTesting code structure...")
    
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Test __init__.py has required functions
        init_path = os.path.join(base_dir, "__init__.py")
        with open(init_path, 'r') as f:
            init_content = f.read()
        
        required_functions = ["async_setup", "async_setup_entry", "async_unload_entry"]
        for func in required_functions:
            if func not in init_content:
                print(f"✗ Missing function in __init__.py: {func}")
                return False
            print(f"✓ Found function: {func}")
        
        # Test sensor.py has required classes
        sensor_path = os.path.join(base_dir, "sensor.py")
        with open(sensor_path, 'r') as f:
            sensor_content = f.read()
        
        required_classes = ["WoTDataUpdateCoordinator", "WoTSensor"]
        for cls in required_classes:
            if f"class {cls}" not in sensor_content:
                print(f"✗ Missing class in sensor.py: {cls}")
                return False
            print(f"✓ Found class: {cls}")
        
        # Test actions.py has required class
        actions_path = os.path.join(base_dir, "actions.py")
        with open(actions_path, 'r') as f:
            actions_content = f.read()
        
        if "class WoTActionHandler" not in actions_content:
            print("✗ Missing WoTActionHandler class in actions.py")
            return False
        print("✓ Found class: WoTActionHandler")
        
        print("✓ Code structure is valid!")
        return True
    except Exception as e:
        print(f"✗ Code structure test failed: {e}")
        return False

def run_all_tests():
    """Run all structure tests."""
    print("=" * 50)
    print("Running WoT HTTP Component Structure Tests")
    print("=" * 50)
    
    tests = [
        test_file_structure,
        test_manifest_structure,
        test_constants,
        test_strings_structure,
        test_code_structure,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n{'=' * 50}")
    print(f"Test Results: {passed}/{total} tests passed")
    print(f"{'=' * 50}")
    
    return passed == total

if __name__ == "__main__":
    result = run_all_tests()
    sys.exit(0 if result else 1)