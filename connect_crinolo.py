import requests
import json
import goutils
import os

import data

crinolo_url = 'http://localhost:3223/api?flags='
default_url_options = 'statIDs,unscaled,calcGP,gameStyle'
base_options = 'statIDs,unscaled,calcGP,withoutModCalc'

def add_stats(dict_player):
    return add_stats_with_options(dict_player, default_url_options)

def add_base_stats(dict_player):
    ec, et, d_stats_base = add_stats_with_options(dict_player, base_options)
    if ec!=0:
        return ec, et, None

    d_stats_base_dict = goutils.roster_from_list_to_dict(d_stats_base)
    new_unit_list = []
    for unit in dict_player["rosterUnit"]:
        unit_id = unit["definitionId"].split(":")[0]
        base_stats = d_stats_base_dict["rosterUnit"][unit_id]["stats"]
        for stat_type in ["base", "gear"]:
            if stat_type in base_stats:
                unit["stats"][stat_type] = base_stats[stat_type]
        new_unit_list.append(unit)

    dict_player["rosterUnit"] = new_unit_list

    return 0, "", dict_player


def add_stats_with_options(dict_player, url_options):
    dict_unitsList = data.get("unitsList_dict.json")

    try:
        r=requests.post(crinolo_url+url_options, json=[dict_player])
        goutils.log2('DBG', "crinolo_url: "+crinolo_url+url_options)
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
