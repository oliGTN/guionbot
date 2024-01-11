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

import goutils
import data as godata
import connect_mysql
import go

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
    query = "SELECT guild_id, bot_allyCode, bot_locked_until, priority_cache FROM guild_bot_infos where bot_allyCode != ''"
    #goutils.log2("DBG", query)
    db_data = connect_mysql.get_table(query)

    ret_dict = {}
    if db_data != None:
        for line in db_data:
            ret_dict[line[0]] = {"allyCode": str(line[1]), "LockedUntil": line[2], "priority_cache":line[3]}

    return ret_dict

async def lock_bot_account_until(guild_id, until_seconds):
    dict_bot_accounts = get_dict_bot_accounts()
    if not guild_id in dict_bot_accounts:
        return 1, "Ce serveur discord n'a pas de warbot", None

    locked_until_txt = datetime.datetime.fromtimestamp(int(time.time())+until_seconds).strftime("%Y-%m-%d %H:%M:%S")
    query = "UPDATE guild_bot_infos SET bot_locked_until='"+locked_until_txt+"' WHERE guild_id='"+guild_id+"'"
    goutils.log2("DBG", query)
    connect_mysql.simple_execute(query)

    return 0, ""

async def lock_bot_account(guild_id):
    return await lock_bot_account_until(guild_id, 3600)

async def unlock_bot_account(guild_id):
    return await lock_bot_account_until(guild_id, 0)

def islocked_bot_account(guildName):
    dict_bot_accounts = get_dict_bot_accounts()
    locked_until_ts = datetime.datetime.timestamp(dict_bot_accounts[guildName]["LockedUntil"])
    is_locked = int(locked_until_ts) > int(time.time())
    return is_locked

#force_update: -1=always use cache / 0=depends on bot priority_cache option / 1=never use cache
async def get_guild_rpc_data(guild_id, event_types, force_update):
    goutils.log2("DBG", "START get_guild_rpc_data("+guild_id+", "+str(event_types)+", "+str(force_update)+")")
    calling_func = inspect.stack()[1][3]

    ec, et, dict_guild = await get_guild_data(guild_id, force_update)
    if ec!=0:
        return ec, et, None

    ec, et, dict_TBmapstats = await get_TBmapstats_data(guild_id, force_update)
    if ec!=0:
        return ec, et, None

    ec, et, dict_events = await get_event_data(dict_guild, event_types, force_update)
    if ec!=0:
        return ec, et, None

    goutils.log2("DBG", "END get_guild_rpc_data")
    return 0, "", [dict_guild, dict_TBmapstats, dict_events]

async def get_guild_data(guild_id, force_update):
    dict_bot_accounts = get_dict_bot_accounts()
    if not guild_id in dict_bot_accounts:
        return 1, "Ce serveur discord n'a pas de warbot", None

    bot_allyCode = dict_bot_accounts[guild_id]["allyCode"]
    goutils.log2("DBG", "bot account for "+guild_id+" is "+bot_allyCode)

    #locking bot has priority. Cannot be overriden
    if islocked_bot_account(guild_id):
        use_cache_data = True
        goutils.log2("WAR", "the bot account is being used... using cached data")
    else:
        if force_update == 1:
            use_cache_data = False
        elif force_update == -1:
            use_cache_data = True
        else: #force_update==0
            use_cache_data = bool(dict_bot_accounts[guild_id]["priority_cache"])

    # RPC REQUEST for guild
    url = "http://localhost:8000/guild"
    params = {"allyCode": bot_allyCode, "use_cache_data":use_cache_data}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "POST guild status="+str(resp.status))
                if resp.status==200:
                    guild_json = await(resp.json())
                else:
                    return 1, "Cannot get guild data from RPC", None

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

    if "guild" in guild_json:
        dict_guild = guild_json["guild"]
    else:
        return 1, "Aucune info de guilde disponible pour "+bot_allyCode, None

    return 0, "", dict_guild

async def get_TBmapstats_data(guild_id, force_update):
    dict_bot_accounts = get_dict_bot_accounts()
    if not guild_id in dict_bot_accounts:
        return 1, "Ce serveur discord n'a pas de warbot", None

    bot_allyCode = dict_bot_accounts[guild_id]["allyCode"]
    goutils.log2("DBG", "bot account for "+guild_id+" is "+bot_allyCode)

    #locking bot has priority. Cannot be overriden
    if islocked_bot_account(guild_id):
        use_cache_data = True
        goutils.log2("WAR", "the bot account is being used... using cached data")
    else:
        if force_update == 1:
            use_cache_data = False
        elif force_update == -1:
            use_cache_data = True
        else: #force_update==0
            use_cache_data = bool(dict_bot_accounts[guild_id]["priority_cache"])

    # RPC REQUEST for TBmapstats
    url = "http://localhost:8000/TBmapstats"
    params = {"allyCode": bot_allyCode, "use_cache_data":use_cache_data}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "POST TBmapstats status="+str(resp.status))
                if resp.status==200:
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

    if "currentStat" in TBmapstats_json:
        dict_TBmapstats = TBmapstats_json["currentStat"]
    else:
        dict_TBmapstats = {}

    return 0, "", dict_TBmapstats

