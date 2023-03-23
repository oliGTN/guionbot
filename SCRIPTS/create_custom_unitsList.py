import json
import sys

game_data = json.load(open(sys.argv[1], 'r'))["units"]
unitsList = json.load(open("DATA/unitsList.json", 'r'))
FRE_FR = json.load(open("DATA/FRE_FR.json", 'r'))

api_units = [unit["baseId"] for unit in unitsList]

list_new_units = []
added_units = []
for unit in game_data:
    if unit["baseId"] in added_units:
        continue
    if not "any_obtainable" in unit["categoryId"]:
        continue
    if unit["baseId"] in api_units:
        continue
    if unit["rarity"] != 1:
        continue
    if unit["obtainableTime"] != "0":
        continue

    dict_unit = {}
    print(unit["baseId"])
    dict_unit["baseId"] = unit["baseId"]
    dict_unit["combatType"] = unit["combatType"]
    dict_unit["forceAlignment"] = unit["forceAlignment"]
    dict_unit["nameKey"] = FRE_FR[unit["nameKey"]]
    dict_unit["categoryIdList"] = unit["categoryId"]
    if " rew" in unit:
        dict_unit["crewList"] = []
        for crew in unit["crew"]:
            new_crew = {"unitId": crew["unitId"]}
            dict_unit["crewList"].append(new_crew)

    list_new_units.append(dict_unit)
    added_units.append(unit["baseId"])

f=open("DATA/unitsList_custom.json", "w")
f.write(json.dumps(list_new_units, indent=4))
f.close()

