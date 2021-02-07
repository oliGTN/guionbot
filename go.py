# -*- coding: utf-8 -*-

from swgohhelp import SWGOHhelp, settings
import sys
import json
import time
import os
import difflib
import math
from functools import reduce
from math import ceil
from connect_gsheets import load_config_bt, load_config_teams, load_config_players, load_config_gt, load_config_counter, load_config_units
import connect_mysql
import goutils
FORCE_CUT_PATTERN = "SPLIT_HERE"

#login password sur https://api.swgoh.help/profile
creds = settings(os.environ['SWGOHAPI_LOGIN'], os.environ['SWGOHAPI_PASSWORD'], '123', 'abc')
client = SWGOHhelp(creds)

#Journey Guide: [minimum required, [[name, stars, gear, relic, capa level, GP, module level, speed], ...]]
journey_guide={}
journey_guide['DARTHREVAN']={}
journey_guide['DARTHREVAN']['Persos']=[5, [['HK47', 7, 10, -1, 8, -1, 5, -1], 
                                        ['CANDEROUSORDO', 7, 10, -1, 8, -1, 5, -1], 
                                        ['CARTHONASI', 7, 10, -1, 8, -1, 5, -1], 
                                        ['BASTILASHANDARK', 7, 10, -1, 8, -1, 5, -1],
                                        ['JUHANI', 7, 10, -1, 8, -1, 5, -1]]]
                                        
journey_guide['JEDIKNIGHTREVAN']={}
journey_guide['JEDIKNIGHTREVAN']['Persos']=[5, [['BASTILASHAN', 7, 9, -1, 8, -1, 5, -1], 
                                        ['JOLEEBINDO', 7, 9, -1, 8, -1, 5, -1], 
                                        ['T3_M4', 7, 9, -1, 8, -1, 5, -1],
                                        ['MISSIONVAO', 7, 9, -1, 8, -1, 5, -1],
                                        ['ZAALBAR', 7, 9, -1, 8, -1, 5, -1]]]
                                        
journey_guide['DARTHMALAK']={}
journey_guide['DARTHMALAK']['Persos']=[12, [['JEDIKNIGHTREVAN', 7, 12, -1, 8, 20000, 6, -1], 
                                        ['BASTILASHAN', 7, 12, -1, 8, 20000, 6, -1],
                                        ['JOLEEBINDO', 7, 12, -1, 8, 20000, 6, -1],
                                        ['T3_M4', 7, 12, -1, 8, 20000, 6, -1],
                                        ['MISSIONVAO', 7, 12, -1, 8, 20000, 6, -1],
                                        ['ZAALBAR', 7, 12, -1, 8, 20000, 6, -1],
                                        ['HK47', 7, 12, -1, 8, 20000, 6, -1],
                                        ['CANDEROUSORDO', 7, 12, -1, 8, 20000, 6, -1],
                                        ['CARTHONASI', 7, 12, -1, 8, 20000, 6, -1],
                                        ['BASTILASHANDARK', 7, 12, -1, 8, 20000, 6, -1],
                                        ['JUHANI', 7, 12, -1, 8, 20000, 6, -1],
                                        ['DARTHREVAN', 7, 12, -1, 8, 20000, 6]]]
journey_guide['DARTHMALAK']['initial shards']=145

journey_guide['GENERALSKYWALKER']={}
journey_guide['GENERALSKYWALKER']['Persos']=[10, [['GENERALKENOBI', 7, 13, 3, 8, 22000, 6, -1], 
                                        ['AHSOKATANO', 7, 13, 3, 8, 22000, 6, -1], 
                                        ['PADMEAMIDALA', 7, 13, 3, 8, 22000, 6, -1], 
                                        ['SHAAKTI', 7, 13, 3, 8, 22000, 6, -1], 
                                        ['ASAJVENTRESS', 7, 13, 3, 8, 22000, 6, -1], 
                                        ['C3POLEGENDARY', 7, 13, 3, 8, 22000, 6, -1],
                                        ['B1BATTLEDROIDV2', 7, 13, 3, 8, 22000, 6, -1], 
                                        ['DROIDEKA', 7, 13, 3, 8, 22000, 6, -1],
                                        ['MAGNAGUARD', 7, 13, 3, 8, 22000, 6, -1], 
                                        ['B2SUPERBATTLEDROID', 7, 13, 3, 8, 22000, 6]]]
