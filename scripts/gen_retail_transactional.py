"""Generate 1,000 retail & transactional emails (label=0) for AURA online-learning augmentation.

Follows section 3.3 of online_learning_dataset.md and applies the quality checks from section 6.

Design:
- 25+ brands across 5 categories (e-commerce, food delivery, travel, finance, streaming).
- Subject and body banks per (brand-category, subtype) so copy matches the real brand flow.
- Every body includes an order / reference / transaction ID (enforced in quality gate).
- URLs are always bare-domain paths on the brand's own domain — no typosquatting, no shorteners.
- No password / credential / verification requests.
"""

from __future__ import annotations

import csv
import hashlib
import random
import re
from pathlib import Path

random.seed(20260418)

OUT_PATH = Path(
    r"C:/Users/Administrator/Documents/Projects/AURA - Adaptive User Risk Analyzer/AURA_Model/datasets/online_learning/retail_transactional.csv"
)

# ------------------------------------------------------------------------------------
# Variable pools
# ------------------------------------------------------------------------------------

FIRST_NAMES = [
    "Alex", "Jordan", "Sam", "Chris", "Taylor", "Morgan", "Riley", "Casey", "Avery",
    "Parker", "Quinn", "Rowan", "Drew", "Emerson", "Finley", "Harper", "Kai", "Logan",
    "Marlowe", "Noor", "Peyton", "Reese", "Sage", "Shea", "Blake", "Dakota", "Ellis",
    "Jamie", "Kendall", "Landon", "Micah", "Nico", "Phoenix", "River",
]

CITIES = [
    "London", "New York", "Paris", "Berlin", "Toronto", "Sydney", "Madrid", "Rome",
    "Amsterdam", "Dublin", "Lisbon", "Vienna", "Prague", "Oslo", "Stockholm", "Brussels",
    "Zurich", "Munich", "Seattle", "Austin", "Boston", "Denver", "Chicago", "Miami",
    "Portland", "Atlanta", "San Francisco", "Los Angeles", "Phoenix", "Dallas",
]

MONTHS = [
    "January", "February", "March", "April", "May", "June", "July", "August",
    "September", "October", "November", "December",
]
MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

FOOD_ITEMS = [
    "pad thai", "chicken tikka masala", "margherita pizza", "sushi platter",
    "cheeseburger", "pho", "ramen bowl", "vegetable biryani", "chicken shawarma",
    "burrito", "falafel wrap", "garlic naan", "spring rolls", "fish tacos",
]

TRAVEL_DESTINATIONS = [
    "Barcelona", "Tokyo", "Reykjavik", "Copenhagen", "Rome", "Lisbon",
    "Mexico City", "Bangkok", "Cape Town", "Istanbul", "Kyoto", "Marrakech",
]

PRODUCTS = [
    "wireless headphones", "kitchen scale", "running shoes", "coffee grinder",
    "desk lamp", "yoga mat", "stainless steel water bottle", "paperback novel",
    "cotton hoodie", "portable speaker", "notebook set", "indoor plant",
    "travel backpack", "winter scarf",
]


def pick(seq):
    return random.choice(seq)


def order_id():
    # Amazon-style hyphenated order numbers
    return f"{random.randint(100, 999)}-{random.randint(1000000, 9999999)}-{random.randint(1000000, 9999999)}"


def short_order_id():
    return f"#{random.randint(100000, 99999999)}"


def ref_id(prefix="REF"):
    return f"{prefix}-{random.randint(100000, 9999999)}"


def txn_id():
    return f"TXN{random.randint(1000000000, 9999999999)}"


def invoice_id():
    return f"INV-{random.randint(10000, 999999)}"


def confirmation_code():
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    return "".join(random.choice(letters) for _ in range(6))


def amount(lo=5, hi=420):
    return f"${random.randint(lo, hi)}.{random.randint(0, 99):02d}"


def masked_card():
    return f"ending in {random.randint(1000, 9999)}"


def flight_no():
    return f"{random.choice(['DL', 'UA', 'AA', 'BA', 'LH'])}{random.randint(100, 4999)}"


# ------------------------------------------------------------------------------------
# Brand catalogue — sender domains exactly match the brand. URL paths always live on
# the brand's own domain.
# ------------------------------------------------------------------------------------

