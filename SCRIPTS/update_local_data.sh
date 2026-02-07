python SCRIPTS/update_localization_dict.py

GAMEDATA_FILE=../warstats/GameData.json
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
echo "update relic promotion table..."
python SCRIPTS/create_relic_promo_table.py $GAMEDATA_FILE
echo "update crinolo data..."
python SCRIPTS/create_crinolo_gameData.py $GAMEDATA_FILE

echo "clean..."
rm CACHE/config_units.json
echo "... OK"
