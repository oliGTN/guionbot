#Get current API version
cd CACHE
if [ -f version ]; then
	rm version
fi
wget https://api.swgoh.help/version 2> /dev/null
set DIFF_RES=$(diff version ../DATA/version)
cd ..
if [ "$DIFF_RES" != "" ]; then
	echo "New data available in SWGOH API"
else
	echo "No change in SWGOH API"
fi

if [ "$DIFF_RES" != "" ] || [ "$1" == "force" ]; then
	mv CACHE/version DATA/
	echo python get_data.py unitsList
	echo python get_data.py unitsList ENG_US
	echo python get_data.py categoryList
	echo python get_data.py categoryList ENG_US
	echo python get_data.py abilityList
	echo python get_data.py skillList
fi

rm CACHE/version
