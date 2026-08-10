# views/voice_control.py — ПОЛНЫЙ ГОТОВЫЙ ФАЙЛ

import discord
from discord.ext import commands
from discord import app_commands, Embed, Color, ButtonStyle
from discord.ui import View, Button, Select, Modal, TextInput
import asyncio
import utils


class VoiceControl(commands.Cog):
    """Система контроля голосового канала во время рейда"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_controls = {}
        print("🎙️ VoiceControl загружен!")
    
    def get_unmuted_ids(self, channel: discord.VoiceChannel, guild_id: int, raid_leader_id: int) -> list:
        """Получить список кого не мутить"""
        unmuted = [raid_leader_id]
        guild = channel.guild
        db = self.bot.get_db(guild_id)
        if not db:
            return unmuted
        
        # Роли которые всегда говорят
        role_keys = ['guild_master', 'vice_master', 'raid_leader', 'senior_officer_role', 'officer_role']
        
        for member in channel.members:
            if member.bot or member.id in unmuted:
                continue
            for role_key in role_keys:
                role_id = utils.safe_int(db.get_setting(role_key, ''))
                if role_id:
                    role = guild.get_role(role_id)
                    if role and role in member.roles:
                        unmuted.append(member.id)
                        break
        
        # Дополнительные роли/пользователи из пресета
        always_roles_str = db.get_setting('pull_always_roles', '')
        always_users_str = db.get_setting('pull_always_users', '')
        always_roles = [int(r) for r in always_roles_str.split(',') if r.strip().isdigit()] if always_roles_str else []
        always_users = [int(u) for u in always_users_str.split(',') if u.strip().isdigit()] if always_users_str else []
        
        for member in channel.members:
            if member.bot or member.id in unmuted:
                continue
            for role_id in always_roles:
                role = guild.get_role(role_id)
                if role and role in member.roles:
                    unmuted.append(member.id)
                    break
            if member.id in always_users and member.id not in unmuted:
                unmuted.append(member.id)
        
        return unmuted
    
    async def mute_all_except(self, channel: discord.VoiceChannel, unmuted_ids: list):
        """Замутить всех кроме указанных"""
        muted_count = 0
        for member in channel.members:
            if member.bot:
                continue
            if member.id in unmuted_ids:
                try:
                    if member.voice and member.voice.mute:
                        await member.edit(mute=False)
                except:
                    pass
            else:
                try:
                    if member.voice and not member.voice.mute:
                        await member.edit(mute=True)
                        muted_count += 1
                except:
                    pass
        return muted_count
    
    async def unmute_all(self, channel: discord.VoiceChannel):
        """Размутить всех"""
        count = 0
        for member in channel.members:
            if member.bot:
                continue
            try:
                if member.voice and member.voice.mute:
                    await member.edit(mute=False)
                    count += 1
            except:
                pass
        return count
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """Автоматически мутить новых участников во время боя"""
        guild = member.guild
        if guild.id not in self.active_controls:
            return
        control = self.active_controls[guild.id]
        if after.channel and after.channel.id == control['channel'].id:
            if member.id not in control['unmuted_users']:
                try:
                    await member.edit(mute=True, reason="Бой идёт")
                except:
                    pass

class PullBattleView(View):
    """Кнопка НАЧАТЬ БОЙ"""
    def __init__(self, cog, guild_id: int, raid_leader_id: int, channel: discord.VoiceChannel):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id
        self.raid_leader_id = raid_leader_id
        self.channel = channel
    
    @discord.ui.button(label="🔇 НАЧАТЬ БОЙ", style=ButtonStyle.danger, emoji="⚔️", row=0)
    async def start(self, interaction: discord.Interaction, button: Button):
        """Начать бой — замутить всех кроме командования"""
        if interaction.user.id != self.raid_leader_id:
            await interaction.response.send_message("❌ Только рейд-лидер может начать бой!", ephemeral=True)
            return
        
        if self.guild_id in self.cog.active_controls:
            await interaction.response.send_message("❌ Бой уже идёт!", ephemeral=True)
            return
        
        channel = interaction.guild.get_channel(self.channel.id)
        if not channel:
            await interaction.response.send_message("❌ Канал не найден!", ephemeral=True)
            return
        
        # Получаем кого не мутить
        unmuted_ids = self.cog.get_unmuted_ids(channel, self.guild_id, self.raid_leader_id)
        
        # Мутим всех
        muted_count = await self.cog.mute_all_except(channel, unmuted_ids)
        
        # Сохраняем состояние
        self.cog.active_controls[self.guild_id] = {
            'channel': channel,
            'unmuted_users': unmuted_ids,
            'raid_leader': self.raid_leader_id,
            'started_at': discord.utils.utcnow()
        }
        
        # Имена говорящих
        unmuted_names = []
        for uid in unmuted_ids:
            member = interaction.guild.get_member(uid)
            if member:
                unmuted_names.append(f"🎤 {member.display_name}")
        
        # Обновляем сообщение
        embed = Embed(
            title="⚔️ БОЙ ИДЁТ!",
            description=f"**Канал:** {channel.name}\n**Замучено:** {muted_count} чел.",
            color=Color.red()
        )
        embed.add_field(
            name=f"🎤 Говорят ({len(unmuted_names)})",
            value="\n".join(unmuted_names) if unmuted_names else "Никто",
            inline=True
        )
        embed.set_footer(text="Нажмите 🔊 ЗАВЕРШИТЬ БОЙ чтобы размутить всех")
        
        new_view = PullEndView(self.cog, self.guild_id, self.raid_leader_id, channel)
        self.cog.bot.add_view(new_view)
        await interaction.response.edit_message(embed=embed, view=new_view)


class PullEndView(View):
    """Кнопка ЗАВЕРШИТЬ БОЙ"""
    def __init__(self, cog, guild_id: int, raid_leader_id: int, channel: discord.VoiceChannel):
        super().__init__(timeout=None)
        self.cog = cog
        self.guild_id = guild_id
        self.raid_leader_id = raid_leader_id
        self.channel = channel
    
    @discord.ui.button(label="🔊 ЗАВЕРШИТЬ БОЙ", style=ButtonStyle.success, emoji="✅", row=0)
    async def end(self, interaction: discord.Interaction, button: Button):
        """Завершить бой — размутить всех"""
        if interaction.user.id != self.raid_leader_id:
            await interaction.response.send_message("❌ Только рейд-лидер!", ephemeral=True)
            return
        
        channel = interaction.guild.get_channel(self.channel.id)
        if not channel:
            await interaction.response.send_message("❌ Канал не найден!", ephemeral=True)
            return
        
        # Размучиваем всех
        count = await self.cog.unmute_all(channel)
        
        # Удаляем состояние
        if self.guild_id in self.cog.active_controls:
            del self.cog.active_controls[self.guild_id]
        
        # Обновляем сообщение
        embed = Embed(
            title="✅ БОЙ ЗАВЕРШЁН!",
            description=f"**Размучено:** {count} чел.\n**Канал:** {channel.name}",
            color=Color.green()
        )
        embed.add_field(
            name="⚡ Готово",
            value="Нажмите 🔇 НАЧАТЬ БОЙ для следующей попытки",
            inline=False
        )
        
        new_view = PullBattleView(self.cog, self.guild_id, self.raid_leader_id, channel)
        self.cog.bot.add_view(new_view)
        await interaction.response.edit_message(embed=embed, view=new_view)
    
    @discord.ui.button(label="🔄 Обновить", style=ButtonStyle.secondary, emoji="🔄", row=1)
    async def refresh(self, interaction: discord.Interaction, button: Button):
        """Обновить список участников"""
        if self.guild_id not in self.cog.active_controls:
            await interaction.response.send_message("❌ Нет активного боя!", ephemeral=True)
            return
        
        control = self.cog.active_controls[self.guild_id]
        channel = interaction.guild.get_channel(self.channel.id)
        if not channel:
            return
        
        unmuted_list = []
        muted_list = []
        for member in channel.members:
            if member.bot:
                continue
            if member.id in control['unmuted_users']:
                unmuted_list.append(f"🎤 {member.display_name}")
            else:
                muted_list.append(f"🔇 {member.display_name}")
        
        embed = Embed(title="⚔️ БОЙ ИДЁТ!", color=Color.red())
        embed.add_field(name=f"🎤 Говорят", value="\n".join(unmuted_list) or "Никто", inline=True)
        embed.add_field(name=f"🔇 Замучены", value="\n".join(muted_list[:15]) or "Никто", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)


class AlwaysSpeakModal(Modal):
    """Модальное окно для настройки дополнительных ролей"""
    def __init__(self, cog, guild_id: int, always_roles: str, always_users: str):
        super().__init__(title="👑 Дополнительные роли/пользователи")
        self.cog = cog
        self.guild_id = guild_id
        
        self.add_item(TextInput(
            label="ID дополнительных ролей (через запятую)",
            placeholder="123456789, 987654321",
            default=always_roles,
            required=False,
            max_length=200
        ))
        self.add_item(TextInput(
            label="ID дополнительных пользователей",
            placeholder="111222333, 444555666",
            default=always_users,
            required=False,
            max_length=200
        ))
    
    async def on_submit(self, interaction: discord.Interaction):
        """Сохранить настройки"""
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
            return
        
        roles_str = self.children[0].value.strip()
        users_str = self.children[1].value.strip()
        
        db.set_setting('pull_always_roles', roles_str)
        db.set_setting('pull_always_users', users_str)
        
        roles_count = len([r for r in roles_str.split(',') if r.strip().isdigit()]) if roles_str else 0
        users_count = len([u for u in users_str.split(',') if u.strip().isdigit()]) if users_str else 0
        
        await interaction.response.send_message(
            f"✅ Сохранено!\n"
            f"🎭 Доп. ролей: **{roles_count}**\n"
            f"👤 Доп. пользователей: **{users_count}**\n\n"
            f"Они будут говорить вместе с Глава/Зам/РЛ/Ст.Офицер/Офицер",
            ephemeral=True
        )


async def setup(bot):
    """Загрузка кога"""
    await bot.add_cog(VoiceControl(bot))
    print("✅ VoiceControl cog загружен")