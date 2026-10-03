import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('V5 mobile telemetry enriches the existing single tracking loop', () {
    final source = File('lib/services/live_location_service.dart').readAsStringSync();

    expect(source, contains("import 'location_point_envelope.dart';"));
    expect(source, contains("import 'location_point_identity.dart';"));
    expect(source, contains('LocationQueueStore.nextClientSequence()'));
    expect(source, contains('LocationPointIdentity.pointId('));
    expect(source, contains('LocationPointEnvelope.build('));
    expect(source, contains('speedMps: position.speed'));
    expect(source, contains('headingDegrees: position.heading'));
    expect(source, contains('altitudeMeters: position.altitude'));

    // Phase-2B telemetry must remain inside the same authoritative scheduler.
    // Phase-3 may adapt cadence, but must not introduce a second recurring loop.
    expect(source, contains('timer = Timer(nextInterval'));
    expect(source, contains('unawaited(runAndSchedule())'));
    expect(source, isNot(contains('Timer.periodic(')));
    expect(RegExp(r'\bTimer\(').allMatches(source).length, 1);
  });

  test('offline queue owns monotonic client sequence allocation', () {
    final source = File('lib/services/location_queue_store.dart').readAsStringSync();

    expect(source, contains('static Future<int> nextClientSequence()'));
    expect(source, contains("_sequenceFileName = '.location_sequence_v5'"));
    expect(source, contains('LocationPointIdentity.nextSequence('));
    expect(source, contains('_withQueueLock'));
    expect(source, contains('return nowMicros;'));
  });
}
