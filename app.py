import sqlite3
from pathlib import Path
from datetime import date, datetime

import pandas as pd
import streamlit as st


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

DB_PATH = Path(__file__).parent / "jobs.db"

st.set_page_config(
    page_title="Job Tracker",
    page_icon="💼",
    layout="wide"
)


STATUSES = [
    "Not contacted",
    "Contacted / applied",
    "Answered",
    "Rejected",
    "Interview",
    "Offer",
    "No open position",
]


# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

def get_connection():
    return sqlite3.connect(DB_PATH)


def get_jobs(search=""):
    conn = get_connection()

    if search:
        search_pattern = f"%{search}%"

        rows = conn.execute(
            """
            SELECT
                id,
                company,
                website,
                job,
                status,
                date_applied_raw,
                date_answer_raw,
                notes
            FROM jobs
            WHERE company LIKE ?
               OR website LIKE ?
               OR job LIKE ?
               OR status LIKE ?
               OR notes LIKE ?
            ORDER BY company COLLATE NOCASE
            """,
            (
                search_pattern,
                search_pattern,
                search_pattern,
                search_pattern,
                search_pattern,
            ),
        ).fetchall()

    else:
        rows = conn.execute(
            """
            SELECT
                id,
                company,
                website,
                job,
                status,
                date_applied_raw,
                date_answer_raw,
                notes
            FROM jobs
            ORDER BY company COLLATE NOCASE
            """
        ).fetchall()

    conn.close()

    columns = [
        "id",
        "company",
        "website",
        "job",
        "status",
        "date_applied",
        "date_answer",
        "notes",
    ]

    return pd.DataFrame(rows, columns=columns)


