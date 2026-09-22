import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:ui';

import 'package:flutter/widgets.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'package:permission_handler/permission_handler.dart' as permissions;

import 'api_service.dart';

const String _trackingEnabledKey = 'ari_live_location_tracking_enabled';
const String _pendingLocationsKey = 'ari_live_location_pending_queue';
const String _notificationChannelId = 'ari_live_location';
const int _notificationId = 4091;
const Duration _trackingInterval = Duration(seconds: 20);
const int _maxPendingLocations = 30;

class LiveLocationException implements Exception {
  const LiveLocationException(this.message);
  final String message;

  @override
  String toString() => message;
}

class LiveLocationService {
  static const FlutterSecureStorage _storage = FlutterSecureStorage();

  static bool get isSupportedPlatform => Platform.isAndroid || Platform.isIOS;

  static Future<void> initialize() async {
    if (!isSupportedPlatform) return;
    final service = FlutterBackgroundService();

    if (Platform.isAndroid) {
      const channel = AndroidNotificationChannel(
        _notificationChannelId,
        'Employee live location',
        description:
            'Shows while ARI SMART RO is sharing an employee location during an active shift.',
        importance: Importance.low,
        showBadge: false,
      );
      final notifications = FlutterLocalNotificationsPlugin();
      await notifications
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.createNotificationChannel(channel);
    }

    await service.configure(
      androidConfiguration: AndroidConfiguration(
        onStart: liveLocationBackgroundEntryPoint,
        autoStart: false,
        autoStartOnBoot: true,
        isForegroundMode: true,
        notificationChannelId: _notificationChannelId,
        initialNotificationTitle: 'ARI SMART RO',
        initialNotificationContent: 'Live location is active for your work shift.',
        foregroundServiceNotificationId: _notificationId,
        foregroundServiceTypes: const [AndroidForegroundType.location],
      ),
      iosConfiguration: IosConfiguration(
        autoStart: false,
        onForeground: liveLocationBackgroundEntryPoint,
        onBackground: liveLocationIosBackground,
      ),
    );
  }

  Future<void> startTracking({bool requestPermissions = true}) async {
    if (!isSupportedPlatform) return;
    if (!await Geolocator.isLocationServiceEnabled()) {
      throw const LiveLocationException(
        'GPS is turned off. Turn on Location to start work tracking.',
      );
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied && requestPermissions) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied) {
      throw const LiveLocationException(
        'Location permission is required for live employee tracking.',
      );
    }
    if (permission == LocationPermission.deniedForever) {
      throw const LiveLocationException(
        'Location permission is blocked. Open phone Settings and allow location for ARI SMART RO.',
      );
    }

    if (Platform.isAndroid) {
      try {
        if (requestPermissions) {
          await permissions.Permission.notification.request();
        }
      } catch (_) {
        // Notification permission does not block the foreground location service.
      }

      var background = await permissions.Permission.locationAlways.status;
      if (!background.isGranted && requestPermissions) {
        background = await permissions.Permission.locationAlways.request();
      }
      if (!background.isGranted) {
        throw const LiveLocationException(
          'For live tracking, set ARI SMART RO Location permission to "Allow all the time".',
        );
      }
    }

    await _storage.write(key: _trackingEnabledKey, value: 'true');
    await sendCurrentLocation();

