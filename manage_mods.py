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

import config
import goutils

class ModOptimizerListParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)

        self.state_parser=0
        #   en recherche de div class='mod-row set'
        #2: en recherche de div class='character-id'
        #3: en recherche de h3
        #4: en recherche de text
        #5: en recherche de div class='mod-set-detail'
        #6: en recherche de div class='mod-image *'
        #8: en recherche de div class='mod-stats'
        #9: en recherche de li > 10
        #                OU div class="assigned-character' > 11
        #                OU button > 11
        #10: en recherche de text PUIS 9
        #11: en recherche de img
        #12: en recherche de text PUIS 6
        #   en recherche de tbody > 1

        self.current_mod_allocation = {}
        self.cur_mod = {}
        self.list_allocations = []

    def handle_starttag(self, tag, attrs):
        #at any point, this tag realigns the parser on the right state
        if tag=='div':
            for name, value in attrs:
                if name=='class' and value=='mod-row set':
                    self.current_mod_allocation = {}
                    self.state_parser=2

        if self.state_parser==2:
            if tag=='div':
                for name, value in attrs:
                    if name=='class' and value=='character-id':
                        self.state_parser=3

        if self.state_parser==3:
            if tag=='h3':
                self.state_parser=4

        if self.state_parser==5:
            if tag=='div':
                for name, value in attrs:
                    if name=='class' and value=='mod-set-detail':
                        self.current_mod_allocation["mods"] = {}
                        self.state_parser=6

        if self.state_parser==6:
            if tag=='div':
                for name, value in attrs:
                    if name=='class' and value.startswith("mod-image"):
                        re_pattern = "mod-image dots-([0-9]) (square|arrow|diamond|triangle|circle|cross) (offense|health|speed|potency|tenacity|critchance|critdamage|defense) (.*)"
                        ret_re = re.search(re_pattern, value)
                        mod_dots = ret_re.group(1)
                        mod_shape = ret_re.group(2)
                        mod_stat = ret_re.group(3)
                        mod_color = ret_re.group(4)

                        self.cur_mod = {"pips": int(mod_dots),
                                   "set": mod_stat,
                                   "color": mod_color}

                        self.current_mod_allocation["mods"][mod_shape] = self.cur_mod

                        self.state_parser=8

        if self.state_parser==8:
            if tag=='div':
                for name, value in attrs:
                    if name=='class' and value=="mod-stats":
                        self.state_parser=9

        if self.state_parser==9:
            if tag=='li':
                self.state_parser=10

        if self.state_parser==9:
            if tag=='div':
                for name, value in attrs:
                    if name=='class' and value=="assigned-character":
                        self.state_parser=11

        if self.state_parser==9:
            if tag=='button':
                self.state_parser=11

        if self.state_parser==11:
            if tag=='span':
                for name, value in attrs:
                    if name=='class' and value=="avatar-name":
                        self.state_parser=12

        #at any point, this tag realigns the parser on the right state
        if tag=='tbody':
            if len(self.current_mod_allocation)>0:
                #print(self.current_mod_allocation)
                self.list_allocations.append(self.current_mod_allocation.copy())
            self.state_parser=9


        #if "character" in self.current_mod_allocation and \
        #   self.current_mod_allocation["character"]=="Old Daka":
        #    print(self.state_parser)



    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        data = data.strip()
        if self.state_parser==4:
            self.current_mod_allocation["character"] = data
            self.state_parser=5

        if self.state_parser==10:
            re_pattern = "([0-9]*\.?[0-9]*%?) (.*)"
            ret_re = re.search(re_pattern, data)
            if ret_re != None:
                stat_value = ret_re.group(1)
                stat_type = ret_re.group(2)

                if not "primary" in self.cur_mod:
                    self.cur_mod["primary"] = [stat_value, stat_type]
                    self.cur_mod["secondary"] = []
                else:
                    self.cur_mod["secondary"].append([stat_value, stat_type])

                self.state_parser=9
            elif data == "None":
                self.state_parser=9


        if self.state_parser==12:
            self.cur_mod["character"] = data
            self.state_parser=6

    def get_allocations(self):
        return self.list_allocations

#############
# MAIN
#############
dict_slot_by_shape = {"square": 2,
                      "arrow": 3,
                      "diamond": 4,
                      "triangle": 5,
                      "circle": 6,
                      "cross":7}
