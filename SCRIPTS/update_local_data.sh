python SCRIPTS/update_localization_dict.py

# Run all generators in one process so each large GameData file is parsed only once.
python -m SCRIPTS.update_local_data

echo "clean..."
rm -f CACHE/config_units.json
rm -f ../swgoh-stat-calc/swgoh-stats/statCalcData/dataVersion.json
echo "... OK"
