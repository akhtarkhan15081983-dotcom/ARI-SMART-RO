import 'package:flutter/material.dart';

import '../../services/complaint_assistant_service.dart';

class ComplaintAssistantScreen extends StatefulWidget {
  const ComplaintAssistantScreen({super.key});

  @override
  State<ComplaintAssistantScreen> createState() => _ComplaintAssistantScreenState();
}

class _ComplaintAssistantScreenState extends State<ComplaintAssistantScreen> {
  final ComplaintAssistantService _service = const ComplaintAssistantService();
  final TextEditingController _descriptionController = TextEditingController();

  late Future<List<Map<String, dynamic>>> _symptomsFuture;
  Map<String, dynamic>? _guidanceData;
  String? _selectedSymptom;
  bool _loadingGuidance = false;
  bool _submitting = false;

  @override
  void initState() {
    super.initState();
    _symptomsFuture = _service.symptoms();
  }

  Future<void> _select(String code) async {
    if (_loadingGuidance || _submitting) return;
    setState(() {
      _selectedSymptom = code;
      _loadingGuidance = true;
      _guidanceData = null;
    });
    try {
      final data = await _service.guidance(code);
      if (!mounted) return;
      setState(() => _guidanceData = data);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.toString().replaceFirst('Exception: ', ''))),
      );
    } finally {
      if (mounted) setState(() => _loadingGuidance = false);
    }
  }

  Future<void> _raise() async {
    final symptom = _selectedSymptom;
    if (symptom == null || _submitting) return;
    setState(() => _submitting = true);
    try {
      final result = await _service.raiseComplaint(
        symptom: symptom,
        description: _descriptionController.text,
      );
      if (!mounted) return;
      final complaint = Map<String, dynamic>.from(
        result['complaint'] as Map? ?? const {},
      );
      await showDialog<void>(
        context: context,
        builder: (context) => AlertDialog(
          icon: const Icon(Icons.check_circle, color: Colors.green, size: 48),
          title: const Text('Complaint Raised'),
          content: Text(
            'Complaint ${complaint['complaint_id'] ?? ''} has been created. ARI will use the attached RO/service context for diagnosis.',
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('OK'),
            ),
          ],
        ),
      );
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(error.toString().replaceFirst('Exception: ', ''))),
      );
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final guidance = Map<String, dynamic>.from(
      _guidanceData?['guidance'] as Map? ?? const {},
    );
    final checks = guidance['checks'] as List<dynamic>? ?? const [];
    final contextData = Map<String, dynamic>.from(
      _guidanceData?['complaint_context'] as Map? ?? const {},
    );

    return Scaffold(
      appBar: AppBar(title: const Text('ARI Care Assistant')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Tell us what you are seeing',
            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 6),
          const Text(
            'ARI Care gives only safe external checks. Technical diagnosis and internal repair remain the engineer’s responsibility.',
          ),
          const SizedBox(height: 18),
          FutureBuilder<List<Map<String, dynamic>>>(
            future: _symptomsFuture,
            builder: (context, snapshot) {
              if (snapshot.connectionState != ConnectionState.done) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snapshot.hasError) {
                return Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      children: [
                        const Text('Unable to load symptom options.'),
                        const SizedBox(height: 8),
                        OutlinedButton.icon(
                          onPressed: () => setState(
                            () => _symptomsFuture = _service.symptoms(),
                          ),
                          icon: const Icon(Icons.refresh),
                          label: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                );
              }
              final symptoms = snapshot.data ?? const <Map<String, dynamic>>[];
              return Wrap(
                spacing: 8,
                runSpacing: 8,
                children: symptoms.map((item) {
                  final code = (item['code'] ?? '').toString();
                  final label = (item['label'] ?? code).toString();
                  return ChoiceChip(
                    label: Text(label),
                    selected: _selectedSymptom == code,
                    onSelected: (_) => _select(code),
                  );
                }).toList(),
              );
            },
          ),
          if (_loadingGuidance) ...[
            const SizedBox(height: 18),
            const LinearProgressIndicator(),
          ],
          if (guidance.isNotEmpty) ...[
            const SizedBox(height: 20),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.health_and_safety_outlined),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            (guidance['label'] ?? 'Safe checks').toString(),
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.w900,
                            ),
                          ),
                        ),
                        if ((guidance['priority'] ?? '') == 'EMERGENCY')
                          const Chip(label: Text('EMERGENCY')),
                      ],
                    ),
                    const SizedBox(height: 12),
                    ...checks.map(
                      (item) => Padding(
                        padding: const EdgeInsets.symmetric(vertical: 5),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Icon(Icons.check_circle_outline, size: 19),
                            const SizedBox(width: 8),
                            Expanded(child: Text(item.toString())),
                          ],
                        ),
                      ),
                    ),
                    const Divider(height: 26),
                    Text(
                      (guidance['safety_note'] ?? '').toString(),
                      style: const TextStyle(fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
              ),
            ),
            if (contextData.isNotEmpty)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'RO context that will help the engineer',
                        style: TextStyle(fontWeight: FontWeight.w900),
                      ),
                      const SizedBox(height: 8),
                      if (contextData['ro_asset_id'] != null)
                        Text('RO: ${contextData['ro_asset_id']}'),
                      if (contextData['ro_model'] != null)
                        Text('Model: ${contextData['ro_model']}'),
                      if (contextData['filter_service_health_status'] != null)
                        Text(
                          'Health: ${(contextData['filter_service_health_status'] ?? '').toString().replaceAll('_', ' ')}',
                        ),
                      if (contextData['last_service_date'] != null)
                        Text('Last service: ${contextData['last_service_date']}'),
                      const SizedBox(height: 6),
                      const Text(
                        'Phone/address and other unnecessary personal details are not added by the assistant.',
                        style: TextStyle(fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 14),
            TextField(
              controller: _descriptionController,
              minLines: 3,
              maxLines: 6,
              enabled: !_submitting,
              decoration: const InputDecoration(
                labelText: 'Anything else you noticed? (optional)',
                hintText: 'Example: leak started today near the outside tube…',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 14),
            SizedBox(
              height: 52,
              child: FilledButton.icon(
                onPressed: _submitting ? null : _raise,
                icon: _submitting
                    ? const SizedBox.square(
                        dimension: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.support_agent),
                label: Text(
                  _submitting
                      ? 'Raising Complaint…'
                      : (guidance['cta'] ?? 'Still having a problem? Raise Complaint').toString(),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  @override
  void dispose() {
    _descriptionController.dispose();
    super.dispose();
  }
}
