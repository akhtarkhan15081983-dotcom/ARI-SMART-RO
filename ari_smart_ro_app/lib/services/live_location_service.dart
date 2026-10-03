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
import 'attendance_service.dart';
import 'location_point_envelope.dart';
import 'location_point_identity.dart';
import 'location_queue_store.dart';

const String _trackingEnabledKey = 'ari_live_location_tracking_enabled';
const String _legacyPendingLocationsKey = 'ari_live_location_pending_queue';
const String _notificationChannelId = 'ari_live_location';
const int _notificationId = 4091;
const Duration _trackingInterval = Duration(seconds: 20);
const Duration _primaryFixTimeout = Duration(seconds: 12);
const Duration _fallbackFixTimeout = Duration(seconds: 8);
const Duration _maxLastKnownAge = Duration(minutes: 2);
const double _maxFallbackAccuracyMeters = 250;

class LiveLocationException implements Exception {
  const LiveLocationException(this.message);
  final String message;

  @override
  String toString() => message;
}

class LiveLocationService {
  static const FlutterSecureStorage _storage = FlutterSecureStorage();
  static Future<void>? _initialization;

  static bool get isSupportedPlatform => Platform.isAndroid || Platform.isIOS;

  static Future<void> initialize() {
    if (!isSupportedPlatform) return Future<void>.value();
    final existing = _initialization;
    if (existing != null) return existing;

    final operation = _configure();
    _initialization = operation;
    return operation.catchError((Object error, StackTrace stackTrace) {
      if (identical(_initialization, operation)) {
        _initialization = null;
      }
      Error.throwWithStackTrace(error, stackTrace);
    });
  }

