##########################################################
# This code takes as input the HTML from <div class="mods-list">
# extracted from mod optimizer (chrome, dev tab) in a file
# input 1: txt file with html content (one line)
# input 2: PLAYERS/bot_xxx.json ou PLAYERS/<playerId>.json
# input 3: authentication token (1234abcd5678efef or user@gmail.com)
##########################################################
import string
import sys
import re
import json
from html.parser import HTMLParser
import copy #deepcopy
import requests
import time

import go
import goutils
import connect_mysql
import connect_rpc
import connect_crinolo
import data as godata
import emojis

#############
# MAIN
#############
dict_slot_by_shape = {"square": 2,
                      "arrow": 3,
                      "diamond": 4,
                      "triangle": 5,
                      "circle": 6,
                      "cross":7}
dict_shape_by_slot = {2: "square",
                      3: "arrow",
                      4: "diamond",
                      5: "triangle",
                      6: "circle",
                      7: "cross"}
dict_stat_by_set = {'1': "health",
                    '2': "offense",
                    '3': "defense",
                    '4': "speed",
                    '5': "critchance",
                    '6': "critdamage",
                    '7': "potency",
                    '8': "tenacity"}
dict_upgrade_level_cost = {1: {3: 6900, 6: 18400, 9: 37900, 12: 86200, 15: 248300},
                           3: {         6: 11500, 9: 31000, 12: 79300, 15: 241400},
                           6: {                   9: 19500, 12: 67800, 15: 229900},
                           9: {                             12: 48300, 15: 210400},
                          12: {                                        15: 162100}}

def transform_mod_list_to_dict(dict_player):
    #Get game mod data
    mod_list = godata.get("modList_dict.json")

    for unit_id in dict_player["rosterUnit"]:
        if not "equippedStatMod" in dict_player["rosterUnit"][unit_id]:
            #no mod for this unit
            continue

        unit_mods = dict_player["rosterUnit"][unit_id]["equippedStatMod"]
        dict_player["rosterUnit"][unit_id]["equippedStatMod"] = {}
        for mod in unit_mods:
            mod_id = mod["id"]
            mod_defId = mod["definitionId"]
            mod_slot = mod_list[mod_defId]["slot"]
            dict_player["rosterUnit"][unit_id]["equippedStatMod"][mod_slot] = mod_id

####################################
# IN: dict_player (from go.load_player)
# IN (optional): initialdata (from connect_rpc.get_player_initialdata)
# OUT: dict_player_mods = {mod_id: {"id":
#                                   "definitionId":
#                                   "unit_id":
#                                   "slot":
#                                   "rarity":
#                                   ... and other mod attributes
def get_dict_player_mods(dict_player, initialdata=None):
    #Get game mod data
    mod_list = godata.get("modList_dict.json")

    dict_player_mods = {}

    for unit_id in dict_player["rosterUnit"]:
        if not "equippedStatMod" in dict_player["rosterUnit"][unit_id]:
            #no mod for this unit
            continue

        unit_mods = dict_player["rosterUnit"][unit_id]["equippedStatMod"]
        for mod in unit_mods:
            mod_id = mod["id"]
            mod_level = mod["level"]
            mod_defId = mod["definitionId"]
            mod_slot = mod_list[mod_defId]["slot"]
            mod_rarity = mod_list[mod_defId]["rarity"]
            dict_player_mods[mod_id] = mod
            dict_player_mods[mod_id]["unit_id"] = unit_id
            dict_player_mods[mod_id]["slot"] = mod_slot
            dict_player_mods[mod_id]["rarity"] = mod_rarity

    if initialdata!=None:
        # Add the unequipped mods to the dictionary
        if not "unequippedMod" in initialdata["inventory"]:
            initialdata["inventory"]["unequippedMod"]=[]
        for mod in initialdata["inventory"]["unequippedMod"]:
            mod_id = mod["id"]
            mod_defId = mod["definitionId"]
            mod_slot = mod_list[mod_defId]["slot"]
            mod_rarity = mod_list[mod_defId]["rarity"]
            dict_player_mods[mod_id] = mod
            dict_player_mods[mod_id]["unit_id"] = None
            dict_player_mods[mod_id]["slot"] = mod_slot
            dict_player_mods[mod_id]["rarity"] = mod_rarity

    return dict_player_mods

