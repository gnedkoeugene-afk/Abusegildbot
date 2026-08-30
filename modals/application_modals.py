# modals/application_modals.py — ПОЛНЫЙ ФАЙЛ С АВТООЧИСТКОЙ ИМЁН

import discord
import asyncio
import re
from discord.ui import Modal, TextInput
from discord import TextStyle, Color, Embed
from datetime import datetime
import utils
from helpers.functions import get_class_emoji
from constants import RAID_ROLE_NAMES


class ApplicationModal(Modal):
    def __init__(self, class_spec: str, temp_data: dict, raid_role: str):
        super().__init__(title="📝 Данные персонажа", timeout=None)
        self.class_spec = class_spec
        self.temp_data = temp_data
        self.raid_role = raid_role
        self.specialization = temp_data.get('specialization', 'Не указана')

        self.add_item(TextInput(
            label="👤 Ваше личное имя",
            placeholder="Только буквы: Алексей",
            required=True,
            max_length=32,
            min_length=2
        ))
        self.add_item(TextInput(
            label="🎮 Имя персонажа",
            placeholder="Только буквы: Варвар",
            required=True,
            max_length=50,
            min_length=2
        ))
        self.add_item(TextInput(
            label="💎 Уровень предметов (iLvl)",
            placeholder="615",
            required=True,
            max_length=4,
            min_length=1
        ))
        self.add_item(TextInput(
            label="🔗 Ссылка на профиль Sirus",
            placeholder="https://sirus.su/game/...",
            required=True,
            max_length=200,
            min_length=10
        ))
        self.add_item(TextInput(
            label="📨 Кто добавил вас в гильдию",
            placeholder="Никнейм или «Поиск гильдии»",
            required=True,
            max_length=50
        ))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.followup.send("❌ Ошибка БД!", ephemeral=True)
            return
        if db.is_blacklisted(interaction.user.id):
            await interaction.followup.send("🚫 Вы в ЧС.", ephemeral=True)
            return

        # ═══════════════════════════════════════════════════════
        # ✅ АВТООЧИСТКА ВСЕХ ПОЛЕЙ
        # ═══════════════════════════════════════════════════════
        
        real_name = self.children[0].value.strip()
        character_name = self.children[1].value.strip()
        invited_by = self.children[4].value.strip()
        
        # Сохраняем оригиналы
        original_real_name = real_name
        original_char_name = character_name
        
        # ─── ОЧИСТКА ЛИЧНОГО ИМЕНИ ───
        # Убираем всё что в скобках: "Женя(123)" → "Женя"
        real_name = re.sub(r'\([^)]*\)', '', real_name)
        # Убираем всё что после цифры: "Женя123" → "Женя"
        real_name = re.sub(r'\d.*$', '', real_name)
        # Убираем всё после пробела: "Женя что-то" → "Женя"
        real_name = real_name.split()[0] if real_name.split() else ''
        # Оставляем только буквы
        real_name = re.sub(r'[^a-zA-Zа-яА-ЯёЁ]', '', real_name)
        
        if not real_name:
            await interaction.followup.send(
                f"❌ **Не удалось определить имя!**\n\n"
                f"Вы написали: `{original_real_name}`\n\n"
                f"Напишите просто своё имя буквами.\n"
                f"Например: `Женя` или `Алексей`",
                ephemeral=True
            )
            return
        
        # ─── ОЧИСТКА ИМЕНИ ПЕРСОНАЖА ───
        # Убираем скобки: "Варвар(твинк)" → "Варвар"
        character_name = re.sub(r'\([^)]*\)', '', character_name)
        # Убираем всё после пробела: "Варвар 123" → "Варвар"
        character_name = character_name.split()[0] if character_name.split() else ''
        # Убираем всё после цифры: "Варвар123" → "Варвар"
        character_name = re.sub(r'\d.*$', '', character_name)
        # Оставляем только буквы
        character_name = re.sub(r'[^a-zA-Zа-яА-ЯёЁ]', '', character_name)
        
        if not character_name:
            await interaction.followup.send(
                f"❌ **Не удалось определить имя персонажа!**\n\n"
                f"Вы написали: `{original_char_name}`\n\n"
                f"Напишите просто имя персонажа буквами.\n"
                f"Например: `Варвар` или `Warrior`",
                ephemeral=True
            )
            return
        
        # ─── ОЧИСТКА "КТО ПРИГЛАСИЛ" ───
        invited_by = re.sub(r'\([^)]*\)', '', invited_by).strip()
        invited_by = ' '.join(invited_by.split())
        
        if not invited_by:
            await interaction.followup.send(
                "❌ **Укажите кто вас пригласил!**\n\n"
                "Напишите ник пригласившего или «Поиск гильдии».",
                ephemeral=True
            )
            return
        
        if len(invited_by) > 30:
            invited_by = invited_by[:30]
        
        # Логируем исправления
        if real_name != original_real_name:
            print(f"✏️ Имя исправлено: '{original_real_name}' → '{real_name}'")
        if character_name != original_char_name:
            print(f"✏️ Персонаж исправлен: '{original_char_name}' → '{character_name}'")

        # ═══════════════════════════════════════════════════════
        # ✅ ВАЛИДАЦИЯ ILVL
        # ═══════════════════════════════════════════════════════
        
        try:
            ilvl = int(self.children[2].value)
            if not (1 <= ilvl <= 1000):
                raise ValueError
        except ValueError:
            await interaction.followup.send("❌ iLvl от 1 до 1000!", ephemeral=True)
            return

        # ═══════════════════════════════════════════════════════
        # ✅ СОЗДАНИЕ ЗАЯВКИ
        # ═══════════════════════════════════════════════════════
        
        data = {
            'real_name': real_name,
            'character_name': character_name,
            'class_spec': self.class_spec,
            'specialization': self.specialization,
            'item_level': ilvl,
            'profile_url': self.children[3].value,
            'available_days': self.temp_data['available_days'],
            'raid_role': self.raid_role,
            'invited_by': invited_by,
        }

        guild = interaction.guild
        cat_id = utils.safe_int(db.get_setting('applications_category', ''))
        category = guild.get_channel(cat_id) if cat_id else None
        if not category:
            category = await guild.create_category_channel("📝 Заявки в гильдию")
            db.set_setting('applications_category', str(category.id))

        app_id = db.add_application(interaction.user.id, data)
        db.add_log("📝 Заявка", interaction.user.id, details=f"Заявка #{app_id}: {data['character_name']} ({data['class_spec']})")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        for role_id in db.get_reviewer_roles():
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        channel = await guild.create_text_channel(f'📝-заявка-{app_id}', category=category, overwrites=overwrites)
        db.cursor.execute('UPDATE applications SET channel_id = ? WHERE id = ?', (channel.id, app_id))
        db.conn.commit()

        mentions = []
        for key in ['guild_master', 'vice_master', 'raid_leader', 'officer']:
            role_id = utils.safe_int(db.get_setting(key, ''))
            if role_id:
                role = guild.get_role(role_id)
                if role:
                    mentions.append(role.mention)

        class_emoji = get_class_emoji(data['class_spec'])
        role_emoji = {"mdd": "⚔️", "rdd": "🏹", "tank": "🛡️", "heal": "💚"}.get(self.raid_role, "⚔️")

        embed = Embed(
            title=f"📝 Заявка #{app_id}",
            description=f"**Заявитель:** {interaction.user.mention}",
            color=Color.purple()
        )
        embed.add_field(name="👤 Личное имя", value=f"```{data['real_name']}```", inline=True)
        embed.add_field(name="🎮 Имя персонажа", value=f"```{data['character_name']}```", inline=True)
        embed.add_field(name="⚔️ Класс", value=f"{class_emoji} **{data['class_spec']}**", inline=True)
        embed.add_field(name="🎯 Специализация", value=f"```{self.specialization}```", inline=True)
        embed.add_field(name="💎 Уровень предметов", value=f"```{data['item_level']} iLvl```", inline=True)
        embed.add_field(name="📅 Дни рейдов", value=f"```{utils.format_days(data['available_days'])}```", inline=True)
        embed.add_field(name=f"{role_emoji} Роль в рейде", value=f"**{RAID_ROLE_NAMES.get(self.raid_role, 'МДД')}**", inline=True)
        embed.add_field(name="📨 Кто пригласил", value=f"```{invited_by}```", inline=True)
        embed.add_field(name="🔗 Профиль", value=f"[Sirus]({data['profile_url']})", inline=True)
        embed.set_footer(text=f"Гильдия: {db.get_setting('guild_name', 'Abuse')} • ID: {app_id}")

        from views.applications import ApplicationReviewView
        view = ApplicationReviewView(channel.id, interaction.user.id, app_id, data)

        msg = await channel.send(content=" ".join(mentions) if mentions else None, embed=embed, view=view)
        interaction.client.add_view(view, message_id=msg.id)
        db.cursor.execute('UPDATE applications SET message_id = ? WHERE id = ?', (msg.id, app_id))
        db.conn.commit()

        # Сообщение с информацией об исправлениях
        correction_note = ""
        if real_name != original_real_name:
            correction_note += f"\n✏️ Имя исправлено: `{original_real_name}` → `{real_name}`"
        if character_name != original_char_name:
            correction_note += f"\n✏️ Персонаж исправлен: `{original_char_name}` → `{character_name}`"

        await interaction.followup.send(
            f"✅ Заявка #{app_id} создана!\n📁 {channel.mention}\n"
            f"👤 {data['real_name']}\n🎮 {data['character_name']} ({data['class_spec']}, {self.specialization})\n"
            f"💎 {data['item_level']} iLvl\n📨 Пригласил: {invited_by}"
            f"{correction_note}",
            ephemeral=True
        )


