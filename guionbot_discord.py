# -*- coding: utf-8 -*-
# Source --> https://realpython.com/how-to-make-a-discord-bot-python/
# CERTIFICATE_VERIFY_FAILED --> https://github.com/Rapptz/discord.py/issues/4159

import os
import config
import sys
import asyncio
import time
import datetime
from pytz import timezone
import difflib
import re
import discord
from discord.ext import tasks, commands
from discord import Activity, ActivityType, Intents, File, DMChannel, MessageReference
from discord import errors as discorderrors
from discord import app_commands
from io import BytesIO
import requests
import traceback
from texttable import Texttable
import zipfile
from typing import List
import json
import threading
import urllib

import bot_commands
import go
import goutils
import connect_gsheets
import connect_mysql
import connect_rpc
import parallel_work
import portraits
import data
import manage_mods
import manage_events
import emojis
import register

# Generic configuration
TOKEN = config.DISCORD_BOT_TOKEN
ADMIN_GUILD = discord.Object(id=config.ADMIN_SERVER_ID)
guild_timezone=timezone(config.GUILD_TIMEZONE)
bot_uptime=datetime.datetime.now(guild_timezone)
MAX_MSG_SIZE = 1900 #keep some margin for extra formating characters
bot_test_mode = False
bot_background_tasks = True
bot_on_message = True

#Global variables that may change during execution
first_bot_loop_5minutes = True
list_alerts_sent_to_admin = []
latestLocalizationBundleVersion = ""
latestGamedataVersion = ""

