import 'dart:async';
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

  final EngineerMapService _service = EngineerMapService();
  final MapController _mapController = MapController();

  List<dynamic> _engineers = <dynamic>[];
  Timer? _refreshTimer;
  bool _isLoading = true;
  bool _isRefreshing = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _loadEngineers();
    _refreshTimer = Timer.periodic(
      const Duration(seconds: 10),
      (_) => _loadEngineers(silent: true),
    );
  }

  Future<void> _loadEngineers({bool silent = false}) async {
    if (_isRefreshing) return;
    _isRefreshing = true;

    if (!silent && mounted) {
      setState(() => _errorMessage = null);
    }

    try {
      final data = await _service.getEngineers();
      if (!mounted) return;

      setState(() {
        _engineers = List<dynamic>.from(data);
        _isLoading = false;
        _errorMessage = null;
      });
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

  String _value(dynamic engineer, String key, {String fallback = '-'}) {
    if (engineer is! Map) return fallback;
    final value = engineer[key]?.toString().trim();
    return value == null || value.isEmpty ? fallback : value;
  }

  bool _isOnline(dynamic engineer) =>
      engineer is Map &&
      (engineer['online'] == true || engineer['online'] == 1);

  String _timeAgo(dynamic updatedAt) {
    final rawValue = updatedAt?.toString();
    if (rawValue == null || rawValue.isEmpty) return 'Not available';

    final timestamp = DateTime.tryParse(rawValue);
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

  double _calculateDistance(LatLng current, LatLng destination) {
    const Distance distance = Distance();

    return distance.as(LengthUnit.Kilometer, current, destination);
  }

  Future<void> _showMyLocation() async {
    try {
      var serviceEnabled = await Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
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
    final current = await Geolocator.getCurrentPosition();

    final uri = Uri.parse(
      "https://www.google.com/maps/dir/?api=1"
      "&origin=${current.latitude},${current.longitude}"
      "&destination=${location.latitude},${location.longitude}"
      "&travelmode=driving",
    );

    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      _showMessage("Could not open Google Maps.");
    }
  }

  void _showMessage(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _showEngineerDetails(dynamic engineer, LatLng location) async {
    _mapController.move(location, 17);

    final name = _value(engineer, 'name', fallback: 'Engineer');
    final phone = _value(engineer, 'phone');
    final photoUrl = _value(engineer, 'photo', fallback: '');
    final online = _isOnline(engineer);
    LatLng? currentLocation;

    try {
      final position = await Geolocator.getCurrentPosition();

      currentLocation = LatLng(position.latitude, position.longitude);
    } catch (_) {}

    final distanceKm = currentLocation == null
        ? null
        : _calculateDistance(currentLocation, location);
    Map<String, dynamic>? routeInfo;

    if (currentLocation != null) {
      routeInfo = await _service.getRoute(
        startLat: currentLocation.latitude,
        startLng: currentLocation.longitude,
        endLat: location.latitude,
        endLng: location.longitude,
      );
    }

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
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 34,
                    backgroundColor: Colors.grey.shade200,
                    backgroundImage: photoUrl.isNotEmpty
                        ? NetworkImage(photoUrl)
                        : null,
                    child: photoUrl.isEmpty
                        ? const Icon(Icons.person, size: 34, color: Colors.grey)
                        : null,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          name,
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
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
                value: _timeAgo(
                  engineer is Map ? engineer['updated_at'] : null,
                ),
              ),
              const SizedBox(height: 12),

              _InfoCard(
                icon: Icons.near_me,
                color: Colors.green,
                label: "Distance",
                value: distanceKm == null
                    ? "Unknown"
                    : "${distanceKm.toStringAsFixed(2)} KM",
              ),
              const SizedBox(height: 12),

              _InfoCard(
                icon: Icons.route,
                color: Colors.deepPurple,
                label: "Road Distance",
                value: routeInfo == null
                    ? "Loading..."
                    : "${(routeInfo["distance"] / 1000).toStringAsFixed(2)} KM",
              ),

              const SizedBox(height: 12),

              _InfoCard(
                icon: Icons.timer,
                color: Colors.red,
                label: "ETA",
                value: routeInfo == null
                    ? "Loading..."
                    : "${(routeInfo["duration"] / 60).round()} Minutes",
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
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Close'),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final markers = _engineers.map(_buildMarker).whereType<Marker>().toList();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Employee Live Location'),
        actions: [
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
                    MarkerLayer(markers: markers),
                    RichAttributionWidget(
                      attributions: const [
                        TextSourceAttribution('OpenStreetMap contributors'),
                      ],
                    ),
                  ],
                ),
                if (_isLoading)
                  const Center(child: CircularProgressIndicator()),
                if (!_isLoading && _errorMessage != null)
                  _ErrorBanner(message: _errorMessage!, onRetry: _loadEngineers),
                if (!_isLoading &&
                    _errorMessage == null &&
                    markers.isEmpty)
                  const Center(child: _EmptyState()),
              ],
            ),
          ),
          if (!_isLoading && _errorMessage == null)
            _EmployeeLocationSummary(
              employees: _engineers,
              onTap: (employee) {
                final location = _locationOf(employee);
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
    final location = _locationOf(engineer);
    if (location == null) return null;
    final online = _isOnline(engineer);
    final name = _value(engineer, 'name', fallback: 'Engineer');

    return Marker(
      point: location,
      width: 126,
      height: 74,
      child: GestureDetector(
        onTap: () => _showEngineerDetails(engineer, location),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              constraints: const BoxConstraints(maxWidth: 118),
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(8),
                boxShadow: const [
                  BoxShadow(color: Colors.black26, blurRadius: 4),
                ],
              ),
              child: Text(
                name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            Stack(
              alignment: Alignment.center,
              children: [
                Icon(
                  Icons.location_pin,
                  color: online ? Colors.green : Colors.red,
                  size: 46,
                ),

                Positioned(
                  top: 6,
                  child: CircleAvatar(
                    radius: 10,
                    backgroundColor: Colors.white,

                    backgroundImage:
                        _value(engineer, "photo", fallback: "").isNotEmpty
                        ? NetworkImage(_value(engineer, "photo", fallback: ""))
                        : null,

                    child: _value(engineer, "photo", fallback: "").isEmpty
                        ? const Icon(Icons.person, size: 12)
                        : null,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }
}

class _EmployeeLocationSummary extends StatelessWidget {
  const _EmployeeLocationSummary({
    required this.employees,
    required this.onTap,
  });

  final List<dynamic> employees;
  final ValueChanged<dynamic> onTap;

  String _status(dynamic employee) {
    if (employee is! Map) return 'MISSING';
    return (employee['location_status'] ?? 'MISSING')
        .toString()
        .toUpperCase();
  }

  String _name(dynamic employee) {
    if (employee is! Map) return 'Employee';
    final value = employee['name']?.toString().trim();
    return value == null || value.isEmpty ? 'Employee' : value;
  }

  @override
  Widget build(BuildContext context) {
    final live = employees.where((e) => _status(e) == 'LIVE').length;
    final stale = employees.where((e) => _status(e) == 'STALE').length;
    final missing = employees.where((e) => _status(e) == 'MISSING').length;

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
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        'Employees: ${employees.length}  •  Live $live  •  Stale $stale  •  Missing $missing',
                        style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
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
                    final color = isLive
                        ? Colors.green
                        : isMissing
                            ? Colors.orange
                            : Colors.red;
                    return InkWell(
                      onTap: () => onTap(employee),
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        width: 150,
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: color.withValues(alpha: .08),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: color.withValues(alpha: .25),
                          ),
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              _name(employee),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontWeight: FontWeight.w800,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              status == 'LIVE'
                                  ? 'Live location'
                                  : status == 'STALE'
                                      ? 'Location stale'
                                      : 'Location missing',
                              style: TextStyle(
                                color: color,
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              employee is Map
                                  ? (employee['designation'] ?? 'EMPLOYEE')
                                      .toString()
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
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w700,
                ),
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
