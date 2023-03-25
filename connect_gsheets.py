# tutorial: https://www.twilio.com/blog/2017/02/an-easy-way-to-read-and-write-to-a-google-spreadsheet-in-python.html
# bug: https://github.com/burnash/gspread/issues/513

import gspread
import os
import config
import sys
import json
import requests
import difflib
import datetime
from pytz import timezone
from oauth2client.service_account import ServiceAccountCredentials
import inspect
import traceback

import connect_mysql
import connect_rpc
import goutils
import data

# client est global pour garder le même en cas d'ouverture de plusieurs fichiers 
# ou plusieurs fois le même (gain de temps)
client=None

guild_timezone=timezone(config.GUILD_TIMEZONE)

def get_gfile_name(server_id):
    query = "SELECT gfile_name FROM guild_bot_infos WHERE server_id="+str(server_id)
    goutils.log2("DBG", query)
    return connect_mysql.get_value(query)

##############################################################
# Function: get_gapi_client
# Parameters: none
# Purpose: crée l'objet global client pour utilisation par
#          toutes les fonctions qui accèdent au fichier
# Output: none
##############################################################
def get_gapi_client():
    global client

    if client == None:
        # use creds to create a client to interact with the Google Drive API
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        try:
            creds_envVar = config.GAPI_CREDS
            creds_json = json.loads(creds_envVar)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
            client = gspread.authorize(creds)
        except KeyError as e:
            goutils.log2('ERR', 'variable de configuration GAPI_CREDS non définie')

def get_dict_columns(list_col_names, list_list_sheet):
    dict_columns = {}
    for i_col in range(len(list_list_sheet[0])):
        for col_name in list_col_names:
            if list_list_sheet[0][i_col] == col_name:
                dict_columns[col_name] = i_col
    return dict_columns

def get_sheet_url(server_id, sheet_name):
    gfile_name = get_gfile_name(server_id)
    if gfile_name==None or gfile_name=='':
        return None
    try:
        get_gapi_client()
        file = client.open(gfile_name)
        worksheet=file.worksheet(sheet_name)
    except Exception as e:
        goutils.log2("ERR", sys.exc_info()[0])
        goutils.log2("ERR", e)
        goutils.log2("ERR", traceback.format_exc())
        goutils.log2("WAR", "Cannot connect to Google API")
        return None

    worksheet_url = "https://docs.google.com/spreadsheets/d/" + file.id + "/edit#gid=" + str(worksheet.id)
    return worksheet_url

##############################################################
# Function: load_config_raids
# Parameters: None
# Purpose: lit l'onglet "Raids" du fichier Sheets
# Output: dict_raids {raid_alias:
#                       [full name,
#                          {team_name:
#                             [phase, normal, super]}]}
##############################################################
def load_config_raids(server_id, force_load):
    gfile_name = get_gfile_name(server_id)
    json_file = "CACHE"+os.path.sep+gfile_name+"_config_raids.json"

    if force_load or not os.path.isfile(json_file):
        try:
            get_gapi_client()
            file = client.open(gfile_name)
            feuille=file.worksheet("Raids")
            list_list_sheet=feuille.get_all_values()
        except Exception as e:
            goutils.log2("ERR", sys.exc_info()[0])
            goutils.log2("ERR", e)
            goutils.log2("ERR", traceback.format_exc())
            goutils.log2("WAR", "Cannot connect to Google API")
            return None

        dict_columns = get_dict_columns(["Alias", "Nom complet", "Phase", "Team", "%", "Normal", "Super"], list_list_sheet)

        #Extract all aliases and get associated ID+nameKey
        dict_raids = {}
        for line in list_list_sheet[1:]:
            alias = line[dict_columns['Alias']]
            if not (alias in dict_raids):
                dict_raids[alias] = [line[dict_columns['Nom complet']], {}]

            dict_raids[alias][1][line[dict_columns['Team']]]=[int(line[dict_columns['Phase']][-1]),
                                                              int(line[dict_columns['Normal']]),
                                                              int(line[dict_columns['Super']])]

        # store json file
        fjson = open(json_file, 'w')
        fjson.write(json.dumps(dict_raids, sort_keys=True, indent=4))
        fjson.close()
    else:
        dict_raids = json.load(open(json_file, "r"))

    return dict_raids

