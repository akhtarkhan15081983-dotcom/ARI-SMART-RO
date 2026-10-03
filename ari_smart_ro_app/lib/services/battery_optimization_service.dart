import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:permission_handler/permission_handler.dart';

class BatteryOptimizationService {
  const BatteryOptimizationService();

  static const FlutterSecureStorage _storage = FlutterSecureStorage();
  static const String _promptedKey = 'ari_battery_optimization_prompted_v1';

  Future<bool> isExempt() async {
    if (!Platform.isAndroid) return true;
    try {
      return (await Permission.ignoreBatteryOptimizations.status).isGranted;
    } catch (_) {
      return false;
    }
  }

  /// Android does not allow an app to silently whitelist itself from battery
  /// optimization. This method asks the employee once through the system-owned
  /// consent UI. A denial never blocks attendance or field work; Device Health
  /// continues to surface the remaining battery restriction.
  Future<bool> requestExemptionOnce() async {
    if (!Platform.isAndroid) return true;
    if (await isExempt()) return true;

    final prompted = await _storage.read(key: _promptedKey) == 'true';
    if (prompted) return false;
    await _storage.write(key: _promptedKey, value: 'true');

    try {
      final status = await Permission.ignoreBatteryOptimizations.request();
      return status.isGranted || await isExempt();
    } catch (_) {
      return false;
    }
  }
}
