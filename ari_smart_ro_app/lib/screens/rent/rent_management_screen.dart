import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../models/rent_management_model.dart';
import '../../services/rent_management_service.dart';
import '../../utils/search_utils.dart';

class RentManagementScreen extends StatefulWidget {
  const RentManagementScreen({super.key});

  @override
  State<RentManagementScreen> createState() => _RentManagementScreenState();
}

class _RentManagementScreenState extends State<RentManagementScreen> {
  bool _isLoading = true;
  String? _error;
  List<RentManagementCustomer> _customers = [];
  final TextEditingController _searchController = TextEditingController();
  String _searchQuery = '';
  String _bucketFilter = 'TODAY';
  String _areaFilter = 'ALL';

  @override
  void initState() {
    super.initState();
    _loadRentManagement();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadRentManagement() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }
    try {
      final response = await RentManagementService.getRentManagement();
      final raw = (response['customers'] ?? const []) as List;
      final customers = raw
          .whereType<Map>()
          .map((e) => RentManagementCustomer.fromJson(Map<String, dynamic>.from(e)))
          .toList();
      if (!mounted) return;
      setState(() {
        _customers = customers;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _error = e.toString().replaceFirst('Exception: ', '');
      });
    }
  }

  Future<void> _refresh() => _loadRentManagement();

  List<RentManagementCustomer> get _filteredCustomers {
    final rows = _customers.where((customer) {
      final bucketMatch =
          _bucketFilter == 'ALL' || customer.collectionBucket == _bucketFilter;
      final areaMatch = _areaFilter == 'ALL' || customer.areaLabel == _areaFilter;
      final searchMatch = matchesAllSearchTerms(_searchQuery, [
        customer.name,
        customer.customerId,
        customer.phone,
        customer.cardNumber,
        customer.oldCardNumber,
        customer.area,
        customer.address,
        customer.city,
        customer.roModel,
        customer.status,
        customer.dueDate,
      ]);
      return bucketMatch && areaMatch && searchMatch;
    }).toList();

    rows.sort((a, b) {
      final due = a.dueDate.compareTo(b.dueDate);
      if (due != 0) return due;
      return a.name.toLowerCase().compareTo(b.name.toLowerCase());
    });
    return rows;
  }

  int _count(String bucket) =>
      _customers.where((e) => e.collectionBucket == bucket).length;

  double get _totalBalance =>
      _customers.fold(0, (sum, customer) => sum + customer.balance);

  double get _totalPaid =>
      _customers.fold(0, (sum, customer) => sum + customer.paidAmount);

  List<String> get _areas {
    final values = _customers.map((e) => e.areaLabel).toSet().toList()..sort();
    return ['ALL', ...values];
  }

  Future<void> _openCustomerDetails(RentManagementCustomer customer) async {
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute(
        builder: (_) => RentCustomerDetailsScreen(customer: customer),
      ),
    );
    if (changed == true && mounted) await _refresh();
  }

  Future<void> _scanCustomerQr() async {
    final customer = await Navigator.push<RentManagementCustomer>(
      context,
      MaterialPageRoute(
        builder: (_) => _RentCustomerQrScanner(customers: _customers),
      ),
    );
    if (customer != null && mounted) {
      await _openCustomerDetails(customer);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Digital Rent Collection'),
        centerTitle: true,
        actions: [
          IconButton(
            tooltip: 'Scan customer QR',
            onPressed: _isLoading ? null : _scanCustomerQr,
            icon: const Icon(Icons.qr_code_scanner),
          ),
          IconButton(
            tooltip: 'Refresh',
            onPressed: _isLoading ? null : _refresh,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isLoading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, size: 56),
              const SizedBox(height: 12),
              Text(_error!, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _refresh,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _refresh,
      child: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          _buildCollectionHeader(),
          const SizedBox(height: 12),
          _buildBucketStrip(),
          const SizedBox(height: 12),
          _buildSearchAndArea(),
          const SizedBox(height: 12),
          _buildCustomerList(),
        ],
      ),
    );
  }

  Widget _buildCollectionHeader() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Collection Desk',
              style: Theme.of(context)
                  .textTheme
                  .titleLarge
                  ?.copyWith(fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 4),
            const Text(
              'Assigned customers only • due-date driven • card/QR searchable',
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Expanded(
                  child: _metricTile(
                    'Customers',
                    _customers.length.toString(),
                    Icons.people_alt_outlined,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _metricTile(
                    'Collected',
                    '₹${_totalPaid.toStringAsFixed(0)}',
                    Icons.payments_outlined,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _metricTile(
                    'Balance',
                    '₹${_totalBalance.toStringAsFixed(0)}',
                    Icons.account_balance_wallet_outlined,
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _metricTile(String title, String value, IconData icon) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Theme.of(context).dividerColor),
      ),
      child: Column(
        children: [
          Icon(icon, size: 22),
          const SizedBox(height: 6),
          Text(
            value,
            textAlign: TextAlign.center,
            style: const TextStyle(fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 2),
          Text(title, style: const TextStyle(fontSize: 11)),
        ],
      ),
    );
  }

  Widget _buildBucketStrip() {
    final buckets = <String, (String, IconData)>[
      ('TODAY', ('Today Due', Icons.today_outlined)),
      ('OVERDUE', ('Overdue', Icons.warning_amber_outlined)),
      ('NEXT_7_DAYS', ('Next 7 Days', Icons.date_range_outlined)),
      ('UPCOMING', ('Upcoming', Icons.event_available_outlined)),
      ('COLLECTED', ('Collected', Icons.check_circle_outline)),
      ('ALL', ('All', Icons.list_alt_outlined)),
    ];

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: Row(
        children: buckets.map((entry) {
          final value = entry.$1;
          final label = entry.$2.$1;
          final icon = entry.$2.$2;
          final count = value == 'ALL' ? _customers.length : _count(value);
          return Padding(
            padding: const EdgeInsets.only(right: 8),
            child: ChoiceChip(
              avatar: Icon(icon, size: 18),
              label: Text('$label  $count'),
              selected: _bucketFilter == value,
              onSelected: (_) => setState(() => _bucketFilter = value),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildSearchAndArea() {
    return Column(
      children: [
        TextField(
          controller: _searchController,
          textInputAction: TextInputAction.search,
          onChanged: (value) => setState(() => _searchQuery = value),
          decoration: InputDecoration(
            hintText: 'Search old/new card, name, ID, phone, area...',
            prefixIcon: const Icon(Icons.search),
            suffixIcon: _searchQuery.isEmpty
                ? IconButton(
                    tooltip: 'Scan customer QR',
                    onPressed: _scanCustomerQr,
                    icon: const Icon(Icons.qr_code_scanner),
                  )
                : IconButton(
                    tooltip: 'Clear',
                    onPressed: () {
                      _searchController.clear();
                      setState(() => _searchQuery = '');
                    },
                    icon: const Icon(Icons.clear),
                  ),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
          ),
        ),
        const SizedBox(height: 10),
        DropdownButtonFormField<String>(
          initialValue: _areas.contains(_areaFilter) ? _areaFilter : 'ALL',
          decoration: const InputDecoration(
            labelText: 'Area / Route',
            prefixIcon: Icon(Icons.route_outlined),
          ),
          items: _areas
              .map(
                (area) => DropdownMenuItem(
                  value: area,
                  child: Text(area == 'ALL' ? 'All areas' : area),
                ),
              )
              .toList(),
          onChanged: (value) => setState(() => _areaFilter = value ?? 'ALL'),
        ),
      ],
    );
  }

  Widget _buildCustomerList() {
    final customers = _filteredCustomers;
    if (customers.isEmpty) {
      return const Card(
        child: Padding(
          padding: EdgeInsets.all(28),
          child: Column(
            children: [
              Icon(Icons.search_off_outlined, size: 48),
              SizedBox(height: 8),
              Text('No customers in this collection view.'),
            ],
          ),
        ),
      );
    }

    final grouped = <String, List<RentManagementCustomer>>{};
    for (final customer in customers) {
      grouped.putIfAbsent(customer.areaLabel, () => []).add(customer);
    }
    final areas = grouped.keys.toList()..sort();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
          child: Text(
            '${customers.length} customer${customers.length == 1 ? '' : 's'}',
            style: const TextStyle(fontWeight: FontWeight.w700),
          ),
        ),
        ...areas.expand((area) sync* {
          final rows = grouped[area]!;
          yield Padding(
            padding: const EdgeInsets.fromLTRB(4, 14, 4, 8),
            child: Row(
              children: [
                const Icon(Icons.location_on_outlined, size: 18),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    area,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                ),
                Text('${rows.length}'),
              ],
            ),
          );
          for (final customer in rows) {
            yield _customerCard(customer);
          }
        }),
      ],
    );
  }

  Widget _customerCard(RentManagementCustomer customer) {
    final isCollected = customer.collectionBucket == 'COLLECTED';
    final dueLabel = switch (customer.collectionBucket) {
      'TODAY' => 'Due today',
      'OVERDUE' => '${customer.daysUntilDue.abs()} day overdue',
      'NEXT_7_DAYS' => 'Due in ${customer.daysUntilDue} day',
      'COLLECTED' => 'Collected',
      _ => 'Due ${customer.dueDate}',
    };

    return Card(
      margin: const EdgeInsets.only(bottom: 9),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => _openCustomerDetails(customer),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  CircleAvatar(
                    child: Text(
                      customer.name.trim().isEmpty
                          ? '?'
                          : customer.name.trim()[0].toUpperCase(),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          customer.name.isEmpty ? 'Customer' : customer.name,
                          style: const TextStyle(fontWeight: FontWeight.w800),
                        ),
                        Text('${customer.customerId} • ${customer.phone}'),
                      ],
                    ),
                  ),
                  Chip(label: Text(dueLabel)),
                ],
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 6,
                children: [
                  if (customer.oldCardNumber.trim().isNotEmpty)
                    _miniChip('Old ${customer.oldCardNumber}'),
                  if (customer.cardNumber.trim().isNotEmpty)
                    _miniChip('ARI ${customer.cardNumber}'),
                  _miniChip('Balance ₹${customer.balance.toStringAsFixed(0)}'),
                  if (customer.hasLocation)
                    _miniChip('GPS saved')
                  else
                    _miniChip('GPS pending'),
                ],
              ),
              if (customer.address.trim().isNotEmpty) ...[
                const SizedBox(height: 8),
                Text(
                  customer.address,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
              const SizedBox(height: 10),
              SizedBox(
                width: double.infinity,
                child: FilledButton.icon(
                  onPressed: isCollected
                      ? null
                      : () => _openCustomerDetails(customer),
                  icon: Icon(isCollected ? Icons.check : Icons.currency_rupee),
                  label: Text(isCollected ? 'COLLECTED' : 'COLLECT RENT'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _miniChip(String label) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: Theme.of(context).dividerColor),
        ),
        child: Text(label, style: const TextStyle(fontSize: 12)),
      );
}

class _RentCustomerQrScanner extends StatefulWidget {
  const _RentCustomerQrScanner({required this.customers});

  final List<RentManagementCustomer> customers;

  @override
  State<_RentCustomerQrScanner> createState() => _RentCustomerQrScannerState();
}

class _RentCustomerQrScannerState extends State<_RentCustomerQrScanner> {
  final MobileScannerController _controller = MobileScannerController();
  bool _processing = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onDetect(BarcodeCapture capture) {
    if (_processing || capture.barcodes.isEmpty) return;
    final raw = capture.barcodes.first.rawValue?.trim() ?? '';
    if (raw.isEmpty) return;
    _processing = true;

    final token = raw.startsWith('ARI-SMART-RO:CUSTOMER:')
        ? raw.substring('ARI-SMART-RO:CUSTOMER:'.length)
        : raw;

    RentManagementCustomer? match;
    for (final customer in widget.customers) {
      if (customer.customerId == token ||
          customer.cardNumber == token ||
          customer.oldCardNumber == token ||
          customer.phone == token) {
        match = customer;
        break;
      }
    }

    if (match != null) {
      Navigator.pop(context, match);
      return;
    }

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('This QR/customer is not in your assigned rent list.')),
    );
    Future<void>.delayed(const Duration(milliseconds: 900), () {
      if (mounted) setState(() => _processing = false);
    });
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        appBar: AppBar(title: const Text('Scan Customer QR')),
        body: Stack(
          fit: StackFit.expand,
          children: [
            MobileScanner(controller: _controller, onDetect: _onDetect),
            Center(
              child: Container(
                width: 260,
                height: 260,
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.white, width: 3),
                  borderRadius: BorderRadius.circular(20),
                ),
              ),
            ),
            const Positioned(
              left: 24,
              right: 24,
              bottom: 34,
              child: Card(
                child: Padding(
                  padding: EdgeInsets.all(14),
                  child: Text(
                    'Scan ARI customer QR. Only customers assigned to your rent list can open.',
                    textAlign: TextAlign.center,
                  ),
                ),
              ),
            ),
          ],
        ),
      );
}