##############################################################
# Class: MyClient
# Description: the bot client, enabling basic bot and slash commands
##############################################################
class MyClient(commands.Bot):
    def __init__(self, *, command_prefix: list, intents: discord.Intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

#create bot
intents = Intents.all()
intents.members = True
intents.presences = True
intents.message_content = True
bot = MyClient(command_prefix=['go.', 'Go.', 'GO.'], intents=intents)

list_tw_opponent_msgIDs = []

dict_platoons_previously_done = {} #Empy set
dict_tb_alerts_previously_done = {}

##############################################################
#                                                            #
#                  FONCTIONS                                 #
#                                                            #
##############################################################

##############################################################
# Function: bot_loop_60secs
# Parameters: none
# Purpose: cette fonction est exécutée toutes les 60 secondes
# Output: none
##############################################################
async def bot_loop_60secs(bot):
    goutils.log2("INFO", "START loop")
    t_start = time.time()

    ########################
    # look for inactive bots
    # this is done before RPC update because RPC updates takes more than 
    # one minute and then the mod(now, period) is never 0
    try:
        query = "SELECT guild_bots.guild_id, allyCode, locked_since, lock_when_played, "\
                "timestampdiff(HOUR, locked_since, CURRENT_TIMESTAMP) AS delta_hours "\
                "FROM guild_bots "\
                "LEFT JOIN events ON events.type='bot_locked_reminder' "\
                "AND events.guild_id=guild_bots.guild_id "\
                "AND events.event_id=CONCAT('ELAPSED:', timestampdiff(HOUR, locked_since, CURRENT_TIMESTAMP)) "\
                "WHERE NOT isnull(locked_since) AND isnull(event_id) "\
                "AND NOT isnull(allyCode) "\
                "AND timestampdiff(HOUR, locked_since, CURRENT_TIMESTAMP)>0 "

        goutils.log2("INFO", query)
        db_data = connect_mysql.get_table(query)
        goutils.log2("INFO", "Required bot_locked_reminder db_data: "+str(db_data))
        if not db_data==None:
            for guild_bot in db_data:
                guild_id = guild_bot[0]
                allyCode = guild_bot[1]
                locked_since = guild_bot[2]
                lock_when_played = guild_bot[3]
                delta_hours = guild_bot[4]
                if lock_when_played:
                    #player account, do not re-activate it, just warn
                    await send_alert_to_bot_owner(guild_id, locked_since=locked_since)

                    #and log the reminder event
                    query = "INSERT INTO events(type, guild_id, event_id) "\
                            "VALUES('bot_locked_reminder', '"+guild_id+"','ELAPSED:"+str(delta_hours)+"') "
                    goutils.log2("DBG", query)
                    connect_mysql.simple_execute(query)

                else:
                    #bot account, re-activate it
                    query = "UPDATE guild_bots SET locked_since=null "\
                            "WHERE allyCode="+str(allyCode)
                    goutils.log2("DBG", query)
                    connect_mysql.simple_execute(query)

    except Exception as e:
        goutils.log2("ERR", traceback.format_exc())
        if not bot_test_mode:
            await send_alert_to_admins(None, "["+guild_id+"] Exception in bot_loop_60minutes:"+str(sys.exc_info()[0]))

    #######################################################################
    # UPDATE RPC data
    #
    # Update when the time since last update is greater than the period 
    # and the time is rounded.
    # (15 min bots are updated only at :00, :15, :30...)
    #
    # THe JOIN players ensures that the bot account is still in the right guild
    query = "SELECT guild_bots.guild_id "\
            "FROM guild_bots "\
            "JOIN players ON guild_bots.allyCode=players.allyCode AND guild_bots.guild_id=players.guildId "\
            "WHERE timestampdiff(MINUTE, latest_update, CURRENT_TIMESTAMP)>=(period-1) "\
            "AND isnull(locked_since) "\
            "AND mod(minute(CURRENT_TIMESTAMP), period)=0 "\
            "AND NOT isnull(guild_bots.allyCode) "
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_column(query)
    goutils.log2("DBG", "db_data: "+str(db_data))

    if not db_data==None:
        for guild_id in db_data:
            #update RPC data before using different commands (tb alerts, tb_platoons)
            try:
                ec, et = await update_rpc_data(guild_id)
                if ec==401:
                    await connect_rpc.lock_bot_account(guild_id)
                    await send_alert_to_bot_owner(guild_id)
                elif ec!=0 and not bot_test_mode:
                    await send_alert_to_admins(None, "["+guild_id+"] "+et)

                #log update time in DB - rounded to fix times
                # (eg: always 00:05, 00:10 for 5 min period)
                query = "UPDATE guild_bots SET latest_update=FROM_UNIXTIME(ROUND(UNIX_TIMESTAMP(NOW())/60/period,0)*60*period) "
                query+= "WHERE guild_id='"+guild_id+"'"
                goutils.log2("DBG", query)
                connect_mysql.simple_execute(query)

            except Exception as e:
                goutils.log2("ERR", traceback.format_exc())

    t_end = time.time()
    goutils.log2("INFO", "END loop ("+str(int(t_end-t_start))+" secs)")

##############################################################
# Function: bot_loop_5minutes
# Parameters: none
# Purpose: executed every 5 minutes
# Output: none
##############################################################
async def bot_loop_5minutes(bot):
    global dict_platoons_previously_done
    global dict_tb_alerts_previously_done
    global first_bot_loop_5minutes

    goutils.log2("DBG", "START loop")
    t_start = time.time()

    guild_bots = connect_rpc.get_dict_bot_accounts()

    for guild_id in guild_bots:
        #################################
        # Manage TW alerts and start of TW
        #################################
        try:
            #CHECK ALERTS FOR TERRITORY WAR
            ec, et, statusChan = await update_tw_status(guild_id)

        except Exception as e:
            goutils.log2("ERR", "["+guild_id+"]"+traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(None, "["+guild_id+"] Exception in bot_loop_5minutes:"+str(sys.exc_info()[0]))

        #################################
        # Manage TB alerts
        #################################
        try:
            if not guild_id in dict_tb_alerts_previously_done:
                dict_tb_alerts_previously_done[guild_id] = []

            #CHECK ALERTS FOR BT
            ec, et, ret_data = await go.get_tb_alerts(guild_id, -1)
            if ec == 0:
                list_tb_alerts = ret_data
                for tb_alert in list_tb_alerts:
                    if not tb_alert in dict_tb_alerts_previously_done[guild_id]:
                        if not first_bot_loop_5minutes:
                            await send_alert_to_echocommanders(guild_id, tb_alert)
                            goutils.log2("INFO", "["+guild_id+"] New TB alert: "+tb_alert)
                        else:
                            goutils.log2("DBG", "["+guild_id+"] New TB alert within the first 5 minutes: "+tb_alert)
                    else:
                        goutils.log2("DBG", "["+guild_id+"] Already known TB alert: "+tb_alert)

                dict_tb_alerts_previously_done[guild_id] = list_tb_alerts

            elif ec == 2:
                # Display TB summary
                tb_summary = ret_data
                await send_tb_summary(guild_bots[guild_id]["guildName"],
                                      tb_summary,
                                      guild_bots[guild_id]["tb_channel_end"])

        except Exception as e:
            goutils.log2("ERR", "["+guild_id+"]"+traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(None, "["+guild_id+"] Exception in bot_loop_5minutes:"+str(sys.exc_info()[0]))

        #################################
        # Check progress of platoons
        #################################
        try:
            #Check if guild can use RPC
            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info_from_guild(guild_id)
            if ec==0:
                guild_id = bot_infos["guild_id"]

                if not guild_id in dict_platoons_previously_done:
                    dict_platoons_previously_done[guild_id] = {}

                err_code, err_txt, ret_data = await connect_rpc.get_actual_tb_platoons(guild_id, -1)

                if err_code != 0:
                    goutils.log2("DBG", "["+guild_id+"] "+str(err_txt))
                    dict_platoons_previously_done[guild_id] = {}
                else:
                    tb_id = ret_data["tb_id"]
                    tbs_round = ret_data["round"]
                    dict_platoons_done = ret_data["platoons"]

                    await connect_mysql.update_tb_platoons(guild_id, tb_id, tbs_round, dict_platoons_done)

                    goutils.log2("DBG", "["+guild_id+"] Current state of platoon filling: "+str(dict_platoons_done))
                    goutils.log2("INFO", "["+guild_id+"] End of platoon parsing for TB: round " + tbs_round)
                    new_allocation_detected = False
                    dict_msg_platoons = {}
                    for territory_platoon in dict_platoons_done:
                        current_progress = compute_platoon_progress(dict_platoons_done[territory_platoon])
                        #goutils.log2("DBG", "["+guild_id+"] Progress of platoon "+territory_platoon+": "+str(current_progress))
                        if not territory_platoon in dict_platoons_previously_done[guild_id]:
                            #If the territory was not already detected, then all allocation within that territory are new
                            for character in dict_platoons_done[territory_platoon]:
                                for player in dict_platoons_done[territory_platoon][character]:
                                    if player != '':
                                        #goutils.log2("INFO", "["+guild_id+"] New platoon allocation: " + territory_platoon + ":" + character + " by " + player)
                                        new_allocation_detected = True

                            if current_progress == 1:
                                territory = territory_platoon[:-1]
                                territory_full_count = compute_territory_progress(dict_platoons_done, territory)
                                territory_display = territory.split("-")[1]
                                if not territory_display in dict_msg_platoons:
                                    dict_msg_platoons[territory_display] = [0, []]
                                dict_msg_platoons[territory_display][0] = territory_full_count
                                dict_msg_platoons[territory_display][1].append(territory_platoon)

                        else:
                            for character in dict_platoons_done[territory_platoon]:
                                if not character in dict_platoons_previously_done[guild_id][territory_platoon]:
                                    for player in dict_platoons_done[territory_platoon][character]:
                                        if player != '':
                                            #goutils.log2("INFO", "["+guild_id+"] New platoon allocation: " + territory_platoon + ":" + character + " by " + player)
                                            new_allocation_detected = True
                                else:
                                    for player in dict_platoons_done[territory_platoon][character]:
                                        if not player in dict_platoons_previously_done[guild_id][territory_platoon][character]:
                                            if player != '':
                                                #goutils.log2("INFO", "["+guild_id+"] New platoon allocation: " + territory_platoon + ":" + character + " by " + player)
                                                new_allocation_detected = True

                            previous_progress = compute_platoon_progress(dict_platoons_previously_done[guild_id][territory_platoon])
                            if current_progress == 1 and previous_progress < 1:
                                territory = territory_platoon[:-1]
                                territory_full_count = compute_territory_progress(dict_platoons_done, territory)
                                territory_display = territory.split("-")[1]
                                if not territory_display in dict_msg_platoons:
                                    dict_msg_platoons[territory_display] = [0, []]
                                dict_msg_platoons[territory_display][0] = territory_full_count
                                dict_msg_platoons[territory_display][1].append(territory_platoon)

                    #if not new_allocation_detected:
                        #goutils.log2("INFO", "["+guild_id+"] No new platoon allocation")
                
                    for territory_display in dict_msg_platoons:
                        territory_full_count = dict_msg_platoons[territory_display][0]
                        list_platoons = dict_msg_platoons[territory_display][1]

                        if territory_full_count == 6:
                            msg = '\N{WHITE HEAVY CHECK MARK}'
                        else:
                            msg = ''
                        if len(list_platoons) <= 1:
                            msg += "Nouveau peloton "
                            msg += list_platoons[0]
                            msg += " qui atteint 100% ("
                        else:
                            msg += "Nouveaux pelotons "
                            for territory_platoon in list_platoons:
                                msg += territory_platoon + " + "
                            msg = msg[:-3]
                            msg += " qui atteignent 100% ("
                        msg += territory_display+": "+str(territory_full_count)+"/6)"
                        if not first_bot_loop_5minutes:
                            goutils.log2("INFO", "["+guild_id+"]"+msg)
                            await send_alert_to_echocommanders(guild_id, msg)

                    dict_platoons_previously_done[guild_id] = dict_platoons_done.copy()

        except Exception as e:
            goutils.log2("ERR", "["+guild_id+"]"+traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(None, "["+guild_id+"] Exception in bot_loop_5minutes:"+str(sys.exc_info()[0]))

    first_bot_loop_5minutes = False

    t_end = time.time()
    goutils.log2("INFO", "END loop ("+str(int(t_end-t_start))+" secs)")

##############################################################
# Function: bot_loop_60minutes
# Parameters: none
# Purpose: high level monitoring, every 6 hours
# Output: none
##############################################################
async def bot_loop_60minutes(bot):
    global latestLocalizationBundleVersion
    global latestGamedataVersion

    goutils.log2("DBG", "START loop")
    t_start = time.time()

    try:
        #REFRESH and CLEAN CACHE DATA FROM SWGOH API
        err_code, err_txt = go.manage_disk_usage()

        if err_code > 0:
            await send_alert_to_admins(None, err_txt)

    except Exception as e:
        goutils.log2("ERR", traceback.format_exc())
        if not bot_test_mode:
            await send_alert_to_admins(None, "["+guild_id+"] Exception in bot_loop_60minutes:"+str(sys.exc_info()[0]))

    # Check metadata
    ec, et, metadata = await connect_rpc.get_metadata()
    if ec!=0:
        goutils.log2("ERR", et)

    LocalizationBundleVersion = metadata["latestLocalizationBundleVersion"]
    goutils.log2("INFO", "LocalizationBundleVersion="+LocalizationBundleVersion)
    if LocalizationBundleVersion != latestLocalizationBundleVersion \
        and latestLocalizationBundleVersion != "":

        if not bot_test_mode:
            await send_alert_to_admins(None, "New LocalizationBundle")
    latestLocalizationBundleVersion = LocalizationBundleVersion

    GamedataVersion = metadata["latestGamedataVersion"]
    goutils.log2("INFO", "GamedataVersion="+GamedataVersion)
    if GamedataVersion != latestGamedataVersion \
        and latestGamedataVersion != "":

        if not bot_test_mode:
            await send_alert_to_admins(None, "New GamedataVersion")
    latestGamedataVersion = GamedataVersion
    
    t_end = time.time()
    goutils.log2("INFO", "END loop ("+str(int(t_end-t_start))+" secs)")


################################################
# IN: platoon_content = {'Greef Karga': ['Dark Cds'], 'Yoda Ermite': ['Dark Cds', 'Toto234'], ...}
# OUT: % of progress
################################################
def compute_platoon_progress(platoon_content):
    all_allocations = [item for sublist in platoon_content.values() for item in sublist]
    real_allocations = [x for x in all_allocations if x != '']
    return len(real_allocations) / len(all_allocations)

################################################
# IN: dict_platoons = {"ROTE1-LS-1": {'Greef Karga': ['Dark Cds'],...}, "ROTE1-DS-1": ...}
# IN: territory = "ROTE1-LS-"
# OUT: [0 - 6]
################################################
def compute_territory_progress(dict_platoons, territory):
    count = 0
    for i_platoon in range(1,7):
        platoon = territory + str(i_platoon)
        platoon_progress = compute_platoon_progress(dict_platoons[platoon])
        if platoon_progress == 1:
            count += 1
    return count

##############################################################
# Function: send_alert_to_bot_owner
# Parameters: guild_id - le id of the guild associated to the warbot
# Purpose: send a message to the owner of the bot account
#          to warn him that the warbot has stopped
# Output: None
##############################################################
async def send_alert_to_bot_owner(guild_id, locked_since=None):
    ec, et, bot_infos = connect_mysql.get_warbot_info_from_guild(guild_id)
    if ec != 0:
        return

    discord_id = bot_infos["discord_id"]
    guild_name = bot_infos["guild_name"]
    if discord_id == None:
        return

    member = bot.get_user(int(discord_id))
    channel = await member.create_dm()

    if locked_since==None:
        message = "Le warbot de "+guild_name+" a été arrêté car tu as joué. Tape `go.bot.enable` pour le relancer"
    else:
        time_txt = locked_since.strftime("%H:%M")
        message = "Le warbot de "+guild_name+" a été arrêté à "+time_txt+" (CET). Tape `go.bot.enable` pour le relancer"
    goutils.log2("INFO", message)
    await channel.send(message)

##############################################################
# Function: send_alert_to_admins
# Parameters: message (string), message to be sent
# Purpose: send a message to bot admins. Only once, then the admin has to
#          stop/start the bot for a new message to be allowed
# Output: None
##############################################################
async def send_alert_to_admins(server, message):
    global list_alerts_sent_to_admin

    if server != None:
        message = "["+server.name+"] "+message

    if not message in list_alerts_sent_to_admin:
        list_ids = config.GO_ADMIN_IDS.split(' ')
        for userid in list_ids:
            member = bot.get_user(int(userid))
            channel = await member.create_dm()
            await channel.send(message)
        list_alerts_sent_to_admin.append(message)

##############################################################
# Function: send_alert_to_echocommanders
# Parameters: message (string), message to be sent
# Purpose: send a message to Echobot admins.
# Output: None
##############################################################
async def send_alert_to_echocommanders(guild_id, message):
    goutils.log2("DBG", "guild_id="+guild_id+", message="+message)
    if bot_test_mode:
        await send_alert_to_admins(None, "["+guild_id+"] "+message)
    else:
        ec, et, warbot_infos = connect_mysql.get_warbot_info_from_guild(guild_id)
        if ec != 0:
            await ctx.send('ERR: commande non utilisable Pour cette guilde')
            return

        goutils.log2("INFO", warbot_infos)
        tbChanOut_id = warbot_infos["tbChanOut_id"]
        tbRoleOut = warbot_infos["tbRoleOut"]
        guild_name = warbot_infos["guild_name"]
        server_id = warbot_infos["server_id"]

        if tbChanOut_id != 0:
            tb_channel = bot.get_channel(tbChanOut_id)
            try:
                await tb_channel.send("["+guild_name+"]"+ message)
            except discorderrors.Forbidden as e:
                goutils.log2("WAR", "["+guild_name+"] Cannot send message to "+str(tbChanOut_id))

        if tbRoleOut != "":
            server = bot.get_guild(server_id)
            if server == None:
                goutils.log2("WAR", "server "+str(server_id)+" not found > cannot send alert to echocommanders")
            else:
                for role in server.roles:
                    if role.name == tbRoleOut:
                        for member in role.members:
                            channel = await member.create_dm()
                            try:
                                await channel.send("["+guild_name+"]"+ message)
                            except discorderrors.Forbidden as e:
                                goutils.log2("WAR", "["+guild_name+"] Cannot send DM to "+member.name)

##############################################################
# Function: get_wb_allocation
# Parameters: tbs_round (string) > nom de phase en TB, sous la forme "GDS2"
# Purpose: lit le channel #batailles de territoire pour retouver
#          l'affectation des pelotons par WookieBot
# Output: dict_platoons_allocation={} #key=platoon_name, value={key=perso, value=[player...]}
##############################################################
async def get_wb_allocation(tbChannel_id, tbs_round):
    dict_tb = data.get("tb_definition.json")
    dict_units = data.get("unitsList_dict.json")
    ENG_US = data.get("ENG_US.json")

    FRE_char_names = []
    ENG_char_names = {}
    for unit_id in dict_units:
        unit = dict_units[unit_id]
        FRE_char_names.append(unit["name"])
        ENG_char_names[ENG_US[unit["nameKey"]]] = unit["name"]

    # Lecture des affectation ECHOBOT
    tb_channel = bot.get_channel(tbChannel_id)
    dict_platoons_allocation = {}  #key=platoon_name, value={key=perso, value=[player...]}

    # Read history of messages
    try:
        async for message in tb_channel.history(limit=500):
            if message.author.id == config.WOOKIEBOT_DISCORD_ID:
                for attachment in message.attachments:
                    goutils.log2("DBG", "Reading attachment...")
                    if not attachment.filename.endswith(".csv"):
                        continue
                    tb_shortname = attachment.filename.split("_")[0]
                    if tb_shortname=="rote":
                        tb_name = "ROTE"
                    else:
                        tb_name = tb_shortname

                    file_content = await attachment.read()
                    file_txt = file_content.decode('utf-8')

        ### do things

    except discorderrors.Forbidden as e:
        goutils.log2("WAR", "Cannot read history of messages in "+str(tbChannel_id))
        return 1, "Impossible de lire <#"+str(tbChannel_id)+"> (#"+tb_channel.name+")", None

    return 0, "", {"phase": eb_phase,
                   "dict_platoons_allocation": dict_platoons_allocation}


##############################################################
# Function: get_eb_allocation
# Parameters: tbs_round (string) > nom de phase en TB, sous la forme "GDS2"
# Purpose: lit le channel #batailles de territoire pour retouver
#          l'affectation des pelotons par Echobot
# Output: dict_platoons_allocation={} #key=platoon_name, value={key=perso, value=[player...]}
##############################################################
async def get_eb_allocation(tbChannel_id, echostation_id, tbs_round):
    dict_tb = data.get("tb_definition.json")
    dict_units = data.get("unitsList_dict.json")
    ENG_US = data.get("ENG_US.json")

    FRE_char_names = []
    ENG_char_names = {}
    for unit_id in dict_units:
        unit = dict_units[unit_id]
        FRE_char_names.append(unit["name"])
        ENG_char_names[ENG_US[unit["nameKey"]]] = unit["name"]

    # Lecture des affectation ECHOBOT
    tb_channel = bot.get_channel(tbChannel_id)
    dict_platoons_allocation = {}  #key=platoon_name, value={key=perso, value=[player...]}
    eb_phases = []
    eb_missions_full = []
    eb_missions_tmp = []
    
    tbs_name = tbs_round[:-1]

    current_tb_phase = {} # key = DS/MS/LS or top/mid/bot, value = number [1,6] of the phase
    detect_previous_BT = False

    sort_by_location = False
    sort_by_unit = False
    sort_by_player = False
    
    # Read history of messages
    try:
        async for message in tb_channel.history(limit=500):
            if message.author.name == "EchoStation" or message.author.id == echostation_id:
                if message.content.startswith('```prolog'):
                    #EB message by territory
                    sort_by_location = True

                    ret_re = re.search('```prolog\n(.*) \((.*)\):.*', message.content)
                    territory_name = ret_re.group(1) #Kashyyk, Zeffo, Hangar...
                    territory_position = ret_re.group(2) #top, mid, bonus...

                    if not territory_name in dict_tb["zone_names"]:
                        return 1, "Impossible de lire <#"+str(tbChannel_id)+"> (#"+tb_channel.name+"), territoire '"+territory_name+"' inconnu", None
                      
                    territory_name_position = dict_tb["zone_names"][territory_name]
                    territory_phase = territory_name_position.split("-")[0][-1]
                    territory_pos = territory_name_position.split("-")[1] #LS, DS, MS, top, mid, bot (+ optional 'b')

                    if territory_pos in current_tb_phase and current_tb_phase[territory_pos]<territory_phase:
                        detect_previous_BT = True
                        return 1
                    current_tb_phase[territory_pos] = territory_phase

                    for embed in message.embeds:
                        dict_embed = embed.to_dict()
                        if 'fields' in dict_embed:
                            platoon_num = dict_embed["description"].split(" ")[2][0]

                            platoon_name = territory_name_position + "-" + platoon_num
                            for dict_player in dict_embed['fields']:
                                player_name = dict_player['name']
                                for character in dict_player['value'].split('\n'):
                                    if "HELP!" in character:
                                        char_name = character[9:-1]
                                    else:
                                        char_name = character[1:-1]
                                    if char_name[0:4]=='*` *':
                                        char_name=char_name[4:]
                                    if "* `" in char_name:
                                        char_name=char_name[:char_name.index("* `")]
                                    if not platoon_name in dict_platoons_allocation:
                                        dict_platoons_allocation[
                                            platoon_name] = {}

                                    #the name may be in English
                                    if char_name in FRE_char_names:
                                        pass
                                    elif char_name in ENG_char_names:
                                        char_name = ENG_char_names[char_name]
                                    else:
                                        goutils.log2("WAR", "Unknwon character in EB allocation: "+char_name)

                                    if not char_name in dict_platoons_allocation[
                                            platoon_name]:
                                        dict_platoons_allocation[platoon_name][
                                            char_name] = []
                                    dict_platoons_allocation[platoon_name][
                                        char_name].append(player_name)
                    
                elif message.content.startswith('Common units:'):
                    #EB message by unit / Common units
                    for embed in message.embeds:
                        dict_embed = embed.to_dict()
                        if 'fields' in dict_embed:
                            # on garde le nom de la BT mais on met X comme numéro de phase
                            # le numéro de phase sera affecté plus tard

                            for dict_char in dict_embed['fields']:
                                char_name = re.search(':.*: (.*)', dict_char['name']).group(1)

                                for line in dict_char['value'].split('\n'):
                                    if line.startswith("**"):
                                        # mid - O3
                                        platoon_pos = line.split(" ")[0][2:] #top, mid, bonus
                                        platoon_num = line.split(" ")[2][1]  #1, 2, 6
                                        platoon_name = tbs_name + "X-" + platoon_pos + "-" + platoon_num
                                    else:
                                        ret_re = re.search("^(:.*: )?(`\*` )?([^:\[]*)(:crown:|:cop:)?( `\[[GR][0-9]*\]`)?$", line)
                                        player_name = ret_re.group(3).strip()
                                        
                                        if not platoon_name in dict_platoons_allocation:
                                            dict_platoons_allocation[platoon_name] = {}

                                        #the name may be in English
                                        if char_name in FRE_char_names:
                                            pass
                                        elif char_name in ENG_char_names:
                                            char_name = ENG_char_names[char_name]
                                        else:
                                            war_txt = "["+str(tbChannel_id)+"] Unknown character in EB allocation: "+char_name
                                            goutils.log2("WAR", war_txt)
                                            await send_alert_to_admins(None, war_txt)

                                        if not char_name in dict_platoons_allocation[
                                                platoon_name]:
                                            dict_platoons_allocation[platoon_name][
                                                char_name] = []
                                        dict_platoons_allocation[platoon_name][
                                            char_name].append(player_name)

                elif message.content.startswith('Rare Units:'):
                    #EB message by unit / Rare units
                    for embed in message.embeds:
                        dict_embed = embed.to_dict()
                        if 'fields' in dict_embed:
                            # on garde le nom de la BT mais on met X comme numéro de phase
                            # le numéro de phase sera affecté plus tard
                            char_name = dict_embed['author']['name']
                            
                            for dict_platoon in dict_embed['fields']:
                                ret_re = re.search('(.*) - .*', dict_platoon['name'])
                                if ret_re != None:
                                    territory_position = ret_re.group(1) #top, mid, bonus
                                    platoon_name = tbs_name + "X-" + territory_position + \
                                                    "-" + dict_platoon['name'][-1]
                                        
                                    for line in dict_platoon['value'].split('\n'):
                                        ret_re = re.search("^(:.*: )?(`\*` )?([^:\[]*)(:crown:|:cop:)?( `\[[GR][0-9]*\]`)?$", line)
                                        player_name = ret_re.group(3).strip()
                                            
                                        if char_name[0:4]=='*` *':
                                            char_name=char_name[4:]
                                        if not platoon_name in dict_platoons_allocation:
                                            dict_platoons_allocation[
                                                platoon_name] = {}

                                        #the name may be in English
                                        if char_name in FRE_char_names:
                                            pass
                                        elif char_name in ENG_char_names:
                                            char_name = ENG_char_names[char_name]
                                        else:
                                            goutils.log2("WAR", "Unknwon character in EB allocation: "+char_name)

                                        if not char_name in dict_platoons_allocation[
                                                platoon_name]:
                                            dict_platoons_allocation[platoon_name][
                                                char_name] = []
                                        dict_platoons_allocation[platoon_name][
                                            char_name].append(player_name)

                elif message.content.startswith(":information_source: **Overview**"):
                    #Overview of the EB posts. Gives the territory names
                    # this name helps allocating the phase
                    # In case of single-territory, helps recovering its position
                    message_lines = message.content.split("\n")

                    first_line = message_lines[0]
                    # this line is under format
                    ## "Overview - P5 (4/M4/4)"
                    eb_phase = first_line.split('(')[0].strip()[-1]

                    goutils.log2("INFO", "EB Overview line: "+message_lines[0])

                    if not sort_by_location:
                        #if EB is sorted by location, the names of territories is already defined
                        tname_tpos_dict = {}
                        for line in message_lines:
                            if ":globe_with_meridians:" in line:
                                ret_re = re.search(":.*: \*\*(.*) \((.*)\)\*\*", line)
                                if ret_re != None:
                                    territory_name = ret_re.group(1)
                                    territory_position = ret_re.group(2) #top, bottom, mid
                                    
                                    if territory_position in tname_tpos_dict:
                                        #ERROR
                                        return 1, "Impossible de lire <#"+str(tbChannel_id)+"> (#"+tb_channel.name+") car il y a deux zones nommées '"+territory_position+"'. Essayez de trier les allocations par *Location*", None

                                    tname_tpos_dict[territory_position] = territory_name

                        # Now that we have ensured no ambiguity in zone short names
                        # then rename platoons
                        for territory_position in tname_tpos_dict:
                            territory_name = tname_tpos_dict[territory_position]
                            ret_code = await replace_territory_name_in_platoons(territory_name, territory_position, dict_platoons_allocation, current_tb_phase)
                            if ret_code == 1:
                                #detect previous BT
                                break
                            elif ret_code == 2:
                                #error in platoon parsing
                                return 1, "Impossible de lire <#"+str(tbChannel_id)+"> (#"+tb_channel.name+"), territoire '"+territory_name+"' inconnu", None


                    # Assumption of a single Echostation allocation per phase
                    # no need to detect platoons from previous phases
                    break

                #elif message.content.startswith("<@") or message.content.startswith("Filled in another phase"):
                else: #try to manage any message as EchoBot allocation may be sent without the "include @mentions" option
                    #EB message by player
                    for embed in message.embeds:
                        dict_embed = embed.to_dict()
                        if 'description' in dict_embed:
                            if dict_embed['description'].startswith(":exclamation: Our guild needs more"):
                                #no need to read this
                                continue
                        if 'fields' in dict_embed:
                            #on garde le nom de la BT mais on met X comme numéro de phase
                            #le numéro de phase sera affecté plus tard
                            player_name = re.search('\*\*(.*)\*\*',
                                    dict_embed['description']).group(1)

                            for dict_platoon in dict_embed['fields']:
                                platoon_pos = dict_platoon['name'].split(" ")[0]
                                platoon_num = dict_platoon['name'][-1]
                                platoon_name = tbs_name + "X-" + platoon_pos + "-" + platoon_num

                                for character in dict_platoon['value'].split('\n'):
                                    if "HELP!" in character:
                                        char_name = character[9:-1]
                                    else:
                                        char_name = character[1:-1]
                                    if char_name[0:4]=='*` *':
                                        char_name=char_name[4:]
                                    if not platoon_name in dict_platoons_allocation:
                                        dict_platoons_allocation[
                                            platoon_name] = {}

                                    #the name may be in English
                                    if char_name in FRE_char_names:
                                        pass
                                    elif char_name in ENG_char_names:
                                        char_name = ENG_char_names[char_name]
                                    else:
                                        goutils.log2("WAR", "Unknwon character in EB allocation: "+char_name)

                                    if not char_name in dict_platoons_allocation[platoon_name]:
                                        dict_platoons_allocation[platoon_name][char_name] = []
                                    dict_platoons_allocation[platoon_name][char_name].append(player_name)

    except discorderrors.Forbidden as e:
        goutils.log2("WAR", "Cannot read history of messages in "+str(tbChannel_id))
        return 1, "Impossible de lire <#"+str(tbChannel_id)+"> (#"+tb_channel.name+")", None

    if len(current_tb_phase) == 0:
        return 1, "Aucune affectation détectée dans <#"+str(tbChannel_id)+"> (#"+tb_channel.name+")", None

    #cleanup btX platoons
    tmp_d = dict_platoons_allocation.copy()
    for platoon in dict_platoons_allocation:
        if platoon.split("-")[0][-1] == "X":
            del tmp_d[platoon]
    dict_platoons_allocation = tmp_d

    return 0, "", {"phase": eb_phase,
                   "dict_platoons_allocation": dict_platoons_allocation}

async def allocate_platoons_from_eb_DM(message):
    #Load DATA
    dict_tb = data.get("tb_definition.json")
    dict_units = data.get("unitsList_dict.json")
    ENG_US = data.get("ENG_US.json")

    FRE_char_names = []
    ENG_char_names = {}
    for unit_id in dict_units:
        unit = dict_units[unit_id]
        FRE_char_names.append(unit["name"])
        ENG_char_names[ENG_US[unit["nameKey"]]] = unit["name"]

    snapshot = message.message_snapshots[0]

    #detect author and associated allyCode
    player_name = ''
    for embed in snapshot.embeds:
        dict_embed = embed.to_dict()
        if "description" in dict_embed:
            player_name = dict_embed["description"][2:-2]
            break

    msg_author_id = message.author.id
    query = "SELECT player_discord.allyCode FROM player_discord "\
            "JOIN players ON players.allyCode=player_discord.allyCode "\
            "WHERE discord_id="+str(msg_author_id)+" " \
            "AND name='"+player_name+"'"
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_column(query)
    if db_data==None or len(db_data)!=1:
        goutils.log2("WAR", "Impossible to identify one single player for ID "+str(msg_author_id)+" and playerName "+player_name)
        await message.channel.send("Utilisateur <@"+str(msg_author_id)+"> inconnu pour le joueur "+player_name)
        return

    txt_allyCode = str(db_data[0])

    await message.channel.send("Lecture des pelotons à poser...")

    dict_allocations = {}
    territory_name_position = ''
    for embed in snapshot.embeds:
        dict_embed = embed.to_dict()
        #print(dict_embed)
        if 'fields' in dict_embed:
            for field in dict_embed["fields"]:
                if field["value"].startswith('```fix\n'):
                    #Zone name
                    ret_re = re.search('```fix\n(.*) \((.*)\)\n```', field["value"])
                    territory_name = ret_re.group(1) #Kashyyk, Zeffo, Hangar...
                    if not territory_name in dict_tb["zone_names"]:
                        goutils.log2("WAR", "Impossible to read EB forwadred DM due to unknown zone '"+territory_name+"'")
                        await message.channel.send("Zone inconnue "+territory_name)
                        return

                    territory_name_position = dict_tb["zone_names"][territory_name]
                    #print(field["value"], territory_name_position)

                elif field["value"].startswith(':arrow_right:'):
                    #character name(s)

                    #first get the platoon position
                    platoon_position = field["name"][-1]

                    #Then read the characters
                    for value_line in field["value"].split('\n'):
                        ret_re = re.search(':arrow_right: \*(.*)\*', value_line)
                        char_name = ret_re.group(1)
                        #print(value_line, char_name)

                        #the name may be in English
                        if char_name in FRE_char_names:
                            pass
                        elif char_name in ENG_char_names:
                            char_name = ENG_char_names[char_name]
                        else:
                            goutils.log2("WAR", "Unknwon character in EB allocation: "+char_name)
                            await message.channel.send("Unité inconnue "+char_name)
                            char_name = ''
                        if territory_name_position!='' and char_name!='':
                            platoon_name = territory_name_position+"-"+platoon_position
                            if not platoon_name in dict_allocations:
                                dict_allocations[platoon_name] = []
                            dict_allocations[platoon_name].append(char_name)

    allocation_txt = ""
    for platoon_name in dict_allocations:
        ec, et, ret_data = await go.deploy_platoons_tb(
                                        txt_allyCode, 
                                        platoon_name, 
                                        dict_allocations[platoon_name])
        if ec == 0:
            deployed_names = ret_data[0]
            undeployed_names = ret_data[1]

            if len(deployed_names)==0:
                if len(undeployed_names)>0:
                    line_txt = "**"+player_name+"** n'a pas pu poser "+str(undeployed_names)+" en " + platoon_name + " >> il faut trouver un autre joueur !"
                else:
                    line_txt = "**"+player_name+"** n'a plus rien à poser en " + platoon_name
            else:
                line_txt = emojis.rightpointingindex+"**"+player_name+"** a posé "+str(deployed_names)+" en " + platoon_name
                if len(undeployed_names)>0:
                    line_txt += ", mais n'a pas pu poser "+str(undeployed_names) + " >> il faut trouver un autre joueur !"

            allocation_txt += line_txt+"\n"
        else:
            allocation_txt += et+'\n'

    await message.channel.send(allocation_txt)

async def register_players_from_wb_guildstatus(message):
    snapshot = message.message_snapshots[0]

    #detect author and associated allyCode
    player_name = ''
    for embed in snapshot.embeds:
        dict_embed = embed.to_dict()
        print(dict_embed.keys())
        if "description" in dict_embed:
            player_name = dict_embed["description"][2:-2]
            break

###############
#OUT: 0 = OK / 1 = detect_previous_BT / 2 = unknown name
async def replace_territory_name_in_platoons(territory_name, territory_position, dict_platoons_allocation, current_tb_phase):
    dict_tb = data.get("tb_definition.json")

    if not territory_name in dict_tb["zone_names"]:
        return 2

    territory_name_position = dict_tb["zone_names"][territory_name]
    tbs_name = territory_name_position.split("-")[0][:-1]
    territory_phase = territory_name_position.split("-")[0][-1]
    territory_pos = territory_name_position.split("-")[1] #LS, DS, MS, top, mid, bot (+ optional 'b')

    if territory_pos in current_tb_phase and current_tb_phase[territory_pos]<territory_phase:
        detect_previous_BT = True
        return 1
    current_tb_phase[territory_pos] = territory_phase

    #Check if this mission/territory has been allocated in previous message
    existing_platoons = [i for i in dict_platoons_allocation.keys()
                         if i.startswith(territory_name_position)]

    if True: #len(existing_platoons) == 0:                    
        #TODO risk of regression here. Check kept for provision
        #necessary to remove the check when same zone has different allocations among several days
        # with the right name for the territory, modify dictionary
        keys_to_rename=[]                         
        for platoon_name in dict_platoons_allocation:
            if platoon_name.startswith(tbs_name + "X-"+territory_position):
                keys_to_rename.append(platoon_name)
            if platoon_name.startswith(tbs_name + "X-PLATOON") \
            or platoon_name.startswith(tbs_name + "X-OPERATION"):
                keys_to_rename.append(platoon_name)
        for key in keys_to_rename:
            new_key = territory_name_position+key[-2:]
            if new_key in dict_platoons_allocation:
                #Case of a platoon allocated twice
                # - either part day1 and part day 2
                # - or day2 replaces day1
                #Anyway the logic is to add, in the day2 allocations (key),
                # all allocations from day1 (new_key) that are not in conflict
                # (day2 has priority)

                for charname in dict_platoons_allocation[new_key]:
                    if charname in dict_platoons_allocation[key]:
                        added_players = [i for i in dict_platoons_allocation[new_key][charname] if i != 'Filled in another phase']
                        players = dict_platoons_allocation[key][charname]
                        for player in added_players:
                            if "Filled in another phase" in players:
                                players.remove("Filled in another phase")
                                players.append(player)
                            else:
                                #platoon already full, previous player is ignored
                                pass
                        dict_platoons_allocation[key][charname] = players
                    else:
                        #should not happen, but just in case...
                        dict_platoons_allocation[key][charname] = dict_platoons_allocation[new_key][charname]

            # Now that the key is well defined, rename it
            dict_platoons_allocation[new_key] = \
                    dict_platoons_allocation[key]
            del dict_platoons_allocation[key]
                    
    return 0

#####################
# IN - guild_id: the game guild ID
# IN - tbChannel_id: the discord channel where to get Echobot allocations
# OUT - full_txt
#####################
async def get_platoons(guild_id, tbs_round, tbChannel_id, echostation_id):

    ec, et, ret = await get_eb_allocation(tbChannel_id, echostation_id, tbs_round)
    if ec != 0:
        return ec, et

    eb_phase = ret["phase"]
    dict_platoons_allocation = ret["dict_platoons_allocation"]
    tbs_name = tbs_round[:-1]
    ec, et = go.store_eb_allocations(guild_id, tbs_name, eb_phase, dict_platoons_allocation)
    return ec, et

#####################
# IN - guild_id: the game guild ID
# IN - txt_allyCode: the allyCode of the player to deploy / None if no deployment
# IN - display_mentions: True if player names are replaced by @discord_name
# OUT - full_txt
#####################
async def check_and_deploy_platoons(guild_id, tbChannel_id, echostation_id, 
                                    deploy_allyCode, player_name, display_mentions, 
                                    filter_zones=[],
                                    connected_allyCode=None,
                                    free_platoons=False,
                                    targets_free_platoons=None):
    dict_tb = data.get("tb_definition.json")

    #Read actual platoons in game
    err_code, err_txt, ret_data = await connect_rpc.get_actual_tb_platoons(guild_id, 0, allyCode=connected_allyCode)
    tbs_round = ret_data["round"]
    dict_platoons_done = ret_data["platoons"]
    list_open_territories = ret_data["open_territories"]

    goutils.log2("DBG", "Current state of platoon filling: "+str(dict_platoons_done))
    for platoon in dict_platoons_done:
        goutils.log2("DBG", "dict_platoons_done["+platoon+"]="+str(dict_platoons_done[platoon]))

    #Recuperation de la liste des joueurs
    dict_players_by_IG = connect_mysql.load_config_players(guild_id=guild_id)[0]

    if tbs_round == '':
        return 1, "Aucune BT en cours"
    
    goutils.log2("INFO", 'Lecture terminée du statut BT : round ' + tbs_round)
    tb_name = tbs_round[:-1]
    tb_id = dict_tb[tb_name]["id"]

    # Read platoon allocations
    if tbChannel_id!=0 and not free_platoons:
        ec, et, ret = await get_eb_allocation(tbChannel_id, echostation_id, tbs_round)
        if ec != 0:
            return ec, et

        dict_platoons_allocation = ret["dict_platoons_allocation"]

        for platoon in dict_platoons_allocation:
            goutils.log2("DBG", "dict_platoons_allocation["+platoon+"]="+str(dict_platoons_allocation[platoon]))
    
        # Read DB platoon allocations
        #ec, et, ret = connect_mysql.get_tb_platoon_allocations(guild_id, tbs_round)
        #if ec != 0:
        #    return ec, et

        #dict_platoons_allocation_db = ret["dict_platoons_allocation"]

        #for platoon in dict_platoons_allocation_db:
        #    goutils.log2("DBG", "dict_platoons_allocation_db["+platoon+"]="+str(dict_platoons_allocation_db[platoon]))

    else:
        dict_platoons_allocation = {}

        if free_platoons and targets_free_platoons==None:
            list_zone_names = [x["zone_name"].split("-")[1] for x in list_open_territories]
            targets_free_platoons = "/".join(list_zone_names)

    
    #Comparaison des dictionnaires
    #Recherche des persos non-affectés
    list_platoon_names = sorted(dict_platoons_done.keys())
    phase_names_already_displayed = []
    list_missing_platoons, list_err = go.get_missing_platoons(
                                            dict_platoons_done, 
                                            dict_platoons_allocation,
                                            list_open_territories,
                                            targets_free_platoons=targets_free_platoons)

    #Affichage des deltas ET auto pose par le bot
    full_txt = ''
    cur_phase = 0

    #Affichage du statut de chaque peloton avant de mettre la liste des joueurs
    list_terr_status = []
    for terr in list_open_territories:
        terr_txt = "__"+terr["zone_name"]+"__: "
        count_15 = 0
        for i_platoon in range(1,7):
            platoon_name = terr["zone_name"]+"-"+str(i_platoon)
            count_done = 0
            for unit in dict_platoons_done[platoon_name]:
                needed_units = len(dict_platoons_done[platoon_name][unit])
                missing_units = dict_platoons_done[platoon_name][unit].count('')
                count_done += (needed_units - missing_units)
            terr_txt += str(count_done)+" "
            if count_done==15:
                count_15+=1

        #overall status of the platoon zone
        if count_15 == 6:
            terr_txt = emojis.check + terr_txt
        elif "cmdState" in terr and terr["cmdState"] == "IGNORED":
            terr_txt = emojis.prohibited + terr_txt
        else:
            terr_txt = emojis.rightpointingindex + terr_txt

        if "cmdMsg" in terr:
            terr_txt += "("+terr["cmdMsg"]+")"
        list_terr_status.append([terr["zone_name"], terr_txt])

    #sort by zone position
    list_terr_status = sorted(list_terr_status, key=lambda x:dict_tb[tb_id]["zonePositions"][x[0].split("-")[1].rstrip("b")] + 0.5*x[0].split("-")[1].endswith("b"))
    for terr_status in list_terr_status:
        full_txt += terr_status[1]+"\n"
    full_txt += "---\n"

    list_info_txt = []
    list_bot_txt = []
    required_bot_deployments = {} #key=platoon_name / value=[perso1, perso2...]
    for missing_platoon in sorted(list_missing_platoons, key=lambda x: (x["platoon"][:4], 
                                                                        str(x["player_name"]), 
                                                                        x["platoon"])):
        allocated_player = missing_platoon["player_name"]
        platoon_name = missing_platoon["platoon"]
        perso = missing_platoon["character_name"]

        # Manage if the notification is sent or not
        # NOT SENT if the platoon zone is locked
        # NOT SENT if the user has defined filter zones and the platoon is not in the filter
        platoon_locked = missing_platoon["locked"]
        if filter_zones != []:
            platoon_allowed = False
            for f in filter_zones:
                if f in platoon_name:
                    platoon_allowed = True

            if not platoon_allowed:
                platoon_locked = True

        # In case the command is meant to display to all
        # AND the platoon is locked or filtered, do not display it
        # which means to ignore it
        if display_mentions and platoon_locked:
            continue

        #write the displayed text
        if (allocated_player in dict_players_by_IG) and display_mentions:
            line_txt = '**' + \
                  dict_players_by_IG[allocated_player][1] + \
                  '** n\'a pas posé ' + perso + \
                  ' en ' + platoon_name
        elif allocated_player == None:
            # No player allocated
            #joueur non-enregistré ou mentions non autorisées,
            # on l'affiche quand même
            line_txt = 'Aucun joueur n\'a posé ' + perso + \
                  ' en ' + platoon_name

            if platoon_locked:
                line_txt = "~~" + line_txt + "~~ ("+platoon_name+" est verrouillé)"
        else:
            #joueur non-enregistré ou mentions non autorisées,
            # on l'affiche quand même
            line_txt = '**' + allocated_player + \
                  '** n\'a pas posé ' + perso + \
                  ' en ' + platoon_name

            if platoon_locked:
                line_txt = "~~" + line_txt + "~~ ("+platoon_name+" est verrouillé)"

        #Pose auto du bot
        bot_line = False
        if deploy_allyCode!=None and not platoon_locked:
            if allocated_player == player_name:
                if not platoon_name in required_bot_deployments:
                    required_bot_deployments[platoon_name] = []
                required_bot_deployments[platoon_name].append(perso)
                bot_line = True

        phase_num = int(platoon_name.split('-')[0][-1])
        if cur_phase != phase_num:
            cur_phase = phase_num
            #full_txt += '\n---- **Phase ' + str(cur_phase) + '**\n'

        position = platoon_name.split('-')[1]
        if position == "bottom":
            position = "bot"

        too_late = False
        for open_terr in list_open_territories:
            if open_terr["zone_name"].endswith(position):
                if cur_phase < open_terr["phase"]:
                    too_late = True

        if too_late:
            if free_platoons:
                continue

            line_txt += ' -- *et c\'est trop tard*\n'
        else:
            line_txt += '\n'

        if not bot_line:
            full_txt += line_txt

    # Deploy the bot required units
    # They are grouped by platoon to be more efficient
    for platoon_name in required_bot_deployments:
        ec, et, ret_data = await go.deploy_platoons_tb(
                                        deploy_allyCode, 
                                        platoon_name, 
                                        required_bot_deployments[platoon_name])
        if ec == 0:
            deployed_names = ret_data[0]
            undeployed_names = ret_data[1]

            if len(deployed_names)==0:
                line_txt = "**"+player_name+"** n'a pas pu poser "+str(undeployed_names)+" en " + platoon_name + " >> il faut trouver un autre joueur !"
            else:
                line_txt = emojis.rightpointingindex+"**"+player_name+"** a posé "+str(deployed_names)+" en " + platoon_name
                if len(undeployed_names)>0:
                    line_txt += ", mais n'a pas pu poser "+str(undeployed_names) + " >> il faut trouver un autre joueur !"

            full_txt += line_txt+"\n"
        else:
            return ec, et

    if len(list_missing_platoons)>0 or len(list_err)>0:
        for err in sorted(set(list_err)):
            full_txt += err + '\n'
    elif tbChannel_id==0:
        full_txt+='WAR: warbot non configuré pour vérifier les allocations EchoBot\n'
    else:
        full_txt += "Aucune erreur de peloton\n"

    return 0, full_txt

##############################################################
# Function: update_tw_status
# Parameters: guild_id (string)
# Purpose: crée ou met à jour le statut de GT
##############################################################
async def update_tw_status(guild_id, backup_channel_id=None, allyCode=None):
    goutils.log2("DBG", (guild_id, backup_channel_id, allyCode))
    if allyCode==None:
        #using the warbot
        #ec, et, ret_tw_alerts = await go.get_tw_alerts(guild_id, -1)
        ret_tw_status = await connect_rpc.get_tw_status(guild_id, -1,
                                                        manage_tw_end=True)
    else:
        #using player connection
        #ec, et, ret_tw_alerts = await go.get_tw_alerts(guild_id, 1, allyCode=allyCode)
        ret_tw_status = await connect_rpc.get_tw_status(guild_id, 1, allyCode=allyCode, 
                                                        manage_tw_end=True)

    #Get the output channel
    query = "SELECT twChanOut_id "\
            "FROM guild_bot_infos "\
            "WHERE guild_id='"+guild_id+"'"
    goutils.log2('DBG', query)
    channel_id = connect_mysql.get_value(query)

    if channel_id == None:
        if backup_channel_id==None:
            return 1, "ERR: pas de channel GT configuré pour la guilde "+guild_id, None
        channel_id = backup_channel_id
        
    tw_bot_channel = bot.get_channel(channel_id)
    goutils.log2("DBG", "["+guild_id+"] TW channel: "+str(channel_id))

    # TW basic info
    tw_id = ret_tw_status["tw_id"]
    if tw_id == None:
        #TW is over
        return 0, "", None

    tw_round = ret_tw_status["tw_round"]
    if tw_round == -1:
        return 1, "GT non démarrée, phase d'inscription", None

    #TW end summary table
    if "tw_summary" in ret_tw_status and ret_tw_status["tw_summary"]!=None:
        # Display TW results
        tw_summary = ret_tw_status["tw_summary"]
        for stxt in goutils.split_txt(tw_summary, MAX_MSG_SIZE):
            await tw_bot_channel.send('```\n' + stxt + '```')

    #intialize parameters
    awayGuild = ret_tw_status["awayGuild"]
    list_opponent_squads = awayGuild["list_defenses"]
    list_opp_territories = awayGuild["list_territories"]
    homeGuild = ret_tw_status["homeGuild"]
    list_def_squads = homeGuild["list_defenses"]
    list_def_territories = homeGuild["list_territories"]

    #Launch TW alert function
    ec, et, ret_tw_alerts = await go.get_tw_alerts(guild_id,
                                                   tw_id,
                                                   list_opponent_squads,
                                                   list_opp_territories,
                                                   list_def_squads,
                                                   list_def_territories)

    goutils.log2("DBG", "["+guild_id+"] get_tw_alerts err_code="+str(ec))
    if ec != 0:
        return ec, et, None

    [dict_messages, tw_ts] = ret_tw_alerts["alerts"]

    # TW ongoing
    dict_guild = ret_tw_status['rpc']['guild']
    tw = dict_guild["territoryWarStatus"][0]
    opp_guild_id = tw["awayGuild"]["profile"]["id"]
    opp_guild_name = tw["awayGuild"]["profile"]["name"]
    score = sum([int(x['zoneStatus']['score']) \
                 for x in tw['homeGuild']['conflictStatus']])
    opp_score = sum([int(x['zoneStatus']['score']) \
                     for x in tw['awayGuild']['conflictStatus']])

    # Check event for TW start, and load opponent guild
    swgohgg_opp_url = None
    if not manage_events.exists("tw_start", guild_id, tw_id):
        goutils.log2("INFO", "["+guild_id+"] loading opponent TW guid...")

        #Fire and forget guild loading in the background
        asyncio.create_task(go.load_guild_from_id(opp_guild_id, True, True))

        #Display swgoh.gg link to opponent guild
        swgohgg_opp_url = "https://swgoh.gg/g/"+opp_guild_id

        #Delete potential previous tw_messages
        query = "DELETE FROM tw_messages WHERE guild_id='"+guild_id+"' "
        query+= "AND timestampdiff(HOUR, FROM_UNIXTIME(tw_ts/1000), CURRENT_TIMESTAMP)>24"
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

        manage_events.create_event("tw_start", guild_id, tw_id)

    # update DB
    await connect_mysql.update_tw(guild_id, tw_id, opp_guild_id,
                                  opp_guild_name, score, opp_score,
                                  homeGuild, awayGuild)

    # Display Link to opponent guild
    if swgohgg_opp_url != None:
        if tw_bot_channel==None:
            print("Guilde adverse : "+swgohgg_opp_url)
        else:
            await tw_bot_channel.send("Guilde adverse : "+swgohgg_opp_url)

    #sort dict_messages
    # defense then lost territories then attack
    d_placements = {key:dict_messages[key] for key in [k for k in dict_messages.keys() if k.startswith("Placement:")]}
    d_home = {key:dict_messages[key] for key in [k for k in dict_messages.keys() if k.startswith("Home:")]}
    d_attack = {key:dict_messages[key] for key in [k for k in dict_messages.keys() if not ":" in k]}
    dict_messages = {**d_placements, **d_home, **d_attack}
    for territory in dict_messages:
        msg_txt = dict_messages[territory]
        goutils.log2("DBG", "["+guild_id+"] TW alert: "+msg_txt)

        #get msg_id for this TW / zone
        query = "SELECT msg_id FROM tw_messages "
        query+= "WHERE guild_id='"+guild_id+"' "
        query+= "AND zone='"+territory+"'"
        goutils.log2("DBG", query)
        old_msg_id = connect_mysql.get_value(query)

        if old_msg_id == None:
            #First time this zone has a message
            goutils.log2("INFO", "first time this zone has this message")

            #Full message to TW guild channel
            if not bot_test_mode:
                if tw_bot_channel==None:
                    print(msg_txt)
                else:
                    new_msg = await tw_bot_channel.send(msg_txt)
                    query = "INSERT INTO tw_messages(guild_id, tw_ts, zone, msg_id) "
                    query+= "VALUES('"+guild_id+"', "+tw_ts+", '"+territory+"', "+str(new_msg.id)+")"
                    goutils.log2("DBG", query)
                    connect_mysql.simple_execute(query)
        else:
            #This zone already has a message
            if tw_bot_channel==None:
                old_msg = None
                old_msg_txt = ""
            else:
                try:
                    old_msg = await tw_bot_channel.fetch_message(old_msg_id)
                except discord.errors.NotFound as e:
                    goutils.log2("ERR", "msg not found id="+str(old_msg_id))
                    raise(e)

                old_msg_txt = old_msg.content

            #Home messages are not modified

            #Placement messages are updated when modified
            #Attack messages are updated when modified
            if territory.startswith('Placement:') \
               or not ":" in territory:
                if old_msg_txt != msg_txt:
                    #Full message modified in TW guild channel
                    if not bot_test_mode:
                        if old_msg==None:
                            print(msg_txt)
                        else:
                            await old_msg.edit(content=msg_txt)

    if tw_bot_channel==None:
        tw_bot_channel_id = None
    else:
        tw_bot_channel_id = tw_bot_channel.id

    return 0, "", tw_bot_channel_id

async def send_tb_summary(guild_name, tb_summary, channel_id):
    goutils.log2("INFO", "["+guild_name+"] tb_summary="+str(tb_summary)[:100]+" on channel "+str(channel_id))
    if channel_id!=0:
        tb_end_channel = bot.get_channel(channel_id)

        (csv, image, endTime, txt_results) = tb_summary
        date_txt = datetime.datetime.fromtimestamp(endTime).strftime("%d/%m")
        msg_txt = "# BT de "+guild_name+" terminée le "+date_txt
        msg_txt += "\n"+txt_results

        #prepare csv file
        export_path="/tmp/tbsummary"+guild_name+".csv"
        export_file = open(export_path, "w")
        export_file.write(csv)
        export_file.close()

        with BytesIO() as image_binary:
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            await tb_end_channel.send(content = msg_txt,
                files=[File(fp=image_binary, filename='image.png'),
                       File(export_path)])

##############################################################
# Function: update_rpc_data
# Parameters: guild_id (string)
# Purpose: crée ou met à jour le statut de GT
##############################################################
async def update_rpc_data(guild_id, allyCode=None):
    goutils.log2("DBG", (guild_id, allyCode))

    #Get guild infos from warbot or player
    guild_bots = connect_rpc.get_dict_bot_accounts()
    if allyCode==None:
        # this is a guild with warbot
        guildName = guild_bots[guild_id]["guildName"]
        tb_channel_end = guild_bots[guild_id]["tb_channel_end"]
        fight_estimation_type = guild_bots[guild_id]["tbFightEstimationType"]
    else:
        # no warbot, get infos from guild linked to player
        query = "SELECT guildName, tbChanEnd_id, tbFightEstimationType "\
                "FROM guild_bot_infos " \
                "JOIN players on players.guildId = guild_bot_infos.guild_id " \
                "WHERE allyCode = "+str(allyCode)
        goutils.log2("DBG", query)
        db_data = connect_mysql.get_line(query)
        if db_data == None:
            guildName = ""
            tb_channel_end = 0
            fight_estimation_type = 0
        else:
            guildName = db_data[0]
            tb_channel_end = db_data[1]
            fight_estimation_type = db_data[2]

    #This RPC call gets everything once, so that next calls in the 
    # following lines are able to use cache data
    ec, et, ret_data = await connect_rpc.get_guild_rpc_data( guild_id, ["TW", "TB", "CHAT"], 1, allyCode=allyCode)
    if ec!=0:
        goutils.log2("ERR", et)
        return ec, et
    dict_guild = ret_data[0]
    dict_events = ret_data[2]

    #Update DB and website during TB
    ec, et, tb_data = await connect_rpc.get_tb_status(guild_id, "", -1, 
                                fight_estimation_type=fight_estimation_type,
                                allyCode=allyCode)
    if ec != 0:
        # No TB ongoing - close TB
        if tb_data!=None and "tb_summary" in tb_data and tb_data["tb_summary"]!=None:
            # Display TB summary
            await send_tb_summary(guildName, tb_data["tb_summary"], tb_channel_end)

    
    #Update log channels
    ec, et, ret_data = await connect_rpc.get_guildLog_messages(guild_id, True, 1, allyCode=allyCode,
                                                               dict_guild=dict_guild,
                                                               dict_events=dict_events)
    if ec!=0:
        goutils.log2("ERR", et)
        return ec, et
    else:
        for logType in ["CHAT", "TW", "TB"]:
            channel_id = ret_data[logType][0]
            list_logs = sorted(ret_data[logType][1], key=lambda x:x[0])
            if channel_id != 0:
                try:
                    output_channel = (bot.get_channel(channel_id) \
                                     or await bot.fetch_channel(channel_id))
                except Exception as e:
                    output_channel = None

                if output_channel!=None:
                    output_txt = ""
                    for line in list_logs:
                        ts = line[0]
                        txt = line[1]
                        ts_txt = datetime.datetime.fromtimestamp(int(ts/1000)).strftime("%H:%M")
                        output_txt+=ts_txt+" - "+txt+"\n"
                    if output_txt != "":
                        output_txt = output_txt[:-1]
                        for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                            await output_channel.send("`"+txt+"`")
                else:
                    war_msg="Error while getting channel for id "+str(channel_id)
                    goutils.log2("WAR", war_msg)
                    return 0, war_msg

    return 0, ""


##############################################################
# Function: get_channel_from_channelname
# Parameters: channel_name (string) > nom de channel sous la forme <#1234567890>
# Purpose: récupère un objet channel pour écrire dans le channel spécifié
# Output: nominal > output_channel (objet channel), ""
#         si erreur > None, "message d'erreur" (string)
##############################################################
async def get_channel_from_channelname(ctx, channel_name):
    try:
        if channel_name.startswith("<#"):
            id_output_channel_txt = channel_name[2:-1]
        else: # https://discord/com/channels/
            id_output_channel_txt = channel_name.split('/')[-1]
        id_output_channel = int(id_output_channel_txt)
    except Exception as e:
        goutils.log2("ERR", e)
        return None, channel_name + ' n\'est pas un channel valide'

    output_channel = bot.get_channel(id_output_channel)
    if output_channel == None:
        return None, 'Channel ' + channel_name + '(id=' \
                    + str(id_output_channel) + ') introuvable'

    if not output_channel.permissions_for(output_channel.guild.me).send_messages:
        output_channel = ctx.message.channel
        return None, 'Il manque les droits d\'écriture dans ' \
                    + channel_name
            
    return output_channel, ''

##############################################################
# Function: manage_me
# Parameters: allyCode_txt (string) > code allié
# Purpose: affecte le code allié de l'auteur si "me"
# Output: code allié (string)
##############################################################
async def manage_me(ctx, alias, allow_tw):
    table_alias = alias.split('/')

    ret_allyCode = []

    #Get identity of command user
    dict_players_by_ID = connect_mysql.load_config_players()[1]
    if ctx!=None and ctx.author.id in dict_players_by_ID:
        cmd_allyCode_txt = str(dict_players_by_ID[ctx.author.id]["main"][0])
        cmd_guild_id = str(dict_players_by_ID[ctx.author.id]["main"][2])
    else:
        cmd_allyCode_txt = None
        cmd_guild_id = None

    # Loop on given aliases
    for alias in table_alias:
        #Special case of 'me' as allyCode
        if alias == 'me':
            if cmd_allyCode_txt != None:
                ret_allyCode_txt = cmd_allyCode_txt
            else:
                ret_allyCode_txt = "ERR: \"me\" (<@"+str(ctx.author.id)+">) n'est pas enregistré dans le bot. Utiliser la comande `go.register <code allié>`"

        elif alias == "-TW":
            if not allow_tw:
                return "ERR: l'option -TW n'est pas utilisable avec cette commande"

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                return "ERR: commande non autorisée depuis un DM avec l'option -TW"

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send('ERR: '+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            connected_allyCode = bot_infos["allyCode"]

            #Launch the actuel search
            ec, et, allyCode = await connect_rpc.get_tw_opponent_leader(guild_id, allyCode=connected_allyCode)
            if ec != 0:
                return "ERR: "+et

            ret_allyCode_txt = allyCode

        elif alias.startswith('<@'):
            # discord @mention
            if alias.startswith('<@!'):
                discord_id = int(alias[3:-1])
            else: # '<@ without the !
                discord_id = int(alias[2:-1])
            goutils.log2("INFO", "command launched with discord @mention "+alias)
            if discord_id in dict_players_by_ID:
                ret_allyCode_txt = str(dict_players_by_ID[discord_id]["main"][0])
            else:
                ret_allyCode_txt = 'ERR: '+alias+' ne fait pas partie des joueurs enregistrés'

        elif re.match("[0-9]{3}-[0-9]{3}-[0-9]{3}", alias) != None:
            # 123-456-789 >> allyCode
            ret_allyCode_txt = alias.replace("-", "")

        elif alias.isnumeric():
            # number >> allyCode
            ret_allyCode_txt = alias

        else:
            if cmd_guild_id != None:
                # Look for the name among user's guild player names
                query = "SELECT name, allyCode FROM players "\
                        "WHERE NOT isnull(name) "\
                        "AND guildId='"+cmd_guild_id+"' "
                goutils.log2("DBG", query)
                guild_db_results = connect_mysql.get_table(query)

                list_names = [x[0] for x in guild_db_results]
                closest_guild_names_db=difflib.get_close_matches(alias, list_names, 1)
                if len(closest_guild_names_db) == 0:
                    closest_guild_name_db = ""
                    closest_guild_name_db_score = 0
                else:
                    closest_guild_name_db = closest_guild_names_db[0]
                    closest_guild_name_db_score = difflib.SequenceMatcher(None, alias, closest_guild_name_db).ratio()
                    for r in guild_db_results:
                        if r[0] == closest_guild_name_db:
                            closest_guild_name_db_ac = str(r[1])
            else:
                closest_guild_name_db = ""
                closest_guild_name_db_score = 0

            # Look for the name among all player names
            # (including current guild. If there is a better match
            # elsewhere it will still be a better match. If there is an
            # equal match, we'll manage it later)
            query = "SELECT name, allyCode FROM players "\
                    "WHERE NOT isnull(name) "
            goutils.log2("DBG", query)
            all_db_results = connect_mysql.get_table(query)

            list_names = [x[0] for x in all_db_results]
            closest_names_db=difflib.get_close_matches(alias, list_names, 1)
            if len(closest_names_db) == 0:
                closest_name_db = ""
                closest_name_db_score = 0
            else:
                closest_name_db = closest_names_db[0]
                closest_name_db_score = difflib.SequenceMatcher(None, alias, closest_name_db).ratio()
                for r in all_db_results:
                    if r[0] == closest_name_db:
                        closest_name_db_ac = str(r[1])

            #check among discord names
            if ctx != None and ctx.guild != None and (closest_name_db != alias):
                #Remove text in [] and in ()
                guild_members_clean = [[x.id, re.sub(r'\([^)]*\)', '',
                                        re.sub(r'\[[^)]*\]', '',x.display_name)).strip()]
                                        for x in ctx.guild.members]
                list_discord_names = [x[1] for x in guild_members_clean]
                closest_names_discord=difflib.get_close_matches(alias, list_discord_names, 1)
                if len(closest_names_discord) == 0:
                    closest_name_discord = ""
                    closest_name_discord_score = 0
                else:
                    closest_name_discord = closest_names_discord[0]
                    closest_name_discord_score = difflib.SequenceMatcher(None, alias, closest_name_discord).ratio()
            else:
                closest_name_discord = ""
                closest_name_discord_score = 0

            #Compare results and select the winner
            if closest_guild_name_db_score == 0 \
               and closest_name_db_score == 0 \
               and closest_name_discord_score == 0:

                goutils.log2("WAR", alias +" not found in DB and in discord")
                ret_allyCode_txt = "ERR: le joueur "+alias+" n'a pas été trouvé"

            elif closest_guild_name_db_score >= closest_name_db_score \
                 and closest_guild_name_db_score >= closest_name_discord_score:

                goutils.log2("INFO", alias +" looks like the DB guild name "+closest_guild_name_db)
                ret_allyCode_txt = closest_guild_name_db_ac

            elif closest_name_db_score >= closest_name_discord_score:

                goutils.log2("INFO", alias +" looks like the DB name "+closest_name_db)
                ret_allyCode_txt = closest_name_db_ac

            else:
                goutils.log2("INFO", alias + " looks like the discord name "+closest_name_discord)

                discord_id = [x[0] for x in guild_members_clean if x[1] == closest_name_discord][0]
                if discord_id in dict_players_by_ID:
                    ret_allyCode_txt = str(dict_players_by_ID[discord_id]["main"][0])
                else:
                    goutils.log2("ERR", alias + " ne fait pas partie des joueurs enregistrés")
                    ret_allyCode_txt = 'ERR: '+alias+' ne fait pas partie des joueurs enregistrés'

        ret_allyCode.append(ret_allyCode_txt)
    
    if len(ret_allyCode)==1:
        return ret_allyCode[0]
    else:
        return ret_allyCode

##############################################################
# Function: read_gsheets
# IN: gfile_name
# OUT: err_code (0 = OK), err_txt
##############################################################
async def read_gsheets(guild_id):
    try:
        err_code = 0
        err_txt = ""

        ec, et, d = connect_gsheets.load_config_units(True)
        if ec != 0:
            err_txt += "ERR: erreur en mettant à jour les UNITS - "+et+"\n"
            err_code = 1

        d = connect_gsheets.load_config_categories(True)
        if d == None:
            err_txt += "ERR: erreur en mettant à jour les CATEGORIES\n"
            err_code = 1

        ec, l, d = connect_gsheets.load_config_teams(None, True)
        if ec != 0:
            err_txt += "ERR: erreur en mettant à jour les TEAMS GV\n"
            err_code = 1

        ec, l, d = connect_gsheets.load_config_teams(guild_id, True)
        if ec == 2:
            err_txt += "ERR: pas de fichier de config pour ce serveur\n"
            err_code = 1
        elif ec == 3:
            err_txt += "ERR: pas d'onglet 'teams' dans le fichier de config\n"
            err_code = 1
        elif ec == 1:
            err_txt += "ERR: erreur en mettant à jour les TEAMS\n"
            err_code = 1

        err_code, [dt, m] = connect_gsheets.get_tb_triggers(guild_id, True)
        if err_code != 0:
            err_txt += "ERR: erreur en mettant à jour les objectifs de BT\n"
            err_code = 1

        l = connect_gsheets.load_tw_counters(guild_id, True)
        if l == None:
            err_txt += "ERR: erreur en mettant à jour les contres GT\n"
            err_code = 1

        ec, et = connect_gsheets.load_config_statq()
        if ec != 0:
            err_txt += "ERR: erreur en mettant à jour les persos statq\n"
            err_code = 1

        return err_code, err_txt
    except Exception as e:
        goutils.log2("ERR", traceback.format_exc())

        return 1, "error while loading gsheet data"

##############################################################
#                                                            #
#                  EVENEMENTS                                #
#                                                            #
##############################################################

##############################################################
# Event: on_ready
# Parameters: none
# Purpose: se lance quand le bot est connecté
#          La première action consiste à recherger les infos de la guilde principale
#          afin d'assurer un refresh permanent du CACHE des membres de la guilde
# Output: none
##############################################################
@bot.event
async def on_ready():
    await bot.change_presence(activity=Activity(type=ActivityType.listening, name="go.help"))

    #recover external IP address
    #ip = requests.get('https://api.ipify.org').text
    ip = requests.get('https://v4.ident.me').text
    
    msg = bot.user.name+" has connected to Discord from ip "+ip
    goutils.log2("INFO", msg)
    if not bot_test_mode:
        await send_alert_to_admins(None, msg)

@bot.event
async def on_resumed():
    msg = "Bot has reconnected to Discord"
    goutils.log2("INFO", msg)

@bot.event
async def on_disconnect():
    msg = "Bot has disconnected from Discord"
    goutils.log2("INFO", msg)


##############################################################
# Event: on_reaction_add
# Parameters: reaction (object containing different other ones)
#             user (user taging with the emoji)
# Purpose: se lance quand une réaction est ajoutée à un message
# Output: none
##############################################################
@bot.event
async def on_raw_reaction_add(payload):
    if not bot_on_message:
        return

    message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
    emoji = payload.emoji.name
    reaction = discord.utils.get(message.reactions, emoji=emoji)
    user = payload.member
    
    await manage_reaction_add(user, message, reaction, emoji)

async def manage_reaction_add(user, message, reaction, emoji):
    try:
        global list_alerts_sent_to_admin

        #prevent reacting to bot's reactions
        if user == bot.user:
            return

        if isinstance(message.channel, DMChannel):
            guild_name = "DM"
            channel_name = "DM"
        else:
            guild_name = message.channel.guild.name
            channel_name = guild_name+"/"+message.channel.name

        author = message.author.display_name
        goutils.log2("DBG", "guild_name: "+guild_name)
        goutils.log2("DBG", "message: "+str(message.content))
        goutils.log2("DBG", "author of the message: "+str(author))
        if len(emoji)==1:
            goutils.log2("DBG", "emoji: "+str(emoji)+" (unicode: "+hex(ord(emoji))+")")
        else:
            goutils.log2("DBG", "emoji: "+str(emoji))
        goutils.log2("DBG", "user of the reaction: "+str(user))

        # Manage cycle arrows to re-launch a command
        if emoji == emojis.cyclearrows:
            # re-launch the command if it is a gobot command, originally launched by the author of the reaction
            lower_msg = message.content.lower().strip()
            #print(lower_msg)
            #print(lower_msg.startswith("go.") , message.author==user)
            if lower_msg.startswith("go.") and message.author==user:
                #remove user reaction, add temporary hourglass from bot
                await message.remove_reaction(emojis.cyclearrows, user)
                await message.add_reaction(emojis.hourglass)

                command_name = lower_msg.split(" ")[0].split(".")[1]
                goutils.log2("INFO", "Command "+message.content+" re-launched by "+user.display_name+" in "+channel_name)

                try:
                    await bot.process_commands(message)
                except Exception as e:
                    goutils.log2("ERR", traceback.format_exc())
                    if not bot_test_mode:
                        await send_alert_to_admins(message.channel.guild, "Exception in guionbot_discord.message_reaction_add:"+str(sys.exc_info()[0]))

                #remove hourglass, add the cyclearrow reaction from bot (so it may be reclickable)
                await message.remove_reaction(emojis.hourglass, bot.user)
                await message.add_reaction(emojis.cyclearrows)

        # Manage the thumb up to messages sent to admins
        if message.content in list_alerts_sent_to_admin \
            and emoji == '\N{THUMBS UP SIGN}' \
            and message.author == bot.user:

            list_alerts_sent_to_admin.remove(message.content)
            await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')
            goutils.log2("DBG", "remaining messages to admin: "+str(list_alerts_sent_to_admin))

        #Manage reactions to PGS messages
        for [rgt_user, list_msg_sizes] in list_tw_opponent_msgIDs:
            list_msg = [x[0] for x in list_msg_sizes]
            if message in list_msg:
                if emoji in emojis.letters and rgt_user == user:
                    img1_url = list_msg[0].attachments[0].url
                    img1_size = list_msg_sizes[0][1][0]

                    img2_position = list_msg.index(message)
                    img2_url = message.attachments[0].url
                    img2_sizes = list_msg_sizes[img2_position][1]

                    letter_position = emojis.letters.index(emoji)
                    if img1_url == img2_url:
                        letter_position += 1

                    for msg in list_msg:
                        await msg.delete()
                    list_tw_opponent_msgIDs.remove([rgt_user, list_msg_sizes])

                    image = portraits.get_result_image_from_images(img1_url, img1_size,
                                                                   img2_url, img2_sizes,
                                                                   letter_position)
                    with BytesIO() as image_binary:
                        image.save(image_binary, 'PNG')
                        image_binary.seek(0)
                        new_msg = await message.channel.send(content = "<@"+str(user.id)+"> Tu peux partager et commenter ton résultat",
                               file=File(fp=image_binary, filename='image.png'))

    except Exception as e:
        goutils.log2("ERR", traceback.format_exc())

##############################################################
# Event: on_message
# Parameters: message (discord object)
# Purpose: basic checks before running command
# Output: none
##############################################################
@bot.event
async def on_message(message):
    try:
        if isinstance(message.channel, DMChannel):
            channel_name = "DM"
        else:
            channel_name = message.guild.name+"/"+message.channel.name

        ### basic command management
        lower_msg = message.content.lower().strip()
        if lower_msg.startswith("go."):
            command_name = lower_msg.split(" ")[0].split(".")[1]
            goutils.log2("INFO", "Command "+message.content+" launched by "+message.author.display_name+" in "+channel_name)

            await bot.process_commands(message)

        ### after these are reaction to other messages than commands
        if not bot_on_message:
            return

        ### forwarded messages to the bot in a DM
        if isinstance(message.channel, DMChannel):
            if message.reference!=None \
                and type(message.reference==MessageReference) \
                and message.message_snapshots!=None \
                and len(message.message_snapshots)==1:

                #This is a forwarded message, by DM, to the bot
                snapshot = message.message_snapshots[0]
                #print(snapshot.embeds)
                if snapshot.embeds!=None and len(snapshot.embeds)>0:
                    author_url = ''
                    for embed in snapshot.embeds:
                        dict_embed = embed.to_dict()
                        if "author" in dict_embed \
                            and "url" in dict_embed["author"]:

                            author_url = dict_embed["author"]["url"]

                        if "title" in dict_embed and dict_embed["title"].startswith("Guild registration status for "):
                            register_count = 0
                            for line in dict_embed["description"].split("\n"):
                                ret_re = re.search('(.*) \(([1-9]{9})\): <@!?(\d*)>.*', line)
                                if ret_re == None:
                                    continue
                                
                                player_name = ret_re.group(1)
                                allyCode_txt = ret_re.group(2)
                                discord_id_txt = ret_re.group(3)
                                ec, et = await register.register_player(
                                                    allyCode_txt,
                                                    discord_id_txt,
                                                    message.author.id)
                                if ec != 0:
                                    await message.channel.send("ERR:  et")
                                else:
                                    player_name = et
                                    await message.channel.send("Enregistrement de "+player_name+" réussi > lié au compte <@"+discord_id_txt+">")
                                    register_count +=1
                            await message.channel.send("Enregistrement réussi de "+str(register_count)+" joueurs")

                    if author_url.startswith('https://echobase.app'):
                        #This is a forward from Echostation
                        # Read then apply platoon allocations

                        await allocate_platoons_from_eb_DM(message)

                        return

        #Read messages from Juke's bot
        if message.author.id == config.JBOT_DISCORD_ID:
            player_name = None
            for embed in message.embeds:
                dict_embed = embed.to_dict()

                if 'title' in dict_embed:
                    embed = dict_embed['title']
                    if embed.endswith("'s unit status"):
                        pos_name = embed.index("'s unit status")
                        player_name = embed[:pos_name]

                if player_name!=None and 'description' in dict_embed:
                    embed = dict_embed['description']
                    for line in embed.split('\n'):
                        if "%` for " in line:
                            unlocked = line.startswith(":white_check_mark:")
                            if line.endswith(":star:"):
                                line = line[:-8]
                            line_tab = line.split("`")
                            progress_txt = line_tab[1]
                            progress = int(progress_txt[:-1])
                            pos_name = line.index("%` for ") + 7
                            character_name = line[pos_name:]

                            connect_mysql.update_gv_history("", player_name, character_name, False,
                                                            progress, unlocked, "j.bot")

        #Read messages from WookieBoot
        if message.author.id == config.WOOKIEBOT_DISCORD_ID:
            goutils.log2("DBG", "Detecting WookieBot message...")
            await store_wookiebot_raid_estimates(message)

        #Read messages from Echobot
        if message.author.id == config.EB_DISCORD_ID:
            goutils.log2("INFO", "Detect message from Echobot "+str(message.id))
            for embed in message.embeds:
                dict_embed = embed.to_dict()
                if "author" in dict_embed:
                    embed_author = dict_embed["author"]
                    if "name" in embed_author:
                        author_name = embed_author["name"]
                        if author_name.startswith("Use one of the buttons below"):
                            #This is the EB message after a list of messages for EB allocation
                            # Time to lauch the reading of allocations
                            goutils.log2("INFO", "Read platoons from Echobot "+str(message.id))
                            tbChanRead_id = message.channel.id
                            query = "SELECT guild_id, echostation_id FROM guild_bot_infos " \
                                    "WHERE tbChanRead_id="+str(tbChanRead_id)
                            goutils.log2("DBG", query)
                            db_data = connect_mysql.get_line(query)

                            if db_data==None:
                                #No need to read EchoBot message if the guild is
                                # not registered as using a warbot
                                return

                            guild_id = db_data[0]
                            echostation_id = db_data[1]
                            if guild_id != None:
                                    # Get guild information
                                    ec, et, dict_guild = await connect_rpc.get_guild_data_from_id(guild_id, 1)
                                    if ec != 0:
                                        goutils.log2('ERR', et)
                                    else:
                                        #Get TB info
                                        if not "territoryBattleStatus" in dict_guild:
                                            goutils.log2('WAR', "pas de BT en cours")
                                        else:
                                            tb_defId = dict_guild["territoryBattleStatus"][0]["definitionId"]
                                            dict_tb = data.get("tb_definition.json")
                                            tb_name = dict_tb[tb_defId]["shortname"]
                                            tb_currentRound = dict_guild["territoryBattleStatus"][0]["currentRound"]
                                            tb_currentRoundEndTime = int(dict_guild["territoryBattleStatus"][0]["currentRoundEndTime"])/1000
                                            if (tb_currentRoundEndTime - time.time()) < dict_tb[tb_defId]["phaseDuration"]/2000:
                                                # The allocation is sent close to the end of the round > for next round
                                                eb_phase = tb_currentRound+1
                                            else:
                                                eb_phase = tb_currentRound
                                            goutils.log2("INFO", (tb_currentRound, tb_currentRoundEndTime, time.time(), eb_phase))
                                            tbs_round=tb_name+str(eb_phase)
                                            ec, ret_txt = await get_platoons(guild_id, tbs_round, tbChanRead_id, echostation_id)

    except discord.errors.NotFound as e:
        # original message deleted, no need to try answering or reacting
        pass
    except Exception as e:
        goutils.log2("ERR", traceback.format_exc())
        if not bot_test_mode:
            await send_alert_to_admins(message.channel.guild, "Exception in guionbot_discord.on_message:"+str(sys.exc_info()[0]))

##############################################################
@bot.event
async def on_message_edit(before, after):
    if not bot_on_message:
        return

    try:
        if isinstance(before.channel, DMChannel):
            channel_name = "DM"
        else:
            channel_name = before.guild.name+"/"+before.channel.name

        goutils.log2("INFO", "Message edited by "+before.author.display_name + " in "+channel_name+"\n" +\
                             "BEFORE:\n" + before.content + "\n" +\
                             "AFTER:\n" + after.content)

        #Read messages from WookieBoot
        if after.author.id == config.WOOKIEBOT_DISCORD_ID:
            goutils.log2("DBG", "Detecting WookieBot message edit...")
            await store_wookiebot_raid_estimates(after)

        #Read messages from Echobot
        # NOT IN PROD (with the if False), because reliability not confirmed
        if False and after.author.id == config.EB_DISCORD_ID:
            for embed in after.embeds:
                dict_embed = embed.to_dict()
                if 'description' in dict_embed:
                    description=dict_embed['description']
                    dict_ac_did = None
                    for line in description.split('\n'):
                        ret_re = re.search(".*`(\\d{9})`.*<@(\\d*)>.*", line)
                        if ret_re != None:
                            allyCode_txt = ret_re.group(1)
                            allyCode = int(allyCode_txt)
                            discord_id_txt = ret_re.group(2)
                            discord_id = int(discord_id_txt)
                            goutils.log2("INFO", "register "+allyCode_txt+" to "+discord_id_txt)

                            #Get guild list of ac/id from the first ac in the list
                            if dict_ac_did == None:
                                query = "SELECT players.allyCode, discord_id FROM player_discord " \
                                        "JOIN players ON players.allyCode=player_discord.allyCode " \
                                        "WHERE guildName = (SELECT guildName FROM players WHERE allyCode="+allyCode_txt+") "
                                goutils.log2("INFO", query)
                                db_data = connect_mysql.get_table(query)

                                dict_ac_did = {}
                                for line in db_data:
                                    dict_ac_did[line[0]] = line[1]

                            #Test if already registered
                            already_registered = False
                            if allyCode in dict_ac_did:
                                if dict_ac_did[allyCode] == discord_id:
                                    already_registered = True

                            if not already_registered:
                                #Actual registration if not only registered

                                #Setup all potential previous accounts as alt
                                query = "UPDATE player_discord SET main=0 WHERE discord_id='"+discord_id_txt+"'"
                                goutils.log2("INFO", query)
                                #connect_mysql.simple_execute(query)

                                #Add discord id in DB
                                query = "INSERT INTO player_discord (allyCode, discord_id)\n"
                                query+= "VALUES("+allyCode_txt+", "+discord_id_txt+") \n"
                                query+= "ON DUPLICATE KEY UPDATE discord_id="+discord_id_txt+",main=1"
                                goutils.log2("DBG", query)
                                #connect_mysql.simple_execute(query)

                                goutils.log2("INFO", "Registering "+allyCode_txt+" for <@"+discord_id_txt+">")

        #Read messages from FFDroid
        if after.author.id == config.FFDROID_DISCORD_ID:
            ret_re = re.search("Absence registered to (.*): (\d{4}-\d{2}-\d{2}) (\d{4}-\d{2}-\d{2}) :", after.content)
            if ret_re != None:
                player_name = ret_re.group(1)
                start_date = ret_re.group(2)
                end_date = ret_re.group(3)
                caller_id = after.interaction.user.id
                query = "SELECT allyCode FROM players " \
                        "WHERE name='"+player_name+"' " \
                        "AND guildId IN ( " \
                        "   SELECT guildId FROM players " \
                        "   JOIN player_discord ON players.allyCode = player_discord.allyCode " \
                        "   WHERE discord_id="+str(caller_id)+") "
                goutils.log2("DBG", query)
                db_data = connect_mysql.get_value(query)
                if db_data != None:
                    allyCode = db_data

                    query = "INSERT INTO attendency(allyCode, startDate, endDate) " \
                            "VALUES("+str(allyCode)+", '"+start_date+"', '"+end_date+"') "
                    goutils.log2("DBG", query)
                    connect_mysql.simple_execute(query)

                    await after.channel.send("Absence enregistrée pour "+player_name+" entre le "+start_date+" et le "+end_date)

    except Exception as e:
        goutils.log2("ERR", traceback.format_exc())

@bot.event
async def on_message_delete(message):
    if not bot_on_message:
        return

    #Unable to detect who is deleting a message
    if isinstance(message.channel, DMChannel):
        channel_name = "DM"
    else:
        channel_name = message.guild.name+"/"+message.channel.name

    goutils.log2("INFO", "Message deleted in "+channel_name+"\n" +\
                         "BEFORE:\n" + message.content)

# This function is called in on_message and on_message_edit
async def store_wookiebot_raid_estimates(message):
    if message.interaction==None:
        if message.reference==None:
            return
        else:
            goutils.log2("INFO", message.reference)
            previous_msg_id = message.reference.message_id
            goutils.log2("INFO", previous_msg_id)
            previous_msg = await message.channel.fetch_message(previous_msg_id)
            cmd_interaction = previous_msg.interaction
    else:
        cmd_interaction = message.interaction

    if cmd_interaction == None:
        return

    cmd_name = cmd_interaction.name
    #print(cmd_name)
    if cmd_name == "raid guild":
        for attachment in message.attachments:
            goutils.log2("DBG", "Reading attachment...")
            if not attachment.filename.endswith(".csv"):
                continue
            raid_shortname = attachment.filename.split("_")[0]
            if raid_shortname=="krayt":
                raid_name = "kraytdragon"
            elif raid_shortname=="endor":
                raid_name = "speederbike"
            else:
                raid_name = raid_shortname

            goutils.log2("INFO", "Storing raid estimates from WookieBot for raid "+raid_name)
            file_content = await attachment.read()
            file_txt = file_content.decode('utf-8')
            ec, et = go.update_raid_estimates_from_wookiebot(raid_name, file_txt)
            if ec != 0:
                goutils.log2("ERR", et)

    elif cmd_name == "guild ready gl":
        for attachment in message.attachments:
            goutils.log2("DBG", "Reading attachment...")
            if not attachment.filename.endswith(".csv"):
                continue
            gl_shortname = attachment.filename.split("-")[0]
            if gl_shortname=="HONDO":
                gl_name = "GLHONDO"
            else:
                gl_name = gl_shortname

            goutils.log2("INFO", "Storing GV progress from WookieBot for GL "+gl_name)
            file_content = await attachment.read()
            file_txt = file_content.decode('utf-8')
            ec, et = go.update_gl_progress_from_wookiebot(gl_name, file_txt)
            if ec != 0:
                goutils.log2("ERR", et)

##############################################################
# Event: on_error_command
# Parameters: error (error raised by the command)
#             ctx (context of the command)
# Purpose: inform that a command is unknown
# Output: error message to the user
##############################################################
@bot.event
async def on_command_error(ctx, error):
    await ctx.message.add_reaction(emojis.thumb)
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("ERR: commande inconnue")
        await ctx.message.add_reaction(emojis.redcross)
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        cmd_name = ctx.command.name
        await ctx.send("ERR: argument manquant. Consultez l'aide avec go.help "+cmd_name)
        await ctx.message.add_reaction(emojis.redcross)
    elif isinstance(error, commands.errors.UnexpectedQuoteError) \
      or isinstance(error, commands.errors.InvalidEndOfQuotedStringError):
        cmd_name = ctx.command.name
        await ctx.send("ERR: erreur de guillemets. Les guillemets vont pas paires et doivent être précédés ou suivis d'un espace.")
        await ctx.message.add_reaction(emojis.redcross)
    elif isinstance(error, commands.CheckFailure):
        if not bot_test_mode:
            await ctx.send("ERR: commande interdite")
            await ctx.message.add_reaction(emojis.redcross)
    else:
        await ctx.send("ERR: erreur inconnue")
        await ctx.message.add_reaction(emojis.redcross)
        goutils.log2("ERR", traceback.format_exc())

        # discord DM to admins
        await send_alert_to_admins(ctx.guild, "ERR: erreur inconnue "+str(error))
        raise error

@bot.event
async def on_member_update(before, after):
    if before.avatar != after.avatar:
        goutils.log2("INFO", "Avatar change  for "+after.display_name)
    if before.display_name != after.display_name:
        goutils.log2("INFO", "Nickname change \""+before.display_name + "\" to \""+after.display_name+"\"")

@bot.event
async def on_user_update(before, after):
    if before.avatar != after.avatar:
        goutils.log2("INFO", "Avatar change  for "+after.display_name)
    if before.display_name != after.display_name:
        goutils.log2("INFO", "Nickname change \""+before.display_name + "\" to \""+after.display_name+"\"")

##############################################################
#                                                            #
#       COMMANDES REGOUPEES PAR CATEGORIE (COG)              #
#                                                            #
##############################################################

##############################################################
# Function: <role>_allowed
# Parameters: ctx (objet Contexte)
# Purpose: check is the user linked to ctx has the right role
#          in test mode, only the admins are allowed to launch commands
# Output: True/False
##############################################################
def admin_command(ctx):
    return str(ctx.author.id) in config.GO_ADMIN_IDS.split(' ')

def member_command(ctx):
    is_owner = (str(ctx.author.id) in config.GO_ADMIN_IDS.split(' '))
    return (not bot_test_mode) or is_owner

def officer_command(ctx):
    is_officer = False
    is_server_admin = False

    if ctx.guild != None:
        # Can be an officer only if in a discord server, not in a DM
        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
        if ec==0:
            guild_id = bot_infos["guild_id"]

            query = "SELECT player_discord.discord_id " \
                    "FROM player_discord " \
                    "JOIN players ON player_discord.allyCode = players.allyCode " \
                    "WHERE guildId='"+guild_id+"' " \
                    "AND player_discord.discord_id<>'' AND guildMemberLevel>=3 "
            goutils.log2("DBG", query)
            db_data = connect_mysql.get_column(query)
            if db_data == None:
                list_did = []
            else:
                list_did = db_data

            if ctx.author.id in list_did:
                is_officer = True
        else:
            goutils.log2("DBG", et)


        # Can have the rights if server admin
        is_server_admin = ctx.author.guild_permissions.administrator

    is_owner = (str(ctx.author.id) in config.GO_ADMIN_IDS.split(' '))
    allow_officer = ((is_officer or is_server_admin) and (not bot_test_mode)) or is_owner

    goutils.log2("INFO", [ctx.author.name, is_owner, is_officer, is_server_admin, allow_officer])
    return allow_officer

##############################################################
# Description: contains all background tasks
##############################################################
class Loop60secsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop_60secs.start()

    @tasks.loop(seconds=60)
    async def loop_60secs(self):
        await bot_loop_60secs(self.bot)
    @loop_60secs.before_loop
    async def before_loop_60secs(self):
        await self.bot.wait_until_ready()

class Loop5minutes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop_5minutes.start()

    @tasks.loop(minutes=5)
    async def loop_5minutes(self):
        await bot_loop_5minutes(self.bot)
    @loop_5minutes.before_loop
    async def before_loop_5minutes(self):
        await self.bot.wait_until_ready()

class Loop60minutes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loop_60minutes.start()

    @tasks.loop(minutes=60)
    async def loop_60minutes(self):
        await bot_loop_60minutes(self.bot)
    @loop_60minutes.before_loop
    async def before_loop_60minutes(self):
        await self.bot.wait_until_ready()

##############################################################
# Class: AdminCog
# Description: contains all admin commands
##############################################################
class AdminCog(commands.Cog, name="Commandes pour les admins"):
    def __init__(self, bot):
        self.bot = bot

    ##############################################################
    # Command: cmd
    # Parameters: ctx (objet Contexte), arg (string)
    # Purpose: exécute la commande donnée entre guillemets et renvoie le résultat
    #          ex: go.cmd "ls -ltr CACHE" (bot déployé sous Linux)
    #          ex: go.cmd "dir CACHE" (bot déployé sous Windows)
    # ATTENTION : cette commande peut potentiellement écraser des fichiers
    #            ou perturber fortement le fonctionnement du bot!
    #            (c'est pour ça qu'elle est réservée aux développeurs)
    # Display: output de la ligne de commande, comme dans une console
    ##############################################################
    @commands.command(name='cmd', help='Shell sur le serveur')
    @commands.check(admin_command)
    async def cmd(self, ctx, *args):
        await ctx.message.add_reaction(emojis.thumb)

        arg = " ".join(args)
        stream = os.popen(arg)
        output = stream.read()
        goutils.log("INFO", "go.cmd", 'CMD: ' + arg)
        goutils.log("INFO", "go.cmd", 'output: ' + output)
        for txt in goutils.split_txt(output, MAX_MSG_SIZE):
            await ctx.send('`' + txt + '`')
        await ctx.message.add_reaction(emojis.check)
        
    ##############################################################
    # Command: info
    # Parameters: ctx (objet Contexte)
    # Purpose: affiche un statut si le bot est ON, avec taille du CACHE
    # Display: statut si le bot est ON, avec taille du CACHE
    ##############################################################
    @commands.command(name='info', help='Statut du bot')
    @commands.check(admin_command)
    async def info(self, ctx):
        await ctx.message.add_reaction(emojis.thumb)

        # get the DB information
        query = "SELECT guilds.name AS Guilde, \
                 count(*) as Joueurs, \
                 guilds.lastUpdated as MàJ, \
                 NOT(isnull(guild_bots.period)) as Warbot \
                 FROM guilds \
                 JOIN players ON players.guildId = guilds.id \
                 LEFT JOIN guild_bots ON guild_bots.guild_id = guilds.id \
                 WHERE update_period_hours>0 \
                 GROUP BY guilds.id \
                 ORDER BY guilds.lastUpdated DESC"
        goutils.log2("DBG", query)
        output_players = connect_mysql.text_query(query)
        total_guilds = connect_mysql.get_value("SELECT count(*) from guilds")
        total_players = connect_mysql.get_value("SELECT count(*) from players")

        await ctx.send("**GuiOn bot is UP** since "+str(bot_uptime)+" (GMT)")
        await ctx.send("Guilde suivies :")
        output_txt=""
        for row in output_players:
            output_txt += str(row)+"\n"
        for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
            await ctx.send("``` " + txt[1:] + "```")
        await ctx.send("et au total "+str(total_guilds)+" guildes et "+str(total_players)+" joueur connus")

        await ctx.message.add_reaction(emojis.check)

    ##############################################################
    # Command: sql
    # Parameters: ctx (objet Contexte), arg (string)
    # Purpose: exécute la reqête donnée entre guillemets et renvoie le résultat
    #          ex: go.sql "SELECT * FROM members"
    # ATTENTION : cette commande peut potentiellement modifier la DB
    #            ou perturber fortement le fonctionnement du bot!
    #            (c'est pour ça qu'elle est réservée aux développeurs)
    # Display: output de la requête, s'il y en a un
    ##############################################################
    @commands.command(name='sql', help='Requête SQL dans la database')
    @commands.check(admin_command)
    async def sql(self, ctx, *args):
        await ctx.message.add_reaction(emojis.thumb)

        arg = " ".join(args)
        output = connect_mysql.text_query(arg)
        goutils.log('INFO', 'go.sql', 'SQL: ' + arg)
        if len(output) >0:
            output_txt=''
            for row in output:
                output_txt+=str(row)+'\n'
            goutils.log('INFO', 'go.sql', output_txt)
            for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                await ctx.send('`' + txt + '`')
        else:
            await ctx.send('*Aucun résultat*')
        
        await ctx.message.add_reaction(emojis.check)
        
    ##############################################################
    # Command: fsg
    # Parameters: allyCode
    # Purpose: get latest info from API
    ##############################################################
    @commands.command(name='fsg',
                 brief="Force la synchro API d'une Guilde",
                 help="Force la synchro API d'une Guilde\n\n"\
                      "Exemple: go.fsg 123456789")
    @commands.check(admin_command)
    async def fsg(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            if len(args)!=1:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help fsg")

            allyCode = await manage_me(ctx, args[0], False)
            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
                return

            err_code, err_txt, dguild = await go.load_guild(allyCode, True, True,
                                                  force_update=True)

            await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: fsj
    # Parameters: allyCode
    #             "clearcache" (or any other text)
    # Purpose: get latest info from API, and also clear cache XML if reaquired
    # Display: INFO if new data if different from the previous
    ##############################################################
    @commands.command(name='fsj',
                 brief="Force la synchro API d'un Joueur",
                 help="Force la synchro API d'un Joueur\n\n"\
                      "Exemple: go.fsj 123456789\n"\
                      "Exemple: go.fsj 123456789 Alex 123123123\n"\
                      "Exemple: go.fsj me clearcache")
    @commands.check(admin_command)
    async def fsj(self, ctx, *options):
        await ctx.message.add_reaction(emojis.thumb)

        options = list(options)
        clear_cache = False
        if "clearcache" in options:
            clear_cache = True
            options.remove("clearcache")

        for ac in options:
            allyCode = await manage_me(ctx, ac, False)

            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
                return

            query = "SELECT CURRENT_TIMESTAMP"
            goutils.log2("DBG", query)
            timestamp_before = connect_mysql.get_value(query)
            e, t, player_before = await go.load_player( allyCode, -1, True)
            if e!=0:
                await ctx.send(t)
                await ctx.message.add_reaction(emojis.redcross)
                return

            player_id = player_before["playerId"]
            if clear_cache:
                json_file = "PLAYERS/"+player_id+".json"
                if os.path.isfile(json_file):
                    os.remove(json_file)

            e, t, player_now = await go.load_player(allyCode, 1, False)
            if e!=0:
                await ctx.send(t)
                await ctx.message.add_reaction(emojis.redcross)
                return

            delta_player = goutils.delta_dict_player(player_before, player_now)

            query = "SELECT * FROM roster_evolutions\n"
            query+= "WHERE allyCode="+allyCode+"\n"
            query+= "AND timestamp >= '"+str(timestamp_before)+"'\n"
            query+= "ORDER BY timestamp DESC"
            goutils.log2("DBG", query)

            output = connect_mysql.text_query(query)
            if len(output) >0:
                output_txt=''
                for row in output:
                    output_txt+=str(row)+'\n'
                goutils.log('INFO', 'go.sql', output_txt)
                for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                    await ctx.send('`' + txt + '`')
            else:
                await ctx.send(allyCode + ' : *Aucune mise à jour*')
        
        await ctx.message.add_reaction(emojis.check)


    ##############################################################
    # Command: servers
    # Parameters: Aucun
    # Purpose: affiche les serveurs discord qui utilisent le bot
    # Display: liste Nom / ID
    #############################################################
    @commands.command(name='servers', help='Liste des serveurs discord du bot')
    @commands.check(admin_command)
    async def servers(self, ctx):
        await ctx.message.add_reaction(emojis.thumb)
        output_txt = ""
        for g in bot.guilds:
            for m in g.members:
                if m.guild_permissions.administrator and not m.bot:
                    query = "SELECT allyCode FROM player_discord WHERE discord_id="+str(m.id)
                    db_data = connect_mysql.get_column(query)
                    output_txt += g.name+ " ("+str(g.id)+"), "+m.name+" ("+str(m.id)+"), "+str(m.guild_permissions.administrator)+", "+str(db_data)+"\n"

        for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
            await ctx.send(txt)
        await ctx.message.add_reaction(emojis.check)

    ##############################################################
    # Command: test
    # Parameters: ça dépend...
    # Purpose: commande de test lors du dev. Doit être mise en commentaires
    #          avant déploiement en service
    # Display: ça dépend
    #############################################################
    @commands.command(name='test', help='Réservé aux admins')
    @commands.check(admin_command)
    async def test(self, ctx, *args):
        for g in bot.guilds:
            print(g.name, g.owner)

    @commands.command(name='reactioncheck', help='Liste ceux qui ont raégit à un message')
    @commands.check(admin_command)
    async def reactioncheck(self, ctx, *args):
        await ctx.message.add_reaction(emojis.thumb)

        allyCode = args[0]
        allyCode = await manage_me(ctx, allyCode, False)

        tab_msg = args[1].split('/')
        msg_id = int(tab_msg[-1])
        channel_id = int(tab_msg[-2])
        try:
            channel = bot.get_channel(channel_id)
            msg = await channel.fetch_message(msg_id)
            guild = channel.guild
        except discord.errors.NotFound as e:
            goutils.log2("ERR", "msg not found id="+str(msg_id))
            raise(e)
            await ctx.message.add_reaction(emojis.redcross)
            return
        except Exception as e:
            goutils.log2("ERR", str(sys.exc_info()[0]))
            goutils.log2("ERR", e)
            goutils.log2("ERR", traceback.format_exc())
            await ctx.message.add_reaction(emojis.redcross)
            return

        list_reactive_user_id = []
        for reaction in msg.reactions:
            async for user in reaction.users():
                list_reactive_user_id.append(user.id)
                guild_member = guild.get_member(user.id)
                if guild_member==None:
                    goutils.log2("INFO", f'{user} (NOT IN THE SERVER) has reacted with {reaction.emoji}')

        query = "select name, discord_id from players join player_discord on players.allyCode=player_discord.allyCode where guildName = (select guildName from players where allyCode="+allyCode+")"
        goutils.log2("DBG", query)
        db_data = connect_mysql.get_table(query)
        for line in db_data:
            if line[1]==None:
                goutils.log2("INFO", "No discord ID for "+line[0])
            elif not line[1] in list_reactive_user_id:
                goutils.log2("INFO", line[0]+" has not reacted to the message")

        await ctx.message.add_reaction(emojis.check)

    @commands.check(admin_command)
    @commands.command(name='laeb',
                 brief="Lit des Allocations de EchoBot",
                 help="Lit des Allocations de BT de EchoBot dans le salon dédié\n\n"\
                      "Exemple : go.laeb")
    async def laeb(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            ###########################
            # get platoon allocations
            ##########
            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send('ERR: '+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            tbChannel_id = bot_infos["tbChanRead_id"]
            echostation_id = bot_infos["echostation_id"]
            if tbChannel_id==0:
                await ctx.send('ERR: warbot mal configuré (tbChannel_id=0)')
                await ctx.message.add_reaction(emojis.redcross)
                return

            ec, et, dict_guild = await connect_rpc.get_guild_data_from_id(guild_id, 1)
            if ec != 0:
                await ctx.send('ERR: '+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            if not "territoryBattleStatus" in dict_guild:
                await ctx.send('ERR: pas de BT en cours')
                await ctx.message.add_reaction(emojis.redcross)
                return

            tb_defId = dict_guild["territoryBattleStatus"][0]["definitionId"]
            dict_tb = data.get("tb_definition.json")
            tb_name = dict_tb[tb_defId]["shortname"]
            tb_currentRound = dict_guild["territoryBattleStatus"][0]["currentRound"]
            tb_currentRoundEndTime = int(dict_guild["territoryBattleStatus"][0]["currentRoundEndTime"])/1000
            if (tb_currentRoundEndTime - time.time()) < dict_tb[tb_defId]["phaseDuration"]/2000:
                # The allocation is sent close to the end of the round > for next round
                eb_phase = tb_currentRound+1
            else:
                eb_phase = tb_currentRound
            goutils.log2("INFO", (tb_currentRound, tb_currentRoundEndTime, time.time(), eb_phase))
            tbs_round=tb_name+str(eb_phase)

            ec, ret_txt = await get_platoons(guild_id, tbs_round, tbChannel_id, echostation_id)
            if ec != 0:
                await ctx.send('ERR: '+ret_txt)
                await ctx.message.add_reaction(emojis.redcross)
                return

            await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())

    @commands.check(admin_command)
    @commands.command(name='sync', brief="Synchronise les commands slash")
    async def sync(self, ctx, *arg):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            if len(arg)>0 and arg[0]=="clear":
                clear_commands=True
            else:
                clear_commands=False
            print(clear_commands)

            print("BEFORE - global")
            for g in bot.tree.get_commands():
                if type(g)==app_commands.commands.Command:
                    print(g.name)
                else:
                    for c in g.commands:
                        print(g.name, c.name)

            for guild in bot.guilds:
                print("#####"+guild.name)
                for g in bot.tree.get_commands(guild=guild):
                    if type(g)==app_commands.commands.Command:
                        print(g.name)
                    else:
                        for c in g.commands:
                            print(g.name, c.name)
                bot.tree.clear_commands(guild=guild)
                print("# cleared")
                for g in bot.tree.get_commands(guild=guild):
                    if type(g)==app_commands.commands.Command:
                        print(g.name)
                    else:
                        for c in g.commands:
                            print(g.name, c.name)
                if clear_commands == False:
                    bot.tree.copy_global_to(guild=guild)
                await bot.tree.sync(guild=guild)
                for g in bot.tree.get_commands(guild=guild):
                    if type(g)==app_commands.commands.Command:
                        print(g.name)
                    else:
                        for c in g.commands:
                            print(g.name, c.name)
                print("# synced")

            #bot.tree.clear_commands(guild=None)
            #await bot.tree.sync()
            await ctx.send('End')

            print("AFTER - global")
            for g in bot.tree.get_commands():
                if type(g)==app_commands.commands.Command:
                    print(g.name)
                else:
                    for c in g.commands:
                        print(g.name, c.name)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())

##############################################################
# Class: TwCog - for Google accounts
# Description: contains all slash commands for TW
##############################################################
class TwCog(commands.GroupCog, name="gt"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="statut")
    async def tw_status(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(thinking=True)

            #get player config from DB
            ec, et, player_infos = connect_mysql.get_google_player_info(interaction.channel.id)
            if ec!=0:
                txt = emojis.redcross+" ERR: "+et
                await interaction.edit_original_response(content=txt)
                return

            guild_id = player_infos["guild_id"]
            allyCode = player_infos["allyCode"]
            goutils.log2("INFO", "START "+allyCode+"@"+guild_id)

            err_code, err_txt = await update_rpc_data(guild_id, allyCode=allyCode)
            if err_code != 0:
                txt = emojis.redcross+" ERR: "+err_txt
                await interaction.edit_original_response(content=txt)
                return

            err_code, err_txt, statusChan = await update_tw_status(guild_id, backup_channel_id=interaction.channel.id, allyCode=allyCode)
            if err_code != 0:
                txt = emojis.redcross+" ERR: "+err_txt
                await interaction.edit_original_response(content=txt)
                return

            if statusChan==None:
                txt = emojis.check+" statut GT mis à jour"
            else:
                txt = emojis.check+" statut GT mis à jour dans <#"+str(statusChan)+">"
            await interaction.edit_original_response(content=txt)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

    @app_commands.command(name="stats")
    async def tw_stats(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(thinking=True)

            #get player config from DB
            ec, et, player_infos = connect_mysql.get_google_player_info(interaction.channel.id)
            if ec!=0:
                txt = emojis.redcross+" ERR: "+et
                await interaction.edit_original_response(content=txt)
                return

            guild_id = player_infos["guild_id"]
            allyCode = player_infos["allyCode"]
            goutils.log2("INFO", "START "+allyCode+"@"+guild_id)

            # Run the TW summary
            err_code, ret_txt = await go.print_tw_summary(guild_id, allyCode=allyCode)
            if err_code != 0:
                txt = emojis.redcross+" ERR: "+err_txt
                await interaction.edit_original_response(content=txt)
                return

            # Print the results
            for txt in goutils.split_txt(ret_txt, MAX_MSG_SIZE):
                await interaction.channel.send('`'+txt+'`')

            #Main status for the command
            txt = emojis.check+" stats GT OK"
            await interaction.edit_original_response(content=txt)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

    @app_commands.command(name="défense")
    @app_commands.rename(units="unités")
    async def tw_defense(self, interaction: discord.Interaction,
                         zone: str,
                         units: str):

        await interaction.response.defer(thinking=True)

        #get player config from DB
        ec, et, player_infos = connect_mysql.get_google_player_info(interaction.channel.id)
        if ec!=0:
            txt = emojis.redcross+" ERR: "+et
            await interaction.edit_original_response(content=txt)
            return

        guild_id = player_infos["guild_id"]
        txt_allyCode = str(player_infos["allyCode"])
        goutils.log2("INFO", "START "+txt_allyCode+"@"+guild_id)

        # split units by <space>, preserving quoted strings
        characters = [p.strip('"') for p in re.split("( |\\\".*?\\\"|'.*?')", units) if p.strip()]

        # Launch the actual command
        ec, et = await go.deploy_def_tw(guild_id, txt_allyCode, zone, characters)
        if ec == 0:
            txt = emojis.check+" "+et
            await interaction.edit_original_response(content=txt)
        else:
            await interaction.edit_original_response(content=emojis.redcross+" "+et)

    # Function used to get dynamic list of TW opponents
    async def list_tw_opponents(self, interaction: discord.Interaction, current: str):
        try:
            user_id = interaction.user.id

            query = "SELECT guildId FROM players " \
                    "JOIN player_discord ON player_discord.allyCode=players.allyCode " \
                    "WHERE discord_id="+str(user_id)+" " \
                    "AND main=1"
            goutils.log2("DBG", query)
            db_data = connect_mysql.get_value(query)
            if db_data==None:
                return []

            guild_id = db_data
            goutils.log2("INFO", "START "+guild_id)

            dict_tw_counters = connect_gsheets.load_tw_counters(guild_id, False)
            list_tw_opponents = list(dict_tw_counters.keys())
            filtered_opponents = [app_commands.Choice(name=value, value=value) 
                                  for value in list_tw_opponents if current.lower() in value.lower()]
            filtered_opponents.sort(key=lambda x:x.name)
            if len(filtered_opponents)>25:
                filtered_opponents = filtered_opponents[:25]
            return filtered_opponents

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

    @app_commands.command(name="contres")
    @app_commands.rename(opponent="adversaire")
    @app_commands.autocomplete(opponent=list_tw_opponents)
    async def tw_defense(self, interaction: discord.Interaction,
                         opponent: str):

        try:
            await interaction.response.defer(thinking=True)

            # Launch the actual command
            user_id = interaction.user.id

            query = "SELECT guildId FROM players " \
                    "JOIN player_discord ON player_discord.allyCode=players.allyCode " \
                    "WHERE discord_id="+str(user_id)+" " \
                    "AND main=1"
            goutils.log2("DBG", query)
            db_data = connect_mysql.get_value(query)
            if db_data==None:
                return []

            guild_id = db_data
            goutils.log2("INFO", "START "+guild_id)

            dict_tw_counters = connect_gsheets.load_tw_counters(guild_id, False)
            list_counters = []

            if len(dict_tw_counters[opponent]) > 0:
                embedList = []
                for e in dict_tw_counters[opponent]:
                    if e["Statut"].lower().startswith("top prio"):
                        embed_color = 0xb10202 #red
                    elif e["Statut"].lower().startswith("lux"):
                        embed_color = 0x00ff19 #green
                    elif e["Statut"].lower().startswith("expériment"):
                        embed_color = 0x0a53a8 #blue
                    elif e["Statut"].lower().startswith("clean"):
                        embed_color = 0xff8000 #orange
                    else:
                        embed_color = 0x7e7e7e #gray
                    print(e["Statut"].lower(), embed_color)

                    embed = discord.Embed(title=e["Contre"]+" vs "+opponent, color=embed_color)
                    for key in e.keys():
                        if not key == "Contre":
                            if not e[key].strip() == "":
                                embed.add_field(name=key, value=e[key])

                    embedList.append(embed)

                await interaction.edit_original_response(content="Contres GT vs "+opponent, embeds=embedList)
            else:
                await interaction.edit_original_response(content=emojis.redcross+" aucun contre connu")

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

##############################################################
# Class: TbCog - for Google accounts
# Description: contains all slash commands for Tb
##############################################################
class TbCog(commands.GroupCog, name="bt"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="pose-pelotons")
    async def deploy_platoons(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(thinking=True)

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_google_player_info(interaction.channel.id)
            if ec!=0:
                txt = emojis.redcross+" ERR: "+et
                await interaction.edit_original_response(content=txt)
                return

            guild_id = bot_infos["guild_id"]
            tbChannel_id = bot_infos["tbChanRead_id"]
            echostation_id = bot_infos["echostation_id"]
            if tbChannel_id==0:
                txt = emojis.redcross+" ERR: warbot mal configuré (tbChannel_id=0)"
                await interaction.edit_original_response(content=txt)
                return

            allyCode = bot_infos["allyCode"]
            player_name = bot_infos["player_name"]
            goutils.log2("INFO", "START "+allyCode+"@"+guild_id)

            ec, ret_txt = await check_and_deploy_platoons(guild_id, tbChannel_id, echostation_id, allyCode, player_name, False)
            if ec != 0:
                txt = emojis.redcross+" ERR: "+ret_txt
                await interaction.edit_original_response(content=txt)
            else:
                #filter deployment lines
                lines = ret_txt.split("\n")
                lines = [l for l in lines if "a posé" in l or "n'a pas pu poser" in l or "est verrouillé" in l]
                txt = "\n".join(lines)

                if txt=='':
                    txt = emojis.check+" rien à déployer"
                else:
                    txt = emojis.check+" déploiements effectués :\n"+txt
                await interaction.edit_original_response(content=txt)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")
    @app_commands.command(name="rare-toons")
    async def rare_toons(self, interaction: discord.Interaction,
                         guilde: str="me",
                         liste_zones: str="",
                         joueur: str=""):
        try:
            if liste_zones=='':
                list_zones=[]
            else:
                list_zones = liste_zones.split(" ")
            if joueur=="":
                filter_player=None
            else:
                filter_player=joueur
            await bot_commands.tb_rare_toons(interaction, guilde, list_zones, filter_player)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

    # Function used to get BT open zones, not forbidden
    async def list_allowed_tb_open_zones(self, interaction: discord.Interaction, current: str):
        try:
            user_id = interaction.channel.id

            query = "SELECT SUBSTRING_INDEX(zone_name, '-', -1), cmdCmd FROM tb_zones "\
                    "JOIN tb_history ON tb_history.id = tb_zones.tb_id AND tb_history.current_round=tb_zones.round "\
                    "JOIN players ON players.guildId=tb_history.guild_id "\
                    "JOIN user_bot_infos ON user_bot_infos.allyCode=players.allyCode " \
                    "WHERE channel_id="+str(user_id)+" "\
                    "AND CURRENT_TIMESTAMP < timestampadd(DAY, 6, start_date) "\
                    "AND score < score_step3 "\
                    "ORDER BY lower(name)"
            goutils.log2("DBG", query)
            db_data = connect_mysql.get_table(query)
            if db_data==None:
                return []
            else:
                open_zones = []
                for value, cmdCmd in db_data:
                    if current.lower() in value.lower():
                        if cmdCmd==3:
                            zone_name = emojis.prohibited+value
                        else:
                            zone_name = value
                        open_zones.append(app_commands.Choice(name=zone_name, value=value))

                return open_zones

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

    @app_commands.command(name="déploie")
    @app_commands.rename(list_alias_txt="liste-persos")
    @app_commands.autocomplete(zone=list_allowed_tb_open_zones)
    async def deploy_tb(self, interaction: discord.Interaction,
                        zone: str="",
                        list_alias_txt: str=""):
        try:
            await bot_commands.deploy_tb(interaction, zone, list_alias_txt)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

##############################################################
# Class: ModsCog - for Google accounts
# Description: contains all slash commands for mods
##############################################################
class ModsCog(commands.GroupCog, name="mods"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="modoptimizer")
    async def modoptimizer(self, interaction: discord.Interaction,
                           fichier: discord.Attachment,
                           simulation: bool=False):
        try:
            await interaction.response.defer(thinking=True)

            channel_id = interaction.channel_id

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_google_player_info(interaction.channel.id)
            if ec!=0:
                txt = emojis.redcross+" ERR: "+et
                await interaction.edit_original_response(content=txt)
                return

            txt_allyCode = str(bot_infos["allyCode"])
            goutils.log2("INFO", "START "+txt_allyCode)

            goutils.log2("INFO", "mods.modoptimizer("+txt_allyCode+", fichier="+fichier.filename+", simu="+str(simulation)+")")

            #Run the function
            player_path = "PLAYERDATA/"+txt_allyCode
            if not os.path.isdir(player_path):
                os.mkdir(player_path)
            file_savename = player_path+"/modoptimizer_input.json"
            await fichier.save(file_savename)
            file_content = await fichier.read()
            try:
                json_content = file_content.decode('utf-8')
            except :
                await interaction.edit_original_response(content=emojis.redcross+" ERR impossible de lire le contenu du fichier "+fichier.url)
                return

            ec, et, ret_data = await manage_mods.apply_modoptimizer_allocations(json_content, txt_allyCode, simulation, interaction)
            # Prepare warning info, to be displayed if error or success
            cost_and_missing = ""
            if "cost" in ret_data:
                cost_and_missing += ret_data["cost"]
            if "missing" in ret_data and len(ret_data["missing"])>0:
                for unit in ret_data["missing"]:
                    value=len(ret_data["missing"][unit])
                    if value==1:
                        cost_and_missing += "\n"+emojis.warning+" "+str(value)+" mod ne peut pas être posé sur "+unit+" car ce mod n'existe plus"
                    else:
                        cost_and_missing += "\n"+emojis.warning+" "+str(value)+" mods ne peuvent pas être posés sur "+unit+" car ils n'existent plus"
            if "forbidden" in ret_data and len(ret_data["forbidden"])>0:
                for unit in ret_data["forbidden"]:
                    value=len(ret_data["forbidden"][unit])
                    if value==1:
                        cost_and_missing += "\n"+emojis.warning+" "+str(value)+" mod ne peut pas être posé sur "+unit+" car ce mod est de niveau or pour un perso de gear inférieur à 12"
                    else:
                        cost_and_missing += "\n"+emojis.warning+" "+str(value)+" mods ne peuvent pas être posés sur "+unit+" car ces mods sont de niveau or pour un perso de gear inférieur à 12"

            if ec == 0:
                # The cost gets a SUCCESS sign
                txt = emojis.check+" "+ cost_and_missing
                if simulation:
                    txt = "[SIMULATION]"+txt
                if len(txt)>1000:
                    txt=txt[:1000]+"..."
                try:
                    await interaction.edit_original_response(content=txt)
                except discord.errors.HTTPException as e:
                    await interaction.message.channel.send(content=txt)
            else:
                err_txt = emojis.redcross+" "+et

                # error happening in the middle of a simulation does not display cost
                # simulation going to its end but failing displays cost
                if not simulation or ec==2:
                    if len(cost_and_missing) > 0:
                        err_txt += "\n "+cost_and_missing
                    if len(err_txt)>1000:
                        err_txt=err_txt[:1000]+"..."

                if not interaction.is_expired():
                    await interaction.edit_original_response(content=err_txt)
                else:
                    # Interaction expired, send a message in the channel
                    output_channel = bot.get_channel(channel_id)
                    await output_channel.send(content=err_txt)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

    @app_commands.command(name="enregistre-conf")
    @app_commands.rename(conf_name="nom-conf")
    @app_commands.rename(list_alias_txt="liste-persos")
    async def save_conf(self, interaction: discord.Interaction,
                           conf_name: str,
                           list_alias_txt: str):
        try:
            await interaction.response.defer(thinking=True)

            channel_id = interaction.channel_id

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_google_player_info(interaction.channel.id)
            if ec!=0:
                txt = emojis.redcross+" ERR: "+et
                await interaction.edit_original_response(content=txt)
                return

            txt_allyCode = str(bot_infos["allyCode"])
            conf_name = conf_name.strip()

            goutils.log2("INFO", "mods.save_conf("+txt_allyCode+", conf_name="+conf_name+", persos="+list_alias_txt+")")

            #transform list_alias parameter into list
            list_alias = list_alias_txt.split(" ")
            while "" in list_alias:
                list_alias.remove("")

            #Check if conf already exists
            query = "SELECT name FROM mod_config_list " \
                    "JOIN user_bot_infos ON user_bot_infos.allyCode=mod_config_list.allyCode " \
                    "WHERE channel_id="+str(channel_id)+" "\
                    "AND lower(name)='"+conf_name.lower()+"'"
            goutils.log2("DBG", query)
            db_data = connect_mysql.get_column(query)
            if len(db_data) > 0:
                user_choice = await bot_commands.confirmationPrompt(interaction, "Voulez-vous écrasez la conf "+conf_name+" ?")
                if user_choice == False:
                    await interaction.edit_original_response(content=emojis.redcross+" enregistrement annulé")

            #Run the function
            ec, et = await manage_mods.create_mod_config(conf_name, txt_allyCode, list_alias)

            if ec == 0:
                await interaction.edit_original_response(content=emojis.check+" "+et)
            else:
                await interaction.edit_original_response(content=emojis.redcross+" "+et)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

    # Function used to get dynamic parameters in applique-conf and delete-conf
    async def list_player_configurations(self, interaction: discord.Interaction, current: str):
        try:
            user_id = interaction.channel.id

            query = "SELECT name FROM mod_config_list " \
                    "JOIN user_bot_infos ON user_bot_infos.allyCode=mod_config_list.allyCode " \
                    "WHERE channel_id="+str(user_id)+" "\
                    "ORDER BY lower(name)"
            goutils.log2("DBG", query)
            db_data = connect_mysql.get_column(query)
            if db_data==None:
                return []
            else:
                filtered_confs = [app_commands.Choice(name=value, value=value) 
                                  for value in db_data if current.lower() in value.lower()]
                return filtered_confs

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

    @app_commands.command(name="applique-conf")
    @app_commands.rename(conf_name="nom-conf")
    @app_commands.autocomplete(conf_name=list_player_configurations)
    async def apply_conf(self, interaction: discord.Interaction,
                         conf_name: str,
                         simulation: bool=False):
        try:
            await interaction.response.defer(thinking=True)

            channel_id = interaction.channel_id

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_google_player_info(interaction.channel.id)
            if ec!=0:
                txt = emojis.redcross+" ERR: "+et
                await interaction.edit_original_response(content=txt)
                return

            txt_allyCode = str(bot_infos["allyCode"])

            goutils.log2("INFO", "mods.apply_conf("+txt_allyCode+", conf_name="+conf_name+", simu="+str(simulation)+")")

            #Run the function
            ec, et, ret_data = await manage_mods.apply_config_allocations(conf_name, txt_allyCode, simulation, interaction)

            # Prepare warning info, to be displayed if error or sucess
            cost_and_missing = ""
            if "cost" in ret_data:
                cost_and_missing += ret_data["cost"]
            if "missing" in ret_data and len(ret_data["missing"])>0:
                for unit in ret_data["missing"]:
                    value=len(ret_data["missing"][unit])
                    if value==1:
                        cost_and_missing += "\n"+emojis.warning+" "+str(value)+" mod ne peut pas être posé sur "+unit+" car ce mod n'existe plus"
                    else:
                        cost_and_missing += "\n"+emojis.warning+" "+str(value)+" mods ne peuvent pas être posés sur "+unit+" car ils n'existent plus"
            if "forbidden" in ret_data and len(ret_data["forbidden"])>0:
                for unit in ret_data["forbidden"]:
                    value=len(ret_data["forbidden"][unit])
                    if value==1:
                        cost_and_missing += "\n"+emojis.warning+" "+str(value)+" mod ne peut pas être posé sur "+unit+" car ce mod est de niveau or pour un perso de gear inférieur à 12"
                    else:
                        cost_and_missing += "\n"+emojis.warning+" "+str(value)+" mods ne peuvent pas être posés sur "+unit+" car ces mods sont de niveau or pour un perso de gear inférieur à 12"

            if ec == 0:
                # The cost gets a SUCCESS sign
                txt = emojis.check+" "+ cost_and_missing
                if simulation:
                    txt = "[SIMULATION]"+txt
                if len(txt)>1000:
                    txt=txt[:1000]+"..."
                await interaction.edit_original_response(content=txt)
            else:
                err_txt = emojis.redcross+" "+et

                # error happening in the middle of a simulation does not display cost
                # simulation going to its end but failing displays cost
                if not simulation or ec==2:
                    if len(cost_and_missing) > 0:
                        err_txt += "\n "+cost_and_missing
                    if len(err_txt)>1000:
                        err_txt=err_txt[:1000]+"..."
                await interaction.edit_original_response(content=err_txt)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

    @app_commands.command(name="supprime-conf")
    @app_commands.rename(conf_name="nom-conf")
    @app_commands.autocomplete(conf_name=list_player_configurations)
    async def delete_conf(self, interaction: discord.Interaction,
                         conf_name: str):
        try:
            await interaction.response.defer(thinking=True)

            channel_id = interaction.channel_id

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_google_player_info(interaction.channel.id)
            if ec!=0:
                txt = emojis.redcross+" ERR: "+et
                await interaction.edit_original_response(content=txt)
                return

            txt_allyCode = str(bot_infos["allyCode"])

            goutils.log2("INFO", "mods.delete_conf("+txt_allyCode+", conf_name="+conf_name+")")

            #Run the function
            query = "SELECT id FROM mod_config_list WHERE allyCode="+txt_allyCode+" AND name='"+conf_name+"'"
            goutils.log2("DBG", query)
            db_data = connect_mysql.get_value(query)
            if db_data==None:
                await interaction.edit_original_response(content=emojis.redcross+" configuration inconnue")
                return
            config_id = db_data

            query = "DELETE FROM mod_config_content WHERE config_id="+str(config_id)
            goutils.log2("DBG", query)
            db_data = connect_mysql.simple_execute(query)

            query = "DELETE FROM mod_config_list WHERE id="+str(config_id)
            goutils.log2("DBG", query)
            db_data = connect_mysql.simple_execute(query)

            await interaction.edit_original_response(content=emojis.check+" configuration effacée")

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

    @app_commands.command(name="exporte-liste")
    async def export_modoptimizer(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(thinking=True)

            channel_id = interaction.channel_id

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_google_player_info(interaction.channel.id)
            if ec!=0:
                txt = emojis.redcross+" ERR: "+et
                await interaction.edit_original_response(content=txt)
                return

            txt_allyCode = str(bot_infos["allyCode"])

            goutils.log2("INFO", "mods.export_modoptimizer("+txt_allyCode+")")

            #Run the function
            ec, et, dict_export = await manage_mods.get_modopti_export(txt_allyCode)

            if ec != 0:
                await interaction.edit_original_response(content=emojis.redcross+" "+et)
            else:
                export_path="/tmp/modoptiRestoreMyProgress_"+txt_allyCode+".json"
                export_file = open(export_path, "w")
                export_txt = json.dumps(dict_export, indent=4)
                export_file.write(export_txt)
                export_file.close()

                await interaction.edit_original_response(content=emojis.check+" fichier prêt", 
                                                         attachments=[discord.File(export_path)])

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")
    @app_commands.command(name="level-up")
    @app_commands.rename(only_speed_sec="avec-secondaire-vitesse")
    @app_commands.rename(with_inventory="avec-inventaire")
    @app_commands.rename(target_level="niveau")
    @app_commands.choices(target_level=[
        app_commands.Choice(name="12", value=12),
        app_commands.Choice(name="15", value=15)])
    async def upgrade_mod_level_up(self, interaction: discord.Interaction,
                                      target_level: int,
                                      simulation: bool=False,
                                      only_speed_sec: bool=False,
                                      with_inventory: bool=False):
        try:
            await bot_commands.upgrade_mod_level(
                        interaction,
                        target_level,
                        simulation,
                        only_speed_sec,
                        with_inventory)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")
    @app_commands.command(name="pose-inventaire")
    async def allocate_random_mods(self, interaction: discord.Interaction):
        try:
            await bot_commands.allocate_random_mods(interaction)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

##############################################################
# Class: BronziumCog - for Google accounts
# Description: one command to open bronzium packs
##############################################################
class BronziumCog(commands.GroupCog, name="bronzium"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="ouvrir")
    @app_commands.rename(quantity="quantité")
    async def bronzium_open(self, interaction: discord.Interaction, quantity: int):
        try:
            await bot_commands.bronzium_open(interaction, quantity)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await interaction.edit_original_response(content=emojis.redcross+" erreur inconnue")

##############################################################
# Class: AuthCog - for connected accounts
# Description: contains all slash commands for authentication
##############################################################
class AuthCog(commands.GroupCog, name="connect"):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    @app_commands.command(name="envoie-otc")
    async def send_otc(self, interaction: discord.Interaction,
                       code: str):
        try:
            await interaction.response.defer(thinking=True)

            #check option
            code=code.strip()
            if not code.isnumeric() or len(code)!=5:
                txt = emojis.redcross+" ERR: le code '"+code+"' doit être un nombre à 5 chiffres"
                await interaction.edit_original_response(content=txt)
                return


            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_google_player_info(interaction.channel.id)
            if ec!=0:
                txt = emojis.redcross+" ERR: "+et
                await interaction.edit_original_response(content=txt)
                return

            txt_allyCode = str(bot_infos["allyCode"])
            player_name = bot_infos["player_name"]

            ec, ret_txt = await connect_rpc.send_ea_otc(txt_allyCode, code)
            if ec != 0:
                txt = emojis.redcross+" ERR: "+ret_txt
                await interaction.edit_original_response(content=txt)
            else:
                await interaction.edit_original_response(content="Code accepté, vous pouvez utiliser le bot")

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())

##############################################################
# Class: ServerCog
# Description: contains all commands linked to the server and its warbot
##############################################################
class ServerCog(commands.Cog, name="Commandes liées au serveur discord et à son warbot"):
    def __init__(self, bot):
        self.bot = bot

    ##############################################################
    # Command: logs
    # Parameters: "grep" text
    # Purpose: list guild events over the latest 48h, and filter with a text
    # Display: list of events with time
    ##############################################################
    @commands.check(officer_command)
    @commands.command(name='logs', brief="Affiche les logs de guilds",
                                   help ="Affiche les logs de guilde\n" \
                                         "Exemple: go.logs\n" \
                                         "Exemple: go.logs Chaton72\n" \
                                         "Exemple: go.logs a perdu\n" \
                                         "Exemple: go.logs -graph      # avec un graphique")
    async def logs(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            case_sensitive = False
            display_graph = False
            args = list(args)
            loop_args = list(args)
            for arg in loop_args:
                if arg == "-graph":
                    display_graph = True
                    args.remove(arg)

            text_grep = " ".join(args)

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send('ERR: '+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            connected_allyCode = bot_infos["allyCode"]

            # Launch the actual command
            ec, et, ret_data = await connect_rpc.get_guildLog_messages(guild_id, False, 1, allyCode=connected_allyCode)
            if ec != 0:
                await ctx.send(et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            list_chat_events = ret_data["CHAT"][1]
            list_tw_events = ret_data["TW"][1]
            list_tb_events = ret_data["TB"][1]

            list_logs = list_chat_events + list_tw_events + list_tb_events

            #Sort by time
            list_logs = sorted(list_logs)

            if case_sensitive:
                list_logs = [x for x in list_logs if text_grep in x[1]]
            else:
                list_logs = [x for x in list_logs if text_grep.lower() in x[1].lower()]

            #Keep max 100 latest
            list_logs = list_logs[-100:]

            #display
            output_txt = ""
            for line in list_logs:
                ts = line[0]
                txt = line[1]
                ts_txt = datetime.datetime.fromtimestamp(int(ts/1000)).strftime("%d/%m %H:%M")
                output_txt+=ts_txt+" - "+txt+"\n"

            for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                await ctx.send('`'+txt+'`')

            #optional graph
            if display_graph:
                list_log_timestamps = [int(x[0]/1000) for x in list_logs]
                image = go.get_distribution_graph(list_log_timestamps, None, 30, None, None,
                                                  "Evénements", "Date", "Nombre", "", "", 
                                                  ts_to_date=True)
                with BytesIO() as image_binary:
                    image.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    await ctx.send(content = "",
                        file=File(fp=image_binary, filename='image.png'))

            await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: vdp
    # Parameters: [optionnel] nom du channel où écrire les résultats (sous forme "#nom_du_channel")
    # Purpose: Vérification du déploiements de Pelotons
    # Display: Une ligne par erreur détectée "JoueurX n'a pas posé persoY en pelotonZ"
    #          avec un groupement par phase puis un tri par joueur
    ##############################################################
    @commands.check(officer_command)
    @commands.command(name='vdp',
                 brief="Vérification des pelotons en BT",
                 help="Vérification de Déploiement des Pelotons en BT\n\n"\
                      "Exemple : go.vdp > liste les déploiements dans le salon courant\n"\
                      "Exemple : go.vdp #batailles-des-territoires > liste les déploiements dans le salon spécifié\n"\
                      "Exemple : go.vdp deploybot\n" \
                      "Exemple : go.vdp -free=DS:1,2,4/MS:3,5/LS")
    async def vdp(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            #Gestion des paramètres : "deploybot" ou le nom d'un salon
            display_mentions=False
            output_channel = ctx.message.channel
            deploy_bot=False
            free_platoons=False

            # Read command options
            output_channel = ctx.message.channel
            display_mentions=False
            targets_platoons = None
            args=list(args)
            loop_args = list(args)
            for arg in loop_args:
                if arg == "deploybot":
                    deploy_bot=True
                    args.remove(arg)
                if arg.startswith("-free"):
                    free_platoons = True
                    if "=" in arg:
                        targets_platoons = arg.split('=')[1]
                    args.remove(arg)
                if arg.startswith('<#') or arg.startswith('https://discord.com/channels/'):
                    got_channel, err_msg = await get_channel_from_channelname(ctx, arg)
                    if got_channel == None:
                        await ctx.send('**ERR**: '+err_msg)
                    else:
                        output_channel = got_channel
                        display_mentions=True
                    args.remove(arg)
            
            list_zones = args

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send(et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            connected_allyCode = bot_infos["allyCode"]
            tbChannel_id = bot_infos["tbChanRead_id"]
            echostation_id = bot_infos["echostation_id"]

            if deploy_bot:
                deploy_allyCode = bot_infos["allyCode"]
                player_name = bot_infos["player_name"]
            else:
                deploy_allyCode = None
                player_name = None

            ec, ret_txt = await check_and_deploy_platoons(guild_id, tbChannel_id, echostation_id, 
                                                          deploy_allyCode, player_name, display_mentions, 
                                                          filter_zones=list_zones,
                                                          connected_allyCode=connected_allyCode,
                                                          free_platoons=free_platoons,
                                                          targets_free_platoons=targets_platoons)
            if ec != 0:
                await ctx.send('ERR: '+ret_txt)
                await ctx.message.add_reaction(emojis.redcross)
            else:
                for txt in goutils.split_txt(ret_txt, MAX_MSG_SIZE):
                    await output_channel.send(txt)

                await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)
        
    #######################################
    @commands.command(name='bot.enable',
            brief="Active le compte warbot",
            help="Active le compte bot pour permettre de suivre la guilde")
    async def botenable(self, ctx, *args):
        await ctx.message.add_reaction(emojis.thumb)

        #Ensure command is launched from a server, not a DM
        if ctx.guild == None:
            query = "SELECT guildId FROM player_discord "\
                    "JOIN guild_bots ON guild_bots.allyCode=player_discord.allyCode "\
                    "JOIN players ON players.allyCode=player_discord.allyCode "\
                    "WHERE discord_id="+str(ctx.author.id)
            goutils.log2("DBG", query)
            db_data = connect_mysql.get_column(query)
            if db_data == None:
                await ctx.send('ERR: vous ne contrôlez pas de warbot')
                await ctx.message.add_reaction(emojis.redcross)
                return

            if len(db_data)>1:
                await ctx.send("ERR: vous contrôlez plus d'un warbot")
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = db_data[0]

            ec, et, bot_infos = connect_mysql.get_warbot_info_from_guild(guild_id)

        else:
            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
        if ec!=0:
            await ctx.send('ERR: '+et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        guild_id = bot_infos["guild_id"]
        guild_name = bot_infos["guild_name"]

        # Launch the actual command
        ec, et = await connect_rpc.unlock_bot_account(guild_id)
        if ec != 0:
            await ctx.send(et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        await ctx.send("Bot de la guilde "+guild_name+" activé > suivi de guilde OK")
        await ctx.message.add_reaction(emojis.check)

    @commands.command(name='bot.disable',
            brief="Désactive le compte warbot",
            help="Désactive le compte bot pour permettre de le jouer")
    async def botdisable(self, ctx, *args):
        await ctx.message.add_reaction(emojis.thumb)

        #Ensure command is launched from a server, not a DM
        if ctx.guild == None:
            await ctx.send('ERR: commande non autorisée depuis un DM')
            await ctx.message.add_reaction(emojis.redcross)
            return

        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
        if ec!=0:
            await ctx.send('ERR: '+et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        guild_id = bot_infos["guild_id"]
        guild_name = bot_infos["guild_name"]

        # Launch the actual command
        ec, et = await connect_rpc.lock_bot_account(guild_id)
        if ec != 0:
            await ctx.send(et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        await ctx.send("Bot de la guilde "+guild_name+" désactivé > prêt à jouer")
        await ctx.message.add_reaction(emojis.check)

    @commands.command(name='bot.jointw',
            brief="Inscrit le bot à la GT",
            help="Inscrit le bot à la GT en cours")
    async def botjointw(self, ctx, *args):
        await ctx.message.add_reaction(emojis.thumb)

        #Ensure command is launched from a server, not a DM
        if ctx.guild == None:
            await ctx.send('ERR: commande non autorisée depuis un DM')
            await ctx.message.add_reaction(emojis.redcross)
            return

        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
        if ec!=0:
            await ctx.send('ERR: '+et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        guild_id = bot_infos["guild_id"]

        # Launch the actual command
        ec, et = await connect_rpc.join_tw(guild_id)
        if ec != 0:
            await ctx.send(et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        await ctx.send(et)
        await ctx.message.add_reaction(emojis.check)

    @commands.command(name='bot.deftw',
                      brief="Défense GT pour le warbot",
                      help="Pose des teams en défense GT pour le warbot")
    async def botdeftw(self, ctx, zone, *characters):
        await ctx.message.add_reaction(emojis.thumb)

        #Ensure command is launched from a server, not a DM
        if ctx.guild == None:
            await ctx.send('ERR: commande non autorisée depuis un DM')
            await ctx.message.add_reaction(emojis.redcross)
            return

        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
        if ec!=0:
            await ctx.send('ERR: '+et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        guild_id = bot_infos["guild_id"]
        txt_allyCode = str(bot_infos["allyCode"])

        # Launch the actual command
        ec, et = await go.deploy_def_tw(guild_id, txt_allyCode, zone, characters)
        if ec != 0:
            await ctx.send(et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        await ctx.send(et)
        await ctx.message.add_reaction(emojis.check)

    @commands.command(name='bot.lastdeftw',
                      brief="Précédente défense GT pour le warbot",
                      help="Affiche les défenses de la dernière fois, pour aider à poser des teams en défense GT pour le warbot")
    async def lastbotdeftw(self, ctx):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send('ERR: '+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            txt_allyCode = str(bot_infos["allyCode"])

            # Launch the actual command
            ec, et = await go.get_previous_tw_defense(txt_allyCode, guild_id, "go.bot.deftw {0} {1}")
            if ec != 0:
                await ctx.send(et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            txt_lines = et.split('\n')
            for txt_line in txt_lines:
                if txt_line.strip() != "":
                    await ctx.send(txt_line)
            await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    #######################################################
    # Deploy the toon(s) represented by caracters in the zone in TB
    # IN: zone (DS, LS, DS or top, mid, bot)
    # IN: list_alias_txt ("ugnaught JTR" or "tag:s:all" or "all" or "tag:darkside")
    #######################################################
    @commands.command(name='bot.deploytb',
            brief="Déploie le warbot en BT",
            help="Déploie des persos en BT")
    async def botdeploytb(self, ctx, zone, list_alias_txt):
        try:
            await bot_commands.deploy_tb(ctx, zone, list_alias_txt)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    @commands.check(officer_command)
    @commands.command(name='tbrappel',
            brief="Tag les joueurs qui n'ont pas tout déployé en BT",
            help="go.tbrappel > tag les joueurs qui n'ont pas tout déployé")
    async def tbrappel(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            display_mentions=False
            output_channel = ctx.message.channel

            #Sortie sur un autre channel si donné en paramètre
            args = list(args)
            output_channel = ctx.message.channel
            display_mentions=False
            tag_officers=True
            ignored_allyCodes=[]
            for arg in args:
                if arg.startswith('<#') or arg.startswith('https://discord.com/channels/'):
                    output_channel, err_msg = await get_channel_from_channelname(ctx, arg)
                    display_mentions=True
                    if output_channel == None:
                        await ctx.send('**ERR**: '+err_msg)
                        output_channel = ctx.message.channel
                        display_mentions=False

                elif arg == "-off":
                    tag_officers=False

                elif arg.startswith('-i'):
                    player_alias_txt = arg.split('=')[1]
                    ret_data = await manage_me(ctx, player_alias_txt, False)

                    if ret_data[0:3] == 'ERR':
                        await ctx.send(ret_data)
                        await ctx.message.add_reaction(emojis.redcross)
                        return

                    if type(ret_data)==str:
                        ignored_allyCodes = [ret_data]
                    else:
                        ignored_allyCodes = ret_data

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send("ERR: "+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            connected_allyCode = bot_infos["allyCode"]

            # Launch the actual command
            err_code, ret_txt, ret_data = await connect_rpc.tag_tb_undeployed_players(
                                                     guild_id, 0, 
                                                     ignored_allyCodes=ignored_allyCodes,
                                                     allyCode=connected_allyCode)
            if err_code == 0:
                lines = ret_data["lines_player"]
                endTime = ret_data["round_endTime"]
                dict_players_by_IG = connect_mysql.load_config_players(guild_id=guild_id)[0]
                expire_time_txt = datetime.datetime.fromtimestamp(int(endTime/1000)).strftime("le %d/%m/%Y à %H:%M")
                output_txt="Joueurs n'ayant pas tout déployé en BT (fin du round "+expire_time_txt+"): \n"
                if len(lines)>0:
                    for [p, txt] in sorted(lines, key=lambda x: x[0].lower()):
                        if display_mentions and (p in dict_players_by_IG):
                            if not tag_officers and dict_players_by_IG[p][2]:
                                p_name= "**" + p + "**"
                            else:
                                p_name = dict_players_by_IG[p][1]
                        else:
                            p_name= "**" + p + "**"
                        output_txt += p_name+": "+txt+"\n"

                    # Total
                    output_txt += "\n__Total__ : "+ret_data["total"]

                else:
                    output_txt += "Aucun"

                for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                    await output_channel.send(txt)

                await ctx.message.add_reaction(emojis.check)
            else:
                await ctx.send(ret_txt)
                await ctx.message.add_reaction(emojis.redcross)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    #######################################################
    # twrappel: creates a reminder for players not enough active in TW
    # IN (optional): channel ID to post the reminder, with discord tags
    #######################################################
    @commands.check(officer_command)
    @commands.command(name='twrappel',
            brief="Tag les joueurs selon leur participation en GT",
            help="go.twrappel     > [phase d'inscription] tag les joueurs qui ne ont pas inscrits\n" \
                 "go.twrappel 3 2 > [phase de def] tag les joueurs qui ont posé moins de 3 escouades au sol ou moins de 2 en vaisseaux\n" \
                 "go.twrappel 3 2 > [phase d'attaque] tag les joueurs qui ont fait moins de 3 attaques au sol ou moins de 2 en vaisseaux\n" \
                 "go.twrappel <options> #salon > envoie lebresultat dans #salon")
    async def twrappel(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            #Sortie sur un autre channel si donné en paramètre
            output_channel = ctx.message.channel
            display_mentions=False
            args = list(args)
            loop_args = list(args)
            for arg in loop_args:
                if arg.startswith('<#') or arg.startswith('https://discord.com/channels/'):
                    output_channel, err_msg = await get_channel_from_channelname(ctx, arg)
                    display_mentions=True
                    if output_channel == None:
                        await ctx.send('**ERR**: '+err_msg)
                        output_channel = ctx.message.channel
                        display_mentions=False
                    args.remove(arg)

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send("ERR: "+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            connected_allyCode = bot_infos["allyCode"]
            fulldef_detection = bot_infos["twFulldefDetection"]

            # Launch the actual command
            err_code, err_txt, ret_data = await go.get_tw_insufficient_attacks(guild_id, args, allyCode=connected_allyCode, fulldef_detection=fulldef_detection)
            if err_code == 0:
                dict_players_by_IG = connect_mysql.load_config_players(guild_id=guild_id)[0]

                if type(ret_data) == dict:
                    d_attacks = ret_data
                    output_txt="La guilde a besoin de vous pour la GT svp : \n"
                    for [p, values] in sorted(d_attacks.items(), key=lambda x: (x[1][2], x[0])):
                        char_attacks = values[0]
                        ship_attacks = values[1]
                        fulldef = values[2]

                        if (p in dict_players_by_IG) and fulldef!=1 and display_mentions:
                            p_name = dict_players_by_IG[p][1]
                        else:
                            #No tag for full defs
                            p_name= "**" + p + "**"

                        if char_attacks==None and ship_attacks==None:
                            #Nothing to report
                            continue
                        elif char_attacks!=None and ship_attacks!=None:
                            output_txt_player = p_name+": "+str(char_attacks)+" toons et "+str(ship_attacks)+" vaisseaux"
                        elif char_attacks==None and ship_attacks!=None:
                            output_txt_player = p_name+": "+str(ship_attacks)+" vaisseaux"
                        else: #char_attacks!=None and ship_attacks==None:
                            output_txt_player = p_name+": "+str(char_attacks)+" toons"

                        if fulldef==1:
                            output_txt_player += " >> détecté full def"
                        elif fulldef==0:
                            output_txt_player += " >> peut-être full def"

                        output_txt += output_txt_player+"\n"
                else: # type = list
                    list_inactive_players = ret_data
                    if len(list_inactive_players)== 0:
                        output_txt="Tous les joueurs sont inscrits à la GT"
                    else:
                        output_txt="N'oubliez pas de vous inscrire pour la GT svp : \n"
                        for p in list_inactive_players:
                            if display_mentions:
                                if p in dict_players_by_IG:
                                    p_name = dict_players_by_IG[p][1]
                                else:
                                    p_name= "**" + p + "**"
                            else:
                                p_name= "**" + p + "**"
                            output_txt += p_name+"\n"

                for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                    await output_channel.send(txt)

                await ctx.message.add_reaction(emojis.check)

            elif err_code==2:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help twrappel")
                await ctx.message.add_reaction(emojis.redcross)
            else:
                await ctx.send(err_txt)
                await ctx.message.add_reaction(emojis.redcross)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    #######################################################
    # coliseum: list coliseum daily scores
    #######################################################
    @commands.check(officer_command)
    @commands.command(name='coliseum',
            brief="Affiche les scores du jour au Colisée",
            help="go.coliseum")
    async def coliseum(self, ctx):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send("ERR: "+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            connected_allyCode = bot_infos["allyCode"]

            # Launch the actual command
            err_code, ret_txt = await go.print_coliseum_guild(
                                            guild_id, 
                                            allyCode=connected_allyCode)
            if err_code == None:
                await ctx.send("ERR: "+txt)
                await ctx.message.add_reaction(emojis.redcross)
                return

            #for txt in goutils.split_txt(ret_txt, MAX_MSG_SIZE):
            #    await ctx.send('```'+txt+'```')

            #Create image from table
            ec, et, image = portraits.get_image_from_texttable(ret_txt)
            with BytesIO() as image_binary:
                image.save(image_binary, 'PNG')
                image_binary.seek(0)
                await ctx.send(file=File(fp=image_binary, filename='image.png'))

            await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    #######################################################
    # raidrappel: creates a reminder for players not enough active in raid
    # IN (optional): channel ID to post the reminder, with discord tags
    #######################################################
    @commands.check(officer_command)
    @commands.command(name='raidrappel',
            brief="Tag les joueurs qui n'ont pas assez attaqué en raid",
            help="go.raidrappel    > tag les joueurs sous 50% par défaut\n" \
                 "go.raidrappel 80 > tag les joueurs sous 80%")
    async def raidrappel(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            #Sortie sur un autre channel si donné en paramètre
            args = list(args)
            output_channel = ctx.message.channel
            use_tags = False
            ignored_allyCodes = []
            for arg in args:
                if arg.startswith('<#') or arg.startswith('https://discord.com/channels/'):
                    output_channel, err_msg = await get_channel_from_channelname(ctx, arg)
                    use_tags = True
                    if output_channel == None:
                        await ctx.send('**ERR**: '+err_msg)
                        output_channel = ctx.message.channel
                        use_tags = True
                    args.remove(arg)
                elif arg.startswith('-i'):
                    player_alias_txt = arg.split('=')[1]
                    ret_data = await manage_me(ctx, player_alias_txt, False)

                    if ret_data[0:3] == 'ERR':
                        await ctx.send(ret_data)
                        await ctx.message.add_reaction(emojis.redcross)
                        return

                    if type(ret_data)==str:
                        ignored_allyCodes = [ret_data]
                    else:
                        ignored_allyCodes = ret_data
                    args.remove(arg)

            target_progress=50
            if len(args) == 1:
                if not args[0].isnumeric():
                    await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help raidrappel")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                target_progress=int(args[0])
                if target_progress<0:
                    target_progress=0
                if target_progress>100:
                    target_progress=100
            elif len(args) > 1:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help raidrappel")
                await ctx.message.add_reaction(emojis.redcross)
                return

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send("ERR: "+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            connected_allyCode = bot_infos["allyCode"]

            # Launch the actual command
            (raid_id, 
            expire_time, 
            list_inactive_players, 
            guild_score, 
            potential_score) = await connect_rpc.get_raid_status(
                                        guild_id, 
                                        target_progress, 
                                        True, 
                                        allyCode=connected_allyCode,
                                        ignored_allyCodes=ignored_allyCodes)
            if raid_id == None:
                await ctx.send("Aucun raid en cours")
                await ctx.message.add_reaction(emojis.redcross)
                return

            dict_players_by_IG = connect_mysql.load_config_players(guild_id=guild_id)[0]
            expire_time_txt = datetime.datetime.fromtimestamp(int(expire_time/1000)).strftime("le %d/%m/%Y à %H:%M")
            score_txt = str(int(guild_score/100000)/10)
            output_txt = "La guilde a besoin de vous pour le raid "+raid_id+" qui se termine "+expire_time_txt+" svp (score actuel = "+score_txt+" M"

            if potential_score == None:
                output_txt += ") : \n"
            else:
                potential_score_txt = str(int(potential_score/100000)/10)
                output_txt += ", "+potential_score_txt+" M si tout le monde atteint "+str(target_progress)+"% de son max) : \n"
            if len(list_inactive_players) > 0 :
                for p in sorted(list_inactive_players, key=lambda x:x["name"].lower()):
                    if use_tags and p["name"] in dict_players_by_IG:
                        p_name = dict_players_by_IG[p["name"]][1]
                    else:
                        p_name= p["name"]

                    output_txt += p_name+" : "+p["status"]+"\n"
            else:
                output_txt += "Tout le monde a joué\n"

            for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                await output_channel.send(txt)

            await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    #######################################################
    # ticketsrappel: creates a reminder for players without required tickets
    # IN (optional): channel ID to post the reminder, with discord tags
    #######################################################
    @commands.check(officer_command)
    @commands.command(name='ticketsrappel',
            brief="Tag les joueurs qui n'ont pas fait leurs tickets",
            help="go.ticketsrappel     > tag les joueurs sous 600 par défaut\n" \
                 "go.ticketsrappel 450 > tag les joueurs sous 450 tickets")
    async def ticketsrappel(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            #Sortie sur un autre channel si donné en paramètre
            args = list(args)
            output_channel = ctx.message.channel
            use_tags = False
            for arg in args:
                if arg.startswith('<#') or arg.startswith('https://discord.com/channels/'):
                    output_channel, err_msg = await get_channel_from_channelname(ctx, arg)
                    use_tags = True
                    if output_channel == None:
                        await ctx.send('**ERR**: '+err_msg)
                        output_channel = ctx.message.channel
                        use_tags = True
                    args.remove(arg)

            required_tickets=600
            if len(args) == 1:
                required_tickets=int(args[0])
                if required_tickets<0:
                    required_tickets=0
                if required_tickets>600:
                    required_tickets=600
            elif len(args) != 0:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help ticketsrappel")
                await ctx.message.add_reaction(emojis.redcross)
                return

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send("ERR: "+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            connected_allyCode = bot_infos["allyCode"]

            # Launch the actual command
            ec, et, list_players, guild_ticket_time = await go.get_ticket_reminder(
                                                         guild_id, 
                                                         required_tickets, 
                                                         allyCode=connected_allyCode)

            if ec!=0:
                await ctx.send("ERR: "+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            dict_players_by_IG = connect_mysql.load_config_players(guild_id=guild_id)[0]
            guild_ticket_time_txt = datetime.datetime.fromtimestamp(guild_ticket_time).strftime("le %d/%m/%Y à %H:%M")
            output_txt = "Pensez à faire vos tickets avant "+guild_ticket_time_txt+" svp\n"

            if len(list_players) > 0 :
                for p in sorted(list_players, key=lambda x:x["name"].lower()):
                    if use_tags and p["name"] in dict_players_by_IG:
                        p_name = dict_players_by_IG[p["name"]][1]
                    else:
                        p_name= p["name"]

                    output_txt += p_name+" : "+str(p["tickets"])+"/"+str(required_tickets)+"\n"
            else:
                output_txt += "Tout le monde a fait ses tickets\n"

            for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                await output_channel.send(txt)

            await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    ####################################################
    # Command tbs
    ####################################################
    @commands.check(officer_command)
    @commands.command(name='tbs',
            brief="Statut de la BT",
            help="Statut de la BT avec les estimations en fonctions des zone:étoiles demandés\n" \
                 "go.tbs DS:1/LS:3/MS:2 -e -p (combats estimés, pelotons prévus)\n" \
                 "go.tbs -ignore=me/chaton75 (joueurs inactifs à ignorer)\n" \
                 "go.tbs DS:1/LS:3/MS:2 -e -p=DS:6/MS:4/LS:0 (combats estimés, 6 pelotons en DS, 4 en MS)\n" \
                 "go.tbs -simu=ROTE DS:1/LS:3/MS:2 -e=DS:55%/MS:70%/LS:60% -p=DS:6/MS:4/LS:0 (simulation de TB de type ROTE)")
    async def tbs(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            # Manage unique command parameters
            options = list(args)
            simulated_tb = None
            output_channel = ctx.message.channel
            ignored_allyCodes = []
            for arg in args:
                if arg.startswith("-s"):
                    if "=" in arg:
                        simulated_tb = arg.split('=')[1]
                    options.remove(arg)
                elif arg.startswith('<#') or arg.startswith('https://discord.com/channels/'):
                    output_channel, err_msg = await get_channel_from_channelname(ctx, arg)
                    display_mentions=True
                    if output_channel == None:
                        await ctx.send('**ERR**: '+err_msg)
                        output_channel = ctx.message.channel
                        display_mentions=False
                    options.remove(arg)
                elif arg.startswith('-i'):
                    player_alias_txt = arg.split('=')[1]
                    ret_data = await manage_me(ctx, player_alias_txt, False)

                    if ret_data[0:3] == 'ERR':
                        await ctx.send(ret_data)
                        await ctx.message.add_reaction(emojis.redcross)
                        return

                    if type(ret_data)==str:
                        ignored_allyCodes = [ret_data]
                    else:
                        ignored_allyCodes = ret_data
                    options.remove(arg)

            #Then split remaining arguments by "+" as phase separator
            remaining_options = " ".join(options)
            all_phase_option_txt = remaining_options.split("+")
            list_phase_options = []
            for phase_option_txt in all_phase_option_txt:
                my_option_txt = phase_option_txt.strip()
                while '\n' in my_option_txt:
                    my_option_txt.replace('\n', ' ')
                while '  ' in my_option_txt:
                    my_option_txt.replace('  ', ' ')
                phase_args = my_option_txt.split(' ')

                estimate_fights = False
                estimate_platoons = False
                estimate_targets = None
                platoon_targets = None
                phase_options = list(phase_args)
                for arg in phase_args:
                    if arg.startswith("-e"):
                        estimate_fights = True
                        if "=" in arg:
                            estimate_targets = arg.split('=')[1]
                        phase_options.remove(arg)
                    elif arg.startswith("-p"):
                        estimate_platoons = True
                        if "=" in arg:
                            platoon_targets = arg.split('=')[1]
                        phase_options.remove(arg)

                if len(phase_options) == 0:
                    star_targets = ""
                elif len(phase_options) == 1:
                    star_targets = phase_options[0]
                else:
                    await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help tbs")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                d_phase_options={"estimate_fights": estimate_fights,
                                 "estimate_platoons": estimate_platoons,
                                 "estimate_targets": estimate_targets,
                                 "platoon_targets": platoon_targets,
                                 "star_targets": star_targets}

                list_phase_options.append(d_phase_options)

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send("ERR: "+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            connected_allyCode = bot_infos["allyCode"]
            fight_estimation_type = bot_infos["tbFightEstimationType"]

            # Loop by phase
            prev_round = None
            for phase_options in list_phase_options:
                goutils.log2("DBG", phase_options)
                if prev_round == None:
                    goutils.log2("DBG", prev_round)
                else:
                    goutils.log2("DBG", prev_round["phase"])

                star_targets = phase_options["star_targets"]
                estimate_fights = phase_options["estimate_fights"]
                estimate_platoons = phase_options["estimate_platoons"]
                estimate_targets = phase_options["estimate_targets"]
                platoon_targets = phase_options["platoon_targets"]

                # Main call
                err_code, ret_txt, ret_data = await go.print_tb_status(
                                                guild_id, star_targets, 0,
                                                simulated_tb=simulated_tb,
                                                estimate_fights=estimate_fights,
                                                estimate_platoons=estimate_platoons,
                                                targets_fights=estimate_targets,
                                                targets_platoons=platoon_targets,
                                                fight_estimation_type=fight_estimation_type,
                                                prev_round = prev_round,
                                                allyCode=connected_allyCode,
                                                ignored_allyCodes=ignored_allyCodes)

                if err_code == 0:
                    images = ret_data["images"]
                    prev_round = ret_data["prev_round"]
                    for txt in goutils.split_txt(ret_txt, MAX_MSG_SIZE):
                        await output_channel.send(txt)

                    if images != None:
                        for image in images:
                            with BytesIO() as image_binary:
                                image.save(image_binary, 'PNG')
                                image_binary.seek(0)
                                await output_channel.send(content = "",
                                    file=File(fp=image_binary, filename='image.png'))

                else:
                    await ctx.send(ret_txt)
                    await ctx.message.add_reaction(emojis.redcross)
                    break

                #Simulation only useful when prev_round is not set
                simulated_tb = None

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", str(sys.exc_info()[0]))
            goutils.log2("ERR", e)
            goutils.log2("ERR", traceback.format_exc())

    ####################################################
    # Command spe
    ####################################################
    @commands.check(officer_command)
    @commands.command(name='spe',
            brief="Statut des missions spéciales en BT",
            help="Statut des missions spéciales en BT avec les résultats par joueur\n" \
                 "go.spe ROTE2-LS")
    async def spe(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            # Manage command options
            options = list(args)
            output_channel = ctx.message.channel
            for arg in args:
                if arg.startswith('<#') or arg.startswith('https://discord.com/channels/'):
                    output_channel, err_msg = await get_channel_from_channelname(ctx, arg)
                    if output_channel == None:
                        await ctx.send('**ERR**: '+err_msg)
                        output_channel = ctx.message.channel
                        display_mentions=False
                    options.remove(arg)

            if len(options) != 1:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help spe")
                await ctx.message.add_reaction(emojis.redcross)
                return

            zone_shortname = options[0]

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send("ERR: "+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            connected_allyCode = bot_infos["allyCode"]

            # launch actual command
            ec, ret_txt, image = await go.print_tb_special_results(guild_id, zone_shortname, allyCode=connected_allyCode)
            if ec != 0:
                await ctx.send("ERR: "+ret_txt)
                await ctx.message.add_reaction(emojis.redcross)
                return

            if image==None:
                await ctx.send(ret_txt)
            else:
                with BytesIO() as image_binary:
                    image.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    await output_channel.send(content = "",
                        file=File(fp=image_binary, filename='image.png'))

            await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            await ctx.send("ERR: erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)
            goutils.log2("ERR", traceback.format_exc())

    ####################################################
    # Command tbstats
    ####################################################
    @commands.check(officer_command)
    @commands.command(name='tbstats',
            brief="Stats des combats en BT",
            help="Stats des combats en BT avec les résultats par joueur\n" \
                 "go.tbstats          > pour toute la BT, tous les joueurs\n" \
                 "go.tbstats chaton73 > pour toute la BT du joueur chaton75\n" \
                 "go.tbstats 2 5      > pour le 2e et le 5e jour, tous les joueurs\n" \
                 "go.tbstats 2 5 toto > pour le 2e et le 5e jour du joueur toto")
    async def tbstats(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            list_allyCodes = []
            rounds = []
            for arg in args:
                if arg.isnumeric():
                    rounds.append(arg)
                else:
                    allyCode = await manage_me(ctx, arg, False)
                    if allyCode[0:3] == 'ERR':
                        await ctx.send(allyCode)
                    else:
                        list_allyCodes.append(allyCode)

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send("ERR: "+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            connected_allyCode = bot_infos["allyCode"]

            # launch actual command
            ec, ret_txt, image = await go.print_tb_strike_stats(guild_id, list_allyCodes, rounds, allyCode=connected_allyCode)
            if ec != 0:
                await ctx.send("ERR: "+ret_txt)
                await ctx.message.add_reaction(emojis.redcross)
                return

            #for txt in goutils.split_txt(ret_txt, MAX_MSG_SIZE):
            #    await ctx.send("```"+txt+"```")
            #await ctx.message.add_reaction(emojis.check)

            if image==None:
                await ctx.send(ret_txt)
            else:
                export_path="/tmp/tbstats_"+guild_id+".csv"
                export_file = open(export_path, "w")
                export_file.write(ret_txt)
                export_file.close()

                with BytesIO() as image_binary:
                    image.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    await ctx.send(content = "",
                        #file=File(fp=image_binary, filename='image.png'))
                        files=[File(fp=image_binary, filename='image.png'),
                               File(export_path)])

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    ####################################################
    # Command tbo
    ####################################################
    @commands.check(officer_command)
    @commands.command(name='tbo',
            brief="Objectif de phase de la BT",
            help="Objectif de la phase de BT en fonctions des zone:étoiles demandés\n" \
                 "go.tbo DS:1 LS:3 MS:2")
    async def tbo(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            # Manage command parameters
            if len(args) == 0:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help tbo")
                await ctx.message.add_reaction(emojis.redcross)
                return
            else:
                tb_phase_target = args
                for arg in args:
                    if " " in arg:
                        await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help tbo")
                        await ctx.message.add_reaction(emojis.redcross)
                        return

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send("ERR: "+et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]

            # Main call
            err_code, ret_txt = await go.set_tb_targets(guild_id, tb_phase_target)
            if err_code == 0:
                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emojis.check)
            else:
                await ctx.send(ret_txt)
                await ctx.message.add_reaction(emojis.redcross)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: spgt
    # Parameters: zone shortname or "all" / alias of a character
    # Purpose: stats of a character/ship for the TW opponents
    # Display: one line per opponent player
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='spgt',
                 brief="Stats de Perso de l'adversaire en GT",
                 help="Stats de Perso de l'adversaire en GT\n\n"\
                      "Potentiellement trié par vitesse (-v), les dégâts (-d), la santé (-s), le pouvoir (-p)\n"\
                      "Exemple: go.spg all JMK\n"\
                      "Exemple: go.spg F1 -v Executor")
    async def spgt(self, ctx, tw_zone, *characters):
        await ctx.message.add_reaction(emojis.thumb)

        #Ensure command is launched from a server, not a DM
        if ctx.guild == None:
            await ctx.send('ERR: commande non autorisée depuis un DM')
            await ctx.message.add_reaction(emojis.redcross)
            return

        if not tw_zone in ['all']+list(data.dict_tw.keys()):
            await ctx.send("ERR: zone GT inconnue")
            await ctx.message.add_reaction(emojis.redcross)
            return

        list_options = []
        list_characters = []
        for item in characters:
            if item[0] == "-":
                list_options.append(item)
            else:
                list_characters.append(item)
        
        if len(list_characters) > 0:
            if len(list_options) <= 1:
                #get bot config from DB
                ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
                if ec!=0:
                    await ctx.send("ERR: "+et)
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                guild_id = bot_infos["guild_id"]

                # Launch the actual command
                ret_cmd = await go.print_character_stats( list_characters,
                    list_options, "", True, guild_id, tw_zone)
            else:
                ret_cmd = 'ERR: merci de préciser au maximum une option de tri'
        else:
            ret_cmd = 'ERR: merci de préciser perso'
            
        if ret_cmd[0:3] == 'ERR':
            await ctx.send(ret_cmd)
            await ctx.message.add_reaction(emojis.redcross)
        else:
            #texte classique
            for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                await ctx.send("```"+txt+"```")

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emojis.check)

    ##############################################################
    # Command: bot.gettwlogs
    # Parameters: none
    # Purpose: Tag all players in the guild which own the selected character
    # Display: One line with all discord tags
    ##############################################################
    @commands.check(officer_command)
    @commands.command(name='bot.gettwlogs',
                 brief="Télécharge le fichier JSON complet des logs de la dernière GT",
                 help="Télécharge le fichier JSON complet des logs de la dernière GT")
    async def botgettwlogs(self, ctx):
        await ctx.message.add_reaction(emojis.thumb)

        #Ensure command is launched from a server, not a DM
        if ctx.guild == None:
            await ctx.send('ERR: commande non autorisée depuis un DM')
            await ctx.message.add_reaction(emojis.redcross)
            return

        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
        if ec!=0:
            await ctx.send('ERR: '+et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        guild_id = bot_infos["guild_id"]
        guild_name = bot_infos["guild_name"]

        if guild_id == None:
            await ctx.send('ERR: Guilde non déclarée dans le bot')
            return

        #Look for latest TW event file for this guild
        search_dir = "EVENTS/"
        files = os.listdir(search_dir)
        files = [os.path.join(search_dir, f) for f in files] # add path to each file
        files = list(filter(os.path.isfile, files))
        files = list(filter(lambda f: guild_id+"_TERRITORY_WAR_EVENT" in f, files))
        files = list(filter(lambda f: "_events" in f, files))
        files.sort(key=lambda x: os.path.getmtime(x))
        latest_log = files[-1]

        #create zip archive
        archive_path="/tmp/TWlogs_"+guild_name+".zip"
        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zipped:
            zipped.write(latest_log)
        file = discord.File(archive_path)
        await ctx.send(file=file, content="Dernier fichier trouvé : "+latest_log)

        await ctx.message.add_reaction(emojis.check)

    ##############################################################
    # Command: bot.gettblogs
    # Parameters: none
    # Purpose: send file of events for latest TB
    ##############################################################
    @commands.check(officer_command)
    @commands.command(name='bot.gettblogs',
                 brief="Télécharge le fichier JSON complet des logs de la dernière BT",
                 help="Télécharge le fichier JSON complet des logs de la dernière BT")
    async def botgettblogs(self, ctx):
        await ctx.message.add_reaction(emojis.thumb)

        #Ensure command is launched from a server, not a DM
        if ctx.guild == None:
            await ctx.send('ERR: commande non autorisée depuis un DM')
            await ctx.message.add_reaction(emojis.redcross)
            return

        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
        if ec!=0:
            await ctx.send('ERR: '+et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        guild_id = bot_infos["guild_id"]
        guild_name = bot_infos["guild_name"]

        if guild_id == None:
            await ctx.send('ERR: Guilde non déclarée dans le bot')
            return

        #Look for latest TB event file for this guild
        search_dir = "EVENTS/"
        files = os.listdir(search_dir)
        files = [os.path.join(search_dir, f) for f in files] # add path to each file
        files = list(filter(os.path.isfile, files))
        files = list(filter(lambda f: guild_id+"_TB_EVENT" in f, files))
        files = list(filter(lambda f: "_events" in f, files))
        files.sort(key=lambda x: os.path.getmtime(x))
        latest_log = files[-1]

        #create zip archive
        archive_path="/tmp/TBlogs_"+guild_name+".zip"
        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=True) as zipped:
            zipped.write(latest_log)
        file = discord.File(archive_path)
        await ctx.send(file=file, content="Dernier fichier trouvé : "+latest_log)

        await ctx.message.add_reaction(emojis.check)

    ##############################################################
    # Command: gettwbest
    # Parameters: none
    # Purpose: Display best teams from last TW
    # Display: image and description of teams
    ##############################################################
    @commands.check(officer_command)
    @commands.command(name='gettwbest',
                      brief="Affiche les meilleures défenses de la BT",
                      help="Affiche les meilleures défenses de la GT")
    async def gettwbest(self, ctx):
        await ctx.message.add_reaction(emojis.thumb)

        #Ensure command is launched from a server, not a DM
        if ctx.guild == None:
            await ctx.send('ERR: commande non autorisée depuis un DM')
            await ctx.message.add_reaction(emojis.redcross)
            return

        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
        if ec!=0:
            await ctx.send('ERR: '+et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        guild_id = bot_infos["guild_id"]
        guild_name = bot_infos["guild_name"]
        connected_allyCode = bot_infos["allyCode"]

        if guild_id == None:
            await ctx.send('ERR: Guilde non déclarée dans le bot')
            return

        # Launch actual command
        ret = await connect_rpc.get_tw_status(guild_id, 0, allyCode=connected_allyCode)

        for home_away in [["homeGuild", "notre défense"], ["awayGuild", "la défense adverse"]]:
            list_team_home=ret[home_away[0]]["list_defenses"]
            best_teams = go.filter_tw_best_teams(list_team_home)
            for unit_type in [["ships", "vaisseaux"], ["chars", "terrestre"]]:
                for beaten_txt in [["beaten", "vaincue"], ["remaining", "invaincue"]]:
                    cur_teams = best_teams[unit_type[0]][beaten_txt[0]]
                    if cur_teams == None:
                        continue

                    team_count = len(cur_teams["images"])
                    fights = cur_teams["fights"]

                    if team_count == 0:
                        txt = "Rien de particulier à signaler pour "+home_away[1]+" "+unit_type[1]+" pour les teams "+beaten_txt[1]+"s"
                    elif team_count == 1:
                        txt = "Meilleure team de **"+home_away[1]+" "+unit_type[1]+"**, "+beaten_txt[1]+" après "+str(fights)+" combats"
                    else:
                        txt = "Meilleures teams de **"+home_away[1]+" "+unit_type[1]+"**, "+beaten_txt[1]+"s après "+str(fights)+" combats"

                    full_img = None
                    for img in cur_teams["images"]:
                        full_img = portraits.add_vertical(full_img, img)

                    if full_img == None:
                        await ctx.send(content = txt)
                    else:
                        with BytesIO() as image_binary:
                            full_img.save(image_binary, 'PNG')
                            image_binary.seek(0)
                            await ctx.send(content = txt, file=File(fp=image_binary, filename='image.png'))

        await ctx.message.add_reaction(emojis.check)

##############################################################
# Class: OfficerCog
# Description: contains all officer commands
##############################################################
class OfficerCog(commands.Cog, name="Commandes pour les officiers"):
    def __init__(self, bot):
        self.bot = bot

    ##############################################################
    # Command: tagcount
    # Parameters: channel
    # Purpose: count player tags in a specific channel (for instance in player-warning channel)
    # Display: list of player tags with counter
    ##############################################################
    @commands.check(officer_command)
    @commands.command(name='tagcount', brief="Compte les tags de joueurs dans un channel",
                                       help ="Compte les tags de joueurs dans un channel\n" \
                                             "Exemple: go.tagcount #avertos\n" \
                                             "Exemple: go.tagcount #avertos -pédagogique")
    async def tagcount(self, ctx, *args):
        await ctx.message.add_reaction(emojis.thumb)

        args = list(args)
        if len(args) == 0 or len(args)>2:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help tagcount")
            await ctx.message.add_reaction(emojis.redcross)
            return

        channel_param = args[0]
        if not channel_param.startswith('<#') and not channel_param.startswith('https://discord.com/channels/'):
            await ctx.send("ERR: commande mal formulée. Le paramètre doit être un channel discord")
            await ctx.message.add_reaction(emojis.redcross)
            return

        channel, err_msg = await get_channel_from_channelname(ctx, channel_param)
        if channel == None:
            await ctx.send('**ERR**: '+err_msg)
            await ctx.send("ERR: commande mal formulée. Le paramètre doit être un channel discord")
            await ctx.message.add_reaction(emojis.redcross)
            return

        if len(args)==2:
            filter_txt = args[1]
            if not filter_txt[0]=="-":
                await ctx.send("ERR: commande mal formulée. Le paramètre doit être un channel discord")
                await ctx.message.add_reaction(emojis.redcross)
                return
            filter_txt = filter_txt[1:]
        else:
            filter_txt = ""

        dict_tag_count = {}
        async for message in channel.history(limit=500):
            message_txt = message.content

            #use message filter
            if filter_txt!="" and filter_txt in message_txt:
                continue

            while "<@" in message_txt:
                start_tag_pos = message_txt.index("<@")
                message_txt = message_txt[start_tag_pos:]
                end_tag_pos = message_txt.index(">")
                user_tag = message_txt[0:end_tag_pos+1]
                if not user_tag in dict_tag_count:
                    dict_tag_count[user_tag] = 0
                dict_tag_count[user_tag] += 1

                if end_tag_pos+1 == len(message_txt):
                    message_txt = ""
                else:
                    message_txt = message_txt[end_tag_pos+1:]

        output_txt = ""
        sorted_count = sorted(dict_tag_count.items(), key=lambda x:-x[1])
        for (user_tag, count) in sorted_count:
            output_txt += user_tag+": "+str(count)+"\n"

        if output_txt == "":
            output_txt = "Aucun tag dans ce channel"

        for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
             await ctx.send(txt)

        await ctx.message.add_reaction(emojis.check)

    ##############################################################
    # Command: lgs
    # Parameters: None
    # Purpose: Update cache files from google sheet, and JSON files from API
    # Display: None
    ##############################################################
    @commands.check(officer_command)
    @commands.command(name='lgs', brief="Lit les dernières infos du google sheet",
                      help="Lit les dernières infos du google sheet")
    async def lgs(self, ctx):
        await ctx.message.add_reaction(emojis.thumb)

        #Ensure command is launched from a server, not a DM
        if ctx.guild == None:
            await ctx.send('ERR: commande non autorisée depuis un DM')
            await ctx.message.add_reaction(emojis.redcross)
            return

        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
        if ec!=0:
            await ctx.send('ERR: '+et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        guild_id = bot_infos["guild_id"]

        #Launch the actual command
        err_code, err_txt = await read_gsheets(guild_id)
        data.reset_data()

        if err_code == 1:
            await ctx.send(err_txt)
            await ctx.message.add_reaction(emojis.redcross)
        else:
            await ctx.message.add_reaction(emojis.check)


    ##############################################################
    # Command: tpg
    # Parameters: alias of the character to find
    # Purpose: Tag all players in the guild which own the selected character
    # Display: One line with all discord tags
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='tpg',
                 brief="Tag les possesseurs d'un Perso dans la Guilde",
                 help="Tag les possesseurs d'un Perso dans la Guilde\n\n"\
                      "(ajouter '-TW' pour prendre en compte les persos posés en défense de GT)\n"\
                      "(OU ajouter '-TB' pour prendre en compte les persos posés en pelotons de BT)\n"\
                      "Exemple : go.tpg me SEE ---> ceux qui ont SEE\n"\
                      "Exemple : go.tpg me SEE:G13 ---> ceux qui ont SEE au moins G13\n"\
                      "Exemple : go.tpg me Mara:o ---> ceux qui ont Mara omicron\n"\
                      "Exemple : go.tpg me Sana:z ---> ceux qui ont Sana zeta\n"\
                      "Exemple : go.tpg me Zorii:zU2 ---> ceux qui ont Zorii avec zeta sur Unique 2\n"\
                      "Exemple : go.tpg me Zorii:zU1:zU2 ---> ceux qui ont Zorii avec les 2 zetas\n"\
                      "Exemple : go.tpg me Mara +SK ---> ceux qui ont Mara et SK\n"\
                      "Exemple : go.tpg me Mara -SK ---> ceux qui ont Mara et qui n'ont pas SK\n"\
                      "Exemple : go.tpg me -Leia:ulti ---> ceux qui ont Leia mais pas Leia avec ulti\n"\
                      "Exemple : go.tpg me LV !Jabba -TW ---> ceux qui ont LV et qui n'ont pas attaqué Jabba en GT\n"\
                      "Exemple : go.tpg me JMK / Jabba ceux qui ont JMK, puis ceux qui ont Jabba (commande lancée 2 fois)")
    async def tpg(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            #Check arguments
            args = list(args)
            tw_mode = False
            tb_mode = False
            guild_id = None

            output_channel = ctx.message.channel
            with_mentions = False
            for arg in args:
                if arg.startswith('<#') or arg.startswith('https://discord.com/channels/'):
                    if not officer_command(ctx):
                        await ctx.send("ERR: l'envoi des résultats dans un autre channel est réservé aux officiers")
                        await ctx.message.add_reaction(emojis.redcross)
                        return

                    output_channel, err_msg = await get_channel_from_channelname(ctx, arg)
                    with_mentions = True
                    if output_channel == None:
                        await ctx.send('**ERR**: '+err_msg)
                        output_channel = ctx.message.channel
                        with_mentions = False
                    args.remove(arg)

            connected_allyCode = None
            if "-TW" in args:
                #Ensure command is launched from a server, not a DM
                if ctx.guild == None:
                    await ctx.send("ERR: commande non autorisée depuis un DM avec l'option -TW")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                tw_mode = True
                args.remove("-TW")

                #get bot config from DB
                ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
                if ec!=0:
                    await ctx.send("ERR: vous devez avoir un fichier de configuration pour utiliser cette commande")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                guild_id = bot_infos["guild_id"]
                connected_allyCode = bot_infos["allyCode"]

            if "-TB" in args:
                if tw_mode:
                    await ctx.send("ERR: impossible d'utiliser les options -TW et -TB en même temps")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                #Ensure command is launched from a server, not a DM
                if ctx.guild == None:
                    await ctx.send("ERR: commande non autorisée depuis un DM avec l'option -TB")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                tb_mode = True
                args.remove("-TB")

                #get bot config from DB
                ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
                if ec!=0:
                    await ctx.send("ERR: vous devez avoir un fichier de configuration pour utiliser cette commande")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                guild_id = bot_infos["guild_id"]
                connected_allyCode = bot_infos["allyCode"]

            if len(args) >= 2:
                allyCode = args[0]

                # Arg management
                # Either we get several checks for general usage or TW defense, separated by a "/"
                # Or we have a unique check during TW, with atack checking
                all_args = " ".join(args[1:])
                if "/" in all_args and "!" in all_args:
                    await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help tpg")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                exclude_attacked_leaders = []
                if "!" in all_args:
                    if not tw_mode:
                        await ctx.send("ERR: impossible d'utiliser l'option ! sans option -TW")
                        await ctx.message.add_reaction(emojis.redcross)
                        return

                    for arg in args[1:]:
                        if arg[0] == "!":
                            exclude_attacked_leaders.append(arg[1:])

                    for leader in exclude_attacked_leaders:
                        args.remove("!"+leader)

                character_list = [x.split(' ') for x in [y.strip() for y in " ".join(args[1:]).split('/')] if x!='']
            else:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help tpg")
                await ctx.message.add_reaction(emojis.redcross)
                return

            allyCode = await manage_me(ctx, allyCode, False)
                    
            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
            else:
                err, errtxt, list_list_ids = \
                    await go.tag_players_with_character(allyCode, character_list,
                                                        guild_id, tw_mode, tb_mode,
                                                        with_mentions, 
                                                        exclude_attacked_leaders=exclude_attacked_leaders,
                                                        connected_allyCode=connected_allyCode)

                if err != 0:
                    await ctx.send(errtxt)
                    await ctx.message.add_reaction(emojis.redcross)
                else:
                    for list_ids in list_list_ids:
                        intro_txt = list_ids[0]
                        if len(list_ids) > 1:
                            await output_channel.send(intro_txt +" :\n" +' / '.join(list_ids[1:])+"\n--> "+str(len(list_ids)-1)+" joueur(s)")
                        else:
                            await output_channel.send(intro_txt +" : aucun joueur")

                    await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: registercheck
    # Parameters: code allié (string) ou "me"
    # Purpose: liste of all guild members and associated discord account
    ##############################################################
    @commands.check(officer_command)
    @commands.command(name='registercheck',
                 brief="Liste les joueurs et leur compte discord",
                 help="Liste les joueurs et leur compte discord\n\n"\
                      "Exemple: go.registercheck me\n"\
                      "Exemple: go.registercheck 123456789")
    async def registercheck(self, ctx, allyCode):
        await bot_commands.registercheck(ctx, allyCode)

##############################################################
# Member slash commands (duplicate of MemberCog
##############################################################
@bot.tree.command()
async def gdp(interaction: discord.Interaction,
              allycode: str) -> None:
    await bot_commands.gdp(interaction, allycode)

@bot.tree.command(name="farm-equipement")
async def farmeqpt(interaction: discord.Interaction,
                   allycode: str,
                   list_alias_txt: str) -> None:
    list_alias = list_alias_txt.split(" ")
    await bot_commands.farmeqpt(interaction, allycode, list_alias)

##############################################################
# Class: MemberCog
# Description: contains all member commands
##############################################################
class MemberCog(commands.Cog, name="Commandes pour les membres"):
    def __init__(self, bot):
        self.bot = bot

    @commands.check(member_command)
    @commands.command(name='gtcontrej',
                      brief="Vérifie la possibilité d'un contre en GT",
                      help="Vérifie la possibilité d'un contre en GT\n\n"\
                           "Exemple: go.gtcontrej 123456789 ITvsGEOS\n"\
                           "Exemple: go.gtcontrej 123456789 SEEvsJMK")
    async def gtcontrej(self, ctx, allyCode, counter_type):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            allyCode = await manage_me(ctx, allyCode, False)
            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send("ERR: vous devez avoir un warbot pour utiliser cette commande")
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]

            ec, txt = await go.check_tw_counter(allyCode, guild_id, counter_type)
            if ec != 0:
                await ctx.send(txt)
                await ctx.message.add_reaction(emojis.redcross)
                return

            await ctx.send(txt)
            await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.graphj"+str(sys.exc_info()[0]))
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    @commands.check(member_command)
    @commands.command(name='register',
                      brief="Lie un code allié à un compte discord",
                      help="Lie un code allié à un compte discord\n\n"\
                           "Exemple: go.register 123456789\n"\
                           "Exemple: go.register 123456789 @chatondu75\n"\
                           "Exemple: go.register 123456789 confirm")
    async def register(self, ctx, *args):
        await bot_commands.register_player(ctx, args)

    @commands.check(member_command)
    @commands.command(name='unregister',
                      brief="Délie un code allié de tout compte discord",
                      help="Délie un code allié de tout compte discord\n\n"\
                           "Exemple: go.unregister 123456789")
    async def unregister(self, ctx, *args):
        await bot_commands.unregister(ctx, args)

    ##############################################################
    # display kit
    # IN: character alias
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='kit',
                      brief="Affiche le kit d'un perso",
                      help="Affiche le kit d'un perso\n\n"\
                           "Exemple: go.kit kitfisto")
    async def kit(self, ctx, alias):
        await ctx.message.add_reaction(emojis.thumb)

        ec, et = go.print_unit_kit(alias)

        if ec != 0:
            await ctx.send(et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        for txt in goutils.split_txt(et, MAX_MSG_SIZE):
             await ctx.send(txt)

        await ctx.message.add_reaction(emojis.check)

    ##############################################################
    # Command: qui
    # Parameters: code allié (string) ou "me" ou pseudo ou @mention
    # Purpose: Donner les infos de base d'unee personne
    # Display: Nom IG, Nom discord, Code allié, statut dans la DB
    #          pareil pour sa guild
    #          et des liens (swgoh.gg)
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='qui',
                      brief="Identifie un joueur et sa guilde",
                      help="Identifie un joueur et sa guilde\n\n"\
                           "Exemple: go.qui 192126111\n"\
                           "Exemple: go.qui dark Patoche\n"\
                           "Exemple: go.qui @chaton372\n"\
                           "Exemple: go.qui -TW")
    async def qui(self, ctx, *alias):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            full_alias = " ".join(alias)
            allyCode = await manage_me(ctx, full_alias, True)
            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
                return

            # Get player info
            e, t, dict_player = await go.load_player(allyCode, 0, False)
            if e!=0:
                await ctx.send("ERR: "+t)
                await ctx.message.add_reaction(emojis.redcross)
                return

            #Look in DB
            query = "SELECT name, guildName, lastUpdated, "\
                    "char_gp, ship_gp, grand_arena_rank, guildId "\
                    "FROM players WHERE allyCode = " + allyCode
            result = connect_mysql.get_line(query)
            if result != None:
                player_name = result[0]
                guildName = result[1]
                lastUpdated = result[2]
                lastUpdated_txt = lastUpdated.strftime("%d/%m/%Y %H:%M:%S")
                gp = int((result[3]+result[4])/100000)/10
                arena_rank = result[5]
                guildId = result[6]
            else:
                player_name = dict_player["name"]
                guildName = dict_player["guildName"]
                lastUpdated_txt = "joueur inconnu"
                gp = "???"
                arena_rank = "???"
                guildId = dict_player["guildId"]

            if guildName == "None":
                guildName = "*pas de guilde*"

            #Look for Discord Pseudo if in guild
            db_data = connect_mysql.load_config_players(guild_id=guildId)
            dict_players_by_IG = db_data[1]

            if player_name in dict_players_by_IG:
                discord_mention = dict_players_by_IG[player_name][1]
                ret_re = re.search("<@(\\d*)>.*", discord_mention)
                discord_id = ret_re.group(1)

                discord_display_names = []
                for guild in bot.guilds:
                    try:
                        discord_user = await guild.fetch_member(discord_id)
                        display_name = discord_user.display_name
                        discord_display_names.append([guild.name, display_name])
                    except:
                        continue

            else:
                discord_display_names = []

            swgohgg_url = "https://swgoh.gg/p/" + allyCode
            try:
                r = requests.get(swgohgg_url, timeout=10)
                if r.status_code == 404:
                    swgohgg_url = "introuvable"
            except requests.exceptions.ReadTimeout as e:
                swgohgg_url = "*site indisponible pour le moment*"
            except urllib.error.HTTPError as e:
                swgohgg_url = "introuvable"

            txt = "Qui est **"+full_alias+"** ?\n"
            txt+= "- code allié : "+str(allyCode)+"\n"
            txt+= "- pseudo IG : "+player_name+"\n"
            txt+= "- guilde : "+guildName+"\n"
            txt+= "- PG : "+str(gp)+"M\n"
            txt+= "- GAC : "+arena_rank+"\n"

            if len(discord_display_names)>0:
                for discord_name in discord_display_names:
                    if ctx.guild == None:
                        # in a DM
                        txt+= "- pseudo Discord chez "+discord_name[0]+" : "+discord_name[1]+"\n"
                    elif discord_name[0] == ctx.guild.name:
                        # in the right guild
                        txt+= "- pseudo Discord chez **"+discord_name[0]+"** : "+discord_name[1]+"\n"
                    else:
                        # in a guild, but nott the right one
                        txt+= "- pseudo Discord chez "+discord_name[0]+" : "+discord_name[1]+"\n"
            else:
                txt+= "- pseudo Discord : ???\n"

            txt+= "- dernier refresh du bot : "+lastUpdated_txt+"\n"
            txt+= "- lien SWGOH.GG : <"+swgohgg_url + ">"

            await ctx.send(txt)

            await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: vtg
    # Parameters: code allié (string) ou "me", une liste de teams séparées par des espaces ou "all"
    # Purpose: Vérification des Teams de la Guilde avec tri par progrès
    # Display: Un tableau avec un joueur par ligne et des peros + stats en colonne
    #          ou plusieurs tableaux à la suite si plusieurs teams
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='vtg',
                      brief="Vérifie la dispo d'une team dans la guilde",
                      help="Vérifie la dispo d'une team dans la guilde\n\n"\
                           "(ajouter '-TW' pour prendre en compte les persos posés en défense de GT)\n"\
                           "Exemple: go.vtg 192126111 all\n"\
                           "Exemple: go.vtg 192126111 NS\n"\
                           "Exemple: go.vtg 192126111 PADME NS DR\n"\
                           "Exemple: go.vtg me NS")
    async def vtg(self, ctx, allyCode, *teams):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            allyCode = await manage_me(ctx, allyCode, True)
            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
                return

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send("ERR: vous devez avoir un fichier de configuration pour utiliser cette commande")
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            gfile_name = bot_infos["gfile_name"]
            if gfile_name == None:
                await ctx.send("ERR: vous devez avoir un fichier de configuration pour utiliser cette commande")
                await ctx.message.add_reaction(emojis.redcross)
                return

            teams = list(teams)
            if "-TW" in teams:
                #Ensure command is launched from a server, not a DM
                if ctx.guild == None:
                    await ctx.send("ERR: commande non autorisée depuis un DM avec l'option -TW")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                #Ensure command is launched from a server which is linked to a warbot
                if guild_id == None:
                    await ctx.send("ERR: vous devez avoir un warbot pour utiliser l'option -TW")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                tw_mode = True
                teams.remove("-TW")
            else:
                tw_mode = False

            if len(teams) == 0:
                teams = ["all"]

            err, ret_cmd = await go.print_vtg( teams, allyCode, guild_id, gfile_name, tw_mode)
            if err == 0:
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send(txt)

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emojis.check)
            else:
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emojis.redcross)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.vtj"+str(sys.exc_info()[0]))
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: vtj
    # Parameters: code allié (string), une liste de teams séparées par des espaces ou "all"
    # Purpose: Vérification des Teams d'un joueur avec tri par progrès
    # Display: Une ligne par joueur avec des peros + stats en colonne
    #          ou plusieurs ligne à la suite si plusieurs teams
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='vtj',
                 brief="Vérifie la dispo d'une ou plusieurs teams chez un joueur",
                 help="Vérifie la dispo d'une ou plusieurs teams chez un joueur\n\n"\
                      "(ajouter '-TW' pour prendre en compte les persos posés en défense de GT)\n"\
                      "Exemple: go.vtj 192126111 all\n"\
                      "Exemple: go.vtj 192126111 NS\n"\
                      "Exemple: go.vtj 192126111 PADME NS DR\n"\
                      "Exemple: go.vtj me NS")
    async def vtj(self, ctx, allyCode, *teams):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            #Ensure command is launched from a server, not a DM
            if ctx.guild == None:
                await ctx.send('ERR: commande non autorisée depuis un DM')
                await ctx.message.add_reaction(emojis.redcross)
                return

            allyCode = await manage_me(ctx, allyCode, False)
            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
            if ec!=0:
                await ctx.send("ERR: vous devez avoir un fichier de configuration pour utiliser cette commande")
                await ctx.message.add_reaction(emojis.redcross)
                return

            guild_id = bot_infos["guild_id"]
            gfile_name = bot_infos["gfile_name"]
            if gfile_name == None:
                await ctx.send("ERR: vous devez avoir un fichier de configuration pour utiliser cette commande")
                await ctx.message.add_reaction(emojis.redcross)
                return

            teams = list(teams)
            if "-TW" in teams:
                #Ensure command is launched from a server, not a DM
                if ctx.guild == None:
                    await ctx.send("ERR: commande non autorisée depuis un DM avec l'option -TW")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                #Ensure command is launched from a server which is linked to a warbot
                if guild_id == None:
                    await ctx.send("ERR: vous devez avoir un warbot pour utiliser l'option -TW")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                tw_mode = True
                teams.remove("-TW")
            else:
                tw_mode = False

            if len(teams) == 0:
                teams = ["all"]

            err, txt, images = await go.print_vtj(teams, allyCode, guild_id, gfile_name, tw_mode)
            if err != 0:
                await ctx.send(txt)
                await ctx.message.add_reaction(emojis.redcross)
            else:
                for sub_txt in goutils.split_txt(txt, MAX_MSG_SIZE):
                    await ctx.send(sub_txt)
                if images != None:
                    image = images[0]
                    with BytesIO() as image_binary:
                        image.save(image_binary, 'PNG')
                        image_binary.seek(0)
                        await ctx.send(content = "",
                            file=File(fp=image_binary, filename='image.png'))

                #Icône de confirmation de fin de commande dans le message d'origine
                    await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.vtj"+str(sys.exc_info()[0]))
            await ctx.message.add_reaction(emojis.redcross)

    @commands.check(member_command)
    @commands.command(name='fegv',
                 brief="Donne les Farming d'Eclats pour le Guide de Voyage",
                 help="Donne les Farmings d'Eclats pour le Guide de Voyage, ou pour tous les persos quiexistent avec l'option -all\n\n"\
                      "Exemple: go.fegv me\n"\
                      "         go.fegv me -all")
    async def fegv(self, ctx, allyCode, *args):
        await ctx.message.add_reaction(emojis.thumb)

        #Check arguments
        args = list(args)

        show_all=False
        if "-all" in args:
            show_all=True
            args.remove("-all")

        allyCode = await manage_me(ctx, allyCode, False)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emojis.redcross)
        else:
            err_code, ret_cmd = go.print_fegv( allyCode, show_all=show_all)
            if err_code == 0:
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send("`"+txt+"`")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emojis.check)
            else:
                await ctx.send(ret_cmd)

    ##############################################################
    @commands.check(member_command)
    @commands.command(name='ftj',
                 brief="Donne le progrès de farming d'une team chez un joueur",
                 help="Donne le progrès de farming d'une team chez un joueur\n\n"\
                      "Exemple: go.ftj me ROTE")
    async def ftj(self, ctx, allyCode, team):
        await ctx.message.add_reaction(emojis.thumb)

        #Ensure command is launched from a server, not a DM
        if ctx.guild == None:
            await ctx.send('ERR: commande non autorisée depuis un DM')
            await ctx.message.add_reaction(emojis.redcross)
            return

        allyCode = await manage_me(ctx, allyCode, False)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emojis.redcross)

        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
        if ec!=0:
            await ctx.send('ERR: '+et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        guild_id = bot_infos["guild_id"]
        gfile_name = bot_infos["gfile_name"]
        if gfile_name == None:
            await ctx.send("ERR: vous devez avoir un fichier de configuration pour utiliser cette commande")
            await ctx.message.add_reaction(emojis.redcross)
            return

        # Actual command
        err_code, ret_cmd = await go.print_ftj( allyCode, team, guild_id, gfile_name)
        if err_code == 0:
            for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                await ctx.send("`"+txt+"`")

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emojis.check)
        else:
            await ctx.send(ret_cmd)

    ##############################################################
    # Command: gvj
    # Parameters: code allié (string), une liste de persos séparées par des espaces ou "all"
    # Purpose: Progrès dans le guide de voyage pour un perso
    # Display: Une ligne par requis du guide de voyage
    #          un score global à la fin
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='gvj',
                 brief="Progrès Guide de Voyage pour un Joueur",
                 help="Donne le progrès dans le guide de voyage pour un perso chez un joueur\n\n"\
                      "Exemple: go.gvj 192126111 all\n"\
                      "Exemple: go.gvj me SEE\n"\
                      "Exemple: go.gvj me thrawn JKL")
    async def gvj(self, ctx, allyCode, *characters):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            allyCode = await manage_me(ctx, allyCode, False)

            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
                return

            if type(allyCode)==list:
                await ctx.send("ERR: cette commande ne prend qu'un seul joueur en paramètre")
                await ctx.message.add_reaction(emojis.redcross)
                return

            if len(characters) == 0:
                characters = ["all"]
                
            err_code, ret_cmd = await go.print_gvj( characters, allyCode, 1)
            if err_code == 0:
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send("`"+txt+"`")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emojis.check)
            else:
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emojis.redcross)

        except discord.errors.NotFound as e:
            # original message deleted, no need to try answering or reacting
            pass
        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.gvj"+str(sys.exc_info()[0]))
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: raf
    # Parameters: code allié (string), une liste de persos séparées par des espaces ou "all"
    # Purpose: Reste à Farm dans le guide de voyage pour un perso
    # Display: Une ligne par requis du guide de voyage
    #          un score global à la fin
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='raf',
                 brief="Reste-A-Farm pour un joueur",
                 help="Donne le reste-à-farm (éclats de personnage, et kyrotech) dans le guide de voyage pour un perso chez un joueur\n\n"\
                      "Exemple: go.raf 192126111 all\n"\
                      "Exemple: go.raf me SEE\n"\
                      "Exemple: go.raf me thrawn JKL")
    async def raf(self, ctx, allyCode, *characters):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            allyCode = await manage_me(ctx, allyCode, False)

            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
                return

            if type(allyCode)==list:
                await ctx.send("ERR: cette commande ne prend qu'un seul joueur en paramètre")
                await ctx.message.add_reaction(emojis.redcross)
                return

            if len(characters) == 0:
                characters = ["all"]
                
            err_code, ret_cmd = await go.print_gvj( characters, allyCode, 2)
            if err_code == 0:
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send("`"+txt+"`")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emojis.check)
            else:
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emojis.redcross)

        except discord.errors.NotFound as e:
            # original message deleted, no need to try answering or reacting
            pass
        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.raf"+str(sys.exc_info()[0]))
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: gvg
    # Parameters: code allié (string),
    #               une liste de persos séparées par des espaces ou "all"
    # Purpose: Progrès dans le guide de voyage pour un perso
    # Display: Une ligne par perso - joueur, avec son score
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='gvg',
                 brief="Progrès Guide de Voyage pour la Guilde",
                 help="Donne le progrès dans le guide de voyage pour un perso dans la guilde\n\n"\
                      "Exemple: go.gvg 192126111 all\n"\
                      "Exemple: go.gvg me SEE\n"\
                      "Exemple: go.gvg me thrawn JKL\n"\
                      "La commande n'affiche que les 40 premiers.")
    async def gvg(self, ctx, allyCode, *characters):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            allyCode = await manage_me(ctx, allyCode, True)

            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
                return

            if type(allyCode)==list:
                await ctx.send("ERR: cette commande ne prend qu'un seul joueur en paramètre")
                await ctx.message.add_reaction(emojis.redcross)
                return

            if len(characters) == 0:
                characters = ["all"]

            err_code, ret_cmd = await go.print_gvg( characters, allyCode)
            if err_code == 0:
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send("`"+txt+"`")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emojis.check)
            else:
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emojis.redcross)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.raf"+str(sys.exc_info()[0]))
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: gvs
    # Parameters: code allié (string), perso ou ship
    # Purpose: Progrès dans le guide de voyage pour un perso dans le shard
    # Display: Une ligne par joueur, avec son score
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='gvs',
                 brief="Progrès Guide de Voyage pour un Shard",
                 help="Donne le progrès dans le guide de voyage pour un perso dans le shard\n\n"\
                      "Exemple: go.gvs me Profundity\n"\
                      "Exemple: go.gvg 123456789 Jabba")
    async def gvs(self, ctx, allyCode, *characters):
        await ctx.message.add_reaction(emojis.thumb)

        allyCode = await manage_me(ctx, allyCode, False)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emojis.redcross)
        else:
            if len(characters) != 1:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help gvs")
                await ctx.message.add_reaction(emojis.redcross)
                return

            err_code, ret_cmd = await go.print_gvs( characters, allyCode)
            if err_code == 0:
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send("`"+txt+"`")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emojis.check)
            else:
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: spj
    # Parameters: code allié (string) ou "me" / nom approximatif d'un perso
    # Purpose: stats vitesse et pouvoir d'un perso
    # Display: la vitess et le pouvoir
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='spj',
                 brief="Stats de Perso d'un Joueur",
                 help="Stats de Perso d'un Joueur\n\n"\
                      "Potentiellement trié par étoiles, gear ou une stat (ex: vitesse)\n"\
                      "Exemple: go.spj 123456789 JKR\n"\
                      "Exemple: go.spj me JKR -étoiles\n"\
                      "Exemple: go.spj me -v \"Dark Maul\" Bastila\n"\
                      "Exemple: go.spj me -p all")
    async def spj(self, ctx, allyCode, *characters):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            allyCode = await manage_me(ctx, allyCode, False)

            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
            else:
                list_options = []
                list_characters = []
                for item in characters:
                    if item[0] == "-":
                        list_options.append(item)
                    else:
                        list_characters.append(item)
                
                if len(list_characters)  == 0:
                    list_characters=['all']

                if len(list_options) <= 1:
                    ret_cmd = await go.print_character_stats( list_characters,
                        list_options, allyCode, False, None, None)
                else:
                    ret_cmd = 'ERR: merci de préciser au maximum une option de tri'
                    
                if ret_cmd[0:3] == 'ERR':
                    await ctx.send(ret_cmd)
                    await ctx.message.add_reaction(emojis.redcross)
                else:
                    #texte classique
                    for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                        await ctx.send("```"+txt+"```")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.spg"+str(sys.exc_info()[0]))
            await ctx.message.add_reaction(emojis.redcross)
    
    ##############################################################
    # Command: spg
    # Parameters: code allié (string) ou "me" / nom approximatif d'un perso
    # Purpose: stats vitesse et pouvoir d'un perso sur toute la guilde
    # Display: la vitess et le pouvoir
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='spg',
                 brief="Stats de Perso d'une Guilde",
                 help="Stats de Perso d'une Guilde\n\n"\
                         "Potentiellement trié par étoiles, gear ou une stat (ex: vitesse)\n"\
                      "Exemple: go.spg 123456789 JKR\n"\
                      "Exemple: go.spg me JKR -étoiles\n"\
                      "Exemple: go.spg me -v \"Dark Maul\"")
    async def spg(self, ctx, allyCode, *characters):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            allyCode = await manage_me(ctx, allyCode, True)

            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
            else:
                list_options = []
                list_characters = []
                for item in characters:
                    if item[0] == "-":
                        list_options.append(item)
                    else:
                        list_characters.append(item)
                
                if len(list_characters) > 0:
                    if len(list_options) <= 1:
                        ret_cmd = await go.print_character_stats( list_characters,
                            list_options, allyCode, True, None, None)
                    else:
                        ret_cmd = 'ERR: merci de préciser au maximum une option de tri'
                else:
                    ret_cmd = 'ERR: merci de préciser perso'
                    
                if ret_cmd[0:3] == 'ERR':
                    await ctx.send(ret_cmd)
                    await ctx.message.add_reaction(emojis.redcross)
                else:
                    #texte classique
                    for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                        await ctx.send("```"+txt+"```")

                    #Icône de confirmation de fin de commande dans le message d'origine
                    await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.spg"+str(sys.exc_info()[0]))
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: gdp
    # Parameters: code allié (string) ou "me"
    # Purpose: graph de distribution des PG des membres de la guilde
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='gdp',
                 brief="Graphique des PG d'une guilde",
                 help="Graphique des PG d'une guilde\n\n"\
                      "Exemple: go.gdp me\n"\
                      "Exemple: go.gdp 123456789\n"\
                      "Exemple: go.gdp -TW")
    async def gdp(self, ctx, allyCode):
        await bot_commands.gdp(ctx, allyCode)


    ##############################################################
    # Command: farmeqpt
    # Parameters: code allié (string) ou "me"
    #             liste de persos
    # Purpose: liste des équipements à farmer
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='farmeqpt',
                 brief="Liste des équipements pour up des persos",
                 help="Liste des équipements pour up des persos G13\n\n"\
                      "Exemple: go.farmeqpt me bensolo\n"\
                      "Exemple: go.farmeqpt me bensolo:R5\n"\
                      "Exemple: go.farmeqpt me guide:BKM\n"\
                      "Exemple: go.farmeqpt me tag:gungan")
    async def farmeqpt(self, ctx, allyCode, *list_alias):
        await bot_commands.farmeqpt(ctx, allyCode, list_alias)

    ##############################################################
    # Command: ggac
    # Parameters: code allié (string) ou "me"
    # Purpose: graph de distribution des rangs de GAC des membres de la guilde
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='ggac',
                 brief="Graphique des rangs de GAC d'une guilde",
                 help="Graphique des rangs de GAC d'une guilde\n\n"\
                      "Exemple: go.ggac me\n"\
                      "Exemple: go.ggac 123456789\n"\
                      "Exemple: go.ggac -TW")
    async def ggac(self, ctx, allyCode):
        await ctx.message.add_reaction(emojis.thumb)

        allyCode = await manage_me(ctx, allyCode, True)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emojis.redcross)
            return

        # Display the chart
        e, err_txt, image = await go.get_gac_distribution(allyCode)
        if e != 0:
            await ctx.send(err_txt)
            await ctx.message.add_reaction(emojis.redcross)
        else:
            with BytesIO() as image_binary:
                image.save(image_binary, 'PNG')
                image_binary.seek(0)
                await ctx.send(content = "",
                       file=File(fp=image_binary, filename='image.png'))

            await ctx.message.add_reaction(emojis.hourglass)

            # Now load all players from the guild
            await go.load_guild( allyCode, True, True)

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.remove_reaction(emojis.hourglass, bot.user)
            await ctx.message.add_reaction(emojis.check)

                
    ##############################################################
    # Command: ggv
    # Parameters: code allié (string) ou "me"
    #             nom du perso
    # Purpose: graph de progrès de GV du perso
    # Display: graph
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='ggv',
                 brief="Graphique de GV d'un perso",
                 help="Graphique de GV d'un perso\n\n"\
                      "Exemple: go.ggv me SEE\n"\
                      "Exemple: go.ggv me/chaton75 SEE\n"\
                      "Exemple: go.ggv me FARM\n"\
                      "Exemple: go.ggv 123456789 JMK")
    async def ggv(self, ctx, allyCode, *characters):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            allyCode = await manage_me(ctx, allyCode, False)

            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
                return

            if len(characters) == 0:
                characters = ["all"]

            if type(allyCode)==str:
                allyCodes = [allyCode]
            else:
                allyCodes = allyCode

            for allyCode in allyCodes:
                #First run a GVJ to ensure at least one result
                err_code, ret_cmd = await go.print_gvj( characters, allyCode, 1)
                if err_code != 0:
                    await ctx.send(ret_cmd)
                    await ctx.message.add_reaction(emojis.redcross)
                    return
            
            #Seoncd, display the graph
            err_code, err_txt, image = go.get_gv_graph( allyCodes, characters)
            if err_code != 0:
                await ctx.send(err_txt)
                await ctx.message.add_reaction(emojis.redcross)
                return

            #Display the output image
            with BytesIO() as image_binary:
                image.save(image_binary, 'PNG')
                image_binary.seek(0)
                await ctx.send(content = "",
                    file=File(fp=image_binary, filename='image.png'))

            await ctx.message.add_reaction(emojis.check)
            
        except discord.errors.NotFound as e:
            # original message deleted, no need to try answering or reacting
            pass
        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.ggv"+str(sys.exc_info()[0]))
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: graphj
    # IN: code allié (string) ou "me"
    # IN: nom du paramètre à afficher
    # Purpose: graph de progrès du paramètre chez le joueur
    # Display: graph
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='graphj',
                 brief="Graphique dans le temps chez un Joueur",
                 help="Graphique dans le temps chez un Joueur\n\n"\
                      "Exemple: go.graphj me modq #graph sur 12 mois\n" \
                      "Exemple: go.graphj me -Y modq #graph sur un an")
    async def graphj(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            args = list(args)
            if len(args) >= 2:
                list_allyCodes = args[0]
                list_params = args[1:]

                is_year = False
                if "-Y" in list_params:
                    list_params.remove("-Y")
                    is_year = True
                elif "-y" in list_params:
                    list_params.remove("-y")
                    is_year = True
                if len(list_params)<1:
                    await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help graphj")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                parameter = list_params[0]
            else:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help graphj")
                await ctx.message.add_reaction(emojis.redcross)
                return

            list_allyCodes = list_allyCodes.split('/')
            allyCodes = []
            for allyCode in list_allyCodes:
                allyCode = await manage_me(ctx, allyCode, False)

                if allyCode[0:3] == 'ERR':
                    await ctx.send(allyCode)
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                allyCodes.append(allyCode)

            e, err_txt, image = await go.get_player_time_graph( allyCodes, False, parameter, is_year)
            if e != 0:
                await ctx.send(err_txt)
                await ctx.message.add_reaction(emojis.redcross)
            else:
                with BytesIO() as image_binary:
                    image.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    await ctx.send(content = "",
                           file=File(fp=image_binary, filename='image.png'))
                await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.graphj"+str(sys.exc_info()[0]))
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: graphg
    # IN: code allié (string) ou "me"
    # IN: nom du paramètre à afficher
    # Purpose: graph de progrès du paramètre chez la guilde du joueur
    # Display: graph
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='graphg',
                 brief="Graphique dans le temps dans une guilde",
                 help="Graphique dans le temps dans une guilde\n\n"\
                      "Exemple: go.graphg me modq #graph sur 12 mois\n" \
                      "Exemple: go.graphg me -Y modq #graph sur un an")
    async def graphg(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            args = list(args)
            if len(args) >= 2:
                allyCode = args[0]
                list_params = args[1:]

                is_year = False
                if "-Y" in list_params:
                    list_params.remove("-Y")
                    is_year = True
                elif "-y" in list_params:
                    list_params.remove("-y")
                    is_year = True
                if len(list_params)<1:
                    await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help graphg")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                parameter = list_params[0]
            else:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help graphg")
                await ctx.message.add_reaction(emojis.redcross)
                return

            allyCode = await manage_me(ctx, allyCode, False)

            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
            else:
                e, err_txt, image = await go.get_player_time_graph( allyCode, True, parameter, is_year)
                if e != 0:
                    await ctx.send(err_txt)
                    await ctx.message.add_reaction(emojis.redcross)
                else:
                    with BytesIO() as image_binary:
                        image.save(image_binary, 'PNG')
                        image_binary.seek(0)
                        await ctx.send(content = "",
                               file=File(fp=image_binary, filename='image.png'))
                    await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.graphj"+str(sys.exc_info()[0]))
            await ctx.send("Erreur inconnue")
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: statqj
    # Parameters: code allié (string) ou "me"
    # Purpose: affiche le statqq d'un joueur
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='statqj',
                 brief="Affiche le StatQ d'un Joueur",
                 help="Affiche le StatQ d'un Joueur\n\n"\
                      "Exemple: go.statqj me\n"
                      "         go.statqj 123456789 gg\n"
                      "         go.statqj 123456789 tag:jedi\n"
                      "         go.statqj 123456789 -score")
    async def statqj(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            options = list(args)
            all_characters=False
            sort_option = "name"
            for arg in args:
                if arg=='-all':
                    all_characters=True
                    options.remove(arg)
                elif arg=='-score':
                    sort_option = "score"
                    options.remove(arg)
                elif arg=='-nom' or arg=='-name' or arg=='-perso':
                    sort_option = "name"
                    options.remove(arg)

            if len(options) == 1:
                allyCode = options[0]
                list_characters = ["all"]
            elif len(options) >= 2 and all_characters==False:
                allyCode = options[0]
                list_characters = options[1:]
            else:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help statqj")
                await ctx.message.add_reaction(emojis.redcross)
                return

            allyCode = await manage_me(ctx, allyCode, False)

            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
            else:
                e, t, dict_player = await go.load_player( allyCode, 1, False)
                if e!=0:
                    await ctx.send(t)
                    await ctx.message.add_reaction(emojis.redcross)
                    return
                
                # Get char IDs from list of alias
                if not "all" in list_characters:
                    list_unit_id, d_id_name, err_alias_txt = goutils.get_characters_from_alias(list_characters)
                else:
                    err_alias_txt = ""
                    list_unit_id = None

                # Get statq data
                ec, et, statq, list_statq = await connect_mysql.get_player_statq(allyCode)
                if ec!=0:
                    await ctx.send(et)
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                #get real unit names
                dict_units = data.get("unitsList_dict.json")
                dict_stat_names = {
                        "sd": "degSpe",
                        "cd": "degCrit",
                        "pd": "degPhys",
                        "protec": "protec",
                        "health": "santé",
                        "speed": "vitesse",
                        "tenacity": "ténacité",
                        "cc": "critChance",
                        "armor": "armure",
                        "potency": "pouvoir"}
                filtered_list = [x for x in list_statq if (list_unit_id==None or x[0] in list_unit_id)]
                list_with_char_names = [
                        [dict_units[x[0]]["name"]]
                        +[dict_stat_names[x[1]]]
                        +list(x[2:]) 
                        for x in filtered_list]
                if sort_option == "name":
                    list_statq_with_names = sorted(list_with_char_names)
                else: #score
                    list_statq_with_names = sorted(list_with_char_names, key=lambda x:(-x[4], x[0]))

                output_table = [['Perso', "Stat", "Valeur (mod)", "Objectif (progrès)", "Score"]] + list_statq_with_names
                t = Texttable()
                t.add_rows(output_table)
                t.set_deco(Texttable.BORDER|Texttable.HEADER|Texttable.VLINES)

                playerName = dict_player["name"]
                if "guildName" in dict_player:
                    guildName = dict_player["guildName"]
                    if guildName == None:
                        guildName = "*pas de guilde*"
                else:
                    guildName = "*pas de guilde*"

                first_msg=True
                for txt in goutils.split_txt(t.draw(), MAX_MSG_SIZE):
                    if first_msg:
                        if err_alias_txt != "":
                            err_alias_txt = 'WAR: impossible de reconnaître ce(s) nom(s) >> '+err_alias_txt+"\n"
                        await ctx.send("statQ de "+playerName+" ("+guildName+")\n"+err_alias_txt+'```' + txt + '```')
                        first_msg=False
                    else:
                        await ctx.send('```' + txt + '```')

                #Create image from table
                ec, et, image = portraits.get_image_from_texttable(t.draw())
                with BytesIO() as image_binary:
                    image.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    await ctx.send(file=File(fp=image_binary, filename='image.png'))

                if list_unit_id==None:
                    await ctx.send("StatQ = "+str(round(statq, 2)))

                await ctx.message.add_reaction(emojis.check)

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.statqj"+str(sys.exc_info()[0]))
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: statqg
    # Parameters: code allié (string) ou "me"
    # Purpose: affiche le statq de la guilde
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='statqg',
                 brief="Affiche le StatQ de la guilde",
                 help="Affiche le StatQ de la guilde\n\n"\
                      "Exemple: go.statqg me")
    async def statqg(self, ctx, allyCode):
        await ctx.message.add_reaction(emojis.thumb)

        allyCode = await manage_me(ctx, allyCode, True)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emojis.redcross)
            return

        e, t, dict_player = await go.load_player( allyCode, 1, False)
        if e!=0:
            await ctx.send(t)
            await ctx.message.add_reaction(emojis.redcross)
            return

        query = "SELECT name, statq FROM players WHERE guildName=(SELECT guildName from players WHERE allyCode="+allyCode+") ORDER BY statq DESC, name"
        goutils.log2("DBG", query)
        output = connect_mysql.text_query(query)

        output_txt=''
        for row in output:
            output_txt+=str(row)+'\n'
        goutils.log2('INFO', output_txt)
        for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
            await ctx.send('`' + txt + '`')

        await ctx.message.add_reaction(emojis.check)

    ##############################################################
    # Command: modqg
    # Parameters: code allié (string) ou "me"
    # Purpose: affiche le modq de la guilde
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='modqg',
                 brief="Affiche le modQ de la guilde",
                 help="Affiche le modQ de la guilde\n\n"\
                      "Exemple: go.modqg me")
    async def modqg(self, ctx, allyCode):
        await ctx.message.add_reaction(emojis.thumb)

        allyCode = await manage_me(ctx, allyCode, True)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emojis.redcross)
            return

        query = "SELECT name, modq FROM players WHERE guildName=(SELECT guildName from players WHERE allyCode="+allyCode+") ORDER BY modq DESC, name"
        goutils.log2("DBG", query)
        output = connect_mysql.text_query(query)

        output_txt=''
        for row in output:
            output_txt+=str(row)+'\n'
        goutils.log2('INFO', output_txt)
        for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
            await ctx.send('`' + txt + '`')

        await ctx.message.add_reaction(emojis.check)

    ##############################################################
    # Command: ppj
    # Parameters: code allié (string) ou "me" / nom approximatif des perso
    # Purpose: afficher une image des portraits choisis
    # Display: l'image produite
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='ppj',
                 brief="Portraits de Perso d'un Joueur",
                 help="Portraits de Perso d'un Joueur\n"\
                      "Exemple: go.ppj 123456789 JKR\n"\
                      "Exemple: go.ppj me -v \"Dark Maul\" Bastila\n")
    async def ppj(self, ctx, allyCode, *characters):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            allyCode = await manage_me(ctx, allyCode, False)

            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
            else:
                if len(characters) > 0:
                    e, ret_cmd, images = await go.get_character_image( [[list(characters),
                                                        allyCode, '']], False, True, '', None)
                        
                    if e == 0:
                        for image in images:
                            with BytesIO() as image_binary:
                                image.save(image_binary, 'PNG')
                                image_binary.seek(0)
                                await ctx.send(content = ret_cmd,
                                       file=File(fp=image_binary, filename='image.png'))

                        #Icône de confirmation de fin de commande dans le message d'origine
                        await ctx.message.add_reaction(emojis.check)

                    else:
                        ret_cmd += 'ERR: merci de préciser un ou plusieurs persos'
                        await ctx.send(ret_cmd)
                        await ctx.message.add_reaction(emojis.redcross)

                else:
                    ret_cmd = 'ERR: merci de préciser un ou plusieurs persos'
                    await ctx.send(ret_cmd)
                    await ctx.message.add_reaction(emojis.redcross)                

        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.ppj"+str(sys.exc_info()[0]))
            await ctx.message.add_reaction(emojis.redcross)
                
    ##############################################################
    # Command: rgt
    # Parameters: code allié (string) ou "me"
    #             liste des persos du joueur
    #             séparateur "VS"
    #             code allié adversaire
    #             un perso de l'adversaire
    # Purpose: afficher une image avec les 2 équipes et un "SUCCESS"
    # Display: l'image produite
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='rgt',
                 brief="Image d'un Résultat en Guerre de Territoire",
                 help="Image d'un Résultat en Guerre de Territoire\n"\
                      "Exemple: go.rgt me GAS echo cra fives rex VS DR\n")
    async def rgt(self, ctx, *options):
        await ctx.message.add_reaction(emojis.thumb)

        #Ensure command is launched from a server, not a DM
        if ctx.guild == None:
            await ctx.send("ERR: commande non autorisée depuis un DM")
            await ctx.message.add_reaction(emojis.redcross)
            return

        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
        if ec!=0:
            await ctx.send('ERR: '+et)
            await ctx.message.add_reaction(emojis.redcross)
            return

        guild_id = bot_infos["guild_id"]
        if guild_id == None:
            await ctx.send("ERR: vous devez avoir un warbot pour lancer cette commande")
            await ctx.message.add_reaction(emojis.redcross)
            return

        # Extract command options
        if not ("VS" in options):
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help rgt")
            await ctx.message.add_reaction(emojis.redcross)
            return

        pos_vs = options.index("VS")
        if pos_vs < 2:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help rgt")
            await ctx.message.add_reaction(emojis.redcross)
            return

        allyCode_attack = options[0]
        list_char_attack = options[1:pos_vs]

        allyCode_attack = await manage_me(ctx, allyCode_attack, False)
        if allyCode_attack[0:3] == 'ERR':
            await ctx.send(allyCode_attack)
            await ctx.message.add_reaction(emojis.redcross)
            return

        if len(options) != (pos_vs+2):
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help rgt")
            await ctx.message.add_reaction(emojis.redcross)
            return

        #only a character is given
        character_defense = options[pos_vs+1]

        # Computes images
        e, ret_cmd, images = await go.get_tw_battle_image( list_char_attack, allyCode_attack, 
                                             character_defense, guild_id)
                        
        if e == 0:      
            #regroup images into bigger ones containing several teams
            list_big_images = []
            cur_big_image = None
            cur_big_image_sizes = []
            for image in images:
                w, h = image.size
                if sum(cur_big_image_sizes) == 0 or (sum(cur_big_image_sizes) + h <= 1000):
                    cur_big_image = portraits.add_vertical(cur_big_image, image)
                    cur_big_image_sizes.append(h)
                    #print("add "+str(cur_big_image_sizes))
                else:
                    list_big_images.append([cur_big_image, cur_big_image_sizes])
                    cur_big_image = image
                    cur_big_image_sizes = [h]
                    #print("new "+str(h))

            list_big_images.append([cur_big_image, cur_big_image_sizes])

            first_image = True
            cur_list_msgIDs = []
            for [image, sizes] in list_big_images:
                with BytesIO() as image_binary:
                    image.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    new_msg = await ctx.send(content = ret_cmd,
                           file=File(fp=image_binary, filename='image.png'))
                    for letter_idx in range(len(sizes)-first_image):
                        emojis.letter = emojis.letters[letter_idx]
                        await new_msg.add_reaction(emojis.letter)
                    cur_list_msgIDs.append([new_msg, sizes])
                first_image = False

            # Add the message list to the global message list, waiting for reaction
            list_tw_opponent_msgIDs.append([ctx.author, cur_list_msgIDs])

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emojis.check)
        else:
            await ctx.send(ret_cmd)
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: gsp
    # Parameters: code allié (string) ou "me"
    #             un perso
    #             une statistique
    # Purpose: afficher un raph des stats de ce persos sur les G13 connus
    #          et la position du joueur dans ce graph
    # Display: l'image du graph
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='gsp',
                 brief="Graphique d'une Statistique d'un Perso",
                 help="Graphique d'une Statistique d'un Perso\n"\
                      "Exemple: go.gsp me GAS vitesse\n" \
                      "Exemple: go.gsp me GAS:R8 vitesse (pour filtrer sur les GAS R8)\n" \
                      "Exemple: go.gsp me GAS:R5+ vitesse (pour filtrer sur les GAS R5 et plus)\n" \
                      "Exemple: go.gsp me GAS:R7- vitesse (pour filtrer sur les GAS R7 et moins)")
    async def gsp(self, ctx, *options):
        await ctx.message.add_reaction(emojis.thumb)

        if len(options) != 3:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help gsp")
            await ctx.message.add_reaction(emojis.redcross)
            return

        allyCode = options[0]
        alias = options[1]
        stat = options[2]
            
        allyCode= await manage_me(ctx, allyCode, False)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emojis.redcross)
            return

        e, err_txt, image = await go.get_stat_graph( allyCode, alias, stat)
        if e == 0:
            with BytesIO() as image_binary:
                image.save(image_binary, 'PNG')
                image_binary.seek(0)
                await ctx.send(content = err_txt,
                       file=File(fp=image_binary, filename='image.png'))
            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emojis.check)
        else:
            await ctx.send(err_txt)
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: erj
    # Parameters: player idenfier
    # Purpose: summary of roster evolution for a player
    # Display: list
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='erj',
                 brief="Evolution du Roster d'un Joueur",
                 help="Evolution du roster d'un joueur sur 30 jours\n"\
                      "Exemple: go.erj me")
    async def erj(self, ctx, allyCode):
        await ctx.message.add_reaction(emojis.thumb)

        allyCode= await manage_me(ctx, allyCode, False)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emojis.redcross)
            return

        e, ret_cmd = await go.print_erx( allyCode, 30, False)
        if e == 0:
            #texte classique
            for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                await ctx.send(txt)

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emojis.check)
        else:
            await ctx.send(ret_cmd)
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: erg
    # Parameters: player idenfier
    # Purpose: summary of roster evolution for a guild
    # Display: list
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='erg',
                 brief="Evolution du Roster d'une Guilde",
                 help="Evolution du roster d'un joueur sur 30 jours\n"\
                      "Exemple: go.erg me")
    async def erg(self, ctx, allyCode):
        await ctx.message.add_reaction(emojis.thumb)

        allyCode= await manage_me(ctx, allyCode, False)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emojis.redcross)
            return

        e, ret_cmd = await go.print_erx( allyCode, 30, True)
        if e == 0:
            #texte classique
            for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                await ctx.send(txt)

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emojis.check)
        else:
            await ctx.send(ret_cmd)
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: loj
    # Parameters: player idenfier
    # Purpose: list of omicrons of a player
    # Display: list
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='loj',
                 brief="Liste des Omicrons d'un Joueur",
                 help="Liste des Omicrons d'un Joueur\n"\
                      "Exemple: go.loj 123456789 \n"\
                      "Exemple: go.loj 123456789 Mara\n"\
                      "Exemple: go.loj 123456789 mode:GA")
    async def loj(self, ctx, *args):
        await ctx.message.add_reaction(emojis.thumb)

        options = list(args)
        all_omicrons=False
        for arg in args:
            if arg=='-all':
                all_omicrons=True
                options.remove(arg)

        if len(options) == 1:
            allyCode = options[0]
            list_characters = ["all"]
        elif len(options) >= 2:
            allyCode = options[0]
            list_characters = options[1:]
        else:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help loj")
            await ctx.message.add_reaction(emojis.redcross)
            return

        allyCode= await manage_me(ctx, allyCode, False)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emojis.redcross)
            return

        e, err_txt, txt_lines = await go.print_lox( allyCode, list_characters, all_omicrons=all_omicrons)
        if e == 0 and len(txt_lines) >0:
            if err_txt != "":
                await ctx.send(err_txt)
            output_txt=''
            for row in txt_lines:
                output_txt+=str(row)+'\n'
            for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                await ctx.send('`' + txt + '`')
            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emojis.check)
        elif e == 0:
            await ctx.send("Aucun omicron trouvé pour "+allyCode)
            await ctx.message.add_reaction(emojis.check)
        else:
            await ctx.send(err_txt)
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: log
    # Parameters: player idenfier
    # Purpose: list of omicrons of a guild
    # Display: list
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='log',
                 brief="Liste des Omicrons d'une Guilde",
                 help="Liste des Omicrons d'une Guilde\n"\
                      "Exemple: go.log 123456789 \n"\
                      "Exemple: go.log 123456789 Mara\n"\
                      "Exemple: go.log 123456789 mode:TW")
    async def log(self, ctx, *args):
        await ctx.message.add_reaction(emojis.thumb)

        if len(args) == 1:
            allyCode = args[0]
            list_characters = ["all"]
        elif len(args) >= 2:
            allyCode = args[0]
            list_characters = args[1:]
        else:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help log")
            await ctx.message.add_reaction(emojis.redcross)
            return

        allyCode= await manage_me(ctx, allyCode, True)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emojis.redcross)
            return

        e, err_txt, txt_lines = await go.print_lox( allyCode, list_characters, compute_guild=True)
        if e == 0 and len(txt_lines) >0:
            if err_txt != "":
                await ctx.send(err_txt)
            output_txt=''
            for row in txt_lines:
                output_txt+=str(row)+'\n'
            for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                await ctx.send('`' + txt + '`')
            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emojis.check)
        elif txt_lines!= None and len(txt_lines)==0:
            await ctx.send("Aucun omicron détecté")
            await ctx.message.add_reaction(emojis.check)
        else:
            await ctx.send(err_txt)
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: dtcg
    # Parameters: player idenfier
    # Purpose: list of datacrons of a guild
    # Display: list
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='dtcg',
                 brief="Liste des Datacrons d'une Guilde",
                 help="Liste des Datacrons d'une Guilde\n"\
                      "Exemple: go.dtcg 123456789 \n"\
                      "Exemple: go.dtcg 123456789 Boushh")
    async def dtcg(self, ctx, *args):
        await ctx.message.add_reaction(emojis.thumb)

        args = list(args)

        output_channel = ctx.message.channel
        with_mentions = False
        for arg in args:
            if arg.startswith('<#') or arg.startswith('https://discord.com/channels/'):
                if not officer_command(ctx):
                    await ctx.send("ERR: l'envoi des résultats dans un autre channel est réservé aux officiers")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                output_channel, err_msg = await get_channel_from_channelname(ctx, arg)
                with_mentions = True
                if output_channel == None:
                    await ctx.send('**ERR**: '+err_msg)
                    output_channel = ctx.message.channel
                    with_mentions = False
                args.remove(arg)

        if len(args) == 1:
            allyCode = args[0]
            filter_txt = None
        elif len(args) == 2:
            allyCode = args[0]
            filter_txt = args[1]
        else:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help dtcg")
            await ctx.message.add_reaction(emojis.redcross)
            return

        allyCode= await manage_me(ctx, allyCode, True)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emojis.redcross)
            return

        e, err_txt, output_txt = await go.print_guild_dtc(allyCode, filter_txt, with_mentions)
        if e == 0 and len(output_txt) >0:
            for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                await output_channel.send(txt)

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emojis.check)
        elif len(output_txt)==0:
            await ctx.send("Aucun datacron détecté")
            await ctx.message.add_reaction(emojis.check)
        else:
            await ctx.send(err_txt)
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: ntg
    # Parameters: 
    #    IN: player from the guild
    #    IN: amount of teams per TW territory
    #    IN: [optional] list of players that do not participate in the TW
    # Purpose: give a recommendation of teams per player in defense
    # Display: one recommendation per group of 1M of PG
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='ntg',
                 brief="Nombre de Teams en GT",
                 help="Nombre de Teams en GT\n\n"\
                      "Exemple : go.ntg me 27\n"\
                      "Exemple : go.ntg 123456789 23 toto123 345123678")
    async def ntg(self, ctx, *args):
        await ctx.message.add_reaction(emojis.thumb)

        if len(args) < 2:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help ntg")
            await ctx.message.add_reaction(emojis.redcross)
            return
        else:
            ac_guild = await manage_me(ctx, args[0], True)
            if ac_guild[0:3] == 'ERR':
                await ctx.send(ac_guild)
                await ctx.message.add_reaction(emojis.redcross)
                return

            try:
                team_count = int(args[1])
            except Exception as e:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help ntg")
                await ctx.message.add_reaction(emojis.redcross)
                return

            list_ac_nonplayers = []
            for player in args[2:]:
                ac = await manage_me(ctx, player, False)
                if ac[0:3] == 'ERR':
                    await ctx.send(ac)
                    await ctx.message.add_reaction(emojis.redcross)
                    return
                list_ac_nonplayers.append(ac)

            query = "SELECT FLOOR((char_gp+ship_gp)/1000000) AS bucket, count(*) FROM players " \
                  + "WHERE guildName = (SELECT guildName FROM players WHERE allyCode="+ac_guild+") "
            if len(list_ac_nonplayers) > 0:
                query += "AND NOT allyCode IN "+str(tuple(list_ac_nonplayers)).replace(",)", ")")+" "
            query+= "GROUP BY bucket " \
                  + "ORDER BY bucket"

            goutils.log2("DBG", query)
            bucket_count = connect_mysql.get_table(query)

            target_count = 10 * team_count
            actual_count = 0
            multiplier = 1.0
            total_players = sum([x[1] for x in bucket_count])
            total_pg = sum([(x[0]+0.5)*x[1] for x in bucket_count])
            goutils.log2("DBG", "total_players="+str(total_players))
            goutils.log2("DBG", "total_pg="+str(total_pg))
            while actual_count < target_count:
                pg_teams = ""
                actual_count = 0
                for b_c in bucket_count:
                    teams = int(round(b_c[0] * target_count / total_pg * multiplier, 0))
                    actual_count += teams * b_c[1]

                    if b_c[1] == 1:
                        pg_teams += str(b_c[1])+" joueur"
                    else:
                        pg_teams += str(b_c[1])+" joueurs"

                    pg_teams += " de "+str(b_c[0])+" à "+str(b_c[0]+1)+" M de PG : "

                    if teams == 1:
                        pg_teams += str(teams)+" team\n"
                    else:
                        pg_teams += str(teams)+" teams\n"

                multiplier += 0.01
                goutils.log2("DBG", "actual_count="+str(actual_count))

            pg_teams = "**Nombre de teams recommandé à poser en défense pour la GT**\n" + pg_teams
            await ctx.send(pg_teams)
            await ctx.message.add_reaction(emojis.check)


    ##############################################################
    # Command: cpg
    # Parameters: joueur, liste de persos
    # Purpose: compte les persos listés groupés par étoiles et gear
    # Display: un tableau
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='cpg', brief="Compte les persos d'une Guilde",
                      help="Compte les persos d'une Guilde\n" \
                              "Exemple : go.cpg me > les GL par défaut\n" \
                              "Exemple : go.cpg me SEE Maul GAS > une liste spécifique\n" \
                              "Exemple : go.cpg -TW SEE Maul GAS > compare avec la guilde adverse en TW")
    async def cpg(self, ctx, *args):
        try:
            await ctx.message.add_reaction(emojis.thumb)

            #Check arguments
            args = list(args)

            if len(args) == 0:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.cpg cpg")
                await ctx.message.add_reaction(emojis.redcross)
                return


            if args[0] == "-TW":
                #Ensure command is launched from a server, not a DM
                if ctx.guild == None:
                    await ctx.send("ERR: commande non autorisée depuis un DM avec l'option -TW")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                #get bot config from DB
                ec, et, bot_infos = connect_mysql.get_warbot_info(ctx.guild.id, ctx.message.channel.id)
                if ec!=0:
                    await ctx.send('ERR: '+et)
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                guild_id = bot_infos["guild_id"]
                if guild_id == None:
                    await ctx.send("ERR: vous devez avoir un warbot pour utiliser l'option -TW")
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                tw_mode = True
                ec, et, opp_allyCode = await connect_rpc.get_tw_opponent_leader(guild_id)
                if ec != 0:
                    await ctx.send(et)
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                ec, et, bot_player = await connect_rpc.get_bot_player_data(guild_id, False)
                if ec != 0:
                    await ctx.send(et)
                    await ctx.message.add_reaction(emojis.redcross)
                    return
                allyCode = str(bot_player["allyCode"])
            else:
                tw_mode = False
                allyCode = args[0]
                allyCode = await manage_me(ctx, allyCode, False)
                guild_id = None

            if "-TW" in args[1:]:
                await ctx.send("ERR: l'option -TW doit être utilisée en première position. Consulter go.help cpg pour plus d'infos.")
                await ctx.message.add_reaction(emojis.redcross)
                return

            if len(args) == 1:
                #default list
                unit_list = ['executor', 'profundity', 'leviathan', 'GLrey', 'SLKR', 'JML', 'SEE', 'JMK', 'LV', 'Jabba', 'glLeia']
            else:
                unit_list = args[1:]

                    
            if allyCode[0:3] == 'ERR':
                await ctx.send(allyCode)
                await ctx.message.add_reaction(emojis.redcross)
                return

            # get the DB information for home guild
            if tw_mode:
                ec, et, output_dict = await go.count_players_with_character(allyCode, unit_list, None, "homeGuild")
            else:
                ec, et, output_dict = await go.count_players_with_character(allyCode, unit_list, None, None)
            if ec != 0:
                await ctx.send(et)
                await ctx.message.add_reaction(emojis.redcross)
                return

            dict_units = data.get("unitsList_dict.json")
            if not tw_mode:
                output_table = [["Perso", "Gear", "Total"]]
                for unit_id in output_dict:
                    unit_name = dict_units[unit_id]['name']
                    unit_gear=''
                    unit_total=''
                    for gear in output_dict[unit_id]:
                        total = output_dict[unit_id][gear][0]

                        if dict_units[unit_id]['combatType'] == 2:
                            #ship, we keep only rarity
                            gear = gear[:2]

                        unit_gear += gear+"\n"
                        unit_total += str(total)+"\n"
                    output_table.append([unit_name, unit_gear.rstrip(), unit_total.rstrip()])

                t = Texttable()
                t.add_rows(output_table)

                for txt in goutils.split_txt(t.draw(), MAX_MSG_SIZE):
                    await ctx.send('`' + txt + '`')
            else:
                #display first the home stats
                output_table = [["Perso", "Gear", "Inscrits\n(posé en def)", "Adversaire\n(vu en def)"]]
                for unit_id in output_dict:
                    unit_name = dict_units[unit_id]['name']
                    unit_gear=''
                    unit_total=''
                    unit_def=''
                    for gear in output_dict[unit_id]:
                        total = output_dict[unit_id][gear][0]
                        def_count = output_dict[unit_id][gear][1]

                        if dict_units[unit_id]['combatType'] == 2:
                            gear = gear[:2]

                        unit_gear += gear+"\n"
                        unit_total += str(total)+" ("+str(def_count)+")\n"
                    output_table.append([unit_name, unit_gear.rstrip(), unit_total.rstrip(), '?'])

                t = Texttable()
                t.add_rows(output_table)

                list_msg = []
                for txt in goutils.split_txt(t.draw(), MAX_MSG_SIZE):
                    new_msg = await ctx.send('`' + txt + '`')
                    list_msg.append(new_msg)

                #Icône d'attente
                await ctx.message.add_reaction(emojis.hourglass)

                # Now load all players from the guild
                await go.load_guild(opp_allyCode, True, True)

                ec, et, opp_dict = await go.count_players_with_character(opp_allyCode, unit_list, guild_id, "awayGuild")
                for unit_id in opp_dict:
                    if not unit_id in output_dict:
                        output_dict[unit_id] = {}
                    for gear in opp_dict[unit_id]:
                        if not gear in output_dict[unit_id]:
                            output_dict[unit_id][gear] = ['', '']
                        opp_total = opp_dict[unit_id][gear][0]
                        opp_def = opp_dict[unit_id][gear][1]
                        output_dict[unit_id][gear].append(opp_total)
                        output_dict[unit_id][gear].append(opp_def)

                #Remove previous table
                for msg in list_msg:
                    await msg.delete()

                #display the home + away stats
                output_table = [["Perso", "Gear", "Inscrits\n(posé en def)", "Adversaire\n(vu en def)"]]
                for unit_id in output_dict:
                    unit_name = dict_units[unit_id]['name']
                    unit_gear=''
                    unit_total=''
                    unit_def=''
                    opp_total=''
                    for gear in output_dict[unit_id]:
                        # gear 
                        if dict_units[unit_id]['combatType'] == 1:
                            unit_gear += gear+"\n"
                        else:
                            unit_gear += gear[:2]+"\n"
 
                        #Home count
                        total = output_dict[unit_id][gear][0]
                        def_count = output_dict[unit_id][gear][1]
                        if total != '' and total > 0:
                            unit_total += str(total)+" ("+str(def_count)+")\n"
                        else:
                            unit_total += "\n"

                        # Opponent count
                        if len(output_dict[unit_id][gear])==3:
                            total = output_dict[unit_id][gear][2]
                            def_count = 0
                        elif len(output_dict[unit_id][gear])==4:
                            total = output_dict[unit_id][gear][2]
                            def_count = output_dict[unit_id][gear][3]
                        else:
                            total = 0

                        if total > 0:
                            opp_total += str(total)+" ("+str(def_count)+")\n"
                        else:
                            opp_total += "\n"

                    output_table.append([unit_name, unit_gear.rstrip(), unit_total.rstrip(), opp_total.rstrip()])

                t = Texttable()
                t.add_rows(output_table)

                for txt in goutils.split_txt(t.draw(), MAX_MSG_SIZE):
                    await ctx.send('`' + txt + '`')

                await ctx.message.remove_reaction(emojis.hourglass, bot.user)

            await ctx.message.add_reaction(emojis.check)
        except Exception as e:
            goutils.log2("ERR", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(ctx.message.channel.guild, "Exception in go.cpg"+str(sys.exc_info()[0]))
            await ctx.message.add_reaction(emojis.redcross)

    ##############################################################
    # Command: shard
    # Parameters: player, sub-commands
    # Purpose: manage members of player's shard
    # Display: depending of the sub-command
    ##############################################################
    @commands.check(member_command)
    @commands.command(name='shard', brief="Gère les shards du joueur",
                 help="Gère les shards du joueur\n"\
                      "Exemple : go.shard me char 123456789 > ajoute le joueur 123456789 à la liste des joueurs  de l'arène de persos\n"\
                      "Exemple : go.shard me ship 123456789 > ajoute le joueur 123456789 à la liste des joueurs  de l'arène de vaisseaux\n"\
                      "Exemple : go.shard me ship -123456789 > retire le joueur 123456789 de la liste des joueurs  de l'arène de vaisseaux\n"\
                      "Exemple : go.shard me char > affiche la liste des joueurs connus de l'arène de persos")
    async def shard(self, ctx, *args):
        await ctx.message.add_reaction(emojis.thumb)

        if len(args) != 3 and len(args) != 2:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help shard")
            await ctx.message.add_reaction(emojis.redcross)
            return

        allyCode = args[0]
        allyCode = await manage_me(ctx, allyCode, False)
                
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emojis.redcross)
            return

        shard_type = args[1]
        if shard_type != "char" and shard_type != "ship":
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help shard")
            await ctx.message.add_reaction(emojis.redcross)
            return

        # get the DB information
        player_shard, n, gn = connect_mysql.get_shard_from_player(allyCode, shard_type)

        if len(args) == 2:
            #list the content of the shard
            output = connect_mysql.get_shard_list(player_shard, shard_type, True)
            output_txt = ""
            for row in output:
                output_txt+=str(row)+'\n'
            for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                await ctx.send('`' + txt + '`')
        else:
            # add or remove player from shard
            shardmate_ac = args[2]
            remove_player = False
            force_merge = False

            if shardmate_ac[0] == "-":
                remove_player = True
                shardmate_ac = shardmate_ac[1:]
            elif shardmate_ac[0] == "+":
                force_merge = True
                shardmate_ac = shardmate_ac[1:]

            shardmate_ac = await manage_me(ctx, shardmate_ac, False)

            if shardmate_ac[0:3] == 'ERR':
                await ctx.send(shardmate_ac)
                await ctx.message.add_reaction(emojis.redcross)
                return

            if remove_player:
                await ctx.send("Suppression du shard pas encore implémentée, demander à l'admin")
                await ctx.message.add_reaction(emojis.redcross)
                return
            else:
                #First ensure that the player exists in DB
                e, t, player_now = await go.load_player(shardmate_ac, -1, False)
                if e!=0:
                    await ctx.send(t)
                    await ctx.message.add_reaction(emojis.redcross)
                    return

                ec, et, ret = connect_mysql.add_player_to_shard(shardmate_ac, player_shard, shard_type, force_merge)
                if ec == 1:
                    await ctx.send("Voulez-vous vraiment fusionner ces 2 shards "+shard_type+ " ?")
                    target_list = connect_mysql.get_shard_list(ret[0], shard_type, True)
                    for row in target_list:
                        output_txt+=str(row)+'\n'
                    player_list = connect_mysql.get_shard_list(ret[1], shard_type, True)
                    output_txt += "et\n"
                    for row in player_list:
                        output_txt+=str(row)+'\n'
                    output_txt += ">> pour cela lancez la commande go.shard "+allyCode+" "+shard_type+ " +"+shardmate_ac

                    for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                        await ctx.send('`' + txt + '`')
                else:
                    output_txt = et
                    await ctx.send(et)

        await ctx.message.add_reaction(emojis.check)


