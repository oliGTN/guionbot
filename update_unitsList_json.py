import sys
import json
import os

#####################################
# This script adapts the official file from SWGOH.HELP API
# It transfoms the initial list into a dictionary, with the unit_id as key
#####################################
unitsList = json.load(open('DATA'+os.path.sep+'unitsList.json', 'r'))

unitsList_dict = {}
unitsList_obtainable = [x for x in list(filter(lambda f:f['rarity']==7 and f['obtainable'] and f['obtainableTime']==0, unitsList))]
for unit in unitsList_obtainable:
    #if (not ':' in unit['id']):
        if unit['baseId'] in unitsList_dict:
            print('WAR: double definition of '+unit['baseId'])
        unitsList_dict[unit['baseId']] = unit

fnew = open('DATA'+os.path.sep+'unitsList_dict.json', 'w')
fnew.write(json.dumps(unitsList_dict, sort_keys=True, indent=4))
fnew.close()

############################################
# It also creates a dictionary of aliases from nameKeys
############################################
unitsList_FRE_FR_obtainable = unitsList_obtainable
unitsList_ENG_US = json.load(open('DATA'+os.path.sep+'unitsList_ENG_US.json', 'r'))
unitsList_ENG_US_obtainable = [x for x in list(filter(lambda f:f['rarity']==7 and f['obtainable'] and f['obtainableTime']==0, unitsList_ENG_US))]
#priority_names=["LEGENDARY", "S3", "GLREY", "HOTHREBELSOLDIER", "IMPERIALPROBEDROID", "AURRA_SING", "AMILYNHOLDO", "VULTUREDROID", "GRIEVOUS", "B1BATTLEDROIDV2", "THEMANDALORIAN", "VADER", "OBJ_CRATE_01", "SCOOTTROOPER"]
priority_names=["CT210408"]

unitsAlias_dict = {}
for unitsList in [unitsList_FRE_FR_obtainable, unitsList_ENG_US_obtainable]:
    for unit in unitsList:
        names = [unit['nameKey']]
        if '"' in unit['nameKey']:
            names += unit['nameKey'].split('"')
        if "" in names:
            names.remove("")
        for nameKey in names:
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
for x in unitsList_FRE_FR_obtainable:
    if x["combatType"] == 1:
        for tag in x["categoryIdList"]:
            if tag in dict_tags_by_id:
                for tag_name in dict_tags_by_id[tag]:
                    id_name = [x["baseId"], x["nameKey"]]
                    if tag_name in dict_categories_by_name:
                        if not id_name in dict_categories_by_name[tag_name]:
                            dict_categories_by_name[tag_name].append(id_name)
                    else:
                        dict_categories_by_name[tag_name] = [id_name]

fnew = open('DATA'+os.path.sep+'tagAlias_dict.json', 'w')
fnew.write(json.dumps(dict_categories_by_name, sort_keys=True, indent=4))
fnew.close()
