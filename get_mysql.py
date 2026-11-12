import golog
import data
from connect_mysql import get_line_async, get_table_async

##############################################################
# Function: load_config_players
# Parameters: optional guild_id to filter players
# Output:  dict_players_by_IG {key=IG name, value=[allycode, <@id>, isOfficer, guild_id]}
#          dict_players_by_ID {key=discord ID, value={"main":[allycode, isOfficer, guild_id]
#                                                     "alts":[[ac, isOff, guild_id], [ac2, isOff, guild_id]...]}}
##############################################################
async def load_config_players(guild_id=None):
    query = "SELECT players.allyCode, players.name, player_discord.discord_id, "\
            "player_discord.main, guildMemberLevel, guildId "\
            "FROM players "\
            "JOIN player_discord ON player_discord.allyCode=players.allyCode "
    if guild_id!=None:
        query+= "WHERE guildId='"+guild_id+"' "
    query+= "ORDER BY player_discord.discord_id, player_discord.main "
    golog.log("DBG", query)
    data_db = await get_table_async(query)

    dict_players_by_IG = {}
    dict_players_by_ID = {}

    if data_db != None:
        list_did = [x[2] for x in data_db]
        for line in data_db:
            ac = line[0]
            name = line[1]
            did = line[2]
            isMain = line[3]
            isOff = (line[4]!=2)
            guild_id = line[5]

            # dict_players_by_IG
            dict_players_by_IG[name] = [ac, name]
            if list_did.count(did) == 1:
                dict_players_by_IG[name] = [ac, "<@"+str(did)+">", isOff, guild_id]
            else:
                dict_players_by_IG[name] = [ac, "<@"+str(did)+"> ["+name+"]", isOff, guild_id]

            # dict_players_by_ID
            if not did in dict_players_by_ID:
                dict_players_by_ID[did] = {"main": None, "alts": []}
                
            if isMain:
                dict_players_by_ID[did]["main"] = [ac, isOff, guild_id]
            else:
                dict_players_by_ID[did]["alts"].append([ac, isOff, guild_id])

    return dict_players_by_IG, dict_players_by_ID


########################################
# Read ROTECODEX allocations imported into tb_platoons
########################################
########################################
# Get guild ID, allyCode and player name for the
#  warbot linked to this discord server
########################################
async def get_warbot_info(server_id, channel_id):
    golog.log("DBG", "looking for bot_infos from server ID...")
    query = "SELECT guild_bots.guild_id, guild_bots.allyCode, players.name, "\
            "tbChanRead_id, tbChanOut_id, tbRoleOut, "\
            "twFulldefDetection, "\
            "guilds.name, gfile_name, echostation_id, "\
            "tbFightEstimationType "\
            "FROM guild_bots "\
            "JOIN guild_bot_infos ON guild_bots.guild_id=guild_bot_infos.guild_id "\
            "JOIN players ON players.allyCode=guild_bots.allyCode "\
            "JOIN guilds ON guilds.id=guild_bots.guild_id "\
            "WHERE server_id="+str(server_id)
    golog.log("DBG", query)
    db_data = await get_line_async(query)

    if db_data == None:
        if channel_id != None:
            #no warbot found from server, try it from the channel as test channel
            golog.log("DBG", "looking for bot_infos from guild channel ID...")
            query = "SELECT guild_bots.guild_id, guild_bots.allyCode, players.name, "\
                    "tbChanRead_id, tbChanOut_id, tbRoleOut, "\
                    "twFulldefDetection, "\
                    "guilds.name, gfile_name, echostation_id, "\
                    "tbFightEstimationType "\
                    "FROM guild_bots "\
                    "JOIN guild_bot_infos ON guild_bots.guild_id=guild_bot_infos.guild_id "\
                    "JOIN players ON players.allyCode=guild_bots.allyCode "\
                    "JOIN guilds ON guilds.id=guild_bots.guild_id "\
                    "JOIN guild_test_channels ON guild_test_channels.guild_id=guild_bots.guild_id "\
                    "WHERE channel_id="+str(channel_id)
            golog.log("DBG", query)
            db_data = await get_line_async(query)

            if db_data == None:
                #no warbot found as test channel, try it from connected user
                golog.log("DBG", "looking for bot_infos from user channel ID...")
                query = "SELECT guildId, players.allyCode, players.name, "\
                        "tbChanRead_id, tbChanOut_id, tbRoleOut, "\
                        "twFulldefDetection, "\
                        "guilds.name, gfile_name, echostation_id, "\
                        "tbFightEstimationType "\
                        "FROM user_bot_infos "\
                        "JOIN players ON user_bot_infos.allyCode=players.allyCode "\
                        "JOIN guilds ON guilds.id=players.guildId "\
                        "LEFT JOIN guild_bot_infos ON players.guildId=guild_bot_infos.guild_id "\
                        "WHERE channel_id="+str(channel_id)
                golog.log("DBG", query)
                db_data = await get_line_async(query)

                if db_data == None:
                    return 1, "Pas de warbot trouvé, ni pour ce serveur, ni pour ce channel", None
        else:
            return 1, "Pas de warbot trouvé pour ce serveur", None
    
    return 0, "", {"guild_id": db_data[0],
                   "allyCode": str(db_data[1]),
                   "player_name": db_data[2],
                   "tbChanRead_id": db_data[3],
                   "tbChanOut_id": db_data[4],
                   "tbRoleOut": db_data[5],
                   "twFulldefDetection": db_data[6],
                   "guild_name": db_data[7],
                   "gfile_name": db_data[8],
                   "echostation_id": db_data[9],
                   "tbFightEstimationType": db_data[10]}

