# tutorial: https://www.twilio.com/blog/2017/02/an-easy-way-to-read-and-write-to-a-google-spreadsheet-in-python.html
# bug: https://github.com/burnash/gspread/issues/513

import gspread
import os
import config
import sys
import json
import requests
import difflib
import connect_mysql
import datetime
from pytz import timezone
from oauth2client.service_account import ServiceAccountCredentials

import goutils
import data

# client est global pour garder le même en cas d'ouverture de plusieurs fichiers 
# ou plusieurs fois le même (gain de temps)
client=None

guild_timezone=timezone(config.GUILD_TIMEZONE)

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
            print('ERR: variable de configuration GAPI_CREDS non définie')

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
def load_config_teams():
    global client

    json_file = "CACHE"+os.path.sep+"config_teams.json"
    try:
        get_gapi_client()
        file = client.open("GuiOnBot config")
        feuille=file.worksheet("teams")

        liste_dict_feuille=feuille.get_all_records()
        # store json file
        fjson = open(json_file, 'w')
        fjson.write(json.dumps(liste_dict_feuille, sort_keys=True, indent=4))
        fjson.close()
    except:
        goutils.log("WAR", "load_config_teams", "Cannot connect to Google API. Using cache file.")
        liste_dict_feuille = json.load(open(json_file, 'r'))

    #Extract all aliases and get associated ID+nameKey
    list_alias=[x['Nom'] for x in liste_dict_feuille]
    list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_alias)
    if txt != '':
        goutils.log('WAR', 'load_config_teams', 'Cannot recognize following alias(es) >> '+txt)


    #Get latest definition of teams
    dict_teams={}
    liste_teams=set([(lambda x:x['Nom équipe'])(x) for x in liste_dict_feuille])
    #print('\nDBG: liste_teams='+str(liste_teams))
    for team in liste_teams:
        liste_dict_team=list(filter(lambda x : x['Nom équipe'] == team, liste_dict_feuille))
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
                            print("WAR: twice the same character in that team: "+ character_id)
                        dict_teams[team]["categories"][index_categorie][2][character_id]=[index_perso,
                                                                            dict_perso['* min'],
                                                                            dict_perso['G min'],
                                                                            dict_perso['* reco'],
                                                                            dict_perso['G reco'],
                                                                            dict_perso['Zetas'],
                                                                            dict_perso['Vitesse'],
                                                                            character_name]
    
    #Update DB
    connect_mysql.update_guild_teams(dict_teams)

    #print('DBG: dict_teams='+str(dict_teams))
    return liste_teams, dict_teams

##############################################################
# Function: load_config_players
# Parameters: none
# Purpose: lit l'onglet "players" du fichier Sheets
# Output:  dict_players_by_IG {key=IG name, value=[allycode, <@id>]}
#          dict_players_by_ID {key=discord ID, value=[allycode, isOfficer]}
##############################################################
def load_config_players():
    global client    
    get_gapi_client()
    file = client.open("GuiOnBot config")
    feuille=file.worksheet("players")
    liste_dict_feuille=feuille.get_all_records()
    liste_discord_id=[(lambda x:x['Discord ID'])(x) for x in liste_dict_feuille]
    dict_players_by_IG={} # {key=IG name, value=[allycode, discord name, discord display name]}
    dict_players_by_ID={} # {key=discord ID, value=[allycode, isOfficer]}

    #print(liste_dict_feuille)
    for ligne in liste_dict_feuille:
        #Fill dict_players_by_IG
        discord_id=ligne['Discord ID']
        if discord_id!='':
            if liste_discord_id.count(discord_id)>1:
                #cas des comptes discord avec plusieurs comptes IG
                dict_players_by_IG[ligne['IG name']]=[ligne['Allycode'], '<@'+str(discord_id)+'> ['+ligne['IG name']+']']
            else:
                dict_players_by_IG[ligne['IG name']]=[ligne['Allycode'], '<@'+str(discord_id)+'>']
        else:
            dict_players_by_IG[ligne['IG name']]=[ligne['Allycode'], ligne['IG name']]
            
        #Fill dict_players_by_ID
        if discord_id!='':
            dict_players_by_ID[discord_id] = [ligne['Allycode'], ligne['Officier']!='']
        
    return dict_players_by_IG, dict_players_by_ID

