import sys
import json
import os

#####################################
# This script adapts the official file from SWGOH.HELP API
# It transfoms the initial list into a dictionary, with the unit_id as key
# Then it add farming information and links ships to crew
#####################################
game_data = json.load(open(sys.argv[1], 'r'))
FRE_FR = json.load(open('DATA/FRE_FR.json', 'r'))
ENG_US = json.load(open('DATA/ENG_US.json', 'r'))

#First transform materialList into dict
materialList_dict = {}
for material in game_data["material"]:
    materialList_dict[material["id"]] = material

#add custom data
my_unit = {"baseId": "LEVIATHAN",
           "nameKey":"UNIT_LEVIATHAN_NAME",
           "combatType":2,
           "rarity":1,
           "obtainableTime":"0",
           "categoryId":["any_obtainable"]}
game_data["units"].append(my_unit)
FRE_FR["UNIT_LEVIATHAN_NAME"] = "Leviathan"
ENG_US["UNIT_LEVIATHAN_NAME"] = "Leviathan"

unitsList_dict = {}
for unit in game_data["units"]:
    if not "any_obtainable" in unit["categoryId"]:
        continue
    if unit["rarity"] != 1:
        continue
    if unit["obtainableTime"] != "0":
        continue

    unit_id = unit['baseId']
    unit['name'] = FRE_FR[unit['nameKey']]
    unit_name = unit['name']
    if unit_id in unitsList_dict:
        #could be if ship has been detected before
        unitsList_dict[unit_id] = {**unitsList_dict[unit_id], **unit}
    else:
        unitsList_dict[unit_id] = unit
        if unit['combatType'] != 2:
            unitsList_dict[unit_id]['ships'] = []

    #attach ships to crew
    if unit['combatType'] == 2 and 'crew' in unit:
        for pilot in unit['crew']:
            pilot_id = pilot['unitId']
            if pilot_id in unitsList_dict:
                unitsList_dict[pilot_id]['ships'].append([unit_id, unit_name])
            else:
                unitsList_dict[pilot_id] = {'ships': [[unit_id, unit_name]]}

    #add farming info
    if not "farmingInfo" in unitsList_dict[unit_id]:
        unitsList_dict[unit_id]['farmingInfo'] = []
    shard_name = 'unitshard_'+unit_id
    if shard_name in materialList_dict:
        farmingSpeed = 3 - int(materialList_dict[shard_name]['sellValue']['quantity']/15)
        if 'lookupMission' in materialList_dict[shard_name]:
            for event in materialList_dict[shard_name]['lookupMission']:
                if not event['missionIdentifier']['campaignMapId'] == 'MARQUEE':
                    farmingLocation = event['missionIdentifier']['campaignId']
                    if not [farmingLocation, farmingSpeed] in unitsList_dict[unit_id]["farmingInfo"]:
                        unitsList_dict[unit_id]["farmingInfo"].append([farmingLocation, farmingSpeed])

fnew = open('DATA'+os.path.sep+'unitsList_dict.json', 'w')
fnew.write(json.dumps(unitsList_dict, sort_keys=True, indent=4))
fnew.close()

############################################
# It also creates a dictionary of aliases from nameKeys
############################################

unitsAlias_dict = {}
priority_names = ["CT210408"]
for unit in game_data["units"]:
    if not "any_obtainable" in unit["categoryId"]:
        continue
    if unit["rarity"] != 1:
        continue
    if unit["obtainableTime"] != "0":
        continue

    for loc in [FRE_FR, ENG_US]:
        loc_name = loc[unit["nameKey"]]
        names = [loc_name]
        if '"' in loc_name:
            names += loc_name.split('"')
        if "" in names:
            names.remove("")
        for name in names:
            name = name.lower()
            if name in unitsAlias_dict:
                if unitsAlias_dict[name][1] != unit['baseId']:
                    prio_found = False
                    for prio in priority_names:
                        if prio in unit['baseId']:
                            unitsAlias_dict[name] = [loc[unitsList_dict[unit['baseId']]['nameKey']], unit['baseId']]
                            prio_found = True
                        elif prio in unitsAlias_dict[name][1]:
                            prio_found = True
                    if not prio_found:
                        print('WAR: double definition of '+name)
                        print(unitsAlias_dict[name][1] + " is kept")
                        print(unit['baseId'] + " is ignored")
                else:
                    pass
            else:
                unitsAlias_dict[name] = [loc[unitsList_dict[unit['baseId']]['nameKey']], unit['baseId']]

fnew = open('DATA'+os.path.sep+'unitsAlias_dict.json', 'w')
fnew.write(json.dumps(unitsAlias_dict, sort_keys=True, indent=4))
fnew.close()

############################################
# It also creates a dictionary of tags (Empire, Jedi...)
############################################

dict_tags_by_id = {}
for x in game_data["category"]:
    if not "uiFilter" in x:
        continue
    for loc in [FRE_FR, ENG_US]:
        tag_id = x["id"]
        if x["descKey"] in loc:
            tag_name = loc[x["descKey"]]
        else:
            tag_name = x["descKey"]
        if not tag_id.startswith("selftag_") \
            and not tag_id.startswith("specialmission_") \
            and not tag_name == "Placeholder":

            if tag_id in dict_tags_by_id:
                if not tag_name in dict_tags_by_id[tag_id]:
                    dict_tags_by_id[tag_id].append(tag_name)
            else:
                dict_tags_by_id[tag_id] = [tag_name]
            
dict_categories_by_name = {}
for x in game_data["units"]:
    if not "any_obtainable" in x["categoryId"]:
        continue
    if x["rarity"] != 1:
        continue
    if x["obtainableTime"] != "0":
        continue

    for tag in x["categoryId"]:
        if tag in dict_tags_by_id:
            for tag_name in dict_tags_by_id[tag]:
                id_name = [x["baseId"], FRE_FR[x["nameKey"]], x["combatType"]]
                if tag_name in dict_categories_by_name:
                    if not id_name in dict_categories_by_name[tag_name]:
                        dict_categories_by_name[tag_name].append(id_name)
                else:
                    dict_categories_by_name[tag_name] = [id_name]

fnew = open('DATA'+os.path.sep+'tagAlias_dict.json', 'w')
fnew.write(json.dumps(dict_categories_by_name, sort_keys=True, indent=4))
fnew.close()

categoryList_dict = {}
for category in game_data["category"]:
    if not "uiFilter" in category:
        continue
    if category['id'] in categoryList_dict:
        print('WAR: double definition of '+category['id'])
    if category["descKey"] in FRE_FR:
        category["descKey"] = FRE_FR[category["descKey"]]
    categoryList_dict[category['id']] = category

fnew = open('DATA'+os.path.sep+'categoryList_dict.json', 'w')
fnew.write(json.dumps(categoryList_dict, sort_keys=True, indent=4))
fnew.close()

modList_dict = {}
for mod in game_data["statMod"]:
    modList_dict[mod['id']] = {"slot": mod["slot"],
                               "setId": mod["setId"],
                               "rarity": mod["rarity"]}

fnew = open('DATA'+os.path.sep+'modList_dict.json', 'w')
fnew.write(json.dumps(modList_dict, sort_keys=True, indent=4))
fnew.close()