async def get_warbot_info_from_guild(guild_id):
    query = "SELECT guild_bots.guild_id, guild_bots.allyCode, players.name, "\
            "tbChanRead_id, tbChanOut_id, tbRoleOut, "\
            "twFulldefDetection, "\
            "guilds.name, server_id, gfile_name, discord_id "\
            "FROM guild_bots "\
            "JOIN guild_bot_infos ON guild_bots.guild_id=guild_bot_infos.guild_id "\
            "JOIN players ON players.allyCode=guild_bots.allyCode "\
            "JOIN guilds ON guilds.id=guild_bots.guild_id "\
            "LEFT JOIN player_discord ON player_discord.allyCode=guild_bots.allyCode "\
            "WHERE guild_bots.guild_id='"+guild_id+"'"
    golog.log("DBG", query)
    db_data = await get_line_async(query)

    if db_data == None:
        return 1, "Pas de warbot trouvé pour cette guilde", None

    return 0, "", {"guild_id": db_data[0],
                   "allyCode": str(db_data[1]),
                   "player_name": db_data[2],
                   "tbChanRead_id": db_data[3],
                   "tbChanOut_id": db_data[4],
                   "tbRoleOut": db_data[5],
                   "twFulldefDetection": db_data[6],
                   "guild_name": db_data[7],
                   "server_id": db_data[8],
                   "gfile_name": db_data[9],
                   "discord_id": db_data[10]}

########################################
# Get guild ID, allyCode and player name for the
#  google account linked to this channel
########################################
async def get_google_player_info(channel_id):
    query = "SELECT guildId, players.allyCode, players.name, \n"
    query+= "       tbChanRead_id, echostation_id, \n"
    query+= "       twChanOut_id \n"
    query+= "FROM user_bot_infos \n"
    query+= "JOIN players ON players.allyCode=user_bot_infos.allyCode \n"
    query+= "LEFT JOIN guild_bot_infos ON guild_bot_infos.guild_id=players.guildId \n"
    query+= "WHERE channel_id="+str(channel_id)
    golog.log("DBG", query)
    db_data = await get_line_async(query)
    if db_data == None:
        return 1, "Pas d'utilisateur trouvé pour ce channel", None
    
    return 0, "", {"guild_id": db_data[0],
                   "allyCode": str(db_data[1]),
                   "player_name": db_data[2],
                   "tbChanRead_id": db_data[3],
                   "echostation_id": db_data[4],
                   "twChanOut_id": db_data[5]}

