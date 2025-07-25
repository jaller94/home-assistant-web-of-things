"""Test the WoT HTTP config flow."""
import pytest
from unittest.mock import AsyncMock, patch
from aiohttp import ClientError

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_NAME

from custom_components.wot_http import config_flow
from custom_components.wot_http.const import DOMAIN


async def test_form_user_success(hass, mock_aiohttp_session, sample_thing_description):
    """Test we get the form and can create entry successfully."""
    # Mock successful HTTP responses
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    
    # Mock main endpoint response
    mock_main_response = AsyncMock()
    mock_main_response.status = 200
    
    # Mock Thing Description response
    mock_td_response = AsyncMock()
    mock_td_response.status = 200
    mock_td_response.json = AsyncMock(return_value=sample_thing_description)
    
    mock_session_instance.get.side_effect = [mock_main_response, mock_td_response]
    
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 8080,
            CONF_NAME: "Test Device",
        },
    )
    await hass.async_block_till_done()

    assert result2["type"] == "create_entry"
    assert result2["title"] == "Test Device"
    assert result2["data"] == {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 8080,
        CONF_NAME: "Test Device",
    }


async def test_form_user_cannot_connect(hass, mock_aiohttp_session):
    """Test we handle cannot connect error."""
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    
    # Mock connection error
    mock_session_instance.get.side_effect = ClientError("Connection failed")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 8080,
            CONF_NAME: "Test Device",
        },
    )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_user_http_error(hass, mock_aiohttp_session):
    """Test we handle HTTP error responses."""
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    
    # Mock HTTP error response
    mock_response = AsyncMock()
    mock_response.status = 404
    mock_session_instance.get.return_value = mock_response

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 8080,
            CONF_NAME: "Test Device",
        },
    )

    assert result2["type"] == "form"
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_form_user_no_thing_description(hass, mock_aiohttp_session):
    """Test successful setup without Thing Description."""
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    
    # Mock main endpoint success, TD endpoint failure
    mock_main_response = AsyncMock()
    mock_main_response.status = 200
    
    mock_td_response = AsyncMock()
    mock_td_response.status = 404
    
    mock_session_instance.get.side_effect = [mock_main_response, mock_td_response]

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: "192.168.1.100",
            CONF_PORT: 8080,
            CONF_NAME: "Test Device",
        },
    )

    # Should still succeed without Thing Description
    assert result2["type"] == "create_entry"
    assert result2["title"] == "Test Device"


async def test_validate_input_function(hass, mock_aiohttp_session, sample_thing_description):
    """Test the validate_input function directly."""
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    
    mock_main_response = AsyncMock()
    mock_main_response.status = 200
    
    mock_td_response = AsyncMock()
    mock_td_response.status = 200
    mock_td_response.json = AsyncMock(return_value=sample_thing_description)
    
    mock_session_instance.get.side_effect = [mock_main_response, mock_td_response]

    data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 8080,
        CONF_NAME: "Test Device",
    }

    result = await config_flow.validate_input(hass, data)
    
    assert result == {"title": "Test Device"}
    assert "thing_description" in data
    assert data["thing_description"] == sample_thing_description


async def test_validate_input_connection_error(hass, mock_aiohttp_session):
    """Test validate_input with connection error."""
    mock_session_instance = AsyncMock()
    mock_aiohttp_session.return_value.__aenter__.return_value = mock_session_instance
    
    mock_session_instance.get.side_effect = ClientError("Connection failed")

    data = {
        CONF_HOST: "192.168.1.100",
        CONF_PORT: 8080,
        CONF_NAME: "Test Device",
    }

    with pytest.raises(config_flow.CannotConnect):
        await config_flow.validate_input(hass, data)