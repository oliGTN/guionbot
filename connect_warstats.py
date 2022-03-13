import urllib.request
import string
import random
import re
from html.parser import HTMLParser
import time
import datetime
import tzlocal
from dateutil import tz

import config
import goutils
import data

# URLs for TB
warstats_tbs_url='https://goh.warstats.net/guilds/tbs/'
warstats_platoons_baseurl='https://goh.warstats.net/platoons/view/'
warstats_tb_resume_baseurl='https://goh.warstats.net/territory-battles/view/'

# URLs for TW
warstats_tws_url='https://goh.warstats.net/guilds/tws/'
warstats_opp_squad_baseurl='https://goh.warstats.net/territory-wars/squads/opponent/'

# URLs for RAIDS
warstats_raids_url='https://goh.warstats.net/guilds/raids/'
warstats_raid_resume_baseurl='https://goh.warstats.net/raids/view/'

tab_dict_platoons=[] #de haut en bas

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

dict_platoon_names['GLS1']={}
dict_platoon_names['GLS1']['A']='top'
dict_platoon_names['GLS1']['B']='mid'
dict_platoon_names['GLS1']['C']='bottom'
dict_platoon_names['GLS2']={}
dict_platoon_names['GLS2']['A']='top'
dict_platoon_names['GLS2']['B']='mid'
dict_platoon_names['GLS2']['C']='bottom'
dict_platoon_names['GLS3']={}
dict_platoon_names['GLS3']['A']='top'
dict_platoon_names['GLS3']['B']='mid'
dict_platoon_names['GLS3']['C']='bottom'
dict_platoon_names['GLS4']={}
dict_platoon_names['GLS4']['A']='top'
dict_platoon_names['GLS4']['B']='mid'
dict_platoon_names['GLS4']['C']='bottom'

dict_platoon_names['HLS1']={}
dict_platoon_names['HLS1']['A']='top'
dict_platoon_names['HLS2']={}
dict_platoon_names['HLS2']['A']='top'
dict_platoon_names['HLS2']['B']='bottom'
dict_platoon_names['HLS3']={}
dict_platoon_names['HLS3']['A']='top'
dict_platoon_names['HLS3']['B']='mid'
dict_platoon_names['HLS3']['C']='bottom'
dict_platoon_names['HLS4']={}
dict_platoon_names['HLS4']['A']='top'
dict_platoon_names['HLS4']['B']='mid'
dict_platoon_names['HLS4']['C']='bottom'
dict_platoon_names['HLS5']={}
dict_platoon_names['HLS5']['A']='top'
dict_platoon_names['HLS5']['B']='mid'
dict_platoon_names['HLS5']['C']='bottom'
dict_platoon_names['HLS6']={}
dict_platoon_names['HLS6']['A']='top'
dict_platoon_names['HLS6']['B']='mid'
dict_platoon_names['HLS6']['C']='bottom'

dict_platoon_names['HDS1']={}
dict_platoon_names['HDS1']['A']='top'
dict_platoon_names['HDS1']['B']='bottom'
dict_platoon_names['HDS2']={}
dict_platoon_names['HDS2']['A']='top'
dict_platoon_names['HDS2']['B']='bottom'
dict_platoon_names['HDS3']={}
dict_platoon_names['HDS3']['A']='top'
dict_platoon_names['HDS3']['B']='mid'
dict_platoon_names['HDS3']['C']='bottom'
dict_platoon_names['HDS4']={}
dict_platoon_names['HDS4']['A']='top'
dict_platoon_names['HDS4']['B']='mid'
dict_platoon_names['HDS4']['C']='bottom'
dict_platoon_names['HDS5']={}
dict_platoon_names['HDS5']['A']='top'
dict_platoon_names['HDS5']['B']='mid'
dict_platoon_names['HDS5']['C']='bottom'
dict_platoon_names['HDS6']={}
dict_platoon_names['HDS6']['A']='top'
dict_platoon_names['HDS6']['B']='mid'
dict_platoon_names['HDS6']['C']='bottom'

dict_tw_territory_names={}
dict_tw_territory_names['Trenches']='T1'
dict_tw_territory_names['Forward turrets']='B1'
dict_tw_territory_names['Hangar']='T2'
dict_tw_territory_names['Infirmary']='B2'
dict_tw_territory_names['Airspace fortification']='F1'
dict_tw_territory_names['Supply depot']='T3'
dict_tw_territory_names['Ion cannon']='B3'
dict_tw_territory_names['Main base']='F2'
dict_tw_territory_names['Command post']='T4'
dict_tw_territory_names['Special ops center']='B4'

#timer and global variables due to warstats tracking
dict_next_warstats_read = {}
WARSTATS_REFRESH_SECS = 15 * 60 # Time between 2 refresh
WARSTATS_REFRESH_TIME = 5 * 60 #Duration of refresh

dict_parse_tb_guild_scores_run_once = {}
dict_tb_territory_scores = {}

dict_parse_tb_platoons_run_once = {}
dict_tb_active_round = {}
dict_tb_platoons = {}
dict_tb_open_territories = {}

dict_parse_tb_player_scores_run_once = {}
dict_tb_player_scores = {}

dict_opponent_teams = {}

dict_raid_player_scores = {} #{raid name:{player name:score}}
dict_raid_phase = {} #{raid name:phase}

#Dictionary to transform txt date into number
dict_months = {'Jan.':1,
               'Feb.':2,
               'Mar.':3,
               'Apr.':4,
               'May.':5,
               'Jun.':6,
               'Jul.':7,
               'Aug.':8,
               'Sep.':9,
               'Oct.':10,
               'Nov.':11,
               'Dec.':12}

def init_globals(guild_id):
    dict_tb_active_round[guild_id] = ""
    dict_tb_territory_scores[guild_id] = {}
    dict_tb_player_scores[guild_id] = {}
    dict_tb_platoons[guild_id] = {}
    dict_tb_open_territories[guild_id] = []

    dict_parse_tb_guild_scores_run_once[guild_id] = False
    dict_parse_tb_player_scores_run_once[guild_id] = False
    dict_parse_tb_platoons_run_once[guild_id] = False

    dict_opponent_teams[guild_id] = []

    dict_raid_player_scores[guild_id] = {}
    dict_raid_phase[guild_id] = {}

    dict_next_warstats_read[guild_id] = {}
    dict_next_warstats_read[guild_id]["tb_territory_scores"] = time.time()
    dict_next_warstats_read[guild_id]["tb_platoons"] = time.time()
    dict_next_warstats_read[guild_id]["tb_player_scores"] = time.time()
    dict_next_warstats_read[guild_id]["tw_teams"] = time.time()
    dict_next_warstats_read[guild_id]["raid_scores"] = time.time()
    
