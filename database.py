"""
SQLite database — Qarz Hisobchi Bot v4.0
Yangi: due_date, category, currency, undo_log, chat_settings
"""
import sqlite3, os, json
from contextlib import contextmanager
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qarz_bot.db')


class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()

    @contextmanager
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self.get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS debts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id     INTEGER NOT NULL,
                    name        TEXT    NOT NULL,
                    amount      REAL    NOT NULL,
                    remaining   REAL    NOT NULL,
                    note        TEXT    DEFAULT '',
                    added_by    TEXT    DEFAULT '',
                    message_id  INTEGER DEFAULT 0,
                    is_active   INTEGER DEFAULT 1,
                    due_date    TEXT    DEFAULT NULL,
                    category    TEXT    DEFAULT '',
                    currency    TEXT    DEFAULT 'UZS',
                    created_at  TEXT    DEFAULT (datetime('now', 'localtime')),
                    updated_at  TEXT    DEFAULT (datetime('now', 'localtime'))
                );
                CREATE TABLE IF NOT EXISTS payments (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    debt_id  INTEGER NOT NULL REFERENCES debts(id),
                    amount   REAL    NOT NULL,
                    paid_at  TEXT    DEFAULT (datetime('now', 'localtime')),
                    note     TEXT    DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS undo_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id     INTEGER NOT NULL,
                    action_type TEXT    NOT NULL,
                    data_json   TEXT    NOT NULL,
                    created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
                );
                CREATE TABLE IF NOT EXISTS chat_settings (
                    chat_id INTEGER NOT NULL,
                    key     TEXT    NOT NULL,
                    value   TEXT    NOT NULL,
                    PRIMARY KEY (chat_id, key)
                );
                CREATE INDEX IF NOT EXISTS idx_debts_chat   ON debts(chat_id);
                CREATE INDEX IF NOT EXISTS idx_debts_active ON debts(is_active);
                CREATE TABLE IF NOT EXISTS audit_log (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id     INTEGER NOT NULL,
                    user_id     INTEGER DEFAULT 0,
                    action      TEXT    NOT NULL,
                    detail_json TEXT    DEFAULT '{}',
                    created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
                );
                CREATE INDEX IF NOT EXISTS idx_audit_chat ON audit_log(chat_id);
            """)
            for col, defn in [
                ('due_date', 'TEXT DEFAULT NULL'),
                ('category', "TEXT DEFAULT ''"),
                ('currency', "TEXT DEFAULT 'UZS'"),
            ]:
                try:
                    conn.execute(f"ALTER TABLE debts ADD COLUMN {col} {defn}")
                except Exception:
                    pass

    # ─── Undo yordamchi ───────────────────────────────────────────────────────
    def _push_undo(self, conn, chat_id, action_type, data: dict):
        conn.execute(
            "INSERT INTO undo_log (chat_id, action_type, data_json) VALUES (?,?,?)",
            (chat_id, action_type, json.dumps(data, ensure_ascii=False))
        )
        conn.execute(
            """DELETE FROM undo_log WHERE chat_id=? AND id NOT IN
               (SELECT id FROM undo_log WHERE chat_id=? ORDER BY id DESC LIMIT 20)""",
            (chat_id, chat_id)
        )

    def pop_undo(self, chat_id):
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM undo_log WHERE chat_id=? ORDER BY id DESC LIMIT 1",
                (chat_id,)
            ).fetchone()
            if not row:
                return None
            entry = {'action_type': row['action_type'],
                     'data': json.loads(row['data_json']),
                     'created_at': row['created_at']}
            data = entry['data']
            at   = entry['action_type']
            if at == 'ADD_DEBT':
                conn.execute("UPDATE debts SET is_active=0 WHERE id=? AND chat_id=?",
                             (data['debt_id'], chat_id))
            elif at == 'PAYMENT':
                conn.execute("DELETE FROM payments WHERE id=?", (data['payment_id'],))
                conn.execute("UPDATE debts SET remaining=? WHERE id=?",
                             (data['prev_remaining'], data['debt_id']))
            elif at == 'UPDATE_DEBT':
                conn.execute("UPDATE debts SET remaining=?, amount=amount-? WHERE id=?",
                             (data['prev_remaining'], data['added_amount'], data['debt_id']))
            elif at == 'DELETE_DEBT':
                conn.execute("UPDATE debts SET is_active=1 WHERE id=? AND chat_id=?",
                             (data['debt_id'], chat_id))
            conn.execute("DELETE FROM undo_log WHERE chat_id=? AND id=(SELECT MAX(id) FROM undo_log WHERE chat_id=?)",
                         (chat_id, chat_id))
            return entry

    # ─── Audit ────────────────────────────────────────────────────────────────
    def log_audit(self, chat_id, user_id, action: str, detail: dict | None = None):
        detail = detail or {}
        with self.get_conn() as conn:
            conn.execute(
                "INSERT INTO audit_log (chat_id, user_id, action, detail_json) VALUES (?,?,?,?)",
                (chat_id, int(user_id or 0), action, json.dumps(detail, ensure_ascii=False)),
            )
            conn.execute(
                """DELETE FROM audit_log WHERE chat_id=? AND id NOT IN
                   (SELECT id FROM audit_log WHERE chat_id=? ORDER BY id DESC LIMIT 200)""",
                (chat_id, chat_id),
            )

    def get_audit(self, chat_id, limit=20):
        limit = max(1, min(100, int(limit)))
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM audit_log WHERE chat_id=? ORDER BY id DESC LIMIT ?",
                (chat_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def _early_benefit(self, chat_id, amount: float, due_date, remaining: float) -> tuple[float, str]:
        """(qarzdan yechiladigan 'effektiv' summa, to'lov izohi qismi)"""
        if amount <= 0 or remaining <= 0:
            return 0.0, ''
        amt = float(amount)
        rem = float(remaining)
        if not due_date:
            return min(amt, rem), ''
        today = datetime.now().strftime('%Y-%m-%d')
        if today >= str(due_date)[:10]:
            return min(amt, rem), ''
        try:
            pct = float(self.get_setting(chat_id, 'early_bonus_pct', '0') or 0)
        except (TypeError, ValueError):
            pct = 0.0
        if pct <= 0:
            return min(amt, rem), ''
        raw = amt * (1 + pct / 100.0)
        ben = min(rem, raw)
        return ben, f'early_bonus_{pct:g}%'

    # ─── Asosiy tranzaksiya ───────────────────────────────────────────────────
    def process_transaction(self, chat_id, debtor_name, amount,
                            is_repayment=False, note='', added_by='',
                            message_id=0, due_date=None, category='', currency='UZS',
                            user_id=None):
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT id, remaining FROM debts WHERE chat_id=? AND LOWER(name)=LOWER(?) AND is_active=1",
                (chat_id, debtor_name)
            ).fetchone()
            if row:
                debt_id = row['id']
                cur_rem = row['remaining']
                if is_repayment:
                    debt_full = conn.execute(
                        "SELECT due_date FROM debts WHERE id=?", (debt_id,)
                    ).fetchone()
                    due_d = debt_full['due_date'] if debt_full else None
                    benefit, pay_note = self._early_benefit(chat_id, amount, due_d, cur_rem)
                    pay_note = (note + ' ' + pay_note).strip() if pay_note else note
                    new_rem = max(0.0, cur_rem - benefit)
                    cur = conn.execute(
                        "INSERT INTO payments (debt_id,amount,note) VALUES (?,?,?)",
                        (debt_id, amount, pay_note),
                    )
                    conn.execute("UPDATE debts SET remaining=?, updated_at=datetime('now','localtime') WHERE id=?",
                                 (new_rem, debt_id))
                    self._push_undo(conn, chat_id, 'PAYMENT', {
                        'debt_id': debt_id, 'payment_id': cur.lastrowid,
                        'amount': amount, 'prev_remaining': cur_rem, 'name': debtor_name
                    })
                    conn.execute(
                        "INSERT INTO audit_log (chat_id, user_id, action, detail_json) VALUES (?,?,?,?)",
                        (chat_id, int(user_id or 0), 'PAYMENT',
                         json.dumps({'debt_id': debt_id, 'name': debtor_name, 'cash': amount,
                                     'benefit': benefit, 'new_remaining': new_rem}, ensure_ascii=False)),
                    )
                    meta_pay = {'repayment': True, 'benefit': benefit, 'cash': float(amount)}
                else:
                    new_rem = cur_rem + amount
                    conn.execute("UPDATE debts SET remaining=?, amount=amount+?, updated_at=datetime('now','localtime') WHERE id=?",
                                 (new_rem, amount, debt_id))
                    self._push_undo(conn, chat_id, 'UPDATE_DEBT', {
                        'debt_id': debt_id, 'added_amount': amount,
                        'prev_remaining': cur_rem, 'name': debtor_name
                    })
                    conn.execute(
                        "INSERT INTO audit_log (chat_id, user_id, action, detail_json) VALUES (?,?,?,?)",
                        (chat_id, int(user_id or 0), 'ADD_TO_DEBT',
                         json.dumps({'debt_id': debt_id, 'name': debtor_name, 'amount': amount,
                                     'new_remaining': new_rem}, ensure_ascii=False)),
                    )
                    meta_pay = {'repayment': False}
                return debt_id, new_rem, True, meta_pay
            else:
                if not is_repayment:
                    cur = conn.execute(
                        """INSERT INTO debts (chat_id,name,amount,remaining,note,added_by,
                           message_id,due_date,category,currency) VALUES (?,?,?,?,?,?,?,?,?,?)""",
                        (chat_id, debtor_name, amount, amount, note, added_by,
                         message_id, due_date, category, currency)
                    )
                    debt_id = cur.lastrowid
                    self._push_undo(conn, chat_id, 'ADD_DEBT', {
                        'debt_id': debt_id, 'name': debtor_name,
                        'amount': amount, 'currency': currency
                    })
                    conn.execute(
                        "INSERT INTO audit_log (chat_id, user_id, action, detail_json) VALUES (?,?,?,?)",
                        (chat_id, int(user_id or 0), 'NEW_DEBT',
                         json.dumps({'debt_id': debt_id, 'name': debtor_name, 'amount': amount,
                                     'currency': currency, 'message_id': message_id}, ensure_ascii=False)),
                    )
                    return debt_id, amount, False, None
                return None, 0, False, None

    # ─── So'rovlar ────────────────────────────────────────────────────────────
    def get_active_debts(self, chat_id, category=None, currency=None):
        sql = ("SELECT id,name,amount,remaining,note,added_by,category,"
               "currency,due_date,created_at FROM debts "
               "WHERE chat_id=? AND is_active=1 AND remaining>0")
        params = [chat_id]
        if category:
            sql += " AND category=?"; params.append(category)
        if currency:
            sql += " AND currency=?"; params.append(currency)
        sql += " ORDER BY remaining DESC"
        with self.get_conn() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def get_all_debts(self, chat_id):
        with self.get_conn() as conn:
            rows = conn.execute(
                """SELECT d.*, COALESCE(SUM(p.amount),0) as paid_total
                   FROM debts d LEFT JOIN payments p ON p.debt_id=d.id
                   WHERE d.chat_id=? GROUP BY d.id ORDER BY d.created_at DESC""",
                (chat_id,)
            ).fetchall()
            result = []
            for r in rows:
                d = dict(r)
                d['paid']   = d['paid_total']
                d['status'] = "To'langan" if (not d['is_active'] or d['remaining']==0) else "Faol"
                result.append(d)
            return result

    def get_debt_by_id(self, debt_id, chat_id):
        with self.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM debts WHERE id=? AND chat_id=? AND is_active=1",
                (debt_id, chat_id)
            ).fetchone()
            return dict(row) if row else None

    def get_overdue_debts(self, chat_id):
        today = datetime.now().strftime('%Y-%m-%d')
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM debts WHERE chat_id=? AND is_active=1 AND remaining>0 AND due_date IS NOT NULL AND due_date < ?",
                (chat_id, today)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_top_debtors(self, chat_id, limit=5):
        with self.get_conn() as conn:
            rows = conn.execute(
                "SELECT name,remaining,currency,due_date FROM debts WHERE chat_id=? AND is_active=1 AND remaining>0 ORDER BY remaining DESC LIMIT ?",
                (chat_id, limit)
            ).fetchall()
            return [dict(r) for r in rows]

    def get_payment_history(self, debt_id, chat_id):
        with self.get_conn() as conn:
            debt = conn.execute("SELECT * FROM debts WHERE id=? AND chat_id=?",
                                (debt_id, chat_id)).fetchone()
            if not debt:
                return None, []
            pays = conn.execute("SELECT * FROM payments WHERE debt_id=? ORDER BY paid_at DESC",
                                (debt_id,)).fetchall()
            return dict(debt), [dict(p) for p in pays]

    def get_monthly_chart_data(self, chat_id, months=6):
        with self.get_conn() as conn:
            added = conn.execute(
                "SELECT strftime('%Y-%m',created_at) as m, COUNT(*) as cnt, SUM(amount) as total FROM debts WHERE chat_id=? GROUP BY m ORDER BY m DESC LIMIT ?",
                (chat_id, months)
            ).fetchall()
            paid = conn.execute(
                "SELECT strftime('%Y-%m',p.paid_at) as m, SUM(p.amount) as total FROM payments p JOIN debts d ON d.id=p.debt_id WHERE d.chat_id=? GROUP BY m ORDER BY m DESC LIMIT ?",
                (chat_id, months)
            ).fetchall()
            return [dict(r) for r in reversed(added)], [dict(r) for r in reversed(paid)]

    def get_categories(self, chat_id):
        with self.get_conn() as conn:
            rows = conn.execute(
                """SELECT category, currency, COUNT(*) as cnt, SUM(remaining) as total
                   FROM debts WHERE chat_id=? AND is_active=1 AND remaining>0 AND category!=''
                   GROUP BY category, currency ORDER BY total DESC""",
                (chat_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_debt(self, debt_id, chat_id):
        with self.get_conn() as conn:
            debt = conn.execute("SELECT * FROM debts WHERE id=? AND chat_id=?",
                                (debt_id, chat_id)).fetchone()
            if debt:
                self._push_undo(conn, chat_id, 'DELETE_DEBT', {
                    'debt_id': debt_id, 'name': debt['name'],
                    'amount': debt['amount'], 'remaining': debt['remaining']
                })
                conn.execute(
                    "INSERT INTO audit_log (chat_id, user_id, action, detail_json) VALUES (?,?,?,?)",
                    (chat_id, 0, 'DELETE_DEBT',
                     json.dumps({'debt_id': debt_id, 'name': debt['name']}, ensure_ascii=False)),
                )
            conn.execute("UPDATE debts SET is_active=0, updated_at=datetime('now','localtime') WHERE id=? AND chat_id=?",
                         (debt_id, chat_id))

    def bulk_import(self, chat_id, rows: list, added_by='import'):
        imported = 0
        with self.get_conn() as conn:
            for r in rows:
                try:
                    name   = str(r.get('name','')).strip()
                    amount = float(str(r.get('amount',0)).replace(',','').replace(' ',''))
                    if not name or amount <= 0:
                        continue
                    conn.execute(
                        "INSERT INTO debts (chat_id,name,amount,remaining,note,added_by,currency,category) VALUES (?,?,?,?,?,?,?,?)",
                        (chat_id, name, amount, amount,
                         str(r.get('note','')),  added_by,
                         str(r.get('currency','UZS')).upper(),
                         str(r.get('category','')))
                    )
                    imported += 1
                except Exception:
                    continue
        if imported:
            self.log_audit(chat_id, 0, 'BULK_IMPORT', {'count': imported, 'by': added_by})
        return imported

    def get_setting(self, chat_id, key, default=None):
        with self.get_conn() as conn:
            row = conn.execute("SELECT value FROM chat_settings WHERE chat_id=? AND key=?",
                               (chat_id, key)).fetchone()
            return row['value'] if row else default

    def set_setting(self, chat_id, key, value):
        with self.get_conn() as conn:
            conn.execute("INSERT OR REPLACE INTO chat_settings (chat_id,key,value) VALUES (?,?,?)",
                         (chat_id, key, str(value)))

    def get_all_chat_ids(self):
        with self.get_conn() as conn:
            rows = conn.execute("SELECT DISTINCT chat_id FROM debts WHERE is_active=1 AND remaining>0").fetchall()
            return [r['chat_id'] for r in rows]

    def get_monthly_stats(self, chat_id, year, month):
        with self.get_conn() as conn:
            a = conn.execute(
                "SELECT COUNT(*) as cnt, COALESCE(SUM(amount),0) as total FROM debts WHERE chat_id=? AND strftime('%Y',created_at)=? AND strftime('%m',created_at)=?",
                (chat_id, str(year), f"{month:02d}")
            ).fetchone()
            p = conn.execute(
                "SELECT COALESCE(SUM(p.amount),0) as total FROM payments p JOIN debts d ON d.id=p.debt_id WHERE d.chat_id=? AND strftime('%Y',p.paid_at)=? AND strftime('%m',p.paid_at)=?",
                (chat_id, str(year), f"{month:02d}")
            ).fetchone()
            return {'added_count': a['cnt'], 'added_total': a['total'], 'paid_total': p['total']}

    def add_payment(self, debt_id, chat_id, amount, user_id=None):
        """To'lov qo'shish (alohida usul). Muddatdan oldin — early_bonus_pct."""
        with self.get_conn() as conn:
            debt = conn.execute(
                "SELECT * FROM debts WHERE id=? AND chat_id=? AND is_active=1",
                (debt_id, chat_id)
            ).fetchone()
            if not debt:
                return {'success': False, 'error': f"#{debt_id} topilmadi"}
            if amount > debt['remaining']:
                curc = debt.get('currency') or 'UZS'
                return {'success': False, 'error': f"Summa katta! Qolgan: {debt['remaining']:,.0f} {curc}"}
            benefit, pay_note = self._early_benefit(
                chat_id, amount, debt.get('due_date'), debt['remaining']
            )
            new_rem = max(0.0, float(debt['remaining']) - benefit)
            cur = conn.execute(
                "INSERT INTO payments (debt_id, amount, note) VALUES (?,?,?)",
                (debt_id, amount, pay_note or ''),
            )
            conn.execute(
                "UPDATE debts SET remaining=?, updated_at=datetime('now','localtime') WHERE id=?",
                (new_rem, debt_id)
            )
            self._push_undo(conn, chat_id, 'PAYMENT', {
                'debt_id': debt_id, 'payment_id': cur.lastrowid,
                'amount': amount, 'prev_remaining': debt['remaining'],
                'name': debt['name']
            })
            conn.execute(
                "INSERT INTO audit_log (chat_id, user_id, action, detail_json) VALUES (?,?,?,?)",
                (chat_id, int(user_id or 0), 'PAYMENT_UI',
                 json.dumps({'debt_id': debt_id, 'name': debt['name'], 'cash': amount,
                             'benefit': benefit, 'new_remaining': new_rem}, ensure_ascii=False)),
            )
            cur_code = debt.get('currency') or 'UZS'
            return {
                'success': True,
                'name': debt['name'],
                'remaining': new_rem,
                'currency': cur_code,
                'benefit': benefit,
                'bonus_applied': bool(pay_note),
            }
