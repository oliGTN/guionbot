# -*- coding: utf-8 -*-
import os

# ======== COMON VARIABLES ===========
# These Google API credentials come from https://console.developers.google.com/
os.environ["GAPI_CREDS"]=""

# https://api.swgoh.help/profile
os.environ["SWGOHAPI_LOGIN"]=""
os.environ["SWGOHAPI_PASSWORD"]=""

# mysql://username:password@hostname/database_name
os.environ["MYSQL_DATABASE_URL"]=""

# Allycode of one member of the guild where the bot is installed
os.environ["MASTER_GUILD_ALLYCODE"]=""

# Timezone for the guild
os.environ["GUILD_TIMEZONE"]=""

# ======== FOR DISCORD ONLY ===========
# This token comes from https://discord.com/developers/ then settings / Bot / Token
os.environ["DISCORD_BOT_TOKEN"]=""

# Channel ID to read EchoBot allocations, and EchoBot Discord name
os.environ["EB_CHANNEL"]=""
os.environ["EB_PROFILE"]=""

# Discord IDs of bot administrators (allowed to launch speciel commands). Separator=<space>
os.environ["GO_ADMIN_IDS"]=""

# Category name to get members and check discord online status
os.environ["DISCORD_MEMBER_ROLE"]=""

# variables to control the refresh rate of players
os.environ["REFRESH_RATE_BOT_MINUTES"]=""
os.environ["REFRESH_RATE_PLAYER_MINUTES"]=""
os.environ["KEEP_MAX_NONMASTER_GUILDS"]=""
os.environ["KEEP_MAX_NOGUILD_PLAYERS"]=""
