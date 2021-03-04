# -*- coding: utf-8 -*-

from swgohhelp import SWGOHhelp, settings
import sys
import time
import os
import difflib
import math
from functools import reduce
from math import ceil
from connect_gsheets import load_config_bt, load_config_teams, load_config_players, load_config_gt, load_config_counter, load_config_units
import connect_mysql
import connect_crinolo
import goutils
FORCE_CUT_PATTERN = "SPLIT_HERE"

#login password sur https://api.swgoh.help/profile
creds = settings(os.environ['SWGOHAPI_LOGIN'], os.environ['SWGOHAPI_PASSWORD'], '123', 'abc')
client = SWGOHhelp(creds)

def refresh_cache():
    #CLEAN OLD FILES NOT ACCESSED FOR LONG TIME
    #Need to keep KEEPDIR to prevent removal of the directory by GIT
    
    # Get the allyCodes to be refreshed
    # the query gets all allyCodes from master guild
    query = "SELECT allyCode FROM players WHERE guildName = ( \
                SELECT guildName \
                FROM players \
                WHERE allyCode = "+os.environ['MASTER_GUILD_ALLYCODE']+" \
            ) \
            ORDER BY lastUpdated ASC"
    list_master_allyCodes = connect_mysql.get_column(query)
    
    # the query gets all allyCodes from non-master guild
    query = "SELECT allyCode from players WHERE guildName != ( \
                SELECT guildName \
                FROM players \
                WHERE allyCode = "+os.environ['MASTER_GUILD_ALLYCODE']+" \
            ) \
            ORDER BY lastUpdated ASC"
    list_nonmaster_allyCodes = connect_mysql.get_column(query)

    #Compute the amount of players to be refreshed based on global refresh rate
    refresh_rate_bot_minutes = int(os.environ['REFRESH_RATE_BOT_MINUTES'])
    refresh_rate_player_minutes = int(os.environ['REFRESH_RATE_PLAYER_MINUTES'])
    nb_refresh_master_players = ceil(
        len(list_master_allyCodes) / refresh_rate_player_minutes * refresh_rate_bot_minutes)
    nb_refresh_nonmaster_players = 1
    print('Refreshing ' + str(nb_refresh_master_players) + '+' +
        str(nb_refresh_nonmaster_players) + ' files')

    #Refresh players from master guild
    for allyCode in list_master_allyCodes[:nb_refresh_master_players]:
        load_player(str(allyCode), True)
        
    #Refresh one player from non-master guild
    if len(list_nonmaster_allyCodes) >0:
        load_player(str(list_nonmaster_allyCodes[0]), True)
    
    #Check the amount of stored guilds, and remove if too many
    query = "SELECT name FROM guilds \
            WHERE name != (SELECT guildName FROM players WHERE allyCode = "+os.environ['MASTER_GUILD_ALLYCODE']+") \
            ORDER BY lastUpdated DESC"
    list_nonmaster_guilds = connect_mysql.get_column(query)
    keep_max_non_master_guilds = int(os.environ['KEEP_MAX_NONMASTER_GUILDS'])
    if len(list_nonmaster_guilds) > keep_max_non_master_guilds:
        for guildname in list_nonmaster_guilds[:keep_max_non_master_guilds]:
            print("INFO: delete guild "+guildname+" from DB")
            connect_mysql.simple_callproc("remove_guild", [guildname])
            
    #Check the amount of noguild players, and remove if too many
    query = "SELECT allyCode FROM players \
            WHERE guildName = '' \
            ORDER BY lastUpdated DESC"
    list_noguild_allyCodes = connect_mysql.get_column(query)
    keep_max_noguild_players = int(os.environ['KEEP_MAX_NOGUILD_PLAYERS'])
    if len(list_noguild_allyCodes) > keep_max_noguild_players:
        for allyCode in list_noguild_allyCodes[:keep_max_noguild_players]:
            print("INFO: delete player "+allyCode+" from DB")
            connect_mysql.simple_callproc("remove_player", [allyCode])

def stats_cache():
    sum_size = 0
    nb_files = 0
    for filename in os.listdir('CACHE'):
        #print(filename)
        if filename != 'KEEPDIR':
            file_path = 'CACHE' + os.path.sep + filename
            file_stats = os.stat(file_path)
            nb_files += 1
            sum_size += file_stats.st_size
    return 'Total CACHE: ' + str(nb_files) + ' files, ' + str(
        int(sum_size / 1024 / 1024 * 10) / 10) + ' MB'


def load_player(txt_allyCode, force_update):
    # The query tests if the update is less than 60 minutes for all players
    # Assumption: when the command is player-related, updating one is costless
    query_result = connect_mysql.get_line("SELECT \
                        (timestampdiff(MINUTE, players.lastUpdated, CURRENT_TIMESTAMP)<=60) AS recent, \
                        name \
                        FROM players WHERE allyCode = '"+txt_allyCode+"'")

    if len(query_result)>0:
        recent_player = query_result[0]
        player_name = query_result[1]
    else:
        recent_player = 0

    if not recent_player or force_update:
        sys.stdout.write('requesting data for ' + txt_allyCode + '...')
        sys.stdout.flush()
        player_data = client.get_data('player', txt_allyCode)
        if isinstance(player_data, list):
            if len(player_data) > 0:
                if len(player_data) > 1:
                    print ('WAR: client.get_data(\'player\', '+txt_allyCode+
                            ') has returned a list of size '+
                            str(len(player_data)))
                            
                ret_player = player_data[0]
                sys.stdout.write(' ' + ret_player['name'])
                sys.stdout.flush()
                
                # update DB
                connect_mysql.update_player(ret_player)
                sys.stdout.write('.\n')
                sys.stdout.flush()
                
            else:
                print ('ERR: client.get_data(\'player\', '+txt_allyCode+
                        ') has returned an empty list')
                return 'ERR: allyCode '+txt_allyCode+' not found'

        else:
            print ('ERR: client.get_data(\'player\', '+
                    txt_allyCode+') has not returned a list')
            print (player_data)
            return 'ERR: allyCode '+txt_allyCode+' not found'

    else:
        sys.stdout.write(player_name + ' OK\n')
    
    return 'OK'

def load_guild(txt_allyCode, load_players):
    
    #rechargement systématique des infos de guilde (liste des membres)
    sys.stdout.write('>Requesting guild data for allyCode ' + txt_allyCode +
                     '...\n')
    client_data = client.get_data('guild', txt_allyCode)
    if isinstance(client_data, list):
        if len(client_data) > 0:
            if len(client_data) > 1:
                print ('WAR: client.get_data(\'guild\', '+txt_allyCode+
                        ') has returned a list of size '+
                        str(len(player_data)))            
                        
            ret_guild = client_data[0]
            list_allyCodes = [x["allyCode"] for x in ret_guild["roster"]]
            connect_mysql.update_guild(ret_guild)

        else:
            print ('ERR: client.get_data(\'guild\', '+txt_allyCode+
                    ') has returned an empty list')
            return 'ERR: canot fetch guild fo allyCode '+txt_allyCode, None

    else:
        print ('ERR: client.get_data(\'guild\', '+
                txt_allyCode+') has not returned a list')
        print (client_data)
        return 'ERR: cannot fetch guild for allyCode '+txt_allyCode, None


    if load_players:
        #Get players and update status from DB
        # The query tests if the update is less than 60 minutes for players in master guild
        # For other players, check if less than 12 hours
        recent_players = connect_mysql.get_table( "\
            SELECT \
            CASE WHEN guildName = (SELECT guildName FROM players WHERE allyCode = "+os.environ['MASTER_GUILD_ALLYCODE']+") \
            THEN (timestampdiff(MINUTE, players.lastUpdated, CURRENT_TIMESTAMP)<=60) \
            ELSE (timestampdiff(HOUR, players.lastUpdated, CURRENT_TIMESTAMP)<=12) END AS recent, \
            allyCode \
            FROM players \
            WHERE players.guildName = (SELECT guildName FROM players WHERE allyCode = '"+txt_allyCode+"')")
        dict_recent_players={}
        for line in recent_players:
            dict_recent_players[line[1]]=line[0]
                
        #add player data
        total_players = len(ret_guild['roster'])
        sys.stdout.write('Total players in guild: ' + 
                            str(total_players) + '\n')
        i_player = 0
        for player in ret_guild['roster']:
            i_player = i_player + 1
            sys.stdout.write(str(i_player) + ': ')
            
            if not player['allyCode'] in dict_recent_players.keys():
                load_player(str(player['allyCode']), False)
            elif not dict_recent_players[player['allyCode']]:
                load_player(str(player['allyCode']), False)
            else:
                sys.stdout.write(player['name']+" OK\n")
    
    return "OK", ret_guild

