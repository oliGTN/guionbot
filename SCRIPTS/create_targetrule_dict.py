import json
import sys

game_data = json.load(open(sys.argv[1], 'r'))

dict_rules = {}
for rule in game_data["battleTargetingRule"]:
    rule_id = rule["id"]
    if "category" in rule:
        for c in rule["category"]["category"]:
            c_id = c["categoryId"]
            if not c["exclude"]:
                if not rule_id in dict_rules:
                    dict_rules[rule_id] = [c_id]
                else:
                    dict_rules[rule_id].append(c_id)
                    if "datacron" in rule_id:
                        print("WAR: double category for rule "+rule_id)

#Write file
f=open("DATA/targetrules_dict.json", "w")
f.write(json.dumps(dict_rules, indent=4))
f.close()
