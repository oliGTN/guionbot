import config

def _user(ctx_interaction):
    if type(ctx_interaction) == commands.Context:
        ctx = ctx_interaction
        user = ctx.author
    else: # Interaction
        interaction = ctx_interaction
        user = interaction.user

    return user

def dm(ctx_interaction, specific_restriction="Cette commande"):
    is_in_dm = (ctx_interaction.guild == None)
    if is_in_dm:
        bot_commands.command_error(ctx_interaction, specific_restriction+" ne peut âs être utilisée dans un DM")
        return True

    return False

def is_bot_admin(ctx_interaction):
    is_bot_admin = str(_user(ctx_interaction).id) in config.GO_ADMIN_IDS.split(' ')
    return is_bot_admin

def admin(ctx_interaction):
    is_bot_admin = is_bot_admin(ctx_interaction)
    if not is_bot_admin:
        bot_commands.command_error(ctx_interaction, "Commande réservée aux admins")
        return False

    return True

def is_officer(ctx_interaction):
    is_bot_admin = is_bot_admin(ctx_interaction)
    is_server_admin = _user(ctx_interaction).guild_permissions.administrator
    is_officer = False

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

    return is_officer or is_bot_admin or is_server_admin

def officer(ctx_interaction, specific_restriction="Cette commande"):
    is_officer = is_officer(ctx_interaction)

    if not is_officer:
        bot_commands.command_error(ctx_interaction, specific_restriction+" est réservée aux officiers (in-game) ou aux admins du serveur")
        return False

    return True

