---
name: {{ name }}
description: {{ description }}
allowed-tools: {{ allowed_tools }}
---

# {{ display_name }}

{{ overview }}

## Prerequisites

{{ prerequisites }}

## Authentication

{% if authentication %}
{{ authentication }}
{% else %}
_Describe the authentication method(s) for this API._

```bash
# Example: Bearer token authentication
curl -H "Authorization: Bearer $API_TOKEN" https://api.example.com/resource
```
{% endif %}

## Endpoints

{% if endpoints %}
{{ endpoints }}
{% else %}
_List and describe the key API endpoints._

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | /resource | List resources |
| POST   | /resource | Create resource |
| GET    | /resource/:id | Get resource by ID |
| PUT    | /resource/:id | Update resource |
| DELETE | /resource/:id | Delete resource |
{% endif %}

## Request/Response Examples

{% if request_response_examples %}
{{ request_response_examples }}
{% else %}
### Create Resource

```bash
curl -X POST https://api.example.com/resource \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "example", "value": "data"}'
```

```json
{
  "id": "abc123",
  "name": "example",
  "value": "data",
  "created_at": "2025-01-01T00:00:00Z"
}
```
{% endif %}

## Error Handling

{% if error_handling %}
{{ error_handling }}
{% else %}
_Describe common error responses and handling strategies._

| Status | Meaning | Action |
|--------|---------|--------|
| 400    | Bad Request | Check request body/params |
| 401    | Unauthorized | Refresh auth token |
| 403    | Forbidden | Check permissions |
| 404    | Not Found | Verify resource ID |
| 429    | Rate Limited | Back off and retry |
| 500    | Server Error | Retry with backoff |
{% endif %}

## Rate Limits

{% if rate_limits %}
{{ rate_limits }}
{% else %}
_Document rate limits and strategies for staying within them._

- Check response headers for rate limit info
- Implement exponential backoff on 429 responses
- Use bulk endpoints where available
- Cache responses when possible
{% endif %}

## Core Workflow

{{ core_workflow }}

## Commands

{{ commands }}

## Common Patterns

{{ patterns }}

{% if configuration %}
## Configuration

{{ configuration }}
{% endif %}

## Tips

{{ tips }}