def get_team_line_from_player(dict_player, objectifs, score_type, score_green,
                              score_amber, gv_mode, txt_mode, player_name):
    #score_type :
    #   1 : from 0 to 100% counting rarity/gear+relic/zetas... and 0 for each character below minimum
    #   2 : Same as #1, but still counting scores below minimum
    #   3 : score = gp*vitesse/vitesse_requise
    #   * : Affichage d'une icône verte (100%), orange (>=80%) ou rouge

    line = ''
    # print('DBG: get_team_line_from_player '+dict_player['name'])
    nb_subobjs = len(objectifs)
    
    #INIT tableau des resultats
    tab_progress_player = [[] for i in range(nb_subobjs)]
    for i_subobj in range(0, nb_subobjs):
        nb_chars = len(objectifs[i_subobj][2])
        if score_type == 1:
            tab_progress_player[i_subobj] = [[0, '.     ', True]
                                            for i in range(nb_chars)]
        elif score_type == 2:
            tab_progress_player[i_subobj] = [[0, '.     ', True]
                                            for i in range(nb_chars)]
        else:  #score_type==3
            tab_progress_player[i_subobj] = [[0, '.         ', True]
                                            for i in range(nb_chars)]

    # Loop on categories within the goals
    for i_subobj in range(0, nb_subobjs):
        dict_char_subobj = objectifs[i_subobj][2]

        for character_id in dict_char_subobj:
            progress = 0
            progress_100 = 0
            
            character_obj = dict_char_subobj[character_id]
            i_character = character_obj[0]
            if character_id in dict_player:
                # print('DBG: '+character_id+' trouvé')

                character_nogo = False
                #print(character_roster)

                #Etoiles
                req_rarity_min = character_obj[1]
                req_rarity_reco = character_obj[3]
                player_rarity = dict_player[character_id]['rarity']
                progress_100 = progress_100 + 1
                progress = progress + min(1, player_rarity / req_rarity_reco)
                if player_rarity < req_rarity_min:
                    character_nogo = True
                # print('DBG: progress='+str(progress)+' progress_100='+str(progress_100))
                
                #Gear
                req_gear_min = character_obj[2]
                req_relic_min=0
                if req_gear_min == '':
                    req_gear_min = 1
                elif type(req_gear_min) == str:
                    req_relic_min=int(req_gear_min[-1])
                    req_gear_min=13
                    
                req_gear_reco = character_obj[4]
                req_relic_reco=0
                if req_gear_reco == '':
                    req_gear_reco = 1
                elif type(req_gear_reco) == str:
                    req_relic_reco=int(req_gear_reco[-1])
                    req_gear_reco=13

                player_gear = dict_player[character_id]['gear']
                if player_gear < 13:
                    player_relic = 0
                else:
                    player_relic = dict_player[character_id]['relic_currentTier'] - 2

                progress_100 = progress_100 + 1
                progress = progress + min(1, (player_gear+player_relic) / (req_gear_reco+req_relic_reco))
                if (player_gear+player_relic) < (req_gear_min+req_relic_min):
                    character_nogo = True
                # print('DBG: player_gear='+str(player_gear)+' player_relic='+str(player_relic))
                # print('DBG: req_gear_min='+str(req_gear_min)+' req_relic_min='+str(req_relic_min))
                # print('DBG: character_nogo='+str(character_nogo))
                # print('DBG: progress='+str(progress)+' progress_100='+str(progress_100))

                #Zetas
                req_zetas = character_obj[5].split(',')
                req_zeta_ids = [goutils.get_zeta_id_from_short(character_id, x) for x in req_zetas]
                req_zeta_ids = list(filter(lambda x: x != '', req_zeta_ids))
                        
                player_nb_zetas = 0
                progress_100 += len(req_zeta_ids)
                for zeta in dict_player[character_id]['zetas']:
                    if zeta in req_zeta_ids:
                        if dict_player[character_id]['zetas'][zeta] == 8:
                            player_nb_zetas += 1
                            progress += 1
                if player_nb_zetas < len(req_zeta_ids):
                    character_nogo = True
                # print('DBG: progress='+str(progress)+' progress_100='+str(progress_100))

                #Vitesse (optionnel)
                req_speed = character_obj[6]
                player_speed = dict_player[character_id]['speed']
                req_speed = character_obj[6]
                if req_speed != '':
                    progress_100 = progress_100 + 1
                    progress = progress + min(1, player_speed / req_speed)
                else:
                    req_speed = player_speed
                # print('DBG: progress='+str(progress)+' progress_100='+str(progress_100))

                player_gp = dict_player[character_id]['gp']


                #Progress
                if score_type == 1:
                    character_progress = progress / progress_100
                elif score_type == 2:
                    character_progress = progress / progress_100
                else:  #score_type==3)
                    character_progress = int(player_gp * player_speed / req_speed)

                #Display
                character_display = str(player_rarity)
                if player_gear < 13:
                    character_display += '.' + "{:02d}".format(player_gear)                        
                else:
                    character_display += '.R' + str(player_relic)
                character_display += '.' + str(player_nb_zetas)
                if score_type == 3:
                    character_display += '.' + "{:03d}".format(player_speed)
                        
                if gv_mode:
                    if player_rarity < req_rarity_reco:
                        character_display += "\N{UP-POINTING RED TRIANGLE} "+\
                                            character_id + \
                                            " est seulement " + \
                                            str(player_rarity) + "/" +\
                                            str(req_rarity_reco) +\
                                            "\N{WHITE MEDIUM STAR}"
                    elif player_gear < req_gear_reco:
                        character_display += "\N{CONFUSED FACE} "+\
                                            character_id + \
                                            " est seulement G" + \
                                            str(player_gear) + "/" +\
                                            str(req_gear_reco)
                    elif player_relic < req_relic_reco:
                        character_display += "\N{WHITE RIGHT POINTING BACKHAND INDEX} "+\
                                            character_id + \
                                            " est seulement relic " + \
                                            str(player_relic) + "/" +\
                                            str(req_relic_reco)
                    else:
                        character_display += "\N{WHITE HEAVY CHECK MARK} "+\
                                            character_id + \
                                            " est OK"
                    character_progress_100 = int(character_progress*100)
                    character_display += " - " + str(character_progress_100) +"%"

                tab_progress_player[i_subobj][i_character - 1][0] = character_progress
                tab_progress_player[i_subobj][i_character - 1][1] = character_display
                tab_progress_player[i_subobj][i_character - 1][2] = character_nogo
                # print(tab_progress_player[i_subobj][i_character - 1])

            else:
                # character not found in player's roster
                # print('DBG: '+character_subobj[0]+' pas trouvé dans '+str(dict_player['roster'].keys()))
                # dict_player[character_id] = {"rarity": 0,
                                            # "gear": 0,
                                            # "rarity": 0,
                                            # "gear": 0,
                                            # "relic_currentTier": 0,
                                            # "gp": 0,
                                            # "speed": 0,
                                            # "zetas": {}}
                                            
                if gv_mode:
                    character_display = "\N{CROSS MARK} "+\
                                        character_id + \
                                        " n'est pas débloqué - 0%"
                tab_progress_player[i_subobj][i_character - 1][1] += character_display

    #calcul du score global
    score = 0
    score100 = 0
    score_nogo = False
    for i_subobj in range(0, nb_subobjs):
        nb_sub_obj = len(objectifs[i_subobj][2])
        for i_character in range(0, nb_sub_obj):
            tab_progress_sub_obj = tab_progress_player[i_subobj][i_character]
            if not gv_mode:
                if not tab_progress_sub_obj[2]:
                    if txt_mode:
                        line += tab_progress_sub_obj[1] + '|'
                    else:
                        line += '**' + goutils.pad_txt2(tab_progress_sub_obj[1]) + '**|'
                else:
                    if txt_mode:
                        line += tab_progress_sub_obj[1] + '|'
                    else:
                        line += goutils.pad_txt2(tab_progress_sub_obj[1]) + '|'
            else:
                line += tab_progress_sub_obj[1] + "\n"

        min_perso = objectifs[i_subobj][1]
        # print('DBG: '+str(tab_progress_player[i_subobj]))

        #Extraction des scores pour les persos non-exclus
        tab_score_player_values = [(lambda f: (f[0] * (not f[2])))(x)
                                   for x in tab_progress_player[i_subobj]]

        score += sum(sorted(tab_score_player_values)[-min_perso:])
        score100 += min_perso
        # print('DBG: score='+str(score)+' score100='+str(score100))
        
        if 0.0 in sorted(tab_score_player_values)[-min_perso:]:
            score_nogo = True

    #pourcentage sur la moyenne
    if score_type == 1:
        score = score / score100 * 100
    elif score_type == 2:
        score = score / score100 * 100

    #affichage du score
    if not gv_mode:
        line += str(int(score))

    # affichage de la couleur
    if not txt_mode:
        if score_nogo:
            line += '\N{CROSS MARK}'
        elif score >= score_green:
            line += '\N{GREEN HEART}'
        elif score >= score_amber:
            line += '\N{LARGE ORANGE DIAMOND}'
        else:
            line += '\N{CROSS MARK}'

    # Display the IG name only, as @mentions only pollute discord
    if not gv_mode:
        line += '|' + player_name + '\n'

    return score, line, score_nogo


