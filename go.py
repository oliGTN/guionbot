from swgohhelp import SWGOHhelp, settings
import sys
import json
import time
import os
import difflib
from functools import reduce
from math import ceil
from connect_gsheets import load_config_bt, load_config_teams, load_config_players, load_config_gt, load_config_counter, load_config_units

#login password sur https://api.swgoh.help/profile
creds = settings(os.environ['SWGOHAPI_LOGIN'], os.environ['SWGOHAPI_PASSWORD'], '123', 'abc')
client = SWGOHhelp(creds)
inactive_duration = 36  #hours


def refresh_cache(nb_minutes_delete, nb_minutes_refresh, refresh_rate_minutes):
    #CLEAN OLD FILES NOT ACCESSED FOR LONG TIME
    #Need to keep KEEPDIR to prevent removal of the directory by GIT
    
    #Firets step is to delete old files (eg: more than 24h)
    for filename in os.listdir('CACHE'):
        #print(filename)
        #The fake file KEEPDIR, and the master guild file, cannot be deleted
        if filename != 'KEEPDIR' and filename != 'G'+os.environ['MASTER_GUILD_ALLYCODE']+'.json':
            file_path = 'CACHE' + os.path.sep + filename
            file_stats = os.stat(file_path)

            delta_mtime_sec = time.time() - file_stats.st_mtime
            #print (filename+' (not modified for '+str(int(delta_mtime_sec/60))+' minutes)')
            if (delta_mtime_sec / 60) > nb_minutes_delete:
                print('Remove ' + filename + ' (not accessed for ' +
                      str(int(delta_mtime_sec / 60)) + ' minutes)')
                os.remove(file_path)

    #LOOP through Guild files to recover player allycodes
    #Master guild file cannot be deleted to ensure keeping players updated
    list_allycodes = []
    for filename in os.listdir('CACHE'):
        #print(filename)
        if filename[0] == 'G':
            file_path = 'CACHE' + os.path.sep + filename
            for line in open(file_path).readlines():
                if line[13:21] == 'allyCode':
                    list_allycodes.append(line[24:33])
    #remove duplicates
    list_allycodes = [x for x in set(list_allycodes)]
    #print('DBG: list_allycodes='+str(list_allycodes))

    #Compute the amount of files to be refreshed based on global refresh rate
    nb_refresh_files = ceil(
        len(list_allycodes) / nb_minutes_refresh * refresh_rate_minutes)
    print('Refreshing ' + str(nb_refresh_files) + ' files')

    #LOOP through files to check modification date
    list_filenames_mtime = []
    for filename in os.listdir('CACHE'):
        if filename[:-5] in list_allycodes:
            file_path = 'CACHE' + os.path.sep + filename
            file_stats = os.stat(file_path)
            list_filenames_mtime.append([filename, file_stats.st_mtime])
            list_allycodes.remove(filename[:-5])
    #sort by mtime
    list_filenames_mtime = sorted(list_filenames_mtime, key=lambda x: x[1])
    #print('DBG: list_filenames_mtime='+str(list_filenames_mtime))

    remaining_files_to_refresh = nb_refresh_files
    #Start creating non-existing files
    for allycode in list_allycodes[:remaining_files_to_refresh]:
        #print('DBG: create '+allycode)
        load_player(allycode)
        remaining_files_to_refresh -= 1

    #Then refresh oldest existing files
    for filename_mtime in list_filenames_mtime[:remaining_files_to_refresh]:
        allycode = filename_mtime[0][:-5]
        file_path = 'CACHE' + os.path.sep + filename_mtime[0]
        #print('DBG: refresh '+allycode)
        os.remove(file_path)
        load_player(allycode)
        remaining_files_to_refresh -= 1


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


