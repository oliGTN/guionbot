import config

def _user(ctx_interaction):
    if type(ctx_interaction) == commands.Context:
        ctx = ctx_interaction
        user = ctx.author
    else: # Interaction
        interaction = ctx_interaction
        user = interaction.user

    return user

def admin(ctx_interaction):
    is_bot_admin = str(_user(ctx_interaction).id) in config.GO_ADMIN_IDS.split(' ')
    if not is_bot_admin:
        bot_commands.command_error(ctx_interaction, "Commande réservée aux admins")
        return False

    return True

def officer(ctx_interaction):
    is_bot_admin = str(_user(ctx_interaction).id) in config.GO_ADMIN_IDS.split(' ')

    is_officer = False
    is_server_admin = False

    if ctx_interaction.guild != None:
        # Can be an officer only if in a discord server, not in a DM
        #get bot config from DB
        ec, et, bot_infos = connect_mysql.get_warbot_info(ctx_interaction.guild.id, 
                                                          ctx_interaction.message.channel.id)
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

            if _user(ctx_interaction).id in list_did:
                is_officer = True
        else:
            goutils.log2("DBG", et)


        # Can have the rights if server admin
        is_server_admin = _user(ctx_interaction).guild_permissions.administrator

    goutils.log2("INFO", [ctx.author.name, is_bot_admin, is_officer, is_server_admin])

    is_allowed = ((is_officer or is_server_admin) and (not bot_test_mode)) or is_bot_admin

    if not is_allowed:
        bot_commands.command_error(ctx_interaction, "Commande réservée aux officiers (in-game) ou aux admins du serveur")
        return False

    return True

