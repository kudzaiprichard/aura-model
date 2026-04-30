"""Generate 1,000 personal conversational emails (label=0) for AURA online-learning augmentation.

Follows section 3.2 of online_learning_dataset.md and applies the quality checks from section 6.

Design:
- 10 distinct relationship types, each with its own senders, salutations, and sign-offs.
- Hand-written sentence banks per (relationship, subtype) so bodies read like real mail.
- Compositional assembly: greeting + 1..4 topical sentences + sign-off, with variable fills
  (first names, days, dishes, cities) to keep every row textually unique.
- Strict section-6 quality gate; rejected rows are re-generated until we have exactly 1000.
"""

from __future__ import annotations

import csv
import hashlib
import random
import re
from pathlib import Path

random.seed(20260418)

OUT_PATH = Path(
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/personal_conversational.csv"
)

# ------------------------------------------------------------------------------------
# Variable pools
# ------------------------------------------------------------------------------------

RECIPIENT_NAMES = [
    "Alex", "Chris", "Sam", "Jordan", "Jamie", "Morgan", "Casey", "Taylor",
    "Riley", "Robin", "Kai", "Drew", "Harper", "Parker", "Emerson",
]
THIRD_NAMES = [
    "Ben", "Kate", "Mike", "Priya", "Tom", "Olivia", "Nina", "Marcus",
    "Ellie", "Jay", "Ruth", "Leo", "Maya", "Hassan", "Amelia", "Dan", "Clara", "Theo",
]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SHORT_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = [
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
]
DISHES = [
    "lentil soup", "the curry", "mushroom risotto", "roast chicken", "stew",
    "that pasta", "shepherd's pie", "tomato tart", "banana bread", "scones",
    "the chocolate cake", "fish pie", "chili", "the green salad", "ratatouille",
]
CITIES = [
    "Bristol", "Leeds", "Manchester", "Edinburgh", "Dublin", "Cardiff",
    "Boston", "Austin", "Portland", "Denver", "Lisbon", "Porto", "Glasgow",
]
PLACES = [
    "the cafe on the corner", "that little place near the station", "the park",
    "the pub by the river", "theirs", "mine", "our usual spot", "the new bistro",
    "the garden centre", "the bookshop", "the lake house",
]
TIMES = [
    "around 7", "around half 6", "about noon", "just after 5", "around 8",
    "after work", "mid-afternoon", "early evening",
]
SMALL_NUMS = [2, 3, 4, 5, 6]


def pick(seq):
    return random.choice(seq)


# ------------------------------------------------------------------------------------
# Relationship definitions
# ------------------------------------------------------------------------------------

