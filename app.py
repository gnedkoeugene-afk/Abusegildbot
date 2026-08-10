# app.py — ПОЛНЫЙ ИСПРАВЛЕННЫЙ ФАЙЛ СО ВСЕМИ КОМАНДАМИ И ВОССТАНОВЛЕНИЕМ ЗАЯВОК

import discord
from discord.ext import commands, tasks
from discord import app_commands, Embed, Color, ButtonStyle
from discord.ui import View, Button, Select, Modal, TextInput
import config
import database
import utils
import asyncio
import os
import json
from datetime import datetime, timedelta

# Импорты из views
from views.applications import (ApplyView, ClassSelectView, RaidRoleSelectView, 
                                 DaySelectView, ApplicationReviewView)
from views.appeals import AppealMainView, AppealReviewView
from views.absences import (AbsenceMainView, build_calendar_embed, 
                            refresh_calendar_for_guild)
from views.characters import (CharactersMainView, FirstCharacterView, ClassSpecSelectView,
                               ChangeMainCharacterSelectView, ConfirmDeleteView,
                               MainChangeReviewView, StaticRequestConfirmView,
                               StaticRequestReviewView, SupportView)
from views.punishments import (PunishmentMainView, PunishmentSelectView,
                                TaskCompleteView, TaskConfirmView)
from views.curator import (CuratorPanelView, CuratorPanelPersistentView, restore_students_channel)
from views.compositions import (CompositionCreateButton, SetLeaderSelectView,
                                 CompositionControlPanel, CompositionMemberSelect,
                                 CompositionReserveSelectView,
                                 CompositionFromReserveSelectView,
                                 AddMemberMenuView)
from views.settings import SettingsView, GuildRolesSettingsView, AbsenceLimitsView
from views.class_settings import ClassSettingsView
from views.reports import ReportReviewView
from views.priority import PriorityRolesSetupView
from views.tasks import TaskSettingsView
from views.static import StaticSettingsView
from views.members import MemberManagementView, ConfirmBroadcastView
from views.permissions import PermissionsSettingsView, PermissionsEditView
from views.admin_center import AdminCenterView

# Импорты из modals
from modals.application_modals import ApplicationModal, RejectModal, BlacklistModal
from modals.appeal_modals import AppealModal
from modals.absence_modals import AbsenceModal, LateModal
from modals.report_modals import ReportModal, ReportResolveModal
from modals.character_modals import (AddTwinModal, EditCharacterModal,
                                      ChangeMainCharacterModal, StaticRequestModal,
                                      SupportModal, SupportReplyModal)
from modals.punishment_modals import (PunishmentSearchModal, PunishmentRemoveSearchModal,
                                       PunishmentModalNew, RemovePunishmentModal,
                                       TaskReportModal, TaskRejectModal)
from modals.composition_modals import (CreateCompositionModal, CompositionEditModal,
                                        CompositionRemoveModal, DuplicateCompositionModal,
                                        CompositionSearchModal, ConfirmAddMemberView,
                                        LeaderSearchModal)
from modals.settings_modals import (RoleSettingModal, ChannelsModal1, ChannelsModal2,
                                     CategoriesModal, InfoModal, RewardRolesModal,
                                     RewardRolesModal2, PriorityRoleInputModal,
                                     PriorityRoleInputModal2, TaskSettingsModal,
                                     StaticMessageModal)
from modals.member_modals import ReminderSettingsModal
from utils.curator_utils import is_curator, can_manage_curator_panel
from utils.trainee_utils import (
    assign_trainee_role,
    remove_trainee_role,
    assign_curator_role,
    remove_curator_role
)
# Импорт voice_welcome
import views.voice_welcome

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

# ========== ХРАНИЛИЩЕ АКТИВНЫХ БОЁВ ==========
active_battles = {}
active_panels = {}

# ========== ХРАНИЛИЩЕ АКТИВНЫХ ЖАЛОБ ==========
active_reports = {}

