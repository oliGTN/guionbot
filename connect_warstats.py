import urllib.request
from html.parser import HTMLParser

warstats_tbs_url='https://goh.warstats.net/guilds/tbs/4090'
warstats_platoons_baseurl='https://goh.warstats.net/platoons/view/'

tab_dict_platoons=[] #de haut en bas

dict_noms_warstats={} #key=nom warstat, value=nom SwGOH.api en français
dict_noms_warstats['Admiral Ackbar']='Amiral Ackbar'
dict_noms_warstats['Ahsoka Tano\\\'s Jedi Starfighter']='Chasseur stellaire Jedi d\'Ahsoka Tano'
dict_noms_warstats['Anakin\\\'s Eta-2 Starfighter']='Chasseur Eta-2 d\'Anakin'
dict_noms_warstats['Biggs Darklighter\\\'s X-wing']='X-Wing de Biggs Darklighter'
dict_noms_warstats['Bistan\\\'s U-wing']='U-Wing de Bistan'
dict_noms_warstats['Captain Han Solo']='Capitaine Han Solo'
dict_noms_warstats['Cassian\\\'s U-wing']='U-wing de Cassian'
dict_noms_warstats['CC-2224 ']='CC-2224 "Cody"'
dict_noms_warstats['Chief Nebit']='Chef Nebit'
dict_noms_warstats['Clone Sergeant\\\'s ARC-170']='ARC-170 du Sergent clone'
dict_noms_warstats['Commander Luke Skywalker']='Commandant Luke Skywalker'
dict_noms_warstats['Coruscant Underworld Police']='Police de la pègre de Coruscant'
dict_noms_warstats['CT-7567 ']='CT-7567 "Rex"'
dict_noms_warstats['Emperor\\\'s Shuttle']='Navette de l’Empereur'
dict_noms_warstats['First Order SF TIE Fighter']='Chasseur TIE/S du Premier Ordre'
dict_noms_warstats['First Order TIE Fighter']='Chasseur TIE du Premier Ordre'
dict_noms_warstats['Garazeb ']='Garazeb "Zeb" Orrelios'
dict_noms_warstats['Gauntlet Starfighter']='Chasseur Gauntlet'
dict_noms_warstats['General Kenobi']='Général Kenobi'
dict_noms_warstats['Grand Master Yoda']='Grand Maître Yoda'
dict_noms_warstats['Han\\\'s Millennium Falcon']='Faucon Millenium de Han'
dict_noms_warstats['Hermit Yoda']='Yoda Ermite'
dict_noms_warstats['Hoth Rebel Scout']='Éclaireur rebelle de Hoth'
dict_noms_warstats['Hoth Rebel Soldier']='Soldat rebelle de Hoth'
dict_noms_warstats['Hound\\\'s Tooth']='Dent du Molosse'
dict_noms_warstats['Imperial TIE Fighter']='Chasseur TIE impérial'
dict_noms_warstats['Jawa Scavenger']='Pillard Jawa'
dict_noms_warstats['Jedi Consular\\\'s Starfighter']='Chasseur stellaire du Jedi Consulaire'
dict_noms_warstats['Jedi Knight Anakin']='Chevalier Jedi Anakin'
dict_noms_warstats['Jedi Knight Guardian']='Chevalier Jedi Gardien'
dict_noms_warstats['Jedi Knight Revan']='Chevalier Jedi Revan'
dict_noms_warstats['Kylo Ren\\\'s Command Shuttle']='Navette de commandement de Kylo Ren'
dict_noms_warstats['Luke Skywalker (Farmboy)']='Luke Skywalker (fermier)'
dict_noms_warstats['Obi-Wan Kenobi (Old Ben)']='Obi-Wan Kenobi (Vieux Ben)'
dict_noms_warstats['Plo Koon\\\'s Jedi Starfighter']='Chasseur stellaire Jedi de Plo Koon'
dict_noms_warstats['Poe Dameron\\\'s X-wing']='X-Wing de Poe Dameron'
dict_noms_warstats['Princess Leia']='Princesse Leia'
dict_noms_warstats['Rex\\\'s ARC-170']='ARC-170 de Rex'
dict_noms_warstats['Rey (Jedi Training)']='Rey (entraînement de Jedi)'
dict_noms_warstats['Rey (Scavenger)']='Rey (Pilleuse)'
dict_noms_warstats['Rey\\\'s Millennium Falcon']='Faucon Millenium de Rey'
dict_noms_warstats['Slave I']='Esclave\xa0I'
dict_noms_warstats['Stormtrooper Han']='Han en stormtrooper'
dict_noms_warstats['TIE Advanced x1']='TIE avancé x1'
dict_noms_warstats['TIE Reaper']='Faucheur TIE'
dict_noms_warstats['TIE Silencer']='TIE silencer'
dict_noms_warstats['Umbaran Starfighter']='Chasseur umbarien'
dict_noms_warstats['Veteran Smuggler Chewbacca']='Contrebandier vétéran Chewbacca'
dict_noms_warstats['Veteran Smuggler Han Solo']='Contrebandier vétéran Han Solo'
dict_noms_warstats['Wedge Antilles\\\'s X-wing']='X-Wing de Wedge Antilles'
dict_noms_warstats['Young Han Solo']='Han Solo jeune'
dict_noms_warstats['Young Lando Calrissian']='Lando Calrissian jeune'


