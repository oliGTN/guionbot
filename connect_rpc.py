import subprocess
import os
import sys
import json
import re
import threading
import time
import datetime
import inspect
import asyncio
import aiohttp
import random
import traceback

import emojis
import goutils
import data as godata
import connect_mysql
import go
import manage_events
import connect_gsheets
import connect_mysql

#GLOBAL variables for previous statuses
prev_dict_guild = {} #key=guild_id
prev_mapstats = {} #key=guild_id


dict_sem={}
async def acquire_sem(id):
    id=str(id)
    calling_func = inspect.stack()[2][3]
    #goutils.log2("DBG", "["+calling_func+"]sem to acquire: "+id)
    if not id in dict_sem:
        dict_sem[id] = threading.Semaphore()

    while not dict_sem[id].acquire(blocking=False):
        await asyncio.sleep(1)

    #goutils.log2("DBG", "["+calling_func+"]sem acquired: "+id)

async def release_sem(id):
    id=str(id)
    calling_func = inspect.stack()[2][3]
    #goutils.log2("DBG", "["+calling_func+"]sem to release: "+id)
    dict_sem[id].release()
    #goutils.log2("DBG", "["+calling_func+"]sem released: "+id)

def get_dict_bot_accounts():
    query = "SELECT guild_bots.guild_id, guild_bots.allyCode, "\
            "locked_since, guild_bots.priority_cache, lock_when_played, force_auth,"\
            "twChanOut_id, tbChanOut_id, tbChanEnd_id, " \
            "guilds.name "\
            "FROM guild_bots "\
            "LEFT JOIN guild_bot_infos ON guild_bots.guild_id=guild_bot_infos.guild_id "\
            "JOIN guilds ON guilds.id=guild_bots.guild_id "\
            "WHERE NOT isnull(guild_bots.allyCode) "
    #goutils.log2("DBG", query)
    db_data = connect_mysql.get_table(query)

    ret_dict = {}
    if db_data != None:
        for line in db_data:
            ret_dict[line[0]] = {"allyCode": str(line[1]), 
                                 "locked_since": line[2], 
                                 "priority_cache":line[3],
                                 "lock_when_played":line[4],
                                 "force_auth":line[5],
                                 "tw_channel_out":line[6],
                                 "tb_channel_out":line[7],
                                 "tb_channel_end":line[8],
                                 "guildName":line[9]}

    return ret_dict

async def lock_bot_account(guild_id):
    dict_bot_accounts = get_dict_bot_accounts()
    if not guild_id in dict_bot_accounts:
        return 1, "Ce serveur discord n'a pas de warbot"

    locked_since_txt = datetime.datetime.fromtimestamp(int(time.time())).strftime("%Y-%m-%d %H:%M:%S")
    query = "UPDATE guild_bots SET locked_since='"+locked_since_txt+"' WHERE guild_id='"+guild_id+"'"
    goutils.log2("DBG", query)
    connect_mysql.simple_execute(query)

    return 0, ""

async def unlock_bot_account(guild_id):
    query = "UPDATE guild_bots SET locked_since=NULL, force_auth=1 WHERE guild_id='"+guild_id+"'"
    goutils.log2("DBG", query)
    connect_mysql.simple_execute(query)

    return 0, ""

def islocked_bot_account(bot_allyCode):
    query = "SELECT NOT isnull(locked_since) FROM guild_bots WHERE allyCode="+str(bot_allyCode)
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_value(query)
    if db_data == None:
        return 0
    else:
        return db_data

def ispriority_cache_bot_account(bot_allyCode):
    query = "SELECT guild_bots.priority_cache "\
            "FROM guild_bots "\
            "JOIN guild_bot_infos ON guild_bot_infos.guild_id=guild_bots.guild_id "\
            "WHERE allyCode="+str(bot_allyCode)
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_value(query)
    if db_data == None:
        return 0
    else:
        return db_data

########################################################
#force_update: -1=always use cache / 0=depends on bot priority_cache option / 1=never use cache
#event_type: []/None, ["TB"], ["TW", CHAT"], ...
async def get_guild_rpc_data(guild_id, event_types, force_update, allyCode=None,
                             dict_guild=None, dict_TBmapstats=None, 
                             dict_events=None):
    calling_func = inspect.stack()[1][3]
    goutils.log2("DBG", "START ["+str(calling_func)+"]get_guild_rpc_data("+str(guild_id)+", "+str(event_types) \
                 +", "+str(force_update)+", "+str(allyCode)+")")

    if dict_guild==None:
        ec, et, dict_guild = await get_guild_data_from_id(guild_id, force_update, allyCode=allyCode)
        if ec!=0:
            return ec, et, None

    if dict_TBmapstats==None:
        if "territoryBattleStatus" in dict_guild:
            ec, et, dict_TBmapstats = await get_TBmapstats_data(guild_id, force_update, allyCode=allyCode)
            if ec!=0:
                return ec, et, None
        else:
            dict_TBmapstats={}

    if dict_events==None:
        if event_types!=None and event_types!=[]:
            ec, et, dict_events = await get_event_data(dict_guild, event_types, force_update, allyCode=allyCode)
            if ec!=0:
                return ec, et, None
        else:
            dict_events = {}

    goutils.log2("DBG", "END get_guild_rpc_data")
    return 0, "", [dict_guild, dict_TBmapstats, dict_events]

#########################################
# Get full guild data, using the bot account
async def get_guild_data_from_id(guild_id, force_update, allyCode=None):
    if allyCode == None:
        dict_bot_accounts = get_dict_bot_accounts()
        if not guild_id in dict_bot_accounts:
            return 1, "Ce serveur discord n'a pas de warbot", None

        bot_allyCode = dict_bot_accounts[guild_id]["allyCode"]

        # retry Auth is allowed if the account is a real bot account,
        # or if the played account if trying to re-auth after a pause
        retryAuth = (not dict_bot_accounts[guild_id]["lock_when_played"]) | dict_bot_accounts[guild_id]["force_auth"]

    else:
        bot_allyCode = allyCode
        retryAuth = 1
    goutils.log2("DBG", "connected account for "+str(guild_id)+" is "+str(bot_allyCode))

    #locking bot has priority. Cannot be overriden
    if islocked_bot_account(bot_allyCode):
        use_cache_data = True
        goutils.log2("WAR", "the connected account is being used... using cached data")
    else:
        if force_update == 1:
            use_cache_data = False
        elif force_update == -1:
            use_cache_data = True
        else: #force_update==0
            use_cache_data = ispriority_cache_bot_account(bot_allyCode)

    if allyCode==None and use_cache_data==0:
        # cancel the force_auth is an actual auth is required
        query = "UPDATE guild_bots SET force_auth=0 WHERE guild_id='"+guild_id+"'"
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

    return await get_guild_data_from_ac(bot_allyCode, use_cache_data, retryAuth=retryAuth)

##############################################
# AUTH functions
##############################################
async def send_ea_otc(txt_allyCode, otc):
    # RPC REQUEST for sending OTC
    url = "http://localhost:8000/auth_ea_otc"
    params = {"allyCode": txt_allyCode, "otc": otc}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "auth_ea_otc status="+str(resp.status))
                if resp.status==200:
                    resp_json = await(resp.json())
                else:
                    return 1, "Cannot send otc from RPC"

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer"
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer"
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer"

    if "err_code" in resp_json:
        return 1, resp_json["err_txt"]

    return 0, ""

#########################################
# Get full guild data, using the allyCode
async def get_guild_data_from_ac(txt_allyCode, use_cache_data, retryAuth=1):
    # RPC REQUEST for guild
    url = "http://localhost:8000/guild"
    params = {"allyCode": txt_allyCode, "use_cache_data":use_cache_data,
              "retryAuth": retryAuth}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "POST guild status="+str(resp.status))
                if resp.status==200:
                    if use_cache_data:
                        cache_json = await(resp.json())
                        cache_ts = cache_json["timestamp"]
                        guild_json = cache_json["data"]
                    else:
                        guild_json = await(resp.json())
                elif resp.status==401:
                    return 401, "authentication failed", None
                else:
                    return 1, "Cannot get guild data from RPC", None

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

    if "err_code" in guild_json:
        return 1, guild_json["err_txt"], None

    if "guild" in guild_json:
        dict_guild = guild_json["guild"]
    else:
        return 1, "Aucune info de guilde disponible pour "+txt_allyCode, None

    #Push some infos in DB
    await connect_mysql.update_guild(dict_guild)

    return 0, "", dict_guild

async def get_TBmapstats_data(guild_id, force_update, allyCode=None):
    if allyCode == None:
        dict_bot_accounts = get_dict_bot_accounts()
        if not guild_id in dict_bot_accounts:
            return 1, "Ce serveur discord n'a pas de warbot", None

        bot_allyCode = dict_bot_accounts[guild_id]["allyCode"]
    else:
        bot_allyCode = allyCode
    goutils.log2("DBG", "connected account for "+guild_id+" is "+bot_allyCode)

    #locking bot has priority. Cannot be overriden
    if islocked_bot_account(bot_allyCode):
        use_cache_data = True
        goutils.log2("WAR", "the bot account is being used... using cached data")
    else:
        if force_update == 1:
            use_cache_data = False
        elif force_update == -1:
            use_cache_data = True
        else: #force_update==0
            use_cache_data = ispriority_cache_bot_account(bot_allyCode)

    # RPC REQUEST for TBmapstats
    url = "http://localhost:8000/TBmapstats"
    params = {"allyCode": bot_allyCode, 
              "guild_id": guild_id,
              "use_cache_data":use_cache_data}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "POST TBmapstats status="+str(resp.status))
                if resp.status==200:
                    if use_cache_data:
                        cache_json = await(resp.json())
                        cache_ts = cache_json["timestamp"]
                        TBmapstats_json = cache_json["data"]
                    else:
                        TBmapstats_json = await(resp.json())
                elif resp.status==201:
                    TBmapstats_json = {}
                elif resp.status==204:
                    TBmapstats_json = {}
                else:
                    return 1, "Cannot get TBmapstats data from RPC", None

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

    if "err_code" in TBmapstats_json:
        return 1, TBmapstats["err_txt"], None

    if "currentStat" in TBmapstats_json:
        dict_TBmapstats = TBmapstats_json["currentStat"]
    else:
        dict_TBmapstats = {}

    return 0, "", dict_TBmapstats

