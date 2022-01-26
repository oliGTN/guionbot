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
from collections import Counter
import inspect
from texttable import Texttable

import connect_gsheets
import connect_mysql
import connect_crinolo
import connect_warstats
import goutils
import portraits
import parallel_work
import data

FORCE_CUT_PATTERN = "SPLIT_HERE"
MAX_GVG_LINES = 50

SCORE_GREEN = 100
SCORE_ALMOST_GREEN = 95
SCORE_AMBER = 80
SCORE_RED = 50

#login password sur https://api.swgoh.help/profile
if config.SWGOHAPI_LOGIN != "":
    creds = settings(config.SWGOHAPI_LOGIN, config.SWGOHAPI_PASSWORD, '123', 'abc')
    client = SWGOHhelp(creds)
else:
    client = None

#Clean temp files
parallel_work.clean_cache()

dict_stat_names={} # unitStatUd, is percentage
dict_stat_names["speed"] = [5, False, "Vitesse"]
dict_stat_names["vitesse"] = [5, False, "Vitesse"]
dict_stat_names["protection"] = [28, False, "Protection"]
dict_stat_names["dégâts physiques"] = [6, False, "Dégâts Physiques"]
dict_stat_names["physical damages"] = [6, False, "Dégâts Physiques"]
dict_stat_names["dégâts spéciaux"] = [7, False, "Dégâts spéciaux"]
dict_stat_names["special damages"] = [7, False, "Dégâts spéciaux"]
dict_stat_names["santé"] = [1, False, "Santé"]
dict_stat_names["health"] = [1, False, "Santé"]
dict_stat_names["chances de coup critique"] = [14, True, "Chances de coups critique"]
dict_stat_names["cdc"] = [14, True, "Chances de coups critique"]
dict_stat_names["critical chance"] = [14, True, "Chances de coups critique"]
dict_stat_names["cc"] = [14, True, "Chances de coups critique"]
dict_stat_names["dégâts critiques"] = [16, True, "Dégâts critiques"]
dict_stat_names["dc"] = [16, True, "Dégâts critiques"]
dict_stat_names["critical damages"] = [16, True, "Dégâts critiques"]
dict_stat_names["cd"] = [16, True, "Dégâts critiques"]
dict_stat_names["pouvoir"] = [17, True, "Pouvoir"]
dict_stat_names["potency"] = [17, True, "Pouvoir"]
dict_stat_names["tenacité"] = [18, True, "Ténacité"]
dict_stat_names["tenacity"] = [18, True, "Ténacité"]

##################################
# Function: manage_disk_usage
# return: None
##################################
def manage_disk_usage():
    st = os.statvfs('/')
    free = st.f_bavail * st.f_frsize
    total = st.f_blocks * st.f_frsize
    used = total - free
    used_percentage = int(used/total*1000)/10
    goutils.log('INFO', 'go.manage_disk_usage', 'Disk usage = ' + str(used_percentage) + '%')

    if used_percentage > 98:
        return 1, "Disk usage is above 98%"
    else:
        return 0, ""

##################################
# Function: refresh_cache
# return: error code
##################################
def refresh_cache():
    #CLEAN OLD FILES NOT ACCESSED FOR LONG TIME
    #Need to keep KEEPDIR to prevent removal of the directory by GIT
    
    # Get the allyCodes to be refreshed
    # the query gets one allyCode by guild in the DB
    query = "SELECT guilds.name, allyCode "\
           +"FROM guilds "\
           +"JOIN players on players.guildName = guilds.name "\
           +"WHERE guilds.update=1 "\
           +"ORDER BY guilds.lastUpdated"
    goutils.log('DBG', 'go.refresh_cache', query)
    ret_table = connect_mysql.get_table(query)
    
    if ret_table != None:
        for line in ret_table:
            guild_name = line[0]
            guild_allyCode = line[1]
            goutils.log('INFO', 'go.refresh_cache', "refresh guild " + guild_name \
                       +" with allyCode " + str(guild_allyCode))
            e, t = load_guild(str(guild_allyCode), False, False)
            if e == "OK" and t['name'] == guild_name:
                e, t = load_guild(str(guild_allyCode), True, False)
                return 0
        
    goutils.log('ERR', 'go.refresh_cache', "Unable to refresh guilds")
    return 1

##################################
# Function: refresh_cache
# inputs: txt_allYCode (string)
#         int force_update (0: default, 1: force update, -1, do not update unless there is no XML)
#         bool no_db: do not put player in DB
# return: erro_code, err_text
##################################
def load_player(txt_allyCode, force_update, no_db):
    goutils.log2("DBG", "START")

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
        goutils.log2("INFO", 'reading file ' + json_file + '...')
        if os.path.isfile(json_file):
            prev_dict_player = json.load(open(json_file, 'r'))
            prev_dict_player = goutils.roster_from_list_to_dict(prev_dict_player)
        else:
            prev_dict_player = None

    if (not recent_player or force_update==1) and not (force_update==-1 and prev_dict_player != None):
        goutils.log("INFO", "go.load_player", 'requesting API data for ' + txt_allyCode + '...')
        if client != None:
            player_data = client.get_data('player', [txt_allyCode], 'FRE_FR')
        else:
            goutils.log("WAR", "go.load_player", 'Cannot connect to API. Using cache data from json')
            player_data = [prev_dict_player]

        if isinstance(player_data, list):
            if len(player_data) > 0:
                if len(player_data) > 1:
                   goutils.log("WAR", "go.load_player", "client.get_data(\'player\', "+txt_allyCode+
                            ", 'FRE_FR') has returned a list of size "+
                            str(len(player_data)))
                            
                dict_player = player_data[0]
        
                #Add statistics
                dict_player = connect_crinolo.add_stats(dict_player)

                #Transform the roster into dictionary with key = defId
                dict_player = goutils.roster_from_list_to_dict(dict_player)

                goutils.log("INFO", "go.load_player", "success retrieving "+dict_player['name']+" from SWGOH.HELP API")
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
                    ret = connect_mysql.update_player(delta_dict_player)
                    if ret == 0:
                        goutils.log("INFO", "go.load_player", "success updating "+dict_player['name']+" in DB")
                    else:
                        goutils.log('ERR', "go.load_player", 'update_player '+txt_allyCode+' returned an error')
                        return 1, None, 'ERR: update_player '+txt_allyCode+' returned an error'
                    sys.stdout.flush()
                
            else:
                goutils.log('ERR', 'go.load_player', 'client.get_data(\'player\', '+txt_allyCode+
                        ", 'FRE_FR') has returned an empty list")
                sys.stdout.flush()
                return 1, None, 'ERR: allyCode '+txt_allyCode+' not found'

        else:
            goutils.log('ERR', 'go.load_player', 'client.get_data(\'player\', '+
                    txt_allyCode+", 'FRE_FR') has not returned a list")
            goutils.log('ERR', 'go.load_player',player_data)
            sys.stdout.flush()
            return 1, None, 'ERR: allyCode '+txt_allyCode+' not found'

    else:
        goutils.log('INFO', 'go.load_player',player_name + ' OK')
        dict_player = prev_dict_player
    
    sys.stdout.flush()
    return 0, dict_player, ''

