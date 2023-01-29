import subprocess
import os
import json
import re

import goutils
import data

dict_bot_accounts = {}
dict_bot_accounts["Kangoo Legends"] = {"Name": "Warstat", "Locked": False}

def lock_bot_account(guildName):
    if not guildName in dict_bot_accounts:
        return 1, "Only available for "+list(dict_bot_accounts.keys())+" but not for ["+guildName+"]"
    dict_bot_accounts[guildName]["Locked"] = True
    return 0, ""

def unlock_bot_account(guildName):
    if not guildName in dict_bot_accounts:
        return 1, "Only available for "+list(dict_bot_accounts.keys())+" but not for ["+guildName+"]"
    dict_bot_accounts[guildName]["Locked"] = False
    return 0, ""

def get_tb_data(guildName):
    if not guildName in dict_bot_accounts:
        return 1, "Only available for "+list(dict_bot_accounts.keys())+" but not for ["+guildName+"]", None
    bot_playerName = dict_bot_accounts[guildName]["Name"]

    if dict_bot_accounts[guildName]["Locked"]:
        return 1, "The bot account is being used... please wait or unlock it", None

    process = subprocess.run(["/home/pi/GuionBot/warstats/getguild.sh", bot_playerName])
    goutils.log2("DBG", "getguild code="+str(process.returncode))
    if process.returncode != 0:
        #Credential issue
        process = subprocess.run(["/home/pi/GuionBot/warstats/auth.sh", bot_playerName])
        goutils.log2("DBG", "auth code="+str(process.returncode))
        process = subprocess.run(["/home/pi/GuionBot/warstats/getguild.sh", bot_playerName])
        goutils.log2("DBG", "getguild code="+str(process.returncode))

    process = subprocess.run(["/home/pi/GuionBot/warstats/getmapstats.sh", bot_playerName])
    goutils.log2("ERR", "getmapstats code="+str(process.returncode))
    if process.returncode == 2:
        return 1, "No TB in progress", None

    process = subprocess.run(["/home/pi/GuionBot/warstats/getevents.sh", bot_playerName])
    goutils.log2("DBG", "getevents code="+str(process.returncode))
    if process.returncode != 0:
        #Credential issue
        process = subprocess.run(["/home/pi/GuionBot/warstats/createsession.sh", bot_playerName])
        if process.returncode!=0:
            goutils.log2("ERR", "createsession code="+str(process.returncode))
            return 1, "creationsession failed", None

        process = subprocess.run(["/home/pi/GuionBot/warstats/getevents.sh", bot_playerName])
        if process.returncode!=0:
            goutils.log2("ERR", "getevents code="+str(process.returncode))
            return 1, "getevents failed", None

    guild_json = json.load(open("/home/pi/GuionBot/warstats/guild.json", "r"))["Guild"]
    events_json = json.load(open("/home/pi/GuionBot/warstats/events.json", "r"))["Event"]
    mapstats_json = json.load(open("/home/pi/GuionBot/warstats/mapstats.json", "r"))["CurrentStat"]

    fevents = "CACHE/"+guildName+"_events.json"
    if os.path.exists(fevents):
        f = open(fevents)
        dict_events=json.load(f)
        f.close()
    else:
        dict_events={}

    for event in events_json:
        event_id = event["Id"]
        if not event_id in dict_events:
            dict_events[event_id] = event
    f=open(fevents, "w")
    f.write(json.dumps(dict_events, indent=4))
    f.close()

    return 0, "", [guild_json, mapstats_json, dict_events]

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

    err_code, err_txt, [dict_guild, mapstats_json, dict_events] = get_tb_data(guildName)

    if err_code != 0:
        goutils.log2("ERR", err_txt)
        return '', None, None, 0

    dict_member_by_id = {}
    for member in dict_guild["Member"]:
        dict_member_by_id[member["PlayerId"]] = member["PlayerName"]

    dict_unitsList = data.get("unitsList_dict.json")

    for battleStatus in dict_guild["TerritoryBattleStatus"]:
        if battleStatus["Selected"]:
            active_round = dict_tb[battleStatus["DefinitionId"]] + str(battleStatus["CurrentRound"])

            for zone in battleStatus["ReconZoneStatus"]:
                zone_name = zone["ZoneStatus"]["ZoneId"]

                if zone["ZoneStatus"]["ZoneState"] == "ZONEOPEN":
                    ret_re = re.search(".*_phase0(\d)_conflict0(\d)_recon01", zone_name)
                    zone_position = int(ret_re.group(2))
                    zone_phase = int(ret_re.group(1))
                    list_open_territories[zone_position-1] = zone_phase

                for platoon in zone["Platoon"]:
                    platoon_name = dict_tb[zone_name] + "-" + platoon["Id"][-1]
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

    return active_round, dict_platoons, list_open_territories, 0
