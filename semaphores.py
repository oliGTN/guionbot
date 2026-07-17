#########################################
#SEMAPHORE functions to manage parallel access to
#- files: id = full file path
#- player data in CG's DB: id = txt_allyCode
#########################################

import inspect
import threading
import asyncio

import goutils

#GLOBAL variable for the bot
dict_sem={}

#IN: id = unique id of the semaphore
#IN: waiting = True if the function needs to wait for the semaphore to be released
#              False if the function return 1 if the semaphore is already locked
#OUT: 0 = semaphore unlocked, ready to use
#     1 = semaphore locked, cannot continue
async def acquire_sem(id, waiting=True):
    global dict_sem

    id=str(id)
    calling_func = inspect.stack()[2][3]
    #goutils.log2("DBG", "["+calling_func+"]sem to acquire: "+id)
    if not id in dict_sem:
        dict_sem[id] = threading.Semaphore()

    while not dict_sem[id].acquire(blocking=False):
        if waiting:
            await asyncio.sleep(1)
        else:
            goutils.log2("WAR", "["+calling_func+"]sem is locked: "+id)
            return 1

    #goutils.log2("DBG", "["+calling_func+"]sem acquired: "+id)

    return 0

async def release_sem(id):
    global dict_sem

    id=str(id)
    calling_func = inspect.stack()[2][3]
    #goutils.log2("DBG", "["+calling_func+"]sem to release: "+id)
    dict_sem[id].release()
    #goutils.log2("DBG", "["+calling_func+"]sem released: "+id)
