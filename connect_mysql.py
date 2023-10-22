import os
import config
import sys
import urllib.parse
import mysql.connector
from mysql.connector import MySQLConnection, Error
import datetime
import time
import wcwidth
import asyncio

def wc_ljust(text, length):
    return text + ' ' * max(0, length - wcwidth.wcswidth(text))

import goutils
import connect_crinolo
import data
import go

mysql_db = None

def db_connect():
    global mysql_db
    #mysql_db = None
    if mysql_db == None or not mysql_db.is_connected():
        if mysql_db == None:
            goutils.log2("INFO", "First connection to mysql")
        else:
            goutils.log2("INFO", "Close connection to mysql")
            mysql_db.close()
            goutils.log2("INFO", "New connection to mysql")
            
        # Recover DB information from URL
        urllib.parse.uses_netloc.append('mysql')
        try:
            url = urllib.parse.urlparse(config.MYSQL_DATABASE_URL)
        except Exception:
            goutils.log2("ERR", 'Unexpected error in connect:', sys.exc_info())
            return
        
        # Connect to DB
        mysql_db = None
        try:
            goutils.log2("INFO", 'Connecting to MySQL database...')
            mysql_db = mysql.connector.connect(host=url.hostname,
                                           database=url.path[1:],
                                           user=url.username,
                                           password=url.password)
            if mysql_db.is_connected():
                # print('Connected to MySQL database')
                pass
            else:
                goutils.log2("ERR", 'Connection failed')

        except Error as e:
            goutils.log2("ERR", 'Exception during connect: '+str(e))
            
    return mysql_db
        
def update_guild_teams(guild_name, dict_team):
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
    cursor = None
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)

        guild_teams_txt = ""
        # "JKR;None/Requis;4|JEDIKNIGHTREVAN;6;11;7;12;vit;capa;mod;pg;Chef,Unique1|BASTILA.../Important;1|GENERALKENOBI...\DR/Requis..."
        
        for team_name in dict_team:
            team_rarity = dict_team[team_name]["rarity"]
            if team_rarity == '':
                team_rarity = 0
            team = dict_team[team_name]["categories"]
            
            subteams_txt = ""
            # Requis;4|JEDIKNIGHTREVAN;6;11;7;12;vit;capa;mod;pg;Chef,Unique1|BASTILA.../Important...
            for sub_team in team:
                subteam_name = sub_team[0]
                subteam_min = sub_team[1]
                subteam_toons = sub_team[2]
                
                toons_txt = ""
                # JEDIKNIGHTREVAN;6;11;7;12;vit;capa;mod;pg;Chef,Unique1|BASTILA...
                for toon_id in subteam_toons:
                    toon = subteam_toons[toon_id]
                    toon_rarity_min = toon[1]
                    toon_gear_min = toon[2]
                    toon_rarity_reco = toon[3]
                    toon_gear_reco = toon[4]
                    
                    toon_zetas = ''
                    for zeta in toon[5].split(","):
                        zeta_id = goutils.get_capa_id_from_short(toon_id, zeta)
                        toon_zetas += zeta_id+","
                    if len(toon_zetas)>0:
                        toon_zetas = toon_zetas[:-1]

                    toon_omicrons = ''
                    for omicron in toon[6].split(","):
                        omicron_id = goutils.get_capa_id_from_short(toon_id, omicron)
                        toon_omicrons += omicron_id+","
                    if len(toon_omicrons)>0:
                        toon_omicrons = toon_omicrons[:-1]
                    
                    toons_txt += toon_id + ";" + \
                                 str(toon_rarity_min) + ";" + \
                                 str(toon_gear_min) + ";" + \
                                 str(toon_rarity_reco) + ";" + \
                                 str(toon_gear_reco) + ";" + \
                                 str(toon_zetas) + ";" + \
                                 str(toon_omicrons) + "|"
                
                # remove last "|"
                toons_txt = toons_txt[:-1]
                
                subteams_txt += subteam_name + ";" + \
                                str(subteam_min) + "|" + \
                                toons_txt + "/"

            # remove last "/"
            subteams_txt = subteams_txt[:-1]
            
            guild_teams_txt += team_name + ";" \
                             + str(team_rarity) + "/" \
                             + subteams_txt + "\\"
       
        # remove last "\"
        subteams_txt = subteams_txt[:-1]

            
        # Launch the unique update with all information
        query_parameters = (guild_name, guild_teams_txt)
        goutils.log2("DBG", query_parameters)
        #print("CALL update_guild_teams"+str(query_parameters))
        cursor.callproc('update_guild_teams', query_parameters)
        
        mysql_db.commit()
    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        
    finally:
        if cursor != None:
            cursor.close()

