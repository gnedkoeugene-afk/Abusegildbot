# modals/composition_modals.py — ПОЛНЫЙ ФАЙЛ С ИСПРАВЛЕНИЯМИ

import discord
from discord.ui import Modal, TextInput, View, Button
from discord import TextStyle, Color, Embed, ButtonStyle
import utils
from constants import RAID_ROLE_NAMES


class CreateCompositionModal(Modal):
    def __init__(self):
        super().__init__(title="Создание нового состава", timeout=None)
        self.add_item(TextInput(label="Название состава", placeholder="Например: Зул'Аман", required=True, max_length=50))
        self.add_item(TextInput(label="Количество мест (основа)", placeholder="10", required=True, max_length=2, default="10"))
        self.add_item(TextInput(label="Количество мест (резерв)", placeholder="5", required=True, max_length=2, default="5"))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)  # ← ИСПРАВЛЕНО
        if not db:  # ← ДОБАВЛЕНО
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        name = self.children[0].value.strip()
        
        try:
            main_slots = int(self.children[1].value)
            reserve_slots = int(self.children[2].value)
            if main_slots < 1 or reserve_slots < 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message("❌ Количество мест должно быть положительным числом!", ephemeral=True, delete_after=20)
            return
        
        composition_id = db.create_composition(name, interaction.user.id, main_slots, reserve_slots)
        
        all_characters = db.get_all_main_characters_with_priority(interaction.guild)
        
        if not all_characters:
            await interaction.response.send_message("❌ Нет игроков с основными персонажами!", ephemeral=True, delete_after=20)
            return
        
        embed = Embed(
            title="👑 Выбор лидера состава",
            description=f"Состав **{name}** создан!\n\nВыберите лидера рейда из списка ниже.",
            color=Color.blue()
        )
        
        from views.compositions import SetLeaderSelectView
        view = SetLeaderSelectView(composition_id, name, main_slots, reserve_slots, all_characters)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class CompositionEditModal(Modal):
    def __init__(self, composition_id: int, name: str, main_slots: int, reserve_slots: int, member: dict):
        super().__init__(title=f"✏️ Редактирование {member['character_name']}", timeout=None)
        self.composition_id = composition_id
        self.name = name
        self.main_slots = main_slots
        self.reserve_slots = reserve_slots
        self.member = member
        
        current_role = {"mdd": "МДД", "rdd": "РДД", "tank": "Танк", "heal": "Хилл"}.get(member['role'], "МДД")
        self.add_item(TextInput(label="Новая роль", placeholder="МДД, РДД, Танк или Хилл", default=current_role, required=True, max_length=10))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        role_input = self.children[0].value.strip().lower()
        
        role_map = {"мдд": "mdd", "рдд": "rdd", "танк": "tank", "хилл": "heal", "mdd": "mdd", "rdd": "rdd", "tank": "tank", "heal": "heal"}
        if role_input not in role_map:
            await interaction.response.send_message("❌ Неверная роль!", ephemeral=True, delete_after=20)
            return
        role = role_map[role_input]
        
        db.update_composition_member_role(self.composition_id, self.member['user_id'], role)
        
        from views.compositions import update_composition_display
        await update_composition_display(interaction, self.composition_id, self.name, self.main_slots, self.reserve_slots)
        
        embed = Embed(title="✅ Данные обновлены", description="Роль игрока изменена.", color=Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)


