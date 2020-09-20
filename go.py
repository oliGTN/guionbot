from swgohhelp import SWGOHhelp, settings
import sys
import json
import time
import os
from math import ceil
from connect_gsheets import load_config_teams

creds = settings('GuiOnEnsai','4yj6GfUSezVjPJKSKpR8','123','abc')
client = SWGOHhelp(creds)
inactive_duration=36 #hours

dict_guidevoyage={} # [catégorie, nombre nécessaire, étoiles, relic, niveau capa, PG, module]
dict_guidevoyage['GAS']=[[[], [], [], []], [[], [], [], []]]
dict_guidevoyage['GAS'][0][0]=["Persos", 10, 7, -1, -1, 17700, -1, ['ASAJVENTRESS', 'PADMEAMIDALA', 'GENERALKENOBI', 'B2SUPERBATTLEDROID', 'MAGNAGUARD', 'C3POLEGENDARY', 'AHSOKATANO', 'DROIDEKA', 'B1BATTLEDROIDV2', 'SHAAKTI']]
dict_guidevoyage['GAS'][0][1]=["Vaisseau amiral", 1, 7, -1, -1, 40000, -1, ['CAPITALJEDICRUISER', 'CAPITALNEGOTIATOR']]
dict_guidevoyage['GAS'][0][2]=["Eta-2", 1, 7, -1, -1, 40000, -1, ['JEDISTARFIGHTERANAKIN']]
dict_guidevoyage['GAS'][0][3]=["Vaisseaux", 3, 7, -1, -1, 40000, -1, ['JEDISTARFIGHTERAHSOKATANO', 'UMBARANSTARFIGHTER', 'ARC170REX', 'BLADEOFDORIN', 'JEDISTARFIGHTERCONSULAR', 'ARC170CLONESERGEANT', 'YWINGCLONEWARS']]
dict_guidevoyage['GAS'][1][0]=["Persos", 10, 7, 3, 8, 22000, 6, ['ASAJVENTRESS', 'PADMEAMIDALA', 'GENERALKENOBI', 'B2SUPERBATTLEDROID', 'MAGNAGUARD', 'C3POLEGENDARY', 'AHSOKATANO', 'DROIDEKA', 'B1BATTLEDROIDV2', 'SHAAKTI']]
dict_guidevoyage['GAS'][1][1]=["Vaisseau amiral", 1, 7, -1, 8, 50000, -1, ['CAPITALJEDICRUISER', 'CAPITALNEGOTIATOR']]
dict_guidevoyage['GAS'][1][2]=["Eta-2", 1, 7, -1, 8, 50000, -1, ['JEDISTARFIGHTERANAKIN']]
dict_guidevoyage['GAS'][1][3]=["Vaisseaux", 3, 7, -1, 8, 50000, -1, ['JEDISTARFIGHTERAHSOKATANO', 'UMBARANSTARFIGHTER', 'ARC170REX', 'BLADEOFDORIN', 'JEDISTARFIGHTERCONSULAR', 'ARC170CLONESERGEANT', 'YWINGCLONEWARS']]
dict_guidevoyage['Luke']=[[[], []]]
dict_guidevoyage['Luke'][0][0]=["Persos", 9, 7, 3, -1, -1, -1, ['COMMANDERLUKESKYWALKER', 'HOTHLEIA', 'HOTHHAN', 'WAMPA', 'CHEWBACCALEGENDARY', 'C3POLEGENDARY', 'VADER', 'ADMINISTRATORLANDO', 'HERMITYODA']]
dict_guidevoyage['Luke'][0][1]=["Vaisseaux", 2, 7, -1, -1, -1, -1, ['XWINGRED2', 'MILLENNIUMFALCON']]

