CMD_PWD=$PWD

# SWGOH-STAT-CALC
cd /home/pi/GuionBot/swgoh-stat-calc
node server.js &

# GUIONBOT
if [ "$1" = "" ]
then
	cd /home/pi/GuionBot/guionbot-master
else
	cd $CMD_PWD
fi

rm CACHE/*.tmp 2>/dev/null
python guionbot_discord.py | while read line; do echo "$line" >> /home/pi/GuionBot/LOGS/guionbot.log; done
