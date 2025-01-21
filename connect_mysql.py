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

        #adapt syntax ty MYSQL
        evo_txt = evo_txt.replace("'","''")

        if defId!=None:
            query = "INSERT INTO roster_evolutions(allyCode, defId, description) "\
                   +"VALUES("+str(allyCode)+", '"+str(defId)+"', '"+evo_txt+"')"
        else:
            query = "INSERT INTO roster_evolutions(allyCode, description) "\
                   +"VALUES("+str(allyCode)+", '"+evo_txt+"')"
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
    dict_rules = data.get("targetrules_dict.json")

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
                goutils.log2("ERR no gp for ", p_playerId+":"+character_id)
                return 1, "ERR no gp for "+ p_playerId+":"+character_id
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
            for capa in character['skill']:
                capa_name = capa['id']
                capa_level = capa['tier']+2
                if capa_level >= dict_capas[character_id][capa_name]["omicronTier"]:
                    capa_omicron_type = dict_capas[character_id][capa_name]["omicronMode"]
                else:
                    capa_omicron_type = ""
                
                capa_shortname = dict_capas[character_id][capa_name]["shortname"]
                    
                if capa_name == 'uniqueskill_GALACTICLEGEND01':
                    capa_shortname = 'GL'
                    
                #launch query to update skills
                query = "INSERT IGNORE INTO roster_skills(roster_id, name) "\
                       +"VALUES("+str(roster_id)+", '"+capa_shortname+"')"
                #goutils.log2("DBG", query)
                cursor.execute(query)

                query = "UPDATE roster_skills "\
                       +"SET level = "+str(capa_level)+", "\
                       +"omicron_type = '"+capa_omicron_type+"' "\
                       +"WHERE roster_id = "+str(roster_id)+" "\
                       +"AND name = '"+capa_shortname+"'"
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
                           +"omicron_type = '' "\
                           +"WHERE roster_id = "+str(roster_id)+" "\
                           +"AND name = 'ULTI'"
                    #goutils.log2("DBG", query)
                    cursor.execute(query)

            #SLEEP at the end of character loop
            await asyncio.sleep(0)
                
        ## GET DEFINITION OF DATACRONS ##
        if 'datacron' in dict_player:
            #Get existing datacron IDs from DB
            query = "SELECT id FROM datacrons WHERE allyCode = "+str(p_allyCode)
            goutils.log2("DBG", query)
            previous_datacrons_ids = get_column(query)
            goutils.log2("DBG", previous_datacrons_ids)

            current_datacrons_ids = []
            for datacron_id in dict_player['datacron']:
                datacron = dict_player['datacron'][datacron_id]
                datacron_setId = datacron['setId']
                current_datacrons_ids.append(datacron_id)

                datacron_level_3 = None
                datacron_level_6 = None
                datacron_level_9 = None

                if "affix" in datacron:
                    if len(datacron["affix"]) >= 3:
                        abilityId = datacron["affix"][2]["abilityId"]
                        targetRule = datacron["affix"][2]["targetRule"]
                        target = dict_rules[targetRule][0]
                        datacron_level_3 = abilityId+":"+target

                    if len(datacron["affix"]) >= 6:
                        abilityId = datacron["affix"][5]["abilityId"]
                        targetRule = datacron["affix"][5]["targetRule"]
                        target = dict_rules[targetRule][0]
                        datacron_level_6 = abilityId+":"+target

                    if len(datacron["affix"]) >= 9:
                        abilityId = datacron["affix"][8]["abilityId"]
                        targetRule = datacron["affix"][8]["targetRule"]
                        target = dict_rules[targetRule][0]
                        datacron_level_9 = abilityId+":"+target

        
                query = "INSERT IGNORE INTO datacrons(id) "\
                       +"VALUES('"+datacron_id+"')"
                goutils.log2("DBG", query)
                cursor.execute(query)
    
                query = "UPDATE datacrons "\
                       +"SET allyCode = "+str(p_allyCode)+", "\
                       +"setId = "+str(datacron_setId)+" "
                if datacron_level_3 != None:
                    query+= ", level_3 = '"+str(datacron_level_3)+"' "
                if datacron_level_6 != None:
                    query+= ", level_6 = '"+str(datacron_level_6)+"' "
                if datacron_level_9 != None:
                    query+= ", level_9 = '"+str(datacron_level_9)+"' "
                query+= "WHERE id = '"+datacron_id+"'"
                goutils.log2("DBG", query)
                cursor.execute(query)

            #remove datacrons not used anymore
            # The removal of datacrons is only done if there was at least ONE change
            # In case of ONE change, all datacrons are removed and re-added
            # This is more simpler than managing a real delta processing
            to_be_removed_datacrons_ids = tuple(set(previous_datacrons_ids)-set(current_datacrons_ids))
            if len(to_be_removed_datacrons_ids) > 0:
                query = "DELETE FROM datacrons WHERE id IN "+ str(tuple(to_be_removed_datacrons_ids)).replace(",)", ")")
                goutils.log2("DBG", query)
                cursor.execute(query)



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
        return 1, error
        
    finally:
        if cursor != None:
            cursor.close()
    
    return 0, ""

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

        if not already_complete and progress>0:
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
# Output:  dict_players_by_IG {key=IG name, value=[allycode, <@id>, isOfficer]}
#          dict_players_by_ID {key=discord ID, value={"main":[allycode, isOfficer]
#                                                     "alts":[[ac, isOff], [ac2, isOff]...]}}
##############################################################
def load_config_players():
    query = "SELECT players.allyCode, players.name, player_discord.discord_id, player_discord.main, guildMemberLevel \n"
    query+= "FROM players \n"
    query+= "JOIN player_discord ON player_discord.allyCode=players.allyCode \n"
    query+= "ORDER BY player_discord.discord_id, player_discord.main "
    goutils.log2("DBG", query)
    data_db = get_table(query)

    dict_players_by_IG = {}
    dict_players_by_ID = {}

    list_did = [x[2] for x in data_db]
    for line in data_db:
        ac = line[0]
        name = line[1]
        did = line[2]
        isMain = line[3]
        isOff = (line[4]!=2)

        # dict_players_by_IG
        dict_players_by_IG[name] = [ac, name]
        if list_did.count(did) == 1:
            dict_players_by_IG[name] = [ac, "<@"+str(did)+">", isOff]
        else:
            dict_players_by_IG[name] = [ac, "<@"+str(did)+"> ["+name+"]", isOff]

        # dict_players_by_ID
        if not did in dict_players_by_ID:
            dict_players_by_ID[did] = {"main": None, "alts": []}
            
        if isMain:
            dict_players_by_ID[did]["main"] = [ac, isOff]
        else:
            dict_players_by_ID[did]["alts"].append([ac, isOff])

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
    # stats values are rounded down, like in the game > FLOOR
    for stat in list_statq_stats:
        s_name = stat[0]
        s_id = stat[1]
        s_percent = stat[2]

        query += "     WHEN stat_name='"+s_name+"'   THEN CONCAT(FLOOR(stat"+str(s_id)

        if s_percent:
            query+="/1000000), '% (' , FLOOR(mod"+str(s_id)+" /1000000), '%)' ) \n"
        else:
            query+="/100000000), ' (', FLOOR(mod"+str(s_id)+" /100000000), ')') \n"

    query +="     END AS `stat_value`, \n" \
          + "     CASE \n"

    #stat_target
    # stats values are rounded down, like in the game > FLOOR
    # ratio is rounded to the nearest > ROUND
    for stat in list_statq_stats:
        s_name = stat[0]
        s_id = stat[1]
        s_percent = stat[2]

        query += "     WHEN stat_name='"+s_name+"' THEN CONCAT(FLOOR((stat"+str(s_id)+"-mod"+str(s_id)+")*(stat_avg*1.02+1)"

        if s_percent:
            query+="/1000000), '%' "
        else:
            query+="/100000000) "
        query += ", ' (',ROUND(mod"+str(s_id)+"*100/((stat"+str(s_id)+"-mod"+str(s_id)+")*(stat_avg*1.02+1)-(stat"+str(s_id)+"-mod"+str(s_id)+"))),'%)') \n"


    query +="     END AS `stat_target`, \n" \
          + "     CASE \n"

    #stat_ratio
    for stat in list_statq_stats:
        s_name = stat[0]
        s_id = stat[1]

        query += "     WHEN stat_name='"+s_name+"'   THEN ROUND((mod"+str(s_id)+" /(stat"+str(s_id)+" -mod"+str(s_id)+" )) /stat_avg / 0.02)*0.02 \n"


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
                 "   and stat"+str(s_id)+" > mod"+str(s_id)+" " \
                 "   and grand_arena_rank='KYBER1' " \
                 "   and (char_gp+ship_gp)>9000000 " \
                 "   and timestampdiff(DAY,lastUpdated,CURRENT_TIMESTAMP)<30 " \
                 ") \n"

    query+= "END \n"

    if not force_all:
        query+= "WHERE (isnull(stat_avg) OR stat_avg=0)"

    goutils.log2("DBG", query)
    simple_execute(query)

