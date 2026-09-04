# views/applications.py — ПОЛНЫЙ ФИНАЛЬНЫЙ ФАЙЛ (ИСПРАВЛЕННЫЙ)

import discord
import asyncio
from discord.ui import View, Button, Select
from discord import ButtonStyle, Color, Embed
from datetime import datetime
import utils
from constants import CLASS_SPECS, RAID_ROLE_NAMES
from helpers.functions import get_class_emoji


async def send_application_log(interaction, db, status, user, moderator, char_name, reason=None):
    """Отправить лог о заявке в канал логов"""
    try:
        log_channel_id = utils.safe_int(db.get_setting('log_channel', ''))
        if not log_channel_id:
            return
        
        log_channel = interaction.guild.get_channel(log_channel_id)
        if not log_channel:
            return
        
        if status == "accepted":
            color = Color.green()
            status_text = "✅ ПРИНЯТО"
        elif status == "rejected":
            color = Color.red()
            status_text = "❌ ОТКЛОНЕНО"
        elif status == "blacklisted":
            color = Color.dark_red()
            status_text = "🚫 ЧС"
        else:
            color = Color.blue()
            status_text = status
        
        embed = Embed(
            title="📝 Заявка в гильдию",
            description=f"**Статус:** {status_text}",
            color=color,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Пользователь", value=user.mention if user else "Неизвестно", inline=True)
        embed.add_field(name="👮 Модератор", value=moderator.mention, inline=True)
        embed.add_field(name="🎮 Персонаж", value=char_name, inline=True)
        
        if reason:
            embed.add_field(name="📝 Причина", value=reason[:500], inline=False)
        
        await log_channel.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка отправки лога: {e}")


class ApplyView(View):
    """Кнопка подачи заявки"""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Подать заявку", style=ButtonStyle.success, emoji="📝", custom_id="apply_button")
    async def apply_button(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        
        if db.is_blacklisted(interaction.user.id):
            await interaction.response.send_message("❌ Вы в чёрном списке!", ephemeral=True, delete_after=20)
            return
        
        member_role_ids = utils.get_role_ids_from_setting(db, 'member_role')
        for rid in member_role_ids:
            member_role = interaction.guild.get_role(rid)
            if member_role and member_role in interaction.user.roles:
                await interaction.response.send_message(
                    "❌ **Вы уже являетесь участником гильдии!**\n\n"
                    "🔹 **Добавить персонажа:** кнопка **'Добавить'** в разделе **'Мои персонажи'**\n"
                    "🔹 **Добавить специализацию:** кнопка **'➕ Специализация'** в разделе **'Мои персонажи'**\n"
                    "🔹 **Сменить основного:** кнопка **'Сменить основного'** в разделе **'Мои персонажи'**\n\n"
                    "Повторная подача заявки недоступна.",
                    ephemeral=True, delete_after=30
                )
                return
        
        existing_main = db.get_main_character(interaction.user.id)
        if existing_main:
            await interaction.response.send_message(
                "❌ **У вас уже есть персонаж в гильдии!**\n\n"
                "🔹 **Добавить твинка:** кнопка **'Добавить'** в разделе **'Мои персонажи'**\n"
                "🔹 **Добавить специализацию:** кнопка **'➕ Специализация'** в разделе **'Мои персонажи'**\n\n"
                "Повторная подача заявки недоступна.",
                ephemeral=True, delete_after=30
            )
            return
        
        can_submit, message, wait = db.can_submit_application(interaction.user.id)
        if not can_submit:
            await interaction.response.send_message(f"❌ {message}", ephemeral=True, delete_after=20)
            return
        
        view = ClassSelectView()
        embed = Embed(
            title="⚔️ Шаг 1/4 — Выберите класс",
            description="Укажите класс вашего персонажа:",
            color=Color.blue()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ClassSelectView(View):
    """Шаг 1: Выбор класса"""
    
    def __init__(self, is_twin: bool = False):
        super().__init__(timeout=120)
        self.selected_class = None
        self.is_twin = is_twin
        
        class_options = []
        for class_name in CLASS_SPECS.keys():
            class_options.append(discord.SelectOption(
                label=class_name, value=class_name,
                emoji=get_class_emoji(class_name)
            ))
        
        self.class_select = Select(placeholder="⚔️ Выберите класс", options=class_options, custom_id="class_select")
        self.class_select.callback = self.on_class_select
        self.add_item(self.class_select)
    
    async def on_class_select(self, interaction: discord.Interaction):
        self.selected_class = interaction.data['values'][0]
        
        db = interaction.client.get_db(interaction.guild_id)
        specs = CLASS_SPECS.get(self.selected_class, [])
        
        spec_options = []
        for spec in specs:
            role_key = db.get_setting(f"spec_role_{self.selected_class}_{spec}", 'mdd')
            role_name = RAID_ROLE_NAMES.get(role_key, role_key)
            spec_options.append(discord.SelectOption(
                label=spec, value=spec,
                description=f"Роль: {role_name}", emoji="🎯"
            ))
        
        view = SpecSelectView(self.selected_class, spec_options, self.is_twin)
        
        if self.is_twin:
            title = f"🎯 Добавление твинка — {self.selected_class}: выберите специализацию"
        else:
            title = f"🎯 Шаг 2/4 — {self.selected_class}: выберите специализацию"
        
        embed = Embed(title=title, description="Выберите одну специализацию:", color=Color.blue())
        await interaction.response.edit_message(embed=embed, view=view)


class SpecSelectView(View):
    """Шаг 2: Выбор специализации"""
    
    def __init__(self, class_name: str, spec_options: list, is_twin: bool = False):
        super().__init__(timeout=120)
        self.class_name = class_name
        self.is_twin = is_twin
        
        select = Select(placeholder="🎯 Выберите специализацию", options=spec_options, custom_id="spec_select")
        select.callback = self.on_spec_select
        self.add_item(select)
    
    async def on_spec_select(self, interaction: discord.Interaction):
        specialization = interaction.data['values'][0]
        db = interaction.client.get_db(interaction.guild_id)
        raid_role = db.get_setting(f"spec_role_{self.class_name}_{specialization}", 'mdd')
        
        if self.is_twin:
            await self.save_as_twin(interaction, specialization, raid_role)
        else:
            view = DaySelectView(self.class_name, specialization, raid_role)
            embed = Embed(
                title=f"📅 Шаг 3/4 — Выберите дни для рейдов",
                description=f"**Класс:** {self.class_name}\n**Специализация:** {specialization}\n\n"
                           f"В какие дни вы можете участвовать в рейдах?\nМожно выбрать несколько дней.",
                color=Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=view)
    
    async def save_as_twin(self, interaction: discord.Interaction, specialization: str, raid_role: str):
        from modals.character_modals import AddTwinModal
        modal = AddTwinModal(is_main=False)
        modal.class_name = self.class_name
        modal.specialization = specialization
        modal.raid_role = raid_role
        await interaction.response.send_modal(modal)


class DaySelectView(View):
    """Шаг 3: Выбор дней рейдов"""
    
    def __init__(self, class_name: str, specialization: str, raid_role: str):
        super().__init__(timeout=120)
        self.class_name = class_name
        self.specialization = specialization
        self.raid_role = raid_role
    
    @discord.ui.select(
        placeholder="📅 Выберите дни (можно несколько)",
        options=[
            discord.SelectOption(label="Понедельник", value="mon", emoji="📅"),
            discord.SelectOption(label="Вторник", value="tue", emoji="📅"),
            discord.SelectOption(label="Среда", value="wed", emoji="📅"),
            discord.SelectOption(label="Четверг", value="thu", emoji="📅"),
            discord.SelectOption(label="Пятница", value="fri", emoji="📅"),
            discord.SelectOption(label="Суббота", value="sat", emoji="📅"),
            discord.SelectOption(label="Воскресенье", value="sun", emoji="📅"),
        ],
        min_values=1, max_values=7, custom_id="select_days"
    )
    async def select_days(self, interaction: discord.Interaction, select: Select):
        selected_days = interaction.data['values']
        temp_data = {'available_days': ','.join(selected_days), 'specialization': self.specialization}
        
        from modals.application_modals import ApplicationModal
        modal = ApplicationModal(self.class_name, temp_data, self.raid_role)
        await interaction.response.send_modal(modal)


class RaidRoleSelectView(View):
    """Больше не используется"""
    pass


class ApplicationReviewView(View):
    def __init__(self, channel_id: int, user_id: int, app_id: int, app_data: dict):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.user_id = user_id
        self.app_id = app_id
        self.app_data = app_data

    def to_dict(self):
        return {
            'channel_id': self.channel_id,
            'user_id': self.user_id,
            'app_id': self.app_id,
            'app_data': self.app_data
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            channel_id=data['channel_id'],
            user_id=data['user_id'],
            app_id=data['app_id'],
            app_data=data['app_data']
        )

    @discord.ui.button(label="✅ Принять", style=ButtonStyle.success, emoji="✅", custom_id="app_accept")
    async def accept(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        if not utils.can_manage_applications(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        if interaction.response.is_done():
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            user = interaction.guild.get_member(self.user_id)
            if not user:
                await interaction.followup.send("❌ Пользователь не найден!", ephemeral=True)
                return
            
            db.update_application_status(self.app_id, "accepted", interaction.user.id)
            
            char_name = self.app_data.get('character_name', 'Unknown')
            char_class = self.app_data.get('class_spec', 'Unknown')
            char_spec = self.app_data.get('specialization', 'Не указана')
            char_ilvl = int(self.app_data.get('item_level', 0))
            char_profile = self.app_data.get('profile_url', '')
            char_role = self.app_data.get('raid_role', 'mdd')
            user_personal_name = self.app_data.get('real_name', user.display_name)
            
            char_data = {
                'character_name': char_name,
                'class_spec': char_class,
                'specialization': char_spec,
                'item_level': char_ilvl,
                'profile_url': char_profile,
                'raid_role': char_role,
                'is_main': 1
            }
            db.add_character(user.id, char_data)
            db.mark_characters_added(user.id)
            
            # Выдача ролей
            print(f"\n🔧 Выдача ролей для {user.display_name} ({user.name}):")
            
            await utils.remove_roles_from_setting(user, db, 'reject_role', "Заявка принята")
            await utils.remove_roles_from_setting(user, db, 'blacklist_role', "Заявка принята")
            await utils.remove_roles_from_setting(user, db, 'guest_role', "Заявка принята")
            await utils.remove_roles_from_setting(user, db, 'violator_role', "Заявка принята")
            
            success = await utils.add_roles_from_setting(user, db, 'member_role', "Заявка принята")
            if success:
                print(f"   ✅ Роль участника выдана успешно")
            else:
                print(f"   ⚠️ Не удалось выдать роль участника")
                guest_success = await utils.add_roles_from_setting(
                    user, db, 'guest_role', 
                    "Заявка принята (member_role не настроена)"
                )
                if guest_success:
                    print(f"   ✅ Выдана роль Гость (запасная)")
                else:
                    print(f"   ❌ Не удалось выдать даже гостя!")
            
            # Никнейм
            try:
                new_nick = f"{char_name}┆{user_personal_name}"
                if len(new_nick) > 32:
                    max_personal_len = 32 - len(char_name) - 3
                    if max_personal_len > 0:
                        new_nick = f"{char_name}┆{user_personal_name[:max_personal_len]}"
                    else:
                        new_nick = f"{char_name[:15]}┆{user_personal_name[:12]}"
                
                await user.edit(nick=new_nick)
                print(f"   ✅ Никнейм изменен на: {new_nick}")
            except Exception as e:
                print(f"   ⚠️ Не удалось изменить никнейм: {e}")
            
            db.add_log("✅ Заявка принята", interaction.user.id, user.id, f"Персонаж: {char_name}")
            await send_application_log(interaction, db, "accepted", user, interaction.user, char_name)
            
            # Архив
            try:
                archive_channel_id = utils.safe_int(db.get_setting('archive_channel', ''))
                if archive_channel_id:
                    archive_channel = interaction.guild.get_channel(archive_channel_id)
                    if archive_channel:
                        app_channel = interaction.guild.get_channel(self.channel_id)
                        if app_channel:
                            async for msg in app_channel.history(limit=5):
                                if msg.author == interaction.client.user and msg.embeds:
                                    e = msg.embeds[0]
                                    ae = Embed(
                                        title=f"📁 Архив: {e.title}",
                                        description=e.description or "",
                                        color=Color.green(),
                                        timestamp=datetime.now()
                                    )
                                    for f in e.fields:
                                        ae.add_field(name=f.name, value=f.value, inline=f.inline)
                                    ae.add_field(name="✅ Статус", value=f"Принята | {interaction.user.mention}", inline=False)
                                    ae.set_footer(text=f"Архивировано | ID: {self.app_id}")
                                    await archive_channel.send(embed=ae)
                                    break
            except:
                pass
            
            # ЛС уведомление
            try:
                embed = Embed(
                    title="✅ Заявка принята!",
                    description=f"**Сервер:** {interaction.guild.name}\n"
                               f"**Персонаж:** {char_name}\n"
                               f"**Принял:** {interaction.user.mention}",
                    color=Color.green()
                )
                await user.send(embed=embed)
            except:
                pass
            
            await interaction.followup.send(
                f"✅ Заявка принята!\n"
                f"👤 **{user_personal_name}**\n"
                f"🎮 **{char_name}** ({char_class}, {char_spec})\n"
                f"💎 **{char_ilvl}** iLvl",
                ephemeral=True
            )
            
            try:
                if interaction.message:
                    embed = interaction.message.embeds[0]
                    embed.color = Color.green()
                    embed.set_footer(text=f"✅ Принято | {interaction.user.display_name}")
                    await interaction.message.edit(embed=embed, view=None)
            except:
                pass
            
            try:
                await asyncio.sleep(3)
                await interaction.channel.delete()
            except:
                pass
            
        except Exception as e:
            print(f"❌ Ошибка принятия заявки: {e}")
            try:
                await interaction.followup.send(f"❌ Ошибка: {str(e)[:100]}", ephemeral=True)
            except:
                pass

    @discord.ui.button(label="❌ Отклонить", style=ButtonStyle.danger, emoji="❌", custom_id="app_reject")
    async def reject(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        if not utils.can_manage_applications(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        if interaction.response.is_done():
            return
        
        from modals.application_modals import RejectModal
        await interaction.response.send_modal(
            RejectModal(self.app_id, self.user_id, self.channel_id)
        )

    @discord.ui.button(label="🚫 ЧС", style=ButtonStyle.secondary, emoji="🚫", custom_id="app_blacklist")
    async def blacklist(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        if not utils.can_manage_applications(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True)
            return
        
        if interaction.response.is_done():
            return
        
        from modals.application_modals import BlacklistModal
        await interaction.response.send_modal(
            BlacklistModal(self.app_id, self.user_id, self.channel_id)
        )
