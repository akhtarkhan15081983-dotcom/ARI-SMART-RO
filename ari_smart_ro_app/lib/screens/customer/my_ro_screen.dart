import 'package:flutter/material.dart';

import '../../models/customer_model.dart';
import '../../services/customer_service.dart';

class MyROScreen extends StatefulWidget {
  const MyROScreen({super.key});

  @override
  State<MyROScreen> createState() => _MyROScreenState();
}

class _MyROScreenState extends State<MyROScreen> {
  final CustomerService _customerService = CustomerService();

  late Future<CustomerModel?> _customerFuture;

  @override
  void initState() {
    super.initState();

    _customerFuture = _loadMyRO();
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
    });

    await _customerFuture;
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("My RO"),
        centerTitle: true,
      ),

      body: FutureBuilder<CustomerModel?>(
        future: _customerFuture,

        builder: (context, snapshot) {
          // ======================================================
          // LOADING
          // ======================================================

          if (snapshot.connectionState ==
              ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          // ======================================================
          // ERROR
          // ======================================================

          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  mainAxisAlignment:
                      MainAxisAlignment.center,
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
                      style: const TextStyle(
                        color: Colors.grey,
                      ),
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
                physics:
                    const AlwaysScrollableScrollPhysics(),
                children: const [
                  SizedBox(height: 180),

                  Icon(
                    Icons.water_drop_outlined,
                    size: 70,
                    color: Colors.blue,
                  ),

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
                      style: TextStyle(
                        color: Colors.grey,
                      ),
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
                // ==================================================
                // RO HEADER
                // ==================================================

                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(20),

                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [
                        Color(0xFF2196F3),
                        Color(0xFF42A5F5),
                      ],

                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),

                    borderRadius:
                        BorderRadius.circular(18),

                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.15),
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

                _sectionTitle(
                  "Customer Information",
                  Icons.person,
                ),

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

                    _infoRow(
                      "Phone",
                      customer.phone,
                      Icons.phone_outlined,
                    ),
                  ],
                ),

                const SizedBox(height: 18),

                // ==================================================
                // RO INFORMATION
                // ==================================================

                _sectionTitle(
                  "RO Information",
                  Icons.water_drop_outlined,
                ),

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

                _sectionTitle(
                  "Service Engineer",
                  Icons.engineering,
                ),

                _infoCard(
                  children: [
                    _infoRow(
                      "Engineer",
                      customer.assignedEngineer != null &&
                              customer.engineerName.isNotEmpty
                          ? customer.engineerName
                          : "Not Assigned",
                      Icons.engineering,
                    ),

                    if (customer.assignedEngineer == null)
                      const Padding(
                        padding: EdgeInsets.only(
                          top: 8,
                        ),
                        child: Row(
                          children: [
                            Icon(
                              Icons.info_outline,
                              color: Colors.orange,
                              size: 20,
                            ),

                            SizedBox(width: 8),

                            Expanded(
                              child: Text(
                                "Your service engineer has not been assigned yet.",
                                style: TextStyle(
                                  color: Colors.orange,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),

                const SizedBox(height: 18),

                // ==================================================
                // ADDRESS
                // ==================================================

                _sectionTitle(
                  "RO Location",
                  Icons.location_on,
                ),

                _infoCard(
                  children: [
                    _infoRow(
                      "Address",
                      customer.address,
                      Icons.home_outlined,
                    ),

                    _infoRow(
                      "Area",
                      customer.area.isEmpty
                          ? "Not Available"
                          : customer.area,
                      Icons.location_city,
                    ),
                  ],
                ),

                const SizedBox(height: 18),

                // ==================================================
                // STATUS
                // ==================================================

                _sectionTitle(
                  "RO Status",
                  Icons.check_circle,
                ),

                Container(
                  padding: const EdgeInsets.all(18),

                  decoration: BoxDecoration(
                    color: Colors.green.withOpacity(0.08),

                    borderRadius:
                        BorderRadius.circular(14),

                    border: Border.all(
                      color: Colors.green.withOpacity(0.3),
                    ),
                  ),

                  child: const Row(
                    children: [
                      Icon(
                        Icons.check_circle,
                        color: Colors.green,
                        size: 32,
                      ),

                      SizedBox(width: 12),

                      Expanded(
                        child: Column(
                          crossAxisAlignment:
                              CrossAxisAlignment.start,
                          children: [
                            Text(
                              "RO ACTIVE",
                              style: TextStyle(
                                color: Colors.green,
                                fontSize: 18,
                                fontWeight:
                                    FontWeight.bold,
                              ),
                            ),

                            SizedBox(height: 4),

                            Text(
                              "Your RO rental system is active.",
                              style: TextStyle(
                                color: Colors.grey,
                              ),
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

                    icon: const Icon(
                      Icons.refresh,
                    ),

                    label: const Text(
                      "Refresh RO Details",
                    ),

                    style:
                        ElevatedButton.styleFrom(
                      backgroundColor:
                          Colors.blue,

                      foregroundColor:
                          Colors.white,

                      shape:
                          RoundedRectangleBorder(
                        borderRadius:
                            BorderRadius.circular(
                          12,
                        ),
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

  Widget _sectionTitle(
    String title,
    IconData icon,
  ) {
    return Padding(
      padding: const EdgeInsets.only(
        bottom: 8,
      ),

      child: Row(
        children: [
          Icon(
            icon,
            color: Colors.blue,
          ),

          const SizedBox(width: 8),

          Text(
            title,
            style: const TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      ),
    );
  }

  // ============================================================
  // INFO CARD
  // ============================================================

  Widget _infoCard({
    required List<Widget> children,
  }) {
    return Card(
      elevation: 3,

      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(14),
      ),

      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          children: children,
        ),
      ),
    );
  }

  // ============================================================
  // INFO ROW
  // ============================================================

  Widget _infoRow(
    String title,
    String value,
    IconData icon,
  ) {
    return Padding(
      padding: const EdgeInsets.symmetric(
        vertical: 9,
      ),

      child: Row(
        crossAxisAlignment:
            CrossAxisAlignment.start,

        children: [
          Icon(
            icon,
            color: Colors.blue,
            size: 23,
          ),

          const SizedBox(width: 12),

          Expanded(
            child: Column(
              crossAxisAlignment:
                  CrossAxisAlignment.start,

              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.grey,
                    fontSize: 13,
                  ),
                ),

                const SizedBox(height: 2),

                Text(
                  value.isEmpty
                      ? "Not Available"
                      : value,

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