async def get_event_data(dict_guild, event_types, force_update, allyCode=None):
    calling_func = inspect.stack()[1][3]
    guild_id = dict_guild["profile"]["id"]
    goutils.log2("DBG", "START ["+calling_func+"]get_event_data("+guild_id+", "\
                        +str(event_types)+", " \
                        +str(force_update)+", "+str(allyCode)+")")

    guild_id = dict_guild["profile"]["id"]

    if allyCode == None:
        dict_bot_accounts = get_dict_bot_accounts()
        if not guild_id in dict_bot_accounts:
            return 1, "Ce serveur discord n'a pas de warbot", None

        bot_allyCode = dict_bot_accounts[guild_id]["allyCode"]
    else:
        bot_allyCode = allyCode
    goutils.log2("DBG", "connected account for "+guild_id+" is "+bot_allyCode)

    #locking bot has priority. Cannot be overriden
    if islocked_bot_account(bot_allyCode):
        use_cache_data = True
        goutils.log2("WAR", "the bot account is being used... using cached data")
    else:
        if force_update == 1:
            use_cache_data = False
        elif force_update == -1:
            use_cache_data = True
        else: #force_update==0
            use_cache_data = ispriority_cache_bot_account(bot_allyCode)

    if event_types!=None and len(event_types) > 0:
        list_rpc_events = []

        #---------------
        #TB events
        list_channels=[]
        if ("territoryBattleStatus" in dict_guild) and ("TB" in event_types):
            for tb_status in dict_guild["territoryBattleStatus"]:
                if tb_status["selected"]:
                    tb_id = tb_status["instanceId"]
                    tb_channel = tb_status["channelId"]
                    list_channels.append(tb_channel)

                    for conflict_zone in tb_status["conflictZoneStatus"]:
                        if conflict_zone["zoneStatus"]["zoneState"] != "ZONELOCKED":
                            zone_channel = conflict_zone["zoneStatus"]["channelId"]
                            list_channels.append(zone_channel)

        if len(list_channels)>0:
            # RPC REQUEST for TB events
            url = "http://localhost:8000/events"
            params = {"allyCode": bot_allyCode, 
                      "guild_id": guild_id,
                      "eventType": "TB",
                      "list_channels": list_channels, 
                      "use_cache_data":use_cache_data}
            req_data = json.dumps(params)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data=req_data) as resp:
                        goutils.log2("DBG", "POST TB events status="+str(resp.status))
                        if resp.status==200:
                            if use_cache_data:
                                cache_json = await(resp.json())
                                cache_ts = cache_json["timestamp"]
                                resp_events = cache_json["data"]
                            else:
                                resp_events = await(resp.json())
                        else:
                            return 1, "Cannot get events data from RPC", None

            except asyncio.exceptions.TimeoutError as e:
                return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
            except aiohttp.client_exceptions.ServerDisconnectedError as e:
                return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
            except aiohttp.client_exceptions.ClientConnectorError as e:
                return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
        else:
            resp_events = None

        #add received events to the whole list
        if resp_events!=None:
            if "err_code" in resp_events:
                return 1, resp_events["err_txt"], None
            list_rpc_events += resp_events['event']

            #Store the new events in the DB
            await connect_mysql.store_tb_events(guild_id, tb_id, resp_events['event'])

        #---------------
        #TW events
        list_channels=[]
        if ("territoryWarStatus" in dict_guild) and ("TW" in event_types):
            for tw_status in dict_guild["territoryWarStatus"]:
                tw_id = tw_status["instanceId"]
                tw_guilds = []
                for guild_type in ["homeGuild", "awayGuild"]:
                    if guild_type in tw_status:
                        tw_guilds.append(tw_status[guild_type])

                for guild_status in tw_guilds:
                    for conflict_zone in guild_status["conflictStatus"]:
                        zone_channel = conflict_zone["zoneStatus"]["channelId"]
                        list_channels.append(zone_channel)

        if len(list_channels)>0:
            # RPC REQUEST for TW events
            url = "http://localhost:8000/events"
            params = {"allyCode": bot_allyCode, 
                      "eventType": "TW",
                      "guild_id": guild_id,
                      "list_channels": list_channels, 
                      "use_cache_data":use_cache_data}
            req_data = json.dumps(params)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data=req_data) as resp:
                        goutils.log2("DBG", "POST TW events status="+str(resp.status))
                        if resp.status==200:
                            if use_cache_data:
                                cache_json = await(resp.json())
                                cache_ts = cache_json["timestamp"]
                                resp_events = cache_json["data"]
                            else:
                                resp_events = await(resp.json())
                        else:
                            return 1, "Cannot get events data from RPC", None

            except asyncio.exceptions.TimeoutError as e:
                return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
            except aiohttp.client_exceptions.ServerDisconnectedError as e:
                return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
            except aiohttp.client_exceptions.ClientConnectorError as e:
                return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
        else:
            resp_events = None

        #add received events to the whole list
        if resp_events!=None:
            if "err_code" in resp_events:
                return 1, resp_events["err_txt"], None
            list_rpc_events += resp_events['event']

            #Store the new events in the DB
            await connect_mysql.store_tw_events(guild_id, tw_id, resp_events['event'])

        #---------------
        #CHAT events
        list_channels=[]
        if ("roomAvailable" in dict_guild) and ("CHAT" in event_types):
            for room in dict_guild["roomAvailable"]:
                if room["type"] == "GUILDDEFAULT":
                    room_channel = room["roomId"]
                    list_channels.append(room_channel)

        # RPC REQUEST for CHAT events
        url = "http://localhost:8000/events"
        params = {"allyCode": bot_allyCode, 
                  "eventType": "CHAT",
                  "guild_id": guild_id,
                  "list_channels": list_channels, 
                  "use_cache_data":use_cache_data}
        req_data = json.dumps(params)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=req_data) as resp:
                    goutils.log2("DBG", "POST CHAT events status="+str(resp.status))
                    if resp.status==200:
                        if use_cache_data:
                            cache_json = await(resp.json())
                            cache_ts = cache_json["timestamp"]
                            resp_events = cache_json["data"]
                        else:
                            resp_events = await(resp.json())
                    else:
                        return 1, "Cannot get events data from RPC", None

        except asyncio.exceptions.TimeoutError as e:
            return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
        except aiohttp.client_exceptions.ServerDisconnectedError as e:
            return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
        except aiohttp.client_exceptions.ClientConnectorError as e:
            return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

        #add received events to the whole list
        if resp_events!=None:
            if "err_code" in resp_events:
                return 1, resp_events["err_txt"], None
            list_rpc_events += resp_events['event']

        # GET latest ts for events
        query = "SELECT eventLatest_ts "
        query+= "FROM guild_bot_infos "
        query+= "WHERE guild_id='"+guild_id+"'"
        goutils.log2("DBG", query)
        eventLatest_ts = connect_mysql.get_value(query)

        goutils.log2("DBG", "start loop list_rpc_events")
        max_event_ts = 0
        dict_new_events = {}
        dict_event_counts = {"chat":0, "tb":0, "tw":0}
        chat_file_ids = []
        tb_file_ids = []
        tw_file_ids = []
        for event in list_rpc_events:
            channel_id = event["channelId"]
            event_ts = int(event["timestamp"])

            if channel_id.startswith("guild-{"):
                event_day_ts = int(event_ts/1000/86400)*86400*1000
                event_file_id = "GUILD_CHAT:"+str(event_day_ts)
                if not event_file_id in chat_file_ids:
                    chat_file_ids.append(event_file_id)
                event_type = "chat"

            elif "TB_EVENT" in channel_id:
                ret_re = re.search(".*\-\{.*\}\-(.*)\-.*", channel_id)
                event_file_id = ret_re.group(1)
                if not event_file_id in tb_file_ids:
                    tb_file_ids.append(event_file_id)
                event_type = "tb"

            elif "TERRITORY_WAR" in channel_id:
                ret_re = re.search(".*\-\{.*\}\-(.*)\-.*", channel_id)
                event_file_id = ret_re.group(1)
                if not event_file_id in tw_file_ids:
                    tw_file_ids.append(event_file_id)
                event_type = "tw"

            else:
                continue

            if eventLatest_ts==None or event_ts <= eventLatest_ts:
                continue

            if event_ts > max_event_ts:
                max_event_ts = event_ts

            dict_event_counts[event_type]+=1
            if not event_file_id in dict_new_events:
                dict_new_events[event_file_id] = []
            dict_new_events[event_file_id].append(event)

        goutils.log2("DBG", "end loop list_rpc_events")

        # SET latest ts for events
        if max_event_ts == 0 and eventLatest_ts!=None:
            max_event_ts = eventLatest_ts
        query = "UPDATE guild_bot_infos "
        query+= "SET eventLatest_ts="+str(max_event_ts)+" "
        query+= "WHERE guild_id='"+guild_id+"'"
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

        #if max(dict_event_counts.values()) > 0:
        goutils.log2("INFO", "New events: "+str(dict_event_counts))

        #PREPARE dict_events to return
        goutils.log2("DBG", "start loop dict_new_events")
        dict_events = {}

        #CHAT events
        for [event_type, file_ids] in [["CHAT", chat_file_ids],
                                       ["TB", tb_file_ids],
                                       ["TW", tw_file_ids]]:
            if event_type in event_types:
                for event_file_id in file_ids:
                    fevents = "EVENTS/"+guild_id+"_"+event_file_id+"_events.json"
                    await acquire_sem(fevents)

                    #Get previous events
                    if os.path.exists(fevents):
                        goutils.log2("DBG", "get previous events from "+fevents)
                        f = open(fevents, "r")
                        try:
                            file_events=json.load(f)
                        except:
                            goutils.log2("WAR", "error while reading "+fevents+" ... ignoring")
                            file_events={}
                        f.close()
                    else:
                        file_events={}

                    #Add new events
                    if event_file_id in dict_new_events:
                        for event in dict_new_events[event_file_id]:
                            event_id = event["id"]
                            file_events[event_id] = event

                        #And write file
                        f = open(fevents, "w")
                        f.write(json.dumps(file_events, indent=4))
                        f.close()
                    await release_sem(fevents)

                    #Add all events to dict_events
                    dict_events[event_file_id] = file_events

            await asyncio.sleep(0)

        goutils.log2("DBG", "end loop dict_new_events")

    else:
        dict_events = {}

    return 0, "", dict_events

async def get_extguild_data_from_ac(txt_allyCode, use_cache_data):
    ec, et, dict_player = await get_extplayer_data(txt_allyCode)
    if ec != 0:
        return 1, et, None

    if not "guildId" in dict_player:
        return 1, "ERR: ce joueur n'a pas de guilde", None

    guild_id = dict_player["guildId"]
    if guild_id == None or guild_id == "":
        return 1, "ERR: ce joueur n'a pas de guilde", None

    ec, et, dict_guild = await get_extguild_data_from_id(guild_id, use_cache_data)

    return ec, et, dict_guild

async def get_extguild_data_from_id(guild_id, use_cache_data):
    url = "http://localhost:8000/extguild"
    params = {"guild_id": guild_id}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "getextguild status="+str(resp.status))
                if resp.status==200:
                    guild_json = await(resp.json())
                else:
                    return 1, "Cannot player data from RPC", None

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

    if "err_code" in guild_json:
        return 1, guild_json["err_txt"], None

    dict_guild = guild_json["guild"]

    #Update data in DB
    await connect_mysql.update_extguild(dict_guild)

    return 0, "", dict_guild

async def get_extplayer_data(ac_or_id, load_roster=True):
    url = "http://localhost:8000/extplayer"
    params = {"player_id": ac_or_id, "noroster": not load_roster}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "extplayer status="+str(resp.status))
                if resp.status==200:
                    dict_player = await(resp.json())
                else:
                    return 1, "Cannot player data from RPC", None

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

    if "err_code" in dict_player:
        return 1, dict_player["err_txt"], None

    return 0, "", dict_player

async def get_player_initialdata(ac, use_cache_data=False):
    # RPC REQUEST for initial data
    url = "http://localhost:8000/initialdata"
    params = {"allyCode": ac,
              "use_cache_data":use_cache_data}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "initialdata status="+str(resp.status))
                if resp.status==200:
                    if use_cache_data:
                        cache_json = await(resp.json())
                        cache_ts = cache_json["timestamp"]
                        initialdata_player = cache_json["data"]
                    else:
                        initialdata_player = await(resp.json())
                else:
                    return 1, "Cannot get initialdata from RPC", None

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

    if "err_code" in initialdata_player:
        return 1, initialdata_player["err_txt"], None

    return 0, "", initialdata_player

async def get_bot_player_data(guild_id, use_cache_data):
    # Get alllyCode from guild ID
    bot_allyCode = connect_mysql.get_value("SELECT allyCode from guild_bots WHERE guild_id='"+guild_id+"'")
    if bot_allyCode == None:
        return 1, "Ce serveur discord n'a pas de warbot", None
    bot_allyCode = str(bot_allyCode)
    goutils.log2("DBG", "bot account for "+guild_id+" is "+bot_allyCode)

    # Manage cache
    use_cache_data = False
    if islocked_bot_account(bot_allyCode):
        use_cache_data = True
        goutils.log2("WAR", "the bot account is being used... using cached data")

    ec, et, d = await get_player_data(bot_allyCode, use_cache_data)
    return ec, et, d

async def get_player_data(txt_allyCode, use_cache_data):
    # prepare actual server request
    url = "http://localhost:8000/player"
    params = {"allyCode":txt_allyCode, "player_id": txt_allyCode, "use_cache_data": use_cache_data}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "player status="+str(resp.status))
                if resp.status==200:
                    if use_cache_data:
                        cache_json = await(resp.json())
                        cache_ts = cache_json["timestamp"]
                        dict_player = cache_json["data"]
                    else:
                        dict_player = await(resp.json())
                else:
                    return 1, "Cannot get player data from RPC", None

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

    if "err_code" in dict_player:
        return 1, dict_player["err_txt"], None

    return 0, "", dict_player

async def join_tw(guild_id):
    dict_bot_accounts = get_dict_bot_accounts()
    if not guild_id in dict_bot_accounts:
        return 1, "Ce serveur discord n'a pas de warbot", None

    err_code, err_txt, dict_guild = await get_guild_data_from_id(guild_id, -1)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en se connectant au bot"

    if "territoryWarStatus" in dict_guild:
        if "playerStatus" in dict_guild["territoryWarStatus"][0]:
            return 0, "Le bot a déjà rejoint la GT"
    else:
        return 0, "Aucune GT en cours"

    bot_allyCode = dict_bot_accounts[guild_id]["allyCode"]
    goutils.log2("DBG", "bot account for "+guild_id+" is "+bot_allyCode)

    # RPC REQUEST for joinTW
    url = "http://localhost:8000/joinTW"
    params = {"allyCode": bot_allyCode}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "POST joinTW status="+str(resp.status))
                if resp.status==200:
                    #normale case
                    rpc_response = await(resp.json())
                elif resp.status==202:
                    return 0, "Aucune GT en cours"
                else:
                    return 1, "Erreur en rejoignant la GT - code="+str(resp.status)

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer"
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer"
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer"

    if rpc_response!=None and "err_code" in rpc_response:
        err_txt = rpc_response["err_txt"]
        return 1, "Erreur en rejoignant la GT - "+err_txt

    return 0, "Le bot a rejoint la GT"

# OUT: dict_platoons = {} #key="GLS1-mid-2", value={key=perso, value=[player, player...]}
async def get_actual_tb_platoons(guild_id, force_update, allyCode=None):
    err_code, err_txt, dict_guild = await get_guild_data_from_id(guild_id, force_update, allyCode=allyCode)

    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return '', None, None

    err_code, err_txt, ret_data = await get_actual_tb_platoons_from_dict(dict_guild)
    return err_code, err_txt, ret_data

# OUT: dict_platoons = {} #key="GLS1-mid-2", value={key=perso, value=[player, player...]}
async def get_actual_tb_platoons_from_dict(dict_guild):
    dict_tb = godata.get("tb_definition.json")

    active_round = "" # "GLS4"
    dict_platoons = {} #key="GLS1-mid-2", value={key=perso, value=[player, player...]}
    list_open_territories = [] # [{"phase":4, "cmdMsg": "full pelotons", "cmdState":"FOCUSED"}, ...]

    guildName = dict_guild["profile"]["name"]

    dict_member_by_id = {}
    for member in dict_guild["member"]:
        dict_member_by_id[member["playerId"]] = member["playerName"]

    dict_unitsList = godata.get("unitsList_dict.json")

    if not "territoryBattleStatus" in dict_guild:
        goutils.log2("WAR", "["+guildName+"] no TB in progress")
        return 2, "["+guildName+"] no TB in progress", {}

    open_zone_count = 0
    for battleStatus in dict_guild["territoryBattleStatus"]:
        if battleStatus["selected"]:
            tb_defId = battleStatus["definitionId"]
            if not tb_defId in dict_tb:
                goutils.log2("WAR", "["+guildName+"] TB inconnue du bot")
                return 1, "["+guildName+"] TB inconnue du bot", {}

            tb_name = dict_tb[tb_defId]["shortname"]
            tb_id = battleStatus["instanceId"]
            active_round = tb_name + str(battleStatus["currentRound"])

            if active_round == 0:
                return 2, "TB in preparation phase", {}

            for zone in battleStatus["reconZoneStatus"]:
                recon_name = zone["zoneStatus"]["zoneId"]
                zone_name = "_".join(recon_name.split("_")[:-1])

                if zone["zoneStatus"]["zoneState"] == "ZONEOPEN":
                    ret_re = re.search(".*_phase0(\d)_conflict0(\d)", zone_name)
                    zone_phase = int(ret_re.group(1))
                    list_open_territories.append( {"phase": zone_phase,
                                                   "zone_name": dict_tb[zone_name]["name"]})
                    if "commandMessage" in zone["zoneStatus"]:
                        list_open_territories[-1]["cmdMsg"] = zone["zoneStatus"]["commandMessage"]
                    if "commandState" in zone["zoneStatus"]:
                        list_open_territories[-1]["cmdState"] = zone["zoneStatus"]["commandState"]
                    open_zone_count += 1

                if not "platoon" in zone:
                    continue

                for platoon in zone["platoon"]:
                    platoon_num = int(platoon["id"][-1])
                    if tb_name == "ROTE":
                        platoon_num_corrected = 7 - platoon_num
                    else:
                        platoon_num_corrected = platoon_num

                    platoon_num_txt = str(platoon_num_corrected)
                    platoon_name = dict_tb[zone_name]["name"] + "-" + platoon_num_txt
                    dict_platoons[platoon_name] = {}

                    for squad in platoon["squad"]:
                        for unit in squad["unit"]:
                            unit_id = unit["unitIdentifier"]
                            unit_defId = unit_id.split(":")[0]
                            unit_name = dict_unitsList[unit_defId]["name"]

                            if not unit_name in dict_platoons[platoon_name]:
                                dict_platoons[platoon_name][unit_name] = []

                            player_id = unit["memberId"]
                            if player_id != '':
                                if player_id in dict_member_by_id:
                                    player_name = dict_member_by_id[player_id]
                                else:
                                    # player with platoons but not in the guild: has left
                                    player_name = "Joueur Inconnu"
                                dict_platoons[platoon_name][unit_name].append(player_name)
                            else:
                                dict_platoons[platoon_name][unit_name].append('')

    if open_zone_count == 0:
        return 1, "No open territory", {}

    return 0, "", {"tb_id": tb_id,
                   "round": active_round, 
                   "platoons": dict_platoons,
                   "open_territories": list_open_territories}

