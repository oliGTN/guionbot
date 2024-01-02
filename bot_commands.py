# PACKAGE imports
from discord.ext import tasks, commands
from discord import Activity, ActivityType, Intents, File, DMChannel, errors as discorderrors
from discord import app_commands, Interaction
from io import BytesIO

# BOT imports
import go
import connect_mysql
import goutils

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
        ctx = ctx_interaction
        if intermediate:
            content = emojis.hourglass+" "+output_txt
        else:
            content = emojis.check+" "+output_txt

        await resp_msg.edit(content=content, attachments=attachments)

    elif type(ctx_interaction) == Interaction:
        interaction = ctx_interaction
        if intermediate:
            content = emojis.hourglass+" "+output_txt
        else:
            content = emojis.check+" "+output_txt

        await interaction.edit_original_response(content=content, attachments=attachments)

    else:
        if intermediate:
            content = "OK "+output_txt
        else:
            content = "In Progress... "+output_txt

        print(content)

        for attachment in attachments:
            print(attachment)


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


##############################################################
async def gdp(ctx_interaction, allyCode):
    resp_msg = await command_ack(ctx_interaction)

    allyCode = await manage_me(ctx_interaction, allyCode, allow_tw=True)
    if allyCode[0:3] == 'ERR':
        await command_error(ctx_interaction, resp_msg, allyCode)
        return

    # Display the chart
    e, err_txt, image = await go.get_gp_distribution(allyCode)
    if e != 0:
        await command_error(ctx_interaction, resp_msg, err_txt)
        return

    await command_ok(ctx_interaction, resp_msg, "chargement des joueurs en cours", images=[image], intermediate=True)

    # Now load all players from the guild
    await go.load_guild( allyCode, True, True)

    #Icône de confirmation de fin de commande dans le message d'origine
    await command_intermediate_to_ok(ctx_interaction, resp_msg, new_txt="chargement des joueurs OK")

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

        print(user_id)
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