def get_team_entete(team_name, objectifs, score_type, txt_mode):
    entete = ''

    nb_levels = len(objectifs)
    #print('DBG: nb_levels='+str(nb_levels))

    #Affichage des prérequis
    entete += '**Team: ' + team_name + '**\n'
    for i_level in range(0, nb_levels):
        #print('DBG: i_level='+str(i_level))
        #print('DBG: obj='+str(objectifs[i_level]))
        nb_sub_obj = len(objectifs[i_level][2])
        #print('DBG: nb_sub_obj='+str(nb_sub_obj))
        entete += '**' + objectifs[i_level][0] + '**\n'
        for i_sub_obj in range(0, nb_sub_obj):
            for perso in objectifs[i_level][2]:
                if objectifs[i_level][2][perso][0] == i_sub_obj + 1:
                    perso_rarity_min = objectifs[i_level][2][perso][1]
                    perso_gear_min = objectifs[i_level][2][perso][2]
                    perso_rarity_reco = objectifs[i_level][2][perso][3]
                    perso_gear_reco = objectifs[i_level][2][perso][4]

                    #Zetas
                    req_zetas = objectifs[i_level][2][perso][5].split(',')
                    req_zeta_names = [x[1] for x in goutils.get_zeta_from_shorts(perso, req_zetas)]
                    
                    entete += '**' + objectifs[i_level][0][0] + str(
                        i_sub_obj + 1) + '**: ' + perso + ' (' + str(
                            perso_rarity_min) + 'G' + str(
                                perso_gear_min) + ' à ' + str(
                                    perso_rarity_reco) + 'G' + str(
                                        perso_gear_reco) + ', zetas=' + str(
                                            req_zeta_names) + ')\n'

    #ligne d'entete
    entete += '\n'
    for i_level in range(0, nb_levels):
        nb_sub_obj = len(objectifs[i_level][2])
        #print('DBG: nb_sub_obj='+str(nb_sub_obj))
        for i_sub_obj in range(0, nb_sub_obj):
            #print('DBG:'+str(objectifs[i_level][0][0]+str(i_sub_obj)))
            if score_type == 1:
                nom_sub_obj = goutils.pad_txt(
                    objectifs[i_level][0][0] + str(i_sub_obj + 1), 6)
            elif score_type == 2:
                nom_sub_obj = goutils.pad_txt(
                    objectifs[i_level][0][0] + str(i_sub_obj + 1), 6)
            else:
                nom_sub_obj = goutils.pad_txt(
                    objectifs[i_level][0][0] + str(i_sub_obj + 1), 10)
            if txt_mode:
                entete += nom_sub_obj + '|'
            else:
                entete += goutils.pad_txt2(nom_sub_obj) + '|'

    entete += 'GLOB|Joueur\n'

    return entete

