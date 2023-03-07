import json
import os

dict_raid_tiers = {}
dict_raid_tiers['Rancor (challenge)']=[41193988, 36425856, 39461352, 37943604]

dict_tb={}
dict_tb["t04D"] = {"PhaseDuration": 129600000, "ZoneNames": {}, "ZonePositions": {}}
dict_tb["t04D"]["Name"] = "Geonosis Light Side"
dict_tb["t04D"]["Shortname"] = "GLS"
dict_tb["t04D"]["ZoneNames"]["top"] = "conflict01"
dict_tb["t04D"]["ZoneNames"]["mid"] = "conflict02"
dict_tb["t04D"]["ZoneNames"]["bot"] = "conflict03"
dict_tb["t04D"]["ZonePositions"]["top"] = 1
dict_tb["t04D"]["ZonePositions"]["mid"] = 2
dict_tb["t04D"]["ZonePositions"]["bot"] = 3
dict_tb["geonosis_republic_phase01_conflict01"] = {}
dict_tb["geonosis_republic_phase01_conflict01"]["Name"] = "GLS1-top"
dict_tb["geonosis_republic_phase01_conflict01"]["Type"] = "Ships"
dict_tb["geonosis_republic_phase01_conflict01"]["Scores"] = [42475000, 84950000, 141580000]
dict_tb["geonosis_republic_phase01_conflict01"]["Strikes"] = {}
dict_tb["geonosis_republic_phase01_conflict01"]["Strikes"]["strike01"] = [1, 523000]
dict_tb["geonosis_republic_phase01_conflict01"]["Coverts"] = {}
dict_tb["geonosis_republic_phase01_conflict02"] = {}
dict_tb["geonosis_republic_phase01_conflict02"]["Name"] = "GLS1-mid"
dict_tb["geonosis_republic_phase01_conflict02"]["Type"] = "Chars"
dict_tb["geonosis_republic_phase01_conflict02"]["Scores"] = [110240000, 166640000, 256370000]
dict_tb["geonosis_republic_phase01_conflict02"]["Strikes"] = {}
dict_tb["geonosis_republic_phase01_conflict02"]["Strikes"]["strike01"] = [4, 1155000]
dict_tb["geonosis_republic_phase01_conflict02"]["Strikes"]["strike02"] = [4, 1155000]
dict_tb["geonosis_republic_phase01_conflict02"]["Coverts"] = {}
dict_tb["geonosis_republic_phase01_conflict02"]["Coverts"]["covert01"] = [1]
dict_tb["geonosis_republic_phase01_conflict03"] = {}
dict_tb["geonosis_republic_phase01_conflict03"]["Name"] = "GLS1-bot"
dict_tb["geonosis_republic_phase01_conflict03"]["Type"] = "Chars"
dict_tb["geonosis_republic_phase01_conflict03"]["Scores"] = [86275000, 120425000, 179740000]
dict_tb["geonosis_republic_phase01_conflict03"]["Strikes"] = {}
dict_tb["geonosis_republic_phase01_conflict03"]["Strikes"]["strike01"] = [4, 1155000]
dict_tb["geonosis_republic_phase01_conflict03"]["Strikes"]["covert01"] = [4, 1501000]
dict_tb["geonosis_republic_phase01_conflict03"]["Coverts"] = {}
dict_tb["geonosis_republic_phase02_conflict01"] = {}
dict_tb["geonosis_republic_phase02_conflict01"]["Name"] = "GLS2-top"
dict_tb["geonosis_republic_phase02_conflict01"]["Type"] = "Ships"
dict_tb["geonosis_republic_phase02_conflict01"]["Scores"] = [71075000, 133535000, 215380000]
dict_tb["geonosis_republic_phase02_conflict01"]["Strikes"] = {}
dict_tb["geonosis_republic_phase02_conflict01"]["Strikes"]["strike01"] = [1, 900000]
dict_tb["geonosis_republic_phase02_conflict01"]["Coverts"] = {}
dict_tb["geonosis_republic_phase02_conflict01"]["Coverts"]["covert01"] = [1]
dict_tb["geonosis_republic_phase02_conflict02"] = {}
dict_tb["geonosis_republic_phase02_conflict02"]["Name"] = "GLS2-mid"
dict_tb["geonosis_republic_phase02_conflict02"]["Type"] = "Chars"
dict_tb["geonosis_republic_phase02_conflict02"]["Scores"] = [96200000, 174235000, 260055000]
dict_tb["geonosis_republic_phase02_conflict02"]["Strikes"] = {}
dict_tb["geonosis_republic_phase02_conflict02"]["Strikes"]["strike01"] = [4, 1377000]
dict_tb["geonosis_republic_phase02_conflict02"]["Strikes"]["strike02"] = [4, 1377000]
dict_tb["geonosis_republic_phase02_conflict02"]["Strikes"]["covert01"] = [4, 1790000]
dict_tb["geonosis_republic_phase02_conflict02"]["Coverts"] = {}
dict_tb["geonosis_republic_phase02_conflict03"] = {}
dict_tb["geonosis_republic_phase02_conflict03"]["Name"] = "GLS2-bot"
dict_tb["geonosis_republic_phase02_conflict03"]["Type"] = "Chars"
dict_tb["geonosis_republic_phase02_conflict03"]["Scores"] = [121030000, 217235000, 310335000]
dict_tb["geonosis_republic_phase02_conflict03"]["Strikes"] = {}
dict_tb["geonosis_republic_phase02_conflict03"]["Strikes"]["strike01"] = [4, 1377000]
dict_tb["geonosis_republic_phase02_conflict03"]["Strikes"]["strike02"] = [4, 1377000]
dict_tb["geonosis_republic_phase02_conflict03"]["Coverts"] = {}
dict_tb["geonosis_republic_phase02_conflict03"]["Coverts"]["covert01"] = [4, 1377000]
dict_tb["geonosis_republic_phase03_conflict01"] = {}
dict_tb["geonosis_republic_phase03_conflict01"]["Name"] = "GLS3-top"
dict_tb["geonosis_republic_phase03_conflict01"]["Type"] = "Ships"
dict_tb["geonosis_republic_phase03_conflict01"]["Scores"] = [91395000, 152325000, 217610000]
dict_tb["geonosis_republic_phase03_conflict01"]["Strikes"] = {}
dict_tb["geonosis_republic_phase03_conflict01"]["Strikes"]["strike01"] = [1, 1800000]
dict_tb["geonosis_republic_phase03_conflict01"]["Coverts"] = {}
dict_tb["geonosis_republic_phase03_conflict01"]["Coverts"]["covert01"] = [1]
dict_tb["geonosis_republic_phase03_conflict02"] = {}
dict_tb["geonosis_republic_phase03_conflict02"]["Name"] = "GLS3-mid"
dict_tb["geonosis_republic_phase03_conflict02"]["Type"] = "Chars"
dict_tb["geonosis_republic_phase03_conflict02"]["Scores"] = [132310000, 257065000, 378035000]
dict_tb["geonosis_republic_phase03_conflict02"]["Strikes"] = {}
dict_tb["geonosis_republic_phase03_conflict02"]["Strikes"]["strike01"] = [4, 1627500]
dict_tb["geonosis_republic_phase03_conflict02"]["Strikes"]["strike02"] = [4, 1627500]
dict_tb["geonosis_republic_phase03_conflict02"]["Strikes"]["covert01"] = [4, 2115750]
dict_tb["geonosis_republic_phase03_conflict02"]["Coverts"] = {}
dict_tb["geonosis_republic_phase03_conflict03"] = {}
dict_tb["geonosis_republic_phase03_conflict03"]["Name"] = "GLS3-bot"
dict_tb["geonosis_republic_phase03_conflict03"]["Type"] = "Chars"
dict_tb["geonosis_republic_phase03_conflict03"]["Scores"] = [110615000, 165925000, 221230000]
dict_tb["geonosis_republic_phase03_conflict03"]["Strikes"] = {}
dict_tb["geonosis_republic_phase03_conflict03"]["Strikes"]["strike01"] = [4, 1627500]
dict_tb["geonosis_republic_phase03_conflict03"]["Coverts"] = {}
dict_tb["geonosis_republic_phase03_conflict03"]["Coverts"]["covert01"] = [4]
dict_tb["geonosis_republic_phase04_conflict01"] = {}
dict_tb["geonosis_republic_phase04_conflict01"]["Name"] = "GLS4-top"
dict_tb["geonosis_republic_phase04_conflict01"]["Type"] = "Ships"
dict_tb["geonosis_republic_phase04_conflict01"]["Scores"] = [122490000, 340255000, 453670000]
dict_tb["geonosis_republic_phase04_conflict01"]["Strikes"] = {}
dict_tb["geonosis_republic_phase04_conflict01"]["Strikes"]["strike01"] = [1, 2750000]
dict_tb["geonosis_republic_phase04_conflict01"]["Coverts"] = {}
dict_tb["geonosis_republic_phase04_conflict01"]["Coverts"]["covert01"] = [1]
dict_tb["geonosis_republic_phase04_conflict02"] = {}
dict_tb["geonosis_republic_phase04_conflict02"]["Name"] = "GLS4-mid"
dict_tb["geonosis_republic_phase04_conflict02"]["Type"] = "Chars"
dict_tb["geonosis_republic_phase04_conflict02"]["Scores"] = [152945000, 270930000, 436980000]
dict_tb["geonosis_republic_phase04_conflict02"]["Strikes"] = {}
dict_tb["geonosis_republic_phase04_conflict02"]["Strikes"]["strike01"] = [4, 1837500]
dict_tb["geonosis_republic_phase04_conflict02"]["Strikes"]["strike02"] = [4, 1837500]
dict_tb["geonosis_republic_phase04_conflict02"]["Coverts"] = {}
dict_tb["geonosis_republic_phase04_conflict02"]["Coverts"]["covert01"] = [4]
dict_tb["geonosis_republic_phase04_conflict03"] = {}
dict_tb["geonosis_republic_phase04_conflict03"]["Name"] = "GLS4-bot"
dict_tb["geonosis_republic_phase04_conflict03"]["Type"] = "Chars"
dict_tb["geonosis_republic_phase04_conflict03"]["Scores"] = [117510000, 268600000, 335750000]
dict_tb["geonosis_republic_phase04_conflict03"]["Strikes"] = {}
dict_tb["geonosis_republic_phase04_conflict03"]["Strikes"]["strike01"] = [4, 1837500]
dict_tb["geonosis_republic_phase04_conflict03"]["Strikes"]["strike02"] = [4, 1837500]
dict_tb["geonosis_republic_phase04_conflict03"]["Strikes"]["covert01"] = [4, 2388750]
dict_tb["geonosis_republic_phase04_conflict03"]["Coverts"] = {}