class RentCustomerDetailsScreen extends StatefulWidget {
  const RentCustomerDetailsScreen({super.key, required this.customer});

  final RentManagementCustomer customer;

  @override
  State<RentCustomerDetailsScreen> createState() =>
      _RentCustomerDetailsScreenState();
}

class _RentCustomerDetailsScreenState extends State<RentCustomerDetailsScreen> {
  bool _savingPayment = false;

  RentManagementCustomer get customer => widget.customer;

  Color _statusColor(String status) {
    switch (status) {
      case 'PAID':
        return Colors.green;
      case 'PARTIAL':
        return Colors.orange;
      case 'PENDING':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  Future<void> _showAddPaymentDialog() async {
    final amountController = TextEditingController(
      text: customer.balance > 0 ? customer.balance.toStringAsFixed(0) : '',
    );
    final remarksController = TextEditingController();
    String paymentMode = 'CASH';

    try {
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => StatefulBuilder(
          builder: (context, setDialogState) => AlertDialog(
            title: const Text('Collect Rent'),
            content: SingleChildScrollView(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    customer.name,
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 4),
                  Text('Balance ₹${customer.balance.toStringAsFixed(2)}'),
                  const SizedBox(height: 14),
                  TextField(
                    controller: amountController,
                    keyboardType:
                        const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(
                      labelText: 'Amount collected',
                      prefixText: '₹ ',
                    ),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: paymentMode,
                    decoration: const InputDecoration(labelText: 'Payment mode'),
                    items: const [
                      DropdownMenuItem(value: 'CASH', child: Text('Cash')),
                      DropdownMenuItem(value: 'UPI', child: Text('UPI')),
                      DropdownMenuItem(value: 'BANK', child: Text('Bank transfer')),
                      DropdownMenuItem(value: 'OTHER', child: Text('Other')),
                    ],
                    onChanged: (value) =>
                        setDialogState(() => paymentMode = value ?? 'CASH'),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: remarksController,
                    maxLines: 2,
                    decoration: const InputDecoration(
                      labelText: 'Remarks / transaction reference',
                    ),
                  ),
                ],
              ),
            ),
            actions: [
              TextButton(
                onPressed: _savingPayment
                    ? null
                    : () => Navigator.pop(dialogContext),
                child: const Text('CANCEL'),
              ),
              FilledButton(
                onPressed: _savingPayment
                    ? null
                    : () async {
                        final amount =
                            double.tryParse(amountController.text.trim());
                        if (amount == null || amount <= 0) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(content: Text('Enter a valid amount.')),
                          );
                          return;
                        }
                        if (amount > customer.balance) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Amount cannot exceed current balance.'),
                            ),
                          );
                          return;
                        }
                        setDialogState(() => _savingPayment = true);
                        Navigator.pop(dialogContext);
                        await _submitPayment(
                          amount: amount,
                          paymentMode: paymentMode,
                          remarks: remarksController.text.trim(),
                        );
                      },
                child: const Text('CONFIRM COLLECTION'),
              ),
            ],
          ),
        ),
      );
    } finally {
      amountController.dispose();
      remarksController.dispose();
    }
  }

  Future<bool> _submitPayment({
    required double amount,
    required String paymentMode,
    required String remarks,
  }) async {
    try {
      final response = await RentManagementService.addRentPayment(
        customerId: customer.id,
        amount: amount,
        paymentMode: paymentMode,
        remarks: remarks,
      );
      if (!mounted) return false;
      final rent = response['rent'] as Map<String, dynamic>?;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            'Payment saved'
            '${rent?['balance'] != null ? ' • Balance ₹${rent?['balance']}' : ''}',
          ),
        ),
      );
      Navigator.pop(context, true);
      return true;
    } catch (e) {
      if (!mounted) return false;
      setState(() => _savingPayment = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(e.toString().replaceFirst('Exception: ', ''))),
      );
      return false;
    }
  }

  @override
  Widget build(BuildContext context) {
    final statusColor = _statusColor(customer.status);
    return Scaffold(
      appBar: AppBar(title: Text(customer.name.isEmpty ? 'Customer Rent' : customer.name)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    customer.name,
                    style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 6),
                  Text('Customer ID: ${customer.customerId}'),
                  Text('Current Card: ${customer.cardNumber}'),
                  if (customer.oldCardNumber.trim().isNotEmpty)
                    Text('Old Card: ${customer.oldCardNumber}'),
                  Text('Phone: ${customer.phone}'),
                  Text('Area: ${customer.areaLabel}'),
                  if (customer.address.trim().isNotEmpty)
                    Text('Address: ${customer.address}'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Current Rent',
                    style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 12),
                  _detailRow('Expected Rent', '₹${customer.rentMonthExpected.toStringAsFixed(2)}'),
                  _detailRow('Paid Amount', '₹${customer.paidAmount.toStringAsFixed(2)}'),
                  _detailRow('Balance', '₹${customer.balance.toStringAsFixed(2)}'),
                  _detailRow('Due Date', customer.dueDate),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      onPressed: customer.balance <= 0 ? null : _showAddPaymentDialog,
                      icon: const Icon(Icons.currency_rupee),
                      label: Text(customer.balance <= 0 ? 'COLLECTED' : 'COLLECT RENT'),
                    ),
                  ),
                  const SizedBox(height: 10),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: .10),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      customer.status,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: statusColor,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Recent Rent History',
                    style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 10),
                  if (customer.history.isEmpty)
                    const Text('No payment history yet.')
                  else
                    ...customer.history.take(12).map(
                          (item) => ListTile(
                            contentPadding: EdgeInsets.zero,
                            title: Text(item.rentMonth ?? '-'),
                            subtitle: Text(
                              'Expected ₹${item.expectedRent.toStringAsFixed(0)} • Paid ₹${item.paidAmount.toStringAsFixed(0)}',
                            ),
                            trailing: Text(item.status),
                          ),
                        ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _detailRow(String label, String value) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(
          children: [
            Expanded(child: Text(label)),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w700)),
          ],
        ),
      );
}
