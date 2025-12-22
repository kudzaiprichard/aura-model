from usage.dataset.phishing import phishing_emails

legitimate_emails = [
    {
        'sender': 'Amazon <auto-confirm@amazon.com>',
        'subject': 'Your Amazon.com order #112-8472956-3847291',
        'body': '''Hello,

Thank you for your order. Your order has been received and is being processed.

Order Details:
Order #112-8472956-3847291
Order Date: December 13, 2025

Items Ordered:
- Wireless Headphones (Black) - Qty: 1 - $79.99
- USB-C Cable (6ft) - Qty: 2 - $12.99 each

Subtotal: $105.97
Shipping: FREE (Prime)
Tax: $9.01
Order Total: $114.98

Estimated Delivery: December 16-18, 2025

Track your package: https://www.amazon.com/progress-tracker/package/ref=ppx_yo_dt_b_track_package

Shipping Address:
John Smith
123 Main Street
New York, NY 10001

You can review your order and manage your account at: https://www.amazon.com/your-orders

Thank you for shopping with Amazon.

Amazon.com''',
        'label': 0
    },
    {
        'sender': 'Best Buy <BestBuyInfo@emailinfo.bestbuy.com>',
        'subject': 'Your Best Buy order BBY01-482956374829 is confirmed',
        'body': '''Thank you for your order!

Order Number: BBY01-482956374829
Order Date: December 13, 2025

Order Summary:
- Samsung 55" 4K Smart TV - $599.99
- HDMI Cable (6ft) - $19.99

Subtotal: $619.98
Tax: $52.70
Total: $672.68

Store Pickup Information:
Best Buy - 456 Market St, San Francisco, CA 94102
Ready for pickup: December 14, 2025 after 12:00 PM

We'll send you an email when your order is ready. Please bring a valid photo ID and your order confirmation.

View your order status: https://www.bestbuy.com/profile/ss/orders/order-details/BBY01-482956374829

Need help? Visit https://www.bestbuy.com/site/customer-service or call 1-888-237-8289

Best Buy''',
        'label': 0
    },
    {
        'sender': 'Target <guest.orders@target.com>',
        'subject': 'Your Target order is on the way - Arrives Dec 15',
        'body': '''Your order has shipped!

Order #827-4820-9283
Shipped on: December 13, 2025
Estimated delivery: December 15, 2025

What's in this shipment:
- Coffee Maker (Black & Decker, 12-Cup) - $89.99
- Coffee Filters (100 count, Unbleached) - $4.99

Tracking Information:
Tracking Number: 1Z9999W99999999999
Carrier: UPS Ground

Track your package: https://www.target.com/orders/827-4820-9283/track

Delivery address:
Sarah Johnson
789 Oak Avenue, Apt 4B
Chicago, IL 60601

Manage your order: https://www.target.com/account/orders

Questions? Visit https://help.target.com or call 1-800-591-3869

Thanks for shopping at Target!

Target''',
        'label': 0
    },
    {
        'sender': 'Apple Store <no_reply@email.apple.com>',
        'subject': 'Your Apple Store order M482957392 is confirmed',
        'body': '''Thank you for your order.

Order Number: M482957392
Order Date: December 13, 2025

Items:
AirPods Pro (2nd generation) with MagSafe Charging Case - $249.00
AppleCare+ for AirPods Pro - $29.00

Subtotal: $278.00
Estimated Tax: $23.63
Total: $301.63

Delivery Estimate: December 16-18, 2025
Shipping Method: Standard Shipping

You'll receive a shipping notification when your order ships.

Track your order: https://www.apple.com/shop/order/list?node=home/shop_order/view_order&orderId=M482957392

Shipping to:
Michael Chen
321 Pine Street, Unit 205
Seattle, WA 98101

Manage your order or contact us: https://www.apple.com/shop/help/orders

Thank you for your purchase.

Apple Store
https://www.apple.com''',
        'label': 0
    },
    {
        'sender': 'Walmart <WalmartOnline@walmart.com>',
        'subject': 'Your Walmart order was delivered',
        'body': '''Your order has been delivered.

Order #948-2847-3829
Delivered on: December 13, 2025 at 2:34 PM

Items delivered:
- Tide Laundry Detergent (100 oz, HE Compatible) - $14.99
- Bounty Paper Towels (12 Double Rolls) - $19.99
- Dawn Dish Soap (3 Pack, Ultra) - $8.99

Order total: $43.97
Payment method: Visa ending in 4829

Delivery details:
Left at: Front door
Photo: View delivery photo at https://www.walmart.com/orders/948-2847-3829/delivery-photo

View your receipt: https://www.walmart.com/orders/948-2847-3829/receipt

Rate your delivery experience: https://www.walmart.com/orders/948-2847-3829/rate

Questions about your order? Visit https://www.walmart.com/help or call 1-800-925-6278

Thank you for shopping with Walmart!

Walmart
https://www.walmart.com''',
        'label': 0
    },
    {
        'sender': 'PayPal <service@paypal.com>',
        'subject': 'Receipt for your payment to Adobe Inc.',
        'body': '''You sent a payment

Transaction Details:
Transaction ID: 8JH29384KD920384
Date: December 13, 2025, 3:45 PM PST

To: Adobe Inc.
Amount: $54.99 USD

Payment for: Adobe Creative Cloud - Monthly Subscription
Type: Automatic subscription payment

Payment method: Bank account ending in ••••4829

View transaction details: https://www.paypal.com/activity/payment/8JH29384KD920384

Need help with this payment?
Visit the Resolution Center: https://www.paypal.com/disputes
Contact Adobe directly: https://www.adobe.com/support

Manage your subscriptions: https://www.paypal.com/myaccount/autopay

Questions about your account?
Visit our Help Center: https://www.paypal.com/smarthelp/home
Call us: 1-888-221-1161

PayPal
https://www.paypal.com

Please do not reply to this email. This mailbox is not monitored.''',
        'label': 0
    },
    {
        'sender': 'Stripe <receipts@stripe.com>',
        'subject': 'Receipt from Notion Labs [Receipt #8392-4820]',
        'body': '''Receipt from Notion Labs

Amount paid: $10.00 USD
Date paid: December 13, 2025

Receipt Number: 8392-4820
Notion Plus - Monthly subscription

Payment method: Visa ending in ••4242
Last 4 digits: 4242

Billing Details:
Name: Jennifer Martinez
Email: jennifer.m@email.com

Description: Notion Plus - Monthly subscription
Unlimited blocks for you
Unlimited file uploads
30 day version history

Next billing date: January 13, 2026

View your receipt: https://invoice.stripe.com/i/acct_1A2B3C4D5E/inv_XYZ789ABC123

Questions about this charge?
Contact Notion Labs: https://www.notion.so/help
Email: team@makenotion.com

Manage your subscription: https://www.notion.so/subscriptions

Stripe | 510 Townsend Street, San Francisco, CA 94103
https://stripe.com''',
        'label': 0
    },
    {
        'sender': 'Square <receipts@messaging.squareup.com>',
        'subject': 'Receipt for $47.50 at Coffee House',
        'body': '''Thanks for your purchase!

Coffee House
123 Main St, Portland, OR 97201
(503) 555-0199

Date: December 13, 2025
Time: 8:45 AM PST

Items:
2x Latte (Large) - $5.00 each = $10.00
1x Croissant (Butter) - $4.50
1x Avocado Toast - $12.00

Subtotal: $26.50
Tax: $2.25
Tip: $18.75
Total: $47.50

Payment method: Visa ending in ••5678
Card type: Visa Credit
Transaction ID: sq_1234567890

View your full receipt: https://square.link/u/ABC123XYZ789

Feedback? Rate your experience: https://square.link/r/ABC123

Download the Square app to track all your receipts:
https://squareup.com/app

Square, Inc.
1455 Market Street, Suite 600, San Francisco, CA 94103
https://squareup.com''',
        'label': 0
    },
    {
        'sender': 'Venmo <venmo@venmo.com>',
        'subject': 'You paid Sarah Johnson $45.00',
        'body': '''You paid Sarah Johnson

Payment Details:
Amount: $45.00
Date: December 13, 2025 at 7:30 PM EST
Note: "Dinner split 🍕"

Paid from: Chase Bank account ending in ••8492
Transaction ID: 3847293847

Sarah's Venmo: @Sarah-Johnson-123

View this payment: https://venmo.com/transaction/3847293847

Your Venmo balance: $127.50

Sent money by mistake?
You can request your money back by going to the payment in your feed and selecting "Request Money Back"

Manage your Venmo account: https://venmo.com/account/settings
View your feed: https://venmo.com/account/feed

Questions? Visit our Help Center: https://help.venmo.com
Contact us: https://venmo.com/about/contact

Venmo - A PayPal Service
2211 North First Street, San Jose, CA 95131
https://venmo.com''',
        'label': 0
    },
    {
        'sender': 'QuickBooks <notifications@intuit.com>',
        'subject': 'Payment received: Invoice #INV-1248 - $1,250.00',
        'body': '''Payment Received

Invoice: INV-1248
Amount: $1,250.00 USD
Date received: December 13, 2025

From: Tech Solutions LLC
Payment method: ACH Bank Transfer
Reference: ACH20251213001248

For: Web Development Services - November 2025
- Frontend development (40 hours @ $25/hr): $1,000
- Backend integration (10 hours @ $25/hr): $250

Invoice status: PAID IN FULL

View invoice: https://quickbooks.intuit.com/app/invoice?txnId=INV-1248

See all your invoices: https://quickbooks.intuit.com/app/sales

This payment has been deposited to your connected bank account ending in ••3847.
Expected in account: December 15-16, 2025

Need help?
Visit QuickBooks Support: https://quickbooks.intuit.com/learn-support/
Call: 1-800-4INTUIT (1-800-446-8848)

QuickBooks Online
Intuit Inc.
https://quickbooks.intuit.com''',
        'label': 0
    },
    {
        'sender': 'Delta Air Lines <delta@emails.delta.com>',
        'subject': 'eTicket receipt - Confirmation #KL8D9F',
        'body': '''Your trip is confirmed

Confirmation Code: KL8D9F
Ticket Number: 0062847293847

Flight Details:
Delta Air Lines Flight 1234
Wednesday, December 20, 2025

Depart: New York (JFK) - Terminal 4
8:00 AM EST

Arrive: Los Angeles (LAX) - Terminal 5
11:30 AM PST

Duration: 6h 30m (nonstop)

Passenger Information:
Name: John Smith
SkyMiles #: 123456789
Seat: 12A (Economy Comfort)

Baggage:
1 Carry-on included
1 Personal item included
1 Checked bag included

Total Paid: $387.60

Check-in opens 24 hours before departure.
Check in online: https://www.delta.com/flight-check-in

View or manage your trip: https://www.delta.com/mytrips/search
Enter confirmation code: KL8D9F

Download the Fly Delta app for mobile boarding pass and real-time updates:
https://www.delta.com/mobile

Questions? Visit https://www.delta.com/contactus or call 1-800-221-1212

Delta Air Lines
Post Office Box 20706, Atlanta, GA 30320-6001
https://www.delta.com''',
        'label': 0
    },
    {
        'sender': 'Marriott Hotels <reservations@marriott.com>',
        'subject': 'Your reservation at Marriott Downtown - Conf# 847293847',
        'body': '''Reservation Confirmed

Confirmation Number: 847293847

Marriott Downtown San Francisco
123 Market Street
San Francisco, CA 94103
Phone: (415) 555-0100

Reservation Details:
Check-in: Thursday, December 18, 2025 (3:00 PM)
Check-out: Sunday, December 21, 2025 (12:00 PM)
Number of nights: 3

Room Type: King Bed, City View
Number of rooms: 1
Number of guests: 2 Adults

Rate Information:
Room rate: $189.00 per night
Total room charges: $567.00 (before taxes and fees)
Estimated taxes and fees: $93.45
Estimated total: $660.45

Cancellation Policy:
Free cancellation until December 17, 2025 at 3:00 PM
Cancellations after this time will be charged one night's room and tax

Manage your reservation: https://www.marriott.com/reservation/lookupReservation.mi?confirmationNumber=847293847

Check-in online: https://www.marriott.com/mobile-check-in (available 24 hours before arrival)

Marriott Bonvoy Member:
Member #: 987654321
You will earn 1,701 points for this stay

Download the Marriott Bonvoy app: https://www.marriott.com/mobile-app

Questions? Contact the hotel directly at (415) 555-0100
or visit: https://www.marriott.com/help/customer-service.mi

Marriott International
10400 Fernwood Road, Bethesda, MD 20817
https://www.marriott.com''',
        'label': 0
    },
    {
        'sender': 'Enterprise Rent-A-Car <donotreply@enterprise.com>',
        'subject': 'Reservation confirmed - Confirmation #J8472938',
        'body': '''Your rental is confirmed

Confirmation Number: J8472938

Pick-up Information:
Location: San Francisco International Airport (SFO)
Address: 780 McDonnell Road, San Francisco, CA 94128
Phone: (650) 697-9200
Date: Monday, December 18, 2025
Time: 12:00 PM

Drop-off Information:
Location: San Francisco International Airport (SFO)
Same address as pick-up
Date: Thursday, December 21, 2025
Time: 12:00 PM

Rental Period: 3 days

Vehicle Information:
Vehicle class: Intermediate (ICAR)
Example vehicle: Toyota Camry or similar
Features: Automatic transmission, 5 seats, 4 doors, A/C

Rate: $45.00 per day
Estimated Total: $135.00 (excluding taxes and fees)

Driver Information:
Name: Michael Chen
Age: 28
Driver's license required at pickup

What to bring:
- Valid driver's license
- Major credit card in driver's name
- Confirmation number: J8472938

Modify or cancel your reservation: https://www.enterprise.com/en/reserve/modifyCancel.html?resId=J8472938

Add extras to your reservation: https://www.enterprise.com/extras

Join Enterprise Plus rewards: https://www.enterprise.com/go/plus

Questions? Contact us:
Call: 1-855-266-9565
Visit: https://www.enterprise.com/help

Enterprise Rent-A-Car
600 Corporate Park Drive, St. Louis, MO 63105
https://www.enterprise.com''',
        'label': 0
    },
    {
        'sender': 'OpenTable <dining@opentable.com>',
        'subject': 'Reservation confirmed at The Steakhouse - Dec 15',
        'body': '''Your reservation is confirmed

The Steakhouse
456 Fine Dining Avenue
New York, NY 10022
Phone: (212) 555-0145

Reservation Details:
Date: Sunday, December 15, 2025
Time: 7:30 PM
Party size: 4 people

Confirmation code: RT8473928

Special requests: Window table preferred (we'll do our best to accommodate)

Important Information:
- Please arrive on time; we'll hold your table for 15 minutes
- Dress code: Business casual
- Valet parking available ($25)

Modify your reservation: https://www.opentable.com/booking/details/RT8473928

Cancel your reservation: https://www.opentable.com/booking/cancel/RT8473928
Cancellation policy: Please cancel up to 2 hours before your reservation time

Add this reservation to your calendar:
https://www.opentable.com/booking/calendar/RT8473928

View restaurant menu: https://www.opentable.com/r/the-steakhouse-new-york

Get directions: https://maps.opentable.com/RT8473928

Download the OpenTable app for easy reservation management:
https://www.opentable.com/mobile

Questions? Contact the restaurant directly at (212) 555-0145
or visit: https://help.opentable.com

OpenTable
1 Montgomery Street, Suite 700, San Francisco, CA 94104
https://www.opentable.com''',
        'label': 0
    },
    {
        'sender': 'Ticketmaster <noreply@ticketmaster.com>',
        'subject': 'Your tickets for Concert at Madison Square Garden',
        'body': '''Your order is confirmed

Order Number: 18-4729/NY
Order Date: December 13, 2025

Event Information:
Rock Band World Tour 2025
Madison Square Garden
4 Pennsylvania Plaza, New York, NY 10001

Event Date: Saturday, December 28, 2025
Doors Open: 7:00 PM
Show Starts: 8:00 PM

Ticket Details:
Section 104, Row F, Seats 12-13
Quantity: 2 tickets
Price per ticket: $125.00

Order Summary:
Tickets (2 x $125.00): $250.00
Service Fee: $35.00
Order Processing Fee: $7.50
Delivery: $0.00 (Mobile Entry)
Total: $292.50

Payment: Visa ending in ••4829

Your tickets are in your Ticketmaster account and will also be available in the app 5 days before the event.

Access your tickets: https://www.ticketmaster.com/myaccount/orders/18-4729

Download the Ticketmaster app for mobile entry:
iOS: https://apps.apple.com/us/app/ticketmaster/id500003565
Android: https://play.google.com/store/apps/details?id=com.ticketmaster.mobile.android.na

Entry Information:
- Mobile tickets only - screenshot will NOT work
- Have your tickets ready on your phone
- One person can hold tickets for entire party
- Tickets activate 24 hours before event

View event details: https://www.ticketmaster.com/event/18-4729
Get directions: https://www.ticketmaster.com/venue/madison-square-garden

Need help? Visit https://help.ticketmaster.com
or call Fan Support at 1-800-653-8000

Ticketmaster
7060 Hollywood Boulevard, Los Angeles, CA 90028
https://www.ticketmaster.com''',
        'label': 0
    },
    {
        'sender': 'Spotify <no-reply@spotify.com>',
        'subject': 'Your receipt from Spotify',
        'body': '''Thanks for being a Premium member!

Receipt for: Spotify Premium Individual
Billing period: December 13, 2025 - January 12, 2026

Subscription Details:
Plan: Premium Individual
Price: $9.99/month
Features:
- Ad-free music listening
- Offline downloads
- Unlimited skips
- High quality audio

Payment Information:
Amount: $9.99
Payment date: December 13, 2025
Payment method: Visa ending in ••4829

Next billing date: January 13, 2026
Next charge: $9.99

Transaction ID: spotify_ch_1A2B3C4D5E6F

View your receipt: https://www.spotify.com/us/account/receipt/?id=1A2B3C4D5E6F

Manage your subscription:
https://www.spotify.com/us/account/subscription/

Change payment method:
https://www.spotify.com/us/account/payment/

Cancel anytime (no fees):
https://www.spotify.com/us/account/subscription/cancel/

Questions about your subscription?
Visit our Support page: https://support.spotify.com/us/account_payment_help/
Contact us: https://support.spotify.com/us/contact-spotify-support/

Download Spotify:
https://www.spotify.com/us/download/

Spotify USA Inc.
150 Greenwich Street, Floor 62, New York, NY 10007
https://www.spotify.com''',
        'label': 0
    },
    {
        'sender': 'Microsoft 365 <microsoft365@mail.microsoft.com>',
        'subject': 'Your Microsoft 365 subscription has renewed',
        'body': '''Your subscription has been renewed

Subscription: Microsoft 365 Family
Subscription ID: MS365-FAM-8472938
Renewal date: December 13, 2025

Subscription Details:
Plan: Microsoft 365 Family (Annual)
Users: Up to 6 people
Next renewal: December 13, 2026

Payment Information:
Amount charged: $99.99
Payment method: Visa credit card ending in ••3847
Payment date: December 13, 2025

What's included in your subscription:
- Premium Office apps: Word, Excel, PowerPoint, Outlook, OneNote
- 1 TB of OneDrive cloud storage per person (up to 6 TB total)
- Advanced security features
- Ongoing technical support
- Works on Windows, macOS, iOS, and Android

Share your subscription:
Add family members: https://account.microsoft.com/services/microsoft365/familysettings

Manage your subscription:
View billing details: https://account.microsoft.com/services/microsoft365/details
Change payment method: https://account.microsoft.com/billing/payments
Cancel subscription: https://account.microsoft.com/services/microsoft365/cancel

Download Office apps:
https://www.microsoft.com/microsoft-365/download-office

View your invoice:
https://account.microsoft.com/billing/invoices?invid=INV-2025-12-8472938

Need help?
Visit Microsoft Support: https://support.microsoft.com/microsoft-365
Contact us: https://support.microsoft.com/contact

Microsoft Corporation
One Microsoft Way, Redmond, WA 98052
https://www.microsoft.com''',
        'label': 0
    },
    {
        'sender': 'Adobe <message@adobe.com>',
        'subject': 'Adobe Creative Cloud payment confirmation',
        'body': '''Payment confirmed

Adobe Creative Cloud - All Apps Plan
Subscription ID: CC-ALL-7293847

Payment Details:
Payment date: December 13, 2025
Amount: $54.99 USD
Payment method: PayPal (account ending in ••8293)
Invoice number: INV-2025-12-8472938

Your Plan Includes:
- 20+ Creative Cloud apps including:
  • Photoshop
  • Illustrator
  • Premiere Pro
  • After Effects
  • InDesign
  • Lightroom
  and more

- 100 GB of cloud storage
- Adobe Fonts (unlimited font library)
- Adobe Portfolio (build your website)
- Adobe Behance (showcase your work)

Next billing date: January 13, 2026
Next charge: $54.99

Download and manage apps:
https://creativecloud.adobe.com/apps

View your plan details:
https://account.adobe.com/plans

Manage payment methods:
https://account.adobe.com/billing/payment-methods

View invoice:
https://account.adobe.com/billing/invoices/INV-2025-12-8472938

Cancel anytime:
https://account.adobe.com/plans/cancel

Need help?
Adobe Support: https://helpx.adobe.com/support.html
Community Forums: https://community.adobe.com
Chat with us: https://helpx.adobe.com/contact.html
Call: 1-800-833-6687

Adobe Systems Incorporated
345 Park Avenue, San Jose, CA 95110
https://www.adobe.com''',
        'label': 0
    },
    {
        'sender': 'PG&E <customerservice@pge.com>',
        'subject': 'Your PG&E bill is ready - Amount due: $127.45',
        'body': '''Your bill is ready

Pacific Gas and Electric Company
Account number: 8472-9384-7293-001
Service address: 456 Oak Street, San Francisco, CA 94102

Bill Summary:
Bill date: December 13, 2025
Amount due: $127.45
Due date: January 2, 2026

Current Charges:
Electric service (Nov 12 - Dec 11, 2025): $89.30
- Energy charges: $76.50
- Delivery charges: $12.80

Gas service (Nov 12 - Dec 11, 2025): $38.15
- Gas charges: $32.40
- Delivery charges: $5.75

Previous balance: $0.00
Payments received: Thank you
Current amount due: $127.45

Usage Comparison:
Electric: 425 kWh (7% less than last year)
Gas: 28 therms (12% more than last year)

View your detailed bill:
https://www.pge.com/myaccount/viewbill?accountId=8472-9384-7293-001

Payment Options:
Pay online: https://www.pge.com/myaccount/pay
AutoPay (save time): https://www.pge.com/myaccount/autopay
By phone: Call 1-877-704-0880
By mail: PO Box 997300, Sacramento, CA 95899-7300

Set up payment arrangements if needed:
https://www.pge.com/myaccount/paymentarrangements

Track your energy use:
https://www.pge.com/myaccount/energyusage

Energy saving tips:
https://www.pge.com/en_US/residential/save-energy-money/savings-solutions-and-rebates/savings-solutions-and-rebates.page

Questions?
Visit: https://www.pge.com/myaccount/customerservice/help
Call: 1-800-743-5000 (24/7)

Pacific Gas and Electric Company
PO Box 770000, San Francisco, CA 94177
https://www.pge.com''',
        'label': 0
    },
    {
        'sender': 'GoDaddy <notify@godaddy.com>',
        'subject': 'Domain renewal receipt - mywebsite.com',
        'body': '''Domain renewal confirmed

Domain name: mywebsite.com
Renewal date: December 13, 2025
New expiration date: December 13, 2026

Order Details:
Order number: 483729384
Order date: December 13, 2025

Items:
Domain renewal - mywebsite.com (1 year): $17.99
ICANN fee: $0.18

Subtotal: $18.17
Total: $18.17

Payment Information:
Payment method: Visa ending in ••4829
Payment date: December 13, 2025

Auto-Renewal Status: ENABLED
Your domain will automatically renew on December 13, 2026

Domain Settings:
Domain lock: Enabled (recommended)
Privacy protection: Not enabled
DNS management: Active

Manage your domain:
https://dcc.godaddy.com/control/mywebsite.com/settings

Turn off auto-renewal:
https://dcc.godaddy.com/control/mywebsite.com/renewals

View invoice:
https://account.godaddy.com/orders/invoice/483729384

Build your website:
Use Website Builder: https://www.godaddy.com/websites/website-builder
WordPress hosting: https://www.godaddy.com/hosting/wordpress-hosting

Email Options:
Professional email: https://www.godaddy.com/email/professional-email
Microsoft 365: https://www.godaddy.com/email/microsoft-365

Need help?
24/7 Support: Call 1-480-505-8877
Help Center: https://www.godaddy.com/help
Community: https://community.godaddy.com

GoDaddy
14455 North Hayden Road, Suite 219, Scottsdale, AZ 85260
https://www.godaddy.com''',
        'label': 0
    },
    {
        'sender': 'Netflix <info@netflix.com>',
        'subject': 'Update your payment information',
        'body': '''Hi there,

We had trouble processing your payment for your Netflix subscription.

Account Information:
Email: user@email.com
Current plan: Premium (4 screens, Ultra HD)
Monthly cost: $19.99
Next billing date: December 18, 2025

What happened:
We were unable to charge your payment method on file.

What you need to do:
Update your payment information to continue enjoying Netflix.

Update payment method: https://www.netflix.com/account/billing

Your current payment method:
Credit card ending in ••4829

Alternate payment methods:
- Credit or debit card
- PayPal
- Netflix gift card

If you recently updated your payment information, please disregard this message. It may take up to 24 hours for changes to process.

Your Netflix membership:
- Unlimited movies and TV shows
- Watch on any device
- Download titles to watch offline
- No commitments, cancel anytime

Having trouble?
Visit our Help Center: https://help.netflix.com/support/23556
Contact us: https://help.netflix.com/contactus

Manage your account: https://www.netflix.com/youraccount

Netflix
100 Winchester Circle, Los Gatos, CA 95032
https://www.netflix.com''',
        'label': 0
    },
    {
        'sender': 'GitHub <noreply@github.com>',
        'subject': 'Pull request #847 merged in your repository',
        'body': '''Your pull request has been successfully merged

Repository: CompanyName/authentication-service
Pull request: #847 - Implement OAuth 2.0 authentication

Merged by: sarah-dev
Merged at: December 13, 2025, 2:30 PM PST
Branch: feature/oauth-integration → main

Changes included:
- Added OAuth 2.0 authentication flow
- Implemented user session management
- Updated security middleware
- Added comprehensive unit tests

Files changed: 12 files
Additions: 487 lines
Deletions: 123 lines

Commits: 8 commits
Contributors: 2 (john-dev, sarah-dev)

View the merged changes:
https://github.com/CompanyName/authentication-service/pull/847

View the commit:
https://github.com/CompanyName/authentication-service/commit/abc123def456

Repository:
https://github.com/CompanyName/authentication-service

Notifications settings:
https://github.com/settings/notifications

Unwatch this repository:
https://github.com/CompanyName/authentication-service/subscription

GitHub Team
88 Colin P Kelly Jr Street, San Francisco, CA 94107
https://github.com''',
        'label': 0
    },
    {
        'sender': 'LinkedIn <messages@linkedin.com>',
        'subject': 'Your connection request was accepted',
        'body': '''Sarah Martinez accepted your invitation

Sarah Martinez
Senior Software Engineer at Tech Corp
San Francisco Bay Area

You are now connected on LinkedIn

View Sarah's profile:
https://www.linkedin.com/in/sarah-martinez-engineer

Send Sarah a message:
https://www.linkedin.com/messaging/thread/new/?recipients=sarah-martinez-engineer

Suggestions for you:
• Endorse Sarah's skills
• Ask for a recommendation
• Explore mutual connections

You have 847 connections
Grow your network: https://www.linkedin.com/mynetwork

People you may know:
• Michael Chen - Product Manager at StartupCo
• Jennifer Kim - UX Designer at DesignStudio
• Robert Johnson - Data Scientist at AI Labs

See all suggestions:
https://www.linkedin.com/mynetwork/invite-connect/connections

Manage your network settings:
https://www.linkedin.com/psettings/connections

Turn off emails like this:
https://www.linkedin.com/psettings/email-frequency

LinkedIn Corporation
1000 West Maude Avenue, Sunnyvale, CA 94085
https://www.linkedin.com''',
        'label': 0
    },
    {
        'sender': 'Dropbox <no-reply@dropbox.com>',
        'subject': 'John Smith shared "Q4_Report.pdf" with you',
        'body': '''John Smith shared a file with you

File: Q4_Report.pdf
Size: 2.4 MB
Shared: December 13, 2025 at 3:15 PM

Message from John:
"Here's the final Q4 report for review. Please add your comments by Friday."

View file:
https://www.dropbox.com/s/abc123xyz789/Q4_Report.pdf

What you can do:
• View the file
• Download to your computer
• Add comments
• Share with others

Don't have Dropbox?
Create a free account to access this file and collaborate:
https://www.dropbox.com/register

Manage sharing settings:
https://www.dropbox.com/share/manage

Already a Dropbox user?
Sign in to view: https://www.dropbox.com/login

Dropbox Features:
- 2 GB free storage
- File synchronization across devices
- Easy sharing and collaboration
- Automatic backup

Upgrade for more space:
Dropbox Plus (2 TB): $11.99/month
https://www.dropbox.com/upgrade

Questions?
Help Center: https://www.dropbox.com/help
Community: https://www.dropboxforum.com

Dropbox
1800 Owens Street, San Francisco, CA 94158
https://www.dropbox.com''',
        'label': 0
    },
    {
        'sender': 'Slack <feedback@slack.com>',
        'subject': 'New message in #engineering channel',
        'body': '''New activity in #engineering

Workspace: TechCompany
Channel: #engineering

Sarah Chen posted:
"@channel The new API documentation is ready for review. Please check it out and leave feedback by EOD Friday. Thanks!"

Posted: December 13, 2025 at 4:30 PM

View in Slack:
https://techcompany.slack.com/archives/C012ABC3DEF/p1639425000

Reply in thread:
https://techcompany.slack.com/archives/C012ABC3DEF/p1639425000?thread_ts=1639425000

Channel information:
#engineering - 45 members
Purpose: Engineering team discussions and updates

Mentions you might have missed:
• 3 new messages in #engineering
• 1 direct message from John Davis
• 2 mentions in #general

Catch up now:
https://techcompany.slack.com/unreads

Download Slack mobile app:
iOS: https://apps.apple.com/app/slack/id618783545
Android: https://play.google.com/store/apps/details?id=com.Slack

Notification settings:
https://techcompany.slack.com/account/notifications

Slack Technologies, LLC
500 Howard Street, San Francisco, CA 94105
https://slack.com''',
        'label': 0
    },
    {
        'sender': 'Google Calendar <calendar-notification@google.com>',
        'subject': 'Reminder: Team Meeting in 1 hour',
        'body': '''Reminder: Team Meeting

When: Today, December 13, 2025
Time: 2:00 PM - 3:00 PM (PST)
Where: Conference Room A / Zoom

Organized by: sarah.manager@company.com

Attendees:
• You (john.developer@company.com)
• Sarah Manager
• Michael Designer
• Jennifer QA
6 more guests

Video call:
Join Zoom Meeting: https://zoom.us/j/1234567890
Meeting ID: 123 456 7890
Passcode: 847293

Agenda:
1. Sprint review
2. Q4 deliverables
3. Holiday schedule
4. Q&A

Calendar event:
https://calendar.google.com/calendar/event?eid=abc123xyz789

More options:
• Accept: https://calendar.google.com/calendar/event?action=RESPOND&eid=abc123xyz789&rst=1
• Decline: https://calendar.google.com/calendar/event?action=RESPOND&eid=abc123xyz789&rst=2
• View your calendar: https://calendar.google.com/calendar
• Change notifications: https://calendar.google.com/calendar/settings

Google Calendar
1600 Amphitheatre Parkway, Mountain View, CA 94043
https://calendar.google.com''',
        'label': 0
    },
    {
        'sender': 'DocuSign <dse@docusign.net>',
        'subject': 'Please sign: Employment Agreement - Tech Corp',
        'body': '''Please DocuSign: Employment Agreement

From: HR Department - Tech Corp
Subject: Employment Agreement - Tech Corp
Document: Employment_Agreement_JohnSmith_2025.pdf

Message from sender:
"Please review and sign your employment agreement. If you have any questions, feel free to reach out to HR at hr@techcorp.com before signing."

Signing deadline: December 20, 2025

Review and sign:
https://docusign.net/Member/PowerFormSigning.aspx?PowerFormId=abc123-def456-ghi789

Document details:
• Employment Agreement
• Pages: 8
• Your action: Signature required on pages 1, 5, and 8

What happens next:
1. Review the document carefully
2. Sign where indicated
3. Submit the signed document
4. You'll receive a completed copy via email

New to DocuSign?
Learn more about electronic signatures:
https://www.docusign.com/how-it-works/electronic-signature/esignature-legality

Security:
DocuSign uses bank-level security to protect your documents and information.

Questions about this document?
Contact the sender: hr@techcorp.com

DocuSign notifications:
Manage your settings: https://www.docusign.com/settings/notifications

DocuSign, Inc.
221 Main Street, Suite 1550, San Francisco, CA 94105
https://www.docusign.com''',
        'label': 0
    },
    {
        'sender': 'Zoom <no-reply@zoom.us>',
        'subject': 'Invitation: Project Kickoff Meeting - Dec 15',
        'body': '''You're invited to a Zoom meeting

Topic: Project Kickoff Meeting - Q1 2026 Initiatives
Host: Sarah Martinez (sarah.martinez@company.com)

Time: December 15, 2025, 10:00 AM Pacific Time (US and Canada)
Duration: 1 hour

Join Zoom Meeting:
https://zoom.us/j/98765432109?pwd=abc123XYZ789

Meeting ID: 987 6543 2109
Passcode: 472938

One tap mobile:
+16699009128,,98765432109#,,,,*472938# US (San Jose)
+13462487799,,98765432109#,,,,*472938# US (Houston)

Dial by your location:
+1 669 900 9128 US (San Jose)
+1 346 248 7799 US (Houston)
+1 253 215 8782 US (Tacoma)
+1 312 626 6799 US (Chicago)
+1 929 205 6099 US (New York)
+1 301 715 8592 US (Washington DC)

Find your local number: https://zoom.us/u/abcdefg123

Join by SIP:
98765432109@zoomcrc.com

Join by H.323:
162.255.37.11 (US West)
162.255.36.11 (US East)

Meeting agenda:
1. Project overview and objectives
2. Team introductions
3. Timeline and milestones
4. Resource allocation
5. Q&A

Add to calendar:
Google Calendar: https://zoom.us/meeting/98765432109/calendar/google
Outlook: https://zoom.us/meeting/98765432109/calendar/outlook
iCal: https://zoom.us/meeting/98765432109/ical

Need help?
Zoom Help Center: https://support.zoom.us
Test your connection: https://zoom.us/test

Zoom Video Communications, Inc.
55 Almaden Boulevard, 6th Floor, San Jose, CA 95113
https://zoom.us''',
        'label': 0
    },
    {
        'sender': 'Grammarly <hello@grammarly.com>',
        'subject': 'Your weekly writing stats are ready',
        'body': '''Your Weekly Writing Report

Week of December 7-13, 2025

Writing Stats:
• Total words checked: 12,847
• Documents: 23
• Suggestions accepted: 184
• Time saved: ~1.5 hours

Top improvements:
1. Clarity: 67 suggestions
2. Correctness: 52 suggestions  
3. Engagement: 38 suggestions
4. Delivery: 27 suggestions

Your writing this week:
Productivity: 15% more than last week
Accuracy: 94% (great job!)
Vocabulary: Using 8% more unique words

Most productive day:
Wednesday, December 11 - 3,492 words

Trending Topics:
Your most-used words this week:
• Project (used 24 times)
• Development (used 19 times)
• Analysis (used 16 times)

Writing goals:
Weekly goal: 10,000 words ✅ Achieved!
Set new goals: https://app.grammarly.com/goals

Explore Grammarly Premium:
• Advanced grammar suggestions
• Vocabulary enhancement
• Plagiarism detection
• Tone adjustments

Try Premium free for 7 days:
https://app.grammarly.com/upgrade

View detailed stats:
https://app.grammarly.com/stats/weekly/2025-12-07

Keep writing!
The Grammarly Team

Grammarly, Inc.
548 Market Street, #35410, San Francisco, CA 94104
https://www.grammarly.com''',
        'label': 0
    },
    {
        'sender': 'Canva <no-reply@canva.com>',
        'subject': 'Your design "Marketing Flyer" is ready',
        'body': '''Your design is ready to download

Design name: Marketing Flyer - December Campaign
Created: December 13, 2025
Type: Flyer (8.5" x 11")

What's next?
Download your design:
https://www.canva.com/design/ABC123XYZ789/download

Download options:
• PDF Print (recommended for printing)
• PNG (transparent background available)
• JPG (smaller file size)
• PDF Standard (for digital sharing)

Share your design:
Get a shareable link: https://www.canva.com/design/ABC123XYZ789/share
Invite team members to edit: https://www.canva.com/design/ABC123XYZ789/invite

Print your design:
Order professional prints: https://www.canva.com/print/ABC123XYZ789
• Business cards
• Posters
• Brochures
• More options available

Design tips:
Check out our design school for free tutorials:
https://www.canva.com/learn

Your Canva account:
Designs created: 47
Team members: 3
Storage used: 2.1 GB / 5 GB

Upgrade to Canva Pro:
• 100+ million premium photos
• 610,000+ premium templates
• Background remover
• Brand kit
• Resize designs instantly

Try Pro free for 30 days:
https://www.canva.com/pro/trial

View all your designs:
https://www.canva.com/folder/all-your-designs

Canva
110 Kippax Street, Surry Hills NSW 2010, Australia
https://www.canva.com''',
        'label': 0
    },
    {
        'sender': 'Mailchimp <login@mailchimp.com>',
        'subject': 'Campaign report: December Newsletter',
        'body': '''Campaign Report: December Newsletter

Campaign: December Newsletter 2025
Sent: December 13, 2025 at 9:00 AM
Recipients: 5,847 contacts

Performance Summary:
✅ Delivered: 5,829 (99.7%)
❌ Bounced: 18 (0.3%)

Engagement:
Opens: 1,749 (30.0%) - Above average!
Clicks: 382 (6.6%) - Above average!
Unsubscribes: 12 (0.2%)

Top clicked links:
1. "Shop Holiday Sale" - 187 clicks
   https://yourstore.com/holiday-sale

2. "Read Full Article" - 95 clicks
   https://yourblog.com/december-article

3. "Follow Us on Instagram" - 58 clicks
   https://instagram.com/yourcompany

Click map:
See which parts of your email got the most clicks:
https://mailchimp.com/reports/ABC123/click-map

Subscriber activity:
Most engaged subscribers:
• sarah.johnson@email.com (opened 3 times, clicked 2 links)
• michael.chen@email.com (opened 2 times, clicked 1 link)
• jennifer.kim@email.com (opened 1 time, clicked 1 link)

Geographic data:
Top locations:
1. New York, NY - 892 opens
2. Los Angeles, CA - 654 opens
3. Chicago, IL - 423 opens

View full report:
https://mailchimp.com/reports/ABC123/summary

Compare to previous campaigns:
https://mailchimp.com/reports/compare

Improve your next campaign:
• Subject line tips: https://mailchimp.com/resources/subject-lines
• Email design best practices: https://mailchimp.com/resources/email-design
• Increase engagement: https://mailchimp.com/resources/engagement

Create your next campaign:
https://mailchimp.com/campaigns/create

Mailchimp
675 Ponce de Leon Ave NE, Suite 5000, Atlanta, GA 30308
https://mailchimp.com''',
        'label': 0
    },
    {
        'sender': 'Trello <taco@trello.com>',
        'subject': 'You were added to the board "Product Roadmap Q1 2026"',
        'body': '''You've been added to a Trello board

Board: Product Roadmap Q1 2026
Added by: Sarah Martinez (sarah.martinez@company.com)
Workspace: Tech Company Team

View board:
https://trello.com/b/ABC123XYZ/product-roadmap-q1-2026

Board details:
• Lists: 5 (Backlog, To Do, In Progress, Review, Done)
• Cards: 23
• Members: 8
• Labels: Planning, Development, Design, Marketing, Launch

Recent activity:
• Sarah Martinez added you to this board
• Michael Chen moved "Feature: User Dashboard" to In Progress
• Jennifer Kim commented on "Bug: Login timeout"

Your role:
You can view, edit, and comment on cards in this board.

What you can do:
• Create new cards
• Move cards between lists
• Add comments and attachments
• Set due dates
• Assign members to cards

Get the Trello mobile app:
iOS: https://apps.apple.com/us/app/trello/id461504587
Android: https://play.google.com/store/apps/details?id=com.trello

Trello tips for new users:
https://trello.com/guide

Notification settings:
Manage what emails you receive from Trello:
https://trello.com/account/notifications

Trello
55 Broadway, 25th Floor, New York, NY 10006
https://trello.com''',
        'label': 0
    },
    {
        'sender': 'Asana <notify@asana.com>',
        'subject': 'New task assigned: Update website homepage',
        'body': '''You have a new task

Task: Update website homepage
Assigned by: Sarah Martinez
Project: Website Redesign 2026
Due date: December 20, 2025

View task:
https://app.asana.com/0/123456789/987654321

Task description:
Update the homepage with new hero image and revised copy. Coordinate with design team for final assets.

Subtasks:
☐ Get new hero image from design team
☐ Update homepage copy
☐ Review with marketing team
☐ Publish changes
☐ Test on mobile devices

Collaborators:
• You (john.developer@company.com)
• Michael Designer (design team)
• Jennifer Marketing (marketing team)

Recent activity:
• Sarah Martinez created this task
• Sarah Martinez set due date to Dec 20
• Michael Designer uploaded "Hero_Image_Final.jpg"

Project: Website Redesign 2026
Progress: 45% complete
Tasks: 12 completed, 15 in progress, 8 to do

View project:
https://app.asana.com/0/123456789

Comment on this task:
https://app.asana.com/0/123456789/987654321#comments

Mark complete:
https://app.asana.com/0/123456789/987654321/complete

Download Asana mobile app:
iOS: https://apps.apple.com/us/app/asana/id489969512
Android: https://play.google.com/store/apps/details?id=com.asana.app

Manage notification settings:
https://app.asana.com/0/my_settings/notifications

Asana
1550 Bryant Street, Suite 800, San Francisco, CA 94103
https://asana.com''',
        'label': 0
    },
    {
        'sender': 'Notion <team@makenotion.com>',
        'subject': 'Sarah Martinez shared "Project Documentation" with you',
        'body': '''Sarah Martinez shared a page with you

Page: Project Documentation - Authentication Service
Workspace: Tech Company
Shared: December 13, 2025 at 5:00 PM

Message from Sarah:
"Hey! I've compiled all the project documentation here. Please review and add any missing details by end of week. Thanks!"

View page:
https://www.notion.so/techcompany/Project-Documentation-abc123xyz789

Page contains:
• Project Overview
• Technical Architecture
• API Documentation
• Development Timeline
• Team Members
• Resources and Links

What you can do:
✅ View and read
✅ Add comments
✅ Edit content (full access)
✅ Share with others

Don't have a Notion account?
Sign up for free: https://www.notion.so/signup

Already have Notion?
Log in to view: https://www.notion.so/login

Notion features:
• Collaborative workspace
• Docs, wikis, and projects
• Real-time collaboration
• Powerful database
• Available on all devices

Get Notion mobile app:
iOS: https://apps.apple.com/us/app/notion/id1232780281
Android: https://play.google.com/store/apps/details?id=notion.id

Manage sharing settings:
https://www.notion.so/techcompany/settings/members

Turn off notifications like this:
https://www.notion.so/my-settings/notifications

Notion Labs, Inc.
2300 Harrison Street, San Francisco, CA 94110
https://www.notion.so''',
        'label': 0
    },
    {
        'sender': 'GitHub <notifications@github.com>',
        'subject': 'Security alert: New SSH key added to your account',
        'body': '''New SSH key added to your account

A new SSH key was just added to your GitHub account.

Key details:
Title: Work MacBook Pro
Fingerprint: SHA256:abc123def456ghi789jkl012mno345pqr678
Added: December 13, 2025 at 6:15 PM PST
IP address: 192.168.1.100

If you added this key:
No action needed. This email is just to let you know.

If you did NOT add this key:
Someone may have unauthorized access to your account.

Secure your account immediately:
1. Review your SSH keys: https://github.com/settings/keys
2. Remove any keys you don't recognize
3. Change your password: https://github.com/settings/security
4. Enable two-factor authentication: https://github.com/settings/two_factor_authentication

View your security log:
https://github.com/settings/security-log

All your SSH keys:
https://github.com/settings/keys

Best practices:
• Use unique, strong passwords
• Enable two-factor authentication
• Regularly review your security settings
• Don't share your SSH keys
• Remove old/unused keys

Learn more about SSH keys:
https://docs.github.com/authentication/connecting-to-github-with-ssh

Questions or concerns?
Contact GitHub Support: https://support.github.com/contact

GitHub Security Team
88 Colin P Kelly Jr Street, San Francisco, CA 94107
https://github.com''',
        'label': 0
    },
    {
        'sender': 'Steam <noreply@steampowered.com>',
        'subject': 'Your Steam purchase receipt',
        'body': '''Thank you for your purchase

Purchase date: December 13, 2025
Order #: 8472-9384-7293

Items purchased:
Cyberpunk Adventure 2077 - $59.99
Game DLC: Expansion Pack - $19.99

Subtotal: $79.98
Tax: $6.80
Total: $86.78

Payment method: Visa ending in ••4829

Your games are ready to download

Install Cyberpunk Adventure 2077:
steam://install/1234567

The DLC will be available in-game after installation.

Download Steam:
If you don't have Steam installed, download it here:
https://store.steampowered.com/about/

View your library:
https://store.steampowered.com/library

Purchase details:
https://store.steampowered.com/account/history

System requirements:
View before downloading: https://store.steampowered.com/app/1234567

Refund policy:
You can request a refund within 14 days of purchase if you've played less than 2 hours.
Request refund: https://help.steampowered.com/wizard/HelpWithPurchase

Community features:
• Join the discussion: https://steamcommunity.com/app/1234567/discussions
• View achievements: https://steamcommunity.com/stats/1234567/achievements
• Find guides: https://steamcommunity.com/app/1234567/guides

Need help?
Steam Support: https://help.steampowered.com
Community: https://steamcommunity.com

Valve Corporation
PO Box 1688, Bellevue, WA 98009
https://store.steampowered.com''',
        'label': 0
    },
    {
        'sender': 'Coursera <no-reply@coursera.org>',
        'subject': 'Certificate earned: Machine Learning Specialization',
        'body': '''Congratulations! You've earned a certificate

Course: Machine Learning Specialization
Completed: December 13, 2025
Instructor: Andrew Ng, Stanford University
Grade achieved: 94%

Certificate ID: ABC123XYZ789DEF456
Verify at: https://www.coursera.org/verify/ABC123XYZ789DEF456

View your certificate:
https://www.coursera.org/account/accomplishments/specialization/ABC123XYZ789DEF456

Download certificate:
• PDF: https://www.coursera.org/account/accomplishments/specialization/ABC123XYZ789DEF456/download
• Add to LinkedIn: https://www.coursera.org/account/accomplishments/specialization/ABC123XYZ789DEF456/linkedin

Course summary:
You've completed all 3 courses in this specialization:
✅ Supervised Machine Learning (Grade: 96%)
✅ Advanced Learning Algorithms (Grade: 93%)
✅ Unsupervised Learning (Grade: 93%)

Total time: 3 months
Skills gained:
• Machine Learning
• Deep Learning
• Neural Networks
• Python Programming
• TensorFlow

Share your achievement:
• Add to LinkedIn profile
• Include in your resume
• Share on social media

Continue your learning:
Recommended next courses:
• Deep Learning Specialization
• Advanced Machine Learning
• AI for Everyone

Browse all courses: https://www.coursera.org/browse

Your learning stats:
Courses completed: 8
Certificates earned: 6
Total learning time: 240 hours

View your dashboard:
https://www.coursera.org/degrees/dashboard

Questions?
Help Center: https://learner.coursera.help
Contact us: https://www.coursera.org/about/contact

Coursera
381 E. Evelyn Avenue, Mountain View, CA 94041
https://www.coursera.org''',
        'label': 0
    },
    {
        'sender': 'Duolingo <hello@duolingo.com>',
        'subject': 'You hit a 30-day streak! 🎉',
        'body': '''¡Felicidades! You've reached a 30-day streak!

Your Spanish learning streak: 30 days 🔥

December 13, 2025

Streak stats:
Current streak: 30 days
Longest streak: 30 days (new record!)
Total XP earned: 4,847
Level: 12

Today's progress:
Lessons completed: 2
XP earned today: 50
Time spent: 15 minutes

Recent achievements:
🏆 30-Day Streak
⭐ Level 12 Reached
📚 100 Lessons Completed
💪 Weekend Warrior

Your learning:
Words learned: 487
Fluency estimate: 24%
Lessons completed: 102

Keep it up! Extend your streak:
Complete today's lesson: https://www.duolingo.com/learn

Streak protection:
Equip a Streak Freeze to protect your streak (costs 10 Lingots)
Buy Streak Freeze: https://www.duolingo.com/shop/streak-freeze

Challenge yourself:
Join the December Challenge: Learn 500 XP this month
See leaderboard: https://www.duolingo.com/leaderboard

Duolingo Plus benefits:
• No ads
• Offline lessons
• Unlimited Hearts
• Monthly progress reports

Try Plus free for 14 days:
https://www.duolingo.com/plus

Download the app:
iOS: https://apps.apple.com/app/duolingo/id570060128
Android: https://play.google.com/store/apps/details?id=com.duolingo

Duolingo
5900 Penn Avenue, Pittsburgh, PA 15206
https://www.duolingo.com''',
        'label': 0
    },
    {
        'sender': 'Airbnb <automated@airbnb.com>',
        'subject': 'Get ready for your trip to Seattle',
        'body': '''Your trip is coming up soon!

Check-in: December 18, 2025 (in 5 days)
Check-out: December 21, 2025

Reservation code: HMAB82947293

Listing: Modern Downtown Loft
789 Pine Avenue, Seattle, WA 98101

Host: Alex Johnson
Superhost ⭐ 4.95 rating

Getting there:
Address: 789 Pine Avenue, Unit 3B, Seattle, WA 98101

Get directions: https://www.airbnb.com/trips/HMAB82947293/directions

Check-in instructions (available 48 hours before):
Will be sent on December 16 at 4:00 PM

Before you go:
☐ Review house rules
☐ Check-in time: 4:00 PM
☐ Check-out time: 11:00 AM
☐ Contact host with questions

House rules:
• No smoking
• No pets
• No parties or events
• Quiet hours: 10 PM - 8 AM

What's included:
✓ WiFi
✓ Kitchen
✓ Free parking
✓ Washer & Dryer
✓ Workspace

Contact your host:
Message Alex: https://www.airbnb.com/trips/HMAB82947293/messages

Phone: Available after check-in

Reservation details:
Guests: 2 adults
Nights: 3
Total paid: $450.00

View your trip: https://www.airbnb.com/trips/HMAB82947293

Manage reservation: https://www.airbnb.com/trips/HMAB82947293/manage

Cancel reservation: https://www.airbnb.com/trips/HMAB82947293/cancellations
Cancellation policy: Flexible (full refund if cancelled 24 hours before check-in)

Things to do in Seattle:
Explore the area: https://www.airbnb.com/s/Seattle/experiences

Get the Airbnb app:
iOS: https://apps.apple.com/app/airbnb/id401626263
Android: https://play.google.com/store/apps/details?id=com.airbnb.android

Need help?
Visit our Help Center: https://www.airbnb.com/help

Airbnb
888 Brannan Street, San Francisco, CA 94103
https://www.airbnb.com''',
        'label': 0
    },
    {
        'sender': 'Uber Eats <ubereats@uber.com>',
        'subject': 'Your order from Pizza Palace is on the way',
        'body': '''Your order is on the way!

Order from: Pizza Palace
123 Main Street, San Francisco, CA

Estimated arrival: 25-35 minutes
Delivery by: 7:45 PM

Track your order:
https://www.ubereats.com/orders/abc-123-xyz-789

Your order:
• Large Pepperoni Pizza - $18.99
• Garlic Bread (6 pieces) - $5.99
• 2L Coca-Cola - $3.99

Subtotal: $28.97
Delivery Fee: $2.99
Service Fee: $1.50
Tax: $2.61
Tip for delivery person: $5.00

Total: $41.07

Payment: Visa ending in ••4829

Delivery address:
456 Oak Avenue, Apt 4B
San Francisco, CA 94102

Meet at: Leave at door

Delivery person: Maria S.
Rating: ⭐ 4.9 (500+ deliveries)

Contact delivery person:
Call: (Tap to call in app)
Message: https://www.ubereats.com/orders/abc-123-xyz-789/chat

Rate your delivery:
After delivery, rate your experience to help others:
https://www.ubereats.com/orders/abc-123-xyz-789/rate

Reorder favorite meals:
Pizza Palace: https://www.ubereats.com/store/pizza-palace

Need help?
Get help with this order: https://www.ubereats.com/orders/abc-123-xyz-789/help
Visit Help Center: https://help.uber.com/ubereats

Download the app:
iOS: https://apps.apple.com/app/uber-eats/id1058959277
Android: https://play.google.com/store/apps/details?id=com.ubercab.eats

Uber Eats
1455 Market Street, San Francisco, CA 94103
https://www.ubereats.com''',
        'label': 0
    },
    {
        'sender': 'DoorDash <no-reply@doordash.com>',
        'subject': 'Your DoorDash order has been delivered',
        'body': '''Your order has been delivered!

Order from: Thai Kitchen
789 Food Street, Los Angeles, CA

Delivered: December 13, 2025 at 8:15 PM
Order #: DD-8472938473

Your order:
• Pad Thai (Chicken) - $13.99
• Spring Rolls (4 pcs) - $6.99
• Thai Iced Tea - $4.50

Subtotal: $25.48
Delivery Fee: $3.99
Service Fee: $1.50
Dasher Tip: $6.00
Tax: $2.29

Total: $39.26

Payment: Mastercard ending in ••3847

Delivered to:
321 Sunset Boulevard, Apt 12
Los Angeles, CA 90028

Left at door (as requested)
Photo of delivery: View in app

Your Dasher: James T.
Rating: ⭐ 5.0

Rate your experience:
How was your order? Rate now to help others:
https://www.doordash.com/orders/DD-8472938473/rate

Rate food quality (1-5 stars)
Rate delivery experience (1-5 stars)

Tip your Dasher:
Add an additional tip: https://www.doordash.com/orders/DD-8472938473/tip

Reorder:
Order again from Thai Kitchen:
https://www.doordash.com/store/thai-kitchen-los-angeles

View receipt:
https://www.doordash.com/orders/DD-8472938473/receipt

Issue with your order?
Get help: https://www.doordash.com/orders/DD-8472938473/help

DashPass members save on every order:
Join DashPass for $0 delivery fees: https://www.doordash.com/dashpass

Download DoorDash:
iOS: https://apps.apple.com/app/doordash/id719972451
Android: https://play.google.com/store/apps/details?id=com.dd.doordash

DoorDash
303 2nd Street, Suite 800, San Francisco, CA 94107
https://www.doordash.com''',
        'label': 0
    },
    {
        'sender': 'Peloton <news@onepeloton.com>',
        'subject': 'New personal record! You crushed it 🎉',
        'body': '''Congratulations on your new personal record!

Workout: 30 Min HIIT Ride
Instructor: Robin Arzón
Date: December 13, 2025
Time: 6:30 AM

Your stats:
Output: 487 kJ 🔥 NEW PERSONAL RECORD!
Avg Output: 162 watts
Distance: 8.2 miles
Calories: 310

Previous PR: 445 kJ
Improvement: +42 kJ (+9.4%)

Workout breakdown:
Total time: 30:00
Avg Resistance: 42
Avg Cadence: 85 RPM
Avg Speed: 16.4 mph

Leaderboard:
Your position: #847 out of 12,493 riders
Top 7% - Great job!

Milestones reached:
🏆 150 Total Rides
⭐ 50 HIIT Rides Completed
💪 10th PR This Month

View full workout stats:
https://members.onepeloton.com/classes/cycling?modal=classDetailsModal&classId=abc123xyz789

Share your achievement:
https://members.onepeloton.com/share/workout/abc123xyz789

Next recommended class:
45 Min Power Zone Endurance Ride with Matt Wilpers
Schedule: https://members.onepeloton.com/schedule/cycling

Your fitness journey:
Total workouts: 150
Active days this month: 18
Current streak: 5 days

Achievements unlocked:
View all badges: https://members.onepeloton.com/profile/achievements

Join the community:
Connect with other riders: https://members.onepeloton.com/social
#PelotonCommunity

Peloton membership:
All-Access Membership - $44/month
Next billing: January 13, 2026

Download the Peloton app:
iOS: https://apps.apple.com/app/peloton/id792750948
Android: https://play.google.com/store/apps/details?id=com.onepeloton.callisto

Peloton Interactive, Inc.
125 West 25th Street, New York, NY 10001
https://www.onepeloton.com''',
        'label': 0
    },
    {
        'sender': 'Strava <strava@strava.com>',
        'subject': 'You got 15 kudos on your morning run',
        'body': '''Your activity is getting love!

Activity: Morning Run 🏃
Date: December 13, 2025 at 6:45 AM

Stats:
Distance: 5.2 miles
Time: 42:18
Pace: 8:08 /mi
Elevation: 287 ft

Kudos: 15 👍
Comments: 3 💬

Recent kudos from:
• Sarah Johnson
• Michael Chen
• Jennifer Martinez
• Robert Kim
• and 11 others

Recent comments:
Sarah Johnson: "Great pace! 🔥"
Michael Chen: "Nice work on those hills!"
Jennifer Martinez: "Crushing it as always 💪"

Reply to comments:
https://www.strava.com/activities/10293847293

Activity highlights:
🏆 Fastest 1 mile: 7:32
📈 Best estimated effort: 156
💪 Calories: 487

Segment achievements:
• Oak Street Hill: 3rd place all-time
• Park Loop: Top 10% this year

View full activity:
https://www.strava.com/activities/10293847293

Share your activity:
https://www.strava.com/activities/10293847293/share

Your week in review:
Activities: 5
Distance: 18.7 miles
Time: 2h 35m
Elevation: 942 ft

Goals progress:
December running goal: 50 miles
Current: 32.4 miles (65% complete)

Join challenges:
December Distance Challenge: Run 100km this month
Join now: https://www.strava.com/challenges/december-distance

Strava Summit features:
• Advanced analytics
• Training plans
• Route planning
• Live segments

Try Summit free for 30 days:
https://www.strava.com/summit

Download Strava:
iOS: https://apps.apple.com/app/strava/id426826309
Android: https://play.google.com/store/apps/details?id=com.strava

Strava, Inc.
208 Utah Street, San Francisco, CA 94103
https://www.strava.com''',
        'label': 0
    },
    {
        'sender': 'Mint <noreply@mint.com>',
        'subject': 'Your December spending summary',
        'body': '''Your Monthly Spending Summary

December 2025 (Dec 1-13)

Total spending: $2,847.32

Spending by category:
🍔 Food & Dining: $687.45 (24%)
🏠 Home: $542.00 (19%)
🚗 Transportation: $398.50 (14%)
🛍️ Shopping: $445.20 (16%)
💳 Bills & Utilities: $427.45 (15%)
🎬 Entertainment: $246.72 (9%)
✈️ Travel: $100.00 (3%)

Budget status:
Food & Dining: $687 / $700 (98% used) ✅
Shopping: $445 / $400 (11% over budget) ⚠️
Entertainment: $247 / $300 (82% used) ✅

Compared to last month:
Total spending: -$342.18 (-11%) 📉
You're spending less - great job!

Top transactions this month:
• Dec 13: Whole Foods - $127.43
• Dec 12: Shell Gas Station - $65.00
• Dec 11: Amazon - $89.99
• Dec 10: PG&E (utility bill) - $127.45
• Dec 9: Spotify - $9.99

View all transactions:
https://mint.intuit.com/transactions

Unusual spending detected:
💡 Tip: You spent $156 more on shopping this week than usual

Net worth update:
Current net worth: $47,382
Change this month: +$1,245 (+2.7%) 📈

Accounts summary:
💰 Cash & Checking: $4,523
💳 Credit Cards: -$1,847
📊 Investments: $42,890
🏠 Property: $15,000
📉 Loans: -$13,184

Bills due soon:
• Dec 18: Credit card payment - $1,847.00
• Dec 20: Rent - $1,800.00
• Dec 31: Car insurance - $156.50

Set up bill reminders: https://mint.intuit.com/bills

Credit score update:
Current score: 742 (Good)
Change: +5 points this month 📈

Improve your score:
• Pay bills on time ✅
• Keep credit utilization under 30%
• Don't close old accounts

Money-saving tips:
💡 You could save $89/month by switching to a lower-cost phone plan
View recommendations: https://mint.intuit.com/ways-to-save

View full dashboard:
https://mint.intuit.com/overview

Download the Mint app:
iOS: https://apps.apple.com/app/mint/id300238550
Android: https://play.google.com/store/apps/details?id=com.mint

Mint by Intuit
2632 Marine Way, Mountain View, CA 94043
https://www.mint.com''',
        'label': 0
    },
    {
        'sender': 'Robinhood <noreply@robinhood.com>',
        'subject': 'Your weekly portfolio update',
        'body': '''Weekly Portfolio Summary

Week ending: December 13, 2025

Portfolio value: $12,847.52
Change this week: +$247.18 (+2.0%) 📈

Performance:
Best performer: Tech Stock ABC +8.4% 🚀
Worst performer: Retail Stock XYZ -3.2% 📉

Your holdings:
Stocks: $8,432.50 (66%)
ETFs: $2,890.00 (22%)
Crypto: $1,125.02 (9%)
Cash: $400.00 (3%)

Top holdings:
1. Tech Stock ABC - $2,450.00 (+8.4% this week)
2. S&P 500 ETF - $1,890.00 (+1.2% this week)
3. Growth Stock DEF - $1,275.00 (+5.7% this week)
4. Bitcoin - $847.50 (+3.2% this week)
5. Tech ETF - $1,000.00 (+2.1% this week)

Recent activity:
• Dec 13: Bought 5 shares of Tech Stock ABC @ $49.00
• Dec 12: Dividend received: $12.50 from Dividend Stock
• Dec 11: Sold 10 shares of Retail Stock XYZ @ $23.50

Dividends this month: $47.85

Market insights:
📊 S&P 500: +1.8% this week
📈 NASDAQ: +2.4% this week
💹 Dow Jones: +1.2% this week

View full portfolio:
https://robinhood.com/account/portfolio

Analyze your investments:
https://robinhood.com/account/investing

Upcoming earnings:
• Dec 18: Tech Stock ABC reports Q4 earnings

Set up price alerts:
Never miss important price movements:
https://robinhood.com/account/notifications

Learn & invest:
Browse investment ideas: https://robinhood.com/collections
Read market news: https://robinhood.com/news
Educational content: https://learn.robinhood.com

Download the Robinhood app:
iOS: https://apps.apple.com/app/robinhood/id938003185
Android: https://play.google.com/store/apps/details?id=com.robinhood.android

Robinhood Markets, Inc.
85 Willow Road, Menlo Park, CA 94025
https://robinhood.com

Investing involves risk. Please invest carefully.''',
        'label': 0
    },
    {
        'sender': 'Coinbase <no-reply@coinbase.com>',
        'subject': 'You received $50.00 in Bitcoin',
        'body': '''You received Bitcoin

Amount received: $50.00 in BTC
From: john.sender@email.com
Date: December 13, 2025 at 3:45 PM PST

Transaction details:
BTC amount: 0.00117584 BTC
Network: Bitcoin
Transaction ID: abc123def456ghi789jkl012mno345pqr678stu901vwx234yz

Note from sender:
"Thanks for dinner last night! 🍕"

View transaction:
https://www.coinbase.com/transactions/abc123def456ghi789jkl012mno345pqr678stu901vwx234yz

Your Bitcoin balance:
0.05847293 BTC ≈ $2,487.50

What you can do:
• Hold your Bitcoin
• Send to another wallet
• Convert to cash
• Trade for other crypto

Manage your crypto:
https://www.coinbase.com/dashboard

Current Bitcoin price:
$42,500.00 USD
24h change: +2.4% 📈

Convert Bitcoin:
Convert BTC to USD: https://www.coinbase.com/convert/BTC-USD
Explore other cryptocurrencies: https://www.coinbase.com/price

Earn rewards:
Learn about crypto and earn up to $50:
https://www.coinbase.com/earn

Security tips:
• Enable two-factor authentication
• Use a strong, unique password
• Never share your private keys
• Verify all transaction details

Set up price alerts:
https://www.coinbase.com/settings/notifications

Download Coinbase app:
iOS: https://apps.apple.com/app/coinbase/id886427730
Android: https://play.google.com/store/apps/details?id=com.coinbase.android

Coinbase, Inc.
100 Pine Street, Suite 1250, San Francisco, CA 94111
https://www.coinbase.com

Cryptocurrency is highly volatile. Invest responsibly.''',
        'label': 0
    }
]