########################################
# Get guild ID, allyCode and player name for the
#  warbot linked to this discord server
########################################
def get_warbot_info(server_id, channel_id):
    goutils.log2("DBG", "looking for bot_infos from server ID...")
    query = "SELECT guild_id, allyCode, players.name, tbChanRead_id, tbChanOut_id, tbRoleOut, guilds.name, gfile_name, echostation_id FROM guild_bot_infos \n"
    query+= "JOIN players ON players.allyCode=guild_bot_infos.bot_allyCode \n"
    query+= "JOIN guilds ON guilds.id=guild_bot_infos.guild_id \n"
    query+= "WHERE server_id="+str(server_id)
    goutils.log2("DBG", query)
    db_data = get_line(query)

    if db_data == None:
        if channel_id != None:
            #no warbot found from server, try it from the channel as test channel
            goutils.log2("DBG", "looking for bot_infos from guild channel ID...")
            query = "SELECT guildId, allyCode, players.name, tbChanRead_id, tbChanOut_id, tbRoleOut, guilds.name, gfile_name, echostation_id FROM guild_bot_infos \n"
            query+= "JOIN players ON players.allyCode=guild_bot_infos.bot_allyCode \n"
            query+= "JOIN guilds ON guilds.id=guild_bot_infos.guild_id \n"
            query+= "JOIN guild_test_channels ON guild_test_channels.guild_id=guild_bot_infos.guild_id \n"
            query+= "WHERE channel_id="+str(channel_id)
            goutils.log2("DBG", query)
            db_data = get_line(query)

            if db_data == None:
                #no warbot found as test channel, try it from connected user
                goutils.log2("DBG", "looking for bot_infos from user channel ID...")
                query = "SELECT guildId, players.allyCode, players.name, tbChanRead_id, tbChanOut_id, tbRoleOut, guilds.name, gfile_name, echostation_id FROM guild_bot_infos \n"
                query+= "JOIN players ON players.guildId=guild_bot_infos.guild_id \n"
                query+= "JOIN guilds ON guilds.id=guild_bot_infos.guild_id \n"
                query+= "JOIN user_bot_infos ON user_bot_infos.allyCode=players.allyCode \n"
                query+= "WHERE channel_id="+str(channel_id)
                goutils.log2("DBG", query)
                db_data = get_line(query)

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
                   "guild_name": db_data[6],
                   "gfile_name": db_data[7],
                   "echostation_id": db_data[8]}

