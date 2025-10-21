# PACKAGE imports
from discord.ext import tasks, commands
from discord import Activity, ActivityType, Intents, File, DMChannel, errors as discorderrors, Embed
from discord import app_commands, Interaction
from discord import ui as discord_ui
from discord import ButtonStyle
from io import BytesIO
import re
import difflib
import sys
import traceback
from texttable import Texttable

# BOT imports
import go
import connect_rpc
import connect_mysql
import connect_gsheets
import manage_mods
import goutils
import portraits
import data

# CONSTANTS
import emojis
MAX_MSG_SIZE = 1900 #keep some margin for extra formating characters

######################################
# basic functions mixinx ctx and interactions
async def command_ack(ctx_interaction):
    msg = None
    if type(ctx_interaction) == commands.Context:
        ctx = ctx_interaction
        msg = await ctx.reply(emojis.thumb+" "+ctx.me.name+" réfléchit...")

    elif type(ctx_interaction) == Interaction:
        interaction = ctx_interaction
        await interaction.response.defer(thinking=True)
    else:
        print("In progress...")

    return msg

async def command_error(ctx_interaction, resp_msg, err_txt):
    if type(ctx_interaction) == commands.Context:
        ctx = ctx_interaction
        content = emojis.redcross+" "+err_txt

        await resp_msg.edit(content=content)

    elif type(ctx_interaction) == Interaction:
        interaction = ctx_interaction
        content = emojis.redcross+" "+err_txt

        await interaction.edit_original_response(content=content)

    else:
        print("ERROR "+err_txt)

async def command_ok(ctx_interaction, resp_msg, output_txt, images=None, files=None, intermediate=False):
    attachments = []

    if images != None:
        for image in images:
            with BytesIO() as image_binary:
                image.save(image_binary, 'PNG')
                image_binary.seek(0)
                attachments.append(File(fp=image_binary, filename='image.png'))

    if files != None:
        attachments += files

    if type(ctx_interaction) == commands.Context:
        goutils.log2("DBG", "context")
        if intermediate:
            content = emojis.hourglass+" "+output_txt
        else:
            content = emojis.check+" "+output_txt

        if attachments==[]:
            await resp_msg.edit(content=content)
        else:
            await resp_msg.edit(content=content, attachments=attachments)

    elif type(ctx_interaction) == Interaction:
        goutils.log2("DBG", "interaction")
        interaction = ctx_interaction
        if intermediate:
            content = emojis.hourglass+" "+output_txt
        else:
            content = emojis.check+" "+output_txt

        if attachments==[]:
            await interaction.edit_original_response(content=content)
        else:
            await interaction.edit_original_response(content=content, attachments=attachments)

    else:
        if intermediate==False:
            content = "OK "+output_txt
        else:
            content = "In Progress... "+output_txt

        print(content)

        for attachment in attachments:
            print(attachment)

async def command_intermediate_to_ok(ctx_interaction, resp_msg, new_txt=None):
    if type(ctx_interaction) == commands.Context:
        ctx = ctx_interaction

        if new_txt == None:
            content = resp_msg.content.replace(emojis.hourglass, emojis.check)
        else:
            content = emojis.check+" "+new_txt

        await resp_msg.edit(content=content)

    elif type(ctx_interaction) == Interaction:
        interaction = ctx_interaction
        if new_txt == None:
            content = interaction.message.content.replace(emojis.hourglass, emojis.check)
        else:
            content = emojis.check+" "+new_txt
        await interaction.edit_original_response(content=content)

    else:
        if new_txt == None:
            print("OK")
        else:
            print("OK "+new_txt)

async def send_message(ctx_interaction, output_txt, images=None, files=None):
    attachments = []

    if images != None:
        for image in images:
            with BytesIO() as image_binary:
                image.save(image_binary, 'PNG')
                image_binary.seek(0)
                attachments.append(File(fp=image_binary, filename='image.png'))

    if files != None:
        attachments += files

    if ctx_interaction != None:
        await ctx_interaction.channel.send(content=content, attachments=attachments)

    else:
        print(content)

        for attachment in attachments:
            print(attachment)

##############################################################
# interaction specifics
class ConfirmationButtons(discord_ui.View):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.confirmed: bool = False

    @discord_ui.button(label = emojis.check, style = ButtonStyle.blurple)
    async def returnTrue(self, interaction: Interaction, button: discord_ui.Button):
        self.confirmed = True
        await interaction.response.defer()
        self.stop()

    @discord_ui.button(label = emojis.redcross, style = ButtonStyle.blurple)
    async def returnFalse(self, interaction: Interaction, button: discord_ui.Button):
        await interaction.response.defer()
        self.stop()

