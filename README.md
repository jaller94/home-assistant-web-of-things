# WoT HTTP Component - Actions Implementation

## WoT Actions Support

The component now supports Web of Things actions through dynamically registered Home Assistant services.

### How It Works

1. **Thing Description Discovery**: During setup, the component fetches the WoT Thing Description from `/.well-known/wot`
2. **Action Registration**: Actions defined in the Thing Description are registered as Home Assistant services
3. **Service Naming**: Services are named as `wot_http.{entry_id}_{action_name}`
4. **Schema Validation**: Action parameters are validated based on the WoT input schema

### Example Thing Description

```json
{
  "@context": "https://www.w3.org/2019/wot/td/v1",
  "title": "Smart Light",
  "properties": {
    "brightness": {
      "type": "number",
      "minimum": 0,
      "maximum": 100
    }
  },
  "actions": {
    "toggle": {
      "description": "Toggle the light on/off"
    },
    "setBrightness": {
      "description": "Set light brightness",
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
```

### Generated Services

From the above Thing Description, these services would be created:
- `wot_http.device_123_toggle` - Toggle light
- `wot_http.device_123_setBrightness` - Set brightness with validation

### Usage in Automations

```yaml
automation:
  - alias: "Turn on light at sunset"
    trigger:
      platform: sun
      event: sunset
    action:
      - service: wot_http.device_123_toggle
      - service: wot_http.device_123_setBrightness
        data:
          brightness: 75
```

### Action Execution

Actions are executed via HTTP requests to the WoT device:
- Default method: POST
- URL: `{base_url}/actions/{action_name}` or from `href` in Thing Description
- Content-Type: `application/json`
- Request body: Action parameters as JSON

### Error Handling

- Connection errors are logged and raise HomeAssistantError
- HTTP 400+ responses are treated as action failures
- Malformed Thing Descriptions are handled gracefully
- Services are automatically unregistered when devices are removed