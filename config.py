import discord
import os

# Define your bot's prefix
prefix = ["h. ", "H. ", "h.", "H."]

# Define your bot's token
YOUR_BOT_TOKEN = os.environ.get('token')

# Your default status
default_status = discord.Status.idle

# Beginner roles for BLEACH guild
bleach_beginner_roles = [
    1144194274607497237, 1143252276325138562, 1144194627801452604
]

# Role IDs to remove from the user
booster_role_ids_to_remove = [
  1176224840726876241, 1176224974088978432, 1176225088908042372,
  1176225265920249978, 1176225567025135617, 1176225671253610617,
  1176225808164077711, 1176225956399157258, 1176225468228321391,
  1176226183910797403, 1176323848015188119, 1176321601801814117,
  1176206230071545919, 1176205652704632933, 1176322853696716811,
  1176206369951592498, 1176206470279331850, 1176204796689125437,
  1176205975544410202, 1176204456157794314, 1176563824040611850,
  1176204373529985155, 1176206132218437772, 1176205379118575697,
  1176205864324059160, 1176456251467645009, 1176456241489387530,
  1176456244593172552, 1176456248082825278, 1176456254797918268
]

# Define guild name and ID
bleach_guild_name = "BLEACH"
bleach_guild_id = 679934068917534720

# Define roles name and ID
owner_role_name = "⎧💠⎫ Soul King"
owner_role_id = 679951055722643459

commander_role_name = "⎧ 👑 ⎫The Commanders"
commander_role_id = 777664276558774275

oken_role_name = "Soul King's Right Hand"
oken_role_id = 1180144923660517536

mod_role_name = "⎧♠️⎫ Gotei 13"
mod_role_id = 1143257541292339200

staff_role_name = "Server Staff"
staff_role_id = 1176230810123255898

mute_role_name = "Sealed by Hogyoku"
mute_role_id = 1176357487058894980

lvl10_role_name = "⎧👻⎫Soul Reaper"
lvl10_role_id = 1176204544590479371

bleach_booster_role_name = "Booster"
bleach_booster_role_id = 680453723377762325

active_mod_role_name = "Active Mod🌸"
active_mod_role_id = 1176233479869055046

inactive_mod_role_name = "Inactive Mod🥀"
inactive_mod_role_id = 1176234092325503048

five_stars_role_name = "⭐️⭐️⭐️⭐️⭐️"
five_stars_role_id = 1176218504240824360

human_role_name = "Human"
human_role_id = 1143252276325138562

hollow_role_name = "⎧💀⎫ Hollow"
hollow_role_id = 1176205337393627277

vollstandig_role_name = "⎧⛩️⎫ Vollständig"
vollstandig_role_id = 1176206170290131014

# Define channels name and ID
log_channel_name = "⇨⛔logs"
log_channel_id = 719749459894075412

attendance_channel_name = "⇨🤓attendance"
attendance_channel_id = 1154288576071213077

report_channel_name = "⇨🗳reports"
report_channel_id = 729453947173077032
