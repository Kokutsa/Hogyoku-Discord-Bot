import discord
from discord import app_commands
import discord.ext.commands
from discord.ext import commands, tasks
from discord.ext.commands import cooldown, BucketType

import asyncio
from datetime import datetime
import datetime
import random
import requests
import sqlite3
import time
import re
from geopy.geocoders import Nominatim

from menu_roles import SelectView
from help_menu import HelpButton
from ctime_menu import CtimeButton
import bleach_wallpapers
import bleach_quotes
from config import prefix, default_status, YOUR_BOT_TOKEN, booster_role_ids_to_remove, bleach_guild_name, bleach_guild_id, owner_role_name, owner_role_id, commander_role_name, commander_role_id, oken_role_name, oken_role_id, mod_role_name, mod_role_id, staff_role_name, staff_role_id, mute_role_name, mute_role_id, lvl10_role_name, lvl10_role_id, bleach_booster_role_name, bleach_booster_role_id, active_mod_role_name, active_mod_role_id, inactive_mod_role_name, inactive_mod_role_id, five_stars_role_name, five_stars_role_id, log_channel_name, log_channel_id, attendance_channel_name, attendance_channel_id
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

# Define the attendance_data attribute in your bot instance
bot.attendance_data = []

# Set the number of fields to display per page
fields_per_page = 10


# Function to create the 'attendance_data' table if it doesn't exist
def create_attendance_table():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance_data
        (user_id INTEGER, attendance_date TEXT, attendance_timestamp INTEGER)
    ''')
    conn.commit()


# Create the 'attendance_data' table if it doesn't exist
create_attendance_table()


# Function to check if a user has already submitted attendance for today
def has_attendance_for_today(user_id):
    current_date_gmt7 = time.strftime("%Y-%m-%d",
                                      time.gmtime(time.time() + 25200))
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute(
        "SELECT attendance_timestamp FROM attendance_data WHERE user_id=? AND attendance_date=?",
        (user_id, current_date_gmt7))
    result = c.fetchone()
    conn.close()
    return result


# Function to delete the previous attendance_timestamp of the user
def delete_previous_attendance_timestamp(user_id):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute(
        "DELETE FROM attendance_data WHERE user_id=? AND attendance_date!=?",
        (user_id, time.strftime("%Y-%m-%d", time.gmtime(time.time() + 25200))))
    conn.commit()
    conn.close()


# Create or connect to the SQLite database for cooldown data
conn = sqlite3.connect('attendance.db')
c = conn.cursor()


# Function to update the last reset time for a user in the database
def update_last_reset(user_id, last_reset):
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO attendance_data (user_id, attendance_date, attendance_timestamp) VALUES (?, ?, ?)",
        (user_id, last_reset, 0))
    conn.commit()
    conn.close()


# Custom check function for cooldown
def reset_per_gmt7_day():

    def predicate(ctx):
        user_id = ctx.author.id
        current_date_gmt7 = time.strftime("%Y-%m-%d",
                                          time.gmtime(time.time() + 25200))
        conn = sqlite3.connect('attendance.db')
        c = conn.cursor()
        c.execute("SELECT attendance_date FROM attendance_data WHERE user_id = ?",
                  (user_id, ))
        row = c.fetchone()
        conn.close()

        if row is None or row[0] != current_date_gmt7:
            last_reset = current_date_gmt7
            update_last_reset(user_id, last_reset)
            return True

        raise commands.CommandOnCooldown(None, 86400,
                                         type=None)  # 86400 seconds in a day

    return commands.check(predicate)


# Function to fetch the attendance data with unique user IDs
def fetch_attendance_data():
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute(
        "SELECT DISTINCT user_id, attendance_date, attendance_timestamp FROM attendance_data ORDER BY attendance_timestamp ASC"
    )
    attendance_data = c.fetchall()
    conn.close()
    return attendance_data


# Implement a timeout for emoji reactions
async def wait_for_reaction_timeout(message, check=None, timeout=30):
    try:
        reaction, user = await bot.wait_for(
            'reaction_add',
            timeout=timeout,
            check=lambda reaction, user: check(
                reaction, user) and user != bot.user
        )
        return reaction, user
    except asyncio.TimeoutError:
        await message.clear_reactions()
        return None, None


# New function to handle pagination logic
async def update_pagination(message, page, num_pages, last_page_size):
    start = (page - 1) * fields_per_page
    end = min(start + fields_per_page, len(bot.attendance_data))
    page_data = bot.attendance_data[start:end]

    embed = generate_embed(page_data, page, num_pages, last_page_size)
    await message.edit(embed=embed)


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
    current_time = time.strftime(
        "%I:%M:%S %p", time.gmtime(time.time() + 25200))
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
            db_cursor.execute(
                "DELETE FROM temp_bans WHERE user_id = ?", (user_id, ))
            db_conn.commit()


# Connect to the SQLite database and create a reminders table
conn = sqlite3.connect('reminders.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS reminders (
                user_id INT,
                message TEXT,
                reminder_time INT
            )''')