def load_player(allycode):
    player_json_filename = 'CACHE' + os.path.sep + allycode + '.json'
    if os.path.exists(player_json_filename):
        f = open(player_json_filename, 'r')
        sys.stderr.write('loading cache for ' + str(allycode) + '...')
        ret_player = json.load(f)
        f.close()
    else:
        sys.stderr.write('requesting data for ' + str(allycode) + '...')
        player_data = client.get_data('player', allycode)
        if isinstance(player_data, list):
            if len(player_data) > 0:
                if len(player_data) > 1:
                    print ('WAR: client.get_data(\'player\', '+allycode+
                            ') has returned a list of size '+str(len(player_data)))
                            
                ret_player = player_data[0]
                f = open(player_json_filename, 'w')
                f.write(json.dumps(ret_player, indent=4, sort_keys=True))
                f.close()
            else:
                print ('ERR: client.get_data(\'player\', '+allycode+
                        ') has returned an empty list')
                return None
        else:
            print ('ERR: client.get_data(\'player\', '+
                    allycode+') has not returned a list')
            return None

    sys.stderr.write(' ' + ret_player['name'] + '\n')
    return ret_player

def load_guild(allycode, load_players):
    is_error = False

    #rechargement systématique des infos de guilde (liste des membres)
    sys.stderr.write('>Requesting guild data for allycode ' + allycode +
                     '...\n')
    client_data = client.get_data('guild', allycode)
    if isinstance(client_data, dict):
        #error code
        ret_guild = str(client)
        sys.stderr.write('ERR: ' + ret_guild + '\n')
        is_error = True
    else:  #list
        ret_guild = client_data[0]
        f = open('CACHE' + os.path.sep + 'G' + allycode + '.json', 'w')
        f.write(json.dumps(ret_guild, indent=4, sort_keys=True))
        sys.stderr.write('Guild found: ' + ret_guild['name'] + '\n')
        f.close()

    if load_players and not is_error:
        #add player data after saving the guild in json
        total_players = len(ret_guild['roster'])
        sys.stderr.write('Total players in guild: ' + str(total_players) +
                         '\n')
        i_player = 0
        for player in ret_guild['roster']:
            i_player = i_player + 1
            sys.stderr.write(str(i_player) + ': ')
            player['dict_player'] = load_player(str(player['allyCode']))

    return ret_guild


##############################################################
# Function: pad_txt
# Parameters: txt (string) > texte à modifier
#             size (intereger) > taille cible pour le texte
# Purpose: ajoute des espaces pour atteindre la taille souhaitée
# Output: ret_pad_txt (string) = txt avec des espaces au bout
##############################################################
def pad_txt(txt, size):
    if len(txt) < size:
        ret_pad_txt = txt + ' ' * (size - len(txt))
    else:
        ret_pad_txt = txt[:size]

    return ret_pad_txt


##############################################################
# Function: pad_txt2
# Parameters: txt (string) > texte à modifier
# Purpose: ajoute des espaces pour atteindre la taille souhaitée
#          dans un affichae Discord où les caractères n'ont pas la même taille
#          Le texte est mis à la taille la plus large possible pour un texte de ce nombre de caractères (cas pire)
# Output: ret_pad_txt (string) = txt avec des espaces au bout
##############################################################
def pad_txt2(txt):
    #pixels mesurés en entrant 20 fois le caractère entre 2 "|"
    size_chars = {}
    size_chars['0'] = 12.3
    size_chars['1'] = 7.1
    size_chars['2'] = 10.7
    size_chars['3'] = 10.5
    size_chars['4'] = 11.9
    size_chars['5'] = 10.6
    size_chars['6'] = 11.4
    size_chars['7'] = 10.6
    size_chars['8'] = 11.4
    size_chars['9'] = 11.4
    size_chars[' '] = 4.5
    size_chars['R'] = 11.3
    size_chars['I'] = 5.3
    size_chars['.'] = 4.4
    padding_char = ' '

    size_txt = 0
    nb_sizeable_chars = 0
    for c in size_chars:
        size_txt += txt.count(c) * size_chars[c]
        nb_sizeable_chars += txt.count(c)
        #print ('DBG: c='+c+' size_txt='+str(size_txt)+' nb_sizeable_chars='+str(nb_sizeable_chars))

    max_size = nb_sizeable_chars * max(size_chars.values())
    nb_padding = round((max_size - size_txt) / size_chars[padding_char])
    #print('DBG: max_size='+str(max_size)+'size='+str(size_txt)+' nb_padding='+str(nb_padding))
    ret_pad_txt = txt + padding_char * nb_padding
    #print('DBG: x'+txt+'x > x'+ret_pad_txt+'x')

    return ret_pad_txt