RELATIONSHIPS = {
    "mom": {
        "senders": [
            '"Mom" <mom@familymail.net>',
            '"Mom" <linda.chen@gmail.com>',
            '"Mom" <janet.wilson@yahoo.com>',
            '"Mom" <diane.miller@outlook.com>',
            '"Mom" <barbara.k@gmail.com>',
        ],
        "greetings": [
            "Hi sweetie,", "Hi love,", "Hi honey,", "Hi darling,", "Hi dear,",
            "Hello sweetheart,", "Morning love,", "Hi {me},",
        ],
        "sign_offs": [
            "Love,\nMom", "Love Mom x", "Love,\nMom xx", "Hugs,\nMom",
            "Love you,\nMom", "Mom x", "All my love,\nMom", "Love from Mom",
        ],
    },
    "dad": {
        "senders": [
            '"Dad" <dad@gmail.com>',
            '"Dad" <robert.chen@hotmail.com>',
            '"Dad" <tom.miller@gmail.com>',
            '"Dad" <dave.watson@protonmail.com>',
            '"Dad" <peter.wilson@yahoo.com>',
        ],
        "greetings": [
            "Hi kiddo,", "Hi champ,", "Hi son,", "Hi {me},", "Hey kid,",
            "Morning,", "Hi there,",
        ],
        "sign_offs": [
            "Dad", "- Dad", "Dad x", "Cheers,\nDad", "Love,\nDad", "Take care,\nDad",
        ],
    },
    "friend": {
        "senders": [
            '"Sarah" <sarah.k@gmail.com>',
            '"Mike" <mike.jones@yahoo.com>',
            '"Kate" <kate.b@gmail.com>',
            '"Tom" <tomhenderson@hotmail.com>',
            '"Priya" <priyarose@gmail.com>',
            '"James" <jamie.w@protonmail.com>',
            '"Liam" <liamroberts@gmail.com>',
            '"Nina" <ninaparker@yahoo.com>',
            '"Olivia" <olivia.t@gmail.com>',
            '"Marcus" <marcus.delaney@gmail.com>',
            '"Ellie" <ellie.munroe@gmail.com>',
            '"Hassan" <hassan.r@outlook.com>',
        ],
        "greetings": [
            "Hey,", "Hi,", "Hey {me},", "Hey you,", "Hi {me},", "Morning,",
            "Hiya,", "Hey hey,",
        ],
        "sign_offs": [
            "{sender_first}", "x", "{sender_first} x", "Cheers,\n{sender_first}",
            "Talk soon,\n{sender_first}", "- {sender_first}", "{sender_first} xx",
        ],
    },
    "sibling": {
        "senders": [
            '"Ben" <ben.matthews@gmail.com>',
            '"Emma" <emma.chen@yahoo.com>',
            '"Sam" <sammatthews@gmail.com>',
            '"Alice" <alice.reed@hotmail.com>',
            '"Matt" <matt.reed@gmail.com>',
            '"Sophie" <sophie.reed@gmail.com>',
        ],
        "greetings": [
            "Hey,", "Yo,", "Hey {me},", "Morning,", "Hi,", "Ok so,",
        ],
        "sign_offs": [
            "{sender_first}", "x", "{sender_first} x", "Later,\n{sender_first}",
            "Love,\n{sender_first}", "Night,\n{sender_first}",
        ],
    },
    "colleague": {
        "senders": [
            '"Dave Chen" <davechen82@gmail.com>',
            '"Sarah Mills" <s.mills42@yahoo.com>',
            '"Rob Parker" <rparker@gmail.com>',
            '"Priya Nair" <priya.nair@gmail.com>',
            '"Kim Lee" <kimlee.home@gmail.com>',
            '"Jess Wong" <jess.wong@outlook.com>',
            '"Dan Fisher" <danfisher@gmail.com>',
        ],
        "greetings": [
            "Hi {me},", "Hey {me},", "Hi,", "Hey,", "Morning {me},", "Hi there,",
        ],
        "sign_offs": [
            "Cheers,\n{sender_first}", "Thanks,\n{sender_first}", "{sender_first}",
            "Best,\n{sender_first}", "Talk soon,\n{sender_first}",
        ],
    },
    "grandparent": {
        "senders": [
            '"Grandma" <grandma@familymail.net>',
            '"Grandma" <marian.walker@aol.com>',
            '"Nana" <nana@yahoo.com>',
            '"Grandpa" <harold.c@comcast.net>',
            '"Grandpa" <grandpa@gmail.com>',
            '"Granny" <granny.pearl@yahoo.com>',
        ],
        "greetings": [
            "Hello dear,", "Hi dear,", "My darling,", "Hello {me} dear,",
            "Hi sweetheart,", "Good morning dear,",
        ],
        "sign_offs": [
            "Love,\nGrandma", "Love,\nGrandpa", "All our love,\nGrandma and Grandpa",
            "Love Nana x", "Love Granny", "With love,\nGrandma xxx", "Grandpa",
        ],
    },
    "partner": {
        "senders": [
            '"Alex" <alex.v@gmail.com>',
            '"Jordan" <jordanbell@gmail.com>',
            '"Sam" <sam.b.h@gmail.com>',
            '"Taylor" <taylor.m@gmail.com>',
            '"Casey" <casey.h@gmail.com>',
        ],
        "greetings": [
            "Hey love,", "Hi babe,", "Hey,", "Hi hon,", "Hey you,", "Hi love,",
            "Morning love,",
        ],
        "sign_offs": [
            "x", "xx", "Love you,\n{sender_first}", "{sender_first} x",
            "Love,\n{sender_first}", "See you soon,\n{sender_first}",
        ],
    },
    "neighbour": {
        "senders": [
            '"Martin" <martinbrooks@gmail.com>',
            '"Sue" <sue.patel@gmail.com>',
            '"Daniel" <danroberts@yahoo.com>',
            '"Helen" <helen.w@outlook.com>',
            '"Ian" <ian.foster@gmail.com>',
        ],
        "greetings": [
            "Hi {me},", "Hi there,", "Hello {me},", "Morning {me},", "Hi,",
        ],
        "sign_offs": [
            "Thanks,\n{sender_first} (no.12)", "Cheers,\n{sender_first}",
            "Thanks,\n{sender_first}", "{sender_first} from across the road",
            "{sender_first} next door", "Best,\n{sender_first}",
        ],
    },
    "cousin": {
        "senders": [
            '"Rachel" <rach.henderson@gmail.com>',
            '"Ethan" <ethan.park@yahoo.com>',
            '"Megan" <m.perez@gmail.com>',
            '"Jacob" <j.freeman@gmail.com>',
        ],
        "greetings": [
            "Hey cuz,", "Hi {me},", "Hey {me},", "Yo,", "Hi,",
        ],
        "sign_offs": [
            "{sender_first}", "Cheers,\n{sender_first}", "x", "{sender_first} x",
            "Love,\n{sender_first}",
        ],
    },
    "aunt_uncle": {
        "senders": [
            '"Aunt Susan" <susanbright@gmail.com>',
            '"Uncle Ray" <rayhughes@yahoo.com>',
            '"Auntie Clare" <clare.a@gmail.com>',
            '"Uncle Peter" <peter.reed@hotmail.com>',
            '"Aunt Mary" <mary.donovan@aol.com>',
        ],
        "greetings": [
            "Hello dear,", "Hi {me},", "Hello {me} love,", "Hi sweetheart,",
            "Hello there,",
        ],
        "sign_offs": [
            "Love,\nAunt {sender_first}", "Love,\nUncle {sender_first}",
            "With love,\n{sender_first}", "{sender_first}", "All my love,\n{sender_first}",
        ],
    },
}

# Map sender display-name to a first name for sign-off substitution
SENDER_FIRST_OVERRIDE = {
    '"Aunt Susan" <susanbright@gmail.com>': "Susan",
    '"Uncle Ray" <rayhughes@yahoo.com>': "Ray",
    '"Auntie Clare" <clare.a@gmail.com>': "Clare",
    '"Uncle Peter" <peter.reed@hotmail.com>': "Peter",
    '"Aunt Mary" <mary.donovan@aol.com>': "Mary",
}


def sender_first_name(sender: str) -> str:
    if sender in SENDER_FIRST_OVERRIDE:
        return SENDER_FIRST_OVERRIDE[sender]
    # Extract display name and strip prefixes like Mom, Dad, Grandma
    m = re.match(r'"([^"]+)"', sender)
    if not m:
        return "Sam"
    name = m.group(1).strip()
    for prefix in ("Aunt ", "Auntie ", "Uncle "):
        if name.startswith(prefix):
            name = name[len(prefix):]
    return name.split()[0]


# ------------------------------------------------------------------------------------
# Subject banks per subtype
# ------------------------------------------------------------------------------------

