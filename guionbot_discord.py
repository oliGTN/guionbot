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
from discord import Activity, ActivityType, Intents, File
import go
import goutils
from connect_gsheets import load_config_players, update_online_dates
from connect_warstats import parse_warstats_page
import connect_mysql
from io import BytesIO
from requests import get

TOKEN = config.DISCORD_BOT_TOKEN
intents = Intents.default()
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix='go.', intents=intents)
guild_timezone=timezone(config.GUILD_TIMEZONE)
bot_uptime=datetime.datetime.now(guild_timezone)
MAX_MSG_SIZE = 1900 #keep some margin for extra formating characters
WARSTATS_REFRESH_SECS = 15*60
WARSTATS_REFRESH_TIME = 2*60
alert_sent_to_admin = False
bot_test_mode = False

#https://til.secretgeek.net/powershell/emoji_list.html
emoji_thumb = '\N{THUMBS UP SIGN}'
emoji_check = '\N{WHITE HEAVY CHECK MARK}'
emoji_error = '\N{CROSS MARK}'

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

dict_lastseen={} #key=discord ID, value=[discord displayname, date last seen (idle or online)]

BOT_LOOP60_ERR = "Unexpected error in bot_loop_60: "

##############################################################
#                                                            #
#                  FONCTIONS                                 #
#                                                            #
##############################################################


##############################################################
# Function: bot_loop_60
# Parameters: none
# Purpose: cette fonction est exécutée toutes les 60 secondes
#          elle rafraîchit les fichiers json récupérés de l'API swgoh
# Output: none
##############################################################
async def bot_loop_60():
    next_warstats_read = time.time()

    await bot.wait_until_ready()
    while not bot.is_closed():
        t_start = time.time()
        try:
            #REFRESH and CLEAN CACHE DATA FROM SWGOH API
            await bot.loop.run_in_executor(None, go.refresh_cache)
            
            #GET ONLINE AND MOBILE STATUS
            for guild in bot.guilds:
                list_members=[]
                for role in guild.roles:
                    if role.name==config.DISCORD_MEMBER_ROLE:
                        for member in role.members:
                            if not member.id in dict_lastseen:
                                dict_lastseen[member.id]= [member.display_name, None]
                            
                            if not(str(member.status) == 'offline' and
                                    str(member.mobile_status) == 'offline'):
                                dict_lastseen[member.id]=[member.display_name, datetime.datetime.now(guild_timezone)]
                                
                            list_members.append([member.display_name,str(member.status),str(member.mobile_status)])
            
            update_online_dates(dict_lastseen)
            
            #CHECK ALERTS FOR BT
            if time.time() >= next_warstats_read:
                list_tb_alerts, last_track_secs = go.get_tb_alerts()
                for tb_alert in list_tb_alerts:
                    userid = tb_alert[0]
                    message = tb_alert[1]
                    
                    member = bot.get_user(int(userid))
                    channel = await member.create_dm()
                    await channel.send(message)
                time_to_wait = WARSTATS_REFRESH_SECS - last_track_secs + WARSTATS_REFRESH_TIME
                next_warstats_read = int(time.time()) + time_to_wait
            print("INFO next warstat refresh in "+str(next_warstats_read-int(time.time()))+" secs")
            
        except Exception as e:
            print(BOT_LOOP60_ERR+str(sys.exc_info()[0]))
            print(e)
            await send_alert_to_admins(BOT_LOOP60_ERR+str(sys.exc_info()[0]))
        
        t_end = time.time()
        loop_duration = 60 * int(config.REFRESH_RATE_BOT_MINUTES)
        waiting_time = max(0, loop_duration - (t_end - t_start))
        
        # Wait X seconds before next loop
        await asyncio.sleep(waiting_time)

##############################################################
# Function: send_alert_to_admins
# Parameters: message (string), message to be sent
# Purpose: send a message to bot admins. Only once, then the admin has to
#          stop/start the bot for a new message to be allowed
# Output: None
##############################################################
async def send_alert_to_admins(message):
    global alert_sent_to_admin
    if not alert_sent_to_admin:
        list_ids = config.GO_ADMIN_IDS.split(' ')
        for userid in list_ids:
            member = bot.get_user(int(userid))
            channel = await member.create_dm()
            await channel.send(message)
    alert_sent_to_admin = True