# Legitimate Emails - Shipping Notifications (10 emails)
# Designed to teach model LEGITIMATE shipping notification patterns

legitimate_shipping_notifications = [
    {
        'sender': 'UPS <auto-notify@ups.com>',
        'subject': 'UPS delivery scheduled for today',
        'body': '''Hello,

Your package is out for delivery and scheduled to arrive today by end of day.

Tracking Number: 1Z9999W99999999999
Service: UPS Ground
Estimated Delivery: December 19, 2025

Package Details:
From: Amazon.com
Weight: 3.2 lbs

You can track your package at ups.com using your tracking number.

To change delivery preferences or provide delivery instructions, sign in to your UPS My Choice account.

Thank you for choosing UPS.''',
        'label': 0
    },
    {
        'sender': 'Amazon <ship-confirm@amazon.com>',
        'subject': 'Your Amazon.com order has shipped',
        'body': '''Hello,

Your package is on the way. Track your package to see delivery progress.

Order #112-8472956-3847291
Arriving: Thursday, December 19

Items in this shipment:
• Wireless Keyboard and Mouse Combo

Carrier: Amazon Logistics
Tracking ID: TBA847293847293847

You can track your shipment and view estimated delivery date in Your Orders.

Questions about your order? Visit our Help pages or contact Customer Service.

Thanks for shopping with us.
Amazon.com''',
        'label': 0
    },
    {
        'sender': 'FedEx <TrackingUpdates@fedex.com>',
        'subject': 'Shipment notification - Tracking 847293847293',
        'body': '''Shipment Information

Dear Customer,

We received your package and it's on its way.

Tracking number: 847293847293847
Ship date: December 18, 2025
Estimated delivery: December 20, 2025

Service: FedEx Ground
Shipper: Best Buy
Destination: Your city, Your state

Current status: In transit

Track your package at fedex.com/tracking

Thank you for using FedEx.''',
        'label': 0
    },
    {
        'sender': 'Target <orders@target.com>',
        'subject': 'Your Target order is on the way',
        'body': '''Hi there,

Good news! Your order is on the way.

Order number: 847293-847293
Order date: December 17, 2025
Estimated arrival: December 20-22, 2025

What's arriving:
• Bath towel set (Qty: 2)
• Kitchen organizer

Shipped via: USPS
Tracking number: 9405536897846291847293

Track your order in the Target app or at Target.com/orders

Questions? Our team is here to help at Target.com/contact

Thanks for shopping at Target!''',
        'label': 0
    },
    {
        'sender': 'Walmart <shipping@walmart.com>',
        'subject': 'Walmart order delivered',
        'body': '''Your Walmart order has been delivered.

Order #: 8472938472938472
Delivered: December 19, 2025 at 2:45 PM
Location: Front door

Items delivered:
• Laundry detergent, 150 oz
• Paper towels, 12 rolls

Carrier: FedEx
Tracking: 847293847293847

How was your delivery experience? Rate your delivery.

View your order details at Walmart.com/orders

Thank you for shopping with Walmart.''',
        'label': 0
    },
    {
        'sender': 'USPS Informed Delivery <USPSInformedDelivery@email.usps.com>',
        'subject': 'Your Informed Delivery Daily Digest for Thursday',
        'body': '''Informed Delivery Daily Digest
Thursday, December 19, 2025

Arriving Today:
• 2 pieces of mail
• 1 package

Package Tracking:
9405536897846291847293
Expected delivery: Today
Status: Out for Delivery
From: eBay seller

To manage your mail and packages, visit informeddelivery.usps.com

Download the USPS Mobile app for real-time updates.

This is an automated message from USPS Informed Delivery.''',
        'label': 0
    },
    {
        'sender': 'Best Buy <BestBuyInfo@emailinfo.bestbuy.com>',
        'subject': 'Your Best Buy order is ready for pickup',
        'body': '''Your order is ready!

Hi John,

Great news! Your order is ready for pickup at your selected store.

Order: BBY01-847293847293
Ready for pickup: December 19, 2025

Items ready:
• Sony WH-1000XM5 Headphones

Store: Best Buy - Downtown
Address: 123 Main Street
Hours: 10 AM - 9 PM

Bring your:
• Order confirmation email
• Photo ID

Pickup instructions: Go to Customer Service desk

Questions? Call your store at (555) 123-4567

Thanks for shopping at Best Buy!''',
        'label': 0
    },
    {
        'sender': 'Apple <no_reply@email.apple.com>',
        'subject': 'Your order has shipped',
        'body': '''Your order has shipped

Hi John,

Your order is on its way and will arrive on December 21, 2025.

Order: M847293847
Ship date: December 19, 2025

What's shipping:
• iPhone 15 Pro Case - Silicone

Track your shipment at apple.com/orderstatus with your order number.

Shipped via: UPS
Tracking number: 1Z9999W99999999999

You'll receive shipping updates via email and text (if you opted in).

If you have questions, visit apple.com/support

Apple Store Team''',
        'label': 0
    },
    {
        'sender': 'Etsy <transaction@etsy.com>',
        'subject': 'Your item from HandmadeStore has shipped',
        'body': '''Your order has shipped!

Hello,

Good news! HandmadeStore has shipped your order.

Order #: 847293847293
Ship date: December 19, 2025
Estimated delivery: December 23-26, 2025

Item: Custom leather wallet

Carrier: USPS First Class
Tracking: 9405536897846291847293

Track your package at etsy.com/your/orders

Message the seller with questions about your order.

Thanks for supporting independent sellers on Etsy!

The Etsy Team''',
        'label': 0
    },
    {
        'sender': 'Chewy <orders@chewy.com>',
        'subject': 'Chewy autoship order shipped - Arriving December 20',
        'body': '''Your Chewy Autoship has shipped!

Hello,

Your Autoship order is on the way.

Order #: 847293847
Ship date: December 19, 2025
Estimated arrival: December 20, 2025

What's arriving:
• Blue Buffalo Dog Food, 30 lb bag
• Greenies Dental Treats

Carrier: FedEx Ground
Tracking: 847293847293847

Track at chewy.com/myorders

Next Autoship: January 19, 2026
Manage your Autoship schedule anytime at chewy.com/autoship

Questions? Our Customer Service team is available 24/7.

Happy tails,
The Chewy Team''',
        'label': 0
    }
]

