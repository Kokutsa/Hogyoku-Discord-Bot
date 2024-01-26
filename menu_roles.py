import discord
from discord.ext import commands
from discord.ui import Select, View

tickets_admin_id = 1176237826472431708
tickets_support_id = 1176237647224656013
pm_id = 1176237344085520464
bleach_media_id = 1176232353568395365
mudae_administrator_id = 1176237108726345800
marriagebot_moderator_id = 1176236924357316730
emergency_meeting_id = 1176231137073451109

class MySelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Tickets Admin",
                value="1",
                description="Manage access to Tickets and #⇨🧾transcripts.",
                emoji="🎫"
            ),
            discord.SelectOption(
                label="Tickets Support",
                value="2",
                description="Support access to opened tickets.",
                emoji="🎟️"
            ),
            discord.SelectOption(
                label="PM",
                value="3",
                description="Manager of Partnership and Affiliate.",
                emoji="📝"
            ),
            discord.SelectOption(
                label="Bleach Media",
                value="4",
                description="Access to #⇨📰bleach-news and #⇨📰las-noches.",
                emoji="📰"
            ),
            discord.SelectOption(
                label="Mudae Administrator",
                value="5",
                description="Manage access to Mudae bot.",
                emoji="🖼️"
            ),
            discord.SelectOption(
                label="MarriageBot Moderator",
                value="6",
                description="Manage access to MarriageBot.",
                emoji="💍"
            ),
            discord.SelectOption(
                label="Emergency Meeting",
                value="7",
                description="Get notified of emergency meetings.",
                emoji="🦺"
            )
        ]
        super().__init__(placeholder="Select roles!", options=options)

    async def callback(self, interaction: discord.Interaction):
        user_roles = [role.id for role in interaction.user.roles]

        role_mapping = {
            "1": tickets_admin_id,
            "2": tickets_support_id,
            "3": pm_id,
            "4": bleach_media_id,
            "5": mudae_administrator_id,
            "6": marriagebot_moderator_id,
            "7": emergency_meeting_id
        }

        selected_value = self.values[0]
        role_id = role_mapping.get(selected_value)

        if role_id:
            if role_id in user_roles:
                await interaction.response.send_message(f"Role **{self.options[int(selected_value) - 1].label}** has been opt-out.", ephemeral=True)
                await interaction.user.remove_roles(
                    discord.utils.get(interaction.guild.roles, id=role_id))
            else:
                await interaction.response.send_message(
                    f"You have opted-in the role **{self.options[int(selected_value) - 1].label}**.",
                    ephemeral=True)
                await interaction.user.add_roles(
                    discord.utils.get(interaction.guild.roles, id=role_id))

class SelectView(View):
    def __init__(self):
        super().__init__()
        self.add_item(MySelect())

