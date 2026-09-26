import 'package:flutter/material.dart';

import '../../models/customer_model.dart';
import '../../services/customer_service.dart';
import '../../services/job_service.dart';
import 'ro_parts_passport_customer_card.dart';

class MyROScreen extends StatefulWidget {
  const MyROScreen({super.key});

  @override
  State<MyROScreen> createState() => _MyROScreenState();
}

class _MyROScreenState extends State<MyROScreen> {
  final CustomerService _customerService = CustomerService();
  final JobService _jobService = JobService();

  late Future<CustomerModel?> _customerFuture;
  late Future<Map<String, dynamic>> _otpFuture;
  late Future<Map<String, dynamic>> _engineerFuture;
  int _passportVersion = 0;

  @override
  void initState() {
    super.initState();
    _reloadFutures();
  }

  void _reloadFutures() {
    _customerFuture = _loadMyRO();
    _otpFuture = _jobService.getCustomerActiveOTP();
    _engineerFuture = _jobService.getCustomerAssignedEngineer();
  }

  Future<CustomerModel?> _loadMyRO() async {
    final customers = await _customerService.getCustomers();
    return customers.isEmpty ? null : customers.first;
  }

  Future<void> _refresh() async {
    if (!mounted) return;
    setState(() {
      _reloadFutures();
      _passportVersion += 1;
    });
    await _customerFuture;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My RO'), centerTitle: true),
      body: FutureBuilder<CustomerModel?>(
        future: _customerFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _errorState(snapshot.error.toString());
          }
          final customer = snapshot.data;
          if (customer == null) return _emptyState();

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _engineerVisitCard(),
                _otpCard(),
                _roHeader(customer),
                const SizedBox(height: 18),
                _sectionTitle('RO Visual Parts Passport', Icons.document_scanner_outlined),
                ROPartsPassportCustomerCard(
                  key: ValueKey<int>(_passportVersion),
                ),
                const SizedBox(height: 18),
                _sectionTitle('Customer Information', Icons.person),
                _infoCard(
                  children: [
                    _infoRow('Customer Name', customer.customerName, Icons.person_outline),
                    _infoRow('Customer ID', customer.customerId, Icons.badge_outlined),
                    _infoRow('Phone', customer.phone, Icons.phone_outlined),
                  ],
                ),
                const SizedBox(height: 18),
                _sectionTitle('RO Information', Icons.water_drop_outlined),
                _infoCard(
                  children: [
                    _infoRow('Card Number', customer.cardNumber, Icons.credit_card),
                    _infoRow(
                      'RO Model',
                      customer.roModel.isEmpty ? 'Not Available' : customer.roModel,
                      Icons.water,
                    ),
                    _infoRow(
                      'Installation Charge',
                      '₹${customer.installationCharge}',
                      Icons.payments_outlined,
                    ),
                    _infoRow(
                      'Monthly Rent',
                      '₹${customer.monthlyRent}',
                      Icons.currency_rupee,
                    ),
                    _infoRow(
                      'Ownership',
                      customer.ownershipType,
                      Icons.inventory_2_outlined,
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                _sectionTitle('RO Location', Icons.location_on),
                _infoCard(
                  children: [
                    _infoRow('Address', customer.address, Icons.home_outlined),
                    _infoRow(
                      'Area',
                      customer.area.isEmpty ? 'Not Available' : customer.area,
                      Icons.location_city,
                    ),
                    _infoRow(
                      'City',
                      customer.city.isEmpty ? 'Not Available' : customer.city,
                      Icons.apartment_outlined,
                    ),
                  ],
                ),
                const SizedBox(height: 18),
                _statusCard(customer),
                const SizedBox(height: 24),
                SizedBox(
                  height: 50,
                  child: ElevatedButton.icon(
                    onPressed: _refresh,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Refresh RO Details'),
                  ),
                ),
                const SizedBox(height: 24),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _engineerVisitCard() {
    return FutureBuilder<Map<String, dynamic>>(
      future: _engineerFuture,
      builder: (context, snapshot) {
        final data = snapshot.data;
        if (data == null || data['available'] != true) {
          return const SizedBox.shrink();
        }
        final engineer = Map<String, dynamic>.from(
          data['engineer'] as Map? ?? const {},
        );
        final photo = (engineer['photo'] ?? '').toString();
        final identityVerified =
            engineer['identity_verified'] == true && engineer['active'] == true;
        final title = (engineer['job_title'] ?? '').toString().trim();
        final designation = title.isNotEmpty
            ? title
            : (engineer['designation'] ?? '').toString();
        return Container(
          width: double.infinity,
          margin: const EdgeInsets.only(bottom: 18),
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            border: Border.all(
              color: identityVerified
                  ? Colors.green.withValues(alpha: .45)
                  : Colors.orange.withValues(alpha: .45),
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    radius: 32,
                    backgroundImage: photo.isNotEmpty ? NetworkImage(photo) : null,
                    child: photo.isEmpty ? const Icon(Icons.engineering, size: 30) : null,
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'YOUR ARI ENGINEER',
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w900,
                            color: Colors.blue,
                          ),
                        ),
                        Text(
                          (engineer['name'] ?? '').toString(),
                          style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900),
                        ),
                        if (designation.isNotEmpty) Text(designation),
                      ],
                    ),
                  ),
                  Icon(
                    identityVerified ? Icons.verified_user_rounded : Icons.warning_amber_rounded,
                    color: identityVerified ? Colors.green : Colors.orange,
                    size: 30,
                  ),
                ],
              ),
              const Divider(height: 26),
              _infoRow(
                'Employee ID',
                (engineer['employee_id'] ?? '').toString(),
                Icons.badge_outlined,
              ),
              _infoRow(
                'Job',
                '${data['job_number'] ?? ''} • ${data['job_type'] ?? ''}',
                Icons.work_outline,
              ),
              _infoRow(
                'Visit status',
                (data['job_status'] ?? '').toString().replaceAll('_', ' '),
                Icons.route_outlined,
              ),
              _infoRow(
                'Verification code',
                (engineer['verification_code'] ?? '').toString(),
                Icons.verified_outlined,
              ),
              const SizedBox(height: 8),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: (identityVerified ? Colors.green : Colors.orange)
                      .withValues(alpha: .08),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  identityVerified
                      ? 'Official ARI employee identity verified. Match the photo and Employee ID before sharing the service OTP.'
                      : 'Employee is assigned, but identity verification is pending. Contact ARI Admin before sharing OTP if unsure.',
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: identityVerified ? Colors.green.shade800 : Colors.orange.shade900,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _otpCard() {
    return FutureBuilder<Map<String, dynamic>>(
      future: _otpFuture,
      builder: (context, snapshot) {
        final data = snapshot.data;
        if (data == null || data['available'] != true) {
          return const SizedBox.shrink();
        }
        return Container(
          width: double.infinity,
          margin: const EdgeInsets.only(bottom: 18),
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.primaryContainer,
            borderRadius: BorderRadius.circular(16),
          ),
          child: Column(
            children: [
              const Text('SERVICE OTP', style: TextStyle(fontWeight: FontWeight.w800)),
              const SizedBox(height: 8),
              Text(
                data['otp']?.toString() ?? '',
                style: const TextStyle(
                  fontSize: 34,
                  fontWeight: FontWeight.w900,
                  letterSpacing: 8,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                "Job ${data['job_number'] ?? ''} • Share this OTP only with your ARI engineer.",
                textAlign: TextAlign.center,
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _roHeader(CustomerModel customer) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF0F4C81), Color(0xFF2196F3)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(18),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: .12),
            blurRadius: 12,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      child: Column(
        children: [
          const Icon(Icons.water_drop, size: 68, color: Colors.white),
          const SizedBox(height: 8),
          const Text(
            'MY RO SYSTEM',
            style: TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          Text(
            customer.cardNumber,
            style: const TextStyle(color: Colors.white, fontSize: 16),
          ),
        ],
      ),
    );
  }

  Widget _statusCard(CustomerModel customer) {
    final active = customer.isActive;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: (active ? Colors.green : Colors.red).withValues(alpha: .08),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: (active ? Colors.green : Colors.red).withValues(alpha: .3),
        ),
      ),
      child: Row(
        children: [
          Icon(
            active ? Icons.check_circle : Icons.cancel_outlined,
            color: active ? Colors.green : Colors.red,
            size: 32,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  active ? 'RO ACTIVE' : 'RO INACTIVE',
                  style: TextStyle(
                    color: active ? Colors.green : Colors.red,
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  active
                      ? 'Your ARI RO account is active.'
                      : (customer.deactivationReason.isEmpty
                          ? 'This RO account is inactive.'
                          : customer.deactivationReason),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionTitle(String title, IconData icon) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, color: Colors.blue),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              title,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ),
        ],
      ),
    );
  }

  Widget _infoCard({required List<Widget> children}) {
    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(children: children),
      ),
    );
  }

  Widget _infoRow(String title, String value, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: Colors.blue, size: 22),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(color: Colors.grey, fontSize: 13)),
                const SizedBox(height: 2),
                Text(
                  value.trim().isEmpty ? 'Not Available' : value,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _errorState(String error) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.error_outline, size: 60, color: Colors.red),
            const SizedBox(height: 15),
            const Text(
              'Unable to load your RO details.',
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            Text(error, textAlign: TextAlign.center),
            const SizedBox(height: 20),
            ElevatedButton.icon(
              onPressed: _refresh,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _emptyState() {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        children: const [
          SizedBox(height: 180),
          Icon(Icons.water_drop_outlined, size: 70, color: Colors.blue),
          SizedBox(height: 20),
          Center(
            child: Text(
              'No RO assigned to your account.',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ),
          SizedBox(height: 10),
          Center(child: Text('Pull down to refresh.')),
        ],
      ),
    );
  }
}