def get_team_progress(list_team_names, txt_allyCode, compute_guild,
                        score_type, score_green, score_amber, gv_mode, txt_mode):
                        
    ret_get_team_progress = {}

    #Recuperation des dernieres donnees sur gdrive
    liste_team_gt, dict_team_gt = load_config_teams()
    dict_units = load_config_units()
    
    if not compute_guild:
        #only one player, potentially several teams
        
        #Load or update data for the player
        ret = load_player(txt_allyCode, False)
        if ret != 'OK':
            #error wile loading guild data
            return 'ERREUR: joueur non trouvée pour code allié ' + txt_allyCode
            
    else:
        #Get data for the guild and associated players
        ret, guild = load_guild(txt_allyCode, True)
        if ret != 'OK':
            return "ERR: cannot get guild data from SWGOH.HELP API"

    if not ('all' in list_team_names) and gv_mode:
        #Need to transform the name of the team into a character
        list_character_ids=[]
        for character_alias in list_team_names:
            #Get full character name
            closest_names=difflib.get_close_matches(character_alias.lower(), dict_units.keys(), 3)
            if len(closest_names)<1:
                ret_print_character_stats += \
                    'INFO: aucun personnage trouvé pour '+character_alias+'\n'
            else:
                [character_name, character_id]=dict_units[closest_names[0]]
                list_character_ids.append(character_id)
        list_team_names = [x+"-GV" for x in list_character_ids]

    #Get player data
    print("Get player data from DB...")
    query = "SELECT players.name, \
            guild_teams.name, \
            guild_team_roster.unit_id, \
            rarity, \
            gear, \
            relic_currentTier, \
            gp, \
            SUM(unscaledDecimalValue/1e8) as speed \
            FROM players \
            JOIN guild_teams \
            JOIN guild_subteams ON guild_subteams.team_id = guild_teams.id \
            JOIN guild_team_roster ON guild_team_roster.subteam_id = guild_subteams.id \
            JOIN roster ON roster.defId = guild_team_roster.unit_id AND roster.player_id = players.id \
            JOIN roster_stats ON roster_stats.roster_id = roster.id AND roster_stats.unitStatId = 5\n"
    if not compute_guild:
        query += "WHERE allyCode = '"+txt_allyCode+"'\n"
    else:
        query += "WHERE players.guildName = \
                (SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"')\n"
    if not 'all' in list_team_names:
        query += "AND("
        for team_name in list_team_names:
            query += "guild_teams.name = '"+team_name+"' OR "
        query = query[:-3] + ")\n"
    elif gv_mode == False:
        query += "AND NOT guild_teams.name LIKE '%-GV'\n"
    else:
        query += "AND guild_teams.name LIKE '%-GV'\n"
       
    query += "GROUP BY players.name, guild_teams.name, guild_team_roster.unit_id, \
            rarity, gear, relic_currentTier, gp \
            ORDER BY players.name, guild_teams.name"
    
    # print(query)
    player_data = connect_mysql.get_table(query)
    #print(player_data)
    
    print("Get zeta data from DB...")
    query = "SELECT players.name, \
            guild_teams.name, \
            guild_team_roster.unit_id, \
            guild_team_roster_zetas.name as zeta, \
            roster_skills.level \
            FROM players \
            JOIN guild_teams \
            JOIN guild_subteams ON guild_subteams.team_id = guild_teams.id \
            JOIN guild_team_roster ON guild_team_roster.subteam_id = guild_subteams.id \
            JOIN guild_team_roster_zetas ON guild_team_roster_zetas.roster_id = guild_team_roster.id \
            JOIN roster ON roster.defId = guild_team_roster.unit_id AND roster.player_id = players.id \
            JOIN roster_skills ON roster_skills.roster_id = roster.id AND roster_skills.name = guild_team_roster_zetas.name \n"
    if not compute_guild:
        query += "WHERE allyCode = '"+txt_allyCode+"'\n"
    else:
        query += "WHERE players.guildName = \
                (SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"')\n"
    if not 'all' in list_team_names:
        query += "AND("
        for team_name in list_team_names:
            query += "guild_teams.name = '"+team_name+"' OR "
        query = query[:-3] + ")\n"
    elif gv_mode == False:
        query += "AND NOT guild_teams.name LIKE '%-GV'\n"
    else:
        query += "AND guild_teams.name LIKE '%-GV'\n"
       
    query += "ORDER BY allyCode, guild_teams.name, guild_subteams.id, guild_team_roster.id"
    
    #print(query)
    player_zeta_data = connect_mysql.get_table(query)
    #print(player_zeta_data)
        
    if len(player_data) > 0:
        print("Recreate dict_teams...")
        dict_teams = goutils.create_dict_teams(player_data, player_zeta_data)
        print("-> OK")
    else:
        print("no data recovered for allyCode="+txt_allyCode+" and teams="+str(list_team_names)+"...")
    
    
    # Compute teams for this player
    if gv_mode:
        filtered_liste_team_gt = [x for x in 
                                filter(lambda f:f[-3:]=="-GV", liste_team_gt)]
    else:
        filtered_liste_team_gt = [x for x in 
                                filter(lambda f:f[-3:]!="-GV", liste_team_gt)]
    if 'all' in list_team_names:
        list_team_names = filtered_liste_team_gt
    
    for team_name in list_team_names:
        if not (team_name in dict_team_gt) and not ('all' in list_team_names):
            if gv_mode:
                ret_get_team_progress[team_name] = \
                        'ERREUR: Guide de Voyage inconnu pour ' + \
                        team_name + '. Liste=' + str(filtered_liste_team_gt)
            else:
                ret_get_team_progress[team_name] = 'ERREUR: team ' + \
                        team_name + ' inconnue. Liste=' + str(filtered_liste_team_gt)
        else:
            ret_team = []
            objectifs = dict_team_gt[team_name]
            #print(objectifs)

            if not gv_mode:
                if len(list_team_names) == 1 and len(dict_teams.keys()):
                    ret_team += get_team_entete(team_name, objectifs, \
                                                score_type, txt_mode)
                else:
                    ret_team += 'Team ' + team_name + '\n'

            tab_lines = []
            count_green = 0
            count_amber = 0
            for player_name in dict_teams:
                if team_name in dict_teams[player_name]:
                    dict_player = dict_teams[player_name][team_name]
                else:
                    dict_player = {}
                    
                #resultats par joueur
                score, line, nogo = get_team_line_from_player(
                    dict_player, objectifs, score_type, score_green, score_amber,
                    gv_mode, txt_mode, player_name)
                tab_lines.append([score, line, nogo])
                if score >= score_green and not nogo:
                    count_green += 1
                if score >= score_amber and not nogo:
                    count_amber += 1

            #Tri des nogo=False en premier, puis score décroissant
            for score, txt, nogo in sorted(tab_lines,
                                           key=lambda x: (x[2], -x[0])):
                ret_team.append([txt, score])

            ret_get_team_progress[team_name] = ret_team, count_green, count_amber

    return ret_get_team_progress

def print_team_progress(list_team_names, txt_allyCode, compute_guild,
                        score_type, score_green, score_amber, gv_mode, txt_mode):
    ret_print_team_progress = ""
    
    ret_get_team_progress = get_team_progress(list_team_names, txt_allyCode,
                            compute_guild, score_type, score_green, score_amber,
                            gv_mode, txt_mode)
    
    if len(ret_get_team_progress) == 1:
        #one team only, one player
        team = list(ret_get_team_progress.keys())[0]
        ret_team = ret_get_team_progress[team]
        if type(ret_team) == str:
            ret_print_team_progress += ret_team
        else:
            for ret_player in ret_team[0]:
                player_txt = ret_player[0]
                player_score = ret_player[1]
                ret_print_team_progress += "Progrès pour "+team+"\n"
                ret_print_team_progress += player_txt + "> Global: "+\
                                            str(int(player_score))+"%"
    else:
        for team in ret_get_team_progress:
            ret_team = ret_get_team_progress[team]
            if type(ret_team) == str:
                ret_print_team_progress += ret_team
            else:
                for ret_player in ret_team[0]:
                    player_txt = ret_player[0]
                    player_score = ret_player[1]
                    ret_print_team_progress += team + ": " + \
                                            str(int(player_score)) + "%\n"
                                            
    return ret_print_team_progress
                        
                        
