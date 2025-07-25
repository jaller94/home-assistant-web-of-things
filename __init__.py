"""Web of Things HTTP integration for Home Assistant."""
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .actions import WoTActionHandler
from .const import DOMAIN, CONF_BASE_URL

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_BASE_URL): cv.string,
                vol.Optional(CONF_NAME, default="WoT Device"): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Web of Things HTTP component."""
    if DOMAIN not in config:
        return True

    hass.data.setdefault(DOMAIN, {})
    
    for device_config in config[DOMAIN]:
        hass.async_create_task(
            hass.helpers.discovery.async_load_platform("sensor", DOMAIN, device_config)
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Web of Things HTTP from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    # Initialize action handler if not already present
    if "action_handler" not in hass.data[DOMAIN]:
        hass.data[DOMAIN]["action_handler"] = WoTActionHandler(hass)

    # Get Thing Description and register actions
    base_url = entry.data[CONF_BASE_URL]
    if not base_url.endswith('/'):
        base_url = base_url + '/'
    
    thing_description = None
    try:
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        
        # Create SSL context for HTTPS if needed
        ssl_context = None
        if parsed.scheme == 'https':
            import ssl
            import functools
            # Run SSL context creation in executor to avoid blocking the event loop
            ssl_context = await hass.async_add_executor_job(
                functools.partial(ssl.create_default_context)
            )
        
        connector = aiohttp.TCPConnector(ssl=ssl_context) if parsed.scheme == 'https' else None
        
        async with aiohttp.ClientSession(connector=connector) as session:
            td_url = f"{base_url.rstrip('/')}/.well-known/wot"
            async with session.get(td_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    thing_description = await response.json()
    except Exception:
        _LOGGER.debug("Could not fetch Thing Description for %s", base_url)

    # Register device actions
    action_handler = hass.data[DOMAIN]["action_handler"]
    action_handler.register_device(entry.entry_id, base_url, thing_description)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unregister device actions
    if "action_handler" in hass.data[DOMAIN]:
        action_handler = hass.data[DOMAIN]["action_handler"]
        action_handler.unregister_device(entry.entry_id)

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok