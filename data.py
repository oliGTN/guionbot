import json
import os

dict_raid_tiers = {}
dict_raid_tiers['Rancor (challenge)']=[41193988, 36425856, 39461352, 37943604]

dict_tb={}
dict_tb["GLS"] = {"id": "t04D"}
dict_tb["t04D"] = {"PhaseDuration": 129600000, "zoneNames": {}, "zonePositions": {}, "maxRound": 4}
dict_tb["t04D"]["name"] = "Geonosis Light Side"
dict_tb["t04D"]["shortname"] = "GLS"
dict_tb["t04D"]["zoneNames"]["top"] = "conflict01"
dict_tb["t04D"]["zoneNames"]["mid"] = "conflict02"
dict_tb["t04D"]["zoneNames"]["bot"] = "conflict03"
dict_tb["t04D"]["zonePositions"]["top"] = 1
dict_tb["t04D"]["zonePositions"]["mid"] = 2
dict_tb["t04D"]["zonePositions"]["bot"] = 3
dict_tb["t04D"]["prefix"] = "geonosis_republic"
dict_tb["geonosis_republic_phase01_conflict01"] = {}
dict_tb["geonosis_republic_phase01_conflict01"]["name"] = "GLS1-top"
dict_tb["geonosis_republic_phase01_conflict01"]["type"] = "ships"
dict_tb["geonosis_republic_phase01_conflict01"]["scores"] = [42475000, 84950000, 141580000]
dict_tb["geonosis_republic_phase01_conflict01"]["strikes"] = {}
dict_tb["geonosis_republic_phase01_conflict01"]["strikes"]["strike01"] = [1, 523000]
dict_tb["geonosis_republic_phase01_conflict01"]["coverts"] = {}
dict_tb["geonosis_republic_phase01_conflict02"] = {}
dict_tb["geonosis_republic_phase01_conflict02"]["name"] = "GLS1-mid"
dict_tb["geonosis_republic_phase01_conflict02"]["type"] = "chars"
dict_tb["geonosis_republic_phase01_conflict02"]["scores"] = [110240000, 166640000, 256370000]
dict_tb["geonosis_republic_phase01_conflict02"]["strikes"] = {}
dict_tb["geonosis_republic_phase01_conflict02"]["strikes"]["strike01"] = [4, 1155000]
dict_tb["geonosis_republic_phase01_conflict02"]["strikes"]["strike02"] = [4, 1155000]
dict_tb["geonosis_republic_phase01_conflict02"]["coverts"] = {}
dict_tb["geonosis_republic_phase01_conflict02"]["coverts"]["covert01"] = [1]
dict_tb["geonosis_republic_phase01_conflict03"] = {}
dict_tb["geonosis_republic_phase01_conflict03"]["name"] = "GLS1-bot"
dict_tb["geonosis_republic_phase01_conflict03"]["type"] = "chars"
dict_tb["geonosis_republic_phase01_conflict03"]["scores"] = [86275000, 120425000, 179740000]
dict_tb["geonosis_republic_phase01_conflict03"]["strikes"] = {}
dict_tb["geonosis_republic_phase01_conflict03"]["strikes"]["strike01"] = [4, 1155000]
dict_tb["geonosis_republic_phase01_conflict03"]["strikes"]["covert01"] = [4, 1501000]
dict_tb["geonosis_republic_phase01_conflict03"]["coverts"] = {}
dict_tb["geonosis_republic_phase02_conflict01"] = {}
dict_tb["geonosis_republic_phase02_conflict01"]["name"] = "GLS2-top"
dict_tb["geonosis_republic_phase02_conflict01"]["type"] = "ships"
dict_tb["geonosis_republic_phase02_conflict01"]["scores"] = [71075000, 133535000, 215380000]
dict_tb["geonosis_republic_phase02_conflict01"]["strikes"] = {}
dict_tb["geonosis_republic_phase02_conflict01"]["strikes"]["strike01"] = [1, 900000]
dict_tb["geonosis_republic_phase02_conflict01"]["coverts"] = {}
dict_tb["geonosis_republic_phase02_conflict01"]["coverts"]["covert01"] = [1]
dict_tb["geonosis_republic_phase02_conflict02"] = {}
dict_tb["geonosis_republic_phase02_conflict02"]["name"] = "GLS2-mid"
dict_tb["geonosis_republic_phase02_conflict02"]["type"] = "chars"
dict_tb["geonosis_republic_phase02_conflict02"]["scores"] = [96200000, 174235000, 260055000]
dict_tb["geonosis_republic_phase02_conflict02"]["strikes"] = {}
dict_tb["geonosis_republic_phase02_conflict02"]["strikes"]["strike01"] = [4, 1377000]
dict_tb["geonosis_republic_phase02_conflict02"]["strikes"]["strike02"] = [4, 1377000]
dict_tb["geonosis_republic_phase02_conflict02"]["strikes"]["covert01"] = [4, 1790000]
dict_tb["geonosis_republic_phase02_conflict02"]["coverts"] = {}
dict_tb["geonosis_republic_phase02_conflict03"] = {}
dict_tb["geonosis_republic_phase02_conflict03"]["name"] = "GLS2-bot"
dict_tb["geonosis_republic_phase02_conflict03"]["type"] = "chars"
dict_tb["geonosis_republic_phase02_conflict03"]["scores"] = [121030000, 217235000, 310335000]
dict_tb["geonosis_republic_phase02_conflict03"]["strikes"] = {}
dict_tb["geonosis_republic_phase02_conflict03"]["strikes"]["strike01"] = [4, 1377000]
dict_tb["geonosis_republic_phase02_conflict03"]["strikes"]["strike02"] = [4, 1377000]
dict_tb["geonosis_republic_phase02_conflict03"]["coverts"] = {}
dict_tb["geonosis_republic_phase02_conflict03"]["coverts"]["covert01"] = [4, 1377000]
dict_tb["geonosis_republic_phase03_conflict01"] = {}
dict_tb["geonosis_republic_phase03_conflict01"]["name"] = "GLS3-top"
dict_tb["geonosis_republic_phase03_conflict01"]["type"] = "ships"
dict_tb["geonosis_republic_phase03_conflict01"]["scores"] = [91395000, 152325000, 217610000]
dict_tb["geonosis_republic_phase03_conflict01"]["strikes"] = {}
dict_tb["geonosis_republic_phase03_conflict01"]["strikes"]["strike01"] = [1, 1800000]
dict_tb["geonosis_republic_phase03_conflict01"]["coverts"] = {}
dict_tb["geonosis_republic_phase03_conflict01"]["coverts"]["covert01"] = [1]
dict_tb["geonosis_republic_phase03_conflict02"] = {}
dict_tb["geonosis_republic_phase03_conflict02"]["name"] = "GLS3-mid"
dict_tb["geonosis_republic_phase03_conflict02"]["type"] = "chars"
dict_tb["geonosis_republic_phase03_conflict02"]["scores"] = [132310000, 257065000, 378035000]
dict_tb["geonosis_republic_phase03_conflict02"]["strikes"] = {}
dict_tb["geonosis_republic_phase03_conflict02"]["strikes"]["strike01"] = [4, 1627500]
dict_tb["geonosis_republic_phase03_conflict02"]["strikes"]["strike02"] = [4, 1627500]
dict_tb["geonosis_republic_phase03_conflict02"]["strikes"]["covert01"] = [4, 2115750]
dict_tb["geonosis_republic_phase03_conflict02"]["coverts"] = {}
dict_tb["geonosis_republic_phase03_conflict03"] = {}
dict_tb["geonosis_republic_phase03_conflict03"]["name"] = "GLS3-bot"
dict_tb["geonosis_republic_phase03_conflict03"]["type"] = "chars"
dict_tb["geonosis_republic_phase03_conflict03"]["scores"] = [110615000, 165925000, 221230000]
dict_tb["geonosis_republic_phase03_conflict03"]["strikes"] = {}
dict_tb["geonosis_republic_phase03_conflict03"]["strikes"]["strike01"] = [4, 1627500]
dict_tb["geonosis_republic_phase03_conflict03"]["coverts"] = {}
dict_tb["geonosis_republic_phase03_conflict03"]["coverts"]["covert01"] = [4]
dict_tb["geonosis_republic_phase04_conflict01"] = {}
dict_tb["geonosis_republic_phase04_conflict01"]["name"] = "GLS4-top"
dict_tb["geonosis_republic_phase04_conflict01"]["type"] = "ships"
dict_tb["geonosis_republic_phase04_conflict01"]["scores"] = [122490000, 340255000, 453670000]
dict_tb["geonosis_republic_phase04_conflict01"]["strikes"] = {}
dict_tb["geonosis_republic_phase04_conflict01"]["strikes"]["strike01"] = [1, 2750000]
dict_tb["geonosis_republic_phase04_conflict01"]["coverts"] = {}
dict_tb["geonosis_republic_phase04_conflict01"]["coverts"]["covert01"] = [1]
dict_tb["geonosis_republic_phase04_conflict02"] = {}
dict_tb["geonosis_republic_phase04_conflict02"]["name"] = "GLS4-mid"
dict_tb["geonosis_republic_phase04_conflict02"]["type"] = "chars"
dict_tb["geonosis_republic_phase04_conflict02"]["scores"] = [152945000, 270930000, 436980000]
dict_tb["geonosis_republic_phase04_conflict02"]["strikes"] = {}
dict_tb["geonosis_republic_phase04_conflict02"]["strikes"]["strike01"] = [4, 1837500]
dict_tb["geonosis_republic_phase04_conflict02"]["strikes"]["strike02"] = [4, 1837500]
dict_tb["geonosis_republic_phase04_conflict02"]["coverts"] = {}
dict_tb["geonosis_republic_phase04_conflict02"]["coverts"]["covert01"] = [4]
dict_tb["geonosis_republic_phase04_conflict03"] = {}
dict_tb["geonosis_republic_phase04_conflict03"]["name"] = "GLS4-bot"
dict_tb["geonosis_republic_phase04_conflict03"]["type"] = "chars"
dict_tb["geonosis_republic_phase04_conflict03"]["scores"] = [117510000, 268600000, 335750000]
dict_tb["geonosis_republic_phase04_conflict03"]["strikes"] = {}
dict_tb["geonosis_republic_phase04_conflict03"]["strikes"]["strike01"] = [4, 1837500]
dict_tb["geonosis_republic_phase04_conflict03"]["strikes"]["strike02"] = [4, 1837500]
dict_tb["geonosis_republic_phase04_conflict03"]["strikes"]["covert01"] = [4, 2388750]
dict_tb["geonosis_republic_phase04_conflict03"]["coverts"] = {}

