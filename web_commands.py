import sys
import asyncio
import json

import connect_rpc

async def main():
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
                ec, et = await connect_rpc.set_zoneOrder(
                            guild_id,
                            map_id,
                            zone_id,
                            zone_msg,
                            zone_cmd,
                            None)

    else:
        ec = 400
        et = "incorrect request name"

    ret_json = {"err_code": ec, "err_txt": et}

    print(json.dumps(ret_json))

    return


####################
### MAIN
####################
asyncio.run(main())