def get_warbot_info_from_guild(guild_id):
    query = "SELECT guild_id, allyCode, players.name, tbChanRead_id, tbChanOut_id, tbRoleOut, guilds.name, server_id, gfile_name FROM guild_bot_infos \n"
    query+= "JOIN players ON players.allyCode=guild_bot_infos.bot_allyCode \n"
    query+= "JOIN guilds ON guilds.id=guild_bot_infos.guild_id \n"
    query+= "WHERE guild_id='"+guild_id+"'"
    goutils.log2("DBG", query)
    db_data = get_line(query)

    if db_data == None:
        return 1, "Pas de warbot trouvé pour cette guilde", None

    return 0, "", {"guild_id": db_data[0],
                   "allyCode": str(db_data[1]),
                   "player_name": db_data[2],
                   "tbChanRead_id": db_data[3],
                   "tbChanOut_id": db_data[4],
                   "tbRoleOut": db_data[5],
                   "guild_name": db_data[6],
                   "server_id": db_data[7],
                   "gfile_name": db_data[8]}

########################################
# Get guild ID, allyCode and player name for the
#  google account linked to this channel
########################################
def get_google_player_info(channel_id):
    query = "SELECT guildId, players.allyCode, players.name, \n"
    query+= "       tbChanRead_id, echostation_id, \n"
    query+= "       twChanOut_id \n"
    query+= "FROM user_bot_infos \n"
    query+= "JOIN players ON players.allyCode=user_bot_infos.allyCode \n"
    query+= "LEFT JOIN guild_bot_infos ON guild_bot_infos.guild_id=players.guildId \n"
    query+= "WHERE channel_id="+str(channel_id)
    goutils.log2("DBG", query)
    db_data = get_line(query)
    if db_data == None:
        return 1, "Pas d'utilisateur trouvé pour ce channel", None
    
    return 0, "", {"guild_id": db_data[0],
                   "allyCode": str(db_data[1]),
                   "player_name": db_data[2],
                   "tbChanRead_id": db_data[3],
                   "echostation_id": db_data[4],
                   "twChanOut_id": db_data[5]}

