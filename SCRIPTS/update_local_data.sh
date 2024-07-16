python SCRIPTS/update_localization_dict.py

GAMEDATA_VERSION=$(grep latestGamedataVersion ../warstats/metadata.json |cut -f4 -d\")
echo $GAMEDATA_VERSION
GAMEDATA_FILE=../GAMEDATA/GameData_${GAMEDATA_VERSION}.json
echo "update units..."
python SCRIPTS/update_unitsList_json.py $GAMEDATA_FILE
echo "update capabilities..."
python SCRIPTS/create_capa_list.py $GAMEDATA_FILE
echo "update equipment..."
python SCRIPTS/create_eqpt_dict.py $GAMEDATA_FILE
echo "update targeting rules..."
python SCRIPTS/create_targetrule_dict.py $GAMEDATA_FILE
echo "update TB..."
python SCRIPTS/create_tb_data.py $GAMEDATA_FILE

echo "clean..."
rm CACHE/config_units.json
echo "... OK"
