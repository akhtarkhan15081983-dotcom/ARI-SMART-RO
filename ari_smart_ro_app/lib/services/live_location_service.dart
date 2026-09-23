import 'dart:async';
import 'dart:convert';

import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;

import 'api_service.dart';

class LiveLocationService {
  static const Duration _trackingInterval = Duration(seconds: 30);
  static Timer? _timer;
  static bool _running = false;
  static bool _sending = false;

  void startTracking() {
    if (_running) return;

    _running = true;
    unawaited(sendCurrentLocation());

    _timer?.cancel();
    _timer = Timer.periodic(_trackingInterval, (_) {
      unawaited(sendCurrentLocation());
    });
  }

  void stopTracking() {
    _timer?.cancel();
    _timer = null;
    _running = false;
  }

  Future<void> sendCurrentLocation() async {
    if (_sending) return;
    _sending = true;

    try {
      final position = await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      ).timeout(const Duration(seconds: 15));

      final response = await http
          .post(
            Uri.parse('${ApiService.baseUrl}/employees/live-location/'),
            headers: await ApiService.authHeaders(),
            body: jsonEncode({
              'live_latitude': position.latitude,
              'live_longitude': position.longitude,
            }),
          )
          .timeout(const Duration(seconds: 15));

      if (response.statusCode == 401) {
        stopTracking();
      }
    } catch (_) {
      // Tracking is best-effort. The next scheduled update will retry.
    } finally {
      _sending = false;
    }
  }
}
