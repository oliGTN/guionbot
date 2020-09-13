git add *
git commit -m "import discord"
git push -u origin master
heroku ps:scale worker=1
heroku logs --tail