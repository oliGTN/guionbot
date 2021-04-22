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
            if 'MYSQL_DATABASE_URL' in config:
                url = urllib.parse.urlparse(config.MYSQL_DATABASE_URL)
                # 'NAME': url.path[1:],
                # 'USER': url.username,
                # 'PASSWORD': url.password,
                # 'HOST': url.hostname,
                # 'PORT': url.port,
                    
            else:
                print('ERR: configuration variable "MYSQL_DATABASE_URL" not set')
                return
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
            c_forceAlignment = dict_units[c_defId]['forceAlignment']
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
        # print("CALL update_player"+str(query_parameters))
        ret = cursor.callproc('update_player', query_parameters)
        mysql_db.commit()
    except Error as error:
        print(error)
        return -1
        
    finally:
        cursor.close()
        # db.close()
    
    return 0

def update_unit(dict_unit):
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor()
        
        # Update basic unit information
        u_baseId = dict_unit['baseId']
        u_combatType = dict_unit['combatType']
        u_descKey = dict_unit['descKey']
        u_forceAlignment = dict_unit['forceAlignment']
        u_unit_id = dict_unit['id']
        u_nameKey = dict_unit['nameKey']
              
        tier_definition_txt="" #separator /
        # Update the baseStats as tier 0
        t_equipmentSet1 = 0
        t_equipmentSet2 = 0
        t_equipmentSet3 = 0
        t_equipmentSet4 = 0
        t_equipmentSet5 = 0
        t_equipmentSet6 = 0
        t_tier = 0

        stat_definition_txt="" #separator |
        for stat in dict_unit['baseStat']['statList']:
            s_scalar = stat['scalar']
            s_statValueDecimal = stat['statValueDecimal']
            s_uiDisplayOverrideValue = stat['uiDisplayOverrideValue']
            s_unitStatId = stat['unitStatId']
            s_unscaledDecimalValue = stat['unscaledDecimalValue']
        
            stat_definition_txt+=str(s_scalar)+","+ \
                                 str(s_statValueDecimal)+","+ \
                                 str(s_uiDisplayOverrideValue)+","+ \
                                 str(s_unitStatId)+","+ \
                                 str(s_unscaledDecimalValue)+"|"
                                 
        tier_definition_txt+=str(t_equipmentSet1)+","+ \
                             str(t_equipmentSet1)+","+ \
                             str(t_equipmentSet1)+","+ \
                             str(t_equipmentSet1)+","+ \
                             str(t_equipmentSet1)+","+ \
                             str(t_equipmentSet1)+","+ \
                             str(t_equipmentSet1)+","+ \
                             stat_definition_txt+"/"
        
        # Update the baseStats per tier in unitTierList
        for tier in dict_unit['unitTierList']:
            t_equipmentSet1 = tier['equipmentSetList'][0]
            t_equipmentSet2 = tier['equipmentSetList'][1]
            t_equipmentSet3 = tier['equipmentSetList'][2]
            t_equipmentSet4 = tier['equipmentSetList'][3]
            t_equipmentSet5 = tier['equipmentSetList'][4]
            t_equipmentSet6 = tier['equipmentSetList'][5]
            t_tier = tier['tier']

            stat_definition_txt="" #separator |
            for stat in tier['baseStat']['statList']:
                s_scalar = stat['scalar']
                s_statValueDecimal = stat['statValueDecimal']
                s_uiDisplayOverrideValue = stat['uiDisplayOverrideValue']
                s_unitStatId = stat['unitStatId']
                s_unscaledDecimalValue = stat['unscaledDecimalValue']
            
                stat_definition_txt+=str(s_scalar)+","+ \
                                     str(s_statValueDecimal)+","+ \
                                     str(s_uiDisplayOverrideValue)+","+ \
                                     str(s_unitStatId)+","+ \
                                     str(s_unscaledDecimalValue)+"|"
            tier_definition_txt+=t_equipmentSet1+","+ \
                                 t_equipmentSet2+","+ \
                                 t_equipmentSet3+","+ \
                                 t_equipmentSet4+","+ \
                                 t_equipmentSet5+","+ \
                                 t_equipmentSet6+","+ \
                                 str(t_tier)+","+ \
                                 stat_definition_txt+"/"

        # Launch the unique update with all information
        query_parameters = (u_baseId,
                            u_combatType,
                            u_descKey,
                            u_forceAlignment,
                            u_unit_id,
                            u_nameKey,
                            tier_definition_txt)
        print("CALL update_unit"+str(query_parameters))
        cursor.callproc('update_unit', query_parameters)
          
        mysql_db.commit()
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        # db.close()