async def get_event_data(dict_guild, event_types, force_update):
    guild_id = dict_guild["profile"]["id"]

    dict_bot_accounts = get_dict_bot_accounts()
    if not guild_id in dict_bot_accounts:
        return 1, "Ce serveur discord n'a pas de warbot", None

    bot_allyCode = dict_bot_accounts[guild_id]["allyCode"]
    goutils.log2("DBG", "bot account for "+guild_id+" is "+bot_allyCode)

    #locking bot has priority. Cannot be overriden
    if islocked_bot_account(guild_id):
        use_cache_data = True
        goutils.log2("WAR", "the bot account is being used... using cached data")
    else:
        if force_update == 1:
            use_cache_data = False
        elif force_update == -1:
            use_cache_data = True
        else: #force_update==0
            use_cache_data = bool(dict_bot_accounts[guild_id]["priority_cache"])

    if len(event_types) > 0:
        list_rpc_events = []

        #---------------
        #TB events
        list_channels=[]
        if ("territoryBattleStatus" in dict_guild) and ("TB" in event_types):
            for tb_status in dict_guild["territoryBattleStatus"]:
                if tb_status["selected"]:
                    tb_channel = tb_status["channelId"]
                    list_channels.append(tb_channel)

                    for conflict_zone in tb_status["conflictZoneStatus"]:
                        if conflict_zone["zoneStatus"]["zoneState"] != "ZONELOCKED":
                            zone_channel = conflict_zone["zoneStatus"]["channelId"]
                            list_channels.append(zone_channel)

        # RPC REQUEST for events
        url = "http://localhost:8000/events"
        params = {"allyCode": bot_allyCode, 
                  "eventType": "TB",
                  "list_channels": list_channels, 
                  "use_cache_data":use_cache_data}
        req_data = json.dumps(params)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=req_data) as resp:
                    goutils.log2("DBG", "POST TB events status="+str(resp.status))
                    if resp.status==200:
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
            list_rpc_events += resp_events['event']

        #---------------
        #TW events
        list_channels=[]
        if ("territoryWarStatus" in dict_guild) and ("TW" in event_types):
            for tw_status in dict_guild["territoryWarStatus"]:
                tw_guilds = []
                for guild_type in ["homeGuild", "awayGuild"]:
                    if guild_type in tw_status:
                        tw_guilds.append(tw_status[guild_type])

                for guild_status in tw_guilds:
                    for conflict_zone in guild_status["conflictStatus"]:
                        zone_channel = conflict_zone["zoneStatus"]["channelId"]
                        list_channels.append(zone_channel)

        # RPC REQUEST for events
        url = "http://localhost:8000/events"
        params = {"allyCode": bot_allyCode, 
                  "eventType": "TW",
                  "list_channels": list_channels, 
                  "use_cache_data":use_cache_data}
        req_data = json.dumps(params)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=req_data) as resp:
                    goutils.log2("DBG", "POST TW events status="+str(resp.status))
                    if resp.status==200:
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
            list_rpc_events += resp_events['event']

        #---------------
        #CHAT events
        list_channels=[]
        if ("roomAvailable" in dict_guild) and ("CHAT" in event_types):
            for room in dict_guild["roomAvailable"]:
                if room["type"] == "GUILDDEFAULT":
                    room_channel = room["roomId"]
                    list_channels.append(room_channel)

        # RPC REQUEST for events
        url = "http://localhost:8000/events"
        params = {"allyCode": bot_allyCode, 
                  "eventType": "CHAT",
                  "list_channels": list_channels, 
                  "use_cache_data":use_cache_data}
        req_data = json.dumps(params)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=req_data) as resp:
                    goutils.log2("DBG", "POST CHAT events status="+str(resp.status))
                    if resp.status==200:
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

            if event_ts <= eventLatest_ts:
                continue

            if event_ts > max_event_ts:
                max_event_ts = event_ts

            dict_event_counts[event_type]+=1
            if not event_file_id in dict_new_events:
                dict_new_events[event_file_id] = []
            dict_new_events[event_file_id].append(event)

        goutils.log2("DBG", "end loop list_rpc_events")

        # SET latest ts for events
        if max_event_ts == 0:
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
                    await release_sem(fevents)

                    #Add all events to dict_events
                    dict_events[event_file_id] = file_events

            await asyncio.sleep(0)

        goutils.log2("DBG", "end loop dict_new_events")

        if not use_cache_data:
            #log update time in DB - rounded to fix times (eg: always 00:05, 00:10 for 5 min period)
            query = "UPDATE guild_bot_infos SET bot_latestUpdate=FROM_UNIXTIME(ROUND(UNIX_TIMESTAMP(NOW())/60/bot_period_min,0)*60*bot_period_min) "
            query+= "WHERE guild_id='"+guild_id+"'"
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

    else:
        dict_events = {}

    return 0, "", dict_events

async def get_guild_data_from_ac(txt_allyCode, use_cache_data):
    ec, et, dict_player = await get_extplayer_data(txt_allyCode)
    if ec != 0:
        return 1, et, None

    if not "guildId" in dict_player:
        return 1, "ERR: ce joueur n'a pas de guilde", None

    guild_id = dict_player["guildId"]
    if guild_id == None or guild_id == "":
        return 1, "ERR: ce joueur n'a pas de guilde", None

    ec, et, dict_guild = await get_guild_data_from_id(guild_id, use_cache_data)

    return ec, et, dict_guild

async def get_guild_data_from_id(guild_id, use_cache_data):
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

    dict_guild = guild_json["guild"]

    return 0, "", dict_guild

async def get_extplayer_data(ac_or_id):
    url = "http://localhost:8000/extplayer"
    params = {"player_id": ac_or_id}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "getplayer status="+str(resp.status))
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

    return 0, "", dict_player

async def get_player_initialdata(ac):
    url = "http://localhost:8000/initialdata"
    params = {"allyCode": ac}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "initialdata status="+str(resp.status))
                if resp.status==200:
                    initialdata_player = await(resp.json())
                else:
                    return 1, "Cannot get initialdata from RPC", None

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

    return 0, "", initialdata_player

async def get_bot_player_data(guild_id, use_cache_data):
    # Get alllyCode from guild ID
    bot_allyCode = connect_mysql.get_value("SELECT bot_allyCode from guild_bot_infos WHERE guild_id='"+guild_id+"'")
    if bot_allyCode == None:
        return 1, "Ce serveur discord n'a pas de warbot", None
    bot_allyCode = str(bot_allyCode)
    goutils.log2("DBG", "bot account for "+guild_id+" is "+bot_allyCode)

    # Manage cache
    use_cache_data = False
    if islocked_bot_account(guild_id):
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
                goutils.log2("DBG", "botplayer status="+str(resp.status))
                if resp.status==200:
                    dict_player = await(resp.json())
                else:
                    return 1, "Cannot get player data from RPC", None

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

    return 0, "", dict_player

async def join_tw(guild_id):
    dict_bot_accounts = get_dict_bot_accounts()
    if not guild_id in dict_bot_accounts:
        return 1, "Ce serveur discord n'a pas de warbot", None

    err_code, err_txt, dict_guild = await get_guild_data(guild_id, -1)
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
                    pass
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

    return 0, "Le bot a rejoint la GT"