class TBSPhaseParser(HTMLParser):
	dict_platoons={} #key="A1" to "C6", value={} key=perso, value=[player, ...]
	platoon_name=''
	char_name=''
	player_name=''
	current_phase=''
	state_parser=0
	#0: en recherche de div class=phases
	#1: en recherche de i class="far fa-dot-circle red-text text-small"
	#2: en recherche de a href
	#3: en recherche de div class="card platoon"
	#4: en recherche de div id
	#5: en recherche de div class="char" ou "char filled"
	#6: en recherche de img-title d'un perso rempli
	#7: en recherche de img-title d'un perso NON rempli
	#8: en recherche de div class=player
	#9: en recherche de data
		
	def handle_starttag(self, tag, attrs):
		if tag=='div':
			for name, value in attrs:
				if name=='class' and value=='phases':
					self.state_parser=1
		
		if self.state_parser==1:
			if tag=='i':
				for name, value in attrs:
					if name=='class' and value=='far fa-dot-circle red-text text-small':
						self.state_parser=2
		
		if self.state_parser==2:
			if tag=='a':
				for name, value in attrs:
					if name=='href':
						self.current_phase=value[-1]
						#print('Phase '+self.current_phase)
						self.state_parser=3
						
		if tag=='div':
			for name, value in attrs:
				if name=='class' and value=='card platoon':
					self.state_parser=4
				if name=='id' and self.state_parser==4:
					self.platoon_name=value[-2:]
					self.state_parser=5
						
		if tag=='div':
			for name, value in attrs:
				if name=='class' and value=='char filled':
					self.state_parser=6
				if name=='class' and value=='char':
					self.state_parser=7

		if self.state_parser==6:
			if tag=='img':
				for name, value in attrs:
					if name=='title':
						self.char_name=value
						self.state_parser=8

		if self.state_parser==7:
			if tag=='img':
				for name, value in attrs:
					if name=='title':
						self.char_name=value
						if self.char_name in dict_noms_warstats:
							self.char_name=dict_noms_warstats[self.char_name]
						#print(self.platoon_name+': '+self.char_name+' > ???')
						if not self.platoon_name in self.dict_platoons:
							self.dict_platoons[self.platoon_name]={}
						if not self.char_name in self.dict_platoons[self.platoon_name]:
							self.dict_platoons[self.platoon_name][self.char_name]=[]
						self.dict_platoons[self.platoon_name][self.char_name].append('')
						self.state_parser=4

		if self.state_parser==8:
			if tag=='div':
				for name, value in attrs:
					if name=='class' and value=='player':
						self.state_parser=9
						
	def handle_data(self, data):
		if self.state_parser==9:
			self.player_name=data
			if self.char_name in dict_noms_warstats:
				self.char_name=dict_noms_warstats[self.char_name]
			#print(self.platoon_name+': '+self.char_name+' > '+self.player_name)
			if not self.platoon_name in self.dict_platoons:
				self.dict_platoons[self.platoon_name]={}
			if not self.char_name in self.dict_platoons[self.platoon_name]:
				self.dict_platoons[self.platoon_name][self.char_name]=[]
			self.dict_platoons[self.platoon_name][self.char_name].append(self.player_name)
			self.state_parser=5

	def get_dict_platoons(self):
		return self.dict_platoons

	def get_phase(self):
		return self.current_phase
			
class GenericTBSParser(HTMLParser):
	warstats_battle_id=''
	state_parser=0
	#0: en recherche de h2
	#1: en recherche de data=Territory Battles
	#2: en recherche de div class=card
	#3: en recherche de a href
		
	def handle_starttag(self, tag, attrs):
		if self.state_parser==0:
			if tag=='h2':
				#print('DBG: h2')
				self.state_parser=1

		if self.state_parser==2:
			if tag=='div':
				#print('DBG: div - '+str(attrs))
				for name, value in attrs:
					if name=='class' and value=='card':
						self.state_parser=3

		if self.state_parser==3:
			if tag=='a':
				#print('DBG: a - '+str(attrs))
				for name, value in attrs:
					if name=='href':
						#print(value.split('/'))
						self.warstats_battle_id=value.split('/')[3]
						self.state_parser=0

	def handle_data(self, data):
		if self.state_parser==1:
			if data=='Territory Battles':
				self.state_parser=2
			else:
				self.state_parser=0
				
	def get_url(self):
		return warstats_platoons_baseurl+self.warstats_battle_id
		

def parse_warstats_page():
	page = urllib.request.urlopen(warstats_tbs_url)
	parser = GenericTBSParser()
	parser.feed(str(page.read()))
	warstats_platoon_url=parser.get_url()
			
	page = urllib.request.urlopen(warstats_platoon_url)
	parser = TBSPhaseParser()
	parser.feed(str(page.read()))

	return parser.get_phase(), parser.get_dict_platoons()