def update_eqpt(dict_eqpt):
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor()
        
        # Update basic unit information
        e_eqpt_id = dict_eqpt['id']
        e_mark = dict_eqpt['mark']
        e_nameKey = dict_eqpt['nameKey']
        e_recipeId = dict_eqpt['recipeId']
        e_requiredLevel = dict_eqpt['requiredLevel']
        e_requiredRarity = dict_eqpt['requiredRarity']
        e_sellValue_bonusQuantity = dict_eqpt['sellValue']['bonusQuantity']
        e_sellValue_currency = dict_eqpt['sellValue']['currency']
        e_sellValue_quantity = dict_eqpt['sellValue']['quantity']
        e_tier = dict_eqpt['tier']
        e_type = dict_eqpt['type']
              
        stat_lookup_raid_definition_txt=""
        
        # get equipmentStat
        nb_stat = 0
        for stat in dict_eqpt['equipmentStat']['statList']:
            s_scalar = stat['scalar']
            s_statValueDecimal = stat['statValueDecimal']
            s_uiDisplayOverrideValue = stat['uiDisplayOverrideValue']
            s_unitStatId = stat['unitStatId']
            s_unscaledDecimalValue = stat['unscaledDecimalValue']
        
            stat_lookup_raid_definition_txt+=str(s_scalar)+","+ \
                                             str(s_statValueDecimal)+","+ \
                                             str(s_uiDisplayOverrideValue)+","+ \
                                             str(s_unitStatId)+","+ \
                                             str(s_unscaledDecimalValue)+"|"
            nb_stat+=1
        
        #remove last | and add a /
        if nb_stat > 0:
            stat_lookup_raid_definition_txt = stat_lookup_raid_definition_txt[:-1]
        stat_lookup_raid_definition_txt = stat_lookup_raid_definition_txt+'/'
        
        # get lookupMissionList
        nb_lookupMission = 0
        for mission in dict_eqpt['lookupMissionList']:
            m_event = mission['event']
            m_campaignId = mission['missionIdentifier']['campaignId']
            m_campaignMapId = mission['missionIdentifier']['campaignMapId']
            m_campaignMissionId = mission['missionIdentifier']['campaignMissionId']
            m_campaignNodeDifficulty = mission['missionIdentifier']['campaignNodeDifficulty']
            m_campaignNodeId = mission['missionIdentifier']['campaignNodeId']
        
            stat_lookup_raid_definition_txt+=str(int(m_event))+","+ \
                                             m_campaignId+","+ \
                                             m_campaignMapId+","+ \
                                             m_campaignMissionId+","+ \
                                             str(m_campaignNodeDifficulty)+","+ \
                                             m_campaignNodeId+"|"
            nb_lookupMission+=1

        #remove last | and add a /
        if nb_lookupMission > 0:
            stat_lookup_raid_definition_txt = stat_lookup_raid_definition_txt[:-1]
        stat_lookup_raid_definition_txt = stat_lookup_raid_definition_txt+'/'

        # get raidLookupList
        nb_raidMission = 0
        for mission in dict_eqpt['raidLookupList']:
            m_event = mission['event']
            m_campaignId = mission['missionIdentifier']['campaignId']
            m_campaignMapId = mission['missionIdentifier']['campaignMapId']
            m_campaignMissionId = mission['missionIdentifier']['campaignMissionId']
            m_campaignNodeDifficulty = mission['missionIdentifier']['campaignNodeDifficulty']
            m_campaignNodeId = mission['missionIdentifier']['campaignNodeId']
        
            stat_lookup_raid_definition_txt+=str(int(m_event))+","+ \
                                             m_campaignId+","+ \
                                             m_campaignMapId+","+ \
                                             m_campaignMissionId+","+ \
                                             str(m_campaignNodeDifficulty)+","+ \
                                             m_campaignNodeId+"|"
            nb_raidMission+=1

        #remove last |
        if nb_raidMission > 0:
            stat_lookup_raid_definition_txt = stat_lookup_raid_definition_txt[:-1]

        # Launch the unique update with all information
        query_parameters = (e_eqpt_id,
                            e_mark,
                            e_nameKey,
                            e_recipeId,
                            e_requiredLevel,
                            e_requiredRarity,
                            e_sellValue_bonusQuantity,
                            e_sellValue_currency,
                            e_sellValue_quantity,
                            e_tier,
                            e_type,
                            stat_lookup_raid_definition_txt)
                            
        print("CALL update_equipment"+str(query_parameters))
        cursor.callproc('update_equipment', query_parameters)
          
        mysql_db.commit()
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        # db.close()

