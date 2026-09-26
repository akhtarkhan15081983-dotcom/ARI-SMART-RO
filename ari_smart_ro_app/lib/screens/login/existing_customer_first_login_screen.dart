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
  final _otp = TextEditingController();
  final _newPassword = TextEditingController();
  final _confirmPassword = TextEditingController();
  bool _busy = false;
  bool _codeSent = false;
  bool _hideNew = true;
  String _activationToken = '';
  String _customerLabel = '';
  String _destination = '';

  @override
  void dispose() {
    _identifier.dispose();
    _otp.dispose();
    _newPassword.dispose();
    _confirmPassword.dispose();
    super.dispose();
  }

  void _show(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  Future<void> _sendVerificationCode() async {
    if (_identifier.text.trim().isEmpty) {
      _show('Customer ID / Card / Mobile is required.');
      return;
    }
    setState(() => _busy = true);
    try {
      final result = await _service.start(identifier: _identifier.text);
      final customer = Map<String, dynamic>.from(result['customer'] as Map);
      if (!mounted) return;
      setState(() {
        _activationToken = result['activation_token'].toString();
        _destination = result['destination']?.toString() ?? '';
        _customerLabel =
            '${customer['name'] ?? ''} • ${customer['customer_id'] ?? ''}';
        _codeSent = true;
      });
      _show('Verification code sent to the registered mobile.');
    } catch (e) {
      _show(e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _finish() async {
    if (_otp.text.trim().length != 6) {
      _show('Enter the 6-digit verification code.');
      return;
    }
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
        otp: _otp.text,
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
                _codeSent ? 'Verify Mobile & Set Password' : 'Activate Existing Customer',
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                      fontWeight: FontWeight.w800,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                _codeSent
                    ? '$_customerLabel\nCode sent to $_destination'
                    : 'Use Customer ID, Card Number, old card number or registered mobile. We will verify the registered mobile before activation.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              if (!_codeSent) ...[
                TextField(
                  controller: _identifier,
                  textCapitalization: TextCapitalization.characters,
                  decoration: const InputDecoration(
                    labelText: 'Customer ID / Card / Mobile',
                    prefixIcon: Icon(Icons.badge_outlined),
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: _busy ? null : _sendVerificationCode,
                  icon: const Icon(Icons.sms_outlined),
                  label: Text(_busy ? 'SENDING…' : 'SEND VERIFICATION CODE'),
                ),
              ] else ...[
                TextField(
                  controller: _otp,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: '6-digit verification code',
                    prefixIcon: Icon(Icons.shield_outlined),
                    border: OutlineInputBorder(),
                    counterText: '',
                  ),
                ),
                const SizedBox(height: 14),
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
                  label: Text(_busy ? 'ACTIVATING…' : 'VERIFY & ACTIVATE'),
                ),
                TextButton(
                  onPressed: _busy
                      ? null
                      : () => setState(() {
                            _codeSent = false;
                            _activationToken = '';
                            _otp.clear();
                          }),
                  child: const Text('START AGAIN / RESEND'),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
