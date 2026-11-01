# TB history API

The TB history API provides read-only historical and current Rise of the Empire (ROTE) Territory Battle data for the guild configured by the API provider.

The endpoint supports retrieving one TB, a list of TBs, or the most recent 500 matching TBs. The client cannot choose a guild, submit SQL, or access the internal database TB identifier.

## Endpoint

- **Method:** `POST`
- **URL:** `https://guionbot.fr/api/v1/tb-history.php`
- **Authentication:** Bearer API key
- **Content-Type:** `application/json`

### Request headers

```http
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
Accept: application/json
```

The API key must belong to a client whose endpoint allowlist includes `tb-history` (or `*`). The guild ID is read from the server-side API configuration and is never accepted from the request.

## Request body

The body must be a JSON object. All fields are optional, but at most one of `tb_id` and `tb_ids` may be supplied.

| Field | Type | Description |
|---|---|---|
| `tb_id` | string | Return the TB matching this public TB identifier. |
| `tb_ids` | array of strings | Return the matching TBs for 1 to 100 public TB identifiers. |
| `blocks` | array of strings | Select response data blocks: `zones` and/or `players`. Defaults to both. |

Only ROTE TB3 Mixed history records are returned. Unknown request fields or block names are rejected.

### Examples

Retrieve the latest matching TB history records, including both blocks:

```json
{}
```

Retrieve one TB:

```json
{
  "tb_id": "TB_EVENT_TB3_MIXED:O1793034000000"
}
```

Retrieve several TBs, returning only zone data:

```json
{
  "tb_ids": [
    "TB_EVENT_TB3_MIXED:O1793034000000",
    "TB_EVENT_TB3_MIXED:O1792429200000"
  ],
  "blocks": ["zones"]
}
```

Retrieve player data only:

```json
{
  "tb_id": "TB_EVENT_TB3_MIXED:O1793034000000",
  "blocks": ["players"]
}
```

The `tb_id` values above are illustrative. Use the public identifier returned by this API; the internal `tb_history.id` database key is never exposed.

## Successful response

HTTP `200 OK`:

```json
{
  "success": true,
  "generated": "2026-11-02T00:00:00Z",
  "tbs": [
    {
      "tb_id": "TB_EVENT_TB3_MIXED:O1793034000000",
      "status": "current",
      "started": "2026-10-26T00:00:00Z",
      "ended": null,
      "rounds": [
        {
          "round": 1,
          "start": "2026-10-26T00:00:00Z",
          "end": "2026-10-27T00:00:00Z"
        },
        {
          "round": 2,
          "start": "2026-10-27T00:00:00Z",
          "end": null
        }
      ],
      "members": 50,
      "events_complete": false,
      "coverage": [
        {
          "zone_id": "tb3_mixed_ls_conflict01",
          "round": 2,
          "events_total": 12345,
          "mapstats_total": 12345,
          "coverage": 1.0
        }
      ],
      "zones": [],
      "players": []
    }
  ]
}
```

The example is illustrative; timestamps, identifiers, counts and array contents depend on the selected TB and available data. The example shows only two rounds for brevity; the API returns all applicable rounds.

Top-level fields:

| Field | Type | Description |
|---|---|---|
| `success` | boolean | `true` when the request completed successfully. |
| `generated` | string | UTC timestamp when the response was generated, in ISO-8601 format. |
| `tbs` | array | Matching TB history records, ordered newest first. |

Each TB contains:

| Field | Type | Description |
|---|---|---|
| `tb_id` | string | Public game TB identifier. |
| `status` | string | `current` or `finished`. |
| `started` | string or null | TB start timestamp in UTC. |
| `ended` | string or null | Estimated end timestamp (start + 144 hours) for a finished TB; otherwise null. |
| `rounds` | array | Round numbers and their UTC start/end timestamps. The end of the current unfinished round is null. |
| `members` | integer or null | Member count recorded for round 1, when available. |
| `events_complete` | boolean | Whether mapstats are available and event totals meet the endpoint's coverage check for the zones it can compare. |
| `coverage` | array, optional | Per-zone comparison between event totals and mapstats totals, included when comparable zone data exists. |
| `zones` | array, optional | Present when the `zones` block was requested. |
| `players` | array, optional | Present when the `players` block was requested. |

### Zone block

Each item in `zones` represents a zone, with its per-round records grouped under that zone.

Zone fields:

| Field | Type | Description |
|---|---|---|
| `zone_id` | string | Game zone identifier. |
| `name` | string or null | Zone display name. |
| `alignment` | string or null | `LS`, `DS`, `MS`, or null when the zone is not one of the recognized conflict alignments. |
| `is_bonus` | boolean | Whether the zone is a bonus zone. |
| `thresholds` | array of integers or nulls | Star thresholds in order: one, two, and three stars. |
| `rounds` | array | Per-round zone data. |

Each zone round contains:

| Field | Type | Description |
|---|---|---|
| `round` | integer | Round number. |
| `score_end` | integer or null | Stored cumulative zone score. |
| `score_raw` | null | Reserved field; currently always null. |
| `stars_end` | integer or null | Stars calculated from the score and the three thresholds (0–3); null when the score or a threshold is unavailable. |
| `strategy` | string or null | Recognized strategy label: `Full`, `Pré remplir`, `Pas d'étoile`, or null. |
| `strategy_code` | integer or null | Stored strategy command code. |
| `recon_filled` | array of six integers or nulls | Reconnaissance progress values, in the order stored for the zone. |
| `platoon_points` | null | Reserved field; currently always null. |

