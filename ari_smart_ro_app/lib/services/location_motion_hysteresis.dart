import 'location_tracking_policy.dart';

/// Accuracy-aware motion-state hysteresis for the single V5 tracking loop.
///
/// It never changes scheduling from one noisy sample. Poor/invalid fixes keep the
/// last trusted state. Entering stationary is intentionally slower than leaving it
/// so a field employee who starts moving does not remain on a low-power cadence
/// longer than necessary after the next credible GPS fix arrives.
class LocationMotionHysteresis {
  LocationMotionHysteresis({LocationMotionState initial = LocationMotionState.unknown})
      : _current = initial;

  LocationMotionState _current;
  LocationMotionState? _candidate;
  int _candidateCount = 0;

  LocationMotionState get current => _current;
  Duration get interval => LocationTrackingPolicy.intervalFor(_current);

  LocationMotionState observe({
    required double? speedMps,
    required double movedMeters,
    required double? accuracyMeters,
  }) {
    if (!_accuracyTrusted(accuracyMeters)) return _current;

    final speed = speedMps != null && speedMps.isFinite && speedMps >= 0
        ? speedMps
        : null;
    final movement = movedMeters.isFinite && movedMeters >= 0 ? movedMeters : 0.0;
    final observed = LocationTrackingPolicy.classify(
      speedMps: speed,
      movedMeters: movement,
    );

    if (observed == LocationMotionState.unknown) {
      _candidate = null;
      _candidateCount = 0;
      return _current;
    }
    if (observed == _current) {
      _candidate = null;
      _candidateCount = 0;
      return _current;
    }

    // A first credible moving fix should wake an unknown/stationary tracker
    // promptly. Slowing down requires confirmation to suppress GPS jitter.
    if ((_current == LocationMotionState.unknown ||
            _current == LocationMotionState.stationary) &&
        (observed == LocationMotionState.walking ||
            observed == LocationMotionState.driving)) {
      _current = observed;
      _candidate = null;
      _candidateCount = 0;
      return _current;
    }

    if (_candidate == observed) {
      _candidateCount += 1;
    } else {
      _candidate = observed;
      _candidateCount = 1;
    }

    final confirmations = observed == LocationMotionState.stationary ? 3 : 2;
    if (_candidateCount >= confirmations) {
      _current = observed;
      _candidate = null;
      _candidateCount = 0;
    }
    return _current;
  }

  bool _accuracyTrusted(double? accuracyMeters) {
    return accuracyMeters != null &&
        accuracyMeters.isFinite &&
        accuracyMeters >= 0 &&
        accuracyMeters <= LocationTrackingPolicy.degradedAccuracyMeters;
  }
}