conn.commit()


@tasks.loop(seconds=60)  # Check for reminders every 60 seconds
async def reminder_task():
    current_time = int(datetime.datetime.now().timestamp())
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


@bot.tree.command(name='remind')
@app_commands.describe(duration="Duration in minutes.",
                       message="I will remind you in DMs.")
async def remind(interaction: discord.Interaction, duration: int, *,
                 message: str):
    """Set a reminder for yourself with a specified duration in minutes."""
    user = interaction.user
    # Check the number of reminders the user has
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

        await interaction.response.send_message(
            f"Reminder set for yourself in {duration} minutes: {message}")


@bot.tree.command(name='reminders')
async def view_reminders(interaction: discord.Interaction):
    """View your stored reminders."""
    user = interaction.user
    c.execute("SELECT message, reminder_time FROM reminders WHERE user_id = ?",
              (user.id, ))
    stored_reminders = c.fetchall()

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
                f"{message.author.display_name} is no longer AFK: {
                    afk_message}{afk_timestamp_str}"
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
                    f"{user.display_name} is currently AFK: {
                        afk_message}{afk_timestamp_str}"
                )

    await bot.process_commands(message)


@bot.tree.command(name='ping')
async def ping(interaction: discord.Interaction):
    """Displays the bot's ping latency."""
    latency = round(bot.latency * 1000)  # Convert to milliseconds
    await interaction.response.send_message(f"Pong! Bot latency is {latency}ms.",
                                            ephemeral=False)


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
@commands.check(is_authorized)
async def attendancelist(ctx, page: int = 1):
    """[STAFF] Displays the staff attendance list."""
    # Clear the bot's attendance_data attribute before updating it
    bot.attendance_data = []

    # Fetch attendance data from the database with unique user IDs
    bot.attendance_data = fetch_attendance_data()

    # Calculate the total number of pages and the last page's size
    num_pages, last_page_size = divmod(
        len(bot.attendance_data), fields_per_page)

    # Ensure the provided page is within the valid range
    if page < 1:
        page = 1
    elif page > num_pages + (1 if last_page_size > 0 else 0):
        page = num_pages + (1 if last_page_size > 0 else 0)

    # Calculate the start and end indices for the current page
    start = (page - 1) * fields_per_page
    end = min(start + fields_per_page, len(bot.attendance_data))

    # Create an embed for the current page
    embed = generate_embed(bot.attendance_data[start:end], page, num_pages,
                           last_page_size)

    # Send the attendance list with pagination
    message = await ctx.send(embed=embed)

    # Add reactions for pagination
    if num_pages + (1 if last_page_size > 0 else 0) > 1:
        await message.add_reaction("⬅️")  # Previous page
        await message.add_reaction("➡️")  # Next page

    # Wait for a reaction with a timeout of 120 seconds
    reaction, user = await wait_for_reaction_timeout(
        message, lambda r, u: u == ctx.author)

    # Handle the reaction if not None
    if reaction:
        await update_pagination(message, page, num_pages, last_page_size)
    else:
        timeout_message = await ctx.send("Reaction timeout. Attendance list closed.")
        await asyncio.sleep(10)  # Delay for 10 seconds
        await timeout_message.delete()


