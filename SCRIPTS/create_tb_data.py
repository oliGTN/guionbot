import json
import sys
game_data = json.load(open(sys.argv[1], 'r'))
FRE_FR = json.load(open('DATA/FRE_FR.json', 'r'))
ENG_US = json.load(open('DATA/ENG_US.json', 'r'))

# shortname, [conflit01, conflict02, conflict03]
tb_aliases = {"t01D": {"alias": "HLS", 
                       "conflict01": "top", 
                       "conflict02": "mid", 
                       "conflict03": "bot", 
                       "positions": ["top", "mid", "bot"]
                       },
              "t02D": {"alias": "HDS", 
                       "conflict01": "top", 
                       "conflict02": "mid", 
                       "conflict03": "bot", 
                       "positions": ["top", "mid", "bot"]
                       },
              "t03D": {"alias": "GDS", 
                       "conflict01": "top", 
                       "conflict02": "mid", 
                       "conflict03": "bot", 
                       "positions": ["top", "mid", "bot"]
                       },
              "t04D": {"alias": "GLS", 
                       "conflict01": "top", 
                       "conflict02": "mid", 
                       "conflict03": "bot", 
                       "positions": ["top", "mid", "bot"]
                       },
              "t05D": {"alias": "ROTE", 
                       "conflict01": "LS", 
                       "conflict02": "DS", 
                       "conflict03": "MS", 
                       "positions": ["DS", "MS", "LS"]
                       },
             }

tb_spe_requirements = {
    "tb3_mixed_phase02_conflict01_covert01": {
        "logic": "AND",
        "items": [
            {"defId": "CEREJUNDA", "relic": 7},
            {
                "logic": "OR",
                "items": [
                    {"defId": "CALKESTIS", "relic": 7},
                    {"defId": "JEDIKNIGHTCAL", "relic": 7}
                ]
            }
        ]
    },
    "tb3_mixed_phase03_conflict03_covert02": {
        "logic": "AND",
        "items": [
            {"defId": "MANDALORBOKATAN", "relic": 7},
            {"defId": "THEMANDALORIANBESKARARMOR", "relic": 7},
            {"defId": "IG12", "relic": 7}
        ]
    }
}


dict_tables = {}
for t in game_data["table"]:
    dict_tables[t["id"]] = t

dict_tb={"zone_names": {}}
for tb in game_data["territoryBattleDefinition"]:
    tb_id = tb["id"]
    tb_alias = tb_aliases[tb_id]["alias"]
    dict_tb[tb_alias] = {"id": tb_id}

    tb_rounds = int(tb["roundCount"])
    dict_tb[tb_id] = {"phaseDuration": int(6*24*3600*1000/tb_rounds),
                      "zonePositions":{},
                      "maxRound":tb_rounds}
    dict_tb[tb_id]["name"] = FRE_FR[tb["nameKey"]]
    dict_tb[tb_id]["shortname"] = tb_alias

    for i in [1, 2, 3]:
        tb_positions = tb_aliases[tb_id]["positions"]
        dict_tb[tb_id]["zonePositions"][tb_positions[i-1]] = i

    first_zone_id = tb["conflictZoneDefinition"][0]["zoneDefinition"][0]["zoneId"]
    dict_tb[tb_id]["prefix"] = "_".join(first_zone_id.split("_")[:-2])

    for c in tb["conflictZoneDefinition"]:
        #print(c)
        zone_id = c["zoneDefinition"][0]["zoneId"]
        zone_name = ENG_US[c["zoneDefinition"][0]["nameKey"]]
        if zone_id.endswith("_bonus"):
            is_bonus = True
            zone_phase = zone_id.split("_")[-3]
            conflict_id = zone_id.split("_")[-2]
        else:
            is_bonus = False
            zone_phase = zone_id.split("_")[-2]
            conflict_id = zone_id.split("_")[-1]

        zone_from_same_phase = [x for x in tb["conflictZoneDefinition"] if zone_phase in x["zoneDefinition"][0]["zoneId"]]
        dict_tb[zone_id] = {}
        if len(zone_from_same_phase) == 1:
            dict_tb[zone_id]["name"] = tb_alias+zone_phase[-1]+"-"+tb_aliases[tb_id]["conflict02"]
        elif len(zone_from_same_phase) == 2:
            if c == zone_from_same_phase[0]:
                dict_tb[zone_id]["name"] = tb_alias+zone_phase[-1]+"-"+tb_aliases[tb_id]["conflict01"]
            else:
                dict_tb[zone_id]["name"] = tb_alias+zone_phase[-1]+"-"+tb_aliases[tb_id]["conflict03"]
        else: # len >= 3
            dict_tb[zone_id]["name"] = tb_alias+zone_phase[-1]+"-"+tb_aliases[tb_id][conflict_id]

            if is_bonus:
                dict_tb[zone_id]["name"] += "b"

        # add an entry by zone name
        dict_tb["zone_names"][zone_name] = dict_tb[zone_id]["name"]

        # define chars/ships/mix
        if c["territoryBattleZoneUnitType"] == 1:
            dict_tb[zone_id]["type"] = "chars"
        elif c["territoryBattleZoneUnitType"] == 2:
            dict_tb[zone_id]["type"] = "ships"
        else:
            dict_tb[zone_id]["type"] = "mix"

        dict_tb[zone_id]["scores"] = [0, 0, 0]
        dict_tb[zone_id]["scores"][0] = int(c["victoryPointsRewards"][0]["galacticScoreRequirement"])
        dict_tb[zone_id]["scores"][1] = int(c["victoryPointsRewards"][1]["galacticScoreRequirement"])
        dict_tb[zone_id]["scores"][2] = int(c["victoryPointsRewards"][2]["galacticScoreRequirement"])

        dict_tb[zone_id]["strikes"] = {}
        dict_tb[zone_id]["coverts"] = {}

    for s in tb["strikeZoneDefinition"]:
        #print(s)
        zone_id = s["zoneDefinition"]["zoneId"]
        conflict_id = "_".join(zone_id.split("_")[:-1])
        strike_id = zone_id.split("_")[-1]

        score_table = dict_tables[s["encounterRewardTable"]]
        dict_tb[conflict_id]["strikes"][strike_id] = [int(score_table["row"][-1]["key"]),
                                                      int(score_table["row"][-1]["value"].split(":")[1])]
                                                     
    for c in tb["covertZoneDefinition"]:
        #print(c)
        zone_id = c["zoneDefinition"]["zoneId"]
        conflict_id = "_".join(zone_id.split("_")[:-1])
        covert_id = zone_id.split("_")[-1]
        dict_tb[conflict_id]["coverts"][covert_id] = {}
        if zone_id in tb_spe_requirements:
            dict_tb[conflict_id]["coverts"][covert_id]["requirements"] = tb_spe_requirements[zone_id]


    for r in tb["reconZoneDefinition"]:
        zone_id = r["zoneDefinition"]["zoneId"]
        conflict_id = "_".join(zone_id.split("_")[:-1])
        platoon_score = int(r["platoonDefinition"][0]["reward"]["value"])
        dict_tb[conflict_id]["platoonScore"] = platoon_score


dict_tb_json = json.dumps(dict_tb, indent=4)
f = open("DATA/tb_definition.json", "w")
f.write(dict_tb_json)
f.close()
