import os
import sys
import urllib.parse
import mysql.connector
from mysql.connector import MySQLConnection, Error
import go
import connect_gsheets

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
        print('Connecting to MySQL database...')
        cleardb_conn = mysql.connector.connect(host=url.hostname,
                                       database=url.path[1:],
                                       user=url.username,
                                       password=url.password)
        if cleardb_conn.is_connected():
            print('Connected to MySQL database')
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
        
        if cursor.lastrowid:
            print('last insert id', cursor.lastrowid)
        else:
            print('last insert id not found')

        db.commit()
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        db.close()

def simple_query(query):
    rows = []
    try:
        db=connect()
        cursor = db.cursor()
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        db.commit()
    except Error as error:
        print(error)
        
    finally:
        cursor.close()
        db.close()
    
    return rows