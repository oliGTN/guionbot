"""Exclusive routing of administrator commands to a development bot instance.

The production and development bot processes share this table. A development
process claims each configured administrator for a short lease; production
silently ignores commands from administrators with a live lease.
"""
import asyncio
import hashlib
import secrets

import connect_mysql
import golog


LEASE_SECONDS = 90
HEARTBEAT_SECONDS = 25
TABLE_NAME = "bot_command_ownership"

_instance_id = secrets.token_hex(16)
_token = secrets.token_hex(32)
_token_hash = hashlib.sha256(_token.encode("utf-8")).hexdigest()
_enabled = False
_admin_ids = []


async def _ensure_table():
    query = """
        CREATE TABLE IF NOT EXISTS bot_command_ownership (
            discord_user_id BIGINT UNSIGNED NOT NULL PRIMARY KEY,
            instance_id CHAR(32) NOT NULL,
            token_hash CHAR(64) NOT NULL,
            heartbeat DATETIME NOT NULL,
            expires_at DATETIME NOT NULL,
            INDEX idx_bot_command_ownership_expires (expires_at)
        ) ENGINE=InnoDB
    """
    await connect_mysql.simple_execute_async(query)


async def acquire(admin_ids):
    """Acquire exclusive command ownership for all configured administrators."""
    global _enabled, _admin_ids

    admin_ids = sorted({int(user_id) for user_id in admin_ids if str(user_id).strip()})
    if not admin_ids:
        raise RuntimeError("GO_ADMIN_IDS is empty; cannot acquire admin command ownership")

    await _ensure_table()
    _admin_ids = admin_ids

    try:
        for user_id in admin_ids:
            # The conditional assignments only replace an expired lease, or
            # refresh a lease already belonging to this exact process.
            query = """
                INSERT INTO bot_command_ownership
                    (discord_user_id, instance_id, token_hash, heartbeat, expires_at)
                VALUES (%s, %s, %s, NOW(), DATE_ADD(NOW(), INTERVAL %s SECOND))
                ON DUPLICATE KEY UPDATE
                    instance_id = IF(
                        expires_at < NOW() OR instance_id = VALUES(instance_id),
                        VALUES(instance_id), instance_id
                    ),
                    token_hash = IF(
                        expires_at < NOW() OR instance_id = VALUES(instance_id),
                        VALUES(token_hash), token_hash
                    ),
                    heartbeat = IF(
                        expires_at < NOW() OR instance_id = VALUES(instance_id),
                        NOW(), heartbeat
                    ),
                    expires_at = IF(
                        expires_at < NOW() OR instance_id = VALUES(instance_id),
                        DATE_ADD(NOW(), INTERVAL %s SECOND), expires_at
                    )
            """
            await connect_mysql.simple_execute_async(
                query,
                (user_id, _instance_id, _token_hash, LEASE_SECONDS, LEASE_SECONDS)
            )

            row = await connect_mysql.get_line_async(
                """
                SELECT instance_id, token_hash, expires_at > NOW()
                FROM bot_command_ownership
                WHERE discord_user_id = %s
                """,
                (user_id,)
            )
            if not row or row[0] != _instance_id or row[1] != _token_hash or not row[2]:
                raise RuntimeError(
                    "Administrator Discord ID "
                    + str(user_id)
                    + " is already owned by another bot instance"
                )

        _enabled = True
        golog.log(
            "INFO",
            "Exclusive admin command ownership acquired for "
            + ", ".join(str(user_id) for user_id in admin_ids)
            + " (instance "
            + _instance_id
            + ")"
        )

    except Exception:
        await release()
        raise


async def heartbeat():
    """Renew all leases and fail closed if ownership has been lost."""
    if not _enabled:
        return

    query = """
        UPDATE bot_command_ownership
        SET heartbeat = NOW(),
            expires_at = DATE_ADD(NOW(), INTERVAL %s SECOND)
        WHERE instance_id = %s AND token_hash = %s
    """
    updated = await connect_mysql.simple_execute_async(
        query, (LEASE_SECONDS, _instance_id, _token_hash)
    )
    if updated != len(_admin_ids):
        raise RuntimeError(
            "Lost exclusive admin command ownership "
            "(renewed "
            + str(updated)
            + "/"
            + str(len(_admin_ids))
            + " leases)"
        )


async def heartbeat_loop():
    while True:
        await asyncio.sleep(HEARTBEAT_SECONDS)
        try:
            await heartbeat()
        except asyncio.CancelledError:
            raise
        except Exception:
            # Do not silently reclaim a lease. Command checks below verify
            # ownership against MariaDB and will fail closed if DB is down.
            golog.log("ERR", "Admin command ownership heartbeat failed")
            golog.log("ERR", __import__("traceback").format_exc())


async def should_process_command(discord_user_id):
    """Return whether this process is the sole permitted command handler."""
    user_id = int(discord_user_id)

    try:
        row = await connect_mysql.get_line_async(
            """
            SELECT instance_id, token_hash, expires_at > NOW()
            FROM bot_command_ownership
            WHERE discord_user_id = %s
            """,
            (user_id,)
        )
    except Exception:
        golog.log(
            "ERR",
            "Cannot verify admin command ownership; ignoring command for "
            + str(user_id)
        )
        return False

    lease_is_active = bool(row and row[2])

    if _enabled:
        return bool(
            lease_is_active
            and row[0] == _instance_id
            and row[1] == _token_hash
        )

    # Production (and any non-owning instance) yields to a live dev lease.
    return not lease_is_active


async def release():
    """Release only rows still carrying this process's unguessable token."""
    global _enabled

    if not _admin_ids:
        _enabled = False
        return

    try:
        placeholders = ", ".join(["%s"] * len(_admin_ids))
        query = (
            "DELETE FROM bot_command_ownership "
            "WHERE instance_id = %s AND token_hash = %s "
            "AND discord_user_id IN (" + placeholders + ")"
        )
        await connect_mysql.simple_execute_async(
            query, (_instance_id, _token_hash, *tuple(_admin_ids))
        )
        golog.log("INFO", "Released exclusive admin command ownership")
    except Exception:
        golog.log("ERR", "Unable to release admin command ownership")
        golog.log("ERR", __import__("traceback").format_exc())
    finally:
        _enabled = False