class CompositionRemoveModal(Modal):
    def __init__(self, composition_id: int, name: str, main_slots: int, reserve_slots: int, members: list):
        super().__init__(title="🗑️ Удаление игрока", timeout=None)
        self.composition_id = composition_id
        self.name = name
        self.main_slots = main_slots
        self.reserve_slots = reserve_slots
        
        options = "\n".join([f"- {m['character_name']} ({m['user_name']})" for m in members[:15]])
        self.add_item(TextInput(label="Имя персонажа для удаления", placeholder=options[:100], required=True, max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        char_name = self.children[0].value.strip().lower()
        
        members = db.get_composition_members(self.composition_id)
        found = None
        for m in members:
            if m['character_name'].lower() == char_name:
                found = m
                break
        
        if not found:
            await interaction.response.send_message(f"❌ Персонаж **{char_name}** не найден!", ephemeral=True, delete_after=20)
            return
        
        db.remove_composition_member(self.composition_id, found['user_id'])
        
        from views.compositions import update_composition_display
        await update_composition_display(interaction, self.composition_id, self.name, self.main_slots, self.reserve_slots)
        
        embed = Embed(title="🗑️ Игрок удалён", description=f"**{found['character_name']}** удалён из состава.", color=Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)

class LeaderSearchModal(Modal):
    """Поиск лидера для состава"""
    def __init__(self, composition_id: int, name: str, main_slots: int, reserve_slots: int, parent_view):
        super().__init__(title="🔍 Поиск лидера", timeout=None)
        self.composition_id = composition_id
        self.name = name
        self.main_slots = main_slots
        self.reserve_slots = reserve_slots
        self.parent_view = parent_view
        
        self.add_item(TextInput(
            label="🔍 Имя персонажа или игрока",
            placeholder="Введите имя для поиска...",
            required=True,
            max_length=100
        ))
    
    async def on_submit(self, interaction: discord.Interaction):
        query = self.children[0].value.strip()
        await self.parent_view.filter_by_search(interaction, query)

class DuplicateCompositionModal(Modal):
    def __init__(self, composition_id: int, old_name: str):
        super().__init__(title="📋 Дублирование состава", timeout=None)
        self.composition_id = composition_id
        self.add_item(TextInput(label="Новое название состава", placeholder=f"Копия: {old_name}", required=True, max_length=50))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        new_name = self.children[0].value.strip()
        
        new_id = db.duplicate_composition(self.composition_id, new_name, interaction.user.id)
        composition = db.get_composition(new_id)
        
        embed = Embed(title="✅ Состав продублирован", description=f"Новый состав **{new_name}** создан!\nID: `{new_id}`", color=Color.green())
        await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=10)
        
        from views.compositions import CompositionControlPanel, update_composition_display
        view = CompositionControlPanel(new_id, new_name, composition.get('main_slots', 10), composition.get('reserve_slots', 5))
        panel_embed = Embed(title=f"🎯 Управление составом: {new_name}", description=f"**Лидер:** <@{composition['leader_id']}>", color=Color.blue())
        await interaction.followup.send(embed=panel_embed, view=view, ephemeral=True)
        
        await update_composition_display(interaction, new_id, new_name, composition.get('main_slots', 10), composition.get('reserve_slots', 5))


class CompositionSearchModal(Modal):
    """Модальное окно для поиска игрока в состав"""
    def __init__(self, composition_id: int, name: str, main_slots: int, reserve_slots: int):
        super().__init__(title=f"🔍 Поиск игрока для состава {name}", timeout=None)
        self.composition_id = composition_id
        self.name = name
        self.main_slots = main_slots
        self.reserve_slots = reserve_slots
        
        self.add_item(TextInput(
            label="🔍 Имя персонажа или игрока",
            placeholder="Введите имя для поиска...",
            required=True,
            max_length=100
        ))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        query = self.children[0].value.strip()
        guild = interaction.guild
        
        # Используем поиск как в наказаниях
        results = db.search_characters(query, guild, limit=25)
        
        if not results:
            await interaction.response.send_message(
                f"❌ По запросу **{query}** никого не найдено.\n"
                f"Используйте @имя для поиска по Discord или введите имя персонажа.",
                ephemeral=True, delete_after=20
            )
            return
        
        # Убираем тех, кто уже в составе
        members = db.get_composition_members(self.composition_id)
        member_ids = [m['user_id'] for m in members]
        filtered = [c for c in results if c['user_id'] not in member_ids]
        
        # Добавляем приоритет
        for char in filtered:
            member = guild.get_member(char['user_id'])
            if member:
                char['priority'] = db.get_user_priority_level(member)
            else:
                char['priority'] = 999
        
        if not filtered:
            await interaction.response.send_message(
                f"❌ Все найденные персонажи уже в составе!",
                ephemeral=True, delete_after=20
            )
            return
        
        # Сортируем
        filtered.sort(key=lambda x: (0 if x.get('is_main', True) else 1, x.get('priority', 999), -x.get('item_level', 0)))
        
        # Показываем список
        from views.compositions import CompositionMemberSelect
        view = CompositionMemberSelect(self.composition_id, self.name, self.main_slots, self.reserve_slots, filtered)
        embed = Embed(
            title=f"🔍 Результаты поиска: {len(filtered)} персонажей",
            description=f"По запросу **{query}** найдено персонажей: {len(filtered)}\n\nВыберите персонажа из списка:",
            color=Color.blue()
        )
        
        # Показываем первых 10 в эмбеде для информации
        for i, char in enumerate(filtered[:10], 1):
            main_tag = "⭐" if char.get('is_main', True) else "🔄"
            embed.add_field(
                name=f"{i}. {main_tag} {char['character_name']}",
                value=f"👤 {char['user_name']}\n🎭 {char['class_spec']} | 💎 {char.get('item_level', 0)} iLvl",
                inline=True
            )
        
        # Удаляем предыдущее сообщение (результаты поиска)
        try:
            await interaction.message.delete()
        except:
            pass
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ConfirmAddMemberView(View):
    def __init__(self, composition_id: int, name: str, main_slots: int, reserve_slots: int, character: dict):
        super().__init__(timeout=30)
        self.composition_id = composition_id
        self.name = name
        self.main_slots = main_slots
        self.reserve_slots = reserve_slots
        self.character = character

    @discord.ui.button(label="✅ Добавить", style=ButtonStyle.success, emoji="✅", custom_id="confirm_add_one")
    async def confirm_add(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.response.send_message("❌ Ошибка БД!", ephemeral=True)
            return
        
        char = self.character
        
        members = db.get_composition_members(self.composition_id)
        main_count = len([m for m in members if not m['is_reserve']])
        
        if main_count >= self.main_slots:
            await interaction.response.send_message(f"❌ Основной состав полный!", ephemeral=True, delete_after=20)
            return
        
        # Проверяем, есть ли уже этот ИГРОК в составе
        for m in members:
            if m['user_id'] == char['user_id']:
                await interaction.response.send_message(f"❌ Игрок уже в составе!", ephemeral=True, delete_after=20)
                return
        
        # Добавляем
        db.add_composition_member(self.composition_id, char['user_id'], char['character_id'], char.get('raid_role', 'mdd'), is_reserve=False)
        
        from views.compositions import update_composition_display
        await update_composition_display(interaction, self.composition_id, self.name, self.main_slots, self.reserve_slots)
        
        main_tag = "⭐ Основной" if char.get('is_main', True) else "🔄 Твинк"
        embed = Embed(
            title="✅ Добавлен в состав",
            description=f"**{char['character_name']}** добавлен!\n📌 {main_tag}",
            color=Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="❌ Отмена", style=ButtonStyle.secondary, emoji="❌", custom_id="cancel_add_one")
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(content="❌ Отменено.", embed=None, view=None)