import discord
from discord.ui import Button, View
from discord.ext import commands
import time


# Function to get the current GMT+7 time
def get_current_time_gmt7():
  return time.strftime("%Y-%m-%d",
                       time.gmtime(time.time() + 25200)), time.strftime(
                           "%H:%M:%S", time.gmtime(time.time() + 25200))


# Function to get the current GMT+7 time in AM/PM format
def get_current_time_gmt7_ampm():
  return time.strftime("%Y-%m-%d",
                       time.gmtime(time.time() + 25200)), time.strftime(
                           "%I:%M:%S %p", time.gmtime(time.time() + 25200))


class CtimeButton(discord.ui.View):

  @discord.ui.button(label="24H Format",
                     style=discord.ButtonStyle.green,
                     custom_id="24h_format")
  async def hour_button_callback(self, interaction: discord.Interaction,
                                 button: discord.ui.Button):
    current_date, current_time = get_current_time_gmt7()

    embed = discord.Embed(title="Hogyoku's Server Time",
                          description="Format: ` 24h format `\nGMT+7 based.",
                          color=discord.Color.blue())

    embed.add_field(name="🗓️ Date", value=current_date, inline=True)
    embed.add_field(name="🕖 Time", value=current_time, inline=True)

    await interaction.response.edit_message(embed=embed)

  @discord.ui.button(label="AM/PM Format",
                     style=discord.ButtonStyle.blurple,
                     custom_id="ampm_format")
  async def ampm_button_callback(self, interaction: discord.Interaction,
                                 button: discord.ui.Button):
    current_date, current_time = get_current_time_gmt7_ampm()

    embed = discord.Embed(title="Hogyoku's Server Time",
                          description="Format: ` AM/PM format `\nGMT+7 based.",
                          color=discord.Color.blue())

    embed.add_field(name="🗓️ Date", value=current_date, inline=True)
    embed.add_field(name="🕖 Time", value=current_time, inline=True)

    await interaction.response.edit_message(embed=embed)
