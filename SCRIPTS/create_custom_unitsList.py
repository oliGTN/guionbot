import json
import sys

game_data = json.load(open(sys.argv[1], 'r'))["Units"]
unitsList = json.load(open("DATA/unitsList.json", 'r'))
FRE_FR = json.load(open("DATA/FRE_FR.json", 'r'))

api_units = [unit["baseId"] for unit in unitsList]

list_new_units = []
added_units = []
for unit in game_data:
    if unit["BaseId"] in added_units:
        continue
    if not "any_obtainable" in unit["CategoryId"]:
        continue
    if unit["BaseId"] in api_units:
        continue
    if unit["Rarity"] != 1:
        continue
    if unit["ObtainableTime"] != "0":
        continue

    dict_unit = {}
    print(unit["BaseId"])
    dict_unit["baseId"] = unit["BaseId"]
    dict_unit["combatType"] = unit["CombatType"]
    dict_unit["forceAlignment"] = unit["ForceAlignment"]
    dict_unit["nameKey"] = FRE_FR[unit["NameKey"]]
    dict_unit["categoryIdList"] = unit["CategoryId"]
    if "Crew" in unit:
        dict_unit["crewList"] = []
        for crew in unit["Crew"]:
            new_crew = {"unitId": crew["UnitId"]}
            dict_unit["crewList"].append(new_crew)

    list_new_units.append(dict_unit)
    added_units.append(unit["BaseId"])

f=open("DATA/unitsList_custom.json", "w")
f.write(json.dumps(list_new_units, indent=4))
f.close()

