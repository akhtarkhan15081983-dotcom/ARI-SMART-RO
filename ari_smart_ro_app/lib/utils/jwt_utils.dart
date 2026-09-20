import 'dart:convert';

bool isJwtUsable(
  String? token, {
  DateTime? now,
  Duration refreshBefore = const Duration(minutes: 2),
}) {
  if (token == null || token.isEmpty) return false;
  try {
    final segments = token.split('.');
    if (segments.length != 3) return false;
    final payload =
        jsonDecode(
              utf8.decode(base64Url.decode(base64Url.normalize(segments[1]))),
            )
            as Map<String, dynamic>;
    final expiry = payload['exp'];
    if (expiry is! int) return false;
    final currentTime = now ?? DateTime.now();
    final refreshAt =
        currentTime.add(refreshBefore).millisecondsSinceEpoch ~/ 1000;
    return expiry > refreshAt;
  } catch (_) {
    return false;
  }
}