##############################################################
# Function: load_config_teams
# Parameters: None
# Purpose: lit l'onglet "teams" du fichier Sheets
# Output: liste_teams (liste des noms d'équipe)
#         dict_teams {team_name: {
#                           rarity: rarity for a GV character
#                           categories:[[catégorie, nombre nécessaire,
#                               {char_alias: [id, étoiles min, gear min, étoiles reco,
#                                       gear reco, liste zeta, vitesse]
#                               }
#                           ], ...]
#                      }
##############################################################
def load_config_teams(server_id, force_load):
    if server_id == 0:
        gfile_name = "GuiOnBot config"
    else:
        gfile_name = get_gfile_name(server_id)

    json_file = "CACHE"+os.path.sep+gfile_name+"_config_teams.json"

    if force_load or not os.path.isfile(json_file):
        try:
            get_gapi_client()
            file = client.open(gfile_name)
            feuille=file.worksheet("teams")
    
            list_dict_sheet=feuille.get_all_records()
        except Exception as e:
            goutils.log2("ERR", sys.exc_info()[0])
            goutils.log2("ERR", e)
            goutils.log2("ERR", traceback.format_exc())
            goutils.log2("WAR", "Cannot connect to Google API")
            return None, None

        #Extract all aliases and get associated ID+nameKey
        list_alias=[x['Nom'] for x in list_dict_sheet]
        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_alias)
        if txt != '':
            goutils.log2('WAR', 'Cannot recognize following alias(es) >> '+txt)


        #Get latest definition of teams
        dict_teams={}
        liste_teams=set([(lambda x:x['Nom équipe'])(x) for x in list_dict_sheet])
        #print('\nDBG: liste_teams='+str(liste_teams))
        for team in liste_teams:
            liste_dict_team=list(filter(lambda x : x['Nom équipe'] == team, list_dict_sheet))
            complete_liste_categories=[x['Catégorie'] for x in liste_dict_team]
            liste_categories=sorted(set(complete_liste_categories), key=lambda x: complete_liste_categories.index(x))
        
            dict_teams[team]={"rarity":liste_dict_team[0]["GV*"],
                            "categories":[[] for i in range(len(liste_categories))]
                            }
            index_categorie=-1
            for categorie in liste_categories:
                index_categorie+=1
                dict_teams[team]["categories"][index_categorie]=[categorie, 0, {}]
                liste_dict_categorie=list(filter(lambda x : x['Catégorie'] == categorie, liste_dict_team))

                index_perso=0
                for dict_perso in liste_dict_categorie:
                    if dict_perso['Nom'] in dict_id_name:
                        for [character_id, character_name] in dict_id_name[dict_perso['Nom']]:
                            index_perso+=1
                            dict_teams[team]["categories"][index_categorie][1] = dict_perso['Min Catégorie']
                            if character_id in dict_teams[team]["categories"][index_categorie][2]:
                                goutils.log2('WAR', "twice the same character in that team: "+ character_id)
                            
                            dict_teams[team]["categories"][index_categorie][2][character_id]=[index_perso,
                                                                                dict_perso['* min'],
                                                                                dict_perso['G min'],
                                                                                dict_perso['* reco'],
                                                                                dict_perso['G reco'],
                                                                                dict_perso['Zetas'],
                                                                                dict_perso['Omicrons'],
                                                                                character_name]
    
        #Update DB
        connect_mysql.update_guild_teams(gfile_name, dict_teams)

        # store json file
        fjson = open(json_file, 'w')
        fjson.write(json.dumps(dict_teams, sort_keys=True, indent=4))
        fjson.close()
    else:
        dict_teams = json.load(open(json_file, "r"))

    #print('DBG: dict_teams='+str(dict_teams))
    #return liste_teams, dict_teams
    return list(dict_teams.keys()), dict_teams

