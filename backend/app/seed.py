"""Creates demo data. Run: python -m app.seed

All passwords are: pulse123
This DROPS ALL TABLES first, so it only runs when APP_ENV is dev or test.

The data is shaped to exercise the minimum group size rule (5):
- Northwind Sales (5 respondents) and Support (6) are shown on their own.
- Northwind Engineering (3) + HR (2) are pooled into "Other teams" (5).
- Bluepeak has only 2 respondents, so its dashboard shows no scores at all.
"""
from .config import IS_DEV, APP_ENV
from .db import Base, engine, SessionLocal
from . import models
from .auth import hash_password
from .services.questions import questions_for

# Open answers as if already scored by the AI: text, score, reason, flags
OPEN = {
    "review": ("I use ChatGPT to draft customer follow-up emails, then edit each one and check any numbers before sending.",
               4, "Regular use with careful review of outputs.", []),
    "paste": ("Pasted a customer's complaint thread into ChatGPT to summarise it before escalating.",
              3, "Useful summary, but customer details went into a public tool.", ["customer_data_shared"]),
    "unchecked": ("Asked AI to write the weekly status report and sent it straight to my manager.",
                  2, "Output was used without being checked.", ["unreviewed_output"]),
    "workflow": ("Built a shared prompt library for ticket triage; the team reviews a sample of outputs every week.",
                 5, "Advanced, reviewed workflow adopted by the team.", []),
    "none": ("I haven't really used AI at work yet.", 1, "No AI use described.", []),
    "code": ("Used Copilot to write unit tests for a refactor and reviewed each test before merging.",
             4, "Thoughtful use with review.", []),
    "pricing": ("Uploaded our pricing spreadsheet to an AI tool to find discount patterns.",
                3, "Good idea, but confidential pricing data was shared.", ["confidential_data_shared"]),
    "boundaries": ("I'd let AI help draft job descriptions, but never make final hiring decisions; those need human judgement.",
                   4, "Clear, thoughtful boundaries on AI use.", []),
}

# Answer profile: option index (0-4) for frequency, policy, data handling, output review,
# role-specific questions; then the open answer key. None = hasn't taken the diagnostic.
# name, email, department, role, job_role, seniority, profile
PEOPLE_NORTHWIND = [
    ("Asha Rao", "asha@northwind.test", None, "admin", "manager", "lead", None),
    ("Vikram Shah", "vikram@northwind.test", "Sales", "employee", "sales", "senior", (3, 3, 3, 3, 3, "review")),
    ("Neha Gupta", "neha@northwind.test", "Sales", "employee", "sales", "junior", (2, 3, 1, 1, 2, "paste")),
    ("Rohan Mehta", "rohan@northwind.test", "Sales", "employee", "sales", "mid", (3, 2, 2, 2, 3, "unchecked")),
    ("Ananya Bose", "ananya@northwind.test", "Sales", "employee", "sales", "mid", (4, 4, 4, 4, 4, "workflow")),
    ("Karan Joshi", "karan@northwind.test", "Sales", "employee", "sales", "junior", (0, 0, 1, 1, 0, "none")),
    ("Farah Ali", "farah@northwind.test", "Sales", "employee", "sales", "senior", None),
    ("Priya Nair", "priya@northwind.test", "Support", "employee", "support", "junior", (1, 1, 2, 2, 2, "paste")),
    ("Arjun Iyer", "arjun@northwind.test", "Support", "employee", "support", "senior", (3, 3, 3, 3, 3, "review")),
    ("Kavitha Menon", "kavitha@northwind.test", "Support", "employee", "support", "mid", (2, 3, 1, 2, 2, "paste")),
    ("Meghna Rao", "meghna@northwind.test", "Support", "employee", "support", "junior", (2, 2, 2, 1, 2, "unchecked")),
    ("Sunil Verma", "sunil@northwind.test", "Support", "employee", "support", "mid", (3, 4, 4, 3, 4, "workflow")),
    ("Tara Singh", "tara@northwind.test", "Support", "employee", "support", "senior", (3, 3, 3, 3, 3, "pricing")),
    ("Dev Malhotra", "dev@northwind.test", "Engineering", "employee", "engineering", "lead", (4, 4, 4, 4, 4, "code")),
    ("Sara Thomas", "sara@northwind.test", "Engineering", "employee", "engineering", "mid", (3, 3, 3, 3, 3, "code")),
    ("Omar Sheikh", "omar@northwind.test", "Engineering", "employee", "engineering", "junior", (2, 1, 1, 1, 2, "unchecked")),
    ("Imran Khan", "imran@northwind.test", "HR", "employee", "manager", "senior", (2, 3, 3, 3, 2, "review")),
]
PEOPLE_BLUEPEAK = [
    ("Meera Pillai", "meera@bluepeak.test", None, "admin", "manager", "lead", None),
    ("Tom Fernandes", "tom@bluepeak.test", "Stores", "employee", "sales", "mid", (2, 1, 2, 2, 2, "review")),
    ("Lina George", "lina@bluepeak.test", "Stores", "employee", "sales", "junior", None),
    ("Kabir Das", "kabir@bluepeak.test", "Customer Care", "employee", "support", "senior", (3, 3, 0, 2, 3, "pricing")),
]
# A consultant who works with both companies: employee at Northwind, admin at Bluepeak
RAVI_NORTHWIND = ("Ravi Kapoor", "ravi@consult.test", "HR", "employee", "manager", "senior", (3, 2, 2, 3, 2, "boundaries"))
RAVI_BLUEPEAK = ("Ravi Kapoor", "ravi@consult.test", None, "admin", "manager", "senior", None)

