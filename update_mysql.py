import os
import config
import sys
from urllib.parse import uses_netloc, urlparse
import datetime
import time
from wcwidth import wcswidth
import asyncio
from decimal import Decimal
from hashlib import md5
from json import dumps as json_dumps

import goutils
import golog
import data

from mysql.connector import Error
from connect_mysql import (
    adb_connect,
    release_async_connection,
    get_value_async,
    get_table_async,
    get_column_async,
    simple_execute_async,
    executemany_async,
)
from statq import get_player_statq

async def update_guild_teams(guild_id, dict_team):
#         dict_team {
#             team_name:{
#                 "rarity": unlocking rarity of GV character
#                 "categories": [
#                     [catégorie, nombre nécessaire, {
#                         nom:[id, étoiles min, gear min, étoiles reco,
#                              gear reco, liste zeta, vitesse, nom court]
#                         }
#                     ], ...
#                 ]
#             }
#         }
    # Manage the SQL case where guild_id=null
    if guild_id==None:
        guild_id_test = 'isnull(guild_id)'
        guild_id_txt = 'NULL'
    else:
        guild_id_test = "guild_id='"+guild_id+"'"
        guild_id_txt = "'"+guild_id+"'"

    # Get all team names, in order to delete the teams
    # that are not defined anymore
    query = "SELECT name FROM guild_teams "\
            "WHERE "+guild_id_test+" "
    golog.log("DBG", query)
    teams_to_remove = await get_column_async(query)

    for team_name in dict_team:
        # Note the team as existing, so not to be removed
        if team_name in teams_to_remove:
            teams_to_remove.remove(team_name)

        # team md5
        team_dict = dict_team[team_name]
        team_txt = json_dumps(team_dict, sort_keys=True)
        team_unicode = team_txt.encode('utf-8')
        team_md5 = md5(team_unicode).hexdigest()

        # Check if team exists
        query = "SELECT md5 FROM guild_teams "\
                "WHERE "+guild_id_test+" "\
                "AND name='"+team_name+"' "
        golog.log("DBG", query)
        existing_md5 = await get_value_async(query)

        if existing_md5 == team_md5:
            # the team exists and is unchanged
            continue
        else:
            # delete team
            query = "DELETE FROM guild_teams "\
                    "WHERE "+guild_id_test+" "\
                    "AND name='"+team_name+"' "
            golog.log("DBG", query)
            await simple_execute_async(query)

        # create team
        team_rarity = dict_team[team_name]["rarity"]
        if team_rarity == '':
            team_rarity = 0
        query = "INSERT INTO guild_teams(guild_id, name, GVrarity, md5) "\
                "VALUES("+guild_id_txt+", '"+team_name+"', "+str(team_rarity)+", '"+team_md5+"') "
        golog.log("DBG", query)
        await simple_execute_async(query)

        # get team ID
        query = "SELECT id FROM guild_teams "\
                "WHERE "+guild_id_test+" "\
                "AND name='"+team_name+"' "
        golog.log("DBG", query)
        team_id = await get_value_async(query)

        subteam_list = dict_team[team_name]["categories"]
        for sub_team in subteam_list:
            subteam_name = sub_team[0]
            subteam_min = sub_team[1]
            subteam_toons = sub_team[2]
            
            # create team
            query = "INSERT INTO guild_subteams(team_id, name, minimum) "\
                    "VALUES("+str(team_id)+", '"+subteam_name+"', "+str(subteam_min)+") "
            golog.log("DBG", query)
            await simple_execute_async(query)

            # get subteam ID
            query = "SELECT id FROM guild_subteams "\
                    "WHERE team_id="+str(team_id)+" "\
                    "AND name='"+subteam_name+"' "
            golog.log("DBG", query)
            subteam_id = await get_value_async(query)

            for toon_id in subteam_toons:
                toon = subteam_toons[toon_id]
                toon_rarity_min = toon[1]
                toon_gear_min = str(toon[2])
                toon_rarity_reco = toon[3]
                toon_gear_reco = str(toon[4])
                
                # create roster element of subteam
                query = "INSERT INTO guild_team_roster(subteam_id, unit_id, "\
                        "rarity_min, gear_min, rarity_reco, gear_reco) "\
                        "VALUE("+str(subteam_id)+", '"+toon_id+"', "\
                        ""+str(toon_rarity_min)+", '"+toon_gear_min+"', "\
                        ""+str(toon_rarity_reco)+", '"+toon_gear_reco+"') "
                golog.log("DBG", query)
                await simple_execute_async(query)

                # get roster ID
                query = "SELECT id FROM guild_team_roster "\
                        "WHERE subteam_id="+str(subteam_id)+" "\
                        "AND unit_id='"+toon_id+"' "
                golog.log("DBG", query)
                roster_id = await get_value_async(query)

                for zeta in toon[5].split(","):
                    zeta_id = goutils.get_capa_id_from_short(toon_id, zeta)
                    query = "INSERT INTO guild_team_roster_zetas(roster_id, name) "\
                            "VALUES("+str(roster_id)+", '"+zeta_id+"') "
                    golog.log("DBG", query)
                    await simple_execute_async(query)

                for omicron in toon[6].split(","):
                    omicron_id = goutils.get_capa_id_from_short(toon_id, omicron)
                    query = "INSERT INTO guild_team_roster_omicrons(roster_id, name) "\
                            "VALUES("+str(roster_id)+", '"+omicron_id+"') "
                    golog.log("DBG", query)
                    await simple_execute_async(query)

        # delete not existing teams that were existing before
        if len(teams_to_remove) > 0:
            query = "DELETE FROM guild_teams "\
                    "WHERE "+guild_id_test+" "\
                    "AND name IN "+ str(tuple(teams_to_remove)).replace(",)", ")")
            golog.log("DBG", query)
            await simple_execute_async(query)
            

async def insert_roster_evo(allyCode, defId, evo_txt):
        #adapt syntax ty MYSQL
        evo_txt = evo_txt.replace("'","''")

        if defId!=None:
            query = "INSERT INTO roster_evolutions(allyCode, defId, description) "\
                   +"VALUES("+str(allyCode)+", '"+str(defId)+"', '"+evo_txt+"')"
        else:
            query = "INSERT INTO roster_evolutions(allyCode, description) "\
                   +"VALUES("+str(allyCode)+", '"+evo_txt+"')"
        golog.log("DBG", query)
        await simple_execute_async(query)

    
#####################################################################
# START of update_player and associated functions
#####################################################################
PLAYER_STATS = ['1', '5', '6', '7', '8', '14', '15', '16', '17', '18', '28']


async def update_player(dict_player):
    """Update a complete player using one shared DB connection."""
    mysql_db = None
    cursor = None

    try:
        mysql_db = await adb_connect()
        cursor = await mysql_db.cursor()

        player_data = await update_player_general(cursor, dict_player)

        ec, et = await update_player_roster(
            cursor, dict_player, player_data
        )
        if ec != 0:
            return ec, et

        await update_player_datacrons(cursor, dict_player)

        p_modq, p_statq = await update_player_quality(
            cursor, player_data
        )

        await update_player_gp_history(
            cursor, player_data, p_modq, p_statq
        )

        await mysql_db.commit()

    except Error as error:
        golog.log("ERR", error)
        return 1, error

    finally:
        if cursor is not None:
            await cursor.close()
        if mysql_db is not None:
            await release_async_connection(mysql_db)

    return 0, ""


