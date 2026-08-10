import discord
from discord.ui import View, Button
from discord import ButtonStyle, Color, Embed
import utils


class TaskSettingsView(View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="📝 Задание №1", style=ButtonStyle.primary, emoji="1️⃣", custom_id="task1_set")
    async def task1_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Только разработчик может изменять настройки!", ephemeral=True, delete_after=20)
            return
        db = interaction.client.get_db(interaction.guild_id)
        current_text = db.get_task_settings(1)
        from modals.settings_modals import TaskSettingsModal
        await interaction.response.send_modal(TaskSettingsModal(1, current_text))

    @discord.ui.button(label="📝 Задание №2", style=ButtonStyle.primary, emoji="2️⃣", custom_id="task2_set")
    async def task2_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Только разработчик может изменять настройки!", ephemeral=True, delete_after=20)
            return
        db = interaction.client.get_db(interaction.guild_id)
        current_text = db.get_task_settings(2)
        from modals.settings_modals import TaskSettingsModal
        await interaction.response.send_modal(TaskSettingsModal(2, current_text))

    @discord.ui.button(label="📝 Задание №3", style=ButtonStyle.primary, emoji="3️⃣", custom_id="task3_set")
    async def task3_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Только разработчик может изменять настройки!", ephemeral=True, delete_after=20)
            return
        db = interaction.client.get_db(interaction.guild_id)
        current_text = db.get_task_settings(3)
        from modals.settings_modals import TaskSettingsModal
        await interaction.response.send_modal(TaskSettingsModal(3, current_text))

    @discord.ui.button(label="📝 Задание №4", style=ButtonStyle.primary, emoji="4️⃣", custom_id="task4_set")
    async def task4_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Только разработчик может изменять настройки!", ephemeral=True, delete_after=20)
            return
        db = interaction.client.get_db(interaction.guild_id)
        current_text = db.get_task_settings(4)
        from modals.settings_modals import TaskSettingsModal
        await interaction.response.send_modal(TaskSettingsModal(4, current_text))

    @discord.ui.button(label="📝 Задание №5", style=ButtonStyle.primary, emoji="5️⃣", custom_id="task5_set")
    async def task5_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Только разработчик может изменять настройки!", ephemeral=True, delete_after=20)
            return
        db = interaction.client.get_db(interaction.guild_id)
        current_text = db.get_task_settings(5)
        from modals.settings_modals import TaskSettingsModal
        await interaction.response.send_modal(TaskSettingsModal(5, current_text))

    @discord.ui.button(label="📝 Задание №6", style=ButtonStyle.primary, emoji="6️⃣", custom_id="task6_set")
    async def task6_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Только разработчик может изменять настройки!", ephemeral=True, delete_after=20)
            return
        db = interaction.client.get_db(interaction.guild_id)
        current_text = db.get_task_settings(6)
        from modals.settings_modals import TaskSettingsModal
        await interaction.response.send_modal(TaskSettingsModal(6, current_text))

    @discord.ui.button(label="📝 Задание №7", style=ButtonStyle.primary, emoji="7️⃣", custom_id="task7_set")
    async def task7_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Только разработчик может изменять настройки!", ephemeral=True, delete_after=20)
            return
        db = interaction.client.get_db(interaction.guild_id)
        current_text = db.get_task_settings(7)
        from modals.settings_modals import TaskSettingsModal
        await interaction.response.send_modal(TaskSettingsModal(7, current_text))

    @discord.ui.button(label="📝 Задание №8", style=ButtonStyle.primary, emoji="8️⃣", custom_id="task8_set")
    async def task8_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Только разработчик может изменять настройки!", ephemeral=True, delete_after=20)
            return
        db = interaction.client.get_db(interaction.guild_id)
        current_text = db.get_task_settings(8)
        from modals.settings_modals import TaskSettingsModal
        await interaction.response.send_modal(TaskSettingsModal(8, current_text))

    @discord.ui.button(label="📝 Задание №9", style=ButtonStyle.primary, emoji="9️⃣", custom_id="task9_set")
    async def task9_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Только разработчик может изменять настройки!", ephemeral=True, delete_after=20)
            return
        db = interaction.client.get_db(interaction.guild_id)
        current_text = db.get_task_settings(9)
        from modals.settings_modals import TaskSettingsModal
        await interaction.response.send_modal(TaskSettingsModal(9, current_text))

    @discord.ui.button(label="📝 Задание №10", style=ButtonStyle.primary, emoji="🔟", custom_id="task10_set")
    async def task10_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Только разработчик может изменять настройки!", ephemeral=True, delete_after=20)
            return
        db = interaction.client.get_db(interaction.guild_id)
        current_text = db.get_task_settings(10)
        from modals.settings_modals import TaskSettingsModal
        await interaction.response.send_modal(TaskSettingsModal(10, current_text))

    @discord.ui.button(label="🔙 Назад", style=ButtonStyle.secondary, emoji="🔙", custom_id="task_back")
    async def back_button(self, interaction: discord.Interaction, button: Button):
        from views.settings import SettingsView
        embed = Embed(title="⚙️ Панель управления", description="Выберите раздел:", color=Color.blue())
        view = SettingsView()
        await interaction.response.edit_message(embed=embed, view=view)