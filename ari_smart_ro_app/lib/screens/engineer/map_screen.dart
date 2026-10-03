import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/engineer_map_service.dart';

class EngineerMapScreen extends StatefulWidget {
  const EngineerMapScreen({super.key});

  @override
  State<EngineerMapScreen> createState() => _EngineerMapScreenState();
}

class _EngineerMapScreenState extends State<EngineerMapScreen> {
  static const LatLng _fallbackCenter = LatLng(27.1767, 78.0081);
  static const Duration _pollInterval = Duration(seconds: 5);
  static const Duration _markerAnimationDuration = Duration(milliseconds: 2200);
  static const Duration _animationFrame = Duration(milliseconds: 80);
  static const int _maxBreadcrumbPoints = 45;
  static const double _minimumTrailMoveMeters = 4;

  final EngineerMapService _service = EngineerMapService();
  final MapController _mapController = MapController();
  final Distance _distance = const Distance();

  List<dynamic> _engineers = <dynamic>[];
  final Map<String, LatLng> _displayPositions = <String, LatLng>{};
  final Map<String, LatLng> _animationStarts = <String, LatLng>{};
  final Map<String, LatLng> _animationTargets = <String, LatLng>{};
  final Map<String, DateTime> _animationStartedAt = <String, DateTime>{};
  final Map<String, List<LatLng>> _breadcrumbs = <String, List<LatLng>>{};
  final Map<String, double> _bearings = <String, double>{};

