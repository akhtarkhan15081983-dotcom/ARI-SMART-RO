# ARI Office SMS Gateway

Private, sideload-only Android app for the dedicated office SIM. It receives `ARI VERIFY ...` messages and forwards only those messages to the ARI backend.

Do not publish this app to Play Store or install it on customer devices.

Build using the repository's existing Gradle wrapper:

```powershell
cd E:\Projects\ARI-SMART-RO\ari_smart_ro_app\android
$env:GRADLE_USER_HOME='C:\Users\DELL\.gradle'
.\gradlew.bat -p E:\Projects\ARI-SMART-RO\office_sms_gateway :app:assembleDebug
```

Provision credentials after backend migrations:

```powershell
cd E:\Projects\ARI-SMART-RO\backend
.\.venv\Scripts\python.exe manage.py provision_sms_gateway OFFICE-01 --name "Main Office Gateway" --phone "YOUR_OFFICE_SIM_NUMBER"
```

Save the one-time `DEVICE_ID` and `GATEWAY_KEY` in the gateway app. During LAN pilot use `http://<laptop-ip>:8000/api`; production must use an HTTPS API URL.
