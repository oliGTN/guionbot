# -*- coding: utf-8 -*-
# Source --> https://realpython.com/how-to-make-a-discord-bot-python/
# CERTIFICATE_VERIFY_FAILED --> https://github.com/Rapptz/discord.py/issues/4159

import os
import sys
import asyncio
import time
import datetime
from pytz import timezone
import difflib
import re
from discord.ext import commands
from discord import Activity, ActivityType, Intents
import go
from connect_gsheets import load_config_players, update_online_dates
from connect_warstats import parse_warstats_page
import connect_mysql

TOKEN = os.environ['DISCORD_BOT_TOKEN']
intents = Intents.default()
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix='go.', intents=intents)
guild_timezone=timezone(os.environ['GUILD_TIMEZONE'])
bot_uptime=datetime.datetime.now(guild_timezone)

#https://til.secretgeek.net/powershell/emoji_list.html
emoji_thumb = '\N{THUMBS UP SIGN}'
emoji_check = '\N{WHITE HEAVY CHECK MARK}'
emoji_error = '\N{CROSS MARK}'
cache_delete_minutes = 1440  #24 hours before deleting unused cache file
cache_refresh_minutes = 60  #60 minutes minimum to refresh data from the guild

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
    #global dict_players
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            #REFRESH and CLEAN CACHE DATA FROM SWGOH API²
            go.refresh_cache(cache_delete_minutes, cache_refresh_minutes, 1)
            
            #GET ONLINE AND MOBILE STATUS
            for guild in bot.guilds:
                list_members=[]
                for role in guild.roles:
                    if role.name==os.environ['DISCORD_MEMBER_ROLE']:
                        for member in role.members:
                            if not member.id in dict_lastseen:
                                dict_lastseen[member.id]= [member.display_name, None]
                            
                            if not(str(member.status) == 'offline' and
                                    str(member.mobile_status) == 'offline'):
                                dict_lastseen[member.id]=[member.display_name, datetime.datetime.now(guild_timezone)]
                                
                            list_members.append([member.display_name,str(member.status),str(member.mobile_status)])
            
            update_online_dates(dict_lastseen)
        except:
            print("Unexpected error: "+str(sys.exc_info()[0]))
        
        await asyncio.sleep(60)  #60 seconds for loop

