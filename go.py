# -*- coding: utf-8 -*-

import asyncio
from collections import Counter
import datetime
import difflib
from functools import reduce
import inspect
import itertools
import json
import math
import matplotlib
matplotlib.use('Agg') #Preventin GTK erros at startup
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import os
from PIL import Image, ImageDraw, ImageFont
import random
import re
import sys
from texttable import Texttable
import time

import config
import connect_gsheets
import connect_mysql
import connect_crinolo
import connect_rpc
import goutils
import guionbot_discord
import portraits
import parallel_work
import data as godata
import emojis
import bot_commands

FORCE_CUT_PATTERN = "SPLIT_HERE"
MAX_GVG_LINES = 50

SCORE_GREEN = 100
SCORE_ALMOST_GREEN = 95
SCORE_AMBER = 80
SCORE_RED = 50

emoji_check = "\N{WHITE HEAVY CHECK MARK}"
emoji_cross = "\N{CROSS MARK}"
emoji_frowning = "\N{SLIGHTLY FROWNING FACE}"

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

BOT_GFILE = None

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
    query = "SELECT name, id, allyCode FROM "\
           +"( "\
           +"  SELECT guilds.name, id, allyCode, update_period_hours, min(players.lastUpdated) as lastUpdated "\
           +"  FROM guilds "\
           +"  JOIN players on players.guildId = guilds.id "\
           +"  WHERE update_period_hours>0 "\
           +"  GROUP BY guilds.id "\
           +") T "\
           +"WHERE current_timestamp>timestampadd(HOUR, update_period_hours, lastUpdated) "\
           +"ORDER BY lastUpdated"
    goutils.log2('DBG', query)
    ret_table = connect_mysql.get_table(query)
    
    if ret_table != None:
        for line in ret_table:
            guild_name = line[0]
            guild_id = line[1]
            guild_allyCode = line[2]
            goutils.log2('INFO', "refresh guild " + guild_name \
                       +" with allyCode " + str(guild_allyCode))
            e, t, dict_guild = await load_guild(str(guild_allyCode), False, False)
            if e == 0 and dict_guild["profile"]['id'] == guild_id:
                e, t, dict_guild = await load_guild(str(guild_allyCode), True, False)
                break
            elif e == 0:
                goutils.log2('WAR', " Error during load_guild("+str(guild_allyCode)+"):"+t)
            else:
                goutils.log2('ERR', 1)
                return 1


    # Get the shards to be refreshed / every 24 hours
    query = "SELECT id, type "\
           +"FROM shards "\
           +"WHERE current_timestamp>timestampadd(HOUR, 24, lastUpdated) "\
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


    # Refresh the oldest known player
    query = "SELECT allyCode "\
           +"FROM players "\
           +"ORDER BY lastUpdated "\
           +"LIMIT 1"
    goutils.log2('DBG', query)
    ret_db = connect_mysql.get_value(query)
    
    if ret_db != None:
        allyCode = str(ret_db)
        goutils.log2('INFO', "refresh oldest player " + allyCode)
        e, t, d = await load_player(allyCode, 0, False)
        if e != 0:
            goutils.log2('ERR', t)
            return 1

    # Refresh the oldest known guild, but not its players
    query = "SELECT id "\
           +"FROM guilds "\
           +"ORDER BY lastUpdated "\
           +"LIMIT 1"
    goutils.log2('DBG', query)
    ret_db = connect_mysql.get_value(query)
    
    if ret_db != None:
        guild_id = str(ret_db)
        goutils.log2('INFO', "refresh oldest guild " + guild_id)
        e, t, d = await load_guild_from_id(guild_id, False, False)
        if e != 0:
            goutils.log2('ERR', t)
            return 1

    return 0

##################################
# Function: load_player
# inputs: txt_allyCode (string)
#         int force_update (0: update if not recently updated,
#                           1: force update,
#                           -1: do not update unless there is no JSON)
#         bool no_db: do not put player in DB
#         bool load_roster: read all characters and datacrons, update DB
#                           (False for quick guild update)
# return: err_code, err_text, dict_player
##################################
async def load_player(ac_or_id, force_update, no_db, load_roster=True):
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
            goutils.log2("DBG", 'reading file ' + json_file + '...')
            if os.path.isfile(json_file):
                if os.path.getsize(json_file) == 0:
                    goutils.log2("DBG", "... empty file, delete it")
                    #empty file, delete it
                    os.remove(json_file)
                    prev_dict_player = None
                    prev_dict_player_list = None
                else:
                    goutils.log2("DBG", "... correct file")
                    prev_dict_player = json.load(open(json_file, 'r'))
                    prev_dict_player = goutils.roster_from_list_to_dict(prev_dict_player)
                    prev_dict_player_list = goutils.roster_from_dict_to_list(prev_dict_player)
            else:
                goutils.log2("DBG", "... the file does not exist")
                prev_dict_player = None
                prev_dict_player_list = None
        else:
            goutils.log2("DBG", "Player "+ac_or_id+" unknown. Need to get whole data")
            recent_player = 0
            prev_dict_player = None
            prev_dict_player_list = None


    if ((not recent_player and force_update!=-1) or force_update==1 or prev_dict_player==None):
        goutils.log2("DBG", 'Requesting RPC data for player ' + ac_or_id + '...')
        ec, et, dict_player_list = await connect_rpc.get_extplayer_data(
                                               ac_or_id, 
                                               load_roster=load_roster)
        if ec != 0:
            goutils.log2("WAR", "RPC error ("+et+"). Using cache data from json")
            dict_player_list = prev_dict_player_list

        if dict_player_list == None:
            goutils.log2("ERR", 'Cannot get player data for '+ac_or_id)
            return 1, 'ERR: cannot get player data for '+ac_or_id, None

        goutils.log2("DBG", "after getplayer")

        #Add mandatory elements to compute stats
        # Stats only computed if the roster is included
        if load_roster:
            for unit in dict_player_list["rosterUnit"]:
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
            err_code, err_txt, dict_player_list = connect_crinolo.add_stats(dict_player_list)

            #Transform the roster into dictionary with key = defId
            dict_player = goutils.roster_from_list_to_dict(dict_player_list)

        else:
            #store previous roster / datacrons (if any) to pu them back when writng the file
            if "rosterUnit" in prev_dict_player:
                prev_roster = prev_dict_player["rosterUnit"]
            else:
                prev_roster = None
            if "datacron" in prev_dict_player:
                prev_datacron = prev_dict_player["datacron"]
            else:
                prev_datacron = None

            dict_player = dict_player_list

        playerId = dict_player["playerId"]
        player_name = dict_player["name"]

        goutils.log2("DBG", "success retrieving "+player_name+" from RPC with load_roster="+str(load_roster))
        
        if not no_db:
            # compute differences
            delta_dict_player = goutils.delta_dict_player(prev_dict_player, dict_player,
                                                          compare_rosters=load_roster)
        
            ###############
            # store json file
            # Put back roster and datacrons if not updated
            if not load_roster:
                if prev_roster!=None:
                    dict_player["rosterUnit"] = prev_roster
                if prev_datacron!=None:
                    dict_player["datacron"] = prev_datacron

            # Actually write the file
            json_file = "PLAYERS/"+playerId+".json"
            fjson = open(json_file, 'w')
            fjson.write(json.dumps(dict_player, indent=4))
            fjson.close()

            # update DB
            ec, et = await connect_mysql.update_player(delta_dict_player)
            if ec == 0:
                goutils.log2("DBG", "success updating "+dict_player['name']+" in DB")
            else:
                return 1, 'ERR: update_player '+ac_or_id+' returned an error', None
                
    else:
        dict_player = prev_dict_player
        player_name = dict_player["name"]
        goutils.log2('DBG', player_name + ' loaded from existing XML OK')
    
    goutils.log2('DBG', "END")
    return 0, "", dict_player

async def load_guild(txt_allyCode, load_players, cmd_request, 
                     ctx_interaction=None,
                     load_rosters=True,
                     force_update=False):
    # Get DB stored guild for the player
    query = "SELECT id FROM guilds "
    query+= "JOIN players ON players.guildName = guilds.name "
    query+= "WHERE allyCode = " + txt_allyCode
    goutils.log2("DBG", 'query: '+query)
    db_result = connect_mysql.get_value(query)

    if db_result == None or db_result == "":
        goutils.log2("WAR", 'Guild ID not found for '+txt_allyCode)
        ec, et, dict_guild = await connect_rpc.get_extguild_data_from_ac(txt_allyCode, False)
        if ec != 0:
            goutils.log2("ERR", "Cannot get guild data for "+txt_allyCode)
            return 1, "ERR Cannot get guild data for "+txt_allyCode, None
        guild_id = dict_guild["profile"]["id"]
    else:
        guild_id = db_result

    goutils.log2("DBG", 'Guild ID for '+txt_allyCode+' is '+guild_id)

    return await load_guild_from_id(guild_id, load_players, cmd_request, 
                                    ctx_interaction=ctx_interaction,
                                    load_rosters=load_rosters,
                                    force_update=force_update)

async def load_guild_from_id(guild_id, load_players, cmd_request,
                             ctx_interaction=None,
                             load_rosters=True,
                             force_update=False):
    #Get RPC guild data
    goutils.log2('DBG', 'Requesting RPC data for guild ' + guild_id)
    ec, et, dict_guild = await connect_rpc.get_extguild_data_from_id(guild_id, False)
    if ec != 0:
        json_file = "GUILDS/"+guild_id+".json"
        if os.path.isfile(json_file):
            goutils.log2("WAR", "RPC error ("+et+"). Using cache data from json")
            prev_dict_guild = json.load(open(json_file, 'r'))
            dict_guild = prev_dict_guild
        else:
            goutils.log2("ERR", "Cannot get guild data for "+txt_allyCode)
            return 1, "ERR Cannot get guild data for "+txt_allyCode, None

    guild_name = dict_guild["profile"]['name']
    guild_id = dict_guild["profile"]['id']
    total_players = dict_guild["profile"]["memberCount"]
    guild_gp = dict_guild["profile"]["guildGalacticPower"]
    if "member" in dict_guild:
        playerId_in_API = [x['playerId'] for x in dict_guild["member"]]
    else:
        playerId_in_API = []
    goutils.log2("INFO", "success retrieving "+guild_name+" ("\
                +str(total_players)+" players, "+str(guild_gp)+" GP) from RPC")
                
    # store json file
    json_file = "GUILDS/"+guild_id+".json"
    fjson = open(json_file, 'w')
    fjson.write(json.dumps(dict_guild, indent=4))
    fjson.close()

    #Get guild data from DB
    query = "SELECT guilds.name, guilds.lastUpdated, MIN(players.lastUpdated) FROM guilds "\
           +"JOIN players ON players.guildId=guilds.id "\
           +"WHERE id = '"+guild_id+"' "\
           +"GROUP BY guilds.name"
    goutils.log2('DBG', query)
    ret_line = connect_mysql.get_line(query)
    if ret_line != None:
        is_new_guild = False
        db_guild_name = ret_line[0]
        lastUpdated = ret_line[1]
        lastPlayerUpdated = ret_line[2]
    else:
        is_new_guild = True
        lastUpdated = None
        lastPlayerUpdated = None

    if is_new_guild:
        #Create guild in DB
        guild_name_txt = guild_name.replace("'", "''")
        query = "INSERT IGNORE INTO guilds(name, id) VALUES('"+guild_name_txt+"', '"+guild_id+"')"
        goutils.log2('DBG', query)
        connect_mysql.simple_execute(query)

        query = "INSERT INTO guild_evolutions(guild_id, description) "
        query+= "VALUES('"+guild_id+"', 'creation of the guild')"
        goutils.log2('DBG', query)
        connect_mysql.simple_execute(query)

    if not is_new_guild and (guild_name != db_guild_name):
        #update the name
        query = "UPDATE guilds SET name='"+guild_name.replace("'", "''")+"' "
        query+= "WHERE id='"+guild_id+"'"
        goutils.log2('DBG', query)
        connect_mysql.simple_execute(query)

        query = "INSERT INTO guild_evolutions(guild_id, description) "
        query+= "VALUES('"+guild_id+"', 'new name for the guild: "+guild_name.replace("'", "''")+"')"
        goutils.log2('DBG', query)
        connect_mysql.simple_execute(query)

    #Update guild values
    query = "UPDATE guilds "\
           +"SET players = "+str(total_players)+", "\
           +"gp = "+str(guild_gp)+" "\
           +"WHERE id = '"+guild_id+"'"
    goutils.log2('DBG', query)
    connect_mysql.simple_execute(query)

    #Update guild history of values
    query = "INSERT IGNORE INTO guild_gp_history(date, guild_id, players, gp) "\
           +"VALUES(CURDATE(), '"+guild_id+"', "+str(total_players)+", "+str(guild_gp)+") "
    goutils.log2('DBG', query)
    connect_mysql.simple_execute(query)

    #Update TB TW scores

    if load_players:
        #Get the list of players to detect which to add or remove
        query = "SELECT playerId FROM players "\
               +"WHERE guildId = '"+guild_id+"'"
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

        #Check if player data needs to be loaded from RPC
        if lastPlayerUpdated != None:
            delta_lastUpdated = datetime.datetime.now() - lastPlayerUpdated
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
        goutils.log2("DBG", "force_update="+str(force_update))

        if is_new_guild or need_refresh_due_to_time or need_to_add_players or force_update:
            #The guild needs to be loaded again
            guild_loading_status = parallel_work.get_guild_loading_status(guild_name)

            if is_new_guild or need_refresh_due_to_time or force_update:
                #add all players
                list_playerId_to_update = [x['playerId'] for x in dict_guild["member"]]
            else:
                #only some players to be added
                list_playerId_to_update = playerId_to_add
                total_players = len(list_playerId_to_update)

            if guild_loading_status != None:
                #The guild is already being loaded
                while guild_loading_status != None:
                    goutils.log2('INFO', "Guild "+guild_name+" already loading ("\
                            + guild_loading_status + "), waiting 30 seconds...")
                    await asyncio.sleep(30)
                    guild_loading_status = parallel_work.get_guild_loading_status(guild_name)
            else:
                #Ensure only one guild loading at a time
                list_other_guilds_loading_status = parallel_work.get_other_guilds_loading_status(guild_name)
                while len(list_other_guilds_loading_status) > 0:
                    goutils.log2('INFO', "Guild "+guild_name+" loading "\
                                +"will start after loading of "+str(list_other_guilds_loading_status))
                    if ctx_interaction!=None:
                        await bot_commands.command_ok(ctx_interaction[0], ctx_interaction[1], "En file d'attente derrière "+str(list_other_guilds_loading_status)+"..." , intermediate=True)
                    await asyncio.sleep(5)
                    list_other_guilds_loading_status = parallel_work.get_other_guilds_loading_status(guild_name)

                #Request to load this guild
                parallel_work.set_guild_loading_status(guild_name, "0/"+str(total_players))

                #add player data
                i_player = 0
                prev_display_time = 0
                for playerId in list_playerId_to_update:
                    i_player += 1
                    goutils.log2("INFO", guild_name+" player #"+str(i_player))
                    
                    e, t, d = await load_player(str(playerId), 0, False, load_roster=load_rosters)
                    goutils.log2("DBG", "after load_player...")
                    parallel_work.set_guild_loading_status(guild_name, str(i_player)+"/"+str(total_players))

                    goutils.log2("DBG", (ctx_interaction, prev_display_time,time.time()))
                    #update status to user
                    if ctx_interaction!=None:
                        if (time.time() - prev_display_time) > 10:
                            await bot_commands.command_ok(ctx_interaction[0], ctx_interaction[1], "chargement du joueur "+str(i_player)+"/"+str(len(list_playerId_to_update))+"...", intermediate=True)
                            prev_display_time = time.time()

                    goutils.log2("DBG", "after set_guild_loading_status...")
                    await asyncio.sleep(1)
                    goutils.log2("DBG", "after sleep...")

                parallel_work.set_guild_loading_status(guild_name, None)

        else:
            lastPlayerUpdated_txt = lastPlayerUpdated.strftime("%d/%m/%Y %H:%M:%S")
            goutils.log2('INFO', "Guild "+guild_name+" last update of players is "+lastPlayerUpdated_txt)

        #Erase guildName and guildId for alyCodes not detected from API
        if len(playerId_to_remove) > 0:
            query = "UPDATE players "\
                   +"SET guildName = '', guildMemberLevel = 2, guildId = '' "\
                   +"WHERE playerId IN "+str(tuple(playerId_to_remove)).replace(",)", ")")
            goutils.log2('DBG', query)
            connect_mysql.simple_execute(query)

        #Manage guild roles (leader, officers)
        query = "SELECT playerId, guildMemberLevel FROM players "\
               +"WHERE guildName = '"+guild_name.replace("'", "''")+"'"
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

    #Update dates in DB
    query = "UPDATE guilds "\
           +"SET lastUpdated = CURRENT_TIMESTAMP "\
           +"WHERE id = '"+guild_id+"' "
    goutils.log2('DBG', query)
    connect_mysql.simple_execute(query)

    if cmd_request:
        query = "UPDATE guilds "\
               +"SET lastRequested = CURRENT_TIMESTAMP "\
               +"WHERE id = '"+guild_id+"' "
        goutils.log2('DBG', query)
        connect_mysql.simple_execute(query)

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
                if ctx_interaction!=None:
                    await bot_commands.command_ok(ctx_interaction[0], ctx_interaction[1], "Chargement de la guilde déjà en cours via une autre commande..." , intermediate=True)
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

#IN: score_type (1: progress % / 2: yellow energy)
async def get_team_line_from_player(team_name_path, dict_teams, dict_team_gt, gv_mode, player_name, score_type):
    dict_unitsList = godata.get("unitsList_dict.json")
    line = ''

    #manage team_name in a path for recursing requests
    team_name = team_name_path.split('/')[-1]
    if team_name_path.count(team_name) > 1:
        #recurring loop, stop it
        return {"score": 0, "unlocked": False, "line": "", "nogo": False, "list_char": [], "unlock_rarity": 7}

    dict_team = dict_team_gt[team_name]
    unlock_rarity = dict_team["rarity"]
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
    d_stars = {0:0, 1:10, 2:25, 3:50, 4:80, 5:145, 6: 230, 7:330}
    # Loop on categories within the goals
    for i_subobj in range(0, nb_subobjs):
        dict_char_subobj = objectifs[i_subobj][2]

        for character_id in dict_char_subobj:
            await asyncio.sleep(0)

            #goutils.log2("DBG", "character_id: "+character_id)
            progress = 0
            progress_100 = 0
            
            character_obj = dict_char_subobj[character_id]

            #Rarity
            req_rarity_min = character_obj[1]
            req_rarity_reco = character_obj[3]
            if req_rarity_min == '' or gv_mode:
                req_rarity_min = 1

            #Gear
            req_gear_min = character_obj[2]
            req_gear_reco = character_obj[4]
            req_relic_min=0
            if req_gear_min == '' or gv_mode:
                req_gear_min = 1
            elif type(req_gear_min) == str:
                if req_gear_min[0] == 'G':
                    req_gear_min=int(req_gear_min[1:])
                else: #assumed to be 'R'
                    req_relic_min=int(req_gear_min[-1])
                    req_gear_min=13
                
            req_relic_reco=0
            if req_gear_reco == '':
                req_gear_reco = 1
            elif type(req_gear_reco) == str:
                if req_gear_reco[0] == 'G':
                    req_gear_reco=int(req_gear_reco[1:])
                else: #assumed to be 'R'
                    req_relic_reco=int(req_gear_reco[-1])
                    req_gear_reco=13


            i_character = character_obj[0]
            character_name = character_obj[7]

            if character_id in dict_player:
                if dict_player[character_id]['reserved']:
                    character_nogo = True
                else:
                    character_nogo = False

                #Etoiles
                player_rarity = dict_player[character_id]['currentRarity']
                progress_100 = progress_100 + 1
                progress = progress + min(1, d_stars[player_rarity] / d_stars[req_rarity_reco])
                if player_rarity < req_rarity_min:
                    character_nogo = True
                
                player_gear = dict_player[character_id]['currentTier']
                if player_gear < 13:
                    player_relic = 0
                else:
                    player_relic = dict_player[character_id]['relic']['currentTier'] - 2

                progress_100 = progress_100 + 1
                progress = progress + min(1, (player_gear+player_relic) / (req_gear_reco+req_relic_reco))
                if (player_gear+player_relic) < (req_gear_min+req_relic_min):
                    character_nogo = True

                #Zetas
                req_zetas = character_obj[5].split(',')
                while '' in req_zetas:
                    req_zetas.remove('')

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
                while '' in req_omicrons:
                    req_omicrons.remove('')

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
                            campaignId = event[0]["campaignId"]
                            campaignMapId = event[0]["campaignMapId"]
                            if campaignId.startswith('C01'):
                                if campaignId[3:] == 'L':
                                    color_emoji = "\N{Large Yellow Circle}LS"
                                elif campaignId[3:] == 'D':
                                    color_emoji = "\N{Large Yellow Circle}DS"
                                elif campaignId[3:] == 'H':
                                    color_emoji = "\N{LARGE RED CIRCLE}"
                                elif campaignId[3:] == 'SP':
                                    color_emoji = "\N{LARGE BLUE CIRCLE}"
                                else:
                                    color_emoji = None

                                color_emoji+= campaignMapId[-1]

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

                if score_type == 1:
                    character_display += " - " + str(character_progress_100) +"%"
                if score_type == 2:
                    #get required yellow energy for shards and kyros
                    kyro_energy, shard_energy = get_unit_farm_energy({"rosterUnit":dict_player}, character_id, req_gear_reco)
                    yellow_energy = kyro_energy
                    if "yellow" in shard_energy:
                        yellow_energy += shard_energy["yellow"]
                    character_progress = yellow_energy
                    character_display += " - " + str(int(yellow_energy))

                tab_progress_player[i_subobj][i_character - 1][0] = character_progress
                tab_progress_player[i_subobj][i_character - 1][1] = character_display
                tab_progress_player[i_subobj][i_character - 1][2] = character_nogo
                tab_progress_player[i_subobj][i_character - 1][3] = character_id
                tab_progress_player[i_subobj][i_character - 1][4] = 1

                goutils.log2("DBG", tab_progress_player[i_subobj][i_character - 1])

            else:
                # unlocked unit
                if gv_mode:
                    character_id_team = character_id + '-GV'
                    if character_id_team in dict_teams[player_name][1]:
                        unit_progress = await get_team_line_from_player(team_name_path+'/'+character_id_team,
                                                                    dict_teams, 
                                                                    dict_team_gt, 
                                                                    gv_mode, 
                                                                    player_name, 
                                                                    score_type)
                        score = unit_progress["score"]
                        character_display = unit_progress["line"]
                        nogo = unit_progress["nogo"]
                        unlock_rarity = unit_progress["unlock_rarity"]

                        max_rarity_score = min(1, d_stars[unlock_rarity] / d_stars[req_rarity_reco])
                        if dict_unitsList[character_id]['combatType']==1:
                            #Unlocking a character only gives the rarity so by default 50%
                            score = max_rarity_score * score / 200.0
                        else:
                            #But for a ship the rarity is mostly everything
                            score = max_rarity_score * score / 100.0

                        #weight = len(list_char)
                        weight = 1
                        character_display = "\N{CROSS MARK} "+\
                                            character_name + \
                                            " n'est pas débloqué"
                    else:
                        score = 0
                        character_display = "\N{CROSS MARK} "+\
                                            character_name + \
                                            " n'est pas débloqué"

                        #Add farming info
                        for event in dict_unitsList[character_id]['farmingInfo']:
                            campaignId = event[0]["campaignId"]
                            if campaignId.startswith('C01'):
                                if campaignId[3:] == 'L':
                                    color_emoji = "\N{Large Yellow Circle}LS"
                                elif campaignId[3:] == 'D':
                                    color_emoji = "\N{Large Yellow Circle}DS"
                                elif campaignId[3:] == 'H':
                                    color_emoji = "\N{LARGE RED CIRCLE}"
                                elif campaignId[3:] == 'SP':
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

                if score_type == 1:
                    character_display += " - " + str(int(score*100)) +"%"
                if score_type == 2:
                    #get required yellow energy for shards and kyros
                    kyro_energy, shard_energy = get_unit_farm_energy({"rosterUnit":dict_player}, character_id, req_gear_reco)
                    yellow_energy = kyro_energy
                    if "yellow" in shard_energy:
                        yellow_energy += shard_energy["yellow"]
                    score = yellow_energy
                    character_display += " - " + str(int(yellow_energy))

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
    yellow_energy = 0
    list_char_id = []
    sorted_tab_progress = [[]] * len(tab_progress_player)
    for i_subobj in range(0, nb_subobjs):
        #Sort best characters first
        min_perso = objectifs[i_subobj][1] #Minimum characters to be ready for this sub objective

        if score_type == 1:
            #sort by %, descending (higher score on top)
            sorted_tab_progress[i_subobj] = sorted(tab_progress_player[i_subobj], key=lambda x: ((-x[0] * (not x[2])), -x[0]))
        else:
            #sort by yellow energy, ascending (higher score on top)
            sorted_tab_progress[i_subobj] = sorted(tab_progress_player[i_subobj], key=lambda x: ((x[0] * (not x[2])), x[0]))
        #print(sorted_tab_progress)

        #remove already used characters
        for char in sorted_tab_progress[i_subobj]:
            if char[3] in list_char_id:
                sorted_tab_progress[i_subobj].remove(char)

        #Compute scores on the best characters
        top_tab_progress = sorted_tab_progress[i_subobj][:min_perso]

        #Add empty characters in case existing ones are not enough compared to min_perso
        if len(top_tab_progress) < min_perso:
            top_tab_progress = top_tab_progress + [[0, '', False, '', 1]]*(min_perso-len(top_tab_progress))

        top_scores = [x[0] for x in top_tab_progress]
        sum_scores = sum(top_scores)
        top_weighted_scores = [x[0] * (not x[2]) * x[4] for x in top_tab_progress]
        sum_weighted_scores = sum(top_weighted_scores)
        top_weights = [x[4] for x in top_tab_progress]
        sum_weights = sum(top_weights)

        #Remove used characters (only if part of the best as used to compute the score)
        top_chars = [x[3] for x in top_tab_progress]
        for x in tab_progress_player[i_subobj]:
            char_id = x[3]
            if char_id in top_chars:
                list_char_id.append(char_id)

        if score_type==1:
            score += sum_weighted_scores
            score100 += sum_weights
        else:
            score += sum_scores

        if 0.0 in top_weighted_scores:
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
    if score_type == 1:
        score = score / score100 * 100

    goutils.log2("DBG", "list_char_id = " + str(list_char_id))
        
    unlocked = False
    if gv_mode and team_name[-3:]=="-GV":
        # in gv_mode, we check if the target character is fully unlocked
        # with the target max rarity
        target_character = team_name[:-3]
        target_rarity = dict_team["rarity"]
        if target_character in dict_player:
            if dict_player[target_character]["currentRarity"] >= target_rarity:
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

    return {"score": score, "unlocked": unlocked, "line": line,
            "nogo": score_nogo, "list_char": list_char_id, "unlock_rarity": unlock_rarity}

