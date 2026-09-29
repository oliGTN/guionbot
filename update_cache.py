import os
import config
import sys
import asyncio
import traceback

import go
import golog
import connect_mysql

##############################################################
#                                                            #
#                  FONCTIONS                                 #
#                                                            #
##############################################################


async def clean_old_data():
    """
    Delete players inactive for more than 6 months,
    then delete guilds with no remaining members.
    """

    golog.log("INFO", "Starting periodic database cleanup")

    # Delete players inactive for more than 6 months.
    query = """
        DELETE FROM players
        WHERE lastActivity < DATE_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 MONTH)
    """

    deleted_players = await connect_mysql.simple_execute_async(query)

    golog.log(
        "INFO",
        f"Database cleanup: deleted {deleted_players} inactive players"
    )

    # Delete guilds that no longer have any players.
    query = """
        DELETE g
        FROM guilds g
        LEFT JOIN players p ON p.guildId = g.id
        WHERE p.allyCode IS NULL
    """

    deleted_guilds = await connect_mysql.simple_execute_async(query)

    golog.log(
        "INFO",
        f"Database cleanup: deleted {deleted_guilds} empty guilds"
    )

    golog.log("INFO", "Database cleanup completed")

##############################################################
# MAIN EXECUTION
##############################################################
async def main():
    last_cleanup = 0

    while True:
        try:
            # Run database cleanup every 24 hours.
            current_time = asyncio.get_running_loop().time()

            if current_time - last_cleanup >= 86400:
                await clean_old_data()
                last_cleanup = current_time

            # Refresh and clean cache data from SWGOH API.
            await go.refresh_cache()

            await asyncio.sleep(60)

        except Exception:
            golog.log("ERR", traceback.format_exc())
            await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
