# -*- coding: utf-8 -*-

import sys
import time
import datetime
import os
import config
import difflib
import math
from functools import reduce
from math import ceil, factorial
import json
import matplotlib
matplotlib.use('Agg') #Preventin GTK erros at startup
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from PIL import Image, ImageDraw, ImageFont
from collections import Counter
import inspect
from texttable import Texttable
import itertools
import numpy as np
import asyncio

import connect_gsheets
import connect_mysql
import connect_crinolo
import connect_warstats
import connect_rpc
import goutils
import portraits
import parallel_work
import data as godata

FORCE_CUT_PATTERN = "SPLIT_HERE"
MAX_GVG_LINES = 50

SCORE_GREEN = 100
SCORE_ALMOST_GREEN = 95
SCORE_AMBER = 80
SCORE_RED = 50

#Clean temp files
parallel_work.clean_cache()

dict_stat_names={} # unitStatUd, is percentage
dict_stat_names["santé"] =  [1, False, "Santé"]
dict_stat_names["health"] = [1, False, "Santé"]
dict_stat_names["speed"] =   [5, False, "Vitesse"]
dict_stat_names["vitesse"] = [5, False, "Vitesse"]
dict_stat_names["dégâts physiques"] = [6, False, "Dégâts Physiques"]
dict_stat_names["dp"] =               [6, False, "Dégâts Physiques"]
dict_stat_names["physical damages"] = [6, False, "Dégâts Physiques"]
dict_stat_names["dégâts spéciaux"] = [7, False, "Dégâts spéciaux"]
dict_stat_names["ds"] =              [7, False, "Dégâts spéciaux"]
dict_stat_names["special damages"] = [7, False, "Dégâts spéciaux"]
dict_stat_names["chances de coup critique physique"] = [14, True, "Chances de coups critique"]
dict_stat_names["cdc"] =                      [14, True, "Chances de coups critique"]
dict_stat_names["physical critical chance"] =          [14, True, "Chances de coups critique"]
dict_stat_names["cc"] =                       [14, True, "Chances de coups critique"]
dict_stat_names["dégâts critiques"] = [16, True, "Dégâts critiques"]
dict_stat_names["dc"] =               [16, True, "Dégâts critiques"]
dict_stat_names["critical damages"] = [16, True, "Dégâts critiques"]
dict_stat_names["cd"] =               [16, True, "Dégâts critiques"]
dict_stat_names["pouvoir"] = [17, True, "Pouvoir"]
dict_stat_names["potency"] = [17, True, "Pouvoir"]
dict_stat_names["tenacité"] = [18, True, "Ténacité"]
dict_stat_names["tenacity"] = [18, True, "Ténacité"]
dict_stat_names["tena"] =     [18, True, "Ténacité"]
dict_stat_names["protec"] =     [28, False, "Protection"]
dict_stat_names["protection"] = [28, False, "Protection"]

BOT_GFILE = 0

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
    goutils.log2('INFO', 'Disk usage = ' + str(used_percentage) + '%')

    if used_percentage > 98:
        return 1, "Disk usage is above 98%"
    else:
        return 0, ""

##################################
# Function: refresh_cache
# return: error code
##################################
async def refresh_cache():
    # Get the guilds to be refreshed
    # the query gets one allyCode by guild in the DB
    query = "SELECT guilds.name, allyCode "\
           +"FROM guilds "\
           +"JOIN players on players.guildName = guilds.name "\
           +"WHERE guilds.update=1 "\
           +"ORDER BY guilds.lastUpdated"
    goutils.log2('DBG', query)
    ret_table = connect_mysql.get_table(query)
    
    if ret_table != None:
        for line in ret_table:
            guild_name = line[0]
            guild_allyCode = line[1]
            goutils.log2('INFO', "refresh guild " + guild_name \
                       +" with allyCode " + str(guild_allyCode))
            e, t, dict_guild = await load_guild(str(guild_allyCode), False, False)
            if e == 0 and dict_guild["profile"]['name'] == guild_name:
                e, t, dict_guild = await load_guild(str(guild_allyCode), True, False)
                break
            elif e == 0:
                goutils.log2('WAR', "load_guild("+str(guild_allyCode)+") returned guild "+guild_name)
            else:
                goutils.log2('ERR', 1)
                return 1
    else:
        goutils.log2('ERR', "Unable to refresh guilds")
        return 1

    # Get the shards to be refreshed
    query = "SELECT id, type "\
           +"FROM shards "\
           +"ORDER BY lastUpdated"
    goutils.log2('DBG', query)
    ret_table = connect_mysql.get_table(query)
    
    if ret_table != None:
        for line in ret_table:
            shard_id = line[0]
            shard_type = line[1]
            goutils.log2('INFO', "refresh shard " + str(shard_id) + " " + shard_type)
            e, t = await load_shard(shard_id, shard_type, False)
            if e == 0:
                break
            else:
                goutils.log2('ERR', t)
                return 1

    else:
        goutils.log2('ERR', "Unable to refresh shards")
        return 1

    return 0

##################################
# Function: load_player
# inputs: txt_allyCode (string)
#         int force_update (0: update if not recently updated,
#                           1: force update,
#                           -1: do not update unless there is no JSON)
#         bool no_db: do not put player in DB
# return: err_code, err_text, dict_player
##################################
async def load_player(ac_or_id, force_update, no_db):
    goutils.log2("DBG", "START")

    #get playerId from allyCode:
    if len(ac_or_id) == 9:
        allyCode = ac_or_id
        query = "SELECT playerId FROM players WHERE allyCode='"+allyCode+"'"
        goutils.log2("DBG", query)
        playerId = connect_mysql.get_value(query)
    else:
        playerId = ac_or_id

    if no_db:
        recent_player = False
        prev_dict_player = None
    else:
        # The query tests if the update is less than 60 minutes for all players
        # Assumption: when the command is player-related, updating one is costless
        if playerId != None:
            query = "SELECT (timestampdiff(MINUTE, players.lastUpdated, CURRENT_TIMESTAMP)<=60) AS recent, "
            query+= "name FROM players WHERE playerId = '"+str(playerId)+"'"
            goutils.log2("DBG", query)
            query_result = connect_mysql.get_line(query)
            if query_result != None:
                recent_player = query_result[0]
            else:
                recent_player = 0

            json_file = "PLAYERS/"+playerId+".json"
            goutils.log2("INFO", 'reading file ' + json_file + '...')
            if os.path.isfile(json_file):
                if os.path.getsize(json_file) == 0:
                    goutils.log2("DBG", "... empty file, delete it")
                    #empty file, delete it
                    os.remove(json_file)
                    prev_dict_player = None
                else:
                    goutils.log2("DBG", "... correct file")
                    prev_dict_player = json.load(open(json_file, 'r'))
                    prev_dict_player = goutils.roster_from_list_to_dict(prev_dict_player)
            else:
                goutils.log2("DBG", "... the file does not exist")
                prev_dict_player = None
        else:
            goutils.log2("DBG", "Player "+ac_or_id+" unknown. Need to get whole data")
            recent_player = 0
            prev_dict_player = None


    if ((not recent_player and force_update!=-1) or force_update==1 or prev_dict_player==None):
        goutils.log2("INFO", 'Requesting RPC data for player ' + ac_or_id + '...')
        ec, et, dict_player = await connect_rpc.get_player_data(ac_or_id, False)
        if ec != 0:
            goutils.log2("WAR", "RPC error ("+et+"). Using cache data from json")
            dict_player = prev_dict_player

        if dict_player == None:
            goutils.log2("ERR", 'Cannot get player data for '+ac_or_id)
            return 1, 'ERR: cannot get player data for '+ac_or_id, None

        #Add mandatory elements to compute stats
        for unit in dict_player["rosterUnit"]:
            if not "equipment" in unit:
                unit["equipment"] = []
            if not "skill" in unit:
                unit["skill"] = []
            if not "equippedStatMod" in unit:
                unit["equippedStatMod"] = []
            else:
                for mod in unit["equippedStatMod"]:
                    if not "secondaryStat" in mod:
                        mod["secondaryStat"] = []


        #Add statistics
        err_code, err_txt, dict_player = connect_crinolo.add_stats(dict_player)

        #Transform the roster into dictionary with key = defId
        dict_player = goutils.roster_from_list_to_dict(dict_player)

        playerId = dict_player["playerId"]
        player_name = dict_player["name"]

        goutils.log2("INFO", "success retrieving "+player_name+" from RPC")
        
        if not no_db:
            # compute differences
            delta_dict_player = goutils.delta_dict_player(prev_dict_player, dict_player)
        
            # store json file
            json_file = "PLAYERS/"+playerId+".json"
            fjson = open(json_file, 'w')
            fjson.write(json.dumps(dict_player, sort_keys=True, indent=4))
            fjson.close()

            # update DB
            ret = await connect_mysql.update_player(delta_dict_player)
            if ret == 0:
                goutils.log2("INFO", "success updating "+dict_player['name']+" in DB")
            else:
                goutils.log2('ERR', 'update_player '+ac_or_id+' returned an error')
                return 1, 'ERR: update_player '+ac_or_id+' returned an error', None
                
    else:
        dict_player = prev_dict_player
        player_name = dict_player["name"]
        goutils.log2('INFO', player_name + ' loaded from existing XML OK')
    
    goutils.log2('DBG', "END")
    return 0, "", dict_player

async def load_guild(txt_allyCode, load_players, cmd_request):
    #Get API data for the guild
    goutils.log2('INFO', 'Requesting RPC data for guild of ' + txt_allyCode)

    query = "SELECT id FROM guilds "
    query+= "JOIN players ON players.guildName = guilds.name "
    query+= "WHERE allyCode = " + txt_allyCode
    goutils.log2("DBG", 'query: '+query)
    db_result = connect_mysql.get_value(query)

    prev_dict_guild = None
    if db_result == None or db_result == "":
        goutils.log2("WAR", 'Guild ID not found for '+txt_allyCode)
        guild_id = ""
    else:
        guild_id = db_result
        goutils.log2("INFO", 'Guild ID for '+txt_allyCode+' is '+guild_id)

        json_file = "GUILDS/"+guild_id+".json"
        if os.path.isfile(json_file):
            prev_dict_guild = json.load(open(json_file, 'r'))

    ec, et, dict_guild = await connect_rpc.get_guild_data(txt_allyCode, False)
    if ec != 0:
        goutils.log2("WAR", "RPC error ("+et+"). Using cache data from json")
        dict_guild = prev_dict_guild

    if dict_guild == None:
        goutils.log2("ERR", "Cannot get guild data for "+txt_allyCode)
        return 1, "ERR Cannot get guild data for "+txt_allyCode, None

    guildName = dict_guild["profile"]['name']
    guild_id = dict_guild["profile"]['id']
    total_players = len(dict_guild["member"])
    playerId_in_API = [x['playerId'] for x in dict_guild["member"]]
    guild_gp = sum([int(x['galacticPower']) for x in dict_guild["member"]])
    goutils.log2("INFO", "success retrieving "+guildName+" ("\
                +str(total_players)+" players, "+str(guild_gp)+" GP) from RPC")
                
    # store json file
    json_file = "GUILDS/"+guild_id+".json"
    fjson = open(json_file, 'w')
    fjson.write(json.dumps(dict_guild, sort_keys=True, indent=4))
    fjson.close()

    #Get guild data from DB
    query = "SELECT lastUpdated FROM guilds "\
           +"WHERE name = '"+guildName.replace("'", "''")+"'"
    goutils.log2('DBG', query)
    lastUpdated = connect_mysql.get_value(query)

    if lastUpdated == None:
        is_new_guild = True

        #Create guild in DB
        query = "INSERT IGNORE INTO guilds(name, id) VALUES('"+guildName.replace("'", "''")+"', '"+guild_id+"')"
        goutils.log2('DBG', query)
        connect_mysql.simple_execute(query)

        query = "INSERT INTO guild_evolutions(guild_id, description) "
        query+= "VALUES('"+guild_id+"', 'creation of the guild')"
        goutils.log2('DBG', query)
        connect_mysql.simple_execute(query)
    else:
        is_new_guild = False


    query = "SELECT playerId FROM players "\
           +"WHERE guildName = '"+guildName.replace("'", "''")+"'"
    goutils.log2('DBG', query)
    playerId_in_DB = connect_mysql.get_column(query)
    while None in playerId_in_DB:
        playerId_in_DB.remove(None)

    playerId_to_add = []
    for id in playerId_in_API:
        if not id in playerId_in_DB:
            playerId_to_add.append(id)
            query = "INSERT INTO guild_evolutions(guild_id, playerId, description) "
            query+= "VALUES('"+guild_id+"', '"+str(id)+"', 'added')"
            goutils.log2('DBG', query)
            connect_mysql.simple_execute(query)

    playerId_to_remove = []
    for id in playerId_in_DB:
        if not id in playerId_in_API:
            playerId_to_remove.append(id)
            query = "INSERT INTO guild_evolutions(guild_id, playerId, description) "
            query+= "VALUES('"+guild_id+"', '"+str(id)+"', 'removed')"
            goutils.log2('DBG', query)
            connect_mysql.simple_execute(query)

    if load_players:
        if lastUpdated != None:
            delta_lastUpdated = datetime.datetime.now() - lastUpdated
            if cmd_request:
                #if guild info used for a command, do not refresh unless more than 3 days (length of TW)
                need_refresh_due_to_time = (delta_lastUpdated.days*86400 + delta_lastUpdated.seconds) > 3*86400
            else:
                #if guild info refreshed regularly, do if more than one hour
                need_refresh_due_to_time = (delta_lastUpdated.days*86400 + delta_lastUpdated.seconds) > 3600
        else:
            need_refresh_due_to_time = False

        need_to_add_players = (len(playerId_to_add) > 0)
        goutils.log2("DBG", "need_to_add_players="+str(need_to_add_players))
        goutils.log2("DBG", "need_refresh_due_to_time="+str(need_refresh_due_to_time))

        if is_new_guild or need_refresh_due_to_time or need_to_add_players:
            #The guild is not defined yet, add it
            guild_loading_status = parallel_work.get_guild_loading_status(guildName)

            if is_new_guild or need_refresh_due_to_time:
                #add all players
                list_playerId_to_update = [x['playerId'] for x in dict_guild["member"]]
            else:
                #only some players to be added
                list_playerId_to_update = playerId_to_add
                total_players = len(list_playerId_to_update)

            if guild_loading_status != None:
                #The guild is already being loaded
                while guild_loading_status != None:
                    goutils.log2('INFO', "Guild "+guildName+" already loading ("\
                            + guild_loading_status + "), waiting 30 seconds...")
                    await asyncio.sleep(30)
                    guild_loading_status = parallel_work.get_guild_loading_status(guildName)
            else:
                #Ensure only one guild loading at a time
                #while len(dict_loading_guilds) > 1:
                list_other_guilds_loading_status = parallel_work.get_other_guilds_loading_status(guildName)
                while len(list_other_guilds_loading_status) > 0:
                    goutils.log2('INFO', "Guild "+guildName+" loading "\
                                +"will start after loading of "+str(list_other_guilds_loading_status))
                    await asyncio.sleep(30)
                    list_other_guilds_loading_status = parallel_work.get_other_guilds_loading_status(guildName)

                #Request to load this guild
                parallel_work.set_guild_loading_status(guildName, "0/"+str(total_players))

                #add player data
                i_player = 0
                for playerId in list_playerId_to_update:
                    i_player += 1
                    goutils.log2("INFO", "player #"+str(i_player))
                    
                    e, t, d = await load_player(str(playerId), 0, False)
                    goutils.log2("DBG", "after load_player...")
                    parallel_work.set_guild_loading_status(guildName, str(i_player)+"/"+str(total_players))
                    goutils.log2("DBG", "after set_guild_loading_status...")
                    await asyncio.sleep(1)
                    goutils.log2("DBG", "after sleep...")

                parallel_work.set_guild_loading_status(guildName, None)

                #Update dates in DB
                query = "UPDATE guilds "\
                       +"SET id = '"+guild_id+"', "\
                       +"lastUpdated = CURRENT_TIMESTAMP "\
                       +"WHERE name = '"+guildName.replace("'", "''") + "'"
                goutils.log2('DBG', query)
                connect_mysql.simple_execute(query)

        else:
            lastUpdated_txt = lastUpdated.strftime("%d/%m/%Y %H:%M:%S")
            goutils.log2('INFO', "Guild "+guildName+" last update is "+lastUpdated_txt)

    #Update dates in DB
    if cmd_request:
        query = "UPDATE guilds "\
               +"SET lastRequested = CURRENT_TIMESTAMP "\
               +"WHERE name = '"+guildName.replace("'", "''") + "'"
        goutils.log2('DBG', query)
        connect_mysql.simple_execute(query)

    #Erase guildName for alyCodes not detected from API
    if len(playerId_to_remove) > 0:
        query = "UPDATE players "\
               +"SET guildName = '', guildMemberLevel = 2 "\
               +"WHERE playerId IN "+str(tuple(playerId_to_remove)).replace(",)", ")")
        goutils.log2('DBG', query)
        connect_mysql.simple_execute(query)

    #Manage guild roles (leader, officers)
    query = "SELECT playerId, guildMemberLevel FROM players "\
           +"WHERE guildName = '"+guildName.replace("'", "''")+"'"
    goutils.log2('DBG', query)
    roles_in_DB = connect_mysql.get_table(query)
    dict_roles = {}
    if roles_in_DB != None:
        for role in roles_in_DB:
            dict_roles[role[0]] = role[1]

    for member in dict_guild["member"]:
        id = member["playerId"]
        if id in dict_roles:
            if member["memberLevel"] != dict_roles[id]:
                #change the role
                query = "UPDATE players SET guildMemberLevel = "+str(member["memberLevel"])+" " \
                       +"WHERE playerId = '"+str(id)+"'"
                goutils.log2('DBG', query)
                connect_mysql.simple_execute(query)
                
                #log it in guild_evolutions
                description = "guildMemberLevel changed from "+str(dict_roles[id])+" to "+str(member["memberLevel"])
                query = "INSERT INTO guild_evolutions(guild_id, playerId, description) "
                query+= "VALUES('"+guild_id+"', '"+str(id)+"', '"+description+"')"
                goutils.log2('DBG', query)
                connect_mysql.simple_execute(query)
            del dict_roles[member["playerId"]]
        else:
            goutils.log2('WAR', str(id)+" found in RPC but not found in DB while updating guild")

    #manage  remaining players
    for id in dict_roles:
        goutils.log2('WAR', str(id)+" found in DB but not found in RPC while updating guild")

    return 0, "", dict_guild

