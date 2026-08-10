# views/curator.py — ПОЛНЫЙ ИСПРАВЛЕННЫЙ ФАЙЛ

import discord
from discord.ui import View, Button, Select, Modal, TextInput
from discord import Embed, Color, ButtonStyle, Interaction, TextStyle
from datetime import datetime, timedelta
import utils
from utils.curator_utils import is_curator, can_manage_curator_panel, get_level_from_points
from modals.curator_modals import (
    AddSectionModal, AddTestModal, AddTaskModal, AssignTaskModal,
    TaskRejectModal, TaskReportModal, EditTheoryModal, EditPassConditionModal,
    EditTaskModal
)


# ============================================
# ГЛАВНАЯ ПАНЕЛЬ КУРАТОРА (НЕ ПЕРСИСТЕНТНАЯ)
# ============================================

class CuratorPanelView(View):
    """Главная панель куратора (для /curator)"""
    
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(AddContentButton())
        self.add_item(ManageTasksButton())
        self.add_item(AddPlayerButton())
        self.add_item(AssignTaskButton())
        self.add_item(ViewRatingButton())
        self.add_item(ViewTaskButton())


# ============================================
# ПЕРСИСТЕНТНАЯ ПАНЕЛЬ КУРАТОРА (ДЛЯ КАНАЛА)
# ============================================