def get_team_header(team_name, objectifs):
    dict_capas = godata.get("unit_capa_list.json")

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
                        perso_min_display += '\\*G' + "{:02d}".format(perso_gear_min)                        
                    else:
                        perso_min_display += '\\*R' + str(perso_relic_min)

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
                        perso_reco_display += '\\*G' + "{:02d}".format(perso_gear_reco)                        
                    else:
                        perso_reco_display += '\\*R' + str(perso_relic_reco)

                    #Zetas
                    req_zetas = objectifs[i_level][2][perso][5].split(',')
                    while '' in req_zetas:
                        req_zetas.remove('')

                    #print(goutils.get_capa_from_shorts(perso, req_zetas))
                    req_zeta_names = [dict_capas[perso][x[1]]["name"]+" ("+x[0]+")" for x in goutils.get_capa_from_shorts(perso, req_zetas)]
                    req_omicrons = objectifs[i_level][2][perso][6].split(',')
                    while '' in req_omicrons:
                        req_omicrons.remove('')

                    req_omicron_names = [x[1] for x in goutils.get_capa_from_shorts(perso, req_omicrons)]
                    
                    perso_name = objectifs[i_level][2][perso][7]
                    entete += "- " + perso_name + ' (' + perso_min_display + ' à ' + \
                            perso_reco_display + ', zetas=' + str(req_zeta_names) + \
                            ', omicrons=' + str(req_omicron_names) + ')\n'

    return entete

####################################################
#IN: compute_guild (0: player, 1: guild, 2: shard)
#IN: gv_mode (0: VTJ, 1: GVJ, 2: FTJ)
#IN: score_type (1: progress % / 2: yellow energy)
####################################################
async def get_team_progress(list_team_names, txt_allyCode, guild_id, gfile_name, compute_guild, exclusive_player_list, gv_mode, dict_tw_def, score_type):
    dict_unitsList = godata.get("unitsList_dict.json")
    ret_get_team_progress = {}

    #Recuperation des dernieres donnees sur gdrive
    ec, list_team_bot, dict_team_bot = connect_gsheets.load_config_teams(BOT_GFILE, False)
    if gfile_name != BOT_GFILE:
        ec, list_team_guild, dict_team_guild = connect_gsheets.load_config_teams(guild_id, False)
        if ec == 2:
            return "", "ERR: pas de fichier de config pour ce serveur"
        elif ec == 3:
            return "", "ERR: pas d'onglet 'teams' dans le fichier de config"
        elif ec != 0:
            return "", "ERR: erreur en lisant le fichier de config"
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
        if "guildName" in d:
            guild_name = d["guildName"]
        else:
            guild_name = ''
            
    elif compute_guild==1:
        #Get data for the guild and associated players
        err_code, err_txt, guild = await load_guild(txt_allyCode, True, True)
        if err_code != 0:
            goutils.log2("WAR", "cannot get guild data from RPC. Using previous data.")
        collection_name = guild["profile"]["name"]
        guild_name = collection_name
    else:
        shard_info = connect_mysql.get_shard_from_player(txt_allyCode, shard_type)
        player_shard = shard_info[0]
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
           +"stat5 as speed, "\
           +"equipment "\
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
        query += "AND guild_teams.guild_id = '"+guild_id+"'\n"

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
                roster_skills.level \
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
            query += "WHERE players.guildName = '"+collection_name.replace("'", "''") +"'\n"
        else:
            query += "WHERE players."+shard_type+"Shard_id = \
                    (SELECT "+shard_type+"Shard_id FROM players WHERE allyCode='"+txt_allyCode+"')\n"
        query += "AND NOT guild_teams.name LIKE '%-GV'\n"
        query += "AND guild_teams.guild_id = '"+guild_id+"'\n"
           
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
                team_name_txt = dict_unitsList[team_name[:-3]]["name"]
                list_team_txt = [dict_unitsList[x[:-3]]["name"] for x in filtered_list_team_gt]
                ret_get_team_progress[team_name] = \
                        "ERREUR: Guide de Voyage inconnu pour **" + \
                        team_name_txt + "**. Liste=" + str(list_team_txt)
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
                unit_progress = await get_team_line_from_player(team_name,
                    dict_teams, dict_team_gt, gv_mode>0, player_name, score_type)
                score = unit_progress["score"]
                unlocked = unit_progress["unlocked"]
                line = unit_progress["line"]
                nogo = unit_progress["nogo"]
                list_char = unit_progress["list_char"]

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

async def print_vtg(list_team_names, txt_allyCode, guild_id, gfile_name, tw_mode):

    #Manage -TW option
    if tw_mode:
        ec, et, ret_dict = await connect_rpc.get_tw_active_players(guild_id, 0)
        if ec != 0:
            return ec, et
        list_active_players = ret_dict["active"]

        ec, et, ret_data = await get_tw_def_attack(guild_id, -1)
        if ec != 0:
            return ec, et
        dict_def_toon_player = ret_data["homeDef"]

    else:
        dict_def_toon_player = {}
        list_active_players = None

    guild_name, ret_get_team_progress = await get_team_progress(list_team_names, txt_allyCode, 
                                              guild_id, gfile_name, 1, list_active_players,
                                              0, dict_def_toon_player, 1)
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

                        connect_mysql.update_gv_history(
                            "", name, team, True,
                            score, unlocked, "go.bot")

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

async def print_vtj(list_team_names, txt_allyCode, guild_id, gfile_name, tw_mode):
    #Manage -TW option
    if tw_mode:
        ec, et, ret_dict = await connect_rpc.get_tw_active_players(guild_id, 0)
        if ec != 0:
            return ec, et
        list_active_players = ret_dict["active"]

        ec, et, ret_data = await get_tw_def_attack(guild_id, -1)
        if ec != 0:
            return ec, et, None
        dict_def_toon_player = ret_data["homeDef"]
    else:
        dict_def_toon_player = {}
        list_active_players = None

    player_name, ret_get_team_progress = await get_team_progress(list_team_names, txt_allyCode, 
                                              guild_id, gfile_name, 0, list_active_players,
                                              0, dict_def_toon_player, 1)
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

                    connect_mysql.update_gv_history(txt_allyCode, "", team, True,
                                                    score, unlocked, "go.bot")
            
                    list_char_allycodes = [[list_char, txt_allyCode, ""]]
                    if tw_mode:
                        image_mode = "TW"
                    else:
                        image_mode = ""
                    e, t, images = await get_character_image(list_char_allycodes, True, False, image_mode, guild_id)

    #In case of several teams, don't display images
    if len(ret_get_team_progress) > 1:
        images = None

    return 0, ret_print_vtx, images

def print_fegv(txt_allyCode, show_all=False):
    if not show_all:
        #Get all characters from Journey Guide, and current status for the player
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
    else:
        #Get all characters, and current status for the player
        query = "SELECT 'farm', T.defId, 7, rarity FROM (SELECT DISTINCT defId FROM roster) T " \
              + "LEFT JOIN roster ON (T.defId=roster.defId AND allyCode="+txt_allyCode+") " \
              + "WHERE (isnull(rarity) OR rarity<7) "

    goutils.log2("DBG", query)
    ret_db = connect_mysql.get_table(query)
    dict_unitsList = godata.get("unitsList_dict.json")

    ret_print_fegv = ""
    for line in ret_db:
        if show_all:
            gv_target_name = 'farm'
        else:
            gv_target_id = line[0][:-3]
            gv_target_name = dict_unitsList[gv_target_id]['name']

        character_id = line[1]
        character_name = dict_unitsList[character_id]['name']

        if line[3] == None:
            character_display = "["+gv_target_name+"] "+character_name+" non-débloqué"
        else:
            character_display = "["+gv_target_name+"] "+character_name+" "+str(line[3])+"/"+str(line[2])+" étoiles"

        for event in dict_unitsList[character_id]['farmingInfo']:
            campaignId = event[0]["campaignId"]
            if campaignId.startswith('C01'):
                if campaignId[3:] == 'L':
                    color_emoji = "\N{Large Yellow Circle}LS"
                elif campaignId[3:] == 'D':
                    color_emoji = "\N{Large Yellow Circle}DS"
                elif campaignId[3:] == 'H':
                    color_emoji = "\N{LARGE RED CIRCLE}"
                elif campaignId[3:] == 'SP':
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

async def print_ftj(txt_allyCode, team, guild_id, gfile_name):
    ret_print_ftj = ""

    player_name, ret_get_team_progress = await get_team_progress([team], txt_allyCode, guild_id, gfile_name, 0, None, 2, {}, 1)
    #print(team)
    #print(ret_get_team_progress)
    if type(ret_get_team_progress) == str:
        return 1, ret_get_team_progress

    list_lines = []

    if not team in ret_get_team_progress:
        return 1, "Team "+team+" not defined "+str(list(ret_get_team_progress.keys()))

    ret_team = ret_get_team_progress[team]
    #print(ret_get_team_progress)
    if type(ret_team) == str:
        #error
        ret_print_ftj += ret_team
    else:
        for [player_score, unlocked, player_txt, player_nogo, player_name, list_char] in ret_team[0]:
            ret_print_ftj += "Progrès de farm de la team "+team+" pour "+player_name+"\n"
            ret_print_ftj += player_txt + "> Global: "+ str(int(player_score))+"%"
            connect_mysql.update_gv_history(txt_allyCode, "", team, True,
                                            player_score, unlocked, "go.bot")

    return 0, ret_print_ftj

#IN: score_type (1: progress % / 2: yellow energy)
async def print_gvj(list_team_names, txt_allyCode, score_type):
    ret_print_gvj = ""

    player_name, ret_get_team_progress = await get_team_progress(list_team_names, txt_allyCode, None, BOT_GFILE, 0, None, 1, {}, score_type)
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
            # Get data for unique player
            [player_score, unlocked, player_txt, player_nogo, player_name, list_char] = ret_team[0][0]

            if score_type == 1:
                ret_print_gvj += "Progrès dans le Guide de Voyage pour "+player_name+" - "+character_id+"\n"
            else:
                ret_print_gvj += "Reste-à-farmer dans le Guide de Voyage pour "+player_name+" - "+character_id+"\n"
            ret_print_gvj += "(Les persos avec -- ne sont pas pris en compte pour le score)\n"
            ret_print_gvj += player_txt + "> Global: "+ str(int(player_score))

            if score_type == 1:
                ret_print_gvj += "%"

            connect_mysql.update_gv_history(txt_allyCode, "", character_id, True,
                                            player_score, unlocked, "go.bot")

    else:
        #Several teams
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
                                    str(int(player_score))
                    if score_type == 1:
                        new_line += "%\n"
                    else:
                        new_line += "\n"

                    list_lines.append([player_score, new_line, player_unlocked])
                    connect_mysql.update_gv_history(txt_allyCode, "", character_id, True,
                                                    player_score, player_unlocked, "go.bot")
                                            
        if score_type == 1:
            #Teams are sorted with the best progress on top, unlocked first
            list_lines = sorted(list_lines, key=lambda x: (-int(x[2]), -x[0]))
        else:
            #Teams are sorted with the lowest RAF, unlocked first
            list_lines = sorted(list_lines, key=lambda x: (-int(x[2]), x[0]))
        if player_name != '':
            if score_type == 1:
                ret_print_gvj += "Progrès dans le Guide de Voyage pour "+player_name+"\n"
            else:
                ret_print_gvj += "Reste-à-farmer dans le Guide de Voyage pour "+player_name+"\n"
        for line in list_lines:
            score = line[0]
            txt = line[1]
            unlocked = line[2]
            if score_type == 1:
                #progress in %
                if unlocked:
                    ret_print_gvj += "\N{WHITE HEAVY CHECK MARK}"
                elif score > 95:
                    ret_print_gvj += "\N{WHITE RIGHT POINTING BACKHAND INDEX}"
                elif score > 80:
                    ret_print_gvj += "\N{CONFUSED FACE}"
                else:
                    ret_print_gvj += "\N{UP-POINTING RED TRIANGLE}"
            else: # score in yellow energy
                if unlocked:
                    ret_print_gvj += "\N{WHITE HEAVY CHECK MARK}"
                elif score == 0:
                    ret_print_gvj += "\N{WHITE RIGHT POINTING BACKHAND INDEX}"
                else:
                    ret_print_gvj += "\N{UP-POINTING RED TRIANGLE}"
            ret_print_gvj += txt

    return 0, ret_print_gvj
                        
async def print_gvg(list_team_names, txt_allyCode):
    ret_print_gvg = ""

    guild_name, ret_get_team_progress = await get_team_progress(list_team_names, txt_allyCode, None, BOT_GFILE, 1, None, 1, {}, 1)

    if type(ret_get_team_progress) == str:
        return 1, ret_get_team_progress

    list_lines = []
    one_valid_team = False # True if at least one result to display
    for team in ret_get_team_progress:
        ret_team = ret_get_team_progress[team]
        character_id = team[:-3]
        if type(ret_team) == str:
            #error
            ret_print_gvg += ret_team + "\n"
        else:
            one_valid_team = True
            for [player_score, player_unlocked, player_txt, player_nogo, player_name, list_char] in ret_team[0]:
                if not player_unlocked:
                    new_line = character_id + " - "+ player_name + ": " + \
                                    str(int(player_score)) + "%\n"
                    list_lines.append([player_score, new_line, player_unlocked])
                    if not player_unlocked and player_score>80:
                        connect_mysql.update_gv_history("", player_name, character_id, True,
                                                        player_score, player_unlocked, "go.bot")

    if one_valid_team:
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
    else:
        ret_print_gvg += emojis.redcross + " aucune team valable à afficher"
            
    return 0, ret_print_gvg

async def print_gvs(list_team_names, txt_allyCode):
    ret_print_gvs = ""

    guild_name, ret_get_team_progress = await get_team_progress(list_team_names, txt_allyCode, None, BOT_GFILE, 2, None, 1, {}, 1)

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
async def print_character_stats(characters, options, txt_allyCode, compute_guild, guild_id, tw_zone):
    dict_unitsList = godata.get("unitsList_dict.json")
    ret_print_character_stats = ''

    #list of stats used as columns (full name, column title)
    #This is not the list used for sorting with options
    list_stats_for_display=[['speed', "Vit"],
                            ['physical damages', "DegPhy"],
                            ['special damages', "DegSpé"],
                            ['health', " Santé"],
                            ['protection', "Protec"],
                            ['potency', "Pouvoir"],
                            ['tenacity', "Ténacité"],
                            ['critical damages', "DegCrit"],
                            ['physical critical chance', "PhyCdC"]]

    #manage sorting options
    sort_option_id=0 # sort by name
    if len(options) == 1:
        sort_option_alias = options[0][1:].lower()

        #Check if sorting by gear or rarity
        if sort_option_alias in ["étoiles", "etoiles", "rarity", "stars"]:
            sort_option_id = -1
        elif sort_option_alias in ["gear", "relic"]:
            sort_option_id = -2
        else:
            #then, look for the sorting statistic
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
                while '' in tab_virtual_character:
                    tab_virtual_character.remove('')

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
        elif sort_option_id == -1:
            ret_print_character_stats += " (tri par étoiles)\n"
        elif sort_option_id == -2:
            ret_print_character_stats += " (tri par gear/relic)\n"
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
            if not guild_id in connect_rpc.get_dict_bot_accounts():
                return "ERR: cannot detect TW opponent in this server"

            rpc_data = await connect_rpc.get_tw_status(guild_id, 0)
            tw_id = rpc_data["tw_id"]
            if tw_id == None:
                return "ERR: no TW ongoing"

            list_opponent_squads = rpc_data["awayGuild"]["list_defenses"]
            tuple_opp_players = tuple(set([x["player_name"] for x in list_opponent_squads]))
            if len(tuple_opp_players)==0:
                return "ERR: impossible de détecter les adversaires sur cette zone"

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
                zone=team["zone_short_name"]
                if tw_zone=="all" or zone==tw_zone:
                    team_char_ids = [x["unitId"] for x in team["list_defId"]]
                    if character_id in team_char_ids:
                        team_player_name = team["player_name"]
                        dict_tw_zone_players[team_player_name] = zone

        #Get data for the guild and associated players
        err_code, err_txt, guild = await load_guild(txt_allyCode, True, True)
        if err_code != 0:
            return "ERR: cannot get guild data from RPC"
                            
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
        elif sort_option_id == -1:
            ret_print_character_stats += " (tri par étoiles)\n"
        elif sort_option_id == -2:
            ret_print_character_stats += " (tri par gear/relic)\n"
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
        if sort_option_id > 0:
            stat_txt = str(sort_option_id)
            list_print_stats = sorted(list_print_stats,
                key=lambda x: -x[2][stat_txt] if stat_txt in x[2] else 0)
        elif sort_option_id == -1:
            #by rarity
            list_print_stats = sorted(list_print_stats,
                    key=lambda x: [-int(x[1].split('*')[0]),
                                   -10*ord(x[1].split('*')[1][0])-int(x[1].split('*')[1][1:])] \
                                   if len(x[1])>2 else [-int(x[1].split('*')[0]), 0] )
        elif sort_option_id == -2:
            #by gear/relic
            list_print_stats = sorted(list_print_stats,
                    key=lambda x: [-10*ord(x[1].split('*')[1][0])-int(x[1].split('*')[1][1:]),
                                   -int(x[1].split('*')[0])] \
                                   if len(x[1])>2 else [0, -int(x[1].split('*')[0])] )
        
        ret_print_character_stats += "=====================================\n"

        ### Title line
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

        ### value lines
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
    else:
        ret_print_character_stats += "Aucun personnage trouvé"

    return ret_print_character_stats

##############################################
def get_distribution_graph(values,               #list of values to distribute
                           values_2,             #Optional 2nd list of values to put on top of first one
                           bin_count,            #Amount of bons for the distribution
                           bin_list,             #ONLY if bin_count=None, to force the bins
                           bin_labels,           #ONLY if bin_count=None, to give names to bins
                           title,                #Title of the graph
                           x_title,              #Name of X axis
                           y_title,              #Name of Y axis
                           legend,               #Optional name of 1st serie
                           legend_2,             #Optional name of 2nd serie
                           highlight_value=None, #Optional value for which create a red virtual bin
                           ts_to_date=False):    #Optional value for which create a red virtual bin

    #auto layout, to ensure everythin stays in the image
    plt.rcParams.update({'figure.autolayout': True})

    # Create figure
    fig, ax = plt.subplots()

    #pre-calculate bins to align histograms
    if bin_count != None:
        #Automatic bins, from a count
        if values_2 != None:
            bins=np.histogram(np.hstack((values, values_2)), bins=bin_count)[1]
            bin_count = len(bins)
        else:
            bins = bin_count
    else:
        #Fixed bins as input
        bins = bin_list

    # 1st hist
    counts, bins = np.histogram(values, bins=bins)
    if ts_to_date:
        from_timestamp = np.vectorize(lambda x: datetime.datetime.utcfromtimestamp(x))
        ax.stairs(counts, edges=from_timestamp(bins), color='blue', label=legend, fill=True)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m %H:%M"))

        #rotate labels
        labels = ax.get_xticklabels()
        plt.setp(labels, rotation=45, horizontalalignment='right')
    else:
        ax.stairs(counts, edges=bins, color='blue', label=legend, fill=True)

    # 2nd hist
    if values_2 != None:
        counts_2, bins = np.histogram(values_2, bins=bins)
        ax.stairs(counts_2, edges=bins, label=legend_2, color='lightblue', fill=True)

    # bin labels in X axis
    if bin_labels != None:
        ax.set_xticks(list(bin_labels.keys()))
        ax.set_xticklabels(list(bin_labels.values()), ha="left")

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
    image = get_distribution_graph(guild_stats, None, 20, None, None, graph_title, "PG du joueur", "nombre de joueurs", "", "")
    logo_img= portraits.get_guild_logo(dict_guild, (80, 80))
    image.paste(logo_img, (10,10), logo_img)
    
    return 0, "", image

