import connect_mysql

query = "SELECT name, guild_id, bot_locked_until, bot_locked_until>CURRENT_TIMESTAMP AS locked " \
        "FROM guild_bot_infos JOIN guilds ON guilds.id=guild_id " \
        "WHERE NOT isnull(bot_allyCode)"

ret = connect_mysql.text_query(query)
for l in ret:
    print(l)
