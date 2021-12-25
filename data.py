import json
import os

dict_raid_tiers = {}
dict_raid_tiers['Rancor (challenge)']=[41193988, 36425856, 39461352, 37943604]

dict_data={}
def get(filename):
    if filename in dict_data:
        return dict_data[filename]
    else:
        new_data = json.load(open("DATA"+os.path.sep+filename, "r"))
        dict_data[filename] = new_data
        return new_data
