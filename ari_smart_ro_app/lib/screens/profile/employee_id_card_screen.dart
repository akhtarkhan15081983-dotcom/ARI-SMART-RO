import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../services/employee_identity_service.dart';

class EmployeeIdCardScreen extends StatefulWidget {
  const EmployeeIdCardScreen({super.key});

  @override
  State<EmployeeIdCardScreen> createState() => _EmployeeIdCardScreenState();
}

class _EmployeeIdCardScreenState extends State<EmployeeIdCardScreen> {
  final _service = const EmployeeIdentityService();
  Map<String, dynamic>? _card;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final card = await _service.myIdCard();
      if (mounted) setState(() => _card = card);
    } catch (e) {
      if (mounted) {
        setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_card == null) {
      return Scaffold(
        appBar: AppBar(title: const Text('My Digital ID')),
        body: Center(
          child: _error == null
              ? const CircularProgressIndicator()
              : Text(_error!, textAlign: TextAlign.center),
        ),
      );
    }
    final card = _card!;
    final onboarding = Map<String, dynamic>.from(
      card['onboarding'] as Map? ?? const {},
    );
    final photo = (card['photo'] ?? '').toString();
    final active = card['active'] == true;
    final verified = card['identity_verified'] == true;

    return Scaffold(
      backgroundColor: const Color(0xFFF2F5FA),
      appBar: AppBar(title: const Text('My Digital ID')),
      body: ListView(
        padding: const EdgeInsets.all(18),
        children: [
          Container(
            padding: const EdgeInsets.all(22),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF092D5C), Color(0xFF0A70D8)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(24),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: .16),
                  blurRadius: 18,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Column(
              children: [
                const Text(
                  'ARI SMART RO',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 23,
                    fontWeight: FontWeight.w900,
                    letterSpacing: 1,
                  ),
                ),
                const Text(
                  'OFFICIAL EMPLOYEE IDENTITY',
                  style: TextStyle(color: Colors.white70, fontSize: 11),
                ),
                const SizedBox(height: 18),
                CircleAvatar(
                  radius: 54,
                  backgroundColor: Colors.white,
                  backgroundImage: photo.isNotEmpty ? NetworkImage(photo) : null,
                  child: photo.isEmpty
                      ? const Icon(Icons.person, size: 58)
                      : null,
                ),
                const SizedBox(height: 14),
                Text(
                  (card['name'] ?? '').toString(),
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 22,
                    fontWeight: FontWeight.w900,
                  ),
                ),
                Text(
                  (card['job_title']?.toString().trim().isNotEmpty == true
                          ? card['job_title']
                          : card['designation'])
                      .toString(),
                  style: const TextStyle(color: Colors.white70),
                ),
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: .12),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(
                    'ID: ${card['employee_id']}',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
                const SizedBox(height: 18),
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: QrImageView(
                    data: (card['qr_payload'] ?? '').toString(),
                    size: 150,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  'Verification: ${card['verification_code']}',
                  style: const TextStyle(
                    color: Colors.white70,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 14),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      active && verified
                          ? Icons.verified_user_rounded
                          : Icons.warning_amber_rounded,
                      color: active && verified
                          ? Colors.lightGreenAccent
                          : Colors.amberAccent,
                    ),
                    const SizedBox(width: 8),
                    Text(
                      active && verified
                          ? 'ACTIVE • IDENTITY VERIFIED'
                          : active
                              ? 'ACTIVE • VERIFICATION PENDING'
                              : 'INACTIVE',
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  'Valid until: ${card['valid_until'] ?? 'Not set'}',
                  style: const TextStyle(color: Colors.white70),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Joining readiness',
                    style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900),
                  ),
                  const SizedBox(height: 10),
                  _check('Profile & employment details',
                      onboarding['profile_complete'] == true),
                  _check('Face & attendance device verification',
                      onboarding['security_complete'] == true),
                  _check('Mandatory training',
                      onboarding['training_complete'] == true),
                  const Divider(),
                  Text(
                    'Status: ${onboarding['status'] ?? '-'}',
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ],
              ),
            ),
          ),
          const Padding(
            padding: EdgeInsets.all(12),
            child: Text(
              'Customer verification card never exposes your salary, home address, HR records or other private information.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.black54, fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }

  Widget _check(String label, bool complete) => ListTile(
        dense: true,
        contentPadding: EdgeInsets.zero,
        leading: Icon(
          complete ? Icons.check_circle : Icons.radio_button_unchecked,
          color: complete ? Colors.green : Colors.orange,
        ),
        title: Text(label),
      );
}