def get_team_line_from_player(dict_player, objectifs, score_type, score_green,
                              score_amber, txt_mode, dict_player_discord):
    #score_type :
    #   1 : de 0 à 100% en fonction de [étoiles, gear, zetas].
    #   2 : score = (2^^gear + 2^^relic)*vitesse > non-utilisé dans les commandes
    #   3 : score = gp*vitesse/vitesse_requise
    #   * : Affichage d'une icône verte (100%), orange (>=80%) ou rouge

    line = ''
    #print('DBG: get_team_line_from_player '+dict_player['name'])
    nb_levels = len(objectifs)

    #INIT tableau des resultats
    tab_progress_player = [[] for i in range(nb_levels)]
    for i_level in range(0, nb_levels):
        nb_sub_obj = len(objectifs[i_level][2])
        if score_type == 1:
            tab_progress_player[i_level] = [[0, '.     ', True]
                                            for i in range(nb_sub_obj)]
        elif score_type == 2:
            tab_progress_player[i_level] = [[0, '.         ', True]
                                            for i in range(nb_sub_obj)]
        else:  #score_type==3
            tab_progress_player[i_level] = [[0, '.         ', True]
                                            for i in range(nb_sub_obj)]

    #boucle sur les persos du joueur
    for character in dict_player['roster']:
        for i_level in range(0, nb_levels):
            dict_perso_objectif = objectifs[i_level][2]

            progress = 0
            progress_100 = 0
            #print(character['nameKey'])
            #print(dict_perso_objectif)
            if character['nameKey'] in dict_perso_objectif:
                character_nogo = False

                perso = character['nameKey']
                i_sub_obj = dict_perso_objectif[perso][0]
                #print(dict_perso_objectif[perso])

                #Etoiles
                req_rarity_min = dict_perso_objectif[perso][1]
                req_rarity_reco = dict_perso_objectif[perso][3]
                player_rarity = character['rarity']
                progress_100 = progress_100 + 1
                progress = progress + min(1, player_rarity / req_rarity_reco)
                if player_rarity < req_rarity_min:
                    character_nogo = True

                #Gear
                req_gear_min = dict_perso_objectif[perso][2]
                req_gear_reco = dict_perso_objectif[perso][4]
                player_gear = character['gear']
                progress_100 = progress_100 + 1
                progress = progress + min(1, player_gear / req_gear_reco)
                if player_gear < req_gear_min:
                    character_nogo = True

                if player_gear < 13:
                    player_relic = 0
                else:
                    player_relic = character['relic']['currentTier'] - 2

                #Zetas
                req_zetas = dict_perso_objectif[perso][5]
                player_nb_zetas = 0
                progress_100 += len(req_zetas)
                for skill in character['skills']:
                    if skill['nameKey'] in req_zetas:
                        if skill['tier'] == 8:
                            player_nb_zetas += 1
                            progress += 1
                if player_nb_zetas < len(req_zetas):
                    character_nogo = True

                #Vitesse (optionnel)
                player_speed, player_potency = get_character_stats(character)
                req_speed = dict_perso_objectif[perso][6]
                if req_speed != '':
                    progress_100 = progress_100 + 1
                    progress = progress + min(1, player_speed / req_speed)
                else:
                    req_speed = player_speed

                player_gp = character['gp']

                tab_progress_player[i_level][i_sub_obj -
                                             1][1] = str(player_rarity)
                if player_gear < 13:
                    tab_progress_player[i_level][
                        i_sub_obj - 1][1] += '.' + "{:02d}".format(player_gear)
                else:
                    tab_progress_player[i_level][
                        i_sub_obj - 1][1] += '.R' + str(player_relic)
                tab_progress_player[i_level][
                    i_sub_obj - 1][1] += '.' + str(player_nb_zetas)

                if score_type == 1:
                    tab_progress_player[i_level][
                        i_sub_obj - 1][0] = progress / progress_100
                elif score_type == 2:
                    tab_progress_player[i_level][i_sub_obj - 1][0] = (
                        2**player_gear + 2**player_relic) * player_speed
                    tab_progress_player[i_level][
                        i_sub_obj -
                        1][1] += '.' + "{:03d}".format(player_speed)
                else:  #score_type==3
                    tab_progress_player[i_level][i_sub_obj - 1][0] = int(
                        player_gp * player_speed / req_speed)
                    tab_progress_player[i_level][
                        i_sub_obj -
                        1][1] += '.' + "{:03d}".format(player_speed)
                tab_progress_player[i_level][i_sub_obj - 1][2] = character_nogo

    #calcul du score global
    score = 0
    score100 = 0
    score_nogo = False
    for i_level in range(0, nb_levels):
        nb_sub_obj = len(objectifs[i_level][2])
        for i_sub_obj in range(0, nb_sub_obj):
            tab_progress_sub_obj = tab_progress_player[i_level][i_sub_obj]
            #print('DBG: '+str(tab_progress_sub_obj))
            #line+=pad_txt(str(int(tab_progress_sub_obj[0]*100))+'%', 8)
            if not tab_progress_sub_obj[2]:
                if txt_mode:
                    line += tab_progress_sub_obj[1] + '|'
                else:
                    line += '**' + pad_txt2(tab_progress_sub_obj[1]) + '**|'
            else:
                if txt_mode:
                    line += tab_progress_sub_obj[1] + '|'
                else:
                    line += pad_txt2(tab_progress_sub_obj[1]) + '|'

        min_perso = objectifs[i_level][1]
        #print('DBG: '+str(tab_progress_player[i_level]))

        #Extraction des scores pour les persos non-exclus
        tab_score_player_values = [(lambda f: (f[0] * (not f[2])))(x)
                                   for x in tab_progress_player[i_level]]
        score += sum(sorted(tab_score_player_values)[-min_perso:])
        score100 += min_perso

        if 0.0 in sorted(tab_score_player_values)[-min_perso:]:
            score_nogo = True

    #pourcentage sur la moyenne
    if score_type == 1:
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

    #Affichage des pseudos IG ou Discord - ON HOLD
    # if dict_player['name'] in dict_player_discord:
        # if txt_mode:  # mode texte, pas de @ discord
            # line += '|' + dict_player['name'] + '\n'
        # else:
            # line += '|' + dict_player_discord[dict_player['name']][2] + '\n'
    # else:  #joueur non-défini dans gsheets
        # line += '|' + dict_player['name'] + '\n'

    # Display the IG name only, as @mentions only pollute discord
    line += '|' + dict_player['name'] + '\n'

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
                    perso_zetas = objectifs[i_level][2][perso][5]
                    entete += '**' + objectifs[i_level][0][0] + str(
                        i_sub_obj + 1) + '**: ' + perso + ' (' + str(
                            perso_rarity_min) + 'G' + str(
                                perso_gear_min) + ' à ' + str(
                                    perso_rarity_reco) + 'G' + str(
                                        perso_gear_reco) + ', zetas=' + str(
                                            perso_zetas) + ')\n'

    #ligne d'entete
    entete += '\n'
    for i_level in range(0, nb_levels):
        nb_sub_obj = len(objectifs[i_level][2])
        #print('DBG: nb_sub_obj='+str(nb_sub_obj))
        for i_sub_obj in range(0, nb_sub_obj):
            #print('DBG:'+str(objectifs[i_level][0][0]+str(i_sub_obj)))
            if score_type == 1:
                nom_sub_obj = pad_txt(
                    objectifs[i_level][0][0] + str(i_sub_obj + 1), 6)
            elif score_type == 2:
                nom_sub_obj = pad_txt(
                    objectifs[i_level][0][0] + str(i_sub_obj + 1), 10)
            else:
                nom_sub_obj = pad_txt(
                    objectifs[i_level][0][0] + str(i_sub_obj + 1), 10)
            if txt_mode:
                entete += nom_sub_obj + '|'
            else:
                entete += pad_txt2(nom_sub_obj) + '|'

    entete += 'GLOB|Joueur\n'

    return entete


