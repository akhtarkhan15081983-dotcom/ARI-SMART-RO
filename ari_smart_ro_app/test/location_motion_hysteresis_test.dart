import 'package:flutter_test/flutter_test.dart';
import 'package:ari_smart_ro_app/services/location_motion_hysteresis.dart';
import 'package:ari_smart_ro_app/services/location_tracking_policy.dart';

void main() {
  group('LocationMotionHysteresis', () {
    test('credible movement wakes unknown tracker immediately', () {
      final tracker = LocationMotionHysteresis();

      expect(
        tracker.observe(speedMps: 1.5, movedMeters: 10, accuracyMeters: 15),
        LocationMotionState.walking,
      );
      expect(tracker.interval, const Duration(seconds: 10));
    });

    test('credible movement wakes stationary tracker immediately', () {
      final tracker = LocationMotionHysteresis(
        initial: LocationMotionState.stationary,
      );

      expect(
        tracker.observe(speedMps: 7, movedMeters: 25, accuracyMeters: 12),
        LocationMotionState.driving,
      );
      expect(tracker.interval, const Duration(seconds: 5));
    });

    test('requires three trusted samples before entering stationary', () {
      final tracker = LocationMotionHysteresis(
        initial: LocationMotionState.walking,
      );

      for (var i = 0; i < 2; i++) {
        expect(
          tracker.observe(speedMps: 0.1, movedMeters: 1, accuracyMeters: 18),
          LocationMotionState.walking,
        );
      }
      expect(
        tracker.observe(speedMps: 0.1, movedMeters: 1, accuracyMeters: 18),
        LocationMotionState.stationary,
      );
      expect(tracker.interval, const Duration(seconds: 45));
    });

    test('poor GPS cannot flip a trusted motion state', () {
      final tracker = LocationMotionHysteresis(
        initial: LocationMotionState.driving,
      );

      for (var i = 0; i < 4; i++) {
        expect(
          tracker.observe(speedMps: 0, movedMeters: 0, accuracyMeters: 220),
          LocationMotionState.driving,
        );
      }
    });

    test('walking to driving requires confirmation', () {
      final tracker = LocationMotionHysteresis(
        initial: LocationMotionState.walking,
      );

      expect(
        tracker.observe(speedMps: 8, movedMeters: 30, accuracyMeters: 10),
        LocationMotionState.walking,
      );
      expect(
        tracker.observe(speedMps: 8, movedMeters: 35, accuracyMeters: 10),
        LocationMotionState.driving,
      );
    });

    test('unknown/noisy observation clears pending transition', () {
      final tracker = LocationMotionHysteresis(
        initial: LocationMotionState.walking,
      );

      expect(
        tracker.observe(speedMps: 8, movedMeters: 30, accuracyMeters: 10),
        LocationMotionState.walking,
      );
      expect(
        tracker.observe(speedMps: 0.5, movedMeters: 5, accuracyMeters: 10),
        LocationMotionState.walking,
      );
      expect(
        tracker.observe(speedMps: 8, movedMeters: 30, accuracyMeters: 10),
        LocationMotionState.walking,
      );
    });
  });
}
