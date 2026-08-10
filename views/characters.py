import discord
import asyncio
from discord.ui import View, Button, Select, Modal, TextInput
from discord import ButtonStyle, Color, Embed, TextStyle
from datetime import datetime
import utils
from constants import RAID_ROLE_NAMES, CLASS_SPECS
from helpers.functions import get_class_emoji


# ===================== ЛОГИРОВАНИЕ =====================
async def send_main_change_log(interaction, db, status, user, moderator, old_char, new_char, reason=None):
    """Отправить лог о смене основного персонажа в канал логов"""
    try:
        log_channel_id = utils.safe_int(db.get_setting('log_channel', ''))
        if not log_channel_id:
            return
        
        log_channel = interaction.guild.get_channel(log_channel_id)
        if not log_channel:
            return
        
        if status == "approved":
            color = Color.green()
            status_text = "✅ ОДОБРЕНО"
        elif status == "rejected":
            color = Color.red()
            status_text = "❌ ОТКЛОНЕНО"
        else:
            color = Color.blue()
            status_text = status
        
        embed = Embed(
            title="🔄 Смена основного персонажа",
            description=f"**Статус:** {status_text}",
            color=color,
            timestamp=datetime.now()
        )
        
        embed.add_field(name="👤 Пользователь", value=user.mention if user else "Неизвестно", inline=True)
        embed.add_field(name="👮 Модератор", value=moderator.mention, inline=True)
        
        if old_char:
            embed.add_field(
                name="📤 Старый основной", 
                value=f"**{old_char.get('character_name', 'Неизвестно')}**\nКласс: {old_char.get('class_spec', 'Неизвестно')}",
                inline=True
            )
        
        if new_char:
            embed.add_field(
                name="📥 Новый основной", 
                value=f"**{new_char.get('character_name', 'Неизвестно')}**\nКласс: {new_char.get('class_spec', 'Неизвестно')}",
                inline=True
            )
        
        if reason:
            embed.add_field(name="📝 Причина", value=reason[:500], inline=False)
        
        await log_channel.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Ошибка отправки лога смены персонажа: {e}")


