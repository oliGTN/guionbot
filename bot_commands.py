import emojis

async def command_ack(ctx_interaction):
    if type(ctx) == discord.ext.commands.Context:
        await ctx_interaction.message.add_reaction(emojis.thumb)
    elif type(ctx) == discord.Interaction:
        await ctx_interaction.response.defer(thinking=True)
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

    if type(ctx_interaction) == discord.ext.commands.Context:
        ctx = ctx_interaction
        if intermediate:
            await ctx.message.add_reaction(emoji.hourglass)
        else:
            await ctx.message.remove_reaction(emoji_hourglass, ctx.me)
            await ctx.message.add_reaction(emoji.check)

        for txt in goutils.split_txt(output_txt, MAX_MSG_SIZE):
            await ctx.send(txt, files=attachments)

    elif type(ctx_interaction) == discord.Interaction:
        interaction = ctx_interaction
        if intermediate:
            txt = emojis.hourglass+" "+text
        else:
            txt = emojis.check+" "+text

        await interaction.edit_original_response(content=txt, attachments=attachments)

    else:
        print("Command OK")
        print(text)

        for attachment in attachments:
            print(attachment)


async def command_error(ctx_interaction, err_txt):
    if type(ctx) == discord.ext.commands.Context:
        await ctx_interaction.message.add_reaction(emoji.redcross)
        await ctx.send(err_txt)

    elif type(ctx) == discord.Interaction:
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

        await command_ok(ctx_interaction, "", images=[image], intermediate=True)

        # Now load all players from the guild
        await go.load_guild( allyCode, True, True)

        #Icône de confirmation de fin de commande dans le message d'origine
        await command_ok(ctx_interaction, "", images=[image])

##############################################################
# Function: manage_me
# IN (string): alias > me / -TW / @mention / allyCode / in-game name / discord name
# OUT (string): find the allyCode from the alias
##############################################################
async def manage_me(ctx_interaction, alias, allow_tw=True):
    #Special case of 'me' as allyCode
    if alias == 'me':
        dict_players_by_ID = connect_mysql.load_config_players()[1]
        #print(dict_players_by_ID)
        if ctx_interaction.author.id in dict_players_by_ID:
            ret_allyCode_txt = str(dict_players_by_ID[ctx_interaction.author.id]["main"][0])
        else:
            ret_allyCode_txt = "ERR: \"me\" (<@"+str(ctx_interaction.author.id)+">) n'est pas enregistré dans le bot. Utiliser la comande `go.register <code allié>`"
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
            await ctx_interaction.message.add_reaction(emoji_error)
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
