import discord
from discord.ui import View, Button, Select
from discord import ButtonStyle, Color, Embed
import utils
from constants import CLASS_SPECS, RAID_ROLE_NAMES


class ClassSettingsView(View):
    """Настройка классов и их ролей в рейде"""
    def __init__(self):
        super().__init__(timeout=120)
        self.update_select()

    def update_select(self):
        """Обновляет список классов"""
        self.clear_items()
        options = []
        for class_name in sorted(CLASS_SPECS.keys()):
            options.append(discord.SelectOption(
                label=class_name,
                value=class_name,
                description=f"Специализаций: {len(CLASS_SPECS[class_name])}",
                emoji="⚔️"
            ))
        
        select = Select(
            placeholder="Выберите класс для настройки ролей",
            options=options[:25],
            custom_id="select_class_to_edit"
        )
        select.callback = self.on_select_class
        self.add_item(select)
        
        back_btn = Button(
            label="🔙 Назад",
            style=ButtonStyle.secondary,
            custom_id="back_to_settings"
        )
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def on_select_class(self, interaction: discord.Interaction):
        class_name = interaction.data['values'][0]
        specs = CLASS_SPECS.get(class_name, [])
        db = interaction.client.get_db(interaction.guild_id)
        
        embed = Embed(
            title=f"⚔️ {class_name}",
            description="Нажмите на специализацию чтобы изменить её роль в рейде:\n",
            color=Color.blue()
        )
        
        for spec in specs:
            role_key = db.get_setting(f"spec_role_{class_name}_{spec}", 'mdd')
            role_name = RAID_ROLE_NAMES.get(role_key, role_key)
            embed.description += f"\n🎯 **{spec}** → {role_name}"
        
        embed.set_footer(text=f"Специализаций: {len(specs)}")
        
        view = SpecRoleView(class_name, specs)
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_callback(self, interaction: discord.Interaction):
        embed = Embed(title="⚙️ Панель управления", description="Выберите раздел:", color=Color.blue())
        from views.settings import SettingsView
        await interaction.response.edit_message(embed=embed, view=SettingsView())


class SpecRoleView(View):
    """Выбор роли для специализации"""
    def __init__(self, class_name: str, specs: list):
        super().__init__(timeout=120)
        self.class_name = class_name
        
        options = []
        for spec in specs:
            options.append(discord.SelectOption(
                label=spec,
                value=f"{class_name}|{spec}",
                description="Нажмите чтобы изменить роль",
                emoji="🎯"
            ))
        
        if options:
            select = Select(
                placeholder="Выберите специализацию для настройки роли",
                options=options[:25],
                custom_id="select_spec_for_role"
            )
            select.callback = self.on_select_spec
            self.add_item(select)
        
        back_btn = Button(
            label="🔙 Назад к классам",
            style=ButtonStyle.secondary,
            custom_id="back_to_classes"
        )
        back_btn.callback = self.back_callback
        self.add_item(back_btn)
    
    async def on_select_spec(self, interaction: discord.Interaction):
        value = interaction.data['values'][0]
        class_name, spec_name = value.split("|", 1)
        
        view = RoleSelectView(class_name, spec_name)
        embed = Embed(
            title=f"🎯 {class_name} — {spec_name}",
            description="Выберите роль в рейде для этой специализации:",
            color=Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=view)
    
    async def back_callback(self, interaction: discord.Interaction):
        embed = Embed(
            title="⚔️ Классы и роли в рейде",
            description="Выберите класс:\n\n" + "\n".join([f"• {c}" for c in sorted(CLASS_SPECS.keys())]),
            color=Color.blue()
        )
        view = ClassSettingsView()
        await interaction.response.edit_message(embed=embed, view=view)


class RoleSelectView(View):
    """Выбор роли: танк, хил, мдд, рдд"""
    def __init__(self, class_name: str, spec_name: str):
        super().__init__(timeout=60)
        self.class_name = class_name
        self.spec_name = spec_name
    
    @discord.ui.select(
        placeholder="Выберите роль в рейде",
        options=[
            discord.SelectOption(label="🗡️ МДД (Милли ДД)", value="mdd", emoji="🗡️"),
            discord.SelectOption(label="🏹 РДД (Ренж ДД)", value="rdd", emoji="🏹"),
            discord.SelectOption(label="🛡️ Танк", value="tank", emoji="🛡️"),
            discord.SelectOption(label="💚 Хиллер", value="heal", emoji="💚"),
        ],
        custom_id="select_raid_role"
    )
    async def select_role(self, interaction: discord.Interaction, select: Select):
        role = interaction.data['values'][0]
        db = interaction.client.get_db(interaction.guild_id)
        
        # Сохраняем настройку
        key = f"spec_role_{self.class_name}_{self.spec_name}"
        db.set_setting(key, role)
        
        role_name = RAID_ROLE_NAMES.get(role, role)
        
        embed = Embed(
            title="✅ Сохранено!",
            description=f"**{self.class_name}** — **{self.spec_name}** → {role_name}",
            color=Color.green()
        )
        
        specs = CLASS_SPECS.get(self.class_name, [])
        embed.add_field(
            name="Специализации класса",
            value="\n".join([
                f"🎯 **{s}** → {RAID_ROLE_NAMES.get(db.get_setting(f'spec_role_{self.class_name}_{s}', 'mdd'), 'mdd')}"
                for s in specs
            ]),
            inline=False
        )
        
        view = SpecRoleView(self.class_name, specs)
        await interaction.response.edit_message(embed=embed, view=view)
    
    @discord.ui.button(label="🔙 Назад", style=ButtonStyle.secondary, custom_id="back_to_specs")
    async def back(self, interaction: discord.Interaction, button: Button):
        specs = CLASS_SPECS.get(self.class_name, [])
        db = interaction.client.get_db(interaction.guild_id)
        
        embed = Embed(title=f"⚔️ {self.class_name}", color=Color.blue())
        for spec in specs:
            role_key = db.get_setting(f"spec_role_{self.class_name}_{spec}", 'mdd')
            role_name = RAID_ROLE_NAMES.get(role_key, role_key)
            embed.description = (embed.description or "") + f"\n🎯 **{spec}** → {role_name}"
        
        embed.set_footer(text=f"Специализаций: {len(specs)}")
        view = SpecRoleView(self.class_name, specs)
        await interaction.response.edit_message(embed=embed, view=view)