def assign_gt(allyCode, txt_mode):
    ret_assign_gt = ''

    dict_players = load_config_players()[0]

    liste_territoires = load_config_gt()
        # index=priorité-1, value=[territoire, [[team, nombre, score]...]]
    liste_team_names = []
    for territoire in liste_territoires:
        for team in territoire[1]:
            liste_team_names.append(team[0])
    liste_team_names = [x for x in set(liste_team_names)]
    #print(liste_team_names)

    #Calcule des meilleurs joueurs pour chaque team
    dict_teams = get_team_progress(liste_team_names, allyCode, True, 3, -1, -1, True)
    if type(dict_teams) == str:
        return dict_teams
    else:
        for team in dict_teams:
            #la fonction renvoie un tuple (txt, nombre)
            #on ne garde que le txt, qu'on splite en lignes avec séparateur
            dict_teams[team] = dict_teams[team][0].split('\n')

    for priorite in liste_territoires:
        nom_territoire = priorite[0]
        for team in priorite[1]:
            tab_lignes_team = dict_teams[team[0]]
            #print(ret_function_gtt)
            if tab_lignes_team[0][0:3] == "ERR":
                ret_assign_gt += nom_territoire + ': **WARNING** team inconnue ' + team[
                    0] + '\n'
            else:
                req_nombre = team[1]
                req_score = team[2]
                nb_joueurs_selectionnes = 0
                copy_tab_lignes_team = [x for x in tab_lignes_team]
                for ligne in copy_tab_lignes_team:
                    tab_joueur = ligne.split('|')
                    if len(tab_joueur) > 1 and tab_joueur[-1] != 'Joueur':
                        #print(tab_joueur)
                        nom_joueur = tab_joueur[-1]
                        score_joueur = int(tab_joueur[-2])
                        if score_joueur >= req_score:
                            if req_nombre == '' or nb_joueurs_selectionnes < req_nombre:
                                nb_joueurs_selectionnes += 1
                                ret_assign_gt += nom_territoire + ': '
                                if nom_joueur in dict_players and not txt_mode:
                                    ret_assign_gt += dict_players[nom_joueur][
                                        2]
                                else:  #joueur non-défini dans gsheets ou mode texte
                                    ret_assign_gt += nom_joueur
                                ret_assign_gt += ' doit placer sa team ' + team[
                                    0] + '\n'
                                tab_lignes_team.remove(ligne)

                if req_nombre != '' and nb_joueurs_selectionnes < req_nombre:
                    ret_assign_gt += nom_territoire + ': **WARNING** pas assez de team ' + team[
                        0] + '\n'

            ret_assign_gt += '\n'

    return ret_assign_gt


def score_of_counter_interest(team_name, counter_matrix):
    current_score = 0
    for row in counter_matrix:
        # Count if the team_name can counter the current team row
        # Ignore the row if the team counters itself
        if team_name in row[1] and row[0] != team_name:
            current_score += 1
    return current_score


def guild_counter_score(txt_allyCode):
    ret_guild_counter_score = f"""
*Rec = Niveau recommandé / Min = Niveau minimum*
*w/o TW Def = Idem en enlevant les équipes placées en défense d'une TW*
*L'intérêt absolu mesure le nombre de fois que l'équipe X intervient en tant qu'équipe de contre*
{FORCE_CUT_PATTERN}
"""

    list_counter_teams = load_config_counter()
    list_needed_teams = set().union(*[(lambda x: x[1])(x)
                                      for x in list_counter_teams])
    dict_needed_teams = get_team_progress(list_needed_teams, txt_allyCode, True,
                                            1, 100, 80, True)
    # for k in dict_needed_teams.keys():
    # dict_needed_teams[k]=list(dict_needed_teams[k])
    # dict_needed_teams[k][0]=[]
    # print(list_counter_teams)

    gt_teams = load_config_gt()
    gt_teams = [(name[0], name[1]) for name in
                [teams for territory in gt_teams for teams in territory[1]]]

    result = []
    for nteam_key in dict_needed_teams.keys():
        if dict_needed_teams[nteam_key][0][:3] == 'ERR':
            result.append({
                "team_name": None,
                "rec_count": None,
                "min_count": None,
                "score": None,
                "max_score": None,
                "error": dict_needed_teams[nteam_key][0]
            })
        else:
            result.append({
                "team_name": nteam_key,
                "rec_count": dict_needed_teams[nteam_key][1],
                "min_count": dict_needed_teams[nteam_key][2],
                "score": score_of_counter_interest(nteam_key,
                                                   list_counter_teams),
                "max_score": len(list_counter_teams),
                "error": None
            })

    result = sorted(
        result,
        key=lambda i:
        (i['score'], i['rec_count'], i['min_count'], i['team_name']))

    ret_guild_counter_score += """
\n**Nombre de joueurs ayant l'équipe X**
```
{0:15}: {1:3} ↗ {2:3} | {3:10} - {4:5}
""".format("Equipe", "Rec", "Min", "w/o TW Def", "Intérêt absolu")

    for line in result:
        if line["error"]:
            ret_guild_counter_score += line["error"] + '\n'
            continue

        gt_subteams = list(
            filter(lambda x: x[0] == line["team_name"], gt_teams))
        needed_team_named = 0
        if gt_subteams:
            needed_team_named = reduce(
                lambda x, y: x[1] + y[1],
                gt_subteams) if len(gt_subteams) > 1 else gt_subteams[0][1]

        ret_guild_counter_score += "{0:15}: {1:3} ↗"\
                " {2:3} | {3:3} ↗ {4:3}  - {5:2}/{6:2}\n".format(
                    line["team_name"],
                    line["rec_count"],
                    line["min_count"],
                    max(0, line["rec_count"]-needed_team_named),
                    max(0, line["min_count"]-needed_team_named),
                    line["score"],
                    line["max_score"])

    ret_guild_counter_score += f"```{FORCE_CUT_PATTERN}"

    ret_guild_counter_score += """
\n**Capacité de contre par adversaire**
```
{0:15}: {1:3} ↗ {2:3} | {3:10} 🎯 {4:2}
""".format("Equipe", "Rec", "Min", "w/o TW Def", "Besoin cible")
    for cteam in sorted(list_counter_teams):
        green_counters = 0
        green_counters_wo_def = 0
        amber_counters = 0
        amber_counters_wo_def = 0
        for team in cteam[1]:
            green_counters += dict_needed_teams[team][1]
            amber_counters += dict_needed_teams[team][2]

            # compute how many we need to set on TW defence
            gt_subteams = list(filter(lambda x: x[0] == team, gt_teams))
            needed_team_named = 0
            if gt_subteams:
                needed_team_named = reduce(
                    lambda x, y: x[1] + y[1],
                    gt_subteams) if len(gt_subteams) > 1 else gt_subteams[0][1]

            green_counters_wo_def += dict_needed_teams[team][1]\
                                   - needed_team_named
            amber_counters_wo_def += dict_needed_teams[team][2]\
                                   - needed_team_named

        ret_guild_counter_score += "{0:15}: {1:3} ↗"\
                                   " {2:3} | {3:3} ↗ {4:3}  🎯 {5:2}\n".format(
                                       cteam[0],
                                       green_counters,
                                       amber_counters,
                                       green_counters_wo_def,
                                       amber_counters_wo_def,
                                       cteam[2])
    ret_guild_counter_score += "```"

    return ret_guild_counter_score