async def update_player_general(cursor, dict_player):
    """Update the players table and return shared player information."""

    allyCode = dict_player["allyCode"]
    playerId = dict_player["playerId"]

    if "guildId" in dict_player:
        guildId = dict_player["guildId"]
        guildName = dict_player["guildName"]
    else:
        guildId = ""
        guildName = ""

    lastActivity_player = int(dict_player["lastActivityTime"])
    lastActivity_ts = datetime.datetime.fromtimestamp(
        lastActivity_player / 1000
    )
    lastActivity = lastActivity_ts.strftime("%Y-%m-%d %H:%M:%S")

    level = dict_player["level"]
    name = dict_player["name"]

    arena_char_rank = None
    arena_ship_rank = None

    for arena in dict_player.get("pvpProfile", []):
        if arena["type"] == "SQUADARENA":
            arena_char_rank = arena["rank"]
        elif arena["type"] == "FLEETARENA":
            arena_ship_rank = arena["rank"]

    arena_char_rank_txt = (
        "NULL" if arena_char_rank is None else str(arena_char_rank)
    )
    arena_ship_rank_txt = (
        "NULL" if arena_ship_rank is None else str(arena_ship_rank)
    )

    if (
        "playerRating" in dict_player
        and "playerRankStatus" in dict_player["playerRating"]
    ):
        rank_status = dict_player["playerRating"]["playerRankStatus"]
        grand_arena_league = rank_status["leagueId"]
        grand_arena_division = 6 - int(rank_status["divisionId"] / 5)

        if "skillRating" in dict_player["playerRating"]["playerSkillRating"]:
            grand_arena_rating = int(
                dict_player["playerRating"]["playerSkillRating"]["skillRating"]
            )
        else:
            grand_arena_rating = 0
    else:
        grand_arena_league = ""
        grand_arena_division = 0
        grand_arena_rating = 0

    grand_arena_rank = grand_arena_league + str(grand_arena_division)

    char_gp = 0
    ship_gp = 0

    for stat in dict_player["profileStat"]:
        if stat["nameKey"] == "STAT_CHARACTER_GALACTIC_POWER_ACQUIRED_NAME":
            char_gp = stat["value"]
        elif stat["nameKey"] == "STAT_SHIP_GALACTIC_POWER_ACQUIRED_NAME":
            ship_gp = stat["value"]

    poUTCOffsetMinutes = dict_player["localTimeZoneOffsetMinutes"]

    query = (
        "INSERT IGNORE INTO players(allyCode) "
        "VALUES(" + str(allyCode) + ")"
    )
    await cursor.execute(query)

    query = (
        "UPDATE players "
        "SET guildId = '" + guildId + "', "
        "guildName = '" + guildName.replace("'", "''") + "', "
        "playerId = '" + playerId + "', "
        "lastActivity = '" + lastActivity + "', "
        "level = " + str(level) + ", "
        "name = '" + str(name).replace("'", "''") + "', "
        "char_gp = " + str(char_gp) + ", "
        "ship_gp = " + str(ship_gp) + ", "
        "arena_char_rank = " + arena_char_rank_txt + ", "
        "arena_ship_rank = " + arena_ship_rank_txt + ", "
        "grand_arena_rank = '" + grand_arena_rank + "', "
        "grand_arena_rating = " + str(grand_arena_rating) + ", "
        "poUTCOffsetMinutes = " + str(poUTCOffsetMinutes) + ", "
        "lastUpdated = CURRENT_TIMESTAMP "
        "WHERE allyCode = " + str(allyCode)
    )
    await cursor.execute(query)

    return {
        "allyCode": allyCode,
        "playerId": playerId,
        "guildName": guildName,
        "arena_char_rank_txt": arena_char_rank_txt,
        "arena_ship_rank_txt": arena_ship_rank_txt,
        "grand_arena_rank": grand_arena_rank,
        "grand_arena_rating": grand_arena_rating,
        "char_gp": char_gp,
        "ship_gp": ship_gp,
        "poUTCOffsetMinutes": poUTCOffsetMinutes,
    }


async def update_player_roster(cursor, dict_player, player_data):
    """Update all characters, mods and abilities."""

    dict_unitsList = data.get("unitsList_dict.json")
    dict_modList = data.get("modList_dict.json")
    dict_capas = data.get("unit_capa_list.json")
    dict_stats = data.get("dict_stats.json")

    allyCode = player_data["allyCode"]
    playerId = player_data["playerId"]

    for character_id, character in dict_player["rosterUnit"].items():
        if "gp" not in character:
            message = "ERR no gp for " + playerId + ":" + character_id
            golog.log("ERR no gp for ", playerId + ":" + character_id)
            return 1, message

        roster_id = await update_character(
            cursor, allyCode, character_id, character, dict_unitsList
        )

        await update_character_mods(
            cursor, roster_id, character, dict_modList, dict_stats
        )

        await update_character_skills(
            cursor, roster_id, character_id, character, dict_capas
        )

        await asyncio.sleep(0)

    return 0, ""


async def update_character(
    cursor, allyCode, character_id, character, dict_unitsList
):
    """Insert/update one roster character and return roster.id."""

    c_combatType = dict_unitsList[character_id]["combatType"]
    c_forceAlignment = dict_unitsList[character_id]["forceAlignment"]
    c_gear = character["currentTier"]
    c_gp = character["gp"]
    c_level = character["currentLevel"]
    c_rarity = character["currentRarity"]
    c_relic_currentTier = character.get("relic", {}).get("currentTier", 0)
    c_eraLevel_txt = str(character["eraLevel"]) if "eraLevel" in character else "NULL"

    query = (
        "INSERT IGNORE INTO roster(allyCode, defId) "
        "VALUES(" + str(allyCode) + ", '" + character_id + "')"
    )
    await cursor.execute(query)

    query = (
        "UPDATE roster "
        "SET allyCode = " + str(allyCode) + ", "
        "defId = '" + character_id + "', "
        "combatType = " + str(c_combatType) + ", "
        "forceAlignment = " + str(c_forceAlignment) + ", "
        "gear = " + str(c_gear) + ", "
        "gp = " + str(c_gp) + ", "
        "level = " + str(c_level) + ", "
        "eraLevel = " + c_eraLevel_txt + ", "
        "rarity = " + str(c_rarity) + ", "
        "relic_currentTier = " + str(c_relic_currentTier)
    )

    equipment = [False] * 6
    for eqpt in character.get("equipment", []):
        equipment[eqpt["slot"]] = True

    query += ",equipment = '" + "".join(
        "1" if value else "0" for value in equipment
    ) + "' "

    if "stats" in character:
        for stat_id in PLAYER_STATS:
            stat_value = character["stats"]["final"].get(stat_id, 0)
            query += ",stat" + stat_id + " = " + str(stat_value) + " "

        if "mods" in character["stats"]:
            for stat_id in PLAYER_STATS:
                if stat_id in ["14", "15"]:
                    stat_mod_id = str(int(stat_id) + 7)
                elif stat_id in ["39", "40"]:
                    stat_mod_id = str(int(stat_id) - 4)
                else:
                    stat_mod_id = stat_id

                stat_value = character["stats"]["mods"].get(stat_mod_id, 0)
                query += ",mod" + stat_id + " = " + str(stat_value) + " "

    query += (
        "WHERE allyCode = " + str(allyCode) +
        " AND defId = '" + character_id + "'"
    )
    await cursor.execute(query)

    query = (
        "SELECT id FROM roster WHERE allyCode = " + str(allyCode) +
        " AND defId = '" + character_id + "'"
    )
    return await get_value_async(query)


async def update_character_mods(
    cursor, roster_id, character, dict_modList, dict_stats
):
    """Update equipped mods and remove mods no longer equipped."""

    query = "SELECT id FROM mods WHERE roster_id = " + str(roster_id)
    previous_mods_ids = await get_column_async(query)

    current_mods_ids = []

    for mod in character.get("equippedStatMod", []):
        await update_mod(
            cursor, roster_id, mod, dict_modList, dict_stats
        )
        current_mods_ids.append(mod["id"])

    to_be_removed = tuple(
        set(previous_mods_ids) - set(current_mods_ids)
    )

    if to_be_removed:
        query = (
            "DELETE FROM mods WHERE id IN " +
            str(to_be_removed).replace(",)", ")")
        )
        await cursor.execute(query)


