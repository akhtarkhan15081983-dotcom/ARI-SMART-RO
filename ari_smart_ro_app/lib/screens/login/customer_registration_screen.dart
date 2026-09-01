import 'package:flutter/material.dart';

import '../../services/customer_auth_service.dart';

class CustomerRegistrationScreen extends StatefulWidget {
  const CustomerRegistrationScreen({super.key});

  @override
  State<CustomerRegistrationScreen> createState() =>
      _CustomerRegistrationScreenState();
}

class _CustomerRegistrationScreenState
    extends State<CustomerRegistrationScreen> {
  final _firstName = TextEditingController();
  final _lastName = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  final _otp = TextEditingController();
  final _service = CustomerAuthService();

  bool _otpStep = false;
  bool _loading = false;

  @override
  void dispose() {
    _firstName.dispose();
    _lastName.dispose();
    _phone.dispose();
    _password.dispose();
    _otp.dispose();
    super.dispose();
  }

  void _message(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(text)));
  }

  bool _validIdentity() {
    final phone = _phone.text.trim();
    if (!RegExp(r'^\d{10}$').hasMatch(phone)) {
      _message('Enter a valid 10-digit phone number.');
      return false;
    }
    if (_password.text.length < 8) {
      _message('Password must contain at least 8 characters.');
      return false;
    }
    return true;
  }

  Future<void> _register() async {
    if (_firstName.text.trim().isEmpty || !_validIdentity()) return;
    setState(() => _loading = true);
    final registration = await _service.register(
      firstName: _firstName.text.trim(),
      lastName: _lastName.text.trim(),
      phone: _phone.text.trim(),
      password: _password.text,
    );
    if (!mounted) return;
    if (!registration.success) {
      setState(() => _loading = false);
      _message(registration.message);
      return;
    }
    await _sendOtp();
  }

  Future<void> _sendOtp() async {
    if (!_validIdentity()) return;
    setState(() => _loading = true);
    final result = await _service.sendOtp(_phone.text.trim());
    if (!mounted) return;
    setState(() {
      _loading = false;
      if (result.success) _otpStep = true;
    });
    _message(result.message);
  }

  Future<void> _verify() async {
    if (!_validIdentity()) return;
    if (!RegExp(r'^\d{6}$').hasMatch(_otp.text.trim())) {
      _message('Enter the 6-digit OTP.');
      return;
    }
    setState(() => _loading = true);
    final result = await _service.verifyOtp(
      phone: _phone.text.trim(),
      otp: _otp.text.trim(),
      password: _password.text,
    );
    if (!mounted) return;
    setState(() => _loading = false);
    _message(result.message);
    if (result.success) {
      Navigator.pop(context, _phone.text.trim());
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Customer Registration')),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          if (!_otpStep) ...[
            TextField(
              controller: _firstName,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(labelText: 'First name'),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _lastName,
              textCapitalization: TextCapitalization.words,
              decoration: const InputDecoration(labelText: 'Last name'),
            ),
          ],
          const SizedBox(height: 12),
          TextField(
            controller: _phone,
            enabled: !_otpStep,
            keyboardType: TextInputType.phone,
            decoration: const InputDecoration(labelText: 'Phone number'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _password,
            obscureText: true,
            decoration: const InputDecoration(labelText: 'Final password'),
          ),
          if (_otpStep) ...[
            const SizedBox(height: 12),
            TextField(
              controller: _otp,
              keyboardType: TextInputType.number,
              maxLength: 6,
              decoration: const InputDecoration(labelText: 'SMS OTP'),
            ),
          ],
          const SizedBox(height: 24),
          FilledButton(
            onPressed: _loading ? null : (_otpStep ? _verify : _register),
            child: _loading
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : Text(_otpStep ? 'VERIFY & ACTIVATE' : 'REGISTER & SEND OTP'),
          ),
          if (!_otpStep)
            TextButton(
              onPressed: _loading ? null : _sendOtp,
              child: const Text('Already registered? Send verification OTP'),
            ),
          if (_otpStep)
            TextButton(
              onPressed: _loading ? null : _sendOtp,
              child: const Text('Resend OTP'),
            ),
        ],
      ),
    );
  }
}
