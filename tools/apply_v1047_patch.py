from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected one match in {path}, found {count}: {old[:80]!r}")
    p.write_text(text.replace(old, new, 1))


# Stable device identity + migration headers.
path = 'ari_smart_ro_app/lib/services/api_service.dart'
replace_once(path, "import 'package:flutter_secure_storage/flutter_secure_storage.dart';\n", "import 'package:flutter_secure_storage/flutter_secure_storage.dart';\nimport 'package:flutter/services.dart';\n")
replace_once(path, '''  static final Map<String, String> _windowsMemory = <String, String>{};
  static const FlutterSecureStorage _secure = FlutterSecureStorage();

  Future<String?> read({required String key}) {
    if (Platform.isWindows) return Future.value(_windowsMemory[key]);
    return _secure.read(key: key);
  }

  Future<void> write({required String key, required String? value}) async {
    if (Platform.isWindows) {
      if (value == null) {
        _windowsMemory.remove(key);
      } else {
        _windowsMemory[key] = value;
      }
      return;
    }
    await _secure.write(key: key, value: value);
  }

  Future<void> delete({required String key}) async {
    if (Platform.isWindows) {
      _windowsMemory.remove(key);
      return;
    }
    await _secure.delete(key: key);
  }
''', '''  static const FlutterSecureStorage _secure = FlutterSecureStorage();

  Future<String?> read({required String key}) => _secure.read(key: key);

  Future<void> write({required String key, required String? value}) =>
      _secure.write(key: key, value: value);

  Future<void> delete({required String key}) => _secure.delete(key: key);
''')
replace_once(path, '  static const AriPlatformStorage storage = AriPlatformStorage();\n', "  static const AriPlatformStorage storage = AriPlatformStorage();\n  static const MethodChannel _deviceChannel = MethodChannel(\n    'com.arismartro.app/device_capabilities',\n  );\n")
replace_once(path, '''  static Future<Map<String, String>> deviceHeaders() async {
    final deviceId = await _deviceId();
    return <String, String>{
      "Content-Type": "application/json",
      "X-ARI-Device-ID": deviceId,
    };
  }
''', '''  static Future<Map<String, String>> deviceHeaders() async {
    final stableDeviceId = await _stableDeviceId();
    final legacyDeviceId = await _deviceId();
    final headers = <String, String>{
      "Content-Type": "application/json",
      "X-ARI-Device-ID": stableDeviceId,
      "X-ARI-Device-ID-Scheme": "stable-v1",
    };
    if (legacyDeviceId.isNotEmpty && legacyDeviceId != stableDeviceId) {
      headers["X-ARI-Legacy-Device-ID"] = legacyDeviceId;
    }
    return headers;
  }
''')
replace_once(path, '''  static Future<String> _deviceId() async {
    const key = "ari_device_id";
    final existing = await storage.read(key: key);
    if (existing != null && existing.isNotEmpty) return existing;
    final random = Random.secure();
    final value = List<int>.generate(
      24,
      (_) => random.nextInt(256),
    ).map((byte) => byte.toRadixString(16).padLeft(2, '0')).join();
    await storage.write(key: key, value: value);
    return value;
  }
''', '''  static Future<String> _deviceId() async {
    const key = "ari_device_id";
    final existing = await storage.read(key: key);
    if (existing != null && existing.isNotEmpty) return existing;
    final random = Random.secure();
    final value = List<int>.generate(
      24,
      (_) => random.nextInt(256),
    ).map((byte) => byte.toRadixString(16).padLeft(2, '0')).join();
    await storage.write(key: key, value: value);
    return value;
  }

  static Future<String> _stableDeviceId() async {
    if (Platform.isAndroid) {
      try {
        final nativeId = await _deviceChannel.invokeMethod<String>('getStableDeviceId');
        final clean = nativeId?.trim();
        if (clean != null && clean.isNotEmpty) return 'android-$clean';
      } on PlatformException {
        // Fall back to the persisted identity.
      } on MissingPluginException {
        // Fall back to the persisted identity.
      }
    }
    if (Platform.isWindows) {
      final host = Platform.localHostname.trim().toLowerCase();
      final user = (Platform.environment['USERNAME'] ?? '').trim().toLowerCase();
      return 'windows-${_fnv1a64('ARI-SMART-RO|$host|$user')}';
    }
    return _deviceId();
  }

  static String _fnv1a64(String input) {
    var hash = 0xcbf29ce484222325;
    for (final byte in utf8.encode(input)) {
      hash ^= byte;
      hash = (hash * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF;
    }
    return hash.toRadixString(16).padLeft(16, '0');
  }
''')

# Native Android stable ID.
path = 'ari_smart_ro_app/android/app/src/main/kotlin/com/arismartro/app/MainActivity.kt'
replace_once(path, 'import android.provider.MediaStore\n', 'import android.provider.MediaStore\nimport android.provider.Settings\n')
replace_once(path, '''            when (call.method) {
                "isLowMemoryDevice" -> {
''', '''            when (call.method) {
                "getStableDeviceId" -> {
                    val androidId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID).orEmpty()
                    result.success(androidId)
                }
                "isLowMemoryDevice" -> {
''')

# Server-side migration from legacy install IDs to stable IDs.
path = 'backend/accounts/views.py'
replace_once(path, '''            if user.active_login_device_id and user.active_login_device_id != device_id:
                _security_event(
                    request,
                    "LOGIN_DEVICE_BLOCKED",
                    user=user,
                    reason="OTHER_DEVICE_ACTIVE",
                )
                return Response(
                    {
                        "success": False,
                        "code": "EMPLOYEE_DEVICE_ALREADY_BOUND",
                        "message": (
                            "This employee ID is already active on another phone. "
                            "Ask Admin to reset the login device before using a new phone."
                        ),
                    },
                    status=status.HTTP_409_CONFLICT,
                )
''', '''            legacy_device_id = str(request.headers.get("X-ARI-Legacy-Device-ID", "") or "").strip()[:64]
            if user.active_login_device_id and user.active_login_device_id != device_id:
                if legacy_device_id and user.active_login_device_id == legacy_device_id:
                    user.previous_login_device_id = legacy_device_id
                    user.active_login_device_id = device_id
                    user.login_device_bound_at = timezone.now()
                    user.save(update_fields=["previous_login_device_id", "active_login_device_id", "login_device_bound_at"])
                    try:
                        employee = user.employee_profile
                    except Exception:
                        employee = None
                    if employee is not None and employee.attendance_device_id == legacy_device_id:
                        employee.attendance_device_id = device_id
                        employee.save(update_fields=["attendance_device_id"])
                else:
                    _security_event(request, "LOGIN_DEVICE_BLOCKED", user=user, reason="OTHER_DEVICE_ACTIVE")
                    return Response(
                        {
                            "success": False,
                            "code": "EMPLOYEE_DEVICE_ALREADY_BOUND",
                            "message": (
                                "This employee ID is already active on another phone. "
                                "Ask Admin to reset the login device before using a new phone."
                            ),
                        },
                        status=status.HTTP_409_CONFLICT,
                    )
''')

path = 'backend/accounts/authentication.py'
replace_once(path, 'from rest_framework_simplejwt.authentication import JWTAuthentication\n', 'from rest_framework_simplejwt.authentication import JWTAuthentication\nfrom django.utils import timezone\n')
replace_once(path, '''            if not device_id or device_id != bound_device_id:
                raise AuthenticationFailed(
                    "This employee session belongs to another phone.",
                    code="employee_device_mismatch",
                )
''', '''            if not device_id or device_id != bound_device_id:
                legacy_device_id = str(request.headers.get("X-ARI-Legacy-Device-ID", "") or "").strip()[:64]
                if device_id and legacy_device_id and legacy_device_id == bound_device_id:
                    user.previous_login_device_id = legacy_device_id
                    user.active_login_device_id = device_id
                    user.login_device_bound_at = timezone.now()
                    user.save(update_fields=["previous_login_device_id", "active_login_device_id", "login_device_bound_at"])
                    try:
                        employee = user.employee_profile
                    except Exception:
                        employee = None
                    if employee is not None and employee.attendance_device_id == legacy_device_id:
                        employee.attendance_device_id = device_id
                        employee.save(update_fields=["attendance_device_id"])
                    bound_device_id = device_id
                else:
                    raise AuthenticationFailed(
                        "This employee session belongs to another phone.",
                        code="employee_device_mismatch",
                    )
''')