dict_team_gt={} # [[catégorie, nombre nécessaire, {key=nom, value=[id, étoiles, gear, relic, [liste zeta]]}]]
dict_team_gt['JKR']=[[], []]
dict_team_gt['JKR'][0]=['Requis', 4, {}]
dict_team_gt['JKR'][0][2]['JEDIKNIGHTREVAN']=[1, 7, 12, ['G\u00e9n\u00e9ral', 'H\u00e9ros', 'Concentration directe']]
dict_team_gt['JKR'][0][2]['JOLEEBINDO']=     [2, 7, 12, ['\u00c7a doit faire mal']]
dict_team_gt['JKR'][0][2]['BASTILASHAN']=    [3, 7, 12, []]
dict_team_gt['JKR'][0][2]['GRANDMASTERYODA']=[4, 7, 12, ['M\u00e9ditation de combat']]
dict_team_gt['JKR'][1]=['Important', 1, {}]
dict_team_gt['JKR'][1][2]['GENERALKENOBI']=[1, 7, 11, ['Soresu']]
dict_team_gt['JKR'][1][2]['HERMITYODA']=   [2, 7, 11, ['Fais-le. Ou ne le fais pas.']]
dict_team_gt['JKR'][1][2]['EZRABRIDGERS3']=  [3, 7, 11, []]
dict_team_gt['JKR'][1][2]['ANAKINKNIGHT']= [4, 7, 11, []]
dict_team_gt['JKR'][1][2]['BARRISSOFFEE']= [5, 7, 11, []]


def dict2str(d, depth, idx):
	#sys.stderr.write('DBG: '+str(d)+'\n')
	ret=''

	if isinstance(d, list):
		for ele in d:
			ret+=dict2str(ele, depth, d.index(ele))+'\n\n'
	elif isinstance(d, dict):
		for key in d:
			if isinstance(d[key], list):
				ret+='\t'*depth+'{}({})\n{}'.format(key, idx, dict2str(d[key], depth+1, ''))+'\n'
			elif isinstance(d[key], dict):
				ret+='\t'*depth+'{}({})\n{}'.format(key, idx, dict2str(d[key], depth+1, ''))+'\n'
			else:
				ret+='\t'*depth+'{}({})\t{}'.format(key, idx, str(d[key]))+'\n'
		ret=ret[:-1]
	else:
		ret='\t'*depth+d
	
	return ret

def refresh_cache(nb_minutes_delete, nb_minutes_refresh, refresh_rate_minutes):
	#CLEAN OLD FILES NOT ACCESSED FOR LONG TIME
	#Need to keep KEEPDIR to prevent removal of the directory by GIT
	for filename in os.listdir('CACHE'):
		#print(filename)
		if filename!='KEEPDIR':
			file_path='CACHE'+os.path.sep+filename
			file_stats=os.stat(file_path)

			delta_atime_sec=time.time()-file_stats.st_atime
			if (delta_atime_sec/60) > nb_minutes_delete:
				print ('Remove '+filename+' (not accessed for '+str(delta_atime_sec/60)+' minutes)')
				os.remove(file_path)
			
	#LOOP through Guild files to recover player allycodes
	list_allycodes=[]
	for filename in os.listdir('CACHE'):
		#print(filename)
		if filename[0]=='G':
			file_path='CACHE'+os.path.sep+filename
			for line in open(file_path).readlines():
				if line[13:21]=='allyCode':
					list_allycodes.append(line[24:33])
	#remove duplicates
	list_allycodes=[x for x in set(list_allycodes)]
	#print('DBG: list_allycodes='+str(list_allycodes))
	
	#Compute the amount of files to be refreshed based on global refresh rate
	nb_refresh_files=ceil(len(list_allycodes) / nb_minutes_refresh * refresh_rate_minutes)
	print('Refreshing '+str(nb_refresh_files)+' files')

	#LOOP through files to check modification date
	list_filenames_mtime=[]
	for filename in os.listdir('CACHE'):
		if filename[:-5] in list_allycodes:
			file_path='CACHE'+os.path.sep+filename
			file_stats=os.stat(file_path)
			list_filenames_mtime.append([filename, file_stats.st_mtime])
			list_allycodes.remove(filename[:-5])
	#sort by mtime
	list_filenames_mtime=sorted(list_filenames_mtime, key=lambda x:x[1])
	#print('DBG: list_filenames_mtime='+str(list_filenames_mtime))
	
	remaining_files_to_refresh=nb_refresh_files
	#Start creating non-existing files
	for allycode in list_allycodes[:remaining_files_to_refresh]:
		#print('DBG: create '+allycode)
		load_player(allycode)
		remaining_files_to_refresh-=1
		
	#Then refresh oldest existing files
	for filename_mtime in list_filenames_mtime[:remaining_files_to_refresh]:
		allycode=filename_mtime[0][:-5]
		file_path='CACHE'+os.path.sep+filename_mtime[0]
		#print('DBG: refresh '+allycode)
		os.remove(file_path)
		load_player(allycode)
		remaining_files_to_refresh-=1
	