##############################################################
# Function: load_config_players
# Parameters: none
# Purpose: lit l'onglet "players" du fichier Sheets
# Output:  dict_players_by_IG {key=IG name, value=[allycode, <@id>]}
#          dict_players_by_ID {key=discord ID, value=[allycode, isOfficer]}
##############################################################
def load_config_players(server_id, force_load):
    gfile_name = get_gfile_name(server_id)
    json_file = "CACHE"+os.path.sep+gfile_name+"_config_players.json"

    if force_load or not os.path.isfile(json_file):
        try:
            get_gapi_client()
            file = client.open(gfile_name)
            feuille=file.worksheet("players")
            list_list_sheet=feuille.get_all_values()
        except Exception as e:
            goutils.log2("ERR", sys.exc_info()[0])
            goutils.log2("ERR", e)
            goutils.log2("ERR", traceback.format_exc())
            goutils.log2("WAR", "Cannot connect to Google API")
            return [None, None]

        dict_columns = get_dict_columns(["Allycode", "IG name", "Discord ID", "Officier", "Last Online"], list_list_sheet)

        liste_discord_id=[str(x[dict_columns['Discord ID']]) for x in list_list_sheet]
        dict_players_by_IG={} # {key=IG name, value=[allycode, discord name, discord display name]}
        dict_players_by_ID={} # {key=discord ID, value=[allycode, isOfficer]}

        #print(list_list_sheet)
        for ligne in list_list_sheet[1:]:
            #Fill dict_players_by_IG
            #needs to transform into str as json only uses str as keys
            discord_id=str(ligne[dict_columns["Discord ID"]])
            goutils.log2("DBG", "discord_id "+discord_id)
            if discord_id!='':
                if liste_discord_id.count(discord_id)>1:
                    #cas des comptes discord avec plusieurs comptes IG
                    dict_players_by_IG[ligne[dict_columns['IG name']]] = [ligne[dict_columns['Allycode']], 
                                                                         '<@'+discord_id+'> ['+ligne[dict_columns['IG name']]+']']
                else:
                    dict_players_by_IG[ligne[dict_columns['IG name']]] = [ligne[dict_columns['Allycode']], '<@'+discord_id+'>']
            else:
                dict_players_by_IG[ligne[dict_columns['IG name']]] = [ligne[dict_columns['Allycode']], 
                                                                      ligne[dict_columns['IG name']]]
            
            #Fill dict_players_by_ID
            if discord_id!='':
                if discord_id in dict_players_by_ID:
                    is_already_officer = dict_players_by_ID[discord_id][1]
                else:
                    is_already_officer = False

                is_officer = is_already_officer or (ligne[dict_columns['Officier']]!='')
                dict_players_by_ID[discord_id] = [ligne[dict_columns['Allycode']], is_officer]

        # store json file
        fjson = open(json_file, 'w')
        fjson.write(json.dumps([dict_players_by_IG, dict_players_by_ID], sort_keys=True, indent=4))
        goutils.log2("INFO", "Write file "+json_file)
        fjson.close()
    else:
        [dict_players_by_IG, dict_players_by_ID] = json.load(open(json_file, "r"))
        
    return [dict_players_by_IG, dict_players_by_ID]

##############################################################
# Function: load_config_gt
# Parameters: none
# Purpose: lit l'onglet "GT" du fichier Sheets
# Output:  liste_territoires [index=priorité-1 value=[territoire, [[team, nombre, score]...]], ...]
##############################################################
def load_config_gt(server_id):
    gfile_name = get_gfile_name(server_id)
    global client    
    get_gapi_client()
    file = client.open(gfile_name)
    feuille=file.worksheet("GT")

    list_dict_sheet=feuille.get_all_records()
    liste_priorites=set([(lambda x:0 if x['Priorité']=='' else x['Priorité'])(x) for x in list_dict_sheet])

    liste_territoires=[['', []] for x in range(0,max(liste_priorites))] # index=priorité-1, value=[territoire, [[team, nombre, score]...]]
    
    for ligne in list_dict_sheet:
        #print(ligne)
        priorite=ligne['Priorité']
        if priorite != '':
            liste_territoires[priorite-1][0]=ligne['Territoire']
            liste_territoires[priorite-1][1].append([ligne['Team'], ligne['Nombre'], ligne['Score mini']])

    return liste_territoires
    
##############################################################
# Function: load_config_counter
# Parameters: none
# Purpose: lit l'onglet "COUNTER" du fichier Sheets
# Output:  list_counter_teams [[nom équipe à contrer, [liste équipes qui peuvent contrer], nombre nécessaire], ...]
##############################################################
def load_config_counter(server_id):
    gfile_name = get_gfile_name(server_id)

    global client    
    get_gapi_client()
    file = client.open(gfile_name)
    feuille=file.worksheet("COUNTER")

    list_dict_sheet=feuille.get_all_records()
    list_counter_teams=[]
    
    for ligne in list_dict_sheet:
        counter_team=['', [], 0]
        for key in ligne.keys():
            if key=='Adversaire':
                counter_team[0]=ligne[key]
            elif key=='Quantité souhaitée':
                counter_team[2]=ligne[key]
            elif key.startswith('Counter'):
                if ligne[key]!='':
                    counter_team[1].append(ligne[key])
        if counter_team[0]!='':
            list_counter_teams.append(counter_team)
    return list_counter_teams

