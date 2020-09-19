# Source --> https://realpython.com/how-to-make-a-discord-bot-python/
# CERTIFICATE_VERIFY_FAILED --> https://github.com/Rapptz/discord.py/issues/4159

import os
import asyncio
import time
import re
from discord.ext import commands
from go import function_gt, function_gtt, split_txt, refresh_cache, stats_cache, load_guild
from connect_gsheets import load_config_players
from connect_warstats import parse_warstats_page

#load_dotenv()
#TOKEN = os.getenv('DISCORD_TOKEN')
TOKEN = 'NzUyOTY5NjQ3MjMzNTY0NzAz.X1fXoQ.arxYkcPspOFTU5SeCooiKsgkZNQ'
bot = commands.Bot(command_prefix='go.')
#dict_players={}

#https://til.secretgeek.net/powershell/emoji_list.html
emoji_thumb = '\N{THUMBS UP SIGN}'
emoji_check = '\N{WHITE HEAVY CHECK MARK}'
emoji_error = '\N{CROSS MARK}'
cache_delete_minutes=1440 #24 hours before deleting unused cache file
cache_refresh_minutes=60 #60 minutes minimum to refresh data from the guild

async def bot_loop_60():
	#global dict_players
	await bot.wait_until_ready()
	while not bot.is_closed():
		try:
			#clean_cache(cache_delete_minutes)
			
			#list_guild_allycodes=[(lambda x:str(x))(x) for x in dict_players]
			refresh_cache(cache_delete_minutes, cache_refresh_minutes, 1)
			await asyncio.sleep(60) #60 seconds for loop
		except Exception as e:
			print(e)
			await asyncio.sleep(60) #60 seconds for loop
			
async def is_owner(ctx):
	return ctx.author.id == 566552780647563285
			
@bot.event
async def on_ready():
	#global dict_players
	#dict_players=load_config_players()
	load_guild('189341793', False)
	print(f'{bot.user.name} has connected to Discord!')

@bot.command(name='info', help='Statut du bot')
async def info(ctx):
	await ctx.message.add_reaction(emoji_thumb)

	await ctx.send('GuiOn bot is UP\n'+stats_cache()+'\n'+str(cache_delete_minutes)+' minutes before deleting\n'+str(cache_refresh_minutes)+' minutes before refreshing\n')
	await ctx.message.add_reaction(emoji_check)
	
@bot.command(name='cmd', help='Réservé à GuiOn Ensai')
@commands.check(is_owner)
async def cmd(ctx, arg):
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
	await ctx.message.add_reaction(emoji_thumb)

	if allycode=='KL':
		allycode='189341793'
		
	ret_cmd=function_gt(allycode, op_alycode)
	if ret_cmd[0:3]=='ERR':
		await ctx.send(ret_cmd)
		await ctx.message.add_reaction(emoji_error)
	else:
		for txt in split_txt(ret_cmd, 1000):
			await ctx.send('`'+txt+'`')
		await ctx.message.add_reaction(emoji_check)

@bot.command(name='gtt', help="Liste la dispo d'une team dans la guilde")
async def gtt(ctx, allycode, team):
	await ctx.message.add_reaction(emoji_thumb)

	if allycode=='KL':
		allycode='189341793'
			
	ret_cmd=function_gtt(allycode, team)
	if ret_cmd[0:3]=='ERR':
		await ctx.send(ret_cmd)
		await ctx.message.add_reaction(emoji_error)
	else:
		for txt in split_txt(ret_cmd, 1000):
			await ctx.send('`'+txt+'`')
		await ctx.message.add_reaction(emoji_check)

@bot.command(name='vdp', help="Vérification de Déploiement des Pelotons en TB")
async def vdp(ctx):
	await ctx.message.add_reaction(emoji_thumb)

	#Lecture du statut des pelotons sur warstats
	tbs_phase, dict_platoons_done = parse_warstats_page()

	if tbs_phase=='':
		await ctx.send('Aucune TBS en cours')
		await ctx.message.add_reaction(emoji_error)
	else:
		print('Lecture terminée du statut TB sur warstats: phase '+tbs_phase)
		bt_channel=bot.get_channel(719211688166948914)
		dict_platoons_allocation={} #key=platton_name, value={key=perso, value=[player...]}
		async for message in bt_channel.history(limit=200):
			if str(message.author)=='EchoStation#0000':
				msg_time=int(message.created_at.timestamp())
				if message.content.startswith(':information_source: **Overview** (Phase'):
					numero_phase=re.search('\((.*?)\)', message.content).group(1)[-1]
					print('Lecture terminée de l\'affectation EchoBot pour la phase '+numero_phase)
					break
					
				if message.content.startswith('```prolog'):
					position_territoire=re.search('\((.*?)\)', message.content).group(1)
					if position_territoire=='top':
						position_territoire='A'
					elif position_territoire=='mid':
						position_territoire='B'
					elif position_territoire=='bottom':
						position_territoire='C'
					
					for embed in message.embeds:
						dict_embed=embed.to_dict()
						if 'fields' in dict_embed:
							#print(dict_embed)
							platoon_name=position_territoire+re.search('\*\*(.*?)\*\*', dict_embed['description']).group(1)[-1]
							for dict_perso in dict_embed['fields']:
								for perso in dict_perso['value'].split('\n'):
									char_name=perso[1:-1]
									if not platoon_name in dict_platoons_allocation:
										dict_platoons_allocation[platoon_name]={}
									if not char_name in dict_platoons_allocation[platoon_name]:
										dict_platoons_allocation[platoon_name][char_name]=[]
									dict_platoons_allocation[platoon_name][char_name].append(dict_perso['name'])
		
		if numero_phase!=tbs_phase:
			await ctx.send('ERR: les phases ne sont pas identiques')
			await ctx.message.add_reaction(emoji_error)
		else:
			#Comparaison des dictionnaires
			#Recherche des persos non-affectés
			#print(dict_platoons_done)
			#print(dict_platoons_allocation)
			for platoon_name in dict_platoons_done:
				for perso in dict_platoons_done[platoon_name]:
					if '' in dict_platoons_done[platoon_name][perso]:
						if platoon_name in dict_platoons_allocation:
							#print (platoon_name+': '+perso)
							#print(dict_platoons_allocation[platoon_name])
							if perso in dict_platoons_allocation[platoon_name]:
								for allocated_player in dict_platoons_allocation[platoon_name][perso]:
									if not allocated_player in dict_platoons_done[platoon_name][perso]:
										await ctx.send('**'+allocated_player+'** n\'a pas affecté '+perso+' en '+platoon_name)
							else:
								await ctx.send('ERR: '+perso+' n\'a pas été affecté')
								print('ERR: '+perso+' n\'a pas été affecté')
								print(dict_platoons_allocation[platoon_name].keys())
			await ctx.message.add_reaction(emoji_check)
						
		
bot.loop.create_task(bot_loop_60())
bot.run(TOKEN)