dict_tb["ROTE"] = {"id": "t05D"}
dict_tb["t05D"] = {"PhaseDuration": 86400000, "zoneNames": {}, "zonePositions": {}, "maxRound": 6}
dict_tb["t05D"]["name"] = "Rise of the Empire"
dict_tb["t05D"]["shortname"] = "ROTE"
dict_tb["t05D"]["zoneNames"]["DS"] = "conflict02"
dict_tb["t05D"]["zoneNames"]["MS"] = "conflict03"
dict_tb["t05D"]["zoneNames"]["LS"] = "conflict01"
dict_tb["t05D"]["zonePositions"]["DS"] = 1
dict_tb["t05D"]["zonePositions"]["MS"] = 2
dict_tb["t05D"]["zonePositions"]["LS"] = 3
dict_tb["t05D"]["prefix"] = "tb3_mixed"
dict_tb["tb3_mixed_phase01_conflict01"] = {}
dict_tb["tb3_mixed_phase01_conflict01"]["name"] = "ROTE1-LS"
dict_tb["tb3_mixed_phase01_conflict01"]["type"] = "mix"
dict_tb["tb3_mixed_phase01_conflict01"]["scores"] = [116406250, 186250000, 248333333]
dict_tb["tb3_mixed_phase01_conflict01"]["strikes"] = {}
dict_tb["tb3_mixed_phase01_conflict01"]["strikes"]["strike01"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict01"]["strikes"]["strike02"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict01"]["strikes"]["strike03"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict01"]["strikes"]["strike04"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict01"]["strikes"]["strike05"] = [1, 400000]
dict_tb["tb3_mixed_phase01_conflict01"]["coverts"] = {}
dict_tb["tb3_mixed_phase01_conflict02"] = {}
dict_tb["tb3_mixed_phase01_conflict02"]["name"] = "ROTE1-DS"
dict_tb["tb3_mixed_phase01_conflict02"]["type"] = "mix"
dict_tb["tb3_mixed_phase01_conflict02"]["scores"] = [116406250, 186250000, 248333333]
dict_tb["tb3_mixed_phase01_conflict02"]["strikes"] = {}
dict_tb["tb3_mixed_phase01_conflict02"]["strikes"]["strike01"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict02"]["strikes"]["strike02"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict02"]["strikes"]["strike03"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict02"]["strikes"]["strike04"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict02"]["strikes"]["strike05"] = [1, 400000]
dict_tb["tb3_mixed_phase01_conflict02"]["coverts"] = {}
dict_tb["tb3_mixed_phase01_conflict03"] = {}
dict_tb["tb3_mixed_phase01_conflict03"]["name"] = "ROTE1-MS"
dict_tb["tb3_mixed_phase01_conflict03"]["type"] = "mix"
dict_tb["tb3_mixed_phase01_conflict03"]["scores"] = [111718750, 178750000, 238333333]
dict_tb["tb3_mixed_phase01_conflict03"]["strikes"] = {}
dict_tb["tb3_mixed_phase01_conflict03"]["strikes"]["strike01"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict03"]["strikes"]["strike02"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict03"]["strikes"]["strike03"] = [2, 200000]
dict_tb["tb3_mixed_phase01_conflict03"]["strikes"]["strike04"] = [1, 400000]
dict_tb["tb3_mixed_phase01_conflict03"]["coverts"] = {}
dict_tb["tb3_mixed_phase01_conflict03"]["coverts"]["covert01"] = [1]

