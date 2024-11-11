import os
import config
import sys
import asyncio

import go
import goutils

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

        except Exception as e:
            goutils.log2("ERR", str(sys.exc_info()[0]))
            goutils.log2("ERR", e)
            goutils.log2("ERR", traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())