def text_query(query):
    rows = []
    cursor = None

    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)
        
        results = cursor.execute(query, multi=True)
        #print("results: "+str(results))
        for cur in results:
            #print("cur: "+str(cur))
            # rows.append('cursor: '+ str(cur))
            if cur.with_rows:
                fetch_results = cur.fetchall()
            
                if len(fetch_results) >0:
                    widths = []
                    columns = []
                    tavnit = '|'
                    separator = '+' 
                
                    index = 0
                    for cd in cur.description:
                        #print("fetch_results: "+str(fetch_results))
                        max_col_length = max(list(map(lambda x: wcwidth.wcswidth(str(x[index])), fetch_results)))
                        widths.append(max(max_col_length, wcwidth.wcswidth(cd[0])))
                        columns.append(cd[0])
                        index+=1

                    for w in widths:
                        tavnit += " %-"+"%s.%ss |" % (w,w)
                        separator += '-'*w + '--+'

                    rows.append(separator)
                    rows.append(tavnit % tuple(columns))
                    rows.append(separator)

                    for fetch in fetch_results:
                        index=0
                        row = "|"
                        for value in fetch:
                            row += " " + wc_ljust(str(value), widths[index]) + " |"
                            index+=1
                        rows.append(row)

                    rows.append(separator)
        
        mysql_db.commit()
    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        rows=[error]
        
    finally:
        if cursor != None:
            cursor.close()
    
    return rows
        
        
def simple_execute(query):
    cursor = None
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)
        #print("simple_callproc: "+proc_name+" "+str(args))
        ret=cursor.execute(query)
        
        mysql_db.commit()
    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        
    finally:
        if cursor != None:
            cursor.close()

def simple_callproc(proc_name, args):
    rows = []
    tuples = []
    cursor = None
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)
        #print("simple_callproc: "+proc_name+" "+str(args))
        ret=cursor.callproc(proc_name, args)
        #print(ret)
        
        mysql_db.commit()
    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        
    finally:
        if cursor != None:
            cursor.close()

def get_value(query):
    tuples = []
    cursor = None
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)
        
        results = cursor.execute(query, multi=True)
        for cur in results:
            # rows.append('cursor: '+ str(cur))
            if cur.with_rows:
                results = cur.fetchall()
                tuples.append(results)

    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        
    finally:
        if cursor != None:
            cursor.close()
    
    if len(tuples[0]) > 0:
        return tuples[0][0][0]
    else:
        return None
        
def get_column(query):
    tuples = []
    cursor = None
    try:
        mysql_db = db_connect()
        #print("DBG: mysql_db="+str(mysql_db))
        cursor = mysql_db.cursor(buffered=True)
        #print("DBG: cursor="+str(cursor))
        
        results = cursor.execute(query, multi=True)
        for cur in results:
            # rows.append('cursor: '+ str(cur))
            if cur.with_rows:
                results = cur.fetchall()
                tuples.append(results)

    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        
    finally:
        if cursor != None:
            cursor.close()

    return [x[0] for x in tuples[0]]
    
def get_line(query):
    tuples = []
    cursor = None
    #print("get_line("+query+")")
    try:
        mysql_db = db_connect()
        #print("DBG: mysql_db="+str(mysql_db))
        cursor = mysql_db.cursor(buffered=True)
        #print("DBG: cursor="+str(cursor))
        
        results = cursor.execute(query, multi=True)
        for cur in results:
            # rows.append('cursor: '+ str(cur))
            if cur.with_rows:
                results = cur.fetchall()
                tuples.append(results)

    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        
    finally:
        if cursor != None:
            cursor.close()
    
    if len(tuples[0]) == 0:
        return None
    else:
        return tuples[0][0]
    
def get_table(query):
    tuples = []
    cursor = None
    try:
        #print("DBG: get_table db_connect")
        mysql_db = db_connect()
        #print("DBG: get_table cursor")
        #print("DBG: mysql_db="+str(mysql_db))
        cursor = mysql_db.cursor(buffered=True)
        #print("DBG: cursor="+str(cursor))

        # print("DBG: get_table execute "+query)
        results = cursor.execute(query, multi=True)
        for cur in results:
            # rows.append('cursor: '+ str(cur))
            if cur.with_rows:
                #print("DBG: get_table fetchall")
                results = cur.fetchall()
                tuples.append(results)

    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        
    finally:
        if cursor != None:
            cursor.close()

    #print("DBG: get_table return")
    if len(tuples[0]) == 0:
        return None
    else:
        return tuples[0]

def insert_roster_evo(allyCode, defId, evo_txt):
    cursor = None
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)

        query = "INSERT INTO roster_evolutions(allyCode, defId, description) "\
               +"VALUES("+str(allyCode)+", '"+defId+"', '"+evo_txt+"')"
        goutils.log2("DBG", query)
        cursor.execute(query)

        mysql_db.commit()
    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        return -1
        
    finally:
        if cursor != None:
            cursor.close()
    