### Player block

Each item in `players` represents a player identified in the TB phase-score data or available mapstats.

| Field | Type | Description |
|---|---|---|
| `player_id` | string | Game player ID. |
| `ally_code` | string or null | Ally code when a player profile is available. |
| `name` | string or null | Most recently updated player name available to the server. |
| `rounds` | array | Six round entries, one for each TB round. |

Each player round contains:

| Field | Type | Description |
|---|---|---|
| `round` | integer | Round number (1–6). |
| `present` | boolean | Whether the player has phase-score or relevant mapstats data for this round. |
| `gp` | integer or null | Total GP recorded for the round. |
| `gp_chars` | integer or null | Character GP recorded for the round. |
| `gp_ships` | integer or null | Ship GP recorded for the round. |
| `deploy_points` | integer or null | Deployment points from mapstats. |
| `combat_points` | integer or null | `summary - deploy_points`, when both values are available. |
| `summary` | integer or null | Summary points from mapstats. |
| `strike_attempts` | integer or null | Strike mission attempts from mapstats. |
| `waves_won` | integer or null | Strike encounters/waves recorded as won in mapstats. |
| `covert_attempts` | integer or null | Covert mission attempts from mapstats. |
| `covert_done` | integer or null | Completed covert missions, summed from mission-specific mapstats. |
| `units_donated` | integer or null | Donated units recorded in mapstats. |
| `disobey` | integer or null | Disobey count recorded in mapstats. |

A null mapstats-derived value means that the relevant mapstats value is unavailable; it must not be interpreted as zero. A zero means the mapstats data was available and recorded no value for that player/statistic. If mapstats are unavailable, the API can still return phase-score data, but mapstats-derived fields are null and `events_complete` is false.

### Coverage

When available, each `coverage` item contains:

- `zone_id`: zone identifier.
- `round`: latest stored round for that zone.
- `events_total`: total relevant conflict deploy/contribution event points recorded for the zone.
- `mapstats_total`: corresponding cumulative zone total from mapstats.
- `coverage`: ratio of event total to mapstats total, rounded to four decimal places, or null when it cannot be compared.

The API marks `events_complete` true only when it has at least one comparable zone and all comparable zones pass the coverage check (at least 0.95, with the zero-total case handled separately). Zones without a usable mapstats player-stat collection are skipped by this comparison. Therefore, `events_complete` is a coverage indicator, not a guarantee that every possible event or statistic is available.

## Current and finished TB data

- **Current TB:** mapstats are retrieved on demand from the GuionBot web command server. The API does not create or persist a mapstats snapshot as part of this request.
- **Finished TB:** mapstats are read from the archived file for that guild and TB.
- If mapstats cannot be retrieved or the archive is unavailable, the API can still return the database-backed TB, zone and phase-score information. Mapstats-derived player values will be null.

All returned timestamps are UTC. The round boundaries are calculated as 24-hour intervals from the stored TB start timestamp.

## Example request

```bash
curl --fail-with-body -sS \
  -X POST 'https://guionbot.fr/api/v1/tb-history.php' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json' \
  --data '{
    "tb_id": "TB_EVENT_TB3_MIXED:O1793034000000",
    "blocks": ["zones", "players"]
  }'
```

Replace `YOUR_API_KEY` with the key provided by the API provider. Keep it secret: do not commit it to source control, expose it in client-side browser code, or include it in logs.

## Result limits and rate limits

- A request can return at most **500 TB records**. If more than 500 match, the API returns HTTP `503` rather than a truncated result.
- The default read rate limit is **5 requests per rolling minute** and **1,000 requests per rolling 24 hours** per API client.
- Read limits are shared across endpoints using the same client and read bucket, not counted separately for this endpoint.
- A client-specific rate limit can override the defaults in the server-side API configuration.

When the rate limit is reached, the API returns HTTP `429 Too Many Requests` with a `Retry-After` header. The response also includes `RateLimit-Limit` and `RateLimit-Remaining` on successful requests.

## HTTP status codes and errors

Error responses use JSON with `success: false` and an `error` message.

| HTTP status | Meaning | Client action |
|---|---|---|
| `200` | Request succeeded. An empty `tbs` array is a valid result. | Process the returned TB records. |
| `400` | Invalid JSON object, unknown request field, invalid TB identifier/list, or invalid/unsupported block. | Correct the request body. |
| `401` | Missing, invalid, or disabled API key. | Check the Bearer token and client configuration. |
| `403` | HTTPS is required, or the client is not allowed to use this endpoint. | Use HTTPS and ask the provider to enable `tb-history` for the client. |
| `405` | Method not allowed. | Use POST. |
| `413` | Request body exceeds 4 KB. | Reduce the request body. |
| `429` | Read rate limit reached. | Wait for `Retry-After` before retrying. |
| `500` | Database query or server-side setup failed. | Retry later; internal details are not exposed in the API response. |
| `503` | API configuration or rate-limit storage is unavailable, or more than 500 TBs match. | Retry later or narrow the request with `tb_id`/`tb_ids`. |

## Client integration recommendations

- Use HTTPS and validate the server certificate. Do not disable TLS verification.
- Keep the API key in server-side configuration or a secret manager, never in a public frontend.
- Set a response timeout long enough to allow the live mapstats request (up to 45 seconds).
- Treat null mapstats values as unavailable, not as zero.
- Retain the last successful response if a request fails; do not replace it with an empty dataset on a non-200 response.
- Respect `Retry-After` and avoid retrying immediately in a tight loop.
