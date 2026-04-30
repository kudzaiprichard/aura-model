"""Generate 800 professional internal-mail emails (label=0) for AURA online-learning augmentation.

Follows section 3.4 of online_learning_dataset.md and applies the quality checks from section 6.

Design:
- 4 sender types: colleague, management, HR, IT Support.
- 5 subtypes: meeting, document, project_update, hr_notice, it_notice.
- Hand-written subject and body banks per subtype. Real-sounding project names, colleague
  names, and internal links (confluence, sharepoint, docs.google.com).
- Strict section-6 gate + section 3.4 body constraints: no urgency, no verification, no
  suspicious links, 50-150 word body.
"""

from __future__ import annotations

import csv
import hashlib
import random
import re
from pathlib import Path

random.seed(20260418)

OUT_PATH = Path(
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/professional_internal.csv"
)

# ------------------------------------------------------------------------------------
# Name pools — generated senders come from these.
# ------------------------------------------------------------------------------------

FIRST_NAMES = [
    "Sarah", "John", "Emma", "Michael", "Priya", "David", "Rachel", "Tom",
    "Olivia", "James", "Nina", "Marcus", "Ellie", "Hassan", "Amelia", "Dan",
    "Clara", "Theo", "Ruth", "Leo", "Maya", "Jay", "Kate", "Ben", "Liam",
    "Sophie", "Matt", "Aisha", "Chen", "Ravi", "Fatima", "Diego", "Lena",
    "Oscar", "Nadia", "Eli", "Tara",
]

LAST_NAMES = [
    "Smith", "Johnson", "Patel", "Chen", "Miller", "Rodriguez", "Wilson",
    "Taylor", "Nguyen", "Brown", "Davis", "Garcia", "Khan", "Kim", "Singh",
    "O'Brien", "Kowalski", "Andersen", "Foster", "Parker", "Morgan", "Cohen",
    "Reed", "Nakamura", "Mendez", "Okafor", "Romano", "Werner", "Silva",
    "Hughes", "Young", "Carter", "Quinn", "Brennan", "Novak",
]

COMPANY_DOMAINS = [
    "company.com", "acme.com", "novatech.io", "contoso.com", "globex.com",
    "initech.com", "stellar.io", "northbound.co", "quaybridge.com", "plumeworks.io",
]

PROJECT_NAMES = [
    "Phoenix", "Atlas", "Horizon", "Kestrel", "Orion", "Helios", "Mercury",
    "Nimbus", "Beacon", "Vega", "Lighthouse", "Compass", "Pioneer", "Summit",
    "Apollo", "Aurora", "Keystone", "Meridian",
]

TEAMS = [
    "Engineering", "Product", "Design", "Marketing", "Sales", "Finance",
    "Operations", "Customer Success", "Data", "Platform", "Growth", "Research",
]

STAKEHOLDERS = [
    "leadership", "the exec team", "the steering committee", "the client",
    "the review panel", "the CTO", "the CFO", "the partnership team",
]

TOPICS = [
    "launch", "rollout", "deliverables", "handover", "migration", "Q2 roadmap",
    "the vendor call", "budget planning", "performance review", "timeline",
    "new requirements", "risk register",
]

MONTHS = [
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
]

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

TIMES = ["9am", "9:30am", "10am", "10:30am", "11am", "1pm", "1:30pm",
         "2pm", "2:30pm", "3pm", "3:30pm", "4pm"]


def pick(seq):
    return random.choice(seq)


def first_last_email(domain: str) -> tuple[str, str, str]:
    first = pick(FIRST_NAMES)
    last = pick(LAST_NAMES)
    local = f"{first[0].lower()}.{last.lower().replace(chr(39), '')}"
    return first, last, f'"{first} {last}" <{local}@{domain}>'


def ref_id(prefix="REQ"):
    return f"{prefix}-{random.randint(1000, 99999)}"


# ------------------------------------------------------------------------------------
# Sender builders per sender-type. Each returns a (sender_string, first_name_for_sign_off).
# ------------------------------------------------------------------------------------

HR_SENDER_TEMPLATES = [
    '"HR Team" <hr@{domain}>',
    '"People Team" <peopleops@{domain}>',
    '"HR Department" <hr-admin@{domain}>',
    '"People Operations" <people@{domain}>',
    '"Benefits Team" <benefits@{domain}>',
    '"{first} {last}" <{local}@{domain}>',  # named HR manager
]

IT_SENDER_TEMPLATES = [
    '"IT Support" <it@{domain}>',
    '"IT Helpdesk" <helpdesk@{domain}>',
    '"Tech Support" <tech-support@{domain}>',
    '"IT Operations" <itops@{domain}>',
    '"Systems Team" <systems@{domain}>',
    '"{first} {last} — IT" <{local}@{domain}>',
]


