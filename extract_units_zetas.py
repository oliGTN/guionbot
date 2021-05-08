import sys
import json
import os

unitsList = json.load(open('DATA'+os.path.sep+'unitsList.json', 'r'))
abilityList = json.load(open('DATA'+os.path.sep+'abilityList.json', 'r'))
skillList = json.load(open('DATA'+os.path.sep+'skillList.json', 'r'))

dict_abilities={}
for ability in abilityList:
    dict_abilities[ability['id']] = [ability['nameKey'], False, '']
for skill in skillList:
    dict_abilities[skill['abilityReference']][1] = skill['isZeta']
    dict_abilities[skill['abilityReference']][2] = skill['id']


#print(dict_abilities)

list_lines=[]
dict_unit_abilities={}
for unit in unitsList:
    #print(unit)
    if unit['id'][-11:]==':SEVEN_STAR' \
        and unit['obtainable']==True \
        and not (unit['baseId'][-5:]=='EVENT') \
        and not (unit['baseId'][-4:]=='DUEL') :
        line=unit['nameKey']+'|'+unit['baseId']
        dict_unit_abilities[unit['baseId']] = {}
        
        #Basic
        for ability in [unit['basicAttackRef']]:
            if ability != None:
                if dict_abilities[ability['abilityId']][1]:
                    line+='|'+dict_abilities[ability['abilityId']][0]
                dict_unit_abilities[unit['baseId']]['B'] = dict_abilities[ability['abilityId']]
        
        #Leader
        for ability in [unit['leaderAbilityRef']]:
            if ability != None:
                if dict_abilities[ability['abilityId']][1]:
                    line+='|'+dict_abilities[ability['abilityId']][0]
                dict_unit_abilities[unit['baseId']]['L'] = dict_abilities[ability['abilityId']]

        #Specials
        id_spe = 1
        for ability in unit['limitBreakRefList']:
            if ability != None:
                if dict_abilities[ability['abilityId']][1]:
                    line+='|'+dict_abilities[ability['abilityId']][0]
                dict_unit_abilities[unit['baseId']]['S'+str(id_spe)] = dict_abilities[ability['abilityId']]
                id_spe += 1
                
        #Uniques
        id_unique = 1
        for ability in unit['uniqueAbilityRefList']:
            if ability != None:
                if ability['abilityId'] == 'uniqueability_galacticlegend01':
                    if dict_abilities[ability['abilityId']][1]:
                        line+='|'+dict_abilities[ability['abilityId']][0]
                    dict_unit_abilities[unit['baseId']]['GL'] = dict_abilities[ability['abilityId']]
                else:
                    if dict_abilities[ability['abilityId']][1]:
                        line+='|'+dict_abilities[ability['abilityId']][0]
                    dict_unit_abilities[unit['baseId']]['U'+str(id_unique)] = dict_abilities[ability['abilityId']]
                    id_unique += 1                
                
        list_lines.append(line)

f = open('DATA'+os.path.sep+'unit_zeta_list.json', 'w')
f.write(json.dumps(dict_unit_abilities, indent=4, sort_keys=True))
f.close()
        
for line in sorted(list_lines):
    print(line)
