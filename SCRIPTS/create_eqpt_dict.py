import json
import sys

game_data = json.load(open(sys.argv[1], 'r'))
FRE_FR = json.load(open("DATA/FRE_FR.json", 'r'))

#Cost by mission node
dict_cost={}
dict_cost["C01D"] = {}
dict_cost["C01D"]["M01"] = {"NORMALDIFF": "6Y", "HARDDIFF": "12Y"}
dict_cost["C01D"]["M02"] = {"NORMALDIFF": "6Y", "HARDDIFF": "12Y"}
dict_cost["C01D"]["M03"] = {"NORMALDIFF": "6Y", "HARDDIFF": "12Y"}
dict_cost["C01D"]["M04"] = {"NORMALDIFF": "6Y", "HARDDIFF": "12Y"}
dict_cost["C01D"]["M05"] = {"NORMALDIFF": "8Y", "HARDDIFF": "16Y"}
dict_cost["C01D"]["M06"] = {"NORMALDIFF": "8Y", "HARDDIFF": "16Y"}
dict_cost["C01D"]["M07"] = {"NORMALDIFF": "10Y", "HARDDIFF": "20Y"}
dict_cost["C01D"]["M08"] = {"NORMALDIFF": "10Y", "HARDDIFF": "20Y"}
dict_cost["C01D"]["M09"] = {"NORMALDIFF": "10Y", "HARDDIFF": "20Y"}

dict_cost["C01L"] = {}
dict_cost["C01L"]["M01"] = {"NORMALDIFF": "6Y", "HARDDIFF": "12Y"}
dict_cost["C01L"]["M02"] = {"NORMALDIFF": "6Y", "HARDDIFF": "12Y"}
dict_cost["C01L"]["M03"] = {"NORMALDIFF": "6Y", "HARDDIFF": "12Y"}
dict_cost["C01L"]["M04"] = {"NORMALDIFF": "6Y", "HARDDIFF": "12Y"}
dict_cost["C01L"]["M05"] = {"NORMALDIFF": "8Y", "HARDDIFF": "16Y"}
dict_cost["C01L"]["M06"] = {"NORMALDIFF": "8Y", "HARDDIFF": "16Y"}
dict_cost["C01L"]["M07"] = {"NORMALDIFF": "10Y", "HARDDIFF": "20Y"}
dict_cost["C01L"]["M08"] = {"NORMALDIFF": "10Y", "HARDDIFF": "20Y"}
dict_cost["C01L"]["M09"] = {"NORMALDIFF": "10Y", "HARDDIFF": "20Y"}

dict_cost["C01H"] = {}
dict_cost["C01H"]["M01"] = {"NORMALDIFF": "8R"}
dict_cost["C01H"]["M02"] = {"NORMALDIFF": "8R"}
dict_cost["C01H"]["M03"] = {"NORMALDIFF": "10R"}
dict_cost["C01H"]["M04"] = {"NORMALDIFF": "10R"}
dict_cost["C01H"]["M05"] = {"NORMALDIFF": "12R"}
dict_cost["C01H"]["M06"] = {"NORMALDIFF": "12R"}
dict_cost["C01H"]["M07"] = {"NORMALDIFF": "16R"}
dict_cost["C01H"]["M08"] = {"NORMALDIFF": "16R"}

dict_cost["C01SP"] = {}
dict_cost["C01SP"]["M01"] = {"NORMALDIFF": "8B", "HARDDIFF": "16B"}
dict_cost["C01SP"]["M02"] = {"NORMALDIFF": "10B", "HARDDIFF": "20B"}
dict_cost["C01SP"]["M03"] = {"NORMALDIFF": "10B", "HARDDIFF": "20B"}
dict_cost["C01SP"]["M04"] = {"NORMALDIFF": "10B", "HARDDIFF": "20B"}
dict_cost["C01SP"]["M05"] = {"NORMALDIFF": "10B", "HARDDIFF": "20B"}

dict_eqpt = {}
for material in game_data["material"]:
    material_id = material["id"]
    if not material_id.startswith("unitshard_"):
        continue
    print(material_id)
    accelerated = (material["sellValue"]["quantity"]==15)
    dict_eqpt[material_id] = []
    if "lookupMission" in material:
        for mission in material["lookupMission"]:
            campaignId = mission["missionIdentifier"]["campaignId"]
            if "EVENTS" in campaignId:
                continue
            campaignMapId = mission["missionIdentifier"]["campaignMapId"]
            campaignNodeDifficulty = mission["missionIdentifier"]["campaignNodeDifficulty"]
            cost = dict_cost[campaignId][campaignMapId][campaignNodeDifficulty]
            if accelerated:
                cost = str(int(int(cost[:-1])/2))+cost[-1]
            dict_eqpt[material_id].append(cost)


f=open("DATA/eqpt_dict.json", "w")
f.write(json.dumps(dict_eqpt, indent=4))
f.close()

