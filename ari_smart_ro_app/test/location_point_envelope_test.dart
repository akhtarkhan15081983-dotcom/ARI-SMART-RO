import 'package:flutter_test/flutter_test.dart';
import 'package:ari_smart_ro_app/services/location_point_envelope.dart';

void main() {
  group('LocationPointEnvelope', () {
    test('builds sanitized V5 telemetry without PII', () {
      final point = LocationPointEnvelope.build(
        latitude: 27.5969,
        longitude: 78.0529,
        accuracyMeters: 12,
        capturedAt: DateTime.utc(2026, 10, 4, 0, 0, 0),
        source: 'FRESH_HIGH_ACCURACY',
        speedMps: 5.5,
        headingDegrees: 87,
        altitudeMeters: 182,
        clientSequence: 42,
        clientPointId: 'pt-42',
        clientPlatform: 'android',
      );

      expect(point, isNotNull);
      expect(point!['live_latitude'], 27.5969);
      expect(point['live_longitude'], 78.0529);
      expect(point['accuracy'], 12);
      expect(point['speed_mps'], 5.5);
      expect(point['heading'], 87);
      expect(point['altitude'], 182);
      expect(point['motion_state'], 'DRIVING');
      expect(point['client_point_id'], 'pt-42');
      expect(point['client_sequence'], 42);
      expect(point['client_platform'], 'android');
      expect(point.containsKey('device_id'), isFalse);
      expect(point.containsKey('user_id'), isFalse);
    });

    test('drops invalid optional numeric telemetry instead of NaN/Infinity', () {
      final point = LocationPointEnvelope.build(
        latitude: 27.5969,
        longitude: 78.0529,
        accuracyMeters: double.nan,
        capturedAt: DateTime.utc(2026, 10, 4, 0, 0, 0),
        source: 'FRESH_BALANCED',
        speedMps: -1,
        headingDegrees: double.infinity,
        altitudeMeters: double.nan,
        clientSequence: 1,
        clientPointId: 'pt-1',
        clientPlatform: 'android',
      );

      expect(point, isNotNull);
      expect(point!.containsKey('accuracy'), isFalse);
      expect(point.containsKey('speed_mps'), isFalse);
      expect(point.containsKey('heading'), isFalse);
      expect(point.containsKey('altitude'), isFalse);
      expect(point['motion_state'], 'UNKNOWN');
    });

    test('suppresses heading while stationary', () {
      final point = LocationPointEnvelope.build(
        latitude: 27.5969,
        longitude: 78.0529,
        accuracyMeters: 8,
        capturedAt: DateTime.utc(2026, 10, 4, 0, 0, 0),
        source: 'FRESH_HIGH_ACCURACY',
        speedMps: 0.1,
        headingDegrees: 270,
        altitudeMeters: 180,
        clientSequence: 2,
        clientPointId: 'pt-2',
        clientPlatform: 'android',
      );

      expect(point, isNotNull);
      expect(point!['motion_state'], 'STATIONARY');
      expect(point.containsKey('heading'), isFalse);
    });

    test('rejects invalid required identity or coordinates', () {
      expect(
        LocationPointEnvelope.build(
          latitude: 95,
          longitude: 78,
          accuracyMeters: 10,
          capturedAt: DateTime.utc(2026, 10, 4),
          source: 'FRESH_HIGH_ACCURACY',
          speedMps: 1,
          headingDegrees: 90,
          altitudeMeters: 100,
          clientSequence: 1,
          clientPointId: 'pt-1',
          clientPlatform: 'android',
        ),
        isNull,
      );

      expect(
        LocationPointEnvelope.build(
          latitude: 27,
          longitude: 78,
          accuracyMeters: 10,
          capturedAt: DateTime.utc(2026, 10, 4),
          source: 'FRESH_HIGH_ACCURACY',
          speedMps: 1,
          headingDegrees: 90,
          altitudeMeters: 100,
          clientSequence: -1,
          clientPointId: '',
          clientPlatform: 'android',
        ),
        isNull,
      );
    });
  });
}