##########################
# STEP3
# Prepare list of modification commands
# Manage the global list of mods to ensure not be blocked
#  by max size inventory
# One command per unit, listing all the mods to add and all the mods to remove
# IN: mod_allocations = {'MAGMATROOPER': [{'id': 'hjsfkjfsdksf34', "slot": 5}, ...]}
##########################
async def apply_mod_allocations(mod_allocations, allyCode, is_simu, interaction, initialdata=None):
    await interaction.edit_original_response(content=emojis.hourglass+" Récupération des infos du joueur...")

    # Get player data
    e, t, dict_player = await go.load_player(allyCode, 1, False)
    if e != 0:
        return 1, "ERR: "+t, {}

    #Get player API initialdata
    if initialdata==None:
        ec, et, initialdata = await connect_rpc.get_player_initialdata(allyCode)
        if ec!=0:
            return ec, et, {}

    # Get player credits
    player_credits = 0
    for currencyItem in initialdata["inventory"]["currencyItem"]:
        if "currency" in currencyItem and currencyItem["currency"] == "GRIND":
            player_credits = currencyItem["quantity"]

    #Create a dict of all mods for the player, by mod ID
    #AND modify the mod list of every unit by a dict, by slot
    await interaction.edit_original_response(content=emojis.hourglass+" Récupération de la liste des mods...")
    dict_player_mods = get_dict_player_mods(dict_player, initialdata)

    # transform mod list into dict of mod_id by slot
    transform_mod_list_to_dict(dict_player)

    #Get the free space in mod inventory
    initial_inventory = len(initialdata["inventory"]["unequippedMod"])
    mod_inventory_spares = 500 - initial_inventory

    max_inventory = initial_inventory
    unit_count = 0
    mod_add_count = 0
    unequip_cost = 0
    unequip_cost_by_rarity = {1: 550,
                              2: 1050,
                              3: 1900,
                              4: 3000,
                              5: 4750,
                              6: 8000}
    missing_mods = {} #key=Unit_defId / value=list of missing mods
    forbidden_mods = {} #key=Unit_defId / value=list of gold mods to gear<12 chars

    prev_display_time = 0
    original_unit_count = len(mod_allocations)
    while(len(mod_allocations)>0):
        #find best allocation (the one with most mods currently not allocated)
        min_delta_inventory = 7 # worst case is 6 added to the inventory
        best_a = None
        count_no_move = 0
        for a in mod_allocations:
            target_char_defId = a["unit_id"]
            target_char_id = dict_player["rosterUnit"][target_char_defId]["id"]
            target_char_gear = dict_player["rosterUnit"][target_char_defId]["currentTier"]

            a_delta_inventory = 0
            a_no_move = 0
            for allocated_mod in a["mods"]:
                allocated_mod_id = allocated_mod["id"]
                mod_slot = allocated_mod["slot"]

                if not allocated_mod_id in dict_player_mods:
                    # This means that the conf is using a mod that the player does not have anymore
                    # Add it to the list of warnings, and ignore it in the allocation
                    if not target_char_defId in missing_mods:
                        missing_mods[target_char_defId] = []
                    missing_mods[target_char_defId] = list(set(missing_mods[target_char_defId]+[allocated_mod_id]))
                    continue

                allocated_mod_rarity = dict_player_mods[allocated_mod_id]["rarity"]

                if allocated_mod_rarity>5 and target_char_gear<12:
                    # not possible to allocate a gold mod on a char with gear<12
                    # Add it to the list of warnings, and ignore it in the allocation
                    if not target_char_defId in forbidden_mods:
                        forbidden_mods[target_char_defId] = []
                    forbidden_mods[target_char_defId] = list(set(forbidden_mods[target_char_defId]+[allocated_mod_id]))
                    continue

                if dict_player_mods[allocated_mod_id]["unit_id"] == target_char_defId:
                    # The mod is already on the character
                    a_no_move += 1
                    continue
                elif dict_player_mods[allocated_mod_id]["unit_id"] == None:
                    # The mod comes from the inventory, this is good
                    a_delta_inventory -= 1

                if mod_slot in dict_player["rosterUnit"][target_char_defId]["equippedStatMod"]:
                    # there is a mod that is replaced. This mod goes back to the inventory,
                    # this is not good
                    a_delta_inventory += 1

            if a_no_move == len(a["mods"]):
                count_no_move += 1
            elif a_delta_inventory < min_delta_inventory:
                min_delta_inventory = a_delta_inventory
                best_a = a

        if best_a ==None:
            a = mod_allocations[0]
        else:
            a = best_a
        goutils.log2("DBG", "len(mod_allocations): "+str(len(mod_allocations)))
        goutils.log2("DBG", "best_a: "+str(best_a))

        #do the job with the allocation a
        new_unit_count = unit_count
        new_mod_add_count = mod_add_count
        new_unequip_cost = unequip_cost

        # An allocation is something like
        # "on the unit PRINCESSLEIA, we need to use mods ID1, ID2, ID3"
        target_char_defId = a["unit_id"]
        target_char_id = dict_player["rosterUnit"][target_char_defId]["id"]
        target_char_level = dict_player["rosterUnit"][target_char_defId]["currentLevel"]
        target_char_gear = dict_player["rosterUnit"][target_char_defId]["currentTier"]

        if target_char_level < 50:
            cost_txt = str(mod_add_count)+" mods déplacés, sur "+str(unit_count)+" persos ("+str(int(unequip_cost/100000)/10)+"M crédits)"
            return 1, target_char_defId+" n'est pas au niveau 50 > pas possible de lui mettre des mods", {"cost": cost_txt, "missing": missing_mods, "forbidden": forbidden_mods}

        mods_to_add = [] # list of mod IDs to be added to this unit
        mods_to_remove = [] # list of mod IDs to be removed from this unit
        for allocated_mod in a["mods"]:
            allocated_mod_id = allocated_mod["id"]
            mod_slot = allocated_mod["slot"]

            ####################
            # add the new mode to mods_to_add, then add the existing to mods_to_remove

            # First check if the target unit does not already have it
            # No need to move a mod if already in place

            # Look for the unit that has this mod
            # If the mod is not equipped, unit=None

            if allocated_mod_id in dict_player_mods:
                current_mod_unit = dict_player_mods[allocated_mod_id]["unit_id"]
            else:
                # This means that the conf is using a mod that the player does not have anymore
                # Already added to the list of warnings, still need to ignore it in the allocation
                continue

            allocated_mod_rarity = dict_player_mods[allocated_mod_id]["rarity"]
            if allocated_mod_rarity>5 and target_char_gear<12:
                # not possible to allocate a gold mod on a char with gear<12
                # Already added to the list of warnings, still need to ignore it in the allocation
                continue

            #print(target_char_defId)
            #print(allocated_mod_id)
            #print(current_mod_unit)
            if current_mod_unit != target_char_defId:
                # The mod is not already equipped

                # If the unit has no mod at all, create its mod dictionary (empty)
                if not "equippedStatMod" in dict_player["rosterUnit"][target_char_defId]:
                    dict_player["rosterUnit"][target_char_defId]["equippedStatMod"] = {}

                #Look for potential mod to be removed before adding the new one
                if mod_slot in dict_player["rosterUnit"][target_char_defId]["equippedStatMod"]:
                    previous_mod_id = dict_player["rosterUnit"][target_char_defId]["equippedStatMod"][mod_slot]
                    previous_mod_rarity = dict_player_mods[previous_mod_id]["rarity"]

                    mods_to_remove.append(previous_mod_id)
                    dict_player_mods[previous_mod_id]["unit_id"] = None
                    del dict_player["rosterUnit"][target_char_defId]["equippedStatMod"][mod_slot]
                    dict_player_mods[previous_mod_id]["unit_id"] = None

                    # add the cost of removing the mod in place on the unit
                    #print("unequip from "+target_char_defId+": "+str(previous_mod_rarity))
                    new_unequip_cost += unequip_cost_by_rarity[previous_mod_rarity]

                #the allocated (new) mod has to be equipped on the target character
                # and removed from previous unit
                mods_to_add.append(allocated_mod_id)
                prev_unit = dict_player_mods[allocated_mod_id]["unit_id"]
                if prev_unit != None:
                    # if the mod was equipped, remove it from the previous unit's dictionary
                    del dict_player["rosterUnit"][prev_unit]["equippedStatMod"][mod_slot]

                    # and add the cost of moving
                    #print("unequip from "+prev_unit+": "+str(allocated_mod_rarity))
                    new_unequip_cost += unequip_cost_by_rarity[allocated_mod_rarity]

                dict_player_mods[allocated_mod_id]["unit_id"] = target_char_defId
                dict_player["rosterUnit"][target_char_defId]["equippedStatMod"][mod_slot] = allocated_mod_id

        if len(mods_to_add) > 0:
            #write update request
            mods_txt = ""
            for id in mods_to_add:
                mods_txt += " +"+id
                new_mod_add_count += 1
            for id in mods_to_remove:
                mods_txt += " -"+id
            goutils.log2("DBG", "updateMods "+allyCode+" "+target_char_id+mods_txt+" #"+target_char_defId)
            new_unit_count += 1

            # If not simulation mode, send the request to RPC
            if not is_simu:
                ec, et = await connect_rpc.update_unit_mods(target_char_id, mods_to_add, mods_to_remove, allyCode)

                if ec!=0:
                    cost_txt = str(mod_add_count)+" mods déplacés, sur "+str(unit_count)+" persos ("+str(int(unequip_cost/100000)/10)+"M crédits)"

                    if et == 'STAT_MOD_ERROR_MOD_STORAGE_FULL_KEY':
                        err_txt = "inventaire plein"
                    else:
                        err_txt = str([target_char_defId, mods_to_add, mods_to_remove])+": "+et
                    return ec, err_txt, {"cost": cost_txt, "missing": missing_mods, "forbidden": forbidden_mods}

        elif len(mods_to_remove) > 0:
            if not is_simu:
                cost_txt = str(mod_add_count)+" mods déplacés, sur "+str(unit_count)+" persos ("+str(int(unequip_cost/100000)/10)+"M crédits)"
                ret_data = {"cost": cost_txt, "missing": missing_mods, "forbidden": forbidden_mods}
            else:
                ret_data = {"missing": missing_mods, "forbidden": forbidden_mods}
            return 1, "ERR: des mods à retirer pour "+target_char_defId+" "+str(mods_to_remove)+" mais aucun à ajouter", ret_data

        #manage max size required in mod inventory
        cur_inventory = [id for id in dict_player_mods if dict_player_mods[id]["unit_id"]==None]
        if len(cur_inventory) > max_inventory:
            max_inventory = len(cur_inventory)

        unit_count = new_unit_count
        mod_add_count = new_mod_add_count
        unequip_cost = new_unequip_cost

        #remove done allocation "a" from the list
        mod_allocations.remove(a)

        #Manage display to user
        if (time.time() - prev_display_time) > 5:
            new_msg_content = emojis.hourglass+" Reste "+str(len(mod_allocations)-count_no_move)+"/"+str(original_unit_count)+"..."
            try:
                await interaction.edit_original_response(content=new_msg_content)
            except Exception as e:
                goutils.log2("WAR", "Unable to update discord msg to: "+new_msg_content)
            prev_display_time = time.time()

    goutils.log2("INFO", "Max inventory: "+str(max_inventory))
    needed_inventory = max_inventory-initial_inventory

    ret_code = 0
    ret_txt = ""
    if is_simu:
        cost_txt = str(mod_add_count)+" mods à déplacer, sur "+str(unit_count)+" persos. "
        cost_txt+= str(needed_inventory)+" places nécessaires dans l'inventaire ("+str(500-initial_inventory)+" disponibles) "
        cost_txt+= "et "+str(int(unequip_cost/100000)/10)+"M crédits ("+str(int(player_credits/100000)/10)+"M disponibles)."
        if max_inventory>500 or unequip_cost>player_credits:
            cost_txt += " ATTENTION : ça ne passe pas !"
            ret_code = 2
            ret_txt = "Simulation échouée"
    else:
        cost_txt = str(mod_add_count)+" mods déplacés, sur "+str(unit_count)+" persos ("+str(int(unequip_cost/100000)/10)+"M crédits)"
    
    return ret_code, ret_txt, {"cost": cost_txt, "missing": missing_mods, "forbidden": forbidden_mods}

