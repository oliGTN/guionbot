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
    if len(ability["tierList"]) > 0:
        upgradeKey_lastTier = ability["tierList"][-1]["upgradeDescKey"]
        if upgradeKey_lastTier.lower().startswith("[c][e7e7e7]"):
            if "pendant une guerre de territoire" in upgradeKey_lastTier.lower():
                omicron_type = "TW"
            elif "dans les guerres de territoire" in upgradeKey_lastTier.lower():
                omicron_type = "TW"
            elif "pendant une bataille de territoire" in upgradeKey_lastTier.lower():
                omicron_type = "TW"
            elif "dans les batailles de territoire" in upgradeKey_lastTier.lower():
                omicron_type = "TW"
            elif "en grande ar\u00e8ne" in upgradeKey_lastTier.lower():
                omicron_type = "GA"

    dict_abilities[ability['id']] = [ability['nameKey'], False, '', omicron_type]
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
    
    #Basic
    for ability in [unit['basicAttackRef']]:
        if ability != None:
            #if dict_abilities[ability['abilityId']][1]:
                #line+='|'+dict_abilities[ability['abilityId']][0]
            dict_unit_abilities[unit['baseId']]['B'] = dict_abilities[ability['abilityId']]
            skill_name = dict_abilities[ability['abilityId']][0]
            skill_id = dict_abilities[ability['abilityId']][2]
            skill_isZeta = dict_abilities[ability['abilityId']][1]
            skill_omicron = dict_abilities[ability['abilityId']][3]
            dict_unit_abilities[unit['baseId']][skill_id] = [skill_name, 'Basique', skill_isZeta, skill_omicron]
    
    #Leader
    for ability in [unit['leaderAbilityRef']]:
        if ability != None:
            #if dict_abilities[ability['abilityId']][1]:
                #line+='|'+dict_abilities[ability['abilityId']][0]
            dict_unit_abilities[unit['baseId']]['L'] = dict_abilities[ability['abilityId']]
            skill_name = dict_abilities[ability['abilityId']][0]
            skill_id = dict_abilities[ability['abilityId']][2]
            skill_isZeta = dict_abilities[ability['abilityId']][1]
            skill_omicron = dict_abilities[ability['abilityId']][3]
            dict_unit_abilities[unit['baseId']][skill_id] = [skill_name, 'Leader', skill_isZeta, skill_omicron]

    #Specials
    id_spe = 1
    for ability in unit['limitBreakRefList']:
        if ability != None:
            #if dict_abilities[ability['abilityId']][1]:
                #line+='|'+dict_abilities[ability['abilityId']][0]
            dict_unit_abilities[unit['baseId']]['S'+str(id_spe)] = dict_abilities[ability['abilityId']]
            skill_name = dict_abilities[ability['abilityId']][0]
            skill_id = dict_abilities[ability['abilityId']][2]
            skill_isZeta = dict_abilities[ability['abilityId']][1]
            skill_omicron = dict_abilities[ability['abilityId']][3]
            dict_unit_abilities[unit['baseId']][skill_id] = [skill_name, 'Spéciale '+str(id_spe), skill_isZeta, skill_omicron]
            id_spe += 1
            
    #Uniques
    id_unique = 1
    for ability in unit['uniqueAbilityRefList']:
        if ability != None:
            if ability['abilityId'] == 'uniqueability_galacticlegend01':
                #if dict_abilities[ability['abilityId']][1]:
                    #line+='|'+dict_abilities[ability['abilityId']][0]
                dict_unit_abilities[unit['baseId']]['GL'] = dict_abilities[ability['abilityId']]
                skill_name = dict_abilities[ability['abilityId']][0]
                skill_id = dict_abilities[ability['abilityId']][2]
                skill_isZeta = dict_abilities[ability['abilityId']][1]
                skill_omicron = dict_abilities[ability['abilityId']][3]
                dict_unit_abilities[unit['baseId']][skill_id] = [skill_name, 'Légende Galactique', skill_isZeta, skill_omicron]
            else:
                #if dict_abilities[ability['abilityId']][1]:
                    #line+='|'+dict_abilities[ability['abilityId']][0]
                dict_unit_abilities[unit['baseId']]['U'+str(id_unique)] = dict_abilities[ability['abilityId']]
                skill_name = dict_abilities[ability['abilityId']][0]
                skill_id = dict_abilities[ability['abilityId']][2]
                skill_isZeta = dict_abilities[ability['abilityId']][1]
                skill_omicron = dict_abilities[ability['abilityId']][3]
                dict_unit_abilities[unit['baseId']][skill_id] = [skill_name, 'Unique '+str(id_unique), skill_isZeta, skill_omicron]
                id_unique += 1                
            
    #list_lines.append(line)

f = open('DATA'+os.path.sep+'unit_zeta_list.json', 'w')
f.write(json.dumps(dict_unit_abilities, indent=4, sort_keys=True))
f.close()
        
#for line in sorted(list_lines):
    #print(line)
