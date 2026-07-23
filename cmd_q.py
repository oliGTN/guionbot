# -*- coding: utf-8 -*-
# Source --> https://realpython.com/how-to-make-a-discord-bot-python/
# CERTIFICATE_VERIFY_FAILED --> https://github.com/Rapptz/discord.py/issues/4159

######################
# Queue and lock commands
######################

import config
from discord.ext import commands
from discord import app_commands, Interaction
import goutils

bot_test_mode = False
bot_background_tasks = True
bot_on_message = True
bot_locked = False
command_queue = []

MAX_QUEUE_SIZE = 5
async def add_command_to_queue(ctx_interaction):
    global command_queue

    #Initial waiting message
    resp_msg = await command_ack(ctx_interaction)

    # Check if not is locked
    is_owner = (str(ctx_interaction.user.id) in config.GO_ADMIN_IDS.split(' '))
    if bot_locked and not is_owner:
        goutils.log2("WAR", "bot is locked")
        await ctx_interaction.edit_original_response(content=emojis.prohibited+" Impossible de lancer la commande car le bot est verrouillé pour maintenance. Veuillez ré-essayer dans quelques minutes.")
        return 1, resp_msg

    # Add command to queue
    command_queue.append(ctx_interaction)

    #Loop to wait that the queue is ready
    pos_cmd = command_queue.index(ctx_interaction)
    while(pos_cmd >= MAX_QUEUE_SIZE):
        await ctx_interaction.edit_original_response(content="Tu es en position "+str(pos_cmd-MAX_QUEUE_SIZE+1)+" de la file d'attente...")
        await asyncio.sleep(10)
        pos_cmd = command_queue.index(ctx_interaction)

    return 0, resp_msg

def remove_command_from_queue(ctx_interaction):
    global command_queue
    while ctx_interaction in command_queue:
        command_queue.remove(ctx_interaction)

def display_command_queue():
    output_txt = ""
    for ctx_interaction in command_queue:
        if type(ctx_interaction) == commands.Context:
            user_id = ctx_interaction.author.id
            channel_id = ctx_interaction.channel.id
            date = ctx_interaction.message.created_at
            cmd = ctx_interaction.message
        else: # Interaction
            user_id = ctx_interaction.user.id
            channel_id = ctx_interaction.channel_id
            date = ctx_interaction.created_at
            cmd = ctx_interaction.command.qualified_name

        output_txt += "user_id=<@"+str(user_id)+"> dans <#"+str(channel_id)+">, date="+str(date)+", cmd="+str(cmd)+"\n"

    return len(command_queue), output_txt

def lock_bot():
    global bot_locked
    bot_locked = True

def unlock_bot():
    global bot_locked
    bot_locked = False

def islocked_bot():
    return bot_locked

async def command_ack(ctx_interaction):
    msg = None
    if type(ctx_interaction) == commands.Context:
        ctx = ctx_interaction
        msg = await ctx.reply(emojis.thumb+" "+ctx.me.name+" réfléchit...")

    elif type(ctx_interaction) == Interaction:
        interaction = ctx_interaction
        await interaction.response.defer(thinking=True)
    else:
        print("In progress...")

    return msg

