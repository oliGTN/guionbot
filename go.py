# -*- coding: utf-8 -*-

from swgohhelp import SWGOHhelp, settings
import sys
import time
import datetime
import os
import config
import difflib
import math
from functools import reduce
from math import ceil
import json
import matplotlib
matplotlib.use('Agg') #Preventin GTK erros at startup
import matplotlib.pyplot as plt
from PIL import Image

import connect_gsheets
import connect_mysql
import connect_crinolo
import connect_warstats
import goutils
import portraits
import parallel_work

FORCE_CUT_PATTERN = "SPLIT_HERE"
MAX_GVG_LINES = 40

#login password sur https://api.swgoh.help/profile
if config.SWGOHAPI_LOGIN != "":
    creds = settings(config.SWGOHAPI_LOGIN, config.SWGOHAPI_PASSWORD, '123', 'abc')
    client = SWGOHhelp(creds)
else:
    client = None
dict_unitsList = json.load(open('DATA'+os.path.sep+'unitsList_dict.json', 'r'))
dict_unitsAlias = json.load(open('DATA'+os.path.sep+'unitsAlias_dict.json', 'r'))
dict_tagAlias = json.load(open('DATA'+os.path.sep+'tagAlias_dict.json', 'r'))

#Clean temp files
parallel_work.clean_cache()

dict_stat_names={}
dict_stat_names["speed"] = [5, False]
dict_stat_names["vitesse"] = [5, False]
dict_stat_names["protection"] = [28, False]
dict_stat_names["dégâts physiques"] = [6, False]
dict_stat_names["physical damages"] = [6, False]
dict_stat_names["dégâts spéciaux"] = [7, False]
dict_stat_names["special damages"] = [7, False]
dict_stat_names["santé"] = [1, False]
dict_stat_names["health"] = [1, False]
dict_stat_names["pouvoir"] = [17, True]
dict_stat_names["potency"] = [17, True]
dict_stat_names["tenacité"] = [18, True]
dict_stat_names["tenacity"] = [18, True]

##################################
# Function: refresh_cache
# return: error code
##################################
def refresh_cache():
    #CLEAN OLD FILES NOT ACCESSED FOR LONG TIME
    #Need to keep KEEPDIR to prevent removal of the directory by GIT
    
    # Get the allyCodes to be refreshed
    # the query gets one allyCode by guild in the DB
    query = "SELECT guilds.name, MIN(allyCode) "\
           +"FROM guilds "\
           +"JOIN players on players.guildName = guilds.name "\
           +"WHERE ((guilds.lastRequested > CURRENT_TIMESTAMP - INTERVAL 1 DAY) "\
           +"   AND (guilds.lastUpdated < CURRENT_TIMESTAMP - INTERVAL 60 MINUTE)) "\
           +"OR ((guilds.lastRequested > CURRENT_TIMESTAMP - INTERVAL 7 DAY) "\
           +"   AND (guilds.lastUpdated < CURRENT_TIMESTAMP - INTERVAL 6 HOUR)) "\
           +"GROUP BY guildName "\
           +"ORDER BY guilds.lastUpdated"
    goutils.log('DBG', 'refresh_cache', query)
    ret_table = connect_mysql.get_table(query)
    
    if ret_table != None:
        #Refresh players from master guild
        guild_name = ret_table[0][0]
        guild_allyCode = ret_table[0][1]
        goutils.log('INFO', 'refresh_cache', "refresh guild "+guild_name)
        e, t = load_guild(str(guild_allyCode), True, False)
        
    return 0

##################################
# Function: refresh_cache
# return: erro_code, err_text
##################################
def load_player(txt_allyCode, force_update, no_db):

    if no_db:
        recent_player = False
        prev_dict_player = None
    else:
        # The query tests if the update is less than 60 minutes for all players
        # Assumption: when the command is player-related, updating one is costless
        query_result = connect_mysql.get_line("SELECT \
                            (timestampdiff(MINUTE, players.lastUpdated, CURRENT_TIMESTAMP)<=60) AS recent, \
                            name \
                            FROM players WHERE allyCode = '"+txt_allyCode+"'")
    
        if query_result != None:
            recent_player = query_result[0]
            player_name = query_result[1]
        else:
            recent_player = 0

        json_file = "PLAYERS"+os.path.sep+txt_allyCode+".json"
        if os.path.isfile(json_file):
            prev_dict_player = json.load(open(json_file, 'r'))
            prev_dict_player = goutils.roster_from_list_to_dict(prev_dict_player)
        else:
            prev_dict_player = None

    if not recent_player or force_update:
        goutils.log("INFO", "load_player", 'requesting API data for ' + txt_allyCode + '...')
        if client != None:
            player_data = client.get_data('player', txt_allyCode, 'FRE_FR')
        else:
            goutils.log("WAR", "load_player", 'Cannot connect to API. Using cache data from json')
            player_data = [prev_dict_player]

        if isinstance(player_data, list):
            if len(player_data) > 0:
                if len(player_data) > 1:
                   goutils.log("WAR", "load_player", "client.get_data(\'player\', "+txt_allyCode+
                            ", 'FRE_FR') has returned a list of size "+
                            str(len(player_data)))
                            
                dict_player = player_data[0]
        
                #Add statistics
                dict_player = connect_crinolo.add_stats(dict_player)

                #Transform the roster into dictionary with key = defId
                dict_player = goutils.roster_from_list_to_dict(dict_player)

                goutils.log("INFO", "load_player", "success retrieving "+dict_player['name']+" from SWGOH.HELP API")
                sys.stdout.flush()
                
                if not no_db:
                    # compute differences
                    delta_dict_player = goutils.delta_dict_player(prev_dict_player, dict_player)
                    sys.stdout.flush()
                
                    # store json file
                    fjson = open(json_file, 'w')
                    fjson.write(json.dumps(dict_player, sort_keys=True, indent=4))
                    fjson.close()

                    # update DB
                    #ret = connect_mysql.update_player(dict_player, dict_unitsList)
                    ret = connect_mysql.update_player(delta_dict_player, dict_unitsList)
                    if ret == 0:
                        goutils.log("INFO", "load_player", "success updating "+dict_player['name']+" in DB")
                    else:
                        goutils.log('ERR', "load_player", 'update_player '+txt_allyCode+' returned an error')
                        return 1, None, 'ERR: update_player '+txt_allyCode+' returned an error'
                    sys.stdout.flush()
                
            else:
                goutils.log('ERR', 'load_player', 'client.get_data(\'player\', '+txt_allyCode+
                        ", 'FRE_FR') has returned an empty list")
                sys.stdout.flush()
                return 1, None, 'ERR: allyCode '+txt_allyCode+' not found'

        else:
            goutils.log('ERR', 'load_player', 'client.get_data(\'player\', '+
                    txt_allyCode+", 'FRE_FR') has not returned a list")
            goutils.log('ERR', 'load_player',player_data)
            sys.stdout.flush()
            return 1, None, 'ERR: allyCode '+txt_allyCode+' not found'

    else:
        goutils.log('INFO', 'load_player',player_name + ' OK')
        dict_player = prev_dict_player
    
    sys.stdout.flush()
    return 0, dict_player, ''