async def create_mod_config(conf_name, txt_allyCode, list_character_alias):
    dict_unitsList = godata.get("unitsList_dict.json")

    #Get game mod data
    mod_list = godata.get("modList_dict.json")

    # Get player data
    e, t, dict_player = await go.load_player(txt_allyCode, 1, False)
    if e != 0:
        return 1, "ERR: "+t

    #Manage request for all characters
    if 'all' in list_character_alias:
        list_unit_ids=list(dict_player["rosterUnit"].keys())
        list_unit_names = []
    else:
        #specific list of characters for one player
        list_unit_ids, dict_id_name, txt = goutils.get_characters_from_alias(list_character_alias)
        if txt != '':
            return 1, 'ERR: impossible de reconnaître ce(s) nom(s) >> '+txt

        list_unit_names = [dict_unitsList[id]["name"] for id in list_unit_ids]

    # Check if the config already exists
    query = "SELECT id\n"
    query+= "FROM mod_config_list\n"
    query+= "WHERE name = '"+conf_name+"' AND allyCode = "+txt_allyCode
    goutils.log2("DBG", query)
    config_id = connect_mysql.get_value(query)

    if config_id == None:
        # New config, create it
        query = "INSERT IGNORE INTO mod_config_list(name, allyCode) \n"
        query+= "VALUES('"+conf_name+"', "+txt_allyCode+")"
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

        #Get its ID
        query = "SELECT id\n"
        query+= "FROM mod_config_list\n"
        query+= "WHERE name = '"+conf_name+"' AND allyCode = "+txt_allyCode
        goutils.log2("DBG", query)
        config_id = connect_mysql.get_value(query)

    else:
        # Existing config,
        # Delete previous definition of this configuration
        query = "DELETE FROM mod_config_content\n"
        query+= "WHERE config_id = "+str(config_id)
        goutils.log2("DBG", query)
        connect_mysql.simple_execute(query)

    #loop on unit that needs to be saved in the config
    config_mod_count = 0
    config_unit_count = 0
    for unit_id in list_unit_ids:
        if not unit_id in dict_player["rosterUnit"]:
            return 1, "ERR: perso "+unit_id+" introuvable pour le joueur "+txt_allyCode

        unit = dict_player["rosterUnit"][unit_id]

        # Create query to add mods to the config
        if not "equippedStatMod" in unit:
            #this unit has no mod, go to next
            continue

        for mod in unit["equippedStatMod"]:
            mod_id = mod["id"]
            mod_defId = mod["definitionId"]
            mod_slot = mod_list[mod_defId]["slot"]
            mod_rarity = mod_list[mod_defId]["rarity"]
            query = "INSERT INTO mod_config_content(config_id, unit_id, mod_id, slot, rarity)\n"
            query+= "VALUES("+str(config_id)+", '"+unit_id+"', '"+mod_id+"', "+str(mod_slot)+", "+str(mod_rarity)+")"
            goutils.log2("DBG", query)
            connect_mysql.simple_execute(query)
            config_mod_count += 1

        config_unit_count += 1
            
    return_txt = "Conf "+conf_name+" créée pour "+txt_allyCode+" avec "+str(config_unit_count)+" persos et "+str(config_mod_count)+" mods"
    if list_unit_names != []:
        return_txt += "\n"+str(list_unit_names)
    else:
        return_txt += "\n(tous les persos)"

    return 0, return_txt

