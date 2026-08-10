# views/reports.py

import discord
from discord.ui import View, Button
from discord import ButtonStyle
import utils


class ReportReviewView(View):
    """Кнопки управления жалобой — работают после рестарта"""

    def __init__(self, report_id: int, reporter_id: int, violator_id: int,
                 channel_id: int, is_anonymous: bool = False):
        super().__init__(timeout=None)
        self.report_id = report_id
        self.reporter_id = reporter_id
        self.violator_id = violator_id
        self.channel_id = channel_id
        self.is_anonymous = is_anonymous

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
            return False
        if not utils.can_manage_reports(interaction.user, db):
            await interaction.response.send_message("❌ У вас нет прав!", ephemeral=True)
            return False
        return True

    @discord.ui.button(
        label="Принять",
        style=ButtonStyle.success,
        emoji="✅",
        row=0,
        custom_id="report_resolve_btn"
    )
    async def resolve_button(self, interaction: discord.Interaction, button: Button):
        if interaction.response.is_done():
            return
        from modals.report_modals import ReportResolveModal
        modal = ReportResolveModal(
            self.report_id, self.channel_id, 'resolve',
            self.reporter_id, self.is_anonymous
        )
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        label="Отклонить",
        style=ButtonStyle.danger,
        emoji="❌",
        row=0,
        custom_id="report_reject_btn"
    )
    async def reject_button(self, interaction: discord.Interaction, button: Button):
        if interaction.response.is_done():
            return
        from modals.report_modals import ReportResolveModal
        modal = ReportResolveModal(
            self.report_id, self.channel_id, 'reject',
            self.reporter_id, self.is_anonymous
        )
        await interaction.response.send_modal(modal)