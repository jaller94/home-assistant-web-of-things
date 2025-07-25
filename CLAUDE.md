# WoT HTTP Component - Development Guide

## Project Overview

This is a Home Assistant custom component that implements support for **Web of Things (WoT) 1.0 and 1.1** specifications. It enables Home Assistant to interact with IoT devices that expose their capabilities through WoT Thing Descriptions.

## Architecture

### Core Components
- **`__init__.py`**: Main component initialization and coordinator setup
- **`sensor.py`**: Sensor platform for WoT properties with automatic visualization
- **`actions.py`**: Action handling for WoT actions (invoke operations)
- **`config_flow.py`**: Configuration UI flow for adding WoT things
- **`const.py`**: Constants and configuration schemas

### Key Features
- **WoT 1.0/1.1 Compliance**: Full support for Thing Description parsing
- **Property Monitoring**: Auto-discovery and polling of WoT properties
- **Smart Visualization**: Graph types based on property semantics in Thing Description
- **Action Support**: Invoke WoT actions with parameter validation
- **Event Support**: Planned future feature for WoT events
- **URL Handling**: Supports both relative and absolute URLs in forms
- **Security**: HTTP Basic Auth, Bearer tokens, API keys
- **Grouping**: Properties from same thing are grouped in Home Assistant

## Thing Discovery & URL Resolution

### Base URL Determination
- Things are identified by their **base URL** (http/https)
- Base URL extracted from Thing Description `@context` and `id` fields
- Supports both secure (https) and insecure (http) connections

### Form URL Resolution
- **Absolute URLs**: Used as-is from Thing Description forms
- **Relative URLs**: Resolved against the thing's base URL
- Handles URL path joining correctly (e.g., `/properties/temp` + base URL)

## Property Handling

### Sensor Creation
- Each WoT property becomes a Home Assistant sensor
- Sensor names derived from property titles or IDs
- Device class and unit of measurement inferred from WoT semantics
- State class determined by property type (measurement, total, etc.)

### Visualization & Graphing
Properties display appropriate graphs based on their WoT type annotations:
- **Temperature**: Line graphs with temperature units
- **Humidity**: Percentage-based visualizations  
- **Power/Energy**: Energy monitoring graphs
- **Boolean**: Binary state indicators
- **Numeric**: Generic measurement graphs
- **String**: Text-based displays

### Polling & Updates
- Configurable polling intervals per thing
- Efficient HTTP requests with proper error handling
- Supports various content types (JSON, plain text, etc.)

## Action Support

### Action Discovery
- Actions parsed from Thing Description `actions` section
- Input/output schemas validated against WoT specifications
- Action forms support GET/POST methods with proper content types

### Action Invocation
- Home Assistant services created for each WoT action
- Parameter validation using WoT input schemas
- Proper HTTP method handling (GET for no-input, POST for input actions)
- Response handling and error reporting

## Authentication & Security

### Supported Auth Methods
- **HTTP Basic Authentication**: Username/password
- **Bearer Tokens**: JWT or API tokens in Authorization header
- **API Key Authentication**: Custom header or query parameter auth
- **No Authentication**: For public endpoints

### Security Considerations
- Credentials stored securely in Home Assistant config entries
- Support for both HTTP and HTTPS endpoints
- Proper certificate validation for HTTPS
- Timeout handling to prevent hanging requests

## Configuration

### YAML Configuration
```yaml
wot_http:
  - name: "My WoT Device"
    base_url: "https://device.local"
    thing_description_url: "https://device.local/td"
    auth_type: "basic"  # basic, bearer, api_key, none
    username: "user"    # for basic auth
    password: "pass"    # for basic auth
    poll_interval: 30   # seconds
```

### Config Flow UI
- User-friendly setup through Home Assistant UI
- Automatic Thing Description fetching and validation
- Auth method selection with appropriate input fields
- Preview of discovered properties and actions

## Development Guidelines

### Code Standards
- Follow Home Assistant development patterns
- Use `async`/`await` for all I/O operations
- Proper error handling and logging
- Type hints throughout codebase
- Comprehensive test coverage

### Critical Rule: No Semantic Assumptions
**NEVER assume the semantics of properties or actions based on their names alone.** 
- Don't infer device classes from property names (e.g., "temp" ≠ temperature)
- Don't assume units or types from names
- Only use explicit WoT Thing Description metadata:
  - Use `@type` annotations for semantic meaning
  - Use `unit` field for measurements
  - Use WoT data schemas for type validation
  - Use semantic vocabularies when available
- Property names are arbitrary identifiers - treat them as such

### Testing
- Unit tests for all core functionality
- Integration tests with mock WoT devices
- Test various Thing Description formats
- Authentication method testing
- URL resolution edge cases

### Key Development Commands
```bash
# Run tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_sensor.py -v

# Run with coverage
python -m pytest --cov=. tests/

# Type checking (if mypy available)
mypy sensor.py actions.py

# Home Assistant validation
hass --script check_config
```

## Future Roadmap

### Planned Features
1. **Event Support**: WebSocket/SSE connections for WoT events
2. **Advanced Security**: OAuth2, certificate-based auth
3. **Discovery**: mDNS/SSDP automatic device discovery  
4. **Protocol Extensions**: CoAP, MQTT protocol bindings
5. **UI Improvements**: Custom cards for WoT device management

### Known Limitations
- Currently HTTP-only (no CoAP/MQTT support)
- Events not yet implemented
- Limited to polling-based property updates
- No automatic device discovery

## Debugging

### Common Issues
- **Connection Errors**: Check base URL accessibility and auth credentials
- **Parsing Errors**: Validate Thing Description JSON format
- **Missing Properties**: Verify property forms have readable hrefs
- **Auth Failures**: Check authentication method and credentials

### Useful Log Commands
```python
import logging
_LOGGER = logging.getLogger(__name__)
_LOGGER.debug("Thing Description: %s", td_data)
_LOGGER.error("Failed to fetch property %s: %s", prop_name, error)
```

### Debug Property Script
Use `debug_properties.py` to test property fetching outside Home Assistant:
```bash
python debug_properties.py https://device.local/td
```

## Contributing

### Pull Request Guidelines
1. All tests must pass
2. Add tests for new functionality  
3. Update documentation for API changes
4. Follow existing code style and patterns
5. Include example configurations for new features

### File Organization
- Keep WoT-specific logic in dedicated modules
- Separate concerns (parsing, HTTP, Home Assistant integration)
- Use Home Assistant's entity patterns consistently
- Maintain backward compatibility when possible