# ===================== ОСНОВНОЙ КЛАСС =====================
class CharactersMainView(View):
    def __init__(self): super().__init__(timeout=None)

    # РЯД 0 — ПРОСМОТР И СОЗДАНИЕ
    @discord.ui.button(label="Мои персонажи", style=ButtonStyle.primary, emoji="👥", row=0, custom_id="chars_my_chars")
    async def my_chars(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        characters = db.get_user_characters(interaction.user.id)
        if not characters:
            view = FirstCharacterView()
            embed = Embed(
                title="👥 Ваши персонажи",
                description="У вас пока нет добавленных персонажей.\nИспользуйте кнопку ниже, чтобы добавить своего первого персонажа.",
                color=Color.orange()
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True, delete_after=60)
            return
        main_char = None; twins = []
        for char in characters:
            char = auto_fix_roles(db, char)
            if char['is_main']: main_char = char
            else: twins.append(char)
        embed = Embed(title="👥 Ваши персонажи", color=Color.blue(), timestamp=discord.utils.utcnow())
        if main_char:
            profile_text = f"🔗 [Профиль Sirus]({main_char['profile_url']})" if main_char['profile_url'] else ""
            raid_role_text = utils.format_raid_roles(main_char.get('raid_role', 'mdd'))
            specs_text = main_char.get('specialization', 'Не указана')
            embed.add_field(
                name="⭐ ОСНОВНОЙ",
                value=f"**{main_char['character_name']}**\n└─ **{main_char['class_spec']}** ({specs_text}) | 💎 {main_char['item_level']} iLvl | {raid_role_text}\n{profile_text}",
                inline=False
            )
        if twins:
            twins_text = ""
            for i, twin in enumerate(twins, 1):
                profile_text_twin = f"🔗 [Профиль Sirus]({twin['profile_url']})" if twin['profile_url'] else ""
                raid_role_text = utils.format_raid_roles(twin.get('raid_role', 'mdd'))
                specs_text = twin.get('specialization', 'Не указана')
                twins_text += f"{i}. **{twin['character_name']}** - **{twin['class_spec']}** ({specs_text}) | 💎 {twin['item_level']} iLvl | {raid_role_text}\n"
                if profile_text_twin: twins_text += f"   {profile_text_twin}\n"
            embed.add_field(name="🔄 ТВИНКИ", value=twins_text, inline=False)
        embed.set_footer(text=f"Всего персонажей: {len(characters)}")
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=120)

    @discord.ui.button(label="Добавить", style=ButtonStyle.success, emoji="➕", row=0, custom_id="chars_add")
    async def add_character(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        main_char = db.get_main_character(interaction.user.id)
        if not main_char:
            view = FirstCharacterView()
            embed = Embed(title="➕ Добавление первого персонажа", description="Добавьте своего первого персонажа:", color=Color.blue())
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            from modals.character_modals import AddTwinModal
            await interaction.response.send_modal(AddTwinModal(is_main=False))

    # РЯД 1 — РЕДАКТИРОВАНИЕ
    @discord.ui.button(label="Редактировать", style=ButtonStyle.primary, emoji="✏️", row=1, custom_id="chars_edit")
    async def edit_character(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        characters = db.get_user_characters(interaction.user.id)
        if not characters:
            await interaction.response.send_message("❌ У вас нет персонажей для редактирования!", ephemeral=True, delete_after=20)
            return
        view = EditMenuView(characters)
        embed = Embed(title="✏️ Редактирование персонажа", description="Выберите что хотите изменить:", color=Color.blue())
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Специализация", style=ButtonStyle.secondary, emoji="🎯", row=1, custom_id="chars_add_spec")
    async def add_specialization(self, interaction: discord.Interaction, button: Button):
        # ... (ваш существующий код)
        pass

    # РЯД 2 — СМЕНА И УДАЛЕНИЕ
    @discord.ui.button(label="Сменить основного", style=ButtonStyle.primary, emoji="🔄", row=2, custom_id="chars_change_main")
    async def change_main(self, interaction: discord.Interaction, button: Button):
        """Подача заявки на смену основного персонажа (с тегами ролей)"""
        db = interaction.client.get_db(interaction.guild_id)
        
        if not db:
            await interaction.response.send_message("❌ Ошибка подключения к БД!", ephemeral=True)
            return
        
        twins = db.get_user_twins(interaction.user.id)
        
        if not twins:
            await interaction.response.send_message(
                "❌ У вас нет твинков!\nСначала добавьте персонажей через **➕ Добавить**",
                ephemeral=True, 
                delete_after=20
            )
            return
        
        pending_request = db.get_pending_main_change_request(interaction.user.id)
        if pending_request:
            await interaction.response.send_message(
                f"❌ У вас уже есть активная заявка! ID: #{pending_request.get('id')}",
                ephemeral=True,
                delete_after=20
            )
            return
        
        view = ChangeMainCharacterSelectView(twins)
        embed = Embed(
            title="🔄 Смена основного персонажа",
            description=(
                "Выберите нового основного персонажа из списка твинков.\n\n"
                "После подачи заявки будет создан канал для рассмотрения.\n"
                "Уполномоченные лица примут решение."
            ),
            color=Color.orange()
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="Удалить", style=ButtonStyle.danger, emoji="🗑️", row=2, custom_id="chars_delete")
    async def delete_character(self, interaction: discord.Interaction, button: Button):
        # ... (ваш существующий код)
        pass

    # РЯД 3 — ЗАПРОСЫ И ПРОСМОТР ВСЕХ
    @discord.ui.button(label="Запрос в статик", style=ButtonStyle.primary, emoji="📋", row=3, custom_id="chars_static_request")
    async def static_request(self, interaction: discord.Interaction, button: Button):
        # ... (ваш существующий код)
        pass

    @discord.ui.button(label="Все персонажи", style=ButtonStyle.secondary, emoji="👁️", row=3, custom_id="chars_view_all")
    async def view_all_chars(self, interaction: discord.Interaction, button: Button):
        # ... (ваш существующий код)
        pass

    @discord.ui.button(label="Обучение на РЛ", style=ButtonStyle.primary, emoji="🎯", row=3, custom_id="chars_trainee")
    async def trainee_apply(self, interaction: discord.Interaction, button: Button):
        # ... (ваш существующий код)
        pass

    # РЯД 4 — СЕРВИСЫ
    @discord.ui.button(label="Техподдержка", style=ButtonStyle.secondary, emoji="🛠️", row=4, custom_id="chars_support")
    async def support_button(self, interaction: discord.Interaction, button: Button):
        from modals.character_modals import SupportModal
        await interaction.response.send_modal(SupportModal())

    @discord.ui.button(label="Жалобы/Обращение", style=ButtonStyle.danger, emoji="<a:f43:1480941692260454450>", row=4, custom_id="chars_report")
    async def report_button(self, interaction: discord.Interaction, button: Button):
        from modals.report_modals import ReportModal
        modal = ReportModal()
        await interaction.response.send_modal(modal)


# ===================== ВСПОМОГАТЕЛЬНЫЕ КЛАССЫ =====================

class ChangeMainCharacterSelectView(View):
    def __init__(self, twins: list):
        super().__init__(timeout=60)
        self.twins = twins
        select = Select(placeholder="🎯 Выберите нового основного персонажа", custom_id="select_new_main_twin")
        options = []
        for twin in twins[:25]:
            raid_role_text = utils.format_raid_roles(twin.get('raid_role', 'mdd'))
            specs_text = twin.get('specialization', 'Не указана')
            options.append(discord.SelectOption(
                label=twin['character_name'], 
                value=str(twin['id']), 
                description=f"{twin['class_spec']} ({specs_text}) | {twin['item_level']} iLvl", 
                emoji="🔄"
            ))
        select.options = options
        async def select_callback(interaction: discord.Interaction):
            twin_id = int(interaction.data['values'][0])
            twin = next((t for t in self.twins if t['id'] == twin_id), None)
            if twin:
                from modals.character_modals import ChangeMainCharacterModal
                await interaction.response.send_modal(ChangeMainCharacterModal(twin['id'], twin['character_name']))
        select.callback = select_callback
        self.add_item(select)
        cancel_btn = Button(label="Отмена", style=ButtonStyle.secondary, custom_id="cancel_main_change")
        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="❌ Отменено.", embed=None, view=None)
        cancel_btn.callback = cancel_callback
        self.add_item(cancel_btn)


class MainChangeReviewView(View):
    def __init__(self, request_id: int, user_id: int, old_char_id: int, new_char_id: int):
        super().__init__(timeout=None)
        self.request_id = request_id
        self.user_id = user_id
        self.old_char_id = old_char_id
        self.new_char_id = new_char_id

    @discord.ui.button(label="Одобрить", style=discord.ButtonStyle.success, emoji="✅", custom_id="approve_main_change_global")
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not utils.can_approve_main_change(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return
        
        db.update_character_main_status(self.old_char_id, False)
        db.update_character_main_status(self.new_char_id, True)
        db.update_main_change_request_status(self.request_id, "approved", interaction.user.id)
        
        # ЛОГИРОВАНИЕ
        user = interaction.guild.get_member(self.user_id)
        old_char = db.get_character_by_id(self.old_char_id)
        new_char = db.get_character_by_id(self.new_char_id)
        
        await send_main_change_log(
            interaction=interaction,
            db=db,
            status="approved",
            user=user,
            moderator=interaction.user,
            old_char=old_char,
            new_char=new_char
        )
        
        await interaction.response.send_message("✅ Одобрено!", ephemeral=True, delete_after=5)
        
        if user:
            try:
                await user.send(embed=Embed(title="✅ Заявка одобрена!", color=Color.green()))
            except:
                pass
        
        try:
            await interaction.channel.delete()
        except:
            pass

    @discord.ui.button(label="Отклонить", style=discord.ButtonStyle.danger, emoji="❌", custom_id="reject_main_change_global")
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not utils.can_approve_main_change(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return
        
        from modals.character_modals import MainChangeRejectModal
        modal = MainChangeRejectModal(
            self.request_id, 
            self.user_id, 
            self.old_char_id, 
            self.new_char_id
        )
        await interaction.response.send_modal(modal)


# Остальные классы (EditMenuView, ManageSpecsView, PaginatedCharactersView, PaginationView,
# FirstCharacterView, ClassSpecSelectView, AddMoreSpecsView, ConfirmDeleteView,
# ChangeMainCharacterSelectView, MainChangeReviewView, StaticRequestConfirmView,
# StaticRequestReviewView, SupportView) — БЕЗ ИЗМЕНЕНИЙ, как в твоём исходном файле.
# Ниже они приведены полностью для удобства.


class EditMenuView(View):
    def __init__(self, characters: list):
        super().__init__(timeout=60)
        self.characters = characters

    @discord.ui.button(label="Информацию", style=ButtonStyle.primary, emoji="📝", custom_id="edit_info_btn")
    async def edit_info(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        options = []
        for char in self.characters:
            char = auto_fix_roles(db, char)
            specs_text = char.get('specialization', 'Не указана')
            options.append(discord.SelectOption(label=char['character_name'], value=str(char['id']), description=f"{char['class_spec']} ({specs_text}) - {char['item_level']} iLvl", emoji=get_class_emoji(char['class_spec'])))
        select = Select(placeholder="🎯 Выберите персонажа", options=options, custom_id="select_char_edit_info")
        async def select_callback(interaction: discord.Interaction):
            char_id = int(interaction.data['values'][0])
            char = db.get_character_by_id(char_id)
            if char:
                from modals.character_modals import EditCharacterModal
                await interaction.response.send_modal(EditCharacterModal(char_id, char))
        select.callback = select_callback
        v = View(timeout=60); v.add_item(select)
        await interaction.response.send_message("Выберите персонажа:", view=v, ephemeral=True)

    @discord.ui.button(label="Специализации", style=ButtonStyle.primary, emoji="🎯", custom_id="edit_specs_btn")
    async def edit_specs(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        options = []
        for char in self.characters:
            char = auto_fix_roles(db, char)
            specs = char.get('specialization', 'Не указана')
            options.append(discord.SelectOption(label=char['character_name'], value=str(char['id']), description=f"{char['class_spec']} | Спеки: {specs}", emoji=get_class_emoji(char['class_spec'])))
        select = Select(placeholder="🎯 Выберите персонажа", options=options, custom_id="select_char_edit_specs")
        async def select_callback(interaction: discord.Interaction):
            char_id = int(interaction.data['values'][0])
            char = db.get_character_by_id(char_id)
            if char:
                char = auto_fix_roles(db, char)
                current_specs = char.get('specialization', '').split(', ')
                current_specs = [s.strip() for s in current_specs if s.strip()]
                embed = Embed(title=f"🎯 Специализации: {char['character_name']}", description=f"**Класс:** {char['class_spec']}\n**Текущие:** {', '.join(current_specs) if current_specs else 'Нет'}\n**Роли:** {utils.format_raid_roles(char.get('raid_role', 'mdd'))}", color=Color.blue())
                view = ManageSpecsView(char)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        select.callback = select_callback
        v = View(timeout=60); v.add_item(select)
        await interaction.response.send_message("Выберите персонажа:", view=v, ephemeral=True)

    @discord.ui.button(label="❌ Отмена", style=ButtonStyle.secondary, custom_id="cancel_edit_menu")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="❌ Отменено.", embed=None, view=None)


class ManageSpecsView(View):
    def __init__(self, char: dict):
        super().__init__(timeout=60)
        self.char = char

    @discord.ui.button(label="Добавить", style=ButtonStyle.success, emoji="➕", custom_id="add_spec_btn")
    async def add_spec(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        current_specs = self.char.get('specialization', '').split(', ')
        current_specs = [s.strip() for s in current_specs if s.strip()]
        class_name = self.char['class_spec']
        all_specs = CLASS_SPECS.get(class_name, [])
        available = [s for s in all_specs if s not in current_specs]
        if not available: await interaction.response.send_message("✅ Все спеки уже добавлены!", ephemeral=True); return
        spec_options = []
        for s in available:
            role_key = db.get_setting(f"spec_role_{class_name}_{s}", 'mdd')
            role_name = RAID_ROLE_NAMES.get(role_key, role_key)
            spec_options.append(discord.SelectOption(label=s, value=s, description=f"Роль: {role_name}", emoji="🎯"))
        select = Select(placeholder="Выберите специализацию", options=spec_options, custom_id="select_spec_add")
        async def callback(interaction: discord.Interaction):
            new_spec = interaction.data['values'][0]
            current_specs.append(new_spec)
            new_specs_str = ', '.join(current_specs)
            all_roles = []
            for spec in current_specs:
                role = db.get_setting(f"spec_role_{class_name}_{spec}", 'mdd')
                if role not in all_roles: all_roles.append(role)
            new_roles = ','.join(all_roles) if all_roles else 'mdd'
            db.cursor.execute('UPDATE characters SET specialization=?, raid_role=? WHERE id=?', (new_specs_str, new_roles, self.char['id']))
            db.conn.commit()
            self.char['specialization'] = new_specs_str; self.char['raid_role'] = new_roles
            embed = Embed(title="✅ Специализация добавлена", description=f"**{self.char['character_name']}**\nСпециализации: **{new_specs_str}**\nРоли: **{utils.format_raid_roles(new_roles)}**", color=Color.green())
            await interaction.response.edit_message(embed=embed, view=ManageSpecsView(self.char))
        select.callback = callback
        v = View(timeout=30); v.add_item(select)
        await interaction.response.send_message("Выберите специализацию:", view=v, ephemeral=True)

    @discord.ui.button(label="Снять", style=ButtonStyle.danger, emoji="🗑️", custom_id="remove_spec_btn")
    async def remove_spec(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db: await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True); return
        current_specs = self.char.get('specialization', '').split(', ')
        current_specs = [s.strip() for s in current_specs if s.strip()]
        if len(current_specs) <= 1: await interaction.response.send_message("⚠️ Нельзя оставить без специализации!", ephemeral=True); return
        spec_options = [discord.SelectOption(label=spec, value=spec, emoji="🗑️") for spec in current_specs]
        select = Select(placeholder="Выберите для снятия", options=spec_options, custom_id="select_spec_remove")
        async def callback(interaction: discord.Interaction):
            spec_to_remove = interaction.data['values'][0]
            current_specs.remove(spec_to_remove)
            new_specs_str = ', '.join(current_specs)
            all_roles = []
            for spec in current_specs:
                role = db.get_setting(f"spec_role_{self.char['class_spec']}_{spec}", 'mdd')
                if role not in all_roles: all_roles.append(role)
            new_roles = ','.join(all_roles) if all_roles else 'mdd'
            db.cursor.execute('UPDATE characters SET specialization=?, raid_role=? WHERE id=?', (new_specs_str, new_roles, self.char['id']))
            db.conn.commit()
            self.char['specialization'] = new_specs_str; self.char['raid_role'] = new_roles
            embed = Embed(title="✅ Специализация снята", description=f"**{self.char['character_name']}**\nОставшиеся: **{new_specs_str}**\nРоли: **{utils.format_raid_roles(new_roles)}**", color=Color.orange())
            await interaction.response.edit_message(embed=embed, view=ManageSpecsView(self.char))
        select.callback = callback
        v = View(timeout=30); v.add_item(select)
        await interaction.response.send_message("Выберите для снятия:", view=v, ephemeral=True)


class PaginatedCharactersView:
    def __init__(self, interaction, all_chars, page=0):
        self.interaction = interaction; self.all_chars = all_chars; self.page = page
        self.items_per_page = 5; self.members_list = list(all_chars.keys())
        self.total_pages = (len(self.members_list) + self.items_per_page - 1) // self.items_per_page

    async def send(self):
        db = self.interaction.client.get_db(self.interaction.guild_id)
        start = self.page * self.items_per_page; end = start + self.items_per_page
        current_members = self.members_list[start:end]
        embed = Embed(title="👁️ Все персонажи гильдии", description=f"Страница {self.page + 1} из {self.total_pages}", color=Color.blue())
        for member in current_members:
            chars = self.all_chars[member]
            main_char = next((c for c in chars if c['is_main']), None)
            twins = [c for c in chars if not c['is_main']]
            value = ""
            if main_char:
                main_char = auto_fix_roles(db, main_char)
                raid_role_text = utils.format_raid_roles(main_char.get('raid_role', 'mdd'))
                specs_text = main_char.get('specialization', 'Не указана')
                value += f"⭐ **{main_char['character_name']}** - {main_char['class_spec']} ({specs_text}) | 💎 {main_char['item_level']} iLvl | {raid_role_text}\n"
            if twins:
                twin_names = []
                for t in twins:
                    t = auto_fix_roles(db, t)
                    twin_roles = utils.format_raid_roles(t.get('raid_role', 'mdd'))
                    twin_names.append(f"{t['character_name']} ({t['class_spec']} - {t.get('specialization', 'Не указана')} | {twin_roles})")
                value += f"🔄 Твинки: {', '.join(twin_names)}"
            embed.add_field(name=f"👤 {member.display_name}", value=value or "Нет персонажей", inline=False)
        view = PaginationView(self, self.page, self.total_pages)
        await self.interaction.response.send_message(embed=embed, view=view, ephemeral=False, delete_after=120)


def build_page_embed(db, paginator, page):
    start = page * paginator.items_per_page; end = start + paginator.items_per_page
    current_members = paginator.members_list[start:end]
    embed = Embed(title="👁️ Все персонажи гильдии", description=f"Страница {page + 1} из {paginator.total_pages}", color=Color.blue())
    for member in current_members:
        chars = paginator.all_chars[member]
        main_char = next((c for c in chars if c['is_main']), None)
        twins = [c for c in chars if not c['is_main']]
        value = ""
        if main_char:
            main_char = auto_fix_roles(db, main_char)
            raid_role_text = utils.format_raid_roles(main_char.get('raid_role', 'mdd'))
            specs_text = main_char.get('specialization', 'Не указана')
            value += f"⭐ **{main_char['character_name']}** - {main_char['class_spec']} ({specs_text}) | 💎 {main_char['item_level']} iLvl | {raid_role_text}\n"
        if twins:
            twin_names = []
            for t in twins:
                t = auto_fix_roles(db, t)
                twin_roles = utils.format_raid_roles(t.get('raid_role', 'mdd'))
                twin_names.append(f"{t['character_name']} ({t['class_spec']} - {t.get('specialization', 'Не указана')} | {twin_roles})")
            value += f"🔄 Твинки: {', '.join(twin_names)}"
        embed.add_field(name=f"👤 {member.display_name}", value=value or "Нет персонажей", inline=False)
    return embed


class PaginationView(View):
    def __init__(self, paginator, current_page, total_pages):
        super().__init__(timeout=60)
        self.paginator = paginator; self.current_page = current_page; self.total_pages = total_pages

    @discord.ui.button(label="◀Назад", style=ButtonStyle.secondary, emoji="◀️", custom_id="pagination_prev")
    async def prev_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page > 0:
            self.current_page -= 1; self.paginator.page = self.current_page
            db = interaction.client.get_db(interaction.guild_id)
            embed = build_page_embed(db, self.paginator, self.current_page)
            view = PaginationView(self.paginator, self.current_page, self.total_pages)
            await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Вперед", style=ButtonStyle.secondary, emoji="▶️", custom_id="pagination_next")
    async def next_button(self, interaction: discord.Interaction, button: Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1; self.paginator.page = self.current_page
            db = interaction.client.get_db(interaction.guild_id)
            embed = build_page_embed(db, self.paginator, self.current_page)
            view = PaginationView(self.paginator, self.current_page, self.total_pages)
            await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🔒 Закрыть", style=ButtonStyle.danger, emoji="🔒", custom_id="pagination_close")
    async def close_button(self, interaction: discord.Interaction, button: Button):
        await interaction.message.delete()


class FirstCharacterView(View):
    def __init__(self): super().__init__(timeout=60)

    @discord.ui.button(label="Добавить основного персонажа", style=ButtonStyle.success, emoji="➕", row=0, custom_id="first_char_add")
    async def add_main(self, interaction: discord.Interaction, button: Button):
        from modals.character_modals import AddTwinModal
        await interaction.response.send_modal(AddTwinModal(is_main=True))


class ClassSpecSelectView(View):
    def __init__(self, modal, character_name: str, item_level: int, profile_url: str, is_main: bool):
        super().__init__(timeout=120)
        self.modal = modal; self.character_name = character_name; self.item_level = item_level
        self.profile_url = profile_url; self.is_main = is_main
        self.selected_class = None; self.selected_specs = []; self.raid_role = 'mdd'
        class_options = []
        for class_name, specs in CLASS_SPECS.items():
            class_options.append(discord.SelectOption(label=class_name, value=class_name, emoji=get_class_emoji(class_name)))
        self.class_select = Select(placeholder="⚔️ Выберите класс", options=class_options, custom_id="class_select")
        self.class_select.callback = self.on_class_select; self.add_item(self.class_select)
    
    async def on_class_select(self, interaction: discord.Interaction):
        self.selected_class = interaction.data['values'][0]
        specs = CLASS_SPECS.get(self.selected_class, [])
        db = interaction.client.get_db(interaction.guild_id)
        spec_options = []
        for spec in specs:
            role_key = db.get_setting(f"spec_role_{self.selected_class}_{spec}", 'mdd')
            role_name = RAID_ROLE_NAMES.get(role_key, role_key)
            spec_options.append(discord.SelectOption(label=spec, value=spec, description=f"Роль: {role_name}", emoji="🎯"))
        if not spec_options: await self.save_character(interaction); return
        self.spec_select = Select(placeholder="🎯 Выберите специализацию", options=spec_options, custom_id="spec_select")
        self.spec_select.callback = self.on_spec_select
        self.clear_items(); self.add_item(self.spec_select)
        await interaction.response.edit_message(content=f"✅ **Класс: {self.selected_class}**\nВыберите специализацию:", view=self)
    
    async def on_spec_select(self, interaction: discord.Interaction):
        specialization = interaction.data['values'][0]
        self.selected_specs = [specialization]
        db = interaction.client.get_db(interaction.guild_id)
        self.raid_role = db.get_setting(f"spec_role_{self.selected_class}_{specialization}", 'mdd')
        specs = CLASS_SPECS.get(self.selected_class, [])
        remaining = [s for s in specs if s != specialization]
        if remaining:
            view = AddMoreSpecsView(self, remaining)
            embed = Embed(title="🎯 Добавить специализацию?", description=f"Выбрана: **{specialization}**\nРоль: **{RAID_ROLE_NAMES.get(self.raid_role, self.raid_role)}**\n\nХотите добавить ещё?", color=Color.blue())
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await self.save_character(interaction)
    
    async def save_character(self, interaction: discord.Interaction):
        specs_str = ', '.join(self.selected_specs)
        db = interaction.client.get_db(interaction.guild_id)
        if len(self.selected_specs) > 1:
            all_roles = []
            for spec in self.selected_specs:
                role = db.get_setting(f"spec_role_{self.selected_class}_{spec}", 'mdd')
                if role not in all_roles: all_roles.append(role)
            self.raid_role = ','.join(all_roles) if all_roles else 'mdd'
        elif len(self.selected_specs) == 1:
            self.raid_role = db.get_setting(f"spec_role_{self.selected_class}_{self.selected_specs[0]}", 'mdd')
        data = {'character_name': self.character_name, 'class_spec': self.selected_class, 'specialization': specs_str, 'item_level': self.item_level, 'profile_url': self.profile_url, 'raid_role': self.raid_role, 'is_main': 1 if self.is_main else 0}
        db.add_character(interaction.user.id, data)
        role_name = utils.format_raid_roles(self.raid_role)
        if self.is_main:
            db.mark_characters_added(interaction.user.id)
            await interaction.response.edit_message(content=f"✅ Основной персонаж **{self.character_name}** добавлен!\nСпециализации: {specs_str}\nРоли: {role_name}", view=None)
        else:
            await interaction.response.edit_message(content=f"✅ Твинк **{self.character_name}** добавлен!\nСпециализации: {specs_str}\nРоли: {role_name}", view=None)
        await asyncio.sleep(3)
        try: await interaction.delete_original_response()
        except: pass


class AddMoreSpecsView(View):
    def __init__(self, parent_view, remaining_specs: list):
        super().__init__(timeout=60)
        self.parent_view = parent_view
        options = [discord.SelectOption(label=spec, value=spec) for spec in remaining_specs]
        options.append(discord.SelectOption(label="✅ Готово (закончить)", value="done", emoji="✅"))
        select = Select(placeholder="Выберите ещё или Готово", options=options, custom_id="add_more_specs")
        select.callback = self.on_select; self.add_item(select)
    
    async def on_select(self, interaction: discord.Interaction):
        value = interaction.data['values'][0]
        if value == "done": await self.parent_view.save_character(interaction)
        else:
            self.parent_view.selected_specs.append(value)
            specs = CLASS_SPECS.get(self.parent_view.selected_class, [])
            remaining = [s for s in specs if s not in self.parent_view.selected_specs]
            if remaining:
                options = [discord.SelectOption(label=spec, value=spec) for spec in remaining]
                options.append(discord.SelectOption(label="✅ Готово", value="done", emoji="✅"))
                select = Select(placeholder=f"Выбрано: {', '.join(self.parent_view.selected_specs)}. Ещё?", options=options, custom_id="add_more_specs2")
                select.callback = self.on_select
                self.clear_items(); self.add_item(select)
                embed = Embed(title="🎯 Специализации", description=f"Выбрано: **{', '.join(self.parent_view.selected_specs)}**\nМожно добавить ещё:", color=Color.blue())
                await interaction.response.edit_message(embed=embed, view=self)
            else: await self.parent_view.save_character(interaction)


class ConfirmDeleteView(View):
    def __init__(self, character_id: int, character_name: str):
        super().__init__(timeout=30)
        self.character_id = character_id; self.character_name = character_name

    @discord.ui.button(label="Да, удалить", style=ButtonStyle.danger, emoji="✅", custom_id="confirm_delete_yes")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        db.delete_character(self.character_id)
        embed = Embed(title="🗑️ Твинк удалён", description=f"Твинк **{self.character_name}** удалён!", color=Color.green())
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="❌ Отмена", style=ButtonStyle.secondary, emoji="❌", custom_id="confirm_delete_no")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="❌ Отменено.", embed=None, view=None)


class ChangeMainCharacterSelectView(View):
    def __init__(self, twins: list):
        super().__init__(timeout=60)
        self.twins = twins
        select = Select(placeholder="🎯 Выберите нового основного персонажа", custom_id="select_new_main_twin")
        options = []
        for twin in twins[:25]:
            raid_role_text = utils.format_raid_roles(twin.get('raid_role', 'mdd'))
            specs_text = twin.get('specialization', 'Не указана')
            options.append(discord.SelectOption(label=twin['character_name'], value=str(twin['id']), description=f"{twin['class_spec']} ({specs_text}) | {twin['item_level']} iLvl", emoji="🔄"))
        select.options = options
        async def select_callback(interaction: discord.Interaction):
            twin_id = int(interaction.data['values'][0])
            twin = next((t for t in self.twins if t['id'] == twin_id), None)
            if twin:
                from modals.character_modals import ChangeMainCharacterModal
                await interaction.response.send_modal(ChangeMainCharacterModal(twin['id'], twin['character_name']))
        select.callback = select_callback; self.add_item(select)
        cancel_btn = Button(label="Отмена", style=ButtonStyle.secondary, custom_id="cancel_main_change")
        async def cancel_callback(interaction: discord.Interaction): await interaction.response.edit_message(content="❌ Отменено.", embed=None, view=None)
        cancel_btn.callback = cancel_callback; self.add_item(cancel_btn)


class MainChangeReviewView(View):
    def __init__(self, request_id: int, user_id: int, old_char_id: int, new_char_id: int):
        super().__init__(timeout=None)
        self.request_id = request_id; self.user_id = user_id; self.old_char_id = old_char_id; self.new_char_id = new_char_id

    @discord.ui.button(label="Одобрить", style=ButtonStyle.success, emoji="✅", custom_id="approve_main_change_global")
    async def approve_button(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not utils.can_approve_main_change(interaction.user, db): await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10); return
        db.update_character_main_status(self.old_char_id, False); db.update_character_main_status(self.new_char_id, True)
        db.update_main_change_request_status(self.request_id, "approved", interaction.user.id)
        await interaction.response.send_message("✅ Одобрено!", ephemeral=True, delete_after=5)
        user = interaction.guild.get_member(self.user_id)
        if user:
            try: await user.send(embed=Embed(title="✅ Заявка одобрена!", color=Color.green()))
            except: pass
        try: await interaction.channel.delete()
        except: pass

    @discord.ui.button(label="Отклонить", style=ButtonStyle.danger, emoji="❌", custom_id="reject_main_change_global")
    async def reject_button(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not utils.can_approve_main_change(interaction.user, db): await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10); return
        db.update_main_change_request_status(self.request_id, "rejected", interaction.user.id)
        await interaction.response.send_message("❌ Отклонено!", ephemeral=True, delete_after=5)
        user = interaction.guild.get_member(self.user_id)
        if user:
            try: await user.send(embed=Embed(title="❌ Заявка отклонена!", color=Color.red()))
            except: pass
        try: await interaction.channel.delete()
        except: pass


class StaticRequestConfirmView(View):
    def __init__(self): super().__init__(timeout=60)

    @discord.ui.button(label="Я ознакомлен", style=ButtonStyle.success, emoji="✅", custom_id="static_confirm")
    async def confirm(self, interaction: discord.Interaction, button: Button):
        from modals.character_modals import StaticRequestModal
        await interaction.response.send_modal(StaticRequestModal())


class StaticRequestReviewView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.votes = {}
        self.total_voters = 0
        self.voters_list = []
        self.initialized = False
    
    async def init_voters(self, interaction):
        if self.initialized:
            return
        
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            return
        
        saved_votes = db.get_static_votes(interaction.channel_id)
        self.votes = saved_votes
        
        vote_roles = []
        for i in range(1, 6):
            role_id = utils.safe_int(db.get_setting(f'vote_role_{i}', ''))
            if role_id:
                role = interaction.guild.get_role(role_id)
                if role:
                    vote_roles.append(role)
        
        if not vote_roles:
            self.total_voters = 1
            self.initialized = True
            return
        
        voters = set()
        for role in vote_roles:
            for member in role.members:
                if not member.bot:
                    voters.add(member.id)
        
        self.voters_list = list(voters)
        self.total_voters = len(voters)
        self.initialized = True
    
    def get_vote_counts(self):
        yes = sum(1 for v in self.votes.values() if v)
        no = sum(1 for v in self.votes.values() if not v)
        remaining = self.total_voters - len(self.votes)
        return yes, no, remaining
    
    def get_voters_mentions(self, vote_type: bool):
        return [f"<@{uid}>" for uid, v in self.votes.items() if v == vote_type]
    
    def get_not_voted_mentions(self):
        return [f"<@{uid}>" for uid in self.voters_list if uid not in self.votes]
    
    def build_embed(self, interaction, request_data=None):
        yes, no, remaining = self.get_vote_counts()
        
        embed = Embed(title="📋 Голосование: Запрос в статик", color=Color.blue())
        
        if request_data:
            embed.description = (
                f"**Персонаж:** {request_data.get('character_name', 'Неизвестно')}\n"
                f"**Класс:** {request_data.get('class_spec', 'Неизвестно')}\n"
                f"**iLvl:** {request_data.get('item_level', '?')}"
            )
        
        embed.add_field(name=f"✅ За ({yes})", value=", ".join(self.get_voters_mentions(True)) or "—", inline=True)
        embed.add_field(name=f"❌ Против ({no})", value=", ".join(self.get_voters_mentions(False)) or "—", inline=True)
        embed.add_field(name=f"⏳ Ожидают ({remaining})", value=", ".join(self.get_not_voted_mentions()) or "Все проголосовали!", inline=False)
        embed.add_field(name="📊 Всего голосующих", value=f"**{self.total_voters}** человек", inline=True)
        embed.set_footer(text=f"Проголосовало: {len(self.votes)}/{self.total_voters}")
        
        return embed
    
    @discord.ui.button(label="За", style=ButtonStyle.success, emoji="✅", custom_id="static_vote_yes")
    async def vote_yes(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
            return
        
        await self.init_voters(interaction)
        
        if not utils.can_accept_static(interaction.user, db):
            await interaction.response.send_message("❌ У вас нет права голоса!", ephemeral=True)
            return
        
        if self.voters_list and interaction.user.id not in self.voters_list:
            await interaction.response.send_message("❌ Вы не в списке голосующих!", ephemeral=True)
            return
        
        if interaction.user.id in self.votes:
            await interaction.response.send_message("❌ Вы уже проголосовали!", ephemeral=True)
            return
        
        self.votes[interaction.user.id] = True
        db.save_static_vote(interaction.channel_id, interaction.user.id, True)
        
        req_data = db.get_pending_static_request(interaction.channel_id)
        request_data = {}
        if req_data:
            request_data = {
                'character_name': req_data.get('character_name', 'Неизвестно'),
                'class_spec': req_data.get('class_spec', 'Неизвестно'),
                'item_level': req_data.get('item_level', '?')
            }
        
        if len(self.votes) >= self.total_voters:
            await self.finalize_voting(interaction, db, request_data)
        else:
            embed = self.build_embed(interaction, request_data)
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.followup.send(
                f"✅ Вы проголосовали **ЗА**! ({len(self.votes)}/{self.total_voters})",
                ephemeral=True
            )
    
    @discord.ui.button(label="Против", style=ButtonStyle.danger, emoji="❌", custom_id="static_vote_no")
    async def vote_no(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
            return
        
        await self.init_voters(interaction)
        
        if not utils.can_accept_static(interaction.user, db):
            await interaction.response.send_message("❌ У вас нет права голоса!", ephemeral=True)
            return
        
        if self.voters_list and interaction.user.id not in self.voters_list:
            await interaction.response.send_message("❌ Вы не в списке голосующих!", ephemeral=True)
            return
        
        if interaction.user.id in self.votes:
            await interaction.response.send_message("❌ Вы уже проголосовали!", ephemeral=True)
            return
        
        self.votes[interaction.user.id] = False
        db.save_static_vote(interaction.channel_id, interaction.user.id, False)
        
        req_data = db.get_pending_static_request(interaction.channel_id)
        request_data = {}
        if req_data:
            request_data = {
                'character_name': req_data.get('character_name', 'Неизвестно'),
                'class_spec': req_data.get('class_spec', 'Неизвестно'),
                'item_level': req_data.get('item_level', '?')
            }
        
        if len(self.votes) >= self.total_voters:
            await self.finalize_voting(interaction, db, request_data)
        else:
            embed = self.build_embed(interaction, request_data)
            await interaction.response.edit_message(embed=embed, view=self)
            await interaction.followup.send(
                f"✅ Вы проголосовали **ПРОТИВ**! ({len(self.votes)}/{self.total_voters})",
                ephemeral=True
            )
    
    @discord.ui.button(label="Статус", style=ButtonStyle.secondary, emoji="📊", custom_id="static_status")
    async def show_status(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
            return
        
        await self.init_voters(interaction)
        
        req_data = db.get_pending_static_request(interaction.channel_id)
        request_data = {}
        if req_data:
            request_data = {
                'character_name': req_data.get('character_name', 'Неизвестно'),
                'class_spec': req_data.get('class_spec', 'Неизвестно'),
                'item_level': req_data.get('item_level', '?')
            }
        
        embed = self.build_embed(interaction, request_data)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def finalize_voting(self, interaction, db, request_data):
        yes, no, _ = self.get_vote_counts()
        
        req_data = db.get_pending_static_request(interaction.channel_id)
        if not req_data:
            return
        
        request_id = req_data.get('id')
        user_id = req_data.get('user_id')
        user = interaction.guild.get_member(user_id)
        
        if yes > no:
            # ПРИНЯТО
            db.update_static_request_status(request_id, "accepted", interaction.user.id)
            if user:
                for i in range(1, 4):
                    remove_role_id = utils.safe_int(db.get_setting(f'static_remove_role_{i}', ''))
                    if remove_role_id:
                        remove_role = interaction.guild.get_role(remove_role_id)
                        if remove_role and remove_role in user.roles:
                            try:
                                await user.remove_roles(remove_role, reason="Принят в статик")
                            except Exception as e:
                                print(f"❌ Ошибка снятия роли: {e}")
                
                add_role_id = utils.safe_int(db.get_setting('static_add_role', ''))
                if not add_role_id:
                    add_role_id = utils.safe_int(db.get_setting('static_role', ''))
                
                if add_role_id:
                    add_role = interaction.guild.get_role(add_role_id)
                    if add_role and add_role not in user.roles:
                        try:
                            await user.add_roles(add_role, reason="Принят в статик по голосованию")
                        except Exception as e:
                            print(f"❌ Ошибка выдачи роли: {e}")
            
            embed = self.build_embed(interaction, request_data)
            embed.title = "✅ Заявка ПРИНЯТА!"
            embed.color = Color.green()
            embed.set_footer(text=f"Итог: {yes} за, {no} против | Принято!")
            
            if user:
                try:
                    dm = Embed(
                        title="✅ Заявка в статик одобрена!",
                        description=f"**Сервер:** {interaction.guild.name}\n"
                                f"**Голосов ЗА:** {yes}\n"
                                f"**Голосов ПРОТИВ:** {no}\n\n"
                                f"Поздравляем! Вы приняты в статик!",
                        color=Color.green()
                    )
                    await user.send(embed=dm)
                except: pass
        else:
            # ОТКЛОНЕНО
            db.update_static_request_status(request_id, "rejected", interaction.user.id)
            
            embed = self.build_embed(interaction, request_data)
            embed.title = "❌ Заявка ОТКЛОНЕНА!"
            embed.color = Color.red()
            embed.set_footer(text=f"Итог: {yes} за, {no} против | Отклонено!")
            
            if user:
                try:
                    dm = Embed(
                        title="❌ Заявка в статик отклонена",
                        description=f"**Сервер:** {interaction.guild.name}\n"
                                f"**Голосов ЗА:** {yes}\n"
                                f"**Голосов ПРОТИВ:** {no}\n\n"
                                f"К сожалению, ваша заявка не набрала нужного количества голосов.",
                        color=Color.red()
                    )
                    await user.send(embed=dm)
                except: pass
        
        # Логи
        try:
            log_ch = utils.safe_int(db.get_setting('log_channel', ''))
            if log_ch:
                ch = interaction.guild.get_channel(log_ch)
                if ch:
                    log_embed = Embed(
                        title="📋 Заявка в статик",
                        description=f"**Статус:** {'✅ ПРИНЯТО' if yes > no else '❌ ОТКЛОНЕНО'} (голосование)",
                        color=Color.green() if yes > no else Color.red(),
                        timestamp=datetime.now()
                    )
                    log_embed.add_field(name="👤 Пользователь", value=user.mention if user else f"ID:{user_id}", inline=True)
                    log_embed.add_field(name="📊 Итог", value=f"За: {yes}\nПротив: {no}", inline=True)
                    await ch.send(embed=log_embed)
        except: pass
        
        db.clear_static_votes(interaction.channel_id)
        await interaction.response.edit_message(embed=embed, view=None)
        
        try:
            await asyncio.sleep(10)
            await interaction.channel.delete()
        except: pass


class SupportView(View):
    def __init__(self, report_id: int, user_id: int):
        super().__init__(timeout=None)
        self.report_id = report_id
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            return False
        
        developer_id = db.get_setting('developer_id', '')
        if str(interaction.user.id) != developer_id:
            await interaction.response.send_message(
                "❌ Только разработчик может использовать эти кнопки!",
                ephemeral=True
            )
            return False
        
        return True

    @discord.ui.button(label="Решено", style=ButtonStyle.success, emoji="✅", custom_id="support_resolved_btn")
    async def resolve_button(self, interaction: discord.Interaction, button: Button):
        if interaction.response.is_done():
            return
        
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
            return
        
        try:
            db.cursor.execute(
                'UPDATE support_reports SET status = "resolved", resolved_by = ? WHERE id = ?',
                (interaction.user.id, self.report_id)
            )
            db.conn.commit()
        except:
            pass
        
        user = interaction.guild.get_member(self.user_id)
        if user:
            try:
                dm_embed = Embed(
                    title=f"✅ Обращение #{self.report_id} решено!",
                    description=f"**Сервер:** {interaction.guild.name}\n"
                               f"**Разработчик:** {interaction.user.mention}\n"
                               f"**Дата:** {discord.utils.format_dt(datetime.now(), 'F')}\n\n"
                               f"Ваше обращение было рассмотрено и исправлено!\n"
                               f"Спасибо за обращение!",
                    color=Color.green(),
                    timestamp=datetime.now()
                )
                await user.send(embed=dm_embed)
            except:
                pass
        
        embed = Embed(
            title=f"✅ Обращение #{self.report_id} закрыто",
            description=f"**Разработчик:** {interaction.user.mention}\n"
                       f"**Статус:** Исправлено ✅",
            color=Color.green(),
            timestamp=datetime.now()
        )
        await interaction.response.send_message(embed=embed)
        
        try:
            await asyncio.sleep(5)
            await interaction.channel.delete()
        except:
            pass

    @discord.ui.button(label="Ответить", style=ButtonStyle.primary, emoji="💬", custom_id="support_reply_btn")
    async def reply_button(self, interaction: discord.Interaction, button: Button):
        if interaction.response.is_done():
            return
        
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ БД не найдена!", ephemeral=True)
            return
        
        from modals.character_modals import SupportReplyModal
        await interaction.response.send_modal(
            SupportReplyModal(self.report_id, self.user_id, interaction.channel)
        )
