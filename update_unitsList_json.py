import sys
import json
import os

#####################################
# This script adapts the offcial file from SWGOH.HELP API
# It transfoms the initial list into a dictionary, with the unit_id as key
#####################################
unitsList = json.load(open('DATA'+os.path.sep+'unitsList.json', 'r'))

unitsList_dict = {}
for unit in unitsList:
    if (not ':' in unit['id']):
        if unit['id'] in unitsList_dict:
            print('WAR: double definition of '+unit['id'])
        unitsList_dict[unit['id']] = unit

fnew = open('DATA'+os.path.sep+'unitsList_dict.json', 'w')
fnew.write(json.dumps(unitsList_dict, sort_keys=True, indent=4))
fnew.close()

############################################
# It also creates a dictionary of aliases from nameKeys
############################################
unitsList_FRE_FR = unitsList
unitsList_ENG_US = json.load(open('DATA'+os.path.sep+'unitsList_ENG_US.json', 'r'))
priority_names=["LEGENDARY", "S3", "GLREY", "HOTHREBELSOLDIER", "IMPERIALPROBEDROID", "AURRA_SING", "AMILYNHOLDO", "VULTUREDROID", "GRIEVOUS", "B1BATTLEDROIDV2", "THEMANDALORIAN", "VADER", "OBJ_CRATE_01", "SCOOTTROOPER"]
unitsAlias_dict = {}
for unitsList in [unitsList_FRE_FR, unitsList_ENG_US]:
    for unit in unitsList:
        if (not ':' in unit['id']) and not "EVENT" in unit['id'] \
                                   and not "PVE" in unit['id'] \
                                   and not "DUEL" in unit['id']:
            #manage characters with number and nickname (eg: clones)
            names = unit['nameKey'].split('"')
            if "" in names:
                names.remove("")
            for nameKey in names:
                if nameKey in unitsAlias_dict:
                    if unitsAlias_dict[nameKey][1] != unit['id']:
                        prio_found = False
                        for prio in priority_names:
                            if prio in unit['id']:
                                unitsAlias_dict[nameKey] = [unitsList_dict[unit['id']]['nameKey'], unit['id']]
                                prio_found = True
                            elif prio in unitsAlias_dict[nameKey][1]:
                                prio_found = True
                        if not prio_found:
                            print('WAR: double definition of '+nameKey)
                            print(unitsAlias_dict[nameKey][1])
                            print(unit['id'])
                    else:
                        pass
                else:
                    unitsAlias_dict[nameKey] = [unitsList_dict[unit['id']]['nameKey'], unit['id']]

fnew = open('DATA'+os.path.sep+'unitsAlias_dict.json', 'w')
fnew.write(json.dumps(unitsAlias_dict, sort_keys=True, indent=4))
fnew.close()