journey_guide['GENERALSKYWALKER']['Vaisseau amiral']=[1, [['CAPITALJEDICRUISER', 7, -1, -1, 8, 50000, -1, -1], 
                                        ['CAPITALNEGOCIATOR', 7, -1, -1, 8, 50000, -1]]]
journey_guide['GENERALSKYWALKER']['Eta-2']=[1, [['JEDISTARFIGHTERANAKIN', 7, -1, -1, 8, 50000, -1]]]
journey_guide['GENERALSKYWALKER']['Vaisseaux']=[3, [['JEDISTARFIGHTERANAKIN', 7, -1, -1, 8, 50000, -1, -1],
                                        ['JEDISTARFIGHTERAHSOKATANO', 7, -1, -1, 8, 50000, -1, -1],
                                        ['UMBARANSTARFIGHTER', 7, -1, -1, 8, 50000, -1, -1],
                                        ['ARC170REX', 7, -1, -1, 8, 50000, -1, -1],
                                        ['BLADEOFDORIN', 7, -1, -1, 8, 50000, -1, -1],
                                        ['JEDISTARFIGHTERCONSULAR', 7, -1, -1, 8, 50000, -1, -1],
                                        ['ARC170CLONESERGEANT', 7, -1, -1, 8, 50000, -1, -1],
                                        ['YWINGCLONEWARS', 7, -1, -1, 8, 50000, -1, -1]]]
journey_guide['GENERALSKYWALKER']['initial shards']=145

journey_guide['JEDIKNIGHTLUKE']={}
journey_guide['JEDIKNIGHTLUKE']['Persos']=[9, [['C3POLEGENDARY', 7, 13, 5, 8, -1, 5, -1], 
                                        ['VADER', 7, 13, 5, 8, -1, 5, -1],
                                        ['CHEWBACCALEGENDARY', 7, 13, 5, 8, -1, 5, -1],
                                        ['COMMANDERLUKESKYWALKER', 7, 13, 5, 8, -1, 5, -1],
                                        ['HERMITYODA', 7, 13, 5, 8, -1, 5, -1],
                                        ['ADMINISTRATORLANDO', 7, 13, 5, 8, -1, 5, -1],
                                        ['HOTHLEIA', 7, 13, 5, 8, -1, 5, -1],
                                        ['WAMPA', 7, 13, 5, 8, -1, 5, -1],
                                        ['HOTHHAN', 7, 13, 5, 8, -1, 5, -1]]]
journey_guide['JEDIKNIGHTLUKE']['Vaisseaux']=[2, [['XWINGRED2', 7, -1, -1, 7, 55000, -1, -1], 
                                        ['MILLENNIUMFALCON', 7, -1, -1, 7, 55000, -1, -1]]]
                                        
journey_guide['SUPREMELEADERKYLOREN']={}
journey_guide['SUPREMELEADERKYLOREN']['Persos']=[12, [['KYLORENUNMASKED', 7, 13, 7, 8, -1, 5, -1], 
                                        ['FIRSTORDERTROOPER', 7, 13, 5, 8, -1, 5, -1], 
                                        ['FIRSTORDEROFFICERMALE', 7, 13, 5, 8, -1, 5, -1], 
                                        ['KYLOREN', 7, 13, 7, 8, -1, 5, -1],
                                        ['PHASMA', 7, 13, 5, 8, -1, 5, -1],
                                        ['FIRSTORDEREXECUTIONER', 7, 13, 5, 8, -1, 5, -1],
                                        ['SMUGGLERHAN', 7, 13, 3, 8, -1, 5, -1],
                                        ['FOSITHTROOPER', 7, 13, 5, 8, -1, 5, -1],
                                        ['FIRSTORDERSPECIALFORCESPILOT', 7, 13, 3, 8, -1, 5, -1],
                                        ['GENERALHUX', 7, 13, 5, 8, -1, 5, -1],
                                        ['FIRSTORDERTIEPILOT', 7, 13, 3, 8, -1, 5, -1],
                                        ['EMPERORPALPATINE', 7, 13, 7, 8, -1, 5, -1]]]
journey_guide['SUPREMELEADERKYLOREN']['mships']=[1, [['CAPITALFINALIZER', 5, -1, -1, -1, -1, -1, -1]]]