# OUT: dict_platoons = {} #key="GLS1-mid-2", value={key=perso, value=[player, player...]}
async def get_actual_tb_platoons(guild_id, force_update):
    active_round = "" # "GLS4"
    dict_platoons = {} #key="GLS1-mid-2", value={key=perso, value=[player, player...]}
    list_open_territories = [0, 0, 0] # [4, 3, 3]

    dict_tb = godata.get("tb_definition.json")

    err_code, err_txt, dict_guild = await get_guild_data(guild_id, force_update)

    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return '', None, None

    guildName = dict_guild["profile"]["name"]

    dict_member_by_id = {}
    for member in dict_guild["member"]:
        dict_member_by_id[member["playerId"]] = member["playerName"]

    dict_unitsList = godata.get("unitsList_dict.json")

    if not "territoryBattleStatus" in dict_guild:
        goutils.log2("WAR", "["+guildName+"] no TB in progress")
        return '', None, None

    for battleStatus in dict_guild["territoryBattleStatus"]:
        if battleStatus["selected"]:
            tb_id = battleStatus["definitionId"]
            if not tb_id in dict_tb:
                goutils.log2("WAR", "["+guildName+"] TB inconnue du bot")
                return '', None, None

            tb_name = dict_tb[tb_id]["shortname"]
            active_round = tb_name + str(battleStatus["currentRound"])

            if active_round == 0:
                return '', None, None

            for zone in battleStatus["reconZoneStatus"]:
                recon_name = zone["zoneStatus"]["zoneId"]
                zone_name = "_".join(recon_name.split("_")[:-1])

                if zone["zoneStatus"]["zoneState"] == "ZONEOPEN":
                    ret_re = re.search(".*_phase0(\d)_conflict0(\d)", zone_name)
                    zone_position = int(ret_re.group(2))
                    zone_phase = int(ret_re.group(1))
                    list_open_territories[zone_position-1] = zone_phase
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
                                player_name = dict_member_by_id[player_id]
                                dict_platoons[platoon_name][unit_name].append(player_name)
                            else:
                                dict_platoons[platoon_name][unit_name].append('')

    if max(list_open_territories)==0:
        return '', None, None

    return active_round, dict_platoons, list_open_territories

async def get_guildLog_messages(guild_id, onlyLatest):

    query = "SELECT bot_allyCode, chatChan_id, twlogChan_id, tblogChan_id, chatLatest_ts "\
            "FROM guild_bot_infos WHERE guild_id='"+guild_id+"'"
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

    if bot_allyCode == '':
        return 1, "ERR: no RPC bot for guild "+guild_id, None

    err_code, err_txt, dict_guild = await get_guild_data(guild_id, -1)
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
    err_code, err_txt, dict_events = await get_event_data(dict_guild, eventTypes, -1)
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
                   "TB":   [tblogChan_id, list_tb_logs]}

async def get_logs_from_events(dict_events, guildId, chatLatest_ts):
    FRE_FR = godata.get('FRE_FR.json')
    dict_unitsList = godata.get("unitsList_dict.json")
    dict_tw = godata.dict_tw
    dict_tb = godata.get("tb_definition.json")

    list_chat_events = []
    list_tw_logs = []
    list_tb_logs = []
    dict_squads={}
    for event_group_id in dict_events:
        event_group = dict_events[event_group_id]
        for event_id in event_group:
            event = event_group[event_id]
            event_ts = int(event["timestamp"])
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

                                if not squad_id in dict_squads:
                                    dict_squads[squad_id]={}
                                dict_squads[squad_id]["leader"] = leader_opponent
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
                                    activity_txt += " (reste "+str(squad_size-count_dead)+")"

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
                                    activity_txt += " (mode avion)"
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
                            scoretotal = activity["zoneData"]["scoreTotal"]
                            activity_txt = "Score: "+scoretotal

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

                    activity_txt = "COMBAT: "+author+" "+str(phases_ok)+"/"+str(phases_tot)+" en "+zone_name
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

async def tag_tb_undeployed_players(guild_id, force_update):
    dict_tb=godata.get("tb_definition.json")
    ec, et, tb_data = await get_tb_status(guild_id, "", False, force_update)
    if ec!=0:
        return 1, et, None

    dict_phase = tb_data["phase"]
    dict_strike_zones = tb_data["strike_zones"]
    dict_tb_players = tb_data["players"]
    dict_open_zones = tb_data["open_zones"]

    dict_deployment_types = {}
    for zone_name in dict_open_zones:
        zone = dict_open_zones[zone_name]
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
    for playerName in dict_tb_players:
        await asyncio.sleep(0)

        player = dict_tb_players[playerName]
        undeployed_player = False

        ret_print_player = ""

        if dict_tb[dict_phase["type"]]["shortname"] == "ROTE":
            if dict_deployment_types["mix"]:
                ratio_deploy_mix = player["score"]["deployedMix"] / player["mix_gp"]
                if ratio_deploy_mix < 0.99:
                    undeployed_player = True
                    ret_print_player += "{:,}".format(dict_tb_players[playerName]["score"]["deployedMix"]) \
                                       +"/" + "{:,}".format(dict_tb_players[playerName]["mix_gp"]) + " "
        else:
            if dict_deployment_types["ships"]:
                ratio_deploy_ships = player["score"]["deployedShips"] / player["ship_gp"]
                if ratio_deploy_ships < 0.99:
                    undeployed_player = True
                    ret_print_player += "Fleet: {:,}".format(dict_tb_players[playerName]["score"]["deployedShips"]) \
                                       +"/" + "{:,}".format(dict_tb_players[playerName]["ship_gp"]) + " "

            if dict_deployment_types["chars"]:
                ratio_deploy_chars = player["score"]["deployedChars"] / player["char_gp"]
                if ratio_deploy_chars < 0.99:
                    undeployed_player = True
                    ret_print_player += "Squad: {:,}".format(dict_tb_players[playerName]["score"]["deployedChars"]) \
                                       +"/" + "{:,}".format(dict_tb_players[playerName]["char_gp"]) + " "

        if undeployed_player:
            lines_player.append([playerName, ret_print_player])

    return 0, "", {"lines_player": lines_player, "round_endTime": dict_phase["round_endTime"]}