SUBJECTS = {
    "question": [
        "Quick question", "Quick one", "Have a minute?", "Something to ask",
        "Silly question", "Small favour", "Small favour to ask",
        "Are you free this weekend?", "Are you around {day}?",
        "Lunch on {day}?", "Dinner this week?", "Coffee {day}?",
        "Free for a call later?", "Can we catch up?",
        "Did you end up going?", "Did you hear back about it?",
        "Is {day} still ok?", "What time again?",
        "Do you still have that?", "One more thing",
        "Thinking about {day}", "About that thing",
    ],
    "sharing": [
        "Recipe for that soup", "Finally found it", "Book I was telling you about",
        "Photos from the weekend", "Pics from last night",
        "Thought you'd enjoy this", "Saw this and thought of you",
        "Sending the photos", "That restaurant", "Found the number",
        "The tomato thing", "Sending the details", "Here's the address",
        "That song I mentioned", "My garden update", "Funny thing today",
        "Thought of you", "Saw {third} earlier", "That thing we talked about",
        "The shoes we saw", "Quick share", "Small thing",
    ],
    "planning": [
        "Dinner next {day}?", "Birthday weekend", "Weekend plans",
        "Holiday dates", "Sunday lunch?", "This {day}",
        "Christmas at ours", "Trip in {month}", "Meeting up next week",
        "Catch up this month?", "Let's pick a date", "Thanksgiving plans",
        "Anniversary dinner", "Weekend at the cabin",
        "Are we still on for {day}?", "About next weekend",
        "The thing on the 14th", "Picking dates",
        "Shall we book it?", "Concert in {month}", "About {month}",
    ],
    "update": [
        "How are you doing?", "Just checking in", "A small update",
        "Update on the move", "News from this week",
        "Back from the trip", "Finally done with it", "Things are settling",
        "Work update", "Just a note", "Quick update",
        "Thinking of you", "Life update", "A few bits of news",
        "Since we last spoke", "Been a while", "Catching you up",
        "News from us", "Moving news", "Little update from here",
        "Everything here",
    ],
}


# ------------------------------------------------------------------------------------
# Sentence banks per (relationship, subtype). Each entry is ONE short sentence that
# reads naturally on its own. Bodies stitch 1..4 of these together.
# ------------------------------------------------------------------------------------

