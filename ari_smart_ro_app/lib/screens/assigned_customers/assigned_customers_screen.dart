import 'dart:async';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../models/customer_model.dart';
import '../../services/customer_service.dart';
import '../../services/work_planner_service.dart';
import '../../utils/search_utils.dart';
import '../installation/installation_screen.dart';

class AssignedCustomersScreen extends StatefulWidget {
  const AssignedCustomersScreen({super.key});

  @override
  State<AssignedCustomersScreen> createState() =>
      _AssignedCustomersScreenState();
}

class _AssignedCustomersScreenState extends State<AssignedCustomersScreen>
    with WidgetsBindingObserver {
  final CustomerService customerService = CustomerService();
  final WorkPlannerService _workPlannerService = WorkPlannerService();

  late Future<List<CustomerModel>> _customersFuture;
  Timer? _refreshTimer;
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  _AssignedCustomerFilter _filter = _AssignedCustomerFilter.all;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _loadCustomers();
    _refreshTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) _refreshCustomers();
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && mounted) {
      _refreshCustomers();
    }
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    _searchController.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  List<CustomerModel> _filteredCustomers(List<CustomerModel> customers) {
    return customers.where((customer) {
      final monthlyRent = double.tryParse(customer.monthlyRent) ?? 0;
      final matchesFilter = switch (_filter) {
        _AssignedCustomerFilter.all => true,
        _AssignedCustomerFilter.rent => monthlyRent > 0,
        _AssignedCustomerFilter.locationMissing =>
          customer.latitude == 0 || customer.longitude == 0,
      };
      return matchesFilter &&
          matchesAllSearchTerms(_searchQuery, [
            customer.customerName,
            customer.customerId,
            customer.phone,
            customer.cardNumber,
            customer.oldCardNumber,
            customer.area,
            customer.address,
            customer.roModel,
          ]);
    }).toList();
  }

  Widget _searchAndFilters(int resultCount) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          TextField(
            controller: _searchController,
            onChanged: (value) => setState(() => _searchQuery = value),
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              hintText: 'Search name, ID, phone, card, area or RO model...',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _searchQuery.isEmpty
                  ? null
                  : IconButton(
                      tooltip: 'Clear search',
                      onPressed: () {
                        _searchController.clear();
                        setState(() => _searchQuery = '');
                      },
                      icon: const Icon(Icons.clear),
                    ),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
              ),
            ),
          ),
          const SizedBox(height: 10),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: _AssignedCustomerFilter.values.map((filter) {
                return Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: ChoiceChip(
                    label: Text(filter.label),
                    selected: _filter == filter,
                    onSelected: (_) => setState(() => _filter = filter),
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            '$resultCount assigned customer${resultCount == 1 ? '' : 's'} found',
            style: TextStyle(
              color: Colors.grey.shade700,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
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
    final cleanPhone = phone.trim().replaceAll(RegExp(r'[^0-9+]'), '');

    if (cleanPhone.isEmpty) {
      _showMessage('Customer phone number is not available.', Colors.red);
      return;
    }

    final Uri uri = Uri(scheme: 'tel', path: cleanPhone);

    try {
      final opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!opened) {
        _showMessage('Unable to open phone dialer.', Colors.red);
      }
    } catch (_) {
      _showMessage('Unable to make phone call.', Colors.red);
    }
  }

  // ============================================================
  // OPEN GOOGLE MAPS
  // ============================================================

  Future<void> _openGoogleMaps(double? latitude, double? longitude) async {
    // Customer location is not available.
    if (latitude == null || longitude == null) {
      _showMessage('Customer location is not available.', Colors.orange);
      return;
    }

    if (latitude == 0 || longitude == 0) {
      _showMessage('Customer location is not available.', Colors.orange);
      return;
    }

    final Uri navigationUri = Uri.parse(
      'google.navigation:q=$latitude,$longitude',
    );

    try {
      if (await canLaunchUrl(navigationUri)) {
        await launchUrl(navigationUri, mode: LaunchMode.externalApplication);
        return;
      }

      // Fallback to Google Maps web URL.
      final Uri webUri = Uri.parse(
        'https://www.google.com/maps/search/?api=1'
        '&query=$latitude,$longitude',
      );

      await launchUrl(webUri, mode: LaunchMode.externalApplication);
    } catch (_) {
      _showMessage('Unable to open Google Maps.', Colors.red);
    }
  }

  Future<void> _captureCustomerLocation(CustomerModel customer) async {
    if (customer.latitude != 0 && customer.longitude != 0) return;
    if (!await Geolocator.isLocationServiceEnabled()) {
      _showMessage('Please enable phone location service.', Colors.orange);
      return;
    }
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      _showMessage('Location permission is required.', Colors.red);
      return;
    }
    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 20),
      ),
    );
    if (!mounted) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Save customer location?'),
        content: Text(
          '${customer.customerName}\n\nAccuracy: ±${position.accuracy.toStringAsFixed(1)} metres\nConfirm that you are at the customer site.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Save'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await _workPlannerService.saveCustomerLocation(
        customerId: customer.id,
        latitude: position.latitude,
        longitude: position.longitude,
        accuracy: position.accuracy,
      );
      await _refreshCustomers();
      _showMessage('Customer location saved successfully.', Colors.green);
    } catch (e) {
      _showMessage(e.toString().replaceFirst('Exception: ', ''), Colors.red);
    }
  }

  // ============================================================
  // MESSAGE
  // ============================================================

  void _showMessage(String message, Color color) {
    if (!mounted) return;

    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text(message), backgroundColor: color));
  }

  // ============================================================
  // CUSTOMER CARD
  // ============================================================

  Widget _customerCard(CustomerModel customer) {
    return Card(
      margin: const EdgeInsets.only(bottom: 15),
      elevation: 4,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(15)),
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
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
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
                const Icon(Icons.phone, color: Colors.green),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    customer.phone,
                    style: const TextStyle(fontSize: 15),
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
                const Icon(Icons.location_on, color: Colors.red),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    customer.address,
                    style: const TextStyle(fontSize: 15),
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
                      _openGoogleMaps(customer.latitude, customer.longitude);
                    },
                    icon: const Icon(Icons.navigation),
                    label: const Text('Navigate'),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 12),

            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: customer.latitude != 0 && customer.longitude != 0
                    ? null
                    : () => _captureCustomerLocation(customer),
                icon: Icon(
                  customer.latitude != 0 && customer.longitude != 0
                      ? Icons.location_on
                      : Icons.add_location_alt_outlined,
                ),
                label: Text(
                  customer.latitude != 0 && customer.longitude != 0
                      ? 'Location Saved'
                      : 'Save Customer Location',
                ),
              ),
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
                      builder: (_) => InstallationScreen(customer: customer),
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
        title: const Text('Assigned Customers'),
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
            icon: const Icon(Icons.refresh),
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

          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }

          // ----------------------------------------------------
          // ERROR
          // ----------------------------------------------------

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
                      style: const TextStyle(color: Colors.grey),
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
                physics: const AlwaysScrollableScrollPhysics(),
                children: const [
                  SizedBox(height: 180),

                  Icon(Icons.people_outline, size: 70, color: Colors.grey),

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
                      style: TextStyle(color: Colors.grey),
                    ),
                  ),
                ],
              ),
            );
          }

          // ----------------------------------------------------
          // CUSTOMER LIST
          // ----------------------------------------------------

          final filtered = _filteredCustomers(customers);

          return RefreshIndicator(
            onRefresh: _refreshCustomers,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              padding: const EdgeInsets.all(15),
              children: [
                _searchAndFilters(filtered.length),
                if (filtered.isEmpty)
                  const Padding(
                    padding: EdgeInsets.only(top: 70),
                    child: Center(child: Text('No matching customer found.')),
                  )
                else
                  ...filtered.map(_customerCard),
              ],
            ),
          );
        },
      ),
    );
  }
}

enum _AssignedCustomerFilter {
  all('All'),
  rent('Rent Customers'),
  locationMissing('Location Missing');

  const _AssignedCustomerFilter(this.label);
  final String label;
}