async def get_guildLog_messages(guild_id, onlyLatest, force_update, allyCode=None, dict_guild=None, dict_events=None):

    query = "SELECT allyCode, chatChan_id, twlogChan_id, tblogChan_id, chatLatest_ts "\
            "FROM guild_bot_infos "\
            "LEFT JOIN guild_bots ON guild_bot_infos.guild_id=guild_bots.guild_id "\
            "WHERE guild_bot_infos.guild_id='"+guild_id+"'"
    goutils.log2("DBG", query)
    line = connect_mysql.get_line(query)
    if line == None:
        return 1, "INFO: no DB data for guild "+guild_id, None
    
    bot_allyCode = line[0]
    chatChan_id = line[1]
    twlogChan_id = line[2]
    tblogChan_id = line[3]

    if onlyLatest:
        chatLatest_ts = line[4]
    else:
        chatLatest_ts = 0

    if allyCode!=None:
        bot_allyCode = allyCode
    elif bot_allyCode == None:
        return 1, "ERR: no RPC bot for guild "+guild_id, None

    if dict_guild==None:
        err_code, err_txt, dict_guild = await get_guild_data_from_id(guild_id, force_update, allyCode=allyCode)
        if err_code != 0:
            goutils.log2("ERR", err_txt)
            return 1, err_txt, None

    # Get latest events only if the discord channel is defined
    if onlyLatest:
        eventTypes = []
        if chatChan_id != 0:
            eventTypes.append("CHAT")
        if twlogChan_id != 0:
            eventTypes.append("TW")
        if tblogChan_id != 0:
            eventTypes.append("TB")
    else:
        eventTypes = ["CHAT", "TW", "TB"]

    # Get data from RPC
    if dict_events==None:
        err_code, err_txt, dict_events = await get_event_data(dict_guild, eventTypes, force_update, allyCode=allyCode)
        if err_code != 0:
            goutils.log2("ERR", err_txt)
            return 1, err_txt, None

    list_chat_events, list_tw_logs, list_tb_logs = await get_logs_from_events(dict_events, guild_id, chatLatest_ts)

    list_all_logs = list_chat_events+list_tw_logs+list_tb_logs
    if len(list_all_logs)>0:
        list_all_logs = sorted(list_all_logs, key=lambda x:x[0])

        max_ts = list_all_logs[-1][0]
        query = "UPDATE guild_bot_infos SET chatLatest_ts="+str(max_ts)+" WHERE guild_id='"+guild_id+"'"
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

    return 0, "", {"CHAT": [chatChan_id, list_chat_events],
                   "TW":   [twlogChan_id, list_tw_logs],
                   "TB":   [tblogChan_id, list_tb_logs],
                   "rpc":  {"guild": dict_guild, "events": dict_events}}

async def get_logs_from_events(dict_events, guildId, chatLatest_ts, phases=[]):
    FRE_FR = godata.get('FRE_FR.json')
    dict_unitsList = godata.get("unitsList_dict.json")
    dict_tw = godata.dict_tw
    dict_tb = godata.get("tb_definition.json")

    list_chat_events = []
    list_tw_logs = []
    list_tb_logs = []
    dict_squads={}
    event_phase = ""
    phases_work = list(phases)
    for event_group_id in dict_events:
        event_group = dict_events[event_group_id]
        for event_id in event_group:
            event = event_group[event_id]
            event_ts = int(event["timestamp"])

            # Manage optional phases
            if phases != []:
                if event_ts >= phases_work[0][0]:
                    event_phase = phases_work[0][1]
                    phases_work = phases_work[1:]

            # Processing depends on event type
            if event_group_id.startswith("GUILD_CHAT"):
                if "message" in event:
                    author = event["authorName"]
                    message = event["message"]
                    if event_ts > chatLatest_ts:
                        list_chat_events.append([event_ts, "\N{SPEECH BALLOON} "+author+" : "+message])
                else:
                    for data in event["data"]:
                        activity = data["activity"]
                        txt_activity = FRE_FR[activity["key"]].replace("\\n", "\n")

                        #remove formating tags
                        while "[" in txt_activity:
                            pos_open = txt_activity.find("[")
                            pos_close = txt_activity.find("]")
                            txt_activity = txt_activity[:pos_open] + txt_activity[pos_close+1:]

                        #add parameters
                        if "param" in activity:
                            for i_param in range(len(activity["param"])):
                                tag_param="{"+str(i_param)+"}"
                                if tag_param in txt_activity:
                                    pos_open = txt_activity.find(tag_param)
                                    pos_close = pos_open + len(tag_param) - 1
                                    param = activity["param"][i_param]
                                    if "paramValue" in param:
                                        val_param = param["paramValue"][0]
                                    else:
                                        val_param = FRE_FR[param["key"]]
                                    txt_activity = txt_activity[:pos_open] + val_param + txt_activity[pos_close+1:]

                        if "UNIT_PROMOTED" in activity["key"]:
                            txt_activity = "\N{WHITE MEDIUM STAR} "+txt_activity
                        if "UNIT_ACTIVATED" in activity["key"]:
                            txt_activity = "\N{OPEN LOCK} "+txt_activity
                        if activity["key"].endswith("_JOIN") or "_PROMOTE_TO_" in activity["key"]:
                            txt_activity = "\N{SLIGHTLY SMILING FACE}"+txt_activity
                        if activity["key"].endswith("_LEFT") or activity["key"].endswith("_REMOVED") \
                           or activity["key"].endswith("_DEMOTE"):
                            txt_activity = "\N{SLIGHTLY FROWNING FACE}"+txt_activity

                        if event_ts > chatLatest_ts:
                            list_chat_events.append([event_ts, txt_activity])

            elif event_group_id.startswith("TERRITORY_WAR_EVENT"):
                author = event["authorName"]
                data=event["data"][0]
                activity=data["activity"]
                zone_id=activity["zoneData"]["zoneId"]
                zone_name = dict_tw[zone_id]
                if "DEPLOY" in activity["zoneData"]["activityLogMessage"]["key"]:
                    if activity["zoneData"]["instanceType"] == "ZONEINSTANCEHOME":
                        leader_id = activity["warSquad"]["squad"]["cell"][0]["unitDefId"].split(":")[0]
                        leader = dict_unitsList[leader_id]["name"]
                        activity_txt = "DEFENSE@"+zone_name+": "+author+" a posé une team "+leader

                        if event_ts > chatLatest_ts:
                            list_tw_logs.append([event_ts, activity_txt])
                else:
                    if activity["zoneData"]["guildId"] == guildId:
                        if "warSquad" in activity:
                            squad_id = activity["warSquad"]["squadId"]
                            if "squad" in activity["warSquad"]:
                                opponent=activity["warSquad"]["playerName"]
                                leader_id = activity["warSquad"]["squad"]["cell"][0]["unitDefId"].split(":")[0]
                                leader = dict_unitsList[leader_id]["name"]
                                leader_opponent = leader+"@"+opponent

                                count_dead=0
                                squad_size = len(activity["warSquad"]["squad"]["cell"])
                                for cell in activity["warSquad"]["squad"]["cell"]:
                                    if cell["unitState"]["healthPercent"] == "0":
                                        count_dead+=1

                                if not squad_id in dict_squads:
                                    dict_squads[squad_id]={}
                                    delta_dead = 0
                                else:
                                    delta_dead = count_dead - dict_squads[squad_id]["dead"]
                                    if delta_dead<0:
                                        # for som reason, sometimes the dead are not shwon and the squad is reduced
                                        # but it comes back afterwards
                                        # So , fix temporary wrong numbers
                                        count_dead = dict_squads[squad_id]["dead"]
                                        squad_size = squad_size - delta_dead

                                dict_squads[squad_id]["leader"] = leader_opponent
                                dict_squads[squad_id]["size"] = squad_size
                                dict_squads[squad_id]["dead"] = count_dead
                            else:
                                if squad_id in dict_squads:
                                    leader_opponent=dict_squads[squad_id]["leader"]
                                else:
                                    leader_opponent="UNKNOWN_LEADER"

                            if activity["warSquad"]["squadStatus"]=="SQUADAVAILABLE":
                                activity_txt = "DEFAITE@"+zone_name+" : "+author+" a perdu contre "+leader_opponent
                                if "squad" in activity["warSquad"]:
                                    count_dead=0
                                    squad_size = len(activity["warSquad"]["squad"]["cell"])
                                    remaining_tm=False
                                    for cell in activity["warSquad"]["squad"]["cell"]:
                                        if cell["unitState"]["healthPercent"] == "0":
                                            count_dead+=1
                                        if cell["unitState"]["turnPercent"] != "0":
                                            remaining_tm=True
                                    #activity_txt += " (reste "+str(squad_size-count_dead)+")"
                                    activity_txt += " ("+str(delta_dead)+" morts)"

                                    if count_dead==0 and remaining_tm:
                                        if "tm_ts" in dict_squads[squad_id]:
                                            #already a TM registered for this squad
                                            if dict_squads[squad_id]["tm_ts"] < event_ts:
                                                #this is a 2nd TM, not critical
                                                activity_txt = "\N{CROSS MARK}"+activity_txt+" (TM sur un TM)"
                                            else:
                                                #This is the first TM (should not happen if events are ordered by time)
                                                activity_txt = "\U0001F4A5"+activity_txt+" >>> TM !!!" #Collision
                                        else:
                                            #no TM registered yet, this is the first TM
                                            activity_txt = "\U0001F4A5"+activity_txt+" >>> TM !!!" #Collision

                                        #register TM timestamp
                                        dict_squads[squad_id]["tm_ts"] = event_ts
                                    else:
                                        activity_txt = "\N{CROSS MARK}"+activity_txt

                                else:
                                    activity_txt += " (abandon)"
                                    activity_txt = "\N{CROSS MARK}"+activity_txt


                            elif activity["warSquad"]["squadStatus"]=="SQUADDEFEATED":
                                if "squad" in activity["warSquad"]:
                                    activity_txt = "VICTOIRE@"+zone_name+": "+author+" a gagné contre "+leader_opponent
                                    activity_txt = "\N{WHITE HEAVY CHECK MARK}"+activity_txt

                            elif activity["warSquad"]["squadStatus"]=="SQUADLOCKED":
                                if "squad" in activity["warSquad"]:
                                    activity_txt = "DEBUT@"+zone_name+"   : "+author+" commence un combat contre "+leader_opponent
                                    activity_txt = "\N{White Right Pointing Backhand Index}"+activity_txt
                            else:
                                activity_txt = activity["warSquad"]["squadStatus"]

                        else:
                            scoreDelta = activity["zoneData"]["scoreDelta"]
                            scoretotal = activity["zoneData"]["scoreTotal"]
                            activity_txt = "Score en "+zone_name+" : "+scoretotal+" (+"+scoreDelta+")"
                            if int(scoreDelta)>100:
                                activity_txt += " > zone terminée \N{THUMBS UP SIGN}"

                        if event_ts > chatLatest_ts:
                            list_tw_logs.append([event_ts, activity_txt])

            elif event_group_id.startswith("TB_EVENT"):
                author = event["authorName"]
                data=event["data"][0]
                activity=data["activity"]
                if "CONFLICT_CONTRIBUTION" in activity["zoneData"]["activityLogMessage"]["key"]:
                    zone_data = activity["zoneData"]
                    zone_id = zone_data["zoneId"]
                    zone_name = dict_tb[zone_id]["name"]
                    phases_ok = zone_data["activityLogMessage"]["param"][2]["paramValue"][0]
                    phases_tot = zone_data["activityLogMessage"]["param"][3]["paramValue"][0]

                    if event_phase!="":
                        activity_txt = event_phase + " - "
                    else:
                        activity_txt = ""
                    activity_txt += "COMBAT: "+author+" "+str(phases_ok)+"/"+str(phases_tot)+" en "+zone_name
                    if event_ts > chatLatest_ts:
                        list_tb_logs.append([event_ts, activity_txt])

                elif "COVERT_COMPLETE" in activity["zoneData"]["activityLogMessage"]["key"]:
                    zone_data = activity["zoneData"]
                    zone_id = zone_data["zoneId"]
                    zone_name = dict_tb[zone_id]["name"]

                    activity_txt = "SPECIAL: "+author+" victoire en "+zone_name
                    if event_ts > chatLatest_ts:
                        list_tb_logs.append([event_ts, activity_txt])

                elif "CONFLICT_DEPLOY" in activity["zoneData"]["activityLogMessage"]["key"]:
                    zone_data = activity["zoneData"]
                    zone_id = zone_data["zoneId"]
                    if zone_id in dict_tb:
                        zone_name = dict_tb[zone_id]["name"]
                    else:
                        zone_name = zone_id
                    points = zone_data["activityLogMessage"]["param"][0]["paramValue"][0]

                    activity_txt = "DEPLOIEMENT: "+author+" déploie "+str(points)+" en "+zone_name

                    if event_ts > chatLatest_ts:
                        list_tb_logs.append([event_ts, activity_txt])

                elif "RECON_CONTRIBUTION" in activity["zoneData"]["activityLogMessage"]["key"]:
                    zone_data = activity["zoneData"]
                    zone_id = zone_data["zoneId"]
                    if zone_id in dict_tb:
                        zone_name = dict_tb[zone_id]["name"]
                    else:
                        zone_name = zone_id
                    points = zone_data["activityLogMessage"]["param"][0]["paramValue"][0]
                    done_platoons = zone_data["activityLogMessage"]["param"][2]["paramValue"][0]
                    total_platoons = zone_data["activityLogMessage"]["param"][3]["paramValue"][0]

                    activity_txt = "PELOTONS: "+author+" termine un peloton en "+zone_name+" ("+str(done_platoons)+"/"+str(total_platoons)+" remplis)"

                    if event_ts > chatLatest_ts:
                        list_tb_logs.append([event_ts, activity_txt])

    return list_chat_events, list_tw_logs, list_tb_logs

