import json
import os

localization_path = "../warstats/LocalizationBundle"
key_map = localization_path+"/Loc_Key_Mapping.txt"
dict_map = {}
f = open(key_map)
for line in f.readlines():
    if line[0] == "#":
        continue
    if line.strip() == "":
        continue
    tab_line = line.split('|')
    key = tab_line[0].strip()
    value = tab_line[1].strip()[2:]
    dict_map[value]=key
f.close()

for filename in os.listdir(localization_path):
    lang = filename[4:10]
    if lang in ["FRE_FR", "ENG_US"]:
        dict_lang = {}
        f = open(localization_path+"/"+filename, 'r')
        for line in f.readlines():
            if line[0] == "#":
                continue
            if line.strip() == "":
                continue
            tab_line = line.split('|')
            key = tab_line[0].strip()
            value = tab_line[1].strip()
            dict_lang[key]=value

            if key in dict_map:
                dict_lang[dict_map[key]]=value

        f.close()
        jsonname = "../DATA/"+lang+".json"
        f = open(jsonname, 'w')
        f.write(json.dumps(dict_lang, sort_keys=True, indent=4))
        f.close()
        print(jsonname+" succesfully written")

key_map = localization_path+"/Loc_Key_Mapping.txt"

