CMD_PWD=$PWD

# GUIONBOT
if [ "$1" = "" ]; then
	cd /home/pi/GuionBot/guionbot-master
else
	cd $CMD_PWD
fi

rm CACHE/*.tmp 2>/dev/null
if [ "$1" = "test" ]; then
	python guionbot_discord.py test
elif [ "$1" = "noloop" ]; then
	python guionbot_discord.py noloop
else
	python guionbot_discord.py 2>&1 | while read line; do echo "$line" >> /home/pi/GuionBot/LOGS/guionbot.log; done
fi
disown -a
