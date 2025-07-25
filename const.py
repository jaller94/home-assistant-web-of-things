"""Constants for the Web of Things HTTP integration."""

DOMAIN = "wot_http"

# Configuration constants
CONF_BASE_URL = "base_url"
CONF_AUTH_TYPE = "auth_type"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_TOKEN = "token"

# Authentication types
AUTH_NONE = "none"
AUTH_BASIC = "basic"
AUTH_BEARER = "bearer"

AUTH_TYPES = [AUTH_NONE, AUTH_BASIC, AUTH_BEARER]