##########################################################
# This code takes as input the HTML from <div class="mods-list">
# extracted from mod optimizer (chrome, dev tab) in a file
# input 1: txt file with html content (one line)
# input 2: PLAYERS/bot_xxx.json
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
dict_alias = json.load(open("DATA/unitsAlias_dict.json", "r"))
mod_list = json.load(open("DATA/modList_dict.json", "r"))


modopti_parser = ModOptimizerListParser()
modopti_parser.feed(open(sys.argv[1], 'r').read())
allocations = modopti_parser.get_allocations()

initial_dict_player = json.load(open(sys.argv[2], 'r'))
initial_dict_player = goutils.roster_from_list_to_dict(initial_dict_player)
cur_dict_player = copy.deepcopy(initial_dict_player)

for a in allocations:
    #print("---------------------")
    target_char_name = a["character"]
    target_char_defId = dict_alias[target_char_name.lower()][1]
    target_char_id = initial_dict_player["rosterUnit"][target_char_defId]["id"]

    equipped_mods = {} #key: id, value: slot
    unequipped_mods = {} #key: id, value: char_defId
    for allocated_mod_shape in a["mods"]:
        allocated_mod = a["mods"][allocated_mod_shape]
        allocated_mod_slot = dict_slot_by_shape[allocated_mod_shape]

        source_char_name = allocated_mod["character"]
        source_char_defId = dict_alias[source_char_name.lower()][1]
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

        replacement_mod = char_mods[allocated_mod_slot]
        if    replacement_mod["pips"] != allocated_mod["pips"] \
           or replacement_mod["set"] != allocated_mod["set"]:
            print("\t"+allocated_mod_shape+": "+str(allocated_mod))
            print("\t\t"+str(replacement_mod))
            print("\t>>> ERREUR incohérence")
            sys.exit(1)

        allocated_mod["id"] = replacement_mod["id"]
        #print("\t"+allocated_mod_shape+": "+str(allocated_mod))

        # add the new mode to equipped_mods, then add the existing to unequipped_mods
        if not allocated_mod["color"].endswith("no-move"):
            equipped_mods[allocated_mod["id"]] = allocated_mod_slot

            unequipped_mods[allocated_mod["id"]] = source_char_defId

            #look for existing mod to be unequipped
            #print(cur_dict_player["rosterUnit"][target_char_defId])
            if "equippedStatMod" in cur_dict_player["rosterUnit"][target_char_defId]:
                for roster_mod in cur_dict_player["rosterUnit"][target_char_defId]["equippedStatMod"]:
                    if "slot" in roster_mod:
                        mod_slot = roster_mod["slot"]
                    else:
                        mod_defId = roster_mod["definitionId"] #string
                        mod_slot = mod_list[mod_defId]["slot"]
                    mod_id = roster_mod["id"]
                    if allocated_mod_slot == mod_slot:
                        unequipped_mods[mod_id] = target_char_defId

    #write update request
    mods_txt = ""
    for id in equipped_mods:
        mods_txt += " +"+id
    for id in unequipped_mods:
        #print(unequipped_mods[id]+" - "+target_char_defId)
        if unequipped_mods[id] == target_char_defId:
            mods_txt += " -"+id
    print("python updateMods.py 24ec0905bac61a77 "+target_char_id+mods_txt+" #"+target_char_name)


    #update current dict_player
    # remove unequipped mods from the target char
    # remove equipped mods from the source char
    for id in unequipped_mods:
        unit_id = unequipped_mods[id]

        if "equippedStatMod" in cur_dict_player["rosterUnit"][unit_id]:
            player_mods = cur_dict_player["rosterUnit"][unit_id]["equippedStatMod"].copy()
            for roster_mod in cur_dict_player["rosterUnit"][unit_id]["equippedStatMod"]:
                if roster_mod["id"]==id:
                    player_mods.remove(roster_mod)
        else:
            player_mods = []
        cur_dict_player["rosterUnit"][unit_id]["equippedStatMod"] = player_mods

    for id in equipped_mods:
        if not "equippedStatMod" in cur_dict_player["rosterUnit"][target_char_defId]:
            cur_dict_player["rosterUnit"][target_char_defId]["equippedStatMod"] = []
        cur_dict_player["rosterUnit"][target_char_defId]["equippedStatMod"].append({"id": id, "slot": equipped_mods[id]})


