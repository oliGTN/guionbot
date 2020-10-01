import urllib.request
from html.parser import HTMLParser

warstats_tbs_url='https://goh.warstats.net/guilds/tbs/4090'
warstats_platoons_baseurl='https://goh.warstats.net/platoons/view/'

tab_dict_platoons=[] #de haut en bas

dict_noms_warstats={}
dict_noms_warstats['Admiral Ackbar']='Amiral Ackbar'
dict_noms_warstats['Admiral Piett']='Amiral Piett'
dict_noms_warstats['Ahsoka Tano\\\'s Jedi Starfighter']='Chasseur stellaire Jedi d\'Ahsoka Tano'
dict_noms_warstats['Anakin\\\'s Eta-2 Starfighter']='Chasseur Eta-2 d\'Anakin'
dict_noms_warstats['ARC Trooper']='Soldat CRA'
dict_noms_warstats['B-28 Extinction-class Bomber']='Bombardier de classe extinction B-28'
dict_noms_warstats['B1 Battle Droid']='Droïde de combat B1'
dict_noms_warstats['B2 Super Battle Droid']='Super droïde de combat B2'
dict_noms_warstats['Bastila Shan (Fallen)']='Bastila Shan (déchue)'
dict_noms_warstats['Biggs Darklighter\\\'s X-wing']='X-Wing de Biggs Darklighter'
dict_noms_warstats['Bistan\\\'s U-wing']='U-Wing de Bistan'
dict_noms_warstats['BTL-B Y-wing Starfighter']='Chasseur Y-wing BTL-B'
dict_noms_warstats['Captain Han Solo']='Capitaine Han Solo'
dict_noms_warstats['Captain Phasma']='Capitaine Phasma'
dict_noms_warstats['Cassian\\\'s U-wing']='U-wing de Cassian'
dict_noms_warstats['CC-2224']='CC-2224 "Cody"'
dict_noms_warstats['Chief Chirpa']='Chef Chirpa'
dict_noms_warstats['Chief Nebit']='Chef Nebit'
dict_noms_warstats['Chimaera']='Chimère'
dict_noms_warstats['Clone Sergeant - Phase I']='Sergent clone - Phase I'
dict_noms_warstats['Clone Sergeant\\\'s ARC-170']='ARC-170 du Sergent clone'
dict_noms_warstats['Clone Wars Chewbacca']='Chewbacca Guerre des Clones'
dict_noms_warstats['Commander Luke Skywalker']='Commandant Luke Skywalker'
dict_noms_warstats['Coruscant Underworld Police']='Police de la pègre de Coruscant'
dict_noms_warstats['Count Dooku']='Comte Dooku'
dict_noms_warstats['CT-21-0408']='CT-21-0408 "Écho"'
dict_noms_warstats['CT-5555']='CT-5555 "Cinqs"'
dict_noms_warstats['CT-7567']='CT-7567 "Rex"'
dict_noms_warstats['Darth Malak']='Dark Malak'
dict_noms_warstats['Darth Maul']='Dark Maul'
dict_noms_warstats['Darth Nihilus']='Dark Nihilus'
dict_noms_warstats['Darth Revan']='Dark Revan'
dict_noms_warstats['Darth Sidious']='Dark Sidious'
dict_noms_warstats['Darth Sion']='Dark Sion'
dict_noms_warstats['Darth Traya']='Dark Traya'
dict_noms_warstats['Darth Vader']='Dark Vador'
dict_noms_warstats['Director Krennic']='Directeur Krennic'
dict_noms_warstats['Droideka']='Droïdeka'
dict_noms_warstats['Emperor Palpatine']='Empereur Palpatine'
dict_noms_warstats['Emperor\\\'s Shuttle']='Navette de l’Empereur'
dict_noms_warstats['Ewok Elder']='Ancien ewok'
dict_noms_warstats['Ewok Scout']='Éclaireur ewok'
dict_noms_warstats['First Order Executioner']='Exécuteur du Premier Ordre'
dict_noms_warstats['First Order Officer']='Officier du Premier Ordre'
dict_noms_warstats['First Order SF TIE Fighter']='Chasseur TIE/S du Premier Ordre'
dict_noms_warstats['First Order SF TIE Pilot']='Pilote de TIE/S du Premier Ordre'
dict_noms_warstats['First Order Stormtrooper']='Stormtrooper du Premier Ordre'
dict_noms_warstats['First Order TIE Fighter']='Chasseur TIE du Premier Ordre'
dict_noms_warstats['First Order TIE Pilot']='Pilote de chasseur TIE du Premier Ordre'
dict_noms_warstats['Gamorrean Guard']='Garde Gamorréen'
dict_noms_warstats['Garazeb']='Garazeb "Zeb" Orrelios'
dict_noms_warstats['Gauntlet Starfighter']='Chasseur Gauntlet'
dict_noms_warstats['General Grievous']='Général Grievous'
dict_noms_warstats['General Hux']='Général Hux'
dict_noms_warstats['General Kenobi']='Général Kenobi'
dict_noms_warstats['General Veers']='Général Veers'
dict_noms_warstats['Geonosian Brood Alpha']='Alpha Géonosien'
dict_noms_warstats['Geonosian Soldier']='Soldat géonosien'
dict_noms_warstats['Geonosian Soldier\\\'s Starfighter']='Chasseur stellaire du soldat géonosien'
dict_noms_warstats['Geonosian Spy']='Espion géonosien'
dict_noms_warstats['Geonosian Spy\\\'s Starfighter']='Chasseur stellaire de l\'espion géonosien'
dict_noms_warstats['Grand Admiral Thrawn']='Grand Amiral Thrawn'
dict_noms_warstats['Grand Master Yoda']='Grand Maître Yoda'
dict_noms_warstats['Han\\\'s Millennium Falcon']='Faucon Millenium de Han'
dict_noms_warstats['Hermit Yoda']='Yoda Ermite'
dict_noms_warstats['Hoth Rebel Scout']='Éclaireur rebelle de Hoth'
dict_noms_warstats['Hoth Rebel Soldier']='Soldat rebelle de Hoth'
dict_noms_warstats['Hound\\\'s Tooth']='Dent du Molosse'
dict_noms_warstats['IG-100 MagnaGuard']='MagnaGarde IG-100'
dict_noms_warstats['IG-86 Sentinel Droid']='Droïde sentinelle IG-86'
dict_noms_warstats['Imperial Probe Droid']='Droïde Sonde Impérial'
dict_noms_warstats['Imperial Super Commando']='Super commando impérial'
dict_noms_warstats['Imperial TIE Fighter']='Chasseur TIE impérial'
dict_noms_warstats['Jawa Engineer']='Ingénieur Jawa'
dict_noms_warstats['Jawa Scavenger']='Pillard Jawa'
dict_noms_warstats['Jedi Consular']='Jedi consulaire'
dict_noms_warstats['Jedi Consular\\\'s Starfighter']='Chasseur stellaire du Jedi Consulaire'
dict_noms_warstats['Jedi Knight Anakin']='Chevalier Jedi Anakin'
dict_noms_warstats['Jedi Knight Guardian']='Chevalier Jedi Gardien'
dict_noms_warstats['Jedi Knight Revan']='Chevalier Jedi Revan'
dict_noms_warstats['Kylo Ren (Unmasked)']='Kylo Ren (sans masque)'
dict_noms_warstats['Kylo Ren\\\'s Command Shuttle']='Navette de commandement de Kylo Ren'
dict_noms_warstats['Lando\\\'s Millennium Falcon']='Faucon Millenium de Lando'
dict_noms_warstats['Luke Skywalker (Farmboy)']='Luke Skywalker (fermier)'
dict_noms_warstats['Mob Enforcer']='Homme de main de la pègre'
dict_noms_warstats['Mother Talzin']='Mère Talzin'
dict_noms_warstats['Nightsister Acolyte']='Acolyte des Soeurs de la Nuit'
dict_noms_warstats['Nightsister Initiate']='Initiée des Soeurs de la Nuit'
dict_noms_warstats['Nightsister Spirit']='Esprit Sœur de la Nuit'
dict_noms_warstats['Nightsister Zombie']='Zombie Sœur de la Nuit'
dict_noms_warstats['Obi-Wan Kenobi (Old Ben)']='Obi-Wan Kenobi (Vieux Ben)'
dict_noms_warstats['Old Daka']='Vieille Daka'
dict_noms_warstats['Plo Koon\\\'s Jedi Starfighter']='Chasseur stellaire Jedi de Plo Koon'
dict_noms_warstats['Poe Dameron\\\'s X-wing']='X-Wing de Poe Dameron'
dict_noms_warstats['Poggle the Lesser']='Poggle le bref'
dict_noms_warstats['Princess Leia']='Princesse Leia'
dict_noms_warstats['Rebel Officer Leia Organa']='Officier rebelle Leia Organa'
dict_noms_warstats['Resistance Hero Finn']='Héros de la Résistance Finn'
dict_noms_warstats['Resistance Hero Poe']='Héros de la Résistance Poe'
dict_noms_warstats['Resistance Pilot']='Pilote de la Résistance'
dict_noms_warstats['Resistance Trooper']='Soldat de la Résistance'
dict_noms_warstats['Resistance X-wing']='X-wing de la Résistance'
dict_noms_warstats['Rex\\\'s ARC-170']='ARC-170 de Rex'
dict_noms_warstats['Rey (Jedi Training)']='Rey (entraînement de Jedi)'
dict_noms_warstats['Rey (Scavenger)']='Rey (Pilleuse)'
dict_noms_warstats['Rey\\\'s Millennium Falcon']='Faucon Millenium de Rey'
dict_noms_warstats['Royal Guard']='Garde royal'
dict_noms_warstats['Scarif Rebel Pathfinder']='Pisteur rebelle de Scarif'
dict_noms_warstats['Scimitar']='Cimeterre'
dict_noms_warstats['Sith Assassin']='Assassin Sith'
dict_noms_warstats['Sith Empire Trooper']='Soldat Sith de l\'Empire'
dict_noms_warstats['Sith Fighter']='Chasseur Sith'
dict_noms_warstats['Sith Marauder']='Maraudeur Sith'
dict_noms_warstats['Sith Trooper']='Soldat Sith'
dict_noms_warstats['Slave I']='Esclave I'
dict_noms_warstats['Stormtrooper Han']='Han en stormtrooper'
dict_noms_warstats['Sun Fac\\\'s Geonosian Starfighter']='Chasseur stellaire géonosien de Sun Fac'
dict_noms_warstats['The Mandalorian']='Le Mandalorien'
dict_noms_warstats['Threepio & Chewie']='3PO et Chewie'
dict_noms_warstats['TIE Advanced x1']='TIE avancé x1'
dict_noms_warstats['TIE Fighter Pilot']='Pilote de chasseur TIE'
dict_noms_warstats['TIE Reaper']='Faucheur TIE'
dict_noms_warstats['TIE Silencer']='TIE silencer'
dict_noms_warstats['Tusken Raider']='Pillard Tusken'
dict_noms_warstats['Tusken Shaman']='Chaman Tusken'
dict_noms_warstats['Umbaran Starfighter']='Chasseur umbarien'
dict_noms_warstats['Vandor Chewbacca']='Chewbacca Vandor'
dict_noms_warstats['Veteran Smuggler Chewbacca']='Contrebandier vétéran Chewbacca'
dict_noms_warstats['Veteran Smuggler Han Solo']='Contrebandier vétéran Han Solo'
dict_noms_warstats['Vulture Droid']='Chasseur droïde de classe Vautour'
dict_noms_warstats['Wedge Antilles\\\'s X-wing']='X-Wing de Wedge Antilles'
dict_noms_warstats['Young Han Solo']='Han Solo jeune'
dict_noms_warstats['Young Lando Calrissian']='Lando Calrissian jeune'

