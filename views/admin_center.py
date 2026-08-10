# views/admin_center.py — ПОЛНЫЙ ИСПРАВЛЕННЫЙ ФАЙЛ

import discord
from discord.ui import View, Button, Select, Modal, TextInput
from discord import ButtonStyle, Color, Embed, TextStyle, Interaction
import utils
from datetime import datetime
import asyncio
import json
import re
from constants import CLASS_SPECS, RAID_ROLE_NAMES


class AdminCenterView(View):
    def __init__(self): 
        super().__init__(timeout=300)
        
        # Ряд 0 — ПОИСК (2 кнопки)
        self.add_item(FindCharacterButton())
        self.add_item(FindUserButton())
        
        # Ряд 1 — УПРАВЛЕНИЕ ДАННЫМИ (2 кнопки)
        self.add_item(DeleteDataButton())
        self.add_item(StatsButton())
        
        # Ряд 2 — СБРОС И ЗАКРЫТИЕ (2 кнопки)
        self.add_item(ResetAttemptsButton())
        self.add_item(CloseButton())
        
        # Ряд 3 — ПОЧИНКА И УДАЛЕНИЕ КУРСАНТА (4 кнопки)
        self.add_item(FixSupportButton())
        self.add_item(FixCompositionButton())
        self.add_item(FixApplicationButtonsButton())
        self.add_item(RemoveTraineeButton())
        
        # Ряд 4 — КУРАТОРЫ И УПРАВЛЕНИЕ РОЛЯМИ (5 кнопок)
        self.add_item(RefreshCuratorPanelButton())
        self.add_item(RefreshStudentsButton())
        self.add_item(CuratorSettingsButtonAdmin())
        self.add_item(GiveCuratorRoleButton())
        self.add_item(RemoveCuratorRoleButton())


# ============================================
# КНОПКИ РЯДА 0 — ПОИСК
# ============================================

class FindCharacterButton(Button):
    def __init__(self):
        super().__init__(
            label="🎮 Найти персонажа",
            style=ButtonStyle.primary,
            emoji="🎮",
            row=0,
            custom_id="admin_find_char"
        )
    
    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        await interaction.response.send_modal(FindCharacterModal())


class FindUserButton(Button):
    def __init__(self):
        super().__init__(
            label="👤 Найти участника",
            style=ButtonStyle.primary,
            emoji="👤",
            row=0,
            custom_id="admin_find_user"
        )
    
    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        await interaction.response.send_modal(FindUserModal())


# ============================================
# КНОПКИ РЯДА 1 — УПРАВЛЕНИЕ ДАННЫМИ
# ============================================

class DeleteDataButton(Button):
    def __init__(self):
        super().__init__(
            label="🗑️ Удалить данные",
            style=ButtonStyle.danger,
            emoji="🗑️",
            row=1,
            custom_id="admin_delete"
        )
    
    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        await interaction.response.send_modal(FindCharForDeleteModal())


class StatsButton(Button):
    def __init__(self):
        super().__init__(
            label="📊 Статистика",
            style=ButtonStyle.secondary,
            emoji="📊",
            row=1,
            custom_id="admin_stats"
        )
    
    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        guild = interaction.guild
        total_members = guild.member_count
        total_chars = db.cursor.execute('SELECT COUNT(*) FROM characters').fetchone()[0]
        pending_apps = len(db.get_pending_applications())
        total_punish = db.cursor.execute('SELECT COUNT(*) FROM punishments').fetchone()[0]
        active_abs = db.cursor.execute('SELECT COUNT(*) FROM absences WHERE status="active"').fetchone()[0]
        total_logs = db.cursor.execute('SELECT COUNT(*) FROM logs').fetchone()[0]
        total_comps = db.cursor.execute('SELECT COUNT(*) FROM raids WHERE status="active"').fetchone()[0]
        
        embed = Embed(title="📊 Статистика гильдии", color=Color.blue(), timestamp=datetime.now())
        embed.add_field(name="👥 Участники", value=str(total_members), inline=True)
        embed.add_field(name="🎮 Персонажи", value=str(total_chars), inline=True)
        embed.add_field(name="📝 Активные заявки", value=str(pending_apps), inline=True)
        embed.add_field(name="⚠️ Наказания", value=str(total_punish), inline=True)
        embed.add_field(name="📅 Активные отсутствия", value=str(active_abs), inline=True)
        embed.add_field(name="🎯 Активные составы", value=str(total_comps), inline=True)
        embed.add_field(name="📋 Логи", value=str(total_logs), inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self.parent)


# ============================================
# КНОПКИ РЯДА 2 — СБРОС И ЗАКРЫТИЕ
# ============================================

class ResetAttemptsButton(Button):
    def __init__(self):
        super().__init__(
            label="🔄 Сброс попыток",
            style=ButtonStyle.secondary,
            emoji="🔄",
            row=2,
            custom_id="admin_reset"
        )
    
    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        await interaction.response.send_modal(FindCharForResetModal())


class CloseButton(Button):
    def __init__(self):
        super().__init__(
            label="🔙 Закрыть",
            style=ButtonStyle.danger,
            emoji="🔙",
            row=2,
            custom_id="admin_close"
        )
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="🔒 Админ-центр закрыт.", embed=None, view=None)


# ============================================
# КНОПКИ РЯДА 3 — ПОЧИНКА И УДАЛЕНИЕ КУРСАНТА
# ============================================

class FixSupportButton(Button):
    def __init__(self):
        super().__init__(
            label="🛠️ Починить техподдержку",
            style=ButtonStyle.secondary,
            emoji="🛠️",
            row=3,
            custom_id="admin_fix_support"
        )
    
    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        fixed = 0
        
        try:
            reports = db.cursor.execute(
                'SELECT id, user_id, channel_id FROM support_reports WHERE status = "open"'
            ).fetchall()
            
            for row in reports:
                report_id, user_id, channel_id = row[0], row[1], row[2]
                channel = interaction.guild.get_channel(channel_id)
                if not channel:
                    continue
                
                async for msg in channel.history(limit=20):
                    if msg.author == interaction.client.user and msg.embeds:
                        embed = msg.embeds[0]
                        if embed.title and ("Баг-репорт" in embed.title or "Обращение" in embed.title or "Техподдержка" in embed.title):
                            from views.characters import SupportView
                            view = SupportView(report_id, user_id)
                            interaction.client.add_view(view)
                            await msg.edit(view=view)
                            fixed += 1
                            break
        except:
            pass
        
        if fixed == 0:
            for channel in interaction.guild.text_channels:
                if "баг" in channel.name.lower() or "🛠️" in channel.name:
                    async for msg in channel.history(limit=10):
                        if msg.author == interaction.client.user and msg.embeds:
                            embed = msg.embeds[0]
                            if embed.title and ("Баг-репорт" in embed.title or "Обращение" in embed.title or "Техподдержка" in embed.title):
                                match = re.search(r'баг-(\d+)', channel.name)
                                report_id = int(match.group(1)) if match else 0
                                user_match = re.search(r'<@!?(\d+)>', embed.description or "")
                                user_id = int(user_match.group(1)) if user_match else 0
                                
                                from views.characters import SupportView
                                view = SupportView(report_id, user_id)
                                interaction.client.add_view(view)
                                await msg.edit(view=view)
                                fixed += 1
                                break
        
        if fixed > 0:
            await interaction.followup.send(
                f"✅ Исправлено каналов: **{fixed}**\n"
                f"Зайдите в канал и нажмите **✅ Решено** чтобы закрыть!",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ Каналы техподдержки не найдены!\n"
                "Удалите канал вручную (ПКМ → Удалить канал).",
                ephemeral=True
            )


