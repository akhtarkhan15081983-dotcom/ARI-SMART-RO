# ARI SMART RO v1.0.16

## Notification & Alert Center
- Unified employee and customer notification inbox.
- Dashboard bell with unread badge.
- Admin broadcast by audience or employee role.
- Automatic leave, payroll, job, service, complaint and rent alerts.
- Read/unread tracking and deduplication.

## Customer Offers
- Festival and promotional campaigns.
- Rent, purchase, service, AMC and referral offer scopes.
- Percentage or fixed discounts.
- Optional promo code, minimum bill and maximum discount cap.
- Auto-apply support.
- Rent ledger stores original rent, discount and final rent.
- Purchase requests store base amount, discount and final amount.
- Offer redemption audit trail.

## Admin Control
- Notifications & Offers dashboard.
- Delivery/unread campaign metrics.
- Existing RBAC and admin full-control rules remain preserved.


## Validation hotfixes
- Preserved legacy employee RBAC defaults when no company membership exists.
- Public request throttling stays enabled in production and is disabled only by the CI/test flag.
- Notification Center Flutter build fix applied.
