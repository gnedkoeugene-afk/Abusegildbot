# utils/curator_utils.py — ПОЛНЫЙ ИСПРАВЛЕННЫЙ ФАЙЛ

import discord
from discord import Embed, Color
from datetime import datetime
from typing import Optional, Dict, List
import utils


def is_curator(user: discord.Member, db) -> bool:
    """Проверяет, является ли пользователь куратором"""
    if not user or not db:
        return False
    
    # Разработчик всегда куратор
    if db.get_setting('developer_id', '') == str(user.id):
        return True
    
    # Проверяем роль куратора
    curator_role_id = utils.safe_int(db.get_setting('curator_role', ''))
    if curator_role_id:
        role = user.guild.get_role(curator_role_id)
        if role and role in user.roles:
            return True
    
    return False


def can_manage_curator_panel(user: discord.Member, db) -> bool:
    """Может ли пользователь управлять панелью куратора"""
    if not user or not db:
        return False
    
    # Разработчик всегда имеет доступ
    if db.get_setting('developer_id', '') == str(user.id):
        return True
    
    # Глава гильдии
    if utils.is_guild_master(user, db):
        return True
    
    # Куратор
    if is_curator(user, db):
        return True
    
    return False


def get_level_from_points(points: int) -> int:
    """Определить уровень по баллам"""
    levels = [
        (0, 0),      # 0 уровень
        (1, 100),    # 1 уровень
        (2, 250),    # 2 уровень
        (3, 500),    # 3 уровень
        (4, 800),    # 4 уровень
        (5, 1200)    # 5 уровень
    ]
    
    current_level = 0
    for level, required in levels:
        if points >= required:
            current_level = level
        else:
            break
    
    return current_level


def get_level_name(level: int) -> str:
    """Получить название уровня"""
    names = {
        0: '🆕 Новичок',
        1: '📖 Ученик',
        2: '👁️ Наблюдатель',
        3: '🎯 Ассистент',
        4: '⚔️ Ведущий',
        5: '🎓 Мастер'
    }
    return names.get(level, '❓ Неизвестно')


def get_next_level_points(points: int) -> int:
    """Получить баллы для следующего уровня"""
    levels = [100, 250, 500, 800, 1200]
    for required in levels:
        if points < required:
            return required
    return 0


def get_progress_bar(points: int) -> str:
    """Получить прогресс-бар"""
    next_level = get_next_level_points(points)
    if next_level == 0:
        return '████████████████████ 100%'
    
    prev_level = 0
    for l in [0, 100, 250, 500, 800, 1200]:
        if l < next_level:
            prev_level = l
    
    progress = ((points - prev_level) / (next_level - prev_level)) * 100
    progress = min(100, max(0, int(progress)))
    
    filled = progress // 5
    empty = 20 - filled
    
    return f"{'█' * filled}{'░' * empty} {progress}%"


def get_difficulty_emoji(difficulty: int) -> str:
    """Получить эмодзи сложности"""
    emojis = {
        1: '🟢',
        2: '🟡',
        3: '🔴'
    }
    return emojis.get(difficulty, '⚪')


def get_difficulty_name(difficulty: int) -> str:
    """Получить название сложности"""
    names = {
        1: 'Легкое',
        2: 'Среднее',
        3: 'Сложное'
    }
    return names.get(difficulty, 'Неизвестно')


def get_status_emoji(status: str) -> str:
    """Получить эмодзи статуса"""
    emojis = {
        'pending': '⏳',
        'active': '📊',
        'completed': '✅',
        'graduated': '🎓',
        'expelled': '❌',
        'approved': '✅',
        'rejected': '❌',
        'expired': '⏰'
    }
    return emojis.get(status, '❓')


def get_points_for_task(difficulty: int) -> int:
    """Сколько баллов давать за задание"""
    rewards = {
        1: 10,   # Легкое
        2: 25,   # Среднее
        3: 50    # Сложное
    }
    return rewards.get(difficulty, 10)


