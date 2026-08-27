import 'dart:math';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class DeviceIdentityService {
  static const _storage = FlutterSecureStorage();
  static const _key = 'attendance_device_id';

  static Future<String> getOrCreate() async {
    final existing = await _storage.read(key: _key);
    if (existing != null && existing.trim().isNotEmpty) return existing;

    final random = Random.secure();
    final bytes = List<int>.generate(32, (_) => random.nextInt(256));
    final id = bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();
    await _storage.write(key: _key, value: id);
    return id;
  }
}
