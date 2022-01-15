# -*- coding: utf-8 -*-
import os
import json
import math
import difflib
from datetime import datetime
import inspect

import config
import connect_mysql
import connect_gsheets
import data


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
        force_split = txt.find(FORCE_CUT_PATTERN, 0, max_size+len(FORCE_CUT_PATTERN))
        if force_split != -1:
            # FORCE_CUT_PATTERN found
            ret_split_txt.append(txt[:force_split])
            txt = txt[force_split + len(FORCE_CUT_PATTERN):]
            continue

        last_cr_in_max = txt.rfind("\n", 0, max_size+1)
        if last_cr_in_max == -1:
            # CR not found within the max_size
            ret_split_txt.append(txt[:max_size-3] + '...')
            next_cr = txt.find("\n")
            if next_cr != -1:
                #There is a CR, let's skip to the next line
                txt = txt[next_cr + 1:]
            else:
                #No CR at all, end this
                txt = ''
        else:
            ret_split_txt.append(txt[:last_cr_in_max])
            txt = txt[last_cr_in_max + 1:]
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
        if not line_defId in dict_players[line_playername][line_teamname]:
            dict_players[line_playername][line_teamname][line_defId]={ \
                                                "rarity": line_rarity}

    return dict_players
    
def create_guild_teams(db_data):
    dict_teams={}

    cur_teamname = ''
    for line in db_data:
        line_teamname = line[0]
        if cur_teamname != line_teamname:
            dict_teams[line_teamname]={"rarity":7, "categories":[]}
            cur_subteamname = ''
            cur_teamname = line_teamname
        
        line_subteamname = line[1]
        if cur_subteamname != line_subteamname:
            line_subteam_min = line[2]
            dict_teams[line_teamname]["categories"].append([line_subteamname, line_subteam_min, {}])
            cur_unit_id = ''
            cur_subteamname = line_subteamname
        
        line_unit_id = line[4]
        if cur_unit_id != line_unit_id:
            line_id = line[3]
            line_rarity_min = line[5]
            line_gear_min = line[6]
            line_rarity_reco = line[7]
            line_gear_reco = line[8]
            line_speed = line[9]
            line_zetaList = line[10]
            dict_teams[line_teamname]["categories"][-1][2][line_unit_id]=[ 
                    line_id,
                    line_rarity_min, line_gear_min,
                    line_rarity_reco, line_gear_reco,
                    line_zetaList,
                    line_speed,
                    ""]
                    
            cur_unit_id = line_unit_id

    liste_teams = list(dict_teams.keys())
    return liste_teams, dict_teams
    