dict_tb["t05D"] = {"PhaseDuration": 86400000, "ZoneNames": {}, "ZonePositions": {}}
dict_tb["t05D"]["Name"] = "Rise of the Empire"
dict_tb["t05D"]["Shortname"] = "ROTE"
dict_tb["t05D"]["ZoneNames"]["DS"] = "conflict02"
dict_tb["t05D"]["ZoneNames"]["MS"] = "conflict03"
dict_tb["t05D"]["ZoneNames"]["LS"] = "conflict01"
dict_tb["t05D"]["ZonePositions"]["DS"] = 1
dict_tb["t05D"]["ZonePositions"]["MS"] = 2
dict_tb["t05D"]["ZonePositions"]["LS"] = 3
dict_tb["tb3_mixed_phase01_conflict01"] = {}
dict_tb["tb3_mixed_phase01_conflict01"]["Name"] = "ROTE1-LS"
dict_tb["tb3_mixed_phase01_conflict01"]["Type"] = "Mix"
dict_tb["tb3_mixed_phase01_conflict01"]["Scores"] = [116406250, 186250000, 248333333]
dict_tb["tb3_mixed_phase01_conflict01"]["Strikes"] = {}
dict_tb["tb3_mixed_phase01_conflict01"]["Strikes"]["strike01"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict01"]["Strikes"]["strike02"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict01"]["Strikes"]["strike03"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict01"]["Strikes"]["strike04"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict01"]["Strikes"]["strike05"] = [1, 400000]
dict_tb["tb3_mixed_phase01_conflict01"]["Coverts"] = {}
dict_tb["tb3_mixed_phase01_conflict02"] = {}
dict_tb["tb3_mixed_phase01_conflict02"]["Name"] = "ROTE1-DS"
dict_tb["tb3_mixed_phase01_conflict02"]["Type"] = "Mix"
dict_tb["tb3_mixed_phase01_conflict02"]["Scores"] = [116406250, 186250000, 248333333]
dict_tb["tb3_mixed_phase01_conflict02"]["Strikes"] = {}
dict_tb["tb3_mixed_phase01_conflict02"]["Strikes"]["strike01"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict02"]["Strikes"]["strike02"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict02"]["Strikes"]["strike03"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict02"]["Strikes"]["strike04"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict02"]["Strikes"]["strike05"] = [1, 400000]
dict_tb["tb3_mixed_phase01_conflict02"]["Coverts"] = {}
dict_tb["tb3_mixed_phase01_conflict03"] = {}
dict_tb["tb3_mixed_phase01_conflict03"]["Name"] = "ROTE1-MS"
dict_tb["tb3_mixed_phase01_conflict03"]["Type"] = "Mix"
dict_tb["tb3_mixed_phase01_conflict03"]["Scores"] = [111718750, 178750000, 238333333]
dict_tb["tb3_mixed_phase01_conflict03"]["Strikes"] = {}
dict_tb["tb3_mixed_phase01_conflict03"]["Strikes"]["strike01"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict03"]["Strikes"]["strike02"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict03"]["Strikes"]["strike03"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict03"]["Strikes"]["strike04"] = [1, 400000]
dict_tb["tb3_mixed_phase01_conflict03"]["Coverts"] = {}
dict_tb["tb3_mixed_phase01_conflict03"]["Coverts"]["covert01"] = [1]

dict_tb["tb3_mixed_phase02_conflict01"] = {}
dict_tb["tb3_mixed_phase02_conflict01"]["Name"] = "ROTE2-LS"
dict_tb["tb3_mixed_phase02_conflict01"]["Type"] = "Mix"
dict_tb["tb3_mixed_phase02_conflict01"]["Scores"] = [142265625, 227625000, 303500000]
dict_tb["tb3_mixed_phase02_conflict01"]["Strikes"] = {}
dict_tb["tb3_mixed_phase02_conflict01"]["Strikes"]["strike01"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict01"]["Strikes"]["strike02"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict01"]["Strikes"]["strike03"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict01"]["Strikes"]["strike04"] = [1, 500000]
dict_tb["tb3_mixed_phase02_conflict01"]["Coverts"] = {}
dict_tb["tb3_mixed_phase02_conflict02"] = {}
dict_tb["tb3_mixed_phase02_conflict02"]["Name"] = "ROTE2-DS"
dict_tb["tb3_mixed_phase02_conflict02"]["Type"] = "Mix"
dict_tb["tb3_mixed_phase02_conflict02"]["Scores"] = [148125000, 237000000, 316000000]
dict_tb["tb3_mixed_phase02_conflict02"]["Strikes"] = {}
dict_tb["tb3_mixed_phase02_conflict02"]["Strikes"]["strike01"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict02"]["Strikes"]["strike02"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict02"]["Strikes"]["strike03"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict02"]["Strikes"]["strike04"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict02"]["Strikes"]["strike05"] = [1, 500000]
dict_tb["tb3_mixed_phase02_conflict02"]["Coverts"] = {}
dict_tb["tb3_mixed_phase02_conflict03"] = {}
dict_tb["tb3_mixed_phase02_conflict03"]["Name"] = "ROTE2-MS"
dict_tb["tb3_mixed_phase02_conflict03"]["Type"] = "Mix"
dict_tb["tb3_mixed_phase02_conflict03"]["Scores"] = [148125000, 237000000, 316000000]
dict_tb["tb3_mixed_phase02_conflict03"]["Strikes"] = {}
dict_tb["tb3_mixed_phase02_conflict03"]["Strikes"]["strike01"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict03"]["Strikes"]["strike02"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict03"]["Strikes"]["strike03"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict03"]["Strikes"]["strike04"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict03"]["Strikes"]["strike05"] = [1, 500000]
dict_tb["tb3_mixed_phase02_conflict03"]["Coverts"] = {}

dict_tb["tb3_mixed_phase03_conflict01"] = {}
dict_tb["tb3_mixed_phase03_conflict01"]["Name"] = "ROTE3-LS"
dict_tb["tb3_mixed_phase03_conflict01"]["Type"] = "Mix"
dict_tb["tb3_mixed_phase03_conflict01"]["Scores"] = [190953126, 305525000, 407366667]
dict_tb["tb3_mixed_phase03_conflict01"]["Strikes"] = {}
dict_tb["tb3_mixed_phase03_conflict01"]["Strikes"]["strike01"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict01"]["Strikes"]["strike02"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict01"]["Strikes"]["strike03"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict01"]["Strikes"]["strike04"] = [1, 682500]
dict_tb["tb3_mixed_phase03_conflict01"]["Coverts"] = {}
dict_tb["tb3_mixed_phase03_conflict02"] = {}
dict_tb["tb3_mixed_phase03_conflict02"]["Name"] = "ROTE3-DS"
dict_tb["tb3_mixed_phase03_conflict02"]["Type"] = "Mix"
dict_tb["tb3_mixed_phase03_conflict02"]["Scores"] = [158960938, 254337500, 339116667]
dict_tb["tb3_mixed_phase03_conflict02"]["Strikes"] = {}
dict_tb["tb3_mixed_phase03_conflict02"]["Strikes"]["strike01"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict02"]["Strikes"]["strike02"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict02"]["Strikes"]["strike03"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict02"]["Strikes"]["strike04"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict02"]["Coverts"] = {}
dict_tb["tb3_mixed_phase03_conflict03"] = {}
dict_tb["tb3_mixed_phase03_conflict03"]["Name"] = "ROTE3-MS"
dict_tb["tb3_mixed_phase03_conflict03"]["Type"] = "Mix"
dict_tb["tb3_mixed_phase03_conflict03"]["Scores"] = [190953125, 305525000, 407366667]
dict_tb["tb3_mixed_phase03_conflict03"]["Strikes"] = {}
dict_tb["tb3_mixed_phase03_conflict03"]["Strikes"]["strike01"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict03"]["Strikes"]["strike03"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict03"]["Strikes"]["strike04"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict03"]["Strikes"]["strike05"] = [1, 682500]
dict_tb["tb3_mixed_phase03_conflict03"]["Coverts"] = {}
dict_tb["tb3_mixed_phase03_conflict03"]["Coverts"]["covert01"] = [1]

dict_data={}
def get(filename):
    if filename in dict_data:
        return dict_data[filename]
    else:
        new_data = json.load(open("DATA"+os.path.sep+filename, "r"))
        dict_data[filename] = new_data
        return new_data

def reset_data():
    dict_data={}
