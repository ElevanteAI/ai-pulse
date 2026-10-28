"""Policy reality check: does what people *say* about the AI policy match how they handle data?

Built only from answers we already collect:
- "says they follow it": common-policy answered "Yes, and I follow it" or "...help others follow it"
- "unaware":             common-policy answered "I don't know" or "I think so, but I haven't read it"
- "risky practice":      common-data answered "I don't think about it" or "Rarely",
                         OR the open answer was flagged for sharing customer/confidential data

The interesting group is people who say they follow the policy AND show risky practice:
the policy exists and people believe in it, but it isn't changing behaviour. That's a
different fix (practical training, approved tools) from people who've never read it.
"""
POLICY_Q, DATA_Q = "common-policy", "common-data"
DATA_FLAGS = {"customer_data_shared", "confidential_data_shared"}

CONSISTENT, GAP, RISKY, UNAWARE, UNKNOWN = "consistent", "gap", "risky", "unaware", "not_enough_data"


def _score(rows, question_id):
    r = next((r for r in rows if r.question_id == question_id), None)
    return r.score if r is not None else None


def classify(rows):
    """One person's answers -> (status, evidence). Evidence is shown to that person only, never to leadership."""
    policy = _score(rows, POLICY_Q)
    if policy is None:
        return UNKNOWN, []

    evidence = []
    data = next((r for r in rows if r.question_id == DATA_Q), None)
    if data is not None and data.score is not None and data.score <= 2:
        evidence.append(f'When asked how often you remove customer or confidential details before pasting, you said "{data.answer}".')
    flagged = sorted({f for r in rows for f in (r.flags or [])} & DATA_FLAGS)
    if flagged:
        what = " and ".join(f.split("_")[0] for f in flagged)
        evidence.append(f"The AI work example you described involved sharing {what} data with an AI tool.")

    if policy <= 2:
        return UNAWARE, evidence
    if evidence:
        return (GAP if policy >= 4 else RISKY), evidence
    return CONSISTENT, evidence


MESSAGES = {
    CONSISTENT: "Your answers about the AI policy and how you handle data line up. Nothing to change here.",
    GAP: "You said you follow the company's AI policy, but some of your answers suggest company or customer "
         "data is still reaching AI tools. Before pasting anything, remove names, emails, order and account "
         "numbers, and check which tools are approved for confidential work.",
    RISKY: "You've read the AI policy, but some of your answers suggest company or customer data is still "
           "reaching AI tools. Before pasting anything, remove names, emails, order and account numbers.",
    UNAWARE: "You're not sure what the company's AI policy says. It's worth a 10-minute read: "
             "it tells you which tools are approved and what you must never paste into them.",
    UNKNOWN: "Take the diagnostic to see how your AI habits compare with the company policy.",
}


def for_employee(rows):
    status, evidence = classify(rows)
    return {"status": status, "message": MESSAGES[status], "evidence": evidence}


def for_group(people):
    """Counts only, for leadership. Only ever called on groups that passed the minimum group size."""
    says_follow = sum(1 for _, rs in people if (_score(rs, POLICY_Q) or 0) >= 4)
    statuses = [classify(rs)[0] for _, rs in people]
    gap, unaware = statuses.count(GAP), statuses.count(UNAWARE)
    return {
        "respondents": len(people),
        "say_they_follow_policy": says_follow,
        "of_whom_risky_practice": gap,
        "gap_rate": round(gap / says_follow, 2) if says_follow else None,
        "unaware_of_policy": unaware,
        "headline": _headline(len(people), says_follow, gap, unaware),
    }


def _headline(n, says, gap, unaware):
    if not says:
        line = f"None of {n} people say they follow the AI policy."
    elif gap:
        line = f"{says} of {n} people say they follow the AI policy, but {gap} of them ({round(100 * gap / says)}%) still show risky data handling."
    else:
        line = f"{says} of {n} people say they follow the AI policy, and their answers back it up."
    if unaware:
        line += f" {unaware} {'is' if unaware == 1 else 'are'} not sure what the policy says."
    return line