#################################
# Function: get_gac_distribution
# IN: txt_allyCode: an allyCode in the target guild
# return: err_code, err_txt, image
#################################
async def get_gac_distribution(txt_allyCode):
    #Load or update data for the guild
    #use only the guild data from the API
    err_code, err_txt, dict_guild = await load_guild(txt_allyCode, True, True)
    if err_code != 0:
        return 1, "ERR: cannot get guild data from RPC", None

    #Get GAC level in numbers
    query = "select " \
            "case left(grand_arena_rank,2) " \
            "when 'KY' then 20 " \
            "when 'AU' then 15 " \
            "when 'CH' then 10 " \
            "when 'BR' then 5 " \
            "else 0 end + 5 - right(grand_arena_rank,1) " \
            "from players where guildId = (select guildId from players where allyCode="+txt_allyCode+") "
    goutils.log2("DBG", query)
    guild_stats = connect_mysql.get_column(query)
    guild_name = dict_guild["profile"]["name"]

    graph_title = "Classement GAC " + guild_name + " ("+str(len(guild_stats))+" joueurs)"

    #compute graph
    image = get_distribution_graph(guild_stats, None, None, 
                                   list(range(26)), # [0 - 25] so that the 24 are in the 24-25 bin
                                   {0:'Carbonite',
                                    5:'Bronzium',
                                    10:'Chromium',
                                    15:'Aurodium',
                                    20:'Kyber'},
                                   graph_title, "Classement GAC", "nombre de joueurs", "", "")
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
async def get_character_image(list_characters_allyCode, is_ID, refresh_player, game_mode, guild_id):
    err_code = 0
    err_txt = ''

    #Get data for all players
    #print(list_characters_allyCode)
    list_allyCodes = list(set([x[1] for x in list_characters_allyCode]))

    #Get reserved TW toons
    if game_mode == "TW":
        ec, et, ret_data = await get_tw_def_attack(guild_id, 0)
        if ec != 0:
            return 1, et, None
        dict_def_toon_player = ret_data["homeDef"]
    
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
        image = portraits.get_image_from_defIds(ids, dict_player, tw_terr, game_mode)
        list_images.append(image)
    
    return err_code, err_txt, list_images

#################################
# Function: get_tw_battle_images
# return: err_code, err_txt, list of images
#################################
async def get_tw_battle_image(list_char_attack, allyCode_attack, \
                        character_defense, guild_id):
    war_txt = ""

    dict_unitsList = godata.get("unitsList_dict.json")

    rpc_data = await connect_rpc.get_tw_status(guild_id, 0)
    tw_id = rpc_data["tw_id"]
    if tw_id == None:
        return 1, "ERR: aucune GT en cours\n", None

    list_opponent_squads = rpc_data["awayGuild"]["list_defenses"]
    if len(list_opponent_squads) == 0:
        goutils.log2("ERR", "aucune phase d'attaque en cours en GT")
        return 1, "ERR: aucune phase d'attaque en cours en GT\n", None

    guildName = rpc_data["opp_guildName"]

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
        territory = opp_squad["zone_short_name"]
        player_name = opp_squad["player_name"]
        squad_char_ids = [x["unitId"] for x in opp_squad["list_defId"]]
        list_opp_squad_ids.append([territory, player_name, squad_char_ids])

    list_opp_squads_with_char = list(filter(lambda x:char_def_id in x[2], list_opp_squad_ids))
    if len(list_opp_squads_with_char) == 0:
        return 1, 'ERR: '+character_defense+' ne fait pas partie des teams en défense\n', None

    # Look for the name among known player names in DB
    query = "SELECT name, allyCode "
    query+= "FROM players "
    query+= "WHERE guildName='"+guildName.replace("'", "''")+"' "
    goutils.log2("DBG", query)
    results = connect_mysql.get_table(query)
    dict_DB_names = {}
    for line in results:
        dict_DB_names[line[0]] = str(line[1])

    for opp_squad in list_opp_squads_with_char:
        player_name = opp_squad[1]

        if not player_name in dict_DB_names:
            goutils.log2("ERR", player_name+' ne fait pas partie des joueurs connus de la guilde '+guildName)
            return 1, "ERR: "+player_name+" ne fait pas partie des joueurs connus dans la guilde "+guildName, None
        opp_squad[1] = dict_DB_names[player_name]

    #print(list_opp_squads_with_char)
    list_char_allycodes = []
    list_char_allycodes.append([list_id_attack, allyCode_attack, ''])
    for opp_squad in list_opp_squads_with_char:
        if not opp_squad[1] == '':
            list_char_allycodes.append([opp_squad[2], opp_squad[1], opp_squad[0]])

    #print(list_char_allycodes)
    ec, et, images = await get_character_image(list_char_allycodes, True, False, 'TW', guild_id)
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
        while '' in tab_alias:
            tab_alias.remove('')

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

    image = get_distribution_graph(stat_g13_values, guild_values, 50, None, None, title, "valeur de la stat", "nombre de persos", "tous", guild_name, highlight_value=player_value)

    return 0, err_txt, image

###############################
async def print_lox(txt_allyCode, characters, compute_guild=False, all_omicrons=False):
    war_txt = ""

    dict_unitsList = godata.get("unitsList_dict.json")
    dict_capas = godata.get("unit_capa_list.json")
    all_modes = []
    for unit_id in dict_capas:
        unit = dict_capas[unit_id]
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
            #print(unit)
            if unit.startswith("mode:"):
                unit_tab = unit.split(":")
                while '' in unit_tab:
                    unit_tab.remove('')

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
            unit = dict_capas[unit_id]
            has_omicron = False
            for ability_id in unit:
                ability = unit[ability_id]
                if ability["omicronTier"] < 99:
                    has_omicron = True
                    break
            if not has_omicron:
                war_txt += "WAR: pas d'omicron connu pour "+dict_unitsList[unit_id]["name"] + "\n"

        if len(list_character_ids)==0 and len(list_modes)==0:
            return 1, "ERR: aucun personnage ni aucun mode omicron défini", None

    list_omicrons = []
    for unit_id in dict_capas:
        for skill in dict_capas[unit_id]:
            if '_' in skill:
                continue
            if dict_capas[unit_id][skill]['omicronTier']==99:
                continue
            list_omicrons.append((unit_id, skill, dict_capas[unit_id][skill]['omicronTier'], dict_capas[unit_id][skill]['omicronMode']))

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

    query = "SELECT players.name AS 'joueur', roster.defId AS 'perso', roster_skills.name AS 'type', \n"
    query+= "CASE WHEN gear=13 THEN CONCAT(rarity, '*R', relic_currentTier-2) \n"
    query+= "ELSE CONCAT(rarity, '*G', gear) END AS 'gear', \n"
    query+= "omicrons.type AS 'mode' \n"
    if all_omicrons:
        query+= ", CASE WHEN roster_skills.level>=omicrons.level THEN 'x' ELSE '' END AS 'actif' \n"
    query+= "FROM roster \n"
    query+= "JOIN roster_skills ON roster_id = roster.id \n"
    query+= "JOIN players ON players.allyCode=roster.allyCode \n"
    query+= "JOIN ( VALUES ('defId', 'name', 'level', 'type'),\n"
    query+= str(list_omicrons)[1:-1]
    query+= ") as omicrons ON (roster.defId=omicrons.defId AND roster_skills.name=omicrons.name) \n"

    query+= "WHERE TRUE \n"
    if not get_all:
        query+= "AND ( \n"
        if len(list_character_ids)>0:
            query+= "    roster.defId IN "+str(tuple(list_character_ids)).replace(",)", ")")+" \n"
        else:
            query+= "    0 \n"
        query+= "    OR\n"
        if len(list_modes)>0:
            query+= "    omicrons.type IN "+str(tuple(list_modes)).replace(",)", ")")+" \n"
        else:
            query+= "    0 \n"
        query+= ") \n"
    if compute_guild:
        query+= "AND guildName=(SELECT guildName FROM players WHERE allyCode="+txt_allyCode+") \n"
    else:
        query+= "AND players.allyCode="+txt_allyCode+" \n"
    if not all_omicrons:
        query+= "AND roster_skills.level>=omicrons.level \n"
    query+= "ORDER BY omicrons.type, roster.defId, omicrons.name, players.name"
    goutils.log2("DBG", query)

    db_lines = connect_mysql.text_query(query)
    return 0, war_txt, db_lines

###############################
async def print_erx(txt_allyCode, days, compute_guild):
    dict_unitsList = godata.get("unitsList_dict.json")
    dict_categoryList = godata.get("categoryList_dict.json")
    dict_categories = connect_gsheets.load_config_categories(False)

    #Update player/guild data
    if not compute_guild:
        #only one player
        #Load or update data for the player
        e, t, d = await load_player(txt_allyCode, 1, False)
        if e != 0:
            #error wile loading guild data
            goutils.log2('ERR', 'erreur lors de la récupération des données joueur pour le code allié ' + txt_allyCode)
            
    else:
        #Get data for the guild and associated players
        err_code, err_txt, guild = await load_guild(txt_allyCode, True, True)
        if err_code != 0:
            goutils.log2('ERR', 'erreur lors de la récupération des données guilde pour le code allié ' + txt_allyCode)

    #get latest Journey Guide definition
    ec, list_teams, dict_teams = connect_gsheets.load_config_teams(BOT_GFILE, False)
    if ec == 2:
        return 1, "ERR: pas de fichier de config pour ce serveur"
    elif ec == 3:
        return 1, "ERR: pas d'onglet 'teams' dans le fichier de config"
    elif ec != 0:
        return 1, "ERR: erreur en lisant le fichier de config"

    #Get all roster evolutions in the given period, but not the datacrons
    if not compute_guild:
        query = "SELECT guildName, name, defId, timestamp FROM roster_evolutions " \
              + "JOIN players ON players.allyCode = roster_evolutions.allyCode " \
              + "WHERE players.allyCode = " + txt_allyCode + " " \
              + "AND NOT isnull(defId) " \
              + "AND timestampdiff(DAY, timestamp, CURRENT_TIMESTAMP)<=" + str(days) + " " \
              + "ORDER BY timestamp DESC"
    else:
        query = "SELECT guildName, name, defId, timestamp FROM roster_evolutions " \
              + "JOIN players ON players.allyCode = roster_evolutions.allyCode " \
              + "WHERE players.allyCode IN (SELECT allyCode FROM players WHERE guildName = (SELECT guildName FROM players WHERE allyCode="+txt_allyCode+")) "\
              + "AND NOT isnull(defId) " \
              + "AND timestampdiff(DAY, timestamp, CURRENT_TIMESTAMP)<=" + str(days) + " " \
              + "ORDER BY timestamp DESC"

    goutils.log2("DBG", query)
    db_data_evo = connect_mysql.get_table(query)

    #Get all unlocked ships by player
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

                #Game catagories
                for category in unit_categories:
                    if category in dict_categoryList:
                        category_name = dict_categoryList[category]["descKey"]
                        if category in stats_categories:
                            stats_categories[category][1] += 1
                        else:
                            stats_categories[category] = [category_name, 1]

                #Custom categories
                for category_name in dict_categories:
                    if unit_id in dict_categories[category_name]:
                        if category_name in stats_categories:
                            stats_categories[category_name][1] += 1
                        else:
                            stats_categories[category_name] = [category_name, 1]

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
        faction_items = [x for x in stats_categories.items() if x[0][:5] in ["affil", "profe", "raid_"]]
        list_evo_categories = sorted(faction_items, key=lambda x:-x[1][1])
        for evo in list_evo_categories[:10]:
            ret_cmd += evo[1][0] + ": " + str(evo[1][1])+'\n'

        ret_cmd += "\n__TOP 10 GUIDE DE VOYAGE__\n"
        list_gv_units = sorted(stats_gv.items(), key=lambda x:-x[1][1])
        for gv in list_gv_units[:10]:
            ret_cmd += gv[1][0] + ": " + str(gv[1][1])+'\n'

        return 0, ret_cmd

    else:
        goutils.log2("WAR", "error while running db_data_evo query, returned NULL")
        return 1, "Aucune évolution détectée dans les "+str(days)+" derniers jours"

############################################
# get_tw_alerts
# IN - guild_id
# OUT - list_tw_alerts [{territory1: alert_territory1,
#                        territory2: alert_territory2...},
#                       tw_timestamp]]
# Err Code: 0 = OK / 1 = config error / 2 = no TW ongoing
############################################
async def get_tw_alerts(guild_id,
                        tw_id,
                        list_opponent_squads,
                        list_opp_territories,
                        list_def_squads,
                        list_def_territories):

    dict_unitsList = godata.get("unitsList_dict.json")

    tw_timestamp = tw_id.split(":")[1][1:]

    list_tw_alerts = [{}, tw_timestamp]

    ########################################
    # OPPONENT territories
    ########################################
    if len(list_opponent_squads) > 0:
        list_opponent_players = [x["player_name"] for x in list_opponent_squads]
        longest_opp_player_name = max(list_opponent_players, key=len)
        longest_opp_player_name = longest_opp_player_name.replace("'", "''")
        list_open_tw_territories = set([x["zone_short_name"] for x in list_opponent_squads])

        for territory_name in list_open_tw_territories:
            territory = [x for x in list_opp_territories if x[0]==territory_name][0]
            orders = territory[5]
            state = territory[6]

            list_opp_squads_terr = [x for x in list_opponent_squads if (x["zone_short_name"]==territory_name and len(x["list_defId"])>0)]
            list_opp_remaining_squads_terr = [x for x in list_opponent_squads if (x["zone_short_name"]==territory_name and len(x["list_defId"])>0 and not x["is_beaten"])]
            counter_leaders = Counter([x["list_defId"][0]["unitId"] for x in list_opp_squads_terr])
            counter_remaining_leaders = Counter([x["list_defId"][0]["unitId"] for x in list_opp_remaining_squads_terr])

            n_territory = int(territory_name[1])
            if territory_name[0] == "T" and int(territory_name[1]) > 2:
                n_territory -= 2

            #Display position of territory_name
            if n_territory == 1:
                msg = "__Le 1er territoire "
            else:
                msg = "__Le "+str(n_territory)+"e territoire "

            #Display short name of territory then char/ship
            if territory_name[0] == "T" and int(territory_name[1]) < 3:
                msg += "du haut__"
            elif territory_name[0] == "T":
                msg += "du milieu__"
            elif territory_name[0] == "F":
                msg += "des vaisseaux__"
            else:
                msg += "du bas__"

            if orders == None:
                txt_orders = ""
            else:
                txt_orders = " - " + orders

            msg += " ("+territory_name+") est ouvert"+txt_orders+"."

            #Display the leaders
            intro_leaders_done = False
            territory_done = True
            for leader in counter_leaders:
                if leader in dict_unitsList:
                    leader_name = dict_unitsList[leader]["name"]
                else:
                    leader_name = leader
                msgleader = leader_name+": "+str(counter_remaining_leaders[leader])+"/"+str(counter_leaders[leader])
                if counter_remaining_leaders[leader] == 0:
                    # remove the display completely, to have simpler reading
                    pass
                    #msg += "\n- ~~"+msgleader+"~~"
                else:
                    if not intro_leaders_done:
                        msg += "\nAvec ces adversaires :"
                        intro_leaders_done = True
                    msg += "\n- "+msgleader
                    territory_done = False

            #Display an emoji depending on done or in progress
            if territory_done:
                msg = '\N{WHITE HEAVY CHECK MARK}'+msg.replace("ouvert", "terminé")
            elif state=="IGNORED":
                msg = '\N{PROHIBITED SIGN}'+msg
            else:
                msg = '\N{WHITE RIGHT POINTING BACKHAND INDEX}'+msg

            list_tw_alerts[0][territory_name] = msg

    ########################################
    # HOME territories
    ########################################
    list_full_territories = [t for t in list_def_territories if t[1]==t[2]]
    nb_full = len(list_full_territories)
    if len(list_def_territories) > 0:
        #Alert for defense fully set OR new orders
        msg = ""
        msg_light = ""
        for territory in list_def_territories:
            territory_name = territory[0]
            size = territory[1]
            filled = territory[2]
            orders = territory[5]
            state = territory[6]

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

            if orders == None:
                txt_orders = ""
            else:
                txt_orders = " - " + orders

            terr_msg=""
            if filled == size:
                terr_msg += emojis.check
            elif state=="IGNORED":
                terr_msg += emojis.prohibited
            else:
                terr_msg += '\U000027A1\U0000FE0F' #right pointing arrow on blue background

            terr_msg += "**DEFENSE** - "+territory_fullname+" ("+territory_name+txt_orders+") "+str(filled)+"/"+str(size)+"\n"

            #detect leaders
            list_def_squads_terr = [x for x in list_def_squads if (x["zone_short_name"]==territory_name and len(x["list_defId"])>0)]
            counter_leaders = Counter([x["list_defId"][0]["unitId"] for x in list_def_squads_terr])
            #sort by values
            counter_leaders = dict(sorted(dict(counter_leaders).items(), key=lambda x:-x[1]))
            
            #Display the leaders
            leader_count=0
            msg_leaders=""
            msg_leaders_light=""
            for leader in counter_leaders:
                if leader in dict_unitsList:
                    leader_name = dict_unitsList[leader]["name"]
                else:
                    leader_name = leader
                msgleader = leader_name+": "+str(counter_leaders[leader])
                msg_leaders += "- "+msgleader+"\n"
                if leader_count<3:
                    msg_leaders_light += "- "+msgleader+"\n"
                elif leader_count==3:
                    msg_leaders_light += "- ...\n"
                else:
                    pass
                leader_count+=1
            msg+=terr_msg+msg_leaders
            msg_light+=terr_msg+msg_leaders_light

        if len(msg) > 1900:
            msg=msg_light

        #Global Defense filling message
        if nb_full==10:
            msg += '\N{WHITE HEAVY CHECK MARK} défense complète'
        else:
            msg += "Progrès de la défense : "+str(nb_full)+"/10"
        list_tw_alerts[0]["Placement:G"] = msg


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

            list_tw_alerts[0]["Home:"+territory_name] = msg

    ret_data = {"tw_id": tw_id, "alerts": list_tw_alerts}

    return 0, "", ret_data

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

