#!/usr/bin/env python3
"""Simple test runner for WoT HTTP component tests without pytest."""

import sys
import os
import asyncio
import traceback
from unittest.mock import MagicMock, AsyncMock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_mock_hass():
    """Create a mock Home Assistant instance."""
    hass = MagicMock()
    hass.data = {}
    hass.services = MagicMock()
    hass.services.has_service = MagicMock(return_value=False)
    hass.services.async_register = MagicMock()
    hass.services.async_remove = MagicMock()
    hass.config_entries = MagicMock()
    hass.config_entries.flow = MagicMock()
    hass.config_entries.async_forward_entry_setups = AsyncMock(return_value=True)
    hass.config_entries.async_unload_platforms = AsyncMock(return_value=True)
    hass.helpers = MagicMock()
    hass.helpers.discovery = MagicMock()
    hass.helpers.discovery.async_load_platform = AsyncMock()
    hass.async_create_task = MagicMock()
    hass.async_block_till_done = AsyncMock()
    return hass

def create_sample_thing_description():
    """Create sample Thing Description for testing."""
    return {
        "@context": "https://www.w3.org/2019/wot/td/v1",
        "title": "Test Device",
        "properties": {
            "temperature": {
                "type": "number",
                "unit": "celsius",
                "readOnly": True
            },
            "brightness": {
                "type": "number",
                "minimum": 0,
                "maximum": 100
            }
        },
        "actions": {
            "toggle": {
                "description": "Toggle device on/off"
            },
            "setBrightness": {
                "description": "Set brightness level",
                "input": {
                    "type": "object",
                    "properties": {
                        "brightness": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100
                        }
                    },
                    "required": ["brightness"]
                },
                "href": "/actions/setBrightness"
            }
        }
    }

async def test_basic_imports():
    """Test basic imports work."""
    print("Testing basic imports...")
    
    try:
        import const
        print(f"✓ Domain imported: {const.DOMAIN}")
        
        import actions
        print("✓ Actions module imported")
        
        import sensor
        print("✓ Sensor module imported")
        
        import config_flow
        print("✓ Config flow imported")
        
        print("✓ All imports successful!")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False

async def test_action_handler_basic():
    """Test basic WoTActionHandler functionality."""
    print("\nTesting WoTActionHandler...")
    
    try:
        import actions
        
        hass = create_mock_hass()
        handler = actions.WoTActionHandler(hass)
        
        # Test device registration
        entry_id = "test_entry"
        thing_description = create_sample_thing_description()
        
        handler.register_device(entry_id, "192.168.1.100", 8080, thing_description)
        
        assert entry_id in handler._devices
        device = handler._devices[entry_id]
        assert device["host"] == "192.168.1.100"
        assert device["port"] == 8080
        
        # Test device unregistration
        handler.unregister_device(entry_id)
        assert entry_id not in handler._devices
        
        print("✓ WoTActionHandler basic functionality works!")
        return True
    except Exception as e:
        print(f"✗ WoTActionHandler test failed: {e}")
        traceback.print_exc()
        return False

async def test_sensor_coordinator():
    """Test basic WoTDataUpdateCoordinator functionality."""
    print("\nTesting WoTDataUpdateCoordinator...")
    
    try:
        import sensor
        
        hass = create_mock_hass()
        coordinator = sensor.WoTDataUpdateCoordinator(hass, "192.168.1.100", 8080)
        
        assert coordinator.host == "192.168.1.100"
        assert coordinator.port == 8080
        assert coordinator.base_url == "http://192.168.1.100:8080"
        
        print("✓ WoTDataUpdateCoordinator basic functionality works!")
        return True
    except Exception as e:
        print(f"✗ WoTDataUpdateCoordinator test failed: {e}")
        traceback.print_exc()
        return False

async def test_wot_sensor():
    """Test basic WoTSensor functionality."""
    print("\nTesting WoTSensor...")
    
    try:
        import sensor
        
        hass = create_mock_hass()
        coordinator = sensor.WoTDataUpdateCoordinator(hass, "192.168.1.100", 8080)
        coordinator.data = {"temperature": 22.5}
        coordinator.last_update_success = True
        
        wot_sensor = sensor.WoTSensor(
            coordinator=coordinator,
            name="Test Temperature",
            property_key="temperature",
            data_type="number",
            unit="°C"
        )
        
        assert wot_sensor.name == "Test Temperature"
        assert wot_sensor.native_value == 22.5
        assert wot_sensor.native_unit_of_measurement == "°C"
        assert wot_sensor.available is True
        
        print("✓ WoTSensor basic functionality works!")
        return True
    except Exception as e:
        print(f"✗ WoTSensor test failed: {e}")
        traceback.print_exc()
        return False

async def test_config_flow_basic():
    """Test basic config flow functionality."""
    print("\nTesting config flow...")
    
    try:
        import config_flow
        
        # Test exception classes exist
        assert hasattr(config_flow, 'CannotConnect')
        assert hasattr(config_flow, 'InvalidAuth')
        assert hasattr(config_flow, 'ConfigFlow')
        
        print("✓ Config flow basic functionality works!")
        return True
    except Exception as e:
        print(f"✗ Config flow test failed: {e}")
        traceback.print_exc()
        return False

async def run_all_tests():
    """Run all basic tests."""
    print("=" * 50)
    print("Running WoT HTTP Component Basic Tests")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_action_handler_basic,
        test_sensor_coordinator,
        test_wot_sensor,
        test_config_flow_basic,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} failed with exception: {e}")
    
    print(f"\n{'=' * 50}")
    print(f"Test Results: {passed}/{total} tests passed")
    print(f"{'=' * 50}")
    
    return passed == total

if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)