  static Future<void> _configure() async {
    await _migrateLegacyQueue();
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

  Future<void> ensureTrackingReady({bool requestPermissions = true}) async {
    if (!isSupportedPlatform) return;
    await initialize();
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
  }

  Future<void> startTracking({bool requestPermissions = true}) async {
    if (!isSupportedPlatform) return;
    await initialize();

    final service = FlutterBackgroundService();
    final trackingEnabled =
        await _storage.read(key: _trackingEnabledKey) == 'true';
    final serviceRunning = await service.isRunning();

    if (trackingEnabled && serviceRunning) {
      // Dashboard refresh/resume can call this repeatedly while an active shift
      // is already being tracked. Keep a cheap compliance check so revoked GPS
      // or background permission is surfaced, but never wait for another 12s +
      // 8s foreground GPS capture. The background isolate already ticks every
      // 20 seconds and remains the single location-capture loop.
      await ensureTrackingReady(requestPermissions: false);
      return;
    }

    await ensureTrackingReady(requestPermissions: requestPermissions);
    await _storage.write(key: _trackingEnabledKey, value: 'true');

    // Start the foreground service before any GPS work. The background entry
    // point executes tick() immediately and then every 20 seconds, so a second
    // UI-isolate sendCurrentLocation() here would duplicate network/GPS work and
    // can make dashboard refreshes feel slow on weak-GPS devices.
    if (!serviceRunning) {
      final started = await service.startService();
      if (!started) {
        await _storage.write(key: _trackingEnabledKey, value: 'false');
        throw const LiveLocationException(
          'Live location service could not start. Please reopen the app and try again.',
        );
      }
    }
  }

  Future<void> stopTracking() async {
    if (!isSupportedPlatform) return;
    await initialize();
    await _storage.write(key: _trackingEnabledKey, value: 'false');
    await _markOffline();
    final service = FlutterBackgroundService();
    if (await service.isRunning()) {
      service.invoke('stopService');
    }
  }

  Future<bool> isTracking() async {
    if (!isSupportedPlatform) return false;
    await initialize();
    final enabled = await _storage.read(key: _trackingEnabledKey) == 'true';
    if (!enabled) return false;
    return FlutterBackgroundService().isRunning();
  }

  Future<int> pendingLocationCount() async {
    if (!isSupportedPlatform) return 0;
    return LocationQueueStore.count();
  }

  Future<void> sendCurrentLocation() async {
    if (!isSupportedPlatform) return;
    await _syncPendingAttendanceBeforeLocation();
    await _flushPendingLocations();
    final stillEnabled = await _storage.read(key: _trackingEnabledKey) == 'true';
    if (!stillEnabled) return;
    final point = await _capturePoint();
    if (point == null) return;
    final sent = await _sendPoint(point);
    if (!sent) {
      await _queuePoint(point);
    }
  }

  static Future<void> _syncPendingAttendanceBeforeLocation() async {
    try {
      await AttendanceService().syncPendingOfflineActions();
    } catch (_) {
      // Attendance sync is best-effort here. A transient failure must not discard
      // queued attendance or location evidence. The server-side shift gate remains
      // authoritative and will stop tracking once it can be reached.
    }
  }

  static Future<Map<String, dynamic>?> _pointFromPosition(
    Position position, {
    required String source,
  }) async {
    final capturedAt = position.timestamp.toUtc();
    final platform = Platform.isIOS ? 'ios' : 'android';
    final sequence = await LocationQueueStore.nextClientSequence();
    final pointId = LocationPointIdentity.pointId(
      platform: platform,
      sequence: sequence,
      capturedAt: capturedAt,
    );

    return LocationPointEnvelope.build(
      latitude: position.latitude,
      longitude: position.longitude,
      accuracyMeters: position.accuracy,
      capturedAt: capturedAt,
      source: source,
      speedMps: position.speed,
      headingDegrees: position.heading,
      altitudeMeters: position.altitude,
      clientSequence: sequence,
      clientPointId: pointId,
      clientPlatform: platform,
    );
  }

  static bool _isUsableLastKnown(Position position) {
    final age = DateTime.now().toUtc().difference(position.timestamp.toUtc());
    return age <= _maxLastKnownAge &&
        position.accuracy.isFinite &&
        position.accuracy <= _maxFallbackAccuracyMeters;
  }

  static Future<Map<String, dynamic>?> _capturePoint() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) return null;
      final permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return null;
      }

      try {
        final position = await Geolocator.getCurrentPosition(
          locationSettings: const LocationSettings(
            accuracy: LocationAccuracy.high,
            timeLimit: _primaryFixTimeout,
          ),
        );
        return await _pointFromPosition(
          position,
          source: 'FRESH_HIGH_ACCURACY',
        );
      } catch (_) {
        // Continue to a faster balanced/network-assisted fix. This is important
        // indoors and on low-end phones where a high-accuracy satellite fix can
        // exceed the foreground tick window.
      }

      try {
        final position = await Geolocator.getCurrentPosition(
          locationSettings: const LocationSettings(
            accuracy: LocationAccuracy.medium,
            timeLimit: _fallbackFixTimeout,
          ),
        );
        return await _pointFromPosition(position, source: 'FRESH_BALANCED');
      } catch (_) {
        // Last-known fallback below is deliberately bounded by age and accuracy.
      }

      final lastKnown = await Geolocator.getLastKnownPosition();
      if (lastKnown != null && _isUsableLastKnown(lastKnown)) {
        return await _pointFromPosition(
          lastKnown,
          source: 'LAST_KNOWN_FALLBACK',
        );
      }
    } catch (_) {
      // The next tracking tick will try again. Never crash the field service.
    }
    return null;
  }

  static Future<http.Response> _postPoint(Map<String, dynamic> point) {
    return ApiService.authHeaders().then(
      (headers) => http
          .post(
            Uri.parse('${ApiService.baseUrl}/employees/live-location/'),
            headers: headers,
            body: jsonEncode(point),
          )
          .timeout(const Duration(seconds: 15)),
    );
  }

  static Future<http.Response> _postBatch(
    List<Map<String, dynamic>> points,
  ) {
    return ApiService.authHeaders().then(
      (headers) => http
          .post(
            Uri.parse('${ApiService.baseUrl}/employees/live-location/batch/'),
            headers: headers,
            body: jsonEncode(<String, dynamic>{'points': points}),
          )
          .timeout(const Duration(seconds: 20)),
    );
  }

  static Future<bool> _acceptSuccessfulResponse(http.Response response) async {
    if (response.statusCode < 200 || response.statusCode >= 300) return false;
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map && decoded['shift_active'] == false) {
        await _storage.write(key: _trackingEnabledKey, value: 'false');
      }
    } catch (_) {
      // Older backend responses may not include shift state.
    }
    return true;
  }

  static Future<bool> _sendPoint(Map<String, dynamic> point) async {
    try {
      var response = await _postPoint(point);
      if (await _acceptSuccessfulResponse(response)) {
        return true;
      }

      if (response.statusCode == 401) {
        final recovered = await ApiService.recoverSessionAfterUnauthorized();
        if (recovered) {
          response = await _postPoint(point);
          if (await _acceptSuccessfulResponse(response)) {
            return true;
          }
        }
      }

      return false;
    } catch (_) {
      return false;
    }
  }

  static Future<bool> _sendBatch(List<Map<String, dynamic>> points) async {
    if (points.isEmpty) return true;
    try {
      var response = await _postBatch(points);
      if (response.statusCode >= 200 && response.statusCode < 300) return true;

      if (response.statusCode == 401) {
        final recovered = await ApiService.recoverSessionAfterUnauthorized();
        if (recovered) {
          response = await _postBatch(points);
          return response.statusCode >= 200 && response.statusCode < 300;
        }
      }
      return false;
    } catch (_) {
      return false;
    }
  }

  static Future<void> _queuePoint(Map<String, dynamic> point) {
    return LocationQueueStore.append(point);
  }

  static Future<void> _flushPendingLocations() async {
    // Drain only one bounded batch per tracking tick. This prevents a large
    // offline backlog from starving capture of the employee's current position.
    final batch = await LocationQueueStore.readBatch();
    if (batch.isEmpty) return;
    if (!await _sendBatch(batch)) return;
    await LocationQueueStore.acknowledgeFirst(batch.length);
  }

  static Future<void> _migrateLegacyQueue() async {
    try {
      final raw = await _storage.read(key: _legacyPendingLocationsKey);
      if (raw == null || raw.isEmpty) return;
      final decoded = jsonDecode(raw);
      if (decoded is List) {
        for (final item in decoded.whereType<Map>()) {
          await LocationQueueStore.append(Map<String, dynamic>.from(item));
        }
      }
      await _storage.delete(key: _legacyPendingLocationsKey);
    } catch (_) {
      // Keep legacy data untouched if migration cannot complete.
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
  await LiveLocationService._migrateLegacyQueue();
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

      await LiveLocationService._syncPendingAttendanceBeforeLocation();
      await LiveLocationService._flushPendingLocations();
      final stillEnabledAfterFlush =
          await storage.read(key: _trackingEnabledKey) == 'true';
      if (!stillEnabledAfterFlush) {
        timer.cancel();
        await service.stopSelf();
        return;
      }

      final point = await LiveLocationService._capturePoint();
      var locationSent = false;
      if (point != null) {
        locationSent = await LiveLocationService._sendPoint(point);
        if (!locationSent) {
          await LiveLocationService._queuePoint(point);
        }
      }

      final shiftStillActive =
          await storage.read(key: _trackingEnabledKey) == 'true';
      if (!shiftStillActive) {
        timer.cancel();
        await service.stopSelf();
        return;
      }

      if (service is AndroidServiceInstance &&
          await service.isForegroundService()) {
        final time =
            '${DateTime.now().hour.toString().padLeft(2, '0')}:${DateTime.now().minute.toString().padLeft(2, '0')}';
        final pending = await LocationQueueStore.count();
        await service.setForegroundNotificationInfo(
          title: point == null
              ? 'ARI SMART RO • Waiting for GPS'
              : locationSent
                  ? 'ARI SMART RO • Live location ON'
                  : 'ARI SMART RO • Location queued safely',
          content: point == null
              ? 'GPS signal unavailable • tracking service is still running'
              : locationSent
                  ? 'Work shift tracking active • updated $time${pending > 0 ? ' • $pending pending' : ''}'
                  : 'Network issue • pending route points: $pending',
        );
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
