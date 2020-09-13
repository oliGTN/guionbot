git add *
set /p cmt=Commentaire:
git commit -m "%cmt"
git push -u origin master