def get_mod_config(conf_name, txt_allyCode):
    # Check if the config exists
    query = "SELECT id\n"
    query+= "FROM mod_config_list\n"
    query+= "WHERE name = '"+conf_name+"' AND allyCode = "+txt_allyCode
    goutils.log2("DBG", query)
    config_id = connect_mysql.get_value(query)

    if config_id == None:
        return 1, "ERR: config "+conf_name+" introuvable pour le joueur "+txt_allyCode, None

    #Get the config content
    query = "SELECT unit_id, mod_id, slot, rarity FROM mod_config_content\n"
    query+= "WHERE config_id="+str(config_id)+"\n"
    query+= "ORDER BY unit_id"
    goutils.log2("DBG", query)
    db_data = connect_mysql.get_table(query)

    if db_data == None:
        return 1, "ERR: aucun perso trouvé pour la config "+conf_name+" du joueur "+txt_allyCode, None

    mod_allocations = []
    cur_unit_allocation = {"unit_id": None}
    for line in db_data:
        unit_id = line[0]
        mod_id = line[1]
        mod_slot = line[2]
        mod_rarity = line[3]

        if cur_unit_allocation["unit_id"] != unit_id:
            #change of unit in the list
            if cur_unit_allocation["unit_id"] != None:
                mod_allocations.append(cur_unit_allocation)

            #create the unit allocation
            cur_unit_allocation = {"unit_id": unit_id, "mods": []}

        cur_unit_allocation["mods"].append({"id": mod_id, "slot": mod_slot, "rarity": mod_rarity})

    #after last line, need to append the latest unit allocation
    mod_allocations.append(cur_unit_allocation)

    return 0, "", mod_allocations

async def apply_modoptimizer_allocations(modopti_content, txt_allyCode, is_simu, 
                                         interaction, initialdata=None):
    modopti_progress = json.loads(modopti_content)

    # a json may contain several profiles
    # look for thevright on
    my_profile = None
    for p in modopti_progress["profiles"]:
        if p["allyCode"] == txt_allyCode:
            my_profile = p
            break

    if my_profile == None:
        return 1, "Le fichier n'a pas de profil pour "+txt_allyCode, {}

    if not "modAssignments" in my_profile or len(my_profile["modAssignments"])==0:
        return 1, "Le fichier de définit aucun déplacement des mods", {}

    player_mods = {}
    for mod in my_profile["mods"]:
        player_mods[mod["mod_uid"]] = mod

    # mod_allocation element - dict
    # {'unit_id': "PRINCESSLEIA",
    #  'mods': [{'id': '9Ax0P8ybxxxxx', 'slot': 4, 'rarity': 5},
    #           {'id': '8Phsg65trTGxxxx', ...}
    #          ]
    # }
    mod_allocations = []
    for mod_assignment in my_profile["modAssignments"]:
        if mod_assignment == None:
            continue
        unit_id = mod_assignment["id"]
        mod_allocation = {"unit_id": unit_id, "mods": []}

        for mod_id in mod_assignment["assignedMods"]:
            mod_slot = dict_slot_by_shape[player_mods[mod_id]["slot"]]
            mod_rarity = player_mods[mod_id]["pips"]
            mod_allocation["mods"].append({"id": mod_id,
                                           "slot": mod_slot,
                                           "rarity": mod_rarity})
        mod_allocations.append(mod_allocation)

    #Apply modifications
    return await apply_mod_allocations(mod_allocations, txt_allyCode, is_simu, 
                                       interaction, initialdata=initialdata)