async def load_shard(shard_id, shard_type, cmd_request):
    #Get API data for the guild
    goutils.log2('INFO', 'Requesting API data for shard ' + str(shard_id))

    guildName = "shard "+shard_type+" "+str(shard_id)

    query = "SELECT lastUpdated FROM shards "\
           +"WHERE id = "+str(shard_id)
    goutils.log2('DBG', query)
    lastUpdated = connect_mysql.get_value(query)

    query = "SELECT allyCode FROM players "
    query+= "WHERE "+shard_type+"Shard_id = " + str(shard_id)
    goutils.log2("DBG", query)
    allyCodes_in_DB = connect_mysql.get_column(query)

    if allyCodes_in_DB == None or len(allyCodes_in_DB) == 0:
        goutils.log2("WAR", 'No player found for shard "+shard_type+" of ID '+str(shard_id))
        return 1, "No player found for shard "+shard_type+" of ID "+str(shard_id)

    delta_lastUpdated = datetime.datetime.now() - lastUpdated
    if cmd_request:
        #if shard info used for a command, do not refresh unless more than a day
        need_refresh_due_to_time = (delta_lastUpdated.days*86400 + delta_lastUpdated.seconds) > 86400
    else:
        #if guild info refreshed regularly, do if more than one hour
        need_refresh_due_to_time = (delta_lastUpdated.days*86400 + delta_lastUpdated.seconds) > 3600

    goutils.log2("DBG", "need_refresh_due_to_time="+str(need_refresh_due_to_time))

    if need_refresh_due_to_time:
        #The guild is not defined yet, add it
        guild_loading_status = parallel_work.get_guild_loading_status(guildName)

        list_allyCodes_to_update = allyCodes_in_DB
        total_players = len(list_allyCodes_to_update)

        if guild_loading_status != None:
            #The guild is already being loaded
            #while dict_loading_guilds[guildName][1] < dict_loading_guilds[guildName][0]:
            while guild_loading_status != None:
                goutils.log2('INFO', "Guild "+guildName+" already loading ("\
                        + guild_loading_status + "), waiting 30 seconds...")
                await asyncio.sleep(30)
                guild_loading_status = parallel_work.get_guild_loading_status(guildName)
        else:
            #Ensure only one guild loading at a time
            #while len(dict_loading_guilds) > 1:
            list_other_guilds_loading_status = parallel_work.get_other_guilds_loading_status(guildName)
            while len(list_other_guilds_loading_status) > 0:
                goutils.log2('INFO', "Guild "+guildName+" loading "\
                            +"will start after loading of "+str(list_other_guilds_loading_status))
                await asyncio.sleep(30)
                list_other_guilds_loading_status = parallel_work.get_other_guilds_loading_status(guildName)

            #Request to load this guild
            parallel_work.set_guild_loading_status(guildName, "0/"+str(total_players))

            #add player data
            i_player = 0
            for allyCode in list_allyCodes_to_update:
                i_player += 1
                goutils.log2("INFO", "player #"+str(i_player))
                
                e, t, d = await load_player(str(allyCode), 0, False)
                parallel_work.set_guild_loading_status(guildName, str(i_player)+"/"+str(total_players))

            parallel_work.set_guild_loading_status(guildName, None)

            #Update dates in DB
            query = "UPDATE shards "\
                   +"SET lastUpdated = CURRENT_TIMESTAMP "\
                   +"WHERE id = "+str(shard_id)
            goutils.log2('DBG', query)
            connect_mysql.simple_execute(query)

    else:
        lastUpdated_txt = lastUpdated.strftime("%d/%m/%Y %H:%M:%S")
        goutils.log2('INFO', guildName+" last update is "+lastUpdated_txt)

    #Update dates in DB
    if cmd_request:
        query = "UPDATE shards "\
               +"SET lastRequested = CURRENT_TIMESTAMP "\
               +"WHERE id = "+str(shard_id)
        goutils.log2('DBG', query)
        connect_mysql.simple_execute(query)

    return 0, ""

async def get_team_line_from_player(team_name_path, dict_teams, dict_team_gt, gv_mode, player_name):
    dict_unitsList = godata.get("unitsList_dict.json")
    line = ''

    #manage team_name in a path for recursing requests
    team_name = team_name_path.split('/')[-1]
    if team_name_path.count(team_name) > 1:
        #recurring loop, stop it
        return 0, False, "", False, []

    dict_team = dict_team_gt[team_name]
    objectifs = dict_team["categories"]
    nb_subobjs = len(objectifs)

    if team_name in dict_teams[player_name][1]:
        dict_player = dict_teams[player_name][1][team_name]
    else:
        dict_player = {}
    
    #INIT tableau des resultats
    tab_progress_player = [[] for i in range(nb_subobjs)]
    for i_subobj in range(0, nb_subobjs):
        nb_chars = len(objectifs[i_subobj][2])

        #score, display, nogo, charater_id, weight
        tab_progress_player[i_subobj] = [[0, '.     ', True, '', 1] for i in range(nb_chars)]

    goutils.log2("DBG", "player: "+player_name)
    # Loop on categories within the goals
    for i_subobj in range(0, nb_subobjs):
        dict_char_subobj = objectifs[i_subobj][2]

        for character_id in dict_char_subobj:
            await asyncio.sleep(0)

            #goutils.log2("DBG", "character_id: "+character_id)
            progress = 0
            progress_100 = 0
            
            character_obj = dict_char_subobj[character_id]
            i_character = character_obj[0]
            character_name = character_obj[7]
            if character_id in dict_player:
                if dict_player[character_id]['reserved']:
                    character_nogo = True
                else:
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
                    if req_gear_min[0] == 'G':
                        req_gear_min=int(req_gear_min[1:])
                    else: #assumed to be 'R'
                        req_relic_min=int(req_gear_min[-1])
                        req_gear_min=13
                    
                req_gear_reco = character_obj[4]
                req_relic_reco=0
                if req_gear_reco == '':
                    req_gear_reco = 1
                elif type(req_gear_reco) == str:
                    if req_gear_reco[0] == 'G':
                        req_gear_reco=int(req_gear_reco[1:])
                    else: #assumed to be 'R'
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
                req_zeta_ids = [goutils.get_capa_id_from_short(character_id, x) for x in req_zetas]
                req_zeta_ids = list(filter(lambda x: x != '', req_zeta_ids))
                        
                player_nb_zetas = 0
                progress_100 += len(req_zeta_ids)
                for zeta in dict_player[character_id]['zetas']:
                    if zeta in req_zeta_ids:
                        if dict_player[character_id]['zetas'][zeta]:
                            player_nb_zetas += 1
                            progress += 1
                if player_nb_zetas < len(req_zeta_ids):
                    character_nogo = True

                #Omicrons
                req_omicrons = character_obj[6].split(',')
                req_omicron_ids = [goutils.get_capa_id_from_short(character_id, x) for x in req_omicrons]
                req_omicron_ids = list(filter(lambda x: x != '', req_omicron_ids))
                        
                player_nb_omicrons = 0
                progress_100 += len(req_omicron_ids)
                for omicron in dict_player[character_id]['omicrons']:
                    if omicron in req_omicron_ids:
                        if dict_player[character_id]['omicrons'][omicron]:
                            player_nb_omicrons += 1
                            progress += 1
                if player_nb_omicrons < len(req_omicron_ids):
                    character_nogo = True

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

                        #Add farming info
                        for event in dict_unitsList[character_id]['farmingInfo']:
                            if event[0].startswith('C01'):
                                if event[0][3:] == 'L':
                                    color_emoji = "\N{Large Yellow Circle}"
                                elif event[0][3:] == 'D':
                                    color_emoji = "\N{Large Yellow Circle}"
                                elif event[0][3:] == 'H':
                                    color_emoji = "\N{LARGE RED CIRCLE}"
                                elif event[0][3:] == 'SP':
                                    color_emoji = "\N{LARGE BLUE CIRCLE}"
                                else:
                                    color_emoji = None

                                if event[1] == 1:
                                    speed_emoji = "x1"
                                elif event[1] == 2:
                                    speed_emoji = "x2"
                                else:
                                    speed_emoji = None

                                if color_emoji!=None and speed_emoji!=None:
                                    character_display += " > farming en "+color_emoji+speed_emoji

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

                #print(tab_progress_player)
                tab_progress_player[i_subobj][i_character - 1][0] = character_progress
                tab_progress_player[i_subobj][i_character - 1][1] = character_display
                tab_progress_player[i_subobj][i_character - 1][2] = character_nogo
                tab_progress_player[i_subobj][i_character - 1][3] = character_id
                tab_progress_player[i_subobj][i_character - 1][4] = 1

                #goutils.log2("DBG", tab_progress_player[i_subobj][i_character - 1])

            else:
                if gv_mode:
                    character_id_team = character_id + '-GV'
                    if character_id_team in dict_teams[player_name][1]:
                        score, unlocked, character_display, nogo, list_char = await get_team_line_from_player(team_name_path+'/'+character_id_team,
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

                        #Add farming info
                        for event in dict_unitsList[character_id]['farmingInfo']:
                            if event[0].startswith('C01'):
                                if event[0][3:] == 'L':
                                    color_emoji = "\N{Large Yellow Circle}"
                                elif event[0][3:] == 'D':
                                    color_emoji = "\N{Large Red Circle}"
                                elif event[0][3:] == 'H':
                                    color_emoji = "\N{LARGE RED CIRCLE}"
                                elif event[0][3:] == 'SP':
                                    color_emoji = "\N{LARGE BLUE CIRCLE}"
                                else:
                                    color_emoji = None

                                if event[1] == 1:
                                    speed_emoji = "x1"
                                elif event[1] == 2:
                                    speed_emoji = "x2"
                                else:
                                    speed_emoji = None

                                if color_emoji!=None and speed_emoji!=None:
                                    character_display += " > farming en "+color_emoji+speed_emoji

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

                goutils.log2("DBG", tab_progress_player[i_subobj][i_character - 1])


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
                if team_name[-3:]=="-GV":
                    line += "-- " + subobj_char_display + "\n"
            else:
                line += subobj_char_display + "\n"

    #pourcentage sur la moyenne
    score = score / score100 * 100

    goutils.log2("DBG", "list_char_id = " + str(list_char_id))
        
    unlocked = False
    if gv_mode and team_name[-3:]=="-GV":
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
                    req_zeta_names = [x[1] for x in goutils.get_capa_from_shorts(perso, req_zetas)]
                    req_omicrons = objectifs[i_level][2][perso][6].split(',')
                    req_omicron_names = [x[1] for x in goutils.get_capa_from_shorts(perso, req_omicrons)]
                    
                    perso_name = objectifs[i_level][2][perso][7]
                    entete += "- " + perso_name + ' (' + perso_min_display + ' à ' + \
                            perso_reco_display + ', zetas=' + str(req_zeta_names) + \
                            ', omicrons=' + str(req_omicron_names) + ')\n'

    return entete

#IN: gv_mode (0: VTJ, 1: GVJ, 2: FTJ)
async def get_team_progress(list_team_names, txt_allyCode, server_id, compute_guild, exclusive_player_list, gv_mode, dict_tw_def):
    dict_unitsList = godata.get("unitsList_dict.json")
    ret_get_team_progress = {}

    #Recuperation des dernieres donnees sur gdrive
    list_team_bot, dict_team_bot = connect_gsheets.load_config_teams(BOT_GFILE, False)
    if server_id != BOT_GFILE:
        list_team_guild, dict_team_guild = connect_gsheets.load_config_teams(server_id, False)
        list_team_gt = list_team_guild + list_team_bot
        dict_team_gt = {**dict_team_guild , **dict_team_bot}
    else:
        list_team_gt = list_team_bot
        dict_team_gt = dict_team_bot
    
    if not ('all' in list_team_names) and gv_mode==1:
        #Need to transform the name of the team into a character
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_team_names)
        if txt != "":
            return "", "ERR: impossible de reconnaître ce(s) nom(s) >> "+txt
        list_team_names = [x+"-GV" for x in list_character_ids]

        if compute_guild==2:
            is_character_ship = (dict_unitsList[list_character_ids[0]]['combatType']==2)
            if is_character_ship:
                shard_type = "ship"
            else:
                shard_type = "char"

    if compute_guild==0:
        #only one player, potentially several teams
        
        #Load or update data for the player
        e, t, d = await load_player(txt_allyCode, 1, False)
        if e != 0:
            #error wile loading guild data
            return "", 'ERR: joueur non trouvé pour code allié ' + txt_allyCode

        collection_name = d["name"]
            
    elif compute_guild==1:
        #Get data for the guild and associated players
        err_code, err_txt, guild = await load_guild(txt_allyCode, True, True)
        if err_code != 0:
            goutils.log2("WAR", "cannot get guild data from SWGOH.HELP API. Using previous data.")
        collection_name = guild["profile"]["name"]
    else:
        player_shard = connect_mysql.get_shard_from_player(txt_allyCode, shard_type)
        err_code, err_txt = await load_shard(player_shard, shard_type, True)
        if err_code != 0:
            goutils.log2("WAR", "cannot get shard data from SWGOH.HELP API. Using previous data.")
            return "", err_txt

        collection_name = "shard "+shard_type+" de "+txt_allyCode

    #Get player data
    goutils.log2("INFO", "Get player data from DB...")
    query = "SELECT players.name, players.allyCode, "\
           +"guild_teams.name, "\
           +"guild_team_roster.unit_id, "\
           +"rarity, "\
           +"gear, "\
           +"relic_currentTier, "\
           +"gp, "\
           +"stat5 as speed "\
           +"FROM players " \
           +"JOIN guild_teams " \
           +"JOIN guild_subteams ON guild_subteams.team_id = guild_teams.id "\
           +"JOIN guild_team_roster ON guild_team_roster.subteam_id = guild_subteams.id "\
           +"JOIN roster ON roster.defId = guild_team_roster.unit_id AND roster.allyCode = players.allyCode "
    if compute_guild==0:
        query += "WHERE roster.allyCode = '"+txt_allyCode+"'\n"
    elif compute_guild==1:
        query += "WHERE players.guildName = \
                (SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"')\n"
    else:
        query += "WHERE players."+shard_type+"Shard_id = \
                (SELECT "+shard_type+"Shard_id FROM players WHERE allyCode='"+txt_allyCode+"')\n"
    if gv_mode == 1:
        query += "AND guild_teams.name LIKE '%-GV'\n"
    else:
        query += "AND NOT guild_teams.name LIKE '%-GV'\n"

    if exclusive_player_list != None:
        query += "AND players.name IN "+str(tuple(exclusive_player_list)).replace(",)", ")")+"\n"
       
    query += "GROUP BY players.name, guild_teams.name, guild_team_roster.unit_id, \
            rarity, gear, relic_currentTier, gp \
            ORDER BY players.name, guild_teams.name"
    goutils.log2("DBG", query)
    player_data = connect_mysql.get_table(query)
    #goutils.log2("DBG", player_data)
    
    if gv_mode==0:
        # Need the zetas to compute the progress of a regular team
        goutils.log2("INFO", "Get zeta data from DB...")
        query = "SELECT players.name, \
                guild_teams.name, \
                guild_team_roster.unit_id, \
                guild_team_roster_zetas.name as zeta, \
                roster_skills.level, \
                roster_skills.omicron_tier \
                FROM players \
                JOIN guild_teams \
                JOIN guild_subteams ON guild_subteams.team_id = guild_teams.id \
                JOIN guild_team_roster ON guild_team_roster.subteam_id = guild_subteams.id \
                JOIN guild_team_roster_zetas ON guild_team_roster_zetas.roster_id = guild_team_roster.id \
                JOIN roster ON roster.defId = guild_team_roster.unit_id AND roster.allyCode = players.allyCode \
                JOIN roster_skills ON roster_skills.roster_id = roster.id AND roster_skills.name = guild_team_roster_zetas.name \n"
        if compute_guild==0:
            query += "WHERE roster.allyCode = '"+txt_allyCode+"'\n"
        elif compute_guild==1:
            query += "WHERE players.guildName = "+collection_name.replace("'", "''") +"\n"
        else:
            query += "WHERE players."+shard_type+"Shard_id = \
                    (SELECT "+shard_type+"Shard_id FROM players WHERE allyCode='"+txt_allyCode+"')\n"
        query += "AND NOT guild_teams.name LIKE '%-GV'\n"
        query += "AND guild_teams.GuildName = '"+collection_name.replace("'", "''")+"'\n"
           
        query += "ORDER BY roster.allyCode, guild_teams.name, guild_subteams.id, guild_team_roster.id"
        goutils.log2("DBG", query)
        
        player_zeta_data = connect_mysql.get_table(query)
        if player_zeta_data == None:
            player_zeta_data = []

        # Reuse previous query for omicrons
        query = query.replace("zeta", "omicron")
        goutils.log2("DBG", query)
        
        player_omicron_data = connect_mysql.get_table(query)
        if player_omicron_data == None:
            player_omicron_data = []
        
    
    else:
        #In gv_mode=1 or 2 (farming), there is no requirement for zetas
        player_zeta_data = []
        player_omicron_data = []
        
    if gv_mode > 0:
        #There is a need to check if the target character is locked or unlocked
        goutils.log2("INFO", "Get GV characters data from DB...")
        query = "SELECT players.name, players.allyCode, defId, rarity \
                FROM roster \
                JOIN players ON players.allyCode = roster.allyCode \n"
        if compute_guild==0:
            query += "WHERE roster.allyCode = '"+txt_allyCode+"'\n"
        elif compute_guild==1:
            query += "WHERE players.guildName = \
                    (SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"')\n"
        else:
            query += "WHERE players."+shard_type+"Shard_id = \
                    (SELECT "+shard_type+"Shard_id FROM players WHERE allyCode='"+txt_allyCode+"')\n"
        query += "AND defId IN (SELECT SUBSTRING_INDEX(name, '-GV', 1) FROM guild_teams WHERE name LIKE '%-GV')"
        goutils.log2("DBG", query)
        
        #print(query)
        gv_characters_unlocked = connect_mysql.get_table(query)        
        goutils.log2("DBG", gv_characters_unlocked)
    else:
        gv_characters_unlocked = []
        
    if player_data != None:
        goutils.log2("INFO", "Recreate dict_teams...")
        dict_teams = goutils.create_dict_teams(player_data,
                                               player_zeta_data,
                                               player_omicron_data,
                                               gv_characters_unlocked,
                                               dict_tw_def)
        goutils.log2("INFO", "Recreation of dict_teams is OK")
    else:
        query = "SELECT name FROM players WHERE allyCode = "+txt_allyCode
        goutils.log2("DBG", query)
        player_name = connect_mysql.get_value(query)
        dict_teams = {player_name: [0, {}]}
        goutils.log2("WAR", "no data recovered for allyCode="+txt_allyCode+" and teams="+str(list_team_names))
    
    # Compute teams for this player
    if gv_mode==1:
        filtered_list_team_gt = [x for x in filter(lambda f:f[-3:]=="-GV", list_team_gt)]
    else:
        filtered_list_team_gt = [x for x in filter(lambda f:f[-3:]!="-GV", list_team_gt)]

    if 'all' in list_team_names or gv_mode==2:
        list_team_names = filtered_list_team_gt
    
    for team_name in list_team_names:
        await asyncio.sleep(0)
        if not (team_name in dict_team_gt) and not ('all' in list_team_names):
            if gv_mode==1:
                ret_get_team_progress[team_name] = \
                        'ERREUR: Guide de Voyage inconnu pour ' + \
                        team_name + '. Liste=' + str(filtered_list_team_gt)
            else:
                ret_get_team_progress[team_name] = 'ERREUR: team ' + \
                        team_name + ' inconnue. Liste=' + str(filtered_list_team_gt)
        else:
            ret_team = []
            objectifs = dict_team_gt[team_name]["categories"]

            if gv_mode==0:
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
                player_allyCode = dict_teams[player_name][0]

                #resultats par joueur
                score, unlocked, line, nogo, list_char = await get_team_line_from_player(team_name,
                    dict_teams, dict_team_gt, gv_mode>0, player_name)
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