  Timer? _refreshTimer;
  Timer? _animationTimer;
  bool _isLoading = true;
  bool _isRefreshing = false;
  bool _hasAutoCentered = false;
  String? _followEmployeeKey;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadEngineers();
    _refreshTimer = Timer.periodic(
      _pollInterval,
      (_) => _loadEngineers(silent: true),
    );
    _animationTimer = Timer.periodic(_animationFrame, (_) => _animateMarkers());
  }

  Future<void> _loadEngineers({bool silent = false}) async {
    if (_isRefreshing) return;
    _isRefreshing = true;
    if (!silent && mounted) setState(() => _errorMessage = null);

    try {
      final data = await _service.getEngineers();
      if (!mounted) return;
      final rows = List<dynamic>.from(data);
      _syncMovingPositions(rows);
      setState(() {
        _engineers = rows;
        _isLoading = false;
        _errorMessage = null;
      });

      if (!_hasAutoCentered) {
        final livePoints = rows
            .where((row) => _status(row) == 'LIVE')
            .map(_locationOf)
            .whereType<LatLng>()
            .toList();
        final anyPoints = rows.map(_locationOf).whereType<LatLng>().toList();
        final points = livePoints.isNotEmpty ? livePoints : anyPoints;
        if (points.isNotEmpty) {
          final target = _centroid(points);
          final zoom = points.length == 1 ? 16.0 : 13.5;
          _hasAutoCentered = true;
          WidgetsBinding.instance.addPostFrameCallback((_) {
            if (mounted) _mapController.move(target, zoom);
          });
        }
      }
    } catch (error, stackTrace) {
      debugPrint('Engineer map load error: $error\n$stackTrace');
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = 'Unable to load employee locations. Please try again.';
      });
    } finally {
      _isRefreshing = false;
    }
  }

  void _syncMovingPositions(List<dynamic> rows) {
    final now = DateTime.now();
    final activeKeys = <String>{};

    for (final engineer in rows) {
      final target = _locationOf(engineer);
      if (target == null) continue;
      final key = _employeeKey(engineer);
      activeKeys.add(key);

      final current = _displayPositions[key];
      if (current == null) {
        _displayPositions[key] = target;
        _appendBreadcrumb(key, target);
        continue;
      }

      final targetDistance = _distance.as(LengthUnit.Meter, current, target);
      if (targetDistance < 1) continue;

      _animationStarts[key] = current;
      _animationTargets[key] = target;
      _animationStartedAt[key] = now;
      _appendBreadcrumb(key, target);
    }

    final staleKeys = _displayPositions.keys
        .where((key) => !activeKeys.contains(key))
        .toList();
    for (final key in staleKeys) {
      _displayPositions.remove(key);
      _animationStarts.remove(key);
      _animationTargets.remove(key);
      _animationStartedAt.remove(key);
      _bearings.remove(key);
    }
  }

  void _appendBreadcrumb(String key, LatLng point) {
    final trail = _breadcrumbs.putIfAbsent(key, () => <LatLng>[]);
    if (trail.isNotEmpty) {
      final previous = trail.last;
      final meters = _distance.as(LengthUnit.Meter, previous, point);
      if (meters < _minimumTrailMoveMeters) return;
      _bearings[key] = _bearingBetween(previous, point);
    }
    trail.add(point);
    if (trail.length > _maxBreadcrumbPoints) {
      trail.removeRange(0, trail.length - _maxBreadcrumbPoints);
    }
  }

  void _animateMarkers() {
    if (!mounted || _animationTargets.isEmpty) return;
    final now = DateTime.now();
    var changed = false;
    final completed = <String>[];

    for (final key in _animationTargets.keys.toList()) {
      final start = _animationStarts[key];
      final target = _animationTargets[key];
      final startedAt = _animationStartedAt[key];
      if (start == null || target == null || startedAt == null) {
        completed.add(key);
        continue;
      }

      final elapsed = now.difference(startedAt).inMilliseconds;
      final rawT = elapsed / _markerAnimationDuration.inMilliseconds;
      final t = rawT.clamp(0.0, 1.0);
      final eased = Curves.easeInOut.transform(t);
      final next = LatLng(
        start.latitude + (target.latitude - start.latitude) * eased,
        start.longitude + (target.longitude - start.longitude) * eased,
      );
      _displayPositions[key] = next;
      changed = true;

      if (_followEmployeeKey == key) {
        _mapController.move(next, 17);
      }
      if (t >= 1) completed.add(key);
    }

    for (final key in completed) {
      final target = _animationTargets.remove(key);
      if (target != null) _displayPositions[key] = target;
      _animationStarts.remove(key);
      _animationStartedAt.remove(key);
    }

    if (changed) setState(() {});
  }

  double? _asDouble(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '');
  }

  LatLng? _locationOf(dynamic engineer) {
    if (engineer is! Map) return null;
    final latitude = _asDouble(engineer['latitude']);
    final longitude = _asDouble(engineer['longitude']);
    if (latitude == null || longitude == null) return null;
    if (latitude.abs() > 90 || longitude.abs() > 180) return null;
    return LatLng(latitude, longitude);
  }

  LatLng? _displayLocationOf(dynamic engineer) {
    final raw = _locationOf(engineer);
    if (raw == null) return null;
    return _displayPositions[_employeeKey(engineer)] ?? raw;
  }

  String _employeeKey(dynamic engineer) {
    if (engineer is Map) {
      for (final field in const <String>[
        'employee_id',
        'user_id',
        'id',
        'email',
        'phone',
        'name',
      ]) {
        final value = engineer[field]?.toString().trim();
        if (value != null && value.isNotEmpty) return '$field:$value';
      }
    }
    return 'employee:${engineer.hashCode}';
  }

  String _value(dynamic engineer, String key, {String fallback = '-'}) {
    if (engineer is! Map) return fallback;
    final value = engineer[key]?.toString().trim();
    return value == null || value.isEmpty ? fallback : value;
  }

  String _status(dynamic engineer) {
    if (engineer is! Map) return 'MISSING';
    return (engineer['location_status'] ?? 'MISSING').toString().toUpperCase();
  }

  bool _isOnline(dynamic engineer) =>
      engineer is Map &&
      (engineer['online'] == true || engineer['online'] == 1);

  LatLng _centroid(List<LatLng> points) {
    var lat = 0.0;
    var lng = 0.0;
    for (final point in points) {
      lat += point.latitude;
      lng += point.longitude;
    }
    return LatLng(lat / points.length, lng / points.length);
  }

  double _bearingBetween(LatLng from, LatLng to) {
    final lat1 = from.latitude * math.pi / 180;
    final lat2 = to.latitude * math.pi / 180;
    final deltaLng = (to.longitude - from.longitude) * math.pi / 180;
    final y = math.sin(deltaLng) * math.cos(lat2);
    final x = math.cos(lat1) * math.sin(lat2) -
        math.sin(lat1) * math.cos(lat2) * math.cos(deltaLng);
    return (math.atan2(y, x) * 180 / math.pi + 360) % 360;
  }

  String _timeAgo(dynamic updatedAt) {
    final raw = updatedAt?.toString();
    if (raw == null || raw.isEmpty) return 'Not available';
    final timestamp = DateTime.tryParse(raw);
    if (timestamp == null) return 'Not available';
    final difference = DateTime.now().difference(timestamp.toLocal());
    if (difference.isNegative) return 'Just now';
    if (difference.inSeconds < 60) return '${difference.inSeconds}s ago';
    if (difference.inMinutes < 60) return '${difference.inMinutes} min ago';
    if (difference.inHours < 24) return '${difference.inHours} hr ago';
    if (difference.inDays < 7) return '${difference.inDays} day ago';
    return '${timestamp.toLocal().day.toString().padLeft(2, '0')}/'
        '${timestamp.toLocal().month.toString().padLeft(2, '0')}/'
        '${timestamp.toLocal().year}';
  }

  String _freshnessLabel(dynamic engineer) {
    if (engineer is! Map) return 'No GPS';
    return _timeAgo(engineer['updated_at']);
  }

  Color _markerColor(dynamic engineer) {
    final status = _status(engineer);
    if (status == 'LIVE') return Colors.green;
    if (status == 'STALE') return Colors.orange;
    if (status == 'LOCATION_MISSING') return Colors.red;
    if (!_isOnline(engineer)) return Colors.blueGrey;
    return Colors.red;
  }

  double _calculateDistance(LatLng current, LatLng destination) {
    return _distance.as(LengthUnit.Kilometer, current, destination);
  }

  Future<LatLng?> _tryCurrentLocation() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) return null;
      final permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        return null;
      }
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          timeLimit: Duration(seconds: 6),
        ),
      );
      return LatLng(position.latitude, position.longitude);
    } catch (error) {
      debugPrint('Admin current-location unavailable: $error');
      return null;
    }
  }

  Future<void> _showMyLocation() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        _showMessage('Please enable location services and try again.');
        return;
      }
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        _showMessage('Location permission is required to show your position.');
        return;
      }
      final position = await Geolocator.getCurrentPosition();
      _mapController.move(LatLng(position.latitude, position.longitude), 16);
    } catch (error) {
      debugPrint('My location error: $error');
      _showMessage('Could not get your current location.');
    }
  }

  Future<void> _callEngineer(String phone) async {
    if (phone == '-') {
      _showMessage('Phone number is not available.');
      return;
    }
    final uri = Uri(
      scheme: 'tel',
      path: phone.replaceAll(RegExp(r'[^0-9+]'), ''),
    );
    if (!await launchUrl(uri)) _showMessage('Could not open the phone app.');
  }

  Future<void> _navigateTo(LatLng location) async {
    final current = await _tryCurrentLocation();
    final query = <String, String>{
      'api': '1',
      'destination': '${location.latitude},${location.longitude}',
      'travelmode': 'driving',
    };
    if (current != null) {
      query['origin'] = '${current.latitude},${current.longitude}';
    }

    final directions = Uri.https('www.google.com', '/maps/dir/', query);
    try {
      if (await launchUrl(directions, mode: LaunchMode.externalApplication)) {
        return;
      }
    } catch (_) {
      // Windows may not support externalApplication for an HTTPS URL.
    }
    try {
      if (await launchUrl(directions, mode: LaunchMode.platformDefault)) {
        return;
      }
    } catch (_) {
      // Fall through to a simple destination search URL.
    }

    final search = Uri.https('www.google.com', '/maps/search/', <String, String>{
      'api': '1',
      'query': '${location.latitude},${location.longitude}',
    });
    try {
      if (await launchUrl(search, mode: LaunchMode.platformDefault)) return;
    } catch (_) {
      // Report one clear error below.
    }
    _showMessage('Could not open Google Maps or your default browser.');
  }

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  void _followEngineer(dynamic engineer) {
    final key = _employeeKey(engineer);
    final location = _displayLocationOf(engineer);
    if (location == null) return;
    setState(() => _followEmployeeKey = key);
    _mapController.move(location, 17);
    _showMessage('Following ${_value(engineer, 'name', fallback: 'employee')} live.');
  }

  Future<void> _showEngineerDetails(dynamic engineer, LatLng location) async {
    _mapController.move(location, 17);

    final name = _value(engineer, 'name', fallback: 'Engineer');
    final phone = _value(engineer, 'phone');
    final photoUrl = _value(engineer, 'photo', fallback: '');
    final online = _isOnline(engineer);

    final results = await Future.wait<dynamic>([
      _tryCurrentLocation(),
      _service.reverseGeocode(
        latitude: location.latitude,
        longitude: location.longitude,
      ),
    ]);
    final currentLocation = results[0] as LatLng?;
    final readableAddress = results[1] as String?;

    final distanceKm = currentLocation == null
        ? null
        : _calculateDistance(currentLocation, location);
    Map<String, dynamic>? routeInfo;
    if (currentLocation != null) {
      try {
        routeInfo = await _service.getRoute(
          startLat: currentLocation.latitude,
          startLng: currentLocation.longitude,
          endLat: location.latitude,
          endLng: location.longitude,
        );
      } catch (error) {
        debugPrint('Road route unavailable: $error');
      }
    }

    if (!mounted) return;
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => SafeArea(
        child: Container(
          margin: const EdgeInsets.all(12),
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            borderRadius: BorderRadius.circular(24),
          ),
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Row(
                  children: [
                    CircleAvatar(
                      radius: 34,
                      backgroundColor: Colors.grey.shade200,
                      backgroundImage: photoUrl.isNotEmpty ? NetworkImage(photoUrl) : null,
                      child: photoUrl.isEmpty
                          ? const Icon(Icons.person, size: 34, color: Colors.grey)
                          : null,
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(name, style: Theme.of(context).textTheme.titleLarge),
                          Text(
                            _value(engineer, 'designation', fallback: 'EMPLOYEE'),
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                          const SizedBox(height: 6),
                          _StatusBadge(online: online),
                        ],
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                _InfoCard(
                  icon: Icons.place_outlined,
                  color: Colors.teal,
                  label: 'Current location',
                  value: readableAddress ?? 'Address unavailable — coordinates shown below',
                ),
                const SizedBox(height: 12),
                _InfoCard(
                  icon: Icons.gps_fixed,
                  color: Colors.indigo,
                  label: 'Coordinates',
                  value: '${location.latitude.toStringAsFixed(6)}, ${location.longitude.toStringAsFixed(6)}',
                ),
                const SizedBox(height: 12),
                _InfoCard(
                  icon: Icons.phone_outlined,
                  color: Colors.blue,
                  label: 'Phone',
                  value: phone,
                ),
                const SizedBox(height: 12),
                _InfoCard(
                  icon: Icons.access_time_outlined,
                  color: Colors.orange,
                  label: 'Last updated',
                  value: _timeAgo(engineer is Map ? engineer['updated_at'] : null),
                ),
                const SizedBox(height: 12),
                _InfoCard(
                  icon: Icons.near_me,
                  color: Colors.green,
                  label: 'Distance',
                  value: distanceKm == null
                      ? 'Admin location unavailable'
                      : '${distanceKm.toStringAsFixed(2)} KM',
                ),
                const SizedBox(height: 12),
                _InfoCard(
                  icon: Icons.route,
                  color: Colors.deepPurple,
                  label: 'Road Distance',
                  value: currentLocation == null
                      ? 'Open Navigate for route'
                      : routeInfo == null
                          ? 'Unavailable'
                          : '${((routeInfo['distance'] as num).toDouble() / 1000).toStringAsFixed(2)} KM',
                ),
                const SizedBox(height: 12),
                _InfoCard(
                  icon: Icons.timer,
                  color: Colors.red,
                  label: 'ETA',
                  value: currentLocation == null
                      ? 'Open Navigate for ETA'
                      : routeInfo == null
                          ? 'Unavailable'
                          : '${((routeInfo['duration'] as num).toDouble() / 60).round()} Minutes',
                ),
                const SizedBox(height: 20),
                Row(
                  children: [
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: () => _callEngineer(phone),
                        icon: const Icon(Icons.call),
                        label: const Text('Call'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.green,
                          foregroundColor: Colors.white,
                          minimumSize: const Size.fromHeight(50),
                        ),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: ElevatedButton.icon(
                        onPressed: () => _navigateTo(location),
                        icon: const Icon(Icons.navigation_outlined),
                        label: const Text('Navigate'),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.blue,
                          foregroundColor: Colors.white,
                          minimumSize: const Size.fromHeight(50),
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: () {
                      Navigator.of(context).pop();
                      _followEngineer(engineer);
                    },
                    icon: const Icon(Icons.gps_fixed),
                    label: const Text('Follow live movement'),
                  ),
                ),
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Close'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  List<Polyline> _breadcrumbPolylines() {
    final activeKeys = _engineers.map(_employeeKey).toSet();
    return _breadcrumbs.entries
        .where((entry) => activeKeys.contains(entry.key) && entry.value.length >= 2)
        .map(
          (entry) => Polyline(
            points: List<LatLng>.unmodifiable(entry.value),
            strokeWidth: 3,
            color: Colors.blueAccent.withValues(alpha: .48),
          ),
        )
        .toList();
  }

  @override
  Widget build(BuildContext context) {
    final markers = _engineers.map(_buildMarker).whereType<Marker>().toList();
    final trails = _breadcrumbPolylines();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Employee Live Location'),
        actions: [
          if (_followEmployeeKey != null)
            IconButton(
              tooltip: 'Stop following',
              onPressed: () => setState(() => _followEmployeeKey = null),
              icon: const Icon(Icons.gps_off),
            ),
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isRefreshing ? null : () => _loadEngineers(),
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        tooltip: 'My location',
        onPressed: _showMyLocation,
        child: const Icon(Icons.my_location),
      ),
      body: Column(
        children: [
          Expanded(
            child: Stack(
              children: [
                FlutterMap(
                  mapController: _mapController,
                  options: const MapOptions(
                    initialCenter: _fallbackCenter,
                    initialZoom: 12,
                  ),
                  children: [
                    TileLayer(
                      urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                      userAgentPackageName: 'com.arismartro.app',
                      maxZoom: 19,
                    ),
                    if (trails.isNotEmpty) PolylineLayer(polylines: trails),
                    MarkerLayer(markers: markers),
                    RichAttributionWidget(
                      attributions: const [
                        TextSourceAttribution('OpenStreetMap contributors'),
                      ],
                    ),
                  ],
                ),
                Positioned(
                  left: 12,
                  top: 12,
                  child: _LiveMovingBadge(
                    pollingSeconds: _pollInterval.inSeconds,
                    following: _followEmployeeKey != null,
                  ),
                ),
                if (_isLoading) const Center(child: CircularProgressIndicator()),
                if (!_isLoading && _errorMessage != null)
                  _ErrorBanner(message: _errorMessage!, onRetry: _loadEngineers),
                if (!_isLoading && _errorMessage == null && markers.isEmpty)
                  const Center(child: _EmptyState()),
              ],
            ),
          ),
          if (!_isLoading && _errorMessage == null)
            _EmployeeLocationSummary(
              employees: _engineers,
              onTap: (employee) {
                final location = _displayLocationOf(employee);
                if (location != null) {
                  _showEngineerDetails(employee, location);
                } else {
                  _showMessage(
                    '${_value(employee, 'name', fallback: 'Employee')} has not shared a location yet.',
                  );
                }
              },
            ),
        ],
      ),
    );
  }

  Marker? _buildMarker(dynamic engineer) {
    final location = _displayLocationOf(engineer);
    if (location == null) return null;
    final key = _employeeKey(engineer);
    final color = _markerColor(engineer);
    final name = _value(engineer, 'name', fallback: 'Engineer');
    final photo = _value(engineer, 'photo', fallback: '');
    final bearing = _bearings[key];
    final following = _followEmployeeKey == key;

    return Marker(
      point: location,
      width: 138,
      height: 94,
      child: GestureDetector(
        onTap: () => _showEngineerDetails(engineer, location),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              constraints: const BoxConstraints(maxWidth: 132),
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(8),
                border: following ? Border.all(color: Colors.blue, width: 2) : null,
                boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 4)],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800),
                  ),
                  Text(
                    '${_status(engineer)} • ${_freshnessLabel(engineer)}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 9,
                      color: color,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ],
              ),
            ),
            SizedBox(
              height: 50,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Icon(Icons.location_pin, color: color, size: 48),
                  Positioned(
                    top: 6,
                    child: CircleAvatar(
                      radius: 10,
                      backgroundColor: Colors.white,
                      backgroundImage: photo.isNotEmpty ? NetworkImage(photo) : null,
                      child: photo.isEmpty ? const Icon(Icons.person, size: 12) : null,
                    ),
                  ),
                  if (bearing != null)
                    Positioned(
                      right: 10,
                      bottom: 4,
                      child: Transform.rotate(
                        angle: bearing * math.pi / 180,
                        child: Icon(Icons.navigation, size: 18, color: color),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _animationTimer?.cancel();
    super.dispose();
  }
}

class _LiveMovingBadge extends StatelessWidget {
  const _LiveMovingBadge({required this.pollingSeconds, required this.following});

  final int pollingSeconds;
  final bool following;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: .94),
          borderRadius: BorderRadius.circular(18),
          boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 5)],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.circle, size: 9, color: Colors.green),
            const SizedBox(width: 6),
            Text(
              following ? 'LIVE MOVING • FOLLOW' : 'LIVE MOVING • ${pollingSeconds}s',
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800),
            ),
          ],
        ),
      );
}

