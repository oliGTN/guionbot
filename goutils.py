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
   
def create_dict_teams(player_data, player_zeta_data, player_omicron_data, gv_characters_unlocked, dict_tw_def):
    dict_capas = data.get('unit_capa_list.json')

    dict_players={}

    cur_playername = ''
    for line in player_data:
        line_playername = line[0]
        line_allyCode = line[1]
        if cur_playername != line_playername:
            dict_players[line_playername]=[line_allyCode, {}]
            cur_teamname = ''
            cur_playername = line_playername
        
        line_teamname = line[2]
        if cur_teamname != line_teamname:
            dict_players[line_playername][1][line_teamname]={}
            cur_defId = ''
            cur_teamname = line_teamname
        
        line_defId = line[3]
        if cur_defId != line_defId:
            line_rarity = line[4]
            line_gear = line[5]
            line_relic_currentTier = line[6]
            line_gp = line[7]
            line_speed = int(line[8])
            line_equipment = line[9]
            equipment = []
            for i_eqpt in range(6):
                if line_equipment[i_eqpt]=="1":
                    equipment.append({"equipmentId":"XXX", "slot":i_eqpt})
            line_character={ \
                "currentRarity": line_rarity,
                "currentTier": line_gear,
                "relic": {"currentTier": line_relic_currentTier},
                "gp": line_gp,
                "speed": line_speed,
                "equipment": equipment,
                "zetas": {},
                "omicrons": {},
                "reserved": False}
            dict_players[line_playername][1][line_teamname][line_defId]=line_character
            if line_defId in dict_tw_def:
                if line_playername in dict_tw_def[line_defId]:
                    dict_players[line_playername][1][line_teamname][line_defId]['reserved'] = True

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
        line_level = line[4]
        line_zeta_tier = dict_capas[line_defId][line_zeta]["zetaTier"]
        is_zeta_active = (line_level >= line_zeta_tier)
        if line_playername in dict_players:
            if line_teamname in dict_players[line_playername][1]:
                if line_defId in dict_players[line_playername][1][line_teamname]:
                    dict_players[line_playername][1][line_teamname]\
                        [line_defId]["zetas"][line_zeta]=is_zeta_active

    cur_playername = ''
    for line in player_omicron_data:
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
            cur_omicron = ''
            cur_defId = line_defId

        line_omicron = line[3]
        line_level = line[4]
        line_omicron_tier = dict_capas[line_defId][line_zeta]["zetaTier"]
        is_omicron_active = (line_level >= line_omicron_tier)
        if line_playername in dict_players:
            if line_teamname in dict_players[line_playername][1]:
                if line_defId in dict_players[line_playername][1][line_teamname]:
                    dict_players[line_playername][1][line_teamname]\
                        [line_defId]["omicrons"][line_omicron]=is_omicron_active

    cur_playername = ''
    if gv_characters_unlocked == None:
        gv_characters_unlocked = []

    for line in gv_characters_unlocked:
        line_playername = line[0]
        line_alyCode = line[1]
        line_defId = line[2]
        line_rarity = line[3]
        line_teamname = line_defId + "-GV"
        if not line_playername in dict_players:
            dict_players[line_playername] = [line_allyCode, {}]
        if not line_teamname in dict_players[line_playername][1]:
            dict_players[line_playername][1][line_teamname] = {}
        if not line_defId in dict_players[line_playername][1][line_teamname]:
            dict_players[line_playername][1][line_teamname][line_defId]={ \
                                                "currentRarity": line_rarity}

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
    
