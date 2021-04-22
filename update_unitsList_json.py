import sys
import json
import os

#####################################
# This script adapts the offcial file from SWGOH.HELP API
# It transfoms the initial list into a dictionary, with the unit_id as key
#####################################
unitsList = json.load(open('DATA'+os.path.sep+'unitsList.json', 'r'))

unitsList_dict = {}
for unit in unitsList:
    if (not ':' in unit['id']):
        if unit['id'] in unitsList_dict:
            print('WAR: double definition of '+unit['id'])
        unitsList_dict[unit['id']] = unit

fnew = open('DATA'+os.path.sep+'unitsList_dict.json', 'w')
fnew.write(json.dumps(unitsList_dict, sort_keys=True, indent=4))
fnew.close()
