import os
import goutils

def get_guild_loading_status(guildName):
    cache_guild_filename = "CACHE"+os.path.sep+guildName+"_loading.tmp"
    if os.path.isfile(cache_guild_filename):
        f=open(cache_guild_filename, 'r')
        status = f.read()
        f.close()
        return status
    else:
        return None

def set_guild_loading_status(guildName, status):
    cache_guild_filename = "CACHE"+os.path.sep+guildName+"_loading.tmp"
    if status == None:
        #remove file
        os.remove(cache_guild_filename)
    else:
        f = open(cache_guild_filename, 'w')
        f.write(status)
        f.close()

def get_other_guilds_loading_status(guildName):
    cache_files = os.listdir("CACHE")
    cache_guild_basename = guildName+"_loading.tmp"
    cache_guild_basenames = [x for x in cache_files if x.endswith("_loading.tmp") \
                                and x!=cache_guild_basename]
    list_status = []
    for basename in cache_guild_basenames:
        f=open("CACHE"+os.path.sep+basename, 'r')
        status = f.read()
        f.close()
        guildName = basename[:-len("_loading.tmp")]
        list_status.append(guildName+" ("+status+")")

    return list_status

def clean_cache():
    if os.path.isdir("CACHE"):
        cache_files = os.listdir("CACHE")
        cache_guild_basenames = [x for x in cache_files if x.endswith("_loading.tmp")]

        for basename in cache_guild_basenames:
            try:
                os.remove("CACHE"+os.path.sep+basename)
            except FileNotFoundError as e:
                pass
    else:
        os.mkdir("CACHE")