    final service = FlutterBackgroundService();
    if (!await service.isRunning()) {
      final started = await service.startService();
      if (!started) {
        throw const LiveLocationException(
          'Live location service could not start. Please reopen the app and try again.',
        );
      }
    }
  }

  Future<void> stopTracking() async {
    if (!isSupportedPlatform) return;
    await _storage.write(key: _trackingEnabledKey, value: 'false');
    await _markOffline();
    final service = FlutterBackgroundService();
    if (await service.isRunning()) {
      service.invoke('stopService');
    }
  }

  Future<bool> isTracking() async {
    if (!isSupportedPlatform) return false;
    final enabled = await _storage.read(key: _trackingEnabledKey) == 'true';
    if (!enabled) return false;
    return FlutterBackgroundService().isRunning();
  }

  Future<int> pendingLocationCount() async {
    if (!isSupportedPlatform) return 0;
    return (await _readQueue()).length;
  }

  Future<void> sendCurrentLocation() async {
    if (!isSupportedPlatform) return;
    await _flushPendingLocations();
    final point = await _capturePoint();
    if (point == null) return;
    final sent = await _sendPoint(point);
    if (!sent) {
      await _queuePoint(point);
    }
  }

  static Future<Map<String, dynamic>?> _capturePoint() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) return null;
      final permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return null;
      }

      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 20),
        ),
      );

      return <String, dynamic>{
        'live_latitude': position.latitude,
        'live_longitude': position.longitude,
        'accuracy': position.accuracy,
        'captured_at': position.timestamp.toUtc().toIso8601String(),
      };
    } catch (_) {
      return null;
    }
  }

  static Future<bool> _sendPoint(Map<String, dynamic> point) async {
    try {
      final response = await http
          .post(
            Uri.parse('${ApiService.baseUrl}/employees/live-location/'),
            headers: await ApiService.authHeaders(),
            body: jsonEncode(point),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return true;
      }
      if (response.statusCode == 401) {
        await _storage.write(key: _trackingEnabledKey, value: 'false');
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  static Future<void> _queuePoint(Map<String, dynamic> point) async {
    final queue = await _readQueue();
    queue.add(point);
    if (queue.length > _maxPendingLocations) {
      queue.removeRange(0, queue.length - _maxPendingLocations);
    }
    await _storage.write(
      key: _pendingLocationsKey,
      value: jsonEncode(queue),
    );
  }

  static Future<void> _flushPendingLocations() async {
    final queue = await _readQueue();
    if (queue.isEmpty) return;

    var sentCount = 0;
    for (final point in queue) {
      if (!await _sendPoint(point)) break;
      sentCount++;
    }
    if (sentCount == 0) return;

    final remaining = queue.sublist(sentCount);
    if (remaining.isEmpty) {
      await _storage.delete(key: _pendingLocationsKey);
    } else {
      await _storage.write(
        key: _pendingLocationsKey,
        value: jsonEncode(remaining),
      );
    }
  }

  static Future<List<Map<String, dynamic>>> _readQueue() async {
    try {
      final raw = await _storage.read(key: _pendingLocationsKey);
      if (raw == null || raw.isEmpty) return <Map<String, dynamic>>[];
      final decoded = jsonDecode(raw);
      if (decoded is! List) return <Map<String, dynamic>>[];
      return decoded
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .toList();
    } catch (_) {
      return <Map<String, dynamic>>[];
    }
  }

  static Future<void> _markOffline() async {
    try {
      await http
          .post(
            Uri.parse('${ApiService.baseUrl}/employees/live-location/'),
            headers: await ApiService.authHeaders(),
            body: jsonEncode(<String, dynamic>{'tracking_active': false}),
          )
          .timeout(const Duration(seconds: 8));
    } catch (_) {
      // Stale-location logic on the server will still mark the employee offline.
    }
  }
}

@pragma('vm:entry-point')
Future<bool> liveLocationIosBackground(ServiceInstance service) async {
  WidgetsFlutterBinding.ensureInitialized();
  DartPluginRegistrant.ensureInitialized();
  return true;
}

@pragma('vm:entry-point')
void liveLocationBackgroundEntryPoint(ServiceInstance service) async {
  WidgetsFlutterBinding.ensureInitialized();
  DartPluginRegistrant.ensureInitialized();

  final storage = const FlutterSecureStorage();
  var timer = Timer(const Duration(days: 3650), () {});
  var busy = false;

  Future<void> tick() async {
    if (busy) return;
    busy = true;
    try {
      final enabled =
          await storage.read(key: _trackingEnabledKey) == 'true';
      if (!enabled) {
        timer.cancel();
        await service.stopSelf();
        return;
      }

      await LiveLocationService._flushPendingLocations();
      final point = await LiveLocationService._capturePoint();
      var locationSent = false;
      if (point != null) {
        locationSent = await LiveLocationService._sendPoint(point);
        if (!locationSent) {
          await LiveLocationService._queuePoint(point);
        }
      }

      if (service is AndroidServiceInstance &&
          await service.isForegroundService()) {
        final time =
            '${DateTime.now().hour.toString().padLeft(2, '0')}:${DateTime.now().minute.toString().padLeft(2, '0')}';
        await service.setForegroundNotificationInfo(
          title: locationSent
              ? 'ARI SMART RO • Live location ON'
              : 'ARI SMART RO • Location required',
          content: locationSent
              ? 'Work shift tracking active • updated $time'
              : 'GPS/permission is off or network failed. Open the app now.',
        );
      }

      final stillEnabled =
          await storage.read(key: _trackingEnabledKey) == 'true';
      if (!stillEnabled) {
        timer.cancel();
        await service.stopSelf();
      }
    } finally {
      busy = false;
    }
  }

  service.on('stopService').listen((_) async {
    timer.cancel();
    await service.stopSelf();
  });

  final enabled = await storage.read(key: _trackingEnabledKey) == 'true';
  if (!enabled) {
    await service.stopSelf();
    return;
  }

  await tick();
  timer = Timer.periodic(_trackingInterval, (_) => tick());
}
