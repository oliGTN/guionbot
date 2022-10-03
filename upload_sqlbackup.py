import config
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
import json

gauth = GoogleAuth()
scope = ["https://www.googleapis.com/auth/drive"]
creds_envVar = config.GAPI_CREDS
creds_json = json.loads(creds_envVar)

gauth.credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
drive = GoogleDrive(gauth)
fid=config.GDRIVE_SQLBACKUP_ID
f = drive.CreateFile({"title": "all_tables.gz", "parents": [{"kind": "drive#fileLink", "id": fid}]})
f.SetContentFile('../SQLBACKUP/all_tables.gz')
f.Upload()

