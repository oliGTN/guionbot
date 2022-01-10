import os
import config
import sys
import urllib.parse
import mysql.connector
from mysql.connector import MySQLConnection, Error
import datetime
import wcwidth
def wc_ljust(text, length):
    return text + ' ' * max(0, length - wcwidth.wcswidth(text))

import goutils
import connect_crinolo
import data

mysql_db = None

def db_connect():
    #global mysql_db
    mysql_db = None
    if mysql_db == None or not mysql_db.is_connected():
        # if mysql_db == None:
            # print("First connection to mysql")
        # else:
            # print("New connection to mysql")
            
        # Recover DB information from URL
        urllib.parse.uses_netloc.append('mysql')
        try:
            url = urllib.parse.urlparse(config.MYSQL_DATABASE_URL)
            # 'NAME': url.path[1:],
            # 'USER': url.username,
            # 'PASSWORD': url.password,
            # 'HOST': url.hostname,
            # 'PORT': url.port,
        except Exception:
            goutils.log2("ERR", 'Unexpected error in connect:', sys.exc_info())
            return
        
        # Connect to DB
        mysql_db = None
        try:
            # print('Connecting to MySQL database...')
            mysql_db = mysql.connector.connect(host=url.hostname,
                                           database=url.path[1:],
                                           user=url.username,
                                           password=url.password)
            if mysql_db.is_connected():
                # print('Connected to MySQL database')
                pass
            else:
                goutils.log("ERR", "connect_mysql.db_connect", 'Connection failed')

        except Error as e:
            goutils.log("ERR", "connect_mysql.db_connect", 'Exception during connect: '+str(e))
            
    return mysql_db
        
def update_guild_teams(dict_team):
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
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)

        guild_teams_txt = ""
        # "JKR/Requis;4|JEDIKNIGHTREVAN;6;11;7;12;vit;capa;mod;pg;Chef,Unique1|BASTILA.../Important;1|GENERALKENOBI...\DR/Requis..."
        
        for team_name in dict_team:
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
                        zeta_id = goutils.get_zeta_id_from_short(toon_id, zeta)
                        toon_zetas += zeta_id+","
                    if len(toon_zetas)>0:
                        toon_zetas = toon_zetas[:-1]
                    
                    toon_speed = toon[6]
                    toon_capaLevel = ""
                    toon_modLevel = ""
                    toon_pg_min = ""
                    
                    toons_txt += toon_id + ";" + \
                                 str(toon_rarity_min) + ";" + \
                                 str(toon_gear_min) + ";" + \
                                 str(toon_rarity_reco) + ";" + \
                                 str(toon_gear_reco) + ";" + \
                                 str(toon_speed) + ";" + \
                                 str(toon_capaLevel) + ";" + \
                                 str(toon_modLevel) + ";" + \
                                 str(toon_pg_min) + ";" + \
                                 str(toon_zetas) + "|"
                
                # remove last "|"
                toons_txt = toons_txt[:-1]
                
                subteams_txt += subteam_name + ";" + \
                                str(subteam_min) + "|" + \
                                toons_txt + "/"

            # remove last "/"
            subteams_txt = subteams_txt[:-1]
            
            guild_teams_txt += team_name + "/" + \
                               subteams_txt + "\\"
       
        # remove last "\"
        subteams_txt = subteams_txt[:-1]

            
        # Launch the unique update with all information
        query_parameters = (guild_teams_txt,)
        #print("CALL update_guild_teams"+str(query_parameters))
        cursor.callproc('update_guild_teams', query_parameters)
        
        mysql_db.commit()
    except Error as error:
        goutils.log("ERR", "connect_mysql.update_guild_teams", error)
        
    finally:
        cursor.close()
        # db.close()

def text_query(query):
    rows = []

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
        goutils.log("ERR", "connect_mysql.text_query", error)
        rows=[error]
        
    finally:
        cursor.close()
    
    return rows
        
        
def simple_execute(query):
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)
        #print("simple_callproc: "+proc_name+" "+str(args))
        ret=cursor.execute(query)
        
        mysql_db.commit()
    except Error as error:
        goutils.log("ERR", "connect_mysql.simple_execute", error)
        
    finally:
        cursor.close()

