import 'dart:io';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';

import '../../services/selfie_quality_service.dart';

class AttendanceSecurityTestScreen extends StatefulWidget {
  const AttendanceSecurityTestScreen({super.key});

  @override
  State<AttendanceSecurityTestScreen> createState() =>
      _AttendanceSecurityTestScreenState();
}

class _AttendanceSecurityTestScreenState
    extends State<AttendanceSecurityTestScreen> {
  static const double _officeLatitude = 27.149028;
  static const double _officeLongitude = 78.045000;
  static const double _radiusMeters = 50;

  final _picker = ImagePicker();
  bool _gpsBusy = false;
  bool _selfieBusy = false;
  bool? _gpsPassed;
  bool? _selfiePassed;
  double? _distance;
  String _gpsMessage = 'Not tested';
  String _selfieMessage = 'Not tested';
  XFile? _selfie;

  Future<void> _testGps() async {
    if (_gpsBusy) return;
    setState(() {
      _gpsBusy = true;
      _gpsPassed = null;
      _gpsMessage = 'Checking current GPS…';
    });
    try {
      if (!await Geolocator.isLocationServiceEnabled())
        throw Exception('Turn on GPS first.');
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied)
        permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever)
        throw Exception('Location permission is required.');
      final p = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 25),
        ),
      );
      final distance = Geolocator.distanceBetween(
        p.latitude,
        p.longitude,
        _officeLatitude,
        _officeLongitude,
      );
      if (!mounted) return;
      setState(() {
        _distance = distance;
        _gpsPassed = distance <= _radiusMeters;
        _gpsMessage = distance <= _radiusMeters
            ? 'PASS — ${distance.toStringAsFixed(0)}m from office'
            : 'FAIL — ${distance.toStringAsFixed(0)}m from office (limit 50m)';
      });
    } catch (e) {
      if (mounted)
        setState(() {
          _gpsPassed = false;
          _gpsMessage =
              'FAIL — ${e.toString().replaceFirst('Exception: ', '')}';
        });
    } finally {
      if (mounted) setState(() => _gpsBusy = false);
    }
  }

  Future<void> _testSelfie() async {
    if (_selfieBusy) return;
    setState(() {
      _selfieBusy = true;
      _selfiePassed = null;
      _selfieMessage = 'Waiting for camera…';
      _selfie = null;
    });
    try {
      final image = await _picker.pickImage(
        source: ImageSource.camera,
        preferredCameraDevice: CameraDevice.front,
        imageQuality: 85,
        maxWidth: 1440,
      );
      if (image == null) {
        if (mounted) setState(() => _selfieMessage = 'Test cancelled');
        return;
      }
      final result = await SelfieQualityService.validate(image.path);
      if (!mounted) return;
      setState(() {
        _selfie = image;
        _selfiePassed = result.isValid;
        _selfieMessage =
            '${result.isValid ? 'PASS' : 'FAIL'} — ${result.message}';
      });
    } catch (_) {
      if (mounted)
        setState(() {
          _selfiePassed = false;
          _selfieMessage = 'FAIL — Unable to test selfie.';
        });
    } finally {
      if (mounted) setState(() => _selfieBusy = false);
    }
  }

  Color? _resultColor(bool? value) => value == null
      ? null
      : value
      ? Colors.green.shade700
      : Colors.red.shade700;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Attendance Security Test')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Card(
            color: const Color(0xFFEAF4FF),
            child: const Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                'ADMIN TEST MODE\n\nThese checks do not create, change, check in, or check out any attendance record.',
                style: TextStyle(fontWeight: FontWeight.w700),
              ),
            ),
          ),
          const SizedBox(height: 16),
          _TestCard(
            icon: Icons.location_on_outlined,
            title: 'Office GPS — 50m',
            message: _gpsMessage,
            resultColor: _resultColor(_gpsPassed),
            busy: _gpsBusy,
            buttonText: 'Test GPS',
            onPressed: _testGps,
          ),
          const SizedBox(height: 16),
          _TestCard(
            icon: Icons.face_retouching_natural,
            title: 'Selfie face quality',
            message: _selfieMessage,
            resultColor: _resultColor(_selfiePassed),
            busy: _selfieBusy,
            buttonText: 'Test Selfie',
            onPressed: _testSelfie,
            trailing: _selfie == null
                ? null
                : ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.file(
                      File(_selfie!.path),
                      width: 72,
                      height: 72,
                      fit: BoxFit.cover,
                    ),
                  ),
          ),
          const SizedBox(height: 20),
          Text(
            'Test cases',
            style: Theme.of(
              context,
            ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          const Text(
            '• Clear single face looking forward → should PASS\n• No face → should FAIL\n• Two people/faces → should FAIL\n• Face too far away → should FAIL\n• Head strongly turned or tilted → should FAIL',
          ),
          if (_distance != null) ...[
            const SizedBox(height: 16),
            Text('Last GPS distance: ${_distance!.toStringAsFixed(1)}m'),
          ],
        ],
      ),
    );
  }
}

class _TestCard extends StatelessWidget {
  const _TestCard({
    required this.icon,
    required this.title,
    required this.message,
    required this.busy,
    required this.buttonText,
    required this.onPressed,
    this.resultColor,
    this.trailing,
  });
  final IconData icon;
  final String title;
  final String message;
  final bool busy;
  final String buttonText;
  final VoidCallback onPressed;
  final Color? resultColor;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 34),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    message,
                    style: TextStyle(
                      color: resultColor,
                      fontWeight: resultColor == null
                          ? FontWeight.normal
                          : FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 12),
                  FilledButton.icon(
                    onPressed: busy ? null : onPressed,
                    icon: busy
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.play_arrow),
                    label: Text(buttonText),
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
