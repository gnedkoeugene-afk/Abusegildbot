import discord
from discord.ui import View, Button
from discord import ButtonStyle, Color, Embed
import utils


class AppealMainView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Подать апелляцию", style=ButtonStyle.secondary, emoji="⚖️", custom_id="appeal_btn")
    async def appeal(self, interaction: discord.Interaction, button: Button):
        if not interaction.client.db.is_blacklisted(interaction.user.id):
            await interaction.response.send_message("❌ Вы не в черном списке!", ephemeral=True, delete_after=20)
            return
        from modals.appeal_modals import AppealModal
        await interaction.response.send_modal(AppealModal())


class AppealReviewView(View):
    def __init__(self, channel_id: int, user_id: int, appeal_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.user_id = user_id
        self.appeal_id = appeal_id

    @discord.ui.button(label="Одобрить", style=ButtonStyle.success, emoji="✅", custom_id="approve_appeal_global")
    async def approve_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_appeals(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return

        db = interaction.client.get_db(interaction.guild_id)
        guild = interaction.guild
        user = guild.get_member(self.user_id)

        if user:
            await utils.remove_roles_from_setting(user, db, 'blacklist_role', "Апелляция одобрена")
            await utils.add_roles_from_setting(user, db, 'member_role', "Апелляция одобрена")

        db.remove_blacklist(self.user_id)
        db.update_appeal_status(self.channel_id, "approved")

        if user:
            await user.send(embed=Embed(title="✅ Апелляция одобрена", description="Вы удалены из черного списка!", color=Color.green()))

        await interaction.response.send_message("✅ Одобрено!", ephemeral=True, delete_after=5)
        await interaction.channel.delete()

    @discord.ui.button(label="Отклонить", style=ButtonStyle.danger, emoji="❌", custom_id="reject_appeal_global")
    async def reject_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_appeals(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return

        db = interaction.client.get_db(interaction.guild_id)
        user = interaction.guild.get_member(self.user_id)
        db.update_appeal_status(self.channel_id, "rejected")

        if user:
            await user.send(embed=Embed(title="❌ Апелляция отклонена", color=Color.red()))

        await interaction.response.send_message("❌ Отклонено.", ephemeral=True, delete_after=5)
        await interaction.channel.delete()