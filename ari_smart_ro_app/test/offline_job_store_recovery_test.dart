import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:ari_smart_ro_app/services/offline_action_dead_letter_store.dart';
import 'package:ari_smart_ro_app/services/offline_job_store.dart';

void main() {
  late Directory tempDir;
  late OfflineJobStore store;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('ari-offline-job-test-');
    store = OfflineJobStore(rootDirectoryOverride: tempDir);
  });

  tearDown(() async {
    if (await tempDir.exists()) {
      await tempDir.delete(recursive: true);
    }
  });

  test('corrupt primary is quarantined and last-known-good backup recovers', () async {
    await store.queueAction(
      type: 'STATUS',
      jobId: 101,
      payload: const <String, dynamic>{'status': 'ACCEPTED'},
      actionId: 'action-1',
    );
    await store.queueAction(
      type: 'GPS',
      jobId: 101,
      payload: const <String, dynamic>{
        'latitude': 28.61,
        'longitude': 77.20,
      },
      actionId: 'action-2',
    );

    final primary = File('${tempDir.path}/offline_job_state_v1.json');
    final backup = File('${tempDir.path}/offline_job_state_v1.backup.json');
    expect(await primary.exists(), isTrue);
    expect(await backup.exists(), isTrue);

    await primary.writeAsString('{broken-json', flush: true);

    final recovered = await store.pendingActions();
    expect(recovered, hasLength(1));
    expect(recovered.single['id'], 'action-1');

    final quarantine = Directory('${tempDir.path}/corrupt_state');
    expect(await quarantine.exists(), isTrue);
    expect(await quarantine.list().where((item) => item is File).isEmpty, isFalse);

    final log = File('${tempDir.path}/offline_job_recovery_events.jsonl');
    expect(await log.exists(), isTrue);
    final events = await log.readAsLines();
    expect(events, isNotEmpty);
    final event = jsonDecode(events.last) as Map<String, dynamic>;
    expect(event['reason'], 'PRIMARY_STATE_CORRUPT');
    expect(event['recovered_from'], 'offline_job_state_v1.backup.json');
  });

  test('corrupt primary without backup is preserved before clean fallback', () async {
    final primary = File('${tempDir.path}/offline_job_state_v1.json');
    await primary.writeAsString('not-json', flush: true);

    final pending = await store.pendingActions();
    expect(pending, isEmpty);

    final quarantine = Directory('${tempDir.path}/corrupt_state');
    final quarantined = await quarantine.list().where((item) => item is File).toList();
    expect(quarantined, hasLength(1));
    expect(await (quarantined.single as File).readAsString(), 'not-json');

    final log = File('${tempDir.path}/offline_job_recovery_events.jsonl');
    final event = jsonDecode((await log.readAsLines()).last) as Map<String, dynamic>;
    expect(event['reason'], 'PRIMARY_STATE_CORRUPT_NO_VALID_BACKUP');
  });

  test('valid temp state is recovered after interrupted primary replacement', () async {
    final primary = File('${tempDir.path}/offline_job_state_v1.json');
    final temp = File('${primary.path}.tmp');
    await primary.writeAsString('{broken-primary', flush: true);
    await temp.writeAsString(
      jsonEncode(<String, dynamic>{
        'jobs': <String, dynamic>{},
        'queue': <dynamic>[
          <String, dynamic>{
            'id': 'temp-recovered-action',
            'type': 'STATUS',
            'job_id': 505,
            'payload': <String, dynamic>{'status': 'ACCEPTED'},
            'created_at': DateTime.now().toUtc().toIso8601String(),
          },
        ],
        'gps_unavailable': <String, dynamic>{},
      }),
      flush: true,
    );

    final pending = await store.pendingActions();

    expect(pending, hasLength(1));
    expect(pending.single['id'], 'temp-recovered-action');
    expect(await temp.exists(), isFalse);
    final log = File('${tempDir.path}/offline_job_recovery_events.jsonl');
    final event = jsonDecode((await log.readAsLines()).last) as Map<String, dynamic>;
    expect(event['reason'], 'RECOVERED_VALID_TEMP_STATE');
  });

  test('duplicate offline action id remains idempotent after state hardening', () async {
    await store.queueAction(
      type: 'STATUS',
      jobId: 202,
      payload: const <String, dynamic>{'status': 'STARTED'},
      actionId: 'stable-retry-id',
    );
    await store.queueAction(
      type: 'STATUS',
      jobId: 202,
      payload: const <String, dynamic>{'status': 'STARTED'},
      actionId: 'stable-retry-id',
    );

    final pending = await store.pendingActions();
    expect(pending, hasLength(1));
    expect(pending.single['id'], 'stable-retry-id');
  });

  test('concurrent writers do not lose queued actions', () async {
    await Future.wait(
      List<Future<String>>.generate(
        20,
        (index) => store.queueAction(
          type: 'STATUS',
          jobId: 600 + index,
          payload: <String, dynamic>{'status': 'ACCEPTED', 'index': index},
          actionId: 'parallel-$index',
        ),
      ),
    );

    final pending = await store.pendingActions();
    expect(pending, hasLength(20));
    expect(
      pending.map((row) => row['id']).toSet(),
      equals(<String>{for (var i = 0; i < 20; i++) 'parallel-$i'}),
    );
  });

  test('two store instances serialize writers through the shared file lock', () async {
    final secondStore = OfflineJobStore(rootDirectoryOverride: tempDir);
    final writes = <Future<String>>[];
    for (var index = 0; index < 20; index++) {
      final writer = index.isEven ? store : secondStore;
      writes.add(
        writer.queueAction(
          type: 'STATUS',
          jobId: 800 + index,
          payload: <String, dynamic>{'status': 'ACCEPTED', 'index': index},
          actionId: 'shared-lock-$index',
        ),
      );
    }

    await Future.wait(writes);

    final pending = await store.pendingActions();
    expect(pending, hasLength(20));
    expect(
      pending.map((row) => row['id']).toSet(),
      equals(<String>{for (var i = 0; i < 20; i++) 'shared-lock-$i'}),
    );
  });

  test('ack removal deletes only the confirmed action', () async {
    for (final id in <String>['ack-a', 'ack-b', 'ack-c']) {
      await store.queueAction(
        type: 'STATUS',
        jobId: 707,
        payload: <String, dynamic>{'status': id},
        actionId: id,
      );
    }

    await store.removeAction('ack-b');

    final pending = await store.pendingActions();
    final ids = pending.map((row) => row['id']).toSet();
    expect(ids, equals(<String>{'ack-a', 'ack-c'}));
  });

  test('missing media is dead-lettered without blocking later actions', () async {
    final missingPath = '${tempDir.path}/pending_media/missing-photo.jpg';
    await store.queueAction(
      type: 'PHOTO',
      jobId: 303,
      payload: const <String, dynamic>{'description': 'offline proof'},
      actionId: 'photo-missing',
      filePath: missingPath,
    );
    await store.queueAction(
      type: 'STATUS',
      jobId: 303,
      payload: const <String, dynamic>{'status': 'COMPLETED'},
      actionId: 'status-after-photo',
    );

    final pending = await store.pendingActions();
    expect(pending, hasLength(1));
    expect(pending.single['id'], 'status-after-photo');

    final deadLetters = OfflineActionDeadLetterStore(
      rootDirectoryOverride: tempDir,
    );
    final entries = await deadLetters.entries();
    expect(entries, hasLength(1));
    expect(entries.single['reason'], 'MEDIA_FILE_MISSING');
    final action = Map<String, dynamic>.from(entries.single['action'] as Map);
    expect(action['id'], 'photo-missing');

    final state = jsonDecode(
      await File('${tempDir.path}/offline_job_state_v1.json').readAsString(),
    ) as Map<String, dynamic>;
    final queue = List<Map<String, dynamic>>.from(
      (state['queue'] as List).map((row) => Map<String, dynamic>.from(row as Map)),
    );
    expect(queue.map((row) => row['id']), contains('status-after-photo'));
    expect(queue.map((row) => row['id']), isNot(contains('photo-missing')));
  });

  test('zero-byte signature is quarantined as unusable media', () async {
    final mediaDir = Directory('${tempDir.path}/pending_media');
    await mediaDir.create(recursive: true);
    final emptySignature = File('${mediaDir.path}/empty-signature.png');
    await emptySignature.writeAsBytes(const <int>[], flush: true);

    await store.queueAction(
      type: 'SIGNATURE',
      jobId: 404,
      payload: const <String, dynamic>{'customer_name': 'Test Customer'},
      actionId: 'empty-signature',
      filePath: emptySignature.path,
    );

    expect(await store.pendingActions(), isEmpty);

    final deadLetters = OfflineActionDeadLetterStore(
      rootDirectoryOverride: tempDir,
    );
    final entries = await deadLetters.entries();
    expect(entries.single['reason'], 'MEDIA_FILE_EMPTY');
  });
}
