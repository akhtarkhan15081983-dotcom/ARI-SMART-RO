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

    // Phase-2B must not sneak in a second scheduler. Adaptive cadence belongs to
    // the next gated phase and will replace this timer inside the same loop.
    expect(source, contains('Timer.periodic(_trackingInterval'));
    expect(RegExp(r'Timer\.periodic\(').allMatches(source).length, 1);
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