def load_guild(txt_allyCode, load_players, cmd_request):
    #Get API data for the guild
    goutils.log('INFO', "load_guild", 'Requesting guild data for allyCode ' + txt_allyCode)
    json_file = "GUILDS"+os.path.sep+"G"+txt_allyCode+".json"
    if client != None:
        client_data = client.get_data('guild', txt_allyCode, 'FRE_FR')
    else:
        goutils.log("WAR", "load_guild", 'Cannot connect to API. Using cache data from json')
        if os.path.isfile(json_file):
            prev_dict_guild = json.load(open(json_file, 'r'))
            client_data = [prev_dict_guild]
        else:
            client_data = None

    if isinstance(client_data, list):
        if len(client_data) > 0:
            if len(client_data) > 1:
                goutils.log('WAR', 'load_guild',"client.get_data(\'guild\', "+txt_allyCode+
                        ", 'FRE_FR') has returned a list of size "+
                        str(len(player_data)))            
                            
            dict_guild = client_data[0]
            guildName = dict_guild['name']
            total_players = len(dict_guild['roster'])
            allyCodes_in_API = [int(x['allyCode']) for x in dict_guild['roster']]
            goutils.log("INFO", "load_guild", "success retrieving "+guildName+" ("\
                        +str(total_players)+" players) from SWGOH.HELP API")
                        
            # store json file
            fjson = open(json_file, 'w')
            fjson.write(json.dumps(dict_guild, sort_keys=True, indent=4))
            fjson.close()
        else:
            goutils.log("ERR", "load_guild", "client.get_data('guild', "+txt_allyCode+
                    ", 'FRE_FR') has returned an empty list")
            return 'ERR: cannot fetch guild fo allyCode '+txt_allyCode, None
    else:
        goutils.log ('ERR', "load_guild", "client.get_data('guild', "+
                txt_allyCode+", 'FRE_FR') has not returned a list")
        goutils.log ("ERR", "load_guild", client_data)
        return 'ERR: cannot fetch guild for allyCode '+txt_allyCode, None

    #Get guild data from DB
    query = "SELECT lastUpdated FROM guilds "\
           +"WHERE name = '"+guildName.replace("'", "''")+"'"
    goutils.log('DBG', 'load_guild', query)
    lastUpdated = connect_mysql.get_value(query)
    is_new_guild = (lastUpdated == None)

    query = "SELECT allyCode FROM players "\
           +"WHERE guildName = '"+guildName.replace("'", "''")+"'"
    goutils.log('DBG', 'load_guild', query)
    allyCodes_in_DB = connect_mysql.get_column(query)

    allyCodes_to_add = []
    for ac in allyCodes_in_API:
        if not ac in allyCodes_in_DB:
            allyCodes_to_add.append(ac)

    allyCodes_to_remove = []
    for ac in allyCodes_in_DB:
        if not ac in allyCodes_in_API:
            allyCodes_to_remove.append(ac)

    if load_players:
        if lastUpdated != None:
            delta_lastUpdated = datetime.datetime.now() - lastUpdated

        need_to_add_players = (len(allyCodes_to_add) > 0)
        need_refresh_due_to_time = (not cmd_request) and (delta_lastUpdated.days*86400 + delta_lastUpdated.seconds) > 3600

        if is_new_guild or need_refresh_due_to_time or need_to_add_players:
            #The guild is not defined yet, add it
            guild_loading_status = parallel_work.get_guild_loading_status(guildName)

            if is_new_guild or need_refresh_due_to_time:
                #add all players
                list_allyCodes_to_update = [x['allyCode'] for x in dict_guild['roster']]
            else:
                #only some players to be added
                list_allyCodes_to_update = allyCodes_to_add
                total_players = len(list_allyCodes_to_update)

            if guild_loading_status != None:
                #The guild is already being loaded
                #while dict_loading_guilds[guildName][1] < dict_loading_guilds[guildName][0]:
                while guild_loading_status != None:
                    goutils.log('INFO', "load_guild", "Guild "+guildName+" already loading ("\
                            + guild_loading_status + "), waiting 30 seconds...")
                    time.sleep(30)
                    guild_loading_status = parallel_work.get_guild_loading_status(guildName)
                    sys.stdout.flush()
            else:
                #First request to load this guild
                parallel_work.set_guild_loading_status(guildName, "0/"+str(total_players))

                #Ensure only one guild loading at a time
                #while len(dict_loading_guilds) > 1:
                list_other_guilds_loading_status = parallel_work.get_other_guilds_loading_status(guildName)
                while len(list_other_guilds_loading_status) > 0:
                    goutils.log('INFO', "load_guild", "Guild "+guildName+" loading "\
                                +"will start after loading of "+str(list_other_guilds_loading_status))
                    time.sleep(30)
                    list_other_guilds_loading_status = parallel_work.get_other_guilds_loading_status(guildName)
                    sys.stdout.flush()

                #Create guild in DB only if the players are loaded
                query = "INSERT IGNORE INTO guilds(name) VALUES('"+guildName.replace("'", "''")+"')"
                goutils.log('DBG', 'load_guild', query)
                connect_mysql.simple_execute(query)

                #add player data
                i_player = 0
                for allyCode in list_allyCodes_to_update:
                    i_player += 1
                    goutils.log("INFO", "load_guild", "player #"+str(i_player))
                    
                    e, d, t = load_player(str(allyCode), False, False)
                    parallel_work.set_guild_loading_status(guildName, str(i_player)+"/"+str(total_players))

                parallel_work.set_guild_loading_status(guildName, None)

                #Update dates in DB
                query = "UPDATE guilds "\
                       +"SET lastUpdated = CURRENT_TIMESTAMP "\
                       +"WHERE name = '"+guildName.replace("'", "''") + "'"
                goutils.log('DBG', 'load_guild', query)
                connect_mysql.simple_execute(query)

        else:
            lastUpdated_txt = lastUpdated.strftime("%d/%m/%Y %H:%M:%S")
            goutils.log('INFO', "load_guild", "Guild "+guildName+" last update is "+lastUpdated_txt)

    #Update dates in DB
    if cmd_request:
        query = "UPDATE guilds "\
               +"SET lastRequested = CURRENT_TIMESTAMP "\
               +"WHERE name = '"+guildName.replace("'", "''") + "'"
        goutils.log('DBG', 'load_guild', query)
        connect_mysql.simple_execute(query)

    #Erase guildName for alyCodes not detected from API
    if len(allyCodes_to_remove) > 0:
        query = "UPDATE players "\
               +"SET guildName = '' "\
               +"WHERE allyCode IN "+str(tuple(allyCodes_to_remove)).replace(",)", ")")
        goutils.log('DBG', 'load_guild', query)
        connect_mysql.simple_execute(query)

    return "OK", dict_guild

