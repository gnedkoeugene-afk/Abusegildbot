# voice_welcome.py — ПОЛНЫЙ ФАЙЛ (ВСЁ РАБОТАЕТ)

import discord
from discord.ext import commands
from discord import app_commands, Embed, Color, ButtonStyle
from discord.ui import View, Button, Select, Modal, TextInput
import asyncio
import os
import json
import subprocess
import utils


class VoiceWelcome(commands.Cog):
    """Система голосового приветствия"""
    
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}
        self.sounds_dir = "sounds"
        self.config_file = "voice_config.json"
        self.ffmpeg_available = self.check_ffmpeg()
        
        os.makedirs(self.sounds_dir, exist_ok=True)
        self.config = self.load_config()
        
        print(f"🎤 VoiceWelcome загружен!")
        print(f"   FFmpeg: {'✅' if self.ffmpeg_available else '❌'}")
        print(f"   Звуков: {len(self.get_available_sounds())}")
    
    def check_ffmpeg(self):
        try:
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return True
        except:
            pass
        
        try:
            local_ffmpeg = os.path.join(os.getcwd(), 'ffmpeg')
            if os.path.exists(local_ffmpeg):
                result = subprocess.run([local_ffmpeg, '-version'], capture_output=True, text=True, timeout=5)
                return result.returncode == 0
        except:
            pass
        
        return False
    
    def load_config(self) -> dict:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_config(self):
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
    
    def get_volume(self, guild_id: int) -> float:
        guild_key = str(guild_id)
        if guild_key in self.config and 'volume' in self.config[guild_key]:
            volume = self.config[guild_key]['volume']
            if isinstance(volume, (int, float)) and 0.1 <= volume <= 1.0:
                return float(volume)
        return 0.5
    
    def get_user_sound(self, guild_id: int, user_id: int) -> str:
        guild_key = str(guild_id)
        user_key = str(user_id)
        
        if guild_key in self.config:
            if user_key in self.config[guild_key]:
                sound_path = self.config[guild_key][user_key]
                if os.path.exists(sound_path):
                    return sound_path
            if 'default' in self.config[guild_key]:
                sound_path = self.config[guild_key]['default']
                if os.path.exists(sound_path):
                    return sound_path
        
        default_path = os.path.join(self.sounds_dir, "default.mp3")
        if os.path.exists(default_path):
            return default_path
        
        return None
    
    def get_available_sounds(self) -> list:
        sounds = []
        if os.path.exists(self.sounds_dir):
            for file in os.listdir(self.sounds_dir):
                if file.endswith(('.mp3', '.wav', '.ogg', '.m4a', '.webm')):
                    sounds.append(file)
        return sorted(sounds)
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        if member.bot:
            return
        
        guild = member.guild
        
        if before.channel is None and after.channel is not None:
            if member.id == guild.owner_id:
                try:
                    member = await guild.fetch_member(member.id)
                except:
                    pass
            
            db = self.bot.get_db(guild.id)
            if not db:
                return
            
            voice_enabled = db.get_setting('voice_welcome_enabled', '0')
            if voice_enabled != '1':
                return
            
            sound_path = self.get_user_sound(guild.id, member.id)
            if not sound_path:
                return
            
            if guild.id in self.voice_clients:
                vc = self.voice_clients[guild.id]
                if vc and vc.is_connected():
                    return
            
            permissions = after.channel.permissions_for(guild.me)
            if not permissions.connect and member.id != guild.owner_id:
                return
            
            if guild.afk_channel and after.channel.id == guild.afk_channel.id:
                return
            
            try:
                voice_client = await after.channel.connect(timeout=10)
                self.voice_clients[guild.id] = voice_client
                
                if self.ffmpeg_available:
                    await asyncio.sleep(0.5)
                    try:
                        volume = self.get_volume(guild.id)
                        audio_source = discord.FFmpegPCMAudio(sound_path, options=f'-af "volume={volume}"')
                        voice_client.play(audio_source)
                        while voice_client.is_playing():
                            await asyncio.sleep(0.3)
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        print(f"❌ Ошибка звука: {e}")
                        await asyncio.sleep(2)
                else:
                    await asyncio.sleep(3)
                
                if voice_client.is_connected():
                    await voice_client.disconnect()
                
                if guild.id in self.voice_clients:
                    del self.voice_clients[guild.id]
                
            except Exception as e:
                print(f"❌ Ошибка: {e}")
                if guild.id in self.voice_clients:
                    del self.voice_clients[guild.id]
        
        elif before.channel is not None:
            for gid, vc in list(self.voice_clients.items()):
                if vc and vc.is_connected() and vc.channel == before.channel and not vc.is_playing():
                    humans = sum(1 for m in vc.channel.members if not m.bot)
                    if humans == 0:
                        await vc.disconnect()
                        del self.voice_clients[guild.id]
    
    def build_settings_embed(self, db, guild_id: int) -> Embed:
        enabled = db.get_setting('voice_welcome_enabled', '0') == '1'
        sounds = self.get_available_sounds()
        guild_key = str(guild_id)
        volume = self.get_volume(guild_id)
        
        embed = Embed(
            title="🎤 Войс-приветствие",
            description="Бот заходит в войс и проигрывает звук\nдля пользователей с назначенным звуком",
            color=Color.green() if enabled else Color.red()
        )
        
        embed.add_field(name="📌 Статус", value="✅ Включено" if enabled else "❌ Выключено", inline=True)
        embed.add_field(name="📁 Звуков", value=str(len(sounds)), inline=True)
        embed.add_field(name="🔧 FFmpeg", value="✅" if self.ffmpeg_available else "❌", inline=True)
        embed.add_field(name="🔉 Громкость", value=f"**{int(volume * 100)}%**", inline=True)
        
        if guild_key in self.config:
            settings = self.config[guild_key]
            if 'default' in settings:
                embed.add_field(name="🔊 По умолчанию", value=f"`{os.path.basename(settings['default'])}`", inline=True)
            
            personal = {k: v for k, v in settings.items() if k not in ['default', 'volume']}
            if personal:
                lines = [f"<@{uid}> → `{os.path.basename(path)}`" for uid, path in personal.items()]
                embed.add_field(name="👤 Персональные", value="\n".join(lines), inline=False)
        
        return embed