def simple_callproc(proc_name, args):
    rows = []
    tuples = []
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)
        #print("simple_callproc: "+proc_name+" "+str(args))
        ret=cursor.callproc(proc_name, args)
        #print(ret)
        
        mysql_db.commit()
    except Error as error:
        goutils.log("ERR", "connect_mysql.simple_callproc", error)
        
    finally:
        cursor.close()

def get_value(query):
    tuples = []
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
        goutils.log("ERR", "connect_mysql.get_value", error)
        
    finally:
        cursor.close()
    
    if len(tuples[0]) > 0:
        return tuples[0][0][0]
    else:
        return None
        
def get_column(query):
    tuples = []
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
        goutils.log("ERR", "connect_mysql.get_column", error)
        
    finally:
        cursor.close()

    return [x[0] for x in tuples[0]]
    
def get_line(query):
    tuples = []
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
        goutils.log("ERR", "connect_mysql.get_line", error)
        
    finally:
        cursor.close()
    
    if len(tuples[0]) == 0:
        return None
    else:
        return tuples[0][0]
    
def get_table(query):
    tuples = []
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
        goutils.log("ERR", "connect_mysql.get_table", error)
        
    finally:
        cursor.close()

    #print("DBG: get_table return")
    if len(tuples[0]) == 0:
        return None
    else:
        return tuples[0]

def insert_roster_evo(allyCode, defId, evo_txt):
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor(buffered=True)

        query = "INSERT INTO roster_evolutions(allyCode, defId, description) "\
               +"VALUES("+str(allyCode)+", '"+defId+"', '"+evo_txt+"')"
        goutils.log("DBG", "insert_roster_evo", query)
        cursor.execute(query)

        mysql_db.commit()
    except Error as error:
        goutils.log("ERR", "insert_roster_evo", error)
        return -1
        
    finally:
        cursor.close()
    
