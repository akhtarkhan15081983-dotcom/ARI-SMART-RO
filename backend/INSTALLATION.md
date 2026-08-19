# ARI Referral & Wallet — Backend V1

This package adds the referral/wallet domain without changing the existing `customers`, `jobs`, `inventory`, `employees`, or rent-payment code.

## 1. Copy the app

Copy the `referrals` folder into:

`E:\Projects\ARI-SMART-RO\backend\referrals`

## 2. Add to settings

In `config/settings.py`, add:

```python
"referrals",
```

to `INSTALLED_APPS`.

## 3. Add URLs

In the main project `config/urls.py`, add:

```python
path("api/referrals/", include("referrals.urls")),
```

Make sure `include` is imported:

```python
from django.urls import include, path
```

## 4. Migrate

Run:

```powershell
python manage.py makemigrations referrals
python manage.py migrate
```

## 5. Tests

Run:

```powershell
python manage.py test referrals
python manage.py test accounts customers employees inventory jobs referrals
```

## API V1

- `GET /api/referrals/me/` — referral code + rewards + referrals
- `POST /api/referrals/claim/` — `{ "referral_code": "ARIXXXXXXX" }`
- `POST /api/referrals/welcome/claim/` — one-time ₹50 welcome reward
- `GET /api/referrals/wallet/` — wallet balance
- `GET /api/referrals/wallet/history/` — immutable ledger history
- `POST /api/referrals/wallet/quote/` — server-side max wallet usage quote
- `POST /api/referrals/wallet/redeem/` — atomic wallet redemption
- `POST /api/referrals/<id>/qualify/` — staff qualification endpoint

## Important integration boundary

The `qualify` endpoint is deliberately staff-controlled in V1. This avoids falsely rewarding a referral merely because a customer profile exists. Later, the real purchase completion and rent/installation completion flows should call `qualify_referral()` automatically at the exact business event that makes a referral successful.

The current project already has customer rent/payment management and purchase APIs, so those event integrations should be added only after their exact qualifying transaction fields are confirmed.

## Business rules implemented

- App welcome reward: ₹50
- Welcome reward validity: 90 days
- Welcome reward maximum: 40% of an eligible bill
- No cash withdrawal/conversion endpoint
- Rent → Rent: ₹600 total (₹50 × 12), rent only
- Rent → Purchase: 15% of qualifying purchase amount, rent only
- Purchase → Rent: ₹600 total, rent only, fully usable
- Purchase → Purchase: qualifying purchase benefit, fully usable for RO/parts/service/purchase
- Minimum payable rent floor: ₹100 for the ₹50/month rent referral benefit
- Self-referral blocked
- One referral attribution per referred account
- Wallet ledger + reward buckets
- Atomic redemption
- Reward expiry/reversal states
