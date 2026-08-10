# modals/settings_modals.py — ПОЛНЫЙ ФАЙЛ (С АВТООБНОВЛЕНИЕМ)

import discord
from discord.ui import Modal, TextInput
from discord import TextStyle, Color, Embed
import utils


# ═══════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ОБНОВЛЕНИЯ
# ═══════════════════════════════════════════════

async def update_apply_embed(interaction: discord.Interaction):
    """Обновляет окно заявок после изменения настроек"""
    try:
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            return
        
        msg_data = db.get_message('apply')
        if not msg_data:
            return
        
        channel = interaction.guild.get_channel(msg_data[0])
        if not channel:
            return
        
        try:
            msg = await channel.fetch_message(msg_data[1])
        except:
            return
        
        guild_name = db.get_setting('guild_name', 'Abuse')
        server = db.get_setting('server', 'Sirus')
        faction = db.get_setting('faction', 'Alliance')
        raid_times = db.get_setting('raid_times', '20:00 МСК')
        apply_desc = db.get_setting('apply_description', '')
        
        apply_embed = discord.Embed(
            title=f"🏰 {guild_name.upper()}",
            description=(
                f"**▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬**\n"
                f"    ДОБРО ПОЖАЛОВАТЬ В ГИЛЬДИЮ!\n"
                f"**▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬**\n\n"
                f"**🌍 Сервер**{server}\n"
                f"**⚔️ Фракция**{faction}\n"
                f"**📅 Рейдовое время**{raid_times}\n`"
            ),
            color=discord.Color.purple()
        )
        
        if apply_desc:
            apply_embed.add_field(
                name="",
                value=f"```ansi\n[1;33m▐[0m[1;37m ТРЕБОВАНИЯ К КАНДИДАТАМ [0m[1;33m▌[0m\n```\n{apply_desc[:1000]}",
                inline=False
            )
        
        apply_embed.add_field(
            name="",
            value=f"```ansi\n[1;32m▐[0m[1;37m ГОТОВЫ ПРИСОЕДИНИТЬСЯ? [0m[1;32m▌[0m\n```\n"
                  f"*Нажмите кнопку **📝 Подать заявку** ниже чтобы начать!*",
            inline=False
        )
        
        if interaction.guild.icon:
            apply_embed.set_thumbnail(url=interaction.guild.icon.url)
        
        apply_embed.set_footer(
            text=f"⭐ {guild_name} • Sirus x3 • Присоединяйся! ⭐",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        from views.applications import ApplyView
        await msg.edit(embed=apply_embed, view=ApplyView())
    except Exception as e:
        print(f"⚠️ Ошибка обновления apply_embed: {e}")


class RoleSettingModal(Modal):
    def __init__(self, role_key: str, role_name: str):
        super().__init__(title=f"Настройка роли: {role_name}", timeout=None)
        self.role_key = role_key
        self.role_name = role_name
        self.add_item(TextInput(
            label="ID роли (можно несколько через запятую)",
            placeholder="123456789, 987654321 или #роль",
            required=False
        ))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.db
        value = self.children[0].value.strip()
        
        if value:
            ids = []
            for part in value.split(','):
                part = part.strip()
                if part.startswith('<@&') and part.endswith('>'):
                    part = part.replace('<@&', '').replace('>', '')
                if part.isdigit():
                    role = interaction.guild.get_role(int(part))
                    if role:
                        ids.append(part)
                    else:
                        await interaction.response.send_message(
                            f"❌ Роль с ID {part} не найдена на сервере!",
                            ephemeral=True, delete_after=20
                        )
                        return
                else:
                    await interaction.response.send_message(
                        f"❌ Неверный формат ID: {part}",
                        ephemeral=True, delete_after=20
                    )
                    return
            
            if ids:
                db.set_setting(self.role_key, ','.join(ids))
                role_mentions = [
                    interaction.guild.get_role(int(rid)).mention
                    for rid in ids
                    if interaction.guild.get_role(int(rid))
                ]
                embed = Embed(
                    title="✅ Роль сохранена",
                    description=f"{self.role_name}: {', '.join(role_mentions)}",
                    color=Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
                await update_apply_embed(interaction)
                return
        
        db.set_setting(self.role_key, '')
        embed = Embed(
            title="✅ Роль удалена",
            description=f"{self.role_name}: ❌ Не настроена",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
        await update_apply_embed(interaction)


class ChannelsModal1(Modal):
    def __init__(self, defaults):
        super().__init__(title="📝 Настройка каналов (1/2)", timeout=None)
        self.add_item(TextInput(
            label="📝 Канал заявок (ID)",
            placeholder="123456789 или #канал",
            required=False,
            default=defaults.get('applications_channel', '')
        ))
        self.add_item(TextInput(
            label="⚖️ Канал апелляций (ID)",
            placeholder="123456789 или #канал",
            required=False,
            default=defaults.get('appeal_channel', '')
        ))
        self.add_item(TextInput(
            label="📁 Канал архива (ID)",
            placeholder="123456789 или #канал",
            required=False,
            default=defaults.get('archive_channel', '')
        ))
        self.add_item(TextInput(
            label="📝 Канал логов (ID)",
            placeholder="123456789 или #канал",
            required=False,
            default=defaults.get('log_channel', '')
        ))
        self.add_item(TextInput(
            label="📅 Канал отсутствий (ID)",
            placeholder="123456789 или #канал",
            required=False,
            default=defaults.get('absence_channel', '')
        ))

    async def on_submit(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message(
                "❌ Только разработчик может изменять настройки!",
                ephemeral=True, delete_after=20
            )
            return
        
        db = interaction.client.db
        
        def parse_id(value):
            if not value:
                return ''
            value = value.strip().replace('<#', '').replace('>', '')
            return value if value.isdigit() else ''
        
        db.set_setting('applications_channel', parse_id(self.children[0].value))
        db.set_setting('appeal_channel', parse_id(self.children[1].value))
        db.set_setting('archive_channel', parse_id(self.children[2].value))
        db.set_setting('log_channel', parse_id(self.children[3].value))
        db.set_setting('absence_channel', parse_id(self.children[4].value))
        
        embed = Embed(
            title="✅ Каналы сохранены (часть 1)",
            description="Теперь настройте остальные каналы во второй части.",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
        await update_apply_embed(interaction)


class ChannelsModal2(Modal):
    def __init__(self, defaults):
        super().__init__(title="📝 Настройка каналов (2/2)", timeout=None)
        self.add_item(TextInput(
            label="🎮 Канал персонажей (ID)",
            placeholder="123456789 или #канал",
            required=False,
            default=defaults.get('characters_channel_id', '')
        ))
        self.add_item(TextInput(
            label="⚠️ Канал наказаний (ID)",
            placeholder="123456789 или #канал",
            required=False,
            default=defaults.get('punishment_channel', '')
        ))
        self.add_item(TextInput(
            label="📋 Канал отображения составов (ID)",
            placeholder="123456789 или #канал",
            required=False,
            default=defaults.get('composition_channel', '')
        ))
        self.add_item(TextInput(
            label="🎯 Канал управления составами (ID)",
            placeholder="123456789 или #канал",
            required=False,
            default=defaults.get('composition_control_channel', '')
        ))

    async def on_submit(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message(
                "❌ Только разработчик может изменять настройки!",
                ephemeral=True, delete_after=20
            )
            return
        
        db = interaction.client.db
        
        def parse_id(value):
            if not value:
                return ''
            value = value.strip().replace('<#', '').replace('>', '')
            return value if value.isdigit() else ''
        
        db.set_setting('characters_channel_id', parse_id(self.children[0].value))
        db.set_setting('punishment_channel', parse_id(self.children[1].value))
        db.set_setting('composition_channel', parse_id(self.children[2].value))
        db.set_setting('composition_control_channel', parse_id(self.children[3].value))
        
        embed = Embed(
            title="✅ Каналы сохранены (часть 2)",
            description="Настройка каналов завершена!",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
        await update_apply_embed(interaction)


class CategoriesModal(Modal):
    def __init__(self, defaults):
        super().__init__(title="📂 Настройка категорий", timeout=None)
        self.add_item(TextInput(
            label="📂 Категория заявок (ID)",
            placeholder="123456789 или #категория",
            required=False,
            default=defaults.get('applications_category', '')
        ))
        self.add_item(TextInput(
            label="📂 Категория апелляций (ID)",
            placeholder="123456789 или #категория",
            required=False,
            default=defaults.get('appeal_category', '')
        ))
        self.add_item(TextInput(
            label="📝 Категория заданий (ID)",
            placeholder="123456789 или #категория",
            required=False,
            default=defaults.get('tasks_category', '')
        ))
        self.add_item(TextInput(
            label="🔄 Категория смены персонажа (ID)",
            placeholder="123456789 или #категория",
            required=False,
            default=defaults.get('main_change_category', '')
        ))
        self.add_item(TextInput(
            label="📋 Категория статик (ID)",
            placeholder="123456789 или #категория",
            required=False,
            default=defaults.get('static_request_category', '')
        ))

    async def on_submit(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message(
                "❌ Только разработчик может изменять настройки!",
                ephemeral=True, delete_after=20
            )
            return
        
        db = interaction.client.db
        
        def parse_id(value):
            if not value:
                return ''
            value = value.strip().replace('<#', '').replace('>', '')
            return value if value.isdigit() else ''
        
        db.set_setting('applications_category', parse_id(self.children[0].value))
        db.set_setting('appeal_category', parse_id(self.children[1].value))
        db.set_setting('tasks_category', parse_id(self.children[2].value))
        db.set_setting('main_change_category', parse_id(self.children[3].value))
        db.set_setting('static_request_category', parse_id(self.children[4].value))
        
        embed = Embed(
            title="✅ Настройки категорий сохранены",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
        await update_apply_embed(interaction)


class InfoModal(Modal):
    def __init__(self, defaults):
        super().__init__(title="ℹ️ Информация о гильдии", timeout=None)
        self.add_item(TextInput(
            label="🏰 Название гильдии",
            required=False,
            default=defaults.get('guild_name', 'Abuse')
        ))
        self.add_item(TextInput(
            label="🌍 Сервер",
            required=False,
            default=defaults.get('server', 'Sirus')
        ))
        self.add_item(TextInput(
            label="⚔️ Фракция",
            required=False,
            default=defaults.get('faction', 'Alliance')
        ))
        self.add_item(TextInput(
            label="📅 Время рейдов",
            required=False,
            default=defaults.get('raid_times', '20:00 МСК')
        ))
        self.add_item(TextInput(
            label="📋 Описание при подаче заявки",
            style=TextStyle.paragraph,
            required=False,
            default=defaults.get('apply_description', ''),
            max_length=500,
            placeholder="Опишите требования к игрокам..."
        ))

    async def on_submit(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message(
                "❌ Только разработчик может изменять настройки!",
                ephemeral=True, delete_after=20
            )
            return
        
        db = interaction.client.db
        db.set_setting('guild_name', self.children[0].value)
        db.set_setting('server', self.children[1].value)
        db.set_setting('faction', self.children[2].value)
        db.set_setting('raid_times', self.children[3].value)
        db.set_setting('apply_description', self.children[4].value)
        
        embed = Embed(
            title="✅ Информация о гильдии сохранена",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
        await update_apply_embed(interaction)


class RewardRolesModal(Modal):
    def __init__(self, defaults):
        super().__init__(title="🎭 Роли для выдачи (1/2)", timeout=None)
        self.add_item(TextInput(
            label="✅ Роль принятия (ID через запятую)",
            placeholder="123456789, 987654321",
            required=False,
            default=defaults.get('member_role', '')
        ))
        self.add_item(TextInput(
            label="❌ Роль отклонения (ID через запятую)",
            placeholder="123456789, 987654321",
            required=False,
            default=defaults.get('reject_role', '')
        ))
        self.add_item(TextInput(
            label="🚫 Роль ЧС (ID через запятую)",
            placeholder="123456789, 987654321",
            required=False,
            default=defaults.get('blacklist_role', '')
        ))
        self.add_item(TextInput(
            label="🟡 Роль AFK (ID через запятую)",
            placeholder="123456789, 987654321",
            required=False,
            default=defaults.get('afk_role', '')
        ))
        self.add_item(TextInput(
            label="⭐ Роль статика (ID через запятую)",
            placeholder="123456789, 987654321",
            required=False,
            default=defaults.get('static_role', '')
        ))

    async def on_submit(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message(
                "❌ Только разработчик может изменять настройки!",
                ephemeral=True, delete_after=20
            )
            return
        
        db = interaction.client.db
        db.set_setting('member_role', self.children[0].value)
        db.set_setting('reject_role', self.children[1].value)
        db.set_setting('blacklist_role', self.children[2].value)
        db.set_setting('afk_role', self.children[3].value)
        db.set_setting('static_role', self.children[4].value)
        
        embed = Embed(
            title="✅ Роли для выдачи (часть 1) сохранены",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
        await update_apply_embed(interaction)


class RewardRolesModal2(Modal):
    def __init__(self, defaults):
        super().__init__(title="🎭 Роли для выдачи (2/2)", timeout=None)
        self.add_item(TextInput(
            label="👑 Роль гостя (ID через запятую)",
            placeholder="123456789, 987654321",
            required=False,
            default=defaults.get('guest_role', '')
        ))
        self.add_item(TextInput(
            label="⚠️ Роль нарушителя (ID через запятую)",
            placeholder="123456789, 987654321",
            required=False,
            default=defaults.get('violator_role', '')
        ))

    async def on_submit(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message(
                "❌ Только разработчик может изменять настройки!",
                ephemeral=True, delete_after=20
            )
            return
        
        db = interaction.client.db
        db.set_setting('guest_role', self.children[0].value)
        db.set_setting('violator_role', self.children[1].value)
        
        embed = Embed(
            title="✅ Настройки ролей для выдачи сохранены",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
        await update_apply_embed(interaction)


class PriorityRoleInputModal(Modal):
    """Приоритеты 1-5"""
    def __init__(self):
        super().__init__(title="⭐ Приоритет ролей (1-5)", timeout=None)
        self.add_item(TextInput(
            label="🥇 Приоритет 1 (наивысший)",
            placeholder="ID роли",
            required=False
        ))
        self.add_item(TextInput(
            label="🥈 Приоритет 2",
            placeholder="ID роли",
            required=False
        ))
        self.add_item(TextInput(
            label="🥉 Приоритет 3",
            placeholder="ID роли",
            required=False
        ))
        self.add_item(TextInput(
            label="4️⃣ Приоритет 4",
            placeholder="ID роли",
            required=False
        ))
        self.add_item(TextInput(
            label="5️⃣ Приоритет 5",
            placeholder="ID роли",
            required=False
        ))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.db
        
        saved = []
        for i, child in enumerate(self.children, 1):
            value = child.value.strip()
            if value:
                if value.startswith('<@&') and value.endswith('>'):
                    value = value.replace('<@&', '').replace('>', '')
                if value.isdigit():
                    role = interaction.guild.get_role(int(value))
                    if role:
                        db.set_setting(f'priority_role_{i}', value)
                        saved.append(f"{['','🥇','🥈','🥉','4️⃣','5️⃣'][i]} {role.mention}")
                    else:
                        await interaction.response.send_message(
                            f"❌ Роль с ID {value} не найдена!",
                            ephemeral=True, delete_after=10
                        )
                        return
                else:
                    await interaction.response.send_message(
                        f"❌ Неверный ID: {value}",
                        ephemeral=True, delete_after=10
                    )
                    return
            else:
                db.set_setting(f'priority_role_{i}', '')
        
        if saved:
            embed = Embed(
                title="✅ Приоритеты 1-5 сохранены",
                description="\n".join(saved),
                color=Color.green()
            )
        else:
            embed = Embed(
                title="✅ Приоритеты 1-5 очищены",
                color=Color.green()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)
        await update_apply_embed(interaction)


class PriorityRoleInputModal2(Modal):
    """Приоритеты 6-10"""
    def __init__(self):
        super().__init__(title="⭐ Приоритет ролей (6-10)", timeout=None)
        self.add_item(TextInput(
            label="6️⃣ Приоритет 6",
            placeholder="ID роли",
            required=False
        ))
        self.add_item(TextInput(
            label="7️⃣ Приоритет 7",
            placeholder="ID роли",
            required=False
        ))
        self.add_item(TextInput(
            label="8️⃣ Приоритет 8",
            placeholder="ID роли",
            required=False
        ))
        self.add_item(TextInput(
            label="9️⃣ Приоритет 9",
            placeholder="ID роли",
            required=False
        ))
        self.add_item(TextInput(
            label="🔟 Приоритет 10",
            placeholder="ID роли",
            required=False
        ))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.db
        
        saved = []
        for i, child in enumerate(self.children, 6):
            value = child.value.strip()
            if value:
                if value.startswith('<@&') and value.endswith('>'):
                    value = value.replace('<@&', '').replace('>', '')
                if value.isdigit():
                    role = interaction.guild.get_role(int(value))
                    if role:
                        db.set_setting(f'priority_role_{i}', value)
                        saved.append(f"{['','','','','','','6️⃣','7️⃣','8️⃣','9️⃣','🔟'][i]} {role.mention}")
                    else:
                        await interaction.response.send_message(
                            f"❌ Роль с ID {value} не найдена!",
                            ephemeral=True, delete_after=10
                        )
                        return
                else:
                    await interaction.response.send_message(
                        f"❌ Неверный ID: {value}",
                        ephemeral=True, delete_after=10
                    )
                    return
            else:
                db.set_setting(f'priority_role_{i}', '')
        
        if saved:
            embed = Embed(
                title="✅ Приоритеты 6-10 сохранены",
                description="\n".join(saved),
                color=Color.green()
            )
        else:
            embed = Embed(
                title="✅ Приоритеты 6-10 очищены",
                color=Color.green()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)
        await update_apply_embed(interaction)


class TaskSettingsModal(Modal):
    def __init__(self, task_number: int, current_text: str = ""):
        super().__init__(title=f"Настройка задания №{task_number}", timeout=None)
        self.task_number = task_number
        self.add_item(TextInput(
            label="📝 Текст задания",
            placeholder="Введите описание задания...",
            style=TextStyle.paragraph,
            required=True,
            max_length=1000,
            default=current_text
        ))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.db
        task_text = self.children[0].value
        db.set_task_settings(self.task_number, task_text)
        
        embed = Embed(
            title="✅ Задание сохранено",
            description=f"Задание №{self.task_number}:\n{task_text}",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
        await update_apply_embed(interaction)


class StaticMessageModal(Modal):
    def __init__(self):
        super().__init__(title="📝 Настройка текста сообщения", timeout=None)
        default_text = (
            "📋 **Запрос в статик**\n\n"
            "Если вы хотите попасть в основной состав рейдовой группы, заполните заявку ниже.\n\n"
            "**Требования:**\n"
            "• Уровень предметов от 600+\n"
            "• Знание тактик\n"
            "• Стабильный онлайн\n\n"
            "Нажмите кнопку **'Я ознакомлен'** и прикрепите скриншоты из AddOns (https://imgur.com)"
        )
        self.add_item(TextInput(
            label="📝 Текст сообщения",
            placeholder="Введите текст...",
            style=TextStyle.paragraph,
            required=True,
            default=default_text,
            max_length=2000
        ))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.db
        message = self.children[0].value
        db.set_static_request_message(message)
        
        embed = Embed(
            title="✅ Текст сохранён",
            description="Новое сообщение для запросов в статик сохранено.",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
        await update_apply_embed(interaction)


class ReportsRolesModal(Modal):
    """Модальное окно для настройки ролей доступа к жалобам"""
    def __init__(self, defaults: dict):
        super().__init__(title="⚠️ Роли для доступа к жалобам", timeout=None)
        
        current_roles = defaults.get('reports_roles', '')
        
        if current_roles:
            role_ids = [r.strip() for r in current_roles.split(',') if r.strip().isdigit()]
            roles_text = ", ".join(role_ids)
            placeholder_text = f"Текущие: {roles_text}"
        else:
            placeholder_text = "Оставьте пустым для стандартных ролей (Офицер+)"
        
        self.add_item(TextInput(
            label="ID ролей через запятую",
            placeholder=placeholder_text,
            default=current_roles,
            required=False,
            max_length=500
        ))
        
        self.add_item(TextInput(
            label="Примечание",
            placeholder="Пусто = стандартные роли (Офицер, РЛ, Зам, Глава)",
            required=False,
            max_length=100,
            default=""
        ))

    async def on_submit(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message(
                "❌ Только разработчик может изменять настройки!",
                ephemeral=True, delete_after=20
            )
            return
        
        db = interaction.client.db
        value = self.children[0].value.strip()
        
        if value:
            ids = []
            for part in value.split(','):
                part = part.strip()
                if part.isdigit():
                    role = interaction.guild.get_role(int(part))
                    if role:
                        ids.append(part)
                    else:
                        await interaction.response.send_message(
                            f"❌ Роль с ID {part} не найдена на сервере!",
                            ephemeral=True, delete_after=20
                        )
                        return
                elif part:
                    await interaction.response.send_message(
                        f"❌ Неверный формат ID: {part}",
                        ephemeral=True, delete_after=20
                    )
                    return
            
            if ids:
                db.set_setting('reports_roles', ','.join(ids))
                role_mentions = [
                    interaction.guild.get_role(int(rid)).mention
                    for rid in ids
                    if interaction.guild.get_role(int(rid))
                ]
                embed = Embed(
                    title="✅ Роли для жалоб сохранены",
                    description=f"Доступ к жалобам имеют:\n{', '.join(role_mentions)}",
                    color=Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
                await update_apply_embed(interaction)
                return
            else:
                db.set_setting('reports_roles', '')
                embed = Embed(
                    title="✅ Сброшено",
                    description="Будут использоваться стандартные роли (Офицер, РЛ, Зам, Глава)",
                    color=Color.green()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
                await update_apply_embed(interaction)
                return
        
        db.set_setting('reports_roles', '')
        embed = Embed(
            title="✅ Сброшено на стандартные роли",
            description="Доступ к жалобам: Офицер, Рейд-лидер, Зам. главы, Глава",
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=20)
        await update_apply_embed(interaction)