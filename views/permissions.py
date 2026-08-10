# views/permissions.py — ПОЛНЫЙ ИСПРАВЛЕННЫЙ ФАЙЛ (работает с role_permissions)

import discord
from discord.ui import View, Button, Select
from discord import ButtonStyle, Color, Embed
import utils


class PermissionsSettingsView(View):
    """Главное меню настройки прав"""
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="👑 Глава гильдии", style=ButtonStyle.primary, emoji="👑", row=0)
    async def gm_button(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        view = PermissionsEditView("guild_master", "👑 Глава гильдии", db)
        embed = build_permissions_embed("guild_master", "👑 Глава гильдии", db)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="⭐ Зам. главы", style=ButtonStyle.primary, emoji="⭐", row=0)
    async def vm_button(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        view = PermissionsEditView("vice_master", "⭐ Зам. главы", db)
        embed = build_permissions_embed("vice_master", "⭐ Зам. главы", db)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="⚔️ Рейд-лидер", style=ButtonStyle.primary, emoji="⚔️", row=1)
    async def rl_button(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        view = PermissionsEditView("raid_leader", "⚔️ Рейд-лидер", db)
        embed = build_permissions_embed("raid_leader", "⚔️ Рейд-лидер", db)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="📋 Офицер", style=ButtonStyle.primary, emoji="📋", row=1)
    async def of_button(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        view = PermissionsEditView("officer", "📋 Офицер", db)
        embed = build_permissions_embed("officer", "📋 Офицер", db)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🔙 Назад", style=ButtonStyle.secondary, emoji="🔙", row=2)
    async def back_button(self, interaction: discord.Interaction, button: Button):
        from views.settings import SettingsView
        view = SettingsView()
        embed = Embed(title="⚙️ Панель управления", description="Выберите раздел:", color=Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)


class PermissionsEditView(View):
    """Редактирование прав для конкретной роли"""
    def __init__(self, role_key: str, role_name: str, db):
        super().__init__(timeout=120)
        self.role_key = role_key
        self.role_name = role_name
        self.db = db
        
        # Все возможные права
        all_permissions = [
            ("applications", "📝 Управление заявками", "📝"),
            ("appeals", "⚖️ Управление апелляциями", "⚖️"),
            ("absences", "📅 Управление отсутствиями", "📅"),
            ("characters", "👥 Просмотр персонажей", "👥"),
            ("punishments", "⚠️ Выдача наказаний", "⚠️"),
            ("remove_punishments", "📋 Снятие наказаний", "📋"),
            ("raids", "🎯 Создание составов", "🎯"),
            ("manage_raids", "📋 Управление составами", "📋"),
            ("settings", "⚙️ Настройки бота", "⚙️"),
            ("static", "⭐ Принятие в статик", "⭐"),
            ("main_change", "🔄 Одобрение смены", "🔄"),
            ("admin_center", "🔧 Админ-центр", "🔧"),
            ('reports', '⚠️ Управление жалобами', '⚠️'),
        ]
        
        options = []
        for perm_key, perm_label, perm_emoji in all_permissions:
            options.append(discord.SelectOption(
                label=perm_label,
                value=perm_key,
                emoji=perm_emoji
            ))
        
        # Select для выбора права
        select = Select(
            placeholder=f"Выберите право для {role_name}",
            options=options,
            custom_id=f"perm_select_{role_key}",
            row=0
        )
        select.callback = self.select_callback
        self.add_item(select)
        
        # ✅ Кнопка "Назад"
        back_btn = Button(
            label="🔙 Назад",
            style=ButtonStyle.secondary,
            custom_id=f"perm_back_{role_key}",
            row=1
        )
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def select_callback(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        perm_key = interaction.data['values'][0]
        
        # Проверяем, есть ли уже такое право
        existing = db.cursor.execute(
            'SELECT enabled FROM role_permissions WHERE role_key = ? AND permission_key = ?',
            (self.role_key, perm_key)
        ).fetchone()
        
        if existing:
            # Переключаем
            new_value = 0 if existing[0] == 1 else 1
            db.cursor.execute(
                'UPDATE role_permissions SET enabled = ? WHERE role_key = ? AND permission_key = ?',
                (new_value, self.role_key, perm_key)
            )
        else:
            # Добавляем новое право
            new_value = 1
            db.cursor.execute(
                'INSERT INTO role_permissions (role_key, permission_key, enabled) VALUES (?, ?, ?)',
                (self.role_key, perm_key, new_value)
            )
        
        db.conn.commit()
        
        # Логируем
        action = "✅ выдано" if new_value == 1 else "❌ отозвано"
        db.add_log(
            "🔐 Права изменены",
            interaction.user.id,
            details=f"{self.role_name}: {action} право '{perm_key}'"
        )
        
        # Обновляем embed
        embed = build_permissions_embed(self.role_key, self.role_name, db)
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def back_callback(self, interaction: discord.Interaction):
        """Возврат в главное меню прав"""
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        view = PermissionsSettingsView()
        embed = Embed(
            title="🔐 Права доступа",
            description="Выберите роль для настройки прав:",
            color=Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)


def build_permissions_embed(role_key: str, role_name: str, db) -> Embed:
    """Создает embed с текущими правами роли"""
    
    all_permissions = [
        ("applications", "📝 Управление заявками"),
        ("appeals", "⚖️ Управление апелляциями"),
        ("absences", "📅 Управление отсутствиями"),
        ("characters", "👥 Просмотр персонажей"),
        ("punishments", "⚠️ Выдача наказаний"),
        ("remove_punishments", "📋 Снятие наказаний"),
        ("raids", "🎯 Создание составов"),
        ("manage_raids", "📋 Управление составами"),
        ("settings", "⚙️ Настройки бота"),
        ("static", "⭐ Принятие в статик"),
        ("main_change", "🔄 Одобрение смены"),
        ("admin_center", "🔧 Админ-центр"),
        ('reports', '⚠️ Управление жалобами'),
    ]
    
    embed = Embed(
        title=f"🔐 Права доступа: {role_name}",
        description="Выберите право из списка ниже, чтобы включить/выключить его.\n\n",
        color=Color.blue()
    )
    
    # Получаем текущие права из таблицы role_permissions
    permissions_data = {}
    rows = db.cursor.execute(
        'SELECT permission_key, enabled FROM role_permissions WHERE role_key = ?',
        (role_key,)
    ).fetchall()
    
    for row in rows:
        permissions_data[row[0]] = row[1] == 1
    
    status_lines = []
    for perm_key, perm_name in all_permissions:
        has_perm = permissions_data.get(perm_key, False)
        status_lines.append(f"{'✅' if has_perm else '❌'} {perm_name}")
    
    embed.add_field(name="📋 Текущие права", value="\n".join(status_lines), inline=False)
    embed.set_footer(text="Выберите право из выпадающего списка чтобы изменить")
    
    return embed


# Функция для проверки прав (используется в utils.py или где нужно)
def has_permission(db, role_key: str, permission_key: str) -> bool:
    """Проверить, есть ли у роли право"""
    row = db.cursor.execute(
        'SELECT enabled FROM role_permissions WHERE role_key = ? AND permission_key = ?',
        (role_key, permission_key)
    ).fetchone()
    
    return row is not None and row[0] == 1


def get_role_permissions(db, role_key: str) -> list:
    """Получить список прав роли"""
    rows = db.cursor.execute(
        'SELECT permission_key FROM role_permissions WHERE role_key = ? AND enabled = 1',
        (role_key,)
    ).fetchall()
    
    return [row[0] for row in rows]