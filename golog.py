# -*- coding: utf-8 -*-
from datetime import datetime
import inspect

import config

################################################
# function: log
################################################
def log(level, txt, identifier=None):
    now = datetime.now()
    dt_string = now.strftime("%Y/%m/%d %H:%M:%S")
    module_name = inspect.stack()[1][1].split("/")[-1][:-3]
    fct = module_name+"."+inspect.stack()[1][3]
    code_line = inspect.stack()[1][2]

    if identifier != None:
        id_txt = "["+identifier+"]"
    else:
        id_txt = ""

    log_string = dt_string+":"+level+":"+fct+"["+str(code_line)+"]:"+id_txt+str(txt)

    if level=='DBG':
        if config.LOG_LEVEL=='DBG':
            print(log_string, flush=True)
    else:
        print(log_string, flush=True)