def load_guild(txt_allyCode, load_players, cmd_request):
    #Get API data for the guild
    goutils.log('INFO', "go.load_guild", 'Requesting guild data for allyCode ' + txt_allyCode)

    query = "SELECT id FROM guilds "
    query+= "JOIN players ON players.guildName = guilds.name "
    query+= "WHERE allyCode = " + txt_allyCode
    goutils.log("DBG", "go.load_guild", 'query: '+query)
    db_result = connect_mysql.get_value(query)

    if db_result == None or db_result == "":
        goutils.log("WAR", "go.load_guild", 'Guild ID not found for '+txt_allyCode)
        guild_id = ""
    else:
        guild_id = db_result
        goutils.log("INFO", "go.load_guild", 'Guild ID for '+txt_allyCode+' is '+guild_id)
    json_file = "GUILDS"+os.path.sep+guild_id+".json"

    if client != None:
        client_data = client.get_data('guild', txt_allyCode, 'FRE_FR')
    else:
        goutils.log("WAR", "go.load_guild", 'Cannot connect to API. Using cache data from json')
        if guild_id == "":
            goutils.log("WAR", "go.load_guild", 'Unknown guild for player '+txt_allyCode)
            client_data = None
        elif os.path.isfile(json_file):
            prev_dict_guild = json.load(open(json_file, 'r'))
            client_data = [prev_dict_guild]
        else:
            goutils.log("WAR", "go.load_guild", 'Failed to find cache data '+json_file)
            client_data = None

    if isinstance(client_data, list):
        if len(client_data) > 0:
            if len(client_data) > 1:
                goutils.log('WAR', 'go.load_guild',"client.get_data(\'guild\', "+txt_allyCode+
                        ", 'FRE_FR') has returned a list of size "+
                        str(len(player_data)))            
                            
            dict_guild = client_data[0]
            guildName = dict_guild['name']
            guild_id = dict_guild['id']
            total_players = len(dict_guild['roster'])
            allyCodes_in_API = [int(x['allyCode']) for x in dict_guild['roster']]
            guild_gp = dict_guild["gp"]
            goutils.log("INFO", "go.load_guild", "success retrieving "+guildName+" ("\
                        +str(total_players)+" players, "+str(guild_gp)+" GP) from SWGOH.HELP API")
                        
            # store json file
            json_file = "GUILDS"+os.path.sep+guild_id+".json"
            fjson = open(json_file, 'w')
            fjson.write(json.dumps(dict_guild, sort_keys=True, indent=4))
            fjson.close()
        else:
            goutils.log("ERR", "go.load_guild", "client.get_data('guild', "+txt_allyCode+
                    ", 'FRE_FR') has returned an empty list")
            return 'ERR: cannot fetch guild fo allyCode '+txt_allyCode, None
    else:
        goutils.log ('ERR', "go.load_guild", "client.get_data('guild', "+
                txt_allyCode+", 'FRE_FR') has not returned a list")
        goutils.log ("ERR", "go.load_guild", client_data)
        return 'ERR: cannot fetch guild for allyCode '+txt_allyCode, None

    #Get guild data from DB
    query = "SELECT lastUpdated FROM guilds "\
           +"WHERE name = '"+guildName.replace("'", "''")+"'"
    goutils.log('DBG', 'go.load_guild', query)
    lastUpdated = connect_mysql.get_value(query)
    is_new_guild = (lastUpdated == None)

    query = "SELECT allyCode FROM players "\
           +"WHERE guildName = '"+guildName.replace("'", "''")+"'"
    goutils.log('DBG', 'go.load_guild', query)
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
                    goutils.log('INFO', "go.load_guild", "Guild "+guildName+" already loading ("\
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
                    goutils.log('INFO', "go.load_guild", "Guild "+guildName+" loading "\
                                +"will start after loading of "+str(list_other_guilds_loading_status))
                    time.sleep(30)
                    list_other_guilds_loading_status = parallel_work.get_other_guilds_loading_status(guildName)
                    sys.stdout.flush()

                #Create guild in DB only if the players are loaded
                query = "INSERT IGNORE INTO guilds(name) VALUES('"+guildName.replace("'", "''")+"')"
                goutils.log('DBG', 'go.load_guild', query)
                connect_mysql.simple_execute(query)

                #add player data
                i_player = 0
                for allyCode in list_allyCodes_to_update:
                    i_player += 1
                    goutils.log("INFO", "go.load_guild", "player #"+str(i_player))
                    
                    e, d, t = load_player(str(allyCode), 0, False)
                    parallel_work.set_guild_loading_status(guildName, str(i_player)+"/"+str(total_players))

                parallel_work.set_guild_loading_status(guildName, None)

                #Update dates in DB
                query = "UPDATE guilds "\
                       +"SET id = '"+guild_id+"', "\
                       +"lastUpdated = CURRENT_TIMESTAMP "\
                       +"WHERE name = '"+guildName.replace("'", "''") + "'"
                goutils.log('DBG', 'go.load_guild', query)
                connect_mysql.simple_execute(query)

        else:
            lastUpdated_txt = lastUpdated.strftime("%d/%m/%Y %H:%M:%S")
            goutils.log('INFO', "go.load_guild", "Guild "+guildName+" last update is "+lastUpdated_txt)

    #Update dates in DB
    if cmd_request:
        query = "UPDATE guilds "\
               +"SET lastRequested = CURRENT_TIMESTAMP "\
               +"WHERE name = '"+guildName.replace("'", "''") + "'"
        goutils.log('DBG', 'go.load_guild', query)
        connect_mysql.simple_execute(query)

    #Erase guildName for alyCodes not detected from API
    if len(allyCodes_to_remove) > 0:
        query = "UPDATE players "\
               +"SET guildName = '' "\
               +"WHERE allyCode IN "+str(tuple(allyCodes_to_remove)).replace(",)", ")")
        goutils.log('DBG', 'go.load_guild', query)
        connect_mysql.simple_execute(query)

    return "OK", dict_guild

def get_team_line_from_player(team_name_path, dict_teams, dict_team_gt, gv_mode, player_name):
    line = ''

    #manage team_name in a path for recursing requests
    team_name = team_name_path.split('/')[-1]
    if team_name_path.count(team_name) > 1:
        #recurring loop, stop it
        return 0, False, "", False, []

    dict_team = dict_team_gt[team_name]
    objectifs = dict_team["categories"]
    nb_subobjs = len(objectifs)

    if team_name in dict_teams[player_name]:
        dict_player = dict_teams[player_name][team_name]
    else:
        dict_player = {}
    
    #INIT tableau des resultats
    tab_progress_player = [[] for i in range(nb_subobjs)]
    for i_subobj in range(0, nb_subobjs):
        nb_chars = len(objectifs[i_subobj][2])

        #score, display, nogo, charater_id, weight
        tab_progress_player[i_subobj] = [[0, '.     ', True, '', 1] for i in range(nb_chars)]

    goutils.log("DBG", "go.get_team_line_from_player", "player: "+player_name)
    # Loop on categories within the goals
    for i_subobj in range(0, nb_subobjs):
        dict_char_subobj = objectifs[i_subobj][2]

        for character_id in dict_char_subobj:
            goutils.log("DBG", "go.get_team_line_from_player", "character_id: "+character_id)
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

                player_gp = dict_player[character_id]['gp']

                #Progress
                character_progress = progress / progress_100

                #Display
                character_display = str(player_rarity)
                if player_gear < 13:
                    character_display += '.' + "{:02d}".format(player_gear)                        
                else:
                    character_display += '.R' + str(player_relic)
                character_display += '.' + str(player_nb_zetas)
                        
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
                tab_progress_player[i_subobj][i_character - 1][3] = character_id
                tab_progress_player[i_subobj][i_character - 1][4] = 1

                goutils.log("DBG", "go.get_team_line_from_player", tab_progress_player[i_subobj][i_character - 1])

            else:
                if gv_mode:
                    character_id_team = character_id + '-GV'
                    if character_id_team in dict_teams[player_name]:
                        score, unlocked, character_display, nogo, list_char = get_team_line_from_player(team_name_path+'/'+character_id_team,
                            dict_teams, dict_team_gt, gv_mode, player_name)

                        #Unlocking a chatacter only gives the rarity so by default 50%
                        score = score / 200.0
                        #weight = len(list_char)
                        weight = 1
                        character_display = "\N{CROSS MARK} "+\
                                            character_name + \
                                            " n'est pas débloqué - "+str(int(score*100))+"%"
                    else:
                        score = 0
                        character_display = "\N{CROSS MARK} "+\
                                            character_name + \
                                            " n'est pas débloqué - 0%"
                        nogo = True
                        weight = 1
                else:
                    score = 0
                    character_display = ""
                    nogo = True
                    weight = 1

                tab_progress_player[i_subobj][i_character - 1][0] = score
                tab_progress_player[i_subobj][i_character - 1][1] = character_display
                tab_progress_player[i_subobj][i_character - 1][2] = nogo
                tab_progress_player[i_subobj][i_character - 1][3] = character_id
                tab_progress_player[i_subobj][i_character - 1][4] = weight

                goutils.log("DBG", "go.get_team_line_from_player", tab_progress_player[i_subobj][i_character - 1])


    #calcul du score global
    score = 0
    score100 = 0
    score_nogo = False
    list_char_id = []
    sorted_tab_progress = [[]] * len(tab_progress_player)
    for i_subobj in range(0, nb_subobjs):
        #Sort best characters first
        min_perso = objectifs[i_subobj][1] #Minimum characters to be ready for this sub objective
        sorted_tab_progress[i_subobj] = sorted(tab_progress_player[i_subobj], key=lambda x: ((-x[0] * (not x[2])), -x[0]))

        #remove already used characters
        for char in sorted_tab_progress[i_subobj]:
            if char[3] in list_char_id:
                sorted_tab_progress[i_subobj].remove(char)

        #Compute scores on the best characters
        top_tab_progress = sorted_tab_progress[i_subobj][:min_perso]
        top_scores_weighted = [x[0] * (not x[2]) * x[4] for x in top_tab_progress]
        sum_scores = sum(top_scores_weighted)
        top_weights = [x[4] for x in top_tab_progress]
        sum_weights = sum(top_weights)

        #Remove used characters (only if part of the best as used to compute the score)
        top_chars = [x[3] for x in top_tab_progress]
        for x in tab_progress_player[i_subobj]:
            char_id = x[3]
            if char_id in top_chars:
                list_char_id.append(char_id)

        score += sum_scores
        score100 += sum_weights
        
        if 0.0 in top_scores_weighted:
            score_nogo = True

        #Display the header of team requirements, for this category
        # And filter already used characters from the available ones
        subobj_size = len(sorted_tab_progress[i_subobj]) #Amount of chars in this sub-objective
        tab_progress_player_subobj = []
        for i_character in range(0, subobj_size):
            subobj_char_display = sorted_tab_progress[i_subobj][i_character][1]
            if i_character >= min_perso:
                line += "-- " + subobj_char_display + "\n"
            else:
                line += subobj_char_display + "\n"

    #pourcentage sur la moyenne
    score = score / score100 * 100

    goutils.log("DBG", "go.get_team_line_from_player", "list char_id = " + str(list_char_id))
        
    unlocked = False
    if gv_mode:
        # in gv_mode, we check if the target character is fully unlocked
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
    if score_nogo:
        line += "\N{UP-POINTING RED TRIANGLE}"
    elif score >= SCORE_GREEN:
        line += "\N{WHITE HEAVY CHECK MARK}"
    elif score >= SCORE_ALMOST_GREEN:
        line += "\N{WHITE RIGHT POINTING BACKHAND INDEX}"
    elif score >= SCORE_AMBER:
        line += "\N{CONFUSED FACE}"
    else:
        line += "\N{UP-POINTING RED TRIANGLE}"

    # Display the IG name only, as @mentions only pollute discord
    if not gv_mode:
        line += '|' + player_name + '\n'

    return score, unlocked, line, score_nogo, list_char_id


def get_team_header(team_name, objectifs):
    entete = ''

    nb_levels = len(objectifs)

    #Affichage des prérequis
    entete += '**Team: ' + team_name + '**\n'
    for i_level in range(0, nb_levels):
        #print('DBG: i_level='+str(i_level))
        #print('DBG: obj='+str(objectifs[i_level]))
        nb_sub_obj = len(objectifs[i_level][2])
        #print('DBG: nb_sub_obj='+str(nb_sub_obj))
        obj_target_count = objectifs[i_level][1]
        if obj_target_count == nb_sub_obj:
            obj_target_txt = "tous"
        else:
            obj_target_txt = str(obj_target_count)+" parmi "+str(nb_sub_obj)

        entete += '**' + objectifs[i_level][0] + ' ('+obj_target_txt+')**\n'
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
                    
                    perso_name = objectifs[i_level][2][perso][7]
                    entete += "- " + perso_name + ' (' + perso_min_display + ' à ' + \
                            perso_reco_display + ', zetas=' + str(req_zeta_names) + ')\n'

    return entete

def get_team_progress(list_team_names, txt_allyCode, compute_guild, gv_mode):
    goutils.log2("DBG", "START")
                        
    ret_get_team_progress = {}

    #Recuperation des dernieres donnees sur gdrive+
    liste_team_gt, dict_team_gt = connect_gsheets.load_config_teams(False)
    
    if not compute_guild:
        #only one player, potentially several teams
        
        #Load or update data for the player
        e, d, t = load_player(txt_allyCode, 0, False)
        if e != 0:
            #error wile loading guild data
            return "", 'ERR: joueur non trouvé pour code allié ' + txt_allyCode

        collection_name = d["name"]
            
    else:
        #Get data for the guild and associated players
        ret, guild = load_guild(txt_allyCode, True, True)
        if ret != 'OK':
            goutils.log("WAR", "go.get_team_progress", "cannot get guild data from SWGOH.HELP API. Using previous data.")
        collection_name = guild["name"]

    if not ('all' in list_team_names) and gv_mode:
        #Need to transform the name of the team into a character
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_team_names)
        if txt != "":
            return "", "ERR: impossible de reconnaître ce(s) nom(s) >> "+txt
        list_team_names = [x+"-GV" for x in list_character_ids]

    #Get player data
    goutils.log("INFO", "go.get_team_progress", "Get player data from DB...")
    query = "SELECT players.name, "\
           +"guild_teams.name, "\
           +"guild_team_roster.unit_id, "\
           +"rarity, "\
           +"gear, "\
           +"relic_currentTier, "\
           +"gp, "\
           +"stat5 as speed "\
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
    if gv_mode == False:
        query += "AND NOT guild_teams.name LIKE '%-GV'\n"
    else:
        query += "AND guild_teams.name LIKE '%-GV'\n"
       
    query += "GROUP BY players.name, guild_teams.name, guild_team_roster.unit_id, \
            rarity, gear, relic_currentTier, gp \
            ORDER BY players.name, guild_teams.name"
    goutils.log("DBG", "go.get_team_progress", query)
    
    # print(query)
    player_data = connect_mysql.get_table(query)
    goutils.log("DBG", "go.get_team_progress", player_data)
    
    if not gv_mode:
        # Need the zetas to compute the progress of a regular team
        goutils.log("INFO", "go.get_team_progress", "Get zeta data from DB...")
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
        query += "AND NOT guild_teams.name LIKE '%-GV'\n"
           
        query += "ORDER BY roster.allyCode, guild_teams.name, guild_subteams.id, guild_team_roster.id"
        goutils.log("DBG", "go.get_team_progress", query)
        
        player_zeta_data = connect_mysql.get_table(query)
        if player_zeta_data == None:
            player_zeta_data = []
        
        gv_characters_unlocked = []
    
    else:
        #In gv_mode, there is no requirement for zetas
        player_zeta_data = []
        
        #There is a need to check if the target character is locked or unlocked
        goutils.log("INFO", "go.get_team_progress", "Get GV characters data from DB...")
        query = "SELECT players.name, defId, rarity \
                FROM roster \
                JOIN players ON players.allyCode = roster.allyCode \n"
        if not compute_guild:
            query += "WHERE roster.allyCode = '"+txt_allyCode+"'\n"
        else:
            query += "WHERE players.guildName = \
                    (SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"')\n"
        query += "AND defId IN (SELECT SUBSTRING_INDEX(name, '-GV', 1) FROM guild_teams WHERE name LIKE '%-GV')"
        goutils.log("DBG", "go.get_team_progress", query)
        
        #print(query)
        gv_characters_unlocked = connect_mysql.get_table(query)        
        goutils.log("DBG", "go.get_team_progress", gv_characters_unlocked)
        
    if player_data != None:
        goutils.log("INFO", "go.get_team_progress", "Recreate dict_teams...")
        dict_teams = goutils.create_dict_teams(player_data, player_zeta_data, gv_characters_unlocked)
        goutils.log("INFO", "go.get_team_progress", "Recreation of dict_teams is OK")
    else:
        query = "SELECT name FROM players WHERE allyCode = "+txt_allyCode
        goutils.log("DBG", "go.get_team_progress", query)
        player_name = connect_mysql.get_value(query)
        dict_teams = {player_name: {}}
        goutils.log("WAR", "go.get_team_progress", "no data recovered for allyCode="+txt_allyCode+" and teams="+str(list_team_names))
    
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

            if not gv_mode:
                if len(list_team_names) == 1:
                    entete = get_team_header(team_name, objectifs)
                else:
                    entete = "Team " + team_name + "\n"
                ret_team.append([999999, True, entete, False, '', []])

            tab_lines = []
            count_green = 0
            count_almost_green = 0
            count_amber = 0
            count_red = 0
            count_not_enough = 0
            for player_name in dict_teams:
                #resultats par joueur
                score, unlocked, line, nogo, list_char = get_team_line_from_player(team_name,
                    dict_teams, dict_team_gt, gv_mode, player_name)
                tab_lines.append([score, unlocked, line, nogo, player_name, list_char])

                if score >= SCORE_GREEN and not nogo:
                    count_green += 1
                elif score >= SCORE_ALMOST_GREEN and not nogo:
                    count_almost_green += 1
                elif score >= SCORE_AMBER and not nogo:
                    count_amber += 1
                elif score >= SCORE_RED and not nogo:
                    count_red += 1
                else:
                    count_not_enough += 1

            #Tri des équipes par nogo=False en premier, puis score décroissant
            for score, unlocked, txt, nogo, name, list_char in sorted(tab_lines,
                                           key=lambda x: (x[3], -x[0])):
                ret_team.append([score, unlocked, txt, nogo, name, list_char])

            ret_get_team_progress[team_name] = ret_team, [count_green, count_almost_green,
                                                          count_amber, count_red, count_not_enough]

    return collection_name, ret_get_team_progress

