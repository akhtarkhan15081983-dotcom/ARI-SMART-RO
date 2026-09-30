import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:timezone/data/latest.dart' as tz;
import 'package:timezone/timezone.dart' as tz;

import '../models/complaint_model.dart';
import '../services/api_service.dart';
import '../services/complaint_service.dart';
import '../services/customer_service.dart';
import '../services/ro_alarm_service.dart';

class ROFilterAlarmPolicy {
  const ROFilterAlarmPolicy._();

  static String complaintMarker(int alarmId) => '[RO-ALARM:$alarmId]';

  static bool complaintFieldsStopReminder({
    required String complaintType,
    required String status,
    required String description,
    required int alarmId,
  }) {
    if (status.trim().toUpperCase() == 'CANCELLED') return false;
    return complaintType.trim().toUpperCase() == 'FILTER_PROBLEM' &&
        description.contains(complaintMarker(alarmId));
  }

  static bool complaintStopsReminder(
    ComplaintModel complaint,
    int alarmId,
  ) =>
      complaintFieldsStopReminder(
        complaintType: complaint.complaintType,
        status: complaint.status,
        description: complaint.description,
        alarmId: alarmId,
      );

  static bool isActiveFilterAlarm(Map<String, dynamic> alarm) {
    final type = (alarm['alarm_type'] ?? '').toString().toUpperCase();
    final status = (alarm['status'] ?? '').toString().toUpperCase();
    return type == 'FILTER_DUE' && status != 'RESOLVED';
  }
}

class ROFilterAlarmGuard extends StatefulWidget {
  const ROFilterAlarmGuard({required this.child, super.key});

  final Widget child;

  @override
  State<ROFilterAlarmGuard> createState() => _ROFilterAlarmGuardState();
}

