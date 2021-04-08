import requests
import json

crinolo_url = 'https://swgoh-stat-calc.glitch.me/api?flags=statIDs,unscaled'

def add_stats(dict_player):
    # Add robustness in case combatType not defined
    # These characters are removed from the stat request
    list_buggy_characters=[]
    for character in dict_player['roster']:
        if character['combatType'] == None:
            print("WAR: unknown combatType for "+character['defId']+" > assume =1")
            character['combatType'] = 1
            list_buggy_characters.append(character)
            dict_player['roster'].remove(character)

    r=requests.post(crinolo_url, json=[dict_player])
    if r.status_code != 200:
        print('ERR: Cannot connect to crinolo API')
        print(r)
        return dict_player
    
    dict_player_with_stats = json.loads(r.content.decode('utf-8'))[0]
    
    # Re-put the buggy characters before going to update player
    for character in list_buggy_characters:
        dict_player_with_stats['roster'].append(character)
    
    return dict_player_with_stats