def print_character_stats(characters, txt_allyCode, compute_guild):
    ret_print_character_stats = ''

    #Recuperation des dernieres donnees sur gdrive
    dict_units = load_config_units()

    list_stats_for_display=[[5, "Vit", False, 'v'],
                            [6, "DegPhy", False, 'd'],
                            [7, "DegSpé", False, ''],
                            [1, " Santé", False, 's'],
                            [28, "Protec", False, ''],
                            [17, "Pouvoir", True, 'p'],
                            [18, "Ténacité", True, '']]
    
    #manage sorting options
    sort_option='name'
    if characters[0][0] == '-':
        sort_option = characters[0][1:]
        characters = characters[1:]
        
    dict_virtual_characters={} #{key=alias or ID, value=[rarity, gear, relic, nameKey]}

    if not compute_guild:
        #only one player, potentially several characters
        
        #parse the list to detect virtual characters "name:rarity:R4" or "name:rarity:G11"
        for character in characters:
            tab_virtual_character = character.split(':')
            if len(tab_virtual_character) == 3:
                char_alias = tab_virtual_character[0]
                if char_alias == "all":
                    return "ERR: impossible de demander un niveau spécifique pour all"
                
                if not tab_virtual_character[1] in "1234567":
                    return "ERR: la syntaxe "+character+" est incorrecte pour les étoiles"
                char_rarity = int(tab_virtual_character[1])
                
                if tab_virtual_character[2][0] in "gG":
                    if tab_virtual_character[2][1:].isnumeric():
                        char_gear = int(tab_virtual_character[2][1:])
                        if (char_gear<1) or (char_gear>13):
                            return "ERR: la syntaxe "+character+" est incorrecte pour le gear"
                        dict_virtual_characters[char_alias] = [char_rarity, char_gear, 0, '']
                    else:
                        return "ERR: la syntaxe "+character+" est incorrecte pour le gear"
                elif tab_virtual_character[2][0] in "rR":
                    if tab_virtual_character[2][1:].isnumeric():
                        char_relic = int(tab_virtual_character[2][1:])
                        if (char_relic<0) or (char_relic>8):
                            return "ERR: la syntaxe "+character+" est incorrecte pour le relic"
                        dict_virtual_characters[char_alias] = [char_rarity, 13, char_relic, '']
                    else:
                        return "ERR: la syntaxe "+character+" est incorrecte pour le relic"
                else:
                    return "ERR: la syntaxe "+character+" est incorrecte pour le gear"
                    
                #now that the virtual character is stored in the dictionary,
                # let the alias only in the list of characters
                characters = [char_alias if x == character else x for x in characters]
                
            elif len(tab_virtual_character) == 1:
                #regular character, not virtual
                pass
            else:
                return "ERR: la syntaxe "+character+" est incorrecte"
        
        #Get data for this player
        ret = load_player(txt_allyCode, False)
        if ret != 'OK':
            #error wile loading guild data
            return 'ERREUR: joueur non trouvé pour code allié ' + txt_allyCode
        
        #Manage request for all characters
        if 'all' in characters:
            print("Get player_data from DB...")
            query ="SELECT players.name, defId, units.nameKey, \
                    roster.combatType, rarity, gear, relic_currentTier, \
                    ifnull(unitStatId,0), coalesce(sum(unscaledDecimalValue),0) \
                    FROM roster \
                    LEFT JOIN roster_stats ON roster_stats.roster_id = roster.id \
                    JOIN players ON players.id = roster.player_id \
                    JOIN units ON units.unit_id = roster.defId \
                    WHERE players.allyCode = '"+txt_allyCode+"' \
                    AND roster.combatType=1 AND roster.level >= 50 \
                    AND ("
            for display_stat in list_stats_for_display:
                query += "unitStatId = "+str(display_stat[0])+" OR "
            query += "isnull(unitStatId)) \
                    GROUP BY players.name, defId, units.nameKey, roster.combatType, rarity, gear, relic_currentTier, unitStatId \
                    ORDER BY players.name, units.nameKey, unitStatId"
            
            db_stat_data = connect_mysql.get_table(query)
            db_stat_data_mods = []
            list_character_ids=set([x[1] for x in db_stat_data])
            
        else:
            #specific list of characters for one player
            list_character_ids=[]
            for character_alias in characters:
                #Get full character name
                closest_names=difflib.get_close_matches(character_alias.lower(), dict_units.keys(), 3)
                if len(closest_names)<1:
                    ret_print_character_stats += \
                        'INFO: aucun personnage trouvé pour '+character_alias+'\n'
                else:
                    [character_name, character_id]=dict_units[closest_names[0]]
                    list_character_ids.append(character_id)
                    
                    if (character_alias in dict_virtual_characters) and \
                        character_alias != character_id:
                        #replace the alias key by the ID key in the dictionary
                        dict_virtual_characters[character_id] = \
                            dict_virtual_characters[character_alias]
                        dict_virtual_characters[character_id][3] = character_name
                        del dict_virtual_characters[character_alias]

            print("Get player_data from DB...")
            query ="SELECT players.name, defId, units.nameKey, \
                    roster.combatType, rarity, gear, relic_currentTier, \
                    ifnull(unitStatId,0), coalesce(sum(unscaledDecimalValue),0) \
                    FROM roster \
                    LEFT JOIN roster_stats ON roster_stats.roster_id = roster.id \
                    JOIN players ON players.id = roster.player_id \
                    JOIN units ON units.unit_id = roster.defId \
                    WHERE players.allyCode = '"+txt_allyCode+"' \
                    AND ("
            for character_id in list_character_ids:
                query += "defId = '"+character_id+"' OR "
            query = query[:-3] + ") \
                    AND ("
            for display_stat in list_stats_for_display:
                query += "unitStatId = "+str(display_stat[0])+" OR "
            query += "isnull(unitStatId)) \
                    GROUP BY players.name, defId, units.nameKey, roster.combatType, rarity, gear, relic_currentTier, unitStatId \
                    ORDER BY players.name, units.nameKey, unitStatId"

            db_stat_data = connect_mysql.get_table(query)
            
            #Get mod data for virtual characters
            if len(dict_virtual_characters) > 0:
                print("Get player mod data from DB...")
                query ="SELECT players.name, defId,  \
                        mods.id, pips, mod_set, mods.level, \
                        isPrimary, unitStat, value \
                        FROM roster \
                        JOIN players ON players.id = roster.player_id \
                        JOIN mods ON mods.roster_id = roster.id \
                        JOIN mod_stats ON mod_stats.mod_id = mods.id \
                        WHERE players.allyCode = '"+txt_allyCode+"' \
                        AND ("
                for character_id in dict_virtual_characters.keys():
                    query += "defId = '"+character_id+"' OR "
                query = query[:-3] + ")"

                db_stat_data_mods = connect_mysql.get_table(query)
            else:
                db_stat_data_mods = []
            
        if len(db_stat_data) == 0:
            query = "SELECT players.name FROM players WHERE allyCode = "+txt_allyCode
            player_name = connect_mysql.get_value(query)
        else:
            player_name = db_stat_data[0][0]
        list_player_names = [player_name]
        
        ret_print_character_stats += "Statistiques pour "+player_name+'\n'

    elif len(characters) == 1 and characters[0] != "all":
        #Compute stats at guild level, only one character
        
        #Get data for the guild and associated players
        ret, guild = load_guild(txt_allyCode, True)
        if ret != 'OK':
            return "ERR: cannot get guild data from SWGOH.HELP API"
        
        #Get character_id
        character_alias = characters[0]
        closest_names=difflib.get_close_matches(character_alias.lower(), dict_units.keys(), 3)
        if len(closest_names)<1:
            ret_print_character_stats += \
                'INFO: aucun personnage trouvé pour '+character_alias+'\n'
        else:
            [character_name, character_id]=dict_units[closest_names[0]]
                    
        print("Get guild_data from DB...")
        query ="SELECT players.name, defId, units.nameKey, \
                roster.combatType, rarity, gear, relic_currentTier, \
                ifnull(unitStatId,0), coalesce(sum(unscaledDecimalValue),0) \
                FROM roster \
                LEFT JOIN roster_stats ON roster_stats.roster_id = roster.id \
                JOIN players ON players.id = roster.player_id \
                JOIN units ON units.unit_id = roster.defId \
                WHERE players.guildName = (SELECT guildName FROM players WHERE allyCode='"+txt_allyCode+"') \
                AND defId = '"+character_id+"' \
                AND ("
        for display_stat in list_stats_for_display:
            query += "unitStatId = "+str(display_stat[0])+" OR "
        query += "isnull(unitStatId)) \
                GROUP BY players.name, defId, units.nameKey, roster.combatType, rarity, gear, relic_currentTier, unitStatId \
                ORDER BY players.name, units.nameKey, unitStatId"

        db_stat_data = connect_mysql.get_table(query)
        db_stat_data_mods = []
        list_character_ids=[character_id]
        list_player_names=set([x[0] for x in db_stat_data])
        
        ret_print_character_stats += "Statistiques pour "+character_name+'\n'
    
    else:
        return "ERR: les stats au niveau guilde ne marchent qu'avec un seul perso à la fois"
    
    # Generate dict with statistics
    dict_stats = goutils.create_dict_stats(db_stat_data, db_stat_data_mods)

    #Manage virtual characters
    #This works only with command SPJ, so only one player_name
    if len(dict_virtual_characters)>0 and not ('all' in characters):
        dict_for_crinolo = {"nameKey": player_name, "roster":[]}

        for character_id in dict_virtual_characters:
            roster_element = {}
            if player_name in dict_stats:
                if character_id in dict_stats[player_name]:
                    #character is unlocked, let's get the mods
                    roster_element = dict_stats[player_name][character_id]
                
            roster_element["defId"] = character_id
            roster_element["nameKey"] = dict_virtual_characters[character_id][3]
            roster_element["level"] = 85
            roster_element["equipped"] = []
            roster_element["rarity"] = dict_virtual_characters[character_id][0]
            roster_element["gear"] = dict_virtual_characters[character_id][1]
            if roster_element["gear"] < 13:
                roster_element["relic"] = {"currentTier": 1}
            else:
                roster_element["relic"] = {
                    "currentTier": dict_virtual_characters[character_id][2]+2}
                    
            dict_for_crinolo["roster"].append(roster_element)
            
        dict_from_crinolo = connect_crinolo.add_stats(dict_for_crinolo)
        
        for roster_element in dict_from_crinolo["roster"]:
            base_stats = roster_element["stats"]["base"]
            if "mods" in roster_element["stats"]:
                mods_stats = roster_element["stats"]["mods"]
            else:
                mods_stats = {}
            sum_stats  = {int(k): base_stats.get(k, 0) + mods_stats.get(k, 0) \
                            for k in set(base_stats) | set(mods_stats)}
            
            if not player_name in dict_stats:
                #no roster recovered from the player
                roster_element["combatType"] = 1
                dict_stats[player_name]={roster_element["defId"]: roster_element}
                
            if not roster_element["defId"] in dict_stats[player_name]:
                #roster recovered without this character
                roster_element["combatType"] = 1
                dict_stats[player_name][roster_element["defId"]] = roster_element

            dict_stats[player_name][roster_element["defId"]]["stats"] = sum_stats
        
    # Create all lines before display
    list_print_stats=[]
    for player_name in list_player_names:
        if player_name in dict_stats:
            dict_player = dict_stats[player_name]
        else:
            dict_player={}
        for character_id in list_character_ids:
            if character_id in dict_player:
                character_name = dict_player[character_id]["nameKey"]
                character_rarity = str(dict_player[character_id]["rarity"])+"*"
                character_gear = dict_player[character_id]["gear"]
                if dict_player[character_id]["combatType"] == 1:
                    if character_gear == 13:
                        character_relic = dict_player[character_id]["relic"]["currentTier"]
                        character_gear = "R"+str(character_relic-2)
                    else:
                        character_gear="G"+str(character_gear)
                else: #ship
                    character_gear=''
                character_stats = dict_player[character_id]["stats"]
                
                if compute_guild:
                    line_header = player_name
                else:
                    line_header = character_name
                list_print_stats.append([line_header, character_rarity+character_gear, character_stats])
                        
            else:
                ret_print_character_stats +=  'INFO: ' + character_id+' non trouvé chez '+player_name+'\n'

    if len (list_print_stats)>0:
        # Default sort by character name in case of "all" for characters
        # or by player name if guild statistics
        if 'all' in characters or compute_guild:
            list_print_stats = sorted(list_print_stats, key=lambda x: x[0])
            
        # Sort by specified stat
        for stat in list_stats_for_display:
            if sort_option == stat[3]:
                list_print_stats = sorted(list_print_stats,
                    key=lambda x: -x[2][stat[0]] if stat[0] in x[2] else 0)
        
        ret_print_character_stats += "=====================================\n"
        max_size_char = max([len(x[0]) for x in list_print_stats])
        if compute_guild:
            ret_print_character_stats += ("{0:"+str(max_size_char)+"}: {1:5} ").format("Joueur", "*+G")
            max_size_char = max(max_size_char, len("Joueur"))
        else:
            ret_print_character_stats += ("{0:"+str(max_size_char)+"}: {1:5} ").format("Perso", "*+G")
            max_size_char = max(max_size_char, len("Perso"))
        
        for stat in list_stats_for_display:
            ret_print_character_stats += stat[1]+' '
        ret_print_character_stats += "\n"

        for print_stat_row in list_print_stats:
            ret_print_character_stats += ("{0:"+str(max_size_char)+"}: ").format(print_stat_row[0])
            ret_print_character_stats += ("{0:5} ").format(print_stat_row[1])
            for stat in list_stats_for_display:
                if stat[0] in print_stat_row[2]:
                    stat_value = print_stat_row[2][stat[0]]
                else:
                    stat_value = 0
                if stat[2]:
                    # Percent value
                    ret_print_character_stats += ("{0:"+str(len(stat[1])-1)+".2f}% ").format(stat_value/1e6)
                else:
                    # Flat value
                    ret_print_character_stats += ("{0:"+str(len(stat[1]))+"} ").format(int(stat_value/1e8))
        
            ret_print_character_stats += "\n"

    return ret_print_character_stats

