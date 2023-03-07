import subprocess
import os
import json
import re
import threading
import time
import datetime

import goutils
import data as godata
import connect_mysql

dict_sem={}
def acquire_sem(id):
    if not id in dict_sem:
        dict_sem[id] = threading.Semaphore()
    dict_sem[id].acquire()

def release_sem(id):
    dict_sem[id].release()

def get_dict_bot_accounts():
    query = "SELECT server_id, bot_android_id, bot_locked_until FROM guild_bot_infos where bot_android_id != ''"
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_table(query)

    ret_dict = {}
    if db_data != None:
        for line in db_data:
            ret_dict[line[0]] = {"AndroidId": line[1], "LockedUntil": line[2]}

    return ret_dict

def get_guildName_from_id(server_id):
    query = "SELECT name from guilds JOIN guild_bot_infos on guilds.id = guild_bot_infos.guild_id WHERE server_id="+str(server_id)
    goutils.log2("DBG", query)
    return connect_mysql.get_value(query)

def bot_account_until(server_id, until_seconds):
    dict_bot_accounts = get_dict_bot_accounts()
    if not server_id in dict_bot_accounts:
        return 1, "Only available for "+str(list(dict_bot_accounts.keys()))+" but not for ["+str(server_id)+"]"

    locked_until_txt = datetime.datetime.fromtimestamp(int(time.time())+until_seconds).strftime("%Y-%m-%d %H:%M:%S")
    query = "UPDATE guild_bot_infos SET bot_locked_until='"+locked_until_txt+"' WHERE server_id="+str(server_id)
    goutils.log2("DBG", query)
    connect_mysql.simple_execute(query)

    return 0, ""

def lock_bot_account(server_id):
    return bot_account_until(server_id, 3600)

def unlock_bot_account(server_id):
    return bot_account_until(server_id, 0)

def islocked_bot_account(guildName):
    dict_bot_accounts = get_dict_bot_accounts()
    locked_until_ts = datetime.datetime.timestamp(dict_bot_accounts[guildName]["LockedUntil"])
    is_locked = int(locked_until_ts) > int(time.time())
    return is_locked