async def confirmationPrompt(interaction: Interaction, confirmation_prompt: str) -> bool:
    view = ConfirmationButtons()
    await interaction.edit_original_response(content=confirmation_prompt, view=view)
    await view.wait()
    await interaction.edit_original_response(content="En cours...", view=None)
    return view.confirmed


##############################################################
# actual bot commands
async def gdp(ctx_interaction, allyCode):
    resp_msg = await command_ack(ctx_interaction)

    ec, et, allyCode = await manage_me(ctx_interaction, allyCode, allow_tw=True)
    if ec!=0:
        await command_error(ctx_interaction, resp_msg, et)
        return

    # Display the chart
    e, err_txt, image = await go.get_gp_distribution(allyCode)
    if e != 0:
        await command_error(ctx_interaction, resp_msg, err_txt)
        return
    
    await command_ok(ctx_interaction, resp_msg, "chargement des joueurs en cours", images=[image], intermediate=True)

    # Now load all players from the guild
    await go.load_guild(allyCode, True, True, ctx_interaction=[ctx_interaction, resp_msg])

    #Icône de confirmation de fin de commande dans le message d'origine
    await command_intermediate_to_ok(ctx_interaction, resp_msg, new_txt="chargement des joueurs OK")

##############################################################
async def registercheck(ctx_interaction, allyCode):
    try:
        resp_msg = await command_ack(ctx_interaction)

        ec, et, allyCode = await manage_me(ctx_interaction, allyCode, allow_tw=True)
        if ec!=0:
            await command_error(ctx_interaction, resp_msg, et)
            return

        # Get data from DB
        query = "SELECT guildName, name, players.allyCode, discord_id FROM players " \
                "LEFT JOIN player_discord ON players.allyCode=player_discord.allyCode " \
                "WHERE guildId=(SELECT guildId FROM players WHERE allyCode = "+str(allyCode)+") " \
                "ORDER by name "
        goutils.log2("DBG", query)
        db_data = connect_mysql.get_table(query)

        guildName = db_data[0][0]
        if guildName == '':
            output_txt = "Aucune guilde associée au compte "+str(allyCode)
        else:
            output_txt = "Liste des comptes sans discord de la guilde "+guildName
            unregistered_count = 0
            for line in db_data:
                player_name = line[1]
                player_ac = line[2]
                discord_id = line[3]
                if discord_id!=None:
                    continue
                output_txt += "\n"+player_name+", "+str(player_ac)
                unregistered_count += 1

            if unregistered_count == 0:
                output_txt = "Aucun compte sans discord de la guilde "+guildName

        await command_ok(ctx_interaction, resp_msg, output_txt, intermediate=False)

    except Exception as e:
        goutils.log2("ERR", traceback.format_exc())
        await command_error(ctx_interaction, resp_msg, "erreur inconnue")

##############################################################
async def farmeqpt(ctx_interaction, allyCode, list_alias_gear):
    try:
        resp_msg = await command_ack(ctx_interaction)

        ec, et, allyCode = await manage_me(ctx_interaction, allyCode)
        if ec!=0:
            await command_error(ctx_interaction, resp_msg, et)
            return

        # Get owned equipment, ONLY for connected users
        check_owned = False
        if ctx_interaction != None:
            ec, et, player_infos = connect_mysql.get_google_player_info(ctx_interaction.channel.id)
            if ec==0:
                connected_allyCode = player_infos["allyCode"]
                if allyCode != connected_allyCode:
                    await command_error(ctx_interaction, resp_msg, "Dans ce salon vous ne pouvez lancer la commande que pour le/la propriétaire du salon : "+player_infos["player_name"])
                    return
                check_owned = True

        ec, txt, ret_dict = await get_farmeqpt_from_player(allyCode, list_alias_gear, check_owned=check_owned)

        if ec==1:
            await command_error(ctx_interaction, resp_msg, txt)
            return

        eqpt_list = ret_dict["eqpt_list"]
        list_display_targets = ret_dict["targets"]
        # Test if there is something to display
        if len(eqpt_list)==0:
            await command_ok(ctx_interaction, resp_msg, "Tous les équipements nécessaires pour passer "+str(", ".join(list_display_targets))+" sont déjà disponibles")
            return

        # Sort with most needed first
        eqpt_list.sort(key=lambda x:x[2]-x[1])

        # Compute image
        image = portraits.get_image_from_eqpt_list(eqpt_list, display_owned=check_owned)
        await command_ok(ctx_interaction, resp_msg, "Liste des équipements nécessaires pour passer "+str(", ".join(list_display_targets)), images=[image])

    except Exception as e:
        goutils.log2("ERR", traceback.format_exc())
        await command_error(ctx_interaction, resp_msg, "erreur inconnue")

