import 'dart:convert';

import 'package:ari_smart_ro_app/utils/jwt_utils.dart';
import 'package:flutter_test/flutter_test.dart';

String _tokenWithExpiry(int expiry) {
  final header = base64Url
      .encode(utf8.encode('{"alg":"none"}'))
      .replaceAll('=', '');
  final payload = base64Url
      .encode(utf8.encode('{"exp":$expiry}'))
      .replaceAll('=', '');
  return '$header.$payload.signature';
}

void main() {
  final now = DateTime.fromMillisecondsSinceEpoch(2000000000 * 1000);

  test('accepts a token safely beyond the refresh window', () {
    expect(isJwtUsable(_tokenWithExpiry(2000000300), now: now), isTrue);
  });

  test('refreshes a token before it expires', () {
    expect(isJwtUsable(_tokenWithExpiry(2000000060), now: now), isFalse);
  });

  test('rejects expired and malformed tokens', () {
    expect(isJwtUsable(_tokenWithExpiry(1999999999), now: now), isFalse);
    expect(isJwtUsable('not-a-jwt', now: now), isFalse);
    expect(isJwtUsable(null, now: now), isFalse);
  });
}