print(f"Created {len(legitimate_shipping_notifications)} legitimate shipping notification emails")
print("✓ Legitimate patterns: Official domains (@ups.com, @amazon.com), no payment requests, no urgency, helpful tracking info")


# Legitimate Emails - Subscription Renewals (10 emails)
# Designed to teach model LEGITIMATE subscription renewal patterns

legitimate_subscription_renewals = [
    {
        'sender': 'Microsoft 365 <msonline@microsoft.com>',
        'subject': 'Your Microsoft 365 subscription has renewed',
        'body': '''Hello,

Your Microsoft 365 Personal subscription has been renewed.

Subscription: Microsoft 365 Personal
Renewal date: December 19, 2025
Amount: $69.99 for 12 months
Payment method: Visa ending in 4829

What's included:
• Premium Office apps (Word, Excel, PowerPoint, Outlook)
• 1 TB OneDrive cloud storage
• Advanced security features

Your subscription will renew again on December 19, 2026.

Manage your subscription at account.microsoft.com/services

View your invoice at account.microsoft.com/billing

Questions? Visit support.microsoft.com

Thank you for choosing Microsoft 365.

Microsoft Account Team''',
        'label': 0
    },
    {
        'sender': 'Amazon Prime <account-update@amazon.com>',
        'subject': 'Your Amazon Prime membership renewed',
        'body': '''Hello,

Your Amazon Prime membership has been renewed.

Membership type: Amazon Prime (Annual)
Renewal date: December 19, 2025
Amount charged: $139.00
Payment method: Visa ending in 4829

Your Prime benefits:
• FREE Two-Day Shipping on millions of items
• Prime Video streaming
• Prime Music with 2 million songs
• Prime Reading
• Exclusive deals and discounts

Your membership will automatically renew on December 19, 2026.

Manage your Prime membership at amazon.com/prime

View payment history at amazon.com/billing

Questions? Visit amazon.com/primehelp

Thanks for being a Prime member!
Amazon Prime''',
        'label': 0
    },
    {
        'sender': 'Spotify <no-reply@spotify.com>',
        'subject': 'Your Spotify Premium subscription renewed',
        'body': '''Hey there,

Your Spotify Premium subscription has renewed successfully.

Plan: Spotify Premium Individual
Renewal: December 19, 2025
Price: $10.99/month
Payment: Mastercard ending in 3847

Keep enjoying:
• Ad-free music
• Offline listening
• Unlimited skips
• High quality audio

Your subscription renews monthly. Next charge: January 19, 2026.

Manage your subscription at spotify.com/account

View payment details at spotify.com/account/subscription

Need help? Visit support.spotify.com

Happy listening,
Spotify''',
        'label': 0
    },
    {
        'sender': 'Adobe <message@adobe.com>',
        'subject': 'Your Creative Cloud subscription renewed',
        'body': '''Hello,

Your Adobe Creative Cloud subscription has renewed.

Plan: Creative Cloud All Apps
Renewal date: December 19, 2025
Amount: $54.99/month
Payment: Visa ending in 4829

Your apps:
• Photoshop, Illustrator, Premiere Pro, After Effects, and 20+ more
• 100 GB cloud storage
• Adobe Portfolio website
• Adobe Fonts

Your next billing date is January 19, 2026.

Manage your plan at account.adobe.com

Download apps at creativecloud.adobe.com

Questions? Chat with us at adobe.com/support

Thank you for creating with Adobe.

Adobe Creative Cloud Team''',
        'label': 0
    },
    {
        'sender': 'Apple <no_reply@email.apple.com>',
        'subject': 'Your iCloud+ storage plan renewed',
        'body': '''Your iCloud+ subscription has renewed

Hi John,

Your iCloud+ subscription renewed successfully.

Plan: 200 GB iCloud+
Renewal: December 19, 2025
Price: $2.99/month
Payment: Apple Card ending in 4829

Your iCloud+ includes:
• 200 GB of storage
• iCloud Private Relay
• Hide My Email
• HomeKit Secure Video support

Your subscription renews monthly on the 19th.

Manage storage at icloud.com/settings
View subscriptions at apple.com/account/subscriptions

Need help? Visit support.apple.com

Apple''',
        'label': 0
    },
    {
        'sender': 'Netflix <info@account.netflix.com>',
        'subject': 'Your Netflix membership is active',
        'body': '''Hi John,

Your Netflix membership has renewed for another month.

Plan: Standard (2 screens, HD)
Renewal: December 19, 2025
Amount: $15.49/month
Payment: Mastercard ending in 3847

Keep enjoying unlimited movies and TV shows.

Your membership will automatically renew on January 19, 2026.

Update payment method: netflix.com/billing
Change your plan: netflix.com/ChangePlan
View account: netflix.com/YourAccount

Questions? Visit help.netflix.com

Happy watching,
Netflix''',
        'label': 0
    },
    {
        'sender': 'YouTube Premium <noreply-subscriptions@youtube.com>',
        'subject': 'YouTube Premium renewed',
        'body': '''Hi,

Your YouTube Premium membership renewed successfully.

Plan: YouTube Premium
Renewal: December 19, 2025
Price: $11.99/month
Payment: Visa ending in 4829

Your benefits:
• Ad-free videos
• Background play
• YouTube Music Premium
• Download videos offline

Your subscription auto-renews monthly.

Manage membership: youtube.com/paid_memberships
Update payment: payments.google.com

Need help? Visit support.google.com/youtube

YouTube Team''',
        'label': 0
    },
    {
        'sender': 'Dropbox <no-reply@dropbox.com>',
        'subject': 'Dropbox Plus subscription renewed',
        'body': '''Hi there,

Your Dropbox Plus subscription has renewed.

Plan: Dropbox Plus
Renewal: December 19, 2025
Amount: $11.99/month
Payment: Mastercard ending in 3847

What you get:
• 2 TB (2,000 GB) of space
• Share large files with Dropbox Transfer
• 30-day file recovery
• Priority email support

Your next billing date is January 19, 2026.

Manage account: dropbox.com/account
View billing: dropbox.com/account/billing

Questions? Contact support.dropbox.com

Thanks for being a Dropbox Plus member!

The Dropbox Team''',
        'label': 0
    },
    {
        'sender': 'Disney+ <DisneyPlus@mail.disneyplus.com>',
        'subject': 'Disney+ subscription renewed',
        'body': '''Hi,

Your Disney+ subscription has renewed successfully.

Plan: Disney+ (No Ads)
Renewal: December 19, 2025
Price: $13.99/month
Payment: Visa ending in 4829

Stream unlimited entertainment from Disney, Pixar, Marvel, Star Wars, and National Geographic.

Your subscription renews monthly on the 19th.

Manage subscription: disneyplus.com/account
Update payment: disneyplus.com/account/billing

Need help? Visit help.disneyplus.com

Thanks for streaming with Disney+!

Disney+ Team''',
        'label': 0
    },
    {
        'sender': 'Grammarly <premium@grammarly.com>',
        'subject': 'Your Grammarly Premium subscription renewed',
        'body': '''Hello,

Your Grammarly Premium subscription has renewed.

Plan: Grammarly Premium (Annual)
Renewal: December 19, 2025
Amount: $144.00 for 12 months
Payment: Visa ending in 4829

Premium features:
• Advanced grammar and punctuation checks
• Clarity suggestions
• Vocabulary enhancement
• Plagiarism detection
• Tone adjustments

Your subscription will renew on December 19, 2026.

Manage subscription: account.grammarly.com
View receipt: account.grammarly.com/receipts

Questions? Visit support.grammarly.com

Keep writing with confidence!

Grammarly Team''',
        'label': 0
    }
]

print(f"Created {len(legitimate_subscription_renewals)} legitimate subscription renewal emails")
print("✓ Legitimate patterns: Official domains, clear pricing, no urgency, manage subscription links, professional tone")