##############################################################
async def get_tb_status(guild_id, targets_zone_stars, compute_estimated_fights, force_update):
    dict_tb = godata.get("tb_definition.json")

    ec, et, rpc_data = await get_guild_rpc_data(guild_id, ["TB"], force_update)
    if ec!=0:
        return 1, et, None

    dict_guild=rpc_data[0]
    mapstats=rpc_data[1]
    dict_all_events=rpc_data[2]
    guildName = dict_guild["profile"]["name"]

    #get guild members
    dict_members_by_id={}
    for member in dict_guild["member"]:
        dict_members_by_id[member["playerId"]] = member

    tb_ongoing=False
    if "territoryBattleStatus" in dict_guild:
        for battleStatus in dict_guild["territoryBattleStatus"]:
            if battleStatus["selected"]:
                battle_id = battleStatus["instanceId"]
                goutils.log2("DBG", "Selected TB = "+battle_id)
                tb_ongoing=True
                tb_type = battleStatus["definitionId"]
                if not tb_type in dict_tb:
                    return 1, "TB inconnue du bot", None

                tb_round = battleStatus["currentRound"]
                if tb_round > dict_tb[tb_type]["maxRound"]:
                    tb_ongoing=True

                tb_round_endTime = int(battleStatus["currentRoundEndTime"])
                tb_round_startTime = tb_round_endTime - dict_tb[tb_type]["PhaseDuration"]
                tb_startTime = tb_round_endTime - tb_round * dict_tb[tb_type]["PhaseDuration"]

                if battle_id in dict_all_events:
                    dict_events=dict_all_events[battle_id]
                else:
                    dict_events={}
                break

    if not tb_ongoing:
        return 1, "No TB on-going", None

    query = "SELECT name, char_gp, ship_gp, playerId FROM players WHERE guildName='"+guildName.replace("'", "''")+"'"
    goutils.log2("DBG", query)
    list_playername_gp_id = connect_mysql.get_table(query)

    dict_tb_players = {}
    dict_strike_zones = {}
    dict_covert_zones = {}
    dict_open_zones = {}
    dict_phase = {"id": battle_id, 
                  "round": tb_round, 
                  "round_endTime": tb_round_endTime, 
                  "type": tb_type, 
                  "name": dict_tb[tb_type]["name"]}

    for playername_gp_id in list_playername_gp_id:
        #test if player participates to TB - if joined guild after start of TB
        player_id = playername_gp_id[3]
        if not player_id in dict_members_by_id:
            #Player already left
            continue

        guildJoinTime = int(dict_members_by_id[playername_gp_id[3]]["guildJoinTime"]) * 1000
        if guildJoinTime > tb_startTime:
            #Player joined after start of TB
            continue

        dict_tb_players[playername_gp_id[0]] = {}
        dict_tb_players[playername_gp_id[0]]["char_gp"] = playername_gp_id[1]
        dict_tb_players[playername_gp_id[0]]["ship_gp"] = playername_gp_id[2]
        dict_tb_players[playername_gp_id[0]]["mix_gp"] = playername_gp_id[1] + playername_gp_id[2]
        dict_tb_players[playername_gp_id[0]]["score"] = {"deployedShips": 0,
                                                      "deployedChars": 0,
                                                      "deployedMix": 0,
                                                      "deployed": 0,
                                                      "Platoons": 0,
                                                      "strikes": 0} 
        dict_tb_players[playername_gp_id[0]]["strikes"] = {} # "conflixtX_strikeY": "1/4"
        dict_tb_players[playername_gp_id[0]]["strike_attempts"] = 0
        dict_tb_players[playername_gp_id[0]]["coverts"] = {} # "conflixtX_covertY": True
        dict_tb_players[playername_gp_id[0]]["covert_attempts"] = 0

    completed_stars = 0 # stars on completed (closed) zones
    for zone in battleStatus["conflictZoneStatus"]:
        zone_name = zone["zoneStatus"]["zoneId"]
        zone_score = int(zone["zoneStatus"]["score"])
        if zone["zoneStatus"]["zoneState"] == "ZONEOPEN":
            dict_open_zones[zone_name] = {"score": zone_score}
        elif zone["zoneStatus"]["zoneState"] == "ZONECOMPLETE":
            for star_score in dict_tb[zone_name]["scores"]:
                if zone_score >= star_score:
                    completed_stars += 1
    dict_phase["prev_stars"] = completed_stars

    #sort the dict to display zones in the same order as the game
    dict_open_zones = dict(sorted(dict_open_zones.items(), key=lambda x:dict_tb[tb_type]["zonePositions"][dict_tb[x[0]]["name"].split("-")[1]]))

    if len(dict_open_zones)==0:
        return 1, "No TB on-going", None

    total_players_guild = len(dict_tb_players)
    dict_phase["TotalPlayers"] = total_players_guild
    for zone in battleStatus["strikeZoneStatus"]:
        if zone["zoneStatus"]["zoneState"] == "ZONEOPEN":
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
        if zone["zoneStatus"]["zoneState"] == "ZONEOPEN":
            covert_name = zone["zoneStatus"]["zoneId"]
            covert_shortname = covert_name.split("_")[-1]

            zone_name = covert_name[:-len(covert_shortname)-1]

            done_coverts = zone["playersParticipated"]
            if not covert_name in dict_covert_zones:
                dict_covert_zones[covert_name] = {}

            dict_covert_zones[covert_name]["participation"] = done_coverts

    for event_id in dict_events:
        event=dict_events[event_id]
        event_time = int(event["timestamp"])
        playerName = event["authorName"]
        if not playerName in dict_tb_players:
            #should not happen unless new player and until API resynchronizes
            continue

        if event_time < tb_round_startTime:
            #event on same zone but bduring previous round
            continue

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
                if zone_name in dict_open_zones:
                    score = int(event_data["activity"][zoneData_key]["scoreDelta"])
                    dict_tb_players[playerName]["score"]["strikes"] += score

                    dict_strike_zones[strike_name]["eventStrikes"] += 1
                    dict_strike_zones[strike_name]["eventStrikeScore"] += score

                    strike_shortname="_".join(strike_name.split("_")[-2:])

                    done_waves = event_data["activity"][zoneData_key]["activityLogMessage"]["param"][2]["paramValue"][0]
                    total_waves = event_data["activity"][zoneData_key]["activityLogMessage"]["param"][3]["paramValue"][0]
                    dict_tb_players[playerName]["strikes"][strike_shortname] = done_waves+"/"+total_waves

            elif "RECON_CONTRIBUTION" in event_key:
                #Complete a platoon
                zone_name = event_data["activity"][zoneData_key]["zoneId"]
                if zone_name in dict_open_zones:
                    score = int(event_data["activity"][zoneData_key]["scoreDelta"])
                    dict_tb_players[playerName]["score"]["Platoons"] += score

            elif "DEPLOY" in event_key:
                #Deployment (strike or platoon)
                zone_name = event_data["activity"][zoneData_key]["zoneId"]
                if zone_name in dict_open_zones:
                    score = int(event_data["activity"][zoneData_key]["scoreDelta"])
                    if dict_tb[zone_name]["type"] == "ships":
                        dict_tb_players[playerName]["score"]["deployedShips"] += score
                        dict_tb_players[playerName]["score"]["deployedMix"] += score
                    elif dict_tb[zone_name]["type"] == "chars":
                        dict_tb_players[playerName]["score"]["deployedChars"] += score
                        dict_tb_players[playerName]["score"]["deployedMix"] += score
                    else:
                        dict_tb_players[playerName]["score"]["deployedMix"] += score

            elif "COVERT_COMPLETE" in event_key:
                # Special mission
                zone_name = event_data["activity"][zoneData_key]["zoneId"]
                strike_name = event_data["activity"][zoneData_key]["sourceZoneId"]
                if zone_name in dict_open_zones:
                    strike_shortname="_".join(strike_name.split("_")[-2:])
                    dict_tb_players[playerName]["coverts"][strike_shortname] = True

    for mapstat in mapstats:
        if mapstat["mapStatId"] == "strike_attempt_round_"+str(tb_round):
            if "playerStat" in mapstat:
                for playerstat in mapstat["playerStat"]:
                    member_id = playerstat["memberId"]
                    playerName = dict_members_by_id[member_id]["playerName"]
                    if not playerName in dict_tb_players:
                        continue

                    attempts = int(playerstat["score"])
                    dict_tb_players[playerName]["strike_attempts"] = attempts

        elif mapstat["mapStatId"] == "covert_attempt_round_"+str(tb_round):
            if "playerStat" in mapstat:
                for playerstat in mapstat["playerStat"]:
                    member_id = playerstat["memberId"]
                    playerName = dict_members_by_id[member_id]["playerName"]
                    if not playerName in dict_tb_players:
                        continue

                    attempts = int(playerstat["score"])
                    dict_tb_players[playerName]["covert_attempts"] = attempts

        elif mapstat["mapStatId"] == "power_round_"+str(tb_round):
            if "playerStat" in mapstat:
                for playerstat in mapstat["playerStat"]:
                    member_id = playerstat["memberId"]
                    playerName = dict_members_by_id[member_id]["playerName"]
                    if not playerName in dict_tb_players:
                        #should not happen unless new player and until API resynchronizes
                        continue

                    score = int(playerstat["score"])
                    dict_tb_players[playerName]["score"]["deployed"] = score
                    if dict_tb_players[playerName]["score"]["deployed"] != dict_tb_players[playerName]["score"]["deployedMix"]:
                        goutils.log2("WAR", "Event deployment does not match total deployment for "+playerName)
                        goutils.log2("WAR", "("+str(dict_tb_players[playerName]["score"]["deployedMix"])+" vs "+str(dict_tb_players[playerName]["score"]["deployed"])+")")

                        #Estimate ships / chars score from total score and current ship / char
                        not_deployed_ships = dict_tb_players[playerName]["ship_gp"] - dict_tb_players[playerName]["score"]["deployedShips"]
                        not_deployed_chars = dict_tb_players[playerName]["char_gp"] - dict_tb_players[playerName]["score"]["deployedChars"]
                        bonus_deployment = dict_tb_players[playerName]["score"]["deployed"] - dict_tb_players[playerName]["score"]["deployedMix"]

                        if (not_deployed_ships + not_deployed_chars) == 0:
                            #if everything is deployed, no need for bonus
                            bonus_ships = 0
                            bonus_chars = 0
                        else:
                            bonus_ships = int(bonus_deployment * not_deployed_ships / (not_deployed_ships + not_deployed_chars))
                            bonus_chars = int(bonus_deployment * not_deployed_chars / (not_deployed_ships + not_deployed_chars))
                        dict_tb_players[playerName]["score"]["deployedShips"] += bonus_ships
                        dict_tb_players[playerName]["score"]["deployedChars"] += bonus_chars
                        dict_tb_players[playerName]["score"]["deployedMix"] = dict_tb_players[playerName]["score"]["deployed"]

    dict_remaining_deploy = {"ships": 0, "chars": 0, "mix": 0}
    for playerName in dict_tb_players:
        playerData = dict_tb_players[playerName]
        dict_remaining_deploy["ships"] += playerData["ship_gp"] - playerData["score"]["deployedShips"]
        dict_remaining_deploy["chars"] += playerData["char_gp"] - playerData["score"]["deployedChars"]
        dict_remaining_deploy["mix"] += playerData["mix_gp"] - playerData["score"]["deployedMix"]
        
    dict_phase["availableShipDeploy"] = dict_remaining_deploy["ships"]
    dict_phase["availableCharDeploy"] = dict_remaining_deploy["chars"]
    dict_phase["availableMixDeploy"] = dict_remaining_deploy["mix"]

    list_deployment_types = []
    for zone_name in dict_open_zones:
        zone_deployment_type = dict_tb[zone_name]["type"]
        if not zone_deployment_type in list_deployment_types:
            list_deployment_types.append(zone_deployment_type)

    #count remaining players
    lines_player = []

    #Loop on all TB players to assess the list of who has finished playing
    finished_players = {"ships": [], "chars": [], "mix": []}
    for playerName in dict_tb_players:

        #depending on the TB, playing in ships/chars, or in mix,
        # detect if the player has finished playing, by checking if all is deployed
        # If the player has deployed < 99%, he is considered not finished 
        # and count as +1 in the remaining players to fight

        if "ships" in list_deployment_types:
            ratio_deploy_ships = dict_tb_players[playerName]["score"]["deployedShips"] / dict_tb_players[playerName]["ship_gp"]
            if ratio_deploy_ships >= 0.99:
                finished_players["ships"].append(playerName)

        if "chars" in list_deployment_types:
            ratio_deploy_chars = dict_tb_players[playerName]["score"]["deployedChars"] / dict_tb_players[playerName]["char_gp"]
            if ratio_deploy_chars >= 0.99:
                finished_players["chars"].append(playerName)

        if "mix" in list_deployment_types:
            ratio_deploy_mix = dict_tb_players[playerName]["score"]["deployedMix"] / dict_tb_players[playerName]["mix_gp"]
            if ratio_deploy_mix >= 0.99:
                finished_players["mix"].append(playerName)

    # Loop by zone then by strike in the zone
    for zone in dict_open_zones:
        total_strikes = 0
        for z in dict_open_zones:
            for s in dict_tb[z]["strikes"]:
                total_strikes+=1

        for strike in dict_tb[zone]["strikes"]:
            strike_shortname = "conflict0"+zone[-1]+"_"+strike
            strike_name = zone+"_"+strike

            # First loop to get the amount of tries in this fight
            tryCount = 0
            for playerName in dict_tb_players:
                if len(dict_tb_players[playerName]["strikes"]) == total_strikes:
                    # the player has fought all possible fights
                    # This helps counting a fight with no wave when the player does them all
                    tryCount += 1
                else:
                    if strike_shortname in dict_tb_players[playerName]["strikes"]:
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
                if not strike_shortname in dict_tb_players[playerName]["strikes"]:

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

    #compute zone stats apart for deployments
    for zone_name in dict_open_zones:
        current_score = dict_open_zones[zone_name]["score"]

        estimated_strike_score = 0
        estimated_strike_fights = 0
        max_strike_score = 0
        cur_strike_score = 0
        cur_strike_fights = {}
        cur_covert_fights = {}
        for strike in dict_tb[zone_name]["strikes"]:
            strike_name = zone_name + "_" + strike
            if compute_estimated_fights:
                estimated_strike_fights += dict_strike_zones[strike_name]["estimatedStrikes"]
                estimated_strike_score += dict_strike_zones[strike_name]["estimatedScore"]
            max_strike_score += dict_strike_zones[strike_name]["maxPossibleScore"]

            cur_strike_fights[strike] = dict_strike_zones[strike_name]["participation"]
            cur_strike_score += dict_strike_zones[strike_name]["eventStrikeScore"]

        for covert in dict_tb[zone_name]["coverts"]:
            covert_name = zone_name + "_" + covert
            cur_covert_fights[covert] = dict_covert_zones[covert_name]["participation"]

        dict_open_zones[zone_name]["strikeScore"] = cur_strike_score
        dict_open_zones[zone_name]["strikeFights"] = cur_strike_fights
        dict_open_zones[zone_name]["covertFights"] = cur_covert_fights
        dict_open_zones[zone_name]["estimatedStrikeFights"] = estimated_strike_fights
        dict_open_zones[zone_name]["estimatedStrikeScore"] = estimated_strike_score
        dict_open_zones[zone_name]["maxStrikeScore"] = max_strike_score
        dict_open_zones[zone_name]["deployment"] = 0

        star_for_score=0
        for star_score in dict_tb[zone_name]["scores"]:
            if current_score >= star_score:
                star_for_score += 1
        dict_open_zones[zone_name]["stars"] = star_for_score

    #zone stats
    tb_type = dict_phase["type"]

    if targets_zone_stars == "":
        #original warstats logic: closest star, then next closest star...
        #split the zones by type
        dict_zones_by_type = {"ships": [], "chars": [], "mix": []}
        for zone_name in dict_open_zones:
            zone_type = dict_tb[zone_name]["type"]
            dict_zones_by_type[zone_type].append(zone_name)

        full_zones = 0
        for zone_type in ["ships", "chars", "mix"]:
            while (dict_remaining_deploy[zone_type] > 0) and (full_zones < len(dict_zones_by_type[zone_type])):
                #find closest star
                min_dist_star = -1
                min_zone_name = ""
                full_zones = 0
                for zone_name in dict_zones_by_type[zone_type]:
                    cur_score = dict_open_zones[zone_name]["score"]
                    if compute_estimated_fights:
                        cur_score += dict_open_zones[zone_name]["estimatedStrikeScore"]
                    cur_score += dict_open_zones[zone_name]["deployment"]

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
                    deploy_value = min(min_dist_star, dict_remaining_deploy[zone_type])
                    dict_open_zones[min_zone_name]["deployment"] += deploy_value
                    dict_remaining_deploy[zone_type] -= deploy_value

    else:
        targets_zone_stars = targets_zone_stars.strip()
        while '  ' in targets_zone_stars:
            targets_zone_stars = targets_zone_stars.replace('  ', ' ')

        already_computed_zones = []
        for target_zone_stars in targets_zone_stars.split(" "):
            if not ":" in target_zone_stars:
                return 1, target_zone_stars + " --> chaque objectif de zone doit être de la forme <zone>:<étoiles> (ex: top:3)", None

            # get and check target zone name
            target_zone_shortname = target_zone_stars.split(":")[0]

            zone_found = False
            list_zone_names = []
            for zone_name in dict_open_zones:
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

            #Targeting 0 stars or 1 is the same target (having the star or just below it)
            if target_stars == 0:
                target_stars = 1

            #Check if the zone is not used twice in the option
            if target_zone_name in already_computed_zones:
                return 1, target_zone_stars+" --> zone utilisée 2 fois : " + target_zone_name, None
            already_computed_zones.append(target_zone_name)



            current_score = dict_open_zones[zone_name]["score"]
            estimated_strike_score = dict_open_zones[zone_name]["estimatedStrikeScore"]
            score_with_estimated_strikes = current_score + estimated_strike_score

            target_star_score = dict_tb[zone_name]["scores"][target_stars-1]
            if dict_tb[zone_name]["type"] == "ships":
                deploy_consumption = max(0, min(dict_remaining_deploy["ships"], target_star_score - score_with_estimated_strikes))
                dict_remaining_deploy["ships"] -= deploy_consumption
            elif dict_tb[zone_name]["type"] == "chars":
                deploy_consumption = max(0, min(dict_remaining_deploy["chars"], target_star_score - score_with_estimated_strikes))
                dict_remaining_deploy["chars"] -= deploy_consumption
            else:
                deploy_consumption = max(0, min(dict_remaining_deploy["mix"], target_star_score - score_with_estimated_strikes))
                dict_remaining_deploy["mix"] -= deploy_consumption

            dict_open_zones[zone_name]["deployment"] = deploy_consumption
            score_with_estimations = score_with_estimated_strikes + deploy_consumption

    dict_phase["remainingShipDeploy"] = dict_remaining_deploy["ships"]
    dict_phase["remainingCharDeploy"] = dict_remaining_deploy["chars"]
    dict_phase["remainingMixDeploy"] = dict_remaining_deploy["mix"]

    #Compute estimated stars per zone
    for zone_name in dict_open_zones:
        cur_score = dict_open_zones[zone_name]["score"]
        if compute_estimated_fights:
            cur_score += dict_open_zones[zone_name]["estimatedStrikeScore"]
        cur_score += dict_open_zones[zone_name]["deployment"]

        star_for_score=0
        for star_score in dict_tb[zone_name]["scores"]:
            if cur_score >= star_score:
                star_for_score += 1
        dict_open_zones[zone_name]["estimatedStars"] = star_for_score

    return 0, "", {"phase": dict_phase, 
                   "strike_zones": dict_strike_zones, 
                   "players": dict_tb_players, 
                   "open_zones": dict_open_zones}