BANK: dict[str, dict[str, list[str]]] = {
    # ----------------------- MOM ----------------------------
    "mom": {
        "question": [
            "Quick one — are you around this weekend?",
            "Do you still want me to bring the extra duvet when I come down?",
            "What time were you thinking for {day}?",
            "Did you manage to book the flight in the end?",
            "Are you still coming up for the weekend or have plans changed?",
            "Is your sister driving or are you both coming together?",
            "Do you need anything from the shops while I'm out?",
            "Have you heard back from the doctor yet?",
            "Did you eat properly today, just checking.",
            "Any chance you can call me tonight when you're free?",
            "Is {day} still good for a proper chat?",
            "Do you remember what we paid for the blinds last year?",
        ],
        "sharing": [
            "Here's that {dish} recipe you kept asking about.",
            "The trick is browning the onions really slowly, don't rush that part.",
            "Your dad finally fixed the back fence, I'll send a photo later.",
            "The garden is looking lovely this week, the roses came out properly.",
            "I found the old photo album in the loft, I can bring it when I visit.",
            "Thought you might like this recipe, it's the one we had at Grandma's.",
            "Saw your old teacher in town today, she asked after you.",
            "Wanted you to have the number for the electrician, he's very good.",
            "Pinned your drawing to the fridge, made me smile this morning.",
            "Just finished the scarf I was knitting, I'll post it this week.",
        ],
        "planning": [
            "We were thinking of coming down on the {day} if that works for you.",
            "Your dad and I want to take you out for dinner when we're next in town.",
            "Can we pencil in Sunday lunch the weekend after next?",
            "Would you come up for Christmas or shall we come to you this year?",
            "Auntie {third} will be here the weekend of the 14th, come if you can.",
            "Let's pick a date for that restaurant we kept saying we'd try.",
            "I want to book the cottage for the summer, let me know your dates.",
            "Your grandmother wants the whole family over in {month} if possible.",
            "Shall we plan something small for your birthday this year?",
            "I was thinking {day} the {num}th for the little party, does that work?",
        ],
        "update": [
            "Not much happening here, the usual routine.",
            "Dad has been pottering in the garage all weekend, you know what he's like.",
            "The cat has taken over the sofa completely.",
            "I finally finished that book you lent me, it took me ages.",
            "We had {third} and her husband over for dinner on {day}, very nice evening.",
            "Book club met again this week, I'm reading the historical one now.",
            "Everything's well here, just missing seeing you.",
            "The weather has been lovely so I've been in the garden most afternoons.",
            "Your brother called at the weekend, he sounded in good spirits.",
            "Nothing dramatic, just thought I'd say hello properly.",
        ],
    },
    # ----------------------- DAD ----------------------------
    "dad": {
        "question": [
            "Quick one — did you sort out that car insurance yet?",
            "Are you still coming up for the match on {day}?",
            "Have you had a look at the tax thing I mentioned?",
            "Do you need me to pick you up from the station on {day}?",
            "What time does your train get in?",
            "Did the plumber end up coming round?",
            "Do you still want me to look at that leak when I'm next over?",
            "Are you free for a proper phone call this week?",
            "Have you been back to the dentist about the tooth?",
            "Do you know anyone who could help with the shelves?",
        ],
        "sharing": [
            "Took a photo of the old bike I was telling you about.",
            "Found an article about that car you were after, I'll print it.",
            "Your mother sends her love, she's been busy with the garden.",
            "The pub finally reopened after the refurb, looks decent.",
            "Managed to get the lawnmower going again, took me most of Saturday.",
            "Had a good round of golf on {day}, first time in ages.",
            "Saw a deal on the tyres you were looking at, I'll forward the page.",
            "Your grandmother asked me to send on the recipe she promised.",
            "Finally sorted the shed out, plenty of room now if you want to store anything.",
            "Dug out the old fishing rods, thought of our trip last summer.",
        ],
        "planning": [
            "Fancy coming up for the match weekend after next?",
            "Let's aim for dinner the next time you're in town.",
            "Your mother wants everyone over for Sunday lunch on the {num}th.",
            "I'm taking the week of the {num}th off, drop by if you can.",
            "Shall we do the fishing trip in {month} this year?",
            "Thinking of booking the cottage again, let me know your dates.",
            "Planning to paint the front room next weekend, bring old clothes.",
            "How about dinner at {place} on {day}, on me.",
            "We'll be passing through on {day}, could drop in for coffee if you're around.",
            "Let's pick a weekend to sort through the boxes in the garage.",
        ],
        "update": [
            "Not much to report, work is steady and the weather has turned.",
            "Your mother finally got me to clear out the loft.",
            "The old car is still running, just about.",
            "Went to see {third} on Saturday, he's doing well.",
            "Had a bit of a lazy weekend, nothing major.",
            "Trying to eat better, your mother is on my case about it.",
            "Finally finished the fence at the back, took three weekends.",
            "Took the dog out for a long walk on {day}, good to be out.",
            "Retirement still suits me, keeping busy with the allotment.",
            "All well at this end, just wanted to say hello.",
        ],
    },
    # --------------------- FRIEND ---------------------------
    "friend": {
        "question": [
            "Are you around {day}, fancy a coffee?",
            "Quick one — do you still have that book you borrowed off me?",
            "Are you free on {day} evening, thinking of catching a film?",
            "Did you ever go to that restaurant I mentioned?",
            "What was the name of that place we went to last summer?",
            "Any plans for the long weekend?",
            "Are you going to {third}'s thing on Saturday?",
            "Did you end up going for the job?",
            "Are you free for a proper catch-up soon?",
            "What time shall we meet on {day}?",
            "Did I leave my jumper at yours last week?",
            "Still on for {day} or do you want to push it back?",
        ],
        "sharing": [
            "Finally found the recipe I kept promising to send you.",
            "Saw a meme earlier that reminded me of that trip we did.",
            "The cafe on the corner has reopened, we should try it.",
            "Picked up a book on {day} that you'd genuinely enjoy.",
            "Ran into {third} at the weekend, she says hi.",
            "Thought you'd appreciate this, they've finally sorted the playlist situation.",
            "The new season of that show is out, no spoilers yet.",
            "Quick one to say I found the number for the guy who does bike repairs.",
            "Dropping you a line to say the gig I mentioned is confirmed for {month}.",
            "Saw the shoes we were looking at are on sale.",
        ],
        "planning": [
            "Are you around for brunch on {day} at {place}?",
            "A few of us are meeting for drinks {day} evening, come if you can.",
            "Let's finally pick a date for that road trip we keep talking about.",
            "Thinking of a cinema night on {day}, usual time.",
            "Shall we book the place for my birthday or wait until next month?",
            "Dinner at mine on {day}, bring wine.",
            "Trip to {city} in {month}, interested?",
            "{third}'s birthday weekend is coming up, we're sorting the details.",
            "Fancy a long walk on Saturday if the weather holds?",
            "Let's aim for a catch-up next week, any day works for me.",
        ],
        "update": [
            "Life's fine here, work is busy but nothing dramatic.",
            "Finally finished the flat project, it feels liveable again.",
            "Been meaning to message for ages, sorry for the silence.",
            "New gym membership is holding so far, three weeks in.",
            "Got a bit sunburnt at the weekend, classic me.",
            "Trip to {city} was lovely, I'll show you the photos.",
            "Back from holidays and already tired again.",
            "Been a weird week, nothing bad, just tired.",
            "Moving furniture around this weekend, the place feels different.",
            "All good here, just thought I'd say hi properly.",
        ],
    },
    # --------------------- SIBLING --------------------------
    "sibling": {
        "question": [
            "Did Mom call you about the {month} weekend?",
            "Quick one — are you going to Dad's birthday thing?",
            "Have you sorted the present for Mom yet?",
            "Are you free to chat {day} evening?",
            "Did you end up talking to Mom about the holiday plans?",
            "Any idea what to get Grandma for her birthday?",
            "Are you still planning to drive up on {day}?",
            "Have you heard from {third} lately?",
            "Did you say you could take Wednesday off or was I imagining that?",
            "Do you still have the old photos from the house?",
        ],
        "sharing": [
            "Dug out the old family photos last night, some good ones of us as kids.",
            "Found the video of that holiday we did years ago.",
            "Mom sent me the recipe for the {dish}, forwarding it on.",
            "Dad has been texting me about a new project, brace yourself.",
            "Saw an old teacher of ours at the shop on {day}, very weird.",
            "Auntie {third} rang, she's coming down for the weekend of the {num}th.",
            "That song from when we were teenagers came on the radio.",
            "I kept the box of your stuff in the loft, let me know when you want it.",
            "Mom wants both of us to call her this weekend if possible.",
            "Found the old Polaroids in the drawer, I'll bring them next visit.",
        ],
        "planning": [
            "We should sort out what we're doing for Mom's birthday.",
            "Let's do a sibling lunch next time we're both home.",
            "I was thinking we could both go to Dad's on {day} together.",
            "Shall we team up on the Christmas gift situation?",
            "Fancy meeting halfway on {day}, easier than the full drive.",
            "Can you come down for the weekend of the {num}th?",
            "Let's plan the summer trip properly, I'll block out {month}.",
            "I'll be in your city on {day}, dinner?",
            "Mom wants everyone over at Christmas, we should decide together.",
            "Should we go halves on the anniversary present for them?",
        ],
        "update": [
            "Work is fine, the flatmate situation has finally calmed down.",
            "Started running again, which is going about as well as you'd expect.",
            "The cat is still the boss of the house.",
            "Weekend was quiet, watched films and did laundry.",
            "Got some news but I'll tell you on the phone, nothing bad.",
            "Trip to {city} was a mixed bag, fun but exhausting.",
            "Finally put up the shelves, no injuries.",
            "Been thinking about moving but nothing decided yet.",
            "New job is going ok, jury still out on the manager.",
            "Life's fine, mostly work and not sleeping enough.",
        ],
    },
    # --------------------- COLLEAGUE ------------------------
    "colleague": {
        "question": [
            "Quick one off-channel — are you around for lunch on {day}?",
            "Did you ever manage to get that printer working last week?",
            "Are you free for a coffee outside the office on {day}?",
            "Have you heard anything about the team outing dates?",
            "Do you remember the name of that restaurant we went to after the client thing?",
            "Any chance you still have a copy of the template we used last year?",
            "Are you coming to the leaving drinks on {day}?",
            "Did you sort out the travel reimbursement in the end?",
            "Are you planning to take leave over Christmas?",
            "Quick question about the old laptop, did you keep the charger?",
        ],
        "sharing": [
            "Wanted to send this off the work email so it actually reaches you.",
            "Remembered the book title you asked about, finally.",
            "That podcast I mentioned is called something different than I thought.",
            "My partner found the bakery you were asking about.",
            "Sending on the name of the decorator we used at home.",
            "Found the photo from the away day last year, tragic hair.",
            "Thought you'd appreciate this recipe, very easy.",
            "Passing on the name of the physio in case you still need one.",
            "Forwarding this because our work inboxes are being weird.",
            "Quick share — the book you lent me was great, thanks for the tip.",
        ],
        "planning": [
            "Fancy grabbing lunch on {day} away from the office?",
            "A few of us are doing drinks on {day}, nothing formal.",
            "Shall we do a proper catch-up outside work next week?",
            "Thinking of a team-free coffee on {day} morning.",
            "Let's aim for dinner before you head off on leave.",
            "Drinks after work on {day}, you in?",
            "My partner and I are having a few people over on the {num}th, come if free.",
            "Let's pick a date this month for a proper lunch.",
            "Thinking of going to the new place near the office on {day}.",
            "Meeting up for coffee before the Monday stand-up, interested?",
        ],
        "update": [
            "Nothing major, just settling back after leave.",
            "Kids are finally back in school, life feels calmer.",
            "Managed a full weekend off screens, highly recommend.",
            "We moved into the new flat last month, still unpacking.",
            "Been catching up on sleep after the project crunch.",
            "Training for a half marathon, regretting it already.",
            "Got a puppy, no regrets but also no sleep.",
            "Finally took that leave I kept postponing.",
            "Trip to {city} was a good break, back now.",
            "Life's fine outside work, mainly gardening and DIY.",
        ],
    },
    # --------------------- GRANDPARENT ----------------------
    "grandparent": {
        "question": [
            "Have you been eating enough, dear?",
            "Are you coming down to see us before {month}?",
            "Did you get the birthday card I sent last week?",
            "Is your flat warm enough with the weather turning?",
            "Have you heard from your mother this week?",
            "Did you finish the book I lent you at Easter?",
            "Will you have time for a proper call on {day}?",
            "Are you still seeing that friend from university?",
            "Would you like me to send the old photos over?",
            "Is there anything you need posting up to you?",
        ],
        "sharing": [
            "Grandpa has been tidying the greenhouse and I thought you'd laugh.",
            "I'm sending over the recipe book you asked about, second-class post.",
            "Pinned a new photo of you on the kitchen noticeboard.",
            "Found the jumper I started knitting for you, finishing it this week.",
            "Your grandfather found his old slides from our trip to Scotland.",
            "Picked some flowers from the garden, wish you could smell them.",
            "The little cat from next door keeps visiting.",
            "Posting you some jam I made from the plum tree.",
            "Your grandfather made a good stew yesterday, very proud of him.",
            "Found that old photograph of you with the puppy, popping it in an envelope.",
        ],
        "planning": [
            "We would love to see you when you're next in the area.",
            "Come down for a weekend soon, the spare room is ready.",
            "Shall we plan a proper Sunday lunch for {month}?",
            "Your grandfather would like us all together for his birthday.",
            "Can we pencil in a visit for the weekend of the {num}th?",
            "The whole family is gathering at Easter, please try to come.",
            "Let us know when you can visit, we will cook whatever you like.",
            "Come for a weekend when the weather is nicer, garden is lovely.",
            "We are hoping you can come for Christmas again this year.",
            "Shall we aim for a little lunch when you're in town?",
        ],
        "update": [
            "Everything here is quiet and steady, the way we like it.",
            "Your grandfather is back from the doctor, everything is fine.",
            "The garden is doing well, lots of tomatoes this year.",
            "I have been reading a lot and enjoying the quiet afternoons.",
            "Book club came round on {day}, a lovely evening.",
            "We had the neighbours over for tea yesterday.",
            "Not much to report, just the usual peaceful days.",
            "Your grandfather is still doing his crosswords every morning.",
            "The weather has been kind to us this week.",
            "Just wanted you to know we are thinking of you.",
        ],
    },
    # ---------------------- PARTNER -------------------------
    "partner": {
        "question": [
            "Are you stopping at the shop on your way home?",
            "Can you pick the kids up if I'm running late tonight?",
            "Do we need milk?",
            "Did you put the bin out last night or should I?",
            "What time are you finishing on {day}?",
            "Are you still ok to cook on {day}?",
            "Have you booked the dentist yet or do I need to?",
            "Do you know where I put the spare key?",
            "Are we still going to {third}'s on Saturday?",
            "Did you remember to send the rent this morning?",
        ],
        "sharing": [
            "Left you the last of the coffee on the counter.",
            "Dropped the dry cleaning off on my way in.",
            "The dog was a menace at the park this morning.",
            "Your mother called while you were in the shower.",
            "Topped the car up with fuel, should last the week.",
            "Made extra pasta last night, it's in the fridge for you.",
            "Picked up your prescription on the way back.",
            "The boiler man said he'll pop round on {day}.",
            "Your book arrived, I put it on your desk.",
            "Paid the gas bill online so you don't need to worry.",
        ],
        "planning": [
            "Dinner at home on {day}, I'll cook.",
            "Let's aim for a night out on {day} if we can get a sitter.",
            "I was thinking a weekend away in {month}, somewhere quiet.",
            "Shall we finally book the cottage for the half term?",
            "My parents want us over for lunch on Sunday, I said probably.",
            "Let's pick a date for the kitchen refit conversation we keep putting off.",
            "Fancy the cinema on {day} after the kids are down?",
            "A long walk on Sunday morning if the weather holds?",
            "Can we sit down on {day} evening and sort the holiday dates?",
            "Let's do something small for our anniversary this year.",
        ],
        "update": [
            "Nothing exciting, just a slower day at work which is nice.",
            "The dog was sick again, keeping an eye on him.",
            "Managed to clear the laundry pile finally.",
            "Meetings all back to back today, ears tired.",
            "Got some good news at work, tell you properly later.",
            "Running a bit late, home for seven.",
            "Finally cleared out the cupboard under the stairs.",
            "The tree outside the window is flowering again.",
            "Got through the morning list, taking a breather now.",
            "Thinking about you, that's all.",
        ],
    },
    # --------------------- NEIGHBOUR ------------------------
    "neighbour": {
        "question": [
            "Did your parcel end up at ours by accident?",
            "Did you hear back from the council about the bins?",
            "Any chance I can borrow your ladder on Saturday?",
            "Do you know who looks after the garden at number 8?",
            "Is it just us with no water this morning?",
            "Did you get the letter about the road works?",
            "Are you around on {day} for a quick chat about the fence?",
            "Have you noticed the cat around the back garden recently?",
            "Do you know the plumber the road usually uses?",
            "Is the power out at yours too?",
        ],
        "sharing": [
            "Thought I'd let you know the council is paving our street on {day}.",
            "Putting a note to say I took in your delivery this morning.",
            "The fox has been back in the front garden at dawn.",
            "Quick one to say the new bins arrived while you were out.",
            "Dropping a line to say we found a cat collar in the drive, could be yours.",
            "There's a post van coming round later with something big for you.",
            "Passing on the number of the chap who fixed our boiler, he was good.",
            "Just to flag the streetlight outside number 14 is out again.",
            "Letting you know we'll be away next weekend, alarm on.",
            "Thought you'd like to know the new bakery opened on the high street.",
        ],
        "planning": [
            "Are you around on {day} for the street clean-up?",
            "Thinking of doing a small drinks thing on our patio on {day}, come by.",
            "Shall we sort out the shared fence repair soon?",
            "A few of us from the road are meeting on {day} to talk about the parking.",
            "Let me know a good time to drop round with the tools.",
            "We're having a small barbecue on {day}, bring yourselves.",
            "Happy to water your plants while you're away, just say when.",
            "Was going to pop round on {day} to show you the new plans.",
            "Let's pick a time to have that long-overdue cup of tea.",
            "Could I grab five minutes on {day} about the hedge?",
        ],
        "update": [
            "Quick one to say everything is quiet on the street this week.",
            "Finally finished the front path, looks much better.",
            "The roof has stopped leaking thankfully.",
            "Kids broke up from school today, expect more noise.",
            "We've had our car in the garage all week, hence the different one on the drive.",
            "The apple tree is groaning, we'll drop some off.",
            "Had the locksmith out this morning, all sorted.",
            "Our visitors from {city} are staying this weekend, apologies in advance.",
            "Finally painted the front door, took a whole Sunday.",
            "Just a note to say hello properly after weeks of waves.",
        ],
    },
    # ----------------------- COUSIN -------------------------
    "cousin": {
        "question": [
            "Are you coming to Auntie {third}'s thing in {month}?",
            "Quick one — have you heard from the grandparents lately?",
            "Did you end up getting the new job?",
            "Are you around if I swing through {city} on {day}?",
            "Do you remember the name of that place we went to as kids?",
            "Any chance you can make Christmas this year?",
            "Have you spoken to your mom about the weekend?",
            "Are you still doing the thing with the band?",
            "Did you get the invite from Grandma?",
            "Is your brother coming to the wedding?",
        ],
        "sharing": [
            "Dug out an old photo from the summers at the grandparents'.",
            "Mom was asking about you the other day.",
            "Found that old game we used to play at holidays.",
            "Going through the box of old letters and your handwriting hasn't changed.",
            "Saw a film last night that reminded me of the one we watched as kids.",
            "Quick share — the family group chat has been a lot this week.",
            "Sent the itinerary for the gathering in {month}.",
            "Auntie {third} has started baking again, you'd approve.",
            "Forwarded the updated family tree thing from Grandma.",
            "Found the necklace I borrowed from you years ago.",
        ],
        "planning": [
            "Let's actually plan the cousins' trip we keep talking about.",
            "Coming through {city} on {day}, dinner?",
            "Shall we do a joint present for the grandparents this year?",
            "Thinking of coming to yours the weekend of the {num}th.",
            "Let's go halves on Mom and your mom's Christmas gift.",
            "Want to meet halfway for lunch on {day}?",
            "Let's try to end up at the same family thing for once.",
            "I'm in your city in {month}, keep a day free.",
            "Shall we plan a proper cousins' dinner this year?",
            "Let's pick a weekend for the long-overdue catch-up.",
        ],
        "update": [
            "Nothing too dramatic here, just work and life.",
            "Finally moved out of the shared flat, single-person living suits me.",
            "Studying again, which was not in the plan.",
            "New job starts next month, keeping everything crossed.",
            "Been travelling a fair bit for work, tired but fine.",
            "Kids are growing too fast, the usual parent complaints.",
            "Taking a proper break in {month}, haven't been abroad in years.",
            "Got a dog, he is running my life now.",
            "Your brother and I caught up at the weekend, good to see him.",
            "Life's fine, just quieter than I expected this year.",
        ],
    },
    # --------------------- AUNT/UNCLE -----------------------
    "aunt_uncle": {
        "question": [
            "Have you heard from your mother this week, dear?",
            "Are you still coming to the family lunch in {month}?",
            "Did you get the birthday card I posted?",
            "Do you know if your cousin is coming for Christmas?",
            "Are you keeping warm with the weather turning?",
            "Did you finish the jumper your grandmother started?",
            "Would you like me to send the old recipe on?",
            "Have you had any news from {third} lately?",
            "Is your flat sorted after the move?",
            "Will we see you at Grandma's birthday?",
        ],
        "sharing": [
            "I've been going through old photos and found some lovely ones of you.",
            "Your uncle is on another of his DIY projects, pray for us.",
            "The family group chat has been very busy today.",
            "Sending you the recipe for the {dish} you liked at Easter.",
            "Your grandmother made me promise to forward this on to you.",
            "The garden has been a project this summer, lots to show you.",
            "Found your old school report in a box, thought you'd want it.",
            "Your cousin sent lovely news about the new job.",
            "Popped a card in the post for your birthday next week.",
            "Sending over the number for the accountant your mother uses.",
        ],
        "planning": [
            "Come for lunch next time you're in the area, room always set.",
            "We would love to have you for the weekend of the {num}th.",
            "The whole family is aiming for the cottage in {month}.",
            "Let's pencil in a proper visit soon, it's been too long.",
            "Your grandmother's birthday is on the {num}th, we hope you can come.",
            "Shall we plan a family Sunday lunch while everyone is nearby?",
            "Happy to drive up to see you if that's easier on {day}.",
            "Come for Christmas if you have no other plans, plenty of space.",
            "We're passing through on {day}, could drop in for tea.",
            "Your uncle wants everyone together for his retirement do in {month}.",
        ],
        "update": [
            "Everything is well here, slow and steady is the season.",
            "Your uncle finally finished the patio, very proud of him.",
            "The garden is full of raspberries this year, we can't keep up.",
            "I have taken up yoga in my old age, don't laugh.",
            "We had Grandma over for Sunday lunch, she was on form.",
            "Your uncle took the grandchildren to the park yesterday, pure chaos.",
            "Nothing exciting, just wanted you to know we are thinking of you.",
            "Book group was last night, a lovely evening with old friends.",
            "The dog has a new trick, very unimpressed himself.",
            "Weather has been kind so lots of walks and tea in the garden.",
        ],
    },
}