def update_gameData(dict_gameData):
    try:
        mysql_db = db_connect()
        cursor = mysql_db.cursor()
        
        # update crTables with mastery information
        mastery_definition_txt="" #separator |
        for key in dict_gameData['crTables']:
            if key[-8:] == '_mastery':
                masteryModifierID = key
                
                stat_definition_txt = ''
                for stat in dict_gameData['crTables'][masteryModifierID]:
                    stat_id = stat
                    stat_value = dict_gameData['crTables'][masteryModifierID][stat]
                    
                    stat_definition_txt+=str(stat_id)+","+ \
                                         str(stat_value)+"|"
                                 
                #remove last |
                stat_definition_txt = stat_definition_txt[:-1]

                mastery_definition_txt+=masteryModifierID+","+ \
                                        stat_definition_txt+"/"
        
        #remove last /
        mastery_definition_txt = mastery_definition_txt[:-1]

        # Launch the unique update with all information
        query_parameters = (mastery_definition_txt,)
        print("CALL update_mastery"+str(query_parameters))
        cursor.callproc('update_mastery', query_parameters)
          
        ######################################################
        # update growthModifier and primaryStat for units
        units_definition_txt="" #separator |
        for unit_id in dict_gameData['unitData']:
            print(unit_id)
            primaryStat = dict_gameData['unitData'][unit_id]['primaryStat']
            
            masteryModifierID = ''
            if 'masteryModifierID' in dict_gameData['unitData'][unit_id]:
                masteryModifierID = dict_gameData['unitData'][unit_id]['masteryModifierID']
            
            growth_definition_txt = ''  #separator /
            for rarity in dict_gameData['unitData'][unit_id]['growthModifiers']:
                value2 = dict_gameData['unitData'][unit_id]['growthModifiers'][rarity]['2']
                value3 = dict_gameData['unitData'][unit_id]['growthModifiers'][rarity]['3']
                value4 = dict_gameData['unitData'][unit_id]['growthModifiers'][rarity]['4']
                
                growth_definition_txt+=rarity+","+ \
                                       str(value2)+","+ \
                                       str(value3)+","+ \
                                       str(value4)+"|"
                             
            #remove last |
            growth_definition_txt = growth_definition_txt[:-1]

            units_definition_txt+=unit_id+","+ \
                                   str(primaryStat)+","+ \
                                   masteryModifierID+","+ \
                                   growth_definition_txt+"/"
        
        #remove last /
        units_definition_txt = units_definition_txt[:-1]

        # Launch the unique update with all information
        query_parameters = (units_definition_txt,)
        print("CALL update_units_gameData"+str(query_parameters))
        cursor.callproc('update_units_gameData', query_parameters)
        
        mysql_db.commit()
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        # db.close()
        
# def run_query(cursor, query):
    # try:
        # print(query)
        # cursor.execute(query)
    # except Error as error:
        # print(error)
