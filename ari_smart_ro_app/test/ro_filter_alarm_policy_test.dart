import 'package:ari_smart_ro_app/widgets/ro_filter_alarm_guard.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('ROFilterAlarmPolicy', () {
    test('open and acknowledged filter alarms remain active', () {
      expect(
        ROFilterAlarmPolicy.isActiveFilterAlarm({
          'alarm_type': 'FILTER_DUE',
          'status': 'OPEN',
        }),
        isTrue,
      );
      expect(
        ROFilterAlarmPolicy.isActiveFilterAlarm({
          'alarm_type': 'FILTER_DUE',
          'status': 'ACKNOWLEDGED',
        }),
        isTrue,
      );
    });

    test('resolved filter alarm and other alarm types are inactive', () {
      expect(
        ROFilterAlarmPolicy.isActiveFilterAlarm({
          'alarm_type': 'FILTER_DUE',
          'status': 'RESOLVED',
        }),
        isFalse,
      );
      expect(
        ROFilterAlarmPolicy.isActiveFilterAlarm({
          'alarm_type': 'SERVICE_DUE',
          'status': 'OPEN',
        }),
        isFalse,
      );
    });

    test('matching filter complaint stops reminders', () {
      expect(
        ROFilterAlarmPolicy.complaintFieldsStopReminder(
          complaintType: 'FILTER_PROBLEM',
          status: 'NEW',
          description: '[RO-ALARM:42] Filter change requested.',
          alarmId: 42,
        ),
        isTrue,
      );
    });

    test('cancelled or unrelated complaint does not stop reminders', () {
      expect(
        ROFilterAlarmPolicy.complaintFieldsStopReminder(
          complaintType: 'FILTER_PROBLEM',
          status: 'CANCELLED',
          description: '[RO-ALARM:42] Filter change requested.',
          alarmId: 42,
        ),
        isFalse,
      );
      expect(
        ROFilterAlarmPolicy.complaintFieldsStopReminder(
          complaintType: 'FILTER_PROBLEM',
          status: 'NEW',
          description: '[RO-ALARM:41] Filter change requested.',
          alarmId: 42,
        ),
        isFalse,
      );
      expect(
        ROFilterAlarmPolicy.complaintFieldsStopReminder(
          complaintType: 'WATER_LEAKAGE',
          status: 'NEW',
          description: '[RO-ALARM:42] Leakage complaint.',
          alarmId: 42,
        ),
        isFalse,
      );
    });
  });
}