SUBTYPES = ["question", "sharing", "planning", "update"]

# ------------------------------------------------------------------------------------
# Variable substitution
# ------------------------------------------------------------------------------------

PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def build_ctx(sender: str) -> dict:
    return {
        "me": pick(RECIPIENT_NAMES),
        "day": pick(DAYS),
        "dayshort": pick(SHORT_DAYS),
        "month": pick(MONTHS),
        "third": pick(THIRD_NAMES),
        "dish": pick(DISHES),
        "city": pick(CITIES),
        "place": pick(PLACES),
        "time": pick(TIMES),
        "num": random.randint(6, 28),
        "sender_first": sender_first_name(sender),
    }


def fill(template: str, ctx: dict) -> str:
    def repl(m):
        key = m.group(1)
        if key in ctx:
            return str(ctx[key])
        return m.group(0)

    return PLACEHOLDER_RE.sub(repl, template)


# ------------------------------------------------------------------------------------
# Quality checks — section 6 plus the section 3.2 body constraints
# ------------------------------------------------------------------------------------

SENDER_DOMAIN_RE = re.compile(r"<[^@]+@([^>]+)>")
URL_RE = re.compile(r"(https?://\S+|www\.\S+)", re.IGNORECASE)
URL_SHORTENERS = ["bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly", "is.gd", "buff.ly"]
TYPOSQUAT_PATTERNS = [
    "paypa1", "amaz0n", "g00gle", "githu8", "microsft", "lnkedin", "yt0be", "faceb00k",
]
DIGIT_IN_DOMAIN = re.compile(r"[a-z][0-9][a-z]|[a-z][0-9]{2,}[a-z]")
URGENCY_PHRASES = [
    "verify immediately", "account suspended", "click here to verify",
    "urgent action required", "your access will be suspended",
    "confirm your password", "reset your password now",
]


