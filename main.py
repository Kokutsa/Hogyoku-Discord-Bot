import discord
from discord import app_commands
import discord.ext.commands
from discord.ext import commands, tasks
from discord.ext.commands import cooldown, BucketType, CommandOnCooldown

import math
import asyncio
from datetime import datetime as dt, timedelta
import datetime
import random
import requests
import sqlite3
import time
import re
from geopy.geocoders import Nominatim
import aiohttp
from typing import Union
import os
import io
from PIL import Image, ImageDraw, ImageFont

from menu_roles import SelectView
from help_menu import HelpButton
from ctime_menu import CtimeButton
import bleach_wallpapers
import bleach_quotes
from config import prefix, default_status, YOUR_BOT_TOKEN, booster_role_ids_to_remove, bleach_guild_name, bleach_guild_id, owner_role_name, owner_role_id, commander_role_name, commander_role_id, oken_role_name, oken_role_id, mod_role_name, mod_role_id, staff_role_name, staff_role_id, mute_role_name, mute_role_id, lvl10_role_name, lvl10_role_id, bleach_booster_role_name, bleach_booster_role_id, active_mod_role_name, active_mod_role_id, inactive_mod_role_name, inactive_mod_role_id, five_stars_role_name, five_stars_role_id, log_channel_name, log_channel_id, report_channel_name, report_channel_id, human_role_name, human_role_id, hollow_role_name, hollow_role_id, vollstandig_role_name, vollstandig_role_id
from keep_alive import keep_alive

keep_alive()

# Define your bot's intents (adjust as needed)
intents = discord.Intents.all()

# Create a bot instance with the specified intents
bot = commands.Bot(command_prefix=prefix,
                   intents=intents,
                   status=default_status)

# Define cooldowns for commands (in seconds)
cooldown_time = 86400  # 24 hours

# Dictionary to store cooldowns
cooldowns = {}

# Set the number of fields to display per page
fields_per_page = 10


# Initialize the SQLite database
def init_database():
  connection = sqlite3.connect('afk_statuses.db')
  cursor = connection.cursor()

  # Create the AFKStatuses table if it doesn't exist
  cursor.execute('''
        CREATE TABLE IF NOT EXISTS AFKStatuses (
            user_id INTEGER PRIMARY KEY,
            message TEXT,
            afk_timestamp REAL
        )
        ''')

  connection.commit()
  connection.close()


# Call the init_database function to create the database and table
init_database()


# Function to get the current GMT+7 time
def get_current_time_gmt7():
  return time.strftime("%Y-%m-%d",
                       time.gmtime(time.time() + 25200)), time.strftime(
                           "%H:%M:%S", time.gmtime(time.time() + 25200))


# Function to get the current GMT+7 time in AM/PM format
def get_current_time_gmt7_ampm():
  current_time = time.strftime("%I:%M:%S %p", time.gmtime(time.time() + 25200))
  return current_time


# Create or connect to the SQLite database
db_conn = sqlite3.connect('warnings.db')
db_cursor = db_conn.cursor()
db_cursor.execute('''CREATE TABLE IF NOT EXISTS warnings (
                    user_id INTEGER,
                    warning_count INTEGER,
                    mute_duration INTEGER,
                    PRIMARY KEY (user_id)
                )''')

# Create a table to store user-specific warnings
db_cursor.execute('''CREATE TABLE IF NOT EXISTS user_warnings (
                    user_id INTEGER,
                    reason TEXT,
                    PRIMARY KEY (user_id, reason)
                )''')

# Create a table to store temporary bans
db_cursor.execute('''CREATE TABLE IF NOT EXISTS temp_bans (
                    user_id INTEGER PRIMARY KEY,
                    unmute_time INTEGER
                )''')
db_conn.commit()


def is_authorized(ctx):
  return staff_role_id in [role.id for role in ctx.author.roles
                           ] or ctx.author.guild_permissions.administrator


def can_remove_warn(ctx):
  return commander_role_id in [role.id for role in ctx.author.roles
                               ] or ctx.author.guild_permissions.administrator


def oken_authorized(ctx):
  return oken_role_id in [role.id for role in ctx.author.roles
                          ] or ctx.author.guild_permissions.administrator


def human_authorized(ctx):
  """Check if the user is authorized to use certain commands."""
  authorized_user_id = 839315540068794399
  if (authorized_user_id == ctx.author.id
      or human_role_id in [role.id for role in ctx.author.roles]
      or ctx.author.guild_permissions.administrator):
    return True
  else:
    raise commands.CheckFailure(
        "Monke, you need to become a human, admin, or Kokugo first.")


def parse_time(duration):
  match = re.match(r'^(\d+)([smh])$', duration)
  if match:
    value, unit = match.groups()
    value = int(value)
    if unit == 's':
      return value
    elif unit == 'm':
      return value * 60
    elif unit == 'h':
      return value * 3600
  return None


@tasks.loop(seconds=60)
async def check_expired_mutes():
  current_time = time.time()
  for row in db_cursor.execute("SELECT user_id, unmute_time FROM temp_bans"):
    user_id, unmute_time = row
    if unmute_time <= current_time:
      user = bot.get_user(user_id)
      if user:
        guild = bot.get_guild(bleach_guild_id)
        mute_role = guild.get_role(mute_role_id)
        await user.remove_roles(mute_role)
      db_cursor.execute("DELETE FROM temp_bans WHERE user_id = ?", (user_id, ))
      db_conn.commit()


# Function to send a log message to the log channel
async def send_log_message(message):
  log_channel = bot.get_channel(log_channel_id)
  if log_channel:
    embed = discord.Embed(title="Log Message",
                          description=message,
                          color=discord.Color.blue())
    await log_channel.send(embed=embed)
  else:
    print("Log channel not found.")


# Custom cooldown decorator
def user_cooldown(
    rate,
    per,
    type=commands.BucketType.default,
    notify_message="Please wait {0:.2f} seconds before using this command again."
):

  def decorator(func):

    async def wrapper(ctx, *args, **kwargs):
      cooldown = commands.CooldownMapping.from_cooldown(rate, per, type)
      bucket = cooldown.get_bucket(ctx.message)
      retry_after = bucket.update_rate_limit()
      if retry_after:
        await ctx.send(notify_message.format(retry_after))
        return
      await func(ctx, *args, **kwargs)

    return wrapper

  return decorator


