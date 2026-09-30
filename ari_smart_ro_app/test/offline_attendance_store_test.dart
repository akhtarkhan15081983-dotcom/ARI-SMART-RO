import 'dart:io';

import 'package:ari_smart_ro_app/services/offline_attendance_store.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('OfflineAttendanceStore', () {
    late Directory temp;
    late OfflineAttendanceStore store;

    setUp(() async {
      temp = await Directory.systemTemp.createTemp('ari-offline-attendance-');
      store = OfflineAttendanceStore(rootDirectoryOverride: temp);
    });

    tearDown(() async {
      if (await temp.exists()) {
        await temp.delete(recursive: true);
      }
    });

    test('enqueue is durable and action ids are de-duplicated', () async {
      final action = <String, dynamic>{
        'action_id': 'action-1234567890',
        'action': 'CHECK_OUT',
        'captured_at': '2026-09-30T10:00:00.000Z',
      };

      await store.enqueue(action);
      await store.enqueue(action);

      final pending = await store.pending();
      expect(pending, hasLength(1));
      expect(pending.single['action'], 'CHECK_OUT');
      expect(await store.count(), 1);
    });

    test('preserved selfie survives until successful removal', () async {
      final source = File('${temp.path}/camera-selfie.jpg');
      await source.writeAsBytes(List<int>.generate(32, (index) => index));
      const actionId = 'action-selfie-123456';
      final preserved = await store.preserveSelfie(source.path, actionId);

      await store.enqueue(<String, dynamic>{
        'action_id': actionId,
        'action': 'CHECK_IN',
        'captured_at': '2026-09-30T10:00:00.000Z',
        'selfie_path': preserved,
      });

      expect(await File(preserved).exists(), isTrue);
      await store.remove(actionId);
      expect(await File(preserved).exists(), isFalse);
      expect(await store.count(), 0);
    });

    test('remove can retain media for dead-letter evidence', () async {
      final source = File('${temp.path}/camera-selfie.jpg');
      await source.writeAsBytes(List<int>.filled(24, 7));
      const actionId = 'action-deadletter-1234';
      final preserved = await store.preserveSelfie(source.path, actionId);

      await store.enqueue(<String, dynamic>{
        'action_id': actionId,
        'action': 'CHECK_IN',
        'captured_at': '2026-09-30T10:00:00.000Z',
        'selfie_path': preserved,
      });

      await store.remove(actionId, deleteMedia: false);
      expect(await File(preserved).exists(), isTrue);
      expect(await store.count(), 0);
    });
  });
}
