# ARI SMART RO v1.0.25 — Customer Edit Stability & Admin Delegation

- Fixes the Flutter red-screen assertion seen when closing/saving the Customer Edit dialog in v1.0.24.
- Defers TextEditingController disposal until the dialog route has fully left the widget tree.
- Customer master editing is Admin-only by default.
- Admin can grant or revoke Customer Edit Access per employee from Employee Management.
- Backend enforces the effective permission; hiding the edit button is not the security boundary.
- Permanent customer deletion remains Admin-only.
- Retains all v1.0.24 training certificate features.