# Ensure the database connection is setup and the table is created
def setup_database():
  conn = sqlite3.connect('reminders.db')
  c = conn.cursor()
  c.execute('''CREATE TABLE IF NOT EXISTS reminders (
                    user_id INT,
                    message TEXT,
                    reminder_time INT
                )''')
  conn.commit()
  conn.close()


setup_database()


@tasks.loop(seconds=60)  # Check for reminders every 60 seconds
async def reminder_task():
  current_time = int(datetime.datetime.now().timestamp())
  conn = sqlite3.connect('reminders.db')
  c = conn.cursor()
  c.execute("SELECT * FROM reminders WHERE reminder_time <= ?",
            (current_time, ))
  reminders = c.fetchall()

  for row in reminders:
    user_id, message, _ = row
    user = bot.get_user(user_id)
    if user:
      await user.send(f"Reminder: {message}")

  # Remove the processed reminders
  for row in reminders:
    c.execute(
        "DELETE FROM reminders WHERE user_id = ? AND message = ? AND reminder_time = ?",
        (row[0], row[1], row[2]))
  conn.commit()
  conn.close()


@bot.tree.command(name='remind')
@app_commands.describe(duration="Duration in minutes.",
                       message="I will remind you in DMs.")
async def remind(interaction: discord.Interaction, duration: int, *,
                 message: str):
  """Set a reminder for yourself with a specified duration in minutes."""
  user = interaction.user
  # Check the number of reminders the user has
  conn = sqlite3.connect('reminders.db')
  c = conn.cursor()
  c.execute("SELECT COUNT(*) FROM reminders WHERE user_id = ?", (user.id, ))
  count = c.fetchone()[0]

  if count >= 3:
    await interaction.response.send_message(
        "You already have the maximum number of reminders (3).",
        ephemeral=True)
  else:
    reminder_time = int((datetime.datetime.now() +
                         datetime.timedelta(minutes=duration)).timestamp())
    c.execute(
        "INSERT INTO reminders (user_id, message, reminder_time) VALUES (?, ?, ?)",
        (user.id, message, reminder_time))
    conn.commit()
    conn.close()
    await interaction.response.send_message(
        f"Reminder set for yourself in {duration} minutes: {message}")


@bot.tree.command(name='reminders')
async def view_reminders(interaction: discord.Interaction):
  """View your stored reminders."""
  user = interaction.user
  conn = sqlite3.connect('reminders.db')
  c = conn.cursor()
  c.execute("SELECT message, reminder_time FROM reminders WHERE user_id = ?",
            (user.id, ))
  stored_reminders = c.fetchall()
  conn.close()

  if not stored_reminders:
    await interaction.response.send_message("You have no reminders stored.",
                                            ephemeral=True)
  else:
    reminder_list = "\n".join([
        f"{message} - <t:{int(time)}:R>" for message, time in stored_reminders
    ])
    await interaction.response.send_message(
        f"Your stored reminders:\n{reminder_list}", ephemeral=True)


@reminder_task.before_loop
async def before_reminder_task():
  await bot.wait_until_ready()


# Connect to SQLite database
conn = sqlite3.connect('bleach_bot.db')
c = conn.cursor()

