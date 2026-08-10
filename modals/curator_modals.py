# modals/curator_modals.py — ПОЛНЫЙ ФАЙЛ

import discord
from discord.ui import Modal, TextInput, Select
from discord import Interaction, Embed, Color
from datetime import datetime, timedelta
import utils
from utils.curator_utils import get_points_for_task


# ============================================
# ДОБАВЛЕНИЕ РАЗДЕЛА
# ============================================

class AddSectionModal(Modal, title="📚 Добавить раздел"):
    
    name = TextInput(
        label="Название раздела",
        placeholder="Например: Толгародская тюрьма 10 об",
        required=True,
        max_length=200
    )
    
    theory_link = TextInput(
        label="Ссылка на теорию",
        placeholder="https://...",
        required=False,
        max_length=500
    )
    
    pass_condition = TextInput(
        label="Условие зачета",
        placeholder="Например: iLvl 200+, знание всех боссов",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: Interaction):
        db = interaction.client.db
        
        section_id = db.create_section(
            name=self.name.value,
            theory_link=self.theory_link.value,
            pass_condition=self.pass_condition.value
        )
        
        db.add_curator_log(
            "📚 Добавлен раздел",
            interaction.user.id,
            f"Название: {self.name.value}",
            section_id
        )
        
        embed = Embed(
            title="✅ Раздел создан!",
            description=(
                f"**Название:** {self.name.value}\n"
                f"**Теория:** {self.theory_link.value or 'Не указана'}\n"
                f"**Условие зачета:** {self.pass_condition.value or 'Не указано'}\n"
                f"**ID:** #{section_id}"
            ),
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================
# ДОБАВЛЕНИЕ ТЕСТА
# ============================================

class AddTestModal(Modal, title="📋 Добавить тест"):
    
    def __init__(self, section_id: int):
        super().__init__()
        self.section_id = section_id
    
    question = TextInput(
        label="Текст вопроса",
        placeholder="Введите вопрос...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )
    
    max_score = TextInput(
        label="Максимальный балл",
        placeholder="Например: 10",
        required=True,
        max_length=10
    )
    
    async def on_submit(self, interaction: Interaction):
        db = interaction.client.db
        
        try:
            max_score = int(self.max_score.value)
            if max_score < 1 or max_score > 100:
                await interaction.response.send_message("❌ Максимальный балл должен быть от 1 до 100!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите число!", ephemeral=True)
            return
        
        test_id = db.create_test(
            section_id=self.section_id,
            question_text=self.question.value,
            max_score=max_score
        )
        
        section = db.get_section(self.section_id)
        
        db.add_curator_log(
            "📋 Добавлен тест",
            interaction.user.id,
            f"Раздел: {section['name'] if section else 'Неизвестно'}, Вопрос: {self.question.value[:50]}",
            test_id
        )
        
        embed = Embed(
            title="✅ Тест добавлен!",
            description=(
                f"**Раздел:** {section['name'] if section else 'Неизвестно'}\n"
                f"**Вопрос:** {self.question.value}\n"
                f"**Макс. балл:** {max_score}\n"
                f"**ID:** #{test_id}"
            ),
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================
# ДОБАВЛЕНИЕ ЗАДАНИЯ
# ============================================

class AddTaskModal(Modal, title="📝 Добавить задание"):
    
    def __init__(self, section_id: int):
        super().__init__()
        self.section_id = section_id
    
    title = TextInput(
        label="Название задания",
        placeholder="Например: Написать тактику на первого босса",
        required=True,
        max_length=200
    )
    
    description = TextInput(
        label="Описание задания",
        placeholder="Опишите задание...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=2000
    )
    
    difficulty = TextInput(
        label="Сложность (1-3)",
        placeholder="1 - Легкое, 2 - Среднее, 3 - Сложное",
        required=True,
        max_length=10
    )
    
    points_reward = TextInput(
        label="Награда (баллы)",
        placeholder="Например: 25",
        required=True,
        max_length=10
    )
    
    async def on_submit(self, interaction: Interaction):
        db = interaction.client.db
        
        try:
            difficulty = int(self.difficulty.value)
            if difficulty not in [1, 2, 3]:
                await interaction.response.send_message("❌ Сложность должна быть 1, 2 или 3!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите число!", ephemeral=True)
            return
        
        try:
            points = int(self.points_reward.value)
            if points < 1 or points > 100:
                await interaction.response.send_message("❌ Награда должна быть от 1 до 100!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите число!", ephemeral=True)
            return
        
        task_id = db.create_task(
            section_id=self.section_id,
            title=self.title.value,
            description=self.description.value,
            difficulty=difficulty,
            points_reward=points
        )
        
        section = db.get_section(self.section_id)
        
        db.add_curator_log(
            "📝 Добавлено задание",
            interaction.user.id,
            f"Раздел: {section['name'] if section else 'Неизвестно'}, Задание: {self.title.value}",
            task_id
        )
        
        embed = Embed(
            title="✅ Задание добавлено!",
            description=(
                f"**Раздел:** {section['name'] if section else 'Неизвестно'}\n"
                f"**Название:** {self.title.value}\n"
                f"**Сложность:** {difficulty}\n"
                f"**Награда:** +{points} баллов\n"
                f"**ID:** #{task_id}"
            ),
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ============================================
# ВЫДАЧА ЗАДАНИЯ КАНДИДАТУ (AssignTaskModal)
# ============================================

class AssignTaskModal(Modal, title="📤 Выдать задание кандидату"):
    
    def __init__(self, trainee_id: int, task_id: int = None):
        super().__init__()
        self.trainee_id = trainee_id
        self.task_id = task_id
    
    comment = TextInput(
        label="Комментарий (опционально)",
        placeholder="Дополнительные инструкции...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )
    
    async def on_submit(self, interaction: Interaction):
        db = interaction.client.db
        
        if not self.task_id:
            await interaction.response.send_message(
                "❌ Сначала выберите задание!",
                ephemeral=True
            )
            return
        
        trainee = db.get_trainee_by_id(self.trainee_id)
        if not trainee:
            await interaction.response.send_message(
                "❌ Кандидат не найден!",
                ephemeral=True
            )
            return
        
        task = db.get_task(self.task_id)
        if not task:
            await interaction.response.send_message(
                "❌ Задание не найдено!",
                ephemeral=True
            )
            return
        
        # Создаём выполнение задания для кандидата
        db.cursor.execute('''
            INSERT INTO trainee_tasks (
                trainee_id, 
                mentor_id, 
                title, 
                description, 
                difficulty, 
                points_reward,
                status,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
        ''', (
            self.trainee_id,
            interaction.user.id,
            task['title'],
            task['description'],
            task['difficulty'],
            task['points_reward']
        ))
        db.conn.commit()
        task_db_id = db.cursor.lastrowid
        
        db.add_curator_log(
            "📤 Выдано задание",
            interaction.user.id,
            f"Кандидату: <@{trainee['user_id']}>, Задание: {task['title']}",
            self.task_id
        )
        
        candidate = interaction.guild.get_member(trainee['user_id'])
        if candidate:
            embed = Embed(
                title="📝 Новое задание!",
                description=f"Вам выдал задание: {interaction.user.mention}",
                color=Color.blue()
            )
            embed.add_field(name="📋 Название", value=task['title'], inline=False)
            embed.add_field(name="📝 Описание", value=task['description'][:500] if task['description'] else 'Нет описания', inline=False)
            embed.add_field(name="💰 Награда", value=f"+{task['points_reward']} баллов", inline=True)
            
            if self.comment.value:
                embed.add_field(name="💬 Комментарий", value=self.comment.value, inline=False)
            
            from views.curator import TraineeTaskView
            view = TraineeTaskView(task_db_id, self.trainee_id)
            await candidate.send(embed=embed, view=view)
        
        await interaction.response.send_message(
            f"✅ Задание выдано!\n"
            f"**Кандидат:** {candidate.mention if candidate else 'Не найден'}\n"
            f"**Задание:** {task['title']}",
            ephemeral=True
        )


# ============================================
# ОТВЕТ НА ЗАДАНИЕ (ДЛЯ КАНДИДАТА)
# ============================================

class TaskReportModal(Modal, title="📝 Отчет по заданию"):
    
    def __init__(self, task_id: int):
        super().__init__()
        self.task_id = task_id
    
    answer = TextInput(
        label="Ваш ответ",
        placeholder="Напишите подробный ответ...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=4000
    )
    
    async def on_submit(self, interaction: Interaction):
        db = interaction.client.db
        
        task = db.get_trainee_task(self.task_id)
        if not task:
            await interaction.response.send_message("❌ Задание не найдено!", ephemeral=True)
            return
        
        trainee = db.get_trainee_by_user(interaction.user.id)
        if not trainee:
            await interaction.response.send_message("❌ Вы не являетесь кандидатом!", ephemeral=True)
            return
        
        report_id = db.create_trainee_report(
            task_id=self.task_id,
            trainee_id=trainee['id'],
            answer=self.answer.value
        )
        
        mentor = interaction.guild.get_member(task['mentor_id'])
        if mentor:
            embed = Embed(
                title="📋 Новый отчет!",
                description=f"**Кандидат:** {interaction.user.mention}\n"
                           f"**Задание:** {task['title']}",
                color=Color.gold()
            )
            embed.add_field(name="📝 Ответ", value=self.answer.value[:500], inline=False)
            embed.set_footer(text=f"ID задания: {self.task_id}")
            
            # Отправляем ментору
            await mentor.send(embed=embed)
        
        db.add_trainee_log(
            trainee['id'],
            f"📋 Отправлен отчет по заданию: {task['title']}",
            interaction.user.id
        )
        
        await interaction.response.send_message(
            f"✅ Отчет отправлен!\n"
            f"**Задание:** {task['title']}\n"
            f"Ожидайте проверки куратора.",
            ephemeral=True
        )


# ============================================
# ОТКЛОНЕНИЕ ЗАДАНИЯ (ДЛЯ МЕНТОРА)
# ============================================

class TaskRejectModal(Modal, title="❌ Отклонить задание"):
    
    def __init__(self, task_id: int, trainee_user_id: int):
        super().__init__()
        self.task_id = task_id
        self.trainee_user_id = trainee_user_id
    
    reason = TextInput(
        label="Причина отклонения",
        placeholder="Укажите причину...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )
    
    async def on_submit(self, interaction: Interaction):
        db = interaction.client.db
        guild = interaction.guild
        
        task = db.get_trainee_task(self.task_id)
        if not task:
            await interaction.response.send_message("❌ Задание не найдено!", ephemeral=True)
            return
        
        db.cursor.execute('''
            UPDATE trainee_tasks 
            SET status = 'rejected', mentor_comment = ?
            WHERE id = ?
        ''', (self.reason.value, self.task_id))
        db.conn.commit()
        
        db.add_trainee_log(
            task['trainee_id'],
            f"❌ Задание отклонено: {task['title']}",
            interaction.user.id
        )
        
        candidate = guild.get_member(self.trainee_user_id)
        if candidate:
            embed = Embed(
                title="❌ Задание отклонено",
                description=f"Ваше задание **{task['title']}** отклонено.",
                color=Color.red()
            )
            embed.add_field(name="📝 Причина", value=self.reason.value, inline=False)
            await candidate.send(embed=embed)
        
        embed = Embed(
            title="❌ Задание отклонено",
            description=f"**Задание:** {task['title']}\n"
                       f"**Причина:** {self.reason.value}",
            color=Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=None)


# ============================================
# РЕДАКТИРОВАНИЕ ТЕОРИИ
# ============================================

class EditTheoryModal(Modal, title="📝 Редактировать теорию"):
    
    def __init__(self, section_id: int):
        super().__init__()
        self.section_id = section_id
        
        db = interaction.client.db
        section = db.get_section(section_id)
        current_theory = section['theory_link'] if section else ''
        
        self.theory = TextInput(
            label="Ссылка на теорию",
            placeholder="https://...",
            default=current_theory,
            required=False,
            max_length=500
        )
        self.add_item(self.theory)
    
    async def on_submit(self, interaction: Interaction):
        db = interaction.client.db
        db.update_section(self.section_id, theory_link=self.theory.value)
        await interaction.response.send_message("✅ Теория обновлена!", ephemeral=True)


# ============================================
# РЕДАКТИРОВАНИЕ УСЛОВИЯ ЗАЧЕТА
# ============================================

class EditPassConditionModal(Modal, title="🏆 Редактировать условие зачета"):
    
    def __init__(self, section_id: int):
        super().__init__()
        self.section_id = section_id
        
        db = interaction.client.db
        section = db.get_section(section_id)
        current_condition = section['pass_condition'] if section else ''
        
        self.condition = TextInput(
            label="Условие зачета",
            placeholder="Например: iLvl 200+, знание всех боссов",
            default=current_condition,
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500
        )
        self.add_item(self.condition)
    
    async def on_submit(self, interaction: Interaction):
        db = interaction.client.db
        db.update_section(self.section_id, pass_condition=self.condition.value)
        await interaction.response.send_message("✅ Условие зачета обновлено!", ephemeral=True)


# ============================================
# РЕДАКТИРОВАНИЕ ЗАДАНИЯ
# ============================================

class EditTaskModal(Modal, title="✏️ Редактировать задание"):
    
    def __init__(self, task_id: int):
        super().__init__()
        self.task_id = task_id
        
        db = interaction.client.db
        task = db.get_task(task_id)
        
        self.title = TextInput(
            label="Название задания",
            placeholder="Введите название...",
            default=task['title'] if task else '',
            required=True,
            max_length=200
        )
        self.add_item(self.title)
        
        self.description = TextInput(
            label="Описание задания",
            placeholder="Опишите задание...",
            default=task['description'] if task else '',
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=2000
        )
        self.add_item(self.description)
        
        self.difficulty = TextInput(
            label="Сложность (1-3)",
            placeholder="1 - Легкое, 2 - Среднее, 3 - Сложное",
            default=str(task['difficulty']) if task else '1',
            required=True,
            max_length=10
        )
        self.add_item(self.difficulty)
        
        self.points = TextInput(
            label="Награда (баллы)",
            placeholder="Например: 25",
            default=str(task['points_reward']) if task else '10',
            required=True,
            max_length=10
        )
        self.add_item(self.points)
    
    async def on_submit(self, interaction: Interaction):
        db = interaction.client.db
        
        try:
            difficulty = int(self.difficulty.value)
            if difficulty not in [1, 2, 3]:
                await interaction.response.send_message("❌ Сложность должна быть 1, 2 или 3!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите число!", ephemeral=True)
            return
        
        try:
            points = int(self.points.value)
            if points < 1 or points > 100:
                await interaction.response.send_message("❌ Награда должна быть от 1 до 100!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Введите число!", ephemeral=True)
            return
        
        db.cursor.execute('''
            UPDATE tasks 
            SET title = ?, description = ?, difficulty = ?, points_reward = ?
            WHERE id = ?
        ''', (self.title.value, self.description.value, difficulty, points, self.task_id))
        db.conn.commit()
        
        db.add_curator_log(
            "✏️ Задание отредактировано",
            interaction.user.id,
            f"Задание #{self.task_id}: {self.title.value}",
            self.task_id
        )
        
        embed = Embed(
            title="✅ Задание обновлено!",
            description=(
                f"**Название:** {self.title.value}\n"
                f"**Сложность:** {difficulty}\n"
                f"**Награда:** +{points} баллов"
            ),
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)