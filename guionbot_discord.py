# Source --> https://realpython.com/how-to-make-a-discord-bot-python/
# CERTIFICATE_VERIFY_FAILED --> https://github.com/Rapptz/discord.py/issues/4159

import os
from discord.ext import commands
from go import function_tw, function_twt, split_txt

#load_dotenv()
#TOKEN = os.getenv('DISCORD_TOKEN')
TOKEN = 'NzUyOTY5NjQ3MjMzNTY0NzAz.X1fXoQ.arxYkcPspOFTU5SeCooiKsgkZNQ'
bot = commands.Bot(command_prefix='go.')
emoji_thumb = '\N{THUMBS UP SIGN}'

nb_commandes=0

async def update_stats():
    await client.wait_until_ready()
    global nb_commandes

    while not bot.is_closed():
        try:
            with open("stats.txt", "a") as f:
                f.write(f"Time: {int(time.time())}, Commandes: {nb_commandes}\n")

            await asyncio.sleep(5)
        except Exception as e:
            print(e)
            await asyncio.sleep(5)
			
@bot.event
async def on_ready():
	print(f'{bot.user.name} has connected to Discord!')

@bot.command(name='info')
async def nine_nine(ctx):
	global nb_commandes
	nb_commandes++

	await ctx.send('GuiOn bot is UP')
	
@bot.command(name='gt', help='Compare 2 guildes pour la GT')
async def gt(ctx, allycode, op_alycode):
	global nb_commandes
	nb_commandes++

	ret_gt=function_tw(allycode, op_alycode)
	#print(len(ret_gt))
	for txt in split_txt(ret_gt, 1000):
		await ctx.send('`'+txt+'`')

@bot.command(name='gtt', help='Liste la dispo d une team dans la guilde')
async def gtt(ctx, allycode, team):
	global nb_commandes
	nb_commandes++

	await ctx.message.add_reaction(emoji_thumb)
	ret_gt=function_twt(allycode, team)
	#print(len(ret_gt))
	for txt in split_txt(ret_gt, 1000):
		await ctx.send('`'+txt+'`')
		
bot.loop.create_task(update_stats())
bot.run(TOKEN)