#!/usr/bin/env python3
import os
import sys
import argparse
import logging
from datetime import date
from decimal import Decimal

from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text

from app import create_app
from app.extensions import db
from app.services import financial as fin

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"audit_{date.today().isoformat()}.log"),
    ],
)
log = logging.getLogger(__name__)

USURY_RATE_EA = Decimal(os.environ.get("USURY_RATE_EA", "0.2762"))


def run_diagnostics(session):
    queries = {
        "duplicate_payments": """
            SELECT payment_reference, loan_id, COUNT(*) AS cnt,
                   MIN(created_at) AS first_seen, MAX(created_at) AS last_seen
            FROM payments
            GROUP BY payment_reference, loan_id
            HAVING COUNT(*) > 1
            ORDER BY cnt DESC
        """,
        "unbalanced_entries": """
            SELECT id, loan_id, entry_type, debit_amount, credit_amount,
                   (debit_amount - credit_amount) AS imbalance
            FROM accounting_entries
            WHERE debit_amount <> credit_amount
        """,
        "loans_overdue_not_flagged": """
            SELECT l.id, l.capital_balance, l.status,
                   MIN(a.due_date) AS oldest_unpaid,
                   CURRENT_DATE - MIN(a.due_date) AS days_overdue
            FROM loans l
            JOIN amortization_schedule a ON a.loan_id = l.id
            WHERE l.status = 'AL_DIA'
              AND a.is_paid = FALSE
              AND a.due_date < CURRENT_DATE - INTERVAL '30 days'
            GROUP BY l.id, l.capital_balance, l.status
        """,
    }

    for name, q in queries.items():
        rows = session.execute(text(q)).fetchall()
        if rows:
            log.warning("[%s] %d issue(s) found", name, len(rows))
            for row in rows[:10]:
                log.warning("  %s", dict(row._mapping))
        else:
            log.info("[%s] clean", name)


def deduplicate_payments(session, dry_run: bool):
    dupes = session.execute(text("""
        SELECT payment_reference, loan_id
        FROM payments
        GROUP BY payment_reference, loan_id
        HAVING COUNT(*) > 1
    """)).fetchall()

    log.info("duplicate payment references: %d", len(dupes))

    for row in dupes:
        payments = session.execute(text("""
            SELECT id, applied_principal, applied_interest, created_at
            FROM payments
            WHERE payment_reference = :ref AND loan_id = :lid
            ORDER BY created_at ASC
        """), {"ref": row.payment_reference, "lid": row.loan_id}).fetchall()

        keep_id = payments[0].id
        for p in payments[1:]:
            log.warning("removing duplicate payment %s (keeping %s)", p.id, keep_id)
            if not dry_run:
                session.execute(text("DELETE FROM accounting_entries WHERE payment_id = :id"), {"id": p.id})
                session.execute(text("""
                    UPDATE loans
                    SET capital_balance = capital_balance + :principal,
                        accrued_interest = accrued_interest + :interest,
                        updated_at = NOW()
                    WHERE id = :lid
                """), {
                    "principal": p.applied_principal,
                    "interest": p.applied_interest,
                    "lid": row.loan_id,
                })
                session.execute(text("DELETE FROM payments WHERE id = :id"), {"id": p.id})

    if not dry_run:
        session.commit()


def fix_unbalanced_entries(session, dry_run: bool):
    rows = session.execute(text("""
        SELECT id, loan_id, payment_id, debit_amount
        FROM accounting_entries
        WHERE debit_amount <> credit_amount
    """)).fetchall()

    log.info("unbalanced entries: %d", len(rows))

    for row in rows:
        log.warning("fixing entry %s (debit=%s)", row.id, row.debit_amount)
        if not dry_run:
            session.execute(text(
                "UPDATE accounting_entries SET credit_amount = debit_amount WHERE id = :id"
            ), {"id": row.id})

    if not dry_run:
        session.commit()


