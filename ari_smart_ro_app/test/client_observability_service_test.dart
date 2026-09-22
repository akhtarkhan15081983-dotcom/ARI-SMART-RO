import 'package:ari_smart_ro_app/services/client_observability_service.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('telemetry sanitizer redacts common secrets and caps output', () {
    final sanitized = ClientObservabilityService.sanitizeForTelemetry(
      'Bearer abc.def.ghi password=Secret123 token:super-token',
      500,
    );

    expect(sanitized, isNot(contains('abc.def.ghi')));
    expect(sanitized, isNot(contains('Secret123')));
    expect(sanitized, isNot(contains('super-token')));
    expect(sanitized, contains('[REDACTED]'));

    final capped = ClientObservabilityService.sanitizeForTelemetry(
      'abcdefghij',
      5,
    );
    expect(capped, 'abcde');
  });
}