def stats_cache():
	sum_size=0
	nb_files=0
	for filename in os.listdir('CACHE'):
		#print(filename)
		if filename!='KEEPDIR':
			file_path='CACHE'+os.path.sep+filename
			file_stats=os.stat(file_path)
			nb_files+=1
			sum_size+=file_stats.st_size
	return 'Total CACHE: '+str(nb_files)+' files, '+str(int(sum_size/1024/1024*10)/10)+' MB'

def load_player(allycode):
	f = None
	try:
		f = open('CACHE'+os.path.sep+allycode+'.json', 'r')
		sys.stderr.write('loading cache for '+str(allycode)+'...')
		ret_player = json.load(f)
	except IOError:
		sys.stderr.write('requesting data for '+str(allycode)+'...')
		ret_player=client.get_data('player', allycode)[0]
		f = open('CACHE'+os.path.sep+allycode+'.json', 'w')
		f.write(json.dumps(ret_player, indent=4, sort_keys=True))
	finally:
		if not f is None:
			f.close()
	sys.stderr.write(' '+ret_player['name']+'\n')
	return ret_player
	
def load_guild(allycode, load_players):
	is_error=False
	try:
		f = open('CACHE'+os.path.sep+'G'+allycode+'.json', 'r')
		sys.stderr.write('>Loading guild data for allycode '+allycode+'...\n')
		ret_guild = json.load(f)
		f.close()
	except IOError:
		sys.stderr.write('>Requesting guild data for allycode '+allycode+'...\n')
		client_data=client.get_data('guild', allycode)
		if isinstance(client_data, dict):
			#error code
			ret_guild=str(client)
			sys.stderr.write('ERR: '+ret_guild+'\n')
			is_error=True
		else: #list
			ret_guild=client_data[0]
			f = open('CACHE'+os.path.sep+'G'+allycode+'.json', 'w')
			f.write(json.dumps(ret_guild, indent=4, sort_keys=True))
			sys.stderr.write('Guild found: '+ret_guild['name']+'\n')
			f.close()
	
	if load_players and not is_error:
		#add player data after saving the guild in json
		total_players=len(ret_guild['roster'])
		sys.stderr.write('Total players in guild: '+str(total_players)+'\n')
		i_player=0
		for player in ret_guild['roster']:
			i_player=i_player+1
			sys.stderr.write(str(i_player)+': ')
			player['dict_player']=load_player(str(player['allyCode']))

	return ret_guild

def get_guild_stats_char(guild, lookup_character):
	guild_stats={}
	for player in guild['roster']:
		for character in player['dict_player']['roster']:
			if (character['defId']==lookup_character) or (lookup_character==''):
				key='G'+"{:02d}".format(character['gear'])
				if key not in guild_stats:
					guild_stats[key]=1
				else:
					guild_stats[key]+=1

				if character['gear']==13:
					key='Tier '+str(character['relic']['currentTier']-2)
					if key not in guild_stats:
						guild_stats[key]=1
					else:
						guild_stats[key]+=1
	return guild_stats
	
def get_guild_char_list(guild):
	char_list=[]
	for player in guild['roster']:
		for character in player['dict_player']['roster']:
			if (not character['nameKey'] in char_list):
				char_list.append(character['nameKey'])
	return sorted(char_list)
	
def get_guild_gp(guild):
	guild_stats={}
	for player in guild['roster']:
		guild_stats[player['name']]=[player['gpChar'], player['gpShip'], (time.time() - player['dict_player']['lastActivity']/1000)/3600]
	return guild_stats

def get_guild_avg_arena(guild, arena):
	sum=0
	for player in guild['roster']:
		if player['dict_player']['arena'][arena]['rank'] is not None:
			sum+=player['dict_player']['arena'][arena]['rank']
	return int(sum/guild['members'])

