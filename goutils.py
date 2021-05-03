# -*- coding: utf-8 -*-
import json
import math
import config
from datetime import datetime

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
    while (len(txt) > max_size) or (FORCE_CUT_PATTERN in txt):
        force_split = txt.find(FORCE_CUT_PATTERN, 0, max_size)
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
   
def create_dict_teams(player_data, player_zeta_data, gv_characters_unlocked):
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

    cur_playername = ''
    for line in gv_characters_unlocked:
        line_playername = line[0]
        line_defId = line[1]
        line_rarity = line[2]
        line_teamname = line_defId + "-GV"
        if not line_playername in dict_players:
            dict_players[line_playername] = {}
        if not line_teamname in dict_players[line_playername]:
            dict_players[line_playername][line_teamname] = {}
        dict_players[line_playername][line_teamname][line_defId]={ \
                                                "rarity": line_rarity}

    return dict_players
    
def create_dict_stats(db_stat_data_char, db_stat_data, db_stat_data_mods, dict_unitsList):
    dict_players={}

    #db_stat_data_char is only used when db_stat_data does not
    # contain all characters (due to not using LEFT JOIN, case of 'all')
    cur_name = ''
    for line in db_stat_data_char:
        line_name = line[0]
        if cur_name != line_name:
            dict_players[line_name]={}
            cur_defId = ''
            cur_name = line_name
        
        line_defId = line[1]
        if cur_defId != line_defId:
            if cur_defId in dict_unitsList:
                line_nameKey = dict_unitsList[line_defId]['nameKey']
            else:
                line_nameKey = line_defId
            line_combatType = line[2]
            line_rarity = line[3]
            line_gear = line[4]
            line_relic_currentTier = line[5]
            dict_players[line_name][line_defId]={ \
                    "nameKey": line_nameKey,
                    "combatType": line_combatType,
                    "rarity": line_rarity,
                    "gear": line_gear,
                    "relic": {"currentTier": line_relic_currentTier},
                    "stats": {}}
                
            cur_defId = line_defId            

    cur_name = ''
    for line in db_stat_data:
        line_name = line[0]
        if cur_name != line_name:
            if not line_name in dict_players:
                dict_players[line_name]={}
            cur_defId = ''
            cur_name = line_name
        
        line_defId = line[1]
        if cur_defId != line_defId:
            if cur_defId in dict_unitsList:
                line_nameKey = dict_unitsList[line_defId]['nameKey']
            else:
                line_nameKey = line_defId
            line_combatType = line[2]
            line_rarity = line[3]
            line_gear = line[4]
            line_relic_currentTier = line[5]
            dict_players[line_name][line_defId]={ \
                    "nameKey": line_nameKey,
                    "combatType": line_combatType,
                    "rarity": line_rarity,
                    "gear": line_gear,
                    "relic": {"currentTier": line_relic_currentTier},
                    "stats": {}}
                
            cur_defId = line_defId
            
        line_unitStatId = line[6]
        line_unscaledDecimalValue = line[7]

        dict_players[line_name][line_defId]["stats"][line_unitStatId] = \
            int(line_unscaledDecimalValue)
    
    cur_name = ''
    for line in db_stat_data_mods:
        line_name = line[0]
        if cur_name != line_name:
            cur_defId = ''
            cur_name = line_name
        
        line_defId = line[1]
        if cur_defId != line_defId:
            cur_mod_id = -1
            dict_players[line_name][line_defId]["mods"]=[]
            cur_defId = line_defId
            
        line_mod_id = line[2]
        if cur_mod_id != line_mod_id:
            line_pips = line[3]
            line_set = line[4]
            line_level = line[5]
            dict_players[line_name][line_defId]["mods"].append(
                {"pips": line_pips,
                "set": line_set,
                "level": line_level,
                "primaryStat": {},
                "secondaryStat": []
                })
                
            cur_mod_id = line_mod_id
            
        line_isPrimary = line[6]
        line_unitStat = line[7]
        line_value = line[8]
        if line_isPrimary:
            dict_players[line_name][line_defId]["mods"][-1]["primaryStat"]["unitStat"] = line_unitStat
            dict_players[line_name][line_defId]["mods"][-1]["primaryStat"]["value"] = line_value
        else:
            dict_players[line_name][line_defId]["mods"][-1]["secondaryStat"].append(
                {"unitStat": line_unitStat,
                "value": line_value})

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

################################################
# function: log
################################################
def log(level, fct, txt):
    now = datetime.now()
    dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
    log_string = dt_string+":"+level+":"+fct+":"+str(txt)

    if level=='DBG':
        if config.LOG_LEVEL=='DBG':
            print(log_string)
    else:
        print(log_string)

################################################
# function: delta_dict_player
# input: 2 dict_players (from API)
# output: differences of dict2 over dict1
################################################
def delta_dict_player(dict1, dict2):
    #basic checks
    if dict1 == None:
        log("DBG", "delta_dict_player", "dict1 is empty, so dict2 is a full delta")
        return dict2

    if dict1['allyCode'] != dict2['allyCode']:
        log("ERR", "delta_dict_player", "cannot compare 2 dict_players for different players")
        return dict2
    allyCode = dict1['allyCode']

    delta_dict = {}
    delta_dict['allyCode'] = allyCode
    delta_dict['roster'] = {}

    #compare player information
    for info in ['guildName', 'id', 'lastActivity', 'level', 'name', 'arena', 'stats', 'poUTCOffsetMinutes']:
        if dict2[info] != dict1[info]:
            log("INFO", "delta_dict_player", info+" has changed for "+str(allyCode))
            delta_dict[info] = dict2[info]

    #compare roster
    for character_id in dict2['roster']:
        character = dict2['roster'][character_id]
        if character_id in dict1['roster']:
            if character != dict1['roster'][character_id]:
                log("INFO", "delta_dict_player", "character "+character_id+" has changed for "+str(allyCode))
                delta_dict['roster'][character_id] = character
        else:
            log("INFO", "delta_dict_player", "new character "+character_id+" for "+str(allyCode))
            delta_dict['roster'][character_id] = character

    return delta_dict

def roster_from_list_to_dict(dict_player):
    txt_allyCode = str(dict_player['allyCode'])

    if type(dict_player['roster']) == dict:
        log("DBG", "roster_from_list_to_dict", "no transformation needed for "+txt_allyCode)
        return dict_player

    dict_roster = {}
    for character in dict_player['roster']:
        dict_roster[character['defId']] = character

    dict_player['roster'] = dict_roster
    log("DBG", "roster_from_list_to_dict", "transformation complete for "+txt_allyCode)

    return dict_player

def roster_from_dict_to_list(dict_player):
    txt_allyCode = str(dict_player['allyCode'])

    if type(dict_player['roster']) == list:
        log("DBG", "roster_from_dict_to_list", "no transformation needed for "+txt_allyCode)
        return dict_player

    list_roster = []
    for character_id in dict_player['roster']:
        character = dict_player['roster'][character_id]
        list_roster.append(character)

    dict_player['roster'] = list_roster
    log("DBG", "roster_from_dict_to_list", "transformation complete for "+txt_allyCode)

    return dict_player