# Preserve customer list position after returning from details.
path = 'ari_smart_ro_app/lib/screens/customer/customer_list_screen.dart'
replace_once(path, '  final TextEditingController _searchController = TextEditingController();\n', '  final TextEditingController _searchController = TextEditingController();\n  final ScrollController _scrollController = ScrollController();\n')
replace_once(path, '''  void dispose() {
    _searchController.dispose();

    super.dispose();
  }
''', '''  void dispose() {
    _searchController.dispose();
    _scrollController.dispose();

    super.dispose();
  }
''')
replace_once(path, '''  Future<void> _openCustomerDetails(CustomerModel customer) async {
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => CustomerDetailsScreen(customer: customer),
      ),
    );
    if (mounted) await _loadCustomers();
  }
''', '''  Future<void> _openCustomerDetails(CustomerModel customer) async {
    final previousOffset = _scrollController.hasClients ? _scrollController.offset : 0.0;
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => CustomerDetailsScreen(customer: customer)),
    );
    if (!mounted) return;
    await _loadCustomers();
    if (!mounted) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      final target = previousOffset.clamp(0.0, _scrollController.position.maxScrollExtent);
      _scrollController.jumpTo(target.toDouble());
    });
  }
''')
replace_once(path, '''              child: ListView(
                padding: const EdgeInsets.all(10),
''', '''              child: ListView(
                controller: _scrollController,
                key: const PageStorageKey<String>('customer-list-scroll'),
                padding: const EdgeInsets.all(10),
''')

# Manual no-bill purchase UI.
path = 'ari_smart_ro_app/lib/screens/inventory/inventory_workflow_screen.dart'
replace_once(path, '''                      TextField(
                        controller: invoice,
                        decoration: const InputDecoration(
                          labelText: 'Invoice number *',
                        ),
                      ),
''', '''                      TextField(
                        controller: invoice,
                        decoration: InputDecoration(
                          labelText: draft == null ? 'Bill / Invoice number (optional)' : 'Invoice number *',
                          helperText: draft == null ? 'No bill? Leave blank; an internal NO-BILL reference will be created.' : null,
                        ),
                      ),
''')
replace_once(path, '    if (ok && invoice.text.trim().isNotEmpty && supplierId != null) {\n', '    if (ok && supplierId != null && (draft == null || invoice.text.trim().isNotEmpty)) {\n')

# Low-RAM selfie capture profile.
path = 'ari_smart_ro_app/lib/screens/attendance/attendance_screen.dart'
replace_once(path, "import '../../services/attendance_reminder_service.dart';\n", "import '../../services/attendance_reminder_service.dart';\nimport '../../services/device_capability_service.dart';\n")
replace_once(path, '''    try {
      final image = await _imagePicker.pickImage(
        source: ImageSource.camera,
        preferredCameraDevice: CameraDevice.front,
        imageQuality: 72,
        maxWidth: 960,
        maxHeight: 1280,
      );
''', '''    try {
      final lowMemoryDevice = await DeviceCapabilityService.isLowMemoryDevice();
      final image = await _imagePicker.pickImage(
        source: ImageSource.camera,
        preferredCameraDevice: CameraDevice.front,
        imageQuality: lowMemoryDevice ? 60 : 72,
        maxWidth: lowMemoryDevice ? 720 : 960,
        maxHeight: lowMemoryDevice ? 960 : 1280,
      );
''')

# Version bump.
replace_once('ari_smart_ro_app/pubspec.yaml', 'version: 1.0.46+46\n', 'version: 1.0.47+47\n')

print('v1.0.47 patch applied successfully')

# trigger-runner