class RejectModal(Modal):
    def __init__(self, app_id: int, user_id: int, channel_id: int, data: dict = None):
        super().__init__(title="❌ Отклонить заявку")
        self.app_id = app_id
        self.user_id = user_id
        self.channel_id = channel_id
        self.data = data or {}
        self.add_item(TextInput(
            label="Причина отклонения",
            placeholder="Укажите причину...",
            style=TextStyle.paragraph,
            required=True,
            max_length=500
        ))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.followup.send("❌ БД не найдена!", ephemeral=True)
            return

        reason = self.children[0].value.strip()
        db.update_application_status(self.app_id, "rejected", interaction.user.id)
        db.update_application_attempt(self.user_id, reason)
        db.add_log("❌ Заявка отклонена", interaction.user.id, self.user_id, f"Причина: {reason}")

        user = interaction.guild.get_member(self.user_id)
        if user:
            await utils.add_roles_from_setting(user, db, 'reject_role', "Заявка отклонена")
            await utils.remove_roles_from_setting(user, db, 'applicant_role', "Заявка отклонена")
            await utils.remove_roles_from_setting(user, db, 'guest_role', "Заявка отклонена")
            try:
                embed = Embed(
                    title="❌ Заявка отклонена",
                    description=f"**Сервер:** {interaction.guild.name}\n**Причина:** {reason}\n\nВы сможете подать заявку снова через некоторое время.",
                    color=Color.red()
                )
                await user.send(embed=embed)
            except:
                pass

        from views.applications import send_application_log
        char_name = self.data.get('character_name', 'Неизвестно') if self.data else 'Неизвестно'
        await send_application_log(interaction, db, "rejected", user, interaction.user, char_name, reason)

        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            try:
                async for msg in channel.history(limit=10):
                    if msg.author == interaction.client.user and msg.embeds:
                        embed = msg.embeds[0]
                        embed.color = Color.red()
                        embed.set_footer(text=f"❌ Отклонено | {interaction.user.display_name}")
                        embed.add_field(name="📝 Причина", value=reason, inline=False)
                        await msg.edit(embed=embed, view=None)
                        break
            except:
                pass
            try:
                archive_channel_id = utils.safe_int(db.get_setting('archive_channel', ''))
                if archive_channel_id:
                    archive_channel = interaction.guild.get_channel(archive_channel_id)
                    if archive_channel:
                        async for msg in channel.history(limit=5):
                            if msg.author == interaction.client.user and msg.embeds:
                                e = msg.embeds[0]
                                ae = Embed(
                                    title=f"📁 Архив: {e.title}",
                                    description=e.description or "",
                                    color=Color.red(),
                                    timestamp=datetime.now()
                                )
                                for f in e.fields:
                                    ae.add_field(name=f.name, value=f.value, inline=f.inline)
                                ae.add_field(name="❌ Статус", value=f"Отклонена | {interaction.user.mention}", inline=False)
                                ae.set_footer(text=f"Архивировано | ID: {self.app_id}")
                                await archive_channel.send(embed=ae)
                                break
            except:
                pass

        await interaction.followup.send(f"✅ Заявка отклонена!\n📝 Причина: {reason}", ephemeral=True)
        try:
            await asyncio.sleep(3)
            await channel.delete()
        except:
            pass