def get_rpc_data(server_id, use_cache_data):
    dict_bot_accounts = get_dict_bot_accounts()
    if not server_id in dict_bot_accounts:
        return 1, "Only available for "+str(list(dict_bot_accounts.keys()))+" but not for ["+str(server_id)+"]", None

    bot_androidId = dict_bot_accounts[server_id]["AndroidId"]
    goutils.log2("DBG", "bot account for "+str(server_id)+" is "+bot_androidId)

    guildName = get_guildName_from_id(server_id)

    if islocked_bot_account(server_id):
        use_cache_data = True
        goutils.log2("WAR", "the bot account is being used... using cached data")

    goutils.log2("DBG", "try to acquire sem in p="+str(os.getpid())+", t="+str(threading.get_native_id()))
    acquire_sem(server_id)
    goutils.log2("DBG", "sem acquired sem in p="+str(os.getpid())+", t="+str(threading.get_native_id()))

    if not use_cache_data:
        process = subprocess.run(["/home/pi/GuionBot/warstats/getguild.sh", bot_androidId])
        goutils.log2("DBG", "getguild code="+str(process.returncode))

    guild_json = json.load(open("/home/pi/GuionBot/warstats/guild_"+bot_androidId+".json", "r"))
    if "Guild" in guild_json:
        dict_guild = guild_json["Guild"]
    else:
        dict_guild = {}

    if not use_cache_data:
        process = subprocess.run(["/home/pi/GuionBot/warstats/getevents.sh", bot_androidId])
        goutils.log2("DBG", "getevents code="+str(process.returncode))
    if os.path.exists("/home/pi/GuionBot/warstats/events_"+bot_androidId+".json"):
        events_json = json.load(open("/home/pi/GuionBot/warstats/events_"+bot_androidId+".json", "r"))
        if "Event" in events_json:
            dict_new_events = events_json["Event"]
        else:
            dict_new_events = {}
    else:
        dict_new_events = {}

    if not use_cache_data:
        process = subprocess.run(["/home/pi/GuionBot/warstats/getmapstats.sh", bot_androidId, "TB"])
        goutils.log2("DBG", "getmapstats code="+str(process.returncode))
    if os.path.exists("/home/pi/GuionBot/warstats/TBmapstats_"+bot_androidId+".json"):
        TBmapstats_json = json.load(open("/home/pi/GuionBot/warstats/TBmapstats_"+bot_androidId+".json", "r"))
        if "CurrentStat" in TBmapstats_json:
            dict_TBmapstats = TBmapstats_json["CurrentStat"]
        else:
            dict_TBmapstats = {}
    else:
        dict_TBmapstats = {}

    if not use_cache_data:
        process = subprocess.run(["/home/pi/GuionBot/warstats/getmapstats.sh", bot_androidId, "TW"])
        goutils.log2("DBG", "getmapstats code="+str(process.returncode))
    if os.path.exists("/home/pi/GuionBot/warstats/TWmapstats_"+bot_androidId+".json"):
        TWmapstats_json = json.load(open("/home/pi/GuionBot/warstats/TWmapstats_"+bot_androidId+".json", "r"))
        if "CurrentStat" in TWmapstats_json:
            dict_TWmapstats = TWmapstats_json["CurrentStat"]
        else:
            dict_TWmapstats = {}
    else:
        dict_TWmapstats = {}

    if not use_cache_data:
        #log update time in DB - rounded to fix times (eg: always 00:05, 00:10 for 5 min period)
        query = "UPDATE guild_bot_infos SET bot_latestUpdate=FROM_UNIXTIME(ROUND(UNIX_TIMESTAMP(NOW())/60/bot_period_min,0)*60*bot_period_min) "
        query+= "WHERE server_id="+str(server_id)
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

    dict_events = {}
    dict_event_counts = {}
    for event in dict_new_events:
        event_id = event["Id"]
        channel_id = event["ChannelId"]
        event_ts = int(event["Timestamp"])
        if channel_id.startswith("guild-{"):
            event_day_ts = int(event_ts/1000/86400)*86400*1000
            event_file_id = "GUILD_CHAT:"+str(event_day_ts)
        else:
            ret_re = re.search(".*\-\{.*\}\-(.*)\-.*", channel_id)
            event_file_id = ret_re.group(1)

        if not event_file_id in dict_events:
            fevents = "EVENTS/"+guildName+"_"+event_file_id+"_events.json"
            if os.path.exists(fevents):
                f = open(fevents)
                dict_events[event_file_id]=json.load(f)
                f.close()
            else:
                dict_events[event_file_id]={}

            dict_event_counts[event_file_id]=0

        if not event_id in dict_events[event_file_id]:
            dict_event_counts[event_file_id]+=1
            dict_events[event_file_id][event_id] = event

    if max(dict_event_counts.values()) > 0:
        goutils.log2("INFO", "New events: "+str(dict_event_counts))

    for event_file_id in dict_events:
        fevents = "EVENTS/"+guildName+"_"+event_file_id+"_events.json"
        f=open(fevents, "w")
        f.write(json.dumps(dict_events[event_file_id], indent=4))
        f.close()

    goutils.log2("DBG", "try to release sem in p="+str(os.getpid())+", t="+str(threading.get_native_id()))
    release_sem(server_id)
    goutils.log2("DBG", "sem released sem in p="+str(os.getpid())+", t="+str(threading.get_native_id()))

    return 0, "", [dict_guild, dict_TBmapstats, dict_events]