def guild_team(txt_allycode, list_team_names, score_type, score_green,
               score_amber, txt_mode):
    ret_guild_team = {}

    #Recuperation des dernieres donnees sur gdrive
    liste_team_gt, dict_team_gt = load_config_teams()
    dict_player_discord = load_config_players()[0]

    #Get data for my guild
    guild = load_guild(txt_allycode, True)
    if isinstance(guild, str):
        #error wile loading guild data
        return 'ERREUR: guilde non trouvée pour code allié ' + txt_allycode

    if 'all' in list_team_names:
        list_team_names = liste_team_gt

    for team_name in list_team_names:
        ret_team = ''
        if not team_name in dict_team_gt:
            ret_guild_team[
                team_name] = 'ERREUR: team ' + team_name + ' inconnue. Liste=' + str(
                    liste_team_gt), 0, 0
            #print(ret_guild_team[team_name][0])
        else:
            objectifs = dict_team_gt[team_name]
            #print(objectifs)

            if len(list_team_names) == 1:
                ret_team += get_team_entete(team_name, objectifs, score_type,
                                            txt_mode)
            else:
                ret_team += 'Team ' + team_name + '\n'

            #resultats par joueur
            tab_lines = []
            count_green = 0
            count_amber = 0
            for player in guild['roster']:
                score, line, nogo = get_team_line_from_player(
                    player['dict_player'], objectifs, score_type, score_green,
                    score_amber, txt_mode, dict_player_discord)
                tab_lines.append([score, line, nogo])
                if score >= score_green and not nogo:
                    count_green += 1
                if score >= score_amber and not nogo:
                    count_amber += 1

            #Tri des nogo=False en premier, puis score décroissant
            for score, txt, nogo in sorted(tab_lines,
                                           key=lambda x: (x[2], -x[0])):
                ret_team += txt

            ret_guild_team[team_name] = ret_team, count_green, count_amber

    return ret_guild_team