# IN: tbs_round > ROTE1 to ROTE6, or ROTE0 to get the latest data
def get_tb_platoon_allocations(guild_id, tbs_round):
    dict_unitsList = data.get("unitsList_dict.json")
    dict_tb = data.get("tb_definition.json")

    tb_name = tbs_round[:-1]
    tb_phase = int(tbs_round[-1])
    if tb_name == "ROTE":
        terr_pos = ["LS", "DS", "MS"]
    else:
        terr_pos = ["top", "mid", "bot"]

    query = "SELECT zone_id, platoon_id, unit_id, name FROM platoon_allocations " \
            "JOIN platoon_config ON platoon_config.id=config_id " \
            "JOIN players ON players.allyCode=platoon_allocations.allyCode " \
            "WHERE guild_id='"+guild_id+"' "
    if tb_phase>0:
        # Get the data for specific phase
        query += "AND phases="+str(tb_phase) 
    else:
        # Get the data for latest stored data of this guild
        query += "AND ABS(timestampdiff(SECOND, timestamp, (select max(timestamp) from platoon_config WHERE guild_id='"+guild_id+"')))<5"

    goutils.log2("DBG", query)
    db_data = get_table(query)
    if db_data == None:
        return 1, "Aucune allocation de peloton connue", None

    dict_platoons_allocation = {}
    for line in db_data:
        zone_id = line[0]
        platoon_id = line[1]
        unit_id = line[2]
        player_name = line[3]

        conflict_id = "_".join(zone_id.split('_')[:-1])
        conflict_name = dict_tb[conflict_id]["name"] # "ROTE1-DS"

        if tb_name == "ROTE":
            platoon_position = str(7-int(platoon_id[-1]))
        else:
            platoon_position = "hoth-platoon-"+platoon_id[-1]

        platoon_name = conflict_name+"-"+platoon_position

        if not platoon_name in dict_platoons_allocation:
            dict_platoons_allocation[platoon_name] = {}
        
        unit_name = dict_unitsList[unit_id]["name"]
        if not unit_name in dict_platoons_allocation[platoon_name]:
            dict_platoons_allocation[platoon_name][unit_name] = []

        if player_name != None:
            dict_platoons_allocation[platoon_name][unit_name].append(player_name)

    return 0, "", {"dict_platoons_allocation": dict_platoons_allocation}