BRANDS = {
    # ---------- e-commerce ----------
    "Amazon": {
        "category": "ecommerce",
        "senders": [
            '"Amazon.com" <auto-confirm@amazon.com>',
            '"Amazon.com" <shipment-tracking@amazon.com>',
            '"Amazon.com" <order-update@amazon.com>',
        ],
        "item": "order",
        "track_url": "amazon.com/gp/your-account/order-details",
        "receipt_url": "amazon.com/gp/your-account/orders",
        "account_url": "amazon.com/gp/your-account",
        "support_line": "Visit amazon.com/help for customer service.",
    },
    "eBay": {
        "category": "ecommerce",
        "senders": [
            '"eBay" <ebay@ebay.com>',
            '"eBay" <orders@ebay.com>',
        ],
        "item": "order",
        "track_url": "ebay.com/mye/myebay/purchase",
        "receipt_url": "ebay.com/mye/myebay/summary",
        "account_url": "ebay.com/mye/myebay/summary",
        "support_line": "Visit ebay.com/help for buyer support.",
    },
    "Etsy": {
        "category": "ecommerce",
        "senders": [
            '"Etsy" <transaction@etsy.com>',
            '"Etsy" <no-reply@etsy.com>',
        ],
        "item": "order",
        "track_url": "etsy.com/your/purchases",
        "receipt_url": "etsy.com/your/purchases",
        "account_url": "etsy.com/your/account",
        "support_line": "Visit help.etsy.com for assistance.",
    },
    "Walmart": {
        "category": "ecommerce",
        "senders": [
            '"Walmart" <help@walmart.com>',
            '"Walmart" <orders@walmart.com>',
        ],
        "item": "order",
        "track_url": "walmart.com/orders",
        "receipt_url": "walmart.com/orders",
        "account_url": "walmart.com/account",
        "support_line": "Visit walmart.com/help for customer service.",
    },
    "Target": {
        "category": "ecommerce",
        "senders": [
            '"Target" <orders@target.com>',
            '"Target" <TargetNews@em.target.com>',
        ],
        "item": "order",
        "track_url": "target.com/orders",
        "receipt_url": "target.com/orders",
        "account_url": "target.com/account",
        "support_line": "Visit target.com/help for support.",
    },
    "Best Buy": {
        "category": "ecommerce",
        "senders": [
            '"Best Buy" <BestBuyInfo@emailinfo.bestbuy.com>',
            '"Best Buy" <orders@bestbuy.com>',
        ],
        "item": "order",
        "track_url": "bestbuy.com/profile/ss/orders",
        "receipt_url": "bestbuy.com/profile/ss/orders",
        "account_url": "bestbuy.com/profile",
        "support_line": "Visit bestbuy.com/help for customer support.",
    },

    # ---------- food delivery ----------
    "Uber Eats": {
        "category": "food",
        "senders": [
            '"Uber Eats" <noreply@uber.com>',
            '"Uber Eats" <receipts@uber.com>',
        ],
        "item": "order",
        "track_url": "ubereats.com/orders",
        "receipt_url": "ubereats.com/orders",
        "account_url": "ubereats.com/account",
        "support_line": "Visit help.uber.com for support.",
    },
    "DoorDash": {
        "category": "food",
        "senders": [
            '"DoorDash" <no-reply@doordash.com>',
            '"DoorDash" <receipts@doordash.com>',
        ],
        "item": "order",
        "track_url": "doordash.com/orders",
        "receipt_url": "doordash.com/orders",
        "account_url": "doordash.com/account",
        "support_line": "Visit help.doordash.com for support.",
    },
    "Grubhub": {
        "category": "food",
        "senders": [
            '"Grubhub" <orders@grubhub.com>',
            '"Grubhub" <no-reply@grubhub.com>',
        ],
        "item": "order",
        "track_url": "grubhub.com/orders",
        "receipt_url": "grubhub.com/orders",
        "account_url": "grubhub.com/account",
        "support_line": "Visit grubhub.com/help for support.",
    },
    "Deliveroo": {
        "category": "food",
        "senders": [
            '"Deliveroo" <noreply@deliveroo.co.uk>',
            '"Deliveroo" <receipts@deliveroo.co.uk>',
        ],
        "item": "order",
        "track_url": "deliveroo.co.uk/orders",
        "receipt_url": "deliveroo.co.uk/orders",
        "account_url": "deliveroo.co.uk/account",
        "support_line": "Visit deliveroo.co.uk/help for support.",
    },
    "Just Eat": {
        "category": "food",
        "senders": [
            '"Just Eat" <orders@just-eat.co.uk>',
            '"Just Eat" <noreply@just-eat.co.uk>',
        ],
        "item": "order",
        "track_url": "just-eat.co.uk/orders",
        "receipt_url": "just-eat.co.uk/orders",
        "account_url": "just-eat.co.uk/account",
        "support_line": "Visit just-eat.co.uk/help for support.",
    },

    # ---------- travel ----------
    "Airbnb": {
        "category": "travel",
        "senders": [
            '"Airbnb" <automated@airbnb.com>',
            '"Airbnb" <noreply@airbnb.com>',
        ],
        "item": "reservation",
        "track_url": "airbnb.com/trips",
        "receipt_url": "airbnb.com/users/transaction_history",
        "account_url": "airbnb.com/account-settings",
        "support_line": "Visit airbnb.com/help for host and guest support.",
    },
    "Booking.com": {
        "category": "travel",
        "senders": [
            '"Booking.com" <noreply@booking.com>',
            '"Booking.com" <customer.service@booking.com>',
        ],
        "item": "booking",
        "track_url": "booking.com/mytrips",
        "receipt_url": "booking.com/mytrips",
        "account_url": "booking.com/myaccount",
        "support_line": "Visit booking.com/help for customer service.",
    },
    "Expedia": {
        "category": "travel",
        "senders": [
            '"Expedia" <itinerary@expedia.com>',
            '"Expedia" <travel@expedia.com>',
        ],
        "item": "trip",
        "track_url": "expedia.com/trips",
        "receipt_url": "expedia.com/trips",
        "account_url": "expedia.com/user/account",
        "support_line": "Visit expedia.com/help for assistance.",
    },
    "Delta Air Lines": {
        "category": "travel",
        "senders": [
            '"Delta Air Lines" <DeltaAirLines@delta.com>',
            '"Delta Air Lines" <receipts@delta.com>',
        ],
        "item": "flight",
        "track_url": "delta.com/mytrips",
        "receipt_url": "delta.com/receipts",
        "account_url": "delta.com/skymiles",
        "support_line": "Visit delta.com/help for support.",
    },
    "United Airlines": {
        "category": "travel",
        "senders": [
            '"United Airlines" <Receipts@united.com>',
            '"United Airlines" <unitedairlines@united.com>',
        ],
        "item": "flight",
        "track_url": "united.com/reservations",
        "receipt_url": "united.com/receipts",
        "account_url": "united.com/mileageplus",
        "support_line": "Visit united.com/help for support.",
    },

    # ---------- finance ----------
    "Bank of America": {
        "category": "finance",
        "senders": [
            '"Bank of America" <onlinebanking@ealerts.bankofamerica.com>',
            '"Bank of America" <alerts@bankofamerica.com>',
        ],
        "item": "transaction",
        "track_url": "bankofamerica.com/activity",
        "receipt_url": "bankofamerica.com/statements",
        "account_url": "bankofamerica.com/accounts",
        "support_line": "Visit bankofamerica.com/help for customer service.",
    },
    "Wells Fargo": {
        "category": "finance",
        "senders": [
            '"Wells Fargo" <alerts@notify.wellsfargo.com>',
            '"Wells Fargo" <online@wellsfargo.com>',
        ],
        "item": "transaction",
        "track_url": "wellsfargo.com/activity",
        "receipt_url": "wellsfargo.com/statements",
        "account_url": "wellsfargo.com/account-summary",
        "support_line": "Visit wellsfargo.com/help for support.",
    },
    "Citibank": {
        "category": "finance",
        "senders": [
            '"Citibank" <alerts@email.citibank.com>',
            '"Citi" <citi@citi.com>',
        ],
        "item": "transaction",
        "track_url": "citibank.com/activity",
        "receipt_url": "citibank.com/statements",
        "account_url": "citibank.com/accounts",
        "support_line": "Visit citibank.com/help for customer support.",
    },
    "Visa": {
        "category": "finance",
        "senders": [
            '"Visa" <alerts@visa.com>',
            '"Visa" <notification@visa.com>',
        ],
        "item": "transaction",
        "track_url": "visa.com/activity",
        "receipt_url": "visa.com/statements",
        "account_url": "visa.com/account",
        "support_line": "Visit visa.com/help for support.",
    },
    "Mastercard": {
        "category": "finance",
        "senders": [
            '"Mastercard" <customerservice@mastercard.com>',
            '"Mastercard" <alerts@mastercard.com>',
        ],
        "item": "transaction",
        "track_url": "mastercard.com/activity",
        "receipt_url": "mastercard.com/statements",
        "account_url": "mastercard.com/account",
        "support_line": "Visit mastercard.com/help for customer support.",
    },
    "American Express": {
        "category": "finance",
        "senders": [
            '"American Express" <AmericanExpress@welcome.aexp.com>',
            '"American Express" <alerts@aexp.com>',
        ],
        "item": "transaction",
        "track_url": "americanexpress.com/activity",
        "receipt_url": "americanexpress.com/statements",
        "account_url": "americanexpress.com/account",
        "support_line": "Visit americanexpress.com/help for support.",
    },

    # ---------- streaming ----------
    "Netflix": {
        "category": "streaming",
        "senders": [
            '"Netflix" <info@mailer.netflix.com>',
            '"Netflix" <billing@mailer.netflix.com>',
        ],
        "item": "subscription",
        "track_url": "netflix.com/youraccount",
        "receipt_url": "netflix.com/youraccount/billingactivity",
        "account_url": "netflix.com/youraccount",
        "support_line": "Visit help.netflix.com for support.",
    },
    "Spotify": {
        "category": "streaming",
        "senders": [
            '"Spotify" <no-reply@spotify.com>',
            '"Spotify" <receipts@spotify.com>',
        ],
        "item": "subscription",
        "track_url": "spotify.com/account/subscription",
        "receipt_url": "spotify.com/account/order-history",
        "account_url": "spotify.com/account",
        "support_line": "Visit support.spotify.com for help.",
    },
    "Hulu": {
        "category": "streaming",
        "senders": [
            '"Hulu" <hulu@hulumail.com>',
            '"Hulu" <billing@hulumail.com>',
        ],
        "item": "subscription",
        "track_url": "hulu.com/account/billing",
        "receipt_url": "hulu.com/account/billing",
        "account_url": "hulu.com/account",
        "support_line": "Visit help.hulu.com for support.",
    },
    "Disney+": {
        "category": "streaming",
        "senders": [
            '"Disney+" <disneyplus@mail.disneyplus.com>',
            '"Disney+" <billing@mail.disneyplus.com>',
        ],
        "item": "subscription",
        "track_url": "disneyplus.com/account/subscription",
        "receipt_url": "disneyplus.com/account/billing",
        "account_url": "disneyplus.com/account",
        "support_line": "Visit help.disneyplus.com for support.",
    },
    "Apple": {
        "category": "streaming",
        "senders": [
            '"Apple" <no_reply@email.apple.com>',
            '"Apple" <receipts@apple.com>',
        ],
        "item": "subscription",
        "track_url": "apple.com/account/subscriptions",
        "receipt_url": "apple.com/account/billing",
        "account_url": "appleid.apple.com",
        "support_line": "Visit support.apple.com for help.",
    },
}