##############################################################
# Function: load_config_gt
# Parameters: none
# Purpose: lit l'onglet "GT" du fichier Sheets
# Output:  liste_territoires [index=priorité-1 value=[territoire, [[team, nombre, score]...]], ...]
##############################################################
def load_config_gt():
    global client    
    get_gapi_client()
    file = client.open("GuiOnBot config")
    feuille=file.worksheet("GT")

    liste_dict_feuille=feuille.get_all_records()
    liste_priorites=set([(lambda x:0 if x['Priorité']=='' else x['Priorité'])(x) for x in liste_dict_feuille])

    liste_territoires=[['', []] for x in range(0,max(liste_priorites))] # index=priorité-1, value=[territoire, [[team, nombre, score]...]]
    
    for ligne in liste_dict_feuille:
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
def load_config_counter():
    global client    
    get_gapi_client()
    file = client.open("GuiOnBot config")
    feuille=file.worksheet("COUNTER")

    liste_dict_feuille=feuille.get_all_records()
    list_counter_teams=[]
    
    for ligne in liste_dict_feuille:
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
def load_config_units():
    global client    
    
    json_file = "CACHE"+os.path.sep+"config_units.json"
    try:
        get_gapi_client()
        file = client.open("GuiOnBot config")
        feuille=file.worksheet("units")

        liste_dict_feuille=feuille.get_all_records()
        
        # store json file
        fjson = open(json_file, 'w')
        fjson.write(json.dumps(liste_dict_feuille, sort_keys=True, indent=4))
        fjson.close()
    except:
        goutils.log("WAR", "load_config_units", "Cannot connect to Google API. Using cache file.")
        liste_dict_feuille = json.load(open(json_file, 'r'))

    dict_units=data.get("unitsAlias_dict.json") #key=alias, value=[nameKey, id]
    
    for ligne in liste_dict_feuille:
        full_name=ligne['Character/Ship']
        id=ligne['ID']

        #Full Name from file is not used as alias, because it is already read from json file
        #if full_name.lower() in dict_units:
            #if dict_units[full_name.lower()][0] != full_name:
                #print('ERR: double définition de '+full_name.lower()+': '+full_name+' et '+dict_units[full_name.lower()][0])
        #else:
            #dict_units[full_name.lower()]=[full_name, id]

        # Char ID cannot be used as alias because of Rey
        # "rey" is the nameKey of GLREY, and "REY" is the ID of scavenger rey
        # if id.lower() in dict_units:
            # if dict_units[id.lower()][0] != full_name:
                # print('ERR: double définition de '+id.lower()+': '+full_name+' et '+dict_units[id.lower()][0])
        # else:
            # dict_units[id.lower()]=[full_name, id]
            
        list_aliases = ligne['Aliases']
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
                
    return dict_units
##############################################################
# Function: update_online_dates
# Parameters: dict_lastseen
#             {key=discord id,
#              value=[discord name, date last seen (idle or online)]}
# Purpose: met à jour la colonne "Last Online" de l'onglet "players"
# Output:  none
##############################################################
def update_online_dates(dict_lastseen):
    global client    
    get_gapi_client()
    
    try:
        file = client.open("GuiOnBot config")
        feuille=file.worksheet("players")
    except:
        print("Unexpected error: "+str(sys.exc_info()[0]))
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
                        goutils.log("WAR", "update_online_dates", 'Discord ID '+str(id)+' not found among guild members')
                        if l > len(online_dates):
                            online_dates.append(['not found in Discord'])
                        else:
                            online_dates[l-1] = ['not found in Discord']
                        
                    # print('id='+str(id)+' '+str(online_dates[l-1]))
            else:
                # Title line. Need to keep it, changing the format to a list
                online_dates[l-1]=[online_dates[l-1]]
            l+=1
        
        column_letter='ABCDEFGHIJKLMNOP'[col_date-1]
        range_name=column_letter+'1:'+column_letter+str(l-1)
        feuille.update(range_name, online_dates, value_input_option='USER_ENTERED')
    else:
        print('At least one column among "'+id_column_title+'" and "'+date_column_title+'" is not found >> online date not updated')

