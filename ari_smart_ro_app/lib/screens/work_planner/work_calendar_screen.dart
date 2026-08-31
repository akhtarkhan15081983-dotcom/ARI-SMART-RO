import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:intl/intl.dart';

import '../../services/api_service.dart';
import '../../services/work_planner_service.dart';
import '../complaint/complaint_details_screen.dart';
import '../jobs/job_details_screen.dart';
import 'calendar_rent_collection_screen.dart';
import 'work_route_screen.dart';

class WorkCalendarScreen extends StatefulWidget {
  const WorkCalendarScreen({super.key});

  @override
  State<WorkCalendarScreen> createState() => _WorkCalendarScreenState();
}

class _WorkCalendarScreenState extends State<WorkCalendarScreen> {
  final _service = WorkPlannerService();
  DateTime _month = DateTime(DateTime.now().year, DateTime.now().month);
  DateTime _selected = DateUtils.dateOnly(DateTime.now());
  List<Map<String, dynamic>> _events = [], _employees = [];
  int? _employeeId;
  String _role = 'ENGINEER';
  bool _loading = true;
  String? _error;

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
      final data = await _service.calendar(_month, employeeId: _employeeId);
      if (!mounted) return;
      setState(() {
        _events = List<Map<String, dynamic>>.from(
          (data['events'] as List? ?? []).map(
            (e) => Map<String, dynamic>.from(e as Map),
          ),
        );
        _employees = List<Map<String, dynamic>>.from(
          (data['employees'] as List? ?? []).map(
            (e) => Map<String, dynamic>.from(e as Map),
          ),
        );
      });
    } catch (e) {
      if (mounted) {
        setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  List<Map<String, dynamic>> _forDay(DateTime day) {
    final value = DateFormat('yyyy-MM-dd').format(day);
    return _events.where((event) => event['date'] == value).toList();
  }

  Color _typeColor(String type) => switch (type) {
    'RENT' => const Color(0xFF16835B),
    'COMPLAINT' => const Color(0xFFE24B3B),
    _ => const Color(0xFF1769AA),
  };

  Future<void> _changeMonth(int delta) async {
    _month = DateTime(_month.year, _month.month + delta);
    _selected = DateTime(_month.year, _month.month, 1);
    await _load();
  }

  Future<void> _reschedule(Map<String, dynamic> event) async {
    final picked = await showDatePicker(
      context: context,
      initialDate:
          DateTime.tryParse(event['scheduled_at'].toString()) ?? _selected,
      firstDate: DateTime.now().subtract(const Duration(days: 31)),
      lastDate: DateTime.now().add(const Duration(days: 730)),
    );
    if (picked == null || !mounted) return;
    final reason = TextEditingController();
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Forward / Reschedule work'),
        content: TextField(
          controller: reason,
          maxLines: 3,
          decoration: const InputDecoration(
            labelText: 'Reason',
            hintText: 'Customer requested another date',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Update'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _service.reschedule(
        eventKey: event['key'].toString(),
        scheduledAt: DateTime(picked.year, picked.month, picked.day, 9),
        employeeId: _employeeId,
        reason: reason.text,
      );
      _month = DateTime(picked.year, picked.month);
      _selected = picked;
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Work schedule updated')));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('$e')));
      }
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
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text(
              'Office can schedule this work; payment collection remains with Admin/Manager or assigned Engineer.',
            ),
          ),
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

  Future<void> _captureLocation(Map<String, dynamic> event) async {
    final customer = Map<String, dynamic>.from(event['customer'] as Map);
    if (customer['latitude'] != null && customer['longitude'] != null) return;
    if (!await Geolocator.isLocationServiceEnabled()) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Please enable phone location service.'),
          ),
        );
      }
      return;
    }
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Location permission is required.')),
        );
      }
      return;
    }
    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 20),
      ),
    );
    if (!mounted) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Save customer location?'),
        content: Text(
          '${customer['name']}\n\nGPS accuracy: ±${position.accuracy.toStringAsFixed(1)} metres\n\nPlease confirm you are at the customer site.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Save Location'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _service.saveCustomerLocation(
        customerId: customer['id'] as int,
        latitude: position.latitude,
        longitude: position.longitude,
        accuracy: position.accuracy,
      );
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Customer location saved successfully.'),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final dayEvents = _forDay(_selected);
    final staffView =
        _role == 'ADMIN' || _role == 'MANAGER' || _role == 'OFFICE';
    return Scaffold(
      appBar: AppBar(
        title: const Text('Work Calendar'),
        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: _load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            if (staffView && _employees.isNotEmpty)
              DropdownButtonFormField<int?>(
                initialValue: _employeeId,
                decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.engineering),
                  labelText: 'Employee work',
                ),
                items: [
                  const DropdownMenuItem<int?>(
                    value: null,
                    child: Text('All engineers'),
                  ),
                  ..._employees.map(
                    (e) => DropdownMenuItem<int?>(
                      value: e['id'] as int,
                      child: Text(e['name'].toString()),
                    ),
                  ),
                ],
                onChanged: (value) {
                  _employeeId = value;
                  _load();
                },
              ),
            if (staffView) const SizedBox(height: 12),
            _CalendarHeader(
              month: _month,
              previous: () => _changeMonth(-1),
              next: () => _changeMonth(1),
            ),
            const SizedBox(height: 10),
            _MonthGrid(
              month: _month,
              selected: _selected,
              eventsFor: _forDay,
              colorFor: _typeColor,
              onSelected: (day) => setState(() => _selected = day),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: Text(
                    DateFormat('EEEE, d MMMM').format(_selected),
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                FilledButton.icon(
                  onPressed: () => Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => WorkRouteScreen(
                        date: _selected,
                        employeeId: _employeeId,
                      ),
                    ),
                  ),
                  icon: const Icon(Icons.route),
                  label: const Text('Route'),
                ),
              ],
            ),
            const SizedBox(height: 10),
            if (_loading)
              const Padding(
                padding: EdgeInsets.all(40),
                child: Center(child: CircularProgressIndicator()),
              )
            else if (_error != null)
              _MessageCard(
                icon: Icons.cloud_off,
                text: _error!,
                color: Colors.red,
              )
            else if (dayEvents.isEmpty)
              const _MessageCard(
                icon: Icons.event_available,
                text: 'No work scheduled for this day.',
                color: Colors.blueGrey,
              )
            else
              ...dayEvents.map(
                (event) => _WorkCard(
                  event: event,
                  color: _typeColor(event['type'].toString()),
                  onOpen: () => _openWork(event),
                  onLocation: () => _captureLocation(event),
                  onReschedule: () => _reschedule(event),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _CalendarHeader extends StatelessWidget {
  const _CalendarHeader({
    required this.month,
    required this.previous,
    required this.next,
  });
  final DateTime month;
  final VoidCallback previous, next;
  @override
  Widget build(BuildContext context) => Row(
    children: [
      IconButton(onPressed: previous, icon: const Icon(Icons.chevron_left)),
      Expanded(
        child: Text(
          DateFormat('MMMM yyyy').format(month),
          textAlign: TextAlign.center,
          style: Theme.of(
            context,
          ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
        ),
      ),
      IconButton(onPressed: next, icon: const Icon(Icons.chevron_right)),
    ],
  );
}

class _MonthGrid extends StatelessWidget {
  const _MonthGrid({
    required this.month,
    required this.selected,
    required this.eventsFor,
    required this.colorFor,
    required this.onSelected,
  });
  final DateTime month, selected;
  final List<Map<String, dynamic>> Function(DateTime) eventsFor;
  final Color Function(String) colorFor;
  final ValueChanged<DateTime> onSelected;
  @override
  Widget build(BuildContext context) {
    final first = DateTime(month.year, month.month, 1),
        days = DateTime(month.year, month.month + 1, 0).day;
    final offset = first.weekday % 7, cells = offset + days;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          children: [
            Row(
              children: [
                for (final d in ['S', 'M', 'T', 'W', 'T', 'F', 'S'])
                  Expanded(
                    child: Text(
                      d,
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        color: Colors.black54,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 8),
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 7,
                childAspectRatio: .88,
              ),
              itemCount: ((cells + 6) ~/ 7) * 7,
              itemBuilder: (_, index) {
                final number = index - offset + 1;
                if (number < 1 || number > days) return const SizedBox();
                final day = DateTime(month.year, month.month, number),
                    events = eventsFor(day),
                    active = DateUtils.isSameDay(day, selected);
                return InkWell(
                  onTap: () => onSelected(day),
                  borderRadius: BorderRadius.circular(12),
                  child: Container(
                    margin: const EdgeInsets.all(2),
                    decoration: BoxDecoration(
                      color: active ? const Color(0xFF0B63A5) : null,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          '$number',
                          style: TextStyle(
                            color: active ? Colors.white : Colors.black87,
                            fontWeight: active
                                ? FontWeight.w800
                                : FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Wrap(
                          spacing: 2,
                          children: events
                              .take(3)
                              .map(
                                (e) => Container(
                                  width: 5,
                                  height: 5,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: active
                                        ? Colors.white
                                        : colorFor(e['type'].toString()),
                                  ),
                                ),
                              )
                              .toList(),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _WorkCard extends StatelessWidget {
  const _WorkCard({
    required this.event,
    required this.color,
    required this.onOpen,
    required this.onLocation,
    required this.onReschedule,
  });
  final Map<String, dynamic> event;
  final Color color;
  final VoidCallback onOpen;
  final VoidCallback onLocation;
  final VoidCallback onReschedule;
  @override
  Widget build(BuildContext context) {
    final customer = Map<String, dynamic>.from(event['customer'] as Map),
        employee = Map<String, dynamic>.from(event['employee'] as Map);
    final locationSaved =
        customer['latitude'] != null && customer['longitude'] != null;
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: [
            Row(
              children: [
                CircleAvatar(
                  backgroundColor: color.withValues(alpha: .12),
                  foregroundColor: color,
                  child: Icon(
                    event['type'] == 'RENT'
                        ? Icons.payments
                        : event['type'] == 'COMPLAINT'
                        ? Icons.report_problem
                        : Icons.home_repair_service,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        event['title'].toString(),
                        style: const TextStyle(
                          fontWeight: FontWeight.w800,
                          fontSize: 16,
                        ),
                      ),
                      Text(
                        '${customer['name']} • ${event['status']}',
                        style: const TextStyle(color: Colors.black54),
                      ),
                    ],
                  ),
                ),
                if (event['amount'] != null)
                  Text(
                    '₹${event['amount']}',
                    style: TextStyle(color: color, fontWeight: FontWeight.w800),
                  ),
              ],
            ),
            const Divider(height: 22),
            Row(
              children: [
                const Icon(Icons.engineering, size: 18),
                const SizedBox(width: 6),
                Expanded(child: Text(employee['name'].toString())),
                if (event['rescheduled'] == true)
                  const Chip(
                    label: Text('Rescheduled'),
                    visualDensity: VisualDensity.compact,
                  ),
              ],
            ),
            Row(
              children: [
                const Icon(Icons.location_on_outlined, size: 18),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    '${customer['address']}, ${customer['city']}',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                TextButton.icon(
                  onPressed: onReschedule,
                  icon: const Icon(Icons.event_repeat),
                  label: const Text('Forward'),
                ),
              ],
            ),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: locationSaved ? null : onLocation,
                icon: Icon(
                  locationSaved
                      ? Icons.location_on
                      : Icons.add_location_alt_outlined,
                ),
                label: Text(
                  locationSaved ? 'Location Saved' : 'Save Customer Location',
                ),
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: onOpen,
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
    );
  }
}

class _MessageCard extends StatelessWidget {
  const _MessageCard({
    required this.icon,
    required this.text,
    required this.color,
  });
  final IconData icon;
  final String text;
  final Color color;
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(24),
      child: Row(
        children: [
          Icon(icon, color: color),
          const SizedBox(width: 12),
          Expanded(child: Text(text)),
        ],
      ),
    ),
  );
}
