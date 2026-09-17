import os
import config
import sys
from urllib.parse import uses_netloc, urlparse
import datetime
import time
from wcwidth import wcswidth
import asyncio
from decimal import Decimal
from hashlib import md5
from json import dumps as json_dumps

import goutils
import data
from connect_mysql import get_value_async, get_line_async, get_column_async, get_table_async, simple_execute_async

##############################################################
# Function: load_config_players
# Parameters: optional guild_id to filter players
# Output:  dict_players_by_IG {key=IG name, value=[allycode, <@id>, isOfficer, guild_id]}
#          dict_players_by_ID {key=discord ID, value={"main":[allycode, isOfficer, guild_id]
#                                                     "alts":[[ac, isOff, guild_id], [ac2, isOff, guild_id]...]}}
##############################################################
async def load_config_players(guild_id=None):
    query = "SELECT players.allyCode, players.name, player_discord.discord_id, "\
            "player_discord.main, guildMemberLevel, guildId "\
            "FROM players "\
            "JOIN player_discord ON player_discord.allyCode=players.allyCode "
    if guild_id!=None:
        query+= "WHERE guildId='"+guild_id+"' "
    query+= "ORDER BY player_discord.discord_id, player_discord.main "
    goutils.log2("DBG", query)
    data_db = await get_table_async(query)

    dict_players_by_IG = {}
    dict_players_by_ID = {}

    if data_db != None:
        list_did = [x[2] for x in data_db]
        for line in data_db:
            ac = line[0]
            name = line[1]
            did = line[2]
            isMain = line[3]
            isOff = (line[4]!=2)
            guild_id = line[5]

            # dict_players_by_IG
            dict_players_by_IG[name] = [ac, name]
            if list_did.count(did) == 1:
                dict_players_by_IG[name] = [ac, "<@"+str(did)+">", isOff, guild_id]
            else:
                dict_players_by_IG[name] = [ac, "<@"+str(did)+"> ["+name+"]", isOff, guild_id]

            # dict_players_by_ID
            if not did in dict_players_by_ID:
                dict_players_by_ID[did] = {"main": None, "alts": []}
                
            if isMain:
                dict_players_by_ID[did]["main"] = [ac, isOff, guild_id]
            else:
                dict_players_by_ID[did]["alts"].append([ac, isOff, guild_id])

    return dict_players_by_IG, dict_players_by_ID


########################################
# Get guild ID, allyCode and player name for the
#  warbot linked to this discord server
########################################
async def get_warbot_info(server_id, channel_id):
    goutils.log2("DBG", "looking for bot_infos from server ID...")
    query = "SELECT guild_bots.guild_id, guild_bots.allyCode, players.name, "\
            "tbChanRead_id, tbChanOut_id, tbRoleOut, "\
            "twFulldefDetection, "\
            "guilds.name, gfile_name, echostation_id, "\
            "tbFightEstimationType "\
            "FROM guild_bots "\
            "JOIN guild_bot_infos ON guild_bots.guild_id=guild_bot_infos.guild_id "\
            "JOIN players ON players.allyCode=guild_bots.allyCode "\
            "JOIN guilds ON guilds.id=guild_bots.guild_id "\
            "WHERE server_id="+str(server_id)
    goutils.log2("DBG", query)
    db_data = await get_line_async(query)

    if db_data == None:
        if channel_id != None:
            #no warbot found from server, try it from the channel as test channel
            goutils.log2("DBG", "looking for bot_infos from guild channel ID...")
            query = "SELECT guild_bots.guild_id, guild_bots.allyCode, players.name, "\
                    "tbChanRead_id, tbChanOut_id, tbRoleOut, "\
                    "twFulldefDetection, "\
                    "guilds.name, gfile_name, echostation_id, "\
                    "tbFightEstimationType "\
                    "FROM guild_bots "\
                    "JOIN guild_bot_infos ON guild_bots.guild_id=guild_bot_infos.guild_id "\
                    "JOIN players ON players.allyCode=guild_bots.allyCode "\
                    "JOIN guilds ON guilds.id=guild_bots.guild_id "\
                    "JOIN guild_test_channels ON guild_test_channels.guild_id=guild_bots.guild_id "\
                    "WHERE channel_id="+str(channel_id)
            goutils.log2("DBG", query)
            db_data = await get_line_async(query)

            if db_data == None:
                #no warbot found as test channel, try it from connected user
                goutils.log2("DBG", "looking for bot_infos from user channel ID...")
                query = "SELECT guildId, players.allyCode, players.name, "\
                        "tbChanRead_id, tbChanOut_id, tbRoleOut, "\
                        "twFulldefDetection, "\
                        "guilds.name, gfile_name, echostation_id, "\
                        "tbFightEstimationType "\
                        "FROM user_bot_infos "\
                        "JOIN players ON user_bot_infos.allyCode=players.allyCode "\
                        "JOIN guilds ON guilds.id=players.guildId "\
                        "LEFT JOIN guild_bot_infos ON players.guildId=guild_bot_infos.guild_id "\
                        "WHERE channel_id="+str(channel_id)
                goutils.log2("DBG", query)
                db_data = await get_line_async(query)

                if db_data == None:
                    return 1, "Pas de warbot trouvé, ni pour ce serveur, ni pour ce channel", None
        else:
            return 1, "Pas de warbot trouvé pour ce serveur", None
    
    return 0, "", {"guild_id": db_data[0],
                   "allyCode": str(db_data[1]),
                   "player_name": db_data[2],
                   "tbChanRead_id": db_data[3],
                   "tbChanOut_id": db_data[4],
                   "tbRoleOut": db_data[5],
                   "twFulldefDetection": db_data[6],
                   "guild_name": db_data[7],
                   "gfile_name": db_data[8],
                   "echostation_id": db_data[9],
                   "tbFightEstimationType": db_data[10]}

