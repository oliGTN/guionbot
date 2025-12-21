import go
import connect_mysql
import goutils
import config

async def register_player(allyCode, discord_id_txt, requestor_discord_id):
    check_user_rights = True
    if discord_id_txt == str(requestor_discord_id):
        #No need to check rights for self register
        check_user_rights = False

    #Ensure the allyCode is registered in DB
    e, t, dict_player = await go.load_player(allyCode, -1, False)
    if e != 0:
        return e, t

    player_name = dict_player["name"]

    if check_user_rights:
        #Need to check that the user is either an admin, or in the same guild
        # as the target allyCode

        #Get the guild ID of the requestor
        query = "SELECT guildId from player_discord "\
                "JOIN players ON players.allyCode=player_discord.allyCode "\
                "WHERE discord_id="+str(requestor_discord_id)
        goutils.log2("DBG", query)
        db_data = connect_mysql.get_value(query)
        if db_data==None:
            return 1, "Vous devez vous même être enregistré sur un code allié avant d'enregistrer un compte différent."

        is_owner = str(requestor_discord_id) in config.GO_ADMIN_IDS.split(' ')
        if db_data != dict_player["guildId"] and not is_owner:
            return 1, "Vous devez être dans la même guilde pour enregistrer un joueur."

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

    return 0, ""
