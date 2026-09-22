import 'package:flutter/material.dart';

import 'app.dart';
import 'services/attendance_reminder_service.dart';
import 'services/live_location_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AttendanceReminderService.initialize();
  await LiveLocationService.initialize();

  runApp(const AriSmartROApp());
}
