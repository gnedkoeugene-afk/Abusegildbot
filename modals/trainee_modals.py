# modals/trainee_modals.py — ПОЛНЫЙ ИСПРАВЛЕННЫЙ ФАЙЛ

import discord
from discord.ui import Modal, TextInput
from discord import Interaction, Embed, Color
from datetime import datetime
import database
import os


class TraineeApplicationModal(Modal, title="📝 Заявка на обучение РЛ"):
    
    experience = TextInput(
        label="Ваш опыт в рейдах",
        placeholder="Например: Водил Naxx 10 раз, ICC 5 раз...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    motivation = TextInput(
        label="Почему хотите стать РЛ?",
        placeholder="Ваша мотивация...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=1000
    )
    
    available_days = TextInput(
        label="Когда можете заниматься?",
        placeholder="Например: ПН, СР, ПТ с 20:00 до 23:00",
        required=True,
        max_length=200
    )
    
    async def on_submit(self, interaction: Interaction):
        # ============================================
        # ПОЛУЧАЕМ БД
        # ============================================
        db = interaction.client.get_db(interaction.guild_id)
        
        if db is None:
            os.makedirs('data', exist_ok=True)
            db = database.Database(f"data/guild_{interaction.guild_id}.db")
            db.init()
            interaction.client.databases[interaction.guild_id] = db
            print(f"✅ БД создана для {interaction.guild_id}")
        
        user = interaction.user
        
        # ============================================
        # 1. ПОЛУЧАЕМ ВСЕХ ПЕРСОНАЖЕЙ
        # ============================================
        all_chars = db.get_user_characters(user.id)
        
        if not all_chars:
            await interaction.response.send_message(
                "❌ Сначала добавьте персонажа в **Мои персонажи**!\n"
                "Используйте кнопку **➕ Добавить**",
                ephemeral=True
            )
            return
        
        # ============================================
        # 2. ПОЛУЧАЕМ ОСНОВНОГО ПЕРСОНАЖА
        # ============================================
        main_char = db.get_main_character(user.id)
        
        if not main_char:
            main_char = all_chars[0]
            db.cursor.execute('UPDATE characters SET is_main = 1 WHERE id = ?', (main_char['id'],))
            db.conn.commit()
            main_char = db.get_character_by_id(main_char['id'])
        
        # ============================================
        # 3. ПРОВЕРКА НА УЖЕ ПОДАННУЮ ЗАЯВКУ
        # ============================================
        existing = db.cursor.execute(
            'SELECT id, status FROM trainee_applications WHERE user_id = ? AND status = "pending"',
            (user.id,)
        ).fetchone()
        
        if existing:
            await interaction.response.send_message(
                f"❌ Вы уже подали заявку! Статус: ожидание рассмотрения.\n"
                f"ID заявки: #{existing[0]}",
                ephemeral=True
            )
            return
        
        # ============================================
        # 4. СОЗДАЁМ ЗАЯВКУ (ТОЛЬКО В БД)
        # ============================================
        app_id = db.create_trainee_application(
            user_id=user.id,
            character_id=main_char['id'],
            experience=self.experience.value,
            motivation=self.motivation.value
        )
        
        # ============================================
        # 5. УВЕДОМЛЕНИЕ ПОЛЬЗОВАТЕЛЮ
        # ============================================
        embed = Embed(
            title="✅ Заявка подана!",
            description=(
                f"Ваша заявка на обучение РЛ отправлена!\n\n"
                f"**Ваш персонаж:** {main_char['character_name']}\n"
                f"**ID заявки:** #{app_id}\n\n"
                f"Ожидайте решения куратора.\n\n"
                f"Кураторы рассматривают заявки через кнопку **'Добавить игрока'** в панели куратора."
            ),
            color=Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # ============================================
        # 6. УВЕДОМЛЕНИЕ КУРАТОРОВ (ОТКЛЮЧЕНО)
        # ============================================
        # Заявки больше не отправляются в канал.
        # Кураторы видят заявки через кнопку "Добавить игрока" в панели куратора.
        # await self.notify_curators(guild, db, user, main_char, app_id)