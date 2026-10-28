"""Creates demo data. Run: python -m app.seed

All passwords are: pulse123
This DROPS ALL TABLES first, so it only runs when APP_ENV is dev or test.
"""
from .config import IS_DEV, APP_ENV
from .db import Base, engine, SessionLocal
from . import models
from .auth import hash_password

PEOPLE_NORTHWIND = [
    # name, email, department, role, job_role, seniority
    ("Asha Rao", "asha@northwind.test", None, "admin", "manager", "lead"),
    ("Vikram Shah", "vikram@northwind.test", "Sales", "employee", "sales", "senior"),
    ("Neha Gupta", "neha@northwind.test", "Sales", "employee", "sales", "junior"),
    ("Rohan Mehta", "rohan@northwind.test", "Sales", "employee", "sales", "mid"),
    ("Priya Nair", "priya@northwind.test", "Support", "employee", "support", "junior"),
    ("Arjun Iyer", "arjun@northwind.test", "Support", "employee", "support", "senior"),
    ("Kavitha Menon", "kavitha@northwind.test", "Support", "employee", "support", "mid"),
    ("Dev Malhotra", "dev@northwind.test", "Engineering", "employee", "engineering", "lead"),
    ("Sara Thomas", "sara@northwind.test", "Engineering", "employee", "engineering", "mid"),
    ("Imran Khan", "imran@northwind.test", "HR", "employee", "manager", "senior"),
]
PEOPLE_BLUEPEAK = [
    ("Meera Pillai", "meera@bluepeak.test", None, "admin", "manager", "lead"),
    ("Tom Fernandes", "tom@bluepeak.test", "Stores", "employee", "sales", "mid"),
    ("Lina George", "lina@bluepeak.test", "Stores", "employee", "sales", "junior"),
    ("Kabir Das", "kabir@bluepeak.test", "Customer Care", "employee", "support", "senior"),
]


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

    def add_people(org, depts, people):
        for name, email, dept, role, job_role, seniority in people:
            u = users.get(email)
            if not u:
                u = models.User(name=name, email=email, password_hash=hash_password("pulse123"))
                db.add(u)
                db.flush()
                users[email] = u
            db.add(models.Membership(
                user_id=u.id, org_id=org.id,
                department_id=depts.get(dept) if dept else None,
                role=role, job_role=job_role, seniority=seniority,
            ))

    add_people(nw, nw_depts, PEOPLE_NORTHWIND)
    add_people(bp, bp_depts, PEOPLE_BLUEPEAK)

    # A consultant who works with both companies
    add_people(nw, nw_depts, [("Ravi Kapoor", "ravi@consult.test", "HR", "employee", "manager", "senior")])
    add_people(bp, bp_depts, [("Ravi Kapoor", "ravi@consult.test", None, "admin", "manager", "senior")])
    db.flush()

    # Some existing results so dashboards aren't empty
    def answer(email, org, qid, text, score, reason=None, flags=None):
        m = db.query(models.Membership).filter_by(user_id=users[email].id, org_id=org.id).first()
        db.add(models.Response(membership_id=m.id, question_id=qid, answer=text, score=score, reason=reason, flags=flags or []))

    answer("vikram@northwind.test", nw, "common-freq", "Daily", 4)
    answer("vikram@northwind.test", nw, "common-open", "Used ChatGPT to draft 20 follow-up emails and edited each one.", 4, "Regular use with editing.", [])
    answer("priya@northwind.test", nw, "common-freq", "A few times a month", 2)
    answer("priya@northwind.test", nw, "common-open", "Pasted a customer's complaint thread into ChatGPT to summarise it.", 3, "Useful summary but shared customer data.", ["customer_data_shared"])
    answer("tom@bluepeak.test", bp, "common-freq", "A few times a week", 3)
    answer("kabir@bluepeak.test", bp, "common-open", "Uploaded our full customer refund list to an AI tool to find patterns.", 3, "Good idea, unsafe data handling.", ["customer_data_shared", "confidential_data_shared"])
    answer("kabir@bluepeak.test", bp, "common-freq", "Daily", 4)

    db.commit()
    db.close()
    print("Seeded. Log in with any seeded email and password 'pulse123'.")


if __name__ == "__main__":
    run()