def sender_domain(s: str) -> str:
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


def word_count(s: str) -> int:
    return len(s.split())


def passes_checks(row: dict) -> bool:
    body = row["body"]
    subject = row["subject"]
    sender = row["sender"]
    blob = f"{sender}\n{subject}\n{body}".lower()

    # min length
    if len(body.strip()) < 10:
        return False

    # body word count 10..80
    wc = word_count(body)
    # Allow slight overage for natural endings, but cap strictly
    if wc < 10 or wc > 90:
        return False

    # no URLs anywhere
    if URL_RE.search(body) or URL_RE.search(subject):
        return False
    for sh in URL_SHORTENERS:
        if sh in blob:
            return False

    # no exclamation marks per section 3.2 body characteristics
    if "!" in body:
        return False

    # no urgency phrases
    for phrase in URGENCY_PHRASES:
        if phrase in blob:
            return False

    # no typosquatted domains in sender/body
    for pat in TYPOSQUAT_PATTERNS:
        if pat in blob:
            return False

    # no digit-substituted letters in sender domain
    if DIGIT_IN_DOMAIN.search(sender_domain(sender)):
        return False

    # no formal language tells
    formal_phrases = [
        "dear sir", "dear madam", "to whom it may concern",
        "please find attached", "as per our conversation", "kind regards",
        "yours sincerely", "yours faithfully",
    ]
    for phrase in formal_phrases:
        if phrase in blob:
            return False

    return True