async def update_player(dict_player):
    dict_unitsList = data.get("unitsList_dict.json")
    dict_modList = data.get("modList_dict.json")
    dict_capas = data.get("unit_capa_list.json")
    dict_stats = data.get("dict_stats.json")
    cursor = None
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor()
        
        # Update basic player information
        p_allyCode = dict_player["allyCode"]
        p_playerId = dict_player["playerId"]
        if "guildId" in dict_player:
            p_guildId = dict_player["guildId"]
            p_guildName = dict_player["guildName"]
        else:
            p_guildId = ""
            p_guildName = ""

        p_lastActivity_player = int(dict_player["lastActivityTime"])
        p_lastActivity_ts = datetime.datetime.fromtimestamp(p_lastActivity_player/1000)
        p_lastActivity = p_lastActivity_ts.strftime('%Y-%m-%d %H:%M:%S')

        p_level = dict_player['level']
        p_name = dict_player['name']

        # SQUAD and FLEET arenas
        p_arena_char_rank = None
        p_arena_ship_rank = None
        for arena in dict_player['pvpProfile']:
            if arena["type"] == "SQUADARENA":
                p_arena_char_rank = arena["rank"]
            elif arena["type"] == "FLEETARENA":
                p_arena_ship_rank = arena["rank"]
        p_arena_char_rank_txt = ("NULL" if p_arena_char_rank == None else str(p_arena_char_rank))
        p_arena_ship_rank_txt = ("NULL" if p_arena_ship_rank == None else str(p_arena_ship_rank))

        #GAC
        if "playerRating" in dict_player and "playerRankStatus" in dict_player["playerRating"]:
            p_grand_arena_league = dict_player['playerRating']["playerRankStatus"]['leagueId']
            p_grand_arena_division = 6 - int(dict_player['playerRating']["playerRankStatus"]['divisionId']/5)
            p_grand_arena_rating = int(dict_player['playerRating']["playerSkillRating"]['skillRating'])
        else:
            p_grand_arena_league = ""
            p_grand_arena_division = 0
            p_grand_arena_rating = 0
        p_grand_arena_rank = p_grand_arena_league + str(p_grand_arena_division)

        for stat in dict_player["profileStat"]:
            if stat['nameKey'] == "STAT_CHARACTER_GALACTIC_POWER_ACQUIRED_NAME":
                p_char_gp = stat['value']
            elif stat['nameKey'] == "STAT_SHIP_GALACTIC_POWER_ACQUIRED_NAME":
                p_ship_gp = stat['value']

        p_poUTCOffsetMinutes = dict_player['localTimeZoneOffsetMinutes']

        query = "INSERT IGNORE INTO players(allyCode) "\
               +"VALUES("+str(p_allyCode)+")"
        #goutils.log2("DBG", query)
        cursor.execute(query)

        query = "UPDATE players "\
               +"SET guildId = '"+p_guildId+"', "\
               +"    guildName = '"+p_guildName.replace("'", "''")+"', "\
               +"    playerId = '"+p_playerId+"', "\
               +"    lastActivity = '"+p_lastActivity+"', "\
               +"    level = "+str(p_level)+", "\
               +"    name = '"+str(p_name).replace("'", "''")+"', "\
               +"    char_gp = "+str(p_char_gp)+", "\
               +"    ship_gp = "+str(p_ship_gp)+", "\
               +"    arena_char_rank = "+ p_arena_char_rank_txt +", "\
               +"    arena_ship_rank = "+ p_arena_ship_rank_txt +", "\
               +"    grand_arena_rank = '"+ p_grand_arena_rank +"', "\
               +"    grand_arena_rating = "+ str(p_grand_arena_rating) +", "\
               +"    poUTCOffsetMinutes = "+str(p_poUTCOffsetMinutes)+", "\
               +"    lastUpdated = CURRENT_TIMESTAMP "\
               +"WHERE allyCode = "+str(p_allyCode)
        goutils.log2("DBG", query)
        cursor.execute(query)

        # Update the roster
        #goutils.log2("DBG", "update "+str(len(dict_player["rosterUnit"]))+" character(s)")
        for character_id in dict_player["rosterUnit"]:
            character = dict_player["rosterUnit"][character_id]
            c_defId = character_id
            c_combatType = dict_unitsList[character_id]['combatType']
            c_forceAlignment = dict_unitsList[c_defId]['forceAlignment']
            c_gear = character['currentTier']
            if not "gp" in character:
                goutils.log2("ERR", p_playerId+":"+character_id)
            c_gp = character['gp']
            c_level = character['currentLevel']
            c_rarity = character['currentRarity']
            
            c_relic_currentTier = 0
            if "relic" in character:
                c_relic_currentTier = character['relic']['currentTier']

            #launch query to update roster element, with stats
            query = "INSERT IGNORE INTO roster(allyCode, defId) "\
                   +"VALUES("+str(p_allyCode)+", '"+c_defId+"')"
            #goutils.log2("DBG", query)
            cursor.execute(query)

            query = "UPDATE roster "\
                   +"SET allyCode = "+str(p_allyCode)+", "\
                   +"    defId = '"+c_defId+"', "\
                   +"    combatType = "+str(c_combatType)+", "\
                   +"    forceAlignment = "+str(c_forceAlignment)+", "\
                   +"    gear = "+str(c_gear)+", "\
                   +"    gp = "+str(c_gp)+", "\
                   +"    level = "+str(c_level)+", "\
                   +"    rarity = "+str(c_rarity)+", "\
                   +"    relic_currentTier = "+str(c_relic_currentTier)+" "

            equipment = [False, False, False, False, False, False]
            if "equipment" in character:
                for eqpt in character["equipment"]:
                    equipment[eqpt["slot"]] = True
            eqpt_txt = ""
            for i in range(6):
                if equipment[i]:
                    eqpt_txt += "1"
                else:
                    eqpt_txt += "0"

            query += ",equipment = '"+eqpt_txt+"' "

            if "stats" in character:
                for stat_id in ['1', '5', '6', '7', '14', '15', '16', '17', '18', '28']:
                    stat_value = 0
                    if stat_id in character["stats"]["final"]:
                        stat_value = character["stats"]["final"][stat_id]
                    
                    query += ",stat"+stat_id+" = "+str(stat_value)+" "

                if "mods" in character["stats"]:
                    for stat_id in ['1', '5', '6', '7', '14', '15', '16', '17', '18', '28']:
                        stat_value = None

                        if stat_id in ['14', '15']:
                            #mod stats for 14 and 15 are actually 21 and 22
                            stat_mod_id = str(int(stat_id)+7)
                        elif stat_id in ['39', '40']:
                            #mod stats for 39 and 40 are actually 35 and 36
                            stat_mod_id = str(int(stat_id)-4)
                        else:
                            stat_mod_id = stat_id

                        if stat_mod_id in character["stats"]["mods"]:
                            stat_value = character["stats"]["mods"][stat_mod_id]
                        if stat_value==None:
                            stat_value="0"
                        
                        query += ",mod"+stat_id+" = "+str(stat_value)+" "

            query +="WHERE allyCode = "+str(p_allyCode)+" "\
                   +"AND   defId = '"+c_defId+"'"

            #goutils.log2("DBG", query)
            cursor.execute(query)
            mysql_db.commit()

            #Get DB index roster_id for next queries
            query = "SELECT id FROM roster WHERE allyCode = "+str(p_allyCode)+" AND defId = '"+c_defId+"'"
            #goutils.log2("DBG", query)
            roster_id = get_value(query)
            #goutils.log2("DBG", "roster_id="+str(roster_id))

            #Get existing mod IDs from DB
            query = "SELECT id FROM mods WHERE roster_id = "+str(roster_id)
            #goutils.log2("DBG", query)
            previous_mods_ids = get_column(query)
            #goutils.log2("DBG", previous_mods_ids)

            ## GET DEFINITION OF MODS ##
            current_mods_ids = []
            if 'equippedStatMod' in character:
                for mod in character['equippedStatMod']:
                    mod_id = mod['id']
                    mod_defId = mod['definitionId']
                    mod_level = mod['level']
                    mod_pips = dict_modList[mod["definitionId"]]['rarity']
                    mod_primaryStat_unitStat = mod['primaryStat']["stat"]['unitStatId']
                    if dict_stats[str(mod_primaryStat_unitStat)]["isDecimal"]:
                        mod_primaryStat_value = int(mod['primaryStat']["stat"]['statValueDecimal'])/100
                    else:
                        mod_primaryStat_value = int(mod['primaryStat']["stat"]['statValueDecimal'])/10000
                    
                    mod_secondaryStat_unitStats=[]
                    mod_secondaryStat_values=[]
                    mod_secondaryStat1_unitStat=0
                    mod_secondaryStat1_value=0
                    mod_secondaryStat2_unitStat=0
                    mod_secondaryStat2_value=0
                    mod_secondaryStat3_unitStat=0
                    mod_secondaryStat3_value=0
                    mod_secondaryStat4_unitStat=0
                    mod_secondaryStat4_value=0
                    for sec_stat in mod['secondaryStat']:
                        mod_secondaryStat_unitStats.append(sec_stat["stat"]["unitStatId"])
                        if dict_stats[str(sec_stat["stat"]["unitStatId"])]["isDecimal"]:
                            sec_stat_value = int(sec_stat["stat"]["statValueDecimal"])/100
                        else:
                            sec_stat_value = int(sec_stat["stat"]["statValueDecimal"])/10000
                        mod_secondaryStat_values.append(sec_stat_value)

                    if len(mod_secondaryStat_unitStats)>0:
                        mod_secondaryStat1_unitStat = mod_secondaryStat_unitStats[0]
                        mod_secondaryStat1_value = mod_secondaryStat_values[0]
                    if len(mod_secondaryStat_unitStats)>1:
                        mod_secondaryStat2_unitStat = mod_secondaryStat_unitStats[1]
                        mod_secondaryStat2_value = mod_secondaryStat_values[1]
                    if len(mod_secondaryStat_unitStats)>2:
                        mod_secondaryStat3_unitStat = mod_secondaryStat_unitStats[2]
                        mod_secondaryStat3_value = mod_secondaryStat_values[2]
                    if len(mod_secondaryStat_unitStats)>3:
                        mod_secondaryStat4_unitStat = mod_secondaryStat_unitStats[3]
                        mod_secondaryStat4_value = mod_secondaryStat_values[3]
                        
                    mod_set = dict_modList[mod["definitionId"]]['setId']
                    mod_slot = dict_modList[mod["definitionId"]]['slot']
                    mod_tier = mod['tier']

                    current_mods_ids.append(mod_id)
            
                    query = "INSERT IGNORE INTO mods(id) "\
                           +"VALUES('"+mod_id+"')"
                    #goutils.log2("DBG", query)
                    cursor.execute(query)
        
                    query = "UPDATE mods "\
                           +"SET roster_id = "+str(roster_id)+", "\
                           +"defId = "+str(mod_defId)+", "\
                           +"level = "+str(mod_level)+", "\
                           +"pips = "+str(mod_pips)+", "\
                           +"mod_set = "+str(mod_set)+", "\
                           +"slot = "+str(mod_slot)+", "\
                           +"tier = "+str(mod_tier)+", "\
                           +"prim_stat = "+str(mod_primaryStat_unitStat)+", "\
                           +"prim_value = "+str(mod_primaryStat_value)+", "\
                           +"sec1_stat = "+str(mod_secondaryStat1_unitStat)+", "\
                           +"sec1_value = "+str(mod_secondaryStat1_value)+", "\
                           +"sec2_stat = "+str(mod_secondaryStat2_unitStat)+", "\
                           +"sec2_value = "+str(mod_secondaryStat2_value)+", "\
                           +"sec3_stat = "+str(mod_secondaryStat3_unitStat)+", "\
                           +"sec3_value = "+str(mod_secondaryStat3_value)+", "\
                           +"sec4_stat = "+str(mod_secondaryStat4_unitStat)+", "\
                           +"sec4_value = "+str(mod_secondaryStat4_value)+" "\
                           +"WHERE id = '"+mod_id+"'"
                    #goutils.log2("DBG", query)
                    cursor.execute(query)

            #remove mods not used anymore
            to_be_removed_mods_ids = tuple(set(previous_mods_ids)-set(current_mods_ids))
            if len(to_be_removed_mods_ids) > 0:
                query = "DELETE FROM mods WHERE id IN "+ str(tuple(to_be_removed_mods_ids)).replace(",)", ")")
                #goutils.log2("DBG", query)
                cursor.execute(query)

            ## GET DEFINITION OF CAPACITIES ##
            c_zeta_count = 0
            for capa in character['skill']:
                capa_name = capa['id']
                capa_level = capa['tier']+2
                capa_isZeta = (dict_capas[character_id][capa_name]["zetaTier"]<99)
                if "omicronMode" in  dict_capas[character_id][capa_name]:
                    capa_omicron_type = dict_capas[character_id][capa_name]["omicronMode"]
                    capa_omicron_tier = dict_capas[character_id][capa_name]["omicronTier"]
                else:
                    capa_omicron_type = ""
                    capa_omicron_tier = "-1"
                
                capa_shortname = capa_name[0].upper()
                if capa_shortname in 'SU' and capa_name[-1] in '0123456789':
                    capa_shortname += capa_name[-1]
                #goutils.log2("DBG", capa_name + " >> " + capa_shortname)
                    
                if capa_name == 'uniqueskill_GALACTICLEGEND01':
                    capa_shortname = 'GL'
                    
                if capa_isZeta == 1 and capa_level >= 8:
                    c_zeta_count += 1
        
                #launch query to update skills
                query = "INSERT IGNORE INTO roster_skills(roster_id, name) "\
                       +"VALUES("+str(roster_id)+", '"+capa_shortname+"')"
                #goutils.log2("DBG", query)
                cursor.execute(query)

                query = "UPDATE roster_skills "\
                       +"SET level = "+str(capa_level)+", "\
                       +"isZeta = "+str(capa_isZeta)+", "\
                       +"omicron_type = '"+capa_omicron_type+"', "\
                       +"omicron_tier = "+str(capa_omicron_tier)+" "\
                       +"WHERE roster_id = "+str(roster_id)+" "\
                       +"AND name = '"+capa_shortname+"'"
                #goutils.log2("DBG", query)
                cursor.execute(query)

            #Update zeta count in roster element
            query = "UPDATE roster "\
                   +"SET zeta_count = "+str(c_zeta_count)+" "\
                   +"WHERE allyCode = "+str(p_allyCode)+" "\
                   +"AND   defId = '"+c_defId+"'"
            #goutils.log2("DBG", query)
            cursor.execute(query)

            ## CHECK FOR ULTIMATE
            if "purchaseAbilityId" in character:
                ultimate = False
                for ability in character["purchaseAbilityId"]:
                    if ability.startswith("ultimate"):
                        ultimate = True

                if ultimate:
                    query = "INSERT IGNORE INTO roster_skills(roster_id, name) "\
                           +"VALUES("+str(roster_id)+", 'ULTI')"
                    #goutils.log2("DBG", query)
                    cursor.execute(query)

                    query = "UPDATE roster_skills "\
                           +"SET level = 1, "\
                           +"isZeta = 0, "\
                           +"omicron_type = '', "\
                           +"omicron_tier = -1 "\
                           +"WHERE roster_id = "+str(roster_id)+" "\
                           +"AND name = 'ULTI'"
                    #goutils.log2("DBG", query)
                    cursor.execute(query)

            #SLEEP at the end of character loop
            await asyncio.sleep(0)
                
        #Compute ModQ from DB data
        query = "SELECT count(mods.id)/(char_gp/100000) " \
              + "FROM mods " \
              + "JOIN roster ON mods.roster_id = roster.id " \
              + "JOIN players ON players.allyCode = roster.allyCode " \
              + "WHERE roster.allyCode="+str(p_allyCode)+" " \
              + "AND ( " \
              + "(sec1_stat=5 AND sec1_value>=15) OR " \
              + "(sec2_stat=5 AND sec2_value>=15) OR " \
              + "(sec3_stat=5 AND sec3_value>=15) OR " \
              + "(sec4_stat=5 AND sec4_value>=15)) "
        #goutils.log2("DBG", query)
        p_modq = get_value(query)
        if p_modq==None:
            p_modq = "NULL"

        #Compute StatQ
        ec, et, p_statq, l_statq = await get_player_statq(str(p_allyCode))
        if ec!=0:
            p_statq = "NULL"

        query = "UPDATE players "\
               +"SET modq = "+str(p_modq)+", "\
               +"    statq = "+str(p_statq)+" "\
               +"WHERE allyCode = "+str(p_allyCode)
        #goutils.log2("DBG", query)
        cursor.execute(query)

        #Manage GP history
        # Define delta minutes versus po time
        time_now = datetime.datetime.now()
        time_po_char_std = time_now.replace(hour=20, minute=0, second=0, microsecond=0)
        time_po_char_player = time_po_char_std - datetime.timedelta(0, p_poUTCOffsetMinutes*60)
        delta_time_po_char = abs((time_now - time_po_char_player).seconds/60)
        time_po_ship_std = time_now.replace(hour=21, minute=0, second=0, microsecond=0)
        time_po_ship_player = time_po_ship_std - datetime.timedelta(0, p_poUTCOffsetMinutes*60)
        delta_time_po_ship = abs((time_now - time_po_ship_player).seconds/60)

        query = "INSERT IGNORE INTO gp_history(date, allyCode) "\
               +"VALUES(CURDATE(), "+str(p_allyCode)+")"
        #goutils.log2("DBG", query)
        cursor.execute(query)

        query = "UPDATE gp_history "\
               +"SET guildName = '"+p_guildName.replace("'", "''")+"', "\
               +"    arena_char_rank = "+ p_arena_char_rank_txt + ", "\
               +"    arena_char_po_delta_minutes = "+ str(delta_time_po_char) + ", "\
               +"    arena_ship_rank = "+ p_arena_ship_rank_txt + ","\
               +"    arena_ship_po_delta_minutes = "+ str(delta_time_po_ship) + ", "\
               +"    grand_arena_rank = '"+ p_grand_arena_rank + "',"\
               +"    grand_arena_rating = "+ str(p_grand_arena_rating) + ","\
               +"    char_gp = "+str(p_char_gp)+", "\
               +"    ship_gp = "+str(p_ship_gp)+", "\
               +"    modq = "+str(p_modq)+", "\
               +"    statq = "+str(p_statq)+" "\
               +"WHERE date = CURDATE() "\
               +"AND allyCode = "+str(p_allyCode)
        #goutils.log2("DBG", query)
        cursor.execute(query)

        mysql_db.commit()
    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        return -1
        
    finally:
        if cursor != None:
            cursor.close()
    
    return 0

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
def update_gv_history(txt_allyCode, player_name, character, is_ID, progress, completed, source):
    cursor = None
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor()

        if txt_allyCode == '':
            query = "SELECT allyCode FROM players WHERE name = '"+player_name.replace("'", "''")+"'"
            goutils.log2("DBG", query)
            list_players = get_column(query)
            if len(list_players) != 1:
                return -1
            txt_allyCode = str(list_players[0])
            goutils.log2("DBG", "allyCode="+txt_allyCode)

        if is_ID:
            character_id = character
        else:
            list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([character])
            character_id = list_character_ids[0]
        goutils.log2("DBG", "character_id="+character_id)

        #Look if the GV already has a date for completed
        if completed:
            query = "SELECT COUNT(*) FROM gv_history " \
                  + "WHERE allyCode="+txt_allyCode+" " \
                  + "AND defId='"+character_id+"' " \
                  + "AND complete=1 " \
                  + "AND source='"+source+"'"
            goutils.log2("DBG", query)
            count_completed = get_value(query)
            already_complete = (count_completed >= 1)
        else:
            already_complete = False

        if not already_complete:
            query = "INSERT IGNORE INTO gv_history(date, allyCode, defId, source) "\
                   +"VALUES(CURDATE(), '"+txt_allyCode+"', '"+character_id+"', '"+source+"')"
            goutils.log2("DBG", query)
            cursor.execute(query)

            query = "UPDATE gv_history "\
                   +"SET progress = "+str(progress)+", "\
                   +"complete = "+str(int(completed))+" "\
                   +"WHERE date = CURDATE() "\
                   +"AND allyCode = '"+txt_allyCode+"' " \
                   +"AND defId = '"+character_id+"' " \
                   +"AND source = '"+source+"' "
            goutils.log2("DBG", query)
            cursor.execute(query)

            mysql_db.commit()

    except Error as error:
        goutils.log2("ERR", query)
        goutils.log2("ERR", error)
        return -1
        
    finally:
        if cursor != None:
            cursor.close()
    
    return 0