async def update_mod(
    cursor, roster_id, mod, dict_modList, dict_stats
):
    """Insert/update one mod."""

    mod_id = mod["id"]
    definition = dict_modList[mod["definitionId"]]

    primary_id = mod["primaryStat"]["stat"]["unitStatId"]
    primary_raw = int(
        mod["primaryStat"]["stat"]["statValueDecimal"]
    )

    if dict_stats[str(primary_id)]["isDecimal"]:
        primary_value = primary_raw / 100
    else:
        primary_value = primary_raw / 10000

    secondary = []
    for sec_stat in mod["secondaryStat"]:
        stat_id = sec_stat["stat"]["unitStatId"]
        raw_value = int(sec_stat["stat"]["statValueDecimal"])

        if dict_stats[str(stat_id)]["isDecimal"]:
            value = raw_value / 100
        else:
            value = raw_value / 10000

        secondary.append((stat_id, value))

    while len(secondary) < 4:
        secondary.append((0, 0))

    query = (
        "INSERT IGNORE INTO mods(id) VALUES('" + mod_id + "')"
    )
    await cursor.execute(query)

    query = (
        "UPDATE mods SET "
        "roster_id = " + str(roster_id) + ", "
        "defId = " + str(mod["definitionId"]) + ", "
        "level = " + str(mod["level"]) + ", "
        "pips = " + str(definition["rarity"]) + ", "
        "mod_set = " + str(definition["setId"]) + ", "
        "slot = " + str(definition["slot"]) + ", "
        "tier = " + str(mod["tier"]) + ", "
        "prim_stat = " + str(primary_id) + ", "
        "prim_value = " + str(primary_value) + ", "
        "sec1_stat = " + str(secondary[0][0]) + ", "
        "sec1_value = " + str(secondary[0][1]) + ", "
        "sec2_stat = " + str(secondary[1][0]) + ", "
        "sec2_value = " + str(secondary[1][1]) + ", "
        "sec3_stat = " + str(secondary[2][0]) + ", "
        "sec3_value = " + str(secondary[2][1]) + ", "
        "sec4_stat = " + str(secondary[3][0]) + ", "
        "sec4_value = " + str(secondary[3][1]) + " "
        "WHERE id = '" + mod_id + "'"
    )
    await cursor.execute(query)


async def update_character_skills(
    cursor, roster_id, character_id, character, dict_capas
):
    """Update normal abilities and ultimate."""

    for capa in character["skill"]:
        capa_name = capa["id"]
        capa_level = capa["tier"] + 2

        if capa_level >= dict_capas[character_id][capa_name]["omicronTier"]:
            capa_omicron_type = dict_capas[character_id][capa_name]["omicronMode"]
        else:
            capa_omicron_type = ""

        capa_shortname = dict_capas[character_id][capa_name]["shortname"]

        if capa_name == "uniqueskill_GALACTICLEGEND01":
            capa_shortname = "GL"

        query = (
            "INSERT IGNORE INTO roster_skills(roster_id, name) "
            "VALUES(" + str(roster_id) + ", '" + capa_shortname + "')"
        )
        await cursor.execute(query)

        query = (
            "UPDATE roster_skills SET "
            "level = " + str(capa_level) + ", "
            "omicron_type = '" + capa_omicron_type + "' "
            "WHERE roster_id = " + str(roster_id) +
            " AND name = '" + capa_shortname + "'"
        )
        await cursor.execute(query)

    await update_character_ultimate(cursor, roster_id, character)


async def update_character_ultimate(cursor, roster_id, character):
    """Update ultimate marker."""

    if not any(
        ability.startswith("ultimate")
        for ability in character.get("purchaseAbilityId", [])
    ):
        return

    query = (
        "INSERT IGNORE INTO roster_skills(roster_id, name) "
        "VALUES(" + str(roster_id) + ", 'ULTI')"
    )
    await cursor.execute(query)

    query = (
        "UPDATE roster_skills SET level = 1, omicron_type = '' "
        "WHERE roster_id = " + str(roster_id) +
        " AND name = 'ULTI'"
    )
    await cursor.execute(query)


async def update_player_datacrons(cursor, dict_player):
    """Update datacrons and remove old datacrons."""

    if "datacron" not in dict_player:
        return

    dict_rules = data.get("targetrules_dict.json")
    allyCode = dict_player["allyCode"]

    query = (
        "SELECT id FROM datacrons WHERE allyCode = " + str(allyCode)
    )
    previous_ids = await get_column_async(query)

    current_ids = []

    for datacron_id, datacron in dict_player["datacron"].items():
        await update_datacron(
            cursor, datacron_id, datacron, dict_rules, allyCode
        )
        current_ids.append(datacron_id)

    to_be_removed = tuple(set(previous_ids) - set(current_ids))

    if to_be_removed:
        query = (
            "DELETE FROM datacrons WHERE id IN " +
            str(to_be_removed).replace(",)", ")")
        )
        await cursor.execute(query)


async def update_datacron(
    cursor, datacron_id, datacron, dict_rules, allyCode
):
    """Insert/update one datacron."""

    levels = {}

    for level, index in ((3, 2), (6, 5), (9, 8), (12, 11), (15, 14)):
        if len(datacron.get("affix", [])) >= level:
            affix = datacron["affix"][index]
            target = dict_rules[affix["targetRule"]][0]
            levels[level] = affix["abilityId"] + ":" + target

    query = (
        "INSERT IGNORE INTO datacrons(id) VALUES('" +
        datacron_id + "')"
    )
    await cursor.execute(query)

    query = (
        "UPDATE datacrons SET "
        "allyCode = " + str(allyCode) + ", "
        "setId = " + str(datacron["setId"]) + " "
    )

    for level in (3, 6, 9, 12, 15):
        if level in levels:
            query += (
                ", level_" + str(level) + " = '" +
                str(levels[level]) + "' "
            )

    query += "WHERE id = '" + datacron_id + "'"
    await cursor.execute(query)


async def update_player_quality(cursor, player_data):
    """Compute ModQ and StatQ, then update players."""

    allyCode = player_data["allyCode"]

    query = (
        "SELECT count(mods.id)/(char_gp/100000) "
        "FROM mods "
        "JOIN roster ON mods.roster_id = roster.id "
        "JOIN players ON players.allyCode = roster.allyCode "
        "WHERE roster.allyCode=" + str(allyCode) + " "
        "AND ("
        "(sec1_stat=5 AND sec1_value>=15) OR "
        "(sec2_stat=5 AND sec2_value>=15) OR "
        "(sec3_stat=5 AND sec3_value>=15) OR "
        "(sec4_stat=5 AND sec4_value>=15))"
    )
    p_modq = await get_value_async(query)

    if p_modq is None:
        p_modq = "NULL"

    ec, et, p_statq, l_statq = await get_player_statq(str(allyCode))
    if ec != 0:
        p_statq = "NULL"

    query = (
        "UPDATE players SET "
        "modq = GREATEST(" + str(p_modq) + ", modq), "
        "statq = GREATEST(" + str(p_statq) + ", statq) "
        "WHERE allyCode = " + str(allyCode)
    )
    await cursor.execute(query)

    return p_modq, p_statq


