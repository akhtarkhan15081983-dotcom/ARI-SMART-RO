import 'dart:async';
import 'dart:io';

import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

class AttendanceReminderService {
  static const _notificationId = 19019;
  static final _plugin = FlutterLocalNotificationsPlugin();
  static Future<void>? _initialization;
  static bool _permissionRequested = false;

  static Future<void> initialize({bool requestPermission = false}) async {
    if (!Platform.isAndroid) return;
    final existing = _initialization;
    if (existing != null) {
      await existing;
    } else {
      final operation = _initializePlugin();
      _initialization = operation;
      try {
        await operation;
      } catch (_) {
        if (identical(_initialization, operation)) {
          _initialization = null;
        }
        rethrow;
      }
    }
    if (requestPermission && !_permissionRequested) {
      final granted = await _plugin
          .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin
          >()
          ?.requestNotificationsPermission();
      _permissionRequested = granted != null;
    }
  }

  static Future<void> _initializePlugin() async {
    tz.initializeTimeZones();
    tz.setLocalLocation(tz.getLocation('Asia/Kolkata'));
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    await _plugin.initialize(
      const InitializationSettings(android: android),
    );
  }

  static Future<void> scheduleCheckout(DateTime reminderAt) async {
    if (!Platform.isAndroid) return;
    await initialize(requestPermission: true);
    await _plugin.cancel(_notificationId);
    final at = tz.TZDateTime.from(reminderAt, tz.local);
    if (!at.isAfter(tz.TZDateTime.now(tz.local))) return;
    await _plugin.zonedSchedule(
      _notificationId,
      'Regular shift complete / 8-hour duty complete',
      'ARI SMART RO आपकी regular shift को 8 hours पर auto-checkout करेगा। Overtime के लिए Admin approval जरूरी है।',
      at,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'attendance_checkout',
          'Attendance checkout reminders',
          channelDescription: 'Reminds checked-in employees to check out.',
          importance: Importance.high,
          priority: Priority.high,
        ),
      ),
      androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
      payload: 'attendance-checkout',
    );
  }

  static Future<void> cancelCheckout() async {
    if (!Platform.isAndroid) return;
    await initialize();
    await _plugin.cancel(_notificationId);
  }
}
