import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/calling_desk_service.dart';

class CallingDeskScreen extends StatefulWidget {
  const CallingDeskScreen({super.key});
  @override
  State<CallingDeskScreen> createState() => _CallingDeskScreenState();
}

class _CallingDeskScreenState extends State<CallingDeskScreen>
    with SingleTickerProviderStateMixin {
  final _service = CallingDeskService();
  final _search = TextEditingController();
  late final TabController _tabs;
  List<Map<String, dynamic>> _leads = [], _customers = [], _history = [];
  Map<String, dynamic> _summary = {};
  final Map<int, DateTime> _started = {};
  bool _loading = true;
  String? _error;
  String _outcome = 'ALL';

  static const outcomes = <String, String>{
    'ALL': 'All outcomes', 'PENDING': 'Pending', 'NO_ANSWER': 'No answer',
    'CALLBACK': 'Call back', 'INTERESTED': 'Interested',
    'NOT_INTERESTED': 'Not interested', 'WRONG_NUMBER': 'Wrong number',
    'CONVERTED': 'Converted',
  };

  @override
  void initState() { super.initState(); _tabs = TabController(length: 3, vsync: this); _load(); }
  @override
  void dispose() { _tabs.dispose(); _search.dispose(); super.dispose(); }

  List<Map<String, dynamic>> _maps(dynamic value) => (value as List? ?? const [])
      .map((e) => Map<String, dynamic>.from(e as Map)).toList();

  Future<void> _load() async {
    setState(() { _loading = true; _error = null; });
    try {
      final data = await _service.list(query: _search.text, outcome: _outcome);
      if (!mounted) return;
      setState(() {
        _leads = _maps(data['leads']); _customers = _maps(data['customers']);
        _history = _maps(data['activities']);
        _summary = Map<String, dynamic>.from(data['summary'] as Map? ?? const {});
      });
    } catch (e) { if (mounted) setState(() => _error = e.toString().replaceFirst('Exception: ', '')); }
    finally { if (mounted) setState(() => _loading = false); }
  }

  void _show(String text) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));

  Future<void> _call(Map<String, dynamic> lead) async {
    final id = (lead['id'] as num).toInt();
    _started[id] = DateTime.now();
    if (!await launchUrl(Uri(scheme: 'tel', path: '${lead['phone']}'), mode: LaunchMode.externalApplication) && mounted) {
      _started.remove(id); _show('Unable to open phone dialer');
    }
  }

  Future<void> _callCustomer(Map<String, dynamic> customer) async {
    try {
      final response = await _service.createLead(customerId: (customer['id'] as num).toInt());
      await _call(Map<String, dynamic>.from(response['lead'] as Map));
      if (mounted) { _tabs.animateTo(0); await _load(); }
    } catch (e) { if (mounted) _show(e.toString().replaceFirst('Exception: ', '')); }
  }

  Future<void> _newLead() async {
    final name = TextEditingController(), phone = TextEditingController();
    final city = TextEditingController(), interest = TextEditingController(), notes = TextEditingController();
    String type = 'PURCHASE', priority = 'NORMAL';
    final save = await showDialog<bool>(context: context, builder: (context) => StatefulBuilder(
      builder: (context, local) => AlertDialog(
        title: const Text('Add New Lead'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: name, decoration: const InputDecoration(labelText: 'Customer name *')),
          TextField(controller: phone, keyboardType: TextInputType.phone, maxLength: 10, decoration: const InputDecoration(labelText: 'Mobile number *')),
          TextField(controller: city, decoration: const InputDecoration(labelText: 'City / Area')),
          DropdownButtonFormField<String>(initialValue: type, decoration: const InputDecoration(labelText: 'Requirement'), items: const [
            DropdownMenuItem(value: 'PURCHASE', child: Text('RO Purchase')), DropdownMenuItem(value: 'RENTAL', child: Text('RO Rental')),
            DropdownMenuItem(value: 'SERVICE', child: Text('RO Service')), DropdownMenuItem(value: 'AMC', child: Text('AMC Plan')),
            DropdownMenuItem(value: 'COMPLAINT', child: Text('Complaint')), DropdownMenuItem(value: 'REFERRAL', child: Text('Referral enquiry')),
          ], onChanged: (v) => type = v ?? type),
          DropdownButtonFormField<String>(initialValue: priority, decoration: const InputDecoration(labelText: 'Priority'), items: const [
            DropdownMenuItem(value: 'LOW', child: Text('Low')), DropdownMenuItem(value: 'NORMAL', child: Text('Normal')),
            DropdownMenuItem(value: 'HIGH', child: Text('High')), DropdownMenuItem(value: 'URGENT', child: Text('Urgent')),
          ], onChanged: (v) => local(() => priority = v ?? priority)),
          TextField(controller: interest, decoration: const InputDecoration(labelText: 'Product / plan interest')),
          TextField(controller: notes, maxLines: 3, decoration: const InputDecoration(labelText: 'Opening notes')),
        ])),
        actions: [TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')), FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('CREATE LEAD'))],
      ),
    )) ?? false;
    if (save) {
      try {
        await _service.createLead(customerName: name.text, phone: phone.text, city: city.text, requestType: type, priority: priority, planName: interest.text, notes: notes.text);
        if (mounted) { _show('Lead created and assigned'); _tabs.animateTo(0); await _load(); }
      } catch (e) { if (mounted) _show(e.toString().replaceFirst('Exception: ', '')); }
    }
    name.dispose(); phone.dispose(); city.dispose(); interest.dispose(); notes.dispose();
  }

  Future<void> _saveCall(Map<String, dynamic> lead) async {
    String result = '${lead['last_call_outcome'] ?? 'PENDING'}';
    final note = TextEditingController(text: '${lead['call_notes'] ?? ''}');
    DateTime? followUp;
    final save = await showDialog<bool>(context: context, builder: (context) => StatefulBuilder(
      builder: (context, local) => AlertDialog(
        title: Text('${lead['customer_name']} • Call result'),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          DropdownButtonFormField<String>(initialValue: result, isExpanded: true, decoration: const InputDecoration(labelText: 'Outcome *'), items: outcomes.entries.where((e) => e.key != 'ALL').map((e) => DropdownMenuItem(value: e.key, child: Text(e.value))).toList(), onChanged: (v) => local(() => result = v ?? result)),
          TextField(controller: note, maxLines: 4, decoration: const InputDecoration(labelText: 'Conversation notes', hintText: 'Need, objection, promise and next action...')),
          const SizedBox(height: 10), OutlinedButton.icon(onPressed: () async {
            final day = await showDatePicker(context: context, initialDate: DateTime.now().add(const Duration(days: 1)), firstDate: DateTime.now(), lastDate: DateTime.now().add(const Duration(days: 365)));
            if (day == null || !context.mounted) return;
            final time = await showTimePicker(context: context, initialTime: const TimeOfDay(hour: 11, minute: 0));
            if (time != null) local(() => followUp = DateTime(day.year, day.month, day.day, time.hour, time.minute));
          }, icon: const Icon(Icons.schedule), label: Text(followUp == null ? 'Schedule follow-up' : '${followUp!.day}/${followUp!.month} ${TimeOfDay.fromDateTime(followUp!).format(context)}')),
          if (result == 'CALLBACK' && followUp == null) const Text('Callback should include follow-up time.', style: TextStyle(color: Colors.orange)),
        ])),
        actions: [TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('CANCEL')), FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('SAVE CALL'))],
      ),
    )) ?? false;
    if (save) {
      try {
        final id = (lead['id'] as num).toInt(), started = _started.remove((lead['id'] as num).toInt());
        await _service.update(id, outcome: result, note: note.text, nextFollowUp: followUp, durationSeconds: started == null ? 0 : DateTime.now().difference(started).inSeconds);
        if (mounted) { _show('Call saved in history'); await _load(); }
      } catch (e) { if (mounted) _show(e.toString().replaceFirst('Exception: ', '')); }
    }
    note.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Caller Command Center'), bottom: TabBar(controller: _tabs, tabs: const [Tab(icon: Icon(Icons.filter_alt_outlined), text: 'Pipeline'), Tab(icon: Icon(Icons.people_outline), text: 'Customers'), Tab(icon: Icon(Icons.history), text: 'History')])),
    floatingActionButton: FloatingActionButton.extended(onPressed: _newLead, icon: const Icon(Icons.person_add_alt_1), label: const Text('NEW LEAD')),
    body: _loading ? const Center(child: CircularProgressIndicator()) : _error != null
      ? Center(child: Column(mainAxisSize: MainAxisSize.min, children: [Text(_error!), FilledButton(onPressed: _load, child: const Text('RETRY'))]))
      : Column(children: [_Header(summary: _summary, search: _search, outcome: _outcome, onSearch: _load, onOutcome: (v) { setState(() => _outcome = v); _load(); }), Expanded(child: TabBarView(controller: _tabs, children: [_pipeline(), _customerList(), _historyList()]))]),
  );

  Widget _pipeline() => RefreshIndicator(onRefresh: _load, child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 90), children: [
    if (_leads.isEmpty) const _Empty('No leads in this filter'),
    ..._leads.map((lead) => Card(child: Padding(padding: const EdgeInsets.all(14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [Expanded(child: Text('${lead['customer_name']}', style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900))), Chip(label: Text('${lead['priority']}'))]),
      Text('${lead['phone']} • ${lead['city']} • ${lead['request_type']}'),
      Text('${lead['record_type'] == 'CUSTOMER' ? 'Existing customer' : 'New lead'} • ${outcomes[lead['last_call_outcome']]} • ${lead['call_count']} calls'),
      if ('${lead['plan_name'] ?? ''}'.isNotEmpty) Text('Interest: ${lead['plan_name']}'),
      if ('${lead['next_follow_up_at'] ?? ''}'.isNotEmpty) Text('Follow-up: ${lead['next_follow_up_at']}', style: const TextStyle(color: Colors.orange, fontWeight: FontWeight.w700)),
      if ('${lead['call_notes'] ?? ''}'.isNotEmpty) Text('Last note: ${lead['call_notes']}'),
      const SizedBox(height: 10), Row(children: [Expanded(child: FilledButton.icon(onPressed: () => _call(lead), icon: const Icon(Icons.call), label: const Text('CALL'))), const SizedBox(width: 8), Expanded(child: OutlinedButton.icon(onPressed: () => _saveCall(lead), icon: const Icon(Icons.fact_check_outlined), label: const Text('SAVE RESULT')))]),
    ])))),
  ]));

  Widget _customerList() => RefreshIndicator(onRefresh: _load, child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 90), children: [
    Card(color: Colors.blue.withValues(alpha: .07), child: Padding(padding: const EdgeInsets.all(12), child: Text('${_customers.length} customers shown • Search by name, phone, card or city'))),
    ..._customers.map((c) => Card(child: ListTile(leading: const CircleAvatar(child: Icon(Icons.person)), title: Text('${c['name']}', style: const TextStyle(fontWeight: FontWeight.w800)), subtitle: Text('${c['customer_id']} • ${c['phone']}\n${c['city']} • ${c['ro_model']} • Calls: ${c['call_count']}'), isThreeLine: true, trailing: IconButton.filled(onPressed: () => _callCustomer(c), icon: const Icon(Icons.call))))),
  ]));

  Widget _historyList() => RefreshIndicator(onRefresh: _load, child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 90), children: [
    if (_history.isEmpty) const _Empty('No call history yet'),
    ..._history.map((a) => Card(child: ListTile(leading: CircleAvatar(child: Icon(a['outcome'] == 'CONVERTED' ? Icons.verified : Icons.call_outlined)), title: Text('${a['name']} • ${outcomes[a['outcome']]}', style: const TextStyle(fontWeight: FontWeight.w800)), subtitle: Text('${a['phone']} • ${a['called_at']}\n${'${a['note'] ?? ''}'.isEmpty ? 'No note recorded' : a['note']}'), isThreeLine: true))),
  ]));
}