async def update_player_gp_history(
    cursor, player_data, p_modq, p_statq
):
    """Update today's GP history."""

    allyCode = player_data["allyCode"]
    guildName = player_data["guildName"]
    poUTCOffsetMinutes = player_data["poUTCOffsetMinutes"]

    time_now = datetime.datetime.now()

    time_po_char_std = time_now.replace(
        hour=20, minute=0, second=0, microsecond=0
    )
    time_po_char_player = (
        time_po_char_std -
        datetime.timedelta(0, poUTCOffsetMinutes * 60)
    )
    delta_time_po_char = abs(
        (time_now - time_po_char_player).seconds / 60
    )

    time_po_ship_std = time_now.replace(
        hour=21, minute=0, second=0, microsecond=0
    )
    time_po_ship_player = (
        time_po_ship_std -
        datetime.timedelta(0, poUTCOffsetMinutes * 60)
    )
    delta_time_po_ship = abs(
        (time_now - time_po_ship_player).seconds / 60
    )

    query = (
        "INSERT IGNORE INTO gp_history(date, allyCode) "
        "VALUES(CURDATE(), " + str(allyCode) + ")"
    )
    await cursor.execute(query)

    query = (
        "UPDATE gp_history SET "
        "guildName = '" + guildName.replace("'", "''") + "', "
        "arena_char_rank = " + player_data["arena_char_rank_txt"] + ", "
        "arena_char_po_delta_minutes = " + str(delta_time_po_char) + ", "
        "arena_ship_rank = " + player_data["arena_ship_rank_txt"] + ", "
        "arena_ship_po_delta_minutes = " + str(delta_time_po_ship) + ", "
        "grand_arena_rank = '" + player_data["grand_arena_rank"] + "', "
        "grand_arena_rating = " + str(player_data["grand_arena_rating"]) + ", "
        "char_gp = " + str(player_data["char_gp"]) + ", "
        "ship_gp = " + str(player_data["ship_gp"]) + ", "
        "modq = " + str(p_modq) + ", "
        "statq = " + str(p_statq) + " "
        "WHERE date = CURDATE() "
        "AND allyCode = " + str(allyCode)
    )
    await cursor.execute(query)
    
#####################################################################
# END of update_player and associated functions
#####################################################################

#####################################################################
# update_gv_history
# IN: txt_alllyCOde - allyCode of the player
# IN: character - character_id or character name
#IN: is_ID - Trus if character_id, False if character name
#IN: progress - value of progress between 0 and 100
#IN: completed - True if the GV is completed (even if not 100%)
#IN: source - name of the bot which has computed the progress
#OUT: 0 if no error
#####################################################################
async def update_gv_history(txt_allyCode, player_name, character, is_ID, progress, completed, source):

    if txt_allyCode == '':
        query = "SELECT allyCode FROM players WHERE name = '"+player_name.replace("'", "''")+"'"
        golog.log("DBG", query)
        list_players = get_column(query)
        if len(list_players) != 1:
            return -1
        txt_allyCode = str(list_players[0])
        golog.log("DBG", "allyCode="+txt_allyCode)

    if is_ID:
        character_id = character
    else:
        list_character_ids, dict_id_name, txt = await goutils.get_characters_from_alias([character])
        character_id = list_character_ids[0]
    golog.log("DBG", "character_id="+character_id)

    #Look if the GV already has a date for completed
    if completed:
        query = "SELECT COUNT(*) FROM gv_history " \
              + "WHERE allyCode="+txt_allyCode+" " \
              + "AND defId='"+character_id+"' " \
              + "AND complete=1 " \
              + "AND source='"+source+"'"
        golog.log("DBG", query)
        count_completed = await get_value_async(query)
        already_complete = (count_completed >= 1)
    else:
        already_complete = False

    if not already_complete and progress>0:
        query = "INSERT IGNORE INTO gv_history(date, allyCode, defId, source) "\
               +"VALUES(CURDATE(), '"+txt_allyCode+"', '"+character_id+"', '"+source+"')"
        golog.log("DBG", query)
        await simple_execute_async(query)

        query = "UPDATE gv_history "\
               +"SET progress = "+str(progress)+", "\
               +"complete = "+str(int(completed))+" "\
               +"WHERE date = CURDATE() "\
               +"AND allyCode = '"+txt_allyCode+"' " \
               +"AND defId = '"+character_id+"' " \
               +"AND source = '"+source+"' "
        golog.log("DBG", query)
        await simple_execute_async(query)


