import json
import os

localization_path = "../warstats/LocalizationBundle"
for filename in os.listdir(localization_path):
    lang = filename[4:10]
    dict_lang = {}
    f = open(localization_path+"/"+filename, 'r')
    for line in f.readlines():
        if line[0] == "#":
            continue
        tab_line = line.split('|')
        key = tab_line[0].strip()
        value = tab_line[1].strip()
        dict_lang[key]=value
    f.close()
    jsonname = "../DATA/"+lang+".json"
    f = open(jsonname, 'w')
    f.write(json.dumps(dict_lang, sort_keys=True, indent=4))
    f.close()
    print(jsonname+" succesfully written")
