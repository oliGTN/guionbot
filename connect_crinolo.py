import requests
import json
import goutils
import os

import data

crinolo_url = 'http://localhost:3223/api?flags=statIDs,unscaled,calcGP,percentVals,gameStyle'

def add_stats(dict_player):
    dict_unitsList = data.get("unitsList_dict.json")

    try:
        r=requests.post(crinolo_url, json=[dict_player])
        goutils.log2('DBG', "crinolo_url: "+crinolo_url)
        goutils.log2('DBG', "r.status_code: "+str(r.status_code))
        if r.status_code != 200:
            goutils.log2('ERR', "Cannot connect to crinolo API")
            goutils.log2('ERR', "status_code: " +str(r.status_code))
            goutils.log2('ERR', "content: " + r.content.decode('utf-8').replace('\n', ' '))
            goutils.log2('ERR', "headers: " + str(r.headers))

            return 1, "Cannot connect to crinolo API", dict_player
            
    except requests.exceptions.ConnectionError as e:
        goutils.log2('ERR', "Cannot connect to Crinolo API")
        goutils.log2('ERR', e)
        return 1, "Cannot connect to crinolo API", dict_player
    
    dict_player_with_stats = json.loads(r.content.decode('utf-8'))[0]
    
    return 0, "", dict_player_with_stats
