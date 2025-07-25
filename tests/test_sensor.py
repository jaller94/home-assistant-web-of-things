"""Test the WoT HTTP sensor platform."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import timedelta

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.setup import async_setup_component

from custom_components.wot_http.sensor import (
    WoTDataUpdateCoordinator,
    WoTSensor,
    async_setup_entry,
)
from custom_components.wot_http.const import DOMAIN


async def test_coordinator_update_with_thing_description(hass, mock_aiohttp_session, sample_thing_description):
    """Test coordinator data update with Thing Description."""
    coordinator = WoTDataUpdateCoordinator(hass, "192.168.1.100", 8080)
    coordinator.thing_description = sample_thing_description

    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance

    # Mock property responses
    temp_response = AsyncMock()
    temp_response.status = 200
    temp_response.json = AsyncMock(return_value={"value": 22.5})

    brightness_response = AsyncMock()
    brightness_response.status = 200
    brightness_response.json = AsyncMock(return_value={"value": 75})

    mock_session_instance.get.side_effect = [temp_response, brightness_response]

    result = await coordinator._async_update_data()

    assert result["temperature"] == 22.5
    assert result["brightness"] == 75
    assert result["_thing_description"] == sample_thing_description


async def test_coordinator_update_fallback_mode(hass, mock_aiohttp_session):
    """Test coordinator fallback mode without Thing Description."""
    coordinator = WoTDataUpdateCoordinator(hass, "192.168.1.100", 8080)

    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance

    # Mock TD request failure and fallback endpoints
    td_response = AsyncMock()
    td_response.status = 404

    fallback_response = AsyncMock()
    fallback_response.status = 200
    fallback_response.json = AsyncMock(return_value={"temperature": 23.0, "humidity": 60})

    mock_session_instance.get.side_effect = [td_response, fallback_response]

    result = await coordinator._async_update_data()

    assert result["temperature"] == 23.0
    assert result["humidity"] == 60


async def test_coordinator_update_connection_error(hass, mock_aiohttp_session):
    """Test coordinator handling connection errors."""
    coordinator = WoTDataUpdateCoordinator(hass, "192.168.1.100", 8080)

    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    mock_session_instance.get.side_effect = Exception("Connection failed")

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_wot_sensor_properties(hass, sample_thing_description):
    """Test WoT sensor properties."""
    coordinator = WoTDataUpdateCoordinator(hass, "192.168.1.100", 8080)
    coordinator.data = {"temperature": 22.5, "brightness": 75}

    sensor = WoTSensor(
        coordinator=coordinator,
        name="Test Temperature",
        property_key="temperature",
        data_type="number",
        unit="°C"
    )

    assert sensor.name == "Test Temperature"
    assert sensor.native_value == 22.5
    assert sensor.native_unit_of_measurement == "°C"
    assert sensor.device_class == "temperature"
    assert sensor.available is True


async def test_wot_sensor_nested_value(hass):
    """Test sensor handling nested value structures."""
    coordinator = WoTDataUpdateCoordinator(hass, "192.168.1.100", 8080)
    coordinator.data = {"temperature": {"value": 22.5, "timestamp": "2023-01-01T00:00:00Z"}}

    sensor = WoTSensor(
        coordinator=coordinator,
        name="Test Temperature",
        property_key="temperature",
        data_type="number",
        unit="°C"
    )

    assert sensor.native_value == 22.5


async def test_wot_sensor_unavailable(hass):
    """Test sensor when coordinator is unavailable."""
    coordinator = WoTDataUpdateCoordinator(hass, "192.168.1.100", 8080)
    coordinator.last_update_success = False

    sensor = WoTSensor(
        coordinator=coordinator,
        name="Test Temperature",
        property_key="temperature",
        data_type="number",
        unit="°C"
    )

    assert sensor.available is False


async def test_wot_sensor_device_class_detection(hass):
    """Test automatic device class detection."""
    coordinator = WoTDataUpdateCoordinator(hass, "192.168.1.100", 8080)
    coordinator.data = {"humidity": 60, "pressure": 1013.25}

    humidity_sensor = WoTSensor(
        coordinator=coordinator,
        name="Test Humidity",
        property_key="humidity",
        data_type="number",
        unit="%"
    )

    pressure_sensor = WoTSensor(
        coordinator=coordinator,
        name="Test Pressure",
        property_key="pressure",
        data_type="number",
        unit="hPa"
    )

    assert humidity_sensor.device_class == "humidity"
    assert pressure_sensor.device_class == "pressure"


async def test_async_setup_entry_with_thing_description(hass, sample_config_entry_data, sample_thing_description):
    """Test sensor platform setup with Thing Description."""
    # Create mock config entry
    config_entry = MagicMock()
    config_entry.data = sample_config_entry_data

    # Mock coordinator
    with patch("custom_components.wot_http.sensor.WoTDataUpdateCoordinator") as mock_coordinator_class:
        mock_coordinator = AsyncMock()
        mock_coordinator.data = sample_thing_description
        mock_coordinator_class.return_value = mock_coordinator

        # Mock entity addition
        mock_add_entities = AsyncMock()

        await async_setup_entry(hass, config_entry, mock_add_entities)

        # Verify coordinator was created and refreshed
        mock_coordinator_class.assert_called_once_with(hass, "192.168.1.100", 8080)
        mock_coordinator.async_config_entry_first_refresh.assert_called_once()

        # Verify entities were added (2 properties in sample TD)
        mock_add_entities.assert_called_once()
        added_sensors = mock_add_entities.call_args[0][0]
        assert len(added_sensors) == 2


async def test_async_setup_entry_fallback_sensor(hass, sample_config_entry_data):
    """Test sensor platform setup without Thing Description (fallback)."""
    config_entry = MagicMock()
    config_entry.data = sample_config_entry_data

    with patch("custom_components.wot_http.sensor.WoTDataUpdateCoordinator") as mock_coordinator_class:
        mock_coordinator = AsyncMock()
        mock_coordinator.data = {}  # No Thing Description
        mock_coordinator_class.return_value = mock_coordinator

        mock_add_entities = AsyncMock()

        await async_setup_entry(hass, config_entry, mock_add_entities)

        # Verify fallback sensor was created
        mock_add_entities.assert_called_once()
        added_sensors = mock_add_entities.call_args[0][0]
        assert len(added_sensors) == 1  # Single fallback sensor


async def test_coordinator_thing_description_caching(hass, mock_aiohttp_session, sample_thing_description):
    """Test that Thing Description is cached after first fetch."""
    coordinator = WoTDataUpdateCoordinator(hass, "192.168.1.100", 8080)

    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance

    # First call - fetch TD
    td_response = AsyncMock()
    td_response.status = 200
    td_response.json = AsyncMock(return_value=sample_thing_description)

    property_response = AsyncMock()
    property_response.status = 200
    property_response.json = AsyncMock(return_value={"value": 22.5})

    mock_session_instance.get.side_effect = [td_response, property_response, property_response]

    await coordinator._async_update_data()
    assert coordinator.thing_description == sample_thing_description

    # Second call - should not fetch TD again
    mock_session_instance.get.side_effect = [property_response, property_response]
    await coordinator._async_update_data()

    # TD should still be cached
    assert coordinator.thing_description == sample_thing_description