class CuratorPanelPersistentView(View):
    """Постоянная панель куратора (работает после рестарта)"""
    
    def __init__(self):
        super().__init__(timeout=None)
        
        # Ряд 0
        self.add_item(AddContentButtonPersistent())
        self.add_item(ManageTasksButtonPersistent())
        
        # Ряд 1
        self.add_item(AddPlayerButtonPersistent())
        self.add_item(AssignTaskButtonPersistent())
        self.add_item(ViewRatingButtonPersistent())
        self.add_item(ViewTaskButtonPersistent())
        
        # Ряд 2
        self.add_item(RefreshStudentsButtonPersistent())
        self.add_item(CuratorHelpButtonPersistent())
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Проверка прав при нажатии (РАЗРАБОТЧИК ВСЕГДА ПРОПУСКАЕТСЯ)"""
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message(
                "❌ Ошибка подключения к базе данных!\n"
                "Пожалуйста, сообщите администратору.",
                ephemeral=True
            )
            return False
        
        dev_id = db.get_setting('developer_id', '')
        if dev_id and str(interaction.user.id) == dev_id:
            return True
        
        if not can_manage_curator_panel(interaction.user, db):
            await interaction.response.send_message(
                "❌ У вас нет прав куратора!\n"
                "Обратитесь к администрации для получения роли.",
                ephemeral=True
            )
            return False
        
        return True


# ============================================
# КНОПКИ ДЛЯ ПЕРСИСТЕНТНОЙ ПАНЕЛИ
# ============================================

class AddContentButtonPersistent(Button):
    """Кнопка: Добавить контент (persistent)"""
    
    def __init__(self):
        super().__init__(
            label="📚 Добавить контент",
            style=ButtonStyle.primary,
            emoji="📚",
            row=0,
            custom_id="curator_add_content_persistent"
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        embed = Embed(
            title="📚 Что хотите добавить?",
            description="Выберите тип контента:",
            color=Color.blue()
        )
        
        embed.add_field(
            name="1️⃣ Раздел (инст)",
            value="Создать новый раздел для обучения",
            inline=False
        )
        embed.add_field(
            name="2️⃣ Теория",
            value="Добавить теорию к существующему разделу",
            inline=False
        )
        embed.add_field(
            name="3️⃣ Тест (опрос)",
            value="Добавить тест к разделу",
            inline=False
        )
        embed.add_field(
            name="4️⃣ Задание",
            value="Добавить задание к разделу",
            inline=False
        )
        embed.add_field(
            name="5️⃣ Зачет",
            value="Настроить условия зачета",
            inline=False
        )
        
        view = ContentTypeSelectView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ManageTasksButtonPersistent(Button):
    """Кнопка: Управление заданиями (persistent)"""
    
    def __init__(self):
        super().__init__(
            label="✏️ Управление заданиями",
            style=ButtonStyle.primary,
            emoji="✏️",
            row=0,
            custom_id="curator_manage_tasks_persistent"
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        sections = db.get_all_sections()
        
        if not sections:
            await interaction.response.send_message(
                "❌ Нет разделов! Сначала создайте раздел.",
                ephemeral=True
            )
            return
        
        embed = Embed(
            title="✏️ Управление заданиями",
            description="Выберите раздел, чтобы управлять заданиями:",
            color=Color.blue()
        )
        
        for section in sections:
            tasks = db.get_tasks_for_section(section['id'])
            task_count = len(tasks)
            embed.add_field(
                name=f"📚 {section['name']}",
                value=f"Заданий: {task_count}",
                inline=True
            )
        
        view = TaskManageSelectView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AddPlayerButtonPersistent(Button):
    """Кнопка: Добавить игрока (persistent)"""
    
    def __init__(self):
        super().__init__(
            label="👤 Добавить игрока",
            style=ButtonStyle.success,
            emoji="👤",
            row=1,
            custom_id="curator_add_player_persistent"
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        # Получаем все заявки со статусом "pending"
        applications = db.get_pending_applications()
        
        if not applications:
            await interaction.response.send_message(
                "📭 Нет заявок на рассмотрение.\n"
                "Игроки подают заявки через 'Обучение на РЛ' в МоиПерсонажи.",
                ephemeral=True
            )
            return
        
        embed = Embed(
            title="👤 Заявки на обучение",
            description=f"Всего заявок: {len(applications)}\n\n"
                       f"Выберите заявку, чтобы просмотреть информацию и принять/отклонить:",
            color=Color.blue()
        )
        
        # Показываем краткий список заявок
        for app in applications[:5]:
            user = interaction.guild.get_member(app['user_id'])
            char = db.get_character_by_id(app['character_id'])
            char_name = char['character_name'] if char else "Неизвестно"
            
            embed.add_field(
                name=f"📋 Заявка #{app['id']}",
                value=(
                    f"**Игрок:** {user.mention if user else 'Не найден'}\n"
                    f"**Персонаж:** {char_name}\n"
                    f"**Дата:** {app['applied_at'][:16] if app['applied_at'] else 'Неизвестно'}"
                ),
                inline=False
            )
        
        view = PlayerSelectView(applications)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AssignTaskButtonPersistent(Button):
    """Кнопка: Выдать задание кандидату (persistent)"""
    
    def __init__(self):
        super().__init__(
            label="📤 Выдать задание",
            style=ButtonStyle.success,
            emoji="📤",
            row=1,
            custom_id="curator_assign_task_persistent"
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        # Получаем всех активных кандидатов
        try:
            candidates = db.cursor.execute('''
                SELECT id, user_id, level, points, status 
                FROM trainees 
                WHERE status = 'active'
                ORDER BY points DESC
            ''').fetchall()
        except:
            candidates = []
        
        if not candidates:
            await interaction.response.send_message(
                "❌ Нет активных кандидатов!\n"
                "Сначала добавьте игроков через 'Добавить игрока'.",
                ephemeral=True
            )
            return
        
        options = []
        for candidate in candidates[:25]:
            user = interaction.guild.get_member(candidate[1])
            if user:
                task_count = db.cursor.execute('''
                    SELECT COUNT(*) FROM trainee_tasks 
                    WHERE trainee_id = ? AND status IN ('pending', 'completed')
                ''', (candidate[0],)).fetchone()[0]
                
                options.append(discord.SelectOption(
                    label=f"{user.display_name[:50]}",
                    value=str(candidate[0]),
                    description=f"Уровень: {candidate[2]}, Заданий: {task_count}"
                ))
        
        if not options:
            await interaction.response.send_message(
                "❌ Нет доступных кандидатов!",
                ephemeral=True
            )
            return
        
        select = Select(
            placeholder="Выберите кандидата...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        async def select_callback(inter: Interaction):
            trainee_id = int(select.values[0])
            await self.show_task_selection(inter, trainee_id)
        
        select.callback = select_callback
        
        view = View()
        view.add_item(select)
        view.add_item(Button(
            label="❌ Отмена",
            style=ButtonStyle.danger,
            custom_id="cancel"
        ))
        
        await interaction.response.send_message(
            "Выберите кандидата для выдачи задания:",
            view=view,
            ephemeral=True
        )
    
    async def show_task_selection(self, interaction: Interaction, trainee_id: int):
        """Показать выбор задания для кандидата"""
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        trainee = db.get_trainee_by_id(trainee_id)
        if not trainee:
            await interaction.response.send_message("❌ Кандидат не найден!", ephemeral=True)
            return
        
        user = interaction.guild.get_member(trainee['user_id'])
        
        embed = Embed(
            title=f"📤 Выдача задания",
            description=f"**Кандидат:** {user.mention if user else 'Не найден'}\n"
                       f"**Уровень:** {trainee['level']}\n"
                       f"**Баллов:** {trainee['points']}",
            color=Color.blue()
        )
        
        # Показываем задания кандидата
        trainee_tasks = db.cursor.execute('''
            SELECT id, title, status, points_reward 
            FROM trainee_tasks 
            WHERE trainee_id = ? 
            ORDER BY created_at DESC
            LIMIT 5
        ''', (trainee_id,)).fetchall()
        
        if trainee_tasks:
            tasks_text = ""
            for t in trainee_tasks:
                status_emoji = "✅" if t[2] == 'approved' else "⏳" if t[2] == 'pending' else "❌" if t[2] == 'rejected' else "📤" if t[2] == 'completed' else "❓"
                tasks_text += f"{status_emoji} **{t[1]}** (+{t[3]} баллов)\n"
            embed.add_field(
                name="📋 Задания кандидата",
                value=tasks_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📋 Задания кандидата",
                value="У кандидата пока нет заданий.",
                inline=False
            )
        
        # Выбор задания для выдачи
        try:
            tasks = db.cursor.execute('''
                SELECT id, title, description, difficulty, points_reward 
                FROM tasks 
                ORDER BY created_at DESC
            ''').fetchall()
        except:
            tasks = []
        
        if not tasks:
            await interaction.response.send_message(
                "❌ Нет доступных заданий!\n"
                "Сначала создайте задание через 'Добавить контент'.",
                ephemeral=True
            )
            return
        
        options = []
        for task in tasks[:25]:
            options.append(discord.SelectOption(
                label=task[1][:50] if task[1] else 'Без названия',
                value=str(task[0]),
                description=f"+{task[4] if task[4] else 0} баллов, Сложность: {task[3]}/3"
            ))
        
        select = Select(
            placeholder="Выберите задание для выдачи...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        async def select_callback(inter: Interaction):
            task_id = int(select.values[0])
            task = db.get_task(task_id)
            
            if not task:
                await inter.response.send_message("❌ Задание не найдено!", ephemeral=True)
                return
            
            existing = db.cursor.execute('''
                SELECT id FROM trainee_tasks 
                WHERE trainee_id = ? AND task_id = ? AND status != 'rejected'
            ''', (trainee_id, task_id)).fetchone()
            
            if existing:
                await inter.response.send_message(
                    "❌ Это задание уже выдано кандидату!\n"
                    "Выберите другое задание.",
                    ephemeral=True
                )
                return
            
            from modals.curator_modals import AssignTaskModal
            modal = AssignTaskModal(trainee_id, task_id)
            await inter.response.send_modal(modal)
        
        select.callback = select_callback
        
        view = View()
        view.add_item(select)
        view.add_item(Button(
            label="🔙 Назад",
            style=ButtonStyle.secondary,
            custom_id="back"
        ))
        
        await interaction.response.edit_message(embed=embed, view=view)


class ViewRatingButtonPersistent(Button):
    """Кнопка: Просмотреть рейтинг (persistent)"""
    
    def __init__(self):
        super().__init__(
            label="📊 Просмотреть рейтинг",
            style=ButtonStyle.primary,
            emoji="📊",
            row=1,
            custom_id="curator_view_rating_persistent"
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        try:
            rating = db.cursor.execute('''
                SELECT user_id, level, points, status
                FROM trainees
                WHERE status IN ('active', 'graduated')
                ORDER BY points DESC
            ''').fetchall()
        except:
            rating = []
        
        if not rating:
            await interaction.response.send_message(
                "📊 Нет данных для рейтинга.",
                ephemeral=True
            )
            return
        
        embed = Embed(
            title="📊 Рейтинг учеников",
            color=Color.gold(),
            timestamp=datetime.now()
        )
        
        for i, student in enumerate(rating[:10], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            user = interaction.guild.get_member(student[0])
            
            status_emoji = "📊" if student[3] == 'active' else "🎓"
            
            embed.add_field(
                name=f"{medal} {user.display_name if user else 'Неизвестно'}",
                value=(
                    f"⭐ Баллы: **{student[2]}**\n"
                    f"📊 Уровень: {student[1]}/5\n"
                    f"{status_emoji} Статус: {student[3]}"
                ),
                inline=True
            )
        
        if len(rating) > 10:
            embed.set_footer(text=f"Показано 10 из {len(rating)}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ViewTaskButtonPersistent(Button):
    """Кнопка: Просмотреть задание (persistent)"""
    
    def __init__(self):
        super().__init__(
            label="👀 Просмотреть задание",
            style=ButtonStyle.primary,
            emoji="👀",
            row=1,
            custom_id="curator_view_task_persistent"
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        tasks = db.get_pending_tasks_for_curator(interaction.user.id)
        
        if not tasks:
            await interaction.response.send_message(
                "📭 Нет заданий на проверку.\n"
                "Все задания либо выполнены, либо ещё не сданы.",
                ephemeral=True
            )
            return
        
        embed = Embed(
            title="👀 Задания на проверку",
            description=f"Всего заданий: {len(tasks)}",
            color=Color.blue(),
            timestamp=datetime.now()
        )
        
        for task in tasks[:10]:
            trainee = interaction.guild.get_member(task.get('trainee_user_id'))
            trainee_name = trainee.mention if trainee else f"ID: {task.get('trainee_user_id')}"
            
            embed.add_field(
                name=f"📝 {task.get('title', 'Без названия')[:50]}",
                value=(
                    f"👤 **Кандидат:** {trainee_name}\n"
                    f"💰 **Награда:** +{task.get('points_reward', 0)} баллов\n"
                    f"📅 **Сдано:** {task.get('completed_at', '')[:16] if task.get('completed_at') else 'Неизвестно'}"
                ),
                inline=False
            )
        
        if len(tasks) > 10:
            embed.set_footer(text=f"Показано 10 из {len(tasks)}")
        
        view = TaskSelectView(tasks)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class RefreshStudentsButtonPersistent(Button):
    """Кнопка обновления списка учеников (persistent)"""
    
    def __init__(self):
        super().__init__(
            label="🔄 Обновить учеников",
            style=ButtonStyle.secondary,
            emoji="🔄",
            row=2,
            custom_id="curator_refresh_students_persistent"
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        guild = interaction.guild
        
        await interaction.response.defer(ephemeral=True)
        
        from utils.curator_utils import create_students_overview_embed, create_activity_embed, refresh_students_channel
        
        # Обновляем канал учеников
        await refresh_students_channel(guild, db)
        
        # Обновляем активности
        activity_msg = db.get_curator_channel_message(guild.id, 'activity')
        if activity_msg:
            channel = guild.get_channel(activity_msg['channel_id'])
            if channel:
                try:
                    msg = await channel.fetch_message(activity_msg['message_id'])
                    embed = create_activity_embed(db, guild)
                    await msg.edit(embed=embed)
                except:
                    pass
        
        db.add_curator_log(
            "🔄 Обновлен список учеников",
            interaction.user.id,
            "Обновлены обзор и активности",
            None
        )
        
        await interaction.followup.send("✅ Список учеников обновлен!", ephemeral=True)


class CuratorHelpButtonPersistent(Button):
    """Кнопка помощи (для панели)"""
    
    def __init__(self):
        super().__init__(
            label="❓ Помощь",
            style=ButtonStyle.secondary,
            emoji="❓",
            row=2,
            custom_id="curator_help_persistent"
        )
    
    async def callback(self, interaction: Interaction):
        embed = Embed(
            title="❓ Справка по панели куратора",
            color=Color.blue()
        )
        
        embed.add_field(
            name="📚 Добавить контент",
            value="Создать раздел, теорию, тест или задание",
            inline=False
        )
        embed.add_field(
            name="✏️ Управление заданиями",
            value="Редактировать или удалять существующие задания",
            inline=False
        )
        embed.add_field(
            name="👤 Добавить игрока",
            value="Взять игрока из заявок и добавить в систему",
            inline=False
        )
        embed.add_field(
            name="📤 Выдать задание",
            value="Выдать задание конкретному кандидату",
            inline=False
        )
        embed.add_field(
            name="📊 Просмотреть рейтинг",
            value="Таблица успехов всех учеников",
            inline=False
        )
        embed.add_field(
            name="👀 Просмотреть задание",
            value="Посмотреть детали заданий кандидатов",
            inline=False
        )
        embed.set_footer(text="Все изменения сохраняются автоматически")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ
# ============================================

class ContentTypeSelectView(View):
    """Выбор типа контента"""
    
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(ContentTypeSelect())
        self.add_item(Button(
            label="❌ Отмена",
            style=ButtonStyle.danger,
            custom_id="cancel"
        ))


class ContentTypeSelect(Select):
    """Выпадающий список для выбора типа контента"""
    
    def __init__(self):
        options = [
            discord.SelectOption(
                label="1️⃣ Раздел (инст)",
                value="section",
                description="Создать новый раздел",
                emoji="📚"
            ),
            discord.SelectOption(
                label="2️⃣ Теория",
                value="theory",
                description="Добавить теорию к разделу",
                emoji="📝"
            ),
            discord.SelectOption(
                label="3️⃣ Тест (опрос)",
                value="test",
                description="Добавить тест к разделу",
                emoji="📋"
            ),
            discord.SelectOption(
                label="4️⃣ Задание",
                value="task",
                description="Добавить задание к разделу",
                emoji="📝"
            ),
            discord.SelectOption(
                label="5️⃣ Зачет",
                value="pass",
                description="Настроить условия зачета",
                emoji="🏆"
            )
        ]
        super().__init__(
            placeholder="Выберите тип контента...",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: Interaction):
        value = self.values[0]
        
        if value == "section":
            modal = AddSectionModal()
            await interaction.response.send_modal(modal)
        
        elif value == "theory":
            await self.show_section_select(interaction, "theory")
        
        elif value == "test":
            await self.show_section_select(interaction, "test")
        
        elif value == "task":
            await self.show_section_select(interaction, "task")
        
        elif value == "pass":
            await self.show_section_select(interaction, "pass")
    
    async def show_section_select(self, interaction: Interaction, action: str):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        sections = db.get_all_sections()
        
        if not sections:
            await interaction.response.send_message(
                "❌ Нет разделов! Сначала создайте раздел через 'Добавить раздел'",
                ephemeral=True
            )
            return
        
        options = []
        for section in sections:
            options.append(discord.SelectOption(
                label=section['name'][:100],
                value=str(section['id']),
                description=f"ID: #{section['id']}"
            ))
        
        select = Select(
            placeholder="Выберите раздел...",
            options=options[:25],
            min_values=1,
            max_values=1
        )
        
        async def select_callback(inter: Interaction):
            section_id = int(select.values[0])
            
            if action == "theory":
                from modals.curator_modals import EditTheoryModal
                modal = EditTheoryModal(section_id)
                await inter.response.send_modal(modal)
            
            elif action == "test":
                modal = AddTestModal(section_id)
                await inter.response.send_modal(modal)
            
            elif action == "task":
                modal = AddTaskModal(section_id)
                await inter.response.send_modal(modal)
            
            elif action == "pass":
                from modals.curator_modals import EditPassConditionModal
                modal = EditPassConditionModal(section_id)
                await inter.response.send_modal(modal)
        
        select.callback = select_callback
        
        view = View()
        view.add_item(select)
        view.add_item(Button(
            label="❌ Отмена",
            style=ButtonStyle.danger,
            custom_id="cancel"
        ))
        
        await interaction.response.edit_message(
            content="Выберите раздел:",
            view=view
        )


class TaskManageSelectView(View):
    """Выбор раздела для управления заданиями"""
    
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(TaskManageSelect())
        self.add_item(Button(
            label="❌ Отмена",
            style=ButtonStyle.danger,
            custom_id="cancel"
        ))


class TaskManageSelect(Select):
    """Выбор раздела"""
    
    def __init__(self):
        super().__init__(
            placeholder="Выберите раздел...",
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        section_id = int(self.values[0])
        section = db.get_section(section_id)
        tasks = db.get_tasks_for_section(section_id)
        
        if not tasks:
            embed = Embed(
                title=f"📚 {section['name']}",
                description="Заданий нет. Создайте задание через 'Добавить контент'.",
                color=Color.orange()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return
        
        embed = Embed(
            title=f"📚 {section['name']}",
            description="Список заданий:",
            color=Color.blue()
        )
        
        for task in tasks:
            status_emoji = "🟢" if task['difficulty'] == 1 else "🟡" if task['difficulty'] == 2 else "🔴"
            embed.add_field(
                name=f"{status_emoji} {task['title']}",
                value=(
                    f"ID: #{task['id']}\n"
                    f"Награда: +{task['points_reward']} баллов\n"
                    f"Сложность: {task['difficulty']}/3"
                ),
                inline=True
            )
        
        view = TaskActionView(section_id)
        await interaction.response.edit_message(embed=embed, view=view)


class TaskActionView(View):
    """Действия с заданиями"""
    
    def __init__(self, section_id: int):
        super().__init__(timeout=60)
        self.section_id = section_id
        self.add_item(TaskEditSelect())
        self.add_item(TaskDeleteSelect())
        self.add_item(Button(
            label="🔙 Назад",
            style=ButtonStyle.secondary,
            custom_id="back",
            row=2
        ))


class TaskEditSelect(Select):
    """Выбор задания для редактирования"""
    
    def __init__(self):
        super().__init__(
            placeholder="✏️ Выбрать для редактирования...",
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        task_id = int(self.values[0])
        task = db.get_task(task_id)
        
        if not task:
            await interaction.response.send_message("❌ Задание не найдено!", ephemeral=True)
            return
        
        from modals.curator_modals import EditTaskModal
        modal = EditTaskModal(task_id)
        await interaction.response.send_modal(modal)


class TaskDeleteSelect(Select):
    """Выбор задания для удаления"""
    
    def __init__(self):
        super().__init__(
            placeholder="🗑️ Выбрать для удаления...",
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        task_id = int(self.values[0])
        task = db.get_task(task_id)
        
        if not task:
            await interaction.response.send_message("❌ Задание не найдено!", ephemeral=True)
            return
        
        embed = Embed(
            title="⚠️ Подтверждение удаления",
            description=f"Вы уверены, что хотите удалить задание **{task['title']}**?",
            color=Color.red()
        )
        
        view = ConfirmDeleteTaskView(task_id)
        await interaction.response.edit_message(embed=embed, view=view)


class ConfirmDeleteTaskView(View):
    """Подтверждение удаления задания"""
    
    def __init__(self, task_id: int):
        super().__init__(timeout=30)
        self.task_id = task_id
        
        self.add_item(Button(
            label="✅ Да, удалить",
            style=ButtonStyle.danger,
            custom_id="confirm_delete"
        ))
        self.add_item(Button(
            label="❌ Отмена",
            style=ButtonStyle.secondary,
            custom_id="cancel_delete"
        ))
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.data['custom_id'] == "confirm_delete":
            db = interaction.client.get_db(interaction.guild_id)
            
            if db is None:
                await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
                return False
            
            task = db.get_task(self.task_id)
            db.delete_task(self.task_id)
            db.add_curator_log(
                "🗑️ Удалено задание",
                interaction.user.id,
                f"Задание: {task['title'] if task else 'Неизвестно'}",
                self.task_id
            )
            embed = Embed(
                title="✅ Задание удалено!",
                color=Color.green()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return True
        
        elif interaction.data['custom_id'] == "cancel_delete":
            embed = Embed(
                title="❌ Удаление отменено",
                color=Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=None)
            return True
        
        return True


# ============================================
# ПРОСМОТР ЗАЯВОК (ДЛЯ КУРАТОРОВ) - PlayerSelectView
# ============================================

class PlayerSelectView(View):
    """Выбор игрока из заявок (с кнопками Принять/Отклонить)"""
    
    def __init__(self, applications):
        super().__init__(timeout=60)
        self.applications = applications
        
        options = []
        for app in applications[:25]:
            options.append(discord.SelectOption(
                label=f"Заявка #{app['id']}",
                value=str(app['id']),
                description=f"User ID: {app['user_id']}"
            ))
        
        select = Select(
            placeholder="Выберите заявку...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        async def select_callback(inter: Interaction):
            app_id = int(select.values[0])
            
            app = None
            for a in self.applications:
                if a['id'] == app_id:
                    app = a
                    break
            
            if not app:
                await inter.response.send_message("❌ Заявка не найдена!", ephemeral=True)
                return
            
            db = inter.client.get_db(inter.guild_id)
            
            if db is None:
                await inter.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
                return
            
            user = inter.guild.get_member(app['user_id'])
            char = db.get_character_by_id(app['character_id'])
            
            embed = Embed(
                title=f"📋 Заявка #{app['id']}",
                color=Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="👤 Кандидат", value=user.mention if user else f"ID: {app['user_id']}", inline=True)
            embed.add_field(name="⚔️ Персонаж", value=char['character_name'] if char else "Неизвестно", inline=True)
            embed.add_field(name="📅 Подана", value=app['applied_at'][:16] if app['applied_at'] else "Неизвестно", inline=True)
            embed.add_field(name="📝 Опыт", value=app['experience'][:500] or "Не указан", inline=False)
            embed.add_field(name="💪 Мотивация", value=app['motivation'][:500] or "Не указана", inline=False)
            
            existing = db.get_trainee_by_user(app['user_id'])
            if existing:
                embed.add_field(
                    name="⚠️ Статус",
                    value="Этот игрок уже добавлен в систему!",
                    inline=False
                )
                await inter.response.send_message(embed=embed, ephemeral=True)
                return
            
            view = ApplicationActionView(app, user, char)
            await inter.response.edit_message(embed=embed, view=view)
        
        select.callback = select_callback
        
        self.add_item(select)
        self.add_item(Button(
            label="❌ Отмена",
            style=ButtonStyle.danger,
            custom_id="cancel"
        ))


class ApplicationActionView(View):
    """Кнопки для действий с заявкой"""
    
    def __init__(self, app, user, char):
        super().__init__(timeout=120)
        self.app = app
        self.user = user
        self.char = char
    
    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_button(self, interaction: Interaction, button: discord.ui.Button):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        guild = interaction.guild
        
        if not await self.can_review(interaction.user, db):
            await interaction.response.send_message("❌ У вас нет прав!", ephemeral=True)
            return
        
        # Обновляем статус заявки
        db.review_application(
            app_id=self.app['id'],
            status='accepted',
            reviewer_id=interaction.user.id,
            comment="Принята куратором"
        )
        
        # Создаём запись в trainees
        db.cursor.execute('''
            INSERT INTO trainees (
                user_id, 
                main_character_id, 
                status, 
                experience, 
                motivation,
                applied_at
            ) VALUES (?, ?, 'active', ?, ?, CURRENT_TIMESTAMP)
        ''', (
            self.app['user_id'],
            self.app['character_id'],
            self.app.get('experience', ''),
            self.app.get('motivation', '')
        ))
        db.conn.commit()
        
        # Выдаём роль курсанта
        member = guild.get_member(self.app['user_id'])
        if member:
            from utils.trainee_utils import assign_trainee_role
            await assign_trainee_role(member, db)
        
        db.add_curator_log(
            "✅ Заявка принята",
            interaction.user.id,
            f"Кандидат: <@{self.app['user_id']}>",
            self.app['user_id']
        )
        
        # Уведомляем кандидата
        if member:
            embed = Embed(
                title="✅ Заявка принята!",
                description=(
                    f"Куратор {interaction.user.mention} принял вашу заявку!\n\n"
                    f"Вам выдана роль **Курсант**.\n"
                    f"Ожидайте заданий от куратора."
                ),
                color=Color.green()
            )
            await member.send(embed=embed)
        
        # Обновляем embed через response.edit_message (ИСПРАВЛЕНО)
        embed = interaction.message.embeds[0]
        embed.color = Color.green()
        embed.add_field(name="✅ Статус", value="✅ ПРИНЯТА", inline=False)
        embed.add_field(name="👨‍🏫 Принял", value=interaction.user.mention, inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject_button(self, interaction: Interaction, button: discord.ui.Button):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        if not await self.can_review(interaction.user, db):
            await interaction.response.send_message("❌ У вас нет прав!", ephemeral=True)
            return
        
        modal = RejectApplicationModal(self.app['id'], self.app['user_id'])
        await interaction.response.send_modal(modal)
    
    async def can_review(self, user: discord.Member, db) -> bool:
        """Проверка прав для рассмотрения заявки"""
        if db.get_setting('developer_id', '') == str(user.id):
            return True
        if utils.is_guild_master(user, db):
            return True
        from utils.curator_utils import is_curator
        if is_curator(user, db):
            return True
        return False


class RejectApplicationModal(Modal, title="❌ Причина отклонения"):
    """Модалка для отклонения заявки"""
    
    def __init__(self, app_id: int, user_id: int):
        super().__init__()
        self.app_id = app_id
        self.user_id = user_id
    
    reason = TextInput(
        label="Причина отклонения",
        placeholder="Укажите причину...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )
    
    async def on_submit(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        guild = interaction.guild
        
        # Обновляем статус заявки
        db.review_application(
            app_id=self.app_id,
            status='rejected',
            reviewer_id=interaction.user.id,
            comment=self.reason.value
        )
        
        db.add_curator_log(
            "❌ Заявка отклонена",
            interaction.user.id,
            f"Кандидат: <@{self.user_id}>, Причина: {self.reason.value[:50]}",
            self.user_id
        )
        
        # Уведомляем кандидата
        member = guild.get_member(self.user_id)
        if member:
            embed = Embed(
                title="❌ Заявка отклонена",
                description=(
                    f"Ваша заявка на обучение РЛ отклонена.\n\n"
                    f"**Причина:** {self.reason.value}\n\n"
                    f"Вы можете подать повторную заявку через 7 дней."
                ),
                color=Color.red()
            )
            await member.send(embed=embed)
        
        # Обновляем embed через response.edit_message (ИСПРАВЛЕНО)
        embed = interaction.message.embeds[0]
        embed.color = Color.red()
        embed.add_field(name="❌ Статус", value="❌ ОТКЛОНЕНА", inline=False)
        embed.add_field(name="📝 Причина", value=self.reason.value, inline=False)
        embed.add_field(name="👮 Отклонил", value=interaction.user.mention, inline=True)
        
        await interaction.response.edit_message(embed=embed, view=None)


class TaskSelectView(View):
    """Выбор задания для просмотра и подтверждения (куратор)"""
    
    def __init__(self, tasks: list):
        super().__init__(timeout=120)
        self.tasks = tasks
        
        options = []
        # Используем переданные задачи, а не db (который еще не определен)
        for task in tasks[:25]:
            trainee_name = f"Кандидат: {task.get('trainee_user_id', '')}"
            
            options.append(discord.SelectOption(
                label=f"{task.get('title', 'Без названия')[:35]}",
                value=str(task.get('id')),
                description=f"{trainee_name[:30]} | +{task.get('points_reward', 0)} баллов"
            ))
        
        if options:
            select = Select(
                placeholder="Выберите задание для просмотра...",
                options=options,
                min_values=1,
                max_values=1
            )
            
            async def select_callback(inter: Interaction):
                task_id = int(select.values[0])
                await self.show_task_details(inter, task_id)
            
            select.callback = select_callback
            self.add_item(select)
        
        self.add_item(Button(
            label="❌ Закрыть",
            style=ButtonStyle.danger,
            custom_id="close_task_view"
        ))
    
    async def show_task_details(self, interaction: Interaction, task_id: int):
        """Показать детали задания"""
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        task = db.get_trainee_task(task_id)
        if not task:
            await interaction.response.send_message("❌ Задание не найдено!", ephemeral=True)
            return
        
        trainee = interaction.guild.get_member(task.get('trainee_user_id'))
        mentor = interaction.guild.get_member(task.get('mentor_id'))
        
        embed = Embed(
            title=f"📝 Задание #{task_id}",
            color=Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(name="📋 Название", value=task.get('title', 'Без названия'), inline=False)
        embed.add_field(name="📝 Описание", value=task.get('description', 'Нет описания')[:500], inline=False)
        embed.add_field(name="👤 Кандидат", value=trainee.mention if trainee else f"ID: {task.get('trainee_user_id')}", inline=True)
        embed.add_field(name="👨‍🏫 Ментор", value=mentor.mention if mentor else f"ID: {task.get('mentor_id')}", inline=True)
        embed.add_field(name="⭐ Сложность", value=f"{task.get('difficulty', 1)}/3", inline=True)
        embed.add_field(name="💰 Награда", value=f"+{task.get('points_reward', 0)} баллов", inline=True)
        embed.add_field(name="📊 Статус", value=task.get('status', 'pending'), inline=True)
        
        # Показываем все задания кандидата
        trainee_tasks = db.cursor.execute('''
            SELECT id, title, status, points_reward, created_at
            FROM trainee_tasks 
            WHERE trainee_id = ?
            ORDER BY created_at DESC
        ''', (task.get('trainee_id'),)).fetchall()
        
        if trainee_tasks:
            tasks_text = ""
            for t in trainee_tasks[:5]:
                status_emoji = "✅" if t[2] == 'approved' else "⏳" if t[2] == 'pending' else "❌" if t[2] == 'rejected' else "📤" if t[2] == 'completed' else "❓"
                tasks_text += f"{status_emoji} **{t[1]}** (+{t[3]} баллов)\n"
            embed.add_field(
                name="📋 Все задания кандидата",
                value=tasks_text,
                inline=False
            )
        
        report = db.get_report_for_task(task_id)
        if report:
            embed.add_field(
                name="📤 Ответ кандидата",
                value=report.get('answer', 'Нет ответа')[:500],
                inline=False
            )
            embed.add_field(
                name="📅 Сдано",
                value=report.get('submitted_at', '')[:16] if report.get('submitted_at') else 'Неизвестно',
                inline=True
            )
        
        view = TaskActionView2(task_id, task.get('trainee_user_id'), task.get('points_reward', 0))
        await interaction.response.edit_message(embed=embed, view=view)


class TaskActionView2(View):
    """Кнопки действий с заданием"""
    
    def __init__(self, task_id: int, trainee_user_id: int, points_reward: int):
        super().__init__(timeout=120)
        self.task_id = task_id
        self.trainee_user_id = trainee_user_id
        self.points_reward = points_reward
        
        self.add_item(ApproveTaskButton(task_id, trainee_user_id, points_reward))
        self.add_item(RejectTaskButton(task_id, trainee_user_id))
        self.add_item(BackToTasksButton())


class ApproveTaskButton(Button):
    """Кнопка подтверждения выполнения задания"""
    
    def __init__(self, task_id: int, trainee_user_id: int, points_reward: int):
        super().__init__(
            label="✅ Подтвердить выполнение",
            style=ButtonStyle.success,
            emoji="✅",
            row=0
        )
        self.task_id = task_id
        self.trainee_user_id = trainee_user_id
        self.points_reward = points_reward
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        guild = interaction.guild
        
        task = db.get_trainee_task(self.task_id)
        if not task:
            await interaction.response.send_message("❌ Задание не найдено!", ephemeral=True)
            return
        
        report = db.get_report_for_task(self.task_id)
        if not report:
            await interaction.response.send_message("❌ Кандидат ещё не сдал задание!", ephemeral=True)
            return
        
        db.cursor.execute('''
            UPDATE trainee_tasks 
            SET status = 'approved', approved_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (self.task_id,))
        db.conn.commit()
        
        db.cursor.execute('''
            UPDATE trainees 
            SET points = points + ?, last_activity = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (self.points_reward, self.trainee_user_id))
        db.conn.commit()
        
        db.add_curator_log(
            "✅ Подтверждено выполнение задания",
            interaction.user.id,
            f"Задание #{self.task_id}, баллов: +{self.points_reward}",
            self.trainee_user_id
        )
        
        candidate = guild.get_member(self.trainee_user_id)
        if candidate:
            embed = Embed(
                title="✅ Задание выполнено!",
                description=f"Ваше задание **{task.get('title', '')}** принято!",
                color=Color.green()
            )
            embed.add_field(name="💰 Баллы", value=f"+{self.points_reward}", inline=True)
            embed.add_field(name="👨‍🏫 Проверил", value=interaction.user.mention, inline=True)
            await candidate.send(embed=embed)
        
        embed = Embed(
            title="✅ Задание подтверждено!",
            description=f"**Задание:** {task.get('title', '')}\n"
                       f"**Кандидат:** {candidate.mention if candidate else 'Не найден'}\n"
                       f"**Баллы:** +{self.points_reward}",
            color=Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class RejectTaskButton(Button):
    """Кнопка отклонения задания"""
    
    def __init__(self, task_id: int, trainee_user_id: int):
        super().__init__(
            label="❌ Отклонить",
            style=ButtonStyle.danger,
            emoji="❌",
            row=0
        )
        self.task_id = task_id
        self.trainee_user_id = trainee_user_id
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        from modals.curator_modals import TaskRejectModal
        
        # Проверяем права
        if not can_manage_curator_panel(interaction.user, db):
            await interaction.response.send_message("❌ У вас нет прав куратора!", ephemeral=True)
            return
        
        modal = TaskRejectModal(self.task_id, self.trainee_user_id)
        await interaction.response.send_modal(modal)


class BackToTasksButton(Button):
    """Кнопка возврата к списку заданий"""
    
    def __init__(self):
        super().__init__(
            label="🔙 Назад к списку",
            style=ButtonStyle.secondary,
            emoji="🔙",
            row=1
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        tasks = db.get_pending_tasks_for_curator(interaction.user.id)
        
        if not tasks:
            await interaction.response.send_message("📭 Нет активных заданий.", ephemeral=True)
            return
        
        embed = Embed(
            title="👀 Задания на проверку",
            description=f"Всего заданий: {len(tasks)}",
            color=Color.blue(),
            timestamp=datetime.now()
        )
        
        for task in tasks[:10]:
            trainee = interaction.guild.get_member(task.get('trainee_user_id'))
            trainee_name = trainee.mention if trainee else f"ID: {task.get('trainee_user_id')}"
            
            embed.add_field(
                name=f"📝 {task.get('title', 'Без названия')[:50]}",
                value=(
                    f"👤 **Кандидат:** {trainee_name}\n"
                    f"💰 **Награда:** +{task.get('points_reward', 0)} баллов"
                ),
                inline=False
            )
        
        view = TaskSelectView(tasks)
        await interaction.response.edit_message(embed=embed, view=view)


# ============================================
# VIEW ДЛЯ ЗАДАНИЯ (У КАНДИДАТА)
# ============================================

class TraineeTaskView(View):
    """Кнопки для задания у кандидата"""
    
    def __init__(self, task_id: int, trainee_id: int):
        super().__init__(timeout=None)
        self.task_id = task_id
        self.trainee_id = trainee_id
    
    @discord.ui.button(label="✅ Выполнил", style=ButtonStyle.success, emoji="✅")
    async def complete_button(self, interaction: Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        trainee = db.get_trainee_by_id(self.trainee_id)
        if not trainee or trainee['user_id'] != interaction.user.id:
            await interaction.response.send_message("❌ Это не ваше задание!", ephemeral=True)
            return
        
        task = db.get_trainee_task(self.task_id)
        if not task:
            await interaction.response.send_message("❌ Задание не найдено!", ephemeral=True)
            return
        
        if task['status'] != 'pending':
            await interaction.response.send_message("❌ Задание уже выполнено или просрочено!", ephemeral=True)
            return
        
        existing_report = db.cursor.execute('''
            SELECT id FROM trainee_reports WHERE task_id = ?
        ''', (self.task_id,)).fetchone()
        
        if existing_report:
            await interaction.response.send_message(
                "❌ Вы уже сдавали это задание!\n"
                "Ожидайте проверки куратора.",
                ephemeral=True
            )
            return
        
        from modals.curator_modals import TaskReportModal
        modal = TaskReportModal(self.task_id)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="📋 Посмотреть задание", style=ButtonStyle.secondary, emoji="📋")
    async def view_task_button(self, interaction: Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        task = db.get_trainee_task(self.task_id)
        if not task:
            await interaction.response.send_message("❌ Задание не найдено!", ephemeral=True)
            return
        
        embed = Embed(
            title=f"📝 Задание: {task['title']}",
            description=task['description'] or 'Нет описания',
            color=Color.blue()
        )
        embed.add_field(name="💰 Награда", value=f"+{task['points_reward']} баллов", inline=True)
        embed.add_field(name="⭐ Сложность", value=f"{task['difficulty']}/3", inline=True)
        embed.add_field(name="📊 Статус", value=task['status'], inline=True)
        
        if task['deadline']:
            embed.add_field(name="⏰ Срок", value=task['deadline'][:16], inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================
# КНОПКА ДЛЯ УЧЕНИКА В КАНАЛЕ (СДАТЬ ЗАДАНИЕ)
# ============================================

class StudentTaskButton(Button):
    """Кнопка для ученика в канале (с уникальным custom_id)"""
    
    def __init__(self, trainee_id: int, user_id: int, username: str):
        super().__init__(
            label=f"📤 {username}",
            style=ButtonStyle.success,
            emoji="📤",
            custom_id=f"student_task_{trainee_id}_{user_id}"  # Добавляем user_id для уникальности
        )
        self.trainee_id = trainee_id
        self.user_id = user_id
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        # Получаем trainee_id из custom_id
        parts = self.custom_id.split('_')
        if len(parts) >= 3:
            trainee_id = int(parts[2])
        else:
            trainee_id = self.trainee_id
        
        # Проверяем, что это тот же пользователь
        trainee = db.get_trainee_by_id(trainee_id)
        if not trainee:
            await interaction.response.send_message("❌ Вы не являетесь учеником!", ephemeral=True)
            return
        
        if trainee['user_id'] != interaction.user.id:
            await interaction.response.send_message("❌ Это не ваша кнопка!", ephemeral=True)
            return
        
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
        
        embed = Embed(
            title="📋 Ваши задания",
            description="Выберите задание для сдачи:",
            color=Color.blue()
        )
        
        options = []
        for task in tasks[:25]:
            options.append(discord.SelectOption(
                label=task[1][:50] if task[1] else 'Без названия',
                value=str(task[0]),
                description=f"+{task[2]} баллов"
            ))
        
        select = Select(
            placeholder="Выберите задание...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        async def select_callback(inter: Interaction):
            task_id = int(select.values[0])
            from modals.curator_modals import TaskReportModal
            modal = TaskReportModal(task_id)
            await inter.response.send_modal(modal)
        
        select.callback = select_callback
        
        view = View()
        view.add_item(select)
        view.add_item(Button(
            label="❌ Отмена",
            style=ButtonStyle.danger,
            custom_id="cancel"
        ))
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ============================================
# ВОССТАНОВЛЕНИЕ КАНАЛА УЧЕНИКОВ-КУРСАНТОВ
# ============================================

async def restore_students_channel(guild: discord.Guild, db):
    """Восстанавливает канал учеников-курсантов после рестарта"""
    
    from utils.curator_utils import create_students_overview_embed, refresh_students_channel
    
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
                
                view = View(timeout=None)  # timeout=None для постоянных кнопок
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


# ============================================
# НЕПЕРСИСТЕНТНЫЕ КНОПКИ (ДЛЯ /curator)
# ============================================

class AddContentButton(Button):
    """Кнопка: Добавить контент (неперсистентная)"""
    
    def __init__(self):
        super().__init__(
            label="📚 Добавить контент",
            style=ButtonStyle.primary,
            emoji="📚",
            row=0
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        embed = Embed(
            title="📚 Что хотите добавить?",
            description="Выберите тип контента:",
            color=Color.blue()
        )
        
        embed.add_field(
            name="1️⃣ Раздел (инст)",
            value="Создать новый раздел для обучения",
            inline=False
        )
        embed.add_field(
            name="2️⃣ Теория",
            value="Добавить теорию к существующему разделу",
            inline=False
        )
        embed.add_field(
            name="3️⃣ Тест (опрос)",
            value="Добавить тест к разделу",
            inline=False
        )
        embed.add_field(
            name="4️⃣ Задание",
            value="Добавить задание к разделу",
            inline=False
        )
        embed.add_field(
            name="5️⃣ Зачет",
            value="Настроить условия зачета",
            inline=False
        )
        
        view = ContentTypeSelectView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ManageTasksButton(Button):
    """Кнопка: Управление заданиями (неперсистентная)"""
    
    def __init__(self):
        super().__init__(
            label="✏️ Управление заданиями",
            style=ButtonStyle.primary,
            emoji="✏️",
            row=0
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        sections = db.get_all_sections()
        
        if not sections:
            await interaction.response.send_message(
                "❌ Нет разделов! Сначала создайте раздел.",
                ephemeral=True
            )
            return
        
        embed = Embed(
            title="✏️ Управление заданиями",
            description="Выберите раздел, чтобы управлять заданиями:",
            color=Color.blue()
        )
        
        for section in sections:
            tasks = db.get_tasks_for_section(section['id'])
            task_count = len(tasks)
            embed.add_field(
                name=f"📚 {section['name']}",
                value=f"Заданий: {task_count}",
                inline=True
            )
        
        view = TaskManageSelectView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AddPlayerButton(Button):
    """Кнопка: Добавить игрока (неперсистентная)"""
    
    def __init__(self):
        super().__init__(
            label="👤 Добавить игрока",
            style=ButtonStyle.success,
            emoji="👤",
            row=1
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        applications = db.get_pending_applications()
        
        if not applications:
            await interaction.response.send_message(
                "📭 Нет заявок на рассмотрение.",
                ephemeral=True
            )
            return
        
        embed = Embed(
            title="👤 Заявки на обучение",
            description=f"Всего заявок: {len(applications)}",
            color=Color.blue()
        )
        
        for app in applications[:5]:
            user = interaction.guild.get_member(app['user_id'])
            char = db.get_character_by_id(app['character_id'])
            char_name = char['character_name'] if char else "Неизвестно"
            
            embed.add_field(
                name=f"📋 Заявка #{app['id']}",
                value=(
                    f"**Игрок:** {user.mention if user else 'Не найден'}\n"
                    f"**Персонаж:** {char_name}"
                ),
                inline=False
            )
        
        view = PlayerSelectView(applications)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class AssignTaskButton(Button):
    """Кнопка: Выдать задание (неперсистентная)"""
    
    def __init__(self):
        super().__init__(
            label="📤 Выдать задание",
            style=ButtonStyle.success,
            emoji="📤",
            row=1
        )
    
    async def callback(self, interaction: Interaction):
        # Используем ту же логику что и в персистентной версии
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        try:
            candidates = db.cursor.execute('''
                SELECT id, user_id, level, points, status 
                FROM trainees 
                WHERE status = 'active'
                ORDER BY points DESC
            ''').fetchall()
        except:
            candidates = []
        
        if not candidates:
            await interaction.response.send_message(
                "❌ Нет активных кандидатов!",
                ephemeral=True
            )
            return
        
        options = []
        for candidate in candidates[:25]:
            user = interaction.guild.get_member(candidate[1])
            if user:
                task_count = db.cursor.execute('''
                    SELECT COUNT(*) FROM trainee_tasks 
                    WHERE trainee_id = ? AND status IN ('pending', 'completed')
                ''', (candidate[0],)).fetchone()[0]
                
                options.append(discord.SelectOption(
                    label=f"{user.display_name[:50]}",
                    value=str(candidate[0]),
                    description=f"Уровень: {candidate[2]}, Заданий: {task_count}"
                ))
        
        if not options:
            await interaction.response.send_message(
                "❌ Нет доступных кандидатов!",
                ephemeral=True
            )
            return
        
        # Создаем временный view для выбора кандидата
        view = View()
        select = Select(
            placeholder="Выберите кандидата...",
            options=options,
            min_values=1,
            max_values=1
        )
        
        async def select_callback(inter: Interaction):
            trainee_id = int(select.values[0])
            # Используем метод из персистентной кнопки
            temp_button = AssignTaskButtonPersistent()
            await temp_button.show_task_selection(inter, trainee_id)
        
        select.callback = select_callback
        view.add_item(select)
        view.add_item(Button(
            label="❌ Отмена",
            style=ButtonStyle.danger,
            custom_id="cancel"
        ))
        
        await interaction.response.send_message(
            "Выберите кандидата для выдачи задания:",
            view=view,
            ephemeral=True
        )


class ViewRatingButton(Button):
    """Кнопка: Просмотреть рейтинг (неперсистентная)"""
    
    def __init__(self):
        super().__init__(
            label="📊 Просмотреть рейтинг",
            style=ButtonStyle.primary,
            emoji="📊",
            row=1
        )
    
    async def callback(self, interaction: Interaction):
        # Используем ту же логику что и в персистентной версии
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        try:
            rating = db.cursor.execute('''
                SELECT user_id, level, points, status
                FROM trainees
                WHERE status IN ('active', 'graduated')
                ORDER BY points DESC
            ''').fetchall()
        except:
            rating = []
        
        if not rating:
            await interaction.response.send_message(
                "📊 Нет данных для рейтинга.",
                ephemeral=True
            )
            return
        
        embed = Embed(
            title="📊 Рейтинг учеников",
            color=Color.gold(),
            timestamp=datetime.now()
        )
        
        for i, student in enumerate(rating[:10], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            user = interaction.guild.get_member(student[0])
            
            embed.add_field(
                name=f"{medal} {user.display_name if user else 'Неизвестно'}",
                value=(
                    f"⭐ Баллы: **{student[2]}**\n"
                    f"📊 Уровень: {student[1]}/5"
                ),
                inline=True
            )
        
        if len(rating) > 10:
            embed.set_footer(text=f"Показано 10 из {len(rating)}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


class ViewTaskButton(Button):
    """Кнопка: Просмотреть задание (неперсистентная)"""
    
    def __init__(self):
        super().__init__(
            label="👀 Просмотреть задание",
            style=ButtonStyle.primary,
            emoji="👀",
            row=1
        )
    
    async def callback(self, interaction: Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        tasks = db.get_pending_tasks_for_curator(interaction.user.id)
        
        if not tasks:
            await interaction.response.send_message(
                "📭 Нет заданий на проверку.",
                ephemeral=True
            )
            return
        
        embed = Embed(
            title="👀 Задания на проверку",
            description=f"Всего заданий: {len(tasks)}",
            color=Color.blue(),
            timestamp=datetime.now()
        )
        
        for task in tasks[:10]:
            trainee = interaction.guild.get_member(task.get('trainee_user_id'))
            trainee_name = trainee.mention if trainee else f"ID: {task.get('trainee_user_id')}"
            
            embed.add_field(
                name=f"📝 {task.get('title', 'Без названия')[:50]}",
                value=(
                    f"👤 **Кандидат:** {trainee_name}\n"
                    f"💰 **Награда:** +{task.get('points_reward', 0)} баллов"
                ),
                inline=False
            )
        
        view = TaskSelectView(tasks)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)