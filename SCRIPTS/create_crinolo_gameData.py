import json
import sys

gameData_name = sys.argv[1]
gameData = json.load(open(gameData_name))

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
    gameDataCrinolo[c] = gameData[c]

gameDataCrinolo_name = gameData_name[:-5]+"Crinolo.json"
fout = open(gameDataCrinolo_name, 'w')
fout.write(json.dumps(gameDataCrinolo))
fout.close()
