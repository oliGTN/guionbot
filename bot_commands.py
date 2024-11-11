# PACKAGE imports
from discord.ext import tasks, commands
from discord import Activity, ActivityType, Intents, File, DMChannel, errors as discorderrors
from discord import app_commands, Interaction
from io import BytesIO
import re
import difflib
import sys
import traceback

# BOT imports
import go
import connect_rpc
import connect_mysql
import goutils
import portraits
import data

# CONSTANTS
import emojis
MAX_MSG_SIZE = 1900 #keep some margin for extra formating characters

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
        await ctx_interaction.message.channel.send(content=content, attachments=attachments)

    else:
        print(content)

        for attachment in attachments:
            print(attachment)



##############################################################
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
async def farmeqpt(ctx_interaction, allyCode, list_alias_gear):
    try:
        dict_units = data.get("unitsList_dict.json")

        resp_msg = await command_ack(ctx_interaction)

        ec, et, allyCode = await manage_me(ctx_interaction, allyCode)
        if ec!=0:
            await command_error(ctx_interaction, resp_msg, et)
            return

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
                            await command_error(ctx_interaction, resp_msg, "Syntax incorrecte pour le gear/relic dans "+alias)
                            return

                    elif tab_alias[1][0].lower() == "r" and tab_alias[1][1:].isnumeric():
                        target_gear = 13
                        target_relic = int(tab_alias[1][1:])

                        if target_relic<0 or target_relic>9:
                            await command_error(ctx_interaction, resp_msg, "Syntax incorrecte pour le gear/relic dans "+alias)
                            return

                    else:
                        await command_error(ctx_interaction, resp_msg, "Syntax incorrecte pour le gear/relic dans "+alias)
                        return

            else: #2 ":" or more
                await command_error(ctx_interaction, resp_msg, "Syntax incorrecte pour le gear/relic dans "+alias)
                return

            list_unit_names.append(target_alias)

            dict_targets[alias] = {"alias": target_alias,
                                   "gear": target_gear,
                                   "relic": target_relic,
                                   "guide": target_guide}


        #Get unit IDs from aliases
        list_unit_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_unit_names)
        if txt != '':
            await command_error(ctx_interaction, resp_msg, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt)
            return

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
                    await command_error(ctx_interaction, resp_msg, "Guide de voyage non défini pour "+target_name)
                    return

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
        ec, et, d_player = await go.load_player(allyCode, 1, False)
        if ec != 0:
            await command_error(ctx_interaction, resp_msg, et)
            return

        # Get equipment dict
        ec, et, eqpt = go.get_needed_eqpt(d_player, list_units)

        # Test if there is something to display
        if len(eqpt) == 0:
            await command_ok(ctx_interaction, resp_msg, "Aucun équipement nécessaire pour passer "+str(", ".join(list_display_targets))+" (les persos sont déjà à niveau)")
            return

        player_eqpt = {}
        display_owned = False

        # Get owned equipment, ONLY for connected users
        if ctx_interaction != None:
            ec, et, player_infos = connect_mysql.get_google_player_info(ctx_interaction.channel.id)
            if ec==0:
                # Connected user, get full player data
                ec, et, i_player = await connect_rpc.get_player_initialdata(allyCode)
                if ec != 0:
                    await command_error(ctx_interaction, resp_msg, et)
                    return

                #create list of owned equipment
                player_eqpt = {}
                for e in i_player["inventory"]["equipment"]:
                    player_eqpt[e["id"]] = e["quantity"]
                for e in i_player["inventory"]["material"]:
                    player_eqpt[e["id"]] = e["quantity"]

                display_owned = True

        # Transform into list
        eqpt_list = []
        for k in eqpt:
            if k == "GRIND":
                continue
            if k in player_eqpt:
                owned = player_eqpt[k]
            else:
                owned = 0
            eqpt_list.append([k, eqpt[k], owned])

        # Sort with most needed first
        eqpt_list.sort(key=lambda x:x[2]-x[1])

        # Test if there is something to display
        if eqpt_list[0][2] >= eqpt_list[0][1]:
            await command_ok(ctx_interaction, resp_msg, "Tous les équipements nécessaires pour passer "+str(", ".join(list_display_targets))+" sont déjà disponibles")
            return

        # Compute image
        image = portraits.get_image_from_eqpt_list(eqpt_list, display_owned=display_owned)

        # Display the image
        await command_ok(ctx_interaction, resp_msg, "Liste des équipements nécessaires pour passer "+str(", ".join(list_display_targets)), images=[image])

    except Exception as e:
        goutils.log2("ERR", str(sys.exc_info()[0]))
        goutils.log2("ERR", e)
        goutils.log2("ERR", traceback.format_exc())

##############################################################
async def tpg(ctx_interaction, *args):
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