class _EmployeeLocationSummary extends StatelessWidget {
  const _EmployeeLocationSummary({required this.employees, required this.onTap});

  final List<dynamic> employees;
  final ValueChanged<dynamic> onTap;

  String _status(dynamic employee) {
    if (employee is! Map) return 'MISSING';
    return (employee['location_status'] ?? 'MISSING').toString().toUpperCase();
  }

  bool _countsAsMissing(String status) =>
      status == 'MISSING' || status == 'LOCATION_MISSING';

  String _name(dynamic employee) {
    if (employee is! Map) return 'Employee';
    final value = employee['name']?.toString().trim();
    return value == null || value.isEmpty ? 'Employee' : value;
  }

  @override
  Widget build(BuildContext context) {
    final live = employees.where((e) => _status(e) == 'LIVE').length;
    final stale = employees.where((e) => _status(e) == 'STALE').length;
    final missing = employees.where((e) => _countsAsMissing(_status(e))).length;

    return Material(
      elevation: 8,
      color: Theme.of(context).colorScheme.surface,
      child: SafeArea(
        top: false,
        child: SizedBox(
          height: 154,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 10, 14, 6),
                child: Text(
                  'Employees: ${employees.length}  •  Live $live  •  Stale $stale  •  Missing $missing',
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13),
                ),
              ),
              Expanded(
                child: ListView.separated(
                  padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
                  scrollDirection: Axis.horizontal,
                  itemCount: employees.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (context, index) {
                    final employee = employees[index];
                    final status = _status(employee);
                    final isLive = status == 'LIVE';
                    final isMissing = status == 'MISSING';
                    final isCriticalMissing = status == 'LOCATION_MISSING';
                    final isCheckedIn =
                        employee is Map && employee['attendance_active'] == true;
                    final color = isLive
                        ? Colors.green
                        : isMissing
                            ? Colors.orange
                            : Colors.red;
                    final statusText = isLive
                        ? 'Live location'
                        : isCheckedIn && status == 'STALE'
                            ? 'Checked in • GPS stale'
                            : isCheckedIn && (isMissing || isCriticalMissing)
                                ? 'Checked in • GPS missing'
                                : status == 'STALE'
                                    ? 'Location stale'
                                    : 'Location missing';
                    return InkWell(
                      onTap: () => onTap(employee),
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        width: 150,
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: color.withValues(alpha: .08),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: color.withValues(alpha: .25)),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              _name(employee),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontWeight: FontWeight.w800),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              statusText,
                              style: TextStyle(
                                color: color,
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              employee is Map
                                  ? (employee['designation'] ?? 'EMPLOYEE').toString()
                                  : 'EMPLOYEE',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.online});
  final bool online;

  @override
  Widget build(BuildContext context) {
    final color = online ? Colors.green : Colors.red;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.circle, size: 8, color: color),
          const SizedBox(width: 6),
          Text(
            online ? 'Online' : 'Offline',
            style: TextStyle(color: color, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({
    required this.icon,
    required this.color,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final Color color;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: color.withValues(alpha: .08),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            CircleAvatar(
              backgroundColor: Colors.white,
              foregroundColor: color,
              child: Icon(icon),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: TextStyle(color: Colors.grey.shade700, fontSize: 13),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    value,
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message, required this.onRetry});
  final String message;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) => Align(
        alignment: Alignment.topCenter,
        child: Container(
          margin: const EdgeInsets.all(16),
          padding: const EdgeInsets.fromLTRB(14, 10, 8, 10),
          decoration: BoxDecoration(
            color: Colors.red.shade50,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.cloud_off_outlined, color: Colors.red),
              const SizedBox(width: 8),
              Flexible(child: Text(message)),
              IconButton(onPressed: onRetry, icon: const Icon(Icons.refresh)),
            ],
          ),
        ),
      );
}

class _EmptyState extends StatelessWidget {
  const _EmptyState();

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.all(24),
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
        ),
        child: const Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.location_off_outlined, size: 40, color: Colors.grey),
            SizedBox(height: 8),
            Text('No employee locations available.'),
          ],
        ),
      );
}
