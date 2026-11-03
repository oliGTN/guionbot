# Guild Connected Accounts API

Returns the connected-account authentication status for all players
belonging to the guild configured on the server.

## Endpoint

- Method: `POST`
- URL: `/api/v1/guild-connected-accounts.php`
- Authentication: Bearer API key
- Content-Type: `application/json`

No input parameters are required.

The request body can be empty or `{}`.

The guild ID is taken from the server-side `web_api.php` configuration.
The client cannot specify or override it.

## Success response

HTTP `200`:

```json
{
  "success": true,
  "data": {"123456789": true, "111222333": true, "555444333": false, ...}
}
