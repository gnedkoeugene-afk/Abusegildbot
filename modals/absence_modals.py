# modals/absence_modals.py — ИСПРАВЛЕННАЯ ВЕРСИЯ

import discord
from discord.ui import Modal, TextInput
from discord import TextStyle
from datetime import datetime, timedelta
import utils


class AbsenceModal(Modal):
    """Заявка на отсутствие"""
    
    def __init__(self):
        super().__init__(title="📝 Запланировать отсутствие", timeout=None)
        
        self.add_item(TextInput(
            label="📅 Даты (ДД или ДД-ДД, например: 23 или 23-27)",
            placeholder="23 или 23-27 или 28-03",
            required=True,
            max_length=11
        ))
        self.add_item(TextInput(
            label="📅 Месяц (цифра, если не текущий)",
            placeholder="5 = Май. Пусто = текущий",
            required=False,
            max_length=2
        ))
        self.add_item(TextInput(
            label="📝 Причина",
            placeholder="Опишите причину...",
            style=TextStyle.paragraph,
            required=True,
            max_length=500
        ))
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.followup.send("❌ Ошибка БД!", ephemeral=True)
            return
        
        dates_input = self.children[0].value.strip()
        month_input = self.children[1].value.strip()
        reason = self.children[2].value.strip()
        
        # Парсим даты
        try:
            if '-' in dates_input:
                # Диапазон: ДД-ДД
                parts = dates_input.split('-')
                if len(parts) != 2:
                    raise ValueError
                start_day = int(parts[0].strip())
                end_day = int(parts[1].strip())
            else:
                # Один день
                start_day = int(dates_input.strip())
                end_day = start_day
            
            if start_day < 1 or start_day > 31 or end_day < 1 or end_day > 31:
                raise ValueError
        except ValueError:
            await interaction.followup.send(
                "❌ Формат: **ДД** (один день) или **ДД-ДД** (диапазон)\n"
                "Например: `23` или `23-27`",
                ephemeral=True
            )
            return
        
        today = datetime.now()
        
        # Определяем месяц и год
        if month_input:
            try:
                month = int(month_input)
                if month < 1 or month > 12:
                    raise ValueError
            except ValueError:
                await interaction.followup.send("❌ Месяц от 1 до 12!", ephemeral=True)
                return
            year = today.year if month >= today.month else today.year + 1
        else:
            month = today.month
            year = today.year
            # Если день уже прошёл в этом месяце — переносим на следующий
            if start_day < today.day:
                month += 1
                if month > 12:
                    month = 1
                    year += 1
        
        # Проверяем переход через месяц
        crosses_month = (end_day < start_day) and ('-' in dates_input)
        
        try:
            start_date = datetime(year, month, start_day)
            if crosses_month:
                end_month = month + 1 if month < 12 else 1
                end_year = year + 1 if month == 12 else year
                end_date = datetime(end_year, end_month, end_day)
            else:
                end_date = datetime(year, month, end_day)
        except ValueError as e:
            await interaction.followup.send(f"❌ Неверная дата! ({str(e)})", ephemeral=True)
            return
        
        if end_date < start_date:
            await interaction.followup.send("❌ Дата окончания раньше начала!", ephemeral=True)
            return
        
        if end_date < today - timedelta(days=1):
            await interaction.followup.send("❌ Нельзя указать прошедшую дату!", ephemeral=True)
            return
        
        # Проверяем лимиты
        new_days = (end_date - max(start_date, today)).days + 1
        limits = db.get_absence_limits()
        
        if limits['consecutive'] > 0 and new_days > limits['consecutive']:
            await interaction.followup.send(
                f"❌ Максимум дней подряд: **{limits['consecutive']}** дн. (у вас {new_days})",
                ephemeral=True
            )
            return
        
        # Проверка лимита в месяце
        month_start = today.replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        used = db.get_user_absence_days_in_period_excluding_lates(
            interaction.user.id, month_start, month_end
        )
        
        new_in_month = 0
        check_s = max(start_date, month_start)
        check_e = min(end_date, month_end)
        if check_s <= check_e:
            new_in_month = (check_e - check_s).days + 1
        
        if limits['month'] > 0 and used + new_in_month > limits['month']:
            await interaction.followup.send(
                f"❌ Лимит месяца: **{used}/{limits['month']}** дн. (+{new_in_month} новых)",
                ephemeral=True
            )
            return
        
        start_str = start_date.strftime('%d.%m.%Y')
        end_str = end_date.strftime('%d.%m.%Y')
        
        # Сохраняем
        db.add_absence_simple(interaction.user.id, start_str, end_str, reason)
        
        # Выдаём роль отсутствия
        role_id = db.get_setting('absence_role', '') or db.get_setting('afk_role', '')
        if role_id:
            try:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    await interaction.user.add_roles(role, reason=f"Отсутствие: {reason[:50]}")
            except Exception as e:
                print(f"❌ Ошибка выдачи роли: {e}")
        
        # Обновляем календарь
        from views.absences import refresh_calendar_for_guild
        await refresh_calendar_for_guild(interaction.guild, db)
        
        # Ответ
        if start_day == end_day:
            await interaction.followup.send(
                f"✅ **Отсутствие запланировано!**\n"
                f"📅 **{start_str}** (1 день)\n"
                f"📊 Месяц: **{used + new_in_month}/{limits['month']}** дн.\n"
                f"📝 *{reason[:100]}*",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"✅ **Отсутствие запланировано!**\n"
                f"📅 **{start_str}** → **{end_str}** ({new_days} дн.)\n"
                f"📊 Месяц: **{used + new_in_month}/{limits['month']}** дн.\n"
                f"📝 *{reason[:100]}*",
                ephemeral=True
            )


