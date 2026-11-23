# RPC-backed read-only API endpoints

These endpoints use the normal API Bearer key and the per-client endpoint allow-list. The guild and connected game account are selected by the API key; callers cannot override either value in the request.

## Per-key configuration

In `/home/pi/GuionBot/SERVER_SECRETS/web_api.php`, configure each client with its own `guild_id` and `allyCode`:

```php
return [
    'api_clients' => [
        'client_name' => [
            'api_key' => 'CLIENT_SECRET',
            'enabled' => true,
            'guild_id' => 'SWGOH_GUILD_ID',
            'allyCode' => '123456789',
            'endpoints' => ['tb-mapstats', 'guild', 'tb-events'],
            'rate_limits' => [
                'read' => ['per_minute' => 5, 'per_day' => 1000],
            ],
        ],
    ],
];
```

The `guild_id` setting is now per API client. Existing clients that use guild-scoped endpoints (including `tb-history`, `tb-zones`, and `tb-platoons`) must also have their guild ID moved into their own client entry. The `allyCode` setting is required by the three new endpoints.

## Endpoints

All endpoints require HTTPS, POST, and a Bearer API key. Send an empty body or `{}`. Responses are JSON and are gzip-compressed when the caller advertises `Accept-Encoding: gzip`.

| Endpoint | API permission | Data source |
| --- | --- | --- |
| `/api/v1/tb-mapstats.php` | `tb-mapstats` | `connect_rpc.get_TBmapstats_data(guild_id, True, allyCode=allyCode)` |
| `/api/v1/guild.php` | `guild` | `connect_rpc.get_guild_data_from_id(guild_id, True, allyCode=allyCode)` |
| `/api/v1/tb-events.php` | `tb-events` | Retrieves guild data with the configured account, then calls `connect_rpc.get_event_data(dict_guild, ["TB"], True, allyCode=None)` |

Successful responses use `{"success":true,"data":...}`. RPC errors are returned as an HTTP error with a generic error message; internal RPC details are logged server-side.
