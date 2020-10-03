# Source --> https://realpython.com/how-to-make-a-discord-bot-python/
# CERTIFICATE_VERIFY_FAILED --> https://github.com/Rapptz/discord.py/issues/4159

import os
import asyncio
import time
import datetime
import re
from discord.ext import commands
from discord import Embed
from go import function_gt, guild_team, player_team, split_txt, refresh_cache, stats_cache, load_guild, assign_bt
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
	for txt in split_txt(output, 2000):
		await ctx.send('`'+txt+'`')
	await ctx.message.add_reaction(emoji_check)
	
# @bot.command(name='test', help='Réservé à GuiOn Ensai')
# @commands.check(is_owner)
# async def test(ctx, allycode):
	# await ctx.message.add_reaction(emoji_thumb)

	# if allycode=='KL':
		# allycode='189341793'
			
	# ret_cmd=assign_bt(allycode)
	# if ret_cmd[0:3]=='ERR':
		# await ctx.send(ret_cmd)
		# await ctx.message.add_reaction(emoji_error)
	# else:
		# # texte classique
		# for txt in split_txt(ret_cmd, 2000):
			# await ctx.send(txt)
			
		# # Icône de confirmation de fin de commande dans le message d'origine
		# await ctx.message.add_reaction(emoji_check)
	
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
		for txt in split_txt(ret_cmd, 2000):
			await ctx.send('`'+txt+'`')
		await ctx.message.add_reaction(emoji_check)

@bot.command(name='vtg', help="Vérifie la dispo d'une team dans la guilde")
async def vtg(ctx, allycode, *teams):
	await ctx.message.add_reaction(emoji_thumb)

	if allycode=='KL':
		allycode='189341793'
	
	ret_cmd=guild_team(allycode, teams, 1, False)
	for team in ret_cmd:
		txt_team=ret_cmd[team]
		for txt in split_txt(txt_team, 2000):
			await ctx.send(txt)
			
	#Icône de confirmation de fin de commande dans le message d'origine
	await ctx.message.add_reaction(emoji_check)

@bot.command(name='vtj', help="Vérifie la dispo d'une ou plusieurs teams chez un joueur")
async def vtj(ctx, allycode, *teams):
	await ctx.message.add_reaction(emoji_thumb)
	
	ret_cmd=player_team(allycode, teams, 1, False)
	for team in ret_cmd:
		txt_team=ret_cmd[team]
		for txt in split_txt(txt_team, 2000):
			await ctx.send(txt)
		
	#Icône de confirmation de fin de commande dans le message d'origine
	await ctx.message.add_reaction(emoji_check)

@bot.command(name='vtg2', help="Comme vtg mais avec un autre scoring utilisé pour agt")
async def vtg2(ctx, allycode, team):
	await ctx.message.add_reaction(emoji_thumb)

	if allycode=='KL':
		allycode='189341793'
	
	ret_cmd=guild_team(allycode, [team], 3, False)[team]
	if ret_cmd[0:3]=='ERR':
		await ctx.send(ret_cmd)
		await ctx.message.add_reaction(emoji_error)
	else:
		#texte classique
		for txt in split_txt(ret_cmd, 2000):
			await ctx.send(txt)
			
		#Icône de confirmation de fin de commande dans le message d'origine
		await ctx.message.add_reaction(emoji_check)

@bot.command(name='agt', help="Assigne les équipes par territoire en BT")
async def agt(ctx, allycode):
	await ctx.message.add_reaction(emoji_thumb)

	if allycode=='KL':
		allycode='189341793'
			
	ret_cmd=assign_bt(allycode, False)
	if ret_cmd[0:3]=='ERR':
		await ctx.send(ret_cmd)
		await ctx.message.add_reaction(emoji_error)
	else:
		#texte classique
		for txt in split_txt(ret_cmd, 2000):
			await ctx.send(txt)
			
		#Icône de confirmation de fin de commande dans le message d'origine
		await ctx.message.add_reaction(emoji_check)