dict_platoon_names={} #key=bataille + phase (ex "GDS1), value= {key=warstats letter, value=echobot position}
dict_platoon_names['GDS1']={}
dict_platoon_names['GDS1']['A']='top'
dict_platoon_names['GDS1']['B']='bottom'
dict_platoon_names['GDS2']={}
dict_platoon_names['GDS2']['A']='top'
dict_platoon_names['GDS2']['B']='mid'
dict_platoon_names['GDS2']['C']='bottom'
dict_platoon_names['GDS3']={}
dict_platoon_names['GDS3']['A']='top'
dict_platoon_names['GDS3']['B']='mid'
dict_platoon_names['GDS3']['C']='bottom'
dict_platoon_names['GDS4']={}
dict_platoon_names['GDS4']['A']='top'
dict_platoon_names['GDS4']['B']='mid'
dict_platoon_names['GDS4']['C']='bottom'


class TBSPhaseParser(HTMLParser):
	dict_platoons={} #key="A1" to "C6", value={} key=perso, value=[player, ...]
	dict_player_allocations={} #key=player, value={ key=perso, value=platoon}
	platoon_name=''
	char_name=''
	player_name=''
	detected_phase=''
	active_phase=''
	state_parser=-4
	#-4: en recherche de h2
	#-3: en recharche de data="Territory Battle"
	#-2: en recherche de small
	#-1: en recherche de data
	#0: en recherche de div class=phases
	#2: en recherche de a href
	#3: en recherche de div class="card platoon"
	#4: en recherche de div id
	#5: en recherche de div class="char" ou "char filled"
	#6: en recherche de img-title d'un perso rempli
	#7: en recherche de img-title d'un perso NON rempli
	#8: en recherche de div class=player
	#9: en recherche de data
	
	state_parser2=0
	#0: en recherche de i class="far fa-dot-circle red-text text-small"
	#1: en recherche de a href
		
	def handle_starttag(self, tag, attrs):
		#PARSER 1 pour la phase décrite dans la page
		if self.state_parser==-4:
			if tag=='h2':
				self.state_parser=-3
						
		if self.state_parser==-2:
			if tag=='small':
				self.state_parser=-1
						
		if self.state_parser==0:
			if tag=='div':
				for name, value in attrs:
					if name=='class' and value=='phases':
						self.state_parser=2
				
		if self.state_parser==2:
			if tag=='a':
				for name, value in attrs:
					if name=='href':
						self.detected_phase=self.detected_phase[0:3]+value[-1]
					if name=='class' and value=='active':
						self.state_parser=3

			if tag=='i':
				for name, value in attrs:
					if name=='class' and value=='far fa-dot-circle red-text text-small':
						self.is_current_phase=True
						
		if self.state_parser==3 or self.state_parser==5:
			if tag=='div':
				for name, value in attrs:
					if name=='class' and value=='card platoon':
						self.state_parser=4
					if name=='id' and self.state_parser==4:
						self.platoon_name=self.detected_phase+'-'+dict_platoon_names[self.detected_phase][value[-2:-1]]+'-'+value[-1]
						self.state_parser=5
						
		if self.state_parser==5:
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
						self.state_parser=5

		if self.state_parser==8:
			if tag=='div':
				for name, value in attrs:
					if name=='class' and value=='player':
						self.state_parser=9

		#PARSER 2 pour la phase active
		if self.state_parser2==0:
			if tag=='i':
				for name, value in attrs:
					if name=='class' and value=='far fa-dot-circle red-text text-small':
						self.state_parser2=1
		if self.state_parser2==1:
			if tag=='a':
				for name, value in attrs:
					if name=='href':
						self.active_phase=self.detected_phase[0:3]+value[-1]
						self.state_parser2=0				
						
	def handle_data(self, data):
		if self.state_parser==-3:
			#print(data)
			if data == 'Territory Battle ':
				self.state_parser=-2
			else:
				self.state_parser=-4
				
		if self.state_parser==-1:
			#print(data)
			if data == 'Geonosian - Dark side':
				self.detected_phase='GDS'
			elif data == 'Geonosian - Light side':
				self.detected_phase='GLS'
			elif data == 'Hoth - Dark side':
				self.detected_phase='HDS'
			elif data == 'Hoth - Light side':
				self.detected_phase='HLS'
			else:
				print('ERR: BT inconnue: '+data)
			
			self.state_parser=0
				
		if self.state_parser==9:
			self.player_name=data
			if self.char_name in dict_noms_warstats:
				self.char_name=dict_noms_warstats[self.char_name]
			#print(self.platoon_name+': '+self.char_name+' > '+self.player_name)
			
			#remplissage dict_platoons
			if not self.platoon_name in self.dict_platoons:
				self.dict_platoons[self.platoon_name]={}
			if not self.char_name in self.dict_platoons[self.platoon_name]:
				self.dict_platoons[self.platoon_name][self.char_name]=[]
			self.dict_platoons[self.platoon_name][self.char_name].append(self.player_name)
			
			#remplissage dict_player_allocations
			if not self.player_name in self.dict_player_allocations:
				self.dict_player_allocations[self.player_name]={}
			if not self.char_name in self.dict_player_allocations[self.player_name]:
				self.dict_player_allocations[self.player_name][self.char_name]=[]
			self.dict_player_allocations[self.player_name][self.char_name]=self.platoon_name
			
			self.state_parser=5

	def get_dict_platoons(self):
		return self.dict_platoons

	def get_dict_player_allocations(self):
		return self.dict_player_allocations

	def get_phase(self):
		return self.detected_phase

	def get_active_phase(self):
		return self.active_phase
			
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
	try:
		page = urllib.request.urlopen(warstats_tbs_url)
	except urllib.error.HTTPError as e:
		return '', None
		
	parser = GenericTBSParser()
	parser.feed(str(page.read()))
	warstats_platoon_url=parser.get_url()
			
	print(warstats_platoon_url)
	try:
		page = urllib.request.urlopen(warstats_platoon_url)
	except urllib.error.HTTPError as e:
		return '', None
	
	complete_dict_platoons={}
	complete_dict_player_allocations={}
	for phase in range(1,6):
		try:
			print('Lecture WARSTATS '+warstats_platoon_url+'/'+str(phase))
			page = urllib.request.urlopen(warstats_platoon_url+'/'+str(phase))
			parser = TBSPhaseParser()
			parser.feed(str(page.read()))
			complete_dict_platoons.update(parser.get_dict_platoons())
			complete_dict_player_allocations.update(parser.get_dict_player_allocations())
		except urllib.error.HTTPError as e:
			print('WAR: page introuvable '+warstats_platoon_url+'/'+str(phase))

	return parser.get_active_phase(), complete_dict_platoons, complete_dict_player_allocations