################################################################
# tag_players_with_character
# IN: txt_allyCode (to identify the guild)
# IN: list_list_character ([["SEE"], ["Mara", "+SK"], ["SEE:7:G8"], ["SEE:R5"]])
#     possible tags
#     - "o" -> omicron (if only one)
#     - "oL" -> lead omicron (or B, S, U, S1, S2, U1, U2)
#     - "z" -> zeta (if only one)
#     - "zL" -> lead zeta (or B, S, U, S1, S2, U1, U2)
#     - "g12" -> gear 12 or above
#     - "R4" -> relic 4 or above
#     - "dtc" -> the player has the datacron with the selftag of this character
# IN: guild_id
# IN: tw_mode (True if the bot shall count defense-used toons as not avail)
# IN: tb_mode (True if the bot shall count platoon-used toons as not avail)
# OUT: err_code, err_txt, list_discord_ids
################################################################
async def tag_players_with_character(txt_allyCode, list_list_characters, guild_id=None,
                                     tw_mode=False, tb_mode=False, with_mentions=False, 
                                     exclude_attacked_leaders=[],
                                     connected_allyCode=None):
    dict_unitsList = godata.get("unitsList_dict.json")
    dict_capas = godata.get("unit_capa_list.json")

    err_code, err_txt, dict_guild = await load_guild(txt_allyCode, True, True)
    if err_code != 0:
        return 1, 'ERR: guilde non trouvée pour code allié ' + txt_allyCode, None

    if tw_mode:
        ec, et, ret_dict = await connect_rpc.get_tw_active_players(guild_id, 0, allyCode=connected_allyCode)
        if ec != 0:
            return ec, et, None
        list_active_players = ret_dict["active"]
        dict_guild = ret_dict["rpc"]["guild"]

    if with_mentions:
        #get list of allyCodes and player tags
        dict_players = connect_mysql.load_config_players()[0]
    else:
        # if this dict is empty, there will be no discord mention
        dict_players = {}


    #Manage -TW or -TB option
    dict_used_toon_player = {} # key=toon, value = [playerName1, playerName2...]
    if tw_mode:
        with_attacks = (len(exclude_attacked_leaders)>0)
        ec, et, ret_data = await get_tw_def_attack(guild_id, 0, with_attacks=with_attacks,
                                                   allyCode=connected_allyCode,
                                                   dict_guild=dict_guild)
        if ec != 0:
            return ec, et, None
        dict_used_toon_player = ret_data["homeDef"]
        dict_attack_toon_player = ret_data["awayAttack"]
    elif tb_mode:
        dict_alias = godata.get("unitsAlias_dict.json")

        err_code, err_txt, ret_data = await connect_rpc.get_actual_tb_platoons(
                                                        guild_id, 0, 
                                                        allyCode=connected_allyCode)
        if err_code != 0:
            return 1, err_txt, None

        tbs_round = ret_data["round"]
        dict_platoons_done = ret_data["platoons"]
        list_open_terr = ret_data["open_territories"]

        tb_name = tbs_round[:-1]
        if tb_name == "ROTE":
            terr_pos = ["LS", "DS", "MS"]
        else:
            terr_pos = ["top", "mid", "bot"]
        list_open_terr_names = ['', '', '']
        list_open_terr_names[0] = list_open_terr[0]["zone_name"]
        list_open_terr_names[1] = list_open_terr[1]["zone_name"]
        list_open_terr_names[2] = list_open_terr[2]["zone_name"]

        for terr in dict_platoons_done:
            #LIMIT: if a terr is filled over several days, a player may have put
            # the toon the day before. So it is available for today, yet
            # the algorithm will detect it as not available
            if terr[:-2] in list_open_terr_names:
                for unit_name in dict_platoons_done[terr]:
                    unit_id = dict_alias[unit_name.lower()][1]
                    if not unit_id in dict_used_toon_player:
                        dict_used_toon_player[unit_id] = []
                    dict_used_toon_player[unit_id] += dict_platoons_done[terr][unit_name]

    #get exclude attacked toon IDs
    if len(exclude_attacked_leaders)>0:
        exclude_attacked_leader_ids, dict_id_name, txt = goutils.get_characters_from_alias(exclude_attacked_leaders)
        if txt != '':
            return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt, None
    else:
        exclude_attacked_leader_ids = []

    list_list_discord_ids=[]
    for list_characters in list_list_characters:
        opposite_search = (list_characters[0][0]=="-")
        if opposite_search and tw_mode:
            return 1, "ERR: impossible de chercher un perso non présent (avec le '-' avant le premier/seul perso) avec l'option -TW", None

        #prepare basic query
        query = "SELECT guildName, name, playerId FROM players " \
              + "WHERE guildName=(" \
              + "SELECT guildName from players WHERE allyCode="+txt_allyCode+") "
        intro_txt = "Ceux"

        list_req_chars = [] #to store the char_id of the required chars in the command
        for character in list_characters:
            tab_virtual_character = character.split(':')
            while '' in tab_virtual_character:
                tab_virtual_character.remove('')

            char_rarity = None
            char_gear = None
            char_relic = None
            char_zetas = []
            char_omicrons = []
            char_ulti = False
            dtc_selftag = None
            simple_search = True

            if character[0]=="-":
                opposite_search = True
                char_alias = tab_virtual_character[0][1:]
            else:
                char_alias = tab_virtual_character[0]

            #Get character_id
            list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([char_alias])
            if txt != '':
                return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt, None
            character_id = list_character_ids[0]

            # Read character options
            for character_option in tab_virtual_character[1:]:
                simple_search = False
                if    (len(character_option)==1 and character_option in "1234567") \
                   or (len(character_option)==2 and character_option[1] == "*" and character_option[0] in "1234567"):
                    char_rarity = int(character_option[0])

                elif character_option[0] in "gG":
                    if character_option[1:].isnumeric():
                        char_gear = int(character_option[1:])
                        char_relic = None
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

                elif character_option[0] in "oO":
                    capa_shortname = character_option[1:]
                    capa_id = goutils.get_capa_id_from_short(character_id, capa_shortname)
                    if capa_id == None:
                        return 1, "ERR: la syntaxe "+character+" est incorrecte pour l'omicron \""+character_option+"\"", None
                    character_omicrons = [x for x in dict_capas[character_id] if dict_capas[character_id][x]["omicronTier"]<99 and not "_" in x]
                    selected_omicrons = [x for x in character_omicrons if x.startswith(capa_id)]
                    if len(selected_omicrons) == 0:
                        return 1, "ERR: l'omicron \""+character_option+"\" n'existe pas pour "+character_id, None
                    elif len(selected_omicrons) > 1:
                        return 1, "ERR: l'omicron \""+character_option+"\" est ambigu pour "+character_id+" "+str(selected_omicrons), None
                    capa_id = selected_omicrons[0]

                    char_omicrons.append({"id":capa_id, "tier":dict_capas[character_id][capa_id]["omicronTier"]})

                elif character_option[0] in "zZ":
                    capa_shortname = character_option[1:]
                    capa_id = goutils.get_capa_id_from_short(character_id, capa_shortname)
                    if capa_id == None:
                        return 1, "ERR: la syntaxe "+character+" est incorrecte pour la zeta \""+character_option+"\"", None
                    character_zetas = [x for x in dict_capas[character_id] if dict_capas[character_id][x]["zetaTier"]<99 and not "_" in x]
                    selected_zetas = [x for x in character_zetas if x.startswith(capa_id)]
                    if len(selected_zetas) == 0:
                        return 1, "ERR: la zeta \""+character_option+"\" n'existe pas pour "+character_id, None
                    elif len(selected_zetas) > 1:
                        return 1, "ERR: la zeta \""+character_option+"\" est ambigue pour "+character_id+" "+str(selected_zetas), None
                    capa_id = selected_zetas[0]

                    char_zetas.append({"id":capa_id, "tier":dict_capas[character_id][capa_id]["zetaTier"]})

                elif character_option.lower() == 'ulti':
                    if not "GL" in dict_capas[character_id]:
                        return 1, "ERR: la syntaxe "+character+" est incorrecte, pas d'ulti pour ce perso", None
                    char_ulti = True

                elif character_option.lower() == 'dtc':
                    for c in dict_unitsList[character_id]["categoryId"]:
                        if c.startswith("selftag_"):
                            dtc_selftag = c
                else:
                    return 1, "ERR: la syntaxe "+character+" est incorrecte pour l'option \""+character_option+"\"", None
            character_name = "**"+dict_unitsList[character_id]["name"]+"**"

            if opposite_search and simple_search:
                intro_txt+= " qui n'ont pas "+character_name
                query+= "AND NOT allyCode IN ( "
            else:
                if opposite_search:
                    intro_txt+= " qui ont ("+character_name+ " mais pas "+character_name
                else:
                    intro_txt+= " qui ont "+character_name
                    list_req_chars.append(character_id)


                if not simple_search:
                    if char_rarity != None:
                        intro_txt += ":"+str(char_rarity)+"*"
                    if char_relic != None:
                        intro_txt += ":R"+str(char_relic)
                    elif char_gear != None:
                        intro_txt += ":G"+str(char_gear)
                    for z in char_zetas:
                        intro_txt += ":zeta("+z["id"]+")"
                    for o in char_omicrons:
                        intro_txt += ":omicron("+o["id"]+")"
                    if char_ulti:
                        intro_txt += ":ulti"
                    if dtc_selftag != None:
                        intro_txt += ":DTC"

                if opposite_search:
                    intro_txt += ")"

                query+= "AND allyCode IN ( "

            query+= "   SELECT players.allyCode "
            query+= "   FROM players "
            query+= "   JOIN roster ON roster.allyCode = players.allyCode "

            # Add skills use for filters
            list_skills = set([x["id"] for x in (char_zetas+char_omicrons)])
            for skill_name in list_skills:
                query+= "   LEFT JOIN roster_skills AS rs"+skill_name+" ON (rs"+skill_name+".roster_id = roster.id AND rs"+skill_name+".name='"+skill_name+"')"

            if char_ulti:
                query+= "   LEFT JOIN roster_skills AS rsULTI ON (rsULTI.roster_id = roster.id AND rsULTI.name='ULTI')"

            if dtc_selftag != None:
                query+= "   LEFT JOIN datacrons ON (datacrons.allyCode = roster.allyCode AND ("
                query+= "      datacrons.level_9 like '%:"+dtc_selftag+"' "
                query+= "      OR datacrons.level_12 like '%:"+dtc_selftag+"' "
                query+= "      OR datacrons.level_15 like '%:"+dtc_selftag+"'))"

            query+= "   WHERE guildName=(" 
            query+= "      SELECT guildName from players WHERE allyCode="+txt_allyCode+") " 
            query+= "      AND defId = '"+character_id+"' "

            if opposite_search:
                if not simple_search:
                    query +="      AND (FALSE " # this "FALSE" is here to allow having a "OR" at each next option

                    if char_rarity!=None:
                        query +="      OR rarity < "+str(char_rarity)+" "

                    if char_gear!=None:
                        query+= "      OR gear < "+str(char_gear)+" "
                    if char_relic!=None:
                        query+= "      OR relic_currentTier < "+str(char_relic+2)+" "

                    for z in char_zetas:
                        query += "      OR rs"+skill_name+".level<"+str(z["tier"])+" "
                    for o in char_omicrons:
                        query += "      OR rs"+skill_name+".level<"+str(o["tier"])+" "

                    if char_ulti:
                        query += "      OR isnull(rsULTI.level) "

                    if dtc_selftag != None:
                        query+= "      OR (NOT datacrons.level_9 LIKE '%:"+dtc_selftag+"' "
                        query+= "      AND NOT datacrons.level_12 LIKE '%:"+dtc_selftag+"' "
                        query+= "      AND NOT datacrons.level_15 LIKE '%:"+dtc_selftag+"')"

                    query+= "      ) "

            else:
                if char_rarity!=None:
                    query+= "      AND rarity >= "+str(char_rarity)+" "
                if char_gear!=None:
                    query+= "      AND gear >= "+str(char_gear)+" "
                if char_relic!=None:
                    query+= "      AND relic_currentTier >= "+str(char_relic+2)+" "

                for z in char_zetas:
                    query += "      AND rs"+skill_name+".level>="+str(z["tier"])+" "
                for o in char_omicrons:
                    query += "      AND rs"+skill_name+".level>="+str(o["tier"])+" "

                if char_ulti:
                    query += "      AND rsULTI.level=1 "

                if dtc_selftag != None:
                    query += "      AND (datacrons.level_9 like '%:"+dtc_selftag+"' "
                    query += "      OR datacrons.level_12 like '%:"+dtc_selftag+"' "
                    query += "      OR datacrons.level_15 like '%:"+dtc_selftag+"')"
            query += ") "
            intro_txt += " et"

        intro_txt = intro_txt[:-3]
        if tw_mode:
            intro_txt += ", qui sont inscrits à la GT, et qui ne l'ont pas mis en défense"
            query += "AND players.name IN "+str(tuple(list_active_players)).replace(",)", ")")+"\n"
        if tb_mode:
            intro_txt += ", et qui ne l'ont pas posé en peloton"
        query += "GROUP BY guildName, players.name "
        goutils.log2('DBG', query)
        allyCodes_in_DB = connect_mysql.get_table(query)
        if allyCodes_in_DB == None:
            allyCodes_in_DB = []
            guildName = ""
        else:
            guildName = allyCodes_in_DB[0][0]

        for leader_id in exclude_attacked_leader_ids:
            leader_name = "**"+dict_unitsList[leader_id]["name"]+"**"
            intro_txt += ", et qui n'ont pas attaqué "+leader_name

        #Build the list of tags
        list_discord_ids = [intro_txt]
        for [guildName, player_name, player_id] in allyCodes_in_DB:
            if player_name == "":
                continue

            goutils.log2('DBG', 'player_name: '+player_name)

            # Look for required chars in used toons
            req_chars_available = True
            for req_char in list_req_chars:
                if req_char in dict_used_toon_player and \
                    player_name in dict_used_toon_player[req_char]:
                    req_chars_available = False

            # Look of player has attacked an exluded leader
            for leader_id in exclude_attacked_leader_ids:
                if leader_id in dict_attack_toon_player:
                    if player_name in dict_attack_toon_player[leader_id]:
                        req_chars_available = False

            if not req_chars_available:
                goutils.log2('DBG', "toon used in TW defense or TB platoon, no tag")
            else:
                if player_name in dict_players:
                    player_mention = dict_players[player_name][1]
                else:
                    player_mention = player_name

                list_discord_ids.append(player_mention)
        list_list_discord_ids.append(list_discord_ids)

    return 0, "", list_list_discord_ids

################################################################
# count_players_with_character
# IN: txt_allyCode (to identify the guild)
# IN: list_characters alias
# IN: guild_id (required to get home guild data when allyCode is in the TW opponent guild)
# IN: tw_mode - "homeGuild" if the bot shall manage registered players and get defense toons for "us"
#               "awayGuild" if the bot shall get seen defense for TW opponent
#               None otherwise
# OUT: err_code, err_txt, {'unit name': [total, in TW defense], ...}
################################################################
async def count_players_with_character(txt_allyCode, list_characters, guild_id, tw_mode,
                                       connected_allyCode=None):
    err_code, err_txt, dict_guild = await load_guild(txt_allyCode, True, True)
    if err_code != 0:
        return 1, 'ERR: guilde non trouvée pour code allié ' + txt_allyCode, None

    if guild_id == None:
        guild_id = dict_guild["profile"]["id"]

    if tw_mode == "homeGuild":
        # For "us", we can detect players who registered to the TW
        ec, et, ret_dict = await connect_rpc.get_tw_active_players(guild_id, 0, allyCode=connected_allyCode)
        if ec != 0:
            return ec, et, None
        list_active_players = ret_dict["active"]

    #get units from alias
    list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_characters)
    if txt != '':
        return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt, None

    #prepare basic query
    query = "SELECT defId, " \
          + "CASE WHEN gear<10 THEN CONCAT(rarity, '*G0', gear) " \
          + "WHEN gear<13 THEN CONCAT(rarity, '*G', gear) " \
          + "ELSE CONCAT(rarity, '*R', relic_currentTier-2) END, " \
          + "count(*) FROM players " \
          + "JOIN roster ON roster.allyCode = players.allyCode " \
          + "WHERE guildName=(" \
          + "SELECT guildName from players WHERE allyCode="+txt_allyCode+") " \
          + "AND defId in "+str(tuple(list_character_ids)).replace(",)", ")")+" " 

    if tw_mode == "homeGuild":
        list_players_patch = [x.replace("'", "''") for x in list_active_players]
        list_players_txt = str(list_players_patch)
        list_players_txt = list_players_txt.replace("[", "(")
        list_players_txt = list_players_txt.replace("]", ")")
        list_players_txt = list_players_txt.replace('"', "'")
        query += "AND players.name IN "+list_players_txt+" "

    query +="GROUP BY defId, rarity, gear, relic_currentTier " \
          + "ORDER BY defId, rarity, gear, relic_currentTier"
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_table(query)
    if db_data==None:
        db_data=[]

    output_dict = {}
    for line in db_data:
        unit_id = line[0]
        unit_gear = line[1]

        if not unit_id in output_dict:
            output_dict[unit_id] = {}
        output_dict[unit_id][unit_gear] = [line[2], 0]

    #print(output_dict)
    #Manage -TW option
    if tw_mode != None:
        ec, et, ret_data = await get_tw_def_attack(guild_id, -1, allyCode=connected_allyCode)
        if ec != 0:
            return ec, et, None
        if tw_mode == "homeGuild":
            dict_def_toon_player = ret_data["homeDef"]
        else: # awayGuild
            dict_def_toon_player = ret_data["awayDef"]

        for unit_id in output_dict:
            if unit_id in dict_def_toon_player:
                for player in dict_def_toon_player[unit_id]:
                    unit = dict_def_toon_player[unit_id][player]
                    unit_stars = unit["unitDefId"].split(':')[1]
                    unit_gear = str(godata.dict_rarity[unit_stars]) + "*"
                    if unit["gear"] < 10:
                        unit_gear += 'G0'+str(unit["gear"])
                    elif unit["gear"] < 13:
                        unit_gear += 'G'+str(unit["gear"])
                    else:
                        unit_gear += 'R'+str(unit["relic"]-2)
                    if unit_gear in output_dict[unit_id]:
                        output_dict[unit_id][unit_gear][1] += 1

    return 0, "", output_dict

#######################################################
# get_gv_graph
# IN txt_allyCode: identifier of the player
# IN farm_list: list of GV characters OR farm teams
# OUT: image of the graph
#######################################################
def get_gv_graph(txt_allyCodes, farm_list):
    sql_allyCodes = str(tuple(txt_allyCodes)).replace(',)', ')')

    # get list of farm history
    query = "SELECT defId FROM gv_history " \
          + "WHERE gv_history.allyCode IN "+sql_allyCodes+" " \
          + "GROUP BY defId"
    goutils.log2("DBG", query)
    ret_db = connect_mysql.get_column(query)
    if ret_db == None:
        return 1, "WAR: aucun progrès enregistré pour "+sql_allyCodes, None
    player_farm_list = ret_db

    if "FARM" in farm_list:
        character_ids_txt = "farm perso"
    elif "all" in farm_list:
        character_ids_txt = "tous les farms"
    else:
        team_ids = []
        remaining_farm_list = list(farm_list)

        # first look for team names, exactly
        for farm in farm_list:
            if farm in player_farm_list:
                remaining_farm_list.remove(farm)
                team_ids.append(farm)

        # then look for GV characters
        if len(remaining_farm_list) > 0:
            list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(remaining_farm_list)
            if txt != '':
                return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt, None
            team_ids += list_character_ids

        character_ids_txt = str(tuple(team_ids)).replace(',)', ')')

    query = "SELECT date, defId, progress, source, name FROM gv_history " \
          + "JOIN players ON players.allyCode = gv_history.allyCode " \
          + "WHERE gv_history.allyCode IN "+sql_allyCodes+" " \
          + "AND progress<=100 " # to filter out entries from RAF command
    if "FARM" in farm_list:
          query += "AND defId='FARM' "
    elif not "all" in farm_list:
          query += "AND defId IN "+character_ids_txt+" "
    query +="ORDER BY date DESC LIMIT 30"
    goutils.log2("DBG", query)
    ret_db = connect_mysql.get_table(query)
    if ret_db == None:
        return 1, "WAR: aucun progrès connu de "+character_ids_txt+" pour "+sql_allyCodes, None

    min_date = None
    max_date = None
    dict_dates={}
    dict_values={}

    if len(txt_allyCodes)==1 and len(farm_list)==1 and farm_list[0]!="all":
        #Only one player, only one unit
        #display the one character progress, use all bots
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

        graph_title = "Progrès de "+character_ids_txt

    elif len(txt_allyCodes)>1 and len(farm_list)==1 and farm_list[0]!="all":
        #more than one player, one character, use only go.bot
        for line in ret_db:
            if line[3] == "go.bot":
                if min_date==None or line[0]<min_date:
                    min_date = line[0]
                if max_date==None or line[0]>max_date:
                    max_date = line[0]

                if not line[4] in dict_dates:
                    dict_dates[line[4]] = []
                    dict_values[line[4]] = []
                dict_dates[line[4]].append(line[0])
                dict_values[line[4]].append(line[2])

        graph_title = "Progrès de "+character_ids_txt

    elif len(txt_allyCodes)==1 and (len(farm_list)>1 or farm_list[0]=="all"):
        #one player, more than one character, use only go.bot
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

        graph_title = "Progrès pour "+line[4]

    else:
        #probably more than one player and more than one character
        # Cannot display
        return 1, "WAR: impossible d'afficher un graph pour plusieurs joueurs et plusieurs persos", None

    #create plot
    fig, ax = plt.subplots()
    #set colormap
    # Have a look at the colormaps here and decide which one you'd like:
    # http://matplotlib.org/1.2.1/examples/pylab_examples/show_colormaps.html
    colormap = plt.cm.gist_ncar
    color_source = np.linspace(0, 1, len(dict_dates))
    color_repeat = np.repeat(color_source, 2) #1 for known values, 1 for extrapolation
    color_list = plt.cm.jet(color_repeat)
    plt.gca().set_prop_cycle(plt.cycler('color', color_list))

    #add series
    for key in dict_dates:
        if key == 'j.bot':
            marker = 'x'
        elif key == 'wookiebot':
            marker = 'o'
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
        else:
            #in case no extrapolation is possible, we still need to draw a line to ensure 
            # color alternance
            # So... just redraw the same, without the label to prevent double in legend
            ax.plot(dict_dates[key], dict_values[key], marker=marker)


    #format dates on X axis
    date_format = mdates.DateFormatter("%d-%m")
    ax.xaxis.set_major_formatter(date_format)
    fig.suptitle(graph_title)

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
# list_allyCodes >> list of allyCode of the players, or list of one player for a guild
# guild_graph (boolean) >> True if the graph is for the guild
# parameter >> ["gp", "arena_char_rank", "arena_ship_rank", "gac_rating", "modq", "statq"]
# is_year = True >> graph one 12 months, instead of 30 days (default)
###############################
async def get_player_time_graph(list_allyCodes, guild_graph, parameter, is_year):
    dict_params = {"gp": ["ship_gp+char_gp", "sum"],
                   "pg": ["ship_gp+char_gp", "sum"],
                   "arena_char_rank": ["arena_char_rank", "avg"],
                   "arena_ship_rank": ["arena_ship_rank", "avg"],
                   "gac_rating": ["grand_arena_rating", "avg"],
                   "modq": ["modq", "avg"],
                   "statq": ["statq", "avg"]}

    if type(list_allyCodes) != list:
        list_allyCodes = [list_allyCodes]

    if guild_graph and len(list_allyCodes)>1:
        return 1, "ERR: un seul joueur possible pour un graph de guilde", None

    if not parameter in dict_params:
        return 1, "ERR: le paramètre "+parameter+" est inconnu dans la liste "+str(list(dict_params.keys())), None

    for txt_allyCode in list_allyCodes:
        # refresh player info from game
        e, t, d = await load_player(txt_allyCode, 1, False)
        if e != 0:
            return 1, "ERR: erreur de mise à jour des données pour "+txt_allyCode, None

    #get basic player info
    db_txt_allyCodes = str(tuple(list_allyCodes)).replace(",)", ")")
    query = "SELECT allyCode, name, guildName FROM players WHERE allyCode IN "+db_txt_allyCodes
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_table(query)
    if db_data == None or len(db_data)<len(list_allyCodes):
        return 1, "ERR: informations manquantes pour les codes "+db_txt_allyCodes, None

    dict_players = {}
    for line in db_data:
        ac = str(line[0])
        playerName = line[1]
        guildName = line[2]
        dict_players[ac] = [playerName, guildName]

    if guild_graph:
        txt_allyCode = list_allyCodes[0]
        playerName = dict_players[txt_allyCode][0]
        guildName = dict_players[txt_allyCode][1]

        if guildName == None or guildName == '':
            return 1, "ERR: aucune guilde connue pour le joueur "+txt_allyCode, None

        txt_param = dict_params[parameter][1]+"("+dict_params[parameter][0]+")"
        query = "SELECT date, "+txt_param+" AS pp, allyCode FROM gp_history " \
              + "WHERE guildName=(SELECT guildName FROM players WHERE allyCode = "+txt_allyCode+") " \
              + "GROUP BY date "
    else:
        txt_param = dict_params[parameter][0]
        query = "SELECT date, "+txt_param+" AS pp, allyCode FROM gp_history " \
              + "WHERE allyCode IN "+db_txt_allyCodes+" "

    if is_year:
        query = "SELECT max(date), pp, allyCode FROM ( " \
              + query \
              + ") T GROUP BY yearweek(date), allyCode ORDER BY DATE DESC LIMIT 52"
    else:
        query = query + "ORDER BY DATE DESC LIMIT 30"

    goutils.log2("DBG", query)
    db_data = connect_mysql.get_table(query)
    if db_data == None:
        return 1, "ERR: aucun "+parameter+" connu pour "+db_txt_allyCodes, None

    #Create plot
    fig, ax = plt.subplots()
    #set colormap
    # Have a look at the colormaps here and decide which one you'd like:
    # http://matplotlib.org/1.2.1/examples/pylab_examples/show_colormaps.html
    colormap = plt.cm.gist_ncar
    color_source = np.linspace(0, 1, len(list_allyCodes))
    color_list = plt.cm.jet(color_source)
    plt.gca().set_prop_cycle(plt.cycler('color', color_list))

    min_date = None
    max_date = None

    #Create series
    print(list_allyCodes)
    for ac in list_allyCodes:
        d_kpi = []
        v_kpi = []
        if guild_graph:
            db_data_ac = db_data
        else:
            db_data_ac = [x for x in db_data if str(x[2])==ac]
        for line in db_data_ac:
            if min_date==None or line[0]<min_date:
                min_date = line[0]
            if max_date==None or line[0]>max_date:
                max_date = line[0]

            d_kpi.append(line[0])
            v_kpi.append(line[1])

        #add series
        playerName = dict_players[ac][0]
        ax.plot(d_kpi, v_kpi, label=playerName)

    #format dates on X axis
    date_format = mdates.DateFormatter("%d-%m")
    ax.xaxis.set_major_formatter(date_format)

    if len(list_allyCodes)>1:
        #Legend only useful if more than one player

        # Shrink current axis by 20% to make room
        # for the legend
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

        # Put a legend to the right of the current axis
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    #add title
    if guild_graph:
        title = "Progrès "+parameter+" pour la guilde "+guildName
    elif len(list_allyCodes)>1:
        list_playerNames = [dict_players[x][0] for x in list_allyCodes]
        playerNames = str(list_playerNames)
        title = "Progrès "+parameter+" pour les joueurs"
    else:
        title = "Progrès "+parameter+" pour le joueur "+playerName
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

async def get_tw_def_attack(guild_id, force_update, with_attacks=False, allyCode=None,
                            dict_guild=None):
    dict_unitsList = godata.get("unitsList_dict.json")

    rpc_data = await connect_rpc.get_tw_status(guild_id, force_update, 
                                               with_attacks=with_attacks,
                                               allyCode=allyCode,
                                               dict_guild=dict_guild)
    tw_id = rpc_data["tw_id"]
    if tw_id == None:
        return 1, "ERR: aucune GT en cours\n", None

    list_home_def_squads = rpc_data["homeGuild"]["list_defenses"]
    list_away_def_squads = rpc_data["awayGuild"]["list_defenses"]
    list_attack_squads = rpc_data["awayGuild"]["list_attacks"]

    dict_home_def_toon_player = {}
    for squad in list_home_def_squads:
        player = squad["player_name"]
        for char in squad["list_defId"]:
            char_id = char["unitId"]
            if not char_id in dict_home_def_toon_player:
                dict_home_def_toon_player[char_id] = {}

            dict_home_def_toon_player[char_id][player] = char

    dict_away_def_toon_player = {}
    for squad in list_away_def_squads:
        player = squad["player_name"]
        for char in squad["list_defId"]:
            char_id = char["unitId"]
            if not char_id in dict_away_def_toon_player:
                dict_away_def_toon_player[char_id] = {}

            dict_away_def_toon_player[char_id][player] = char

    dict_attack_toon_player = {}
    for squad in list_attack_squads:
        player = squad["attacker"]
        for char in squad["list_chars"]:
            char_id = char["unitId"]
            if not char_id in dict_attack_toon_player:
                dict_attack_toon_player[char_id] = []

            dict_attack_toon_player[char_id].append(player)

    return 0, "", {"homeDef": dict_home_def_toon_player, 
                   "awayDef": dict_away_def_toon_player, 
                   "awayAttack": dict_attack_toon_player}

#############################################################################
# find_best_toons_in_guild
# IN: txt_allyCode: one allyCode in the guild
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

