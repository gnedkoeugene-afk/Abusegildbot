# modals/character_modals.py — ПОЛНЫЙ ИСПРАВЛЕННЫЙ ФАЙЛ

import discord
import asyncio
from discord.ui import Modal, TextInput
from discord import TextStyle, Color, Embed
import utils
from constants import RAID_ROLE_NAMES


class AddTwinModal(Modal):
    """Добавление персонажа (основного или твинка)"""
    def __init__(self, is_main: bool = False):
        super().__init__(title="📝 Добавление персонажа", timeout=None)
        self.is_main = is_main
        self.class_name = None
        self.specialization = None
        self.raid_role = 'mdd'
        
        self.add_item(TextInput(label="✨ Имя персонажа", placeholder="Варвар", required=True, max_length=50))
        self.add_item(TextInput(label="💎 Уровень предметов (iLvl)", placeholder="615", required=True, max_length=4))
        self.add_item(TextInput(label="🔗 Ссылка на профиль Sirus", placeholder="https://sirus.su/game/...", required=False, max_length=200))
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.followup.send("❌ Ошибка БД!", ephemeral=True)
            return
        
        character_name = self.children[0].value.strip()
        if not character_name:
            await interaction.followup.send("❌ Имя персонажа не может быть пустым!", ephemeral=True)
            return
        
        try:
            item_level = int(self.children[1].value.strip())
            if not (1 <= item_level <= 1000):
                raise ValueError
        except ValueError:
            await interaction.followup.send("❌ Уровень предметов должен быть числом от 1 до 1000!", ephemeral=True)
            return
        
        profile_url = self.children[2].value.strip() if self.children[2].value else ""
        
        if self.is_main:
            existing_main = db.get_main_character(interaction.user.id)
            if existing_main:
                await interaction.followup.send("❌ У вас уже есть основной персонаж!", ephemeral=True)
                return
        
        # ✅ Получаем класс из атрибутов (установлены заранее)
        class_name = getattr(self, 'class_name', None)
        specialization = getattr(self, 'specialization', None)
        raid_role = getattr(self, 'raid_role', 'mdd')
        
        # Если класс уже установлен — сохраняем персонажа сразу
        if class_name and specialization:
            specs_str = specialization if isinstance(specialization, str) else ', '.join(specialization)
            
            char_data = {
                'character_name': character_name,
                'class_spec': class_name,
                'specialization': specs_str,
                'item_level': item_level,
                'profile_url': profile_url,
                'raid_role': raid_role,
                'is_main': 1 if self.is_main else 0
            }
            
            db.add_character(interaction.user.id, char_data)
            
            if self.is_main:
                db.mark_characters_added(interaction.user.id)
            
            db.add_log("➕ Персонаж добавлен", interaction.user.id, details=f"{character_name} ({class_name}, {specs_str}, {item_level} iLvl)")
            
            type_text = "Основной персонаж" if self.is_main else "Твинк"
            await interaction.followup.send(
                f"✅ **{type_text} добавлен!**\n"
                f"👤 **{character_name}**\n"
                f"⚔️ **{class_name}** — {specs_str}\n"
                f"💎 **{item_level}** iLvl\n"
                f"🎭 Роль: **{utils.format_raid_roles(raid_role)}**",
                ephemeral=True,
                delete_after=10
            )
        else:
            # Открываем выбор класса
            from views.characters import ClassSpecSelectView
            view = ClassSpecSelectView(self, character_name, item_level, profile_url, is_main=self.is_main)
            embed = Embed(
                title="⚔️ Выберите класс и специализацию",
                description=f"Укажите класс вашего {'основного персонажа' if self.is_main else 'твинка'}:",
                color=Color.blue()
            )
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)


