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
from discord.ext import commands
from discord import Activity, ActivityType, Intents, File, GroupChannel, errors as discorderrors
from io import BytesIO
from requests import get
import traceback

import go
import goutils
import connect_gsheets
import connect_warstats
import connect_mysql
import portraits
import data

TOKEN = config.DISCORD_BOT_TOKEN
intents = Intents.default()
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix=['go.', 'Go.', 'GO.'], intents=intents)
guild_timezone=timezone(config.GUILD_TIMEZONE)
bot_uptime=datetime.datetime.now(guild_timezone)
MAX_MSG_SIZE = 1900 #keep some margin for extra formating characters
list_alerts_sent_to_admin = []
bot_test_mode = False
first_bot_loop_5minutes = True

#https://til.secretgeek.net/powershell/emoji_list.html
emoji_thumb = '\N{THUMBS UP SIGN}'
emoji_thumbdown = '\N{THUMBS DOWN SIGN}'
emoji_check = '\N{WHITE HEAVY CHECK MARK}'
emoji_error = '\N{CROSS MARK}'
emoji_hourglass = '\N{HOURGLASS}'
emoji_letters = ['\N{REGIONAL INDICATOR SYMBOL LETTER A}', \
                 '\N{REGIONAL INDICATOR SYMBOL LETTER B}', \
                 '\N{REGIONAL INDICATOR SYMBOL LETTER C}', \
                 '\N{REGIONAL INDICATOR SYMBOL LETTER D}', \
                 '\N{REGIONAL INDICATOR SYMBOL LETTER E}', \
                 '\N{REGIONAL INDICATOR SYMBOL LETTER F}', \
                 '\N{REGIONAL INDICATOR SYMBOL LETTER G}', \
                 '\N{REGIONAL INDICATOR SYMBOL LETTER H}', \
                 '\N{REGIONAL INDICATOR SYMBOL LETTER I}']

dict_BT_missions={}
dict_BT_missions['HLS']={}
dict_BT_missions['HLS']['Rebel Base Mission']='HLS1-top'
dict_BT_missions['HLS']['Ion Cannon Mission']='HLS2-top'
dict_BT_missions['HLS']['Overlook Mission']='HLS2-bottom'
dict_BT_missions['HLS']['Rear Airspace Mission']='HLS3-top'
dict_BT_missions['HLS']['Rear Trench Mission']='HLS3-mid'
dict_BT_missions['HLS']['Power Generator Mission']='HLS3-bottom'
dict_BT_missions['HLS']['Forward Airspace Mission']='HLS4-top'
dict_BT_missions['HLS']['Forward Trench Mission']='HLS4-mid'
dict_BT_missions['HLS']['Outer Pass Mission']='HLS4-bottom'
dict_BT_missions['HLS']['Contested Airspace Mission']='HLS5-top'
dict_BT_missions['HLS']['Snowfields Mission']='HLS5-mid'
dict_BT_missions['HLS']['Forward Stronghold Mission']='HLS5-bottom'
dict_BT_missions['HLS']['Imperial Fleet Mission']='HLS6-top'
dict_BT_missions['HLS']['Imperial Flank Mission']='HLS6-mid'
dict_BT_missions['HLS']['Imperial Landing Mission']='HLS6-bottom'
dict_BT_missions['HDS']={}
dict_BT_missions['HDS']['Imperial Flank Mission']='HDS1-top'
dict_BT_missions['HDS']['Imperial Landing Mission']='HDS1-bottom'
dict_BT_missions['HDS']['Snowfields Mission']='HDS2-top'
dict_BT_missions['HDS']['Forward Stronghold Mission']='HDS2-bottom'
dict_BT_missions['HDS']['Imperial Fleet']='HDS3-top'
dict_BT_missions['HDS']['Ion Cannon Mission']='HDS3-mid'
dict_BT_missions['HDS']['Outer Pass Mission']='HDS3-bottom'
dict_BT_missions['HDS']['Contested Airspace']='HDS4-top'
dict_BT_missions['HDS']['Power Generator Mission']='HDS4-mid'
dict_BT_missions['HDS']['Rear Trench Mission']='HDS4-bottom'
dict_BT_missions['HDS']['Forward Airspace Fleet']='HDS5-top'
dict_BT_missions['HDS']['Forward Trenches Mission']='HDS5-mid'
dict_BT_missions['HDS']['Overlook Mission Mission']='HDS5-bottom'
dict_BT_missions['HDS']['Rear Airspace']='HDS6-top'
dict_BT_missions['HDS']['Rebel Base (Main Entrance) Mission']='HDS6-mid'
dict_BT_missions['HDS']['Rebel Base (South Entrance) Mission']='HDS6-bottom'
dict_BT_missions['GLS']={}
dict_BT_missions['GLS']['Republic Fleet Mission']='GLS1-top'
dict_BT_missions['GLS']['Count Dooku\'s Hangar Mission']='GLS1-mid'
dict_BT_missions['GLS']['Rear Flank Mission']='GLS1-bottom'
dict_BT_missions['GLS']['Contested Airspace (Republic) Mission']='GLS2-top'
dict_BT_missions['GLS']['Battleground Mission']='GLS2-mid'
dict_BT_missions['GLS']['Sand Dunes Mission']='GLS2-bottom'
dict_BT_missions['GLS']['Contested Airspace (Separatist) Mission']='GLS3-top'
dict_BT_missions['GLS']['Separatist Command Mission']='GLS3-mid'
dict_BT_missions['GLS']['Petranaki Arena Mission']='GLS3-bottom'
dict_BT_missions['GLS']['Separatist Armada Mission']='GLS4-top'
dict_BT_missions['GLS']['Factory Waste Mission']='GLS4-mid'
dict_BT_missions['GLS']['Canyons Mission']='GLS4-bottom'
dict_BT_missions['GDS']={}
dict_BT_missions['GDS']['Droid Factory Mission']='GDS1-top'
dict_BT_missions['GDS']['Canyons Mission']='GDS1-bottom'
dict_BT_missions['GDS']['Core Ship Yards Mission']='GDS2-top'
dict_BT_missions['GDS']['Separatist Command Mission']='GDS2-mid'
dict_BT_missions['GDS']['Petranaki Arena Mission']='GDS2-bottom'
dict_BT_missions['GDS']['Contested Airspace Mission']='GDS3-top'
dict_BT_missions['GDS']['Battleground Mission']='GDS3-mid'
dict_BT_missions['GDS']['Sand Dunes Mission']='GDS3-bottom'
dict_BT_missions['GDS']['Republic Fleet Mission']='GDS4-top'
dict_BT_missions['GDS']['Count Dooku\'s Hangar Mission']='GDS4-mid'
dict_BT_missions['GDS']['Rear Flank Mission']='GDS4-bottom'

dict_member_lastseen={} #{guild discord name: {player discord id: [discord displayname, date last seen (idle or online)]}

list_tw_opponent_msgIDs = []

dict_platoons_previously_done = {} #Empy set
dict_tb_alerts_previously_done = {}
dict_tw_alerts_previously_done = {}

##############################################################
#                                                            #
#                  FONCTIONS                                 #
#                                                            #
##############################################################

def set_id_lastseen(event_name, guild_name, player_id):
    global dict_member_lastseen

    if guild_name in dict_member_lastseen:
        if player_id in dict_member_lastseen[guild_name]:
            dict_member_lastseen[guild_name][player_id][1]=datetime.datetime.now(guild_timezone)
            alias = dict_member_lastseen[guild_name][player_id][0]
            goutils.log2("DBG", event_name+": guild="+guild_name+" user="+str(player_id)+" ("+alias+")")
        else:
            goutils.log2("WAR", "unknown id "+str(player_id)+" for guild="+guild_name)
    else:
        goutils.log2("WAR", "unknown guild="+guild_name)