def update_tb_round(guild_id, tb_id, tb_round, dict_phase, dict_zones, dict_strike_zones, list_open_zones, dict_tb_players):
    dict_tb = data.get("tb_definition.json")
    now = datetime.datetime.now()

    # Check / Create the TB in DB
    query = "SELECT id FROM tb_history " \
            "WHERE tb_id='"+tb_id+"' "\
            "AND guild_id='"+guild_id+"' "
    goutils.log2("DBG", query)
    db_data = get_value(query)

    if db_data==None:
        tb_ts = int(tb_id.split(":")[1][1:-3])
        tb_date = datetime.datetime.fromtimestamp(tb_ts).strftime("%Y/%m/%d %H:%M:%S")
        query = "INSERT INTO tb_history(tb_id, tb_name, date, guild_id) " \
                "VALUES('"+tb_id+"', '"+dict_phase["name"].replace("'", "''")+"', '"+tb_date+"', '"+guild_id+"') "
        goutils.log2("DBG", query)
        simple_execute(query)

        # Get the id of the new TB
        query = "SELECT id FROM tb_history " \
                "WHERE tb_id='"+tb_id+"' "\
                "AND guild_id='"+guild_id+"' "
        goutils.log2("DBG", query)
        tb_db_id = str(get_value(query))
    else:
        tb_db_id = str(db_data)


    i_zone = 0
    for zone_fullname in list_open_zones:
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
        query = "SELECT id FROM tb_zones " \
                "WHERE tb_id="+tb_db_id+" "\
                "AND zone_id='"+zone_fullname+"' "\
                "AND round="+round+" "
        goutils.log2("DBG", query)
        db_data = get_value(query)

        score_step1 = str(dict_tb[zone_fullname]["scores"][0])
        score_step2 = str(dict_tb[zone_fullname]["scores"][1])
        score_step3 = str(dict_tb[zone_fullname]["scores"][2])
        if db_data==None:
            query = "INSERT INTO tb_zones(tb_id, zone_id, zone_name, zone_phase, round, "\
                    "score_step1, score_step2, score_step3, is_bonus) "\
                    "VALUES("+tb_db_id+", '"+zone_fullname+"', '"+zone_shortname+"', "+zone_round+", "+round+", "\
                    ""+score_step1+", "+score_step2+", "+score_step3+", "+is_bonus+") "
            goutils.log2("DBG", query)
            simple_execute(query)

            # Get the id of the new Zone
            query = "SELECT id FROM tb_zones " \
                    "WHERE tb_id="+tb_db_id+" "\
                    "AND zone_id='"+zone_fullname+"' "\
                    "AND round="+round+" "
            goutils.log2("DBG", query)
            zone_db_id = str(get_value(query))
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

        query = "UPDATE tb_zones "\
                "SET score="+str(score)+",  "\
                "    estimated_strikes="+str(score)+", "\
                "    estimated_deployments="+str(deployment)+", "\
                "    max_fights="+str(maxStrikeScore)+" "\
                "WHERE id="+zone_db_id+" "
        goutils.log2("DBG", query)
        simple_execute(query)

    return 0, ""