async def get_farmeqpt_from_player(allyCode, list_alias_gear, check_owned=False,
                                   dict_player=None, initialdata_player=None):
    dict_units = data.get("unitsList_dict.json")

    #Get alias and target gear/relic
    list_unit_names = []
    dict_targets = {}
    for alias in list_alias_gear:
        tab_alias = alias.split(":")
        if len(tab_alias)==1:
            target_alias = alias
            target_gear = 13
            target_relic = 0
            target_guide = False

        elif len(tab_alias)==2:
            if tab_alias[0] == "guide":
                # need to get pre-requisites for character from journey guide
                target_alias = tab_alias[1]
                target_guide = True
                target_gear = None
                target_relic = None
            else:
                target_alias = tab_alias[0]
                target_guide = False
                if tab_alias[1][0].lower() == "g" and tab_alias[1][1:].isnumeric():
                    target_gear = int(tab_alias[1][1:])
                    target_relic = 0

                    if target_gear<1 or target_gear>13:
                        return 1, "Syntax incorrecte pour le gear/relic dans "+alias, None

                elif tab_alias[1][0].lower() == "r" and tab_alias[1][1:].isnumeric():
                    target_gear = 13
                    target_relic = int(tab_alias[1][1:])

                    if target_relic<0 or target_relic>9:
                        return 1, "Syntax incorrecte pour le gear/relic dans "+alias, None

                else:
                    return 1, "Syntax incorrecte pour le gear/relic dans "+alias, None

        else: #2 ":" or more
            return 1, "Syntax incorrecte pour le gear/relic dans "+alias, None

        list_unit_names.append(target_alias)

        dict_targets[alias] = {"alias": target_alias,
                               "gear": target_gear,
                               "relic": target_relic,
                               "guide": target_guide}


    #Get unit IDs from aliases
    list_unit_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_unit_names)
    if txt != '':
        return 1, 'Impossible de reconnaître ce(s) nom(s) >> '+txt, None

    list_units = []
    list_display_targets = []
    for alias in dict_targets:
        target = dict_targets[alias] 
        if target["guide"]:
            target_id = dict_id_name[target["alias"]][0][0]
            query = "SELECT unit_id, gear_reco FROM guild_team_roster " \
                    "JOIN guild_subteams ON guild_team_roster.subteam_id = guild_subteams.id " \
                    "JOIN guild_teams ON guild_subteams.team_id = guild_teams.id " \
                    "WHERE guild_teams.name='"+target_id+"-GV' "
            goutils.log2("DBG", query)
            results = connect_mysql.get_table(query)

            if results == None:
                target_name = dict_units[target_id]["name"]
                return 1, "Guide de voyage non défini pour "+target_name, None

            for line in results:
                unit_id = line[0]
                unit_name = dict_units[unit_id]["name"]
                if line[1]=='':
                    #ship
                    pass
                elif line[1][0].lower() == "g":
                    target_gear = int(line[1][1:])
                    target_relic = 0
                    list_display_targets.append(unit_name+" au niveau G"+str(target_gear))
                elif line[1][0].lower() == "r":
                    target_gear = 13
                    target_relic = int(line[1][1:])
                    list_display_targets.append(unit_name+" au niveau R"+str(target_relic))
                else:
                    # number without prefix > gear
                    target_gear = int(line[1])
                    target_relic = 0
                    list_display_targets.append(unit_name+" au niveau G"+str(target_gear))

                unit = {"defId": unit_id,
                        "gear": target_gear,
                        "relic": target_relic}

                list_units.append(unit)
        else:
            unit_id = dict_id_name[target["alias"]][0][0]
            unit_name = dict_units[unit_id]["name"]
            unit = {"defId": unit_id,
                    "gear": target["gear"],
                    "relic": target["relic"]}

            if target["relic"] > 0:
                list_display_targets.append(unit_name+" au niveau R"+str(target["relic"]))
            else:
                list_display_targets.append(unit_name+" au niveau G"+str(target["gear"]))

            list_units.append(unit)

    # Get regular player data
    if dict_player==None:
        ec, et, d_player = await go.load_player(allyCode, 1, False)
        if ec != 0:
            return 1, et, None
    else:
        d_player = dict_player

    # Get equipment dict
    ec, et, needed_eqpt = go.get_needed_eqpt(d_player, list_units)

    # Test if there is something to display
    if len(needed_eqpt) == 0:
        return 1, "Aucun équipement nécessaire pour passer "+str(", ".join(list_display_targets))+" (les persos sont déjà à niveau)", None

    # Get owned equipment, ONLY for connected users
    player_eqpt = {}
    if check_owned:
        # Connected user, get full player data
        if initialdata_player==None:
            ec, et, i_player = await connect_rpc.get_player_initialdata(allyCode)
            if ec != 0:
                return 1, et, None
        else:
            i_player = initialdata_player

        #create list of owned equipment
        player_eqpt = {}
        for e in i_player["inventory"]["equipment"]:
            player_eqpt[e["id"]] = e["quantity"]
        for e in i_player["inventory"]["material"]:
            player_eqpt[e["id"]] = e["quantity"]

    # Loop from high level eqpt, check if owned
    #  then breakdown into next level, chck if owned
    #  loop...
    initial_player_eqpt = dict(player_eqpt)
    continue_loop = True
    needed_owned_eqpt = {}
    while(continue_loop):
        for eqpt_id in needed_eqpt:
            if eqpt_id in player_eqpt:
                #Store player amount for later display
                if player_eqpt[eqpt_id] > needed_eqpt[eqpt_id]:
                    if not eqpt_id in needed_owned_eqpt:
                        needed_owned_eqpt[eqpt_id] = 0
                    needed_owned_eqpt[eqpt_id] += needed_eqpt[eqpt_id]
                    player_eqpt[eqpt_id] -= needed_eqpt[eqpt_id]
                    needed_eqpt[eqpt_id] = 0
                else:
                    if not eqpt_id in needed_owned_eqpt:
                        needed_owned_eqpt[eqpt_id] = 0
                    needed_owned_eqpt[eqpt_id] += player_eqpt[eqpt_id]
                    needed_eqpt[eqpt_id] -= player_eqpt[eqpt_id]
                    player_eqpt[eqpt_id] = 0

        #Now that all has been checked, breakdown remaining needed one level
        needed_eqpt, continue_loop = go.breakdown_to_farmable_eqpt(needed_eqpt, one_level=True)

    # Transform into list
    eqpt_list = []
    list_eqpt_id = set(list(needed_eqpt.keys())+list(needed_owned_eqpt.keys()))
    still_needed_eqpt = needed_eqpt
    for k in list_eqpt_id:
        if k == 'GRIND':
            continue

        if k in still_needed_eqpt:
            still_needed = still_needed_eqpt[k]
        else:
            still_needed = 0
        if still_needed == 0:
            continue

        if k in needed_owned_eqpt:
            needed_owned = needed_owned_eqpt[k]
            total_owned = initial_player_eqpt[k]
        else:
            needed_owned = 0
            total_owned = 0
        eqpt_list.append([k, still_needed+needed_owned, total_owned])

    return 0, "",  {"eqpt_list": eqpt_list, "targets": list_display_targets}

