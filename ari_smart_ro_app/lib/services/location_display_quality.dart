import 'dart:math' as math;

import 'location_tracking_policy.dart';

enum LocationDisplayDecisionKind {
  accepted,
  jitterSuppressed,
  poorAccuracy,
  stale,
  impossibleJump,
  invalid,
}

class LocationDisplaySample {
  const LocationDisplaySample({
    required this.latitude,
    required this.longitude,
    required this.accuracyMeters,
    required this.capturedAt,
    this.speedMps,
    this.headingDegrees,
  });

  final double latitude;
  final double longitude;
  final double accuracyMeters;
  final DateTime capturedAt;
  final double? speedMps;
  final double? headingDegrees;
}

class LocationDisplayDecision {
  const LocationDisplayDecision({
    required this.kind,
    required this.raw,
    required this.displayLatitude,
    required this.displayLongitude,
    required this.headingDegrees,
    required this.hasTrustedDisplay,
  });

  final LocationDisplayDecisionKind kind;
  final LocationDisplaySample raw;
  final double displayLatitude;
  final double displayLongitude;
  final double? headingDegrees;
  final bool hasTrustedDisplay;

  bool get acceptedForDisplay =>
      kind == LocationDisplayDecisionKind.accepted ||
      kind == LocationDisplayDecisionKind.jitterSuppressed;
}

class LocationDisplayFilter {
  LocationDisplayFilter({
    this.maxSampleAge = const Duration(minutes: 3),
    this.futureClockSkew = const Duration(seconds: 30),
  });

  final Duration maxSampleAge;
  final Duration futureClockSkew;

  LocationDisplaySample? _trustedSample;
  double? _displayLatitude;
  double? _displayLongitude;
  double? _smoothedHeading;

  LocationDisplayDecision evaluate(
    LocationDisplaySample sample, {
    DateTime? now,
  }) {
    final referenceNow = (now ?? DateTime.now()).toUtc();
    final raw = LocationDisplaySample(
      latitude: sample.latitude,
      longitude: sample.longitude,
      accuracyMeters: sample.accuracyMeters,
      capturedAt: sample.capturedAt.toUtc(),
      speedMps: sample.speedMps,
      headingDegrees: sample.headingDegrees,
    );

    if (!_isValid(raw)) {
      return _rejected(LocationDisplayDecisionKind.invalid, raw);
    }

    final age = referenceNow.difference(raw.capturedAt);
    if (age > maxSampleAge || age < -futureClockSkew) {
      return _rejected(LocationDisplayDecisionKind.stale, raw);
    }

    if (raw.accuracyMeters > LocationTrackingPolicy.degradedAccuracyMeters) {
      return _rejected(LocationDisplayDecisionKind.poorAccuracy, raw);
    }

    final previous = _trustedSample;
    if (previous == null) {
      _trustedSample = raw;
      _displayLatitude = raw.latitude;
      _displayLongitude = raw.longitude;
      _smoothedHeading = _normalizedHeading(raw.headingDegrees);
      return _decision(LocationDisplayDecisionKind.accepted, raw);
    }

    final elapsed = raw.capturedAt.difference(previous.capturedAt);
    if (elapsed <= Duration.zero) {
      return _rejected(LocationDisplayDecisionKind.invalid, raw);
    }

    final movedMeters = _distanceMeters(
      previous.latitude,
      previous.longitude,
      raw.latitude,
      raw.longitude,
    );
    if (!LocationTrackingPolicy.isPlausibleTransition(
      movedMeters: movedMeters,
      elapsed: elapsed,
    )) {
      return _rejected(LocationDisplayDecisionKind.impossibleJump, raw);
    }

    final speed = _usableSpeed(raw.speedMps);
    final jitterThreshold = math.max(
      LocationTrackingPolicy.minimumMeaningfulMoveMeters,
      math.min(raw.accuracyMeters, LocationTrackingPolicy.acceptableAccuracyMeters) *
          0.35,
    );
    final appearsStationary = speed == null ||
        speed < LocationTrackingPolicy.walkingSpeedMps;
    if (appearsStationary && movedMeters < jitterThreshold) {
      _smoothedHeading = _smoothHeading(
        current: _smoothedHeading,
        target: raw.headingDegrees,
        factor: 0.25,
      );
      return _decision(LocationDisplayDecisionKind.jitterSuppressed, raw);
    }

    final factor = _positionBlendFactor(raw, speed: speed);
    _displayLatitude = _blend(_displayLatitude!, raw.latitude, factor);
    _displayLongitude = _blend(_displayLongitude!, raw.longitude, factor);

    final derivedHeading = movedMeters >=
            LocationTrackingPolicy.minimumMeaningfulMoveMeters
        ? _bearingDegrees(
            previous.latitude,
            previous.longitude,
            raw.latitude,
            raw.longitude,
          )
        : null;
    _smoothedHeading = _smoothHeading(
      current: _smoothedHeading,
      target: raw.headingDegrees ?? derivedHeading,
      factor: speed != null && speed >= LocationTrackingPolicy.drivingSpeedMps
          ? 0.55
          : 0.35,
    );
    _trustedSample = raw;
    return _decision(LocationDisplayDecisionKind.accepted, raw);
  }