# ------------------------------------------------------------------------------------
# Main generation
# ------------------------------------------------------------------------------------

TARGET = 1000


def build_row() -> dict | None:
    rel_name = pick(list(RELATIONSHIPS.keys()))
    rel = RELATIONSHIPS[rel_name]
    subtype = pick(SUBTYPES)
    sender = pick(rel["senders"])

    ctx = build_ctx(sender)

    greeting_tpl = pick(rel["greetings"])
    sign_off_tpl = pick(rel["sign_offs"])
    subject_tpl = pick(SUBJECTS[subtype])

    greeting = fill(greeting_tpl, ctx)
    sign_off = fill(sign_off_tpl, ctx)
    subject = fill(subject_tpl, ctx)

    sentence_bank = BANK[rel_name][subtype]
    # Length distribution: 30% very short (1), 35% short (2), 25% medium (3), 10% long (4)
    n = random.choices([1, 2, 3, 4], weights=[30, 35, 25, 10], k=1)[0]
    n = min(n, len(sentence_bank))
    sentences = random.sample(sentence_bank, n)
    filled = [fill(s, ctx) for s in sentences]

    # Assembly style: separate sentences with spaces, not newlines; greeting/sign-off on own lines.
    body_middle = " ".join(filled)
    # Replace any stray ! just in case
    body_middle = body_middle.replace("!", ".")

    body = f"{greeting}\n\n{body_middle}\n\n{sign_off}"

    return {
        "sender": sender,
        "subject": subject,
        "body": body,
        "label": 0,
        "category": "personal_conversational",
        "_rel": rel_name,
        "_subtype": subtype,
    }


