SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
echo SCRIPT_DIR=$SCRIPT_DIR

rm -rf /home/pi/GuionBot/SQLBACKUP/
mkdir /home/pi/GuionBot/SQLBACKUP
for table in gp_history guilds guild_bot_infos guild_gp_history players player_discord shards statq_table user_bot_infos
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

echo Copy config.py...
cp /home/GuionBot/guionbot-dev/config.py /home/pi/GuionBot/SQLBACKUP

echo Compress...
tar -zcvf /home/pi/GuionBot/all_tables.gz /home/pi/GuionBot/SQLBACKUP
mv /home/pi/GuionBot/all_tables.gz /home/pi/GuionBot/SQLBACKUP

echo Upload...
python $SCRIPT_DIR/upload_sqlbackup.py $1