def create_dict_stats(db_stat_data_char, db_stat_data):
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
                line_nameKey = dict_unitsList[line_defId]['name']
            else:
                line_nameKey = line_defId
            line_combatType = line[2]
            line_rarity = line[3]
            line_gear = line[4]
            line_relic_currentTier = line[5]
            dict_players[line_name][line_defId]={ \
                    "defId": line_defId+":STARS",
                    "currentRarity": line_rarity,
                    "currentTier": line_gear,
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
                line_nameKey = dict_unitsList[line_defId]['name']
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
            line_stat14 = line[10]
            line_stat16 = line[11]
            line_stat17 = line[12]
            line_stat18 = line[13]
            line_stat28 = line[14]
            dict_players[line_name][line_defId]={ \
                    "defId": line_defId+":STARS",
                    "currentRarity": line_rarity,
                    "currentTier": line_gear,
                    "relic": {"currentTier": line_relic_currentTier},
                    "stats": {'final':{}}}

            dict_players[line_name][line_defId]["stats"]["final"]['1'] = int(line_stat1)
            dict_players[line_name][line_defId]["stats"]["final"]['5'] = int(line_stat5)
            dict_players[line_name][line_defId]["stats"]["final"]['6'] = int(line_stat6)
            dict_players[line_name][line_defId]["stats"]["final"]['7'] = int(line_stat7)
            dict_players[line_name][line_defId]["stats"]["final"]['14'] = int(line_stat14)
            dict_players[line_name][line_defId]["stats"]["final"]['16'] = int(line_stat16)
            dict_players[line_name][line_defId]["stats"]["final"]['17'] = int(line_stat17)
            dict_players[line_name][line_defId]["stats"]["final"]['18'] = int(line_stat18)
            dict_players[line_name][line_defId]["stats"]["final"]['28'] = int(line_stat28)

            cur_defId = line_defId

    return dict_players
    
def get_capa_name_from_id(character_id, capa_id):
    dict_capas = data.get('unit_capa_list.json')
    if not character_id in dict_capas:
        log2("ERR", "unknown character id "+character_id)
        return capa_id
    if not capa_id in dict_capas[character_id]:
        log2("ERR", "unknown capa id "+capa_id)
        return capa_id

    return dict_capas[character_id][capa_id]["name"]
    
def get_capa_from_shorts(character_id, capa_shorts):
    dict_capas = data.get('unit_capa_list.json')
    req_capa_ids = []
    for capa in capa_shorts:
        capa_id = get_capa_id_from_short(character_id, capa)
        if capa_id == '':
            continue
        if capa_id in dict_capas[character_id]:
            req_capa_ids.append([capa_id, dict_capas[character_id][capa_id]["id"]])
        else:
            log2("WAR", "cannot find capa "+capa+" for "+character_id)
    
    return req_capa_ids

###########################
# IN Chef, Leader, Unique1, Unique2
# OUT L, L, U1, U2
###########################
def get_capa_id_from_short(character_id, capa_short):
    dict_capas = data.get('unit_capa_list.json')
    capa_standard = capa_short.upper().replace(' ', '')

    if capa_standard == '':
        return ''
    elif capa_standard[0] == 'B':
        capa_id = 'B'
    elif capa_standard[0] == 'S':
        capa_id = 'S'
        if capa_standard[-1] in '0123456789':
            capa_id += capa_standard[-1]
        else:
            capa_id += '1'
    elif capa_standard[0] == 'C' or capa_standard[0] == 'L':
        capa_id = 'L'
    elif capa_standard[0] == 'U':
        capa_id = 'U'
        if capa_standard[-1] in '0123456789':
            capa_id += capa_standard[-1]
        else:
            capa_id += '1'

        # Manage the galactic legends
        if (capa_id not in dict_capas[character_id] or \
            dict_capas[character_id][capa_id]["name"] == 'Placeholder') and \
            'GL' in dict_capas[character_id]:
            capa_id = 'GL'

    elif capa_standard[0] == 'H':
        capa_id = 'H'
        if capa_standard[-1] in '0123456789':
            capa_id += capa_standard[-1]
        else:
            capa_id += '1'

    else:
        capa_id = None
    
    return capa_id

################################################
# function: log
################################################
def log(level, fct, txt):
    now = datetime.now()
    dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
    log_string = dt_string+":"+level+":"+fct+":"+str(txt)

    if level=='DBG':
        if config.LOG_LEVEL=='DBG':
            print(log_string, flush=True)
    else:
        print(log_string, flush=True)

################################################
# function: log
################################################
def log2(level, txt):
    now = datetime.now()
    dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
    module_name = inspect.stack()[1][1].split("/")[-1][:-3]
    fct = module_name+"."+inspect.stack()[1][3]
    code_line = inspect.stack()[1][2]
    log_string = dt_string+":"+level+":"+fct+"["+str(code_line)+"]:"+str(txt)

    if level=='DBG':
        if config.LOG_LEVEL=='DBG':
            print(log_string, flush=True)
    else:
        print(log_string, flush=True)

################################################
# function: delta_dict_player
# input: 2 dict_players (from API)
# output: differences of dict2 over dict1
################################################
def delta_dict_player(dict1, dict2):
    allyCode = dict2['allyCode']

    #basic checks
    if dict1 == None:
        log2("DBG", "dict1 is empty, so dict2 is a full delta")
        connect_mysql.insert_roster_evo(allyCode, "all", "adding full roster")
        return dict2

    if dict1['allyCode'] != dict2['allyCode']:
        log2("ERR", "cannot compare 2 dict_players for different players")
        return dict2

    delta_dict = {}
    delta_dict['allyCode'] = allyCode
    delta_dict['rosterUnit'] = {}
    delta_dict['datacron'] = {}

    #compare player information
    for info in ["playerId", "guildName", "guildId", "lastActivityTime", "level", "name", "pvpProfile", "playerRating", "profileStat", "localTimeZoneOffsetMinutes", "equipment"]:
        if not info in dict2:
            dict2[info] = None
        if not info in dict1:
            dict1[info] = None

        if dict2[info] != dict1[info]:
            log2("DBG", info+" has changed for "+str(allyCode))
        delta_dict[info] = dict2[info]

        #manage missing elements
        if delta_dict[info] == None:
            del delta_dict[info]

    #compare roster
    for character_id in dict2['rosterUnit']:
        character = dict2['rosterUnit'][character_id]
        if character_id in dict1['rosterUnit']:
            if character != dict1['rosterUnit'][character_id]:
                log2("DBG", "character "+character_id+" has changed for "+str(allyCode))
                detect_delta_roster_element(allyCode, dict1['rosterUnit'][character_id], character)
                delta_dict['rosterUnit'][character_id] = character
        else:
            log2("DBG", "new character "+character_id+" for "+str(allyCode))
            connect_mysql.insert_roster_evo(allyCode, character_id, "unlocked")
            delta_dict['rosterUnit'][character_id] = character

    #compare datacrons
    if "datacron" in dict2:
        for datacron_id in dict2['datacron']:
            datacron = dict2['datacron'][datacron_id]
            if "datacron" in dict1 and datacron_id in dict1['datacron']:
                if datacron != dict1['datacron'][datacron_id]:
                    log2("DBG", "datacron "+datacron_id+" has changed for "+str(allyCode))
                    detect_delta_datacron(allyCode, dict1['datacron'][datacron_id], datacron)
                    delta_dict['datacron'][datacron_id] = datacron
            else:
                log2("DBG", "new datacron "+datacron_id+" for "+str(allyCode))
                delta_dict['datacron'][datacron_id] = datacron

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
    
#######################
# This function fills roster_evolutions
#######################
def detect_delta_roster_element(allyCode, char1, char2):
    dict_capas = data.get('unit_capa_list.json')
    defId = char1['definitionId'].split(":")[0]

    #RARITY
    if (char1['currentRarity'] != char2['currentRarity']) and (char2['currentRarity'] >= 4):
        for rarity_step in range(max(char1['currentRarity']+1, 4),
                                 char2['currentRarity']+1):
            evo_txt = "rarity changed to "+str(rarity_step)
            log2("DBG", defId+": "+evo_txt)
            connect_mysql.insert_roster_evo(allyCode, defId, evo_txt)

    #LEVEL
    if (char1["currentLevel"] != char2["currentLevel"]) and (char2["currentLevel"] == 85):
        evo_txt = "level changed to 85"
        log2("DBG", defId+": "+evo_txt)
        connect_mysql.insert_roster_evo(allyCode, defId, evo_txt)

    #GEAR / RELIC
    if "relic" in char1:
        relic1 = char1["relic"]
    else:
        relic1 = None
    if "relic" in char2:
        relic2 = char2["relic"]
    else:
        relic2 = None
    gear1 = extended_gear(char1["currentTier"], len(char1["equipment"]), relic1)
    gear2 = extended_gear(char2["currentTier"], len(char2["equipment"]), relic2)
    if (gear1 != gear2) and (gear2>=8):
        for gear_step in range(max(gear1+1, 8), gear2+1):
            evo_txt = "gear changed to "+extended_gear_to_txt(gear_step)
            log2("DBG", defId+": "+evo_txt)
            connect_mysql.insert_roster_evo(allyCode, defId, evo_txt)

    #ULTIMATE
    char1_ulti = False
    if "purchaseAbilityId" in char1:
        for ability in char1["purchaseAbilityId"]:
            if ability.startswith("ultimateability"):
                char1_ulti = True
    char2_ulti = False
    if "purchaseAbilityId" in char2:
        for ability in char2["purchaseAbilityId"]:
            if ability.startswith("ultimateability"):
                char2_ulti = True
    if (not char1_ulti) and char2_ulti:
        evo_txt = "ultimate unlocked"
        log2("DBG", defId+": "+evo_txt)
        connect_mysql.insert_roster_evo(allyCode, defId, evo_txt)

    #ZETAS
    for skill2 in char2['skill']:
        skill_id = skill2['id']
        if skill_id in dict_capas[defId]:
            skill2_isZeta = ( (skill2['tier']+2) >= dict_capas[defId][skill_id]["zetaTier"] )
            skill2_isOmicron = ( (skill2['tier']+2) >= dict_capas[defId][skill_id]["omicronTier"] )
        else:
            skill2_isZeta = False
            skill2_isOmicron = False

        skill1_matchID = [x for x in char1['skill'] if x['id'] == skill_id]
        if len(skill1_matchID)>0:
            skill1 = skill1_matchID[0]
            if skill_id in dict_capas[defId]:
                skill1_isZeta = ( (skill1['tier']+2) >= dict_capas[defId][skill_id]["zetaTier"] )
                skill1_isOmicron = ( (skill1['tier']+2) >= dict_capas[defId][skill_id]["omicronTier"] )
            else:
                skill1_isZeta = False
                skill1_isOmicron = False
        else:
            skill1 = None

        if skill2_isZeta and (skill1 == None or not skill1_isZeta):
            evo_txt = "new zeta "+get_capa_name_from_id(defId, skill_id)
            log2("DBG", defId+": "+evo_txt)
            connect_mysql.insert_roster_evo(allyCode, defId, evo_txt)
        if skill2_isOmicron and (skill1 == None or not skill1_isOmicron):
            if not "omicronMode" in dict_capas[defId][skill_id]:
                log2("ERR", skill_id+" detected as omicron but no omicronMode")
            evo_txt = "new omicron "+get_capa_name_from_id(defId, skill_id)
            evo_txt += " for " + dict_capas[defId][skill_id]["omicronMode"]
            log2("DBG", defId+": "+evo_txt)
            connect_mysql.insert_roster_evo(allyCode, defId, evo_txt)

#######################
# This function fills roster_evolutions
#######################
def detect_delta_datacron(allyCode, dtc1, dtc2):
    if len(dtc1['affix'])<6 and len(dtc2['affix'])>=6:
        abilityId = dtc2["affix"][5]["abilityId"]
        targetRule = dtc2["affix"][5]["targetRule"]
        target = dict_rules[targetRule][0]
        datacron_level_6 = abilityId+":"+target

        evo_txt = "new datacron level 6 "+datacron_level_6
        log2("DBG", defId+": "+evo_txt)
        connect_mysql.insert_roster_evo(allyCode, None, evo_txt)

    if len(dtc1['affix'])<9 and len(dtc2['affix'])>=9:
        abilityId = dtc2["affix"][8]["abilityId"]
        targetRule = dtc2["affix"][8]["targetRule"]
        target = dict_rules[targetRule][0]
        datacron_level_9 = abilityId+":"+target

        evo_txt = "new datacron level 9 "+datacron_level_9
        log2("DBG", defId+": "+evo_txt)
        connect_mysql.insert_roster_evo(allyCode, None, evo_txt)


###############################
def roster_from_list_to_dict(dict_player):
    txt_allyCode = str(dict_player['allyCode'])

    if type(dict_player['rosterUnit']) == dict:
        log2("DBG", "no transformation needed for roster of "+txt_allyCode)
    else:
        #Transform the list of units into a dict
        dict_roster = {}
        for character in dict_player['rosterUnit']:
            dict_roster[character['definitionId'].split(":")[0]] = character
        dict_player['rosterUnit'] = dict_roster

    if "datacron" in dict_player:
        if type(dict_player['datacron']) == dict:
            log2("DBG", "no transformation needed for datacrons of "+txt_allyCode)
        else:
            #Transform the list of datacrons into a dict
            dict_datacrons = {}
            for datacron in dict_player['datacron']:
                dict_datacrons[datacron['id']] = datacron
            dict_player['datacron'] = dict_datacrons

    log2("DBG", "transformation complete for "+txt_allyCode)

    return dict_player

def roster_from_dict_to_list(dict_player_in):
    dict_player = dict_player_in.copy()
    txt_allyCode = str(dict_player['allyCode'])

    if type(dict_player['rosterUnit']) == list:
        log("DBG", "roster_from_dict_to_list", "no transformation needed for roster of "+txt_allyCode)
    else:
        #Transform the dict of units into a list
        list_roster = []
        for character_id in dict_player['rosterUnit']:
            character = dict_player['rosterUnit'][character_id]
            list_roster.append(character)
        dict_player['rosterUnit'] = list_roster

    if "datacron" in dict_player:
        if type(dict_player['datacron']) == list:
            log("DBG", "roster_from_dict_to_list", "no transformation needed for datacrons of "+txt_allyCode)
        else:
            #Transform the dict of datacrons into a list
            list_datacrons = []
            for datacron_id in dict_player['datacron']:
                datacron = dict_player['datacron'][datacron_id]
            list_datacrons.append(datacron)
        dict_player['datacrons'] = list_datacrons

    log("DBG", "roster_from_dict_to_list", "transformation complete for "+txt_allyCode)

    return dict_player

##################################################################
# IN: list_alias = ["gleia", "tag:c:empire", "JMK", ...]
# OUT: list_ids = ["GLLEIA", "LOBOT", "SABINES3", ...]
# OUT: dict_id_name = {"gleia": [["GLEIA", "Leia Organa"]], "tag:c:empire": [["VADOR", "Dark Vador"], ["THRAWN", "Grand Amiral Trawn"], ...], ...}
# OUT: txt_not_found_characters = "toto poisson spock "
#
# If alias not found, the character is not in list_ids and dict_id_name
##################################################################
def get_characters_from_alias(list_alias):
    #Recuperation des dernieres donnees sur gdrive
    dict_unitsList = data.get("unitsList_dict.json")
    dict_unitAlias = connect_gsheets.load_config_units(False)
    dict_tagAlias = data.get("tagAlias_dict.json")
    dict_capas = data.get('unit_capa_list.json')

    txt_not_found_characters = ''
    dict_id_name = {}
    list_ids = []
    for character_alias in list_alias:
        if character_alias.startswith("tag:omicron"):
            dict_id_name[character_alias] = []
            for char_id in dict_capas:
                char_with_omicron = False
                for skill in dict_capas[char_id]:
                    if "omicronMode" in dict_capas[char_id][skill]:
                        char_with_omicron = True
                if char_with_omicron:
                    list_ids.append(char_id)
                    char_name = dict_unitsList[char_id]["name"]
                    dict_id_name[character_alias].append([char_id, char_name])

        elif character_alias.startswith("tag:"):
            #Alias of a tag / faction
            tag_definition = character_alias[4:]
            if tag_definition.lower().startswith("c:"):
                #Alias of a tag / faction for characters
                tag_alias = tag_definition[tag_definition.index(":")+1:]
                combatType = 1
            elif tag_definition.lower().startswith("s:"):
                #Alias of a tag / faction for ships
                tag_alias = tag_definition[tag_definition.index(":")+1:]
                combatType = 2
                only_capital_ship = False
                only_fighter_ship = False
            elif tag_definition.lower().startswith("cs:"):
                #Alias of a tag / faction for ships
                tag_alias = tag_definition[tag_definition.index(":")+1:]
                combatType = 2
                only_capital_ship = True
                only_fighter_ship = False
            elif tag_definition.lower().startswith("fs:"):
                #Alias of a tag / faction for ships
                tag_alias = tag_definition[tag_definition.index(":")+1:]
                combatType = 2
                only_capital_ship = False
                only_fighter_ship = True
            else:
                #Alias of tag / faction for characters and ships
                tag_alias = character_alias[4:]
                combatType = 0

            if tag_alias == "all":
                dict_id_name[character_alias] = []
                for character_id in dict_unitsList:
                    character_name = dict_unitsList[character_id]["name"]
                    char_ct = dict_unitsList[character_id]["combatType"]
                    char_cs = "role_capital" in dict_unitsList[character_id]["categoryId"]
                    if combatType != 0 and (combatType != char_ct):
                        continue
                    if combatType==2 and only_capital_ship and not char_cs:
                        continue
                    if combatType==2 and only_fighter_ship and char_cs:
                        continue

                    if not character_id in list_ids:
                        list_ids.append(character_id)
                    if not [character_id, character_name] in dict_id_name[character_alias]:
                        dict_id_name[character_alias].append([character_id, character_name])
            else:
                closest_names=difflib.get_close_matches(tag_alias.lower(), dict_tagAlias.keys(), 3)
                if len(closest_names)<1:
                    log2('WAR', "No tag found for "+tag_alias)
                    txt_not_found_characters += character_alias + ' '
                else:
                    dict_id_name[character_alias] = []
                    for [character_id, xcn, xct] in dict_tagAlias[closest_names[0]]:
                        character_name = dict_unitsList[character_id]["name"]
                        char_ct = dict_unitsList[character_id]["combatType"]
                        char_cs = "role_capital" in dict_unitsList[character_id]["categoryId"]
                        if combatType != 0 and (combatType != char_ct):
                            continue
                        if combatType==2 and only_capital_ship and not char_cs:
                            continue
                        if combatType==2 and only_fighter_ship and char_cs:
                            continue

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

def remove_format_from_desc(desc):
    while "[" in desc:
        pos_open = desc.find("[")
        pos_close = desc.find("]")
        desc = desc[:pos_open] + desc[pos_close+1:]

    return desc.replace("\\n", "\n")