def create_dict_stats(db_stat_data_char, db_stat_data, db_stat_data_mods):
    dict_players={}
    dict_unitsList = data.get("unitsList_dict.json")

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
            if line_defId in dict_unitsList:
                line_nameKey = dict_unitsList[line_defId]['nameKey']
            else:
                line_nameKey = line_defId
            line_combatType = line[2]
            line_rarity = line[3]
            line_gear = line[4]
            line_relic_currentTier = line[5]
            dict_players[line_name][line_defId]={ \
                    "nameKey": line_nameKey,
                    "defId": line_defId,
                    "combatType": line_combatType,
                    "rarity": line_rarity,
                    "gear": line_gear,
                    "relic": {"currentTier": line_relic_currentTier},
                    "stats": {'final':{}}}
                
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
            if line_defId in dict_unitsList:
                line_nameKey = dict_unitsList[line_defId]['nameKey']
            else:
                line_nameKey = line_defId
            line_combatType = line[2]
            line_rarity = line[3]
            line_gear = line[4]
            line_relic_currentTier = line[5]
            line_stat1 = line[6]
            line_stat5 = line[7]
            line_stat6 = line[8]
            line_stat7 = line[9]
            line_stat17 = line[10]
            line_stat18 = line[11]
            line_stat28 = line[12]
            dict_players[line_name][line_defId]={ \
                    "nameKey": line_nameKey,
                    "defId": line_defId,
                    "combatType": line_combatType,
                    "rarity": line_rarity,
                    "gear": line_gear,
                    "relic": {"currentTier": line_relic_currentTier},
                    "stats": {'final':{}}}

            dict_players[line_name][line_defId]["stats"]["final"]['1'] = int(line_stat1)
            dict_players[line_name][line_defId]["stats"]["final"]['5'] = int(line_stat5)
            dict_players[line_name][line_defId]["stats"]["final"]['6'] = int(line_stat6)
            dict_players[line_name][line_defId]["stats"]["final"]['7'] = int(line_stat7)
            dict_players[line_name][line_defId]["stats"]["final"]['17'] = int(line_stat17)
            dict_players[line_name][line_defId]["stats"]["final"]['18'] = int(line_stat18)
            dict_players[line_name][line_defId]["stats"]["final"]['28'] = int(line_stat28)

            cur_defId = line_defId

    
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
            
        line_prim_stat = line[6]
        line_prim_value = line[7]
        dict_players[line_name][line_defId]["mods"][-1]["primaryStat"]["unitStat"] = line_prim_stat
        dict_players[line_name][line_defId]["mods"][-1]["primaryStat"]["value"] = line_prim_value

        line_sec1_stat = line[8]
        line_sec1_value = line[9]
        dict_players[line_name][line_defId]["mods"][-1]["secondaryStat"].append(
            {"unitStat": line_sec1_stat, "value": line_sec1_value})
        line_sec2_stat = line[10]
        line_sec2_value = line[11]
        dict_players[line_name][line_defId]["mods"][-1]["secondaryStat"].append(
            {"unitStat": line_sec2_stat, "value": line_sec2_value})
        line_sec3_stat = line[12]
        line_sec3_value = line[13]
        dict_players[line_name][line_defId]["mods"][-1]["secondaryStat"].append(
            {"unitStat": line_sec3_stat, "value": line_sec3_value})
        line_sec4_stat = line[14]
        line_sec4_value = line[15]
        dict_players[line_name][line_defId]["mods"][-1]["secondaryStat"].append(
            {"unitStat": line_sec4_stat, "value": line_sec4_value})

    return dict_players
    
def get_zeta_from_id(character_id, zeta_id):
    dict_zetas = data.get('unit_zeta_list.json')
    if not character_id in dict_zetas:
        log("ERR", "get_zeta_from_id", "unknown character id "+character_id)
        return zeta_id
    if not zeta_id in dict_zetas[character_id]:
        log("ERR", "get_zeta_from_id", "unknown zeta id "+zeta_id)
        return zeta_id

    return dict_zetas[character_id][zeta_id][1]
    
def get_zeta_from_shorts(character_id, zeta_shorts):
    dict_zetas = data.get('unit_zeta_list.json')
    
    req_zeta_ids = []
    for zeta in zeta_shorts:
        zeta_id = get_zeta_id_from_short(character_id, zeta)
        if zeta_id == '':
            continue
        if zeta_id in dict_zetas[character_id]:
            if dict_zetas[character_id][zeta_id][1]:
                req_zeta_ids.append([zeta_id, dict_zetas[character_id][zeta_id][0]])
        else:
            log("WAR", "get_zeta_from_shorts", "cannot find zeta "+zeta+" for "+character_id)
    
    return req_zeta_ids

def get_zeta_id_from_short(character_id, zeta_short):
    dict_zetas = data.get('unit_zeta_list.json')

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
    dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
    log_string = dt_string+":"+level+":"+fct+":"+str(txt)

    if level=='DBG':
        if config.LOG_LEVEL=='DBG':
            print(log_string)
    else:
        print(log_string)

