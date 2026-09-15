String normalizeSearchValue(String value) {
  return value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), '');
}

bool matchesAllSearchTerms(String query, Iterable<String> values) {
  final terms = query
      .trim()
      .toLowerCase()
      .split(RegExp(r'\s+'))
      .where((term) => term.isNotEmpty);
  final candidates = values
      .map(
        (value) =>
            (raw: value.toLowerCase(), normalized: normalizeSearchValue(value)),
      )
      .toList(growable: false);

  return terms.every((term) {
    final normalizedTerm = normalizeSearchValue(term);
    if (normalizedTerm.isEmpty) return false;
    return candidates.any(
      (candidate) =>
          candidate.raw.contains(term) ||
          candidate.normalized.contains(normalizedTerm),
    );
  });
}
