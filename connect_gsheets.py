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

def get_gfile_name(guild_id: str):
    query = "SELECT gfile_name FROM guild_bot_infos WHERE guild_id='"+guild_id+"'"
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

def get_sheet_url(guild_id: str, sheet_name):
    gfile_name = get_gfile_name(guild_id)
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
def load_config_raids(guild_id: str, force_load):
    if guild_id == None:
        gfile_name = "GuiOnBot config"
        guild_name = gfile_name
    else:
        gfile_name = get_gfile_name(guild_id)

        #Get guild name (in case gfile_name is different)
        query = "SELECT name FROM guilds WHERE id='"+guild_id+"'"
        goutils.log2("DBG", query)
        guild_name = connect_mysql.get_value(query)

    if gfile_name==None:
        goutils.log2("WAR", "No gfile for this guild ID "+guild_id)
        return 2, [], {}

    json_file = "CACHE"+os.path.sep+guild_name+"_config_raids.json"

    if force_load or not os.path.isfile(json_file):
        try:
            get_gapi_client()
            file = client.open(gfile_name)
            feuille=file.worksheet("Raids")
            list_list_sheet=feuille.get_all_values()
        except gspread.exceptions.WorksheetNotFound:
            return {}
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
def load_config_teams(guild_id: str, force_load):
    if guild_id == None:
        gfile_name = "GuiOnBot config"
        guild_name = gfile_name
        cache_name = "GuiOnBot"
    else:
        gfile_name = get_gfile_name(guild_id)

        #Get guild name (in case gfile_name is different)
        query = "SELECT name FROM guilds WHERE id='"+guild_id+"'"
        goutils.log2("DBG", query)
        guild_name = connect_mysql.get_value(query)
        cache_name = guild_id

    if gfile_name==None:
        goutils.log2("WAR", "No gfile for this guild ID "+guild_id)
        return 2, [], {}

    json_file = "CACHE/"+cache_name+"_config_teams.json"

    if force_load or not os.path.isfile(json_file):
        try:
            get_gapi_client()
            file = client.open(gfile_name)
            feuille=file.worksheet("teams")
    
            list_dict_sheet=feuille.get_all_records()
        except gspread.exceptions.WorksheetNotFound:
            goutils.log2("WAR", "teams sheet not found")
            return 3, [], {}
        except Exception as e:
            goutils.log2("ERR", sys.exc_info()[0])
            goutils.log2("ERR", e)
            goutils.log2("ERR", traceback.format_exc())
            goutils.log2("WAR", "Cannot connect to Google API")
            return 1, [], {}

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
        connect_mysql.update_guild_teams(guild_id, dict_teams)

        # store json file
        fjson = open(json_file, 'w')
        fjson.write(json.dumps(dict_teams, sort_keys=True, indent=4))
        fjson.close()
    else:
        dict_teams = json.load(open(json_file, "r"))

    return 0, list(dict_teams.keys()), dict_teams

##############################################################
# Function: load_config_units
# Parameters: none
# Purpose: lit l'onglet "units" du fichier Sheets
# Output:  dict_units {key=alias, value=[name, id]}
##############################################################
def load_config_units(force_load):
    dict_unitsList = data.get("unitsList_dict.json")
    json_file = "CACHE"+os.path.sep+"config_units.json"

    if force_load or not os.path.isfile(json_file):
        try:
            get_gapi_client()
            file = client.open("GuiOnBot config")
            feuille=file.worksheet("units")

            list_dict_sheet=feuille.get_all_values()
        except gspread.exceptions.WorksheetNotFound:
            return 1, "Worksheet not found: GuiOnNot config", {}
        except Exception as e:
            goutils.log2("ERR", sys.exc_info()[0])
            goutils.log2("ERR", e)
            goutils.log2("ERR", traceback.format_exc())
            goutils.log2("ERR", "Cannot connect to Google API")
            return 1, "Cannot connect to Google API", None

        dict_units=data.get("unitsAlias_dict.json") #key=alias, value=[nameKey, id]
    
        for ligne in list_dict_sheet[1:]:
            #print(ligne)
            id=ligne[1]
            full_name = dict_unitsList[id]["name"]

            if not full_name.lower() in dict_units:
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
                            goutils.log2("ERR", "alias="+alias)
                            goutils.log2("ERR", "dict_units[alias]="+str(dict_units[alias]))
                            goutils.log2("ERR", "full_name="+full_name)
                            goutils.log2("ERR", "double définition of "+alias+": "+dict_units[alias][0]+" and "+full_name)
                    else:
                        dict_units[alias]=[full_name, id]

        # store json file
        fjson = open(json_file, 'w')
        fjson.write(json.dumps(dict_units, sort_keys=True, indent=4))
        fjson.close()
    else:
        dict_units = json.load(open(json_file, "r"))
                
    return 0, "", dict_units