# ------------------------------------------------------------------------------------
# Subject banks keyed by (brand_category, subtype)
# ------------------------------------------------------------------------------------

SUBJECTS = {
    ("ecommerce", "order_confirmation"): [
        "Your {brand} order {order_id} has been confirmed",
        "Order confirmed: {order_id}",
        "Thanks for your {brand} order — {short_order}",
        "Your {brand} order {short_order} has shipped",
        "{brand} order {short_order} is on its way",
        "Delivery update for order {short_order}",
        "Your {brand} order is out for delivery today",
        "Arriving today: {brand} order {short_order}",
        "Shipment confirmation for {brand} order {short_order}",
        "Your {brand} package has been delivered",
    ],
    ("food", "order_confirmation"): [
        "Your {brand} order {short_order} is confirmed",
        "{brand} order {short_order}: we're getting it ready",
        "Your {brand} courier is on the way — order {short_order}",
        "Your {brand} order is out for delivery",
        "Order {short_order} delivered — enjoy your meal",
        "{brand}: your food is almost there",
        "Your {brand} order from {restaurant} is on its way",
        "Thanks for ordering with {brand} — {short_order}",
    ],
    ("travel", "order_confirmation"): [
        "Your {brand} booking is confirmed — {conf_code}",
        "Reservation confirmed — {brand} — {conf_code}",
        "Your {brand} itinerary for {date}",
        "Booking confirmation — reference {conf_code}",
        "Your {brand} trip to {destination} is booked",
        "Flight confirmation — {flight_no} — {conf_code}",
        "Your {brand} stay in {destination} is confirmed",
        "Itinerary for your upcoming trip — {conf_code}",
    ],

    ("ecommerce", "receipt"): [
        "Receipt for your {brand} purchase — {short_order}",
        "Your {brand} receipt — {amount}",
        "{brand} invoice {invoice_id}",
        "Payment confirmed — {brand} — {short_order}",
        "Your {brand} order receipt — {short_order}",
    ],
    ("food", "receipt"): [
        "Your {brand} receipt for order {short_order}",
        "{brand} — payment confirmed — {amount}",
        "Receipt: {brand} order {short_order}",
        "Your {brand} order receipt — {amount}",
    ],
    ("travel", "receipt"): [
        "{brand} — payment receipt — {conf_code}",
        "Your {brand} booking receipt — {conf_code}",
        "Receipt for your {brand} reservation — {amount}",
        "{brand} payment confirmed — reference {conf_code}",
    ],
    ("streaming", "receipt"): [
        "Your {brand} receipt — {amount}",
        "Payment received — {brand} — {txn_id}",
        "{brand} — your subscription receipt",
        "Thanks for your {brand} payment — {txn_id}",
        "Your monthly {brand} receipt",
    ],
    ("finance", "receipt"): [
        "Payment received — {brand} — {txn_id}",
        "Your {brand} payment receipt — {amount}",
        "{brand} — transaction receipt {txn_id}",
        "Receipt for your {brand} payment on {date}",
        "{brand}: payment confirmation — {ref_id}",
        "Your {brand} card payment receipt",
    ],

    ("travel", "reminder"): [
        "Upcoming reservation — {brand} — {conf_code}",
        "Reminder: your {brand} trip on {date}",
        "Your {brand} stay starts in {N} days",
        "Reminder — check-in for your {brand} flight — {flight_no}",
        "Your upcoming {brand} reservation in {destination}",
        "{brand}: your trip is coming up",
    ],
    ("streaming", "reminder"): [
        "Your {brand} subscription renews in {N} days",
        "Reminder: {brand} renewal on {date}",
        "Your {brand} plan renews tomorrow",
        "Upcoming renewal — {brand} — {amount}",
        "{brand}: your next billing date",
        "Your {brand} membership renews on {date}",
    ],
    ("finance", "reminder"): [
        "Upcoming payment reminder — {brand}",
        "Reminder: your {brand} statement payment",
        "{brand}: payment due on {date}",
        "Your {brand} autopay will run on {date}",
        "Minimum payment reminder — {brand} — {ref_id}",
    ],
    ("ecommerce", "reminder"): [
        "Reminder: your {brand} delivery tomorrow",
        "Upcoming {brand} auto-reorder — {short_order}",
        "Your {brand} subscribe & save ships on {date}",
        "Reminder: {brand} pick-up ready — {short_order}",
    ],

    ("finance", "account_notification"): [
        "New transaction on your {brand} account",
        "{brand}: transaction notification — {txn_id}",
        "Your {brand} monthly statement is ready",
        "Balance update on your {brand} account",
        "Your {brand} statement for {month}",
        "Account alert: transaction authorised — {brand}",
        "Your {brand} account summary for {month}",
    ],
    ("streaming", "account_notification"): [
        "Your {brand} plan has been updated",
        "{brand}: payment method updated",
        "Your {brand} billing address was changed",
        "Account update — your {brand} plan",
        "Your {brand} subscription was updated on {date}",
    ],
    ("ecommerce", "account_notification"): [
        "Your {brand} monthly summary",
        "Activity on your {brand} account",
        "{brand}: your recent orders summary",
        "Your {brand} account statement for {month}",
    ],
    ("travel", "account_notification"): [
        "Your {brand} account activity for {month}",
        "{brand}: reward points summary",
        "Your {brand} travel summary for {month}",
        "Miles statement — {brand} — {month}",
    ],
}

