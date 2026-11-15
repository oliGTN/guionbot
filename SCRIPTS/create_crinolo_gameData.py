import json
try:
    from SCRIPTS.game_data_utils import load_game_data
except ModuleNotFoundError:  # Support direct execution: python SCRIPTS/script.py
    from game_data_utils import load_game_data
import sys

gameData_name = sys.argv[1]
gameData = dict(load_game_data(gameData_name))

gameDataCrinolo = {}

# list from dataBuilder.js
collections = [
          'equipment',
          'relicTierDefinition',
          'skill',
          'statModSet',
          'statProgression',
          'table',
          'units',
          'xpTable'
]

for c in collections:
    gameDataCrinolo = gameData[c]

    gameDataCrinolo_name = gameData_name[:-5]+"Crinolo_"+c+".json"
    fout = open(gameDataCrinolo_name, 'w')
    fout.write(json.dumps(gameDataCrinolo))
    fout.close()
