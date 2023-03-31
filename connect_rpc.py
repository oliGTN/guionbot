import subprocess
import os
import json
import re
import threading
import time
import datetime
import inspect

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
    #goutils.log2("DBG", query)
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

def get_rpc_data(server_id, with_events, use_cache_data):
    #goutils.log2("DBG", "START get_rpc_data("+str(server_id)+", "+str(with_events)+", "+str(use_cache_data)+")")
    #if use_cache_data == False:
    #    print(inspect.stack())
    dict_bot_accounts = get_dict_bot_accounts()
    if not server_id in dict_bot_accounts:
        return 1, "Only available for "+str(list(dict_bot_accounts.keys()))+" but not for ["+str(server_id)+"]", None

    bot_androidId = dict_bot_accounts[server_id]["AndroidId"]
    goutils.log2("DBG", "bot account for "+str(server_id)+" is "+bot_androidId)

    guildName = get_guildName_from_id(server_id)

    if islocked_bot_account(server_id):
        use_cache_data = True
        goutils.log2("WAR", "the bot account is being used... using cached data")

    guild_file = "/home/pi/GuionBot/warstats/guild_"+bot_androidId+".json"
    acquire_sem(guild_file)
    if not use_cache_data:
        process = subprocess.run(["/home/pi/GuionBot/warstats/getguild.sh", bot_androidId])
        goutils.log2("DBG", "getguild code="+str(process.returncode))
    guild_json = json.load(open(guild_file, "r"))
    if "guild" in guild_json:
        dict_guild = guild_json["guild"]
    else:
        dict_guild = {}
    release_sem(guild_file)

    tbmap_file = "/home/pi/GuionBot/warstats/TBmapstats_"+bot_androidId+".json"
    acquire_sem(tbmap_file)
    if not use_cache_data:
        process = subprocess.run(["/home/pi/GuionBot/warstats/getmapstats.sh", bot_androidId,])
        goutils.log2("DBG", "getmapstats code="+str(process.returncode))
    if os.path.exists(tbmap_file):
        TBmapstats_json = json.load(open(tbmap_file, "r"))
        if "currentStat" in TBmapstats_json:
            dict_TBmapstats = TBmapstats_json["currentStat"]
        else:
            dict_TBmapstats = {}
    else:
        dict_TBmapstats = {}
    release_sem(tbmap_file)

    twmap_file = "/home/pi/GuionBot/warstats/TWmapstats_"+bot_androidId+".json"
    acquire_sem(twmap_file)
    if os.path.exists(twmap_file):
        TWmapstats_json = json.load(open(twmap_file, "r"))
        if "currentStat" in TWmapstats_json:
            dict_TWmapstats = TWmapstats_json["currentStat"]
        else:
            dict_TWmapstats = {}
    else:
        dict_TWmapstats = {}
    release_sem(twmap_file)

    if with_events:
        events_file = "/home/pi/GuionBot/warstats/events_"+bot_androidId+".json"
        acquire_sem(events_file)
        if not use_cache_data:
            process = subprocess.run(["/home/pi/GuionBot/warstats/getevents.sh", bot_androidId])
            goutils.log2("DBG", "getevents code="+str(process.returncode))
        if os.path.exists(events_file):
            events_json = json.load(open(events_file, "r"))
            if "event" in events_json:
                list_new_events = events_json["event"]
            else:
                list_new_events = []
        else:
            list_new_events = []
        release_sem(events_file)

        dict_events = {}
        dict_event_counts = {}
        for event in list_new_events:
            event_id = event["id"]
            channel_id = event["channelId"]
            event_ts = int(event["timestamp"])
            if channel_id.startswith("guild-{"):
                event_day_ts = int(event_ts/1000/86400)*86400*1000
                event_file_id = "GUILD_CHAT:"+str(event_day_ts)
            else:
                ret_re = re.search(".*\-\{.*\}\-(.*)\-.*", channel_id)
                event_file_id = ret_re.group(1)

            if not event_file_id in dict_events:
                fevents = "EVENTS/"+guildName+"_"+event_file_id+"_events.json"
                if os.path.exists(fevents):
                    acquire_sem(fevents)
                    f = open(fevents)
                    dict_events[event_file_id]=json.load(f)
                    f.close()
                    release_sem(fevents)
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
            acquire_sem(fevents)
            f=open(fevents, "w")
            f.write(json.dumps(dict_events[event_file_id], indent=4))
            f.close()
            release_sem(fevents)
    else:
        dict_events = {}

    if not use_cache_data:
        #log update time in DB - rounded to fix times (eg: always 00:05, 00:10 for 5 min period)
        query = "UPDATE guild_bot_infos SET bot_latestUpdate=FROM_UNIXTIME(ROUND(UNIX_TIMESTAMP(NOW())/60/bot_period_min,0)*60*bot_period_min) "
        query+= "WHERE server_id="+str(server_id)
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

    return 0, "", [dict_guild, dict_TBmapstats, dict_events]