journey_guide['GRANDADMIRALTHRAWN']={}
journey_guide['GRANDADMIRALTHRAWN']['Phoenix']=[5, [['HERASYNDULLAS3', 7, 9, -1, 7, -1, 5, -1],
                                        ['SABINEWRENS3', 7, 9, -1, 7, -1, 5, -1],
                                        ['CHOPPERS3', 7, 9, -1, 7, -1, 5, -1],
                                        ['EZRABRIDGERS3', 7, 9, -1, 7, -1, 5, -1],
                                        ['ZEBS3', 7, 9, -1, 7, -1, 5, -1],
                                        ['KANANJARRUSS3', 7, 9, -1, 7, -1, 5, -1]]]

journey_guide['SITHPALPATINE']={}
journey_guide['SITHPALPATINE']['Persos']=[14, [['EMPERORPALPATINE', 7, 13, 7, 8, -1, 5], 
                                        ['DARTHVADER', 7, 13, 7, 8, -1, 5], 
                                        ['ROYALGUARD', 7, 13, 3, 8, -1, 5], 
                                        ['ADMIRALPIETT', 7, 13, 5, 8, -1, 5],
                                        ['DIRECTORKRENNIC', 7, 13, 4, 8, -1, 5],
                                        ['DARTHSIDIOUS', 7, 13, 7, 8, -1, 5],
                                        ['DARTHMAUL', 7, 13, 4, 8, -1, 5],
                                        ['COUNTDOOKU', 7, 13, 6, 8, -1, 5],
                                        ['SITHMARAUDER', 7, 13, 7, 8, -1, 5],
                                        ['ANAKINKNIGHT', 7, 13, 7, 8, -1, 5],
                                        ['GRANDADMIRALTHRAWN', 7, 13, 6, 8, -1, 5],
                                        ['VEERS', 7, 13, 3, 8, -1, 5],
                                        ['COLONELSTARCK', 7, 13, 3, 8, -1, 5],
                                        ['GRANDMOFFTARKIN', 7, 13, 3, 8, -1, 5, -1]]]
journey_guide['SITHPALPATINE']['Vaisseaux']=[1, [['TIEBOMBERIMPERIAL', 6, -1, -1, -1, -1, -1, -1]]]

journey_guide['GRANDMASTERLUKE']={}
journey_guide['GRANDMASTERLUKE']['Persos']=[14, [['OLDBENKENOBI', 7, 13, 5, 8, -1, 5, -1], 
                                        ['REYJEDITRAINING', 7, 13, 7, 8, -1, 5, -1], 
                                        ['C3POLEGENDARY', 7, 13, 5, 8, -1, 5, -1], 
                                        ['MONMOTHMA', 7, 13, 5, 8, -1, 5, -1],
                                        ['C3POCHEWBACCA', 7, 13, 5, 8, -1, 5, -1],
                                        ['JEDIKNIGHTLUKE', 7, 13, 7, 8, -1, 5, -1],
                                        ['R2D2_LEGENDARY', 7, 13, 7, 8, -1, 5, -1],
                                        ['HANSOLO', 7, 13, 6, 8, -1, 5, -1],
                                        ['CHEWBACCALEGENDARY', 7, 13, 6, 8, -1, 5, -1],
                                        ['PRINCESSLEIA', 7, 13, 3, 8, -1, 5, -1],
                                        ['HERMITYODA', 7, 13, 5, 8, -1, 5, -1],
                                        ['WEDGEANTILLES', 7, 13, 3, 8, -1, 5, -1],
                                        ['BIGGSDARKLIGHTER', 7, 13, 3, 8, -1, 5, -1],
                                        ['ADMINISTRATORLANDO', 7, 13, 5, 8, -1, 5, -1]]]
journey_guide['GRANDMASTERLUKE']['Vaisseaux']=[1, [['YWINGREBEL', 6, -1, -1, -1, -1, -1, -1]]]

