enum LocationMotionState { stationary, walking, driving, unknown }

class LocationTrackingPolicy {
  const LocationTrackingPolicy._();

  static const Duration drivingInterval = Duration(seconds: 5);
  static const Duration walkingInterval = Duration(seconds: 10);
  static const Duration unknownInterval = Duration(seconds: 20);
  static const Duration stationaryInterval = Duration(seconds: 45);

  static const double drivingSpeedMps = 4.5;
  static const double walkingSpeedMps = 0.8;
  static const double stationarySpeedMps = 0.35;

  static const double minimumMeaningfulMoveMeters = 4;
  static const double rejectImpossibleSpeedMps = 65;
  static const double excellentAccuracyMeters = 20;
  static const double acceptableAccuracyMeters = 60;
  static const double degradedAccuracyMeters = 150;

  static LocationMotionState classify({
    required double? speedMps,
    required double movedMeters,
  }) {
    final speed = speedMps ?? 0;
    if (speed >= drivingSpeedMps) return LocationMotionState.driving;
    if (speed >= walkingSpeedMps || movedMeters >= 8) {
      return LocationMotionState.walking;
    }
    if (speed <= stationarySpeedMps && movedMeters < minimumMeaningfulMoveMeters) {
      return LocationMotionState.stationary;
    }
    return LocationMotionState.unknown;
  }

  static Duration intervalFor(LocationMotionState state) {
    switch (state) {
      case LocationMotionState.driving:
        return drivingInterval;
      case LocationMotionState.walking:
        return walkingInterval;
      case LocationMotionState.stationary:
        return stationaryInterval;
      case LocationMotionState.unknown:
        return unknownInterval;
    }
  }

  static String qualityLabel(double accuracyMeters) {
    if (!accuracyMeters.isFinite || accuracyMeters < 0) return 'INVALID';
    if (accuracyMeters <= excellentAccuracyMeters) return 'EXCELLENT';
    if (accuracyMeters <= acceptableAccuracyMeters) return 'GOOD';
    if (accuracyMeters <= degradedAccuracyMeters) return 'DEGRADED';
    return 'POOR';
  }

  static bool isPlausibleTransition({
    required double movedMeters,
    required Duration elapsed,
  }) {
    if (movedMeters < 0 || elapsed <= Duration.zero) return false;
    final seconds = elapsed.inMilliseconds / 1000.0;
    if (seconds <= 0) return false;
    return movedMeters / seconds <= rejectImpossibleSpeedMps;
  }
}
