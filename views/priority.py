import discord
from discord.ui import View, Button
from discord import ButtonStyle, Color, Embed


class PriorityRolesSetupView(View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="⭐ Приоритеты 1-5", style=ButtonStyle.success, emoji="⭐", custom_id="priority_1_5")
    async def priority_1_5(self, interaction: discord.Interaction, button: Button):
        from modals.settings_modals import PriorityRoleInputModal
        await interaction.response.send_modal(PriorityRoleInputModal())

    @discord.ui.button(label="⭐ Приоритеты 6-10", style=ButtonStyle.success, emoji="⭐", custom_id="priority_6_10")
    async def priority_6_10(self, interaction: discord.Interaction, button: Button):
        from modals.settings_modals import PriorityRoleInputModal2
        await interaction.response.send_modal(PriorityRoleInputModal2())

    @discord.ui.button(label="🗑️ Очистить всё", style=ButtonStyle.danger, emoji="🗑️", custom_id="clear_priority_roles")
    async def clear_priority_roles(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        for i in range(1, 11):
            db.set_setting(f'priority_role_{i}', '')
        embed = Embed(title="✅ Приоритет ролей очищен", description="Теперь приоритет будет определяться только по iLvl.", color=Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)

    @discord.ui.button(label="👁️ Просмотр", style=ButtonStyle.secondary, emoji="👁️", custom_id="view_priority_roles")
    async def view_priority_roles(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        priority_roles = db.get_priority_roles()
        if not priority_roles:
            embed = Embed(title="📋 Приоритет ролей", description="Приоритет не настроен.", color=Color.blue())
        else:
            medals = ['🥇','🥈','🥉','4️⃣','5️⃣','6️⃣','7️⃣','8️⃣','9️⃣','🔟']
            text = ""
            for idx, role_id in enumerate(priority_roles):
                role = interaction.guild.get_role(role_id)
                medal = medals[idx] if idx < 10 else f"{idx+1}."
                text += f"{medal} {role.mention if role else f'❌ {role_id}'}\n"
            embed = Embed(title="📋 Приоритет ролей", description=text, color=Color.blue())
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)

    @discord.ui.button(label="🔙 Назад", style=ButtonStyle.secondary, emoji="🔙", custom_id="priority_back")
    async def back_button(self, interaction: discord.Interaction, button: Button):
        from views.settings import SettingsView
        embed = Embed(title="⚙️ Панель управления", description="Выберите раздел:", color=Color.blue())
        view = SettingsView()
        await interaction.response.edit_message(embed=embed, view=view)