  LocationDisplayDecision _decision(
    LocationDisplayDecisionKind kind,
    LocationDisplaySample raw,
  ) {
    return LocationDisplayDecision(
      kind: kind,
      raw: raw,
      displayLatitude: _displayLatitude ?? raw.latitude,
      displayLongitude: _displayLongitude ?? raw.longitude,
      headingDegrees: _smoothedHeading,
      hasTrustedDisplay: _displayLatitude != null && _displayLongitude != null,
    );
  }

  LocationDisplayDecision _rejected(
    LocationDisplayDecisionKind kind,
    LocationDisplaySample raw,
  ) {
    return LocationDisplayDecision(
      kind: kind,
      raw: raw,
      displayLatitude: _displayLatitude ?? raw.latitude,
      displayLongitude: _displayLongitude ?? raw.longitude,
      headingDegrees: _smoothedHeading,
      hasTrustedDisplay: _displayLatitude != null && _displayLongitude != null,
    );
  }

  bool _isValid(LocationDisplaySample sample) {
    if (!sample.latitude.isFinite ||
        !sample.longitude.isFinite ||
        !sample.accuracyMeters.isFinite) {
      return false;
    }
    if (sample.latitude.abs() > 90 ||
        sample.longitude.abs() > 180 ||
        sample.accuracyMeters < 0) {
      return false;
    }
    final speed = sample.speedMps;
    if (speed != null && (!speed.isFinite || speed < 0)) return false;
    final heading = sample.headingDegrees;
    if (heading != null && !heading.isFinite) return false;
    return true;
  }

  double? _usableSpeed(double? raw) {
    if (raw == null || !raw.isFinite || raw < 0) return null;
    if (raw > LocationTrackingPolicy.rejectImpossibleSpeedMps) return null;
    return raw;
  }

  double _positionBlendFactor(
    LocationDisplaySample sample, {
    required double? speed,
  }) {
    if (speed != null && speed >= LocationTrackingPolicy.drivingSpeedMps) {
      return 0.88;
    }
    if (sample.accuracyMeters <= LocationTrackingPolicy.excellentAccuracyMeters) {
      return 0.78;
    }
    if (sample.accuracyMeters <= LocationTrackingPolicy.acceptableAccuracyMeters) {
      return 0.58;
    }
    return 0.38;
  }

  static double _blend(double current, double target, double factor) =>
      current + (target - current) * factor;

  static double? _normalizedHeading(double? heading) {
    if (heading == null || !heading.isFinite) return null;
    final normalized = heading % 360;
    return normalized < 0 ? normalized + 360 : normalized;
  }

  static double? _smoothHeading({
    required double? current,
    required double? target,
    required double factor,
  }) {
    final normalizedTarget = _normalizedHeading(target);
    if (normalizedTarget == null) return current;
    if (current == null) return normalizedTarget;

    final normalizedCurrent = _normalizedHeading(current)!;
    final delta =
        ((normalizedTarget - normalizedCurrent + 540) % 360) - 180;
    return _normalizedHeading(normalizedCurrent + delta * factor);
  }

  static double _distanceMeters(
    double lat1,
    double lon1,
    double lat2,
    double lon2,
  ) {
    const earthRadiusMeters = 6371000.0;
    final p1 = lat1 * math.pi / 180;
    final p2 = lat2 * math.pi / 180;
    final deltaLat = (lat2 - lat1) * math.pi / 180;
    final deltaLon = (lon2 - lon1) * math.pi / 180;
    final a = math.sin(deltaLat / 2) * math.sin(deltaLat / 2) +
        math.cos(p1) *
            math.cos(p2) *
            math.sin(deltaLon / 2) *
            math.sin(deltaLon / 2);
    final c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a));
    return earthRadiusMeters * c;
  }

  static double _bearingDegrees(
    double lat1,
    double lon1,
    double lat2,
    double lon2,
  ) {
    final p1 = lat1 * math.pi / 180;
    final p2 = lat2 * math.pi / 180;
    final deltaLon = (lon2 - lon1) * math.pi / 180;
    final y = math.sin(deltaLon) * math.cos(p2);
    final x = math.cos(p1) * math.sin(p2) -
        math.sin(p1) * math.cos(p2) * math.cos(deltaLon);
    return ((math.atan2(y, x) * 180 / math.pi) + 360) % 360;
  }
}