######################################
# update the TB history
# update all zones, even past ones, as te volume is acceptable
# update player data only if something has changed, for performance reasons
async def update_tb_round(guild_id, tb_id, tb_round, dict_phase, dict_zones, dict_strike_zones, list_open_zones, dict_tb_players):
    dict_tb = data.get("tb_definition.json")

    ##################################
    # Whole TB data
    ##################################
    # Check / Create the TB in DB
    query = "SELECT id FROM tb_history " \
            "WHERE tb_id='"+tb_id+"' "\
            "AND guild_id='"+guild_id+"' "
    golog.log("DBG", query)
    db_data = await get_value_async(query)

    if db_data==None:
        tb_ts = int(tb_id.split(":")[1][1:-3])
        tb_date = datetime.datetime.fromtimestamp(tb_ts).strftime("%Y/%m/%d %H:%M:%S")
        query = "INSERT INTO tb_history(tb_id, tb_name, "\
                "start_date, guild_id, current_round) " \
                "VALUES('"+tb_id+"', '"+dict_phase["name"].replace("'", "''")+"', "\
                "'"+tb_date+"', '"+guild_id+"', "\
                ""+str(tb_round)+") "
        golog.log("DBG", query)
        await simple_execute_async(query)

        # Get the id of the new TB
        query = "SELECT id FROM tb_history " \
                "WHERE tb_id='"+tb_id+"' "\
                "AND guild_id='"+guild_id+"' "
        golog.log("DBG", query)
        tb_db_id = str(await get_value_async(query))
    else:
        tb_db_id = str(db_data)
        query = "UPDATE tb_history "\
                "SET lastUpdated=CURRENT_TIMESTAMP(), "\
                "current_round="+str(tb_round)+" "\
                "WHERE id="+str(tb_db_id)
        golog.log("DBG", query)
        await simple_execute_async(query)

    ##################################
    # TB phase / day / round
    ##################################
    # Check / Create the TB phase in DB
    query = "SELECT id FROM tb_phases " \
            "WHERE tb_id='"+tb_db_id+"' "\
            "AND round="+str(tb_round)
    golog.log("DBG", query)
    db_data = await get_value_async(query)

    if db_data==None:
        query = "INSERT INTO tb_phases(tb_id, round, prev_stars) " \
                "VALUES("\
                ""+str(tb_db_id)+", "\
                ""+str(tb_round)+", "\
                ""+str(dict_phase["prev_stars"])+") "
        golog.log("DBG", query)
        await simple_execute_async(query)

        # Get the id of the new TB phase
        query = "SELECT id FROM tb_phases " \
                "WHERE tb_id='"+tb_db_id+"' "\
                "AND round="+str(tb_round)
        golog.log("DBG", query)
        phase_id = str(await get_value_async(query))
    else:
        phase_id = str(db_data)

    totalPlayers = dict_phase["TotalPlayers"]
    deploymentType = 0 # mix
    if "chars" in dict_phase["deployment_types"]:
        deploymentType = 1 # chars only
    if "ships" in dict_phase["deployment_types"]:
        deploymentType = 2 # chars and ships

    availableShipDeploy  = dict_phase["availableShipDeploy"]
    availableCharDeploy = dict_phase["availableCharDeploy"]
    availableMixDeploy = dict_phase["availableMixDeploy"]
    remainingShipDeploy = dict_phase["remainingShipDeploy"]
    remainingCharDeploy = dict_phase["remainingCharDeploy"]
    remainingMixDeploy = dict_phase["remainingMixDeploy"]
    remainingShipPlayers = dict_phase["shipPlayers"]
    remainingCharPlayers = dict_phase["charPlayers"]
    remainingMixPlayers = dict_phase["mixPlayers"]

    query = "UPDATE tb_phases "\
            "SET "\
            "totalPlayers = "+str(totalPlayers)+", "\
            "deploymentType = "+str(deploymentType)+", "\
            "availableShipDeploy  = "+str(availableShipDeploy)+", "\
            "availableCharDeploy = "+str(availableCharDeploy)+", "\
            "availableMixDeploy = "+str(availableMixDeploy)+", "\
            "remainingShipDeploy = "+str(remainingShipDeploy)+", "\
            "remainingCharDeploy = "+str(remainingCharDeploy)+", "\
            "remainingMixDeploy = "+str(remainingMixDeploy)+", "\
            "remainingShipPlayers = "+str(remainingShipPlayers)+", "\
            "remainingCharPlayers = "+str(remainingCharPlayers)+", "\
            "remainingMixPlayers = "+str(remainingMixPlayers)+" "\
            "WHERE id="+str(phase_id)
    golog.log("DBG", query)
    await simple_execute_async(query)

    ##################################
    # TB zones
    ##################################
    i_zone = 0
    zone_updates = []
    for zone_fullname in dict_zones:
        zone = dict_zones[zone_fullname]
        zone_shortname = dict_tb[zone_fullname]["name"]

        if zone_fullname.endswith("_bonus"):
            zone_round = zone_fullname[-18]
            is_bonus = "1"
        else:
            zone_round = zone_fullname[-12]
            is_bonus = "0"

        round = str(dict_phase["round"])

        # Check / Create the zone in DB
        if zone_fullname in list_open_zones:
            #look for the zone in current round
            query = "SELECT id FROM tb_zones " \
                    "WHERE tb_id="+tb_db_id+" "\
                    "AND zone_id='"+zone_fullname+"' "\
                    "AND round="+round+" "
        else:
            #look for the latest round of this zone
            query = "SELECT id FROM tb_zones " \
                    "WHERE tb_id="+tb_db_id+" "\
                    "AND zone_id='"+zone_fullname+"' "\
                    "ORDER BY round DESC "\
                    "LIMIT 1 "

        golog.log("DBG", query)
        db_data = await get_value_async(query)

        score_step1 = str(dict_tb[zone_fullname]["scores"][0])
        score_step2 = str(dict_tb[zone_fullname]["scores"][1])
        score_step3 = str(dict_tb[zone_fullname]["scores"][2])

        if db_data==None:
            if not zone_fullname in list_open_zones:
                #past zone not yet recorded, possible for guilds with manual updates
                # allow it
                pass

            query = "INSERT INTO tb_zones(tb_id, zone_id, zone_name, zone_phase, round, "\
                    "score_step1, score_step2, score_step3, is_bonus) "\
                    "VALUES("+tb_db_id+", '"+zone_fullname+"', '"+zone_shortname+"', "+zone_round+", "+round+", "\
                    ""+score_step1+", "+score_step2+", "+score_step3+", "+is_bonus+") "
            golog.log("DBG", query)
            await simple_execute_async(query)

            # Get the id of the new Zone
            query = "SELECT id FROM tb_zones " \
                    "WHERE tb_id="+tb_db_id+" "\
                    "AND zone_id='"+zone_fullname+"' "\
                    "AND round="+round+" "
            golog.log("DBG", query)
            zone_db_id = str(await get_value_async(query))
        else:
            zone_db_id = str(db_data)

        # Update current status of the zone
        #zone stars
        if "stars" in zone:
            zone_stars = zone["stars"]
        else:
            zone_stars = zone["completed_stars"]

        #zone scores (for the graph)
        score = min(int(score_step3), zone["score"])

        estimatedStrikeScore = 0
        if "estimatedStrikeScore" in zone:
            estimatedStrikeScore=zone["estimatedStrikeScore"]

        deployment=0
        if "deployment" in zone:
            deployment=zone["deployment"]

        maxStrikeScore=0
        if "maxStrikeScore" in zone:
            maxStrikeScore=zone["maxStrikeScore"]

        cmdMsg=zone["cmdMsg"]
        cmdCmd=zone["cmdCmd"]

        recon1_filled=zone["platoons"]["filling"][1]
        recon2_filled=zone["platoons"]["filling"][2]
        recon3_filled=zone["platoons"]["filling"][3]
        recon4_filled=zone["platoons"]["filling"][4]
        recon5_filled=zone["platoons"]["filling"][5]
        recon6_filled=zone["platoons"]["filling"][6]

        recon_cmdMsg=zone["platoons"]["cmdMsg"]
        recon_cmdCmd=zone["platoons"]["cmdCmd"]

        # Store current status of the zone for the batch UPDATE
        zone_updates.append((
            int(zone_db_id),
            score,
            estimatedStrikeScore,
            deployment,
            maxStrikeScore,
            cmdMsg,
            cmdCmd,
            recon1_filled,
            recon2_filled,
            recon3_filled,
            recon4_filled,
            recon5_filled,
            recon6_filled,
            recon_cmdMsg,
            recon_cmdCmd
        ))

        # breathe
        await asyncio.sleep(0)

    # Update all zones in one SQL statement
    if zone_updates:
        fields = [
            "score",
            "estimated_strikes",
            "estimated_deployments",
            "max_fights",
            "cmdMsg",
            "cmdCmd",
            "recon1_filled",
            "recon2_filled",
            "recon3_filled",
            "recon4_filled",
            "recon5_filled",
            "recon6_filled",
            "recon_cmdMsg",
            "recon_cmdCmd"
        ]

        cases = []

        for field_index, field in enumerate(fields, start=1):
            case = "CASE id "
            for update in zone_updates:
                zone_id = update[0]
                value = update[field_index]

                if field in ("cmdMsg", "recon_cmdMsg"):
                    value = (
                        str(value)
                        .replace("\\", "\\\\")
                        .replace("'", "''")
                    )
                    case += (
                        "WHEN " + str(zone_id) +
                        " THEN '" + value + "' "
                    )
                else:
                    case += (
                        "WHEN " + str(zone_id) +
                        " THEN " + str(value) + " "
                    )

            case += "END"
            cases.append(field + "=" + case)

        zone_ids = ",".join(str(update[0]) for update in zone_updates)

        query = (
            "UPDATE tb_zones SET "
            + ", ".join(cases)
            + " WHERE id IN (" + zone_ids + ")"
        )

        golog.log(
            "DBG",
            "Batch update of " + str(len(zone_updates)) + " TB zones"
        )
        rowcount = await simple_execute_async(query)
        golog.log("INFO", "Row count="+str(rowcount), identifier=guild_id)


    ## players
    # Get DB data
    query = "SELECT round, player_id, gp, deployed_gp, score_strikes, score_platoons, "\
            "score_deployed, strikes, waves "\
            "FROM tb_player_score "\
            "WHERE tb_id="+str(tb_db_id)
    golog.log("DBG", query)
    db_data = await get_table_async(query)
    if db_data == None:
        db_data = []
    dict_db_players = {}
    for line in db_data:
        round = line[0]
        p_id = line[1]
        p_data = line[3:] # gp is not included to prevent updating previous rounds when only gp moves
        dict_db_players[p_id+":"+str(round)] = p_data

    for player_name in dict_tb_players:
        player = dict_tb_players[player_name]
        id = player["id"]
        gp = player["mix_gp"]
        char_gp = player["char_gp"]
        ship_gp = player["ship_gp"]
        for round in range(1, len(player["rounds"])+1): # round from 1 to 6
            player_round = player["rounds"][round-1]
            deployed_gp = player_round["score"]["deployedMix"]
            score_strikes = player_round["score"]["strikes"]
            score_platoons = player_round["score"]["Platoons"]
            score_deployed = player_round["score"]["deployed"]
            strikes = player_round["strike_attempts"]
            waves = player_round["strike_waves"]

            player_key = id+":"+str(round)
            if not player_key in dict_db_players:
                #need to create player/round in DB
                query = "INSERT INTO tb_player_score(tb_id, round, player_id, "\
                        "gp, char_gp, ship_gp, deployed_gp, score_strikes, score_platoons, "\
                        "score_deployed, strikes, waves) "\
                        "VALUES("+str(tb_db_id)+", "+str(round)+", '"+id+"', "\
                        ""+str(gp)+", "+str(char_gp)+", "+str(ship_gp)+", "\
                        ""+str(deployed_gp)+", "+str(score_strikes)+", "\
                        ""+str(score_platoons)+", "+str(score_deployed)+", "\
                        ""+str(strikes)+", "+str(waves)+") "
                golog.log("DBG", query)
                await simple_execute_async(query)

            else:
                # player/round already exists
                #  need to see if necessary to update
                player_data = [deployed_gp, score_strikes, score_platoons, 
                               score_deployed, strikes, waves]
                if player_data != list(dict_db_players[player_key]):
                    query = "UPDATE tb_player_score "\
                            "SET gp="+str(gp)+", "\
                            "char_gp="+str(char_gp)+", "\
                            "ship_gp="+str(ship_gp)+", "\
                            "deployed_gp="+str(deployed_gp)+", "\
                            "score_strikes="+str(score_strikes)+", "\
                            "score_platoons="+str(score_platoons)+", "\
                            "score_deployed="+str(score_deployed)+", "\
                            "strikes="+str(strikes)+", "\
                            "waves="+str(waves)+" "\
                            "WHERE tb_id="+str(tb_db_id)+" "\
                            "AND player_id='"+id+"' "\
                            "AND round="+str(round)+" "
                    golog.log("DBG", query)
                    await simple_execute_async(query)

        #breathe
        await asyncio.sleep(0)

    return 0, ""