##########################################"
# OUT: dict_territory_scores = {"tb3_mixed_phase03_conflit02": 24500000, ...}
# OUT: tb_active_round = 3
##########################################"
async def get_tb_guild_scores(guild_id, force_update):
    dict_tb = godata.get("tb_definition.json")
    ec, et, tb_data = await get_tb_status(guild_id, "", False, force_update)
    if ec!=0:
        return {}, ""

    dict_phase = tb_data["phase"]
    dict_strike_zones = tb_data["strike_zones"]
    dict_tb_players = tb_data["players"]
    dict_open_zones = tb_data["open_zones"]

    active_round = dict_tb[dict_phase["type"]]["shortname"]+str(dict_phase["round"])
    dict_territory_scores = {}
    for zone in dict_open_zones:
        zone_name_tab = dict_tb[zone]["name"].split("-")
        zone_name = zone_name_tab[0][:-1]
        zone_name += "-P"
        zone_name += zone_name_tab[0][-1]
        zone_name += "-"
        zone_name += zone_name_tab[1]
        zone_score = dict_open_zones[zone]["score"]
        dict_territory_scores[zone] = zone_score

    return dict_territory_scores, active_round

########################################
# get_tw_opponent_leader
# get an allyCode of the opponent TW guild
########################################
async def get_tw_opponent_leader(guild_id):
    ec, et, dict_guild = await get_guild_data(guild_id, -1)
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

    ec, et, dict_guild = await get_guild_data_from_id(opp_guild_id, False)
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
#   "homeGuild": {"list_teams": [["T1", "Karcot", ["GENERALSKYWALGER", "ARCTROOPER", ...], <is_beaten>, <fights>],
#                                ["T1", "JeanLuc"...
#                 "list_territories": [["T1", <size>, <filled>, <victories>, <fails>, <commandMsg>, <status>], ...]
#                }, 
#   "awayGuild": {"list_teams": ...,
#                 "list_territories": ...
#                }, 
#   "opp_guildName": name, 
#   "opp_guildId": id
# }
########################################
async def get_tw_status(guild_id, force_update):
    dict_tw=godata.dict_tw

    ec, et, dict_guild = await get_guild_data(guild_id, force_update)
    if ec!=0:
        return {"tw_id": None}

    dict_members_by_id={}
    for member in dict_guild["member"]:
        dict_members_by_id[member["playerId"]] = member["playerName"]

    tw_id=None
    if "territoryWarStatus" in dict_guild:
        for battleStatus in dict_guild["territoryWarStatus"]:
            # the TW is considered on-going during
            # - defense phase (round=0, awayGuild is defined)
            # - attack phase (round=1)
            # - analyse phase (round=2)
            if "awayGuild" in battleStatus:
                tw_id = battleStatus["instanceId"]
                cur_tw = battleStatus
                tw_round = battleStatus["currentRound"]

    if tw_id == None:
        return {"tw_id": None}

    opp_guildName = battleStatus["awayGuild"]["profile"]["name"]
    opp_guildId = battleStatus["awayGuild"]["profile"]["id"]

    list_teams = {}
    list_territories = {}

    capa_list = godata.get("unit_capa_list.json")
    for guild in ["homeGuild", "awayGuild"]:
        list_teams[guild] = []
        list_territories[guild] = []
        if guild in cur_tw:
            for zone in cur_tw[guild]["conflictStatus"]:
                zone_id = zone["zoneStatus"]["zoneId"]
                zone_shortname = dict_tw[zone_id]
                victories=0
                fails=0
                if "warSquad" in zone:
                    for squad in zone["warSquad"]:
                        player_name = squad["playerName"]
                        list_chars = []
                        for c in squad["squad"]["cell"]:
                            unit_id = c["unitDefId"].split(":")[0]
                            my_unit = {"unitDefId": c["unitDefId"],
                                       "unitId": unit_id,
                                       "level": c["unitBattleStat"]["level"],
                                       "gear": c["unitBattleStat"]["tier"],
                                       "relic": c["unitBattleStat"]["unitRelicTier"]-5,
                                       "zetas": [],
                                       "omicrons": [],
                                       "turnMeter": c["unitState"]["turnPercent"]}
                            if "skill" in c["unitBattleStat"]:
                                for s in c["unitBattleStat"]["skill"]:
                                    skill_id = s["id"]
                                    skill_tier = s["tier"]+2
                                    if skill_id in capa_list[unit_id]:
                                        if capa_list[unit_id][skill_id]["zetaTier"] < 99 and \
                                           capa_list[unit_id][skill_id]["zetaTier"] <= skill_tier:
                                            my_unit["zetas"].append(skill_id)
                                        if capa_list[unit_id][skill_id]["omicronTier"] < 99 and \
                                           capa_list[unit_id][skill_id]["omicronTier"] <= skill_tier:
                                            my_unit["omicrons"].append(skill_id)

                            list_chars.append(my_unit)

                        is_beaten = (squad["squadStatus"]=="SQUADDEFEATED")
                        fights = squad["successfulDefends"]
                        list_teams[guild].append([zone_shortname, player_name, list_chars, is_beaten, fights])

                        if is_beaten:
                            victories+=1
                            fails+=(fights-1)
                        else:
                            fails+=fights

                zone_size = zone["squadCapacity"]
                filled = zone["squadCount"] + victories
                if "commandMessage" in zone["zoneStatus"]:
                    commandMsg = zone["zoneStatus"]["commandMessage"]
                else:
                    commandMsg = None
                if "commandState" in zone["zoneStatus"]:
                    commandState = zone["zoneStatus"]["commandState"]
                else:
                    commandState = None
                list_territories[guild].append([zone_shortname, zone_size, filled, victories, fails, commandMsg, commandState])

    return {"tw_id": tw_id, \
            "tw_round": tw_round, \
            "homeGuild": {"list_teams": list_teams["homeGuild"], \
                         "list_territories": list_territories["homeGuild"]}, \
            "awayGuild": {"list_teams": list_teams["awayGuild"], \
                         "list_territories": list_territories["awayGuild"]}, \
            "opp_guildName": opp_guildName, \
            "opp_guildId": opp_guildId}