def get_team_line_from_player(team_name, dict_player, dict_team, score_type, score_green,
                              score_amber, gv_mode, txt_mode, player_name):
    #score_type :
    #   1 : from 0 to 100% counting rarity/gear+relic/zetas... and 0 for each character below minimum
    #   2 : Same as #1, but still counting scores below minimum
    #   3 : score = gp*vitesse/vitesse_requise
    #   * : Affichage d'une icône verte (100%), orange (>=80%) ou rouge

    line = ''
    objectifs = dict_team["categories"]
    nb_subobjs = len(objectifs)
    
    #INIT tableau des resultats
    tab_progress_player = [[] for i in range(nb_subobjs)]
    for i_subobj in range(0, nb_subobjs):
        nb_chars = len(objectifs[i_subobj][2])
        if score_type == 1:
            tab_progress_player[i_subobj] = [[0, '.     ', True]
                                            for i in range(nb_chars)]
        elif score_type == 2:
            tab_progress_player[i_subobj] = [[0, '.     ', True]
                                            for i in range(nb_chars)]
        else:  #score_type==3
            tab_progress_player[i_subobj] = [[0, '.         ', True]
                                            for i in range(nb_chars)]
    # Loop on categories within the goals
    for i_subobj in range(0, nb_subobjs):
        dict_char_subobj = objectifs[i_subobj][2]

        for character_id in dict_char_subobj:
            progress = 0
            progress_100 = 0
            
            character_obj = dict_char_subobj[character_id]
            i_character = character_obj[0]
            character_name = character_obj[7]
            if character_id in dict_player:
                character_nogo = False

                #Etoiles
                req_rarity_min = character_obj[1]
                req_rarity_reco = character_obj[3]
                player_rarity = dict_player[character_id]['rarity']
                progress_100 = progress_100 + 1
                progress = progress + min(1, player_rarity / req_rarity_reco)
                if player_rarity < req_rarity_min:
                    character_nogo = True
                
                #Gear
                req_gear_min = character_obj[2]
                req_relic_min=0
                if req_gear_min == '':
                    req_gear_min = 1
                elif type(req_gear_min) == str:
                    req_relic_min=int(req_gear_min[-1])
                    req_gear_min=13
                    
                req_gear_reco = character_obj[4]
                req_relic_reco=0
                if req_gear_reco == '':
                    req_gear_reco = 1
                elif type(req_gear_reco) == str:
                    req_relic_reco=int(req_gear_reco[-1])
                    req_gear_reco=13

                player_gear = dict_player[character_id]['gear']
                if player_gear < 13:
                    player_relic = 0
                else:
                    player_relic = dict_player[character_id]['relic_currentTier'] - 2

                progress_100 = progress_100 + 1
                progress = progress + min(1, (player_gear+player_relic) / (req_gear_reco+req_relic_reco))
                if (player_gear+player_relic) < (req_gear_min+req_relic_min):
                    character_nogo = True
                # print('DBG: player_gear='+str(player_gear)+' player_relic='+str(player_relic))
                # print('DBG: req_gear_min='+str(req_gear_min)+' req_relic_min='+str(req_relic_min))
                # print('DBG: character_nogo='+str(character_nogo))
                # print('DBG: progress='+str(progress)+' progress_100='+str(progress_100))

                #Zetas
                req_zetas = character_obj[5].split(',')
                req_zeta_ids = [goutils.get_zeta_id_from_short(character_id, x) for x in req_zetas]
                req_zeta_ids = list(filter(lambda x: x != '', req_zeta_ids))
                        
                player_nb_zetas = 0
                progress_100 += len(req_zeta_ids)
                for zeta in dict_player[character_id]['zetas']:
                    if zeta in req_zeta_ids:
                        if dict_player[character_id]['zetas'][zeta] == 8:
                            player_nb_zetas += 1
                            progress += 1
                if player_nb_zetas < len(req_zeta_ids):
                    character_nogo = True

                #Vitesse (optionnel)
                req_speed = character_obj[6]
                player_speed = dict_player[character_id]['speed']
                req_speed = character_obj[6]
                if req_speed != '':
                    progress_100 = progress_100 + 1
                    progress = progress + min(1, player_speed / req_speed)
                else:
                    req_speed = player_speed

                player_gp = dict_player[character_id]['gp']

                #Progress
                if score_type == 1:
                    character_progress = progress / progress_100
                elif score_type == 2:
                    character_progress = progress / progress_100
                else:  #score_type==3)
                    character_progress = int(player_gp * player_speed / req_speed)

                #Display
                character_display = str(player_rarity)
                if player_gear < 13:
                    character_display += '.' + "{:02d}".format(player_gear)                        
                else:
                    character_display += '.R' + str(player_relic)
                character_display += '.' + str(player_nb_zetas)
                if score_type == 3:
                    character_display += '.' + "{:03d}".format(player_speed)
                        
                if gv_mode:
                    if player_rarity < req_rarity_reco:
                        character_display += "\N{UP-POINTING RED TRIANGLE} "+\
                                            character_name + \
                                            " est seulement " + \
                                            str(player_rarity) + "/" +\
                                            str(req_rarity_reco) +\
                                            "\N{WHITE MEDIUM STAR}"
                    elif player_gear < req_gear_reco:
                        character_display += "\N{CONFUSED FACE} "+\
                                            character_name + \
                                            " est seulement G" + \
                                            str(player_gear) + "/" +\
                                            str(req_gear_reco)
                    elif player_relic < req_relic_reco:
                        character_display += "\N{WHITE RIGHT POINTING BACKHAND INDEX} "+\
                                            character_name + \
                                            " est seulement relic " + \
                                            str(player_relic) + "/" +\
                                            str(req_relic_reco)
                    else:
                        character_display += "\N{WHITE HEAVY CHECK MARK} "+\
                                            character_name + \
                                            " est OK"
                    character_progress_100 = int(character_progress*100)
                    character_display += " - " + str(character_progress_100) +"%"

                tab_progress_player[i_subobj][i_character - 1][0] = character_progress
                tab_progress_player[i_subobj][i_character - 1][1] = character_display
                tab_progress_player[i_subobj][i_character - 1][2] = character_nogo

                goutils.log("DBG", "get_team_line_from_player", tab_progress_player[i_subobj][i_character - 1])

            else:
                if gv_mode:
                    character_display = "\N{CROSS MARK} "+\
                                        character_name + \
                                        " n'est pas débloqué - 0%"
                    tab_progress_player[i_subobj][i_character - 1][1] += character_display
    
    #calcul du score global
    score = 0
    score100 = 0
    score_nogo = False
    for i_subobj in range(0, nb_subobjs):
        nb_sub_obj = len(objectifs[i_subobj][2])
        for i_character in range(0, nb_sub_obj):
            tab_progress_sub_obj = tab_progress_player[i_subobj][i_character]
            if not gv_mode:
                if not tab_progress_sub_obj[2]:
                    if txt_mode:
                        line += tab_progress_sub_obj[1] + '|'
                    else:
                        line += '**' + goutils.pad_txt2(tab_progress_sub_obj[1]) + '**|'
                else:
                    if txt_mode:
                        line += tab_progress_sub_obj[1] + '|'
                    else:
                        line += goutils.pad_txt2(tab_progress_sub_obj[1]) + '|'
            else:
                line += tab_progress_sub_obj[1] + "\n"

        min_perso = objectifs[i_subobj][1]

        #Extraction des scores pour les persos non-exclus
        tab_score_player_values = [(lambda f: (f[0] * (not f[2])))(x)
                                   for x in tab_progress_player[i_subobj]]

        score += sum(sorted(tab_score_player_values)[-min_perso:])
        score100 += min_perso
        
        if 0.0 in sorted(tab_score_player_values)[-min_perso:]:
            score_nogo = True

    #pourcentage sur la moyenne
    if score_type == 1:
        score = score / score100 * 100
    elif score_type == 2:
        score = score / score100 * 100
        
    unlocked = False
    if gv_mode:
        # in gv_mode, we check if the target character is unlocked
        # with the target max rarity
        target_character = team_name[:-3]
        target_rarity = dict_team["rarity"]
        if target_character in dict_player:
            if dict_player[target_character]["rarity"] >= target_rarity:
                unlocked = True

    #affichage du score
    if not gv_mode:
        line += str(int(score))

    # affichage de la couleur
    if not txt_mode:
        if score_nogo:
            line += '\N{CROSS MARK}'
        elif score >= score_green:
            line += '\N{GREEN HEART}'
        elif score >= score_amber:
            line += '\N{LARGE ORANGE DIAMOND}'
        else:
            line += '\N{CROSS MARK}'

    # Display the IG name only, as @mentions only pollute discord
    if not gv_mode:
        line += '|' + player_name + '\n'

    return score, unlocked, line, score_nogo


def get_team_entete(team_name, objectifs, score_type, txt_mode):
    entete = ''

    nb_levels = len(objectifs)
    #print('DBG: nb_levels='+str(nb_levels))

    #Affichage des prérequis
    entete += '**Team: ' + team_name + '**\n'
    for i_level in range(0, nb_levels):
        #print('DBG: i_level='+str(i_level))
        #print('DBG: obj='+str(objectifs[i_level]))
        nb_sub_obj = len(objectifs[i_level][2])
        #print('DBG: nb_sub_obj='+str(nb_sub_obj))
        entete += '**' + objectifs[i_level][0] + '**\n'
        for i_sub_obj in range(0, nb_sub_obj):
            for perso in objectifs[i_level][2]:
                if objectifs[i_level][2][perso][0] == i_sub_obj + 1:
                    perso_rarity_min = objectifs[i_level][2][perso][1]
                    perso_gear_min = objectifs[i_level][2][perso][2]
                    perso_relic_min=0
                    if perso_gear_min == '':
                        perso_gear_min = 1
                    elif type(perso_gear_min) == str:
                        perso_relic_min=int(perso_gear_min[-1])
                        perso_gear_min=13
                    perso_min_display = str(perso_rarity_min)
                    if perso_relic_min == 0:
                        perso_min_display += '.' + "{:02d}".format(perso_gear_min)                        
                    else:
                        perso_min_display += '.R' + str(perso_relic_min)

                    perso_rarity_reco = objectifs[i_level][2][perso][3]
                    perso_gear_reco = objectifs[i_level][2][perso][4]                    
                    perso_relic_reco=0
                    if perso_gear_reco == '':
                        perso_gear_reco = 1
                    elif type(perso_gear_reco) == str:
                        perso_relic_reco=int(perso_gear_reco[-1])
                        perso_gear_reco=13
                    perso_reco_display = str(perso_rarity_reco)
                    if perso_relic_reco == 0:
                        perso_reco_display += '.' + "{:02d}".format(perso_gear_reco)                        
                    else:
                        perso_reco_display += '.R' + str(perso_relic_reco)

                    #Zetas
                    req_zetas = objectifs[i_level][2][perso][5].split(',')
                    req_zeta_names = [x[1] for x in goutils.get_zeta_from_shorts(perso, req_zetas)]
                    
                    entete += '**' + objectifs[i_level][0][0] + str(i_sub_obj + 1) + \
                            '**: ' + perso + ' (' + perso_min_display + ' à ' + \
                            perso_reco_display + ', zetas=' + str(req_zeta_names) + ')\n'

    #ligne d'entete
    entete += '\n'
    for i_level in range(0, nb_levels):
        nb_sub_obj = len(objectifs[i_level][2])
        #print('DBG: nb_sub_obj='+str(nb_sub_obj))
        for i_sub_obj in range(0, nb_sub_obj):
            #print('DBG:'+str(objectifs[i_level][0][0]+str(i_sub_obj)))
            if score_type == 1:
                nom_sub_obj = goutils.pad_txt(
                    objectifs[i_level][0][0] + str(i_sub_obj + 1), 6)
            elif score_type == 2:
                nom_sub_obj = goutils.pad_txt(
                    objectifs[i_level][0][0] + str(i_sub_obj + 1), 6)
            else:
                nom_sub_obj = goutils.pad_txt(
                    objectifs[i_level][0][0] + str(i_sub_obj + 1), 10)
            if txt_mode:
                entete += nom_sub_obj + '|'
            else:
                entete += goutils.pad_txt2(nom_sub_obj) + '|'

    entete += 'GLOB|Joueur\n'

    return entete

