# TB platoons read-only API (Apache/PHP)

This API returns current unfinished Territory Battle platoons for one configured guild. The client cannot select a guild or submit SQL.

## Endpoint

- Method: POST
- URL: https://YOUR_DOMAIN/api/v1/tb-platoons.php
- Header: `Authorization: Bearer YOUR_API_KEY`
- Body: empty or `{}`
- Success JSON: `success`, `count`, and `data` with only `platoon_name`, `unit_name`, and `player_name`.

Requires HTTPS. Limits: 5 requests per rolling minute and 1,000 per rolling 24 hours. The rate counter is a locked file under PHP's system temporary directory, shared by workers on this host; it can reset if that directory is cleared or the host reboots.

## 1. Install endpoint

Deploy `html/api/v1/tb-platoons.php` from the `chatgpt` branch into the corresponding directory under your website document root.

## 2. Database connection

The endpoint uses `require_once dirname(__DIR__, 2) . '/guionbotdb.php';` to reuse the website's existing connection. That file already loads `websitedb_secret.php`, defines `$host` and `$dbname`, and creates `$conn_guionbot` using `$username` and `$password`. No duplicate database credentials are needed in the API configuration.

**Privilege note:** this means the endpoint uses the existing `website` database account and inherits its grants. The endpoint itself only executes the fixed SELECT query, but if `website` has write permissions, this is not database-enforced read-only isolation. We can review the account's grants separately if you want to tighten them without changing other website features.

## 3. Configure API secrets outside the website root

Generate an API key on the Raspberry Pi:

```bash
openssl rand -hex 32
```

Create a configuration file outside the document root. On standard Debian Apache, the worker account is usually `www-data`.

```bash
sudo install -d -o root -g www-data -m 0750 /etc/guionbot
sudo nano /etc/guionbot/tb_platoons_api.php
sudo chown root:www-data /etc/guionbot/tb_platoons_api.php
sudo chmod 0640 /etc/guionbot/tb_platoons_api.php
```

File contents (replace the API key placeholder; the guild ID is already set):

```php
<?php
return [
    'api_key' => 'PASTE_THE_RANDOM_KEY_HERE',
    'guild_id' => 'oroRFpT_QdqL-BqbAs0UZA',
];
```

Do not put this file inside the website document root or commit it to Git. Confirm Apache can read it and connect to MariaDB.

## 4. Test from the remote server

```bash
curl --fail-with-body -sS \
  -X POST 'https://YOUR_DOMAIN/api/v1/tb-platoons.php' \
  -H 'Authorization: Bearer YOUR_API_KEY' \
  -H 'Content-Type: application/json' \
  --data '{}'
```

The returned values depend on the database. If there is no unfinished TB for the configured guild, `data` is an empty array.

## HTTP status codes

- 200: query succeeded.
- 400: malformed body or request contains parameters.
- 401: missing/incorrect key.
- 403: request was not made over HTTPS.
- 405: method other than POST.
- 413: request body too large.
- 429: rate limit reached; inspect `Retry-After`.
- 500: database query failed; details are only logged server-side.
- 503: configuration/storage unavailable or result exceeds 5,000 rows.

## Before exposing it publicly

- Verify a valid HTTPS certificate is installed.
- Check the configuration file is outside the web root and has restrictive permissions.
- Confirm the existing website DB connection works and inspect the `website` account's grants if you need database-enforced read-only isolation.
- Test invalid key (401), GET request (405), non-empty body (400), and repeated requests (429).
- If the remote server later has a stable public IP, consider an IP allowlist at the firewall or reverse proxy.