async def print_tb_status(guild_id, targets_zone_stars, force_update, 
                          estimate_fights=False, estimate_platoons=False,
                          targets_platoons=None, allyCode=None):
    dict_tb = godata.get("tb_definition.json")

    ec, et, tb_data = await connect_rpc.get_tb_status(guild_id, targets_zone_stars, force_update,
                                                      compute_estimated_platoons=estimate_platoons,
                                                      targets_platoons=targets_platoons, allyCode=allyCode)
    if ec!=0:
        return 1, et, None

    dict_phase = tb_data["phase"]
    list_open_zones = tb_data["open_zones"]
    dict_zones = tb_data["zones"]
    dict_strike_zones = tb_data["strike_zones"]
    dict_tb_players = tb_data["players"]
    tb_round = dict_phase["round"]
    tb_id = dict_phase["id"]
 
    #Update DB (short so no need to parallelize)
    await connect_mysql.update_tb_round(guild_id, tb_id, tb_round, dict_phase,
                                  dict_zones, dict_strike_zones,
                                  list_open_zones, dict_tb_players)

    list_deployment_types = []
    for zone_name in list_open_zones:
        zone_deployment_type = dict_tb[zone_name]["type"]
        if not zone_deployment_type in list_deployment_types:
            list_deployment_types.append(zone_deployment_type)

    # START THE DISPLAY PART
    ret_print_tb_status = "**Territory Battle** - round "+str(dict_phase["round"])+"\n"
    sheet_url = connect_gsheets.get_sheet_url(guild_id, "BT graphs")
    if sheet_url != None:
        ret_print_tb_status += "More details, including players: "+sheet_url+"\n"

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
    round_estimated_stars = dict_phase["prev_stars"] # stars from previous rounds
    for zone_name in list_open_zones:
        ret_print_tb_status+="---------------\n"
        ret_print_tb_status+="**"+dict_tb[zone_name]["name"]+"**\n"

        max_zone_score = dict_tb[zone_name]["scores"][-1]

        # Current score - GREEN
        current_score = dict_zones[zone_name]["score"]
        if current_score > max_zone_score:
            current_score = max_zone_score
        ret_print_tb_status+="Current score: "+str(round(current_score/1000000, 1))+"M "

        # Including done fights - TEXT ONLY
        cur_strike_score = dict_zones[zone_name]["strikeScore"]
        cur_strike_fights = sum(dict_zones[zone_name]["strikeFights"].values())
        ret_print_tb_status+="(including "+str(round(cur_strike_score/1000000, 1))+"M in "+str(cur_strike_fights)+" fights)\n"

        # Estimated platoons - LIGHT GREEN
        if estimate_platoons:
            estimated_platoon_score = dict_zones[zone_name]["remainingPlatoonScore"]
            score_with_estimated_platoons = current_score + estimated_platoon_score

            if score_with_estimated_platoons > max_zone_score:
                estimated_platoon_score = max_zone_score - current_score
                score_with_estimated_platoons = max_zone_score

            if estimated_platoon_score > 0:
                ret_print_tb_status+="Estimated platoons: "+str(round(estimated_platoon_score/1000000, 1))+"M \n"
        else:
            estimated_platoon_score = 0

        # Estimated fights - ORANGE
        if estimate_fights:
            estimated_strike_score = dict_zones[zone_name]["estimatedStrikeScore"]
            estimated_strike_fights = dict_zones[zone_name]["estimatedStrikeFights"]
        else:
            estimated_strike_score = 0
            estimated_strike_fights = 0

        score_with_estimated_strikes = current_score + estimated_strike_score
        if score_with_estimated_strikes > max_zone_score:
            estimated_strike_score = max_zone_score - current_score
            score_with_estimated_strikes = max_zone_score

        if estimate_fights and estimated_strike_score > 0:
            ret_print_tb_status+="Estimated fights: "+str(round(estimated_strike_score/1000000, 1))+"M "
            ret_print_tb_status+="(in "+str(estimated_strike_fights)+" fights)\n"

        # Deployment - YELLOW
        deploy_consumption = dict_zones[zone_name]["deployment"]
        score_with_estimations = score_with_estimated_strikes + deploy_consumption
        ret_print_tb_status+="Deployment: "+str(round(deploy_consumption/1000000, 1))+"M\n"

        # Max fights - RED
        max_strike_score = dict_zones[zone_name]["maxStrikeScore"]

        # Stars
        star_for_score = dict_zones[zone_name]["estimatedStars"]
        round_estimated_stars += star_for_score
        if zone_name.endswith("bonus"):
            # Only 1 star possible in bonus zones
            ret_print_tb_status+="\u27a1 Zone result: "+'\u2b50'*star_for_score+'\u2729'*(1-star_for_score)+"\n"
        else:
            ret_print_tb_status+="\u27a1 Zone result: "+'\u2b50'*star_for_score+'\u2729'*(3-star_for_score)+"\n"

        #create image
        img = draw_tb_previsions(dict_tb[zone_name]["name"], dict_tb[zone_name]["scores"],
                                 current_score, estimated_platoon_score, estimated_strike_score, 
                                 deploy_consumption, max_strike_score)
        list_images.append(img)

    ret_print_tb_status += "----------------------------\n"
    # total stars estiated at the end of the round
    ret_print_tb_status += "Round result: "+str(round_estimated_stars)+"\u2b50\n"

    # unused depoyments (margin)
    if "ships" in list_deployment_types:
        ret_print_tb_status += "Unused deployment ships: "+str(round(remaining_ship_deploy/1000000, 1))+"M\n"
    if "chars" in list_deployment_types:
        ret_print_tb_status += "Unused deployment squads: "+str(round(remaining_char_deploy/1000000, 1))+"M\n"
    if "mix" in list_deployment_types:
        ret_print_tb_status += "Unused deployment mix: "+str(round(remaining_mix_deploy/1000000, 1))+"M\n"
    ret_print_tb_status += "----------------------------\n"

    return 0, ret_print_tb_status, list_images

def draw_score_zone(zone_img_draw, start_score, delta_score, max_score, color, position):
    goutils.log2("DBG", "draw_score_zone("+str(start_score)+", "+str(delta_score)+", "+str(max_score)+")")

    font = ImageFont.truetype("IMAGES"+os.path.sep+"arial.ttf", 18)

    end_score = start_score + delta_score
    if end_score >= max_score:
        end_score = max_score
        delta_score = max_score - start_score
    else:
        end_score = int(end_score)
    if delta_score <= 10: # allows rounding error (10 over some M points)
        return start_score

    #colored rectangle
    x_start = int(start_score/max_score*(480-20)+20)+1
    x_end = int(end_score/max_score*(480-20)+20)
    zone_img_draw.rectangle((x_start, 80, x_end, 110), color)

    #downward score bar
    zone_img_draw.line([(x_end, 80), (x_end, 120+20*position)], fill="black", width=0)

    #Text for the score bar
    end_score_txt = "{:,}".format(end_score)
    end_score_txt = str(round(end_score/1000000, 1))
    if end_score < max_score/2:
        x_txt = x_end +5
    else:
        end_score_txt_size = font.getsize(end_score_txt)
        x_txt = x_end - end_score_txt_size[0] - 5
    zone_img_draw.text((x_txt, 110+20*position), end_score_txt, "black", font=font)

    return end_score

# zone_name = ROTE4-DS
def draw_tb_previsions(zone_name, zone_scores, current_score, estimated_platoons, estimated_strikes, deployments, max_strikes):
    goutils.log2("DBG", "draw_tb_previsions("+zone_name+", "+str(zone_scores)+", "+str(current_score)+", "+str(estimated_strikes)+", "+str(deployments)+", "+str(max_strikes)+")")
    zone_img = Image.new('RGB', (500, 240), (255, 255, 255))
    zone_img_draw = ImageDraw.Draw(zone_img)

    score_3stars = zone_scores[2]

    current_score = draw_score_zone(zone_img_draw, 0, current_score, score_3stars, "darkgreen", 1)
    estplatoon_score = draw_score_zone(zone_img_draw, current_score, estimated_platoons, score_3stars, "lightgreen", 2)
    eststrike_score = draw_score_zone(zone_img_draw, estplatoon_score, estimated_strikes, score_3stars, "orange", 3)
    deployment_score = draw_score_zone(zone_img_draw, eststrike_score, deployments, score_3stars, "yellow", 4)
    final_score = draw_score_zone(zone_img_draw, deployment_score, max_strikes-estimated_strikes, score_3stars, "red", 5)

    #Draw stars
    active_star_image = Image.open("IMAGES/PORTRAIT_FRAME/star.png")
    inactive_star_image = Image.open("IMAGES/PORTRAIT_FRAME/star-inactive.png")
    active_bonus_image = Image.open("IMAGES/PORTRAIT_FRAME/bonus.png")
    inactive_bonus_image = Image.open("IMAGES/PORTRAIT_FRAME/bonus-inactive.png")
    drawn_stars = 0
    for score_star in zone_scores:
        x_star = 200 + drawn_stars*50
        if current_score >= score_star:
            if zone_name.endswith("b") and score_star!=zone_scores[2]:
                star_image = active_bonus_image
            else:
                star_image = active_star_image
        else:
            if zone_name.endswith("b") and score_star!=zone_scores[2]:
                star_image = inactive_bonus_image
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

    #add star limits
    for score_star in zone_scores:
        x_star = int(score_star / score_3stars * (480-20) + 20)

        zone_img_draw.line([(x_star, 80), (x_star, 120)], fill="black", width=2)
        
        font = ImageFont.truetype("IMAGES"+os.path.sep+"arial.ttf", 12)
        score_star_txt = "{:,}".format(score_star)
        score_star_txt_size = font.getsize(score_star_txt)
        x_txt = x_star - score_star_txt_size[0] - 5
        zone_img_draw.text((x_txt, 115), score_star_txt, "black", font=font)

    #legend
    zone_img_draw.rectangle((150, 10, 160, 20), fill="darkgreen")
    zone_img_draw.text((165, 10), "Score actuel", "black", font=font)
    zone_img_draw.rectangle((250, 10, 260, 20), fill="lightgreen")
    zone_img_draw.text((265, 10), "Pelotons", "black", font=font)
    zone_img_draw.rectangle((250, 30, 260, 40), fill="yellow")
    zone_img_draw.text((265, 30), "Déploiement", "black", font=font)
    zone_img_draw.rectangle((350, 10, 360, 20), fill="orange")
    zone_img_draw.text((365, 10), "Combats estimés", "black", font=font)
    zone_img_draw.rectangle((350, 30, 360, 40), fill="red")
    zone_img_draw.text((365, 30), "Combats max", "black", font=font)


    font = ImageFont.truetype("IMAGES"+os.path.sep+"arial.ttf", 24)
    zone_img_draw.text((10, 10), zone_name, "black", font=font)

    return zone_img

async def get_tb_alerts(guild_id, force_update):
    ec, et, tb_data = await connect_rpc.get_tb_status(guild_id, "", force_update)
    if ec!=0:
        goutils.log2("INFO", "["+guild_id+"] tb_data="+str(tb_data)[:100])
        if tb_data!=None and "tb_summary" in tb_data and tb_data["tb_summary"]!=None:
            return 2, "", tb_data["tb_summary"]
        else:
            return 1, et, None

    dict_phase = tb_data["phase"]
    dict_strike_zones = tb_data["strike_zones"]
    list_open_zones = tb_data["open_zones"]
    dict_zones = tb_data["zones"]

    territory_scores, active_round = await connect_rpc.get_tb_guild_scores(guild_id,
                                                                           dict_phase,
                                                                           dict_strike_zones,
                                                                           list_open_zones,
                                                                           dict_zones)
    goutils.log2("DBG", "["+guild_id+"] territory_scores="+str(territory_scores))

    if active_round != "":
        dict_tb = godata.get("tb_definition.json")
        
        err_code, [daily_targets, margin] = connect_gsheets.get_tb_triggers(guild_id, False)
        if err_code!=0:
            return 1, "No TB target for "+guild_id, None

        goutils.log2("DBG", "["+guild_id+"] tb_triggers="+str([daily_targets, margin]))

        #print(territory_scores)
        tb_name = dict_tb[list(territory_scores.keys())[0]]["name"].split("-")[0][:-1]
        base_zonename = "_".join(list(territory_scores.keys())[0].split("_")[:-2])
        round_number = int(active_round[-1])
        if round_number > len(daily_targets[tb_name]):
            #virtual round, after the end of TB
            return 0, "", []

        #transform targets by using zone names
        zone_daily_targets = [] # list by day
        if tb_name == "ROTE":
            pos_conflict = [[0, "02"], [1, "03"], [2, "01"]]
        else:
            if tb_name in ["GDS", "HDS"] and round_number==1:
                pos_conflict = [[0, "01"], [2, "02"]]
            elif tb_name in ["HDS"] and round_number==2:
                pos_conflict = [[0, "01"], [2, "02"]]
            else:
                pos_conflict = [[0, "01"], [1, "02"], [2, "03"]]

        #loop on days in TB targets
        for tb_daily_target in daily_targets[tb_name]:
            zone_daily_target = {}
            for pos, conflict in pos_conflict:
                zone_target = tb_daily_target[pos]
                if zone_target == "-":
                    continue
                phase = zone_target.split('-')[0][-1]
                stars = int(zone_target.split('-')[1])
                zone_name = base_zonename+"_phase0"+phase+"_conflict"+conflict
                zone_daily_target[zone_name] = stars

            zone_daily_targets.append(zone_daily_target)

        current_targets = zone_daily_targets[round_number-1]

        tb_trigger_messages=[]
        for zone in current_targets:
            zone_short_name = dict_tb[zone]["name"]
            if not zone in territory_scores:
                tb_trigger_messages.append("ERREUR: phase "+zone_short_name+" non atteinte")
            else:
                current_target_stars = current_targets[zone]
                current_score = territory_scores[zone]
                star_scores = dict_tb[zone]["scores"]

                if current_target_stars == 0:
                    if current_score >= star_scores[0]:
                        tb_trigger_messages.append(":x: 1ère étoile atteinte en "+zone_short_name+" alors qu'il ne fallait pas !")
                    elif current_score >= (star_scores[0]-margin):
                        delta_score_M = round((star_scores[0]-current_score)/1000000, 1)
                        tb_trigger_messages.append(":warning: la 1ère étoile se rapproche en "+zone_short_name+" et il ne faut pas l'atteindre (il reste "+str(delta_score_M)+"M)")
                elif current_target_stars == 1:
                    if current_score >= star_scores[2]:
                        tb_trigger_messages.append(":heart_eyes: 3e étoile atteinte en "+zone_short_name+" alors qu'on en visait une seule !")
                    elif current_score >= star_scores[1]:
                        tb_trigger_messages.append(":heart_eyes: 2e étoile atteinte en "+zone_short_name+" alors qu'on en visait une seule !")
                    elif current_score >= star_scores[0]:
                        tb_trigger_messages.append(":white_check_mark: 1ère étoile atteinte en "+zone_short_name+", objectif atteint")
                    elif current_score >= (star_scores[0]-margin):
                        delta_score_M = round((star_scores[0]-current_score)/1000000, 1)
                        tb_trigger_messages.append(":point_right: la 1ère étoile se rapproche en "+zone_short_name+" (il reste "+str(delta_score_M)+"M)")
    
                elif current_target_stars == 2:
                    if current_score >= star_scores[2]:
                        tb_trigger_messages.append(":heart_eyes: 3e étoile atteinte en "+zone_short_name+" alors qu'on en visait seulement deux !")
                    elif current_score >= star_scores[1]:
                        tb_trigger_messages.append(":white_check_mark: 2e étoile atteinte en "+zone_short_name+", objectif atteint")
                    elif current_score >= (star_scores[1]-margin):
                        delta_score_M = round((star_scores[1]-current_score)/1000000, 1)
                        tb_trigger_messages.append(":point_right: la 2e étoile se rapproche en "+zone_short_name+" (il reste "+str(delta_score_M)+"M)")
                    elif current_score >= star_scores[0]:
                        tb_trigger_messages.append(":thumbsup: 1ère étoile atteinte en "+zone_short_name+", en route vers la 2e")

                elif current_target_stars == 3:
                    if current_score >= star_scores[2]:
                        tb_trigger_messages.append(":white_check_mark: 3e étoile atteinte en "+zone_short_name+", objectif atteint")
                    elif current_score >= (star_scores[2]-margin):
                        delta_score_M = round((star_scores[2]-current_score)/1000000, 1)
                        tb_trigger_messages.append(":point_right: la 3e étoile se rapproche en "+zone_short_name+" (il reste "+str(delta_score_M)+"M)")
                    elif current_score >= star_scores[1]:
                        tb_trigger_messages.append(":thumbsup: 2e étoile atteinte en "+zone_short_name+", en route vers la 3e")
                    elif current_score >= star_scores[0]:
                        tb_trigger_messages.append(":thumbsup: 1ère étoile atteinte en "+zone_short_name+", en route vers la 3e")
    else:
        tb_trigger_messages = []

    return 0, "", tb_trigger_messages
    
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
        #print(txt_cmd)

##############################
# IN guild_id
# IN txt_allyCode: tis account needs to be a bot or a google user
# IN zone_shortname: DS, LS, MS, bot, mid, top
# IN characters: one alias for one unit ("lobot") or a group of units ("all", "tag:c:all", "tag:empire")
#
# This function extracts the unit IDs and sends the list to the RPC function
##############################
async def deploy_tb(guild_id, txt_allyCode, zone_shortname, characters):
    dict_unitsList = godata.get("unitsList_dict.json")

    #Manage request for all characters
    if characters == 'all':
        list_character_ids=list(dict_unitsList.keys())
    else:
        #specific list of characters for one player
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([characters])
        if txt != '':
            return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt

    dict_tb = godata.get("tb_definition.json")
    ec, et, tb_data = await connect_rpc.get_tb_status(guild_id, "", -1)
    if ec!=0:
        return 1, et

    dict_phase = tb_data["phase"]
    list_open_zones = tb_data["open_zones"]

    tb_type = dict_phase["type"]
    if not tb_type in dict_tb:
        return 1, "TB inconnue du bot"

    zone_found = False
    list_zone_names = []
    for zone_name in list_open_zones:
        list_zone_names.append(dict_tb[zone_name]["name"])
        if dict_tb[zone_name]["name"].endswith("-"+zone_shortname):
            target_zone_name = dict_tb[zone_name]["name"]
            zone_found = True
            break

    if not zone_found:
        return 1, "zone inconnue: " + zone_shortname + " " + str(list_zone_names)

    # Filter out units depending on zone type mix/char/ship
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

    ec, txt = await connect_rpc.deploy_tb(txt_allyCode, zone_name, list_character_ids)

    return ec, txt

############################################################
# transforms aliases into defID and zone alias into zone Id
async def deploy_def_tw(guild_id, txt_allyCode, zone_shortname, characters):
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

    ec, txt = await connect_rpc.deploy_tw(guild_id, txt_allyCode, zone_name, list_character_ids)

    return ec, txt

############################################################
# transforms aliases into defID and platoon_name into zone Id
async def deploy_platoons_tb(allyCode, platoon_name, characters):
    dict_unitsList = godata.get("unitsList_dict.json")

    #specific list of characters for one player
    list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(characters)
    if txt != '':
        return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt

    dict_tb = godata.get("tb_definition.json")
    tb_name = platoon_name.split('-')[0][:-1]
    tb_phase = platoon_name.split('-')[0][-1]
    platoon_side = platoon_name.split('-')[1]
    platoon_zone_name = platoon_name[:-2]
    platoon_position = platoon_name.split('-')[2]
    tb_id = dict_tb[tb_name]["id"]
    tb_prefix = dict_tb[tb_id]["prefix"]

    zone_found = False
    list_zone_names = []
    for key in dict_tb:
        #print(key)
        if not key.startswith(tb_prefix):
            continue
        zone_name = key
        list_zone_names.append(dict_tb[zone_name]["name"])
        if dict_tb[zone_name]["name"] == platoon_zone_name:
            zone_name = zone_name+"_recon01"
            zone_found = True
            break

    if not zone_found:
        return 1, "zone inconnue: " + platoon_name + " " + str(list_zone_names)

    if tb_name == "ROTE":
        platoon_id = "tb3-platoon-"+str(7-int(platoon_position))
    else:
        platoon_id = "hoth-platoon-"+platoon_position

    ec, txt = await connect_rpc.platoon_tb(str(allyCode), zone_name, platoon_id, list_character_ids)

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
    if "limitBreakRef" in dict_units[unit_id]:
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
    if "uniqueAbilityRef" in dict_units[unit_id]:
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

    if dict_abilities[ability_id]["nameKey"] in FRE_FR:
        ability_name = FRE_FR[dict_abilities[ability_id]["nameKey"]]
    else:
        ability_name = dict_abilities[ability_id]["nameKey"]
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

###########################################
#FUNCTION: detect_fulldef(guild_id)
#IN: server ID
#OUT: dict_player_status {"Vince":1, "Gui":1, "HB":0, "Darak":-1}
#with 1=fulldef / -1=normal / 0=unknown
###########################################
async def detect_fulldef(guild_id, force_update, allyCode=None):
    dict_unitsList = godata.get("unitsList_dict.json")
    ec, et, ret_data = await get_tw_def_attack(guild_id, force_update, allyCode=allyCode)
    if ec != 0:
        return ec, et, None
    dict_def_toon_player = ret_data["homeDef"]

    # Get the count of units and capital ships in the guild
    query = "SELECT defId, count(*) FROM roster " \
            "JOIN players ON players.allyCode=roster.allyCode " \
            "WHERE guildId='"+guild_id+"' " \
            "AND ((combatType=1 AND gear>=12) OR (combatType=2 AND defId like 'CAPITAL%')) " \
            "GROUP BY defId "
    goutils.log2("DBG", query)
    data_db = connect_mysql.get_table(query)

    # This dict contains the ratio (units in defense) / (units in the guild)
    # If a player puts lots of low-ratio units in defense, he is probably full def
    dict_char_ratio_rarity = {}
    for [unit_id, unit_count] in data_db:
        if unit_id in dict_def_toon_player:
            dict_char_ratio_rarity[unit_id] = len(dict_def_toon_player[unit_id]) / unit_count

    # Get the count of units and capital ships per player in the guild
    query = "SELECT name, count(*) FROM roster " \
            "JOIN players ON players.allyCode=roster.allyCode " \
            "WHERE guildId='"+guild_id+"' " \
            "AND ((combatType=1 AND gear>=12) OR (combatType=2 AND defId like 'CAPITAL%')) " \
            "GROUP BY players.allyCode "
    goutils.log2("DBG", query)
    data_db = connect_mysql.get_table(query)
    
    dict_units_per_player = {}
    for [name, unit_count] in data_db:
        dict_units_per_player[name] = unit_count


    # This dict contains all defense units of a player
    dict_def_player_toon = {}
    for unit_id in dict_def_toon_player:
        for player in dict_def_toon_player[unit_id]:
            if not player in dict_def_player_toon:
                dict_def_player_toon[player] = []
            dict_def_player_toon[player].append(unit_id)

    dict_player_fulldef_ratio = {}
    for player in dict_def_player_toon:
        if not player in dict_units_per_player:
            #player has left the guild
            continue

        list_ratio_rarity = []
        for unit_id in dict_def_player_toon[player]:
            if unit_id in dict_char_ratio_rarity:
                list_ratio_rarity.append(dict_char_ratio_rarity[unit_id])
        if len(list_ratio_rarity)==0:
            ratio_rarity=1
        else:
            # Average of unit rarity in def
            ratio_rarity = sum(list_ratio_rarity)/len(list_ratio_rarity)

        # Ratio with used def units / total player units
        ratio_usage = len(dict_def_player_toon[player]) / dict_units_per_player[player]
        dict_player_fulldef_ratio[player] = ratio_rarity / ratio_usage

    dict_fulldef = {}
    for player in dict_player_fulldef_ratio:
        ratio = dict_player_fulldef_ratio[player]
        if ratio >= 1.0:
            dict_fulldef[player] = -1
        else:
            dict_fulldef[player] = 1

    return 0, "", dict_fulldef