# ------------------------------------------------------------------------------------
# Body banks keyed by (brand_category, subtype). Every template injects an ID.
# ------------------------------------------------------------------------------------

BODIES = {
    ("ecommerce", "order_confirmation"): [
        (
            "Hi {first},\n\nThanks for your {brand} order. We've received order {order_id} for {product} and "
            "the total charged to your card {card} was {amount}. We'll send another message when the package "
            "ships. You can view the full order details at {track_url}.\n\n{support_line}\n\nThe {brand} team"
        ),
        (
            "Hi {first},\n\nYour {brand} order {short_order} has shipped. The carrier picked up the package on "
            "{short_date} and it is expected to arrive on {short_date2}. Follow the tracking at {track_url} for "
            "live status updates.\n\nIf the address needs updating, please contact us before the parcel is out for "
            "delivery.\n\n{support_line}"
        ),
        (
            "Hello {first},\n\nGood news — your {brand} order {short_order} is out for delivery today. You'll "
            "receive a separate text when the driver is near. In the meantime you can follow the tracking at "
            "{track_url}. Total paid: {amount}, card {card}.\n\n{support_line}\n\nThanks for shopping with {brand}."
        ),
        (
            "Hi {first},\n\nYour {brand} package has been delivered. Order {order_id} was left at the address on "
            "file in {city}. If anything is missing or damaged, please report it within 48 hours at {track_url} so "
            "we can make it right.\n\n{support_line}\n\nThe {brand} team"
        ),
        (
            "Hi {first},\n\nOrder {short_order} has been confirmed and will be processed shortly. The {product} "
            "is in stock and ready to ship from the warehouse closest to you. You can manage the delivery window at "
            "{track_url} at any point before dispatch.\n\nTotal {amount}, charged to card {card}.\n\n{support_line}"
        ),
        (
            "Hello {first},\n\nThanks for shopping at {brand}. Your order {order_id} has been received and payment "
            "of {amount} was processed successfully on card {card}. A tracking number will appear at {track_url} "
            "once the item ships.\n\nIf you need to change anything, do it before the order moves to dispatch.\n\n"
            "{support_line}"
        ),
        (
            "Hi {first},\n\nWe packed your {brand} order {short_order} today and it's heading your way. Estimated "
            "delivery: {short_date2}. Full tracking and delivery instructions live at {track_url}.\n\nThanks for "
            "your order,\nThe {brand} team"
        ),
    ],
    ("food", "order_confirmation"): [
        (
            "Hi {first},\n\nWe've got your {brand} order {short_order} from {restaurant}. The courier is "
            "heading there now and should be with you in about {N} minutes, traffic permitting. You can "
            "follow the driver in real time at {track_url}. The order contains {food} plus your usual "
            "sides.\n\nOrder total: {amount}, paid with card {card} on {date}. A full itemised receipt will "
            "follow once the delivery is complete.\n\n{support_line}\n\nThanks for ordering with {brand}."
        ),
        (
            "Hi {first},\n\nYour {brand} order {short_order} has been delivered to the address on file in "
            "{city}. Hope the {food} from {restaurant} hit the spot. If something wasn't right — missing "
            "items, wrong dish, or temperature issues — you can report it within 24 hours via the order "
            "details at {track_url} and our support team will help resolve it.\n\n{support_line}\n\nThe "
            "{brand} team"
        ),
        (
            "Hello {first},\n\nThanks for ordering with {brand}. {restaurant} is preparing your {food} now, "
            "order reference {short_order}. Estimated delivery is around {N} minutes from now. Once the food "
            "is ready a nearby courier will collect it and head to the delivery address. Track the courier "
            "live at {track_url}.\n\nTotal charged: {amount} including service fee and any applicable "
            "tip.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nYour {brand} courier has picked up order {short_order} from {restaurant} and is "
            "about {N} minutes away from you. The driver's name, vehicle, and live location are all visible "
            "at {track_url}. Total charged to card {card} was {amount} — this includes food subtotal, "
            "delivery fee, and any adjustments applied at checkout.\n\n{support_line}\n\nEnjoy the meal."
        ),
        (
            "Hi {first},\n\nOrder {short_order} from {restaurant} is on its way to you in {city}. Please keep "
            "an eye on the buzzer or your phone — the driver will attempt contact before leaving the {food} "
            "at the door if you've requested contactless delivery. Full order details and a copy of the "
            "receipt are available at {track_url}.\n\nThanks for ordering with {brand}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nYour {brand} order {short_order} has been confirmed. {restaurant} will start "
            "preparing your {food} shortly and aims to hand it to a courier within the next {N} minutes. The "
            "driver will then head to the delivery address in {city}. Live tracking, delivery instructions, "
            "and the full itemised total of {amount} are visible at {track_url}.\n\n{support_line}"
        ),
    ],
    ("travel", "order_confirmation"): [
        (
            "Hi {first},\n\nYour {brand} booking is confirmed. Reference {conf_code} for a {N}-night stay in "
            "{destination}, check-in on {date}. Total paid: {amount} on card {card}. Full itinerary at "
            "{track_url}.\n\n{support_line}\n\nSafe travels,\nThe {brand} team"
        ),
        (
            "Hello {first},\n\nThanks for booking with {brand}. Your reservation in {destination} is confirmed "
            "under reference {conf_code}. Dates: {date} to {date2}. You can view or modify the booking any time at "
            "{track_url}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nYour {brand} flight {flight_no} is confirmed. Reference {conf_code}. Departure on "
            "{date} at {time}, seat {seat}. Check in online 24 hours before departure at {track_url}. Total "
            "{amount}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nWe've confirmed your {brand} trip to {destination}. Booking reference {conf_code} "
            "includes {N} nights and complimentary breakfast. You can see the full itinerary and add extras at "
            "{track_url}.\n\n{support_line}\n\nEnjoy the trip."
        ),
        (
            "Hello {first},\n\nThanks for booking through {brand}. Itinerary {conf_code} is saved to your "
            "account. You'll receive check-in details closer to the date. Any questions can be handled through the "
            "help centre, and full details live at {track_url}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nYour {brand} reservation {conf_code} has been confirmed. Payment of {amount} was "
            "charged to card {card}. Check-in on {date}. You can print the confirmation or view it on the app at "
            "{track_url}.\n\n{support_line}"
        ),
    ],

    ("ecommerce", "receipt"): [
        (
            "Hi {first},\n\nThanks for your {brand} purchase. Here is the receipt for order {short_order}: "
            "total {amount}, paid with card {card} on {date}. A copy is always available at {receipt_url}. "
            "Invoice reference {invoice_id}.\n\n{support_line}\n\nThe {brand} team"
        ),
        (
            "Hi {first},\n\nReceipt for your {brand} order {order_id}. Subtotal {amount}, paid with card {card}. "
            "A PDF copy is attached for your records and a full breakdown is available at "
            "{receipt_url}.\n\n{support_line}"
        ),
        (
            "Hello {first},\n\nYour {brand} payment of {amount} has been processed. Order {short_order}, "
            "invoice {invoice_id}. You can download the receipt at {receipt_url}. No further action is "
            "needed.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nThis email confirms payment for {brand} order {short_order}. Amount: {amount}, "
            "method: card {card}. The receipt is stored on your account at {receipt_url} for up to seven "
            "years.\n\n{support_line}\n\nThanks for shopping with {brand}."
        ),
    ],
    ("food", "receipt"): [
        (
            "Hi {first},\n\nHere is the receipt for your {brand} order {short_order}. Subtotal {amount}, paid "
            "with card {card} on {date}. You can view the itemised breakdown at {receipt_url}.\n\n"
            "{support_line}\n\nThanks for using {brand}."
        ),
        (
            "Hi {first},\n\n{brand} — payment confirmed for order {short_order}. Card {card} was charged "
            "{amount}. A full receipt with tip and service fees is at {receipt_url}.\n\n{support_line}"
        ),
        (
            "Hello {first},\n\nReceipt for your {brand} order {short_order} from {restaurant}. Total {amount}. "
            "This is your final receipt; no further charges for this order.\n\nView or download at "
            "{receipt_url}.\n\n{support_line}"
        ),
    ],
    ("travel", "receipt"): [
        (
            "Hi {first},\n\nReceipt for your {brand} booking reference {conf_code}. Total paid: {amount}, "
            "charged to card {card} on {date}. A printable copy is available at {receipt_url}.\n\n"
            "{support_line}\n\nSafe travels,\nThe {brand} team"
        ),
        (
            "Hi {first},\n\nThanks for booking with {brand}. Payment of {amount} for reservation {conf_code} "
            "has been processed. View the itemised receipt at {receipt_url}.\n\n{support_line}"
        ),
        (
            "Hello {first},\n\n{brand} payment receipt — reference {conf_code}. The charge of {amount} was "
            "applied to card {card}. Your full invoice and any taxes or fees are listed at "
            "{receipt_url}.\n\n{support_line}"
        ),
    ],
    ("streaming", "receipt"): [
        (
            "Hi {first},\n\nThanks for your {brand} payment. We've received {amount} for your subscription, "
            "transaction {txn_id}. Your plan is active through {date}. A detailed receipt lives at "
            "{receipt_url}.\n\n{support_line}\n\nThe {brand} team"
        ),
        (
            "Hi {first},\n\nYour monthly {brand} receipt: {amount} charged to card {card}, transaction "
            "{txn_id}. No further action is needed — your membership continues as normal. Full billing "
            "history at {receipt_url}.\n\n{support_line}"
        ),
        (
            "Hello {first},\n\nPayment received for your {brand} subscription. Reference {txn_id}, amount "
            "{amount}. Your plan renewed on {date} and is valid through the next billing cycle. Manage at "
            "{account_url}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nThis is a record of your latest {brand} payment. Transaction {txn_id} for "
            "{amount} completed successfully. You can download a VAT receipt for business use at "
            "{receipt_url}.\n\n{support_line}"
        ),
    ],
    ("finance", "receipt"): [
        (
            "Hi {first},\n\nWe've received your {brand} payment. Transaction {txn_id} for {amount} was "
            "processed on {date} and has posted to the account ending {card}. This message serves as "
            "confirmation — keep it for your records or access a duplicate at {receipt_url}.\n\n"
            "{support_line}\n\nThe {brand} customer team"
        ),
        (
            "Hello {first},\n\nThank you for your {brand} payment of {amount}. Reference {txn_id} has been "
            "applied to your account ending {card}. The updated balance and a printable receipt are both "
            "visible at {account_url}. Future payments can be scheduled from the same page.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nYour {brand} payment of {amount} has cleared. Transaction reference {txn_id}. "
            "The funds left your linked account on {date} and have been applied to the statement in full. "
            "A copy of the receipt is available at {receipt_url} whenever you need it.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nReceipt confirmation from {brand}: payment of {amount} processed successfully. "
            "Reference {txn_id}, applied to card {card}. You can view the full posting details, including "
            "the effective date and descriptor, at {receipt_url}. No further action is needed from you "
            "for this payment.\n\n{support_line}"
        ),
    ],

    ("travel", "reminder"): [
        (
            "Hi {first},\n\nJust a friendly reminder that your {brand} reservation {conf_code} is coming up on "
            "{date}. Your {N}-night stay in {destination} is all set. Review or update your booking at "
            "{track_url}.\n\n{support_line}\n\nSafe travels,\nThe {brand} team"
        ),
        (
            "Hi {first},\n\nYour {brand} trip starts in {N} days. Reference {conf_code} — {destination}, "
            "{date} to {date2}. You can review the full itinerary and any add-ons at {track_url}.\n\n"
            "{support_line}"
        ),
        (
            "Hello {first},\n\nYour {brand} flight {flight_no} on {date} is approaching. Online check-in opens "
            "24 hours before departure at {track_url}. Reference {conf_code}, seat {seat}, departure "
            "time {time}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nA quick reminder about your {brand} reservation {conf_code}. Check-in is on "
            "{date}. The host will share the address and key instructions 48 hours ahead of arrival. In the "
            "meantime you can message them through {track_url}.\n\n{support_line}"
        ),
    ],
    ("streaming", "reminder"): [
        (
            "Hi {first},\n\nYour {brand} subscription renews on {date} for {amount}. No action needed — the "
            "charge will go through automatically to card {card}. You can review or change the plan any time "
            "at {account_url}. Reference {ref_id}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nHeads up — your {brand} plan renews tomorrow. The next charge of {amount} will be "
            "applied to your saved payment method {card}. Manage the subscription at {account_url}. "
            "Reference {ref_id}.\n\n{support_line}"
        ),
        (
            "Hello {first},\n\nYour {brand} annual plan renews in {N} days. Amount: {amount}. If you want to "
            "switch plans before the renewal you can do so at {account_url}. Billing reference "
            "{ref_id}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nQuick reminder that your {brand} subscription will renew on {date}. We'll charge "
            "{amount} to the card on file. No action needed; everything is handled. Reference "
            "{ref_id}.\n\nSee plan details at {account_url}.\n\n{support_line}"
        ),
    ],
    ("finance", "reminder"): [
        (
            "Hi {first},\n\nYour {brand} statement payment is due on {date}. The minimum payment for reference "
            "{ref_id} is {amount}. Autopay is enabled, so the full balance will be taken automatically unless "
            "you change it at {account_url}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nReminder: {brand} payment due {date}. The total owed on reference {ref_id} is "
            "{amount}. You can pay early or schedule the payment via {account_url}.\n\n{support_line}\n\nThe "
            "{brand} team"
        ),
        (
            "Hello {first},\n\nYour {brand} autopay will run on {date}. {amount} will be deducted to settle "
            "statement {ref_id}. If you need to update the source account, make the change at least 48 hours "
            "before the run at {account_url}.\n\n{support_line}"
        ),
    ],
    ("ecommerce", "reminder"): [
        (
            "Hi {first},\n\nReminder: your {brand} subscribe-and-save delivery {short_order} ships on {date}. "
            "Items in the box: {product}. Review or skip the delivery before {short_date2} at "
            "{track_url}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nHeads up — your {brand} pick-up order {short_order} is ready for collection from "
            "the {city} store. Please collect within {N} days. Details at {track_url}.\n\n{support_line}"
        ),
        (
            "Hello {first},\n\nYour next {brand} auto-reorder for {product} goes out on {date}. Reference "
            "{short_order}. If you'd like to skip or change the frequency, you can do that at "
            "{track_url}.\n\n{support_line}"
        ),
    ],

    ("finance", "account_notification"): [
        (
            "Hi {first},\n\nA new transaction was recorded on your {brand} account: {amount} at {merchant} on "
            "{date}. Reference {txn_id}, card {card}. No action needed; this is an informational alert. View "
            "activity at {track_url}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nYour {brand} monthly statement for {month} is ready. Closing balance {amount}, "
            "reference {ref_id}. View or download the statement at {receipt_url}.\n\n{support_line}\n\nThe "
            "{brand} team"
        ),
        (
            "Hello {first},\n\nTransaction notification from {brand}: {amount} at {merchant} was authorised on "
            "card {card}. Reference {txn_id}. If you recognise this charge, no further action is needed. "
            "Review at {track_url}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nYour {brand} account summary for {month} is now available. Total debits: {amount}. "
            "Statement reference {ref_id}. Access the full breakdown including categorised spending at "
            "{account_url}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nBalance update on your {brand} account ending {card}. Current available balance "
            "includes the recent transaction of {amount}, reference {txn_id}. Full history is at "
            "{track_url}.\n\n{support_line}"
        ),
    ],
    ("streaming", "account_notification"): [
        (
            "Hi {first},\n\nA quick note about your {brand} account: your plan was updated on {date}. The new "
            "plan is active immediately. Reference {ref_id}. You can review it at {account_url}. No action "
            "needed.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nYour {brand} payment method has been updated. The card ending {card} is now the "
            "default. Reference {ref_id}. If this was not you, roll it back at {account_url}.\n\n{support_line}"
        ),
        (
            "Hello {first},\n\nYour {brand} billing address was changed on {date}. Reference {ref_id}. The next "
            "invoice will reflect the new address. View or correct it at {account_url}.\n\n{support_line}"
        ),
    ],
    ("ecommerce", "account_notification"): [
        (
            "Hi {first},\n\nYour {brand} monthly summary for {month} is ready. You placed {N} orders totalling "
            "{amount}. Most-ordered category: {product}. Full summary reference {ref_id} lives at "
            "{account_url}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\nActivity on your {brand} account: {N} orders over the last 30 days. Total spend "
            "{amount}, reference {ref_id}. You can download the activity report at {receipt_url}.\n\n"
            "{support_line}"
        ),
        (
            "Hello {first},\n\nHere is your {brand} recent orders summary. Since {date} you've placed {N} "
            "orders. The most recent is {short_order}. You can browse or reorder any of them at "
            "{account_url}.\n\n{support_line}"
        ),
    ],
    ("travel", "account_notification"): [
        (
            "Hi {first},\n\nYour {brand} account summary for {month}: {N} completed trips, {amount} total "
            "spend, {miles} miles earned. Reference {ref_id}. Full history at {account_url}.\n\n{support_line}"
        ),
        (
            "Hi {first},\n\n{brand} reward points statement: current balance {miles} miles. Reference "
            "{ref_id}. Points expire after 24 months of inactivity. Review and redeem at "
            "{account_url}.\n\n{support_line}"
        ),
        (
            "Hello {first},\n\nYour {brand} travel summary for {month} is ready. Trips taken: {N}. Total "
            "spend: {amount}. Summary reference {ref_id}. View your detailed travel history at "
            "{account_url}.\n\n{support_line}"
        ),
    ],
}

