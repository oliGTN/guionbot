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
def get_unit_stats(dict_unit, dict_player):
    if dict_unit['combatType'] == 2:
        return get_ship_stats(dict_unit, dict_player)
    else:
        return get_character_stats(dict_unit)

def get_ship_stats(ship, dict_player):
    gameData = json.load(open('gameData.json', 'r'))

    list_crewId = [x["unitId"] for x in ship["crew"]]
    print(list_crewId)
    crew = list(filter(lambda x: x["defId"] in list_crewId, dict_player["roster"]))
    print(crew)
    stats = getShipRawStats(ship, crew, gameData)
    print(stats)
    stats = calculateBaseStats(stats, ship["level"], ship["defId"])
    stats = formatStats(stats, ship["level"])
    stats = renameStats(stats)
    
def getShipRawStats(ship, crew, gameData):
    unitData = gameData["unitData"]
    crTables = gameData["crTables"]
    
    # ensure crew is the correct crew
    if len(crew) != len(unitData[ship["defId"]]["crew"]):
        print("Incorrect number of crew members for ship "+ship["defId"])

    for char in crew:
        print(char)
        if not char["defId"] in unitData[ship["defId"]]["crew"]:
            print("Unit "+char["defId"]+" is not in "+ship["defId"]+"'s crew")

    # if still here, crew is good -- go ahead and determine stats
    crewRating = getCrewRating(crew, gameData)
    stats = {"base": unitData[ship["defId"]]["stats"],
            "crew": {},
            "growthModifiers": unitData[ship["defId"]]["growthModifiers"][str(ship["rarity"])]}

    for txt_statID in unitData[ship["defId"]]["crewStats"]:
        statValue = unitData[ship["defId"]]["crewStats"][txt_statID]
        statID = int(txt_statID)
        # stats 1-15 and 28 all have final integer values
        # other stats require decimals -- shrink to 8 digits of precision through 'unscaled' values this calculator uses
        stats["crew"][ statID ] = statValue * \
                                    crTables["shipRarityFactor"][str(ship["rarity"])] * \
                                    crewRating

    return stats

def getCrewRating(crew, gameData):
    crTables = gameData["crTables"]

    totalCR = 0
    for char in crew:
        crewRating = 0
        crewRating += crTables["unitLevelCR"][ str(char["level"]) ] + \
                      crTables["crewRarityCR"][ str(char["rarity"]) ] # add CR from level/rarity
        
        for gearLvl in range(1, char["gear"]):
            crewRating += crTables["gearPieceCR"][ str(gearLvl) ] * 6 # add CR from complete gear levels

        crewRating += crTables["gearPieceCR"][ str(char["gear"]) ] * len(char["equipped"]) # add CR from currently equipped gear
        
        for skill in char["skills"]:
            crewRating += getSkillCrewRating(skill, gameData) # add CR from ability levels
        for mod in char["mods"]:
            crewRating += crTables["modRarityLevelCR"][ str(mod["pips"]) ][ str(mod["level"]) ] # add CR from mods

        if char["relic"]["currentTier"] > 2:
            crewRating += crTables["relicTierCR"][ str(char["relic"]["currentTier"]) ]
            crewRating += char["level"] * \
                    crTables["relicTierLevelFactor"][ str(char["relic"]["currentTier"]) ]

        return crewRating;

    return totalCR # * crTables.crewSizeFactor[ crew.length ];

def getSkillCrewRating(skill, gameData):
    crTables = gameData["crTables"]
    return crTables["abilityLevelCR"][ str(skill["tier"]) ]

def get_character_stats(dict_character):
    gameData = json.load(open('gameData.json', 'r'))
        
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
    
def create_dict_teams(player_data, player_zeta_data):
    dict_players={}

    cur_playername = ''
    for line in player_data:
        line_playername = line[0]
        if cur_playername != line_playername:
            dict_players[line_playername]={}
            cur_teamname = ''
            cur_playername = line_playername
        
        line_teamname = line[1]
        if cur_teamname != line_teamname:
            dict_players[line_playername][line_teamname]={}
            cur_defId = ''
            cur_teamname = line_teamname
        
        line_defId = line[2]
        if cur_defId != line_defId:
            line_rarity = line[3]
            line_gear = line[4]
            line_relic_currentTier = line[5]
            line_gp = line[6]
            line_speed = int(line[7])
            dict_players[line_playername][line_teamname][line_defId]={ \
                    "rarity": line_rarity,
                    "gear": line_gear,
                    "rarity": line_rarity,
                    "gear": line_gear,
                    "relic_currentTier": line_relic_currentTier,
                    "gp": line_gp,
                    "speed": line_speed,
                    "zetas": {}}
            cur_defId = line_defId
            
    cur_playername = ''
    for line in player_zeta_data:
        line_playername = line[0]
        if cur_playername != line_playername:
            cur_teamname = ''
            cur_playername = line_playername
        
        line_teamname = line[1]
        if cur_teamname != line_teamname:
            cur_defId = ''
            cur_teamname = line_teamname
        
        line_defId = line[2]
        if cur_defId != line_defId:
            cur_zeta = ''
            cur_defId = line_defId

        line_zeta = line[3]
        if cur_zeta != line_zeta:
            line_level = line[4]
            dict_players[line_playername][line_teamname]\
                [line_defId]["zetas"][line_zeta]=line_level

            cur_zeta = line_zeta
            
    #print(dict_players)
    return dict_players
    
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
    
def get_zeta_from_shorts(character_id, zeta_shorts):
    dict_zetas = json.load(open('unit_zeta_list.json', 'r'))
    
    req_zeta_ids = []
    for zeta in zeta_shorts:
        zeta_id = get_zeta_id_from_short(character_id, zeta)
        if zeta_id == '':
            continue
        if zeta_id in dict_zetas[character_id]:
            if dict_zetas[character_id][zeta_id][1]:
                req_zeta_ids.append([zeta_id, dict_zetas[character_id][zeta_id][0]])
        else:
            print('WAR: cannot find zeta '+zeta+' for '+character_id)
    
    return req_zeta_ids

def get_zeta_id_from_short(character_id, zeta_short):
    dict_zetas = json.load(open('unit_zeta_list.json', 'r'))

    zeta_standard = zeta_short.upper().replace(' ', '')
    if zeta_standard == '':
        return ''
    elif zeta_standard[0] == 'B':
        zeta_id = 'B'
    elif zeta_standard[0] == 'S':
        zeta_id = 'S'
        if zeta_standard[-1] in '0123456789':
            zeta_id += zeta_standard[-1]
        else:
            zeta_id += '1'
    elif zeta_standard[0] == 'C' or zeta_standard[0] == 'L':
        zeta_id = 'L'
    elif zeta_standard[0] == 'U':
        zeta_id = 'U'
        if zeta_standard[-1] in '0123456789':
            zeta_id += zeta_standard[-1]
        else:
            zeta_id += '1'

        # Manage the galactic legends
        if (zeta_id not in dict_zetas[character_id] or \
            dict_zetas[character_id][zeta_id][0] == 'Placeholder') and \
            'GL' in dict_zetas[character_id]:
            zeta_id = 'GL'
    
    return zeta_id