# Update tb_events table from list of events
# list_events my be actually a dictionary
async def store_tb_events(guild_id, tb_id, list_events):
    # Get the DB tb_id from the game tb_id and the guild_id
    query = (
        "SELECT id FROM tb_history "
        "WHERE tb_id=%s AND guild_id=%s"
    )

    tb_db_id = await get_value_async(
        query,
        (tb_id, guild_id)
    )

    if tb_db_id is None:
        return

    values = []

    for event in list_events:
        # Manage the case where list_events is a dict
        if isinstance(event, str):
            event = list_events[event]

        event_ts = int(event["timestamp"])
        author_id = event["authorId"]

        data = event["data"][0]
        activity = data["activity"]
        zone_data = activity["zoneData"]
        activity_log = zone_data["activityLogMessage"]

        event_type = activity_log["key"]
        zone_id = zone_data["zoneId"]
        params = activity_log.get("param", [])

        if "CONFLICT_CONTRIBUTION" in event_type:
            param0 = params[0]["paramValue"][0]
            param2 = params[2]["paramValue"][0]
            param3 = params[3]["paramValue"][0]

            values.append((
                tb_db_id,
                event_ts,
                "CONFLICT_CONTRIBUTION",
                zone_id,
                author_id,
                param0,
                param2,
                param3
            ))

        elif "COVERT_COMPLETE" in event_type:

            values.append((
                tb_db_id,
                event_ts,
                "COVERT_COMPLETE",
                zone_id,
                author_id,
                None,
                None,
                None
            ))

        elif "CONFLICT_DEPLOY" in event_type:
            param0 = params[0]["paramValue"][0]

            values.append((
                tb_db_id,
                event_ts,
                "CONFLICT_DEPLOY",
                zone_id,
                author_id,
                param0,
                None,
                None
            ))

        elif "RECON_CONTRIBUTION" in event_type:
            param0 = params[0]["paramValue"][0]
            param2 = params[2]["paramValue"][0]
            param3 = params[3]["paramValue"][0]

            values.append((
                tb_db_id,
                event_ts,
                "RECON_CONTRIBUTION",
                zone_id,
                author_id,
                param0,
                param2,
                param3
            ))

        # Give other asyncio tasks a chance to run
        await asyncio.sleep(0)

    if not values:
        return

    query = """
        INSERT IGNORE INTO tb_events
        (
            tb_id,
            timestamp,
            event_type,
            zone_id,
            author_id,
            param0,
            param2,
            param3
        )
        VALUES (
            %s,
            FROM_UNIXTIME(%s * 0.001),
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
    """
    golog.log("INFO", query, identifier=guild_id)

    rowcount = await executemany_async(query, values)

    golog.log("INFO", "Row count="+str(rowcount), identifier=guild_id)

# store patoon progress
# this helps checking platoons in case same player has to put
#  same toon in same platoon 2 days in a row
async def update_tb_platoons(guild_id, tb_id, tb_round, dict_platoons_done):
    ##################################
    # Whole TB data
    ##################################
    # Get the TB in DB
    query = "SELECT id FROM tb_history " \
            "WHERE tb_id='"+tb_id+"' "\
            "AND guild_id='"+guild_id+"' "
    golog.log("DBG", query)
    db_data = await get_value_async(query)

    if db_data==None:
        #wait for TB to be created
        golog.log("WAR", "TB "+tb_id+" does not exist for guild "+guild_id)
        return

    tb_db_id = db_data

    ##################################
    # Get stored platoons
    ##################################
    query = "SELECT platoon_name, unit_name, player_name "\
            "FROM tb_platoons "\
            "WHERE tb_id="+str(tb_db_id)
    golog.log("DBG", query)
    db_data = await get_table_async(query)
    if db_data is None:
        db_data = []

    # Store existing combinations so we can quickly detect new ones.
    existing_platoons = {
        (line[0], line[1], line[2])
        for line in db_data
    }

    ##################################
    # Build rows to insert
    ##################################

    values = []

    for platoon_name, units in dict_platoons_done.items():
        for unit_name, player_names in units.items():
            for player_name in player_names:

                # Do not store empty player names.
                if player_name == "":
                    continue

                key = (platoon_name, unit_name, player_name)

                if key in existing_platoons:
                    continue

                values.append((
                    tb_db_id,
                    tb_round[-1],
                    platoon_name,
                    unit_name,
                    player_name
                ))

                # Also add it locally so duplicate entries in
                # dict_platoons_done cannot generate duplicate INSERTs.
                existing_platoons.add(key)

    ##################################
    # Insert all new platoons at once
    ##################################

    if values:
        query = """
            INSERT INTO tb_platoons
                (tb_id, round, platoon_name, unit_name, player_name)
            VALUES (%s, %s, %s, %s, %s)
        """

        golog.log(
            "INFO",
            "Inserting " + str(len(values)) + " new platoon assignments"
        )

        rowcount = await executemany_async(query, values)

        golog.log("INFO", "Row count="+str(rowcount), identifier=guild_id)

    return