def parse_tb_platoons(server_id, use_cache_data):
    active_round = "" # GLS4"
    dict_platoons = {} #key="GLS1-mid-2", value={key=perso, value=[player, player...]}
    list_open_territories = [0, 0, 0] # [4, 3, 3]

    dict_tb = {}
    dict_tb["t04D"] = "GLS"
    dict_tb["geonosis_republic_phase01_conflict01_recon01"] = "GLS1-top"
    dict_tb["geonosis_republic_phase01_conflict02_recon01"] = "GLS1-mid"
    dict_tb["geonosis_republic_phase01_conflict03_recon01"] = "GLS1-bottom"
    dict_tb["geonosis_republic_phase02_conflict01_recon01"] = "GLS2-top"
    dict_tb["geonosis_republic_phase02_conflict02_recon01"] = "GLS2-mid"
    dict_tb["geonosis_republic_phase02_conflict03_recon01"] = "GLS2-bottom"
    dict_tb["geonosis_republic_phase03_conflict01_recon01"] = "GLS3-top"
    dict_tb["geonosis_republic_phase03_conflict02_recon01"] = "GLS3-mid"
    dict_tb["geonosis_republic_phase03_conflict03_recon01"] = "GLS3-bottom"
    dict_tb["geonosis_republic_phase04_conflict01_recon01"] = "GLS4-top"
    dict_tb["geonosis_republic_phase04_conflict02_recon01"] = "GLS4-mid"
    dict_tb["geonosis_republic_phase04_conflict03_recon01"] = "GLS4-bottom"

    dict_tb["t05D"] = "ROTE"
    dict_tb["tb3_mixed_phase01_conflict01_recon01"] = "ROTE1-LS"
    dict_tb["tb3_mixed_phase01_conflict02_recon01"] = "ROTE1-DS"
    dict_tb["tb3_mixed_phase01_conflict03_recon01"] = "ROTE1-MS"
    dict_tb["tb3_mixed_phase02_conflict01_recon01"] = "ROTE2-LS"
    dict_tb["tb3_mixed_phase02_conflict02_recon01"] = "ROTE2-DS"
    dict_tb["tb3_mixed_phase02_conflict03_recon01"] = "ROTE2-MS"
    dict_tb["tb3_mixed_phase03_conflict01_recon01"] = "ROTE3-LS"
    dict_tb["tb3_mixed_phase03_conflict02_recon01"] = "ROTE3-DS"
    dict_tb["tb3_mixed_phase03_conflict03_recon01"] = "ROTE3-MS"
    dict_tb["tb3_mixed_phase04_conflict01_recon01"] = "ROTE4-LS"
    dict_tb["tb3_mixed_phase04_conflict02_recon01"] = "ROTE4-DS"
    dict_tb["tb3_mixed_phase04_conflict03_recon01"] = "ROTE4-MS"
    dict_tb["tb3_mixed_phase05_conflict01_recon01"] = "ROTE5-LS"
    dict_tb["tb3_mixed_phase05_conflict02_recon01"] = "ROTE5-DS"
    dict_tb["tb3_mixed_phase05_conflict03_recon01"] = "ROTE5-MS"
    dict_tb["tb3_mixed_phase06_conflict01_recon01"] = "ROTE6-LS"
    dict_tb["tb3_mixed_phase06_conflict02_recon01"] = "ROTE6-DS"
    dict_tb["tb3_mixed_phase06_conflict03_recon01"] = "ROTE6-MS"

    err_code, err_txt, rpc_data = get_rpc_data(server_id, use_cache_data)

    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return '', None, None, 0

    dict_guild = rpc_data[0]
    mapstats_json = rpc_data[1]
    dict_events = rpc_data[2]
    guildName = dict_guild["Profile"]["Name"]

    dict_member_by_id = {}
    for member in dict_guild["Member"]:
        dict_member_by_id[member["PlayerId"]] = member["PlayerName"]

    dict_unitsList = godata.get("unitsList_dict.json")

    if not "TerritoryBattleStatus" in dict_guild:
        goutils.log2("WAR", "["+guildName+"] no TB in progress")
        return '', None, None, 0

    for battleStatus in dict_guild["TerritoryBattleStatus"]:
        if battleStatus["Selected"]:
            tb_id = battleStatus["DefinitionId"]
            tb_name = dict_tb[tb_id]
            active_round = tb_name + str(battleStatus["CurrentRound"])

            if active_round == 0:
                return '', None, None, 0

            for zone in battleStatus["ReconZoneStatus"]:
                zone_name = zone["ZoneStatus"]["ZoneId"]

                if zone["ZoneStatus"]["ZoneState"] == "ZONEOPEN":
                    ret_re = re.search(".*_phase0(\d)_conflict0(\d)_recon01", zone_name)
                    zone_position = int(ret_re.group(2))
                    zone_phase = int(ret_re.group(1))
                    list_open_territories[zone_position-1] = zone_phase
                if not "Platoon" in zone:
                    continue

                for platoon in zone["Platoon"]:
                    platoon_num = int(platoon["Id"][-1])
                    if tb_name == "ROTE":
                        platoon_num_corrected = 7 - platoon_num
                    else:
                        platoon_num_corrected = platoon_num

                    platoon_num_txt = str(platoon_num_corrected)
                    platoon_name = dict_tb[zone_name] + "-" + platoon_num_txt
                    dict_platoons[platoon_name] = {}

                    for squad in platoon["Squad"]:
                        for unit in squad["Unit"]:
                            unit_id = unit["UnitIdentifier"]
                            unit_defId = unit_id.split(":")[0]
                            unit_name = dict_unitsList[unit_defId]["nameKey"]

                            if not unit_name in dict_platoons[platoon_name]:
                                dict_platoons[platoon_name][unit_name] = []

                            player_id = unit["MemberId"]
                            if player_id != '':
                                player_name = dict_member_by_id[player_id]
                                dict_platoons[platoon_name][unit_name].append(player_name)
                            else:
                                dict_platoons[platoon_name][unit_name].append('')

    if max(list_open_territories)==0:
        return '', None, None, 0

    return active_round, dict_platoons, list_open_territories, 0

