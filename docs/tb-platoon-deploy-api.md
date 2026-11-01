# TB platoon deployment API

This endpoint accepts a plan JSON document and deploys the requested platoon units through the bot's existing `connect_rpc.platoon_tb` function.

## Endpoint

- Method: `POST`
- URL: `/api/v1/tb-platoon-deploy.php`
- Header: `Authorization: Bearer YOUR_API_KEY`
- Content-Type: `application/json`

The endpoint uses a configured API key and forwards requests to an internal
deployment service. Server-side configuration details are intentionally omitted.

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

A fully successful deployment returns HTTP 200. This response corresponds to
the single assignment in the request example above:

```json
{
  "success": true,
  "ally_code": "123456789",
  "completed": 1,
  "partial": 0,
  "failed": 0,
  "total": 1,
  "results": [
    {
      "planet": "Example Planet",
      "zone_id": "tb3_mixed_phase04_conflict02_recon01",
      "squad_id": "tb3-platoon-1",
      "platoon_strategy": "FULL",
      "requested_defIds": ["DATHCHA"],
      "status": "SUCCESS",
      "deployed_defIds": ["DATHCHA"],
      "notDeployed_defIds": []
    }
  ]
}
```

Each platoon result exposes only the deployment outcome:

- `SUCCESS`: every requested unit is deployed or was already deployed in this
  exact platoon.
- `PARTIAL`: at least one requested unit is deployed, but at least one is not.
- `FAILED`: none of the requested units is confirmed deployed.

`deployed_defIds` contains units confirmed deployed in the target platoon.
`notDeployed_defIds` contains the remaining requested units. Both lists
partition `requested_defIds`; internal checks, RPC status codes, error messages,
and intermediate result categories are not exposed.

HTTP 200 is returned only when every platoon is `SUCCESS`. Otherwise the API
returns HTTP 207 (Multi-Status). The top-level `completed`, `partial`, and
`failed` fields count platoons in each outcome category.

## Limits and security

- HTTPS and Bearer API-key authentication are required.
- Maximum request body: 1 MiB.
- Maximum 50 planets, 200 distinct platoon groups, and 1,000 unit assignments.
- Deployment endpoint rate limit: 20 requests per rolling minute and 100 per rolling 24 hours.
- The internal deployment service is not exposed publicly.
- The endpoint never accepts a guild ID from the request; the RPC acts using the submitted top-level ally code.

HTTP status codes include 200 (all groups succeeded), 207 (partial/total group failure),
400 (invalid payload), 401 (invalid API key), 403 (HTTPS required), 405 (wrong method),
413 (request too large), 429 (rate limit), 502 (local deployment service unavailable),
and 503 (server-side configuration unavailable).
