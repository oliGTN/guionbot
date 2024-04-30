import json
import sys

game_data = json.load(open(sys.argv[1], 'r'))
FRE_FR = json.load(open("DATA/FRE_FR.json", 'r'))

dict_capa = {}
added_units = []

#create dict for skills
dict_skills={}
for skill in game_data["skill"]:
    dict_skills[skill["id"]] = skill

#create dict for abilities
dict_abilities={}
dict_lore={}
for ability in game_data["ability"]:
    dict_abilities[ability["id"]] = ability
    dict_lore[ability["nameKey"]] = ability["descKey"]

f=open("DATA/skillList_dict.json", "w")
f.write(json.dumps(dict_skills, indent=4))
f.close()
f=open("DATA/abilityList_dict.json", "w")
f.write(json.dumps(dict_abilities, indent=4))
f.close()
f=open("DATA/lore_dict.json", "w")
f.write(json.dumps(dict_lore, indent=4))
f.close()


for unit in game_data["units"]:
    if unit["baseId"] in added_units:
        continue
    if not "any_obtainable" in unit["categoryId"]:
        continue
    if unit["rarity"] != 1:
        continue
    if unit["obtainableTime"] != "0":
        continue

    unit_id = unit["baseId"]
    dict_capa[unit_id] = {}
    list_skills = []
    for skillref in unit["skillReference"]:
        skill_id = skillref["skillId"]
        list_skills.append(skill_id)
    if "crew" in unit:
        for crew in unit["crew"]:
            for skillref in crew["skillReference"]:
                skill_id = skillref["skillId"]
                list_skills.append(skill_id)

    for skill_id in list_skills:
        skill = dict_skills[skill_id]
        my_capa = {}

        if skill_id.startswith("basic"):
            skill_shortname = "B"
            skill_type = "Basique"
        elif skill_id.startswith("leader"):
            skill_shortname = "L"
            skill_type = "Leader"
        elif skill_id.startswith("special"):
            skill_shortname = "S"+skill_id[-1]
            skill_type = "Spéciale "+skill_id[-1]
        elif skill_id.startswith("uniqueskill_GALACTICLEGEND"):
            skill_shortname = "GL"
            skill_type = "Légende Galactique"
        elif skill_id.startswith("unique"):
            skill_shortname = "U"+skill_id[-1]
            skill_type = "Unique "+skill_id[-1]
        elif skill_id.startswith("hardware"):
            skill_shortname = "H"+skill_id[-1]
            skill_type = "Hardware "+skill_id[-1]
        elif skill_id.startswith("contract"):
            skill_shortname = "C"
            skill_type = "Contrat"
        else:
            print("Type de skill inconnu : "+skill_id)
            sys.exit(1)

        ability_id = skill["abilityReference"]
        ability = dict_abilities[ability_id]
        ability_name = FRE_FR[ability["nameKey"]]

        my_capa["name"] = ability_name
        my_capa["type"] = skill_type

        my_capa["zetaTier"] = 99
        for i_tier in range(len(skill["tier"])):
            tier = skill["tier"][i_tier]
            if tier["isZetaTier"]:
                my_capa["zetaTier"] = i_tier+2
                break

        my_capa["id"] = skill_id

        if "omicronMode" in skill:
            if skill["omicronMode"] == "CONQUEST_OMICRON":
                my_capa["omicronMode"] = "CQ"
            elif skill["omicronMode"] == "GUILD_RAID_OMICRON":
                my_capa["omicronMode"] = "RD"
            elif skill["omicronMode"] == "GAC_3_OMICRON":
                my_capa["omicronMode"] = "GA3"
            elif skill["omicronMode"] == "GAC_5_OMICRON":
                my_capa["omicronMode"] = "GA5"
            elif skill["omicronMode"] == "TERRITORY_BATTLE_BOTH_OMICRON":
                my_capa["omicronMode"] = "TB"
            elif skill["omicronMode"] == "TERRITORY_WAR_OMICRON":
                my_capa["omicronMode"] = "TW"
            elif skill["omicronMode"] == "GAC_OMICRON":
                my_capa["omicronMode"] = "GA"
            elif skill["omicronMode"] == "GALACTIC_CHALLENGE_OMICRON":
                my_capa["omicronMode"] = "GC"
            else:
                print("OmicronMode inconnu : "+skill["omicronMode"])
                sys.exit(1)

        my_capa["omicronTier"] = 99
        for i_tier in range(len(skill["tier"])):
            tier = skill["tier"][i_tier]
            if tier["isOmicronTier"]:
                my_capa["omicronTier"] = i_tier+2
                break

        dict_capa[unit_id][skill_id] = my_capa
        dict_capa[unit_id][skill_shortname] = my_capa
        dict_capa[unit_id][ability_id] = my_capa

    added_units.append(unit["baseId"])

f=open("DATA/unit_capa_list.json", "w")
f.write(json.dumps(dict_capa, indent=4))
f.close()

