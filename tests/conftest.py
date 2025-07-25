"""Global fixtures for WoT HTTP component tests."""
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from aiohttp import ClientResponse

# Import the Home Assistant testing framework fixtures
pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)  
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations defined in the test dir."""
    yield


@pytest.fixture
def mock_setup_entry():
    """Mock async_setup_entry."""
    with patch(
        "custom_components.wot_http.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        yield mock_setup_entry


@pytest.fixture
def mock_aiohttp_session():
    """Mock aiohttp session."""
    with patch("aiohttp.ClientSession") as mock_session:
        yield mock_session


@pytest.fixture
def mock_response():
    """Mock aiohttp response."""
    response = MagicMock(spec=ClientResponse)
    response.status = 200
    response.json = AsyncMock(return_value={})
    response.text = AsyncMock(return_value="")
    return response


@pytest.fixture
def sample_thing_description():
    """Sample WoT Thing Description."""
    return {
        "@context": "https://www.w3.org/2019/wot/td/v1",
        "title": "Test Device",
        "properties": {
            "temperature": {
                "type": "number",
                "unit": "celsius",
                "readOnly": True,
                "href": "/properties/temperature"
            },
            "brightness": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
                "href": "/properties/brightness"
            }
        },
        "actions": {
            "toggle": {
                "description": "Toggle device on/off",
                "href": "/actions/toggle"
            },
            "setBrightness": {
                "description": "Set brightness level",
                "input": {
                    "type": "object",
                    "properties": {
                        "brightness": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 100
                        }
                    },
                    "required": ["brightness"]
                },
                "href": "/actions/setBrightness"
            }
        }
    }


@pytest.fixture
def sample_config_entry_data():
    """Sample config entry data."""
    return {
        "host": "192.168.1.100",
        "port": 8080,
        "name": "Test WoT Device"
    }


@pytest.fixture
def snapshot():
    """Snapshot fixture for syrupy."""
    # This will be provided by syrupy when available
    pass