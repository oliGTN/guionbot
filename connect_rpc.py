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

                        elif activity["Key"] == "GUILD_CHANNEL_ACTIVITY_ZETA_APPLIED"\
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

                        elif activity["Key"] == "GUILD_CHANNEL_ACTIVITY_UNIT_PROMOTED" \
                        or activity["Key"] == "GUILD_CHANNEL_ACTIVITY_UNIT_ACTIVATED":
                            author = activity["Param"][0]["ParamValue"][0]
                            unit_key = activity["Param"][1]["Key"]
                            if unit_key in FRE_FR:
                                unit_key = FRE_FR[unit_key]
                            if "PROMOTED" in activity["Key"]:
                                list_chat_events.append([event_ts, "\N{WHITE MEDIUM STAR} "+author+" vient de promouvoir "+unit_key+" à 7 étoiles"])
                            else:
                                list_chat_events.append([event_ts, "\N{OPEN LOCK} "+author+" vient de débloquer "+unit_key])

                        elif activity["Key"] == "GUILD_CHANNEL_ACTIVITY_TB_STARTED":
                            tb_key = activity["Param"][0]["Key"]
                            if tb_key in FRE_FR:
                                tb_key = FRE_FR[tb_key]
                            phase = activity["Param"][1]["ParamValue"][0]
                            list_chat_events.append([event_ts, tb_key+" la phase "+phase+" a commencé"])

                        elif activity["Key"] == "GUILD_CHANNEL_ACTIVITY_SIMMED_RAID_AUTO_SUMMONED":
                            raid_key = activity["Param"][0]["Key"]
                            if raid_key in FRE_FR:
                                raid_key = FRE_FR[raid_key]
                            list_chat_events.append([event_ts, "Le Raid : "+raid_key+" (simulation activée) vient de commencer, participez maintenant !"])

                        elif activity["Key"] == "GUILD_CHANNEL_ACTIVITY_DEMOTE":
                            demoted = activity["Param"][0]["ParamValue"][0]
                            demoter = activity["Param"][1]["ParamValue"][0]
                            list_chat_events.append([event_ts, demoted+" a été rétrogradé par "+demoter])

                        elif activity["Key"] == "GUILD_CHANNEL_ACTIVITY_RAID_TALLY_COMPLETE":
                            list_chat_events.append([event_ts, "Les raids sont disponibles et peuvent être lancés"])

                        else:
                            goutils.log2("WAR", "Unknown key "+activity["Key"])

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
        zone_deployment_type = dict_tb[zone_name]["Type"]
        if zone["Score"] < dict_tb[zone_name]["Scores"][2]:
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

        if dict_tb[dict_phase["Type"]]["Shortname"] == "ROTE":
            if dict_deployment_types["Mix"]:
                ratio_deploy_mix = player["score"]["DeployedMix"] / player["mix_gp"]
                if ratio_deploy_mix < 0.99:
                    undeployed_player = True
                    ret_print_player += "{:,}".format(dict_tb_players[playerName]["score"]["DeployedMix"]) \
                                       +"/" + "{:,}".format(dict_tb_players[playerName]["mix_gp"]) + " "
        else:
            if dict_deployment_types["Ships"]:
                ratio_deploy_ships = player["score"]["DeployedShips"] / player["ship_gp"]
                if ratio_deploy_ships < 0.99:
                    undeployed_player = True
                    ret_print_player += "Fleet: {:,}".format(dict_tb_players[playerName]["score"]["DeployedShips"]) \
                                       +"/" + "{:,}".format(dict_tb_players[playerName]["ship_gp"]) + " "

            if dict_deployment_types["Chars"]:
                ratio_deploy_chars = player["score"]["DeployedChars"] / player["char_gp"]
                if ratio_deploy_chars < 0.99:
                    undeployed_player = True
                    ret_print_player += "Squad: {:,}".format(dict_tb_players[playerName]["score"]["DeployedChars"]) \
                                       +"/" + "{:,}".format(dict_tb_players[playerName]["char_gp"]) + " "

        if undeployed_player:
            lines_player.append([playerName, ret_print_player])

    return 0, "", lines_player

