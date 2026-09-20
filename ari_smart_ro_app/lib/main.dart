import 'package:flutter/material.dart';

import 'app.dart';
import 'services/attendance_reminder_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await AttendanceReminderService.initialize();

  runApp(const AriSmartROApp());
}