COMMON = ["common-freq", "common-policy", "common-data", "common-review"]


def answers_for(membership, profile):
    """Builds a full, valid diagnostic for one person from their profile."""
    *levels, open_key = profile
    common = dict(zip(COMMON, levels[:4]))
    rows = []
    for q in questions_for(membership.job_role, membership.seniority):
        if q["type"] == "mcq":
            option = q["options"][common.get(q["id"], levels[4])]
            rows.append(models.Response(membership_id=membership.id, question_id=q["id"],
                                        answer=option["text"], score=option["points"], flags=[]))
        else:
            key = open_key if q["id"] == "common-open" else "boundaries"
            text, score, reason, flags = OPEN[key]
            rows.append(models.Response(membership_id=membership.id, question_id=q["id"], answer=text,
                                        score=score, reason=reason, flags=flags,
                                        ai_status="scored", scored_by="seed"))
    return rows


def run():
    if not IS_DEV:
        raise SystemExit(f"Refusing to seed: APP_ENV={APP_ENV!r}. Seeding drops every table; set APP_ENV=dev.")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    def make_org(name, depts):
        org = models.Organization(name=name)
        db.add(org)
        db.flush()
        d = {}
        for dn in depts:
            dept = models.Department(org_id=org.id, name=dn)
            db.add(dept)
            db.flush()
            d[dn] = dept.id
        return org, d

    nw, nw_depts = make_org("Northwind Logistics", ["Sales", "Support", "Engineering", "HR"])
    bp, bp_depts = make_org("Bluepeak Retail", ["Stores", "Customer Care"])

    users = {}
    password_hash = hash_password("pulse123")  # one hash for all demo users keeps seeding fast

    def add_people(org, depts, people):
        for name, email, dept, role, job_role, seniority, profile in people:
            u = users.get(email)
            if not u:
                u = models.User(name=name, email=email, password_hash=password_hash)
                db.add(u)
                db.flush()
                users[email] = u
            m = models.Membership(
                user_id=u.id, org_id=org.id,
                department_id=depts.get(dept) if dept else None,
                role=role, job_role=job_role, seniority=seniority,
            )
            db.add(m)
            db.flush()
            if profile:
                db.add_all(answers_for(m, profile))

    add_people(nw, nw_depts, PEOPLE_NORTHWIND + [RAVI_NORTHWIND])
    add_people(bp, bp_depts, PEOPLE_BLUEPEAK + [RAVI_BLUEPEAK])

    db.commit()
    db.close()
    print("Seeded. Log in with any seeded email and password 'pulse123'.")


if __name__ == "__main__":
    run()
