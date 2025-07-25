"""Test the WoT HTTP actions functionality."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import voluptuous as vol

from homeassistant.core import ServiceCall
from homeassistant.exceptions import HomeAssistantError

from custom_components.wot_http.actions import WoTActionHandler


@pytest.fixture
def action_handler(hass):
    """Create a WoTActionHandler instance."""
    return WoTActionHandler(hass)


@pytest.fixture
def sample_action_schema():
    """Sample action with input schema."""
    return {
        "setBrightness": {
            "description": "Set brightness level",
            "input": {
                "type": "object",
                "properties": {
                    "brightness": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 100
                    },
                    "duration": {
                        "type": "integer",
                        "minimum": 0,
                        "default": 1000
                    }
                },
                "required": ["brightness"]
            },
            "href": "/actions/setBrightness"
        }
    }


async def test_register_device_with_actions(hass, action_handler, sample_thing_description):
    """Test registering a device with actions."""
    entry_id = "test_entry_123"
    
    action_handler.register_device(
        entry_id, "192.168.1.100", 8080, sample_thing_description
    )
    
    # Verify device is registered
    assert entry_id in action_handler._devices
    device = action_handler._devices[entry_id]
    assert device["host"] == "192.168.1.100"
    assert device["port"] == 8080
    assert device["base_url"] == "http://192.168.1.100:8080"
    assert device["thing_description"] == sample_thing_description
    
    # Verify services are registered
    assert hass.services.has_service("wot_http", f"{entry_id}_toggle")
    assert hass.services.has_service("wot_http", f"{entry_id}_setBrightness")


async def test_register_device_without_actions(hass, action_handler):
    """Test registering a device without actions."""
    entry_id = "test_entry_456"
    thing_description = {
        "@context": "https://www.w3.org/2019/wot/td/v1",
        "title": "Simple Device",
        "properties": {
            "state": {"type": "string"}
        }
    }
    
    action_handler.register_device(
        entry_id, "192.168.1.101", 8080, thing_description
    )
    
    # Device should be registered but no services
    assert entry_id in action_handler._devices
    assert not hass.services.has_service("wot_http", f"{entry_id}_toggle")


async def test_unregister_device(hass, action_handler, sample_thing_description):
    """Test unregistering a device and its services."""
    entry_id = "test_entry_789"
    
    # Register device first
    action_handler.register_device(
        entry_id, "192.168.1.100", 8080, sample_thing_description
    )
    
    assert hass.services.has_service("wot_http", f"{entry_id}_toggle")
    
    # Unregister device
    action_handler.unregister_device(entry_id)
    
    # Verify device and services are removed
    assert entry_id not in action_handler._devices
    assert not hass.services.has_service("wot_http", f"{entry_id}_toggle")


async def test_execute_simple_action(hass, action_handler, sample_thing_description, mock_aiohttp_session):
    """Test executing a simple action without parameters."""
    entry_id = "test_entry_simple"
    action_handler.register_device(
        entry_id, "192.168.1.100", 8080, sample_thing_description
    )
    
    # Mock HTTP response
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"result": "success"})
    mock_session_instance.request.return_value.__aenter__.return_value = mock_response
    
    # Create service call
    service_call = ServiceCall("wot_http", f"{entry_id}_toggle", {})
    
    # Execute action
    service_handler = action_handler._create_action_handler(entry_id, "toggle")
    await service_handler(service_call)
    
    # Verify HTTP request was made
    mock_session_instance.request.assert_called_once()
    call_args = mock_session_instance.request.call_args
    assert call_args[0][0] == "POST"  # HTTP method
    assert call_args[0][1] == "http://192.168.1.100:8080/actions/toggle"  # URL


async def test_execute_action_with_parameters(hass, action_handler, sample_thing_description, mock_aiohttp_session):
    """Test executing an action with parameters."""
    entry_id = "test_entry_params"
    action_handler.register_device(
        entry_id, "192.168.1.100", 8080, sample_thing_description
    )
    
    # Mock HTTP response
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_session_instance.request.return_value.__aenter__.return_value = mock_response
    
    # Create service call with parameters
    service_call = ServiceCall("wot_http", f"{entry_id}_setBrightness", {"brightness": 75})
    
    # Execute action
    service_handler = action_handler._create_action_handler(entry_id, "setBrightness")
    await service_handler(service_call)
    
    # Verify HTTP request was made with correct parameters
    mock_session_instance.request.assert_called_once()
    call_args = mock_session_instance.request.call_args
    assert call_args[0][0] == "POST"
    assert call_args[0][1] == "http://192.168.1.100:8080/actions/setBrightness"
    assert call_args[1]["json"] == {"brightness": 75}


async def test_execute_action_http_error(hass, action_handler, sample_thing_description, mock_aiohttp_session):
    """Test action execution with HTTP error response."""
    entry_id = "test_entry_error"
    action_handler.register_device(
        entry_id, "192.168.1.100", 8080, sample_thing_description
    )
    
    # Mock HTTP error response
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    
    mock_response = AsyncMock()
    mock_response.status = 500
    mock_response.text = AsyncMock(return_value="Internal Server Error")
    mock_session_instance.request.return_value.__aenter__.return_value = mock_response
    
    # Create service call
    service_call = ServiceCall("wot_http", f"{entry_id}_toggle", {})
    
    # Execute action and expect error
    service_handler = action_handler._create_action_handler(entry_id, "toggle")
    with pytest.raises(HomeAssistantError, match="Action toggle failed with status 500"):
        await service_handler(service_call)


async def test_execute_action_connection_error(hass, action_handler, sample_thing_description, mock_aiohttp_session):
    """Test action execution with connection error."""
    entry_id = "test_entry_conn_error"
    action_handler.register_device(
        entry_id, "192.168.1.100", 8080, sample_thing_description
    )
    
    # Mock connection error
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    mock_session_instance.request.side_effect = Exception("Connection failed")
    
    # Create service call
    service_call = ServiceCall("wot_http", f"{entry_id}_toggle", {})
    
    # Execute action and expect error
    service_handler = action_handler._create_action_handler(entry_id, "toggle")
    with pytest.raises(HomeAssistantError, match="Unexpected error executing action toggle"):
        await service_handler(service_call)


async def test_execute_action_unknown_device(hass, action_handler):
    """Test executing action for unknown device."""
    service_call = ServiceCall("wot_http", "unknown_device_action", {})
    
    service_handler = action_handler._create_action_handler("unknown_device", "action")
    with pytest.raises(HomeAssistantError, match="Device unknown_device not found"):
        await service_handler(service_call)


async def test_build_action_schema_simple(action_handler):
    """Test building schema for simple action."""
    action_data = {"description": "Simple action"}
    schema = action_handler._build_action_schema(action_data)
    
    # Should return empty schema
    assert isinstance(schema, vol.Schema)


async def test_build_action_schema_with_parameters(action_handler, sample_action_schema):
    """Test building schema with parameters."""
    action_data = sample_action_schema["setBrightness"]
    schema = action_handler._build_action_schema(action_data)
    
    # Test valid data
    valid_data = {"brightness": 50, "duration": 2000}
    result = schema(valid_data)
    assert result["brightness"] == 50
    assert result["duration"] == 2000
    
    # Test default value
    minimal_data = {"brightness": 75}
    result = schema(minimal_data)
    assert result["brightness"] == 75
    assert result["duration"] == 1000  # default value
    
    # Test validation errors
    with pytest.raises(vol.Invalid):
        schema({"brightness": 150})  # exceeds maximum
    
    with pytest.raises(vol.Invalid):
        schema({"brightness": -10})  # below minimum
    
    with pytest.raises(vol.Invalid):
        schema({})  # missing required field


async def test_build_action_schema_enum_constraint(action_handler):
    """Test building schema with enum constraint."""
    action_data = {
        "input": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["auto", "manual", "off"]
                }
            },
            "required": ["mode"]
        }
    }
    
    schema = action_handler._build_action_schema(action_data)
    
    # Test valid enum value
    result = schema({"mode": "auto"})
    assert result["mode"] == "auto"
    
    # Test invalid enum value
    with pytest.raises(vol.Invalid):
        schema({"mode": "invalid"})


async def test_build_action_schema_different_types(action_handler):
    """Test building schema with different parameter types."""
    action_data = {
        "input": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "count": {"type": "integer"},
                "rate": {"type": "number"},
                "enabled": {"type": "boolean"}
            }
        }
    }
    
    schema = action_handler._build_action_schema(action_data)
    
    # Test type conversions
    result = schema({
        "name": "test",
        "count": "42",  # string -> int
        "rate": "3.14",  # string -> float
        "enabled": True
    })
    
    assert result["name"] == "test"
    assert result["count"] == 42
    assert result["rate"] == 3.14
    assert result["enabled"] is True