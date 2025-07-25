"""Web of Things HTTP actions."""
import logging
from typing import Any, Dict

import aiohttp
import async_timeout

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .http_utils import create_http_session
from .const import (
    CONF_AUTH_TYPE, 
    CONF_USERNAME, 
    CONF_PASSWORD, 
    CONF_TOKEN,
    AUTH_NONE
)

_LOGGER = logging.getLogger(__name__)


class WoTActionHandler:
    """Handler for WoT actions."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the action handler."""
        self.hass = hass
        self._devices: Dict[str, Dict[str, Any]] = {}

    def register_device(
        self, 
        entry_id: str, 
        base_url: str, 
        thing_description: Dict[str, Any] | None,
        auth_type: str = AUTH_NONE,
        username: str = None,
        password: str = None,
        token: str = None
    ) -> None:
        """Register a device and its actions."""
        if not base_url.endswith('/'):
            base_url = base_url + '/'
        self._devices[entry_id] = {
            "base_url": base_url.rstrip('/'),
            "thing_description": thing_description,
            "auth_type": auth_type,
            "username": username,
            "password": password,
            "token": token,
        }

        if thing_description and "actions" in thing_description:
            for action_name, action_data in thing_description["actions"].items():
                service_name = f"{entry_id}_{action_name}"
                self.hass.services.async_register(
                    "wot_http",
                    service_name,
                    self._create_action_handler(entry_id, action_name),
                    schema=self._build_action_schema(action_data),
                )
                _LOGGER.debug("Registered action service: %s", service_name)

    def unregister_device(self, entry_id: str) -> None:
        """Unregister a device and its actions."""
        if entry_id not in self._devices:
            return

        thing_description = self._devices[entry_id].get("thing_description")
        if thing_description and "actions" in thing_description:
            for action_name in thing_description["actions"]:
                service_name = f"{entry_id}_{action_name}"
                if self.hass.services.has_service("wot_http", service_name):
                    self.hass.services.async_remove("wot_http", service_name)
                    _LOGGER.debug("Unregistered action service: %s", service_name)

        self._devices.pop(entry_id, None)

    def _create_action_handler(self, entry_id: str, action_name: str):
        """Create a service handler for a specific action."""
        async def action_handler(call: ServiceCall) -> None:
            """Handle the action service call."""
            device = self._devices.get(entry_id)
            if not device:
                raise HomeAssistantError(f"Device {entry_id} not found")

            thing_description = device.get("thing_description")
            if not thing_description or "actions" not in thing_description:
                raise HomeAssistantError(f"No actions available for device {entry_id}")

            action_data = thing_description["actions"].get(action_name)
            if not action_data:
                raise HomeAssistantError(f"Action {action_name} not found")

            await self._execute_action(device, action_name, action_data, call.data)

        return action_handler

    async def _execute_action(
        self,
        device: Dict[str, Any],
        action_name: str,
        action_data: Dict[str, Any],
        call_data: Dict[str, Any],
    ) -> None:
        """Execute a WoT action."""
        base_url = device["base_url"]
        
        # Determine action URL
        if "href" in action_data:
            action_url = f"{base_url}{action_data['href']}"
        else:
            action_url = f"{base_url}/actions/{action_name}"

        # Get HTTP method (default to POST)
        method = action_data.get("op", ["invokeaction"])[0] if "op" in action_data else "invokeaction"
        http_method = "POST"
        if method == "readproperty":
            http_method = "GET"
        elif method == "writeproperty":
            http_method = "PUT"

        # Prepare request data
        request_data = {}
        if "input" in action_data and call_data:
            # Filter call_data based on action input schema
            input_schema = action_data["input"]
            if "properties" in input_schema:
                for prop_name in input_schema["properties"]:
                    if prop_name in call_data:
                        request_data[prop_name] = call_data[prop_name]
            else:
                request_data = call_data

        try:
            async with create_http_session(
                self.hass, 
                base_url, 
                device.get("auth_type"),
                device.get("username"),
                device.get("password"),
                device.get("token")
            ) as session:
                async with async_timeout.timeout(30):
                    if http_method == "GET":
                        async with session.get(action_url) as response:
                            await self._handle_action_response(response, action_name)
                    else:
                        headers = {"Content-Type": "application/json"}
                        async with session.request(
                            http_method, action_url, json=request_data, headers=headers
                        ) as response:
                            await self._handle_action_response(response, action_name)

        except aiohttp.ClientError as err:
            _LOGGER.error("HTTP error executing action %s: %s", action_name, err)
            raise HomeAssistantError(f"Failed to execute action {action_name}: {err}")
        except Exception as err:
            _LOGGER.error("Unexpected error executing action %s: %s", action_name, err)
            raise HomeAssistantError(f"Unexpected error executing action {action_name}: {err}")

    async def _handle_action_response(self, response: aiohttp.ClientResponse, action_name: str) -> None:
        """Handle the action response."""
        if response.status >= 400:
            error_text = await response.text()
            _LOGGER.error("Action %s failed with status %s: %s", action_name, response.status, error_text)
            raise HomeAssistantError(f"Action {action_name} failed with status {response.status}")

        # Log successful action
        _LOGGER.info("Action %s executed successfully", action_name)

        # Try to parse response if it's JSON
        try:
            response_data = await response.json()
            _LOGGER.debug("Action %s response: %s", action_name, response_data)
        except Exception:
            # Non-JSON response is okay
            pass

    def _build_action_schema(self, action_data: Dict[str, Any]):
        """Build Home Assistant service schema from WoT action data."""
        import voluptuous as vol
        
        if "input" not in action_data:
            return vol.Schema({})

        input_schema = action_data["input"]
        if "properties" not in input_schema:
            return vol.Schema({})

        schema_dict = {}
        properties = input_schema["properties"]

        for prop_name, prop_data in properties.items():
            prop_type = prop_data.get("type", "string")
            required = prop_name in input_schema.get("required", [])

            # Convert WoT types to voluptuous validators
            if prop_type == "string":
                validator = str
            elif prop_type == "number":
                validator = vol.Coerce(float)
            elif prop_type == "integer":
                validator = vol.Coerce(int)
            elif prop_type == "boolean":
                validator = bool
            else:
                validator = str

            # Add constraints
            if "minimum" in prop_data and "maximum" in prop_data:
                validator = vol.All(validator, vol.Range(min=prop_data["minimum"], max=prop_data["maximum"]))
            elif "minimum" in prop_data:
                validator = vol.All(validator, vol.Range(min=prop_data["minimum"]))
            elif "maximum" in prop_data:
                validator = vol.All(validator, vol.Range(max=prop_data["maximum"]))

            if "enum" in prop_data:
                validator = vol.All(validator, vol.In(prop_data["enum"]))

            # Add to schema
            if required:
                schema_dict[vol.Required(prop_name)] = validator
            else:
                default = prop_data.get("default")
                if default is not None:
                    schema_dict[vol.Optional(prop_name, default=default)] = validator
                else:
                    schema_dict[vol.Optional(prop_name)] = validator

        return vol.Schema(schema_dict)