import 'package:flutter_test/flutter_test.dart';
import 'package:ari_smart_ro_app/services/location_tracking_policy.dart';

void main() {
  group('LocationTrackingPolicy', () {
    test('uses faster cadence for driving than walking and stationary states', () {
      expect(
        LocationTrackingPolicy.intervalFor(LocationMotionState.driving),
        const Duration(seconds: 5),
      );
      expect(
        LocationTrackingPolicy.intervalFor(LocationMotionState.walking),
        const Duration(seconds: 10),
      );
      expect(
        LocationTrackingPolicy.intervalFor(LocationMotionState.unknown),
        const Duration(seconds: 20),
      );
      expect(
        LocationTrackingPolicy.intervalFor(LocationMotionState.stationary),
        const Duration(seconds: 45),
      );
    });

    test('classifies motion conservatively', () {
      expect(
        LocationTrackingPolicy.classify(speedMps: 7, movedMeters: 20),
        LocationMotionState.driving,
      );
      expect(
        LocationTrackingPolicy.classify(speedMps: 1.4, movedMeters: 10),
        LocationMotionState.walking,
      );
      expect(
        LocationTrackingPolicy.classify(speedMps: 0.1, movedMeters: 1),
        LocationMotionState.stationary,
      );
    });

    test('labels accuracy quality for fleet telemetry', () {
      expect(LocationTrackingPolicy.qualityLabel(8), 'EXCELLENT');
      expect(LocationTrackingPolicy.qualityLabel(45), 'GOOD');
      expect(LocationTrackingPolicy.qualityLabel(120), 'DEGRADED');
      expect(LocationTrackingPolicy.qualityLabel(220), 'POOR');
    });

    test('rejects physically implausible jumps', () {
      expect(
        LocationTrackingPolicy.isPlausibleTransition(
          movedMeters: 100,
          elapsed: const Duration(seconds: 10),
        ),
        isTrue,
      );
      expect(
        LocationTrackingPolicy.isPlausibleTransition(
          movedMeters: 1000,
          elapsed: const Duration(seconds: 5),
        ),
        isFalse,
      );
    });
  });
}
