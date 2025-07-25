"""Web of Things HTTP sensor platform."""
import logging
from datetime import timedelta
from typing import Any

import async_timeout

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    DOMAIN, 
    CONF_BASE_URL, 
    CONF_AUTH_TYPE, 
    CONF_USERNAME, 
    CONF_PASSWORD, 
    CONF_TOKEN,
    AUTH_NONE
)
from .http_utils import create_http_session, is_thing_description, get_property_url, parse_property_value, convert_text_to_number

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up WoT HTTP sensor based on a config entry."""
    base_url = config_entry.data[CONF_BASE_URL]
    name = config_entry.data[CONF_NAME]
    
    # Extract authentication parameters
    auth_type = config_entry.data.get(CONF_AUTH_TYPE, AUTH_NONE)
    username = config_entry.data.get(CONF_USERNAME)
    password = config_entry.data.get(CONF_PASSWORD)
    token = config_entry.data.get(CONF_TOKEN)

    coordinator = WoTDataUpdateCoordinator(hass, base_url, auth_type, username, password, token)
    await coordinator.async_config_entry_first_refresh()

    sensors = []
    
    # Create sensors based on Thing Description or fallback to basic sensor
    if coordinator.thing_description and "properties" in coordinator.thing_description:
        # Use Thing Description to create sensors
        properties = coordinator.thing_description["properties"]
        for prop_name, prop_data in properties.items():
            # Use property title if available, otherwise use property name
            prop_title = prop_data.get("title", prop_name)
            sensors.append(
                WoTSensor(
                    coordinator,
                    prop_title,
                    prop_name,
                    prop_data.get("type", "string"),
                    prop_data.get("unit"),
                )
            )
    elif coordinator.data and "properties" in coordinator.data:
        # Fallback: use properties found in data
        for prop_name, prop_data in coordinator.data["properties"].items():
            # Use property title if available, otherwise use property name
            prop_title = prop_data.get("title", prop_name)
            sensors.append(
                WoTSensor(
                    coordinator,
                    prop_title,
                    prop_name,
                    prop_data.get("type", "string"),
                    prop_data.get("unit"),
                )
            )
    else:
        # Final fallback: create a basic sensor
        sensors.append(
            WoTSensor(coordinator, name, "state", "string", None)
        )

    async_add_entities(sensors, update_before_add=True)


class WoTDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching WoT data from the API."""

    def __init__(
        self, 
        hass: HomeAssistant, 
        base_url: str,
        auth_type: str = AUTH_NONE,
        username: str = None,
        password: str = None,
        token: str = None
    ) -> None:
        """Initialize."""
        if not base_url.endswith('/'):
            base_url = base_url + '/'
        self.base_url = base_url.rstrip('/')
        self.auth_type = auth_type
        self.username = username
        self.password = password
        self.token = token
        self.thing_description = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )

    def _is_thing_description(self, data: dict) -> bool:
        """Check if JSON data looks like a WoT Thing Description."""
        if not isinstance(data, dict):
            return False
        
        # Check for WoT TD indicators
        has_context = "@context" in data
        has_properties = "properties" in data and isinstance(data["properties"], dict)
        has_title = "title" in data
        has_type_thing = data.get("@type") == "Thing" or "Thing" in str(data.get("@type", ""))
        
        # Must have either @context or properties to be considered a TD
        return (has_context or has_properties) and (has_title or has_type_thing or has_properties)

    def _get_property_url(self, prop_name: str, prop_info: dict) -> str:
        """Get the property URL from WoT 1.0 or 1.1 format."""
        
        # WoT 1.0 format - simple href
        if "href" in prop_info:
            href = prop_info['href']
            return self._resolve_url(href)
        
        # WoT 1.1 format - forms array
        if "forms" in prop_info and isinstance(prop_info["forms"], list):
            for form in prop_info["forms"]:
                if isinstance(form, dict) and "href" in form:
                    # Look for HTTP-based forms (not WebSocket)
                    href = form["href"]
                    if not href.lower().startswith(('ws://', 'wss://')):
                        # Check if this form supports readproperty operation
                        ops = form.get("op", [])
                        if "readproperty" in ops or not ops:  # If no ops specified, assume it supports read
                            return self._resolve_url(href)
        
        # Fallback to default WoT endpoint
        return f"{self.base_url}/properties/{prop_name}"

    def _resolve_url(self, href: str) -> str:
        """Resolve href to absolute URL."""
        # Handle absolute URLs, relative paths, and relative URLs properly
        if href.lower().startswith(('http://', 'https://')):
            # Absolute URL - use as-is
            return href
        elif href.startswith('/'):
            # Relative path from root - append to base URL
            return f"{self.base_url}{href}"
        else:
            # Relative URL - append to base URL with separator
            return f"{self.base_url}/{href}"

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via library."""
        try:
            session = await create_http_session(
                self.hass, 
                self.base_url, 
                self.auth_type, 
                self.username, 
                self.password, 
                self.token
            )
            async with session:
                # First, try to get Thing Description if we don't have it
                if self.thing_description is None:
                    # Try standard WoT Thing Description endpoints
                    td_endpoints = [
                        f"{self.base_url}/.well-known/wot",  # WoT standard
                        f"{self.base_url}/",  # Root endpoint (some devices serve TD here)
                    ]
                    
                    for td_url in td_endpoints:
                        try:
                            async with async_timeout.timeout(10):
                                async with session.get(td_url) as response:
                                    if response.status == 200:
                                        data = await response.json()
                                        # Check if this looks like a Thing Description
                                        if self._is_thing_description(data):
                                            self.thing_description = data
                                            _LOGGER.debug("Found Thing Description at %s", td_url)
                                            break
                        except Exception as e:
                            _LOGGER.debug("Could not fetch Thing Description from %s: %s", td_url, e)

                # Fetch property values
                data = {}
                
                if self.thing_description and "properties" in self.thing_description:
                    # Use Thing Description to fetch properties
                    properties = self.thing_description["properties"]
                    _LOGGER.debug("Fetching %d properties from Thing Description", len(properties))
                    
                    for prop_name, prop_info in properties.items():
                        # Construct property URL - handle both WoT 1.0 and 1.1 formats
                        prop_url = self._get_property_url(prop_name, prop_info)
                        
                        _LOGGER.debug("Fetching property '%s' from URL: %s", prop_name, prop_url)
                        
                        try:
                            async with async_timeout.timeout(10):
                                async with session.get(prop_url) as response:
                                    _LOGGER.debug("Property '%s' response status: %d", prop_name, response.status)
                                    
                                    if response.status == 200:
                                        try:
                                            prop_data = await response.json()
                                            _LOGGER.debug("Property '%s' raw data: %s", prop_name, prop_data)
                                            
                                            value = parse_property_value(prop_data)
                                            data[prop_name] = value
                                            _LOGGER.debug("Property '%s' processed value: %s", prop_name, value)
                                            
                                        except ValueError as json_err:
                                            # Try to get as text if JSON parsing fails
                                            try:
                                                text_data = await response.text()
                                                _LOGGER.debug("Property '%s' text data: %s", prop_name, text_data)
                                                data[prop_name] = convert_text_to_number(text_data)
                                            except Exception:
                                                _LOGGER.warning("Failed to parse property '%s' as JSON or text: %s", prop_name, json_err)
                                    else:
                                        _LOGGER.warning("HTTP %d error fetching property '%s' from %s", 
                                                      response.status, prop_name, prop_url)
                        
                        except Exception as err:
                            _LOGGER.warning("Error fetching property '%s' from %s: %s", prop_name, prop_url, err)
                    
                    # Store the thing description for reference
                    data["_thing_description"] = self.thing_description
                else:
                    # Fallback: try common endpoints when no Thing Description is available
                    _LOGGER.debug("No Thing Description available, trying fallback endpoints")
                    endpoints = ["/properties", "/", "/state"]
                    
                    for endpoint in endpoints:
                        try:
                            fallback_url = f"{self.base_url}{endpoint}"
                            _LOGGER.debug("Trying fallback endpoint: %s", fallback_url)
                            
                            async with async_timeout.timeout(10):
                                async with session.get(fallback_url) as response:
                                    _LOGGER.debug("Fallback endpoint '%s' response status: %d", endpoint, response.status)
                                    
                                    if response.status == 200:
                                        try:
                                            endpoint_data = await response.json()
                                            _LOGGER.debug("Fallback endpoint '%s' data: %s", endpoint, endpoint_data)
                                            
                                            # If this looks like a Thing Description, try to use it
                                            if endpoint == "/" and is_thing_description(endpoint_data):
                                                _LOGGER.debug("Found Thing Description at root endpoint")
                                                self.thing_description = endpoint_data
                                                # Restart the process with the Thing Description
                                                return await self._async_update_data()
                                            else:
                                                # Use as direct property data
                                                data.update(endpoint_data)
                                                break
                                        except ValueError:
                                            _LOGGER.debug("Fallback endpoint '%s' returned non-JSON data", endpoint)
                        except Exception as err:
                            _LOGGER.debug("Fallback endpoint '%s' failed: %s", endpoint, err)
                            continue

                _LOGGER.debug("Final data collected: %s", data)
                return data

        except Exception as err:
            _LOGGER.error("Error updating WoT sensor data: %s", err)
            raise UpdateFailed(f"Error communicating with API: {err}")


class WoTSensor(CoordinatorEntity, SensorEntity):
    """Representation of a WoT HTTP Sensor."""

    def __init__(
        self,
        coordinator: WoTDataUpdateCoordinator,
        name: str,
        property_key: str,
        data_type: str,
        unit: str | None,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._name = name
        self._property_key = property_key
        self._data_type = data_type
        self._unit = unit
        # Create unique ID from base URL and property key
        import hashlib
        url_hash = hashlib.md5(coordinator.base_url.encode()).hexdigest()[:8]
        self._attr_unique_id = f"wot_http_{url_hash}_{property_key}"
        
        # Create device info to group all sensors from the same WoT device
        device_name = f"WoT Device ({coordinator.base_url})"
        if coordinator.thing_description and "title" in coordinator.thing_description:
            device_name = coordinator.thing_description["title"]
            
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, url_hash)},
            name=device_name,
            manufacturer="Web of Things",
            model="WoT HTTP Device",
            configuration_url=coordinator.base_url,
        )

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self._name

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        
        value = self.coordinator.data.get(self._property_key)
        
        # Handle nested data structures
        if isinstance(value, dict) and "value" in value:
            value = value["value"]
        
        # Convert to appropriate numeric type for better Home Assistant integration
        if self._data_type in ("number", "integer") and value is not None:
            try:
                if self._data_type == "integer":
                    return int(float(value))  # Convert via float first to handle "25.0" -> 25
                elif self._data_type == "number":
                    return float(value)
            except (ValueError, TypeError):
                # If conversion fails, return as-is
                pass
        
        return value

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement."""
        return self._unit

    @property
    def device_class(self) -> str | None:
        """Return device class based on WoT metadata only - never assume from names."""
        if self._data_type not in ("number", "integer") or not self._unit:
            return None
            
        # Only use explicit unit information from Thing Description
        unit_lower = self._unit.lower()
        unit_mapping = {
            "temperature": ("°c", "°f", "celsius", "fahrenheit", "k", "kelvin"),
            "humidity": ("%", "percent", "rh"),
            "pressure": ("pa", "hpa", "kpa", "mbar", "bar", "mmhg", "inhg", "psi"),
            "power": ("w", "watt", "kw", "kilowatt", "kwh", "wh"),
        }
        
        for device_class, units in unit_mapping.items():
            if unit_lower in units:
                return device_class
                
        return None

    @property
    def state_class(self) -> SensorStateClass | None:
        """Return state class for numeric sensors to enable statistics."""
        if self._data_type in ("number", "integer"):
            # All numeric properties get measurement state class for statistics and graphs
            return SensorStateClass.MEASUREMENT
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes including geo location."""
        attributes = {}
        
        # Add geo location from Thing Description if available
        if self.coordinator.thing_description:
            td = self.coordinator.thing_description
            
            # Check for geo:lat and geo:long (WoT standard with geo namespace)
            if "geo:lat" in td and "geo:long" in td:
                try:
                    lat = float(td["geo:lat"])
                    lon = float(td["geo:long"])
                    attributes["latitude"] = lat
                    attributes["longitude"] = lon
                    _LOGGER.debug("Added geo location from geo:lat/geo:long: %s, %s", lat, lon)
                except (ValueError, TypeError) as e:
                    _LOGGER.debug("Could not parse geo:lat/geo:long: %s", e)
            
            # Alternative: check for direct latitude/longitude fields
            elif "latitude" in td and "longitude" in td:
                try:
                    lat = float(td["latitude"])
                    lon = float(td["longitude"])
                    attributes["latitude"] = lat
                    attributes["longitude"] = lon
                    _LOGGER.debug("Added geo location from latitude/longitude: %s, %s", lat, lon)
                except (ValueError, TypeError) as e:
                    _LOGGER.debug("Could not parse latitude/longitude: %s", e)
            
            # Alternative: check for lat/lng fields
            elif "lat" in td and "lng" in td:
                try:
                    lat = float(td["lat"])
                    lon = float(td["lng"])
                    attributes["latitude"] = lat
                    attributes["longitude"] = lon
                    _LOGGER.debug("Added geo location from lat/lng: %s, %s", lat, lon)
                except (ValueError, TypeError) as e:
                    _LOGGER.debug("Could not parse lat/lng: %s", e)
            
            # Add other useful Thing Description metadata
            if "title" in td and td["title"] != self._name:
                attributes["thing_title"] = td["title"]
            if "description" in td:
                attributes["thing_description"] = td["description"]
        
        return attributes if attributes else None