##############################################################
# Function: bot_loop_60
# Parameters: none
# Purpose: cette fonction est exécutée toutes les 60 secondes
# Output: none
##############################################################
async def bot_loop_60():
    await bot.wait_until_ready()
    while not bot.is_closed():
        t_start = time.time()

        try:
            #GET ONLINE AND MOBILE STATUS
            for guild in bot.guilds:
                if not guild.name in dict_member_lastseen:
                    dict_member_lastseen[guild.name] = {}

                list_members=[]
                for role in guild.roles:
                    for member in role.members:
                        #Ensure all guild members are in the dict, so that other events
                        #  know which users to update
                        if not member.id in dict_member_lastseen[guild.name]:
                            dict_member_lastseen[guild.name][member.id]= [member.display_name, None]
                            
                        if not(str(member.status) == 'offline' and
                                str(member.mobile_status) == 'offline'):
                            dict_member_lastseen[guild.name][member.id]=[member.display_name, datetime.datetime.now(guild_timezone)]
                                
                        list_members.append([member.display_name,str(member.status),str(member.mobile_status)])
            
                #goutils.log2("DBG", "guildname="+guild.name+", dict_last_seen="+str(dict_member_lastseen[guild.name]))
                connect_gsheets.update_online_dates(guild.name, dict_member_lastseen[guild.name])

        except Exception as e:
            goutils.log("ERR", "bot_loop_60", sys.exc_info()[0])
            goutils.log("ERR", "bot_loop_60", e)
            goutils.log("ERR", "bot_loop_60", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(None, "Exception in bot_loop_60:"+str(sys.exc_info()[0]))
        
        # Wait X seconds before next loop
        t_end = time.time()
        waiting_time = max(0, 60 - (t_end - t_start))
        await asyncio.sleep(waiting_time)

        #Ensure writing in logs
        sys.stdout.flush()

##############################################################
# Function: bot_loop_10minutes
# Parameters: none
# Purpose: cette fonction est exécutée toutes les 600 secondes
# Output: none
##############################################################
async def bot_loop_10minutes():
    await bot.wait_until_ready()
    while not bot.is_closed():
        t_start = time.time()

        try:
            #REFRESH and CLEAN CACHE DATA FROM SWGOH API
            await bot.loop.run_in_executor(None, go.refresh_cache)

        except Exception as e:
            goutils.log("ERR", "guionbot_discord.bot_loop_10minutes", str(sys.exc_info()[0]))
            goutils.log("ERR", "guionbot_discord.bot_loop_10minutes", e)
            goutils.log("ERR", "guionbot_discord.bot_loop_10minutes", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(None, "Exception in bot_loop_10minutes:"+str(sys.exc_info()[0]))

        # Wait X seconds before next loop
        t_end = time.time()
        waiting_time = max(0, 60*10 - (t_end - t_start))
        await asyncio.sleep(waiting_time)

def compute_platoon_progress(platoon_content):
    all_allocations = [item for sublist in platoon_content.values() for item in sublist]
    real_allocations = [x for x in all_allocations if x != '']
    return len(real_allocations) / len(all_allocations)

def compute_territory_progress(dict_platoons, territory):
    count = 0
    for i_platoon in range(1,7):
        platoon = territory + str(i_platoon)
        platoon_progress = compute_platoon_progress(dict_platoons[platoon])
        if platoon_progress == 1:
            count += 1
    return count

##############################################################
# Function: bot_loop_5minutes
# Parameters: none
# Purpose: executed every 15 minutes, typicaly for warstats sync
# Output: none
##############################################################
async def bot_loop_5minutes():
    global dict_platoons_previously_done
    global dict_tb_alerts_previously_done
    global dict_tw_alerts_previously_done
    global first_bot_loop_5minutes

    await bot.wait_until_ready()
    while not bot.is_closed():
        t_start = time.time()

        dict_tw_alerts = {}
        for guild in bot.guilds:
            try:
                if not guild.name in dict_tw_alerts_previously_done:
                    dict_tw_alerts_previously_done[guild.name] = [0, {}]

                #CHECK ALERTS FOR TERRITORY WAR
                list_tw_alerts = go.get_tw_alerts(guild.name)
                if len(list_tw_alerts) > 0:
                    [channel_id, dict_messages] = list_tw_alerts
                    tw_bot_channel = bot.get_channel(channel_id)

                    if len(dict_messages) == 0:
                        #No TW started, reset prev_alerts per territory
                        dict_tw_alerts_previously_done[guild.name][1] = {}

                    for territory in dict_messages:
                        msg_txt = dict_messages[territory]
                        goutils.log2("DBG", "["+guild.name+"] TW alert: "+msg_txt)

                        if not territory in dict_tw_alerts_previously_done[guild.name][1]:
                            if not first_bot_loop_5minutes:
                                #Short message to admins
                                if territory.startswith('Home:'):
                                    await send_alert_to_admins(guild.name, territory+" is lost")
                                elif territory.startswith('Placement:'):
                                    await send_alert_to_admins(guild.name, territory+" is filled")
                                else:
                                    await send_alert_to_admins(guild.name, territory+" is open")

                                if not bot_test_mode:
                                    #Full message to TW guild channel
                                    new_msg = await tw_bot_channel.send(msg_txt)
                                    dict_tw_alerts_previously_done[guild.name][1][territory] = [msg_txt, new_msg.id]

                                goutils.log2("DBG", "["+guild.name+"] New TW alert sent to admins " \
                                            +"and channel "+str(channel_id))
                            else:
                                dict_tw_alerts_previously_done[guild.name][1][territory] = [msg_txt, 0]
                                goutils.log2("DBG", "["+guild.name+"] TW alert not sent during 1st 5minute loop")
                        elif not territory.startswith('Placement:'):
                            #Placement alerts are only sent once, never modified

                            [old_msg_txt, old_msg_id] = dict_tw_alerts_previously_done[guild.name][1][territory]
                            if old_msg_txt != msg_txt:
                                #Short message to admins
                                await send_alert_to_admins(guild.name, territory+" is modified")


                                if not bot_test_mode:
                                    #Full message modified in TW guild channel
                                    if old_msg_id != 0:
                                        old_msg = await tw_bot_channel.fetch_message(old_msg_id)
                                        await old_msg.edit(content=msg_txt)
                                        dict_tw_alerts_previously_done[guild.name][1][territory][0] = msg_txt
                                    else:
                                        #TW alert detected but not sent because during the first bot loop
                                        # because it is modified, it is now sent
                                        new_msg = await tw_bot_channel.send(msg_txt)
                                        dict_tw_alerts_previously_done[guild.name][1][territory] = [msg_txt, new_msg.id]

                                goutils.log2("DBG", "["+guild.name+"] Modified TW alert sent to admins " \
                                            +"and channel "+str(channel_id))
                else:
                    goutils.log2("WAR", "["+guild.name+"] TW alerts could not be detected")

            except Exception as e:
                goutils.log2("ERR", "["+guild.name+"]"+str(sys.exc_info()[0]))
                goutils.log2("ERR", "["+guild.name+"]"+str(e))
                goutils.log2("ERR", "["+guild.name+"]"+traceback.format_exc())
                if not bot_test_mode:
                    await send_alert_to_admins(guild.name, "Exception in bot_loop_5minutes:"+str(sys.exc_info()[0]))

            try:
                if not guild.name in dict_tb_alerts_previously_done:
                    dict_tb_alerts_previously_done[guild.name] = []

                #CHECK ALERTS FOR BT
                list_tb_alerts = go.get_tb_alerts(guild.name, False)
                for tb_alert in list_tb_alerts:
                    if not tb_alert in dict_tb_alerts_previously_done[guild.name]:
                        if not first_bot_loop_5minutes:
                            await send_alert_to_echocommanders(guild.name, tb_alert)
                            goutils.log2("INFO", "["+guild.name+"] New TB alert: "+tb_alert)
                        else:
                            goutils.log2("DBG", "["+guild.name+"] New TB alert within the first 5 minutes: "+tb_alert)
                    else:
                        goutils.log2("DBG", "["+guild.name+"] Already known TB alert: "+tb_alert)

                dict_tb_alerts_previously_done[guild.name] = list_tb_alerts

            except Exception as e:
                goutils.log2("ERR", "["+guild.name+"]"+str(sys.exc_info()[0]))
                goutils.log2("ERR", "["+guild.name+"]"+str(e))
                goutils.log2("ERR", "["+guild.name+"]"+traceback.format_exc())
                if not bot_test_mode:
                    await send_alert_to_admins(guild.name, "Exception in bot_loop_5minutes:"+str(sys.exc_info()[0]))

            try:
                #get guild_id from DB
                query = "SELECT warstats_id FROM guilds WHERE name='"+guild.name.replace("'", "''")+"'"
                goutils.log2("DBG", query)
                guild_id = connect_mysql.get_value(query)

                if guild_id == 0:
                    goutils.log2("ERR", "warstats_id=0 for guild "+guild.name)
                    raise Exception("unknown guild id")

                if not guild.name in dict_platoons_previously_done:
                    dict_platoons_previously_done[guild.name] = {}

                #Lecture du statut des pelotons sur warstats
                tbs_round, dict_platoons_done, list_open_territories, \
                    sec_last_track = connect_warstats.parse_tb_platoons(guild_id, False)
                if tbs_round == '':
                    goutils.log2("DBG", "["+guild.name+"] No TB in progress")
                    dict_platoons_previously_done[guild.name] = {}
                else:
                    goutils.log2("DBG", "["+guild.name+"] Current state of platoon filling: "+str(dict_platoons_done))
                    goutils.log2("INFO", "["+guild.name+"] End of warstats parsing for TB: round " + tbs_round)
                    new_allocation_detected = False
                    dict_msg_platoons = {}
                    for territory_platoon in dict_platoons_done:
                        current_progress = compute_platoon_progress(dict_platoons_done[territory_platoon])
                        goutils.log("DBG", "guionbot_discord.bot_loop_5minutes", "["+guild.name+"] Progress of platoon "+territory_platoon+": "+str(current_progress))
                        if not territory_platoon in dict_platoons_previously_done[guild.name]:
                            #If the territory was not already detected, then all allocation within that territory are new
                            for character in dict_platoons_done[territory_platoon]:
                                for player in dict_platoons_done[territory_platoon][character]:
                                    if player != '':
                                        goutils.log("INFO", "guionbot_discord.bot_loop_5minutes", "["+guild.name+"] New platoon allocation: " + territory_platoon + ":" + character + " by " + player)
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
                                if not character in dict_platoons_previously_done[guild.name][territory_platoon]:
                                    for player in dict_platoons_done[territory_platoon][character]:
                                        if player != '':
                                            goutils.log("INFO", "guionbot_discord.bot_loop_5minutes", "["+guild.name+"] New platoon allocation: " + territory_platoon + ":" + character + " by " + player)
                                            new_allocation_detected = True
                                else:
                                    for player in dict_platoons_done[territory_platoon][character]:
                                        if not player in dict_platoons_previously_done[guild.name][territory_platoon][character]:
                                            if player != '':
                                                goutils.log("INFO", "guionbot_discord.bot_loop_5minutes", "["+guild.name+"] New platoon allocation: " + territory_platoon + ":" + character + " by " + player)
                                                new_allocation_detected = True

                            previous_progress = compute_platoon_progress(dict_platoons_previously_done[guild.name][territory_platoon])
                            if current_progress == 1 and previous_progress < 1:
                                territory = territory_platoon[:-1]
                                territory_full_count = compute_territory_progress(dict_platoons_done, territory)
                                territory_display = territory.split("-")[1]
                                if not territory_display in dict_msg_platoons:
                                    dict_msg_platoons[territory_display] = [0, []]
                                dict_msg_platoons[territory_display][0] = territory_full_count
                                dict_msg_platoons[territory_display][1].append(territory_platoon)

                    if not new_allocation_detected:
                        goutils.log("INFO", "guionbot_discord.bot_loop_5minutes", "["+guild.name+"] No new platoon allocation")
                
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
                        goutils.log("INFO", "guionbot_discord.bot_loop_5minutes", "["+guild.name+"]"+msg)
                        if not first_bot_loop_5minutes:
                            await send_alert_to_echocommanders(guild.name, msg)

                    dict_platoons_previously_done[guild.name] = dict_platoons_done.copy()

            except Exception as e:
                goutils.log2("ERR", "["+guild.name+"]"+str(sys.exc_info()[0]))
                goutils.log2("ERR", "["+guild.name+"]"+str(e))
                goutils.log2("ERR", "["+guild.name+"]"+traceback.format_exc())
                if not bot_test_mode:
                    await send_alert_to_admins(guild.name, "Exception in bot_loop_5minutes:"+str(sys.exc_info()[0]))

        first_bot_loop_5minutes = False

        # Wait X seconds before next loop
        t_end = time.time()
        waiting_time = max(0, 60*5 - (t_end - t_start))
        await asyncio.sleep(waiting_time)

        #Ensure writing in logs
        sys.stdout.flush()

##############################################################
# Function: bot_loop_6hours
# Parameters: none
# Purpose: high level monitoring, every 6 hours
# Output: none
##############################################################
async def bot_loop_6hours():
    await bot.wait_until_ready()
    while not bot.is_closed():
        t_start = time.time()

        try:
            #REFRESH and CLEAN CACHE DATA FROM SWGOH API
            err_code, err_txt = await bot.loop.run_in_executor(None, go.manage_disk_usage)

            if err_code > 0:
                await send_alert_to_admins(None, err_txt)

        except Exception as e:
            goutils.log("ERR", "guionbot_discord.bot_loop_6hours", str(sys.exc_info()[0]))
            goutils.log("ERR", "guionbot_discord.bot_loop_6hours", e)
            goutils.log("ERR", "guionbot_discord.bot_loop_6hours", traceback.format_exc())
            if not bot_test_mode:
                await send_alert_to_admins(None, "Exception in bot_loop_6hours:"+str(sys.exc_info()[0]))

        # Wait X seconds before next loop
        t_end = time.time()
        waiting_time = max(0, 3600*6 - (t_end - t_start))
        await asyncio.sleep(waiting_time)

        #Ensure writing in logs
        sys.stdout.flush()

##############################################################
# Function: send_alert_to_admins
# Parameters: message (string), message to be sent
# Purpose: send a message to bot admins. Only once, then the admin has to
#          stop/start the bot for a new message to be allowed
# Output: None
##############################################################
async def send_alert_to_admins(server_name, message):
    global list_alerts_sent_to_admin

    if server_name != None:
        message = "["+server_name+"] "+message

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
async def send_alert_to_echocommanders(server_name, message):
    goutils.log2("DBG", "server_name="+server_name+", message="+message)
    if bot_test_mode:
        await send_alert_to_admins(server_name, message)
    else:
        query = "SELECT tbChanOut_id, tbRoleOut FROM guilds WHERE name='"+server_name.replace("'", "''")+"'"
        goutils.log2("DBG", query)
        result = connect_mysql.get_line(query)
        if result == None:
            await ctx.send('ERR: commande non utilisable sur ce serveur')
            return

        [tbChanOut_id, tbRoleOut] = result

        if tbChanOut_id != 0:
            tb_channel = bot.get_channel(tbChanOut_id)
            try:
                await tb_channel.send("["+server_name+"]"+ message)
            except discorderrors.Forbidden as e:
                goutils.log2("WAR", "["+server_name+"] Cannot send message to "+str(tbChanOut_id))

        if tbRoleOut != "":
            for guild in bot.guilds:
                if guild.name == server_name:
                    for role in guild.roles:
                        if role.name == tbRoleOut:
                            for member in role.members:
                                channel = await member.create_dm()
                                try:
                                    await channel.send("["+server_name+"]"+ message)
                                except discorderrors.Forbidden as e:
                                    goutils.log2("WAR", "["+server_name+"] Cannot send DM to "+member.name)

##############################################################
# Function: get_eb_allocation
# Parameters: tbs_round (string) > nom de phase en TB, sous la forme "GDS2"
# Purpose: lit le channel #bateilles de territoire pour retouver
#          l'affectation des pelotons par Echobot
# Output: dict_platoons_allocation={} #key=platoon_name, value={key=perso, value=[player...]}
##############################################################
async def get_eb_allocation(tbChannel_id, tbs_round):
    # Lecture des affectation ECHOBOT
    tb_channel = bot.get_channel(tbChannel_id)
    dict_platoons_allocation = {}  #key=platton_name, value={key=perso, value=[player...]}
    eb_phases = []
    eb_missions_full = []
    eb_missions_tmp = []
    
    tbs_name = tbs_round[0:3]
    
    async for message in tb_channel.history(limit=500):
        if str(message.author).startswith("EchoStation#") \
        or str(message.author).startswith("Echobase#"):
            if (datetime.datetime.now(guild_timezone) - message.created_at.astimezone(guild_timezone)).days > 7:
                #On considère que si un message echobot a plus de 7 jours c'est une ancienne BT
                break

            if message.content.startswith('```prolog'):
                #EB message by territory
                ret_re = re.search('```prolog\n.* \((.*)\):.*', message.content)
                territory_position = ret_re.group(1)
                  
                for embed in message.embeds:
                    dict_embed = embed.to_dict()
                    if 'fields' in dict_embed:
                        #on garde le nom de la BT mais on met X comme numéro de phase
                        #le numéro de phase sera affecté plus tard
                        platoon_num = dict_embed["description"].split(" ")[2][0]

                        platoon_name = tbs_name + "X-" + territory_position + "-" + platoon_num
                        for dict_player in dict_embed['fields']:
                            player_name = dict_player['name']
                            for character in dict_player['value'].split('\n'):
                                char_name = character[1:-1]
                                if char_name != 'Filled in another phase':
                                    if char_name[0:4]=='*` *':
                                        char_name=char_name[4:]
                                    if not platoon_name in dict_platoons_allocation:
                                        dict_platoons_allocation[
                                            platoon_name] = {}
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
                                    platoon_pos = line.split(" ")[0][2:]
                                    platoon_num = line.split(" ")[2][1]
                                    platoon_name = tbs_name + "X-" + platoon_pos + "-" + platoon_num
                                else:
                                    ret_re = re.search("^(:.*: )?(`\*` )?([^:\[]*)( (:crown:|:cop:)?( `\[G[0-9]*\]`)?)?$",
                                                        line)
                                    player_name = ret_re.group(3).strip()
                                    
                                    if player_name != 'Filled in another phase':
                                        if not platoon_name in dict_platoons_allocation:
                                            dict_platoons_allocation[platoon_name] = {}
                                        if not char_name in dict_platoons_allocation[
                                                platoon_name]:
                                            dict_platoons_allocation[platoon_name][
                                                char_name] = []
                                        dict_platoons_allocation[platoon_name][
                                            char_name].append(player_name)

            elif message.content.startswith('Rare Units:'):
                #EB message by unit / Rare unis
                for embed in message.embeds:
                    dict_embed = embed.to_dict()
                    if 'fields' in dict_embed:
                        # on garde le nom de la BT mais on met X comme numéro de phase
                        # le numéro de phase sera affecté plus tard
                        char_name = dict_embed['author']['name']
                        
                        for dict_platoon in dict_embed['fields']:
                            ret_re = re.search('(.*) - .*', dict_platoon['name'])
                            if ret_re != None:
                                territory_position = ret_re.group(1)
                                platoon_name = tbs_name + "X-" + territory_position + \
                                                "-" + dict_platoon['name'][-1]
                                    
                                for line in dict_platoon['value'].split('\n'):
                                    ret_re = re.search("^(:.*: )?(`\*` )?([^:\[]*)( (:crown:|:cop:)?( `\[G[0-9]*\]`)?)?$",
                                                    line)
                                    player_name = ret_re.group(3).strip()
                                        
                                    if char_name != 'Filled in another phase':
                                        if char_name[0:4]=='*` *':
                                            char_name=char_name[4:]
                                        if not platoon_name in dict_platoons_allocation:
                                            dict_platoons_allocation[
                                                platoon_name] = {}
                                        if not char_name in dict_platoons_allocation[
                                                platoon_name]:
                                            dict_platoons_allocation[platoon_name][
                                                char_name] = []
                                        dict_platoons_allocation[platoon_name][
                                            char_name].append(player_name)

            elif message.content.startswith("<@"):
                #EB message by player
                for embed in message.embeds:
                    dict_embed = embed.to_dict()
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
                                char_name = character[1:-1]
                                if char_name != 'Filled in another phase':
                                    if char_name[0:4]=='*` *':
                                        char_name=char_name[4:]
                                    if not platoon_name in dict_platoons_allocation:
                                        dict_platoons_allocation[
                                            platoon_name] = {}
                                    if not char_name in dict_platoons_allocation[
                                            platoon_name]:
                                        dict_platoons_allocation[platoon_name][
                                            char_name] = []
                                    dict_platoons_allocation[platoon_name][
                                        char_name].append(player_name)

            elif message.content.startswith(":information_source: **Overview**"):
                #Overview of the EB posts. Gives the territory names
                # this name helps allocatting the phase
                # In case of single-territory, helps recovering its position
                for line in message.content.split("\n"):
                    if line.startswith(":"):
                        ret_re = re.search(":.*: \*\*(.*) \((.*)\)\*\*", line)
                        if ret_re != None:
                            territory_name = ret_re.group(1)
                            territory_position = ret_re.group(2) #top, bottom, mid
                            
                            if territory_name in dict_BT_missions[tbs_name]:
                                territory_name_position = dict_BT_missions[
                                                        tbs_name][territory_name]
                            
                                #Check if this mission/territory has been allocated in previous message
                                existing_platoons = [i for i in dict_platoons_allocation.keys()
                                                if i.startswith(territory_name_position)]
                                                
                                if len(existing_platoons) == 0:                    
                                    # with the right name for the territory, modify dictionary
                                    keys_to_rename=[]                         
                                    for platoon_name in dict_platoons_allocation:
                                        if platoon_name.startswith(tbs_name + "X-"+territory_position):
                                            keys_to_rename.append(platoon_name)
                                        if platoon_name.startswith(tbs_name + "X-PLATOON"):
                                            keys_to_rename.append(platoon_name)
                                    for key in keys_to_rename:
                                        new_key = territory_name_position+key[-2:]
                                        dict_platoons_allocation[new_key] = \
                                                dict_platoons_allocation[key]
                                        del dict_platoons_allocation[key]
                                        
                            else:
                                goutils.log("WAR", "get_eb_allocation", 'Mission \"'+territory_name+'\" inconnue')

    return dict_platoons_allocation


##############################################################
# Function: get_channel_from_channelname
# Parameters: channel_name (string) > nom de channel sous la forme <#1234567890>
# Purpose: récupère un objet channel pour écrire dans le channel spécifié
# Output: nominal > output_channel (objet channel), ""
#         si erreur > None, "message d'erreur" (string)
##############################################################
async def get_channel_from_channelname(ctx, channel_name):
    try:
        id_output_channel = int(channel_name[2:-1])
    except Exception as e:
        goutils.log("ERR", "guionbot_discord.get_channel_from_channelname", e)
        return None, channel_name + ' n\'est pas un channel valide'

    output_channel = bot.get_channel(id_output_channel)
    if output_channel == None:
        return None, 'Channel ' + channel_name + '(id=' \
                    + str(id_output_channel) + ') introuvable'

    if not output_channel.permissions_for(ctx.guild.me).send_messages:
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
def manage_me(ctx, alias):
    #Special case of 'me' as allyCode
    if alias == 'me':
        dict_players_by_ID = connect_gsheets.load_config_players(ctx.guild.name, False)[1]
        if str(ctx.author.id) in dict_players_by_ID:
            ret_allyCode_txt = str(dict_players_by_ID[str(ctx.author.id)][0])
        else:
            ret_allyCode_txt = "ERR: \"me\" (<@"+str(ctx.author.id)+">) n'est pas enregistré dans le bot"
    elif alias.startswith('<@'):
        # discord @mention
        if alias.startswith('<@!'):
            discord_id_txt = alias[3:-1]
        else: # '<@ without the !
            discord_id_txt = alias[2:-1]
        goutils.log("INFO", "guionbot_discord.manage_me", "command launched with discord @mention "+alias)
        dict_players_by_ID = connect_gsheets.load_config_players(ctx.guild.name, False)[1]
        if discord_id_txt.isnumeric() and discord_id_txt in dict_players_by_ID:
            ret_allyCode_txt = str(dict_players_by_ID[discord_id_txt][0])
        else:
            ret_allyCode_txt = 'ERR: '+alias+' ne fait pas partie des joueurs enregistrés'

    elif re.match("[0-9]{3}-[0-9]{3}-[0-9]{3}", alias) != None:
        # 123-456-789 >> allyCode
        ret_allyCode_txt = alias.replace("-", "")

    elif alias.isnumeric():
        # number >> allyCode
        ret_allyCode_txt = alias

    else:
        # Look for the name among known player names
        results = connect_mysql.get_table("SELECT name, allyCode FROM players")
        list_names = [x[0] for x in results]
        closest_names_db=difflib.get_close_matches(alias, list_names, 1)
        if len(closest_names_db) == 0:
            closest_name_db = ""
            closest_name_db_score = 0
        else:
            closest_name_db = closest_names_db[0]
            closest_name_db_score = difflib.SequenceMatcher(None, alias, closest_name_db).ratio()

        #check among discord names
        if ctx != None and (closest_name_db != alias):
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

            if closest_name_db_score >= closest_name_discord_score:
                select_db_name = True
            else:
                select_db_name = False
        else:
            select_db_name = True

        if select_db_name:
            if closest_name_db_score == 0:
                goutils.log2("WAR", alias +" not found in DB and in discord")
                ret_allyCode_txt = "ERR: "+alias+" n'a pas été trouvé"
            else:
                goutils.log2("INFO", alias +" looks like the DB name "+closest_name_db)
                for r in results:
                    if r[0] == closest_name_db:
                        ret_allyCode_txt = str(r[1])

        else:
            goutils.log2("INFO", alias + " looks like the discord name "+closest_name_discord)

            discord_id = [str(x[0]) for x in guild_members_clean \
                            if x[1] == closest_name_discord][0]
            dict_players_by_ID = connect_gsheets.load_config_players(ctx.guild.name, False)[1]
            if discord_id in dict_players_by_ID:
                ret_allyCode_txt = str(dict_players_by_ID[discord_id][0])
            else:
                goutils.log2("ERR", alias + " ne fait pas partie des joueurs enregistrés")
                ret_allyCode_txt = 'ERR: '+alias+' ne fait pas partie des joueurs enregistrés'

    
    return ret_allyCode_txt

##############################################################
# Function: read_gsheets
# IN: guild_name (= discord server name)
# Purpose: affecte le code allié de l'auteur si "me"
# OUT: err_code (0 = OK), err_txt
##############################################################
def read_gsheets(guild_name):
    err_code = 0
    err_txt = ""

    d = connect_gsheets.load_config_units(True)
    if d == None:
        err_txt += "ERR: erreur en mettant à jour les UNITS\n"
        err_code = 1

    l, d = connect_gsheets.load_config_teams("GuiOnBot config", True)
    if d == None:
        err_txt += "ERR: erreur en mettant à jour les TEAMS GV\n"
        err_code = 1

    l, d = connect_gsheets.load_config_teams(guild_name, True)
    if d == None:
        err_txt += "ERR: erreur en mettant à jour les TEAMS\n"
        err_code = 1

    d = connect_gsheets.load_config_raids(guild_name, True)
    if d == None:
        err_txt += "ERR: erreur en mettant à jour les RAIDS\n"
        err_code = 1

    [ts, dt, m] = connect_gsheets.get_tb_triggers(guild_name, True)
    if ts == None:
        err_txt += "ERR: erreur en mettant à jour la BT\n"
        err_code = 1

    l = connect_gsheets.load_tb_teams(guild_name, True)
    if l == None:
        err_txt += "ERR: erreur en mettant à jour les BT teams\n"
        err_code = 1

    [d1, d2] = connect_gsheets.load_config_players(guild_name, True)
    if d1 == None:
        err_txt += "ERR: erreur en mettant à jour les PLAYERS\n"
        err_code = 1

    return err_code, err_txt

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
    ip = get('https://api.ipify.org').text
    
    msg = bot.user.name+" has connected to Discord from ip "+ip
    goutils.log("INFO", "guionbot_discord.on_ready", msg)
    if not bot_test_mode:
        await send_alert_to_admins(None, msg)


##############################################################
# Event: on_reaction_add
# Parameters: reaction (object containing different other ones)
#             user (user taging with the emoji)
# Purpose: se lance quand une réaction est ajoutée à un message
# Output: none
##############################################################
@bot.event
async def on_reaction_add(reaction, user):
    global list_alerts_sent_to_admin

    #prevent reacting to bot's reactions
    if user == bot.user:
        return

    message = reaction.message
    if isinstance(message.channel, GroupChannel):
        guild_name = message.channel.guild.name
        set_id_lastseen("on_reaction_add", reaction.message.channel.guild.name, user.id)
    else:
        guild_name = "DM"
    author = message.author
    emoji = reaction.emoji
    goutils.log2("DBG", "guild_name: "+guild_name)
    goutils.log2("DBG", "message: "+str(message))
    goutils.log2("DBG", "author of the message: "+str(author))
    goutils.log2("DBG", "emoji: "+str(emoji))
    goutils.log2("DBG", "user of the reaction: "+str(user))

    
    # Manage the thumb up to messages sent to admins
    if message.content in list_alerts_sent_to_admin \
        and emoji == '\N{THUMBS UP SIGN}' \
        and author == bot.user:
        list_alerts_sent_to_admin.remove(message.content)
        await message.add_reaction('\N{WHITE HEAVY CHECK MARK}')

    #Manage reactions to PGS messages
    for [rgt_user, list_msg_sizes] in list_tw_opponent_msgIDs:
        list_msg = [x[0] for x in list_msg_sizes]
        if message in list_msg:
            if emoji in emoji_letters and rgt_user == user:
                img1_url = list_msg[0].attachments[0].url
                img1_size = list_msg_sizes[0][1][0]

                img2_position = list_msg.index(message)
                img2_url = message.attachments[0].url
                img2_sizes = list_msg_sizes[img2_position][1]

                letter_position = emoji_letters.index(emoji)
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

##############################################################
# Event: on_message
# Parameters: message (discord object)
# Purpose: basic checks before running command
# Output: none
##############################################################
@bot.event
async def on_message(message):
    if isinstance(message.channel, GroupChannel):
        set_id_lastseen("on_message", message.channel.guild.name, message.author.id)

    lower_msg = message.content.lower().strip()
    if lower_msg.startswith("go."):
        command_name = lower_msg.split(" ")[0].split(".")[1]
        goutils.log2("INFO", "Command "+message.content+" launched by "+message.author.display_name)

    try:
        await bot.process_commands(message)
    except Exception as e:
        goutils.log2("ERR", sys.exc_info()[0])
        goutils.log2("ERR", e)
        goutils.log2("ERR", traceback.format_exc())
        if not bot_test_mode:
            await send_alert_to_admins(guild_name, "Exception in guionbot_discord.on_message:"+str(sys.exc_info()[0]))

    #Read messages from Juke's bot
    if message.author.id == config.JBOT_DISCORD_ID:
        for embed in message.embeds:
            dict_embed = embed.to_dict()

            if 'title' in dict_embed:
                embed = dict_embed['title']
                if embed.endswith("'s unit status"):
                    pos_name = embed.index("'s unit status")
                    player_name = embed[:pos_name]

            if 'description' in dict_embed:
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

##############################################################
# Event: on_error_command
# Parameters: error (error raised by the command)
#             ctx (context of the command)
# Purpose: inform that a command is unknown
# Output: error message to the user
##############################################################
@bot.event
async def on_command_error(ctx, error):
    await ctx.message.add_reaction(emoji_thumb)
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("ERR: commande inconnue")
        await ctx.message.add_reaction(emoji_error)
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        cmd_name = ctx.command.name
        await ctx.send("ERR: argument manquant. Consultez l'aide avec go.help "+cmd_name)
        await ctx.message.add_reaction(emoji_error)
    elif isinstance(error, commands.CheckFailure):
        if not bot_test_mode:
            await ctx.send("ERR: commande interdite")
            await ctx.message.add_reaction(emoji_error)
    else:
        await ctx.send("ERR: erreur inconnue")
        await ctx.message.add_reaction(emoji_error)
        goutils.log2("ERR", error)
        await send_alert_to_admins(ctx.guild.name, "ERR: erreur inconnue "+str(error))
        raise error

##############################################################
# Other events used only to monitor the activity of guild members
##############################################################
@bot.event
async def on_typing(channel, user, when):
    guild_name = channel.guild.name
    set_id_lastseen("on_typing", guild_name, user.id)

@bot.event
async def on_message_delete(message):
    #Unable to detect who is deleting a message
    pass

@bot.event
async def on_message_edit(before, after):
    if isinstance(before.channel, GroupChannel):
        channel_name = before.channel.name
    else:
        channel_name = "DM"

    goutils.log2("INFO", "Message edited by "+before.author.display_name + " in "+channel_name+"\n" +\
                         "BEFORE:\n" + before.content + "\n" +\
                         "AFTER:\n" + after.content)
    guild_name = before.channel.guild.name
    set_id_lastseen("on_message_edit", guild_name, before.author.id)

@bot.event
async def on_reaction_remove(reaction, user):
    guild_name = reaction.message.channel.guild.name
    set_id_lastseen("on_reaction_remove", guild_name, user.id)

@bot.event
async def on_member_join(member):
    guild_name = member.guild.name
    set_id_lastseen("on_member_join", guild_name, member.id)

@bot.event
async def on_member_update(before, after):
    guild_name = before.guild.name
    set_id_lastseen("on_member_update", guild_name, before.id)
    if before.display_name != after.display_name:
        goutils.log2("INFO", "Nickname change \""+before.display_name + "\" to \""+after.display_name+"\"")

@bot.event
async def on_user_update(before, after):
    if isinstance(before.channel, GroupChannel):
        guild_name = before.channel.guild.name
    else:
        guild_name = "DM"

    set_id_lastseen("on_user_update", guild_name, before.id)

@bot.event
async def on_voice_state_update(member, before, after):
    guild_name = member.guild.name
    set_id_lastseen("on_voice_state_update", guild_name, member.id)

##############################################################
#                                                            #
#       COMMANDES REGOUPEES PAR CATEGORIE (COG)              #
#                                                            #
##############################################################

##############################################################
# Class: AdminCog
# Description: contains all admin commands
##############################################################
class AdminCog(commands.Cog, name="Commandes pour les admins"):
    def __init__(self, bot):
        self.bot = bot

    ##############################################################
    # Function: is_owner
    # Parameters: ctx (objet Contexte)
    # Purpose: vérifie si le contexte appartient à un admin du bot
    #          Le but est de limiter certains commandes aux développeurs
    # Output: True/False
    ##############################################################
    async def is_owner(ctx):
        return str(ctx.author.id) in config.GO_ADMIN_IDS.split(' ')

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
    @commands.command(name='cmd', help='Lance une ligne de commande sur le serveur')
    @commands.check(is_owner)
    async def cmd(self, ctx, *args):
        await ctx.message.add_reaction(emoji_thumb)

        arg = " ".join(args)
        stream = os.popen(arg)
        output = stream.read()
        goutils.log("INFO", "go.cmd", 'CMD: ' + arg)
        goutils.log("INFO", "go.cmd", 'output: ' + output)
        for txt in goutils.split_txt(output, MAX_MSG_SIZE):
            await ctx.send('`' + txt + '`')
        await ctx.message.add_reaction(emoji_check)
        
    ##############################################################
    # Command: info
    # Parameters: ctx (objet Contexte)
    # Purpose: affiche un statut si le bot est ON, avec taille du CACHE
    # Display: statut si le bot est ON, avec taille du CACHE
    ##############################################################
    @commands.command(name='info', help='Statut du bot')
    @commands.check(is_owner)
    async def info(self, ctx):
        await ctx.message.add_reaction(emoji_thumb)

        # get the DB information
        output_txt=''
        output_size = connect_mysql.text_query("CALL get_db_size()")
        for row in output_size:
            output_txt+=str(row)+'\n'

        output_players = connect_mysql.text_query("SELECT guilds.name AS Guilde, \
                                                    count(*) as Joueurs, \
                                                    guilds.lastUpdated as MàJ \
                                                    FROM guilds \
                                                    JOIN players ON players.guildName = guilds.name \
                                                    GROUP BY guilds.name \
                                                    ORDER BY guilds.lastUpdated DESC")
        output_txt += "\n"
        for row in output_players:
            output_txt+=str(row)+'\n'


        await ctx.send('**GuiOn bot is UP** since '+str(bot_uptime)+' (GMT)')
        for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
            await ctx.send('``` '+txt[1:]+'```')

        await ctx.message.add_reaction(emoji_check)

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
    @commands.command(name='sql', help='Lance une requête SQL dans la database')
    @commands.check(is_owner)
    async def sql(self, ctx, *args):
        await ctx.message.add_reaction(emoji_thumb)

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
        
        await ctx.message.add_reaction(emoji_check)
        
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
                      "Exemple: go.fsj me clearcache")
    @commands.check(is_owner)
    async def fsj(self, ctx, allyCode, *options):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            clear_cache = (len(options)>0)
            query = "SELECT CURRENT_TIMESTAMP"
            goutils.log2("DBG", query)
            timestamp_before = connect_mysql.get_value(query)
            e, t, player_before = await bot.loop.run_in_executor(
                                            None, go.load_player,
                                            allyCode, -1, True)
            if e!=0:
                await ctx.send(t)
                await ctx.message.add_reaction(emoji_error)
                return

            if clear_cache:
                json_file = "PLAYERS/"+allyCode+".json"
                if os.path.isfile(json_file):
                    os.remove(json_file)

            e, t, player_now = await bot.loop.run_in_executor(
                                            None, go.load_player,
                                            allyCode, 1, False)
            if e!=0:
                await ctx.send(t)
                await ctx.message.add_reaction(emoji_error)
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
                await ctx.send('*Aucune mise à jour*')
        
            await ctx.message.add_reaction(emoji_check)


    ##############################################################
    # Command: test
    # Parameters: ça dépend...
    # Purpose: commande de test lors du dev. Doit être mise en commentaires
    #          avant déploiement en service
    # Display: ça dépend
    #############################################################
    #@commands.command(name='test', help='Réservé aux admins')
    #@commands.check(is_owner)
    #async def test(self, ctx, *args):
    #    pass

##############################################################
# Class: OfficerCog
# Description: contains all officer commands
##############################################################
class OfficerCog(commands.Cog, name="Commandes pour les officiers"):
    def __init__(self, bot):
        self.bot = bot

    ##############################################################
    # Function: is_officer
    # Parameters: ctx (objet Contexte)
    # Purpose: vérifie si le contexte appartient à un officier
    #          Le but est de limiter certains commandes aux officiers
    # Output: True/False
    ##############################################################
    async def is_officer(ctx):
        ret_is_officer = False
        dict_players_by_ID = connect_gsheets.load_config_players(ctx.guild.name, False)[1]
        if str(ctx.author.id) in dict_players_by_ID:
            if dict_players_by_ID[str(ctx.author.id)][1]:
                ret_is_officer = True

        is_owner = (str(ctx.author.id) in config.GO_ADMIN_IDS.split(' '))

        return (ret_is_officer and (not bot_test_mode)) or is_owner

    ##############################################################
    # Command: lgs
    # Parameters: None
    # Purpose: Update cache files from google sheet, and JSON files from API
    # Display: None
    ##############################################################
    @commands.check(is_officer)
    @commands.command(name='lgs', brief="Lit les dernières infos du google sheet",
                             help="Lit les dernières infos du google sheet")
    async def lgs(self, ctx):
        await ctx.message.add_reaction(emoji_thumb)
        data.reset_data()
        err_code, err_txt = read_gsheets(ctx.guild.name)

        if err_code == 1:
            await ctx.send(err_txt)
            await ctx.message.add_reaction(emoji_error)
        else:
            await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: rrg
    # Parameters: nom du raid, tel que défini dans le fichier gsheets
    # Purpose: Affichage des scores en fonction des teams du joueur
    # Display: Une ligne par joueur, avec ses teams et son score
    ##############################################################
    @commands.check(is_officer)
    @commands.command(name='rrg',
                 brief="Résultats de raid de Guilde",
                 help="Résultats de raid de Guilde\n\n"
                      "Exemple : go.rrg me crancor")
    async def rrg(self, ctx, *args):
        await ctx.message.add_reaction(emoji_thumb)

        display_mentions=True
        #Sortie sur un autre channel si donné en paramètre
        if len(args) == 3:
            if args[2].startswith('no'):
                display_mentions=False
                output_channel = ctx.message.channel
            else:
                output_channel, err_msg = await get_channel_from_channelname(ctx, args[2])
                if output_channel == None:
                    await ctx.send('**ERR**: '+err_msg)
                    output_channel = ctx.message.channel
        elif len(args) == 2:
            display_mentions=False
            output_channel = ctx.message.channel
        else:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help rrg")
            await ctx.message.add_reaction(emoji_error)
            return

        allyCode = args[0]
        raid_name = args[1]

        allyCode = manage_me(ctx, allyCode)
                
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            err, errtxt, ret_cmd = go.print_raid_progress(allyCode, ctx.guild.name, raid_name, display_mentions)
            if err != 0:
                await ctx.send(errtxt)
                await ctx.message.add_reaction(emoji_error)
            else:
                output_part = 0
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    if txt.startswith("__Rappels"):
                        output_part = 1
                    if "*phase en cours*" in txt:
                        output_part = 2

                    if output_part == 0:
                        await ctx.send("```"+txt+"```")
                    else: # 1 or 2
                        await ctx.send(txt)
                        if (output_channel != ctx.message.channel) and (output_part == 2):
                            await output_channel.send(txt)

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: rbg
    # Parameters: name of the TB (GDS, HLS...)
    # Purpose: Display results by player depending on whcih teams they have
    # Display: One line per player, with emojis
    ##############################################################
    @commands.check(is_officer)
    @commands.command(name='trg',
                 brief="Teams de Raid de Guilde",
                 help="Teams de Raid de Guilde\n\n"
                      "Exemple : go.trg me crancor")
    async def trg(self, ctx, *args):
        await ctx.message.add_reaction(emoji_thumb)

        if len(args) != 2:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help trg")
            await ctx.message.add_reaction(emoji_error)
            return

        allyCode = args[0]
        raid_name = args[1]

        allyCode = manage_me(ctx, allyCode)
                
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            err, txt, dict_best_teams = await bot.loop.run_in_executor(None,
                                                    go.find_best_teams_for_raid,
                                                    allyCode, ctx.guild.name, raid_name, True)
            if err !=0:
                await ctx.send(txt)
                await ctx.message.add_reaction(emoji_error)
            else:
                output_txt = ""
                for pname in dict_best_teams:
                    lbts = dict_best_teams[pname]
                    output_txt += "**" + pname + "**: " + str(lbts[0]) + "\n"

                for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                    await ctx.send(txt)

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: rbg
    # Parameters: name of the TB (GDS, HLS...)
    # Purpose: Display results by player depending on whcih teams they have
    # Display: One line per player, with emojis
    ##############################################################
    @commands.check(is_officer)
    @commands.command(name='rbg',
                 brief="Résultats de BT de Guilde",
                 help="Résultats de BT de Guilde\n\n"
                      "Exemple : go.rbg me GLS")
    async def rbg(self, ctx, *args):
        await ctx.message.add_reaction(emoji_thumb)

        display_mentions=True
        #Sortie sur un autre channel si donné en paramètre
        if len(args) == 3:
            if args[2].startswith('no'):
                display_mentions=False
                output_channel = ctx.message.channel
            else:
                output_channel, err_msg = await get_channel_from_channelname(ctx, args[2])
                if output_channel == None:
                    await ctx.send('**ERR**: '+err_msg)
                    output_channel = ctx.message.channel
        elif len(args) == 2:
            display_mentions=False
            output_channel = ctx.message.channel
        else:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help rbg")
            await ctx.message.add_reaction(emoji_error)
            return

        allyCode = args[0]
        tb_name = args[1]

        allyCode = manage_me(ctx, allyCode)
                
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            err, errtxt, ret_cmd = go.print_tb_progress(allyCode, ctx.guild.name, tb_name, display_mentions)
            if err != 0:
                await ctx.send(errtxt)
                await ctx.message.add_reaction(emoji_error)
            else:
                output_part = 0
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    if txt.startswith("__Rappels"):
                        output_part = 1

                    if output_part == 0:
                        await ctx.send("```"+txt+"```")
                    else:
                        await ctx.send(txt)
                        if output_channel != ctx.message.channel:
                            await output_channel.send(txt)

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)


    ##############################################################
    # Command: vdp
    # Parameters: [optionnel] nom du channel où écrire les résultats (sous forme "#nom_du_channel")
    # Purpose: Vérification du déploiements de Pelotons
    # Display: Une ligne par erreur détectée "JoueurX n'a pas déployé persoY en pelotonZ"
    #          avec un groupement par phase puis un tri par joueur
    ##############################################################
    @commands.check(is_officer)
    @commands.command(name='vdp',
                 brief="Vérification de Déploiement des Pelotons en BT",
                 help="Vérification de Déploiement des Pelotons en BT\n\n"\
                      "Exemple : go.vdp #batailles-des-territoires\n"\
                      "Exemple : go.vdp no-mentions")
    async def vdp(self, ctx, *args):
        await ctx.message.add_reaction(emoji_thumb)

        display_mentions=True
        #Sortie sur un autre channel si donné en paramètre
        if len(args) == 1:
            if args[0].startswith('no'):
                display_mentions=False
                output_channel = ctx.message.channel
            else:
                output_channel, err_msg = await get_channel_from_channelname(ctx, args[0])
                if output_channel == None:
                    await ctx.send('**ERR**: '+err_msg)
                    output_channel = ctx.message.channel
        else:
            display_mentions=False
            output_channel = ctx.message.channel

        #get warstats_id from DB
        query = "SELECT warstats_id, tbChanRead_id FROM guilds WHERE server_id = " + str(ctx.guild.id)
        goutils.log2("DBG", query)
        result = connect_mysql.get_line(query)

        if result == None:
            await ctx.send('ERR: commande non utilisable sur ce serveur')
            return

        [warstats_id, tbChannel_id] = result
        if warstats_id==0 or tbChannel_id==0:
            await ctx.send('ERR: commande non utilisable sur ce serveur')
            return

        #Lecture du statut des pelotons sur warstats
        tbs_round, dict_platoons_done, list_open_territories, \
            secs_track = connect_warstats.parse_tb_platoons(warstats_id, False)
        goutils.log2("DBG", "Current state of platoon filling: "+str(dict_platoons_done))

        #Recuperation des dernieres donnees sur gdrive
        dict_players_by_IG = connect_gsheets.load_config_players(ctx.guild.name, False)[0]

        if tbs_round == '':
            await ctx.send("Aucune BT en cours (dernier update warstats: "+int(secs_track)+" secs")
            await ctx.message.add_reaction(emoji_error)
        else:
            goutils.log2("INFO", 'Lecture terminée du statut BT sur warstats: round ' + tbs_round)

            dict_platoons_allocation = await get_eb_allocation(tbChannel_id, tbs_round)
            goutils.log2("DBG", "Platoon allocation: "+str(dict_platoons_allocation))
            
            #Comparaison des dictionnaires
            #Recherche des persos non-affectés
            erreur_detectee = False
            list_platoon_names = sorted(dict_platoons_done.keys())
            phase_names_already_displayed = []
            list_txt = []  #[[joueur, peloton, txt], ...]
            list_err = []
            # print(dict_platoons_done["GDS1-top-5"])
            # print(dict_platoons_allocation["GDS1-top-5"])
            for platoon_name in dict_platoons_done:
                phase_name = platoon_name[0:3]
                if not phase_name in phase_names_already_displayed:
                    phase_names_already_displayed.append(phase_name)
                for perso in dict_platoons_done[platoon_name]:
                    if '' in dict_platoons_done[platoon_name][perso]:
                        if platoon_name in dict_platoons_allocation:
                            if perso in dict_platoons_allocation[platoon_name]:
                                for allocated_player in dict_platoons_allocation[
                                        platoon_name][perso]:
                                    if not allocated_player in dict_platoons_done[
                                            platoon_name][perso]:
                                        erreur_detectee = True
                                        if (allocated_player in dict_players_by_IG) and display_mentions:
                                            list_txt.append([
                                                allocated_player, platoon_name,
                                                '**' +
                                                dict_players_by_IG[allocated_player][1] +
                                                '** n\'a pas affecté ' + perso +
                                                ' en ' + platoon_name
                                            ])
                                        else:
                                            #joueur non-défini dans gsheets ou mentions non autorisées,
                                            # on l'affiche quand même
                                            list_txt.append([
                                                allocated_player, platoon_name,
                                                '**' + allocated_player +
                                                '** n\'a pas affecté ' + perso +
                                                ' en ' + platoon_name
                                            ])
                            else:
                                erreur_detectee = True
                                list_err.append('ERR: ' + perso +
                                                ' n\'a pas été affecté ('+platoon_name+')')
                                goutils.log('ERR', "guionbot_discord.vdp", perso + ' n\'a pas été affecté')
                                goutils.log("ERR", "guionbot_discord.vdp", dict_platoons_allocation[platoon_name].keys())

            full_txt = ''
            cur_phase = 0

            for txt in sorted(list_txt, key=lambda x: (x[1][:4], x[0], x[1])):
                if cur_phase != int(txt[1][3]):
                    cur_phase = int(txt[1][3])
                    full_txt += '\n---- **Phase ' + str(cur_phase) + '**\n'

                position = txt[1].split('-')[1]
                if position == 'top':
                    open_for_position = list_open_territories[0]
                elif position == 'mid':
                    open_for_position = list_open_territories[1]
                else:  #bottom
                    open_for_position = list_open_territories[2]
                if cur_phase < open_for_position:
                    full_txt += txt[2] + ' -- *et c\'est trop tard*\n'
                else:
                    full_txt += txt[2] + '\n'

            if erreur_detectee:
                for txt in sorted(set(list_err)):
                    full_txt += txt + '\n'
            else:
                full_txt = "Aucune erreur de peloton\n"

            secs_track_txt = str(int(secs_track/60))+" min "+str(secs_track%60)+ " s"
            full_txt += "(dernier update warstats : "+secs_track_txt+")"

            for txt in goutils.split_txt(full_txt, MAX_MSG_SIZE):
                await output_channel.send(txt)

            await ctx.message.add_reaction(emoji_check)
        
    ##############################################################
    # Command: platoons
    # Parameters: alias of the character to find
    # Purpose: Tag all players in the guild which own the selected character
    # Display: One line with all discord tags
    ##############################################################
    @commands.check(is_officer)
    @commands.command(name='platoons',
                 brief="Affecte les pelotons pour la BT",
                 help="Affecte les pelotons pour la BT\n\n"\
                      "Exemple : go.platoons me ROTE1-DS-6 ROTE1-Mix-2\n"\
                      "Exemple : go.platoons me ROTE1-DS ROTE1-Mix\n"\
                      "Exemple : go.platoons me ROTE1")
    async def platoons(self, ctx, *args):
        await ctx.message.add_reaction(emoji_thumb)

        #Check arguments
        args = list(args)

        if len(args) >= 2:
            allyCode = args[0]
            list_zones = args[1:]
        else:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help platoons")
            await ctx.message.add_reaction(emoji_error)
            return

        allyCode = manage_me(ctx, allyCode)
                
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            err, errtxt, dict_players = go.allocate_platoons(allyCode, list_zones)
            if err == 1:
                for txt in goutils.split_txt(errtxt, MAX_MSG_SIZE):
                    await ctx.send(txt)
                if len(dict_players)==0:
                    await ctx.send("Aucune ops possibles parmi ces zones")
                else:
                    await ctx.send("CONSEIL: choisir parmi les ops possibles : "+" ".join(dict_players))
                await ctx.message.add_reaction(emoji_error)
            elif err == 2:
                await ctx.send("ERR: "+errtxt)
                await ctx.message.add_reaction(emoji_error)
            else:
                dict_players_by_IG = connect_gsheets.load_config_players(ctx.guild.name, False)[0]
                output_txt=""
                for p in sorted(dict_players.keys()):
                    if p in dict_players_by_IG:
                        p_name = dict_players_by_IG[p][1]
                    else:
                        p_name=p

                    for x in dict_players[p]:
                        output_txt += p_name+" doit poser "+x[1]+" en "+x[0] +"\n"

                for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                    await ctx.send(txt)

                await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: srg
    # Parameters: minimum relic level
    # Purpose: display the PG for DS and LS characters above a minimum relic level
    # Display: the total PG for DS, LS and total
    ##############################################################
    @commands.check(is_officer)
    @commands.command(name='srg',
                 brief="Synthèse de PG pour un niveau de Relic dans la Guilde",
                 help="Synthèse de PG pour un niveau de Relic dans la Guilde\n\n"\
                      "Exemple : go.srg me R5")
    async def srg(self, ctx, *args):
        await ctx.message.add_reaction(emoji_thumb)

        #Check arguments
        args = list(args)

        if len(args) == 2:
            allyCode = args[0]
            relic_min = args[1]
        else:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help srg")
            await ctx.message.add_reaction(emoji_error)
            return

        allyCode = manage_me(ctx, allyCode)
                
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
            return

        if relic_min[0] != 'R' or not relic_min[1:].isnumeric():
            await ctx.send("ERR: relic minimum incorect")
            await ctx.message.add_reaction(emoji_error)
            return
        relic_min = relic_min[1:]

        query = "SELECT guildName, " \
              + "ROUND(sum(CASE WHEN forceAlignment<>3 THEN gp ELSE 0 END)/1000000,1) as 'PG DS/N', " \
              + "ROUND(sum(CASE WHEN forceAlignment<>2 THEN gp ELSE 0 END)/1000000,1) as 'PG LS/N', " \
              + "ROUND(sum(gp)/1000000,1) as 'PG' " \
              + "FROM roster JOIN players ON players.allyCode = roster.allyCode " \
              + "WHERE players.guildName = (SELECT guildName FROM players WHERE allyCode='"+allyCode+"') " \
              + "AND (relic_currentTier-2)>="+relic_min+" " \
              + "group by guildName "
        goutils.log2("DBG", query)
        output = connect_mysql.text_query(query)
        output_txt = ""
        for row in output:
            output_txt+=str(row)+'\n'
        await ctx.send('`' + output_txt + '`')

        await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: tpg
    # Parameters: alias of the character to find
    # Purpose: Tag all players in the guild which own the selected character
    # Display: One line with all discord tags
    ##############################################################
    @commands.check(is_officer)
    @commands.command(name='tpg',
                 brief="Tag les possesseurs d'un Perso dans la Guilde",
                 help="Tag les possesseurs d'un Perso dans la Guilde\n\n"\
                      "(ajouter '-TW' pour prendre en compte les persos posés en défense de GT)\n"\
                      "Exemple : go.tbg me SEE\n"\
                      "Exemple : go.tbg me SEE:G13")
    async def tpg(self, ctx, *args):
        await ctx.message.add_reaction(emoji_thumb)

        #Check arguments
        args = list(args)
        if "-TW" in args:
            tw_mode = True
            args.remove("-TW")
        else:
            tw_mode = False

        if len(args) == 2:
            allyCode = args[0]
            character_alias = args[1]
        else:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help tpg")
            await ctx.message.add_reaction(emoji_error)
            return

        allyCode = manage_me(ctx, allyCode)
                
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            err, errtxt, ret_cmd = go.tag_players_with_character(allyCode, character_alias,
                                                                 ctx.guild.name, tw_mode)
            if err != 0:
                await ctx.send(errtxt)
                await ctx.message.add_reaction(emoji_error)
            else:
                intro_txt = ret_cmd[0]
                if len(ret_cmd) > 1:
                    await ctx.send(intro_txt +" :\n" +' / '.join(ret_cmd[1:]))
                else:
                    await ctx.send(intro_txt +" : aucun joueur")

                await ctx.message.add_reaction(emoji_check)