# ------------------------------------------------------------------------------------
# Per-subtype suffix banks. Randomly appended to bodies to push word count into the
# 80-200 range specified by section 3.3 while varying the closing detail.
# ------------------------------------------------------------------------------------

SUFFIXES = {
    "order_confirmation": [
        (
            "\n\nA reminder: once the parcel is handed to the carrier we cannot amend the delivery "
            "address, so please double-check the details before dispatch. If you have any questions about "
            "the order, reply to this email and we'll get back to you within one business day."
        ),
        (
            "\n\nIf you need to change the delivery window, you can do so through your account up until "
            "the evening before dispatch. After that the parcel is in the carrier's hands. Returns are "
            "accepted within 30 days of delivery for unopened items."
        ),
        (
            "\n\nFor your records, the billing address and payment method will appear on the receipt. "
            "We'll never ask you to confirm card details over email — any changes should be made through "
            "your account page directly."
        ),
        (
            "\n\nEstimated delivery may shift slightly depending on carrier load at this time of year. "
            "We'll email again with any update that materially affects the arrival window. Thanks again "
            "for shopping with us."
        ),
        (
            "\n\nOnce the order is delivered we'll send a short satisfaction check — no pressure to "
            "respond, but the feedback helps us improve service on future orders. Full order history "
            "is stored on your account for reference."
        ),
    ],
    "receipt": [
        (
            "\n\nThis email serves as your official receipt and can be used for expense reporting or tax "
            "purposes. A duplicate PDF copy is attached on web view and will remain accessible from your "
            "account history for several years."
        ),
        (
            "\n\nNo action is needed from you — the payment has settled and nothing further will be "
            "charged for this transaction. If you spot anything on the receipt that doesn't match what "
            "you ordered, please contact us within 14 days."
        ),
        (
            "\n\nA full itemised breakdown, including any applicable taxes, discounts, and loyalty "
            "adjustments, is available on the linked page. You can export the receipt as PDF or CSV "
            "format for your records."
        ),
        (
            "\n\nFor business customers: a VAT-compliant invoice is available on request through your "
            "account. We keep receipts accessible for at least seven years in line with tax regulations "
            "in most jurisdictions."
        ),
    ],
    "reminder": [
        (
            "\n\nThis is an informational reminder only. No response is required from you — the change "
            "or charge will happen automatically on the date shown. Any modifications should be made "
            "through your account at least 24 hours before the scheduled time."
        ),
        (
            "\n\nWe send one reminder per upcoming charge or event as a courtesy. If you would prefer "
            "fewer reminders, you can adjust the notification preferences on your account page at any "
            "time without affecting the underlying service."
        ),
        (
            "\n\nIf you want to pause, skip, or cancel the upcoming cycle, the options are available on "
            "the manage page. Changes made before the scheduled date take effect immediately; changes "
            "made after the date apply to the next cycle."
        ),
        (
            "\n\nJust a heads up so nothing takes you by surprise. Everything is ready on our side. "
            "You do not need to reply to this message, and no further action is required unless you "
            "would like to make a change."
        ),
    ],
    "account_notification": [
        (
            "\n\nThis alert is purely informational. If the activity matches what you expect, no action "
            "is required. If anything looks unfamiliar, you can dispute the item directly from the "
            "activity page within the standard dispute window."
        ),
        (
            "\n\nAll recent activity, including pending transactions, is visible in your account. We "
            "group routine notifications into a single daily summary where possible to keep your inbox "
            "quieter without missing anything important."
        ),
        (
            "\n\nReminder: we will never ask you to share your password, full card number, or "
            "verification codes by email. If a message ever requests that, please report it to us through "
            "the help centre so we can investigate."
        ),
        (
            "\n\nPaperless statements are the default on this account. You can change to mailed "
            "statements at any time from the preferences page, though you'll still receive routine "
            "notifications like this one by email."
        ),
    ],
}


