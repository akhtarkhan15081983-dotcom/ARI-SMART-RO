import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:intl/intl.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/api_service.dart';
import '../../services/work_planner_service.dart';
import '../../utils/search_utils.dart';
import '../complaint/complaint_details_screen.dart';
import '../jobs/job_details_screen.dart';
import 'calendar_rent_collection_screen.dart';

class WorkRouteScreen extends StatefulWidget {
  const WorkRouteScreen({super.key, required this.date, this.employeeId});

  final DateTime date;
  final int? employeeId;

  @override
  State<WorkRouteScreen> createState() => _WorkRouteScreenState();
}

class _WorkRouteScreenState extends State<WorkRouteScreen> {
  static const _fallback = LatLng(27.1767, 78.0081);

  final _service = WorkPlannerService();
  final _controller = MapController();
  final _searchController = TextEditingController();

  List<Map<String, dynamic>> _stops = [];
  List<Map<String, dynamic>> _missingStops = [];
  List<LatLng> _actualRoute = [];
  List<Map<String, dynamic>> _actualWork = [];
  List<Map<String, dynamic>> _trackingGaps = [];
  Map<String, dynamic>? _attendance;
  Map<String, dynamic>? _routeEmployee;

  bool _loading = true;
  String? _error;
  String _role = 'ENGINEER';
  String _query = '';
  String _typeFilter = 'ALL';
  double _distanceKm = 0;
  int _pointCount = 0;

