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

####################
#add custom data
"""
my_units = [
          {"baseId": "GLAHSOKA",
           "nameKey":"UNIT_GLAHSOKA_NAME",    # the key is defined a few lines below
           "combatType":1,                  # 1: char / 2: ship
           "rarity":7,
           "maxRarity":7,
           "obtainableTime":"0",
           "obtainable":True,
           "categoryId":["any_obtainable"]}
          ]
for my_unit in my_units:
    game_data["units"].append(my_unit)
FRE_FR["UNIT_GLAHSOKA_NAME"] = "Ahsoka Tano"
ENG_US["UNIT_GLAHSOKA_NAME"] = "Ahsoka Tano"
"""

with open('DATA/FRE_FR.json', 'w') as f_loc:
    f_loc.write(json.dumps(FRE_FR, indent=4))
with open('DATA/ENG_US.json', 'w') as f_loc:
    f_loc.write(json.dumps(ENG_US, indent=4))
####################

unitsList_dict = {}
for unit in game_data["units"]:
    if unit["rarity"] != unit["maxRarity"]:
        continue

    #Following filter to remove PVE units - same filter above for unitsAlias
    if not "any_obtainable" in unit["categoryId"]:
        continue
    if unit["obtainableTime"] != "0":
        continue
    if not unit["obtainable"]:
        continue

    unit_id = unit['baseId']

    if unit['nameKey'] in FRE_FR:
        unit['name'] = FRE_FR[unit['nameKey']]
    else:
        print("WAR: "+unit['nameKey']+" not found in FRE_FR")
        unit['name'] = unit['nameKey']

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
                    farmingLocation = event['missionIdentifier']
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
    if unit["rarity"] != unit["maxRarity"]:
        continue

    #Following filter to remove PVE units - same filter above for unitsList
    playable_unit=True
    if not "any_obtainable" in unit["categoryId"]:
        playable_unit=False
        continue
    if unit["obtainableTime"] != "0":
        playable_unit=False
        continue
    if not unit["obtainable"]:
        playable_unit=False
        continue

    for loc in [FRE_FR, ENG_US]:
        # unit["nameKey"] is a generic variable "UNIT_LOBOT_NAME", to read in the loc dictionary
        if unit["nameKey"] in loc:
            loc_name = loc[unit["nameKey"]]
        else:
            loc_name = unit["nameKey"]

        names = [loc_name]
        if '"' in loc_name:
            names += loc_name.split('"')
        if "" in names:
            names.remove("")
        for name in names:
            name = name.lower()
            if name in unitsAlias_dict:
                if unitsAlias_dict[name][1] != unit['baseId']:
                    #if playable_unit:
                    #    #New unit is playable and then gets automatic priority
                    #    unitsAlias_dict[name] = [loc[unitsList_dict[unit['baseId']]['nameKey']], unit['baseId']]
                    #    print('WAR: double definition of '+name)
                    #    print(unitsAlias_dict[name][1] + " is removed")
                    #    print(unit['baseId'] + " is playable and then kept")

                    #else:
                        prio_found = False
                        for prio in priority_names:
                            if prio in unit['baseId']:
                                # the main language in French
                                unitsAlias_dict[name] = [FRE_FR[unitsList_dict[unit['baseId']]['nameKey']], unit['baseId']]
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
                if unitsList_dict[unit['baseId']]['nameKey'] in loc:
                    unit_name = FRE_FR[unitsList_dict[unit['baseId']]['nameKey']]
                else:
                    unit_name = unitsList_dict[unit['baseId']]['nameKey']
                unitsAlias_dict[name] = [unit_name, unit['baseId']]

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
