import 'dart:io';

import 'package:flutter/material.dart';

import '../../services/sms_gateway_service.dart';

class SmsGatewaySetupScreen extends StatefulWidget {
  const SmsGatewaySetupScreen({super.key});

  @override
  State<SmsGatewaySetupScreen> createState() => _SmsGatewaySetupScreenState();
}

class _SmsGatewaySetupScreenState extends State<SmsGatewaySetupScreen> {
  final _service = const SmsGatewayService();
  final _phone = TextEditingController();
  bool _loading = true;
  bool _saving = false;
  bool _localConfigured = false;
  Map<String, dynamic>? _gateway;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _phone.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final status = await _service.fetchStatus();
      final configured = status['configured'] == true;
      final gateway = configured && status['gateway'] is Map
          ? Map<String, dynamic>.from(status['gateway'] as Map)
          : null;
      final localConfigured = await _service.isConfiguredOnThisPhone();
      if (!mounted) return;
      if (gateway != null && _phone.text.isEmpty) {
        _phone.text = gateway['phone_number']?.toString() ?? '';
      }
      setState(() {
        _gateway = gateway;
        _localConfigured = localConfigured;
      });
    } catch (error) {
      if (mounted) {
        setState(() => _error = error.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _activate() async {
    final phone = _phone.text.replaceAll(RegExp(r'\D'), '');
    if (phone.length != 10) {
      _show('Enter the 10-digit number of the SIM installed in this office phone.');
      return;
    }
    setState(() => _saving = true);
    try {
      await _service.provision(phoneNumber: phone);
      if (!mounted) return;
      _show('Office SIM gateway activated on this Android phone.');
      await _load();
    } catch (error) {
      if (mounted) {
        _show(error.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _disable() async {
    setState(() => _saving = true);
    try {
      await _service.disable();
      if (!mounted) return;
      _show('SIM gateway disabled.');
      await _load();
    } catch (error) {
      if (mounted) _show(error.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _show(String message) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  String _lastSeen() {
    final raw = _gateway?['last_seen_at']?.toString();
    if (raw == null || raw.isEmpty || raw == 'null') return 'No verification SMS received yet';
    return raw.replaceFirst('T', ' ').replaceFirst('Z', ' UTC');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Free SIM Verification Gateway'),
        actions: [
          IconButton(onPressed: _loading ? null : _load, icon: const Icon(Icons.refresh)),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(20),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(18),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Icon(
                              _gateway != null ? Icons.verified_rounded : Icons.sms_outlined,
                              color: _gateway != null ? Colors.green : null,
                            ),
                            const SizedBox(width: 10),
                            Expanded(
                              child: Text(
                                _gateway != null ? 'Gateway Active' : 'Gateway Not Configured',
                                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                                      fontWeight: FontWeight.w800,
                                    ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'Use one ARI office Android phone with a normal SIM. Customers send a pre-filled ARI VERIFY SMS from their registered SIM. This phone receives it and securely verifies the customer account without MSG91/Twilio.',
                        ),
                        if (!Platform.isAndroid) ...[
                          const SizedBox(height: 12),
                          const Text(
                            'Setup must be completed from an Android phone. Windows can view status only.',
                            style: TextStyle(fontWeight: FontWeight.w700),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(_error!, style: const TextStyle(color: Colors.red)),
                  ),
                TextField(
                  controller: _phone,
                  enabled: Platform.isAndroid && !_saving,
                  keyboardType: TextInputType.phone,
                  maxLength: 10,
                  decoration: const InputDecoration(
                    labelText: 'SIM number installed in this office phone',
                    prefixText: '+91 ',
                    border: OutlineInputBorder(),
                    counterText: '',
                  ),
                ),
                const SizedBox(height: 12),
                if (_gateway != null) ...[
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.sim_card),
                    title: Text('+91 ${_gateway!['phone_number'] ?? ''}'),
                    subtitle: Text(
                      'Server gateway: ${_gateway!['name'] ?? 'ARI Office SMS Gateway'}\nLast received: ${_lastSeen()}',
                    ),
                  ),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(
                      _localConfigured ? Icons.phone_android : Icons.phonelink_erase,
                      color: _localConfigured ? Colors.green : Colors.orange,
                    ),
                    title: Text(
                      _localConfigured
                          ? 'This phone has gateway credentials'
                          : 'This phone is not the active receiver',
                    ),
                    subtitle: const Text(
                      'Re-activate below if the office SIM was moved to this phone.',
                    ),
                  ),
                ],
                const SizedBox(height: 12),
                FilledButton.icon(
                  onPressed: Platform.isAndroid && !_saving ? _activate : null,
                  icon: const Icon(Icons.sms_rounded),
                  label: Text(
                    _saving
                        ? 'PLEASE WAIT…'
                        : _gateway == null
                            ? 'ACTIVATE THIS PHONE AS GATEWAY'
                            : 'RE-ACTIVATE / MOVE GATEWAY TO THIS PHONE',
                  ),
                ),
                if (_gateway != null) ...[
                  const SizedBox(height: 10),
                  OutlinedButton.icon(
                    onPressed: !_saving ? _disable : null,
                    icon: const Icon(Icons.power_settings_new),
                    label: const Text('DISABLE GATEWAY'),
                  ),
                ],
                const SizedBox(height: 24),
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Text(
                      'Customer flow: Create / Activate Account → Verify Using My SIM SMS → phone opens an SMS addressed to the ARI office SIM → customer taps Send → this gateway validates sender number + one-time token → account activates automatically. Only ARI VERIFY messages are processed.',
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}
