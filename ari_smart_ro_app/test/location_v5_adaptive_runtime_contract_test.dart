import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('V5 adaptive runtime keeps exactly one self-rescheduling capture loop', () {
    final source = File('lib/services/live_location_service.dart').readAsStringSync();

    expect(source, contains("import 'location_motion_hysteresis.dart';"));
    expect(source, contains("import 'location_tracking_policy.dart';"));
    expect(source, contains('final motion = LocationMotionHysteresis();'));
    expect(source, contains('updateAdaptiveMotion(point);'));
    expect(source, contains('LocationTrackingPolicy.isPlausibleTransition('));
    expect(source, contains('LocationTrackingPolicy.rejectImpossibleSpeedMps'));
    expect(source, contains('LocationTrackingPolicy.unknownInterval'));
    expect(source, contains('timer = Timer(nextInterval'));
    expect(source, contains('unawaited(runAndSchedule())'));
    expect(source, isNot(contains('Timer.periodic(')));
    expect(source, isNot(contains('_trackingInterval')));
    expect(RegExp(r'\bTimer\(').allMatches(source).length, 1);
  });

  test('poor or impossible motion evidence cannot directly poison cadence state', () {
    final source = File('lib/services/live_location_service.dart').readAsStringSync();

    expect(
      source,
      contains('accuracy > LocationTrackingPolicy.degradedAccuracyMeters'),
    );
    expect(source, contains("point['motion_state'] = motion.current.name.toUpperCase();"));
    expect(
      source,
      contains('speed > LocationTrackingPolicy.rejectImpossibleSpeedMps'),
    );
    expect(source, contains('nextInterval = LocationTrackingPolicy.unknownInterval;'));
  });

  test('offline retention still covers more than a workday at fastest cadence', () {
    final queue = File('lib/services/location_queue_store.dart').readAsStringSync();

    expect(queue, contains('maxRetainedPoints = 24000'));
    expect(queue, contains('defaultBatchSize = 200'));
    expect(queue, contains('_withQueueLock'));
    expect(queue, contains('_replaceAtomically'));
  });

  test('stop path cancels the only future capture before service shutdown', () {
    final source = File('lib/services/live_location_service.dart').readAsStringSync();

    expect(source, contains("service.on('stopService').listen"));
    expect(source, contains('stopping = true;'));
    expect(source, contains('timer?.cancel();'));
    expect(source, contains('await service.stopSelf();'));
  });
}