# OUT: 1 > error | 2 > missing arguments
# Actualy manages
# - missing registrations in round -1
# - insufficient defenses in round 0
# - insufficient attacks in round 1
async def get_tw_insufficient_attacks(guild_id, args, allyCode=None, fulldef_detection=False):
    if allyCode==None:
        ec, et, ret_dict = await connect_rpc.get_tw_active_players(guild_id, 0)
    else:
        ec, et, ret_dict = await connect_rpc.get_tw_active_players(guild_id, 1, allyCode=allyCode)

    if ec != 0:
        return ec, et, None
    list_active_players = ret_dict["active"]
    tw_round = ret_dict["round"]

    if tw_round == None:
        return 1, "ERR: pas de GT en cours", None
    elif tw_round==-1:
        # sign up phase. Only check missing members
        list_inactive_players = ret_dict["inactive"]
        return 0, "", list_inactive_players

    if len(args) != 2:
        return 2, "need 2 values in args", None

    min_char_teams = int(args[0])
    min_ship_teams = int(args[1])

    if tw_round==0:
        # DEFENSE phase
        dict_guild = ret_dict["rpc"]["guild"]
        twStatus = dict_guild["territoryWarStatus"][0]
        dict_leaderboard = {} # key=playerName, value=[gnd def, 0, ship def, 0, 0]
        for conflictStatus in twStatus["homeGuild"]["conflictStatus"]:
            is_ship = conflictStatus["zoneStatus"]["zoneId"] in ['tw_jakku01_phase03_conflict01',
                                                                 'tw_jakku01_phase04_conflict01']
            if "warSquad" in conflictStatus:
                for warSquad in conflictStatus["warSquad"]:
                    playerName = warSquad["playerName"]
                    if not playerName in dict_leaderboard:
                        dict_leaderboard[playerName] = [0, 0, 0, 0, 0]
                    if is_ship:
                        dict_leaderboard[playerName][2] +=1
                    else:
                        dict_leaderboard[playerName][0] +=1

        dict_fulldef = {}
    else:
        # ATTACK phase
        # Called with use_cache_data = -1 as RPC call was just made in get_tw_active
        ec, et, dict_leaderboard = await connect_rpc.get_tw_participation(guild_id, -1, allyCode=allyCode)
        if ec != 0:
            return ec, et, None

        if fulldef_detection:
            ec, et, dict_fulldef = await detect_fulldef(guild_id, -1, allyCode=allyCode)
            if ec != 0:
                return ec, et, None
        else:
            dict_fulldef = {}
            for player in list_active_players:
                dict_fulldef[player] = -1

    dict_players = connect_mysql.load_config_players()[0]

    dict_insufficient_teams = {}
    for player in list_active_players:
        if player in dict_leaderboard:
            scores = dict_leaderboard[player]
            char_teams = dict_leaderboard[player][0]
            ship_teams = dict_leaderboard[player][2]
        else:
            char_teams = 0
            ship_teams = 0

        if player in dict_fulldef:
            fulldef = dict_fulldef[player]
        elif tw_round==0:
            fulldef = -1 #normal
        else:
            fulldef = 0 #unknown
        dict_insufficient_teams[player] = [None, None, fulldef]
        if char_teams < min_char_teams:
            dict_insufficient_teams[player][0] = char_teams
        if ship_teams < min_ship_teams:
            dict_insufficient_teams[player][1] = ship_teams

    return 0, "", dict_insufficient_teams


##############################
# IN: dict_platoons_done
# IN: dict_platoons_allocation
# OUT: list_missing_platoons - [{"player_name": "Jerome342", "platoon": "ROTE1-DS-3", "locked": True", character_name": "General Kenobi"}, {"player_name": "Tartufe du 75", "platoon": "ROTE2-LS-6", "locked": Flase, "character_name": "Lobot"}, ...]
# OUT: list_err - ["ERR - ça va pas", "ERR - perso manquant", ...]
##############################
def get_missing_platoons(dict_platoons_done, dict_platoons_allocation, list_open_territories,
                         targets_free_platoons=None):

    # prepare free platoons
    list_free_platoons = [] # [ROTE2-MS-1, ROTE2-MS-2, ROTE3-MS-4, ...]
    if targets_free_platoons != None:
        for p in targets_free_platoons.split('/'):
            if ":" in p:
                p_zone = p.split(":")[0]
                p_num = p.split(":")[1].split(",")
            else:
                p_zone = p
                p_num = ["1", "2", "3", "4", "5", "6"]

            for terr in list_open_territories:
                if terr["zone_name"].endswith(p_zone):
                    p_zone = terr["zone_name"]
            for num in p_num:
                list_free_platoons.append(p_zone+"-"+num)

    list_platoon_names = sorted(dict_platoons_done.keys())
    phase_names_already_displayed = []
    list_missing_platoons = []
    list_err = []
    # print(dict_platoons_done["GDS1-top-5"])
    # print(dict_platoons_allocation["GDS1-top-5"])
    for platoon_name in dict_platoons_done:
        phase_name = platoon_name.split('-')[0][:-1]
        if not phase_name in phase_names_already_displayed:
            phase_names_already_displayed.append(phase_name)
        #print("---"+platoon_name)
        #print(dict_platoons_done[platoon_name])
        zone_name = platoon_name[:-2]

        platoon_locked = False
        open_platoon = False
        for terr in list_open_territories:
            if terr["zone_name"] == zone_name:
                open_platoon = True
                if "cmdState" in terr:
                    platoon_locked = (terr["cmdState"] == "IGNORED")
        if not open_platoon:
            continue

        for perso in dict_platoons_done[platoon_name]:
            if '' in dict_platoons_done[platoon_name][perso]:
                if platoon_name in dict_platoons_allocation:
                    #print(dict_platoons_allocation[platoon_name])
                    if perso in dict_platoons_allocation[platoon_name]:
                        for allocated_player in dict_platoons_allocation[
                                platoon_name][perso]:
                            if not allocated_player in dict_platoons_done[
                                    platoon_name][perso] and allocated_player \
                                    != "Filled in another phase":
                                        list_missing_platoons.append({"player_name": allocated_player, 
                                                                      "platoon": platoon_name, 
                                                                      "locked": platoon_locked, 
                                                                      "character_name": perso})
                    else:
                        err_msg = perso + " existe dans la zone "+platoon_name+" mais n\'a pas été affecté par le bot"
                        list_err.append('ERR: ' + err_msg)
                        goutils.log2("ERR", err_msg)
                        goutils.log2("ERR", dict_platoons_allocation[platoon_name].keys())

                        # Still need to display it as not filled
                        list_missing_platoons.append({"player_name": None,
                                                      "platoon": platoon_name, 
                                                      "locked": platoon_locked, 
                                                      "character_name": perso})
                elif platoon_name in list_free_platoons:
                    # whole zone not allocated
                    list_missing_platoons.append({"player_name": None,
                                                  "platoon": platoon_name, 
                                                  "locked": platoon_locked, 
                                                  "character_name": perso})

    return list_missing_platoons, list_err

#############################
# IN: dict_player
# IN: unit_id
# OUT: [kyro_energy, shard_energy={"yellow"=23, "red"=30, "blue"=200}]
#############################
def get_unit_farm_energy(dict_player, unit_id, target_gear):
    #target_rarity = 7 by default

    dict_unitsList = godata.get("unitsList_dict.json")
    shard_droprate = 0.3
    kyro_droprate = 0.2

    #SHARDS
    if unit_id in dict_player["rosterUnit"]:
        #print(dict_player["rosterUnit"][unit_id])
        unit_rarity = dict_player["rosterUnit"][unit_id]["currentRarity"]
        unit_gear = dict_player["rosterUnit"][unit_id]["currentTier"]
        unit_eqpt = [None, None, None, None, None, None]
        for eqpt in dict_player["rosterUnit"][unit_id]["equipment"]:
            unit_eqpt[eqpt["slot"]] = eqpt["equipmentId"]
    else:
        unit_rarity = 0
        unit_gear = 1
        unit_eqpt = [None, None, None, None, None, None]

    d_stars = {0:330, 1:320, 2:305, 3:280, 4:230, 5:185, 6: 100, 7:0}
    d_energy = {}
    d_energy["yellow"] = {"M01":12, "M02":12, "M03":12,
                          "M04":12, "M05":16, "M06":16,
                          "M07":20, "M08":20, "M09":20}
    d_energy["red"] =    {"M01": 8, "M02": 8, "M03":10,
                          "M04":10, "M05":12, "M06":12,
                          "M07":16, "M08":16}
    d_energy["blue"] =   {"M01":16, "M02":20, "M03":20,
                          "M04":20, "M05":20}
                          
    needed_shards = d_stars[unit_rarity]
    shard_energy = {}
    if "farmingInfo" in dict_unitsList[unit_id]:
        if len(dict_unitsList[unit_id]['farmingInfo']) > 0:
            for farming_location in dict_unitsList[unit_id]['farmingInfo']:
                campaignId = farming_location[0]["campaignId"]
                if campaignId.startswith('C01'):
                    if campaignId[3:] == 'L':
                        energy_color = "yellow"
                    elif campaignId[3:] == 'D':
                        energy_color = "yellow"
                    elif campaignId[3:] == 'H':
                        energy_color = "red"
                    elif campaignId[3:] == 'SP':
                        energy_color = "blue"
                else:
                    #not a energy node, go to next farming location
                    continue

                shard_location_found = True
                tab = farming_location[0]["campaignMapId"]
                farming_speed = farming_location[1]
                shard_cost = d_energy[energy_color][tab]
                needed_energy = shard_cost * needed_shards / farming_speed / shard_droprate

                #DEBUG
                #print("farming_speed="+str(farming_speed))
                #print("needed_shards="+str(needed_shards))
                #print("shard_cost="+str(shard_cost))

                if not energy_color in shard_energy:
                    shard_energy[energy_color] = needed_energy
                else:
                    current_energy = shard_energy[energy_color]
                    if current_energy > needed_energy:
                        shard_energy[energy_color] = needed_energy

        else:
            #cas des persos farmables nulle-part
            # on prend la cas pire : énergie jaune 20 énergies par éclat
            needed_energy = 20 * needed_shards / 1 / shard_droprate
            shard_energy["yellow"] = needed_energy


    # Kyros
    #key=eqpt_id, value=count
    err_code, err_txt, needed_eqpt = get_needed_eqpt(dict_player,
                                                     [{"defId": unit_id,
                                                       "gear": target_gear,
                                                       "relic": 0}], 
                                                     breakdown=True)
    kyro_energy = 0
    if "172Salvage" in needed_eqpt:
        kyro_energy += needed_eqpt["172Salvage"] * 10 / kyro_droprate
    if "173Salvage" in needed_eqpt:
        kyro_energy += needed_eqpt["173Salvage"] * 10 / kyro_droprate

    return kyro_energy, shard_energy

def get_needed_eqpt(dict_player, list_units, breakdown=False):
    dict_unitsList = godata.get("unitsList_dict.json")
    dict_relic = godata.get("relic_dict.json")

    needed_eqpt = {} #key=eqpt_id, value=count

    for unit in list_units:
        unit_id = unit["defId"]
        target_gear = unit["gear"]
        target_relic = unit["relic"]

        if dict_unitsList[unit_id]["combatType"]==2:
            # No equipment required for a ship
            continue

        if unit_id in dict_player["rosterUnit"]:
            unit_gear = dict_player["rosterUnit"][unit_id]["currentTier"]
            if "relic" in dict_player["rosterUnit"][unit_id]:
                unit_relic = max(0, dict_player["rosterUnit"][unit_id]["relic"]["currentTier"]-2)
            else:
                unit_relic = 0
            unit_eqpt = [None, None, None, None, None, None]
            for eqpt in dict_player["rosterUnit"][unit_id]["equipment"]:
                unit_eqpt[eqpt["slot"]] = eqpt["equipmentId"]
        else:
            unit_rarity = 0
            unit_gear = 1
            unit_relic = 0
            unit_eqpt = [None, None, None, None, None, None]

        #####################
        # GEAR equipment
        #####################
        if unit_gear < target_gear:
            # current tier
            tier_eqpt = dict_unitsList[unit_id]["unitTier"][unit_gear-1]["equipmentSet"]
            for pos_eqpt in [0, 1, 2, 3, 4, 5]:
                if unit_eqpt[pos_eqpt]==None:
                    if not tier_eqpt[pos_eqpt] in needed_eqpt:
                        needed_eqpt[tier_eqpt[pos_eqpt]] = 0
                    needed_eqpt[tier_eqpt[pos_eqpt]] += 1
                #print(needed_eqpt)

            # other tiers
            for i_gear in range(unit_gear, target_gear-1):
                tier_eqpt = dict_unitsList[unit_id]["unitTier"][i_gear]["equipmentSet"]
                #print(str(i_gear+1)+": "+str(tier_eqpt))
                for eqpt in tier_eqpt:
                    if not eqpt in needed_eqpt:
                        needed_eqpt[eqpt] = 0
                    needed_eqpt[eqpt] += 1
                #print(needed_eqpt)

            #breakdown equipments
            if breakdown:
                needed_eqpt, remain_to_breakdown = breakdown_to_farmable_eqpt(needed_eqpt)

        #####################
        # RELIC equipment
        #####################
        if unit_relic < target_relic:
            for i_relic in range(unit_relic+1, target_relic+1):
                relic_recipe = dict_relic[str(i_relic)]
                for eqpt in relic_recipe:
                    if not eqpt in needed_eqpt:
                        needed_eqpt[eqpt] = 0
                    needed_eqpt[eqpt] += relic_recipe[eqpt]
                #print(needed_eqpt)

    return 0, "", needed_eqpt

#####################
#IN: list of eqpt
#IN: one_level: True if breakdown only once / False if breakdown completely
#OUT: list of farmable eqpt, to get the needed one
#OUT: remain_to_breakdown: True if something remains to breakdown (always False if one_level=False)
def breakdown_to_farmable_eqpt(needed_eqpt, one_level=False):
    dict_eqpt = godata.get("eqpt_dict.json")

    farmable_eqpt = dict(needed_eqpt) #copy the source

    continue_loop = True
    while(continue_loop):
        continue_loop = False
        eqpt_id_list = list(farmable_eqpt.keys())
        for eqpt_id in eqpt_id_list:
            if eqpt_id in dict_eqpt and "recipe" in dict_eqpt[eqpt_id]:
                continue_loop = True
                eqpt_count = farmable_eqpt[eqpt_id]
                recipe = dict_eqpt[eqpt_id]["recipe"]
                for ingredient in recipe:
                    if not ingredient["id"] in farmable_eqpt:
                        farmable_eqpt[ingredient["id"]] = 0
                    farmable_eqpt[ingredient["id"]] += eqpt_count * ingredient["maxQuantity"]
                del farmable_eqpt[eqpt_id]

        if one_level:
            break

    return farmable_eqpt, continue_loop

def update_raid_estimates_from_wookiebot(raid_name, file_content):
    #print(file_content[:100])
    for line in file_content.split("\n")[1:]:
        fields = line.split('"')
        if len(fields)<4:
            break
        allyCode_txt = fields[3]
        columns = line.split(",")
        score_txt = columns[2]
        query = "INSERT INTO raid_estimates (raid_name, allyCode, score)\n"
        query+= "VALUES('"+raid_name+"', "+allyCode_txt+", "+score_txt+") \n"
        query+= "ON DUPLICATE KEY UPDATE score="+score_txt
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

    return 0, ""

def update_gl_progress_from_wookiebot(gl_name, file_content):
    #print(file_content[:100])
    for line in file_content.split("\n")[1:]:
        fields = line.split(',')
        if len(fields)<3:
            break
        allyCode_txt = fields[1][1:-1] #removing the " at both ends
        progress = float(fields[2])
        completed = (fields[3] != '"-"')
        connect_mysql.update_gv_history(allyCode_txt, None, gl_name, True, progress, completed, "wookiebot")

    return 0, ""

def store_eb_allocations(guild_id, tb_name, phase, allocations):
    goutils.log2("INFO", (guild_id, tb_name, phase))
    if phase[-1] == "1":
        #1st phase of TB, remove all previous configs for this guild
        query = "DELETE FROM platoon_allocations " \
                "WHERE config_id IN (SELECT id FROM platoon_config WHERE guild_id='"+guild_id+"')"
        goutils.log2("INFO", query)
        connect_mysql.simple_execute(query)

        query = "DELETE FROM platoon_config " \
                "WHERE guild_id='"+guild_id+"'"
        goutils.log2("INFO", query)
        connect_mysql.simple_execute(query)
    else:
        #Not 1st phase of TB, remove all previous configs for this guild and phase
        query = "DELETE FROM platoon_allocations " \
                "WHERE config_id IN (SELECT id FROM platoon_config WHERE guild_id='"+guild_id+"' AND phases='"+phase+"')"
        goutils.log2("INFO", query)
        connect_mysql.simple_execute(query)

        query = "DELETE FROM platoon_config " \
                "WHERE guild_id='"+guild_id+"'" \
                "AND phases='"+phase+"'"
        goutils.log2("INFO", query)
        connect_mysql.simple_execute(query)

    #Create config
    query = "INSERT INTO platoon_config(guild_id, tb_name, phases) \n"
    query+= "VALUES('"+guild_id+"', '"+tb_name+"', '"+phase+"')"
    goutils.log2("INFO", query)
    connect_mysql.simple_execute(query)

    #Get the newly created conf ID
    query = "SELECT id FROM platoon_config \n"
    query+= "WHERE guild_id='"+guild_id+"' \n"
    query+= "AND tb_name='"+tb_name+"'\n"
    query+= "AND phases='"+phase+"'"
    goutils.log2("INFO", query)
    conf_id = connect_mysql.get_value(query)

    #Prepare the dict to transform names into unit ID
    dict_units = godata.get("unitsList_dict.json")
    FRE_FR = godata.get("FRE_FR.json")
    dict_names = {}
    for unit_id in dict_units:
        unit_name = FRE_FR[dict_units[unit_id]["nameKey"]]
        dict_names[unit_name] = unit_id

    #Prepare the dict to transform player names into allyCodes
    query = "SELECT name, allyCode FROM players WHERE guildId='"+guild_id+"'"
    goutils.log2("INFO", query)
    db_data = connect_mysql.get_table(query)
    dict_players = {}
    for line in db_data:
        dict_players[line[0]] = line[1]

    #Prepare the dict to transform platoon names into zone IDs
    dict_tb = godata.get("tb_definition.json")
    tb_zones = [k for k in dict_tb.keys() if re.fullmatch(".*phase\d\d_conflict\d\d(_bonus)?", k)!=None]
    dict_zones = {}
    for zone in tb_zones:
        dict_zones[dict_tb[zone]["name"]] = zone

    #Store new allocations
    for platoon_name in allocations:
        platoon_zone = platoon_name[:-2]
        platoon_position = platoon_name[-1]
        zone_id = dict_zones[platoon_zone]+"_recon01"
        if tb_name == "ROTE":
            platoon_id = "tb3-platoon-"+str(7-int(platoon_position))
        else:
            platoon_id = "hoth-platoon-"+platoon_position

        allocation = allocations[platoon_name]

        for unit_name in allocation:
            unit_id = dict_names[unit_name]
            players = allocation[unit_name]

            for p_name in players:
                if p_name=='':
                    ac = "NULL"
                elif p_name=='Filled in another phase':
                    ac = "-1"
                elif p_name in dict_players:
                    ac = str(dict_players[p_name])
                else:
                    #player has left the guild
                    ac = "999999999"
                query = "INSERT INTO platoon_allocations(config_id, allyCode, unit_id, zone_id, platoon_id) \n"
                query+= "VALUES("+str(conf_id)+", "+ac+", '"+unit_id+"', '"+zone_id+"', '"+platoon_id+"')"
                goutils.log2("INFO", query)
                connect_mysql.simple_execute(query)

    return 0, ""

async def check_tw_counter(txt_allyCode, guild_id, counter_type):
    dict_capas = godata.get("unit_capa_list.json")

    known_counters = ['SEEvsJMK', 'ITvsGEOS']
    if not counter_type in known_counters:
        return 1, "Counter inconnu: "+counter_type+" (dans la liste "+str(known_counters)+")"

    # Get TW data and opponent teams
    rpc_data = await connect_rpc.get_tw_status(guild_id, 0)
    tw_id = rpc_data["tw_id"]
    if tw_id == None:
        return 2, "ERR: pas de GT en cours"

    list_opponent_squads = [x for x in rpc_data["awayGuild"]["list_defenses"] if not x["is_beaten"]]
    opp_guild_name = rpc_data["opp_guildName"]

    # Get data for this player
    e, t, dict_player = await load_player(txt_allyCode, 1, False)
    if e != 0:
        return 1, 'ERR: joueur non trouvé pour code allié ' + txt_allyCode, []

    output_txt = "Counter "+counter_type+" pour "+dict_player["name"]
    count_opponent = 0
    if counter_type == "ITvsGEOS":
        # Check attacker stats
        if not "ADMIRALPIETT" in dict_player["rosterUnit"]:
            return 2, "Pas de ITvsGEOS sans Piett"
        my_Piett_speed = int(dict_player["rosterUnit"]["ADMIRALPIETT"]["stats"]["final"]["5"]*1e-8)
        output_txt += "\nVitesse de mon Piett = "+str(my_Piett_speed)

        output_txt += "\n-----"

        # Check opponent stats
        required_opp_units = ['GEONOSIANBROODALPHA', 'GEONOSIANSPY', 'SUNFAC', 'GEONOSIANSOLDIER', 'POGGLETHELESSER']
        for squad in list_opponent_squads:
            opp_player_name = squad["player_name"]
            opp_units = [x["unitId"] for x in squad["list_defId"]]
            #print(squad["player_name"]+": "+str(opp_units))
            counter_required = 0
            for unit in opp_units:
                if unit in required_opp_units:
                    counter_required+=1
            if counter_required < len(required_opp_units):
                # not valid ennemy
                continue

            count_opponent+=1
            #Get fastest unit in enemy squad
            query = "SELECT MAX(stat5) FROM roster " \
                    "JOIN players on players.allyCode=roster.allyCode "\
                    "WHERE players.name='"+opp_player_name.replace("'", "''")+"' "\
                    "AND guildName='"+opp_guild_name.replace("'", "''")+"' "\
                    "AND defId IN "+str(tuple(required_opp_units))
            goutils.log2("DBG", query)
            db_data = connect_mysql.get_value(query)
            if db_data == None:
                return 1, "Joueur "+opp_player_name+" inconnu, veuillez charger les infos la guilde adverse avant de lancer cette commande"

            opp_geo_max_speed = int(db_data*1e-8)
            output_txt += "\nVitesse max des géos de "+opp_player_name+" = "+str(opp_geo_max_speed)

            if opp_geo_max_speed < (my_Piett_speed-40):
                output_txt += " > "+emoji_check
            else:
                output_txt += " > "+emoji_cross

        if len(list_opponent_squads)==0:
            output_txt += "Aucun adversaire détecté"
        return 0, output_txt

    elif counter_type == "SEEvsJMK":
        # Check attacker stats
        if not "SITHPALPATINE" in dict_player["rosterUnit"]:
            return 2, "Pas de SEEvsJMK sans SEE"
        my_SEE_health = int(dict_player["rosterUnit"]["SITHPALPATINE"]["stats"]["final"]["1"]*1e-8)
        output_txt += "\nSanté de mon SEE = "+str(my_SEE_health)

        if my_SEE_health < 180000:
            output_txt += "\nSanté de mon SEE < 180k"
            output_txt += "\nCounter probablement non-valide"

        if not "WATTAMBOR" in dict_player["rosterUnit"]:
            return 2, "Pas de SEEvsJMK sans Wat"

        if not "ARMORER" in dict_player["rosterUnit"]:
            return 2, "Pas de SEEvsJMK sans l'Armurière"
        my_Armorer_speed = int(dict_player["rosterUnit"]["ARMORER"]["stats"]["final"]["5"]*1e-8)
        output_txt += "\nVitesse de mon Armurière = "+str(my_Armorer_speed)

        if not "GRANDADMIRALTHRAWN" in dict_player["rosterUnit"]:
            return 2, "Pas de SEEvsJMK sans Thrawn"
        my_Thrawn_speed = int(dict_player["rosterUnit"]["GRANDADMIRALTHRAWN"]["stats"]["final"]["5"]*1e-8)
        output_txt += "\nVitesse de mon Thrawn = "+str(my_Thrawn_speed)

        if my_Armorer_speed < my_Thrawn_speed+21:
            output_txt += "\nVitesse de mon Armurière < vitesse de mon Thrawn+21"
            output_txt += "\nCounter non-valide"
            return 2, output_txt

        output_txt += "\n-----"

        # Check opponent stats
        required_opp_units = ['JEDIMASTERKENOBI', 'COMMANDERAHSOKA', 'AHSOKATANO', 'GENERALKENOBI']
        fifth_unit_id = None
        macewindu_U2_omicronTier = dict_capas['MACEWINDU']['U2']["omicronTier"]
        for squad in list_opponent_squads:
            opp_player_name = squad["player_name"]
            opp_units = [x["unitId"] for x in squad["list_defId"]]
            #print(squad["player_name"]+": "+str(opp_units))
            counter_required = 0
            for unit in opp_units:
                if unit in required_opp_units:
                    counter_required+=1
                else:
                    fifth_unit_id = unit
            if counter_required < len(required_opp_units):
                # not valid ennemy
                continue

            count_opponent+=1

            #Get speed of ennemy GK
            query = "SELECT stat5 FROM roster " \
                    "JOIN players on players.allyCode=roster.allyCode "\
                    "WHERE players.name='"+opp_player_name.replace("'", "''")+"' "\
                    "AND guildName='"+opp_guild_name.replace("'", "''")+"' "\
                    "AND defId='GENERALKENOBI' "
            goutils.log2("DBG", query)
            db_data = connect_mysql.get_value(query)
            if db_data == None:
                return 1, "Joueur "+opp_player_name+" inconnu, veuillez charger les infos la guilde adverse avant de lancer cette commande"
            gk_speed = int(db_data/100000000)

            if gk_speed > (my_Thrawn_speed-11):
                output_txt += "\nVitesse du General Kenobi de "+opp_player_name+" = "+str(gk_speed)+" ( >Thrawn-11)"
                output_txt += " > "+emoji_cross
                continue

            # Check specific 5th units for which the speed is not relevant
            if fifth_unit_id == "SHAAKTI":
                # She cannot oppose the counter
                output_txt += "\nLe 5e perso de "+opp_player_name+" est Shaak-Ti > "+emoji_check
                continue
            elif fifth_unit_id == "AAYLASECURA":
                # stun ability is a nogo
                output_txt += "\nLe 5e perso de "+opp_player_name+" est Aayla > "+emoji_cross
                continue
            elif fifth_unit_id == "R2D2_LEGENDARY":
                # stun ability is a nogo
                output_txt += "\nLe 5e perso de "+opp_player_name+" est R2-D2 > "+emoji_cross
                continue

            #Get speed of 5th ennemy
            query = "SELECT stat5, roster_skills.level  FROM roster " \
                    "JOIN players on players.allyCode=roster.allyCode "\
                    "LEFT JOIN roster_skills ON (roster_skills.roster_id=roster.id AND roster_skills.name='U2') " \
                    "WHERE players.name='"+opp_player_name.replace("'", "''")+"' "\
                    "AND guildName='"+opp_guild_name.replace("'", "''")+"' "\
                    "AND defId='"+fifth_unit_id+"' "
            goutils.log2("DBG", query)
            db_data = connect_mysql.get_line(query)
            if db_data == None:
                return 1, "Joueur "+opp_player_name+" inconnu, veuillez charger les infos la guilde adverse avant de lancer cette commande"

            fifth_unit_speed = int(db_data[0]/100000000)
            fifth_unit_U2level = db_data[1]
            if fifth_unit_speed > (my_Thrawn_speed-11):
                output_txt += "\nVitesse du 5e perso ("+fifth_unit_id+") de "+opp_player_name+" = "+str(fifth_unit_speed)+" ( >Thrawn-11)"
                output_txt += " > "+emoji_cross
                continue

            windu_u2_omi_tier = dict_capas["MACEWINDU"]["U2"]["omicronTier"]
            if fifth_unit_id == "MACEWINDU" and fifth_unit_U2level!=None and fifth_unit_U2level>=windu_u2_omi_tier:
                output_txt += "\n"+opp_player_name+" > "+emoji_frowning+" attention omicron Windu !"
                continue

            output_txt += "\n"+opp_player_name+" > "+emoji_check

        if count_opponent==0:
            output_txt += "Aucun adversaire détecté"
        return 0, output_txt
    else:
        return 1, "Counter inconnu: "+counter_type

