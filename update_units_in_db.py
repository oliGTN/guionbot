import sys
import json
import os
import connect_mysql

unitsList = json.load(open('..\DATA'+os.path.sep+'unitsList.json', 'r'))

for unit in unitsList:
    # if (not ':' in unit['id']):
        # connect_mysql.update_unit(unit)

    if unit['id'] in ['ARMORER', 'THEMANDALORIANBESKARARMOR', 'DARKTROOPER']:
        print(unit['id'])
        connect_mysql.update_unit(unit)