def get_tb_triggers(territory_scores, return_active_triggers):
    global client    
    get_gapi_client()
    
    try:
        file = client.open("GuiOnBot config")
        feuille=file.worksheet("BT")
    except:
        print("Unexpected error: "+str(sys.exc_info()[0]))
        return []
        
    #parsing title row
    col_territory=0
    col_gp=0
    col_id=0
    col_date=0
    territory_column_title='Territoire alerte'
    gp_alert_column_title='PG alerte'
    discord_id_column_title='Discord ID alerte'
    date_column_title='Date alerte'
    date_column_comment='Commentaire'

    list_tb_triggers=[]
    list_active_tb_triggers=[]
    
    c = 1
    first_row=feuille.row_values(1)
    for value in first_row:
        if value==territory_column_title:
            col_territory=c
        elif value==gp_alert_column_title:
            col_gp=c
        elif value==discord_id_column_title:
            col_id=c
        elif value==date_column_title:
            col_date=c
        elif value==date_column_comment:
            col_cmt=c
        c+=1

    if (col_date > 0) and (col_territory > 0) \
        and (col_gp > 0) and (col_id > 0) and (col_cmt > 0):
        
        territories=feuille.col_values(col_territory)
        gp_alerts=feuille.col_values(col_gp)
        discord_ids=feuille.col_values(col_id)
        alert_dates=feuille.col_values(col_date)
        alert_comments=feuille.col_values(col_cmt)

        #Looping through lines, through the ID column
        l = 1
        for territory in territories:
            if l > 1:
                # print("DBG - territory: "+str(territory))
                if territory!='':
                    if territory in territory_scores:
                        cur_score = territory_scores[territory]

                        if l <= len(gp_alerts):
                            gp_alert = gp_alerts[l-1].replace('\u202f', '')
                            if gp_alert:
                                gp_alert=int(gp_alert)
                            else:
                                gp_alert = -1
                        else:
                            gp_alert = -1

                        if l <= len(alert_dates):
                            cur_date = alert_dates[l-1]
                        else:
                            cur_date = ''
                            
                        if l <= len(alert_comments):
                            cur_cmt = alert_comments[l-1]
                        else:
                            cur_cmt = ''
                            
                        # print("DBG - cur_score: "+str(cur_score))
                        # print("DBG - gp_alert: "+str(gp_alert))
                        # print("DBG - cur_date: "+str(cur_date))
                        if cur_date == '' and cur_score >= gp_alert and gp_alert!=-1:
                            discord_id = discord_ids[l-1]
                            message = "BT: "+territory+" a atteint "+cur_cmt \
                                    + " (" + str(cur_score)+"/"+str(gp_alert) + ")"
                            # print("DBG - message: "+str(message))
                            list_tb_triggers.append([discord_id, message])
                            
                            last_date_value=datetime.datetime.now(guild_timezone).strftime("%Y-%m-%d %H:%M:%S")
                            if l > len(alert_dates):
                                alert_dates.append([last_date_value])
                            else:
                                alert_dates[l-1] = [last_date_value]
                        else:
                            #no alert to be sent, just keep the date if already there
                            if l > len(alert_dates):
                                alert_dates.append([''])
                            else:
                                alert_dates[l-1] = [alert_dates[l-1]]
                    else:
                        #no alert to be sent, just keep the date if already there
                        if l > len(alert_dates):
                            alert_dates.append([''])
                            discord_id = discord_ids[l-1]
                            list_active_tb_triggers.append([discord_id, territory])
                        else:
                            if alert_dates[l-1] == '':
                                discord_id = discord_ids[l-1]
                                list_active_tb_triggers.append([discord_id, territory])
                            alert_dates[l-1] = [alert_dates[l-1]]
                else:
                    #no alert to be sent, just keep the date if already there
                    if l > len(alert_dates):
                        alert_dates.append([''])
                    else:
                        alert_dates[l-1] = [alert_dates[l-1]]
            else:
                # Title line. Need to keep it, changing the format to a list
                alert_dates[l-1]=[alert_dates[l-1]]
            l+=1
        
        column_letter='ABCDEFGHIJKLMNOP'[col_date-1]
        range_name=column_letter+'1:'+column_letter+str(l-1)
        feuille.update(range_name, alert_dates, value_input_option='USER_ENTERED')
    else:
        print('At least one column among "'+territory_column_title+'", "' +\
                gp_alert_column_title+'", "' +\
                discord_id_column_title+'" and "' +\
                date_column_title+'" and "' +\
                date_column_comment+'" is not found >> BT alerts not sent')
                
    if return_active_triggers:
        return list_active_tb_triggers
    else:
        return list_tb_triggers