def print_vtg(list_team_names, txt_allyCode):

    guild_name, ret_get_team_progress = get_team_progress(list_team_names, txt_allyCode, 
                                              True, False)
    if type(ret_get_team_progress) == str:
        goutils.log("ERR", "go.print_vtg", "get_team_progress has returned an error: "+ret_print_vtx)
        return 1,  ret_get_team_progress
    else:
        ret_print_vtx = "Vérification des Teams de la Guilde **"+guild_name+"**\n\n"
        for team in ret_get_team_progress:
            ret_team = ret_get_team_progress[team]
            if type(ret_team) == str:
                #error
                ret_print_vtx += ret_team + "\n"
            else:
                total_green = ret_team[1][0]
                total_almost_green = ret_team[1][1]
                total_amber = ret_team[1][2]
                total_not_enough = ret_team[1][4]
                for [score, unlocked, txt, nogo, name, list_char] in ret_team[0]:
                    if score == 999999:
                        #Header of the team
                        ret_print_vtx += txt
                        if len(list_team_names)==1 and list_team_names[0]!="all":
                            ret_print_vtx += "\n"
                    else:
                        line_print_vtx = ""
                        if score >= SCORE_GREEN and not nogo:
                            line_print_vtx += "\N{WHITE HEAVY CHECK MARK}"
                        elif score >= SCORE_ALMOST_GREEN and not nogo:
                            line_print_vtx += "\N{WHITE RIGHT POINTING BACKHAND INDEX}"
                        elif score >= SCORE_AMBER and not nogo:
                            line_print_vtx += "\N{CONFUSED FACE}"
                        #elif score >= SCORE_RED:
                        else:
                            line_print_vtx += "\N{UP-POINTING RED TRIANGLE}"
                            total_not_enough -= 1

                        #if score >= SCORE_RED:
                        line_print_vtx += " " + name + ": " + str(round(score, 1)) + "%\n"

                        if len(list_team_names)==1 and list_team_names[0]!="all":
                            ret_print_vtx += line_print_vtx

                if total_not_enough > 0:
                    if len(list_team_names)==1 and list_team_names[0]!="all":
                        ret_print_vtx += "... et " + str(total_not_enough) + " joueurs sous 50%\n"

                if len(list_team_names)==1 and list_team_names[0]!="all":
                    ret_print_vtx += "\n"
                ret_print_vtx += "**Total**: " + str(total_green) + " \N{WHITE HEAVY CHECK MARK}" \
                               + " + " + str(total_almost_green) + " \N{WHITE RIGHT POINTING BACKHAND INDEX}" \
                               + " + " + str(total_amber) + " \N{CONFUSED FACE}"

            ret_print_vtx += "\n\n"
                
    return 0, ret_print_vtx

def print_vtj(list_team_names, txt_allyCode):
    player_name, ret_get_team_progress = get_team_progress(list_team_names, txt_allyCode, 
                                              False, False)
    if type(ret_get_team_progress) == str:
        goutils.log("ERR", "go.print_vtj", "get_team_progress has returned an error: "+ret_get_team_progress)
        return 1,  ret_get_team_progress, None
    else:
        ret_print_vtx = "Vérification des Teams du Joueur **"+player_name+"**\n\n"
        if len(ret_get_team_progress) > 0:
            values_view = ret_get_team_progress.values()
            value_iterator = iter(values_view)
            first_team = next(value_iterator)
            if type(first_team) == str:
                goutils.log("ERR", "go.print_vtj", "get_team_progress has returned an error: "+first_team)
                return 1,  first_team, None
            player_name = first_team[0][1][4]
            ret_print_vtx += "**Joueur : " + player_name + "**\n"

        for team in ret_get_team_progress:
            ret_team = ret_get_team_progress[team]

            #If onnly one team, display the detais
            for [score, unlocked, txt, nogo, name, list_char] in ret_team[0]:
                if score == 999999:
                    #Header of the team
                    if len(ret_get_team_progress) == 1:
                        ret_print_vtx += txt + "\n"
                        team = "Score"
                else:
                    if score >= SCORE_GREEN and not nogo:
                        ret_print_vtx += "\N{WHITE HEAVY CHECK MARK}"
                    elif score >= SCORE_ALMOST_GREEN and not nogo:
                        ret_print_vtx += "\N{WHITE RIGHT POINTING BACKHAND INDEX}"
                    elif score >= SCORE_AMBER and not nogo:
                        ret_print_vtx += "\N{CONFUSED FACE}"
                    else:
                        ret_print_vtx += "\N{UP-POINTING RED TRIANGLE}"
                    ret_print_vtx += " " + team + ": " + str(round(score, 1)) + "%\n"

                    list_char_allycodes = [[list_char, txt_allyCode, ""]]
                    e, t, images = get_character_image(list_char_allycodes, True, True)

    #In case of several teams, don't display images
    if len(ret_get_team_progress) > 1:
        images = None

    return 0, ret_print_vtx, images