################################################
# function: log
################################################
def log2(level, txt):
    now = datetime.now()
    dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
    module_name = inspect.stack()[1][1].split("/")[-1][:-3]
    fct = module_name+"."+inspect.stack()[1][3]
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
    allyCode = dict2['allyCode']

    #basic checks
    if dict1 == None:
        log("DBG", "delta_dict_player", "dict1 is empty, so dict2 is a full delta")
        connect_mysql.insert_roster_evo(allyCode, "all", "adding full roster")
        return dict2

    if dict1['allyCode'] != dict2['allyCode']:
        log("ERR", "delta_dict_player", "cannot compare 2 dict_players for different players")
        return dict2

    delta_dict = {}
    delta_dict['allyCode'] = allyCode
    delta_dict['roster'] = {}

    #compare player information
    for info in ['guildName', 'id', 'lastActivity', 'level', 'name', 'arena', 'grandArena', 'stats', 'poUTCOffsetMinutes']:
        if dict2[info] != dict1[info]:
            log("INFO", "delta_dict_player", info+" has changed for "+str(allyCode))
        delta_dict[info] = dict2[info]

    #compare roster
    for character_id in dict2['roster']:
        character = dict2['roster'][character_id]
        if character_id in dict1['roster']:
            if character != dict1['roster'][character_id]:
                log("INFO", "delta_dict_player", "character "+character_id+" has changed for "+str(allyCode))
                detect_delta_roster_element(allyCode, dict1['roster'][character_id], character)
                delta_dict['roster'][character_id] = character
        else:
            log("INFO", "delta_dict_player", "new character "+character_id+" for "+str(allyCode))
            connect_mysql.insert_roster_evo(allyCode, character_id, "unlocked")
            delta_dict['roster'][character_id] = character

    return delta_dict

def extended_gear(gear, equipped, relic):
    if gear < 10:
        return gear
    elif gear < 13:
        return 10 + (gear-10)*6 + equipped
    else:
        return 26 + relic['currentTier']

def extended_gear_to_txt(extended_gear):
    if extended_gear >= 29:
        return "R" + str(extended_gear-28)
    elif extended_gear == 28:
        return "G13"
    elif extended_gear >= 10:
        equipped = (extended_gear-10)%6
        gear = 10 + int((extended_gear-equipped-10)/6)
        return "G"+str(gear)+"+"+str(equipped)
    else:
        return str(extended_gear)
    
def detect_delta_roster_element(allyCode, char1, char2):
    dict_zetas = data.get('unit_zeta_list.json')
    defId = char1['defId']

    #RARITY
    if (char1['rarity'] != char2['rarity']) and (char2['rarity'] >= 4):
        for rarity_step in range(max(char1['rarity']+1, 4),
                                 char2['rarity']+1):
            evo_txt = "rarity changed to "+str(rarity_step)
            log("INFO", "delta_roster_element", defId+": "+evo_txt)
            connect_mysql.insert_roster_evo(allyCode, defId, evo_txt)

    #LEVEL
    if (char1['level'] != char2['level']) and (char2['level'] == 85):
        evo_txt = "level changed to 85"
        log("INFO", "delta_roster_element", defId+": "+evo_txt)
        connect_mysql.insert_roster_evo(allyCode, defId, evo_txt)

    #GEAR / RELIC
    gear1 = extended_gear(char1['gear'], len(char1['equipped']), char1['relic'])
    gear2 = extended_gear(char2['gear'], len(char2['equipped']), char2['relic'])
    if (gear1 != gear2) and (gear2>=8):
        for gear_step in range(max(gear1+1, 8), gear2+1):
            evo_txt = "gear changed to "+extended_gear_to_txt(gear_step)
            log("INFO", "delta_roster_element", defId+": "+evo_txt)
            connect_mysql.insert_roster_evo(allyCode, defId, evo_txt)

    #ZETAS
    for skill2 in char2['skills']:
        skill_id = skill2['id']
        skill2_isZeta = skill2['isZeta'] and skill2['tier']>=8
        if defId in dict_zetas:
            skill2_isOmicron = dict_zetas[defId][skill_id][3]!="" \
                               and skill2['tier'] == dict_zetas[defId][skill_id][4]
        else:
            log2('ERR', defId + " not found in dict_zetas")
            skill2_isOmicron = False

        skill1_matchID = [x for x in char1['skills'] if x['id'] == skill_id]
        if len(skill1_matchID)>0:
            skill1 = skill1_matchID[0]
            skill1_isZeta = skill1['isZeta'] and skill1['tier']>=8
            if defId in dict_zetas:
                skill1_isOmicron = dict_zetas[defId][skill_id][3]!="" \
                                   and skill1['tier'] == dict_zetas[defId][skill_id][4]
            else:
                skill1_isOmicron = False
        else:
            skill1 = None
        if skill2_isZeta and (skill1 == None or not skill1_isZeta):
            evo_txt = "new zeta "+get_zeta_from_id(defId, skill_id)
            log("INFO", "delta_roster_element", defId+": "+evo_txt)
            connect_mysql.insert_roster_evo(allyCode, defId, evo_txt)
        if skill2_isOmicron and (skill1 == None or not skill1_isOmicron):
            evo_txt = "new omicron "+get_zeta_from_id(defId, skill_id)
            evo_txt += " for " + dict_zetas[defId][skill_id][3]
            log("INFO", "delta_roster_element", defId+": "+evo_txt)
            connect_mysql.insert_roster_evo(allyCode, defId, evo_txt)

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

