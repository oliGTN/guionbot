import sys
import json
import os

unitsList = json.load(open('DATA'+os.path.sep+'unitsList.json', 'r'))
abilityList = json.load(open('DATA'+os.path.sep+'abilityList.json', 'r'))
skillList = json.load(open('DATA'+os.path.sep+'skillList.json', 'r'))

dict_abilities={}
for ability in abilityList:
    #Look for Omicron
    omicron_type = ""
    omicron_tier = -1
    if len(ability["tierList"]) > 0:
        upgradeKey_lastTier = ability["tierList"][-1]["upgradeDescKey"]
        if upgradeKey_lastTier.lower().startswith("[c][e7e7e7]"):
            omicron_tier = len(ability["tierList"])+1
            if "pendant une guerre de territoire" in upgradeKey_lastTier.lower():
                omicron_type = "TW"
            elif "dans les guerres de territoire" in upgradeKey_lastTier.lower():
                omicron_type = "TW"
            elif "pendant une bataille de territoire" in upgradeKey_lastTier.lower():
                omicron_type = "TB"
            elif "dans les batailles de territoire" in upgradeKey_lastTier.lower():
                omicron_type = "TB"
            elif "en grande ar\u00e8ne" in upgradeKey_lastTier.lower():
                omicron_type = "GA"
            elif "en grandes ar\u00e8nes" in upgradeKey_lastTier.lower():
                omicron_type = "GA"
            else:
                print("Unknown omicron type for "+ability['id'])
                omicron_type="??"

    dict_abilities[ability['id']] = [ability['nameKey'], False, '', omicron_type, omicron_tier]
for skill in skillList:
    dict_abilities[skill['abilityReference']][1] = skill['isZeta']
    dict_abilities[skill['abilityReference']][2] = skill['id']


#print(dict_abilities)

list_lines=[]
dict_unit_abilities={}
unitsList_obtainable = [x for x in list(filter(lambda f:f['rarity']==7 and f['obtainable'] and f['obtainableTime']==0, unitsList))]
for unit in unitsList_obtainable:
    line=unit['nameKey']+'|'+unit['baseId']
    dict_unit_abilities[unit['baseId']] = {}
    
    for [ref_name, capa_type, capa_short, isIterable, sec_ref, sec_type, sec_short] in \
            [['basicAttackRef', 'Basique', 'B', False, '', '', ''],
             ['leaderAbilityRef', 'Leader', 'L', False, '', '', ''],
             ['limitBreakRefList', 'Spéciale', 'S', True, '', '', ''],
             ['uniqueAbilityRefList', 'Unique', 'U', True, 'uniqueability_galacticlegend01', 'Légende Galactique', 'GL']]:

        if not isIterable:
            list_abilities = [unit[ref_name]]
        else:
            list_abilities = unit[ref_name]

        for ability in list_abilities:
            id_ability = 1
            if ability != None:
                if ability['abilityId'] == sec_ref:
                    capa_short_txt = sec_short
                else:
                    if isIterable:
                        capa_short_txt = capa_short + str(id_ability)
                    else:
                        capa_short_txt = capa_short

                dict_unit_abilities[unit['baseId']][capa_short_txt] = dict_abilities[ability['abilityId']]
                skill_name = dict_abilities[ability['abilityId']][0]
                skill_id = dict_abilities[ability['abilityId']][2]
                skill_isZeta = dict_abilities[ability['abilityId']][1]
                skill_omicron_type = dict_abilities[ability['abilityId']][3]
                skill_omicron_tier = dict_abilities[ability['abilityId']][4]

                if ability['abilityId'] == sec_ref:
                    capa_type_txt = sec_type
                else:
                    if isIterable:
                        capa_type_txt = capa_type + " " + str(id_ability)
                    else:
                        capa_type_txt = capa_type

                dict_unit_abilities[unit['baseId']][skill_id] = [skill_name, capa_type_txt, skill_isZeta, skill_omicron_type, skill_omicron_tier]
                id_ability += 1
    
    #list_lines.append(line)

f = open('DATA'+os.path.sep+'unit_capa_list.json', 'w')
f.write(json.dumps(dict_unit_abilities, indent=4, sort_keys=True))
f.close()
        
#for line in sorted(list_lines):
    #print(line)