def get_guild_data(txt_allyCode, use_cache_data):
    ec, et, dict_player = get_player_data(txt_allyCode, use_cache_data)
    if ec != 0:
        return 1, et, None

    if not "guildId" in dict_player:
        return 1, "ERR: ce joueur n'a pas de guilde", None

    guild_id = dict_player["guildId"]
    if guild_id == None or guild_id == "":
        return 1, "ERR: ce joueur n'a pas de guilde", None

    acquire_sem(guild_id)
    if not use_cache_data:
        process = subprocess.run(["/home/pi/GuionBot/warstats/getextguild.sh", guild_id])
        goutils.log2("DBG", "getextguild code="+str(process.returncode))

    guild_json = "/home/pi/GuionBot/warstats/GUILDS/"+guild_id+".json"
    if os.path.exists(guild_json):
        dict_guild = json.load(open(guild_json, "r"))["guild"]
    else:
        return 1, "ERR: impossible de trouver les données pour la guilde "+guild_id, None

    release_sem(guild_id)

    return 0, "", dict_guild


def get_player_data(txt_allyCode, use_cache_data):
    acquire_sem(txt_allyCode)
    
    if not use_cache_data:
        process = subprocess.run(["/home/pi/GuionBot/warstats/getplayer.sh", txt_allyCode])
        goutils.log2("DBG", "getplayer code="+str(process.returncode))

    player_json = "/home/pi/GuionBot/warstats/PLAYERS/"+txt_allyCode+".json"
    if os.path.exists(player_json):
        dict_player = json.load(open(player_json, "r"))
    else:
        return 1, "ERR: impossible de trouver les données pour le joueur "+txt_allyCode, None

    release_sem(txt_allyCode)

    return 0, "", dict_player

def get_bot_player_data(server_id, use_cache_data):
    dict_bot_accounts = get_dict_bot_accounts()
    if not server_id in dict_bot_accounts:
        return 1, "Only available for "+str(list(dict_bot_accounts.keys()))+" but not for ["+str(server_id)+"]", None

    bot_androidId = dict_bot_accounts[server_id]["AndroidId"]
    goutils.log2("DBG", "bot account for "+str(server_id)+" is "+bot_androidId)

    if islocked_bot_account(server_id):
        use_cache_data = True
        goutils.log2("WAR", "the bot account is being used... using cached data")

    acquire_sem(server_id)
    
    if not use_cache_data:
        process = subprocess.run(["/home/pi/GuionBot/warstats/getplayerbot.sh", bot_androidId])
        goutils.log2("DBG", "getplayerbot code="+str(process.returncode))

    dict_player = json.load(open("/home/pi/GuionBot/warstats/PLAYERS/bot_"+bot_androidId+".json", "r"))

    release_sem(server_id)

    return 0, "", dict_player

def join_raids(server_id):
    dict_bot_accounts = get_dict_bot_accounts()
    if not server_id in dict_bot_accounts:
        return 1, "Only available for "+str(list(dict_bot_accounts.keys()))+" but not for ["+str(server_id)+"]", None

    err_code, err_txt, rpc_data = get_rpc_data(server_id, False, True)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en se connectant au bot"

    dict_guild = rpc_data[0]
    if "raidStatus" in dict_guild:
        list_raids = [x["raidId"] for x in dict_guild["raidStatus"] if not x["hasPlayerParticipated"]]
        if len(list_raids) == 0:
            return 0, "Le bot a déjà rejoint tous les raids possibles"
    else:
        return 0, "Le bot a déjà rejoint tous les raids possibles"

    bot_androidId = dict_bot_accounts[server_id]["AndroidId"]
    goutils.log2("DBG", "bot account for "+str(server_id)+" is "+bot_androidId)

    process = subprocess.run(["/home/pi/GuionBot/warstats/joinraids.sh", bot_androidId])
    goutils.log2("DBG", "joinraids code="+str(process.returncode))
    if process.returncode!=0:
        return 1, "Erreur en rejoignant les raids - code="+str(process.returncode)

    return 0, "Le bot a rejoint "+str(list_raids)