##############################################################
# Function: load_config_units
# Parameters: none
# Purpose: lit l'onglet "units" du fichier Sheets
# Output:  dict_units {key=alias, value=[name, id]}
##############################################################
def load_config_units(force_load):
    json_file = "CACHE"+os.path.sep+"config_units.json"

    if force_load or not os.path.isfile(json_file):
        try:
            get_gapi_client()
            file = client.open("GuiOnBot config")
            feuille=file.worksheet("units")

            list_dict_sheet=feuille.get_all_values()
        except Exception as e:
            goutils.log2("ERR", sys.exc_info()[0])
            goutils.log2("ERR", e)
            goutils.log2("ERR", traceback.format_exc())
            goutils.log2("ERR", "Cannot connect to Google API")
            return None

        dict_units=data.get("unitsAlias_dict.json") #key=alias, value=[nameKey, id]
    
        for ligne in list_dict_sheet[1:]:
            full_name=ligne[1]
            id=ligne[2]

        #Full Name from file is not used as alias, because it is already read from json file
            if not full_name.lower() in dict_units:
            #if dict_units[full_name.lower()][0] != full_name:
                #print('ERR: double définition de '+full_name.lower()+': '+full_name+' et '+dict_units[full_name.lower()][0])
        #else:
                dict_units[full_name.lower()]=[full_name, id]

        # Char ID cannot be used as alias because of Rey
        # "rey" is the nameKey of GLREY, and "REY" is the ID of scavenger rey
        # if id.lower() in dict_units:
            # if dict_units[id.lower()][0] != full_name:
                # print('ERR: double définition de '+id.lower()+': '+full_name+' et '+dict_units[id.lower()][0])
        # else:
            # dict_units[id.lower()]=[full_name, id]
            
            list_aliases = ligne[0]
            if type(list_aliases) != str:
                list_aliases = str(list_aliases)
            if list_aliases != '':
                for alias in list_aliases.split(','):
                    alias = alias.strip().lower()
                    if alias in dict_units:
                        if dict_units[alias][0] != full_name:
                            goutils("ERR", "connect_gsheets.load_config_units", "alias="+alias)
                            goutils("ERR", "connect_gsheets.load_config_units", "dict_units[alias]="+dict_units[alias])
                            goutils("ERR", "connect_gsheets.load_config_units", "full_name="+full_name)
                            goutils("ERR", "connect_gsheets.load_config_units", 'double définition of '+alias+': '+dict_units[alias][0]+' and '+full_name)
                    else:
                        dict_units[alias]=[full_name, id]

        # store json file
        fjson = open(json_file, 'w')
        fjson.write(json.dumps(dict_units, sort_keys=True, indent=4))
        fjson.close()
    else:
        dict_units = json.load(open(json_file, "r"))
                
    return dict_units

##############################################################
# Function: update_online_dates
# Parameters: gfile_name (used for the file name)
#             dict_lastseen
#             {key=discord id,
#              value=[discord name, date last seen (idle or online)]}
# Purpose: met à jour la colonne "Last Online" de l'onglet "players"
# Output:  none
##############################################################
def update_online_dates(server_id, dict_lastseen):
    gfile_name = get_gfile_name(server_id)

    try:
        get_gapi_client()
        file = client.open(gfile_name)
        feuille=file.worksheet("players")
    except:
        goutils.log2("ERR", "Unexpected error: "+str(sys.exc_info()[0]))
        return

    #parsing title row
    col_id=0
    col_date=0
    id_column_title='Discord ID'
    date_column_title='Last Online'

    c = 1
    first_row=feuille.row_values(1)
    for value in first_row:
        if value==id_column_title:
            col_id=c
        elif value==date_column_title:
            col_date=c
        c+=1

    if (col_date > 0) and (col_id > 0):
        ids=feuille.col_values(col_id)
        online_dates=feuille.col_values(col_date)

        #Looping through lines, through the ID column
        l = 1
        for str_id in ids:
            if l > 1:
                if str_id=='':
                    #no Discord ID > empty date
                    if l > len(online_dates):
                        online_dates.append([''])
                    else:
                        online_dates[l-1] = ['']
                else:
                    id=int(str_id)
                    if id in dict_lastseen:
                        last_date=dict_lastseen[id][1]
                        if last_date == None:
                            # Not seen recently > no change
                            if l > len(online_dates):
                                # Yet if the table did not contain this ID,
                                # create an empty cell so that next ID can be added properly
                                online_dates.append([''])
                            else:
                                online_dates[l-1] = [online_dates[l-1]]
                        else:
                            last_date_value=last_date.strftime("%Y-%m-%d %H:%M:%S")
                            if l > len(online_dates):
                                online_dates.append([last_date_value])
                            else:
                                online_dates[l-1] = [last_date_value]
                    else:
                        # ID is gsheets does not match an ID in Discord
                        if l > len(online_dates):
                            online_dates.append(['Not a guild member'])
                        else:
                            online_dates[l-1] = ['Not a guild member']
                        
                    # print('id='+str(id)+' '+str(online_dates[l-1]))
            else:
                # Title line. Need to keep it, changing the format to a list
                online_dates[l-1]=[online_dates[l-1]]
            l+=1
        
        column_letter='ABCDEFGHIJKLMNOP'[col_date-1]
        range_name=column_letter+'1:'+column_letter+str(l-1)
        feuille.update(range_name, online_dates, value_input_option='USER_ENTERED')
    else:
        goutils.log2("ERR", 'At least one column among "'+id_column_title+'" and "'+date_column_title+'" is not found >> online date not updated')