async def apply_config_allocations(config_name, txt_allyCode, is_simu, interaction):
    e, t, mod_allocations = get_mod_config(config_name, txt_allyCode)
    if e!=0:
        return 1, t, {}

    return await apply_mod_allocations(mod_allocations, txt_allyCode, is_simu,
                                       interaction)

########################################
async def get_modopti_export(txt_allyCode):
    mod_list = godata.get("modList_dict.json")
    dict_unitsList = godata.get("unitsList_dict.json")

    # get swgoh.gg character list for images
    #swgohgg_characters_url = 'https://swgoh.gg/api/characters'
    #goutils.log2("DBG", "Get data from " + swgohgg_characters_url)
    #r = requests.get(swgohgg_characters_url, allow_redirects=True)
    #list_characters = json.loads(r.content.decode('utf-8'))
    #dict_images = {}
    #for c in list_characters:
    #    dict_images[c["base_id"]] = c["image"]
    swgohgg_img_path = "https://game-assets.swgoh.gg/textures/"

    #Get player API data
    ec, et, dict_player = await go.load_player(txt_allyCode, 1, True)
    if ec!=0:
        return ec, et, None

    dict_player = goutils.roster_from_dict_to_list(dict_player)

    #Get player API initialdata
    ec, et, initialdata = await connect_rpc.get_player_initialdata(txt_allyCode)
    if ec!=0:
        return ec, et, None

    #Add stats
    ec, et, dict_player = connect_crinolo.add_base_stats(dict_player)
    if ec!=0:
        return ec, et, None

    modopti_export = {}
    modopti_export["profiles"] = []
    modopti_export["gameSettings"] = []
    modopti_export["lastRuns"] = []
    modopti_export["characterTemplates"] = []
    modopti_export["version"] = "1.8"
    modopti_export["allyCode"] = str(dict_player["allyCode"])

    my_profile = {}
    my_profile["allyCode"] = str(dict_player["allyCode"])
    my_profile["playerName"] = dict_player["name"]
    my_profile["characters"] = {}
    my_profile["mods"] = []
    my_profile["selectedCharacters"] = []
    my_profile["modAssignments"] = []
    my_profile["globalSettings"] = {"modChangeThreshold": 0,
                                    "lockUnselectedCharacters": False,
                                    "forceCompleteSets": False,
                                    "omicronBoostsGac": False,
                                    "omicronBoostsTw": False,
                                    "omicronBoostsTb": False,
                                    "omicronBoostsRaids": False,
                                    "omicronBoostsConquest": False}
    my_profile["previousSettings"] = {}
    my_profile["incrementalOptimizeIndex"] = None


    #Loop on all roster units. Fill profile characters and GameSettings
    for player_unit in dict_player["rosterUnit"]:
        if "crew" in player_unit["stats"]:
            #ignore ships
            continue

        unit_defId = player_unit["definitionId"].split(":")[0]
        #if unit_defId!="HERMITYODA":
        #    continue
        #print(unit_defId)
        #for s in player_unit["stats"]:
        #    print(s+":"+str(player_unit["stats"][s]))

        modopti_unit = {}
        modopti_unit["baseID"] = unit_defId
        modopti_unit["playerValues"] = {}
        modopti_unit["playerValues"]["level"] = player_unit["currentLevel"]
        modopti_unit["playerValues"]["stars"] = player_unit["currentRarity"]
        modopti_unit["playerValues"]["gearLevel"] = player_unit["currentTier"]

        modopti_unit["playerValues"]["gearPieces"] = []
        if "equipment" in player_unit:
            for eqpt in player_unit["equipment"]:
                modopti_unit["playerValues"]["gearPieces"].append(eqpt["equipmentId"])

        modopti_unit["playerValues"]["galacticPower"] = player_unit["gp"]

        ######################
        # BASE STATS
        
        # clean base stats
        remove_s = []
        for s in player_unit["stats"]["base"]:
            if player_unit["stats"]["base"][s] == None:
                remove_s.append(s)
        for s in remove_s:
            del player_unit["stats"]["base"][s]

        modopti_unit["playerValues"]["baseStats"] = {}
        if "1" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["health"] = int(player_unit["stats"]["base"]["1"]*1e-8)
        else:
            modopti_unit["playerValues"]["baseStats"]["health"] = 0

        if "28" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["protection"] = int(player_unit["stats"]["base"]["28"]*1e-8)
        else:
            modopti_unit["playerValues"]["baseStats"]["protection"] = 0

        if "5" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["speed"] = int(player_unit["stats"]["base"]["5"]*1e-8)
        else:
            modopti_unit["playerValues"]["baseStats"]["speed"] = 0

        if "17" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["potency"] = int(player_unit["stats"]["base"]["17"]*1e-6)
        else:
            modopti_unit["playerValues"]["baseStats"]["potency"] = 0

        if "18" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["tenacity"] = int(player_unit["stats"]["base"]["18"]*1e-6)
        else:
            modopti_unit["playerValues"]["baseStats"]["tenacity"] = 0

        if "16" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["critDmg"] = player_unit["stats"]["base"]["16"]*1e-6
        else:
            modopti_unit["playerValues"]["baseStats"]["critDmg"] = 0

        if "39" in player_unit["stats"]["final"]:
            modopti_unit["playerValues"]["baseStats"]["critAvoid"] = player_unit["stats"]["final"]["39"]*1e-6
        else:
            modopti_unit["playerValues"]["baseStats"]["critAvoid"] = 0

        if "37" in player_unit["stats"]["final"]:
            modopti_unit["playerValues"]["baseStats"]["accuracy"] = player_unit["stats"]["final"]["37"]*1e-6
        else:
            modopti_unit["playerValues"]["baseStats"]["accuracy"] = 0

        if "6" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["physDmg"] = int(player_unit["stats"]["base"]["6"]*1e-8)
        else:
            modopti_unit["playerValues"]["baseStats"]["physDmg"] = 0

        if "14" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["physCritRating"] = int(player_unit["stats"]["base"]["14"]*1e-8)
        else:
            modopti_unit["playerValues"]["baseStats"]["physCritRating"] = 0

        if "8" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["armor"] = int(player_unit["stats"]["base"]["8"]*1e-8)
        else:
            modopti_unit["playerValues"]["baseStats"]["armor"] = 0

        if "7" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["specDmg"] = int(player_unit["stats"]["base"]["7"]*1e-8)
        else:
            modopti_unit["playerValues"]["baseStats"]["specDmg"] = 0

        if "15" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["specCritRating"] = int(player_unit["stats"]["base"]["15"]*1e-8)
        else:
            modopti_unit["playerValues"]["baseStats"]["specCritRating"] = 0

        if "9" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["resistance"] = int(player_unit["stats"]["base"]["9"]*1e-8)
        else:
            modopti_unit["playerValues"]["baseStats"]["resistance"] = 0

        if "14" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["physCritChance"] = modopti_unit["playerValues"]["baseStats"]["physCritRating"] /24+10
        else:
            modopti_unit["playerValues"]["baseStats"]["physCritChance"] = 0

        if "15" in player_unit["stats"]["base"]:
            modopti_unit["playerValues"]["baseStats"]["specCritChance"] = modopti_unit["playerValues"]["baseStats"]["specCritRating"] /24+10
        else:
            modopti_unit["playerValues"]["baseStats"]["specCritChance"] = 0

        ######################
        # EQUIPPED STATS

        #copy base stats
        modopti_unit["playerValues"]["equippedStats"] = dict(modopti_unit["playerValues"]["baseStats"])

        #Then add gear if any
        if "1" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["health"] += int(player_unit["stats"]["gear"]["1"]*1e-8)

        if "28" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["protection"] += int(player_unit["stats"]["gear"]["28"]*1e-8)

        if "5" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["speed"] += int(player_unit["stats"]["gear"]["5"]*1e-8)

        if "17" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["potency"] += int(player_unit["stats"]["gear"]["17"]*1e-6)

        if "18" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["tenacity"] += int(player_unit["stats"]["gear"]["18"]*1e-6)

        if "16" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["critDmg"] += int(player_unit["stats"]["gear"]["16"]*1e-6)

        if "6" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["physDmg"] += int(player_unit["stats"]["gear"]["6"]*1e-8)

        if "14" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["physCritRating"] += int(player_unit["stats"]["gear"]["14"]*1e-8)

        if "8" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["armor"] += int(player_unit["stats"]["gear"]["8"]*1e-8)

        if "7" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["specDmg"] += int(player_unit["stats"]["gear"]["7"]*1e-8)

        if "15" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["specCritRating"] += int(player_unit["stats"]["gear"]["15"]*1e-8)

        if "9" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["resistance"] += int(player_unit["stats"]["gear"]["9"]*1e-8)

        if "14" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["physCritChance"] = modopti_unit["playerValues"]["equippedStats"]["physCritRating"] /24+10

        if "15" in player_unit["stats"]["gear"]:
            modopti_unit["playerValues"]["equippedStats"]["specCritChance"] = modopti_unit["playerValues"]["equippedStats"]["specCritRating"] /24+10

        #Relic
        if "relic" in player_unit:
            modopti_unit["playerValues"]["relicTier"] = player_unit["relic"]["currentTier"]
            if modopti_unit["playerValues"]["relicTier"]==1:
                modopti_unit["playerValues"]["relicTier"]=2

        modopti_unit["optimizerSettings"] = {"targets": [],
                                             "minimumModDots": 1,
                                             "sliceMods": False,
                                             "isLocked": False}
                                    
        # Add the unit to modopti_export
        my_profile["characters"][unit_defId] = modopti_unit

        ##################################
        # Loop through equipped mods

        if "equippedStatMod" in player_unit:
            for mod in player_unit["equippedStatMod"]:
                modopti_mod = mod_to_modopti(mod, unit_defId)
                my_profile["mods"].append(modopti_mod)

        ##################################
        # GameSettings

        my_unit_setting = {}
        my_unit_setting["baseID"] = unit_defId
        my_unit_setting["name"] = dict_unitsList[unit_defId]["name"]
        #my_unit_setting["avatarUrl"] = dict_images[unit_defId]
        my_unit_setting["avatarUrl"] = swgohgg_img_path+dict_unitsList[unit_defId]["thumbnailName"]+".png"
        my_unit_setting["description"] = ""
        
        forceAlignment = dict_unitsList[unit_defId]["forceAlignment"]
        if forceAlignment==1:
            my_unit_setting["alignment"] = "neutral"
        elif forceAlignment==2:
            my_unit_setting["alignment"] = "light"
        else:
            my_unit_setting["alignment"] = "dark"
        my_unit_setting["tags"] = dict_unitsList[unit_defId]["categoryId"]

        modopti_export["gameSettings"].append(my_unit_setting)

    #Loop on unequipped mods
    for mod in initialdata["inventory"]["unequippedMod"]:
        modopti_mod = mod_to_modopti(mod, None)
        my_profile["mods"].append(modopti_mod)

    modopti_export["profiles"].append(my_profile)

    return 0, "", modopti_export
    
