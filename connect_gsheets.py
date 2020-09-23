# tutorial: https://www.twilio.com/blog/2017/02/an-easy-way-to-read-and-write-to-a-google-spreadsheet-in-python.html
# bug: https://github.com/burnash/gspread/issues/513

import gspread
from oauth2client.service_account import ServiceAccountCredentials

client=None

def load_config_teams():
	global client
	global file_config
	
	if client == None:
		# use creds to create a client to interact with the Google Drive API
		scope = ['https://spreadsheets.google.com/feeds',
				 'https://www.googleapis.com/auth/drive']
		creds = ServiceAccountCredentials.from_json_keyfile_name('GuiOnBot-46e15dffc1ad.json', scope)
		client = gspread.authorize(creds)

	file = client.open("GuiOnBot config")	
	feuille=file.worksheet("teams")

	dict_team_tw={} # [[catégorie, nombre nécessaire, {key=nom, value=[id, étoiles, gear, relic, [liste zeta]]}]]

	liste_dict_feuille=feuille.get_all_records()
	#print(liste_dict_feuille)
	liste_teams=set([(lambda x:x['Nom équipe'])(x) for x in liste_dict_feuille])
	print('\nDBG: liste_teams='+str(liste_teams))
	for team in liste_teams:
		liste_dict_team=list(filter(lambda x : x['Nom équipe'] == team, liste_dict_feuille))
		#print(liste_dict_team)
		complete_liste_categories=[(lambda x:x['Catégorie'])(x) for x in liste_dict_team]
		liste_categories=sorted(set(complete_liste_categories), key=lambda x: complete_liste_categories.index(x))
		
		#print('liste_categories='+str(liste_categories))
		dict_team_tw[team]=[[] for i in range(len(liste_categories))]
		index_categorie=-1
		for categorie in liste_categories:
			index_categorie+=1
			dict_team_tw[team][index_categorie]=[categorie, 0, {}]
			liste_dict_categorie=list(filter(lambda x : x['Catégorie'] == categorie, liste_dict_team))
			index_perso=0
			for dict_perso in liste_dict_categorie:
				index_perso+=1
				dict_team_tw[team][index_categorie][1] = dict_perso['Min Catégorie']
				dict_team_tw[team][index_categorie][2][dict_perso['Nom']]=[index_perso, dict_perso['Etoiles'], dict_perso['Gear'], []]
				for zeta in ['Zeta1', 'Zeta2', 'Zeta3']:
					if dict_perso[zeta]!='':
						dict_team_tw[team][index_categorie][2][dict_perso['Nom']][3].append(dict_perso[zeta])
		#print('DBG: dict_team_tw='+str(dict_team_tw))
	return liste_teams, dict_team_tw

def load_config_players():
	global client
	
	if client == None:
		# use creds to create a client to interact with the Google Drive API
		scope = ['https://spreadsheets.google.com/feeds',
				 'https://www.googleapis.com/auth/drive']
		creds = ServiceAccountCredentials.from_json_keyfile_name('GuiOnBot-46e15dffc1ad.json', scope)
		client = gspread.authorize(creds)

	file = client.open("GuiOnBot config")
	feuille=file.worksheet("players")

	dict_players={} # {key=IG name, value=[allycode, discord name, discord id]]

	liste_dict_feuille=feuille.get_all_records()
	#print(liste_dict_feuille)
	for ligne in liste_dict_feuille:
		if ligne['Discord name']!='':
			dict_players[ligne['IG name']]=[ligne['Allycode'], ligne['Discord name'], ligne['Discord ID']]
		
	return dict_players
	
#print(load_config_teams())	
		
