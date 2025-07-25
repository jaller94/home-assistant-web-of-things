#!/usr/bin/env python3
"""Debug script to test WoT property fetching."""

import asyncio
import aiohttp
import json
import sys
from urllib.parse import urlparse

async def debug_wot_device(base_url):
    """Debug a WoT device's property endpoints."""
    print(f"🔍 Debugging WoT device at: {base_url}")
    print("=" * 60)
    
    # Ensure URL ends with /
    if not base_url.endswith('/'):
        base_url = base_url + '/'
    base_url = base_url.rstrip('/')
    
    parsed = urlparse(base_url)
    
    # Create SSL context for HTTPS if needed
    ssl_context = None
    if parsed.scheme == 'https':
        import ssl
        ssl_context = ssl.create_default_context()
    
    connector = aiohttp.TCPConnector(ssl=ssl_context) if parsed.scheme == 'https' else None
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # 1. Try to get Thing Description
        print("\n📋 Step 1: Fetching Thing Description...")
        td_url = f"{base_url}/.well-known/wot"
        print(f"Thing Description URL: {td_url}")
        
        thing_description = None
        try:
            async with session.get(td_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    thing_description = await response.json()
                    print("✅ Thing Description found!")
                    print(f"Title: {thing_description.get('title', 'N/A')}")
                    
                    if "properties" in thing_description:
                        props = thing_description["properties"]
                        print(f"Properties found: {list(props.keys())}")
                    else:
                        print("❌ No properties in Thing Description")
                else:
                    print(f"❌ HTTP {response.status}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        # 2. Test property endpoints
        if thing_description and "properties" in thing_description:
            print("\n🔧 Step 2: Testing Property Endpoints...")
            properties = thing_description["properties"]
            
            for prop_name, prop_info in properties.items():
                print(f"\n--- Testing property: {prop_name} ---")
                
                # Construct property URL
                if "href" in prop_info:
                    href = prop_info['href']
                    # Handle absolute URLs, relative paths, and relative URLs properly
                    if href.lower().startswith(('http://', 'https://')):
                        # Absolute URL - use as-is
                        prop_url = href
                        print(f"📍 Using absolute URL: {href}")
                    elif href.startswith('/'):
                        # Relative path from root - append to base URL
                        prop_url = f"{base_url}{href}"
                        print(f"📍 Using relative path: {href}")
                    else:
                        # Relative URL - append to base URL with separator
                        prop_url = f"{base_url}/{href}"
                        print(f"📍 Using relative URL: {href}")
                else:
                    prop_url = f"{base_url}/properties/{prop_name}"
                    print(f"📍 Using default endpoint (no href)")
                
                print(f"Property URL: {prop_url}")
                print(f"Expected type: {prop_info.get('type', 'unknown')}")
                
                try:
                    async with session.get(prop_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                        print(f"Status: {response.status}")
                        
                        if response.status == 200:
                            content_type = response.headers.get('content-type', 'unknown')
                            print(f"Content-Type: {content_type}")
                            
                            try:
                                prop_data = await response.json()
                                print(f"Raw JSON: {json.dumps(prop_data, indent=2)}")
                                
                                # Show how it would be processed
                                if isinstance(prop_data, dict) and "value" in prop_data:
                                    value = prop_data["value"]
                                    print(f"✅ Processed value (WoT format): {value}")
                                elif isinstance(prop_data, dict) and len(prop_data) == 1:
                                    value = list(prop_data.values())[0]
                                    print(f"✅ Processed value (single key): {value}")
                                else:
                                    value = prop_data
                                    print(f"✅ Processed value (direct): {value}")
                                    
                            except Exception as json_err:
                                print(f"❌ JSON parse error: {json_err}")
                                try:
                                    text_data = await response.text()
                                    print(f"Raw text: {text_data}")
                                except Exception:
                                    print("❌ Could not read as text either")
                        else:
                            print(f"❌ HTTP {response.status}")
                            
                except Exception as e:
                    print(f"❌ Request error: {e}")
        
        # 3. Test fallback endpoints
        print("\n🔄 Step 3: Testing Fallback Endpoints...")
        fallback_endpoints = ["/", "/properties", "/state"]
        
        for endpoint in fallback_endpoints:
            print(f"\n--- Testing fallback: {endpoint} ---")
            fallback_url = f"{base_url}{endpoint}"
            print(f"URL: {fallback_url}")
            
            try:
                async with session.get(fallback_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    print(f"Status: {response.status}")
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            print(f"JSON data: {json.dumps(data, indent=2)}")
                        except Exception:
                            text = await response.text()
                            print(f"Text data: {text[:200]}...")
                    else:
                        print(f"❌ HTTP {response.status}")
                        
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_properties.py <base_url>")
        print("Example: python debug_properties.py http://192.168.1.100:8080")
        sys.exit(1)
    
    base_url = sys.argv[1]
    asyncio.run(debug_wot_device(base_url))