def add_stats_to_modopti_mod(type_name, value_name, roll_name, mod_stat_info, modopti_mod):
    #print(mod_stat)
    mod_stat = mod_stat_info["stat"]
    if mod_stat["unitStatId"]==1:
        modopti_mod[type_name] = "Health"
        stat_value = int(int(mod_stat["unscaledDecimalValue"])*1e-8)
    elif mod_stat["unitStatId"]==5:
        modopti_mod[type_name] = "Speed"
        stat_value = int(int(mod_stat["unscaledDecimalValue"])*1e-8)
    elif mod_stat["unitStatId"]==16:
        modopti_mod[type_name] = "Critical Damage %"
        stat_value = round(int(mod_stat["unscaledDecimalValue"])*1e-6, 3)
    elif mod_stat["unitStatId"]==17:
        modopti_mod[type_name] = "Potency %"
        stat_value = round(int(mod_stat["unscaledDecimalValue"])*1e-6, 3)
    elif mod_stat["unitStatId"]==18:
        modopti_mod[type_name] = "Tenacity %"
        stat_value = round(int(mod_stat["unscaledDecimalValue"])*1e-6, 3)
    elif mod_stat["unitStatId"]==28:
        modopti_mod[type_name] = "Protection"
        stat_value = int(int(mod_stat["unscaledDecimalValue"])*1e-8)
    elif mod_stat["unitStatId"]==41:
        modopti_mod[type_name] = "Offense"
        stat_value = int(int(mod_stat["unscaledDecimalValue"])*1e-8)
    elif mod_stat["unitStatId"]==42:
        modopti_mod[type_name] = "Defense"
        stat_value = int(int(mod_stat["unscaledDecimalValue"])*1e-8)
    elif mod_stat["unitStatId"]==48:
        modopti_mod[type_name] = "Offense %"
        stat_value = round(int(mod_stat["unscaledDecimalValue"])*1e-6, 3)
    elif mod_stat["unitStatId"]==49:
        modopti_mod[type_name] = "Defense %"
        stat_value = round(int(mod_stat["unscaledDecimalValue"])*1e-6, 3)
    elif mod_stat["unitStatId"]==52:
        modopti_mod[type_name] = "Accuracy %"
        stat_value = round(int(mod_stat["unscaledDecimalValue"])*1e-6, 3)
    elif mod_stat["unitStatId"]==53:
        modopti_mod[type_name] = "Critical Chance %"
        stat_value = round(int(mod_stat["unscaledDecimalValue"])*1e-6, 3)
    elif mod_stat["unitStatId"]==54:
        modopti_mod[type_name] = "Critical Avoidance %"
        stat_value = round(int(mod_stat["unscaledDecimalValue"])*1e-6, 3)
    elif mod_stat["unitStatId"]==55:
        modopti_mod[type_name] = "Health %"
        stat_value = round(int(mod_stat["unscaledDecimalValue"])*1e-6, 3)
    elif mod_stat["unitStatId"]==56:
        modopti_mod[type_name] = "Protection %"
        stat_value = round(int(mod_stat["unscaledDecimalValue"])*1e-6, 3)
    else:
        print("Unknown mod stat: "+str(mod_stat["unitStatId"]))
        sys.exit(1)
    
    stat_value_txt = str(stat_value)
    if "." in stat_value_txt:
        stat_value_txt = stat_value_txt.strip("0")
        if stat_value_txt[-1]==".":
            stat_value_txt = stat_value_txt[:-1]
    modopti_mod[value_name] = "+"+stat_value_txt

    if "statRolls" in mod_stat_info:
        modopti_mod[roll_name] = mod_stat_info["statRolls"]

    return modopti_mod