def refresh_cache(nb_minutes_delete, nb_minutes_refresh, refresh_rate_minutes):
    #CLEAN OLD FILES NOT ACCESSED FOR LONG TIME
    #Need to keep KEEPDIR to prevent removal of the directory by GIT
    
    # Get the allyOcdes to be refreshed
    # the query gets all allyCodes form all guilds that have been updated
    # in the latest 7 days, and the player not updated in the last <refresh_rate_minutes> minutes
    query = "SELECT allyCode from players WHERE guildName = ( \
                SELECT name \
                FROM guilds \
                WHERE timestampdiff(DAY, lastUpdated, CURRENT_TIMESTAMP)<=7 \
            ) \
            ORDER BY lastUpdated ASC"
    list_allyCodes = connect_mysql.get_column(query)

    #Compute the amount of players to be refreshed based on global refresh rate
    nb_refresh_players = ceil(
        len(list_allyCodes) / nb_minutes_refresh * refresh_rate_minutes)
    print('Refreshing ' + str(nb_refresh_players) + ' files')

    for allyCode in list_allyCodes[:nb_refresh_players]:
        load_player(str(allyCode), True)

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
    query_result = connect_mysql.get_line("SELECT \
                        (timestampdiff(MINUTE, lastUpdated, CURRENT_TIMESTAMP)<=60), \
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
            return 'ERR: canot fetch guild fo allyCode '+txt_allyCode

    else:
        print ('ERR: client.get_data(\'guild\', '+
                txt_allyCode+') has not returned a list')
        print (client_data)
        return 'ERR: canot fetch guild fo allyCode '+txt_allyCode


    if load_players:
        #Get players and update status from DB
        recent_players = connect_mysql.get_table( "\
            SELECT \
            (timestampdiff(MINUTE, lastUpdated, CURRENT_TIMESTAMP)<=60), \
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
    
    return "OK"

def get_team_line_from_player(dict_player, objectifs, score_type, score_green,
                              score_amber, txt_mode, player_name):
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
            if character_id in dict_player:
                # print('DBG: '+character_id+' trouvé')

                character_nogo = False
                character_obj = dict_char_subobj[character_id]
                i_character = character_obj[0]
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

                #Display
                tab_progress_player[i_subobj][i_character -
                                             1][1] = str(player_rarity)
                if player_gear < 13:
                    tab_progress_player[i_subobj][
                        i_character - 1][1] += '.' + "{:02d}".format(player_gear)
                else:
                    tab_progress_player[i_subobj][
                        i_character - 1][1] += '.R' + str(player_relic)
                tab_progress_player[i_subobj][
                    i_character - 1][1] += '.' + str(player_nb_zetas)

                if score_type == 1:
                    tab_progress_player[i_subobj][
                        i_character - 1][0] = progress / progress_100
                    tab_progress_player[i_subobj][i_character - 1][2] = character_nogo
                elif score_type == 2:
                    tab_progress_player[i_subobj][
                        i_character - 1][0] = progress / progress_100
                    tab_progress_player[i_subobj][i_character - 1][2] = False
                else:  #score_type==3
                    tab_progress_player[i_subobj][i_character - 1][0] = int(
                        player_gp * player_speed / req_speed)
                    tab_progress_player[i_subobj][
                        i_character -
                        1][1] += '.' + "{:03d}".format(player_speed)
                    tab_progress_player[i_subobj][i_character - 1][2] = character_nogo
                # print(tab_progress_player[i_subobj][i_character - 1])

            else:
                # character not found in player's roster
                # print('DBG: '+character_subobj[0]+' pas trouvé dans '+str(dict_player['roster'].keys()))
                dict_player[character_id] = {"rarity": 0,
                                            "gear": 0,
                                            "rarity": 0,
                                            "gear": 0,
                                            "relic_currentTier": 0,
                                            "gp": 0,
                                            "speed": 0,
                                            "zetas": {}}

    #calcul du score global
    score = 0
    score100 = 0
    score_nogo = False
    for i_subobj in range(0, nb_subobjs):
        nb_sub_obj = len(objectifs[i_subobj][2])
        for i_character in range(0, nb_sub_obj):
            tab_progress_sub_obj = tab_progress_player[i_subobj][i_character]
            #print('DBG: '+str(tab_progress_sub_obj))
            #line+=goutils.pad_txt(str(int(tab_progress_sub_obj[0]*100))+'%', 8)
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
                        score_type, score_green, score_amber, txt_mode):
                        
    ret_get_team_progress = {}

    #Recuperation des dernieres donnees sur gdrive
    liste_team_gt, dict_team_gt = load_config_teams()
    
    if not compute_guild:
        #only one player, potentially several teams
        
        #Load or update data for the player
        ret = load_player(txt_allyCode, False)
        if ret != 'OK':
            #error wile loading guild data
            return 'ERREUR: joueur non trouvée pour code allié ' + txt_allyCode
            
    else:
        #Get data for the guild and associated players
        ret = load_guild(txt_allyCode, True)
        if ret != 'OK':
            return "ERR: cannot get guild data from SWGOH.HELP API"

    if 'all' in list_team_names:
        list_team_names = liste_team_gt
        
    #Get player data
    print("Get player data from DB...")
    query = "SELECT players.name, \
            guild_teams.name, \
            guild_team_roster.unit_id, \
            rarity, \
            gear, \
            relic_currentTier, \
            gp, \
            unscaledDecimalValue/1e8 as speed \
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
       
    query += "ORDER BY allyCode, guild_teams.name, guild_team_roster.id"
    
    #print(query)
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
    for team_name in list_team_names:
        if not team_name in dict_team_gt:
            ret_get_team_progress[team_name] = 'ERREUR: team ' + \
                    team_name + ' inconnue. Liste=' + str(liste_team_gt)
        else:
            ret_team = ''
            objectifs = dict_team_gt[team_name]
            #print(objectifs)

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
                    txt_mode, player_name)
                tab_lines.append([score, line, nogo])
                if score >= score_green and not nogo:
                    count_green += 1
                if score >= score_amber and not nogo:
                    count_amber += 1

            #Tri des nogo=False en premier, puis score décroissant
            for score, txt, nogo in sorted(tab_lines,
                                           key=lambda x: (x[2], -x[0])):
                ret_team += txt

            ret_get_team_progress[team_name] = ret_team, count_green, count_amber

    return ret_get_team_progress


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

    #Calcule des meilleures joueurs pour chaque team
    dict_teams = guild_team(allyCode, liste_team_names, 3, -1, -1, True)
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
        
    if not compute_guild:
        #only one player, potentially several characters
        
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
            
        player_name = db_stat_data[0][0]
        list_player_names = [player_name]
        
        ret_print_character_stats += "Statistiques pour "+player_name+'\n'

    elif len(characters) == 1 and characters[0] != "all":
        #Compute stats at guild level, only one character
        
        #Get data for the guild and associated players
        ret = load_guild(txt_allyCode, True)
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
        list_character_ids=[character_id]
        list_player_names=set([x[0] for x in db_stat_data])
        
        ret_print_character_stats += "Statistiques pour "+character_name+'\n'
    
    else:
        return "ERR: les stats au niveau guilde ne marchent qu'avec un seul perso à la fois"
    
    # Generate dict with statistics
    dict_stats = goutils.create_dict_stats(db_stat_data)
    
    # Create all lines before display
    list_print_stats=[]
    for player_name in list_player_names:
        dict_player = dict_stats[player_name]
        for character_id in list_character_ids:
            if character_id in dict_player:
                if dict_player[character_id]["combatType"] == 1:
                    character_name = dict_player[character_id]["nameKey"]
                    character_rarity = str(dict_player[character_id]["rarity"])+"*"
                    character_gear = dict_player[character_id]["gear"]
                    if character_gear == 13:
                        character_relic = dict_player[character_id]["relic"]["currentTier"]
                        character_gear = "R"+str(character_relic-2)
                    else:
                        character_gear="G"+str(character_gear)
                    character_stats = dict_player[character_id]["stats"]
                    
                    if compute_guild:
                        line_header = player_name
                    else:
                        line_header = character_name
                    list_print_stats.append([line_header, character_rarity+character_gear, character_stats])
                        
                else:
                    ret_print_character_stats += 'INFO: ' + dict_player[character_id]['nameKey']+' est un vaisseau, stats non accessibles pour le moment\n'
            
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
            ret_print_character_stats += ("{0:"+str(max_size_char)+"}: {1:5} ").format("Perso", "*+G")
        else:
            ret_print_character_stats += ("{0:"+str(max_size_char)+"}: {1:5} ").format("Joueur", "*+G")
        
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
		guild_stats[player['name']]=[player['gpChar'], player['gpShip'],
                                    (time.time() - player['dict_player']['lastActivity']/1000)/3600]
	return guild_stats

