# Source --> https://realpython.com/how-to-make-a-discord-bot-python/
# CERTIFICATE_VERIFY_FAILED --> https://github.com/Rapptz/discord.py/issues/4159

import os
import asyncio
import time
from discord.ext import commands
from go import function_gt, function_gtt, split_txt, clean_cache

#load_dotenv()
#TOKEN = os.getenv('DISCORD_TOKEN')
TOKEN = 'NzUyOTY5NjQ3MjMzNTY0NzAz.X1fXoQ.arxYkcPspOFTU5SeCooiKsgkZNQ'
bot = commands.Bot(command_prefix='go.')

#https://til.secretgeek.net/powershell/emoji_list.html
emoji_thumb = '\N{THUMBS UP SIGN}'
emoji_check = '\N{WHITE HEAVY CHECK MARK}'

nb_commandes=0

async def bot_loop_60():
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            clean_cache(15)
            await asyncio.sleep(60)
        except Exception as e:
            print(e)
            await asyncio.sleep(60)
			
async def is_owner(ctx):
	return ctx.author.id == 566552780647563285
			
@bot.event
async def on_ready():
	print(f'{bot.user.name} has connected to Discord!')

@bot.command(name='info')
async def info(ctx):
	global nb_commandes
	nb_commandes+=1
	await ctx.message.add_reaction(emoji_thumb)

	await ctx.send('GuiOn bot is UP\n'+clean_cache(99))
	await ctx.message.add_reaction(emoji_check)
	
@bot.command(name='cmd')
@commands.check(is_owner)
async def cmd(ctx, arg):
	global nb_commandes
	nb_commandes+=1
	await ctx.message.add_reaction(emoji_thumb)

	stream = os.popen(arg)
	output = stream.read()
	print('CMD: '+arg)
	print(output)
	for txt in split_txt(output, 1000):
		await ctx.send('`'+txt+'`')
	await ctx.message.add_reaction(emoji_check)
	
@bot.command(name='gt', help='Compare 2 guildes pour la GT')
async def gt(ctx, allycode, op_alycode):
	global nb_commandes
	nb_commandes+=1
	await ctx.message.add_reaction(emoji_thumb)

	ret_gt=function_gt(allycode, op_alycode)
	#print(len(ret_gt))
	for txt in split_txt(ret_gt, 1000):
		await ctx.send('`'+txt+'`')
	await ctx.message.add_reaction(emoji_check)

@bot.command(name='gtt', help='Liste la dispo d une team dans la guilde')
async def gtt(ctx, allycode, team):
	global nb_commandes
	nb_commandes+=1
	await ctx.message.add_reaction(emoji_thumb)

	ret_gt=function_gtt(allycode, team)
	#print(len(ret_gt))
	for txt in split_txt(ret_gt, 1000):
		await ctx.send('`'+txt+'`')
	await ctx.message.add_reaction(emoji_check)
		
bot.loop.create_task(bot_loop_60())
bot.run(TOKEN)