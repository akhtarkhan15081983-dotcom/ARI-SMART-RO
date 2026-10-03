import 'location_tracking_policy.dart';

/// Builds the V5 mobile telemetry envelope without changing transport behavior.
///
/// This helper deliberately contains no plugin, network, storage, or device-ID
/// dependencies so its safety rules stay deterministic and unit-testable.
class LocationPointEnvelope {
  const LocationPointEnvelope._();

  static Map<String, dynamic>? build({
    required double latitude,
    required double longitude,
    required double accuracyMeters,
    required DateTime capturedAt,
    required String source,
    required double speedMps,
    required double headingDegrees,
    required double altitudeMeters,
    required int clientSequence,
    required String clientPointId,
    required String clientPlatform,
  }) {
    if (!_coordinateIsValid(latitude, -90, 90) ||
        !_coordinateIsValid(longitude, -180, 180) ||
        clientSequence < 0 ||
        clientPointId.isEmpty) {
      return null;
    }

    final platform = clientPlatform.trim().toLowerCase();
    if (platform != 'android' && platform != 'ios') return null;

    final accuracy = _finiteInRange(accuracyMeters, 0, 10000);
    final speed = _finiteInRange(speedMps, 0, 200);
    final altitude = _finiteInRange(altitudeMeters, -1000, 20000);

    // A geolocator heading describes course over ground. Do not promote it to
    // authoritative movement direction while speed is unavailable/stationary.
    // The later quality engine may add richer heading confidence/filtering.
    double? heading;
    if (speed != null && speed > LocationTrackingPolicy.stationarySpeedMps) {
      heading = _finiteInRange(headingDegrees, 0, 360);
      if (heading == 360) heading = 0;
    }

    final motionState = speed == null
        ? LocationMotionState.unknown
        : LocationTrackingPolicy.classify(
            speedMps: speed,
            movedMeters: 0,
          );

    final point = <String, dynamic>{
      'live_latitude': latitude,
      'live_longitude': longitude,
      'captured_at': capturedAt.toUtc().toIso8601String(),
      'source': source.trim(),
      'motion_state': motionState.name.toUpperCase(),
      'client_point_id': clientPointId,
      'client_sequence': clientSequence,
      'client_platform': platform,
    };

    if (accuracy != null) point['accuracy'] = accuracy;
    if (speed != null) point['speed_mps'] = speed;
    if (heading != null) point['heading'] = heading;
    if (altitude != null) point['altitude'] = altitude;

    return point;
  }

  static bool _coordinateIsValid(double value, double min, double max) {
    return value.isFinite && value >= min && value <= max;
  }

  static double? _finiteInRange(double value, double min, double max) {
    if (!value.isFinite || value < min || value > max) return null;
    return value;
  }
}
