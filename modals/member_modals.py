from discord.ui import Modal, TextInput
from discord import TextStyle, Color, Embed
import utils


class ReminderSettingsModal(Modal):
    def __init__(self, defaults):
        super().__init__(title="⚙️ Настройка напоминаний", timeout=None)
        self.add_item(TextInput(label="👥 Роли для проверки (ID через запятую)", placeholder="123456789, 987654321", required=False, default=defaults.get('character_reminder_roles', '')))
        self.add_item(TextInput(label="⏰ Интервал напоминаний (часов)", placeholder="24", required=False, default=defaults.get('character_reminder_interval', '24')))
        self.add_item(TextInput(label="✅ Включить напоминания (1=да, 0=нет)", placeholder="1", required=False, default=defaults.get('character_reminder_enabled', '1')))
        self.add_item(TextInput(label="📝 Текст напоминания", placeholder="Используйте {channel} для вставки канала", style=TextStyle.paragraph, required=False, default=defaults.get('character_reminder_message', '')))

    async def on_submit(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Только разработчик может изменять настройки!", ephemeral=True, delete_after=20)
            return
        db = interaction.client.db
        db.set_setting('character_reminder_roles', self.children[0].value)
        db.set_setting('character_reminder_interval', self.children[1].value)
        db.set_setting('character_reminder_enabled', self.children[2].value)
        db.set_setting('character_reminder_message', self.children[3].value)
        embed = Embed(title="✅ Настройки напоминаний сохранены", color=Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)