# views/punishments.py — ПОЛНЫЙ ФАЙЛ С ИСПРАВЛЕНИЯМИ

import discord
import asyncio
import random
from datetime import datetime, timedelta
from discord.ui import View, Button, Select
from discord import ButtonStyle, Color, Embed
import utils
from constants import RAID_ROLE_NAMES


class PunishmentMainView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Выдать наказание", style=ButtonStyle.danger, emoji="⚠️", row=0, custom_id="punish_main_btn")
    async def punish(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        if not utils.can_issue_punishments(interaction.user, db):
            await interaction.response.send_message("❌ У вас нет прав на выдачу наказаний!", ephemeral=True, delete_after=5)
            return
        from modals.punishment_modals import PunishmentSearchModal
        await interaction.response.send_modal(PunishmentSearchModal())

    @discord.ui.button(label="Снять наказание", style=ButtonStyle.primary, emoji="📋", row=0, custom_id="remove_punishment_btn")
    async def remove_punishment(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        if not utils.can_remove_punishments(interaction.user, db):
            await interaction.response.send_message("❌ Только Глава гильдии, Зам. главы или Рейд-лидер могут снимать наказания!", ephemeral=True, delete_after=5)
            return
        from modals.punishment_modals import PunishmentRemoveSearchModal
        await interaction.response.send_modal(PunishmentRemoveSearchModal())

    @discord.ui.button(label="Выполнить задание", style=ButtonStyle.success, emoji="📝", row=1, custom_id="do_task_btn")
    async def do_task(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        characters = db.get_user_characters(interaction.user.id)
        
        chars_with_punishments = []
        for char in characters:
            total = db.get_total_violations_by_character(char['id'])
            if total > 0:
                chars_with_punishments.append({
                    'character_id': char['id'],
                    'character_name': char['character_name'],
                    'user_id': interaction.user.id,
                    'user_name': interaction.user.display_name,
                    'is_main': char['is_main'],
                    'violations': total,
                    'class_spec': char['class_spec'],
                    'raid_role': char.get('raid_role', 'mdd')
                })
        
        if not chars_with_punishments:
            await interaction.response.send_message("✅ У вас нет персонажей с активными наказаниями!", ephemeral=True, delete_after=20)
            return
        
        if len(chars_with_punishments) == 1:
            await show_task_selection(interaction, chars_with_punishments[0])
        else:
            view = PunishmentSelectView(chars_with_punishments, is_removing=False, for_task=True)
            embed = Embed(title="📝 Выбор персонажа для задания", description="Выберите персонажа:", color=Color.blue())
            for i, char in enumerate(chars_with_punishments[:10], 1):
                status_emoji = "⭐" if char['is_main'] else "🔄"
                embed.add_field(name=f"{i}. {status_emoji} {char['character_name']}", value=f"⚠️ {char['violations']} нарушений", inline=True)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="📊 Статистика наказаний", style=ButtonStyle.secondary, emoji="📊", row=1, custom_id="punishment_stats_btn")
    async def punishment_stats(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        if not utils.can_manage_characters(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=5)
            return
        
        guild = interaction.guild
        
        all_characters = []
        for member in guild.members:
            chars = db.get_user_characters(member.id)
            for char in chars:
                total = db.get_total_violations_by_character(char['id'])
                if total > 0:
                    all_characters.append({
                        'character_name': char['character_name'],
                        'user_name': member.display_name,
                        'violations': total,
                        'is_main': char['is_main']
                    })
        
        all_characters.sort(key=lambda x: x['violations'], reverse=True)
        
        embed = Embed(title="📊 Статистика наказаний", color=Color.blue())
        if not all_characters:
            embed.description = "📭 Нет наказаний в гильдии."
        else:
            text = ""
            for i, char in enumerate(all_characters[:15], 1):
                main_tag = "⭐ " if char['is_main'] else "🔄 "
                text += f"{i}. {main_tag}**{char['character_name']}** - {char['user_name']} - {char['violations']} нар.\n"
            embed.add_field(name="🏆 Топ нарушителей", value=text, inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=60)


class PunishmentSelectView(View):
    def __init__(self, characters: list, is_removing: bool = False, for_task: bool = False):
        super().__init__(timeout=60)
        self.characters = characters
        self.is_removing = is_removing
        self.for_task = for_task
        
        for char in characters[:10]:
            button = Button(
                label=f"{char['character_name']} ({char['user_name']})",
                style=ButtonStyle.primary if not is_removing else ButtonStyle.success,
                custom_id=f"select_{char['character_id']}",
                emoji="⭐" if char['is_main'] else "🔄"
            )
            button.callback = self.create_callback(char)
            self.add_item(button)
        
        cancel_btn = Button(label="❌ Отмена", style=ButtonStyle.danger, custom_id="cancel_select")
        cancel_btn.callback = self.cancel_callback
        self.add_item(cancel_btn)
    
    def create_callback(self, character):
        async def callback(interaction: discord.Interaction):
            db = interaction.client.get_db(interaction.guild_id)
            if not db:
                await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
                return
            
            if self.is_removing:
                punishments = db.get_punishments_by_character(character['character_id'])
                await show_punishment_list(interaction, character, punishments)
            elif self.for_task:
                await show_task_selection(interaction, character)
            else:
                from modals.punishment_modals import PunishmentModalNew
                await interaction.response.send_modal(PunishmentModalNew(character['character_id'], character['character_name'], character['user_id']))
        return callback
    
    async def cancel_callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="❌ Отменено.", embed=None, view=None)


async def show_task_selection(interaction, character):
    db = interaction.client.get_db(interaction.guild_id)
    if not db:
        await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
        return
    
    available_tasks = db.get_all_tasks()
    
    if not available_tasks:
        await interaction.response.send_message("❌ Задания не настроены!", ephemeral=True, delete_after=20)
        return
    
    task_text = random.choice(available_tasks)
    punishments = db.get_punishments_by_character(character['character_id'])
    
    if not punishments:
        await interaction.response.send_message("❌ Нет наказаний!", ephemeral=True, delete_after=10)
        return
    
    oldest_punishment = punishments[-1]
    task_id = db.create_punishment_task(character['user_id'], character['character_id'], oldest_punishment['id'], task_text)
    
    category = None
    cat_id = utils.safe_int(db.get_setting('tasks_category', ''))
    if cat_id:
        category = interaction.guild.get_channel(cat_id)
    if not category:
        category = await interaction.guild.create_category_channel("📝 Задания")
        db.set_setting('tasks_category', str(category.id))
    
    overwrites = {
        interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
    }
    for role_id in db.get_reviewer_roles():
        role = interaction.guild.get_role(role_id)
        if role:
            overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    
    channel = await interaction.guild.create_text_channel(f"📝-задание-{task_id}", category=category, overwrites=overwrites)
    db.update_task_channel(task_id, channel.id)
    
    embed = Embed(
        title="📝 Задание для снятия наказания",
        description=f"**Игрок:** {interaction.user.mention}\n**Персонаж:** {character['character_name']}\n\n**Задание:**\n{task_text}\n\nНажмите **✅ Готово** когда выполните.",
        color=Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    
    view = TaskCompleteView()
    await channel.send(embed=embed, view=view)
    
    await interaction.response.send_message(f"✅ Канал создан: {channel.mention}", ephemeral=True, delete_after=10)


async def show_punishment_list(interaction, character, punishments):
    if not punishments:
        await interaction.response.send_message(f"✅ Нет активных наказаний.", ephemeral=True, delete_after=10)
        return
    
    options = []
    for p in punishments[:25]:
        issuer = interaction.guild.get_member(p['issuer_id'])
        issuer_name = issuer.display_name if issuer else f"ID: {p['issuer_id']}"
        options.append(discord.SelectOption(label=f"#{p['id']} - {p['violation_count']} нар.", value=str(p['id']), description=f"{p['reason'][:50]}... | {issuer_name}", emoji="📋"))
    
    select = Select(placeholder="📋 Выберите наказание для снятия", options=options, custom_id="select_punishment_to_remove")
    
    async def select_callback(interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        punishment_id = int(interaction.data['values'][0])
        from modals.punishment_modals import RemovePunishmentModal
        await interaction.response.send_modal(RemovePunishmentModal(punishment_id, character['character_name']))
    
    select.callback = select_callback
    
    view = View(timeout=60)
    view.add_item(select)
    cancel_btn = Button(label="Отмена", style=ButtonStyle.secondary, custom_id="cancel_remove")
    async def cancel_callback(interaction: discord.Interaction):
        await interaction.response.edit_message(content="Отменено.", embed=None, view=None)
    cancel_btn.callback = cancel_callback
    view.add_item(cancel_btn)
    
    embed = Embed(title=f"Наказания: {character['character_name']}", description=f"Всего: {sum(p['violation_count'] for p in punishments)}", color=Color.orange())
    for p in punishments[:10]:
        issuer = interaction.guild.get_member(p['issuer_id'])
        issuer_name = issuer.display_name if issuer else f"ID: {p['issuer_id']}"
        embed.add_field(name=f"⚠️ #{p['id']}", value=f"Нарушений: {p['violation_count']}\n{p['reason'][:100]}\nВыдал: {issuer_name}", inline=False)
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=120)


class TaskCompleteView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Готово (отправить отчёт)", style=ButtonStyle.success, emoji="✅", custom_id="task_complete_fixed")
    async def complete_button(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        task = db.cursor.execute(
            'SELECT id, character_id, punishment_id FROM punishment_tasks WHERE channel_id = ? AND status = "pending"',
            (interaction.channel_id,)
        ).fetchone()
        
        if not task:
            await interaction.response.send_message("❌ Задание не найдено в БД!", ephemeral=True, delete_after=10)
            return
        
        task_id, character_id, punishment_id = task
        from modals.punishment_modals import TaskReportModal
        await interaction.response.send_modal(TaskReportModal(task_id, character_id, punishment_id))


class TaskConfirmView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Принять (задание выполнено)", style=ButtonStyle.success, emoji="✅", custom_id="task_accept_fixed")
    async def accept_button(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        if not utils.can_remove_punishments(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return
        
        task = db.cursor.execute(
            'SELECT id, character_id, punishment_id, user_id FROM punishment_tasks WHERE channel_id = ? AND status = "pending"',
            (interaction.channel_id,)
        ).fetchone()
        
        if not task:
            await interaction.response.send_message("❌ Задание не найдено!", ephemeral=True, delete_after=10)
            return
        
        task_id, character_id, punishment_id, user_id = task
        user = interaction.guild.get_member(user_id)
        
        db.remove_punishment(punishment_id)
        db.complete_task(task_id)
        
        await interaction.response.send_message("✅ Наказание снято!", ephemeral=True, delete_after=5)
        
        if user:
            try:
                await user.send(embed=Embed(title="✅ Задание принято! Наказание снято", description=f"Проверил: {interaction.user.display_name}", color=Color.green()))
            except: pass
        
        log_channel_id = utils.safe_int(db.get_setting('log_channel', ''))
        if log_channel_id:
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(embed=Embed(title="📋 Отчёт ПРИНЯТ", description=f"Задание #{task_id}\nПроверил: {interaction.user.mention}", color=Color.green()))
        
        try:
            await interaction.channel.delete()
        except: pass

    @discord.ui.button(label="Отклонить (не выполнено)", style=ButtonStyle.danger, emoji="❌", custom_id="task_reject_fixed")
    async def reject_button(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        if not utils.can_remove_punishments(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return
        
        task = db.cursor.execute(
            'SELECT id, character_id, punishment_id FROM punishment_tasks WHERE channel_id = ? AND status = "pending"',
            (interaction.channel_id,)
        ).fetchone()
        
        if not task:
            await interaction.response.send_message("❌ Задание не найдено!", ephemeral=True, delete_after=10)
            return
        
        task_id, character_id, punishment_id = task
        from modals.punishment_modals import TaskRejectModal
        await interaction.response.send_modal(TaskRejectModal(task_id, character_id, punishment_id, interaction.channel))


async def schedule_punishment_after_delay(interaction, character_id, user_id, character_name, expires_at):
    async def punishment_task():
        await asyncio.sleep(24 * 3600)
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            return
        active_warning = db.get_active_warning(character_id)
        if active_warning:
            guild = interaction.guild
            user = guild.get_member(user_id)
            if user:
                try:
                    roles_to_remove = [role for role in user.roles if role.name != "@everyone"]
                    for role in roles_to_remove:
                        try:
                            await user.remove_roles(role, reason="3 нарушения не сняты")
                        except: pass
                    
                    await utils.add_roles_from_setting(user, db, 'guest_role', "3 нарушения - гость")
                    await utils.add_roles_from_setting(user, db, 'violator_role', "3 нарушения - нарушитель")
                    
                    log_channel_id = utils.safe_int(db.get_setting('log_channel', ''))
                    if log_channel_id:
                        log_channel = guild.get_channel(log_channel_id)
                        if log_channel:
                            await log_channel.send(embed=Embed(
                                title="⚠️ Нарушение правил",
                                description=f"**Игрок:** {user.mention}\n**Персонаж:** {character_name}\n**Действие:** Сняты все роли, выданы роли Гость и Нарушитель",
                                color=Color.red()
                            ))
                except Exception as e:
                    print(f"Ошибка при снятии ролей: {e}")
    asyncio.create_task(punishment_task())