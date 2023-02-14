import subprocess
import os
import json
import re
import threading

import goutils
import data

dict_bot_accounts = {}
dict_bot_accounts["Kangoo Legends"] = {"Name": "Warstat", "Locked": False, "sem": threading.Semaphore()}

def lock_bot_account(guildName):
    if not guildName in dict_bot_accounts:
        return 1, "Only available for "+str(list(dict_bot_accounts.keys()))+" but not for ["+guildName+"]"
    dict_bot_accounts[guildName]["Locked"] = True
    return 0, ""

def unlock_bot_account(guildName):
    if not guildName in dict_bot_accounts:
        return 1, "Only available for "+str(list(dict_bot_accounts.keys()))+" but not for ["+guildName+"]"
    dict_bot_accounts[guildName]["Locked"] = False
    return 0, ""

def get_rpc_data(guildName):
    if not guildName in dict_bot_accounts:
        return 1, "Only available for "+str(list(dict_bot_accounts.keys()))+" but not for ["+guildName+"]", None
    bot_playerName = dict_bot_accounts[guildName]["Name"]

    if dict_bot_accounts[guildName]["Locked"]:
        return 1, "The bot account is being used... please wait or unlock it", None

    goutils.log2("DBG", "try to acquire sem in p="+str(os.getpid())+", t="+str(threading.get_native_id()))
    dict_bot_accounts[guildName]["sem"].acquire()
    goutils.log2("DBG", "sem acquired sem in p="+str(os.getpid())+", t="+str(threading.get_native_id()))

    process = subprocess.run(["/home/pi/GuionBot/warstats/getguild.sh", bot_playerName])
    goutils.log2("DBG", "getguild code="+str(process.returncode))
    guild_json = json.load(open("/home/pi/GuionBot/warstats/guild_"+bot_playerName+".json", "r"))
    if "Guild" in guild_json:
        dict_guild = guild_json["Guild"]
    else:
        dict_guild = {}

    process = subprocess.run(["/home/pi/GuionBot/warstats/getevents.sh", bot_playerName])
    goutils.log2("DBG", "getevents code="+str(process.returncode))
    events_json = json.load(open("/home/pi/GuionBot/warstats/events_"+bot_playerName+".json", "r"))
    if "Event" in events_json:
        dict_new_events = events_json["Event"]
    else:
        dict_new_events = {}

    process = subprocess.run(["/home/pi/GuionBot/warstats/getmapstats.sh", bot_playerName, "TB"])
    goutils.log2("DBG", "getmapstats code="+str(process.returncode))
    if os.path.exists("/home/pi/GuionBot/warstats/TBmapstats_"+bot_playerName+".json"):
        TBmapstats_json = json.load(open("/home/pi/GuionBot/warstats/TBmapstats_"+bot_playerName+".json", "r"))
        if "CurrentStat" in TBmapstats_json:
            dict_TBmapstats = TBmapstats_json["CurrentStat"]
        else:
            dict_TBmapstats = {}
    else:
        dict_TBmapstats = {}

    process = subprocess.run(["/home/pi/GuionBot/warstats/getmapstats.sh", bot_playerName, "TW"])
    goutils.log2("DBG", "getmapstats code="+str(process.returncode))
    if os.path.exists("/home/pi/GuionBot/warstats/TWmapstats_"+bot_playerName+".json"):
        TWmapstats_json = json.load(open("/home/pi/GuionBot/warstats/TWmapstats_"+bot_playerName+".json", "r"))
        if "CurrentStat" in TWmapstats_json:
            dict_TWmapstats = TWmapstats_json["CurrentStat"]
        else:
            dict_TWmapstats = {}
    else:
        dict_TWmapstats = {}


    dict_events = {}
    for event in dict_new_events:
        event_id = event["Id"]
        channel_id = event["ChannelId"]
        ret_re = re.search(".*\-\{.*\}\-(.*)\-.*", channel_id)
        event_battle_id = ret_re.group(1)

        if not event_battle_id in dict_events:
            fevents = "EVENTS/"+guildName+"_"+event_battle_id+"_events.json"
            if os.path.exists(fevents):
                f = open(fevents)
                dict_events[event_battle_id]=json.load(f)
                f.close()
            else:
                dict_events[event_battle_id]={}

        if not event_id in dict_events[event_battle_id]:
            dict_events[event_battle_id][event_id] = event

    for event_battle_id in dict_events:
        fevents = "EVENTS/"+guildName+"_"+event_battle_id+"_events.json"
        f=open(fevents, "w")
        f.write(json.dumps(dict_events[event_battle_id], indent=4))
        f.close()

    goutils.log2("DBG", "try to release sem in p="+str(os.getpid())+", t="+str(threading.get_native_id()))
    dict_bot_accounts[guildName]["sem"].release()
    goutils.log2("DBG", "sem released sem in p="+str(os.getpid())+", t="+str(threading.get_native_id()))

    return 0, "", [dict_guild, dict_TBmapstats, dict_events]

