# Source --> https://realpython.com/how-to-make-a-discord-bot-python/
# CERTIFICATE_VERIFY_FAILED --> https://github.com/Rapptz/discord.py/issues/4159

import os
import asyncio
import time
from discord.ext import commands
from go import function_gt, function_gtt, split_txt, clean_cache, refresh_cache, stats_cache
from connect_gsheets import load_config_players

#load_dotenv()
#TOKEN = os.getenv('DISCORD_TOKEN')
TOKEN = 'NzUyOTY5NjQ3MjMzNTY0NzAz.X1fXoQ.arxYkcPspOFTU5SeCooiKsgkZNQ'
bot = commands.Bot(command_prefix='go.')
dict_players={}

#https://til.secretgeek.net/powershell/emoji_list.html
emoji_thumb = '\N{THUMBS UP SIGN}'
emoji_check = '\N{WHITE HEAVY CHECK MARK}'
emoji_error = '\N{CROSS MARK}'
cache_delete_minutes=240 #4 hours before deleting unused cache file
cache_refresh_minutes=15 #15 minutes minimum to refresh data from the guild
nb_commandes=0

dict_players={}
async def bot_loop_60():
	global dict_players
	await bot.wait_until_ready()
	while not bot.is_closed():
		try:
			clean_cache(cache_delete_minutes)
			
			list_guild_allycodes=[(lambda x:str(x))(x) for x in dict_players]
			refresh_cache(cache_delete_minutes, list_guild_allycodes)
			await asyncio.sleep(60) #60 seconds for loop
		except Exception as e:
			print(e)
			await asyncio.sleep(60) #60 seconds for loop
			
async def is_owner(ctx):
	return ctx.author.id == 566552780647563285
			
@bot.event
async def on_ready():
	global dict_players
	dict_players=load_config_players()
	print(f'{bot.user.name} has connected to Discord!')

@bot.command(name='info', help='Statut du bot')
async def info(ctx):
	global nb_commandes
	nb_commandes+=1
	await ctx.message.add_reaction(emoji_thumb)

	await ctx.send('GuiOn bot is UP\n'+stats_cache()+'\n'+str(cache_delete_minutes)+' minutes before deleting\n'+str(cache_refresh_minutes)+' minutes before refreshing\n')
	await ctx.message.add_reaction(emoji_check)
	
@bot.command(name='cmd', help='Réservé à GuiOn Ensai')
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

	if allycode=='me':
		discord_name=str(ctx.message.author)
		print(discord_name)
		if discord_name in dict_players:
			allycode = dict_players[discord_name]
		else:
			allycode=''
			await ctx.send("Tu n'es pas enregistré pour utiliser ce bot, merci d'utiliser un <code allié> explicite ou 'KL' pour la guile Kangoo Legends")
			await ctx.message.add_reaction(emoji_error)
	elif allycode=='KL':
		allycode='189341793'
		
	if allycode!='':
		ret_gt=function_gt(allycode, op_alycode)
		#print(len(ret_gt))
		for txt in split_txt(ret_gt, 1000):
			await ctx.send('`'+txt+'`')
		await ctx.message.add_reaction(emoji_check)

@bot.command(name='gtt', help="Liste la dispo d'une team dans la guilde")
async def gtt(ctx, allycode, team):
	global nb_commandes
	nb_commandes+=1
	await ctx.message.add_reaction(emoji_thumb)

	if allycode=='me':
		discord_name=str(ctx.message.author)
		print(discord_name)
		if discord_name in dict_players:
			allycode = dict_players[discord_name]
		else:
			allycode=''
			await ctx.send("Tu n'es pas enregistré pour utiliser ce bot, merci d'utiliser un <code allié> explicite ou 'KL' pour la guile Kangoo Legends")
			await ctx.message.add_reaction(emoji_error)
	elif allycode=='KL':
		allycode='189341793'
			
	if allycode!='':
		ret_gt=function_gtt(allycode, team)
		#print(len(ret_gt))
		for txt in split_txt(ret_gt, 1000):
			await ctx.send('`'+txt+'`')
		await ctx.message.add_reaction(emoji_check)
		
bot.loop.create_task(bot_loop_60())
bot.run(TOKEN)