def join_tw(server_id):
    dict_bot_accounts = get_dict_bot_accounts()
    if not server_id in dict_bot_accounts:
        return 1, "Only available for "+str(list(dict_bot_accounts.keys()))+" but not for ["+str(server_id)+"]", None

    err_code, err_txt, rpc_data = get_rpc_data(server_id, False, True)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en se connectant au bot"

    dict_guild = rpc_data[0]
    if "territoryWarStatus" in dict_guild:
        if "playerStatus" in dict_guild["territoryWarStatus"][0]:
            return 0, "Le bot a déjà rejoint la GT"
    else:
        return 0, "Aucune GT en cours"

    bot_androidId = dict_bot_accounts[server_id]["AndroidId"]
    goutils.log2("DBG", "bot account for "+str(server_id)+" is "+bot_androidId)

    process = subprocess.run(["/home/pi/GuionBot/warstats/join_tw.sh", bot_androidId])
    goutils.log2("DBG", "join_tw code="+str(process.returncode))
    if process.returncode!=0:
        return 1, "Erreur en rejoignant la GT - code="+str(process.returncode)

    return 0, "Le bot a rejoint la GT"

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

    err_code, err_txt, rpc_data = get_rpc_data(server_id, True, use_cache_data)

    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return '', None, None, 0

    dict_guild = rpc_data[0]
    mapstats_json = rpc_data[1]
    dict_events = rpc_data[2]
    guildName = dict_guild["profile"]["name"]

    dict_member_by_id = {}
    for member in dict_guild["member"]:
        dict_member_by_id[member["playerId"]] = member["playerName"]

    dict_unitsList = godata.get("unitsList_dict.json")

    if not "territoryBattleStatus" in dict_guild:
        goutils.log2("WAR", "["+guildName+"] no TB in progress")
        return '', None, None, 0

    for battleStatus in dict_guild["territoryBattleStatus"]:
        if battleStatus["selected"]:
            tb_id = battleStatus["definitionId"]
            tb_name = dict_tb[tb_id]
            active_round = tb_name + str(battleStatus["currentRound"])

            if active_round == 0:
                return '', None, None, 0

            for zone in battleStatus["reconZoneStatus"]:
                zone_name = zone["zoneStatus"]["zoneId"]

                if zone["zoneStatus"]["zoneState"] == "ZONEOPEN":
                    ret_re = re.search(".*_phase0(\d)_conflict0(\d)_recon01", zone_name)
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
                    platoon_name = dict_tb[zone_name] + "-" + platoon_num_txt
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
        return '', None, None, 0

    return active_round, dict_platoons, list_open_territories, 0

