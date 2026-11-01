# API client access configuration

The PHP API loads its private configuration from
`/home/pi/GuionBot/SERVER_SECRETS/web_api.php`, outside the web document root.

Keep the existing `api_key` and `guild_id` entries unchanged during migration.
The existing single API key remains accepted as the legacy client and retains
access to all endpoints. New clients are configured under `api_clients` using
SHA-256 hashes of their API keys.

Example addition to the existing returned PHP array:

```php
'api_clients' => [
    'tb_history_client' => [
        'key_hash' => '99a0cd77577d66e4369dd9fe44b98c5a3fa54649dc059bd3493b1af3ec69ed9c',
        'enabled' => true,
        'endpoints' => ['tb-history'],
        // Optional. Defaults are 5 requests/minute and 1,000/day.
        'rate_limits' => [
            'read' => ['per_minute' => 5, 'per_day' => 1000]
        ]
    ]
],
```

Endpoint permission names:
- `tb-platoons` — `/api/v1/tb-platoons.php`
- `tb-zones` — `/api/v1/tb-zones.php`
- `tb-history` — `/api/v1/tb-history.php`
- `tb-platoon-deploy` — `/api/v1/tb-platoon-deploy.php`

Use `['*']` to grant every endpoint. An empty list grants none.
Set `enabled` to false to revoke a client without deleting its configuration.
Read and deployment limits use separate buckets; deployment defaults are
20 requests/minute and 100/day.

The existing `api_key` legacy entry can be removed after migrating the existing
client to an `api_clients` entry with its SHA-256 hash and `endpoints => ['*']`.
Do not remove it until that migration is complete.
