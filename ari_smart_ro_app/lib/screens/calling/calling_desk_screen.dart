import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/calling_desk_service.dart';

class CallingDeskScreen extends StatefulWidget {
  const CallingDeskScreen({super.key});

  @override
  State<CallingDeskScreen> createState() => _CallingDeskScreenState();
}

class _CallingDeskScreenState extends State<CallingDeskScreen> {
  final _service = CallingDeskService();
  final _search = TextEditingController();
  List<Map<String, dynamic>> _leads = const [];
  bool _loading = true;
  String? _error;
  String _outcome = 'ALL';
  int _due = 0;

  static const outcomes = <String, String>{
    'ALL': 'All outcomes',
    'PENDING': 'Pending',
    'NO_ANSWER': 'No answer',
    'CALLBACK': 'Call back',
    'INTERESTED': 'Interested',
    'NOT_INTERESTED': 'Not interested',
    'WRONG_NUMBER': 'Wrong number',
    'CONVERTED': 'Converted',
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await _service.list(query: _search.text, outcome: _outcome);
      if (!mounted) return;
      setState(() {
        _leads = (data['leads'] as List? ?? const [])
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
        _due = (data['due_follow_ups'] as num?)?.toInt() ?? 0;
      });
    } catch (e) {
      if (mounted) setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _call(String phone) async {
    final uri = Uri(scheme: 'tel', path: phone);
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication) && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Unable to open phone dialer')));
    }
  }

  Future<void> _update(Map<String, dynamic> lead) async {
    String result = (lead['last_call_outcome'] ?? 'PENDING').toString();
    final note = TextEditingController(text: (lead['call_notes'] ?? '').toString());
    DateTime? followUp;
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setLocal) => AlertDialog(
          title: Text(lead['customer_name']?.toString() ?? 'Lead'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  initialValue: result,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Call outcome'),
                  items: outcomes.entries.where((e) => e.key != 'ALL')
                      .map((e) => DropdownMenuItem(value: e.key, child: Text(e.value)))
                      .toList(),
                  onChanged: (v) => result = v ?? 'PENDING',
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: note,
                  maxLines: 3,
                  decoration: const InputDecoration(labelText: 'Call notes'),
                ),
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: OutlinedButton.icon(
                    onPressed: () async {
                      final day = await showDatePicker(
                        context: context,
                        initialDate: DateTime.now().add(const Duration(days: 1)),
                        firstDate: DateTime.now(),
                        lastDate: DateTime.now().add(const Duration(days: 365)),
                      );
                      if (day == null || !context.mounted) return;
                      final time = await showTimePicker(
                        context: context,
                        initialTime: const TimeOfDay(hour: 11, minute: 0),
                      );
                      if (time != null) {
                        setLocal(() => followUp = DateTime(day.year, day.month, day.day, time.hour, time.minute));
                      }
                    },
                    icon: const Icon(Icons.schedule),
                    label: Text(followUp == null ? 'Set follow-up' : 'Follow-up: ${followUp!.day}/${followUp!.month} ${TimeOfDay.fromDateTime(followUp!).format(context)}'),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('SAVE')),
          ],
        ),
      ),
    ) ?? false;
    if (!ok) {
      note.dispose();
      return;
    }
    try {
      await _service.update((lead['id'] as num).toInt(), outcome: result, note: note.text, nextFollowUp: followUp);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Call follow-up saved')));
        await _load();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))));
    } finally {
      note.dispose();
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Calling Desk')),
    body: _loading
        ? const Center(child: CircularProgressIndicator())
        : _error != null
            ? Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text(_error!, textAlign: TextAlign.center),
                const SizedBox(height: 12),
                FilledButton(onPressed: _load, child: const Text('RETRY')),
              ]))
            : RefreshIndicator(
                onRefresh: _load,
                child: ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Card(
                      child: ListTile(
                        leading: const CircleAvatar(child: Icon(Icons.schedule)),
                        title: Text('$_due follow-ups due'),
                        subtitle: Text('${_leads.length} leads shown'),
                      ),
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _search,
                      textInputAction: TextInputAction.search,
                      onSubmitted: (_) => _load(),
                      decoration: InputDecoration(
                        hintText: 'Search name, phone, city, request...',
                        prefixIcon: const Icon(Icons.search),
                        suffixIcon: IconButton(onPressed: _load, icon: const Icon(Icons.arrow_forward)),
                      ),
                    ),
                    const SizedBox(height: 10),
                    DropdownButtonFormField<String>(
                      initialValue: _outcome,
                      isExpanded: true,
                      decoration: const InputDecoration(labelText: 'Outcome filter'),
                      items: outcomes.entries.map((e) => DropdownMenuItem(value: e.key, child: Text(e.value))).toList(),
                      onChanged: (v) {
                        setState(() => _outcome = v ?? 'ALL');
                        _load();
                      },
                    ),
                    const SizedBox(height: 12),
                    if (_leads.isEmpty)
                      const Card(child: Padding(padding: EdgeInsets.all(24), child: Center(child: Text('No leads found')))),
                    ..._leads.map((lead) => Card(
                      child: Padding(
                        padding: const EdgeInsets.all(14),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(lead['customer_name']?.toString() ?? '', style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w800)),
                            Text('${lead['phone']} • ${lead['city']} • ${lead['request_type']}'),
                            const SizedBox(height: 6),
                            Text('Outcome: ${outcomes[lead['last_call_outcome']] ?? lead['last_call_outcome']}'),
                            if ((lead['plan_name'] ?? '').toString().isNotEmpty) Text('Interest: ${lead['plan_name']}'),
                            if ((lead['call_notes'] ?? '').toString().isNotEmpty) Text('Notes: ${lead['call_notes']}'),
                            const SizedBox(height: 10),
                            Row(children: [
                              Expanded(child: FilledButton.icon(
                                onPressed: () => _call(lead['phone'].toString()),
                                icon: const Icon(Icons.call),
                                label: const Text('CALL'),
                              )),
                              const SizedBox(width: 8),
                              Expanded(child: OutlinedButton.icon(
                                onPressed: () => _update(lead),
                                icon: const Icon(Icons.edit_note),
                                label: const Text('UPDATE'),
                              )),
                            ]),
                          ],
                        ),
                      ),
                    )),
                  ],
                ),
              ),
  );
}
