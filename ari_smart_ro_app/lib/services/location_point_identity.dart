import 'dart:math' as math;

/// Pure helpers for durable V5 client point sequencing.
class LocationPointIdentity {
  const LocationPointIdentity._();

  static int nextSequence({required int? persisted, required int nowMicros}) {
    final safeNow = math.max(0, nowMicros);
    if (persisted == null || persisted < 0) return safeNow;
    return math.max(persisted + 1, safeNow);
  }

  static String pointId({
    required String platform,
    required int sequence,
    required DateTime capturedAt,
  }) {
    final normalizedPlatform = platform.trim().toLowerCase();
    final safePlatform = normalizedPlatform == 'ios' ? 'ios' : 'android';
    return '$safePlatform:${capturedAt.toUtc().microsecondsSinceEpoch}:$sequence';
  }
}
