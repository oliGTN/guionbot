import os
import config
import sys
from urllib.parse import uses_netloc, urlparse
import datetime
import time
from wcwidth import wcswidth
import asyncio
from decimal import Decimal
from hashlib import md5
from json import dumps as json_dumps

import goutils
import data

##############################################################
# this global var is used in several functions
list_statq_stats = []
list_statq_stats.append(["health", 1, False])
list_statq_stats.append(["speed", 5, False])
list_statq_stats.append(["pd", 6, False])
list_statq_stats.append(["sd", 7, False])
list_statq_stats.append(["armor", 8, True])
list_statq_stats.append(["cc", 14, True])
list_statq_stats.append(["cd", 16, True])
list_statq_stats.append(["potency", 17, True])
list_statq_stats.append(["tenacity", 18, True])
list_statq_stats.append(["protec", 28, False])
##############################################################
# Command: get_player_statqj
# IN: allyCode
# IN: load_player: True if need to load player data
# Output: statq, list_unit_stats
##############################################################
async def get_player_statq(txt_allyCode):

    query = "select count(*) from statq_table"
    statq_count = await get_value_async(query)

    query = "SELECT \n" \
          + "defId,stat_name,stat_value, stat_target, \n" \
          + "CASE WHEN stat_ratio>=1.02 THEN 4 WHEN stat_ratio>=0.98 THEN 3 WHEN stat_ratio>=0.95 THEN 2 WHEN stat_ratio>=0.90 THEN 1 ELSE 0 END as score \n" \
          + "FROM( \n" \
          + "     SELECT my_roster.allyCode, my_roster.defId, stat_name, \n" \
          + "     CASE \n"

    #stat_value
    # stats values are rounded down, like in the game > FLOOR
    for stat in list_statq_stats:
        s_name = stat[0]
        s_id = stat[1]
        s_percent = stat[2]

        query += "     WHEN stat_name='"+s_name+"'   THEN CONCAT(FLOOR(stat"+str(s_id)

        if s_percent:
            query+="/1000000), '% (' , FLOOR(mod"+str(s_id)+" /1000000), '%)' ) \n"
        else:
            query+="/100000000), ' (', FLOOR(mod"+str(s_id)+" /100000000), ')') \n"

    query +="     END AS `stat_value`, \n" \
          + "     CASE \n"

    #stat_target
    # stats values are rounded down, like in the game > FLOOR
    # ratio is rounded to the nearest > ROUND
    for stat in list_statq_stats:
        s_name = stat[0]
        s_id = stat[1]
        s_percent = stat[2]

        query += "     WHEN stat_name='"+s_name+"' THEN CONCAT(FLOOR((stat"+str(s_id)+"-mod"+str(s_id)+")*(stat_avg*1.02+1)"

        if s_percent:
            query+="/1000000), '%' "
        else:
            query+="/100000000) "
        query += ", ' (',ROUND(mod"+str(s_id)+"*100/((stat"+str(s_id)+"-mod"+str(s_id)+")*(stat_avg*1.02+1)-(stat"+str(s_id)+"-mod"+str(s_id)+"))),'%)') \n"


    query +="     END AS `stat_target`, \n" \
          + "     CASE \n"

    #stat_ratio
    for stat in list_statq_stats:
        s_name = stat[0]
        s_id = stat[1]

        query += "     WHEN stat_name='"+s_name+"'   THEN ROUND((mod"+str(s_id)+" /(stat"+str(s_id)+" -mod"+str(s_id)+" )) /stat_avg / 0.02)*0.02 \n"


    query +="     END AS `stat_ratio`, coef \n" \
          + "     FROM roster AS my_roster \n" \
          + "     JOIN statq_table ON my_roster.defId=statq_table.defId AND NOT isnull(statq_table.stat_avg) \n" \
          + "     WHERE stat_avg>0 AND relic_currentTier>=5 AND allyCode="+txt_allyCode+" \n" \
          + ") ratios \n" \
          + "JOIN players ON players.allyCode = ratios.allyCode \n" \
          + "WHERE players.allyCode = "+txt_allyCode

    goutils.log2("DBG", query)
    db_data = await get_table_async(query)
    if db_data==None:
        db_data=[]
        statq = 0
    else:
        list_scores = [x[4] for x in db_data]
        statq = sum(list_scores)*statq_count/len(list_scores)

        #update staq for player
        query = "UPDATE players SET statq="+str(statq)+" WHERE allyCode="+txt_allyCode
        await simple_execute_async(query)

        #update daily statq for player
        query = "UPDATE gp_history SET statq="+str(statq)+" WHERE allyCode="+txt_allyCode+" AND date=DATE(current_timestamp)"
        await simple_execute_async(query)

    return 0, "", statq, db_data

##############################################################
# Function: compute_statq_avg
# IN: force_all (True: reset all stats / False: compute only null stats)
# OUT: none
##############################################################
def compute_statq_avg(force_all):
    #Compute stat_avg for statq_table, from KYBER1 players
    query = "UPDATE statq_table SET stat_avg = CASE \n"

    for stat in list_statq_stats:
        s_name = stat[0]
        s_id = stat[1]

        #filter relic>=3 and GP>10M PG
        query += "WHEN stat_name='"+s_name+"' THEN ( " \
                 "   select avg(mod"+str(s_id)+"/(stat"+str(s_id)+"-mod"+str(s_id)+")) " \
                 "   from roster " \
                 "   join players on players.allyCode=roster.allyCode " \
                 "   where statq_table.defId=roster.defId " \
                 "   and relic_currentTier>=5 " \
                 "   and stat"+str(s_id)+" > mod"+str(s_id)+" " \
                 "   and grand_arena_rank='KYBER1' " \
                 "   and (char_gp+ship_gp)>10000000 " \
                 "   and timestampdiff(DAY,lastUpdated,CURRENT_TIMESTAMP)<30 " \
                 ") \n"

    query+= "END \n"

    if not force_all:
        query+= "WHERE (isnull(stat_avg) OR stat_avg=0)"

    goutils.log2("DBG", query)
    simple_execute(query)

