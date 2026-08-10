import discord
import asyncio
import random
from datetime import datetime, timedelta
from discord.ui import Modal, TextInput
from discord import TextStyle, Color, Embed
import utils
from helpers.functions import delete_message_after_delay
from views.punishments import TaskConfirmView

class PunishmentSearchModal(Modal):
    def __init__(self):
        super().__init__(title="🔍 Поиск персонажа для наказания", timeout=None)
        self.add_item(TextInput(label="🔍 Введите имя персонажа или @пользователя", placeholder="Например: Варвар или @Игрок", required=True, max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.db
        guild = interaction.guild
        query = self.children[0].value.strip()
        
        results = db.search_characters(query, guild, limit=10)
        
        if not results:
            await interaction.response.send_message(f"❌ По запросу **{query}** ничего не найдено.", ephemeral=True, delete_after=10)
            return
        
        from views.punishments import PunishmentSelectView
        view = PunishmentSelectView(results, is_removing=False)
        
        embed = Embed(title="🔍 Результаты поиска", description=f"Найдено персонажей: {len(results)}\n\nВыберите персонажа для выдачи наказания:", color=Color.blue())
        
        for i, char in enumerate(results[:10], 1):
            status_emoji = "⭐" if char['is_main'] else "🔄"
            violations_text = f"⚠️ {char['violations']} нарушений" if char['violations'] > 0 else "✅ без нарушений"
            embed.add_field(name=f"{i}. {status_emoji} {char['character_name']}", value=f"👤 {char['user_name']}\n📊 {violations_text}\n🎭 {char['class_spec']}", inline=True)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class PunishmentRemoveSearchModal(Modal):
    def __init__(self):
        super().__init__(title="🔍 Поиск персонажа для снятия наказания", timeout=None)
        self.add_item(TextInput(label="🔍 Введите имя персонажа или @пользователя", placeholder="Например: Варвар или @Игрок", required=True, max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.db
        guild = interaction.guild
        query = self.children[0].value.strip()
        
        results = db.search_characters(query, guild, limit=10)
        results_with_punishments = [r for r in results if r['violations'] > 0]
        
        if not results_with_punishments:
            await interaction.response.send_message(f"❌ По запросу **{query}** нет персонажей с наказаниями.", ephemeral=True, delete_after=10)
            return
        
        from views.punishments import PunishmentSelectView
        view = PunishmentSelectView(results_with_punishments, is_removing=True)
        
        embed = Embed(title="🔍 Результаты поиска", description=f"Найдено персонажей с наказаниями: {len(results_with_punishments)}\n\nВыберите персонажа для снятия наказания:", color=Color.orange())
        
        for i, char in enumerate(results_with_punishments[:10], 1):
            status_emoji = "⭐" if char['is_main'] else "🔄"
            embed.add_field(name=f"{i}. {status_emoji} {char['character_name']}", value=f"👤 {char['user_name']}\n⚠️ {char['violations']} нарушений\n🎭 {char['class_spec']}", inline=True)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class PunishmentModalNew(Modal):
    def __init__(self, character_id: int, character_name: str, user_id: int):
        super().__init__(title=f"⚠️ Наказание - {character_name}", timeout=None)
        self.character_id = character_id
        self.character_name = character_name
        self.user_id = user_id
        
        self.add_item(TextInput(label="📝 Причина нарушения", placeholder="Опишите причину нарушения...", style=TextStyle.paragraph, required=True, max_length=500))
        self.add_item(TextInput(label="📎 Ссылка на фото/видео фиксацию", placeholder="https://imgur.com/...", required=True, max_length=200))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.db
        reason = self.children[0].value
        evidence_link = self.children[1].value.strip()
        
        current_violations = db.get_total_violations_by_character(self.character_id)
        
        if current_violations >= 3:
            await interaction.response.send_message(f"❌ У персонажа **{self.character_name}** уже 3 нарушения!", ephemeral=True, delete_after=10)
            return
        
        if current_violations == 0:
            violation_count = 1
        elif current_violations == 1:
            violation_count = 2
        elif current_violations == 2:
            violation_count = 3
        else:
            violation_count = 1
        
        new_total = current_violations + violation_count
        
        db.add_punishment(self.character_id, self.user_id, violation_count, reason, interaction.user.id)
        
        user = interaction.guild.get_member(self.user_id)
        
        embed = Embed(title="⚠️ НАКАЗАНИЕ ВЫДАНО", description=f"**Персонаж:** {self.character_name}\n**Игрок:** {user.mention if user else f'ID: {self.user_id}'}\n**Нарушений:** {violation_count}\n**Всего:** {new_total}\n**Причина:** {reason}\n**Фиксация:** {evidence_link}\n**Выдал:** {interaction.user.mention}", color=Color.red(), timestamp=discord.utils.utcnow())
        
        warning_message = ""
        punishment_scheduled = False
        
        if new_total >= 3:
            existing_warning = db.get_active_warning(self.character_id)
            if not existing_warning:
                expires_at = datetime.now() + timedelta(hours=24)
                db.add_warning(self.character_id, self.user_id, 3, expires_at)
                warning_message = f"\n\n⚠️ **ПРЕДУПРЕЖДЕНИЕ 3-го УРОВНЯ!**\nУ вас есть 24 часа, чтобы снять наказания."
                from views.punishments import schedule_punishment_after_delay
                asyncio.create_task(schedule_punishment_after_delay(interaction, self.character_id, self.user_id, self.character_name, expires_at))
                punishment_scheduled = True
        
        if warning_message:
            embed.description += warning_message
        
        punishment_channel_id = utils.safe_int(db.get_setting('punishment_channel', ''))
        if punishment_channel_id:
            punishment_channel = interaction.guild.get_channel(punishment_channel_id)
            if punishment_channel:
                msg = await punishment_channel.send(embed=embed)
                asyncio.create_task(delete_message_after_delay(msg, 10))
        
        if user:
            try:
                user_embed = Embed(title="⚠️ Вам выдано наказание", description=f"**Персонаж:** {self.character_name}\n**Нарушений:** {violation_count}\n**Всего:** {new_total}\n**Причина:** {reason}", color=Color.red())
                if warning_message:
                    user_embed.description += warning_message
                await user.send(embed=user_embed)
            except: pass
        
        log_channel_id = utils.safe_int(db.get_setting('log_channel', ''))
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(embed=embed)
        
        if punishment_scheduled:
            await interaction.response.send_message(f"✅ Наказание выдано! Всего: {new_total}\n⚠️ 3 нарушения — 24 часа на снятие!", ephemeral=True, delete_after=30)
        else:
            await interaction.response.send_message(f"✅ Наказание выдано! Всего: {new_total}", ephemeral=True, delete_after=10)


class RemovePunishmentModal(Modal):
    def __init__(self, punishment_id: int, character_name: str):
        super().__init__(title="📋 Снятие наказания", timeout=None)
        self.punishment_id = punishment_id
        self.character_name = character_name
        self.add_item(TextInput(label="📝 Причина снятия", placeholder="Укажите причину...", style=TextStyle.paragraph, required=True, max_length=500))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.db
        reason = self.children[0].value
        
        db.cursor.execute('SELECT character_id, violation_count, issuer_id FROM punishments WHERE id = ?', (self.punishment_id,))
        row = db.cursor.fetchone()
        
        if not row:
            await interaction.response.send_message("❌ Наказание не найдено!", ephemeral=True, delete_after=5)
            return
        
        character_id, violation_count, issuer_id = row
        old_total = db.get_total_violations_by_character(character_id)
        db.remove_punishment(self.punishment_id)
        new_total = db.get_total_violations_by_character(character_id)
        
        character = db.get_character_by_id(character_id)
        user = interaction.guild.get_member(character['user_id']) if character else None
        issuer = interaction.guild.get_member(issuer_id)
        issuer_name = issuer.display_name if issuer else f"ID: {issuer_id}"
        
        embed = Embed(title="📋 Наказание снято", description=f"**Персонаж:** {self.character_name}\n**Игрок:** {user.mention if user else '?'}\n**Снято:** {violation_count}\n**Было:** {old_total}\n**Стало:** {new_total}\n**Причина:** {reason}\n**Снял:** {interaction.user.mention}", color=Color.green(), timestamp=discord.utils.utcnow())
        
        if new_total < 3:
            active_warning = db.get_active_warning(character_id)
            if active_warning:
                db.update_warning_status(active_warning['id'], 'resolved')
                embed.description += "\n\n✅ Предупреждение 3-го уровня снято!"
        
        punishment_channel_id = utils.safe_int(db.get_setting('punishment_channel', ''))
        if punishment_channel_id:
            punishment_channel = interaction.guild.get_channel(punishment_channel_id)
            if punishment_channel:
                msg = await punishment_channel.send(embed=embed)
                asyncio.create_task(delete_message_after_delay(msg, 10))
        
        if user:
            try:
                await user.send(embed=Embed(title="📋 Наказание снято", description=f"Снято: {violation_count}\nВсего теперь: {new_total}", color=Color.green()))
            except: pass
        
        log_channel_id = utils.safe_int(db.get_setting('log_channel', ''))
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(embed=embed)
        
        await interaction.response.send_message(f"✅ Наказание снято! Всего теперь: {new_total}", ephemeral=True, delete_after=10)


class TaskReportModal(Modal):
    def __init__(self, task_id: int, character_id: int, punishment_id: int):
        super().__init__(title="📝 Отчёт о выполнении задания", timeout=None)
        self.task_id = task_id
        self.character_id = character_id
        self.punishment_id = punishment_id
        
        self.add_item(TextInput(label="📎 Ссылки на скриншоты/видео", placeholder="https://imgur.com/... (обязательно)", required=True, max_length=500))
        self.add_item(TextInput(label="📝 Комментарий", placeholder="Опишите, что вы сделали...", style=TextStyle.paragraph, required=False, max_length=1000))

    async def on_submit(self, interaction: discord.Interaction):
        report_links = self.children[0].value
        report_comment = self.children[1].value if self.children[1].value else "Без комментария"
        
        embed = Embed(
            title="📝 Отчёт о выполнении задания",
            description=f"**Игрок:** {interaction.user.mention}\n**Задание ID:** {self.task_id}\n\n**📎 Ссылки:** {report_links}\n\n**📝 Комментарий:** {report_comment}",
            color=Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.set_footer(text="Ожидает проверки руководством")
        
        from views.punishments import TaskConfirmView
        view = TaskConfirmView()
        await interaction.channel.send(embed=embed, view=view)
        
        await interaction.response.send_message("✅ Отчёт отправлен! Ожидайте проверки.", ephemeral=True, delete_after=10)


class TaskRejectModal(Modal):
    def __init__(self, task_id: int, character_id: int, punishment_id: int, channel=None):
        super().__init__(title="❌ Отказ в выполнении задания", timeout=None)
        self.task_id = task_id
        self.character_id = character_id
        self.punishment_id = punishment_id
        self.channel = channel
        
        self.add_item(TextInput(label="📝 Причина отказа", placeholder="Укажите, почему задание не принято...", style=TextStyle.paragraph, required=True, max_length=500))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.db
        reason = self.children[0].value
        
        task = db.get_punishment_task(self.task_id)
        user = interaction.guild.get_member(task['user_id']) if task else None
        
        db.complete_task(self.task_id)
        
        await interaction.response.send_message("❌ Задание отклонено, наказание остаётся.", ephemeral=True, delete_after=10)
        
        if user:
            try:
                await user.send(embed=Embed(title="❌ Задание отклонено", description=f"**Причина:** {reason}\nНаказание остаётся.", color=Color.red()))
            except: pass
        
        log_channel_id = utils.safe_int(db.get_setting('log_channel', ''))
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(embed=Embed(title="📋 Отчёт ОТКЛОНЁН", description=f"Задание #{self.task_id}\nПроверил: {interaction.user.mention}\nПричина: {reason}", color=Color.red()))
        
        if self.channel:
            try:
                await self.channel.delete()
            except: pass