def get_team_progress(list_team_names, txt_allyCode, compute_guild,
                        score_type, score_green, score_amber, gv_mode, txt_mode):
                        
    ret_get_team_progress = {}

    #Recuperation des dernieres donnees sur gdrive+
    liste_team_gt, dict_team_gt = connect_gsheets.load_config_teams(dict_unitsAlias, dict_tagAlias)
    
    if not compute_guild:
        #only one player, potentially several teams
        
        #Load or update data for the player
        e, d, t = load_player(txt_allyCode, False, False)
        if e != 0:
            #error wile loading guild data
            return 'ERREUR: joueur non trouvée pour code allié ' + txt_allyCode
            
    else:
        #Get data for the guild and associated players
        ret, guild = load_guild(txt_allyCode, True, True)
        if ret != 'OK':
            goutils.log("WAR", "get_team_progress", "cannot get guild data from SWGOH.HELP API. Using previous data.")

    if not ('all' in list_team_names) and gv_mode:
        #Need to transform the name of the team into a character
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_team_names, dict_unitsAlias, dict_tagAlias)
        if txt != "":
            return 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt
        list_team_names = [x+"-GV" for x in list_character_ids]

    #Get player data
    goutils.log("INFO", "get_team_progress", "Get player data from DB...")
    query = "SELECT players.name, "\
           +"guild_teams.name, "\
           +"guild_team_roster.unit_id, "\
           +"rarity, "\
           +"gear, "\
           +"relic_currentTier, "\
           +"gp, "\
           +"stat5_base+stat5_gear+stat5_mods_crew as speed "\
           +"FROM players "\
           +"JOIN guild_teams "\
           +"JOIN guild_subteams ON guild_subteams.team_id = guild_teams.id "\
           +"JOIN guild_team_roster ON guild_team_roster.subteam_id = guild_subteams.id "\
           +"JOIN roster ON roster.defId = guild_team_roster.unit_id AND roster.allyCode = players.allyCode "
    if not compute_guild:
        query += "WHERE roster.allyCode = '"+txt_allyCode+"'\n"
    else:
        query += "WHERE players.guildName = \
                (SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"')\n"
    if not 'all' in list_team_names:
        query += "AND("
        for team_name in list_team_names:
            query += "guild_teams.name = '"+team_name+"' OR "
        query = query[:-3] + ")\n"
    elif gv_mode == False:
        query += "AND NOT guild_teams.name LIKE '%-GV'\n"
    else:
        query += "AND guild_teams.name LIKE '%-GV'\n"
       
    query += "GROUP BY players.name, guild_teams.name, guild_team_roster.unit_id, \
            rarity, gear, relic_currentTier, gp \
            ORDER BY players.name, guild_teams.name"
    goutils.log("DBG", "get_team_progress", query)
    
    # print(query)
    player_data = connect_mysql.get_table(query)
    goutils.log("DBG", "get_team_progress", player_data)
    
    if not gv_mode:
        # Need the zetas to compute the progress of a regular team
        goutils.log("INFO", "get_team_progress", "Get zeta data from DB...")
        query = "SELECT players.name, \
                guild_teams.name, \
                guild_team_roster.unit_id, \
                guild_team_roster_zetas.name as zeta, \
                roster_skills.level \
                FROM players \
                JOIN guild_teams \
                JOIN guild_subteams ON guild_subteams.team_id = guild_teams.id \
                JOIN guild_team_roster ON guild_team_roster.subteam_id = guild_subteams.id \
                JOIN guild_team_roster_zetas ON guild_team_roster_zetas.roster_id = guild_team_roster.id \
                JOIN roster ON roster.defId = guild_team_roster.unit_id AND roster.allyCode = players.allyCode \
                JOIN roster_skills ON roster_skills.roster_id = roster.id AND roster_skills.name = guild_team_roster_zetas.name \n"
        if not compute_guild:
            query += "WHERE roster.allyCode = '"+txt_allyCode+"'\n"
        else:
            query += "WHERE players.guildName = \
                    (SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"')\n"
        if not 'all' in list_team_names:
            query += "AND("
            for team_name in list_team_names:
                query += "guild_teams.name = '"+team_name+"' OR "
            query = query[:-3] + ")\n"
        elif gv_mode == False:
            query += "AND NOT guild_teams.name LIKE '%-GV'\n"
        else:
            query += "AND guild_teams.name LIKE '%-GV'\n"
           
        query += "ORDER BY roster.allyCode, guild_teams.name, guild_subteams.id, guild_team_roster.id"
        goutils.log("DBG", "get_team_progress", query)
        
        player_zeta_data = connect_mysql.get_table(query)
        if player_zeta_data == None:
            player_zeta_data = []
        
        gv_characters_unlocked = []
    
    else:
        #In gv_mode, there is no requirement for zetas
        player_zeta_data = []
        
        #There is a need to check if the target character is locked or unlocked
        goutils.log("INFO", "get_team_progress", "Get GV characters data from DB...")
        query = "SELECT players.name, defId, rarity \
                FROM roster \
                JOIN players ON players.allyCode = roster.allyCode \n"
        if not compute_guild:
            query += "WHERE roster.allyCode = '"+txt_allyCode+"'\n"
        else:
            query += "WHERE players.guildName = \
                    (SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"')\n"
        query += "AND defId IN (SELECT SUBSTRING_INDEX(name, '-GV', 1) FROM guild_teams WHERE name LIKE '%-GV')"
        goutils.log("DBG", "get_team_progress", query)
        
        #print(query)
        gv_characters_unlocked = connect_mysql.get_table(query)        
        
    if player_data != None:
        goutils.log("INFO", "get_team_progress", "Recreate dict_teams...")
        dict_teams = goutils.create_dict_teams(player_data, player_zeta_data, gv_characters_unlocked)
        goutils.log("INFO", "get_team_progress", "Recreation of dict_teams is OK")
    else:
        query = "SELECT name FROM players WHERE allyCode = "+txt_allyCode
        goutils.log("DBG", "get_team_progress", query)
        player_name = connect_mysql.get_value(query)
        dict_teams = {player_name: {}}
        goutils.log("WAR", "get_team_progress", "no data recovered for allyCode="+txt_allyCode+" and teams="+str(list_team_names))
    
    # Compute teams for this player
    if gv_mode:
        filtered_liste_team_gt = [x for x in 
                                filter(lambda f:f[-3:]=="-GV", liste_team_gt)]
    else:
        filtered_liste_team_gt = [x for x in 
                                filter(lambda f:f[-3:]!="-GV", liste_team_gt)]
    if 'all' in list_team_names:
        list_team_names = filtered_liste_team_gt
    
    for team_name in list_team_names:
        if not (team_name in dict_team_gt) and not ('all' in list_team_names):
            if gv_mode:
                ret_get_team_progress[team_name] = \
                        'ERREUR: Guide de Voyage inconnu pour ' + \
                        team_name + '. Liste=' + str(filtered_liste_team_gt)
            else:
                ret_get_team_progress[team_name] = 'ERREUR: team ' + \
                        team_name + ' inconnue. Liste=' + str(filtered_liste_team_gt)
        else:
            ret_team = []
            objectifs = dict_team_gt[team_name]["categories"]
            #print(objectifs)

            if not gv_mode:
                if len(list_team_names) == 1 and len(dict_teams.keys()) == 1:
                    entete = get_team_entete(team_name, objectifs, \
                                                score_type, txt_mode)
                else:
                    entete = "Team " + team_name + "\n"
                ret_team.append([entete, 999999, '', True])

            tab_lines = []
            count_green = 0
            count_amber = 0
            for player_name in dict_teams:
                if team_name in dict_teams[player_name]:
                    dict_player = dict_teams[player_name][team_name]
                else:
                    dict_player = {}

                #resultats par joueur
                score, unlocked, line, nogo = get_team_line_from_player(team_name,
                    dict_player, dict_team_gt[team_name], score_type, score_green,
                    score_amber, gv_mode, txt_mode, player_name)
                tab_lines.append([score, unlocked, line, nogo, player_name])

                if score >= score_green and not nogo:
                    count_green += 1
                if score >= score_amber and not nogo:
                    count_amber += 1

            #Tri des nogo=False en premier, puis score décroissant
            for score, unlocked, txt, nogo, name in sorted(tab_lines,
                                           key=lambda x: (x[3], -x[0])):
                ret_team.append([txt, score, name, unlocked])

            ret_get_team_progress[team_name] = ret_team, count_green, count_amber

    return ret_get_team_progress

