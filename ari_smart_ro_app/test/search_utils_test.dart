import 'package:ari_smart_ro_app/utils/search_utils.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const employee = [
    'Aamir Khan',
    'EMP-2026-000042',
    '+91 98765-43210',
    'ENGINEER',
  ];

  test('empty query matches all records', () {
    expect(matchesAllSearchTerms('', employee), isTrue);
  });

  test('matches each supported employee identifier', () {
    expect(matchesAllSearchTerms('aamir', employee), isTrue);
    expect(matchesAllSearchTerms('000042', employee), isTrue);
    expect(matchesAllSearchTerms('9876543210', employee), isTrue);
    expect(matchesAllSearchTerms('engineer', employee), isTrue);
  });

  test('ignores punctuation and spacing in IDs and phone numbers', () {
    expect(matchesAllSearchTerms('EMP2026000042', employee), isTrue);
    expect(matchesAllSearchTerms('919876543210', employee), isTrue);
  });

  test('requires every search term to match available fields', () {
    expect(matchesAllSearchTerms('aamir engineer', employee), isTrue);
    expect(matchesAllSearchTerms('aamir office', employee), isFalse);
  });

  test('does not treat punctuation-only query as a match', () {
    expect(matchesAllSearchTerms('---', employee), isFalse);
  });
}
