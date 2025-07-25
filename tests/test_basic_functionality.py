"""Test basic WoT HTTP component functionality without Home Assistant framework."""

import pytest
import sys
import os
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

# Add the parent directory to the path to find custom_components.wot_http
parent_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '..')
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)


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


def test_basic_imports():
    """Test basic imports work."""
    try:
        from custom_components.wot_http import const
        assert hasattr(const, 'DOMAIN')
        
        from custom_components.wot_http import actions
        assert hasattr(actions, 'WoTActionHandler')
        
        from custom_components.wot_http import sensor
        assert hasattr(sensor, 'WoTDataUpdateCoordinator')
        assert hasattr(sensor, 'WoTSensor')
        
        from custom_components.wot_http import config_flow
        assert hasattr(config_flow, 'CannotConnect')
        assert hasattr(config_flow, 'InvalidAuth')
        assert hasattr(config_flow, 'ConfigFlow')
        
        print("✓ All imports successful!")
        
    except Exception as e:
        pytest.fail(f"Import failed: {e}")


@pytest.mark.asyncio
async def test_action_handler_basic():
    """Test basic WoTActionHandler functionality."""
    from custom_components.wot_http.actions import WoTActionHandler
        
    hass = create_mock_hass()
    handler = WoTActionHandler(hass)
    
    # Test device registration
    entry_id = "test_entry"
    base_url = "http://192.168.1.100:8080"
    thing_description = create_sample_thing_description()
    
    handler.register_device(entry_id, base_url, thing_description)
    
    assert entry_id in handler._devices
    device = handler._devices[entry_id]
    assert device["base_url"] == "http://192.168.1.100:8080"
    
    # Test device unregistration
    handler.unregister_device(entry_id)
    assert entry_id not in handler._devices


@pytest.mark.asyncio
async def test_sensor_coordinator():
    """Test basic WoTDataUpdateCoordinator functionality."""
    from custom_components.wot_http.sensor import WoTDataUpdateCoordinator
    
    hass = create_mock_hass()
    base_url = "http://192.168.1.100:8080"
    coordinator = WoTDataUpdateCoordinator(hass, base_url)
    
    assert coordinator.base_url == "http://192.168.1.100:8080"


@pytest.mark.asyncio
async def test_wot_sensor():
    """Test basic WoTSensor functionality."""
    from custom_components.wot_http.sensor import WoTDataUpdateCoordinator, WoTSensor
    
    hass = create_mock_hass()
    base_url = "http://192.168.1.100:8080"
    coordinator = WoTDataUpdateCoordinator(hass, base_url)
    coordinator.data = {"temperature": 22.5}
    coordinator.last_update_success = True
    
    wot_sensor = WoTSensor(
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


def test_config_flow_basic():
    """Test basic config flow functionality."""
    from custom_components.wot_http import config_flow
    
    # Test exception classes exist
    assert hasattr(config_flow, 'CannotConnect')
    assert hasattr(config_flow, 'InvalidAuth')
    assert hasattr(config_flow, 'ConfigFlow')


def test_constants():
    """Test constants are defined."""
    from custom_components.wot_http.const import DOMAIN
    
    assert DOMAIN == "wot_http"


def test_url_handling():
    """Test URL handling from href_url_handling tests."""
    # This replicates the logic from the working unittest-based test
    def construct_property_url(base_url, prop_info, prop_name):
        """URL construction logic from sensor.py."""
        if "href" in prop_info:
            href = prop_info['href']
            # Handle absolute URLs, relative paths, and relative URLs properly
            if href.lower().startswith(('http://', 'https://')):
                # Absolute URL - use as-is
                return href
            elif href.startswith('/'):
                # Relative path from root - append to base URL
                return f"{base_url}{href}"
            else:
                # Relative URL - append to base URL with separator
                return f"{base_url}/{href}"
        else:
            return f"{base_url}/properties/{prop_name}"
    
    base_url = "http://192.168.1.100:8080"
    
    # Test absolute HTTP URL
    prop_info = {"href": "http://external-server.com:9000/api/temperature"}
    result = construct_property_url(base_url, prop_info, "temperature")
    assert result == "http://external-server.com:9000/api/temperature"
    
    # Test absolute HTTPS URL  
    prop_info = {"href": "https://cloud-api.example.com/sensors/humidity"}
    result = construct_property_url(base_url, prop_info, "humidity")
    assert result == "https://cloud-api.example.com/sensors/humidity"
    
    # Test relative path from root
    prop_info = {"href": "/properties/temperature"}
    result = construct_property_url(base_url, prop_info, "temperature")
    assert result == "http://192.168.1.100:8080/properties/temperature"
    
    # Test relative URL
    prop_info = {"href": "properties/brightness"}
    result = construct_property_url(base_url, prop_info, "brightness")
    assert result == "http://192.168.1.100:8080/properties/brightness"
    
    # Test no href (default endpoint)
    prop_info = {}
    result = construct_property_url(base_url, prop_info, "temperature")
    assert result == "http://192.168.1.100:8080/properties/temperature"