#################################
# update TW in DB
async def update_tw(guild_id, tw_id, opp_guild_id, opp_guild_name, score, opp_score,
              homeGuild, awayGuild):
    dict_tw = data.dict_tw

    # Check / Create the TW in DB
    query = "SELECT id FROM tw_history " \
            "WHERE tw_id='"+tw_id+"' "\
            "AND guild_id='"+guild_id+"' "
    golog.log("DBG", query)
    db_data = await get_value_async(query)

    if db_data==None:
        # Create TW in tw_history
        tw_ts = int(tw_id.split(":")[1][1:-3])
        tw_date = datetime.datetime.fromtimestamp(tw_ts).strftime("%Y/%m/%d %H:%M:%S")
        query = "INSERT INTO tw_history(tw_id, start_date, guild_id, " \
                "away_guild_id, away_guild_name, homeScore, awayScore) " \
                "VALUES('"+tw_id+"', '"+tw_date+"', '"+guild_id+"', " \
                "'"+opp_guild_id+"', '"+opp_guild_name.replace("'", "''")+"', "\
                ""+str(score)+", "+str(opp_score)+") "
        golog.log("DBG", query)
        await simple_execute_async(query)

        # Get TB id
        query = "SELECT id FROM tw_history " \
                "WHERE tw_id='"+tw_id+"' "\
                "AND guild_id='"+guild_id+"' "
        golog.log("DBG", query)
        tw_db_id = await get_value_async(query)
    else:
        # Update existing TW
        tw_db_id = str(db_data)
        query = "UPDATE tw_history "\
                "SET lastUpdated=CURRENT_TIMESTAMP(), "\
                "    homeScore="+str(score)+", "\
                "    awayScore="+str(opp_score)+" "\
                "WHERE id="+str(tw_db_id)
        golog.log("DBG", query)
        await simple_execute_async(query)

    # Get DB TW zones
    query = "SELECT id, side, zone_name, size, filled, victories, fails FROM tw_zones " \
            "WHERE tw_id="+str(tw_db_id)
    golog.log("DBG", query)
    db_data = await get_table_async(query)
    if db_data==None:
        db_data=[]

    # Transform into dictionary
    dict_tw_zones = {'home': {}, 'away': {}}
    for line in db_data:
        zone_id = line[0]
        side = line[1]
        zone_name = line[2]
        size = line[3]
        filled = line[4]
        victories = line[5]
        fails = line[6]
        if not zone_name in dict_tw_zones[side]:
            dict_tw_zones[side][zone_name] = [zone_id, size, filled, victories, fails]

    for [side, guild] in [["home", homeGuild], ["away", awayGuild]]:
        zones = guild['list_territories']
        for zone in zones:
            zone_name = zone[0]
            size = zone[1]
            filled = zone[2]
            victories = zone[3]
            fails = zone[4]
            commandMsg = zone[5]
            status = zone[6]
            zoneState = zone[7]
            zone_id = dict_tw[zone_name]

            if commandMsg == None:
                cmdMsg_txt = "NULL"
            else:
                cmdMsg_txt = "'"+commandMsg.replace("'", "''")+"'"
            if status == None:
                status_txt = "NULL"
            else:
                status_txt = "'"+status+"'"
            if zoneState == None:
                zoneState_txt = "NULL"
            else:
                zoneState_txt = "'"+zoneState+"'"

            if not zone_name in dict_tw_zones[side]:
                query = "INSERT INTO tw_zones(tw_id, side, zone_id, zone_name, size, "\
                        "filled, victories, fails, commandMsg, status, zoneState) "\
                        "VALUES("+str(tw_db_id)+", '"+side+"', '"+zone_id+"', "\
                        "'"+zone_name+"', "+str(size)+", "\
                        ""+str(filled)+", "+str(victories)+", "+str(fails)+", "\
                        ""+cmdMsg_txt+", "\
                        ""+status_txt+", "\
                        ""+zoneState_txt+") "
                golog.log("DBG", query)
                await simple_execute_async(query)

                # Get the id of the new Zone
                query = "SELECT id FROM tw_zones " \
                        "WHERE tw_id="+str(tw_db_id)+" "\
                        "AND side='"+side+"' "\
                        "AND zone_id='"+zone_id+"' "
                golog.log("DBG", query)
                zone_db_id = str(await get_value_async(query))

            else:
                zone_db_id = dict_tw_zones[side][zone_name][0]
                # Update current status of the zone
                query = "UPDATE tw_zones "\
                        "SET filled="+str(filled)+",  "\
                        "    victories="+str(victories)+", "\
                        "    fails="+str(fails)+", "\
                        "    commandMsg="+cmdMsg_txt+", "\
                        "    status="+status_txt+", "\
                        "    zoneState="+zoneState_txt+" "\
                        "WHERE id="+str(zone_db_id)+" "
                golog.log("DBG", query)
                await simple_execute_async(query)

            # breathe
            await asyncio.sleep(0)

        # Get squads in DB
        query = "SELECT id, zone_name, player_name, is_beaten, fights, gp, datacron_id "\
                "FROM tw_squads "\
                "WHERE tw_id="+str(tw_db_id)+" "\
                "AND side='"+side+"'"
        golog.log("DBG", query)
        db_data = await get_table_async(query)
        if db_data == None:
            db_data = []

        dict_tw_squads = {}
        for line in db_data:
            squad_id = line[0]
            zone_name = line[1]
            player_name = line[2]
            is_beaten = line[3]
            fights = line[4]
            gp = line[5]
            datacron_id = line[6]
            dict_tw_squads[squad_id] = [zone_name, player_name, 
                                        is_beaten, fights, gp,
                                        datacron_id]

        # Now get RPC data and compare with DB, create/insert if necessary
        squads = guild['list_defenses']
        for squad in squads:
            zone_name = squad["zone_short_name"]
            player_name = squad["player_name"]
            cells = squad["list_defId"]
            is_beaten = squad["is_beaten"]
            fights = squad["fights"]
            squad_gp = squad["team_gp"]
            squad_id = squad["squad_id"]
            datacron_id = squad["datacron_id"]
            if datacron_id==None:
                datacron_id_txt="NULL"
            else:
                datacron_id_txt="'"+datacron_id+"'"

            # Check / create squads in DB
            if not squad_id in dict_tw_squads:
                query = "INSERT INTO tw_squads(id, tw_id, side, zone_name, player_name, "\
                        "is_beaten, fights, gp, datacron_id) "\
                        "VALUES('"+squad_id+"', "+str(tw_db_id)+", '"+side+"', "\
                        "'"+zone_name+"', '"+player_name.replace("'", "''")+"', "\
                        ""+str(is_beaten)+", "+str(fights)+", "+str(squad_gp)+", "\
                        ""+datacron_id_txt+")"
                golog.log("DBG", query)
                await simple_execute_async(query)
            else:
                # update
                if [is_beaten, fights] != dict_tw_squads[squad_id][2:4]:
                    query = "UPDATE tw_squads "\
                            "SET is_beaten="+str(is_beaten)+", "\
                            "fights="+str(fights)+" "\
                            "WHERE id='"+squad_id+"' "
                    golog.log("DBG", query)
                    await simple_execute_async(query)

            # Check / create squad cells in DB
            cellIndex = 0
            for cell in cells:
                defId = cell["unitDefId"]
                level = cell["level"]
                tier = cell["gear"]
                unitRelicTier = cell["relic"]
                zetaCount = cell["zetaCount"]
                omicronCount = cell["omicronCount"]

                if not squad_id in dict_tw_squads:
                    query = "INSERT INTO tw_squad_cells(tw_id, squad_id, "\
                            "defId, cellIndex, level, tier, unitRelicTier, "\
                            "zetaCount, omicronCount) "\
                            "VALUES("+str(tw_db_id)+", '"+squad_id+"', "\
                            "'"+defId+"', "\
                            ""+str(cellIndex)+", "\
                            ""+str(level)+", "\
                            ""+str(tier)+", "\
                            ""+str(unitRelicTier)+", "\
                            ""+str(zetaCount)+", "\
                            ""+str(omicronCount)+") "
                    golog.log("DBG", query)
                    await simple_execute_async(query)

                cellIndex += 1

            # breathe
            await asyncio.sleep(0)

    return 0, ""

