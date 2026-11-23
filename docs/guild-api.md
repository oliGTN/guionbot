# Guild data API

Retrieve the guild profile and roster data for the guild associated with your API key.

## Endpoint

- **Method:** `POST`
- **URL:** `https://guionbot.fr/api/v1/guild.php`
- **Authentication:** Bearer API key
- **Content-Type:** `application/json`

## Authentication

Send the API key provided by the API provider in the `Authorization` header:

```http
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
Accept: application/json
```

Your API key is configured for a specific guild and, optionally, a specific SWGOH ally code. The guild and account are selected by the provider and cannot be overridden in the request. Ask the provider to configure both values if they are not set for your key.

The key must be allowed to access the `guild` endpoint.

## Request

Send an empty JSON object:

```json
{}
```

No request parameters are supported. In particular, do not send `guild_id` or `allyCode`; those values are associated with your API key.

## Successful response

HTTP `200 OK`:

```json
{
  "success": true,
  "data": {}
}
```

The example shows the response envelope only. The `data` value contains the guild object returned by the game service, including the guild profile and the available member/roster information. Its detailed fields follow the SWGOH game data structure and may evolve as the game service changes. The API passes the guild object through without reshaping it.

The guild object is returned under `data`. Read the fields you need from that object and allow for optional fields that may not be present for every guild or member.

Always check `success` and the HTTP status before processing `data`.

## Example request

```bash
curl --fail-with-body -sS \
  -X POST 'https://guionbot.fr/api/v1/guild.php' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  --data '{}'
```

Replace `YOUR_API_KEY` with the key supplied by the API provider. Keep it secret: do not commit it to source control, expose it in browser-side code, or include it in logs.

## Rate limits

The default read limits are shared across all read endpoints used by the same API key:

- **5 requests per rolling minute**
- **1,000 requests per rolling 24 hours**

The provider may configure different limits for your key. Successful responses include `RateLimit-Limit` and `RateLimit-Remaining` headers. When a limit is reached, the API returns HTTP `429 Too Many Requests` and a `Retry-After` header. Wait for that many seconds before retrying.

Guild retrieval can take time. Use a suitably long response timeout (up to 180 seconds) and cache successful responses where practical.

## HTTP status codes

Error responses are JSON and normally contain `success: false` and an `error` message.

| HTTP status | Meaning | Client action |
|---|---|---|
| `200` | Request succeeded. | Process `data`. |
| `400` | Request body is not empty or an empty JSON object. | Send `{}` or an empty body. |
| `401` | API key is missing, invalid, or disabled. | Check the Bearer token with the provider. |
| `403` | HTTPS is required, or the key is not allowed to use this endpoint. | Use HTTPS and ask the provider to enable `guild`. |
| `405` | Method not allowed. | Use POST. |
| `413` | Request body exceeds 1 KB. | Send an empty body or `{}`. |
| `429` | Read rate limit reached. | Wait for `Retry-After` before retrying. |
| `500` | An internal server error occurred. | Retry later. |
| `502` | Guild data could not be retrieved from the game service. | Retry later; do not treat this as an empty guild. |
| `503` | Server configuration or service is unavailable, or the key has invalid guild/account settings. | Contact the API provider. |

## Client integration recommendations

- Use HTTPS and validate the server certificate.
- Keep the API key in server-side configuration or a secret manager.
- Do not assume every optional field exists in every guild/member object.
- Cache successful responses and retain the last known-good guild data if a request fails.
- Respect `Retry-After` and use backoff for transient server errors.
