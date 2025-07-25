#!/usr/bin/env python3
"""Test the WoTDataUpdateCoordinator with the YouBikes server."""

import asyncio
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_youbikes_coordinator():
    """Test WoTDataUpdateCoordinator with YouBikes device."""
    print("Testing WoTDataUpdateCoordinator with YouBikes device...")
    print("=" * 60)
    
    try:
        # Mock Home Assistant instance
        class MockHass:
            async def async_add_executor_job(self, func):
                """Mock executor job."""
                return func()
        
        # Create a standalone version of WoTDataUpdateCoordinator for testing
        import aiohttp
        import async_timeout
        import logging
        from datetime import timedelta
        
        _LOGGER = logging.getLogger(__name__)
        
        class MockDataUpdateCoordinator:
            def __init__(self, hass, base_url):
                self.hass = hass
                self.base_url = base_url.rstrip('/')
                self.thing_description = None
                self.data = None
                self.last_update_success = True
        
        class WoTDataUpdateCoordinator(MockDataUpdateCoordinator):
            """Standalone version for testing."""
            
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

            async def _async_update_data(self):
                """Update data via library."""
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(self.base_url)
                    
                    # Create SSL context for HTTPS if needed
                    ssl_context = None
                    if parsed.scheme == 'https':
                        import ssl
                        import functools
                        # Run SSL context creation in executor to avoid blocking the event loop
                        ssl_context = await self.hass.async_add_executor_job(
                            functools.partial(ssl.create_default_context)
                        )
                    
                    connector = aiohttp.TCPConnector(ssl=ssl_context) if parsed.scheme == 'https' else None
                    
                    async with aiohttp.ClientSession(connector=connector) as session:
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
                                                    
                                                    # Handle different response formats
                                                    if isinstance(prop_data, dict) and "value" in prop_data:
                                                        # WoT standard format: {"value": actual_value}
                                                        value = prop_data["value"]
                                                    elif isinstance(prop_data, dict) and len(prop_data) == 1:
                                                        # Single key-value pair
                                                        value = list(prop_data.values())[0]
                                                    else:
                                                        # Direct value or complex object
                                                        value = prop_data
                                                    
                                                    data[prop_name] = value
                                                    _LOGGER.debug("Property '%s' processed value: %s", prop_name, value)
                                                    
                                                except ValueError as json_err:
                                                    # Try to get as text if JSON parsing fails
                                                    try:
                                                        text_data = await response.text()
                                                        _LOGGER.debug("Property '%s' text data: %s", prop_name, text_data)
                                                        # Try to parse as number if possible
                                                        try:
                                                            data[prop_name] = float(text_data) if '.' in text_data else int(text_data)
                                                        except ValueError:
                                                            data[prop_name] = text_data
                                                    except Exception:
                                                        _LOGGER.warning("Failed to parse property '%s' as JSON or text: %s", prop_name, json_err)
                                            else:
                                                _LOGGER.warning("HTTP %d error fetching property '%s' from %s", 
                                                              response.status, prop_name, prop_url)
                                
                                except Exception as err:
                                    _LOGGER.warning("Error fetching property '%s' from %s: %s", prop_name, prop_url, err)
                            
                            # Store the thing description for reference
                            data["_thing_description"] = self.thing_description
                        
                        _LOGGER.debug("Final data collected: %s", data)
                        self.data = data
                        return data

                except Exception as err:
                    _LOGGER.error("Error updating WoT sensor data: %s", err)
                    raise Exception(f"Error communicating with API: {err}")
        
        hass = MockHass()
        base_url = "https://wot.chrpaul.de/youbikes/501202057"
        
        coordinator = WoTDataUpdateCoordinator(hass, base_url)
        
        print(f"Created coordinator for: {base_url}")
        print(f"Base URL: {coordinator.base_url}")
        
        # Test data fetching
        print("\nFetching data...")
        data = await coordinator._async_update_data()
        
        print(f"\nData fetched successfully!")
        print(f"Number of properties: {len(data)}")
        
        for key, value in data.items():
            if not key.startswith('_'):  # Skip internal keys
                print(f"  {key}: {value}")
        
        # Check if Thing Description was found
        if coordinator.thing_description:
            print(f"\n✅ Thing Description found!")
            print(f"Title: {coordinator.thing_description.get('title', 'N/A')}")
            properties = coordinator.thing_description.get('properties', {})
            print(f"Properties in TD: {list(properties.keys())}")
            
            # Check for geo location information
            print(f"\n🌍 Geo Location Information:")
            td = coordinator.thing_description
            if "geo:lat" in td and "geo:long" in td:
                print(f"  geo:lat: {td['geo:lat']}")
                print(f"  geo:long: {td['geo:long']}")
                print(f"  📍 This device will appear on Home Assistant map!")
            elif "latitude" in td and "longitude" in td:
                print(f"  latitude: {td['latitude']}")
                print(f"  longitude: {td['longitude']}")
                print(f"  📍 This device will appear on Home Assistant map!")
            elif "lat" in td and "lng" in td:
                print(f"  lat: {td['lat']}")
                print(f"  lng: {td['lng']}")
                print(f"  📍 This device will appear on Home Assistant map!")
            else:
                print(f"  ❌ No geo location found")
            
            # Show property details for debugging
            print(f"\n📋 Property Details:")
            for prop_name, prop_info in properties.items():
                print(f"  {prop_name}:")
                if "forms" in prop_info:
                    print(f"    - WoT 1.1 forms: {len(prop_info['forms'])} forms")
                    for i, form in enumerate(prop_info['forms']):
                        if isinstance(form, dict):
                            print(f"      Form {i+1}: href={form.get('href', 'N/A')}, op={form.get('op', 'N/A')}")
                elif "href" in prop_info:
                    print(f"    - WoT 1.0 href: {prop_info['href']}")
                else:
                    print(f"    - No href or forms")
                    
                # Show the URL that would be constructed
                constructed_url = coordinator._get_property_url(prop_name, prop_info) 
                print(f"    - Constructed URL: {constructed_url}")
        else:
            print("❌ No Thing Description found")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_youbikes_coordinator())
    sys.exit(0 if success else 1)