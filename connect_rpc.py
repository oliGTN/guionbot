import subprocess
import json
import goutils

def get_tb_data(guildName):
    if not guildName=="Kangoo Legends":
        return 1, "Only available for Kangoo Legends ["+guildName+"]", None

    bot_playerName = "Warstat"

    process = subprocess.run(["/home/pi/GuionBot/warstats/getguild.sh", bot_playerName])
    print("getguild code="+str(process.returncode))
    if process.returncode != 0:
        #Credential issue
        process = subprocess.run(["/home/pi/GuionBot/warstats/auth.sh", bot_playerName])
        print("auth code="+str(process.returncode))
        process = subprocess.run(["/home/pi/GuionBot/warstats/getguild.sh", bot_playerName])
        print("getguild code="+str(process.returncode))

    process = subprocess.run(["/home/pi/GuionBot/warstats/getevents.sh", bot_playerName])
    print("getevents code="+str(process.returncode))
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

    guild_json = json.load(open("/home/pi/GuionBot/warstats/guild.json", "r"))
    events_json = json.load(open("/home/pi/GuionBot/warstats/events.json", "r"))

    return 0, "", [guild_json, events_json]
