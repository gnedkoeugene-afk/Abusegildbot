import discord
import asyncio
from discord.ui import Modal, TextInput
from discord import TextStyle, Color, Embed
import utils


class AppealModal(Modal):
    def __init__(self):
        super().__init__(title="⚖️ Апелляция", timeout=None)
        self.add_item(TextInput(label="Имя персонажа", placeholder="Введите имя", required=True))
        self.add_item(TextInput(label="Причина апелляции", placeholder="Объясните ситуацию...", style=TextStyle.paragraph, required=True))

    async def on_submit(self, interaction: discord.Interaction):
        db = interaction.client.db
        guild = interaction.guild

        cat_id = utils.safe_int(db.get_setting('appeal_category', ''))
        category = guild.get_channel(cat_id) if cat_id else None
        if not category:
            category = await guild.create_category_channel("⚖️ Апелляции")
            db.set_setting('appeal_category', category.id)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        for role_id in db.get_reviewer_roles():
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        appeal_id = db.get_next_id('appeals')
        channel = await guild.create_text_channel(f'⚖️-апелляция-{appeal_id}', category=category, overwrites=overwrites)

        db.add_appeal(interaction.user.id, channel.id, self.children[0].value, self.children[1].value)

        mentions = [role.mention for role_id in db.get_reviewer_roles() if (role := guild.get_role(role_id))]

        embed = Embed(title=f"⚖️ Апелляция #{appeal_id}", description=f"**Заявитель:** {interaction.user.mention}", color=Color.orange())
        embed.add_field(name="Персонаж", value=self.children[0].value, inline=True)
        embed.add_field(name="Причина", value=self.children[1].value, inline=False)
        embed.set_footer(text=f"Гильдия: {db.get_setting('guild_name', 'Abuse')}")

        from views.appeals import AppealReviewView
        view = AppealReviewView(channel.id, interaction.user.id, appeal_id)
        await channel.send(content=" ".join(mentions) if mentions else None, embed=embed, view=view)

        msg = await interaction.response.send_message(f"✅ Апелляция #{appeal_id} отправлена!", ephemeral=True)
        await asyncio.sleep(20)
        try:
            await msg.delete()
        except:
            pass