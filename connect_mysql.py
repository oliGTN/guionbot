import os
import sys
import urllib.parse
import mysql.connector
from mysql.connector import MySQLConnection, Error
import datetime

dict_forbidden_columns = {'index': 'index_'}

def connect():
    # Recover DB information from URL
    urllib.parse.uses_netloc.append('mysql')
    try:
        if 'MYSQL_DATABASE_URL' in os.environ:
            url = urllib.parse.urlparse(os.environ['MYSQL_DATABASE_URL'])
            # 'NAME': url.path[1:],
            # 'USER': url.username,
            # 'PASSWORD': url.password,
            # 'HOST': url.hostname,
            # 'PORT': url.port,
                
        else:
            print('ERR: environment variable "MYSQL_DATABASE_URL" not set')
            return
    except Exception:
        print('Unexpected error:', sys.exc_info())
        return
    
    # Connect to DB
    cleardb_conn = None
    try:
        # print('Connecting to MySQL database...')
        cleardb_conn = mysql.connector.connect(host=url.hostname,
                                       database=url.path[1:],
                                       user=url.username,
                                       password=url.password)
        if cleardb_conn.is_connected():
            # print('Connected to MySQL database')
            pass
        else:
            print('Connection failed')

    except Error as e:
        print(e)
    
    return cleardb_conn
    
def insert_members():
    dict_players_by_IG, dict_players_by_ID = connect_gsheets.load_config_players()
    query = "INSERT INTO members(allycode,ig_name,discord_id,is_officier) " \
            "VALUES(%s,%s,%s,%s)"

    list_members=[]
    for ig_name in dict_players_by_IG:
        # print(ig_name)
        # print(dict_players_by_IG[ig_name])
        allycode = str(dict_players_by_IG[ig_name][0])
        display_name = dict_players_by_IG[ig_name][2]
        if display_name[0] == '<':
            discord_id = str(display_name[2:20])
            is_officer = dict_players_by_ID[int(discord_id)][1]
        else:
            discord_id = ''
            is_officer = False
        list_members.append((allycode, ig_name, discord_id, int(is_officer)))
        # print(list_members)
        
    try:
        db=connect()
        cursor = db.cursor()
        cursor.executemany(query, list_members)

        db.commit()
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        db.close()
        # print('Connection to MySQL closed')

def simple_query(query):
    rows = []
    try:
        db=connect()
        cursor = db.cursor()
        
        results = cursor.execute(query, multi=True)
        for cur in results:
            # rows.append('cursor: '+ str(cur))
            if cur.with_rows:
                results = cur.fetchall()
            
                widths = []
                columns = []
                tavnit = '|'
                separator = '+' 
                
                index = 0
                for cd in cur.description:
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
        
        db.commit()
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        db.close()
    
    return rows
    
def update_player(dict_player):
    try:
        db=connect()
        cursor = db.cursor()
        
        # Update basic player information
        p_allyCode = dict_player['allyCode']
        p_guildName = dict_player['guildName']
        p_id = dict_player['id']

        p_lastActivity_player = dict_player['lastActivity']
        p_lastActivity_ts = datetime.datetime.fromtimestamp(p_lastActivity_player/1000)
        p_lastActivity = p_lastActivity_ts.strftime('%Y-%m-%d %H:%M:%S')

        p_level = dict_player['level']
        p_name = dict_player['name']
        p_poUTCOffsetMinutes = dict_player['poUTCOffsetMinutes']
                      
        # Update the roster
        roster_definition_txt="" #separator /
        for character in dict_player['roster']:
            c_combatType = character['combatType']
            c_defId = character['defId']
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
                            
            mod_definition_txt="" #separator |
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

            roster_definition_txt+=str(c_combatType)+","+ \
                                   c_defId+","+ \
                                   str(c_gear)+","+ \
                                   str(c_gp)+","+ \
                                   str(c_level)+","+ \
                                   c_nameKey+","+ \
                                   str(c_rarity)+","+ \
                                   str(c_relic_currentTier)+","+ \
                                   str(c_equipped[0])+","+ \
                                   str(c_equipped[1])+","+ \
                                   str(c_equipped[2])+","+ \
                                   str(c_equipped[3])+","+ \
                                   str(c_equipped[4])+","+ \
                                   str(c_equipped[5])+","+ \
                                   mod_definition_txt+"/"

        # Launch the unique update with all information
        query_parameters = (p_allyCode,
                            p_guildName,
                            p_id,
                            p_lastActivity,
                            p_level,
                            p_name,
                            p_poUTCOffsetMinutes,
                            roster_definition_txt)
        # print("CALL update_player"+str(query_parameters))
        cursor.callproc('update_player', query_parameters)
          
        db.commit()
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        db.close()

def update_unit(dict_unit):
    try:
        db=connect()
        cursor = db.cursor()
        
        # Update basic unit information
        u_baseId = dict_unit['baseId']
        u_combatType = dict_unit['combatType']
        u_descKey = dict_unit['descKey']
        u_forceAlignment = dict_unit['forceAlignment']
        u_unit_id = dict_unit['id']
        u_nameKey = dict_unit['nameKey']
        u_obtainable = dict_unit['obtainable']
              
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
                            u_obtainable,
                            tier_definition_txt)
        print("CALL update_unit"+str(query_parameters))
        cursor.callproc('update_unit', query_parameters)
          
        db.commit()
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        db.close()

def update_eqpt(dict_eqpt):
    try:
        db=connect()
        cursor = db.cursor()
        
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
          
        db.commit()
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        db.close()
        
def run_query(cursor, query):
    try:
        # print(query)
        cursor.execute(query)
    except Error as error:
        print(error)

def export_procedures():
    try:
        db=connect()
        cursor = db.cursor()
        cursor.execute("SHOW PROCEDURE STATUS")
        results = cursor.fetchall()
        for r in results:
            proc_name = r[1]
            cursor.execute("SHOW CREATE PROCEDURE "+proc_name)
            for line in cursor.fetchall():
                print (line[2])
        
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        db.close()

    