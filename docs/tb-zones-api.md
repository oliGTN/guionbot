# TB zones read-only API

This endpoint returns the current-round zones for the configured guild whose Territory Battle has not been finalized. The client cannot choose a guild or submit SQL.

## Endpoint

- Method: POST
- URL: `https://guionbot.fr/api/v1/tb-zones.php`
- Header: `Authorization: Bearer YOUR_API_KEY`
- Content-Type: `application/json`
- Body: `{}` (or empty)

The API key and guild ID are read from `/home/pi/GuionBot/SERVER_SECRETS/web_api.php`, using the same configuration as the `tb-platoons` endpoint. The guild ID is not accepted from client input.

## Successful response

HTTP `200 OK`:

```json
{
  "success": true,
  "count": 2,
  "data": [
    {
      "zone_name": "Example zone",
      "score_step1": 100000,
      "score_step2": 200000,
      "score_step3": 300000,
      "score": 250000,
      "stars": 2
    }
  ]
}
```

The values above are illustrative. Each record contains:

- `zone_name`
- `score_step1`
- `score_step2`
- `score_step3`
- `score`
- `stars`, calculated by the SQL CASE expression:
  - `3` when `score >= score_step3`
  - `2` when `score >= score_step2`
  - `2` when `score >= score_step1`
  - `0` otherwise

The query selects rows for the configured guild where `tb_history.stars_final IS NULL` and `tb_zones.round = tb_history.current_round`. An empty `data` array with HTTP 200 is a successful response with no matching zones.

## Example request

```bash
curl -sS \
  -X POST 'https://guionbot.fr/api/v1/tb-zones.php' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  --data '{}'
```

Replace `YOUR_API_KEY` with the same key used for the platoons endpoint. Do not disable TLS certificate verification or log the API key.

## Security, rate limits, and errors

This endpoint uses the same HTTPS requirement, Bearer authentication, fixed configured guild, database connection, and rate-limit counter as `tb-platoons.php`. The two endpoints share the same limit: 5 requests per rolling minute and 1,000 per rolling 24 hours, combined.

HTTP status codes:
- `200`: success.
- `400`: malformed/non-empty request body.
- `401`: missing or invalid API key.
- `403`: HTTPS required.
- `405`: method other than POST.
- `413`: request body too large.
- `429`: rate limit reached; respect `Retry-After`.
- `500`: database query failed.
- `503`: configuration/rate-limit storage unavailable or result exceeds 5,000 rows.

The client should retain its last successful dataset if a request fails, rather than replacing it with an empty array.