##############################################################
# Function: get_eb_allocation
# Parameters: tbs_round (string) > nom de phase en TB, sous la forme "GDS2"
# Purpose: lit le channel #bateilles de territoire pour retouver
#          l'affectation des pelotons par Echobot
# Output: dict_platoons_allocation={} #key=platoon_name, value={key=perso, value=[player...]}
##############################################################
async def get_eb_allocation(tbs_round):
    # Lecture des affectation ECHOBOT
    bt_channel = bot.get_channel(int(os.environ['EB_CHANNEL']))
    dict_platoons_allocation = {}  #key=platton_name, value={key=perso, value=[player...]}
    eb_phases = []
    eb_missions_full = []
    eb_missions_tmp = []
    async for message in bt_channel.history(limit=500):
        if str(message.author) == os.environ['EB_PROFILE']:
            if (datetime.datetime.now(guild_timezone) - message.created_at.astimezone(guild_timezone)).days > 7:
                #On considère que si un message echobot a plus de 7 jours c'est une ancienne BT
                break

            if message.content.startswith('```prolog'):
                nom_territoire = re.search('```prolog\n(.*?) \((.*?)\)',
                                            message.content).group(1)
                #eb_missions_tmp.append(position_territoire)
                if nom_territoire in dict_BT_missions[tbs_round[0:3]]:
                    nom_position_territoire = dict_BT_missions[
                                            tbs_round[0:3]][nom_territoire]
                    #Check if this mission/territory has been allocated in previous message
                    existing_platoons = [i for i in dict_platoons_allocation.keys()
                                    if i.startswith(nom_position_territoire)]
                    if len(existing_platoons) == 0:                    
                        for embed in message.embeds:
                            dict_embed = embed.to_dict()
                            if 'fields' in dict_embed:
                                #print(dict_embed)
                                #on garde le nom de la BT mais on met X comme numéro de phase
                                #le numéro de phase sera affecté plus tard
                                platoon_name = (nom_position_territoire
                                    + '-' + re.search('\*\*(.*?)\*\*',
                                        dict_embed['description']).group(1)[-1])
                                for dict_perso in dict_embed['fields']:
                                    for perso in dict_perso['value'].split('\n'):
                                        char_name = perso[1:-1]
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
                                                char_name].append(dict_perso['name'])
                else:
                    print('Mission \"'+nom_territoire+'\" inconnue')

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
        list_names = [x[0] for x in results[0]]
        
        closest_names=difflib.get_close_matches(allycode_txt, list_names, 1)
        if len(closest_names)<1:
            ret_allycode_txt = 'ERR: '+allycode_txt+' ne fait pas partie des joueurs connus'
        else:
            print('INFO: cmd launched with name that looks like '+closest_names[0])
            ret_allycode_txt = 'ERR: '+closest_names[0]+' ne fait pas partie des joueurs connus'
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
    go.load_guild(os.environ['MASTER_GUILD_ALLYCODE'], False)
    await bot.change_presence(activity=Activity(type=ActivityType.listening, name="go.help"))
    print(f'{bot.user.name} has connected to Discord!')


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
        return str(ctx.author.id) in os.environ['GO_ADMIN_IDS'].split(' ')

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
        for txt in go.split_txt(output, 1000):
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
        output = connect_mysql.simple_query("CALL get_db_size()", True)
        output_txt=''
        for row in output:
            output_txt+=str(row)+'\n'

        await ctx.send('**GuiOn bot is UP** since '+str(bot_uptime)+' (GMT)\n' +
                        go.stats_cache() + '\n' +
                        str(cache_delete_minutes) + ' minutes before deleting\n' +
                        str(cache_refresh_minutes) + ' minutes before refreshing\n' +
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
        for txt in go.split_txt(output_txt, 1000):
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
        return ret_is_officer

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
            ret_cmd = go.guild_team(allycode, teams, 3, 100000, 80000, False)
            for team in ret_cmd:
                txt_team = ret_cmd[team][0]
                for txt in go.split_txt(txt_team, 1000):
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
            ret_cmd = go.assign_gt(allycode, False)
            if ret_cmd[0:3] == 'ERR':
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emoji_error)
            else:
                #texte classique
                for txt in go.split_txt(ret_cmd, 1000):
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
        tbs_round, dict_platoons_done, dict_player_allocations, list_open_territories = parse_warstats_page()

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

            for txt in go.split_txt(full_txt, 1000):
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
    # Command: vtg
    # Parameters: code allié (string) ou "me", une liste de teams séparées par des espaces ou "all"
    # Purpose: Vérification des Teams de la Guilde avec tri par progrès
    # Display: Un tableau avec un joueur par ligne et des peros + stats en colonne
    #          ou plusieurs tableaux à la suite si plusieurs teams
    ##############################################################
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
            ret_cmd = go.guild_team(allycode, teams, 1, 100, 80, False)
            for team in ret_cmd:
                txt_team = ret_cmd[team][0]
                for txt in go.split_txt(txt_team, 1000):
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
            ret_cmd = go.player_team(allycode, teams, 1, 100, 80, False)
            for team in ret_cmd:
                txt_team = ret_cmd[team]
                for txt in go.split_txt(txt_team, 1000):
                    await ctx.send(txt)

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
            ret_cmd = go.guild_counter_score(allycode)
            if ret_cmd[0:3] == 'ERR':
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emoji_error)
            else:
                #texte classique
                for txt in go.split_txt(ret_cmd, 1000):
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
            if len(characters) > 0:
                ret_cmd = go.print_character_stats(characters, allycode)
            else:
                ret_cmd = 'ERR: merci de préciser un ou plusieurs persos'
                
            if ret_cmd[0:3] == 'ERR':
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emoji_error)
            else:
                #texte classique
                for txt in go.split_txt(ret_cmd, 1000):
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
            ret_cmd = go.get_gp_distribution(allycode, 36)
            if ret_cmd[0:3] == 'ERR':
                await ctx.send(ret_cmd)
                await ctx.message.add_reaction(emoji_error)
            else:
                #texte classique
                for txt in go.split_txt(ret_cmd, 1000):
                    await ctx.send("```"+txt+"```")

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)

    ##############################################################
    # Command: gvj
    # Parameters: code allié (string) ou "me", nom d'un personnage
    # Purpose: afficher le progrès vers un perso du guide de voyage
    # Display: progrès général, et détai par catégorie
    ##############################################################
    @commands.command(name='gvj',
                 brief="Progrès dans le guide de voyage pour un perso",
                 help="Progrès dans le guide de voyage pour un perso\n\n"\
                      "Exemple: go.gvj me GAS\n"\
                      "Exemple: go.gvj 123456789 JKLS")
    async def gvj(self, ctx, allycode, character_alias):
        await ctx.message.add_reaction(emoji_thumb)

        allycode = manage_me(ctx, allycode)

        if allycode[0:3] == 'ERR':
            await ctx.send(allycode)
            await ctx.message.add_reaction(emoji_error)
        else:
            [progress, msg, player_name, character_name, list_progress] = go.player_journey_progress(allycode, character_alias)
            if progress == -1:
                await ctx.send(msg)
                await ctx.message.add_reaction(emoji_error)
            else:
                await ctx.send('Progrès de **'+player_name+'** pour **'+character_name+'**: '+str(int(progress*100))+'%')
                await ctx.send('__Détails :__\n')
                for prog in list_progress:
                    prog_name = prog[0]
                    prog_rate = prog[1]
                    prog_weight = prog[2]
                    await ctx.send('- '+prog_name+'('+str(prog_weight)+'): '+str(int(prog_rate*100))+'%')

                #Icône de confirmation de fin de commande dans le message d'origine
                await ctx.message.add_reaction(emoji_check)

##############################################################
# MAIN EXECUTION
##############################################################
#création de la tâche périodique à 60 secondes
bot.loop.create_task(bot_loop_60())

#Ajout des commandes groupées par catégorie
bot.add_cog(AdminCog(bot))
bot.add_cog(OfficerCog(bot))
bot.add_cog(MemberCog(bot))

#Lancement du bot
bot.run(TOKEN)
