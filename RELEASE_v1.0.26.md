# ARI SMART RO v1.0.26

## Single-device employee login security

- Employee accounts (Manager, Engineer, Office and Calling) are bound to one ARI SMART RO app installation at a time.
- The first successful login registers that phone as the employee's active login device.
- The same employee phone/password cannot be used to sign in from a second phone while the first device remains registered.
- Device enforcement happens on both login and authenticated backend API requests, so copying an access token does not bypass the restriction.
- Admin Employee Management now shows whether a login phone is registered and provides **Reset Login Device**.
- Resetting a login device immediately invalidates the employee's old-device session. The next successful login registers the replacement phone.
- Customer accounts are unaffected.
- Admin accounts remain exempt so an administrator can recover employee access after a lost, damaged or replaced phone.
- Security events record blocked cross-device login attempts and admin device resets.
- Includes automated backend tests for first-device binding, same-device login, second-device blocking, token/device mismatch and reset invalidation.