# ------------------------------------------------------------------------------------
# Plan — how many rows per (brand_category, subtype). Sum == 1000.
# ------------------------------------------------------------------------------------

PLAN = [
    # Order confirmations (250)
    ("ecommerce", "order_confirmation", 120),
    ("food", "order_confirmation", 80),
    ("travel", "order_confirmation", 50),
    # Receipts (250)
    ("ecommerce", "receipt", 50),
    ("food", "receipt", 50),
    ("travel", "receipt", 40),
    ("streaming", "receipt", 60),
    ("finance", "receipt", 50),
    # Reminders (250)
    ("travel", "reminder", 70),
    ("streaming", "reminder", 100),
    ("finance", "reminder", 50),
    ("ecommerce", "reminder", 30),
    # Account notifications (250)
    ("finance", "account_notification", 120),
    ("streaming", "account_notification", 50),
    ("ecommerce", "account_notification", 40),
    ("travel", "account_notification", 40),
]
assert sum(c for _, _, c in PLAN) == 1000

BRANDS_BY_CATEGORY: dict[str, list[str]] = {}
for bname, b in BRANDS.items():
    BRANDS_BY_CATEGORY.setdefault(b["category"], []).append(bname)


# ------------------------------------------------------------------------------------
# Context builder / fill
# ------------------------------------------------------------------------------------

