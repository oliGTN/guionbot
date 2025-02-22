import connect_mysql

query = "SELECT name, guild_bots.guild_id, locked_since, NOT isnull(locked_since) AS locked " \
        "FROM guild_bot_infos JOIN guilds ON guilds.id=guild_id " \
        "JOIN guild_bots ON guild_bot_infos.guild_id=guild_bots.guild_id " \
        "WHERE NOT isnull(bot_allyCode)"

ret = connect_mysql.text_query(query)
for l in ret:
    print(l)
