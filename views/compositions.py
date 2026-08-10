# views/compositions.py — ПОЛНЫЙ ФАЙЛ С ПОИСКОМ ЛИДЕРА

import discord
import asyncio
from datetime import datetime
from discord.ui import View, Button, Select
from discord import ButtonStyle, Color, Embed
import utils
from constants import RAID_ROLE_NAMES, format_raid_roles


class CompositionCreateButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Создать состав", style=ButtonStyle.success, emoji="➕", custom_id="create_comp_btn")
    async def create(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        if not utils.can_manage_compositions(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return
        from modals.composition_modals import CreateCompositionModal
        await interaction.response.send_modal(CreateCompositionModal())


class SetLeaderSelectView(View):
    def __init__(self, composition_id: int, name: str, main_slots: int, reserve_slots: int, characters: list):
        super().__init__(timeout=120)
        self.composition_id = composition_id
        self.name = name
        self.main_slots = main_slots
        self.reserve_slots = reserve_slots
        self.characters = characters
        
        # Кнопка поиска
        search_btn = Button(
            label="🔍 Поиск лидера",
            style=ButtonStyle.primary,
            emoji="🔍",
            custom_id="search_leader_btn"
        )
        search_btn.callback = self.search_leader
        self.add_item(search_btn)
        
        # Выпадающий список
        select = Select(placeholder="👑 Выберите лидера рейда", custom_id="select_leader")
        self.update_select_options(select, characters)
        
        async def select_callback(interaction: discord.Interaction):
            db = interaction.client.get_db(interaction.guild_id)
            if not db:
                await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
                return
            
            user_id = int(interaction.data['values'][0])
            if user_id == 0:
                await interaction.response.send_message("❌ Нет персонажей для выбора!", ephemeral=True, delete_after=10)
                return
            
            member = interaction.guild.get_member(user_id)
            if not member:
                await interaction.response.send_message("❌ Игрок не найден!", ephemeral=True, delete_after=10)
                return
            if not utils.is_raid_leader(member, db):
                await interaction.response.send_message("❌ Не является Рейд-лидером!", ephemeral=True, delete_after=10)
                return
            
            selected = None
            for char in characters:
                if char['user_id'] == user_id:
                    selected = char
                    break
            if not selected:
                await interaction.response.send_message("❌ Игрок не найден!", ephemeral=True, delete_after=10)
                return
            
            db.cursor.execute('UPDATE raids SET leader_id = ? WHERE id = ?', (user_id, self.composition_id))
            db.conn.commit()
            
            raid_roles = selected.get('raid_role', 'mdd').split(',')
            first_role = raid_roles[0].strip()
            db.add_composition_member(self.composition_id, user_id, selected['character_id'], first_role, is_reserve=False)
            
            # Логирование
            db.add_log("👑 Лидер", interaction.user.id, user_id, f"Назначен лидером состава '{self.name}'")
            
            ctrl_ch_id = utils.safe_int(db.get_setting('composition_control_channel', ''))
            if ctrl_ch_id:
                ctrl_ch = interaction.guild.get_channel(ctrl_ch_id)
                if ctrl_ch:
                    view = CompositionControlPanel()
                    emb = Embed(
                        title=f"🎯 Управление составом: {self.name}",
                        description=f"**Лидер:** {selected['user_name']}\n**Всего мест:** {self.main_slots} | **Резерв:** {self.reserve_slots}",
                        color=Color.blue(),
                        timestamp=discord.utils.utcnow()
                    )
                    emb.set_footer(text=f"ID состава: {self.composition_id}")
                    await ctrl_ch.send(embed=emb, view=view)
            
            await update_composition_display(interaction, self.composition_id, self.name, self.main_slots, self.reserve_slots)
            
            try:
                await interaction.message.delete()
            except: pass
            
            await interaction.response.send_message(f"✅ Состав **{self.name}** создан!", ephemeral=True, delete_after=5)
        
        select.callback = select_callback
        self.select = select
        self.add_item(select)
        
        cancel_btn = Button(label="Отмена", style=ButtonStyle.secondary, custom_id="cancel_leader")
        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="❌ Отменено.", embed=None, view=None)
        cancel_btn.callback = cancel_callback
        self.add_item(cancel_btn)
    
    def update_select_options(self, select, characters):
        """Обновляет опции в выпадающем списке"""
        options = []
        for char in characters[:25]:
            raid_role_text = format_raid_roles(char.get('raid_role', 'mdd'))
            options.append(discord.SelectOption(
                label=f"{char['character_name']} ({char['user_name']})",
                value=str(char['user_id']),
                description=f"{char['class_spec']} | {char['item_level']} iLvl | {raid_role_text}",
                emoji="👑"
            ))
        select.options = options if options else [discord.SelectOption(label="Нет персонажей", value="0")]
    
    async def search_leader(self, interaction: discord.Interaction):
        """Открывает модальное окно поиска лидера"""
        from modals.composition_modals import LeaderSearchModal
        await interaction.response.send_modal(
            LeaderSearchModal(self.composition_id, self.name, self.main_slots, self.reserve_slots, self)
        )
    
    async def filter_by_search(self, interaction: discord.Interaction, query: str):
        """Фильтрует список лидеров по запросу"""
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            return
        
        query = query.strip().lower()
        filtered = []
        
        for char in self.characters:
            if (query in char['character_name'].lower() or 
                query in char['user_name'].lower() or
                query in char['class_spec'].lower()):
                filtered.append(char)
        
        if not filtered:
            await interaction.followup.send("❌ Никого не найдено!", ephemeral=True, delete_after=5)
            return
        
        # Обновляем опции в выпадающем списке
        self.update_select_options(self.select, filtered)
        
        # Создаём новый embed
        embed = Embed(
            title=f"🔍 Результаты поиска: {len(filtered)}",
            description=f"По запросу **{query}** найдено лидеров: {len(filtered)}",
            color=Color.blue()
        )
        
        # Отвечаем на взаимодействие
        await interaction.response.edit_message(embed=embed, view=self)


class CompositionControlPanel(View):
    def __init__(self):
        super().__init__(timeout=None)

    def _get_cid(self, message):
        if message.embeds and message.embeds[0].footer.text:
            text = message.embeds[0].footer.text
            if "ID состава:" in text:
                return int(text.replace("ID состава:", "").strip())
        return 0

    @discord.ui.button(label="Добавить", style=ButtonStyle.success, emoji="➕", row=0, custom_id="comp_add_fixed")
    async def add_member(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        if not utils.can_manage_compositions(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return
        
        comp_id = self._get_cid(interaction.message)
        comp = db.get_composition(comp_id)
        if not comp:
            await interaction.response.send_message("❌ Состав не найден!", ephemeral=True, delete_after=10)
            return
        
        view = AddMemberMenuView(comp_id, comp['name'], comp['main_slots'], comp['reserve_slots'])
        await interaction.response.send_message(
            embed=Embed(title=f"➕ Добавление в {comp['name']}", description="Выберите способ поиска:", color=Color.blue()),
            view=view, ephemeral=True
        )

    @discord.ui.button(label="Роль", style=ButtonStyle.primary, emoji="✏️", row=0, custom_id="comp_edit_fixed")
    async def edit_role(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        if not utils.can_manage_compositions(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return
        
        comp_id = self._get_cid(interaction.message)
        comp = db.get_composition(comp_id)
        if not comp:
            await interaction.response.send_message("❌ Состав не найден!", ephemeral=True, delete_after=10)
            return
        
        members = db.get_composition_members(comp_id)
        if not members:
            await interaction.response.send_message("📭 Нет участников!", ephemeral=True, delete_after=10)
            return
        
        options = []
        for m in members[:25]:
            user_name = m.get('user_name', f"ID: {m['user_id']}")
            role_icon = {"mdd": "⚔️", "rdd": "🏹", "tank": "🛡️", "heal": "💚"}.get(m['role'], "⚔️")
            reserve_tag = " [Р]" if m['is_reserve'] else ""
            options.append(discord.SelectOption(
                label=f"{m['character_name']} ({user_name}){reserve_tag}",
                value=str(m['user_id']),
                description=f"{role_icon} {m['class_spec']}",
                emoji="✏️"
            ))
        
        select = Select(placeholder="Выберите игрока", options=options, custom_id="comp_edit_role_select")
        
        async def select_callback(interaction: discord.Interaction):
            db = interaction.client.get_db(interaction.guild_id)
            if not db:
                await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
                return
            user_id = int(interaction.data['values'][0])
            selected = None
            for m in members:
                if m['user_id'] == user_id:
                    selected = m
                    break
            if selected:
                from modals.composition_modals import CompositionEditModal
                await interaction.response.send_modal(
                    CompositionEditModal(comp_id, comp['name'], comp['main_slots'], comp['reserve_slots'], selected)
                )
        
        select.callback = select_callback
        
        v = View(timeout=60)
        v.add_item(select)
        cancel_btn = Button(label="Отмена", style=ButtonStyle.secondary, custom_id="cancel_edit_role")
        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="Отменено.", embed=None, view=None)
        cancel_btn.callback = cancel_callback
        v.add_item(cancel_btn)
        
        await interaction.response.send_message(
            embed=Embed(title=f"✏️ Изменение роли в {comp['name']}", description="Выберите игрока:", color=Color.orange()),
            view=v, ephemeral=True
        )

    @discord.ui.button(label="Удалить", style=ButtonStyle.danger, emoji="🗑️", row=0, custom_id="comp_remove_fixed")
    async def remove_member(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        if not utils.can_manage_compositions(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return
        
        comp_id = self._get_cid(interaction.message)
        comp = db.get_composition(comp_id)
        if not comp:
            await interaction.response.send_message("❌ Состав не найден!", ephemeral=True, delete_after=10)
            return
        
        members = db.get_composition_members(comp_id)
        if not members:
            await interaction.response.send_message("📭 Нет участников!", ephemeral=True, delete_after=10)
            return
        
        options = []
        for m in members[:25]:
            user_name = m.get('user_name', f"ID: {m['user_id']}")
            options.append(discord.SelectOption(
                label=f"{m['character_name']} ({user_name})",
                value=str(m['user_id']),
                description=m['class_spec'],
                emoji="🗑️"
            ))
        
        select = Select(placeholder="Выберите игрока для удаления", options=options, custom_id="comp_remove_select")
        
        async def select_callback(interaction: discord.Interaction):
            db = interaction.client.get_db(interaction.guild_id)
            if not db:
                await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
                return
            user_id = int(interaction.data['values'][0])
            selected = None
            for m in members:
                if m['user_id'] == user_id:
                    selected = m
                    break
            if not selected:
                await interaction.response.send_message("❌ Не найден!", ephemeral=True, delete_after=10)
                return
            
            try:
                await interaction.message.delete()
            except: pass
            
            confirm_view = View(timeout=30)
            
            async def confirm_callback(interaction: discord.Interaction):
                db2 = interaction.client.get_db(interaction.guild_id)
                if not db2:
                    await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
                    return
                db2.remove_composition_member(comp_id, user_id)
                await update_composition_display(interaction, comp_id, comp['name'], comp['main_slots'], comp['reserve_slots'])
                await interaction.response.edit_message(
                    embed=Embed(title="🗑️ Удалён", description=f"**{selected['character_name']}** удалён.", color=Color.red()),
                    view=None
                )
            
            confirm_btn = Button(label="Да", style=ButtonStyle.danger, emoji="✅", custom_id="confirm_remove_yes")
            confirm_btn.callback = confirm_callback
            confirm_view.add_item(confirm_btn)
            
            cancel_btn2 = Button(label="Нет", style=ButtonStyle.secondary, emoji="❌", custom_id="confirm_remove_no")
            async def cancel_confirm_callback(interaction: discord.Interaction):
                await interaction.response.edit_message(content="❌ Отменено.", embed=None, view=None)
            cancel_btn2.callback = cancel_confirm_callback
            confirm_view.add_item(cancel_btn2)
            
            await interaction.response.send_message(
                embed=Embed(title="🗑️ Подтверждение", description=f"Удалить **{selected['character_name']}**?", color=Color.red()),
                view=confirm_view, ephemeral=True
            )
        
        select.callback = select_callback
        
        v = View(timeout=60)
        v.add_item(select)
        cancel_btn = Button(label="Отмена", style=ButtonStyle.secondary, custom_id="cancel_remove")
        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="Отменено.", embed=None, view=None)
        cancel_btn.callback = cancel_callback
        v.add_item(cancel_btn)
        
        await interaction.response.send_message(
            embed=Embed(title=f"🗑️ Удаление из {comp['name']}", description="Выберите игрока:", color=Color.red()),
            view=v, ephemeral=True
        )

    @discord.ui.button(label="В резерв", style=ButtonStyle.primary, emoji="📦", row=1, custom_id="comp_reserve_fixed")
    async def move_to_reserve(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        if not utils.can_manage_compositions(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return
        
        comp_id = self._get_cid(interaction.message)
        comp = db.get_composition(comp_id)
        if not comp:
            return
        
        members = db.get_composition_members(comp_id)
        main_members = [m for m in members if not m['is_reserve']]
        if not main_members:
            await interaction.response.send_message("📭 Нет участников в основе!", ephemeral=True, delete_after=10)
            return
        
        view = CompositionReserveSelectView(comp_id, comp['name'], comp['main_slots'], comp['reserve_slots'], main_members)
        await interaction.response.send_message(
            embed=Embed(title=f"📦 Перемещение в резерв", description="Выберите игрока:", color=Color.blue()),
            view=view, ephemeral=True
        )

    @discord.ui.button(label="⬆Из резерва", style=ButtonStyle.primary, emoji="⬆️", row=1, custom_id="comp_from_reserve_fixed")
    async def from_reserve(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        if not utils.can_manage_compositions(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return
        
        comp_id = self._get_cid(interaction.message)
        comp = db.get_composition(comp_id)
        if not comp:
            return
        
        members = db.get_composition_members(comp_id)
        reserve_members = [m for m in members if m['is_reserve']]
        if not reserve_members:
            await interaction.response.send_message("📭 Нет участников в резерве!", ephemeral=True, delete_after=10)
            return
        
        view = CompositionFromReserveSelectView(comp_id, comp['name'], comp['main_slots'], comp['reserve_slots'], reserve_members)
        await interaction.response.send_message(
            embed=Embed(title=f"⬆️ Перемещение из резерва", description="Выберите игрока:", color=Color.blue()),
            view=view, ephemeral=True
        )

    @discord.ui.button(label="Копия", style=ButtonStyle.primary, emoji="📋", row=2, custom_id="comp_dup_fixed")
    async def duplicate(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        if not utils.can_manage_compositions(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return
        
        comp_id = self._get_cid(interaction.message)
        comp = db.get_composition(comp_id)
        if not comp:
            return
        
        from modals.composition_modals import DuplicateCompositionModal
        await interaction.response.send_modal(DuplicateCompositionModal(comp_id, comp['name']))

    @discord.ui.button(label="Закрыть", style=ButtonStyle.danger, emoji="🔒", row=2, custom_id="comp_close_fixed")
    async def close(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        if not utils.can_manage_compositions(interaction.user, db):
            await interaction.response.send_message("❌ Нет прав!", ephemeral=True, delete_after=10)
            return
        
        comp_id = self._get_cid(interaction.message)
        comp = db.get_composition(comp_id)
        if not comp:
            return
        
        db.close_composition(comp_id)
        
        # Логирование
        db.add_log("🔒 Состав закрыт", interaction.user.id, details=f"Состав #{comp_id}: {comp['name']}")
        
        try:
            await interaction.message.delete()
        except: pass
        
        await update_composition_display(interaction, comp_id, comp['name'], comp['main_slots'], comp['reserve_slots'])
        await interaction.response.send_message(
            embed=Embed(title="🔒 Состав закрыт", description=f"**{comp['name']}** закрыт.", color=Color.red()),
            ephemeral=True, delete_after=5
        )


class AddMemberMenuView(View):
    def __init__(self, composition_id: int, name: str, main_slots: int, reserve_slots: int):
        super().__init__(timeout=60)
        self.composition_id = composition_id
        self.name = name
        self.main_slots = main_slots
        self.reserve_slots = reserve_slots

    @discord.ui.button(label="Поиск", style=ButtonStyle.primary, emoji="🔍", custom_id="add_member_search")
    async def search(self, interaction: discord.Interaction, button: Button):
        from modals.composition_modals import CompositionSearchModal
        await interaction.response.send_modal(
            CompositionSearchModal(self.composition_id, self.name, self.main_slots, self.reserve_slots)
        )

    @discord.ui.button(label="Все", style=ButtonStyle.secondary, emoji="📋", custom_id="add_member_list")
    async def list_all(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        guild = interaction.guild
        
        all_chars = []
        for member in guild.members:
            chars = db.get_user_characters(member.id)
            for char in chars:
                all_chars.append({
                    'user_id': member.id,
                    'user_name': member.display_name,
                    'character_id': char['id'],
                    'character_name': char['character_name'],
                    'class_spec': char['class_spec'],
                    'item_level': char.get('item_level', 0),
                    'raid_role': char.get('raid_role', 'mdd'),
                    'is_main': char['is_main'],
                    'priority': db.get_user_priority_level(member)
                })
        
        members = db.get_composition_members(self.composition_id)
        member_ids = [m['user_id'] for m in members]
        available = [c for c in all_chars if c['user_id'] not in member_ids]
        
        if not available:
            await interaction.response.send_message("📭 Нет доступных игроков!", ephemeral=True, delete_after=10)
            return
        
        available.sort(key=lambda x: (0 if x.get('is_main', True) else 1, x['priority'], -x['item_level']))
        view = CompositionMemberSelect(self.composition_id, self.name, self.main_slots, self.reserve_slots, available)
        await interaction.response.send_message(
            embed=Embed(title=f"➕ Добавление в {self.name}", description="Выберите игрока:", color=Color.blue()),
            view=view, ephemeral=True
        )

    @discord.ui.button(label="Отмена", style=ButtonStyle.danger, emoji="❌", custom_id="add_member_cancel")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="❌ Отменено.", embed=None, view=None)


class CompositionMemberSelect(View):
    def __init__(self, composition_id: int, name: str, main_slots: int, reserve_slots: int, characters: list):
        super().__init__(timeout=60)
        self.composition_id = composition_id
        self.name = name
        self.main_slots = main_slots
        self.reserve_slots = reserve_slots
        
        characters.sort(key=lambda x: (0 if x.get('is_main', True) else 1, x['priority'], -x['item_level']))
        
        select = Select(placeholder="Выберите персонажа", custom_id="comp_member_select")
        options = []
        for char in characters[:25]:
            main_tag = "⭐ " if char.get('is_main', True) else "🔄 "
            raid_roles_text = format_raid_roles(char.get('raid_role', 'mdd'))
            options.append(discord.SelectOption(
                label=f"{main_tag}{char['character_name']} ({char['user_name']})",
                value=str(char['character_id']),
                description=f"{char['class_spec']} | {char['item_level']} iLvl | {raid_roles_text}",
                emoji="⭐" if char.get('is_main', True) else "🔄"
            ))
        select.options = options
        
        async def select_callback(interaction: discord.Interaction):
            db = interaction.client.get_db(interaction.guild_id)
            if not db:
                await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
                return
            character_id = int(interaction.data['values'][0])
            selected = None
            for char in characters:
                if char['character_id'] == character_id:
                    selected = char
                    break
            if selected:
                raid_roles = selected.get('raid_role', 'mdd').split(',')
                raid_roles = [r.strip() for r in raid_roles if r.strip()]
                
                if len(raid_roles) > 1:
                    view = RoleSelectForCompositionView(
                        self.composition_id, self.name, self.main_slots, self.reserve_slots,
                        selected, raid_roles
                    )
                    embed = Embed(
                        title="🎯 Выберите роль",
                        description=f"У **{selected['character_name']}** несколько ролей. Выберите одну для состава:",
                        color=Color.blue()
                    )
                    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                else:
                    await add_member_to_comp(
                        interaction, self.composition_id, self.name,
                        self.main_slots, self.reserve_slots,
                        selected, raid_roles[0] if raid_roles else 'mdd'
                    )
        
        select.callback = select_callback
        self.add_item(select)
        
        cancel = Button(label="Отмена", style=ButtonStyle.secondary, custom_id="cancel_select")
        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="Отменено.", embed=None, view=None)
        cancel.callback = cancel_callback
        self.add_item(cancel)


class RoleSelectForCompositionView(View):
    def __init__(self, composition_id, name, main_slots, reserve_slots, character, roles):
        super().__init__(timeout=60)
        self.composition_id = composition_id
        self.name = name
        self.main_slots = main_slots
        self.reserve_slots = reserve_slots
        self.character = character
        
        role_names = {"mdd": "⚔️ МДД", "rdd": "🏹 РДД", "tank": "🛡️ Танк", "heal": "💚 Хилл"}
        
        for role in roles:
            role = role.strip()
            if role in role_names:
                btn = Button(
                    label=role_names[role],
                    style=ButtonStyle.primary,
                    custom_id=f"sel_role_{role}_{character['character_id']}"
                )
                btn.callback = self.make_callback(role)
                self.add_item(btn)
    
    def make_callback(self, role):
        async def callback(interaction: discord.Interaction):
            await add_member_to_comp(
                interaction, self.composition_id, self.name,
                self.main_slots, self.reserve_slots,
                self.character, role
            )
            try:
                await interaction.message.delete()
            except: pass
        return callback


async def add_member_to_comp(interaction, composition_id, name, main_slots, reserve_slots, character, selected_role):
    db = interaction.client.get_db(interaction.guild_id)
    if not db:
        await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
        return
    
    members = db.get_composition_members(composition_id)
    main_count = len([m for m in members if not m['is_reserve']])
    
    if main_count >= main_slots:
        await interaction.response.send_message("❌ Состав полный!", ephemeral=True, delete_after=10)
        return
    
    for m in members:
        if m['user_id'] == character['user_id']:
            await interaction.response.send_message("❌ Игрок уже в составе!", ephemeral=True, delete_after=10)
            return
    
    db.add_composition_member(composition_id, character['user_id'], character['character_id'], selected_role, is_reserve=False)
    await update_composition_display(interaction, composition_id, name, main_slots, reserve_slots)
    
    all_roles_display = format_raid_roles(character.get('raid_role', 'mdd'))
    
    embed = Embed(
        title="✅ Добавлен в состав",
        description=f"**{character['user_name']}**\n{character['character_name']} ({character['class_spec']})\n"
                    f"Роль в составе: {RAID_ROLE_NAMES.get(selected_role, selected_role)}\n"
                    f"Все роли: {all_roles_display}",
        color=Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=5)


class CompositionReserveSelectView(View):
    def __init__(self, composition_id: int, name: str, main_slots: int, reserve_slots: int, members: list):
        super().__init__(timeout=60)
        self.composition_id = composition_id
        self.name = name
        self.main_slots = main_slots
        self.reserve_slots = reserve_slots
        
        select = Select(placeholder="Выберите игрока в резерв", custom_id="comp_reserve_select")
        options = []
        for m in members[:25]:
            user_name = m.get('user_name', f"ID: {m['user_id']}")
            options.append(discord.SelectOption(
                label=f"{m['character_name']} ({user_name})",
                value=str(m['user_id']),
                description=m['class_spec'],
                emoji="📦"
            ))
        select.options = options
        
        async def select_callback(interaction: discord.Interaction):
            db = interaction.client.get_db(interaction.guild_id)
            if not db:
                await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
                return
            user_id = int(interaction.data['values'][0])
            reserve_count = len([m for m in db.get_composition_members(self.composition_id) if m['is_reserve']])
            if reserve_count >= self.reserve_slots:
                await interaction.response.send_message("❌ Резерв полный!", ephemeral=True, delete_after=10)
                return
            db.move_to_reserve(self.composition_id, user_id, True)
            await update_composition_display(interaction, self.composition_id, self.name, self.main_slots, self.reserve_slots)
            try:
                await interaction.message.delete()
            except: pass
            await interaction.response.send_message("📦 Перемещён в резерв", ephemeral=True, delete_after=5)
        
        select.callback = select_callback
        self.add_item(select)
        
        cancel = Button(label="Отмена", style=ButtonStyle.secondary, custom_id="cancel_reserve")
        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="Отменено.", embed=None, view=None)
        cancel.callback = cancel_callback
        self.add_item(cancel)


class CompositionFromReserveSelectView(View):
    def __init__(self, composition_id: int, name: str, main_slots: int, reserve_slots: int, members: list):
        super().__init__(timeout=60)
        self.composition_id = composition_id
        self.name = name
        self.main_slots = main_slots
        self.reserve_slots = reserve_slots
        
        select = Select(placeholder="Выберите игрока в основу", custom_id="comp_from_reserve_select")
        options = []
        for m in members[:25]:
            user_name = m.get('user_name', f"ID: {m['user_id']}")
            options.append(discord.SelectOption(
                label=f"{m['character_name']} ({user_name})",
                value=str(m['user_id']),
                description=m['class_spec'],
                emoji="⬆️"
            ))
        select.options = options
        
        async def select_callback(interaction: discord.Interaction):
            db = interaction.client.get_db(interaction.guild_id)
            if not db:
                await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
                return
            user_id = int(interaction.data['values'][0])
            main_count = len([m for m in db.get_composition_members(self.composition_id) if not m['is_reserve']])
            if main_count >= self.main_slots:
                await interaction.response.send_message("❌ Основной состав полный!", ephemeral=True, delete_after=10)
                return
            db.move_to_reserve(self.composition_id, user_id, False)
            await update_composition_display(interaction, self.composition_id, self.name, self.main_slots, self.reserve_slots)
            try:
                await interaction.message.delete()
            except: pass
            await interaction.response.send_message("⬆️ Перемещён в основу", ephemeral=True, delete_after=5)
        
        select.callback = select_callback
        self.add_item(select)
        
        cancel = Button(label="Отмена", style=ButtonStyle.secondary, custom_id="cancel_from_reserve")
        async def cancel_callback(interaction: discord.Interaction):
            await interaction.response.edit_message(content="Отменено.", embed=None, view=None)
        cancel.callback = cancel_callback
        self.add_item(cancel)


async def update_composition_display(interaction: discord.Interaction, composition_id: int, name: str, main_slots: int, reserve_slots: int):
    db = interaction.client.get_db(interaction.guild_id)
    if not db:
        return
    
    members = db.get_composition_members(composition_id)
    
    main_roster = [m for m in members if not m['is_reserve']]
    reserves = [m for m in members if m['is_reserve']]
    
    for m in members:
        user = interaction.guild.get_member(m['user_id'])
        m['user_name'] = user.display_name if user else f"ID: {m['user_id']}"
    
    composition = db.get_composition(composition_id)
    leader_name = f"<@{composition['leader_id']}>" if composition else "Не назначен"
    is_closed = composition['status'] == 'closed' if composition else False
    
    embed = Embed(
        title=f"📋 {name}" + (" 🔒" if is_closed else ""),
        description=f"**Лидер:** {leader_name}\n**Основа:** {len(main_roster)}/{main_slots} | **Резерв:** {len(reserves)}/{reserve_slots}"
                    + ("\n**Статус:** ЗАКРЫТ" if is_closed else ""),
        color=Color.red() if is_closed else (Color.green() if len(main_roster) == main_slots else Color.orange()),
        timestamp=discord.utils.utcnow()
    )
    
    for role_key, emoji, label in [('tank', '🛡️', 'Танки'), ('heal', '💚', 'Хилы'), ('mdd', '⚔️', 'МДД'), ('rdd', '🏹', 'РДД')]:
        group = [m for m in main_roster if m['role'] == role_key]
        if group:
            embed.add_field(
                name=f"{emoji} {label} ({len(group)})",
                value="\n".join([f"{emoji} **{m['character_name']}** ({m['class_spec']}) - {m['user_name']}" for m in group]),
                inline=False
            )
    
    if reserves:
        reserves_text = ""
        for m in reserves:
            icon = {"tank": "🛡️", "heal": "💚", "mdd": "⚔️", "rdd": "🏹"}.get(m['role'], "⚔️")
            reserves_text += f"{icon} **{m['character_name']}** ({m['class_spec']}) - {m['user_name']} (резерв)\n"
        embed.add_field(name=f"📦 Резерв ({len(reserves)})", value=reserves_text, inline=False)
    
    embed.set_footer(text=f"ID состава: {composition_id}")
    
    display_ch_id = utils.safe_int(db.get_setting('composition_channel', ''))
    
    if composition and composition.get('message_id') and composition.get('channel_id'):
        try:
            channel = interaction.guild.get_channel(composition['channel_id'])
            if channel:
                msg = await channel.fetch_message(composition['message_id'])
                await msg.edit(embed=embed, view=None)
                return
        except: pass
    
    if display_ch_id:
        channel = interaction.guild.get_channel(display_ch_id)
        if channel:
            msg = await channel.send(embed=embed)
            db.save_composition_message(composition_id, channel.id, msg.id)