def make_sender(sender_type: str):
    domain = pick(COMPANY_DOMAINS)
    if sender_type in ("colleague", "management"):
        first, last, sender = first_last_email(domain)
        return sender, first, domain
    if sender_type == "hr":
        tpl = pick(HR_SENDER_TEMPLATES)
        if "{first}" in tpl:
            first, last, _ = first_last_email(domain)
            local = f"{first[0].lower()}.{last.lower().replace(chr(39), '')}"
            sender = tpl.format(domain=domain, first=first, last=last, local=local)
        else:
            sender = tpl.format(domain=domain)
            first = "the People team"
        return sender, first, domain
    if sender_type == "it":
        tpl = pick(IT_SENDER_TEMPLATES)
        if "{first}" in tpl:
            first, last, _ = first_last_email(domain)
            local = f"{first[0].lower()}.{last.lower().replace(chr(39), '')}"
            sender = tpl.format(domain=domain, first=first, last=last, local=local)
        else:
            sender = tpl.format(domain=domain)
            first = "IT Support"
        return sender, first, domain
    raise ValueError(sender_type)


# ------------------------------------------------------------------------------------
# Subject banks per subtype
# ------------------------------------------------------------------------------------

SUBJECTS = {
    "meeting": [
        "Meeting tomorrow at {time}",
        "Follow up from today's call",
        "Can we sync this week?",
        "Quick catch-up {day}?",
        "Kick-off meeting for {project}",
        "Calendar check — {day}",
        "30-min sync on {topic}",
        "Shall we schedule a call on {topic}?",
        "Moving {day}'s meeting",
        "Meeting notes from {day}",
        "Invite: {project} stand-up",
        "Block on calendar for {day}",
        "Recap of our call on {topic}",
        "{project} working session on {day}",
        "Reschedule our 1:1",
    ],
    "document": [
        "Draft report attached",
        "Please review the proposal",
        "Updated {project} timeline",
        "Q{qn} report ready for review",
        "{project} spec for feedback",
        "Updated deck for {day}",
        "Slides from the workshop",
        "Revised draft — your thoughts?",
        "Budget file for review",
        "Meeting notes from {day}",
        "{project} RFC draft",
        "Quick review of the one-pager",
        "{project} retrospective notes",
        "Proposal v{vn} — take another look",
    ],
    "project_update": [
        "Project status update — {project}",
        "{project} weekly update",
        "Team announcement",
        "New process starting {day}",
        "Quick update on {project}",
        "Sprint summary — week of {date}",
        "Status report — {project}",
        "{project} milestone reached",
        "Update from the {team} team",
        "Heads up on {topic}",
        "{project} — end of week note",
        "Monthly update from the team",
    ],
    "hr_notice": [
        "Reminder: expense submission deadline",
        "Updated leave policy",
        "Team outing next Friday",
        "{month} pay slip now available",
        "Reminder: benefits enrolment",
        "Updated employee handbook",
        "Annual review schedule",
        "New hires joining this month",
        "Wellness programme update",
        "Training schedule for {month}",
        "Volunteer day sign-up",
        "Office closure — {date}",
        "Reminder: performance conversations",
        "Learning budget refresh",
        "Quarterly all-hands on {date}",
    ],
    "it_notice": [
        "Scheduled maintenance this weekend",
        "Email downtime tonight",
        "New VPN rolling out",
        "Reminder: password rotation schedule",
        "Office Wi-Fi upgrade",
        "New laptops arriving next week",
        "System refresh — Saturday",
        "Slack upgrade — no action needed",
        "Phone system migration",
        "MFA rollout update",
        "Jira maintenance window",
        "Conference room equipment refresh",
    ],
}


# ------------------------------------------------------------------------------------
# Body banks per (sender_type, subtype). Signed off contextually.
# ------------------------------------------------------------------------------------