def print_vtx(list_team_names, txt_allyCode, compute_guild):
    ret_print_vtx = ""

    ret_get_team_progress = get_team_progress(list_team_names, txt_allyCode, 
                            compute_guild, 1, 100, 80, False, False)
    for team in ret_get_team_progress:
        ret_team = ret_get_team_progress[team]
        if type(ret_team) == str:
            ret_print_vtx += ret_team + "\n"
        else:
            for team_line in ret_team[0]:
                ret_print_vtx += team_line[0]
    
        ret_print_vtx += "\n"
                
    return ret_print_vtx

def print_gvj(list_team_names, txt_allyCode):
    ret_print_gvj = ""
    
    ret_get_team_progress = get_team_progress(list_team_names, txt_allyCode,
                            False, 1, 100, 80, True, True)
    
    list_lines = []
    if len(ret_get_team_progress) == 1:
        #one team only, one player
        team = list(ret_get_team_progress.keys())[0]
        ret_team = ret_get_team_progress[team]
        if type(ret_team) == str:
            ret_print_gvj += ret_team
        else:
            for ret_player in ret_team[0]:
                player_txt = ret_player[0]
                player_score = ret_player[1]
                player_name = ret_player[2]
                ret_print_gvj += "Progrès dans le Guide de Voyage pour "+player_name+" - "+team[:-3]+"\n"
                ret_print_gvj += player_txt + "> Global: "+\
                                            str(int(player_score))+"%"

    else:
        player_name = ''
        for team in ret_get_team_progress:
            ret_team = ret_get_team_progress[team]
            if type(ret_team) == str:
                ret_print_gvj += ret_team
            else:
                for ret_player in ret_team[0]:
                    player_txt = ret_player[0]
                    player_score = ret_player[1]
                    player_name = ret_player[2]
                    player_unlocked = ret_player[3]
                    new_line = team[:-3] + " - "+ player_name + ": " + \
                                    str(int(player_score)) + "%\n"
                    list_lines.append([player_score, new_line, player_unlocked])
                                            
        list_lines = sorted(list_lines, key=lambda x: -x[0])
        if player_name != '':
            ret_print_gvj += "Progrès dans le Guide de Voyage pour "+player_name+"\n"
        for line in list_lines:
            score = line[0]
            txt = line[1]
            unlocked = line[2]
            if unlocked:
                ret_print_gvj += "\N{WHITE HEAVY CHECK MARK}"
            elif score > 95:
                ret_print_gvj += "\N{WHITE RIGHT POINTING BACKHAND INDEX}"
            elif score > 80:
                ret_print_gvj += "\N{CONFUSED FACE}"
            else:
                ret_print_gvj += "\N{UP-POINTING RED TRIANGLE}"
            ret_print_gvj += txt

    return ret_print_gvj
                        
def print_gvg(list_team_names, txt_allyCode):
    ret_print_gvg = ""
    
    ret_get_team_progress = get_team_progress(list_team_names, txt_allyCode,
                            True, 1, 100, 80, True, True)
    
    list_lines = []
    for team in ret_get_team_progress:
        ret_team = ret_get_team_progress[team]
        if type(ret_team) == str:
            ret_print_gvg += ret_team + "\n"
        else:
            for ret_player in ret_team[0]:
                player_txt = ret_player[0]
                player_score = ret_player[1]
                player_name = ret_player[2]
                player_unlocked = ret_player[3]
                if not player_unlocked:
                    new_line = team[:-3] + " - "+ player_name + ": " + \
                                    str(int(player_score)) + "%\n"
                    list_lines.append([player_score, new_line, player_unlocked])
                    
    list_lines = sorted(list_lines, key=lambda x: -x[0])
    ret_print_gvg += "Progrès dans le Guide de Voyage pour la guilde (top "+str(MAX_GVG_LINES)+")\n"
    ret_print_gvg += "(seuls les joueurs qui n'ont pas le perso au max sont listés)\n"
    for line in list_lines[:MAX_GVG_LINES]:
        score = line[0]
        txt = line[1]
        unlocked = line[2]
        if score > 95:
            ret_print_gvg += "\N{WHITE RIGHT POINTING BACKHAND INDEX}"
        elif score > 80:
            ret_print_gvg += "\N{CONFUSED FACE}"
        else:
            ret_print_gvg += "\N{UP-POINTING RED TRIANGLE}"
        ret_print_gvg += txt
        
    return ret_print_gvg
                       
def assign_gt(allyCode, txt_mode):
    ret_assign_gt = ''

    dict_players = connect_gsheets.load_config_players()[0]

    liste_territoires = connect_gsheets.load_config_gt()
        # index=priorité-1, value=[territoire, [[team, nombre, score]...]]
    liste_team_names = []
    for territoire in liste_territoires:
        for team in territoire[1]:
            liste_team_names.append(team[0])
    liste_team_names = [x for x in set(liste_team_names)]
    #print(liste_team_names)

    #Calcule des meilleurs joueurs pour chaque team
    dict_teams = get_team_progress(liste_team_names, allyCode, True, 3, -1, -1, True, True)
    if type(dict_teams) == str:
        return dict_teams
    else:
        for team in dict_teams:
            #la fonction renvoie un tuple (txt, nombre)
            #on ne garde que le txt, qu'on splite en lignes avec séparateur
            dict_teams[team] = dict_teams[team][0].split('\n')

    for priorite in liste_territoires:
        nom_territoire = priorite[0]
        for team in priorite[1]:
            tab_lignes_team = dict_teams[team[0]]
            #print(ret_function_gtt)
            if tab_lignes_team[0][0:3] == "ERR":
                ret_assign_gt += nom_territoire + ': **WARNING** team inconnue ' + team[
                    0] + '\n'
            else:
                req_nombre = team[1]
                req_score = team[2]
                nb_joueurs_selectionnes = 0
                copy_tab_lignes_team = [x for x in tab_lignes_team]
                for ligne in copy_tab_lignes_team:
                    tab_joueur = ligne.split('|')
                    if len(tab_joueur) > 1 and tab_joueur[-1] != 'Joueur':
                        #print(tab_joueur)
                        nom_joueur = tab_joueur[-1]
                        score_joueur = int(tab_joueur[-2])
                        if score_joueur >= req_score:
                            if req_nombre == '' or nb_joueurs_selectionnes < req_nombre:
                                nb_joueurs_selectionnes += 1
                                ret_assign_gt += nom_territoire + ': '
                                if nom_joueur in dict_players and not txt_mode:
                                    player_mention = dict_players[nom_joueur][1]
                                    ret_assign_gt += player_mention
                                else:  #joueur non-défini dans gsheets ou mode texte
                                    ret_assign_gt += nom_joueur
                                ret_assign_gt += ' doit placer sa team ' + team[
                                    0] + '\n'
                                tab_lignes_team.remove(ligne)

                if req_nombre != '' and nb_joueurs_selectionnes < req_nombre:
                    ret_assign_gt += nom_territoire + ': **WARNING** pas assez de team ' + team[
                        0] + '\n'

            ret_assign_gt += '\n'

    return ret_assign_gt


def score_of_counter_interest(team_name, counter_matrix):
    current_score = 0
    for row in counter_matrix:
        # Count if the team_name can counter the current team row
        # Ignore the row if the team counters itself
        if team_name in row[1] and row[0] != team_name:
            current_score += 1
    return current_score