# Update tb_events table from list of events
# list_events my be actually a dictionary
def store_tb_events(guild_id, tb_id, list_events):
    # Get timestamp for latest registered event in DB
    query = "SELECT UNIX_TIMESTAMP(MAX(timestamp)) FROM tb_events"
    goutils.log2("DBG", query)
    max_ts = get_value(query)
    if max_ts==None:
        max_ts=0

    # Get the DB tb_id from the game tb_id and the guild_id
    query = "SELECT id FROM tb_history WHERE tb_id='"+tb_id+"' AND guild_id='"+guild_id+"'"
    goutils.log2("DBG", query)
    tb_db_id = get_value(query)

    for event in list_events:
        #Manage the case where list_events is a dict
        if type(event)==str:
            event_id = event
            event = list_events[event_id]

        event_ts = round(int(event["timestamp"])*0.001, 3) # to prevent values like 1737416568.6330001
        if event_ts <= max_ts:
            #goutils.log2("DBG", str(event_ts)+" < "+str(max_ts))
            continue

        author_id = event["authorId"]
        data=event["data"][0]
        activity=data["activity"]
        event_type = activity["zoneData"]["activityLogMessage"]["key"]
        if "CONFLICT_CONTRIBUTION" in activity["zoneData"]["activityLogMessage"]["key"]:
            zone_data = activity["zoneData"]
            zone_id = zone_data["zoneId"]
            param2 = zone_data["activityLogMessage"]["param"][2]["paramValue"][0]
            param3 = zone_data["activityLogMessage"]["param"][3]["paramValue"][0]

            query = "INSERT INTO tb_events(tb_id, timestamp, event_type, zone_id, "\
                    "author_id, param2, param3) "\
                    "VALUES("+str(tb_db_id)+", "\
                    "FROM_UNIXTIME("+str(event_ts)+"), "\
                    "'CONFLICT_CONTRIBUTION', "\
                    "'"+zone_id+"', "\
                    "'"+author_id+"', "\
                    ""+str(param2)+", "\
                    ""+str(param3)+") "
            goutils.log2("DBG", query)
            simple_execute(query)

        elif "COVERT_COMPLETE" in activity["zoneData"]["activityLogMessage"]["key"]:
            zone_data = activity["zoneData"]
            zone_id = zone_data["zoneId"]

            query = "INSERT INTO tb_events(tb_id, timestamp, event_type, zone_id, "\
                    "author_id) "\
                    "VALUES("+str(tb_db_id)+", "\
                    "FROM_UNIXTIME("+str(event_ts)+"), "\
                    "'COVERT_COMPLETE', "\
                    "'"+zone_id+"', "\
                    "'"+author_id+"') "
            goutils.log2("DBG", query)
            simple_execute(query)

        elif "CONFLICT_DEPLOY" in activity["zoneData"]["activityLogMessage"]["key"]:
            zone_data = activity["zoneData"]
            zone_id = zone_data["zoneId"]
            param0 = zone_data["activityLogMessage"]["param"][0]["paramValue"][0]

            query = "INSERT INTO tb_events(tb_id, timestamp, event_type, zone_id, "\
                    "author_id, param0) "\
                    "VALUES("+str(tb_db_id)+", "\
                    "FROM_UNIXTIME("+str(event_ts)+"), "\
                    "'CONFLICT_DEPLOY', "\
                    "'"+zone_id+"', "\
                    "'"+author_id+"', "\
                    ""+str(param0)+") "
            goutils.log2("DBG", query)
            simple_execute(query)

        elif "RECON_CONTRIBUTION" in activity["zoneData"]["activityLogMessage"]["key"]:
            zone_data = activity["zoneData"]
            zone_id = zone_data["zoneId"]
            param0 = zone_data["activityLogMessage"]["param"][0]["paramValue"][0]
            param2 = zone_data["activityLogMessage"]["param"][2]["paramValue"][0]
            param3 = zone_data["activityLogMessage"]["param"][3]["paramValue"][0]

            query = "INSERT INTO tb_events(tb_id, timestamp, event_type, zone_id, "\
                    "author_id, param0, param2, param3) "\
                    "VALUES("+str(tb_db_id)+", "\
                    "FROM_UNIXTIME("+str(event_ts)+"), "\
                    "'RECON_CONTRIBUTION', "\
                    "'"+zone_id+"', "\
                    "'"+author_id+"', "\
                    ""+str(param0)+", "\
                    ""+str(param2)+", "\
                    ""+str(param3)+") "
            goutils.log2("DBG", query)
            simple_execute(query)