##############################################################
# Function: get_eb_allocation
# Parameters: tbs_round (string) > nom de phase en TB, sous la forme "GDS2"
# Purpose: lit le channel #bateilles de territoire pour retouver
#          l'affectation des pelotons par Echobot
# Output: dict_platoons_allocation={} #key=platoon_name, value={key=perso, value=[player...]}
##############################################################
async def get_eb_allocation(tbs_round):
    # Lecture des affectation ECHOBOT
    bt_channel = bot.get_channel(int(config.EB_CHANNEL))
    dict_platoons_allocation = {}  #key=platton_name, value={key=perso, value=[player...]}
    eb_phases = []
    eb_missions_full = []
    eb_missions_tmp = []
    
    eb_sort_character=False
    eb_sort_territory = False
    eb_sort_player = False
    
    tbs_name = tbs_round[0:3]
    
    allocation_without_overview = False
    async for message in bt_channel.history(limit=500):
        if str(message.author) == config.EB_PROFILE:
            if (datetime.datetime.now(guild_timezone) - message.created_at.astimezone(guild_timezone)).days > 7:
                #On considère que si un message echobot a plus de 7 jours c'est une ancienne BT
                break

            # when the message has reactions, detect the sorting rule of the EB messages
            if len(message.reactions)>0:
                eb_sort_character=True
                eb_sort_territory = True
                eb_sort_player = True
                for reaction in message.reactions:
                    if reaction.emoji == "\N{WORLD MAP}":
                        eb_sort_territory = False
                    elif reaction.emoji == "\N{BUSTS IN SILHOUETTE}":
                        eb_sort_character = False
                    elif reaction.emoji == "\N{MOBILE PHONE}":
                        eb_sort_player = False
                
                if allocation_without_overview:
                    print("ERR: some platoons have been defined but no Overview detected!")

            if eb_sort_territory and message.content.startswith('```prolog'):
                #EB message by territory
                  
                for embed in message.embeds:
                    dict_embed = embed.to_dict()
                    if 'fields' in dict_embed:
                        # print(dict_embed)
                        #on garde le nom de la BT mais on met X comme numéro de phase
                        #le numéro de phase sera affecté plus tard
                        ret_re = re.search(':.*: \*\*(.*)\*\* - (.*)',
                                            dict_embed['description'])
                        territory_position = ret_re.group(2)
                        platoon_position = ret_re.group(1)[-1]
                        platoon_name = tbs_name + "X-" + territory_position + "-" + platoon_position
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
                    
                allocation_without_overview = True
    
            elif eb_sort_character and message.content.startswith('Common units:'):
                #EB message by unit / Common units
                for embed in message.embeds:
                    dict_embed = embed.to_dict()
                    if 'fields' in dict_embed:
                        # print(dict_embed)
                        # on garde le nom de la BT mais on met X comme numéro de phase
                        # le numéro de phase sera affecté plus tard

                        for dict_char in dict_embed['fields']:
                            char_name = re.search(':.*: (.*)', dict_char['name']).group(1)

                            for line in dict_char['value'].split('\n'):
                                # print("DBG - line: |"+line+"|")
                                if line.startswith("**"):
                                    ret_re = re.search('\*\*(.*) - [PS](.)\*\*', line)
                                    territory_position = ret_re.group(1)
                                    platoon_position = ret_re.group(2)
                                    platoon_name = tbs_name + "X-" + territory_position + "-" + platoon_position
                                else:
                                    ret_re = re.search("^(:.*: )?(`\*` )?([^:\[]*)( (:crown:|:cop:)?( `\[G[0-9]*\]`)?)?$",
                                                        line)
                                    player_name = ret_re.group(3)
                                    
                                    if player_name != 'Filled in another phase':
                                        if not platoon_name in dict_platoons_allocation:
                                            dict_platoons_allocation[platoon_name] = {}
                                        if not char_name in dict_platoons_allocation[
                                                platoon_name]:
                                            dict_platoons_allocation[platoon_name][
                                                char_name] = []
                                        dict_platoons_allocation[platoon_name][
                                            char_name].append(player_name)

                allocation_without_overview = True 
                
            elif eb_sort_character and message.content.startswith('Rare Units:'):
                #EB message by unit / Rare unis
                for embed in message.embeds:
                    dict_embed = embed.to_dict()
                    if 'fields' in dict_embed:
                        # print(dict_embed)
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
                                    player_name = ret_re.group(3)
                                        
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

                allocation_without_overview = True            
            elif eb_sort_player and "<@" in message.content and \
                not (message.content.startswith(":information_source:")):

                # print("DBG - message.content:"+str(message.content))
                #EB message by player
                for embed in message.embeds:
                    dict_embed = embed.to_dict()
                    # print("DBG - dict_embed:"+str(dict_embed))
                    if 'fields' in dict_embed:
                        #print(dict_embed)
                        #on garde le nom de la BT mais on met X comme numéro de phase
                        #le numéro de phase sera affecté plus tard
                        player_name = re.search('\*\*(.*)\*\*',
                                dict_embed['description']).group(1)

                        for dict_platoon in dict_embed['fields']:
                            # print("DBG - dict_platoon['name']:"+str(dict_platoon['name']))
                            platoon_name = tbs_name + "X-" + re.search('(.*) - .*',
                                dict_platoon['name']).group(1) + "-" + dict_platoon['name'][-1]
                                
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

                allocation_without_overview = True

            elif message.content.startswith(":information_source: **Overview**"):
                #Overview of the EB posts. Gives the territory names
                # this name helps allocatting the phase
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
                                    for key in keys_to_rename:
                                        new_key = territory_name_position+key[-2:]
                                        dict_platoons_allocation[new_key] = \
                                                dict_platoons_allocation[key]
                                        del dict_platoons_allocation[key]
                                        
                            else:
                                print('Mission \"'+territory_name+'\" inconnue')

                #Also reset parsing status as it is the top (so the end) of the allocation
                allocation_without_overview = False
                eb_sort_character=False
                eb_sort_territory = False
                eb_sort_player = False

                
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
        print(e)
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
# Parameters: allycode_txt (string) > code allié
# Purpose: affecte le code allié de l'auteur si "me"
# Output: code allié (string)
##############################################################
def manage_me(ctx, allycode_txt):
    #Special case of 'me' as allycode
    if allycode_txt == 'me':
        dict_players = load_config_players()[1]
        if ctx.author.id in dict_players.keys():
            ret_allycode_txt = str(dict_players[ctx.author.id][0])
        else:
            ret_allycode_txt = 'ERR: \"me\" ne fait pas partie de la guilde'
    elif allycode_txt[:3] == '<@!':
        # discord @mention
        discord_id_txt = allycode_txt[3:-1]
        print('INFO: cmd launched with discord @mention '+allycode_txt)
        dict_players = load_config_players()[1]
        if discord_id_txt.isnumeric() and int(discord_id_txt) in dict_players.keys():
            ret_allycode_txt = str(dict_players[int(discord_id_txt)][0])
        else:
            ret_allycode_txt = 'ERR: '+allycode_txt+' ne fait pas partie de la guilde'
    elif not allycode_txt.isnumeric():
        # Look for the name among known player names
        results = connect_mysql.simple_query("SELECT name, allyCode FROM players", False)
        #print(results)
        list_names = [x[0] for x in results[0]]
        
        closest_names=difflib.get_close_matches(allycode_txt, list_names, 1)
        #print(closest_names)
        if len(closest_names)<1:
            ret_allycode_txt = 'ERR: '+allycode_txt+' ne fait pas partie des joueurs connus'
        else:
            print('INFO: cmd launched with name that looks like '+closest_names[0])
            for r in results[0]:
                if r[0] == closest_names[0]:
                    ret_allycode_txt = str(r[1])

    else:
        # number >> allyCode
        ret_allycode_txt = allycode_txt
    
    return ret_allycode_txt

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
    go.load_guild(config.MASTER_GUILD_ALLYCODE, False)
    await bot.change_presence(activity=Activity(type=ActivityType.listening, name="go.help"))

    #recover external IP address
    ip = get('https://api.ipify.org').text
    
    msg = "\n"+bot.user.name+" has connected to Discord from ip "+ip
    print(msg)
    if not bot_test_mode:
        await send_alert_to_admins(msg)
        alert_sent_to_admin = False