##############################################################
async def tpg(ctx_interaction, *args):
    try:
        resp_msg = await command_ack(ctx_interaction)

        #Check arguments
        args = list(args)
        tw_mode = False
        tb_mode = False
        guild_id = None

        if "-TW" in args:
            #Ensure command is launched from a server, not a DM
            if commands_check.dm(ctx_interaction, "L'option -TW"):
                return

            tw_mode = True
            args.remove("-TW")

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx_interaction.guild.id, ctx_interaction.message.channel.id)
            if ec!=0:
                await command_error(ctx_interaction, resp_msg, "ERR: vous devez avoir un warbot pour utiliser l'option -TW")
                return

            guild_id = bot_infos["guild_id"]

        if "-TB" in args:
            if tw_mode:
                await command_error(ctx_interaction, resp_msg, "ERR: impossible d'utiliser les options -TW et -TB en même temps")
                return

            #Ensure command is launched from a server, not a DM
            #Ensure command is launched from a server, not a DM
            if commands_check.dm(ctx_interaction, "L'option -TB"):
                return

            tb_mode = True
            args.remove("-TB")

            #get bot config from DB
            ec, et, bot_infos = connect_mysql.get_warbot_info(ctx_interaction.guild.id, ctx_interaction.message.channel.id)
            if ec!=0:
                await command_error(ctx_interaction, resp_msg, "ERR: vous devez avoir un warbot pour utiliser l'option -TB")
                return

            guild_id = bot_infos["guild_id"]

        ec, et, ret = get_channel_from_args(arg)
        if ec!=0:
            await command_error(ctx_interaction, resp_msg, et)
            return

        args = ret["args"]
        display_mentions = ret["display_mentions"]
        output_channel = ret["output_channel"]

        if len(args) >= 2:
            allyCode = args[0]
            character_list = [x.split(' ') for x in [y.strip() for y in " ".join(args[1:]).split('/')]]
        else:
            await command_error(ctx_interaction, resp_msg, "ERR: commande mal formulée. Veuillez consulter l'aide avec go.help tpg")
            return

        ec, et, allyCode = await manage_me(ctx_interaction, allyCode, False)
        if ec!=0:
            await command_error(ctx_interaction, resp_msg, et)
            return

        err, errtxt, list_list_ids = await go.tag_players_with_character(allyCode, character_list,
                                                                         guild_id, tw_mode, tb_mode,
                                                                         display_mentions)
        if err != 0:
            await command_error(ctx_interaction, resp_msg, errtxt)
            return

        for list_ids in list_list_ids:
            intro_txt = list_ids[0]
            if len(list_ids) > 1:
                await send_message(ctx_interaction, intro_txt +" :\n" +' / '.join(list_ids[1:])+"\n--> "+str(len(list_ids)-1)+" joueur(s)")
            else:
                await send_message(ctx_interaction, intro_txt +" : aucun joueur")

        await command_ok(ctx_interaction, resp_msg, "Commande terminée")

    except Exception as e:
        goutils.log2("ERR", traceback.format_exc())
        await command_error(ctx_interaction, resp_msg, "erreur inconnue")