def create_students_overview_embed(guild: discord.Guild, db) -> discord.Embed:
    """Создает эмбед с обзором учеников"""
    
    try:
        total = db.cursor.execute('SELECT COUNT(*) FROM trainees WHERE status IN ("active", "graduated")').fetchone()[0]
        active = db.cursor.execute('SELECT COUNT(*) FROM trainees WHERE status = "active"').fetchone()[0]
        graduated = db.cursor.execute('SELECT COUNT(*) FROM trainees WHERE status = "graduated"').fetchone()[0]
        
        students = db.cursor.execute('''
            SELECT 
                id,
                user_id,
                level,
                points,
                status,
                main_character_id,
                experience,
                motivation,
                applied_at,
                graduated_at
            FROM trainees
            WHERE status IN ('active', 'graduated')
            ORDER BY points DESC
        ''').fetchall()
    except:
        students = []
        total = 0
        active = 0
        graduated = 0
    
    embed = discord.Embed(
        title="📚 УЧЕНИКИ И КУРСАНТЫ",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="📊 СТАТИСТИКА",
        value=(
            f"👥 Всего учеников: **{total}**\n"
            f"🟢 Активных: **{active}**\n"
            f"🎓 Выпускников: **{graduated}**"
        ),
        inline=False
    )
    
    if not students:
        embed.description = "📭 Нет активных учеников."
        embed.color = discord.Color.orange()
        return embed
    
    for student in students[:10]:
        user = guild.get_member(student[1])
        username = user.display_name if user else f"ID: {student[1]}"
        trainee_id = student[0]
        level = student[2] or 0
        points = student[3] or 0
        status = student[4] or 'active'
        
        status_emoji = "🟢" if status == 'active' else "🎓"
        status_text = "Активен" if status == 'active' else "Выпускник"
        
        progress = min(100, int((points / 1200) * 100))
        bar = '█' * (progress // 5) + '░' * (20 - progress // 5)
        
        embed.add_field(
            name=f"{status_emoji} **{username}**",
            value=(
                f"📊 Уровень: **{level}/5**\n"
                f"⭐ Баллы: **{points}**\n"
                f"📈 Прогресс: `{bar}` {progress}%\n"
                f"📋 Статус: {status_text}"
            ),
            inline=True
        )
    
    if len(students) > 10:
        embed.set_footer(text=f"Показано 10 из {len(students)} учеников")
    else:
        embed.set_footer(text=f"Всего: {len(students)} учеников")
    
    return embed


def create_activity_embed(db, guild: discord.Guild = None, limit: int = 10) -> discord.Embed:
    """Создает эмбед с последними активностями (из trainee_logs)"""
    
    embed = discord.Embed(
        title="📋 ПОСЛЕДНИЕ ДЕЙСТВИЯ",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    try:
        activities = db.cursor.execute('''
            SELECT 
                trainee_id,
                action,
                details,
                performed_by,
                created_at
            FROM trainee_logs
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,)).fetchall()
    except:
        activities = []
    
    if not activities:
        embed.description = "📭 Нет активностей."
        embed.color = discord.Color.orange()
        return embed
    
    for activity in activities[:10]:
        trainee_id = activity[0]
        action = activity[1] or '📝 Действие'
        details = activity[2] or ''
        performed_by = activity[3]
        created_at = activity[4][:16] if activity[4] else 'Неизвестно'
        
        username = f"Кандидат #{trainee_id}"
        if guild:
            trainee = db.get_trainee_by_id(trainee_id) if hasattr(db, 'get_trainee_by_id') else None
            if trainee:
                user = guild.get_member(trainee['user_id'])
                username = user.mention if user else f"ID: {trainee['user_id']}"
        
        performer = "Система"
        if performed_by:
            performer_obj = guild.get_member(performed_by) if guild else None
            performer = performer_obj.mention if performer_obj else f"ID: {performed_by}"
        
        embed.add_field(
            name=action,
            value=(
                f"👤 **{username}**\n"
                f"📝 {details[:200] if details else '—'}\n"
                f"👮 {performer}\n"
                f"⏰ {created_at}"
            ),
            inline=False
        )
    
    embed.set_footer(text=f"Показано {len(activities)} последних действий")
    
    return embed


def create_curator_panel_embed(guild: discord.Guild, db) -> discord.Embed:
    """Создает эмбед для панели кураторов"""
    
    try:
        pending_apps = len(db.get_pending_applications())
        sections = len(db.get_all_sections())
        active_students = 0
        if hasattr(db, 'cursor'):
            active_students = db.cursor.execute(
                'SELECT COUNT(*) FROM trainees WHERE status = "active"'
            ).fetchone()[0]
    except:
        pending_apps = 0
        sections = 0
        active_students = 0
    
    embed = discord.Embed(
        title="👨‍🏫 ПАНЕЛЬ КУРАТОРОВ",
        description="Управление обучением игроков",
        color=discord.Color.blue(),
        timestamp=datetime.now()
    )
    
    embed.add_field(
        name="📊 СТАТИСТИКА",
        value=(
            f"📝 Заявок на рассмотрении: **{pending_apps}**\n"
            f"📚 Разделов: **{sections}**\n"
            f"👤 Активных учеников: **{active_students}**"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🛠️ ДОСТУПНЫЕ ДЕЙСТВИЯ",
        value=(
            "📚 **Добавить контент** — раздел, тест, задание\n"
            "✏️ **Управление заданиями** — редактировать/удалять\n"
            "👤 **Добавить игрока** — из заявок\n"
            "📤 **Выдать задание** — назначить игроку\n"
            "📊 **Просмотреть рейтинг** — таблица успехов\n"
            "👀 **Просмотреть задание** — детали"
        ),
        inline=False
    )
    
    embed.set_footer(
        text=f"Сервер: {guild.name}",
        icon_url=guild.icon.url if guild.icon else None
    )
    
    return embed


def get_active_students_with_progress(db, guild: discord.Guild) -> List[Dict]:
    """Получить активных учеников с прогрессом"""
    try:
        return db.get_active_students_with_progress()
    except:
        return []


def get_recent_student_activity(db, limit: int = 5) -> List[Dict]:
    """Получить последние активности"""
    try:
        return db.get_recent_student_activity(limit)
    except:
        return []


# ============================================
# StudentTaskButton — ПЕРЕМЕЩЕН СЮДА
# ============================================

class StudentTaskButton(discord.ui.Button):
    """Кнопка для ученика в канале (со статическим custom_id)"""
    
    def __init__(self, trainee_id: int, user_id: int, username: str):
        super().__init__(
            label=f"📤 {username}",
            style=discord.ButtonStyle.success,
            emoji="📤",
            custom_id="student_task_button"  # СТАТИЧЕСКИЙ custom_id
        )
        self.trainee_id = trainee_id
        self.user_id = user_id
    
    async def callback(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        # Получаем trainee_id из БД по user_id
        trainee = db.get_trainee_by_user(interaction.user.id)
        if not trainee:
            await interaction.response.send_message("❌ Вы не являетесь учеником!", ephemeral=True)
            return
        
        trainee_id = trainee['id']
        
        tasks = db.cursor.execute('''
            SELECT id, title, points_reward, difficulty, status
            FROM trainee_tasks
            WHERE trainee_id = ? AND status = 'pending'
            ORDER BY created_at DESC
        ''', (trainee_id,)).fetchall()
        
        if not tasks:
            await interaction.response.send_message(
                "📭 У вас нет активных заданий!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📋 Ваши задания",
            description="Выберите задание для сдачи:",
            color=discord.Color.blue()
        )
        
        options = []
        for task in tasks[:25]:
            options.append(discord.SelectOption(
                label=task[1][:50] if task[1] else 'Без названия',
                value=str(task[0]),
                description=f"+{task[2]} баллов"
            ))
        
        select = discord.ui.Select(
            placeholder="Выберите задание...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        async def select_callback(inter: discord.Interaction):
            task_id = int(select.values[0])
            from modals.curator_modals import TaskReportModal
            modal = TaskReportModal(task_id)
            await inter.response.send_modal(modal)
        
        select.callback = select_callback
        
        view = discord.ui.View()
        view.add_item(select)
        view.add_item(discord.ui.Button(
            label="❌ Отмена",
            style=discord.ButtonStyle.danger,
            custom_id="cancel"
        ))
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ============================================
# ОБНОВЛЕНИЕ КАНАЛА УЧЕНИКОВ
# ============================================

async def refresh_students_channel(guild: discord.Guild, db):
    """Обновляет канал учеников-курсантов (перезаписывает сообщение)"""
    
    from views.curator import StudentTaskButton
    
    channel_id = db.get_setting('students_channel', '')
    if not channel_id:
        return
    
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return
    
    embed = create_students_overview_embed(guild, db)
    
    students = db.cursor.execute('''
        SELECT id, user_id FROM trainees WHERE status = 'active'
    ''').fetchall()
    
    view = discord.ui.View(timeout=None)  # timeout=None для постоянных кнопок
    
    for student in students[:10]:
        user = guild.get_member(student[1])
        if user:
            button = StudentTaskButton(student[0], student[1], user.display_name[:20])
            view.add_item(button)
    
    # Ищем старое сообщение и обновляем его
    try:
        async for msg in channel.history(limit=30):
            if msg.author == guild.me:
                await msg.edit(embed=embed, view=view)
                # Сохраняем ID сообщения в БД для восстановления
                db.set_setting('students_message_id', str(msg.id))
                print(f"✅ Канал учеников обновлён на {guild.name}")
                return
    except:
        pass
    
    # Если сообщения нет — отправляем новое
    new_msg = await channel.send(embed=embed, view=view)
    db.set_setting('students_message_id', str(new_msg.id))
    print(f"✅ Новое сообщение отправлено в канал учеников на {guild.name}")


# ============================================
# ВОССТАНОВЛЕНИЕ КАНАЛА УЧЕНИКОВ
# ============================================

async def restore_students_channel(guild: discord.Guild, db):
    """Восстанавливает канал учеников-курсантов после рестарта"""
    
    channel_id = db.get_setting('students_channel', '')
    if not channel_id:
        return
    
    channel = guild.get_channel(int(channel_id))
    if not channel:
        return
    
    # Пробуем найти сохраненное сообщение
    message_id = db.get_setting('students_message_id', '')
    
    if message_id:
        try:
            msg = await channel.fetch_message(int(message_id))
            if msg.author == guild.me:
                # Обновляем сообщение
                embed = create_students_overview_embed(guild, db)
                
                students = db.cursor.execute('''
                    SELECT id, user_id FROM trainees WHERE status = 'active'
                ''').fetchall()
                
                view = discord.ui.View(timeout=None)
                for student in students[:10]:
                    user = guild.get_member(student[1])
                    if user:
                        button = StudentTaskButton(student[0], student[1], user.display_name[:20])
                        view.add_item(button)
                
                await msg.edit(embed=embed, view=view)
                print(f"✅ Канал учеников восстановлен на {guild.name}")
                return
        except:
            pass
    
    # Если сообщение не найдено — обновляем канал
    await refresh_students_channel(guild, db)