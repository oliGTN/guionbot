# Mod inventory API

Retrieve the unequipped mods for a Star Wars: Galaxy of Heroes player.

## Request

- **Method:** `POST`
- **URL:** `https://guionbot.fr/api/v1/mod-inventory.php`
- **Authentication:** Bearer API key
- **Content-Type:** `application/json`

Request body:

```json
{
  "allycode": "123456789"
}
```

The allycode must be a string containing exactly nine digits.

## Successful response

HTTP `200`:

```json
{
  "unequippedMod": [
    ...
  ]
}
```

The response contains only the `unequippedMod` key and its value from
`initialdata.inventory`. Equipped mods and all other player or inventory
data are not returned.

The endpoint requests fresh data by calling
`connect_rpc.get_player_initialdata(ac=allycode, use_cache_data=False)`.

## EA One-Time Code required

When the EA authentication flow requests an email verification code, the
endpoint returns HTTP `202 Accepted`:

```json
{
  "err_code": 100,
  "action_required": "EA_ONE_TIME_CODE",
  "message": "EA has sent a One-Time Code to the email address linked to this account. Ask the user to check their email and submit the 5- or 6-digit code in GuionBot using /connect envoie-otc in the Discord channel where GuionBot is configured. Retry this request after the code has been accepted."
}
```

The API client should display this instruction to the user. The user must submit
the code through GuionBot's Discord command `/connect envoie-otc`; the API does
not collect or transmit the code. After GuionBot confirms that the code was
accepted, the client can retry the mod-inventory request.

## Errors

- `400`: Missing or invalid JSON body / allycode.
- `401`: Missing or invalid API key.
- `403`: The API key is not authorized for `mod-inventory`, or HTTPS is required.
- `405`: Method other than POST.
- `413`: Request body exceeds the size limit.
- `429`: API rate limit exceeded.
- `202`: EA email One-Time Code is required; display the returned instruction to the user.
- `502`: RPC failed or returned an invalid response.
- `503`: Internal mod-inventory service is unavailable or not configured.

The endpoint uses the shared API read rate-limit bucket (default: 5 requests
per minute and 1,000 per rolling 24 hours).