##############################################################
# Function: manage_me
# IN (string): alias > me / -TW / @mention / allyCode / in-game name / discord name
# OUT (string): find the allyCode from the alias
##############################################################
async def manage_me(ctx_interaction, alias, allow_tw=True):
    #Special case of 'me' as allyCode
    if alias == 'me':
        dict_players_by_ID = connect_mysql.load_config_players()[1]
        if type(ctx_interaction) == commands.Context:
            user_id = ctx_interaction.author.id
        else: # Interaction
            user_id = ctx_interaction.user.id

        if user_id in dict_players_by_ID:
            ret_allyCode_txt = str(dict_players_by_ID[user_id]["main"][0])
        else:
            ret_allyCode_txt = "ERR: \"me\" (<@"+str(user_id)+">) n'est pas enregistré dans le bot. Utiliser la comande `go.register <code allié>`"
    elif alias == "-TW":
        if not allow_tw:
            return 1, "ERR: l'option -TW n'est pas utilisable avec cette commande", None

        #Ensure command is launched from a server, not a DM
        if ctx_interaction.guild == None:
            return 1, "ERR: commande non autorisée depuis un DM avec l'option -TW", None

        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_warbot_info(ctx_interaction.guild.id, ctx_interaction.message.channel.id)
        if ec!=0:
            return ec, et, None

        guild_id = bot_infos["guild_id"]

        #Launch the actuel search
        ec, et, allyCode = await connect_rpc.get_tw_opponent_leader(guild_id)
        if ec != 0:
            return ec, "ERR: "+et, None

        ret_allyCode_txt = allyCode

    elif alias.startswith('<@'):
        # discord @mention
        if alias.startswith('<@!'):
            discord_id = int(alias[3:-1])
        else: # '<@ without the !
            discord_id = int(alias[2:-1])
        goutils.log2("INFO", "command launched with discord @mention "+alias)
        dict_players_by_ID = connect_mysql.load_config_players()[1]
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
        # Look for the name among known player names
        results = connect_mysql.get_table("SELECT name, allyCode FROM players WHERE NOT isnull(name)")
        list_names = [x[0] for x in results]
        closest_names_db=difflib.get_close_matches(alias, list_names, 1)
        if len(closest_names_db) == 0:
            closest_name_db = ""
            closest_name_db_score = 0
        else:
            closest_name_db = closest_names_db[0]
            closest_name_db_score = difflib.SequenceMatcher(None, alias, closest_name_db).ratio()

        #check among discord names
        if ctx_interaction != None and ctx_interaction.guild != None and (closest_name_db != alias):
            #Remove text in [] and in ()
            guild_members_clean = [[x.id, re.sub(r'\([^)]*\)', '',
                                    re.sub(r'\[[^)]*\]', '',x.display_name)).strip()]
                                    for x in ctx_interaction.guild.members]
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

            discord_id = [x[0] for x in guild_members_clean if x[1] == closest_name_discord][0]
            dict_players_by_ID = connect_mysql.load_config_players()[1]
            if discord_id in dict_players_by_ID:
                ret_allyCode_txt = str(dict_players_by_ID[discord_id]["main"][0])
            else:
                goutils.log2("ERR", alias + " ne fait pas partie des joueurs enregistrés")
                ret_allyCode_txt = 'ERR: '+alias+' ne fait pas partie des joueurs enregistrés'

    
    goutils.log2("DBG", ret_allyCode_txt)
    return 0, "", ret_allyCode_txt