###########################################
# Update tw_events table from list of events
# list_events my be actually a dictionary
async def store_tw_events(guild_id, tw_id, list_events):
    # Get the DB tw_id from the game tw_id and the guild_id
    query = (
        "SELECT id FROM tw_history "
        "WHERE tw_id=%s AND guild_id=%s"
    )

    tw_db_id = await get_value_async(
        query,
        (tw_id, guild_id)
    )

    if tw_db_id==None:
        # TW not registered yet, wait for next time
        return

    values = []

    for event in list_events:
        #Manage the case where list_events is a dict
        if isinstance(event, str):
            event = list_events[event]

        event_ts = int(event["timestamp"]) # to prevent values like 1737416568.6330001
        author_id = event["authorId"]

        data=event["data"][0]
        activity=data["activity"]
        zone_data = activity["zoneData"]
        activity_log = zone_data["activityLogMessage"]

        event_type = activity_log["key"]
        zone_id = zone_data["zoneId"]

        if "DEPLOY" in activity_log["key"]:
            if zone_data["instanceType"] == "ZONEINSTANCEHOME":
                warSquad = activity["warSquad"]
                squad_id = warSquad["squadId"]
                leader_id = warSquad["squad"]["cell"][0]["unitDefId"]
                squad_size = len(warSquad["squad"]["cell"])

                values.append((
                    tw_db_id,
                    event_ts,
                    "DEPLOY",
                    zone_id,
                    author_id,
                    squad_id,
                    None,
                    leader_id,
                    squad_size,
                    None,
                    None,
                    None,
                    None
                ))

                """
                query = "INSERT IGNORE INTO tw_events(tw_id, timestamp, event_type, zone_id, "\
                        "author_id, squad_id, squad_leader) "\
                        "VALUES("+str(tw_db_id)+", "\
                        "FROM_UNIXTIME("+str(event_ts*0.001)+"), "\
                        "'DEPLOY', "\
                        "'"+zone_id+"', "\
                        "'"+author_id+"', "\
                        "'"+squad_id+"', "\
                        "'"+leader_id+"') "
                golog.log("DBG", query)
                await simple_execute_async(query)
                """

        elif "warSquad" in activity:
            warSquad = activity["warSquad"]
            squad_id = warSquad["squadId"]
            event_type = warSquad["squadStatus"]
            if "squad" in warSquad:
                squad_player_id=warSquad["playerId"]
                leader_id = warSquad["squad"]["cell"][0]["unitDefId"]
                squad_size = len(warSquad["squad"]["cell"])
                
                count_dead=0
                remaining_tm=False
                for cell in warSquad["squad"]["cell"]:
                    if cell["unitState"]["healthPercent"] == "0":
                        count_dead+=1
                    if cell["unitState"]["turnPercent"] != "0":
                        remaining_tm=True

                values.append((
                    tw_db_id,
                    event_ts,
                    event_type,
                    zone_id,
                    author_id,
                    squad_id,
                    squad_player_id,
                    leader_id,
                    squad_size,
                    count_dead,
                    remaining_tm,
                    None,
                    None
                ))

                """
                query = "INSERT IGNORE INTO tw_events(tw_id, timestamp, event_type, zone_id, "\
                        "author_id, squad_id, squad_player_id, squad_leader, "\
                        "squad_size, squad_dead, squad_tm) "\
                        "VALUES("+str(tw_db_id)+", "\
                        "FROM_UNIXTIME("+str(event_ts*0.001)+"), "\
                        "'"+event_type+"', "\
                        "'"+zone_id+"', "\
                        "'"+author_id+"', "\
                        "'"+squad_id+"', "\
                        "'"+squad_player_id+"', "\
                        "'"+leader_id+"', "\
                        ""+str(squad_size)+", "\
                        ""+str(count_dead)+", "\
                        ""+str(int(remaining_tm))+") "
                golog.log("DBG", query)
                await simple_execute_async(query)
                """

            else: # no squad, only squad_id
                values.append((
                    tw_db_id,
                    event_ts,
                    event_type,
                    zone_id,
                    author_id,
                    squad_id,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None
                ))

                """
                query = "INSERT IGNORE INTO tw_events(tw_id, timestamp, event_type, zone_id, "\
                        "author_id, squad_id) "\
                        "VALUES("+str(tw_db_id)+", "\
                        "FROM_UNIXTIME("+str(event_ts*0.001)+"), "\
                        "'"+event_type+"', "\
                        "'"+zone_id+"', "\
                        "'"+author_id+"', "\
                        "'"+squad_id+"') "
                golog.log("DBG", query)
                await simple_execute_async(query)
                """


        else: # no warSquad > score event
            if not "scoreDelta" in activity["zoneData"]:
                golog.log("WAR", "no scoreDelta in "+str(event))
            scoreDelta = 0
            scoreTotal = activity["zoneData"]["scoreTotal"]

            values.append((
                tw_db_id,
                event_ts,
                "SCORE",
                zone_id,
                author_id,
                None,
                None,
                None,
                None,
                None,
                None,
                scoreDelta,
                scoreTotal
            ))

            """
            query = "INSERT IGNORE INTO tw_events(tw_id, timestamp, event_type, zone_id, "\
                    "author_id, scoreDelta, scoreTotal) "\
                    "VALUES("+str(tw_db_id)+", "\
                    "FROM_UNIXTIME("+str(event_ts*0.001)+"), "\
                    "'SCORE', "\
                    "'"+zone_id+"', "\
                    "'"+author_id+"', "\
                    ""+scoreDelta+", "\
                    ""+scoreTotal+") "
            golog.log("DBG", query)
            await simple_execute_async(query)
            """

        # breathe
        await asyncio.sleep(0)

    if not values:
        return

    query = """
        INSERT IGNORE INTO tw_events
        (
            tw_id,
            timestamp,
            event_type,
            zone_id,
            author_id,
            squad_id,
            squad_player_id,
            squad_leader,
            squad_size,
            squad_dead,
            squad_tm,
            scoreDelta,
            scoreTotal
        )
        VALUES (
            %s,
            FROM_UNIXTIME(%s * 0.001),
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s
        )
    """
    golog.log("INFO", query, identifier=guild_id)

    rowcount = await executemany_async(query, values)

    golog.log("INFO", "Row count="+str(rowcount), identifier=guild_id)

async def update_guild(dict_guild):
    guild_id = dict_guild["profile"]["id"]
    if "territoryBattleResult" in dict_guild:
        for tbr in dict_guild["territoryBattleResult"]:
            tb_id = tbr["instanceId"]
            tb_stars = tbr["totalStars"]
            query = "UPDATE tb_history SET stars_final="+tb_stars+" "\
                    "WHERE guild_id='"+guild_id+"' "\
                    "AND tb_id='"+tb_id+"' "
            golog.log("DBG", query)
            await simple_execute_async(query)

async def update_extguild(dict_guild):
    guild_id = dict_guild["profile"]["id"]
    if "recentTerritoryWarResult" in dict_guild:
        for twr in dict_guild["recentTerritoryWarResult"]:
            tw_endtime = twr["endTimeSeconds"]
            tw_warid = twr["territoryWarId"]
            tw_score = twr["score"]
            tw_oppscore = twr["opponentScore"]

            tw_starttime = int(tw_endtime)-24*3600
            tw_starttime = round(tw_starttime/3600)*3600 #because some end times are 19:01 instaed of 19:00, but start time are always right
            tw_letter = tw_warid[-1]
            tw_id = "TERRITORY_WAR_EVENT_"+tw_letter+":O"+str(tw_starttime)+"000"

            query = "UPDATE tw_history SET homeScore="+tw_score+", "\
                    "awayScore="+tw_oppscore+" "\
                    "WHERE guild_id='"+guild_id+"' "\
                    "AND tw_id='"+tw_id+"' "
            golog.log("DBG", query)
            await simple_execute_async(query)


