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

    allyCode = dict_player["allyCode"]
    for character_id in dict_player["rosterUnit"]:
        if character_id!='CAPTAINREX':
            continue
        character = dict_player["rosterUnit"][character_id]

        equipment = [False, False, False, False, False, False]
        if "equipment" in character:
            for eqpt in character["equipment"]:
                equipment[eqpt["slot"]] = True
        print(equipment)
        eqpt_txt = ""
        for i in range(6):
            if equipment[i]:
                eqpt_txt+="1"
            else:
                eqpt_txt+="0"

        query = "UPDATE roster SET equipment='"+eqpt_txt+"' "

        query += "WHERE allyCode="+str(allyCode)+" "
        query += "AND defId='"+character_id+"'"
        print(query)
        connect_mysql.simple_execute(query)
