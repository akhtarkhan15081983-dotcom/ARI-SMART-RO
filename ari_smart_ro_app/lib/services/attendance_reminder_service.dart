import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:timezone/data/latest.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

class AttendanceReminderService {
  static const _notificationId = 19019;
  static final _plugin = FlutterLocalNotificationsPlugin();

  static Future<void> initialize() async {
    tz.initializeTimeZones();
    tz.setLocalLocation(tz.getLocation('Asia/Kolkata'));
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    await _plugin.initialize(
      const InitializationSettings(android: android),
    );
    await _plugin
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >()
        ?.requestNotificationsPermission();
  }

  static Future<void> scheduleCheckout(DateTime reminderAt) async {
    await cancelCheckout();
    final at = tz.TZDateTime.from(reminderAt, tz.local);
    if (!at.isAfter(tz.TZDateTime.now(tz.local))) return;
    await _plugin.zonedSchedule(
      _notificationId,
      'Check-out बाकी है / Checkout reminder',
      'आपकी duty पूरी हो गई है। ARI SMART RO में check-out करना न भूलें।',
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

  static Future<void> cancelCheckout() => _plugin.cancel(_notificationId);
}
