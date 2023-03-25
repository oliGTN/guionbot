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
for ability in game_data["ability"]:
    dict_abilities[ability["id"]] = ability

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

        dict_capa[unit_id][skill_shortname] = ["", False, "", "", -1]
        dict_capa[unit_id][skill_id] = ["", "", False, "", -1]

        ability_id = skill["abilityReference"]
        ability = dict_abilities[ability_id]
        ability_name = FRE_FR[ability["nameKey"]]
        dict_capa[unit_id][skill_shortname][0] = ability_name
        dict_capa[unit_id][skill_id][0] = ability_name

        dict_capa[unit_id][skill_id][1] = skill_type

        dict_capa[unit_id][skill_shortname][1] = skill["isZeta"]
        dict_capa[unit_id][skill_id][2] = skill["isZeta"]

        dict_capa[unit_id][skill_shortname][2] = skill_id

        if "omicronMode" in skill:
            if skill["omicronMode"] == "CONQUEST_OMICRON":
                dict_capa[unit_id][skill_shortname][3] = "CQ"
                dict_capa[unit_id][skill_id][3] = "CQ"
            elif skill["omicronMode"] == "GUILD_RAID_OMICRON":
                dict_capa[unit_id][skill_shortname][3] = "RD"
                dict_capa[unit_id][skill_id][3] = "RD"
            elif skill["omicronMode"] == "GAC_3_OMICRON":
                dict_capa[unit_id][skill_shortname][3] = "GA3"
                dict_capa[unit_id][skill_id][3] = "GA3"
            elif skill["omicronMode"] == "TERRITORY_BATTLE_BOTH_OMICRON":
                dict_capa[unit_id][skill_shortname][3] = "TB"
                dict_capa[unit_id][skill_id][3] = "TB"
            elif skill["omicronMode"] == "TERRITORY_WAR_OMICRON":
                dict_capa[unit_id][skill_shortname][3] = "TW"
                dict_capa[unit_id][skill_id][3] = "TW"
            elif skill["omicronMode"] == "GAC_OMICRON":
                dict_capa[unit_id][skill_shortname][3] = "GA"
                dict_capa[unit_id][skill_id][3] = "GA"
            else:
                print("OmicronMode inconnu : "+skill["omicronMode"])
                sys.exit(1)

            for skill_tier in range(len(skill["tier"])):
                if skill["tier"][skill_tier]["isOmicronTier"]:
                    break
            dict_capa[unit_id][skill_shortname][4] = skill_tier+2
            dict_capa[unit_id][skill_id][4] = skill_tier+2
            


    added_units.append(unit["baseId"])

f=open("DATA/unit_capa_list.json", "w")
f.write(json.dumps(dict_capa, indent=4))
f.close()