BODIES = {
    # -------------------- COLLEAGUE --------------------
    ("colleague", "meeting"): [
        (
            "Hi {me},\n\nHope your week is going well. I wanted to follow up on what we discussed in "
            "Tuesday's planning session. Do you have 30 minutes this week for a quick sync on the {project} "
            "timeline? I'm free most afternoons after 3 or any time {day} morning.\n\nI'll keep it short — "
            "mostly want to align on the launch date and the open questions from {teammate}'s email.\n\n"
            "Thanks,\n{first}"
        ),
        (
            "Hi {me},\n\nCan we find 20 minutes before {day} to go over the {project} handover notes? "
            "I've blocked out the morning so any slot that works for you is fine. The main things I want "
            "to cover are the testing gaps {teammate} flagged and the decision about the launch window.\n\n"
            "Happy to jump on a call or meet in person if you're in the office.\n\nThanks,\n{first}"
        ),
        (
            "Hi {me},\n\nQuick note to confirm our 1:1 moved to {time} on {day}. Same room, same agenda "
            "as last time. I'll add a couple of items from the {project} retro so we can talk through the "
            "action points together.\n\nIf the new time doesn't work, just let me know and we can find "
            "another slot.\n\nThanks,\n{first}"
        ),
        (
            "Hi {me},\n\nFollowing up on our call earlier — good chat. I've added the action items from "
            "what we discussed into the {project} tracker. Could we grab another 30 minutes next week to "
            "review progress and decide on the next milestone? {day} afternoon works best on my end but "
            "I'm flexible.\n\nThanks,\n{first}"
        ),
        (
            "Hi {me},\n\nWould you be up for a quick catch-up on {day}? Nothing urgent — just want to "
            "bounce some thoughts on the {project} approach and hear what {team} is seeing on their end. "
            "Coffee in the kitchen or the usual meeting room, either works.\n\nLet me know.\n\nThanks,"
            "\n{first}"
        ),
        (
            "Hi {me},\n\nShall we do a short working session on {topic} this week? I was thinking an hour "
            "on {day} at {time}. {teammate} said she can join for the first half. Agenda would be: walk "
            "through the current options, pick a direction, then identify owners before we close out.\n\n"
            "Thanks,\n{first}"
        ),
    ],
    ("colleague", "document"): [
        (
            "Hi {me},\n\nSharing the draft of the {project} proposal for your review. No rush, but it would "
            "be great to have your comments by {day} so I can fold them in before the {stakeholder} meeting. "
            "The document is on SharePoint: company.sharepoint.com/sites/{team}/{project}-proposal.\n\n"
            "Let me know if anything needs more context.\n\nThanks,\n{first}"
        ),
        (
            "Hi {me},\n\nI've just pushed a revised version of the {project} spec. Main changes are in the "
            "scoping section after the feedback from {teammate}. Link here: confluence.{domain}/pages/"
            "{project}-spec-v{vn}.\n\nHappy to walk through it on a call if you'd prefer — {day} afternoon "
            "works for me.\n\nThanks,\n{first}"
        ),
        (
            "Hi {me},\n\nAttaching the Q{qn} numbers for {team}. Nothing surprising but a couple of the "
            "line items shifted after the reallocation in {month}. The spreadsheet is at docs.google.com/"
            "spreadsheets/{ref_id}.\n\nIf you spot anything off, please flag before Friday so I can "
            "correct it ahead of the review.\n\nThanks,\n{first}"
        ),
        (
            "Hi {me},\n\nPlease take a look at the {project} timeline when you have a moment. I've "
            "incorporated {teammate}'s suggestions from the retro and added the dependencies on the "
            "{team} deliverables. The doc is live at confluence.{domain}/{project}/timeline.\n\nComments "
            "in the doc are fine. Thanks,\n{first}"
        ),
        (
            "Hi {me},\n\nSharing the slides from the {topic} workshop we ran on {day}. Happy with how "
            "it went overall and the discussion in the back half was more energetic than I expected. A "
            "few action items ended up with {team}, including the research into the vendor options and "
            "the write-up for {stakeholder}. Deck lives at company.sharepoint.com/sites/{team}/workshops/"
            "{project}.\n\nIf anything looks off, ping me before {day2} and I'll get it updated.\n\n"
            "Thanks,\n{first}"
        ),
        (
            "Hi {me},\n\nHere is the updated one-pager for {project}. I've tightened the narrative and "
            "swapped the chart based on what you said last week, and moved the scope section up so it "
            "leads with the customer outcome. View and suggest mode is on: docs.google.com/document/"
            "{ref_id}.\n\nLet me know if you want to give it one more pass before I circulate it to "
            "{stakeholder} on {day}. Happy to hold off a day if you'd rather read it fresh.\n\nThanks,"
            "\n{first}"
        ),
        (
            "Hi {me},\n\nI've put together a short review of the {project} architecture options. Two of "
            "them look viable; the third I've parked with notes explaining why. The doc is at confluence."
            "{domain}/{project}/options and I'd appreciate your eyes on the trade-offs section before "
            "I take it to {stakeholder} on {day}.\n\n{teammate} reviewed an earlier draft and her "
            "comments are already in the doc.\n\nThanks,\n{first}"
        ),
        (
            "Hi {me},\n\nAttaching the revised budget file for {team} for Q{qn}. Most of the line items "
            "are unchanged, but I've flagged three that shifted after the reallocation discussion with "
            "{stakeholder} last week. The spreadsheet is at docs.google.com/spreadsheets/{ref_id}.\n\n"
            "If the numbers look right to you, I'll send it on to finance on {day}. Otherwise let me "
            "know what needs another look.\n\nThanks,\n{first}"
        ),
    ],
    ("colleague", "project_update"): [
        (
            "Hi team,\n\nQuick update on {project} for the week of {date}. We finished the integration work "
            "with {team} on {day} and the first end-to-end test passed. Two small issues raised by "
            "{teammate} are being investigated and should be closed by next week.\n\nFull write-up is on "
            "Confluence: confluence.{domain}/{project}/weekly.\n\nThanks,\n{first}"
        ),
        (
            "Hi all,\n\nSharing a short status note on {project}. We are on track for the {date} milestone. "
            "The {team} dependency is resolved, and QA has started the regression cycle. {teammate} is "
            "going to circulate the test plan later this week.\n\nDetails in the dashboard: company."
            "sharepoint.com/sites/{team}.\n\nThanks,\n{first}"
        ),
        (
            "Hi everyone,\n\nEnd-of-week note from the {project} side. We closed out {N} tickets this "
            "sprint and demoed the new flow to {stakeholder} on {day}. Feedback was positive. Next focus: "
            "the performance work that blocked us last cycle.\n\nAgenda for {day}'s stand-up will cover "
            "the handoff to {team}.\n\nThanks,\n{first}"
        ),
        (
            "Hi team,\n\nProject status for {project}: on track. We hit the internal milestone on {day}, "
            "{N} days ahead of plan. Thanks to {teammate} for covering the review cycle while I was out. "
            "Next up is the hand-off to {team} for integration testing.\n\nFull notes: confluence.{domain}"
            "/{project}/status.\n\nThanks,\n{first}"
        ),
        (
            "Hi all,\n\nSprint summary for the week of {date}. We closed {N} stories and moved two into "
            "next sprint due to a dependency from {team}. No blockers to flag. {teammate} and I will run "
            "a short retro on {day} to capture lessons learned.\n\nMore detail in the Jira board.\n\n"
            "Thanks,\n{first}"
        ),
        (
            "Hi team,\n\nHeads up on {topic} — we're changing the way we handle {topic} from next sprint. "
            "{teammate} wrote up the new process on the team wiki: confluence.{domain}/{team}/process. "
            "Nothing dramatic, but please skim it before our {day} stand-up so we can answer any "
            "questions together.\n\nThanks,\n{first}"
        ),
    ],

    # -------------------- MANAGEMENT --------------------
    ("management", "meeting"): [
        (
            "Hi {me},\n\nLet's put 30 minutes on the calendar for {day} at {time} to go over {project} "
            "priorities for the quarter. I'd like to talk through resourcing with you and see how the "
            "{team} pipeline is shaping up. Please bring the latest headcount numbers if you have "
            "them.\n\nThanks,\n{first}"
        ),
        (
            "Hi team,\n\nOur quarterly planning review is on {day} at {time}. I've attached the agenda "
            "and the supporting document to the calendar invite. Please come prepared to cover your "
            "team's three priorities for the quarter and any known risks.\n\nWe'll wrap by {time2}.\n\n"
            "Thanks,\n{first}"
        ),
        (
            "Hi {me},\n\nMoving our 1:1 from {day} to {day2} at {time}. Sorry for the short notice — "
            "{stakeholder} booked a conflicting session. Everything else on the agenda stands and I'd "
            "still like to cover the {project} plan and your career conversation.\n\nThanks,\n{first}"
        ),
        (
            "Hi all,\n\nScheduling a {project} steering committee for the {date} week. Please hold "
            "{day} from {time} until {time2}. Invitees are the usual group plus {teammate} from {team}. "
            "Agenda will follow on {day2}.\n\nThanks,\n{first}"
        ),
        (
            "Hi {me},\n\nCan we find 20 minutes before the end of the week to align on the {topic} "
            "decision? {stakeholder} is expecting a recommendation from our side by {day}. I'd rather "
            "we discuss live than go back and forth on email.\n\nLet me know what time works.\n\nThanks,"
            "\n{first}"
        ),
    ],
    ("management", "document"): [
        (
            "Hi team,\n\nAttached is the Q{qn} plan for {team}. Please take some time to review it "
            "before our meeting on {day}. The key asks from me are to validate the headcount numbers "
            "in section two, sense-check the {project} milestones, and flag any dependencies I might "
            "have missed. Document is at company.sharepoint.com/sites/{team}/q{qn}-plan.\n\nI'll fold "
            "comments in by {day2} so we can bring a clean version to {stakeholder}.\n\nThanks for the "
            "quick turnaround.\n\n{first}"
        ),
        (
            "Hi all,\n\nSharing the proposal that went to {stakeholder} last week. No changes are "
            "expected, but it's worth reading so everyone has the same context heading into the "
            "{project} kick-off on {day}. The document covers the scope we're committing to, the "
            "staffing assumptions, and the dependencies on {team}.\n\nYou can find it at confluence."
            "{domain}/leadership/{project}-proposal. If anything looks surprising, flag it to me or "
            "{teammate} before the kick-off.\n\nThanks,\n{first}"
        ),
        (
            "Hi team,\n\nUpdated {project} timeline attached. Two milestones shifted after the scope "
            "clarification from {stakeholder} on {day} and one has moved earlier thanks to progress from "
            "{team}. The revised dates are in the plan at company.sharepoint.com/sites/{team}/{project}."
            "\n\n{teammate} will walk through the changes on {day2} at {time} and answer any questions. "
            "If you can't make it, comments in the doc are fine and I'll respond directly.\n\nThanks,"
            "\n{first}"
        ),
        (
            "Hi {me},\n\nPlease take another pass through the {project} RFC before I share it with "
            "{stakeholder}. I've addressed the comments from the last round, added the alternatives "
            "section you asked about, and tightened the risks table so the trade-offs are clearer. "
            "Document is at docs.google.com/document/{ref_id}.\n\nIf you're happy with it, I'll send "
            "it out after our {day} 1:1. Otherwise I'm happy to iterate one more time.\n\nThanks for "
            "the iteration.\n\n{first}"
        ),
        (
            "Hi team,\n\nFinal version of the {project} retrospective notes is ready. I've incorporated "
            "what came up in the session on {day}, turned the top three items into owners with dates, "
            "and added a short section on what we'd do differently next cycle. Please read before "
            "{day2} and flag anything that doesn't feel right at confluence.{domain}/{project}/retro."
            "\n\nI'll share a summary with {stakeholder} once we've settled on the follow-ups.\n\n"
            "Thanks,\n{first}"
        ),
        (
            "Hi all,\n\nSharing the updated strategy deck for {team}. I've pulled in the numbers from "
            "the latest {project} review and reworked the narrative around the three priorities we "
            "settled on. The deck is at company.sharepoint.com/sites/{team}/strategy and there is a "
            "short written summary at the top for anyone short on time.\n\nI'll walk through it in "
            "the all-hands on {day}. Questions or comments before then are very welcome.\n\nThanks,\n"
            "{first}"
        ),
    ],
    ("management", "project_update"): [
        (
            "Hi team,\n\nQuick update on {project}. We hit the Phase 1 milestone on {day}, slightly ahead "
            "of the plan. Huge thanks to everyone who pushed to close out the {team} dependencies. Next "
            "up: QA cycle starts on {day2}, with {teammate} leading test coverage.\n\nWe'll recap in "
            "{day2}'s stand-up.\n\nThanks,\n{first}"
        ),
        (
            "Hi all,\n\nTeam announcement: {teammate} is moving into the {team} lead role starting "
            "{month}, working closely on {project} priorities. This is a well-earned step up and I "
            "know she'll do a great job. Please join me in congratulating her and helping with the "
            "transition over the next few weeks. Her existing responsibilities will be redistributed "
            "across the team; we'll confirm the final split at the {day} stand-up.\n\nMore detail at "
            "the next all-hands.\n\nThanks,\n{first}"
        ),
        (
            "Hi team,\n\nWeekly status for {project}: on track. Two risks to flag — the {team} "
            "dependency is slipping by a week, and we have a staffing gap in the {month} cycle. I'm "
            "working with {teammate} on both. Nothing blocking right now.\n\nFull notes: confluence."
            "{domain}/{project}.\n\nThanks,\n{first}"
        ),
        (
            "Hi everyone,\n\nNew process starting {day}: we're moving {project} stand-ups to async in "
            "Slack. The motivation is to free up calendar time for focused work. The template and "
            "channel are live already: #{team}-standup.\n\nLet me know if anything is unclear.\n\n"
            "Thanks,\n{first}"
        ),
        (
            "Hi team,\n\nEnd of week note. {project} launched on {day} without major issues. Thanks to "
            "the {team} team for the extended hours on Friday. {teammate} is compiling the customer "
            "feedback and we'll talk through it at next week's all-hands.\n\nRest up over the weekend.\n\n"
            "Thanks,\n{first}"
        ),
    ],

    # -------------------- HR --------------------
    ("hr", "hr_notice"): [
        (
            "Hi everyone,\n\nA reminder that the expense submission deadline for {month} is this Friday "
            "at 5pm. Please submit through the usual portal: company.sharepoint.com/sites/finance/"
            "expenses. Late submissions will roll into next month's cycle and may not appear on your "
            "next pay slip.\n\nIf the portal is giving you trouble, let us know and we'll help sort it "
            "out.\n\nThanks,\n{first}\nPeople Operations"
        ),
        (
            "Hi team,\n\nWe've updated the leave policy with a few changes effective from {month}. The "
            "main update is the addition of two wellness days per year and clearer guidance on carrying "
            "unused leave over. The full policy is at confluence.{domain}/people/leave-policy.\n\nIf you "
            "have any questions, you can bring them to the next office hours on {day}.\n\nThanks,\n{first}"
            "\nPeople Operations"
        ),
        (
            "Hi all,\n\nThe team outing this {month} will be on {day}. We've booked a private room at the "
            "usual venue and everyone is welcome to bring a plus-one. Dietary requirements can be noted "
            "on the sign-up form at company.sharepoint.com/sites/people/outing.\n\nRSVP by {day2} so we "
            "can finalise numbers.\n\nThanks,\n{first}"
        ),
        (
            "Hi {me},\n\nYour {month} pay slip is now available in the employee portal at company."
            "sharepoint.com/sites/people/payroll. There are no changes to your standard deductions this "
            "month. If you notice anything unexpected, please reach out to the payroll team directly.\n\n"
            "Thanks,\n{first}\nPeople Operations"
        ),
        (
            "Hi team,\n\nBenefits enrolment opens on {day} and runs for two weeks. Even if you don't plan "
            "to change anything, please log in and confirm your selections — the system needs a positive "
            "confirmation for audit reasons. Portal and guides: confluence.{domain}/people/benefits.\n\n"
            "Office hours on {day2} for anyone with questions.\n\nThanks,\n{first}"
        ),
        (
            "Hi all,\n\nThe {month} training schedule is now live. We've added two new courses on people "
            "management and one on inclusive hiring. Sign-up, descriptions, and dates are on the learning "
            "portal: confluence.{domain}/people/training.\n\nSpaces are limited, so book early if anything "
            "catches your eye.\n\nThanks,\n{first}"
        ),
        (
            "Hi team,\n\nAnnual performance review cycle kicks off on {date}. The process is the same as "
            "last year, with one minor change: the self-review form has been shortened. Timelines, "
            "templates, and manager guides are at confluence.{domain}/people/reviews.\n\n{first} and I "
            "will run two drop-in sessions next week for anyone with questions.\n\nThanks,\n{first}"
        ),
        (
            "Hi everyone,\n\nTwo new joiners are starting this {month}. {teammate} joins {team} as a "
            "senior engineer on {day}, and we have one more starting the week after. Please help make "
            "them feel welcome when you see them in the office or on calls.\n\nIntroductions will go "
            "out on the team Slack channel.\n\nThanks,\n{first}\nPeople Operations"
        ),
        (
            "Hi team,\n\nQuick note on the wellness programme. We've added a subsidised gym membership "
            "and an employee assistance line, both effective from {month}. Details and sign-up links "
            "are at confluence.{domain}/people/wellness.\n\nIf you have suggestions for future additions, "
            "drop them in the feedback form at the bottom of the page.\n\nThanks,\n{first}"
        ),
        (
            "Hi all,\n\nReminder that our quarterly all-hands is on {date} at {time}. Agenda is going "
            "out on {day} and we'd like to hold time for Q&A at the end. Submissions can go through the "
            "form at company.sharepoint.com/sites/people/all-hands.\n\nHope to see you all there.\n\n"
            "Thanks,\n{first}"
        ),
    ],

    # -------------------- HR (document-sharing) --------------------
    ("hr", "document"): [
        (
            "Hi team,\n\nSharing the updated employee handbook for {month}. Changes are summarised at "
            "the top; most updates are clarifications rather than new policies. Please read through at "
            "your own pace: confluence.{domain}/people/handbook.\n\nOffice hours with the People team "
            "are on {day} for anything that needs discussion.\n\nThanks,\n{first}\nPeople Operations"
        ),
        (
            "Hi all,\n\nAttaching the updated performance review template for the {month} cycle. The "
            "main change is the shorter self-review section, which should save everyone time. Template "
            "and guide are at company.sharepoint.com/sites/people/review-template.\n\nLet us know if "
            "anything is unclear.\n\nThanks,\n{first}"
        ),
        (
            "Hi {me},\n\nThe updated contractor onboarding guide is ready. We've streamlined the "
            "paperwork and added a clearer checklist for hiring managers. Guide: confluence.{domain}/"
            "people/contractors.\n\nIf you're bringing on anyone in the next few weeks, please use the "
            "new version.\n\nThanks,\n{first}\nPeople Operations"
        ),
    ],

    # -------------------- IT --------------------
    ("it", "it_notice"): [
        (
            "Hi all,\n\nScheduled maintenance this Saturday between 10pm and 2am local time. Email, VPN, "
            "and SharePoint will be unavailable during the window. No action needed on your end — we'll "
            "post in the #ops Slack channel when everything is back up.\n\nApologies for any "
            "inconvenience.\n\nIT Support"
        ),
        (
            "Hi team,\n\nWe're rolling out a new VPN client over the next two weeks. Your laptop will "
            "prompt you to install when you connect to the office network. The process takes about five "
            "minutes and no settings need to be changed. Full guide: confluence.{domain}/it/vpn.\n\n"
            "Questions welcome — helpdesk@{domain}.\n\nIT Support"
        ),
        (
            "Hi everyone,\n\nReminder that password rotation is due on {date}. You can change your "
            "password through the usual self-service portal at company.sharepoint.com/sites/it/password. "
            "If you miss the deadline, you'll be prompted on your next sign-in — nothing is locked or "
            "suspended.\n\nThanks,\nIT Support"
        ),
        (
            "Hi team,\n\nThe office Wi-Fi upgrade is planned for {day} between {time} and {time2}. "
            "During the window, the guest network will remain available. Staff devices may briefly "
            "drop and reconnect. No action needed from you.\n\nMore detail: confluence.{domain}/it/"
            "network-upgrade.\n\nIT Support"
        ),
        (
            "Hi everyone,\n\nNew laptops for the {team} refresh cycle arrive next week. {teammate} will "
            "coordinate handover slots. If you're on the list you'll get a separate email with a time. "
            "Data migration is handled by us — we'll walk you through it on the day.\n\nThanks,\nIT "
            "Support"
        ),
        (
            "Hi team,\n\nMFA rollout reaches {team} on {date}. The setup takes about five minutes and "
            "works with the Authenticator app you already have. Step-by-step guide: confluence.{domain}"
            "/it/mfa. The service desk is running drop-in sessions on {day} for anyone who wants help.\n\n"
            "Thanks,\nIT Support"
        ),
        (
            "Hi all,\n\nJira maintenance window is scheduled for {day} at {time}. The service will be "
            "read-only for around 30 minutes while we apply the update. Any tickets you open during "
            "that window will go through as soon as the service is back.\n\nThanks for your patience.\n"
            "\nIT Support"
        ),
        (
            "Hi team,\n\nWe're upgrading conference room equipment across floors two and three over "
            "{month}. The rooms may be out of action for a day at a time while the work is done. "
            "Booking calendars will show which room is affected and when. Fallback rooms are listed at "
            "confluence.{domain}/it/rooms.\n\nThanks,\nIT Support"
        ),
    ],

    ("it", "project_update"): [
        (
            "Hi team,\n\nQuick infrastructure status. The {project} migration is on track for a {date} "
            "cutover. {teammate} from {team} is helping us with the validation scripts and the early "
            "results look good — error rates on the shadow traffic match the old system within tolerance."
            " No downtime is expected for end users during the cutover itself. Detailed plan and "
            "rollback steps: confluence.{domain}/it/{project}.\n\nI'll share the go/no-go criteria "
            "ahead of the {day} stand-up. Happy to take questions there or in #it-platform.\n\nThanks,\n"
            "{first}"
        ),
        (
            "Hi all,\n\nUpdate on the chat platform migration. We've completed the pilot with {team} "
            "and the feedback is positive overall; the main asks were around notification controls and "
            "search, both of which are now in the backlog for {month}. Broader rollout begins shortly "
            "after with a phased approach to keep support load manageable. The transition guide is on "
            "Confluence: confluence.{domain}/it/chat-platform and {teammate} is running drop-in sessions "
            "every {day} for anyone who wants a walk-through.\n\nIT Support"
        ),
        (
            "Hi everyone,\n\nEnd of week note from IT. We closed {N} tickets this week, with median "
            "resolution just under four hours — our best number this quarter. One planned maintenance "
            "window to flag for {day2}; details follow next week but expect a short outage on the "
            "internal wiki. Thanks to {teammate} for covering the on-call rotation and to the {team} "
            "team for flagging the Jira issue early so we could patch it quietly.\n\nHave a good "
            "weekend.\n\nThanks,\nIT Support"
        ),
        (
            "Hi team,\n\nQuick note on the access management rollout. Phase one landed on {day} for "
            "{team} and the new request flow is already reducing ticket volume — about {N} fewer open "
            "requests than this time last cycle. Phase two covers the rest of the org in {month}. "
            "The updated guide is at confluence.{domain}/it/access-management and {teammate} will run "
            "a short overview at the next all-hands.\n\nNo action needed from anyone right now.\n\n"
            "Thanks,\n{first}"
        ),
    ],
    ("it", "meeting"): [
        (
            "Hi {me},\n\nCan we book 20 minutes on {day} at {time} to walk through the {project} setup? "
            "I want to confirm the access requests and make sure the hand-off to {team} is clean. "
            "Either room 3B or a quick call, whichever is easier for you.\n\nThanks,\n{first} from IT"
        ),
        (
            "Hi team,\n\nQuick heads up — I'd like to schedule a short review of the {project} "
            "architecture diagram. Proposing {day} at {time}. {teammate} will join to cover the "
            "integration piece. Doc to read ahead: confluence.{domain}/it/{project}.\n\nThanks,\n"
            "{first}"
        ),
    ],
    ("it", "document"): [
        (
            "Hi team,\n\nSharing the {project} runbook draft for review. I'd appreciate eyes on sections "
            "three and four, which cover the failover steps and the on-call handover. {teammate} has "
            "already reviewed the networking side, so you can skim that part unless something jumps out. "
            "Document lives at confluence.{domain}/it/{project}-runbook — comments welcome in the doc.\n"
            "\nI'd like to finalise by {day} so we can circulate it to {stakeholder} ahead of the "
            "cutover.\n\nThanks,\n{first} from IT"
        ),
        (
            "Hi all,\n\nThe updated access management guide is now live. The main change is the new "
            "request form for temporary access, which replaces the old helpdesk ticket route and should "
            "cut turnaround time by roughly half. We've also added a short FAQ at the end based on the "
            "most common questions from {team} during the pilot. Guide: confluence.{domain}/it/"
            "access-management.\n\nReach out with any questions — we're monitoring the inbox closely "
            "through {month}.\n\nThanks,\nIT Support"
        ),
        (
            "Hi {me},\n\nAttaching the draft of the updated security guidance for {team}. The policy "
            "itself hasn't changed much, but we've rewritten the examples and added a troubleshooting "
            "section based on the tickets we've seen over the last two quarters. The doc is at "
            "confluence.{domain}/it/security and I'd value your read before I share it more widely on "
            "{day}. No rush if you'd rather wait until after the {project} milestone lands.\n\nThanks,"
            "\n{first} from IT"
        ),
        (
            "Hi team,\n\nSharing the {project} operational checklist for your review. It covers the "
            "pre-launch validation, the cutover steps, and the first-24-hours monitoring plan. "
            "{teammate} has already added comments on the database section and I've folded those in. "
            "Full doc is at confluence.{domain}/it/{project}-checklist.\n\nIf you can review before "
            "our {day} sync, that gives us time to close any gaps before the go-live.\n\nThanks,\n"
            "{first} from IT"
        ),
        (
            "Hi all,\n\nSharing the updated incident response playbook. The main additions are a new "
            "section on communication during a live incident and clearer ownership for the first "
            "responder role. We ran a tabletop with {team} on {day} and folded the feedback in. "
            "Document: confluence.{domain}/it/incident-response.\n\nIf anything is unclear, {teammate} "
            "and I are running a walkthrough in the next all-hands.\n\nThanks,\nIT Support"
        ),
    ],
}


