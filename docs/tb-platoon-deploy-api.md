# TB platoon deployment API

This endpoint accepts a plan JSON document and deploys the requested platoon units through the bot's existing `connect_rpc.platoon_tb` function.

## Endpoint

- Method: `POST`
- URL: `https://guionbot.fr/api/v1/tb-platoon-deploy.php`
- Header: `Authorization: Bearer YOUR_API_KEY`
- Content-Type: `application/json`

It uses the same API key configuration as the TB read-only endpoints:
`/home/pi/GuionBot/SERVER_SECRETS/web_api.php`.
The PHP endpoint forwards the request to the local web command service using
`/home/pi/GuionBot/SERVER_SECRETS/web_commands.token`. The local service listens
only on `127.0.0.1:9000`.

## Request body

The request must contain a 9-digit `ally_code` and a non-empty `planets` object.
Other plan metadata (such as `plan_id`, `phase`, `player`, and `discord_id`)
is accepted but not used for deployment.

Example (valid JSON):

```json
{
  "plan_id": "a1b2c3d4",
  "phase": 4,
  "player": "ExamplePlayer",
  "ally_code": "111222333",
  "discord_id": "111111111111111111",
  "planets": {
    "Haven-class Medical Station (DS4)": {
      "zone_id": "P4-C2",
      "planet_strategy": "FULL",
      "platoons": {
        "1": [
          {
            "slot": "P4-C2|tb3-platoon-6|8",
            "squad_id": "tb3-platoon-6",
            "unit_id": "BASTILASHANDARK",
            "unit": "Bastila Shan (Fallen)"
          },
          {
            "slot": "P4-C2|tb3-platoon-6|9",
            "squad_id": "tb3-platoon-6",
            "unit_id": "VADER",
            "unit": "Darth Vader",
          }
        ]
      }
    }
  }
}
```

The zone code must match `P<phase>-C<conflict>`, for example `P4-C2`.
It is converted to the game zone identifier by zero-padding both numbers and
appending the recon suffix:

- `P4-C2` -> `tb3_mixed_phase04_conflict02_recon01`

For each distinct `(zone_id, squad_id)` pair, the service makes one call:

```python
await connect_rpc.platoon_tb(
    txt_allyCode,
    zone_id,
    platoon_id,
    requested_defIds
)
```

- `txt_allyCode`: top-level `ally_code`.
- `zone_id`: converted game zone identifier.
- `platoon_id`: assignment `squad_id`.
- `requested_defIds`: the `unit_id` values for that pair, in their original
  JSON order. The first listed unit remains first in the RPC request.

The service groups entries in first-seen order. It continues to later platoons
if an earlier RPC call fails, and returns an individual result for every group.
The API does not use the per-unit player/ally_code/discord_id fields; all
assignments are deployed using the top-level `ally_code`.

## Response

A fully successful deployment returns HTTP 200:

```json
{
  "success": true,
  "err_code": 0,
  "err_txt": "Successfully processed 1/1 platoon(s).",
  "ally_code": "368553333",
  "completed": 1,
  "total": 1,
  "results": [
    {
      "planet": "Haven-class Medical Station (DS4)",
      "zone_id": "tb3_mixed_phase04_conflict02_recon01",
      "squad_id": "tb3-platoon-6",
      "requested_defIds": ["BASTILASHANDARK", "VADER"],
      "err_code": 0,
      "err_txt": "",
      "result": {
        "noneedToDeploy_defIds": [],
        "playerUsed_defIds": [],
        "deployed_defIds": ["BASTILASHANDARK", "VADER"]
      }
    }
  ]
}
```

If at least one platoon call fails, the service returns HTTP 207 (Multi-Status)
with `success: false`, and includes both successful and failed group results.
Check each `results[].err_code`; `completed` counts successful RPC calls,
not necessarily the number of individual units deployed. A successful RPC can
also report units in `noneedToDeploy_defIds` or `playerUsed_defIds`.

## Limits and security

- HTTPS and Bearer API-key authentication are required.
- Maximum request body: 1 MiB.
- Maximum 50 planets, 200 distinct platoon groups, and 1,000 unit assignments.
- Deployment endpoint rate limit: 2 requests per rolling minute and 100 per rolling 24 hours.
- The local web command endpoint is protected by the separate web commands token and is bound to localhost.
- The endpoint never accepts a guild ID from the request; the RPC acts using the submitted top-level ally code.

HTTP status codes include 200 (all groups succeeded), 207 (partial/total group failure),
400 (invalid payload), 401 (invalid API key), 403 (HTTPS required), 405 (wrong method),
413 (request too large), 429 (rate limit), 502 (local deployment service unavailable),
and 503 (server-side configuration unavailable).