##############################################################
# Function: load_config_categories
# Parameters: none
# Purpose: lit l'onglet "categories" du fichier Sheets
# Output:  dict_categories {key=category_name, value=[unit_id1, unit_id2, ...]}
##############################################################
def load_config_categories(force_load):
    json_file = "CACHE"+os.path.sep+"config_categories.json"

    if force_load or not os.path.isfile(json_file):
        try:
            get_gapi_client()
            file = client.open("GuiOnBot config")
            feuille=file.worksheet("categories")

            list_dict_sheet=feuille.get_all_values()
        except gspread.exceptions.WorksheetNotFound:
            return {}
        except Exception as e:
            goutils.log2("ERR", sys.exc_info()[0])
            goutils.log2("ERR", e)
            goutils.log2("ERR", traceback.format_exc())
            goutils.log2("ERR", "Cannot connect to Google API")
            return None

        dict_categories = {}
        i_col = 0
        #loop on custom categories
        for cell in list_dict_sheet[1]:
            if cell != "":
                dict_categories[cell] = []
                for row in list_dict_sheet[2:]:
                    row_cell = row[i_col]
                    if row_cell == "":
                        #end of the column, move to next column
                        break
                    if row_cell.startswith("tag:"):
                        list_ids, dict_id_name, txt_not_found_characters = \
                            goutils.get_characters_from_alias([row_cell])
                        for id in list_ids:
                            dict_categories[cell].append(id)
                    else:
                        dict_categories[cell].append(row_cell)
                i_col += 1
            else:
                break

        # store json file
        fjson = open(json_file, 'w')
        fjson.write(json.dumps(dict_categories, sort_keys=True, indent=4))
        fjson.close()
    else:
        dict_categories = json.load(open(json_file, "r"))
                
    return dict_categories

