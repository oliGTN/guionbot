import requests
import json
import goutils
import os

crinolo_url = 'https://swgoh-stat-calc.glitch.me/api?flags=statIDs,unscaled,calcGP,percentVals,gameStyle'
crinolo_character_list = json.load(open('DATA'+os.path.sep+'crinolo_gameData_light.json', 'r'))

def add_stats(dict_player):
    # Add robustness in case combatType not defined
    # These characters are removed from the stat request
    list_buggy_characters=[]
    list_non_buggy_characters = [x for x in dict_player['roster']]
    for character in dict_player['roster']:
        #if (character['combatType'] == None)\
        if not (character['defId'] in crinolo_character_list):
            goutils.log2('DBG', "character: "+str(character))
            goutils.log2('WAR', "unknown character "+character['defId']+" in crinolo API > removed from stats")
            list_non_buggy_characters.remove(character)
            character['combatType'] = 1
            list_buggy_characters.append(character)

    dict_player['roster'] = list_non_buggy_characters
    
    try:
        r=requests.post(crinolo_url, json=[dict_player])
        if r.status_code != 200:
            goutils.log2('ERR', "Cannot connect to crinolo API")
            goutils.log2('ERR', "status_code: " +str(r.status_code))
            goutils.log2('ERR', "content: " + r.content.decode('utf-8').replace('\n', ' '))
            goutils.log2('ERR', "headers: " + str(r.headers))
            for char in dict_player['roster']:
                goutils.log2('ERR', "dict_player roster contains "+char['defId'])

            return 1, "Cannot connect to crinolo API", dict_player
            
    except requests.exceptions.ConnectionError as e:
        goutils.log2('ERR', "Cannot connect to Crinolo API")
        goutils.log2('ERR', e)
        return 1, "Cannot connect to crinolo API", dict_player
    
    
    dict_player_with_stats = json.loads(r.content.decode('utf-8'))[0]
    
    # Re-put the buggy characters before going to update player
    #  They will have no stats, yet they will appear in the list
    list_buggy_character_ids = ""
    for character in list_buggy_characters:
        dict_player_with_stats['roster'].append(character)
        list_buggy_character_ids += character['defId']
    
    return 0, list_buggy_character_ids, dict_player_with_stats