##############################################################
# Class: MemberCog
# Description: contains all member commands
##############################################################
class MemberCog(commands.Cog, name="Commandes pour les membres"):
    def __init__(self, bot):
        self.bot = bot

    ##############################################################
    # Function: command_allowed
    # Parameters: ctx (objet Contexte)
    # Purpose: vérifie si on est en mode test
    #          En mode test, seuls les admins peuvent lancer des commandes
    # Output: True/False
    ##############################################################
    async def command_allowed(ctx):
        is_owner = (str(ctx.author.id) in config.GO_ADMIN_IDS.split(' '))
        return (not bot_test_mode) or is_owner

    ##############################################################
    # Command: qui
    # Parameters: code allié (string) ou "me" ou pseudo ou @mention
    # Purpose: Donner les infos de base d'unee personne
    # Display: Nom IG, Nom discord, Code allié, statut dans la DB
    #          pareil pour sa guild
    #          et des liens (swgoh.gg ou warstats)
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='qui',
                      brief="Identifie un joueur et sa guilde",
                      help="Identifie un joueur et sa guilde\n\n"\
                           "Exemple: go.qui 192126111\n"\
                           "Exemple: go.qui dark Patoche\n"\
                           "Exemple: go.qui @chaton372")
    async def qui(self, ctx, *alias):
        await ctx.message.add_reaction(emoji_thumb)

        full_alias = " ".join(alias)
        allyCode = manage_me(ctx, full_alias)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            #Look in DB
            query = "SELECT name, guildName, lastUpdated FROM players WHERE allyCode = " + allyCode
            result = connect_mysql.get_line(query)
            if result != None:
                player_name = result[0]
                guildName = result[1]
                lastUpdated = result[2]
                lastUpdated_txt = lastUpdated.strftime("%d/%m/%Y %H:%M:%S")
            else:
                #Unknown allyCode in DB
                e, t, dict_player = go.load_player(allyCode, 0, True)
                if e == 0:
                    player_name = dict_player["name"]
                    guildName = dict_player["guildName"]
                    lastUpdated_txt = "joueur inconnu"
                else:
                    player_name = "???"
                    guildName = "???"
                    lastUpdated_txt = "joueur inconnu"

            #Look for Discord Pseudo if in guild
            dict_players_by_IG = connect_gsheets.load_config_players(ctx.guild.name, False)[0]
            if player_name in dict_players_by_IG:
                discord_mention = dict_players_by_IG[player_name][1]
                ret_re = re.search("<@(\\d*)>.*", discord_mention)
                try:
                    discord_id = ret_re.group(1)
                    discord_user = await ctx.guild.fetch_member(discord_id)
                    discord_name = discord_user.display_name
                except:
                    discord_name = "???"
            else:
                discord_name = "???"

            swgohgg_url = "https://swgoh.gg/p/" + allyCode
            try:
                r = get(swgohgg_url)
                if r.status_code == 404:
                    swgohgg_url = "introuvable"
            except urllib.error.HTTPError as e:
                swgohgg_url = "introuvable"

            warstats_url = "https://goh.warstats.net/players/view/" + allyCode
            try:
                r = get(warstats_url)
                if r.status_code == 404:
                    warstats_url = "introuvable"
            except urllib.error.HTTPError as e:
                warstats_url = "introuvable"

            txt = "Qui est **"+full_alias+"** ?\n"
            txt+= "- code allié : "+str(allyCode)+"\n"
            txt+= "- pseudo IG : "+player_name+"\n"
            txt+= "- pseudo Discord : "+discord_name+"\n"
            txt+= "- guilde : "+guildName+"\n"
            txt+= "- dernier refresh du bot : "+lastUpdated_txt+"\n"
            txt+= "- lien SWGOH.GG : <"+swgohgg_url + ">\n"
            txt+= "- lien WARSTATS : <"+warstats_url + ">"

            await ctx.send(txt)

            await ctx.message.add_reaction(emoji_check)
    ##############################################################
    # Command: vtg
    # Parameters: code allié (string) ou "me", une liste de teams séparées par des espaces ou "all"
    # Purpose: Vérification des Teams de la Guilde avec tri par progrès
    # Display: Un tableau avec un joueur par ligne et des peros + stats en colonne
    #          ou plusieurs tableaux à la suite si plusieurs teams
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='vtg',
                      brief="Vérifie la dispo d'une team dans la guilde",
                      help="Vérifie la dispo d'une team dans la guilde\n\n"\
                           "(ajouter '-TW' pour prendre en compte les persos posés en défense de GT)\n"\
                           "Exemple: go.vtg 192126111 all\n"\
                           "Exemple: go.vtg 192126111 NS\n"\
                           "Exemple: go.vtg 192126111 PADME NS DR\n"\
                           "Exemple: go.vtg me NS")
    async def vtg(self, ctx, allyCode, *teams):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)
                
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            teams = list(teams)
            if "-TW" in teams:
                tw_mode = True
                teams.remove("-TW")
            else:
                tw_mode = False

            if len(teams) == 0:
                teams = ["all"]

            err, ret_cmd = await bot.loop.run_in_executor(None, go.print_vtg,
                                                    teams, allyCode, ctx.guild.name, tw_mode)
            if err == 0:
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send(txt)

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)
            else:
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emoji_error)

    ##############################################################
    # Command: vtj
    # Parameters: code allié (string), une liste de teams séparées par des espaces ou "all"
    # Purpose: Vérification des Teams d'un joueur avec tri par progrès
    # Display: Une ligne par joueur avec des peros + stats en colonne
    #          ou plusieurs ligne à la suite si plusieurs teams
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='vtj',
                 brief="Vérifie la dispo d'une ou plusieurs teams chez un joueur",
                 help="Vérifie la dispo d'une ou plusieurs teams chez un joueur\n\n"\
                      "(ajouter '-TW' pour prendre en compte les persos posés en défense de GT)\n"\
                      "Exemple: go.vtj 192126111 all\n"\
                      "Exemple: go.vtj 192126111 NS\n"\
                      "Exemple: go.vtj 192126111 PADME NS DR\n"\
                      "Exemple: go.vtj me NS")
    async def vtj(self, ctx, allyCode, *teams):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            teams = list(teams)
            if "-TW" in teams:
                tw_mode = True
                teams.remove("-TW")
            else:
                tw_mode = False

            if len(teams) == 0:
                teams = ["all"]

            err, txt, images = await bot.loop.run_in_executor(None, go.print_vtj,
                                                    teams, allyCode, ctx.guild.name, tw_mode)
            if err != 0:
                await ctx.send(txt)
                await ctx.message.add_reaction(emoji_error)
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
                await ctx.message.add_reaction(emoji_check)

    @commands.check(command_allowed)
    @commands.command(name='pfj',
                 brief="Donne le progrès de farming perso chez un joueur",
                 help="Donne le progrès de farming perso chez un joueur\n\n"\
                      "Exemple: go.pfj 192126111\n"\
                      "Exemple: go.pfj me")
    async def pfj(self, ctx, allyCode):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            err_code, ret_cmd = await bot.loop.run_in_executor(None, go.print_pfj, allyCode, ctx.guild.name)
            if err_code == 0:
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send("`"+txt+"`")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)
            else:
                await ctx.send(ret_cmd)

    @commands.check(command_allowed)
    @commands.command(name='pfg',
                 brief="Donne le progrès de farming perso dans la guilde",
                 help="Donne le progrès de farming perso dans la guilde\n\n"\
                      "Exemple: go.pjg 192126111\n"\
                      "Exemple: go.pjg me")
    async def pfg(self, ctx, allyCode):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            err_code, ret_cmd = await bot.loop.run_in_executor(None, go.print_pfg, allyCode, ctx.guild.name)
            if err_code == 0:
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send("`"+txt+"`")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)
            else:
                await ctx.send(ret_cmd)

    ##############################################################
    # Command: gvj
    # Parameters: code allié (string), une liste de persos séparées par des espaces ou "all"
    # Purpose: Progrès dans le guide de voyage pour un perso
    # Display: Une ligne par requis du guide de voyage
    #          un score global à la fin
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='gvj',
                 brief="Donne le progrès dans le guide de voyage pour un perso chez un joueur",
                 help="Donne le progrès dans le guide de voyage pour un perso chez un joueur\n\n"\
                      "Exemple: go.gvj 192126111 all\n"\
                      "Exemple: go.gvj me SEE\n"\
                      "Exemple: go.gvj me thrawn JKL")
    async def gvj(self, ctx, allyCode, *characters):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            if len(characters) == 0:
                characters = ["all"]
                
            err_code, ret_cmd = await bot.loop.run_in_executor(None, go.print_gvj, characters, allyCode)
            if err_code == 0:
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send("`"+txt+"`")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)
            else:
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emoji_error)

    ##############################################################
    # Command: gvg
    # Parameters: code allié (string),
    #               une liste de persos séparées par des espaces ou "all"
    # Purpose: Progrès dans le guide de voyage pour un perso
    # Display: Une ligne par perso - joueur, avec son score
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='gvg',
                 brief="Donne le progrès dans le guide de voyage pour une perso dans la guilde",
                 help="Donne le progrès dans le guide de voyage pour une perso dans la guilde\n\n"\
                      "Exemple: go.gvg 192126111 all\n"\
                      "Exemple: go.gvg me SEE\n"\
                      "Exemple: go.gvg me thrawn JKL\n"\
                      "La commande n'affiche que les 40 premiers.")
    async def gvg(self, ctx, allyCode, *characters):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            if len(characters) == 0:
                characters = ["all"]

            err_code, ret_cmd = await bot.loop.run_in_executor(None, go.print_gvg, characters, allyCode)
            if err_code == 0:
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send("`"+txt+"`")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)
            else:
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emoji_error)

    ##############################################################
    # Command: gvs
    # Parameters: code allié (string), perso ou ship
    # Purpose: Progrès dans le guide de voyage pour un perso dans le shard
    # Display: Une ligne par joueur, avec son score
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='gvs',
                 brief="Donne le progrès dans le guide de voyage pour un perso dans le shard",
                 help="Donne le progrès dans le guide de voyage pour un perso dans le shard\n\n"\
                      "Exemple: go.gvs me Profundity\n"\
                      "Exemple: go.gvg 123456789 Jabba")
    async def gvs(self, ctx, allyCode, *characters):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            if len(characters) != 1:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help gvs")
                await ctx.message.add_reaction(emoji_error)
                return

            err_code, ret_cmd = await bot.loop.run_in_executor(None, go.print_gvs, characters, allyCode)
            if err_code == 0:
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send("`"+txt+"`")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)
            else:
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emoji_error)

    ##############################################################
    # Command: scg
    # Parameters: code allié (string) ou "me"
    # Purpose: Score de Counter de la Guilde
    # Display: Un premier tableau donnant la dispo des équipes utilisées en counter
    #          Un 2e tableau donnant les possibilités de counter contre des équipes données
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='scg',
                 brief="Capacité de contre de la guilde",
                 help="Capacité de contre de la guilde\n\n"\
                      "Exemple: go.scg 192126111\n"\
                      "Exemple: go.scg me")
    async def scg(self, ctx, allyCode):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            ret_cmd = await bot.loop.run_in_executor(None,
                go.guild_counter_score, allyCode)
            if ret_cmd[0:3] == 'ERR':
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emoji_error)
            else:
                #texte classique
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send(txt)

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: spj
    # Parameters: code allié (string) ou "me" / nom approximatif d'un perso
    # Purpose: stats vitesse et pouvoir d'un perso
    # Display: la vitess et le pouvoir
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='spj',
                 brief="Stats de Perso d'un Joueur",
                 help="Stats de Perso d'un Joueur\n\n"\
                      "Potentiellement trié par vitesse (-v), les dégâts (-d), la santé (-s), le pouvoir (-p)\n"\
                      "Exemple: go.spj 123456789 JKR\n"\
                      "Exemple: go.spj me -v \"Dark Maul\" Bastila\n"\
                      "Exemple: go.spj me -p all")
    async def spj(self, ctx, allyCode, *characters):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
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
                ret_cmd = await bot.loop.run_in_executor(None,
                    go.print_character_stats, list_characters,
                    list_options, allyCode, False)
            else:
                ret_cmd = 'ERR: merci de préciser au maximum une option de tri'
                
            if ret_cmd[0:3] == 'ERR':
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emoji_error)
            else:
                #texte classique
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send("```"+txt+"```")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)
    
    ##############################################################
    # Command: spg
    # Parameters: code allié (string) ou "me" / nom approximatif d'un perso
    # Purpose: stats vitesse et pouvoir d'un perso sur toute la guilde
    # Display: la vitess et le pouvoir
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='spg',
                 brief="Stats de Perso d'une Guilde",
                 help="Stats de Perso d'une Guilde\n\n"\
                      "Potentiellement trié par vitesse (-v), les dégâts (-d), la santé (-s), le pouvoir (-p)\n"\
                      "Exemple: go.spg 123456789 JKR\n"\
                      "Exemple: go.spj me -v \"Dark Maul\"")
    async def spg(self, ctx, allyCode, *characters):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
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
                    ret_cmd = await bot.loop.run_in_executor(None,
                        go.print_character_stats, list_characters,
                        list_options, allyCode, True)
                else:
                    ret_cmd = 'ERR: merci de préciser au maximum une option de tri'
            else:
                ret_cmd = 'ERR: merci de préciser perso'
                
            if ret_cmd[0:3] == 'ERR':
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emoji_error)
            else:
                #texte classique
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send("```"+txt+"```")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: gdp
    # Parameters: code allié (string) ou "me"
    # Purpose: graph de distribution des PG des membres de la guilde
    # Display: graph (#=actif, .=inactif depuis 36 heures)
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='gdp',
                 brief="Graphique des PG d'une guilde",
                 help="Graphique des PG d'une guilde\n\n"\
                      "Exemple: go.gdp me\n"\
                      "Exemple: go.gdp 123456789")
    async def gdp(self, ctx, allyCode):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            # First call to display the chart quickly, without the inactive players
            e, err_txt, image = await bot.loop.run_in_executor(None,
                go.get_gp_distribution, allyCode)
            if e != 0:
                await ctx.send(err_txt)
                await ctx.message.add_reaction(emoji_error)
            else:
                with BytesIO() as image_binary:
                    image.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    await ctx.send(content = "",
                           file=File(fp=image_binary, filename='image.png'))

                await ctx.message.add_reaction(emoji_hourglass)

                # Now load all players from the guild
                await bot.loop.run_in_executor(None, go.load_guild, allyCode, True, True)

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.remove_reaction(emoji_hourglass, bot.user)
                await ctx.message.add_reaction(emoji_check)
                
    ##############################################################
    # Command: ggv
    # Parameters: code allié (string) ou "me"
    #             nom du perso
    # Purpose: graph de progrès de GV du perso
    # Display: graph
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='ggv',
                 brief="Graphique de GV d'un perso",
                 help="Graphique de GV d'un perso\n\n"\
                      "Exemple: go.ggv me SEE\n"\
                      "Exemple: go.ggv me FARM\n"\
                      "Exemple: go.ggv 123456789 JMK")
    async def ggv(self, ctx, allyCode, *characters):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
            return

        if len(characters) == 0:
            characters = ["all"]

        #First run a GVJ to ensure at least on result
        if "FARM" in characters:
            characters = ["FARM"]
            err_code, ret_cmd = await bot.loop.run_in_executor(None,
                                                           go.print_pfj,
                                                           allyCode,
                                                           ctx.guild.name)
        else:
            err_code, ret_cmd = await bot.loop.run_in_executor(None,
                                                           go.print_gvj,
                                                           characters,
                                                           allyCode)
        if err_code != 0:
            await ctx.send(ret_cmd)
            await ctx.message.add_reaction(emoji_error)
            return
        
        #Seoncd, display the graph
        err_code, err_txt, image = await bot.loop.run_in_executor(None,
                                                                  go.get_gv_graph,
                                                                  allyCode,
                                                                  characters)
        if err_code != 0:
            await ctx.send(err_txt)
            await ctx.message.add_reaction(emoji_error)
            return

        #Display the output image
        with BytesIO() as image_binary:
            image.save(image_binary, 'PNG')
            image_binary.seek(0)
            await ctx.send(content = "",
                   file=File(fp=image_binary, filename='image.png'))

        await ctx.message.add_reaction(emoji_check)
        

    ##############################################################
    # Command: gmj
    # Parameters: code allié (string) ou "me"
    # Purpose: graph de progrès de modq du joueur
    # Display: graph
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='gmj',
                 brief="Graphique de Modq d'un Joueur",
                 help="Graphique de Modq d'un Joueur\n\n"\
                      "Exemple: go.gmj me")
    async def gmj(self, ctx, allyCode):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            e, err_txt, image = await bot.loop.run_in_executor(None, go.get_modq_graph, allyCode)
            if e != 0:
                await ctx.send(err_txt)
                await ctx.message.add_reaction(emoji_error)
            else:
                with BytesIO() as image_binary:
                    image.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    await ctx.send(content = "",
                           file=File(fp=image_binary, filename='image.png'))

                await ctx.message.add_reaction(emoji_check)
                

    ##############################################################
    # Command: ppj
    # Parameters: code allié (string) ou "me" / nom approximatif des perso
    # Purpose: afficher une image des portraits choisis
    # Display: l'image produite
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='ppj',
                 brief="Portraits de Perso d'un Joueur",
                 help="Portraits de Perso d'un Joueur\n"\
                      "Exemple: go.ppj 123456789 JKR\n"\
                      "Exemple: go.ppj me -v \"Dark Maul\" Bastila\n")
    async def ppj(self, ctx, allyCode, *characters):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode = manage_me(ctx, allyCode)

        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            if len(characters) > 0:
                e, ret_cmd, images = await bot.loop.run_in_executor(None,
                    go.get_character_image, [[list(characters), allyCode, '']], False, True, '', ctx.guild.name)
                    
                if e == 0:
                    for image in images:
                        with BytesIO() as image_binary:
                            image.save(image_binary, 'PNG')
                            image_binary.seek(0)
                            await ctx.send(content = ret_cmd,
                                   file=File(fp=image_binary, filename='image.png'))

                    #Icône de confirmation de fin de commande dans le message d'origine
                    await ctx.message.add_reaction(emoji_check)

                else:
                    ret_cmd += 'ERR: merci de préciser un ou plusieurs persos'
                    await ctx.send(ret_cmd)
                    await ctx.message.add_reaction(emoji_error)

            else:
                ret_cmd = 'ERR: merci de préciser un ou plusieurs persos'
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emoji_error)                
                
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
    @commands.check(command_allowed)
    @commands.command(name='rgt',
                 brief="Image d'un Résultat en Guerre de Territoire",
                 help="Image d'un Résultat en Guerre de Territoire\n"\
                      "Exemple: go.rgt me GAS echo cra fives rex VS DR\n")
    async def rgt(self, ctx, *options):
        await ctx.message.add_reaction(emoji_thumb)

        # Extract command options
        if not ("VS" in options):
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help rgt")
            await ctx.message.add_reaction(emoji_error)
            return

        pos_vs = options.index("VS")
        if pos_vs < 2:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help rgt")
            await ctx.message.add_reaction(emoji_error)
            return

        allyCode_attack = options[0]
        list_char_attack = options[1:pos_vs]

        allyCode_attack = manage_me(ctx, allyCode_attack)
        if allyCode_attack[0:3] == 'ERR':
            await ctx.send(allyCode_attack)
            await ctx.message.add_reaction(emoji_error)
            return

        if len(options) != (pos_vs+2):
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help rgt")
            await ctx.message.add_reaction(emoji_error)
            return

        #only a character is given
        character_defense = options[pos_vs+1]

        # Computes images
        e, ret_cmd, images = await bot.loop.run_in_executor(None,
                    go.get_tw_battle_image, list_char_attack, allyCode_attack, \
                                             character_defense, ctx.guild.name)
                        
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
                        emoji_letter = emoji_letters[letter_idx]
                        await new_msg.add_reaction(emoji_letter)
                    cur_list_msgIDs.append([new_msg, sizes])
                first_image = False

            # Add the message list to the global message list, waiting for reaction
            list_tw_opponent_msgIDs.append([ctx.author, cur_list_msgIDs])

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emoji_check)
        else:
            await ctx.send(ret_cmd)
            await ctx.message.add_reaction(emoji_error)

    ##############################################################
    # Command: gsp
    # Parameters: code allié (string) ou "me"
    #             un perso
    #             une statistique
    # Purpose: afficher un raph des stats de ce persos sur les G13 connus
    #          et la position du joueur dans ce graph
    # Display: l'image du graph
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='gsp',
                 brief="Graphique d'une Statistique d'un Perso",
                 help="Graphique d'une Statistique d'un Perso\n"\
                      "Exemple: go.gsp me GAS vitesse")
    async def gsp(self, ctx, *options):
        await ctx.message.add_reaction(emoji_thumb)

        if len(options) != 3:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help gsp")
            await ctx.message.add_reaction(emoji_error)
            return

        allyCode = options[0]
        alias = options[1]
        stat = options[2]
            
        allyCode= manage_me(ctx, allyCode)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
            return

        e, err_txt, image = await bot.loop.run_in_executor(None,
                    go.get_stat_graph, allyCode, alias, stat)
        if e == 0:
            with BytesIO() as image_binary:
                image.save(image_binary, 'PNG')
                image_binary.seek(0)
                await ctx.send(content = err_txt,
                       file=File(fp=image_binary, filename='image.png'))
            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emoji_check)
        else:
            await ctx.send(err_txt)
            await ctx.message.add_reaction(emoji_error)

    ##############################################################
    # Command: erj
    # Parameters: player idenfier
    # Purpose: summary of roster evolution for a player
    # Display: list
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='erj',
                 brief="Evolution du Roster d'un Joueur",
                 help="Evolution du roster d'un joueur sur X jours\n"\
                      "Exemple: go.erj me 30")
    async def erj(self, ctx, allyCode, days=30):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode= manage_me(ctx, allyCode)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
            return

        e, ret_cmd = await bot.loop.run_in_executor(None,
                    go.print_erx, allyCode, days, False)
        if e == 0:
            #texte classique
            for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                await ctx.send(txt)

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emoji_check)
        else:
            await ctx.send(ret_cmd)
            await ctx.message.add_reaction(emoji_error)

    ##############################################################
    # Command: erg
    # Parameters: player idenfier
    # Purpose: summary of roster evolution for a guild
    # Display: list
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='erg',
                 brief="Evolution du Roster d'un Joueur",
                 help="Evolution du roster d'un joueur sur X jours\n"\
                      "Exemple: go.erg me 30")
    async def erg(self, ctx, allyCode, days=30):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode= manage_me(ctx, allyCode)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
            return

        e, ret_cmd = await bot.loop.run_in_executor(None,
                    go.print_erx, allyCode, days, True)
        if e == 0:
            #texte classique
            for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                await ctx.send(txt)

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emoji_check)
        else:
            await ctx.send(ret_cmd)
            await ctx.message.add_reaction(emoji_error)

    ##############################################################
    # Command: loj
    # Parameters: player idenfier
    # Purpose: list of omicrons of a player
    # Display: list
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='loj',
                 brief="Liste des Omicrons d'un Joueur",
                 help="Liste des Omicrons d'un Joueur\n"\
                      "Exemple: go.loj 123456789")
    async def loj(self, ctx, allyCode):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode= manage_me(ctx, allyCode)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
            return

        e, err_txt, txt_lines = await bot.loop.run_in_executor(None,
                                      go.print_lox, allyCode, False)
        if e == 0 and len(txt_lines) >0:
            output_txt=''
            for row in txt_lines:
                output_txt+=str(row)+'\n'
            for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                await ctx.send('`' + txt + '`')
            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emoji_check)
        elif e == 0:
            await ctx.send("Aucun omicron trouvé pour "+allyCode)
            await ctx.message.add_reaction(emoji_check)
        else:
            await ctx.send(err_txt)
            await ctx.message.add_reaction(emoji_error)

    ##############################################################
    # Command: log
    # Parameters: player idenfier
    # Purpose: list of omicrons of a guild
    # Display: list
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='log',
                 brief="Liste des Omicrons d'une Guilde",
                 help="Liste des Omicrons d'une Guilde\n"\
                      "Exemple: go.log 123456789")
    async def log(self, ctx, allyCode):
        await ctx.message.add_reaction(emoji_thumb)

        allyCode= manage_me(ctx, allyCode)
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
            return

        e, err_txt, txt_lines = await bot.loop.run_in_executor(None,
                    go.print_lox, allyCode, True)
        if e == 0 and len(txt_lines) >0:
            output_txt=''
            for row in txt_lines:
                output_txt+=str(row)+'\n'
            for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                await ctx.send('`' + txt + '`')
            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emoji_check)
        else:
            await ctx.send(ret_cmd)
            await ctx.message.add_reaction(emoji_error)

    ##############################################################
    # Command: ntg
    # Parameters: 
    #    IN: player from the guild
    #    IN: amount of teams per TW territory
    #    IN: [optional] list of players that do not participate in the TW
    # Purpose: give a recommendation of teams per player in defense
    # Display: one recommendation per group of 1M of PG
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='ntg',
                 brief="Nombre de Teams en GT",
                 help="Nombre de Teams en GT\n\n"\
                      "Exemple : go.ntg me 27\n"\
                      "Exemple : go.ntg 123456789 23 toto123 345123678")
    async def ntg(self, ctx, *args):
        await ctx.message.add_reaction(emoji_thumb)

        if len(args) < 2:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help ntg")
            await ctx.message.add_reaction(emoji_error)
            return
        else:
            ac_guild = manage_me(ctx, args[0])
            if ac_guild[0:3] == 'ERR':
                await ctx.send(ac_guild)
                await ctx.message.add_reaction(emoji_error)
                return

            try:
                team_count = int(args[1])
            except Exception as e:
                await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help ntg")
                await ctx.message.add_reaction(emoji_error)
                return

            list_ac_nonplayers = []
            for player in args[2:]:
                ac = manage_me(ctx, player)
                if ac[0:3] == 'ERR':
                    await ctx.send(ac)
                    await ctx.message.add_reaction(emoji_error)
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
            await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: trj
    # IN: name of the payer, name of the raid
    # OUT: a line with the teams for the payer to make the best score
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='trj',
                 brief="Teams de Raid du Joueur",
                 help="Teams de Raid du Joueur\n\n"
                      "Exemple : go.trj me crancor")
    async def trj(self, ctx, *args):
        await ctx.message.add_reaction(emoji_thumb)

        if len(args) != 2:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help trj")
            await ctx.message.add_reaction(emoji_error)
            return

        allyCode = args[0]
        raid_name = args[1]

        allyCode = manage_me(ctx, allyCode)
                
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
        else:
            err, txt, dict_best_teams = await bot.loop.run_in_executor(None,
                                                    go.find_best_teams_for_raid,
                                                    allyCode, ctx.guild.name, raid_name, False)
            if err !=0:
                await ctx.send(txt)
                await ctx.message.add_reaction(emoji_error)
            else:
                output_txt = ""
                for pname in dict_best_teams:
                    lbts = dict_best_teams[pname]
                    txt_teams = str(lbts[0])
                    if txt_teams == "":
                        txt_teams = "*Aucune des teams recommandées*"
                    output_txt += "**" + pname + "**: " + txt_teams + "\n"

                for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                    await ctx.send(txt)

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: cpg
    # Parameters: joueur, liste de persos
    # Purpose: compte les persos listés groupés par étoiles et gear
    # Display: un tableau
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='cpg', help="Compte les GLs d'une Guilde")
    async def info(self, ctx, *args):
        await ctx.message.add_reaction(emoji_thumb)

        if len(args) != 1:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help cpg")
            await ctx.message.add_reaction(emoji_error)
            return

        allyCode = args[0]
        allyCode = manage_me(ctx, allyCode)
                
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
            return

        # get the DB information
        query = "SELECT defId AS `Perso`, " \
              + "CASE WHEN gear=1 THEN CONCAT(rarity, '*') " \
              + "     WHEN gear<=12 THEN CONCAT(rarity, '*G', gear) " \
              + "     ELSE CONCAT(rarity, '*R', relic_currentTier-2) " \
              + "END AS `gear`, " \
              + "count(*) AS `Nombre` " \
              + "FROM players " \
              + "JOIN roster ON players.allyCode = roster.allyCode " \
              + "WHERE defId IN ('CAPITALEXECUTOR', " \
              + "                'GLREY', " \
              + "                'SUPREMELEADERKYLOREN', " \
              + "                'GRANDMASTERLUKE', " \
              + "                'SITHPALPATINE', " \
              + "                'JEDIMASTERKENOBI', " \
              + "                'LORDVADER') " \
              + "AND guildName=(SELECT guildName FROM players WHERE allyCode='"+str(allyCode)+"') " \
              + "GROUP BY defId, gear"
        goutils.log2("DBG", query)
        output = connect_mysql.text_query(query)
        if len(output) >0:
            output_txt=''
            for row in output:
                output_txt+=str(row)+'\n'
            goutils.log2('INFO', output_txt)
            for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
                await ctx.send('`' + txt + '`')
        else:
            await ctx.send('*aucun perso trouvé dans cette guilde*')

        await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: shard
    # Parameters: player, sub-commands
    # Purpose: manage members of player's shard
    # Display: depending of the sub-command
    ##############################################################
    @commands.check(command_allowed)
    @commands.command(name='shard', brief="Gère les shards du joueur",
                 help="Gère les shards du joueur\n"\
                      "Exemple : go.shard me char 123456789 > ajoute le joueur 123456789 à la liste des joueurs  de l'arène de persos"\
                      "Exemple : go.shard me ship 123456789 > ajoute le joueur 123456789 à la liste des joueurs  de l'arène de vaisseaux"\
                      "Exemple : go.shard me ship -123456789 > retire le joueur 123456789 de la liste des joueurs  de l'arène de vaisseaux"\
                      "Exemple : go.shard me char > affiche la liste des joueurs connus de l'arène de persos")
    async def shard(self, ctx, *args):
        await ctx.message.add_reaction(emoji_thumb)

        if len(args) != 3 and len(args) != 2:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help shard")
            await ctx.message.add_reaction(emoji_error)
            return

        allyCode = args[0]
        allyCode = manage_me(ctx, allyCode)
                
        if allyCode[0:3] == 'ERR':
            await ctx.send(allyCode)
            await ctx.message.add_reaction(emoji_error)
            return

        shard_type = args[1]
        if shard_type != "char" and shard_type != "ship":
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help shard")
            await ctx.message.add_reaction(emoji_error)
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

            shardmate_ac = manage_me(ctx, shardmate_ac)

            if shardmate_ac[0:3] == 'ERR':
                await ctx.send(shardmate_ac)
                await ctx.message.add_reaction(emoji_error)
                return

            if remove_player:
                await ctx.send("Suppression du shard pas encore implémentée, demander à l'admin")
                await ctx.message.add_reaction(emoji_error)
                return
            else:
                #First ensure that the player exists in DB
                e, t, player_now = await bot.loop.run_in_executor(
                                                None, go.load_player,
                                                shardmate_ac, -1, False)
                if e!=0:
                    await ctx.send(t)
                    await ctx.message.add_reaction(emoji_error)
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

        await ctx.message.add_reaction(emoji_check)


##############################################################
# MAIN EXECUTION
##############################################################
def main():
    bot_noloop_mode = False
    global bot_test_mode
    goutils.log2("INFO", "Starting...")
    # Use command-line parameters
    if len(sys.argv) > 1:
        goutils.log2("INFO", "TEST MODE - options="+str(sys.argv[1:]))
        bot_test_mode = True
        if sys.argv[1] == "noloop":
            goutils.log2("INFO", "Disable loops")
            bot_noloop_mode = True

    #Create periodic tasks
    goutils.log2("INFO", "Create tasks...")
    if not bot_noloop_mode:
        bot.loop.create_task(bot_loop_60())
        bot.loop.create_task(bot_loop_10minutes())
        bot.loop.create_task(bot_loop_5minutes())
        bot.loop.create_task(bot_loop_6hours())

    #Ajout des commandes groupées par catégorie
    goutils.log2("INFO", "Create Cogs...")
    bot.add_cog(AdminCog(bot))
    bot.add_cog(OfficerCog(bot))
    bot.add_cog(MemberCog(bot))

    #Lancement du bot
    goutils.log2("INFO", "Run bot...")
    bot.run(TOKEN)

if __name__ == "__main__":
    main()