# ------------------------------------------------------------------------------------
# Plan: sum must equal 800. Maps (sender_type, subtype) -> count.
# ------------------------------------------------------------------------------------

PLAN = [
    # Colleague (240)
    ("colleague", "meeting", 80),
    ("colleague", "document", 80),
    ("colleague", "project_update", 80),
    # Management (220)
    ("management", "meeting", 60),
    ("management", "document", 80),
    ("management", "project_update", 80),
    # HR (180)
    ("hr", "hr_notice", 160),
    ("hr", "document", 20),
    # IT (160)
    ("it", "it_notice", 80),
    ("it", "project_update", 40),
    ("it", "meeting", 20),
    ("it", "document", 20),
]
assert sum(c for _, _, c in PLAN) == 800


# ------------------------------------------------------------------------------------
# Context builder and placeholder fill
# ------------------------------------------------------------------------------------

PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def build_ctx(first_sender: str, domain: str) -> dict:
    # Choose two distinct teammate names (one for "me" recipient style, one for teammate ref)
    me = pick(FIRST_NAMES)
    teammate = pick(FIRST_NAMES)
    while teammate == me:
        teammate = pick(FIRST_NAMES)
    return {
        "me": me,
        "teammate": teammate,
        "first": first_sender,
        "project": pick(PROJECT_NAMES),
        "team": pick(TEAMS),
        "stakeholder": pick(STAKEHOLDERS),
        "topic": pick(TOPICS),
        "month": pick(MONTHS),
        "day": pick(DAYS),
        "day2": pick(DAYS),
        "time": pick(TIMES),
        "time2": pick(TIMES),
        "date": f"{pick(MONTHS)} {random.randint(1, 28)}",
        "qn": random.randint(1, 4),
        "vn": random.randint(2, 8),
        "N": random.randint(3, 24),
        "ref_id": ref_id(),
        "domain": domain,
    }


