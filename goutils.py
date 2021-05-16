# -*- coding: utf-8 -*-
import os
import json
import math
import difflib
from datetime import datetime

import config
import connect_mysql
import connect_gsheets


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
                    "stats": {}}
                
            dict_players[line_name][line_defId]["stats"][1] = int(line_stat1)
            dict_players[line_name][line_defId]["stats"][5] = int(line_stat5)
            dict_players[line_name][line_defId]["stats"][6] = int(line_stat6)
            dict_players[line_name][line_defId]["stats"][7] = int(line_stat7)
            dict_players[line_name][line_defId]["stats"][17] = int(line_stat17)
            dict_players[line_name][line_defId]["stats"][18] = int(line_stat18)
            dict_players[line_name][line_defId]["stats"][28] = int(line_stat28)

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
    
def get_zeta_from_shorts(character_id, zeta_shorts):
    dict_zetas = json.load(open('DATA'+os.path.sep+'unit_zeta_list.json', 'r'))
    
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
    dict_zetas = json.load(open('DATA'+os.path.sep+'unit_zeta_list.json', 'r'))

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
                detect_delta_roster_element(allyCode, dict1['roster'][character_id], character)
                delta_dict['roster'][character_id] = character
        else:
            log("INFO", "delta_dict_player", "new character "+character_id+" for "+str(allyCode))
            connect_mysql.insert_roster_evo(allyCode, character_id, "unlocked")
            delta_dict['roster'][character_id] = character

    return delta_dict

def detect_delta_roster_element(allyCode, char1, char2):
    defId = char1['defId']

    #RARITY
    if char1['rarity'] != char2['rarity']:
        evo_txt = "rarity changed from "\
                  +str(char1['rarity'])+" to "+str(char2['rarity'])
        log("INFO", "delta_roster_element", defId+": "+evo_txt)
        connect_mysql.insert_roster_evo(allyCode, defId, evo_txt)

    #LEVEL
    if char1['level'] != char2['level']:
        evo_txt = "level changed from "\
                  +str(char1['level'])+" to "+str(char2['level'])
        log("INFO", "delta_roster_element", defId+": "+evo_txt)
        connect_mysql.insert_roster_evo(allyCode, defId, evo_txt)

    #GEAR / RELIC
    if char1['gear'] < 13:
        gear1 = "G"+str(char1['gear'])
    else:
        gear1 = "R"+str(char1['relic']['currentTier']-2)
    if char2['gear'] < 13:
        gear2 = "G"+str(char2['gear'])
    else:
        gear2 = "R"+str(char2['relic']['currentTier']-2)

    if gear1 != gear2:
        evo_txt = "gear changed from "+gear1+" to "+gear2
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

def get_characters_from_alias(list_alias, dict_unitsAlias, dict_tagAlias):
    #Recuperation des dernieres donnees sur gdrive
    dict_units = connect_gsheets.load_config_units(dict_unitsAlias)

    txt_not_found_characters = ''
    dict_id_name = {}
    list_ids = []
    for character_alias in list_alias:
        if character_alias.startswith("tag:"):
            #Alias of a tag / faction
            tag_alias = character_alias[4:]
            closest_names=difflib.get_close_matches(tag_alias.lower(), dict_tagAlias.keys(), 3)
            if len(closest_names)<1:
                log('WAR', "get_characters_from_alias", "No tag found for "+tag_alias)
                txt_not_found_characters += character_alias + ' '
            else:
                dict_id_name[character_alias] = []
                for [character_id, character_name] in dict_tagAlias[closest_names[0]]:
                    list_ids.append(character_id)
                    dict_id_name[character_alias].append([character_id, character_name])
        else:
            #Normal alias
            closest_names=difflib.get_close_matches(character_alias.lower(), dict_units.keys(), 3)
            if len(closest_names)<1:
                log('WAR', "get_characters_from_alias", "No character found for "+character_alias)
                txt_not_found_characters += character_alias + ' '
            else:
                [character_name, character_id]=dict_units[closest_names[0]]
                list_ids.append(character_id)
                dict_id_name[character_alias] = [[character_id, character_name]]
            
    return list_ids, dict_id_name, txt_not_found_characters
