import sys
import aiohttp
from asyncio import run
from json import dumps as json_dumps, loads as json_loads
from base64 import b64decode

from connect_rpc import set_zoneOrder, get_dict_bot_accounts
from connect_mysql import simple_execute_async, get_value_async
import goutils


async def process_tbzone_order(order_dict, session):
    """Process a TB zone-order request using shared service resources."""
    guild_id = order_dict['guild_id']
    map_id = order_dict['tb_id']

    # Get the bot allyCode once to prevent set_zoneOrder() from querying it
    # for every zone.
    dict_bot_accounts = await get_dict_bot_accounts()

    if guild_id not in dict_bot_accounts:
        return {"err_code": 400, "err_txt": "no warbot"}

    if dict_bot_accounts[guild_id]["locked_since"] is not None:
        return {"err_code": 400, "err_txt": "warbot in use"}

    bot_allyCode = dict_bot_accounts[guild_id]["allyCode"]

    for order in order_dict['list_orders']:
        zone_id = order['zone_id']
        zone_msg = order['zone_msg']
        zone_cmd = order['zone_cmd']

        if not zone_cmd.isnumeric() or int(zone_cmd) not in (1, 2, 3):
            return {
                "err_code": 400,
                "err_txt": "incorrect parameter count"
            }

        zone_cmd = int(zone_cmd)

        goutils.log2("INFO", order)

        ec, et = await set_zoneOrder(
            guild_id,
            map_id,
            zone_id,
            zone_msg,
            zone_cmd,
            None,
            allyCode=bot_allyCode,
            session=session
        )

        if ec != 0:
            return {"err_code": ec, "err_txt": et}

        goutils.log2("INFO", "RPC OK")

        # Update message and command in tb_zones.
        if "recon" in zone_id:
            tb_zone_id = zone_id[:-8]
            db_cmdMsg = "recon_cmdMsg"
            db_cmdCmd = "recon_cmdCmd"
        else:
            tb_zone_id = zone_id
            db_cmdMsg = "cmdMsg"
            db_cmdCmd = "cmdCmd"

        query = (
            "UPDATE tb_zones "
            "JOIN tb_history ON tb_history.id=tb_zones.tb_id "
            "SET " + db_cmdMsg + "='" + zone_msg + "', "
            + db_cmdCmd + "=" + str(zone_cmd) + " "
            "WHERE tb_history.tb_id='" + map_id + "' "
            "AND tb_history.guild_id='" + guild_id + "' "
            "AND tb_zones.round=tb_history.current_round "
            "AND tb_zones.zone_id='" + tb_zone_id + "'"
        )
        goutils.log2("DBG", query)
        await simple_execute_async(query)

        # Store order for next time.
        tb_type = map_id.split(':')[0]
        query = (
            "SELECT id FROM tb_orders "
            "WHERE guild_id='" + guild_id + "' "
            "AND tb_type='" + tb_type + "' "
            "AND zone_id='" + zone_id + "' "
        )
        goutils.log2("DBG", query)
        db_data = await get_value_async(query)

        if db_data is None:
            query = (
                "INSERT INTO tb_orders(guild_id, tb_type, zone_id) "
                "VALUES('" + guild_id + "', "
                "'" + tb_type + "', "
                "'" + zone_id + "')"
            )
            goutils.log2("DBG", query)
            await simple_execute_async(query)

            query = (
                "SELECT id FROM tb_orders "
                "WHERE guild_id='" + guild_id + "' "
                "AND tb_type='" + tb_type + "' "
                "AND zone_id='" + zone_id + "' "
            )
            goutils.log2("DBG", query)
            db_data = await get_value_async(query)

        order_id = str(db_data)
        query = (
            "UPDATE tb_orders "
            "SET cmdMsg='" + zone_msg + "', "
            "cmdCmd=" + str(zone_cmd) + " "
            "WHERE id=" + order_id
        )
        goutils.log2("DBG", query)
        await simple_execute_async(query)

        goutils.log2("INFO", "DB OK")

    return {"err_code": ec, "err_txt": et}


async def main():
    """Legacy command-line entry point."""
    if len(sys.argv) == 1:
        print(json_dumps({
            "err_code": 400,
            "err_txt": "missing request name"
        }))
        return

    if sys.argv[1] == "TBzoneOrder":
        #Check parameter count
        if len(sys.argv) != 3:
            print(json_dumps({
                "err_code": 400,
                "err_txt": "incorrect parameter count"
            }))
            return

        order_txt = b64decode(sys.argv[2])
        order_dict = json_loads(order_txt)
        print(order_dict)

        async with aiohttp.ClientSession() as session:
            ret_json = await process_tbzone_order(order_dict, session)

        print(json_dumps(ret_json))
        return

    # Unknown request
    print(json_dumps({
        "err_code": 400,
        "err_txt": "incorrect request name"
    }))
    return




if __name__ == "__main__":
    run(main())