async def print_guild_dtc(txt_allyCode, filter_txt, with_mentions=False):
    err_code, err_txt, dict_guild = await load_guild(txt_allyCode, True, True)
    if err_code != 0:
        return 1, 'ERR: guilde non trouvée pour code allié ' + txt_allyCode, None

    if with_mentions:
        #get list of allyCodes and player tags
        dict_players = connect_mysql.load_config_players()[0]
    else:
        # if this dict is empty, there will be no discord mention
        dict_players = {}

    dict_dtc = {}
    for member in dict_guild["member"]:
        player_id = member["playerId"]
        player_file = "PLAYERS/"+player_id+".json"
        player = json.load(open(player_file))
        player_name = player["name"]

        if not "datacron" in player:
            continue

        for dtcid in player["datacron"]:
            dtc=player["datacron"][dtcid]
            lvl6 = None
            lvl9 = None
            lvl12 = None
            lvl15 = None
            if not "affix" in dtc:
                continue

            if len(dtc["affix"]) < 6:
                # Not useful to display dtcs below lvl6
                continue
            abilityId = dtc["affix"][5]["abilityId"]
            ability_short = "_".join(abilityId.split("_")[2:])
            print(abilityId, ability_short)
            target_rule = dtc["affix"][5]["targetRule"][16:]
            lvl6 = ability_short+"("+target_rule+")"
            if len(dtc["affix"]) >= 9:
                abilityId = dtc["affix"][8]["abilityId"]
                ability_short = "_".join(abilityId.split("_")[2:])
                target_rule = dtc["affix"][8]["targetRule"][16:]
                lvl9 = ability_short+"("+target_rule+")"
            if len(dtc["affix"]) >= 12:
                abilityId = dtc["affix"][11]["abilityId"]
                ability_short = "_".join(abilityId.split("_")[2:])
                target_rule = dtc["affix"][11]["targetRule"][16:]
                lvl12 = ability_short+"("+target_rule+")"
            if len(dtc["affix"]) >= 15:
                abilityId = dtc["affix"][14]["abilityId"]
                ability_short = "_".join(abilityId.split("_")[2:])
                target_rule = dtc["affix"][14]["targetRule"][16:]
                lvl15 = ability_short+"("+target_rule+")"
            if "focused" in dtc["templateId"]:
                key_dtc = "LVL6="+lvl6+" / LVL9="+str(lvl9)+" / LVL12="+str(lvl12)+" / LVL15="+str(lvl15)
            else:
                key_dtc = "LVL6="+lvl6+" / LVL9="+str(lvl9)

            if not key_dtc in dict_dtc:
                dict_dtc[key_dtc] = []

            if player_name in dict_players:
                player_mention = dict_players[player_name][1]
            else:
                player_mention = player_name
            dict_dtc[key_dtc].append(player_mention)

    output_txt = ""

    for dtc in dict_dtc:
        if filter_txt != None:
            if filter_txt.lower() in dtc.lower():
                output_txt += dtc+":\n"+", ".join(dict_dtc[dtc])+"\n\n"
        else:
            output_txt += dtc+":\n"+", ".join(dict_dtc[dtc])+"\n\n"

    return 0, "", output_txt

async def get_previous_tw_defense(txt_allyCode, guild_id, command_schema):
    # get TW status to know if one is ongoing
    rpc_data = await connect_rpc.get_tw_status(guild_id, -1)
    tw_id = rpc_data["tw_id"]

    # Get TW defense orders
    dict_orders = {}
    for terr in rpc_data["homeGuild"]["list_territories"]:
        zone_shortId = terr[0]
        size = terr[1]
        filled = terr[2]
        cmdMsg = terr[5]
        if cmdMsg == None:
            cmdMsg = "<aucun ordre défini>"
        state = terr[6]
        if state=="IGNORED" or size==filled:
            dict_orders[zone_shortId] = emojis.prohibited+" "+cmdMsg
        else:
            dict_orders[zone_shortId] = "("+str(filled)+"/"+str(size)+") "+cmdMsg

    # Get player Id
    query = "SELECT playerId FROM players WHERE allyCode="+txt_allyCode
    goutils.log2("DBG", query)
    player_id = connect_mysql.get_value(query)
    if player_id == None:
        return 1, "Joueur inconnu"

    # Get list of previous TWs
    event_filenames = os.listdir("EVENTS/")
    event_tw_filenames = [x for x in event_filenames if x.startswith(guild_id+"_TERRITORY_WAR")]

    if tw_id!=None:
        event_prev_tw_filenames = [x for x in event_tw_filenames if not tw_id in x]

    # Get filename for latest TW
    event_previous_tw_filename = sorted(event_prev_tw_filenames, key=lambda x:x[-26:-12])[-1]

    # Read and extract defenses
    dict_unitsList = godata.get("unitsList_dict.json")
    dict_tw = godata.dict_tw
    dict_events = json.load(open("EVENTS/"+event_previous_tw_filename))
    deftw_cmd = ""
    for event_id in dict_events:
        event = dict_events[event_id]
        if event["authorId"] != player_id:
            continue
        activity = event["data"][0]["activity"]
        if not activity["zoneData"]["activityLogMessage"]["key"].endswith("_DEPLOY"):
            continue

        if activity["warSquad"]["playerId"] != player_id:
            if "eGBR" in event_id:
                goutils.log2("WAR", "warSquad player != event player for "+event_id)
            continue

        zoneId = activity["zoneData"]["zoneId"]
        zone_shortId = dict_tw[zoneId]

        list_units=""
        for cell in activity["warSquad"]["squad"]["cell"]:
            unitDefId = cell["unitDefId"].split(":")[0]
            unit_name = dict_unitsList[unitDefId]["name"].replace('"', '')
            list_units += '"'+unit_name+'" '
        deftw_cmd += command_schema.format(zone_shortId, list_units)
        deftw_cmd += "\n"+zone_shortId+": "+dict_orders[zone_shortId]+"\n--------------\n"

    return 0, deftw_cmd

def filter_tw_best_teams(tw_teams):
    dict_unitsList = godata.get("unitsList_dict.json")
    dict_rarity = godata.dict_rarity

    best_teams = {"ships": {"beaten": None, "remaining": None},
                  "chars": {"beaten": None, "remaining": None}}

    for [terr_prefixes, unit_type_txt] in [["TB", "chars"], ["F", "ships"]]:
        for [beaten, beaten_txt] in [[False, "remaining"], [True, "beaten"]]:
            terr_beaten_teams = [x for x in tw_teams if (x["zone_short_name"][0] in terr_prefixes and x["is_beaten"]==beaten)]
            #goutils.log2('DBG', "tw_teams="+str(tw_teams))
            #goutils.log2('DBG', "terr_beaten_teams="+str(terr_beaten_teams))
            if len(terr_beaten_teams) > 0:
                max_fights = max(terr_beaten_teams, key=lambda x: x["fights"])["fights"]
                goutils.log2('DBG', "max_fights="+str(max_fights))
                list_team_txt = []
                list_team_img = []

                # Report teams which managed at least 2 fails
                if (max_fights + int(not(beaten))) > 2:
                    best_terr_beaten_teams = [x for x in terr_beaten_teams if x["fights"]==max_fights]
                    goutils.log2('DBG', "best_terr_beaten_teams="+str(best_terr_beaten_teams))
                    for t in best_terr_beaten_teams:
                        # text description
                        player_name = t["player_name"]
                        team_gp = t["team_gp"]
                        list_unit_names = [dict_unitsList[x["unitId"]]["name"] for x in t["list_defId"]]
                        team_txt = player_name + " "
                        for u in list_unit_names:
                            team_txt += '"'+u.replace('"', '')+'" '
                        list_team_txt.append(team_txt)

                        # image
                        list_units = []
                        for tw_unit in t["list_defId"]:
                            unitDefId = tw_unit["unitDefId"]
                            txt_rarity = unitDefId.split(':')[1]
                            rarity = dict_rarity[txt_rarity]
                            unit = {"definitionId": tw_unit["unitDefId"],
                                    "currentRarity": rarity,
                                    "currentTier": tw_unit["gear"],
                                    "relic": {"currentTier": tw_unit["relic"]},
                                    "currentLevel": tw_unit["level"],
                                    "skill": []}
                            if "purchaseAbilityId" in tw_unit:
                                unit["purchaseAbilityId"] = tw_unit["purchaseAbilityId"]
                            if "skill" in tw_unit:
                                unit["skill"] = tw_unit["skill"]
                            list_units.append({"unit": unit, "crew": []})

                        team_img = portraits.get_image_from_units(list_units, player_name, 
                                                                  team_gp=team_gp,
                                                                  omicron_mode="TW")
                        list_team_img.append(team_img)

                best_teams[unit_type_txt][beaten_txt] = {"fights": max_fights,
                                                         "text":   list_team_txt,
                                                         "images": list_team_img}

    return best_teams

async def set_tb_targets(guild_id, tb_phase_target):
    dict_tb = godata.get("tb_definition.json")

    ec, et, tb_data = await connect_rpc.get_tb_status(guild_id, "", 0)
    if ec!=0:
        return 1, et

    dict_phase = tb_data["phase"]
    list_open_zones = tb_data["open_zones"]

    list_targets=[]
    for t in tb_phase_target:
        t_zone = t.split(':')[0]
        t_stars = t.split(':')[1]

        if not '-' in t_zone:
            # shortname (DS) instead of full (ROTE-DS)
            # > get the full name by looking at the open zones
            for oz in list_open_zones:
                oz_shortname = dict_tb[oz]["name"]
                if t_zone in oz_shortname:
                    t_zone = oz_shortname

        list_targets.append([t_zone, t_stars])

    goutils.log2("DBG", list_targets)
    err_code, err_txt = connect_gsheets.set_tb_targets(guild_id, list_targets)

    return err_code, err_txt

async def get_tw_summary(guild_id, allyCode=None, dict_guild=None, dict_events=None):
    err_code, err_txt, ret = await connect_rpc.get_guildLog_messages(guild_id, False, 1,
                                                                     allyCode=allyCode,
                                                                     dict_guild=dict_guild,
                                                                     dict_events=dict_events)

    if err_code!=0:
        return 1, err_txt, None

    tw_logs = ret["TW"][1]
    dict_guild = ret["rpc"]["guild"]

    return await get_tw_summary_from_logs(tw_logs, dict_guild)

async def get_tw_summary_from_logs(tw_logs, dict_guild):
    dict_tw_summary = {} # playerName:{"chars":{"fights":nn, "loss":nn, "partial":nn, "win":nn, "TM":nn},
                         #             "ships":{"loss":nn, "partial":nn, "win":nn, "TM":nn}}

    # Initialize with all TW participants
    dict_members = {}
    for member in dict_guild["member"]:
        dict_members[member["playerId"]] = member["playerName"]
    for member in dict_guild["territoryWarStatus"][0]["optedInMember"]:
        if member["memberId"] in dict_members:
            playerName = dict_members[member["memberId"]]
        else:
            playerName = "???"
        dict_tw_summary[playerName] = {"chars": {"fights":0, "loss":0, "partial":0, "win":0, "TM":0},
                                       "ships": {"fights":0, "loss":0, "partial":0, "win":0, "TM":0}}

    # Read events and fill the data
    for ts_log in tw_logs:
        log = ts_log[1]
        if "DEBUT" in log:
            re_txt = ".*DEBUT@([FTB])\d   : (.*) commence un combat contre .*"
            ret_re = re.search(re_txt, log)
            zonePrefix = ret_re.group(1)
            playerName = ret_re.group(2)

            if zonePrefix=="F":
                combat_type = "ships"
            else:
                combat_type = "chars"

            if not playerName in dict_tw_summary:
                dict_tw_summary[playerName] = {"chars": {"fights":0, "loss":0, "partial":0, "win":0, "TM":0},
                                               "ships": {"fights":0, "loss":0, "partial":0, "win":0, "TM":0}}
            dict_tw_summary[playerName][combat_type]["fights"] += 1
            dict_tw_summary[playerName]["ongoing"] = True

        elif "VICTOIRE" in log:
            re_txt = ".*VICTOIRE@([FTB])\d: (.*) a gagné contre .*"
            ret_re = re.search(re_txt, log)
            zonePrefix = ret_re.group(1)
            playerName = ret_re.group(2)

            if zonePrefix=="F":
                combat_type = "ships"
            else:
                combat_type = "chars"

            if not playerName in dict_tw_summary:
                dict_tw_summary[playerName] = {"chars": {"fights":0, "loss":0, "partial":0, "win":0, "TM":0},
                                               "ships": {"fights":0, "loss":0, "partial":0, "win":0, "TM":0}}
            if "ongoing" in dict_tw_summary[playerName]:
                del dict_tw_summary[playerName]["ongoing"]
            else:
                #The event for the start of the battle has been missed, fix it
                dict_tw_summary[playerName][combat_type]["fights"] += 1

            dict_tw_summary[playerName][combat_type]["win"] += 1

        elif "DEFAITE" in log:
            re_txt = ".*DEFAITE@([FTB])\d : (.*) a perdu contre .* \((abandon|(\d) morts)\)( >>> TM !!!)?"
            ret_re = re.search(re_txt, log)
            zonePrefix = ret_re.group(1)
            playerName = ret_re.group(2)
            deadCount = ret_re.group(4)
            if deadCount==0:
                # Cancel fight
                deadCount = 0
            is_tm = (ret_re.group(5) != None)

            if zonePrefix=="F":
                combat_type = "ships"
            else:
                combat_type = "chars"

            if not playerName in dict_tw_summary:
                dict_tw_summary[playerName] = {"chars": {"fights":0, "loss":0, "partial":0, "win":0, "TM":0},
                                               "ships": {"fights":0, "loss":0, "partial":0, "win":0, "TM":0}}
            if "ongoing" in dict_tw_summary[playerName]:
                del dict_tw_summary[playerName]["ongoing"]
            else:
                #The event for the start of the battle has been missed, fix it
                dict_tw_summary[playerName][combat_type]["fights"] += 1

            #Useless to count complete losses, as it is deduced from fight count afterwards
            if is_tm:
                dict_tw_summary[playerName][combat_type]["TM"] += 1
            else:
                dict_tw_summary[playerName][combat_type]["partial"] += 1

    # Due to some fights not counted as loss (airplane mode), need to deduce losses after
    for playerName in dict_tw_summary:
        if "ongoing" in dict_tw_summary[playerName]:
            del dict_tw_summary[playerName]["ongoing"]
        for combat_type in dict_tw_summary[playerName]:
            fights = dict_tw_summary[playerName][combat_type]["fights"]
            partial = dict_tw_summary[playerName][combat_type]["partial"]
            win = dict_tw_summary[playerName][combat_type]["win"]

            dict_tw_summary[playerName][combat_type]["loss"] = fights - partial - win

    return 0, "", dict_tw_summary

async def print_tw_summary(guild_id, allyCode=None, dict_guild=None, dict_events=None):
    err_code, err_txt, dict_tw_summary = await get_tw_summary(guild_id, allyCode=allyCode,
                                                              dict_guild=dict_guild,
                                                              dict_events=dict_events)
    if err_code!=0:
        return 1, err_txt

    summary_list = []
    for k in dict_tw_summary:
        #print(k, dict_tw_summary[k])
        player = k
        tm = dict_tw_summary[k]["chars"]["TM"] + dict_tw_summary[k]["ships"]["TM"]
        wins = dict_tw_summary[k]["chars"]["win"] + dict_tw_summary[k]["ships"]["win"]
        ground_fights = dict_tw_summary[k]["chars"]["fights"]
        ship_fights = dict_tw_summary[k]["ships"]["fights"]
        if ground_fights+ship_fights>0:
            fails = dict_tw_summary[k]["chars"]["loss"] \
                  + dict_tw_summary[k]["chars"]["partial"] \
                  + dict_tw_summary[k]["ships"]["loss"] \
                  + dict_tw_summary[k]["ships"]["partial"]
            fail_rate_percent = round(100*fails/(ground_fights+ship_fights), 1)
            fail_txt = str(fails)+" ("+str(fail_rate_percent)+"%)"
        else:
            fail_txt = "--"

        line = [player, tm, wins, ground_fights, ship_fights, fail_txt]
        summary_list.append(line)

    summary_list.sort(key=lambda x:(-x[3], -x[4], -x[2], x[0].lower()))
    summary_list = [["Player", "TM", "Wins", "Ground\nfights", "Ship\nfights", "Fails"]] + summary_list
    t = Texttable()
    t.add_rows(summary_list)
    t.set_deco(Texttable.BORDER|Texttable.HEADER|Texttable.VLINES)

    return 0, t.draw()

