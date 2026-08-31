import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/customer_onboarding_service.dart';
import '../dashboard/dashboard_screen.dart';

class CustomerOnboardingScreen extends StatefulWidget {
  const CustomerOnboardingScreen({super.key, this.referralCode = ''});

  final String referralCode;

  @override
  State<CustomerOnboardingScreen> createState() =>
      _CustomerOnboardingScreenState();
}

class _CustomerOnboardingScreenState extends State<CustomerOnboardingScreen> {
  final _service = CustomerOnboardingService();
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  final _confirmPassword = TextEditingController();
  final _referral = TextEditingController();
  final _otp = TextEditingController();
  bool _otpStep = false;
  bool _busy = false;
  bool _hidePassword = true;
  bool _registered = false;
  Timer? _simPollTimer;
  bool _simPolling = false;
  String? _simStatus;

  @override
  void initState() {
    super.initState();
    _referral.text = widget.referralCode.trim().toUpperCase();
    _name.addListener(_refreshPasswordGuidance);
    _password.addListener(_refreshPasswordGuidance);
  }

  void _refreshPasswordGuidance() {
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _simPollTimer?.cancel();
    _name.removeListener(_refreshPasswordGuidance);
    _password.removeListener(_refreshPasswordGuidance);
    for (final controller in [
      _name,
      _phone,
      _password,
      _confirmPassword,
      _referral,
      _otp,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  Future<void> _createAccount() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _busy = true);
    try {
      final names = _name.text.trim().split(RegExp(r'\s+'));
      if (!_registered) {
        await _service.register(
          firstName: names.first,
          lastName: names.skip(1).join(' '),
          phone: _phone.text,
          password: _password.text,
        );
        _registered = true;
      }
      await _service.sendOtp(_phone.text);
      if (!mounted) return;
      setState(() => _otpStep = true);
      _show('OTP sent to ${_phone.text.trim()}');
    } catch (e) {
      final message = e.toString().replaceFirst('Exception: ', '');
      if (!_registered && message.toLowerCase().contains('already exists')) {
        try {
          await _service.sendOtp(_phone.text);
          if (!mounted) return;
          _registered = true;
          setState(() => _otpStep = true);
          _show('Existing account found. OTP sent to complete verification.');
        } catch (sendError) {
          _show(sendError.toString().replaceFirst('Exception: ', ''));
        }
      } else {
        _show(message);
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _verify() async {
    if (_otp.text.trim().length != 6) {
      _show('Please enter the 6-digit OTP.');
      return;
    }
    setState(() => _busy = true);
    try {
      final result = await _service.verifyAndLogin(
        phone: _phone.text,
        otp: _otp.text,
        password: _password.text,
        referralCode: _referral.text,
      );
      if (!mounted) return;
      final linked = result['existing_customer_linked'] == true;
      final referralWarning = result['referral_warning']?.toString();
      _show(
        referralWarning != null
            ? 'Account ready. Referral was not applied: $referralWarning'
            : linked
            ? 'Your existing ARI customer account is connected.'
            : 'Your ARI account is ready.',
      );
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

  Future<void> _verifyBySimSms() async {
    if (_simPolling) return;
    final passwordError = _passwordError(_password.text);
    if (passwordError != null) {
      _show(passwordError);
      return;
    }
    setState(() {
      _simPolling = true;
      _simStatus = 'Preparing secure SIM verification…';
    });
    try {
      final challenge = await _service.startSimVerification(
        phone: _phone.text,
        password: _password.text,
      );
      final destination = challenge['destination_number'].toString();
      final body = challenge['sms_body'].toString();
      final uri = Uri(
        scheme: 'sms',
        path: destination,
        queryParameters: {'body': body},
      );
      if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
        throw Exception('Unable to open the phone SMS app.');
      }
      if (!mounted) return;
      setState(
        () => _simStatus =
            'Send the prepared SMS using your registered SIM. Waiting for office gateway…',
      );
      final challengeId = challenge['challenge_id'] as int;
      final pollSecret = challenge['poll_secret'].toString();
      _simPollTimer?.cancel();
      _simPollTimer = Timer.periodic(const Duration(seconds: 3), (timer) async {
        try {
          final result = await _service.pollSimVerification(
            challengeId: challengeId,
            pollSecret: pollSecret,
            referralCode: _referral.text,
          );
          final status = result['status']?.toString() ?? 'PENDING';
          if (!mounted) return;
          if (status == 'VERIFIED') {
            timer.cancel();
            setState(() {
              _simPolling = false;
              _simStatus = 'SIM verified successfully.';
            });
            _finishOnboarding(result);
          } else if (status == 'EXPIRED' || status == 'CANCELLED') {
            timer.cancel();
            setState(() {
              _simPolling = false;
              _simStatus = 'Verification expired. Please try again.';
            });
          }
        } catch (error) {
          timer.cancel();
          if (mounted) {
            setState(() {
              _simPolling = false;
              _simStatus = error.toString().replaceFirst('Exception: ', '');
            });
          }
        }
      });
    } catch (error) {
      if (mounted) {
        setState(() {
          _simPolling = false;
          _simStatus = error.toString().replaceFirst('Exception: ', '');
        });
      }
    }
  }

  void _finishOnboarding(Map<String, dynamic> result) {
    if (!mounted) return;
    final warning = result['referral_warning']?.toString();
    if (warning != null) {
      _show('Account verified. Referral was not applied: $warning');
    }
    Navigator.pushAndRemoveUntil(
      context,
      MaterialPageRoute(builder: (_) => const DashboardScreen()),
      (_) => false,
    );
  }

  void _show(String message) {
    if (mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(message)));
    }
  }

  bool get _passwordHasLength => _password.text.length >= 8;
  bool get _passwordHasUpper => RegExp(r'[A-Z]').hasMatch(_password.text);
  bool get _passwordHasLower => RegExp(r'[a-z]').hasMatch(_password.text);
  bool get _passwordHasNumber => RegExp(r'[0-9]').hasMatch(_password.text);
  bool get _passwordHasSymbol =>
      RegExp(r'[^A-Za-z0-9]').hasMatch(_password.text);
  bool get _passwordIsDifferentFromName {
    final password = _password.text.toLowerCase();
    final nameParts = _name.text
        .toLowerCase()
        .split(RegExp(r'\s+'))
        .where((part) => part.length >= 3);
    return password.isNotEmpty && !nameParts.any(password.contains);
  }

  String? _passwordError(String? value) {
    if ((value ?? '').isEmpty) return 'Create a password.';
    if (!_passwordHasLength) return 'Use at least 8 characters.';
    if (!_passwordHasUpper || !_passwordHasLower) {
      return 'Add both uppercase and lowercase letters.';
    }
    if (!_passwordHasNumber) return 'Add at least one number.';
    if (!_passwordHasSymbol) return 'Add at least one special character.';
    if (!_passwordIsDifferentFromName) {
      return 'Password must not contain your name.';
    }
    return null;
  }

  Widget _passwordRule(String label, bool passed) {
    return Padding(
      padding: const EdgeInsets.only(top: 5),
      child: Row(
        children: [
          Icon(
            passed ? Icons.check_circle : Icons.radio_button_unchecked,
            size: 17,
            color: passed ? const Color(0xFF16834A) : Colors.grey.shade600,
          ),
          const SizedBox(width: 7),
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 12.5,
                color: passed ? const Color(0xFF126B3D) : Colors.grey.shade700,
                fontWeight: passed ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Create / Activate Account')),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Icon(
                  Icons.verified_user_outlined,
                  size: 64,
                  color: Color(0xFF0877C9),
                ),
                const SizedBox(height: 12),
                Text(
                  _otpStep
                      ? 'Verify your mobile'
                      : 'One account for everything',
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  _otpStep
                      ? 'Enter the OTP sent to +91 ${_phone.text.trim()}.'
                      : 'Existing ARI customers and new shoppers can activate their own account.',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 28),
                if (!_otpStep) ...[
                  TextFormField(
                    controller: _name,
                    textCapitalization: TextCapitalization.words,
                    decoration: const InputDecoration(
                      labelText: 'Full name',
                      prefixIcon: Icon(Icons.person_outline),
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) => value == null || value.trim().isEmpty
                        ? 'Enter your name.'
                        : null,
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _phone,
                    keyboardType: TextInputType.phone,
                    maxLength: 10,
                    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                    decoration: const InputDecoration(
                      labelText: 'Registered mobile number',
                      prefixText: '+91 ',
                      prefixIcon: Icon(Icons.phone_outlined),
                      border: OutlineInputBorder(),
                      counterText: '',
                    ),
                    validator: (value) => value?.length == 10
                        ? null
                        : 'Enter a valid 10-digit mobile number.',
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _password,
                    obscureText: _hidePassword,
                    decoration: InputDecoration(
                      labelText: 'Create password',
                      prefixIcon: const Icon(Icons.lock_outline),
                      border: const OutlineInputBorder(),
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
                    validator: _passwordError,
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 7, 8, 2),
                    child: Column(
                      children: [
                        _passwordRule(
                          'At least 8 characters',
                          _passwordHasLength,
                        ),
                        _passwordRule(
                          'Uppercase and lowercase letters',
                          _passwordHasUpper && _passwordHasLower,
                        ),
                        _passwordRule(
                          'At least one number',
                          _passwordHasNumber,
                        ),
                        _passwordRule(
                          'At least one special character',
                          _passwordHasSymbol,
                        ),
                        _passwordRule(
                          'Must not contain your name',
                          _passwordIsDifferentFromName,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _confirmPassword,
                    obscureText: true,
                    decoration: const InputDecoration(
                      labelText: 'Confirm password',
                      prefixIcon: Icon(Icons.lock_reset),
                      border: OutlineInputBorder(),
                    ),
                    validator: (value) => value != _password.text
                        ? 'Passwords do not match.'
                        : null,
                  ),
                  const SizedBox(height: 14),
                  TextFormField(
                    controller: _referral,
                    textCapitalization: TextCapitalization.characters,
                    decoration: const InputDecoration(
                      labelText: 'Referral code (optional)',
                      prefixIcon: Icon(Icons.card_giftcard_outlined),
                      border: OutlineInputBorder(),
                    ),
                  ),
                ] else ...[
                  TextFormField(
                    controller: _otp,
                    autofocus: true,
                    keyboardType: TextInputType.number,
                    maxLength: 6,
                    inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 8,
                    ),
                    decoration: const InputDecoration(
                      labelText: '6-digit OTP',
                      border: OutlineInputBorder(),
                      counterText: '',
                    ),
                  ),
                  const SizedBox(height: 12),
                  TextButton(
                    onPressed: _busy
                        ? null
                        : () => _service
                              .sendOtp(_phone.text)
                              .then((_) => _show('A new OTP has been sent.'))
                              .catchError(
                                (e) => _show(
                                  e.toString().replaceFirst('Exception: ', ''),
                                ),
                              ),
                    child: const Text('Resend OTP'),
                  ),
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 8),
                    child: Row(
                      children: [
                        Expanded(child: Divider()),
                        Padding(
                          padding: EdgeInsets.symmetric(horizontal: 12),
                          child: Text('OR'),
                        ),
                        Expanded(child: Divider()),
                      ],
                    ),
                  ),
                  OutlinedButton.icon(
                    onPressed: _simPolling ? null : _verifyBySimSms,
                    icon: const Icon(Icons.sim_card_outlined),
                    label: Text(
                      _simPolling
                          ? 'WAITING FOR SIM SMS…'
                          : 'VERIFY USING MY SIM SMS',
                    ),
                  ),
                  if (_simStatus != null) ...[
                    const SizedBox(height: 10),
                    Text(
                      _simStatus!,
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ],
                ],
                const SizedBox(height: 22),
                FilledButton.icon(
                  onPressed: _busy
                      ? null
                      : (_otpStep ? _verify : _createAccount),
                  icon: _busy
                      ? const SizedBox.square(
                          dimension: 18,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Icon(
                          _otpStep
                              ? Icons.verified_outlined
                              : Icons.arrow_forward,
                        ),
                  label: Text(
                    _otpStep
                        ? 'VERIFY & CONTINUE'
                        : 'CREATE / ACTIVATE ACCOUNT',
                  ),
                ),
                if (!_otpStep) ...[
                  const SizedBox(height: 12),
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Already have an account? Login'),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
