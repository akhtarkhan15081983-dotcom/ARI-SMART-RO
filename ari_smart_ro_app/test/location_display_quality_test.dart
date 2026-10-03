import 'package:flutter_test/flutter_test.dart';
import 'package:ari_smart_ro_app/services/location_display_quality.dart';

LocationDisplaySample sample({
  required double latitude,
  required double longitude,
  required DateTime capturedAt,
  double accuracy = 12,
  double? speed,
  double? heading,
}) {
  return LocationDisplaySample(
    latitude: latitude,
    longitude: longitude,
    accuracyMeters: accuracy,
    capturedAt: capturedAt,
    speedMps: speed,
    headingDegrees: heading,
  );
}

void main() {
  final base = DateTime.utc(2026, 10, 4, 0, 0);

  test('first fresh accurate sample becomes trusted display position', () {
    final filter = LocationDisplayFilter();
    final decision = filter.evaluate(
      sample(
        latitude: 28.6139,
        longitude: 77.2090,
        capturedAt: base,
        heading: 90,
      ),
      now: base,
    );

    expect(decision.kind, LocationDisplayDecisionKind.accepted);
    expect(decision.hasTrustedDisplay, isTrue);
    expect(decision.displayLatitude, closeTo(28.6139, 1e-9));
    expect(decision.displayLongitude, closeTo(77.2090, 1e-9));
    expect(decision.headingDegrees, closeTo(90, 1e-9));
  });

  test('poor accuracy cannot move an existing trusted marker', () {
    final filter = LocationDisplayFilter();
    final first = filter.evaluate(
      sample(
        latitude: 28.6139,
        longitude: 77.2090,
        capturedAt: base,
      ),
      now: base,
    );
    final rejected = filter.evaluate(
      sample(
        latitude: 28.6200,
        longitude: 77.2200,
        capturedAt: base.add(const Duration(seconds: 20)),
        accuracy: 220,
      ),
      now: base.add(const Duration(seconds: 20)),
    );

    expect(rejected.kind, LocationDisplayDecisionKind.poorAccuracy);
    expect(rejected.displayLatitude, first.displayLatitude);
    expect(rejected.displayLongitude, first.displayLongitude);
  });

  test('impossible jump is rejected without poisoning trusted position', () {
    final filter = LocationDisplayFilter();
    final first = filter.evaluate(
      sample(
        latitude: 28.6139,
        longitude: 77.2090,
        capturedAt: base,
      ),
      now: base,
    );
    final rejected = filter.evaluate(
      sample(
        latitude: 28.7041,
        longitude: 77.1025,
        capturedAt: base.add(const Duration(seconds: 5)),
        accuracy: 10,
        speed: 3,
      ),
      now: base.add(const Duration(seconds: 5)),
    );

    expect(rejected.kind, LocationDisplayDecisionKind.impossibleJump);
    expect(rejected.displayLatitude, first.displayLatitude);
    expect(rejected.displayLongitude, first.displayLongitude);
  });

  test('small stationary jitter is suppressed but accumulated move can progress', () {
    final filter = LocationDisplayFilter();
    final first = filter.evaluate(
      sample(
        latitude: 28.613900,
        longitude: 77.209000,
        capturedAt: base,
        accuracy: 12,
        speed: 0.1,
      ),
      now: base,
    );
    final jitter = filter.evaluate(
      sample(
        latitude: 28.613912,
        longitude: 77.209010,
        capturedAt: base.add(const Duration(seconds: 20)),
        accuracy: 12,
        speed: 0.1,
      ),
      now: base.add(const Duration(seconds: 20)),
    );
    final moved = filter.evaluate(
      sample(
        latitude: 28.614020,
        longitude: 77.209020,
        capturedAt: base.add(const Duration(seconds: 40)),
        accuracy: 12,
        speed: 1.2,
      ),
      now: base.add(const Duration(seconds: 40)),
    );

    expect(jitter.kind, LocationDisplayDecisionKind.jitterSuppressed);
    expect(jitter.displayLatitude, first.displayLatitude);
    expect(moved.kind, LocationDisplayDecisionKind.accepted);
    expect(moved.displayLatitude, greaterThan(first.displayLatitude));
  });

  test('stale sample does not replace an existing trusted display', () {
    final filter = LocationDisplayFilter();
    final first = filter.evaluate(
      sample(
        latitude: 28.6139,
        longitude: 77.2090,
        capturedAt: base,
      ),
      now: base,
    );
    final stale = filter.evaluate(
      sample(
        latitude: 28.6200,
        longitude: 77.2200,
        capturedAt: base.add(const Duration(seconds: 10)),
      ),
      now: base.add(const Duration(minutes: 4)),
    );

    expect(stale.kind, LocationDisplayDecisionKind.stale);
    expect(stale.displayLatitude, first.displayLatitude);
    expect(stale.displayLongitude, first.displayLongitude);
  });

  test('heading smoothing crosses north on shortest circular path', () {
    final filter = LocationDisplayFilter();
    filter.evaluate(
      sample(
        latitude: 28.6139,
        longitude: 77.2090,
        capturedAt: base,
        heading: 359,
      ),
      now: base,
    );
    final next = filter.evaluate(
      sample(
        latitude: 28.6141,
        longitude: 77.2090,
        capturedAt: base.add(const Duration(seconds: 20)),
        speed: 1.5,
        heading: 1,
      ),
      now: base.add(const Duration(seconds: 20)),
    );

    expect(next.kind, LocationDisplayDecisionKind.accepted);
    expect(next.headingDegrees, anyOf(lessThan(5), greaterThan(355)));
  });
}