async def tag_tb_undeployed_players(guild_id, force_update, allyCode=None):
    dict_tb=godata.get("tb_definition.json")
    ec, et, tb_data = await get_tb_status(guild_id, "", force_update, allyCode=allyCode)
    if ec!=0:
        return 1, et, None

    dict_phase = tb_data["phase"]
    dict_strike_zones = tb_data["strike_zones"]
    dict_tb_players = tb_data["players"]
    list_open_zones = tb_data["open_zones"]
    dict_zones = tb_data["zones"]

    tb_round = dict_phase["round"]

    dict_deployment_types = {}
    for zone_name in list_open_zones:
        zone = dict_zones[zone_name]
        zone_deployment_type = dict_tb[zone_name]["type"]
        if zone["score"] < dict_tb[zone_name]["scores"][2]:
            zone_deployment_useful = True
        else:
            zone_deployment_useful = False
        if not zone_deployment_type in dict_deployment_types:
            dict_deployment_types[zone_deployment_type] = zone_deployment_useful
        elif dict_deployment_types[zone_deployment_type] == False:
            dict_deployment_types[zone_deployment_type] = zone_deployment_useful

    #count remaining players
    lines_player = []
    total_remainingMix = [0, 0] #total, officers only
    total_remainingChars = [0, 0] #total, officers only
    total_remainingShips = [0, 0] #total, officers only
    for playerName in dict_tb_players:
        await asyncio.sleep(0)

        player = dict_tb_players[playerName]
        player_score = player["rounds"][tb_round-1]["score"]
        player_isOff = (player["role"]>2)
        undeployed_player = False

        ret_print_player = ""

        if dict_tb[dict_phase["type"]]["shortname"] == "ROTE":
            if dict_deployment_types["mix"]:
                ratio_deploy_mix = player_score["deployedMix"] / player["mix_gp"]
                if ratio_deploy_mix < 0.99:
                    undeployed_player = True
                    ret_print_player += "{:,}".format(player_score["deployedMix"]) \
                                       +"/" + "{:,}".format(player["mix_gp"]) + " "

                    total_remainingMix[0] += player["mix_gp"]-player_score["deployedMix"]
                    if player_isOff:
                        total_remainingMix[1] += player["mix_gp"]-player_score["deployedMix"]
        else:
            if dict_deployment_types["ships"]:
                ratio_deploy_ships = player_score["deployedShips"] / player["ship_gp"]
                if ratio_deploy_ships < 0.99:
                    undeployed_player = True
                    ret_print_player += "Fleet: {:,}".format(player_score["deployedShips"]) \
                                       +"/" + "{:,}".format(player["ship_gp"]) + " "

                    total_remainingShips[0] += player["ship_gp"]-player_score["deployedShips"]
                    if player_isOff:
                        total_remainingShips[1] += player["ship_gp"]-player_score["deployedShips"]

            if dict_deployment_types["chars"]:
                ratio_deploy_chars = player_score["deployedChars"] / player["char_gp"]
                if ratio_deploy_chars < 0.99:
                    undeployed_player = True
                    ret_print_player += "Squad: {:,}".format(player_score["deployedChars"]) \
                                       +"/" + "{:,}".format(player["char_gp"]) + " "

                    total_remainingChars[0] += player["char_gp"]-player_score["deployedChars"]
                    if player_isOff:
                        total_remainingChars[1] += player["char_gp"]-player_score["deployedChars"]

        if undeployed_player:
            lines_player.append([playerName, ret_print_player])

        total = ""
        if total_remainingMix[0] > 0:
            total += "{:,}".format(total_remainingMix[0]) \
                    +" (officiers : " + "{:,}".format(total_remainingMix[1]) + ") "
        if total_remainingChars[0] > 0:
            total += "Chars: {:,}".format(total_remainingChars[0]) \
                    +" (officiers : " + "{:,}".format(total_remainingChars[1]) + ") "
        if total_remainingShips[0] > 0:
            total += "Ships: {:,}".format(total_remainingShips[0]) \
                    +" (officiers : " + "{:,}".format(total_remainingShips[1]) + ") "

    return 0, "", {"lines_player": lines_player, "round_endTime": dict_phase["round_endTime"], "total": total}