def backfill_interest_accrual(session, from_date: date, to_date: date, dry_run: bool):
    active_loans = session.execute(text("""
        SELECT id, interest_rate, capital_balance
        FROM loans
        WHERE status IN ('AL_DIA', 'EN_MORA', 'REESTRUCTURADO')
          AND disbursement_date IS NOT NULL
    """)).fetchall()

    log.info("checking accruals for %d active loans", len(active_loans))
    created = 0

    for loan in active_loans:
        cursor = date(from_date.year, from_date.month, 1)
        end = date(to_date.year, to_date.month, 1)

        while cursor <= end:
            existing = session.execute(text("""
                SELECT id FROM accounting_entries
                WHERE loan_id = :lid
                  AND entry_type = 'CAUSACION_INTERESES'
                  AND DATE_TRUNC('month', entry_date) = DATE_TRUNC('month', :d::date)
            """), {"lid": loan.id, "d": cursor.isoformat()}).fetchone()

            if not existing:
                monthly_rate = fin.convert_rate_to_monthly(
                    Decimal(str(loan.interest_rate)), "EFECTIVA_ANUAL"
                )
                interest = (Decimal(str(loan.capital_balance or 0)) * monthly_rate).quantize(Decimal("0.01"))

                if interest > 0:
                    log.warning("missing accrual loan=%s month=%s amount=%s", loan.id, cursor, interest)
                    if not dry_run:
                        session.execute(text("""
                            INSERT INTO accounting_entries
                                (id, loan_id, entry_type, entry_date, puc_debit, puc_credit,
                                 debit_amount, credit_amount, description, created_at)
                            VALUES
                                (gen_random_uuid(), :lid, 'CAUSACION_INTERESES', :d,
                                 '270505', '411005', :amt, :amt, :desc, NOW())
                        """), {
                            "lid": loan.id,
                            "d": cursor.isoformat(),
                            "amt": float(interest),
                            "desc": f"backfill {cursor.strftime('%Y-%m')}",
                        })
                        session.execute(text("""
                            UPDATE loans SET accrued_interest = accrued_interest + :amt,
                                updated_at = NOW()
                            WHERE id = :lid
                        """), {"amt": float(interest), "lid": loan.id})
                        created += 1

            cursor = date(cursor.year + (cursor.month // 12), (cursor.month % 12) + 1, 1)

    if not dry_run:
        session.commit()
    log.info("accrual entries created: %d", created)


def update_delinquent_loans(session, dry_run: bool):
    overdue = session.execute(text("""
        SELECT l.id, l.capital_balance, l.interest_rate, MIN(a.due_date) AS oldest_due
        FROM loans l
        JOIN amortization_schedule a ON a.loan_id = l.id
        WHERE l.status = 'AL_DIA'
          AND a.is_paid = FALSE
          AND a.due_date < CURRENT_DATE - INTERVAL '30 days'
        GROUP BY l.id, l.capital_balance, l.interest_rate
    """)).fetchall()

    log.info("loans to flag as EN_MORA: %d", len(overdue))

    for loan in overdue:
        days_late = (date.today() - loan.oldest_due).days
        monthly_rate = fin.convert_rate_to_monthly(Decimal(str(loan.interest_rate)), "EFECTIVA_ANUAL")
        mora = fin.calculate_default_interest(
            Decimal(str(loan.capital_balance or 0)), monthly_rate, days_late, USURY_RATE_EA
        )
        log.warning("loan %s overdue %d days, mora=%s", loan.id, days_late, mora)

        if not dry_run:
            session.execute(text("""
                UPDATE loans SET status = 'EN_MORA', days_in_default = :days,
                    updated_at = NOW()
                WHERE id = :lid
            """), {"days": days_late, "lid": loan.id})

            if mora > 0:
                session.execute(text("""
                    INSERT INTO accounting_entries
                        (id, loan_id, entry_type, entry_date, puc_debit, puc_credit,
                         debit_amount, credit_amount, description, created_at)
                    VALUES
                        (gen_random_uuid(), :lid, 'MORA', :d,
                         '270505', '410520', :amt, :amt, :desc, NOW())
                """), {
                    "lid": loan.id,
                    "d": date.today().isoformat(),
                    "amt": float(mora),
                    "desc": f"default interest accrual – {days_late} days overdue",
                })

    if not dry_run:
        session.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--from-date", type=date.fromisoformat, default=date(2026, 1, 1))
    parser.add_argument("--to-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--diagnose-only", action="store_true")
    args = parser.parse_args()

    log.info("starting remediation dry_run=%s", args.dry_run)

    app = create_app(os.environ.get("FLASK_ENV", "development"))
    with app.app_context():
        session = db.session
        run_diagnostics(session)
        if args.diagnose_only:
            return
        deduplicate_payments(session, args.dry_run)
        fix_unbalanced_entries(session, args.dry_run)
        backfill_interest_accrual(session, args.from_date, args.to_date, args.dry_run)
        update_delinquent_loans(session, args.dry_run)

    log.info("done – see audit log for details")


if __name__ == "__main__":
    main()