# Create tables for users, leveling, and currency
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    exp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    daily_streak INTEGER DEFAULT 0,
    last_daily TIMESTAMP,
    soul_coins INTEGER DEFAULT 0,
    zanpakuto_tokens INTEGER DEFAULT 0,
    hogyoku_shards INTEGER DEFAULT 0,
    spirit_points INTEGER DEFAULT 0,
    gikongan_pills INTEGER DEFAULT 0
)
''')
conn.commit()


# Function to calculate experience and level
def calculate_exp(level):
  return (level / 0.07)**2


def calculate_level(exp):
  return int(0.07 * math.sqrt(exp))


# Function to add experience points
def add_exp(user_id, exp):
  c.execute('SELECT exp FROM users WHERE user_id = ?', (user_id, ))
  row = c.fetchone()
  if row:
    new_exp = row[0] + exp
    new_level = calculate_level(new_exp)
    c.execute('UPDATE users SET exp = ?, level = ? WHERE user_id = ?',
              (new_exp, new_level, user_id))
  else:
    new_exp = exp
    new_level = calculate_level(new_exp)
    c.execute('INSERT INTO users (user_id, exp, level) VALUES (?, ?, ?)',
              (user_id, new_exp, new_level))
  conn.commit()


# Function to get user data
def get_user_data(user_id):
  c.execute('SELECT * FROM users WHERE user_id = ?', (user_id, ))
  return c.fetchone()


@bot.event
async def on_ready():
  guild = bot.get_guild(bleach_guild_id)
  five_stars_role = discord.utils.get(guild.roles, id=five_stars_role_id)

  if five_stars_role:
    # Calculate the number of users with the bleach_booster_role in bleach_guild_id
    total_five_stars = sum(1 for member in guild.members
                           if five_stars_role in member.roles)
    activity = discord.Activity(type=discord.ActivityType.watching,
                                name=f"{total_five_stars} Five Stars Members")

    await bot.change_presence(status=default_status, activity=activity)
  print(f'{bot.user.name} ({bot.user.id}) is online!')

  # Start a reminder task
  reminder_task.start()
  check_expired_mutes.start()
  daily_reset.start()
  try:
    synced = await bot.tree.sync()
    print(f'Synced {len(synced)} Commands')
  except Exception as e:
    print(e)
    print('Worked')


async def temp_unban(user_id, unban_time):
  await asyncio.sleep(unban_time - time.time())
  user = bot.get_user(user_id)
  if user:
    guild = bot.get_guild(bleach_guild_id)
    mute_role = guild.get_role(mute_role_id)
    await user.remove_roles(mute_role)
  db_cursor.execute("DELETE FROM temp_bans WHERE user_id = ?", (user_id, ))
  db_conn.commit()


@bot.event
async def on_message(message):
  if message.author.bot:
    return

  if not message.author.bot:
    author_id = message.author.id
    connection = sqlite3.connect('afk_statuses.db')
    cursor = connection.cursor()
    cursor.execute(
        'SELECT message, afk_timestamp FROM AFKStatuses WHERE user_id = ?',
        (author_id, ))
    row = cursor.fetchone()

    if row:
      afk_message, afk_timestamp = row
      if afk_timestamp:
        afk_timestamp_str = f" - <t:{int(afk_timestamp)}:R>"
      else:
        afk_timestamp_str = ""
      afk_notification = await message.channel.send(
          f"{message.author.display_name} is no longer AFK: {afk_message}{afk_timestamp_str}"
      )

      cursor.execute('DELETE FROM AFKStatuses WHERE user_id = ?',
                     (author_id, ))
      connection.commit()
      connection.close()

      await asyncio.sleep(15)
      await afk_notification.delete()

    mentioned_users = message.mentions
    for user in mentioned_users:
      connection = sqlite3.connect('afk_statuses.db')
      cursor = connection.cursor()
      cursor.execute(
          'SELECT message, afk_timestamp FROM AFKStatuses WHERE user_id = ?',
          (user.id, ))
      row = cursor.fetchone()
      connection.close()

      if row:
        afk_message, afk_timestamp = row
        if afk_timestamp:
          afk_timestamp_str = f" - <t:{int(afk_timestamp)}:R>"
        else:
          afk_timestamp_str = ""
        await message.channel.send(
            f"{user.display_name} is currently AFK: {afk_message}{afk_timestamp_str}"
        )

  await bot.process_commands(message)


@bot.tree.command(name='ping')
async def ping(interaction: discord.Interaction):
  """Displays the bot's ping latency."""
  latency = round(bot.latency * 1000)  # Convert to milliseconds
  await interaction.response.send_message(f"Pong! Bot latency is {latency}ms.",
                                          ephemeral=False)


@bot.command()
async def daily(ctx):
  """Claim your daily reward."""
  user_id = ctx.author.id
  user_data = get_user_data(user_id)

  now = dt.now()
  last_daily = dt.strptime(
      user_data[4],
      '%Y-%m-%d %H:%M:%S.%f') if user_data[4] else now - timedelta(days=1)

  if now - last_daily >= timedelta(days=1):
    new_streak = user_data[3] + 1 if now - last_daily < timedelta(
        days=2) else 1

    # Calculate rewards
    exp_reward = new_streak * 10
    soul_coins_reward = new_streak * 5
    zanpakuto_tokens_reward = new_streak * 2

    hogyoku_shards_reward = new_streak if new_streak >= 7 else 0
    spirit_points_reward = new_streak if new_streak >= 7 else 0
    gikongan_pills_reward = new_streak if new_streak >= 7 else 0

    # Update database
    add_exp(user_id, exp_reward)
    c.execute(
        '''
            UPDATE users
            SET daily_streak = ?, last_daily = ?, soul_coins = soul_coins + ?, zanpakuto_tokens = zanpakuto_tokens + ?,
                hogyoku_shards = hogyoku_shards + ?, spirit_points = spirit_points + ?, gikongan_pills = gikongan_pills + ?
            WHERE user_id = ?
        ''', (new_streak, now, soul_coins_reward, zanpakuto_tokens_reward,
              hogyoku_shards_reward, spirit_points_reward,
              gikongan_pills_reward, user_id))
    conn.commit()

    await ctx.send(
        f'You have claimed your daily rewards! Streak: {new_streak} days')
  else:
    next_claim_time = last_daily + timedelta(days=1)
    next_claim_timestamp = int(next_claim_time.timestamp())
    await ctx.send(
        f'You have already claimed your daily rewards. Try again <t:{next_claim_timestamp}:R>!'
    )


@tasks.loop(hours=24)
async def daily_reset():
  now = dt.now()
  for guild in bot.guilds:
    for member in guild.members:
      if not member.bot:
        user_id = member.id
        user_data = get_user_data(user_id)
        if user_data:
          last_daily = dt.strptime(
              user_data[4],
              '%Y-%m-%d %H:%M:%S.%f') if user_data[4] else now - timedelta(
                  days=1)
          if now - last_daily >= timedelta(days=2):
            c.execute('UPDATE users SET daily_streak = 0 WHERE user_id = ?',
                      (user_id, ))
  conn.commit()


@bot.event
async def on_message(message):
  if message.author.bot:
    return

  user_id = message.author.id
  add_exp(user_id, 5)  # Earn exp for chatting

  await bot.process_commands(message)


@bot.command()
async def shop(ctx):
  """Display the shop menu."""
  user_id = ctx.author.id
  user_data = get_user_data(user_id)

  def check(m):
    return m.author == ctx.author and m.channel == ctx.channel

  await ctx.send(
      'Welcome to the shop! You can purchase the following items:\n1. Custom Role\n2. Exclusive Role\nPlease enter the number of the item you want to purchase:'
  )

  try:
    response = await bot.wait_for('message', check=check, timeout=30)
    choice = int(response.content)

    if choice == 1:
      await ctx.send('Enter the name for your custom role:')
      role_name = await bot.wait_for('message', check=check, timeout=30)
      await ctx.send(
          'Enter the color code for your custom role (e.g., #ff0000):')
      color_code = await bot.wait_for('message', check=check, timeout=30)

      color = discord.Color(int(color_code.content.strip('#'), 16))
      guild = ctx.guild
      custom_role = await guild.create_role(name=role_name.content,
                                            color=color)
      await ctx.author.add_roles(custom_role)
      await ctx.send(
          f'Custom role {role_name.content} created and assigned to you!')

    elif choice == 2:
      await ctx.send('Exclusive roles are not available yet.')
    else:
      await ctx.send('Invalid choice.')
  except Exception as e:
    await ctx.send('Shop session timed out or an error occurred.')


@bot.command()
async def level(ctx):
  """Display the user's level and exp."""
  user_id = ctx.author.id
  user_data = get_user_data(user_id)

  # Calculate the level and exp
  exp = user_data[1]
  level = int(0.07 * exp**0.5)
  exp_for_next_level = int(((level + 1) / 0.07)**2)
  exp_for_current_level = int((level / 0.07)**2)
  progress = exp - exp_for_current_level
  progress_total = exp_for_next_level - exp_for_current_level
  progress_percent = progress / progress_total

  # Create an image for the level card
  img = Image.new('RGB', (400, 200), color=(30, 30, 30))
  draw = ImageDraw.Draw(img)

  # Use a default font if arial.ttf is not available
  try:
    font = ImageFont.truetype("arial.ttf", 24)
  except OSError:
    font = ImageFont.load_default()

  # Draw user info on the image
  draw.text((20, 20),
            f"User: {ctx.author.display_name}",
            fill=(255, 255, 255),
            font=font)
  draw.text((20, 60), f"Level: {level}", fill=(255, 255, 255), font=font)
  draw.text((20, 100),
            f"EXP: {exp} / {exp_for_next_level}",
            fill=(255, 255, 255),
            font=font)

  # Draw the progress bar
  bar_width = 300
  bar_height = 30
  bar_x = 20
  bar_y = 140
  draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height],
                 fill=(50, 50, 50))
  draw.rectangle([
      bar_x, bar_y, bar_x + int(bar_width * progress_percent),
      bar_y + bar_height
  ],
                 fill=(255, 69, 0))

  # Convert the image to a Discord-compatible format
  with io.BytesIO() as image_binary:
    img.save(image_binary, 'PNG')
    image_binary.seek(0)
    await ctx.send(file=discord.File(fp=image_binary, filename='level.png'))


# Helper function to fetch user data
def get_user_data(user_id):
  c.execute("SELECT * FROM users WHERE user_id = ?", (user_id, ))
  result = c.fetchone()
  if not result:
    # If no data is found, initialize a new user with default values
    c.execute(
        "INSERT INTO users (user_id, exp, level, daily_streak, last_daily) VALUES (?, 0, 0, 0, NULL)",
        (user_id, ))
    conn.commit()
    return [user_id, 0, 0, 0, None]
  return result


@bot.command()
async def balance(ctx):
  """Display the user's balance."""
  user_id = ctx.author.id
  user_data = get_user_data(user_id)

  embed = discord.Embed(title="Your Balance", color=discord.Color.blue())
  embed.add_field(name="Soul Coins", value=user_data[5], inline=True)
  embed.add_field(name="Zanpakutō Tokens", value=user_data[6], inline=True)
  embed.add_field(name="Hogyoku Shards", value=user_data[7], inline=True)
  embed.add_field(name="Spirit Points", value=user_data[8], inline=True)
  embed.add_field(name="Gikongan Pills", value=user_data[9], inline=True)

  await ctx.send(embed=embed)


@bot.command(aliases=['PUNCH', 'Punch'])
@commands.check(human_authorized)
async def punch(ctx, user: discord.Member = None):
  """Challenges someone for a math duel."""
  if not user:
    await ctx.send("Bruh, mention the user, monke.")
    return

  if user.bot:
    await ctx.send("How low can your IQ be, monke?")
    return

  if user.guild_permissions.administrator:
    await ctx.send("You cannot punch your boss, filthy monke.")
    return

  if commander_role_id in [role.id for role in user.roles]:
    await ctx.send("Know your place, monke. That's your commander.")
    return

  author_hollow_role = discord.utils.get(ctx.author.roles, id=hollow_role_id)
  target_staff_role = discord.utils.get(user.roles, id=staff_role_id)

  if target_staff_role is not None and author_hollow_role is None:
    await ctx.send("Reach level 30 to target staff.")
    return

  if ctx.author.id == user.id:
    await ctx.send("You're already undergoing a challenge!")
    return

  if ctx.author.id in bot.challenges.values():
    await ctx.send("You're already undergoing a challenge!")
    return

  num1 = random.randint(1, 10)
  num2 = random.randint(1, 10)
  operator = random.choice(['+', '-', '*', '/'])
  question = f'What is {num1} {operator} {num2}?'

  await ctx.send(
      f'{ctx.author.mention} challenges {user.mention}:\n## {question}')

  bot.challenges[ctx.author.id] = user.id
  bot.challenges[user.id] = ctx.author.id

  def check(msg):
    # Check if the message is from the author or the mentioned user
    return msg.author == ctx.author or msg.author == user

  try:
    answer = await bot.wait_for('message', timeout=10.0, check=check)

    # Validate if the answer is a correct number
    try:
      if int(answer.content) == eval(f'{num1}{operator}{num2}'):
        await ctx.send('<:BleachKonSalute:1176232805617909981> Correct answer!'
                       )
      else:
        await ctx.send(
            f'<:L_:980785479635042364> {answer.author.mention} gave the wrong answer and lost their roles for 3 minutes.'
        )
        roles = answer.author.roles[1:]  # Exclude the @everyone role
        await answer.author.edit(roles=[])
        await asyncio.sleep(180)  # Wait for 3 minutes
        await answer.author.edit(roles=roles)  # Restore roles

    except ValueError:
      await ctx.send(
          f'<:L_:980785479635042364> {answer.author.mention} provided an invalid input and lost their roles for 3 minutes.'
      )
      roles = answer.author.roles[1:]  # Exclude the @everyone role
      await answer.author.edit(roles=[])
      await asyncio.sleep(180)  # Wait for 3 minutes
      await answer.author.edit(roles=roles)  # Restore roles

  except asyncio.TimeoutError:
    await ctx.send('⏲️ No one answered in time.')

  finally:
    # Clean up the challenge, regardless of outcome
    del bot.challenges[ctx.author.id]
    del bot.challenges[user.id]


bot.challenges = {}


# Command to kick a member
@bot.command(aliases=['KICK', 'slap', 'SLAP'])
@commands.check(is_authorized)
async def kick(ctx, user: discord.Member, *, reason="No reason provided"):
  if user.bot:
    await ctx.send("How low can your IQ be, monke?")
    return

  if user.guild_permissions.administrator:
    await ctx.send("You cannot kick your boss, filthy monke.")
    return

  if user == ctx.author:
    await ctx.send("You cannot kick yourself.")
    return

  if staff_role_id in [role.id for role in user.roles]:
    await ctx.send("You cannot kick a staff member.")
    return

  if ctx.author.guild_permissions.kick_members:
    await user.kick(reason=reason)
    await ctx.send(f"{user.name} has been kicked.")

    # Send DM message to the kicked user
    try:
      await user.send(
          f"You have been kicked from {ctx.guild.name} for the following reason: {reason}"
      )
    except discord.HTTPException:
      await ctx.send("Failed to send a DM to the kicked user.")

    await send_log_message(
        f"{user.name} has been kicked by {ctx.author.name}. Reason: {reason}")
  else:
    await ctx.send("You don't have permission to use this command.")


# Implement the reaction event for pagination
@bot.event
async def on_reaction_add(reaction, user):
  if user == bot.user or reaction.message.author != bot.user:
    return

  if reaction.emoji == "⬅️" or reaction.emoji == "➡️":
    page_text = reaction.message.embeds[0].title.split()[-1]
    current_page, num_pages = map(int, page_text[:-1].split("/"))

    if reaction.emoji == "⬅️":
      current_page = (current_page - 2) % num_pages + 1
    elif reaction.emoji == "➡️":
      current_page = current_page % num_pages + 1

    await update_pagination(reaction.message, current_page, num_pages, 0)
    await reaction.message.remove_reaction(reaction.emoji, user)


@bot.command()
@commands.cooldown(
    1, 86400,
    commands.BucketType.user)  # 1 use per 86400 seconds (24 hours) per user
async def report(ctx, user: discord.Member = None, *, reason: str = None):
  """Report a user for a specific reason to staff."""

  # Check if the user has either of the required roles (role IDs: lvl10_role_id and oken_role_id)
  required_report_role_ids = [lvl10_role_id, oken_role_id]
  required_report_role = [
      discord.utils.get(ctx.author.roles, id=role_id)
      for role_id in required_report_role_ids
  ]

  if not any(required_report_role):
    await ctx.send("Go reach level 10 first! <#679934725800198175>")
    return

  if not user:
    await ctx.send("Invalid user. Please mention a valid user.")
    return

  if not reason or not reason.strip():
    await ctx.send("What's the reason, monke?")
    return

  # Check if the user is not reporting themselves
  if user == ctx.author:
    await ctx.send("You cannot report yourself.")
    return

  if user.bot:
    await ctx.send("How low can your IQ be, monke?")
    return

  staff_role = discord.utils.get(ctx.guild.roles, id=staff_role_id)

  # Check if the user is not reporting a staff member
  if staff_role in user.roles:
    await ctx.send("You cannot report a staff member.")
    return

  # Get the report channel by ID
  report_channel = bot.get_channel(report_channel_id)

  if not report_channel:
    await ctx.send("The report channel could not be found.")
    return

  # Create an embed message
  embed = discord.Embed(title="Report", color=0xFF0000)
  embed.add_field(name="User", value=user.mention)
  embed.add_field(name="Reason", value=reason)

  # Include a jump link to the original message
  embed.add_field(name="Jump to Message",
                  value=f"[Jump]({ctx.message.jump_url})",
                  inline=False)

  # Remove the icon_url attribute
  embed.set_footer(
      text=f"Reported by {ctx.author.display_name} (ID: {ctx.author.id})")

  # Send the embed message to the report channel
  await report_channel.send(f"<@&{mod_role_id}>", embed=embed)

  # Send a confirmation message in the same channel where the command is executed
  await ctx.send(f"{user.mention} has been successfully reported.")


# Handle the cooldown error
@report.error
async def report_error(ctx, error):
  if isinstance(error, commands.CommandOnCooldown):
    retry_after = int(time.time() + error.retry_after)
    await ctx.send(f"Monke, chill out <t:{retry_after}:R>.")


@bot.command()
@commands.check(is_authorized)
async def mute(ctx, user: discord.Member, duration=None, *, reason):
  """[STAFF] Mutes user with reason."""
  if user.guild_permissions.administrator or staff_role_id in [
      role.id for role in user.roles
  ]:
    await ctx.send("You cannot mute this user.")
    return

  if duration is None:
    duration = "1w"  # Set the default mute duration to 1 week if not specified

  mute_duration = parse_time(duration)
  # Max mute duration: 1 week (604800 seconds)
  if mute_duration is None or mute_duration > 604800:
    await ctx.send("Invalid mute duration. Maximum duration is 1 week.")
    return

  mute_role = ctx.guild.get_role(mute_role_id)
  await user.add_roles(mute_role)
  await ctx.send(
      f"{user.mention} has been muted for {duration} due to: {reason}.")

  unmute_time = time.time() + mute_duration
  db_cursor.execute(
      "INSERT OR REPLACE INTO temp_bans (user_id, unmute_time) VALUES (?, ?)",
      (user.id, unmute_time))
  db_cursor.execute(
      "INSERT OR REPLACE INTO warnings (user_id, warning_count, mute_duration) VALUES (?, 0, ?)",
      (user.id, mute_duration))
  db_conn.commit()
  asyncio.create_task(temp_unban(user.id, unmute_time))

  log_channel = bot.get_channel(log_channel_id)
  await log_channel.send(
      f"{user.mention} has been muted for {duration} due to: {reason}.")


@bot.command()
@commands.check(is_authorized)
async def unmute(ctx, user: discord.Member, *, reason="No reason provided"):
  """[STAFF] Unmutes user with optional reason."""
  if user.guild_permissions.administrator or staff_role_id in [
      role.id for role in user.roles
  ]:
    await ctx.send("You cannot unmute this user.")
    return

  mute_role = ctx.guild.get_role(mute_role_id)
  await user.remove_roles(mute_role)
  db_cursor.execute("DELETE FROM temp_bans WHERE user_id = ?", (user.id, ))
  db_conn.commit()

  total_warnings = db_cursor.execute(
      "SELECT warning_count FROM warnings WHERE user_id = ?",
      (user.id, )).fetchone()
  if total_warnings:
    mute_duration = db_cursor.execute(
        "SELECT mute_duration FROM warnings WHERE user_id = ?",
        (user.id, )).fetchone()[0]
    if mute_duration is not None:
      db_cursor.execute(
          "UPDATE warnings SET mute_duration = NULL WHERE user_id = ?",
          (user.id, ))
      db_conn.commit()

  await ctx.send(f"{user.mention} has been unmuted due to: {reason}.")

  log_channel = bot.get_channel(log_channel_id)
  await log_channel.send(f"{user.mention} has been unmuted due to: {reason}.")


@bot.command()
@commands.check(is_authorized)
async def warn(ctx, user: discord.Member = None, *, reason=None):
  """[STAFF] Warns a user for a specified reason."""

  if user == bot.user:
    await ctx.send("You cannot warn a bot.")
    return

  if user.guild_permissions.administrator or staff_role_id in [
      role.id for role in user.roles
  ]:
    await ctx.send("You cannot warn this user.")
    return

  if user is None:
    await ctx.send("Who are you trying to warn?")
    return

  if reason is None:
    await ctx.send("Please provide the reason, monke.")
    return

  db_cursor.execute(
      "INSERT OR IGNORE INTO warnings (user_id, warning_count, mute_duration) VALUES (?, 0, NULL)",
      (user.id, ))
  db_cursor.execute(
      "UPDATE warnings SET warning_count = warning_count + 1 WHERE user_id = ?",
      (user.id, ))
  db_cursor.execute(
      "INSERT INTO user_warnings (user_id, reason) VALUES (?, ?)",
      (user.id, reason))
  db_conn.commit()

  total_warnings = db_cursor.execute(
      "SELECT warning_count FROM warnings WHERE user_id = ?",
      (user.id, )).fetchone()[0]

  if total_warnings >= 10:
    await ctx.send(
        f"{user.mention} has received their 10th warning and is now permanently banned."
    )
    await user.ban(reason=f"Reached 10 warnings: {reason}")
    await user.send(
        f"You have been permanently banned due to reaching 10 warnings: {reason}"
    )
  elif total_warnings == 5:
    mute_role = ctx.guild.get_role(mute_role_id)
    await user.add_roles(mute_role)
    await ctx.send(
        f"{user.mention} has received their 5th warning and is now muted for 1 hour."
    )
    await user.send(
        f"You have been warned and muted for 1 hour due to reaching 5 warnings: {reason}."
    )

    unban_time = time.time() + 3600
    db_cursor.execute(
        "INSERT OR REPLACE INTO temp_bans (user_id, unmute_time) VALUES (?, ?)",
        (user.id, unban_time))
    db_conn.commit()
    asyncio.create_task(temp_unban(user.id, unban_time))
  else:
    await ctx.send(
        f"{user.mention} has been warned for: {reason} and is now muted for 1 hour."
    )
    mute_role = ctx.guild.get_role(mute_role_id)
    await user.add_roles(mute_role)

  log_channel = bot.get_channel(log_channel_id)
  await log_channel.send(
      f"{user.mention} has been warned for: {reason} (Total Warnings: {total_warnings})"
  )


@bot.command()
@commands.check(is_authorized)
async def warnings(ctx, user: discord.Member = None):
  """[STAFF] Displays user's total warnings."""
  total_warnings = db_cursor.execute(
      "SELECT warning_count FROM warnings WHERE user_id = ?",
      (user.id, )).fetchone()

  if user is None:
    user = ctx.author

  if not total_warnings:
    await ctx.send(f"{user.mention} has no warnings.")
    return

  total_warnings = total_warnings[0]
  warnings = db_cursor.execute(
      "SELECT reason FROM user_warnings WHERE user_id = ?",
      (user.id, )).fetchall()

  if not warnings:
    await ctx.send(f"{user.mention} has no warnings.")
    return

  warnings_list = "\n".join(f"{i+1}. {warning[0]}"
                            for i, warning in enumerate(warnings))
  await ctx.send(
      f"{user.mention} has {total_warnings} warning(s):\n{warnings_list}")


@bot.command()
@commands.check(can_remove_warn)
async def removewarn(ctx, user: discord.Member, warning_num: int, *, reason):
  """[STAFF] Remove user's warn."""
  if user.guild_permissions.administrator or commander_role_id in [
      role.id for role in user.roles
  ]:
    await ctx.send("You cannot remove warnings from this user.")
    return

  warnings = db_cursor.execute(
      "SELECT reason FROM user_warnings WHERE user_id = ?",
      (user.id, )).fetchall()

  if not warnings:
    await ctx.send(f"{user.mention} has no warnings to remove.")
    return

  if warning_num < 1 or warning_num > len(warnings):
    await ctx.send(
        "Invalid warning number. Please provide a valid warning number to remove."
    )
    return

  warning_to_remove = warnings[warning_num - 1][0]
  db_cursor.execute(
      "DELETE FROM user_warnings WHERE user_id = ? AND reason = ?",
      (user.id, warning_to_remove))
  db_cursor.execute(
      "UPDATE warnings SET warning_count = warning_count - 1 WHERE user_id = ?",
      (user.id, ))
  db_conn.commit()

  await ctx.send(
      f"Warning number {warning_num} has been removed for {user.mention}: {warning_to_remove}."
  )

  log_channel = bot.get_channel(log_channel_id)
  await log_channel.send(
      f"Warning number {warning_num} has been removed for {user.mention}: {warning_to_remove}. Reason: {reason}"
  )

  user_dm = await user.create_dm()
  await user_dm.send(
      f"Your warning number {warning_num} has been removed by {ctx.author.mention}. Reason: {reason}"
  )


@bot.command()
async def afk(ctx, *, message: str = "AFK"):
  """Set your AFK status with an optional message."""
  user_id = ctx.author.id

  # Remove the existing AFK status from the database
  connection = sqlite3.connect('afk_statuses.db')
  cursor = connection.cursor()
  cursor.execute('DELETE FROM AFKStatuses WHERE user_id = ?', (user_id, ))
  connection.commit()
  connection.close()

  # Store the current afk_timestamp as a Unix afk_timestamp
  afk_timestamp = time.time()

  # Store the AFK status in the database
  connection = sqlite3.connect('afk_statuses.db')
  cursor = connection.cursor()
  cursor.execute(
      'INSERT INTO AFKStatuses (user_id, message, afk_timestamp) VALUES (?, ?, ?)',
      (user_id, message, afk_timestamp))
  connection.commit()
  connection.close()

  await ctx.send(
      f"{ctx.author.mention} is now AFK: {message} - <t:{int(afk_timestamp)}:R>"
  )


@bot.command()
async def unafk(ctx, member: discord.Member):
  """[STAFF] Clear the AFK status of a user."""

  # Check if the command sender has the staff role
  staff_role = discord.utils.get(ctx.guild.roles, id=staff_role_id)
  if staff_role and staff_role in ctx.author.roles:
    user_id = member.id

    # Remove the AFK status from the database
    connection = sqlite3.connect('afk_statuses.db')
    cursor = connection.cursor()
    cursor.execute('DELETE FROM AFKStatuses WHERE user_id = ?', (user_id, ))
    connection.commit()
    connection.close()

    await ctx.send(
        f"{member.mention}'s AFK status has been cleared by {ctx.author.mention}."
    )
  else:
    await ctx.send(
        f"{ctx.author.mention}, you do not have permission to use this command."
    )


@bot.command(aliases=['SNIPE', 'Snipe'])
async def snipe(ctx):
  """Displays last deleted message in a channel."""

  required_snipe_role_ids = [lvl10_role_id, oken_role_id]
  required_snipe_role = [
      discord.utils.get(ctx.author.roles, id=role_id)
      for role_id in required_snipe_role_ids
  ]

  if not any(required_snipe_role):
    await ctx.send("Go reach level 10 first! <#679934725800198175>")
    return

  try:
    deleted_message = deleted_messages.get(ctx.channel.id)

    if deleted_message:
      author = deleted_message.author
      content = deleted_message.content
      attachments = deleted_message.attachments

      # Get the message to which the deleted message was a reply
      replied_to_message = await ctx.channel.fetch_message(
          deleted_message.reference.message_id
      ) if deleted_message.reference else None

      embed = discord.Embed(title=f'Message Sniped by {author.display_name}',
                            color=discord.Color.blurple())

      if content:
        embed.description = content

      for attachment in attachments:
        if attachment.url.endswith(
            ('.png', '.jpg', '.jpeg', '.gif', '.mp4', '.webm', '.webp', '.txt',
             '.apng', '.mp3')):
          embed.set_image(url=attachment.url)

      if attachments:
        download_links = '\n'.join([
            f"[Download Attachment {i+1}]({attachment.url})"
            for i, attachment in enumerate(attachments)
        ])
        embed.add_field(name="Attachments", value=download_links)

      if replied_to_message:
        embed.add_field(
            name="Replied to",
            value=f"[Jump to Replied Message]({replied_to_message.jump_url})")

      await ctx.send(embed=embed)
    else:
      await ctx.send("No deleted messages to snipe!")
  except KeyError:
    await ctx.send("No deleted messages to snipe!")


# Event: Store deleted messages with attachments in the global dictionary
@bot.event
async def on_message_delete(message):
  if not message.author.bot:  # Ignore messages from bots
    deleted_messages[message.channel.id] = message


@bot.command(aliases=['ESNIPE', 'Esnipe', 'editsnipe', 'Editsnipe'])
async def esnipe(ctx):
  """Displays last edited message in a channel."""

  required_esnipe_role_ids = [lvl10_role_id, oken_role_id]
  required_esnipe_role = [
      discord.utils.get(ctx.author.roles, id=role_id)
      for role_id in required_esnipe_role_ids
  ]

  if not any(required_esnipe_role):
    await ctx.send("Go reach level 10 first! <#679934725800198175>")
    return

  edited_message = bot.edited_messages.get(ctx.channel.id)
  if edited_message:
    author = edited_message['author']
    content_before_edit = edited_message['content_before_edit']
    content_after_edit = edited_message['content_after_edit']
    jump_link = f"[Jump to Message](https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{edited_message['id']})"

    embed = discord.Embed(
        title=f'Message Edited by {author.display_name}',
        description=
        f'Before Edit: {content_before_edit}\nAfter Edit: {content_after_edit}\n\n{jump_link}',
        color=discord.Color.gold())

    # Check if the command was a reply
    if ctx.message.reference:
      replied_message = await ctx.channel.fetch_message(
          ctx.message.reference.message_id)
      if replied_message:
        embed.add_field(
            name="In Response to",
            value=f"[Jump to Replied Message]({replied_message.jump_url})")

    await ctx.send(embed=embed)
  else:
    await ctx.send("No edited messages to snipe!")


@bot.event
async def on_message_edit(before, after):
  if not before.author.bot:  # Ignore messages from bots
    bot.edited_messages[before.channel.id] = {
        "author": before.author,
        "content_before_edit": before.content,
        "content_after_edit": after.content,
        "timestamp": after.created_at,
        "id": after.id
    }


bot.edited_messages = {}
deleted_messages = {}


@bot.command(aliases=['bn', 'ban', 'Banner', 'BANNER'])
@user_cooldown(1,
               3,
               type=commands.BucketType.user,
               notify_message=
               "Please wait {0:.2f} seconds before using this command again.")
async def banner(ctx, user: Union[discord.Member, str] = None):
  """Displays user's banner."""
  if isinstance(user, str):
    try:
      user = await commands.MemberConverter().convert(ctx, user)
    except commands.MemberNotFound:
      await ctx.send("User not found.")
      return

  if user is None:
    user = ctx.author

  embed = discord.Embed(title=f"{user.display_name} Banner", color=user.color)

  if isinstance(user, discord.Member):
    # Fetch the user to access banner information
    try:
      user = await bot.fetch_user(user.id)
    except discord.NotFound:
      await ctx.send("User not found.")
      return

  if isinstance(user, discord.Member) and ctx.guild and user.banner:
    # Check if the guild has a Guild Member Banner
    if user.banner:
      guild_banner_url = f"https://cdn.discordapp.com/guilds/{ctx.guild.id}/users/{user.id}/banners/{user.banner}"
      embed.set_image(url=guild_banner_url)
      embed.set_footer(text=f"Requested by {ctx.author.name}")
      try:
        await ctx.send(embed=embed)
        return
      except discord.HTTPException:
        await ctx.send(
            "Error: Failed to send the embed message. Please check the permissions and try again."
        )

  # Check if the user has a User Banner
  if isinstance(user, discord.User) and user.banner:
    banner_url = user.banner.url
    embed.set_image(url=banner_url)
    embed.set_footer(text=f"Requested by {ctx.author.name}")
    try:
      await ctx.send(embed=embed)
    except discord.HTTPException:
      await ctx.send(
          "Error: Failed to send the embed message. Please check the permissions and try again."
      )
  else:
    await ctx.send("The user doesn't have a banner set.")


@bot.command()
@commands.cooldown(1, 5, commands.BucketType.user)
async def get(ctx, option: str, user: discord.Member = None):
  """Displays user's avatar or banner."""
  # Define the aliases for options
  option_aliases = {
      "banner": "banner",
      "ban": "banner",
      "avatar": "avatar",
      "av": "avatar"
  }

  # Check if the option is valid
  if option_aliases.get(option) is None:
    await ctx.send("Invalid option. Use 'banner' or 'avatar'.")
    return

  if user is None:
    user = ctx.author

  # Fetch the mentioned member's banner or server avatar using user ID
  try:
    user = await bot.fetch_user(user.id)
  except discord.NotFound:
    await ctx.send("User not found.")
    return

  user_banner = user.banner.url if option_aliases[option] == "banner" else None
  user_avatar = user.avatar.url if option_aliases[option] == "avatar" else None

  # Create an embed message based on the option
  if option_aliases[option] == "banner":
    embed = discord.Embed(
        title=f"{user.display_name}'s Banner",
        color=ctx.author.color,  # You can use ctx.author's color
    )
    embed.set_image(url=user_banner)
  elif option_aliases[option] == "avatar":
    embed = discord.Embed(
        title=f"{user.display_name}'s Avatar",
        color=user.color if isinstance(user, discord.Member) else None,
    )
    embed.set_image(url=user_avatar)

  embed.set_author(
      name=f"{user.name}",
      icon_url=user_avatar,
  )
  await ctx.send(embed=embed)


@get.error
async def get_error(ctx, error):
  if isinstance(error, commands.CommandOnCooldown):
    await ctx.send(
        f"This command is on cooldown. Please try again in {error.retry_after:.2f} seconds."
    )
  elif isinstance(error, commands.BadArgument):
    await ctx.send(
        "Invalid user argument. Mention a valid user or use 'h.get option' without mentioning a user."
    )
  elif isinstance(error, discord.Forbidden):
    await ctx.send(f"I don't have permission to fetch the user's information.")
  elif isinstance(error, discord.NotFound):
    await ctx.send(f"{ctx.author.display_name} does not have a profile banner."
                   )


@bot.tree.command(name='ctime')
async def currenttime(interaction: discord.Interaction):
  """Get the current server time of Hogyoku."""

  view = CtimeButton()

  embed = discord.Embed(title="Hogyoku's Server Time",
                        description="Please choose the time format.",
                        color=discord.Color.blue())

  await interaction.response.send_message(embed=embed,
                                          view=view,
                                          ephemeral=True)


@bot.tree.command(name='staffrolesmenu')
async def staffrolesmenu(interaction: discord.Interaction):
  """[STAFF] Opt additional staff roles."""
  staff_role = discord.utils.get(interaction.guild.roles, id=staff_role_id)
  if staff_role not in interaction.user.roles:
    await interaction.response.send_message(
        f"You do not have permission to use this command.", ephemeral=True)
    return
  views = SelectView()
  await interaction.response.send_message(f"The choice is in your hands.",
                                          ephemeral=True,
                                          view=views)


@bot.tree.command(name='say')
@app_commands.describe(
    text="The text you want the bot to send.",
    attachment="An optional attachment to include.",
    anonymous="An optional flag to send the message anonymously.")
async def say(interaction: discord.Interaction,
              text: str,
              attachment: discord.Attachment = None,
              anonymous: bool = False):
  """Repeats what you say in an embed message."""

  guild = interaction.guild
  if guild is None:
    return

  member = interaction.user
  if member is None:
    return

  vollstandig_role = guild.get_role(vollstandig_role_id)
  commander_role = guild.get_role(commander_role_id)
  administrator_permissions = discord.Permissions(administrator=True)

  has_vollstandig_role = vollstandig_role in member.roles
  has_commander_role = commander_role in member.roles
  has_admin_permissions = member.guild_permissions & administrator_permissions

  if not (has_vollstandig_role or has_commander_role or has_admin_permissions):
    await interaction.response.send_message(
        "You do not have permission to use this command.", ephemeral=True)
    return

  embed = discord.Embed(description=text)

  if attachment:
    embed.set_image(url=attachment.url)

  if not anonymous:
    embed.set_author(name=member.display_name, icon_url=member.avatar.url)

  await interaction.response.send_message("Message sent ✅", ephemeral=True)
  await interaction.channel.send(embed=embed)


@bot.tree.command(name='help')
async def help_command(interaction: discord.Interaction):
  """Shows my commands list."""
  embed = discord.Embed(
      title="Welcome to my help page!",
      description=
      "Click the button below! <a:BleachAizenLetHimCook:1138618255381119067>\n\n"
      + random.choice(bleach_quotes.bleach_quotes))
  views = HelpButton()
  views.bot = bot
  random_wallpaper_url = random.choice(bleach_wallpapers.wallpaper_urls)
  embed.set_image(url=random_wallpaper_url)
  await interaction.response.send_message(embed=embed,
                                          view=views,
                                          ephemeral=True)


# Replace the rest of the commands as needed

# Run the main bot
bot.run(YOUR_BOT_TOKEN)