def parse_tw_opponent_teams(server_id, use_cache_data):
    dict_unitsList = godata.get("unitsList_dict.json")

    list_teams = [] # [['T1', 'Karcot', ['General Skywalker', 'CT-555 Fives, ...], <beaten>, <fights>],
                    #  ['T1', 'E80', [...]]]
    list_territories = [] # [['T1', <size>, <filled>, <victories>, <fails>], ...],

    err_code, err_txt, rpc_data = get_rpc_data(server_id, False, use_cache_data)

    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return '', None, None, 0

    dict_guild = rpc_data[0]
    mapstats_json = rpc_data[1]

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

    err_code, err_txt, rpc_data = get_rpc_data(server_id, True, use_cache_data)

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
            event_ts = int(event["timestamp"])
            if event_ts > chatLatest_ts:
                if "message" in event:
                    author = event["authorName"]
                    message = event["message"]
                    list_chat_events.append([event_ts, "\N{SPEECH BALLOON} "+author+" : "+message])
                else:
                    for data in event["data"]:
                        activity = data["activity"]
                        if activity["key"] == "GUILD_CHANNEL_ACTIVITY_UNIT_TIERUP":
                            author = activity["param"][0]["paramValue"][0]
                            unit_key = activity["param"][1]["key"]
                            if unit_key in FRE_FR:
                                unit_key = FRE_FR[unit_key]
                            gear_key = activity["param"][2]["key"]
                            if gear_key in FRE_FR:
                                gear_key = FRE_FR[gear_key]
                            list_chat_events.append([event_ts, author+" a augmenté l'équipement de "+unit_key+" au niveau "+gear_key])

                        elif activity["key"] == "GUILD_CHANNEL_ACTIVITY_ZETA_APPLIED"\
                        or activity["key"] == "GUILD_CHANNEL_ACTIVITY_OMICRON_APPLIED":
                            author = activity["param"][0]["paramValue"][0]
                            ability_key = activity["param"][1]["key"]
                            if ability_key in FRE_FR:
                                ability_key = FRE_FR[ability_key]
                            unit_key = activity["param"][2]["key"]
                            if unit_key in FRE_FR:
                                unit_key = FRE_FR[unit_key]

                            if "ZETA" in activity["key"]:
                                list_chat_events.append([event_ts, author+" a utilisé une amélioration zêta sur "+ability_key+" ("+unit_key+")"])
                            else:
                                list_chat_events.append([event_ts, author+" a utilisé une amélioration omicron sur "+ability_key+" ("+unit_key+")"])

                        elif activity["key"] == "GUILD_CHANNEL_ACTIVITY_UNIT_PROMOTED" \
                        or activity["key"] == "GUILD_CHANNEL_ACTIVITY_UNIT_ACTIVATED":
                            author = activity["param"][0]["paramValue"][0]
                            unit_key = activity["param"][1]["key"]
                            if unit_key in FRE_FR:
                                unit_key = FRE_FR[unit_key]
                            if "PROMOTED" in activity["key"]:
                                list_chat_events.append([event_ts, "\N{WHITE MEDIUM STAR} "+author+" vient de promouvoir "+unit_key+" à 7 étoiles"])
                            else:
                                list_chat_events.append([event_ts, "\N{OPEN LOCK} "+author+" vient de débloquer "+unit_key])

                        elif activity["key"] == "GUILD_CHANNEL_ACTIVITY_TB_STARTED":
                            tb_key = activity["param"][0]["key"]
                            if tb_key in FRE_FR:
                                tb_key = FRE_FR[tb_key]
                            phase = activity["param"][1]["paramValue"][0]
                            list_chat_events.append([event_ts, tb_key+" la phase "+phase+" a commencé"])

                        elif activity["key"] == "GUILD_CHANNEL_ACTIVITY_SIMMED_RAID_AUTO_SUMMONED":
                            raid_key = activity["param"][0]["key"]
                            if raid_key in FRE_FR:
                                raid_key = FRE_FR[raid_key]
                            list_chat_events.append([event_ts, "Le Raid : "+raid_key+" (simulation activée) vient de commencer, participez maintenant !"])

                        elif activity["key"] == "GUILD_CHANNEL_ACTIVITY_RAID_AUTO_SUMMONED_TU15":
                            raid_key = activity["param"][0]["key"]
                            if raid_key in FRE_FR:
                                raid_key = FRE_FR[raid_key]
                            list_chat_events.append([event_ts, "Le Raid : "+raid_key+" vient de commencer"])

                        elif activity["key"] == "GUILD_CHANNEL_ACTIVITY_DEMOTE":
                            demoted = activity["param"][0]["paramValue"][0]
                            demoter = activity["param"][1]["paramValue"][0]
                            list_chat_events.append([event_ts, demoted+" a été rétrogradé par "+demoter])

                        elif activity["key"] == "GUILD_CHANNEL_ACTIVITY_RAID_TALLY_COMPLETE":
                            list_chat_events.append([event_ts, "Les raids sont disponibles et peuvent être lancés"])

                        else:
                            goutils.log2("WAR", "Unknown key "+activity["key"])

    if len(list_chat_events)>0:
        list_chat_events = sorted(list_chat_events, key=lambda x:x[0])

        max_ts = list_chat_events[-1][0]
        query = "UPDATE guild_bot_infos SET chatLatest_ts="+str(max_ts)+" WHERE server_id="+str(server_id)
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

    return 0, "", [chatChan_id, list_chat_events]