class EditCharacterModal(Modal):
    """Редактирование персонажа"""
    def __init__(self, character_id: int, current_data: dict):
        super().__init__(title="✏️ Редактирование персонажа", timeout=None)
        self.character_id = character_id
        
        self.add_item(TextInput(label="✨ Имя персонажа", default=current_data.get('character_name', ''), required=True, max_length=50))
        self.add_item(TextInput(label="💎 Уровень предметов (iLvl)", default=str(current_data.get('item_level', 0)), required=True, max_length=4))
        self.add_item(TextInput(label="🔗 Ссылка на профиль Sirus", default=current_data.get('profile_url', ''), required=False, max_length=200))
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.followup.send("❌ Ошибка БД!", ephemeral=True)
            return
        
        character_name = self.children[0].value.strip()
        if not character_name:
            await interaction.followup.send("❌ Имя персонажа не может быть пустым!", ephemeral=True)
            return
        
        try:
            item_level = int(self.children[1].value.strip())
            if not (1 <= item_level <= 1000):
                raise ValueError
        except ValueError:
            await interaction.followup.send("❌ Уровень предметов от 1 до 1000!", ephemeral=True)
            return
        
        profile_url = self.children[2].value.strip() if self.children[2].value else ""
        
        db.cursor.execute(
            'UPDATE characters SET character_name = ?, item_level = ?, profile_url = ? WHERE id = ?',
            (character_name, item_level, profile_url, self.character_id)
        )
        db.conn.commit()
        
        embed = Embed(
            title="✅ Персонаж обновлён",
            description=f"**{character_name}**\n💎 {item_level} iLvl",
            color=Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


class ChangeMainCharacterModal(Modal):
    """Заявка на смену основного персонажа"""
    def __init__(self, twin_id: int, twin_name: str):
        super().__init__(title=f"🔄 Смена основного персонажа на {twin_name}", timeout=None)
        self.twin_id = twin_id
        self.add_item(TextInput(
            label="📝 Причина смены",
            placeholder="Укажите причину...",
            style=TextStyle.paragraph,
            required=True,
            max_length=500
        ))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.followup.send("❌ Ошибка базы данных!", ephemeral=True)
            return
        
        reason = self.children[0].value.strip()
        if not reason:
            await interaction.followup.send("❌ Укажите причину смены!", ephemeral=True)
            return
        
        twin = db.get_character_by_id(self.twin_id)
        if not twin:
            await interaction.followup.send("❌ Персонаж не найден!", ephemeral=True)
            return
        
        current_main = db.get_main_character(interaction.user.id)
        if not current_main:
            await interaction.followup.send("❌ У вас нет основного персонажа!", ephemeral=True)
            return
        
        category = None
        cat_id = utils.safe_int(db.get_setting('main_change_category', ''))
        if cat_id:
            category = interaction.guild.get_channel(cat_id)
        if not category:
            category = await interaction.guild.create_category_channel("🔄 Смена основного персонажа")
            db.set_setting('main_change_category', str(category.id))
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role_id in db.get_reviewer_roles():
            role = interaction.guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        request_id = db.create_main_change_request(interaction.user.id, current_main['id'], twin['id'], reason)
        channel = await interaction.guild.create_text_channel(
            f"🔄-смена-персонажа-{request_id}",
            category=category,
            overwrites=overwrites
        )
        
        embed = Embed(
            title=f"🔄 Заявка на смену основного персонажа #{request_id}",
            description=f"**Игрок:** {interaction.user.mention}\n"
                        f"**Текущий основной:** {current_main['character_name']} ({current_main['class_spec']})\n"
                        f"**Новый основной:** {twin['character_name']} ({twin['class_spec']})\n"
                        f"**Причина:** {reason}",
            color=Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        
        from views.characters import MainChangeReviewView
        view = MainChangeReviewView(request_id, interaction.user.id, current_main['id'], twin['id'])
        await channel.send(embed=embed, view=view)
        
        await interaction.followup.send(
            f"✅ Заявка на смену основного персонажа отправлена! Следите за {channel.mention}",
            ephemeral=True
        )


class StaticRequestModal(Modal):
    """Запрос в статик"""
    def __init__(self):
        super().__init__(title="📋 Запрос в статик", timeout=None)
        self.add_item(TextInput(
            label="🔗 Ссылка на скриншоты (Imgur)",
            placeholder="https://imgur.com/a/...",
            required=True,
            max_length=200
        ))
        self.add_item(TextInput(
            label="📝 Дополнительная информация",
            placeholder="Опишите свой опыт...",
            style=TextStyle.paragraph,
            required=False,
            max_length=500
        ))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.followup.send("❌ БД не найдена!", ephemeral=True); return
        
        # ✅ Проверка роли
        required_role_id = utils.safe_int(db.get_setting('static_required_role', ''))
        if not required_role_id:
            required_role_id = utils.safe_int(db.get_setting('member_role', ''))
        if not required_role_id:
            await interaction.followup.send("❌ Роль для подачи не настроена!", ephemeral=True); return
        required_role = interaction.guild.get_role(required_role_id)
        if not required_role: await interaction.followup.send("❌ Роль не найдена!", ephemeral=True); return
        if required_role not in interaction.user.roles:
            no_role_text = db.get_setting('static_no_role_text', '')
            if not no_role_text:
                no_role_text = f"Для подачи заявки в статик нужна роль **{required_role.name}**."
            embed = Embed(title="🔒 Недоступно", description=no_role_text, color=Color.orange())
            await interaction.followup.send(embed=embed, ephemeral=True, delete_after=10)
            return
            
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.followup.send("❌ Ошибка базы данных!", ephemeral=True)
            return
        
        imgur_link = self.children[0].value.strip()
        additional_info = self.children[1].value.strip() if self.children[1].value else "Не указано"
        
        # Проверяем ссылку
        if not (imgur_link.startswith("https://imgur.com/") or imgur_link.startswith("https://i.imgur.com/")):
            await interaction.followup.send("❌ Ссылка должна быть на https://imgur.com/!", ephemeral=True)
            return
        
        # Проверяем основного персонажа
        main_char = db.get_main_character(interaction.user.id)
        if not main_char:
            await interaction.followup.send("❌ У вас нет основного персонажа!", ephemeral=True)
            return
        
        # Создаём категорию если нет
        category = None
        cat_id = utils.safe_int(db.get_setting('static_request_category', ''))
        if cat_id:
            category = interaction.guild.get_channel(cat_id)
        if not category:
            category = await interaction.guild.create_category_channel("📋 Запросы в статик")
            db.set_setting('static_request_category', str(category.id))
        
        # ✅ Права доступа — ВСЕ роли голосования видят канал
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, manage_channels=True
            )
        }
        
        # ✅ Добавляем все роли голосования в права канала
        vote_roles = []
        for i in range(1, 6):
            role_id = utils.safe_int(db.get_setting(f'vote_role_{i}', ''))
            if role_id:
                role = interaction.guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True,
                        read_message_history=True
                    )
                    vote_roles.append(role)
        
        # Создаём канал
        channel = await interaction.guild.create_text_channel(
            f"📋-статик-{main_char['character_name']}",
            category=category,
            overwrites=overwrites,
            topic=f"Заявка в статик от {interaction.user.display_name} | Голосование"
        )
        
        # Создаём заявку в БД
        request_id = db.create_static_request(
            interaction.user.id,
            main_char['id'],
            imgur_link,
            additional_info,
            channel.id
        )
        
        # Создаём Embed с информацией
        embed = Embed(
            title=f"📋 Запрос в статик от {main_char['character_name']}",
            description=f"**Игрок:** {interaction.user.mention}\n"
                        f"**Персонаж:** {main_char['character_name']} ({main_char['class_spec']})\n"
                        f"**Специализация:** {main_char.get('specialization', 'Не указана')}\n"
                        f"**iLvl:** {main_char['item_level']}\n"
                        f"**Роль:** {utils.format_raid_roles(main_char.get('raid_role', 'mdd'))}\n\n"
                        f"**Скриншоты:** [Нажмите для просмотра]({imgur_link})\n\n"
                        f"**Дополнительно:**\n{additional_info}",
            color=Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"ID заявки: {request_id} | Статус: Голосование")
        
        # ✅ Создаём View и регистрируем в боте
        from views.characters import StaticRequestReviewView
        view = StaticRequestReviewView()
        interaction.client.add_view(view)
        
        # Отправляем сообщение с кнопками
        await channel.send(embed=embed, view=view)
        
        # ✅ Упоминаем роли голосования
        if vote_roles:
            mentions = [role.mention for role in vote_roles]
            await channel.send(
                f"📋 **Голосование!** Требуется решение от: {', '.join(mentions)}\n"
                f"Используйте кнопки ✅ За / ❌ Против под заявкой.\n"
                f"Когда все члены этих ролей проголосуют — бот подведёт итог."
            )
        
        # Уведомляем заявителя
        await interaction.followup.send(
            f"✅ Запрос в статик отправлен!\n"
            f"📁 Канал: {channel.mention}\n"
            f"📋 ID заявки: {request_id}\n\n"
            f"Ожидайте голосования.",
            ephemeral=True
        )