###########################################################
async def get_channel_from_args(ctx_interaction, args):
    for arg in args:
        if arg.startswith('<#'):
            id_output_channel = int(channel_name[2:-1])
            output_channel = bot.get_channel(id_output_channel)

            if output_channel == None:
                return 1, "Channel " + arg + "(id=" + str(id_output_channel) + ") introuvable", \
                          {"args": args.remove(arg),
                           "output_channel": None,
                           "display_mentions": False}

            if not output_channel.permissions_for(ctx_interaction.me).send_messages:
                return 1, 'Il manque les droits d\'écriture dans ' + channel_name, \
                          {"args": args.remove(arg),
                           "output_channel": None,
                           "display_mentions": False}
            
            display_mentions = officer(ctx_interaction)
            return 0, "", {"args": args.remove(arg), 
                           "output_channel": output_channel,
                           "display_mentions": True}
                    
    # If we reach this point, it means no channel was in the arguments
    return 0, "", {"args": args,
                   "output_channel": ctx_interaction.message.channel,
                   "display_mentions": False}

###################################################
async def register(ctx_interaction, args):
    try:
        resp_msg = await command_ack(ctx_interaction)

        if len(args)==0:
            await command_error(ctx_interaction, resp_msg, "ERR: merci de renseigner un code allié")
            return

        ac = args[0]

        if re.match("[0-9]{3}-[0-9]{3}-[0-9]{3}", ac) != None:
            # 123-456-789 >> allyCode
            allyCode = ac.replace("-", "")

        elif ac.isnumeric():
            # number >> allyCode
            allyCode = ac

        else:
            await command_error(ctx_interaction, resp_msg, "ERR: merci de renseigner un code allié")
            return

        #Registration of the allyCode to a discord ID
        if len(args) == 1:
            #registering allyCOde to self
            discord_id_txt = str(ctx_interaction.author.id)

        elif len(args) == 2 and args[1]=="confirm":
            # Specific mode, not used to register an allyCode, but
            #  to confirm that the user is actually controlling that allyCode

            #Ensure command is launched from a DM, not a server
            if ctx_interaction.guild != None:
                await command_error(ctx_interaction, resp_msg, "Pour des raisons de confidentialité, cette commande doit être envoyée en message privé au bot.")
                return

            #Launch or get the challenge
            code, txt = await go.register_confirm(allyCode, ctx_interaction.author.id)

            if code==1:
                await command_error(ctx_interaction, resp_msg, txt)
            elif code==2:
                await command_ok(ctx_interaction, resp_msg, txt)
            else: #code==0
                await command_ok(ctx_interaction, resp_msg, txt)

            return

        elif len(args) == 2:
            mention = args[1]

            if mention.startswith('<@'):
                # discord @mention
                if mention.startswith('<@!'):
                    discord_id_txt = mention[3:-1]
                else: # '<@ without the !
                    discord_id_txt = mention[2:-1]
                goutils.log2("INFO", "command launched with discord @mention "+mention)
        else:
            await command_error(ctx_interaction, resp_msg, "ERR: commande mal formulée. Veuillez consulter l'aide avec go.help register")

        #Ensure the allyCode is registered in DB
        e, t, dict_player = await go.load_player(allyCode, -1, False)
        if e != 0:
            await command_error(ctx_interaction, resp_msg, t)
            return

        player_name = dict_player["name"]

        #Setup all potential previous accounts as alt
        query = "UPDATE player_discord SET main=0 WHERE discord_id='"+discord_id_txt+"'"
        goutils.log2("INFO", query)
        connect_mysql.simple_execute(query)

        #Add discord id in DB
        query = "INSERT INTO player_discord (allyCode, discord_id)\n"
        query+= "VALUES("+allyCode+", "+discord_id_txt+") \n"
        query+= "ON DUPLICATE KEY UPDATE discord_id="+discord_id_txt+",main=1"
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

        #Ensure that any discord_id has a main account
        query = "UPDATE player_discord SET main=1 "\
                "WHERE discord_id IN ( "\
                "SELECT discord_id "\
                "FROM player_discord "\
                "GROUP BY discord_id "\
                "HAVING max(main)=0 "\
                ")"
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

        await command_ok(ctx_interaction, resp_msg, "Enregistrement de "+player_name+" réussi > lié au compte <@"+discord_id_txt+">")

    except Exception as e:
        goutils.log2("ERR", traceback.format_exc())

