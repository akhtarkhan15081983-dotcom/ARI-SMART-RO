# Customer Bulk Import + QR — Final Requirement

Status: **Accepted final requirement**

## Customer creation modes

1. **Single Customer**
   - Admin/Manager can add one customer from the app.
   - Customer ID and card number continue to auto-generate when not supplied.
   - A stable QR payload is available immediately after creation.

2. **Bulk Customer Import**
   - Admin/Manager can upload **XLSX** or **CSV**.
   - Maximum 5,000 rows per upload and 10 MB per file.
   - Minimum required columns: **Name** and **Phone**.
   - Supported optional fields: alternate phone, email, gender, address, area, city, state, pincode, RO model, installation charge, monthly rent, security deposit, installation date, old card number, new card number.
   - Duplicate phone numbers are skipped and reported.
   - Invalid rows are reported without blocking valid rows.
   - Preview mode is supported by the API before saving.

## QR behavior

Every customer has a deterministic QR value:

`ARI-SMART-RO:CUSTOMER:<CUSTOMER_ID>`

This means the QR does not need to be stored as an image. The app renders it from the customer ID whenever needed, so it stays consistent and avoids duplicate media files.

The QR is returned for:
- newly created single customers,
- every successfully bulk-imported customer,
- existing customers through the customer serializer / QR endpoint.

## Permissions

- Bulk import: **Admin / Manager**
- Single customer create: existing **Admin / Manager** permission
- QR view: Admin / Manager / Office; assigned Engineer; verified owning Customer

## API

- `POST /api/customers/bulk-import/`
- `GET /api/customers/<id>/qr/`
- Existing `POST /api/customers/create/` remains the single-customer endpoint.
