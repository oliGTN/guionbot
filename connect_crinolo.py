import requests
import json
import goutils
import os

import data

crinolo_url = 'https://swgoh-stat-calc.glitch.me/api?flags=statIDs,unscaled,calcGP,percentVals,gameStyle'
crinolo_url = 'http://localhost:8000/api?flags=statIDs,unscaled,calcGP,percentVals,gameStyle'

def add_stats(dict_player):
    dict_unitsList = data.get("unitsList_dict.json")

    # Add robustness in case combatType not defined
    for character in dict_player['roster']:
        if character['combatType'] == None:
            char_id = character['defId']
            if char_id in dict_unitsList:
                character['combatType'] = dict_unitsList[char_id]['combatType']
            else:
                goutils.log2('DBG', char_id+" >> combatType forced to 1")
                character['combatType'] = 1
    
    try:
        r=requests.post(crinolo_url, json=[dict_player])
        goutils.log2('DBG', "crinolo_url: "+crinolo_url)
        goutils.log2('DBG', "r.status_code: "+str(r.status_code))
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
    
    return 0, "", dict_player_with_stats