def set_next_warstats_read_short(seconds_since_last_track, counter_name, guild_id):
    global dict_next_warstats_read

    time_to_wait = WARSTATS_REFRESH_SECS - seconds_since_last_track + WARSTATS_REFRESH_TIME
    dict_next_warstats_read[guild_id][counter_name] = int(time.time()) + time_to_wait
    next_warstats_read_txt = datetime.datetime.fromtimestamp(dict_next_warstats_read[guild_id][counter_name]).strftime('%Y-%m-%d %H:%M:%S')
    goutils.log2("DBG", next_warstats_read_txt)
    
def set_next_warstats_read_long(time_hour, tz_name, counter_name, guild_id):
    global dict_next_warstats_read

    next_time_tz = tz.gettz(tz_name)
    next_time = datetime.datetime.now().replace(hour=time_hour,
                                                minute=0, 
                                                second=0, 
                                                microsecond=0,
                                                tzinfo=next_time_tz)

    bot_tz = tz.tzlocal()
    bot_now = datetime.datetime.now().replace(tzinfo=bot_tz)

    while next_time < bot_now:
        goutils.log2('DBG', "next_time="+str(next_time)+" < bot_now="+str(bot_now))
        next_time = next_time + datetime.timedelta(days=1)
    next_time_secs = datetime.datetime.timestamp(next_time)

    dict_next_warstats_read[guild_id][counter_name] = next_time_secs
    next_warstats_read_txt = datetime.datetime.fromtimestamp(dict_next_warstats_read[guild_id][counter_name]).strftime('%Y-%m-%d %H:%M:%S')
    goutils.log2("DBG", next_warstats_read_txt)
    
def get_next_warstats_read(counter_name, guild_id):
    time_to_wait = dict_next_warstats_read[guild_id][counter_name] - int(time.time())
    return time_to_wait
    
###################################################################################
# Parseing of a platoon page for a specific phase in TB
###################################################################################
class TBSPhasePlatoonParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.dict_platoons={} #key="A1" to "C6", value={} key=perso, value=[player, ...]
        self.platoon_name=''
        self.char_name=''
        self.player_name=''
        self.page_round='' # "GDS1" with the phase of the parsed page
        self.active_round='' # "GDS1" with the current phase of the TB
        self.state_parser=-4
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
        
        self.state_parser2=0
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
                    if name=='class' and value.startswith('phases'):
                        self.state_parser=2
                
        if self.state_parser==2:
            if tag=='a':
                for name, value in attrs:
                    if name=='href':
                        self.page_round=self.page_round[0:3]+value[-1]
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
                        self.platoon_name=self.page_round+'-'+dict_platoon_names[self.page_round][value[-2:-1]]+'-'+value[-1]
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
                        list_ids, dict_id_name, txt = goutils.get_characters_from_alias([self.char_name])
                        self.char_name = dict_id_name[self.char_name][0][1]
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
                        self.active_round=self.page_round[0:3]+value[-1]
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
                self.page_round='GDS'
            elif data == 'Geonosian - Light side':
                self.page_round='GLS'
            elif data == 'Hoth - Dark side':
                self.page_round='HDS'
            elif data == 'Hoth - Light side':
                self.page_round='HLS'
            else:
                goutils.log2('ERR', "BT inconnue: "+data)
            
            self.state_parser=0
                
        if self.state_parser==9:
            self.player_name=data
            list_ids, dict_id_name, txt = goutils.get_characters_from_alias([self.char_name])
            self.char_name = dict_id_name[self.char_name][0][1]
            
            #remplissage dict_platoons
            if not self.platoon_name in self.dict_platoons:
                self.dict_platoons[self.platoon_name]={}
            if not self.char_name in self.dict_platoons[self.platoon_name]:
                self.dict_platoons[self.platoon_name][self.char_name]=[]
            self.dict_platoons[self.platoon_name][self.char_name].append(self.player_name)
            
            self.state_parser=5

    def get_dict_platoons(self):
        return self.dict_platoons

    def get_page_round(self):
        return self.page_round

    def get_active_round(self):
        return self.active_round
            
class TBSListParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.tb_alias=''
        self.warstats_battle_id=''
        self.warstats_battle_in_progress=False
        self_seconds_since_last_track = 0

        self.state_parser=0
        #0: en recherche de h2
        #1: en recherche de data=Territory Battles
        #2: en recherche de div class='card card-table'
        #3: en recherche de tbody
        #4: en recherche de tr
        #5: en recherche de <i title="In progress" OR <a href
        #6: en recherche de img
        #    if tb_alias found >> 7
        #    else >> 4
        #7: end

        self.state_parser2=0
        #0: en recherche de <span id="track-timer"
        #1: en recherche de script
        #2: en recherche de data
        
    def handle_starttag(self, tag, attrs):
        if self.state_parser==0:
            if tag=='h2':
                #print('DBG: h2')
                self.state_parser=1

        if self.state_parser==2:
            if tag=='div':
                #print('DBG: div - '+str(attrs))
                for name, value in attrs:
                    if name=='class' and value=='card card-table':
                        self.state_parser=3

        if self.state_parser==3:
            if tag=='tbody':
                self.state_parser=4

        if self.state_parser==4:
            if tag=='tr':
                self.state_parser=5

        if self.state_parser==5:
            if tag=="i":
                #print('DBG: i - '+str(attrs))
                for name, value in attrs:
                    if name=='title' and value=='In progress':
                        self.warstats_battle_in_progress=True
            elif tag=='a':
                #print('DBG: a - '+str(attrs))
                for name, value in attrs:
                    if name=='href':
                        #print(value.split('/'))
                        if value!='':
                            self.warstats_battle_id=value.split('/')[3]
                        self.state_parser=6

        if self.state_parser==6:
            if tag=='img':
                for name, value in attrs:
                    if name=='alt':
                        if self.tb_alias == "":
                            #If no specific battle required, the latest is OK
                            self.state_parser=7
                        elif value == "geo_light" and self.tb_alias == "GLS":
                            self.state_parser=7
                        elif value == "geo_dark" and self.tb_alias == "GDS":
                            self.state_parser=7
                        elif value == "light" and self.tb_alias == "HLS":
                            self.state_parser=7
                        elif value == "dark" and self.tb_alias == "HDS":
                            self.state_parser=7
                        else:
                            self.state_parser=4

        #PARSER 2 pour le timer du tracker
        if self.state_parser2==0:
            if tag=='span':
                for name, value in attrs:
                    if name=='id' and value=='track-timer':
                        self.state_parser2=1
                        
        if self.state_parser2==1:
            if tag=='script':
                self.state_parser2=2

    def handle_data(self, data):
        if self.state_parser==1:
            if data=='Territory Battles':
                self.state_parser=2
            else:
                self.state_parser=0

        if self.state_parser2==2:
            ret_re = re.search('{seconds: (.*?)}', data)
            timer_seconds_txt = ret_re.group(1)
            self.seconds_since_last_track = int(timer_seconds_txt)
            self.state_parser2=0
                
    def get_battle_id(self, force_latest):
        #If the oarser has not reached the end status, the required battle was not found
        if self.state_parser!=7:
            return None

        if self.warstats_battle_in_progress or force_latest:
            return self.warstats_battle_id
        else:
            return None

    def get_last_track(self):
        return self.seconds_since_last_track
                
    def set_tb_alias(self, tb_alias):
        self.tb_alias = tb_alias
                
###################################################################################
# Parseing of a normale (resume) page for a specific phase in TB
###################################################################################
class TBSPhaseResumeParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.list_data=[]
        self.list_open_territories=[0, 0, 0] #[top open territory, mid open territory, bottom open territory]
        self.territory_scores=[0, 0, 0] #[top open territory, mid open territory, bottom open territory]
        self.active_round='' #GDS1 with the phase of the TB
        self.page_round='' #GDS1 with the phase of the page
        self.seconds_since_last_track = 0
        self.player_name=''
        self.span_count=0
        self.dict_player_scores={} #key=name, value=[[1], [4, 3], ...]
        
        self.state_parser=-4
        #-4: en recherche de h2
        #-3: en recharche de data="Territory Battle"
        #-2: en recherche de small
        #-1: en recherche de data
        #0: en recherche de div class=phases
        #1: en recherche de a href
        #2: en recherche de div id="resume"
        #3: en recherche de div class="valign-wrapper full-line"
        #4: en recherche de data
        #5: en recherche de div class="score-text"
        #6: en recherche de data

        self.state_parser2=0
        #0: en recherche de i class="far fa-dot-circle red-text text-small"
        #1: en recherche de a href
        
        self.state_parser3=0
        #0: en recherche de <span id="track-timer"
        #1: en recherche de script
        #2: en recherche de data
        
        self.state_parser4=0
        #0: en recherche de h3
        #1: en recherche de tbody
        #2: en recherche de tr
        #3: en recherche de td
        #4: en recherche de td
        #5: en recherche de a
        #6: en recherche de data
        #7: en recherche de td
        #8: en recherche de span >9 OU data!="" >11
        #9: en recherche de data > state 10
        #10:waiting for /span
        #11:end

    def handle_starttag(self, tag, attrs):
        if self.state_parser==-4:
            if tag=='h2':
                self.state_parser=-3
                        
        if self.state_parser==-2:
            if tag=='small':
                self.state_parser=-1
                        
        if self.state_parser==0:
            if tag=='div':
                for name, value in attrs:
                    if name=='class' and value.startswith('phases'):
                        self.state_parser=1

        if self.state_parser==1:
            if tag=='a':
                for name, value in attrs:
                    if name=='href':
                        detected_round = value[-1]
                    if name=='class' and value=='active':
                        self.page_round=self.page_round[0:3]+detected_round
                        self.state_parser=2

        if self.state_parser==2:
            if tag=='div':
                for name, value in attrs:
                    if name=='id' and value=='resume':
                        self.state_parser=3

        elif self.state_parser==3:
            if tag=='div':
                for name, value in attrs:
                    if name=='class' and value=='valign-wrapper full-line':
                        self.list_data=[]
                        self.state_parser=4
                        
        elif self.state_parser==5:
            if tag=='div':
                for name, value in attrs:
                    if name=='class' and value=='score-text':
                        self.state_parser=6

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
                        self.active_round=self.page_round[0:3]+value[-1]
                        self.state_parser2=0
                        #print("DBG self.active_round: "+str(self.active_round))

        #PARSER 3 pour le timer du tracker
        if self.state_parser3==0:
            if tag=='span':
                for name, value in attrs:
                    if name=='id' and value=='track-timer':
                        self.state_parser3=1
                        
        if self.state_parser3==1:
            if tag=='script':
                self.state_parser3=2
                        
        #PARSER 4 for player scores
        if self.state_parser4==0:
            if tag=='h3':
                self.state_parser4=1

        elif self.state_parser4==1:
            if tag=='tbody':
                self.state_parser4=2

        elif self.state_parser4==2:
            if tag=='tr':
                self.td_count=0
                self.state_parser4=3

        elif self.state_parser4==3:
            if tag=='td':
                self.state_parser4=4

        elif self.state_parser4==4:
            if tag=='td':
                self.state_parser4=5

        elif self.state_parser4==5:
            if tag=='a':
                self.state_parser4=6

        elif self.state_parser4==7:
            if tag=='td':
                self.td_count+=1
                self.span_count=0
                self.state_parser4=8

        elif self.state_parser4==8:
            if tag=='span':
                self.span_count+=1
                self.state_parser4=9

    def handle_endtag(self, tag):
        if self.state_parser==4:
            if tag=='div':
                if len(self.list_data)==1:
                    #the phase of the territory is the same as the round/day
                    territory_phase=int(self.page_round[-1])
                else:
                    #the phase of the territory is late compared to the round/day
                    territory_phase=int(self.list_data[1][-1])

                if self.list_data[0]=='North':
                    self.list_open_territories[0]=territory_phase
                elif self.list_data[0]=='Middle':
                    self.list_open_territories[1]=territory_phase
                else: #South
                    self.list_open_territories[2]=territory_phase
                self.state_parser=5
                        
        if self.state_parser4 > 2:
            if tag=='tr':
                self.state_parser4 = 2

        if self.state_parser4 in [7, 8]:
            if tag=='td':
                self.state_parser4 = 7

        if self.state_parser4 == 10:
            if tag=='span':
                self.state_parser4 = 8

    def handle_data(self, data):
        data = data.strip(" \t\n")
        if self.state_parser==-3:
            #print(data)
            if data == 'Territory Battle':
                self.state_parser=-2
            else:
                self.state_parser=-4
                
        if self.state_parser==-1:
            if data == 'Geonosian - Dark side':
                self.page_round='GDS'
            elif data == 'Geonosian - Light side':
                self.page_round='GLS'
            elif data == 'Hoth - Dark side':
                self.page_round='HDS'
            elif data == 'Hoth - Light side':
                self.page_round='HLS'
            else:
                goutils.log2('ERR', "BT inconnue: "+data)
            
            self.state_parser=0
                
        if self.state_parser==4:
            if data != '':
                self.list_data.append(data)
        elif self.state_parser==6:
            number = int(data.replace('/', '').replace(',', '').strip(" "))
            if self.list_data[0]=='North':
                self.territory_scores[0]=number
            elif self.list_data[0]=='Middle':
                self.territory_scores[1]=number
            else: #South
                self.territory_scores[2]=number
            self.state_parser=3

        if self.state_parser3==2:
            ret_re = re.search('{seconds: (.*?)}', data)
            timer_seconds_txt = ret_re.group(1)
            self.seconds_since_last_track = int(timer_seconds_txt)
            self.state_parser3=0

        if self.state_parser4==6:
            self.player_name = data
            self.dict_player_scores[self.player_name] = []
            self.state_parser4=7
                
        if self.state_parser4==8:
            if data != "" and self.td_count > 5:
                self.dict_player_scores[self.player_name].append(data)
                self.state_parser4=11
                
        if self.state_parser4==9:
            if self.span_count == 1:
                #after the first <span, create the list for the territory and initiate with phase ID
                territory_phase = self.list_open_territories[self.td_count-5]
                self.dict_player_scores[self.player_name].append([territory_phase])

            #then fill the scores, each <span is a new fight in the territory
            self.dict_player_scores[self.player_name][-1].append(data)
            self.state_parser4=10

    def get_active_round(self):
        return self.active_round

    def get_open_territories(self):
        return self.list_open_territories

    def get_territory_scores(self):
        dict_tb_territory_scores = {}

        #print("DBG - self.list_open_territories: "+str(self.list_open_territories))
        if self.list_open_territories[0] > 0:
            top_name = self.page_round[0:3]+"-P"+str(self.list_open_territories[0])+"-top"
            dict_tb_territory_scores[top_name] = self.territory_scores[0]
        if self.list_open_territories[1] > 0:
            mid_name = self.page_round[0:3]+"-P"+str(self.list_open_territories[1])+"-mid"
            dict_tb_territory_scores[mid_name] = self.territory_scores[1]
        if self.list_open_territories[2] > 0:
            bot_name = self.page_round[0:3]+"-P"+str(self.list_open_territories[2])+"-bot"
            dict_tb_territory_scores[bot_name] = self.territory_scores[2]
            
        return dict_tb_territory_scores

    def get_last_track(self):
        return self.seconds_since_last_track

    def get_player_scores(self):
        dict_player_scores_with_phase = {}
        for player in self.dict_player_scores:
            dict_player_scores_with_phase[player]={self.page_round:self.dict_player_scores[player]}

        return dict_player_scores_with_phase

class TWSListParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.warstats_war_id=''
        self.start_time = None
        self.warstats_war_in_progress=False
        self.state_parser=0
        #0: en recherche de h2
        #1: en recherche de data=Territory Wars
        #2: en recherche de div class='card card-table'
        #3: en recherche de a href
        #4: en recherche de data (date)
        #5: fin
        
    def handle_starttag(self, tag, attrs):
        if self.state_parser==0:
            if tag=='h2':
                #print('DBG: h2')
                self.state_parser=1

        if self.state_parser==2:
            if tag=='div':
                #print('DBG: div - '+str(attrs))
                for name, value in attrs:
                    if name=='class' and value=='card card-table':
                        self.state_parser=3

        if self.state_parser==3:
            if tag=='a':
                #print('DBG: a - '+str(attrs))
                for name, value in attrs:
                    if name=='href':
                        #print(value.split('/'))
                        self.warstats_war_id=value.split('/')[3]
                        self.state_parser=4

    def handle_data(self, data):
        if self.state_parser==1:
            if data=='Territory Wars':
                #print("state_parser=2")
                self.state_parser=2
            else:
                #print("state_parser=0")
                self.state_parser=0

        if self.state_parser==4:
            split_data = data.split(' ')
            day = int(split_data[0])
            month = dict_months[split_data[1]]
            year = int(split_data[2])

            start_time_tz = tz.gettz('UTC')
            self.start_time = datetime.datetime(year=year, month=month, day=day, hour=19)\
                              .replace(tzinfo=start_time_tz)

            bot_tz = tz.tzlocal()
            bot_now = datetime.datetime.now().replace(tzinfo=bot_tz)
            delta_days = (bot_now - self.start_time)
            goutils.log2("DBG", "days since start of TW: "+str(delta_days.days))
            if delta_days.days >= 2 and delta_days.days < 3:
                self.warstats_war_in_progress=True

            self.state_parser=5
                
    def get_war_id(self):
        return [self.warstats_war_id, self.warstats_war_in_progress]
 
    def get_last_track(self):
        return self.seconds_since_last_track
                
class TWSOpponentSquadParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.seconds_since_last_track = 0
        self.territory_name = ""
        self.opp_name = ""
        self.list_opp_teams = [] # [['T1', 'Karcot', ['Genaral Skywoalker', 'CT-555 Fives, ...]],
                                 #  ['T1', 'E80', [...]]]
        self.state_parser=-3
        #-3: en recherche de <h2>
        #-2: en recherche de <h2>
        #-1: en recherche de data
        #0: en recherche de <div class="frame tw-logs">
        #1: en recherche de <td>
        #2: en recherche de data
        #3: en recherche de <td>
        #4: en recherche de <div	class="char-detail..."> OU de <td> OU de <h2>
        #5: en recherche de <td> >> goto state 1
        
        self.state_parser2=0
        #0: en recherche de <span id="track-timer"
        #1: en recherche de script
        #2: en recherche de data
        
    def handle_starttag(self, tag, attrs):
        if self.state_parser==-3:
            if tag=='h2':
                #print(attrs)
                #print("state_parser=-2")
                self.state_parser=-2

        elif self.state_parser==-2:
            if tag=='h2':
                #print(attrs)
                #print("state_parser=-1")
                self.state_parser=-1

        elif self.state_parser==0:
            if tag=='div':
                #print('DBG: div - '+str(attrs))
                for name, value in attrs:
                    if name=='class' and value=='frame tw-logs':
                        #print("state_parser=1")
                        self.state_parser=1

        elif self.state_parser==1:
            if tag=='td':
                #print(attrs)
                #print("state_parser=2")
                self.state_parser=2

        elif self.state_parser==3:
            if tag=='td':
                #print(attrs)
                #print("state_parser=4")
                self.state_parser=4

        elif self.state_parser==4:
            if tag=='h2':
                #print(attrs)
                #print("state_parser=-1")
                self.state_parser=-1

            char_detected=False
            if tag=='div':
                #print('DBG: div - '+str(attrs))
                for name, value in attrs:
                    if name=='class' and (value.startswith('char-detail') \
                                          or value.startswith('ship-detail')):
                        char_detected=True
                    if name=='title' and char_detected:
                        #print(value)
                        self.list_opp_teams[-1][2].append(value)

            elif tag=='td':
                #print(attrs)
                #print("state_parser=5")
                self.state_parser=5

        elif self.state_parser==5:
            if tag=='h2':
                #print(attrs)
                #print("state_parser=-1")
                self.state_parser=-1

            elif tag=='td':
                #print(attrs)
                #print("state_parser=2")
                self.state_parser=2

        #PARSER 2 pour le timer du tracker
        if self.state_parser2==0:
            if tag=='span':
                for name, value in attrs:
                    if name=='id' and value=='track-timer':
                        self.state_parser2=1
                        
        elif self.state_parser2==1:
            if tag=='script':
                self.state_parser2=2
                        
    def handle_data(self, data):
        data = data.strip(" \t\n")
        if self.state_parser==-1:
            if data!='':
                #print("Territory: "+data)
                self.territory_name = dict_tw_territory_names[data]
                #print("Territory: "+self.territory_name)
                #print("state_parser=0")
                self.state_parser=0

        elif self.state_parser==2:
            if data!='':
                #print("Player: "+data)
                self.opp_name = data
                self.list_opp_teams.append([self.territory_name, self.opp_name, []])
                #print("state_parser=3")
                self.state_parser=3

        #PARSER 2 for TIME TRACK
        if self.state_parser2==2:
            #print(data)
            ret_re = re.search('{seconds: (.*?)}', data)
            timer_seconds_txt = ret_re.group(1)
            self.seconds_since_last_track = int(timer_seconds_txt)
            self.state_parser2=0
                
    def get_opp_teams(self):
        return self.list_opp_teams
                
    def get_last_track(self):
        return self.seconds_since_last_track

class RaidListParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.warstats_raid_name=''
        self.warstats_raid_id=''
        self.warstats_raid_in_progress=True
        self.state_parser=0
        #0: en recherche de div id="raids"
        #1: en recherche de h2 ou h3
        #2: en recherche de data="In progress" ou "Previous raids"
        #3: en recherche de <tbody>
        #4: en recherche de <tr>
        #5: en recherche de <td>
        #6: en recherche de <a>
        #7: en recherche de data = raid_name >> goto state 8 si trouvé, sinon state 4
        #>3: en recherche de </tbody> >> goto state 1
        #8: état final, raid trouvé

        self.state_parser2=0
        #0: en recherche de <span id="track-timer"
        #1: en recherche de script
        #2: en recherche de data
        
    def handle_starttag(self, tag, attrs):
        if self.state_parser==0:
            if tag=='div':
                for name, value in attrs:
                    if name=='id' and value=='raids':
                        self.state_parser=1

        elif self.state_parser==1:
            if tag=='h2' or tag=='h3':
                self.state_parser=2

        elif self.state_parser==3:
            if tag=='tbody':
                self.state_parser=4

        elif self.state_parser==4:
            if tag=='tr':
                self.state_parser=5

        elif self.state_parser==5:
            if tag=='td':
                self.state_parser=6

        elif self.state_parser==6:
            if tag=='a':
                for name, value in attrs:
                    if name=='href':
                        self.warstats_raid_id = value.split("/")[3]
                        self.state_parser=7


        #PARSER 2 pour le timer du tracker
        if self.state_parser2==0:
            if tag=='span':
                for name, value in attrs:
                    if name=='id' and value=='track-timer':
                        self.state_parser2=1
                        
        elif self.state_parser2==1:
            if tag=='script':
                self.state_parser2=2


    def handle_endtag(self, tag):
        if self.state_parser >3 and self.state_parser!=8:
            if tag=='tbody':
                self.state_parser=1

    def handle_data(self, data):
        data = data.strip(" \t\n")
        if self.state_parser==2:
            if data=='In progress':
                self.warstats_raid_in_progress = True
                self.state_parser=3
            elif data=='Previous raids':
                self.warstats_raid_in_progress = False
                self.state_parser=3
            else:
                self.state_parser=1

        if self.state_parser==7:
            if data==self.warstats_raid_name:
                self.state_parser=8
            else:
                self.state_parser=4


        #PARSER 2 for TIME TRACK
        if self.state_parser2==2:
            #print(data)
            ret_re = re.search('{seconds: (.*?)}', data)
            timer_seconds_txt = ret_re.group(1)
            self.seconds_since_last_track = int(timer_seconds_txt)
            self.state_parser2=0
                
    def get_raid_id(self):
        return [self.warstats_raid_id, self.warstats_raid_in_progress]
 
    def get_last_track(self):
        return self.seconds_since_last_track

    def set_raid_name(self, raid_name):
        self.warstats_raid_name = raid_name
                
                
class RaidResumeParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.seconds_since_last_track = 0
        self.player_name = ""
        self.dict_player_scores = {}
        self.raid_phase = 0
        self.state_parser = -3
        #-3: en recherche de <div class="raid-banner
        #-2: en recherche de <div class="current"
        #-1: en recherche de data
        #0: en recherche de <h3>
        #1: en recherche de data = "Players"
        #2: en recherche de <tbody>
        #3: en recherche de <tr>
        #4: en recherche de <td>
        #5: en recherche de <td>
        #6: en recherche de data
        #7: en recherche de <td>
        #8: en recherche de data >> goto state 3
        #>2: en recherche de </tbody> >> goto state 9
        #9: état final
        
        self.state_parser2=0
        #0: en recherche de <span id="track-timer"
        #1: en recherche de script
        #2: en recherche de data
        
    def handle_starttag(self, tag, attrs):
        if self.state_parser==-3:
            if tag=='div':
                for name, value in attrs:
                    if name=='class' and value.startswith("raid-banner"):
                        self.state_parser=-2

        elif self.state_parser==-2:
            if tag=='div':
                for name, value in attrs:
                    if name=='class' and value=="current":
                        self.state_parser=-1

        elif self.state_parser<=0:
            if tag=='h3':
                self.state_parser=1

        elif self.state_parser==2:
            if tag=='tbody':
                self.state_parser=3

        elif self.state_parser==3:
            if tag=='tr':
                self.state_parser=4

        elif self.state_parser==4:
            if tag=='td':
                self.state_parser=5

        elif self.state_parser==5:
            if tag=='td':
                self.state_parser=6

        elif self.state_parser==7:
            if tag=='td':
                self.state_parser=8


        #PARSER 2 pour le timer du tracker
        if self.state_parser2==0:
            if tag=='span':
                for name, value in attrs:
                    if name=='id' and value=='track-timer':
                        self.state_parser2=1
                        
        elif self.state_parser2==1:
            if tag=='script':
                self.state_parser2=2

    def handle_endtag(self, tag):
        if self.state_parser >2:
            if tag=='tbody':
                self.state_parser=9

    def handle_data(self, data):
        data = data.strip(" \t\n")
        if self.state_parser==-1:
            self.raid_phase = int(float(data[:-1])/25 + 1)
            self.state_parser=0

        elif self.state_parser==1:
            if data=="Players":
                self.state_parser=2

        elif self.state_parser==6:
            if data!='':
                self.player_name = data
                self.state_parser=7

        elif self.state_parser==8:
            if data!='':
                if data == "-":
                    score = 0
                else:
                    score_txt = data.replace(",", "")
                    score=int(score_txt)
                self.dict_player_scores[self.player_name] = score
                self.state_parser=3

        #PARSER 2 for TIME TRACK
        if self.state_parser2==2:
            #print(data)
            ret_re = re.search('{seconds: (.*?)}', data)
            timer_seconds_txt = ret_re.group(1)
            self.seconds_since_last_track = int(timer_seconds_txt)
            self.state_parser2=0
                
    def get_player_scores(self):
        return self.dict_player_scores
                
    def get_raid_phase(self):
        return self.raid_phase
                
    def get_last_track(self):
        return self.seconds_since_last_track
                

###############################################################
# Function: fresh_urlopen
# Description: create a url with a random and fake argument
#              and require a max-age parameter in header
#              to force the server sending fresh data
# Input: url (string)
# Output: same as urllib.request.urlopen
###############################################################
def urlopen(url):
    req = urllib.request.Request(url)
    goutils.log2("INFO", url)
    return urllib.request.urlopen(req, timeout=10)

def parse_tb_platoons(guild_id, force_latest):
    global dict_next_warstats_read
    global dict_parse_tb_platoons_run_once
    global dict_tb_active_round
    global dict_tb_platoons
    global dict_tb_open_territories

    if not guild_id in dict_next_warstats_read:
        init_globals(guild_id)

    #First, check there is value to re-parse the page
    if time.time() < dict_next_warstats_read[guild_id]["tb_platoons"] and dict_parse_tb_platoons_run_once[guild_id]:
        goutils.log2("DBG", "Use cached data. Next warstats refresh in "+str(get_next_warstats_read("tb_platoons", guild_id))+" secs")
    else:
        warstats_tbs_url_guild = warstats_tbs_url + str(guild_id)
        try:
            page = urlopen(warstats_tbs_url_guild)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            goutils.log2('ERR', 'error while opening '+warstats_tbs_url_guild)
            return dict_tb_active_round[guild_id], dict_tb_platoons[guild_id], dict_tb_open_territories[guild_id]
        
        dict_parse_tb_platoons_run_once[guild_id] = True

        tb_list_parser = TBSListParser()
        tb_list_parser.feed(page.read().decode('utf-8', 'ignore'))
    
        if tb_list_parser.get_battle_id(force_latest) == None:
            goutils.log2('INFO', 'no TB in progress')

            dict_tb_active_round[guild_id] = ""
            dict_tb_platoons[guild_id] = {}
            dict_tb_open_territories[guild_id] = []

            set_next_warstats_read_long(18, 'UTC', "tb_platoons", guild_id)

            return dict_tb_active_round[guild_id], dict_tb_platoons[guild_id], dict_tb_open_territories[guild_id]
        else:
            goutils.log2('INFO', "TB "+tb_list_parser.get_battle_id(force_latest)+" in progress")
        
        warstats_platoon_url=warstats_platoons_baseurl+tb_list_parser.get_battle_id(force_latest)
    
        for phase in range(1,7):
            try:
                page = urlopen(warstats_platoon_url+'/'+str(phase))
            except (urllib.error.HTTPError, urllib.error.URLError) as e:
                goutils.log2('WAR', 'page introuvable '+warstats_platoon_url+'/'+str(phase))
                continue

            platoon_parser = TBSPhasePlatoonParser()
            platoon_parser.feed(page.read().decode('utf-8', 'ignore'))
            dict_tb_platoons[guild_id].update(platoon_parser.get_dict_platoons())
            dict_tb_active_round[guild_id] = platoon_parser.get_active_round()
    
        if dict_tb_active_round[guild_id] != "":
            warstats_tb_resume_url=warstats_tb_resume_baseurl+tb_list_parser.get_battle_id(force_latest)+'/'+dict_tb_active_round[guild_id][3]

            page = urlopen(warstats_tb_resume_url)
            resume_parser = TBSPhaseResumeParser()
            #resume_parser.set_active_round(int(platoon_parser.get_active_round()[3]))
            resume_parser.feed(page.read().decode('utf-8', 'ignore'))
    
            dict_tb_open_territories[guild_id] = resume_parser.get_open_territories()
        else:
            goutils.log2('WAR', "Erreur de lecture, renvoie des valeurs précédentes")

        set_next_warstats_read_short(resume_parser.get_last_track(), "tb_platoons", guild_id)

    return dict_tb_active_round[guild_id], dict_tb_platoons[guild_id], dict_tb_open_territories[guild_id]