def parse_tw_opponent_teams(server_id, use_cache_data):
    dict_unitsList = godata.get("unitsList_dict.json")

    list_teams = [] # [['T1', 'Karcot', ['General Skywalker', 'CT-555 Fives, ...], <beaten>, <fights>],
                    #  ['T1', 'E80', [...]]]
    list_territories = [] # [['T1', <size>, <filled>, <victories>, <fails>], ...],

    err_code, err_txt, rpc_data = get_rpc_data(server_id, use_cache_data)

    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return '', None, None, 0

    dict_guild = rpc_data[0]
    mapstats_json = rpc_data[1]
    dict_events = rpc_data[2]

    return 0, "", [list_teams, list_territories]

def get_guildChat_messages(server_id, use_cache_data):
    FRE_FR = godata.get('FRE_FR.json')

    query = "SELECT bot_android_id, chatChan_id, chatLatest_ts FROM guild_bot_infos WHERE server_id="+str(server_id)
    goutils.log2("DBG", query)
    line = connect_mysql.get_line(query)
    if line == None:
        return 1, "INFO: no DB data for server "+str(server_id), None
    
    bot_android_id = line[0]
    chatChan_id = line[1]
    chatLatest_ts = line[2]

    if bot_android_id == '':
        return 1, "ERR: no RPC bot for guild "+str(server_id), None
    if chatChan_id == 0:
        return 1, "ERR: no discord chat channel for guild "+str(server_id), None

    err_code, err_txt, rpc_data = get_rpc_data(server_id, use_cache_data)

    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return '', None, None, 0

    dict_guild = rpc_data[0]
    mapstats_json = rpc_data[1]
    dict_events = rpc_data[2]

    list_chat_events = []
    for event_group_id in dict_events:
        if not event_group_id.startswith("GUILD_CHAT"):
            continue
        event_group = dict_events[event_group_id]
        for event_id in event_group:
            event = event_group[event_id]
            event_ts = int(event["Timestamp"])
            if event_ts > chatLatest_ts:
                if "Message" in event:
                    author = event["AuthorName"]
                    message = event["Message"]
                    list_chat_events.append([event_ts, "\N{SPEECH BALLOON} "+author+" : "+message])
                else:
                    for data in event["Data"]:
                        activity = data["Activity"]
                        if activity["Key"] == "GUILD_CHANNEL_ACTIVITY_UNIT_TIERUP":
                            author = activity["Param"][0]["ParamValue"][0]
                            unit_key = activity["Param"][1]["Key"]
                            if unit_key in FRE_FR:
                                unit_key = FRE_FR[unit_key]
                            gear_key = activity["Param"][2]["Key"]
                            if gear_key in FRE_FR:
                                gear_key = FRE_FR[gear_key]
                            list_chat_events.append([event_ts, author+" a augmenté l'équipement de "+unit_key+" au niveau "+gear_key])

                        if activity["Key"] == "GUILD_CHANNEL_ACTIVITY_ZETA_APPLIED"\
                        or activity["Key"] == "GUILD_CHANNEL_ACTIVITY_OMICRON_APPLIED":
                            author = activity["Param"][0]["ParamValue"][0]
                            ability_key = activity["Param"][1]["Key"]
                            if ability_key in FRE_FR:
                                ability_key = FRE_FR[ability_key]
                            unit_key = activity["Param"][2]["Key"]
                            if unit_key in FRE_FR:
                                unit_key = FRE_FR[unit_key]

                            if "ZETA" in activity["Key"]:
                                list_chat_events.append([event_ts, author+" a utilisé une amélioration zêta sur "+ability_key+" ("+unit_key+")"])
                            else:
                                list_chat_events.append([event_ts, author+" a utilisé une amélioration omicron sur "+ability_key+" ("+unit_key+")"])

                        if activity["Key"] == "GUILD_CHANNEL_ACTIVITY_UNIT_PROMOTED" \
                        or activity["Key"] == "GUILD_CHANNEL_ACTIVITY_UNIT_ACTIVATED":
                            author = activity["Param"][0]["ParamValue"][0]
                            unit_key = activity["Param"][1]["Key"]
                            if unit_key in FRE_FR:
                                unit_key = FRE_FR[unit_key]
                            if "PROMOTED" in activity["Key"]:
                                list_chat_events.append([event_ts, "\N{WHITE MEDIUM STAR} "+author+" vient de promouvoir "+unit_key+" à 7 étoiles"])
                            else:
                                list_chat_events.append([event_ts, "\N{OPEN LOCK} "+author+" vient de débloquer "+unit_key])

                        if activity["Key"] == "GUILD_CHANNEL_ACTIVITY_TB_STARTED":
                            tb_key = activity["Param"][0]["Key"]
                            if tb_key in FRE_FR:
                                tb_key = FRE_FR[tb_key]
                            phase = activity["Param"][1]["ParamValue"][0]
                            list_chat_events.append([event_ts, tb_key+" la phase "+phase+" a commencé"])
                        if activity["Key"] == "GUILD_CHANNEL_ACTIVITY_SIMMED_RAID_AUTO_SUMMONED":
                            raid_key = activity["Param"][0]["Key"]
                            if raid_key in FRE_FR:
                                raid_key = FRE_FR[raid_key]
                            list_chat_events.append([event_ts, "Le Raid : "+raid+" (simulation activée) vient de commencer, participez maintenant !"])

                        if activity["Key"] == "GUILD_CHANNEL_ACTIVITY_DEMOTE":
                            demoted = activity["Param"][0]["ParamValue"][0]
                            demoter = activity["Param"][1]["ParamValue"][0]
                            list_chat_events.append([event_ts, demoted+" a été rétrogradé par "+demoter])

    if len(list_chat_events)>0:
        list_chat_events = sorted(list_chat_events, key=lambda x:x[0])

        max_ts = list_chat_events[-1][0]
        query = "UPDATE guild_bot_infos SET chatLatest_ts="+str(max_ts)+" WHERE server_id="+str(server_id)
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

    return 0, "", [chatChan_id, list_chat_events]

