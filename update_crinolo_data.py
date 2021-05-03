import requests
import os
import json

# Download file
url = 'https://swgoh-stat-calc.glitch.me/gameData.json'
r = requests.get(url, allow_redirects=True)

fcrinolo = open('DATA'+os.path.sep+'crinolo_gameData.json', 'wb')
fcrinolo.write(r.content)
fcrinolo.close()

# Create light file
fcrinolo = open('DATA'+os.path.sep+'crinolo_gameData.json', 'r')
crinolo_gameData = json.load(fcrinolo)

prev_list_characters_crinolo = json.load(open('DATA'+os.path.sep+'crinolo_gameData_light.json', 'r'))
list_characters_crinolo = list(crinolo_gameData['unitData'].keys())
fcrinolo_light = open('DATA'+os.path.sep+'crinolo_gameData_light.json', 'w')
fcrinolo_light.write(json.dumps(list_characters_crinolo))
fcrinolo_light.close()

# Display differences
for char in list_characters_crinolo:
    if not char in prev_list_characters_crinolo:
        print("NEW: "+char)
