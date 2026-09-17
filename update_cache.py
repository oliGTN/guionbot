import os
import config
import sys
import asyncio
import traceback

import go
import golog

##############################################################
#                                                            #
#                  FONCTIONS                                 #
#                                                            #
##############################################################


##############################################################
# MAIN EXECUTION
##############################################################
async def main():
    while True:
        try:
            #REFRESH and CLEAN CACHE DATA FROM SWGOH API
            await go.refresh_cache()
            await asyncio.sleep(60) # wait 1 minute before next loop

        except Exception as e:
            golog.log("ERR", traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())