##############################################################
# Event: on_reaction_add
# Parameters: reaction (object containing different other ones)
#             user (user taging with the emoji)
# Purpose: se lance quand une réaction est ajoutée à un message
# Output: none
##############################################################
@bot.event
async def on_reaction_add(reaction, user):
    message = reaction.message
    author = message.author
    
    # Manage the thumb up to boot60 error message, to reset the alert
    if message.content.startswith(BOT_LOOP60_ERR) \
        and reaction.emoji == '\N{THUMBS UP SIGN}' \
        and message.author == bot.user:
        alert_sent_to_admin = False
        message.add_reaction('\N{WHITE HEAVY CHECK MARK}')


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
    async def cmd(self, ctx, arg):
        await ctx.message.add_reaction(emoji_thumb)

        stream = os.popen(arg)
        output = stream.read()
        print('CMD: ' + arg)
        print(output)
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
        output_size = connect_mysql.simple_query("CALL get_db_size()", True)
        for row in output_size:
            output_txt+=str(row)+'\n'

        output_players = connect_mysql.simple_query("SELECT guildName AS Guilde, \
                                                    count(*) as Joueurs \
                                                    FROM players \
                                                    GROUP BY guildName", True)
        output_txt += "\n"
        for row in output_players:
            output_txt+=str(row)+'\n'


        await ctx.send('**GuiOn bot is UP** since '+str(bot_uptime)+' (GMT)\n' +
                        '``` '+output_txt[1:]+'```')

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
    async def sql(self, ctx, arg):
        await ctx.message.add_reaction(emoji_thumb)

        output = connect_mysql.simple_query(arg, True)
        print('SQL: ' + arg)
        output_txt=''
        for row in output:
            output_txt+=str(row)+'\n'
        print(output_txt)
        for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
            await ctx.send('`' + txt + '`')
        
        await ctx.message.add_reaction(emoji_check)
        
    ##############################################################
    # Command: test
    # Parameters: ça dépend...
    # Purpose: commande de test lors du dev. Doit être mise en commentaires
    #          avant déploiement en service
    # Display: ça dépend
    #############################################################
    # @commands.command(name='test', help='Réservé aux admins')
    # @commands.check(is_owner)
    # async def test(self, ctx, *args):
        # cmd_with_fields = args[0]
        # dict_players_by_IG, dict_players_by_ID = load_config_players()
        # for player_ID in dict_players_by_ID:
            # player_allycode=dict_players_by_ID[player_ID][0]
            # cmd_to_be_sent = cmd_with_fields.replace("$mention", '<@'+str(player_ID)+'>')\
                                            # .replace("$allycode", str(player_allycode))
            # print(cmd_to_be_sent)
            # await ctx.send(cmd_to_be_sent)
            # time.sleep(10)

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
        dict_players = load_config_players()[1]
        if ctx.author.id in dict_players.keys():
            if dict_players[ctx.author.id][1]:
                ret_is_officer = True

        is_owner = (str(ctx.author.id) in config.GO_ADMIN_IDS.split(' '))

        return (ret_is_officer and (not bot_test_mode)) or is_owner

    ##############################################################
    # Command: vtg_agt
    # Parameters: code allié (string) ou "me", une liste de teams séparées par des espaces ou "all"
    # Purpose: Vérification des Teams de la Guilde avec tri par PG
    # Display: Un tableau avec un joueur par ligne et des peros + stats en colonne
    #          ou plusieurs tableaux à la suite si plusieurs teams
    ##############################################################
    @commands.check(is_officer)
    @commands.command(name='vtg_agt',
                 brief="Comme vtg mais avec un autre scoring utilisé pour agt",
                 help="Comme vtg mais avec un autre scoring utilisé pour agt\n\n"\
                                  "Exemple: go.vtg_agt 192126111 all\n"\
                                  "Exemple: go.vtg_agt 192126111 NS\n"\
                                  "Exemple: go.vtg_agt 192126111 PADME NS DR\n"\
                                  "Exemple: go.vtg_agt me NS")
    async def vtg_agt(self, ctx, allycode, *teams):
        await ctx.message.add_reaction(emoji_thumb)

        allycode = manage_me(ctx, allycode)
        if allycode[0:3] == 'ERR':
            await ctx.send(allycode)
            await ctx.message.add_reaction(emoji_error)
        else:
            ret_cmd = await bot.loop.run_in_executor(None,
                go.get_team_progress, teams, allycode, True, 3, 100000, 80000, False)
            for team in ret_cmd:
                txt_team = ret_cmd[team][0]
                for txt in goutils.split_txt(txt_team, MAX_MSG_SIZE):
                    await ctx.send(txt)

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: agt
    # Parameters: code allié (string) ou "me"
    # Purpose: Assignation Guerre de Territoire
    # Display: Une ligne par affectation "joueurX doit affecter teamY en territoireZ"
    ##############################################################
    @commands.check(is_officer)
    @commands.command(name='agt', brief="Assigne les équipes par territoire en GT",
                             help="Assigne les équipes par territoire en GT\n\n"\
                                  "Exemple: go.agt me")
    async def agt(self, ctx, allycode):
        await ctx.message.add_reaction(emoji_thumb)

        allycode = manage_me(ctx, allycode)

        if allycode[0:3] == 'ERR':
            await ctx.send(allycode)
            await ctx.message.add_reaction(emoji_error)
        else:
            ret_cmd = await bot.loop.run_in_executor(None,
                go.assign_gt, allycode, False)
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
            output_channel = ctx.message.channel

        #Lecture du statut des pelotons sur warstats
        tbs_round, dict_platoons_done, \
            dict_player_allocations, \
            list_open_territories = parse_warstats_page()

        #Recuperation des dernieres donnees sur gdrive
        dict_players = load_config_players()[0]

        if tbs_round == '':
            await ctx.send('Aucune BT en cours')
            await ctx.message.add_reaction(emoji_error)
        else:
            print('Lecture terminée du statut BT sur warstats: round ' + tbs_round)

            dict_platoons_allocation = await get_eb_allocation(tbs_round)
            
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
                                        if (allocated_player in dict_players) and display_mentions:
                                            list_txt.append([
                                                allocated_player, platoon_name,
                                                '**' +
                                                dict_players[allocated_player][2] +
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
                                print('ERR: ' + perso + ' n\'a pas été affecté')
                                print(dict_platoons_allocation[platoon_name].keys())

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
                full_txt += 'Aucune erreur de peloton\n'

            for txt in goutils.split_txt(full_txt, MAX_MSG_SIZE):
                await output_channel.send(txt)

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
                           "Exemple: go.vtg 192126111 all\n"\
                           "Exemple: go.vtg 192126111 NS\n"\
                           "Exemple: go.vtg 192126111 PADME NS DR\n"\
                           "Exemple: go.vtg me NS")
    async def vtg(self, ctx, allycode, *teams):
        await ctx.message.add_reaction(emoji_thumb)

        allycode = manage_me(ctx, allycode)
                
        if allycode[0:3] == 'ERR':
            await ctx.send(allycode)
            await ctx.message.add_reaction(emoji_error)
        else:
            ret_cmd = await bot.loop.run_in_executor(None, go.print_vtx,
                                                    teams, allycode, True)
            for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                await ctx.send(txt)

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: vtj
    # Parameters: code allié (string), une liste de teams séparées par des espaces ou "all"
    # Purpose: Vérification des Teams d'un joueur avec tri par progrès
    # Display: Une ligne par joueur avec des peros + stats en colonne
    #          ou plusieurs ligne à la suite si plusieurs teams
    ##############################################################
    @commands.command(name='vtj',
                 brief="Vérifie la dispo d'une ou plusieurs teams chez un joueur",
                 help="Vérifie la dispo d'une ou plusieurs teams chez un joueur\n\n"\
                      "Exemple: go.vtj 192126111 all\n"\
                      "Exemple: go.vtj 192126111 NS\n"\
                      "Exemple: go.vtj 192126111 PADME NS DR\n"\
                      "Exemple: go.vtj me NS")
    async def vtj(self, ctx, allycode, *teams):
        await ctx.message.add_reaction(emoji_thumb)

        allycode = manage_me(ctx, allycode)
        if allycode[0:3] == 'ERR':
            await ctx.send(allycode)
            await ctx.message.add_reaction(emoji_error)
        else:
            ret_cmd = await bot.loop.run_in_executor(None, go.print_vtx,
                                                    teams, allycode, False)
            for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                await ctx.send(txt)

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: gvj
    # Parameters: code allié (string), une liste de persos séparées par des espaces ou "all"
    # Purpose: Progrès dans le guide de voyage pour un perso
    # Display: Une ligne par requis du guide de voyage
    #          un score global à la fin
    ##############################################################
    @commands.command(name='gvj',
                 brief="Donne le progrès dans le guide de voyage pour une perso chez un joueur",
                 help="Donne le progrès dans le guide de voyage pour une perso chez un un joueur\n\n"\
                      "Exemple: go.gvj 192126111 all\n"\
                      "Exemple: go.gvj me SEE\n"\
                      "Exemple: go.gvj me thrawn JKL")
    async def gvj(self, ctx, allycode, *teams):
        await ctx.message.add_reaction(emoji_thumb)

        allycode = manage_me(ctx, allycode)

        if allycode[0:3] == 'ERR':
            await ctx.send(allycode)
            await ctx.message.add_reaction(emoji_error)
        else:
            if len(teams) == 0:
                teams = ["all"]
                
            else:
                ret_cmd = await bot.loop.run_in_executor(None, go.print_gvj, teams, allycode)
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    await ctx.send("`"+txt+"`")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: gvg
    # Parameters: code allié (string),
    #               une liste de persos séparées par des espaces ou "all"
    # Purpose: Progrès dans le guide de voyage pour un perso
    # Display: Une ligne par perso - joueur, avec son score
    ##############################################################
    @commands.command(name='gvg',
                 brief="Donne le progrès dans le guide de voyage pour une perso dans la guilde",
                 help="Donne le progrès dans le guide de voyage pour une perso dans la guilde\n\n"\
                      "Exemple: go.gvg 192126111 all\n"\
                      "Exemple: go.gvg me SEE\n"\
                      "Exemple: go.gvg me thrawn JKL\n"\
                      "La commande n'affiche que les 40 premiers.")
    async def gvg(self, ctx, allycode, *teams):
        await ctx.message.add_reaction(emoji_thumb)

        allycode = manage_me(ctx, allycode)

        if allycode[0:3] == 'ERR':
            await ctx.send(allycode)
            await ctx.message.add_reaction(emoji_error)
        else:
            if len(teams) == 0:
                teams = ["all"]

            ret_cmd = await bot.loop.run_in_executor(None, go.print_gvg, teams, allycode)
            for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                await ctx.send("`"+txt+"`")

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: scg
    # Parameters: code allié (string) ou "me"
    # Purpose: Score de Counter de la Guilde
    # Display: Un premier tableau donnant la dispo des équipes utilisées en counter
    #          Un 2e tableau donnant les possibilités de counter contre des équipes données
    ##############################################################
    @commands.command(name='scg',
                 brief="Capacité de contre de la guilde",
                 help="Capacité de contre de la guilde\n\n"\
                      "Exemple: go.scg 192126111\n"\
                      "Exemple: go.scg me")
    async def scg(self, ctx, allycode):
        await ctx.message.add_reaction(emoji_thumb)

        allycode = manage_me(ctx, allycode)

        if allycode[0:3] == 'ERR':
            await ctx.send(allycode)
            await ctx.message.add_reaction(emoji_error)
        else:
            ret_cmd = await bot.loop.run_in_executor(None,
                go.guild_counter_score, allycode)
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
    @commands.command(name='spj',
                 brief="Stats de Perso d'un Joueur",
                 help="Stats de Perso d'un Joueur\n\n"\
                      "Potentiellement trié par vitesse (-v), les dégâts (-d), la santé (-s), le pouvoir (-p)\n"\
                      "Exemple: go.spj 123456789 JKR\n"\
                      "Exemple: go.spj me -v \"Dark Maul\" Bastila\n"\
                      "Exemple: go.spj me -p all")
    async def spj(self, ctx, allycode, *characters):
        await ctx.message.add_reaction(emoji_thumb)

        allycode = manage_me(ctx, allycode)

        if allycode[0:3] == 'ERR':
            await ctx.send(allycode)
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
                        go.print_character_stats, list(characters), allycode, False)
                else:
                    ret_cmd = 'ERR: merci de préciser au maximum une option de tri'
            else:
                ret_cmd = 'ERR: merci de préciser un ou plusieurs persos'
                
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
    @commands.command(name='spg',
                 brief="Stats de Perso d'une Guilde",
                 help="Stats de Perso d'une Guilde\n\n"\
                      "Potentiellement trié par vitesse (-v), les dégâts (-d), la santé (-s), le pouvoir (-p)\n"\
                      "Exemple: go.spg 123456789 JKR\n"\
                      "Exemple: go.spj me -v \"Dark Maul\"")
    async def spg(self, ctx, allycode, *characters):
        await ctx.message.add_reaction(emoji_thumb)

        allycode = manage_me(ctx, allycode)

        if allycode[0:3] == 'ERR':
            await ctx.send(allycode)
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
                        go.print_character_stats, list(characters), allycode, True)
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
    @commands.command(name='gdp',
                 brief="Graphique des PG d'une guilde",
                 help="Graphique des PG d'une guilde\n\n"\
                      "Exemple: go.gdp me\n"\
                      "Exemple: go.gdp 123456789")
    async def gdp(self, ctx, allycode):
        await ctx.message.add_reaction(emoji_thumb)

        allycode = manage_me(ctx, allycode)

        if allycode[0:3] == 'ERR':
            await ctx.send(allycode)
            await ctx.message.add_reaction(emoji_error)
        else:
            # First call to display the chart quickly, without the inactive players
            ret_cmd = await bot.loop.run_in_executor(None,
                go.get_gp_distribution, allycode, 36, True)
            if ret_cmd[0:3] == 'ERR':
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emoji_error)
            else:
                #texte classique
                list_msg = []
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    msg = await ctx.send("```"+txt+"```")
                    list_msg.append(msg)

                # Second call to load all players
                ret_cmd = await bot.loop.run_in_executor(None,
                    go.get_gp_distribution, allycode, 36, False)
                i_msg = 0
                for txt in goutils.split_txt(ret_cmd, MAX_MSG_SIZE):
                    msg = list_msg[i_msg]
                    await msg.edit(content = "```"+txt+"```")
                    i_msg += 1
                
                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: ppj
    # Parameters: code allié (string) ou "me" / nom approximatif des perso
    # Purpose: afficher une image des portraits choisis
    # Display: l'image produite
    ##############################################################
    @commands.command(name='ppj',
                 brief="Portraits de Perso d'un Joueur",
                 help="Exemple: go.ppj 123456789 JKR\n"\
                      "Exemple: go.ppj me -v \"Dark Maul\" Bastila\n")
    async def ppj(self, ctx, allycode, *characters):
        await ctx.message.add_reaction(emoji_thumb)

        allycode = manage_me(ctx, allycode)

        if allycode[0:3] == 'ERR':
            await ctx.send(allycode)
            await ctx.message.add_reaction(emoji_error)
        else:
            if len(characters) > 0:
                e, ret_cmd, image = await bot.loop.run_in_executor(None,
                    go.get_character_image, [[list(characters), allycode]], False)
                    
                if e == 0:
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
    # Command: pgs
    # Parameters: code allié (string) ou "me"
    #             liste des persos du joueur
    #             séparateur "VS"
    #             code allié adversaire
    #             un perso de l'adversaire
    # Purpose: afficher une image avec les 2 équipes et un "SUCCESS"
    # Display: l'image produite
    ##############################################################
    @commands.command(name='pgs',
                 brief="Image résumé d'un succès en Guerre de Territoire",
                 help="Exemple: go.pgs me GAS echo cra fives rex VS MechantPaBo DR\n")
    async def pgs(self, ctx, *options):
        await ctx.message.add_reaction(emoji_thumb)

        # Extract command options
        if not ("VS" in options):
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help pgs")
            await ctx.message.add_reaction(emoji_error)
            return

        pos_vs = options.index("VS")
        if pos_vs < 2:
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help pgs")
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
            await ctx.send("ERR: commande mal formulée. Veuillez consulter l'aide avec go.help pgs")
            await ctx.message.add_reaction(emoji_error)
            return

        #only a character is given
        character_defense = options[pos_vs+1]

        # Computes image
        e, ret_cmd, image = await bot.loop.run_in_executor(None,
                    go.get_tw_battle_image, list_char_attack, allyCode_attack, \
                                             character_defense)
                    
        if e == 0:
            with BytesIO() as image_binary:
                image.save(image_binary, 'PNG')
                image_binary.seek(0)
                await ctx.send(content = ret_cmd,
                           file=File(fp=image_binary, filename='image.png'))

            #Icône de confirmation de fin de commande dans le message d'origine
            await ctx.message.add_reaction(emoji_check)
        else:
            await ctx.send(ret_cmd)
            await ctx.message.add_reaction(emoji_error)


##############################################################
# MAIN EXECUTION
##############################################################
# Use command-line parameters
if len(sys.argv) > 1:
    if sys.argv[1] == "test":
        print("Launch in TEST MODE")
        bot_test_mode = True

#création de la tâche périodique à 60 secondes
bot.loop.create_task(bot_loop_60())

#Ajout des commandes groupées par catégorie
bot.add_cog(AdminCog(bot))
bot.add_cog(OfficerCog(bot))
bot.add_cog(MemberCog(bot))

#Lancement du bot
bot.run(TOKEN)