def fill(template: str, ctx: dict) -> str:
    def repl(m):
        key = m.group(1)
        return str(ctx.get(key, m.group(0)))
    return PLACEHOLDER_RE.sub(repl, template)


# ------------------------------------------------------------------------------------
# Quality gate
# ------------------------------------------------------------------------------------

SENDER_DOMAIN_RE = re.compile(r"<[^@]+@([^>]+)>")
URL_SHORTENERS = ["bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly", "is.gd", "buff.ly"]
TYPOSQUAT_PATTERNS = [
    "paypa1", "amaz0n", "g00gle", "githu8", "microsft", "lnkedin", "yt0be",
    "faceb00k", "paypai",
]
DIGIT_IN_DOMAIN = re.compile(r"[a-z][0-9][a-z]|[a-z][0-9]{2,}[a-z]")
URGENCY_PHRASES = [
    "click here to verify", "urgent action required", "your access will be suspended",
    "account suspended", "verify your account immediately", "verify immediately",
    "click now or lose access", "confirm your password", "enter your password",
    "reset your password now",
]
# section 3.4: internal links only. These external link patterns imply suspicion.
SUSPICIOUS_URL_PATTERNS = [
    "http://", "bit.ly", "tinyurl", "t.co/",
]


def sender_domain(s):
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