def player_team(txt_allycode, list_team_names, score_type, score_green,
                score_amber, txt_mode):
    ret_player_team = {}

    #Recuperation des dernieres donnees sur gdrive
    liste_team_gt, dict_team_gt = load_config_teams()
    dict_player_discord = load_config_players()[0]

    #Get data for my guild
    dict_player = load_player(txt_allycode)
    if isinstance(dict_player, str):
        #error wile loading guild data
        return 'ERREUR: joueur non trouvée pour code allié ' + txt_allycode

    if 'all' in list_team_names:
        list_team_names = liste_team_gt

    for team_name in list_team_names:
        ret_team = ''
        if not team_name in dict_team_gt:
            ret_player_team[
                team_name] = 'ERREUR: team ' + team_name + ' inconnue. Liste=' + str(
                    liste_team_gt)
        else:
            objectifs = dict_team_gt[team_name]
            #print(objectifs)

            if len(list_team_names) == 1:
                ret_team += get_team_entete(team_name, objectifs, score_type,
                                            txt_mode)
            else:
                ret_team += 'Team ' + team_name + '\n'

            #resultats par joueur
            score, line, nogo = get_team_line_from_player(
                dict_player, objectifs, score_type, score_green, score_amber,
                txt_mode, dict_player_discord)
            ret_team += line

            ret_player_team[team_name] = ret_team

    return ret_player_team


##############################################################
# Function: split_txt
# Parameters: txt (string) > long texte à couper en morceaux
#             max_size (int) > taille max d'un morceau
# Purpose: découpe un long texte en morceaux de taille maximale donnée
#          en coupant des lignes entières (caractère '\n')
#          Cette fonction est utilisée pour afficher de grands textes dans Discord
# Output: tableau de texte de taille acceptable
##############################################################
FORCE_CUT_PATTERN = "SPLIT_HERE"


def split_txt(txt, max_size):
    ret_split_txt = []
    remaining_txt = txt
    while len(txt) > max_size:
        force_split = txt.rfind(FORCE_CUT_PATTERN, 0, max_size)
        if force_split != -1:
            ret_split_txt.append(txt[:force_split])
            txt = txt[force_split + len(FORCE_CUT_PATTERN):]
            continue

        last_cr = -1
        last_cr = txt.rfind("\n", 0, max_size)
        if last_cr == -1:
            ret_split_txt.append(txt[-3] + '...')
            txt = ''
        else:
            ret_split_txt.append(txt[:last_cr])
            txt = txt[last_cr + 1:]
    ret_split_txt.append(txt)

    return ret_split_txt


