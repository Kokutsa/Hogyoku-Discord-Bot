import discord
from discord.ui import Button, View
from discord.ext import commands
from config import prefix


class HelpButton(discord.ui.View):

  @discord.ui.button(label="Bot Commands",
                     style=discord.ButtonStyle.grey,
                     custom_id="bot_commands")
  async def bot_commands(self, interaction: discord.Interaction,
                         button: discord.ui.Button):
    bot_commands = []
    for command in self.bot.walk_commands():
      if not command.parent:
        bot_commands.append(command)
    bot_commands.sort(key=lambda x: x.name)  # Sort bot commands alphabetically

    embed = discord.Embed(
        title="Bot Commands",
        description=
        f"My prefixes are: ` {' | '.join(prefix)} `\n\nList of available commands:",
        color=3092790)
    for command in bot_commands:
      embed.add_field(name=command.name,
                      value=command.help or "No description provided.",
                      inline=True)
    await interaction.response.edit_message(embed=embed)

  @discord.ui.button(label="Application Commands",
                     style=discord.ButtonStyle.blurple,
                     custom_id="app_commands")
  async def app_commands(self, interaction: discord.Interaction,
                         button: discord.ui.Button):
    application_id = self.bot.user.id

    # Fetch the registered application commands for this bot
    app_commands = await self.bot.http.get_global_commands(application_id)

    if app_commands:
      app_commands.sort(
          key=lambda x: x["name"])  # Sort application commands alphabetically

      embed = discord.Embed(
          title="Application Commands",
          description=
          f"Reach [level 10](https://discord.com/channels/679934068917534720/679934725800198175/1144558618658750585) to obtain permission of these commands.\n\nList of application commands:",
          color=3092790)
      for command in app_commands:
        command_name = command["name"]
        command_id = command["id"]
        command_description = command[
            "description"] or "No description provided."
        command_format = f"</{command_name}:{command_id}>"  # Use the 'id' from the command
        embed.add_field(name=command_name,
                        value=f"{command_format} {command_description}",
                        inline=True)
      await interaction.response.edit_message(embed=embed)
