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

## 2. Create a restricted MariaDB account

Run as a MariaDB administrator; replace the example password with a unique random value. Do not commit it to Git.

```sql
CREATE USER 'tb_platoons_api'@'localhost'
  IDENTIFIED BY 'REPLACE_WITH_A_LONG_RANDOM_PASSWORD';

GRANT SELECT (platoon_name, unit_name, player_name)
  ON guionbotdb.tb_platoons TO 'tb_platoons_api'@'localhost';

GRANT SELECT (id, guild_id, stars_final)
  ON guionbotdb.tb_history TO 'tb_platoons_api'@'localhost';
```

This grants only column-level SELECT access needed by the endpoint, and no write privileges. If the account already exists, inspect its grants before changing anything.

## 3. Configure secrets outside the website root

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

File contents (replace both placeholders):

```php
<?php
return [
    'api_key' => 'PASTE_THE_RANDOM_KEY_HERE',
    'guild_id' => 'oroRFpT_QdqL-BqbAs0UZA',
    'db_host' => 'localhost',
    'db_name' => 'guionbotdb',
    'db_user' => 'tb_platoons_api',
    'db_password' => 'REPLACE_WITH_THE_DATABASE_PASSWORD',
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
- Check grants with `SHOW GRANTS FOR 'tb_platoons_api'@'localhost';`.
- Test invalid key (401), GET request (405), non-empty body (400), and repeated requests (429).
- If the remote server later has a stable public IP, consider an IP allowlist at the firewall or reverse proxy.