async def get_tw_active_players(guild_id, force_update):
    ec, et, dict_guild = await get_guild_data(guild_id, force_update)
    if ec!=0:
        return 1, et, None

    dict_members={}
    list_active_players = []
    for member in dict_guild["member"]:
        dict_members[member["playerId"]] = member["playerName"]
    for member in dict_guild["territoryWarStatus"][0]["optedInMember"]:
        list_active_players.append(dict_members[member["memberId"]])

    return 0, "", list_active_players

async def deploy_tb(txt_allyCode, zone, list_defId):
    err_code, err_txt, dict_player = await get_player_data(txt_allyCode, False)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en se connectant au bot"

    list_char_id = []
    for unit in dict_player["rosterUnit"]:
        full_defId = unit["definitionId"]
        defId = full_defId.split(":")[0]
        if defId in list_defId:
            list_char_id.append(unit["id"])

    if len(list_char_id) == 0:
        return 1, "Plus rien à déployer"

    process_cmd_list = ["/home/pi/GuionBot/warstats/deploy_tb.sh", txt_allyCode, zone]+list_char_id
    goutils.log2("DBG", process_cmd_list)
    process = subprocess.run(process_cmd_list)
    goutils.log2("DBG", "deploy_tb code="+str(process.returncode))
    if process.returncode!=0:
        if process.returncode == 202:
            return 1, "Erreur en déployant en TB - pas de TB en cours"
        elif process.returncode == 203:
            return 1, "Erreur en déployant en TB - rien à déployer"
        elif process.returncode != 0:
            return 1, "Erreur en déployant en TB - code="+str(process.returncode)

    return 0, "Déploiement OK en " + zone

