echo Enter root password for mysql
mysqldump -u root -p guionbotdb --no-data --routines > mysql_procedures.txt
