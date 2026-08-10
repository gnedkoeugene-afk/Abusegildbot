# views/settings.py — ПОЛНЫЙ ФАЙЛ (С ИСПРАВЛЕННЫМИ РОЛЯМИ)

import discord
from discord.ui import View, Button, Select, Modal, TextInput
from discord import ButtonStyle, Color, Embed, Interaction
from constants import CLASS_SPECS
import utils
from datetime import datetime


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
        
        apply_embed = Embed(
            title=f"🏰 {guild_name.upper()}",
            description=(
                f"**▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬**\n"
                f"    ДОБРО ПОЖАЛОВАТЬ В ГИЛЬДИЮ!\n"
                f"**▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬**\n\n"
                f"**🌍 Сервер**{server}\n"
                f"**⚔️ Фракция**{faction}\n"
                f"**📅 Рейдовое время**{raid_times}\n"
            ),
            color=Color.purple()
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


# ═══════════════════════════════════════════════
# ОСНОВНОЙ КЛАСС НАСТРОЕК
# ═══════════════════════════════════════════════

class SettingsView(View):
    def __init__(self):
        super().__init__(timeout=900)

        # ═══════════════════════════════════════════════
        # РЯД 0 — 3 кнопки
        # ═══════════════════════════════════════════════
        self.add_item(GuildRolesSettingsButton())
        self.add_item(Channels1Button())
        self.add_item(Channels2Button())

        # ═══════════════════════════════════════════════
        # РЯД 1 — 3 кнопки
        # ═══════════════════════════════════════════════
        self.add_item(CategoriesButton())
        self.add_item(InfoButton())
        self.add_item(RewardRolesButton())

        # ═══════════════════════════════════════════════
        # РЯД 2 — 3 кнопки
        # ═══════════════════════════════════════════════
        self.add_item(RewardRolesButton2())
        self.add_item(MemberManagementButton())
        self.add_item(ClassRolesButton())

        # ═══════════════════════════════════════════════
        # РЯД 3 — 4 кнопки
        # ═══════════════════════════════════════════════
        self.add_item(PriorityRolesButton())
        self.add_item(TasksButton())
        self.add_item(StaticSettingsButton())
        self.add_item(AbsenceLimitsButton())

        # ═══════════════════════════════════════════════
        # РЯД 4 — 5 кнопок (МАКСИМУМ 5)
        # ═══════════════════════════════════════════════
        self.add_item(PermissionsButton())
        self.add_item(VoiceButton())
        self.add_item(BattleRolesButton())
        self.add_item(ReportsRolesButton())
        self.add_item(TraineeRolesSettingsButton())


# ═══════════════════════════════════════════════
# КНОПКИ РЯДА 0
# ═══════════════════════════════════════════════

class GuildRolesSettingsButton(Button):
    def __init__(self):
        super().__init__(
            label="👥 Роли гильдии",
            style=ButtonStyle.primary,
            emoji="👥",
            row=0,
            custom_id="settings_roles"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        embed = Embed(title="👥 Настройка ролей гильдии", color=Color.blue())
        view = GuildRolesSettingsView()
        await interaction.response.edit_message(embed=embed, view=view)


class Channels1Button(Button):
    def __init__(self):
        super().__init__(
            label="📝 Каналы (1/2)",
            style=ButtonStyle.primary,
            emoji="📝",
            row=0,
            custom_id="settings_channels1"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        db = interaction.client.get_db(interaction.guild_id)
        defaults = {
            'applications_channel': db.get_setting('applications_channel', ''),
            'appeal_channel': db.get_setting('appeal_channel', ''),
            'archive_channel': db.get_setting('archive_channel', ''),
            'log_channel': db.get_setting('log_channel', ''),
            'absence_channel': db.get_setting('absence_channel', '')
        }
        from modals.settings_modals import ChannelsModal1
        await interaction.response.send_modal(ChannelsModal1(defaults))


class Channels2Button(Button):
    def __init__(self):
        super().__init__(
            label="📝 Каналы (2/2)",
            style=ButtonStyle.primary,
            emoji="📝",
            row=0,
            custom_id="settings_channels2"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        db = interaction.client.get_db(interaction.guild_id)
        defaults = {
            'characters_channel_id': db.get_setting('characters_channel_id', ''),
            'punishment_channel': db.get_setting('punishment_channel', ''),
            'composition_channel': db.get_setting('composition_channel', ''),
            'composition_control_channel': db.get_setting('composition_control_channel', '')
        }
        from modals.settings_modals import ChannelsModal2
        await interaction.response.send_modal(ChannelsModal2(defaults))


# ═══════════════════════════════════════════════
# КНОПКИ РЯДА 1
# ═══════════════════════════════════════════════

class CategoriesButton(Button):
    def __init__(self):
        super().__init__(
            label="📂 Категории",
            style=ButtonStyle.primary,
            emoji="📂",
            row=1,
            custom_id="settings_categories"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        db = interaction.client.get_db(interaction.guild_id)
        defaults = {
            'applications_category': db.get_setting('applications_category', ''),
            'appeal_category': db.get_setting('appeal_category', ''),
            'tasks_category': db.get_setting('tasks_category', ''),
            'main_change_category': db.get_setting('main_change_category', ''),
            'static_request_category': db.get_setting('static_request_category', '')
        }
        from modals.settings_modals import CategoriesModal
        await interaction.response.send_modal(CategoriesModal(defaults))


class InfoButton(Button):
    def __init__(self):
        super().__init__(
            label="ℹ️ Информация",
            style=ButtonStyle.primary,
            emoji="ℹ️",
            row=1,
            custom_id="settings_info"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        db = interaction.client.get_db(interaction.guild_id)
        defaults = {
            'guild_name': db.get_setting('guild_name', 'Abuse'),
            'server': db.get_setting('server', 'Sirus'),
            'faction': db.get_setting('faction', 'Alliance'),
            'raid_times': db.get_setting('raid_times', '20:00 МСК'),
            'apply_description': db.get_setting('apply_description', '')
        }
        from modals.settings_modals import InfoModal
        await interaction.response.send_modal(InfoModal(defaults))


class RewardRolesButton(Button):
    def __init__(self):
        super().__init__(
            label="🎭 Роли выдачи (1/2)",
            style=ButtonStyle.primary,
            emoji="🎭",
            row=1,
            custom_id="settings_reward_roles"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        db = interaction.client.get_db(interaction.guild_id)
        defaults = {
            'member_role': db.get_setting('member_role', ''),
            'reject_role': db.get_setting('reject_role', ''),
            'blacklist_role': db.get_setting('blacklist_role', ''),
            'afk_role': db.get_setting('afk_role', ''),
            'static_role': db.get_setting('static_role', '')
        }
        from modals.settings_modals import RewardRolesModal
        await interaction.response.send_modal(RewardRolesModal(defaults))


# ═══════════════════════════════════════════════
# КНОПКИ РЯДА 2
# ═══════════════════════════════════════════════

class RewardRolesButton2(Button):
    def __init__(self):
        super().__init__(
            label="🎭 Роли выдачи (2/2)",
            style=ButtonStyle.primary,
            emoji="🎭",
            row=2,
            custom_id="settings_reward_roles2"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        db = interaction.client.get_db(interaction.guild_id)
        defaults = {'guest_role': db.get_setting('guest_role', ''), 'violator_role': db.get_setting('violator_role', '')}
        from modals.settings_modals import RewardRolesModal2
        await interaction.response.send_modal(RewardRolesModal2(defaults))


class MemberManagementButton(Button):
    def __init__(self):
        super().__init__(
            label="🔔 Участники",
            style=ButtonStyle.primary,
            emoji="🔔",
            row=2,
            custom_id="settings_members"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        from views.members import MemberManagementView
        view = MemberManagementView()
        embed = Embed(title="🔔 Управление участниками", color=Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)


class ClassRolesButton(Button):
    def __init__(self):
        super().__init__(
            label="⚔️ Классы",
            style=ButtonStyle.primary,
            emoji="⚔️",
            row=2,
            custom_id="settings_classes"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        from views.class_settings import ClassSettingsView
        view = ClassSettingsView()
        embed = Embed(title="⚔️ Классы и роли", color=Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)


# ═══════════════════════════════════════════════
# КНОПКИ РЯДА 3
# ═══════════════════════════════════════════════

class PriorityRolesButton(Button):
    def __init__(self):
        super().__init__(
            label="⭐ Приоритет",
            style=ButtonStyle.primary,
            emoji="⭐",
            row=3,
            custom_id="settings_priority"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        from views.priority import PriorityRolesSetupView
        view = PriorityRolesSetupView()
        embed = Embed(title="⭐ Приоритет ролей", color=Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)


class TasksButton(Button):
    def __init__(self):
        super().__init__(
            label="📝 Задания",
            style=ButtonStyle.primary,
            emoji="📝",
            row=3,
            custom_id="settings_tasks"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        from views.tasks import TaskSettingsView
        view = TaskSettingsView()
        embed = Embed(title="📝 Задания", color=Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)


class StaticSettingsButton(Button):
    def __init__(self):
        super().__init__(
            label="📋 Статик",
            style=ButtonStyle.primary,
            emoji="📋",
            row=3,
            custom_id="settings_static"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        from views.static import StaticSettingsView
        view = StaticSettingsView()
        embed = Embed(title="📋 Статик", color=Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)


class AbsenceLimitsButton(Button):
    def __init__(self):
        super().__init__(
            label="📅 Лимиты",
            style=ButtonStyle.secondary,
            emoji="📅",
            row=3,
            custom_id="settings_abs_limits"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        db = interaction.client.get_db(interaction.guild_id)
        limits = db.get_absence_limits()
        embed = Embed(title="📅 Лимиты отсутствий", color=Color.blue())
        embed.add_field(name="📅 Неделя", value=f"**{limits['week']}** дн.", inline=True)
        embed.add_field(name="📆 Месяц", value=f"**{limits['month']}** дн.", inline=True)
        embed.add_field(name="🔒 Подряд", value=f"**{limits['consecutive']}** дн.", inline=True)
        embed.add_field(name="⚔️ Рейдов", value=f"**{limits['raids']}** рейдов", inline=True)
        view = AbsenceLimitsView()
        await interaction.response.edit_message(embed=embed, view=view)


# ═══════════════════════════════════════════════
# КНОПКИ РЯДА 4 (МАКСИМУМ 5)
# ═══════════════════════════════════════════════

class PermissionsButton(Button):
    def __init__(self):
        super().__init__(
            label="🔐 Права",
            style=ButtonStyle.primary,
            emoji="🔐",
            row=4,
            custom_id="settings_permissions"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        from views.permissions import PermissionsSettingsView
        view = PermissionsSettingsView()
        embed = Embed(title="🔐 Права доступа", color=Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)


class VoiceButton(Button):
    def __init__(self):
        super().__init__(
            label="🎤 Войс",
            style=ButtonStyle.primary,
            emoji="🎤",
            row=4,
            custom_id="settings_voice"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        cog = interaction.client.get_cog("VoiceWelcome")
        if not cog:
            await interaction.response.send_message("❌ Модуль не загружен!", ephemeral=True)
            return
        from views.voice_welcome import VoiceSettingsView
        view = VoiceSettingsView(cog, interaction.client.db, interaction.guild_id)
        embed = cog.build_settings_embed(interaction.client.db, interaction.guild_id)
        await interaction.response.edit_message(embed=embed, view=view)


class BattleRolesButton(Button):
    def __init__(self):
        super().__init__(
            label="🎭 Роли боя",
            style=ButtonStyle.primary,
            emoji="🎭",
            row=4,
            custom_id="settings_battle_roles"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        db = interaction.client.get_db(interaction.guild_id)
        roles_info = {
            'guild_master': ('👑 Глава', db.get_setting('guild_master', '')),
            'vice_master': ('⭐ Зам. главы', db.get_setting('vice_master', '')),
            'raid_leader': ('⚔️ Рейд-лидер', db.get_setting('raid_leader', '')),
            'senior_officer_role': ('⭐ Ст. Офицер', db.get_setting('senior_officer_role', '')),
            'officer_role': ('📋 Офицер', db.get_setting('officer_role', ''))
        }
        embed = Embed(title="🎭 Роли для контроля боя", description="Настройте роли которые всегда говорят во время боя", color=Color.blue())
        for key, (name, role_id) in roles_info.items():
            role_id_int = utils.safe_int(role_id)
            role = interaction.guild.get_role(role_id_int) if role_id_int else None
            embed.add_field(name=name, value=role.mention if role else "❌ Не настроена", inline=True)
        embed.set_footer(text="Нажмите кнопку чтобы настроить роль")
        view = BattleRolesView(db)
        await interaction.response.edit_message(embed=embed, view=view)


class ReportsRolesButton(Button):
    def __init__(self):
        super().__init__(
            label="⚠️ Жалобы: роли",
            style=ButtonStyle.danger,
            emoji="⚠️",
            row=4,
            custom_id="settings_reports_roles"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        db = interaction.client.get_db(interaction.guild_id)
        reports_roles_str = db.get_setting('reports_roles', '')
        embed = Embed(title="⚠️ Роли для доступа к жалобам", description="Настройте роли, которые могут видеть каналы с жалобами", color=Color.orange())
        if reports_roles_str:
            role_ids = [int(r.strip()) for r in reports_roles_str.split(',') if r.strip().isdigit()]
            roles_text = ""
            for rid in role_ids:
                role = interaction.guild.get_role(rid)
                if role: roles_text += f"{role.mention}\n"
            embed.add_field(name="📋 Текущие роли", value=roles_text or "Роли не найдены", inline=False)
        else:
            embed.add_field(name="📋 Текущие роли", value="Стандартные (Офицер, РЛ, Зам, Глава)", inline=False)
        embed.set_footer(text="Пусто = стандартные роли")
        defaults = {'reports_roles': reports_roles_str}
        from modals.settings_modals import ReportsRolesModal
        await interaction.response.send_modal(ReportsRolesModal(defaults))


class TraineeRolesSettingsButton(Button):
    """Кнопка для настроек ролей кураторов и курсантов"""
    
    def __init__(self):
        super().__init__(
            label="🎯 Кураторы и курсанты",
            style=ButtonStyle.primary,
            emoji="🎯",
            row=4,
            custom_id="settings_trainee_roles"
        )
    
    async def callback(self, interaction: Interaction):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        db = interaction.client.get_db(interaction.guild_id)
        
        curator_role_id = db.get_setting('curator_role', '')
        trainee_role_id = db.get_setting('trainee_role', '')
        
        embed = Embed(
            title="🎯 Настройки кураторов и курсантов",
            description="Настройте роли для системы обучения РЛ",
            color=Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="👨‍🏫 Роль куратора",
            value=f"<@&{curator_role_id}>" if curator_role_id else "❌ Не настроена",
            inline=False
        )
        embed.add_field(
            name="📖 Роль курсанта (стажера)",
            value=f"<@&{trainee_role_id}>" if trainee_role_id else "❌ Не настроена",
            inline=False
        )
        embed.set_footer(text="Используйте кнопки ниже для настройки")
        
        view = TraineeRolesSettingsView()
        await interaction.response.edit_message(embed=embed, view=view)


# ═══════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ
# ═══════════════════════════════════════════════════

class GuildRolesSettingsView(View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="👑 Глава", style=ButtonStyle.primary, emoji="👑", row=0)
    async def set_gm(self, interaction: discord.Interaction, button: Button):
        from modals.settings_modals import RoleSettingModal
        await interaction.response.send_modal(RoleSettingModal("guild_master", "Глава гильдии"))

    @discord.ui.button(label="⭐ Зам", style=ButtonStyle.primary, emoji="⭐", row=0)
    async def set_vm(self, interaction: discord.Interaction, button: Button):
        from modals.settings_modals import RoleSettingModal
        await interaction.response.send_modal(RoleSettingModal("vice_master", "Зам. главы"))

    @discord.ui.button(label="⚔️ РЛ", style=ButtonStyle.primary, emoji="⚔️", row=1)
    async def set_rl(self, interaction: discord.Interaction, button: Button):
        from modals.settings_modals import RoleSettingModal
        await interaction.response.send_modal(RoleSettingModal("raid_leader", "Рейд-лидер"))

    @discord.ui.button(label="📋 Офицер", style=ButtonStyle.primary, emoji="📋", row=1)
    async def set_of(self, interaction: discord.Interaction, button: Button):
        from modals.settings_modals import RoleSettingModal
        await interaction.response.send_modal(RoleSettingModal("officer", "Офицер"))

    @discord.ui.button(label="👁️ Просмотр", style=ButtonStyle.secondary, emoji="👁️", row=2)
    async def view_roles(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        embed = Embed(title="👥 Роли гильдии", color=Color.blue())
        def format_roles(key, default="❌"):
            ids_str = db.get_setting(key, '')
            if not ids_str: return default
            ids = [r.strip() for r in ids_str.split(',') if r.strip().isdigit()]
            mentions = []
            for rid in ids:
                role = interaction.guild.get_role(int(rid))
                if role: mentions.append(role.mention)
            return ', '.join(mentions) if mentions else default
        for key, name in [('guild_master', '👑 Глава'), ('vice_master', '⭐ Зам'), ('raid_leader', '⚔️ РЛ'), ('officer', '📋 Офицер')]:
            embed.add_field(name=name, value=format_roles(key), inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔙 Назад", style=ButtonStyle.secondary, emoji="🔙", row=2)
    async def back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(embed=Embed(title="⚙️ Панель управления", description="Выберите раздел:", color=Color.blue()), view=SettingsView())


class BattleRolesView(View):
    def __init__(self, db):
        super().__init__(timeout=120)
        self.db = db

    @discord.ui.button(label="👑 Глава", style=ButtonStyle.primary, emoji="👑", row=0)
    async def set_gm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BattleRoleModal(self.db, 'guild_master', '👑 Глава гильдии'))

    @discord.ui.button(label="⭐ Зам", style=ButtonStyle.primary, emoji="⭐", row=0)
    async def set_vm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BattleRoleModal(self.db, 'vice_master', '⭐ Зам. главы'))

    @discord.ui.button(label="⚔️ РЛ", style=ButtonStyle.primary, emoji="⚔️", row=1)
    async def set_rl(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BattleRoleModal(self.db, 'raid_leader', '⚔️ Рейд-лидер'))

    @discord.ui.button(label="⭐ Ст. Офицер", style=ButtonStyle.primary, emoji="⭐", row=1)
    async def set_sr(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BattleRoleModal(self.db, 'senior_officer_role', '⭐ Ст. Офицер'))

    @discord.ui.button(label="📋 Офицер", style=ButtonStyle.primary, emoji="📋", row=2)
    async def set_of(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BattleRoleModal(self.db, 'officer_role', '📋 Офицер'))

    @discord.ui.button(label="🔙 Назад", style=ButtonStyle.secondary, emoji="🔙", row=2)
    async def back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(embed=Embed(title="⚙️ Панель управления", description="Выберите раздел:", color=Color.blue()), view=SettingsView())


class BattleRoleModal(Modal):
    def __init__(self, db, key: str, title: str):
        super().__init__(title=title)
        self.db = db
        self.key = key
        current = db.get_setting(key, '')
        self.add_item(TextInput(label="ID роли Discord", placeholder="123456789", default=current, required=False, max_length=20))

    async def on_submit(self, interaction: discord.Interaction):
        role_id = self.children[0].value.strip()
        if role_id:
            if not role_id.isdigit():
                await interaction.response.send_message("❌ Числовой ID!", ephemeral=True)
                return
            role = interaction.guild.get_role(int(role_id))
            if not role:
                await interaction.response.send_message("❌ Роль не найдена!", ephemeral=True)
                return
            self.db.set_setting(self.key, role_id)
            await interaction.response.send_message(f"✅ {role.mention}", ephemeral=True)
        else:
            self.db.set_setting(self.key, '')
            await interaction.response.send_message("✅ Сброшено", ephemeral=True)
        
        await update_apply_embed(interaction)


class AbsenceLimitsView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.select(placeholder="Выберите лимит", options=[
        discord.SelectOption(label="📅 Лимит в неделю", value="week"),
        discord.SelectOption(label="📆 Лимит в месяц", value="month"),
        discord.SelectOption(label="🔒 Лимит подряд", value="consecutive"),
        discord.SelectOption(label="⚔️ Лимит рейдов", value="raids"),
    ], custom_id="select_absence_limit")
    async def select_limit(self, interaction: discord.Interaction, select: Select):
        limit_type = interaction.data['values'][0]
        names = {
            'week': ('📅 Неделя', 'absence_limit_week', 'дней', '3'),
            'month': ('📆 Месяц', 'absence_limit_month', 'дней', '10'),
            'consecutive': ('🔒 Подряд', 'absence_limit_consecutive', 'дней', '14'),
            'raids': ('⚔️ Рейдов', 'absence_limit_raids', 'рейдов', '3'),
        }
        name, key, unit, default = names[limit_type]
        db = interaction.client.get_db(interaction.guild_id)
        current = db.get_setting(key, default)
        await interaction.response.send_modal(AbsenceLimitModal(limit_type, name, key, unit, current))

    @discord.ui.button(label="🔙 Назад", style=ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(embed=Embed(title="⚙️ Панель управления", description="Выберите раздел:", color=Color.blue()), view=SettingsView())


class AbsenceLimitModal(Modal):
    def __init__(self, limit_type: str, name: str, key: str, unit: str, current: str):
        super().__init__(title=f"Изменить: {name}")
        self.key = key
        self.unit = unit
        self.add_item(TextInput(label=f"Значение ({unit}, 0=безлимит)", placeholder=f"Текущее: {current}", default=current, required=True, max_length=2))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            value = int(self.children[0].value)
            if value < 0 or value > 31: raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ От 0 до 31!", ephemeral=True)
            return
        db = interaction.client.get_db(interaction.guild_id)
        db.set_setting(self.key, str(value))
        limits = db.get_absence_limits()
        embed = Embed(title="✅ Лимит обновлён!", color=Color.green())
        embed.add_field(name="Новое значение", value=f"**{value}** {self.unit}", inline=True)
        embed.add_field(name="📊 Все лимиты", value=f"📅 Неделя: **{limits['week']}** дн.\n📆 Месяц: **{limits['month']}** дн.\n🔒 Подряд: **{limits['consecutive']}** дн.\n⚔️ Рейдов: **{limits['raids']}** рейдов", inline=False)
        await interaction.response.edit_message(embed=embed, view=AbsenceLimitsView())
        await update_apply_embed(interaction)


# ═══════════════════════════════════════════════════
# НАСТРОЙКИ РОЛЕЙ КУРАТОРОВ И КУРСАНТОВ
# ═══════════════════════════════════════════════════

class TraineeRolesSettingsView(View):
    """Панель настроек ролей кураторов и курсантов"""
    
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SetCuratorRoleButton())
        self.add_item(SetTraineeRoleButton())
        self.add_item(BackToSettingsButton())


class SetCuratorRoleButton(Button):
    """Кнопка для настройки роли куратора (через ввод ID)"""
    
    def __init__(self):
        super().__init__(
            label="👨‍🏫 Роль куратора",
            style=ButtonStyle.primary,
            emoji="👨‍🏫",
            row=0
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.db
        
        if not utils.can_manage_settings(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        await interaction.response.send_modal(RoleIdModal(interaction, "curator_role", "👨‍🏫 Роль куратора"))


class SetTraineeRoleButton(Button):
    """Кнопка для настройки роли курсанта (через ввод ID)"""
    
    def __init__(self):
        super().__init__(
            label="📖 Роль курсанта",
            style=ButtonStyle.primary,
            emoji="📖",
            row=0
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.db
        
        if not utils.can_manage_settings(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        await interaction.response.send_modal(RoleIdModal(interaction, "trainee_role", "📖 Роль курсанта"))


class RoleIdModal(Modal):
    """Модальное окно для ввода ID роли"""
    
    def __init__(self, interaction: Interaction, setting_key: str, title: str):
        super().__init__(title=f"Настройка: {title}")
        self.interaction = interaction
        self.setting_key = setting_key
        
        db = interaction.client.db
        current = db.get_setting(setting_key, '')
        
        self.role_id_input = TextInput(
            label="ID роли (или оставьте пустым для очистки)",
            placeholder="Введите числовой ID роли...",
            default=current,
            required=False,
            max_length=20
        )
        self.add_item(self.role_id_input)
    
    async def on_submit(self, interaction: Interaction):
        db = interaction.client.db
        guild = interaction.guild
        
        role_id = self.role_id_input.value.strip()
        
        if role_id:
            if not role_id.isdigit():
                await interaction.response.send_message(
                    "❌ ID должен содержать только цифры!\n"
                    "Включите режим разработчика и скопируйте ID роли.",
                    ephemeral=True
                )
                return
            
            role = guild.get_role(int(role_id))
            if not role:
                await interaction.response.send_message(
                    f"❌ Роль с ID **{role_id}** не найдена на сервере!",
                    ephemeral=True
                )
                return
            
            db.set_setting(self.setting_key, role_id)
            await interaction.response.send_message(
                f"✅ Роль **{role.name}** установлена!\n"
                f"ID: `{role_id}`",
                ephemeral=True
            )
        else:
            db.set_setting(self.setting_key, '')
            await interaction.response.send_message(
                "✅ Роль очищена!",
                ephemeral=True
            )
        
        # Обновляем эмбед
        await self.update_settings_embed(interaction)
    
    async def update_settings_embed(self, interaction: Interaction):
        db = interaction.client.db
        
        curator_role_id = db.get_setting('curator_role', '')
        trainee_role_id = db.get_setting('trainee_role', '')
        
        embed = Embed(
            title="🎯 Настройки кураторов и курсантов",
            description="Настройте роли для системы обучения РЛ",
            color=Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="👨‍🏫 Роль куратора",
            value=f"<@&{curator_role_id}>" if curator_role_id else "❌ Не настроена",
            inline=False
        )
        embed.add_field(
            name="📖 Роль курсанта (стажера)",
            value=f"<@&{trainee_role_id}>" if trainee_role_id else "❌ Не настроена",
            inline=False
        )
        embed.set_footer(text="Используйте кнопки ниже для настройки")
        
        view = TraineeRolesSettingsView()
        
        # Используем edit_original_response для обновления
        try:
            await interaction.edit_original_response(embed=embed, view=view)
        except:
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class BackToSettingsButton(Button):
    """Кнопка возврата в главные настройки"""
    
    def __init__(self):
        super().__init__(
            label="🔙 Назад",
            style=ButtonStyle.danger,
            emoji="🔙",
            row=2
        )
    
    async def callback(self, interaction: Interaction):
        view = SettingsView()
        embed = Embed(
            title="⚙️ Панель управления",
            description="Выберите раздел:",
            color=Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)