dict_stat_by_set = {'1': "health",
                    '2': "offense",
                    '3': "defense",
                    '4': "speed",
                    '5': "critchance",
                    '6': "critdamage",
                    '7': "potency",
                    '8': "tenacity"}

#Prepare the dict to transform names into unit ID
dict_units = json.load(open("DATA/unitsList_dict.json", "r"))
ENG_US = json.load(open("DATA/ENG_US.json", "r"))
dict_names = {}
for unit_id in dict_units:
    unit_name = ENG_US[dict_units[unit_id]["nameKey"]]
    dict_names[unit_name] = unit_id

#Get game mod data
mod_list = json.load(open("DATA/modList_dict.json", "r"))

def get_mod_allocations_from_modoptimizer(html_file, initial_dict_player):
    ##########################
    # STEP1
    # Read Mod Optimizer HTM
    # Get a list of mods per unit, with the target mod, 
    #  its characteristic, and which unit has it now
    #
    # modopti_allocations - list
    # modopti_allocation element - dict
    #    character: 'English unit name'
    #    mods - list
    #    mod element - dict
    #       'square': {'pips': 5, 
    #                  'set': 'potency', 
    #                  'color': 'blue'
    #                  'primary': ['5.88%', 'Offense'],
    #                  'secondary': [['10', 'Speed'], 
    #                                ['1.36%', 'Protection'], 
    #                                ['1148', 'Protection'], 
    #                                ['1.38%', 'Defense']], 
    #                  'character': 'Resistance Hero Poe'},
    #       'arrow': ...
    ##########################
    modopti_parser = ModOptimizerListParser()
    modopti_parser.feed(open(html_file, 'r').read())
    modopti_allocations = modopti_parser.get_allocations()

    ##########################
    # STEP2
    # Transform ModOpti allocation into mod id allocation
    # Read current player info to get mod IDs
    # Check consistency of characteristics in the process
    ##########################
    mod_allocations = []
    # mod_allocations - list
    # mod_allocation element - dict
    # {'unit_id': "PRINCESSLEIA",
    #  'mods': ['9Ax0P8ybxxxxx', '8Phsg65trTGxxxx', ...]}

    for a in modopti_allocations:
        target_char_name = a["character"]
        target_char_defId = dict_names[target_char_name]

        mod_allocation = {'unit_id': target_char_defId, 'mods': []}
        for allocated_mod_shape in a["mods"]:
            allocated_mod = a["mods"][allocated_mod_shape]
            allocated_mod_slot = dict_slot_by_shape[allocated_mod_shape]

            source_char_name = allocated_mod["character"]
            source_char_defId = dict_names[source_char_name]

            #get a dict (char_mods) with existing mods for the source character (before any move)
            char_mods = {}
            for roster_mod in initial_dict_player["rosterUnit"][source_char_defId]["equippedStatMod"]:
                mod_defId = roster_mod["definitionId"] #string
                mod_rarity = mod_list[mod_defId]["rarity"]
                mod_setId = mod_list[mod_defId]["setId"]
                mod_slot = mod_list[mod_defId]["slot"]
                mod_id = roster_mod["id"]
                char_mods[mod_slot] = {"pips": mod_rarity,
                                      "set": dict_stat_by_set[mod_setId],
                                      "id": mod_id}

            #compare replacement mod characteristics with the mod from the source character
            replacement_mod = char_mods[allocated_mod_slot]
            if    replacement_mod["pips"] != allocated_mod["pips"] \
               or replacement_mod["set"] != allocated_mod["set"]:
                print("\t"+allocated_mod_shape+": "+str(allocated_mod))
                print("\t\t"+str(replacement_mod))
                print("\t>>> ERREUR incohérence")
                sys.exit(1)

            mod_allocation['mods'].append(replacement_mod["id"])

        mod_allocations.append(mod_allocation)

    return mod_allocations

