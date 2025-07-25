#!/usr/bin/env python3
"""Debug script: Test WoTDataUpdateCoordinator with YouBikes server using optimized utilities."""

import asyncio
import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

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
        
        # Import our optimized utilities
        from http_utils import (
            create_http_session, is_thing_description, get_property_url, 
            parse_property_value, convert_text_to_number
        )
        
        class WoTDataUpdateCoordinator(MockDataUpdateCoordinator):
            """Test version using optimized utilities."""

            async def _async_update_data(self):
                """Update data via library."""
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(self.base_url)
                    
                    session = await create_http_session(self.hass, self.base_url)
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
                                                if is_thing_description(data):
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
                                prop_url = get_property_url(self.base_url, prop_name, prop_info)
                                
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
                constructed_url = get_property_url(coordinator.base_url, prop_name, prop_info)
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