def print_gp_graph(guild_stats):
	ret_print_gp_graph=''
	dict_gp_clusters={} #key=gp group, value=[nb active, nb inactive]
	for player in guild_stats:
		#print(guild_stats[player])
		gp=guild_stats[player][0]+guild_stats[player][1]
		gp_key=int(gp/500000)/2
		if gp_key in dict_gp_clusters:
			if guild_stats[player][2] < inactive_duration:
				dict_gp_clusters[gp_key][0] = dict_gp_clusters[gp_key][0] + 1
			else:
				dict_gp_clusters[gp_key][1] = dict_gp_clusters[gp_key][1] + 1
		else:
			if guild_stats[player][2] < inactive_duration:
				dict_gp_clusters[gp_key] = [1, 0]
			else:
				dict_gp_clusters[gp_key] = [0, 1]

	#print (dict_gp_clusters)	
	#write line from the top = max bar size
	max_cluster=max(dict_gp_clusters.values(), key=lambda p: p[0]+p[1])
	line_graph=max_cluster[0]+max_cluster[1]
	max_key=max(dict_gp_clusters.keys())
	while line_graph > 0:
		if (line_graph % 5) == 0:
			line_txt="{:02d}".format(line_graph)
		else:
			line_txt='  '
		for gp_key_x2 in range(0, int(max_key*2)+1):
			gp_key=gp_key_x2 / 2
			if gp_key in dict_gp_clusters:
				#print(dict_gp_clusters[gp_key])
				if dict_gp_clusters[gp_key][0] >= line_graph:
					line_txt = line_txt + '    #'
				elif dict_gp_clusters[gp_key][0]+dict_gp_clusters[gp_key][1] >= line_graph:
					line_txt = line_txt + '    .'
				else:
					line_txt = line_txt + '     '
			else:
				line_txt = line_txt + '     '
		ret_print_gp_graph+=line_txt+'\n'
		line_graph=line_graph - 1
	ret_print_gp_graph+='--'+'-----'*int(max(dict_gp_clusters.keys())*2+1)+'\n'

	line_txt='   '
	for gp_key_x2 in range(0, int(max_key*2)+1):
		gp_key=gp_key_x2 / 2
		if int(gp_key)==gp_key:
			line_txt=line_txt+'   '+str(int(gp_key))+' '
		else:
			line_txt=line_txt+'  '+str(gp_key)
	ret_print_gp_graph+=line_txt+'\n'

	line_txt='   '
	for gp_key_x2 in range(0, int(max_key*2)+1):
		gp_key=gp_key_x2 / 2
		if int(gp_key)==gp_key:
			line_txt=line_txt+'  '+str(gp_key+0.5)
		else:
			line_txt=line_txt+'   '+str(int(gp_key+0.5))+' '
	ret_print_gp_graph+=line_txt+'\n'
	
	return ret_print_gp_graph

def function_gt(txt_alycode, txt_op_allycode):
	ret_function_gt=''
	## GUERRE DE TERRITOIRE ##
	my_allycode=txt_alycode
	opponent_allycode=txt_op_allycode
	
	#Get data for my guild
	guild = load_guild(my_allycode, True)
	if isinstance(guild, str):
		#error wile loading guild data
		return 'ERREUR: guilde non trouvée pour code allié '+my_allycode
		
	#Get data for opponent guild
	opponent_guild = load_guild(opponent_allycode, True)
	if isinstance(opponent_guild, str):
		#error wile loading guild data
		return 'ERREUR: guilde non trouvée pour code allié '+opponent_allycode

	ret_function_gt+='\n'+guild['name']+' vs '+opponent_guild['name']+'\n'
	ret_function_gt+='==Overview==\n'
	ret_function_gt+='Members:         '+pad_txt(str(guild['members']), 8)+str(opponent_guild['members'])+'\n'
	ret_function_gt+='GP:              '+pad_txt(str(int(guild['gp']/100000)/10), 8)+str(int(opponent_guild['gp']/100000)/10)+'\n'
	ret_function_gt+='Avg arena chars: '+pad_txt(str(get_guild_avg_arena(guild, 'char')), 8)+str(get_guild_avg_arena(opponent_guild, 'char'))+'\n'
	ret_function_gt+='Avg arena ships: '+pad_txt(str(get_guild_avg_arena(guild, 'ship')), 9)+str(get_guild_avg_arena(opponent_guild, 'ship'))+'\n'


	guild_stats=get_guild_stats_char(guild, '')
	op_guild_stats=get_guild_stats_char(opponent_guild, '')
	ret_function_gt+='\n==Gears==\n'
	for key in ['G11', 'G12', 'G13']:
		if key in guild_stats:
			line=pad_txt(key, 8)+pad_txt(str(guild_stats[key]), 9)
		else:
			line=pad_txt(key, 8)+'-       '
		if key in op_guild_stats:
			line=line+str(op_guild_stats[key])
		else:
			line=line+'-'
		ret_function_gt+=line+'\n'

	ret_function_gt+='\n==Relics==\n'
	for key in ['Tier 0', 'Tier 1', 'Tier 2', 'Tier 3', 'Tier 4', 'Tier 5', 'Tier 6', 'Tier 7']:
		if key in guild_stats:
			line=pad_txt(key, 8)+pad_txt(str(guild_stats[key]), 8)
		else:
			line=pad_txt(key, 8)+'-      '
		if key in op_guild_stats:
			line=line+str(op_guild_stats[key])
		else:
			line=line+'-'
		ret_function_gt+=line+'\n'

