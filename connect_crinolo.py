import requests
import json

crinolo_url = 'https://swgoh-stat-calc.glitch.me/api?flags=statIDs,unscaled'

def add_stats(dict_player):
    r=requests.post(crinolo_url, json=[dict_player])
    if r.status_code != 200:
        print('ERR: Cannot connect to crinolo API')
        return  dict_player
    
    return json.loads(r.content.decode('utf-8'))[0]