##############################################################
async def get_tb_status(guild_id, list_target_zone_steps, force_update,
                        compute_estimated_platoons=False,
                        targets_platoons=None, allyCode=None,
                        my_tb_round=None, my_list_open_zones=None,
                        dict_guild=None, dict_TBmapstats=None,
                        dict_all_events=None):
    global prev_dict_guild
    global prev_mapstats

    dict_tb = godata.get("tb_definition.json")

    ec, et, rpc_data = await get_guild_rpc_data(guild_id, ["TB"], 
                                  force_update, allyCode=allyCode,
                                  dict_guild=dict_guild, 
                                  dict_TBmapstats=dict_TBmapstats,
                                  dict_events=dict_all_events)
    if ec!=0:
        return 1, et, None

    if dict_guild==None:
        dict_guild=rpc_data[0]
    if dict_TBmapstats==None:
        mapstats=rpc_data[1]
    else:
        mapstats=dict_TBmapstats
    if dict_all_events==None:
        dict_all_events=rpc_data[2]
    guildName = dict_guild["profile"]["name"]
    guildId = dict_guild["profile"]["id"]

    #get guild members
    dict_members_by_id={}
    for member in dict_guild["member"]:
        dict_members_by_id[member["playerId"]] = member

    # Get TB id, basic infos and TB events
    tb_ongoing=False
    if "territoryBattleStatus" in dict_guild:
        for battleStatus in dict_guild["territoryBattleStatus"]:
            if battleStatus["selected"]:
                battle_id = battleStatus["instanceId"]
                tb_ongoing=True
                tb_type = battleStatus["definitionId"]
                goutils.log2("DBG", "Selected TB = "+battle_id+"/"+tb_type)
                if not tb_type in dict_tb:
                    return 1, "TB inconnue du bot", None

                if my_tb_round == None:
                    tb_round = battleStatus["currentRound"]
                    if tb_round==7:
                        goutils.log2("INFO", battleStatus["instanceId"])
                        goutils.log2("INFO", battleStatus["definitionId"])
                        goutils.log2("INFO", battleStatus["conflictZoneStatus"])
                        goutils.log2("INFO", battleStatus["currentRound"])
                else:
                    tb_round = my_tb_round

                if tb_round <= dict_tb[tb_type]["maxRound"]:
                    tb_ongoing=True

                tb_startTime = int(battleStatus["instanceId"].split(':')[1][1:])
                tb_round_endTime = tb_startTime + tb_round*dict_tb[tb_type]["phaseDuration"]
                tb_round_startTime = tb_round_endTime - dict_tb[tb_type]["phaseDuration"]

                if battle_id in dict_all_events:
                    dict_events=dict_all_events[battle_id]
                else:
                    dict_events={}
                break

    if not tb_ongoing:
        # Check if previous TB has ended properly, with associated actions
        latest_tb_end_ts = 0
        latest_tb_id = ""

        #Get the latest (=max) TB timestamp in known TB results
        if "territoryBattleResult" in dict_guild:
            for battleResult in dict_guild["territoryBattleResult"]:
                tb_end_ts = int(battleResult["endTime"])
                if tb_end_ts > latest_tb_end_ts:
                    latest_tb_end_ts = tb_end_ts
                    latest_tb_id = battleResult["instanceId"]

        tb_summary = None
        if latest_tb_end_ts > 0:
            if not manage_events.exists("tb_end", guild_id, latest_tb_id):
                # the closure is not done yet
                goutils.log2("INFO", "Close TB "+latest_tb_id+" for guild "+guild_id)

                #Copy gsheets
                try:
                    await connect_gsheets.close_tb_gwarstats(guild_id)
                except Exception as e:
                    goutils.log2("ERR", "["+guild_id+"]"+traceback.format_exc())
                    goutils.log2("ERR", "["+guild_id+"] cannot update gwarstats")

                #Save guild file
                if guild_id in prev_dict_guild:
                    guild_filename = "EVENTS/"+guildId+"_"+latest_tb_id+"_guild.json"
                    if guild_id in prev_dict_guild:
                        fjson = open(guild_filename, 'w')
                        fjson.write(json.dumps(prev_dict_guild[guild_id], indent=4))
                        fjson.close()

                    mapstats_filename = "EVENTS/"+guildId+"_"+latest_tb_id+"_mapstats.json"
                    if guild_id in prev_mapstats:
                        fjson = open(mapstats_filename, 'w')
                        fjson.write(json.dumps(prev_mapstats[guild_id], indent=4))
                        fjson.close()

                # Get TB summary stats
                err_code, csv, image = await go.print_tb_strike_stats(
                                                guild_id, [], [],
                                                allyCode=allyCode)

                # Get TB result (stars and bonus)
                if guild_id in prev_dict_guild \
                   and "territoryBattleStatus" in prev_dict_guild[guild_id]:
                    tbs = prev_dict_guild[guild_id]["territoryBattleStatus"][0]
                    stars = 0
                    bonus = {}
                    for z in tbs["conflictZoneStatus"]:
                        z_id = z["zoneStatus"]["zoneId"]
                        z_name = dict_tb[z_id]["fullname"]
                        z_score = int(z["zoneStatus"]["score"])
                        z_steps = dict_tb[z_id]["scores"]
                        my_stars = 0
                        if z_score >= z_steps[0]:
                            my_stars+=1
                        if z_score >= z_steps[1]:
                            my_stars+=1
                        if z_score >= z_steps[2]:
                            my_stars+=1

                        goutils.log2("DBG", z_id)
                        if z_id.endswith("bonus"):
                            #bonus planet
                            bonus[z_name] = min(my_stars, 2)
                            goutils.log2("DBG", bonus)
                            if my_stars==3:
                                stars+=1
                        else:
                            stars+=my_stars
                        goutils.log2("DBG", stars)
                    txt_results = str(stars)+emojis.star
                    goutils.log2("DBG", txt_results)
                    for zb in bonus:
                        if bonus[zb]>0:
                            txt_results += " / "+zb+bonus[zb]*emojis.bluecircle
                            goutils.log2("DBG", txt_results)
                else:
                    txt_results=""

                if err_code != 0:
                    goutils.log2("WAR", csv)
                    tb_summary = None
                else:
                    tb_summary=(csv, image, txt_results)

                manage_events.create_event("tb_end", guild_id, latest_tb_id)


        return 1, "No TB on-going", {"tb_summary": tb_summary}

    prev_dict_guild[guild_id] = dict_guild
    prev_mapstats[guild_id] = mapstats

    query = "SELECT name, char_gp, ship_gp, playerId, guildMemberlevel "\
            "FROM players WHERE guildName='"+guildName.replace("'", "''")+"'"
    goutils.log2("DBG", query)
    list_playername_gp_id_role = connect_mysql.get_table(query)

    dict_tb_players = {}
    dict_strike_zones = {}
    dict_covert_zones = {}
    dict_recon_zones = {}
    list_open_zones = []
    dict_zones = {}
    dict_phase = {"id": battle_id, 
                  "round": tb_round, 
                  "round_endTime": tb_round_endTime, 
                  "type": tb_type, 
                  "name": dict_tb[tb_type]["name"]}

    for playername_gp_id_role in list_playername_gp_id_role:
        player_name = playername_gp_id_role[0]
        player_char_gp = playername_gp_id_role[1]
        player_ship_gp = playername_gp_id_role[2]
        player_id = playername_gp_id_role[3]
        player_role = playername_gp_id_role[4]

        #test if player participates to TB - if joined guild after start of TB
        if not player_id in dict_members_by_id:
            #Player already left
            continue

        guildJoinTime = int(dict_members_by_id[player_id]["guildJoinTime"]) * 1000
        if guildJoinTime > tb_startTime:
            #Player joined after start of TB
            continue

        dict_tb_players[player_name] = {}
        dict_tb_players[player_name]["id"] = player_id
        dict_tb_players[player_name]["char_gp"] = player_char_gp
        dict_tb_players[player_name]["ship_gp"] = player_ship_gp
        dict_tb_players[player_name]["mix_gp"] = player_char_gp + player_ship_gp
        dict_tb_players[player_name]["role"] = player_role

        dict_tb_players[player_name]["rounds"] = []
        round_empty_score = {}

        for phase in range(dict_tb[tb_type]["maxRound"]):
            dict_tb_players[player_name]["rounds"].append({})
            dict_tb_players[player_name]["rounds"][phase]["score"] = {"deployedShips": 0,
                                                                      "deployedChars": 0,
                                                                      "deployedMix": 0,
                                                                      "deployed": 0,
                                                                      "Platoons": 0,
                                                                      "strikes": 0} 
            dict_tb_players[player_name]["rounds"][phase]["strikes"] = {} # "conflixtX_strikeY": "1/4"
            dict_tb_players[player_name]["rounds"][phase]["strike_attempts"] = 0
            dict_tb_players[player_name]["rounds"][phase]["strike_waves"] = 0
            dict_tb_players[player_name]["rounds"][phase]["coverts"] = {} # "conflixtX_covertY": True
            dict_tb_players[player_name]["rounds"][phase]["covert_attempts"] = 0

    completed_stars = 0 # stars on completed (closed) zones
    for zone in battleStatus["conflictZoneStatus"]:
        zone_stars = 0
        zone_name = zone["zoneStatus"]["zoneId"]
        zone_score = int(zone["zoneStatus"]["score"])
        if zone["zoneStatus"]["zoneState"] == "ZONEOPEN":
            list_open_zones.append(zone_name)
        elif zone["zoneStatus"]["zoneState"] == "ZONECOMPLETE":
            if zone_name.endswith("bonus"):
                # bonus zones have only 1 star, for the 3rd step
                if zone_score >= dict_tb[zone_name]["scores"][2]:
                    zone_stars += 1
            else:
                for star_score in dict_tb[zone_name]["scores"]:
                    if zone_score >= star_score:
                        zone_stars += 1
        else: #ZONELOCKED
            #zone not yet opened, no need to add it
            continue

        completed_stars += zone_stars
        dict_zones[zone_name] = {"score": zone_score, "completed_stars": zone_stars,
                                 "remainingPlatoonScore": 0}
    dict_phase["prev_stars"] = completed_stars

    #sort the dict to display zones in the same order as the game
    if my_list_open_zones == None:
        # sort by position by removing the "b" for bonus
        # then add 0.5 for bonus zone
        list_open_zones = sorted(list_open_zones, key=lambda x:dict_tb[tb_type]["zonePositions"][dict_tb[x]["name"].split("-")[1].rstrip("b")] + 0.5*dict_tb[x]["name"].split("-")[1].endswith("b"))
    else:
        list_open_zones = my_list_open_zones

    if len(list_open_zones)==0:
        return 1, "No TB on-going", None

    total_players_guild = len(dict_tb_players)
    dict_phase["TotalPlayers"] = total_players_guild
    for zone in battleStatus["strikeZoneStatus"]:
        if True: #zone["zoneStatus"]["zoneState"] == "ZONEOPEN":
            strike_name = zone["zoneStatus"]["zoneId"]
            strike_shortname = strike_name.split("_")[-1]

            zone_name = strike_name[:-len(strike_shortname)-1]

            done_strikes = zone["playersParticipated"]
            score = int(zone["zoneStatus"]["score"])
            not_done_strikes = total_players_guild - done_strikes
            remaining_fight = not_done_strikes * dict_tb[zone_name]["strikes"][strike_shortname][1]
            if not strike_name in dict_strike_zones:
                dict_strike_zones[strike_name] = {}

            dict_strike_zones[strike_name]["participation"] = done_strikes
            dict_strike_zones[strike_name]["score"] = score
            dict_strike_zones[strike_name]["maxPossibleStrikes"] = not_done_strikes
            dict_strike_zones[strike_name]["maxPossibleScore"] = remaining_fight
            dict_strike_zones[strike_name]["estimatedStrikes"] = 0
            dict_strike_zones[strike_name]["estimatedScore"] = 0
            dict_strike_zones[strike_name]["eventStrikes"] = 0
            dict_strike_zones[strike_name]["eventStrikeScore"] = 0

    for zone in battleStatus["covertZoneStatus"]:
        if zone["zoneStatus"]["zoneState"] in ("ZONEOPEN", "ZONECOMPLETE"):
            covert_name = zone["zoneStatus"]["zoneId"]
            covert_shortname = covert_name.split("_")[-1]

            zone_name = covert_name[:-len(covert_shortname)-1]

            done_coverts = zone["playersParticipated"]
            if not covert_name in dict_covert_zones:
                dict_covert_zones[covert_name] = {}

            dict_covert_zones[covert_name]["participation"] = done_coverts

    for zone in battleStatus["reconZoneStatus"]:
        if zone["zoneStatus"]["zoneState"] in ("ZONEOPEN", "ZONECOMPLETE"):
            recon_name = zone["zoneStatus"]["zoneId"]
            recon_shortname = recon_name.split("_")[-1]
            if "commandMessage" in zone["zoneStatus"]:
                cmdMsg = zone["zoneStatus"]["commandMessage"]
            else:
                cmdMsg = ""

            zone_name = recon_name[:-len(recon_shortname)-1]
            dict_zones[zone_name]["platoons"] = {"cmdMsg": cmdMsg, "filling": {}}

            for platoon in zone["platoon"]:
                platoon_id = platoon["id"]
                platoon_pos = int(platoon_id[-1])
                if zone_name.startswith('tb3'):
                    platoon_pos = 7-platoon_pos
                platoon_filled = 0
                for squad in platoon["squad"]:
                    for unit in squad["unit"]:
                        if "memberId" in unit and unit["memberId"]!="":
                            platoon_filled += 1

                dict_zones[zone_name]["platoons"]["filling"][platoon_pos] = platoon_filled

    for event_id in dict_events:
        event=dict_events[event_id]
        event_time = int(event["timestamp"])
        playerName = event["authorName"]
        if not playerName in dict_tb_players:
            #should not happen unless new player and until API resynchronizes
            continue

        event_round = int(tb_round + (event_time-tb_round_startTime)/dict_tb[tb_type]["phaseDuration"])

        for event_data in event["data"]:
            if "zoneData" in event_data["activity"]:
                zoneData_key = "zoneData"
            else:
                goutils.log2("ERR", "Event without zoneData: "+str(event))
                continue

            event_key = event_data["activity"][zoneData_key]["activityLogMessage"]["key"]
            if "CONFLICT_CONTRIBUTION" in event_key:
                # Strike partially or completely succesful
                zone_name = event_data["activity"][zoneData_key]["zoneId"]
                strike_name = event_data["activity"][zoneData_key]["sourceZoneId"]

                score = int(event_data["activity"][zoneData_key]["scoreDelta"])
                dict_tb_players[playerName]["rounds"][event_round-1]["score"]["strikes"] += score

                if event_round == tb_round:
                    # this dict is only valid for current round
                    #  as it is used for estimations
                    dict_strike_zones[strike_name]["eventStrikes"] += 1
                    dict_strike_zones[strike_name]["eventStrikeScore"] += score

                if "bonus" in strike_name:
                    strike_shortname="_".join(strike_name.split("_")[-3:])
                else:
                    strike_shortname="_".join(strike_name.split("_")[-2:])

                done_waves = event_data["activity"][zoneData_key]["activityLogMessage"]["param"][2]["paramValue"][0]
                total_waves = event_data["activity"][zoneData_key]["activityLogMessage"]["param"][3]["paramValue"][0]
                dict_tb_players[playerName]["rounds"][event_round-1]["strikes"][strike_shortname] = done_waves+"/"+total_waves

            elif "RECON_CONTRIBUTION" in event_key:
                #Complete a platoon
                zone_name = event_data["activity"][zoneData_key]["zoneId"]
                score = int(event_data["activity"][zoneData_key]["scoreDelta"])
                dict_tb_players[playerName]["rounds"][event_round-1]["score"]["Platoons"] += score

            elif "DEPLOY" in event_key:
                #Deployment (strike or platoon)
                zone_name = event_data["activity"][zoneData_key]["zoneId"]
                score = int(event_data["activity"][zoneData_key]["scoreDelta"])

                if dict_tb[zone_name]["type"] == "ships":
                    dict_tb_players[playerName]["rounds"][event_round-1]["score"]["deployedShips"] += score
                    dict_tb_players[playerName]["rounds"][event_round-1]["score"]["deployedMix"] += score
                elif dict_tb[zone_name]["type"] == "chars":
                    dict_tb_players[playerName]["rounds"][event_round-1]["score"]["deployedChars"] += score
                    dict_tb_players[playerName]["rounds"][event_round-1]["score"]["deployedMix"] += score
                else:
                    dict_tb_players[playerName]["rounds"][event_round-1]["score"]["deployedMix"] += score

            elif "COVERT_COMPLETE" in event_key:
                # Special mission
                zone_name = event_data["activity"][zoneData_key]["zoneId"]
                strike_name = event_data["activity"][zoneData_key]["sourceZoneId"]
                strike_shortname="_".join(strike_name.split("_")[-2:])
                dict_tb_players[playerName]["rounds"][event_round-1]["coverts"][strike_shortname] = True

    for mapstat in mapstats:
        if mapstat["mapStatId"].startswith("strike_attempt_round_"):
            mapstat_round = int(mapstat["mapStatId"][-1])
            if "playerStat" in mapstat:
                for playerstat in mapstat["playerStat"]:
                    member_id = playerstat["memberId"]
                    playerName = dict_members_by_id[member_id]["playerName"]
                    if not playerName in dict_tb_players:
                        continue

                    attempts = int(playerstat["score"])
                    dict_tb_players[playerName]["rounds"][mapstat_round-1]["strike_attempts"] = attempts

        elif mapstat["mapStatId"].startswith("strike_encounter_round_"):
            mapstat_round = int(mapstat["mapStatId"][-1])
            if "playerStat" in mapstat:
                for playerstat in mapstat["playerStat"]:
                    member_id = playerstat["memberId"]
                    playerName = dict_members_by_id[member_id]["playerName"]
                    if not playerName in dict_tb_players:
                        continue

                    waves = int(playerstat["score"])
                    dict_tb_players[playerName]["rounds"][mapstat_round-1]["strike_waves"] = waves

        elif mapstat["mapStatId"].startswith("covert_attempt_round_"):
            mapstat_round = int(mapstat["mapStatId"][-1])
            if "playerStat" in mapstat:
                for playerstat in mapstat["playerStat"]:
                    member_id = playerstat["memberId"]
                    playerName = dict_members_by_id[member_id]["playerName"]
                    if not playerName in dict_tb_players:
                        continue

                    attempts = int(playerstat["score"])
                    dict_tb_players[playerName]["rounds"][mapstat_round-1]["covert_attempts"] = attempts

        elif mapstat["mapStatId"].startswith("power_round_"):
            mapstat_round = int(mapstat["mapStatId"][-1])
            if "playerStat" in mapstat:
                for playerstat in mapstat["playerStat"]:
                    member_id = playerstat["memberId"]
                    if not member_id in dict_members_by_id:
                        #player has left the guild
                        continue
                    playerName = dict_members_by_id[member_id]["playerName"]
                    if not playerName in dict_tb_players:
                        #should not happen unless new player and until API resynchronizes
                        continue

                    score = int(playerstat["score"])
                    dict_tb_players[playerName]["rounds"][mapstat_round-1]["score"]["deployed"] = score
                    if dict_tb_players[playerName]["rounds"][mapstat_round-1]["score"]["deployed"] != dict_tb_players[playerName]["rounds"][mapstat_round-1]["score"]["deployedMix"]:
                        goutils.log2("WAR", "Event deployment does not match total deployment for "+playerName)
                        goutils.log2("WAR", "("+str(dict_tb_players[playerName]["rounds"][mapstat_round-1]["score"]["deployedMix"])+" vs "+str(dict_tb_players[playerName]["rounds"][mapstat_round-1]["score"]["deployed"])+")")

                        #Estimate ships / chars score from total score and current ship / char
                        not_deployed_ships = dict_tb_players[playerName]["ship_gp"] - dict_tb_players[playerName]["rounds"][mapstat_round-1]["score"]["deployedShips"]
                        not_deployed_chars = dict_tb_players[playerName]["char_gp"] - dict_tb_players[playerName]["rounds"][mapstat_round-1]["score"]["deployedChars"]
                        bonus_deployment = dict_tb_players[playerName]["rounds"][mapstat_round-1]["score"]["deployed"] - dict_tb_players[playerName]["rounds"][mapstat_round-1]["score"]["deployedMix"]

                        if (not_deployed_ships + not_deployed_chars) == 0:
                            #if everything is deployed, no need for bonus
                            bonus_ships = 0
                            bonus_chars = 0
                        else:
                            bonus_ships = int(bonus_deployment * not_deployed_ships / (not_deployed_ships + not_deployed_chars))
                            bonus_chars = int(bonus_deployment * not_deployed_chars / (not_deployed_ships + not_deployed_chars))
                        dict_tb_players[playerName]["rounds"][mapstat_round-1]["score"]["deployedShips"] += bonus_ships
                        dict_tb_players[playerName]["rounds"][mapstat_round-1]["score"]["deployedChars"] += bonus_chars
                        dict_tb_players[playerName]["rounds"][mapstat_round-1]["score"]["deployedMix"] = dict_tb_players[playerName]["rounds"][mapstat_round-1]["score"]["deployed"]

    dict_remaining_deploy = {"ships": {"all": 0, "officers": 0},
                             "chars": {"all": 0, "officers": 0},
                             "mix":   {"all": 0, "officers": 0}}
    if tb_ongoing:
        for playerName in dict_tb_players:
            playerData = dict_tb_players[playerName]
            player_remain_deploy_ships = playerData["ship_gp"] - playerData["rounds"][tb_round-1]["score"]["deployedShips"]
            player_remain_deploy_chars = playerData["char_gp"] - playerData["rounds"][tb_round-1]["score"]["deployedChars"]
            player_remain_deploy_mix   = playerData["mix_gp"]  - playerData["rounds"][tb_round-1]["score"]["deployedMix"]

            dict_remaining_deploy["ships"]["all"] += player_remain_deploy_ships
            dict_remaining_deploy["chars"]["all"] += player_remain_deploy_chars
            dict_remaining_deploy["mix"]["all"] += player_remain_deploy_mix

            if playerData["role"] > 2:
                #This member is an officier of the guild
                dict_remaining_deploy["ships"]["officers"] += player_remain_deploy_ships
                dict_remaining_deploy["chars"]["officers"] += player_remain_deploy_chars
                dict_remaining_deploy["mix"]["officers"] += player_remain_deploy_mix
            
    dict_phase["availableShipDeploy"] = dict_remaining_deploy["ships"]["all"]
    dict_phase["availableCharDeploy"] = dict_remaining_deploy["chars"]["all"]
    dict_phase["availableMixDeploy"] = dict_remaining_deploy["mix"]["all"]

    list_deployment_types = []
    for zone_name in list_open_zones:
        zone_deployment_type = dict_tb[zone_name]["type"]
        if not zone_deployment_type in list_deployment_types:
            list_deployment_types.append(zone_deployment_type)
            dict_phase["deployment_types"] = list_deployment_types

    #count remaining players
    lines_player = []

    #Loop on all TB players to assess the list of who has finished playing
    finished_players = {"ships": [], "chars": [], "mix": []}
    if tb_ongoing:
        for playerName in dict_tb_players:

            #depending on the TB, playing in ships/chars, or in mix,
            # detect if the player has finished playing, by checking if all is deployed
            # If the player has deployed < 99%, he is considered not finished 
            # and count as +1 in the remaining players to fight

            if "ships" in list_deployment_types:
                ratio_deploy_ships = dict_tb_players[playerName]["rounds"][tb_round-1]["score"]["deployedShips"] / dict_tb_players[playerName]["ship_gp"]
                if ratio_deploy_ships >= 0.99:
                    finished_players["ships"].append(playerName)

            if "chars" in list_deployment_types:
                ratio_deploy_chars = dict_tb_players[playerName]["rounds"][tb_round-1]["score"]["deployedChars"] / dict_tb_players[playerName]["char_gp"]
                if ratio_deploy_chars >= 0.99:
                    finished_players["chars"].append(playerName)

            if "mix" in list_deployment_types:
                ratio_deploy_mix = dict_tb_players[playerName]["rounds"][tb_round-1]["score"]["deployedMix"] / dict_tb_players[playerName]["mix_gp"]
                if ratio_deploy_mix >= 0.99:
                    finished_players["mix"].append(playerName)

    # Loop by zone then by strike in the zone
    for zone in list_open_zones:
        # Get total strikes for the phase
        total_strikes = 0
        for z in list_open_zones:
            for s in dict_tb[z]["strikes"]:
                total_strikes+=1

        # Compute stats for the zone
        for strike in dict_tb[zone]["strikes"]:
            if zone.endswith("bonus"):
                strike_shortname = "conflict0"+zone[-7]+"_bonus_"+strike
            else:
                strike_shortname = "conflict0"+zone[-1]+"_"+strike
            strike_name = zone+"_"+strike

            # First loop to get the amount of tries in this fight
            tryCount = 0
            for playerName in dict_tb_players:
                if len(dict_tb_players[playerName]["rounds"][tb_round-1]["strikes"]) == total_strikes:
                    # the player has fought all possible fights
                    # This helps counting a fight with no wave when the player does them all
                    tryCount += 1
                else:
                    if strike_shortname in dict_tb_players[playerName]["rounds"][tb_round-1]["strikes"]:
                        tryCount += 1
                    else:
                        # if the player has finished, it is considered as a participation to the fight
                        # possibly of 0
                        if   dict_tb[zone]["type"]=="ships" and playerName in finished_players["ships"]:
                            tryCount += 1
                        elif dict_tb[zone]["type"]=="chars" and playerName in finished_players["chars"]:
                            tryCount += 1
                        elif dict_tb[zone]["type"]=="mix"   and playerName in finished_players["mix"]:
                            tryCount += 1

            #Previous idea: actual participation
            # not counting fights with 0 wave
            #strike_fights = dict_strike_zones[strike_name]["participation"]

            #Previous idea: not finished players
            # not good when player fight and do not deploy > overestimates the possible score
            #strike_fights = len(finished_players[dict_tb[zone]["type"]])

            #Current idea: all players who have fought OR who has finished
            # if the player has done all fights, then fights with 0 ar in the count
            strike_fights = tryCount

            strike_score = dict_strike_zones[strike_name]["eventStrikeScore"]
            if strike_fights > 0:
                strike_average_score = strike_score / strike_fights
            else:
                strike_average_score = 0

            # A try is when there strike is recorded for the player, or if the player has finished playing this phase
            #Loop on all TB players to get estimated score
            for playerName in dict_tb_players:
                #If the player has not fought for this strike, his potential score
                # is estimated by giving him the average done score from other players
                # which is (total score for the strike) / (players who participated on this strike + players who has finished and not participated)
                # If no player has tried this strike, then estimated score is 0
                # The estimated score is used only of the player has not finished playing
                if not strike_shortname in dict_tb_players[playerName]["rounds"][tb_round-1]["strikes"]:

                    if   dict_tb[zone]["type"]=="ships" and not playerName in finished_players["ships"]:
                        dict_strike_zones[strike_name]["estimatedStrikes"] += 1
                        dict_strike_zones[strike_name]["estimatedScore"] += strike_average_score

                    elif dict_tb[zone]["type"]=="chars" and not playerName in finished_players["chars"]:
                        dict_strike_zones[strike_name]["estimatedStrikes"] += 1
                        dict_strike_zones[strike_name]["estimatedScore"] += strike_average_score

                    elif dict_tb[zone]["type"]=="mix"   and not playerName in finished_players["mix"]:
                        dict_strike_zones[strike_name]["estimatedStrikes"] += 1
                        dict_strike_zones[strike_name]["estimatedScore"] += strike_average_score


    dict_phase["shipPlayers"] = len(dict_tb_players) - len(finished_players["ships"])
    dict_phase["charPlayers"] = len(dict_tb_players) - len(finished_players["chars"])
    dict_phase["mixPlayers"] = len(dict_tb_players) - len(finished_players["mix"])

    # Get platoon remaining scores
    if compute_estimated_platoons:
        err_code, err_txt, ret_data = await get_actual_tb_platoons_from_dict(dict_guild)
        tbs_round = ret_data["round"]
        dict_platoons_done = ret_data["platoons"]

        tb_name = tbs_round[:-1]

        # check for done platoons, unless they are hard given:
        if targets_platoons==None:
            err_code, err_txt, ret_dict = connect_mysql.get_tb_platoon_allocations(guild_id, tbs_round)

            if ret_dict == None:
                dict_platoons_allocation = {}
            else:
                dict_platoons_allocation = ret_dict["dict_platoons_allocation"]

            for zone_name in list_open_zones:
                recon_zoneId = zone_name+"_recon01"
                zone_shortname = dict_tb[zone_name]["name"]


                # Fill done platoons with allocations
                zone_done_count=0
                zone_target_count=0
                for platoon in dict_platoons_done:
                    if platoon[:-2] == zone_shortname:
                        current_platoon_count=0
                        future_platoon_count=0
                        for unit in dict_platoons_done[platoon]:
                            empty_players = dict_platoons_done[platoon][unit].count('')
                            current_platoon_count+=len(dict_platoons_done[platoon][unit]) - empty_players
                            future_platoon_count+=len(dict_platoons_done[platoon][unit]) - empty_players

                            if platoon in dict_platoons_allocation:
                                dict_platoon_allocations = dict_platoons_allocation[platoon]
                                if unit in dict_platoon_allocations:
                                    #print(platoon, unit, dict_platoons_done[platoon][unit], dict_platoon_allocations[unit])
                                    for i in range(empty_players):
                                        target_players = dict_platoon_allocations[unit]
                                        for player in target_players:
                                            if not player in dict_platoons_done[platoon][unit]:
                                                dict_platoons_done[platoon][unit].remove('')
                                                dict_platoons_done[platoon][unit].append(player)
                                                dict_platoon_allocations[unit].remove(player)
                                                future_platoon_count += 1
                                                break

                                    #print(platoon, unit, dict_platoons_done[platoon][unit], dict_platoon_allocations[unit])
                        #print(current_platoon_count, future_platoon_count)
                        zone_done_count += (current_platoon_count==15)
                        zone_target_count += (future_platoon_count==15)

                                    
                # Compute remaining platoons score
                remaining_score = 0
                if zone_target_count > zone_done_count:
                    platoon_score = dict_tb[zone_name]["platoonScore"]
                    remaining_score = (zone_target_count-zone_done_count) * platoon_score

                dict_zones[zone_name]["remainingPlatoonScore"] = remaining_score

        else:
            for target_platoon in targets_platoons.split("/"):
                if not ":" in target_platoon:
                    return 1, target_platoon + " --> chaque objectif de peloton doit être de la forme <zone>:<pelotons> (ex: MS:4)", None

                # get and check target zone name
                target_zone_shortname = target_platoon.split(":")[0]

                zone_found = False
                list_zone_names = []
                for zone_name in list_open_zones:
                    list_zone_names.append(dict_tb[zone_name]["name"])
                    if dict_tb[zone_name]["name"].endswith("-"+target_zone_shortname):
                        target_zone_name = dict_tb[zone_name]["name"]
                        zone_found = True
                        break

                if not zone_found:
                    return 1, target_platoon+" --> zone inconnue: " + target_zone_shortname + " " + str(list_zone_names), None

                #define platoon target score
                zone_done_count = 0
                for platoon in dict_platoons_done:
                    if platoon.startswith(target_zone_name):
                        platoon_done_count=0
                        for char_name in dict_platoons_done[platoon]:
                            for player_name in dict_platoons_done[platoon][char_name]:
                                if player_name != '':
                                    platoon_done_count += 1
                        if platoon_done_count==15:
                            zone_done_count+=1

                zone_target_count = int(target_platoon.split(":")[1])
                remaining_score = 0
                if zone_target_count > zone_done_count:
                    platoon_score = dict_tb[zone_name]["platoonScore"]
                    remaining_score = (zone_target_count-zone_done_count) * platoon_score

                dict_zones[zone_name]["remainingPlatoonScore"] = remaining_score

    #####################################################
    # Start filling the graph with scores
    # 1- actual score
    # 2- estimated fights
    #####################################################

    #compute zone stats apart for deployments
    for zone_name in list_open_zones:
        current_score = dict_zones[zone_name]["score"]

        #ALTERNATE solution to get score whe TB is over
        # not ready  as sometimes good, sometimes wrong
        #zone_summary = [ms for ms in mapstats if ms["mapStatId"]=="summary_zone_"+zone_name][0]
        #print(zone_summary)
        #if "playerStat" in zone_summary:
        #    l = zone_summary["playerStat"]
        #    #print(l)
        #    k = [int(x["score"]) for x in l]
        #    if "phase04_conflict01" in zone_name:
        #        print(k)
        #    current_score = sum(k)
        #else:
        #    current_score = 0
        #print(zone_name, current_score)

        estimated_strike_score = 0
        estimated_strike_fights = 0
        max_strike_score = 0
        cur_strike_score = 0
        cur_strike_fights = {}
        cur_covert_fights = {}
        for strike in dict_tb[zone_name]["strikes"]:
            strike_name = zone_name + "_" + strike
            estimated_strike_fights += dict_strike_zones[strike_name]["estimatedStrikes"]
            estimated_strike_score += dict_strike_zones[strike_name]["estimatedScore"]
            max_strike_score += dict_strike_zones[strike_name]["maxPossibleScore"]

            cur_strike_fights[strike] = dict_strike_zones[strike_name]["participation"]
            cur_strike_score += dict_strike_zones[strike_name]["eventStrikeScore"]

        for covert in dict_tb[zone_name]["coverts"]:
            covert_name = zone_name + "_" + covert
            cur_covert_fights[covert] = dict_covert_zones[covert_name]["participation"]

        dict_zones[zone_name]["strikeScore"] = cur_strike_score
        dict_zones[zone_name]["strikeFights"] = cur_strike_fights
        dict_zones[zone_name]["covertFights"] = cur_covert_fights
        dict_zones[zone_name]["estimatedStrikeFights"] = estimated_strike_fights
        dict_zones[zone_name]["estimatedStrikeScore"] = estimated_strike_score
        dict_zones[zone_name]["maxStrikeScore"] = max_strike_score
        dict_zones[zone_name]["deployment"] = 0

        star_for_score=0
        if zone_name.endswith("bonus"):
            # bonus zones have only 1 star, for the 3rd step
            if current_score >= dict_tb[zone_name]["scores"][2]:
                star_for_score += 1
        else:
            for star_score in dict_tb[zone_name]["scores"]:
                if current_score >= star_score:
                    star_for_score += 1

        dict_zones[zone_name]["stars"] = star_for_score

    # 3- fill with deployment points
    tb_type = dict_phase["type"]

    if list_target_zone_steps == "":
        #original warstats logic: closest star, then next closest star...
        #split the zones by type
        dict_zones_by_type = {"ships": [], "chars": [], "mix": []}
        for zone_name in list_open_zones:
            zone_type = dict_tb[zone_name]["type"]
            dict_zones_by_type[zone_type].append(zone_name)

        full_zones = 0
        for zone_type in ["ships", "chars", "mix"]:
            while (dict_remaining_deploy[zone_type]["all"] > 0) and (full_zones < len(dict_zones_by_type[zone_type])):
                #find closest star
                min_dist_star = -1
                min_zone_name = ""
                full_zones = 0
                for zone_name in dict_zones_by_type[zone_type]:
                    cur_score = dict_zones[zone_name]["score"]
                    cur_score += dict_zones[zone_name]["estimatedStrikeScore"]
                    if compute_estimated_platoons:
                        cur_score += dict_zones[zone_name]["remainingPlatoonScore"]
                    cur_score += dict_zones[zone_name]["deployment"]

                    if cur_score >= dict_tb[zone_name]["scores"][2]:
                        full_zones += 1
                        continue

                    for star_score in dict_tb[zone_name]["scores"]:
                        if cur_score < star_score:
                            dist_star = star_score - cur_score
                            if min_dist_star == -1 or dist_star < min_dist_star:
                                min_dist_star = dist_star
                                min_zone_name = zone_name
                            break

                #deploy in the found zone
                if min_zone_name != "":
                    deploy_value = min(min_dist_star, dict_remaining_deploy[zone_type]["all"])
                    dict_zones[min_zone_name]["deployment"] += deploy_value
                    dict_remaining_deploy[zone_type]["all"] -= deploy_value

    else:
        list_target_zone_steps = list_target_zone_steps.strip()
        while '  ' in list_target_zone_steps:
            list_target_zone_steps = list_target_zone_steps.replace('  ', ' ')

        already_computed_zones = []
        for target_zone_stars in list_target_zone_steps.split(" "):
            if not ":" in target_zone_stars:
                return 1, target_zone_stars + " --> chaque objectif de zone doit être de la forme <zone>:<étoiles> (ex: top:3)", None

            # get and check target zone name
            target_zone_shortname = target_zone_stars.split(":")[0]

            zone_found = False
            list_zone_names = []
            for zone_name in list_open_zones:
                list_zone_names.append(dict_tb[zone_name]["name"])
                if dict_tb[zone_name]["name"].endswith("-"+target_zone_shortname):
                    target_zone_name = dict_tb[zone_name]["name"]
                    zone_found = True
                    break

            if not zone_found:
                return 1, target_zone_stars+" --> zone inconnue: " + target_zone_shortname + " " + str(list_zone_names), None

            #get and check target zone stars
            target_stars_txt = target_zone_stars.split(":")[1]
            if not target_stars_txt.isnumeric():
                return 1, target_zone_stars+" --> le nombre d'étoiles doit être... un nombre", None
            target_stars = int(target_stars_txt)
            if target_stars <0 or target_stars > 3:
                return 1, target_zone_stars + " --> la cible d'étoiles doit être entre 0 et 3", None

            #Check if the zone is not used twice in the option
            if target_zone_name in already_computed_zones:
                return 1, target_zone_stars+" --> zone utilisée 2 fois : " + target_zone_name, None
            already_computed_zones.append(target_zone_name)


            current_score = dict_zones[zone_name]["score"]
            estimated_strike_score = dict_zones[zone_name]["estimatedStrikeScore"]
            if compute_estimated_platoons:
                estimated_platoon_score = dict_zones[zone_name]["remainingPlatoonScore"]
            else:
                estimated_platoon_score = 0
            score_with_estimations = current_score + estimated_strike_score + estimated_platoon_score

            #Targeting 0 stars is targeting score for 1 star, or almost
            if target_stars == 0:
                target_star_score = dict_tb[zone_name]["scores"][0] - 10
            else:
                target_star_score = dict_tb[zone_name]["scores"][target_stars-1]

            if dict_tb[zone_name]["type"] == "ships":
                deploy_consumption = max(0, min(dict_remaining_deploy["ships"]["all"], target_star_score - score_with_estimations))
                dict_remaining_deploy["ships"]["all"] -= deploy_consumption
            elif dict_tb[zone_name]["type"] == "chars":
                deploy_consumption = max(0, min(dict_remaining_deploy["chars"]["all"], target_star_score - score_with_estimations))
                dict_remaining_deploy["chars"]["all"] -= deploy_consumption
            else:
                deploy_consumption = max(0, min(dict_remaining_deploy["mix"]["all"], target_star_score - score_with_estimations))
                dict_remaining_deploy["mix"]["all"] -= deploy_consumption

            dict_zones[zone_name]["deployment"] = deploy_consumption

    dict_phase["remainingShipDeploy"] = dict_remaining_deploy["ships"]["all"]
    dict_phase["remainingCharDeploy"] = dict_remaining_deploy["chars"]["all"]
    dict_phase["remainingMixDeploy"] = dict_remaining_deploy["mix"]["all"]

    #Compute estimated stars per zone
    for zone_name in list_open_zones:
        estimated_score = dict_zones[zone_name]["score"]
        estimated_score += dict_zones[zone_name]["estimatedStrikeScore"]
        if compute_estimated_platoons:
            estimated_score += dict_zones[zone_name]["remainingPlatoonScore"]
        estimated_score += dict_zones[zone_name]["deployment"]

        star_for_score=0
        if zone_name.endswith("bonus"):
            # bonus zones have only 1 star, for the 3rd step
            if estimated_score >= dict_tb[zone_name]["scores"][2]:
                star_for_score += 1
        else:
            for star_score in dict_tb[zone_name]["scores"]:
                if estimated_score >= star_score:
                    star_for_score += 1
        dict_zones[zone_name]["estimatedStars"] = star_for_score

    #Update DB
    await connect_mysql.update_tb_round(guild_id, 
                                        dict_phase["id"], 
                                        dict_phase["round"], 
                                        dict_phase,
                                        dict_zones, 
                                        dict_strike_zones,
                                        list_open_zones, 
                                        dict_tb_players)

    return 0, "", {"phase": dict_phase, 
                   "strike_zones": dict_strike_zones, 
                   "players": dict_tb_players, 
                   "open_zones": list_open_zones,
                   "zones": dict_zones,
                   "guild": dict_guild,
                   "mapstats": mapstats,
                   "events": dict_all_events},

