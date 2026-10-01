import 'package:geolocator/geolocator.dart';

/// Device-side integrity signal used as one layer of attendance anti-fraud.
///
/// This is intentionally advisory rather than a substitute for server-side
/// geofence checks or future platform attestation. If the platform cannot
/// provide the signal, attendance keeps working and the server still applies
/// its existing location/device/selfie controls.
class AttendanceIntegrityService {
  const AttendanceIntegrityService._();

  static Future<bool> isCurrentLocationMocked() async {
    try {
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 8),
        ),
      );
      return position.isMocked;
    } catch (_) {
      return false;
    }
  }
}