##############################################################
# Function: load_config_statq
# Parameters: none
# Purpose: lit l'onglet "statq" du fichier CONFIG
# Output:  None
##############################################################
def load_config_statq():
    err_code = 0
    err_txt = ""

    #GET GSHEETS table
    try:
        get_gapi_client()
        file = client.open("GuiOnBot config")
        feuille=file.worksheet("statq")

        list_dict_sheet=feuille.get_all_values()
    except gspread.exceptions.WorksheetNotFound:
        return 0, ""
    except Exception as e:
        goutils.log2("ERR", sys.exc_info()[0])
        goutils.log2("ERR", e)
        goutils.log2("ERR", traceback.format_exc())
        goutils.log2("ERR", "Cannot connect to Google API")
        return 1, "Erreur de connexion au gsheet"

    dict_unit_stats_gs = {}
    for line in list_dict_sheet[1:]:
        unit_alias=line[0]

        #cleanup "omicron"
        if unit_alias.endswith("omicron"):
            unit_alias = unit_alias[:unit_alias.index("omicron")]
        stat1=line[1]
        stat2=line[2]

        list_character_ids, dict_id_name, txt = goutils.get_characters_from_alias([unit_alias])
        if txt != '':
            goutils.log2('WAR', 'Cannot recognize following alias(es) >> '+txt)
            err_txt += "Perso inconnu : "+txt+"\n"
            continue

        unit_id = list_character_ids[0]
        if unit_id in dict_unit_stats_gs:
            goutils.log2('WAR', "Unit listed twice: "+unit_id)
            #err_txt += "Perso configuré 2 fois : "+unit_id+"\n"
            #continue

        if not unit_id in dict_unit_stats_gs:
            dict_unit_stats_gs[unit_id] = {}
        dict_unit_stats_gs[unit_id][stat1] = 1
        if stat2!="":
            dict_unit_stats_gs[unit_id][stat2] = 1

    print(dict_unit_stats_gs)

    #Get DB table
    query = "SELECT * from statq_table"
    db_data = connect_mysql.get_table(query)

    dict_unit_stats_db = {}
    for line in db_data:
        unit_id=line[0]
        stat=line[1]
        coef=line[2]

        if not unit_id in dict_unit_stats_db:
            dict_unit_stats_db[unit_id] = {}

        dict_unit_stats_db[unit_id][stat] = coef

    print(dict_unit_stats_db)

    #Process DIFF and update table
    for unit_id in dict_unit_stats_gs:
        if unit_id in dict_unit_stats_db:
            #The unit is alredy in the DB table
            unit_gs = dict_unit_stats_gs[unit_id]
            unit_db = dict_unit_stats_db[unit_id]

            for stat in unit_gs:
                if stat in unit_db:
                    #The stat is already in DB
                    coef_gs = unit_gs[stat]
                    coef_db = unit_db[stat]

                    if coef_gs == coef_db:
                        #Coef is identical, nothing to do
                        query = None
                    else:
                        #Need to update the coef
                        query = "UPDATE statq_table SET coef="+str(coef_gs)+" WHERE defIf='"+unit_id+"' AND stat_name='"+stat+"'"
                else:
                    #The stat is not in the DB, add it
                    coef = unit_gs[stat]
                    query = "INSERT INTO statq_table(defId, stat_name, coef) VALUES('"+unit_id+"', '"+stat+"', "+str(coef)+")" 

                if query != None:
                    goutils.log2("DBG", query)
                    connect_mysql.simple_execute(query)

            #remove stats that are not used anymore
            for stat in unit_db:
                if not stat in unit_gs:
                    #remove it
                    query = "DELETE FROM statq_table WHERE defId='"+unit_id+"' AND stat_name='"+stat+"'"
                else:
                    query = None

                if query != None:
                    goutils.log2("DBG", query)
                    connect_mysql.simple_execute(query)

        else:
            #The unit is not in the DB table, insert it
            for stat in unit_gs:
                coef = unit_gs[stat]
                query = "INSERT INTO statq_table(defId, stat_name, coef) VALUES('"+unit_id+"', '"+stat+"', "+str(coef)+")" 
                goutils.log2("DBG", query)
                connect_mysql.simple_execute(query)

    #remove units that are not used anymore
    for unit_id in dict_unit_stats_db:
        if not unit_id in dict_unit_stats_gs:
            #remove it
            query = "DELETE FROM statq_table WHERE defId='"+unit_id+"'"
        else:
            query=None

        if query != None:
            goutils.log2("DBG", query)
            connect_mysql.simple_execute(query)

    #update stat average
    connect_mysql.compute_statq_avg(False)

    return err_code, err_txt

##############################################################
# Function: get_tb_triggers
# Parameters: force_load (True: read the sheet / False: read the cache)
# Purpose: Read the "BT" tab of the gsheets
# Output: dict of scores by territory
#         dict of star tagrets by TB and by day
#         margin of score before reaching the target
##############################################################
def get_tb_triggers(guild_id: str, force_load):
    if guild_id == None:
        gfile_name = "GuiOnBot config"
        guild_name = gfile_name
    else:
        gfile_name = get_gfile_name(guild_id)

        #Get guild name (in case gfile_name is different)
        query = "SELECT name FROM guilds WHERE id='"+guild_id+"'"
        goutils.log2("DBG", query)
        guild_name = connect_mysql.get_value(query)

    if gfile_name==None:
        goutils.log2("WAR", "No gfile for this guild ID "+guild_id)
        return 2, [None, 0]

    json_file = "CACHE"+os.path.sep+guild_name+"_config_tb.json"

    if force_load or not os.path.isfile(json_file):
        try:
            get_gapi_client()
            file = client.open(gfile_name)
            feuille=file.worksheet("BT")
        except:
            goutils.log2("ERR", "Unexpected error: "+str(sys.exc_info()[0]))
            return 1, [None, 0]
        
        #parsing title row
        col_top=0
        col_mid=0
        col_bot=0
        col_margin=0
        top_column_title='Top'
        mid_column_title='Mid'
        bot_column_title='Bot'
        margin_column_title='Marge'

        #Detect columns
        c = 1
        first_row=feuille.row_values(1)
        for value in first_row:
            if value==top_column_title:
                col_top=c
            elif value==mid_column_title:
                col_mid=c
            elif value==bot_column_title:
                col_bot=c
            elif value==margin_column_title:
                col_margin=c
            c+=1

        if      (col_top > 0) \
            and (col_mid > 0) \
            and (col_bot > 0) \
            and (col_margin > 0):
        
            #detect TB targets per day
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
            goutils.log2("ERR", 'At least one column among "'+
                    top_column_title+'", "' +\
                    mid_column_title+'", "' +\
                    bot_column_comment+'" is not found >> BT alerts not sent')
                
        # store json file
        fjson = open(json_file, 'w')
        fjson.write(json.dumps([daily_targets, margin], sort_keys=True, indent=4))
        fjson.close()
    else:
        [daily_targets, margin] = json.load(open(json_file, "r"))

    return 0, [daily_targets, margin]