def build_ctx(brand_name: str) -> dict:
    brand = BRANDS[brand_name]
    month_idx = random.randint(0, 11)
    day = random.randint(1, 28)
    day2 = min(28, day + random.randint(1, 6))
    return {
        "brand": brand_name,
        "first": pick(FIRST_NAMES),
        "order_id": order_id(),
        "short_order": short_order_id(),
        "ref_id": ref_id(),
        "txn_id": txn_id(),
        "invoice_id": invoice_id(),
        "conf_code": confirmation_code(),
        "amount": amount(),
        "card": masked_card(),
        "flight_no": flight_no(),
        "seat": f"{random.randint(1, 34)}{random.choice('ABCDEF')}",
        "destination": pick(TRAVEL_DESTINATIONS),
        "restaurant": pick([
            "Olive & Bloom", "The Noodle Bar", "Riverside Grill", "Curry House",
            "La Bella Napoli", "Green Leaf Kitchen", "Sakura Sushi", "The Taco Spot",
            "Hearth & Hen", "The Corner Cafe",
        ]),
        "food": pick(FOOD_ITEMS),
        "product": pick(PRODUCTS),
        "city": pick(CITIES),
        "merchant": pick([
            "WHOLE FOODS MARKET", "AMZN MKTP", "SAINSBURYS", "TESCO", "SHELL OIL",
            "STARBUCKS", "APPLE STORE", "TARGET #1245", "UBER", "BP",
        ]),
        "miles": f"{random.randint(500, 98000):,}",
        "N": random.randint(2, 12),
        "month": MONTHS[month_idx],
        "date": f"{MONTHS[month_idx]} {day}",
        "date2": f"{MONTHS[month_idx]} {day2}",
        "short_date": f"{MONTHS_SHORT[month_idx]} {day}",
        "short_date2": f"{MONTHS_SHORT[month_idx]} {day2}",
        "time": f"{random.randint(1, 23):02d}:{random.choice(['00', '15', '30', '45'])}",
        "track_url": brand["track_url"],
        "receipt_url": brand["receipt_url"],
        "account_url": brand["account_url"],
        "support_line": brand["support_line"],
    }


PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def fill(template: str, ctx: dict) -> str:
    def repl(m):
        key = m.group(1)
        return str(ctx.get(key, m.group(0)))

    return PLACEHOLDER_RE.sub(repl, template)


# ------------------------------------------------------------------------------------
# Quality checks — section 6 plus section 3.3 constraints
# ------------------------------------------------------------------------------------

SENDER_DOMAIN_RE = re.compile(r"<[^@]+@([^>]+)>")
URL_SHORTENERS = ["bit.ly", "tinyurl", "t.co/", "goo.gl", "ow.ly", "is.gd", "buff.ly"]
TYPOSQUAT_PATTERNS = [
    "paypa1", "amaz0n", "g00gle", "githu8", "microsft", "paypai", "amzon",
    "lnkedin", "yt0be", "faceb00k", "netfl1x", "sp0tify",
]
DIGIT_IN_DOMAIN = re.compile(r"[a-z][0-9][a-z]|[a-z][0-9]{2,}[a-z]")
# ID signal: Amazon-style, short #123456, REF-..., TXN..., INV-..., 6-letter booking codes.
ID_SIGNAL = re.compile(
    r"(?:"
    r"\d{3}-\d{7}-\d{7}"            # Amazon-style order IDs
    r"|#\d{4,}"                     # #12345
    r"|REF-\d{4,}"                  # REF-...
    r"|TXN\d{6,}"                   # TXN...
    r"|INV-\d{4,}"                  # INV-...
    r"|\b[A-Z]{2}\d{3,}\b"          # flight numbers like DL1234
    r"|\b[A-Z]{6}\b"                # 6-letter booking codes
    r")"
)
URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
CREDENTIAL_PHRASES = [
    "enter your password", "confirm your password", "update your password",
    "reset your password", "verify your password", "provide your password",
    "re-enter your password", "enter your credit card", "confirm your credit card",
    "provide your social security", "provide your ssn", "verify your identity now",
    "click here to verify", "verify your account immediately", "account will be suspended",
]


def sender_domain(s: str) -> str:
    m = SENDER_DOMAIN_RE.search(s)
    return m.group(1).lower() if m else ""


def passes_checks(row: dict, brand_name: str) -> bool:
    sender = row["sender"]
    subject = row["subject"]
    body = row["body"]
    blob = f"{sender}\n{subject}\n{body}".lower()

    # (2) min body length
    if len(body.strip()) < 10:
        return False

    # body word count 80-200 per section 3.3
    wc = len(body.split())
    if wc < 80 or wc > 205:
        return False

    # (3) typosquat
    for pat in TYPOSQUAT_PATTERNS:
        if pat in blob:
            return False

    # (5) digit-in-domain
    if DIGIT_IN_DOMAIN.search(sender_domain(sender)):
        return False

    # (6) URL shorteners
    for sh in URL_SHORTENERS:
        if sh in blob:
            return False

    # no https URLs (we only use bare domains per section 3.1 body style + section 3.3 "legitimate-looking URL")
    # The spec explicitly says bare domain URLs for legitimate. Not strictly banned, but keep it clean.

    # credential / urgency phrases
    for phrase in CREDENTIAL_PHRASES:
        if phrase in blob:
            return False

    # required ID signal (section 3.3: order / reference / transaction ID)
    if not ID_SIGNAL.search(body):
        return False

    # sender domain must include the brand's primary domain
    brand_primary_domain = BRANDS[brand_name]["track_url"].split("/")[0]
    # Strip any subdomain prefixes from brand_primary_domain — for .co.uk and similar too.
    # Accept if sender domain equals or ends with the primary domain.
    s_domain = sender_domain(sender)
    if not (s_domain == brand_primary_domain or s_domain.endswith("." + brand_primary_domain)
            # Accept legitimate parent-domain patterns used by some brands (e.g. aexp.com for Amex).
            or brand_primary_domain.endswith("." + s_domain.split(".", 1)[-1]) and False):
        # allow whitelisted secondary domains (AmericanExpress.com uses aexp.com, Apple uses apple.com,
        # Hulu uses hulumail.com, Disney+ uses mail.disneyplus.com). Check against configured senders list.
        if sender not in BRANDS[brand_name]["senders"]:
            return False

    return True


# ------------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------------

def generate() -> list[dict]:
    from collections import Counter

    rows: list[dict] = []
    seen: set[str] = set()
    template_use: Counter = Counter()

    for bcat, subtype, count in PLAN:
        subjects = SUBJECTS[(bcat, subtype)]
        bodies = BODIES[(bcat, subtype)]
        produced = 0
        attempts = 0
        max_attempts = count * 60
        brand_pool = BRANDS_BY_CATEGORY[bcat]

        while produced < count and attempts < max_attempts:
            attempts += 1
            brand_name = pick(brand_pool)
            brand = BRANDS[brand_name]
            sender = pick(brand["senders"])

            subj_tpl = pick(subjects)
            body_tpl = pick(bodies)
            key = (bcat, subtype, subj_tpl, body_tpl)
            if template_use[key] >= 5:
                continue

            ctx = build_ctx(brand_name)
            subject = fill(subj_tpl, ctx)
            body = fill(body_tpl, ctx)
            # Append two distinct subtype-specific suffixes to bring the word count into the 80-200 range.
            sfx_pool = SUFFIXES[subtype]
            sfx_choices = random.sample(sfx_pool, k=min(2, len(sfx_pool)))
            for sfx in sfx_choices:
                body = body + fill(sfx, ctx)
            row = {
                "sender": sender,
                "subject": subject,
                "body": body,
                "label": 0,
                "category": "retail_transactional",
            }

            h = hashlib.sha1(f"{sender}\n{subject}\n{body}".encode()).hexdigest()
            if h in seen:
                continue
            if not passes_checks(row, brand_name):
                continue

            rows.append(row)
            seen.add(h)
            template_use[key] += 1
            produced += 1

        if produced < count:
            raise RuntimeError(
                f"Only produced {produced}/{count} for ({bcat}, {subtype}) in {attempts} attempts"
            )

    assert len(rows) == 1000
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
