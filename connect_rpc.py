import subprocess
import os
import json

import goutils

def get_tb_data(guildName):
    if not guildName=="Kangoo Legends":
        return 1, "Only available for Kangoo Legends ["+guildName+"]", None

    bot_playerName = "Warstat"

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
