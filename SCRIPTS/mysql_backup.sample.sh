rm -rf /home/pi/GuionBot/SQLBACKUP/
mkdir /home/pi/GuionBot/SQLBACKUP
for table in gp_history gv_history roster_evolutions guilds guild_bot_infos players shards stat_list guild_evolutions
do
    echo $table
	mysqldump -u<user> -p<password> --opt guionbotdb $table > /home/pi/GuionBot/SQLBACKUP/$table.sql
done

echo Copy EVENTS... only latest 30 days
OIFS="$IFS"
IFS=$'\n'
for f in $(find /home/pi/GuionBot/EVENTS/ -type f -mtime -30)
do
    echo "   $f"
    cp $f /home/pi/GuionBot/SQLBACKUP
done
IFS="$OIFS"

echo Compress...
tar -zcvf /home/pi/GuionBot/all_tables.gz /home/pi/GuionBot/SQLBACKUP
mv /home/pi/GuionBot/all_tables.gz /home/pi/GuionBot/SQLBACKUP

echo Upload...
python /home/pi/GuionBot/guionbot-dev/SCRIPTS/upload_sqlbackup.py $1

