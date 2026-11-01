# TB platoon deployment API

This endpoint accepts a plan JSON document and deploys the requested platoon units through the bot's existing `connect_rpc.platoon_tb` function.

## Endpoint

- Method: `POST`
- URL: `/api/v1/tb-platoon-deploy.php`
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

Example (valid JSON), retaining the plan format produced by the planner:

```json
{
  "plan_id": "example-plan",
  "phase": 5,
  "player": "Example Player",
  "ally_code": "123456789",
  "discord_id": "000000000000000000",
  "planets": {
    "Example Planet": {
      "zone_id": "P4-C2",
      "planet_strategy": "FULL",
      "platoon_strategies": {
        "6": "FULL"
      },
      "platoons": {
        "6": [
          {
            "priority": 1,
            "rare": true,
            "slot": "P4-C2|tb3-platoon-1|13",
            "squad_id": "tb3-platoon-1",
            "unit_id": "DATHCHA",
            "unit": "Dathcha"
          }
        ]
      }
    }
  }
}
```

`planet_strategy`, `priority`, and `rare` are accepted as part of the plan
format but are not used by the deployment endpoint. The `platoon_strategies`
object maps each key in `platoons` to its required strategy (`FULL` or
`PRELOAD`). The assignment arrays under `platoons` retain their original
format and fields. For `PRELOAD`, the RPC call receives `preload=True`;
for `FULL`, it receives `preload=False`.

A strategy entry is required for every platoon key. If multiple entries resolve
to the same zone and squad, they must specify the same strategy.

The zone code must match `P<phase>-C<conflict>` for a regular zone, or `P<phase>-C<conflict>-B` for a bonus planet. Phase and conflict numbers are zero-padded to two digits in the Comlink zone identifier. The `-B` suffix selects the bonus zone identifier rather than the regular recon zone:

- `P4-C2` -> `tb3_mixed_phase04_conflict02_recon01`
- `P3-C1-B` (Zeffo) -> `tb3_mixed_phase03_conflict01_bonus_recon01`
- `P4-C3-B` (Mandalore) -> `tb3_mixed_phase04_conflict03_bonus_recon01`

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
  "ally_code": "111222333",
  "completed": 1,
  "total": 1,
  "results": [
    {
      "planet": "Haven-class Medical Station (DS4)",
      "zone_id": "tb3_mixed_phase04_conflict02_bonus_recon01",
      "squad_id": "tb3-platoon-6",
      "platoon_strategy": "FULL",
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

Each `results[]` entry includes a `status`:

- `SUCCESS`: RPC succeeded and every requested unit is accounted for as deployed,
  needing no deployment, or already deployed in this exact platoon.
- `PARTIAL`: RPC succeeded, but one or more units are in
  `playerUsed_defIds`, missing from all outcome lists, duplicated across lists,
  unexpected, or a result list has an invalid format.
- `ERROR`: the RPC returned a non-zero error. Any unit outcome lists returned
  by the RPC are preserved in `result`.

The recognized outcome lists are `deployed_defIds`, `playerUsed_defIds`,
`noneedToDeploy_defIds`, and `alreadyDeployed_defIds`. The last means the unit
is already deployed in this exact platoon and counts as fulfilled.
`playerUsed_defIds` does not count as fulfilled.

HTTP 200 is returned only when every platoon is `SUCCESS`. Otherwise the API
returns HTTP 207 (Multi-Status), with `success: false` and individual results
for all platoons. `completed` counts fully successful platoons. If a result
list is inconsistent, the platoon includes a `validation` object identifying
missing, unexpected, duplicated, or malformed categories.

## Limits and security

- HTTPS and Bearer API-key authentication are required.
- Maximum request body: 1 MiB.
- Maximum 50 planets, 200 distinct platoon groups, and 1,000 unit assignments.
- Deployment endpoint rate limit: 20 requests per rolling minute and 100 per rolling 24 hours.
- The internal deployment service is protected by a separate service token and is not exposed publicly.
- The endpoint never accepts a guild ID from the request; the RPC acts using the submitted top-level ally code.

HTTP status codes include 200 (all groups succeeded), 207 (partial/total group failure),
400 (invalid payload), 401 (invalid API key), 403 (HTTPS required), 405 (wrong method),
413 (request too large), 429 (rate limit), 502 (local deployment service unavailable),
and 503 (server-side configuration unavailable).