def save_active_reports():
    try:
        data = {}
        for msg_id, info in active_reports.items():
            data[str(msg_id)] = {
                'report_id': info['report_id'],
                'reporter_id': info['reporter_id'],
                'violator_id': info.get('violator_id'),
                'channel_id': info['channel_id'],
                'is_anonymous': info['is_anonymous'],
                'guild_id': info['guild_id'],
                'message_id': info['message_id']
            }
        os.makedirs('data', exist_ok=True)
        with open('data/active_reports.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Ошибка сохранения жалоб: {e}")

def load_active_reports():
    global active_reports
    try:
        with open('data/active_reports.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        loaded = 0
        for msg_id, info in data.items():
            active_reports[int(msg_id)] = info
            loaded += 1
        print(f"✅ Загружено {loaded} активных жалоб")
        return loaded
    except FileNotFoundError:
        print("📋 Файл жалоб не найден")
        return 0
    except Exception as e:
        print(f"❌ Ошибка загрузки жалоб: {e}")
        return 0

def save_active_panels():
    try:
        data = {}
        for msg_id, info in active_panels.items():
            battle_config = info.get('battle_config', {})
            data[str(msg_id)] = {
                'channel_id': info['channel_id'],
                'guild_id': info['guild_id'],
                'voice_channel_id': info['voice_channel_id'],
                'created_at': info['created_at'].isoformat() if info.get('created_at') else None,
                'creator_id': info['creator_id'],
                'empty_since': info['empty_since'].isoformat() if info.get('empty_since') else None,
                'battle_ended_at': info['battle_ended_at'].isoformat() if info.get('battle_ended_at') else None,
                'battle_config': {
                    'channel_id': battle_config.get('channel_id'),
                    'mode': battle_config.get('mode', 'standard'),
                    'custom_members': battle_config.get('custom_members', []),
                    'creator_id': battle_config.get('creator_id')
                }
            }
        os.makedirs('data', exist_ok=True)
        with open('data/active_panels.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"❌ Ошибка сохранения панелей: {e}")

def load_active_panels():
    global active_panels
    try:
        with open('data/active_panels.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        loaded = 0
        for msg_id, info in data.items():
            active_panels[int(msg_id)] = {
                'channel_id': info['channel_id'],
                'guild_id': info['guild_id'],
                'voice_channel_id': info['voice_channel_id'],
                'created_at': datetime.fromisoformat(info['created_at']) if info.get('created_at') else None,
                'creator_id': info['creator_id'],
                'empty_since': datetime.fromisoformat(info['empty_since']) if info.get('empty_since') else None,
                'battle_ended_at': datetime.fromisoformat(info['battle_ended_at']) if info.get('battle_ended_at') else None,
                'battle_config': info.get('battle_config', {})
            }
            loaded += 1
        print(f"✅ Загружено {loaded} панелей из файла")
        return loaded
    except FileNotFoundError:
        print("📋 Файл панелей не найден")
        return 0
    except Exception as e:
        print(f"❌ Ошибка загрузки панелей: {e}")
        return 0

def get_unmuted_ids(channel, battle_config, guild_id, user_id=None):
    unmuted = []
    guild = channel.guild
    db = bot.get_db(guild_id)
    if not db:
        return unmuted
    guild_master_role_id = utils.safe_int(db.get_setting('guild_master', ''))
    vice_master_role_id = utils.safe_int(db.get_setting('vice_master', ''))
    raid_leader_role_id = utils.safe_int(db.get_setting('raid_leader', ''))
    senior_officer_role_id = utils.safe_int(db.get_setting('senior_officer_role', ''))
    officer_role_id = utils.safe_int(db.get_setting('officer_role', ''))
    mode = battle_config.get('mode', 'standard') if battle_config else 'standard'
    if mode == "custom" and battle_config:
        custom_members = battle_config.get('custom_members', [])
        for member in channel.members:
            if member.bot:
                continue
            if member.id in custom_members:
                unmuted.append(member.id)
    else:
        for member in channel.members:
            if member.bot:
                continue
            if guild_master_role_id:
                role = guild.get_role(guild_master_role_id)
                if role and role in member.roles:
                    unmuted.append(member.id)
                    continue
            if vice_master_role_id:
                role = guild.get_role(vice_master_role_id)
                if role and role in member.roles:
                    unmuted.append(member.id)
                    continue
            if raid_leader_role_id:
                role = guild.get_role(raid_leader_role_id)
                if role and role in member.roles:
                    unmuted.append(member.id)
                    continue
            if mode in ["standard", "free"]:
                if senior_officer_role_id:
                    role = guild.get_role(senior_officer_role_id)
                    if role and role in member.roles:
                        unmuted.append(member.id)
                        continue
                if officer_role_id:
                    role = guild.get_role(officer_role_id)
                    if role and role in member.roles:
                        unmuted.append(member.id)
                        continue
    if user_id and user_id not in unmuted:
        unmuted.append(user_id)
    always_roles_str = db.get_setting('pull_always_roles', '')
    always_users_str = db.get_setting('pull_always_users', '')
    if always_roles_str:
        role_ids = [int(r.strip()) for r in always_roles_str.split(',') if r.strip().isdigit()]
        for member in channel.members:
            if member.bot or member.id in unmuted:
                continue
            for role_id in role_ids:
                role = guild.get_role(role_id)
                if role and role in member.roles:
                    unmuted.append(member.id)
                    break
    if always_users_str:
        user_ids = [int(u.strip()) for u in always_users_str.split(',') if u.strip().isdigit()]
        for uid in user_ids:
            if uid not in unmuted:
                unmuted.append(uid)
    return unmuted

class GuildBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        self.databases = {}
        self.db = None

    def get_db(self, guild_id: int):
        return self.databases.get(guild_id)

    def remove_active_report(self, message_id: int):
        if message_id in active_reports:
            del active_reports[message_id]
            save_active_reports()
            print(f"🗑️ Жалоба удалена из active_reports: {message_id}")

    async def global_interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.guild_id:
            db = self.get_db(interaction.guild_id)
            if db:
                interaction.client.db = db
        return True

    async def setup_hook(self):
        os.makedirs('data', exist_ok=True)
        self.databases[config.MAIN_GUILD_ID] = database.Database(config.MAIN_DB_PATH)
        self.databases[config.MAIN_GUILD_ID].init()
        self.databases[config.TEST_GUILD_ID] = database.Database(config.TEST_DB_PATH)
        self.databases[config.TEST_GUILD_ID].init()
        print("✅ Базы данных инициализированы")
        load_active_panels()
        load_active_reports()
        try:
            await self.load_extension('views.voice_welcome')
            print("✅ VoiceWelcome cog загружен")
        except Exception as e:
            print(f"❌ Ошибка загрузки VoiceWelcome: {e}")
        self.tree.interaction_check = self.global_interaction_check
        self.add_view(ApplyView())
        self.add_view(AppealMainView())
        self.add_view(AbsenceMainView())
        self.add_view(CharactersMainView())
        self.add_view(PunishmentMainView())
        self.add_view(CompositionCreateButton())
        self.add_view(TaskCompleteView())
        self.add_view(TaskConfirmView())
        self.add_view(CompositionControlPanel())
        self.add_view(StaticRequestReviewView())
        self.add_view(CuratorPanelPersistentView())
        print("✅ View зарегистрированы")

    @tasks.loop(minutes=1)
    async def reject_role_cleanup(self):
        for guild in self.guilds:
            db = self.get_db(guild.id)
            if not db: continue
            reject_role_id = utils.safe_int(db.get_setting('reject_role', ''))
            if not reject_role_id: continue
            reject_role = guild.get_role(reject_role_id)
            if not reject_role: continue
            for member in guild.members:
                if reject_role not in member.roles: continue
                can_submit, _, _ = db.can_submit_application(member.id)
                if can_submit:
                    try:
                        await member.remove_roles(reject_role, reason="Время ожидания истекло")
                        print(f"   ✅ Роль {reject_role.name} снята с {member.display_name}")
                    except: pass

    @tasks.loop(minutes=10)
    async def report_cleanup_task(self):
        for guild in self.guilds:
            db = self.get_db(guild.id)
            if not db: continue
            try:
                reports = db.cursor.execute(
                    "SELECT id, channel_id FROM reports WHERE status IN ('resolved', 'rejected') AND resolved_at IS NOT NULL"
                ).fetchall()
                for report_id, channel_id in reports:
                    resolved_at_str = db.get_setting(f'report_{report_id}_resolved_at', '')
                    if not resolved_at_str:
                        continue
                    try:
                        resolved_at = datetime.fromisoformat(resolved_at_str)
                        if (datetime.now() - resolved_at).total_seconds() > 3600:
                            channel = guild.get_channel(channel_id)
                            if channel:
                                try:
                                    await channel.delete()
                                    print(f"🗑️ Канал жалобы #{report_id} удалён (1 час)")
                                except:
                                    pass
                            db.set_setting(f'report_{report_id}_resolved_at', '')
                    except:
                        pass
            except:
                pass

    @tasks.loop(minutes=5)
    async def check_expired_tasks(self):
        for guild in self.guilds:
            db = self.get_db(guild.id)
            if not db:
                continue
            try:
                now = datetime.now()
                expired = db.cursor.execute('''
                    SELECT tt.id, tt.trainee_id, tt.title, tt.points_reward, tt.deadline, tr.user_id
                    FROM trainee_tasks tt
                    JOIN trainees tr ON tt.trainee_id = tr.id
                    WHERE tt.status = 'pending' AND tt.deadline < ?
                ''', (now.isoformat(),)).fetchall()
                if not expired:
                    continue
                for task in expired:
                    task_id, trainee_id, task_title, points, deadline, user_id = task
                    penalty = max(5, points // 2)
                    db.cursor.execute('UPDATE trainee_tasks SET status = "expired" WHERE id = ?', (task_id,))
                    db.cursor.execute('UPDATE trainees SET points = points - ?, last_activity = CURRENT_TIMESTAMP WHERE user_id = ?', (penalty, user_id))
                    db.conn.commit()
                    db.add_trainee_log(trainee_id, f"⏰ Задание просрочено: {task_title} (штраф: -{penalty} баллов)", None)
                    member = guild.get_member(user_id)
                    if member:
                        try:
                            embed = Embed(title="⏰ Задание просрочено!", description=f"Вы не сдали задание **{task_title}** вовремя.", color=Color.red())
                            embed.add_field(name="📉 Штраф", value=f"-{penalty} баллов", inline=True)
                            embed.add_field(name="📅 Дедлайн был", value=deadline[:16] if deadline else "Неизвестно", inline=True)
                            await member.send(embed=embed)
                        except:
                            pass
                    log_channel_id = db.get_setting('log_channel', '')
                    if log_channel_id:
                        channel = guild.get_channel(int(log_channel_id))
                        if channel:
                            embed = Embed(title="⏰ Задание просрочено", description=f"**Кандидат:** <@{user_id}>\n**Задание:** {task_title}\n**Штраф:** -{penalty} баллов", color=Color.orange(), timestamp=datetime.now())
                            await channel.send(embed=embed)
                    print(f"   ⏰ Задание #{task_id} просрочено, штраф: -{penalty} баллов")
            except Exception as e:
                print(f"❌ Ошибка проверки просроченных заданий на {guild.name}: {e}")

    @check_expired_tasks.before_loop
    async def before_check_expired_tasks(self):
        await self.wait_until_ready()

    @report_cleanup_task.before_loop
    async def before_report_cleanup(self):
        await self.wait_until_ready()

    async def on_ready(self):
        print(f"✅ Бот {self.user} запущен!")
        print(f"📊 Находится на {len(self.guilds)} серверах:")
        for g in self.guilds:
            print(f"   - {g.name} (ID: {g.id})")

        # Синхронизация команд
        print("\n🔄 Синхронизация команд...")
        try:
            global_cmds = await self.tree.sync()
            print(f"   ✅ Глобально: {len(global_cmds)} команд")
        except Exception as e:
            print(f"   ❌ Глобальная ошибка: {e}")
        for guild in self.guilds:
            try:
                guild_obj = discord.Object(id=guild.id)
                guild_cmds = await self.tree.sync(guild=guild_obj)
                print(f"   ✅ {guild.name}: {len(guild_cmds)} команд")
            except Exception as e:
                print(f"   ❌ {guild.name}: {e}")

        print("\n🔧 Инициализация ролей...")
        for guild in self.guilds:
            db = self.get_db(guild.id)
            if db:
                try:
                    db.init_default_roles(guild)
                    print(f"   ✅ {guild.name}: роли готовы")
                except Exception as e:
                    print(f"   ⚠️ {guild.name}: {e}")

        try:
            if not self.check_expired_tasks.is_running():
                self.check_expired_tasks.start()
                print("✅ Задача проверки просроченных заданий запущена")
        except Exception as e:
            print(f"⚠️ Ошибка запуска проверки просроченных заданий: {e}")

        await asyncio.sleep(1)

        # ========== ВОССТАНОВЛЕНИЕ ЗАЯВОК ==========
        print("\n" + "=" * 60)
        print("📝 ВОССТАНОВЛЕНИЕ АКТИВНЫХ ЗАЯВОК")
        print("=" * 60)
        total_apps = 0
        restored_apps = 0
        failed_apps = 0

        for guild in self.guilds:
            db = self.get_db(guild.id)
            if not db:
                continue
            print(f"\n🔍 Проверка заявок на сервере: {guild.name} (ID: {guild.id})")
            try:
                pending_apps = db.cursor.execute('''
                    SELECT id, user_id, channel_id, message_id, data
                    FROM applications
                    WHERE status = "pending"
                ''').fetchall()
                total_apps += len(pending_apps)
                if not pending_apps:
                    print(f"   📭 Нет активных заявок на {guild.name}")
                    continue
                print(f"   📋 Найдено заявок: {len(pending_apps)}")
                for app_id, user_id, channel_id, message_id, data_raw in pending_apps:
                    channel = guild.get_channel(channel_id)
                    if not channel:
                        print(f"   ❌ Заявка #{app_id}: КАНАЛ НЕ НАЙДЕН (ID: {channel_id})")
                        failed_apps += 1
                        continue
                    print(f"\n   📌 Заявка #{app_id}:")
                    print(f"      👤 Пользователь: <@{user_id}> (ID: {user_id})")
                    print(f"      📁 Канал: #{channel.name} (ID: {channel_id})")
                    data = {}
                    if isinstance(data_raw, str):
                        try:
                            data = json.loads(data_raw)
                            print(f"      📝 Данные: {list(data.keys()) if data else 'Пусто'}")
                        except:
                            print(f"      ⚠️ Ошибка разбора данных")
                    elif isinstance(data_raw, dict):
                        data = data_raw
                        print(f"      📝 Данные: {list(data.keys()) if data else 'Пусто'}")
                    view = ApplicationReviewView(channel_id, user_id, app_id, data)
                    found = False

                    # 1. Пытаемся восстановить по message_id
                    if message_id:
                        try:
                            msg = await channel.fetch_message(message_id)
                            if msg.author == self.user and msg.embeds:
                                self.add_view(view, message_id=msg.id)
                                await msg.edit(view=view)
                                found = True
                                restored_apps += 1
                                print(f"      ✅ ВОССТАНОВЛЕНА по message_id! Сообщение ID: {msg.id}")
                        except discord.NotFound:
                            print(f"      ⚠️ Сообщение {message_id} не найдено, ищем в истории...")
                        except Exception as e:
                            print(f"      ❌ Ошибка получения сообщения {message_id}: {e}")

                    # 2. Ищем в истории канала
                    if not found:
                        try:
                            async for msg in channel.history(limit=30):
                                if msg.author == self.user and msg.embeds:
                                    embed_title = msg.embeds[0].title if msg.embeds else ""
                                    if "Заявка" in embed_title or "📝" in embed_title:
                                        self.add_view(view, message_id=msg.id)
                                        await msg.edit(view=view)
                                        db.cursor.execute('UPDATE applications SET message_id = ? WHERE id = ?', (msg.id, app_id))
                                        db.conn.commit()
                                        found = True
                                        restored_apps += 1
                                        print(f"      ✅ ВОССТАНОВЛЕНА из истории! Сообщение ID: {msg.id}")
                                        break
                        except Exception as e:
                            print(f"      ❌ Ошибка поиска в истории: {e}")

                    # 3. Если не нашли – пересоздаём сообщение
                    if not found:
                        try:
                            # Создаём embed заново
                            embed = Embed(title=f"📝 Заявка #{app_id}", description=f"**Заявитель:** <@{user_id}>", color=Color.purple())
                            embed.add_field(name="👤 Личное имя", value=f"```{data.get('real_name', '')}```", inline=True)
                            embed.add_field(name="🎮 Имя персонажа", value=f"```{data.get('character_name', '')}```", inline=True)
                            embed.add_field(name="⚔️ Класс", value=f"**{data.get('class_spec', 'Не указан')}**", inline=True)
                            embed.add_field(name="🎯 Специализация", value=f"```{data.get('specialization', 'Не указана')}```", inline=True)
                            embed.add_field(name="💎 iLvl", value=f"```{data.get('item_level', 0)}```", inline=True)
                            embed.add_field(name="📅 Дни рейдов", value=f"```{utils.format_days(data.get('available_days', ''))}```", inline=True)
                            embed.add_field(name="🎭 Роль", value=f"**{RAID_ROLE_NAMES.get(data.get('raid_role', 'mdd'), 'МДД')}**", inline=True)
                            embed.add_field(name="👤 Пригласил", value=f"```{data.get('invited_by', '')}```", inline=True)
                            if data.get('profile_url'):
                                embed.add_field(name="🔗 Профиль", value=f"[Sirus]({data['profile_url']})", inline=True)
                            embed.set_footer(text=f"ID: {app_id}")

                            msg = await channel.send(embed=embed, view=view)
                            self.add_view(view, message_id=msg.id)
                            db.cursor.execute('UPDATE applications SET message_id = ? WHERE id = ?', (msg.id, app_id))
                            db.conn.commit()
                            found = True
                            restored_apps += 1
                            print(f"      ✅ СООБЩЕНИЕ ПЕРЕСОЗДАНО! Новый ID: {msg.id}")
                        except Exception as e:
                            print(f"      ❌ Ошибка пересоздания сообщения: {e}")

                    if not found:
                        print(f"      ❌ НЕ УДАЛОСЬ ВОССТАНОВИТЬ заявку #{app_id}")
                        failed_apps += 1

            except Exception as e:
                print(f"   ❌ Ошибка при обработке заявок на {guild.name}: {e}")

        print("\n" + "=" * 60)
        print("📊 ИТОГИ ВОССТАНОВЛЕНИЯ ЗАЯВОК:")
        print(f"   📝 Всего заявок: {total_apps}")
        print(f"   ✅ Восстановлено: {restored_apps}")
        print(f"   ❌ Не удалось: {failed_apps}")
        print("=" * 60)

        # Восстановление pull-панелей
        print("\n🔄 Восстановление pull-панелей...")
        await restore_battle_panels()

        # Восстановление View
        print("\n🔄 Восстановление View...")
        await self.restore_views()

        # Восстановление канала учеников-курсантов
        print("\n🔄 Восстановление канала учеников-курсантов...")
        for guild in self.guilds:
            db = self.get_db(guild.id)
            if db:
                try:
                    await restore_students_channel(guild, db)
                    print(f"   ✅ Канал учеников восстановлен на {guild.name}")
                except Exception as e:
                    print(f"   ⚠️ Ошибка восстановления канала на {guild.name}: {e}")

        # Запуск задач
        for task in [
            self.character_reminder_task,
            self.weekly_cleanup_task,
            self.monthly_calendar_task,
            self.calendar_refresh_task,
            self.reject_role_cleanup
        ]:
            try:
                task.start()
            except RuntimeError:
                pass

        try:
            if not self.report_cleanup_task.is_running():
                self.report_cleanup_task.start()
                print("✅ Задача очистки жалоб запущена")
        except Exception as e:
            print(f"⚠️ Ошибка запуска очистки жалоб: {e}")

        try:
            if not cleanup_inactive_panels.is_running():
                cleanup_inactive_panels.start()
                print("✅ Задача очистки панелей запущена")
        except Exception as e:
            print(f"⚠️ Ошибка запуска очистки панелей: {e}")

        print("\n🎉 Бот полностью готов к работе!")
        print("=" * 50)

    async def restore_views(self):
        print("\n" + "=" * 60)
        print("🔄 ВОССТАНОВЛЕНИЕ VIEW")
        print("=" * 60)
        for guild in self.guilds:
            db = self.get_db(guild.id)
            if not db:
                continue
            print(f"\n🔍 Обработка сервера: {guild.name} (ID: {guild.id})")
            message_views = {
                'apply': ('📝 Заявки', ApplyView()),
                'appeal': ('⚖️ Апелляции', AppealMainView()),
                'absence': ('📅 Отсутствия', AbsenceMainView()),
                'characters': ('🎮 Персонажи', CharactersMainView()),
                'punishment': ('⚠️ Наказания', PunishmentMainView()),
                'composition_button': ('🎯 Составы', CompositionCreateButton())
            }
            for key, (label, view) in message_views.items():
                msg_data = db.get_message(key)
                if msg_data:
                    channel = guild.get_channel(msg_data[0])
                    if channel:
                        try:
                            msg = await channel.fetch_message(msg_data[1])
                            if key == 'apply':
                                guild_name = db.get_setting('guild_name', 'Abuse')
                                server = db.get_setting('server', 'Sirus')
                                faction = db.get_setting('faction', 'Alliance')
                                raid_times = db.get_setting('raid_times', '20:00 МСК')
                                apply_embed = Embed(
                                    title=f"🏰 {guild_name.upper()}",
                                    description=(
                                        f"**▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬**\n"
                                        f"    ДОБРО ПОЖАЛОВАТЬ В ГИЛЬДИЮ!\n"
                                        f"**▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬**\n\n"
                                        f"**🌍 Сервер**{server}"
                                        f"**⚔️ Фракция**{faction}"
                                        f"**📅 Рейдовое время**{raid_times}"
                                    ),
                                    color=Color.purple()
                                )
                                apply_desc = db.get_setting('apply_description', '')
                                if apply_desc:
                                    apply_embed.add_field(
                                        name="",
                                        value=f"```ansi\n[1;33m▐[0m[1;37m ТРЕБОВАНИЯ К КАНДИДАТАМ [0m[1;33m▌[0m\n```\n{apply_desc[:1000]}",
                                        inline=False
                                    )
                                apply_embed.add_field(
                                    name="",
                                    value=f"```ansi\n[1;32m▐[0m[1;37m ГОТОВЫ ПРИСОЕДИНИТЬСЯ? [0m[1;32m▌[0m\n```\n"
                                        f"*Нажмите кнопку **📝 Подать заявку** ниже чтобы начать!*"
                                        f"❓ Если остались вопросы — спросите у офицеров!",
                                    inline=False
                                )
                                if guild.icon:
                                    apply_embed.set_thumbnail(url=guild.icon.url)
                                apply_embed.set_footer(
                                    text=f"⭐ {guild_name} • Sirus x3 • Присоединяйся! ⭐",
                                    icon_url=guild.icon.url if guild.icon else None
                                )
                                await msg.edit(embed=apply_embed, view=view)
                                print(f"   ✅ {label}: обновлено в #{channel.name}")
                            elif key == 'absence':
                                today = datetime.now()
                                new_embed = build_calendar_embed(guild, db, today.year, today.month)
                                await msg.edit(embed=new_embed, view=view)
                                print(f"   ✅ {label}: обновлено в #{channel.name}")
                            else:
                                await msg.edit(view=view)
                                print(f"   ✅ {label}: обновлено в #{channel.name}")
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            print(f"   ❌ {label}: ошибка - {e}")
            try:
                appeals = db.get_pending_appeals_full()
                if appeals:
                    print(f"   📋 Найдено апелляций: {len(appeals)}")
                for appeal in appeals:
                    channel = guild.get_channel(appeal['channel_id'])
                    if channel:
                        try:
                            async for msg in channel.history(limit=5):
                                if msg.author == self.user and msg.embeds:
                                    v = AppealReviewView(channel.id, appeal['user_id'], appeal['appeal_id'])
                                    self.add_view(v)
                                    await msg.edit(view=v)
                                    print(f"   ✅ Апелляция #{appeal['appeal_id']} восстановлена в #{channel.name}")
                                    break
                        except:
                            pass
            except:
                pass
            try:
                changes = db.cursor.execute(
                    'SELECT id, user_id, character_id, new_character_id FROM main_change_requests WHERE status = "pending"'
                ).fetchall()
                if changes:
                    print(f"   📋 Найдено смен персонажа: {len(changes)}")
                for change in changes:
                    req_id, uid, old_id, new_id = change[0], change[1], change[2], change[3]
                    for ch in guild.text_channels:
                        if f"смена-персонажа-{req_id}" in ch.name:
                            try:
                                async for msg in ch.history(limit=5):
                                    if msg.author == self.user and msg.embeds:
                                        v = MainChangeReviewView(req_id, uid, old_id, new_id)
                                        self.add_view(v)
                                        await msg.edit(view=v)
                                        print(f"   ✅ Смена персонажа #{req_id} восстановлена в #{ch.name}")
                                        break
                            except:
                                pass
            except:
                pass
            try:
                requests = db.cursor.execute(
                    'SELECT id, channel_id FROM static_requests WHERE status = "pending"'
                ).fetchall()
                if requests:
                    print(f"   📋 Найдено запросов в статик: {len(requests)}")
                for req in requests:
                    req_id, channel_id = req[0], req[1]
                    channel = guild.get_channel(channel_id)
                    if not channel:
                        continue
                    try:
                        async for msg in channel.history(limit=10):
                            if msg.author == self.user and msg.embeds:
                                v = StaticRequestReviewView()
                                self.add_view(v)
                                await msg.edit(view=v)
                                print(f"   ✅ Статик #{req_id} восстановлен в #{channel.name}")
                                break
                    except Exception as e:
                        print(f"   ⚠️ Ошибка восстановления статика #{req_id}: {e}")
            except Exception as e:
                print(f"   ⚠️ Ошибка получения статик заявок: {e}")
            try:
                tasks_list = db.cursor.execute(
                    'SELECT id, channel_id FROM punishment_tasks WHERE status = "pending"'
                ).fetchall()
                if tasks_list:
                    print(f"   📋 Найдено заданий: {len(tasks_list)}")
                for task in tasks_list:
                    task_id, channel_id = task[0], task[1]
                    channel = guild.get_channel(channel_id)
                    if not channel:
                        continue
                    try:
                        async for msg in channel.history(limit=10):
                            if msg.author != self.user or not msg.embeds:
                                continue
                            title = msg.embeds[0].title or ""
                            if "Отчёт" in title:
                                v = TaskConfirmView()
                            elif "Задание" in title:
                                v = TaskCompleteView()
                            else:
                                continue
                            self.add_view(v)
                            await msg.edit(view=v)
                            print(f"   ✅ Задание #{task_id} восстановлено в #{channel.name}")
                    except Exception as e:
                        print(f"   ⚠️ Ошибка восстановления задания #{task_id}: {e}")
            except Exception as e:
                print(f"   ⚠️ Ошибка получения заданий: {e}")
            try:
                reports = db.cursor.execute(
                    'SELECT id, user_id, channel_id FROM support_reports WHERE status = "open"'
                ).fetchall()
                if reports:
                    print(f"   📋 Найдено обращений в техподдержку: {len(reports)}")
                for row in reports:
                    report_id, user_id, channel_id = row[0], row[1], row[2]
                    channel = guild.get_channel(channel_id)
                    if not channel:
                        db.cursor.execute('UPDATE support_reports SET status = "expired" WHERE id = ?', (report_id,))
                        db.conn.commit()
                        continue
                    async for msg in channel.history(limit=10):
                        if msg.author == self.user and msg.embeds:
                            v = SupportView(report_id, user_id)
                            self.add_view(v)
                            await msg.edit(view=v)
                            print(f"   ✅ Техподдержка #{report_id} восстановлена в #{channel.name}")
                            break
            except:
                pass
            ctrl_ch_id = utils.safe_int(db.get_setting('composition_control_channel', ''))
            if ctrl_ch_id:
                ctrl_ch = guild.get_channel(ctrl_ch_id)
                if ctrl_ch:
                    comps = db.cursor.execute(
                        'SELECT id, name, leader_id, main_slots, reserve_slots FROM raids WHERE status = "active"'
                    ).fetchall()
                    if comps:
                        print(f"   📋 Найдено составов: {len(comps)}")
                        try:
                            async for msg in ctrl_ch.history(limit=100):
                                if msg.author == self.user:
                                    await msg.delete()
                        except:
                            pass
                        for comp in comps:
                            cid, name, lid, ms, rs = comp[0], comp[1], comp[2], comp[3], comp[4]
                            v = CompositionControlPanel()
                            emb = Embed(
                                title=f"🎯 Управление составом: {name}",
                                description=f"**Лидер:** <@{lid}>\n**Всего мест:** {ms} | **Резерв:** {rs}",
                                color=Color.blue()
                            )
                            emb.set_footer(text=f"ID состава: {cid}")
                            await ctrl_ch.send(embed=emb, view=v)
                            print(f"   ✅ Состав {name} восстановлен")
                    else:
                        msg_data = db.get_message('composition_button')
                        if msg_data:
                            try:
                                msg = await ctrl_ch.fetch_message(msg_data[1])
                                await msg.edit(view=CompositionCreateButton())
                                print(f"   ✅ Кнопка создания составов восстановлена")
                            except:
                                embed = Embed(title="🎯 Управление составами", description="Создавайте составы.", color=Color.blue())
                                new_msg = await ctrl_ch.send(embed=embed, view=CompositionCreateButton())
                                db.save_message('composition_button', ctrl_ch.id, new_msg.id)
                                print(f"   ✅ Новая кнопка создания составов создана")
                        else:
                            embed = Embed(title="🎯 Управление составами", description="Создавайте составы.", color=Color.blue())
                            new_msg = await ctrl_ch.send(embed=embed, view=CompositionCreateButton())
                            db.save_message('composition_button', ctrl_ch.id, new_msg.id)
                            print(f"   ✅ Новая кнопка создания составов создана")
        print("\n" + "=" * 60)
        print("✅ ВОССТАНОВЛЕНИЕ VIEW ЗАВЕРШЕНО")
        print("=" * 60)

    @tasks.loop(minutes=10)
    async def calendar_refresh_task(self):
        now = datetime.now()
        for guild in self.guilds:
            db = self.get_db(guild.id)
            if not db: continue
            today_str = now.strftime('%Y-%m-%d')
            expired = db.cursor.execute('''SELECT id, user_id FROM absences WHERE status = 'active' AND reason NOT LIKE '⚠️ Опоздание:%' AND date(substr(end_date, 7, 4) || '-' || substr(end_date, 4, 2) || '-' || substr(end_date, 1, 2)) < date(?)''', (today_str,)).fetchall()
            for absence_id, user_id in expired:
                db.mark_absence_completed(absence_id)
                member = guild.get_member(user_id)
                if member:
                    await utils.remove_roles_from_setting(member, db, 'absence_role', "Отсутствие завершено")
            auto_expired = db.cursor.execute('''SELECT id, user_id FROM absences WHERE status = 'active' AND reason LIKE '⚠️ Опоздание:%' AND auto_complete_at IS NOT NULL AND auto_complete_at <= ?''', (now.isoformat(),)).fetchall()
            for absence_id, user_id in auto_expired:
                db.mark_absence_completed(absence_id)
            if expired or auto_expired or now.minute % 30 == 0:
                await refresh_calendar_for_guild(guild, db)
            if now.hour == 0 and now.minute < 10:
                await refresh_calendar_for_guild(guild, db)

    @tasks.loop(hours=1)
    async def monthly_calendar_task(self):
        now = datetime.now()
        if now.day == 1 and now.hour == 0:
            for guild in self.guilds:
                db = self.get_db(guild.id)
                if not db: continue
                await refresh_calendar_for_guild(guild, db)

    @tasks.loop(hours=24)
    async def character_reminder_task(self):
        await self.wait_until_ready()
        for guild in self.guilds:
            db = self.get_db(guild.id)
            if not db or db.get_setting('character_reminder_enabled', '1') != '1': continue
            target_role_ids = db.get_character_reminder_roles()
            if not target_role_ids: continue
            users_need = db.get_users_who_need_reminder(target_role_ids, guild)
            if not users_need: continue
            ch_mention = f"<#{db.get_setting('characters_channel_id', '')}>" if db.get_setting('characters_channel_id', '') else "канале"
            msg_tpl = db.get_setting('character_reminder_message', '').format(channel=ch_mention)
            for u in users_need:
                try:
                    await u['user'].send(msg_tpl)
                    db.update_reminder_sent(u['user_id'])
                    await asyncio.sleep(1)
                except: pass

    @tasks.loop(hours=1)
    async def weekly_cleanup_task(self):
        now = datetime.now()
        if now.weekday() == 6 and now.hour == 0 and now.minute < 5:
            for guild in self.guilds:
                db = self.get_db(guild.id)
                if not db: continue
                for key in ['composition_channel', 'composition_control_channel']:
                    ch_id = utils.safe_int(db.get_setting(key, ''))
                    if ch_id:
                        ch = guild.get_channel(ch_id)
                        if ch:
                            try:
                                async for msg in ch.history(limit=100):
                                    if msg.author == self.user:
                                        await msg.delete()
                            except: pass
                db.cursor.execute('DELETE FROM raid_members')
                db.cursor.execute('DELETE FROM raids')
                db.conn.commit()

# ========== ФУНКЦИИ ВОССТАНОВЛЕНИЯ ПАНЕЛЕЙ ==========

async def restore_battle_panels():
    restored = 0
    deleted = 0
    for msg_id, panel_info in list(active_panels.items()):
        try:
            guild = bot.get_guild(panel_info['guild_id'])
            if not guild: del active_panels[msg_id]; deleted += 1; continue
            db = bot.get_db(panel_info['guild_id'])
            if not db: continue
            channel = guild.get_channel(panel_info['channel_id'])
            if not channel: del active_panels[msg_id]; deleted += 1; continue
            voice_channel = guild.get_channel(panel_info['voice_channel_id'])
            if not voice_channel:
                try: await (await channel.fetch_message(msg_id)).delete()
                except: pass
                del active_panels[msg_id]; deleted += 1; continue
            try: await (await channel.fetch_message(msg_id)).delete()
            except: pass
            del active_panels[msg_id]
            battle_config = panel_info.get('battle_config', {})
            mode_names = {"standard":"⚔️ Стандартный","strict":"🔒 Строгий","free":"🆓 Свободный","custom":"🎯 Выборочный"}
            mode = battle_config.get('mode','standard')
            embed = Embed(title="⚔️ ПАНЕЛЬ УПРАВЛЕНИЯ БОЕМ",description=f"**🔊 Канал:** {voice_channel.name}\n**👑 Создал:** <@{panel_info['creator_id']}>\n**⚙️ Режим:** {mode_names.get(mode)}",color=Color.blue())
            embed.add_field(name="⚡ Управление",value="🔇 НАЧАТЬ БОЙ | ⚙️ РЕЖИМ | 🗑️ ЗАКРЫТЬ",inline=False)
            view = create_restored_battle_view(battle_config, panel_info, db, guild)
            new_message = await channel.send(embed=embed, view=view)
            active_panels[new_message.id] = {'channel_id':panel_info['channel_id'],'guild_id':panel_info['guild_id'],'voice_channel_id':panel_info['voice_channel_id'],'created_at':datetime.now(),'creator_id':panel_info['creator_id'],'empty_since':None,'battle_ended_at':None,'battle_config':battle_config}
            restored += 1
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            if msg_id in active_panels: del active_panels[msg_id]; deleted += 1
    print(f"📊 Панели: +{restored} -{deleted}")
    save_active_panels()

def create_restored_battle_view(battle_config, panel_info, db, guild):
    class V(View):
        def __init__(self): super().__init__(timeout=None)
        @discord.ui.button(label="🔇 НАЧАТЬ БОЙ", style=ButtonStyle.danger, emoji="⚔️", row=0)
        async def start_btn(self, inter, button):
            if inter.response.is_done(): return
            cdb = bot.get_db(inter.guild_id)
            if not cdb: await inter.response.send_message("❌ БД!", ephemeral=True); return
            if not (utils.is_guild_master(inter.user,cdb) or utils.is_vice_master(inter.user,cdb) or utils.is_raid_leader(inter.user,cdb)): await inter.response.send_message("❌ Права!", ephemeral=True); return
            ch = guild.get_channel(battle_config['channel_id'])
            if not ch: await inter.response.send_message("❌ Канал!", ephemeral=True); return
            unmuted = get_unmuted_ids(ch, battle_config, guild.id, inter.user.id)
            for m in ch.members:
                if m.bot: continue
                try:
                    if m.id in unmuted:
                        if m.voice and m.voice.mute: await m.edit(mute=False)
                    else:
                        if m.voice and not m.voice.mute: await m.edit(mute=True)
                except: pass
            active_battles[guild.id] = {'channel':ch,'unmuted':unmuted,'config':battle_config}
            ev = create_restored_end_view(battle_config, panel_info, db, guild)
            emb = Embed(title="⚔️ БОЙ ИДЁТ!", color=Color.red())
            await inter.response.edit_message(embed=emb, view=ev)
        @discord.ui.button(label="⚙️ РЕЖИМ", style=ButtonStyle.primary, emoji="⚙️", row=1)
        async def mode_btn(self, inter, button): await inter.response.send_message("⚙️ Через меню", ephemeral=True)
        @discord.ui.button(label="🗑️ ЗАКРЫТЬ", style=ButtonStyle.danger, emoji="🗑️", row=2)
        async def close_btn(self, inter, button):
            if inter.response.is_done(): return
            if guild.id in active_battles:
                ch = guild.get_channel(battle_config['channel_id'])
                if ch:
                    for m in ch.members:
                        if m.bot: continue
                        try:
                            if m.voice and m.voice.mute: await m.edit(mute=False)
                        except: pass
                del active_battles[guild.id]
            if inter.message.id in active_panels: del active_panels[inter.message.id]; save_active_panels()
            await inter.message.delete()
    return V()

def create_restored_end_view(battle_config, panel_info, db, guild):
    class V(View):
        def __init__(self): super().__init__(timeout=None)
        @discord.ui.button(label="🔊 ЗАВЕРШИТЬ", style=ButtonStyle.success, emoji="✅", row=0)
        async def end_btn(self, inter, button):
            if inter.response.is_done(): return
            ch = guild.get_channel(battle_config['channel_id'])
            if ch:
                for m in ch.members:
                    if m.bot: continue
                    try:
                        if m.voice and m.voice.mute: await m.edit(mute=False)
                    except: pass
            if guild.id in active_battles: del active_battles[guild.id]
            bv = create_restored_battle_view(battle_config, panel_info, db, guild)
            await inter.response.edit_message(embed=Embed(title="✅ БОЙ ЗАВЕРШЁН!", color=Color.green()), view=bv)
        @discord.ui.button(label="🔄 ОБНОВИТЬ", style=ButtonStyle.secondary, emoji="🔄", row=1)
        async def refresh_btn(self, inter, button):
            if inter.response.is_done(): return
            if guild.id not in active_battles: await inter.response.send_message("❌ Нет боя!", ephemeral=True); return
            await inter.response.edit_message(embed=Embed(title="⚔️ БОЙ ИДЁТ!", color=Color.red()))
        @discord.ui.button(label="🗑️ УДАЛИТЬ", style=ButtonStyle.danger, emoji="🗑️", row=2)
        async def delete_btn(self, inter, button):
            if inter.response.is_done(): return
            ch = guild.get_channel(battle_config['channel_id'])
            if ch:
                for m in ch.members:
                    if m.bot: continue
                    try:
                        if m.voice and m.voice.mute: await m.edit(mute=False)
                    except: pass
            if guild.id in active_battles: del active_battles[guild.id]
            if inter.message.id in active_panels: del active_panels[inter.message.id]; save_active_panels()
            await inter.message.delete()
    return V()

async def update_apply_embed(self, guild):
    db = self.get_db(guild.id)
    if not db:
        return
    msg_data = db.get_message('apply')
    if not msg_data:
        return
    channel = guild.get_channel(msg_data[0])
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
    apply_embed = Embed(
        title=f"🏰 {guild_name.upper()}",
        description=(
            f"**▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬**\n"
            f"    ДОБРО ПОЖАЛОВАТЬ В ГИЛЬДИЮ!\n"
            f"**▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬**\n\n"
            f"**🌍 Сервер**`{server}\n"
            f"**⚔️ Фракция**`{faction}\n"
            f"**📅 Рейдовое время**`{raid_times}\n"
        ),
        color=Color.purple()
    )
    apply_desc = db.get_setting('apply_description', '')
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
    if guild.icon:
        apply_embed.set_thumbnail(url=guild.icon.url)
    apply_embed.set_footer(
        text=f"⭐ {guild_name} • Sirus x3 • Присоединяйся! ⭐",
        icon_url=guild.icon.url if guild.icon else None
    )
    await msg.edit(embed=apply_embed)

# ========== АВТООЧИСТКА ПАНЕЛЕЙ ==========

@tasks.loop(minutes=5)
async def cleanup_inactive_panels():
    current_time = datetime.now()
    for message_id, panel_info in list(active_panels.items()):
        try:
            guild = bot.get_guild(panel_info['guild_id'])
            if not guild: del active_panels[message_id]; continue
            channel = guild.get_channel(panel_info['channel_id'])
            if not channel: del active_panels[message_id]; continue
            voice_channel = guild.get_channel(panel_info['voice_channel_id'])
            should_delete = False
            if not voice_channel: should_delete = True
            elif len(voice_channel.members) == 0:
                if panel_info.get('empty_since'):
                    if (current_time - panel_info['empty_since']).total_seconds() > 1800: should_delete = True
                else: panel_info['empty_since'] = current_time
            else: panel_info['empty_since'] = None
            if not should_delete and panel_info.get('created_at'):
                if (current_time - panel_info['created_at']).total_seconds() > 86400: should_delete = True
            if not should_delete and panel_info['guild_id'] not in active_battles:
                if panel_info.get('battle_ended_at'):
                    if (current_time - panel_info['battle_ended_at']).total_seconds() > 3600: should_delete = True
            if should_delete:
                try: await (await channel.fetch_message(message_id)).delete()
                except: pass
                if message_id in active_panels: del active_panels[message_id]
        except: pass

@cleanup_inactive_panels.before_loop
async def before_cleanup(): await bot.wait_until_ready()

# ========== ОБРАБОТЧИК УДАЛЕНИЯ КАНАЛА ==========
bot = GuildBot()

@bot.event
async def on_guild_channel_delete(channel):
    if isinstance(channel, discord.VoiceChannel):
        for msg_id in [m for m, i in active_panels.items() if i['voice_channel_id'] == channel.id]:
            try: await (await channel.guild.get_channel(active_panels[msg_id]['channel_id']).fetch_message(msg_id)).delete()
            except: pass
            if msg_id in active_panels: del active_panels[msg_id]
        if channel.guild.id in active_battles:
            if active_battles[channel.guild.id].get('channel') and active_battles[channel.guild.id]['channel'].id == channel.id:
                del active_battles[channel.guild.id]

# ========== ОСНОВНЫЕ КОМАНДЫ ==========

@bot.tree.command(name="set_developer", description="🔧 Назначить разработчика по ID")
@app_commands.describe(user_id="ID пользователя Discord (цифры)")
async def set_developer(interaction: discord.Interaction, user_id: str):
    if interaction.user.id != config.BOT_OWNER_ID:
        await interaction.response.send_message("❌ Нет прав! Только владелец бота.", ephemeral=True)
        return
    if not user_id.isdigit():
        await interaction.response.send_message("❌ Неверный ID! Введите числовой ID.", ephemeral=True)
        return
    db = bot.get_db(interaction.guild_id)
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    current_dev = db.get_setting('developer_id', '')
    if current_dev and current_dev != user_id:
        await interaction.response.send_message(f"❌ Разработчик уже назначен! Сначала удалите через `/remove_developer`.\nТекущий: <@{current_dev}>", ephemeral=True)
        return
    db.set_setting('developer_id', user_id)
    db.add_log("🔧 Разработчик", interaction.user.id, int(user_id), "Назначен разработчик")
    try:
        user = await bot.fetch_user(int(user_id))
        if user:
            embed = Embed(title="🔧 Вы назначены разработчиком!", description=f"Сервер: **{interaction.guild.name}**\nНазначил: **{interaction.user.display_name}**\n\nПолный доступ ко всем функциям бота!", color=Color.purple())
            await user.send(embed=embed)
    except: pass
    await interaction.response.send_message(f"✅ Разработчик: <@{user_id}>", ephemeral=True)

@bot.tree.command(name="remove_developer", description="🔧 Удалить разработчика")
async def remove_developer(interaction: discord.Interaction):
    if interaction.user.id != config.BOT_OWNER_ID:
        await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
        return
    db = bot.get_db(interaction.guild_id)
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    current_dev = db.get_setting('developer_id', '')
    if not current_dev:
        await interaction.response.send_message("❌ Разработчик не назначен!", ephemeral=True)
        return
    db.set_setting('developer_id', '')
    db.add_log("🔧 Разработчик", interaction.user.id, int(current_dev), "Разработчик удалён")
    try:
        user = await bot.fetch_user(int(current_dev))
        if user:
            await user.send(embed=Embed(title="🔧 Вы сняты с должности разработчика", description=f"Сервер: **{interaction.guild.name}**", color=Color.red()))
    except: pass
    await interaction.response.send_message(f"✅ Разработчик <@{current_dev}> удалён!", ephemeral=True)

@bot.tree.command(name="my_permissions", description="🔐 Показать ваши права")
async def my_permissions(interaction: discord.Interaction):
    db = bot.get_db(interaction.guild_id)
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    user = interaction.user
    is_dev = db.get_setting('developer_id', '') == str(user.id)
    is_gm = utils.is_guild_master(user, db)
    is_vm = utils.is_vice_master(user, db)
    is_rl = utils.is_raid_leader(user, db)
    is_of = utils.is_officer(user, db)
    if is_dev:
        level = "🔧 Разработчик (полный доступ)"
        color = Color.purple()
    elif is_gm:
        level = "👑 Глава гильдии"
        color = Color.gold()
    elif is_vm:
        level = "⭐ Зам. главы"
        color = Color.gold()
    elif is_rl:
        level = "⚔️ Рейд-лидер"
        color = Color.blue()
    elif is_of:
        level = "📋 Офицер"
        color = Color.blue()
    else:
        level = "👤 Участник"
        color = Color.greyple()
    embed = Embed(title="🔐 Ваши права", description=f"**Уровень:** {level}", color=color)
    permissions = []
    if utils.can_manage_applications(user, db): permissions.append("✅ 📝 Управление заявками")
    else: permissions.append("📝 Подача заявок")
    if utils.can_manage_appeals(user, db): permissions.append("✅ ⚖️ Управление апелляциями")
    else: permissions.append("⚖️ Подача апелляций")
    if utils.can_manage_characters(user, db): permissions.append("✅ 👥 Просмотр всех персонажей")
    else: permissions.append("👥 Свои персонажи")
    if utils.can_issue_punishments(user, db): permissions.append("✅ ⚠️ Выдача наказаний")
    if utils.can_remove_punishments(user, db): permissions.append("✅ 📋 Снятие наказаний")
    if not utils.can_issue_punishments(user, db) and not utils.can_remove_punishments(user, db): permissions.append("📝 Выполнение заданий")
    if utils.can_manage_absences(user, db): permissions.append("✅ 📅 Отметка отсутствий")
    else: permissions.append("📅 Заявка на отсутствие")
    if utils.can_manage_raids(user, db): permissions.append("✅ 🎯 Создание составов")
    if utils.can_manage_compositions(user, db): permissions.append("✅ 📋 Управление составами")
    if utils.can_accept_static(user, db): permissions.append("✅ ⭐ Принятие в статик")
    else: permissions.append("📋 Запрос в статик")
    if utils.can_approve_main_change(user, db): permissions.append("✅ 🔄 Одобрение смены")
    else: permissions.append("🔄 Смена персонажа")
    if utils.can_use_admin_center(user, db): permissions.append("✅ 🔧 Админ-центр")
    if utils.can_manage_settings(user, db): 
        permissions.append("✅ ⚙️ Настройки бота")
        permissions.append("✅ 🗑️ Очистка БД")
    embed.add_field(name="📋 Доступные действия", value="\n".join(permissions), inline=False)
    embed.set_footer(text="По вопросам — Техподдержка в Мои персонажи")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="clear_db", description="🗑️ Очистить базу данных")
@app_commands.choices(target=[
    app_commands.Choice(name="📝 Заявки", value="applications"),
    app_commands.Choice(name="🚫 ЧС", value="blacklist"),
    app_commands.Choice(name="⚖️ Апелляции", value="appeals"),
    app_commands.Choice(name="📅 Отсутствия", value="absences"),
    app_commands.Choice(name="🎮 Персонажи", value="characters"),
    app_commands.Choice(name="⚠️ Наказания", value="punishments"),
    app_commands.Choice(name="📋 Составы", value="raids"),
    app_commands.Choice(name="💾 ВСЁ", value="all")
])
async def clear_db(interaction: discord.Interaction, target: str):
    db = bot.get_db(interaction.guild_id)
    if not db: return
    if str(interaction.user.id) != db.get_setting('developer_id', ''):
        await interaction.response.send_message("❌ Только разработчик!", ephemeral=True)
        return
    if target == 'all': db.clear_all_data()
    else: db.clear_table(target)
    db.add_log("🗑️ Очистка", interaction.user.id, details=f"Очищено: {target}")
    await interaction.response.send_message(f"✅ Очищено: {target}", ephemeral=True, delete_after=10)

@bot.tree.command(name="settings", description="⚙️ Настройка бота")
async def settings_command(interaction: discord.Interaction):
    if not utils.can_manage_settings(interaction.user, interaction.client.db):
        await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
        return
    view = SettingsView()
    await interaction.response.send_message(embed=Embed(title="⚙️ Панель управления", description="Выберите раздел:", color=Color.blue()), view=view, ephemeral=True)

@bot.tree.command(name="setup", description="🚀 Автонастройка")
async def setup_command(interaction: discord.Interaction):
    if not utils.can_manage_settings(interaction.user, interaction.client.db):
        await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
        return
    await interaction.response.defer(ephemeral=True)
    db = interaction.client.db
    guild = interaction.guild
    app_cat = await guild.create_category_channel("📝 Заявки в гильдию")
    appeal_cat = await guild.create_category_channel("⚖️ Апелляции")
    punish_cat = await guild.create_category_channel("⚠️ Наказания")
    chars_cat = await guild.create_category_channel("🎮 Управление персонажами")
    tasks_cat = await guild.create_category_channel("📝 Задания")
    change_cat = await guild.create_category_channel("🔄 Смена персонажа")
    static_cat = await guild.create_category_channel("📋 Запросы в статик")
    db.set_setting('applications_category', str(app_cat.id))
    db.set_setting('appeal_category', str(appeal_cat.id))
    db.set_setting('tasks_category', str(tasks_cat.id))
    db.set_setting('main_change_category', str(change_cat.id))
    db.set_setting('static_request_category', str(static_cat.id))
    apply_ch = await guild.create_text_channel("📝-подать-заявку", category=app_cat)
    appeal_ch = await guild.create_text_channel("⚖️-подать-апелляцию", category=appeal_cat)
    punish_ch = await guild.create_text_channel("⚠️-наказания", category=punish_cat)
    chars_ch = await guild.create_text_channel("🎮-мои-персонажи", category=chars_cat)
    absence_ch = await guild.create_text_channel("📅-отсутствия")
    archive_ch = await guild.create_text_channel("📁-архив-заявок")
    log_ch = await guild.create_text_channel("📝-логи-бота")
    comp_display_ch = await guild.create_text_channel("📋-составы-рейдов")
    comp_ctrl_ch = await guild.create_text_channel("🎯-управление-составами")
    for key, ch in [
        ('applications_channel', apply_ch), ('appeal_channel', appeal_ch),
        ('punishment_channel', punish_ch), ('characters_channel_id', chars_ch),
        ('absence_channel', absence_ch), ('archive_channel', archive_ch),
        ('log_channel', log_ch), ('composition_channel', comp_display_ch),
        ('composition_control_channel', comp_ctrl_ch)
    ]:
        db.set_setting(key, str(ch.id))
    for ch in [apply_ch, appeal_ch]:
        await ch.set_permissions(guild.default_role, read_messages=False)
    apply_embed = Embed(
        title="📝 Вступление в гильдию",
        description=f"**{db.get_setting('guild_name', 'Abuse')}** приглашает!\n\n"
                    f"🌍 **Сервер:** {db.get_setting('server', 'Sirus')}\n"
                    f"⚔️ **Фракция:** {db.get_setting('faction', 'Alliance')}\n"
                    f"📅 **Рейды:** {db.get_setting('raid_times', '20:00 МСК')}",
        color=Color.purple()
    )
    apply_desc = db.get_setting('apply_description', '')
    if apply_desc:
        apply_embed.add_field(name="📋 Требования", value=apply_desc, inline=False)
    apply_embed.set_footer(text="Нажмите кнопку ниже, чтобы подать заявку")
    msg1 = await apply_ch.send(embed=apply_embed, view=ApplyView())
    db.save_message('apply', apply_ch.id, msg1.id)
    msg2 = await appeal_ch.send(embed=Embed(title="⚖️ Апелляция", description="Нажмите кнопку чтобы подать апелляцию.", color=Color.orange()), view=AppealMainView())
    db.save_message('appeal', appeal_ch.id, msg2.id)
    today = datetime.now()
    msg3 = await absence_ch.send(embed=build_calendar_embed(guild, db, today.year, today.month), view=AbsenceMainView())
    db.save_message('absence', absence_ch.id, msg3.id)
    msg4 = await chars_ch.send(embed=Embed(title="🎮 Управление персонажами", description="Управляйте своими персонажами.", color=Color.blue()), view=CharactersMainView())
    db.save_message('characters', chars_ch.id, msg4.id)
    msg5 = await punish_ch.send(embed=Embed(title="⚠️ Система наказаний", description="Выдача и снятие наказаний.", color=Color.red()), view=PunishmentMainView())
    db.save_message('punishment', punish_ch.id, msg5.id)
    msg6 = await comp_ctrl_ch.send(embed=Embed(title="🎯 Управление составами", description="Создавайте составы.", color=Color.blue()), view=CompositionCreateButton())
    db.save_message('composition_button', comp_ctrl_ch.id, msg6.id)
    db.add_log("🚀 Настройка", interaction.user.id, details="Автонастройка завершена")
    await interaction.followup.send("✅ Автонастройка завершена!", ephemeral=True)

# ========== ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ ==========

@bot.tree.command(name="update_buttons", description="🔄 Обновить все кнопки")
async def update_buttons(interaction: discord.Interaction):
    db = bot.get_db(interaction.guild_id)
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    if str(interaction.user.id) != db.get_setting('developer_id', '') and not utils.can_manage_settings(interaction.user, db):
        await interaction.response.send_message("❌ У вас нет прав!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    all_msgs = db.get_all_messages()
    if not all_msgs:
        await interaction.followup.send("❌ Таблица `messages` пуста! Выполните `/setup`.", ephemeral=True)
        return
    views_map = {}
    try: from views.applications import ApplyView; views_map['apply'] = ApplyView()
    except: pass
    try: from views.appeals import AppealMainView; views_map['appeal'] = AppealMainView()
    except: pass
    try: from views.absences import AbsenceMainView; views_map['absence'] = AbsenceMainView()
    except: pass
    try: from views.characters import CharactersMainView; views_map['characters'] = CharactersMainView()
    except: pass
    try: from views.punishments import PunishmentMainView; views_map['punishment'] = PunishmentMainView()
    except: pass
    try: from views.compositions import CompositionCreateButton; views_map['composition_button'] = CompositionCreateButton()
    except: pass
    updated = []
    for key, view in views_map.items():
        msg_data = db.get_message(key)
        if msg_data:
            channel = interaction.guild.get_channel(msg_data[0])
            if channel:
                try:
                    msg = await channel.fetch_message(msg_data[1])
                    if key == 'apply':
                        guild_name = db.get_setting('guild_name', 'Abuse')
                        server = db.get_setting('server', 'Sirus')
                        faction = db.get_setting('faction', 'Alliance')
                        raid_times = db.get_setting('raid_times', '20:00 МСК')
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
                        apply_desc = db.get_setting('apply_description', '')
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
                        await msg.edit(embed=apply_embed, view=view)
                    elif key == 'absence':
                        today = datetime.now()
                        new_embed = build_calendar_embed(interaction.guild, db, today.year, today.month)
                        await msg.edit(embed=new_embed, view=view)
                    else:
                        await msg.edit(view=view)
                    updated.append(f"✅ `{key}`")
                except:
                    updated.append(f"❌ `{key}`")
            else:
                updated.append(f"❌ `{key}` (канал)")
    await interaction.followup.send("📊 **Результат:**\n" + "\n".join(updated), ephemeral=True)

@bot.tree.command(name="calendar", description="📅 Показать календарь отсутствий")
async def calendar_command(interaction: discord.Interaction):
    db = bot.get_db(interaction.guild_id)
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    today = datetime.now()
    embed = build_calendar_embed(interaction.guild, db, today.year, today.month)
    view = AbsenceMainView()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

@bot.tree.command(name="absence_limits", description="⚙️ Настроить лимиты отсутствий")
@app_commands.describe(
    week="Максимум дней в неделю (0=безлимит)",
    month="Максимум дней в месяц (0=безлимит)",
    consecutive="Максимум дней подряд (0=безлимит)",
    raids="Максимум пропущенных рейдов (0=безлимит)"
)
async def set_absence_limits(interaction: discord.Interaction, week: int = None, month: int = None, consecutive: int = None, raids: int = None):
    db = bot.get_db(interaction.guild_id)
    if not db or not utils.can_manage_settings(interaction.user, db):
        await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
        return
    if week is not None: db.set_setting('absence_limit_week', str(week))
    if month is not None: db.set_setting('absence_limit_month', str(month))
    if consecutive is not None: db.set_setting('absence_limit_consecutive', str(consecutive))
    if raids is not None: db.set_setting('absence_limit_raids', str(raids))
    limits = db.get_absence_limits()
    embed = Embed(title="⚙️ Лимиты отсутствий", color=Color.green())
    embed.add_field(name="📅 Неделя", value=f"**{limits['week']}** дн.", inline=True)
    embed.add_field(name="📆 Месяц", value=f"**{limits['month']}** дн.", inline=True)
    embed.add_field(name="🔒 Подряд", value=f"**{limits['consecutive']}** дн.", inline=True)
    embed.add_field(name="⚔️ Рейдов", value=f"**{limits['raids']}** рейдов", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="help", description="📖 Справка по боту")
async def help_command(interaction: discord.Interaction):
    embed = Embed(title="⚔️ Guild Bot — Твой помощник в гильдии", description="Привет! Я помогаю управлять гильдией на Sirus x3.\nВот что я умею:", color=Color.purple(), timestamp=discord.utils.utcnow())
    embed.add_field(name="👤 Для всех участников", value="📝 Подать заявку\n⚖️ Подать апелляцию\n👥 Мои персонажи\n📅 Отсутствие\n📋 Запрос в статик\n📝 Выполнить задание", inline=False)
    embed.add_field(name="👮 Для офицеров", value="📋 Заявки\n⚠️ Наказания\n👁️ Просмотр персонажей\n📅 Отсутствия", inline=False)
    embed.add_field(name="👑 Для руководства", value="🎯 Составы\n⭐ Статик\n⚙️ Настройки\n🗑️ Очистка БД", inline=False)
    embed.add_field(name="💡 Команды", value="🔐 `/my_permissions` — права\n📅 `/calendar` — календарь\n📋 `/logs` — логи\n📖 `/help` — справка", inline=False)
    embed.add_field(name="🛠️ Нужна помощь?", value="Нажми кнопку **'🛠️ Техподдержка'** в разделе **'Мои персонажи'**.\nРазработчик получит сообщение и поможет!", inline=False)
    embed.set_footer(text="Guild Bot v2.0 | Sirus x3")
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="logs", description="📋 Последние действия (логи)")
async def view_logs(interaction: discord.Interaction):
    db = bot.get_db(interaction.guild_id)
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    if not utils.can_manage_settings(interaction.user, db):
        await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
        return
    logs = db.get_recent_logs(20)
    if not logs:
        await interaction.response.send_message("📭 Логи пусты.", ephemeral=True)
        return
    embed = Embed(title="📋 Последние действия", color=Color.blue(), timestamp=discord.utils.utcnow())
    for action, user_id, target_id, details, created_at in logs[:20]:
        user = interaction.guild.get_member(user_id)
        user_name = user.display_name if user else f"ID:{user_id}"
        target_text = ""
        if target_id:
            target = interaction.guild.get_member(target_id)
            target_text = f" → {target.display_name if target else f'ID:{target_id}'}"
        embed.add_field(
            name=f"{action} — {user_name}{target_text}",
            value=f"{details[:100]}\n{created_at}",
            inline=False
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="refresh_all_views", description="🔄 Полное обновление всех View (разработчик)")
async def refresh_all_views(interaction: discord.Interaction):
    db = bot.get_db(interaction.guild_id)
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    if str(interaction.user.id) != db.get_setting('developer_id', ''):
        await interaction.response.send_message("❌ Только разработчик!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    for view in bot.persistent_views:
        view.stop()
    bot.persistent_views.clear()
    await bot.restore_views()
    await interaction.followup.send("✅ Все View перезагружены!", ephemeral=True)

@bot.tree.command(name="ping", description="🏓 Проверка задержки")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Понг!", ephemeral=True)

@bot.tree.command(name="admin_panel_setup", description="🔧 Создать канал админ-центра с кнопками")
async def admin_panel_setup(interaction: discord.Interaction):
    db = bot.get_db(interaction.guild_id)
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    if not utils.is_developer(interaction.user, db):
        await interaction.response.send_message("❌ Только разработчик может настраивать админ-центр!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild
    existing_channel_id = utils.safe_int(db.get_setting('admin_channel', ''))
    if existing_channel_id:
        existing_channel = guild.get_channel(existing_channel_id)
        if existing_channel:
            await interaction.followup.send(
                f"⚠️ Канал админ-центра уже существует: {existing_channel.mention}\n"
                f"Используйте `/admin_panel` чтобы обновить кнопки в существующем канале.",
                ephemeral=True
            )
            return
    category = None
    cat_id = utils.safe_int(db.get_setting('admin_category', ''))
    if cat_id:
        category = guild.get_channel(cat_id)
    if not category:
        category = await guild.create_category_channel("🔧 Управление")
        db.set_setting('admin_category', str(category.id))
    admin_ch = await guild.create_text_channel(
        "🔧-админ-центр",
        category=category,
        topic="Панель управления гильдией | Только для администраторов"
    )
    await admin_ch.set_permissions(guild.default_role, read_messages=False)
    await admin_ch.set_permissions(guild.me, read_messages=True, send_messages=True)
    db.set_setting('admin_channel', str(admin_ch.id))
    view = AdminCenterView()
    embed = Embed(
        title="🔧 Админ-центр",
        description=(
            "Добро пожаловать в панель управления гильдией!\n\n"
            "**Доступные действия:**\n"
            "👤 **Найти участника** — полная карточка участника\n"
            "🎮 **Найти персонажа** — поиск по имени персонажа\n"
            "🗑️ **Удалить данные** — удаление данных пользователя\n"
            "📊 **Статистика** — общая сводка по гильдии\n"
            "🔄 **Сброс попыток** — сброс ограничений на подачу заявок\n\n"
            "⚙️ **Права доступа** выдаются в `/settings` → 🔐 Права доступа → `admin_center`"
        ),
        color=Color.blue(),
        timestamp=datetime.now()
    )
    embed.set_footer(text=f"Сервер: {guild.name} | Разработчик: {interaction.user.display_name}")
    await admin_ch.send(embed=embed, view=view)
    db.add_log("🔧 Админ-центр", interaction.user.id, details=f"Канал создан: {admin_ch.name}")
    await interaction.followup.send(
        f"✅ **Админ-центр создан!**\n\n"
        f"📁 Канал: {admin_ch.mention}\n"
        f"🔐 Права доступа: `/settings` → 🔐 Права доступа → `admin_center`\n"
        f"🔄 Обновить кнопки: `/admin_panel`",
        ephemeral=True
    )

@bot.tree.command(name="admin_panel", description="🔄 Обновить кнопки в канале админ-центра")
async def admin_panel(interaction: discord.Interaction):
    db = bot.get_db(interaction.guild_id)
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    if not utils.is_developer(interaction.user, db):
        await interaction.response.send_message("❌ Только разработчик!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    channel_id = utils.safe_int(db.get_setting('admin_channel', ''))
    if not channel_id:
        await interaction.followup.send(
            "❌ Канал админ-центра не настроен!\n"
            "Выполните `/admin_panel_setup` для создания.",
            ephemeral=True
        )
        return
    channel = interaction.guild.get_channel(channel_id)
    if not channel:
        await interaction.followup.send("❌ Канал не найден! Создайте новый: `/admin_panel_setup`", ephemeral=True)
        return
    try:
        async for msg in channel.history(limit=50):
            if msg.author == interaction.client.user:
                await msg.delete()
    except: pass
    view = AdminCenterView()
    embed = Embed(
        title="🔧 Админ-центр",
        description=(
            "Панель управления гильдией\n\n"
            "👤 Найти участника | 🎮 Найти персонажа\n"
            "🗑️ Удалить данные | 📊 Статистика\n"
            "🔄 Сброс попыток\n\n"
            "⚙️ Права: `/settings` → 🔐 Права доступа → `admin_center`"
        ),
        color=Color.blue(),
        timestamp=datetime.now()
    )
    await channel.send(embed=embed, view=view)
    db.add_log("🔄 Админ-центр", interaction.user.id, details="Кнопки обновлены")
    await interaction.followup.send(f"✅ Кнопки обновлены в {channel.mention}!", ephemeral=True)


# ========== КОМАНДЫ УПРАВЛЕНИЯ БОЕМ ==========

@bot.tree.command(name="pull_panel", description="⚔️ Создать панель управления боем")
async def pull_panel(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    db = bot.get_db(interaction.guild_id)
    if not db:
        await interaction.followup.send("❌ БД не найдена!", ephemeral=True)
        return
    
    # Проверка прав: Глава, Зам, РЛ или разработчик
    if not (utils.is_guild_master(interaction.user, db) or 
            utils.is_vice_master(interaction.user, db) or 
            utils.is_raid_leader(interaction.user, db) or
            str(interaction.user.id) == db.get_setting('developer_id', '')):
        await interaction.followup.send("❌ Только Глава, Зам. главы, Рейд-лидер или Разработчик!", ephemeral=True)
        return
    
    voice_channels = interaction.guild.voice_channels
    if not voice_channels:
        await interaction.followup.send("❌ Нет голосовых каналов!", ephemeral=True)
        return
    
    # Сортируем: сначала с людьми, потом пустые
    voice_channels.sort(key=lambda vc: (-len(vc.members), vc.name))
    
    # Опции каналов
    options = []
    for vc in voice_channels:
        member_count = len(vc.members)
        if member_count > 0:
            options.append(discord.SelectOption(
                label=vc.name, value=str(vc.id),
                description=f"👥 {member_count} участников",
                emoji="🔊"
            ))
        else:
            options.append(discord.SelectOption(
                label=vc.name, value=str(vc.id),
                description="Пустой канал",
                emoji="🔹"
            ))
    
    # Режимы боя
    battle_modes = [
        discord.SelectOption(label="Стандартный бой", value="standard", description="Говорят: Глава, Зам, РЛ, Ст.Офицер, Офицер", emoji="⚔️"),
        discord.SelectOption(label="Строгий бой", value="strict", description="Говорят: Глава, Зам, РЛ", emoji="🔒"),
        discord.SelectOption(label="Свободный бой", value="free", description="Говорят: Глава, Зам, РЛ, все Офицеры", emoji="🆓"),
        discord.SelectOption(label="Выборочный бой", value="custom", description="Выбрать кто будет говорить", emoji="🎯")
    ]
    
    mode_names = {
        "standard": "⚔️ Стандартный",
        "strict": "🔒 Строгий",
        "free": "🆓 Свободный",
        "custom": "🎯 Выборочный"
    }
    
    mode_descriptions = {
        "standard": "👑 Глава | ⭐ Зам | ⚔️ РЛ | ⭐ Ст.Офицер | 📋 Офицер",
        "strict": "👑 Глава | ⭐ Зам | ⚔️ РЛ",
        "free": "👑 Глава | ⭐ Зам | ⚔️ РЛ | ⭐ Все Офицеры",
        "custom": "Выбрано вручную"
    }
    
    class ChannelAndModeSelect(View):
        def __init__(self):
            super().__init__(timeout=120)
            self.selected_channel = None
            self.selected_mode = None
            
            channel_select = Select(placeholder="1️⃣ Выберите канал...", options=options[:25])
            channel_select.callback = self.channel_callback
            self.add_item(channel_select)
            
            mode_select = Select(placeholder="2️⃣ Выберите режим боя...", options=battle_modes)
            mode_select.callback = self.mode_callback
            self.add_item(mode_select)
        
        async def channel_callback(self, inter: discord.Interaction):
            self.selected_channel = int(inter.data['values'][0])
            await inter.response.defer()
        
        async def mode_callback(self, inter: discord.Interaction):
            self.selected_mode = inter.data['values'][0]
            
            if self.selected_channel is None:
                await inter.response.send_message("❌ Сначала выберите канал!", ephemeral=True)
                return
            
            if self.selected_mode == "custom":
                await self.show_member_selection(inter)
            else:
                await self.create_battle_panel(inter)
        
        async def show_member_selection(self, inter: discord.Interaction):
            channel = interaction.guild.get_channel(self.selected_channel)
            if not channel:
                await inter.response.send_message("❌ Канал не найден!", ephemeral=True)
                return
            
            members = [m for m in channel.members if not m.bot]
            if not members:
                await inter.response.send_message("❌ В канале нет участников!", ephemeral=True)
                return
            
            member_options = []
            for m in members[:25]:
                role_tag = ""
                if utils.is_guild_master(m, db): role_tag = "👑 "
                elif utils.is_vice_master(m, db): role_tag = "⭐ "
                elif utils.is_raid_leader(m, db): role_tag = "⚔️ "
                
                member_options.append(discord.SelectOption(
                    label=f"{role_tag}{m.display_name}",
                    value=str(m.id),
                    emoji="🎤"
                ))
            
            embed_members = Embed(
                title="🎯 Выберите кто будет говорить",
                description=f"**Канал:** {channel.name}\nВыберите участников для голоса.",
                color=Color.purple()
            )
            
            class MemberSelect(View):
                def __init__(self):
                    super().__init__(timeout=60)
                    select = Select(
                        placeholder="Выберите участников...",
                        options=member_options,
                        max_values=len(member_options),
                        min_values=1
                    )
                    select.callback = self.select_callback
                    self.add_item(select)
                
                async def select_callback(self, inter2: discord.Interaction):
                    selected_members = [int(v) for v in inter2.data['values']]
                    await self.create_battle_panel(inter2, custom_members=selected_members)
            
            await inter.response.edit_message(embed=embed_members, view=MemberSelect())
        
        async def create_battle_panel(self, inter, custom_members=None):
            channel = interaction.guild.get_channel(self.selected_channel)
            if not channel:
                await inter.response.send_message("❌ Канал не найден!", ephemeral=True)
                return
            
            battle_config = {
                'channel_id': self.selected_channel,
                'mode': self.selected_mode,
                'custom_members': custom_members or [],
                'creator_id': inter.user.id
            }
            
            embed = Embed(
                title="⚔️ ПАНЕЛЬ УПРАВЛЕНИЯ БОЕМ",
                description=f"**🔊 Канал:** {channel.name}\n"
                           f"**👑 Создал:** {inter.user.mention}\n"
                           f"**⚙️ Режим:** {mode_names.get(self.selected_mode, 'Стандартный')}\n"
                           f"**📊 Статус:** ⏳ Ожидание боя\n\n"
                           f"**🎤 Говорят:** {mode_descriptions.get(self.selected_mode, '')}",
                color=Color.blue()
            )
            embed.add_field(
                name="⚡ Управление",
                value="🔇 **НАЧАТЬ БОЙ** — замутить всех кроме указанных\n"
                      "⚙️ **РЕЖИМ** — изменить кто говорит\n"
                      "🗑️ **ЗАКРЫТЬ** — удалить панель",
                inline=False
            )
            embed.add_field(
                name="🕒 Автоудаление",
                value="• Канал пуст 30 мин\n• Старше 24 часов\n• Бой завершён час назад",
                inline=False
            )
            embed.set_footer(text=f"Создано: {datetime.now().strftime('%H:%M')} | 👑 Глава | ⭐ Зам | ⚔️ РЛ")
            
            # ===== BATLLEVIEW =====
            class BattleView(View):
                def __init__(self):
                    super().__init__(timeout=None)
                
                @discord.ui.button(label="НАЧАТЬ БОЙ", style=ButtonStyle.danger, emoji="⚔️", row=0)
                async def start_btn(self, inter2: discord.Interaction, button: Button):
                    if inter2.response.is_done():
                        return
                    
                    if not (utils.is_guild_master(inter2.user, db) or 
                            utils.is_vice_master(inter2.user, db) or 
                            utils.is_raid_leader(inter2.user, db) or
                            str(inter2.user.id) == db.get_setting('developer_id', '')):
                        await inter2.response.send_message("❌ Только командование!", ephemeral=True)
                        return
                    
                    try:
                        ch = interaction.guild.get_channel(battle_config['channel_id'])
                        if not ch:
                            await inter2.response.send_message("❌ Канал не найден!", ephemeral=True)
                            return
                        
                        unmuted_ids = get_unmuted_ids(ch, battle_config, interaction.guild_id, inter2.user.id)
                        
                        muted_count = 0
                        for m in ch.members:
                            if m.bot: continue
                            try:
                                if m.id in unmuted_ids:
                                    if m.voice and m.voice.mute:
                                        await m.edit(mute=False)
                                else:
                                    if m.voice and not m.voice.mute:
                                        await m.edit(mute=True)
                                        muted_count += 1
                            except: pass
                        
                        active_battles[interaction.guild_id] = {
                            'channel': ch,
                            'unmuted': unmuted_ids,
                            'config': battle_config
                        }
                        
                        unmuted_names = []
                        for uid in unmuted_ids:
                            member = interaction.guild.get_member(uid)
                            if member:
                                role_tag = ""
                                if utils.is_guild_master(member, db): role_tag = "👑 "
                                elif utils.is_vice_master(member, db): role_tag = "⭐ "
                                elif utils.is_raid_leader(member, db): role_tag = "⚔️ "
                                unmuted_names.append(f"{role_tag}{member.mention}")
                        
                        muted_names = [m.mention for m in ch.members if not m.bot and m.id not in unmuted_ids]
                        
                        emb = Embed(
                            title="⚔️ БОЙ ИДЁТ!",
                            description=f"**🔊 Канал:** {ch.name}\n"
                                       f"**⚙️ Режим:** {mode_names.get(battle_config['mode'], 'Стандартный')}\n"
                                       f"**🔇 Замучено:** {muted_count} чел.",
                            color=Color.red()
                        )
                        emb.add_field(name=f"🎤 Говорят ({len(unmuted_names)})", value="\n".join(unmuted_names[:15]) or "Никто", inline=True)
                        if muted_names:
                            emb.add_field(name=f"🔇 Замучены ({len(muted_names)})", value="\n".join(muted_names[:10]) + (f"\n...и ещё {len(muted_names)-10}" if len(muted_names) > 10 else ""), inline=True)
                        emb.set_footer(text="🔊 ЗАВЕРШИТЬ | 🔄 ОБНОВИТЬ | ⚙️ РЕЖИМ | 🗑️ УДАЛИТЬ")
                        
                        panel_msg_id = inter2.message.id
                        
                        # ===== ENDVIEW =====
                        class EndView(View):
                            def __init__(self):
                                super().__init__(timeout=None)
                            
                            @discord.ui.button(label="🔊 ЗАВЕРШИТЬ", style=ButtonStyle.success, emoji="✅", row=0)
                            async def end_btn(self, inter3: discord.Interaction, button2: Button):
                                if inter3.response.is_done():
                                    return
                                
                                if not (utils.is_guild_master(inter3.user, db) or 
                                        utils.is_vice_master(inter3.user, db) or 
                                        utils.is_raid_leader(inter3.user, db) or
                                        str(inter3.user.id) == db.get_setting('developer_id', '')):
                                    await inter3.response.send_message("❌ Только командование!", ephemeral=True)
                                    return
                                
                                try:
                                    ch2 = interaction.guild.get_channel(battle_config['channel_id'])
                                    if not ch2:
                                        await inter3.response.send_message("❌ Канал не найден!", ephemeral=True)
                                        return
                                    
                                    unmuted2 = 0
                                    for m in ch2.members:
                                        if m.bot: continue
                                        try:
                                            if m.voice and m.voice.mute:
                                                await m.edit(mute=False)
                                                unmuted2 += 1
                                        except: pass
                                    
                                    if panel_msg_id in active_panels:
                                        active_panels[panel_msg_id]['battle_ended_at'] = datetime.now()
                                    
                                    if interaction.guild_id in active_battles:
                                        del active_battles[interaction.guild_id]
                                    
                                    emb2 = Embed(
                                        title="✅ БОЙ ЗАВЕРШЁН!",
                                        description=f"**🔊 Канал:** {ch2.name}\n"
                                                   f"**🔊 Размучено:** {unmuted2} чел.\n\n"
                                                   f"🕒 Панель удалится через час",
                                        color=Color.green()
                                    )
                                    emb2.add_field(name="⚡ Готово", value="🔇 НАЧАТЬ БОЙ для следующей попытки", inline=False)
                                    
                                    if not inter3.response.is_done():
                                        await inter3.response.edit_message(embed=emb2, view=BattleView())
                                except Exception as e:
                                    print(f"Ошибка завершения боя: {e}")
                            
                            @discord.ui.button(label="ОБНОВИТЬ", style=ButtonStyle.secondary, emoji="🔄", row=1)
                            async def refresh_btn(self, inter4: discord.Interaction, button3: Button):
                                if inter4.response.is_done():
                                    return
                                try:
                                    if interaction.guild_id not in active_battles:
                                        await inter4.response.send_message("❌ Нет боя!", ephemeral=True)
                                        return
                                    
                                    battle = active_battles[interaction.guild_id]
                                    ch3 = interaction.guild.get_channel(battle_config['channel_id'])
                                    if not ch3:
                                        return
                                    
                                    unmuted_list = []
                                    for m in ch3.members:
                                        if m.bot or m.id not in battle['unmuted']:
                                            continue
                                        role_tag = ""
                                        if utils.is_guild_master(m, db): role_tag = "👑 "
                                        elif utils.is_vice_master(m, db): role_tag = "⭐ "
                                        elif utils.is_raid_leader(m, db): role_tag = "⚔️ "
                                        unmuted_list.append(f"{role_tag}{m.mention}")
                                    
                                    muted_list = [m.mention for m in ch3.members if not m.bot and m.id not in battle['unmuted']]
                                    
                                    emb3 = Embed(title="⚔️ БОЙ ИДЁТ!", color=Color.red())
                                    emb3.add_field(name=f"🎤 Говорят ({len(unmuted_list)})", value="\n".join(unmuted_list[:10]) or "Никто", inline=True)
                                    emb3.add_field(name=f"🔇 Замучены ({len(muted_list)})", value="\n".join(muted_list[:10]) + (f"\n...и ещё {len(muted_list)-10}" if len(muted_list) > 10 else ""), inline=True)
                                    
                                    if not inter4.response.is_done():
                                        await inter4.response.edit_message(embed=emb3, view=self)
                                except:
                                    pass
                            
                            @discord.ui.button(label="⚙️ РЕЖИМ", style=ButtonStyle.primary, emoji="⚙️", row=1)
                            async def change_mode_btn(self, inter5: discord.Interaction, button4: Button):
                                if inter5.response.is_done():
                                    return
                                
                                if not (utils.is_guild_master(inter5.user, db) or 
                                        utils.is_vice_master(inter5.user, db) or 
                                        utils.is_raid_leader(inter5.user, db) or
                                        str(inter5.user.id) == db.get_setting('developer_id', '')):
                                    await inter5.response.send_message("❌ Только командование!", ephemeral=True)
                                    return
                                
                                mode_embed = Embed(title="⚙️ Смена режима", description="Выберите новый режим:", color=Color.blue())
                                
                                class ModeChangeView(View):
                                    def __init__(self):
                                        super().__init__(timeout=30)
                                        for mode_opt in battle_modes:
                                            btn = Button(label=mode_opt.label, emoji=mode_opt.emoji, style=ButtonStyle.secondary)
                                            btn.callback = self.make_callback(mode_opt.value)
                                            self.add_item(btn)
                                    
                                    def make_callback(self, mode_value):
                                        async def callback(inter6: discord.Interaction):
                                            if mode_value == "custom":
                                                ch_temp = interaction.guild.get_channel(battle_config['channel_id'])
                                                if not ch_temp:
                                                    await inter6.response.edit_message(content="❌ Канал не найден!", embed=None, view=None)
                                                    return
                                                
                                                members_temp = [m for m in ch_temp.members if not m.bot]
                                                
                                                if not members_temp:
                                                    await inter6.response.edit_message(content="❌ В канале нет участников для выбора!", embed=None, view=None)
                                                    return
                                                
                                                member_opts = []
                                                for m in members_temp[:25]:
                                                    role_tag = ""
                                                    if utils.is_guild_master(m, db): role_tag = "👑 "
                                                    elif utils.is_vice_master(m, db): role_tag = "⭐ "
                                                    elif utils.is_raid_leader(m, db): role_tag = "⚔️ "
                                                    member_opts.append(discord.SelectOption(
                                                        label=f"{role_tag}{m.display_name}", 
                                                        value=str(m.id), 
                                                        emoji="🎤"
                                                    ))
                                                
                                                if not member_opts:
                                                    await inter6.response.edit_message(content="❌ Нет доступных участников!", embed=None, view=None)
                                                    return
                                                
                                                class QuickSelect(View):
                                                    def __init__(self):
                                                        super().__init__(timeout=30)
                                                        max_vals = min(len(member_opts), 25)
                                                        sel = Select(
                                                            placeholder="Кто будет говорить?", 
                                                            options=member_opts, 
                                                            max_values=max_vals, 
                                                            min_values=1
                                                        )
                                                        sel.callback = self.sel_callback
                                                        self.add_item(sel)
                                                    
                                                    async def sel_callback(self, inter7: discord.Interaction):
                                                        battle_config['mode'] = mode_value
                                                        battle_config['custom_members'] = [int(v) for v in inter7.data['values']]
                                                        
                                                        if interaction.guild_id in active_battles:
                                                            ch_temp2 = interaction.guild.get_channel(battle_config['channel_id'])
                                                            if ch_temp2:
                                                                unmuted_ids_new = get_unmuted_ids(ch_temp2, battle_config, interaction.guild_id, inter7.user.id)
                                                                for m in ch_temp2.members:
                                                                    if m.bot: continue
                                                                    try:
                                                                        if m.id in unmuted_ids_new:
                                                                            if m.voice and m.voice.mute:
                                                                                await m.edit(mute=False)
                                                                        else:
                                                                            if m.voice and not m.voice.mute:
                                                                                await m.edit(mute=True)
                                                                    except: pass
                                                                active_battles[interaction.guild_id]['unmuted'] = unmuted_ids_new
                                                                active_battles[interaction.guild_id]['config'] = battle_config
                                                                
                                                                unmuted_list_new = []
                                                                for m in ch_temp2.members:
                                                                    if m.bot or m.id not in unmuted_ids_new:
                                                                        continue
                                                                    role_tag = ""
                                                                    if utils.is_guild_master(m, db): role_tag = "👑 "
                                                                    elif utils.is_vice_master(m, db): role_tag = "⭐ "
                                                                    elif utils.is_raid_leader(m, db): role_tag = "⚔️ "
                                                                    unmuted_list_new.append(f"{role_tag}{m.mention}")
                                                                
                                                                muted_list_new = [m.mention for m in ch_temp2.members if not m.bot and m.id not in unmuted_ids_new]
                                                                
                                                                emb_new = Embed(
                                                                    title="⚔️ БОЙ ИДЁТ!",
                                                                    description=f"**🔊 Канал:** {ch_temp2.name}\n"
                                                                               f"**⚙️ Режим:** 🎯 Выборочный\n"
                                                                               f"**🔇 Замучено:** {len(muted_list_new)} чел.",
                                                                    color=Color.red()
                                                                )
                                                                emb_new.add_field(name=f"🎤 Говорят ({len(unmuted_list_new)})", value="\n".join(unmuted_list_new[:10]) or "Никто", inline=True)
                                                                if muted_list_new:
                                                                    emb_new.add_field(name=f"🔇 Замучены ({len(muted_list_new)})", value="\n".join(muted_list_new[:10]) + (f"\n...и ещё {len(muted_list_new)-10}" if len(muted_list_new) > 10 else ""), inline=True)
                                                                
                                                                await inter5.message.edit(embed=emb_new, view=EndView())
                                                        
                                                        await inter7.response.edit_message(content="✅ Режим изменён!", embed=None, view=None)
                                                
                                                await inter6.response.edit_message(content="Выберите участников:", embed=None, view=QuickSelect())
                                            else:
                                                battle_config['mode'] = mode_value
                                                
                                                if interaction.guild_id in active_battles:
                                                    ch_temp2 = interaction.guild.get_channel(battle_config['channel_id'])
                                                    if ch_temp2:
                                                        unmuted_ids_new = get_unmuted_ids(ch_temp2, battle_config, interaction.guild_id, inter6.user.id)
                                                        for m in ch_temp2.members:
                                                            if m.bot: continue
                                                            try:
                                                                if m.id in unmuted_ids_new:
                                                                    if m.voice and m.voice.mute:
                                                                        await m.edit(mute=False)
                                                                else:
                                                                    if m.voice and not m.voice.mute:
                                                                        await m.edit(mute=True)
                                                            except: pass
                                                        active_battles[interaction.guild_id]['unmuted'] = unmuted_ids_new
                                                        active_battles[interaction.guild_id]['config'] = battle_config
                                                        
                                                        unmuted_list_new = []
                                                        for m in ch_temp2.members:
                                                            if m.bot or m.id not in unmuted_ids_new:
                                                                continue
                                                            role_tag = ""
                                                            if utils.is_guild_master(m, db): role_tag = "👑 "
                                                            elif utils.is_vice_master(m, db): role_tag = "⭐ "
                                                            elif utils.is_raid_leader(m, db): role_tag = "⚔️ "
                                                            unmuted_list_new.append(f"{role_tag}{m.mention}")
                                                        
                                                        muted_list_new = [m.mention for m in ch_temp2.members if not m.bot and m.id not in unmuted_ids_new]
                                                        
                                                        emb_new = Embed(
                                                            title="⚔️ БОЙ ИДЁТ!",
                                                            description=f"**🔊 Канал:** {ch_temp2.name}\n"
                                                                       f"**⚙️ Режим:** {mode_names.get(mode_value, mode_value)}\n"
                                                                       f"**🔇 Замучено:** {len(muted_list_new)} чел.",
                                                            color=Color.red()
                                                        )
                                                        emb_new.add_field(name=f"🎤 Говорят ({len(unmuted_list_new)})", value="\n".join(unmuted_list_new[:10]) or "Никто", inline=True)
                                                        if muted_list_new:
                                                            emb_new.add_field(name=f"🔇 Замучены ({len(muted_list_new)})", value="\n".join(muted_list_new[:10]) + (f"\n...и ещё {len(muted_list_new)-10}" if len(muted_list_new) > 10 else ""), inline=True)
                                                        
                                                        await inter5.message.edit(embed=emb_new, view=EndView())
                                                
                                                await inter6.response.edit_message(content="✅ Режим изменён!", embed=None, view=None)
                                        return callback
                                
                                await inter5.response.send_message(embed=mode_embed, view=ModeChangeView(), ephemeral=True)
                            
                            @discord.ui.button(label="🗑️ УДАЛИТЬ", style=ButtonStyle.danger, emoji="🗑️", row=2)
                            async def delete_btn(self, inter8: discord.Interaction, button5: Button):
                                if inter8.response.is_done():
                                    return
                                
                                if not (utils.is_guild_master(inter8.user, db) or 
                                        utils.is_vice_master(inter8.user, db) or 
                                        utils.is_raid_leader(inter8.user, db) or
                                        str(inter8.user.id) == db.get_setting('developer_id', '')):
                                    await inter8.response.send_message("❌ Только командование!", ephemeral=True)
                                    return
                                
                                try:
                                    ch4 = interaction.guild.get_channel(battle_config['channel_id'])
                                    if ch4:
                                        for m in ch4.members:
                                            if m.bot: continue
                                            try:
                                                if m.voice and m.voice.mute:
                                                    await m.edit(mute=False)
                                            except: pass
                                    
                                    if interaction.guild_id in active_battles:
                                        del active_battles[interaction.guild_id]
                                    
                                    if panel_msg_id in active_panels:
                                        del active_panels[panel_msg_id]
                                    
                                    await inter8.message.delete()
                                except Exception as e:
                                    print(f"Ошибка удаления: {e}")
                        
                        if not inter2.response.is_done():
                            await inter2.response.edit_message(embed=emb, view=EndView())
                    except Exception as e:
                        print(f"Ошибка начала боя: {e}")
                
                @discord.ui.button(label="РЕЖИМ", style=ButtonStyle.primary, emoji="⚙️", row=1)
                async def change_mode_panel_btn(self, inter9: discord.Interaction, button6: Button):
                    if inter9.response.is_done():
                        return
                    
                    if not (utils.is_guild_master(inter9.user, db) or 
                            utils.is_vice_master(inter9.user, db) or 
                            utils.is_raid_leader(inter9.user, db) or
                            str(inter9.user.id) == db.get_setting('developer_id', '')):
                        await inter9.response.send_message("❌ Только командование!", ephemeral=True)
                        return
                    
                    mode_embed = Embed(title="⚙️ Выбор режима", description="Выберите режим боя:", color=Color.blue())
                    
                    class ModeSelectForPanel(View):
                        def __init__(self):
                            super().__init__(timeout=30)
                            for mode_opt in battle_modes:
                                btn = Button(label=mode_opt.label, emoji=mode_opt.emoji, style=ButtonStyle.secondary)
                                btn.callback = self.make_callback(mode_opt.value)
                                self.add_item(btn)
                        
                        def make_callback(self, mode_value):
                            async def callback(inter10: discord.Interaction):
                                if mode_value == "custom":
                                    ch_temp = interaction.guild.get_channel(battle_config['channel_id'])
                                    if not ch_temp:
                                        await inter10.response.edit_message(content="❌ Канал не найден!", embed=None, view=None)
                                        return
                                    
                                    members_temp = [m for m in ch_temp.members if not m.bot]
                                    
                                    if not members_temp:
                                        await inter10.response.edit_message(content="❌ В канале нет участников для выбора!", embed=None, view=None)
                                        return
                                    
                                    member_opts = []
                                    for m in members_temp[:25]:
                                        role_tag = ""
                                        if utils.is_guild_master(m, db): role_tag = "👑 "
                                        elif utils.is_vice_master(m, db): role_tag = "⭐ "
                                        elif utils.is_raid_leader(m, db): role_tag = "⚔️ "
                                        member_opts.append(discord.SelectOption(
                                            label=f"{role_tag}{m.display_name}", 
                                            value=str(m.id), 
                                            emoji="🎤"
                                        ))
                                    
                                    if not member_opts:
                                        await inter10.response.edit_message(content="❌ Нет доступных участников!", embed=None, view=None)
                                        return
                                    
                                    class QuickSelect2(View):
                                        def __init__(self):
                                            super().__init__(timeout=30)
                                            max_vals = min(len(member_opts), 25)
                                            sel = Select(
                                                placeholder="Кто будет говорить?", 
                                                options=member_opts, 
                                                max_values=max_vals, 
                                                min_values=1
                                            )
                                            sel.callback = self.sel_callback
                                            self.add_item(sel)
                                        
                                        async def sel_callback(self, inter11: discord.Interaction):
                                            battle_config['mode'] = mode_value
                                            battle_config['custom_members'] = [int(v) for v in inter11.data['values']]
                                            
                                            embed_upd = Embed(
                                                title="⚔️ ПАНЕЛЬ УПРАВЛЕНИЯ БОЕМ",
                                                description=f"**🔊 Канал:** {channel.name}\n"
                                                           f"**👑 Создал:** {interaction.user.mention}\n"
                                                           f"**⚙️ Режим:** 🎯 Выборочный\n"
                                                           f"**📊 Статус:** ⏳ Ожидание\n\n"
                                                           f"**🎤 Говорят:** Выбрано {len(battle_config['custom_members'])} чел.",
                                                color=Color.blue()
                                            )
                                            embed_upd.add_field(
                                                name="⚡ Управление", 
                                                value="🔇 НАЧАТЬ БОЙ | ⚙️ РЕЖИМ | 🗑️ ЗАКРЫТЬ", 
                                                inline=False
                                            )
                                            embed_upd.add_field(
                                                name="🕒 Автоудаление",
                                                value="• Канал пуст 30 мин\n• Старше 24 часов\n• Бой завершён час назад",
                                                inline=False
                                            )
                                            
                                            await inter9.message.edit(embed=embed_upd, view=BattleView())
                                            await inter11.response.edit_message(content="✅ Режим изменён!", embed=None, view=None)
                                    
                                    await inter10.response.edit_message(content="Выберите участников:", embed=None, view=QuickSelect2())
                                else:
                                    battle_config['mode'] = mode_value
                                    
                                    embed_upd = Embed(
                                        title="⚔️ ПАНЕЛЬ УПРАВЛЕНИЯ БОЕМ",
                                        description=f"**🔊 Канал:** {channel.name}\n"
                                                   f"**👑 Создал:** {interaction.user.mention}\n"
                                                   f"**⚙️ Режим:** {mode_names.get(mode_value, mode_value)}\n"
                                                   f"**📊 Статус:** ⏳ Ожидание\n\n"
                                                   f"**🎤 Говорят:** {mode_descriptions.get(mode_value, '')}",
                                        color=Color.blue()
                                    )
                                    embed_upd.add_field(
                                        name="⚡ Управление", 
                                        value="🔇 НАЧАТЬ БОЙ | ⚙️ РЕЖИМ | 🗑️ ЗАКРЫТЬ", 
                                        inline=False
                                    )
                                    embed_upd.add_field(
                                        name="🕒 Автоудаление",
                                        value="• Канал пуст 30 мин\n• Старше 24 часов\n• Бой завершён час назад",
                                        inline=False
                                    )
                                    
                                    await inter9.message.edit(embed=embed_upd, view=BattleView())
                                    await inter10.response.edit_message(content="✅ Режим изменён!", embed=None, view=None)
                            return callback
                    
                    await inter9.response.send_message(embed=mode_embed, view=ModeSelectForPanel(), ephemeral=True)
                
                @discord.ui.button(label="ЗАКРЫТЬ", style=ButtonStyle.danger, emoji="🗑️", row=2)
                async def delete_panel_btn(self, inter12: discord.Interaction, button7: Button):
                    if inter12.response.is_done():
                        return
                    
                    if not (utils.is_guild_master(inter12.user, db) or 
                            utils.is_vice_master(inter12.user, db) or 
                            utils.is_raid_leader(inter12.user, db) or
                            str(inter12.user.id) == db.get_setting('developer_id', '')):
                        await inter12.response.send_message("❌ Только командование!", ephemeral=True)
                        return
                    
                    try:
                        if interaction.guild_id in active_battles:
                            ch5 = interaction.guild.get_channel(battle_config['channel_id'])
                            if ch5:
                                for m in ch5.members:
                                    if m.bot: continue
                                    try:
                                        if m.voice and m.voice.mute:
                                            await m.edit(mute=False)
                                    except: pass
                            del active_battles[interaction.guild_id]
                        
                        msg_id = inter12.message.id
                        if msg_id in active_panels:
                            del active_panels[msg_id]
                        
                        await inter12.message.delete()
                    except Exception as e:
                        print(f"Ошибка удаления: {e}")
            
            # Отправляем панель
            panel_msg = await interaction.channel.send(embed=embed, view=BattleView())
            
            # Сохраняем информацию
            active_panels[panel_msg.id] = {
                'channel_id': interaction.channel.id,
                'guild_id': interaction.guild.id,
                'voice_channel_id': self.selected_channel,
                'created_at': datetime.now(),
                'creator_id': inter.user.id,
                'empty_since': None,
                'battle_ended_at': None
            }
            
            await inter.response.edit_message(content=f"✅ Панель для **{channel.name}** создана!", view=None)
    
    await interaction.followup.send("🔊 Выберите канал и режим:", view=ChannelAndModeSelect(), ephemeral=True)


def get_unmuted_ids(channel, battle_config, guild_id, user_id=None):
    """Получить список кого не мутить"""
    unmuted = []
    guild = channel.guild
    db = bot.get_db(guild_id)
    if not db:
        return unmuted
    
    guild_master_role_id = utils.safe_int(db.get_setting('guild_master', ''))
    vice_master_role_id = utils.safe_int(db.get_setting('vice_master', ''))
    raid_leader_role_id = utils.safe_int(db.get_setting('raid_leader', ''))
    senior_officer_role_id = utils.safe_int(db.get_setting('senior_officer_role', ''))
    officer_role_id = utils.safe_int(db.get_setting('officer_role', ''))
    
    mode = battle_config.get('mode', 'standard') if battle_config else 'standard'
    
    if mode == "custom" and battle_config:
        custom_members = battle_config.get('custom_members', [])
        for member in channel.members:
            if member.bot:
                continue
            if member.id in custom_members:
                unmuted.append(member.id)
    else:
        for member in channel.members:
            if member.bot:
                continue
            
            if guild_master_role_id:
                role = guild.get_role(guild_master_role_id)
                if role and role in member.roles:
                    unmuted.append(member.id)
                    continue
            
            if vice_master_role_id:
                role = guild.get_role(vice_master_role_id)
                if role and role in member.roles:
                    unmuted.append(member.id)
                    continue
            
            if raid_leader_role_id:
                role = guild.get_role(raid_leader_role_id)
                if role and role in member.roles:
                    unmuted.append(member.id)
                    continue
            
            if mode in ["standard", "free"]:
                if senior_officer_role_id:
                    role = guild.get_role(senior_officer_role_id)
                    if role and role in member.roles:
                        unmuted.append(member.id)
                        continue
                if officer_role_id:
                    role = guild.get_role(officer_role_id)
                    if role and role in member.roles:
                        unmuted.append(member.id)
                        continue
    
    if user_id and user_id not in unmuted:
        unmuted.append(user_id)
    
    always_roles_str = db.get_setting('pull_always_roles', '')
    always_users_str = db.get_setting('pull_always_users', '')
    
    if always_roles_str:
        role_ids = [int(r.strip()) for r in always_roles_str.split(',') if r.strip().isdigit()]
        for member in channel.members:
            if member.bot or member.id in unmuted:
                continue
            for role_id in role_ids:
                role = guild.get_role(role_id)
                if role and role in member.roles:
                    unmuted.append(member.id)
                    break
    
    if always_users_str:
        user_ids = [int(u.strip()) for u in always_users_str.split(',') if u.strip().isdigit()]
        for uid in user_ids:
            if uid not in unmuted:
                unmuted.append(uid)
    
    return unmuted


@bot.tree.command(name="pull_setup", description="⚙️ Настроить дополнительные роли/пользователей")
async def pull_setup(interaction: discord.Interaction):
    db = bot.get_db(interaction.guild_id)
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    
    class SetupModal(Modal, title="👑 Дополнительные роли/пользователи"):
        roles_input = TextInput(
            label="ID доп. ролей (через запятую)",
            placeholder="123, 456",
            default=db.get_setting('pull_always_roles', ''),
            required=False,
            max_length=200
        )
        users_input = TextInput(
            label="ID доп. пользователей (через запятую)",
            placeholder="111, 222",
            default=db.get_setting('pull_always_users', ''),
            required=False,
            max_length=200
        )
        
        async def on_submit(self, inter: discord.Interaction):
            db2 = bot.get_db(inter.guild_id)
            db2.set_setting('pull_always_roles', self.roles_input.value.strip())
            db2.set_setting('pull_always_users', self.users_input.value.strip())
            await inter.response.send_message("✅ Сохранено!", ephemeral=True)
    
    await interaction.response.send_modal(SetupModal())


@bot.tree.command(name="pull_status", description="📊 Показать статус боя")
async def pull_status(interaction: discord.Interaction):
    if interaction.guild_id not in active_battles:
        await interaction.response.send_message("❌ Нет активного боя!", ephemeral=True)
        return
    
    battle = active_battles[interaction.guild_id]
    ch = battle['channel']
    db = bot.get_db(interaction.guild_id)
    
    unmuted_list = []
    for m in ch.members:
        if m.bot or m.id not in battle['unmuted']:
            continue
        role_tag = ""
        if db:
            if utils.is_guild_master(m, db): role_tag = "👑 "
            elif utils.is_vice_master(m, db): role_tag = "⭐ "
            elif utils.is_raid_leader(m, db): role_tag = "⚔️ "
        unmuted_list.append(f"🎤 {role_tag}{m.display_name}")
    
    muted_list = [f"🔇 {m.display_name}" for m in ch.members if not m.bot and m.id not in battle['unmuted']]
    
    embed = Embed(title="⚔️ Статус боя", description=f"**Канал:** {ch.name}", color=Color.orange())
    embed.add_field(name=f"🎤 Говорят ({len(unmuted_list)})", value="\n".join(unmuted_list) or "Никто", inline=True)
    embed.add_field(name=f"🔇 Замучены ({len(muted_list)})", value="\n".join(muted_list[:15]) or "Никто", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="pull_check", description="🔄 Проверить и исправить муты")
async def pull_check(interaction: discord.Interaction):
    if interaction.guild_id not in active_battles:
        await interaction.response.send_message("❌ Нет активного боя!", ephemeral=True)
        return
    
    db = bot.get_db(interaction.guild_id)
    if not (utils.is_guild_master(interaction.user, db) or 
            utils.is_vice_master(interaction.user, db) or 
            utils.is_raid_leader(interaction.user, db)):
        await interaction.response.send_message("❌ Только командование!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    battle = active_battles[interaction.guild_id]
    channel = battle.get('channel')
    battle_config = battle.get('config', {})
    
    if not channel:
        del active_battles[interaction.guild_id]
        await interaction.followup.send("❌ Канал не найден!", ephemeral=True)
        return
    
    unmuted_ids = get_unmuted_ids(channel, battle_config, interaction.guild_id)
    battle['unmuted'] = unmuted_ids
    
    fixed_muted = 0
    fixed_unmuted = 0
    
    for member in channel.members:
        if member.bot:
            continue
        try:
            should_be_unmuted = member.id in unmuted_ids
            is_muted = member.voice.mute if member.voice else False
            
            if should_be_unmuted and is_muted:
                await member.edit(mute=False)
                fixed_unmuted += 1
            elif not should_be_unmuted and not is_muted:
                await member.edit(mute=True)
                fixed_muted += 1
        except:
            pass
    
    embed = Embed(title="🔄 Проверка мутов", description=f"**Канал:** {channel.name}", color=Color.green())
    embed.add_field(name="✅ Исправлено", value=f"🔇 Замучено: {fixed_muted}\n🔊 Размучено: {fixed_unmuted}")
    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="pull_panels", description="📋 Показать активные панели")
async def pull_panels(interaction: discord.Interaction):
    db = bot.get_db(interaction.guild_id)
    if not (utils.is_guild_master(interaction.user, db) or 
            utils.is_vice_master(interaction.user, db) or 
            utils.is_raid_leader(interaction.user, db)):
        await interaction.response.send_message("❌ Только командование!", ephemeral=True)
        return
    
    guild_panels = {msg_id: info for msg_id, info in active_panels.items() 
                   if info['guild_id'] == interaction.guild.id}
    
    if not guild_panels:
        await interaction.response.send_message("📋 Нет активных панелей", ephemeral=True)
        return
    
    embed = Embed(title="📋 Активные панели", description=f"Всего: {len(guild_panels)}", color=Color.blue())
    
    for msg_id, info in guild_panels.items():
        voice_channel = interaction.guild.get_channel(info['voice_channel_id'])
        channel_name = voice_channel.name if voice_channel else "Удалён"
        created_at = info['created_at'].strftime("%H:%M %d.%m")
        status = "⚔️ Бой" if interaction.guild.id in active_battles else "⏳ Ожидание"
        
        embed.add_field(
            name=f"ID: {msg_id}",
            value=f"Канал: {channel_name}\nСтатус: {status}\nСоздана: {created_at}",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="pull_cleanup", description="🧹 Удалить все неактивные панели (Глава)")
async def pull_cleanup(interaction: discord.Interaction):
    db = bot.get_db(interaction.guild_id)
    if not utils.is_guild_master(interaction.user, db):
        await interaction.response.send_message("❌ Только Глава гильдии!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    deleted = 0
    for msg_id, panel_info in list(active_panels.items()):
        if panel_info['guild_id'] != interaction.guild.id:
            continue
        try:
            channel = interaction.guild.get_channel(panel_info['channel_id'])
            if channel:
                try:
                    message = await channel.fetch_message(msg_id)
                    await message.delete()
                except:
                    pass
            deleted += 1
        except:
            pass
        
        if msg_id in active_panels:
            del active_panels[msg_id]
    
    await interaction.followup.send(f"🧹 Удалено панелей: {deleted}", ephemeral=True)


# ========== АВТОМАТИЧЕСКИЙ МУТ НОВЫХ УЧАСТНИКОВ ==========

@bot.event
async def on_voice_state_update(member, before, after):
    if member.guild.id not in active_battles:
        return
    
    battle = active_battles[member.guild.id]
    channel = battle.get('channel')
    battle_config = battle.get('config', {})
    
    if not channel:
        del active_battles[member.guild.id]
        return
    
    if member == member.guild.me and after.channel is None:
        for m in channel.members:
            if m.bot:
                continue
            try:
                if m.voice and m.voice.mute:
                    await m.edit(mute=False)
            except:
                pass
        
        if member.guild.id in active_battles:
            del active_battles[member.guild.id]
        return
    
    if after.channel and after.channel.id == channel.id:
        if member.bot:
            return
        
        unmuted_ids = get_unmuted_ids(channel, battle_config, member.guild.id)
        battle['unmuted'] = unmuted_ids
        
        if member.id not in unmuted_ids:
            try:
                await member.edit(mute=True, reason=f"Бой идёт | Режим: {battle_config.get('mode', 'standard')}")
            except:
                pass
        else:
            try:
                if member.voice and member.voice.mute:
                    await member.edit(mute=False)
            except:
                pass
    
    if before.channel and before.channel.id == channel.id:
        if after.channel is None or after.channel.id != channel.id:
            try:
                if member.voice and member.voice.mute:
                    await member.edit(mute=False)
            except:
                pass


# ========== АВТООЧИСТКА ПАНЕЛЕЙ ==========

@tasks.loop(minutes=5)
async def cleanup_inactive_panels():
    current_time = datetime.now()
    
    for message_id, panel_info in list(active_panels.items()):
        try:
            guild = bot.get_guild(panel_info['guild_id'])
            if not guild:
                del active_panels[message_id]
                continue
            
            channel = guild.get_channel(panel_info['channel_id'])
            if not channel:
                del active_panels[message_id]
                continue
            
            voice_channel = guild.get_channel(panel_info['voice_channel_id'])
            should_delete = False
            
            if not voice_channel:
                should_delete = True
            elif voice_channel and len(voice_channel.members) == 0:
                if panel_info.get('empty_since'):
                    empty_time = current_time - panel_info['empty_since']
                    if empty_time.total_seconds() > 1800:
                        should_delete = True
                else:
                    panel_info['empty_since'] = current_time
            else:
                panel_info['empty_since'] = None
            
            if not should_delete and panel_info.get('created_at'):
                panel_age = current_time - panel_info['created_at']
                if panel_age.total_seconds() > 86400:
                    should_delete = True
            
            if not should_delete and panel_info['guild_id'] not in active_battles:
                if panel_info.get('battle_ended_at'):
                    ended_time = current_time - panel_info['battle_ended_at']
                    if ended_time.total_seconds() > 3600:
                        should_delete = True
            
            if should_delete:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.delete()
                except discord.NotFound:
                    pass
                except Exception as e:
                    print(f"Ошибка удаления панели {message_id}: {e}")
                finally:
                    if message_id in active_panels:
                        del active_panels[message_id]
                        
        except Exception as e:
            print(f"Ошибка очистки панели {message_id}: {e}")


@cleanup_inactive_panels.before_loop
async def before_cleanup():
    await bot.wait_until_ready()


# ========== ОБРАБОТЧИК УДАЛЕНИЯ КАНАЛА ==========

@bot.event
async def on_guild_channel_delete(channel):
    if isinstance(channel, discord.VoiceChannel):
        panels_to_delete = []
        for msg_id, panel_info in active_panels.items():
            if panel_info['voice_channel_id'] == channel.id:
                panels_to_delete.append(msg_id)
        
        for msg_id in panels_to_delete:
            try:
                text_channel = channel.guild.get_channel(active_panels[msg_id]['channel_id'])
                if text_channel:
                    message = await text_channel.fetch_message(msg_id)
                    await message.delete()
            except:
                pass
            
            if msg_id in active_panels:
                del active_panels[msg_id]
        
        if channel.guild.id in active_battles:
            battle = active_battles[channel.guild.id]
            if battle.get('channel') and battle['channel'].id == channel.id:
                del active_battles[channel.guild.id]


# ========== ОБРАБОТЧИК СООБЩЕНИЙ (ЖАЛОБЫ) ==========

@bot.event
async def on_message(message: discord.Message):
    """Обработка команд в каналах жалоб"""
    if message.author.bot:
        return
    
    # Проверяем, что это канал жалобы
    if not message.channel.name.startswith('⚠️-жалоба-'):
        return
    
    db = bot.get_db(message.guild.id)
    if not db:
        return
    
    # Проверяем права
    if not utils.can_manage_reports(message.author, db):
        return
    
    content = message.content.strip()
    
    # !принять причина
    if content.startswith('!принять'):
        reason = content[8:].strip()
        if not reason:
            await message.channel.send("❌ Укажите причину: `!принять причина`")
            return
        
        try:
            report_id = int(message.channel.name.replace('⚠️-жалоба-', ''))
        except:
            return
        
        await resolve_report(message, report_id, 'resolve', reason)
    
    # !отклонить причина
    elif content.startswith('!отклонить'):
        reason = content[10:].strip()
        if not reason:
            await message.channel.send("❌ Укажите причину: `!отклонить причина`")
            return
        
        try:
            report_id = int(message.channel.name.replace('⚠️-жалоба-', ''))
        except:
            return
        
        await resolve_report(message, report_id, 'reject', reason)


async def resolve_report(message: discord.Message, report_id: int, action: str, comment: str):
    """Обработка решения по жалобе"""
    db = bot.get_db(message.guild.id)
    if not db:
        return
    
    new_status = 'resolved' if action == 'resolve' else 'rejected'
    status_text = "✅ ПРИНЯТО" if new_status == 'resolved' else "❌ ОТКЛОНЕНО"
    status_color = Color.green() if new_status == 'resolved' else Color.red()
    status_emoji = "✅" if new_status == 'resolved' else "❌"
    
    db.update_report_status(report_id, new_status, message.author.id, comment)
    db.set_setting(f'report_{report_id}_resolved_at', datetime.now().isoformat())
    db.set_setting(f'report_{report_id}_channel_id', str(message.channel.id))
    
    async for msg in message.channel.history(limit=10):
        if msg.author == message.guild.me and msg.embeds:
            embed = msg.embeds[0]
            embed.color = status_color
            
            for i, field in enumerate(embed.fields):
                if field.name == "📊 СТАТУС":
                    embed.set_field_at(i, name="📊 СТАТУС", value=f"{status_emoji} **{status_text}**", inline=True)
                if field.name == "⏳ Ожидает":
                    embed.set_field_at(i, name="👮 Модератор", value=message.author.mention, inline=True)
            
            embed.add_field(name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", value="", inline=False)
            embed.add_field(
                name=f"{status_emoji} РЕШЕНИЕ",
                value=f"**Модератор:** {message.author.mention}\n"
                      f"**Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                      f"```{comment}```",
                inline=False
            )
            embed.set_footer(text=f"ID: {report_id} | {status_text} | Автоудаление через 1 час")
            await msg.edit(embed=embed)
            break
    
    await message.channel.send(
        f"## {status_emoji} {status_text}\n"
        f"**Модератор:** {message.author.mention}\n"
        f"**Комментарий:** {comment}\n\n"
        f"*⏳ Канал будет удалён через 1 час.*"
    )
    
    await archive_report(message, report_id, status_text, status_color, comment)
    await notify_reporter(message, report_id, new_status, comment, status_emoji, status_color)
    db.add_log(f"{status_emoji} Жалоба", message.author.id, details=f"#{report_id}: {comment[:100]}")


async def archive_report(message, report_id, status_text, status_color, comment):
    """Архивирует жалобу"""
    db = bot.get_db(message.guild.id)
    archive_channel_id = utils.safe_int(db.get_setting('archive_channel', ''))
    if not archive_channel_id:
        return
    
    archive_channel = message.guild.get_channel(archive_channel_id)
    if not archive_channel:
        return
    
    report = db.get_report_by_id(report_id)
    if not report:
        return
    
    archive_embed = Embed(
        title=f"📁 Архив: Жалоба #{report_id}",
        color=status_color,
        timestamp=datetime.now()
    )
    archive_embed.add_field(name="👤 Нарушитель", value=report['violator_name'], inline=True)
    archive_embed.add_field(name="📋 Тип", value=report['violation_type'], inline=True)
    archive_embed.add_field(name="📊 Статус", value=status_text, inline=True)
    archive_embed.add_field(name="👮 Модератор", value=message.author.mention, inline=False)
    archive_embed.add_field(name="📝 Решение", value=comment, inline=False)
    archive_embed.set_footer(text=f"ID: {report_id}")
    
    await archive_channel.send(embed=archive_embed)


async def notify_reporter(message, report_id, new_status, comment, status_emoji, status_color):
    """Уведомляет автора жалобы"""
    db = bot.get_db(message.guild.id)
    report = db.get_report_by_id(report_id)
    if not report:
        return
    
    reporter = message.guild.get_member(report['reporter_id'])
    if not reporter:
        return
    
    status_word = "одобрена" if new_status == 'resolved' else "отклонена"
    try:
        await reporter.send(embed=Embed(
            title=f"{status_emoji} Ваша жалоба #{report_id} {status_word}",
            description=f"**Сервер:** {message.guild.name}\n\n"
                       f"**Результат:**\n```{comment}```\n\n"
                       f"**Модератор:** {message.author.mention}\n"
                       f"**Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                       f"💙 Спасибо за обращение!",
            color=status_color,
            timestamp=datetime.now()
        ))
    except:
        pass


# ============================================
# КОМАНДЫ ДЛЯ ПАНЕЛИ КУРАТОРОВ
# ============================================

@bot.tree.command(name="curator_panel_setup", description="🔧 Создать каналы для кураторов и курсантов")
async def curator_panel_setup(interaction: discord.Interaction):
    """Создает выделенные каналы для кураторов и курсантов"""
    db = bot.get_db(interaction.guild_id)
    
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    
    if str(interaction.user.id) != db.get_setting('developer_id', '') and not utils.is_guild_master(interaction.user, db):
        await interaction.response.send_message("❌ Только разработчик или глава гильдии!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    guild = interaction.guild
    
    # Ищем или создаем категорию
    category = None
    for cat in guild.categories:
        if "куратор" in cat.name.lower() or "обучение" in cat.name.lower():
            category = cat
            break
    
    if not category:
        category = await guild.create_category_channel("👨‍🏫 Обучение")
    
    curator_role_id = db.get_setting('curator_role', '')
    
    # ============================================
    # 1. КАНАЛ ДЛЯ КУРАТОРОВ
    # ============================================
    
    existing_channel_id = db.get_setting('curator_channel', '')
    if existing_channel_id:
        existing_channel = guild.get_channel(int(existing_channel_id))
        if existing_channel:
            await interaction.followup.send(
                f"⚠️ Канал кураторов уже существует: {existing_channel.mention}\n"
                f"Используйте `/curator_panel_refresh` чтобы обновить панель.",
                ephemeral=True
            )
            return
    
    curator_channel = await guild.create_text_channel(
        "👨‍🏫-панель-кураторов",
        category=category,
        topic="Панель управления обучением | Только для кураторов"
    )
    
    everyone = guild.default_role
    await curator_channel.set_permissions(everyone, read_messages=False)
    
    if curator_role_id:
        role = guild.get_role(int(curator_role_id))
        if role:
            await curator_channel.set_permissions(role, read_messages=True, send_messages=True)
    
    gm_role_id = db.get_setting('guild_master', '')
    if gm_role_id:
        role = guild.get_role(int(gm_role_id))
        if role:
            await curator_channel.set_permissions(role, read_messages=True, send_messages=True)
    
    dev_id = db.get_setting('developer_id', '')
    if dev_id:
        dev = guild.get_member(int(dev_id))
        if dev:
            await curator_channel.set_permissions(dev, read_messages=True, send_messages=True)
    
    db.set_setting('curator_channel', str(curator_channel.id))
    
    from views.curator import CuratorPanelPersistentView
    from utils.curator_utils import create_curator_panel_embed
    
    embed = create_curator_panel_embed(guild, db)
    view = CuratorPanelPersistentView()
    message = await curator_channel.send(embed=embed, view=view)
    db.save_curator_message(guild.id, curator_channel.id, message.id, 'panel')
    
    # ============================================
    # 2. КАНАЛ ДЛЯ КУРСАНТОВ
    # ============================================
    
    students_channel = await guild.create_text_channel(
        "📚-ученики-курсанты",
        category=category,
        topic="Обзор активных учеников | Только для кураторов"
    )
    
    await students_channel.set_permissions(everyone, read_messages=False)
    if curator_role_id:
        role = guild.get_role(int(curator_role_id))
        if role:
            await students_channel.set_permissions(role, read_messages=True, send_messages=True)
    if gm_role_id:
        role = guild.get_role(int(gm_role_id))
        if role:
            await students_channel.set_permissions(role, read_messages=True, send_messages=True)
    if dev_id:
        dev = guild.get_member(int(dev_id))
        if dev:
            await students_channel.set_permissions(dev, read_messages=True, send_messages=True)
    
    db.set_setting('students_channel', str(students_channel.id))
    
    from utils.curator_utils import create_students_overview_embed, create_activity_embed
    
    overview_embed = create_students_overview_embed(guild, db)
    overview_msg = await students_channel.send(embed=overview_embed)
    db.save_curator_channel_message(guild.id, students_channel.id, overview_msg.id, 'students')
    
    activity_embed = create_activity_embed(db)
    activity_msg = await students_channel.send(embed=activity_embed)
    db.save_curator_channel_message(guild.id, students_channel.id, activity_msg.id, 'activity')
    
    db.add_curator_log(
        "🔧 Созданы каналы кураторов и курсантов",
        interaction.user.id,
        f"Кураторы: {curator_channel.name}, Курсанты: {students_channel.name}",
        None
    )
    
    await interaction.followup.send(
        f"✅ **Каналы созданы!**\n\n"
        f"👨‍🏫 **Канал кураторов:** {curator_channel.mention}\n"
        f"📚 **Канал курсантов:** {students_channel.mention}\n\n"
        f"🔐 Настройте роль кураторов в `/settings` → Кураторы\n"
        f"🔄 Обновить панель: `/curator_panel_refresh`",
        ephemeral=True
    )


@bot.tree.command(name="curator_panel_refresh", description="🔄 Обновить панель кураторов")
async def curator_panel_refresh(interaction: discord.Interaction):
    """Обновляет панель кураторов (если кнопки сломались)"""
    db = bot.get_db(interaction.guild_id)
    
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    
    if str(interaction.user.id) != db.get_setting('developer_id', '') and not utils.is_guild_master(interaction.user, db):
        await interaction.response.send_message("❌ Только разработчик или глава гильдии!", ephemeral=True)
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
        await interaction.followup.send(
            "❌ Канал кураторов не найден!\n"
            "Создайте новый: `/curator_panel_setup`",
            ephemeral=True
        )
        return
    
    try:
        message = await channel.fetch_message(panel_data['message_id'])
    except:
        await interaction.followup.send(
            "❌ Сообщение с панелью не найдено!\n"
            "Создайте новое: `/curator_panel_setup`",
            ephemeral=True
        )
        return
    
    from views.curator import CuratorPanelPersistentView
    from utils.curator_utils import create_curator_panel_embed
    
    embed = create_curator_panel_embed(interaction.guild, db)
    view = CuratorPanelPersistentView()
    
    await message.edit(embed=embed, view=view)
    
    db.add_curator_log(
        "🔄 Обновлена панель кураторов",
        interaction.user.id,
        f"Канал: {channel.name}",
        channel.id
    )
    
    await interaction.followup.send(
        f"✅ Панель кураторов обновлена в {channel.mention}!",
        ephemeral=True
    )


@bot.tree.command(name="curator_panel_remove", description="🗑️ Удалить канал кураторов")
async def curator_panel_remove(interaction: discord.Interaction):
    """Удаляет канал кураторов"""
    db = bot.get_db(interaction.guild_id)
    
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    
    if str(interaction.user.id) != db.get_setting('developer_id', '') and not utils.is_guild_master(interaction.user, db):
        await interaction.response.send_message("❌ Только разработчик или глава гильдии!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    channel_id = db.get_setting('curator_channel', '')
    if not channel_id:
        await interaction.followup.send("❌ Канал кураторов не найден!", ephemeral=True)
        return
    
    channel = interaction.guild.get_channel(int(channel_id))
    if channel:
        await channel.delete()
    
    db.set_setting('curator_channel', '')
    db.set_setting('curator_panel_message', '')
    
    db.add_curator_log(
        "🗑️ Удалена панель кураторов",
        interaction.user.id,
        f"Канал: {channel.name if channel else 'Не найден'}",
        None
    )
    
    await interaction.followup.send("✅ Канал кураторов удален!", ephemeral=True)


@bot.tree.command(name="check_apps", description="🔍 Проверить активные заявки (разработчик)")
async def check_apps(interaction: discord.Interaction):
    db = bot.get_db(interaction.guild_id)
    if not db:
        await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
        return
    if str(interaction.user.id) != db.get_setting('developer_id', ''):
        await interaction.response.send_message("❌ Только разработчик!", ephemeral=True)
        return
    all_apps = db.cursor.execute('SELECT id, user_id, channel_id, status FROM applications').fetchall()
    pending = db.cursor.execute('SELECT id, user_id, channel_id, status FROM applications WHERE status = "pending"').fetchall()
    embed = Embed(title="📋 Статус заявок", color=Color.blue())
    embed.add_field(name="📝 Всего заявок", value=str(len(all_apps)), inline=True)
    embed.add_field(name="⏳ В ожидании", value=str(len(pending)), inline=True)
    if pending:
        for app in pending:
            app_id, user_id, channel_id, status = app
            channel = interaction.guild.get_channel(channel_id)
            embed.add_field(
                name=f"Заявка #{app_id}",
                value=f"👤 <@{user_id}>\n📁 {channel.mention if channel else 'Канал не найден'}\n📊 Статус: {status}",
                inline=False
            )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="fix_app", description="🔧 Восстановить кнопки в заявке (разработчик)")
@app_commands.describe(app_id="ID заявки")
async def fix_app(interaction: discord.Interaction, app_id: int):
    db = bot.get_db(interaction.guild_id)
    if not db or str(interaction.user.id) != db.get_setting('developer_id', ''):
        await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    app = db.cursor.execute('''
        SELECT id, user_id, channel_id, message_id, data, status
        FROM applications WHERE id = ? AND status = "pending"
    ''', (app_id,)).fetchone()

    if not app:
        await interaction.followup.send(f"❌ Заявка #{app_id} не найдена или не активна.", ephemeral=True)
        return

    app_id_db, user_id, channel_id, message_id, data_raw, status = app
    channel = interaction.guild.get_channel(channel_id)
    if not channel:
        await interaction.followup.send(f"❌ Канал не найден.", ephemeral=True)
        return

    data = json.loads(data_raw) if data_raw else {}
    view = ApplicationReviewView(channel_id, user_id, app_id, data)

    # Ищем сообщение
    if message_id:
        try:
            msg = await channel.fetch_message(message_id)
            if msg.author == interaction.client.user and msg.embeds:
                interaction.client.add_view(view, message_id=msg.id)
                await msg.edit(view=view)
                await interaction.followup.send(f"✅ Кнопки восстановлены (сообщение {msg.id})", ephemeral=True)
                return
        except:
            pass

    # Ищем в истории
    async for msg in channel.history(limit=30):
        if msg.author == interaction.client.user and msg.embeds:
            embed_title = msg.embeds[0].title if msg.embeds else ""
            if "Заявка" in embed_title or "📝" in embed_title:
                interaction.client.add_view(view, message_id=msg.id)
                await msg.edit(view=view)
                db.cursor.execute('UPDATE applications SET message_id = ? WHERE id = ?', (msg.id, app_id))
                db.conn.commit()
                await interaction.followup.send(f"✅ Кнопки восстановлены из истории (сообщение {msg.id})", ephemeral=True)
                return

    # Если ничего не найдено – пересоздаём
    embed = Embed(title=f"📝 Заявка #{app_id}", description=f"**Заявитель:** <@{user_id}>", color=Color.purple())
    embed.add_field(name="👤 Личное имя", value=f"```{data.get('real_name', '')}```", inline=True)
    embed.add_field(name="🎮 Имя персонажа", value=f"```{data.get('character_name', '')}```", inline=True)
    embed.add_field(name="⚔️ Класс", value=f"**{data.get('class_spec', 'Не указан')}**", inline=True)
    embed.add_field(name="🎯 Специализация", value=f"```{data.get('specialization', 'Не указана')}```", inline=True)
    embed.add_field(name="💎 iLvl", value=f"```{data.get('item_level', 0)}```", inline=True)
    embed.add_field(name="📅 Дни рейдов", value=f"```{utils.format_days(data.get('available_days', ''))}```", inline=True)
    embed.add_field(name="🎭 Роль", value=f"**{RAID_ROLE_NAMES.get(data.get('raid_role', 'mdd'), 'МДД')}**", inline=True)
    embed.add_field(name="👤 Пригласил", value=f"```{data.get('invited_by', '')}```", inline=True)
    if data.get('profile_url'):
        embed.add_field(name="🔗 Профиль", value=f"[Sirus]({data['profile_url']})", inline=True)
    embed.set_footer(text=f"ID: {app_id}")

    msg = await channel.send(embed=embed, view=view)
    interaction.client.add_view(view, message_id=msg.id)
    db.cursor.execute('UPDATE applications SET message_id = ? WHERE id = ?', (msg.id, app_id))
    db.conn.commit()
    await interaction.followup.send(f"✅ Сообщение пересоздано (ID {msg.id})", ephemeral=True)


@bot.tree.command(name="force_app_status", description="🔧 Принудительно изменить статус заявки (разработчик)")
@app_commands.describe(app_id="ID заявки", status="Новый статус (pending/accepted/rejected/blacklisted)")
async def force_app_status(interaction: discord.Interaction, app_id: int, status: str):
    db = bot.get_db(interaction.guild_id)
    if not db or str(interaction.user.id) != db.get_setting('developer_id', ''):
        await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
        return

    if status not in ['pending', 'accepted', 'rejected', 'blacklisted']:
        await interaction.response.send_message("❌ Неверный статус! Допустимые: pending, accepted, rejected, blacklisted", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    # Проверяем, существует ли заявка
    db.cursor.execute('SELECT id, user_id, channel_id, data, status FROM applications WHERE id = ?', (app_id,))
    app = db.cursor.fetchone()
    if not app:
        await interaction.followup.send(f"❌ Заявка #{app_id} не найдена!", ephemeral=True)
        return

    app_id_db, user_id, channel_id, data_raw, old_status = app

    # Обновляем статус
    db.cursor.execute('UPDATE applications SET status = ?, reviewer_id = ? WHERE id = ?', (status, interaction.user.id, app_id))
    db.conn.commit()
    db.add_log(f"🔄 Статус заявки #{app_id} изменён", interaction.user.id, details=f"{old_status} → {status}")

    # Если новый статус pending, восстанавливаем кнопки (вызовем fix_app логику)
    if status == 'pending':
        # Просто перенаправим логику восстановления (можно скопировать из fix_app, но проще вызвать fix_app через команду? Нет, проще продублировать)
        data = json.loads(data_raw) if data_raw else {}
        channel = interaction.guild.get_channel(channel_id)
        if channel:
            from views.applications import ApplicationReviewView
            view = ApplicationReviewView(channel_id, user_id, app_id, data)
            # Поиск сообщения
            found = False
            if app[3]:  # message_id
                try:
                    msg = await channel.fetch_message(app[3])
                    if msg.author == interaction.client.user and msg.embeds:
                        interaction.client.add_view(view, message_id=msg.id)
                        await msg.edit(view=view)
                        found = True
                        await interaction.followup.send(f"✅ Статус заявки #{app_id} изменён на `{status}` и кнопки восстановлены по message_id!", ephemeral=True)
                except:
                    pass
            if not found:
                async for msg in channel.history(limit=30):
                    if msg.author == interaction.client.user and msg.embeds:
                        embed_title = msg.embeds[0].title if msg.embeds else ""
                        if "Заявка" in embed_title or "📝" in embed_title:
                            interaction.client.add_view(view, message_id=msg.id)
                            await msg.edit(view=view)
                            db.cursor.execute('UPDATE applications SET message_id = ? WHERE id = ?', (msg.id, app_id))
                            db.conn.commit()
                            found = True
                            await interaction.followup.send(f"✅ Статус заявки #{app_id} изменён на `{status}` и кнопки восстановлены из истории!", ephemeral=True)
                            break
            if not found:
                # пересоздаем сообщение
                embed = Embed(title=f"📝 Заявка #{app_id}", description=f"**Заявитель:** <@{user_id}>", color=Color.purple())
                embed.add_field(name="👤 Личное имя", value=f"```{data.get('real_name', '')}```", inline=True)
                embed.add_field(name="🎮 Имя персонажа", value=f"```{data.get('character_name', '')}```", inline=True)
                embed.add_field(name="⚔️ Класс", value=f"**{data.get('class_spec', 'Не указан')}**", inline=True)
                embed.add_field(name="🎯 Специализация", value=f"```{data.get('specialization', 'Не указана')}```", inline=True)
                embed.add_field(name="💎 iLvl", value=f"```{data.get('item_level', 0)}```", inline=True)
                embed.add_field(name="📅 Дни рейдов", value=f"```{utils.format_days(data.get('available_days', ''))}```", inline=True)
                embed.add_field(name="🎭 Роль", value=f"**{RAID_ROLE_NAMES.get(data.get('raid_role', 'mdd'), 'МДД')}**", inline=True)
                embed.add_field(name="👤 Пригласил", value=f"```{data.get('invited_by', '')}```", inline=True)
                if data.get('profile_url'):
                    embed.add_field(name="🔗 Профиль", value=f"[Sirus]({data['profile_url']})", inline=True)
                embed.set_footer(text=f"ID: {app_id}")
                msg = await channel.send(embed=embed, view=view)
                interaction.client.add_view(view, message_id=msg.id)
                db.cursor.execute('UPDATE applications SET message_id = ? WHERE id = ?', (msg.id, app_id))
                db.conn.commit()
                await interaction.followup.send(f"✅ Статус заявки #{app_id} изменён на `{status}` и сообщение пересоздано!", ephemeral=True)
        else:
            await interaction.followup.send(f"✅ Статус заявки #{app_id} изменён на `{status}`, но канал не найден.", ephemeral=True)
    else:
        await interaction.followup.send(f"✅ Статус заявки #{app_id} изменён на `{status}`", ephemeral=True)


@bot.tree.command(name="fix_trainee_duplicates", description="🔧 Удалить дубликаты в trainees (разработчик)")
async def fix_trainee_duplicates(interaction: discord.Interaction):
    db = bot.get_db(interaction.guild_id)
    if not db or str(interaction.user.id) != db.get_setting('developer_id', ''):
        await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    # Находим дубликаты
    db.cursor.execute('''
        SELECT user_id, COUNT(*) as count 
        FROM trainees 
        GROUP BY user_id 
        HAVING COUNT(*) > 1
    ''')
    duplicates = db.cursor.fetchall()
    
    if not duplicates:
        await interaction.followup.send("✅ Дубликатов не найдено!", ephemeral=True)
        return
    
    # Удаляем дубликаты
    db.cursor.execute('''
        DELETE FROM trainees 
        WHERE id NOT IN (
            SELECT MIN(id) 
            FROM trainees 
            GROUP BY user_id
        )
    ''')
    db.conn.commit()
    
    deleted = db.cursor.rowcount
    
    # Обновляем канал учеников
    from utils.curator_utils import refresh_students_channel
    await refresh_students_channel(interaction.guild, db)
    
    await interaction.followup.send(
        f"✅ Удалено дубликатов: **{deleted}**\n"
        f"🔄 Канал учеников обновлён!",
        ephemeral=True
    )
# ========== ЗАПУСК БОТА ==========

if __name__ == "__main__":
    bot.run(config.TOKEN)