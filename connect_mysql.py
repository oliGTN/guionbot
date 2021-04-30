import os
import config
import sys
import urllib.parse
import mysql.connector
from mysql.connector import MySQLConnection, Error
import datetime
import goutils
import connect_crinolo

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
            print('Unexpected error in connect:', sys.exc_info())
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
                print('Connection failed')

        except Error as e:
            print('Exception during connect: '+str(e))
            
    return mysql_db
        
def update_guild_teams(dict_team):
#         dict_teams {key=team_name,
#                     value=[[catégorie, nombre nécessaire,
#                               {key=nom,
#                                value=[id, étoiles min, gear min, étoiles reco,
#                                       gear reco, liste zeta, vitesse, nom court]
#                                }
#                             ], ...]
#                      }
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor()

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
        print(error)
        
    finally:
        cursor.close()
        # db.close()

def simple_query(query, txt_mode):
    rows = []
    tuples = []
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor()
        
        results = cursor.execute(query, multi=True)
        for cur in results:
            # rows.append('cursor: '+ str(cur))
            if cur.with_rows:
                results = cur.fetchall()
                tuples.append(results)
            
                if txt_mode:
                    widths = []
                    columns = []
                    tavnit = '|'
                    separator = '+' 
                    
                    index = 0
                    for cd in cur.description:
                        #print(results)
                        max_col_length = max(list(map(lambda x: len(str(x[index])), results)))
                        widths.append(max(max_col_length, len(cd[0])))
                        columns.append(cd[0])
                        index+=1

                    for w in widths:
                        tavnit += " %-"+"%s.%ss |" % (w,w)
                        separator += '-'*w + '--+'

                    rows.append(separator)
                    rows.append(tavnit % tuple(columns))
                    rows.append(separator)

                    for fetch in results:
                        rows.append(tavnit % fetch)

                    rows.append(separator)
        
        mysql_db.commit()
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        # db.close()
    
    if txt_mode:
        return rows
    else:
        return tuples
        
        
def simple_callproc(proc_name, args):
    rows = []
    tuples = []
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor()
        #print("simple_callproc: "+proc_name+" "+str(args))
        ret=cursor.callproc(proc_name, args)
        #print(ret)
        
        mysql_db.commit()
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        # db.close()

def get_value(query):
    tuples = []
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor()
        
        results = cursor.execute(query, multi=True)
        for cur in results:
            # rows.append('cursor: '+ str(cur))
            if cur.with_rows:
                results = cur.fetchall()
                tuples.append(results)

    except Error as error:
        print(error)
        
    finally:
        cursor.close()
    
    # print(query)
    # print(tuples)
    return tuples[0][0][0]
        
def get_column(query):
    tuples = []
    try:
        mysql_db = db_connect()
        #print("DBG: mysql_db="+str(mysql_db))
        cursor = mysql_db.cursor()
        #print("DBG: cursor="+str(cursor))
        
        results = cursor.execute(query, multi=True)
        for cur in results:
            # rows.append('cursor: '+ str(cur))
            if cur.with_rows:
                results = cur.fetchall()
                tuples.append(results)

    except Error as error:
        print(error)
        
    finally:
        cursor.close()

    return [x[0] for x in tuples[0]]
    
def get_line(query):
    tuples = []
    #print("get_line("+query+")")
    try:
        mysql_db = db_connect()
        #print("DBG: mysql_db="+str(mysql_db))
        cursor = mysql_db.cursor()
        #print("DBG: cursor="+str(cursor))
        
        results = cursor.execute(query, multi=True)
        for cur in results:
            # rows.append('cursor: '+ str(cur))
            if cur.with_rows:
                results = cur.fetchall()
                tuples.append(results)

    except Error as error:
        print(error)
        
    finally:
        cursor.close()
    
    if len(tuples[0]) == 0:
        return []
    else:
        return tuples[0][0]
    
def get_table(query):
    tuples = []
    try:
        #print("DBG: get_table db_connect")
        mysql_db = db_connect()
        #print("DBG: get_table cursor")
        #print("DBG: mysql_db="+str(mysql_db))
        cursor = mysql_db.cursor()
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
        print(error)
        
    finally:
        cursor.close()

    #print("DBG: get_table return")
    return tuples[0]