#########################################
# Display strike / wave statistics for the whole TB or a round
# May be manually launched, or automatic for the end of the TB
#########################################
async def print_tb_strike_stats(guild_id, list_allyCodes, tb_rounds, allyCode=None):
    # Get current guild and mapstats data
    err_code, err_txt, rpc_data = await connect_rpc.get_guild_rpc_data(guild_id, None, 1, allyCode=allyCode)
    if err_code!=0:
        return 1, err_txt, None

    guild = rpc_data[0]
    current_mapstats = rpc_data[1]
    if not "territoryBattleStatus" in guild:
        # TB has ended, check latest results
        max_endTime=0
        for tbr in guild["territoryBattleResult"]:
            if int(tbr["endTime"]) > max_endTime:
                max_endTime = int(tbr["endTime"])
                tb_id = tbr["instanceId"]
                tb_type = tb_id.split(":")[0]
                current_mapstats = tbr["finalStat"]
    else:
        tb_id = guild["territoryBattleStatus"][0]["instanceId"]
        tb_type = tb_id.split(":")[0]

    # Get previous TB mapstats
    stored_events = os.listdir("EVENTS/")
    filename_begin = guild_id+"_"+tb_type
    stored_guild_mapstats = [x for x in stored_events if x.startswith(filename_begin) 
                                                         and x.endswith("_mapstats.json")
                                                         and not tb_id in x]
    if len(stored_guild_mapstats)==0:
        previous_mapstats = {}
    else:
        prev_mapstats_file = sorted(stored_guild_mapstats, 
                                    key=lambda x: x.split(":")[1].split("_")[0])[-1]
        try:
            previous_mapstats = json.load(open("EVENTS/"+prev_mapstats_file))
        except json.decoder.JSONDecodeError as e:
            previous_mapstats = {}

    # Get member list id/name
    dict_members = {}
    if "guild" in guild:
        guild=guild["guild"]
    for m in guild["member"]:
        dict_members[m["playerId"]] = {'name': m["playerName"],
                                       'gp': int(m["galacticPower"])}

    if len(list_allyCodes)>0:
        query = "SELECT allyCode, name FROM players WHERE guildId='"+guild_id+"'"
        db_data = connect_mysql.get_table(query)

        filtered_memberNames = []
        for line in db_data:
            if str(line[0]) in list_allyCodes:
                filtered_memberNames.append(line[1])
    else:
        filtered_memberNames = []

    # Create stats for current TB
    dict_stats = {}
    if "currentStat" in current_mapstats:
        current_mapstats=current_mapstats["currentStat"]

    for tb_round in ["all", "1", "2", "3", "4", "5", "6"]:
        if tb_round=="all":
            encounter_id = "strike_encounter"
            attempt_id = "strike_attempt"
            score_id = "summary"
        else:
            encounter_id = "strike_encounter_round_"+tb_round
            attempt_id = "strike_attempt_round_"+tb_round
            score_id = "summary_round_"+tb_round

        for [tag, mapstats] in [["current", current_mapstats], ["previous", previous_mapstats]]:
            for ms in mapstats:
                if ms["mapStatId"] in [encounter_id, attempt_id, score_id]:
                    if not "playerStat" in ms:
                        continue
                    for p in ms["playerStat"]:
                        if p["memberId"] in dict_members:
                            p_name = dict_members[p["memberId"]]['name']
                            p_gp = dict_members[p["memberId"]]['gp']
                        else:
                            continue
                        if not p_name in dict_stats:
                            dict_stats[p_name] = {"current": {}, "previous": {}, "gp": p_gp}
                        dict_stats[p_name][tag][ms["mapStatId"]] = int(p["score"])

    list_stats = []
    list_colors = []
    for p in sorted(dict_stats):
        if len(filtered_memberNames)>0 and not p in filtered_memberNames:
            continue
        if len(tb_rounds)==0:
            if len(filtered_memberNames)>0:
                # if individual players are required, then display all phases
                list_display_rounds = ["all", "1", "2", "3", "4", "5", "6"]
            else:
                list_display_rounds = ["all"]
        else:
            list_display_rounds = tb_rounds

        for tb_round in list_display_rounds:
            if tb_round=="all":
                encounter_id = "strike_encounter"
                attempt_id = "strike_attempt"
                score_id = "summary"
            else:
                encounter_id = "strike_encounter_round_"+tb_round
                attempt_id = "strike_attempt_round_"+tb_round
                score_id = "summary_round_"+tb_round

            cur_strikes = 0
            if attempt_id in dict_stats[p]["current"]:
                cur_strikes = dict_stats[p]["current"][attempt_id]

            cur_waves = 0
            if encounter_id in dict_stats[p]["current"]:
                cur_waves = dict_stats[p]["current"][encounter_id]

            cur_score = 0
            if score_id in dict_stats[p]["current"]:
                cur_score = dict_stats[p]["current"][score_id]

            prev_strikes = 0
            if attempt_id in dict_stats[p]["previous"]:
                prev_strikes = dict_stats[p]["previous"][attempt_id]

            prev_waves = 0
            if encounter_id in dict_stats[p]["previous"]:
                prev_waves = dict_stats[p]["previous"][encounter_id]

            prev_score = 0
            if score_id in dict_stats[p]["previous"]:
                prev_score = dict_stats[p]["previous"][score_id]

            #Compare with previous TB and give a quality score
            round_quality = 0
            if prev_strikes == 0:
                percent_strikes = " --"
            else:
                ratio_strikes = (cur_strikes-prev_strikes)/prev_strikes
                percent_strikes = str(int(100*ratio_strikes))+"%"
                if percent_strikes == "0%":
                    percent_strikes = " 0%"
                elif ratio_strikes>0:
                    percent_strikes = "+"+percent_strikes

                if ratio_strikes>0.5:
                    round_quality+=2
                elif ratio_strikes>0.25:
                    round_quality+=1
                elif ratio_strikes<-0.5:
                    round_quality-=2
                elif ratio_strikes<-0.25:
                    round_quality-=1

            if prev_waves == 0:
                percent_waves = " --"
            else:
                ratio_waves = (cur_waves-prev_waves)/prev_waves
                percent_waves = str(int(100*ratio_waves))+"%"
                if percent_waves == "0%":
                    percent_waves = " 0%"
                elif ratio_waves>0:
                    percent_waves = "+"+percent_waves

                if ratio_waves>0.5:
                    round_quality+=2
                elif ratio_waves>0.25:
                    round_quality+=1
                elif ratio_waves<-0.5:
                    round_quality-=2
                elif ratio_waves<-0.25:
                    round_quality-=1
                    
            ratio_score = round(cur_score/dict_stats[p]["gp"], 1)
            short_score = round(cur_score/1000000, 1)

            if len(previous_mapstats) > 0:
                line_stats = [tb_round, p, str(cur_strikes).rjust(3)+" ("+percent_strikes+")",
                                 str(cur_waves).rjust(3)+" ("+percent_waves+")",
                                 str(short_score).rjust(5)+"M ("+str(ratio_score)+")"]

            else:
                line_stats = [tb_round, p, str(cur_strikes).rjust(3),
                                 str(cur_waves).rjust(3),
                                 str(short_score).rjust(5)+"M ("+str(ratio_score)+")"]
                list_colors.append("black")

            list_stats.append(line_stats)
            if cur_strikes==0:
                list_colors.append("red")
            elif round_quality<-3:
                list_colors.append("red")
            elif round_quality<-1:
                list_colors.append("orange")
            elif round_quality>3:
                list_colors.append("green")
            else:
                list_colors.append("black")

    ec, txt = goutils.dict_to_csv(dict_stats, "player")
    if ec == 0:
        csv_content = txt
    else:
        return ec, txt, None

    list_stats = [["Round", "Joueur", "Combats", "Vagues réussies", "Score"],
                  ["", "", "(progrès)", "(progrès)", "(ratio /PG)"]] + list_stats
    list_colors = ["black", "black"] + list_colors

    t = Texttable(0)
    t.add_rows(list_stats)
    t.set_deco(0)
    ec, et, image = portraits.get_image_from_texttable(t.draw(), list_colors)

    return 0, csv_content, image

#########################################
# Display points statistics by phase for the whole TB or a round
# May be manually lauched, or automatic for the end of the TB
#########################################
async def print_tb_stats(guild_id, round=None, allyCode=None):
    dict_tb = godata.get("tb_definition.json")

    # Get current guild and mapstats data
    err_code, err_txt, rpc_data = await connect_rpc.get_guild_rpc_data(guild_id, ["TB"], 0, allyCode=allyCode)
    if err_code!=0:
        return 1, err_txt

    guild = rpc_data[0]
    if not "territoryBattleStatus" in guild:
        # TB has ended, get events from file
        max_endTime=0
        for tbr in guild["territoryBattleResult"]:
            if int(tbr["endTime"]) > max_endTime:
                max_endTime = int(tbr["endTime"])
                tb_id = tbr["instanceId"]
                tb_defId = tbr["definitionId"]
                cur_events_file = guild_id+"_"+tb_id+"_events.json"
                current_events = json.load(open("EVENTS/"+cur_events_file))
    else:
        tb_id = guild["territoryBattleStatus"][0]["instanceId"]
        tb_defId = guild["territoryBattleStatus"][0]["definitionId"]
        current_events = rpc_data[2][tb_id]

    tb_type = tb_id.split(":")[0]
    current_startTime = int(tb_id.split(':')[1][1:])
    maxRounds = dict_tb[tb_defId]["maxRound"]

    # Get previous TB events
    stored_events = os.listdir("EVENTS/")
    filename_begin = guild_id+"_"+tb_type
    stored_guild_events = [x for x in stored_events if x.startswith(filename_begin) 
                                                         and x.endswith("_events.json")
                                                         and not tb_id in x]
    if len(stored_guild_events)==0:
        previous_events = {}
    else:
        prev_events_file = sorted(stored_guild_events, 
                                  key=lambda x: x.split(":")[1].split("_")[0])[-1]
        prev_startTime = int(prev_events_file.split(':')[1].split('_')[0][1:])
        previous_events = json.load(open("EVENTS/"+prev_events_file))

    # Create stats for current TB
    dict_results = {}
    for [tag, events, startTime] in [["current", current_events, current_startTime], ["previous", previous_events, prev_startTime]]:
        for eid in events:
            e=events[eid]
            if guild_id in e["channelId"]:
                ts = int(e["timestamp"])
                phase = int ((ts-startTime) / (86400000*6/maxRounds)) + 1
                if not phase in dict_results:
                    dict_results[phase]={"current":  {"deployment":0, "platoons":0,
                                                      "fights":0, "openZones":[]},
                                         "previous": {"deployment":0, "platoons":0,
                                                      "fights":0, "openZones":[]}}
                if "data" in e:
                    data=e["data"][0]
                    if "activity" in data:
                        activity=data["activity"]
                        if "zoneData" in activity:
                            zoneData=activity["zoneData"]
                            zoneId=zoneData["zoneId"]
                            if not zoneId in dict_results[phase][tag]["openZones"]:
                                dict_results[phase][tag]["openZones"].append(zoneId)
                                
                            if "CONFLICT_CONTRIBUTION" in zoneData["activityLogMessage"]["key"]:
                                score = int(zoneData["activityLogMessage"]["param"][0]["paramValue"][0])
                                dict_results[phase][tag]["fights"] += score
                            elif "DEPLOY" in zoneData["activityLogMessage"]["key"]:
                                score = int(zoneData["activityLogMessage"]["param"][0]["paramValue"][0])
                                dict_results[phase][tag]["deployment"] += score
                            elif "RECON_CONTRIBUTION" in zoneData["activityLogMessage"]["key"]:
                                score = int(zoneData["activityLogMessage"]["param"][0]["paramValue"][0])
                                dict_results[phase][tag]["platoons"] += score

    for i in dict_results:
        for j in dict_results[i]:
            print(i,j,dict_results[i][j])

    list_stats = []
    for p in dict_results:
        cur_deployment = dict_results[p]["current"]["deployment"]
        cur_platoons = dict_results[p]["current"]["platoons"]
        cur_fights = dict_results[p]["current"]["fights"]
        cur_openZones = sorted(dict_results[p]["current"]["openZones"])

        prev_deployment = dict_results[p]["previous"]["deployment"]
        prev_platoons = dict_results[p]["previous"]["platoons"]
        prev_fights = dict_results[p]["previous"]["fights"]
        prev_openZones = sorted(dict_results[p]["previous"]["openZones"])

        if prev_deployment == 0:
            percent_deployment = " --"
        else:
            ratio_deployment = (cur_deployment-prev_deployment)/prev_deployment
            percent_deployment = str(int(100*ratio_deployment))+"%"
            if percent_deployment == "0%":
                percent_deployment = " 0%"
            elif ratio_deployment>0:
                percent_deployment = "+"+percent_deployment

        if prev_platoons == 0:
            percent_platoons = " --"
        else:
            ratio_platoons = (cur_platoons-prev_platoons)/prev_platoons
            percent_platoons = str(int(100*ratio_platoons))+"%"
            if percent_platoons == "0%":
                percent_platoons = " 0%"
            elif ratio_platoons>0:
                percent_platoons = "+"+percent_platoons

        if prev_fights == 0:
            percent_fights = " --"
        else:
            ratio_fights = (cur_fights-prev_fights)/prev_fights
            percent_fights = str(int(100*ratio_fights))+"%"
            if percent_fights == "0%":
                percent_fights = " 0%"
            elif ratio_fights>0:
                percent_fights = "+"+percent_fights

        if cur_openZones != prev_openZones:
            zone_check = "Zones différentes !"
        else:
            zone_check = ""

        line_stats = [p, str(cur_deployment).rjust(3)+" ("+str(prev_deployment).rjust(3)+", "+percent_deployment+")",
                         str(cur_platoons).rjust(3)+" ("+str(prev_platoons).rjust(3)+", "+percent_platoons+")",
                         str(cur_fights).rjust(3)+" ("+str(prev_fights).rjust(3)+", "+percent_fights+")",
                         zone_check]

        list_stats.append(line_stats)

    list_stats = [["Phase", "Déploiements", "Pelotons", "Combats", ""]] + list_stats
    t = Texttable()
    t.add_rows(list_stats)
    t.set_deco(Texttable.BORDER|Texttable.HEADER|Texttable.VLINES)

    return 0, t.draw()

# Details about special missions in TB
async def print_tb_special_results(guild_id, zone_shortname, allyCode=None):
    dict_tb = godata.get("tb_definition.json")

    #zone name check not useful now, yet important to check before 
    #  launching long operation like get_tb_status
    zone_name = None
    for x in dict_tb:
        x_item = dict_tb[x]
        if "name" in x_item and x_item["name"]==zone_shortname:
            zone_name = x
            break

    if zone_name==None:
        return 1, "Zone inconnue: "+zone_shortname, None

    #Get TB data
    ec, et, tb_data = await connect_rpc.get_tb_status(guild_id, "", 0, allyCode=allyCode)
    if ec!=0:
        return 1, et, None

    guild = tb_data["guild"]
    mapstats = tb_data["mapstats"]

    return await print_tb_special_results_from_rpc(guild, mapstats, zone_shortname)

async def print_tb_special_results_from_rpc(guild, mapstats, zone_shortname, dict_ready_players={}):
    dict_tb = godata.get("tb_definition.json")

    zone_name = None
    for x in dict_tb:
        x_item = dict_tb[x]
        if "name" in x_item and x_item["name"]==zone_shortname:
            zone_name = x
            break

    if zone_name==None:
        return 1, "Zone inconnue: "+zone_shortname, None

    tb = guild["territoryBattleStatus"][0]
    list_covert_zones = [x["zoneStatus"]["zoneId"] for x in tb["covertZoneStatus"] if x["zoneStatus"]["zoneId"].startswith(zone_name)]

    dict_members = {}
    for m in guild["member"]:
        dict_members[m["playerId"]] = m["playerName"]

    dict_coverts = {}
    for mapstat in mapstats:
        mapStatId = mapstat["mapStatId"]
        if mapStatId.startswith("covert_round_attempted_mission") and zone_name in mapStatId:
            if not "playerStat" in mapstat:
                # Round not yet played
                continue
            covert_name = zone_name + "_" + mapStatId.split("_")[-1]
            for m in mapstat["playerStat"]:
                mid = m["memberId"]
                pname = dict_members[mid]
                if not covert_name in dict_coverts:
                    dict_coverts[covert_name] = {}
                if not pname in dict_coverts[covert_name]:
                    dict_coverts[covert_name][pname] = {}
                dict_coverts[covert_name][pname]["round"] = m["score"]

        elif mapStatId.startswith("covert_complete_mission") and zone_name in mapStatId:
            if not "playerStat" in mapstat:
                # Round not yet played
                continue
            covert_name = zone_name + "_" + mapStatId.split("_")[-1]
            for m in mapstat["playerStat"]:
                mid = m["memberId"]
                pname = dict_members[mid]
                if not covert_name in dict_coverts:
                    dict_coverts[covert_name] = {}
                if not pname in dict_coverts[covert_name]:
                    dict_coverts[covert_name][pname] = {}
                dict_coverts[covert_name][pname]["score"] = m["score"]

    line_colors = []
    output_txt = "**Missions spéciales pour "+zone_shortname+"**"
    line_colors.append("black")
    if len(list_covert_zones)!=0:
        for c in sorted(list_covert_zones):
            #TODO make it configurable with tb_definition.json
            if c == "tb3_mixed_phase02_conflict01_covert01" and not c in dict_ready_players:
                # Bracca > Zeffo
                query = "SELECT name FROM ( "\
                        "    SELECT players.name, "\
                        "    GROUP_CONCAT(CASE WHEN defId='CEREJUNDA' THEN relic_currentTier ELSE NULL END) AS `CEREJUNDA`, "\
                        "    GROUP_CONCAT(CASE WHEN defId='JEDIKNIGHTCAL' THEN relic_currentTier ELSE NULL END) AS `JEDIKNIGHTCAL`, "\
                        "    GROUP_CONCAT(CASE WHEN defId='CALKESTIS' THEN relic_currentTier ELSE NULL END) AS `CALKESTIS` "\
                        "    FROM players "\
                        "    JOIN roster ON (players.allyCode=roster.allyCode AND defId IN ('CEREJUNDA', 'JEDIKNIGHTCAL', 'CALKESTIS')) "\
                        "    WHERE guildId='"+guild['profile']['id']+"' "\
                        "    GROUP BY players.allyCode "\
                        ") T "\
                        "WHERE CEREJUNDA>=9 AND (JEDIKNIGHTCAL>=9 OR CALKESTIS>=9) "
                goutils.log2("DBG", query)
                ready_players = connect_mysql.get_column(query)
                if ready_players == None:
                    ready_players = []

            elif c == "tb3_mixed_phase03_conflict03_covert02" and not c in dict_ready_players:
                # > Mandalore
                query = "SELECT name FROM ( "\
                        "    SELECT players.name, "\
                        "    GROUP_CONCAT(CASE WHEN defId='MANDALORBOKATAN' THEN relic_currentTier ELSE NULL END) AS `MANDALORBOKATAN`, "\
                        "    GROUP_CONCAT(CASE WHEN defId='THEMANDALORIANBESKARARMOR' THEN relic_currentTier ELSE NULL END) AS `THEMANDALORIANBESKARARMOR` "\
                        "    FROM players "\
                        "    JOIN roster ON (players.allyCode=roster.allyCode AND defId IN ('MANDALORBOKATAN', 'THEMANDALORIANBESKARARMOR')) "\
                        "    WHERE guildId='"+guild['profile']['id']+"' "\
                        "    GROUP BY players.allyCode "\
                        ") T "\
                        "WHERE MANDALORBOKATAN>=9 AND THEMANDALORIANBESKARARMOR>=9 "
                goutils.log2("DBG", query)
                ready_players = connect_mysql.get_column(query)
                if ready_players == None:
                    ready_players = []

            elif c == "tb3_mixed_phase03_conflict03_covert01" and not c in dict_ready_players:
                # Reva
                tagAlias = godata.get('tagAlias_dict.json')
                dict_unitsList = godata.get("unitsList_dict.json")
                list_ids = [x for x in tagAlias["Inquisitorius"] if dict_unitsList[x]['combatType']==1 and x!='GRANDINQUISITOR']
                query = "SELECT players.name FROM players "\
                        "JOIN ("\
                        "    SELECT name "\
                        "    FROM players "\
                        "    JOIN roster ON (players.allyCode=roster.allyCode AND defId IN "+str(tuple(list_ids))+" "\
                        "                    AND relic_currentTier>=9) "\
                        "    WHERE guildId='"+guild['profile']['id']+"' "\
                        "    GROUP BY players.allyCode "\
                        "    HAVING COUNT(defId) >= 4 "\
                        ") T ON T.name=players.name "\
                        "JOIN roster ON (players.allyCode=roster.allyCode AND defId ='GRANDINQUISITOR' "\
                        "                AND relic_currentTier>=9) "\
                        "WHERE guildId='"+guild['profile']['id']+"' "
                goutils.log2("DBG", query)
                ready_players = connect_mysql.get_column(query)
                if ready_players == None:
                    ready_players = []

            elif c == "tb3_mixed_phase03_conflict01_bonus_covert01" and not c in dict_ready_players:
                # Clones sur Mandalore
                tagAlias = godata.get('tagAlias_dict.json')
                dict_unitsList = godata.get("unitsList_dict.json")
                list_ids = [x for x in tagAlias["Soldat clone"] if dict_unitsList[x]['combatType']==1]
                query = "SELECT players.name FROM players "\
                        "JOIN roster ON (players.allyCode=roster.allyCode AND defId IN "+str(tuple(list_ids))+" "\
                        "                AND relic_currentTier>=9) "\
                        "WHERE guildId='"+guild['profile']['id']+"' "\
                        "GROUP BY players.allyCode "\
                        "HAVING COUNT(defId) >= 5 "
                goutils.log2("DBG", query)
                ready_players = connect_mysql.get_column(query)
                if ready_players == None:
                    ready_players = []
            elif c in dict_ready_players:
                ready_players = dict_ready_players[c]
            else:
                ready_players = None

            output_txt += "\nMission "+c[-1]
            line_colors.append("black")
            success = 0
            if not c in dict_coverts:
                dict_coverts[c] = {}
            for p in sorted(list(dict_coverts[c].keys())):
                output_txt += "\n  "+p+" (round "+dict_coverts[c][p]["round"]+")"
                if "score" in dict_coverts[c][p] and dict_coverts[c][p]["score"]=="1":
                    output_txt += " > OK !"
                    success+=1
                    line_colors.append("green")
                else:
                    output_txt += " > échec"
                    line_colors.append("red")
            if ready_players != None:
                for p in sorted(ready_players):
                    if not p in dict_coverts[c].keys():
                        output_txt += "\n  "+p+" > pas joué"
                        line_colors.append("gray")
            else:
                output_txt += "\n  *** les joueurs ready ne sont pas affichés pour ce combat"
                line_colors.append("black")
            output_txt += "\n  >> "+str(success)+"/"+str(len(dict_coverts[c]))
            if ready_players != None:
                output_txt += " et reste "+str(len(ready_players)-len(dict_coverts[c]))
            line_colors.append("black")

        ec, et, image = portraits.get_image_from_texttable(output_txt, line_colors)
    else:
        output_txt += "\n aucune mission spéciale dans cette zone"
        line_colors.append("black")
        image = None

    return 0, output_txt, image

async def register_confirm(txt_allyCode, discord_id):
    dict_unitsList = godata.get("unitsList_dict.json")
    dict_modList = godata.get("modList_dict.json")
    dict_shape_by_slot = {2: "carré",
                          3: "flèche",
                          4: "losange",
                          5: "triangle",
                          6: "rond",
                          7: "croix"}


    e, t, dict_player = await load_player(txt_allyCode, 1, False)
    if e != 0:
        return 1, 'ERR: joueur non trouvé pour code allié ' + txt_allyCode
    
    #Check if confirmation already ongoing
    query = "SELECT timestampdiff(SECOND, timestamp, CURRENT_TIMESTAMP), defId, mod_slot "\
            "FROM register_confirm WHERE allyCode="+txt_allyCode
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_line(query)

    if db_data == None:
        # Nothing ongoing, prepare confirmation protocole
        dict_player = goutils.roster_from_dict_to_list(dict_player)
        sixmod_roster = [u for u in dict_player['rosterUnit']
                         if len(u['equippedStatMod'])==6]
        lower_6units = sorted(sixmod_roster, key=lambda x:x['gp'])[:6]
        unit_ids = [u['definitionId'] for u in lower_6units]
        defId = random.choice(unit_ids).split(':')[0]
        slot = random.choice([2, 3, 4, 5, 6, 7])

        #store challenge in DB
        query = "INSERT INTO register_confirm(allyCode, defId, mod_slot) "\
                "VALUES("+txt_allyCode+", '"+defId+"', "+str(slot)+")"
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

        #Return message to user
        return 2, "Début du protocole de confirmation. Vous avez 5 minutes pour **enlever le mod "+dict_shape_by_slot[slot]+"** sur **"+dict_unitsList[defId]["name"]+"** et uniquement celui-là. Puis relancez la commande à l'identique."

    else:
        # Challenge already defined, need to check if user has complied
        delta_ts = db_data[0]
        defId = db_data[1]
        slot = db_data[2]

        #Whatever the outcome (sucessful or not, the challenge is deleted)
        query = "DELETE FROM register_confirm WHERE allyCode="+txt_allyCode
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)
        
        #Check duration
        if delta_ts>300:
            return 1, "Vous avez mis trop de temps à répondre, veuillez reprendre à zéro en relançant la commande à l'identique."

        unit_mods = dict_player['rosterUnit'][defId]['equippedStatMod']
        mods_ok = [None, None, False, False, False, False, False, False] #index 0 and 1 not used
        mods_ok[slot] = True
        for mod in unit_mods:
            mod_defId = mod['definitionId']
            mod_slot = dict_modList[mod_defId]['slot']
            if mod_slot == slot:
                mods_ok[mod_slot] = False
            else:
                mods_ok[mod_slot] = True

        sum_ok = sum(mods_ok[2:])
        if sum_ok==6:
            #challenge OK
            query = "UPDATE player_discord SET confirmed=1 WHERE allyCode="+txt_allyCode
            goutils.log2("DBG", query)
            connect_mysql.simple_execute(query)

            return 0, "Vous avez été confirmé comme propriétaire du compte "+txt_allyCode+" (n'oubliez pas de remettre le mod enlevé)."
        else:
            #challenge NOK
            return 1, "Vous n'avez pas rempli les conditions demandées, veuillez reprendre à zéro en relançant la commande à l'identique."

#######################################
async def update_tw_from_guild(dict_guild):
    guild_id = dict_guild["profile"]["id"]
    tw = dict_guild["territoryWarStatus"][0]
    opp_guild_id = tw["awayGuild"]["profile"]["id"]
    opp_guild_name = tw["awayGuild"]["profile"]["name"]
    score = sum([int(x['zoneStatus']['score']) \
                 for x in tw['homeGuild']['conflictStatus']])
    opp_score = sum([int(x['zoneStatus']['score']) \
                     for x in tw['awayGuild']['conflictStatus']])

    ret_dict = await connect_rpc.get_tw_status(guild_id, 0, dict_guild=dict_guild)

    tw_id = ret_dict["tw_id"]
    homeGuild = ret_dict["homeGuild"]
    awayGuild = ret_dict["awayGuild"]

    await connect_mysql.update_tw(guild_id, tw_id, opp_guild_id,
              opp_guild_name, score, opp_score,
              homeGuild, awayGuild)

