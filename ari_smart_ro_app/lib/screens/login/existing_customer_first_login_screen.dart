import 'package:flutter/material.dart';

import '../../services/existing_customer_access_service.dart';
import '../dashboard/dashboard_screen.dart';

class ExistingCustomerFirstLoginScreen extends StatefulWidget {
  const ExistingCustomerFirstLoginScreen({super.key});

  @override
  State<ExistingCustomerFirstLoginScreen> createState() =>
      _ExistingCustomerFirstLoginScreenState();
}

class _ExistingCustomerFirstLoginScreenState
    extends State<ExistingCustomerFirstLoginScreen> {
  final _service = ExistingCustomerAccessService();
  final _identifier = TextEditingController();
  final _temporaryPassword = TextEditingController();
  final _newPassword = TextEditingController();
  final _confirmPassword = TextEditingController();
  bool _busy = false;
  bool _verified = false;
  bool _hideTemp = true;
  bool _hideNew = true;
  String _activationToken = '';
  String _customerLabel = '';

  @override
  void dispose() {
    _identifier.dispose();
    _temporaryPassword.dispose();
    _newPassword.dispose();
    _confirmPassword.dispose();
    super.dispose();
  }

  void _show(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _verifyExisting() async {
    if (_identifier.text.trim().isEmpty || _temporaryPassword.text.isEmpty) {
      _show('Customer ID / Card / Mobile and temporary password are required.');
      return;
    }
    setState(() => _busy = true);
    try {
      final result = await _service.start(
        identifier: _identifier.text,
        temporaryPassword: _temporaryPassword.text,
      );
      final customer = Map<String, dynamic>.from(result['customer'] as Map);
      if (!mounted) return;
      setState(() {
        _activationToken = result['activation_token'].toString();
        _customerLabel =
            '${customer['name'] ?? ''} • ${customer['customer_id'] ?? ''}';
        _verified = true;
      });
      _show('Customer verified. Create your personal password now.');
    } catch (e) {
      _show(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _finish() async {
    if (_newPassword.text != _confirmPassword.text) {
      _show('New password and confirm password do not match.');
      return;
    }
    if (_newPassword.text.length < 8) {
      _show('Use at least 8 characters for your personal password.');
      return;
    }
    setState(() => _busy = true);
    try {
      await _service.complete(
        activationToken: _activationToken,
        newPassword: _newPassword.text,
      );
      if (!mounted) return;
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (_) => const DashboardScreen()),
        (_) => false,
      );
    } catch (e) {
      _show(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Existing Customer First Login')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Icon(Icons.verified_user_outlined, size: 64),
              const SizedBox(height: 12),
              Text(
                _verified ? 'Create Personal Password' : 'Activate Existing Customer',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                _verified
                    ? _customerLabel
                    : 'Use Customer ID, Card Number, old card number or registered mobile.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              if (!_verified) ...[
                TextField(
                  controller: _identifier,
                  textCapitalization: TextCapitalization.characters,
                  decoration: const InputDecoration(
                    labelText: 'Customer ID / Card / Mobile',
                    prefixIcon: Icon(Icons.badge_outlined),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: _temporaryPassword,
                  obscureText: _hideTemp,
                  decoration: InputDecoration(
                    labelText: 'Temporary universal password',
                    prefixIcon: const Icon(Icons.key_outlined),
                    border: const OutlineInputBorder(),
                    suffixIcon: IconButton(
                      onPressed: () => setState(() => _hideTemp = !_hideTemp),
                      icon: Icon(
                        _hideTemp
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: _busy ? null : _verifyExisting,
                  icon: const Icon(Icons.verified_outlined),
                  label: Text(_busy ? 'VERIFYING…' : 'VERIFY EXISTING CUSTOMER'),
                ),
              ] else ...[
                const Text(
                  'The temporary password works only for first activation. Choose a private password now; the temporary password cannot be reused for this account.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 18),
                TextField(
                  controller: _newPassword,
                  obscureText: _hideNew,
                  decoration: InputDecoration(
                    labelText: 'New personal password',
                    prefixIcon: const Icon(Icons.lock_outline),
                    border: const OutlineInputBorder(),
                    suffixIcon: IconButton(
                      onPressed: () => setState(() => _hideNew = !_hideNew),
                      icon: Icon(
                        _hideNew
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                TextField(
                  controller: _confirmPassword,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: 'Confirm personal password',
                    prefixIcon: Icon(Icons.lock_reset),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: _busy ? null : _finish,
                  icon: const Icon(Icons.check_circle_outline),
                  label: Text(_busy ? 'ACTIVATING…' : 'ACTIVATE & LOGIN'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