async def tb_rare_toons(ctx_interaction, guild_ac, list_zones, filter_player_ac_txt=None):
    resp_msg = await command_ack(ctx_interaction)

    ec, et, guild_ac = await manage_me(ctx_interaction, guild_ac, allow_tw=False)
    if ec!=0:
        await command_error(ctx_interaction, resp_msg, et)
        return

    if filter_player_ac_txt != None:
        ec, et, filter_player_ac_txt = await manage_me(ctx_interaction, filter_player_ac_txt, allow_tw=False)
        if ec!=0:
            await command_error(ctx_interaction, resp_msg, et)
            return

    # Get list of platoons from SWGOH wiki
    ec, et, dict_ops = connect_gsheets.read_rote_operations(list_zones)
    if ec!=0:
        await command_error(ctx_interaction, resp_msg, et)
        return

    # Get list of allyCodes from guild
    query = "SELECT allyCode "\
            "FROM players "\
            "WHERE guildId=(SELECT guildId FROM players WHERE allyCode="+guild_ac+") "\
            "AND guildId!='' "
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_column(query)
    if db_data==None:
        await command_error(ctx_interaction, resp_msg, guild_ac+" n'est dans aucune guilde")
        return
    list_guild_ac = db_data

    # Get list of toons from guild
    query = "SELECT players.name, defId, relic_currentTier "\
            "FROM roster "\
            "JOIN players ON players.allyCode=roster.allyCode "\
            "WHERE guildId=(SELECT guildId FROM players WHERE allyCode="+guild_ac+") "\
            "AND rarity=7 "\
            "AND defId IN "+str(tuple(dict_ops.keys()))
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_table(query)
    d_guild = {}
    d_players = {}
    for l in db_data:
        ac = l[0]
        defId = l[1]
        relic = max(l[2]-2, 0)

        if not ac in d_players:
            d_players[ac] = {}
        d_players[ac][defId]=relic

        if not defId in d_guild:
            d_guild[defId] = {}
        if not relic in d_guild[defId]:
            d_guild[defId][relic] = 0
        d_guild[defId][relic] += 1

    #get rare toons
    d_rares = {}
    for unit in dict_ops:
        for relic in dict_ops[unit]:
            req = dict_ops[unit][relic]
            guild = 0
            for g_relic in d_guild[unit]:
                if g_relic >= relic:
                    guild += d_guild[unit][g_relic]
            if (guild-req) < 2 and relic<9:
                #print(unit, dict_ops[unit], d_guild[unit])
                d_rares[unit+":"+str(relic)]=[req, guild]

    if filter_player_ac_txt == None:
        #No filter player, list rare toons of the guild
        list_rares = [["Unit", "Needed", "Owned"]]
        list_colors=["black"]
        for u in sorted(d_rares.keys()):
            list_rares.append([u, d_rares[u][0], d_rares[u][1]])
            if d_rares[u][0] > d_rares[u][1]:
                list_colors.append("orange")
            else:
                list_colors.append("black")

        t = Texttable(0)
        t.add_rows(list_rares)
        t.set_deco(0)
        ec, et, image = portraits.get_image_from_texttable(t.draw(), line_colors=list_colors)

        zones_txt = "ROTE"
        if list_zones!=[]:
            zones_txt = str(list_zones)
        await command_ok(ctx_interaction, resp_msg, "Liste des toons rares pour "+zones_txt, images=[image])

    else:
        #filter player is given, list rare toons of this player
        ec, et, d_player = await go.load_player(filter_player_ac_txt, 1, False)
        if ec != 0:
            await command_error(ctx_interaction, resp_msg, et)

        filter_player_ac = int(filter_player_ac_txt)
        filter_player_name = d_player["name"]
        list_rares = [["Unit", "Needed", "Owned"]]
        list_u_rares = []
        list_colors=["black"]
        if filter_player_ac in list_guild_ac:
            # player is part of the guild
            for u in d_rares:
                uid = u.split(':')[0]
                if uid in list_u_rares:
                    continue
                list_u_rares.append(uid)
                urelic = int(u.split(':')[1])
                if uid in d_players[filter_player_name] and urelic>0:
                    p_relic = d_players[filter_player_name][uid]
                    if p_relic>=urelic:
                        list_rares.append([u, d_rares[u][0], d_rares[u][1]])
                        if d_rares[u][1] == 1:
                            list_colors.append("orange")
                            #print(filter_player_name+" est le seul à avoir "+uid+":R"+str(p_relic))
                        else:
                            list_colors.append("black")
                            #print(filter_player_name+" a le toon rare "+uid+":R"+str(p_relic))

        else:
            # filter_player is not in the guild
            for u in d_rares:
                uid = u.split(':')[0]
                if uid in list_u_rares:
                    continue
                list_u_rares.append(uid)
                urelic = int(u.split(':')[1])
                if uid in d_player["rosterUnit"] and urelic>0:
                    p_relic = d_player["rosterUnit"][uid]["relic"]["currentTier"]-2
                    if p_relic>=urelic:
                        list_rares.append([u, d_rares[u][0], d_rares[u][1]])
                        if d_rares[u][1] == 0:
                            list_colors.append("green")
                            #print(filter_player_name+" a toon qui manque "+uid+":R"+str(p_relic))
                        else:
                            list_colors.append("black")
                            #print(filter_player_name+" a le toon rare "+uid+":R"+str(p_relic))
        print(list_rares)
        t = Texttable(0)
        t.add_rows(list_rares)
        t.set_deco(0)
        ec, et, image = portraits.get_image_from_texttable(t.draw(), line_colors=list_colors)

        zones_txt = "ROTE"
        if list_zones!=[]:
            zones_txt = str(list_zones)
        await command_ok(ctx_interaction, resp_msg, "Liste des toons rares de "+filter_player_name+" pour "+zones_txt, images=[image])