async def print_vtg(list_team_names, txt_allyCode, server_id, tw_mode):

    #Manage -TW option
    if tw_mode:
        ec, et, list_active_players = await connect_rpc.get_tw_active_players(server_id, False)
        if ec != 0:
            return ec, et

        ec, et, dict_def_toon_player = get_tw_defense_toons(server_id, True)
        if ec != 0:
            return ec, et

    else:
        dict_def_toon_player = {}
        list_active_players = None

    guild_name, ret_get_team_progress = await get_team_progress(list_team_names, txt_allyCode, 
                                              server_id, 1, list_active_players, 0, dict_def_toon_player)
    if type(ret_get_team_progress) == str:
        goutils.log2("ERR", "get_team_progress has returned an error: "+ret_print_vtx)
        return 1, ret_get_team_progress
    else:
        ret_print_vtx = "Vérification des Teams de la Guilde **"+guild_name+"**\n"
        if tw_mode:
            ret_print_vtx += "(les toons posés en défense de GT sont considérés indisponibles)\n"
            ret_print_vtx += "(les joueurs non-inscrits à la GT sont considérés indisponibles)\n"
        ret_print_vtx += "\n"

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

async def print_vtj(list_team_names, txt_allyCode, server_id, tw_mode):
    #Manage -TW option
    if tw_mode:
        ec, et, list_active_players = await connect_rpc.get_tw_active_players(server_id, False)
        if ec != 0:
            return ec, et

        ec, et, dict_def_toon_player = await get_tw_defense_toons(server_id, True)
        if ec != 0:
            return ec, et, None
    else:
        dict_def_toon_player = {}
        list_active_players = None

    player_name, ret_get_team_progress = await get_team_progress(list_team_names, txt_allyCode, 
                                              server_id, 0, list_active_players, 0, dict_def_toon_player)
    print("eeee", flush=True)
    if type(ret_get_team_progress) == str:
        goutils.log2("ERR", "get_team_progress has returned an error: "+ret_get_team_progress)
        return 1,  ret_get_team_progress, None
    else:
        ret_print_vtx = "Vérification des Teams du Joueur **"+player_name+"**\n"
        if tw_mode:
            ret_print_vtx += "(les toons posés en défense de GT sont considérés indisponibles)\n"
            ret_print_vtx += "(les joueurs non-inscrits à la GT sont considérés indisponibles)\n"
        ret_print_vtx += "\n"

        if len(ret_get_team_progress) > 0:
            values_view = ret_get_team_progress.values()
            value_iterator = iter(values_view)
            first_team = next(value_iterator)
            if type(first_team) == str:
                goutils.log2("ERR", "get_team_progress has returned an error: "+first_team)
                return 1,  first_team, None
            player_name = first_team[0][1][4]
            ret_print_vtx += "**Joueur : " + player_name + "**\n"

        for team in ret_get_team_progress:
            ret_team = ret_get_team_progress[team]

            #If only one team, display the detais
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
                    if tw_mode:
                        image_mode = "TW"
                    else:
                        image_mode = ""
                    e, t, images = await get_character_image(list_char_allycodes, True, False, image_mode, server_id)

    print("eeee", flush=True)
    #In case of several teams, don't display images
    if len(ret_get_team_progress) > 1:
        images = None

    return 0, ret_print_vtx, images

def print_fegv(txt_allyCode):
    query = "SELECT gt.name, unit_id, rarity_reco, rarity FROM guild_teams as gt " \
          + "JOIN guild_subteams as gst ON gst.team_id=gt.id " \
          + "JOIN guild_team_roster as gtr ON gtr.subteam_id=gst.id " \
          + "LEFT JOIN roster ON (unit_id=defId AND allyCode="+txt_allyCode+") " \
          + "WHERE gt.name IN( " \
          + "SELECT DISTINCT(gt.name) FROM guild_teams as gt " \
          + "JOIN guild_subteams as gst ON gst.team_id=gt.id " \
          + "JOIN guild_team_roster as gtr ON gtr.subteam_id=gst.id " \
          + "LEFT JOIN roster ON (gt.name=CONCAT(defId, '-GV') AND allyCode="+txt_allyCode+") " \
          + "WHERE gt.name LIKE '%-GV' " \
          + "AND (isnull(rarity) OR rarity<GVrarity) " \
          + ") " \
          + "AND (isnull(rarity) OR rarity<rarity_reco) "
    goutils.log2("DBG", query)
    ret_db = connect_mysql.get_table(query)
    dict_unitsList = godata.get("unitsList_dict.json")

    ret_print_fegv = ""
    for line in ret_db:
        gv_target_id = line[0][:-3]
        gv_target_name = dict_unitsList[gv_target_id]['name']
        character_id = line[1]
        character_name = dict_unitsList[character_id]['name']
        character_display = "["+gv_target_name+"] "+character_name+" "+str(line[3])+"/"+str(line[2])+" étoiles"

        for event in dict_unitsList[character_id]['farmingInfo']:
            if event[0].startswith('C01'):
                if event[0][3:] == 'L':
                    color_emoji = "\N{Large Yellow Circle}"
                elif event[0][3:] == 'D':
                    color_emoji = "\N{Large Yellow Circle}"
                elif event[0][3:] == 'H':
                    color_emoji = "\N{LARGE RED CIRCLE}"
                elif event[0][3:] == 'SP':
                    color_emoji = "\N{LARGE BLUE CIRCLE}"
                else:
                    color_emoji = None

                if event[1] == 1:
                    speed_emoji = "x1"
                elif event[1] == 2:
                    speed_emoji = "x2"
                else:
                    speed_emoji = None

                if color_emoji!=None and speed_emoji!=None:
                    character_display += " > farming en "+color_emoji+speed_emoji
        ret_print_fegv += character_display+"\n"

    return 0, ret_print_fegv

async def print_ftj(txt_allyCode, team, server_id):
    ret_print_ftj = ""

    player_name, ret_get_team_progress = await get_team_progress([team], txt_allyCode, server_id, 0, None, 2, {})
    #print(team)
    #print(ret_get_team_progress)
    if type(ret_get_team_progress) == str:
        return 1, ret_get_team_progress

    list_lines = []

    if not team in ret_get_team_progress:
        return 1, "Team "+team+" not defined"

    ret_team = ret_get_team_progress[team]
    #print(ret_get_team_progress)
    if type(ret_team) == str:
        #error
        ret_print_ftj += ret_team
    else:
        for [player_score, unlocked, player_txt, player_nogo, player_name, list_char] in ret_team[0]:
            ret_print_ftj += "Progrès de farm de la team "+team+" pour "+player_name+"\n"
            ret_print_ftj += player_txt + "> Global: "+ str(int(player_score))+"%"
            connect_mysql.update_gv_history(txt_allyCode, "", "FARM", True,
                                            player_score, unlocked, "go.bot")

    return 0, ret_print_ftj

async def print_gvj(list_team_names, txt_allyCode):
    ret_print_gvj = ""

    player_name, ret_get_team_progress = await get_team_progress(list_team_names, txt_allyCode, BOT_GFILE, 0, None, 1, {})
    if type(ret_get_team_progress) == str:
        return 1, ret_get_team_progress

    list_lines = []
    if len(ret_get_team_progress) == 1:
        #one team only, one player
        team = list(ret_get_team_progress.keys())[0]
        character_id = team[:-3]
        ret_team = ret_get_team_progress[team]
        if type(ret_team) == str:
            #error
            ret_print_gvj += ret_team
        else:
            for [player_score, unlocked, player_txt, player_nogo, player_name, list_char] in ret_team[0]:
                ret_print_gvj += "Progrès dans le Guide de Voyage pour "+player_name+" - "+character_id+"\n"
                ret_print_gvj += "(Les persos avec -- ne sont pas pris en compte pour le score)\n"
                ret_print_gvj += player_txt + "> Global: "+ str(int(player_score))+"%"
                connect_mysql.update_gv_history(txt_allyCode, "", character_id, True,
                                                player_score, unlocked, "go.bot")

    else:
        #Several tams
        player_name = ''
        for team in ret_get_team_progress:
            ret_team = ret_get_team_progress[team]
            character_id = team[:-3]
            if type(ret_team) == str:
                #error
                ret_print_gvj += ret_team
            else:
                for [player_score, player_unlocked, player_txt, player_nogo, player_name, list_char] in ret_team[0]:
                    new_line = character_id + " - "+ player_name + ": " + \
                                    str(int(player_score)) + "%\n"
                    list_lines.append([player_score, new_line, player_unlocked])
                    connect_mysql.update_gv_history(txt_allyCode, "", character_id, True,
                                                    player_score, player_unlocked, "go.bot")
                                            
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
                        
async def print_gvg(list_team_names, txt_allyCode):
    ret_print_gvg = ""

    guild_name, ret_get_team_progress = await get_team_progress(list_team_names, txt_allyCode, BOT_GFILE, 1, None, 1, {})

    if type(ret_get_team_progress) == str:
        return 1, ret_get_team_progress

    list_lines = []
    for team in ret_get_team_progress:
        ret_team = ret_get_team_progress[team]
        character_id = team[:-3]
        if type(ret_team) == str:
            #error
            ret_print_gvg += ret_team + "\n"
        else:
            for [player_score, player_unlocked, player_txt, player_nogo, player_name, list_char] in ret_team[0]:
                if not player_unlocked:
                    new_line = character_id + " - "+ player_name + ": " + \
                                    str(int(player_score)) + "%\n"
                    list_lines.append([player_score, new_line, player_unlocked])
                    if not player_unlocked and player_score>80:
                        connect_mysql.update_gv_history("", player_name, character_id, True,
                                                        player_score, player_unlocked, "go.bot")

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

async def print_gvs(list_team_names, txt_allyCode):
    ret_print_gvs = ""

    guild_name, ret_get_team_progress = await get_team_progress(list_team_names, txt_allyCode, BOT_GFILE, 2, None, 1, {})

    if type(ret_get_team_progress) == str:
        return 1, ret_get_team_progress

    list_lines = []
    for team in ret_get_team_progress:
        ret_team = ret_get_team_progress[team]
        character_id = team[:-3]
        if type(ret_team) == str:
            #error
            ret_print_gvs += ret_team + "\n"
        else:
            for [player_score, player_unlocked, player_txt, player_nogo, player_name, list_char] in ret_team[0]:
                if not player_unlocked:
                    new_line = character_id + " - "+ player_name + ": " + \
                                    str(int(player_score)) + "%\n"
                    list_lines.append([player_score, new_line, player_unlocked])
                    if not player_unlocked and player_score>80:
                        connect_mysql.update_gv_history("", player_name, character_id, True,
                                                        player_score, player_unlocked, "go.bot")

    list_lines = sorted(list_lines, key=lambda x: -x[0])
    ret_print_gvs += "Progrès dans le Guide de Voyage pour le shard (top "+str(MAX_GVG_LINES)+")\n"
    ret_print_gvs += "(seuls les joueurs qui n'ont pas le perso au max sont listés)\n"
    if len(list_lines) > 0:
        for [score, txt, unlocked] in list_lines[:MAX_GVG_LINES]:
            if score > 95:
                ret_print_gvs += "\N{WHITE RIGHT POINTING BACKHAND INDEX}"
            elif score > 80:
                ret_print_gvs += "\N{CONFUSED FACE}"
            else:
                ret_print_gvs += "\N{UP-POINTING RED TRIANGLE}"
            ret_print_gvs += txt
        
        not_displayed_count = max(0, len(list_lines) - MAX_GVG_LINES)
        if not_displayed_count > 0:
            ret_print_gvs += "... et encore "+str(not_displayed_count)+" lignes mais ça fait trop à afficher"
    else:
        ret_print_gvs += "... sauf que tout le monde l'a \N{SMILING FACE WITH HEART-SHAPED EYES}"
        
    return 0, ret_print_gvs
                       
#########################################"
# IN tw_zone: name of the TW zone to filter the players (other guild) - only for compute_guild=True
#########################################"
async def print_character_stats(characters, options, txt_allyCode, compute_guild, server_id, tw_zone):
    dict_unitsList = godata.get("unitsList_dict.json")
    ret_print_character_stats = ''

    list_stats_for_display=[['speed', "Vit"],
                            ['physical damages', "DegPhy"],
                            ['special damages', "DegSpé"],
                            ['health', " Santé"],
                            ['protection', "Protec"],
                            ['potency', "Pouvoir"],
                            ['tenacity', "Ténacité"],
                            ['critical damages', "DegCrit"],
                            ['physical critical chance', "PhyCdC "]]

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
                            if (char_relic<0) or (char_relic>9):
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
                            if (char_relic<0) or (char_relic>9):
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
        e, t, dict_player = await load_player(txt_allyCode, 1, False)
        player_name = dict_player["name"]
        list_player_names = [player_name]

        if e != 0:
            #error wile loading guild data
            return 'ERREUR: joueur non trouvé pour code allié ' + txt_allyCode
        
        #Manage request for all characters
        if 'all' in characters:
            dict_stats = {player_name: dict_player["rosterUnit"]}
            list_character_ids=list(dict_player["rosterUnit"].keys())
            
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

                        dict_player["rosterUnit"][character_id]["level"] = 85
                        if virtual_rarity != None:
                            dict_player["rosterUnit"][character_id]["rarity"] = virtual_rarity
                        if dict_unitsList[character_id]["combatType"] == 1:
                            if virtual_gear != None:
                                    dict_player["rosterUnit"][character_id]["gear"] = virtual_gear
                            if virtual_relic != None:
                                dict_player["rosterUnit"][character_id]["relic"]["currentTier"] = virtual_relic +2
                
                #Recompute stats with Crinolo API
                dict_player = goutils.roster_from_dict_to_list(dict_player)
                err_code, err_txt, dict_player = connect_crinolo.add_stats(dict_player)
                dict_player = goutils.roster_from_list_to_dict(dict_player)

            dict_stats = {player_name: dict_player["rosterUnit"]}

        
        ret_print_character_stats += "Statistiques pour "+player_name
        if sort_option_id == 0:
            ret_print_character_stats += " (tri par nom)\n"
        else:
            sort_option_full_name = dict_stat_names[sort_option_name][2]
            ret_print_character_stats += " (tri par "+sort_option_full_name+")\n"


    elif len(characters) == 1 and characters[0] != "all" and not characters[0].startswith("tag:"):
        #Compute stats at guild level, only one character
        
        #Get character_id
        character_alias = characters[0]
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([character_alias])
        if txt != '':
            return 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt
        character_id = list_character_ids[0]

        #if tw_zone is set, need to find the txt_allyCode by using the TW opponent
        if tw_zone != None:
            #Check if the guild can use RPC
            if not server_id in connect_rpc.get_dict_bot_accounts():
                return "ERR: cannot detect TW opponent in this server"

            rpc_data = await connect_rpc.get_tw_status(server_id, True)
            tw_id = rpc_data[0]
            if tw_id == None:
                return "ERR: no TW ongoing"

            list_opponent_squads = rpc_data[2][0]
            tuple_opp_players = tuple(set([x[1] for x in list_opponent_squads]))

            #get one allyCode from opponent guild
            query = "SELECT allyCode FROM players "
            query+= "WHERE name in "+str(tuple_opp_players)+" "
            query+= "GROUP BY guildName ORDER BY count(*) DESC LIMIT 1"
            goutils.log2("DBG", query)
            db_data = connect_mysql.get_value(query)
            if db_data == None:
                return "ERR: la guilde adverse n'a pas été entrée dans le bot"
            txt_allyCode = str(db_data)

            #filter the players that needs to be displayed
            dict_tw_zone_players = {}
            for team in list_opponent_squads:
                zone=team[0]
                if tw_zone=="all" or zone==tw_zone:
                    team_char_ids = team[2]
                    if character_id in team_char_ids:
                        team_player_name = team[1]
                        dict_tw_zone_players[team_player_name] = zone

        #Get data for the guild and associated players
        err_code, err_txt, guild = await load_guild(txt_allyCode, True, True)
        if err_code != 0:
            return "ERR: cannot get guild data from SWGOH.HELP API"
                            
        db_stat_data_char = []
        goutils.log2("INFO", "Get guild_data from DB...")
        query = "SELECT players.name, defId, "\
               +"roster.combatType, rarity, gear, relic_currentTier, "\
               +"stat1, "\
               +"stat5, "\
               +"stat6, "\
               +"stat7, "\
               +"stat14, "\
               +"stat16, "\
               +"stat17, "\
               +"stat18, "\
               +"stat28 "\
               +"FROM roster "\
               +"JOIN players ON players.allyCode = roster.allyCode "\
               +"WHERE players.guildName = (SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"') "\
               +"AND defId = '"+character_id+"' "\
               +"ORDER BY players.name, defId"

        goutils.log2("DBG", query)
        db_stat_data = connect_mysql.get_table(query)
        if db_stat_data == None:
            return "ERR: aucune donnée trouvée"

        list_character_ids=[character_id]
        list_player_names=set([x[0] for x in db_stat_data])
        character_name = dict_id_name[character_alias][0][1]
        
        ret_print_character_stats += "Statistiques pour "+character_name
        if tw_zone!=None:
            ret_print_character_stats += " en GT"
            if tw_zone!="all":
                ret_print_character_stats += " sur la zone "+tw_zone

        if sort_option_id == 0:
            ret_print_character_stats += " (tri par nom)\n"
        else:
            sort_option_full_name = dict_stat_names[sort_option_name][2]
            ret_print_character_stats += " (tri par "+sort_option_full_name+")\n"
    
        # Generate dict from DB data
        dict_stats = goutils.create_dict_stats(db_stat_data_char, db_stat_data)
    else:
        return "ERR: les stats au niveau guilde ne marchent qu'avec un seul perso à la fois"
    

    # Create all lines before display
    list_print_stats=[]
    for player_name in list_player_names:
        if tw_zone!=None and not player_name in dict_tw_zone_players:
            continue

        if player_name in dict_stats:
            dict_player = dict_stats[player_name]
        else:
            dict_player={}
        for character_id in list_character_ids:
            if character_id in dict_player:
                character_name = dict_unitsList[character_id]["name"]
                character_rarity = str(dict_player[character_id]["currentRarity"])+"*"
                character_gear = dict_player[character_id]["currentTier"]
                if dict_unitsList[character_id]["combatType"] == 1:
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
                    if tw_zone == None:
                        line_header = player_name
                    else:
                        line_header = dict_tw_zone_players[player_name]+":"+player_name
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

