CURWD=$PWD

#Get current API version
cd CACHE
if [ -f version ]; then
	rm version
fi
wget https://api.swgoh.help/version 2> /dev/null
DIFF_RES=$(diff version ../DATA/version)
cd ..

if [ "$DIFF_RES" != "" ]; then
	echo "New data available in SWGOH API"
else
	echo "No change in SWGOH API"
fi

if [ "$DIFF_RES" != "" ] || [ "$1" == "force" ]; then
	cp CACHE/version DATA/
	python get_data.py unitsList
	python get_data.py unitsList ENG_US
	python get_data.py categoryList
	python get_data.py categoryList ENG_US
	python get_data.py abilityList
	python get_data.py skillList
	python get_data.py materialList
	ls -ltr DATA/
fi

cd CACHE
if [ -f version ]; then
	rm version
fi
cd ..

#rebuild gameData.json
cd ../swgoh-stat-calc/swgoh-stat-calc-dataBuilder
node runDataBuilder.js $(grep SWGOHAPI_LOGIN $CURWD/config.py|cut -f2 -d\") $(grep SWGOHAPI_PASSWORD $CURWD/config.py|cut -f2 -d\")