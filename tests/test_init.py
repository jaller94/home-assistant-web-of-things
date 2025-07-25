"""Test the WoT HTTP component initialization."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME
from homeassistant.config_entries import ConfigEntry

from custom_components.wot_http import (
    async_setup,
    async_setup_entry,
    async_unload_entry,
    DOMAIN,
)


async def test_async_setup_no_config(hass):
    """Test async_setup with no configuration."""
    result = await async_setup(hass, {})
    assert result is True


async def test_async_setup_with_config(hass):
    """Test async_setup with configuration."""
    config = {
        DOMAIN: {
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 8080,
            CONF_NAME: "Test Device"
        }
    }
    
    with patch.object(hass.helpers.discovery, "async_load_platform") as mock_load_platform:
        result = await async_setup(hass, config)
        
        assert result is True
        assert DOMAIN in hass.data
        mock_load_platform.assert_called_once()


async def test_async_setup_entry_success(hass, sample_config_entry_data, sample_thing_description, mock_aiohttp_session):
    """Test successful config entry setup."""
    # Create mock config entry
    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.entry_id = "test_entry_123"
    config_entry.data = sample_config_entry_data
    
    # Mock successful Thing Description fetch
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=sample_thing_description)
    mock_session_instance.get.return_value.__aenter__.return_value = mock_response
    
    # Mock platform setup
    with patch.object(hass.config_entries, "async_forward_entry_setups") as mock_forward:
        mock_forward.return_value = True
        
        result = await async_setup_entry(hass, config_entry)
        
        assert result is True
        assert DOMAIN in hass.data
        assert config_entry.entry_id in hass.data[DOMAIN]
        assert "action_handler" in hass.data[DOMAIN]
        
        # Verify platform setup was called
        mock_forward.assert_called_once_with(config_entry, ["sensor"])


async def test_async_setup_entry_no_thing_description(hass, sample_config_entry_data, mock_aiohttp_session):
    """Test config entry setup without Thing Description."""
    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.entry_id = "test_entry_456"
    config_entry.data = sample_config_entry_data
    
    # Mock Thing Description fetch failure
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    mock_session_instance.get.side_effect = Exception("Connection failed")
    
    with patch.object(hass.config_entries, "async_forward_entry_setups") as mock_forward:
        mock_forward.return_value = True
        
        result = await async_setup_entry(hass, config_entry)
        
        # Should still succeed without Thing Description
        assert result is True
        assert config_entry.entry_id in hass.data[DOMAIN]


async def test_async_setup_entry_action_handler_reuse(hass, sample_config_entry_data, mock_aiohttp_session):
    """Test that action handler is reused across multiple entries."""
    # Setup first entry
    config_entry1 = MagicMock(spec=ConfigEntry)
    config_entry1.entry_id = "test_entry_1"
    config_entry1.data = sample_config_entry_data
    
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    mock_session_instance.get.side_effect = Exception("No TD")
    
    with patch.object(hass.config_entries, "async_forward_entry_setups"):
        await async_setup_entry(hass, config_entry1)
        
        action_handler1 = hass.data[DOMAIN]["action_handler"]
        
        # Setup second entry
        config_entry2 = MagicMock(spec=ConfigEntry)
        config_entry2.entry_id = "test_entry_2"
        config_entry2.data = sample_config_entry_data
        
        await async_setup_entry(hass, config_entry2)
        
        action_handler2 = hass.data[DOMAIN]["action_handler"]
        
        # Should be the same instance
        assert action_handler1 is action_handler2


async def test_async_unload_entry_success(hass, sample_config_entry_data):
    """Test successful config entry unload."""
    # Setup entry first
    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.entry_id = "test_entry_unload"
    config_entry.data = sample_config_entry_data
    
    # Add entry data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = config_entry.data
    
    # Mock action handler
    mock_action_handler = MagicMock()
    hass.data[DOMAIN]["action_handler"] = mock_action_handler
    
    with patch.object(hass.config_entries, "async_unload_platforms") as mock_unload:
        mock_unload.return_value = True
        
        result = await async_unload_entry(hass, config_entry)
        
        assert result is True
        assert config_entry.entry_id not in hass.data[DOMAIN]
        
        # Verify action handler cleanup was called
        mock_action_handler.unregister_device.assert_called_once_with(config_entry.entry_id)
        
        # Verify platform unload was called
        mock_unload.assert_called_once_with(config_entry, ["sensor"])


async def test_async_unload_entry_platform_failure(hass, sample_config_entry_data):
    """Test config entry unload when platform unload fails."""
    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.entry_id = "test_entry_fail"
    config_entry.data = sample_config_entry_data
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = config_entry.data
    
    with patch.object(hass.config_entries, "async_unload_platforms") as mock_unload:
        mock_unload.return_value = False  # Platform unload failed
        
        result = await async_unload_entry(hass, config_entry)
        
        assert result is False
        # Entry data should not be removed if platform unload failed
        assert config_entry.entry_id in hass.data[DOMAIN]


async def test_async_unload_entry_no_action_handler(hass, sample_config_entry_data):
    """Test config entry unload when no action handler exists."""
    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.entry_id = "test_entry_no_handler"
    config_entry.data = sample_config_entry_data
    
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = config_entry.data
    # Note: no action_handler in hass.data[DOMAIN]
    
    with patch.object(hass.config_entries, "async_unload_platforms") as mock_unload:
        mock_unload.return_value = True
        
        # Should not raise an exception
        result = await async_unload_entry(hass, config_entry)
        
        assert result is True
        assert config_entry.entry_id not in hass.data[DOMAIN]


async def test_domain_data_initialization(hass):
    """Test that domain data is properly initialized."""
    # Ensure clean state
    if DOMAIN in hass.data:
        del hass.data[DOMAIN]
    
    config_entry = MagicMock(spec=ConfigEntry)
    config_entry.entry_id = "test_init"
    config_entry.data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 8080,
        CONF_NAME: "Test Device"
    }
    
    with patch("aiohttp.ClientSession"), \
         patch.object(hass.config_entries, "async_forward_entry_setups"):
        
        await async_setup_entry(hass, config_entry)
        
        # Verify domain data structure
        assert DOMAIN in hass.data
        assert isinstance(hass.data[DOMAIN], dict)
        assert config_entry.entry_id in hass.data[DOMAIN]
        assert "action_handler" in hass.data[DOMAIN]


async def test_multiple_entries_same_domain(hass, mock_aiohttp_session):
    """Test handling multiple config entries for the same domain."""
    entries_data = [
        {"host": "192.168.1.100", "port": 8080, "name": "Device 1"},
        {"host": "192.168.1.101", "port": 8080, "name": "Device 2"},
    ]
    
    entries = []
    for i, data in enumerate(entries_data):
        config_entry = MagicMock(spec=ConfigEntry)
        config_entry.entry_id = f"test_entry_{i}"
        config_entry.data = data
        entries.append(config_entry)
    
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    mock_session_instance.get.side_effect = Exception("No TD")
    
    with patch.object(hass.config_entries, "async_forward_entry_setups"):
        # Setup both entries
        for entry in entries:
            result = await async_setup_entry(hass, entry)
            assert result is True
        
        # Verify both entries are tracked
        assert len([k for k in hass.data[DOMAIN].keys() if k != "action_handler"]) == 2
        assert "action_handler" in hass.data[DOMAIN]
        
        # Unload one entry
        with patch.object(hass.config_entries, "async_unload_platforms", return_value=True):
            result = await async_unload_entry(hass, entries[0])
            assert result is True
        
        # Verify only one entry remains
        assert len([k for k in hass.data[DOMAIN].keys() if k != "action_handler"]) == 1
        assert entries[1].entry_id in hass.data[DOMAIN]