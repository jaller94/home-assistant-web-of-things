#!/usr/bin/env python3
"""Examples of different href URL handling scenarios."""

def demonstrate_href_handling():
    """Demonstrate how different href values are processed."""
    
    base_url = "http://192.168.1.100:8080"
    
    # Test cases showing different href scenarios
    test_cases = [
        {
            "name": "Absolute HTTP URL",
            "href": "http://external-api.com:9000/temperature",
            "description": "Property hosted on external server"
        },
        {
            "name": "Absolute HTTPS URL", 
            "href": "https://cloud-service.example.com/sensors/humidity",
            "description": "Property from secure cloud service"
        },
        {
            "name": "Relative path from root",
            "href": "/api/sensors/temperature",
            "description": "Standard relative path on same device"
        },
        {
            "name": "Relative URL",
            "href": "sensors/pressure",
            "description": "Relative path without leading slash"
        },
        {
            "name": "Default (no href)",
            "href": None,
            "description": "Uses WoT standard /properties/{name} endpoint"
        },
        {
            "name": "Case-insensitive protocol",
            "href": "HTTPS://UPPERCASE-DOMAIN.COM/api",
            "description": "Uppercase protocol should work"
        },
        {
            "name": "With query parameters",
            "href": "/api/sensor?type=temp&unit=celsius",
            "description": "Preserves query parameters"
        }
    ]
    
    print("🔗 WoT HTTP href URL Handling Examples")
    print("=" * 60)
    print(f"Base URL: {base_url}")
    print("=" * 60)
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n{i}. {case['name']}")
        print(f"   Description: {case['description']}")
        
        if case['href']:
            print(f"   href: \"{case['href']}\"")
            
            # Apply the same logic as in sensor.py
            href = case['href']
            if href.lower().startswith(('http://', 'https://')):
                result_url = href
                url_type = "Absolute URL (used as-is)"
            elif href.startswith('/'):
                result_url = f"{base_url}{href}"
                url_type = "Relative path from root"
            else:
                result_url = f"{base_url}/{href}"
                url_type = "Relative URL"
        else:
            result_url = f"{base_url}/properties/example_property"
            url_type = "Default WoT endpoint"
            
        print(f"   Type: {url_type}")
        print(f"   Final URL: {result_url}")
        
        # Show what this enables
        if case['href'] and case['href'].lower().startswith(('http://', 'https://')):
            print(f"   ✨ Enables: Cross-domain property access")
        elif case['href'] and not case['href'].startswith('/'):
            print(f"   ✨ Enables: Flexible endpoint organization")
        else:
            print(f"   ✨ Enables: Standard WoT property access")

    print(f"\n{'=' * 60}")
    print("💡 Key Benefits:")
    print("   • Supports federated IoT architectures")
    print("   • Enables cloud-hybrid deployments") 
    print("   • Maintains WoT specification compliance")
    print("   • Handles various URL formats robustly")
    print(f"{'=' * 60}")

if __name__ == "__main__":
    demonstrate_href_handling()