def tag_tb_undeployed_players(server_id, use_cache_data):
    dict_tb=godata.dict_tb
    ec, et, tb_data = get_tb_status(server_id, "", False, use_cache_data)
    if ec!=0:
        return 1, et, None

    [dict_phase, dict_strike_zones, dict_tb_players, dict_open_zones] = tb_data

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

    return 0, "", lines_player

def get_tb_status(server_id, targets_zone_stars, compute_estimated_fights, use_cache_data):
    dict_tb=godata.dict_tb

    ec, et, rpc_data = get_rpc_data(server_id, True, use_cache_data)
    if ec!=0:
        return 1, et, None

    dict_guild=rpc_data[0]
    mapstats=rpc_data[1]
    dict_all_events=rpc_data[2]
    guildName = dict_guild["profile"]["name"]

    dict_members_by_id={}
    for member in dict_guild["member"]:
        dict_members_by_id[member["playerId"]] = member["playerName"]

    tb_ongoing=False
    if "territoryBattleStatus" in dict_guild:
        for battleStatus in dict_guild["territoryBattleStatus"]:
            if battleStatus["selected"]:
                battle_id = battleStatus["instanceId"]
                goutils.log2("DBG", "Selected TB = "+battle_id)
                tb_ongoing=True
                tb_round = battleStatus["currentRound"]
                tb_type = battleStatus["definitionId"]
                tb_round_endTime = int(battleStatus["currentRoundEndTime"])
                tb_round_startTime = tb_round_endTime - dict_tb[tb_type]["PhaseDuration"]
                if battle_id in dict_all_events:
                    dict_events=dict_all_events[battle_id]
                else:
                    dict_events={}
                break

    if not tb_ongoing:
        return 1, "No TB on-going", None

    query = "SELECT name, char_gp, ship_gp FROM players WHERE guildName='"+guildName.replace("'", "''")+"'"
    goutils.log2("DBG", query)
    list_playername_gp = connect_mysql.get_table(query)

    dict_tb_players = {}
    dict_strike_zones = {}
    dict_open_zones = {}
    dict_phase = {"id": battle_id, "round": tb_round, "type": tb_type, "name": dict_tb[tb_type]["name"]}

    for playername_gp in list_playername_gp:
        dict_tb_players[playername_gp[0]] = {}
        dict_tb_players[playername_gp[0]]["char_gp"] = playername_gp[1]
        dict_tb_players[playername_gp[0]]["ship_gp"] = playername_gp[2]
        dict_tb_players[playername_gp[0]]["mix_gp"] = playername_gp[1] + playername_gp[2]
        dict_tb_players[playername_gp[0]]["score"] = {"deployedShips": 0,
                                                      "deployedChars": 0,
                                                      "deployedMix": 0,
                                                      "deployed": 0,
                                                      "Platoons": 0,
                                                      "strikes": 0} 
        dict_tb_players[playername_gp[0]]["strikes"] = []

    for zone in battleStatus["conflictZoneStatus"]:
        if zone["zoneStatus"]["zoneState"] == "ZONEOPEN":
            zone_name = zone["zoneStatus"]["zoneId"]
            zone_score = int(zone["zoneStatus"]["score"])
            dict_open_zones[zone_name] = {"score": zone_score}

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
            dict_strike_zones[strike_name]["estimatedScore"] = 0
            dict_strike_zones[strike_name]["estimatedScore"] = 0
            dict_strike_zones[strike_name]["eventStrikes"] = 0
            dict_strike_zones[strike_name]["eventStrikeScore"] = 0

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
                zone_name = event_data["activity"][zoneData_key]["zoneId"]
                strike_name = event_data["activity"][zoneData_key]["sourceZoneId"]
                if zone_name in dict_open_zones:
                    score = int(event_data["activity"][zoneData_key]["scoreDelta"])
                    dict_tb_players[playerName]["score"]["strikes"] += score

                    dict_strike_zones[strike_name]["eventStrikes"] += 1
                    dict_strike_zones[strike_name]["eventStrikeScore"] += score

                    strike_shortname="_".join(strike_name.split("_")[-2:])
                    dict_tb_players[playerName]["strikes"].append(strike_shortname)

            elif "RECON_CONTRIBUTION" in event_key:
                zone_name = event_data["activity"][zoneData_key]["zoneId"]
                if zone_name in dict_open_zones:
                    score = int(event_data["activity"][zoneData_key]["scoreDelta"])
                    dict_tb_players[playerName]["score"]["Platoons"] += score

            elif "DEPLOY" in event_key:
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

    for mapstat in mapstats:
        if mapstat["mapStatId"] == "strike_attempt_round_"+str(tb_round):
            if "playerStat" in mapstat:
                for playerstat in mapstat["playerStat"]:
                    member_id = playerstat["memberId"]
                    playerName = dict_members_by_id[member_id]
                    if not playerName in dict_tb_players:
                        continue

                    attempts = int(playerstat["score"])
                    while len(dict_tb_players[playerName]["strikes"]) < attempts:
                        dict_tb_players[playerName]["strikes"].append("?")

        elif mapstat["mapStatId"] == "power_round_"+str(tb_round):
            if "playerStat" in mapstat:
                for playerstat in mapstat["playerStat"]:
                    member_id = playerstat["memberId"]
                    playerName = dict_members_by_id[member_id]
                    if not playerName in dict_tb_players:
                        #should not happen unless new player and until API resynchronizes
                        continue

                    score = int(playerstat["score"])
                    dict_tb_players[playerName]["score"]["deployed"] = score
                    if dict_tb_players[playerName]["score"]["deployed"] != dict_tb_players[playerName]["score"]["deployedMix"]:
                        goutils.log2("WAR", "Event deployment does not match total deployment for "+playerName)
                        goutils.log2("WAR", "("+str(dict_tb_players[playerName]["score"]["deployedMix"])+" vs "+str(dict_tb_players[playerName]["score"]["deployed"])+")")
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
    remaining_to_play_ships = 0
    remaining_to_play_chars = 0
    remaining_to_play_mix = 0
    lines_player = []
    for playerName in dict_tb_players:
        if "ships" in list_deployment_types:
            ratio_deploy_ships = dict_tb_players[playerName]["score"]["deployedShips"] / dict_tb_players[playerName]["ship_gp"]
            if ratio_deploy_ships < 0.99:
                remaining_to_play_ships += 1
            else:
                ratio_deploy_ships = 1

        if "chars" in list_deployment_types:
            ratio_deploy_chars = dict_tb_players[playerName]["score"]["deployedChars"] / dict_tb_players[playerName]["char_gp"]
            if ratio_deploy_chars < 0.99:
                remaining_to_play_chars += 1
            else:
                ratio_deploy_chars = 1

        if "mix" in list_deployment_types:
            ratio_deploy_mix = dict_tb_players[playerName]["score"]["deployedMix"] / dict_tb_players[playerName]["mix_gp"]
            if ratio_deploy_mix < 0.99:
                remaining_to_play_mix += 1
            else:
                ratio_deploy_mix = 1

        for zone in dict_open_zones:
            for strike in dict_tb[zone]["strikes"]:
                strike_shortname = "conflict0"+zone[-1]+"_"+strike
                strike_name = zone+"_"+strike
                if not strike_shortname in dict_tb_players[playerName]["strikes"]:
                    strike_fights = dict_strike_zones[strike_name]["participation"]
                    strike_score = dict_strike_zones[strike_name]["eventStrikeScore"]

                    if strike_fights > 0:
                        strike_average_score = strike_score / strike_fights
                    else:
                        strike_average_score = 0

                    if dict_tb[zone]["type"]=="ships" and ratio_deploy_ships<0.99:
                        dict_strike_zones[strike_name]["estimatedStrikes"] += 1
                        dict_strike_zones[strike_name]["estimatedScore"] += strike_average_score
                    elif dict_tb[zone]["type"]=="chars" and ratio_deploy_chars<0.99:
                        dict_strike_zones[strike_name]["estimatedStrikes"] += 1
                        dict_strike_zones[strike_name]["estimatedScore"] += strike_average_score
                    elif dict_tb[zone]["type"]=="mix" and ratio_deploy_mix<0.99:
                        dict_strike_zones[strike_name]["estimatedStrikes"] += 1
                        dict_strike_zones[strike_name]["estimatedScore"] += strike_average_score

    dict_phase["shipPlayers"] = remaining_to_play_ships
    dict_phase["charPlayers"] = remaining_to_play_chars
    dict_phase["mixPlayers"] = remaining_to_play_mix

    #compute zone stats apart for deployments
    for zone_name in dict_open_zones:
        current_score = dict_open_zones[zone_name]["score"]

        estimated_strike_score = 0
        estimated_strike_fights = 0
        max_strike_score = 0
        cur_strike_score = 0
        cur_strike_fights = {}
        for strike in dict_tb[zone_name]["strikes"]:
            strike_name = zone_name + "_" + strike
            if compute_estimated_fights:
                estimated_strike_fights += dict_strike_zones[strike_name]["estimatedStrikes"]
                estimated_strike_score += dict_strike_zones[strike_name]["estimatedScore"]
            max_strike_score += dict_strike_zones[strike_name]["maxPossibleScore"]

            cur_strike_fights[strike] = dict_strike_zones[strike_name]["participation"]
            cur_strike_score += dict_strike_zones[strike_name]["eventStrikeScore"]

        dict_open_zones[zone_name]["strikeScore"] = cur_strike_score
        dict_open_zones[zone_name]["strikeFights"] = cur_strike_fights
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
        #split the zoes by type
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

        for target_zone_stars in targets_zone_stars.split(" "):
            target_zone_name = target_zone_stars.split(":")[0]
            target_stars = int(target_zone_stars.split(":")[1])

            if target_zone_name in dict_tb[tb_type]["zoneNames"]:
                conflict = dict_tb[tb_type]["zoneNames"][target_zone_name]
            else:
                return 1, "zone inconnue: " + target_zone_name + " " + str(list(dict_tb[tb_type]["zoneNames"].keys())), None

            for zone_name in dict_open_zones:
                if zone_name.endswith(conflict):
                    break

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

    return 0, "", [dict_phase, dict_strike_zones, dict_tb_players, dict_open_zones]
