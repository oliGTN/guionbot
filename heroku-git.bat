move /Y CACHE\*.json ..\CACHE\
git add *
set /p cmt=Commentaire:
git commit -m "%cmt%"
git push -u origin master
copy ..\CACHE\*.json CACHE