class FixCompositionButton(Button):
    def __init__(self):
        super().__init__(
            label="🎯 Починить кнопки составов",
            style=ButtonStyle.secondary,
            emoji="🎯",
            row=3,
            custom_id="admin_fix_composition"
        )
    
    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        channel_id = utils.safe_int(db.get_setting('composition_control_channel', ''))
        if not channel_id:
            await interaction.followup.send("❌ Канал управления составами не настроен!", ephemeral=True)
            return
        
        channel = interaction.guild.get_channel(channel_id)
        if not channel:
            await interaction.followup.send("❌ Канал не найден!", ephemeral=True)
            return
        
        try:
            async for msg in channel.history(limit=50):
                if msg.author == interaction.client.user:
                    await msg.delete()
        except:
            pass
        
        embed = Embed(
            title="🎯 Управление составами",
            description="Создавайте и управляйте составами рейдов.",
            color=Color.blue()
        )
        
        from views.compositions import CompositionCreateButton
        view = CompositionCreateButton()
        msg = await channel.send(embed=embed, view=view)
        db.save_message('composition_button', channel.id, msg.id)
        
        await interaction.followup.send(
            f"✅ Кнопки составов восстановлены в {channel.mention}!",
            ephemeral=True
        )


class FixApplicationButtonsButton(Button):
    def __init__(self):
        super().__init__(
            label="📝 Починить кнопки заявок",
            style=ButtonStyle.secondary,
            emoji="📝",
            row=3,
            custom_id="admin_fix_apps"
        )
    
    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        from views.applications import ApplicationReviewView
        import json
        
        pending_apps = db.cursor.execute('''
            SELECT id, user_id, channel_id, message_id, data
            FROM applications
            WHERE status = "pending"
        ''').fetchall()
        
        if not pending_apps:
            await interaction.followup.send("📭 Нет активных заявок для восстановления.", ephemeral=True)
            return
        
        total = len(pending_apps)
        restored = 0
        failed = 0
        details = []
        
        for app_id, user_id, channel_id, message_id, data_raw in pending_apps:
            channel = interaction.guild.get_channel(channel_id)
            if not channel:
                failed += 1
                details.append(f"❌ Заявка #{app_id}: канал не найден")
                continue
            
            data = {}
            if isinstance(data_raw, str):
                try:
                    data = json.loads(data_raw)
                except:
                    pass
            elif isinstance(data_raw, dict):
                data = data_raw
            
            view = ApplicationReviewView(channel_id, user_id, app_id, data)
            found = False
            
            if message_id:
                try:
                    msg = await channel.fetch_message(message_id)
                    if msg.author == interaction.client.user and msg.embeds:
                        interaction.client.add_view(view, message_id=msg.id)
                        await msg.edit(view=view)
                        found = True
                        restored += 1
                        details.append(f"✅ Заявка #{app_id} восстановлена по message_id")
                except discord.NotFound:
                    pass
                except Exception as e:
                    details.append(f"⚠️ Заявка #{app_id}: ошибка при message_id – {e}")
            
            if not found:
                try:
                    async for msg in channel.history(limit=30):
                        if msg.author == interaction.client.user and msg.embeds:
                            embed_title = msg.embeds[0].title if msg.embeds else ""
                            if "Заявка" in embed_title or "📝" in embed_title:
                                interaction.client.add_view(view, message_id=msg.id)
                                await msg.edit(view=view)
                                db.cursor.execute('UPDATE applications SET message_id = ? WHERE id = ?', (msg.id, app_id))
                                db.conn.commit()
                                found = True
                                restored += 1
                                details.append(f"✅ Заявка #{app_id} восстановлена из истории (сообщение {msg.id})")
                                break
                except Exception as e:
                    details.append(f"⚠️ Заявка #{app_id}: ошибка при поиске в истории – {e}")
            
            if not found:
                failed += 1
                details.append(f"❌ Заявка #{app_id}: сообщение с кнопками не найдено")
        
        embed = Embed(
            title="📝 Результат восстановления заявок",
            description=f"**Всего заявок:** {total}\n**Восстановлено:** {restored}\n**Не удалось:** {failed}",
            color=Color.green() if restored > 0 else Color.orange(),
            timestamp=datetime.now()
        )
        
        if details:
            embed.add_field(
                name="📋 Детали",
                value="\n".join(details[:10]) + (f"\n...и ещё {len(details)-10}" if len(details) > 10 else ""),
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


class RemoveTraineeButton(Button):
    def __init__(self):
        super().__init__(
            label="🗑️ Удалить курсанта",
            style=ButtonStyle.danger,
            emoji="🗑️",
            row=3,
            custom_id="admin_remove_trainee"
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        trainees = db.cursor.execute('SELECT user_id FROM trainees WHERE status = "active"').fetchall()
        if not trainees:
            await interaction.response.send_message("❌ Нет активных курсантов для удаления.", ephemeral=True)
            return
        
        embed = Embed(
            title="🗑️ Удаление курсанта",
            description="Выберите курсанта, которого хотите удалить из системы обучения:",
            color=Color.red()
        )
        
        view = SelectTraineeForRemoveView(interaction, trainees)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ============================================
# КНОПКИ РЯДА 4 — КУРАТОРЫ И УПРАВЛЕНИЕ РОЛЯМИ
# ============================================

class RefreshCuratorPanelButton(Button):
    def __init__(self):
        super().__init__(
            label="🔄 Обновить панель кураторов",
            style=ButtonStyle.primary,
            emoji="🔄",
            row=4,
            custom_id="admin_refresh_curator"
        )
    
    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        panel_data = db.get_curator_message(interaction.guild_id, 'panel')
        if not panel_data:
            await interaction.followup.send(
                "❌ Панель кураторов не найдена!\n"
                "Создайте ее: `/curator_panel_setup`",
                ephemeral=True
            )
            return
        
        channel = interaction.guild.get_channel(panel_data['channel_id'])
        if not channel:
            await interaction.followup.send("❌ Канал не найден!", ephemeral=True)
            return
        
        try:
            message = await channel.fetch_message(panel_data['message_id'])
        except:
            await interaction.followup.send("❌ Сообщение не найдено!", ephemeral=True)
            return
        
        from views.curator import CuratorPanelPersistentView
        from utils.curator_utils import create_curator_panel_embed
        
        embed = create_curator_panel_embed(interaction.guild, db)
        view = CuratorPanelPersistentView()
        
        await message.edit(embed=embed, view=view)
        
        db.add_curator_log(
            "🔄 Обновлена панель кураторов (из админ-центра)",
            interaction.user.id,
            f"Канал: {channel.name}",
            channel.id
        )
        
        await interaction.followup.send(
            f"✅ Панель кураторов обновлена в {channel.mention}!",
            ephemeral=True
        )


class RefreshStudentsButton(Button):
    def __init__(self):
        super().__init__(
            label="🔄 Обновить учеников",
            style=ButtonStyle.primary,
            emoji="🔄",
            row=4,
            custom_id="admin_refresh_students"
        )
    
    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        from utils.curator_utils import create_students_overview_embed, create_activity_embed
        
        students_msg = db.get_curator_channel_message(interaction.guild_id, 'students')
        if students_msg:
            channel = interaction.guild.get_channel(students_msg['channel_id'])
            if channel:
                try:
                    msg = await channel.fetch_message(students_msg['message_id'])
                    embed = create_students_overview_embed(interaction.guild, db)
                    await msg.edit(embed=embed)
                except:
                    pass
        
        activity_msg = db.get_curator_channel_message(interaction.guild_id, 'activity')
        if activity_msg:
            channel = interaction.guild.get_channel(activity_msg['channel_id'])
            if channel:
                try:
                    msg = await channel.fetch_message(activity_msg['message_id'])
                    embed = create_activity_embed(db)
                    await msg.edit(embed=embed)
                except:
                    pass
        
        db.add_curator_log(
            "🔄 Обновлен список учеников (из админ-центра)",
            interaction.user.id,
            "Обновлены обзор и активности",
            None
        )
        
        await interaction.followup.send("✅ Список учеников обновлен!", ephemeral=True)


class CuratorSettingsButtonAdmin(Button):
    def __init__(self):
        super().__init__(
            label="⚙️ Настройки кураторов",
            style=ButtonStyle.secondary,
            emoji="⚙️",
            row=4,
            custom_id="admin_curator_settings"
        )
    
    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        curator_role_id = db.get_setting('curator_role', '')
        curator_channel_id = db.get_setting('curator_channel', '')
        
        embed = Embed(
            title="⚙️ Настройки кураторов",
            description="Текущие настройки системы кураторов",
            color=Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="👨‍🏫 Роль куратора",
            value=f"<@&{curator_role_id}>" if curator_role_id else "❌ Не настроена",
            inline=False
        )
        embed.add_field(
            name="📢 Канал кураторов",
            value=f"<#{curator_channel_id}>" if curator_channel_id else "❌ Не настроен",
            inline=False
        )
        
        embed.set_footer(text="Используйте /settings → Кураторы для изменения")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class GiveCuratorRoleButton(Button):
    def __init__(self):
        super().__init__(
            label="👨‍🏫 Выдать роль куратора",
            style=ButtonStyle.success,
            emoji="👨‍🏫",
            row=4,
            custom_id="admin_give_curator"
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        curator_role_id = db.get_setting('curator_role', '')
        if not curator_role_id:
            await interaction.response.send_message(
                "❌ Роль куратора не настроена!\n"
                "Сначала настройте роль в `/settings` → Кураторы и курсанты.",
                ephemeral=True
            )
            return
        
        embed = Embed(
            title="👨‍🏫 Выдать роль куратора",
            description="Выберите участника, которому хотите выдать роль куратора:",
            color=Color.blue()
        )
        
        view = SelectCuratorMemberView(interaction, "give")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RemoveCuratorRoleButton(Button):
    def __init__(self):
        super().__init__(
            label="👨‍🏫 Снять роль куратора",
            style=ButtonStyle.danger,
            emoji="👨‍🏫",
            row=4,
            custom_id="admin_remove_curator"
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db or not utils.can_use_admin_center(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        curator_role_id = db.get_setting('curator_role', '')
        if not curator_role_id:
            await interaction.response.send_message(
                "❌ Роль куратора не настроена!\n"
                "Сначала настройте роль в `/settings` → Кураторы и курсанты.",
                ephemeral=True
            )
            return
        
        embed = Embed(
            title="👨‍🏫 Снять роль куратора",
            description="Выберите участника, у которого хотите снять роль куратора:",
            color=Color.orange()
        )
        
        view = SelectCuratorMemberView(interaction, "remove")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ VIEW
# ============================================

class SelectTraineeForRemoveView(View):
    def __init__(self, interaction: Interaction, trainees: list):
        super().__init__(timeout=60)
        self.interaction = interaction
        
        options = []
        used_values = set()
        
        for trainee_row in trainees[:25]:
            user_id = trainee_row[0]
            
            if str(user_id) in used_values:
                continue
            used_values.add(str(user_id))
            
            member = interaction.guild.get_member(user_id)
            if member:
                options.append(discord.SelectOption(
                    label=member.display_name[:100],
                    value=str(user_id),
                    description=f"ID: {user_id}"
                ))
        
        # Если опций нет, добавляем фиктивную, но с проверкой в callback
        if not options:
            options.append(discord.SelectOption(
                label="Нет доступных курсантов",
                value="none",
                default=True
            ))
        
        select = Select(
            placeholder="Выберите курсанта для удаления...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        async def select_callback(inter: Interaction):
            user_id_str = select.values[0]
            
            if user_id_str == "none":
                await inter.response.send_message("❌ Нет доступных курсантов для удаления.", ephemeral=True)
                return
            
            user_id = int(user_id_str)
            member = inter.guild.get_member(user_id)
            if not member:
                await inter.response.send_message("❌ Участник не найден!", ephemeral=True)
                return
            
            embed = Embed(
                title="⚠️ Подтверждение удаления",
                description=f"Вы действительно хотите удалить **{member.display_name}** из системы обучения?\n\n"
                            f"Будут удалены:\n"
                            f"• Все задания курсанта\n"
                            f"• Все логи\n"
                            f"• Наказания\n"
                            f"• Снята роль курсанта (если настроена)\n\n"
                            f"Это действие нельзя отменить!",
                color=Color.red()
            )
            view = ConfirmRemoveTraineeView(member.id)
            await inter.response.edit_message(embed=embed, view=view)
        
        select.callback = select_callback
        self.add_item(select)
        self.add_item(Button(
            label="❌ Отмена",
            style=ButtonStyle.danger,
            custom_id="cancel"
        ))

class ConfirmRemoveTraineeView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=30)
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Да, удалить", style=ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        member = interaction.guild.get_member(self.user_id)
        if not member:
            await interaction.response.send_message("❌ Участник не найден!", ephemeral=True)
            return
        
        from utils.trainee_utils import remove_trainee_completely
        success = await remove_trainee_completely(member, db)
        
        if success:
            embed = Embed(
                title="✅ Курсант удалён",
                description=f"**{member.mention}** удалён из системы обучения.\n"
                            f"Все данные очищены.",
                color=Color.green()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            
            db.add_log(
                "🗑️ Удалён курсант",
                interaction.user.id,
                member.id,
                "Удалён через админ-панель"
            )
            
            try:
                await member.send(embed=Embed(
                    title="🗑️ Вы удалены из системы обучения",
                    description=f"**Сервер:** {interaction.guild.name}\n"
                                f"**Удалил:** {interaction.user.mention}\n\n"
                                f"Ваши данные (задания, логи, наказания) удалены.",
                    color=Color.red()
                ))
            except:
                pass
        else:
            await interaction.response.send_message(
                f"❌ Не удалось удалить {member.mention}!\n"
                "Проверьте логи.",
                ephemeral=True
            )
    
    @discord.ui.button(label="❌ Отмена", style=ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: Interaction, button: Button):
        await interaction.response.edit_message(content="❌ Отменено.", view=None)


class SelectCuratorMemberView(View):
    def __init__(self, interaction: Interaction, action: str):
        super().__init__(timeout=60)
        self.action = action
        self.interaction = interaction
        
        options = []
        for member in interaction.guild.members:
            if not member.bot:
                options.append(discord.SelectOption(
                    label=member.display_name[:100],
                    value=str(member.id),
                    description=f"ID: {member.id}"
                ))
        
        options = options[:25]
        
        select = Select(
            placeholder="Выберите участника...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        async def select_callback(inter: Interaction):
            user_id = int(select.values[0])
            member = inter.guild.get_member(user_id)
            if not member:
                await inter.response.send_message("❌ Участник не найден!", ephemeral=True)
                return
            
            if self.action == "give":
                await self.give_curator_role(inter, member)
            else:
                await self.remove_curator_role(inter, member)
        
        select.callback = select_callback
        self.add_item(select)
        self.add_item(Button(
            label="❌ Отмена",
            style=ButtonStyle.danger,
            custom_id="cancel"
        ))
    
    async def give_curator_role(self, interaction: Interaction, member: discord.Member):
        db = interaction.client.get_db(interaction.guild_id)
        
        from utils.trainee_utils import assign_curator_role
        success = await assign_curator_role(member, db)
        
        if success:
            db.add_log(
                "👨‍🏫 Выдана роль куратора (из админ-центра)",
                interaction.user.id,
                member.id,
                "Выдано через админ-панель"
            )
            embed = Embed(
                title="✅ Роль куратора выдана!",
                description=f"**Участник:** {member.mention}",
                color=Color.green()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            
            try:
                embed_dm = Embed(
                    title="👨‍🏫 Вы назначены куратором!",
                    description=(
                        f"**Сервер:** {interaction.guild.name}\n"
                        f"**Назначил:** {interaction.user.mention}\n\n"
                        f"Теперь вы можете управлять обучением РЛ через панель куратора."
                    ),
                    color=Color.blue()
                )
                await member.send(embed=embed_dm)
            except:
                pass
        else:
            await interaction.response.send_message(
                f"❌ Не удалось выдать роль {member.mention}!\n"
                "Проверьте, что роль существует и у бота есть права.",
                ephemeral=True
            )
    
    async def remove_curator_role(self, interaction: Interaction, member: discord.Member):
        db = interaction.client.get_db(interaction.guild_id)
        
        from utils.trainee_utils import remove_curator_role
        success = await remove_curator_role(member, db)
        
        if success:
            db.add_log(
                "👨‍🏫 Снята роль куратора (из админ-центра)",
                interaction.user.id,
                member.id,
                "Снято через админ-панель"
            )
            embed = Embed(
                title="✅ Роль куратора снята!",
                description=f"**Участник:** {member.mention}",
                color=Color.orange()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            
            try:
                embed_dm = Embed(
                    title="👨‍🏫 Вы сняты с должности куратора",
                    description=(
                        f"**Сервер:** {interaction.guild.name}\n"
                        f"**Снял:** {interaction.user.mention}"
                    ),
                    color=Color.orange()
                )
                await member.send(embed=embed_dm)
            except:
                pass
        else:
            await interaction.response.send_message(
                f"❌ Не удалось снять роль с {member.mention}!\n"
                "Проверьте, что роль существует и у бота есть права.",
                ephemeral=True
            )


# ============================================
# МОДАЛЬНЫЕ ОКНА
# ============================================

class FindCharacterModal(Modal):
    def __init__(self):
        super().__init__(title="🎮 Поиск персонажа")
        self.add_item(TextInput(label="Имя персонажа", placeholder="Введите имя персонажа", required=True, max_length=50))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: 
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        query = self.children[0].value.strip().lower()
        found = []
        
        for member in interaction.guild.members:
            chars = db.get_user_characters(member.id)
            for char in chars:
                if query in char['character_name'].lower():
                    found.append((member, char))
        
        if not found:
            await interaction.response.send_message("❌ Персонаж не найден!", ephemeral=True)
            return
        
        if len(found) == 1:
            member, char = found[0]
            embed = build_character_embed(member, char, db)
            view = UserActionsView(member.id, member.display_name)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            options = []
            for member, char in found[:25]:
                options.append(discord.SelectOption(
                    label=f"{char['character_name']} ({member.display_name})",
                    value=str(char['id']),
                    description=f"{char['class_spec']} | {char.get('item_level', 0)} iLvl",
                    emoji="⭐" if char['is_main'] else "🔄"
                ))
            
            select = Select(placeholder=f"Найдено {len(found)} персонажей. Выберите:", options=options, custom_id="select_found_char")
            
            async def sel_callback(interaction: discord.Interaction):
                char_id = int(interaction.data['values'][0])
                char = db.get_character_by_id(char_id)
                if char:
                    owner = None
                    for m in interaction.guild.members:
                        user_chars = db.get_user_characters(m.id)
                        if any(c['id'] == char_id for c in user_chars):
                            owner = m
                            break
                    if owner:
                        embed = build_character_embed(owner, char, db)
                        view = UserActionsView(owner.id, owner.display_name)
                        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            select.callback = sel_callback
            v = View(timeout=30); v.add_item(select)
            await interaction.response.send_message(f"🎮 Найдено {len(found)} персонажей. Выберите:", view=v, ephemeral=True)


class FindUserModal(Modal):
    def __init__(self):
        super().__init__(title="👤 Поиск участника")
        self.add_item(TextInput(label="ID или @имя", placeholder="123456789 или @Имя", required=True, max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: 
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        query = self.children[0].value.strip()
        user = None
        if query.isdigit():
            user = interaction.guild.get_member(int(query))
        else:
            query = query.replace('@', '').lower()
            for member in interaction.guild.members:
                if query in member.display_name.lower() or query in member.name.lower():
                    user = member; break
        
        if not user:
            await interaction.response.send_message("❌ Участник не найден!", ephemeral=True)
            return
        
        await show_user_info(interaction, user, db)


class FindCharForDeleteModal(Modal):
    def __init__(self):
        super().__init__(title="🗑️ Поиск персонажа")
        self.add_item(TextInput(label="Имя персонажа", placeholder="Введите имя персонажа", required=True, max_length=50))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: 
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        query = self.children[0].value.strip().lower()
        found = []
        
        for member in interaction.guild.members:
            chars = db.get_user_characters(member.id)
            for char in chars:
                if query in char['character_name'].lower():
                    found.append((member, char))
        
        if not found:
            await interaction.response.send_message("❌ Персонаж не найден!", ephemeral=True)
            return
        
        if len(found) == 1:
            member, char = found[0]
            view = DeleteUserDataView(member.id, member.display_name)
            embed = Embed(title="🗑️ Удаление данных", description=f"**Пользователь:** {member.mention}\n**Персонаж:** {char['character_name']}\n\nВыберите, что удалить:", color=Color.red())
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            user_chars = {}
            for member, char in found:
                if member.id not in user_chars:
                    user_chars[member.id] = {'member': member, 'chars': []}
                user_chars[member.id]['chars'].append(char)
            
            options = []
            for user_id, data in user_chars.items():
                member = data['member']
                chars_list = data['chars']
                char_names = ', '.join([c['character_name'] for c in chars_list[:3]])
                if len(chars_list) > 3: char_names += f" и ещё {len(chars_list) - 3}"
                options.append(discord.SelectOption(label=f"{member.display_name}", value=str(user_id), description=f"Персонажи: {char_names}", emoji="👤"))
            
            select = Select(placeholder="Выберите пользователя для удаления данных", options=options[:25], custom_id="select_user_delete")
            
            async def sel_callback(interaction: discord.Interaction):
                user_id = int(interaction.data['values'][0])
                member = interaction.guild.get_member(user_id)
                if member:
                    view = DeleteUserDataView(user_id, member.display_name)
                    embed = Embed(title="🗑️ Удаление данных", description=f"**Пользователь:** {member.mention}\n\nВыберите, что удалить:", color=Color.red())
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
            select.callback = sel_callback
            v = View(timeout=30); v.add_item(select)
            await interaction.response.send_message(f"Найдено {len(user_chars)} пользователей. Выберите:", view=v, ephemeral=True)


class FindCharForResetModal(Modal):
    def __init__(self):
        super().__init__(title="🔄 Сброс попыток")
        self.add_item(TextInput(label="Имя персонажа", placeholder="Введите имя персонажа", required=True, max_length=50))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: 
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        query = self.children[0].value.strip().lower()
        found_users = {}
        
        for member in interaction.guild.members:
            chars = db.get_user_characters(member.id)
            for char in chars:
                if query in char['character_name'].lower() and member.id not in found_users:
                    found_users[member.id] = (member, char)
        
        if not found_users:
            await interaction.response.send_message("❌ Персонаж не найден!", ephemeral=True)
            return
        
        found_list = list(found_users.values())
        
        if len(found_list) == 1:
            member, char = found_list[0]
            db.reset_application_attempts(member.id)
            db.add_log("🔄 Сброс попыток", interaction.user.id, member.id, f"Через персонажа {char['character_name']}")
            await interaction.response.send_message(f"✅ Попытки для **{member.display_name}** сброшены!", ephemeral=True, delete_after=5)
        else:
            options = []
            for member, char in found_list[:25]:
                options.append(discord.SelectOption(label=f"{member.display_name}", value=str(member.id), description=f"Персонаж: {char['character_name']}", emoji="🔄"))
            
            select = Select(placeholder="Выберите пользователя для сброса попыток", options=options, custom_id="select_user_reset")
            
            async def sel_callback(interaction: discord.Interaction):
                user_id = int(interaction.data['values'][0])
                member = interaction.guild.get_member(user_id)
                if member:
                    db.reset_application_attempts(user_id)
                    db.add_log("🔄 Сброс попыток", interaction.user.id, user_id)
                    await interaction.response.send_message(f"✅ Попытки для **{member.display_name}** сброшены!", ephemeral=True, delete_after=5)
            
            select.callback = sel_callback
            v = View(timeout=30); v.add_item(select)
            await interaction.response.send_message(f"Найдено {len(found_list)} пользователей. Выберите:", view=v, ephemeral=True)


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

async def show_user_info(interaction, user, db):
    chars = db.get_user_characters(user.id)
    main_char = db.get_main_character(user.id)
    punishments = sum(db.get_total_violations_by_character(c['id']) for c in chars)
    absences = db.cursor.execute('SELECT COUNT(*) FROM absences WHERE user_id=?', (user.id,)).fetchone()[0]
    apps = db.cursor.execute('SELECT COUNT(*) FROM applications WHERE user_id=?', (user.id,)).fetchone()[0]
    static_requests = db.cursor.execute('SELECT COUNT(*) FROM static_requests WHERE user_id=?', (user.id,)).fetchone()[0]
    
    embed = Embed(title=f"👤 {user.display_name}", color=Color.blue(), timestamp=datetime.now())
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="🆔 ID", value=str(user.id), inline=True)
    embed.add_field(name="📅 На сервере с", value=user.joined_at.strftime('%d.%m.%Y') if user.joined_at else "Н/Д", inline=True)
    
    if main_char:
        from views.characters import auto_fix_roles
        main_char = auto_fix_roles(db, main_char)
        raid_role = utils.format_raid_roles(main_char.get('raid_role', 'mdd'))
        embed.add_field(name="⭐ Основной", value=f"{main_char['character_name']} ({main_char['class_spec']})\n💎 {main_char['item_level']} iLvl | {raid_role}", inline=False)
    
    embed.add_field(name="🎮 Персонажей", value=str(len(chars)), inline=True)
    embed.add_field(name="⚠️ Наказаний", value=str(punishments), inline=True)
    embed.add_field(name="📅 Отсутствий", value=str(absences), inline=True)
    embed.add_field(name="📝 Заявок", value=str(apps), inline=True)
    embed.add_field(name="📋 Статик заявок", value=str(static_requests), inline=True)
    
    view = UserActionsView(user.id, user.display_name)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


def build_character_embed(member, char, db=None):
    from views.characters import auto_fix_roles
    if db: char = auto_fix_roles(db, char)
    
    raid_role_text = utils.format_raid_roles(char.get('raid_role', 'mdd'))
    embed = Embed(title=f"🎮 {char['character_name']}", color=Color.blue(), timestamp=datetime.now())
    embed.add_field(name="👤 Владелец", value=member.mention if member else "Неизвестно", inline=True)
    embed.add_field(name="🆔 ID персонажа", value=str(char['id']), inline=True)
    embed.add_field(name="⚔️ Класс", value=char['class_spec'], inline=True)
    embed.add_field(name="🎯 Специализации", value=char.get('specialization', 'Не указана'), inline=True)
    embed.add_field(name="💎 iLvl", value=str(char.get('item_level', 0)), inline=True)
    embed.add_field(name="🎭 Роли", value=raid_role_text, inline=True)
    embed.add_field(name="📌 Тип", value="⭐ Основной" if char['is_main'] else "🔄 Твинк", inline=True)
    if char.get('profile_url'): embed.add_field(name="🔗 Профиль", value=f"[Sirus]({char['profile_url']})", inline=False)
    return embed


# ============================================
# VIEW С ДЕЙСТВИЯМИ
# ============================================

class UserActionsView(View):
    def __init__(self, user_id: int, user_name: str):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.user_name = user_name

    @discord.ui.button(label="✏️ Редактировать", style=ButtonStyle.primary, emoji="✏️", row=0, custom_id="edit_user_char")
    async def edit_char(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        
        chars = db.get_user_characters(self.user_id)
        if not chars: await interaction.response.send_message(f"❌ Нет персонажей!", ephemeral=True); return
        
        options = []
        for char in chars[:25]:
            from views.characters import auto_fix_roles
            char = auto_fix_roles(db, char)
            specs = char.get('specialization', 'Не указана')
            options.append(discord.SelectOption(label=f"{'⭐' if char['is_main'] else '🔄'} {char['character_name']}", value=str(char['id']), description=f"{char['class_spec']} | {specs} | 💎{char.get('item_level', 0)}", emoji="⭐" if char['is_main'] else "🔄"))
        
        select = Select(placeholder="Выберите персонажа для редактирования", options=options, custom_id="select_char_edit_admin")
        
        async def char_callback(interaction: discord.Interaction):
            char_id = int(interaction.data['values'][0])
            char = db.get_character_by_id(char_id)
            if char:
                clean_char = {'id': char['id'], 'character_name': str(char.get('character_name', 'Unknown')), 'item_level': int(char.get('item_level', 0)), 'profile_url': str(char.get('profile_url', '')), 'class_spec': str(char.get('class_spec', '')), 'specialization': str(char.get('specialization', '')), 'is_main': bool(char.get('is_main', False)), 'raid_role': str(char.get('raid_role', 'mdd')), 'user_id': self.user_id}
                await interaction.response.send_modal(EditCharacterAdminModal(clean_char))
        
        select.callback = char_callback
        v = View(timeout=30); v.add_item(select)
        await interaction.response.send_message("Выберите персонажа:", view=v, ephemeral=True)

    @discord.ui.button(label="🗑️ Удалить данные", style=ButtonStyle.danger, emoji="🗑️", row=0, custom_id="del_user_data")
    async def delete_data(self, interaction: discord.Interaction, button: Button):
        view = DeleteUserDataView(self.user_id, self.user_name)
        embed = Embed(title="🗑️ Удаление данных", description=f"**Пользователь:** {self.user_name}\n\nВыберите, что удалить:", color=Color.red())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🎯 Специализации", style=ButtonStyle.primary, emoji="🎯", row=1, custom_id="manage_specs_admin")
    async def manage_specs(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        
        chars = db.get_user_characters(self.user_id)
        if not chars: await interaction.response.send_message(f"❌ Нет персонажей!", ephemeral=True); return
        
        options = []
        for char in chars[:25]:
            from views.characters import auto_fix_roles
            char = auto_fix_roles(db, char)
            specs = char.get('specialization', 'Не указана')
            options.append(discord.SelectOption(label=f"{'⭐' if char['is_main'] else '🔄'} {char['character_name']}", value=str(char['id']), description=f"{char['class_spec']} | Спеки: {specs}", emoji="⭐" if char['is_main'] else "🔄"))
        
        select = Select(placeholder="Выберите персонажа", options=options, custom_id="select_char_specs_admin")
        
        async def char_callback(interaction: discord.Interaction):
            char_id = int(interaction.data['values'][0])
            char = db.get_character_by_id(char_id)
            if char:
                from views.characters import auto_fix_roles
                char = auto_fix_roles(db, char)
                current_specs = char.get('specialization', '').split(', ')
                current_specs = [s.strip() for s in current_specs if s.strip()]
                class_name = char['class_spec']
                all_specs = CLASS_SPECS.get(class_name, [])
                
                spec_options = []
                for spec in current_specs:
                    role_key = db.get_setting(f"spec_role_{class_name}_{spec}", 'mdd')
                    role_name = RAID_ROLE_NAMES.get(role_key, role_key)
                    spec_options.append(discord.SelectOption(label=f"🗑️ {spec}", value=f"remove_{spec}", description=f"Роль: {role_name}", emoji="🗑️"))
                
                for spec in all_specs:
                    if spec not in current_specs:
                        role_key = db.get_setting(f"spec_role_{class_name}_{spec}", 'mdd')
                        role_name = RAID_ROLE_NAMES.get(role_key, role_key)
                        spec_options.append(discord.SelectOption(label=f"➕ {spec}", value=f"add_{spec}", description=f"Роль: {role_name}", emoji="➕"))
                
                if not spec_options: await interaction.response.send_message("❌ Нет доступных специализаций!", ephemeral=True); return
                
                spec_select = Select(placeholder=f"Управление спеками {char['character_name']}", options=spec_options[:25], custom_id="manage_specs_select_admin")
                
                async def spec_callback(interaction: discord.Interaction):
                    action_value = interaction.data['values'][0]
                    if action_value.startswith("add_"):
                        new_spec = action_value[4:]; current_specs.append(new_spec); action_text = f"добавлена **{new_spec}**"
                    elif action_value.startswith("remove_"):
                        spec_to_remove = action_value[7:]
                        if len(current_specs) <= 1: await interaction.response.send_message("⚠️ Нельзя оставить персонажа без специализации!", ephemeral=True); return
                        current_specs.remove(spec_to_remove); action_text = f"удалена **{spec_to_remove}**"
                    else: return
                    
                    new_specs_str = ', '.join(current_specs) if current_specs else 'Не указана'
                    all_roles = []
                    for spec in current_specs:
                        role = db.get_setting(f"spec_role_{class_name}_{spec}", 'mdd')
                        if role not in all_roles: all_roles.append(role)
                    new_roles = ','.join(all_roles) if all_roles else 'mdd'
                    
                    db.cursor.execute('UPDATE characters SET specialization=?, raid_role=? WHERE id=?', (new_specs_str, new_roles, char_id))
                    db.conn.commit()
                    db.add_log("🎯 Специализации изменены", interaction.user.id, self.user_id, f"#{char_id} {char['character_name']}: {action_text}")
                    
                    role_display = utils.format_raid_roles(new_roles)
                    await interaction.response.send_message(f"✅ Для **{char['character_name']}** {action_text}!\n📋 Специализации: **{new_specs_str}**\n🎯 Роли: **{role_display}**", ephemeral=True, delete_after=10)
                
                spec_select.callback = spec_callback
                v = View(timeout=60); v.add_item(spec_select)
                await interaction.response.send_message(f"🎯 Управление специализациями для **{char['character_name']}**\n📋 Текущие: **{', '.join(current_specs) if current_specs else 'Нет'}**\nВыберите действие:", view=v, ephemeral=True)
        
        select.callback = char_callback
        v = View(timeout=30); v.add_item(select)
        await interaction.response.send_message("Выберите персонажа:", view=v, ephemeral=True)

    @discord.ui.button(label="🔄 Сбросить попытки", style=ButtonStyle.secondary, emoji="🔄", row=1, custom_id="reset_user_attempts")
    async def reset_attempts(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        db.reset_application_attempts(self.user_id)
        db.add_log("🔄 Сброс попыток", interaction.user.id, self.user_id)
        await interaction.response.send_message(f"✅ Попытки для **{self.user_name}** сброшены!", ephemeral=True, delete_after=5)

    @discord.ui.button(label="📝 Заявки", style=ButtonStyle.secondary, emoji="📝", row=2, custom_id="user_apps")
    async def show_apps(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        
        apps = db.cursor.execute('SELECT id, status, data, created_at FROM applications WHERE user_id=? ORDER BY created_at DESC LIMIT 10', (self.user_id,)).fetchall()
        if not apps: await interaction.response.send_message(f"📭 Нет заявок!", ephemeral=True); return
        
        embed = Embed(title=f"📝 Заявки {self.user_name}", color=Color.blue())
        for app_id, status, data_json, created_at in apps:
            data = json.loads(data_json) if data_json else {}
            status_emoji = {"pending": "⏳", "accepted": "✅", "rejected": "❌", "blacklisted": "🚫"}.get(status, "❓")
            embed.add_field(name=f"#{app_id} {status_emoji}", value=f"👤 {data.get('character_name', 'Н/Д')}\n⚔️ {data.get('class_spec', 'Н/Д')}\n📅 {created_at}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🔙 Закрыть", style=ButtonStyle.secondary, emoji="🔙", row=2, custom_id="close_user_actions")
    async def close(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="🔒 Закрыто.", embed=None, view=None)


class DeleteUserDataView(View):
    def __init__(self, user_id: int, user_name: str):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.user_name = user_name

    @discord.ui.button(label="⚠️ Наказания", style=ButtonStyle.danger, emoji="⚠️", row=0, custom_id="del_user_punishments")
    async def delete_punishments(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        chars = db.get_user_characters(self.user_id)
        total_deleted = 0
        for char in chars:
            db.cursor.execute('DELETE FROM punishments WHERE character_id=?', (char['id'],))
            db.cursor.execute('DELETE FROM punishment_tasks WHERE character_id=?', (char['id'],))
            db.cursor.execute('DELETE FROM warnings WHERE character_id=?', (char['id'],))
            total_deleted += db.cursor.rowcount
        db.conn.commit()
        db.add_log("🗑️ Наказания удалены", interaction.user.id, self.user_id, "Все наказания пользователя")
        await interaction.response.send_message(f"✅ Наказания **{self.user_name}** удалены! ({total_deleted} записей)", ephemeral=True, delete_after=5)

    @discord.ui.button(label="📅 Отсутствия", style=ButtonStyle.danger, emoji="📅", row=0, custom_id="del_user_absences")
    async def delete_absences(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        db.cursor.execute('DELETE FROM absences WHERE user_id=?', (self.user_id,))
        count = db.cursor.rowcount
        db.conn.commit()
        db.add_log("🗑️ Отсутствия удалены", interaction.user.id, self.user_id)
        try:
            from views.absences import refresh_calendar_for_guild
            await refresh_calendar_for_guild(interaction.guild, db)
        except: pass
        await interaction.response.send_message(f"✅ Отсутствия **{self.user_name}** удалены! ({count} записей)", ephemeral=True, delete_after=5)

    @discord.ui.button(label="📝 Заявки", style=ButtonStyle.danger, emoji="📝", row=1, custom_id="del_user_apps")
    async def delete_applications(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        db.cursor.execute('DELETE FROM applications WHERE user_id=?', (self.user_id,))
        count = db.cursor.rowcount
        db.conn.commit()
        db.add_log("🗑️ Заявки удалены", interaction.user.id, self.user_id)
        await interaction.response.send_message(f"✅ Заявки **{self.user_name}** удалены! ({count} записей)", ephemeral=True, delete_after=5)

    @discord.ui.button(label="📋 Статик", style=ButtonStyle.danger, emoji="📋", row=1, custom_id="del_user_static")
    async def delete_static_requests(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        
        count = db.cursor.execute('SELECT COUNT(*) FROM static_requests WHERE user_id = ?', (self.user_id,)).fetchone()[0]
        if count == 0: await interaction.response.send_message(f"❌ У пользователя **{self.user_name}** нет заявок в статик!", ephemeral=True); return
        
        view = ConfirmDeleteStaticView(self.user_id, self.user_name, count)
        embed = Embed(title="🗑️ Подтверждение", description=f"Удалить **{count}** заявок в статик у **{self.user_name}**?\n\n⚠️ Все связанные каналы также будут удалены!\nЭто действие нельзя отменить!", color=Color.red())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🎮 Персонажи", style=ButtonStyle.danger, emoji="🎮", row=2, custom_id="del_user_chars")
    async def delete_characters(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        chars = db.get_user_characters(self.user_id)
        if not chars: await interaction.response.send_message("❌ У пользователя нет персонажей!", ephemeral=True); return
        
        options = []
        for char in chars[:25]:
            options.append(discord.SelectOption(label=f"{'⭐' if char['is_main'] else '🔄'} {char['character_name']} ({char['class_spec']})", value=str(char['id']), description=f"iLvl: {char.get('item_level', 0)}", emoji="⭐" if char['is_main'] else "🔄"))
        options.insert(0, discord.SelectOption(label="🗑️ УДАЛИТЬ ВСЕХ", value="all", description="Удалить всех персонажей!", emoji="⚠️"))
        
        select = Select(placeholder="Выберите персонажа или 'удалить всех'", options=options, custom_id="select_char_delete_user")
        
        async def del_callback(interaction: discord.Interaction):
            value = interaction.data['values'][0]
            if value == "all":
                for char in chars:
                    char_id = char['id']
                    db.cursor.execute('DELETE FROM characters WHERE id=?', (char_id,))
                    db.cursor.execute('DELETE FROM punishments WHERE character_id=?', (char_id,))
                    db.cursor.execute('DELETE FROM punishment_tasks WHERE character_id=?', (char_id,))
                    db.cursor.execute('DELETE FROM warnings WHERE character_id=?', (char_id,))
                db.conn.commit()
                db.add_log("🗑️ Все персонажи удалены", interaction.user.id, self.user_id)
                await interaction.response.send_message(f"✅ Все персонажи **{self.user_name}** удалены! ({len(chars)} шт.)", ephemeral=True, delete_after=5)
            else:
                char_id = int(value)
                char = db.get_character_by_id(char_id)
                if char:
                    db.cursor.execute('DELETE FROM characters WHERE id=?', (char_id,))
                    db.cursor.execute('DELETE FROM punishments WHERE character_id=?', (char_id,))
                    db.cursor.execute('DELETE FROM punishment_tasks WHERE character_id=?', (char_id,))
                    db.cursor.execute('DELETE FROM warnings WHERE character_id=?', (char_id,))
                    db.conn.commit()
                    db.add_log("🗑️ Персонаж удалён", interaction.user.id, self.user_id, f"#{char_id} {char['character_name']}")
                    await interaction.response.send_message(f"✅ **{char['character_name']}** удалён!", ephemeral=True, delete_after=5)
        
        select.callback = del_callback
        v = View(timeout=30); v.add_item(select)
        cancel_btn = Button(label="❌ Отмена", style=ButtonStyle.secondary, custom_id="cancel_delete_chars")
        async def cancel_callback(interaction: discord.Interaction): await interaction.response.edit_message(content="❌ Отменено.", view=None)
        cancel_btn.callback = cancel_callback; v.add_item(cancel_btn)
        await interaction.response.send_message(f"🎮 Выберите персонажа для удаления у **{self.user_name}**:", view=v, ephemeral=True)

    @discord.ui.button(label="📋 Логи", style=ButtonStyle.danger, emoji="📋", row=2, custom_id="del_user_logs")
    async def delete_logs(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        db.cursor.execute('DELETE FROM logs WHERE user_id=? OR target_id=?', (self.user_id, self.user_id))
        count = db.cursor.rowcount
        db.conn.commit()
        db.add_log("🗑️ Логи удалены", interaction.user.id, self.user_id)
        await interaction.response.send_message(f"✅ Логи **{self.user_name}** удалены! ({count} записей)", ephemeral=True, delete_after=5)

    @discord.ui.button(label="🔙 Назад", style=ButtonStyle.secondary, emoji="🔙", row=3, custom_id="back_from_delete")
    async def back(self, interaction: discord.Interaction, button: Button):
        embed = Embed(title="🔧 Админ-центр", description="Выберите действие:", color=Color.blue())
        await interaction.response.edit_message(embed=embed, view=AdminCenterView())


class ConfirmDeleteStaticView(View):
    def __init__(self, user_id: int, user_name: str, count: int):
        super().__init__(timeout=30)
        self.user_id = user_id
        self.user_name = user_name
        self.count = count
    
    @discord.ui.button(label="✅ Да, удалить", style=ButtonStyle.danger, emoji="✅")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        channels_to_delete = []
        try:
            rows = db.cursor.execute(
                'SELECT id, channel_id, status FROM static_requests WHERE user_id = ? AND channel_id IS NOT NULL',
                (self.user_id,)
            ).fetchall()
            for row in rows:
                if row[1]:
                    channels_to_delete.append((row[1], row[0], row[2]))
        except Exception as e:
            print(f"❌ Ошибка получения каналов: {e}")
        
        db.cursor.execute('DELETE FROM static_requests WHERE user_id = ?', (self.user_id,))
        db.cursor.execute('DELETE FROM static_votes WHERE channel_id IN (SELECT channel_id FROM static_requests WHERE user_id = ?)', (self.user_id,))
        db.conn.commit()
        
        deleted_channels = 0
        failed_channels = 0
        
        for channel_id, request_id, status in channels_to_delete:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                try:
                    await channel.delete(reason=f"Заявки в статик удалены для {self.user_name}")
                    deleted_channels += 1
                    await asyncio.sleep(0.5)
                except:
                    failed_channels += 1
        
        db.add_log("🗑️ Статик заявки удалены", interaction.user.id, self.user_id, f"Удалено {self.count} заявок, {deleted_channels} каналов")
        
        msg = f"✅ **{self.count}** заявок в статик удалены у **{self.user_name}**!"
        if deleted_channels > 0:
            msg += f"\n📁 Удалено каналов: **{deleted_channels}**"
        if failed_channels > 0:
            msg += f"\n⚠️ Не удалось удалить каналов: **{failed_channels}**"
        
        await interaction.response.edit_message(content=msg, view=None)
    
    @discord.ui.button(label="❌ Отмена", style=ButtonStyle.secondary, emoji="❌")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="❌ Отменено.", view=None)


class EditCharacterAdminModal(Modal):
    def __init__(self, char: dict):
        char_name = str(char.get('character_name', 'Unknown'))[:30]
        super().__init__(title=f"✏️ {char_name}")
        self.char = char
        
        name_default = str(char.get('character_name', ''))[:32]
        if not name_default or len(name_default) < 4: name_default = "Unknown"
        
        ilvl_value = char.get('item_level', 0)
        if ilvl_value is None: ilvl_value = 0
        ilvl_default = str(int(ilvl_value)).zfill(4)[:4]
        if not ilvl_default.isdigit(): ilvl_default = "0000"
        
        profile_default = str(char.get('profile_url', ''))[:200] if char.get('profile_url') else ""
        if profile_default.lower() in ['none', 'null']: profile_default = ""
        
        self.add_item(TextInput(label="Имя персонажа", default=name_default, placeholder="Введите имя персонажа", required=True, max_length=32, min_length=4))
        self.add_item(TextInput(label="Уровень предметов (iLvl)", default=ilvl_default, placeholder="0250", required=True, max_length=4, min_length=4))
        self.add_item(TextInput(label="Ссылка на профиль Sirus", default=profile_default, placeholder="Необязательно", required=False, max_length=200))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        
        new_name = self.children[0].value.strip()
        if not new_name or len(new_name) < 2: await interaction.response.send_message("❌ Имя должно быть от 2 символов!", ephemeral=True); return
        
        ilvl_str = self.children[1].value.strip().lstrip('0')
        if not ilvl_str: ilvl_str = "0"
        if not ilvl_str.isdigit(): await interaction.response.send_message("❌ iLvl должен содержать только цифры!", ephemeral=True); return
        
        new_ilvl = int(ilvl_str)
        if new_ilvl < 0 or new_ilvl > 9999: await interaction.response.send_message("❌ iLvl должен быть от 0 до 9999!", ephemeral=True); return
        
        new_profile = self.children[2].value.strip() if self.children[2].value else ""
        
        try:
            db.cursor.execute('UPDATE characters SET character_name=?, item_level=?, profile_url=? WHERE id=?', (new_name, new_ilvl, new_profile, self.char['id']))
            db.conn.commit()
            user_id = self.char.get('user_id', 0)
            db.add_log("✏️ Персонаж изменён", interaction.user.id, user_id, f"#{self.char['id']}: {self.char.get('character_name', '?')} → {new_name}, {new_ilvl} iLvl")
            await interaction.response.send_message(f"✅ Персонаж обновлён!\n**Имя:** {new_name}\n**iLvl:** {new_ilvl}\n**Профиль:** {new_profile if new_profile else 'Не указан'}", ephemeral=True, delete_after=10)
        except Exception as e:
            await interaction.response.send_message(f"❌ Ошибка при сохранении: {e}", ephemeral=True)


# ============================================
# СТАРЫЕ КЛАССЫ ДЛЯ ОБРАТНОЙ СОВМЕСТИМОСТИ
# ============================================

class RequestDeleteView(View):
    def __init__(self, requester_id: int): super().__init__(timeout=120); self.requester_id = requester_id

    @discord.ui.button(label="📩 Отправить запрос", style=ButtonStyle.primary, emoji="📩", custom_id="send_delete_request")
    async def send_request(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        dev_id = db.get_setting('developer_id', '')
        if not dev_id: await interaction.response.send_message("❌ Разработчик не назначен!", ephemeral=True); return
        developer = interaction.guild.get_member(int(dev_id))
        if not developer: await interaction.response.send_message("❌ Разработчик не найден!", ephemeral=True); return
        embed = Embed(title="🔒 Запрос на удаление данных", description=f"**От:** {interaction.user.mention}\n**ID:** {interaction.user.id}\n\nТребуется ваше подтверждение.", color=Color.orange(), timestamp=datetime.now())
        view = ApproveDeleteView(interaction.user.id)
        try: await developer.send(embed=embed, view=view); await interaction.response.edit_message(content=f"✅ Запрос отправлен {developer.mention}!", embed=None, view=None)
        except: await interaction.response.send_message("❌ Не удалось отправить ЛС!", ephemeral=True)


class ApproveDeleteView(View):
    def __init__(self, requester_id: int): super().__init__(timeout=None); self.requester_id = requester_id

    @discord.ui.button(label="✅ Одобрить (5 мин)", style=ButtonStyle.success, emoji="✅", custom_id="approve_delete")
    async def approve(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        db.set_setting(f'temp_delete_{self.requester_id}', datetime.now().isoformat())
        requester = interaction.guild.get_member(self.requester_id)
        if requester:
            try: await requester.send(embed=Embed(title="✅ Доступ разрешён", description="Используйте `/admin` → 🗑️ Удалить данные в течение 5 минут.", color=Color.green()))
            except: pass
        await interaction.response.edit_message(content=f"✅ Доступ разрешён для <@{self.requester_id}> на 5 минут!", embed=None, view=None)

    @discord.ui.button(label="❌ Отклонить", style=ButtonStyle.danger, emoji="❌", custom_id="reject_delete")
    async def reject(self, interaction: discord.Interaction, button: Button):
        requester = interaction.guild.get_member(self.requester_id)
        if requester:
            try: await requester.send(embed=Embed(title="❌ Запрос отклонён", description="Доступ к удалению не разрешён.", color=Color.red()))
            except: pass
        await interaction.response.edit_message(content="❌ Запрос отклонён.", embed=None, view=None)


class ManageSpecsAdminView(View):
    def __init__(self, char: dict): super().__init__(timeout=60); self.char = char

    @discord.ui.button(label="➕ Добавить", style=ButtonStyle.success, emoji="➕", custom_id="add_spec_admin_btn")
    async def add_spec(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        current_specs = self.char.get('specialization', '').split(', ')
        current_specs = [s.strip() for s in current_specs if s.strip()]
        class_name = self.char['class_spec']
        all_specs = CLASS_SPECS.get(class_name, [])
        available = [s for s in all_specs if s not in current_specs]
        if not available: await interaction.response.send_message("✅ Все спеки уже добавлены!", ephemeral=True); return
        spec_options = []
        for s in available:
            role_key = db.get_setting(f"spec_role_{class_name}_{s}", 'mdd')
            role_name = RAID_ROLE_NAMES.get(role_key, role_key)
            spec_options.append(discord.SelectOption(label=s, value=s, description=f"Роль: {role_name}", emoji="🎯"))
        select = Select(placeholder="Выберите специализацию", options=spec_options, custom_id="select_spec_add_admin")
        async def callback(interaction: discord.Interaction):
            new_spec = interaction.data['values'][0]
            current_specs.append(new_spec)
            new_specs_str = ', '.join(current_specs)
            all_roles = []
            for spec in current_specs:
                role = db.get_setting(f"spec_role_{class_name}_{spec}", 'mdd')
                if role not in all_roles: all_roles.append(role)
            new_roles = ','.join(all_roles) if all_roles else 'mdd'
            db.cursor.execute('UPDATE characters SET specialization=?, raid_role=? WHERE id=?', (new_specs_str, new_roles, self.char['id']))
            db.conn.commit()
            self.char['specialization'] = new_specs_str
            self.char['raid_role'] = new_roles
            embed = Embed(title="✅ Специализация добавлена", description=f"**{self.char['character_name']}**\nСпециализации: **{new_specs_str}**\nРоли: **{utils.format_raid_roles(new_roles)}**", color=Color.green())
            await interaction.response.edit_message(embed=embed, view=ManageSpecsAdminView(self.char))
        select.callback = callback
        v = View(timeout=30)
        v.add_item(select)
        await interaction.response.send_message("Выберите специализацию:", view=v, ephemeral=True)

    @discord.ui.button(label="🗑️ Снять", style=ButtonStyle.danger, emoji="🗑️", custom_id="remove_spec_admin_btn")
    async def remove_spec(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        current_specs = self.char.get('specialization', '').split(', ')
        current_specs = [s.strip() for s in current_specs if s.strip()]
        if len(current_specs) <= 1: await interaction.response.send_message("⚠️ Нельзя оставить без специализации!", ephemeral=True); return
        spec_options = [discord.SelectOption(label=spec, value=spec, emoji="🗑️") for spec in current_specs]
        select = Select(placeholder="Выберите для снятия", options=spec_options, custom_id="select_spec_remove_admin")
        async def callback(interaction: discord.Interaction):
            spec_to_remove = interaction.data['values'][0]
            current_specs.remove(spec_to_remove)
            new_specs_str = ', '.join(current_specs)
            all_roles = []
            for spec in current_specs:
                role = db.get_setting(f"spec_role_{self.char['class_spec']}_{spec}", 'mdd')
                if role not in all_roles: all_roles.append(role)
            new_roles = ','.join(all_roles) if all_roles else 'mdd'
            db.cursor.execute('UPDATE characters SET specialization=?, raid_role=? WHERE id=?', (new_specs_str, new_roles, self.char['id']))
            db.conn.commit()
            self.char['specialization'] = new_specs_str
            self.char['raid_role'] = new_roles
            embed = Embed(title="✅ Специализация снята", description=f"**{self.char['character_name']}**\nОставшиеся: **{new_specs_str}**\nРоли: **{utils.format_raid_roles(new_roles)}**", color=Color.orange())
            await interaction.response.edit_message(embed=embed, view=ManageSpecsAdminView(self.char))
        select.callback = callback
        v = View(timeout=30)
        v.add_item(select)
        await interaction.response.send_message("Выберите для снятия:", view=v, ephemeral=True)