def get_distribution_graph(values, values_2, bin_count, title, x_title, y_title, legend, legend_2, highlight_value):
    fig, ax = plt.subplots()

    #pre-calculate bins to align histograms
    if values_2 != None:
        bins=np.histogram(np.hstack((values, values_2)), bins=bin_count)[1]
        bin_count = len(bins)
    else:
        bins = bin_count

    # 1st hist
    ax.hist(values, bins=bins, color='blue', label=legend)

    # 2nd hist
    if values_2 != None:
        ax.hist(values_2, bins=bins, label=legend_2, color='lightblue')

    # legend
    if legend!='' or legend_2!='':
        ax.legend(loc='upper right')

    # titles
    fig.suptitle(title)
    ax.set_xlabel(x_title)
    ax.set_ylabel(y_title)

    if highlight_value != None:
        min_x = plt.xlim()[0]
        max_x = plt.xlim()[1]
        bin_width = (max_x - min_x) / bin_count
        plt.axvspan(highlight_value - bin_width/2,
                    highlight_value + bin_width/2,
                    color='red', alpha = 0.5)

    fig.canvas.draw()
    fig_size = fig.canvas.get_width_height()
    fig_bytes = fig.canvas.tostring_rgb()
    image = Image.frombytes('RGB', fig_size, fig_bytes)

    return image

async def get_gp_distribution(txt_allyCode):
    #Load or update data for the guild
    #use only the guild data from the API
    err_code, err_txt, dict_guild = await load_guild(txt_allyCode, False, True)
    if err_code != 0:
        return 1, "ERR: cannot get guild data from SWGOH.HELP API", None

    guild_stats=[] #Serie of all players
    for player in dict_guild["member"]:
        gp = int(player['galacticPower']) / 1000000
        guild_stats.append(gp)
    guild_name = dict_guild["profile"]["name"]

    graph_title = "GP stats " + guild_name + " ("+str(len(guild_stats))+" joueurs)"

    #compute ASCII graphs
    image = get_distribution_graph(guild_stats, None, 20, graph_title, "PG du joueur", "nombre de joueurs", "", "", None)
    logo_img= portraits.get_guild_logo(dict_guild, (80, 80))
    image.paste(logo_img, (10,10), logo_img)
    
    return 0, "", image

#################################
# Function: get_character_image
# IN: list_characters_allyCode: [[[[id1, unavail], [id2, unavail], ...], allyCode, tw territory], ...]
# IN: is_ID: True if list_character_alyCode contains chartacter IDs (False if names)
# IN: refresh_player: False to prevent refreshing player via API
# IN: game_mode: 'TW', 'TB', ... or '' for undefined
# return: err_code, err_txt, image
#################################
async def get_character_image(list_characters_allyCode, is_ID, refresh_player, game_mode, server_id):
    err_code = 0
    err_txt = ''

    #Get data for all players
    #print(list_characters_allyCode)
    list_allyCodes = list(set([x[1] for x in list_characters_allyCode]))

    #Get reserved TW toons
    if game_mode == "TW":
        ec, et, dict_def_toon_player = await get_tw_defense_toons(server_id, False)
        if ec != 0:
            return 1, et, None
    
    #transform aliases into IDs
    if not is_ID:
        list_alias = [j for i in [x[0] for x in list_characters_allyCode] for j in i]
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_alias)
        if txt != '':
            err_txt += 'WAR: impossible de reconnaître ce(s) nom(s) >> '+txt+"\n"

    list_ids_dictplayer = []
    for [characters, txt_allyCode, tw_terr] in list_characters_allyCode:
        # refresh_player = True  > load_player(force_update=1)
        # refresh_player = False > load_player(force_update=-1)
        e, t, dict_player = await load_player(txt_allyCode, 2*int(refresh_player)-1, False)

        #Tag reserved characters
        if game_mode == "TW":
            player_name = dict_player['name']
            for char_id in dict_player["rosterUnit"]:
                dict_player["rosterUnit"][char_id]['reserved'] = False
                if char_id in dict_def_toon_player:
                    if player_name in dict_def_toon_player[char_id]:
                        dict_player["rosterUnit"][char_id]['reserved'] = True

        if e != 0:
            #error wile loading guild data
            goutils.log2("WAR", "joueur non trouvé pour code allié " + txt_allyCode)
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
        image = portraits.get_image_from_team(ids, dict_player, tw_terr, game_mode)
        list_images.append(image)
    
    return err_code, err_txt, list_images

#################################
# Function: get_tw_battle_images
# return: err_code, err_txt, list of images
#################################
async def get_tw_battle_image(list_char_attack, allyCode_attack, \
                        character_defense, server_id):
    war_txt = ""

    dict_unitsList = godata.get("unitsList_dict.json")

    #Check if the guild can use RPC
    if not server_id in connect_rpc.get_dict_bot_accounts():
        return []

    query = "SELECT name, twChanOut_id FROM guild_bot_infos "
    query+= "JOIN guilds on guilds.id = guild_bot_infos.guild_id "
    query+= "WHERE server_id="+str(server_id)
    goutils.log2('DBG', query)
    db_data = connect_mysql.get_line(query)

    guildName = db_data[0]
    twChannel_id = db_data[1]
    if twChannel_id == 0:
        return 1, "ERR: commande inutilisable sur ce serveur\n", None

    rpc_data = await connect_rpc.get_tw_status(server_id, True)
    tw_id = rpc_data[0]
    if tw_id == None:
        return 1, "ERR: aucune GT en cours\n", None

    list_opponent_squads = rpc_data[2][0]
    if len(list_opponent_squads) == 0:
        goutils.log2("ERR", "aucune phase d'attaque en cours en GT")
        return 1, "ERR: aucune phase d'attaque en cours en GT\n", None

    guildName = rpc_data[3][0]

    #Get full character names for attack
    list_id_attack, dict_id_name, txt = goutils.get_characters_from_alias(list_char_attack)
    if txt != '':
        war_txt += 'WAR: impossible de reconnaître ce(s) nom(s) >> '+txt+"\n"

    #Get full character name for defense
    list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([character_defense])
    if txt != '':
        war_txt += 'WAR: impossible de reconnaître ce(s) nom(s) >> '+txt+"\n"
    char_def_id = list_character_ids[0]

    list_opp_squad_ids = []
    for opp_squad in list_opponent_squads:
        territory = opp_squad[0]
        player_name = opp_squad[1]
        squad_char_ids = opp_squad[2]
        list_opp_squad_ids.append([territory, player_name, squad_char_ids])

    list_opp_squads_with_char = list(filter(lambda x:char_def_id in x[2], list_opp_squad_ids))
    if len(list_opp_squads_with_char) == 0:
        return 1, 'ERR: '+character_defense+' ne fait pas partie des teams en défense\n', None

    # Look for the name among known player names in DB
    query = "SELECT name, allyCode "
    query+= "FROM players "
    query+= "WHERE guildName='"+guildName.replace("'", "''")+"' "
    query+= "ORDER BY name"
    goutils.log2("DBG", query)
    results = connect_mysql.get_table(query)
    list_DB_names = [x[0] for x in results]

    for opp_squad in list_opp_squads_with_char:
        player_name = opp_squad[1]

        closest_names=difflib.get_close_matches(player_name, list_DB_names, 1)
        #print(closest_names)
        if len(closest_names)<1:
            goutils.log2("ERR", player_name+' ne fait pas partie des joueurs connus de la guilde '+guildName)
            return 1, 'ERR: '+player_name+' ne fait pas partie des joueurs connus\n', None
        else:
            goutils.log2("INFO", "cmd launched with name that looks like "+closest_names[0])
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
    ec, et, images = await get_character_image(list_char_allycodes, True, False, 'TW', server_id)
    if ec != 0:
        return 1, et, None

    return 0, war_txt, images

async def get_stat_graph(txt_allyCode, character_alias, stat_name):
    err_txt = ""

    e, t, d = await load_player(txt_allyCode, 1, False)
    if e != 0:
        return 1, "ERR: cannot get player data from SWGOH.HELP API", None
        
    #get the relic filter if any
    if ":" in character_alias:
        tab_alias = character_alias.split(":")
        character_alias = tab_alias[0]
        relic_txt = tab_alias[1]
        if relic_txt[0].lower() != "r":
            return 1, "ERR: syntaxe incorrecte pour le filtre relic", None

        # check for R7+ or R7-
        if relic_txt[-1] == "+":
            relic_filter = ">="
            relic_num = relic_txt[:-1]
        elif relic_txt[-1] == "-":
            relic_filter = "<="
            relic_num = relic_txt[:-1]
        else:
            relic_filter = "="
            relic_num = relic_txt

        if not relic_num[1:].isnumeric():
            return 1, "ERR: syntaxe incorrecte pour le filtre relic", None
        relic = int(relic_num[1:])
        if relic<0 or relic>9:
            return 1, "ERR: syntaxe incorrecte pour le filtre relic", None
    else:
        #default filter R0+
        relic_txt = "R0+"
        relic_filter = ">="
        relic = 0

    #Get character_id
    list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([character_alias])
    if txt != '':
        return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt, None
            
    character_id = list_character_ids[0]
    character_name = dict_id_name[character_alias][0][1]
    player_name = d["name"]
    guild_name = d["guildName"]

    #Get statistic id
    closest_names=difflib.get_close_matches(stat_name.lower(), dict_stat_names.keys(), 1)
    if len(closest_names)<1:
        return 1, 'ERR: '+stat_name+' ne fait pas partie des stats connues '+str(list(dict_stat_names.keys())), None

    goutils.log2("INFO", "cmd launched with stat name that looks like "+closest_names[0])
    stat_name = closest_names[0]
    stat_id = dict_stat_names[stat_name][0]
    stat_isPercent = dict_stat_names[stat_name][1]
    stat_frName = dict_stat_names[stat_name][2]
    stat_string = "stat"+str(stat_id)

    #Get data from DB
    db_stat_data_char = []
    goutils.log2("INFO", "Get player data from DB...")
    query = "SELECT r.allyCode, gear, combatType,"\
           +stat_string+", guildName "\
           +"FROM roster AS r "\
           +"JOIN players ON players.allyCode = r.allyCode "\
           +"WHERE defId = '"+character_id+"' "\
           +"AND not "+stat_string+"=0 " \
           +"AND ((gear=13 and relic_currentTier "+relic_filter+str(relic+2)+") or r.allyCode = "+txt_allyCode+" or combatType=2)"
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_table(query)

    if stat_isPercent:
        stat_divider = 1000000
    else:
        stat_divider = 100000000

    stat_g13_values = [x[3]/stat_divider for x in db_data if (x[1]==13 or x[2]==2)]
    player_values = [x[3]/stat_divider for x in db_data if x[0]==int(txt_allyCode)]
    if len(player_values) > 0:
        if stat_isPercent:
            player_value = int(100*player_values[0])/100
        else:
            player_value = int(player_values[0])
    else:
        goutils.log2("WAR", "Character "+character_alias+" is locked for "+txt_allyCode)
        err_txt +="WAR: Le perso "+character_alias+" n'est pas débloqué pour "+txt_allyCode
        player_value = None
    if guild_name != "":
        guild_values = [x[3]/stat_divider for x in db_data if x[4]==guild_name]
    else:
        guild_values = None

    # Draw graph
    title = stat_frName + " de " + character_name + " (" + str(player_value) + ") pour "+player_name+"\n"
    title+= "comparée aux " + str(len(stat_g13_values)) + " " + character_name + " "+relic_txt+" connus"

    image = get_distribution_graph(stat_g13_values, guild_values, 50, title, "valeur de la stat", "nombre de persos", "tous", guild_name, player_value)

    return 0, err_txt, image

###############################
async def print_lox(txt_allyCode, characters, compute_guild):
    war_txt = ""

    dict_capa = godata.get("unit_capa_list.json")
    all_modes = []
    for unit_id in dict_capa:
        unit = dict_capa[unit_id]
        has_omicron = False
        for ability_id in unit:
            ability = unit[ability_id]
            if ability["omicronTier"] < 99:
                all_modes.append(ability["omicronMode"])
    all_modes = set(all_modes)

    if 'all' in characters:
        #Manage request for all characters
        get_all = True
    else:
        get_all = False

        #look for omicron tag
        non_mode_characters = []
        list_modes = []
        for unit in characters:
            print(unit)
            if unit.startswith("mode:"):
                unit_tab = unit.split(":")
                if len(unit_tab)>2:
                    return 1, "ERR: syntax incorrecte pour le mode omicron "+unit, None
                mode = unit_tab[1]
                if not mode in all_modes:
                    return 1, "ERR: mode omicron inconnu "+mode+" parmi "+str(all_modes), None
                list_modes.append(mode)

                #manage GA combinations
                if mode=='GA':
                    list_modes.append("GA3")
                    list_modes.append("GA5")
                elif mode=='GA3':
                    list_modes.append("GA")
                elif mode=='GA5':
                    list_modes.append("GA")
            else:
                non_mode_characters.append(unit)
                
        #specific list of characters for one player
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(non_mode_characters)
        if txt != '':
            return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt, None
        for unit_id in list_character_ids:
            unit = dict_capa[unit_id]
            has_omicron = False
            for ability_id in unit:
                ability = unit[ability_id]
                if ability["omicronTier"] < 99:
                    has_omicron = True
                    break
            if not has_omicron:
                war_txt += "WAR: pas d'omicron connu pour "+dict_id_name[unit_id] + "\n"

        if len(list_character_ids)==0 and len(list_modes)==0:
            return 1, "ERR: aucun personnage ni aucun mode omicron défini", None

    #GET DATA FROM PLAYER OR GUILD
    if compute_guild:
        err_code, err_txt, guild = await load_guild(txt_allyCode, True, True)
        if err_code != 0:
            return 1, 'ERR: guilde non trouvée pour code allié ' + txt_allyCode, []
    else:
        #Get data for this player
        e, t, d = await load_player(txt_allyCode, 1, False)
        if e != 0:
            return 1, 'ERR: joueur non trouvé pour code allié ' + txt_allyCode, []

    query = "SELECT players.name AS 'joueur', defId AS 'perso', roster_skills.name AS 'type', "
    query+= "CASE WHEN gear=13 THEN CONCAT(rarity, '*R', relic_currentTier-2) "
    query+= "ELSE CONCAT(rarity, '*G', gear) END AS 'gear', "
    query+= "omicron_type as 'mode' FROM roster "
    query+= "JOIN roster_skills ON roster_id = roster.id \n"
    query+= "JOIN players ON players.allyCode=roster.allyCode \n"
    query+= "WHERE (roster_skills.omicron_tier>0 AND roster_skills.level>=roster_skills.omicron_tier) \n"
    if not get_all:
        query+= "AND ( \n"
        if len(list_character_ids)>0:
            query+= "    defId IN "+str(tuple(list_character_ids)).replace(",)", ")")+" \n"
        else:
            query+= "    0 \n"
        query+= "    OR\n"
        if len(list_modes)>0:
            query+= "    omicron_type IN "+str(tuple(list_modes)).replace(",)", ")")+" \n"
        else:
            query+= "    0 \n"
        query+= ") \n"
    if compute_guild:
        query+= "AND guildName=(SELECT guildName FROM players WHERE allyCode="+txt_allyCode+") \n"
    else:
        query+= "AND players.allyCode="+txt_allyCode+" \n"
    query+= "ORDER BY omicron_type, defId, players.name"
    goutils.log2("DBG", query)

    db_lines = connect_mysql.text_query(query)
    return 0, war_txt, db_lines