def get_shard_from_player(txt_allyCode, shard_type):
    # test if the shard already exists
    query = "SELECT "+shard_type+"Shard_id, name, guildName " \
          + "FROM players " \
          + "WHERE allyCode='"+txt_allyCode+"'"
    goutils.log2("DBG", query)
    existingShard, name, guildName = get_line(query)
    if existingShard == None:
        # If the player has no shard, create one and allocate it to him or her
        query = "INSERT INTO shards(type) "\
               +"VALUES('"+shard_type+"')"
        goutils.log2("DBG", query)
        simple_execute(query)

        query = "SELECT MAX(id) FROM shards"
        goutils.log2("DBG", query)
        new_shard = get_value(query)

        query = "UPDATE players "\
               +"SET "+shard_type+"Shard_id="+str(new_shard)+" " \
               +"WHERE allyCode="+txt_allyCode
        goutils.log2("DBG", query)
        simple_execute(query)

        return new_shard, name, guildName
    else:
        return existingShard, name, guildName

def get_shard_list(shard_id, shard_type, txt_mode):
    query = "SELECT allyCode, name, guildName, arena_"+shard_type+"_rank, " \
          + "time('01-01-01 19:00:00' - interval poUTCOffsetMinutes minute) as 'PO_utc' " \
          + "FROM players " \
          + "WHERE "+shard_type+"Shard_id="+str(shard_id)+" "\
          + "ORDER BY arena_"+shard_type+"_rank, name"
    goutils.log2("DBG", query)
    if txt_mode:
        return text_query(query)
    else:
        return get_table(query)

