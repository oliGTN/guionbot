from swgohhelp import SWGOHhelp, settings
import sys
import json
import os
import config

creds = settings(config.SWGOHAPI_LOGIN, config.SWGOHAPI_PASSWORD, '123', 'abc')
client = SWGOHhelp(creds)

data_type = sys.argv[1]
if len(sys.argv)>2:
    language = sys.argv[2] #FRE_FR, ENG_US
else:
    language = 'FRE_FR'

print('>Requesting data for type '+data_type+'...')
data = client.get_data('data', data_type, language)

if language != 'FRE_FR':
    json_name = 'DATA'+os.path.sep+data_type+'_'+language+'.json'
else:
    json_name = 'DATA'+os.path.sep+data_type+'.json'

print('Dumping data in '+json_name+'...')
f = open(json_name, 'w')
f.write(json.dumps(data, indent=4, sort_keys=True))
f.close()