##########################################"
# OUT: dict_territory_scores = {"GLS-P3-top": 24500000, ...}
# OUT: tb_active_round = 3
##########################################"
def get_tb_guild_scores(server_id, use_cache_data):
    dict_tb = godata.dict_tb
    ec, et, tb_data = get_tb_status(server_id, "", False, use_cache_data)
    if ec!=0:
        return {}, ""

    [dict_phase, dict_strike_zones, dict_tb_players, dict_open_zones] = tb_data
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
        dict_territory_scores[zone_name] = zone_score

    return dict_territory_scores, active_round

########################################
# get_tw_status
# get statues of territories in attack and def
# list_teams: [["T1", "Karcot", ["General Skywalker", "CT-5555 Fives", ...], <is_beaten>, <fights>],
#              ["T1", "JeanLuc"...
# list_territories: [["T1", <size>, <filled>, <victories>, <fails>, <commandMsg>], ...]
########################################
def get_tw_status(server_id, use_cache_data):
    dict_tw=godata.dict_tw

    ec, et, rpc_data = get_rpc_data(server_id, False, use_cache_data)
    if ec!=0:
        return 1, et, None

    dict_guild=rpc_data[0]
    mapstats=rpc_data[1]
    guildName = dict_guild["profile"]["name"]

    dict_members_by_id={}
    for member in dict_guild["member"]:
        dict_members_by_id[member["playerId"]] = member["playerName"]

    tw_ongoing=False
    if "territoryWarStatus" in dict_guild:
        for battleStatus in dict_guild["territoryWarStatus"]:
            if "awayGuild" in battleStatus:
                    tw_ongoing = True
                    cur_tw = battleStatus

    if not tw_ongoing:
        return False, [[], []], [[], []]

    list_teams = {}
    list_territories = {}

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
                        list_chars = [c["unitDefId"].split(":")[0] for c in squad["squad"]["cell"]]
                        is_beaten = (squad["squadStatus"]=="SQUADDEFEATED")
                        fights = squad["successfulDefends"]
                        list_teams[guild].append([zone_shortname, player_name, list_chars, is_beaten, fights])

                        if is_beaten:
                            victories+=1
                            fails+=(fights-1)
                        else:
                            fails+=fights

                zone_size = zone["squadCapacity"]
                filled = zone["squadCount"]
                if "commandMessage" in zone["zoneStatus"]:
                    commandMsg = zone["zoneStatus"]["commandMessage"]
                else:
                    commandMsg = None
                list_territories[guild].append([zone_shortname, zone_size, filled, victories, fails, commandMsg])

    return True, [list_teams["homeGuild"], list_territories["homeGuild"]], \
                 [list_teams["awayGuild"], list_territories["awayGuild"]]