##############################################################
# MAIN EXECUTION
##############################################################
async def main():
    global bot_test_mode
    global bot_background_tasks
    global bot_on_message
    global bot

    #Init bot
    goutils.log2("INFO", "Starting...")
    # Use command-line parameters
    if len(sys.argv) > 1:
        goutils.log2("INFO", "TEST MODE - options="+str(sys.argv[1:]))
        bot_test_mode = True
        if "noloop" in sys.argv[1:]:
            goutils.log2("INFO", "Disable loops")
            bot_background_tasks = False
        if "nomsg" in sys.argv[1:]:
            goutils.log2("INFO", "Disable on_message")
            bot_on_message = False

    #Clean tmp files
    list_cache_files = os.listdir("CACHE")
    for cache_file in list_cache_files:
        if cache_file.endswith(".tmp"):
            os.remove("CACHE/"+cache_file)
    parallel_work.clean_cache()

    #Ajout des commandes groupées par catégorie
    goutils.log2("INFO", "Create Cogs...")
    await bot.add_cog(AdminCog(bot))
    await bot.add_cog(ServerCog(bot))
    await bot.add_cog(OfficerCog(bot))
    await bot.add_cog(MemberCog(bot))
    await bot.add_cog(ModsCog(bot))
    await bot.add_cog(TbCog(bot))
    await bot.add_cog(TwCog(bot))
    await bot.add_cog(BronziumCog(bot))
    await bot.add_cog(AuthCog(bot))

    if bot_background_tasks:
        await bot.add_cog(Loop60secsCog(bot))
        await bot.add_cog(Loop5minutes(bot))
        await bot.add_cog(Loop60minutes(bot))

    #Lancement du bot
    goutils.log2("INFO", "Run bot...")
    await bot.start(TOKEN, reconnect=True)

if __name__ == "__main__":
    asyncio.run(main())


