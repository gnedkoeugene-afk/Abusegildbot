# modals/report_modals.py — ПОЛНЫЙ ФАЙЛ (ФИНАЛЬНЫЙ С ПРАВИЛЬНЫМ ВРЕМЕНЕМ)

import discord
from discord.ui import Modal, TextInput
from discord import TextStyle, Color, Embed
from datetime import datetime, timedelta, timezone
import utils

# Часовой пояс (UTC+3 — Москва, Минск, Киев)
LOCAL_TZ = timezone(timedelta(hours=3))


class ReportModal(Modal):
    """Модальное окно для подачи жалобы"""

    def __init__(self, target_user_id: int = None, target_user_name: str = None):
        super().__init__(title="⚠️ Подать жалобу", timeout=None)
        self.target_user_id = target_user_id
        self.target_user_name = target_user_name

        if target_user_name:
            self.title = f"⚠️ Жалоба на {target_user_name[:20]}"

        self.add_item(TextInput(
            label="👤 Нарушитель (@упоминание или имя)",
            placeholder="@Участник или никнейм",
            default=f"<@{target_user_id}>" if target_user_id else "",
            required=True,
            max_length=100
        ))
        self.add_item(TextInput(
            label="📋 Тип нарушения",
            placeholder="Оскорбления / Срыв рейда / Токсичность / Другое",
            required=True,
            max_length=50
        ))
        self.add_item(TextInput(
            label="📝 Подробное описание ситуации",
            placeholder="Опишите что произошло, когда и где...",
            style=TextStyle.paragraph,
            required=True,
            max_length=1000
        ))
        self.add_item(TextInput(
            label="📎 Доказательства (ссылки)",
            placeholder="https://imgur.com/...",
            style=TextStyle.paragraph,
            required=False,
            max_length=500
        ))
        self.add_item(TextInput(
            label="🕶️ Анонимно? (да/нет)",
            placeholder="нет",
            required=False,
            max_length=3,
            default="нет"
        ))

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.followup.send("❌ БД не найдена!", ephemeral=True)
            return

        guild = interaction.guild
        now = datetime.now(LOCAL_TZ)

        violator_text = self.children[0].value.strip()
        violation_type = self.children[1].value.strip()
        description = self.children[2].value.strip()
        evidence = self.children[3].value.strip() or "Не предоставлены"
        anonymous_str = self.children[4].value.strip().lower()
        is_anonymous = anonymous_str in ('да', 'yes', '1', 'ага')

        # Поиск нарушителя
        violator_id = None
        violator_name = violator_text

        if violator_text.startswith('<@') and violator_text.endswith('>'):
            id_part = violator_text[2:-1].replace('!', '')
            if id_part.isdigit():
                violator_id = int(id_part)
                violator = guild.get_member(violator_id)
                violator_name = violator.display_name if violator else f"ID:{violator_id}"

        if not violator_id:
            for member in guild.members:
                if violator_text.lower() in member.display_name.lower() or \
                   violator_text.lower() in member.name.lower():
                    violator_id = member.id
                    violator_name = member.display_name
                    break

        # Категория
        category_id = utils.safe_int(db.get_setting('reports_category', ''))
        category = guild.get_channel(category_id) if category_id else None
        if not category:
            category = await guild.create_category_channel("⚠️ Жалобы")
            db.set_setting('reports_category', str(category.id))

        report_id = db.get_next_report_id()

        # Права доступа
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
        }
        if not is_anonymous:
            overwrites[interaction.user] = discord.PermissionOverwrite(
                read_messages=True, send_messages=True
            )
        for role_id in db.get_reports_roles():
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True
                )

        channel = await guild.create_text_channel(
            f'⚠️-жалоба-{report_id}',
            category=category,
            overwrites=overwrites,
            topic=f"Жалоба #{report_id} | {'Аноним' if is_anonymous else interaction.user.display_name}"
        )

        db.create_report(
            report_id=report_id, reporter_id=interaction.user.id,
            violator_id=violator_id, violator_name=violator_name,
            violation_type=violation_type, description=description,
            evidence=evidence, witnesses="", channel_id=channel.id,
            is_anonymous=is_anonymous
        )

        # ═══════════════════════════════════════════════════════
        # 🎨 КРАСИВЫЙ EMBED ЖАЛОБЫ
        # ═══════════════════════════════════════════════════════

        # Цвет по типу нарушения
        type_colors = {
            "оскорбления": Color.red(),
            "срыв": Color.orange(),
            "токсичность": Color.purple(),
            "спам": Color.dark_red(),
            "рейд": Color.orange(),
            "лут": Color.gold(),
            "ниндзя": Color.gold(),
        }
        embed_color = Color.orange()
        for key, col in type_colors.items():
            if key in violation_type.lower():
                embed_color = col
                break

        # Иконка типа
        type_icon = "📋"
        vt_lower = violation_type.lower()
        if "срыв" in vt_lower: type_icon = "⚔️"
        elif "токсич" in vt_lower: type_icon = "😡"
        elif "оскорбл" in vt_lower: type_icon = "🤬"
        elif "спам" in vt_lower: type_icon = "📢"
        elif "рейд" in vt_lower: type_icon = "🎯"
        elif "лут" in vt_lower or "ниндзя" in vt_lower: type_icon = "💎"

        # Заявитель
        if is_anonymous:
            reporter_display = f"🕶️ **Анонимно**"
            reporter_sub = f"└─ 🔑 **{interaction.user.display_name}**"
        else:
            reporter_display = f"👤 {interaction.user.mention}"
            reporter_sub = f"└─ 🏷️ **{interaction.user.display_name}**"

        embed = Embed(
            title=f"╔══════════════════════════╗\n"
                  f"║  ⚠️  ЖАЛОБА  #{report_id}  ║\n"
                  f"╚══════════════════════════╝",
            color=embed_color,
            timestamp=now
        )

        # Статус-бар
        embed.add_field(
            name="",
            value=f"```ansi\n[1;37m▐[0m[1;31m НА РАССМОТРЕНИИ [0m[1;37m▌[0m\n```",
            inline=False
        )

        # Карточки
        embed.add_field(
            name="👤 ЗАЯВИТЕЛЬ",
            value=f"{reporter_display}\n{reporter_sub}" if reporter_sub else reporter_display,
            inline=True
        )
        embed.add_field(
            name="🎯 НАРУШИТЕЛЬ",
            value=f"👤 **{violator_name}**",
            inline=True
        )
        embed.add_field(
            name=f"{type_icon} ТИП НАРУШЕНИЯ",
            value=f"```{violation_type}```",
            inline=True
        )

        # Разделитель
        embed.add_field(name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", value="", inline=False)

        # Описание
        embed.add_field(
            name="📝 ОПИСАНИЕ НАРУШЕНИЯ",
            value=f"```{description[:1000]}```",
            inline=False
        )

        # Доказательства
        if evidence != "Не предоставлены":
            embed.add_field(name="📎 ДОКАЗАТЕЛЬСТВА", value=evidence[:1024], inline=False)
            embed.add_field(name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", value="", inline=False)

        # Статус и дата
        embed.add_field(name="📊 СТАТУС", value="🔴 **На рассмотрении**", inline=True)
        embed.add_field(name="⏳ ОЖИДАЕТ", value="Решения модератора", inline=True)
        embed.add_field(name="📅 ДАТА", value=f"📥 {now.strftime('%d.%m.%Y %H:%M')}", inline=True)

        embed.set_footer(
            text=f"ID: {report_id} | {interaction.guild.name} | Используйте кнопки ниже",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )

        # Кнопки
        from views.reports import ReportReviewView
        view = ReportReviewView(
            report_id=report_id, reporter_id=interaction.user.id,
            violator_id=violator_id, channel_id=channel.id,
            is_anonymous=is_anonymous
        )

        # Упоминания
        mentions = []
        for role_id in db.get_reports_roles():
            role = guild.get_role(role_id)
            if role:
                mentions.append(role.mention)

        if mentions:
            msg = await channel.send(content=" ".join(mentions), embed=embed, view=view)
        else:
            msg = await channel.send(embed=embed, view=view)

        # Регистрируем View
        interaction.client.add_view(view, message_id=msg.id)

        # Сохраняем
        import app
        app.active_reports[msg.id] = {
            'report_id': report_id, 'reporter_id': interaction.user.id,
            'violator_id': violator_id, 'channel_id': channel.id,
            'is_anonymous': is_anonymous, 'guild_id': interaction.guild_id,
            'message_id': msg.id
        }
        app.save_active_reports()

        db.add_log("⚠️ Жалоба", interaction.user.id, violator_id, f"Жалоба #{report_id}: {violation_type}")

        await interaction.followup.send(
            f"✅ **Жалоба #{report_id} создана!**\n\n"
            f"📁 Канал: {channel.mention}\n"
            f"👤 Нарушитель: **{violator_name}**\n"
            f"📋 Тип: **{violation_type}**\n"
            f"{'🕶️ Анонимно' if is_anonymous else ''}\n\n"
            f"⏳ Результат придёт в личные сообщения.",
            ephemeral=True
        )


class ReportResolveModal(Modal):
    """Модальное окно для решения жалобы"""

    def __init__(self, report_id: int, channel_id: int, action: str,
                 reporter_id: int, is_anonymous: bool):
        action_text = "✅ Принять" if action == 'resolve' else "❌ Отклонить"
        super().__init__(title=f"{action_text}: Жалоба #{report_id}")
        self.report_id = report_id
        self.channel_id = channel_id
        self.action = action
        self.reporter_id = reporter_id
        self.is_anonymous = is_anonymous

        self.add_item(TextInput(
            label="💬 Комментарий к решению",
            placeholder="Опишите принятые меры или причину отклонения...",
            style=TextStyle.paragraph,
            required=True,
            max_length=500
        ))

    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
        except:
            pass

        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            try:
                await interaction.followup.send("❌ БД не найдена!", ephemeral=True)
            except:
                pass
            return

        now = datetime.now(LOCAL_TZ)
        comment = self.children[0].value.strip()
        new_status = 'resolved' if self.action == 'resolve' else 'rejected'
        status_text = "ПРИНЯТО" if new_status == 'resolved' else "ОТКЛОНЕНО"
        status_color = Color.green() if new_status == 'resolved' else Color.red()
        status_emoji = "✅" if new_status == 'resolved' else "❌"

        # Обновляем БД
        try:
            db.update_report_status(self.report_id, new_status, interaction.user.id, comment)
            db.set_setting(f'report_{self.report_id}_resolved_at', now.isoformat())
        except Exception as e:
            print(f"❌ Ошибка обновления БД: {e}")

        # Обновляем embed в канале жалобы
        channel = interaction.guild.get_channel(self.channel_id)
        if channel:
            try:
                async for msg in channel.history(limit=20):
                    if msg.author == interaction.client.user and msg.embeds:
                        embed = msg.embeds[0]
                        embed.color = status_color

                        for i, field in enumerate(embed.fields):
                            if field.name == "📊 СТАТУС":
                                embed.set_field_at(i, name="📊 СТАТУС", value=f"{status_emoji} **{status_text}**", inline=True)
                            if field.name == "⏳ ОЖИДАЕТ":
                                embed.set_field_at(i, name="👮 МОДЕРАТОР", value=interaction.user.mention, inline=True)

                        embed.add_field(name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", value="", inline=False)
                        embed.add_field(
                            name=f"{status_emoji} РЕШЕНИЕ",
                            value=f"**Модератор:** {interaction.user.mention}\n"
                                  f"**Дата:** {now.strftime('%d.%m.%Y %H:%M')}\n\n```{comment}```",
                            inline=False
                        )
                        embed.set_footer(text=f"ID: {self.report_id} | {status_text} | Автоудаление через 1 час")
                        await msg.edit(embed=embed, view=None)

                        if hasattr(interaction.client, 'remove_active_report'):
                            interaction.client.remove_active_report(msg.id)
                        break
            except Exception as e:
                print(f"❌ Ошибка обновления embed: {e}")


        # ═══════════════════════════════════════════════════════
        # 📁 АРХИВ ЖАЛОБЫ — ПРЕМИУМ ДИЗАЙН
        # ═══════════════════════════════════════════════════════
        try:
            archive_channel_id = utils.safe_int(db.get_setting('archive_channel', ''))
            if archive_channel_id:
                archive_channel = interaction.guild.get_channel(archive_channel_id)
                if archive_channel:
                    report = db.get_report_by_id(self.report_id)
                    if report:
                        if new_status == 'resolved':
                            accent_color = Color.green()
                            status_title = "ЖАЛОБА ПРИНЯТА"
                        else:
                            accent_color = Color.red()
                            status_title = "ЖАЛОБА ОТКЛОНЕНА"

                        if report.get('is_anonymous'):
                            reporter_display = f"🕶️ **Анонимно**"
                            reporter_sub = f"└─ 🔑 {report.get('reporter_name', 'Неизвестно')}"
                        else:
                            reporter = interaction.guild.get_member(report.get('reporter_id'))
                            if reporter:
                                reporter_display = f"👤 {reporter.mention}"
                                reporter_sub = f"└─ 🏷️ **{reporter.display_name}**"
                            else:
                                reporter_display = "👤 Неизвестно"
                                reporter_sub = ""

                        violation_type = report.get('violation_type', 'Не указан')
                        type_icon = "📋"
                        vt_lower = violation_type.lower()
                        if "срыв" in vt_lower: type_icon = "⚔️"
                        elif "токсич" in vt_lower: type_icon = "😡"
                        elif "оскорбл" in vt_lower: type_icon = "🤬"
                        elif "спам" in vt_lower: type_icon = "📢"
                        elif "рейд" in vt_lower: type_icon = "🎯"

                        description_text = report.get('description', '')
                        if len(description_text) > 400:
                            description_text = description_text[:397] + "..."

                        evidence_text = report.get('evidence', 'Не предоставлены')
                        if evidence_text and evidence_text != 'Не предоставлены' and len(evidence_text) > 200:
                            evidence_text = evidence_text[:197] + "..."

                        try:
                            created_at = report.get('created_at')
                            if isinstance(created_at, str):
                                # SQLite возвращает строку, пробуем разные форматы
                                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                                    try:
                                        created_at_dt = datetime.strptime(created_at, fmt)
                                        created_at_dt = created_at_dt.replace(tzinfo=None)
                                        break
                                    except:
                                        created_at_dt = None
                                if not created_at_dt:
                                    created_at_dt = datetime.fromisoformat(created_at)
                            else:
                                created_at_dt = created_at
                            
                            # Приводим к локальному времени если нужно
                            if created_at_dt and created_at_dt.tzinfo is None:
                                created_at_dt = created_at_dt.replace(tzinfo=timezone.utc).astimezone(LOCAL_TZ)
                            
                            delta = now - created_at_dt.replace(tzinfo=None) if created_at_dt and created_at_dt.tzinfo else now - created_at_dt
                            hours = int(delta.total_seconds() // 3600)
                            minutes = int((delta.total_seconds() % 3600) // 60)
                            if hours > 0:
                                resolution_time = f"{hours} ч. {minutes} мин."
                            else:
                                resolution_time = f"{minutes} мин."
                        except:
                            resolution_time = "—"
                            created_at_dt = None

                        embed = Embed(
                            title=f"╔══════════════════════════════╗\n"
                                  f"║  📁  АРХИВ ЖАЛОБЫ  #{self.report_id}  ║\n"
                                  f"╚══════════════════════════════╝",
                            color=accent_color,
                            timestamp=now
                        )

                        embed.add_field(
                            name="",
                            value=f"```ansi\n[1;37m▐[0m[1;{'32' if new_status == 'resolved' else '31'}m {status_title} [0m[1;37m▌[0m\n```",
                            inline=False
                        )

                        embed.add_field(
                            name="👤 ЗАЯВИТЕЛЬ",
                            value=f"{reporter_display}\n{reporter_sub}" if reporter_sub else reporter_display,
                            inline=True
                        )
                        embed.add_field(
                            name="🎯 НАРУШИТЕЛЬ",
                            value=f"👤 **{report.get('violator_name', 'Неизвестно')}**",
                            inline=True
                        )
                        embed.add_field(
                            name=f"{type_icon} ТИП",
                            value=f"```{violation_type}```",
                            inline=True
                        )

                        embed.add_field(name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", value="", inline=False)
                        embed.add_field(name="📝 ОПИСАНИЕ НАРУШЕНИЯ", value=f"```{description_text}```", inline=False)

                        if evidence_text and evidence_text != 'Не предоставлены':
                            embed.add_field(name="📎 ДОКАЗАТЕЛЬСТВА", value=evidence_text[:1024], inline=False)
                            embed.add_field(name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", value="", inline=False)

                        embed.add_field(
                            name=f"{status_emoji} РЕШЕНИЕ МОДЕРАТОРА",
                            value=f"**Модератор:** {interaction.user.mention}\n"
                                  f"**Дата:** {now.strftime('%d.%m.%Y в %H:%M')}\n\n```{comment}```",
                            inline=False
                        )

                        embed.add_field(name="▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬", value="", inline=False)

                        created_str = created_at_dt.strftime('%d.%m.%Y в %H:%M') if created_at_dt else str(report.get('created_at', '—'))

                        embed.add_field(
                            name="⏱️ ХРОНОЛОГИЯ",
                            value=f"📥 **Создана:** {created_str}\n"
                                  f"📤 **Решена:** {now.strftime('%d.%m.%Y в %H:%M')}\n"
                                  f"⏳ **Рассмотрение:** {resolution_time}",
                            inline=True
                        )
                        embed.add_field(
                            name="📊 ИНФО",
                            value=f"🔢 **ID:** {self.report_id}\n"
                                  f"🏰 **Гильдия:** {interaction.guild.name}",
                            inline=True
                        )

                        embed.set_footer(
                            text=f"Архив жалоб • {interaction.guild.name} • {now.strftime('%d.%m.%Y')}",
                            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
                        )

                        await archive_channel.send(embed=embed)
        except Exception as e:
            print(f"❌ Ошибка архива: {e}")

        # ═══════════════════════════════════════════════════════
        # ✉️ УВЕДОМЛЕНИЕ АВТОРУ
        # ═══════════════════════════════════════════════════════
        try:
            report = db.get_report_by_id(self.report_id)
            if report:
                reporter = interaction.guild.get_member(report.get('reporter_id'))
                if reporter:
                    status_word = "одобрена" if new_status == 'resolved' else "отклонена"
                    try:
                        await reporter.send(embed=Embed(
                            title=f"{status_emoji} Ваша жалоба #{self.report_id} {status_word}",
                            description=(
                                f"**Сервер:** {interaction.guild.name}\n\n"
                                f"**Результат:**\n```{comment}```\n\n"
                                f"**Модератор:** {interaction.user.mention}\n"
                                f"**Дата:** {now.strftime('%d.%m.%Y %H:%M')}\n\n"
                                f"💙 Спасибо за обращение!"
                            ),
                            color=status_color,
                            timestamp=now
                        ))
                    except:
                        pass
        except Exception as e:
            print(f"❌ Ошибка уведомления: {e}")

        # Лог
        try:
            db.add_log(f"{status_emoji} Жалоба", interaction.user.id, details=f"#{self.report_id}: {comment[:100]}")
        except:
            pass

        # Ответ модератору
        try:
            await interaction.followup.send(f"{status_emoji} Готово! Жалоба #{self.report_id} обработана.", ephemeral=True)
        except:
            pass