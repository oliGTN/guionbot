REM à faire une fois après installation du procfile
REM heroku ps:scale worker=1

git add *
git commit -m "import discord"
git push -u origin master
heroku logs --tail