class VoiceSettingsView(View):
    def __init__(self, cog: VoiceWelcome, db, guild_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.db = db
        self.guild_id = guild_id
    
    @discord.ui.button(label="🔊 Вкл/Выкл", style=ButtonStyle.primary, emoji="🔊", row=0)
    async def toggle(self, interaction: discord.Interaction, button: Button):
        current = self.db.get_setting('voice_welcome_enabled', '0')
        new_value = "0" if current == "1" else "1"
        self.db.set_setting('voice_welcome_enabled', new_value)
        embed = self.cog.build_settings_embed(self.db, self.guild_id)
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🔊 По умолчанию", style=ButtonStyle.success, emoji="🔊", row=0)
    async def set_default(self, interaction: discord.Interaction, button: Button):
        sounds = self.cog.get_available_sounds()
        if not sounds:
            await interaction.response.send_message("❌ Нет звуков в папке `sounds/`!", ephemeral=True)
            return
        view = SoundSelectView(self.cog, self.guild_id, "default")
        await interaction.response.send_message("🔊 Выберите звук по умолчанию:", view=view, ephemeral=True)
    
    @discord.ui.button(label="👤 Персональный", style=ButtonStyle.primary, emoji="👤", row=1)
    async def set_personal(self, interaction: discord.Interaction, button: Button):
        sounds = self.cog.get_available_sounds()
        if not sounds:
            await interaction.response.send_message("❌ Нет звуков в папке `sounds/`!", ephemeral=True)
            return
        await interaction.response.send_modal(UserSelectModal(self.cog, self.guild_id))
    
    @discord.ui.button(label="🗑️ Удалить", style=ButtonStyle.danger, emoji="🗑️", row=1)
    async def delete_user(self, interaction: discord.Interaction, button: Button):
        guild_key = str(self.guild_id)
        if guild_key not in self.cog.config:
            await interaction.response.send_message("❌ Нет настроенных пользователей!", ephemeral=True)
            return
        
        personal = {k: v for k, v in self.cog.config[guild_key].items() if k not in ['default', 'volume']}
        if not personal:
            await interaction.response.send_message("❌ Нет персональных звуков!", ephemeral=True)
            return
        
        options = []
        for uid, path in personal.items():
            user = interaction.guild.get_member(int(uid))
            name = user.display_name if user else f"ID: {uid}"
            options.append(discord.SelectOption(label=name, value=uid, description=f"Звук: {os.path.basename(path)}", emoji="🗑️"))
        
        view = DeleteUserSoundView(self.cog, self.guild_id, options)
        await interaction.response.send_message("🗑️ Выберите пользователя для удаления:", view=view, ephemeral=True)
    
    @discord.ui.button(label="🔉 Громкость", style=ButtonStyle.secondary, emoji="🔉", row=2)
    async def set_volume(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(VolumeModal(self.cog, self.guild_id))
    
    @discord.ui.button(label="📋 Список", style=ButtonStyle.secondary, emoji="📋", row=2)
    async def list_sounds(self, interaction: discord.Interaction, button: Button):
        sounds = self.cog.get_available_sounds()
        guild_key = str(self.guild_id)
        volume = self.cog.get_volume(self.guild_id)
        
        embed = Embed(title="🎵 Звуки и настройки", color=Color.blue())
        embed.add_field(name="📁 Файлы", value="\n".join([f"`{s}`" for s in sounds]) if sounds else "Нет", inline=False)
        embed.add_field(name="🔉 Громкость", value=f"**{int(volume * 100)}%**", inline=True)
        
        if guild_key in self.cog.config:
            if 'default' in self.cog.config[guild_key]:
                embed.add_field(name="🔊 По умолчанию", value=f"`{os.path.basename(self.cog.config[guild_key]['default'])}`", inline=True)
            personal = {k: v for k, v in self.cog.config[guild_key].items() if k not in ['default', 'volume']}
            if personal:
                lines = [f"<@{uid}> → `{os.path.basename(path)}`" for uid, path in personal.items()]
                embed.add_field(name="👤 Персональные", value="\n".join(lines), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="🔙 Назад", style=ButtonStyle.danger, emoji="🔙", row=3)
    async def back(self, interaction: discord.Interaction, button: Button):
        from views.settings import SettingsView
        view = SettingsView()
        embed = Embed(title="⚙️ Панель управления", description="Выберите раздел:", color=Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)


class DeleteUserSoundView(View):
    def __init__(self, cog: VoiceWelcome, guild_id: int, options: list):
        super().__init__(timeout=60)
        self.cog = cog
        self.guild_id = guild_id
        
        select = Select(placeholder="Выберите пользователя для удаления", options=options[:25], custom_id="delete_user_sound")
        select.callback = self.on_select
        self.add_item(select)
    
    async def on_select(self, interaction: discord.Interaction):
        user_id = interaction.data['values'][0]
        guild_key = str(self.guild_id)
        
        if guild_key in self.cog.config and user_id in self.cog.config[guild_key]:
            sound_name = os.path.basename(self.cog.config[guild_key][user_id])
            del self.cog.config[guild_key][user_id]
            self.cog.save_config()
            await interaction.response.send_message(f"✅ Звук для <@{user_id}> (`{sound_name}`) удалён!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Пользователь не найден!", ephemeral=True)


class SoundSelectView(View):
    def __init__(self, cog: VoiceWelcome, guild_id: int, mode: str, user_id: int = None):
        super().__init__(timeout=60)
        self.cog = cog
        self.guild_id = guild_id
        self.mode = mode
        self.user_id = user_id
        
        sounds = cog.get_available_sounds()
        options = [discord.SelectOption(label=s, value=s, emoji="🎵") for s in sounds[:25]]
        
        select = Select(placeholder="Выберите звук", options=options, custom_id=f"sound_{mode}")
        select.callback = self.on_select
        self.add_item(select)
    
    async def on_select(self, interaction: discord.Interaction):
        sound_name = interaction.data['values'][0]
        sound_path = os.path.join(self.cog.sounds_dir, sound_name)
        
        guild_key = str(self.guild_id)
        if guild_key not in self.cog.config:
            self.cog.config[guild_key] = {}
        
        if self.mode == "default":
            self.cog.config[guild_key]['default'] = sound_path
            self.cog.save_config()
            await interaction.response.send_message(f"✅ Звук по умолчанию: `{sound_name}`", ephemeral=True)
        else:
            self.cog.config[guild_key][str(self.user_id)] = sound_path
            self.cog.save_config()
            await interaction.response.send_message(f"✅ Звук для <@{self.user_id}>: `{sound_name}`", ephemeral=True)


class UserSelectModal(Modal):
    def __init__(self, cog: VoiceWelcome, guild_id: int):
        super().__init__(title="👤 Выбор пользователя")
        self.cog = cog
        self.guild_id = guild_id
        
        self.add_item(TextInput(label="ID пользователя Discord (цифры)", placeholder="123456789012345678", required=True, max_length=20, min_length=17))
    
    async def on_submit(self, interaction: discord.Interaction):
        query = self.children[0].value.strip()
        
        if not query.isdigit():
            await interaction.response.send_message("❌ Введите **числовой ID**!\nКак узнать: Настройки → Режим разработчика → ПКМ → Копировать ID", ephemeral=True)
            return
        
        user_id = int(query)
        user = None
        
        user = interaction.guild.get_member(user_id)
        if not user:
            for member in interaction.guild.members:
                if member.id == user_id:
                    user = member
                    break
        if not user:
            try:
                user = await interaction.guild.fetch_member(user_id)
            except:
                pass
        if not user and user_id == interaction.guild.owner_id:
            user = interaction.guild.owner
        
        if not user:
            await interaction.response.send_message(f"❌ Пользователь с ID `{user_id}` не найден!", ephemeral=True)
            return
        
        sounds = self.cog.get_available_sounds()
        if not sounds:
            await interaction.response.send_message("❌ Нет звуков в папке `sounds/`!", ephemeral=True)
            return
        
        view = SoundSelectView(self.cog, self.guild_id, "personal", user.id)
        await interaction.response.send_message(f"🎵 Выберите звук для **{user.display_name}**:", view=view, ephemeral=True)


class VolumeModal(Modal):
    def __init__(self, cog: VoiceWelcome, guild_id: int):
        super().__init__(title="🔉 Громкость звука")
        self.cog = cog
        self.guild_id = guild_id
        
        current = cog.get_volume(guild_id)
        self.add_item(TextInput(label="Громкость (0.1 - 1.0)", placeholder=f"Текущая: {current} ({int(current * 100)}%)", default=str(current), required=True, max_length=3))
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            volume = float(self.children[0].value.strip().replace(',', '.'))
            if volume < 0.1 or volume > 1.0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Введите число от **0.1** до **1.0**!", ephemeral=True)
            return
        
        guild_key = str(self.guild_id)
        if guild_key not in self.cog.config:
            self.cog.config[guild_key] = {}
        self.cog.config[guild_key]['volume'] = volume
        self.cog.save_config()
        await interaction.response.send_message(f"✅ Громкость: **{int(volume * 100)}%**", ephemeral=True)


async def setup(bot):
    await bot.add_cog(VoiceWelcome(bot))
    print("✅ VoiceWelcome cog загружен")