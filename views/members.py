import discord
import asyncio
from discord.ui import View, Button
from discord import ButtonStyle, Color, Embed
import utils


class MemberManagementView(View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="Статус добавления", style=ButtonStyle.primary, emoji="📊", row=0, custom_id="member_status")
    async def check_status_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_characters(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ У вас нет прав на просмотр статуса!", ephemeral=True, delete_after=20)
            return
        
        db = interaction.client.get_db(interaction.guild_id)
        guild = interaction.guild
        target_role_ids = db.get_character_reminder_roles()
        
        if not target_role_ids:
            await interaction.response.send_message("⚠️ Роли для проверки не настроены! Используйте настройки напоминаний.", ephemeral=True, delete_after=20)
            return
        
        users_need_reminder = db.get_users_who_need_reminder(target_role_ids, guild)
        users_added = []
        
        for role_id in target_role_ids:
            role = guild.get_role(role_id)
            if role:
                for member in role.members:
                    if db.has_added_characters(member.id):
                        users_added.append(member)
        
        embed = Embed(title="📊 Статус добавления персонажей", color=Color.blue(), timestamp=discord.utils.utcnow())
        
        added_text = "\n".join([f"✅ {user.display_name}" for user in users_added[:20]]) if users_added else "❌ Нет"
        if len(users_added) > 20:
            added_text += f"\n... и ещё {len(users_added) - 20}"
        embed.add_field(name=f"✅ Добавили персонажей ({len(users_added)})", value=added_text, inline=False)
        
        need_text = ""
        for u in users_need_reminder[:20]:
            need_text += f"⚠️ {u['user'].display_name} (напоминаний: {u['reminder_count']})\n"
        if not need_text:
            need_text = "✅ Все добавили!"
        if len(users_need_reminder) > 20:
            need_text += f"\n... и ещё {len(users_need_reminder) - 20}"
        embed.add_field(name=f"⚠️ Ещё не добавили ({len(users_need_reminder)})", value=need_text, inline=False)
        
        embed.set_footer(text="Используйте кнопку ниже для отправки напоминаний")
        
        view = View()
        send_btn = Button(label="Отправить напоминания всем", style=ButtonStyle.primary, emoji="📢", custom_id="send_reminders_from_status")
        
        async def send_reminders(interaction: discord.Interaction):
            if not utils.can_manage_characters(interaction.user, db):
                await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
                return
            await interaction.response.defer(ephemeral=True)
            
            chars_channel_id = db.get_setting('characters_channel_id', '')
            chars_channel = guild.get_channel(int(chars_channel_id)) if chars_channel_id else None
            channel_mention = chars_channel.mention if chars_channel else "канале управления персонажами"
            
            reminder_message = db.get_setting('character_reminder_message', '').format(channel=channel_mention)
            
            sent_count = 0
            for u in users_need_reminder:
                try:
                    await u['user'].send(reminder_message)
                    db.update_reminder_sent(u['user_id'])
                    sent_count += 1
                    await asyncio.sleep(0.5)
                except:
                    pass
            
            await interaction.followup.send(f"✅ Отправлено напоминаний: {sent_count}", ephemeral=True)
        
        send_btn.callback = send_reminders
        view.add_item(send_btn)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=60)

    @discord.ui.button(label="Напомнить всем", style=ButtonStyle.primary, emoji="📢", row=0, custom_id="member_broadcast")
    async def broadcast_reminder_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_characters(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ У вас нет прав на управление персонажами!", ephemeral=True, delete_after=20)
            return
        
        db = interaction.client.get_db(interaction.guild_id)
        guild = interaction.guild
        target_role_ids = db.get_character_reminder_roles()
        
        if not target_role_ids:
            await interaction.response.send_message("⚠️ Роли для проверки не настроены! Используйте настройки напоминаний.", ephemeral=True, delete_after=20)
            return
        
        users_need_reminder = db.get_users_who_need_reminder(target_role_ids, guild)
        
        if not users_need_reminder:
            await interaction.response.send_message("✅ Все участники уже добавили своих персонажей!", ephemeral=True, delete_after=20)
            return
        
        view = ConfirmBroadcastView(len(users_need_reminder))
        embed = Embed(title="📢 Подтверждение рассылки", description=f"Вы собираетесь отправить напоминание **{len(users_need_reminder)}** пользователям.\n\nЭто действие нельзя отменить. Продолжить?", color=Color.orange())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Настройки напоминаний", style=ButtonStyle.secondary, emoji="⚙️", row=1, custom_id="member_settings")
    async def reminder_settings_button(self, interaction: discord.Interaction, button: Button):
        if not utils.can_manage_settings(interaction.user, interaction.client.db):
            await interaction.response.send_message("❌ Только разработчик может изменять настройки!", ephemeral=True, delete_after=20)
            return
        db = interaction.client.get_db(interaction.guild_id)
        defaults = {
            'character_reminder_roles': db.get_setting('character_reminder_roles', ''),
            'character_reminder_interval': db.get_setting('character_reminder_interval', '24'),
            'character_reminder_enabled': db.get_setting('character_reminder_enabled', '1'),
            'character_reminder_message': db.get_setting('character_reminder_message', '📢 Уважаемый игрок! Вы до сих пор не добавили своих персонажей в базу данных гильдии. Пожалуйста, перейдите в канал {channel} и добавьте своих персонажей.')
        }
        from modals.member_modals import ReminderSettingsModal
        await interaction.response.send_modal(ReminderSettingsModal(defaults))

    @discord.ui.button(label="Назад", style=ButtonStyle.secondary, emoji="🔙", row=1, custom_id="member_back")
    async def back_button(self, interaction: discord.Interaction, button: Button):
        from views.settings import SettingsView
        embed = Embed(title="⚙️ Панель управления", description="Выберите раздел:", color=Color.blue())
        view = SettingsView()
        await interaction.response.edit_message(embed=embed, view=view)


class ConfirmBroadcastView(View):
    def __init__(self, count: int):
        super().__init__(timeout=30)
        self.count = count

    @discord.ui.button(label="Да, отправить", style=ButtonStyle.danger, emoji="✅", custom_id="confirm_broadcast_yes")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        
        db = interaction.client.get_db(interaction.guild_id)
        guild = interaction.guild
        target_role_ids = db.get_character_reminder_roles()
        users_need_reminder = db.get_users_who_need_reminder(target_role_ids, guild)
        
        chars_channel_id = db.get_setting('characters_channel_id', '')
        chars_channel = guild.get_channel(int(chars_channel_id)) if chars_channel_id else None
        channel_mention = chars_channel.mention if chars_channel else "канале управления персонажами"
        
        reminder_message = db.get_setting('character_reminder_message', '').format(channel=channel_mention)
        full_message = f"{reminder_message}\n\n📢 Напоминание от: {interaction.user.mention}"
        
        sent_count = 0
        failed_count = 0
        
        for user_data in users_need_reminder:
            try:
                await user_data['user'].send(full_message)
                db.update_reminder_sent(user_data['user_id'])
                sent_count += 1
                await asyncio.sleep(0.5)
            except:
                failed_count += 1
        
        embed = Embed(title="📢 Рассылка завершена", description=f"✅ Отправлено: {sent_count}\n❌ Не доставлено: {failed_count}", color=Color.green() if sent_count > 0 else Color.red(), timestamp=discord.utils.utcnow())
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.ui.button(label="Отмена", style=ButtonStyle.secondary, emoji="❌", custom_id="confirm_broadcast_no")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="❌ Рассылка отменена.", embed=None, view=None)