def get_gp_distribution(allyCode, inactive_duration):
    ret_get_gp_distribution = ''
    
    #Load or update data for the guild
    load_guild(txt_allyCode, True)
    if guild == None:
        return "ERR: cannot get guild data from SWGOH.HELP API"
        
    guild_stats=get_guild_gp(guild)

    #compute ASCII graphs
    ret_get_gp_distribution = '==GP stats '+guild['name']+ \
                            '== (. = inactif depuis '+ \
                            str(inactive_duration)+' heures)\n'
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

def get_farm_cost_from_id(dict_player, character_id, target_stats):
    output_message=''

    #target_stats=[rarity, gear, relic]

    equipment_stats = json.load(open('equipment_stats.json', 'r'))
    units_stats = json.load(open('units_stats.json', 'r'))

    character_unlocked=False
    possible_to_unlock=True
    if character_id in dict_player['roster']:
        character = dict_player['roster'][character_id]
        character_unlocked=True
        character_rarity=character['rarity']
        character_is_ship=(character['combatType']==2)
        
        if not character_is_ship:
            character_gear=character['gear']
            if character_gear < 13:
                character_relic = 0
            else:
                character_relic = character['relic']['currentTier'] - 2
            character_eqpt = [(lambda f:f['equipmentId'])(x) for x in character['equipped']]
    
    [energy_per_shard, shards_to_unlock, list_pilots] = units_stats[character_id]['recipe']
    cost_to_unlock=0
    if not character_unlocked:
        #add requirements to unlock
        character_is_ship = units_stats[character_id]['is_ship']
        if energy_per_shard == -1:
            if character_id in journey_guide:
                cost_to_unlock=0
                
                #Mandatory characters
                if 'mandatory' in journey_guide[character_id]:
                    for requirement in journey_guide[character_id]['mandatory']:
                        req_id=requirement[0]
                        req_rarity=requirement[1]
                        req_gear=requirement[2]
                        req_relic=requirement[3]
                        [req_cost, req_msg] = get_farm_cost_from_id(dict_player, req_id, 
                                            [req_rarity, req_gear, req_relic])
                        cost_to_unlock+=req_cost
                        output_message+=req_msg
                    
                #Optional characters
                if 'optional' in journey_guide[character_id]:
                    optional_count = journey_guide[character_id]['optional'][0]
                    list_optional_costs=[] # [[cost, msg, ID], ...]
                    for requirement in journey_guide[character_id]['optional'][1]:
                        req_id=requirement[0]
                        req_rarity=requirement[1]
                        req_gear=requirement[2]
                        req_relic=requirement[3]
                        [req_cost, req_msg] = get_farm_cost_from_id(dict_player, req_id, 
                                            [req_rarity, req_gear, req_relic])
                        list_optional_costs.append([req_cost, req_msg, req_id])
                    
                    list_to_farm = sorted(list_optional_costs)[0:optional_count]
                    for requirement in list_to_farm:
                        cost_to_unlock+=requirement[0]
                        output_message+=requirement[1]
                    
                if 'initial shards' in journey_guide[character_id]:
                    shards_to_unlock = journey_guide[character_id]['initial shards']
                else:
                    # by default journey guide goes up to 7*
                    shards_to_unlock = 330
                
            else:
                possible_to_unlock=False
        else:
            cost_to_unlock = energy_per_shard*shards_to_unlock
            if len(list_pilots)>0:
                for pilot in list_pilots:
                    [req_cost, req_msg] = get_farm_cost_from_id(dict_player, pilot, 
                                        [1, 1, 0])
                    cost_to_unlock+=req_cost
                    output_message+=req_msg
        
        #define stats when unlocked
        character_gear=1
        if shards_to_unlock==10:
            character_rarity=1
        elif shards_to_unlock==25:
            character_rarity=2
        elif shards_to_unlock==50:
            character_rarity=3
        elif shards_to_unlock==80:
            character_rarity=4
        elif shards_to_unlock==145:
            character_rarity=5
        elif shards_to_unlock==230:
            character_rarity=6
        elif shards_to_unlock==330:
            character_rarity=7
        character_eqpt=[]
        
        #Add the character into the roster to simulate cost being paid
        #this serves for characters being used twice for computing cost
        # eg: Mission needed at G9 for Revan then G12 for Malak
        new_char={}
        new_char['defId']=character_id
        new_char['rarity']=target_stats[0]
        if not character_is_ship:
            new_char['gear']=target_stats[1]
            new_char['relic']={}
            if new_char['gear'] < 13:
                new_char['relic']['currentTier'] = 1
            else:
                new_char['relic']['currentTier'] = target_stats[2]+2
            new_char['equipped'] = []
            new_char['combatType'] = 1
        else:
            new_char['combatType'] = 2
            
        dict_player['roster'].append(new_char)
        
    else:
        #Modify the character stats into the roster to simulate cost being paid
        #this serves for characters being used twice for computing cost
        # eg: Mission needed at G9 for Revan then G12 for Malak
        dict_player['roster'].remove(character_id)

        character['rarity']=target_stats[0]
        if not character_is_ship:
            character['gear']=target_stats[1]
            if character['gear'] < 13:
                character['relic']['currentTier'] = 1
            else:
                character['relic']['currentTier'] = target_stats[2]+2
            character['equipped'] = []
            character['combatType'] = 1
        else:
            character['combatType'] = 1
            
        dict_player['roster'][character_id]=character

    
    #remaining cost for rarity / stars
    if target_stats[0] == 1:
        target_shards = 10
    elif target_stats[0] == 2:
        target_shards = 25
    elif target_stats[0] == 3:
        target_shards = 50
    elif target_stats[0] == 4:
        target_shards = 80
    elif target_stats[0] == 5:
        target_shards = 145
    elif target_stats[0] == 6:
        target_shards = 230
    elif target_stats[0] == 7:
        target_shards = 330

    if character_rarity == 1:
        missing_shards = target_shards-10
    elif character_rarity == 2:
        missing_shards = target_shards-25
    elif character_rarity == 3:
        missing_shards = target_shards-50
    elif character_rarity == 4:
        missing_shards = target_shards-80
    elif character_rarity == 5:
        missing_shards = target_shards-145
    elif character_rarity == 6:
        missing_shards = target_shards-230
    elif character_rarity == 7:
        missing_shards = target_shards-330

    if missing_shards>0:    
        cost_missing_shards = missing_shards*energy_per_shard
    else:
        cost_missing_shards=0
    
    cost_missing_character_eqpt=0
    if not character_is_ship:
        #remaining cost for gear
        if character_gear < target_stats[1]:
            #When gear level not reached, define necessary eqpt
            full_character_eqpt = units_stats[character_id]['gear_stats'][character_gear - 1][2]
            missing_character_eqpt = [value for value in full_character_eqpt \
                                        if not (value in character_eqpt)]
            if character_gear<12:
                for future_gear in range(character_gear, target_stats[1]):
                    missing_character_eqpt+=units_stats[character_id]['gear_stats'][future_gear - 1][2]

            #print(missing_character_eqpt)
            cost_missing_character_eqpt=0
            for eqpt in missing_character_eqpt:
                if equipment_stats[eqpt][3]>0:
                    cost_missing_character_eqpt+=equipment_stats[eqpt][3]

    #Display name and current stats
    if character_unlocked:
        output_message+=character_id+' '+str(character_rarity)+'*'
        if not character_is_ship:
            if character_gear<13:
                if len(character_eqpt)>0:
                    output_message+=' G'+str(character_gear)+'+'+str(len(character_eqpt))
                else:
                    output_message+=' G'+str(character_gear)
            else:
                output_message+=' G'+str(character_gear)+'r'+str(character_relic)
    elif not possible_to_unlock:
        output_message+=character_id+': Impossible à débloquer !'
    else:
        output_message+=character_id+': à débloquer'
    
    #Display target stats
    output_message+=' > '+str(target_stats[0])+'*'
    if not character_is_ship:
        if target_stats[1]<13:
            output_message+=' G'+str(target_stats[1])
        else:
            output_message+=' G'+str(target_stats[1])+'r'+str(target_stats[2])
    output_message+='\n'
    
    #Display cost of upgrade
    output_message+='cost_to_unlock: '+str(int(cost_to_unlock))+'\n'
    output_message+='cost_missing_shards: '+str(int(cost_missing_shards))+'\n'
    output_message+='cost_missing_character_eqpt: '+str(int(cost_missing_character_eqpt))+'\n'

    return [cost_to_unlock+cost_missing_shards+cost_missing_character_eqpt, output_message]

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