def get_tw_active_players(server_id):
    ec, et, rpc_data = get_rpc_data(server_id, False, use_cache_data)
    if ec!=0:
        return 1, et, None

    dict_guild=rpc_data[0]
    dict_members={}
    list_active_players = []
    for member in dict_guild["member"]:
        dict_members[member["playerId"]] = member["playerName"]
    for member in dict_guild["territoryWarStatus"]["optedInMember"]:
        list_active_players.append(dict_members[member["memberId"]])

    return 0, "", list_active_players

def deploy_tb(server_id, zone, list_defId):
    dict_bot_accounts = get_dict_bot_accounts()
    if not server_id in dict_bot_accounts:
        return 1, "Only available for "+str(list(dict_bot_accounts.keys()))+" but not for ["+str(server_id)+"]", None

    err_code, err_txt, rpc_data = get_rpc_data(server_id, False, True)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en se connectant au bot"
    dict_guild = rpc_data[0]

    err_code, err_txt, rpc_data = get_bot_player_data(server_id, True)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en se connectant au bot"
    dict_player = rpc_data

    bot_androidId = dict_bot_accounts[server_id]["AndroidId"]

    list_char_id = []
    for unit in dict_player["rosterUnit"]:
        full_defId = unit["definitionId"]
        defId = full_defId.split(":")[0]
        if defId in list_defId:
            list_char_id.append(unit["id"])

    if len(list_char_id) == 0:
        return 1, "Plus rien à déployer"

    process = subprocess.run(["/home/pi/GuionBot/warstats/deploy_tb.sh", bot_androidId, zone]+list_char_id)
    goutils.log2("DBG", "deploy_tb code="+str(process.returncode))
    if process.returncode!=0 and process.returncode<10:
        return 1, "Erreur en déployant en TB - code="+str(process.returncode)

    return 0, "Le bot a déployé "+str(process.returnCode)+" en " + zone

