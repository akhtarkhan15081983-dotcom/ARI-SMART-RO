import 'dart:io';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';

import '../../services/attendance_service.dart';
import '../../services/selfie_quality_service.dart';

class AttendanceScreen extends StatefulWidget {
  const AttendanceScreen({super.key});

  @override
  State<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends State<AttendanceScreen> {
  static const double _officeLatitude = 27.149028;
  static const double _officeLongitude = 78.045000;
  static const double _officeRadiusMeters = 50.0;

  final AttendanceService _attendanceService = AttendanceService();
  final ImagePicker _imagePicker = ImagePicker();

  Position? _position;
  XFile? _selfie;
  bool _isSelfieVerified = false;
  String? _selfieMessage;
  bool _isLocationVerified = false;
  double? _distanceFromOffice;
  bool _isLoadingLocation = false;
  bool _isCapturingSelfie = false;
  bool _isSubmitting = false;
  bool _isCheckedIn = false;
  bool _isCheckedOut = false;
  DateTime? _checkInTime;
  DateTime? _checkOutTime;

  @override
  void initState() {
    super.initState();
    _loadTodayAttendance();
  }

  Future<void> _loadTodayAttendance() async {
    try {
      final attendance = await _attendanceService.todayAttendance();
      if (attendance == null || !mounted) return;
      setState(() {
        _isCheckedIn = attendance.checkIn != null;
        _checkInTime = attendance.checkIn == null
            ? null
            : DateTime.parse(attendance.checkIn!);
        _isCheckedOut = attendance.checkOut != null;
        _checkOutTime = attendance.checkOut == null
            ? null
            : DateTime.parse(attendance.checkOut!);
      });
    } catch (e) {
      debugPrint('LOAD ATTENDANCE ERROR: $e');
    }
  }

  bool get _canCheckIn =>
      _isLocationVerified &&
      _position != null &&
      _selfie != null &&
      _isSelfieVerified &&
      !_isSubmitting &&
      !_isCheckedIn;

  Future<void> _verifyLocation() async {
    if (_isLoadingLocation || _isSubmitting) return;
    setState(() {
      _isLoadingLocation = true;
      _isLocationVerified = false;
      _position = null;
      _distanceFromOffice = null;
    });
    try {
      if (!await Geolocator.isLocationServiceEnabled())
        throw const _AttendanceException(
          'Location services are turned off. Enable GPS and try again.',
        );
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied)
        permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied)
        throw const _AttendanceException('Location permission was denied.');
      if (permission == LocationPermission.deniedForever)
        throw const _AttendanceException(
          'Location permission is permanently denied. Enable it in Settings.',
        );
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 25),
        ),
      );
      final distance = Geolocator.distanceBetween(
        position.latitude,
        position.longitude,
        _officeLatitude,
        _officeLongitude,
      );
      if (!mounted) return;
      if (distance > _officeRadiusMeters) {
        setState(() {
          _distanceFromOffice = distance;
          _isLocationVerified = false;
        });
        throw _AttendanceException(
          'You are ${distance.toStringAsFixed(0)}m from the office. Attendance is allowed only within 50m.',
        );
      }
      setState(() {
        _position = position;
        _distanceFromOffice = distance;
        _isLocationVerified = true;
      });
      _showSnackBar(
        'Office location verified (${distance.toStringAsFixed(0)}m away).',
        isSuccess: true,
      );
    } on _AttendanceException catch (error) {
      _showSnackBar(error.message);
    } on LocationServiceDisabledException {
      _showSnackBar(
        'Location services are turned off. Enable GPS and try again.',
      );
    } catch (_) {
      _showSnackBar(
        'Unable to get an accurate location. Please try again outdoors.',
      );
    } finally {
      if (mounted) setState(() => _isLoadingLocation = false);
    }
  }

  Future<void> _captureSelfie() async {
    if (_isCapturingSelfie || _isSubmitting) return;
    setState(() {
      _isCapturingSelfie = true;
      _selfie = null;
      _isSelfieVerified = false;
      _selfieMessage = null;
    });
    try {
      final image = await _imagePicker.pickImage(
        source: ImageSource.camera,
        preferredCameraDevice: CameraDevice.front,
        imageQuality: 85,
        maxWidth: 1440,
      );
      if (image == null || !mounted) return;
      final result = await SelfieQualityService.validate(image.path);
      if (!mounted) return;
      if (!result.isValid) {
        setState(() {
          _selfie = null;
          _isSelfieVerified = false;
          _selfieMessage = result.message;
        });
        _showSnackBar(result.message);
        return;
      }
      setState(() {
        _selfie = image;
        _isSelfieVerified = true;
        _selfieMessage = result.message;
      });
      _showSnackBar(result.message, isSuccess: true);
    } catch (_) {
      _showSnackBar(
        'Unable to verify the selfie. Check camera permission and try again in good light.',
      );
    } finally {
      if (mounted) setState(() => _isCapturingSelfie = false);
    }
  }

  Future<void> _checkIn() async {
    if (!_canCheckIn) {
      _showSnackBar(
        'Verify office GPS and pass the live selfie quality check first.',
      );
      return;
    }
    final confirm = await _confirmAction(
      title: 'Check In',
      message: 'Are you sure you want to check in?',
    );
    if (!confirm) return;
    setState(() => _isSubmitting = true);
    try {
      final result = await _attendanceService.checkIn(
        latitude: _position!.latitude,
        longitude: _position!.longitude,
        selfiePath: _selfie!.path,
      );
      if (!result.success) {
        if (!mounted) return;
        final distance = result.distanceFromOfficeMeters;
        final detail = distance == null
            ? result.message
            : '${result.message} Current distance: ${distance.toStringAsFixed(1)}m.';
        _showSnackBar(detail);
        return;
      }
      if (!mounted) return;
      setState(() {
        _isCheckedIn = true;
        _checkInTime = DateTime.now();
      });
      _showSnackBar(result.message, isSuccess: true);
      await _loadTodayAttendance();
    } catch (error) {
      _showSnackBar('Unable to complete check-in: $error');
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  Future<void> _checkOut() async {
    final confirm = await _confirmAction(
      title: 'Check Out',
      message: 'Are you sure you want to check out?',
    );
    if (!confirm || _isSubmitting || !_isCheckedIn || _isCheckedOut) return;
    setState(() => _isSubmitting = true);
    try {
      await _attendanceService.checkOut();
      if (!mounted) return;
      setState(() {
        _isCheckedOut = true;
        _checkOutTime = DateTime.now();
      });
      _showSnackBar('Checked out successfully.', isSuccess: true);
      await _loadTodayAttendance();
    } catch (_) {
      _showSnackBar('Check-out failed. Please try again.');
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  Future<bool> _confirmAction({
    required String title,
    required String message,
  }) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Yes'),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  void _showSnackBar(String message, {bool isSuccess = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(message),
          behavior: SnackBarBehavior.floating,
          backgroundColor: isSuccess
              ? Colors.green.shade700
              : Colors.red.shade700,
        ),
      );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final date = MaterialLocalizations.of(
      context,
    ).formatMediumDate(DateTime.now());
    final completed = _isCheckedOut;
    final status = completed
        ? 'Attendance completed'
        : _isCheckedIn
        ? 'You are checked in'
        : 'Mark your attendance';
    final locationDetail = _isLocationVerified && _position != null
        ? 'Office verified · ${_distanceFromOffice?.toStringAsFixed(0) ?? '0'}m away'
        : _distanceFromOffice != null
        ? 'Outside office radius · ${_distanceFromOffice!.toStringAsFixed(0)}m away'
        : 'Must be within 50m of the office';
    final selfieDetail = _isSelfieVerified
        ? 'One clear face detected · quality check passed'
        : _selfieMessage ??
              'Take a clear front-camera photo with only one face visible';

    return Scaffold(
      appBar: AppBar(title: const Text('Attendance')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(20),
          children: [
            Text(
              status,
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 6),
            Text(date, style: theme.textTheme.bodyMedium),
            const SizedBox(height: 24),
            _AttendanceSummary(
              checkedIn: _isCheckedIn,
              checkedOut: _isCheckedOut,
              checkInTime: _checkInTime,
              checkOutTime: _checkOutTime,
            ),
            const SizedBox(height: 16),
            _VerificationCard(
              icon: Icons.location_on_outlined,
              title: 'Office GPS verification',
              detail: locationDetail,
              buttonLabel: _isLocationVerified ? 'Refresh GPS' : 'Verify GPS',
              isVerified: _isLocationVerified,
              isLoading: _isLoadingLocation,
              enabled: !completed && !_isCheckedIn,
              onPressed: _verifyLocation,
            ),
            const SizedBox(height: 14),
            _VerificationCard(
              icon: Icons.camera_front_outlined,
              title: 'Live selfie quality verification',
              detail: selfieDetail,
              buttonLabel: _isSelfieVerified ? 'Retake selfie' : 'Take selfie',
              isVerified: _isSelfieVerified,
              isLoading: _isCapturingSelfie,
              enabled: !completed && !_isCheckedIn,
              onPressed: _captureSelfie,
              trailing: _selfie == null
                  ? null
                  : ClipRRect(
                      borderRadius: BorderRadius.circular(10),
                      child: Image.file(
                        File(_selfie!.path),
                        width: 64,
                        height: 64,
                        fit: BoxFit.cover,
                        errorBuilder: (_, _, _) => const SizedBox(
                          width: 64,
                          height: 64,
                          child: Icon(Icons.broken_image_outlined),
                        ),
                      ),
                    ),
            ),
            const SizedBox(height: 28),
            SizedBox(
              height: 52,
              child: FilledButton.icon(
                onPressed: _isSubmitting || completed
                    ? null
                    : _isCheckedIn
                    ? _checkOut
                    : _canCheckIn
                    ? _checkIn
                    : null,
                icon: _isSubmitting
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : Icon(
                        completed
                            ? Icons.check_circle_outline
                            : _isCheckedIn
                            ? Icons.logout
                            : Icons.login,
                      ),
                label: Text(
                  _isSubmitting
                      ? 'Please wait…'
                      : completed
                      ? 'Attendance completed'
                      : _isCheckedIn
                      ? 'Check out'
                      : 'Check in',
                ),
              ),
            ),
            if (!_isCheckedIn && !completed) ...[
              const SizedBox(height: 12),
              Text(
                'Check-in requires office GPS, the enrolled device, and a clear single-person live selfie. This quality check does not identify the employee.',
                textAlign: TextAlign.center,
                style: theme.textTheme.bodySmall,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _AttendanceSummary extends StatelessWidget {
  const _AttendanceSummary({
    required this.checkedIn,
    required this.checkedOut,
    this.checkInTime,
    this.checkOutTime,
  });
  final bool checkedIn;
  final bool checkedOut;
  final DateTime? checkInTime;
  final DateTime? checkOutTime;
  @override
  Widget build(BuildContext context) {
    final localizations = MaterialLocalizations.of(context);
    String timeFor(DateTime? value) => value == null
        ? '—'
        : localizations.formatTimeOfDay(TimeOfDay.fromDateTime(value));
    return Card(
      color: checkedOut
          ? Colors.green.withValues(alpha: 0.08)
          : checkedIn
          ? Colors.blue.withValues(alpha: 0.08)
          : null,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            Icon(
              checkedOut
                  ? Icons.task_alt
                  : checkedIn
                  ? Icons.access_time_filled_outlined
                  : Icons.pending_outlined,
              color: checkedOut
                  ? Colors.green.shade700
                  : checkedIn
                  ? Colors.blue.shade700
                  : null,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                checkedOut
                    ? 'Checked in ${timeFor(checkInTime)} · Checked out ${timeFor(checkOutTime)}'
                    : checkedIn
                    ? 'Checked in at ${timeFor(checkInTime)}'
                    : 'Not checked in yet',
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _VerificationCard extends StatelessWidget {
  const _VerificationCard({
    required this.icon,
    required this.title,
    required this.detail,
    required this.buttonLabel,
    required this.isVerified,
    required this.isLoading,
    required this.enabled,
    required this.onPressed,
    this.trailing,
  });
  final IconData icon;
  final String title;
  final String detail;
  final String buttonLabel;
  final bool isVerified;
  final bool isLoading;
  final bool enabled;
  final VoidCallback onPressed;
  final Widget? trailing;
  @override
  Widget build(BuildContext context) {
    final color = isVerified ? Colors.green.shade700 : null;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CircleAvatar(
              backgroundColor: isVerified
                  ? Colors.green.withValues(alpha: 0.12)
                  : null,
              child: Icon(isVerified ? Icons.check : icon, color: color),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(detail, maxLines: 3, overflow: TextOverflow.ellipsis),
                  const SizedBox(height: 8),
                  TextButton.icon(
                    onPressed: enabled && !isLoading ? onPressed : null,
                    icon: isLoading
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Icon(isVerified ? Icons.refresh : icon),
                    label: Text(buttonLabel),
                  ),
                ],
              ),
            ),
            if (trailing != null) ...[const SizedBox(width: 8), trailing!],
          ],
        ),
      ),
    );
  }
}

class _AttendanceException implements Exception {
  const _AttendanceException(this.message);
  final String message;
}
