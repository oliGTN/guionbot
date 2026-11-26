# Territory Battle events API

Retrieve Territory Battle event activity for the guild associated with your API key.

## Endpoint

- **Method:** `POST`
- **URL:** `https://guionbot.fr/api/v1/tb-events.php`
- **Authentication:** Bearer API key
- **Content-Type:** `application/json`

## Authentication

Send the API key provided by the API provider in the `Authorization` header:

```http
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
Accept: application/json
```

Your API key is configured for a specific guild and SWGOH ally code. The guild and account are selected by the provider and cannot be overridden in the request. Ask the provider to configure both values if they are not set for your key.

The key must be allowed to access the `tb-events` endpoint.

## Request

The request body is a JSON object. The only supported parameter is `earliest_timestamp`, which is optional.

### Retrieve all available TB events

Send an empty JSON object:

```json
{}
```

With no timestamp specified, no timestamp-based filtering is requested.

### Retrieve events since a timestamp

```json
{
  "earliest_timestamp": 1764000000000
}
```

- **`earliest_timestamp`**: optional, non-negative integer representing a Unix timestamp in **milliseconds**. Events earlier than the supplied timestamp are excluded (the game service's event retrieval/filtering behavior applies).

Do not send `guild_id` or `allyCode`; those values are associated with your API key.

Unknown request parameters are rejected. The timestamp must be an integer (not a string, floating-point value or boolean) and must be non-negative.

## Successful response

HTTP `200 OK`:

```json
{
  "success": true,
  "data": {}
}
```

The example shows the response envelope only. The `data` value contains the TB event result from the SWGOH event data structure, grouped by event-file identifier and event ID. The contents depend on the active Territory Battle and event activity available from the game service.

When a timestamp is supplied, the result is limited accordingly. Without a timestamp, the API requests event data without an implicit timestamp cutoff.

If there are no available TB event channels or no event data, `data` may be empty. An empty result is not an API error when returned with HTTP 200 and `success: true`.

The API retrieval is read-only with respect to the bot's event persistence: it does not insert TB events into the bot's event database, update the event synchronization timestamp, or read/write the local TB event JSON files. (Retrieving guild data may still involve the bot's separate guild-data refresh/cache workflow.)

Always check `success` and the HTTP status before processing `data`.

## Example requests

Retrieve all events:

```bash
curl --fail-with-body -sS \
  -X POST 'https://guionbot.fr/api/v1/tb-events.php' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  --data '{}'
```

Retrieve events since a timestamp (milliseconds):

```bash
curl --fail-with-body -sS \
  -X POST 'https://guionbot.fr/api/v1/tb-events.php' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  --data '{"earliest_timestamp":1764000000000}'
```

Replace `YOUR_API_KEY` with the key supplied by the API provider. Keep it secret: do not commit it to source control, expose it in browser-side code, or include it in logs.

## Rate limits

The default read limits are shared across all read endpoints used by the same API key:

- **5 requests per rolling minute**
- **1,000 requests per rolling 24 hours**

The provider may configure different limits for your key. Successful responses include `RateLimit-Limit` and `RateLimit-Remaining` headers. When a limit is reached, the API returns HTTP `429 Too Many Requests` and a `Retry-After` header. Wait for that many seconds before retrying.

Event retrieval first obtains guild data and then retrieves TB event activity. Use a suitably long response timeout (up to 180 seconds).

## HTTP status codes

Error responses are JSON and normally contain `success: false` and an `error` message.

| HTTP status | Meaning | Client action |
|---|---|---|
| `200` | Request succeeded. | Process `data`, including an empty result. |
| `400` | Invalid JSON, unsupported parameter, or invalid `earliest_timestamp`. | Send a JSON object containing only an optional non-negative integer timestamp. |
| `401` | API key is missing, invalid, or disabled. | Check the Bearer token with the provider. |
| `403` | HTTPS is required, or the key is not allowed to use this endpoint. | Use HTTPS and ask the provider to enable `tb-events`. |
| `405` | Method not allowed. | Use POST. |
| `413` | Request body exceeds 1 KB. | Send a small JSON object. |
| `429` | Read rate limit reached. | Wait for `Retry-After` before retrying. |
| `500` | An internal server error occurred. | Retry later. |
| `502` | Guild data or TB event data could not be retrieved from the game service. | Retry later; do not treat this as an empty event result. |
| `503` | Server configuration or service is unavailable, or the key has invalid guild/account settings. | Contact the API provider. |

## Client integration recommendations

- Use HTTPS and validate the server certificate.
- Keep the API key in server-side configuration or a secret manager.
- Treat an empty `data` value as a valid empty result only when HTTP status is 200 and `success` is true.
- Cache successful responses where practical and retain the last known-good data if a request fails.
- Respect `Retry-After` and use backoff for transient server errors.