async def deploy_tw(guild_id, zone, list_defId):
    dict_unitsList = godata.get("unitsList_dict.json")

    dict_bot_accounts = get_dict_bot_accounts()
    if not guild_id in dict_bot_accounts:
        return 1, "Ce serveur discord n'a pas de warbot", None

    err_code, err_txt, dict_player = await get_bot_player_data(guild_id, False)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en se connectant au bot"

    bot_allyCode = dict_bot_accounts[guild_id]["allyCode"]

    dict_roster = {}
    for unit in dict_player["rosterUnit"]:
        full_defId = unit["definitionId"]
        defId = full_defId.split(":")[0]
        dict_roster[defId] = unit

    list_char_id = []
    team_combatType = None
    for defId in list_defId:
        list_char_id.append(dict_roster[defId]["id"])
        unit_combatType = dict_unitsList[defId]["combatType"]
        if team_combatType==None or team_combatType==unit_combatType:
            team_combatType=unit_combatType
        else:
            goutils.log2("ERR", "Mixing chars and ships")
            return 1, "ERR: ne pas mélanger toons et vaisseaux svp"
            
    if team_combatType == 1 and len(list_char_id) != 5:
        goutils.log2("ERR", "Need 5 units but found "+str(list_char_id))
        return 1, "ERR: il faut exactement 5 persos"

    if team_combatType == 2 and len(list_char_id) < 4:
        goutils.log2("ERR", "Need at least 4 units but found "+str(list_char_id))
        return 1, "ERR: il faut au moins 4 vaisseaux"

    if team_combatType==2:
        #Fleet
        process = subprocess.run(["/home/pi/GuionBot/warstats/deploy_tw.sh", bot_allyCode, zone, '-s']+list_char_id)
    else:
        #Ground
        process = subprocess.run(["/home/pi/GuionBot/warstats/deploy_tw.sh", bot_allyCode, zone]+list_char_id)

    goutils.log2("DBG", "deploy_tw code="+str(process.returncode))
    if process.returncode==202:
        return 1, "Erreur en déployant en GT - pas de GT en cours"
    elif process.returncode==203:
        return 1, "Erreur en déployant en GT - le bot n'a pas tous les persos demandés"
    elif process.returncode==204:
        return 1, "Erreur en déployant en GT - au moins un perso est déjà déployé"
    elif process.returncode==205:
        return 1, "Erreur en déployant en GT - le bot n'a pas rejoint la GT"
    elif process.returncode!=0:
        return 1, "Erreur en déployant en GT - code="+str(process.returncode)

    return 0, "Le bot a posé "+str(list_defId)+" en " + zone