def get_characters_from_alias(list_alias):
    #Recuperation des dernieres donnees sur gdrive
    dict_unitsList = data.get("unitsList_dict.json")
    dict_unitAlias = connect_gsheets.load_config_units(False)
    dict_tagAlias = data.get("tagAlias_dict.json")
    dict_zetas = data.get('unit_zeta_list.json')

    txt_not_found_characters = ''
    dict_id_name = {}
    list_ids = []
    for character_alias in list_alias:
        if character_alias.startswith("tag:omicron"):
            dict_id_name[character_alias] = []
            for char_id in dict_zetas:
                char_with_omicron = False
                for skill in dict_zetas[char_id]:
                    if dict_zetas[char_id][skill][4] >= 0:
                        char_with_omicron = True
                if char_with_omicron:
                    list_ids.append(char_id)
                    char_name = dict_unitsList[char_id]["nameKey"]
                    dict_id_name[character_alias].append([char_id, char_name])

        elif character_alias.startswith("tag:"):
            #Alias of a tag / faction
            tag_definition = character_alias[4:]
            if tag_definition.lower().startswith("char:") or \
               tag_definition.lower().startswith("c:") or \
               tag_definition.lower().startswith("character:") or \
               tag_definition.lower().startswith("characters:"):
                #Alias of a tag / faction for characters
                tag_alias = tag_definition[tag_definition.index(":")+1:]
                combatType = 1
            elif tag_definition.lower().startswith("ship:") or \
                 tag_definition.lower().startswith("s:") or \
                 tag_definition.lower().startswith("ships:"):
                #Alias of a tag / faction for ships
                tag_alias = tag_definition[tag_definition.index(":")+1:]
                combatType = 2
            else:
                #Alias of tag / faction for characters and ships
                tag_alias = character_alias[5:]
                combatType = 0

            closest_names=difflib.get_close_matches(tag_alias.lower(), dict_tagAlias.keys(), 3)
            if len(closest_names)<1:
                log2('WAR', "No tag found for "+tag_alias)
                txt_not_found_characters += character_alias + ' '
            else:
                dict_id_name[character_alias] = []
                for [character_id, character_name, char_ct] in dict_tagAlias[closest_names[0]]:
                    if combatType == 0 or (combatType == char_ct):
                        if not character_id in list_ids:
                            list_ids.append(character_id)
                        if not [character_id, character_name] in dict_id_name[character_alias]:
                            dict_id_name[character_alias].append([character_id, character_name])
        else:
            #First look for exact match (better for performance)
            if character_alias.lower() in dict_unitAlias:
                [character_name, character_id]=dict_unitAlias[character_alias.lower()]
                if not character_id in list_ids:
                    list_ids.append(character_id)
                dict_id_name[character_alias] = [[character_id, character_name]]
            else:
                #Normal alias
                closest_names=difflib.get_close_matches(character_alias.lower(), dict_unitAlias.keys(), 3)
                if len(closest_names)<1:
                    log2('WAR', "No character found for "+character_alias)
                    txt_not_found_characters += character_alias + ' '
                else:
                    [character_name, character_id]=dict_unitAlias[closest_names[0]]
                    if not character_id in list_ids:
                        list_ids.append(character_id)
                    dict_id_name[character_alias] = [[character_id, character_name]]

    return list_ids, dict_id_name, txt_not_found_characters