#	for lookup_character in ['JEDIKNIGHTREVAN', 'PADMEAMIDALA', 'COMMANDERLUKESKYWALKER', 'JEDIKNIGHTLUKE', 'GENERALSKYWALKER', 'GEONOSIANBROODALPHA', 'DARTHREVAN', 'DARTHMALAK', 'DARTHTRAYA', 'ENFYSNEST', 'GRIEVOUS', 'GLREY', 'SUPREMELEADERKYLOREN' ]:
	for lookup_character in []:
		ret_function_gt+='\n=='+lookup_character+'==\n'
		guild_stats=get_guild_stats_char(guild, lookup_character)
		gear_list=sorted(guild_stats.keys())

		op_guild_stats=get_guild_stats_char(opponent_guild, lookup_character)
		gear_list=sorted(gear_list + list(set(op_guild_stats.keys()) - set(gear_list)))
		
		if len(gear_list)>0:
			for key in gear_list:
				if key in guild_stats:
					line=pad_txt(key, 8)+pad_txt(str(guild_stats[key]), 8)
				else:
					line=pad_txt(key, 8)+'-      '
				if len(opponent_guild)>0:
					if key in op_guild_stats:
						line=line+str(op_guild_stats[key])
					else:
						line=line+'-'
				ret_function_gt+=line+'\n'
		else:
			ret_function_gt+='none\n'

	guild_stats=get_guild_gp(guild)
	op_guild_stats=get_guild_gp(opponent_guild)
	
	# print('\n==GP stats for Excel==')
	# print(guild['name']+',Chars,Ships')
	# for key in guild_stats:
		# print(key+','+str(guild_stats[key][0])+','+str(guild_stats[key][1]))

	# print('\n'+opponent_guild['name']+',Chars,Ships')
	# for key in op_guild_stats:
			# print(key+','+str(op_guild_stats[key][0])+','+str(op_guild_stats[key][1]))
			
	#compute ASCII graphs
	ret_function_gt+='\n==GP stats '+guild['name']+'==  (# = actif | . = inactif depuis '+str(inactive_duration)+' heures)\n'
	ret_function_gt+=print_gp_graph(guild_stats)+'\n'

	ret_function_gt+='\n==GP stats '+opponent_guild['name']+'==\n'
	ret_function_gt+=print_gp_graph(op_guild_stats)+'\n'
	
	return ret_function_gt

def function_ct(txt_alycode):
	ret_function_ct=''
	
	my_allycode=sys.argv[2]

	#Get data for my guild
	guild = load_guild(my_allycode, True)
	if isinstance(guild, str):
		#error wile loading guild data
		return 'ERREUR: guilde non trouvée pour code allié '+my_allycode
	
	char_list=get_guild_char_list(guild)
	
	line='Member,GP'
	for char in char_list:
		line=line+','+char
	ret_function_ct+=line+'\n'

	for player in guild['roster']:
		dict_char_player={}
		for character in player['dict_player']['roster']:
			if character['combatType']==1:
				#character
				dict_char_player[character['nameKey']]=str(character['rarity'])+'* G'+"{:02d}".format(character['gear'])
				if character['gear']==13:
					#Ajout du niveau de relique
					dict_char_player[character['nameKey']]+='('+str(character['relic']['currentTier']-2)+')'
			elif character['combatType']==2:
				#ship
				dict_char_player[character['nameKey']]=str(character['rarity'])+'*'
			else:
				print('ERR combatType inconnu pour '+character['nameKey'])
		line=player['name']+','+str(player['gp'])
		for char in char_list:
			if char in dict_char_player:
				line=line+','+dict_char_player[char]
			else:
				line=line+','
		ret_function_ct+=line+'\n'
	
	return ret_function_ct

