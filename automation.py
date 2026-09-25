import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path


DB_PATH = Path(__file__).parent / "jobs.db"


def get_follow_ups(days=7):
    """Find companies contacted at least `days` ago that have not answered."""

    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute("""
        SELECT
            id,
            company,
            website,
            date_applied_raw,
            status,
            notes
        FROM jobs
        WHERE date_applied_raw IS NOT NULL
          AND date_applied_raw != ''
          AND status != 'Answered'
    """).fetchall()

    conn.close()

    follow_ups = []

    for row in rows:
        job_id, company, website, date_applied, status, notes = row

        # Try to understand the date from your existing data.
        parsed_date = None

        for fmt in ("%d.%m.%Y", "%d.%m", "%Y-%m-%d"):
            try:
                parsed_date = datetime.strptime(
                    date_applied,
                    fmt
                ).date()

                # Your original data sometimes has dates without a year.
                if fmt == "%d.%m":
                    parsed_date = parsed_date.replace(
                        year=date.today().year
                    )

                break

            except ValueError:
                pass

        if parsed_date is None:
            continue

        days_since_contact = (date.today() - parsed_date).days

        if days_since_contact >= days:
            follow_ups.append({
                "id": job_id,
                "company": company,
                "website": website,
                "date_applied": date_applied,
                "days_since_contact": days_since_contact,
                "status": status,
                "notes": notes,
            })

    return follow_ups


def main():
    print("\nJOB TRACKER AUTOMATION")
    print("=" * 30)

    follow_ups = get_follow_ups(days=7)

    if not follow_ups:
        print("\nNo follow-ups are currently due.")
        return

    print(f"\n{len(follow_ups)} follow-up(s) due:\n")

    for job in follow_ups:
        print(
            f"• {job['company']} "
            f"— contacted {job['days_since_contact']} days ago"
        )


if __name__ == "__main__":
    main()