def deploy_tw(server_id, zone, list_defId):
    dict_bot_accounts = get_dict_bot_accounts()
    if not server_id in dict_bot_accounts:
        return 1, "Only available for "+str(list(dict_bot_accounts.keys()))+" but not for ["+str(server_id)+"]", None

    err_code, err_txt, rpc_data = get_rpc_data(server_id, False, True)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en se connectant au bot"
    dict_guild = rpc_data[0]

    err_code, err_txt, rpc_data = get_bot_player_data(server_id, True)
    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return 1, "Erreur en se connectant au bot"
    dict_player = rpc_data

    bot_androidId = dict_bot_accounts[server_id]["AndroidId"]

    dict_roster = {}
    for unit in dict_player["rosterUnit"]:
        full_defId = unit["definitionId"]
        defId = full_defId.split(":")[0]
        dict_roster[defId] = unit

    list_char_id = []
    for defId in list_defId:
        list_char_id.append(dict_roster[defId]["id"])
    if len(list_char_id) != 5:
        goutils.log2("ERR", "Need 5 units but found "+str(list_char_id))
        return 1, "ERR: il faut exactement 5 persos"

    process = subprocess.run(["/home/pi/GuionBot/warstats/deploy_tw.sh", bot_androidId, zone]+list_char_id)
    goutils.log2("DBG", "deploy_tw code="+str(process.returncode))
    if process.returncode!=0:
        return 1, "Erreur en déployant en GT - code="+str(process.returncode)

    return 0, "Le bot a posé "+str(list_defId)+" en " + zone
