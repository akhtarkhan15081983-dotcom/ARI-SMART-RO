import 'package:flutter/material.dart';

import '../../services/customer_service.dart';

class CustomerProfileScreen extends StatefulWidget {
  const CustomerProfileScreen({super.key});

  @override
  State<CustomerProfileScreen> createState() => _CustomerProfileScreenState();
}

class _CustomerProfileScreenState extends State<CustomerProfileScreen> {
  final _service = CustomerService();
  bool _loading = true;
  bool _saving = false;
  String? _error;
  Map<String, dynamic> _profile = const {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final profile = await _service.getMyProfile();
      if (!mounted) return;
      setState(() => _profile = profile);
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _value(String key, [String fallback = 'Not available']) {
    final value = (_profile[key] ?? '').toString().trim();
    return value.isEmpty ? fallback : value;
  }

  Future<void> _edit() async {
    final email = TextEditingController(text: _value('email', ''));
    final alternatePhone = TextEditingController(
      text: _value('alternate_phone', ''),
    );
    final address = TextEditingController(text: _value('address', ''));
    final area = TextEditingController(text: _value('area', ''));
    final city = TextEditingController(text: _value('city', ''));
    final state = TextEditingController(text: _value('state', ''));
    final pincode = TextEditingController(text: _value('pincode', ''));

    final save = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Edit Profile'),
        content: SizedBox(
          width: 520,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                _field(email, 'Email'),
                _field(alternatePhone, 'Alternate phone'),
                _field(address, 'Address', lines: 2),
                _field(area, 'Area'),
                _field(city, 'City'),
                _field(state, 'State'),
                _field(pincode, 'Pincode'),
              ],
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (save == true) {
      setState(() => _saving = true);
      try {
        final updated = await _service.updateMyProfile({
          'email': email.text.trim(),
          'alternate_phone': alternatePhone.text.trim(),
          'address': address.text.trim(),
          'area': area.text.trim(),
          'city': city.text.trim(),
          'state': state.text.trim(),
          'pincode': pincode.text.trim(),
        });
        if (!mounted) return;
        setState(() => _profile = updated);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Profile updated successfully.')),
        );
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
          );
        }
      } finally {
        if (mounted) setState(() => _saving = false);
      }
    }

    for (final controller in [
      email, alternatePhone, address, area, city, state, pincode
    ]) {
      controller.dispose();
    }
  }

  Widget _field(
    TextEditingController controller,
    String label, {
    int lines = 1,
  }) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: TextField(
          controller: controller,
          maxLines: lines,
          decoration: InputDecoration(
            labelText: label,
            border: const OutlineInputBorder(),
          ),
        ),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('My Profile'),
        actions: [
          IconButton(onPressed: _loading ? null : _load, icon: const Icon(Icons.refresh)),
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
                        Text(_error!, textAlign: TextAlign.center),
                        const SizedBox(height: 12),
                        FilledButton(onPressed: _load, child: const Text('Retry')),
                      ],
                    ),
                  ),
                )
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(18),
                          child: Row(
                            children: [
                              const CircleAvatar(
                                radius: 34,
                                child: Icon(Icons.person_rounded, size: 34),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      _value('name'),
                                      style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                            fontWeight: FontWeight.w800,
                                          ),
                                    ),
                                    Text(_value('customer_id')),
                                    Text(_value('card_number')),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      _row('Phone', _value('phone')),
                      _row('Alternate phone', _value('alternate_phone')),
                      _row('Email', _value('email')),
                      _row('Address', [
                        _value('address', ''),
                        _value('area', ''),
                        _value('city', ''),
                        _value('state', ''),
                        _value('pincode', ''),
                      ].where((e) => e.isNotEmpty).join(', ')),
                      _row('RO model', _value('ro_model')),
                      _row('Ownership', _value('ownership_type')),
                      _row('Installation date', _value('installation_date')),
                      const SizedBox(height: 12),
                      FilledButton.icon(
                        onPressed: _saving ? null : _edit,
                        icon: const Icon(Icons.edit_outlined),
                        label: Text(_saving ? 'Saving...' : 'EDIT PROFILE'),
                      ),
                    ],
                  ),
                ),
    );
  }

  Widget _row(String label, String value) => Card(
        child: ListTile(
          title: Text(label, style: const TextStyle(fontSize: 12)),
          subtitle: Text(
            value.trim().isEmpty ? 'Not available' : value,
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
        ),
      );
}
