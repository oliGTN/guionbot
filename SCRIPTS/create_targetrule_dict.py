import json
import sys

game_data = json.load(open(sys.argv[1], 'r'))

dict_tags = {} # key:tag / value:unit defId

for unit in game_data["units"]:
    if unit["rarity"] != unit["maxRarity"]:
        continue

    #Following filter to remove PVE units - same filter above for unitsAlias
    if not "any_obtainable" in unit["categoryId"]:
        continue
    if unit["obtainableTime"] != "0":
        continue
    if not unit["obtainable"]:
        continue

    defId = unit["baseId"]
    for c in unit["categoryId"]:
        if c.startswith("selftag"):
            if not c in dict_tags:
                dict_tags[c] = defId
            else:
                if dict_tags[c] != defId:
                    print(c, defId, dict_tags[c])

dict_rules = {}
for rule in game_data["battleTargetingRule"]:
    rule_id = rule["id"]
    if "category" in rule:
        for c in rule["category"]["category"]:
            c_id = c["categoryId"]
            if c_id.startswith("selftag"):
                if c_id in dict_tags:
                    dict_rules[rule_id] = dict_tags[c_id]

#Write file
f=open("DATA/targeting_rule_list.json", "w")
f.write(json.dumps(dict_rules, indent=4))
f.close()