def print_gvj(list_team_names, txt_allyCode):
    ret_print_gvj = ""
    
    player_name, ret_get_team_progress = get_team_progress(list_team_names, txt_allyCode, False, True)
    if type(ret_get_team_progress) == str:
        return 1, ret_get_team_progress
    
    list_lines = []
    if len(ret_get_team_progress) == 1:
        #one team only, one player
        team = list(ret_get_team_progress.keys())[0]
        ret_team = ret_get_team_progress[team]
        if type(ret_team) == str:
            #error
            ret_print_gvj += ret_team
        else:
            for [player_score, unlocked, player_txt, player_nogo, player_name, list_char] in ret_team[0]:
                ret_print_gvj += "Progrès dans le Guide de Voyage pour "+player_name+" - "+team[:-3]+"\n"
                ret_print_gvj += "(Les persos avec -- ne sont pas pris en compte pour le score)\n"
                ret_print_gvj += player_txt + "> Global: "+ str(int(player_score))+"%"

    else:
        #Several tams
        player_name = ''
        for team in ret_get_team_progress:
            ret_team = ret_get_team_progress[team]
            if type(ret_team) == str:
                #error
                ret_print_gvj += ret_team
            else:
                for [player_score, player_unlocked, player_txt, player_nogo, player_name, list_char] in ret_team[0]:
                    new_line = team[:-3] + " - "+ player_name + ": " + \
                                    str(int(player_score)) + "%\n"
                    list_lines.append([player_score, new_line, player_unlocked])
                                            
        #Teams are sorted with the best progress on top
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

    return 0, ret_print_gvj
                        
def print_gvg(list_team_names, txt_allyCode):
    ret_print_gvg = ""
    
    guild_name, ret_get_team_progress = get_team_progress(list_team_names, txt_allyCode, True, True)
    
    if type(ret_get_team_progress) == str:
        return 1, ret_get_team_progress

    list_lines = []
    for team in ret_get_team_progress:
        ret_team = ret_get_team_progress[team]
        if type(ret_team) == str:
            #error
            ret_print_gvg += ret_team + "\n"
        else:
            for [player_score, player_unlocked, player_txt, player_nogo, player_name, list_char] in ret_team[0]:
                if not player_unlocked:
                    new_line = team[:-3] + " - "+ player_name + ": " + \
                                    str(int(player_score)) + "%\n"
                    list_lines.append([player_score, new_line, player_unlocked])
                    
    list_lines = sorted(list_lines, key=lambda x: -x[0])
    ret_print_gvg += "Progrès dans le Guide de Voyage pour la guilde (top "+str(MAX_GVG_LINES)+")\n"
    ret_print_gvg += "(seuls les joueurs qui n'ont pas le perso au max sont listés)\n"
    if len(list_lines) > 0:
        for [score, txt, unlocked] in list_lines[:MAX_GVG_LINES]:
            if score > 95:
                ret_print_gvg += "\N{WHITE RIGHT POINTING BACKHAND INDEX}"
            elif score > 80:
                ret_print_gvg += "\N{CONFUSED FACE}"
            else:
                ret_print_gvg += "\N{UP-POINTING RED TRIANGLE}"
            ret_print_gvg += txt
        
        not_displayed_count = max(0, len(list_lines) - MAX_GVG_LINES)
        if not_displayed_count > 0:
            ret_print_gvg += "... et encore "+str(not_displayed_count)+" lignes mais ça fait trop à afficher"
    else:
        ret_print_gvg += "... sauf que tout le monde l'a \N{SMILING FACE WITH HEART-SHAPED EYES}"
        
    return 0, ret_print_gvg
                       
def assign_gt(allyCode):
    ret_assign_gt = ''

    dict_players = connect_gsheets.load_config_players(False)[0]

    liste_territoires = connect_gsheets.load_config_gt()
        # index=priorité-1, value=[territoire, [[team, nombre, score]...]]
    liste_team_names = []
    for territoire in liste_territoires:
        for team in territoire[1]:
            liste_team_names.append(team[0])
    liste_team_names = [x for x in set(liste_team_names)]
    #print(liste_team_names)

    #Calcule des meilleurs joueurs pour chaque team
    dict_teams = guild_name, get_team_progress(liste_team_names, allyCode, True, True)
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
                                if nom_joueur in dict_players:
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
    guild_name, dict_needed_teams = get_team_progress(list_needed_teams, txt_allyCode, True, True)
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

def print_character_stats(characters, options, txt_allyCode, compute_guild):
    ret_print_character_stats = ''

    list_stats_for_display=[['speed', "Vit"],
                            ['physical damages', "DegPhy"],
                            ['special damages', "DegSpé"],
                            ['health', " Santé"],
                            ['protection', "Protec"],
                            ['potency', "Pouvoir"],
                            ['tenacity', "Ténacité"]]
    
    #manage sorting options
    sort_option_id=0 # sort by name
    if len(options) == 1:
        sort_option_alias = options[0][1:].lower()
        closest_names = difflib.get_close_matches(sort_option_alias,
                                                  dict_stat_names.keys(),
                                                  1)
        if len(closest_names) < 1:
            return "ERR: "+options[0]+" ne fait pas partie des stats connues "+\
                    str(list(dict_stat_names.keys()))
        sort_option_name = closest_names[0]
        sort_option_id = dict_stat_names[sort_option_name][0]

        
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
        e, dict_player, t = load_player(txt_allyCode, 0, False)
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
            list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(characters)
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

        
        ret_print_character_stats += "Statistiques pour "+player_name
        if sort_option_id == 0:
            ret_print_character_stats += " (tri par nom)\n"
        else:
            sort_option_full_name = dict_stat_names[sort_option_name][2]
            ret_print_character_stats += " (tri par "+sort_option_full_name+")\n"


    elif len(characters) == 1 and characters[0] != "all" and not characters[0].startswith("tag:"):
        #Compute stats at guild level, only one character
        
        #Get data for the guild and associated players
        ret, guild = load_guild(txt_allyCode, True, True)
        if ret != 'OK':
            return "ERR: cannot get guild data from SWGOH.HELP API"
                            
        #Get character_id
        character_alias = characters[0]
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([character_alias])
        if txt != '':
            return 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt
                                    
        character_id = list_character_ids[0]
        db_stat_data_char = []
        goutils.log("INFO", "go.print_character_stats", "Get guild_data from DB...")
        query = "SELECT players.name, defId, "\
               +"roster.combatType, rarity, gear, relic_currentTier, "\
               +"stat1, "\
               +"stat5, "\
               +"stat6, "\
               +"stat7, "\
               +"stat17, "\
               +"stat18, "\
               +"stat28 "\
               +"FROM roster "\
               +"JOIN players ON players.allyCode = roster.allyCode "\
               +"WHERE players.guildName = (SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"') "\
               +"AND defId = '"+character_id+"' "\
               +"ORDER BY players.name, defId"

        db_stat_data = connect_mysql.get_table(query)
        if db_stat_data == None:
            return "ERR: aucune donnée trouvée"

        db_stat_data_mods = []
        list_character_ids=[character_id]
        list_player_names=set([x[0] for x in db_stat_data])
        character_name = dict_id_name[character_alias][0][1]
        
        ret_print_character_stats += "Statistiques pour "+character_name
        if sort_option_id == 0:
            ret_print_character_stats += " (tri par nom)\n"
        else:
            sort_option_full_name = dict_stat_names[sort_option_name][2]
            ret_print_character_stats += " (tri par "+sort_option_full_name+")\n"
    
        # Generate dict from DB data
        dict_stats = goutils.create_dict_stats(db_stat_data_char, db_stat_data, db_stat_data_mods)
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
                stat_type = "final"
                if stat_type in dict_player[character_id]["stats"]:
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
            list_print_stats = sorted(list_print_stats, key=lambda x: x[0].lower())
            
        # Sort by specified stat
        if sort_option_id != 0:
            stat_txt = str(sort_option_id)
            list_print_stats = sorted(list_print_stats,
                key=lambda x: -x[2][stat_txt] if stat_txt in x[2] else 0)
        
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
                stat_id = str(dict_stat_names[stat[0]][0])
                stat_percent = dict_stat_names[stat[0]][1]
                if stat_id in print_stat_row[2]:
                    stat_value = print_stat_row[2][stat_id]
                else:
                    stat_value = 0
                if stat_percent:
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
    ret, dict_guild = load_guild(txt_allyCode, False, True)
    if ret != 'OK':
        return 1, "ERR: cannot get guild data from SWGOH.HELP API", None

    guild_stats=[] #Serie of all players
    for player in dict_guild['roster']:
        gp = (player['gpChar'] + player['gpShip']) / 1000000
        guild_stats.append(gp)
    guild_name = dict_guild["name"]

    graph_title = "GP stats " + guild_name + " ("+str(len(guild_stats))+" joueurs)"

    #compute ASCII graphs
    image = get_distribution_graph(guild_stats, 20, graph_title, None)
    logo_img= portraits.get_guild_logo(dict_guild, (80, 80))
    image.paste(logo_img, (10,10), logo_img)
    
    return 0, "", image