def parse_tb_player_scores(guild_id, tb_alias, force_latest):
    global dict_next_warstats_read
    global dict_parse_tb_player_scores_run_once
    global dict_tb_active_round
    global dict_tb_player_scores
    global dict_tb_open_territories

    if not guild_id in dict_next_warstats_read:
        init_globals(guild_id)

    #First, check there is value to re-parse the page
    if time.time() < dict_next_warstats_read[guild_id]["tb_player_scores"] and dict_parse_tb_platoons_run_once[guild_id]:
        goutils.log2("DBG", "Use cached data. Next warstats refresh in "+str(get_next_warstats_read("tb_player_scores", guild_id))+" secs")
    else:
        warstats_tbs_url_guild = warstats_tbs_url + str(guild_id)
        try:
            page = urlopen(warstats_tbs_url_guild)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            goutils.log2('ERR', 'error while opening '+warstats_tbs_url_guild)
            return dict_tb_active_round[guild_id], dict_tb_player_scores[guild_id], dict_tb_open_territories[guild_id]
        
        dict_parse_tb_player_scores_run_once[guild_id] = True

        tb_list_parser = TBSListParser()
        tb_list_parser.set_tb_alias(tb_alias)
        tb_list_parser.feed(page.read().decode('utf-8', 'ignore'))
    
        if tb_list_parser.get_battle_id(force_latest) == None:
            goutils.log2('INFO', 'no TB '+tb_alias+' found')

            dict_tb_active_round[guild_id] = ""
            dict_tb_player_scores[guild_id] = {}
            dict_tb_open_territories[guild_id] = []

            set_next_warstats_read_long(18, 'UTC', "tb_player_scores", guild_id)

            return dict_tb_active_round[guild_id], dict_tb_player_scores[guild_id], dict_tb_open_territories[guild_id]
        else:
            goutils.log2('INFO', "TB "+tb_list_parser.get_battle_id(force_latest)+" in progress")
        
        warstats_tb_resume_url=warstats_tb_resume_baseurl+tb_list_parser.get_battle_id(force_latest)
    
        for phase in range(1,7):
            try:
                page = urlopen(warstats_tb_resume_url+'/'+str(phase))
            except (urllib.error.HTTPError, urllib.error.URLError) as e:
                goutils.log2('WAR', 'page introuvable '+warstats_tb_resume_url+'/'+str(phase))
                continue

            resume_parser = TBSPhaseResumeParser()
            resume_parser.feed(page.read().decode('utf-8', 'ignore'))
            phase_player_scores = resume_parser.get_player_scores()
            for player in dict_tb_player_scores[guild_id]:
                if player in phase_player_scores:
                    dict_tb_player_scores[guild_id][player].update(phase_player_scores[player])
            for player in phase_player_scores:
                if not player in dict_tb_player_scores[guild_id]:
                    dict_tb_player_scores[guild_id][player] = dict(phase_player_scores[player])
            dict_tb_active_round[guild_id] = resume_parser.get_active_round()

            if phase == dict_tb_active_round[guild_id]:
                dict_tb_open_territories[guild_id] = resume_parser.get_open_territories()
    
        set_next_warstats_read_short(resume_parser.get_last_track(), "tb_player_scores", guild_id)

    return dict_tb_active_round[guild_id], dict_tb_player_scores[guild_id], dict_tb_open_territories[guild_id]

def parse_tb_guild_scores(guild_id, force_latest):
    global dict_next_warstats_read
    global dict_parse_tb_guild_scores_run_once
    global dict_tb_active_round
    global dict_tb_territory_scores

    if not guild_id in dict_next_warstats_read:
        init_globals(guild_id)

    #First, check there is value to re-parse the page
    if time.time() < dict_next_warstats_read[guild_id]["tb_territory_scores"] and dict_parse_tb_guild_scores_run_once[guild_id]:
        goutils.log2("DBG", "Use cached data. Next warstats refresh in "+str(get_next_warstats_read("tb_territory_scores", guild_id))+" secs")
    else:
        warstats_tbs_url_guild = warstats_tbs_url + str(guild_id)
        try:
            page = urlopen(warstats_tbs_url_guild)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            goutils.log2('WAR', 'error while opening '+warstats_tbs_url_guild)
            return dict_tb_territory_scores[guild_id], dict_tb_active_round[guild_id]
        
        dict_parse_tb_guild_scores_run_once[guild_id] = True

        tb_list_parser = TBSListParser()
        tb_list_parser.feed(page.read().decode('utf-8', 'ignore'))
        
        if tb_list_parser.get_battle_id(force_latest) == None:
            goutils.log2('INFO', 'no TB in progress')

            dict_tb_active_round[guild_id] = ""
            dict_tb_territory_scores[guild_id] = {}

            set_next_warstats_read_long(18, 'UTC', "tb_territory_scores", guild_id)

            return dict_tb_territory_scores[guild_id], dict_tb_active_round[guild_id]
        else:
            goutils.log2('INFO', "TB "+tb_list_parser.get_battle_id(force_latest)+" in progress")
    
        warstats_tb_resume_url=warstats_tb_resume_baseurl+tb_list_parser.get_battle_id(force_latest)
        try:
            page = urlopen(warstats_tb_resume_url)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            goutils.log2("ERR", "error while opening "+warstats_tb_resume_url)
            return dict_tb_territory_scores[guild_id], dict_tb_active_round[guild_id]

        resume_parser = TBSPhaseResumeParser()
        # resume_parser.set_active_round(int(platoon_parser.get_active_round()[3]))
        resume_parser.feed(page.read().decode('utf-8', 'ignore'))
        dict_tb_active_round[guild_id] = resume_parser.get_active_round()
    
        goutils.log2('INFO', "TB name = "+dict_tb_active_round[guild_id])
        dict_tb_territory_scores[guild_id] = resume_parser.get_territory_scores()

        set_next_warstats_read_short(resume_parser.get_last_track(), "tb_territory_scores", guild_id)

    return dict_tb_territory_scores[guild_id], dict_tb_active_round[guild_id]