##########################################"
# OUT: dict_territory_scores = {"tb3_mixed_phase03_conflit02": 24500000, ...}
# OUT: tb_active_round = 3
##########################################"
async def get_tb_guild_scores(guild_id, dict_phase, dict_strike_zones, list_open_zones, dict_zones):
    dict_tb = godata.get("tb_definition.json")

    active_round = dict_tb[dict_phase["type"]]["shortname"]+str(dict_phase["round"])

    dict_territory_scores = {}
    for zone in list_open_zones:
        zone_name_tab = dict_tb[zone]["name"].split("-")
        zone_name = zone_name_tab[0][:-1]
        zone_name += "-P"
        zone_name += zone_name_tab[0][-1]
        zone_name += "-"
        zone_name += zone_name_tab[1]
        zone_score = dict_zones[zone]["score"]
        dict_territory_scores[zone] = zone_score

    return dict_territory_scores, active_round

########################################
# get_tw_opponent_leader
# get an allyCode of the opponent TW guild
########################################
async def get_tw_opponent_leader(guild_id, allyCode=None):
    if allyCode == None:
        ec, et, dict_guild = await get_guild_data_from_id(guild_id, -1)
    else:
        ec, et, dict_guild = await get_guild_data_from_id(guild_id, 1, allyCode)

    if ec!=0:
        return 1, et, None

    tw_ongoing=False
    opp_guild_id = None
    if "territoryWarStatus" in dict_guild:
        for battleStatus in dict_guild["territoryWarStatus"]:
            tw_ongoing = True
            if "awayGuild" in battleStatus:
                opp_guild_id = battleStatus["awayGuild"]["profile"]["id"]

    if not tw_ongoing:
        return 1, "Pas de GT en cours", None
    if opp_guild_id == None:
        return 1, "Adversaire de GT pas encore connu", None

    ec, et, dict_guild = await get_extguild_data_from_id(opp_guild_id, False)
    if ec != 0:
        return ec, et, None

    for member in dict_guild["member"]:
        if member["memberLevel"] == 4:
            leader_id = member["playerId"]

    ec, et, dict_player = await get_extplayer_data(leader_id)
    if ec != 0:
        return ec, et, None

    leader_ac = dict_player["allyCode"]

    return 0, "", str(leader_ac)

