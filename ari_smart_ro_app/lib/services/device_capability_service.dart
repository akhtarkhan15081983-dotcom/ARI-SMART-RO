import 'package:flutter/services.dart';

enum DevicePerformanceProfile {
  lowRam,
  standard,
  highMemory,
}

class DeviceCapabilityService {
  DeviceCapabilityService._();

  static const MethodChannel _channel = MethodChannel(
    'com.arismartro.app/device_capabilities',
  );

  static Future<bool> isLowMemoryDevice() async {
    return (await performanceProfile()) == DevicePerformanceProfile.lowRam;
  }

  static Future<DevicePerformanceProfile> performanceProfile() async {
    try {
      final health = await _channel.invokeMapMethod<String, dynamic>(
        'getDeviceHealth',
      );
      if (health == null) return DevicePerformanceProfile.standard;

      final lowMemory = health['low_memory_device'] == true;
      if (lowMemory) return DevicePerformanceProfile.lowRam;

      final totalMemoryMb = _asInt(health['total_memory_mb']);
      if (totalMemoryMb >= 6144) {
        return DevicePerformanceProfile.highMemory;
      }
      return DevicePerformanceProfile.standard;
    } on PlatformException {
      return DevicePerformanceProfile.standard;
    } on MissingPluginException {
      return DevicePerformanceProfile.standard;
    }
  }

  static int _asInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }
}
