import 'package:flutter/material.dart';

import '../../services/password_reset_service.dart';
import '../../services/api_service.dart';

class ForgotPasswordScreen extends StatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _service = const PasswordResetService();
  final _phone = TextEditingController();
  final _code = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();

  bool _requestSent = false;
  bool _loading = false;
  bool _hidePassword = true;

  @override
  void dispose() {
    _phone.dispose();
    _code.dispose();
    _password.dispose();
    _confirm.dispose();
    super.dispose();
  }

  Future<void> _requestReset() async {
    final phone = _phone.text.trim();
    if (phone.length != 10 || int.tryParse(phone) == null) {
      _show('Enter a valid 10-digit mobile number.');
      return;
    }
    setState(() => _loading = true);
    try {
      await _service.requestReset(phone);
      if (!mounted) return;
      setState(() => _requestSent = true);
      _show(
        'Reset request sent. Ask your administrator to approve it and give you the one-time reset code.',
      );
    } catch (error) {
      if (mounted) {
        _show(error.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _completeReset() async {
    final phone = _phone.text.trim();
    final code = _code.text.trim();
    if (code.length != 6 || int.tryParse(code) == null) {
      _show('Enter the 6-digit code given by your administrator.');
      return;
    }
    if (_password.text.length < 8) {
      _show('Use a strong password with at least 8 characters.');
      return;
    }
    if (_password.text != _confirm.text) {
      _show('New password and confirmation do not match.');
      return;
    }

    setState(() => _loading = true);
    try {
      await _service.completeReset(
        phone: phone,
        code: code,
        newPassword: _password.text,
      );
      await ApiService.clearRememberedCredentials();
      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const Text('Password changed'),
          content: const Text(
            'Your password has been changed successfully. Sign in with the new password.',
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text('OK'),
            ),
          ],
        ),
      );
      if (mounted) Navigator.pop(context);
    } catch (error) {
      if (mounted) {
        _show(error.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _show(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), behavior: SnackBarBehavior.floating),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Forgot Password')),
        body: SafeArea(
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              const Icon(Icons.lock_reset_rounded, size: 72),
              const SizedBox(height: 14),
              Text(
                'Admin-approved password reset',
                style: Theme.of(context).textTheme.headlineSmall,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              const Text(
                'Your existing password cannot be viewed. Send a reset request, get approval from your administrator, then set a new password.',
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              TextField(
                controller: _phone,
                enabled: !_requestSent && !_loading,
                keyboardType: TextInputType.phone,
                maxLength: 10,
                decoration: const InputDecoration(
                  labelText: 'Registered mobile number',
                  prefixIcon: Icon(Icons.phone_outlined),
                ),
              ),
              FilledButton.icon(
                onPressed: _loading || _requestSent ? null : _requestReset,
                icon: const Icon(Icons.send_outlined),
                label: const Text('SEND RESET REQUEST'),
              ),
              if (_requestSent) ...[
                const SizedBox(height: 24),
                TextField(
                  controller: _code,
                  enabled: !_loading,
                  keyboardType: TextInputType.number,
                  maxLength: 6,
                  decoration: const InputDecoration(
                    labelText: '6-digit admin reset code',
                    prefixIcon: Icon(Icons.pin_outlined),
                  ),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: _password,
                  enabled: !_loading,
                  obscureText: _hidePassword,
                  enableSuggestions: false,
                  autocorrect: false,
                  decoration: InputDecoration(
                    labelText: 'New password',
                    prefixIcon: const Icon(Icons.lock_outline),
                    suffixIcon: IconButton(
                      onPressed: () =>
                          setState(() => _hidePassword = !_hidePassword),
                      icon: Icon(
                        _hidePassword
                            ? Icons.visibility_outlined
                            : Icons.visibility_off_outlined,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _confirm,
                  enabled: !_loading,
                  obscureText: true,
                  enableSuggestions: false,
                  autocorrect: false,
                  decoration: const InputDecoration(
                    labelText: 'Confirm new password',
                    prefixIcon: Icon(Icons.lock_outline),
                  ),
                ),
                const SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: _loading ? null : _completeReset,
                  icon: _loading
                      ? const SizedBox.square(
                          dimension: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.check_circle_outline),
                  label: const Text('CHANGE PASSWORD'),
                ),
              ],
            ],
          ),
        ),
      );
}