class LateModal(Modal):
    """Опоздание — часы и минуты отдельно"""
    
    def __init__(self):
        super().__init__(title="⚠️ Опаздываю", timeout=None)
        
        self.add_item(TextInput(
            label="📅 Дата (ДД, пусто = сегодня)",
            placeholder="23",
            required=False,
            max_length=2
        ))
        self.add_item(TextInput(
            label="⏰ Часы (сколько часов опоздания)",
            placeholder="1",
            required=False,
            max_length=2
        ))
        self.add_item(TextInput(
            label="🕐 Минуты (сколько минут опоздания)",
            placeholder="30",
            required=False,
            max_length=2
        ))
        self.add_item(TextInput(
            label="📝 Причина (необязательно)",
            placeholder="Пробки, работа...",
            required=False,
            max_length=200
        ))
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        db = interaction.client.get_db(interaction.guild_id)
        if not db:
            await interaction.followup.send("❌ Ошибка БД!", ephemeral=True)
            return
        
        day_input = self.children[0].value.strip()
        hours_input = self.children[1].value.strip()
        minutes_input = self.children[2].value.strip()
        reason = self.children[3].value.strip() or "Не указана"
        
        # Парсим время
        hours = 0
        minutes = 0
        
        if hours_input:
            try:
                hours = int(hours_input)
                if hours < 0 or hours > 24:
                    raise ValueError
            except ValueError:
                await interaction.followup.send("❌ Часы: число от 0 до 24!", ephemeral=True)
                return
        
        if minutes_input:
            try:
                minutes = int(minutes_input)
                if minutes < 0 or minutes > 59:
                    raise ValueError
            except ValueError:
                await interaction.followup.send("❌ Минуты: число от 0 до 59!", ephemeral=True)
                return
        
        if hours == 0 and minutes == 0:
            await interaction.followup.send("❌ Укажите хотя бы часы или минуты!", ephemeral=True)
            return
        
        # Формируем читаемое время
        time_parts = []
        if hours > 0:
            time_parts.append(f"{hours} ч.")
        if minutes > 0:
            time_parts.append(f"{minutes} мин.")
        late_time = " ".join(time_parts)
        
        # Общее количество минут для авто-завершения
        total_minutes = hours * 60 + minutes
        
        today = datetime.now()
        
        if day_input:
            try:
                day = int(day_input)
                if day < 1 or day > 31:
                    raise ValueError
                if day >= today.day:
                    date = datetime(today.year, today.month, day)
                else:
                    if today.month == 12:
                        date = datetime(today.year + 1, 1, day)
                    else:
                        date = datetime(today.year, today.month + 1, day)
            except ValueError:
                await interaction.followup.send("❌ Неверный день!", ephemeral=True)
                return
        else:
            date = today
        
        date_str = date.strftime('%d.%m.%Y')
        
        # Формируем причину
        full_reason = f"⚠️ Опоздание: {late_time}"
        if reason != "Не указана":
            full_reason += f" ({reason})"
        
        # Сохраняем с авто-завершением
        db.add_absence_with_auto_complete(
            interaction.user.id, date_str, date_str, full_reason, total_minutes
        )
        
        # Обновляем календарь
        from views.absences import refresh_calendar_for_guild
        await refresh_calendar_for_guild(interaction.guild, db)
        
        # Ответ
        if total_minutes > 0:
            await interaction.followup.send(
                f"✅ **Опоздание отмечено!**\n"
                f"📅 {date_str}\n"
                f"⏰ **{late_time}**\n"
                f"🕐 Автозавершение через {late_time}",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"✅ **Опоздание отмечено!**\n"
                f"📅 {date_str}\n"
                f"⏰ **{late_time}**",
                ephemeral=True
            )