@bot.command(name='vdp', help="Vérification de Déploiement des Pelotons en TB")
async def vdp(ctx):
	await ctx.message.add_reaction(emoji_thumb)

	#Lecture du statut des pelotons sur warstats
	tbs_phase, dict_platoons_done, dict_player_allocations, list_open_territories = parse_warstats_page()
	
	#Recuperation des dernieres donnees sur gdrive
	dict_players=load_config_players() # {key=IG name, value=[allycode, discord name, discord id]]

	if tbs_phase=='':
		await ctx.send('Aucune BT en cours')
		await ctx.message.add_reaction(emoji_error)
	else:
		print('Lecture terminée du statut BT sur warstats: phase '+tbs_phase)
		
		# Lecture des affectation ECHOBOT
		bt_channel=bot.get_channel(719211688166948914) #channel batailles de territoire
		dict_platoons_allocation={} #key=platton_name, value={key=perso, value=[player...]}
		eb_phases=[]
		eb_missions_full=[]
		eb_missions_tmp=[]
		async for message in bt_channel.history(limit=500):
			if str(message.author)=='EchoStation#0000':
				if (datetime.datetime.now() - message.created_at).days > 7:
					#On considère que si un message echobot a plus de 7 jours c'est une ancienne BT
					break

				if message.content.startswith(':information_source: **Overview** (Phase'):
					numero_phase=re.search('\((.*?)\)', message.content).group(1)[-1]

					#renumérotation des clés du dictionnaire avec la phase (si pas déjà lue)
					#print(dict_platoons_allocation)
					old_platoon_names=set(dict_platoons_allocation.keys())
					for old_platoon_name in old_platoon_names:
						new_platoon_name=old_platoon_name[0:3]+numero_phase+old_platoon_name[4:]
						if old_platoon_name[3]=='X':
							phase_position=numero_phase+'-'+old_platoon_name.split('-')[1]
							#print(phase_position)
							#print(eb_missions_full)
							if not (phase_position in eb_missions_full):
								dict_platoons_allocation[new_platoon_name]=dict_platoons_allocation[old_platoon_name]
							#print('del dict_platoons_allocation['+old_platoon_name+']')
							del dict_platoons_allocation[old_platoon_name]
					#print(dict_platoons_allocation)
					#print('=========================')
					
					#Ajout des phases lues dans la liste complète
					for pos in eb_missions_tmp:
						if not (numero_phase+'-'+pos) in eb_missions_full:
							eb_missions_full.append(numero_phase+'-'+pos)
					eb_missions_tmp=[]

					if not (numero_phase in eb_phases):
						eb_phases.append(numero_phase)
						print('Lecture terminée de l\'affectation EchoBot pour la phase '+numero_phase)
						
					
				if message.content.startswith('```prolog'):
					position_territoire=re.search('\((.*?)\)', message.content).group(1)
					eb_missions_tmp.append(position_territoire)
					
					for embed in message.embeds:
						dict_embed=embed.to_dict()
						if 'fields' in dict_embed:
							#print(dict_embed)
							#on garde le nom de la BT mais on met X comme numéro de phase
							#le numéro de phase sera affecté plus tard
							platoon_name=tbs_phase[0:3]+'X-'+position_territoire+'-'+re.search('\*\*(.*?)\*\*', dict_embed['description']).group(1)[-1]
							for dict_perso in dict_embed['fields']:
								for perso in dict_perso['value'].split('\n'):
									char_name=perso[1:-1]
									if not platoon_name in dict_platoons_allocation:
										dict_platoons_allocation[platoon_name]={}
									if not char_name in dict_platoons_allocation[platoon_name]:
										dict_platoons_allocation[platoon_name][char_name]=[]
									dict_platoons_allocation[platoon_name][char_name].append(dict_perso['name'])
		
		#Comparaison des dictionnaires
		#Recherche des persos non-affectés
		#print(dict_platoons_done)
		#print(dict_platoons_allocation)
		#print(dict_player_allocations)
		erreur_detectee=False
		list_platoon_names = sorted(dict_platoons_done.keys())
		phase_names_already_displayed=[]
		list_txt=[] #[[joueur, peloton, txt], ...]
		list_err=[]
		for platoon_name in dict_platoons_done:
			#print('platoon_name='+platoon_name)
			phase_name=platoon_name[0:3]
			if not phase_name in phase_names_already_displayed:
				#list_txt.append('\n**Phase '+platoon_name[3]+'**')
				phase_names_already_displayed.append(phase_name)
			
			for perso in dict_platoons_done[platoon_name]:
				if '' in dict_platoons_done[platoon_name][perso]:
					if platoon_name in dict_platoons_allocation:
						# if perso == 'Faucon Millenium de Han':
							# print (platoon_name+': '+perso)
							# print(dict_platoons_done[platoon_name])
							# print(dict_platoons_allocation[platoon_name])
						if perso in dict_platoons_allocation[platoon_name]:
							for allocated_player in dict_platoons_allocation[platoon_name][perso]:
								if not allocated_player in dict_platoons_done[platoon_name][perso]:
									erreur_detectee=True
									alternative_allocation=''
									#if allocated_player in dict_player_allocations:
									#TO-DO ne marche pas en regardant es allocatoins sur plusieurs jours
									#	if perso in dict_player_allocations[allocated_player]:
									#		alternative_allocation=" *(mais l'a mis en "+dict_player_allocations[allocated_player][perso]+')*'

									#print(allocated_player+' n\'a pas affecté '+perso+' en '+platoon_name+alternative_allocation)
									if allocated_player in dict_players:
										list_txt.append([allocated_player, platoon_name, '**'+dict_players[allocated_player][2]+'** n\'a pas affecté '+perso+' en '+platoon_name+alternative_allocation])
									else: #joueur non-défini dans gsheets, on l'affiche quand même
										list_txt.append([allocated_player, platoon_name, '**'+allocated_player+'** n\'a pas affecté '+perso+' en '+platoon_name+alternative_allocation])
						else:
							erreur_detectee=True
							list_err.append('ERR: '+perso+' n\'a pas été affecté')
							print('ERR: '+perso+' n\'a pas été affecté')
							print(dict_platoons_allocation[platoon_name].keys())
		
		full_txt=''
		cur_phase=0
		for txt in sorted(list_txt, key=lambda x: (x[1][:4], x[0], x[1])):
			if cur_phase!=int(txt[1][3]):
				cur_phase=int(txt[1][3])
				full_txt+='\n---- **Phase '+str(cur_phase)+'**\n'
				
			position=txt[1].split('-')
			if position=='top':
				open_for_position=list_open_territories[0]
			elif position=='mid':
				open_for_position=list_open_territories[1]
			else: #bottom
				open_for_position=list_open_territories[2]
			if cur_phase<open_for_position:
				full_txt+=txt[2]+' -- *et c\'est trop tard*\n'
			else:
				full_txt+=txt[2]+'\n'
			
		if erreur_detectee:
			for txt in sorted(set(list_err)):
				full_txt+=txt+'\n'
		else:
			full_txt+='Aucune erreur de peloton\n'
			
		for txt in split_txt(full_txt, 2000):
			await ctx.send(txt)
			
		
		await ctx.message.add_reaction(emoji_check)
		
bot.loop.create_task(bot_loop_60())
bot.run(TOKEN)