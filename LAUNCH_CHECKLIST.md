# ARI SMART RO launch checklist

## Backend

- Put the values from `.env.production.example` in the hosting provider's secret settings and replace every placeholder.
- Use PostgreSQL, HTTPS, persistent uploaded-media storage, and automated database/media backups.
- Run for each release:

  ```sh
  python manage.py check --deploy
  python manage.py makemigrations --check --dry-run
  python manage.py migrate --noinput
  python manage.py collectstatic --noinput
  python manage.py test
  ```

## Android signing

The permanent Android application ID is `com.arismartro.app`. Do not change it after the first Play Store release.

1. Create an upload keystore outside Git.
2. Copy `ari_smart_ro_app/android/key.properties.example` to `ari_smart_ro_app/android/key.properties` and add the real values.
3. Securely back up the keystore and passwords, and enable Google Play App Signing.

## Release build

Release builds require the deployed HTTPS API URL:

```sh
flutter clean
flutter pub get
flutter analyze
flutter test
flutter build appbundle --release --dart-define=API_BASE_URL=https://api.your-domain.com/api
```

Upload `build/app/outputs/bundle/release/app-release.aab` to Play Console Internal testing first.

## Physical-phone smoke test

- Fresh install, login/logout, expired session, and wrong password.
- Every supported role's dashboard and permissions.
- Complaints, jobs, installation, OTP, and payment flows.
- Camera, QR, microphone, location, maps, uploads, and signature.
- Offline/slow-network handling; confirm that logs expose no tokens or customer data.
- Complete the Play Store privacy policy, Data Safety, content rating, support, screenshots, and account-access sections before staged production rollout.