def get_tb_alerts(force_latest):
    territory_scores, active_round = connect_warstats.parse_tb_guild_scores(4090, force_latest)

    if active_round != "":
        [territory_stars, daily_targets, margin] = connect_gsheets.get_tb_triggers(False)

        #print(territory_scores)
        tb_trigger_messages=[]
        tb_name = list(territory_scores.keys())[0][0:3]
        round_number = int(active_round[-1])
        current_targets = daily_targets[tb_name][round_number-1]

        for pos, name in [[0, "top"], [1, "mid"], [2, "bot"]]:
            current_target = current_targets[pos]
            if current_target == "-":
                continue
            current_target_phase = current_target.split('-')[0]
            current_target_stars = current_target.split('-')[1]
            full_phase_name = tb_name+"-"+current_target_phase+"-"+name
            if not full_phase_name in territory_scores:
                tb_trigger_messages.append("ERREUR: phase "+current_target_top_phase+" non atteinte en "+name)
            else:
                current_score = territory_scores[full_phase_name]
                star1_score = territory_stars[full_phase_name][0]
                star2_score = territory_stars[full_phase_name][1]
                star3_score = territory_stars[full_phase_name][2]
                if current_target_stars == "0":
                    if current_score >= star1_score:
                        tb_trigger_messages.append(":x: 1ère étoile atteinte en "+name+" alors qu'il ne fallait pas !")
                    elif current_score >= (star1_score-margin):
                        delta_score_M = round((star1_score-current_score)/1000000, 1)
                        tb_trigger_messages.append(":warning: la 1ère étoile se rapproche en "+name+" et il ne faut pas l'atteindre (il reste "+str(delta_score_M)+"M)")
                elif current_target_stars == "1":
                    if current_score >= star3_score:
                        tb_trigger_messages.append(":heart_eyes: 3e étoile atteinte en "+name+" alors qu'on en visait une seule !")
                    elif current_score >= star2_score:
                        tb_trigger_messages.append(":heart_eyes: 2e étoile atteinte en "+name+" alors qu'on en visait une seule !")
                    elif current_score >= star1_score:
                        tb_trigger_messages.append(":white_check_mark: 1ère étoile atteinte en "+name+", objectif atteint")
                    elif current_score >= (star1_score-margin):
                        delta_score_M = round((star1_score-current_score)/1000000, 1)
                        tb_trigger_messages.append(":point_right: la 1ère étoile se rapproche en "+name+" (il reste "+str(delta_score_M)+"M)")
    
                elif current_target_stars == "2":
                    if current_score >= star3_score:
                        tb_trigger_messages.append(":heart_eyes: 3e étoile atteinte en "+name+" alors qu'on en visait seulement deux !")
                    elif current_score >= star2_score:
                        tb_trigger_messages.append(":white_check_mark: 2e étoile atteinte en "+name+", objectif atteint")
                    elif current_score >= (star2_score-margin):
                        delta_score_M = round((star2_score-current_score)/1000000, 1)
                        tb_trigger_messages.append(":point_right: la 2e étoile se rapproche en "+name+" (il reste "+str(delta_score_M)+"M)")
                    elif current_score >= star1_score:
                        tb_trigger_messages.append(":thumbsup: 1ère étoile atteinte en "+name+", en route vers la 2e")

                elif current_target_stars == "3":
                    if current_score >= star3_score:
                        tb_trigger_messages.append(":white_check_mark: 3e étoile atteinte en "+name+", objectif atteint")
                    elif current_score >= (star3_score-margin):
                        delta_score_M = round((star3_score-current_score)/1000000, 1)
                        tb_trigger_messages.append(":point_right: la 3e étoile se rapproche en "+name+" (il reste "+str(delta_score_M)+"M)")
                    elif current_score >= star2_score:
                        tb_trigger_messages.append(":thumbsup: 2e étoile atteinte en "+name+", en route vers la 3e")
                    elif current_score >= star1_score:
                        tb_trigger_messages.append(":thumbsup: 1ère étoile atteinte en "+name+", en route vers la 3e")
    else:
        tb_trigger_messages = []

    return tb_trigger_messages
    
#################################
# Function: get_character_image
# IN: list_characters_allyCode: [[[id1, id2, ...], allyCode, tw territory], ...]
# IN: is_ID: True if list_character_alyCode contains chartacter IDs (False if names)
# IN: refresh_player: False to revent refreshing player via API
# return: err_code, err_txt, image
#################################
def get_character_image(list_characters_allyCode, is_ID, refresh_player):
    err_code = 0
    err_txt = ''

    #Get data for all players
    #print(list_characters_allyCode)
    list_allyCodes = list(set([x[1] for x in list_characters_allyCode]))
    
    #transform aliases into IDs
    if not is_ID:
        list_alias = [j for i in [x[0] for x in list_characters_allyCode] for j in i]
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_alias)
        if txt != '':
            err_txt += 'WAR: impossible de reconnaître ce(s) nom(s) >> '+txt+"\n"

    list_ids_dictplayer = []
    for [characters, txt_allyCode, tw_terr] in list_characters_allyCode:
        e, dict_player, t = load_player(txt_allyCode, -int(not(refresh_player)), False)
        if e != 0:
            #error wile loading guild data
            goutils.log("WAR", "go.get_character_image", "joueur non trouvé pour code allié " + txt_allyCode)
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
        
        if len(list_ids) == 0:
            err_txt += 'WAR: aucun personnage valide pour '+txt_allyCode + "\n"
        else:
            list_ids_dictplayer.append([list_ids, dict_player, tw_terr])

    if len(list_ids_dictplayer) == 0:
        return 1, err_txt, None

    #Return a list of images
    list_images = []
    for [ids, dict_player, tw_terr] in list_ids_dictplayer:
        image = portraits.get_image_from_team(ids, dict_player, tw_terr)
        list_images.append(image)
    
    return err_code, err_txt, list_images

#################################
# Function: get_tw_battle_images
# return: err_code, err_txt, list of images
#################################
def get_tw_battle_image(list_char_attack, allyCode_attack, \
                        character_defense):
    err_code = 0
    err_txt = ''

    #Get full character names for attack
    list_id_attack, dict_id_name, txt = goutils.get_characters_from_alias(list_char_attack)
    if txt != '':
        err_txt += 'WAR: impossible de reconnaître ce(s) nom(s) >> '+txt+"\n"

    #Get full character name for defense
    list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([character_defense])
    if txt != '':
        err_txt += 'WAR: impossible de reconnaître ce(s) nom(s) >> '+txt+"\n"
    char_def_id = list_character_ids[0]

    #Get full character names for defense squads

    query = "SELECT warstats_id FROM guilds "
    query+= "JOIN players ON guilds.name = players.guildName "
    query+= "where allyCode = "+allyCode_attack
    warstats_id = connect_mysql.get_value(query)

    if warstats_id == None or warstats_id == 0:
        return 1, "ERR: ID de guilde warstats non défini\n", None

    list_opponent_squads = connect_warstats.parse_tw_teams(warstats_id)
    if len(list_opponent_squads) == 0:
        goutils.log("ERR", "go.get_tw_battle_image", "aucune phase d'attaque en cours en GT")
        err_txt += "ERR: aucune phase d'attaque en cours en GT\n"
        return 1, err_txt, None

    list_opponent_char_alias = list(set([j for i in [x[2] for x in list_opponent_squads] for j in i]))
    list_opponent_char_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_opponent_char_alias)
    if txt != '':
        err_txt += 'WAR: impossible de reconnaître ce(s) nom(s) >> '+txt+"\n"

    list_opp_squad_ids = []
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
    results = connect_mysql.get_table("SELECT name, allyCode FROM players")
    list_names = [x[0] for x in results]

    for opp_squad in list_opp_squads_with_char:
        player_name = opp_squad[1]

        closest_names=difflib.get_close_matches(player_name, list_names, 1)
        #print(closest_names)
        if len(closest_names)<1:
            err_txt += 'ERR: '+player_name+' ne fait pas partie des joueurs connus\n'
            goutils.log("ERR", "go.get_tw_battle_image", player_name+' ne fait pas partie des joueurs connus')
            opp_squad[1]=''
        else:
            goutils.log("INFO", "go.get_tw_battle_image", "cmd launched with name that looks like "+closest_names[0])
            for r in results:
                if r[0] == closest_names[0]:
                    opp_squad[1] = str(r[1])

    #print(list_opp_squads_with_char)
    list_char_allycodes = []
    list_char_allycodes.append([list_id_attack, allyCode_attack, ''])
    for opp_squad in list_opp_squads_with_char:
        if not opp_squad[1] == '':
            list_char_allycodes.append([opp_squad[2], opp_squad[1], opp_squad[0]])

    #print(list_char_allycodes)
    e, t, images = get_character_image(list_char_allycodes, True, False)
    err_txt += t
    if e != 0:
        return 1, err_txt, None

    return 0, err_txt, images