##############################################################
# Function: get_character_stats
# Parameters: dict_character > dictionaire tel que renvoyé par swgoh.help API (voir dans le json)
# Purpose: renvoie la vitesse et le pouvoir en fonction du gear, des équipements et des mods
# Output: [total_speed (integer), total_potency (float)]
##############################################################
def get_character_stats(dict_character):
    equipment_stats = json.load(open('equipment_stats.json', 'r'))
    units_stats = json.load(open('units_stats.json', 'r'))

    #print('==============\n'+dict_character['nameKey'])
    base_speed = units_stats[dict_character['defId']][dict_character['gear'] - 1][0]
    base_potency = units_stats[dict_character['defId']][dict_character['gear'] - 1][1]
    #print('base: '+str(base_speed)+'/'+str(base_potency))

    eqpt_speed = 0
    eqpt_potency = 0
    for eqpt in dict_character['equipped']:
        eqpt_speed += equipment_stats[eqpt['equipmentId']][0]
        eqpt_potency += equipment_stats[eqpt['equipmentId']][1]
        #print('eqpt '+str(eqpt_speed)+'/'+str(eqpt_potency))

    #Constants
    SPEED_STAT_ID = 5
    SPEED_MOD_SET = 4
    POTENCY_STAT_ID = 17
    POTENCY_MOD_SET = 7
    
    #Compute stats
    total_speed_mods = 0
    nb_speed_mods_level15 = 0
    mod_speed = 0
    total_potency_mods = 0
    nb_potency_mods_level15 = 0
    mod_potency = 0
    for mod in dict_character['mods']:
        #print(mod)
        if mod['set'] == SPEED_MOD_SET:
            total_speed_mods += 1
            if mod['level'] == 15:
                nb_speed_mods_level15 += 1               
        elif mod['set'] == POTENCY_MOD_SET:
            total_potency_mods += 1
            if mod['level'] == 15:
                nb_potency_mods_level15 += 1

        if mod['primaryStat']['unitStat'] == SPEED_STAT_ID:
            mod_speed += mod['primaryStat']['value']
        elif mod['primaryStat']['unitStat'] == POTENCY_STAT_ID:
            mod_potency += mod['primaryStat']['value']/100
            #print('primary mod potency: '+str(mod_potency))

        for secondary in mod['secondaryStat']:
            if secondary['unitStat'] == SPEED_STAT_ID:
                mod_speed += secondary['value']
            elif secondary['unitStat'] == POTENCY_STAT_ID:
                mod_potency += secondary['value']/100
                #print('sec mod potency: '+str(mod_potency))
 
    #Bonus on speed mods (groups of 4)
    if total_speed_mods < 4:
        total_speed = base_speed + eqpt_speed + mod_speed
    else:
        if nb_speed_mods_level15 < 4:
            total_speed = int(base_speed * 1.05) + eqpt_speed + mod_speed
        else:
            total_speed = int(base_speed * 1.10) + eqpt_speed + mod_speed

    #Bonus on potency mods (groups of 2)
    if total_potency_mods < 2:
        total_potency = base_potency + eqpt_potency + mod_potency
    elif total_potency_mods < 4:
        if nb_potency_mods_level15 < 2:
            total_potency = base_potency + 0.075 + eqpt_potency + mod_potency
        else:
            total_potency = base_potency + .15 + eqpt_potency + mod_potency
    elif total_potency_mods < 6:
        if nb_potency_mods_level15 < 2:
            total_potency = base_potency + 0.075 + 0.075 + eqpt_potency + mod_potency
        elif nb_potency_mods_level15 < 4:
            total_potency = base_potency + 0.075 + 0.15 + eqpt_potency + mod_potency
        else:
            total_potency = base_potency + 0.15 + 0.15 + eqpt_potency + mod_potency
    else: #total_potency_mods == 6
        if nb_potency_mods_level15 < 2:
            total_potency = base_potency + 0.075 + 0.075 + 0.075 + eqpt_potency + mod_potency
        elif nb_potency_mods_level15 < 4:
            total_potency = base_potency + 0.075 + 0.075 + 0.15 + eqpt_potency + mod_potency
        elif nb_potency_mods_level15 < 6:
            total_potency = base_potency + 0.075 + 0.15 + 0.15 + eqpt_potency + mod_potency
        else:
            total_potency = base_potency + 0.15 + 0.15 + 0.15 + eqpt_potency + mod_potency

    return total_speed, int(10000*total_potency)/100


