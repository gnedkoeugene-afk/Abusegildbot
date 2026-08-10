# views/absences.py — ИСПРАВЛЕННАЯ ВЕРСИЯ

import discord
from discord.ui import View, Button, Select
from discord import ButtonStyle, Color, Embed
from datetime import datetime, timedelta
import calendar
import utils
from zoneinfo import ZoneInfo


# ============================================================
#  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ РАБОТЫ С ДАТАМИ
# ============================================================

# Используем UTC для единообразия
TIMEZONE = ZoneInfo('UTC')  # или 'Europe/Moscow'

def get_now():
    """Получить текущее время в UTC"""
    return datetime.now(TIMEZONE)

def parse_date(date_str: str) -> datetime:
    """Преобразовать строку 'dd.mm.yyyy' в datetime с таймзоной"""
    naive = datetime.strptime(date_str, '%d.%m.%Y')
    return naive.replace(tzinfo=TIMEZONE)

def to_date_string(dt: datetime) -> str:
    """Преобразовать datetime в строку 'dd.mm.yyyy'"""
    return dt.strftime('%d.%m.%Y')

def to_db_date(dt: datetime) -> str:
    """Преобразовать datetime в формат для SQLite 'yyyy-mm-dd'"""
    return dt.strftime('%Y-%m-%d')