class _Header extends StatelessWidget {
  const _Header({required this.summary, required this.search, required this.outcome, required this.onSearch, required this.onOutcome});
  final Map<String, dynamic> summary; final TextEditingController search; final String outcome; final VoidCallback onSearch; final ValueChanged<String> onOutcome;
  @override Widget build(BuildContext context) => Padding(padding: const EdgeInsets.fromLTRB(12, 8, 12, 4), child: Column(children: [
    SingleChildScrollView(scrollDirection: Axis.horizontal, child: Row(children: [_Kpi('Calls today', summary['calls_today'], Icons.call, Colors.blue), _Kpi('Due', summary['due'], Icons.alarm, Colors.orange), _Kpi('Interested', summary['interested'], Icons.thumb_up, Colors.teal), _Kpi('Converted', summary['converted'], Icons.verified, Colors.green)])),
    Row(children: [Expanded(child: TextField(controller: search, textInputAction: TextInputAction.search, onSubmitted: (_) => onSearch(), decoration: InputDecoration(isDense: true, hintText: 'Name, phone, card, city...', prefixIcon: const Icon(Icons.search), suffixIcon: IconButton(onPressed: onSearch, icon: const Icon(Icons.arrow_forward))))), PopupMenuButton<String>(initialValue: outcome, onSelected: onOutcome, itemBuilder: (_) => _CallingDeskScreenState.outcomes.entries.map((e) => PopupMenuItem(value: e.key, child: Text(e.value))).toList(), icon: const Icon(Icons.tune))]),
  ]));
}

class _Kpi extends StatelessWidget {
  const _Kpi(this.label, this.value, this.icon, this.color); final String label; final dynamic value; final IconData icon; final Color color;
  @override Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7), child: Row(children: [Icon(icon, color: color), const SizedBox(width: 6), Column(children: [Text('${value ?? 0}', style: const TextStyle(fontWeight: FontWeight.w900)), Text(label, style: const TextStyle(fontSize: 10))])])));
}

class _Empty extends StatelessWidget {
  const _Empty(this.text); final String text;
  @override Widget build(BuildContext context) => Card(child: Padding(padding: const EdgeInsets.all(28), child: Center(child: Text(text))));
}
