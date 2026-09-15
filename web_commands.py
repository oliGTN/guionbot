import sys
import os
from asyncio import run
import aiohttp
from json import dumps as json_dumps, loads as json_loads
from base64 import b64decode

from connect_rpc import set_zoneOrder, get_dict_bot_accounts
from connect_mysql import simple_execute_async, get_value_async
import goutils

async def main():
    if len(sys.argv)==1:
        ret_json = {"err_code": 400, "err_txt": "missing request name"}
        print(json_dumps(ret_json))
        return

    elif sys.argv[1] == "TBzoneOrder":
        if len(sys.argv) != 3:
            ret_json = {"err_code": 400, "err_txt": "incorrect parameter count"}
            print(json_dumps(ret_json))
            return
        else:
            order_txt = b64decode(sys.argv[2])
            order_dict = json_loads(order_txt)
            print(order_dict)
            guild_id = order_dict['guild_id']
            map_id = order_dict['tb_id']

            #Get the bot allyCode to prevent set_zoneOrder to get it each time
            dict_bot_accounts = await get_dict_bot_accounts()

            if guild_id not in dict_bot_accounts:
                ret_json = {"err_code": 400, "err_txt": "no warbot"}
                print(json_dumps(ret_json))
                return

            if dict_bot_accounts[guild_id]["locked_since"] is not None:
                ret_json = {"err_code": 400, "err_txt": "warbot in use"}
                print(json_dumps(ret_json))
                return

            bot_allyCode = dict_bot_accounts[guild_id]["allyCode"]


            #Create MYSQL session
            async with aiohttp.ClientSession() as session:
                for order in order_dict['list_orders']:
                    zone_id = order['zone_id']
                    zone_msg = order['zone_msg']
                    zone_cmd = order['zone_cmd']

                    if not zone_cmd.isnumeric() or not int(zone_cmd) in (1,2,3):
                        ret_json = {"err_code": 400, "err_txt": "incorrect parameter count"}
                        print(json_dumps(ret_json))
                        return

                    zone_cmd = int(zone_cmd)
                    ec, et = await set_zoneOrder(
                                guild_id,
                                map_id,
                                zone_id,
                                zone_msg,
                                zone_cmd,
                                None,
                                allyCode=bot_allyCode,
                                session=session)

                    if ec==0:
                        #Update message and command in tb_zones
                        if "recon" in zone_id:
                            tb_zone_id = zone_id[:-8]
                            db_cmdMsg = "recon_cmdMsg"
                            db_cmdCmd = "recon_cmdCmd"
                        else:
                            tb_zone_id = zone_id
                            db_cmdMsg = "cmdMsg"
                            db_cmdCmd = "cmdCmd"
                        query = "UPDATE tb_zones " \
                                "JOIN tb_history ON tb_history.id=tb_zones.tb_id " \
                                "SET "+db_cmdMsg+"='"+zone_msg+"', " \
                                ""+db_cmdCmd+"="+str(zone_cmd)+" " \
                                "WHERE tb_history.tb_id='"+map_id+"' " \
                                "AND tb_history.guild_id='"+guild_id+"' " \
                                "AND tb_zones.round=tb_history.current_round " \
                                "AND tb_zones.zone_id='"+tb_zone_id+"'"
                        goutils.log2("DBG", query)
                        await simple_execute_async(query)

                        #Store order for next time
                        tb_type = map_id.split(':')[0]
                        query = "SELECT id FROM tb_orders " \
                                "WHERE guild_id='"+guild_id+"' " \
                                "AND tb_type='"+tb_type+"' " \
                                "AND zone_id='"+zone_id+"' "
                        goutils.log2("DBG", query)
                        db_data = await get_value_async(query)

                        if db_data==None:
                            query = "INSERT INTO tb_orders(guild_id, tb_type, " \
                                    "zone_id) " \
                                    "VALUES('"+guild_id+"', " \
                                    "'"+tb_type+"', " \
                                    "'"+zone_id+"') "
                            goutils.log2("DBG", query)
                            await simple_execute_async(query)

                            query = "SELECT id FROM tb_orders " \
                                    "WHERE guild_id='"+guild_id+"' " \
                                    "AND tb_type='"+tb_type+"' " \
                                    "AND zone_id='"+zone_id+"' "
                            goutils.log2("DBG", query)
                            db_data = await get_value_async(query)

                        order_id = str(db_data)
                        query = "UPDATE tb_orders " \
                                "SET cmdMsg='"+zone_msg+"', " \
                                "cmdCmd="+str(zone_cmd)+" " \
                                "WHERE id="+order_id
                        goutils.log2("DBG", query)
                        await simple_execute_async(query)

    else:
        ret_json = {"err_code": 400, "err_txt": "incorrect request name"}
        print(json_dumps(ret_json))
        return

    #Normal exit
    ret_json = {"err_code": ec, "err_txt": et}
    print(json_dumps(ret_json))
    return


####################
### MAIN
####################
run(main())

