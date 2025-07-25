"""HTTP utilities for WoT HTTP integration."""
import ssl
import functools
import base64
from typing import Any, Optional
from urllib.parse import urlparse

import aiohttp

from homeassistant.core import HomeAssistant
from .const import AUTH_BASIC, AUTH_BEARER


async def create_http_session(
    hass: HomeAssistant, 
    base_url: str, 
    auth_type: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    token: Optional[str] = None
) -> aiohttp.ClientSession:
    """Create HTTP session with appropriate SSL context and authentication."""
    parsed = urlparse(base_url)
    
    # SSL configuration
    if parsed.scheme == 'https':
        ssl_context = await hass.async_add_executor_job(
            functools.partial(ssl.create_default_context)
        )
        connector = aiohttp.TCPConnector(ssl=ssl_context)
    else:
        connector = None
    
    # Authentication headers
    headers = {}
    if auth_type == AUTH_BASIC and username and password:
        # HTTP Basic Authentication
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        headers["Authorization"] = f"Basic {encoded_credentials}"
    elif auth_type == AUTH_BEARER and token:
        # Bearer Token Authentication
        headers["Authorization"] = f"Bearer {token}"
    
    return aiohttp.ClientSession(connector=connector, headers=headers)


def resolve_url(base_url: str, href: str) -> str:
    """Resolve href to absolute URL."""
    if href.lower().startswith(('http://', 'https://')):
        return href
    elif href.startswith('/'):
        return f"{base_url.rstrip('/')}{href}"
    else:
        return f"{base_url.rstrip('/')}/{href}"


def is_thing_description(data: Any) -> bool:
    """Check if data looks like a WoT Thing Description."""
    if not isinstance(data, dict):
        return False
    
    has_context = "@context" in data
    has_properties = "properties" in data and isinstance(data["properties"], dict)
    has_title = "title" in data
    has_type_thing = data.get("@type") == "Thing" or "Thing" in str(data.get("@type", ""))
    
    return (has_context or has_properties) and (has_title or has_type_thing or has_properties)


def get_property_url(base_url: str, prop_name: str, prop_info: dict) -> str:
    """Get property URL from WoT 1.0 or 1.1 format."""
    # WoT 1.0 format
    if "href" in prop_info:
        return resolve_url(base_url, prop_info['href'])
    
    # WoT 1.1 format - forms array
    if "forms" in prop_info and isinstance(prop_info["forms"], list):
        for form in prop_info["forms"]:
            if isinstance(form, dict) and "href" in form:
                href = form["href"]
                if not href.lower().startswith(('ws://', 'wss://')):
                    ops = form.get("op", [])
                    if "readproperty" in ops or not ops:
                        return resolve_url(base_url, href)
    
    # Fallback
    return f"{base_url.rstrip('/')}/properties/{prop_name}"


def parse_property_value(response_data: Any) -> Any:
    """Parse property value from various response formats."""
    if isinstance(response_data, dict) and "value" in response_data:
        # WoT standard format: {"value": actual_value}
        return response_data["value"]
    elif isinstance(response_data, dict) and len(response_data) == 1:
        # Single key-value pair
        return list(response_data.values())[0]
    else:
        # Direct value or complex object
        return response_data


def convert_text_to_number(text: str) -> Any:
    """Convert text to number if possible, otherwise return as string."""
    try:
        return float(text) if '.' in text else int(text)
    except ValueError:
        return text