def get_stat_graph(txt_allyCode, character_alias, stat_name):
    err_txt = ""

    e, d, t = load_player(txt_allyCode, 0, False)
    if e != 0:
        return 1, "ERR: cannot get player data from SWGOH.HELP API", None
        
    #Get character_id
    list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([character_alias])
    if txt != '':
        return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt, None
            
    character_id = list_character_ids[0]
    character_name = dict_id_name[character_alias][0][1]

    #Get statistic id
    closest_names=difflib.get_close_matches(stat_name.lower(), dict_stat_names.keys(), 1)
    if len(closest_names)<1:
        return 1, 'ERR: '+stat_name+' ne fait pas partie des stats connues '+str(list(dict_stat_names.keys())), None

    goutils.log("INFO", "go.get_stat_graph", "cmd launched with stat name that looks like "+closest_names[0])
    stat_name = closest_names[0]
    stat_id = dict_stat_names[stat_name][0]
    stat_isPercent = dict_stat_names[stat_name][1]
    stat_frName = dict_stat_names[stat_name][2]
    stat_string = "stat"+str(stat_id)

    #Get data from DB
    db_stat_data_char = []
    goutils.log("INFO", "go.get_stat_char", "Get player data from DB...")
    query = "SELECT allyCode, gear,"\
           +stat_string+","\
           +"CASE WHEN allyCode="+txt_allyCode+" THEN 1 ELSE 0 END "\
           +"from roster "\
           +"where defId = '"+character_id+"' "\
           +"AND not "+stat_string+"=0 "\
           +"AND (gear = 13 or allyCode = "+txt_allyCode+")"
    goutils.log("DBG", "go.get_stat_graph", query)
    db_data = connect_mysql.get_table(query)

    if stat_isPercent:
        stat_divider = 1000000
    else:
        stat_divider = 100000000

    stat_g13_values = [x[2]/stat_divider for x in db_data if x[1]==13]
    player_values = [x[2]/stat_divider for x in db_data if x[3]==1]
    if len(player_values) > 0:
        if stat_isPercent:
            player_value = int(100*player_values[0])/100
        else:
            player_value = int(player_values[0])
    else:
        goutils.log("WAR", "go.get_stat_graph", "Character "+character_alias+" is locked for "+txt_allyCode)
        err_txt +="WAR: Le perso "+character_alias+" n'est pas débloqué pour "+txt_allyCode
        player_value = None

    title = stat_frName + " de " + character_name + " (" + str(player_value) + ")\n"
    title+= "comparée aux " + str(len(stat_g13_values)) + " " + character_name + " relic connus"
    image = get_distribution_graph(stat_g13_values, 50, title, player_value)
    
    return 0, err_txt, image

###############################
def print_lox(txt_allyCode, compute_guild):
    if compute_guild:
        ret, guild = load_guild(txt_allyCode, True, True)
        if ret != 'OK':
            return 1, 'ERR: guilde non trouvée pour code allié ' + txt_allyCode, []
    else:
        e, d, t = load_player(txt_allyCode, 0, False)
        if e != 0:
            return 1, 'ERR: joueur non trouvé pour code allié ' + txt_allyCode, []

    query = "select players.name, defId, roster_skills.name, omicron_type from roster \n"
    query+= "join roster_skills on roster_id = roster.id \n"
    query+= "join players on players.allyCode=roster.allyCode \n"
    query+= "where (roster_skills.omicron_tier>0 and roster_skills.level>=roster_skills.omicron_tier) \n"
    if compute_guild:
        query+= "and guildName=(select guildName from players where allyCode="+txt_allyCode+") \n"
    else:
        query+= "and players.allyCode="+txt_allyCode+" \n"
    query+= "order by omicron_type, defId, players.name"
    goutils.log2("DBG", query)

    db_lines = connect_mysql.text_query(query)
    return 0, "", db_lines

###############################
def print_erx(allyCode_txt, days, compute_guild):
    dict_unitsList = data.get("unitsList_dict.json")
    dict_categoryList = data.get("categoryList_dict.json")

    #Recuperation des dernieres donnees sur gdrive
    liste_teams, dict_teams = connect_gsheets.load_config_teams(False)

    if not compute_guild:
        query = "SELECT guildName, name, defId, timestamp FROM roster_evolutions " \
              + "JOIN players ON players.allyCode = roster_evolutions.allyCode " \
              + "WHERE players.allyCode = " + allyCode_txt + " " \
              + "AND timestampdiff(DAY, timestamp, CURRENT_TIMESTAMP)<=" + str(days) + " " \
              + "ORDER BY timestamp DESC"
    else:
        query = "SELECT guildName, name, defId, timestamp FROM roster_evolutions " \
              + "JOIN players ON players.allyCode = roster_evolutions.allyCode " \
              + "WHERE players.allyCode IN (SELECT allyCode FROM players WHERE guildName = (SELECT guildName FROM players WHERE allyCode="+allyCode_txt+")) "\
              + "AND timestampdiff(DAY, timestamp, CURRENT_TIMESTAMP)<=" + str(days) + " " \
              + "ORDER BY timestamp DESC"

    goutils.log2("DBG", query)
    db_data_evo = connect_mysql.get_table(query)

    if not compute_guild:
        query = "SELECT name, defId FROM roster " \
              + "JOIN players ON players.allyCode = roster.allyCode " \
              + "WHERE players.allyCode = " + allyCode_txt + " " \
              + "AND defId IN (SELECT LEFT(name, LENGTH(name) - 3) FROM guild_teams WHERE name LIKE '%-GV')"
    else:
        query = "SELECT name, defId FROM roster " \
              + "JOIN players ON players.allyCode = roster.allyCode " \
              + "WHERE players.allyCode IN (SELECT allyCode FROM players WHERE guildName = (SELECT guildName FROM players WHERE allyCode="+allyCode_txt+")) "\
              + "AND defId IN (SELECT LEFT(name, LENGTH(name) - 3) FROM guild_teams WHERE name LIKE '%-GV')"

    goutils.log2("DBG", query)
    db_data_gv = connect_mysql.get_table(query)
    dict_gv_done = {}
    for line in db_data_gv:
        player = line[0]
        char_id = line[1]
        if not (player in dict_gv_done):
            dict_gv_done[player] = []
        dict_gv_done[player].append(char_id)

    if db_data_evo != None:
        guild_name = db_data_evo[0][0]
        oldest = db_data_evo[-1][3]
        latest = db_data_evo[0][3]

        #prepare stats for Journey Guide
        dict_teams_gv = {}
        for team_name in dict_teams:
            if team_name.endswith("-GV"):
                team_name_gv = team_name[:-3]
                team_elements = []
                for team_category in dict_teams[team_name]["categories"]:
                    list_alias = list(team_category[2].keys())
                    team_elements = team_elements + list_alias
                dict_teams_gv[team_name_gv] = team_elements

        stats_units = {} #id: [name, count]
        stats_categories = {} #id: [name, count]
        stats_gv = {} #id: [name, count]
        for line in db_data_evo:
            player_name = line[1]
            unit_id = line[2]
            if unit_id != "all":
                unit_combatType = dict_unitsList[unit_id]["combatType"]
                if unit_combatType == 1:
                    unit_name = dict_unitsList[unit_id]["nameKey"]
                    if unit_id in stats_units:
                        stats_units[unit_id][1] += 1
                    else:
                        stats_units[unit_id] = [unit_name, 1]

                    unit_categories = dict_unitsList[unit_id]["categoryIdList"]
                    for category in unit_categories:
                        if category in dict_categoryList:
                            category_name = dict_categoryList[category]["descKey"]
                            if category in stats_categories:
                                stats_categories[category][1] += 1
                            else:
                                stats_categories[category] = [category_name, 1]

                    for char_gv_id in dict_teams_gv:
                        if player_name in dict_gv_done:
                            if char_gv_id in dict_gv_done[player_name]:
                                continue
                        char_gv_name = dict_unitsList[char_gv_id]["nameKey"]
                        if unit_id in dict_teams_gv[char_gv_id]:
                            if char_gv_id in stats_gv:
                                stats_gv[char_gv_id][1] += 1
                            else:
                                stats_gv[char_gv_id] = [char_gv_name, 1]


        goutils.log2("DBG", "stats_units: "+str(stats_units))
        goutils.log2("DBG", "stats_categories: "+str(stats_categories))
        goutils.log2("DBG", "stats_gv: "+str(stats_gv))

        if compute_guild:
            evo_item_name = guild_name
        else:
            evo_item_name = player_name
            
        ret_cmd = "**Evolutions du roster de "+evo_item_name+" durant les "+str(days)+" derniers jours "\
                + "(du "+str(oldest)+" au "+str(latest)+")**\n"
        ret_cmd += "1 évolution =  1 step de niveau (peut regrouper plusieurs steps si faits ensemble), de gear, de relic, 1 zeta en plus, déblocage du perso\n"
        if "alignment_light" in stats_categories:
            lightside = stats_categories["alignment_light"][1]
        else:
            lightside=0
        if "alignment_dark" in stats_categories:
            darkside = stats_categories["alignment_dark"][1]
        else:
            darkside=0
        ret_cmd += "\nLight / Dark = "+str(lightside)+"/"+str(darkside)+"\n"

        ret_cmd += "\n__TOP 10 PERSOS__\n"
        list_evo_units = sorted(stats_units.items(), key=lambda x:-x[1][1])
        for evo in list_evo_units[:10]:
            ret_cmd += evo[1][0] + ": " + str(evo[1][1])+'\n'

        ret_cmd += "\n__TOP 10 FACTIONS__\n"
        faction_items = [x for x in stats_categories.items() if x[0][:5] in ["affil", "profe"]]
        list_evo_categories = sorted(faction_items, key=lambda x:-x[1][1])
        for evo in list_evo_categories[:10]:
            ret_cmd += evo[1][0] + ": " + str(evo[1][1])+'\n'

        ret_cmd += "\n__TOP 10 GUIDE DE VOYAGE__\n"
        list_gv_units = sorted(stats_gv.items(), key=lambda x:-x[1][1])
        for gv in list_gv_units[:10]:
            ret_cmd += gv[1][0] + ": " + str(gv[1][1])+'\n'

        return 0, ret_cmd

    else:
        goutils.log2("ERR", "error while running query, returned NULL")
        return 1, "ERR: erreur lors de la connexion à la DB"