def get_tb_status(server_id, targets_zone_stars, compute_estimated_fights, use_cache_data):
    dict_tb=godata.dict_tb

    ec, et, rpc_data = get_rpc_data(server_id, use_cache_data)
    if ec!=0:
        return 1, et, None

    dict_guild=rpc_data[0]
    mapstats=rpc_data[1]
    dict_all_events=rpc_data[2]
    guildName = dict_guild["Profile"]["Name"]

    dict_members_by_id={}
    for member in dict_guild["Member"]:
        dict_members_by_id[member["PlayerId"]] = member["PlayerName"]

    tb_ongoing=False
    if "TerritoryBattleStatus" in dict_guild:
        for battleStatus in dict_guild["TerritoryBattleStatus"]:
            if battleStatus["Selected"]:
                battle_id = battleStatus["InstanceId"]
                goutils.log2("DBG", "Selected TB = "+battle_id)
                tb_ongoing=True
                tb_round = battleStatus["CurrentRound"]
                tb_type = battleStatus["DefinitionId"]
                tb_round_endTime = int(battleStatus["CurrentRoundEndTime"])
                tb_round_startTime = tb_round_endTime - dict_tb[tb_type]["PhaseDuration"]
                if battle_id in dict_all_events:
                    dict_events=dict_all_events[battle_id]
                else:
                    dict_events={}
                break

    if not tb_ongoing:
        return 1, "No TB on-going", None

    query = "SELECT name, char_gp, ship_gp FROM players WHERE guildName='"+guildName.replace("'", "''")+"'"
    list_playername_gp = connect_mysql.get_table(query)

    dict_tb_players = {}
    dict_strike_zones = {}
    dict_open_zones = {}
    dict_phase = {"Id": battle_id, "Round": tb_round, "Type": tb_type, "Name": dict_tb[tb_type]["Name"]}

    for playername_gp in list_playername_gp:
        dict_tb_players[playername_gp[0]] = {}
        dict_tb_players[playername_gp[0]]["char_gp"] = playername_gp[1]
        dict_tb_players[playername_gp[0]]["ship_gp"] = playername_gp[2]
        dict_tb_players[playername_gp[0]]["mix_gp"] = playername_gp[1] + playername_gp[2]
        dict_tb_players[playername_gp[0]]["score"] = {"DeployedShips": 0,
                                                      "DeployedChars": 0,
                                                      "DeployedMix": 0,
                                                      "Deployed": 0,
                                                      "Platoons": 0,
                                                      "Strikes": 0} 
        dict_tb_players[playername_gp[0]]["Strikes"] = []

    for zone in battleStatus["ConflictZoneStatus"]:
        if zone["ZoneStatus"]["ZoneState"] == "ZONEOPEN":
            zone_name = zone["ZoneStatus"]["ZoneId"]
            zone_score = int(zone["ZoneStatus"]["Score"])
            dict_open_zones[zone_name] = {"Score": zone_score}

    #sort the dict to display zones in the same order as the game
    dict_open_zones = dict(sorted(dict_open_zones.items(), key=lambda x:dict_tb[tb_type]["ZonePositions"][dict_tb[x[0]]["Name"].split("-")[1]]))

    if len(dict_open_zones)==0:
        return 1, "No TB on-going", None

    total_players_guild = len(dict_tb_players)
    dict_phase["TotalPlayers"] = total_players_guild
    for zone in battleStatus["StrikeZoneStatus"]:
        if zone["ZoneStatus"]["ZoneState"] == "ZONEOPEN":
            strike_name = zone["ZoneStatus"]["ZoneId"]
            strike_shortname = strike_name.split("_")[-1]

            zone_name = strike_name[:-len(strike_shortname)-1]

            done_strikes = zone["PlayersParticipated"]
            score = int(zone["ZoneStatus"]["Score"])
            not_done_strikes = total_players_guild - done_strikes
            remaining_fight = not_done_strikes * dict_tb[zone_name]["Strikes"][strike_shortname][1]
            if not strike_name in dict_strike_zones:
                dict_strike_zones[strike_name] = {}

            dict_strike_zones[strike_name]["Participation"] = done_strikes
            dict_strike_zones[strike_name]["Score"] = score
            dict_strike_zones[strike_name]["MaxPossibleStrikes"] = not_done_strikes
            dict_strike_zones[strike_name]["MaxPossibleScore"] = remaining_fight
            dict_strike_zones[strike_name]["EstimatedStrikes"] = 0
            dict_strike_zones[strike_name]["EstimatedScore"] = 0
            dict_strike_zones[strike_name]["EstimatedScore"] = 0
            dict_strike_zones[strike_name]["EstimatedScore"] = 0
            dict_strike_zones[strike_name]["EventStrikes"] = 0
            dict_strike_zones[strike_name]["EventStrikeScore"] = 0

    for event_id in dict_events:
        event=dict_events[event_id]
        event_time = int(event["Timestamp"])
        playerName = event["AuthorName"]
        if not playerName in dict_tb_players:
            #should not happen unless new player and until API resynchronizes
            continue

        if event_time < tb_round_startTime:
            #event on same zone but bduring previous round
            continue

        for event_data in event["Data"]:
            if "ZoneData" in event_data["Activity"]:
                ZoneData_key = "ZoneData"
            else:
                goutils.log2("ERR", "Event without ZoneData: "+str(event))
                continue

            event_key = event_data["Activity"][ZoneData_key]["ActivityLogMessage"]["Key"]
            if "CONFLICT_CONTRIBUTION" in event_key:
                zone_name = event_data["Activity"][ZoneData_key]["ZoneId"]
                strike_name = event_data["Activity"][ZoneData_key]["SourceZoneId"]
                if zone_name in dict_open_zones:
                    score = int(event_data["Activity"][ZoneData_key]["ScoreDelta"])
                    dict_tb_players[playerName]["score"]["Strikes"] += score

                    dict_strike_zones[strike_name]["EventStrikes"] += 1
                    dict_strike_zones[strike_name]["EventStrikeScore"] += score

                    strike_shortname="_".join(strike_name.split("_")[-2:])
                    dict_tb_players[playerName]["Strikes"].append(strike_shortname)

            elif "RECON_CONTRIBUTION" in event_key:
                zone_name = event_data["Activity"][ZoneData_key]["ZoneId"]
                if zone_name in dict_open_zones:
                    score = int(event_data["Activity"][ZoneData_key]["ScoreDelta"])
                    dict_tb_players[playerName]["score"]["Platoons"] += score

            elif "DEPLOY" in event_key:
                zone_name = event_data["Activity"][ZoneData_key]["ZoneId"]
                if zone_name in dict_open_zones:
                    score = int(event_data["Activity"][ZoneData_key]["ScoreDelta"])
                    if dict_tb[zone_name]["Type"] == "Ships":
                        dict_tb_players[playerName]["score"]["DeployedShips"] += score
                        dict_tb_players[playerName]["score"]["DeployedMix"] += score
                    elif dict_tb[zone_name]["Type"] == "Chars":
                        dict_tb_players[playerName]["score"]["DeployedChars"] += score
                        dict_tb_players[playerName]["score"]["DeployedMix"] += score
                    else:
                        dict_tb_players[playerName]["score"]["DeployedMix"] += score

    for mapstat in mapstats:
        if mapstat["MapStatId"] == "strike_attempt_round_"+str(tb_round):
            if "PlayerStat" in mapstat:
                for playerstat in mapstat["PlayerStat"]:
                    member_id = playerstat["MemberId"]
                    playerName = dict_members_by_id[member_id]
                    attempts = int(playerstat["score"])

                    while len(dict_tb_players[playerName]["Strikes"]) < attempts:
                        dict_tb_players[playerName]["Strikes"].append("?")

        elif mapstat["MapStatId"] == "power_round_"+str(tb_round):
            if "PlayerStat" in mapstat:
                for playerstat in mapstat["PlayerStat"]:
                    member_id = playerstat["MemberId"]
                    playerName = dict_members_by_id[member_id]
                    if not playerName in dict_tb_players:
                        #should not happen unless new player and until API resynchronizes
                        continue

                    score = int(playerstat["score"])
                    dict_tb_players[playerName]["score"]["Deployed"] = score
                    if dict_tb_players[playerName]["score"]["Deployed"] != dict_tb_players[playerName]["score"]["DeployedMix"]:
                        goutils.log2("WAR", "Event deployment does not match total deployment for "+playerName)
                        goutils.log2("WAR", "("+str(dict_tb_players[playerName]["score"]["DeployedMix"])+" vs "+str(dict_tb_players[playerName]["score"]["Deployed"])+")")
                        dict_tb_players[playerName]["score"]["DeployedMix"] = dict_tb_players[playerName]["score"]["Deployed"]

    dict_remaining_deploy = {"Ships": 0, "Chars": 0, "Mix": 0}
    for playerName in dict_tb_players:
        playerData = dict_tb_players[playerName]
        dict_remaining_deploy["Ships"] += playerData["ship_gp"] - playerData["score"]["DeployedShips"]
        dict_remaining_deploy["Chars"] += playerData["char_gp"] - playerData["score"]["DeployedChars"]
        dict_remaining_deploy["Mix"] += playerData["mix_gp"] - playerData["score"]["DeployedMix"]
        
    dict_phase["AvailableShipDeploy"] = dict_remaining_deploy["Ships"]
    dict_phase["AvailableCharDeploy"] = dict_remaining_deploy["Chars"]
    dict_phase["AvailableMixDeploy"] = dict_remaining_deploy["Mix"]

    list_deployment_types = []
    for zone_name in dict_open_zones:
        zone_deployment_type = dict_tb[zone_name]["Type"]
        if not zone_deployment_type in list_deployment_types:
            list_deployment_types.append(zone_deployment_type)

    #count remaining players
    remaining_to_play_ships = 0
    remaining_to_play_chars = 0
    remaining_to_play_mix = 0
    lines_player = []
    for playerName in dict_tb_players:
        if "Ships" in list_deployment_types:
            ratio_deploy_ships = dict_tb_players[playerName]["score"]["DeployedShips"] / dict_tb_players[playerName]["ship_gp"]
            if ratio_deploy_ships < 0.99:
                remaining_to_play_ships += 1
            else:
                ratio_deploy_ships = 1

        if "Chars" in list_deployment_types:
            ratio_deploy_chars = dict_tb_players[playerName]["score"]["DeployedChars"] / dict_tb_players[playerName]["char_gp"]
            if ratio_deploy_chars < 0.99:
                remaining_to_play_chars += 1
            else:
                ratio_deploy_chars = 1

        if "Mix" in list_deployment_types:
            ratio_deploy_mix = dict_tb_players[playerName]["score"]["DeployedMix"] / dict_tb_players[playerName]["mix_gp"]
            if ratio_deploy_mix < 0.99:
                remaining_to_play_mix += 1
            else:
                ratio_deploy_mix = 1

        for zone in dict_open_zones:
            for strike in dict_tb[zone]["Strikes"]:
                strike_shortname = "conflict0"+zone[-1]+"_"+strike
                strike_name = zone+"_"+strike
                if not strike_shortname in dict_tb_players[playerName]["Strikes"]:
                    strike_fights = dict_strike_zones[strike_name]["Participation"]
                    strike_score = dict_strike_zones[strike_name]["EventStrikeScore"]

                    if strike_fights > 0:
                        strike_average_score = strike_score / strike_fights
                    else:
                        strike_average_score = 0

                    if dict_tb[zone]["Type"]=="Ships" and ratio_deploy_ships<0.99:
                        dict_strike_zones[strike_name]["EstimatedStrikes"] += 1
                        dict_strike_zones[strike_name]["EstimatedScore"] += strike_average_score
                    elif dict_tb[zone]["Type"]=="Chars" and ratio_deploy_chars<0.99:
                        dict_strike_zones[strike_name]["EstimatedStrikes"] += 1
                        dict_strike_zones[strike_name]["EstimatedScore"] += strike_average_score
                    elif dict_tb[zone]["Type"]=="Mix" and ratio_deploy_mix<0.99:
                        dict_strike_zones[strike_name]["EstimatedStrikes"] += 1
                        dict_strike_zones[strike_name]["EstimatedScore"] += strike_average_score

    dict_phase["ShipPlayers"] = remaining_to_play_ships
    dict_phase["CharPlayers"] = remaining_to_play_chars
    dict_phase["MixPlayers"] = remaining_to_play_mix

    #compute zone stats apart for deployments
    for zone_name in dict_open_zones:
        current_score = dict_open_zones[zone_name]["Score"]

        estimated_strike_score = 0
        estimated_strike_fights = 0
        max_strike_score = 0
        cur_strike_score = 0
        cur_strike_fights = {}
        for strike in dict_tb[zone_name]["Strikes"]:
            strike_name = zone_name + "_" + strike
            if compute_estimated_fights:
                estimated_strike_fights += dict_strike_zones[strike_name]["EstimatedStrikes"]
                estimated_strike_score += dict_strike_zones[strike_name]["EstimatedScore"]
            max_strike_score += dict_strike_zones[strike_name]["MaxPossibleScore"]

            cur_strike_fights[strike] = dict_strike_zones[strike_name]["Participation"]
            cur_strike_score += dict_strike_zones[strike_name]["EventStrikeScore"]

        dict_open_zones[zone_name]["StrikeScore"] = cur_strike_score
        dict_open_zones[zone_name]["StrikeFights"] = cur_strike_fights
        dict_open_zones[zone_name]["EstimatedStrikeFights"] = estimated_strike_fights
        dict_open_zones[zone_name]["EstimatedStrikeScore"] = estimated_strike_score
        dict_open_zones[zone_name]["MaxStrikeScore"] = max_strike_score
        dict_open_zones[zone_name]["Deployment"] = 0

        star_for_score=0
        for star_score in dict_tb[zone_name]["Scores"]:
            if current_score >= star_score:
                star_for_score += 1
        dict_open_zones[zone_name]["Stars"] = star_for_score

    #zone stats
    tb_type = dict_phase["Type"]

    if targets_zone_stars == "":
        #original warstats logic: closest star, then next closest star...
        #split the zoes by type
        dict_zones_by_type = {"Ships": [], "Chars": [], "Mix": []}
        for zone_name in dict_open_zones:
            zone_type = dict_tb[zone_name]["Type"]
            dict_zones_by_type[zone_type].append(zone_name)

        full_zones = 0
        for zone_type in ["Ships", "Chars", "Mix"]:
            while (dict_remaining_deploy[zone_type] > 0) and (full_zones < len(dict_zones_by_type[zone_type])):
                #find closest star
                min_dist_star = -1
                min_zone_name = ""
                full_zones = 0
                for zone_name in dict_zones_by_type[zone_type]:
                    cur_score = dict_open_zones[zone_name]["Score"]
                    if compute_estimated_fights:
                        cur_score += dict_open_zones[zone_name]["EstimatedStrikeScore"]
                    cur_score += dict_open_zones[zone_name]["Deployment"]

                    if cur_score == dict_tb[zone_name]["Scores"][2]:
                        full_zones += 1
                        continue

                    for star_score in dict_tb[zone_name]["Scores"]:
                        if cur_score < star_score:
                            dist_star = star_score - cur_score
                            if min_dist_star == -1 or dist_star < min_dist_star:
                                min_dist_star = dist_star
                                min_zone_name = zone_name
                            break

                #deploy in the found zone
                if min_zone_name != "":
                    deploy_value = min(min_dist_star, dict_remaining_deploy[zone_type])
                    dict_open_zones[min_zone_name]["Deployment"] += deploy_value
                    dict_remaining_deploy[zone_type] -= deploy_value

    else:
        targets_zone_stars = targets_zone_stars.strip()
        while '  ' in targets_zone_stars:
            targets_zone_stars = targets_zone_stars.replace('  ', ' ')

        for target_zone_stars in targets_zone_stars.split(" "):
            target_zone_name = target_zone_stars.split(":")[0]
            target_stars = int(target_zone_stars.split(":")[1])

            if target_zone_name in dict_tb[tb_type]["ZoneNames"]:
                conflict = dict_tb[tb_type]["ZoneNames"][target_zone_name]
            else:
                return 1, "Zone inconnue: " + target_zone_name + " " + str(list(dict_tb[tb_type]["ZoneNames"].keys())), None

            for zone_name in dict_open_zones:
                if zone_name.endswith(conflict):
                    break

            current_score = dict_open_zones[zone_name]["Score"]
            estimated_strike_score = dict_open_zones[zone_name]["EstimatedStrikeScore"]
            score_with_estimated_strikes = current_score + estimated_strike_score

            target_star_score = dict_tb[zone_name]["Scores"][target_stars-1]
            if dict_tb[zone_name]["Type"] == "Ships":
                deploy_consumption = max(0, min(dict_remaining_deploy["Ships"], target_star_score - score_with_estimated_strikes))
                dict_remaining_deploy["Ships"] -= deploy_consumption
            elif dict_tb[zone_name]["Type"] == "Chars":
                deploy_consumption = max(0, min(dict_remaining_deploy["Chars"], target_star_score - score_with_estimated_strikes))
                dict_remaining_deploy["Chars"] -= deploy_consumption
            else:
                deploy_consumption = max(0, min(dict_remaining_deploy["Mix"], target_star_score - score_with_estimated_strikes))
                dict_remaining_deploy["Mix"] -= deploy_consumption

            dict_open_zones[zone_name]["Deployment"] = deploy_consumption
            score_with_estimations = score_with_estimated_strikes + deploy_consumption

    dict_phase["RemainingShipDeploy"] = dict_remaining_deploy["Ships"]
    dict_phase["RemainingCharDeploy"] = dict_remaining_deploy["Chars"]
    dict_phase["RemainingMixDeploy"] = dict_remaining_deploy["Mix"]

    #Compute estimated stars per zone
    for zone_name in dict_open_zones:
        cur_score = dict_open_zones[zone_name]["Score"]
        if compute_estimated_fights:
            cur_score += dict_open_zones[zone_name]["EstimatedStrikeScore"]
        cur_score += dict_open_zones[zone_name]["Deployment"]

        star_for_score=0
        for star_score in dict_tb[zone_name]["Scores"]:
            if cur_score >= star_score:
                star_for_score += 1
        dict_open_zones[zone_name]["EstimatedStars"] = star_for_score

    return 0, "", [dict_phase, dict_strike_zones, dict_tb_players, dict_open_zones]
##########################################"
# OUT: dict_territory_scores = {"GLS-P3-top": 24500000, ...}
# OUT: tb_active_round = 3
##########################################"
def get_tb_guild_scores(server_id, use_cache_data):
    dict_tb = godata.dict_tb
    ec, et, tb_data = get_tb_status(server_id, "", False, use_cache_data)
    if ec!=0:
        return 1, et, None

    [dict_phase, dict_strike_zones, dict_tb_players, dict_open_zones] = tb_data
    active_round = dict_tb[dict_phase["Type"]]["Shortname"]+str(dict_phase["Round"])
    dict_territory_scores = {}
    for zone in dict_open_zones:
        zone_name_tab = dict_tb[zone]["Name"].split("-")
        zone_name = zone_name_tab[0][:-1]
        zone_name += "-P"
        zone_name += zone_name_tab[0][-1]
        zone_name += "-"
        zone_name += zone_name_tab[1]
        zone_score = dict_open_zones[zone]["Score"]
        dict_territory_scores[zone_name] = zone_score

    return dict_territory_scores, active_round
