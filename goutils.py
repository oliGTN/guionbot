# -*- coding: utf-8 -*-
import json
import math

##############################################################
# Function: pad_txt
# Parameters: txt (string) > texte à modifier
#             size (intereger) > taille cible pour le texte
# Purpose: ajoute des espaces pour atteindre la taille souhaitée
# Output: ret_pad_txt (string) = txt avec des espaces au bout
##############################################################
def pad_txt(txt, size):
    if len(txt) < size:
        ret_pad_txt = txt + ' ' * (size - len(txt))
    else:
        ret_pad_txt = txt[:size]

    return ret_pad_txt


##############################################################
# Function: pad_txt2
# Parameters: txt (string) > texte à modifier
# Purpose: ajoute des espaces pour atteindre la taille souhaitée
#          dans un affichae Discord où les caractères n'ont pas la même taille
#          Le texte est mis à la taille la plus large possible pour un texte de ce nombre de caractères (cas pire)
# Output: ret_pad_txt (string) = txt avec des espaces au bout
##############################################################
def pad_txt2(txt):
    #pixels mesurés en entrant 20 fois le caractère entre 2 "|"
    size_chars = {}
    size_chars['0'] = 12.3
    size_chars['1'] = 7.1
    size_chars['2'] = 10.7
    size_chars['3'] = 10.5
    size_chars['4'] = 11.9
    size_chars['5'] = 10.6
    size_chars['6'] = 11.4
    size_chars['7'] = 10.6
    size_chars['8'] = 11.4
    size_chars['9'] = 11.4
    size_chars[' '] = 4.5
    size_chars['R'] = 11.3
    size_chars['I'] = 5.3
    size_chars['.'] = 4.4
    padding_char = ' '

    size_txt = 0
    nb_sizeable_chars = 0
    for c in size_chars:
        size_txt += txt.count(c) * size_chars[c]
        nb_sizeable_chars += txt.count(c)
        #print ('DBG: c='+c+' size_txt='+str(size_txt)+' nb_sizeable_chars='+str(nb_sizeable_chars))

    max_size = nb_sizeable_chars * max(size_chars.values())
    nb_padding = round((max_size - size_txt) / size_chars[padding_char])
    #print('DBG: max_size='+str(max_size)+'size='+str(size_txt)+' nb_padding='+str(nb_padding))
    ret_pad_txt = txt + padding_char * nb_padding
    #print('DBG: x'+txt+'x > x'+ret_pad_txt+'x')

    return ret_pad_txt


##############################################################
# Function: split_txt
# Parameters: txt (string) > long texte à couper en morceaux
#             max_size (int) > taille max d'un morceau
# Purpose: découpe un long texte en morceaux de taille maximale donnée
#          en coupant des lignes entières (caractère '\n')
#          Cette fonction est utilisée pour afficher de grands textes dans Discord
# Output: tableau de texte de taille acceptable
##############################################################
FORCE_CUT_PATTERN = "SPLIT_HERE"


def split_txt(txt, max_size):
    ret_split_txt = []
    remaining_txt = txt
    while len(txt) > max_size:
        force_split = txt.rfind(FORCE_CUT_PATTERN, 0, max_size)
        if force_split != -1:
            ret_split_txt.append(txt[:force_split])
            txt = txt[force_split + len(FORCE_CUT_PATTERN):]
            continue

        last_cr = -1
        last_cr = txt.rfind("\n", 0, max_size)
        if last_cr == -1:
            ret_split_txt.append(txt[-3] + '...')
            txt = ''
        else:
            ret_split_txt.append(txt[:last_cr])
            txt = txt[last_cr + 1:]
    ret_split_txt.append(txt)

    return ret_split_txt


