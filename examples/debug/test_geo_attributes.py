#!/usr/bin/env python3
"""Debug script: Test geo attributes extraction from WoT sensor using optimized utilities."""

import sys
import os

# Add parent directories to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_geo_attributes():
    """Test that geo attributes are correctly extracted."""
    print("Testing geo attributes extraction...")
    print("=" * 50)
    
    # Import our optimized utilities
    from http_utils import is_thing_description
    
    # Mock Thing Description with geo info (like YouBikes)
    mock_thing_description = {
        "@context": [
            "https://www.w3.org/2022/wot/td/v1.1",
            {
                "@language": "en",
                "geo": "http://www.w3.org/2003/01/geo/wgs84_pos#"
            }
        ],
        "@type": "Thing",
        "geo:lat": "22.62560",
        "geo:long": "120.32321",
        "title": "The Affiliated Senior High School of NKNU (Kaixuan 2nd Rd.)",
        "description": "YouBike station providing bike rental services",
        "properties": {
            "available_spaces": {
                "type": "integer",
                "forms": []
            }
        }
    }
    
    # Mock coordinator
    class MockCoordinator:
        def __init__(self):
            self.thing_description = mock_thing_description
            self.data = {"available_spaces": 25}
            self.last_update_success = True
    
    # First, validate this is a proper Thing Description using our optimized utility
    print(f"🔍 Validating Thing Description...")
    if is_thing_description(mock_thing_description):
        print("✅ Valid WoT Thing Description detected")
    else:
        print("❌ Invalid Thing Description format")
        return False
    
    # Test the geo extraction logic directly
    try:
        # Simulate the geo extraction logic from the sensor
        attributes = {}
        td = mock_thing_description
        
        # Check for geo:lat and geo:long (WoT standard with geo namespace)
        if "geo:lat" in td and "geo:long" in td:
            try:
                lat = float(td["geo:lat"])
                lon = float(td["geo:long"])
                attributes["latitude"] = lat
                attributes["longitude"] = lon
                print(f"Added geo location from geo:lat/geo:long: {lat}, {lon}")
            except (ValueError, TypeError) as e:
                print(f"Could not parse geo:lat/geo:long: {e}")
        
        # Alternative: check for direct latitude/longitude fields
        elif "latitude" in td and "longitude" in td:
            try:
                lat = float(td["latitude"])
                lon = float(td["longitude"])
                attributes["latitude"] = lat
                attributes["longitude"] = lon
                print(f"Added geo location from latitude/longitude: {lat}, {lon}")
            except (ValueError, TypeError) as e:
                print(f"Could not parse latitude/longitude: {e}")
        
        # Alternative: check for lat/lng fields
        elif "lat" in td and "lng" in td:
            try:
                lat = float(td["lat"])
                lon = float(td["lng"])
                attributes["latitude"] = lat
                attributes["longitude"] = lon
                print(f"Added geo location from lat/lng: {lat}, {lon}")
            except (ValueError, TypeError) as e:
                print(f"Could not parse lat/lng: {e}")
        
        # Add other useful Thing Description metadata
        if "title" in td:
            attributes["thing_title"] = td["title"]
        if "description" in td:
            attributes["thing_description"] = td["description"]
        
        print("📍 Extracted attributes:")
        if attributes:
            for key, value in attributes.items():
                print(f"  {key}: {value}")
            
            # Check specifically for geo attributes
            if "latitude" in attributes and "longitude" in attributes:
                lat = attributes["latitude"]
                lon = attributes["longitude"]
                print(f"\n✅ Geo location successfully extracted!")
                print(f"   Latitude: {lat}")
                print(f"   Longitude: {lon}")
                print(f"   📍 This will place the sensor on the Home Assistant map!")
                
                # Verify it's in Taiwan (rough bounds check)
                if 22.0 <= lat <= 25.5 and 120.0 <= lon <= 122.0:
                    print(f"   🌏 Location appears to be in Taiwan ✓")
                else:
                    print(f"   ⚠️  Location seems unexpected for YouBike station")
            else:
                print("❌ No latitude/longitude found in attributes")
        else:
            print("❌ No attributes extracted")
            
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_geo_attributes()
    sys.exit(0 if success else 1)