def guild_counter_score(txt_allyCode):
    ret_guild_counter_score = f"""
*Rec = Niveau recommandé / Min = Niveau minimum*
*w/o TW Def = Idem en enlevant les équipes placées en défense d'une TW*
*L'intérêt absolu mesure le nombre de fois que l'équipe X intervient en tant qu'équipe de contre*
{FORCE_CUT_PATTERN}
"""

    list_counter_teams = connect_gsheets.load_config_counter()
    list_needed_teams = set().union(*[(lambda x: x[1])(x)
                                      for x in list_counter_teams])
    dict_needed_teams = get_team_progress(list_needed_teams, txt_allyCode, True,
                                            1, 100, 80, False, True)
    # for k in dict_needed_teams.keys():
    # dict_needed_teams[k]=list(dict_needed_teams[k])
    # dict_needed_teams[k][0]=[]
    # print(list_counter_teams)

    gt_teams = connect_gsheets.load_config_gt()
    gt_teams = [(name[0], name[1]) for name in
                [teams for territory in gt_teams for teams in territory[1]]]

    result = []
    for nteam_key in dict_needed_teams.keys():
        if dict_needed_teams[nteam_key][0][:3] == 'ERR':
            result.append({
                "team_name": None,
                "rec_count": None,
                "min_count": None,
                "score": None,
                "max_score": None,
                "error": dict_needed_teams[nteam_key][0]
            })
        else:
            result.append({
                "team_name": nteam_key,
                "rec_count": dict_needed_teams[nteam_key][1],
                "min_count": dict_needed_teams[nteam_key][2],
                "score": score_of_counter_interest(nteam_key,
                                                   list_counter_teams),
                "max_score": len(list_counter_teams),
                "error": None
            })

    result = sorted(
        result,
        key=lambda i:
        (i['score'], i['rec_count'], i['min_count'], i['team_name']))

    ret_guild_counter_score += """
\n**Nombre de joueurs ayant l'équipe X**
```
{0:15}: {1:3} ↗ {2:3} | {3:10} - {4:5}
""".format("Equipe", "Rec", "Min", "w/o TW Def", "Intérêt absolu")

    for line in result:
        if line["error"]:
            ret_guild_counter_score += line["error"] + '\n'
            continue

        gt_subteams = list(
            filter(lambda x: x[0] == line["team_name"], gt_teams))
        needed_team_named = 0
        if gt_subteams:
            needed_team_named = reduce(
                lambda x, y: x[1] + y[1],
                gt_subteams) if len(gt_subteams) > 1 else gt_subteams[0][1]

        ret_guild_counter_score += "{0:15}: {1:3} ↗"\
                " {2:3} | {3:3} ↗ {4:3}  - {5:2}/{6:2}\n".format(
                    line["team_name"],
                    line["rec_count"],
                    line["min_count"],
                    max(0, line["rec_count"]-needed_team_named),
                    max(0, line["min_count"]-needed_team_named),
                    line["score"],
                    line["max_score"])

    ret_guild_counter_score += f"```{FORCE_CUT_PATTERN}"

    ret_guild_counter_score += """
\n**Capacité de contre par adversaire**
```
{0:15}: {1:3} ↗ {2:3} | {3:10} 🎯 {4:2}
""".format("Equipe", "Rec", "Min", "w/o TW Def", "Besoin cible")
    for cteam in sorted(list_counter_teams):
        green_counters = 0
        green_counters_wo_def = 0
        amber_counters = 0
        amber_counters_wo_def = 0
        for team in cteam[1]:
            green_counters += dict_needed_teams[team][1]
            amber_counters += dict_needed_teams[team][2]

            # compute how many we need to set on TW defence
            gt_subteams = list(filter(lambda x: x[0] == team, gt_teams))
            needed_team_named = 0
            if gt_subteams:
                needed_team_named = reduce(
                    lambda x, y: x[1] + y[1],
                    gt_subteams) if len(gt_subteams) > 1 else gt_subteams[0][1]

            green_counters_wo_def += dict_needed_teams[team][1]\
                                   - needed_team_named
            amber_counters_wo_def += dict_needed_teams[team][2]\
                                   - needed_team_named

        ret_guild_counter_score += "{0:15}: {1:3} ↗"\
                                   " {2:3} | {3:3} ↗ {4:3}  🎯 {5:2}\n".format(
                                       cteam[0],
                                       green_counters,
                                       amber_counters,
                                       green_counters_wo_def,
                                       amber_counters_wo_def,
                                       cteam[2])
    ret_guild_counter_score += "```"

    return ret_guild_counter_score

