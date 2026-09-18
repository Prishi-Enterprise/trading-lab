# WhatsApp alert setup

Pick one provider → fill `.env` → `python3 -m goldtracker test-alert`.
Provider details change; double-check the linked consoles when setting up.

| Provider | Official? | Effort | Cost | Notes |
|---|---|---|---|---|
| `callmebot` | no (3rd-party) | 2 min | free | Only to your own number. Good for day 1. |
| `meta` (WhatsApp Cloud API) | yes | ~1 h + template approval | per-message pricing (utility templates) | Proper long-term option; sends from a business number. |
| `twilio` | yes (BSP) | 15 min sandbox | Twilio + Meta fees | Sandbox needs periodic re-join; prod needs templates too. |

## Option A — CallMeBot (fastest)
1. Follow the WhatsApp instructions on callmebot.com: save their number, send the activation
   phrase from your WhatsApp, receive your API key.
2. `.env`: `NOTIFIER=callmebot`, `CALLMEBOT_PHONE=91XXXXXXXXXX`, `CALLMEBOT_APIKEY=...`

## Option B — Meta WhatsApp Cloud API (official)
1. developers.facebook.com → **Create app** → type *Business* → add the **WhatsApp** product.
2. In *WhatsApp → API Setup* you get a free **test sender number**, its **Phone number ID**, and a
   temporary access token. Add your personal number as an allowed recipient (verify via OTP).
3. **Permanent token**: Meta Business Suite → Settings → Users → *System users* → add → assign
   the app + WhatsApp account → generate token with `whatsapp_business_messaging` (+ `whatsapp_business_management`).
4. **Template** (required for business-initiated messages outside the 24 h window):
   WhatsApp Manager → Message templates → Create → Category **Utility**, name `gold_price_alert`,
   language English, body with exactly 5 variables in this order:
   ```
   Gold price alert: {{1}} is now {{2}} ({{3}} vs today's open {{4}}). As of {{5}}.
   ```
   Sample values: `Gold 24K /10g (Ahmedabad bullion rate)`, `₹1,38,600`, `-10.05%`, `₹1,54,090`, `18 Sep 14:20 IST`.
   Wait for approval (usually minutes–hours).
5. `.env`:
   ```
   NOTIFIER=meta
   WA_TOKEN=<system user token>
   WA_PHONE_NUMBER_ID=<id from API Setup>
   WA_TO=91XXXXXXXXXX            # comma-separate for family members
   WA_TEMPLATE=gold_price_alert
   WA_TEMPLATE_LANG=en
   ```
   Leave `WA_TEMPLATE` empty to send free-form text — only delivered if the recipient messaged
   the business number within the last 24 h.
6. Later, to send from your own business number: add & verify a real number in WhatsApp Manager
   (it must not be active on the regular WhatsApp app), and complete business verification.

## Option C — Twilio
1. twilio.com console → Messaging → *Try it out* → **WhatsApp sandbox**; join by sending the shown
   `join <code>` message from your phone.
2. `.env`: `NOTIFIER=twilio`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`,
   `TWILIO_WHATSAPP_FROM=<sandbox number>`, `WA_TO=91XXXXXXXXXX`.

## Message format (free-form providers)
```
🔻 Gold alert – Ahmedabad
Gold 24K /10g (Ahmedabad bullion rate): ₹1,38,600
Today's open: ₹1,54,090 (10:40 IST)
Change: -10.05% (threshold -10%)
As of 18 Sep 14:20 IST
```
