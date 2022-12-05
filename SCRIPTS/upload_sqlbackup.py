import config
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from oauth2client.service_account import ServiceAccountCredentials
import json
import sys

gauth = GoogleAuth()
scope = ["https://www.googleapis.com/auth/drive"]
creds_envVar = config.GAPI_CREDS
creds_json = json.loads(creds_envVar)

gauth.credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds_json, scope)
drive = GoogleDrive(gauth)
dir_id=config.GDRIVE_SQLBACKUP_ID
fpath=config.SQLBACKUP_GZ
if len(sys.argv)>1 and sys.argv[1] == "create":
    f = drive.CreateFile({"title": "all_tables.gz", "parents": [{"kind": "drive#fileLink", "id": dir_id}]})
else:
    file_list = drive.ListFile({'q': "'"+str(dir_id)+"' in parents and trashed=false"}).GetList()
    fid = (file_list[0]['id'])
    f = drive.CreateFile({"id": fid})

f.SetContentFile(fpath)
f.Upload()