# IN: list_targets=[["ROTE1-DS", 3], ["ROTE2-MS", 3], ...]
def set_tb_targets(guild_id: str, list_targets):
    gfile_name = get_gfile_name(guild_id)
    try:
        get_gapi_client()
        file = client.open(gfile_name)
        feuille=file.worksheet("BT")
    except:
        goutils.log2("ERR", "Unexpected error: "+str(sys.exc_info()[0]))
        return 1, "Cannot read BT sheet"
    
    #parsing title row
    col_top=0
    col_mid=0
    col_bot=0
    col_margin=0
    top_column_title='Top'
    mid_column_title='Mid'
    bot_column_title='Bot'
    margin_column_title='Marge'

    #Detect columns
    c = 1
    first_row=feuille.row_values(1)
    for value in first_row:
        if value==top_column_title:
            col_top=c
        elif value==mid_column_title:
            col_mid=c
        elif value==bot_column_title:
            col_bot=c
        elif value==margin_column_title:
            col_margin=c
        c+=1

    if      (col_top > 0) \
        and (col_mid > 0) \
        and (col_bot > 0) \
        and (col_margin > 0):
    
        #detect TB targets per day
        daily_names=feuille.col_values(col_top-1)
        top_stars=feuille.col_values(col_top)
        mid_stars=feuille.col_values(col_mid)
        bot_stars=feuille.col_values(col_bot)
    else:
        return 1, "Cannot read BT sheet"

    cells = []
    for target in list_targets:
        try:
            zone=target[0]
            tbs_round = zone.split('-')[0]
            tb_name = tbs_round[:-1]
            tb_phase = tbs_round[-1]
            side = zone.split('-')[1]
            stars = int(target[1])
        except:
            goutils.log2("ERR", "Unexpected error: "+str(sys.exc_info()[0]))
            return 1, "Cannot read BT targets"

        l = 1
        for daily_name in daily_names:
            top_target = top_stars[l-1] + '-' + top_stars[l]
            mid_target = mid_stars[l-1] + '-' + mid_stars[l]
            bot_target = bot_stars[l-1] + '-' + bot_stars[l]

            if daily_name!='':
                if top_stars[l-1] in [top_column_title, "DS"]:
                    current_tb_name = daily_name
                if current_tb_name==tb_name:
                    if daily_name!='':
                        current_tb_phase = daily_name[-1]
                    if current_tb_phase==tb_phase:
                        if top_target!='' or mid_target!='' or bot_target!='' and current_tb_phase==tb_phase:
                            if side in ["top", "DS"]:
                                c=col_top
                            elif side in ["mid", "MS"]:
                                c=col_mid
                            else: # side in ["bot", "LS"]:
                                c=col_bot

                            cells.append(gspread.cell.Cell(row=l+1, col=c, value=stars))

            l+=1

    feuille.update_cells(cells)

    # recreate CACHE file (return value is not useful)
    ret = get_tb_triggers(guild_id, True)
    data.reset_data()
    
    return 0, ""

def load_tb_teams(guild_id: str, force_load):
    if guild_id == None:
        gfile_name = "GuiOnBot config"
        guild_name = gfile_name
    else:
        gfile_name = get_gfile_name(guild_id)

        #Get guild name (in case gfile_name is different)
        query = "SELECT name FROM guilds WHERE id='"+guild_id+"'"
        goutils.log2("DBG", query)
        guild_name = connect_mysql.get_value(query)

    if gfile_name==None:
        goutils.log2("WAR", "No gfile for this guild ID "+guild_id)
        return 2, [], {}

    json_file = "CACHE"+os.path.sep+guild_name+"_config_tb_teams.json"

    if force_load or not os.path.isfile(json_file):
        try:
            get_gapi_client()
            file = client.open(gfile_name)
            feuille=file.worksheet("BT teams")

            list_dict_sheet=feuille.get_all_records()
        except gspread.exceptions.WorksheetNotFound:
            return [{}, {}, {}, {}]
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