async def platoon_tb(allyCode, zone_name, platoon_id, list_defId):
    # Launch RPC command
    process_cmd = "/home/pi/GuionBot/warstats/platoons_tb.sh "+ str(allyCode)+" "+ zone_name+" "+ platoon_id+" "+" ".join(list_defId)
    goutils.log2("DBG", "process_params="+process_cmd)

    process = await asyncio.create_subprocess_shell(process_cmd)
    while process.returncode == None:
        goutils.log2("DBG", "waiting platoons_tb...")
        await asyncio.sleep(1)
    goutils.log2("DBG", "platoons_tb code="+str(process.returncode))

    if process.returncode==2:
        return 1, "Erreur en déployant les pelotons en BT - (usage)"
    elif process.returncode==100:
        return 1, "Erreur en déployant les pelotons en BT - (pas de BT en cours)"
    elif process.returncode==103:
        return 1, "Erreur en déployant les pelotons en BT - (emplacement déjà occupé)"
    elif process.returncode==101:
        return 1, "Erreur en déployant les pelotons en BT - (toon déjà déployé)"
    elif process.returncode==102:
        return 1, "Erreur en déployant les pelotons en BT - (rien à déployer)"
    elif process.returncode!=0:
        return 1, "Erreur en déployant les pelotons en BT - code="+str(process.returncode)

    return 0, "Le bot a posé "+str(list_defId)+" en " + zone_name

async def update_K1_players():
    url = "http://localhost:8000/leaderboard"
    params = {"ga_rank": "KYBER1"}
    req_data = json.dumps(params)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=req_data) as resp:
                goutils.log2("DBG", "leaderboard status="+str(resp.status))
                if resp.status==200:
                    leaderboard_json = await(resp.json())
                else:
                    return 1, "Cannot get leaderboard data from RPC", None

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

    #Loop through plalers and add/update them
    for player in leaderboard_json["player"]:
        await go.load_player(player["id"], 0, False)


####################################################
# IN: guild ID
# OUT: {"player name": [gnd attacks, gnd victories, ship attacks, ship victories, defense], ...}
####################################################
async def get_tw_participation(guild_id, force_update):
    dict_tw = godata.dict_tw

    err_code, err_txt, dict_guild = await get_guild_data(guild_id, force_update)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, err_txt, None

    err_code, err_txt, dict_events = await get_event_data(dict_guild, ["TW"], force_update)
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
async def get_raid_status(guild_id, target_percent, force_update):
    ec, et, dict_guild = await get_guild_data(guild_id, force_update)
    if ec!=0:
        return None, None, [], 0

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
        return None, None, [], 0

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
            score = 0

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
                    resp_data = await(resp.json())

                    if "err_code" in resp_data:
                        return resp_data["err_code"], resp_data["err_txt"]
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
                    metadata = await(resp.json())
                else:
                    return 1, "ERR during RPC metadata - code "+str(resp.status), None

    except asyncio.exceptions.TimeoutError as e:
        return 1, "Timeout lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ServerDisconnectedError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None
    except aiohttp.client_exceptions.ClientConnectorError as e:
        return 1, "Erreur lors de la requete RPC, merci de ré-essayer", None

    return 0, "", metadata