###############################
async def print_erx(txt_allyCode, days, compute_guild):
    dict_unitsList = godata.get("unitsList_dict.json")
    dict_categoryList = godata.get("categoryList_dict.json")

    #Recuperation des dernieres donnees sur gdrive
    list_teams, dict_teams = connect_gsheets.load_config_teams(BOT_GFILE, False)

    if not compute_guild:
        query = "SELECT guildName, name, defId, timestamp FROM roster_evolutions " \
              + "JOIN players ON players.allyCode = roster_evolutions.allyCode " \
              + "WHERE players.allyCode = " + txt_allyCode + " " \
              + "AND timestampdiff(DAY, timestamp, CURRENT_TIMESTAMP)<=" + str(days) + " " \
              + "ORDER BY timestamp DESC"
    else:
        query = "SELECT guildName, name, defId, timestamp FROM roster_evolutions " \
              + "JOIN players ON players.allyCode = roster_evolutions.allyCode " \
              + "WHERE players.allyCode IN (SELECT allyCode FROM players WHERE guildName = (SELECT guildName FROM players WHERE allyCode="+txt_allyCode+")) "\
              + "AND timestampdiff(DAY, timestamp, CURRENT_TIMESTAMP)<=" + str(days) + " " \
              + "ORDER BY timestamp DESC"

    goutils.log2("DBG", query)
    db_data_evo = connect_mysql.get_table(query)

    if not compute_guild:
        query = "SELECT name, defId FROM roster " \
              + "JOIN players ON players.allyCode = roster.allyCode " \
              + "WHERE players.allyCode = " + txt_allyCode + " " \
              + "AND combatType=2"
    else:
        query = "SELECT name, defId FROM roster " \
              + "JOIN players ON players.allyCode = roster.allyCode " \
              + "WHERE players.allyCode IN (SELECT allyCode FROM players WHERE guildName = (SELECT guildName FROM players WHERE allyCode="+txt_allyCode+")) " \
              + "AND combatType=2"

    goutils.log2("DBG", query)
    db_data_ships = connect_mysql.get_table(query)
    dict_ships = {}
    if db_data_ships != None:
        for line in db_data_ships:
            player_name=line[0]
            char_id=line[1]
            if not player_name in dict_ships:
                dict_ships[player_name] = []
            dict_ships[player_name].append(char_id)

    if not compute_guild:
        query = "SELECT players.name, defId FROM roster " \
              + "JOIN players ON players.allyCode = roster.allyCode " \
              + "JOIN guild_teams ON (" \
              + "    defId=LEFT(guild_teams.name, LENGTH(guild_teams.name) - 3) " \
              + "    AND rarity>=GVrarity) " \
              + "WHERE players.allyCode = " + txt_allyCode
    else:
        query = "SELECT players.name, defId FROM roster " \
              + "JOIN players ON players.allyCode = roster.allyCode " \
              + "JOIN guild_teams ON (" \
              + "    defId=LEFT(guild_teams.name, LENGTH(guild_teams.name) - 3) " \
              + "    AND rarity>=GVrarity) " \
              + "WHERE players.allyCode IN (" \
              + "    SELECT allyCode FROM players " \
              + "    WHERE guildName = (" \
              + "        SELECT guildName " \
              + "        FROM players " \
              + "        WHERE allyCode="+txt_allyCode+"))"

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
            await asyncio.sleep(0)

            player_name = line[1]
            unit_id = line[2]
            if unit_id != "all":
                if unit_id in dict_unitsList:
                    unit_name = dict_unitsList[unit_id]["name"]
                else:
                    unit_name = unit_id

                if unit_id in stats_units:
                    stats_units[unit_id][1] += 1
                else:
                    stats_units[unit_id] = [unit_name, 1]

                if unit_id in dict_unitsList:
                    if "categoryId" in dict_unitsList[unit_id]:
                        unit_categories = dict_unitsList[unit_id]["categoryId"]
                    else:
                        unit_categories = []

                    if "ships" in dict_unitsList[unit_id]:
                        unit_ships = dict_unitsList[unit_id]["ships"]
                    else:
                        unit_ships = []
                else:
                    unit_categories = []
                    unit_ships = []

                for category in unit_categories:
                    if category in dict_categoryList:
                        category_name = dict_categoryList[category]["descKey"]
                        if category in stats_categories:
                            stats_categories[category][1] += 1
                        else:
                            stats_categories[category] = [category_name, 1]

                for [ship_id, ship_name] in unit_ships:
                    if player_name in dict_ships and ship_id in dict_ships[player_name]:
                        if ship_id in stats_units:
                            stats_units[ship_id][1] += 1
                        else:
                            stats_units[ship_id] = [ship_name, 1]

                for char_gv_id in dict_teams_gv:
                    if player_name in dict_gv_done:
                        if char_gv_id in dict_gv_done[player_name]:
                            continue
                    if not char_gv_id in dict_unitsList:
                        return 1, "ERR: "+char_gv_id+" is defined in the GV but not in the unitsList"

                    char_gv_name = dict_unitsList[char_gv_id]["name"]
                    if unit_id in dict_teams_gv[char_gv_id]:
                        if char_gv_id in stats_gv:
                            stats_gv[char_gv_id][1] += 1
                        else:
                            stats_gv[char_gv_id] = [char_gv_name, 1]

                    for ship_id in unit_ships:
                        if ship_id in dict_teams_gv[char_gv_id]:
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
        ret_cmd += "1 évolution =  1 step de niveau (peut regrouper plusieurs steps si faits ensemble), de gear, de relic, 1 zeta en plus, déblocage du perso, monter le pilote d'un vaisseau\n"
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
async def print_raid_progress(txt_allyCode, server_id, raid_alias, use_mentions):
    dict_raids = connect_gsheets.load_config_raids(server_id, False)
    dict_raid_tiers = godata.dict_raid_tiers
    if raid_alias in dict_raids:
        raid_config = dict_raids[raid_alias]
    else:
        return 1, "ERR: unknown raid "+raid_alias+" among "+str(list(dict_raids.keys())), ""

    ec, et, dict_teams_by_player = await find_best_teams_for_raid(txt_allyCode, server_id, raid_alias, True)
    if ec != 0:
        return 1, et, ""
    dict_players_by_team = {}
    for player in dict_teams_by_player:
        for team in dict_teams_by_player[player][0]:
            if not team in dict_players_by_team:
                dict_players_by_team[team] = []
            dict_players_by_team[team].append(player)

    query = "SELECT name FROM guilds "
    query+= "JOIN guild_bot_infos ON guild_bot_infos.guild_id = guilds.id "
    query+= "WHERE server_id = "+str(server_id)
    guild_name = connect_mysql.get_value(query)

    if guild_name == None:
        return 1, "ERR: Guidle non définie dans le bot", ""

    raid_name = raid_config[0]
    raid_teams = raid_config[1]
    #sort team names by phase, then by name
    raid_team_names = list({k: v for k, v in sorted(raid_teams.items(),
                                                    key=lambda item: (
                                                        item[1][0], item[0]))}.keys())
    raid_phase, raid_scores = connect_warstats.parse_raid_scores(server_id, raid_name)

    #Player lines
    dict_players_by_IG = connect_mysql.load_config_players()[0]
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

        #Check if player is known in the guild
        if not player_name in dict_teams_by_player:
            if not player_name in list_unknown_players:
                list_unknown_players.append(player_name)

        normal_score = 0
        super_score = 0
        for team in raid_team_names:
            if team in dict_players_by_team:
                if player_name in dict_players_by_team[team]:
                    player_has_team = True
                else:
                    player_has_team = False
            else:
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
                if guild_score_by_phase[team_phase-1] > dict_raid_tiers[raid_name][team_phase-1]:
                    guild_score_by_phase[team_phase-1] = dict_raid_tiers[raid_name][team_phase-1]

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
    ret_print_raid_progress+= "S ({0:8}/{1:8}) {2:8}\n".format("Normal", "Super", "Score")

    #Display all players
    for line in list_scores:
        ret_print_raid_progress+= "{0:20}".format(line[0])
        for id in range(1, team_id):
            if line[id]:
                ret_print_raid_progress+= "X  "
            else:
                ret_print_raid_progress+= ".  "
            if id > 9:
                ret_print_raid_progress+= " "

        ret_print_raid_progress+= "{0:1} ({1:8}/{2:8}) {3:8}\n".format(
                                line[id+4],
                                line[id+2],
                                line[id+3],
                                line[id+1])

    #Display theoretical obtainable score and phase
    goutils.log2("DBG", "guild_score_by_phase = "+str(guild_score_by_phase))
    goutils.log2("DBG", "dict_raid_tiers = "+str(dict_raid_tiers))
    if guild_score_by_phase[0] < dict_raid_tiers[raid_name][0]:
        total_normal_score = guild_score_by_phase[0]
    elif guild_score_by_phase[1] < dict_raid_tiers[raid_name][1]:
        total_normal_score = sum(guild_score_by_phase[:2])
    elif guild_score_by_phase[2] < dict_raid_tiers[raid_name][2]:
        total_normal_score = sum(guild_score_by_phase[:3])
    else:
        total_normal_score = sum(guild_score_by_phase)

    if total_normal_score >= sum(dict_raid_tiers[raid_name]):
        normal_raid_phase = 5
    elif total_normal_score >= sum(dict_raid_tiers[raid_name][:3]):
        normal_raid_phase = 4
        normal_progress = (                  total_normal_score - sum(dict_raid_tiers[raid_name][:3]))/ \
                          (sum(dict_raid_tiers[raid_name]) - sum(dict_raid_tiers[raid_name][:3]))
    elif total_normal_score >= sum(dict_raid_tiers[raid_name][:2]):
        normal_raid_phase = 3
        normal_progress = (                      total_normal_score - sum(dict_raid_tiers[raid_name][:2]))/ \
                          (sum(dict_raid_tiers[raid_name][:3]) - sum(dict_raid_tiers[raid_name][:2]))
    elif total_normal_score >= dict_raid_tiers[raid_name][0]:
        normal_raid_phase = 2
        normal_progress = (                      total_normal_score - dict_raid_tiers[raid_name][0])/ \
                          (sum(dict_raid_tiers[raid_name][:2]) - dict_raid_tiers[raid_name][0])
    else:
        normal_raid_phase = 1
        normal_progress = total_normal_score / sum(dict_raid_tiers[raid_name])
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
async def print_tb_progress(txt_allyCode, server_id, tb_alias, use_mentions):
    list_tb_teams = connect_gsheets.load_tb_teams(server_id, False)
    tb_team_names = list(set(sum(sum([list(x.values()) for x in list_tb_teams], []), [])))
    tb_team_names.remove('')
    list_known_bt = list(set(sum([[y[0:3] for y in x.keys()] for x in list_tb_teams], [])))
    if not tb_alias in list_known_bt:
        return 1, "ERR: unknown BT", ""

    query = "SELECT warstats_id FROM guild_bot_infos "
    query+= "WHERE server_id = "+str(server_id)
    warstats_id = connect_mysql.get_value(query)

    if warstats_id == None or warstats_id == 0:
        return 1, "ERR: Guide non déclarée dans le bot", ""

    guild_name, dict_teams = await get_team_progress(tb_team_names, txt_allyCode, server_id, 1, None, 0, {})
    dict_teams_by_player = {}
    for team in dict_teams:
        dict_teams_by_player[team]={}
        for line in dict_teams[team][0][1:]:
            nogo = line[3]
            player_name = line[4]
            dict_teams_by_player[team][player_name] = not nogo

    # TODO move to RPC data
    #active_round, dict_player_scores, list_open_territories = \
    #        connect_warstats.parse_tb_player_scores(server_id, tb_alias, True)

    if tb_alias[0] == "H":
        tb_day_count = 6
    else:
        tb_day_count = 4

    #Player lines
    dict_players_by_IG = connect_mysql.load_config_players()[0]
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

############################################
# get_tw_alerts
# IN - server_id (equivalent to guild id)
# OUT - list_tw_alerts [twChannel_id, {territory1: alert_territory1,
#                                      territory2: alert_territory2...},
#                       tw_timestamp]]
############################################
async def get_tw_alerts(server_id, use_cache_data):
    dict_unitsList = godata.get("unitsList_dict.json")

    #Check if the guild can use RPC
    if not server_id in connect_rpc.get_dict_bot_accounts():
        return []

    query = "SELECT name, twChanOut_id FROM guild_bot_infos "
    query+= "JOIN guilds on guilds.id = guild_bot_infos.guild_id "
    query+= "WHERE server_id="+str(server_id)
    goutils.log2('DBG', query)
    db_data = connect_mysql.get_line(query)

    guildName = db_data[0]
    twChannel_id = db_data[1]
    if twChannel_id == 0:
        return []

    rpc_data = await connect_rpc.get_tw_status(server_id, use_cache_data)
    tw_id = rpc_data[0]
    if tw_id == None:
        return []

    tw_timestamp = tw_id.split(":")[1][1:]

    list_tw_alerts = [twChannel_id, {}, tw_timestamp]

    list_opponent_squads = rpc_data[2][0]
    list_opp_territories = rpc_data[2][1]
    if len(list_opponent_squads) > 0:
        list_opponent_players = [x[1] for x in list_opponent_squads]
        longest_opp_player_name = max(list_opponent_players, key=len)
        longest_opp_player_name = longest_opp_player_name.replace("'", "''")
        list_open_tw_territories = set([x[0] for x in list_opponent_squads])

        for territory in list_open_tw_territories:
            list_opp_squads_terr = [x for x in list_opponent_squads if (x[0]==territory and len(x[2])>0)]
            list_opp_remaining_squads_terr = [x for x in list_opponent_squads if (x[0]==territory and len(x[2])>0 and not x[3])]
            counter_leaders = Counter([x[2][0] for x in list_opp_squads_terr])
            counter_remaining_leaders = Counter([x[2][0] for x in list_opp_remaining_squads_terr])

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
                if leader in dict_unitsList:
                    leader_name = dict_unitsList[leader]["name"]
                else:
                    leader_name = leader
                msgleader = " - "+leader_name+": "+str(counter_remaining_leaders[leader])+"/"+str(counter_leaders[leader])
                if counter_remaining_leaders[leader] == 0:
                    msg += "\n~~"+msgleader+"~~"
                else:
                    msg += "\n"+msgleader

            list_tw_alerts[1][territory] = msg

    list_defense_squads = rpc_data[1][0]
    list_def_territories = rpc_data[1][1]
    list_full_territories = [t for t in list_def_territories if t[1]==t[2]]
    nb_full = len(list_full_territories)
    if len(list_def_territories) > 0:
        #Alert for defense fully set OR new orders
        for territory in list_def_territories:
            territory_name = territory[0]
            size = territory[1]
            filled = territory[2]
            orders = territory[5]

            n_territory = int(territory_name[1])
            if territory_name[0] == "T" and int(territory_name[1]) > 2:
                n_territory -= 2

            if n_territory == 1:
                territory_fullname = "__Le 1er territoire "
            else:
                territory_fullname = "__Le "+str(n_territory)+"e territoire "

            if territory_name[0] == "T" and int(territory_name[1]) < 3:
                territory_fullname += "du haut__"
            elif territory_name[0] == "T":
                territory_fullname += "du milieu__"
            elif territory_name[0] == "F":
                territory_fullname += "des vaisseaux__"
            else:
                territory_fullname += "du bas__"

            if size == filled:
                if orders == None:
                    txt_orders = ""
                else:
                    txt_orders = " - " + orders
                msg = "**DEFENSE** - "+territory_fullname+"("+territory_name+txt_orders+") "
                msg+= "est rempli ("+str(nb_full)+"/10)."

                if nb_full==10:
                    msg = '\N{WHITE HEAVY CHECK MARK}'+msg

                list_tw_alerts[1]["Placement:"+territory_name] = msg

            if orders != None:
                msg = "**DEFENSE** - "+territory_fullname+"("+territory_name+") "
                msg+= "a de nouveaux ordres : "+orders.strip()
                list_tw_alerts[1]["Ordres:"+territory_name] = msg

        #Alert for defense lost
        list_lost_territories = [t for t in list_def_territories if t[1]==t[3]]
        for territory in list_lost_territories:
            territory_name = territory[0]

            n_territory = int(territory_name[1])
            if territory_name[0] == "T" and int(territory_name[1]) > 2:
                n_territory -= 2

            if n_territory == 1:
                msg = "**DEFENSE** - __Le 1er territoire "
            else:
                msg = "**DEFENSE** - __Le "+str(n_territory)+"e territoire "

            if territory_name[0] == "T" and int(territory_name[1]) < 3:
                msg += "du haut__"
            elif territory_name[0] == "T":
                msg += "du milieu__"
            elif territory_name[0] == "F":
                msg += "des vaisseaux__"
            else:
                msg += "du bas__"

            nb_fails = territory[4]
            msg += " ("+territory_name+") est tombé avec "+str(nb_fails)+" fails."

            list_tw_alerts[1]["Home:"+territory_name] = msg

    return list_tw_alerts

############################################
# develop_teams
# IN - dict_teams (output of connect_gsheets.load_config_teams)
# OUT - dict_develop_teams {'PADME-RANCOR': [[PADME, ANAKIN, AHSOKA, C3PO, GK], [PADME, ANAKIN, AHSOKA, CAT, GK]],
#                           'SEE-RANCOR': [[SEE, Malak, Vader, Gard, WAT], [...]]}
############################################
def develop_teams(dict_teams):
    dict_developed_teams = {}

    for team_name in dict_teams:
        goutils.log2("DBG", "team: "+team_name)
        list_combinations = []
        for category in dict_teams[team_name]['categories']:
            list_toons = list(category[2].keys())
            toon_amount = category[1]
            combination = list(itertools.combinations(list_toons, toon_amount))
            list_combinations.append(combination)
        product_combinations = list(itertools.product(*list_combinations))
        #list_developed_toons = [[i for s in x for i in s] for x in product_combinations]
        #dict_developed_teams[team_name] = list_developed_toons
        if len(product_combinations) == 1:
            product_combinations = [((product_combinations[0][0], ()))]

        dict_developed_teams[team_name] = product_combinations

    return 0, "", dict_developed_teams