# Modify the generate_embed function to accept last_page_size as an argument
def generate_embed(page_data, page, num_pages, last_page_size):
    if last_page_size == 0 and page == num_pages:
        num_pages -= 1
    embed = discord.Embed(
        title=f"Attendance List (Page {page}/{num_pages + 1})")
    displayed_users = set()  # Create a set to store displayed users
    for user_id, date, attendance_timestamp in page_data:
        user = bot.get_user(user_id)  # Use bot.get_user to retrieve users
        if user and user not in displayed_users:
            # Convert attendance_timestamp to human-readable date and time
            attendance_timestamp_str = f"<t:{attendance_timestamp}:R>"
            embed.add_field(
                # Display ID alongside name
                name=f"{user.display_name} ({user_id})",
                value=f"{date} {attendance_timestamp_str}",
                inline=False,
            )
            # Add the user to the set of displayed users
            displayed_users.add(user)
    return embed


@bot.command(aliases=[
    'ATTENDANCE', 'Attendance', 'ATtendance', 'ATTEndance', 'ATTENDance',
    'ATTENdance', 'ATTENDAnce', 'ATTENDANce', 'ATTENDANCe', 'aTtendance'
])
@commands.check(is_authorized)
@reset_per_gmt7_day()
async def attendance(ctx):
    """[STAFF] Daily attendance command."""

    # Check if the command is used in the allowed channel
    if ctx.channel.id != attendance_channel_id:
        await ctx.author.send(
            f"`attendance` can only be executed in <#{attendance_channel_id}>.")
        return

    # Get the current GMT+7 date and time
    current_date_gmt7 = time.strftime("%Y-%m-%d",
                                      time.gmtime(time.time() + 25200))
    current_time = get_current_time_gmt7()

    # Delete the previous attendance_timestamp of the user
    delete_previous_attendance_timestamp(ctx.author.id)

    # Check if the user has already submitted attendance for today or in the past
    existing_attendance_timestamp = has_attendance_for_today(ctx.author.id)

    if existing_attendance_timestamp:
        # User has submitted attendance for today or in the past; update the attendance_timestamp and attendance date
        conn = sqlite3.connect('attendance.db')
        c = conn.cursor()
        c.execute(
            "UPDATE attendance_data SET attendance_timestamp=?, attendance_date=? WHERE user_id=?",
            (int(time.time()), current_date_gmt7, ctx.author.id))
        await ctx.send(
            f"✅ Successfully updated your attendance for {current_date_gmt7}.")
        conn.commit()
        conn.close()
    else:
        # User hasn't submitted attendance for today or in the past; insert a new entry
        conn = sqlite3.connect('attendance.db')
        c = conn.cursor()
        c.execute(
            "INSERT INTO attendance_data (user_id, attendance_date, attendance_timestamp) VALUES (?, ?, ?)",
            (ctx.author.id, current_date_gmt7, int(time.time())))
        await ctx.send(
            f"✅ Successfully recorded your attendance for {current_date_gmt7}.")
        conn.commit()
        conn.close()


# Attach the custom cooldown to the command
@attendance.error
async def attendance_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            "⏰ You have already done your attendance today. Wait for a new GMT+7 day.\nCheck </ctime:1167098614766641163> to view the current GMT+7 time."
        )


