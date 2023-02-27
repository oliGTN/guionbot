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
        goutils.log("DBG", "insert_roster_evo", query)
        cursor.execute(query)

        mysql_db.commit()
    except Error as error:
        goutils.log("ERR", "insert_roster_evo", error)
        return -1
        
    finally:
        if cursor != None:
            cursor.close()
    
def update_player(dict_player):
    dict_unitsList = data.get("unitsList_dict.json")
    dict_capas = data.get("unit_capa_list.json")
    cursor = None
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
                if character_id in dict_capas:
                    if capa_name in dict_capas[character_id]:
                        capa_omicron_type = dict_capas[character_id][capa_name][3]
                        capa_omicron_tier = dict_capas[character_id][capa_name][4]
                
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
        goutils.log2("DBG", query)
        p_modq = get_value(query)

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
        goutils.log2("DBG", query)
        cursor.execute(query)

        query = "UPDATE gp_history "\
               +"SET guildName = '"+p_guildName.replace("'", "''")+"', "\
               +"    arena_char_rank = "+ p_arena_char_rank_txt + ", "\
               +"    arena_char_po_delta_minutes = "+ str(delta_time_po_char) + ", "\
               +"    arena_ship_rank = "+ p_arena_ship_rank_txt + ","\
               +"    arena_ship_po_delta_minutes = "+ str(delta_time_po_ship) + ", "\
               +"    grand_arena_rank = '"+ p_grand_arena_rank + "',"\
               +"    char_gp = "+str(p_char_gp)+", "\
               +"    ship_gp = "+str(p_ship_gp)+", "\
               +"    modq = "+str(p_modq)+" "\
               +"WHERE date = CURDATE() "\
               +"AND allyCode = "+str(p_allyCode)
        goutils.log("DBG", "update_player", query)
        cursor.execute(query)

        mysql_db.commit()
    except Error as error:
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
            query = "SELECT allyCode FROM players WHERE name = '"+player_name+"'"
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
def load_config_players(guild_name):
    query = "SELECT allyCode, name, discord_id, guildMemberLevel FROM players "
    query+= "WHERE guildName = '"+guild_name+"'"
    goutils.log2("DBG", query)
    data_db = get_table(query)

    dict_players_by_IG = {}
    dict_players_by_ID = {}

    list_did = [x[2] for x in data_db]
    for line in data_db:
        ac = line[0]
        name = line[1]
        did = line[2]
        isOff = (line[3]!=2)

        if list_did.count(did) == 1:
            dict_players_by_IG[name] = [ac, "<@"+did+">"]
        else:
            dict_players_by_IG[name] = [ac, "<@"+did+"> ["+name+"]"]
        dict_players_by_ID[did] = [ac, isOff]

    return dict_players_by_IG, dict_players_by_ID