def passes_checks(row: dict) -> bool:
    sender = row["sender"]
    subject = row["subject"]
    body = row["body"]
    blob = f"{sender}\n{subject}\n{body}".lower()

    if len(body.strip()) < 10:
        return False

    wc = len(body.split())
    # spec: medium 50-150 words
    if wc < 50 or wc > 155:
        return False

    for pat in TYPOSQUAT_PATTERNS:
        if pat in blob:
            return False

    if DIGIT_IN_DOMAIN.search(sender_domain(sender)):
        return False

    for sh in URL_SHORTENERS:
        if sh in blob:
            return False

    for phrase in URGENCY_PHRASES:
        if phrase in blob:
            return False

    for pat in SUSPICIOUS_URL_PATTERNS:
        if pat in blob:
            return False

    # Must reference real-sounding internal context in the BODY itself:
    # either a project noun, an internal link fragment, or a day/time reference.
    body_lower = body.lower()
    project_lower = [p.lower() for p in PROJECT_NAMES]
    has_project = any(p in body_lower for p in project_lower)
    has_internal_link = any(
        token in body_lower for token in ["confluence", "sharepoint", "docs.google.com", "jira"]
    )
    has_day_or_time = any(d.lower() in body_lower for d in DAYS) or any(
        t.lower() in body_lower for t in TIMES
    )
    has_context = has_project or has_internal_link or has_day_or_time
    if not has_context:
        return False

    return True


