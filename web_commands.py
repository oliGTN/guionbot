import sys
from asyncio import run
from json import dumps as json_dumps, loads as json_loads
from base64 import b64decode

from connect_rpc import set_zoneOrder
from connect_mysql import simple_execute, get_value
from goutils import log2

async def main():
    if len(sys.argv)==1:
        ec = 400
        et = "missing request name"

    elif sys.argv[1] == "TBzoneOrder":
        if len(sys.argv) != 3:
            ec = 400
            et = "incorrect parameter count"
        else:
            order_txt = b64decode(sys.argv[2])
            order_dict = json_loads(order_txt)
            print(order_dict)
            guild_id = order_dict['guild_id']
            map_id = order_dict['tb_id']

            for order in order_dict['list_orders']:
                zone_id = order['zone_id']
                zone_msg = order['zone_msg']
                zone_cmd = order['zone_cmd']

                if not zone_cmd.isnumeric() or not int(zone_cmd) in (1,2,3):
                    ec = 400
                    et = "incorrect parameter count"
                    continue

                zone_cmd = int(zone_cmd)
                ec, et = await set_zoneOrder(
                            guild_id,
                            map_id,
                            zone_id,
                            zone_msg,
                            zone_cmd,
                            None)

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
                    log2("DBG", query)
                    simple_execute(query)

                    #Store order for next time
                    tb_type = map_id.split(':')[0]
                    query = "SELECT id FROM tb_orders " \
                            "WHERE guild_id='"+guild_id+"' " \
                            "AND tb_type='"+tb_type+"' " \
                            "AND zone_id='"+zone_id+"' "
                    log2("DBG", query)
                    db_data = get_value(query)

                    if db_data==None:
                        query = "INSERT INTO tb_orders(guild_id, tb_type, " \
                                "zone_id) " \
                                "VALUES('"+guild_id+"', " \
                                "'"+tb_type+"', " \
                                "'"+zone_id+"') "
                        log2("DBG", query)
                        simple_execute(query)

                        query = "SELECT id FROM tb_orders " \
                                "WHERE guild_id='"+guild_id+"' " \
                                "AND tb_type='"+tb_type+"' " \
                                "AND zone_id='"+zone_id+"' "
                        log2("DBG", query)
                        db_data = get_value(query)

                    order_id = str(db_data)
                    query = "UPDATE tb_orders " \
                            "SET cmdMsg='"+zone_msg+"', " \
                            "cmdCmd="+str(zone_cmd)+" " \
                            "WHERE id="+order_id
                    log2("DBG", query)
                    simple_execute(query)

    else:
        ec = 400
        et = "incorrect request name"

    ret_json = {"err_code": ec, "err_txt": et}

    print(json_dumps(ret_json))

    return


####################
### MAIN
####################
run(main())