def get_gp_graph(guild_stats, inactive_duration):
	ret_print_gp_graph=''
	dict_gp_clusters={} #key=gp group, value=[nb active, nb inactive]
	for player in guild_stats:
		#print(guild_stats[player])
		gp=guild_stats[player][0]+guild_stats[player][1]
		gp_key=int(gp/500000)/2
		if gp_key in dict_gp_clusters:
			if guild_stats[player][2] < inactive_duration:
				dict_gp_clusters[gp_key][0] = dict_gp_clusters[gp_key][0] + 1
			else:
				dict_gp_clusters[gp_key][1] = dict_gp_clusters[gp_key][1] + 1
		else:
			if guild_stats[player][2] < inactive_duration:
				dict_gp_clusters[gp_key] = [1, 0]
			else:
				dict_gp_clusters[gp_key] = [0, 1]

	#print (dict_gp_clusters)	
	#write line from the top = max bar size
	max_cluster=max(dict_gp_clusters.values(), key=lambda p: p[0]+p[1])
	line_graph=max_cluster[0]+max_cluster[1]
	max_key=max(dict_gp_clusters.keys())
	while line_graph > 0:
		if (line_graph % 5) == 0:
			line_txt="{:02d}".format(line_graph)
		else:
			line_txt='  '
		for gp_key_x2 in range(0, int(max_key*2)+1):
			gp_key=gp_key_x2 / 2
			if gp_key in dict_gp_clusters:
				#print(dict_gp_clusters[gp_key])
				if dict_gp_clusters[gp_key][0] >= line_graph:
					line_txt = line_txt + '    #'
				elif dict_gp_clusters[gp_key][0]+dict_gp_clusters[gp_key][1] >= line_graph:
					line_txt = line_txt + '    .'
				else:
					line_txt = line_txt + '     '
			else:
				line_txt = line_txt + '     '
		ret_print_gp_graph+=line_txt+'\n'
		line_graph=line_graph - 1
	ret_print_gp_graph+='--'+'-----'*int(max(dict_gp_clusters.keys())*2+1)+'\n'

	line_txt='   '
	for gp_key_x2 in range(0, int(max_key*2)+1):
		gp_key=gp_key_x2 / 2
		if int(gp_key)==gp_key:
			line_txt=line_txt+'   '+str(int(gp_key))+' '
		else:
			line_txt=line_txt+'  '+str(gp_key)
	ret_print_gp_graph+=line_txt+'\n'

	line_txt='   '
	for gp_key_x2 in range(0, int(max_key*2)+1):
		gp_key=gp_key_x2 / 2
		if int(gp_key)==gp_key:
			line_txt=line_txt+'  '+str(gp_key+0.5)
		else:
			line_txt=line_txt+'   '+str(int(gp_key+0.5))+' '
	ret_print_gp_graph+=line_txt+'\n'
	
	return ret_print_gp_graph

