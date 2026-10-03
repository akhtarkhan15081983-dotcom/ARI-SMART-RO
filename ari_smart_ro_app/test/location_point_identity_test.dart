import 'package:flutter_test/flutter_test.dart';
import 'package:ari_smart_ro_app/services/location_point_identity.dart';

void main() {
  group('LocationPointIdentity', () {
    test('advances above persisted value and wall-clock seed', () {
      expect(
        LocationPointIdentity.nextSequence(persisted: 100, nowMicros: 50),
        101,
      );
      expect(
        LocationPointIdentity.nextSequence(persisted: 100, nowMicros: 500),
        500,
      );
    });

    test('recovers safely from missing or corrupt negative persisted state', () {
      expect(
        LocationPointIdentity.nextSequence(persisted: null, nowMicros: 1234),
        1234,
      );
      expect(
        LocationPointIdentity.nextSequence(persisted: -9, nowMicros: 1234),
        1234,
      );
    });

    test('creates backend-safe stable point id format', () {
      final id = LocationPointIdentity.pointId(
        platform: 'android',
        sequence: 42,
        capturedAt: DateTime.utc(2026, 10, 4, 0, 0, 0),
      );
      expect(id, startsWith('android:'));
      expect(id, endsWith(':42'));
      expect(RegExp(r'^[A-Za-z0-9_.:-]+$').hasMatch(id), isTrue);
    });
  });
}