def get_job(job_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT
            id,
            company,
            website,
            job,
            status,
            applied_raw,
            sent_raw,
            linkedin_follow_raw,
            date_applied_raw,
            date_answer_raw,
            notes,
            needs_review
        FROM jobs
        WHERE id = ?
        """,
        (job_id,),
    ).fetchone()

    conn.close()

    return row


def update_job(job_id, data):
    conn = get_connection()

    conn.execute(
        """
        UPDATE jobs
        SET
            company = ?,
            website = ?,
            job = ?,
            status = ?,
            applied_raw = ?,
            sent_raw = ?,
            linkedin_follow_raw = ?,
            date_applied_raw = ?,
            date_answer_raw = ?,
            notes = ?
        WHERE id = ?
        """,
        (
            data["company"],
            data["website"],
            data["job"],
            data["status"],
            data["applied_raw"],
            data["sent_raw"],
            data["linkedin_follow_raw"],
            data["date_applied_raw"],
            data["date_answer_raw"],
            data["notes"],
            job_id,
        ),
    )

    conn.commit()
    conn.close()


def add_job(data):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO jobs (
            company,
            website,
            job,
            status,
            applied_raw,
            sent_raw,
            linkedin_follow_raw,
            date_applied_raw,
            date_answer_raw,
            notes,
            needs_review
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (
            data["company"],
            data["website"],
            data["job"],
            data["status"],
            data["applied_raw"],
            data["sent_raw"],
            data["linkedin_follow_raw"],
            data["date_applied_raw"],
            data["date_answer_raw"],
            data["notes"],
        ),
    )

    conn.commit()
    conn.close()


def delete_job(job_id):
    conn = get_connection()

    conn.execute(
        "DELETE FROM jobs WHERE id = ?",
        (job_id,),
    )

    conn.commit()
    conn.close()


# ---------------------------------------------------------
# FOLLOW-UP AUTOMATION
# ---------------------------------------------------------

def get_follow_ups(days=7):
    """
    Find companies contacted at least `days` ago
    that have not received an answer.
    """

    conn = get_connection()

    rows = conn.execute(
        """
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
        """
    ).fetchall()

    conn.close()

    follow_ups = []

    for row in rows:
        (
            job_id,
            company,
            website,
            date_applied,
            status,
            notes,
        ) = row

        parsed_date = None

        # Try different date formats
        for fmt in (
            "%d.%m.%Y",
            "%d.%m",
            "%Y-%m-%d",
        ):
            try:
                parsed_date = datetime.strptime(
                    date_applied.strip(),
                    fmt
                ).date()

                # If the date has no year,
                # assume the current year.
                if fmt == "%d.%m":
                    parsed_date = parsed_date.replace(
                        year=date.today().year
                    )

                break

            except ValueError:
                pass

        # Skip dates we cannot understand
        if parsed_date is None:
            continue

        days_since_contact = (
            date.today() - parsed_date
        ).days

        if days_since_contact >= days:
            follow_ups.append(
                {
                    "id": job_id,
                    "company": company,
                    "website": website,
                    "date_applied": date_applied,
                    "days_since_contact": days_since_contact,
                    "status": status,
                    "notes": notes,
                }
            )

    return follow_ups


# ---------------------------------------------------------
# CHECK DATABASE
# ---------------------------------------------------------

st.title("💼 Job Tracker")
st.caption("Python + SQLite + Streamlit")


if not DB_PATH.exists():
    st.error(
        f"Database not found: {DB_PATH}"
    )
    st.stop()


# ---------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------

with st.sidebar:

    st.header("🔎 Search")

    search = st.text_input(
        "Search companies",
        placeholder="Company, job, website..."
    )

    st.divider()

    st.header("📊 Filter")

    status_filter = st.selectbox(
        "Status",
        ["All"] + STATUSES
    )


# ---------------------------------------------------------
# ADD COMPANY
# ---------------------------------------------------------

with st.expander("➕ Add a new company"):

    with st.form("add_company_form"):

        company = st.text_input(
            "Company *"
        )

        website = st.text_input(
            "Website"
        )

        job = st.text_input(
            "Job / position"
        )

        status = st.selectbox(
            "Status",
            STATUSES
        )

        applied_raw = st.text_input(
            "Applied?"
        )

        sent_raw = st.text_input(
            "Sent?"
        )

        linkedin_follow_raw = st.text_input(
            "LinkedIn follow?"
        )

        date_applied_raw = st.text_input(
            "Date contacted / applied",
            placeholder="e.g. 24.09.2026"
        )

        date_answer_raw = st.text_input(
            "Date answered",
            placeholder="e.g. 30.09.2026"
        )

        notes = st.text_area(
            "Notes"
        )

        submitted = st.form_submit_button(
            "Add company"
        )

        if submitted:

            if not company.strip():

                st.error(
                    "Company name is required."
                )

            else:

                add_job(
                    {
                        "company": company.strip(),
                        "website": website.strip(),
                        "job": job.strip(),
                        "status": status,
                        "applied_raw": applied_raw.strip(),
                        "sent_raw": sent_raw.strip(),
                        "linkedin_follow_raw": linkedin_follow_raw.strip(),
                        "date_applied_raw": date_applied_raw.strip(),
                        "date_answer_raw": date_answer_raw.strip(),
                        "notes": notes.strip(),
                    }
                )

                st.success(
                    f"{company} added!"
                )

                st.rerun()


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

df = get_jobs(search)


# ---------------------------------------------------------
# STATUS FILTER
# ---------------------------------------------------------

if status_filter != "All":

    df = df[
        df["status"] == status_filter
    ]


# ---------------------------------------------------------
# DASHBOARD METRICS
# ---------------------------------------------------------

st.subheader("📊 Dashboard")

total_companies = len(df)

contacted = len(
    df[
        df["status"] == "Contacted / applied"
    ]
)

answered = len(
    df[
        df["status"] == "Answered"
    ]
)

interviews = len(
    df[
        df["status"] == "Interview"
    ]
)

offers = len(
    df[
        df["status"] == "Offer"
    ]
)


c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Companies",
    total_companies
)

c2.metric(
    "Contacted",
    contacted
)

c3.metric(
    "Answered",
    answered
)

c4.metric(
    "Interviews",
    interviews
)

c5.metric(
    "Offers",
    offers
)


# ---------------------------------------------------------
# FOLLOW-UPS
# ---------------------------------------------------------

st.divider()

st.subheader("🔔 Follow-ups due")

follow_ups = get_follow_ups(
    days=7
)


if not follow_ups:

    st.success(
        "No follow-ups are currently due. 🎉"
    )

else:

    st.warning(
        f"{len(follow_ups)} companies may need a follow-up."
    )

    follow_up_df = pd.DataFrame(
        follow_ups
    )

    follow_up_df = follow_up_df[
        [
            "company",
            "website",
            "date_applied",
            "days_since_contact",
            "status",
            "notes",
        ]
    ]

    follow_up_df = follow_up_df.rename(
        columns={
            "company": "Company",
            "website": "Website",
            "date_applied": "Date contacted",
            "days_since_contact": "Days since contact",
            "status": "Status",
            "notes": "Notes",
        }
    )

    st.dataframe(
        follow_up_df,
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------
# EDIT COMPANY
# ---------------------------------------------------------

st.divider()

st.subheader("✏️ Edit company")

if len(df) == 0:

    st.info(
        "No companies match your search."
    )

else:

    company_options = {
        f"{row.company} — ID {row.id}": row.id
        for row in df.itertuples()
    }

    selected_company = st.selectbox(
        "Select a company",
        list(company_options.keys())
    )

    selected_id = company_options[
        selected_company
    ]

    job = get_job(selected_id)

    if job:

        (
            job_id,
            company,
            website,
            job_title,
            status,
            applied_raw,
            sent_raw,
            linkedin_follow_raw,
            date_applied_raw,
            date_answer_raw,
            notes,
            needs_review,
        ) = job

        with st.form("edit_company_form"):

            new_company = st.text_input(
                "Company",
                value=company or ""
            )

            new_website = st.text_input(
                "Website",
                value=website or ""
            )

            new_job = st.text_input(
                "Job / position",
                value=job_title or ""
            )

            current_status_index = (
                STATUSES.index(status)
                if status in STATUSES
                else 0
            )

            new_status = st.selectbox(
                "Status",
                STATUSES,
                index=current_status_index
            )

            new_applied_raw = st.text_input(
                "Applied?",
                value=applied_raw or ""
            )

            new_sent_raw = st.text_input(
                "Sent?",
                value=sent_raw or ""
            )

            new_linkedin_follow_raw = st.text_input(
                "LinkedIn follow?",
                value=linkedin_follow_raw or ""
            )

            new_date_applied_raw = st.text_input(
                "Date contacted / applied",
                value=date_applied_raw or ""
            )

            new_date_answer_raw = st.text_input(
                "Date answered",
                value=date_answer_raw or ""
            )

            new_notes = st.text_area(
                "Notes",
                value=notes or ""
            )

            save = st.form_submit_button(
                "💾 Save changes"
            )

            if save:

                update_job(
                    selected_id,
                    {
                        "company": new_company.strip(),
                        "website": new_website.strip(),
                        "job": new_job.strip(),
                        "status": new_status,
                        "applied_raw": new_applied_raw.strip(),
                        "sent_raw": new_sent_raw.strip(),
                        "linkedin_follow_raw": new_linkedin_follow_raw.strip(),
                        "date_applied_raw": new_date_applied_raw.strip(),
                        "date_answer_raw": new_date_answer_raw.strip(),
                        "notes": new_notes.strip(),
                    }
                )

                st.success(
                    "Company updated!"
                )

                st.rerun()


# ---------------------------------------------------------
# DELETE COMPANY
# ---------------------------------------------------------

st.divider()

st.subheader("🗑️ Delete company")

if len(df) > 0:

    delete_options = {
        f"{row.company} — ID {row.id}": row.id
        for row in df.itertuples()
    }

    delete_company = st.selectbox(
        "Select company to delete",
        list(delete_options.keys()),
        key="delete_company"
    )

    delete_id = delete_options[
        delete_company
    ]

    confirm_delete = st.checkbox(
        "I understand that this cannot be undone."
    )

    if st.button(
        "🗑️ Delete selected company",
        disabled=not confirm_delete
    ):

        delete_job(delete_id)

        st.success(
            "Company deleted."
        )

        st.rerun()


# ---------------------------------------------------------
# COMPANY TABLE
# ---------------------------------------------------------

st.divider()

st.subheader("🏢 Companies")

if df.empty:

    st.info(
        "No companies found."
    )

else:

    display_df = df.copy()

    display_df = display_df.rename(
        columns={
            "company": "Company",
            "website": "Website",
            "job": "Job",
            "status": "Status",
            "date_applied": "Date contacted",
            "date_answer": "Date answered",
            "notes": "Notes",
        }
    )

    display_df = display_df[
        [
            "Company",
            "Website",
            "Job",
            "Status",
            "Date contacted",
            "Date answered",
            "Notes",
        ]
    ]

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
    )


# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    f"Database: {DB_PATH}"
)