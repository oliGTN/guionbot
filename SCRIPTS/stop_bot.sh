PS_LIST=$(ps -edf|grep "python guionbot"|grep -v grep|awk '{print $2}')
while [ "$PS_LIST" != "" ]
do
	echo $PS_LIST
	kill -9 $PS_LIST
	PS_LIST=$(ps -edf|grep "python guionbot"|grep -v grep|awk '{print $2}')
	sleep 1
done

