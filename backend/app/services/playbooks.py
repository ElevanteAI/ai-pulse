"""Remediation playbooks, keyed by risk flag (the same labels the scoring service allows).

`executive` is shown to admins when they click a risk on the dashboard.
`employee` is a short list of tips shown on the report of anyone flagged for that risk.
"""

PLAYBOOKS = {
    "customer_data_shared": {
        "title": "Customer data shared with AI tools",
        "summary": "Employees are pasting customer information into AI tools, which may store or train on it.",
        "executive": {
            "guardrails": [
                "Ban personal data (names, emails, order or account details) in any non-approved AI tool",
                "Require customer data to be anonymised or replaced with placeholders before prompting",
                "Add AI-tool use to the data-protection and incident-reporting policy",
            ],
            "approved_tooling": [
                "Provide a company-licensed AI workspace with a no-training, no-retention data agreement",
                "Block consumer AI chatbots on devices that handle customer records",
            ],
            "team_guidance": [
                "Run a 30-minute session using real, redacted examples from your own tickets",
                "Name one owner per team who employees can ask before using AI on customer data",
            ],
        },
        "employee": [
            "Before prompting, replace names, emails, phone numbers and IDs with placeholders like [CUSTOMER]",
            "Paste only the part of a thread you actually need summarised",
            "If you already pasted customer data into a public tool, tell your manager so it can be handled properly",
        ],
    },
    "confidential_data_shared": {
        "title": "Confidential company data shared with AI tools",
        "summary": "Internal documents, financials, code or strategy are being given to tools the company does not control.",
        "executive": {
            "guardrails": [
                "Define what counts as confidential (financials, source code, contracts, roadmap) in one page",
                "Prohibit uploading files in that list to non-approved AI tools",
                "Review vendor terms for retention and training before any tool is approved",
            ],
            "approved_tooling": [
                "Approve a short list of tools with enterprise terms, and publish it where people will find it",
                "Use data-loss-prevention rules to warn on large uploads to unapproved AI sites",
            ],
            "team_guidance": [
                "Give each team a list of tasks that are fine to do with AI and tasks that are not",
                "Make asking whether something is allowed quick: one channel, answered within a day",
            ],
        },
        "employee": [
            "Use summaries or fake sample data instead of the real file whenever the task allows it",
            "Never paste secrets, keys, contracts or unreleased numbers into a prompt",
            "Check the approved-tools list before uploading any internal document",
        ],
    },
    "unreviewed_output": {
        "title": "AI output used without review",
        "summary": "AI-generated text, code or analysis is being sent or shipped without a human check.",
        "executive": {
            "guardrails": [
                "Require a named human to review and own anything AI-generated that leaves the company",
                "Add an AI-assisted checkbox to existing review steps (code review, customer replies, reports)",
                "Track errors traced to AI output so the policy can be tuned",
            ],
            "approved_tooling": [
                "Prefer tools that show sources or citations so claims can be verified quickly",
            ],
            "team_guidance": [
                "Share two or three real examples of AI getting facts wrong in your domain",
                "Agree what a good check looks like for each role so reviewing is routine, not extra work",
            ],
        },
        "employee": [
            "Verification checklist: facts and numbers, names and dates, tone, anything that sounds too sure",
            "For code: run it, read it, and write a test before merging",
            "Edit in your own voice before sending; you are responsible for what goes out",
        ],
    },
    "policy_unaware": {
        "title": "Employees unaware of AI usage policy",
        "summary": "People are using AI at work without knowing what the company allows.",
        "executive": {
            "guardrails": [
                "Publish a short, plain-language AI usage policy (one page, with do and do-not examples)",
                "Include the policy in onboarding and acknowledge it annually",
            ],
            "approved_tooling": [
                "List approved tools and their intended uses in the same place as the policy",
            ],
            "team_guidance": [
                "Have each manager walk their team through the policy once, then repeat the diagnostic after a quarter",
                "Appoint a point of contact for policy questions",
            ],
        },
        "employee": [
            "Ask your manager where the AI usage policy lives, and read it once",
            "When unsure whether a task is allowed, ask before pasting anything",
        ],
    },
}


def employee_tips(flags):
    """Remediation tips for the flags on one employee's report, in a stable order."""
    return [
        {"risk": f, "title": PLAYBOOKS[f]["title"], "tips": PLAYBOOKS[f]["employee"]}
        for f in sorted(flags) if f in PLAYBOOKS
    ]


def executive_card(flag):
    p = PLAYBOOKS.get(flag)
    if p is None:
        return None
    return {"risk": flag, "title": p["title"], "summary": p["summary"], **p["executive"]}