def print_character_stats(characters, txt_allyCode, compute_guild):
    ret_print_character_stats = ''

    #Recuperation des dernieres donnees sur gdrive
    dict_units = connect_gsheets.load_config_units(dict_unitsAlias)

    list_stats_for_display=[['5', "Vit", False, 'v'],
                            ['6', "DegPhy", False, 'd'],
                            ['7', "DegSpé", False, ''],
                            ['1', " Santé", False, 's'],
                            ['28', "Protec", False, ''],
                            ['17', "Pouvoir", True, 'p'],
                            ['18', "Ténacité", True, '']]
    
    #manage sorting options
    sort_option='name'
    if characters[0][0] == '-':
        sort_option = characters[0][1:]
        characters = characters[1:]
        
    dict_virtual_characters={} #{key=alias or ID, value=[gear, relic, nameKey]}

    if not compute_guild:
        #only one player, potentially several characters
        
        #parse the list to detect virtual characters "name:R4" or "name:G11"
        for character in characters:
            if not character.startswith("tag:"):
                tab_virtual_character = character.split(':')
                if len(tab_virtual_character) == 3:
                    char_alias = tab_virtual_character[0]
                    if char_alias == "all":
                        return "ERR: impossible de demander un niveau spécifique pour all"
                    
                    if not tab_virtual_character[1] in "1234567":
                        return "ERR: la syntaxe "+character+" est incorrecte pour les étoiles"
                    char_rarity = int(tab_virtual_character[1])

                    if tab_virtual_character[2][0] in "gG":
                        if tab_virtual_character[2][1:].isnumeric():
                            char_gear = int(tab_virtual_character[2][1:])
                            if (char_gear<1) or (char_gear>13):
                                return "ERR: la syntaxe "+character+" est incorrecte pour le gear"
                            dict_virtual_characters[char_alias] = [char_rarity, char_gear, 0]
                        else:
                            return "ERR: la syntaxe "+character+" est incorrecte pour le gear"
                    elif tab_virtual_character[2][0] in "rR":
                        if tab_virtual_character[2][1:].isnumeric():
                            char_relic = int(tab_virtual_character[2][1:])
                            if (char_relic<0) or (char_relic>8):
                                return "ERR: la syntaxe "+character+" est incorrecte pour le relic"
                            dict_virtual_characters[char_alias] = [char_rarity, 13, char_relic]
                        else:
                            return "ERR: la syntaxe "+character+" est incorrecte pour le relic"
                    else:
                        return "ERR: la syntaxe "+character+" est incorrecte pour le gear"
                        
                    #now that the virtual character is stored in the dictionary,
                    # let the alias only in the list of characters
                    characters = [char_alias if x == character else x for x in characters]
                    
                elif len(tab_virtual_character) == 2:
                    char_alias = tab_virtual_character[0]
                    if char_alias == "all":
                        return "ERR: impossible de demander un niveau spécifique pour all"
                    
                    if tab_virtual_character[1][0] in "gG":
                        if tab_virtual_character[1][1:].isnumeric():
                            char_gear = int(tab_virtual_character[1][1:])
                            if (char_gear<1) or (char_gear>13):
                                return "ERR: la syntaxe "+character+" est incorrecte pour le gear"
                            dict_virtual_characters[char_alias] = [None, char_gear, 0]
                        else:
                            return "ERR: la syntaxe "+character+" est incorrecte pour le gear"
                    elif tab_virtual_character[1][0] in "rR":
                        if tab_virtual_character[1][1:].isnumeric():
                            char_relic = int(tab_virtual_character[1][1:])
                            if (char_relic<0) or (char_relic>8):
                                return "ERR: la syntaxe "+character+" est incorrecte pour le relic"
                            dict_virtual_characters[char_alias] = [None, 13, char_relic]
                        else:
                            return "ERR: la syntaxe "+character+" est incorrecte pour le relic"
                    elif tab_virtual_character[1] in "1234567":
                        char_rarity = int(tab_virtual_character[1])
                        dict_virtual_characters[char_alias] = [char_rarity, None, None]

                    else:
                        return "ERR: la syntaxe "+character+" est incorrecte"
                        
                    #now that the virtual character is stored in the dictionary,
                    # let the alias only in the list of characters
                    characters = [char_alias if x == character else x for x in characters]
                    
                elif len(tab_virtual_character) == 1:
                    #regular character, not virtual
                    pass
                else:
                    return "ERR: la syntaxe "+character+" est incorrecte"
        
        #Get data for this player
        e, dict_player, t = load_player(txt_allyCode, False, False)
        player_name = dict_player["name"]
        list_player_names = [player_name]

        if e != 0:
            #error wile loading guild data
            return 'ERREUR: joueur non trouvé pour code allié ' + txt_allyCode
        
        #Manage request for all characters
        if 'all' in characters:
            dict_stats = {player_name: dict_player['roster']}
            list_character_ids=list(dict_player["roster"].keys())
            
        else:
            #specific list of characters for one player
            list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(characters, dict_unitsAlias, dict_tagAlias)
            if txt != '':
                return 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt

            #Manage virtual characters
            if len(dict_virtual_characters) > 0:
                for character_alias in dict_id_name:
                    [character_id, character_name] = dict_id_name[character_alias][0]
                    if (character_alias in dict_virtual_characters) and \
                        character_alias != character_id:
                        #Update the character information in roster
                        virtual_rarity = dict_virtual_characters[character_alias][0]
                        virtual_gear = dict_virtual_characters[character_alias][1]
                        virtual_relic = dict_virtual_characters[character_alias][2]

                        dict_player["roster"][character_id]["level"] = 85
                        if virtual_rarity != None:
                            dict_player["roster"][character_id]["rarity"] = virtual_rarity
                        if dict_player["roster"][character_id]["combatType"] == 1:
                            if virtual_gear != None:
                                    dict_player["roster"][character_id]["gear"] = virtual_gear
                            if virtual_relic != None:
                                dict_player["roster"][character_id]["relic"]["currentTier"] = virtual_relic +2
                
                #Filter on useful only characters
                del dict_player["arena"]
                del dict_player["grandArena"]
                del dict_player["portraits"]
                del dict_player["stats"]
                del dict_player["titles"]
                
                #Recompute stats with Crinolo API
                dict_player = goutils.roster_from_dict_to_list(dict_player)
                dict_player = connect_crinolo.add_stats(dict_player)
                dict_player = goutils.roster_from_list_to_dict(dict_player)

            dict_stats = {player_name: dict_player['roster']}

        
        ret_print_character_stats += "Statistiques pour "+player_name+'\n'


    elif len(characters) == 1 and characters[0] != "all" and not characters[0].startswith("tag:"):
        #Compute stats at guild level, only one character
        
        #Get data for the guild and associated players
        ret, guild = load_guild(txt_allyCode, True, True)
        if ret != 'OK':
            return "ERR: cannot get guild data from SWGOH.HELP API"
                            
        #Get character_id
        character_alias = characters[0]
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([character_alias], dict_unitsAlias, dict_tagAlias)
        if txt != '':
            return 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt
                                    
        character_id = list_character_ids[0]
        db_stat_data_char = []
        goutils.log("INFO", "print_character_stats", "Get guild_data from DB...")
        query = "SELECT players.name, defId, "\
               +"roster.combatType, rarity, gear, relic_currentTier, "\
               +"stat1_base+stat1_gear+stat1_mods_crew AS stat1, "\
               +"stat5_base+stat5_gear+stat5_mods_crew AS stat5, "\
               +"stat6_base+stat5_gear+stat6_mods_crew AS stat6, "\
               +"stat7_base+stat5_gear+stat7_mods_crew AS stat7, "\
               +"stat17_base+stat17_gear+stat17_mods_crew AS stat17, "\
               +"stat18_base+stat18_gear+stat18_mods_crew AS stat18, "\
               +"stat28_base+stat28_gear+stat28_mods_crew AS stat28 "\
               +"FROM roster "\
               +"JOIN players ON players.allyCode = roster.allyCode "\
               +"WHERE players.guildName = (SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"') "\
               +"AND defId = '"+character_id+"' "\
               +"ORDER BY players.name, defId"

        db_stat_data = connect_mysql.get_table(query)
        db_stat_data_mods = []
        list_character_ids=[character_id]
        list_player_names=set([x[0] for x in db_stat_data])
        character_name = dict_id_name[character_alias][0][1]
        
        ret_print_character_stats += "Statistiques pour "+character_name+'\n'
    
        # Generate dict from DB data
        dict_stats = goutils.create_dict_stats(db_stat_data_char, db_stat_data, db_stat_data_mods, dict_unitsList)
    else:
        return "ERR: les stats au niveau guilde ne marchent qu'avec un seul perso à la fois"
    

    # Create all lines before display
    list_print_stats=[]
    for player_name in list_player_names:
        if player_name in dict_stats:
            dict_player = dict_stats[player_name]
        else:
            dict_player={}
        for character_id in list_character_ids:
            if character_id in dict_player:
                character_name = dict_player[character_id]["nameKey"]
                character_rarity = str(dict_player[character_id]["rarity"])+"*"
                character_gear = dict_player[character_id]["gear"]
                if dict_player[character_id]["combatType"] == 1:
                    if character_gear == 13:
                        character_relic = dict_player[character_id]["relic"]["currentTier"]
                        character_gear = "R"+str(character_relic-2)
                    else:
                        character_gear="G"+str(character_gear)
                else: #ship
                    character_gear=''

                #Sum all different stats into one
                character_stats = {}
                for stat_type in dict_player[character_id]["stats"]:
                    for stat_id in dict_player[character_id]["stats"][stat_type]:
                        stat_value = dict_player[character_id]["stats"][stat_type][stat_id]
                        if stat_value != None:
                            if stat_id in character_stats:
                                character_stats[stat_id] += dict_player[character_id]["stats"][stat_type][stat_id]
                            else:
                                character_stats[stat_id] = dict_player[character_id]["stats"][stat_type][stat_id]
                
                if compute_guild:
                    line_header = player_name
                else:
                    line_header = character_name
                list_print_stats.append([line_header, character_rarity+character_gear, character_stats])
                        
            else:
                ret_print_character_stats +=  'INFO: ' + character_id+' non trouvé chez '+player_name+'\n'

    if len (list_print_stats)>0:
        # Default sort by character name in case of "all" for characters
        # or by player name if guild statistics
        if 'all' in characters or compute_guild:
            list_print_stats = sorted(list_print_stats, key=lambda x: x[0])
            
        # Sort by specified stat
        for stat in list_stats_for_display:
            if sort_option == stat[3]:
                list_print_stats = sorted(list_print_stats,
                    key=lambda x: -x[2][stat[0]] if stat[0] in x[2] else 0)
        
        ret_print_character_stats += "=====================================\n"
        max_size_char = max([len(x[0]) for x in list_print_stats])
        if compute_guild:
            ret_print_character_stats += ("{0:"+str(max_size_char)+"}: {1:5} ").format("Joueur", "*+G")
            max_size_char = max(max_size_char, len("Joueur"))
        else:
            ret_print_character_stats += ("{0:"+str(max_size_char)+"}: {1:5} ").format("Perso", "*+G")
            max_size_char = max(max_size_char, len("Perso"))
        
        for stat in list_stats_for_display:
            ret_print_character_stats += stat[1]+' '
        ret_print_character_stats += "\n"

        for print_stat_row in list_print_stats:
            ret_print_character_stats += ("{0:"+str(max_size_char)+"}: ").format(print_stat_row[0])
            ret_print_character_stats += ("{0:5} ").format(print_stat_row[1])
            for stat in list_stats_for_display:
                if stat[0] in print_stat_row[2]:
                    stat_value = print_stat_row[2][stat[0]]
                else:
                    stat_value = 0
                if stat[2]:
                    # Percent value
                    ret_print_character_stats += ("{0:"+str(len(stat[1])-1)+".2f}% ").format(stat_value/1e6)
                else:
                    # Flat value
                    ret_print_character_stats += ("{0:"+str(len(stat[1]))+"} ").format(int(stat_value/1e8))
        
            ret_print_character_stats += "\n"

    return ret_print_character_stats

def get_distribution_graph(values, bins, title, highlight_value):
    fig, ax = plt.subplots()
    ax.hist(values, bins=bins)
    fig.suptitle(title)

    if highlight_value != None:
        min_x = plt.xlim()[0]
        max_x = plt.xlim()[1]
        bin_width = (max_x - min_x) / bins
        plt.axvspan(highlight_value - bin_width/2,
                    highlight_value + bin_width/2,
                    color='red', alpha = 0.5)

    fig.canvas.draw()
    fig_size = fig.canvas.get_width_height()
    fig_bytes = fig.canvas.tostring_rgb()
    image = Image.frombytes('RGB', fig_size, fig_bytes)

    return image

def get_gp_distribution(txt_allyCode):
    #Load or update data for the guild
    #use only the guild data from the API
    ret, guild = load_guild(txt_allyCode, False, True)
    if ret != 'OK':
        return 1, "ERR: cannot get guild data from SWGOH.HELP API", None

    guild_stats=[] #Serie of all players
    for player in guild['roster']:
        gp = (player['gpChar'] + player['gpShip']) / 1000000
        guild_stats.append(gp)
    guild_name = guild["name"]

    graph_title = "GP stats " + guild_name + "("+str(len(guild_stats))+" joueurs)"

    #compute ASCII graphs
    image = get_distribution_graph(guild_stats, 20, graph_title, None)
    
    return 0, "", image