# ------------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------------

def generate():
    from collections import Counter
    rows: list[dict] = []
    seen: set[str] = set()
    template_use: Counter = Counter()

    for sender_type, subtype, count in PLAN:
        if (sender_type, subtype) not in BODIES:
            raise KeyError(f"Missing body bank for {(sender_type, subtype)}")
        subjects = SUBJECTS[subtype]
        bodies = BODIES[(sender_type, subtype)]
        produced = 0
        attempts = 0
        max_attempts = count * 80
        while produced < count and attempts < max_attempts:
            attempts += 1
            sender, first, domain = make_sender(sender_type)
            subj_tpl = pick(subjects)
            body_tpl = pick(bodies)
            key = (sender_type, subtype, subj_tpl, body_tpl)
            if template_use[key] >= 5:
                continue
            ctx = build_ctx(first, domain)
            subject = fill(subj_tpl, ctx)
            body = fill(body_tpl, ctx)
            row = {
                "sender": sender,
                "subject": subject,
                "body": body,
                "label": 0,
                "category": "professional_internal",
            }
            h = hashlib.sha1(f"{sender}\n{subject}\n{body}".encode()).hexdigest()
            if h in seen:
                continue
            if not passes_checks(row):
                continue
            rows.append(row)
            seen.add(h)
            template_use[key] += 1
            produced += 1
        if produced < count:
            raise RuntimeError(
                f"Only produced {produced}/{count} for ({sender_type}, {subtype}) in {attempts} attempts"
            )
    assert len(rows) == 800
    return rows


def main():
    rows = generate()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["sender", "subject", "body", "label", "category"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