# IN: tbs_round > ROTE1 to ROTE6, or ROTE0 to get the latest data
async def get_tb_platoon_allocations(guild_id, tbs_round):
    """
    Read the saved platoon allocations for the requested TB round.

    Each unit contains its lowest allocation priority and the assigned players:
    {platoon_name: {unit_name: {"priority": int, "players": [player_name, ...]}}}

    ROTE0 reads the most recently saved ROTE configuration.
    """
    if not isinstance(tbs_round, str) or len(tbs_round) < 4:
        return 1, "Round de BT invalide: " + str(tbs_round), None

    tb_name = tbs_round[:-1]
    try:
        tb_phase = int(tbs_round[-1])
    except (TypeError, ValueError):
        return 1, "Phase de BT invalide: " + str(tbs_round), None

    if tb_phase < 0 or tb_phase > 6:
        return 1, "Phase de BT invalide: " + str(tb_phase), None

    dict_units = data.get("unitsList_dict.json")
    dict_tb = data.get("tb_definition.json")

    query = """
        SELECT pa.zone_id, pa.platoon_id, pa.unit_id, p.name,
               COALESCE(pa.priority, 1)
        FROM platoon_allocations AS pa
        INNER JOIN platoon_config AS pc ON pc.id = pa.config_id
        LEFT JOIN players AS p ON p.allyCode = pa.allyCode
        WHERE pc.guild_id = %s
          AND pc.tb_name = %s
    """
    params = [guild_id, tb_name]
    if tb_phase > 0:
        query += " AND pc.phases = %s"
        params.append(str(tb_phase))
    else:
        query += """
          AND ABS(TIMESTAMPDIFF(
              SECOND,
              pc.timestamp,
              (
                  SELECT MAX(timestamp)
                  FROM platoon_config
                  WHERE guild_id = %s AND tb_name = %s
              )
          )) < 5
        """
        params.extend([guild_id, tb_name])
    query += " ORDER BY pa.priority, pa.zone_id, pa.platoon_id, pa.unit_id"

    golog.log("DBG", query + " -- " + str(params))
    db_data = await get_table_async(query, tuple(params))
    if db_data is None:
        return 0, "", None
    if not db_data:
        return 0, "", None

    allocations = {}
    for zone_id, platoon_id, unit_id, player_name, priority in db_data:
        if not zone_id or not platoon_id or not unit_id:
            continue

        conflict_id = "_".join(zone_id.split("_")[:-1])
        zone_definition = dict_tb.get(conflict_id) if isinstance(dict_tb, dict) else None
        unit_definition = dict_units.get(unit_id) if isinstance(dict_units, dict) else None
        if not isinstance(zone_definition, dict) or not zone_definition.get("name"):
            golog.log("ERR", "Unknown platoon allocation zone_id: " + str(zone_id))
            continue
        if not isinstance(unit_definition, dict) or not unit_definition.get("name"):
            golog.log("ERR", "Unknown platoon allocation unit_id: " + str(unit_id))
            continue

        if tb_name == "ROTE":
            try:
                platoon_position = str(7 - int(platoon_id.rsplit("-", 1)[1]))
            except (ValueError, IndexError):
                golog.log("ERR", "Invalid ROTE platoon_id: " + str(platoon_id))
                continue
        else:
            platoon_position = platoon_id.rsplit("-", 1)[-1]
            if not platoon_position.startswith("hoth-platoon-"):
                platoon_position = "hoth-platoon-" + platoon_position

        platoon_name = zone_definition["name"] + "-" + platoon_position
        unit_name = unit_definition["name"]
        try:
            allocation_priority = int(priority) if priority is not None else 1
        except (TypeError, ValueError):
            allocation_priority = 1

        unit_allocations = allocations.setdefault(platoon_name, {})
        if unit_name not in unit_allocations:
            unit_allocations[unit_name] = {
                "priority": allocation_priority,
                "players": []
            }
        else:
            unit_allocations[unit_name]["priority"] = min(
                unit_allocations[unit_name]["priority"], allocation_priority
            )
        unit_allocation = unit_allocations[unit_name]

        if player_name and player_name not in unit_allocation["players"]:
            unit_allocation["players"].append(player_name)

    if not allocations:
        return 0, "", None
    return 0, "", allocations

