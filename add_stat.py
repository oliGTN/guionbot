import sys
import json
import connect_mysql
import connect_crinolo
import goutils

list_json_files = sys.argv[1:]
for filename in list_json_files:
    print(filename)
    json_file = open(filename, 'r')
    dict_player = json.load(json_file)
    json_file.close()

    dict_player = goutils.roster_from_dict_to_list(dict_player)
    dict_player = connect_crinolo.add_stats(dict_player)
    dict_player = goutils.roster_from_list_to_dict(dict_player)

    fjson = open(filename, 'w')
    fjson.write(json.dumps(dict_player, sort_keys=True, indent=4))
    fjson.close()

    allyCode = dict_player["allyCode"]
    for character_id in dict_player["roster"]:
        character = dict_player["roster"][character_id]
        query = "UPDATE roster SET "

        for stat_type in ['base', 'gear', 'mods', 'crew']:
            if stat_type in character["stats"]:
                del character["stats"][stat_type]

        stat_type = "final"
        if stat_type in character["stats"]:
            for stat_id in ['1', '5', '6', '7', '14', '15', '16', '17', '18', '28']:
                if stat_id in character["stats"][stat_type]:
                    stat_value = character["stats"][stat_type][stat_id]
                    query += "stat"+stat_id+"="+str(stat_value)+","
        query = query[:-1]+" "
        query += "WHERE allyCode="+str(allyCode)+" "
        query += "AND defId='"+character_id+"'"
        #print(query)
        connect_mysql.simple_execute(query)