def get_tb_alerts():
    tb_trigger_messages=[]

    tb_active_triggers = connect_gsheets.get_tb_triggers({}, True)
    #print(tb_active_triggers)
    if len(tb_active_triggers) > 0:
        territory_scores = connect_warstats.parse_warstats_tb_scores()
        #print(territory_scores)
        if len(territory_scores) > 0:
            tb_trigger_messages = connect_gsheets.get_tb_triggers(territory_scores, False)
    
    return tb_trigger_messages
    
#################################
# Function: get_character_image
# IN:list_characters_allyCode: [[[id1, id2, ...], allyCode, tw territory], ...]
# return: err_code, err_txt, image
#################################
def get_character_image(list_characters_allyCode, is_ID):
    err_code = 0
    err_txt = ''

    #Get data for all players
    #print(list_characters_allyCode)
    list_allyCodes = list(set([x[1] for x in list_characters_allyCode]))
    
    #transform aliases into IDs
    if not is_ID:
        list_alias = [j for i in [x[0] for x in list_characters_allyCode] for j in i]
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_alias, dict_unitsAlias, dict_tagAlias)
        if txt != '':
            err_txt += 'WAR: impossible de reconnaître ce(s) nom(s) >> '+txt+"\n"

    list_ids_dictplayer = []
    for [characters, txt_allyCode, tw_terr] in list_characters_allyCode:
        e, dict_player, t = load_player(txt_allyCode, False, False)
        if e != 0:
            #error wile loading guild data
            goutils.log("WAR", "get_character_image", "joueur non trouvé pour code allié " + txt_allyCode)
            err_txt += 'WAR: joueur non trouvé pour code allié ' + txt_allyCode+'\n'
            dict_player = {"allyCode": txt_allyCode}

        if is_ID:
            list_ids = characters
        else:
            list_ids = []
            for alias in characters:
                if alias in dict_id_name:
                    for id_name in dict_id_name[alias]:
                        list_ids.append(id_name[0])
        
        for id in list_ids:
            if id in dict_player["roster"]:
                if id in dict_unitsList:
                    forceAlignment = dict_unitsList[id]["forceAlignment"]
                else:
                    goutils.log("WAR", "get_character_image", "unknown forceAlignment for "+id)
                    forceAlignment = 1
                dict_player["roster"][id]["forceAlignment"] = forceAlignment
            
        if len(list_ids) == 0:
            err_txt += 'WAR: aucun personnage valide pour '+txt_allyCode
        else:
            list_ids_dictplayer.append([list_ids, dict_player, tw_terr])

    if len(list_ids_dictplayer) == 0:
        return 1, err_txt, None

    list_images = []
    idx = 0
    while len(list_ids_dictplayer) > idx:
        list_ids_dictplayer_5 = list_ids_dictplayer[idx:idx+5]
        image = portraits.get_image_from_teams(list_ids_dictplayer_5)
        list_images.append([image, len(list_ids_dictplayer_5)])
        idx += 5
    
    return err_code, err_txt, list_images

#################################
# Function: get_tw_battle_images
# return: err_code, err_txt, list of images
#################################
def get_tw_battle_image(list_char_attack, allyCode_attack, \
                        character_defense):
    err_code = 0
    err_txt = ''

    #Recuperation des dernieres donnees sur gdrive
    dict_units = connect_gsheets.load_config_units(dict_unitsAlias)
    
    #Get full character names for attack
    list_id_attack, dict_id_name, txt = goutils.get_characters_from_alias(list_char_attack, dict_unitsAlias, dict_tagAlias)
    if txt != '':
        err_txt += 'WAR: impossible de reconnaître ce(s) nom(s) >> '+txt+"\n"

    #Get full character name for defense
    list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([character_defense], dict_unitsAlias, dict_tagAlias)
    if txt != '':
        err_txt += 'WAR: impossible de reconnaître ce(s) nom(s) >> '+txt+"\n"
    char_def_id = list_character_ids[0]

    #Get full character names for defense squads
    list_opp_squad_ids = []

    list_opponent_squads = connect_warstats.parse_warstats_tw_teams()
    if len(list_opponent_squads) == 0:
        goutils.log("ERR", "get_tw_battle_image", "aucune phase d'attaque en cours en GT")
        err_txt += "ERR: aucune phase d'attaque en cours en GT\n"
        return 1, err_txt, None

    list_opponent_char_alias = list(set([j for i in [x[2] for x in list_opponent_squads] for j in i]))
    list_opponent_char_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_opponent_char_alias, dict_unitsAlias, dict_tagAlias)
    if txt != '':
        err_txt += 'WAR: impossible de reconnaître ce(s) nom(s) >> '+txt+"\n"

    for opp_squad in list_opponent_squads:
        territory = opp_squad[0]
        player_name = opp_squad[1]
        squad_char_ids = []
        squad_char_alias = opp_squad[2]
        for char_alias in squad_char_alias:
            char_id = dict_id_name[char_alias][0][0]
            squad_char_ids.append(char_id)

        list_opp_squad_ids.append([territory, player_name, squad_char_ids])

    list_opp_squads_with_char = list(filter(lambda x:char_def_id in x[2], list_opp_squad_ids))
    if len(list_opp_squads_with_char) == 0:
        err_txt += 'ERR: '+character_defense+' ne fait pas partie des teams en défense\n'
        return 1, err_txt, None

    # Look for the name among known player names in DB
    results = connect_mysql.simple_query("SELECT name, allyCode FROM players", False)
    #print(results)
    list_names = [x[0] for x in results[0]]

    for opp_squad in list_opp_squads_with_char:
        player_name = opp_squad[1]

        closest_names=difflib.get_close_matches(player_name, list_names, 1)
        #print(closest_names)
        if len(closest_names)<1:
            err_txt += 'ERR: '+player_name+' ne fait pas partie des joueurs connus\n'
        else:
            print('INFO: cmd launched with name that looks like '+closest_names[0])
            for r in results[0]:
                if r[0] == closest_names[0]:
                    opp_squad[1] = str(r[1])

    #print(list_opp_squads_with_char)
    list_char_allycodes = []
    list_char_allycodes.append([list_id_attack, allyCode_attack, ''])
    for opp_squad in list_opp_squads_with_char:
        list_char_allycodes.append([opp_squad[2], opp_squad[1], opp_squad[0]])

    #print(list_char_allycodes)
    e, t, images = get_character_image(list_char_allycodes, True)
    err_txt += t
    if e != 0:
        return 1, err_txt, None

    return 0, err_txt, images

def get_stat_graph(txt_allyCode, character_alias, stat_name):
    ret, guild = load_guild(txt_allyCode, True, True)
    if ret != 'OK':
        return 1, "ERR: cannot get guild data from SWGOH.HELP API", None
        
    #Get character_id
    list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([character_alias], dict_unitsAlias, dict_tagAlias)
    if txt != '':
        return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt, None
            
    character_id = list_character_ids[0]
    character_name = dict_id_name[character_alias][0][1]

    #Get statistic id
    closest_names=difflib.get_close_matches(stat_name.lower(), dict_stat_names.keys(), 1)
    if len(closest_names)<1:
        return 1, 'ERR: '+stat_name+' ne fait pas partie des stats connues', None

    goutils.log("INFO", "get_stat_graph", "cmd launched with stat name that looks like "+closest_names[0])
    stat_name = closest_names[0]
    stat_id = dict_stat_names[stat_name][0]
    stat_isPercent = dict_stat_names[stat_name][1]
    stat_header = "stat"+str(stat_id)
    stat_string = stat_header+"_base + "+\
                  stat_header+"_gear + "+\
                  stat_header+"_mods + "+\
                  stat_header+"_crew"

    #Get data from DB
    db_stat_data_char = []
    goutils.log("INFO", "get_stat_char", "Get guild_data from DB...")
    query = "SELECT allyCode, gear,"\
           +stat_string+","\
           +"CASE WHEN allyCode="+txt_allyCode+" THEN 1 ELSE 0 END "\
           +"from roster "\
           +"where defId = '"+character_id+"' "\
           +"AND not isnull("+stat_string+") "\
           +"AND (gear = 13 or allyCode = "+txt_allyCode+")"
    goutils.log("DBG", "get_stat_graph", query)
    db_data = connect_mysql.get_table(query)

    if stat_isPercent:
        stat_divider = 1000000
    else:
        stat_divider = 100000000

    stat_g13_values = [x[2]/stat_divider for x in db_data if x[1]==13]
    player_value = [x[2]/stat_divider for x in db_data if x[3]==1][0]

    title = stat_name + " de " + character_name
    title+= " parmi les " + str(len(stat_g13_values)) + " relic connus"
    image = get_distribution_graph(stat_g13_values, 50, title, player_value)
    
    return 0, "", image
