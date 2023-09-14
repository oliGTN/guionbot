python SCRIPTS/update_localization_dict.py

GAMEDATA_VERSION=$(grep latestGamedataVersion ../warstats/metadata.json |cut -f4 -d\")
echo $GAMEDATA_VERSION
GAMEDATA_FILE=../warstats/GameData_${GAMEDATA_VERSION}.json
python SCRIPTS/update_unitsList_json.py $GAMEDATA_FILE
python SCRIPTS/create_capa_list.py $GAMEDATA_FILE

rm CACHE/config_units.json