def add_player_to_shard(txt_allyCode, target_shard, shard_type, force_merge):
    player_existing_shard, name, guildName = get_shard_from_player(txt_allyCode, shard_type)

    if player_existing_shard == target_shard:
        #Already in the good shard
        return 0, "Joueur "+txt_allyCode+" ("+name+" @ "+guildName+") déjà dans le shard", None
    else:
        #player already in another shard
        player_shard_size = len(get_shard_list(player_existing_shard, shard_type, False))
        if player_shard_size == 1:
            #The player is alone in its own shard
            # set the shard for this player
            query = "UPDATE players "\
                   +"SET "+shard_type+"Shard_id="+str(target_shard)+" " \
                   +"WHERE allyCode="+txt_allyCode
            goutils.log2("DBG", query)
            simple_execute(query)

            # delete the previous shard of the player
            query = "DELETE FROM shards " \
                   +"WHERE id="+str(player_existing_shard)
            goutils.log2("DBG", query)
            simple_execute(query)

            return 0, "Joueur "+txt_allyCode+" ("+name+" @ "+guildName+") ajouté au shard", None

        target_shard_size = len(get_shard_list(target_shard, shard_type, False))
        if target_shard_size == 1 or force_merge:
            #If the requesting player (me) is alone in its shard
            # replace the target shard by the shard of the player
            query = "UPDATE players "\
                   +"SET "+shard_type+"Shard_id="+str(player_existing_shard)+" " \
                   +"WHERE "+shard_type+"Shard_id="+str(target_shard)
            goutils.log2("DBG", query)
            simple_execute(query)

            # delete the target shard
            query = "DELETE FROM shards " \
                   +"WHERE id="+str(target_shard)
            goutils.log2("DBG", query)
            simple_execute(query)

            return 0, "Joueur "+txt_allyCode+" ("+name+" @ "+guildName+") ajouté au shard", None

        #target shard and shard from player are both filled with several players
        # need to merge them with confirmation from player
        return 1, "", [target_shard, player_existing_shard]