def parse_tb_platoons(guildName):
    active_round = "" # GLS4"
    dict_platoons = {} #key="GLS1-mid-2", value={key=perso, value=[player, player...]}
    list_open_territories = [0, 0, 0] # [4, 3, 3]

    dict_tb = {}
    dict_tb["t04D"] = "GLS"
    dict_tb["geonosis_republic_phase01_conflict01_recon01"] = "GLS1-top"
    dict_tb["geonosis_republic_phase01_conflict02_recon01"] = "GLS1-mid"
    dict_tb["geonosis_republic_phase01_conflict03_recon01"] = "GLS1-bot"
    dict_tb["geonosis_republic_phase02_conflict01_recon01"] = "GLS2-top"
    dict_tb["geonosis_republic_phase02_conflict02_recon01"] = "GLS2-mid"
    dict_tb["geonosis_republic_phase02_conflict03_recon01"] = "GLS2-bot"
    dict_tb["geonosis_republic_phase03_conflict01_recon01"] = "GLS3-top"
    dict_tb["geonosis_republic_phase03_conflict02_recon01"] = "GLS3-mid"
    dict_tb["geonosis_republic_phase03_conflict03_recon01"] = "GLS3-bot"
    dict_tb["geonosis_republic_phase04_conflict01_recon01"] = "GLS4-top"
    dict_tb["geonosis_republic_phase04_conflict02_recon01"] = "GLS4-mid"
    dict_tb["geonosis_republic_phase04_conflict03_recon01"] = "GLS4-bot"

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

    err_code, err_txt, rpc_data = get_rpc_data(guildName)

    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return '', None, None, 0

    dict_guild = rpc_data[0]
    mapstats_json = rpc_data[1]
    dict_events = rpc_data[2]

    dict_member_by_id = {}
    for member in dict_guild["Member"]:
        dict_member_by_id[member["PlayerId"]] = member["PlayerName"]

    dict_unitsList = data.get("unitsList_dict.json")

    if not "TerritoryBattleStatus" in dict_guild:
        goutils.log2("WAR", "["+guildName+"] no TB in progress")
        return '', None, None, 0

    for battleStatus in dict_guild["TerritoryBattleStatus"]:
        if battleStatus["Selected"]:
            active_round = dict_tb[battleStatus["DefinitionId"]] + str(battleStatus["CurrentRound"])

            if active_round == 0:
                return '', None, None, 0

            for zone in battleStatus["ReconZoneStatus"]:
                zone_name = zone["ZoneStatus"]["ZoneId"]

                if zone["ZoneStatus"]["ZoneState"] == "ZONEOPEN":
                    ret_re = re.search(".*_phase0(\d)_conflict0(\d)_recon01", zone_name)
                    zone_position = int(ret_re.group(2))
                    zone_phase = int(ret_re.group(1))
                    list_open_territories[zone_position-1] = zone_phase

                for platoon in zone["Platoon"]:
                    platoon_num = int(platoon["Id"][-1])
                    platoon_num_corrected = 7 - platoon_num
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

    return active_round, dict_platoons, list_open_territories, 0