@bot.command()
@commands.check(oken_authorized)
async def attendanceremove(ctx, target: discord.Member):
    """[OKEN] Removes user's attendance record."""
    # Check if the user has the oken_role
    oken_role = discord.utils.get(ctx.guild.roles, id=oken_role_id)
    if oken_role not in ctx.author.roles:
        await ctx.send("You do not have permission to use this command.")
        return

    # Remove the target user from the attendance database
    conn = sqlite3.connect('attendance.db')
    c = conn.cursor()
    c.execute("DELETE FROM attendance_data WHERE user_id = ?", (target.id, ))
    conn.commit()
    conn.close()

    await ctx.send(
        f"✅ Removed {
            target.display_name} ({target.id}) from the attendance records."
    )


@bot.command()
@commands.check(oken_authorized)
async def attendancereset(ctx):
    """[OKEN] Resets attendance data."""
    # Check if the user has the 'Staff' role
    oken_role = discord.utils.get(ctx.guild.roles, id=oken_role_id)
    if oken_role not in ctx.author.roles:
        await ctx.send("You do not have permission to use this command.")
        return

    # Confirm reset with the user
    await ctx.send("Are you sure you want to reset the attendance data? (yes/no)"
                   )

    def check(response):
        return response.author == ctx.author and response.content.lower() in [
            "yes", "no"
        ]

    try:
        response = await bot.wait_for("message", check=check, timeout=30)

        if response.content.lower() == "yes":
            # Reset the attendance database
            conn = sqlite3.connect('attendance.db')
            c = conn.cursor()
            c.execute("DELETE FROM attendance_data")
            conn.commit()
            await ctx.send("✅ Attendance data has been reset.")
            conn.close()
        else:
            await ctx.send("Reset request canceled.")
    except asyncio.TimeoutError:
        await ctx.send("Reset request timed out")


@bot.command()
async def report(ctx, user: discord.User, *, reason: str):
    """Report a user for a specific reason to staff."""
    # Check if the user has either the required roles (role IDs: lvl10_role_id and token_role_id)
    required_report_role_ids = [lvl10_role_id, oken_role_id]
    required_report_role = [
        discord.utils.get(ctx.author.roles, id=role_id)
        for role_id in required_report_role_ids
    ]

    if required_report_role is None:
        await ctx.send("You have not reached Level 10 to use this command.")
        return

    # Get the report channel by ID
    report_channel_id = 729453947173077032
    report_channel = bot.get_channel(report_channel_id)

    if report_channel is None:
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
    embed.set_footer(text=f"Reported by {ctx.author.display_name}")

    # Send the embed message to the report channel
    await report_channel.send(f"<@&{mod_role_id}>", embed=embed)

    # Send a confirmation message in the same channel where the command is executed
    await ctx.send(f"{user.mention} has been successfully reported.")


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
async def warn(ctx, user: discord.Member, *, reason):
    """[STAFF] Warns a user for a specified reason."""
    if user.guild_permissions.administrator or staff_role_id in [
        role.id for role in user.roles
    ]:
        await ctx.send("You cannot warn this user.")
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
            f"You have been permanently banned due to reaching 10 warnings: {
                reason}"
        )
    elif total_warnings == 5:
        mute_role = ctx.guild.get_role(mute_role_id)
        await user.add_roles(mute_role)
        await ctx.send(
            f"{user.mention} has received their 5th warning and is now muted for 1 hour."
        )
        await user.send(
            f"You have been warned and muted for 1 hour due to reaching 5 warnings: {
                reason}."
        )

        unban_time = time.time() + 3600
        db_cursor.execute(
            "INSERT OR REPLACE INTO temp_bans (user_id, unmute_time) VALUES (?, ?)",
            (user.id, unban_time))
        db_conn.commit()
        asyncio.create_task(temp_unban(user.id, unban_time))
    else:
        await ctx.send(
            f"{user.mention} has been warned for: {
                reason} and is now muted for 1 hour."
        )
        mute_role = ctx.guild.get_role(mute_role_id)
        await user.add_roles(mute_role)

    log_channel = bot.get_channel(log_channel_id)
    await log_channel.send(
        f"{user.mention} has been warned for: {
            reason} (Total Warnings: {total_warnings})"
    )