##########################
# STEP3
# Prepare list of modification commands
# Manage the global list of mods to ensure not be blocked
#  by max size inventory
# One command per unit, listing all the ods to add and all the mods to remove
##########################
def apply_mod_allocations(mod_allocations, allyCode, initial_dict_player):
    #Create a dict of all mods for the player, by mod ID
    #AND modify the mod list of every unit by a dict, by slot
    initial_dict_player_mods = {}
    for unit_id in initial_dict_player["rosterUnit"]:
        if not "equippedStatMod" in initial_dict_player["rosterUnit"][unit_id]:
            #no mod for this unit
            continue

        unit_mods = initial_dict_player["rosterUnit"][unit_id]["equippedStatMod"]
        initial_dict_player["rosterUnit"][unit_id]["equippedStatMod"] = {}
        for mod in unit_mods:
            mod_id = mod["id"]
            mod_defId = mod["definitionId"]
            mod_slot = mod_list[mod_defId]["slot"]
            initial_dict_player["rosterUnit"][unit_id]["equippedStatMod"][mod_slot] = mod_id
            initial_dict_player_mods[mod_id] = {"unit_id": unit_id, "slot": mod_slot}

    cur_dict_player = copy.deepcopy(initial_dict_player)
    cur_dict_player_mods = copy.deepcopy(initial_dict_player_mods)

    max_unallocated = 0
    for a in mod_allocations:
        #dbg_mod = "3hS3gxH7Q5mXpFu2oaNWZA"
        #print(cur_dict_player_mods[dbg_mod])
        # An allocation is something like
        # "on the unit PRINCESSLEIA, we need to use mods ID1, ID2, ID3"
        target_char_defId = a["unit_id"]
        target_char_id = cur_dict_player["rosterUnit"][target_char_defId]["id"]

        mods_to_add = [] # list of mod IDs to be added to this unit
        mods_to_remove = [] # list of mod IDs to be removed from this unit
        for allocated_mod_id in a["mods"]:
            # add the new mode to mods_to_add, then add the existing to mods_to_remove

            # First check if the target unit does not already have it
            current_mod_unit = cur_dict_player_mods[allocated_mod_id]["unit_id"]
            #print(target_char_defId)
            #print(allocated_mod_id)
            #print(current_mod_unit)
            mod_slot = cur_dict_player_mods[allocated_mod_id]["slot"]
            if current_mod_unit != target_char_defId:
                if not "equippedStatMod" in cur_dict_player["rosterUnit"][target_char_defId]:
                    cur_dict_player["rosterUnit"][target_char_defId]["equippedStatMod"] = {}

                #Look for potential mod to be removed before adding the new one
                if mod_slot in cur_dict_player["rosterUnit"][target_char_defId]["equippedStatMod"]:
                    previous_mod_id = cur_dict_player["rosterUnit"][target_char_defId]["equippedStatMod"][mod_slot]
                    mods_to_remove.append(previous_mod_id)
                    cur_dict_player_mods[previous_mod_id]["unit_id"] = None
                    del cur_dict_player["rosterUnit"][target_char_defId]["equippedStatMod"][mod_slot]

                #the allocated (new) mod has to be equipped on the target character
                # and removed from previous unit
                mods_to_add.append(allocated_mod_id)
                prev_unit = cur_dict_player_mods[allocated_mod_id]["unit_id"]
                if prev_unit != None:
                    del cur_dict_player["rosterUnit"][prev_unit]["equippedStatMod"][mod_slot]
                cur_dict_player_mods[allocated_mod_id]["unit_id"] = target_char_defId
                cur_dict_player["rosterUnit"][target_char_defId]["equippedStatMod"][mod_slot] = allocated_mod_id

        if len(mods_to_add) > 0:
            #write update request
            mods_txt = ""
            for id in mods_to_add:
                mods_txt += " +"+id
            for id in mods_to_remove:
                mods_txt += " -"+id
            print("python updateMods.py "+allyCode+" "+target_char_id+mods_txt+" #"+target_char_defId)
        elif len(mods_to_remove) > 0:
            print("ERR: des mods à retirer pour "+target_char_defId+" "+str(mods_to_remove)+" mais aucun à ajouter")
            sys.exit(1)

        #manage max size required in mod inventory
        unallocated_mods = [id for id in cur_dict_player_mods if cur_dict_player_mods[id]["unit_id"]==None]
        if len(unallocated_mods)>max_unallocated:
            max_unallocated = len(unallocated_mods)

    print("============\nMax unallocated: "+str(max_unallocated))

############################
# MAIN
############################
if __name__ == "__main__":
    #Need to have the dict_player, to get mod IDs
    initial_dict_player = json.load(open(sys.argv[2], 'r'))
    initial_dict_player = goutils.roster_from_list_to_dict(initial_dict_player)

    mod_allocations = get_mod_allocations_from_modoptimizer(sys.argv[1], initial_dict_player)
    allyCode = sys.argv[3]

    apply_mod_allocations(mod_allocations, allyCode, initial_dict_player)