def parse_tw_teams(guild_id):
    global dict_next_warstats_read
    global dict_opponent_teams

    if not guild_id in dict_next_warstats_read:
        init_globals(guild_id)

    #First, check there is value to re-parse the page
    if time.time() < dict_next_warstats_read[guild_id]["tw_teams"]:
        goutils.log2("DBG", "Use cached data. Next warstats refresh in "+str(get_next_warstats_read("tw_teams", guild_id))+" secs")
    else:
        warstats_tws_url_guild = warstats_tws_url + str(guild_id)
        try:
            page = urlopen(warstats_tws_url_guild)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            goutils.log2('ERR', 'error while opening '+warstats_tws_url_guild)
            return dict_opponent_teams[guild_id]
        
        tw_list_parser = TWSListParser()
        tw_list_parser.feed(page.read().decode('utf-8', 'ignore'))
    
        [war_id, war_in_progress] = tw_list_parser.get_war_id()
        if not war_in_progress:
            goutils.log2('INFO', "no TW in progress")
            dict_opponent_teams[guild_id] = []

            set_next_warstats_read_long(19, 'UTC', "tw_teams", guild_id)

            return dict_opponent_teams[guild_id]
    
        goutils.log2('INFO', "Current TW is "+war_id)
        warstats_opp_squad_url=warstats_opp_squad_baseurl+war_id
        try:
            page = urlopen(warstats_opp_squad_url)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            goutils.log2('ERR', 'error while opening '+warstats_opp_squad_url)
            return dict_opponent_teams[guild_id]

        opp_squad_parser = TWSOpponentSquadParser()
        opp_squad_parser.feed(page.read().decode('utf-8', 'ignore'))

        dict_opponent_teams[guild_id] = opp_squad_parser.get_opp_teams()

        set_next_warstats_read_short(opp_squad_parser.get_last_track(), "tw_teams", guild_id)

    return dict_opponent_teams[guild_id]

def parse_raid_scores(guild_id, raid_name):
    global dict_next_warstats_read
    global dict_raid_player_scores
    global dict_raid_phase

    if not guild_id in dict_next_warstats_read:
        init_globals(guild_id)

    #First, check there is value to re-parse the page
    if time.time() < dict_next_warstats_read[guild_id]["raid_scores"]:
        goutils.log2("DBG", "Use cached data. Next warstats refresh in "+str(get_next_warstats_read("raid_scores", guild_id))+" secs")
    else:
        warstats_raids_url_guild = warstats_raids_url + str(guild_id)
        try:
            page = urlopen(warstats_raids_url_guild)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            goutils.log2('ERR', 'error while opening '+warstats_raids_url_guild)
            return dict_raid_phase[guild_id][raid_name], dict_raid_player_scores[guild_id][raid_name]
        
        raid_list_parser = RaidListParser()
        raid_list_parser.set_raid_name(raid_name)
        raid_list_parser.feed(page.read().decode('utf-8', 'ignore'))
    
        [raid_id, raid_in_progress] = raid_list_parser.get_raid_id()
        if raid_id == 0:
            goutils.log2('INFO', raid_name+" raid not found")
            dict_raid_player_scores[guild_id][raid_name] = {}
            dict_raid_phase[guild_id][raid_name] = 0
        else:
            if raid_in_progress:
                goutils.log2('INFO', "Current "+raid_name+" raid is "+raid_id)
            else:
                goutils.log2('INFO', "Latest "+raid_name+" raid is "+raid_id)
    
            warstats_raid_resume_url=warstats_raid_resume_baseurl+raid_id
            try:
                page = urlopen(warstats_raid_resume_url)
            except (urllib.error.HTTPError, urllib.error.URLError) as e:
                goutils.log2('ERR', 'error while opening '+warstats_raid_resume_url)
                return dict_raid_phase[guild_id][raid_name], dict_raid_player_scores[guild_id][raid_name]

            raid_resume_parser = RaidResumeParser()

            raid_resume_parser.feed(page.read().decode('utf-8', 'ignore'))

            dict_raid_player_scores[guild_id][raid_name] = raid_resume_parser.get_player_scores()
            dict_raid_phase[guild_id][raid_name] = raid_resume_parser.get_raid_phase()
            if dict_raid_phase[guild_id][raid_name] == 5:
                total_score = sum(dict_raid_player_scores[guild_id][raid_name].values())
                if total_score >= sum(data.dict_raid_tiers[raid_name]):
                    dict_raid_phase[guild_id][raid_name] = 5
                elif total_score >= sum(data.dict_raid_tiers[raid_name][:3]):
                    dict_raid_phase[guild_id][raid_name] = 4
                elif total_score >= sum(data.dict_raid_tiers[raid_name][:2]):
                    dict_raid_phase[guild_id][raid_name] = 3
                elif total_score >= sum(data.dict_raid_tiers[raid_name][:1]):
                    dict_raid_phase[guild_id][raid_name] = 2
                else:
                    dict_raid_phase[guild_id][raid_name] = 1

        set_next_warstats_read_short(raid_list_parser.get_last_track(), "raid_scores", guild_id)

    return dict_raid_phase[guild_id][raid_name], dict_raid_player_scores[guild_id][raid_name]