############################################
# find_best_teams
# IN - list_player_toon [['123456789', 'PADMEAMIDALA'], ['123456789', 'LORDVADER'], ['111222333', 'PADMEAMIDALA']]
# IN - player_name 'toto'
# IN - dict_team_score {'PADME-RANCOR': [1, 234, 345], 'JMK-RANCOR': [3, 34, 45]]
# IN - dict_teams {'PADME-RANCOR': [[(PADME, GK), (SNIPS, CAT)], [(PADME, GK), (SNIPS, C3P0)]],
#                  'JMK-RANCOR': [[...]]}
# OUT - error_code, error_text, list_best_teams_score [['PADME-RANCOR', 'JMK-RANCOR'], 13, 24]
############################################
async def find_best_teams_for_player(list_allyCode_toon, txt_allyCode, dict_team_score, dict_teams):
    list_best_teams_score = ["", 0, []]

    list_toon_player = [x[1] for x in list_allyCode_toon if x[0]==int(txt_allyCode)]

    list_all_required_toons = []
    for team in dict_teams:
        for team_combination in dict_teams[team]:
            for required_toon in team_combination[0]:
                if not required_toon in list_all_required_toons:
                    list_all_required_toons.append(required_toon)

    list_scoring_teams = [] #[['PADME', [padme, gk, snips]], ['PADME', [padme GK CAT]], ...]
    for scoring_team_name in dict_team_score:
        await asyncio.sleep(0)

        if scoring_team_name in dict_teams:
            dict_scoring_teams_by_required_toons = {}
            for [required_toons, important_toons] in dict_teams[scoring_team_name]:
                team_complete=True
                list_toons = []
                for toon in required_toons:
                    list_toons.append(toon)
                    if not (toon in list_toon_player):
                        team_complete=False

                list_required_toons = []
                for toon in important_toons:
                    list_toons.append(toon)
                    if not (toon in list_toon_player):
                        team_complete=False
                    if toon in list_all_required_toons:
                        list_required_toons .append(toon)
                if team_complete:
                    list_required_toons.sort()
                    key_required_toons = str(list_required_toons)
                    dict_scoring_teams_by_required_toons[key_required_toons] = list_toons

            if '[]' in dict_scoring_teams_by_required_toons:
                #print(dict_teams[scoring_team_name])
                list_scoring_teams.append([scoring_team_name,
                                           dict_scoring_teams_by_required_toons['[]'],
                                           dict_team_score[scoring_team_name][1]])
            else:
                for key in dict_scoring_teams_by_required_toons:
                    list_scoring_teams.append([scoring_team_name, 
                                               dict_scoring_teams_by_required_toons[key], 
                                               dict_team_score[scoring_team_name][1]])

        else:
            err_txt = "Team "+scoring_team_name+ " required but not defined"
            goutils.log2('ERR', err_txt)
            return 1, err_txt, None


    goutils.log2('INFO', "List of teams fillable by "+txt_allyCode+"="+str(list_scoring_teams))
    goutils.log2('DBG', str(len(list_scoring_teams))+" list to permute...")
    max_permutable_teams = 9
    if len(list_scoring_teams)>max_permutable_teams:
        goutils.log2('DBG', str(len(list_scoring_teams))+" reducing to "+str(max_permutable_teams)+" best")
        list_scoring_teams = sorted(list_scoring_teams, key=lambda x: -x[2])[:max_permutable_teams]
        goutils.log2('INFO', "List of "+str(max_permutable_teams)+" best teams fillable by "+txt_allyCode+"="+str(list_scoring_teams))

    permutations_scoring_teams = itertools.permutations(list_scoring_teams)
    goutils.log2('INFO', str(factorial(len(list_scoring_teams)))+" permutations...")
    list_txt_scores = []
    i_permutation = 0
    for permutation in permutations_scoring_teams:
        await asyncio.sleep(0)

        i_permutation += 1
        if (i_permutation % 100000) == 0:
            goutils.log2('INFO', "Current permutation: "+str(i_permutation))
        #print("NEW PERMUTATION")
        toon_bucket = list(list_toon_player)
        cur_team_list_score = ["",  0, 0]
        permutation_teams = []
        team_per_raid_phase = [False, False, False, False]
        for scoring_team in permutation:
            #print(scoring_team)
            scoring_team_name = scoring_team[0]
            scoring_team_toons = scoring_team[1]
            scoring_team_phase = dict_team_score[scoring_team_name][0]
            permutation_teams.append(scoring_team)

            if scoring_team_phase in [2, 3] and team_per_raid_phase[scoring_team_phase-1]:
                #print("phase break")
                break
            team_per_raid_phase[scoring_team_phase-1] = True

            team_complete=True
            for toon in scoring_team_toons:
                if toon in toon_bucket:
                    toon_bucket.remove(toon)
                else:
                    team_complete=False


            if team_complete:
                permutation_team_names = [x[0] for x in permutation_teams]
                cur_team_list_score[0] = permutation_team_names
                cur_team_list_score[1] += dict_team_score[scoring_team_name][1]
                cur_team_list_score[2] += dict_team_score[scoring_team_name][2]
                #print("complete: "+str(permutation_teams))
            else:
                #print("incomplete break")
                break

        txt_score = str(cur_team_list_score[0]) + ": " + str(cur_team_list_score[1])    
        if not txt_score in list_txt_scores:
            list_txt_scores.append(txt_score)

        if cur_team_list_score[1] > list_best_teams_score[1]:
            list_best_teams_score = list(cur_team_list_score)


    #if txt_allyCode == '419576861':
    #    for txt_score in list_txt_scores:
    #        print(txt_score)

    return 0, "", list_best_teams_score

################################################################
# find_best_teams_for_raid
# IN: txt_allyCode
# IN: raid_name
# IN: compute_guild (True/False)
# OUT: err_code, err_txt, dict_best_teams {'Gui On': ['JKR', 'DR'], ...}
################################################################
async def find_best_teams_for_raid(txt_allyCode, server_id, raid_name, compute_guild):
    if compute_guild:
        err_code, err_txt, dict_guild = await load_guild(txt_allyCode, True, True)
        if err_code != 0:
            return 1, 'ERR: guilde non trouvée pour code allié ' + txt_allyCode, {}
    else:
        e, t, d = await load_player(txt_allyCode, 1, False)
        if e != 0:
            return 1, 'ERR: joueur non trouvé pour code allié ' + txt_allyCode, {}

    dict_raids = connect_gsheets.load_config_raids(server_id, True)

    if not raid_name in dict_raids:
        goutils.log2("ERR", "raid "+raid_name+" inconnu")
        return 1, "ERR: raid "+raid_name+" inconnu", {}

    dts = {}
    for team_name in dict_raids[raid_name][1]:
        dts[team_name] = dict_raids[raid_name][1][team_name]
    goutils.log2("DBG", dts)

    l, d = connect_gsheets.load_config_teams(server_id, True)
    d_raid = {k: d[k] for k in dts.keys()}
    ec, et, ddt = develop_teams(d_raid)

    if compute_guild:
        query = "SELECT allyCode, defId FROM roster " \
              + "WHERE allyCode IN (" \
              + "SELECT allyCode from players WHERE guildName=(" \
              + "SELECT guildName from players WHERE allyCode="+txt_allyCode \
              + ")) AND relic_currentTier>=7"
    else:
        query = "SELECT allyCode, defId FROM roster " \
              + "WHERE allyCode="+txt_allyCode+" " \
              + "AND relic_currentTier>=7"

    goutils.log2("DBG", query)
    allyCode_toon = connect_mysql.get_table(query)

    if compute_guild:
        query = "SELECT allyCode, name FROM players " \
              + "WHERE guildName=(SELECT guildName from players WHERE allyCode="+txt_allyCode+") " \
              + "ORDER BY name"
    else:
        query = "SELECT allyCode, name FROM players " \
              + "WHERE allyCode="+txt_allyCode+" " \
              + "ORDER BY name"

    goutils.log2("DBG", query)
    ac_name = connect_mysql.get_table(query)

    list_acs = [str(x[0]) for x in ac_name]
    #list_acs = ['513353354']
    dict_best_teams = {}
    for ac in list_acs:
        ec, et, lbts = await find_best_teams_for_player(allyCode_toon, ac, dts, ddt)
        if ec != 0:
            return 1, et, {}
        pname = [x[1] for x in ac_name if x[0]==int(ac)][0]
        dict_best_teams[pname] = lbts

    return 0, "", dict_best_teams

################################################################
# tag_players_with_character
# IN: txt_allyCode (to identify the guild)
# IN: character ("SEE" or "SEE:7:G8" or "SEE:R5")
# IN: server_id (discord server id)
# IN: tw_mode (True if the bot shall count defense-used toons as not avail)
# OUT: err_code, err_txt, list_discord_ids
################################################################
async def tag_players_with_character(txt_allyCode, list_characters, server_id, tw_mode):
    err_code, err_txt, dict_guild = await load_guild(txt_allyCode, True, True)
    if err_code != 0:
        return 1, 'ERR: guilde non trouvée pour code allié ' + txt_allyCode, None

    if tw_mode:
        ec, et, list_active_players = await connect_rpc.get_tw_active_players(server_id, False)
        if ec != 0:
            return ec, et

    opposite_search = (list_characters[0][0]=="-")
    if opposite_search and tw_mode:
        return 1, "ERR: impossible de chercher un perso non présent (avec le '-' avant le premier/seul perso) avec l'option -TW", None

    #prepare basic query
    query = "SELECT guildName, name FROM players " \
          + "WHERE guildName=(" \
          + "SELECT guildName from players WHERE allyCode="+txt_allyCode+") "
    intro_txt = "Ceux"

    first_char = True #to store the char_id of the first char in the command
    for character in list_characters:
        tab_virtual_character = character.split(':')

        char_rarity = 0
        char_gear = 0
        char_relic = -2
        char_omicron = False

        opposite_search = (character[0]=="-")
        if len(tab_virtual_character) == 1:
            #regular character, not virtual
            char_alias = tab_virtual_character[0]
            simple_search = True
        else:
            char_alias = tab_virtual_character[0]
            simple_search = False

            for character_option in tab_virtual_character[1:]:
                if len(character_option)==1 and character_option in "1234567":
                    char_rarity = int(character_option)

                elif character_option[0] in "gG":
                    if character_option[1:].isnumeric():
                        char_gear = int(character_option[1:])
                        char_relic = -2
                        if (char_gear<1) or (char_gear>13):
                            return 1, "ERR: la syntaxe "+character+" est incorrecte pour le gear", None
                    else:
                        return 1, "ERR: la syntaxe "+character+" est incorrecte pour le gear", None

                elif character_option[0] in "rR":
                    if character_option[1:].isnumeric():
                        char_relic = int(character_option[1:])
                        char_gear = 13
                        if (char_relic<0) or (char_relic>9):
                            return 1, "ERR: la syntaxe "+character+" est incorrecte pour le relic", None
                    else:
                        return 1, "ERR: la syntaxe "+character+" est incorrecte pour le relic", None

                elif character_option == "omicron":
                    char_omicron = True
                else:
                    return 1, "ERR: la syntaxe "+character+" est incorrecte pour le gear", None
                
        #Get character_id
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([char_alias])
        if txt != '':
            return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt, None
        character_id = list_character_ids[0]
        if first_char:
            first_char_id = character_id

        goutils.log2("DBG", character_id)
        goutils.log2("DBG", opposite_search)
        goutils.log2("DBG", simple_search)
        if opposite_search and simple_search:
            intro_txt+= " qui n'ont pas "+character_id
            query+= "AND NOT allyCode IN ( "
        else:
            if opposite_search:
                intro_txt = " qui ont ("+character_id+ " mais pas "+character_id
            else:
                intro_txt+= " qui ont "+character_id

            if not simple_search:
                if char_rarity>0:
                    intro_txt += ":"+str(char_rarity)+"*"
                if char_relic>-2:
                    intro_txt += ":R"+str(char_relic)
                elif char_gear>0:
                    intro_txt += ":G"+str(char_gear)
                if char_omicron:
                    intro_txt += ":omicron"

            if opposite_search:
                intro_txt += ")"

            query+= "AND allyCode IN ( "

        query+= "   SELECT players.allyCode FROM players "
        query+= "   JOIN roster ON roster.allyCode = players.allyCode "

        if char_omicron:
            query+= "   JOIN roster_skills ON roster_id = roster.id "

        query+= "   WHERE guildName=(" 
        query+= "      SELECT guildName from players WHERE allyCode="+txt_allyCode+") " 
        query+= "      AND defId = '"+character_id+"' "

        if opposite_search:
            if not simple_search:
                query +="      AND (rarity < "+str(char_rarity)+" "
                query+= "      OR gear < "+str(char_gear)+" "
                query+= "      OR relic_currentTier < "+str(char_relic+2)+" "

                if char_omicron:
                    query += "      OR (roster_skills.omicron_tier>0 AND roster_skills.level<roster_skills.omicron_tier) "

                query+= "      ) "

        else:
            query+= "      AND rarity >= "+str(char_rarity)+" "
            query+= "      AND gear >= "+str(char_gear)+" "
            query+= "      AND relic_currentTier >= "+str(char_relic+2)+" "

            if char_omicron:
                query += "      AND (roster_skills.omicron_tier>0 AND roster_skills.level>=roster_skills.omicron_tier) " 
        query += ") "
        intro_txt += " et"
        first_char = False

    intro_txt = intro_txt[:-3]
    if tw_mode:
        intro_txt += ", qui sont inscrits à la GT, et qui ne l'ont pas mis en défense"
        query += "AND players.name IN "+str(tuple(list_active_players)).replace(",)", ")")+"\n"
    query += "GROUP BY guildName, players.name "

    goutils.log2('DBG', query)
    allyCodes_in_DB = connect_mysql.get_table(query)

    if allyCodes_in_DB == None:
        allyCodes_in_DB = []

    guildName = allyCodes_in_DB[0][0]
    dict_players = connect_mysql.load_config_players()[0]

    #Manage -TW option
    if tw_mode:
        ec, et, dict_def_toon_player = await get_tw_defense_toons(server_id, True)
        if ec != 0:
            return ec, et, None

    else:
        dict_def_toon_player = {}

    #Build the list of tags
    list_discord_ids = [intro_txt]
    for [guildName, player_name] in allyCodes_in_DB:
        if player_name == "":
            continue

        goutils.log2('DBG', 'player_name: '+player_name)

        if character_id in dict_def_toon_player and \
            player_name in dict_def_toon_player[first_char_id]:

            goutils.log2('DBG', "toon used in TW defense, no tag")
        else:
            if player_name in dict_players:
                player_mention = dict_players[player_name][1]
            else:
                player_mention = player_name

            list_discord_ids.append(player_mention)

    return 0, "", list_discord_ids

################################################################
# count_players_with_character
# IN: txt_allyCode (to identify the guild)
# IN: list_characters alias
# IN: server_id (discord server id)
# IN: tw_mode (True if the bot shall manage registered players and display count for adversary
# OUT: err_code, err_txt, {'unit name': [total, in TW defense], ...}
################################################################
async def count_players_with_character(txt_allyCode, list_characters, server_id, tw_mode):
    err_code, err_txt, dict_guild = await load_guild(txt_allyCode, True, True)
    if err_code != 0:
        return 1, 'ERR: guilde non trouvée pour code allié ' + txt_allyCode, None

    if tw_mode:
        ec, et, list_active_players = await connect_rpc.get_tw_active_players(server_id, False)
        if ec != 0:
            return ec, et

    #get units from alias
    list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_characters)

    #prepare basic query
    query = "SELECT defId, " \
          + "CASE WHEN gear<10 THEN CONCAT('G0', gear) " \
          + "WHEN gear<13 THEN CONCAT('G', gear) " \
          + "ELSE CONCAT('R', relic_currentTier-2) END, " \
          + "count(*) FROM players " \
          + "JOIN roster ON roster.allyCode = players.allyCode " \
          + "WHERE guildName=(" \
          + "SELECT guildName from players WHERE allyCode="+txt_allyCode+") " \
          + "AND defId in "+str(tuple(list_character_ids)).replace(",)", ")")+" " 

    if tw_mode:
        query += "AND players.name IN "+str(tuple(list_active_players)).replace(",)", ")")+" "

    query +="GROUP BY defId, gear, relic_currentTier " \
          + "ORDER BY defId, gear, relic_currentTier"
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_table(query)

    output_dict = {}
    for line in db_data:
        unit_id = line[0]
        unit_gear = line[1]
        if not unit_id in output_dict:
            output_dict[unit_id] = {}
        output_dict[unit_id][unit_gear] = [line[2], None]

    print(output_dict)
    #Manage -TW option
    if tw_mode:
        ec, et, dict_def_toon_player = await get_tw_defense_toons(server_id, True)
        if ec != 0:
            return ec, et, None

        for unit_id in output_dict:
            if unit_id in dict_def_toon_player:
                list_def_players = dict_def_toon_player[unit_id]

                query = "SELECT defId, " \
                      + "CASE WHEN gear<10 THEN CONCAT('G0', gear) " \
                      + "WHEN gear<13 THEN CONCAT('G', gear) " \
                      + "ELSE CONCAT('R', relic_currentTier-2) END, " \
                      + "count(*) FROM players " \
                      + "JOIN roster ON roster.allyCode = players.allyCode " \
                      + "WHERE guildName=(" \
                      + "SELECT guildName from players WHERE allyCode="+txt_allyCode+") " \
                      + "AND defId='"+unit_id+"' " \
                      + "AND name in "+str(tuple(list_def_players)).replace(",)", ")")+" " \
                      + "GROUP BY defId, gear, relic_currentTier "
                goutils.log2("DBG", query)
                db_data = connect_mysql.get_table(query)

                for line in db_data:
                    unit_id = line[0]
                    unit_gear = line[1]
                    unit_count = line[2]
                    output_dict[unit_id][unit_gear][1] = unit_count

    return 0, "", output_dict

