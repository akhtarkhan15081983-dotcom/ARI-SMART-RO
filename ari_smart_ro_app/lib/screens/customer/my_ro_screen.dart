import 'package:flutter/material.dart';

import '../../models/customer_model.dart';
import '../../services/customer_service.dart';
import '../../services/job_service.dart';

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

  @override
  void initState() {
    super.initState();

    _customerFuture = _loadMyRO();
    _otpFuture = _jobService.getCustomerActiveOTP();
    _engineerFuture = _jobService.getCustomerAssignedEngineer();
  }

  // ============================================================
  // LOAD CUSTOMER RO
  // ============================================================

  Future<CustomerModel?> _loadMyRO() async {
    final customers = await _customerService.getCustomers();

    if (customers.isEmpty) {
      return null;
    }

    return customers.first;
  }

  // ============================================================
  // REFRESH
  // ============================================================

  Future<void> _refresh() async {
    setState(() {
      _customerFuture = _loadMyRO();
      _otpFuture = _jobService.getCustomerActiveOTP();
      _engineerFuture = _jobService.getCustomerAssignedEngineer();
    });

    await _customerFuture;
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("My RO"), centerTitle: true),

      body: FutureBuilder<CustomerModel?>(
        future: _customerFuture,

        builder: (context, snapshot) {
          // ======================================================
          // LOADING
          // ======================================================

          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          // ======================================================
          // ERROR
          // ======================================================

          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Icon(
                      Icons.error_outline,
                      size: 60,
                      color: Colors.red,
                    ),

                    const SizedBox(height: 15),

                    const Text(
                      "Unable to load your RO details.",
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),

                    const SizedBox(height: 10),

                    Text(
                      snapshot.error.toString(),
                      textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.grey),
                    ),

                    const SizedBox(height: 20),

                    ElevatedButton.icon(
                      onPressed: _refresh,
                      icon: const Icon(Icons.refresh),
                      label: const Text("Retry"),
                    ),
                  ],
                ),
              ),
            );
          }

          // ======================================================
          // NO CUSTOMER
          // ======================================================

          final customer = snapshot.data;

          if (customer == null) {
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
                      "No RO assigned to your account.",
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),

                  SizedBox(height: 10),

                  Center(
                    child: Text(
                      "Pull down to refresh.",
                      style: TextStyle(color: Colors.grey),
                    ),
                  ),
                ],
              ),
            );
          }

          // ======================================================
          // CUSTOMER DATA
          // ======================================================

          return RefreshIndicator(
            onRefresh: _refresh,

            child: ListView(
              padding: const EdgeInsets.all(16),

              children: [
                FutureBuilder<Map<String, dynamic>>(
                  future: _engineerFuture,
                  builder: (context, engineerSnapshot) {
                    final data = engineerSnapshot.data;
                    if (data == null || data['available'] != true) {
                      return const SizedBox.shrink();
                    }
                    final engineer = Map<String, dynamic>.from(
                      data['engineer'] as Map? ?? const {},
                    );
                    final photo = (engineer['photo'] ?? '').toString();
                    final identityVerified =
                        engineer['identity_verified'] == true &&
                        engineer['active'] == true;
                    return Container(
                      width: double.infinity,
                      margin: const EdgeInsets.only(bottom: 18),
                      padding: const EdgeInsets.all(18),
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(18),
                        border: Border.all(
                          color: identityVerified
                              ? Colors.green.withValues(alpha: .45)
                              : Colors.orange.withValues(alpha: .45),
                        ),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withValues(alpha: .07),
                            blurRadius: 12,
                            offset: const Offset(0, 5),
                          ),
                        ],
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              CircleAvatar(
                                radius: 34,
                                backgroundImage:
                                    photo.isNotEmpty ? NetworkImage(photo) : null,
                                child: photo.isEmpty
                                    ? const Icon(Icons.engineering, size: 32)
                                    : null,
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
                                    const SizedBox(height: 3),
                                    Text(
                                      (engineer['name'] ?? '').toString(),
                                      style: const TextStyle(
                                        fontSize: 19,
                                        fontWeight: FontWeight.w900,
                                      ),
                                    ),
                                    Text(
                                      (engineer['job_title']
                                                  ?.toString()
                                                  .trim()
                                                  .isNotEmpty ==
                                              true
                                          ? engineer['job_title']
                                          : engineer['designation'])
                                      .toString(),
                                    ),
                                  ],
                                ),
                              ),
                              Icon(
                                identityVerified
                                    ? Icons.verified_user_rounded
                                    : Icons.warning_amber_rounded,
                                color: identityVerified
                                    ? Colors.green
                                    : Colors.orange,
                                size: 30,
                              ),
                            ],
                          ),
                          const Divider(height: 28),
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
                              color: identityVerified
                                  ? Colors.green.withValues(alpha: .08)
                                  : Colors.orange.withValues(alpha: .08),
                              borderRadius: BorderRadius.circular(12),
                            ),
                            child: Text(
                              identityVerified
                                  ? 'Official ARI employee identity verified. Match the photo and Employee ID before sharing the service OTP.'
                                  : 'Employee is assigned to your job, but identity verification is pending. Contact ARI Admin before sharing OTP if you are unsure.',
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                color: identityVerified
                                    ? Colors.green.shade800
                                    : Colors.orange.shade900,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ),
                        ],
                      ),
                    );
                  },
                ),

                FutureBuilder<Map<String, dynamic>>(
                  future: _otpFuture,
                  builder: (context, otpSnapshot) {
                    final data = otpSnapshot.data;
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
                          const Text(
                            'SERVICE OTP',
                            style: TextStyle(fontWeight: FontWeight.w800),
                          ),
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
                ),

                // ==================================================
                // RO HEADER
                // ==================================================
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(20),

                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF2196F3), Color(0xFF42A5F5)],

                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),

                    borderRadius: BorderRadius.circular(18),

                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.15),
                        blurRadius: 10,
                        offset: const Offset(0, 5),
                      ),
                    ],
                  ),

                  child: Column(
                    children: [
                      const Icon(
                        Icons.water_drop,
                        size: 70,
                        color: Colors.white,
                      ),

                      const SizedBox(height: 10),

                      const Text(
                        "MY RO SYSTEM",
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 24,
                          fontWeight: FontWeight.bold,
                        ),
                      ),

                      const SizedBox(height: 5),

                      Text(
                        customer.cardNumber,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 20),

                // ==================================================
                // CUSTOMER INFORMATION
                // ==================================================
                _sectionTitle("Customer Information", Icons.person),

                _infoCard(
                  children: [
                    _infoRow(
                      "Customer Name",
                      customer.customerName,
                      Icons.person_outline,
                    ),

                    _infoRow(
                      "Customer ID",
                      customer.customerId,
                      Icons.badge_outlined,
                    ),

                    _infoRow("Phone", customer.phone, Icons.phone_outlined),
                  ],
                ),

                const SizedBox(height: 18),

                // ==================================================
                // RO INFORMATION
                // ==================================================
                _sectionTitle("RO Information", Icons.water_drop_outlined),

                _infoCard(
                  children: [
                    _infoRow(
                      "Card Number",
                      customer.cardNumber,
                      Icons.credit_card,
                    ),

                    _infoRow(
                      "RO Model",
                      customer.roModel.isEmpty
                          ? "Not Available"
                          : customer.roModel,
                      Icons.water,
                    ),

                    _infoRow(
                      "Installation Charge",
                      "₹${customer.installationCharge}",
                      Icons.payments_outlined,
                    ),

                    _infoRow(
                      "Monthly Rent",
                      "₹${customer.monthlyRent}",
                      Icons.currency_rupee,
                    ),
                  ],
                ),

                const SizedBox(height: 18),

                // ==================================================
                // ASSIGNED ENGINEER
                // ==================================================
                _sectionTitle("Service Engineer", Icons.engineering),

                FutureBuilder<Map<String, dynamic>>(
                  future: _engineerFuture,
                  builder: (context, engineerSnapshot) {
                    final data = engineerSnapshot.data;
                    final available = data != null && data['available'] == true;
                    return _infoCard(
                      children: [
                        _infoRow(
                          "Engineer Assignment",
                          available
                              ? "Assigned • Verify using the official card above"
                              : "No active engineer visit assigned",
                          Icons.engineering,
                        ),
                      ],
                    );
                  },
                ),

                const SizedBox(height: 18),

                // ==================================================
                // ADDRESS
                // ==================================================
                _sectionTitle("RO Location", Icons.location_on),

                _infoCard(
                  children: [
                    _infoRow("Address", customer.address, Icons.home_outlined),

                    _infoRow(
                      "Area",
                      customer.area.isEmpty ? "Not Available" : customer.area,
                      Icons.location_city,
                    ),
                  ],
                ),

                const SizedBox(height: 18),

                // ==================================================
                // STATUS
                // ==================================================
                _sectionTitle("RO Status", Icons.check_circle),

                Container(
                  padding: const EdgeInsets.all(18),

                  decoration: BoxDecoration(
                    color: Colors.green.withValues(alpha: 0.08),

                    borderRadius: BorderRadius.circular(14),

                    border: Border.all(
                      color: Colors.green.withValues(alpha: 0.3),
                    ),
                  ),

                  child: const Row(
                    children: [
                      Icon(Icons.check_circle, color: Colors.green, size: 32),

                      SizedBox(width: 12),

                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              "RO ACTIVE",
                              style: TextStyle(
                                color: Colors.green,
                                fontSize: 18,
                                fontWeight: FontWeight.bold,
                              ),
                            ),

                            SizedBox(height: 4),

                            Text(
                              "Your RO rental system is active.",
                              style: TextStyle(color: Colors.grey),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 30),

                // ==================================================
                // REFRESH BUTTON
                // ==================================================
                SizedBox(
                  width: double.infinity,
                  height: 50,

                  child: ElevatedButton.icon(
                    onPressed: _refresh,

                    icon: const Icon(Icons.refresh),

                    label: const Text("Refresh RO Details"),

                    style: ElevatedButton.styleFrom(
                      backgroundColor: Colors.blue,

                      foregroundColor: Colors.white,

                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12),
                      ),
                    ),
                  ),
                ),

                const SizedBox(height: 20),
              ],
            ),
          );
        },
      ),
    );
  }

  // ============================================================
  // SECTION TITLE
  // ============================================================

  Widget _sectionTitle(String title, IconData icon) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),

      child: Row(
        children: [
          Icon(icon, color: Colors.blue),

          const SizedBox(width: 8),

          Text(
            title,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }

  // ============================================================
  // INFO CARD
  // ============================================================

  Widget _infoCard({required List<Widget> children}) {
    return Card(
      elevation: 3,

      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),

      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(children: children),
      ),
    );
  }

  // ============================================================
  // INFO ROW
  // ============================================================

  Widget _infoRow(String title, String value, IconData icon) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),

      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,

        children: [
          Icon(icon, color: Colors.blue, size: 23),

          const SizedBox(width: 12),

          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,

              children: [
                Text(
                  title,
                  style: const TextStyle(color: Colors.grey, fontSize: 13),
                ),

                const SizedBox(height: 2),

                Text(
                  value.isEmpty ? "Not Available" : value,

                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
