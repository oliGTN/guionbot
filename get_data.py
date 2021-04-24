from swgohhelp import SWGOHhelp, settings
import sys
import json
import os

creds = settings(os.environ['SWGOHAPI_LOGIN'], os.environ['SWGOHAPI_PASSWORD'], '123', 'abc')
client = SWGOHhelp(creds)

for data_type in sys.argv[1:]:
	print('>Requesting data for type '+data_type+'...')
	data = client.get_data('data', data_type)

	# print('Dumping data in '+data_type+'.json...')
	# f = open('DATA'+os.path.sep+data_type+'.json', 'w')
	# json.dump(data, f)
	# f.close()

	print('Dumping data in '+data_type+'.json...')
	f = open('DATA'+os.path.sep+data_type+'.json', 'w')
	f.write(json.dumps(data, indent=4, sort_keys=True))
	f.close()



