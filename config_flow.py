"""Config flow for Web of Things HTTP integration."""
import logging
from typing import Any
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_BASE_URL
from .http_utils import create_http_session

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): str,
        vol.Optional(CONF_NAME, default="WoT Device"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    base_url = data[CONF_BASE_URL].strip()
    
    # Basic URL validation
    if not base_url:
        raise InvalidInput("Base URL cannot be empty")
    
    # Add protocol if missing
    if not base_url.startswith(('http://', 'https://')):
        base_url = f"http://{base_url}"
        data[CONF_BASE_URL] = base_url
    
    # Parse and validate URL
    try:
        parsed = urlparse(base_url)
        if not parsed.scheme in ('http', 'https'):
            raise InvalidInput("URL must use HTTP or HTTPS protocol")
        if not parsed.netloc:
            raise InvalidInput("Invalid URL format")
    except Exception:
        raise InvalidInput("Invalid URL format")
    
    # Ensure URL ends with /
    if not base_url.endswith('/'):
        base_url = base_url + '/'
        data[CONF_BASE_URL] = base_url
    
    try:
        async with create_http_session(hass, base_url) as session:
            # Try root endpoint first
            try:
                async with session.get(base_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 404:
                        # Try WoT Thing Description endpoint directly
                        td_url = f"{base_url.rstrip('/')}/.well-known/wot"
                        async with session.get(td_url, timeout=aiohttp.ClientTimeout(total=5)) as td_response:
                            if td_response.status != 200:
                                raise CannotConnect("No WoT Thing Description found")
                    elif response.status >= 400:
                        raise CannotConnect(f"HTTP {response.status} error")
            except aiohttp.ClientConnectorError as e:
                if "certificate verify failed" in str(e):
                    raise CannotConnect("SSL certificate verification failed. Check HTTPS configuration.")
                raise CannotConnect(f"Cannot connect to device: {str(e)}")
            except aiohttp.ServerTimeoutError:
                raise CannotConnect("Connection timeout - device may be slow to respond")
                
            # Try to get WoT Thing Description
            td_url = f"{base_url.rstrip('/')}/.well-known/wot"
            thing_description = None
            try:
                async with session.get(td_url, timeout=aiohttp.ClientTimeout(total=5)) as td_response:
                    if td_response.status == 200:
                        try:
                            thing_description = await td_response.json()
                            data["thing_description"] = thing_description
                            
                            # Validate basic WoT TD structure
                            if not isinstance(thing_description, dict):
                                raise InvalidInput("Invalid Thing Description format")
                            
                            # Log discovered capabilities
                            properties_count = len(thing_description.get("properties", {}))
                            actions_count = len(thing_description.get("actions", {}))
                            
                            _LOGGER.info(
                                "Discovered WoT device '%s' with %d properties and %d actions", 
                                thing_description.get("title", data[CONF_NAME]),
                                properties_count,
                                actions_count
                            )
                            
                            # Use device title from TD if available
                            if "title" in thing_description and not data.get("name_from_user"):
                                data[CONF_NAME] = thing_description["title"]
                                
                        except (ValueError, TypeError) as e:
                            _LOGGER.warning("Invalid JSON in Thing Description: %s", e)
                            raise InvalidInput("Device returned invalid JSON Thing Description")
            except aiohttp.ClientError:
                # Thing Description is optional, continue without it
                _LOGGER.info("No WoT Thing Description found at %s, using basic HTTP mode", td_url)
                    
    except CannotConnect:
        raise
    except InvalidInput:
        raise
    except Exception as e:
        _LOGGER.exception("Unexpected error during validation: %s", e)
        raise CannotConnect("Unexpected error occurred")

    return {"title": data[CONF_NAME]}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Web of Things HTTP."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # Check if already configured
            unique_id = user_input[CONF_BASE_URL].rstrip('/')
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()
            
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect as e:
                errors["base"] = "cannot_connect"
                _LOGGER.warning("Cannot connect to WoT device: %s", str(e))
            except InvalidInput as e:
                errors["base"] = "invalid_input"
                _LOGGER.warning("Invalid input: %s", str(e))
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class InvalidInput(HomeAssistantError):
    """Error to indicate invalid user input."""


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for WoT HTTP component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_NAME,
                    default=self.config_entry.options.get(
                        CONF_NAME, self.config_entry.data.get(CONF_NAME, "WoT Device")
                    ),
                ): str,
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)