##############################################################
# Function: get_tb_triggers
# Parameters: force_load (True: read the sheet / False: read the cache)
# Purpose: Read the "BT" tab of the gsheets
# Output: dict of scores by territory
#         dict of star tagrets by TB and by day
#         margin of score before reaching the target
##############################################################
def get_tb_triggers(server_id, force_load):
    gfile_name = get_gfile_name(server_id)

    json_file = "CACHE"+os.path.sep+gfile_name+"_config_tb.json"

    if force_load or not os.path.isfile(json_file):
        try:
            get_gapi_client()
            file = client.open(gfile_name)
            feuille=file.worksheet("BT")
        except:
            goutils.log2("ERR", "Unexpected error: "+str(sys.exc_info()[0]))
            return [None, None, 0]
        
        #parsing title row
        col_territory=0
        col_star1=0
        col_star2=0
        col_star3=0
        col_top=0
        col_mid=0
        col_bot=0
        territory_column_title='Territoire'
        star1_column_title='Etoile 1'
        star2_column_title='Etoile 2'
        star3_column_title='Etoile 3'
        top_column_title='Top'
        mid_column_title='Mid'
        bot_column_title='Bot'
        margin_column_title='Marge'

        #Detect columns
        c = 1
        first_row=feuille.row_values(1)
        for value in first_row:
            if value==territory_column_title:
                col_territory=c
            elif value==star1_column_title:
                col_star1=c
            elif value==star2_column_title:
                col_star2=c
            elif value==star3_column_title:
                col_star3=c
            elif value==top_column_title:
                col_top=c
            elif value==mid_column_title:
                col_mid=c
            elif value==bot_column_title:
                col_bot=c
            elif value==margin_column_title:
                col_margin=c
            c+=1

        if (col_territory > 0) \
            and (col_star1 > 0) \
            and (col_star2 > 0) \
            and (col_star3 > 0) \
            and (col_top > 0) \
            and (col_mid > 0) \
            and (col_bot > 0) \
            and (col_margin > 0):
        
            #Looping through lines, through the ID column
            territories=feuille.col_values(col_territory)
            star1_scores=feuille.col_values(col_star1)
            star2_scores=feuille.col_values(col_star2)
            star3_scores=feuille.col_values(col_star3)
            territory_stars = {}
            l = 1
            for territory in territories:
                if territory!='' and territory != territory_column_title:
                    star1_score = star1_scores[l-1].replace('\u202f', '')
                    if star1_score:
                        star1_score = int(star1_score)
                    else:
                        star1_score = -1

                    star2_score = star2_scores[l-1].replace('\u202f', '')
                    if star2_score:
                        star2_score = int(star2_score)
                    else:
                        star2_score = -1

                    star3_score = star3_scores[l-1].replace('\u202f', '')
                    if star3_score:
                        star3_score = int(star3_score)
                    else:
                        star3_score = -1

                    territory_stars[territory] = [star1_score, star2_score, star3_score]

                l+=1
            goutils.log2("DBG", 'territory_stars='+str(territory_stars))

            daily_names=feuille.col_values(col_top-1)
            top_stars=feuille.col_values(col_top)
            mid_stars=feuille.col_values(col_mid)
            bot_stars=feuille.col_values(col_bot)
            daily_targets = {}
            current_tb_name = ""
            l = 1
            for daily_name in daily_names:
                top_target = top_stars[l-1] + '-' + top_stars[l]
                mid_target = mid_stars[l-1] + '-' + mid_stars[l]
                bot_target = bot_stars[l-1] + '-' + bot_stars[l]

                if daily_name!='':
                    if top_stars[l-1] in [top_column_title, "DS"]:
                        current_tb_name = daily_name
                    elif daily_name!='':
                        day_index = int(daily_name[-1])-1
                        if not current_tb_name in daily_targets:
                            if current_tb_name[0] == 'G': #Geonosis: 4 days
                                daily_targets[current_tb_name] = [[], [], [], []]
                            else: #Hoth: 6 days
                                daily_targets[current_tb_name] = [[], [], [], [], [], []]
                        daily_targets[current_tb_name][day_index] = [top_target, mid_target, bot_target]
                l+=1
            goutils.log2("DBG", 'daily_targets='+str(daily_targets))

            margin = feuille.col_values(col_margin)[1]
            margin = margin.replace('\u202f', '')
            if margin:
                margin = int(margin)
            else:
                margin = 0
            goutils.log2("DBG", 'margin='+str(margin))

        else:
            goutils.log2("ERR", 'At least one column among "'+territory_column_title+'", "' +\
                    star1_column_title+'", "' +\
                    star2_column_title+'", "' +\
                    star3_column_title+'", "' +\
                    top_column_title+'", "' +\
                    mid_column_title+'", "' +\
                    bot_column_comment+'" is not found >> BT alerts not sent')
                
        # store json file
        fjson = open(json_file, 'w')
        fjson.write(json.dumps([territory_stars, daily_targets, margin], sort_keys=True, indent=4))
        fjson.close()
    else:
        [territory_stars, daily_targets, margin] = json.load(open(json_file, "r"))

    return [territory_stars, daily_targets, margin]