def assign_gt(allycode, txt_mode):
    ret_assign_gt = ''

    dict_players = load_config_players()[0]

    liste_territoires = load_config_gt(
    )  # index=priorité-1, value=[territoire, [[team, nombre, score]...]]
    liste_team_names = []
    for territoire in liste_territoires:
        for team in territoire[1]:
            liste_team_names.append(team[0])
    liste_team_names = [x for x in set(liste_team_names)]
    #print(liste_team_names)

    #Calcule des meilleures joueurs pour chaque team
    dict_teams = guild_team(allycode, liste_team_names, 3, -1, -1, True)
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


def guild_counter_score(txt_allycode):
    ret_guild_counter_score = f"""
*Rec = Niveau recommandé / Min = Niveau minimum*
*w/o TW Def = Idem en enlevant les équipes placées en défense d'une TW*
*L'intérêt absolu mesure le nombre de fois que l'équipe X intervient en tant qu'équipe de contre*
{FORCE_CUT_PATTERN}
"""

    list_counter_teams = load_config_counter()
    list_needed_teams = set().union(*[(lambda x: x[1])(x)
                                      for x in list_counter_teams])
    dict_needed_teams = guild_team(txt_allycode, list_needed_teams, 1, 100, 80,
                                   True)
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

def print_character_stats(characters, txt_allycode):
    ret_print_character_stats = ''

    #Recuperation des dernieres donnees sur gdrive
    dict_units = load_config_units()

    #Get data for this player
    dict_player = load_player(txt_allycode)
    if isinstance(dict_player, str):
        #error wile loading guild data
        return 'ERREUR: joueur non trouvé pour code allié ' + txt_allycode
    else:
        ret_print_character_stats += "Statistiques pour "+dict_player['name']
        
    #manage sorting options
    sort_option='name'
    if characters[0] == '-v':
        sort_option = 'speed'
        characters = characters[1:]
    elif characters[0] == '-p':
        sort_option = 'potency'
        characters = characters[1:]
    
    list_print_stats=[]
    #Manage request for all characters
    if 'all' in characters:
        for character in dict_player['roster']:
            if character['combatType'] == 1 and character['level'] >= 50:
                speed, potency = get_character_stats(character)
                list_print_stats.append([speed, potency, character['nameKey']])
    else:
        list_character_names=[]
        for character_alias in characters:
            #Get full character name
            closest_names=difflib.get_close_matches(character_alias.lower(), dict_units.keys(), 3)
            if len(closest_names)<1:
                ret_print_character_stats += 'INFO: aucun personnage trouvé pour '+character_alias+'\n'
            else:
                list_character_names.append(dict_units[closest_names[0]])

        set_character_names = set(list_character_names)
        for character in dict_player['roster']:
            if character['nameKey'] in set_character_names:
                if character['combatType'] == 1:
                    speed, potency = get_character_stats(character)
                    list_print_stats.append([speed, potency, character['nameKey']])
                    list_character_names.remove(character['nameKey'])
                else:
                    ret_print_character_stats += 'INFO:' + character['nameKey']+' est un vaisseau, stats non accessibles pour le moment\n'
        
        for character_name in list_character_names:
            ret_print_character_stats +=  'INFO:' + character_name+' non trouvé chez '+txt_allycode+'\n'
    
    #Sort by speed then display
    if sort_option == 'speed':
        list_print_stats = sorted(list_print_stats, key=lambda x: -x[0])
    elif sort_option == 'potency':
        list_print_stats = sorted(list_print_stats, key=lambda x: -x[1])
    else: # by name
        list_print_stats = sorted(list_print_stats, key=lambda x: x[2])
        
    ret_print_character_stats += """
=====================================
{0:30}: {1:3} {2:7}""".format("Perso", "Vit", "Pouvoir")
    for print_stat_row in list_print_stats:
        ret_print_character_stats += "\n{0:30.30}: {1:3} {2:6.2f}%".format(
                                print_stat_row[2],
                                print_stat_row[0],
                                print_stat_row[1])
    
    return ret_print_character_stats

########### MAIN (DEBUG uniquement, à commenter avant mise en service)#########
# me = '189341793'
# ret= guild_team(me, ['GEO-WAT'], 2, 100,80, True)
# for a in ret:
    # print(ret[a][0])