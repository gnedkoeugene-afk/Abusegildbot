# database.py — ПОЛНЫЙ ФАЙЛ С ОПИСАНИЯМИ

import sqlite3
from datetime import datetime, timedelta
import json
import discord
from typing import Optional, List, Dict, Any


class Database:
    """
    Основной класс для работы с базой данных SQLite.
    Содержит все методы для управления данными бота.
    """

    def __init__(self, db_path: str):
        """Инициализация с указанием пути к файлу БД"""
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    # ============================================
    # ПОДКЛЮЧЕНИЕ К БД
    # ============================================

    def connect(self):
        """Устанавливает соединение с базой данных"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()

    def close(self):
        """Закрывает соединение с базой данных"""
        if self.conn:
            self.conn.close()

    def init(self):
        """Инициализация всех таблиц базы данных"""
        self.connect()
        
        # ============================================
        # ОСНОВНЫЕ ТАБЛИЦЫ
        # ============================================
        
        # Настройки бота (ключ-значение)
        self.cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        
        # Заявки на вступление в гильдию
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id INTEGER,
                status TEXT DEFAULT 'pending',
                reviewer_id INTEGER,
                reason TEXT,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Попытки подачи заявок (для ограничений)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS application_attempts (
                user_id INTEGER PRIMARY KEY,
                attempt_count INTEGER DEFAULT 0,
                last_attempt TIMESTAMP,
                last_reject_reason TEXT
            )
        ''')
        
        # Сохранённые сообщения бота (для восстановления кнопок)
        self.cursor.execute('CREATE TABLE IF NOT EXISTS messages (key TEXT PRIMARY KEY, channel_id INTEGER, message_id INTEGER)')
        
        # Чёрный список
        self.cursor.execute('CREATE TABLE IF NOT EXISTS blacklist (user_id INTEGER PRIMARY KEY, reason TEXT, moderator_id INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
        
        # Апелляции
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS appeals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                channel_id INTEGER,
                character_name TEXT,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Отсутствия
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS absences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                start_date TEXT,
                end_date TEXT,
                reason TEXT,
                status TEXT DEFAULT 'active',
                message_id INTEGER,
                channel_id INTEGER,
                auto_complete_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Подтверждения отсутствий офицерами
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS absence_acknowledgments (
                absence_id INTEGER,
                officer_id INTEGER,
                acknowledged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (absence_id, officer_id)
            )
        ''')
        
        # Персонажи игроков
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                character_name TEXT,
                class_spec TEXT,
                specialization TEXT,
                item_level INTEGER,
                profile_url TEXT,
                raid_role TEXT DEFAULT 'mdd',
                is_main INTEGER DEFAULT 0,
                has_added BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Напоминания о персонажах
        self.cursor.execute('CREATE TABLE IF NOT EXISTS character_reminders (user_id INTEGER PRIMARY KEY, reminder_count INTEGER DEFAULT 0, last_reminder TIMESTAMP)')
        
        # Наказания
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS punishments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER,
                user_id INTEGER,
                violation_count INTEGER,
                reason TEXT,
                issuer_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Предупреждения
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                character_id INTEGER,
                user_id INTEGER,
                level INTEGER,
                expires_at TIMESTAMP,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Запросы на смену основного персонажа
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS main_change_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                character_id INTEGER,
                new_character_id INTEGER,
                reason TEXT,
                status TEXT DEFAULT 'pending',
                reviewer_id INTEGER,
                review_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Составы рейдов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS raids (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                leader_id INTEGER,
                main_slots INTEGER DEFAULT 10,
                reserve_slots INTEGER DEFAULT 5,
                status TEXT DEFAULT 'active',
                message_id INTEGER,
                channel_id INTEGER,
                panel_channel_id INTEGER,
                panel_message_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Участники составов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS raid_members (
                raid_id INTEGER,
                user_id INTEGER,
                character_id INTEGER,
                role TEXT DEFAULT 'mdd',
                is_reserve INTEGER DEFAULT 0,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (raid_id, user_id)
            )
        ''')
        
        # Задания для наказаний
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS punishment_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                character_id INTEGER,
                punishment_id INTEGER,
                task_text TEXT,
                status TEXT DEFAULT 'pending',
                channel_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Настройки заданий
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_number INTEGER,
                task_text TEXT
            )
        ''')
        
        # Заявки в статик
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS static_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                character_id INTEGER,
                imgur_link TEXT,
                additional_info TEXT,
                channel_id INTEGER,
                status TEXT DEFAULT 'pending',
                reviewer_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Голоса за заявки в статик
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS static_votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                vote INTEGER NOT NULL,
                UNIQUE(channel_id, user_id)
            )
        ''')
        
        # Права ролей
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_key TEXT,
                permission_key TEXT,
                enabled INTEGER DEFAULT 1,
                PRIMARY KEY (role_key, permission_key)
            )
        ''')
        
        # Техподдержка (баг-репорты)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_reports (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                channel_id INTEGER,
                message_id INTEGER,
                title TEXT,
                description TEXT,
                screenshots TEXT,
                status TEXT DEFAULT 'open',
                resolved_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Логи действий
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT,
                user_id INTEGER,
                target_id INTEGER,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Жалобы на игроков
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY,
                reporter_id INTEGER,
                violator_id INTEGER,
                violator_name TEXT,
                violation_type TEXT,
                description TEXT,
                evidence TEXT,
                witnesses TEXT,
                channel_id INTEGER,
                status TEXT DEFAULT 'open',
                resolver_id INTEGER,
                resolution TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP,
                is_anonymous INTEGER DEFAULT 0
            )
        ''')
        
        self.conn.commit()
        
        # ============================================
        # МИГРАЦИИ (добавление новых колонок)
        # ============================================
        
        migrations = [
            'ALTER TABLE characters ADD COLUMN raid_role TEXT DEFAULT "mdd"',
            'ALTER TABLE raids ADD COLUMN main_slots INTEGER DEFAULT 10',
            'ALTER TABLE raids ADD COLUMN reserve_slots INTEGER DEFAULT 5',
            'ALTER TABLE raids ADD COLUMN message_id INTEGER',
            'ALTER TABLE raids ADD COLUMN channel_id INTEGER',
            'ALTER TABLE raids ADD COLUMN panel_channel_id INTEGER',
            'ALTER TABLE raids ADD COLUMN panel_message_id INTEGER',
            'ALTER TABLE main_change_requests ADD COLUMN new_character_id INTEGER',
            'ALTER TABLE absences ADD COLUMN auto_complete_at TIMESTAMP',
        ]
        for migration in migrations:
            try:
                self.cursor.execute(migration)
                self.conn.commit()
            except:
                pass
        
        try:
            self.cursor.execute('ALTER TABLE reports ADD COLUMN is_anonymous INTEGER DEFAULT 0')
        except:
            pass

        try:
            self.cursor.execute('ALTER TABLE applications ADD COLUMN message_id INTEGER')
            self.conn.commit()
        except:
            pass
        
        # ============================================
        # ПРАВА ПО УМОЛЧАНИЮ
        # ============================================
        
        self.cursor.execute('SELECT COUNT(*) FROM role_permissions')
        if self.cursor.fetchone()[0] == 0:
            default_permissions = {
                'guild_master': ['applications', 'appeals', 'absences', 'characters', 'punishments', 'remove_punishments', 'raids', 'manage_raids', 'settings', 'static', 'main_change', 'admin_center', 'reports'],
                'vice_master': ['applications', 'appeals', 'absences', 'characters', 'punishments', 'remove_punishments', 'raids', 'manage_raids', 'settings', 'static', 'main_change', 'reports'],
                'raid_leader': ['applications', 'appeals', 'absences', 'characters', 'punishments', 'remove_punishments'],
                'officer': ['applications', 'appeals', 'absences', 'characters', 'punishments'],
            }
            for role_key, permissions in default_permissions.items():
                for perm in permissions:
                    self.cursor.execute('INSERT OR IGNORE INTO role_permissions (role_key, permission_key, enabled) VALUES (?, ?, 1)', (role_key, perm))
            self.conn.commit()
        
        # ============================================
        # ТАБЛИЦЫ ДЛЯ КУРАТОРОВ
        # ============================================
        
        self.init_curator_tables()

    # ============================================
    # ТАБЛИЦЫ КУРАТОРОВ
    # ============================================

    def init_curator_tables(self):
        """Создает таблицы для системы кураторов и обучения РЛ"""
        
        # Разделы (инсты) для обучения
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                theory_link TEXT,
                pass_condition TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Тесты к разделам
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                max_score INTEGER DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
            )
        ''')
        
        # Задания к разделам
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                difficulty INTEGER DEFAULT 1,
                points_reward INTEGER DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
            )
        ''')
        
        # Заявки на обучение (из МоиПерсонажи)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trainee_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                character_id INTEGER,
                experience TEXT,
                motivation TEXT,
                available_days TEXT,
                status TEXT DEFAULT 'pending',
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewer_id INTEGER,
                review_comment TEXT,
                FOREIGN KEY (character_id) REFERENCES characters(id)
            )
        ''')
        
        # Назначения (игрок → раздел)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                section_id INTEGER NOT NULL,
                status TEXT DEFAULT 'active',
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                points_earned INTEGER DEFAULT 0,
                FOREIGN KEY (section_id) REFERENCES sections(id) ON DELETE CASCADE
            )
        ''')
        
        # Выполнение заданий
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS task_completions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL,
                answer_text TEXT,
                status TEXT DEFAULT 'pending',
                points_awarded INTEGER DEFAULT 0,
                submitted_at TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewer_id INTEGER,
                review_comment TEXT,
                FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
            )
        ''')
        
        # Ответы на тесты
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                assignment_id INTEGER NOT NULL,
                test_id INTEGER NOT NULL,
                answer_text TEXT,
                score INTEGER DEFAULT 0,
                reviewed_at TIMESTAMP,
                reviewer_id INTEGER,
                FOREIGN KEY (assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
                FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE
            )
        ''')
        
        # Логи кураторов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS curator_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                details TEXT,
                performed_by INTEGER,
                target_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Кандидаты (ученики)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trainees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                main_character_id INTEGER,
                mentor_id INTEGER,
                level INTEGER DEFAULT 1,
                points INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                experience TEXT,
                classes_known TEXT,
                motivation TEXT,
                available_days TEXT,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                graduated_at TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (main_character_id) REFERENCES characters(id)
            )
        ''')
        
        # Задания для кандидатов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trainee_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trainee_id INTEGER NOT NULL,
                mentor_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                difficulty INTEGER DEFAULT 1,
                points_reward INTEGER,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deadline TIMESTAMP,
                completed_at TIMESTAMP,
                approved_at TIMESTAMP,
                mentor_comment TEXT,
                FOREIGN KEY (trainee_id) REFERENCES trainees(id)
            )
        ''')
        
        # Отчеты по заданиям кандидатов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trainee_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                trainee_id INTEGER NOT NULL,
                answer TEXT NOT NULL,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                mentor_feedback TEXT,
                points_awarded INTEGER DEFAULT 0,
                FOREIGN KEY (task_id) REFERENCES trainee_tasks(id),
                FOREIGN KEY (trainee_id) REFERENCES trainees(id)
            )
        ''')
        
        # Логи кандидатов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trainee_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trainee_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                details TEXT,
                performed_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Наказания кандидатов
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trainee_punishments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trainee_id INTEGER NOT NULL,
                points_deducted INTEGER NOT NULL,
                reason TEXT NOT NULL,
                issued_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Настройки системы обучения
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trainee_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT NOT NULL UNIQUE,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Уровни обучения
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS trainee_levels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level_number INTEGER NOT NULL UNIQUE,
                level_name TEXT NOT NULL,
                points_required INTEGER NOT NULL,
                role_id INTEGER,
                bonus_percent INTEGER DEFAULT 0,
                description TEXT
            )
        ''')
        
        self.conn.commit()
        
        # Добавляем начальные уровни
        self.init_default_trainee_levels()
        self.init_default_trainee_settings()

    def init_default_trainee_levels(self):
        """Добавляет начальные уровни обучения"""
        levels = [
            (1, '📖 Ученик', 100, 'Начальный уровень, изучение теории'),
            (2, '👁️ Наблюдатель', 250, 'Наблюдение за рейдами'),
            (3, '🎯 Ассистент', 500, 'Помощь РЛу в рейдах'),
            (4, '⚔️ Ведущий', 800, 'Самостоятельное ведение рейдов'),
            (5, '🎓 Мастер', 1200, 'Полноценный Рейд-Лидер')
        ]
        
        for level_num, name, points, desc in levels:
            self.cursor.execute('''
                INSERT OR IGNORE INTO trainee_levels 
                (level_number, level_name, points_required, description)
                VALUES (?, ?, ?, ?)
            ''', (level_num, name, points, desc))
        
        self.conn.commit()

    def init_default_trainee_settings(self):
        """Добавляет настройки обучения по умолчанию"""
        settings = [
            ('mentor_role', ''),
            ('trainee_role', ''),
            ('assistant_role', ''),
            ('raid_leader_role', ''),
            ('trainee_channel', ''),
            ('trainee_category', ''),
            ('check_interval', '5'),
            ('punishment_points', '25'),
            ('max_trainees_per_mentor', '5'),
            ('auto_graduation', '1'),
            ('notification_gm', '1'),
            ('notification_dev', '1')
        ]
        
        for key, value in settings:
            self.cursor.execute('''
                INSERT OR IGNORE INTO trainee_settings (setting_key, setting_value)
                VALUES (?, ?)
            ''', (key, value))
        
        self.conn.commit()

    # ============================================
    # НАСТРОЙКИ
    # ============================================

    def get_setting(self, key: str, default: str = '') -> str:
        """Получить значение настройки"""
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = self.cursor.fetchone()
        return row[0] if row else default

    def set_setting(self, key: str, value: str):
        """Установить значение настройки"""
        self.cursor.execute('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)', (key, value))
        self.conn.commit()

    # ============================================
    # ЛИМИТЫ ОТСУТСТВИЙ
    # ============================================

    def get_absence_limits(self) -> dict:
        """Получить лимиты отсутствий"""
        return {
            'week': int(self.get_setting('absence_limit_week', '3')),
            'month': int(self.get_setting('absence_limit_month', '10')),
            'consecutive': int(self.get_setting('absence_limit_consecutive', '14')),
            'raids': int(self.get_setting('absence_limit_raids', '3'))
        }

    def get_user_absence_days_in_period_excluding_lates(self, user_id, start_date, end_date) -> int:
        """Получить количество дней отсутствия пользователя в периоде (без опозданий)"""
        self.cursor.execute('''
            SELECT start_date, end_date FROM absences
            WHERE user_id = ? AND status IN ('active', 'early_return')
            AND reason NOT LIKE '⚠️ Опоздание:%'
            AND date(substr(end_date, 7, 4) || '-' || substr(end_date, 4, 2) || '-' || substr(end_date, 1, 2)) >= date(?)
            AND date(substr(start_date, 7, 4) || '-' || substr(start_date, 4, 2) || '-' || substr(start_date, 1, 2)) <= date(?)
        ''', (user_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        
        total = 0
        for ex_start, ex_end in self.cursor.fetchall():
            ex_s = datetime.strptime(ex_start, '%d.%m.%Y')
            ex_e = datetime.strptime(ex_end, '%d.%m.%Y')
            ex_s = max(ex_s, start_date)
            ex_e = min(ex_e, end_date)
            if ex_s <= ex_e:
                total += (ex_e - ex_s).days + 1
        return total

    # ============================================
    # ЛОГИРОВАНИЕ
    # ============================================

    def add_log(self, action: str, user_id: int, target_id: int = None, details: str = ""):
        """Добавить запись в лог"""
        self.cursor.execute(
            'INSERT INTO logs (action, user_id, target_id, details) VALUES (?, ?, ?, ?)',
            (action, user_id, target_id, details)
        )
        self.conn.commit()

    def get_recent_logs(self, limit: int = 20) -> list:
        """Получить последние логи"""
        try:
            self.cursor.execute('SELECT action, user_id, target_id, details, created_at FROM logs ORDER BY id DESC LIMIT ?', (limit,))
            return self.cursor.fetchall()
        except:
            return []

    # ============================================
    # АРХИВИРОВАНИЕ
    # ============================================

    def archive_application(self, app_id: int):
        """Переместить заявку в архив"""
        try:
            self.cursor.execute('''
                INSERT INTO applications_archive (id, user_id, channel_id, status, reviewer_id, reason, data, created_at)
                SELECT id, user_id, channel_id, status, reviewer_id, reason, data, created_at
                FROM applications WHERE id = ?
            ''', (app_id,))
            self.cursor.execute('DELETE FROM applications WHERE id = ?', (app_id,))
            self.conn.commit()
        except Exception as e:
            print(f"❌ Ошибка архивирования заявки #{app_id}: {e}")

    # ============================================
    # СООБЩЕНИЯ (ДЛЯ ВОССТАНОВЛЕНИЯ КНОПОК)
    # ============================================

    def save_message(self, key: str, channel_id: int, message_id: int):
        """Сохранить сообщение для восстановления"""
        self.cursor.execute('INSERT OR REPLACE INTO messages (key, channel_id, message_id) VALUES (?, ?, ?)', 
                           (key, channel_id, message_id))
        self.conn.commit()

    def get_message(self, key: str):
        """Получить сохранённое сообщение по ключу"""
        self.cursor.execute('SELECT channel_id, message_id FROM messages WHERE key = ?', (key,))
        row = self.cursor.fetchone()
        if row:
            return (row[0], row[1])
        return None

    def get_all_messages(self) -> list:
        """Получить все сохранённые сообщения"""
        try:
            self.cursor.execute('SELECT key, channel_id, message_id FROM messages')
            return self.cursor.fetchall()
        except:
            return []

    # ============================================
    # ОТСУТСТВИЯ
    # ============================================

    def add_absence_simple(self, user_id: int, start_date: str, end_date: str, reason: str) -> int:
        """Добавить обычное отсутствие"""
        self.cursor.execute('INSERT INTO absences (user_id, start_date, end_date, reason, status) VALUES (?, ?, ?, ?, "active")', 
                           (user_id, start_date, end_date, reason))
        self.conn.commit()
        return self.cursor.lastrowid

    def add_absence_with_auto_complete(self, user_id, start_str, end_str, reason, auto_complete_minutes=0):
        """Добавить отсутствие с авто-завершением (опоздание)"""
        auto_complete_at = None
        if auto_complete_minutes > 0:
            auto_complete_at = (datetime.now() + timedelta(minutes=auto_complete_minutes)).isoformat()
        
        self.cursor.execute(
            'INSERT INTO absences (user_id, start_date, end_date, reason, status, auto_complete_at) VALUES (?, ?, ?, ?, "active", ?)',
            (user_id, start_str, end_str, reason, auto_complete_at)
        )
        self.conn.commit()
        return self.cursor.lastrowid

    def update_absence_message(self, absence_id: int, message_id: int, channel_id: int):
        """Обновить ID сообщения отсутствия"""
        self.cursor.execute('UPDATE absences SET message_id = ?, channel_id = ? WHERE id = ?', (message_id, channel_id, absence_id))
        self.conn.commit()

    def remove_trainee(self, user_id: int):
        self.cursor.execute('DELETE FROM trainees WHERE user_id = ?', (user_id,))
        self.conn.commit()

    def mark_absence_completed(self, absence_id: int):
        """Отметить отсутствие как завершённое"""
        self.cursor.execute('UPDATE absences SET status = "completed" WHERE id = ?', (absence_id,))
        self.conn.commit()

    def mark_absence_early_return(self, absence_id: int):
        """Отметить раннее возвращение"""
        self.cursor.execute('UPDATE absences SET status = "early_return" WHERE id = ?', (absence_id,))
        self.conn.commit()

    def acknowledge_absence(self, absence_id: int, officer_id: int):
        """Подтвердить отсутствие офицером"""
        self.cursor.execute('INSERT OR IGNORE INTO absence_acknowledgments (absence_id, officer_id) VALUES (?, ?)', (absence_id, officer_id))
        self.conn.commit()

    def get_acknowledged_officers(self, absence_id: int) -> list:
        """Получить офицеров, подтвердивших отсутствие"""
        self.cursor.execute('SELECT officer_id FROM absence_acknowledgments WHERE absence_id = ?', (absence_id,))
        return [r[0] for r in self.cursor.fetchall()]

    # ============================================
    # ПРИОРИТЕТ РОЛЕЙ
    # ============================================

    def set_priority_role(self, position: int, role_id: int):
        """Установить приоритетную роль"""
        self.set_setting(f'priority_role_{position}', str(role_id))

    def get_priority_roles(self) -> list:
        """Получить список приоритетных ролей"""
        result = []
        position = 1
        while True:
            role_id = self.get_setting(f'priority_role_{position}', '')
            if not role_id or not role_id.isdigit():
                break
            result.append(int(role_id))
            position += 1
        return result

    def get_user_priority_level(self, user: discord.Member) -> int:
        """Получить уровень приоритета пользователя"""
        priority_roles = self.get_priority_roles()
        for idx, role_id in enumerate(priority_roles):
            role = user.guild.get_role(role_id)
            if role and role in user.roles:
                return idx + 1
        return 999

    # ============================================
    # ЗАЯВКИ
    # ============================================

    def add_application(self, user_id: int, data: dict) -> int:
        """Добавить заявку"""
        data_json = json.dumps(data, ensure_ascii=False)
        self.cursor.execute('INSERT INTO applications (user_id, data, status) VALUES (?, ?, "pending")', (user_id, data_json))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_application_status(self, app_id: int, status: str, reviewer_id: int):
        """Обновить статус заявки"""
        self.cursor.execute(
            'UPDATE applications SET status = ?, reviewer_id = ? WHERE id = ?',
            (status, reviewer_id, app_id)
        )
        self.conn.commit()

    def get_pending_applications(self) -> list:
        """Получить все ожидающие заявки"""
        self.cursor.execute('SELECT id, user_id, data FROM applications WHERE status = "pending"')
        return self.cursor.fetchall()

    def get_pending_applications_full(self) -> list:
        """Получить все ожидающие заявки с полными данными"""
        self.cursor.execute('SELECT id, user_id, channel_id, data FROM applications WHERE status = "pending"')
        rows = self.cursor.fetchall()
        result = []
        for row in rows:
            data = json.loads(row[3]) if row[3] else {}
            data['app_id'] = row[0]
            result.append({'app_id': row[0], 'user_id': row[1], 'channel_id': row[2], **data})
        return result

    def get_pending_applications_by_user(self, user_id: int) -> list:
        """Получить заявки пользователя в ожидании"""
        self.cursor.execute('SELECT id, status FROM applications WHERE user_id = ? AND status = "pending"', (user_id,))
        return self.cursor.fetchall()

    # ============================================
    # ПОВТОРНЫЕ ЗАЯВКИ
    # ============================================

    def get_application_attempts(self, user_id: int) -> dict:
        """Получить количество попыток подачи заявки"""
        self.cursor.execute('SELECT attempt_count, last_attempt, last_reject_reason FROM application_attempts WHERE user_id = ?', (user_id,))
        row = self.cursor.fetchone()
        if row:
            return {'attempt_count': row[0], 'last_attempt': datetime.fromisoformat(row[1]) if row[1] else None, 'last_reject_reason': row[2]}
        return {'attempt_count': 0, 'last_attempt': None, 'last_reject_reason': None}

    def get_wait_time_for_next_attempt(self, user_id: int) -> int:
        """Получить время ожидания до следующей попытки (в минутах)"""
        attempts = self.get_application_attempts(user_id)
        count = attempts['attempt_count']
        if attempts['last_attempt']:
            days_since = (datetime.now() - attempts['last_attempt']).days
            if days_since >= 7:
                self.reset_application_attempts(user_id)
                return 0
        wait_times = [10, 30, 60, 120, 360, 720, 1440]
        if count < len(wait_times):
            return wait_times[count]
        return 1440

    def can_submit_application(self, user_id: int) -> tuple:
        """Проверить, может ли пользователь подать заявку"""
        pending = self.get_pending_applications_by_user(user_id)
        if pending:
            return False, "У вас уже есть активная заявка!", 0
        attempts = self.get_application_attempts(user_id)
        if attempts['attempt_count'] == 0:
            return True, None, 0
        if attempts['last_attempt']:
            wait_minutes = self.get_wait_time_for_next_attempt(user_id)
            time_since = (datetime.now() - attempts['last_attempt']).total_seconds() / 60
            if time_since >= wait_minutes:
                self.reset_application_attempts(user_id)
                return True, None, 0
            remaining = int(wait_minutes - time_since)
            hours, minutes = remaining // 60, remaining % 60
            reason_text = f"\n📋 **Причина:** {attempts['last_reject_reason']}" if attempts['last_reject_reason'] else ""
            message = f"Повторная заявка через **{hours} ч. {minutes} мин.**{reason_text}" if hours > 0 else f"Повторная заявка через **{minutes} мин.**{reason_text}"
            return False, message, remaining
        return True, None, 0

    def update_application_attempt(self, user_id: int, reason: str = None):
        """Обновить количество попыток подачи заявки"""
        self.cursor.execute('''
            INSERT INTO application_attempts (user_id, attempt_count, last_attempt, last_reject_reason)
            VALUES (?, 1, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                attempt_count = attempt_count + 1,
                last_attempt = ?,
                last_reject_reason = ?
        ''', (user_id, datetime.now(), reason, datetime.now(), reason))
        self.conn.commit()

    def reset_application_attempts(self, user_id: int):
        """Сбросить попытки подачи заявки"""
        self.cursor.execute('DELETE FROM application_attempts WHERE user_id = ?', (user_id,))
        self.conn.commit()

    # ============================================
    # ЧЁРНЫЙ СПИСОК
    # ============================================

    def is_blacklisted(self, user_id: int) -> bool:
        """Проверить, находится ли пользователь в ЧС"""
        self.cursor.execute('SELECT 1 FROM blacklist WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone() is not None

    def add_blacklist(self, user_id: int, reason: str, moderator_id: int):
        """Добавить пользователя в ЧС"""
        self.cursor.execute('INSERT OR REPLACE INTO blacklist (user_id, reason, moderator_id) VALUES (?, ?, ?)', (user_id, reason, moderator_id))
        self.conn.commit()

    def remove_blacklist(self, user_id: int):
        """Удалить пользователя из ЧС"""
        self.cursor.execute('DELETE FROM blacklist WHERE user_id = ?', (user_id,))
        self.conn.commit()

    # ============================================
    # АПЕЛЛЯЦИИ
    # ============================================

    def add_appeal(self, user_id: int, channel_id: int, character_name: str, reason: str):
        """Добавить апелляцию"""
        self.cursor.execute('INSERT INTO appeals (user_id, channel_id, character_name, reason, status) VALUES (?, ?, ?, ?, "pending")', 
                           (user_id, channel_id, character_name, reason))
        self.conn.commit()

    def update_appeal_status(self, channel_id: int, status: str):
        """Обновить статус апелляции"""
        self.cursor.execute('UPDATE appeals SET status = ? WHERE channel_id = ?', (status, channel_id))
        self.conn.commit()

    def get_pending_appeals_full(self) -> list:
        """Получить все ожидающие апелляции"""
        self.cursor.execute('SELECT id, user_id, channel_id, character_name, reason FROM appeals WHERE status = "pending"')
        rows = self.cursor.fetchall()
        return [{'appeal_id': r[0], 'user_id': r[1], 'channel_id': r[2], 'character_name': r[3], 'reason': r[4]} for r in rows]

    def get_next_id(self, table: str) -> int:
        """Получить следующий ID для таблицы"""
        self.cursor.execute(f'SELECT MAX(id) FROM {table}')
        row = self.cursor.fetchone()
        return (row[0] + 1) if row[0] else 1

    # ============================================
    # ПЕРСОНАЖИ
    # ============================================

    def get_user_characters(self, user_id: int) -> list:
        """Получить всех персонажей пользователя"""
        self.cursor.execute('SELECT id, character_name, class_spec, specialization, item_level, profile_url, raid_role, is_main FROM characters WHERE user_id = ?', (user_id,))
        rows = self.cursor.fetchall()
        return [{'id': r[0], 'character_name': r[1], 'class_spec': r[2], 'specialization': r[3], 'item_level': r[4], 'profile_url': r[5], 'raid_role': r[6], 'is_main': r[7]} for r in rows]

    def get_user_twins(self, user_id: int) -> list:
        """Получить твинков пользователя"""
        self.cursor.execute('SELECT id, character_name, class_spec, specialization, item_level, profile_url, raid_role FROM characters WHERE user_id = ? AND is_main = 0', (user_id,))
        rows = self.cursor.fetchall()
        return [{'id': r[0], 'character_name': r[1], 'class_spec': r[2], 'specialization': r[3], 'item_level': r[4], 'profile_url': r[5], 'raid_role': r[6]} for r in rows]

    def get_main_character(self, user_id: int):
        """Получить основного персонажа пользователя"""
        self.cursor.execute('SELECT id, character_name, class_spec, specialization, item_level, profile_url, raid_role, is_main FROM characters WHERE user_id = ? AND is_main = 1', (user_id,))
        row = self.cursor.fetchone()
        if row:
            return {'id': row[0], 'character_name': row[1], 'class_spec': row[2], 'specialization': row[3], 'item_level': row[4], 'profile_url': row[5], 'raid_role': row[6], 'is_main': row[7]}
        return None

    def get_character_by_id(self, character_id: int):
        """Получить персонажа по ID"""
        self.cursor.execute('SELECT id, user_id, character_name, class_spec, specialization, item_level, profile_url, raid_role, is_main FROM characters WHERE id = ?', (character_id,))
        row = self.cursor.fetchone()
        if row:
            return {'id': row[0], 'user_id': row[1], 'character_name': row[2], 'class_spec': row[3], 'specialization': row[4], 'item_level': row[5], 'profile_url': row[6], 'raid_role': row[7], 'is_main': row[8]}
        return None

    def add_character(self, user_id: int, data: dict) -> int:
        """Добавить персонажа"""
        self.cursor.execute('INSERT INTO characters (user_id, character_name, class_spec, specialization, item_level, profile_url, raid_role, is_main) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', 
                           (user_id, data['character_name'], data['class_spec'], data['specialization'], data['item_level'], data['profile_url'], data.get('raid_role', 'mdd'), data['is_main']))
        self.conn.commit()
        return self.cursor.lastrowid

    def delete_character(self, character_id: int):
        """Удалить персонажа"""
        self.cursor.execute('DELETE FROM characters WHERE id = ?', (character_id,))
        self.conn.commit()

    def update_character_main_status(self, character_id: int, is_main: bool):
        """Обновить статус основного персонажа"""
        self.cursor.execute('UPDATE characters SET is_main = ? WHERE id = ?', (1 if is_main else 0, character_id))
        self.conn.commit()

    def mark_characters_added(self, user_id: int):
        """Отметить, что пользователь добавил персонажей"""
        self.cursor.execute('UPDATE characters SET has_added = 1 WHERE user_id = ?', (user_id,))
        self.conn.commit()

    def has_added_characters(self, user_id: int) -> bool:
        """Проверить, добавил ли пользователь персонажей"""
        self.cursor.execute('SELECT 1 FROM characters WHERE user_id = ? AND has_added = 1', (user_id,))
        return self.cursor.fetchone() is not None

    def get_all_main_characters_with_priority(self, guild) -> list:
        """Получить всех основных персонажей с приоритетом"""
        result = []
        for member in guild.members:
            main_char = self.get_main_character(member.id)
            if main_char:
                priority = self.get_user_priority_level(member)
                result.append({
                    'user_id': member.id,
                    'user_name': member.display_name,
                    'character_id': main_char['id'],
                    'character_name': main_char['character_name'],
                    'class_spec': main_char['class_spec'],
                    'specialization': main_char['specialization'],
                    'item_level': main_char['item_level'],
                    'raid_role': main_char.get('raid_role', 'mdd'),
                    'priority': priority
                })
        result.sort(key=lambda x: (x['priority'], -x['item_level']))
        return result

    # ============================================
    # НАПОМИНАНИЯ
    # ============================================

    def get_character_reminder_roles(self) -> list:
        """Получить роли для напоминаний о персонажах"""
        roles_str = self.get_setting('character_reminder_roles', '')
        if not roles_str:
            return []
        return [int(r.strip()) for r in roles_str.split(',') if r.strip().isdigit()]

    def get_users_who_need_reminder(self, target_role_ids: list, guild) -> list:
        """Получить пользователей, которым нужно напоминание"""
        result = []
        for member in guild.members:
            if any(role.id in target_role_ids for role in member.roles):
                if not self.has_added_characters(member.id):
                    self.cursor.execute('INSERT OR IGNORE INTO character_reminders (user_id, reminder_count) VALUES (?, 0)', (member.id,))
                    self.conn.commit()
                    self.cursor.execute('SELECT reminder_count FROM character_reminders WHERE user_id = ?', (member.id,))
                    row = self.cursor.fetchone()
                    result.append({'user': member, 'reminder_count': row[0] if row else 0})
        return result

    def update_reminder_sent(self, user_id: int):
        """Обновить счётчик отправленных напоминаний"""
        self.cursor.execute('UPDATE character_reminders SET reminder_count = reminder_count + 1, last_reminder = CURRENT_TIMESTAMP WHERE user_id = ?', (user_id,))
        self.conn.commit()

    # ============================================
    # НАКАЗАНИЯ
    # ============================================

    def get_total_violations_by_character(self, character_id: int) -> int:
        """Получить общее количество нарушений персонажа"""
        self.cursor.execute('SELECT SUM(violation_count) FROM punishments WHERE character_id = ?', (character_id,))
        row = self.cursor.fetchone()
        return row[0] if row and row[0] else 0

    def get_punishments_by_character(self, character_id: int) -> list:
        """Получить все наказания персонажа"""
        self.cursor.execute('SELECT id, violation_count, reason, issuer_id, created_at FROM punishments WHERE character_id = ? ORDER BY created_at DESC', (character_id,))
        rows = self.cursor.fetchall()
        return [{'id': r[0], 'violation_count': r[1], 'reason': r[2], 'issuer_id': r[3], 'created_at': r[4]} for r in rows]

    def add_punishment(self, character_id: int, user_id: int, violation_count: int, reason: str, issuer_id: int) -> int:
        """Добавить наказание"""
        self.cursor.execute('INSERT INTO punishments (character_id, user_id, violation_count, reason, issuer_id) VALUES (?, ?, ?, ?, ?)', 
                           (character_id, user_id, violation_count, reason, issuer_id))
        self.conn.commit()
        return self.cursor.lastrowid

    def remove_punishment(self, punishment_id: int):
        """Удалить наказание"""
        self.cursor.execute('DELETE FROM punishments WHERE id = ?', (punishment_id,))
        self.conn.commit()

    def get_available_punishment_levels(self, character_id: int) -> list:
        """Получить доступные уровни наказаний"""
        current_violations = self.get_total_violations_by_character(character_id)
        if current_violations == 0:
            return [1]
        elif current_violations == 1:
            return [2]
        elif current_violations == 2:
            return [3]
        else:
            return []

    def search_characters(self, query: str, guild, limit: int = 10) -> list:
        """Поиск персонажей"""
        query = query.strip()
        all_results = []
        
        search_by_discord = query.startswith('@')
        if search_by_discord:
            query = query[1:].lower()
        else:
            query = query.lower()
        
        for member in guild.members:
            chars = self.get_user_characters(member.id)
            
            if search_by_discord:
                if (query in member.display_name.lower() or 
                    query in member.name.lower() or
                    str(member.id) == query):
                    for char in chars:
                        all_results.append({
                            'character_id': char['id'],
                            'character_name': char['character_name'],
                            'user_id': member.id,
                            'user_name': member.display_name,
                            'is_main': char['is_main'],
                            'violations': self.get_total_violations_by_character(char['id']),
                            'class_spec': char['class_spec'],
                            'item_level': char.get('item_level', 0),
                            'raid_role': char.get('raid_role', 'mdd')
                        })
                    if chars:
                        continue
            else:
                for char in chars:
                    if query in char['character_name'].lower():
                        all_results.append({
                            'character_id': char['id'],
                            'character_name': char['character_name'],
                            'user_id': member.id,
                            'user_name': member.display_name,
                            'is_main': char['is_main'],
                            'violations': self.get_total_violations_by_character(char['id']),
                            'class_spec': char['class_spec'],
                            'item_level': char.get('item_level', 0),
                            'raid_role': char.get('raid_role', 'mdd')
                        })
        
        if search_by_discord:
            all_results.sort(key=lambda x: (0 if x['is_main'] else 1, -x['item_level']))
        else:
            q = query.lower()
            all_results.sort(key=lambda x: (
                0 if x['character_name'].lower() == q else 1 if x['character_name'].lower().startswith(q) else 2,
                0 if x['is_main'] else 1
            ))
        
        return all_results[:limit]

    # ============================================
    # ПРЕДУПРЕЖДЕНИЯ
    # ============================================

    def add_warning(self, character_id: int, user_id: int, level: int, expires_at):
        """Добавить предупреждение"""
        self.cursor.execute('INSERT INTO warnings (character_id, user_id, level, expires_at, status) VALUES (?, ?, ?, ?, "active")', 
                           (character_id, user_id, level, expires_at))
        self.conn.commit()

    def get_active_warning(self, character_id: int):
        """Получить активное предупреждение"""
        self.cursor.execute('SELECT id, expires_at, status FROM warnings WHERE character_id = ? AND status = "active"', (character_id,))
        row = self.cursor.fetchone()
        if row:
            return {'id': row[0], 'expires_at': row[1], 'status': row[2]}
        return None

    def update_warning_status(self, warning_id: int, status: str):
        """Обновить статус предупреждения"""
        self.cursor.execute('UPDATE warnings SET status = ? WHERE id = ?', (status, warning_id))
        self.conn.commit()

    # ============================================
    # СМЕНА ОСНОВНОГО
    # ============================================

    def create_main_change_request(self, user_id: int, old_character_id: int, new_character_id: int, reason: str) -> int:
        """Создать запрос на смену основного персонажа"""
        self.cursor.execute('INSERT INTO main_change_requests (user_id, character_id, new_character_id, reason, status) VALUES (?, ?, ?, ?, "pending")', 
                           (user_id, old_character_id, new_character_id, reason))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_main_change_request_status(self, request_id: int, status: str, reviewer_id: int = None, review_reason: str = None):
        """Обновить статус запроса на смену основного"""
        if reviewer_id:
            self.cursor.execute('UPDATE main_change_requests SET status = ?, reviewer_id = ?, review_reason = ? WHERE id = ?', 
                               (status, reviewer_id, review_reason, request_id))
        else:
            self.cursor.execute('UPDATE main_change_requests SET status = ? WHERE id = ?', (status, request_id))
        self.conn.commit()

    # ============================================
    # СОСТАВЫ
    # ============================================

    def create_composition(self, name: str, leader_id: int, main_slots: int = 10, reserve_slots: int = 5) -> int:
        """Создать состав"""
        self.cursor.execute('INSERT INTO raids (name, leader_id, main_slots, reserve_slots, status) VALUES (?, ?, ?, ?, "active")', 
                           (name, leader_id, main_slots, reserve_slots))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_composition(self, raid_id: int):
        """Получить состав по ID"""
        self.cursor.execute('SELECT id, name, leader_id, status, main_slots, reserve_slots, message_id, channel_id FROM raids WHERE id = ?', (raid_id,))
        row = self.cursor.fetchone()
        if row:
            return {
                'id': row[0], 'name': row[1], 'leader_id': row[2], 'status': row[3],
                'main_slots': row[4], 'reserve_slots': row[5], 'message_id': row[6], 'channel_id': row[7]
            }
        return None

    def get_active_compositions(self) -> list:
        """Получить все активные составы"""
        self.cursor.execute('SELECT id, name, leader_id, main_slots, reserve_slots, message_id, channel_id FROM raids WHERE status = "active" ORDER BY id DESC')
        rows = self.cursor.fetchall()
        return [{'id': r[0], 'name': r[1], 'leader_id': r[2], 'main_slots': r[3], 'reserve_slots': r[4], 'message_id': r[5], 'channel_id': r[6]} for r in rows]

    def get_composition_members(self, raid_id: int) -> list:
        """Получить участников состава"""
        self.cursor.execute('''
            SELECT rm.user_id, rm.character_id, rm.role, rm.is_reserve,
                   c.character_name, c.class_spec, c.specialization, c.item_level, c.raid_role
            FROM raid_members rm
            JOIN characters c ON rm.character_id = c.id
            WHERE rm.raid_id = ?
            ORDER BY rm.is_reserve ASC
        ''', (raid_id,))
        rows = self.cursor.fetchall()
        return [{
            'user_id': r[0], 'character_id': r[1], 'role': r[2], 'is_reserve': bool(r[3]),
            'character_name': r[4], 'class_spec': r[5], 'specialization': r[6] or "", 'item_level': r[7] or 0, 'raid_role': r[8]
        } for r in rows]

    def add_composition_member(self, raid_id: int, user_id: int, character_id: int, role: str, is_reserve: bool = False) -> bool:
        """Добавить участника в состав"""
        try:
            self.cursor.execute('INSERT INTO raid_members (raid_id, user_id, character_id, role, is_reserve) VALUES (?, ?, ?, ?, ?)', 
                               (raid_id, user_id, character_id, role, 1 if is_reserve else 0))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def remove_composition_member(self, raid_id: int, user_id: int) -> bool:
        """Удалить участника из состава"""
        self.cursor.execute('DELETE FROM raid_members WHERE raid_id = ? AND user_id = ?', (raid_id, user_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def update_composition_member_role(self, raid_id: int, user_id: int, role: str) -> bool:
        """Обновить роль участника в составе"""
        self.cursor.execute('UPDATE raid_members SET role = ? WHERE raid_id = ? AND user_id = ?', (role, raid_id, user_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def move_to_reserve(self, raid_id: int, user_id: int, is_reserve: bool) -> bool:
        """Переместить участника в резерв"""
        self.cursor.execute('UPDATE raid_members SET is_reserve = ? WHERE raid_id = ? AND user_id = ?', (1 if is_reserve else 0, raid_id, user_id))
        self.conn.commit()
        return self.cursor.rowcount > 0

    def close_composition(self, raid_id: int):
        """Закрыть состав"""
        self.cursor.execute('UPDATE raids SET status = "closed" WHERE id = ?', (raid_id,))
        self.conn.commit()

    def save_composition_message(self, raid_id: int, channel_id: int, message_id: int):
        """Сохранить ID сообщения состава"""
        self.cursor.execute('UPDATE raids SET channel_id = ?, message_id = ? WHERE id = ?', (channel_id, message_id, raid_id))
        self.conn.commit()

    def save_composition_panel(self, raid_id: int, channel_id: int, message_id: int):
        """Сохранить ID панели управления составом"""
        self.cursor.execute('UPDATE raids SET panel_channel_id = ?, panel_message_id = ? WHERE id = ?', 
                           (channel_id, message_id, raid_id))
        self.conn.commit()

    def get_active_panels(self) -> list:
        """Получить активные панели управления"""
        try:
            self.cursor.execute('SELECT id, name, leader_id, main_slots, reserve_slots, panel_channel_id, panel_message_id FROM raids WHERE status = "active" AND panel_message_id IS NOT NULL')
            rows = self.cursor.fetchall()
            return [{'id': r[0], 'name': r[1], 'leader_id': r[2], 'main_slots': r[3], 'reserve_slots': r[4], 'panel_channel_id': r[5], 'panel_message_id': r[6]} for r in rows]
        except:
            return []

    def duplicate_composition(self, raid_id: int, new_name: str, new_leader_id: int) -> int:
        """Дублировать состав"""
        old = self.get_composition(raid_id)
        if not old:
            return 0
        new_id = self.create_composition(new_name, new_leader_id, old.get('main_slots', 10), old.get('reserve_slots', 5))
        old_members = self.get_composition_members(raid_id)
        for m in old_members:
            self.add_composition_member(new_id, m['user_id'], m['character_id'], m['role'], m['is_reserve'])
        return new_id

    # ============================================
    # ЗАДАНИЯ ДЛЯ НАКАЗАНИЙ
    # ============================================

    def get_task_settings(self, task_number: int) -> str:
        """Получить текст задания по номеру"""
        self.cursor.execute('SELECT task_text FROM task_settings WHERE task_number = ?', (task_number,))
        row = self.cursor.fetchone()
        return row[0] if row else ""

    def set_task_settings(self, task_number: int, task_text: str):
        """Установить текст задания"""
        self.cursor.execute('INSERT OR REPLACE INTO task_settings (task_number, task_text) VALUES (?, ?)', (task_number, task_text))
        self.conn.commit()

    def get_all_tasks(self) -> list:
        """Получить все задания"""
        self.cursor.execute('SELECT task_text FROM task_settings ORDER BY task_number')
        rows = self.cursor.fetchall()
        return [row[0] for row in rows if row[0]]

    def create_punishment_task(self, user_id: int, character_id: int, punishment_id: int, task_text: str) -> int:
        """Создать задание для наказания"""
        self.cursor.execute('INSERT INTO punishment_tasks (user_id, character_id, punishment_id, task_text, status) VALUES (?, ?, ?, ?, "pending")', 
                           (user_id, character_id, punishment_id, task_text))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_punishment_task(self, task_id: int):
        """Получить задание наказания по ID"""
        self.cursor.execute('SELECT id, user_id, character_id, punishment_id, task_text, status, channel_id FROM punishment_tasks WHERE id = ?', (task_id,))
        row = self.cursor.fetchone()
        if row:
            return {'id': row[0], 'user_id': row[1], 'character_id': row[2], 'punishment_id': row[3], 'task_text': row[4], 'status': row[5], 'channel_id': row[6]}
        return None

    def update_task_channel(self, task_id: int, channel_id: int):
        """Обновить канал задания"""
        self.cursor.execute('UPDATE punishment_tasks SET channel_id = ? WHERE id = ?', (channel_id, task_id))
        self.conn.commit()

    def complete_task(self, task_id: int):
        """Отметить задание как выполненное"""
        self.cursor.execute('UPDATE punishment_tasks SET status = "completed" WHERE id = ?', (task_id,))
        self.conn.commit()

    # ============================================
    # СТАТИК
    # ============================================

    def get_static_request_message(self) -> str:
        """Получить сообщение для заявок в статик"""
        return self.get_setting('static_request_message', '📋 **Запрос в статик**\n\nЕсли вы хотите попасть в основной состав рейдовой группы, заполните заявку ниже.')

    def set_static_request_message(self, message: str):
        """Установить сообщение для заявок в статик"""
        self.set_setting('static_request_message', message)

    def create_static_request(self, user_id: int, character_id: int, imgur_link: str, additional_info: str, channel_id: int) -> int:
        """Создать заявку в статик"""
        self.cursor.execute('INSERT INTO static_requests (user_id, character_id, imgur_link, additional_info, channel_id, status) VALUES (?, ?, ?, ?, ?, "pending")', 
                           (user_id, character_id, imgur_link, additional_info, channel_id))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_static_request_status(self, request_id: int, status: str, reviewer_id: int):
        """Обновить статус заявки в статик"""
        self.cursor.execute('UPDATE static_requests SET status = ?, reviewer_id = ? WHERE id = ?', (status, reviewer_id, request_id))
        self.conn.commit()

    def get_pending_static_request(self, channel_id: int) -> dict:
        """Получить ожидающую заявку в статик по ID канала"""
        self.cursor.execute('''
            SELECT sr.*, c.character_name, c.class_spec, c.specialization, c.item_level, c.raid_role
            FROM static_requests sr
            LEFT JOIN characters c ON sr.character_id = c.id
            WHERE sr.channel_id = ? AND sr.status = "pending"
        ''', (channel_id,))
        
        row = self.cursor.fetchone()
        if not row:
            return {}
        
        columns = [desc[0] for desc in self.cursor.description]
        result = {}
        for i, col in enumerate(columns):
            result[col] = row[i] if i < len(row) else None
        return result

    def save_static_vote(self, channel_id: int, user_id: int, vote: bool):
        """Сохранить голос за заявку в статик"""
        vote_int = 1 if vote else 0
        self.cursor.execute(
            'INSERT OR REPLACE INTO static_votes (channel_id, user_id, vote) VALUES (?, ?, ?)',
            (channel_id, user_id, vote_int)
        )
        self.conn.commit()

    def get_static_votes(self, channel_id: int) -> dict:
        """Получить все голоса для канала"""
        self.cursor.execute(
            'SELECT user_id, vote FROM static_votes WHERE channel_id = ?',
            (channel_id,)
        )
        votes = {}
        for row in self.cursor.fetchall():
            votes[row[0]] = bool(row[1])
        return votes

    def clear_static_votes(self, channel_id: int):
        """Удалить голоса для канала"""
        self.cursor.execute('DELETE FROM static_votes WHERE channel_id = ?', (channel_id,))
        self.conn.commit()

    # ============================================
    # ОЧИСТКА
    # ============================================

    def clear_table(self, table: str) -> int:
        """Очистить таблицу"""
        self.cursor.execute(f'DELETE FROM {table}')
        deleted = self.cursor.rowcount
        self.conn.commit()
        return deleted

    def clear_all_data(self) -> int:
        """Очистить все таблицы"""
        tables = ['applications', 'blacklist', 'appeals', 'absences', 'characters', 'character_reminders', 'punishments', 'warnings', 'main_change_requests', 'raids', 'raid_members', 'punishment_tasks', 'task_settings', 'static_requests']
        total = 0
        for table in tables:
            self.cursor.execute(f'DELETE FROM {table}')
            total += self.cursor.rowcount
        self.conn.commit()
        return total

    # ============================================
    # РОЛИ
    # ============================================

    def init_default_roles(self, guild):
        """Инициализирует роли по умолчанию (синхронно)"""
        role_mappings = {'guild_master': 'Глава гильдии', 'vice_master': 'Зам. главы', 'raid_leader': 'Рейд-лидер', 'officer': 'Офицер'}
        for key, role_name in role_mappings.items():
            if not self.get_setting(key):
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    self.set_setting(key, str(role.id))

    def get_reviewer_roles(self) -> list:
        """Получить роли, которые могут просматривать заявки"""
        roles = []
        for role_id in [self.get_setting('officer', ''), self.get_setting('raid_leader', ''), self.get_setting('vice_master', ''), self.get_setting('guild_master', '')]:
            if role_id and role_id.isdigit():
                roles.append(int(role_id))
        return roles

    def get_role_permissions_settings(self, role_key: str) -> dict:
        """Получить настройки прав для роли"""
        self.cursor.execute('SELECT permission_key, enabled FROM role_permissions WHERE role_key = ?', (role_key,))
        rows = self.cursor.fetchall()
        return {row[0]: bool(row[1]) for row in rows}

    def set_role_permission(self, role_key: str, permission_key: str, value: str):
        """Установить право для роли"""
        self.set_setting(f"perm_{role_key}_{permission_key}", str(value))

    def get_reports_roles(self) -> list:
        """Получить роли для доступа к жалобам"""
        roles_str = self.get_setting('reports_roles', '')
        if roles_str:
            return [int(r.strip()) for r in roles_str.split(',') if r.strip().isdigit()]
        return self.get_reviewer_roles()

    # ============================================
    # ЖАЛОБЫ
    # ============================================

    def get_next_report_id(self) -> int:
        """Получить следующий ID для жалобы"""
        self.cursor.execute('SELECT COALESCE(MAX(id), 0) + 1 FROM reports')
        return self.cursor.fetchone()[0]

    def create_report(self, report_id, reporter_id, violator_id, violator_name,
                    violation_type, description, evidence, witnesses, channel_id,
                    is_anonymous=False):
        """Создать жалобу"""
        self.cursor.execute('''
            INSERT INTO reports (id, reporter_id, violator_id, violator_name,
                                violation_type, description, evidence, witnesses,
                                channel_id, status, is_anonymous)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', ?)
        ''', (report_id, reporter_id, violator_id, violator_name,
            violation_type, description, evidence, witnesses, channel_id,
            1 if is_anonymous else 0))
        self.conn.commit()

    def update_report_status(self, report_id, status, resolver_id=None, resolution=None):
        """Обновить статус жалобы"""
        if resolver_id and resolution:
            self.cursor.execute('''
                UPDATE reports SET status = ?, resolver_id = ?, resolution = ?, resolved_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, resolver_id, resolution, report_id))
        else:
            self.cursor.execute('UPDATE reports SET status = ? WHERE id = ?', (status, report_id))
        self.conn.commit()

    def get_report_by_id(self, report_id):
        """Получить жалобу по ID"""
        self.cursor.execute('SELECT * FROM reports WHERE id = ?', (report_id,))
        row = self.cursor.fetchone()
        if not row:
            return {}
        columns = [desc[0] for desc in self.cursor.description]
        return dict(zip(columns, row))

    # ============================================
    # МЕТОДЫ ДЛЯ КУРАТОРОВ (ОБУЧЕНИЕ РЛ)
    # ============================================

    def get_curator_channel_message(self, guild_id: int, msg_type: str) -> Optional[Dict]:
        """Получает сохраненное сообщение из канала курсантов"""
        try:
            self.cursor.execute('''
                SELECT setting_value FROM settings 
                WHERE guild_id = ? AND setting_key = ?
            ''', (guild_id, f'curator_{msg_type}_message'))
            row = self.cursor.fetchone()
            if row:
                parts = row[0].split(':')
                if len(parts) == 2:
                    return {
                        'channel_id': int(parts[0]),
                        'message_id': int(parts[1])
                    }
            return None
        except:
            return None

    def get_curator_message(self, guild_id: int, msg_type: str) -> Optional[Dict]:
        """Получает сохраненное сообщение панели куратора"""
        try:
            self.cursor.execute('''
                SELECT setting_value FROM settings 
                WHERE guild_id = ? AND setting_key = ?
            ''', (guild_id, f'curator_{msg_type}_message'))
            row = self.cursor.fetchone()
            if row:
                parts = row[0].split(':')
                if len(parts) == 2:
                    return {
                        'channel_id': int(parts[0]),
                        'message_id': int(parts[1])
                    }
            return None
        except:
            return None

    def save_curator_message(self, guild_id: int, channel_id: int, message_id: int, msg_type: str):
        """Сохраняет ID сообщения панели куратора"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO settings (guild_id, setting_key, setting_value)
                VALUES (?, ?, ?)
            ''', (guild_id, f'curator_{msg_type}_message', f"{channel_id}:{message_id}"))
            self.conn.commit()
        except:
            pass

    def save_curator_channel_message(self, guild_id: int, channel_id: int, message_id: int, msg_type: str):
        """Сохраняет ID сообщения в канале курсантов"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO settings (guild_id, setting_key, setting_value)
                VALUES (?, ?, ?)
            ''', (guild_id, f'curator_{msg_type}_message', f"{channel_id}:{message_id}"))
            self.conn.commit()
        except:
            pass

    def add_curator_log(self, action: str, performed_by: int, details: str = '', target_id: int = None):
        """Добавляет запись в лог кураторов"""
        try:
            self.cursor.execute('''
                INSERT INTO curator_logs (action, details, performed_by, target_id)
                VALUES (?, ?, ?, ?)
            ''', (action, details, performed_by, target_id))
            self.conn.commit()
        except:
            pass

    def get_curator_logs(self, limit: int = 20) -> List[Dict]:
        """Получить логи кураторов"""
        try:
            self.cursor.execute('''
                SELECT id, action, details, performed_by, target_id, created_at
                FROM curator_logs
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'action': row[1],
                    'details': row[2],
                    'performed_by': row[3],
                    'target_id': row[4],
                    'created_at': row[5]
                }
                for row in rows
            ]
        except:
            return []

    # ============================================
    # МЕТОДЫ ДЛЯ РАЗДЕЛОВ (КУРАТОРЫ)
    # ============================================

    def create_section(self, name: str, theory_link: str = '', pass_condition: str = '') -> int:
        """Создать новый раздел обучения"""
        try:
            self.cursor.execute('''
                INSERT INTO sections (name, theory_link, pass_condition)
                VALUES (?, ?, ?)
            ''', (name, theory_link, pass_condition))
            self.conn.commit()
            return self.cursor.lastrowid
        except:
            return 0

    def get_all_sections(self) -> List[Dict]:
        """Получить все разделы"""
        try:
            self.cursor.execute('''
                SELECT id, name, theory_link, pass_condition, created_at
                FROM sections
                ORDER BY created_at DESC
            ''')
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'name': row[1] or 'Без названия',
                    'theory_link': row[2] or '',
                    'pass_condition': row[3] or '',
                    'created_at': row[4]
                }
                for row in rows
            ]
        except:
            return []

    def get_section(self, section_id: int) -> Optional[Dict]:
        """Получить раздел по ID"""
        try:
            self.cursor.execute('''
                SELECT id, name, theory_link, pass_condition, created_at
                FROM sections
                WHERE id = ?
            ''', (section_id,))
            row = self.cursor.fetchone()
            if not row:
                return None
            return {
                'id': row[0],
                'name': row[1] or 'Без названия',
                'theory_link': row[2] or '',
                'pass_condition': row[3] or '',
                'created_at': row[4]
            }
        except:
            return None

    def update_section(self, section_id: int, name: str = None, theory_link: str = None, pass_condition: str = None):
        """Обновить раздел"""
        try:
            if name is not None:
                self.cursor.execute('UPDATE sections SET name = ? WHERE id = ?', (name, section_id))
            if theory_link is not None:
                self.cursor.execute('UPDATE sections SET theory_link = ? WHERE id = ?', (theory_link, section_id))
            if pass_condition is not None:
                self.cursor.execute('UPDATE sections SET pass_condition = ? WHERE id = ?', (pass_condition, section_id))
            self.conn.commit()
        except:
            pass

    # ============================================
    # МЕТОДЫ ДЛЯ ТЕСТОВ (КУРАТОРЫ)
    # ============================================

    def create_test(self, section_id: int, question_text: str, max_score: int = 10) -> int:
        """Создать тестовый вопрос"""
        try:
            self.cursor.execute('''
                INSERT INTO tests (section_id, question_text, max_score)
                VALUES (?, ?, ?)
            ''', (section_id, question_text, max_score))
            self.conn.commit()
            return self.cursor.lastrowid
        except:
            return 0

    def get_tests_for_section(self, section_id: int) -> List[Dict]:
        """Получить все тесты для раздела"""
        try:
            self.cursor.execute('''
                SELECT id, section_id, question_text, max_score, created_at
                FROM tests
                WHERE section_id = ?
                ORDER BY created_at DESC
            ''', (section_id,))
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'section_id': row[1],
                    'question_text': row[2],
                    'max_score': row[3],
                    'created_at': row[4]
                }
                for row in rows
            ]
        except:
            return []

    # ============================================
    # МЕТОДЫ ДЛЯ ЗАДАНИЙ (КУРАТОРЫ)
    # ============================================

    def create_task(self, section_id: int, title: str, description: str, 
                    difficulty: int = 1, points_reward: int = 10) -> int:
        """Создать задание для раздела"""
        try:
            self.cursor.execute('''
                INSERT INTO tasks (section_id, title, description, difficulty, points_reward)
                VALUES (?, ?, ?, ?, ?)
            ''', (section_id, title, description, difficulty, points_reward))
            self.conn.commit()
            return self.cursor.lastrowid
        except:
            return 0

    def get_tasks_for_section(self, section_id: int) -> List[Dict]:
        """Получить все задания для раздела"""
        try:
            self.cursor.execute('''
                SELECT id, section_id, title, description, difficulty, points_reward, created_at
                FROM tasks
                WHERE section_id = ?
                ORDER BY created_at DESC
            ''', (section_id,))
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'section_id': row[1],
                    'title': row[2] or 'Без названия',
                    'description': row[3] or '',
                    'difficulty': row[4] or 1,
                    'points_reward': row[5] or 0,
                    'created_at': row[6]
                }
                for row in rows
            ]
        except:
            return []

    def get_task(self, task_id: int) -> Optional[Dict]:
        """Получить задание по ID"""
        try:
            self.cursor.execute('''
                SELECT id, section_id, title, description, difficulty, points_reward, created_at
                FROM tasks
                WHERE id = ?
            ''', (task_id,))
            row = self.cursor.fetchone()
            if not row:
                return None
            return {
                'id': row[0],
                'section_id': row[1],
                'title': row[2] or 'Без названия',
                'description': row[3] or '',
                'difficulty': row[4] or 1,
                'points_reward': row[5] or 0,
                'created_at': row[6]
            }
        except:
            return None

    def get_all_tasks(self) -> List[Dict]:
        """Получить все задания (для выдачи)"""
        try:
            self.cursor.execute('''
                SELECT id, section_id, title, description, difficulty, points_reward, created_at
                FROM tasks
                ORDER BY created_at DESC
            ''')
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'section_id': row[1],
                    'title': row[2] or 'Без названия',
                    'description': row[3] or '',
                    'difficulty': row[4] or 1,
                    'points_reward': row[5] or 0,
                    'created_at': row[6]
                }
                for row in rows
            ]
        except:
            return []

    def delete_task(self, task_id: int):
        """Удалить задание"""
        try:
            self.cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            self.conn.commit()
        except:
            pass

    # ============================================
    # МЕТОДЫ ДЛЯ ЗАЯВОК НА ОБУЧЕНИЕ (КУРАТОРЫ)
    # ============================================

    def create_trainee_application(self, user_id: int, character_id: int, 
                                   experience: str, motivation: str) -> int:
        """Создать заявку на обучение"""
        try:
            self.cursor.execute('''
                INSERT INTO trainee_applications (user_id, character_id, experience, motivation)
                VALUES (?, ?, ?, ?)
            ''', (user_id, character_id, experience, motivation))
            self.conn.commit()
            return self.cursor.lastrowid
        except:
            return 0

    def get_pending_applications(self) -> List[Dict]:
        """Получить все заявки в ожидании"""
        try:
            self.cursor.execute('''
                SELECT id, user_id, character_id, experience, motivation, applied_at
                FROM trainee_applications
                WHERE status = 'pending'
                ORDER BY applied_at ASC
            ''')
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'character_id': row[2],
                    'experience': row[3] or '',
                    'motivation': row[4] or '',
                    'applied_at': row[5]
                }
                for row in rows
            ]
        except:
            return []

    def review_application(self, app_id: int, status: str, reviewer_id: int, comment: str = ''):
        """Рассмотреть заявку на обучение"""
        try:
            self.cursor.execute('''
                UPDATE trainee_applications 
                SET status = ?, reviewed_at = CURRENT_TIMESTAMP, reviewer_id = ?, review_comment = ?
                WHERE id = ?
            ''', (status, reviewer_id, comment, app_id))
            self.conn.commit()
        except:
            pass

    # ============================================
    # МЕТОДЫ ДЛЯ НАЗНАЧЕНИЙ (КУРАТОРЫ)
    # ============================================

    def create_assignment(self, user_id: int, section_id: int) -> int:
        """Назначить игрока на раздел обучения"""
        try:
            self.cursor.execute('''
                INSERT INTO assignments (user_id, section_id)
                VALUES (?, ?)
            ''', (user_id, section_id))
            self.conn.commit()
            return self.cursor.lastrowid
        except:
            return 0

    def get_assignments_for_user(self, user_id: int) -> List[Dict]:
        """Получить все назначения пользователя"""
        try:
            self.cursor.execute('''
                SELECT id, user_id, section_id, status, assigned_at, completed_at, points_earned
                FROM assignments
                WHERE user_id = ?
                ORDER BY assigned_at DESC
            ''', (user_id,))
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'section_id': row[2],
                    'status': row[3] or 'active',
                    'assigned_at': row[4],
                    'completed_at': row[5],
                    'points_earned': row[6] or 0
                }
                for row in rows
            ]
        except:
            return []

    def get_active_students_with_progress(self) -> List[Dict]:
        """Получить активных учеников с прогрессом"""
        try:
            self.cursor.execute('''
                SELECT 
                    a.id as assignment_id,
                    a.user_id,
                    a.section_id,
                    a.assigned_at,
                    a.points_earned,
                    s.name as section_name,
                    COUNT(DISTINCT t.id) as total_tasks,
                    SUM(CASE WHEN tc.status = 'approved' THEN 1 ELSE 0 END) as tasks_completed
                FROM assignments a
                JOIN sections s ON a.section_id = s.id
                LEFT JOIN tasks t ON s.id = t.section_id
                LEFT JOIN task_completions tc ON a.id = tc.assignment_id
                WHERE a.status = 'active'
                GROUP BY a.id
                ORDER BY a.points_earned DESC
            ''')
            rows = self.cursor.fetchall()
            
            result = []
            for row in rows:
                approved = row[7] or 0
                total = row[6] or 0
                progress = int((approved / total * 100)) if total > 0 else 0
                
                result.append({
                    'assignment_id': row[0],
                    'user_id': row[1],
                    'section_id': row[2],
                    'assigned_at': row[3],
                    'points_earned': row[4] or 0,
                    'section_name': row[5] or 'Неизвестно',
                    'tasks_completed': approved,
                    'total_tasks': total,
                    'progress': progress
                })
            
            return result
        except:
            return []

    def get_rating(self) -> List[Dict]:
        """Получить рейтинг учеников"""
        try:
            self.cursor.execute('''
                SELECT 
                    a.user_id,
                    COUNT(DISTINCT a.section_id) as sections,
                    SUM(a.points_earned) as total_points,
                    COUNT(DISTINCT tc.id) as tasks_completed
                FROM assignments a
                LEFT JOIN task_completions tc ON a.id = tc.assignment_id AND tc.status = 'approved'
                GROUP BY a.user_id
                ORDER BY total_points DESC
            ''')
            rows = self.cursor.fetchall()
            
            return [
                {
                    'user_id': row[0],
                    'sections': row[1] or 0,
                    'total_points': row[2] or 0,
                    'tasks_completed': row[3] or 0
                }
                for row in rows
            ]
        except:
            return []

    def get_recent_student_activity(self, limit: int = 5) -> List[Dict]:
        """Получить последние активности учеников"""
        try:
            self.cursor.execute('''
                SELECT 
                    tc.id,
                    tc.submitted_at,
                    tc.status,
                    tc.points_awarded,
                    a.user_id,
                    t.title as task_title,
                    CASE 
                        WHEN tc.status = 'pending' THEN '📤 Сдал задание'
                        WHEN tc.status = 'approved' THEN '✅ Задание принято'
                        WHEN tc.status = 'rejected' THEN '❌ Задание отклонено'
                        ELSE '📝 Действие'
                    END as action
                FROM task_completions tc
                JOIN assignments a ON tc.assignment_id = a.id
                JOIN tasks t ON tc.task_id = t.id
                ORDER BY tc.submitted_at DESC
                LIMIT ?
            ''', (limit,))
            rows = self.cursor.fetchall()
            
            return [
                {
                    'id': row[0],
                    'submitted_at': row[1],
                    'status': row[2],
                    'points_awarded': row[3] or 0,
                    'user_id': row[4],
                    'task_title': row[5] or 'Без названия',
                    'action': row[6] or '📝 Действие'
                }
                for row in rows
            ]
        except:
            return []

    # ============================================
    # МЕТОДЫ ДЛЯ КАНДИДАТОВ (TRAINEES)
    # ============================================

    def get_trainee_by_user(self, user_id: int) -> Optional[Dict]:
        """Получить кандидата по ID пользователя"""
        try:
            self.cursor.execute('''
                SELECT id, user_id, main_character_id, mentor_id, level, points, status,
                       experience, classes_known, motivation, available_days, 
                       applied_at, graduated_at, last_activity
                FROM trainees
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
            ''', (user_id,))
            row = self.cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'user_id': row[1],
                'main_character_id': row[2],
                'mentor_id': row[3],
                'level': row[4] or 1,
                'points': row[5] or 0,
                'status': row[6] or 'pending',
                'experience': row[7] or '',
                'classes_known': row[8] or '',
                'motivation': row[9] or '',
                'available_days': row[10] or '',
                'applied_at': row[11],
                'graduated_at': row[12],
                'last_activity': row[13]
            }
        except:
            return None

    def get_trainee_by_id(self, trainee_id: int) -> Optional[Dict]:
        """Получить кандидата по ID"""
        try:
            self.cursor.execute('''
                SELECT id, user_id, main_character_id, mentor_id, level, points, status,
                       experience, classes_known, motivation, available_days, 
                       applied_at, graduated_at, last_activity
                FROM trainees
                WHERE id = ?
            ''', (trainee_id,))
            row = self.cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'user_id': row[1],
                'main_character_id': row[2],
                'mentor_id': row[3],
                'level': row[4] or 1,
                'points': row[5] or 0,
                'status': row[6] or 'pending',
                'experience': row[7] or '',
                'classes_known': row[8] or '',
                'motivation': row[9] or '',
                'available_days': row[10] or '',
                'applied_at': row[11],
                'graduated_at': row[12],
                'last_activity': row[13]
            }
        except:
            return None

    def add_trainee_log(self, trainee_id: int, action: str, performed_by: int = None):
        """Добавить запись в лог кандидата"""
        try:
            self.cursor.execute('''
                INSERT INTO trainee_logs (trainee_id, action, performed_by)
                VALUES (?, ?, ?)
            ''', (trainee_id, action, performed_by))
            self.conn.commit()
        except:
            pass

    # ============================================
    # МЕТОДЫ ДЛЯ ЗАДАНИЙ КАНДИДАТОВ
    # ============================================

    def create_trainee_task(self, trainee_id: int, mentor_id: int, title: str,
                           description: str, difficulty: int, points_reward: int,
                           deadline: datetime) -> int:
        """Создать задание для кандидата с дедлайном"""
        try:
            self.cursor.execute('''
                INSERT INTO trainee_tasks 
                (trainee_id, mentor_id, title, description, difficulty, points_reward, deadline)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (trainee_id, mentor_id, title, description, difficulty, points_reward, deadline))
            self.conn.commit()
            return self.cursor.lastrowid
        except:
            return 0

    def get_trainee_task(self, task_id: int) -> Optional[Dict]:
        """Получить задание кандидата по ID"""
        try:
            self.cursor.execute('''
                SELECT 
                    tt.id, tt.trainee_id, tt.mentor_id, tt.title, tt.description, 
                    tt.difficulty, tt.points_reward, tt.status, tt.created_at, 
                    tt.deadline, tt.completed_at, tt.approved_at, tt.mentor_comment,
                    tr.user_id as trainee_user_id
                FROM trainee_tasks tt
                JOIN trainees tr ON tt.trainee_id = tr.id
                WHERE tt.id = ?
            ''', (task_id,))
            row = self.cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'trainee_id': row[1],
                'mentor_id': row[2],
                'title': row[3] or 'Без названия',
                'description': row[4] or '',
                'difficulty': row[5] or 1,
                'points_reward': row[6] or 0,
                'status': row[7] or 'pending',
                'created_at': row[8],
                'deadline': row[9],
                'completed_at': row[10],
                'approved_at': row[11],
                'mentor_comment': row[12] or '',
                'trainee_user_id': row[13]
            }
        except:
            return None

    def get_report_for_task(self, task_id: int) -> Optional[Dict]:
        """Получить отчет по заданию кандидата"""
        try:
            self.cursor.execute('''
                SELECT id, task_id, trainee_id, answer, submitted_at, mentor_feedback, points_awarded
                FROM trainee_reports
                WHERE task_id = ?
                ORDER BY submitted_at DESC
                LIMIT 1
            ''', (task_id,))
            row = self.cursor.fetchone()
            
            if not row:
                return None
            
            return {
                'id': row[0],
                'task_id': row[1],
                'trainee_id': row[2],
                'answer': row[3] or '',
                'submitted_at': row[4],
                'mentor_feedback': row[5] or '',
                'points_awarded': row[6] or 0
            }
        except:
            return None

    def get_pending_tasks_for_curator(self, curator_id: int) -> List[Dict]:
        """Получить все задания на проверку для куратора"""
        try:
            self.cursor.execute('''
                SELECT 
                    tt.id,
                    tt.trainee_id,
                    tt.mentor_id,
                    tt.title,
                    tt.description,
                    tt.difficulty,
                    tt.points_reward,
                    tt.status,
                    tt.created_at,
                    tt.deadline,
                    tt.completed_at,
                    tr.user_id,
                    tr.character_id
                FROM trainee_tasks tt
                JOIN trainees tr ON tt.trainee_id = tr.id
                WHERE tt.mentor_id = ? 
                AND tt.status = 'completed'
                ORDER BY tt.created_at DESC
            ''', (curator_id,))
            rows = self.cursor.fetchall()
            
            return [
                {
                    'id': row[0],
                    'trainee_id': row[1],
                    'mentor_id': row[2],
                    'title': row[3] or 'Без названия',
                    'description': row[4] or '',
                    'difficulty': row[5] or 1,
                    'points_reward': row[6] or 0,
                    'status': row[7] or 'pending',
                    'created_at': row[8],
                    'deadline': row[9],
                    'completed_at': row[10],
                    'user_id': row[11],
                    'character_id': row[12]
                }
                for row in rows
            ]
        except:
            return []

    def create_trainee_application(self, user_id: int, character_id: int, 
                                experience: str, motivation: str) -> int:
        """Создать заявку на обучение"""
        try:
            self.cursor.execute('''
                INSERT INTO trainee_applications (user_id, character_id, experience, motivation)
                VALUES (?, ?, ?, ?)
            ''', (user_id, character_id, experience, motivation))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"❌ Ошибка create_trainee_application: {e}")
            return 0


    def get_pending_applications(self) -> List[Dict]:
        """Получить все заявки в ожидании"""
        try:
            self.cursor.execute('''
                SELECT id, user_id, character_id, experience, motivation, applied_at
                FROM trainee_applications
                WHERE status = 'pending'
                ORDER BY applied_at ASC
            ''')
            rows = self.cursor.fetchall()
            return [
                {
                    'id': row[0],
                    'user_id': row[1],
                    'character_id': row[2],
                    'experience': row[3] or '',
                    'motivation': row[4] or '',
                    'applied_at': row[5]
                }
                for row in rows
            ]
        except Exception as e:
            print(f"❌ Ошибка get_pending_applications: {e}")
            return []


    def get_application(self, app_id: int) -> Optional[Dict]:
        """Получить заявку по ID"""
        try:
            self.cursor.execute('''
                SELECT id, user_id, character_id, experience, motivation, status, 
                    applied_at, reviewed_at, reviewer_id, review_comment
                FROM trainee_applications
                WHERE id = ?
            ''', (app_id,))
            row = self.cursor.fetchone()
            if not row:
                return None
            return {
                'id': row[0],
                'user_id': row[1],
                'character_id': row[2],
                'experience': row[3] or '',
                'motivation': row[4] or '',
                'status': row[5] or 'pending',
                'applied_at': row[6],
                'reviewed_at': row[7],
                'reviewer_id': row[8],
                'review_comment': row[9] or ''
            }
        except Exception as e:
            print(f"❌ Ошибка get_application: {e}")
            return None


    def review_application(self, app_id: int, status: str, reviewer_id: int, comment: str = ''):
        """Рассмотреть заявку"""
        try:
            self.cursor.execute('''
                UPDATE trainee_applications 
                SET status = ?, reviewed_at = CURRENT_TIMESTAMP, reviewer_id = ?, review_comment = ?
                WHERE id = ?
            ''', (status, reviewer_id, comment, app_id))
            self.conn.commit()
        except Exception as e:
            print(f"❌ Ошибка review_application: {e}")

    def remove_trainee(self, user_id: int):
        """Полностью удалить запись о курсанте по ID пользователя"""
        try:
            # Удаляем все задания курсанта
            self.cursor.execute('''
                DELETE FROM trainee_tasks 
                WHERE trainee_id IN (SELECT id FROM trainees WHERE user_id = ?)
            ''', (user_id,))
            # Удаляем все логи курсанта
            self.cursor.execute('''
                DELETE FROM trainee_logs 
                WHERE trainee_id IN (SELECT id FROM trainees WHERE user_id = ?)
            ''', (user_id,))
            # Удаляем наказания курсанта
            self.cursor.execute('''
                DELETE FROM trainee_punishments 
                WHERE trainee_id IN (SELECT id FROM trainees WHERE user_id = ?)
            ''', (user_id,))
            # Удаляем саму запись
            self.cursor.execute('DELETE FROM trainees WHERE user_id = ?', (user_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка удаления курсанта {user_id}: {e}")
            return False
            
   # =========================================================
    # МЕТОДЫ ДЛЯ ЗАЯВОК НА СМЕНУ ОСНОВНОГО ПЕРСОНАЖА
    # =========================================================

    def update_main_change_request_status(self, request_id: int, status: str, reviewer_id: int):
        """Обновить статус заявки на смену основного персонажа"""
        try:
            self.cursor.execute('''
                UPDATE main_change_requests 
                SET status = ?, reviewed_at = CURRENT_TIMESTAMP, reviewer_id = ?
                WHERE id = ?
            ''', (status, reviewer_id, request_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка обновления статуса заявки: {e}")
            return False

    def get_pending_main_change_request(self, user_id: int) -> dict:
        """Получить активную заявку на смену основного персонажа для пользователя"""
        try:
            self.cursor.execute('''
                SELECT * FROM main_change_requests 
                WHERE user_id = ? AND status = 'pending'
                ORDER BY created_at DESC LIMIT 1
            ''', (user_id,))
            row = self.cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            print(f"❌ Ошибка получения заявки: {e}")
            return None

    def create_main_change_request(self, user_id: int, old_char_id: int, new_char_id: int, reason: str) -> int:
        """Создать новую заявку на смену основного персонажа"""
        try:
            self.cursor.execute('''
                INSERT INTO main_change_requests (user_id, old_char_id, new_char_id, reason, status)
                VALUES (?, ?, ?, ?, 'pending')
            ''', (user_id, old_char_id, new_char_id, reason))
            self.conn.commit()
            return self.cursor.lastrowid
        except Exception as e:
            print(f"❌ Ошибка создания заявки: {e}")
            return None

    def update_main_change_request_channel(self, request_id: int, channel_id: int):
        """Сохранить ID канала для заявки"""
        try:
            self.cursor.execute('''
                UPDATE main_change_requests SET channel_id = ? WHERE id = ?
            ''', (channel_id, request_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"❌ Ошибка обновления канала заявки: {e}")
            return False

    def create_main_change_table(self):
        """Создать таблицу для заявок на смену основного персонажа"""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS main_change_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    old_char_id INTEGER NOT NULL,
                    new_char_id INTEGER NOT NULL,
                    reason TEXT,
                    status TEXT DEFAULT 'pending',
                    channel_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    reviewed_at TIMESTAMP,
                    reviewer_id INTEGER
                )
            ''')
            self.conn.commit()
            print("✅ Таблица main_change_requests создана/проверена")
            return True
        except Exception as e:
            print(f"❌ Ошибка создания таблицы: {e}")
            return False    
