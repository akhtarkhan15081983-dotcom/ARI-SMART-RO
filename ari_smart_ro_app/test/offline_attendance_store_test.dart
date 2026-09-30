import 'dart:convert';
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
      if (await temp.exists()) await temp.delete(recursive: true);
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

    test('concurrent writers preserve every committed action', () async {
      final first = OfflineAttendanceStore(rootDirectoryOverride: temp);
      final second = OfflineAttendanceStore(rootDirectoryOverride: temp);
      await Future.wait(List<Future<void>>.generate(12, (index) {
        final writer = index.isEven ? first : second;
        return writer.enqueue(<String, dynamic>{
          'action_id': 'concurrent-$index',
          'action': 'CHECK_OUT',
          'captured_at': '2026-09-30T10:${index.toString().padLeft(2, '0')}:00.000Z',
        });
      }));
      final pending = await store.pending();
      expect(pending, hasLength(12));
      expect(pending.map((row) => row['action_id']).toSet(), hasLength(12));
    });

    test('valid temp is recovered when primary is corrupt', () async {
      final primary = File('${temp.path}/pending_attendance_actions_v1.json');
      final tempFile = File('${primary.path}.tmp');
      await primary.writeAsString('{broken');
      await tempFile.writeAsString(jsonEncode(<Map<String, dynamic>>[
        <String, dynamic>{
          'action_id': 'temp-recovered',
          'action': 'CHECK_OUT',
          'captured_at': '2026-09-30T11:00:00.000Z',
        },
      ]));
      final pending = await store.pending();
      expect(pending.single['action_id'], 'temp-recovered');
      expect(await tempFile.exists(), isFalse);
      final quarantine = Directory('${temp.path}/corrupt_state');
      expect(await quarantine.exists(), isTrue);
    });

    test('backup recovers last committed queue after corrupt primary', () async {
      await store.enqueue(<String, dynamic>{
        'action_id': 'backup-recovered',
        'action': 'CHECK_OUT',
        'captured_at': '2026-09-30T12:00:00.000Z',
      });
      final primary = File('${temp.path}/pending_attendance_actions_v1.json');
      await primary.writeAsString('not-json', flush: true);
      final recovered = OfflineAttendanceStore(rootDirectoryOverride: temp);
      final pending = await recovered.pending();
      expect(pending.single['action_id'], 'backup-recovered');
      expect(jsonDecode(await primary.readAsString()), isA<List<dynamic>>());
    });
  });
}