###############################
async def upgrade_mod_level(ctx_interaction, target_level, simulation, only_speed_sec, with_inventory, connected_allyCode=None):
    resp_msg = await command_ack(ctx_interaction)

    if connected_allyCode == None:
        channel_id = ctx_interaction.channel_id

        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_google_player_info(channel_id)
        if ec!=0:
            await command_error(ctx_interaction, resp_msg, et)
            return
    
        txt_allyCode = str(bot_infos["allyCode"])
    else:
        txt_allyCode = connected_allyCode

    goutils.log2("INFO", "mods.upgrade_mod_level_up("+txt_allyCode+")")

    #Get player data
    ec, et, dict_player = await go.load_player(txt_allyCode, 1, False)
    if ec!=0:
        await command_error(ctx_interaction, resp_msg, et)
        return

    if with_inventory:
        ec, et, initialdata = await connect_rpc.get_player_initialdata(txt_allyCode)
        if ec!=0:
            await command_error(ctx_interaction, resp_msg, et)
            return
    else:
        initialdata = None

    #Get player mods
    dict_player_mods = manage_mods.get_dict_player_mods(
                            dict_player,
                            initialdata = initialdata)

    #Run the function
    ec, et = await manage_mods.upgrade_roster_mods(
                      dict_player_mods,
                      target_level,
                      txt_allyCode,
                      is_simu=simulation,
                      only_speed_sec=only_speed_sec)

    if ec != 0:
        await command_error(ctx_interaction, resp_msg, et)
        return

    await command_ok(ctx_interaction, resp_msg, et)

###############################
async def deploy_tb(ctx_interaction, zone, list_alias_txt):
    resp_msg = await command_ack(ctx_interaction)

    if type(ctx_interaction) == Interaction:
        channel_id = ctx_interaction.channel_id
    else: #Context
        channel_id = ctx_interaction.message.channel.id

    #get bot or player config from DB
    ec, et, bot_infos = connect_mysql.get_warbot_info(ctx_interaction.guild.id, channel_id)
    if ec!=0:
        await command_error(ctx_interaction, resp_msg, "ERR: vous devez avoir un warbot ou une connexion EA pour utiliser cette commande")
        return

    guild_id = bot_infos["guild_id"]
    txt_allyCode = str(bot_infos["allyCode"])

    goutils.log2("INFO", "bt.déploie("+txt_allyCode+")")

    #Run the function
    ec, et = await go.deploy_tb(guild_id, txt_allyCode, zone, list_alias_txt)

    if ec != 0:
        await command_error(ctx_interaction, resp_msg, et)
        return

    await command_ok(ctx_interaction, resp_msg, et)

#######################################"
async def allocate_random_mods(ctx_interaction):
    resp_msg = await command_ack(ctx_interaction)

    if connected_allyCode == None:
        channel_id = ctx_interaction.channel_id

        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_google_player_info(channel_id)
        if ec!=0:
            await command_error(ctx_interaction, resp_msg, et)
            return
    
        txt_allyCode = str(bot_infos["allyCode"])
    else:
        txt_allyCode = connected_allyCode

    goutils.log2("INFO", "mods.allocate_random_mods("+txt_allyCode+")")

    #Get player data
    ec, et, dict_player = await go.load_player(txt_allyCode, 1, False)
    if ec!=0:
        await command_error(ctx_interaction, resp_msg, et)
        return

    ec, et, initialdata = await connect_rpc.get_player_initialdata(txt_allyCode)
    if ec!=0:
        await command_error(ctx_interaction, resp_msg, et)
        return

    #Get mod allocations
    ec, et, mod_allocations = await manage_mods.alocate_mods_to_empty_slots(
                                        txt_allyCode,
                                        initialdata=initialdata)
    if ec!=0:
        await command_error(ctx_interaction, resp_msg, et)
        return

    #Apply mod allocations
    ec, et, ret_data = await manage_mods.apply_mod_allocations(
                            mod_allocations,
                            txt_allyCode,
                            True, #Simu=True [TEMPORARY for TESTS]
                            ctx_interaction,
                            initialdata=initialdata)
    if ec!=0:
        await command_error(ctx_interaction, resp_msg, et)
        return

    ret_txt = emojis.check+" "+ret_data["cost"]
    await command_ok(ctx_interaction, resp_msg, ret_txt)

    return