  @override
  void initState() {
    super.initState();
    _initialise();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _initialise() async {
    _role = (await ApiService.getRole() ?? 'ENGINEER').toUpperCase();
    await _load();
  }

  String _dateKey(DateTime value) =>
      '${value.year}-${value.month.toString().padLeft(2, '0')}-${value.day.toString().padLeft(2, '0')}';

  Future<void> _load() async {
    if (mounted) {
      setState(() {
        _loading = true;
        _error = null;
      });
    }

    try {
      final routeFuture = _service.route(widget.date, employeeId: widget.employeeId);
      final calendarFuture = _service.calendar(widget.date, employeeId: widget.employeeId);
      final canLoadActualRoute = _role == 'ENGINEER' || widget.employeeId != null;
      final actualFuture = canLoadActualRoute
          ? _service.dayRoute(widget.date, employeeId: widget.employeeId)
          : Future<Map<String, dynamic>>.value(<String, dynamic>{});

      final results = await Future.wait<Map<String, dynamic>>([
        routeFuture,
        calendarFuture,
        actualFuture,
      ]);
      if (!mounted) return;

      final routeData = results[0];
      final calendarData = results[1];
      final actualData = results[2];
      final selectedDate = _dateKey(widget.date);

      final stops = List<Map<String, dynamic>>.from(
        (routeData['stops'] as List? ?? const []).map(
          (e) => Map<String, dynamic>.from(e as Map),
        ),
      );
      final allDayEvents = List<Map<String, dynamic>>.from(
        (calendarData['events'] as List? ?? const [])
            .where((e) => (e as Map)['date']?.toString() == selectedDate)
            .map((e) => Map<String, dynamic>.from(e as Map)),
      );
      final missing = allDayEvents.where((event) => _point(event) == null).toList();

      final actualPoints = List<Map<String, dynamic>>.from(
        (actualData['route'] as List? ?? const []).map(
          (e) => Map<String, dynamic>.from(e as Map),
        ),
      );
      final actualRoute = actualPoints
          .map((point) {
            final lat = double.tryParse('${point['latitude']}');
            final lng = double.tryParse('${point['longitude']}');
            if (lat == null || lng == null) return null;
            return LatLng(lat, lng);
          })
          .whereType<LatLng>()
          .toList();

      setState(() {
        _stops = stops;
        _missingStops = missing;
        _actualRoute = actualRoute;
        _actualWork = List<Map<String, dynamic>>.from(
          (actualData['work_events'] as List? ?? const []).map(
            (e) => Map<String, dynamic>.from(e as Map),
          ),
        );
        _trackingGaps = List<Map<String, dynamic>>.from(
          (actualData['gaps'] as List? ?? const []).map(
            (e) => Map<String, dynamic>.from(e as Map),
          ),
        );
        _attendance = actualData['attendance'] is Map
            ? Map<String, dynamic>.from(actualData['attendance'] as Map)
            : null;
        _routeEmployee = actualData['employee'] is Map
            ? Map<String, dynamic>.from(actualData['employee'] as Map)
            : null;
        _distanceKm = (actualData['total_distance_km'] as num?)?.toDouble() ?? 0;
        _pointCount = actualData['point_count'] as int? ?? actualRoute.length;
      });

      final focus = _actualRoute.isNotEmpty
          ? _actualRoute.first
          : _stops.isNotEmpty
              ? _point(_stops.first)
              : null;
      if (focus != null) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) _controller.move(focus, 13);
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  LatLng? _point(Map<String, dynamic> event) {
    final rawCustomer = event['customer'];
    if (rawCustomer is! Map) return null;
    final customer = Map<String, dynamic>.from(rawCustomer);
    final lat = double.tryParse('${customer['latitude']}');
    final lng = double.tryParse('${customer['longitude']}');
    if (lat == null || lng == null) return null;
    if (lat.abs() > 90 || lng.abs() > 180) return null;
    return LatLng(lat, lng);
  }

  Color _color(String type) => type == 'RENT'
      ? const Color(0xFF16835B)
      : type == 'COMPLAINT'
          ? const Color(0xFFE24B3B)
          : const Color(0xFF1769AA);

  Future<void> _call(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone.replaceAll(RegExp(r'[^0-9+]'), ''));
    if (!await launchUrl(uri)) _message('Phone app could not be opened.');
  }

  Future<void> _navigate(LatLng destination) async {
    String url =
        'https://www.google.com/maps/dir/?api=1&destination=${destination.latitude},${destination.longitude}&travelmode=driving';
    try {
      final permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.always ||
          permission == LocationPermission.whileInUse) {
        final position = await Geolocator.getCurrentPosition();
        url += '&origin=${position.latitude},${position.longitude}';
      }
    } catch (_) {}
    if (!await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication)) {
      _message('Google Maps could not be opened.');
    }
  }

  void _message(String value) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(value)));
  }

  Future<void> _captureCustomerLocation(Map<String, dynamic> event) async {
    final rawCustomer = event['customer'];
    if (rawCustomer is! Map) return;
    final customer = Map<String, dynamic>.from(rawCustomer);
    final id = customer['id'] as int?;
    if (id == null) return;

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Save customer GPS'),
        content: Text(
          'Only continue when you are physically at ${customer['name']}. The current phone GPS will become this customer\'s saved work location.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('CANCEL'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('SAVE CURRENT GPS'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;

    try {
      if (!await Geolocator.isLocationServiceEnabled()) {
        _message('Turn on GPS first.');
        return;
      }
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) {
        permission = await Geolocator.requestPermission();
      }
      if (permission == LocationPermission.denied ||
          permission == LocationPermission.deniedForever) {
        _message('Location permission is required.');
        return;
      }
      final position = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.high,
          timeLimit: Duration(seconds: 20),
        ),
      );
      await _service.saveCustomerLocation(
        customerId: id,
        latitude: position.latitude,
        longitude: position.longitude,
        accuracy: position.accuracy,
        source: 'WORK_ROUTE',
      );
      _message('Customer GPS saved. Work Map refreshed.');
      await _load();
    } catch (e) {
      _message(e.toString().replaceFirst('Exception: ', ''));
    }
  }

  Future<void> _openWork(Map<String, dynamic> event) async {
    final type = event['type']?.toString();
    final id = event['detail_id'] as int?;
    if (id == null) return;
    Widget screen;
    if (type == 'JOB') {
      screen = JobDetailsScreen(jobId: id);
    } else if (type == 'COMPLAINT') {
      screen = ComplaintDetailsScreen(complaintId: id);
    } else if (type == 'RENT') {
      if (_role == 'OFFICE') {
        _message(
          'Office can schedule work; collection remains with Admin/Manager or assigned Engineer.',
        );
        return;
      }
      screen = CalendarRentCollectionScreen(event: event);
    } else {
      return;
    }
    await Navigator.push(context, MaterialPageRoute(builder: (_) => screen));
    await _load();
  }

  List<Map<String, dynamic>> get _filteredStops {
    return _stops.where((event) {
      final type = (event['type'] ?? '').toString().toUpperCase();
      if (_typeFilter != 'ALL' && type != _typeFilter) return false;
      final customer = Map<String, dynamic>.from(event['customer'] as Map);
      return matchesAllSearchTerms(_query, [
        (event['title'] ?? '').toString(),
        (event['status'] ?? '').toString(),
        type,
        (customer['name'] ?? '').toString(),
        (customer['customer_id'] ?? '').toString(),
        (customer['phone'] ?? '').toString(),
        (customer['address'] ?? '').toString(),
        (customer['area'] ?? '').toString(),
        (customer['city'] ?? '').toString(),
        (customer['pincode'] ?? '').toString(),
      ]);
    }).toList();
  }

  String _clock(dynamic raw) {
    final parsed = DateTime.tryParse(raw?.toString() ?? '');
    if (parsed == null) return '-';
    return DateFormat('h:mm a').format(parsed.toLocal());
  }

  Widget _summaryCard() {
    final employeeName = _routeEmployee?['name']?.toString();
    final checkIn = _attendance?['check_in'];
    final checkOut = _attendance?['check_out'];
    return Card(
      margin: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.route),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    employeeName == null ? 'Today Work Map' : '$employeeName • Day Route',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 14,
              runSpacing: 6,
              children: [
                Text('GPS points: $_pointCount'),
                Text('Distance: ${_distanceKm.toStringAsFixed(2)} km'),
                Text('Work: ${_actualWork.length}'),
                Text('Missing GPS: ${_missingStops.length}'),
                if (checkIn != null) Text('In: ${_clock(checkIn)}'),
                if (checkOut != null) Text('Out: ${_clock(checkOut)}'),
              ],
            ),
            if (_trackingGaps.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(
                '${_trackingGaps.length} tracking gap(s) detected. Route is shown only from real GPS points; no fake line is invented across missing periods.',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ],
            if (_role != 'ENGINEER' && widget.employeeId == null) ...[
              const SizedBox(height: 8),
              const Text(
                'Select an employee from Work Calendar to see that employee\'s actual travelled route.',
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _map() {
    final filteredStops = _filteredStops;
    final markers = filteredStops.map((event) {
      final point = _point(event)!;
      final sequence = event['sequence']?.toString() ?? '';
      return Marker(
        point: point,
        width: 54,
        height: 54,
        child: GestureDetector(
          onTap: () => _showStopDetails(event),
          child: Stack(
            alignment: Alignment.center,
            children: [
              Icon(
                Icons.location_pin,
                size: 52,
                color: _color(event['type'].toString()),
              ),
              Positioned(
                top: 9,
                child: CircleAvatar(
                  radius: 10,
                  backgroundColor: Colors.white,
                  child: Text(
                    sequence,
                    style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w900),
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }).toList();

    final initial = _actualRoute.isNotEmpty
        ? _actualRoute.first
        : filteredStops.isNotEmpty
            ? _point(filteredStops.first)!
            : _fallback;

    return FlutterMap(
      mapController: _controller,
      options: MapOptions(initialCenter: initial, initialZoom: 13),
      children: [
        TileLayer(
          urlTemplate: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
          subdomains: const ['a', 'b', 'c'],
          userAgentPackageName: 'com.arismartro.app',
        ),
        if (_actualRoute.length >= 2)
          PolylineLayer(
            polylines: [
              Polyline(
                points: _actualRoute,
                strokeWidth: 5,
                color: Theme.of(context).colorScheme.primary,
              ),
            ],
          ),
        MarkerLayer(markers: markers),
      ],
    );
  }

  void _showStopDetails(Map<String, dynamic> event) {
    final customer = Map<String, dynamic>.from(event['customer'] as Map);
    final point = _point(event);
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(20, 14, 20, 20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                customer['name']?.toString() ?? 'Customer',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
              ),
              Text('${event['title']} • ${event['status']}'),
              const Divider(height: 26),
              _Detail(icon: Icons.badge_outlined, text: '${customer['customer_id'] ?? '-'}'),
              _Detail(icon: Icons.phone_outlined, text: '${customer['phone'] ?? '-'}'),
              _Detail(
                icon: Icons.location_on_outlined,
                text: '${customer['address'] ?? ''}, ${customer['area'] ?? ''}, ${customer['city'] ?? ''} - ${customer['pincode'] ?? ''}',
              ),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _call('${customer['phone'] ?? ''}'),
                      icon: const Icon(Icons.call),
                      label: const Text('Call'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: point == null ? null : () => _navigate(point),
                      icon: const Icon(Icons.navigation),
                      label: const Text('Navigate'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: FilledButton.tonalIcon(
                  onPressed: () {
                    Navigator.pop(context);
                    _openWork(event);
                  },
                  icon: const Icon(Icons.play_circle_outline),
                  label: const Text('Open Work Flow'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _workList() {
    final mapped = _filteredStops;
    final missing = _missingStops.where((event) {
      final type = (event['type'] ?? '').toString().toUpperCase();
      if (_typeFilter != 'ALL' && type != _typeFilter) return false;
      final customer = Map<String, dynamic>.from(event['customer'] as Map);
      return matchesAllSearchTerms(_query, [
        event['title']?.toString() ?? '',
        event['status']?.toString() ?? '',
        customer['name']?.toString() ?? '',
        customer['phone']?.toString() ?? '',
        customer['area']?.toString() ?? '',
      ]);
    }).toList();

    return ListView(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 18),
      children: [
        if (mapped.isEmpty && missing.isEmpty && _actualWork.isEmpty)
          const Padding(
            padding: EdgeInsets.all(24),
            child: Center(child: Text('No work found for this day.')),
          ),
        for (final event in mapped)
          Card(
            child: ListTile(
              onTap: () {
                final point = _point(event);
                if (point != null) _controller.move(point, 16);
                _showStopDetails(event);
              },
              leading: CircleAvatar(
                backgroundColor: _color(event['type'].toString()),
                foregroundColor: Colors.white,
                child: Text('${event['sequence'] ?? ''}'),
              ),
              title: Text(
                '${(event['customer'] as Map)['name']}',
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              subtitle: Text('${event['title']} • ${event['status']}'),
              trailing: const Icon(Icons.chevron_right),
            ),
          ),
        if (missing.isNotEmpty) ...[
          const Padding(
            padding: EdgeInsets.only(top: 10, bottom: 4),
            child: Text(
              'LOCATION MISSING',
              style: TextStyle(fontWeight: FontWeight.w900),
            ),
          ),
          for (final event in missing)
            Card(
              child: ListTile(
                leading: const Icon(Icons.location_off),
                title: Text('${(event['customer'] as Map)['name']}'),
                subtitle: Text('${event['title']} • ${(event['customer'] as Map)['area']}'),
                trailing: TextButton(
                  onPressed: () => _captureCustomerLocation(event),
                  child: const Text('CAPTURE GPS'),
                ),
                onTap: () => _openWork(event),
              ),
            ),
        ],
        if (_actualWork.isNotEmpty) ...[
          const Padding(
            padding: EdgeInsets.only(top: 14, bottom: 4),
            child: Text(
              'ACTUAL WORK TIMELINE',
              style: TextStyle(fontWeight: FontWeight.w900),
            ),
          ),
          for (final work in _actualWork)
            Card(
              child: ListTile(
                leading: Icon(
                  (work['status'] ?? '').toString().toUpperCase() == 'COMPLETED'
                      ? Icons.check_circle
                      : Icons.work_outline,
                ),
                title: Text('${work['title'] ?? 'Work'} • ${work['status'] ?? '-'}'),
                subtitle: Text(
                  '${(work['customer'] as Map?)?['name'] ?? '-'}\nScheduled ${_clock(work['scheduled_at'])}${work['started_at'] != null ? ' • Started ${_clock(work['started_at'])}' : ''}${work['completed_at'] != null ? ' • Completed ${_clock(work['completed_at'])}' : ''}',
                ),
                isThreeLine: true,
              ),
            ),
        ],
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Today Work Map • ${DateFormat('d MMM').format(widget.date)}'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _loading ? null : _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        const Icon(Icons.cloud_off, size: 44),
                        const SizedBox(height: 10),
                        Text(_error!, textAlign: TextAlign.center),
                        TextButton(onPressed: _load, child: const Text('Retry')),
                      ],
                    ),
                  ),
                )
              : Column(
                  children: [
                    _summaryCard(),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(12, 4, 12, 4),
                      child: Row(
                        children: [
                          Expanded(
                            flex: 2,
                            child: TextField(
                              controller: _searchController,
                              onChanged: (value) => setState(() => _query = value),
                              decoration: InputDecoration(
                                hintText: 'Search work/customer...',
                                prefixIcon: const Icon(Icons.search),
                                suffixIcon: _query.isEmpty
                                    ? null
                                    : IconButton(
                                        onPressed: () {
                                          _searchController.clear();
                                          setState(() => _query = '');
                                        },
                                        icon: const Icon(Icons.clear),
                                      ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: DropdownButtonFormField<String>(
                              initialValue: _typeFilter,
                              decoration: const InputDecoration(labelText: 'Type'),
                              items: const [
                                DropdownMenuItem(value: 'ALL', child: Text('All')),
                                DropdownMenuItem(value: 'JOB', child: Text('Jobs')),
                                DropdownMenuItem(value: 'COMPLAINT', child: Text('Complaints')),
                                DropdownMenuItem(value: 'RENT', child: Text('Rent')),
                              ],
                              onChanged: (value) => setState(() => _typeFilter = value ?? 'ALL'),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Expanded(flex: 3, child: _map()),
                    Expanded(flex: 3, child: _workList()),
                  ],
                ),
    );
  }
}

class _Detail extends StatelessWidget {
  const _Detail({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 20),
            const SizedBox(width: 10),
            Expanded(child: Text(text)),
          ],
        ),
      );
}