class _ROFilterAlarmGuardState extends State<ROFilterAlarmGuard>
    with WidgetsBindingObserver {
  static const Duration _refreshEvery = Duration(minutes: 1);

  final ROAlarmService _alarmService = const ROAlarmService();
  final ComplaintService _complaintService = ComplaintService();
  final CustomerService _customerService = CustomerService();
  final _reminders = const _ROFilterAlarmReminderService();

  Timer? _timer;
  Map<String, dynamic>? _warningAlarm;
  Set<int> _dismissedThisSession = <int>{};
  bool _syncing = false;
  bool _raisingComplaint = false;
  String? _actionError;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _sync());
    _timer = Timer.periodic(_refreshEvery, (_) => _sync());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _dismissedThisSession = <int>{};
      _sync();
    }
  }

  Future<void> _sync() async {
    if (_syncing) return;
    _syncing = true;
    try {
      final role = (await ApiService.getRole() ?? '')
          .trim()
          .toUpperCase()
          .replaceAll('ROLE_', '');
      if (role != 'CUSTOMER') {
        if (mounted && _warningAlarm != null) {
          setState(() => _warningAlarm = null);
        }
        return;
      }

      final results = await Future.wait<dynamic>([
        _alarmService.fetchAlarms(),
        _complaintService.getComplaints(),
      ]);
      final alarms = (results[0] as List<Map<String, dynamic>>)
          .where(ROFilterAlarmPolicy.isActiveFilterAlarm)
          .toList();
      final complaints = results[1] as List<ComplaintModel>;

      final active = <Map<String, dynamic>>[];
      for (final alarm in alarms) {
        final id = (alarm['id'] as num?)?.toInt();
        if (id == null) continue;
        final hasComplaint = complaints.any(
          (complaint) =>
              ROFilterAlarmPolicy.complaintStopsReminder(complaint, id),
        );
        if (!hasComplaint) active.add(alarm);
      }

      await _reminders.sync(active);

      Map<String, dynamic>? next;
      for (final alarm in active) {
        final id = (alarm['id'] as num?)?.toInt();
        if (id != null && !_dismissedThisSession.contains(id)) {
          next = alarm;
          break;
        }
      }
      if (!mounted) return;
      setState(() {
        _warningAlarm = next;
        _actionError = null;
      });
    } catch (_) {
      // Alarm monitoring must never block login/dashboard when offline or when
      // the server is temporarily unavailable. The next sync retries.
    } finally {
      _syncing = false;
    }
  }

  Future<void> _raiseComplaint() async {
    final alarm = _warningAlarm;
    final alarmId = (alarm?['id'] as num?)?.toInt();
    if (alarm == null || alarmId == null || _raisingComplaint) return;

    setState(() {
      _raisingComplaint = true;
      _actionError = null;
    });
    try {
      final customers = await _customerService.getCustomers();
      if (customers.isEmpty) {
        throw Exception('No active customer account is linked to this login.');
      }
      final assetId = (alarm['asset_id'] ?? 'your RO').toString();
      final dueDate = (alarm['due_date'] ?? '').toString().trim();
      final marker = ROFilterAlarmPolicy.complaintMarker(alarmId);
      final description = <String>[
        marker,
        'Automatic filter-change alarm for $assetId.',
        if (dueDate.isNotEmpty) 'Filter due date: $dueDate.',
        'Please inspect and replace the required filters.',
      ].join(' ');

      await _complaintService.createComplaint(
        customer: customers.first.id,
        complaintType: 'FILTER_PROBLEM',
        description: description,
        priority: 'NORMAL',
      );
      await _reminders.cancelAlarm(alarmId);
      _dismissedThisSession.add(alarmId);
      if (!mounted) return;
      setState(() => _warningAlarm = null);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'Filter-change complaint registered. 3-hour alarm reminders stopped.',
          ),
        ),
      );
      unawaited(_sync());
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _actionError = error
            .toString()
            .replaceFirst('Exception: ', '')
            .trim();
      });
    } finally {
      if (mounted) setState(() => _raisingComplaint = false);
    }
  }

  void _dismissWarning() {
    final id = (_warningAlarm?['id'] as num?)?.toInt();
    if (id != null) _dismissedThisSession.add(id);
    setState(() {
      _warningAlarm = null;
      _actionError = null;
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final alarm = _warningAlarm;
    return Stack(
      fit: StackFit.expand,
      children: [
        widget.child,
        if (alarm != null)
          Material(
            color: const Color(0xFFE00000),
            child: SafeArea(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(24),
                child: ConstrainedBox(
                  constraints: BoxConstraints(
                    minHeight: MediaQuery.sizeOf(context).height - 48,
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.warning_amber_rounded,
                        size: 88,
                        color: Colors.white,
                      ),
                      const SizedBox(height: 18),
                      const Text(
                        'FILTER CHANGE ALERT',
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 30,
                          fontWeight: FontWeight.w900,
                          letterSpacing: 1.2,
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        (alarm['title'] ?? 'RO filter change is due.').toString(),
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        _warningDetails(alarm),
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 17,
                          height: 1.35,
                        ),
                      ),
                      const SizedBox(height: 18),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: Colors.black.withValues(alpha: .22),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: const Text(
                          'Mobile reminder sound repeats about every 3 hours until a filter-change complaint is registered.',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                      if (_actionError != null) ...[
                        const SizedBox(height: 12),
                        Text(
                          _actionError!,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ],
                      const SizedBox(height: 24),
                      SizedBox(
                        width: double.infinity,
                        height: 54,
                        child: FilledButton.icon(
                          style: FilledButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: const Color(0xFFB00000),
                          ),
                          onPressed: _raisingComplaint ? null : _raiseComplaint,
                          icon: _raisingComplaint
                              ? const SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.build_circle_outlined),
                          label: Text(
                            _raisingComplaint
                                ? 'REGISTERING...'
                                : 'RAISE FILTER COMPLAINT',
                            style: const TextStyle(fontWeight: FontWeight.w900),
                          ),
                        ),
                      ),
                      const SizedBox(height: 10),
                      TextButton(
                        onPressed: _raisingComplaint ? null : _dismissWarning,
                        child: const Text(
                          'CONTINUE TO APP',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }

  String _warningDetails(Map<String, dynamic> alarm) {
    final asset = (alarm['asset_id'] ?? '').toString().trim();
    final due = (alarm['due_date'] ?? '').toString().trim();
    final message = (alarm['message'] ?? '').toString().trim();
    return <String>[
      if (asset.isNotEmpty) 'RO: $asset',
      if (due.isNotEmpty) 'Due: $due',
      if (message.isNotEmpty) message,
    ].join('\n');
  }
}

class _ROFilterAlarmReminderService {
  const _ROFilterAlarmReminderService();

  static const FlutterSecureStorage _storage = FlutterSecureStorage();
  static final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();
  static Future<void>? _initialization;
  static const String _scheduledKey = 'ro_filter_alarm_scheduled_ids_v2';
  static const int _slots = 8; // Eight daily slots maintain a 3-hour cadence.

  Future<void> sync(List<Map<String, dynamic>> active) async {
    if (!_isAndroid) return;
    await _initialize(requestPermission: true);

    final activeIds = active
        .map((alarm) => (alarm['id'] as num?)?.toInt())
        .whereType<int>()
        .toSet();
    final previous = await _readScheduledIds();

    for (final stale in previous.difference(activeIds)) {
      await cancelAlarm(stale);
    }

    final newlyActive = activeIds.difference(previous);
    for (final alarm in active) {
      final alarmId = (alarm['id'] as num?)?.toInt();
      if (alarmId == null || !newlyActive.contains(alarmId)) continue;
      await _showImmediate(alarmId, alarm);
      await _scheduleThreeHourly(alarmId, alarm);
    }

    await _storage.write(
      key: _scheduledKey,
      value: activeIds.join(','),
    );
  }

  Future<void> cancelAlarm(int alarmId) async {
    if (!_isAndroid) return;
    await _initialize();
    await _plugin.cancel(_notificationId(alarmId, 99));
    for (var slot = 0; slot < _slots; slot++) {
      await _plugin.cancel(_notificationId(alarmId, slot));
    }

    final ids = await _readScheduledIds();
    ids.remove(alarmId);
    await _storage.write(key: _scheduledKey, value: ids.join(','));
  }

  Future<void> _showImmediate(
    int alarmId,
    Map<String, dynamic> alarm,
  ) async {
    await _plugin.show(
      _notificationId(alarmId, 99),
      'FILTER CHANGE ALERT',
      _notificationBody(alarm),
      _details,
      payload: 'ro-filter-alarm:$alarmId',
    );
  }

  Future<void> _scheduleThreeHourly(
    int alarmId,
    Map<String, dynamic> alarm,
  ) async {
    final now = tz.TZDateTime.now(tz.local);
    for (var slot = 0; slot < _slots; slot++) {
      final when = now.add(Duration(hours: 3 * (slot + 1)));
      await _plugin.cancel(_notificationId(alarmId, slot));
      await _plugin.zonedSchedule(
        _notificationId(alarmId, slot),
        'FILTER CHANGE ALERT',
        _notificationBody(alarm),
        when,
        _details,
        androidScheduleMode: AndroidScheduleMode.inexactAllowWhileIdle,
        payload: 'ro-filter-alarm:$alarmId',
        matchDateTimeComponents: DateTimeComponents.time,
      );
    }
  }

  Future<Set<int>> _readScheduledIds() async {
    final raw = await _storage.read(key: _scheduledKey) ?? '';
    return raw
        .split(',')
        .map((part) => int.tryParse(part.trim()))
        .whereType<int>()
        .toSet();
  }

  Future<void> _initialize({bool requestPermission = false}) async {
    if (!_isAndroid) return;
    final existing = _initialization;
    if (existing != null) {
      await existing;
    } else {
      final operation = _doInitialize();
      _initialization = operation;
      try {
        await operation;
      } catch (_) {
        if (identical(_initialization, operation)) _initialization = null;
        rethrow;
      }
    }
    if (requestPermission) {
      await _plugin
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.requestNotificationsPermission();
    }
  }

  Future<void> _doInitialize() async {
    tz.initializeTimeZones();
    tz.setLocalLocation(tz.getLocation('Asia/Kolkata'));
    const android = AndroidInitializationSettings('@mipmap/ic_launcher');
    await _plugin.initialize(
      const InitializationSettings(android: android),
    );
  }

  bool get _isAndroid =>
      !kIsWeb && defaultTargetPlatform == TargetPlatform.android;

  int _notificationId(int alarmId, int slot) =>
      500000 + ((alarmId % 4000) * 100) + slot;

  String _notificationBody(Map<String, dynamic> alarm) {
    final asset = (alarm['asset_id'] ?? 'your RO').toString();
    return '$asset filter change is due. Raise a filter complaint to stop 3-hour reminders.';
  }

  NotificationDetails get _details => const NotificationDetails(
        android: AndroidNotificationDetails(
          'ro_filter_alarm',
          'RO filter change alarms',
          channelDescription:
              'Repeating filter-change reminders until a complaint is registered.',
          importance: Importance.max,
          priority: Priority.max,
          playSound: true,
          enableVibration: true,
          category: AndroidNotificationCategory.alarm,
          ticker: 'FILTER CHANGE ALERT',
        ),
      );
}