#######################################################
# get_gv_graph
# IN txt_allyCode: identifier of the player
# IN characters: list of GV characters
# OUT: image of the graph
#######################################################
def get_gv_graph(txt_allyCode, characters):
    if "FARM" in characters:
        character_ids_txt = "farm perso"
    elif not "all" in characters:
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(characters)
        if txt != '':
            return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt, None
        character_ids_txt = str(tuple(list_character_ids)).replace(',)', ')')
    else:
        character_ids_txt = "tout le guide"

    query = "SELECT date, defId, progress, source, name FROM gv_history " \
          + "JOIN players ON players.allyCode = gv_history.allyCode " \
          + "WHERE gv_history.allyCode="+txt_allyCode+" "
    if "FARM" in characters:
          query += "AND defId='FARM' "
    elif not "all" in characters:
          query += "AND defId IN "+character_ids_txt+" "
    query +="ORDER BY date DESC LIMIT 30"
    goutils.log2("DBG", query)
    ret_db = connect_mysql.get_table(query)
    if ret_db == None:
        return 1, "WAR: aucun progrès connu de "+character_ids_txt+" pour "+txt_allyCode, None

    min_date = None
    max_date = None
    dict_dates={}
    dict_values={}

    if len(characters) == 1 and characters[0]!="all":
        #display the one character progress, with both j.bot and go.bot
        for line in ret_db:
            if min_date==None or line[0]<min_date:
                min_date = line[0]
            if max_date==None or line[0]>max_date:
                max_date = line[0]

            if not line[3] in dict_dates:
                dict_dates[line[3]] = []
                dict_values[line[3]] = []
            dict_dates[line[3]].append(line[0])
            dict_values[line[3]].append(line[2])

            player_name = line[4]

    else: #more than one character, all characters displayed only with go.bot
        for line in ret_db:
            if line[3] == "go.bot":
                if min_date==None or line[0]<min_date:
                    min_date = line[0]
                if max_date==None or line[0]>max_date:
                    max_date = line[0]

                if not line[1] in dict_dates:
                    dict_dates[line[1]] = []
                    dict_values[line[1]] = []
                dict_dates[line[1]].append(line[0])
                dict_values[line[1]].append(line[2])

                player_name = line[4]

    #create plot
    fig, ax = plt.subplots()
    #set colormap
    # Have a look at the colormaps here and decide which one you'd like:
    # http://matplotlib.org/1.2.1/examples/pylab_examples/show_colormaps.html
    colormap = plt.cm.gist_ncar
    plt.gca().set_prop_cycle(plt.cycler('color', plt.cm.jet(np.linspace(0, 1, len(dict_dates)))))

    #add series
    for key in dict_dates:
        if key == 'j.bot':
            marker = 'x'
        else:
            marker = '.'
        ax.plot(dict_dates[key], dict_values[key], label=key, marker=marker)

        if max(dict_values[key])<100:
            #extrapolate values until 100%
            epoch=datetime.date(1970, 1, 1)
            today = datetime.datetime.now().date()

            if len(dict_dates[key])>=3:
                #remove the stable values at the beginning
                for i in range(len(dict_dates[key])-1, 1, -1):
                    if dict_values[key][i] == dict_values[key][i-1]:
                        pass
                    else:
                        break
                list_dates_progressing = dict_dates[key][:i+1]
                list_values_progressing = dict_values[key][:i+1]
            else:
                list_dates_progressing = dict_dates[key]
                list_values_progressing = dict_values[key]

            #transfom datetime into an amount of days (from epoch)
            date_days = [(x-epoch).days for x in list_dates_progressing]

            #extrapolation to get value from day
            fit = np.polyfit(date_days, list_values_progressing, 2)

            #extrapolate the date when the value will reach 100
            cur_date = max(list_dates_progressing)
            cur_value = 0
            while (cur_date-today).days<30 and cur_value<100:
                cur_day = (cur_date-epoch).days
                cur_value = fit[0]*cur_day*cur_day + fit[1]*cur_day + fit[2]
                cur_date = cur_date+datetime.timedelta(1)

            if cur_value < max(list_values_progressing):
                #the extrapolation decreases, do not go further
                date_end = max(list_dates_progressing)
            else:
                date_end = epoch+datetime.timedelta(cur_day)

            #plot the extrapolation line, max 20 points
            # first set the 20 points for the dates
            list_dates_fit = [min(list_dates_progressing)]
            scale_days = (date_end-min(list_dates_progressing)).days
            for i in range(20):
                next_date = list_dates_fit[0]+datetime.timedelta((i+1)*scale_days/20)
                list_dates_fit.append(next_date)
            list_days = [(x-epoch).days for x in list_dates_fit]

            # then compute the values at these dates
            list_values_fit = []
            for d in list_days:
                value_fit = fit[0]*d*d + fit[1]*d + fit[2]
                list_values_fit.append(value_fit)

            #plot a dashed line for the extrapolation
            ax.plot(list_dates_fit, list_values_fit, linestyle="dashed")


    #format dates on X axis
    date_format = mdates.DateFormatter("%d-%m")
    ax.xaxis.set_major_formatter(date_format)
    #add title
    if len(characters)==1:
        title = "Progrès de "+character_ids_txt+" pour "+player_name
    else:
        title = "Progrès pour "+player_name
    fig.suptitle(title)

    # Shrink current axis by 20%
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

    # Put a legend to the right of the current axis
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    #set min/max on X axis
    if min_date == max_date:
        ax.set_xlim([min_date-datetime.timedelta(days=1), 
                     max_date+datetime.timedelta(days=1)])
                
    #Render the image
    fig.canvas.draw()
    fig_size = fig.canvas.get_width_height()
    fig_bytes = fig.canvas.tostring_rgb()
    image = Image.frombytes('RGB', fig_size, fig_bytes)

    return 0, "", image

###############################
# is_modq = True  >> ModQ graph
# is_modq = False >> StatQ graph
###############################
def get_modqstatq_graph(txt_allyCode, is_modq):
    if is_modq:
        kpi_name = "modq"
    else:
        kpi_name = "statq"

    query = "SELECT date, "+kpi_name+", name FROM gp_history " \
          + "JOIN players ON players.allyCode = gp_history.allyCode " \
          + "WHERE gp_history.allyCode="+txt_allyCode+" " \
          + "AND timestampdiff(DAY, date, CURRENT_TIMESTAMP)<=30 " \
          + "AND NOT isnull("+kpi_name+") " \
          + "ORDER BY date DESC"
    goutils.log2("DBG", query)
    ret_db = connect_mysql.get_table(query)
    if ret_db == None:
        return 1, "WAR: aucun "+kpi_name+" connu de "+character_id+" pour "+txt_allyCode+" dans les 30 derniers jours", None

    d_kpi = []
    v_kpi = []
    min_date = None
    max_date = None
    for line in ret_db:
        if min_date==None or line[0]<min_date:
            min_date = line[0]
        if max_date==None or line[0]>max_date:
            max_date = line[0]

        d_kpi.append(line[0])
        v_kpi.append(line[1])

        player_name = line[2]

    #create plot
    fig, ax = plt.subplots()
    #add series
    ax.plot(d_kpi, v_kpi, label=kpi_name)
    #format dates on X axis
    date_format = mdates.DateFormatter("%d-%m")
    ax.xaxis.set_major_formatter(date_format)
    #add title
    title = "Progrès "+kpi_name+" de "+player_name
    fig.suptitle(title)
    #set min/max on X axis
    if min_date == max_date:
        ax.set_xlim([min_date-datetime.timedelta(days=1), 
                     max_date+datetime.timedelta(days=1)])

    fig.canvas.draw()
    fig_size = fig.canvas.get_width_height()
    fig_bytes = fig.canvas.tostring_rgb()
    image = Image.frombytes('RGB', fig_size, fig_bytes)

    return 0, "", image

async def get_tw_defense_toons(server_id, use_cache_data):
    dict_unitsList = godata.get("unitsList_dict.json")

    #Check if the guild can use RPC
    if not server_id in connect_rpc.get_dict_bot_accounts():
        return []

    query = "SELECT name, twChanOut_id FROM guild_bot_infos "
    query+= "JOIN guilds on guilds.id = guild_bot_infos.guild_id "
    query+= "WHERE server_id="+str(server_id)
    goutils.log2('DBG', query)
    db_data = connect_mysql.get_line(query)

    guildName = db_data[0]
    twChannel_id = db_data[1]
    if twChannel_id == 0:
        return 1, "ERR: commande inutilisable sur ce serveur\n", None

    rpc_data = await connect_rpc.get_tw_status(server_id, use_cache_data)
    tw_id = rpc_data[0]
    if tw_id == None:
        return 1, "ERR: aucune GT en cours\n", None

    list_defense_squads = rpc_data[1][0]

    dict_def_toon_player = {}
    for squad in list_defense_squads:
        player = squad[1]
        for char_id in squad[2]:
            if not char_id in dict_def_toon_player:
                dict_def_toon_player[char_id] = []

            dict_def_toon_player[char_id].append(player)

    return 0, "", dict_def_toon_player

def allocate_platoons(txt_allyCode, list_zones):
    total_err_txt = ""
    dict_zones, dict_tb_toons = connect_gsheets.load_new_tb()

    list_ops=[]
    for zone in list_zones:
        match_count = 0
        for existing_zone in dict_zones.keys():
            if existing_zone.startswith(zone):
                match_count+=1
                list_ops.append(existing_zone)
        if match_count==0:
            return 2, "Impossible de reconnaître la zone "+zone, None

    list_ops=sorted(set(list_ops))
    goutils.log2('DBG', list_ops)

    dict_toons = {}
    for ops in list_ops:
        for toon in dict_zones[ops]:
            if not toon in dict_toons:
                dict_toons[toon] = [0, dict_zones[ops][toon][1]]
            dict_toons[toon][0] += dict_zones[ops][toon][0]
    dict_guild={}

    dict_unitsList = godata.get("unitsList_dict.json")
    list_blocked_ops=[]
    for defId in dict_toons:
        count = dict_toons[defId][0]
        min_relic = dict_toons[defId][1]
        unit = dict_unitsList[defId]
        if unit['combatType']==1:
            #CHARACTER
            query = "SELECT name, roster.allyCode, gp " \
                  + "FROM roster JOIN players ON players.allyCode = roster.allyCode " \
                  + "WHERE players.guildName = " \
                  + "(SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"') " \
                  + "AND defId='"+defId+"' AND (relic_currentTier-2)>="+str(min_relic)+" " \
                  + "ORDER BY gp, rand() " \
                  + "LIMIT "+ str(count)
        else:
            #SHIP
            query = "SELECT name, roster.allyCode, gp " \
                  + "FROM roster JOIN players ON players.allyCode = roster.allyCode " \
                  + "WHERE players.guildName = " \
                  + "(SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"') " \
                  + "AND defId='"+defId+"' AND rarity=7 " \
                  + "ORDER BY gp, rand() " \
                  + "LIMIT "+ str(count)
        goutils.log2("DBG", query)
        ret_db = connect_mysql.get_table(query)
        if ret_db==None:
            size_db=0
        else:
            size_db=len(ret_db)
        if size_db < count:
            filtered_list_zones = [x for x in list_ops if x in dict_tb_toons[defId]]
            character_name = dict_unitsList[defId]['name']
            ec, et, list = find_best_toons_in_guild(txt_allyCode, defId, "R9")
            if dict_unitsList[defId]['combatType']==1:
                best_next_toons = [x[0]+" ("+str(x[1])+" étoiles "+x[2]+")" for x in list[size_db:count+1]]
                err_txt = "Pas assez de **"+character_name+"** relic "+str(min_relic)+" ("+str(size_db)+"/"+str(count)+") " \
                    + "pour remplir "+str(filtered_list_zones)
                err_txt+=" > les plus proches sont "+str(best_next_toons)
            else:
                best_next_toons = [x[0]+" ("+str(x[1])+" étoiles)" for x in list[size_db:count+1]]
                err_txt = "Pas assez de **"+character_name+"** ("+str(size_db)+"/"+str(count)+") " \
                    + "pour remplir "+str(filtered_list_zones)
                err_txt+=" > les plus proches sont "+str(best_next_toons)
            goutils.log2("WAR", err_txt)
            total_err_txt += err_txt+"\n"

            if size_db==0 or len(filtered_list_zones)==1:
                list_blocked_ops+=filtered_list_zones
        else:
            list_ac=[x[0] for x in ret_db]
            dict_guild[defId]=list_ac

    if len(total_err_txt) > 0:
        list_blocked_ops=sorted(set(list_blocked_ops))
        goutils.log2("INFO", list_blocked_ops)
        list_possible_ops = [x for x in list_ops if not x in list_blocked_ops]
        return 1, total_err_txt, list_possible_ops

    #print(dict_guild)
    dict_players={}
    for zone in list_ops:
        #print(zone)
        for defId in dict_zones[zone]:
            #print(defId)
            list_players=dict_guild[defId]
            player=list_players[0]
            #print(player)
            new_list_players=list_players[1:]
            dict_guild[defId]=new_list_players
            
            if not player in dict_players:
                dict_players[player]=[]
            dict_players[player].append([zone, dict_unitsList[defId]['name']])

    return 0, "", dict_players

#############################################################################
# find_best_toons_in_guild
# IN: txt_alllyCode: one allyCode in the guild
# IN: character_id: defId of the toon
# IN: max_gear: maximum gear or relic level ("G8" or "R5")
# OUT: list [[playerName, rarity, gear/relic], ...]
#############################################################################
def find_best_toons_in_guild(txt_allyCode, character_id, max_gear):
    if max_gear[0] == 'G':
        max_gear_int=int(max_gear[1:])
    elif max_gear[0] == 'R':
        max_gear_int=13+int(max_gear[1:])
    else:
        return 1, "ERR: gear incorrect", None

    query = "SELECT name, rarity, " \
          + "CASE WHEN gear<13 THEN concat('G', gear) " \
          + "ELSE CONCAT('R',relic_currentTier-2) " \
          + "END as 'gear', " \
          + "(rarity/7*0.5+(gear+relic_currentTier-2)/(13+9)*0.5) as progress " \
          + "FROM roster JOIN players " \
          + "ON players.allyCode = roster.allyCode " \
          + "WHERE players.guildName = (SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"') " \
          + "AND defId='"+character_id+"' " \
          + "AND (gear+relic_currentTier-2)<"+str(max_gear_int)+" " \
          + "ORDER BY progress desc "
    goutils.log2("DBG", query)
    ret_db = connect_mysql.get_table(query)
    if ret_db==None:
        ret_db=[]

    #remove the 4th column (progress) from the table
    ret_db = [[x[0], x[1], x[2]] for x in ret_db]

    return 0, "", ret_db

async def print_tb_status(server_id, targets_zone_stars, compute_estimated_fights, use_cache_data):
    dict_tb = godata.dict_tb
    ec, et, tb_data = await connect_rpc.get_tb_status(server_id, targets_zone_stars, compute_estimated_fights, use_cache_data)
    if ec!=0:
        return 1, et, None

    [dict_phase, dict_strike_zones, dict_tb_players, dict_open_zones] = tb_data
    list_deployment_types = []
    for zone_name in dict_open_zones:
        zone_deployment_type = dict_tb[zone_name]["type"]
        if not zone_deployment_type in list_deployment_types:
            list_deployment_types.append(zone_deployment_type)

    # START THE DISPLAY PART
    ret_print_tb_status = ""
    sheet_url = connect_gsheets.get_sheet_url(server_id, "BT graphs")
    if sheet_url != None:
        ret_print_tb_status += "More details, including players \u2013 "+sheet_url+"\n"

    ret_print_tb_status+="---------------\n"
    available_ship_deploy = dict_phase["availableShipDeploy"]
    available_char_deploy = dict_phase["availableCharDeploy"]
    available_mix_deploy = dict_phase["availableMixDeploy"]
    remaining_ship_deploy = dict_phase["remainingShipDeploy"]
    remaining_char_deploy = dict_phase["remainingCharDeploy"]
    remaining_mix_deploy = dict_phase["remainingMixDeploy"]
    remaining_to_play_ships = dict_phase["shipPlayers"]
    remaining_to_play_chars = dict_phase["charPlayers"]
    remaining_to_play_mix = dict_phase["mixPlayers"]
    if "ships" in list_deployment_types:
        ret_print_tb_status += "Remaining to deploy ships \u2013 "+str(round(available_ship_deploy/1000000, 1))+"M"
        ret_print_tb_status += " (waiting for "+str(remaining_to_play_ships)+" players)\n"
    if "chars" in list_deployment_types:
        ret_print_tb_status += "Remaining to deploy chars \u2013 "+str(round(available_char_deploy/1000000, 1))+"M"
        ret_print_tb_status += " (waiting for "+str(remaining_to_play_chars)+" players)\n"
    if "mix" in list_deployment_types:
        ret_print_tb_status += "Remaining to deploy \u2013 "+str(round(available_mix_deploy/1000000, 1))+"M"
        ret_print_tb_status += " (waiting for "+str(remaining_to_play_mix)+" players)\n"

    list_images = []
    tb_type = dict_phase["type"]
    for zone_name in dict_open_zones:
        ret_print_tb_status+="---------------\n"
        ret_print_tb_status+="**"+dict_tb[zone_name]["name"]+"**\n"

        current_score = dict_open_zones[zone_name]["score"]
        ret_print_tb_status+="Current score \u2013 "+str(round(current_score/1000000, 1))+"M "

        cur_strike_score = dict_open_zones[zone_name]["strikeScore"]
        cur_strike_fights = sum(dict_open_zones[zone_name]["strikeFights"].values())
        estimated_strike_score = dict_open_zones[zone_name]["estimatedStrikeScore"]
        estimated_strike_fights = dict_open_zones[zone_name]["estimatedStrikeFights"]
        max_strike_score = dict_open_zones[zone_name]["maxStrikeScore"]

        ret_print_tb_status+="(including "+str(round(cur_strike_score/1000000, 1))+"M in "+str(cur_strike_fights)+" fights)\n"

        score_with_estimated_strikes = current_score + estimated_strike_score
        if compute_estimated_fights:
            ret_print_tb_status+="Estimated fights \u2013 "+str(round(estimated_strike_score/1000000, 1))+"M "
            ret_print_tb_status+="(in "+str(estimated_strike_fights)+" fights)\n"

        deploy_consumption = dict_open_zones[zone_name]["deployment"]
        score_with_estimations = score_with_estimated_strikes + deploy_consumption
        ret_print_tb_status+="Deployment \u2013 "+str(round(deploy_consumption/1000000, 1))+"M\n"

        star_for_score = dict_open_zones[zone_name]["estimatedStars"]
        ret_print_tb_status+="\u27a1 Zone result \u2013 "+'\u2b50'*star_for_score+'\u2729'*(3-star_for_score)+"\n"

        #create image
        img = draw_tb_previsions(dict_tb[zone_name]["name"], dict_tb[zone_name]["scores"],
                                 current_score, estimated_strike_score, deploy_consumption,
                                 max_strike_score)
        list_images.append(img)

    ret_print_tb_status += "----------------------------\n"
    if "ships" in list_deployment_types:
        ret_print_tb_status += "Unused deployment ships \u2013 "+str(round(remaining_ship_deploy/1000000, 1))+"M\n"
    if "chars" in list_deployment_types:
        ret_print_tb_status += "Unused deployment squads \u2013 "+str(round(remaining_char_deploy/1000000, 1))+"M\n"
    if "mix" in list_deployment_types:
        ret_print_tb_status += "Unused deployment mix \u2013 "+str(round(remaining_mix_deploy/1000000, 1))+"M\n"
    ret_print_tb_status += "----------------------------\n"

    return 0, ret_print_tb_status, list_images

