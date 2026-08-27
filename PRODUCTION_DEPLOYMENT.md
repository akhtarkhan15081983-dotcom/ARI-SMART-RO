# ARI SMART RO production deployment

## Required services

- PostgreSQL database. Production refuses to start with SQLite.
- Durable media storage: an S3-compatible bucket or a persistent mounted volume.
- Customer OTP delivery through MSG91 or an HTTPS webhook.
- HTTPS API hostname.

Copy `.env.production.example` into the deployment platform's secret settings and replace every placeholder. Never commit the real values.

## OTP delivery

For India, configure an approved MSG91 OTP template and set:

```text
OTP_SMS_BACKEND=msg91
OTP_SMS_COUNTRY_CODE=91
MSG91_AUTH_KEY=...
MSG91_TEMPLATE_ID=...
```

The integration uses MSG91's official SendOTP endpoint. If delivery fails, the API invalidates the OTP and returns HTTP 503 instead of claiming that it was sent.

Official setup reference: https://docs.msg91.com/otp/sendotp

## Container deployment

```powershell
docker build -t ari-smart-ro .
docker run --env-file .env.production -p 8000:8000 ari-smart-ro
```

Container startup applies migrations, collects static files, and then starts Gunicorn as a non-root user. Configure the platform health check as:

```text
GET /health/
```

If `DJANGO_MEDIA_STORAGE_BACKEND=filesystem` is selected, mount the persistent volume at exactly `DJANGO_MEDIA_ROOT`. Prefer `s3` when the platform can run multiple containers.

## Android release

The permanent application ID is:

```text
com.arismartro.app
```

Create the upload key once and keep it backed up outside Git:

```powershell
keytool -genkeypair -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
Copy-Item android\key.properties.example android\key.properties
```

Fill `android/key.properties`, then build with the real HTTPS API URL:

```powershell
flutter build appbundle --release --dart-define=API_BASE_URL=https://api.your-domain.com/api
```

Release builds fail closed when signing configuration or `API_BASE_URL` is missing. CI compiles a release bundle with a CI-only debug signature to catch build failures; that artifact must never be uploaded to Play Console.

## GitHub release controls

After the production fix is merged into `main`, enable a branch ruleset for `main`:

- require pull requests;
- require the `backend`, `flutter`, and `container` checks;
- block force pushes and deletion;
- require the branch to be up to date before merge.

Create a signed tag such as `v1.0.0` only after staging smoke tests pass.
