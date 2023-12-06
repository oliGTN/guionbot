import json
import sys

guild_file = sys.argv[1]
guild = json.load(open(guild_file))
dict_dtc = {}

for member in guild["member"]:
    player_id = member["playerId"]
    player_file = "PLAYERS/"+player_id+".json"
    player = json.load(open(player_file))
    player_name = player["name"]

    if not "datacron" in player:
        continue

    for dtc in player["datacron"]:
        lvl6 = None
        lvl9 = None
        if not "affix" in dtc:
            continue

        if len(dtc["affix"]) < 6:
            continue
        abilityId = dtc["affix"][5]["abilityId"]
        target_rule = dtc["affix"][5]["targetRule"][16:]
        lvl6 = abilityId+"@"+target_rule
        if len(dtc["affix"]) >= 9:
            lvl9 = dtc["affix"][8]["targetRule"][16:]
        key_dtc = lvl6+":"+str(lvl9)

        if not key_dtc in dict_dtc:
            dict_dtc[key_dtc] = []
        dict_dtc[key_dtc].append(player_name)

for k in dict_dtc:
    print(k+": "+str(dict_dtc[k]))
