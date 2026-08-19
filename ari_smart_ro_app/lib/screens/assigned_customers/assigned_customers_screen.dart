import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../models/customer_model.dart';
import '../../services/customer_service.dart';
import '../installation/installation_screen.dart';

class AssignedCustomersScreen extends StatefulWidget {
  const AssignedCustomersScreen({super.key});

  @override
  State<AssignedCustomersScreen> createState() =>
      _AssignedCustomersScreenState();
}

class _AssignedCustomersScreenState
    extends State<AssignedCustomersScreen> {
  final CustomerService customerService = CustomerService();

  late Future<List<CustomerModel>> _customersFuture;

  @override
  void initState() {
    super.initState();
    _loadCustomers();
  }

  // ============================================================
  // LOAD ASSIGNED CUSTOMERS
  // ============================================================

  void _loadCustomers() {
    _customersFuture = customerService.getMyCustomers();
  }

  Future<void> _refreshCustomers() async {
    setState(() {
      _loadCustomers();
    });

    await _customersFuture;
  }

  // ============================================================
  // CALL CUSTOMER
  // ============================================================

  Future<void> _makePhoneCall(String phone) async {
    final cleanPhone = phone.trim();

    if (cleanPhone.isEmpty) {
      _showMessage(
        'Customer phone number is not available.',
        Colors.red,
      );
      return;
    }

    final Uri uri = Uri(
      scheme: 'tel',
      path: cleanPhone,
    );

    try {
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      } else {
        _showMessage(
          'Unable to open phone dialer.',
          Colors.red,
        );
      }
    } catch (_) {
      _showMessage(
        'Unable to make phone call.',
        Colors.red,
      );
    }
  }

  // ============================================================
  // OPEN GOOGLE MAPS
  // ============================================================

  Future<void> _openGoogleMaps(
    double? latitude,
    double? longitude,
  ) async {
    // Customer location is not available.
    if (latitude == null || longitude == null) {
      _showMessage(
        'Customer location is not available.',
        Colors.orange,
      );
      return;
    }

    if (latitude == 0 || longitude == 0) {
      _showMessage(
        'Customer location is not available.',
        Colors.orange,
      );
      return;
    }

    final Uri navigationUri = Uri.parse(
      'google.navigation:q=$latitude,$longitude',
    );

    try {
      if (await canLaunchUrl(navigationUri)) {
        await launchUrl(
          navigationUri,
          mode: LaunchMode.externalApplication,
        );
        return;
      }

      // Fallback to Google Maps web URL.
      final Uri webUri = Uri.parse(
        'https://www.google.com/maps/search/?api=1'
        '&query=$latitude,$longitude',
      );

      await launchUrl(
        webUri,
        mode: LaunchMode.externalApplication,
      );
    } catch (_) {
      _showMessage(
        'Unable to open Google Maps.',
        Colors.red,
      );
    }
  }

  // ============================================================
  // MESSAGE
  // ============================================================

  void _showMessage(
    String message,
    Color color,
  ) {
    if (!mounted) return;

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: color,
      ),
    );
  }

  // ============================================================
  // CUSTOMER CARD
  // ============================================================

  Widget _customerCard(CustomerModel customer) {
    return Card(
      margin: const EdgeInsets.only(bottom: 15),
      elevation: 4,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(15),
      ),
      child: Padding(
        padding: const EdgeInsets.all(15),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ----------------------------------------------------
            // CUSTOMER NAME
            // ----------------------------------------------------

            Text(
              customer.customerName,
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 8),

            // ----------------------------------------------------
            // CARD NUMBER
            // ----------------------------------------------------

            Text(
              'Card No : ${customer.cardNumber}',
              style: const TextStyle(
                color: Colors.blue,
                fontWeight: FontWeight.bold,
              ),
            ),

            const SizedBox(height: 10),

            // ----------------------------------------------------
            // PHONE
            // ----------------------------------------------------

            Row(
              children: [
                const Icon(
                  Icons.phone,
                  color: Colors.green,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    customer.phone,
                    style: const TextStyle(
                      fontSize: 15,
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 10),

            // ----------------------------------------------------
            // ADDRESS
            // ----------------------------------------------------

            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(
                  Icons.location_on,
                  color: Colors.red,
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    customer.address,
                    style: const TextStyle(
                      fontSize: 15,
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 18),

            // ----------------------------------------------------
            // CALL + NAVIGATE
            // ----------------------------------------------------

            Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () {
                      _makePhoneCall(customer.phone);
                    },
                    icon: const Icon(Icons.call),
                    label: const Text('Call'),
                  ),
                ),

                const SizedBox(width: 10),

                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: () {
                      _openGoogleMaps(
                        customer.latitude,
                        customer.longitude,
                      );
                    },
                    icon: const Icon(Icons.navigation),
                    label: const Text('Navigate'),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 12),

            // ----------------------------------------------------
            // INSTALLATION
            // ----------------------------------------------------

            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                icon: const Icon(Icons.build),
                label: const Text('Installation'),
                onPressed: () {
                  Navigator.push(
                    context,
                    MaterialPageRoute(
                      builder: (_) => InstallationScreen(
                        customer: customer,
                      ),
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          'Assigned Customers',
        ),
        centerTitle: true,
        backgroundColor: Colors.blue,
        foregroundColor: Colors.white,

        actions: [
          IconButton(
            tooltip: 'Refresh',
            onPressed: () {
              setState(() {
                _loadCustomers();
              });
            },
            icon: const Icon(
              Icons.refresh,
            ),
          ),
        ],
      ),

      // --------------------------------------------------------
      // ASSIGNED CUSTOMER LIST
      // --------------------------------------------------------

      body: FutureBuilder<List<CustomerModel>>(
        future: _customersFuture,

        builder: (context, snapshot) {
          // ----------------------------------------------------
          // LOADING
          // ----------------------------------------------------

          if (snapshot.connectionState ==
              ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          // ----------------------------------------------------
          // ERROR
          // ----------------------------------------------------

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
                      'Unable to load assigned customers.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.bold,
                      ),
                    ),

                    const SizedBox(height: 8),

                    Text(
                      snapshot.error.toString(),
                      textAlign: TextAlign.center,
                      style: const TextStyle(
                        color: Colors.grey,
                      ),
                    ),

                    const SizedBox(height: 20),

                    ElevatedButton.icon(
                      onPressed: () {
                        setState(() {
                          _loadCustomers();
                        });
                      },
                      icon: const Icon(Icons.refresh),
                      label: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            );
          }

          // ----------------------------------------------------
          // DATA
          // ----------------------------------------------------

          final customers = snapshot.data ?? [];

          // ----------------------------------------------------
          // EMPTY
          // ----------------------------------------------------

          if (customers.isEmpty) {
            return RefreshIndicator(
              onRefresh: _refreshCustomers,
              child: ListView(
                physics:
                    const AlwaysScrollableScrollPhysics(),
                children: const [
                  SizedBox(height: 180),

                  Icon(
                    Icons.people_outline,
                    size: 70,
                    color: Colors.grey,
                  ),

                  SizedBox(height: 15),

                  Center(
                    child: Text(
                      'No Customers Assigned',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),

                  SizedBox(height: 8),

                  Center(
                    child: Text(
                      'Customers assigned to you will appear here.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Colors.grey,
                      ),
                    ),
                  ),
                ],
              ),
            );
          }

          // ----------------------------------------------------
          // CUSTOMER LIST
          // ----------------------------------------------------

          return RefreshIndicator(
            onRefresh: _refreshCustomers,
            child: ListView.builder(
              physics:
                  const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(15),
              itemCount: customers.length,
              itemBuilder: (context, index) {
                final customer = customers[index];

                return _customerCard(customer);
              },
            ),
          );
        },
      ),
    );
  }
}