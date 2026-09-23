"""WhatsApp notifiers. Pick one with NOTIFIER=<name> in the environment / .env.

  console   - print only (default; safe for testing)
  meta      - official WhatsApp Cloud API (Meta). Business-initiated messages need an
              approved *template* (see docs/whatsapp.md). Free-form text only works within
              24h of the recipient messaging your business number.
  twilio    - Twilio WhatsApp (sandbox is quickest to try; prod also needs templates)
  callmebot - free unofficial personal API; only sends to your own number. Easiest start.

All config comes from env vars so nothing account-specific lives in code.
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Alert:
    title: str          # "Gold 24K /10g (bullions.co.in)"
    price: str          # "₹1,38,600"
    change_pct: float   # -10.2
    open_price: str     # "₹1,54,000"
    as_of: str          # "18 Sep 14:20 IST"
    text: str           # full free-form message


class NotifyError(Exception):
    pass


def _env(name: str, required: bool = True, default: Optional[str] = None) -> str:
    v = os.environ.get(name, default)
    if required and not v:
        raise NotifyError(f"missing env var {name}")
    return v or ""


def _recipients(var: str) -> List[str]:
    return [r.strip().lstrip("+") for r in _env(var).split(",") if r.strip()]


def _post(url: str, body: bytes, headers: Dict[str, str]) -> str:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        raise NotifyError(f"{url} -> HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}") from e
    except Exception as e:  # noqa: BLE001
        raise NotifyError(f"{url} failed: {e}") from e


class ConsoleNotifier:
    name = "console"

    def send(self, alert: Alert) -> None:
        print("----- ALERT (console notifier) -----")
        print(alert.text)
        print("------------------------------------")


class MetaCloudNotifier:
    """WhatsApp Cloud API. Env:
    WA_TOKEN, WA_PHONE_NUMBER_ID, WA_TO (comma list, intl format e.g. 9198xxxxxxx)
    WA_TEMPLATE (optional; if set, sends template with 5 body params), WA_TEMPLATE_LANG (default en)
    WA_GRAPH_VERSION (default v21.0)
    """
    name = "meta"

    def __init__(self) -> None:
        self.token = _env("WA_TOKEN")
        self.phone_id = _env("WA_PHONE_NUMBER_ID")
        self.to = _recipients("WA_TO")
        self.template = _env("WA_TEMPLATE", required=False)
        self.lang = _env("WA_TEMPLATE_LANG", required=False, default="en")
        self.version = _env("WA_GRAPH_VERSION", required=False, default="v21.0")

    def payload(self, to: str, alert: Alert) -> dict:
        if self.template:
            params = [alert.title, alert.price, f"{alert.change_pct:+.2f}%", alert.open_price, alert.as_of]
            return {
                "messaging_product": "whatsapp", "to": to, "type": "template",
                "template": {
                    "name": self.template, "language": {"code": self.lang},
                    "components": [{"type": "body",
                                    "parameters": [{"type": "text", "text": p} for p in params]}],
                },
            }
        return {"messaging_product": "whatsapp", "to": to, "type": "text",
                "text": {"preview_url": False, "body": alert.text}}

    def send(self, alert: Alert) -> None:
        url = f"https://graph.facebook.com/{self.version}/{self.phone_id}/messages"
        for to in self.to:
            _post(url, json.dumps(self.payload(to, alert)).encode(),
                  {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})


class TwilioNotifier:
    """Env: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM (e.g. 14155238886), WA_TO"""
    name = "twilio"

    def __init__(self) -> None:
        self.sid = _env("TWILIO_ACCOUNT_SID")
        self.auth = _env("TWILIO_AUTH_TOKEN")
        self.frm = _env("TWILIO_WHATSAPP_FROM").lstrip("+")
        self.to = _recipients("WA_TO")

    def send(self, alert: Alert) -> None:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Messages.json"
        basic = base64.b64encode(f"{self.sid}:{self.auth}".encode()).decode()
        for to in self.to:
            body = urllib.parse.urlencode({"From": f"whatsapp:+{self.frm}", "To": f"whatsapp:+{to}",
                                           "Body": alert.text}).encode()
            _post(url, body, {"Authorization": f"Basic {basic}",
                              "Content-Type": "application/x-www-form-urlencoded"})


class CallMeBotNotifier:
    """Env: CALLMEBOT_PHONE (your number, intl format), CALLMEBOT_APIKEY"""
    name = "callmebot"

    def __init__(self) -> None:
        self.phone = _env("CALLMEBOT_PHONE").lstrip("+")
        self.key = _env("CALLMEBOT_APIKEY")

    def send(self, alert: Alert) -> None:
        q = urllib.parse.urlencode({"phone": self.phone, "text": alert.text, "apikey": self.key})
        req = urllib.request.Request(f"https://api.callmebot.com/whatsapp.php?{q}")
        try:
            with urllib.request.urlopen(req, timeout=25) as r:
                r.read()
        except Exception as e:  # noqa: BLE001
            raise NotifyError(f"callmebot failed: {e}") from e


NOTIFIERS = {c.name: c for c in (ConsoleNotifier, MetaCloudNotifier, TwilioNotifier, CallMeBotNotifier)}


def get_notifier(name: Optional[str] = None):
    name = (name or os.environ.get("NOTIFIER") or "console").lower()
    if name not in NOTIFIERS:
        raise NotifyError(f"unknown NOTIFIER {name!r}; choose one of {sorted(NOTIFIERS)}")
    return NOTIFIERS[name]()
