import os
import sys
import urllib.parse
import mysql.connector
from mysql.connector import MySQLConnection, Error
import go
import connect_gsheets
import datetime

dict_forbidden_columns = {'index': 'index_'}

def connect():
    # Recover DB information from URL
    urllib.parse.uses_netloc.append('mysql')
    try:
        if 'CLEARDB_DATABASE_URL' in os.environ:
            url = urllib.parse.urlparse(os.environ['CLEARDB_DATABASE_URL'])
            # 'NAME': url.path[1:],
            # 'USER': url.username,
            # 'PASSWORD': url.password,
            # 'HOST': url.hostname,
            # 'PORT': url.port,
                
        else:
            print('ERR: environment variable "CLEARDB_DATABASE_URL" not set')
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
                for fetch in cur.fetchall():
                    rows.append(str(fetch))
        
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
        
        run_query(cursor, "CALL update_player("+
                                str(p_allyCode)+","+
                                "'"+p_guildName+"',"+
                                "'"+p_id+"',"+
                                "'"+p_lastActivity+"',"+
                                str(p_level)+","+
                                "'"+p_name+"',"+
                                str(p_poUTCOffsetMinutes)+","+
                                "@player_id)")
        cursor.execute("SELECT @player_id")                        
        p_player_id = cursor.fetchall()[0][0]
        # print('p_player_id: '+str(p_player_id))
        
        # Update the roster
        list_values_roster=[]
        for character in dict_player['roster']:
            p_combatType = character['combatType']
            p_defId = character['defId']
            p_gear = character['gear']
            p_gp = character['gp']
            p_level = character['level']
            p_nameKey = character['nameKey']
            p_rarity = character['rarity']
            p_relic_currentTier = 0
            if character['relic'] != None:
                p_relic_currentTier = character['relic']['currentTier']
                            
            mod_definition_txt=""
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

            list_values_roster.append((p_player_id, p_combatType, p_defId, p_gear, p_gp, p_level,
                                       p_nameKey, p_rarity, p_relic_currentTier, mod_definition_txt))

        query = "CALL update_roster(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
        # run_querymany(cursor, query, list_values_roster)
        
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

def run_querymany(cursor, query, values):
    try:
        # print('query: '+query)
        # print('values: '+str(values))
        cursor.executemany(query, values)
    except Error as error:
        print(error)


    