##############################################################
# Function: get_character_stats
# Parameters: dict_character > dictionaire tel que renvoyé par swgoh.help API (voir dans le json)
# Purpose: renvoie la vitesse et le pouvoir en fonction du gear, des équipements et des mods
# Output: [base_stats[1:61], eqpt_stats[1:61], mod_stats[1:61]]
##############################################################
def get_character_stats(dict_character):
    
    gameData = json.load(open('gameData.json', 'r'))

    if dict_character['combatType'] == 2:
        #no stats for ships
        return None, None, None
        
    char_defId = dict_character['defId']
    char_gear = dict_character['gear']
    char_rarity = dict_character['rarity']
    char_level = dict_character['level']
    char_relic_currentTier = 0
    if 'currentTier' in dict_character['relic']:
        char_relic_currentTier = dict_character['relic']['currentTier']

    ########################################
    # getCharRawStats from crinolo
    ########################################

    # Base stats of the character, up to G12
    base_stats = {}
    for i in range(1, 62):
        base_stats[i] = 0
    for statID in gameData['unitData'][char_defId]['gearLvl'][str(char_gear)]['stats']:
        base_stats[int(statID)] = gameData['unitData'][char_defId]['gearLvl'][str(char_gear)]['stats'][statID]
    # print('base_stats='+str(base_stats))

    growthModifiers_stats = {2:0, 3:0, 4:0}
    for statID in gameData['unitData'][char_defId]['growthModifiers'][str(char_rarity)]:
        growthModifiers_stats[int(statID)] = gameData['unitData'][char_defId]['growthModifiers'][str(char_rarity)][statID]
    # print('growthModifiers_stats='+str(growthModifiers_stats))
    
    # manage equipment
    gear_stats = {}
    for i in range(1, 62):
        gear_stats[i] = 0
        
    if 'equipped' in dict_character:
        for eqpt in dict_character['equipped']:
            if eqpt['equipmentId'] != 'None':
                gearStats = gameData['gearData'][eqpt['equipmentId']]['stats']
                for statID in gearStats:
                    if (statID == '2' or statID == '3' or statID == '4'):
                        # Primary Stat, applies before mods
                        base_stats[ int(statID) ] += gearStats[ statID ]
                    else:
                        #Secondary Stat, applies after mods
                        gear_stats[ int(statID) ] += gearStats[ statID ]
    
    # Manage relic level (base_stats stop at G12)
    if (char_relic_currentTier > 2):
        # calculate stats from relics
        relic = gameData['relicData'][ gameData['unitData'][char_defId]['relic'][ str(char_relic_currentTier) ] ];
        for statID in relic['stats']:
            base_stats[ int(statID) ] += relic['stats'][ statID ]
            
        for statID in relic['gms']:
            growthModifiers_stats[ int(statID) ] += relic['gms'][ statID ]
            
    ########################################
    # calculateBaseStats from crinolo
    ########################################
    # calculate bonus Primary stats from Growth Modifiers:
    base_stats[2] += math.floor( growthModifiers_stats[2] * char_level ) # Strength
    base_stats[3] += math.floor( growthModifiers_stats[3] * char_level ) # Agility
    base_stats[4] += math.floor( growthModifiers_stats[4] * char_level ) # Tactics
    # print('base_stats='+str(base_stats))
    
    if 61 in base_stats:
        # calculate effects of Mastery on Secondary stats:
        mms = gameData['crTables'][ gameData['unitData'][char_defId]['masteryModifierID'] ]
        for statID in mms:
            base_stats[ int(statID) ] += base_stats[61]*mms[ statID ]
    # print('base_stats='+str(base_stats))

    # calculate effects of Primary stats on Secondary stats:
    base_stats[1] = base_stats[1] + base_stats[2] * 18;                                          # Health += STR * 18
    base_stats[6] = math.floor( base_stats[6] + base_stats[ gameData['unitData'][char_defId]['primaryStat'] ] * 1.4 )           # Ph. Damage += MainStat * 1.4
    base_stats[7] = math.floor( base_stats[7] + base_stats[4] * 2.4 )                            # Sp. Damage += TAC * 2.4
    base_stats[8] = math.floor( base_stats[8] + base_stats[2] * 0.14 + base_stats[3] * 0.07 )    # Armor += STR*0.14 + AGI*0.07
    base_stats[9] = math.floor( base_stats[9] + base_stats[4] * 0.1 )                            # Resistance += TAC * 0.1
    base_stats[14] = math.floor( base_stats[14] + base_stats[3] * 0.4 )                          # Ph. Crit += AGI * 0.4
    # add hard-coded minimums or potentially missing stats
    base_stats[12] = base_stats[12] + (24 * 1e8)  # Dodge (24 -> 2%)
    base_stats[13] = base_stats[13] + (24 * 1e8)  # Deflection (24 -> 2%)
    base_stats[15] = base_stats[15]               # Sp. Crit
    base_stats[16] = base_stats[16] + (150 * 1e6) # +150% Crit Damage
    base_stats[18] = base_stats[18] + (15 * 1e6)  # +15% Tenacity
    # print('base_stats='+str(base_stats))

    ########################################
    # calculateModStats from crinolo
    ########################################
    rawModStats = {}
    for i in range(1, 62):
        rawModStats[i] = 0
        
    modStats = {}
    for i in range(1, 62):
        modStats[i] = 0
        
    if 'mods' in dict_character:
        setBonuses = {}
        for mod in dict_character['mods']:
            # add to set bonuses counters (same for both formats)
            if (mod['set'] in setBonuses) :
                # set bonus already found, increment
                setBonuses[ mod['set'] ]['count'] += 1
            else :
                # new set bonus, create object
                setBonuses[ mod['set'] ]={'count':1, 'maxLevel':0}
            if (mod['level'] == 15):
                setBonuses[ mod['set'] ]['maxLevel'] += 1
    
            # using /player.roster format
            stat = mod['primaryStat']
            if (stat['unitStat'] == 1 or
                stat['unitStat'] == 5 or
                stat['unitStat'] == 28 or
                stat['unitStat'] == 41 or
                stat['unitStat'] == 42):
                # Flat stats
                scaleStatValue = stat['value'] * 1e8
            else:
                # Percent stats
                scaleStatValue = stat['value'] * 1e6
            
            rawModStats[ stat['unitStat'] ] += scaleStatValue
            
            for stat in mod['secondaryStat']:
                if (stat['unitStat'] == 1 or
                    stat['unitStat'] == 5 or
                    stat['unitStat'] == 28 or
                    stat['unitStat'] == 41 or
                    stat['unitStat'] == 42):
                    # Flat stats
                    scaleStatValue = stat['value'] * 1e8
                else:
                    # Percent stats
                    scaleStatValue = stat['value'] * 1e6
                
                rawModStats[ stat['unitStat'] ] += scaleStatValue
            

    # print('rawModStats='+str(rawModStats))
    # print('setBonuses='+str(setBonuses))
    # add stats given by set bonuses
    for setID in setBonuses:
        setDef = gameData['modSetData'][str(setID)]
        count = setBonuses[setID]['count']
        maxCount = setBonuses[setID]['maxLevel']
        multiplier = math.floor(count / setDef['count']) + math.floor(maxCount / setDef['count'])
        rawModStats[ setDef['id'] ] += (setDef['value'] * multiplier)
    # print('rawModStats='+str(rawModStats))

    # calculate actual stat bonuses from mods
    for statID in rawModStats:
        value = rawModStats[ statID ]
        if statID == 41: # Offense
            modStats[6] += value # Ph. Damage
            modStats[7] += value # Sp. Damage
        elif statID == 42: # Defense
            modStats[8] += value # Armor
            modStats[9] += value # Resistance
        elif statID == 48: # Offense %
            modStats[6] = math.floor( modStats[6] + base_stats[6] * 1e-8 * value) # Ph. Damage
            modStats[7] = math.floor( modStats[7] + base_stats[7] * 1e-8 * value) # Sp. Damage
        elif statID == 49: # Defense %
            modStats[8] = math.floor( modStats[8] + base_stats[8] * 1e-8 * value) # Armor
            modStats[9] = math.floor( modStats[9] + base_stats[9] * 1e-8 * value) # Resistance
        elif statID == 53: # Crit Chance
            modStats[21] += value # Ph. Crit Chance
            modStats[22] += value # Sp. Crit Chance
        elif statID == 54: # Crit Avoid
            modStats[35] += value # Ph. Crit Avoid
            modStats[36] += value # Ph. Crit Avoid
        elif statID == 55: # Heatlth %
            modStats[1] = math.floor( modStats[1] + base_stats[1] * 1e-8 * value) # Health
        elif statID == 56: # Protection %
            modStats[28] = math.floor( modStats[28] + base_stats[28] * 1e-8 * value) # Protection may not exist in base
        elif statID == 57: # Speed %
            modStats[5] = math.floor( modStats[5] + base_stats[5] * 1e-8 * value) # Speed
        else:
            # other stats add like flat values
            modStats[ statID ] += value
    

    # print('base_stats='+str(base_stats))
    # print('gear_stats='+str(gear_stats))
    # print('modStats='+str(modStats))
    return base_stats, gear_stats, modStats