async def get_warbot_info_from_guild(guild_id):
    query = "SELECT guild_bots.guild_id, guild_bots.allyCode, players.name, "\
            "tbChanRead_id, tbChanOut_id, tbRoleOut, "\
            "twFulldefDetection, "\
            "guilds.name, server_id, gfile_name, discord_id "\
            "FROM guild_bots "\
            "JOIN guild_bot_infos ON guild_bots.guild_id=guild_bot_infos.guild_id "\
            "JOIN players ON players.allyCode=guild_bots.allyCode "\
            "JOIN guilds ON guilds.id=guild_bots.guild_id "\
            "LEFT JOIN player_discord ON player_discord.allyCode=guild_bots.allyCode "\
            "WHERE guild_bots.guild_id='"+guild_id+"'"
    goutils.log2("DBG", query)
    db_data = await get_line_async(query)

    if db_data == None:
        return 1, "Pas de warbot trouvé pour cette guilde", None

    return 0, "", {"guild_id": db_data[0],
                   "allyCode": str(db_data[1]),
                   "player_name": db_data[2],
                   "tbChanRead_id": db_data[3],
                   "tbChanOut_id": db_data[4],
                   "tbRoleOut": db_data[5],
                   "twFulldefDetection": db_data[6],
                   "guild_name": db_data[7],
                   "server_id": db_data[8],
                   "gfile_name": db_data[9],
                   "discord_id": db_data[10]}

########################################
# Get guild ID, allyCode and player name for the
#  google account linked to this channel
########################################
async def get_google_player_info(channel_id):
    query = "SELECT guildId, players.allyCode, players.name, \n"
    query+= "       tbChanRead_id, echostation_id, \n"
    query+= "       twChanOut_id \n"
    query+= "FROM user_bot_infos \n"
    query+= "JOIN players ON players.allyCode=user_bot_infos.allyCode \n"
    query+= "LEFT JOIN guild_bot_infos ON guild_bot_infos.guild_id=players.guildId \n"
    query+= "WHERE channel_id="+str(channel_id)
    goutils.log2("DBG", query)
    db_data = await get_line_async(query)
    if db_data == None:
        return 1, "Pas d'utilisateur trouvé pour ce channel", None
    
    return 0, "", {"guild_id": db_data[0],
                   "allyCode": str(db_data[1]),
                   "player_name": db_data[2],
                   "tbChanRead_id": db_data[3],
                   "echostation_id": db_data[4],
                   "twChanOut_id": db_data[5]}

# IN: tbs_round > ROTE1 to ROTE6, or ROTE0 to get the latest data
async def get_tb_platoon_allocations(guild_id, tbs_round):
    dict_unitsList = data.get("unitsList_dict.json")
    dict_tb = data.get("tb_definition.json")

    tb_name = tbs_round[:-1]
    tb_phase = int(tbs_round[-1])
    if tb_name == "ROTE":
        terr_pos = ["LS", "DS", "MS"]
    else:
        terr_pos = ["top", "mid", "bot"]

    query = "SELECT zone_id, platoon_id, unit_id, name FROM platoon_allocations " \
            "JOIN platoon_config ON platoon_config.id=config_id " \
            "JOIN players ON players.allyCode=platoon_allocations.allyCode " \
            "WHERE guild_id='"+guild_id+"' "
    if tb_phase>0:
        # Get the data for specific phase
        query += "AND phases="+str(tb_phase) 
    else:
        # Get the data for latest stored data of this guild
        query += "AND ABS(timestampdiff(SECOND, timestamp, (select max(timestamp) from platoon_config WHERE guild_id='"+guild_id+"')))<5"

    goutils.log2("DBG", query)
    db_data = await get_table_async(query)
    if db_data == None:
        return 1, "Aucune allocation de peloton connue", None

    dict_platoons_allocation = {}
    for line in db_data:
        zone_id = line[0]
        platoon_id = line[1]
        unit_id = line[2]
        player_name = line[3]

        conflict_id = "_".join(zone_id.split('_')[:-1])
        conflict_name = dict_tb[conflict_id]["name"] # "ROTE1-DS"

        if tb_name == "ROTE":
            platoon_position = str(7-int(platoon_id[-1]))
        else:
            platoon_position = "hoth-platoon-"+platoon_id[-1]

        platoon_name = conflict_name+"-"+platoon_position

        if not platoon_name in dict_platoons_allocation:
            dict_platoons_allocation[platoon_name] = {}
        
        unit_name = dict_unitsList[unit_id]["name"]
        if not unit_name in dict_platoons_allocation[platoon_name]:
            dict_platoons_allocation[platoon_name][unit_name] = []

        if player_name != None:
            dict_platoons_allocation[platoon_name][unit_name].append(player_name)

    return 0, "", {"dict_platoons_allocation": dict_platoons_allocation}