def load_tw_counters(guild_id: str, force_load):
    if guild_id == None:
        gfile_name = "GuiOnBot config"
        guild_name = gfile_name
    else:
        gfile_name = get_gfile_name(guild_id)

        #Get guild name (in case gfile_name is different)
        query = "SELECT name FROM guilds WHERE id='"+guild_id+"'"
        goutils.log2("DBG", query)
        guild_name = connect_mysql.get_value(query)

    if gfile_name==None:
        goutils.log2("WAR", "No gfile for this guild ID "+guild_id)
        return 2, [], {}

    json_file = "CACHE"+os.path.sep+guild_name+"_config_tw_counters.json"

    if force_load or not os.path.isfile(json_file):
        try:
            get_gapi_client()
            file = client.open(gfile_name)
            feuille=file.worksheet("TW counters")

            list_dict_sheet=feuille.get_all_records()
        except gspread.exceptions.WorksheetNotFound:
            return [{}, {}, {}, {}]
        except Exception as e:
            goutils.log2("ERR", sys.exc_info()[0])
            goutils.log2("ERR", e)
            goutils.log2("ERR", traceback.format_exc())
            goutils.log2("ERR", "Cannot connect to Google API")
            return None

        tw_counters = {}
        for dict_line in list_dict_sheet:
            if dict_line['Adversaire'] != '':
                opponent = dict_line["Adversaire"]

                counter_def = {}
                for key in dict_line:
                    if key=="":
                        break
                    if key != "Adversaire":
                        counter_def[key] = dict_line[key]

                if not opponent in tw_counters:
                    tw_counters[opponent] = []
                tw_counters[opponent].append(counter_def)

        # store json file
        fjson = open(json_file, 'w')
        fjson.write(json.dumps(tw_counters, sort_keys=True, indent=4))
        fjson.close()
    else:
        tw_counters = json.load(open(json_file, "r"))

    return tw_counters

def read_rote_operations(list_zones=[]):
    dict_units = data.get("unitsList_dict.json")
    dict_tb = data.get("tb_definition.json")

    # Check list of zones
    list_planets = []
    goutils.log2("DBG", list_zones)
    for z in list_zones:
        if not z.startswith("ROTE"):
            return 1, "Zone ROTE inconnue "+z, None
        if not '-' in z:
            # eg: "ROTE4"
            if not z[4:] in ['1', '2', '3', '4', '5', '6', '']:
                return 1, "Phase/zone inconnue "+z, None
            list_planets += [k for k in dict_tb["zone_names"] if dict_tb["zone_names"][k].startswith(z)]

        else:
            # eg: "ROTE3-DS"
            filtered_planets = [k for k in dict_tb["zone_names"] if dict_tb["zone_names"][k]==z]
            if len(filtered_planets)!=1:
                return 1, "Zone inconnue "+z, None

            list_planets += filtered_planets

    rote_sheet_key = '1JqHbujIYTsHAkO9DCyQZFt0G-kKdhiwNBVgcI-VzJcw'
    try:
        goutils.log2("DBG", "Get client...")
        get_gapi_client()
        goutils.log2("DBG", "Open file...")
        file = client.open_by_key(rote_sheet_key)
        goutils.log2("DBG", "Open worksheet...")
        worksheet=file.worksheet('long_format')
        goutils.log2("DBG", "Read worksheet...")
        list_op_chars=worksheet.get_all_values()
    except Exception as e:
        goutils.log2("ERR", sys.exc_info()[0])
        goutils.log2("ERR", e)
        goutils.log2("ERR", traceback.format_exc())
        goutils.log2("WAR", "Cannot connect to Google API")
        return 1, "Impossible d'ouvrir le fichier des pelotons ROTE", None

    relic_by_phase = {'1': 5,
                      '2': 6,
                      '3': 7,
                      '4': 8,
                      '5': 9,
                      '6': 9}

    dict_ops_by_relic = {}
    goutils.log2("DBG", "Parse worksheet...")
    for char in list_op_chars[1:]:
        char_phase = char[1]
        char_planet = char[2]
        char_id = char[7]

        if len(list_planets)>0 and not char_planet in list_planets:
            continue
        
        if dict_units[char_id]["combatType"]==1:
            char_relic = relic_by_phase[char_phase]
        else:
            char_relic = 0

        if not char_id in dict_ops_by_relic:
            dict_ops_by_relic[char_id] = {}

        if not char_relic in dict_ops_by_relic[char_id]:
            dict_ops_by_relic[char_id][char_relic] = 0
        dict_ops_by_relic[char_id][char_relic] += 1

    return 0, "", dict_ops_by_relic