def load_tb_teams(server_id, force_load):
    gfile_name = get_gfile_name(server_id)

    json_file = "CACHE"+os.path.sep+gfile_name+"_config_tb_teams.json"

    if force_load or not os.path.isfile(json_file):
        try:
            get_gapi_client()
            file = client.open(gfile_name)
            feuille=file.worksheet("BT teams")

            list_dict_sheet=feuille.get_all_records()
        except Exception as e:
            goutils.log2("ERR", sys.exc_info()[0])
            goutils.log2("ERR", e)
            goutils.log2("ERR", traceback.format_exc())
            goutils.log2("ERR", "Cannot connect to Google API")
            return None

        tb_teams = [{}, {}, {}, {}]
        cur_day = 0
        for dict_line in list_dict_sheet:
            if dict_line['Jour'] != '':
                cur_day = int(dict_line['Jour'][-1])

            terr = dict_line['Territoire']
            if not terr in tb_teams[cur_day-1]:
                tb_teams[cur_day-1][terr] = []

            team = dict_line['Team']
            tb_teams[cur_day-1][terr].append(team)

        # store json file
        fjson = open(json_file, 'w')
        fjson.write(json.dumps(tb_teams, sort_keys=True, indent=4))
        fjson.close()
    else:
        tb_teams = json.load(open(json_file, "r"))

    return tb_teams

##############################################################
# Function: load_new_tb
# Parameters: none
# Purpose: lit les operations de la nouvelle BT
# Output:  dict_zones= {zone_name: {defId: [count, relic_min], ...}}
##############################################################
def load_new_tb():
    global client    
    get_gapi_client()
    file = client.open('NewTB_operations')
    feuille=file.worksheet("long_format")

    list_dict_sheet=feuille.get_all_records()
    
    dict_zones={}
    dict_toons={}
    for ligne in list_dict_sheet:
        zone_name = 'ROTE'+str(ligne['phase'])+'-'+ligne['alignment']+'-'+str(ligne['operation'])
        if not zone_name in dict_zones:
            dict_zones[zone_name] = {}
        baseId = ligne['baseId']
        if not baseId in dict_zones[zone_name]:
            dict_zones[zone_name][baseId] = [0, min(ligne['phase']+4, 9)]
        dict_zones[zone_name][baseId][0] +=1

        if not baseId in dict_toons:
            dict_toons[baseId] = []
        dict_toons[baseId].append(zone_name)

    return dict_zones, dict_toons
    