def update_guild(dict_guild):
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor()
        
        # Manage guild names with a ' in it
        guild_name = dict_guild["name"].replace("'", "''")
        
        query = "REPLACE INTO guilds(name) VALUES('"+guild_name+"')"
        cursor.execute(query)

        players_in_db = get_column("SELECT allyCode FROM players")
        guild_players_in_db = get_column("SELECT allyCode FROM players WHERE guildName='"+guild_name+"'")
        players_in_api = [x["allyCode"] for x in dict_guild["roster"]]
        
        for player_api in dict_guild["roster"]:
            if not player_api["allyCode"] in players_in_db:
                # insert empty player to allow the update process
                # force lastUpdated to 24h in the past
                player_name = player_api["name"].replace("'", "''")
                query = "INSERT INTO players (allyCode,name,guildName,lastUpdated) \
                        VALUES ("+str(player_api["allyCode"])+",'" + \
                        player_name+"','"+ \
                        guild_name+"',CURRENT_TIMESTAMP-INTERVAL 24 HOUR)"
                print(query)
                cursor.execute(query)
                                                
        for allyCode_db in guild_players_in_db:
            if not allyCode_db in players_in_api:
                query = "UPDATE players SET guildName='' WHERE allyCode="+str(allyCode_db)
                print(query)
                cursor.execute(query)
          
        mysql_db.commit()
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        # db.close()       
        
        
def update_player(dict_player, dict_units):
    #Start by getting all stats for the player
    dict_player = connect_crinolo.add_stats(dict_player)

    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor()
        
        # Update basic player information
        p_allyCode = dict_player['allyCode']
        p_guildName = dict_player['guildName']
        p_id = dict_player['id']

        p_lastActivity_player = dict_player['lastActivity']
        p_lastActivity_ts = datetime.datetime.fromtimestamp(p_lastActivity_player/1000)
        p_lastActivity = p_lastActivity_ts.strftime('%Y-%m-%d %H:%M:%S')

        p_level = dict_player['level']
        p_name = dict_player['name']
        p_arena_char_rank = dict_player['arena']['char']['rank']
        p_arena_ship_rank = dict_player['arena']['ship']['rank']

        for stat in dict_player['stats']:
            if stat['nameKey'] == "Puissance Galactique (personnages)\u00a0:":
                p_char_gp = stat['value']
            elif stat['nameKey'] == "Puissance Galactique (vaisseaux)\u00a0:":
                p_ship_gp = stat['value']

        p_poUTCOffsetMinutes = dict_player['poUTCOffsetMinutes']
                      
        # Update the roster
        roster_definition_txt="" #separator \
        # 1,MAGMATROOPER,gear,gp,level,,rarity,relicTier,eq1,eq2,eq3,eq4,eq5,eq6/<mod1>|<mod2>/capa1,lvl1|capa2,lvl2\capa3,lvl3\1,GREEFKARGA...
        for character in dict_player['roster']:
            c_combatType = character['combatType']
            c_defId = character['defId']
            if c_defId in dict_units:
                c_forceAlignment = dict_units[c_defId]['forceAlignment']
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
                            
            ## GET DEFINITION OF MODS ##
            mod_definition_txt="" #separator |
            # level,pips,sPrim,vPrim,sSec1,vSec1,sSec2,vSec2,sSec3,vSec3,sSec4,vSec4,set,slot,tier
            mod_count = 0
            for mod in character['mods']:
                mod_level = mod['level']
                mod_pips = mod['pips']
                mod_primaryStat_unitStat = mod['primaryStat']['unitStat']
                mod_primaryStat_value = mod['primaryStat']['value']
                
                mod_secondaryStat_unitstats=[]
                mod_secondaryStat_values=[]
                mod_secondaryStat1_unitstat=0
                mod_secondaryStat1_value=0
                mod_secondaryStat2_unitstat=0
                mod_secondaryStat2_value=0
                mod_secondaryStat3_unitstat=0
                mod_secondaryStat3_value=0
                mod_secondaryStat4_unitstat=0
                mod_secondaryStat4_value=0
                for sec_stat in mod['secondaryStat']:
                    mod_secondaryStat_unitstats.append(sec_stat['unitStat'])
                    mod_secondaryStat_values.append(sec_stat['value'])
                if len(mod_secondaryStat_unitstats)>0:
                    mod_secondaryStat1_unitstat = mod_secondaryStat_unitstats[0]
                    mod_secondaryStat1_value = mod_secondaryStat_values[0]
                if len(mod_secondaryStat_unitstats)>1:
                    mod_secondaryStat2_unitstat = mod_secondaryStat_unitstats[1]
                    mod_secondaryStat2_value = mod_secondaryStat_values[1]
                if len(mod_secondaryStat_unitstats)>2:
                    mod_secondaryStat3_unitstat = mod_secondaryStat_unitstats[2]
                    mod_secondaryStat3_value = mod_secondaryStat_values[2]
                if len(mod_secondaryStat_unitstats)>3:
                    mod_secondaryStat4_unitstat = mod_secondaryStat_unitstats[3]
                    mod_secondaryStat4_value = mod_secondaryStat_values[3]
                    
                mod_set = mod['set']
                mod_slot = mod['slot']
                mod_tier = mod['tier']
        
                mod_definition_txt+=str(mod_level)+","+ \
                                    str(mod_pips)+","+ \
                                    str(mod_primaryStat_unitStat)+","+str(mod_primaryStat_value)+","+ \
                                    str(mod_secondaryStat1_unitstat)+","+str(mod_secondaryStat1_value)+","+ \
                                    str(mod_secondaryStat2_unitstat)+","+str(mod_secondaryStat2_value)+","+ \
                                    str(mod_secondaryStat3_unitstat)+","+str(mod_secondaryStat3_value)+","+ \
                                    str(mod_secondaryStat4_unitstat)+","+str(mod_secondaryStat4_value)+","+ \
                                    str(mod_set)+","+ \
                                    str(mod_slot)+","+ \
                                    str(mod_tier)+"|"
                mod_count+=1
                
            # remove last "|"
            if mod_count>0:
                mod_definition_txt = mod_definition_txt[:-1]

            ## GET DEFINITION OF CAPACITIES ##
            capa_definition_txt="" #separator |
            # name,level,isZeta (name = B, L, Un, Sn, GL | isZeta = 0 or 1)
            capa_count = 0
            c_zeta_count = 0
            for capa in character['skills']:
                capa_name = capa['id']
                capa_level = capa['tier']
                capa_isZeta = capa['isZeta']
                
                capa_shortname = capa_name[0].upper()
                if capa_name[-1] in '0123456789':
                    capa_shortname += capa_name[-1]
                    
                if capa_name == 'uniqueskill_GALACTICLEGEND01':
                    capa_shortname = 'GL'
                    
                if capa_isZeta == 1 and capa_level == 8:
                    c_zeta_count += 1
        
                capa_definition_txt+=capa_shortname+","+ \
                                    str(capa_level)+","+ \
                                    str(int(capa_isZeta))+"|"
                capa_count+=1
                
            # remove last "|"
            if capa_count>0:
                capa_definition_txt = capa_definition_txt[:-1]

            ## SET DEFINITION OF STATS ##
            stat_definition_txt="" #separator |
            stat_count = 0
            for stat_type in ["base", "gear", "mods", "crew"]:
                if "stats" in character:
                    if stat_type in character["stats"]:
                        stat_list = character["stats"][stat_type]
                        for stat_id in stat_list:
                            stat_value = stat_list[stat_id]

                            if stat_value != 0:
                                stat_definition_txt+=str(stat_id)+","+ \
                                                    str(stat_value)+","+ \
                                                    stat_type+"|"
                                stat_count+=1
                    
            # remove last "|"
            if stat_count>0:
                stat_definition_txt = stat_definition_txt[:-1]

            ## FINALIZE DEFINITION OF CHARACTER WITH CAPAS, MODS,STATS ##
            roster_definition_txt+=str(c_combatType)+","+ \
                                   c_defId+","+ \
                                   str(c_forceAlignment)+","+ \
                                   str(c_gear)+","+ \
                                   str(c_gp)+","+ \
                                   str(c_level)+","+ \
                                   c_nameKey+","+ \
                                   str(c_rarity)+","+ \
                                   str(c_relic_currentTier)+","+ \
                                   str(c_zeta_count)+","+ \
                                   str(c_equipped[0])+","+ \
                                   str(c_equipped[1])+","+ \
                                   str(c_equipped[2])+","+ \
                                   str(c_equipped[3])+","+ \
                                   str(c_equipped[4])+","+ \
                                   str(c_equipped[5])+"/"+ \
                                   mod_definition_txt+"/" + \
                                   capa_definition_txt+"/" + \
                                   stat_definition_txt+"\\"

        # remove last "\"
        roster_definition_txt = roster_definition_txt[:-1]

        # Launch the unique update with all information
        query_parameters = (p_allyCode,
                            p_guildName,
                            p_id,
                            p_lastActivity,
                            p_level,
                            p_name,
                            p_arena_char_rank,
                            p_arena_ship_rank,
                            p_char_gp,
                            p_ship_gp,
                            p_poUTCOffsetMinutes,
                            roster_definition_txt)
        goutils.log("DBG", "update_player", "CALL update_player"+str(query_parameters))
        ret = cursor.callproc('update_player', query_parameters)
        mysql_db.commit()
    except Error as error:
        print(error)
        return -1
        
    finally:
        cursor.close()
        # db.close()
    
    return 0