def function_gv(txt_allycode, character_name):
	ret_function_gv=''

	my_allycode=txt_allycode

	if character_name in dict_guidevoyage:
		objectifs=dict_guidevoyage[character_name]
	else:
		sys.stderr.write('ERR: Guide de voyage inconnu pour '+character_name+'\n')
		sys.exit(1)		
	
	#Get data for my guild
	guild = load_guild(my_allycode, True)
	if isinstance(guild, str):
		#error wile loading guild data
		return 'ERREUR: guilde non trouvée pour code allié '+my_allycode
	
	ret_function_gv+='Joueur'
	nb_levels=len(objectifs)
	nb_sub_obj=len(objectifs[0])
	#print('DBG: nb_levels='+str(nb_levels)+' nb_sub_obj='+str(nb_sub_obj))
	for i_level in range(0,nb_levels):
		for i_sub_obj in range(0, nb_sub_obj):
			nom_sub_obj=objectifs[i_level][i_sub_obj][0]
			ret_function_gv+=','+nom_sub_obj
			if i_level==0:
				ret_function_gv+=' min'
			else:
				ret_function_gv+=' reco'
		ret_function_gv+=',Total'
		if i_level==0:
			ret_function_gv+=' min'
		else:
			ret_function_gv+=' reco'
	ret_function_gv+='\n'
	
	for player in guild['roster']:
		ret_function_gv+=player['name']
		
		tab_progress_player=[[[] for i in range(nb_sub_obj)] for i in range(2)]
		
		for character in player['dict_player']['roster']:
			for i_level in range(0,nb_levels):
				for i_sub_obj in range(0, nb_sub_obj):
					#print('DBG: '+str(i_sub_obj))
					sub_obj=objectifs[i_level][i_sub_obj]
					progress=0
					progress_100=0
					if character['defId'] in sub_obj[7]:
						if sub_obj[2] != -1:
							progress_100=progress_100+1
							progress=progress+min(1, character['rarity']/sub_obj[2])
						if sub_obj[3] != -1:
							progress_100=progress_100+1
							progress=progress+min(1, character['relic']['currentTier']/sub_obj[3])
						if sub_obj[4] != -1:
							for skill in character['skills']:
								progress_100=progress_100+1
								progress=progress+min(1, skill['tier']/sub_obj[4])
						if sub_obj[5] != -1:
							progress_100=progress_100+1
							progress=progress+min(1, character['gp']/sub_obj[5])
						if sub_obj[6] != -1:
							for mod in character['mods']:
								progress_100=progress_100+1
								progress=progress+min(1, mod['pips']/sub_obj[6])
						tab_progress_player[i_level][i_sub_obj].append(progress/progress_100)
						#print('DBG: '+character['defId']+':'+str(tab_progress_player))
						#print('DBG: '+character['defId']+':'+str(progress/progress_100))

		for i_level in range(0,nb_levels):
			total_progress=0
			total_progress_100=0
			for i_sub_obj in range(0, nb_sub_obj):
				tab_progress_sub_obj=tab_progress_player[i_level][i_sub_obj]
				#print('DBG: '+str(tab_progress_sub_obj))
				min_nb_sub_obj=objectifs[i_level][i_sub_obj][1]
				cur_nb_sub_obj=len(tab_progress_player[i_level][i_sub_obj])
				#print('DBG: '+str(min_nb_sub_obj)+':'+str(cur_nb_sub_obj))
				if cur_nb_sub_obj < min_nb_sub_obj:
					tab_progress_sub_obj = tab_progress_sub_obj	+ [0]*(min_nb_sub_obj - cur_nb_sub_obj)
				else:
					tab_progress_sub_obj = sorted(tab_progress_sub_obj, reverse=True)[0:min_nb_sub_obj]
				#print('DBG: '+str(tab_progress_sub_obj))
				progress=sum(tab_progress_sub_obj)
				ret_function_gv+=','+str(int(progress/min_nb_sub_obj*100))+'%'
				total_progress=total_progress+progress
				total_progress_100=total_progress_100+min_nb_sub_obj
			ret_function_gv+=','+str(int(total_progress/total_progress_100*100))+'%'
		ret_function_gv+='\n'
		
	return ret_function_gv

def pad_txt(txt, size):
	if len(txt) < size:
		ret_pad_txt=txt+' '*(size-len(txt))
	else:
		ret_pad_txt=txt[:size]
	
	return ret_pad_txt