#################################
# Function: print_raid_progress
# return: err_code, err_txt, list of players with teams and scores
#################################
def print_raid_progress(allyCode_txt, raid_alias, use_mentions):
    dict_raids = connect_gsheets.load_config_raids(False)
    if raid_alias in dict_raids:
        raid_config = dict_raids[raid_alias]
    else:
        return 1, "ERR: unknown raid "+raid_alias+" among "+str(list(dict_raids.keys())), ""

    query = "SELECT warstats_id FROM guilds "
    query+= "JOIN players ON guilds.name = players.guildName "
    query+= "where allyCode = "+allyCode_txt
    warstats_id = connect_mysql.get_value(query)

    if warstats_id == None or warstats_id == 0:
        return 1, "ERR: ID de guilde warstats non défini", ""

    raid_name = raid_config[0]
    raid_teams = raid_config[1]
    raid_team_names = raid_teams.keys()
    guild_name, dict_teams = get_team_progress(raid_team_names, allyCode_txt, True, False)
    dict_teams_by_player = {}
    for team in dict_teams:
        dict_teams_by_player[team]={}
        for line in dict_teams[team][0][1:]:
            nogo = line[3]
            player_name = line[4]
            dict_teams_by_player[team][player_name] = not nogo

    raid_phase, raid_scores = connect_warstats.parse_raid_scores(warstats_id, raid_name)

    #Player lines
    dict_players_by_IG = connect_gsheets.load_config_players(False)[0]
    list_scores = []
    list_unknown_players = []
    list_inactive_players = []
    guild_score_by_phase = [0, 0, 0, 0]
    for player_name in raid_scores:
        line=[player_name]

        if use_mentions and (player_name in dict_players_by_IG):
            player_mention = dict_players_by_IG[player_name][1]
            txt_alert = "**" + player_mention + "** n'a pas joué malgré :"
        else:
            txt_alert = "**" + player_name + "** n'a pas joué malgré :"

        normal_score = 0
        super_score = 0
        for team in raid_team_names:
            if player_name in dict_teams_by_player[team]:
                player_has_team = dict_teams_by_player[team][player_name]
            else:
                if not player_name in list_unknown_players:
                    list_unknown_players.append(player_name)
                player_has_team = False
            team_phase = raid_teams[team][0]
            team_normal_score = raid_teams[team][1]
            team_super_score = raid_teams[team][2]

            if player_has_team and raid_phase >= team_phase:
                normal_score += team_normal_score
                super_score += team_super_score
                txt_alert += " " + team + ","

            if player_has_team:
                guild_score_by_phase[team_phase-1] += team_normal_score
                if guild_score_by_phase[team_phase-1] > data.dict_raid_tiers[raid_name][team_phase-1]:
                    guild_score_by_phase[team_phase-1] = data.dict_raid_tiers[raid_name][team_phase-1]

            line.append(player_has_team)
        player_score = raid_scores[player_name]
        line.append(player_score)
        line.append(normal_score)
        line.append(super_score)

        if normal_score == 0:
            player_status = "-"
        elif player_score >= super_score:
            player_status = "\N{WHITE HEAVY CHECK MARK}"
        elif player_score >= normal_score:
            player_status = "\N{WHITE RIGHT POINTING BACKHAND INDEX}"
        elif player_score > 0:
            player_status = "\N{UP-POINTING RED TRIANGLE}"
        else:
            player_status = "\N{CROSS MARK}"
            list_inactive_players.append(txt_alert[:-1])
        line.append(player_status)

        list_scores.append(line)

    #Display
    if raid_phase == 0 or raid_phase == 5:
        raid_phase_txt = "terminé"
    else:
        raid_phase_txt = "phase "+str(raid_phase)
    ret_print_raid_progress = "Résultat du Raid "+raid_name+" ("+raid_phase_txt+") pour la guilde "+guild_name+"\n\n"
    ret_print_raid_progress+= "Teams recommandées :\n"
    team_id = 1
    for team in raid_team_names:
        ret_print_raid_progress+= "T{0:1}: {1:20} - P{2:1} (normal: {3:8}, "\
                                  "super: {4:8})\n".format(
                                          team_id,
                                          team,
                                          raid_teams[team][0],
                                          raid_teams[team][1],
                                          raid_teams[team][2])
        team_id += 1

    #Header line
    ret_print_raid_progress+= "\nSPLIT_HERE{0:20}".format("Joueur")
    for id in range(1, team_id):
        ret_print_raid_progress+= "T"+str(id)+" "
    ret_print_raid_progress+= "{0:8} ({1:8}/{2:8}) Statut\n".format("Score", "Normal", "Super")

    #Display all players
    for line in list_scores:
        ret_print_raid_progress+= "{0:20}".format(line[0])
        for id in range(1, team_id):
            if line[id]:
                ret_print_raid_progress+= "X  "
            else:
                ret_print_raid_progress+= ".  "
        ret_print_raid_progress+= "{0:8} ({1:8}/{2:8}) {3:1}\n".format(
                                line[id+1],
                                line[id+2],
                                line[id+3],
                                line[id+4])

    #Display theoretical obtainable score and phase
    goutils.log2("DBG", "guild_score_by_phase = "+str(guild_score_by_phase))
    if guild_score_by_phase[0] < data.dict_raid_tiers[raid_name][0]:
        total_normal_score = guild_score_by_phase[0]
    elif guild_score_by_phase[1] < data.dict_raid_tiers[raid_name][1]:
        total_normal_score = sum(guild_score_by_phase[:2])
    elif guild_score_by_phase[2] < data.dict_raid_tiers[raid_name][2]:
        total_normal_score = sum(guild_score_by_phase[:3])
    else:
        total_normal_score = sum(guild_score_by_phase)

    if total_normal_score >= sum(data.dict_raid_tiers[raid_name]):
        normal_raid_phase = 5
    elif total_normal_score >= sum(data.dict_raid_tiers[raid_name][:3]):
        normal_raid_phase = 4
        normal_progress = (                  total_normal_score - sum(data.dict_raid_tiers[raid_name][:3]))/ \
                          (sum(data.dict_raid_tiers[raid_name]) - sum(data.dict_raid_tiers[raid_name][:3]))
    elif total_normal_score >= sum(data.dict_raid_tiers[raid_name][:2]):
        normal_raid_phase = 3
        normal_progress = (                      total_normal_score - sum(data.dict_raid_tiers[raid_name][:2]))/ \
                          (sum(data.dict_raid_tiers[raid_name][:3]) - sum(data.dict_raid_tiers[raid_name][:2]))
    elif total_normal_score >= data.dict_raid_tiers[raid_name][0]:
        normal_raid_phase = 2
        normal_progress = (                      total_normal_score - data.dict_raid_tiers[raid_name][0])/ \
                          (sum(data.dict_raid_tiers[raid_name][:2]) - data.dict_raid_tiers[raid_name][0])
    else:
        normal_raid_phase = 1
        normal_progress = total_normal_score / sum(data.dict_raid_tiers[raid_name][0])
    ret_print_raid_progress+= "\nScore atteignable par la guilde en mode normal : "+str(total_normal_score)
    if normal_raid_phase == 5:
        ret_print_raid_progress+= " (raid terminé)"
    else:
        normal_progress_percent = int(normal_progress*100)
        ret_print_raid_progress+= " ("+str(normal_progress_percent)+"% de la phase "+str(normal_raid_phase)+")"
    
    if len(list_unknown_players)>0:
        ret_print_raid_progress+= "\nWAR: joueurs inconnus de la guilde "+str(list_unknown_players)

    if len(list_inactive_players)>0:
        ret_print_raid_progress+= "\n\nSPLIT_HERE__Rappels pour le raid **"+raid_name+"** :__"
        ret_print_raid_progress+= "\n(dites \"go.vtj me <nom team>\" au bot pour voir la composition)"
        for txt_alert in list_inactive_players:
            ret_print_raid_progress+= "\n" + txt_alert

    return 0, "", ret_print_raid_progress

