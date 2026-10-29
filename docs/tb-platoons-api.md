# TB platoons API

This API lets a remote client retrieve the current unfinished Territory Battle platoon assignments for the guild configured by the API provider.

The endpoint is read-only. The client cannot select a guild, change the query, or submit SQL.

## Endpoint

- **Method:** `POST`
- **URL:** `https://guionbot.fr/api/v1/tb-platoons.php`
- **Authentication:** Bearer API key
- **Content-Type:** `application/json`

### Request headers

```http
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
Accept: application/json
```

### Request body

Send an empty body or an empty JSON object:

```json
{}
```

No parameters are required. In particular, do not send a `guild_id`: the API always returns data for the guild configured by the provider.

## Successful response

HTTP `200 OK`:

```json
{
  "success": true,
  "count": 2,
  "data": [
    {
      "platoon_name": "Platoon 1",
      "unit_name": "Darth Vader",
      "player_name": "PlayerOne"
    },
    {
      "platoon_name": "Platoon 1",
      "unit_name": "Bastila Shan (Fallen)",
      "player_name": null
    }
  ]
}
```

The example values are illustrative. The response contains:

| Field | Type | Description |
|---|---|---|
| `success` | boolean | `true` when the query completed successfully. |
| `count` | integer | Number of returned records. |
| `data` | array | Current unfinished TB platoon assignments. |
| `data[].platoon_name` | string | Platoon name. |
| `data[].unit_name` | string | Unit required by that platoon. |
| `data[].player_name` | string or null | Player who has already assigned the unit; `null` when no player is recorded. |

An empty `data` array with `count: 0` and `success: true` is a successful response: there are currently no matching unfinished platoon records.

The API returns at most 5,000 records. If the result would exceed this limit, the API returns HTTP `503` instead of a truncated dataset.

## Example request

Using curl:

```bash
curl --fail-with-body -sS \
  -X POST 'https://guionbot.fr/api/v1/tb-platoons.php' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  --data '{}'
```

Replace `YOUR_API_KEY` with the API key provided to you. Keep the key secret: do not commit it to source control, expose it in client-side browser code, or include it in logs.

## Rate limits

The API key is subject to these shared limits:

- **5 requests per rolling minute**
- **1,000 requests per rolling 24 hours**

When the limit is reached, the API returns HTTP `429 Too Many Requests` and a `Retry-After` header containing the number of seconds to wait before retrying.

The response also includes rate-limit headers:

- `RateLimit-Limit`: per-minute request limit (`5`).
- `RateLimit-Remaining`: remaining requests in the current minute, when available.

Cache the last successful response where practical instead of polling unnecessarily.

## HTTP status codes and errors

Error responses use JSON with `success: false` and an `error` message.

| HTTP status | Meaning | Client action |
|---|---|---|
| `200` | Request succeeded. | Process `data`, including an empty array. |
| `400` | Invalid request body. Only an empty body or `{}` is accepted. | Send an empty body or `{}`. |
| `401` | Missing or invalid API key. | Check the Bearer token. |
| `403` | HTTPS is required. | Use the HTTPS endpoint. |
| `405` | Method not allowed. | Use POST. |
| `413` | Request body is too large. | Send an empty body or `{}`. |
| `429` | Rate limit reached. | Wait for the number of seconds in `Retry-After` before retrying. |
| `500` | The server could not retrieve the data. | Retry later; internal database details are not exposed. |
| `503` | Server configuration/storage is unavailable, or the result exceeds 5,000 records. | Retry later or contact the API provider. |

For any non-200 response, do not replace a previously cached successful dataset with an empty list. Treat an empty list as valid only when received in a successful HTTP 200 response with `success: true`.

## Client integration recommendations

- Use HTTPS and validate the server certificate. Do not disable TLS verification.
- Keep the API key in server-side configuration or a secret manager, not in a public frontend.
- Set reasonable connection and response timeouts.
- Respect `Retry-After` on HTTP 429; do not retry immediately in a tight loop.
- Cache successful responses and retain the last known-good data if a request fails.
- Handle `player_name: null` as an unassigned unit.