def get_guild_gp(guild):
	guild_stats={}
	for player in guild['roster']:
		guild_stats[player['name']]=[player['gpChar'], player['gpShip'], 0]
	return guild_stats

def get_gp_distribution(txt_allyCode, inactive_duration, fast_chart):
    ret_get_gp_distribution = ''
    
    #Load or update data for the guild
    if (fast_chart):
        #use only the guild data from the API
        ret, guild = load_guild(txt_allyCode, False)
        if ret != 'OK':
            return "ERR: cannot get guild data from SWGOH.HELP API"

        guild_stats=get_guild_gp(guild)
        guild_name = guild["name"]

        ret_get_gp_distribution = "==GP stats "+guild_name+ "==\n"
    else:
        # Need to load players also to get their lastActivity
        ret, guild = load_guild(txt_allyCode, True)
        if ret != 'OK':
            return "ERR: cannot get guild data from SWGOH.HELP API"
            
        query = "SELECT guildName, allyCode, char_gp, ship_gp, \
                timestampdiff(HOUR, lastActivity, CURRENT_TIMESTAMP) \
                FROM players \
                WHERE guildName = (SELECT guildName FROM players WHERE allyCode = "+txt_allyCode+")"
        guild_db_data = connect_mysql.get_table(query)
        guild_name = guild_db_data[0][0]
        guild_stats = {}
        for line in guild_db_data:
            guild_stats[line[1]] = [line[2], line[3], line[4]]

        ret_get_gp_distribution = '==GP stats '+guild_name+ \
                                '== (. = inactif depuis '+ \
                                str(inactive_duration)+' heures)\n'

    #compute ASCII graphs
    ret_get_gp_distribution += get_gp_graph(guild_stats, inactive_duration)
    
    return ret_get_gp_distribution

def get_farm_cost_from_alias(txt_allyCode, character_alias, target_stats):
    #target_stats=[rarity, gear, relic]
    
    #Recuperation des dernieres donnees sur gdrive
    dict_units = load_config_units()

    #Get full character name
    closest_names=difflib.get_close_matches(character_alias.lower(), dict_units.keys(), 3)
    if len(closest_names)<1:
        return [-1, 'ERREUR: aucun personnage trouvé pour '+character_alias]
    else:
        [character_name, character_id]=dict_units[closest_names[0]]

    #Get data for this player
    if txt_allyCode == '0':
        dict_player = {'roster' : {}}
    else:
        dict_player = load_player(txt_allyCode, False)
        if isinstance(dict_player, str):
            #error wile loading guild data
            return [-1, 'ERREUR: joueur non trouvé pour code allié ' + txt_allyCode]
        
    return get_farm_cost_from_id(dict_player, character_id, target_stats)

def player_journey_progress(txt_allyCode, character_alias):
    #Recuperation des dernieres donnees sur gdrive
    dict_units = load_config_units()

    #Get full character name
    closest_names=difflib.get_close_matches(character_alias.lower(), dict_units.keys(), 3)
    if len(closest_names)<1:
        return [-1, 'ERR: aucun personnage trouvé pour '+character_alias, '', '', []]
    else:
        [character_name, character_id]=dict_units[closest_names[0]]

    if character_id in journey_guide:
        objectifs=journey_guide[character_id]
    else:
        return [-1, 'ERR: guide de voyage inconnu pour '+character_id+'\n'+
                    'Valeurs autorisées : '+str(journey_guide.keys()), '', '', []]

    dict_player = load_player(txt_allyCode, False)
    if isinstance(dict_player, str):
        #error wile loading guild data
        return [-1, 'ERR: joueur non trouvé pour code allié ' + txt_allyCode, '', '', []]
        
    tab_progress_player={}
    for sub_obj in objectifs:
        if sub_obj == 'initial shards':
            continue
        
        tab_progress_player[sub_obj]=[]
        
        for character_subobj in objectifs[sub_obj][1]:
            progress=0
            progress_100=0
            
            if character_subobj[0] in dict_player['roster']:
                # print('DBG: '+character_subobj[0]+' trouvé')
                character_roster = dict_player['roster'][character_subobj[0]]
            else:
                # character not found in player's roster
                # print('DBG: '+character_subobj[0]+' pas trouvé dans '+str(dict_player['roster'].keys()))
                character_roster = {'defId': character_subobj[0],
                                    'rarity': 0,
                                    'gear': 0,
                                    'relic': {'currentTier': 1},
                                    'skills': [],
                                    'gp': 0,
                                    'mods': []}
                
            if character_subobj[1] != -1:
                progress_100=progress_100+1
                progress=progress+min(1, character_roster['rarity']/character_subobj[1])
            if character_subobj[2] != -1:
                progress_100=progress_100+1
                progress=progress+min(1, character_roster['gear']/character_subobj[2])
            if character_subobj[3] != -1:
                progress_100=progress_100+1
                if character_roster['relic']['currentTier'] > 1:
                    progress=progress+min(1, (character_roster['relic']['currentTier']-2)/character_subobj[3])
            if character_subobj[4] != -1:
                for skill in character_roster['skills']:
                    progress_100=progress_100+1
                    if skill['tier'] == skill['tiers']:
                        progress=progress+1
                    else:
                        progress=progress+min(1, skill['tier']/character_subobj[4])
            if character_subobj[5] != -1:
                progress_100=progress_100+1
                progress=progress+min(1, character_roster['gp']/character_subobj[5])
            if character_subobj[6] != -1:
                for mod in character_roster['mods']:
                    progress_100=progress_100+1
                    progress=progress+min(1, mod['pips']/character_subobj[6])
            tab_progress_player[sub_obj].append(progress/progress_100)
            # print('DBG: '+character_roster['defId']+':'+str(progress/progress_100))
            # print('DBG: '+character_roster['defId']+':'+str(tab_progress_player))

    # Then compute the progress for each character who has its own journey guide
    # eg: JKLS progress for journey guide of JMLS
    # TO-DO

    list_progress = []
    total_progress = 0
    total_progress_100 = 0
    for sub_obj in objectifs:
        if sub_obj == 'initial shards':
            continue

        tab_progress_sub_obj=tab_progress_player[sub_obj]
        # print('DBG: '+str(tab_progress_sub_obj))
        min_nb_sub_obj=objectifs[sub_obj][0]
        cur_nb_sub_obj=len(tab_progress_player[sub_obj])
        # print('DBG: '+str(min_nb_sub_obj)+':'+str(cur_nb_sub_obj))
        if cur_nb_sub_obj < min_nb_sub_obj:
            tab_progress_sub_obj = tab_progress_sub_obj + [0]*(min_nb_sub_obj - cur_nb_sub_obj)
        else:
            tab_progress_sub_obj = sorted(tab_progress_sub_obj, reverse=True)[0:min_nb_sub_obj]
        # print('DBG: '+str(tab_progress_sub_obj))
        progress=sum(tab_progress_sub_obj)

        list_progress.append([sub_obj, progress/min_nb_sub_obj, min_nb_sub_obj])
        
        total_progress_100+=min_nb_sub_obj
        total_progress+=progress

    return [total_progress/total_progress_100, '', dict_player['name'], character_name, list_progress]
