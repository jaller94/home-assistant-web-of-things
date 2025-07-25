# WoT HTTP Component Tests

## Overview

Comprehensive test suite for the Web of Things HTTP Home Assistant component.

## Test Structure

- `conftest.py` - Shared fixtures and test utilities
- `test_config_flow.py` - Configuration flow tests
- `test_sensor.py` - Sensor platform tests  
- `test_actions.py` - WoT actions functionality tests
- `test_init.py` - Component initialization tests

## Test Coverage

### Config Flow Tests
- ✅ Successful device configuration
- ✅ Connection error handling
- ✅ HTTP error responses
- ✅ Thing Description discovery
- ✅ Fallback without Thing Description

### Sensor Platform Tests
- ✅ Data coordinator updates with Thing Description
- ✅ Fallback mode without Thing Description
- ✅ Connection error handling
- ✅ Sensor property mapping
- ✅ Device class detection
- ✅ Nested value structures
- ✅ Availability tracking

### Actions Tests
- ✅ Action registration from Thing Description
- ✅ Service creation and removal
- ✅ Parameter validation and schema building
- ✅ HTTP request execution
- ✅ Error handling (connection, HTTP errors)
- ✅ Different parameter types and constraints

### Initialization Tests
- ✅ Component setup and teardown
- ✅ Action handler lifecycle
- ✅ Multiple device entries
- ✅ Platform forwarding
- ✅ Data structure management

## Running Tests

```bash
# Install test requirements
pip install -r requirements.txt

# Run all tests
pytest

# Run specific test file
pytest test_config_flow.py

# Run with coverage
pytest --cov=custom_components.wot_http

# Run specific test
pytest test_actions.py::test_execute_action_with_parameters -v
```

## Test Fixtures

### Mock Data
- `sample_thing_description` - Complete WoT Thing Description
- `sample_config_entry_data` - Device configuration data
- `mock_aiohttp_session` - HTTP session mocking

### Test Scenarios
- Valid WoT devices with actions and properties
- Non-WoT HTTP devices (fallback mode) 
- Network errors and timeouts
- Malformed Thing Descriptions
- Various parameter types and validation

## Mocking Strategy

Tests use extensive mocking to:
- Simulate HTTP responses from WoT devices
- Test error conditions without real devices
- Verify correct API calls and parameters
- Isolate component logic from external dependencies