def draw_score_zone(zone_img_draw, start_score, delta_score, max_score, color, position):
    font = ImageFont.truetype("IMAGES"+os.path.sep+"arial.ttf", 18)

    if delta_score == 0:
        return start_score

    end_score = int(start_score + delta_score)
    if end_score > max_score:
        end_score = max_score
        delta_score = max_score - start_score
    x_start = int(start_score/max_score*(480-20)+20)+1
    x_end = int(end_score/max_score*(480-20)+20)
    if delta_score > 0:
        zone_img_draw.rectangle((x_start, 80, x_end, 110), color)
    zone_img_draw.line([(x_end, 80), (x_end, 120+20*position)], fill="black", width=0)

    end_score_txt = "{:,}".format(end_score)
    end_score_txt = str(round(end_score/1000000, 1))
    if end_score < max_score/2:
        x_txt = x_end +5
    else:
        end_score_txt_size = font.getsize(end_score_txt)
        x_txt = x_end - end_score_txt_size[0] - 5
    zone_img_draw.text((x_txt, 110+20*position), end_score_txt, "black", font=font)

    return end_score

def draw_tb_previsions(zone_name, zone_scores, current_score, estimated_strikes, deployments, max_strikes):
    zone_img = Image.new('RGB', (500, 220), (255, 255, 255))
    zone_img_draw = ImageDraw.Draw(zone_img)

    score_3stars = zone_scores[2]

    current_score = draw_score_zone(zone_img_draw, 0, current_score, score_3stars, "darkgreen", 1)
    eststrike_score = draw_score_zone(zone_img_draw, current_score, estimated_strikes, score_3stars, "orange", 3)
    deployment_score = draw_score_zone(zone_img_draw, eststrike_score, deployments, score_3stars, "yellow", 2)
    final_score = draw_score_zone(zone_img_draw, deployment_score, max_strikes-estimated_strikes, score_3stars, "red", 4)

    #Draw stars
    active_star_image = Image.open("IMAGES/PORTRAIT_FRAME/star.png")
    inactive_star_image = Image.open("IMAGES/PORTRAIT_FRAME/star-inactive.png")
    drawn_stars = 0
    for score_star in zone_scores:
        x_star = 200 + drawn_stars*50
        if current_score >= score_star:
            star_image = active_star_image
        else:
            star_image = inactive_star_image

        zone_img.paste(star_image, (x_star, 50), star_image)
        drawn_stars += 1

    #Draw lines and text at the end
    #Draw rectangle
    zone_img_draw.line([(20, 80), (480, 80)], fill="black", width=2)
    zone_img_draw.line([(20, 110), (480, 110)], fill="black", width=2)
    zone_img_draw.line([(20, 80), (20, 110)], fill="black", width=2)
    zone_img_draw.line([(480, 80), (480, 110)], fill="black", width=2)

    #add ster limits
    for score_star in zone_scores:
        x_star = int(score_star / score_3stars * (480-20) + 20)

        zone_img_draw.line([(x_star, 80), (x_star, 120)], fill="black", width=2)
        
        font = ImageFont.truetype("IMAGES"+os.path.sep+"arial.ttf", 12)
        score_star_txt = "{:,}".format(score_star)
        score_star_txt_size = font.getsize(score_star_txt)
        x_txt = x_star - score_star_txt_size[0] - 5
        zone_img_draw.text((x_txt, 115), score_star_txt, "black", font=font)

    #legend
    zone_img_draw.rectangle((250, 10, 260, 20), fill="darkgreen")
    zone_img_draw.text((265, 10), "Score actuel", "black", font=font)
    zone_img_draw.rectangle((250, 30, 260, 40), fill="yellow")
    zone_img_draw.text((265, 30), "Déploiement", "black", font=font)
    zone_img_draw.rectangle((350, 10, 360, 20), fill="orange")
    zone_img_draw.text((365, 10), "Combats estimés", "black", font=font)
    zone_img_draw.rectangle((350, 30, 360, 40), fill="red")
    zone_img_draw.text((365, 30), "Combats max", "black", font=font)


    font = ImageFont.truetype("IMAGES"+os.path.sep+"arial.ttf", 24)
    zone_img_draw.text((10, 10), zone_name, "black", font=font)

    return zone_img

def print_events(fevent_name, fguild_name):
    g=json.load(open(fguild_name,"r"))
    guildId = g["guild"]["profile"]["id"]
    dict_tb = godata.dict_tb
    dict_tw = godata.dict_tw

    d=json.load(open(fevent_name,"r"))
    sorted_d=dict(sorted(d.items(), key=lambda x:int(x[1]["timestamp"])))
    dict_squads={}
    for id in sorted_d:
        event=d[id]
        author=event["authorName"]
        timestamp= int(int(event["timestamp"])/1000)
        time=datetime.datetime.fromtimestamp(timestamp)
        data=event["data"][0]

        #TW
        if data["activityType"]=="TERRITORY_WAR_CONFLICT_ACTIVITY":
            activity=data["activity"]
            zone_id=activity["zoneData"]["zoneId"]
            zone_name = dict_tw[zone_id]
            if "DEPLOY" in activity["zoneData"]["activityLogMessage"]["key"]:
                if activity["zoneData"]["instanceType"] == "ZONEINSTANCEHOME":
                    leader = activity["warSquad"]["squad"]["cell"][0]["unitDefId"].split(":")[0]
                    print(str(time)+" DEFENSE@"+zone_name+": "+author+" "+leader)
            else:
                if activity["zoneData"]["guildId"] == guildId:
                    if "warSquad" in activity:
                        squad_id = activity["warSquad"]["squadId"]
                        if "squad" in activity["warSquad"]:
                            opponent=activity["warSquad"]["playerName"]
                            leader = activity["warSquad"]["squad"]["cell"][0]["unitDefId"].split(":")[0]
                            leader_opponent = leader+"@"+opponent
                            dict_squads[squad_id]=leader_opponent
                        else:
                            if squad_id in dict_squads:
                                leader_opponent=dict_squads[squad_id]
                            else:
                                leader_opponent="UNKNOWN_LEADER"

                        if activity["warSquad"]["squadStatus"]=="SQUADAVAILABLE":
                            count_dead=0
                            remaining_tm=False
                            if "squad" in activity["warSquad"]:
                                for cell in activity["warSquad"]["squad"]["cell"]:
                                    if cell["unitState"]["healthPercent"] == "0":
                                        count_dead+=1
                                    if cell["unitState"]["turnPercent"] != "100" \
                                        and cell["unitState"]["turnPercent"] != "0":
                                        remaining_tm=True

                            sys.stdout.write(str(time)+" DEFAITE@"+zone_name+": "+author+" "+leader_opponent+" ("+str(count_dead)+" morts)")
                            if count_dead==0 and remaining_tm:
                                sys.stdout.write(" >>> TM !!!\n")
                            else:
                                sys.stdout.write("\n")

                        elif activity["warSquad"]["squadStatus"]=="SQUADDEFEATED":
                            if "squad" in activity["warSquad"]:
                                print(str(time)+" VICTOIRE@"+zone_name+": "+author+" "+leader_opponent)
                        elif activity["warSquad"]["squadStatus"]=="SQUADLOCKED":
                            if "squad" in activity["warSquad"]:
                                print(str(time)+" DEBUT: "+author+" "+leader_opponent)
                        else:
                            print(str(time)+" "+activity["warSquad"]["squadStatus"])
                    else:
                        scoretotal = activity["zoneData"]["scoreTotal"]
                        print(str(time)+" Score: "+scoretotal)

        #TB
        elif data["activityType"]=="TERRITORY_CONFLICT_ACTIVITY":
            activity=data["activity"]
            if "CONFLICT_CONTRIBUTION" in activity["zoneData"]["activityLogMessage"]["key"]:
                zone_data = activity["zoneData"]
                zone_id = zone_data["zoneId"]
                zone_name = dict_tb[zone_id]["name"]
                phases_ok = zone_data["activityLogMessage"]["param"][2]["paramValue"][0]
                phases_tot = zone_data["activityLogMessage"]["param"][3]["paramValue"][0]
                print(str(time)+" COMBAT: "+author+" "+str(phases_ok)+"/"+str(phases_tot)+" en "+zone_name)
            elif "CONFLICT_DEPLOY" in activity["zoneData"]["activityLogMessage"]["key"]:
                zone_data = activity["zoneData"]
                zone_id = zone_data["zoneId"]
                if zone_id in dict_tb:
                    zone_name = dict_tb[zone_id]["name"]
                else:
                    zone_name = zone_id
                points = zone_data["activityLogMessage"]["param"][0]["paramValue"][0]
                print(str(time)+" DEPLOIEMENT: "+author+" déploie "+str(points)+" en "+zone_name)

        else:
            print(data["activityType"])

    return

async def get_tb_alerts(server_id, force_latest):
    #Check if the guild can use RPC
    if server_id in connect_rpc.get_dict_bot_accounts():
        territory_scores, active_round = await connect_rpc.get_tb_guild_scores(server_id, not force_latest)
    else:
        return []
    goutils.log2("DBG", "["+str(server_id)+"] territory_scores="+str(territory_scores))

    if active_round != "":
        [territory_stars, daily_targets, margin] = connect_gsheets.get_tb_triggers(server_id, False)
        goutils.log2("DBG", "["+str(server_id)+"] tb_triggers="+str([territory_stars, daily_targets, margin]))

        #print(territory_scores)
        tb_trigger_messages=[]
        tb_name = list(territory_scores.keys())[0].split("-")[0]
        round_number = int(active_round[-1])
        current_targets = daily_targets[tb_name][round_number-1]

        if tb_name == "ROTE":
            pos_name = [[0, "DS"], [1, "MS"], [2, "LS"]]
        else:
            pos_name = [[0, "top"], [1, "mid"], [2, "bot"]]

        for pos, name in pos_name:
            current_target = current_targets[pos]
            if current_target == "-":
                continue
            current_target_phase = current_target.split('-')[0]
            current_target_stars = current_target.split('-')[1]
            full_phase_name = tb_name+"-"+current_target_phase+"-"+name
            if not full_phase_name in territory_scores:
                tb_trigger_messages.append("ERREUR: phase "+full_phase_name+" non atteinte en "+name)
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
    
def get_tw_player_def(fevents_name, player_name):
    dict_units = godata.get("unitsList_dict.json")
    dict_tw = godata.dict_tw

    tw_events = json.load(open(fevents_name, 'r'))
    if "event" in tw_events:
        #events from rpc, not in EVENTS
        dict_tw_events = {}
        for event in tw_events["event"]:
            event_id = event["id"]
            dict_tw_events[event_id] = event
    else:
        dict_tw_events = tw_events

    dict_def = {}

    for event_id in dict_tw_events:
        event = dict_tw_events[event_id]
        if "TERRITORY_WAR" in event["channelId"] \
            and event["authorName"] == player_name \
            and event["data"][0]["activityType"]=="TERRITORY_WAR_CONFLICT_ACTIVITY" \
            and event["data"][0]["activity"]["zoneData"]["activityLogMessage"]["key"]=="TERRITORY_CHANNEL_ACTIVITY_CONFLICT_DEFENSE_DEPLOY":

            #defense from the player
            territory = event["data"][0]["activity"]["zoneData"]["zoneId"]
            cur_def = [territory]
            warSquad = event["data"][0]["activity"]["warSquad"]
            for cell in warSquad["squad"]["cell"]:
                cur_def.append([cell["unitDefId"], cell["unitId"]])
            leader = cur_def[1][0]
            dict_def[leader] = cur_def

    for leader in dict_def:
        zone_id = dict_def[leader][0]
        txt_cmd = "go.bot.deftw "+dict_tw[zone_id]
        for element in dict_def[leader][1:]:
            unit_id = element[0].split(":")[0]
            txt_cmd += " \""+dict_units[unit_id]["name"]+"\""
        print(txt_cmd)

async def deploy_bot_tb(server_id, zone_shortname, characters):
    dict_unitsList = godata.get("unitsList_dict.json")

    #Manage request for all characters
    if characters == 'all':
        list_character_ids=list(dict_unitsList.keys())
    else:
        #specific list of characters for one player
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([characters])
        if txt != '':
            return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt

    dict_tb = godata.dict_tb
    ec, et, tb_data = await connect_rpc.get_tb_status(server_id, "", False, True)
    if ec!=0:
        return 1, et
    [dict_phase, dict_strike_zones, dict_tb_players, dict_open_zones] = tb_data
    tb_type = dict_phase["type"]
    if not tb_type in dict_tb:
        return 1, "TB inconnue du bot"

    if zone_shortname in dict_tb[tb_type]["zoneNames"]:
        conflict = dict_tb[tb_type]["zoneNames"][zone_shortname]
    else:
        return 1, "Zone inconnue pour cette BT"

    for zone_name in dict_open_zones:
        if zone_name.endswith(conflict):
            break

    zone_type = dict_tb[zone_name]["type"]
    if zone_type != "mix":
        if zone_type == "chars":
            combatType = 1
        else:
            combatType = 2
        filtered_list_character_ids = []
        for unit_id in list_character_ids:
            if dict_unitsList[unit_id]["combatType"] == combatType:
                filtered_list_character_ids.append(unit_id)
        list_character_ids = filtered_list_character_ids

    ec, txt = await connect_rpc.deploy_tb(server_id, zone_name, list_character_ids)

    return ec, txt

async def deploy_bot_tw(server_id, zone_shortname, characters):
    dict_unitsList = godata.get("unitsList_dict.json")

    #specific list of characters for one player
    list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(characters)
    if txt != '':
        return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt

    dict_tw=godata.dict_tw

    if zone_shortname in dict_tw:
        zone_name = dict_tw[zone_shortname]
    else:
        return 1, "Zone GT inconnue"

    ec, txt = await connect_rpc.deploy_tw(server_id, zone_name, list_character_ids)

    return ec, txt

async def deploy_platoons_tb(server_id, platoon_name, characters):
    dict_unitsList = godata.get("unitsList_dict.json")

    #specific list of characters for one player
    list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(characters)
    if txt != '':
        return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt

    dict_tb = godata.dict_tb
    tb_name = platoon_name.split('-')[0][:-1]
    tb_phase = platoon_name.split('-')[0][-1]
    platoon_side = platoon_name.split('-')[1]
    platoon_position = platoon_name.split('-')[2]
    tb_id = dict_tb[tb_name]["id"]
    tb_prefix = dict_tb[tb_id]["prefix"]
    side_name = dict_tb[tb_id]["zoneNames"][platoon_side]
    zone_name = tb_prefix+"_phase0"+tb_phase+"_"+side_name+"_recon01"

    if tb_name == "ROTE":
        platoon_id = "tb3-platoon-"+str(7-int(platoon_position))
    else:
        platoon_id = "hoth-platoon-"+platoon_position
    ec, txt = await connect_rpc.platoon_tb(server_id, zone_name, platoon_id, list_character_ids)

    return ec, txt

##############################################################
# print_unit_kit
# IN: character alias
##############################################################
def print_unit_kit(alias):
    list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([alias])
    if len(list_character_ids) == 0:
        return 1, "ERR: personnage inconnu"
    if len(list_character_ids) > 1:
        return 1, "ERR: un seul personnage à la fois"

    dict_units = godata.get("unitsList_dict.json")
    dict_abilities = godata.get("abilityList_dict.json")
    dict_lore = godata.get("lore_dict.json")
    dict_capas = godata.get("unit_capa_list.json")
    FRE_FR = godata.get("FRE_FR.json")
    unit_id = list_character_ids[0]

    #NAME
    nameKey = dict_units[unit_id]["nameKey"]
    descKey = dict_units[unit_id]["descKey"]
    output_txt = "**"+FRE_FR[nameKey]+"** : "+FRE_FR[descKey]+"\n"

    #LORE
    if nameKey in dict_lore:
        lore_desc = FRE_FR[dict_lore[nameKey]]
        lore_desc = goutils.remove_format_from_desc(lore_desc)
        output_txt+= lore_desc+"\n"

    #BASIC
    ability_id = dict_units[unit_id]["basicAttackRef"]["abilityId"]
    output_txt += print_ability(unit_id, ability_id, "Basique")

    #SPECIALS
    ab_id = 1
    for special in dict_units[unit_id]["limitBreakRef"]:
        ability_id = special["abilityId"]
        if ability_id == "generic_reinforcement":
            continue
        output_txt += print_ability(unit_id, ability_id, "Spéciale "+str(ab_id))
        ab_id+=1

    #LEADER
    if "leaderAbilityRef" in dict_units[unit_id]:
        ability_id = dict_units[unit_id]["leaderAbilityRef"]["abilityId"]
        output_txt += print_ability(unit_id, ability_id, "Chef")

    #UNIQUES
    ab_id = 1
    for special in dict_units[unit_id]["uniqueAbilityRef"]:
        ability_id = special["abilityId"]
        ability_name = FRE_FR[dict_abilities[ability_id]["nameKey"]]
        if ability_name == "Placeholder":
            continue
        output_txt += print_ability(unit_id, ability_id, "Unique "+str(ab_id))
        ab_id+=1

    return 0, output_txt

def print_ability(unit_id, ability_id, ability_type):
    output_txt = ""

    dict_abilities = godata.get("abilityList_dict.json")
    dict_capas = godata.get("unit_capa_list.json")
    FRE_FR = godata.get("FRE_FR.json")

    ability_name = FRE_FR[dict_abilities[ability_id]["nameKey"]]
    ability_name = goutils.remove_format_from_desc(ability_name)

    ability_desc = FRE_FR[dict_abilities[ability_id]["descKey"]]
    isZeta = False
    isOmicron = False
    if "cooldown" in dict_abilities[ability_id]:
        ability_cooldown = dict_abilities[ability_id]["cooldown"]
    else:
        ability_cooldown = 0

    if "tier" in dict_abilities[ability_id]:
        ability_desc = FRE_FR[dict_abilities[ability_id]["tier"][-1]["descKey"]]
        if "cooldownMaxOverride" in dict_abilities[ability_id]["tier"][-1]:
            ability_cooldown = dict_abilities[ability_id]["tier"][-1]["cooldownMaxOverride"]
        isZeta = dict_capas[unit_id][ability_id]["zetaTier"] < 99
        isOmicron = dict_capas[unit_id][ability_id]["omicronTier"] < 99

    if ability_name != "":
        ability_desc = goutils.remove_format_from_desc(ability_desc)
        output_txt+= "\n** "+ability_type+" - "+ability_name
        if isZeta:
            output_txt+= " - ZETA"
        if isOmicron:
            output_txt+= " - OMICRON"
        output_txt+= " **"
        if ability_cooldown > 0:
            output_txt+= " (délai de "+str(ability_cooldown)+")"
        output_txt+= " : "+ability_desc+"\n"

    return output_txt
