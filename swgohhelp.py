# -*- coding: utf-8 -*-
"""
Created on Tue Sep  4 20:49:07 2018

@author: platzman
"""

import requests
from json import loads, dumps
import time

class SWGOHhelp():
    def __init__(self, settings):
        self.user = "username="+settings.username     
        self.user += "&password="+settings.password
        self.user += "&grant_type=password"
        self.user += "&client_id="+settings.client_id
        self.user += "&client_secret="+settings.client_secret
    	    	
        self.token = str()
        self.token_expires = time.time()
        
        self.urlBase = 'https://api.swgoh.help'
        self.signin = '/auth/signin'
        
    def get_token(self):
        if (time.time() >= self.token_expires) or (not 'Authorization' in self.token):
            sign_url = self.urlBase+self.signin
            payload = self.user
            head = {"Content-type": "application/x-www-form-urlencoded",
                    'Content-Length': str(len(payload))}
            r = requests.request('POST',sign_url, headers=head, data=payload, timeout = 10)
            if r.status_code != 200:
                error = 'Cannot login with these credentials'
                return  {"status_code" : r.status_code,
                         "message": error}
            _tok = loads(r.content.decode('utf-8'))['access_token']
            _tok_expires = loads(r.content.decode('utf-8'))['expires_in']
            self.token = { 'Authorization':"Bearer "+_tok} 
            self.token_expires = time.time()+_tok_expires
        
        return(self.token)

    def get_data(self, data_type, spec, language):
        token = self.get_token()
        # print("DBG - token: "+str(token))
        if 'Authorization' in token:
            head = {'Method': 'POST','Content-Type': 'application/json','Authorization': token['Authorization']}

            if spec in ["zetas", "squads"]:
                data_type = spec
                payload = {}
            elif data_type == 'data':
                if spec == "unitsList":
                    match_opts = {'rarity':7, 'obtainable':True, 'obtainableTime':0}
                else:
                    match_opts = {}
                payload = {'collection': spec, 'language': language, 'match': match_opts}
            else:
                payload = {'allycode': spec, 'language': language}
            data_url = self.urlBase+"/swgoh/"+data_type
            #print("data_url: "+str(data_url))
            try:
                r = requests.request('POST',data_url, headers=head, data = dumps(payload))
                if r.status_code != 200:
                    data = {"status_code" : r.status_code,
                             "message": r.content.decode('utf-8')}
                    print("headers: "+str(r.headers))
                else:
                    data = loads(r.content.decode('utf-8'))
            except:
                data = {"message": 'Cannot fetch data'}
            return data
        else:
            print("token: "+str(token))
            return {"message": 'no token from https://api.swgoh.help/'}

class settings():
    def __init__(self, _username, _password, _client_id, _client_secret):
        self.username = _username
        self.password = _password
        self.client_id = _client_id
        self.client_secret = _client_secret