def update_player(dict_player):
    dict_unitsList = data.get("unitsList_dict.json")
    dict_zetas = data.get("unit_zeta_list.json")
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor()
        
        # Update basic player information
        p_allyCode = dict_player['allyCode']
        p_guildName = dict_player['guildName']

        p_lastActivity_player = dict_player['lastActivity']
        p_lastActivity_ts = datetime.datetime.fromtimestamp(p_lastActivity_player/1000)
        p_lastActivity = p_lastActivity_ts.strftime('%Y-%m-%d %H:%M:%S')

        p_level = dict_player['level']
        p_name = dict_player['name']
        p_arena_char_rank = dict_player['arena']['char']['rank']
        p_arena_char_rank_txt = ("NULL" if p_arena_char_rank == None else str(p_arena_char_rank))
        p_arena_ship_rank = dict_player['arena']['ship']['rank']
        p_arena_ship_rank_txt = ("NULL" if p_arena_ship_rank == None else str(p_arena_ship_rank))
        if len(dict_player['grandArena'])>0:
            p_grand_arena_league = dict_player['grandArena'][-1]['league']
            p_grand_arena_division = 6 - int(dict_player['grandArena'][-1]['division']/5)
            p_grand_arena_rank = p_grand_arena_league + str(p_grand_arena_division)
        else:
            p_grand_arena_rank = "NULL"

        for stat in dict_player['stats']:
            if stat['nameKey'] == "Puissance Galactique (personnages)\u00a0:":
                p_char_gp = stat['value']
            elif stat['nameKey'] == "Puissance Galactique (vaisseaux)\u00a0:":
                p_ship_gp = stat['value']

        p_poUTCOffsetMinutes = dict_player['poUTCOffsetMinutes']

        query = "INSERT IGNORE INTO players(allyCode) "\
               +"VALUES("+str(p_allyCode)+")"
        goutils.log("DBG", "update_player", query)
        cursor.execute(query)

        query = "UPDATE players "\
               +"SET guildName = '"+p_guildName.replace("'", "''")+"', "\
               +"    lastActivity = '"+p_lastActivity+"', "\
               +"    level = "+str(p_level)+", "\
               +"    name = '"+str(p_name).replace("'", "''")+"', "\
               +"    arena_char_rank = "+ p_arena_char_rank_txt +", "\
               +"    arena_ship_rank = "+ p_arena_ship_rank_txt +", "\
               +"    grand_arena_rank = '"+ p_grand_arena_rank +"', "\
               +"    char_gp = "+str(p_char_gp)+", "\
               +"    ship_gp = "+str(p_ship_gp)+", "\
               +"    poUTCOffsetMinutes = "+str(p_poUTCOffsetMinutes)+", "\
               +"    lastUpdated = CURRENT_TIMESTAMP "\
               +"WHERE allyCode = "+str(p_allyCode)
        goutils.log("DBG", "update_player", query)
        cursor.execute(query)

        # Update the roster
        goutils.log2("DBG", "update "+str(len(dict_player['roster']))+" character(s)")
        for character_id in dict_player['roster']:
            character = dict_player['roster'][character_id]
            c_combatType = character['combatType']
            c_defId = character['defId']
            if c_defId in dict_unitsList:
                c_forceAlignment = dict_unitsList[c_defId]['forceAlignment']
            else:
                c_forceAlignment = 1
            c_gear = character['gear']
            c_gp = character['gp']
            c_level = character['level']
            c_nameKey = ''
            c_rarity = character['rarity']
            
            c_relic_currentTier = 0
            if character['relic'] != None:
                c_relic_currentTier = character['relic']['currentTier']

            c_equipped = ['', '', '', '', '', '']
            for eqpt in character['equipped']:
                c_equipped[eqpt['slot']] = eqpt['equipmentId']
                            
            #launch query to update roster element, with stats
            query = "INSERT IGNORE INTO roster(allyCode, defId) "\
                   +"VALUES("+str(p_allyCode)+", '"+c_defId+"')"
            goutils.log("DBG", "update_player", query)
            cursor.execute(query)

            query = "UPDATE roster "\
                   +"SET allyCode = "+str(p_allyCode)+", "\
                   +"    defId = '"+c_defId+"', "\
                   +"    combatType = "+str(c_combatType)+", "\
                   +"    forceAlignment = "+str(c_forceAlignment)+", "\
                   +"    gear = "+str(c_gear)+", "\
                   +"    gp = "+str(c_gp)+", "\
                   +"    level = "+str(c_level)+", "\
                   +"    nameKey = '"+c_nameKey+"', "\
                   +"    rarity = "+str(c_rarity)+", "\
                   +"    relic_currentTier = "+str(c_relic_currentTier)+" "

            for i_eqpt in range(6):
                if c_equipped[i_eqpt] != '':
                   query += ",eqpt"+str(i_eqpt+1)+" = '"+c_equipped[i_eqpt]+"'"

            if "stats" in character:
                stat_type = "final"
                if stat_type in character["stats"]:
                    for stat_id in ['1', '5', '6', '7', '14', '16', '17', '18', '28']:
                        stat_value = 0
                        if stat_id in character["stats"][stat_type]:
                            stat_value = character["stats"][stat_type][stat_id]
                        
                        query += ",stat"+stat_id+" = "+str(stat_value)+" "

            query +="WHERE allyCode = "+str(p_allyCode)+" "\
                   +"AND   defId = '"+c_defId+"'"

            goutils.log("DBG", "update_player", query)
            cursor.execute(query)
            mysql_db.commit()

            #Get DB index rroster_id for next queries
            query = "SELECT id FROM roster WHERE allyCode = "+str(p_allyCode)+" AND defId = '"+c_defId+"'"
            goutils.log("DBG", "update_player", query)
            roster_id = get_value(query)
            goutils.log("DBG", "update_player", "roster_id="+str(roster_id))

            #Get existing mod IDs from DB
            query = "SELECT id FROM mods WHERE roster_id = "+str(roster_id)
            goutils.log("DBG", "update_player", query)
            previous_mods_ids = get_column(query)
            goutils.log("DBG", "update_player", previous_mods_ids)

            ## GET DEFINITION OF MODS ##
            current_mods_ids = []
            for mod in character['mods']:
                mod_id = mod['id']
                mod_level = mod['level']
                mod_pips = mod['pips']
                mod_primaryStat_unitStat = mod['primaryStat']['unitStat']
                mod_primaryStat_value = mod['primaryStat']['value']
                
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
                    mod_secondaryStat_unitStats.append(sec_stat['unitStat'])
                    mod_secondaryStat_values.append(sec_stat['value'])
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
                    
                mod_set = mod['set']
                mod_slot = mod['slot']
                mod_tier = mod['tier']

                current_mods_ids.append(mod_id)
        
                query = "INSERT IGNORE INTO mods(id) "\
                       +"VALUES('"+mod_id+"')"
                goutils.log("DBG", "update_player", query)
                cursor.execute(query)
    
                query = "UPDATE mods "\
                       +"SET roster_id = "+str(roster_id)+", "\
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
                goutils.log("DBG", "update_player", query)
                cursor.execute(query)

            #remove mods not used anymore
            to_be_removed_mods_ids = tuple(set(previous_mods_ids)-set(current_mods_ids))
            if len(to_be_removed_mods_ids) > 0:
                query = "DELETE FROM mods WHERE id IN "+ str(tuple(to_be_removed_mods_ids)).replace(",)", ")")
                goutils.log("DBG", "update_player", query)
                cursor.execute(query)

            ## GET DEFINITION OF CAPACITIES ##
            c_zeta_count = 0
            for capa in character['skills']:
                capa_name = capa['id']
                capa_level = capa['tier']
                capa_isZeta = capa['isZeta']
                
                capa_omicron_type = ""
                capa_omicron_tier = "-1"
                if character_id in dict_zetas:
                    if capa_name in dict_zetas[character_id]:
                        capa_omicron_type = dict_zetas[character_id][capa_name][3]
                        capa_omicron_tier = dict_zetas[character_id][capa_name][4]
                
                capa_shortname = capa_name[0].upper()
                if capa_shortname in 'SU' and capa_name[-1] in '0123456789':
                    capa_shortname += capa_name[-1]
                goutils.log2("DBG", capa_name + " >> " + capa_shortname)
                    
                if capa_name == 'uniqueskill_GALACTICLEGEND01':
                    capa_shortname = 'GL'
                    
                if capa_isZeta == 1 and capa_level >= 8:
                    c_zeta_count += 1
        
                #launch query to update skills
                query = "INSERT IGNORE INTO roster_skills(roster_id, name) "\
                       +"VALUES("+str(roster_id)+", '"+capa_shortname+"')"
                goutils.log("DBG", "update_player", query)
                cursor.execute(query)

                query = "UPDATE roster_skills "\
                       +"SET level = "+str(capa_level)+", "\
                       +"isZeta = "+str(capa_isZeta)+", "\
                       +"omicron_type = '"+capa_omicron_type+"', "\
                       +"omicron_tier = "+str(capa_omicron_tier)+" "\
                       +"WHERE roster_id = "+str(roster_id)+" "\
                       +"AND name = '"+capa_shortname+"'"
                goutils.log("DBG", "update_player", query)
                cursor.execute(query)

            #Update zeta count in roster element
            query = "UPDATE roster "\
                   +"SET zeta_count = "+str(c_zeta_count)+" "\
                   +"WHERE allyCode = "+str(p_allyCode)+" "\
                   +"AND   defId = '"+c_defId+"'"
            goutils.log2("DBG", query)
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
        goutils.log("DBG", "update_player", query)
        cursor.execute(query)

        query = "UPDATE gp_history "\
               +"SET guildName = '"+p_guildName.replace("'", "''")+"', "\
               +"    arena_char_rank = "+ p_arena_char_rank_txt + ", "\
               +"    arena_char_po_delta_minutes = "+ str(delta_time_po_char) + ", "\
               +"    arena_ship_rank = "+ p_arena_ship_rank_txt + ","\
               +"    arena_ship_po_delta_minutes = "+ str(delta_time_po_ship) + ", "\
               +"    grand_arena_rank = '"+ p_grand_arena_rank + "',"\
               +"    char_gp = "+str(p_char_gp)+", "\
               +"    ship_gp = "+str(p_ship_gp)+" "\
               +"WHERE date = CURDATE() "\
               +"AND allyCode = "+str(p_allyCode)
        goutils.log("DBG", "update_player", query)
        cursor.execute(query)

        mysql_db.commit()
    except Error as error:
        goutils.log("ERR", "update_player", error)
        return -1
        
    finally:
        cursor.close()
    
    return 0
