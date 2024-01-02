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
    if type(ctx_interaction) == commands.Context:
        ctx = ctx_interaction
        await ctx.message.add_reaction(emojis.thumb)

    elif type(ctx_interaction) == Interaction:
        interaction = ctx_interaction
        await interaction.response.defer(thinking=True)
    else:
        print("In progress...")

async def command_ok(ctx_interaction, output_txt, images=None, files=None, intermediate=False):
    attachments = []

    if images != None:
        for image in images:
            with BytesIO() as image_binary:
                image.save(image_binary, 'PNG')
                image_binary.seek(0)
                attachments.append(File(fp=image_binary, filename='image.png'))

    if files != None:
        attachments += files

    answer_messages = None

    if type(ctx_interaction) == commands.Context:
        ctx = ctx_interaction
        if intermediate:
            await ctx.message.add_reaction(emojis.hourglass)
        else:
            await ctx.message.add_reaction(emojis.check)

        answer_messages = []
        for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
            msg = await ctx.send(txt, files=attachments)
            answer_messages.append(msg)

    elif type(ctx_interaction) == Interaction:
        interaction = ctx_interaction
        if intermediate:
            txt = emojis.hourglass+" "+output_txt
        else:
            txt = emojis.check+" "+output_txt

        await interaction.edit_original_response(content=txt, attachments=attachments)

    else:
        print("Command OK")
        print(output_txt)

        for attachment in attachments:
            print(attachment)

    return answer_messages

async def command_intermediate_to_ok(ctx_interaction, answer_messages=None, new_txt=None):
    if type(ctx_interaction) == commands.Context:
        ctx = ctx_interaction
        await ctx.message.remove_reaction(emojis.hourglass, ctx.me)
        await ctx.message.add_reaction(emojis.check)

        if new_txt != None:
            await answer_messages[0].edit(content=new_txt)

    elif type(ctx_interaction) == Interaction:
        interaction = ctx_interaction
        if new_txt == None:
            new_content = interaction.message.content.replace(emojis.hourglass, emojis.check)
        else:
            new_content = emojis.check+" "+new_txt
        await interaction.edit_original_response(content=new_content)

    else:
        print("Command OK")

async def command_error(ctx_interaction, err_txt):
    if type(ctx_interaction) == commands.Context:
        ctx = ctx_interaction
        await ctx.message.add_reaction(emojis.redcross)
        await ctx.send(err_txt)

    elif type(ctx_interaction) == Interaction:
        interaction = ctx_interaction
        txt = emojis.redcross+" "+err_txt
        await interaction.edit_original_response(content=txt)

    else:
        print("ERROR")
        print(err_txt)

async def gdp(ctx_interaction, allyCode):
    await command_ack(ctx_interaction)

    allyCode = await manage_me(ctx_interaction, allyCode, allow_tw=True)
    if allyCode[0:3] == 'ERR':
        await command_error(ctx_interaction, allyCode)
        return

    # Display the chart
    e, err_txt, image = await go.get_gp_distribution(allyCode)
    if e != 0:
        await command_error(ctx_interaction, err_txt)
        return

    answer_messages = await command_ok(ctx_interaction, "chargement des joueurs en cours", images=[image], intermediate=True)

    # Now load all players from the guild
    await go.load_guild( allyCode, True, True)

    #Icône de confirmation de fin de commande dans le message d'origine
    await command_intermediate_to_ok(ctx_interaction, answer_messages=answer_messages,
                                     new_txt="chargement des joueurs OK")

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
            return "ERR: l'option -TW n'est pas utilisable avec cette commande"

        #Ensure command is launched from a server, not a DM
        if ctx_interaction.guild == None:
            return "ERR: commande non autorisée depuis un DM avec l'option -TW"

        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_warbot_info(ctx_interaction.guild.id, ctx_interaction.message.channel.id)
        if ec!=0:
            await ctx_interaction.send('ERR: '+et)
            await ctx_interaction.message.add_reaction(emojis.redcross)
            return

        guild_id = bot_infos["guild_id"]

        #Launch the actuel search
        ec, et, allyCode = await connect_rpc.get_tw_opponent_leader(guild_id)
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

    
    return ret_allyCode_txt