class BlacklistModal(Modal):
    def __init__(self, app_id: int, user_id: int, channel_id: int, data: dict = None):
        super().__init__(title="🚫 Добавить в ЧС")
        self.app_id = app_id
        self.user_id = user_id
        self.channel_id = channel_id
        self.data = data or {}
        self.add_item(TextInput(
            label="Причина добавления в ЧС",
            placeholder="Укажите причину...",
            style=TextStyle.paragraph,
            required=True,
            max_length=500
        ))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.followup.send("❌ БД не найдена!", ephemeral=True)
            return

        reason = self.children[0].value.strip()
        db.blacklist_user(self.user_id, reason, interaction.user.id)
        db.update_application_status(self.app_id, "blacklisted", interaction.user.id)
        db.update_application_attempt(self.user_id, reason)
        db.add_log("🚫 ЧС", interaction.user.id, self.user_id, f"Причина: {reason}")

        user = interaction.guild.get_member(self.user_id)
        if user:
            await utils.remove_roles_from_setting(user, db, 'member_role', "ЧС")
            await utils.remove_roles_from_setting(user, db, 'guest_role', "ЧС")
            await utils.remove_roles_from_setting(user, db, 'applicant_role', "ЧС")
            await utils.remove_roles_from_setting(user, db, 'reject_role', "ЧС")
            await utils.add_roles_from_setting(user, db, 'blacklist_role', "ЧС")
            try:
                await user.send(embed=Embed(
                    title="🚫 Вы добавлены в ЧС",
                    description=f"**Сервер:** {interaction.guild.name}\n**Причина:** {reason}",
                    color=Color.dark_red()
                ))
            except:
                pass

        from views.applications import send_application_log
        char_name = self.data.get('character_name', 'Неизвестно') if self.data else 'Неизвестно'
        await send_application_log(interaction, db, "blacklisted", user, interaction.user, char_name, reason)

        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            try:
                async for msg in channel.history(limit=10):
                    if msg.author == interaction.client.user and msg.embeds:
                        embed = msg.embeds[0]
                        embed.color = Color.dark_red()
                        embed.set_footer(text=f"🚫 ЧС | {interaction.user.display_name}")
                        embed.add_field(name="📝 Причина", value=reason, inline=False)
                        await msg.edit(embed=embed, view=None)
                        break
            except:
                pass
            try:
                archive_channel_id = utils.safe_int(db.get_setting('archive_channel', ''))
                if archive_channel_id:
                    archive_channel = interaction.guild.get_channel(archive_channel_id)
                    if archive_channel:
                        async for msg in channel.history(limit=5):
                            if msg.author == interaction.client.user and msg.embeds:
                                e = msg.embeds[0]
                                ae = Embed(
                                    title=f"📁 Архив: {e.title}",
                                    description=e.description or "",
                                    color=Color.dark_red(),
                                    timestamp=datetime.now()
                                )
                                for f in e.fields:
                                    ae.add_field(name=f.name, value=f.value, inline=f.inline)
                                ae.add_field(name="🚫 Статус", value=f"ЧС | {interaction.user.mention}", inline=False)
                                ae.set_footer(text=f"Архивировано | ID: {self.app_id}")
                                await archive_channel.send(embed=ae)
                                break
            except:
                pass

        await interaction.followup.send(f"✅ Пользователь добавлен в ЧС!\n📝 Причина: {reason}", ephemeral=True)
        try:
            await asyncio.sleep(3)
            await channel.delete()
        except:
            pass
