rm -rf /home/pi/GuionBot/SQLBACKUP/
mkdir /home/pi/GuionBot/SQLBACKUP
for table in gp_history gv_history roster_evolutions guilds guild_bot_infos players shards stat_list guild_evolutions
do
	mysqldump -u<user> -p<password> --opt guionbotdb $table > /home/pi/GuionBot/SQLBACKUP/$table.sql
done
cp -r /home/pi/GuionBot/EVENTS /home/pi/GuionBot/SQLBACKUP

tar -zcvf /home/pi/GuionBot/all_tables.gz /home/pi/GuionBot/SQLBACKUP
mv /home/pi/GuionBot/all_tables.gz /home/pi/GuionBot/SQLBACKUP

python /home/pi/GuionBot/guionbot-master/SCRIPTS/upload_sqlbackup.py $1