dict_tb["tb3_mixed_phase02_conflict01"] = {}
dict_tb["tb3_mixed_phase02_conflict01"]["name"] = "ROTE2-LS"
dict_tb["tb3_mixed_phase02_conflict01"]["type"] = "mix"
dict_tb["tb3_mixed_phase02_conflict01"]["scores"] = [142265625, 227625000, 303500000]
dict_tb["tb3_mixed_phase02_conflict01"]["strikes"] = {}
dict_tb["tb3_mixed_phase02_conflict01"]["strikes"]["strike01"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict01"]["strikes"]["strike02"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict01"]["strikes"]["strike03"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict01"]["strikes"]["strike04"] = [1, 500000]
dict_tb["tb3_mixed_phase02_conflict01"]["coverts"] = {}
dict_tb["tb3_mixed_phase02_conflict02"] = {}
dict_tb["tb3_mixed_phase02_conflict02"]["name"] = "ROTE2-DS"
dict_tb["tb3_mixed_phase02_conflict02"]["type"] = "mix"
dict_tb["tb3_mixed_phase02_conflict02"]["scores"] = [148125000, 237000000, 316000000]
dict_tb["tb3_mixed_phase02_conflict02"]["strikes"] = {}
dict_tb["tb3_mixed_phase02_conflict02"]["strikes"]["strike01"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict02"]["strikes"]["strike02"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict02"]["strikes"]["strike03"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict02"]["strikes"]["strike04"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict02"]["strikes"]["strike05"] = [1, 500000]
dict_tb["tb3_mixed_phase02_conflict02"]["coverts"] = {}
dict_tb["tb3_mixed_phase02_conflict03"] = {}
dict_tb["tb3_mixed_phase02_conflict03"]["name"] = "ROTE2-MS"
dict_tb["tb3_mixed_phase02_conflict03"]["type"] = "mix"
dict_tb["tb3_mixed_phase02_conflict03"]["scores"] = [148125000, 237000000, 316000000]
dict_tb["tb3_mixed_phase02_conflict03"]["strikes"] = {}
dict_tb["tb3_mixed_phase02_conflict03"]["strikes"]["strike01"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict03"]["strikes"]["strike02"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict03"]["strikes"]["strike03"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict03"]["strikes"]["strike04"] = [2, 250000]
dict_tb["tb3_mixed_phase02_conflict03"]["strikes"]["strike05"] = [1, 500000]
dict_tb["tb3_mixed_phase02_conflict03"]["coverts"] = {}

dict_tb["tb3_mixed_phase03_conflict01"] = {}
dict_tb["tb3_mixed_phase03_conflict01"]["name"] = "ROTE3-LS"
dict_tb["tb3_mixed_phase03_conflict01"]["type"] = "mix"
dict_tb["tb3_mixed_phase03_conflict01"]["scores"] = [190953126, 305525000, 407366667]
dict_tb["tb3_mixed_phase03_conflict01"]["strikes"] = {}
dict_tb["tb3_mixed_phase03_conflict01"]["strikes"]["strike01"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict01"]["strikes"]["strike02"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict01"]["strikes"]["strike03"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict01"]["strikes"]["strike04"] = [1, 682500]
dict_tb["tb3_mixed_phase03_conflict01"]["coverts"] = {}
dict_tb["tb3_mixed_phase03_conflict01_bonus"] = {}
dict_tb["tb3_mixed_phase03_conflict01_bonus"]["name"] = "ROTE3-LSb"
dict_tb["tb3_mixed_phase03_conflict01_bonus"]["type"] = "mix"
dict_tb["tb3_mixed_phase03_conflict01_bonus"]["scores"] = [143589583, 229743333, 287179167]
dict_tb["tb3_mixed_phase03_conflict01_bonus"]["strikes"] = {}
dict_tb["tb3_mixed_phase03_conflict01_bonus"]["strikes"]["strike01"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict01_bonus"]["strikes"]["strike02"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict01_bonus"]["strikes"]["strike03"] = [2, 1023750]
dict_tb["tb3_mixed_phase03_conflict01_bonus"]["strikes"]["strike04"] = [1, 682500]
dict_tb["tb3_mixed_phase03_conflict01_bonus"]["coverts"] = {}
dict_tb["tb3_mixed_phase03_conflict02"] = {}
dict_tb["tb3_mixed_phase03_conflict02"]["name"] = "ROTE3-DS"
dict_tb["tb3_mixed_phase03_conflict02"]["type"] = "mix"
dict_tb["tb3_mixed_phase03_conflict02"]["scores"] = [158960938, 254337500, 339116667]
dict_tb["tb3_mixed_phase03_conflict02"]["strikes"] = {}
dict_tb["tb3_mixed_phase03_conflict02"]["strikes"]["strike01"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict02"]["strikes"]["strike02"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict02"]["strikes"]["strike03"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict02"]["strikes"]["strike04"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict02"]["coverts"] = {}
dict_tb["tb3_mixed_phase03_conflict03"] = {}
dict_tb["tb3_mixed_phase03_conflict03"]["name"] = "ROTE3-MS"
dict_tb["tb3_mixed_phase03_conflict03"]["type"] = "mix"
dict_tb["tb3_mixed_phase03_conflict03"]["scores"] = [190953125, 305525000, 407366667]
dict_tb["tb3_mixed_phase03_conflict03"]["strikes"] = {}
dict_tb["tb3_mixed_phase03_conflict03"]["strikes"]["strike01"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict03"]["strikes"]["strike03"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict03"]["strikes"]["strike04"] = [2, 341250]
dict_tb["tb3_mixed_phase03_conflict03"]["strikes"]["strike05"] = [1, 682500]
dict_tb["tb3_mixed_phase03_conflict03"]["coverts"] = {}
dict_tb["tb3_mixed_phase03_conflict03"]["coverts"]["covert01"] = [1]

dict_tb["tb3_mixed_phase04_conflict01"] = {}
dict_tb["tb3_mixed_phase04_conflict01"]["name"] = "ROTE4-LS"
dict_tb["tb3_mixed_phase04_conflict01"]["type"] = "mix"
dict_tb["tb3_mixed_phase04_conflict01"]["scores"] = [246742558, 419987333, 524984167]
dict_tb["tb3_mixed_phase04_conflict01"]["strikes"] = {}
dict_tb["tb3_mixed_phase04_conflict01"]["strikes"]["strike01"] = [2, 493594]
dict_tb["tb3_mixed_phase04_conflict01"]["strikes"]["strike02"] = [2, 493594]
dict_tb["tb3_mixed_phase04_conflict01"]["strikes"]["strike03"] = [2, 493594]
dict_tb["tb3_mixed_phase04_conflict01"]["strikes"]["strike04"] = [1, 987188]
dict_tb["tb3_mixed_phase04_conflict01"]["strikes"]["specialmission"] = [1, 0]
dict_tb["tb3_mixed_phase04_conflict01"]["coverts"] = {}
dict_tb["tb3_mixed_phase04_conflict02"] = {}
dict_tb["tb3_mixed_phase04_conflict02"]["name"] = "ROTE4-DS"
dict_tb["tb3_mixed_phase04_conflict02"]["type"] = "mix"
dict_tb["tb3_mixed_phase04_conflict02"]["scores"] = [235143105, 400243583, 500304479]
dict_tb["tb3_mixed_phase04_conflict02"]["strikes"] = {}
dict_tb["tb3_mixed_phase04_conflict02"]["strikes"]["strike01"] = [2, 493594]
dict_tb["tb3_mixed_phase04_conflict02"]["strikes"]["strike02"] = [2, 493594]
dict_tb["tb3_mixed_phase04_conflict02"]["strikes"]["strike03"] = [2, 493594]
dict_tb["tb3_mixed_phase04_conflict02"]["strikes"]["strike04"] = [1, 987188]
dict_tb["tb3_mixed_phase04_conflict02"]["coverts"] = {}
dict_tb["tb3_mixed_phase04_conflict02"]["coverts"]["covert01"] = [1]
dict_tb["tb3_mixed_phase04_conflict03"] = {}
dict_tb["tb3_mixed_phase04_conflict03"]["name"] = "ROTE4-MS"
dict_tb["tb3_mixed_phase04_conflict03"]["type"] = "mix"
dict_tb["tb3_mixed_phase04_conflict03"]["scores"] = [235143105, 400243583, 500304479]
dict_tb["tb3_mixed_phase04_conflict03"]["strikes"] = {}
dict_tb["tb3_mixed_phase04_conflict03"]["strikes"]["strike01"] = [2, 493594]
dict_tb["tb3_mixed_phase04_conflict03"]["strikes"]["strike02"] = [2, 493594]
dict_tb["tb3_mixed_phase04_conflict03"]["strikes"]["strike03"] = [2, 493594]
dict_tb["tb3_mixed_phase04_conflict03"]["strikes"]["strike04"] = [1, 987188]
dict_tb["tb3_mixed_phase04_conflict03"]["strikes"]["specialmission"] = [1, 0]
dict_tb["tb3_mixed_phase04_conflict03"]["coverts"] = {}
dict_tb["tb3_mixed_phase04_conflict03"]["coverts"]["covert01"] = [1]

dict_data={}
dict_tb["tb3_mixed_phase05_conflict01"] = {}
dict_tb["tb3_mixed_phase05_conflict01"]["name"] = "ROTE5-LS"
dict_tb["tb3_mixed_phase05_conflict01"]["type"] = "mix"
dict_tb["tb3_mixed_phase05_conflict01"]["scores"] = [341250768, 620455942, 729948167]
dict_tb["tb3_mixed_phase05_conflict01"]["strikes"] = {}
dict_tb["tb3_mixed_phase05_conflict01"]["strikes"]["strike01"] = [2, 721744]
dict_tb["tb3_mixed_phase05_conflict01"]["strikes"]["strike02"] = [2, 721744]
dict_tb["tb3_mixed_phase05_conflict01"]["strikes"]["strike03"] = [2, 721744]
dict_tb["tb3_mixed_phase05_conflict01"]["strikes"]["strike04"] = [2, 721744]
dict_tb["tb3_mixed_phase05_conflict01"]["strikes"]["strike05"] = [1, 1443488]
dict_tb["tb3_mixed_phase05_conflict01"]["coverts"] = {}
dict_tb["tb3_mixed_phase05_conflict02"] = {}
dict_tb["tb3_mixed_phase05_conflict02"]["name"] = "ROTE5-DS"
dict_tb["tb3_mixed_phase05_conflict02"]["type"] = "mix"
dict_tb["tb3_mixed_phase05_conflict02"]["scores"] = [341250768, 620455942, 729948167]
dict_tb["tb3_mixed_phase05_conflict02"]["strikes"] = {}
dict_tb["tb3_mixed_phase05_conflict02"]["strikes"]["strike01"] = [2, 721744]
dict_tb["tb3_mixed_phase05_conflict02"]["strikes"]["strike02"] = [2, 721744]
dict_tb["tb3_mixed_phase05_conflict02"]["strikes"]["strike03"] = [2, 721744]
dict_tb["tb3_mixed_phase05_conflict02"]["strikes"]["strike04"] = [2, 721744]
dict_tb["tb3_mixed_phase05_conflict02"]["coverts"] = {}
dict_tb["tb3_mixed_phase05_conflict03"] = {}
dict_tb["tb3_mixed_phase05_conflict03"]["name"] = "ROTE5-MS"
dict_tb["tb3_mixed_phase05_conflict03"]["type"] = "mix"
dict_tb["tb3_mixed_phase05_conflict03"]["scores"] = [341250768, 620455942, 729948167]
dict_tb["tb3_mixed_phase05_conflict03"]["strikes"] = {}
dict_tb["tb3_mixed_phase05_conflict03"]["strikes"]["strike01"] = [2, 721744]
dict_tb["tb3_mixed_phase05_conflict03"]["strikes"]["strike02"] = [2, 721744]
dict_tb["tb3_mixed_phase05_conflict03"]["strikes"]["strike03"] = [2, 721744]
dict_tb["tb3_mixed_phase05_conflict03"]["strikes"]["strike04"] = [1, 1443744]
dict_tb["tb3_mixed_phase05_conflict03"]["strikes"]["specialmission"] = [1, 0]
dict_tb["tb3_mixed_phase05_conflict03"]["coverts"] = {}
dict_tb["tb3_mixed_phase05_conflict03"]["coverts"]["covert01"] = [1]

dict_tb["tb3_mixed_phase06_conflict01"] = {}
dict_tb["tb3_mixed_phase06_conflict01"]["name"] = "ROTE6-LS"
dict_tb["tb3_mixed_phase06_conflict01"]["type"] = "mix"
dict_tb["tb3_mixed_phase06_conflict01"]["scores"] = [555710999, 1010383635, 1188686629]
dict_tb["tb3_mixed_phase06_conflict01"]["strikes"] = {}
dict_tb["tb3_mixed_phase06_conflict01"]["strikes"]["strike01"] = [2, 1151719]
dict_tb["tb3_mixed_phase06_conflict01"]["strikes"]["strike02"] = [2, 1151719]
dict_tb["tb3_mixed_phase06_conflict01"]["strikes"]["strike03"] = [2, 1151719]
dict_tb["tb3_mixed_phase06_conflict01"]["strikes"]["strike04"] = [2, 1151719]
dict_tb["tb3_mixed_phase06_conflict01"]["strikes"]["specialmission"] = [1, 2303438]
dict_tb["tb3_mixed_phase06_conflict01"]["coverts"] = {}
dict_tb["tb3_mixed_phase06_conflict02"] = {}
dict_tb["tb3_mixed_phase06_conflict02"]["name"] = "ROTE6-DS"
dict_tb["tb3_mixed_phase06_conflict02"]["type"] = "mix"
dict_tb["tb3_mixed_phase06_conflict02"]["scores"] = [582632425, 1059331682, 1246272567]
dict_tb["tb3_mixed_phase06_conflict02"]["strikes"] = {}
dict_tb["tb3_mixed_phase06_conflict02"]["strikes"]["strike01"] = [2, 1151719]
dict_tb["tb3_mixed_phase06_conflict02"]["strikes"]["strike02"] = [2, 1151719]
dict_tb["tb3_mixed_phase06_conflict02"]["strikes"]["strike03"] = [2, 1151719]
dict_tb["tb3_mixed_phase06_conflict02"]["strikes"]["strike04"] = [1, 1151719]
dict_tb["tb3_mixed_phase06_conflict02"]["strikes"]["strike05"] = [1, 2303438]
dict_tb["tb3_mixed_phase06_conflict02"]["coverts"] = {}
dict_tb["tb3_mixed_phase06_conflict03"] = {}
dict_tb["tb3_mixed_phase06_conflict03"]["name"] = "ROTE6-MS"
dict_tb["tb3_mixed_phase06_conflict03"]["type"] = "mix"
dict_tb["tb3_mixed_phase06_conflict03"]["scores"] = [582632425, 1059331682, 1246272567]
dict_tb["tb3_mixed_phase06_conflict03"]["strikes"] = {}
dict_tb["tb3_mixed_phase06_conflict03"]["strikes"]["strike01"] = [2, 1151719]
dict_tb["tb3_mixed_phase06_conflict03"]["strikes"]["strike02"] = [2, 1151719]
dict_tb["tb3_mixed_phase06_conflict03"]["strikes"]["strike03"] = [2, 1151719]
dict_tb["tb3_mixed_phase06_conflict03"]["strikes"]["strike04"] = [1, 1151719]
dict_tb["tb3_mixed_phase06_conflict03"]["strikes"]["strike05"] = [1, 2303438]
dict_tb["tb3_mixed_phase06_conflict03"]["coverts"] = {}

dict_tw = {}
dict_tw["tw_jakku01_phase01_conflict01"] = "T1"
dict_tw["tw_jakku01_phase01_conflict02"] = "B1"
dict_tw["tw_jakku01_phase02_conflict01"] = "T2"
dict_tw["tw_jakku01_phase02_conflict02"] = "B2"
dict_tw["tw_jakku01_phase03_conflict01"] = "F1"
dict_tw["tw_jakku01_phase03_conflict02"] = "T3"
dict_tw["tw_jakku01_phase03_conflict03"] = "B3"
dict_tw["tw_jakku01_phase04_conflict01"] = "F2"
dict_tw["tw_jakku01_phase04_conflict02"] = "T4"
dict_tw["tw_jakku01_phase04_conflict03"] = "B4"
dict_tw["T1"] = "tw_jakku01_phase01_conflict01"
dict_tw["B1"] = "tw_jakku01_phase01_conflict02"
dict_tw["T2"] = "tw_jakku01_phase02_conflict01"
dict_tw["B2"] = "tw_jakku01_phase02_conflict02"
dict_tw["F1"] = "tw_jakku01_phase03_conflict01"
dict_tw["T3"] = "tw_jakku01_phase03_conflict02"
dict_tw["B3"] = "tw_jakku01_phase03_conflict03"
dict_tw["F2"] = "tw_jakku01_phase04_conflict01"
dict_tw["T4"] = "tw_jakku01_phase04_conflict02"
dict_tw["B4"] = "tw_jakku01_phase04_conflict03"

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