def create_dict_player_for_stats(player_data, player_mods):
    dict_player={"level": player_data[0][5],
                "name": player_data[0][0],
                "roster": {}}
    
    cur_defId = ''
    for line in player_data:
        line_defId = line[2]
        if cur_defId != line_defId:
            line_nameKey = line[3]
            line_combatType = line[4]
            line_gear = line[5]
            line_rarity = line[6]
            line_level = line[7]
            line_relic_currentTier = line[8]
            dict_player["roster"][line_defId] = {"defId": line_defId,
                                                 "nameKey": line_nameKey,
                                                 "combatType": line_combatType,
                                                 "gear": line_gear,
                                                 "rarity": line_rarity,
                                                 "level": line_level,
                                                 "relic": {"currentTier": line_relic_currentTier},
                                                 "equipped": [],
                                                 "mods": []}
            cur_defId = line_defId
            
        line_eqpt = line[9]
        dict_player["roster"][line_defId]["equipped"].append({"equipmentId": str(line_eqpt)})
    
    cur_mod_id = -1
    for line in player_mods:
        line_defId = line[0]
        line_mod_id = line[1]
        if cur_mod_id != line_mod_id:
            line_mod_level = line[2]
            line_mod_set = line[3]
            dict_player["roster"][line_defId]["mods"].append({"level": line_mod_level,
                                                              "set": line_mod_set,
                                                              "secondaryStat": []})
            cur_mod_id = line_mod_id
            
        line_unitStat = line[4]
        line_value = line[5]
        # all stats are considered secondary as it does not change the global computation
        dict_player["roster"][line_defId]["mods"][-1] \
            ["secondaryStat"].append({"unitStat": line_unitStat,
                                      "value": line_value})
                                      
    return dict_player
    
