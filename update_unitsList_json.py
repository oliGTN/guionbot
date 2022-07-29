import sys
import json
import os

#####################################
# This script adapts the official file from SWGOH.HELP API
# It transfoms the initial list into a dictionary, with the unit_id as key
# Then it add farming information
#####################################
#First transform materialList into dict
materialList = json.load(open('DATA'+os.path.sep+'materialList.json', 'r'))
materialList_dict = {}
for material in materialList:
    materialList_dict[material["id"]] = material

unitsList = json.load(open('DATA'+os.path.sep+'unitsList.json', 'r'))
unitsList_dict = {}
for unit in unitsList:
    #if (not ':' in unit['id']):
        unit_id = unit['baseId']
        if unit_id in unitsList_dict:
            #could be if ship has been detected before
            unitsList_dict[unit_id] = {**unitsList_dict[unit_id], **unit}
        else:
            unitsList_dict[unit_id] = unit
            if unit['combatType'] != 2:
                unitsList_dict[unit_id]['ships'] = []

        #attach ships to crew
        if unit['combatType'] == 2:
            for pilot in unit['crewList']:
                pilot_id = pilot['unitId']
                if pilot_id in unitsList_dict:
                    unitsList_dict[pilot_id]['ships'].append(unit_id)
                else:
                    unitsList_dict[pilot_id] = {'ships': [unit_id]}

        #add farming info
        if not "farmingInfo" in unitsList_dict[unit_id]:
            unitsList_dict[unit_id]['farmingInfo'] = []
        shard_name = 'unitshard_'+unit_id
        if shard_name in materialList_dict:
            farmingSpeed = 3 - int(materialList_dict[shard_name]['sellValue']['quantity']/15)
            if 'lookupMissionList' in materialList_dict[shard_name]:
                for event in materialList_dict[shard_name]['lookupMissionList']:
                    if not event['missionIdentifier']['campaignMapId'] == 'MARQUEE':
                        farmingLocation = event['missionIdentifier']['campaignId']
                        if not [farmingLocation, farmingSpeed] in unitsList_dict[unit_id]["farmingInfo"]:
                            unitsList_dict[unit_id]["farmingInfo"].append([farmingLocation, farmingSpeed])

            else:
                print('lookupMissionList not found for '+shard_name)

unitsList_custom = json.load(open('DATA'+os.path.sep+'unitsList_custom.json', 'r'))
for unit_id in unitsList_custom:
    if unit_id in unitsList_dict:
        print(unit_id + ' in custom is alreday in basic unitsList')
    else:
        unitsList_dict[unit_id] = unitsList_custom[unit_id]

fnew = open('DATA'+os.path.sep+'unitsList_dict.json', 'w')
fnew.write(json.dumps(unitsList_dict, sort_keys=True, indent=4))
fnew.close()

############################################
# It also creates a dictionary of aliases from nameKeys
############################################
unitsList_FRE_FR = unitsList
unitsList_ENG_US = json.load(open('DATA'+os.path.sep+'unitsList_ENG_US.json', 'r'))
#priority_names=["LEGENDARY", "S3", "GLREY", "HOTHREBELSOLDIER", "IMPERIALPROBEDROID", "AURRA_SING", "AMILYNHOLDO", "VULTUREDROID", "GRIEVOUS", "B1BATTLEDROIDV2", "THEMANDALORIAN", "VADER", "OBJ_CRATE_01", "SCOOTTROOPER"]
priority_names=["CT210408"]

if len(unitsList_FRE_FR) != len(unitsList_ENG_US):
    print("Listes FRE_FR et ENG_US differentes ("+str(len(unitsList_FRE_FR))+ " vs "+str(len(unitsList_ENG_US))+")")
    print(set(unitsList_FRE_FR).difference(set(unitsList_ENG_US)))
    sys.exit(1)

unitsAlias_dict = {}
for unitsList in [unitsList_FRE_FR, unitsList_ENG_US]:
    for unit in unitsList:
        names = [unit['nameKey']]
        if '"' in unit['nameKey']:
            names += unit['nameKey'].split('"')
        if "" in names:
            names.remove("")
        for nameKey in names:
            nameKey = nameKey.lower()
            if nameKey in unitsAlias_dict:
                if unitsAlias_dict[nameKey][1] != unit['baseId']:
                    prio_found = False
                    for prio in priority_names:
                        if prio in unit['baseId']:
                            unitsAlias_dict[nameKey] = [unitsList_dict[unit['baseId']]['nameKey'], unit['baseId']]
                            prio_found = True
                        elif prio in unitsAlias_dict[nameKey][1]:
                            prio_found = True
                    if not prio_found:
                        print('WAR: double definition of '+nameKey)
                        print(unitsAlias_dict[nameKey][1] + " is kept")
                        print(unit['baseId'] + " is ignored")
                else:
                    pass
            else:
                unitsAlias_dict[nameKey] = [unitsList_dict[unit['baseId']]['nameKey'], unit['baseId']]

fnew = open('DATA'+os.path.sep+'unitsAlias_dict.json', 'w')
fnew.write(json.dumps(unitsAlias_dict, sort_keys=True, indent=4))
fnew.close()

############################################
# It also creates a dictionary of tags (Empire, Jedi...)
############################################
categoryList_FRE_FR = json.load(open('DATA'+os.path.sep+'categoryList.json', 'r'))
categoryList_ENG_US = json.load(open('DATA'+os.path.sep+'categoryList_ENG_US.json', 'r'))

dict_tags_by_id = {}
for x in categoryList_FRE_FR:
    tag_id = x["id"]
    tag_name = x["descKey"]
    if not tag_id.startswith("selftag_") \
        and not tag_id.startswith("specialmission_") \
        and not tag_name == "Placeholder":
        dict_tags_by_id[tag_id] = [tag_name]
    
for x in categoryList_ENG_US:
    tag_id = x["id"]
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
for x in unitsList_FRE_FR:
    for tag in x["categoryIdList"]:
        if tag in dict_tags_by_id:
            for tag_name in dict_tags_by_id[tag]:
                id_name = [x["baseId"], x["nameKey"], x["combatType"]]
                if tag_name in dict_categories_by_name:
                    if not id_name in dict_categories_by_name[tag_name]:
                        dict_categories_by_name[tag_name].append(id_name)
                else:
                    dict_categories_by_name[tag_name] = [id_name]

fnew = open('DATA'+os.path.sep+'tagAlias_dict.json', 'w')
fnew.write(json.dumps(dict_categories_by_name, sort_keys=True, indent=4))
fnew.close()

categoryList_dict = {}
for category in categoryList_FRE_FR:
    if len(category["uiFilterList"])>0:
        if category['id'] in categoryList_dict:
            print('WAR: double definition of '+category['id'])
        categoryList_dict[category['id']] = category

fnew = open('DATA'+os.path.sep+'categoryList_dict.json', 'w')
fnew.write(json.dumps(categoryList_dict, sort_keys=True, indent=4))
fnew.close()
