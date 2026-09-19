import 'package:flutter/services.dart';

class DeviceCapabilityService {
  DeviceCapabilityService._();

  static const MethodChannel _channel = MethodChannel(
    'com.arismartro.app/device_capabilities',
  );

  static Future<bool> isLowMemoryDevice() async {
    try {
      return await _channel.invokeMethod<bool>('isLowMemoryDevice') ?? false;
    } on PlatformException {
      return false;
    } on MissingPluginException {
      return false;
    }
  }
}