def safe_int(value, default=0):
    """Безопасное преобразование в int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# ============================================================
#  AbsenceMainView — главное окно календаря
# ============================================================

class AbsenceMainView(View):
    def __init__(self, year: int = None, month: int = None):
        super().__init__(timeout=None)
        now = get_now()
        self.year = year or now.year
        self.month = month or now.month

    @discord.ui.button(label="Запланировать", style=ButtonStyle.success, emoji="📝", row=0, custom_id="absence_plan")
    async def plan_absence(self, interaction: discord.Interaction, button: Button):
        from modals.absence_modals import AbsenceModal
        await interaction.response.send_modal(AbsenceModal())

    @discord.ui.button(label="Опаздываю", style=ButtonStyle.danger, emoji="⚠️", row=0, custom_id="absence_late")
    async def late_button(self, interaction: discord.Interaction, button: Button):
        from modals.absence_modals import LateModal
        await interaction.response.send_modal(LateModal())

    @discord.ui.button(label="Мои записи", style=ButtonStyle.secondary, emoji="👤", row=0, custom_id="absence_my")
    async def my_absences(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        await show_my_absences(interaction, db)

    @discord.ui.button(label="◀", style=ButtonStyle.gray, row=1, custom_id="cal_prev_month")
    async def prev_month(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        await interaction.response.edit_message(
            embed=build_calendar_embed(interaction.guild, db, self.year, self.month)
        )

    @discord.ui.button(label="Сегодня", style=ButtonStyle.blurple, row=1, custom_id="cal_today")
    async def today(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        now = get_now()
        self.month = now.month
        self.year = now.year
        await interaction.response.edit_message(
            embed=build_calendar_embed(interaction.guild, db, now.year, now.month)
        )

    @discord.ui.button(label="▶", style=ButtonStyle.gray, row=1, custom_id="cal_next_month")
    async def next_month(self, interaction: discord.Interaction, button: Button):
        db = interaction.client.get_db(interaction.guild_id)
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        await interaction.response.edit_message(
            embed=build_calendar_embed(interaction.guild, db, self.year, self.month)
        )


# ============================================================
#  MyAbsencesView — окно "Мои записи"
# ============================================================

class MyAbsencesView(View):
    def __init__(self, user_id: int, absences: list, lates: list):
        super().__init__(timeout=120)
        self.user_id = user_id
        all_items = absences + lates
        
        if not all_items:
            return
        
        if len(all_items) == 1:
            a = all_items[0]
            btn = Button(label="✅ Завершить", style=ButtonStyle.success, custom_id=f"return_{a['id']}")
            btn.callback = self.make_callback(a['id'])
            self.add_item(btn)
        else:
            options = []
            for a in absences:
                options.append(discord.SelectOption(
                    label=f"🚫 {a['start_date']} → {a['end_date']}",
                    value=str(a['id']),
                    description=f"Отсутствие • {a['reason'][:40]}",
                    emoji="🚫"
                ))
            for a in lates:
                options.append(discord.SelectOption(
                    label=f"⏰ {a['start_date']}",
                    value=str(a['id']),
                    description=f"Опоздание • {a['reason'].replace('⚠️ Опоздание: ', '')[:40]}",
                    emoji="⏰"
                ))
            select = Select(
                placeholder="▸ Выберите запись для завершения",
                options=options,
                custom_id="select_return"
            )
            select.callback = self.on_select
            self.add_item(select)
    
    def make_callback(self, absence_id: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message(
                    "❌ Только автор!",
                    ephemeral=True,
                    delete_after=3
                )
                return
            await process_early_return(interaction, absence_id)
        return callback
    
    async def on_select(self, interaction: discord.Interaction):
        await process_early_return(interaction, int(interaction.data['values'][0]))


async def process_early_return(interaction: discord.Interaction, absence_id: int):
    """Обработка досрочного возврата"""
    try:
        db = interaction.client.get_db(interaction.guild_id)
        
        absence = db.cursor.execute(
            'SELECT id, user_id, reason FROM absences WHERE id = ? AND status = "active"',
            (absence_id,)
        ).fetchone()
        
        if not absence:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Не найдено!",
                    ephemeral=True,
                    delete_after=3
                )
            else:
                await interaction.followup.send(
                    "❌ Не найдено!",
                    ephemeral=True,
                    delete_after=3
                )
            return
        
        db.mark_absence_completed(absence_id)
        
        if not absence[2].startswith('⚠️ Опоздание:'):
            role_id = db.get_setting('absence_role', '') or db.get_setting('afk_role', '')
            if role_id:
                try:
                    role = interaction.guild.get_role(int(role_id))
                    if role and role in interaction.user.roles:
                        await interaction.user.remove_roles(
                            role,
                            reason="Вернулся"
                        )
                except (ValueError, TypeError):
                    pass
        
        await refresh_calendar_for_guild(interaction.guild, db)
        
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "✅ Готово!",
                ephemeral=True,
                delete_after=3
            )
        else:
            await interaction.followup.send(
                "✅ Готово!",
                ephemeral=True,
                delete_after=3
            )
            
    except Exception as e:
        print(f"Ошибка в process_early_return: {e}")
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    f"❌ Ошибка: {str(e)[:100]}",
                    ephemeral=True,
                    delete_after=5
                )
            else:
                await interaction.followup.send(
                    f"❌ Ошибка: {str(e)[:100]}",
                    ephemeral=True,
                    delete_after=5
                )
        except:
            pass


async def show_my_absences(interaction: discord.Interaction, db):
    """Показать мои отсутствия"""
    try:
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True)
        
        user_id = interaction.user.id
        now = get_now()
        today_str = to_db_date(now)
        
        # Получаем активные записи
        all_active = db.cursor.execute(
            '''SELECT id, start_date, end_date, reason 
               FROM absences 
               WHERE user_id = ? AND status = 'active' 
               AND date(substr(end_date, 7, 4) || '-' || substr(end_date, 4, 2) || '-' || substr(end_date, 1, 2)) >= date(?)
               ORDER BY date(substr(start_date, 7, 4) || '-' || substr(start_date, 4, 2) || '-' || substr(start_date, 1, 2))''',
            (user_id, today_str)
        ).fetchall()
        
        absences, lates = [], []
        for a in all_active:
            is_late = a[3].startswith('⚠️ Опоздание:')
            (lates if is_late else absences).append({
                'id': a[0],
                'start_date': a[1],
                'end_date': a[2],
                'reason': a[3],
                'is_late': is_late
            })
        
        # Считаем дни в этом месяце
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        limits = db.get_absence_limits()
        month_days = 0
        
        for a in absences:
            try:
                start = parse_date(a['start_date'])
                end = parse_date(a['end_date'])
                real_start = max(start, month_start)
                real_end = min(end, now)
                if real_start <= real_end:
                    days = (real_end - real_start).days + 1
                    month_days += days
            except Exception as e:
                print(f"Ошибка обработки даты {a['start_date']}: {e}")
                continue
        
        # Создаем Embed
        embed = Embed(color=0x1a1b1e, timestamp=now)
        embed.set_author(
            name=f"📋 {interaction.user.display_name}",
            icon_url=interaction.user.display_avatar.url
        )
        
        limit_month = limits.get('month', 0) if limits else 0
        embed.add_field(
            name="",
            value=f"`📅 Месяц` **{month_days}/{limit_month}** дн.  •  "
                  f"`⚠️ Осталось` **{max(0, limit_month - month_days)}** дн.  •  "
                  f"`🚫 Отсутствий` **{len(absences)}**  •  "
                  f"`⏰ Опозданий` **{len(lates)}**",
            inline=False
        )
        
        if not all_active:
            embed.description = "\n✨ **У вас нет активных записей!**"
            view = View(timeout=60)
        else:
            parts = []
            
            if absences:
                parts.append("### 🚫 Отсутствия\n")
                for i, a in enumerate(absences, 1):
                    try:
                        sd = parse_date(a['start_date'])
                        ed = parse_date(a['end_date'])
                        
                        # Вычисляем прогресс
                        total_days = (ed - sd).days + 1
                        days_left = 0
                        
                        if now.date() == ed.date():
                            days_left = 1
                        elif now.date() < ed.date():
                            days_left = (ed.date() - now.date()).days
                        
                        days_passed = total_days - days_left
                        pct = min(100, max(0, int(days_passed / max(1, total_days) * 100)))
                        
                        bar = "█" * min(20, int(pct / 5)) + "░" * max(0, 20 - min(20, int(pct / 5)))
                        bar_emoji = "🟢" if pct < 30 else ("🟡" if pct < 70 else "🔴")
                        
                        parts.append(
                            f"**{i}. {a['start_date']} → {a['end_date']}**\n"
                            f"{bar_emoji} `{bar}` **{pct}%** • осталось **{days_left}** дн. из **{total_days}**\n"
                            f"└ *{a['reason'][:60]}*\n"
                        )
                    except Exception as e:
                        print(f"Ошибка обработки отсутствия {i}: {e}")
                        continue
            
            if lates:
                parts.append("### ⏰ Опоздания\n")
                for i, a in enumerate(lates, 1):
                    parts.append(
                        f"**{i}. {a['start_date']}**\n"
                        f"└ *{a['reason'].replace('⚠️ Опоздание: ', '')[:60]}*\n"
                    )
            
            embed.description = "\n".join(parts) if parts else "\n✨ **Нет активных записей!**"
            embed.set_footer(text="▸ Выберите запись для завершения")
            view = MyAbsencesView(user_id, absences, lates)
        
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
    except Exception as e:
        print(f"Ошибка в show_my_absences: {e}")
        try:
            if interaction.response.is_done():
                await interaction.followup.send(
                    f"❌ Ошибка: {str(e)[:100]}",
                    ephemeral=True,
                    delete_after=5
                )
            else:
                await interaction.response.send_message(
                    f"❌ Ошибка: {str(e)[:100]}",
                    ephemeral=True,
                    delete_after=5
                )
        except:
            pass


async def refresh_calendar_for_guild(guild, db):
    """Обновить календарь для гильдии"""
    try:
        if not guild:
            return
            
        ch_id = db.get_setting('absence_channel', '')
        if not ch_id:
            return
            
        try:
            ch_id = int(ch_id)
        except (ValueError, TypeError):
            return
            
        channel = guild.get_channel(ch_id)
        if not channel:
            return
            
        msg_data = db.get_message('absence')
        if not msg_data or len(msg_data) < 2:
            return
            
        msg_id = msg_data[1]
        if not msg_id:
            return
            
        try:
            msg = await channel.fetch_message(int(msg_id))
            now = get_now()
            await msg.edit(
                embed=build_calendar_embed(guild, db, now.year, now.month)
            )
        except discord.NotFound:
            pass
        except discord.Forbidden:
            pass
        except Exception as e:
            print(f"Ошибка обновления календаря: {e}")
            
    except Exception as e:
        print(f"Ошибка в refresh_calendar_for_guild: {e}")


def build_calendar_embed(guild, db, year: int, month: int) -> Embed:
    """Построить Embed календаря"""
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    now = get_now()
    cal = calendar.monthcalendar(year, month)
    
    month_start = datetime(year, month, 1, tzinfo=TIMEZONE)
    if month == 12:
        month_end = datetime(year + 1, 1, 1, tzinfo=TIMEZONE) - timedelta(days=1)
    else:
        month_end = datetime(year, month + 1, 1, tzinfo=TIMEZONE) - timedelta(days=1)
    
    # Границы отображения
    if month == 1:
        prev_month = 12
        prev_year = year - 1
    else:
        prev_month = month - 1
        prev_year = year
    
    last_day_prev = calendar.monthrange(prev_year, prev_month)[1]
    
    first_week = cal[0]
    first_real_idx = next(i for i, d in enumerate(first_week) if d != 0)
    display_start = month_start - timedelta(days=first_real_idx)
    
    last_week = cal[-1]
    last_real_idx = max(i for i, d in enumerate(last_week) if d != 0)
    display_end = month_end + timedelta(days=(6 - last_real_idx))
    
    # Получаем данные
    try:
        rows = db.cursor.execute(
            '''SELECT a.user_id, a.start_date, a.end_date, a.reason 
               FROM absences a 
               WHERE a.status = 'active' 
               AND date(substr(a.start_date, 7, 4) || '-' || substr(a.start_date, 4, 2) || '-' || substr(a.start_date, 1, 2)) <= date(?)
               AND date(substr(a.end_date, 7, 4) || '-' || substr(a.end_date, 4, 2) || '-' || substr(a.end_date, 1, 2)) >= date(?)''',
            (to_db_date(display_end), to_db_date(display_start))
        ).fetchall()
    except Exception as e:
        print(f"Ошибка получения данных: {e}")
        rows = []
    
    # Обработка данных
    day_data_full = {}
    user_absences = {}
    user_lates = {}
    
    for user_id, start_str, end_str, reason in rows:
        try:
            start = parse_date(start_str)
            end = parse_date(end_str)
        except ValueError:
            continue
            
        is_late = reason.startswith('⚠️ Опоздание:')
        member = guild.get_member(user_id) if guild else None
        name = member.display_name if member else str(user_id)
        
        current = max(start, display_start)
        end_check = min(end, display_end)
        
        if is_late:
            if user_id not in user_lates:
                user_lates[user_id] = {'name': name, 'days': set(), 'reasons': []}
            clean = reason.replace('⚠️ Опоздание: ', '')
            if clean not in user_lates[user_id]['reasons']:
                user_lates[user_id]['reasons'].append(clean)
            
            while current <= end_check:
                date_key = to_db_date(current)
                if date_key not in day_data_full:
                    day_data_full[date_key] = {'absent': False, 'late': False}
                day_data_full[date_key]['late'] = True
                user_lates[user_id]['days'].add(current.day)
                current += timedelta(days=1)
        else:
            if user_id not in user_absences:
                user_absences[user_id] = {'name': name, 'ranges': [], 'reasons': []}
            if reason not in user_absences[user_id]['reasons']:
                user_absences[user_id]['reasons'].append(reason)
            
            while current <= end_check:
                date_key = to_db_date(current)
                if date_key not in day_data_full:
                    day_data_full[date_key] = {'absent': False, 'late': False}
                day_data_full[date_key]['absent'] = True
                current += timedelta(days=1)
            
            user_absences[user_id]['ranges'].append((start.day, end.day))
    
    # Объединяем диапазоны
    for uid in user_absences:
        ranges = sorted(user_absences[uid]['ranges'])
        merged = []
        for r in ranges:
            if merged and r[0] <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], r[1]))
            else:
                merged.append(r)
        user_absences[uid]['ranges'] = merged
    
    # Настройки сезона
    season_config = {
        1: ("⛄", 0x89CFF0), 2: ("⛄", 0x89CFF0),
        3: ("🌱", 0xA8E6CF), 4: ("🌸", 0xFFB7B2),
        5: ("🌿", 0x77DD77), 6: ("🌞", 0xFFD700),
        7: ("🌞", 0xFF6B6B), 8: ("🌞", 0xFF6B6B),
        9: ("🍁", 0xFFA500), 10: ("🍁", 0xFF8C00),
        11: ("🍂", 0x8B4513), 12: ("⛄", 0x89CFF0)
    }
    season_emoji, season_color = season_config.get(month, ("📅", 0x5865f2))
    
    title = f"{season_emoji}  {now.day} {month_names[month-1]} {year}"
    embed = Embed(title=title, color=season_color, timestamp=now)
    
    days_ru = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    day_emojis = ["🔹", "🔸", "🔷", "🔶", "💎", "🌟", "✨"]
    
    calendar_text = "```\n"
    
    header = ""
    for i, d in enumerate(days_ru):
        header += " " + day_emojis[i] + d + " "
    calendar_text += header + "\n"
    calendar_text += "─" * 35 + "\n"
    
    day_counter = last_day_prev - first_real_idx + 1
    next_day_counter = 1
    
    for week in cal:
        row = ""
        for day in week:
            if day == 0:
                if day_counter <= last_day_prev:
                    current_day_num = day_counter
                    day_counter += 1
                else:
                    current_day_num = next_day_counter
                    next_day_counter += 1
                row += " ⬛" + f"{current_day_num:02d}" + " "
            else:
                is_today = (day == now.day and month == now.month and year == now.year)
                date_key = f"{year}-{month:02d}-{day:02d}"
                info = day_data_full.get(date_key, {'absent': False, 'late': False})
                absent = info['absent']
                late = info['late']
                
                if absent and late:
                    icon = "⚡"
                elif late:
                    icon = "⚠️"
                elif absent:
                    icon = "❌"
                elif is_today:
                    icon = "🔷"
                else:
                    icon = "✅"
                
                row += " " + icon + f"{day:02d}" + " "
        
        calendar_text += row + "\n"
    
    calendar_text += "```"
    
    embed.add_field(name="", value=calendar_text, inline=False)
    embed.add_field(
        name="",
        value="✅ Свободен  •  🔷 Сегодня  •  ❌ Отсутствует  •  ⚠️ Опаздывает  •  ⚡ Оба  •  ⬛ Другой месяц",
        inline=False
    )
    
    # Список пользователей
    desc_parts = []
    
    if user_absences:
        desc_parts.append("### ❌ Отсутствуют")
        for uid, info in sorted(user_absences.items(), key=lambda x: x[1]['name']):
            ranges = [f"{s}-{e}" if s != e else str(s) for s, e in info['ranges']]
            reason = f" — *{info['reasons'][0][:45]}*" if info['reasons'] else ""
            desc_parts.append(f"**{info['name']}**  `{', '.join(ranges)}`{reason}")
    
    if user_lates:
        if desc_parts:
            desc_parts.append("")
        desc_parts.append("### ⚠️ Опаздывают")
        for uid, info in sorted(user_lates.items(), key=lambda x: x[1]['name']):
            days = ", ".join(str(d) for d in sorted(info['days']))
            reason = f" — *{info['reasons'][0][:45]}*" if info['reasons'] else ""
            desc_parts.append(f"**{info['name']}**  `{days}`{reason}")
    
    embed.description = "\n".join(desc_parts) if desc_parts else "### ✨ Все на месте!"
    
    ta, tl = len(user_absences), len(user_lates)
    footer = ""
    if ta > 0:
        footer += f"❌ {ta} отсутствуют"
    if tl > 0:
        footer += ("  •  " if footer else "") + f"⚠️ {tl} опаздывают"
    embed.set_footer(text=f"{footer or '✨ Все на месте'}  •  Обновлено")
    
    return embed