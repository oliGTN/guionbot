import sys
from asyncio import run
from json import dumps

from connect_rpc import set_zoneOrder
from connect_mysql import simple_execute, get_value
from goutils import log2

async def main():
    print("start", flush=True)
    if len(sys.argv)==1:
        ec = 400
        et = "missing request name"

    elif sys.argv[1] == "TBzoneOrder":
        if len(sys.argv) != 7:
            ec = 400
            et = "incorrect parameter count"
        else:
            guild_id = sys.argv[2]
            map_id = sys.argv[3]
            zone_id = sys.argv[4]
            zone_msg = sys.argv[5]
            if not sys.argv[6].isnumeric() or not int(sys.argv[6]) in (1,2,3):
                ec = 400
                et = "incorrect parameter count"
            else:
                zone_cmd = int(sys.argv[6])
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

    print(dumps(ret_json))

    return


####################
### MAIN
####################
run(main())