class SupportModal(Modal):
    """Сообщить о проблеме"""
    def __init__(self):
        super().__init__(title="🛠️ Сообщить о проблеме", timeout=None)
        self.add_item(TextInput(label="📝 Краткое описание", placeholder="Опишите проблему...", required=True, max_length=200))
        self.add_item(TextInput(label="📋 Подробности", placeholder="Опишите подробно...", style=TextStyle.paragraph, required=True, max_length=1000))
        self.add_item(TextInput(label="📎 Скриншоты (ссылка)", placeholder="https://imgur.com/...", required=False, max_length=300))

# modals/character_modals.py — SupportModal.on_submit

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.followup.send("❌ Ошибка базы данных!", ephemeral=True)
            return
        
        title = self.children[0].value.strip()
        description = self.children[1].value.strip()
        screenshots = self.children[2].value.strip() if self.children[2].value else "Не прикреплены"
        
        if not title or not description:
            await interaction.followup.send("❌ Заполните обязательные поля!", ephemeral=True)
            return
        
        guild = interaction.guild
        
        category = None
        cat_id = utils.safe_int(db.get_setting('support_category', ''))
        if cat_id:
            category = guild.get_channel(cat_id)
        if not category:
            category = await guild.create_category_channel("🛠️ Техподдержка")
            db.set_setting('support_category', str(category.id))
        
        report_id = db.get_next_id('support_reports')
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }
        developer_id = db.get_setting('developer_id', '')
        if developer_id:
            developer = guild.get_member(int(developer_id))
            if developer:
                overwrites[developer] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        
        channel = await guild.create_text_channel(f"🛠️-баг-{report_id}", category=category, overwrites=overwrites)
        
        # Сохраняем в БД
        db.cursor.execute(
            'INSERT INTO support_reports (id, user_id, channel_id, title, description, screenshots, status) VALUES (?, ?, ?, ?, ?, ?, "open")',
            (report_id, interaction.user.id, channel.id, title, description, screenshots)
        )
        db.conn.commit()
        
        embed = Embed(
            title=f"🛠️ Баг-репорт #{report_id}",
            description=f"**Отправитель:** {interaction.user.mention}\n"
                        f"**Проблема:** {title}\n\n"
                        f"**Подробности:**\n{description}\n\n"
                        f"**Скриншоты:** {screenshots}",
            color=Color.red(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"ID: {report_id} | Статус: Открыт")
        
        # ✅ СОЗДАЁМ VIEW И РЕГИСТРИРУЕМ
        from views.characters import SupportView
        view = SupportView(report_id, interaction.user.id)
        interaction.client.add_view(view)
        
        await channel.send(embed=embed, view=view)
        
        await interaction.followup.send(
            f"✅ Обращение #{report_id} зарегистрировано!\nРазработчик рассмотрит его.\n{channel.mention}",
            ephemeral=True
        )


class SupportReplyModal(Modal):
    """Ответ на обращение"""
    def __init__(self, report_id: int, user_id: int, channel):
        super().__init__(title=f"💬 Ответ на обращение #{report_id}", timeout=None)
        self.report_id = report_id
        self.user_id = user_id
        self.channel = channel
        
        self.add_item(TextInput(
            label="📝 Текст ответа",
            placeholder="Введите ответ...",
            style=TextStyle.paragraph,
            required=True,
            max_length=1000
        ))

    async def on_submit(self, interaction: discord.Interaction):
        reply_text = self.children[0].value.strip()
        if not reply_text:
            await interaction.response.send_message("❌ Введите текст ответа!", ephemeral=True)
            return
        
        # ✅ Отправляем ответ от имени бота в канал
        embed = Embed(
            title=f"💬 Ответ на обращение #{self.report_id}",
            description=reply_text,
            color=Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text=f"Ответ от бота | Разработчик: {interaction.user.display_name}")
        
        await self.channel.send(embed=embed)
        
        # ✅ Отправляем ЛС заявителю
        guild = interaction.guild
        user = guild.get_member(self.user_id)
        if user:
            try:
                dm_embed = Embed(
                    title=f"💬 Ответ на обращение #{self.report_id}",
                    description=f"**Сервер:** {guild.name}\n\n"
                               f"**Сообщение от разработчика:**\n{reply_text}\n\n"
                               f"Вы можете ответить в канале {self.channel.mention}",
                    color=Color.blue(),
                    timestamp=discord.utils.utcnow()
                )
                dm_embed.set_footer(text=f"Ответ через бота | Разработчик: {interaction.user.display_name}")
                await user.send(embed=dm_embed)
            except:
                pass
        
        await interaction.response.send_message("✅ Ответ отправлен!", ephemeral=True, delete_after=5)


class StaticRejectModal(Modal):
    """Отклонение заявки в статик"""
    def __init__(self, request_id: int, user_id: int, channel):
        super().__init__(title="❌ Отклонить заявку в статик")
        self.request_id = request_id
        self.user_id = user_id
        self.channel = channel
        
        self.add_item(TextInput(
            label="📝 Причина отклонения",
            placeholder="Укажите причину отказа...",
            style=TextStyle.paragraph,
            required=True,
            max_length=500
        ))
    
    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        reason = self.children[0].value.strip()
        if not reason:
            await interaction.response.send_message("❌ Укажите причину!", ephemeral=True)
            return
        
        db.update_static_request_status(self.request_id, "rejected", interaction.user.id)
        
        user = interaction.guild.get_member(self.user_id)
        
        if user:
            try:
                embed = Embed(
                    title="❌ Заявка в статик отклонена",
                    description=f"**Сервер:** {interaction.guild.name}\n"
                               f"**Модератор:** {interaction.user.mention}\n\n"
                               f"**Причина:** {reason}",
                    color=Color.red()
                )
                await user.send(embed=embed)
            except:
                pass
        
        from views.characters import send_static_log
        await send_static_log(interaction, db, "❌ ОТКЛОНЕНО", user, interaction.user, reason)
        
        await interaction.response.send_message(
            f"✅ Заявка отклонена!\n📝 Причина: {reason}",
            ephemeral=True,
            delete_after=10
        )
        
        try:
            await asyncio.sleep(3)
            await interaction.channel.delete()
        except:
            pass