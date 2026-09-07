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

## Permanent product-photo storage (Render + Cloudflare R2)

Render's free filesystem is temporary. It can keep product names in PostgreSQL while deleting the corresponding image files on a redeploy, which causes image `404` errors in the app. Use Cloudflare R2 once to keep photos permanently.

1. In Cloudflare, open **R2 Object Storage** and create a bucket, for example `ari-smart-ro-media`.
2. In that bucket, open **Settings** and connect a public custom domain such as `media.yourdomain.com`. A public R2 development URL can be used for testing, but a custom domain is the production choice.
3. Create an R2 API token limited to this bucket with **Object Read & Write**. Copy the access key and secret immediately; do not send the secret in chat or store it in Git.
4. In Render, open `ari-smart-ro-api` → **Environment** and set the values below directly:

```text
DJANGO_MEDIA_STORAGE_BACKEND=s3
AWS_ACCESS_KEY_ID=<R2 access key>
AWS_SECRET_ACCESS_KEY=<R2 secret key>
AWS_STORAGE_BUCKET_NAME=ari-smart-ro-media
AWS_S3_REGION_NAME=auto
AWS_S3_ENDPOINT_URL=https://<Cloudflare account ID>.r2.cloudflarestorage.com
AWS_S3_CUSTOM_DOMAIN=media.yourdomain.com
```

5. Save the settings and deploy the latest code. Upload one test product image in Django Admin, then open it in the app. That image will remain available across redeploys.

Photos that were already deleted from Render cannot be recovered from the database because it only retains their file names. Re-upload each original source photo once after R2 is active; every photo uploaded after that is permanent until you deliberately delete it.

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
