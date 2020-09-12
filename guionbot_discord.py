# Source --> https://realpython.com/how-to-make-a-discord-bot-python/
# CERTIFICATE_VERIFY_FAILED --> https://github.com/Rapptz/discord.py/issues/4159

import os
#import aiocron
from discord.ext import commands
#from dotenv import load_dotenv
from go import function_tw, function_twt, split_txt

#load_dotenv()
#TOKEN = os.getenv('DISCORD_TOKEN')
TOKEN = 'NzUyOTY5NjQ3MjMzNTY0NzAz.X1fXoQ.arxYkcPspOFTU5SeCooiKsgkZNQ'
bot = commands.Bot(command_prefix='go.')
emoji_thumb = '\N{THUMBS UP SIGN}'

@bot.event
async def on_ready():
	print(f'{bot.user.name} has connected to Discord!')

@bot.command(name='99')
async def nine_nine(ctx):
	await ctx.send('99 aussi')
	
@bot.command(name='gt', help='Compare 2 guildes pour la GT')
async def gt(ctx, allycode, op_alycode):
	ret_gt=function_tw(allycode, op_alycode)
	#print(len(ret_gt))
	for txt in split_txt(ret_gt, 1000):
		await ctx.send('`'+txt+'`')

@bot.command(name='gtt', help='Liste la dispo d une team dans la guilde')
async def gtt(ctx, allycode, team):
	await ctx.message.add_reaction(emoji_thumb)
	ret_gt=function_twt(allycode, team)
	#print(len(ret_gt))
	for txt in split_txt(ret_gt, 1000):
		await ctx.send('`'+txt+'`')

#@aiocron.crontab('*/1 * * * *') # toutes les 1 minutes
#async def cornjob1():
#	channel = client.get_channel(751908336479502357)
#	await channel.send('Cron Test')


bot.run(TOKEN)