def mod_to_modopti(mod, unit_defId):
    mod_list = godata.get("modList_dict.json")

    mod_defId = mod["definitionId"]

    modopti_mod = {}

    #print(mod["id"])
    modopti_mod = add_stats_to_modopti_mod("primaryBonusType",
                                           "primaryBonusValue",
                                           None,
                                           mod["primaryStat"],
                                           modopti_mod)

    if not "secondaryStat" in mod:
        #Create empty table, to ensure creating empty values for secondary stats
        mod["secondaryStat"] = []

    #Loop through secondary values
    pos_sec_stat = 1
    for sec_stat in mod["secondaryStat"]:
        modopti_mod = add_stats_to_modopti_mod("secondaryType_"+str(pos_sec_stat),
                                               "secondaryValue_"+str(pos_sec_stat),
                                               "secondaryRoll_"+str(pos_sec_stat),
                                               sec_stat,
                                               modopti_mod)

        pos_sec_stat += 1

    #Create empty secondary values (otherwise Mod Optimizer crashes)
    for empty_pos in range(pos_sec_stat,5):
        modopti_mod["secondaryType_"+str(empty_pos)] = ""
        modopti_mod["secondaryValue_"+str(empty_pos)] = ""
        modopti_mod["secondaryRoll_"+str(empty_pos)] = ""

    modopti_mod["mod_uid"] = mod["id"]
    modopti_mod["slot"] = dict_shape_by_slot[mod_list[mod_defId]["slot"]]
    modopti_mod["set"] = dict_stat_by_set[mod_list[mod_defId]["setId"]]
    modopti_mod["level"] = mod["level"]
    modopti_mod["pips"] = mod_list[mod_defId]["rarity"]
    modopti_mod["characterID"] = unit_defId
    modopti_mod["tier"] = mod["tier"]

    return modopti_mod

async def get_mod_stats(txt_allyCode):
    #Get game mod data
    mod_list = godata.get("modList_dict.json")

    # Get player data
    e, t, dict_player = await go.load_player(txt_allyCode, -1, False)
    if e != 0:
        return 1, "ERR: "+t

    set_count = {}
    for unit_id in dict_player["rosterUnit"]:
        unit = dict_player["rosterUnit"][unit_id]
        for mod in unit["equippedStatMod"]:
            mod_defId=mod["definitionId"]
            mod_setId=mod_list[mod_defId]["setId"]
            mod_set=dict_stat_by_set[mod_setId]
            if not mod_set in set_count:
                set_count[mod_set]=0

            set_count[mod_set]+=1

    # normalize to 100%
    total_mods=sum(set_count.values())
    for k in set_count:
        set_count[k]=set_count[k]/total_mods

    return set_count