def create_dict_guild_for_stats(guild_data, guild_mods):
    dict_players={}
    
    cur_allyCode = ''
    for line in guild_data:
        line_allyCode = str(line[1])
        if cur_allyCode != line_allyCode:
            line_name = line[0]
            line_defId = line[2]
            line_nameKey = line[3]
            line_combatType = line[4]
            line_gear = line[5]
            line_rarity = line[6]
            line_level = line[7]
            line_relic_currentTier = line[8]
            dict_players[line_allyCode] = {"allyCode": line_allyCode,
                                           "name": line_name,
                                           "roster": {line_defId: {}}}
            
            dict_players[line_allyCode]["roster"] \
                [line_defId] = { "defId": line_defId,
                                 "nameKey": line_nameKey,
                                 "combatType": line_combatType,
                                 "gear": line_gear,
                                 "rarity": line_rarity,
                                 "level": line_level,
                                 "relic": {"currentTier": line_relic_currentTier},
                                 "equipped": [],
                                 "mods": []}
            cur_allyCode = line_allyCode
            
        line_eqpt = line[9]
        dict_players[line_allyCode]["roster"][line_defId] \
            ["equipped"].append({"equipmentId": str(line_eqpt)})
    
    cur_mod_id = -1
    for line in guild_mods:
        line_allyCode = str(line[0])
        line_defId = line[1]
        line_mod_id = line[2]
        if cur_mod_id != line_mod_id:
            line_mod_level = line[3]
            line_mod_set = line[4]
            dict_players[line_allyCode]["roster"][line_defId] \
                ["mods"].append({ "level": line_mod_level,
                                  "set": line_mod_set,
                                  "secondaryStat": []})
            cur_mod_id = line_mod_id
            
        line_unitStat = line[5]
        line_value = line[6]
        # all stats are considered secondary as it does not change the global computation
        dict_players[line_allyCode]["roster"][line_defId]["mods"][-1] \
            ["secondaryStat"].append({"unitStat": line_unitStat,
                                      "value": line_value})
                                      
    return dict_players
    