#################################
# Function: print_tb_progress
# return: err_code, err_txt, list of players with teams and scores
#################################
def print_tb_progress(allyCode_txt, tb_alias, use_mentions):
    list_tb_teams = connect_gsheets.load_tb_teams(False)
    tb_team_names = list(set(sum(sum([list(x.values()) for x in list_tb_teams], []), [])))
    tb_team_names.remove('')
    list_known_bt = list(set(sum([[y[0:3] for y in x.keys()] for x in list_tb_teams], [])))
    if not tb_alias in list_known_bt:
        return 1, "ERR: unknown BT", ""

    query = "SELECT warstats_id FROM guilds "
    query+= "JOIN players ON guilds.name = players.guildName "
    query+= "where allyCode = "+allyCode_txt
    warstats_id = connect_mysql.get_value(query)

    if warstats_id == None or warstats_id == 0:
        return 1, "ERR: ID de guilde warstats non défini", ""

    guild_name, dict_teams = get_team_progress(tb_team_names, allyCode_txt, True, False)
    dict_teams_by_player = {}
    for team in dict_teams:
        dict_teams_by_player[team]={}
        for line in dict_teams[team][0][1:]:
            nogo = line[3]
            player_name = line[4]
            dict_teams_by_player[team][player_name] = not nogo

    active_round, dict_player_scores, list_open_territories = \
            connect_warstats.parse_tb_player_scores(warstats_id, tb_alias, True)

    if tb_alias[0] == "H":
        tb_day_count = 6
    else:
        tb_day_count = 4

    #Player lines
    dict_players_by_IG = connect_gsheets.load_config_players(False)[0]
    list_scores = []
    list_terr_by_day = [""] * tb_day_count
    first_player = True
    list_unknown_players = []
    list_inactive_players_by_day = [[] for i in range(tb_day_count)]
    for player_name in dict_player_scores:
        if player_name == "":
            continue

        goutils.log2('DBG', 'player_name: '+player_name)
        line=[player_name]

        if use_mentions and (player_name in dict_players_by_IG):
            player_mention = dict_players_by_IG[player_name][1]
        else:
            player_mention = player_name

        for team in tb_team_names:
            player_has_team = False
            if player_name in dict_teams_by_player[team]:
                player_has_team = dict_teams_by_player[team][player_name]
            else:
                if not player_name in list_unknown_players:
                    list_unknown_players.append(player_name)

            if player_has_team:
                line.append("X")
            else:
                line.append("")

        for i_day in range(tb_day_count):
            day_progress_txt = ""
            day_name = tb_alias+str(i_day+1)
            goutils.log2('DBG', 'day_name: '+day_name)

            if not day_name in dict_player_scores[player_name]:
                line.append("")
                continue

            day_scores = dict_player_scores[player_name][day_name]
            goutils.log2('DBG', 'day_scores: '+str(day_scores))
            total_fight_count_day = int(day_scores[-1])
            max_fights_day = max([len(x) for x in day_scores])
            if len(day_scores)==2: #index, name, is_ground
                list_territories = [[0, "top", True], [1, "bot", True]]
            else:
                list_territories = [[0, "top", False], [1, "mid", True], [2, "bot", True]]

            team_list_day = [[], []]
            fight_count_day = [0, 0] #[ships, ground]
            for [idx, pos, is_ground] in list_territories:
                territory_scores = day_scores[idx]
                terr_round = territory_scores[0]
                full_terr_name = tb_alias+"-P"+str(terr_round)+"-"+pos
                if first_player:
                    list_terr_by_day[i_day] += "P"+str(terr_round)+"-"+pos + "\n"

                terr_teams = list_tb_teams[i_day][full_terr_name]

                team_count_terr = 0
                for team in terr_teams:
                    if team == "":
                        continue
                    if player_name in dict_teams_by_player[team]:
                        if dict_teams_by_player[team][player_name]:
                            goutils.log2("DBG", player_name + " has " + team)
                            team_count_terr += 1
                            team_list_day[is_ground].append(team)

                count_4=0
                count_1to3=0
                count_0=0
                for score in territory_scores[1:]:
                    fight_count_day[is_ground] += 1
                    if score == '4' or (pos=="top" and score == "1"):
                        count_4+=1
                    elif score in ['1', '2', '3']:
                        count_1to3+=1
                    elif score == '0':
                        count_0+=1
                    else:#no fight
                        #cancel the +1 for fight count
                        fight_count_day[is_ground] -= 1

                terr_txt = ""
                while team_count_terr > 0:
                    if count_4 > 0:
                        count_4 -= 1
                        terr_txt += "\N{WHITE HEAVY CHECK MARK}"
                    elif count_1to3 > 0:
                        count_1to3 -= 1
                        terr_txt +=  "\N{WHITE RIGHT POINTING BACKHAND INDEX}"
                    elif count_0 > 0:
                        count_0 -= 1
                        terr_txt += "\N{UP-POINTING RED TRIANGLE}"
                    else:
                        if total_fight_count_day == sum(fight_count_day):
                            terr_txt += "\N{CROSS MARK}"
                        else:
                            terr_txt += "\N{TRIANGULAR FLAG ON POST}"

                    team_count_terr -= 1

                if len(terr_txt) < len(territory_scores[1:]):
                    terr_txt += "\N{WHITE LARGE SQUARE}" * (len(territory_scores[1:]) - len(terr_txt))
                if len(terr_txt) < max_fights_day:
                    terr_txt += "\N{BLACK LARGE SQUARE}" * (max_fights_day - len(terr_txt))

                day_progress_txt += terr_txt+"\n"

            line.append(day_progress_txt[:-1])

            #create alerts for inactive players
            full_team_list_day = [y for x in team_list_day for y in x]
            if len(full_team_list_day) > total_fight_count_day:
                if len(team_list_day[False]) == fight_count_day[False]:
                    txt_alert = "**" + player_mention + "** a fait " + str(fight_count_day[True]) \
                                + " combats terrestres malgré "+str(team_list_day[True])
                elif len(team_list_day[True]) == fight_count_day[True]:
                    txt_alert = "**" + player_mention + "** a fait " + str(fight_count_day[False]) \
                                + " combats de vaisseaux malgré "+str(team_list_day[False])
                else:
                    txt_alert = "**" + player_mention + "** a fait " + str(total_fight_count_day) \
                                + " combats malgré "+str(full_team_list_day)
                list_inactive_players_by_day[i_day].append(txt_alert)

        list_scores.append(line)
        first_player = False

    #Display
    if active_round == "":
        tb_phase_txt = "terminée"
    else:
        tb_phase_txt = "Jour "+active_round
    ret_print_tb_progress = "Résultat de la BT "+tb_alias+" ("+tb_phase_txt+") pour la guilde "+guild_name+"\n\n"
    ret_print_tb_progress+= "Teams utilisées :\n"

    team_id = 1
    for team in tb_team_names:
        #look in which territory the team is useful
        team_terr_set = set([])
        for day_teams in list_tb_teams:
            for terr_name in day_teams:
                if team in day_teams[terr_name]:
                    team_terr_set.add(terr_name[4:])

        ret_print_tb_progress+= "T"+str(team_id)+": "+team+" "+str(team_terr_set)+"\n"
        team_id += 1

    #Legend of emojis
    ret_print_tb_progress+= "\nLégende :\n"
    ret_print_tb_progress+= "- \N{WHITE HEAVY CHECK MARK} : team dispo et max atteint\n"
    ret_print_tb_progress+= "- \N{WHITE RIGHT POINTING BACKHAND INDEX} : team dispo et entre 1 et 3 vagues\n"
    ret_print_tb_progress+= "- \N{UP-POINTING RED TRIANGLE} : team dispo et aucune vague de réussie\n"
    ret_print_tb_progress+= "- \N{CROSS MARK} : team dispo et combat pas tenté\n"
    ret_print_tb_progress+= "- \N{TRIANGULAR FLAG ON POST} : team dispo et inconnu entre pas tenté et aucune vague\n"
    ret_print_tb_progress+= "- \N{WHITE LARGE SQUARE} : pas de team dispo\n"

    #Header line
    line_header = ["Joueur"]
    for id in range(1, team_id):
        line_header.append("T"+str(id))
    for id in range(0, tb_day_count):
        terr_day = list_terr_by_day[id]
        line_header.append("Jour "+str(id+1) + "\n" + terr_day[:-1])

    #Display all players
    t = Texttable()
    t.add_rows([line_header] + list_scores)
    ret_print_tb_progress+= "\n"+t.draw()

    if len(list_unknown_players)>0:
        ret_print_tb_progress+= "\n joueurs inconnus dans la guilde "+str(list_unknown_players)

    for i_day in range(tb_day_count):
        if len(list_inactive_players_by_day[i_day])>0:
            ret_print_tb_progress+= "\n\nSPLIT_HERE__Rappels pour le jour "\
                                 +str(i_day+1) + " de la **BT " + tb_alias + "**__ :"
            if active_round != "" and active_round[-1] == str(i_day+1):
                ret_print_tb_progress+= " *phase en cours*"

            ret_print_tb_progress+= "\n(dites \"go.vtj me <nom team>\" au bot pour voir la composition)"
            for row in list_inactive_players_by_day[i_day]:
                ret_print_tb_progress+= "\n"+row

    ret_print_tb_progress+= "\n\nCes rappels sont __en rôdage__. Contactez un officier si vous voyez une erreur."

    return 0, "", ret_print_tb_progress

def get_tw_alerts():
    dict_unitsList = data.get("unitsList_dict.json")

    query = "SELECT name, twChannel_id, warstats_id FROM guilds "
    query+= "WHERE twChannel_id > 0 AND warstats_id > 0"
    goutils.log2('DBG', query)
    db_data = connect_mysql.get_table(query)

    dict_tw_alerts = {}
    for [guildName, twChannel_id, warstats_id] in db_data:
        dict_tw_alerts[guildName] = [twChannel_id, []]

        list_opponent_squads = connect_warstats.parse_tw_teams(warstats_id)
        if len(list_opponent_squads) == 0:
            #TW not started
            continue
        list_opponent_players = [x[1] for x in list_opponent_squads]
        longest_opp_player_name = max(list_opponent_players, key=len)
        list_open_tw_territories = set([x[0] for x in list_opponent_squads])

        query = "SELECT players.name, defId, roster_skills.name from roster\n"
        query+= "JOIN roster_skills ON roster_id=roster.id\n"
        query+= "JOIN players ON players.allyCode=roster.allyCode\n"
        query+= "WHERE guildName=(SELECT guildName FROM players WHERE name='"+longest_opp_player_name+"')\n"
        query+= "AND omicron_tier=roster_skills.level\n"
        query+= "AND omicron_type='TW'"
        goutils.log2("DBG", query)
        omicron_table = connect_mysql.get_table(query)
        goutils.log2("DBG", omicron_table)

        for territory in list_open_tw_territories:
            list_opp_squads_terr = [x for x in list_opponent_squads if (x[0]==territory and len(x[2])>0)]
            counter_leaders = Counter([x[2][0] for x in list_opp_squads_terr])

            n_territory = int(territory[1])
            if territory[0] == "T" and int(territory[1]) > 2:
                n_territory -= 2

            if n_territory == 1:
                msg = "__Le 1er territoire "
            else:
                msg = "__Le "+str(n_territory)+"e territoire "

            if territory[0] == "T" and int(territory[1]) < 3:
                msg += "du haut__"
            elif territory[0] == "T":
                msg += "du milieu__"
            elif territory[0] == "F":
                msg += "des vaisseaux__"
            else:
                msg += "du bas__"

            msg += " ("+territory+") est ouvert. Avec ces adversaires :"
            for leader in counter_leaders:
                msg += "\n - "+leader+": "+str(counter_leaders[leader])
                for squad in list_opp_squads_terr:
                    opp_name = squad[1]
                    if squad[2][0] == leader:
                        leader_toon = True
                        for toon in squad[2]:
                            list_id, dict_id, txt = goutils.get_characters_from_alias([toon])
                            toon_id = list_id[0]
                            filtered_omicron_table = list(filter(lambda x: x[:2]==(opp_name, toon_id), omicron_table))
                            if len(filtered_omicron_table) == 1:
                                msg += "\n    - "+opp_name+": omicron sur "+toon
                                if filtered_omicron_table[0][2] == 'L' and not leader_toon:
                                    msg += "... qui n'est pas posé en chef \N{THINKING FACE}"
                            leader_toon = False


            dict_tw_alerts[guildName][1].append(msg)

    return dict_tw_alerts
