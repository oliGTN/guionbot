import json
import sys

game_data = json.load(open(sys.argv[1], 'r'))
FRE_FR = json.load(open("DATA/FRE_FR.json", 'r'))

dict_relic = {}
for recipe in game_data["recipe"]:
    if "type" in recipe and recipe["type"] == "RELIC":
        promo_index = int(recipe["id"].split("_")[-1])
        dict_relic[promo_index] = {}

        for ingredient in recipe["ingredients"]:
            dict_relic[promo_index][ingredient["id"]] = ingredient["minQuantity"]

f=open("DATA/relic_dict.json", "w")
f.write(json.dumps(dict_relic, indent=4))
f.close()

