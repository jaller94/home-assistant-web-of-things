#!/usr/bin/env python3
"""Test href URL handling in WoT HTTP component."""

import unittest
from unittest.mock import MagicMock


class TestHrefUrlHandling(unittest.TestCase):
    """Test cases for href URL handling logic."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_url = "http://192.168.1.100:8080"
        self.https_base_url = "https://device.local:8443"

    def construct_property_url(self, base_url, prop_info, prop_name):
        """
        Replicate the URL construction logic from sensor.py.
        This method should match the logic in WoTDataUpdateCoordinator._async_update_data
        """
        if "href" in prop_info:
            href = prop_info['href']
            # Handle absolute URLs, relative paths, and relative URLs properly
            if href.lower().startswith(('http://', 'https://')):
                # Absolute URL - use as-is
                return href
            elif href.startswith('/'):
                # Relative path from root - append to base URL
                return f"{base_url}{href}"
            else:
                # Relative URL - append to base URL with separator
                return f"{base_url}/{href}"
        else:
            return f"{base_url}/properties/{prop_name}"

    def test_absolute_http_url(self):
        """Test absolute HTTP URL handling."""
        prop_info = {"href": "http://external-server.com:9000/api/temperature"}
        result = self.construct_property_url(self.base_url, prop_info, "temperature")
        
        # Should use the absolute URL as-is
        self.assertEqual(result, "http://external-server.com:9000/api/temperature")

    def test_absolute_https_url(self):
        """Test absolute HTTPS URL handling."""
        prop_info = {"href": "https://cloud-api.example.com/sensors/humidity"}
        result = self.construct_property_url(self.base_url, prop_info, "humidity")
        
        # Should use the absolute URL as-is
        self.assertEqual(result, "https://cloud-api.example.com/sensors/humidity")

    def test_relative_path_from_root(self):
        """Test relative path starting with slash."""
        prop_info = {"href": "/api/sensors/temperature"}
        result = self.construct_property_url(self.base_url, prop_info, "temperature")
        
        # Should append to base URL
        self.assertEqual(result, "http://192.168.1.100:8080/api/sensors/temperature")

    def test_relative_path_from_root_https(self):
        """Test relative path with HTTPS base URL."""
        prop_info = {"href": "/sensors/temp"}
        result = self.construct_property_url(self.https_base_url, prop_info, "temperature")
        
        # Should work with HTTPS base
        self.assertEqual(result, "https://device.local:8443/sensors/temp")

    def test_relative_url_without_slash(self):
        """Test relative URL without leading slash."""
        prop_info = {"href": "api/temperature"}
        result = self.construct_property_url(self.base_url, prop_info, "temperature")
        
        # Should add separator and append to base URL
        self.assertEqual(result, "http://192.168.1.100:8080/api/temperature")

    def test_relative_url_nested_path(self):
        """Test relative URL with nested path."""
        prop_info = {"href": "sensors/environmental/temperature"}
        result = self.construct_property_url(self.base_url, prop_info, "temperature")
        
        # Should handle nested paths correctly
        self.assertEqual(result, "http://192.168.1.100:8080/sensors/environmental/temperature")

    def test_no_href_default_endpoint(self):
        """Test default endpoint when no href is provided."""
        prop_info = {"type": "number", "unit": "celsius"}  # No href
        result = self.construct_property_url(self.base_url, prop_info, "temperature")
        
        # Should use default WoT property endpoint
        self.assertEqual(result, "http://192.168.1.100:8080/properties/temperature")

    def test_empty_href(self):
        """Test empty href string."""
        prop_info = {"href": ""}
        result = self.construct_property_url(self.base_url, prop_info, "temperature")
        
        # Empty href should be treated as relative URL
        self.assertEqual(result, "http://192.168.1.100:8080/")

    def test_href_with_query_parameters(self):
        """Test href with query parameters."""
        prop_info = {"href": "/api/sensor?type=temperature&unit=celsius"}
        result = self.construct_property_url(self.base_url, prop_info, "temperature")
        
        # Should preserve query parameters
        self.assertEqual(result, "http://192.168.1.100:8080/api/sensor?type=temperature&unit=celsius")

    def test_absolute_url_with_query_parameters(self):
        """Test absolute URL with query parameters."""
        prop_info = {"href": "https://api.example.com/sensor?id=123&format=json"}
        result = self.construct_property_url(self.base_url, prop_info, "temperature")
        
        # Should preserve absolute URL with query parameters
        self.assertEqual(result, "https://api.example.com/sensor?id=123&format=json")

    def test_href_with_fragment(self):
        """Test href with fragment identifier."""
        prop_info = {"href": "/api/sensors#temperature"}
        result = self.construct_property_url(self.base_url, prop_info, "temperature")
        
        # Should preserve fragment
        self.assertEqual(result, "http://192.168.1.100:8080/api/sensors#temperature")

    def test_base_url_with_trailing_slash(self):
        """Test base URL that ends with slash."""
        base_with_slash = "http://192.168.1.100:8080/"
        # Simulate the base_url processing from the coordinator
        base_url_processed = base_with_slash.rstrip('/')
        
        prop_info = {"href": "/api/temperature"}
        result = self.construct_property_url(base_url_processed, prop_info, "temperature")
        
        # Should handle trailing slash correctly
        self.assertEqual(result, "http://192.168.1.100:8080/api/temperature")

    def test_different_protocols_in_absolute_urls(self):
        """Test various protocols in absolute URLs."""
        test_cases = [
            ("http://example.com/temp", "http://example.com/temp"),
            ("https://secure.example.com/temp", "https://secure.example.com/temp"),
            ("HTTP://UPPERCASE.COM/temp", "HTTP://UPPERCASE.COM/temp"),  # Should preserve case
            ("HTTPS://MIXED-case.Example.Com/temp", "HTTPS://MIXED-case.Example.Com/temp"),
        ]
        
        for href_input, expected_output in test_cases:
            with self.subTest(href=href_input):
                prop_info = {"href": href_input}
                result = self.construct_property_url(self.base_url, prop_info, "temperature")
                self.assertEqual(result, expected_output)

    def test_edge_cases(self):
        """Test edge cases and unusual but valid URLs."""
        test_cases = [
            # IPv4 addresses
            ({"href": "http://10.0.0.1:8080/sensor"}, "http://10.0.0.1:8080/sensor"),
            # IPv6 addresses (simplified test)
            ({"href": "http://[::1]:8080/sensor"}, "http://[::1]:8080/sensor"),
            # Ports in relative paths (should not be treated as absolute)
            ({"href": "device:8080/sensor"}, "http://192.168.1.100:8080/device:8080/sensor"),
            # Just a port number (relative)
            ({"href": "8080/sensor"}, "http://192.168.1.100:8080/8080/sensor"),
        ]
        
        for prop_info, expected in test_cases:
            with self.subTest(href=prop_info.get("href")):
                result = self.construct_property_url(self.base_url, prop_info, "test")
                self.assertEqual(result, expected)

    def test_multiple_properties_same_device(self):
        """Test multiple properties with different href types on same device."""
        properties = {
            "local_temp": {"href": "/sensors/temperature"},
            "cloud_humidity": {"href": "https://cloud.example.com/humidity"},
            "relative_pressure": {"href": "sensors/pressure"},
            "default_light": {"type": "boolean"}  # No href
        }
        
        expected_urls = {
            "local_temp": "http://192.168.1.100:8080/sensors/temperature",
            "cloud_humidity": "https://cloud.example.com/humidity",
            "relative_pressure": "http://192.168.1.100:8080/sensors/pressure",
            "default_light": "http://192.168.1.100:8080/properties/default_light"
        }
        
        for prop_name, prop_info in properties.items():
            result = self.construct_property_url(self.base_url, prop_info, prop_name)
            self.assertEqual(result, expected_urls[prop_name], 
                           f"Failed for property {prop_name}")


def run_tests():
    """Run all URL handling tests."""
    print("=" * 60)
    print("Running WoT HTTP href URL Handling Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestHrefUrlHandling)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print(f"✅ All {result.testsRun} tests passed!")
    else:
        print(f"❌ {len(result.failures)} failures, {len(result.errors)} errors out of {result.testsRun} tests")
        
        if result.failures:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"- {test}: {traceback}")
                
        if result.errors:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"- {test}: {traceback}")
    
    print("=" * 60)
    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)