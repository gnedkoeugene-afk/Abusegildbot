# views/static.py — ПОЛНЫЙ ФАЙЛ (ДОБАВЛЕН ТЕКСТ "КАК СТАТЬ УЧЕНИКОМ")

import discord
from discord.ui import View, Button, Select, Modal, TextInput
from discord import ButtonStyle, Color, Embed
import utils


class StaticSettingsView(View):
    """Настройки статика"""
    def __init__(self):
        super().__init__(timeout=300)
    
    @discord.ui.button(label="📝 Текст сообщения", style=ButtonStyle.primary, emoji="📝", row=0)
    async def set_message(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        await interaction.response.send_modal(StaticMessageModal(db))
    
    @discord.ui.button(label="📝 Текст 'Как стать учеником'", style=ButtonStyle.primary, emoji="📝", row=0)
    async def set_no_role_text(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        await interaction.response.send_modal(StaticNoRoleTextModal(db))
    
    @discord.ui.button(label="📋 Роли голосования", style=ButtonStyle.primary, emoji="📋", row=1)
    async def vote_roles(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        embed = Embed(title="📋 Роли для голосования в статик", description="Укажите до 5 ролей, которые будут голосовать.", color=Color.blue())
        for i in range(1, 6):
            role_id = utils.safe_int(db.get_setting(f'vote_role_{i}', ''))
            role = interaction.guild.get_role(role_id) if role_id else None
            member_count = len(role.members) if role else 0
            embed.add_field(name=f"Роль #{i}", value=f"{role.mention if role else '❌ Не настроена'} — **{member_count}** чел.", inline=True)
        view = VoteRolesSetupView(db)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="🎭 Роли при принятии", style=ButtonStyle.primary, emoji="🎭", row=1)
    async def role_changes(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        add_role_id = utils.safe_int(db.get_setting('static_add_role', '')); add_role = interaction.guild.get_role(add_role_id) if add_role_id else None
        remove_roles = [interaction.guild.get_role(utils.safe_int(db.get_setting(f'static_remove_role_{i}', ''))) for i in range(1, 4) if utils.safe_int(db.get_setting(f'static_remove_role_{i}', ''))]
        remove_roles = [r for r in remove_roles if r]
        embed = Embed(title="🎭 Роли при принятии в статик", description="Настройте какие роли выдавать и убирать при принятии", color=Color.blue())
        embed.add_field(name="✅ Выдаётся", value=add_role.mention if add_role else "❌ Не настроена", inline=False)
        if remove_roles: embed.add_field(name="❌ Убираются", value="\n".join([r.mention for r in remove_roles]), inline=False)
        else: embed.add_field(name="❌ Убираются", value="Не настроены", inline=False)
        embed.add_field(name="💡 Подсказка", value="При принятии в статик:\n• Выдаётся указанная роль\n• Убираются указанные роли", inline=False)
        view = StaticRoleChangesView(db)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="🔑 Роль для подачи", style=ButtonStyle.primary, emoji="🔑", row=2)
    async def required_role(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        role_id = utils.safe_int(db.get_setting('static_required_role', '')); role = interaction.guild.get_role(role_id) if role_id else None
        embed = Embed(title="🔑 Роль для подачи заявки в статик", description="Укажите роль, которая нужна чтобы подать заявку в статик.\nЕсли не указано — используется роль **Участник**.", color=Color.blue())
        embed.add_field(name="Текущая роль", value=role.mention if role else "❌ Не настроена", inline=False)
        view = StaticRequiredRoleView(db)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="👁️ Просмотр", style=ButtonStyle.secondary, emoji="👁️", row=2)
    async def view_settings(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        message = db.get_setting('static_request_message', 'Не настроено')
        no_role_text = db.get_setting('static_no_role_text', 'Не настроено')
        embed = Embed(title="📋 Настройки статика", color=Color.blue())
        embed.add_field(name="📝 Текст сообщения", value=message[:500] or "Не настроено", inline=False)
        embed.add_field(name="📝 Текст 'Как стать учеником'", value=no_role_text[:500] or "Не настроено", inline=False)
        roles_text = ""; total_voters = set()
        for i in range(1, 6):
            role_id = utils.safe_int(db.get_setting(f'vote_role_{i}', ''))
            if role_id: 
                role = interaction.guild.get_role(role_id)
                if role:
                    for m in role.members:
                        if not m.bot: total_voters.add(m.id)
                    roles_text += f"**Роль #{i}:** {role.mention} ({len(role.members)} чел.)\n"
        if roles_text: embed.add_field(name="📋 Роли голосования", value=roles_text, inline=False); embed.add_field(name="👥 Всего голосующих", value=f"**{len(total_voters)}** человек", inline=True)
        add_role_id = utils.safe_int(db.get_setting('static_add_role', '')); add_role = interaction.guild.get_role(add_role_id) if add_role_id else None
        remove_roles_text = ""
        for i in range(1, 4):
            role_id = utils.safe_int(db.get_setting(f'static_remove_role_{i}', ''))
            role = interaction.guild.get_role(role_id) if role_id else None
            if role: remove_roles_text += f"❌ {role.mention}\n"
        embed.add_field(name="✅ Выдаётся", value=add_role.mention if add_role else "Не настроена", inline=True)
        embed.add_field(name="❌ Убираются", value=remove_roles_text or "Не настроены", inline=True)
        req_role_id = utils.safe_int(db.get_setting('static_required_role', '')); req_role = interaction.guild.get_role(req_role_id) if req_role_id else None
        embed.add_field(name="🔑 Роль для подачи", value=req_role.mention if req_role else "Роль Участник", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🔙 Назад", style=ButtonStyle.danger, emoji="🔙", row=3)
    async def back(self, interaction: discord.Interaction, button: Button):
        from views.settings import SettingsView
        view = SettingsView()
        embed = Embed(title="⚙️ Панель управления", description="Выберите раздел:", color=Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)


class VoteRolesSetupView(View):
    def __init__(self, db): super().__init__(timeout=120); self.db = db
    @discord.ui.button(label="1️⃣", style=ButtonStyle.primary, row=0)
    async def role1(self, interaction, button): await interaction.response.send_modal(VoteRoleModal(self.db, 'vote_role_1', 'Роль #1'))
    @discord.ui.button(label="2️⃣", style=ButtonStyle.primary, row=0)
    async def role2(self, interaction, button): await interaction.response.send_modal(VoteRoleModal(self.db, 'vote_role_2', 'Роль #2'))
    @discord.ui.button(label="3️⃣", style=ButtonStyle.primary, row=0)
    async def role3(self, interaction, button): await interaction.response.send_modal(VoteRoleModal(self.db, 'vote_role_3', 'Роль #3'))
    @discord.ui.button(label="4️⃣", style=ButtonStyle.primary, row=1)
    async def role4(self, interaction, button): await interaction.response.send_modal(VoteRoleModal(self.db, 'vote_role_4', 'Роль #4'))
    @discord.ui.button(label="5️⃣", style=ButtonStyle.primary, row=1)
    async def role5(self, interaction, button): await interaction.response.send_modal(VoteRoleModal(self.db, 'vote_role_5', 'Роль #5'))
    @discord.ui.button(label="🔙", style=ButtonStyle.secondary, row=1)
    async def back(self, interaction, button):
        db = interaction.client.get_db(interaction.guild_id)
        embed = Embed(title="📋 Роли для голосования", color=Color.blue())
        for i in range(1, 6):
            role_id = utils.safe_int(db.get_setting(f'vote_role_{i}', '')); role = interaction.guild.get_role(role_id) if role_id else None
            embed.add_field(name=f"Роль #{i}", value=f"{role.mention if role else '❌'} — **{len(role.members) if role else 0}** чел.", inline=True)
        await interaction.response.edit_message(embed=embed, view=VoteRolesSetupView(db))


class VoteRoleModal(Modal):
    def __init__(self, db, key, title):
        super().__init__(title=title); self.db = db; self.key = key
        self.add_item(TextInput(label="ID роли Discord", placeholder="123456789", default=db.get_setting(key, ''), required=False, max_length=20))
    async def on_submit(self, interaction):
        role_id = self.children[0].value.strip()
        if role_id:
            if not role_id.isdigit(): await interaction.response.send_message("❌ Числовой ID!", ephemeral=True); return
            role = interaction.guild.get_role(int(role_id))
            if not role: await interaction.response.send_message("❌ Роль не найдена!", ephemeral=True); return
            self.db.set_setting(self.key, role_id); await interaction.response.send_message(f"✅ {role.mention} — **{len(role.members)}** чел.", ephemeral=True)
        else: self.db.set_setting(self.key, ''); await interaction.response.send_message("✅ Сброшено", ephemeral=True)


class StaticRoleChangesView(View):
    def __init__(self, db): super().__init__(timeout=120); self.db = db
    @discord.ui.button(label="✅ Выдавать", style=ButtonStyle.success, emoji="✅", row=0)
    async def set_add(self, interaction, button): await interaction.response.send_modal(StaticRoleModal(self.db, 'static_add_role', '✅ Выдаваемая роль'))
    @discord.ui.button(label="❌ Убрать 1", style=ButtonStyle.danger, emoji="❌", row=1)
    async def set_rm1(self, interaction, button): await interaction.response.send_modal(StaticRoleModal(self.db, 'static_remove_role_1', '❌ Убрать #1'))
    @discord.ui.button(label="❌ Убрать 2", style=ButtonStyle.danger, emoji="❌", row=1)
    async def set_rm2(self, interaction, button): await interaction.response.send_modal(StaticRoleModal(self.db, 'static_remove_role_2', '❌ Убрать #2'))
    @discord.ui.button(label="❌ Убрать 3", style=ButtonStyle.danger, emoji="❌", row=1)
    async def set_rm3(self, interaction, button): await interaction.response.send_modal(StaticRoleModal(self.db, 'static_remove_role_3', '❌ Убрать #3'))
    @discord.ui.button(label="🔙", style=ButtonStyle.secondary, emoji="🔙", row=2)
    async def back(self, interaction, button):
        db = interaction.client.get_db(interaction.guild_id)
        add_role_id = utils.safe_int(db.get_setting('static_add_role', '')); add_role = interaction.guild.get_role(add_role_id) if add_role_id else None
        remove_roles = [interaction.guild.get_role(utils.safe_int(db.get_setting(f'static_remove_role_{i}', ''))) for i in range(1, 4)]
        remove_roles = [r for r in remove_roles if r]
        embed = Embed(title="🎭 Роли при принятии", color=Color.blue())
        embed.add_field(name="✅ Выдаётся", value=add_role.mention if add_role else "❌", inline=False)
        if remove_roles: embed.add_field(name="❌ Убираются", value="\n".join([r.mention for r in remove_roles]), inline=False)
        await interaction.response.edit_message(embed=embed, view=StaticRoleChangesView(db))


class StaticRoleModal(Modal):
    def __init__(self, db, key, title):
        super().__init__(title=title); self.db = db; self.key = key
        self.add_item(TextInput(label="ID роли Discord", placeholder="123456789", default=db.get_setting(key, ''), required=False, max_length=20))
    async def on_submit(self, interaction):
        role_id = self.children[0].value.strip()
        if role_id:
            if not role_id.isdigit(): await interaction.response.send_message("❌ Числовой ID!", ephemeral=True); return
            role = interaction.guild.get_role(int(role_id))
            if not role: await interaction.response.send_message("❌ Роль не найдена!", ephemeral=True); return
            self.db.set_setting(self.key, role_id); await interaction.response.send_message(f"✅ {role.mention}", ephemeral=True)
        else: self.db.set_setting(self.key, ''); await interaction.response.send_message("✅ Сброшено", ephemeral=True)


class StaticRequiredRoleView(View):
    def __init__(self, db): super().__init__(timeout=120); self.db = db
    @discord.ui.button(label="🔑 Указать роль", style=ButtonStyle.primary, emoji="🔑", row=0)
    async def set_role(self, interaction, button): await interaction.response.send_modal(StaticRequiredRoleModal(self.db))
    @discord.ui.button(label="🗑️ Сбросить", style=ButtonStyle.danger, emoji="🗑️", row=0)
    async def reset(self, interaction, button): self.db.set_setting('static_required_role', ''); await interaction.response.send_message("✅ Сброшено!", ephemeral=True)
    @discord.ui.button(label="🔙", style=ButtonStyle.secondary, emoji="🔙", row=1)
    async def back(self, interaction, button):
        db = interaction.client.get_db(interaction.guild_id)
        role_id = utils.safe_int(db.get_setting('static_required_role', '')); role = interaction.guild.get_role(role_id) if role_id else None
        embed = Embed(title="🔑 Роль для подачи", color=Color.blue()); embed.add_field(name="Текущая", value=role.mention if role else "❌", inline=False)
        await interaction.response.edit_message(embed=embed, view=StaticRequiredRoleView(db))


class StaticRequiredRoleModal(Modal):
    def __init__(self, db):
        super().__init__(title="🔑 Роль для подачи в статик"); self.db = db
        self.add_item(TextInput(label="ID роли Discord", placeholder="123456789", default=db.get_setting('static_required_role', ''), required=False, max_length=20))
    async def on_submit(self, interaction):
        role_id = self.children[0].value.strip()
        if role_id:
            if not role_id.isdigit(): await interaction.response.send_message("❌ Числовой ID!", ephemeral=True); return
            role = interaction.guild.get_role(int(role_id))
            if not role: await interaction.response.send_message("❌ Роль не найдена!", ephemeral=True); return
            self.db.set_setting('static_required_role', role_id); await interaction.response.send_message(f"✅ {role.mention} теперь нужна!", ephemeral=True)
        else: self.db.set_setting('static_required_role', ''); await interaction.response.send_message("✅ Сброшено!", ephemeral=True)


class StaticMessageModal(Modal):
    def __init__(self, db):
        super().__init__(title="📝 Текст сообщения для статика"); self.db = db
        current = db.get_setting('static_request_message', '')
        self.add_item(TextInput(label="Текст сообщения", placeholder="Введите текст...", style=discord.TextStyle.paragraph, default=current, required=True, max_length=1000))
    async def on_submit(self, interaction):
        self.db.set_setting('static_request_message', self.children[0].value.strip())
        await interaction.response.send_message("✅ Обновлено!", ephemeral=True)


class StaticNoRoleTextModal(Modal):
    """Текст если нет роли"""
    def __init__(self, db):
        super().__init__(title="📝 Текст 'Как стать учеником'"); self.db = db
        current = db.get_setting('static_no_role_text', '')
        self.add_item(TextInput(label="Текст сообщения", placeholder="Опишите как получить роль...", style=discord.TextStyle.paragraph, default=current, required=True, max_length=1000))
    async def on_submit(self, interaction):
        self.db.set_setting('static_no_role_text', self.children[0].value.strip())
        await interaction.response.send_message("✅ Обновлено!", ephemeral=True)