def pad_txt2(txt):
	size_digits=[0,0,0,0,0,0,0,0,0,0]
	size_digits[0]=12.3
	size_digits[1]=7.1
	size_digits[2]=10.7
	size_digits[3]=10.5
	size_digits[4]=11.9
	size_digits[5]=10.6
	size_digits[6]=11.4
	size_digits[7]=10.6
	size_digits[8]=11.4
	size_digits[9]=11.4
	size_space=4.5
	
	size_txt=0
	nb_digits=0
	for i in range(10):
		size_txt+=txt.count(str(i))*size_digits[i]
		nb_digits+=txt.count(str(i))
		#print ('DBG: i='+str(i)+' size_txt='+str(size_txt)+' nb_digits='+str(nb_digits))
	
	max_size=nb_digits*max(size_digits)
	espaces_additionnels=round((max_size-size_txt)/size_space)
	#print('DBG: max_size='+str(max_size)+' espaces_additionnels='+str(espaces_additionnels))
	ret_pad_txt=txt+'\xa0'*espaces_additionnels
	#print('DBG: x'+txt+'x > x'+ret_pad_txt+'x')

	return ret_pad_txt

def function_gtt(txt_allycode, character_name):
	ret_function_gtt=''

	my_allycode=txt_allycode

	#Recuperation des dernieres donnees sur gdrivedict_team_gt
	liste_team_gt, dict_team_gt=load_config_teams()
	
	if character_name in dict_team_gt:
		objectifs=dict_team_gt[character_name]
		#print(objectifs)
	else:
		return 'ERREUR: team '+character_name+' inconnue. Liste='+str(liste_team_gt)	
	
	#Get data for my guild
	guild = load_guild(my_allycode, True)
	if isinstance(guild, str):
		#error wile loading guild data
		return 'ERREUR: guilde non trouvée pour code allié '+my_allycode
	
	nb_levels=len(objectifs)
	#print('DBG: nb_levels='+str(nb_levels))
	
	#Affichage des prérequis
	ret_function_gtt+='**Team: '+character_name+'**\n'
	for i_level in range(0,nb_levels):
		#print('DBG: i_level='+str(i_level))
		#print('DBG: obj='+str(objectifs[i_level]))
		nb_sub_obj=len(objectifs[i_level][2])
		#print('DBG: nb_sub_obj='+str(nb_sub_obj))
		ret_function_gtt+='**'+objectifs[i_level][0]+'**\n'
		for i_sub_obj in range(0, nb_sub_obj):
			for perso in objectifs[i_level][2]:
				if objectifs[i_level][2][perso][0] == i_sub_obj+1:
					perso_rarity=objectifs[i_level][2][perso][1]
					perso_gear=objectifs[i_level][2][perso][2]
					perso_zetas=objectifs[i_level][2][perso][3]
					ret_function_gtt+='**'+objectifs[i_level][0][0]+str(i_sub_obj+1)+'**: '+perso+' ('+str(perso_rarity)+'*, G'+str(perso_gear)+', zetas='+str(perso_zetas)+')\n'

	#ligne d'entete
	list_player_names=[(lambda x:x['name'])(x) for x in guild['roster']]
	ret_function_gtt+='\n'
	for i_level in range(0,nb_levels):
		nb_sub_obj=len(objectifs[i_level][2])
		#print('DBG: nb_sub_obj='+str(nb_sub_obj))
		for i_sub_obj in range(0, nb_sub_obj):
			#print('DBG:'+str(objectifs[i_level][0][0]+str(i_sub_obj)))
			nom_sub_obj=objectifs[i_level][0][0]+str(i_sub_obj+1)
			ret_function_gtt+=pad_txt2(nom_sub_obj)+'       |'
			
	ret_function_gtt+='GLOB|Joueur\n'
	
	#resultats par joueur
	tab_lines=[]
	for player in guild['roster']:
		line=''
		#print('DBG: '+player['name'])
		
		#INIT tableau des resultats
		tab_progress_player=[[] for i in range(nb_levels)]
		for i_level in range(0,nb_levels):
			nb_sub_obj=len(objectifs[i_level][2])
			tab_progress_player[i_level]=[[0, '.\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0\xa0.'] for i in range(nb_sub_obj)]
		
		#boucle sur les persos du joueur
		for character in player['dict_player']['roster']:
			for i_level in range(0,nb_levels):				
				dict_perso_objectif=objectifs[i_level][2]

				progress=0
				progress_100=0
				#print(character['nameKey'])
				#print(dict_perso_objectif)
				if character['nameKey'] in dict_perso_objectif:
					perso=character['nameKey']
					i_sub_obj=dict_perso_objectif[perso][0]
					#print(dict_perso_objectif[perso])
					req_rarity=dict_perso_objectif[perso][1]
					player_rarity=character['rarity']
					if req_rarity != -1:
						progress_100=progress_100+1
						progress=progress+min(1, player_rarity/req_rarity)
						
					req_gear=dict_perso_objectif[perso][2]
					player_gear=character['gear']
					if req_gear != -1:
						progress_100=progress_100+1
						progress=progress+min(1, player_gear/req_gear)
					
					req_zetas=dict_perso_objectif[perso][3]
					player_nb_zetas=0
					progress_100+=len(req_zetas)
					for skill in character['skills']:
						if skill['nameKey'] in req_zetas:
							if skill['tier'] == 8:
								player_nb_zetas+=1
								progress+=1
							
					tab_progress_player[i_level][i_sub_obj-1][0] = progress/progress_100
					tab_progress_player[i_level][i_sub_obj-1][1] = str(player_rarity)+'.'+"{:02d}".format(player_gear)+'.'+str(player_nb_zetas)
					#print('DBG: '+character['defId']+':'+str(tab_progress_player))
		
		#print(tab_progress_player)
		progress=0
		progress100=0
		progress_nogo=False
		for i_level in range(0,nb_levels):
			nb_sub_obj=len(objectifs[i_level][2])
			for i_sub_obj in range(0, nb_sub_obj):
				tab_progress_sub_obj=tab_progress_player[i_level][i_sub_obj]
				#print('DBG: '+str(tab_progress_sub_obj))
				#line+=pad_txt(str(int(tab_progress_sub_obj[0]*100))+'%', 8)
				if tab_progress_sub_obj[0] == 1:
					line+='**'+pad_txt2(tab_progress_sub_obj[1])+'**|'
				else:
					line+=pad_txt2(tab_progress_sub_obj[1])+'|'
					
			min_perso = objectifs[i_level][1]
			#print('DBG: '+str(tab_progress_player[i_level]))
			tab_progress_player_values=[(lambda f:f[0])(x) for x in tab_progress_player[i_level]]
			progress+=sum(sorted(tab_progress_player_values)[-min_perso:])
			progress100+=min_perso
			if 0.0 in sorted(tab_progress_player_values)[-min_perso:]:
				progress_nogo=True
			
		if progress_nogo:
			global_progress=0
			line+='\N{CROSS MARK}'
		else:
			global_progress=int(progress/progress100*100)
			if global_progress==100:
				line+='\N{GREEN HEART}'
			elif global_progress>=80:
				line+='\N{LARGE ORANGE DIAMOND}'
			else:
				line+='\N{CROSS MARK}'

		line+='|'+player['name']+'\n'
		tab_lines.append([global_progress, line])
		
	for progress, txt in sorted(tab_lines, reverse=True):
		ret_function_gtt+=txt
	
	
	return ret_function_gtt