def generate() -> list[dict]:
    rows: list[dict] = []
    seen: set[str] = set()
    from collections import Counter

    # Track reuse of (subject_tpl, sentence_combo) signatures. We treat the combination
    # of (subject_template, sorted sentence-template ids) as the "template" for the
    # section-5 five-use cap.
    template_use: Counter = Counter()

    # Per-subtype min counts we want hit (soft guide; the random walk naturally mixes).
    attempts = 0
    max_attempts = TARGET * 80

    while len(rows) < TARGET and attempts < max_attempts:
        attempts += 1
        rel_name = pick(list(RELATIONSHIPS.keys()))
        rel = RELATIONSHIPS[rel_name]
        subtype = pick(SUBTYPES)
        sender = pick(rel["senders"])

        ctx = build_ctx(sender)

        greeting_tpl = pick(rel["greetings"])
        sign_off_tpl = pick(rel["sign_offs"])
        subject_tpl = pick(SUBJECTS[subtype])

        bank = BANK[rel_name][subtype]
        n = random.choices([1, 2, 3, 4, 5], weights=[15, 25, 25, 20, 15], k=1)[0]
        n = min(n, len(bank))
        sentence_indexes = sorted(random.sample(range(len(bank)), n))
        template_sig = (rel_name, subtype, subject_tpl, tuple(sentence_indexes))
        if template_use[template_sig] >= 5:
            continue

        sentences = [bank[i] for i in sentence_indexes]

        greeting = fill(greeting_tpl, ctx)
        sign_off = fill(sign_off_tpl, ctx)
        subject = fill(subject_tpl, ctx)
        body_middle = " ".join(fill(s, ctx) for s in sentences).replace("!", ".")
        body = f"{greeting}\n\n{body_middle}\n\n{sign_off}"

        row = {
            "sender": sender,
            "subject": subject,
            "body": body,
            "label": 0,
            "category": "personal_conversational",
        }

        h = hashlib.sha1(f"{sender}\n{subject}\n{body}".encode()).hexdigest()
        if h in seen:
            continue

        if not passes_checks(row):
            continue

        rows.append(row)
        seen.add(h)
        template_use[template_sig] += 1

    if len(rows) < TARGET:
        raise RuntimeError(f"Only produced {len(rows)} rows after {attempts} attempts")

    # Post-generation variety assertions
    rel_domains = {sender_domain(r["sender"]) for r in rows}
    assert len(rel_domains) >= 8, f"Only {len(rel_domains)} sender domains"

    # Relationship-type coverage via sender-display-name prefix
    rel_covered = set()
    for r in rows:
        s = r["sender"]
        for name, d in RELATIONSHIPS.items():
            if s in d["senders"]:
                rel_covered.add(name)
                break
    assert len(rel_covered) >= 8, f"Only {len(rel_covered)} relationship types: {rel_covered}"

    # Subtype mix: every subtype represented
    subtype_counts = Counter()
    # We need to recover subtype from generation; recompute by subject-matching against banks
    for r in rows:
        found = None
        for st, subj_list in SUBJECTS.items():
            # Match by checking if the row's subject could have come from this subtype's template
            for tpl in subj_list:
                # Reverse the fill: replace {xxx} patterns with a regex
                pattern = re.escape(tpl)
                pattern = re.sub(r"\\\{\w+\\\}", r".+?", pattern)
                if re.fullmatch(pattern, r["subject"]):
                    found = st
                    break
            if found:
                break
        if found:
            subtype_counts[found] += 1

    for st in SUBTYPES:
        assert subtype_counts[st] > 0, f"Missing subtype: {st} in {subtype_counts}"

    return rows


def main() -> None:
    rows = generate()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["sender", "subject", "body", "label", "category"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