################################
# upgrade all mods within mod_allocations to level 15
async def upgrade_allocated_mods_to_15(mod_allocations, dict_player_mods, allyCode, is_simu):
    # list all mods below level 15
    list_mods = []
    upgrade_cost = 0
    for a in mod_allocations:
        for allocated_mod in a["mods"]:
            allocated_mod_id = allocated_mod["id"]
            mod_level = dict_player_mods[allocated_mod_id]["level"]
            if mod_level<15:
                list_mods.append(allocated_mod_id)
                mod_upgrade_cost = dict_upgrade_level_cost[mod_level][15]
                upgrade_cost += mod_upgrade_cost

    if not is_simu:
        # launch the request
        err_code, err_txt = await connect_rpc.upgrade_level_mods(list_mods, 15, allyCode)
    else:
        err_code = 0
        err_txt = ""

    return err_code, err_txt, upgrade_cost

############################################################
# upgrade all equipped mods to specified level
# option for mods having speed as a secondary
# dict_player_mods should only contain only equipped mods
async def upgrade_roster_mods(dict_player_mods, target_level, allyCode, is_simu=False, only_speed_sec=False):
    # list all mods below target level
    list_mods = []
    upgrade_cost = 0
    for mod_id in dict_player_mods:
        mod = dict_player_mods[mod_id]
        mod_level = mod["level"]
        if mod_level<target_level:
            if only_speed_sec:
                if not "secondaryStat" in mod:
                    # no secondary = no speed secondary
                    # exit loop and go to next mod
                    continue

                has_speed_sec = False
                for secStat in mod["secondaryStat"]:
                    if secStat["stat"]["unitStatId"] == 5:
                        has_speed_sec = True
                if not has_speed_sec:
                    # no speed secondary
                    # exit loop and go to next mod
                    continue

            list_mods.append(mod_id)
            mod_upgrade_cost = dict_upgrade_level_cost[mod_level][target_level]
            upgrade_cost += mod_upgrade_cost

    if len(list_mods)==0:
        return 1, "Aucun mod à passer au niveau "+str(target_level)

    err_code=0
    if not is_simu:
        # launch the request
        err_code, err_txt = await connect_rpc.upgrade_level_mods(list_mods, target_level, allyCode)

    if err_code == 0:
        mod_count = len(list_mods)
        if is_simu:
            cost_txt = "[SIMULATION] "+str(mod_count)+" mods à passer au niveau "+str(target_level)+" ("+str(int(upgrade_cost/100000)/10)+"M crédits nécessaires)"
        else:
            cost_txt = str(mod_count)+" mods passés au niveau "+str(target_level)+" ("+str(int(upgrade_cost/100000)/10)+"M crédits)"

        return 0, cost_txt
    else:
        return err_code, err_txt

async def allocate_mods_to_empty_slots(txt_allyCode, initialdata=None):
    mod_list = godata.get("modList_dict.json")
    dict_units = godata.get("unitsList_dict.json")

    # Get player data
    e, t, dict_player = await go.load_player(txt_allyCode, 1, False)
    if e != 0:
        return 1, "ERR: "+t, {}

    #Get player API initialdata
    if initialdata==None:
        ec, et, initialdata = await connect_rpc.get_player_initialdata(txt_allyCode)
        if ec!=0:
            return ec, et, {}

    dict_player_mods = get_dict_player_mods(dict_player, initialdata=initialdata)

    unallocated_mods = {2: [], 3: [], 4: [], 5: [], 6: [], 7: []}
    for mod_id in dict_player_mods:
        mod = dict_player_mods[mod_id]
        if mod["unit_id"] == None:
            mod_slot = mod["slot"]
            mod_speed = 0
            if mod["primaryStat"]["stat"]["unitStatId"]==5:
                mod_speed = int(mod["primaryStat"]["stat"]["statValueDecimal"])/10000
            elif "secondaryStat" in mod:
                for sec_stat in mod["secondaryStat"]:
                    if sec_stat["stat"]["unitStatId"]==5:
                        mod_speed = int(sec_stat["stat"]["statValueDecimal"])/10000
            mod["mod_speed"] = mod_speed
            unallocated_mods[mod_slot].append(mod)

    #Sort mods by amount of revealed secondary stat, then speed
    #Best mod is at the start of the list
    for mod_slot in unallocated_mods:
        list_mods = unallocated_mods[mod_slot]
        list_mods.sort(key=lambda x: (-len(x["secondaryStat"]), -x["mod_speed"]))
        unallocated_mods[mod_slot] = list_mods

    mod_allocations = {} #{'MAGMATROOPER': [{'id': 'hjsfkjfsdksf34', "slot": 5}, ...]}
    for unit_id in dict_player['rosterUnit']:
        combatType = dict_units[unit_id]["combatType"]
        if combatType != 1:
            continue

        unit = dict_player['rosterUnit'][unit_id]
        unit_gear = unit["currentTier"]

        #Find empty mod slots for this unit
        empty_slots = [2, 3, 4, 5, 6, 7]
        if "equippedStatMod" in unit:
            for mod in unit["equippedStatMod"]:
                mod_defId = mod["definitionId"]
                mod_slot = mod_list[mod_defId]["slot"]
                empty_slots.remove(mod_slot)

        #Now that we have the empty slots, allocate them
        for empty_slot in empty_slots:
            if len(unallocated_mods[empty_slot]) > 0:
                best_mod_pos = 0
                best_mod = None
                mod_found = False
                while not mod_found:
                    best_mod = unallocated_mods[empty_slot][best_mod_pos]
                    if best_mod["rarity"]>5 and unit_gear<12:
                        # not possible to allocate a gold mod on a char with gear<12
                        if best_mod_pos+1 == len(unallocated_mods[empty_slot]):
                            # no more mods, cancel
                            break

                        # Try the next one
                        best_mod_pos+=1
                        continue

                    #Mod is suitable
                    mod_found = True

                if mod_found:
                    if not unit_id in mod_allocations:
                        mod_allocations[unit_id] = []
                    mod_allocations[unit_id].append({"id": best_mod["id"], "slot": empty_slot})
                    del unallocated_mods[empty_slot][best_mod_pos]

    return 0, "", {"mod_allocations": mod_allocations,
                   "rpc_data": {"dict_player": dict_player, 
                                "initialdata": initialdata} }
