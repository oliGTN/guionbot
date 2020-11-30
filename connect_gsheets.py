# tutorial: https://www.twilio.com/blog/2017/02/an-easy-way-to-read-and-write-to-a-google-spreadsheet-in-python.html
# bug: https://github.com/burnash/gspread/issues/513

import gspread
import os
import json
from oauth2client.service_account import ServiceAccountCredentials

# client est global pour garder le même en cas d'ouverture de plusieurs fichiers 
# ou plusieurs fois le même (gain de temps)
client=None

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
            creds_envVar = os.environ['GAPI_CREDS']
            creds_json = json.loads(creds_envVar)
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
            client = gspread.authorize(creds)
        except KeyError as e:
            print('ERR: variable d\'environment GAPI_CREDS non définie')

##############################################################
# Function: load_config_teams
# Parameters: none
# Purpose: lit l'onglet "teams" du fichier Sheets
# Output: liste_teams (liste des noms d'équipe)
#         dict_teams {key=team_name,
#                     value=[[catégorie, nombre nécessaire,
#                               {key=nom,
#                                value=[id, étoiles min, gear min, étoiles reco, gear reco, [liste zeta], vitesse, nom court]
#                                }
#                             ], ...]
#                      }
##############################################################
def load_config_teams():
    global client    
    get_gapi_client()
    file = client.open("GuiOnBot config")
    feuille=file.worksheet("teams")

    dict_teams={} # {key=team_name, value=[[catégorie, nombre nécessaire, {key=nom, value=[id, étoiles min, gear min, étoiles reco, gear reco, [liste zeta], vitesse, nom court]}]]}

    liste_dict_feuille=feuille.get_all_records()
    #print(liste_dict_feuille)
    liste_teams=set([(lambda x:x['Nom équipe'])(x) for x in liste_dict_feuille])
    #print('\nDBG: liste_teams='+str(liste_teams))
    for team in liste_teams:
        liste_dict_team=list(filter(lambda x : x['Nom équipe'] == team, liste_dict_feuille))
        #print(liste_dict_team)
        complete_liste_categories=[(lambda x:x['Catégorie'])(x) for x in liste_dict_team]
        liste_categories=sorted(set(complete_liste_categories), key=lambda x: complete_liste_categories.index(x))
        
        #print('liste_categories='+str(liste_categories))
        dict_teams[team]=[[] for i in range(len(liste_categories))]
        index_categorie=-1
        for categorie in liste_categories:
            index_categorie+=1
            dict_teams[team][index_categorie]=[categorie, 0, {}]
            liste_dict_categorie=list(filter(lambda x : x['Catégorie'] == categorie, liste_dict_team))
            index_perso=0
            for dict_perso in liste_dict_categorie:
                index_perso+=1
                dict_teams[team][index_categorie][1] = dict_perso['Min Catégorie']
                dict_teams[team][index_categorie][2][dict_perso['Nom']]=[index_perso, dict_perso['* min'], dict_perso['G min'], dict_perso['* reco'], dict_perso['G reco'], [], dict_perso['Vitesse'], dict_perso['Nom court']]
                for zeta in ['Zeta1', 'Zeta2', 'Zeta3']:
                    if dict_perso[zeta]!='':
                        dict_teams[team][index_categorie][2][dict_perso['Nom']][5].append(dict_perso[zeta])
        #print('DBG: dict_teams='+str(dict_teams))
    return liste_teams, dict_teams

##############################################################
# Function: load_config_players
# Parameters: none
# Purpose: lit l'onglet "players" du fichier Sheets
# Output:  dict_players_by_IG {key=IG name, value=[allycode, discord name, discord display name]}
##############################################################
def load_config_players():
    global client    
    get_gapi_client()
    file = client.open("GuiOnBot config")
    feuille=file.worksheet("players")
    liste_dict_feuille=feuille.get_all_records()
    liste_discord_id=[(lambda x:x['Discord ID'])(x) for x in liste_dict_feuille]
    dict_players_by_IG={} # {key=IG name, value=[allycode, discord name, discord display name]}
    dict_players_by_ID={} # {key=Discord ID, value=allycode}

    #print(liste_dict_feuille)
    for ligne in liste_dict_feuille:
        #Fill dict_players_by_IG
        discord_id=ligne['Discord ID']
        if discord_id!='':
            if liste_discord_id.count(discord_id)>1:
                #cas des comptes discord avec plusieurs comptes IG
                dict_players_by_IG[ligne['IG name']]=[ligne['Allycode'], ligne['Discord name'], '<@'+str(discord_id)+'> ['+ligne['IG name']+']']
            else:
                dict_players_by_IG[ligne['IG name']]=[ligne['Allycode'], ligne['Discord name'], '<@'+str(discord_id)+'>']
        else:
            dict_players_by_IG[ligne['IG name']]=[ligne['Allycode'], ligne['Discord name'], ligne['IG name']]
            
        #Fill dict_players_by_ID
        if discord_id!='':
            dict_players_by_ID[discord_id] = [ligne['Allycode'], ligne['Officier']!='']
        
    return dict_players_by_IG, dict_players_by_ID

##############################################################
# Function: load_config_bt
# Parameters: none
# Purpose: lit l'onglet "BT" du fichier Sheets
# Output:  liste_territoires [index=priorité-1 value=[territoire, [[team, nombre, score]...]], ...]
##############################################################
def load_config_bt():
    global client    
    get_gapi_client()
    file = client.open("GuiOnBot config")
    feuille=file.worksheet("BT")

    liste_dict_feuille=feuille.get_all_records()
    liste_teams = []
    for ligne in liste_dict_feuille:
        for key in ligne.keys():
            if key=='Besoin guilde':
                liste_teams.append(ligne[key])
            else:
                continue
    return liste_teams

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
    liste_priorites=set([(lambda x:x['Priorité'])(x) for x in liste_dict_feuille])

    liste_territoires=[['', []] for x in range(0,max(liste_priorites))] # index=priorité-1, value=[territoire, [[team, nombre, score]...]]
    
    for ligne in liste_dict_feuille:
        #print(ligne)
        priorite=ligne['Priorité']
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
# Output:  dict_units {key=alias, value=name}
##############################################################
def load_config_units():
    global client    
    get_gapi_client()
    file = client.open("GuiOnBot config")
    feuille=file.worksheet("units")

    liste_dict_feuille=feuille.get_all_records()
    dict_units={}
    
    for ligne in liste_dict_feuille:
        full_name=ligne['Character/Ship']
        if full_name.lower() in dict_units:
            if full_name != dict_units[full_name.lower()]:
                print('ERR: double définition de '+full_name.lower()+': '+full_name+' et '+dict_units[full_name.lower()])
        else:
            dict_units[full_name.lower()]=full_name
            
        if ligne['Aliases'] != '':
            for alias in ligne['Aliases'].split(','):
                alias = alias.strip().lower()
                if alias in dict_units:
                    if dict_units[alias] != full_name:
                        print('ERR: double définition de '+alias+': '+dict_units[alias]+' et '+full_name)
                else:
                    dict_units[alias]=full_name
                
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
    file = client.open("GuiOnBot config")
    
    try:
        feuille=file.worksheet("players")
    except requests.exceptions.ConnectionError as e:
        print(e)
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
        online_dates=feuille.col_values(col_date)
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
                        print('id '+str(id)+' not found among guild members')
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

#MAIN (DEBUG, à commenter avant mise en service)

    