##############################################################
def update_gwarstats(server_id):
    gfile_name = get_gfile_name(server_id)

    ec, et, tb_data = connect_rpc.get_tb_status(server_id, "", False, True)
    if ec != 0:
        return 1, et

    [dict_phase, dict_strike_zones, dict_tb_players, dict_open_zones] = tb_data

    try:
        get_gapi_client()
        file = client.open(gfile_name)
        feuille=file.worksheet("BT graphs")
    except:
        goutils.log2("ERR", "Unexpected error: "+str(sys.exc_info()[0]))
        return

    now = datetime.datetime.now()

    #first need to check if the round has evolved
    # in that case, duplicate current sheet as backup copy
    prev_round = int(feuille.get("B2")[0][0])
    prev_shortname = feuille.get("A4")[0][0].split("-")[0][:-1]
    if prev_round != dict_phase["round"]:
        max_sheet_id = max([ws.id for ws in file.worksheets()])
        new_sheet_name=prev_shortname+" J"+str(prev_round)+" "+now.strftime("%d/%m")
        feuille.duplicate(insert_sheet_index=max_sheet_id+1, new_sheet_name=new_sheet_name)


    dict_tb = data.dict_tb
    cells = []
    cells.append(gspread.cell.Cell(row=1, col=2, value=dict_phase["name"]))
    cells.append(gspread.cell.Cell(row=2, col=2, value=dict_phase["round"]))
    cells.append(gspread.cell.Cell(row=1, col=8, value=now.strftime("%d/%m/%Y %H:%M:%S")))

    i_zone = 0
    for zone_fullname in dict_open_zones:
        zone = dict_open_zones[zone_fullname]
        zone_shortname = dict_tb[zone_fullname]["name"]
        cells.append(gspread.cell.Cell(row=4, col=1+4*i_zone, value=zone_shortname))

        zone_round = zone_fullname[-12]
        if zone_round == str(dict_phase["round"]):
            cells.append(gspread.cell.Cell(row=4, col=2+4*i_zone, value=""))
        else:
            cells.append(gspread.cell.Cell(row=4, col=2+4*i_zone, value="!!! Phase "+zone_round))

        #zone stars
        cells.append(gspread.cell.Cell(row=6, col=1+4*i_zone, value=zone["stars"]))

        #zone star scores
        i_col = 1
        for star_score in dict_tb[zone_fullname]["scores"]:
            cells.append(gspread.cell.Cell(row=12, col=1+i_col+4*i_zone, value=star_score))
            i_col += 1

        #zone scores (for the graph)
        cells.append(gspread.cell.Cell(row=14, col=2+4*i_zone, value=min(star_score, zone["score"])))
        cells.append(gspread.cell.Cell(row=15, col=2+4*i_zone, value=zone["estimatedStrikeScore"]))
        cells.append(gspread.cell.Cell(row=16, col=2+4*i_zone, value=zone["deployment"]))
        cells.append(gspread.cell.Cell(row=17, col=2+4*i_zone, value=zone["maxStrikeScore"]))

        #zone strike stats
        for line in [19, 20, 21, 22, 23]:
            cells.append(gspread.cell.Cell(row=line, col=1+4*i_zone, value=""))
            cells.append(gspread.cell.Cell(row=line, col=2+4*i_zone, value=""))

        line = 19
        i_strike = 1
        total_strikes=0
        for strike in dict_tb[zone_fullname]["strikes"]:
            cells.append(gspread.cell.Cell(row=line, col=1+4*i_zone, value="strike "+str(i_strike)))
            strike_val = str(zone["strikeFights"][strike])+"/"+str(dict_phase["TotalPlayers"])
            total_strikes += zone["strikeFights"][strike]
            cells.append(gspread.cell.Cell(row=line, col=2+4*i_zone, value=strike_val))
            i_strike+=1
            line+=1
        remaining_zone_strikes = (i_strike-1)*dict_phase["TotalPlayers"] - total_strikes
        cells.append(gspread.cell.Cell(row=27, col=5+2*i_zone, value=remaining_zone_strikes))
        cells.append(gspread.cell.Cell(row=27, col=6+2*i_zone, value=zone["maxStrikeScore"]))

        i_covert = 1
        for strike in dict_tb[zone_fullname]["coverts"]:
            cells.append(gspread.cell.Cell(row=line, col=1+4*i_zone, value="Special "+str(i_covert)))
            cells.append(gspread.cell.Cell(row=line, col=2+4*i_zone, value="inconnu"))
            i_covert+=1
            line+=1

        #strikes success
        cells.append(gspread.cell.Cell(row=32, col=1+4*i_zone, value=zone["strikeScore"]))
        total_strikes_zone = sum(zone["strikeFights"].values())
        if total_strikes_zone == 0:
            cells.append(gspread.cell.Cell(row=32, col=2+4*i_zone, value=0))
        else:
            cells.append(gspread.cell.Cell(row=32, col=2+4*i_zone, value=zone["strikeScore"]/total_strikes_zone))
        
        i_zone+=1

    #global stats
    #Remaining Deployments
    if dict_tb[dict_phase["type"]]["shortname"] == "ROTE":
        cells.append(gspread.cell.Cell(row=26, col=1, value="Mix"))
        cells.append(gspread.cell.Cell(row=26, col=2, value=""))
        cells.append(gspread.cell.Cell(row=27, col=1, value=dict_phase["availableMixDeploy"]))
        cells.append(gspread.cell.Cell(row=27, col=2, value=""))
    else:
        cells.append(gspread.cell.Cell(row=26, col=1, value="Fleet"))
        cells.append(gspread.cell.Cell(row=26, col=2, value="Squad"))
        cells.append(gspread.cell.Cell(row=27, col=1, value=dict_phase["availableShipDeploy"]))
        cells.append(gspread.cell.Cell(row=27, col=2, value=dict_phase["availableCharDeploy"]))

    #players
    if dict_tb[dict_phase["type"]]["shortname"] == "ROTE":
        cells.append(gspread.cell.Cell(row=1, col=16, value="Mix deployment"))
        cells.append(gspread.cell.Cell(row=1, col=19, value=""))

    sorted_dict_tb_players = dict(sorted(dict_tb_players.items(), key=lambda x: x[1]["score"]["deployed"] + x[1]["score"]["strikes"], reverse=True))

    line = 3
    for playername in sorted_dict_tb_players:
        player = dict_tb_players[playername]
        cells.append(gspread.cell.Cell(row=line, col=14, value=playername))
        total_score = player["score"]["deployed"] + player["score"]["strikes"]
        cells.append(gspread.cell.Cell(row=line, col=15, value=total_score))

        if dict_tb[dict_phase["type"]]["shortname"] == "ROTE":
            cells.append(gspread.cell.Cell(row=line, col=16, value=player["score"]["deployedMix"]))
            cells.append(gspread.cell.Cell(row=line, col=17, value=player["mix_gp"]))
            cells.append(gspread.cell.Cell(row=line, col=19, value=""))
            cells.append(gspread.cell.Cell(row=line, col=20, value=""))
        else:
            cells.append(gspread.cell.Cell(row=line, col=16, value=player["score"]["deployedShips"]))
            cells.append(gspread.cell.Cell(row=line, col=17, value=player["ship_gp"]))
            cells.append(gspread.cell.Cell(row=line, col=19, value=player["score"]["deployedChars"]))
            cells.append(gspread.cell.Cell(row=line, col=20, value=player["char_gp"]))

        total_strikes = 0
        player_strikes = 0
        i_zone = 1
        for zone_fullname in dict_open_zones:
            strike_txt = ""
            conflict = zone_fullname.split("_")[-1]
            i_strike = 1
            for strike in dict_tb[zone_fullname]["strikes"]:
                total_strikes += 1
                conflict_strike = conflict+"_"+strike
                if conflict_strike in player["strikes"]:
                    player_strikes += 1
                    strike_txt += "S"+str(i_strike)+" "
                i_strike+=1
            cells.append(gspread.cell.Cell(row=line, col=21+i_zone, value=strike_txt))
            i_zone += 1
        cells.append(gspread.cell.Cell(row=line, col=25, value=str(player_strikes)+"/"+str(total_strikes)))

        line += 1

    while line<53:
        cells.append(gspread.cell.Cell(row=line, col=14, value=""))
        cells.append(gspread.cell.Cell(row=line, col=15, value=""))
        cells.append(gspread.cell.Cell(row=line, col=16, value=""))
        cells.append(gspread.cell.Cell(row=line, col=17, value=""))
        cells.append(gspread.cell.Cell(row=line, col=19, value=""))
        cells.append(gspread.cell.Cell(row=line, col=20, value=""))
        line += 1


    feuille.update_cells(cells)

    return 0, ""
