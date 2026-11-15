import sys
import json
import golog

#############################
game_data = json.load(open(sys.argv[1], 'r'))

dict_recipes = {}
for recipe in game_data["recipe"]:
    dict_recipes[recipe["id"]] = recipe

dict_tables = {}
for table in game_data["table"]:
    dict_tables[table["id"]] = table

modList_dict = {}
for mod in game_data["statMod"]:
    modList_dict[mod['id']] = {"slot": mod["slot"],
                               "setId": mod["setId"],
                               "rarity": mod["rarity"]}

    if "promotionId" in mod and mod["promotionId"]!='':
        modList_dict[mod['id']]["promotionId"] = mod["promotionId"]

    if "promotionRecipeId" in mod and mod["promotionRecipeId"]!='':
        promotionRecipe = {}
        for ingredient in dict_recipes[mod["promotionRecipeId"]]["ingredients"]:
            promotionRecipe[ingredient["id"]] = ingredient["minQuantity"]
        modList_dict[mod['id']]["promotionRecipe"] = promotionRecipe

    if "tierUpRecipeTableId" in mod and mod["tierUpRecipeTableId"]!='':
        tierUpRecipeTable = []
        for tierUpRecipe in dict_tables[mod["tierUpRecipeTableId"]]["row"]:
            promotionRecipe = {}
            for ingredient in dict_recipes[tierUpRecipe["value"]]["ingredients"]:
                promotionRecipe[ingredient["id"]] = ingredient["minQuantity"]
            tierUpRecipeTable.append(promotionRecipe)
        modList_dict[mod['id']]["tierUpRecipeTable"] = tierUpRecipeTable


fnew = open('DATA/modList_dict.json', 'w')
fnew.write(json.dumps(modList_dict, sort_keys=True, indent=4))
fnew.close()