def create_dict_guild_for_teams(guild_data):
    dict_players={}
    
    cur_allyCode = ''
    cur_defId = ''
    for line in guild_data:
        line_allyCode = str(line[0])
        line_name = str(line[1])
        if cur_allyCode != line_allyCode:
            dict_players[line_allyCode] = {"allyCode": line_allyCode,
                                           "name": line_name,
                                           "roster": {}}
            cur_allyCode = line_allyCode
        
        line_defId = line[2]
        if cur_defId != line_defId:
            line_rarity = line[3]
            line_gear = line[4]
            line_relic_currentTier = line[5]
            line_combatType = line[6]
            line_gp = line[7]
            
            dict_players[line_allyCode]["roster"] \
                [line_defId] = { "defId": line_defId,
                                 "combatType": line_combatType,
                                 "gear": line_gear,
                                 "gp": line_gp,
                                 "rarity": line_rarity,
                                 "relic": {"currentTier": line_relic_currentTier},
                                 "skills": []}
            cur_defId = line_defId
            
        line_skill_name = line[8]
        line_skill_level = line[9]
        line_skill_isZeta = line[10]
        dict_players[line_allyCode]["roster"][line_defId] \
            ["skills"].append({"id": line_skill_name,
                                "tier": line_skill_level,
                                "isZeta": (line_skill_isZeta==1)})
                                      
    return dict_players
    
def create_dict_player_for_teams(player_data):
    dict_player={"allyCode": player_data[0][0],
                "name": player_data[0][1],
                "roster": {}}
    
    cur_defId = ''
    for line in player_data:
        line_defId = line[2]
        if cur_defId != line_defId:
            line_rarity = line[3]
            line_gear = line[4]
            line_relic_currentTier = line[5]
            line_combatType = line[6]
            line_gp = line[7]
            
            dict_player["roster"][line_defId] = { \
                                 "defId": line_defId,
                                 "combatType": line_combatType,
                                 "gear": line_gear,
                                 "gp": line_gp,
                                 "rarity": line_rarity,
                                 "relic": {"currentTier": line_relic_currentTier},
                                 "skills": []}
            cur_defId = line_defId
            
        line_skill_name = line[8]
        line_skill_level = line[9]
        line_skill_isZeta = line[10]
        dict_player["roster"][line_defId]["skills"].append({ \
                                "id": line_skill_name,
                                "tier": line_skill_level,
                                "isZeta": (line_skill_isZeta==1)})
                                      
    return dict_player
    
def create_dict_stats(db_stat_data):
    dict_players={}

    cur_name = ''
    for line in db_stat_data:
        line_name = line[0]
        if cur_name != line_name:
            dict_players[line_name]={}
            cur_defId = ''
            cur_name = line_name
        
        line_defId = line[1]
        if cur_defId != line_defId:
            line_nameKey = line[2]
            line_combatType = line[3]
            line_rarity = line[4]
            line_gear = line[5]
            line_relic_currentTier = line[6]
            dict_players[line_name][line_defId]={ \
                    "nameKey": line_nameKey,
                    "combatType": line_combatType,
                    "rarity": line_rarity,
                    "gear": line_gear,
                    "relic": {"currentTier": line_relic_currentTier},
                    "stats": {}}
            cur_defId = line_defId
            
        line_unitStatId = line[7]
        line_unscaledDecimalValue = line[8]

        dict_players[line_name][line_defId]["stats"][line_unitStatId] = \
            int(line_unscaledDecimalValue)
                                      
    return dict_players