########################################
# get_tw_status
# get status of territories in attack and def
# {
#   "tw_id": None / "TERRITORY_WAR_EVENT_C:01681236000000", 
#   "tw_round": tw_round, 
#   "homeGuild": {"list_defenses": [["T1", "Karcot", ["GENERALSKYWALGER", "ARCTROOPER", ...], <is_beaten>, <fights>],
#                                ["T1", "JeanLuc"...
#                 "list_territories": [["T1", <size>, <filled>, <victories>, <fails>, <commandMsg>, <status>], ...]
#                }, 
#   "awayGuild": {"list_defenses": ...,
#                 "list_territories": ...
#                }, 
#   "opp_guildName": name, 
#   "opp_guildId": id
# }
########################################
async def get_tw_status(guild_id, force_update, with_attacks=False, allyCode=None, 
                        manage_tw_end=False, dict_guild=None):
    global prev_dict_guild
    global prev_mapstats

    dict_tw=godata.dict_tw

    if with_attacks or allyCode!=None:
        #events are gathered when necessary (with_attacks) 
        # or just when command launched from connected user 
        # (as this kind of user may benefit fr go.logs command)
        event_types="TW"
    else:
        event_types=""

    if with_attacks or dict_guild==None:
        ec, et, ret_data = await get_guild_rpc_data(guild_id, event_types, force_update, 
                                                allyCode=allyCode,
                                                dict_guild=dict_guild)
        if ec!=0:
            goutils.log2("ERR", et)
            return {"tw_id": None, "rpc": None}

        dict_guild = ret_data[0]
        dict_events = ret_data[2]
    else:
        dict_events=None

    guildId = dict_guild["profile"]["id"]

    dict_members_by_id={}
    for member in dict_guild["member"]:
        dict_members_by_id[member["playerId"]] = member["playerName"]

    tw_id=None
    tw_round=None
    if "territoryWarStatus" in dict_guild:
        for battleStatus in dict_guild["territoryWarStatus"]:
            # the TW is considered on-going during
            # - registration phase (round=-1, awayGuild is not defined)
            # - defense phase (round=0, awayGuild is defined)
            # - attack phase (round=1)
            # - analyse phase (round=2)
            tw_id = battleStatus["instanceId"]
            cur_tw = battleStatus
            if "awayGuild" in battleStatus:
                tw_round = battleStatus["currentRound"]
            else:
                tw_round = -1

    goutils.log2("DBG", str(tw_id)+", "+str(tw_round))
    if tw_id == None:
        return {"tw_id": None, "rpc": {"guild": dict_guild, "events": dict_events}}

    tw_summary = None
    if tw_round == 2 and manage_tw_end:
        # Check if previous TW has ended properly, with associated actions

        if not manage_events.exists("tw_end", guild_id, tw_id):
            # the closure is not done yet
            goutils.log2("INFO", "Close TW "+tw_id+" for guild "+guild_id)

            #Save guild file
            if guild_id in prev_dict_guild:
                guild_filename = "EVENTS/"+guildId+"_"+tw_id+"_guild.json"
                fjson = open(guild_filename, 'w')
                fjson.write(json.dumps(prev_dict_guild[guild_id], indent=4))
                fjson.close()

            #Read TW events in case they were not gathered before
            if len(dict_events)==0:
                events_filename = "EVENTS/"+guildId+"_"+tw_id+"_events.json"
                dict_events = {"TERRITORY_WAR_EVENT": json.load(open(events_filename))}

            #TW end summary table
            err_code, tw_summary = await go.print_tw_summary(guild_id, allyCode=allyCode,
                                                             dict_guild=dict_guild,
                                                             dict_events=dict_events)

            # Display best teams in GT channel
            # TODO

            manage_events.create_event("tw_end", guild_id, tw_id)

    prev_dict_guild[guild_id] = dict_guild

    if tw_round >= 0:
        opp_guildName = battleStatus["awayGuild"]["profile"]["name"]
        opp_guildId = battleStatus["awayGuild"]["profile"]["id"]
    else:
        opp_guildName = "unknown"
        opp_guildId = 0

    list_defenses = {}
    list_territories = {}

    capa_list = godata.get("unit_capa_list.json")
    for guild in ["homeGuild", "awayGuild"]:
        list_defenses[guild] = []
        list_territories[guild] = []
        if guild in cur_tw:
            for zone in cur_tw[guild]["conflictStatus"]:
                zone_id = zone["zoneStatus"]["zoneId"]
                zone_shortname = dict_tw[zone_id]
                victories=0
                fails=0
                if "warSquad" in zone:
                    for squad in zone["warSquad"]:
                        squad_id = squad["squadId"]
                        player_name = squad["playerName"]
                        list_chars = []
                        for c in squad["squad"]["cell"]:
                            unit_id = c["unitDefId"].split(":")[0]
                            my_unit = {"unitDefId": c["unitDefId"],
                                       "unitId": unit_id,
                                       "level": c["unitBattleStat"]["level"],
                                       "gear": c["unitBattleStat"]["tier"],
                                       "relic": c["unitBattleStat"]["unitRelicTier"],
                                       "turnMeter": c["unitState"]["turnPercent"],
                                       "health": c["unitState"]["healthPercent"]}
                            if "skill" in c["unitBattleStat"]:
                                my_unit["skill"] = c["unitBattleStat"]["skill"]
                            if "purchaseAbilityId" in c["unitBattleStat"]:
                                my_unit["purchaseAbilityId"] = c["unitBattleStat"]["purchaseAbilityId"]

                            list_chars.append(my_unit)

                        is_beaten = (squad["squadStatus"]=="SQUADDEFEATED")
                        fights = squad["successfulDefends"]
                        team_gp = squad["power"]
                        list_defenses[guild].append([zone_shortname, player_name, list_chars, is_beaten, fights, team_gp, squad_id])

                        if is_beaten:
                            victories+=1
                            fails+=(fights-1)
                        else:
                            fails+=fights

                zone_size = zone["squadCapacity"]
                filled = zone["squadCount"] + victories
                if "zoneState" in zone["zoneStatus"]:
                    zoneState = zone["zoneStatus"]["zoneState"]
                else:
                    zoneState = None
                if "commandMessage" in zone["zoneStatus"]:
                    commandMsg = zone["zoneStatus"]["commandMessage"]
                else:
                    commandMsg = None
                if "commandState" in zone["zoneStatus"]:
                    commandState = zone["zoneStatus"]["commandState"]
                else:
                    commandState = None
                list_territories[guild].append([zone_shortname, zone_size, filled, victories, fails, commandMsg, commandState, zoneState])

    #Detect who has attacked what
    list_attacks = []
    if with_attacks:
        for event_group_id in dict_events:
            event_group = dict_events[event_group_id]
            for event_id in event_group:
                event = event_group[event_id]
                event_ts = int(event["timestamp"])
                if event_group_id.startswith("TERRITORY_WAR_EVENT"):
                    author_id = event["authorId"]
                    attacker_name = event["authorName"]
                    data=event["data"][0]
                    activity=data["activity"]
                    if "DEPLOY" in activity["zoneData"]["activityLogMessage"]["key"]:
                        # deployment
                        pass
                    else:
                        if activity["zoneData"]["guildId"] == guildId:
                            if "warSquad" in activity:
                                squad_id = activity["warSquad"]["squadId"]
                                if activity["warSquad"]["squadStatus"] in ("SQUADLOCKED", "SQUADDEFEATED"):
                                    if "squad" in activity["warSquad"]:
                                        zone_id = activity["zoneData"]["zoneId"]
                                        zone_shortname = dict_tw[zone_id]
                                        defenser_name = activity["warSquad"]["playerName"]
                                        team_gp = activity["warSquad"]["power"]
                                        squad = activity["warSquad"]["squad"]
                                        list_chars = []
                                        for c in squad["cell"]:
                                            unit_id = c["unitDefId"].split(":")[0]
                                            my_unit = {"unitDefId": c["unitDefId"],
                                                       "unitId": unit_id,
                                                       "level": c["unitBattleStat"]["level"],
                                                       "gear": c["unitBattleStat"]["tier"],
                                                       "relic": c["unitBattleStat"]["unitRelicTier"],
                                                       "turnMeter": c["unitState"]["turnPercent"],
                                                       "health": c["unitState"]["healthPercent"]}
                                            if "skill" in c["unitBattleStat"]:
                                                my_unit["skill"] = c["unitBattleStat"]["skill"]
                                            if "purchaseAbilityId" in c["unitBattleStat"]:
                                                my_unit["purchaseAbilityId"] = c["unitBattleStat"]["purchaseAbilityId"]

                                            list_chars.append(my_unit)

                                        list_attacks.append({"zone": zone_shortname, 
                                                             "attacker": attacker_name, 
                                                             "defenser": defenser_name,
                                                             "list_chars": list_chars, 
                                                             "gp": team_gp,
                                                             "squad_id": squad_id})

    ret_dict =  {"tw_id": tw_id, \
                 "tw_round": tw_round, \
                 "homeGuild": {"list_defenses": list_defenses["homeGuild"], \
                               "list_territories": list_territories["homeGuild"]}, \
                 "awayGuild": {"list_defenses": list_defenses["awayGuild"], \
                               "list_territories": list_territories["awayGuild"], \
                               "list_attacks": list_attacks}, \
                 "opp_guildName": opp_guildName, \
                 "opp_guildId": opp_guildId, \
                 "tw_summary": tw_summary, \
                 "rpc": {"guild": dict_guild, "events": dict_events}}

    return ret_dict

async def get_tw_active_players(guild_id, force_update, allyCode=None):
    ec, et, dict_guild = await get_guild_data_from_id(guild_id, force_update, allyCode=allyCode)
    if ec!=0:
        return 1, et, None

    if not "territoryWarStatus" in dict_guild:
        return 0, "", {"active": [], "inactive": [], "round": None,
                       "rpc": {"guild": dict_guild}}

    dict_members={}
    list_active_players = []
    for member in dict_guild["member"]:
        dict_members[member["playerId"]] = member["playerName"]
    for member in dict_guild["territoryWarStatus"][0]["optedInMember"]:
        if member["memberId"] in dict_members:
            list_active_players.append(dict_members[member["memberId"]])

    list_inactive_players = []
    for member in dict_guild["member"]:
        if not member["playerName"] in list_active_players:
            list_inactive_players.append(member["playerName"])

    # the TW is considered on-going during
    # - registration phase (round=-1, awayGuild is not defined)
    # - defense phase (round=0, awayGuild is defined)
    # - attack phase (round=1)
    # - analyse phase (round=2)
    battleStatus = dict_guild["territoryWarStatus"][0]
    if "awayGuild" in battleStatus:
        tw_round = battleStatus["currentRound"]
    else:
        tw_round = -1

    return 0, "", {"active": list_active_players, "inactive": list_inactive_players,
                   "round": tw_round, "rpc": {"guild": dict_guild}}

async def deploy_tb(txt_allyCode, zone_id, requested_defIds):

    # transform list of defId (LOBOT) into unit id (dkh65_TR-CxrT5jk547)
    err_code, err_txt, dict_player = await get_player_data(txt_allyCode, False)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en récupérant les infos joueur de "+txt_allyCode

    player_name = dict_player["name"]
    player_id = dict_player["playerId"]

    list_unit_ids = []
    for unit in dict_player["rosterUnit"]:
        full_defId = unit["definitionId"]
        defId = full_defId.split(":")[0]
        if defId in requested_defIds:
            list_unit_ids.append(unit["id"])

    if len(list_unit_ids) == 0:
        return 1, "Plus rien à déployer"

    # Remove already deployed units
    err_code, err_txt, dict_guild = await get_guild_data_from_ac(txt_allyCode, False)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en récupérant les infos guilde de "+txt_allyCode

    dict_zone_states = {}
    prev_score = 0
    for tb in dict_guild["territoryBattleStatus"]:
        if tb["selected"]:
            tb_id = tb["instanceId"]
            for zone in tb["conflictZoneStatus"]:
                zone_status = zone["zoneStatus"]
                if "commandState" in zone["zoneStatus"]:
                    dict_zone_states[zone_status["zoneId"]] = zone_status["commandState"]
            if "playerStatus" in tb:
                if "unitStatus" in tb["playerStatus"]:
                    for unit in tb["playerStatus"]["unitStatus"]:
                        if unit["unitId"] in list_unit_ids:
                            #print("Déjà déployé : "+unit["unitId"])
                            list_unit_ids.remove(unit["unitId"])
            for mapstat in tb["currentStat"]:
                if mapstat["mapStatId"] == "summary":
                    for player_stat in mapstat["playerStat"]:
                        if player_stat["memberId"] == player_id:
                            prev_score = int(player_stat["score"])

        if zone_id in dict_zone_states:
            knownCommandState = dict_zone_states[zone_id]
            zone_param = tb_id+":"+zone_id+":"+knownCommandState
        else:
            zone_param = tb_id+":"+zone_id

    if len(list_unit_ids) == 0:
        return 1, "Plus rien à déployer"

    # Launch the actual command
    process_cmd_list = ["/home/pi/GuionBot/warstats/deploy_tb.sh", txt_allyCode, zone_param]+list_unit_ids
    goutils.log2("DBG", process_cmd_list)
    process = subprocess.run(process_cmd_list)
    goutils.log2("DBG", "deploy_tb code="+str(process.returncode))
    if process.returncode!=0:
        if process.returncode == 202:
            return 1, "Erreur en déployant en TB - pas de TB en cours"
        elif process.returncode == 203:
            return 1, "Erreur en déployant en TB - rien à déployer"
        elif process.returncode == 44:
            return 1, "Erreur en déployant en TB - incohérence des ordres de zone (ouvert / bloqué), essayez avec le territoire ouvert"
        elif process.returncode != 0:
            return 1, "Erreur en déployant en TB - code="+str(process.returncode)

    return 0, "Déploiement OK de "+str(len(list_unit_ids))+" unités en " + zone_id