##############################################################
# Function: load_config_players
# Parameters: none
# Output:  dict_players_by_IG {key=IG name, value=[allycode, <@id>]}
#          dict_players_by_ID {key=discord ID, value=[allycode, isOfficer]}
##############################################################
def load_config_players():
    query = "SELECT allyCode, players.name, discord_id, guildMemberLevel FROM players "
    goutils.log2("DBG", query)
    data_db = get_table(query)

    dict_players_by_IG = {}
    dict_players_by_ID = {}

    list_did = [x[2] for x in data_db]
    for line in data_db:
        ac = line[0]
        name = line[1]
        did = line[2]
        if did == None:
            did=""
        isOff = (line[3]!=2)

        if did != "":
            dict_players_by_IG[name] = [ac, name]
            if list_did.count(did) == 1:
                dict_players_by_IG[name] = [ac, "<@"+did+">"]
            else:
                dict_players_by_IG[name] = [ac, "<@"+did+"> ["+name+"]"]
            dict_players_by_ID[did] = [ac, isOff]

    return dict_players_by_IG, dict_players_by_ID


##############################################################
# this global var is used in several functions
list_statq_stats = []
list_statq_stats.append(["health", 1, False])
list_statq_stats.append(["speed", 5, False])
list_statq_stats.append(["pd", 6, False])
list_statq_stats.append(["sd", 7, False])
list_statq_stats.append(["cc", 14, True])
list_statq_stats.append(["cd", 16, True])
list_statq_stats.append(["potency", 17, True])
list_statq_stats.append(["tenacity", 18, True])
list_statq_stats.append(["protec", 28, False])
##############################################################
# Command: get_player_statqj
# IN: allyCode
# IN: load_player: True if need to load player data
# Output: statq, list_unit_stats
##############################################################
async def get_player_statq(txt_allyCode):

    query = "select count(*) from statq_table"
    statq_count = get_value(query)

    query = "SELECT \n" \
          + "defId,stat_name,stat_value, stat_target, \n" \
          + "CASE WHEN stat_ratio>=1.02 THEN 4 WHEN stat_ratio>=0.98 THEN 3 WHEN stat_ratio>=0.95 THEN 2 WHEN stat_ratio>=0.90 THEN 1 ELSE 0 END as score \n" \
          + "FROM( \n" \
          + "     SELECT my_roster.allyCode, my_roster.defId, stat_name, \n" \
          + "     CASE \n"

    #stat_value
    for stat in list_statq_stats:
        s_name = stat[0]
        s_id = stat[1]
        s_percent = stat[2]

        query += "     WHEN stat_name='"+s_name+"'   THEN CONCAT(ROUND(stat"+str(s_id)

        if s_percent:
            query+="/1000000, 1), '% (' , ROUND(mod"+str(s_id)+" /1000000), '%)' ) \n"
        else:
            query+="/100000000), ' (', ROUND(mod"+str(s_id)+" /100000000), ')') \n"

    query +="     END AS `stat_value`, \n" \
          + "     CASE \n"

    #stat_target
    for stat in list_statq_stats:
        s_name = stat[0]
        s_id = stat[1]
        s_percent = stat[2]

        query += "     WHEN stat_name='"+s_name+"' THEN CONCAT(ROUND((stat"+str(s_id)+"-mod"+str(s_id)+")*(stat_avg*1.02+1)"

        if s_percent:
            query+="/1000000, 1), '%' "
        else:
            query+="/100000000) "
        query += ", ' (',ROUND(mod"+str(s_id)+"*100/((stat"+str(s_id)+"-mod"+str(s_id)+")*(stat_avg*1.02+1)-(stat"+str(s_id)+"-mod"+str(s_id)+"))),'%)') \n"


    query +="     END AS `stat_target`, \n" \
          + "     CASE \n"

    #stat_ratio
    for stat in list_statq_stats:
        s_name = stat[0]
        s_id = stat[1]

        query += "     WHEN stat_name='"+s_name+"'   THEN (mod"+str(s_id)+" /(stat"+str(s_id)+" -mod"+str(s_id)+" )) /stat_avg \n"


    query +="     END AS `stat_ratio`, coef \n" \
          + "     FROM roster AS my_roster \n" \
          + "     JOIN statq_table ON my_roster.defId=statq_table.defId AND NOT isnull(statq_table.stat_avg) \n" \
          + "     WHERE stat_avg>0 AND gear>=12 AND allyCode="+txt_allyCode+" \n" \
          + ") ratios \n" \
          + "JOIN players ON players.allyCode = ratios.allyCode \n" \
          + "WHERE players.allyCode = "+txt_allyCode

    goutils.log2("DBG", query)
    db_data = get_table(query)
    if db_data==None:
        db_data=[]
        statq = 0
    else:
        list_scores = [x[4] for x in db_data]
        statq = sum(list_scores)*statq_count/len(list_scores)

        #update staq for player
        query = "UPDATE players SET statq="+str(statq)+" WHERE allyCode="+txt_allyCode
        simple_execute(query)

        #update daily staq for player
        query = "UPDATE gp_history SET statq="+str(statq)+" WHERE allyCode="+txt_allyCode+" AND date=DATE(current_timestamp)"
        simple_execute(query)

    return 0, "", statq, db_data

##############################################################
# Function: compute_statq_avg
# IN: force_all (True: reset all stats / False: compute only null stats)
# OUT: none
##############################################################
def compute_statq_avg(force_all):
    #Compute stat_avg for statq_table, from KYBER1 players
    query = "UPDATE statq_table SET stat_avg = CASE \n"

    for stat in list_statq_stats:
        s_name = stat[0]
        s_id = stat[1]

        query += "WHEN stat_name='"+s_name+"' THEN ( " \
                 "   select avg(mod"+str(s_id)+"/(stat"+str(s_id)+"-mod"+str(s_id)+")) " \
                 "   from roster " \
                 "   join players on players.allyCode=roster.allyCode " \
                 "   where statq_table.defId=roster.defId " \
                 "   and gear>=12 " \
                 "   and mod1>stat1 " \
                 "   and grand_arena_rank='KYBER1' " \
                 "   and timestampdiff(DAY,lastUpdated,CURRENT_TIMESTAMP)<30 " \
                 ") \n"

    query+= "END \n"

    if not force_all:
        query+= "WHERE (isnull(stat_avg) OR stat_avg=0)"

    goutils.log2("DBG", query)
    simple_execute(query)
