import json
from SCRIPTS.game_data_utils import load_game_data
import sys

game_data = load_game_data(sys.argv[1])
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