async def deploy_tw(guild_id, txt_allyCode, zone_id, requested_defIds):
    dict_unitsList = godata.get("unitsList_dict.json")

    # get player roster
    err_code, err_txt, dict_player = await get_player_data(txt_allyCode, False)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en se connectant au compte "+txt_allyCode

    player_name = dict_player["name"]
    dict_roster = {}
    for unit in dict_player["rosterUnit"]:
        full_defId = unit["definitionId"]
        defId = full_defId.split(":")[0]
        dict_roster[defId] = unit

    # get guild tw info, including player deployed units
    err_code, err_txt, dict_guild = await get_guild_data_from_ac(txt_allyCode, False)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en récupérant les infos guilde de "+txt_allyCode

    if not "territoryWarStatus" in dict_guild:
        return 1, "Pas de GT en cours"

    dict_zone_states = {}
    tw = dict_guild["territoryWarStatus"][0]
    tw_id = tw["instanceId"]
    for zone in tw["homeGuild"]["conflictStatus"]:
        zone_status = zone["zoneStatus"]
        if "commandState" in zone_status:
            dict_zone_states[zone_status["zoneId"]] = zone_status["commandState"]

    if zone_id in dict_zone_states:
        knownCommandState = dict_zone_states[zone_id]
        zone_param = tw_id+":"+zone_id+":"+knownCommandState
    else:
        zone_param = tw_id+":"+zone_id

    if not "playerStatus" in tw:
        return 1, "ERR: " + player_name+" n'a pas rejoint la GT"

    list_used_units = []
    if "unitStatus" in tw["playerStatus"]:
        for unit in tw["playerStatus"]["unitStatus"]:
            list_used_units.append(unit["unitId"])

    list_unit_ids = []
    team_combatType = None
    for defId in requested_defIds:
        unit_id = dict_roster[defId]["id"]
        unit_level = str(dict_roster[defId]["currentLevel"])
        unit_tier = str(dict_roster[defId]["currentTier"])
        if unit_id in list_used_units:
            return 1, "ERR: " + player_name + " a déjà déployé " + defId

        list_unit_ids.append(defId+":"+unit_id+":"+unit_level+":"+unit_tier)
        unit_combatType = dict_unitsList[defId]["combatType"]
        if team_combatType==None or team_combatType==unit_combatType:
            team_combatType=unit_combatType
        else:
            goutils.log2("ERR", "Mixing chars and ships")
            return 1, "ERR: ne pas mélanger persos et vaisseaux svp"
            
    if team_combatType == 1 and len(list_unit_ids) != 5:
        goutils.log2("ERR", "Need 5 units but found "+str(list_unit_ids))
        return 1, "ERR: il faut exactement 5 persos"

    if team_combatType == 2 and len(list_unit_ids) < 4:
        goutils.log2("ERR", "Need at least 4 units but found "+str(list_unit_ids))
        return 1, "ERR: il faut au moins 4 vaisseaux"

    if team_combatType==2:
        #Fleet
        process_cmd_list = ["/home/pi/GuionBot/warstats/deploy_tw.sh", txt_allyCode, zone_param, '-s']+list_unit_ids
        goutils.log2("DBG", process_cmd_list)
        process = subprocess.run(process_cmd_list)
    else:
        #Ground
        process_cmd_list = ["/home/pi/GuionBot/warstats/deploy_tw.sh", txt_allyCode, zone_param]+list_unit_ids
        goutils.log2("DBG", process_cmd_list)
        process = subprocess.run(process_cmd_list)

    goutils.log2("DBG", "deploy_tw code="+str(process.returncode))
    if process.returncode==202:
        return 1, "Erreur en déployant en GT - pas de GT en cours"
    elif process.returncode==203:
        return 1, "Erreur en déployant en GT - "+player_name+" n'a pas tous les persos demandés"
    elif process.returncode==204:
        return 1, "Erreur en déployant en GT - au moins un perso est déjà déployé"
    elif process.returncode==205:
        return 1, "Erreur en déployant en GT - "+player_name+" n'a pas rejoint la GT"
    elif process.returncode==94:
        return 1, "Erreur en déployant en GT - version du client incompatible (contacter l'admin)"
    elif process.returncode!=0:
        return 1, "Erreur en déployant en GT - code="+str(process.returncode)

    return 0, player_name+" a posé "+str(requested_defIds)+" en " + zone_id

async def platoon_tb(txt_allyCode, zone_id, platoon_id, requested_defIds):
    # get player roster
    # use CACHE data as unit IDs do not change often
    err_code, err_txt, dict_player = await get_player_data(txt_allyCode, False)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en se connectant au compte "+txt_allyCode
    
    player_name = dict_player["name"]
    dict_roster = {}
    for unit in dict_player["rosterUnit"]:
        full_defId = unit["definitionId"]
        defId = full_defId.split(":")[0]
        dict_roster[defId] = unit

    # get guild tb info, including player deployed units
    # use CACHE data to speed up the command, with the risk that another player deploys
    # the same unit at the same place
    err_code, err_txt, dict_guild = await get_guild_data_from_ac(txt_allyCode, False)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en récupérant les infos guilde de "+txt_allyCode

    if not "territoryBattleStatus" in dict_guild:
        return 1, "Pas de BT en cours"

    for tb in dict_guild["territoryBattleStatus"]:
        if tb["selected"]:
            break
    tb_id = tb["instanceId"]

    # add the squad id to the unit id
    # look for the required unitDefId, in the right zone
    # then take first occurrence not taken, and allocate the squad
    list_id_squad = []
    list_unit_id = []
    deployed_defIds = []
    remaining_defIds = requested_defIds.copy()
    for reconZone in tb["reconZoneStatus"]:
        if reconZone["zoneStatus"]["zoneId"] != zone_id:
            continue
        for platoon in reconZone["platoon"]:
            if platoon["id"] != platoon_id:
                continue
            for squad in platoon["squad"]:
                squad_id = squad["id"]
                for unit in squad["unit"]:
                    if unit["memberId"] != "":
                        # unit already taken by a player
                        continue
                    unit_defId = unit["unitIdentifier"].split(':')[0]
                    if unit_defId in remaining_defIds:
                        unit_id = dict_roster[unit_defId]["id"]
                        #list_id_squad.append(unit_id+":"+squad_id) #this format for the command-line RPC
                        list_id_squad.append([unit_id, squad_id]) # this format for the POST RPC
                        list_unit_id.append(unit_id)
                        deployed_defIds.append(unit_defId)
                        remaining_defIds.remove(unit_defId)

    if "playerStatus" in tb:
        if "unitStatus" in tb["playerStatus"]:
            for unit in tb["playerStatus"]["unitStatus"]:
                if unit["unitId"] in list_unit_id:
                    return 1, "ERR: "+unit["unitId"]+" est déjà déployé par "+txt_allyCode

    if len(list_id_squad) == 0:
        return 1, "ERR: plus rien à déployer"


    # RPC REQUEST for platoonsTB
    url = "http://localhost:8000/platoonsTB"
    params = {"allyCode": txt_allyCode,
              "tb_id": tb_id,
              "zone_id": zone_id,
              "platoon_id": platoon_id,
              "units": list_id_squad}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "POST platoonsTB status="+str(resp.status))
                if resp.status==200:
                    #normale case
                    resp_json = await(resp.json())
                elif resp.status==201:
                    return 1, "ERR: rien à déployer"
                else:
                    return 1, "Erreur en posant les pelotons de BT - code="+str(resp.status)

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer"
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer"
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer"

    if resp_json!=None and "err_code" in resp_json:
        return 1, resp_json["err_txt"], None

    return 0, player_name+" a posé "+str(deployed_defIds)+" en " + zone_id

async def update_K1_players():
    url = "http://localhost:8000/leaderboard"
    params = {"ga_rank": "KYBER1"}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "leaderboard status="+str(resp.status))
                if resp.status==200:
                    resp_json = await(resp.json())
                else:
                    return 1, "Cannot get leaderboard data from RPC", None

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

    if resp_json!=None and "err_code" in resp_json:
        return 1, resp_json["err_txt"], None

    leaderboard_json = resp_json
    #Loop through plalers and add/update them
    for player in leaderboard_json["player"]:
        await go.load_player(player["id"], 1, False)


####################################################
# IN: guild ID
# OUT: {"player name": [gnd attacks, gnd victories, ship attacks, ship victories, defense], ...}
####################################################
async def get_tw_participation(guild_id, force_update, allyCode=None):
    dict_tw = godata.dict_tw

    err_code, err_txt, dict_guild = await get_guild_data_from_id(guild_id, force_update, allyCode=allyCode)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, err_txt, None

    err_code, err_txt, dict_events = await get_event_data(dict_guild, ["TW"], force_update, allyCode=allyCode)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, err_txt, None

    dict_participation = {} # {"player name": [gnd attacks, gnd victories, ship attacks, ship victories, defense], ...}

    for tw_id in dict_events:
        tw_events = dict_events[tw_id]
        for event_id in tw_events:
            event = tw_events[event_id]
            player_name = event["authorName"]

            data = event["data"][0]
            if data["activity"]["zoneData"]["guildId"] != guild_id:
                continue

            if not player_name in dict_participation:
                dict_participation[player_name] = [0, 0, 0, 0, 0]

            if data["activityType"]=="TERRITORY_WAR_CONFLICT_ACTIVITY":
                activity=data["activity"]
                zone_id=activity["zoneData"]["zoneId"]
                zone_name = dict_tw[zone_id]
                if "DEPLOY" in activity["zoneData"]["activityLogMessage"]["key"]:
                    if activity["zoneData"]["instanceType"] == "ZONEINSTANCEHOME":
                        dict_participation[player_name][4] += 1
                else:
                    zone_id = activity["zoneData"]["zoneId"]
                    if dict_tw[zone_id][0] == "F":
                        is_ship_fight = True
                    else:
                        is_ship_fight = False

                    if "warSquad" in activity:
                        if activity["warSquad"]["squadStatus"]=="SQUADDEFEATED":
                            if "squad" in activity["warSquad"]:
                                if is_ship_fight:
                                    dict_participation[player_name][3] += 1
                                else:
                                    dict_participation[player_name][1] += 1
                        elif activity["warSquad"]["squadStatus"]=="SQUADLOCKED":
                            if "squad" in activity["warSquad"]:
                                if is_ship_fight:
                                    dict_participation[player_name][2] += 1
                                else:
                                    dict_participation[player_name][0] += 1


    return 0, "", dict_participation

########################################
# get_raid_status
# get status of current raid
# OUT: raid_id: None / "kraytdragon"
# OUT: expire_time: 169123456000
# OUT: list_inactive_players: ["Karcot", "MolEliza", ...]
########################################
async def get_raid_status(guild_id, target_percent, force_update, allyCode=None):
    ec, et, dict_guild = await get_guild_data_from_id(guild_id, force_update, allyCode=allyCode)
    if ec!=0:
        return None, None, [], 0, 0

    #Get dict to transform player ID into player object
    dict_members_by_id={}
    for member in dict_guild["member"]:
        dict_members_by_id[member["playerId"]] = member

    #Get raid data
    raid_id=None
    if "raidStatus" in dict_guild:
        for raidStatus in dict_guild["raidStatus"]:
            raid_id = raidStatus["raidId"]
            cur_raid = raidStatus

    if raid_id == None:
        return None, None, [], 0, 0

    #Get raid estimates from WookieBot
    query = "SELECT playerId, score FROM raid_estimates\n"
    query+= "JOIN players ON raid_estimates.allyCode = players.allyCode\n"
    query+= "JOIN guilds ON guilds.id = players.guildId\n"
    query+= "WHERE guilds.id='"+guild_id+"'\n"
    query+= "AND raid_name='"+raid_id+"'"
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_table(query)
    if db_data==None:
        # running without estilates is still possible
        db_data = []

    #prepare estilate scores per player
    dict_estimates = {}
    for line in db_data:
        dict_estimates[line[0]] = line[1]

    #Get generic progress about the raid
    expire_time = int(raidStatus["expireTime"])
    raid_join_time = raidStatus["joinPeriodEndTimeMs"]
    guild_score = int(raidStatus["guildRewardScore"])

    dict_raid_members_by_id={}
    for member in raidStatus["raidMember"]:
        dict_raid_members_by_id[member["playerId"]] = member

    list_inactive_players = []
    potential_score = guild_score
    for member_id in dict_members_by_id:
        member = dict_members_by_id[member_id]
        if member["guildJoinTime"]*1000 >= raid_join_time:
            #player joined after start of raid
            continue

        if member_id in dict_raid_members_by_id:
            score = int(dict_raid_members_by_id[member_id]["memberProgress"])
        else:
            #If the member if not in the raid status, it probably indicates
            # that he joined the guild too late to participate
            # No need to report that member in the status
            continue

        if member_id in dict_estimates:
            estimated_score = dict_estimates[member_id]
            status_txt = str(int(score/100000)/10)+"/"+str(int(estimated_score/100000)/10)+"M"
        else:
            #no estimate, can only check that the player has done something
            estimated_score = 0
            status_txt = "Aucun combat"

        if score <= estimated_score*target_percent/100:
            #this is not enough
            list_inactive_players.append({"name": member["playerName"], "status": status_txt})
            potential_score += estimated_score*target_percent/100 - score

    return raid_id, expire_time, list_inactive_players, guild_score, potential_score

async def update_unit_mods(unit_id, equipped_mods, unequipped_mods, txt_allyCode):
    url = "http://localhost:8000/updateMods"
    params = {"allyCode": txt_allyCode,
              "unit_id": unit_id, # this the unit ID('sjhf56FTFt'), not the definition ID ('ACKBAR')
              "equipped_mods": equipped_mods,
              "unequipped_mods": unequipped_mods}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "updateMods status="+str(resp.status))
                if resp.status==200:
                    resp_json = await(resp.json())

                elif resp.status==201:
                    return 1, "ERR: il faut au moins un mod à ajouter"
                else:
                    return 1, "ERR during RPC updateMods - code "+str(resp.status)

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer"
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer"
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer"

    if "err_code" in resp_json:
        return resp_json["err_code"], resp_json["err_txt"]

    return 0, ""

async def get_metadata():
    url = "http://localhost:8000/metadata"
    params = {}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "get metadata status="+str(resp.status))
                if resp.status==200:
                    resp_json = await(resp.json())
                else:
                    return 1, "ERR during RPC metadata - code "+str(resp.status), None

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

    if "err_code" in resp_json:
        return resp_json["err_code"], resp_json["err_txt"]

    metadata = resp_json
    return 0, "", metadata