def split_txt(txt, max_size):
	ret_split_txt=[]
	remaining_txt = txt
	while len(txt)> max_size:
		last_cr=-1
		for pos_char in range(0, max_size):
			if txt[pos_char]=='\n':
				last_cr=pos_char
		if last_cr==-1:
			ret_split_txt.append(txt[-3]+'...')
			txt=''
		else:
			ret_split_txt.append(txt[:last_cr])
			txt=txt[last_cr+1:]
	ret_split_txt.append(txt)
	
	return ret_split_txt
	
def print_help():
	print('Commande inconnue')
	print(sys.argv[0]+' gt <allycode> <opponent allycode>')
	print(sys.argv[0]+' ct <allycode>')
	print(sys.argv[0]+' gv <allycode> <character>')
	
########### MAIN #########
if len(sys.argv)>1:
	cmd=sys.argv[1]
	if cmd=='gt':
		for txt in split_txt(function_gt(sys.argv[2], sys.argv[3]), 1000):
			print(txt)
		
	elif cmd=='gtt':
		print(function_gtt(sys.argv[2], sys.argv[3]))

	elif cmd=='ct':
		## CHARACTER TABLE ##
		print(function_ct(sys.argv[2]))

	elif cmd=='gv':
		## GUIDE de VOYAGE ##
		print(function_gv(sys.argv[2], sys.argv[3]))
			
	else:
		print_help()
		sys.exit(1)	