@bot.command()
@commands.check(is_authorized)
async def warnings(ctx, user: discord.Member):
    """[STAFF] Displays user's total warnings."""
    total_warnings = db_cursor.execute(
        "SELECT warning_count FROM warnings WHERE user_id = ?",
        (user.id, )).fetchone()

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
        f"Warning number {warning_num} has been removed for {
            user.mention}: {warning_to_remove}."
    )

    log_channel = bot.get_channel(log_channel_id)
    await log_channel.send(
        f"Warning number {warning_num} has been removed for {
            user.mention}: {warning_to_remove}. Reason: {reason}"
    )

    user_dm = await user.create_dm()
    await user_dm.send(
        f"Your warning number {warning_num} has been removed by {
            ctx.author.mention}. Reason: {reason}"
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
        f"{ctx.author.mention} is now AFK: {message} - <t:{int(afk_timestamp)}:R>")


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
        cursor.execute(
            'DELETE FROM AFKStatuses WHERE user_id = ?', (user_id, ))
        connection.commit()
        connection.close()

        await ctx.send(
            f"{member.mention}'s AFK status has been cleared by {
                ctx.author.mention}."
        )
    else:
        await ctx.send(
            f"{ctx.author.mention}, you do not have permission to use this command."
        )


@bot.command()
@commands.has_any_role(lvl10_role_id,
                       oken_role_id)  # Replace with your role ID
async def snipe(ctx):
    """Displays last deleted message in a channel."""
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


@bot.command()
@commands.has_any_role(lvl10_role_id,
                       oken_role_id)  # Replace with your role ID
async def esnipe(ctx):
    """Displays last edited message in a channel."""
    edited_message = bot.edited_messages.get(ctx.channel.id)
    if edited_message:
        author = edited_message['author']
        content_before_edit = edited_message['content_before_edit']
        content_after_edit = edited_message['content_after_edit']
        jump_link = f"[Jump to Message](https://discord.com/channels/{ctx.guild.id}/{
            ctx.channel.id}/{edited_message['id']})"

        embed = discord.Embed(
            title=f'Message Edited by {author.display_name}',
            description=f'Before Edit: {content_before_edit}\nAfter Edit: {
                content_after_edit}\n\n{jump_link}',
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


# Define the response for users without the specified role
@snipe.error
@esnipe.error
async def command_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send(
            "Reach level 10 to unlock this feature <#679934725800198175>.")


bot.edited_messages = {}
deleted_messages = {}


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
            f"This command is on cooldown. Please try again in {
                error.retry_after:.2f} seconds."
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


@bot.command()
async def status(ctx, status_type):
    """[OKEN] Set the bot status."""
    oken_role = discord.utils.get(ctx.guild.roles, name=oken_role_name)

    if oken_role and oken_role in ctx.author.roles:
        global default_status

        if status_type.lower() == "online":
            default_status = discord.Status.online
        elif status_type.lower() == "dnd":
            default_status = discord.Status.dnd
        elif status_type.lower() == "idle":
            default_status = discord.Status.idle
        elif status_type.lower() == "invisible":
            default_status = discord.Status.invisible
        else:
            await ctx.send(
                "Invalid status type. Use 'online', 'dnd', 'idle', or 'invisible'.")
            return

        await bot.change_presence(status=default_status)
        await ctx.send(f"Default status set to {status_type.capitalize()} ✅")
    else:
        await ctx.send(
            f"You don't have permission to use this command, {
                ctx.author.mention}."
        )


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


@bot.tree.command(name='help')
async def help_command(interaction: discord.Interaction):
    """Shows my commands list."""
    embed = discord.Embed(
        title="Welcome to my help page!",
        description="Click the button below! <a:BleachAizenLetHimCook:1138618255381119067>\n\n"
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
