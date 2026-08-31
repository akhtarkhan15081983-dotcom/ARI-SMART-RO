import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:intl/intl.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/api_service.dart';
import '../../services/work_planner_service.dart';
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
  List<Map<String, dynamic>> _stops = [];
  bool _loading = true;
  String? _error;
  int _missing = 0;
  String _role = 'ENGINEER';

  @override
  void initState() {
    super.initState();
    _initialise();
  }

  Future<void> _initialise() async {
    _role = (await ApiService.getRole() ?? 'ENGINEER').toUpperCase();
    await _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _service.route(
        widget.date,
        employeeId: widget.employeeId,
      );
      if (!mounted) return;
      setState(() {
        _stops = List<Map<String, dynamic>>.from(
          (data['stops'] as List? ?? []).map(
            (e) => Map<String, dynamic>.from(e as Map),
          ),
        );
        _missing = data['missing_location_count'] as int? ?? 0;
      });
      if (_stops.isNotEmpty) _controller.move(_point(_stops.first)!, 13);
    } catch (e) {
      if (mounted)
        setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  LatLng? _point(Map<String, dynamic> event) {
    final customer = Map<String, dynamic>.from(event['customer'] as Map);
    final lat = double.tryParse('${customer['latitude']}'),
        lng = double.tryParse('${customer['longitude']}');
    return lat == null || lng == null ? null : LatLng(lat, lng);
  }

  Color _color(String type) => type == 'RENT'
      ? const Color(0xFF16835B)
      : type == 'COMPLAINT'
      ? const Color(0xFFE24B3B)
      : const Color(0xFF1769AA);

  Future<void> _call(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone);
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
    if (!await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication))
      _message('Google Maps could not be opened.');
  }

  void _message(String value) => ScaffoldMessenger.of(
    context,
  ).showSnackBar(SnackBar(content: Text(value)));

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

  void _details(Map<String, dynamic> event) {
    final customer = Map<String, dynamic>.from(event['customer'] as Map),
        point = _point(event)!;
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
              Center(
                child: Container(
                  width: 44,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.black26,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  CircleAvatar(
                    backgroundColor: _color(
                      event['type'].toString(),
                    ).withOpacity(.12),
                    child: Text(
                      '${event['sequence']}',
                      style: TextStyle(
                        color: _color(event['type'].toString()),
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          customer['name'].toString(),
                          style: Theme.of(context).textTheme.titleLarge
                              ?.copyWith(fontWeight: FontWeight.w800),
                        ),
                        Text('${event['title']} • ${event['status']}'),
                      ],
                    ),
                  ),
                ],
              ),
              const Divider(height: 28),
              _Detail(
                icon: Icons.badge_outlined,
                text: customer['customer_id'].toString(),
              ),
              _Detail(
                icon: Icons.phone_outlined,
                text: customer['phone'].toString(),
              ),
              _Detail(
                icon: Icons.location_on_outlined,
                text:
                    '${customer['address']}, ${customer['area']}, ${customer['city']} - ${customer['pincode']}',
              ),
              if (event['amount'] != null)
                _Detail(
                  icon: Icons.payments_outlined,
                  text: 'Collection due: ₹${event['amount']}',
                ),
              const SizedBox(height: 14),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton.icon(
                      onPressed: () => _call(customer['phone'].toString()),
                      icon: const Icon(Icons.call),
                      label: const Text('Call'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: () => _navigate(point),
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
                  icon: Icon(
                    event['type'] == 'RENT'
                        ? Icons.payments
                        : Icons.play_circle_outline,
                  ),
                  label: Text(
                    event['type'] == 'RENT'
                        ? 'Collect Rent'
                        : event['type'] == 'COMPLAINT'
                        ? 'Open Complaint Flow'
                        : 'Open Work Flow',
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final markers = _stops.map((event) {
      final point = _point(event)!;
      return Marker(
        point: point,
        width: 54,
        height: 54,
        child: GestureDetector(
          onTap: () => _details(event),
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
                    '${event['sequence']}',
                    style: const TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      );
    }).toList();
    return Scaffold(
      appBar: AppBar(
        title: Text('Work Route • ${DateFormat('d MMM').format(widget.date)}'),
        actions: [
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh)),
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
                if (_missing > 0)
                  MaterialBanner(
                    content: Text(
                      '$_missing work item map par nahi dikh raha kyunki customer GPS location missing hai.',
                    ),
                    leading: const Icon(
                      Icons.location_off,
                      color: Colors.orange,
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => ScaffoldMessenger.of(
                          context,
                        ).hideCurrentMaterialBanner(),
                        child: const Text('OK'),
                      ),
                    ],
                  ),
                Expanded(
                  flex: 3,
                  child: FlutterMap(
                    mapController: _controller,
                    options: MapOptions(
                      initialCenter: markers.isEmpty
                          ? _fallback
                          : _point(_stops.first)!,
                      initialZoom: 13,
                    ),
                    children: [
                      TileLayer(
                        urlTemplate:
                            'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
                        subdomains: const ['a', 'b', 'c'],
                        userAgentPackageName: 'com.arismartro.app',
                      ),
                      MarkerLayer(markers: markers),
                    ],
                  ),
                ),
                Expanded(
                  flex: 2,
                  child: _stops.isEmpty
                      ? const Center(
                          child: Text('No mapped work stops for this day.'),
                        )
                      : ListView.separated(
                          padding: const EdgeInsets.all(12),
                          itemCount: _stops.length,
                          separatorBuilder: (_, __) =>
                              const SizedBox(height: 6),
                          itemBuilder: (_, index) {
                            final event = _stops[index],
                                customer = Map<String, dynamic>.from(
                                  event['customer'] as Map,
                                ),
                                point = _point(event)!;
                            return Card(
                              child: ListTile(
                                onTap: () {
                                  _controller.move(point, 16);
                                  _details(event);
                                },
                                leading: CircleAvatar(
                                  backgroundColor: _color(
                                    event['type'].toString(),
                                  ),
                                  foregroundColor: Colors.white,
                                  child: Text('${event['sequence']}'),
                                ),
                                title: Text(
                                  customer['name'].toString(),
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                                subtitle: Text(
                                  '${event['title']} • ${customer['area']}',
                                ),
                                trailing: IconButton(
                                  onPressed: () => _navigate(point),
                                  icon: const Icon(Icons.navigation),
                                ),
                              ),
                            );
                          },
                        ),
                ),
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
        Icon(icon, size: 20, color: Colors.black54),
        const SizedBox(width: 10),
        Expanded(child: Text(text)),
      ],
    ),
  );
}
