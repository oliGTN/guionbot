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
        except gspread.exceptions.WorksheetNotFound:
            return 0, [], {}
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
        connect_mysql.update_guild_teams(gfile_name, dict_teams)

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
            return {}
        except Exception as e:
            goutils.log2("ERR", sys.exc_info()[0])
            goutils.log2("ERR", e)
            goutils.log2("ERR", traceback.format_exc())
            goutils.log2("ERR", "Cannot connect to Google API")
            return None

        dict_units=data.get("unitsAlias_dict.json") #key=alias, value=[nameKey, id]
    
        for ligne in list_dict_sheet[1:]:
            print(ligne)
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
                
    return dict_units

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

##############################################################
async def update_gwarstats(server_id):
    gfile_name = get_gfile_name(server_id)

    ec, et, tb_data = await connect_rpc.get_tb_status(server_id, "", False, -1)
    if ec != 0:
        return 1, et

    dict_phase = tb_data["phase"]
    dict_strike_zones = tb_data["strike_zones"]
    dict_tb_players = tb_data["players"]
    dict_open_zones = tb_data["open_zones"]

    try:
        get_gapi_client()
        file = client.open(gfile_name)
        feuille=file.worksheet("BT graphs")
    except:
        goutils.log2("ERR", "Unexpected error: "+str(sys.exc_info()[0]))
        return 1, "Erreur inconnue"

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

    ######################
    #players
    ######################

    #title line
    player_row1 = 35
    player_col1 = 1
    if dict_tb[dict_phase["type"]]["shortname"] == "ROTE":
        cells.append(gspread.cell.Cell(row=player_row1, col=player_col1+3, value="Mix deployment"))
        cells.append(gspread.cell.Cell(row=player_row1, col=player_col1+6, value=""))
    else:
        cells.append(gspread.cell.Cell(row=player_row1, col=player_col1+3, value="Fleet deployment"))
        cells.append(gspread.cell.Cell(row=player_row1, col=player_col1+6, value="Squad deployment"))

    sorted_dict_tb_players = dict(sorted(dict_tb_players.items(), key=lambda x: x[1]["score"]["deployed"] + x[1]["score"]["strikes"], reverse=True))

    #loop on each player
    line = player_row1 + 2
    for playername in sorted_dict_tb_players:
        # player name
        player = dict_tb_players[playername]
        cells.append(gspread.cell.Cell(row=line, col=player_col1+1, value=playername))

        # player score
        total_score = player["score"]["deployed"] + player["score"]["strikes"]
        cells.append(gspread.cell.Cell(row=line, col=player_col1+2, value=total_score))

        # deployments
        if dict_tb[dict_phase["type"]]["shortname"] == "ROTE":
            cells.append(gspread.cell.Cell(row=line, col=player_col1+3, value=player["score"]["deployedMix"]))
            cells.append(gspread.cell.Cell(row=line, col=player_col1+4, value=player["mix_gp"]))
            cells.append(gspread.cell.Cell(row=line, col=player_col1+6, value=""))
            cells.append(gspread.cell.Cell(row=line, col=player_col1+7, value=""))
        else:
            cells.append(gspread.cell.Cell(row=line, col=player_col1+3, value=player["score"]["deployedShips"]))
            cells.append(gspread.cell.Cell(row=line, col=player_col1+4, value=player["ship_gp"]))
            cells.append(gspread.cell.Cell(row=line, col=player_col1+6, value=player["score"]["deployedChars"]))
            cells.append(gspread.cell.Cell(row=line, col=player_col1+7, value=player["char_gp"]))

        # strikes
        total_strikes = 0
        i_zone = 1
        for zone_fullname in dict_open_zones:
            strike_txt = ""
            conflict = zone_fullname.split("_")[-1]

            #loop on all existing strikes in the TB dictionary
            for strike in dict_tb[zone_fullname]["strikes"]:
                max_waves = dict_tb[zone_fullname]["strikes"][strike][0]
                total_strikes += 1
                conflict_strike = conflict+"_"+strike
                if conflict_strike in player["strikes"]:
                    strike_txt += player["strikes"][conflict_strike]+" "
                else:
                    strike_txt += "?/"+str(max_waves)+" "
            cells.append(gspread.cell.Cell(row=line, col=player_col1+8+i_zone, value=strike_txt.strip()))
            i_zone += 1
        player_strikes = player["strike_attempts"]
        cells.append(gspread.cell.Cell(row=line, col=player_col1+12, value=str(player_strikes)+"/"+str(total_strikes)))

        line += 1

    # erase the table up to 50th line
    while line<player_row1+52:
        cells.append(gspread.cell.Cell(row=line, col=player_col1+1, value=""))
        cells.append(gspread.cell.Cell(row=line, col=player_col1+2, value=""))
        cells.append(gspread.cell.Cell(row=line, col=player_col1+3, value=""))
        cells.append(gspread.cell.Cell(row=line, col=player_col1+4, value=""))
        cells.append(gspread.cell.Cell(row=line, col=player_col1+6, value=""))
        cells.append(gspread.cell.Cell(row=line, col=player_col1+7, value=""))
        line += 1


    feuille.update_cells(cells)

    return 0, ""
