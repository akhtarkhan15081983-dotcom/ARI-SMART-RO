import 'package:flutter/material.dart';

import '../../models/rent_management_model.dart';
import '../../services/rent_management_service.dart';

class RentManagementScreen extends StatefulWidget {
  const RentManagementScreen({super.key});

  @override
  State<RentManagementScreen> createState() =>
      _RentManagementScreenState();
}

class _RentManagementScreenState
    extends State<RentManagementScreen> {

  // ============================================================
  // STATE
  // ============================================================

  bool _isLoading = true;

  String? _error;

  List<RentManagementCustomer> _customers = [];

  // ============================================================
  // CUSTOMER SEARCH
  // ============================================================

  final TextEditingController _searchController =
      TextEditingController();

  String _searchQuery = "";

  List<RentManagementCustomer> get _filteredCustomers {
    final query = _searchQuery.trim().toLowerCase();

    if (query.isEmpty) {
      return _customers;
    }

    return _customers.where((customer) {
      return customer.name.toLowerCase().contains(query) ||
          customer.customerId.toLowerCase().contains(query) ||
          customer.phone.toLowerCase().contains(query) ||
          customer.cardNumber.toLowerCase().contains(query) ||
          customer.oldCardNumber.toLowerCase().contains(query);
    }).toList();
  }

  // ============================================================
  // SUMMARY
  // ============================================================

  double get _totalExpected {
    return _customers.fold(
      0.0,
      (sum, customer) =>
          sum + customer.rentMonthExpected,
    );
  }

  double get _totalPaid {
    return _customers.fold(
      0.0,
      (sum, customer) =>
          sum + customer.paidAmount,
    );
  }

  double get _totalBalance {
    return _customers.fold(
      0.0,
      (sum, customer) =>
          sum + customer.balance,
    );
  }

  int get _paidCount {
    return _customers
        .where(
          (customer) =>
              customer.status == "PAID",
        )
        .length;
  }

  int get _pendingCount {
    return _customers
        .where(
          (customer) =>
              customer.status == "PENDING",
        )
        .length;
  }

  int get _partialCount {
    return _customers
        .where(
          (customer) =>
              customer.status == "PARTIAL",
        )
        .length;
  }

  // ============================================================
  // INIT
  // ============================================================

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

  // ============================================================
  // LOAD DATA
  // ============================================================

  Future<void> _loadRentManagement() async {

    if (mounted) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }

    try {

      final response =
          await RentManagementService
              .getRentManagement();

      final customerList =
          (response["customers"] ?? [])
              as List;

      final customers =
          customerList
              .map(
                (item) =>
                    RentManagementCustomer
                        .fromJson(
                  item
                      as Map<String, dynamic>,
                ),
              )
              .toList();

      if (!mounted) return;

      setState(() {

        _customers = customers;

        _isLoading = false;

        _error = null;
      });

    } catch (e) {

      debugPrint(
        "RENT MANAGEMENT ERROR: $e",
      );

      if (!mounted) return;

      setState(() {

        _isLoading = false;

        _error = e
            .toString()
            .replaceFirst(
              "Exception: ",
              "",
            );
      });
    }
  }

  // ============================================================
  // REFRESH
  // ============================================================

  Future<void> _refresh() async {
    await _loadRentManagement();
  }

  // ============================================================
  // STATUS COLOR
  // ============================================================

  Color _statusColor(
    String status,
  ) {

    switch (status) {

      case "PAID":
        return Colors.green;

      case "PARTIAL":
        return Colors.orange;

      case "PENDING":
        return Colors.red;

      case "NO_RENT":
        return Colors.grey;

      default:
        return Colors.blue;
    }
  }

  // ============================================================
  // STATUS TEXT
  // ============================================================

  String _statusText(
    String status,
  ) {

    switch (status) {

      case "PAID":
        return "PAID";

      case "PARTIAL":
        return "PARTIAL";

      case "PENDING":
        return "PENDING";

      case "NO_RENT":
        return "NO RENT";

      default:
        return status;
    }
  }

  // ============================================================
  // CUSTOMER DETAILS
  // ============================================================

  Future<void> _openCustomerDetails(
    RentManagementCustomer customer,
  ) async {

    final paymentSaved =
        await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) =>
            RentCustomerDetailsScreen(
          customer: customer,
        ),
      ),
    );

    if (paymentSaved == true) {
      await _refresh();
    }
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(
    BuildContext context,
  ) {

    return Scaffold(

      appBar: AppBar(

        title: const Text(
          "Rent Management",
        ),

        centerTitle: true,

        actions: [

          IconButton(
            icon: const Icon(
              Icons.refresh,
            ),
            onPressed: _isLoading
                ? null
                : _refresh,
          ),
        ],
      ),

      body: _buildBody(),
    );
  }

  // ============================================================
  // BODY
  // ============================================================

  Widget _buildBody() {

    if (_isLoading) {

      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (_error != null) {

      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize:
                MainAxisSize.min,
            children: [

              const Icon(
                Icons.error_outline,
                size: 60,
                color: Colors.red,
              ),

              const SizedBox(
                height: 16,
              ),

              Text(
                _error!,
                textAlign:
                    TextAlign.center,
                style: const TextStyle(
                  fontSize: 16,
                ),
              ),

              const SizedBox(
                height: 20,
              ),

              ElevatedButton.icon(
                onPressed:
                    _refresh,
                icon: const Icon(
                  Icons.refresh,
                ),
                label: const Text(
                  "Retry",
                ),
              ),
            ],
          ),
        ),
      );
    }

    if (_customers.isEmpty) {

      return RefreshIndicator(
        onRefresh: _refresh,
        child: ListView(
          children: const [

            SizedBox(
              height: 200,
            ),

            Center(
              child: Text(
                "No customer rent records found.",
                style: TextStyle(
                  fontSize: 16,
                ),
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(

      onRefresh: _refresh,

      child: ListView(

        padding:
            const EdgeInsets.all(12),

        children: [

          _buildSummary(),

          const SizedBox(
            height: 12,
          ),

          _buildCustomerSearch(),

          const SizedBox(
            height: 10,
          ),

          _buildCustomerList(),
        ],
      ),
    );
  }

  // ============================================================
  // SUMMARY CARD
  // ============================================================

  Widget _buildSummary() {

    return Card(

      elevation: 3,

      shape:
          RoundedRectangleBorder(
        borderRadius:
            BorderRadius.circular(16),
      ),

      child: Padding(

        padding:
            const EdgeInsets.all(16),

        child: Column(

          crossAxisAlignment:
              CrossAxisAlignment.start,

          children: [

            const Text(
              "Rent Summary",
              style: TextStyle(
                fontSize: 20,
                fontWeight:
                    FontWeight.bold,
              ),
            ),

            const SizedBox(
              height: 16,
            ),

            Row(
              children: [

                Expanded(
                  child:
                      _summaryBox(
                    "Customers",
                    _customers.length
                        .toString(),
                    Icons.people,
                    Colors.blue,
                  ),
                ),

                const SizedBox(
                  width: 8,
                ),

                Expanded(
                  child:
                      _summaryBox(
                    "Paid",
                    _paidCount
                        .toString(),
                    Icons.check_circle,
                    Colors.green,
                  ),
                ),

                const SizedBox(
                  width: 8,
                ),

                Expanded(
                  child:
                      _summaryBox(
                    "Pending",
                    _pendingCount
                        .toString(),
                    Icons.pending,
                    Colors.red,
                  ),
                ),
              ],
            ),

            const SizedBox(
              height: 12,
            ),

            Row(
              children: [

                Expanded(
                  child:
                      _summaryBox(
                    "Expected",
                    "₹${_totalExpected.toStringAsFixed(0)}",
                    Icons.account_balance_wallet,
                    Colors.blueGrey,
                  ),
                ),

                const SizedBox(
                  width: 8,
                ),

                Expanded(
                  child:
                      _summaryBox(
                    "Collected",
                    "₹${_totalPaid.toStringAsFixed(0)}",
                    Icons.payments,
                    Colors.green,
                  ),
                ),

                const SizedBox(
                  width: 8,
                ),

                Expanded(
                  child:
                      _summaryBox(
                    "Balance",
                    "₹${_totalBalance.toStringAsFixed(0)}",
                    Icons.money_off,
                    Colors.orange,
                  ),
                ),
              ],
            ),

            if (_partialCount > 0) ...[

              const SizedBox(
                height: 12,
              ),

              Text(
                "Partial Payments: $_partialCount",
                style: const TextStyle(
                  color: Colors.orange,
                  fontWeight:
                      FontWeight.w600,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  // ============================================================
  // SUMMARY BOX
  // ============================================================

  Widget _summaryBox(
    String title,
    String value,
    IconData icon,
    Color color,
  ) {

    return Container(

      padding:
          const EdgeInsets.all(10),

      decoration:
          BoxDecoration(

        color:
            color.withOpacity(0.08),

        borderRadius:
            BorderRadius.circular(12),

        border:
            Border.all(
          color:
              color.withOpacity(0.20),
        ),
      ),

      child: Column(

        children: [

          Icon(
            icon,
            color: color,
            size: 24,
          ),

          const SizedBox(
            height: 6,
          ),

          Text(
            value,
            textAlign:
                TextAlign.center,
            style: TextStyle(
              fontSize: 16,
              fontWeight:
                  FontWeight.bold,
              color: color,
            ),
          ),

          const SizedBox(
            height: 3,
          ),

          Text(
            title,
            textAlign:
                TextAlign.center,
            style: const TextStyle(
              fontSize: 11,
            ),
          ),
        ],
      ),
    );
  }

  // ============================================================
  // CUSTOMER LIST
  // ============================================================

  Widget _buildCustomerSearch() {
    final resultCount = _filteredCustomers.length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: _searchController,
          onChanged: (value) {
            setState(() {
              _searchQuery = value;
            });
          },
          textInputAction: TextInputAction.search,
          decoration: InputDecoration(
            hintText:
              "Search name, ID, phone, current card or old card...",
            prefixIcon: const Icon(Icons.search),
            suffixIcon: _searchQuery.isEmpty
                ? null
                : IconButton(
                    tooltip: "Clear search",
                    icon: const Icon(Icons.clear),
                    onPressed: () {
                      _searchController.clear();
                      setState(() {
                        _searchQuery = "";
                      });
                    },
                  ),
            filled: true,
            fillColor: Colors.white,
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: BorderSide(
                color: Colors.grey.shade300,
              ),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: BorderSide(
                color: Colors.grey.shade300,
              ),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(
                color: Colors.blue,
                width: 1.5,
              ),
            ),
          ),
        ),

        if (_searchQuery.trim().isNotEmpty) ...[
          const SizedBox(height: 8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Text(
              resultCount == 0
                  ? "No customer found"
                  : "$resultCount customer${resultCount == 1 ? "" : "s"} found",
              style: TextStyle(
                color: resultCount == 0
                    ? Colors.red
                    : Colors.grey.shade700,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildCustomerList() {
    final customers = _filteredCustomers;

    if (customers.isEmpty) {
      return Card(
        elevation: 1,
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              Icon(
                Icons.person_search,
                size: 52,
                color: Colors.grey.shade500,
              ),
              const SizedBox(height: 10),
              Text(
                _searchQuery.trim().isEmpty
                    ? "No customer rent records found."
                    : "No customer matches your search.",
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
              if (_searchQuery.trim().isNotEmpty) ...[
                const SizedBox(height: 6),
                Text(
                  "Try name, customer ID, phone, current card or old card number.",
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Colors.grey.shade600,
                  ),
                ),
              ],
            ],
          ),
        ),
      );
    }

    return Column(
      children: customers.map(
        (customer) {

          return Card(

            margin:
                const EdgeInsets.only(
              bottom: 10,
            ),

            elevation: 2,

            shape:
                RoundedRectangleBorder(
              borderRadius:
                  BorderRadius.circular(
                14,
              ),
            ),

            child: InkWell(

              borderRadius:
                  BorderRadius.circular(
                14,
              ),

              onTap: () =>
                  _openCustomerDetails(
                customer,
              ),

              child: Padding(

                padding:
                    const EdgeInsets.all(
                  14,
                ),

                child: Column(

                  crossAxisAlignment:
                      CrossAxisAlignment
                          .start,

                  children: [

                    Row(
                      children: [

                        CircleAvatar(

                          backgroundColor:
                              Colors.blue
                                  .withOpacity(
                            0.10,
                          ),

                          child:
                              const Icon(
                            Icons.person,
                            color:
                                Colors.blue,
                          ),
                        ),

                        const SizedBox(
                          width: 12,
                        ),

                        Expanded(
                          child: Column(

                            crossAxisAlignment:
                                CrossAxisAlignment
                                    .start,

                            children: [

                              Text(
                                customer.name
                                    .isEmpty
                                    ? "Unknown Customer"
                                    : customer.name,
                                style:
                                    const TextStyle(
                                  fontSize: 17,
                                  fontWeight:
                                      FontWeight.bold,
                                ),
                              ),

                              const SizedBox(
                                height: 3,
                              ),

                              Text(
                                customer.customerId,
                                style:
                                    const TextStyle(
                                  color:
                                      Colors.grey,
                                ),
                              ),

                              Text(
                                customer.phone,
                                style:
                                    const TextStyle(
                                  color:
                                      Colors.grey,
                                  fontSize:
                                      12,
                                ),
                              ),
                            ],
                          ),
                        ),

                        _statusBadge(
                          customer.status,
                        ),
                      ],
                    ),

                    const Divider(
                      height: 24,
                    ),

                    Row(
                      children: [

                        Expanded(
                          child:
                              _amountColumn(
                            "Expected",
                            customer
                                .rentMonthExpected,
                          ),
                        ),

                        Expanded(
                          child:
                              _amountColumn(
                            "Paid",
                            customer
                                .paidAmount,
                          ),
                        ),

                        Expanded(
                          child:
                              _amountColumn(
                            "Balance",
                            customer.balance,
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(
                      height: 12,
                    ),

                    Row(
                      children: [

                        const Icon(
                          Icons.calendar_today,
                          size: 16,
                          color:
                              Colors.grey,
                        ),

                        const SizedBox(
                          width: 6,
                        ),

                        Text(
                          "Due: ${customer.dueDate}",
                          style:
                              const TextStyle(
                            fontSize: 13,
                            color:
                                Colors.grey,
                          ),
                        ),

                        const Spacer(),

                        const Icon(
                          Icons.chevron_right,
                          color:
                              Colors.grey,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ).toList(),
    );
  }

  // ============================================================
  // AMOUNT COLUMN
  // ============================================================

  Widget _amountColumn(
    String title,
    double amount,
  ) {

    return Column(

      crossAxisAlignment:
          CrossAxisAlignment.start,

      children: [

        Text(
          title,
          style:
              const TextStyle(
            fontSize: 12,
            color:
                Colors.grey,
          ),
        ),

        const SizedBox(
          height: 3,
        ),

        Text(
          "₹${amount.toStringAsFixed(2)}",
          style:
              const TextStyle(
            fontSize: 15,
            fontWeight:
                FontWeight.bold,
          ),
        ),
      ],
    );
  }

  // ============================================================
  // STATUS BADGE
  // ============================================================

  Widget _statusBadge(
    String status,
  ) {

    final color =
        _statusColor(status);

    return Container(

      padding:
          const EdgeInsets.symmetric(
        horizontal: 9,
        vertical: 5,
      ),

      decoration:
          BoxDecoration(

        color:
            color.withOpacity(0.10),

        borderRadius:
            BorderRadius.circular(
          20,
        ),

        border:
            Border.all(
          color:
              color.withOpacity(0.30),
        ),
      ),

      child: Text(
        _statusText(status),
        style: TextStyle(
          color: color,
          fontSize: 11,
          fontWeight:
              FontWeight.bold,
        ),
      ),
    );
  }
}


// =================================================================
// CUSTOMER RENT DETAILS
// =================================================================

class RentCustomerDetailsScreen
    extends StatefulWidget {

  const RentCustomerDetailsScreen({
    super.key,
    required this.customer,
  });

  final RentManagementCustomer
      customer;

  @override
  State<RentCustomerDetailsScreen>
      createState() =>
          _RentCustomerDetailsScreenState();
}

class _RentCustomerDetailsScreenState
    extends State<RentCustomerDetailsScreen> {

  // ============================================================
  // LOCAL STATE
  // ============================================================

  bool _savingPayment = false;

  // ============================================================
  // CUSTOMER
  // ============================================================

  RentManagementCustomer get customer =>
      widget.customer;

  // ============================================================
  // STATUS COLOR
  // ============================================================

  Color _statusColor(
    String status,
  ) {

    switch (status) {

      case "PAID":
        return Colors.green;

      case "PARTIAL":
        return Colors.orange;

      case "PENDING":
        return Colors.red;

      default:
        return Colors.grey;
    }
  }

  // ============================================================
  // STATUS TEXT
  // ============================================================

  String _statusText(
    String status,
  ) {

    switch (status) {

      case "PAID":
        return "PAID";

      case "PARTIAL":
        return "PARTIAL";

      case "PENDING":
        return "PENDING";

      case "NO_RENT":
        return "NO RENT";

      default:
        return status;
    }
  }

  // ============================================================
  // ADD PAYMENT DIALOG
  // ============================================================

  Future<void> _showAddPaymentDialog() async {

    final amountController =
        TextEditingController();

    final remarksController =
        TextEditingController();

    String paymentMode = "CASH";

    try {

      await showDialog(
        context: context,
        builder: (dialogContext) {

          return StatefulBuilder(
            builder: (
              context,
              setDialogState,
            ) {

              return AlertDialog(

                title: const Text(
                  "Add Rent Payment",
                ),

                content:
                    SingleChildScrollView(

                  child: Column(

                    mainAxisSize:
                        MainAxisSize.min,

                    children: [

                      Text(
                        customer.name.isEmpty
                            ? "Customer"
                            : customer.name,
                        style:
                            const TextStyle(
                          fontWeight:
                              FontWeight.bold,
                          fontSize: 17,
                        ),
                      ),

                      const SizedBox(
                        height: 6,
                      ),

                      Text(
                        "Balance: ₹${customer.balance.toStringAsFixed(2)}",
                        style:
                            const TextStyle(
                          color:
                              Colors.orange,
                          fontWeight:
                              FontWeight.w600,
                        ),
                      ),

                      const SizedBox(
                        height: 18,
                      ),

                      TextField(

                        controller:
                            amountController,

                        keyboardType:
                            const TextInputType
                                .numberWithOptions(
                          decimal: true,
                        ),

                        decoration:
                            const InputDecoration(
                          labelText:
                              "Payment Amount",
                          prefixText:
                              "₹ ",
                          border:
                              OutlineInputBorder(),
                        ),
                      ),

                      const SizedBox(
                        height: 12,
                      ),

                      DropdownButtonFormField<
                          String>(

                        initialValue:
                            paymentMode,

                        decoration:
                            const InputDecoration(
                          labelText:
                              "Payment Mode",
                          border:
                              OutlineInputBorder(),
                        ),

                        items: const [

                          DropdownMenuItem(
                            value: "CASH",
                            child:
                                Text("Cash"),
                          ),

                          DropdownMenuItem(
                            value: "UPI",
                            child:
                                Text("UPI"),
                          ),

                          DropdownMenuItem(
                            value: "BANK",
                            child:
                                Text(
                              "Bank Transfer",
                            ),
                          ),

                          DropdownMenuItem(
                            value: "OTHER",
                            child:
                                Text("Other"),
                          ),
                        ],

                        onChanged:
                            _savingPayment
                                ? null
                                : (value) {

                                    if (value ==
                                        null) {
                                      return;
                                    }

                                    setDialogState(
                                      () {
                                        paymentMode =
                                            value;
                                      },
                                    );
                                  },
                      ),

                      const SizedBox(
                        height: 12,
                      ),

                      TextField(

                        controller:
                            remarksController,

                        maxLines: 2,

                        decoration:
                            const InputDecoration(
                          labelText:
                              "Remarks",
                          hintText:
                              "Optional",
                          border:
                              OutlineInputBorder(),
                        ),
                      ),
                    ],
                  ),
                ),

                actions: [

                  TextButton(

                    onPressed:
                        _savingPayment
                            ? null
                            : () {
                                Navigator.pop(
                                  dialogContext,
                                );
                              },

                    child:
                        const Text(
                      "CANCEL",
                    ),
                  ),

                  ElevatedButton(

                    onPressed:
                        _savingPayment
                            ? null
                            : () async {

                                final amount =
                                    double.tryParse(
                                  amountController
                                      .text
                                      .trim(),
                                );

                                if (amount ==
                                        null ||
                                    amount <= 0) {

                                  ScaffoldMessenger
                                      .of(
                                    context,
                                  ).showSnackBar(
                                    const SnackBar(
                                      content:
                                          Text(
                                        "Please enter a valid payment amount.",
                                      ),
                                    ),
                                  );

                                  return;
                                }

                                if (amount >
                                    customer.balance) {

                                  ScaffoldMessenger
                                      .of(
                                    context,
                                  ).showSnackBar(
                                    const SnackBar(
                                      content:
                                          Text(
                                        "Payment cannot be greater than balance.",
                                      ),
                                    ),
                                  );

                                  return;
                                }

                                // IMPORTANT:
                                // Close the payment dialog before making the
                                // API call. The previous implementation kept
                                // the dialog mounted while _submitPayment()
                                // popped the customer details route, which
                                // caused Flutter's "_dependencies.isEmpty"
                                // assertion on some devices.

                                setDialogState(
                                  () {
                                    _savingPayment = true;
                                  },
                                );

                                Navigator.pop(
                                  dialogContext,
                                );

                                await _submitPayment(
                                  amount: amount,
                                  paymentMode: paymentMode,
                                  remarks:
                                      remarksController
                                          .text
                                          .trim(),
                                );
                              },

                    child:
                        _savingPayment

                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child:
                                    CircularProgressIndicator(
                                  strokeWidth:
                                      2,
                                ),
                              )

                            : const Text(
                                "SAVE PAYMENT",
                              ),
                  ),
                ],
              );
            },
          );
        },
      );

    } finally {

      amountController.dispose();

      remarksController.dispose();
    }
  }

  // ============================================================
  // SUBMIT PAYMENT
  // ============================================================

  Future<bool> _submitPayment({
    required double amount,
    required String paymentMode,
    required String remarks,
  }) async {

    try {

      final response =
          await RentManagementService
              .addRentPayment(

        customerId:
            customer.id,

        amount:
            amount,

        paymentMode:
            paymentMode,

        remarks:
            remarks,
      );

      if (!mounted) {
        return false;
      }

      final rent =
          response["rent"]
              as Map<String, dynamic>?;

      final newPaid =
          rent?["paid_amount"];

      final newBalance =
          rent?["balance"];

      final newStatus =
          rent?["status"];

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(
        SnackBar(
          content: Text(
            "Payment saved successfully"
            "${newPaid != null ? " • Paid: ₹$newPaid" : ""}"
            "${newBalance != null ? " • Balance: ₹$newBalance" : ""}",
          ),
          backgroundColor:
              Colors.green,
        ),
      );

      Navigator.of(
        context,
      ).pop(true);

      return true;

    } catch (e) {

      if (!mounted) {
        return false;
      }

      ScaffoldMessenger.of(
        context,
      ).showSnackBar(
        SnackBar(
          content: Text(
            e
                .toString()
                .replaceFirst(
                  "Exception: ",
                  "",
                ),
          ),
          backgroundColor:
              Colors.red,
        ),
      );

      return false;
    }
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(
    BuildContext context,
  ) {

    final statusColor =
        _statusColor(
      customer.status,
    );

    return Scaffold(

      appBar: AppBar(

        title: Text(
          customer.name.isEmpty
              ? "Customer Rent"
              : customer.name,
        ),
      ),

      body: ListView(

        padding:
            const EdgeInsets.all(16),

        children: [

          // ------------------------------------------------------
          // CUSTOMER INFO
          // ------------------------------------------------------

          Card(

            child: Padding(

              padding:
                  const EdgeInsets.all(16),

              child: Column(

                crossAxisAlignment:
                    CrossAxisAlignment.start,

                children: [

                  Text(
                    customer.name,
                    style:
                        const TextStyle(
                      fontSize: 21,
                      fontWeight:
                          FontWeight.bold,
                    ),
                  ),

                  const SizedBox(
                    height: 6,
                  ),

                  Text(
                    "Customer ID: ${customer.customerId}",
                  ),

                  Text(
                    "Card: ${customer.cardNumber}",
                  ),

                  if (customer.oldCardNumber.trim().isNotEmpty)
                    Text(
                      "Old Card: ${customer.oldCardNumber}",
                      style: TextStyle(
                        color: Colors.orange.shade800,
                        fontWeight: FontWeight.w600,
                      ),
                    ),

                  Text(
                    "Phone: ${customer.phone}",
                  ),

                  if (customer.roModel
                      .isNotEmpty)

                    Text(
                      "RO Model: ${customer.roModel}",
                    ),
                ],
              ),
            ),
          ),

          const SizedBox(
            height: 12,
          ),

          // ------------------------------------------------------
          // CURRENT RENT
          // ------------------------------------------------------

          Card(

            child: Padding(

              padding:
                  const EdgeInsets.all(16),

              child: Column(

                crossAxisAlignment:
                    CrossAxisAlignment.start,

                children: [

                  const Text(
                    "Current Rent",
                    style:
                        TextStyle(
                      fontSize: 19,
                      fontWeight:
                          FontWeight.bold,
                    ),
                  ),

                  const SizedBox(
                    height: 16,
                  ),

                  _detailRow(
                    "Expected Rent",
                    "₹${customer.rentMonthExpected.toStringAsFixed(2)}",
                  ),

                  _detailRow(
                    "Paid Amount",
                    "₹${customer.paidAmount.toStringAsFixed(2)}",
                  ),

                  _detailRow(
                    "Balance",
                    "₹${customer.balance.toStringAsFixed(2)}",
                  ),

                  _detailRow(
                    "Due Date",
                    customer.dueDate,
                  ),

                  const SizedBox(
                    height: 10,
                  ),

                  // ------------------------------------------------
                  // ADD PAYMENT BUTTON
                  // ------------------------------------------------

                  SizedBox(
                    width:
                        double.infinity,

                    child:
                        ElevatedButton.icon(

                      onPressed:
                          customer.balance <= 0
                              ? null
                              : _showAddPaymentDialog,

                      icon:
                          const Icon(
                        Icons.add_card,
                      ),

                      label:
                          const Text(
                        "ADD PAYMENT",
                      ),
                    ),
                  ),

                  const SizedBox(
                    height: 10,
                  ),

                  // ------------------------------------------------
                  // STATUS
                  // ------------------------------------------------

                  Container(

                    width:
                        double.infinity,

                    padding:
                        const EdgeInsets.all(
                      10,
                    ),

                    decoration:
                        BoxDecoration(

                      color:
                          statusColor
                              .withOpacity(
                        0.10,
                      ),

                      borderRadius:
                          BorderRadius.circular(
                        10,
                      ),
                    ),

                    child:
                        Text(

                      _statusText(
                        customer.status,
                      ),

                      textAlign:
                          TextAlign.center,

                      style:
                          TextStyle(
                        color:
                            statusColor,
                        fontWeight:
                            FontWeight.bold,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(
            height: 12,
          ),

          // ------------------------------------------------------
          // RO DETAILS
          // ------------------------------------------------------

          Card(

            child: Padding(

              padding:
                  const EdgeInsets.all(16),

              child: Column(

                crossAxisAlignment:
                    CrossAxisAlignment.start,

                children: [

                  const Text(
                    "RO Details",
                    style:
                        TextStyle(
                      fontSize: 19,
                      fontWeight:
                          FontWeight.bold,
                    ),
                  ),

                  const SizedBox(
                    height: 12,
                  ),

                  _detailRow(
                    "Monthly Rent",
                    "₹${customer.monthlyRent.toStringAsFixed(2)}",
                  ),

                  _detailRow(
                    "Installation Charge",
                    "₹${customer.installationCharge.toStringAsFixed(2)}",
                  ),

                  _detailRow(
                    "Security Deposit",
                    "₹${customer.securityDeposit.toStringAsFixed(2)}",
                  ),

                  _detailRow(
                    "Installation Date",
                    customer
                            .installationDate ??
                        "-",
                  ),
                ],
              ),
            ),
          ),

          const SizedBox(
            height: 12,
          ),

          // ------------------------------------------------------
          // HISTORY
          // ------------------------------------------------------

          Card(

            child: Padding(

              padding:
                  const EdgeInsets.all(16),

              child: Column(

                crossAxisAlignment:
                    CrossAxisAlignment.start,

                children: [

                  const Text(
                    "Rent History",
                    style:
                        TextStyle(
                      fontSize: 19,
                      fontWeight:
                          FontWeight.bold,
                    ),
                  ),

                  const SizedBox(
                    height: 12,
                  ),

                  if (customer.history
                      .isEmpty)

                    const Text(
                      "No rent history available.",
                    )

                  else

                    ...customer.history
                        .map(
                      (item) =>
                          _historyItem(
                        item,
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

  // ============================================================
  // DETAIL ROW
  // ============================================================

  Widget _detailRow(
    String title,
    String value,
  ) {

    return Padding(

      padding:
          const EdgeInsets.only(
        bottom: 9,
      ),

      child: Row(

        children: [

          Expanded(
            child: Text(
              title,
              style:
                  const TextStyle(
                color:
                    Colors.grey,
              ),
            ),
          ),

          Text(
            value,
            style:
                const TextStyle(
              fontWeight:
                  FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  // ============================================================
  // HISTORY ITEM
  // ============================================================

  Widget _historyItem(
    RentHistoryItem item,
  ) {

    final color =
        _statusColor(
      item.status,
    );

    return Container(

      margin:
          const EdgeInsets.only(
        bottom: 10,
      ),

      padding:
          const EdgeInsets.all(12),

      decoration:
          BoxDecoration(

        border:
            Border.all(
          color:
              Colors.grey.shade300,
        ),

        borderRadius:
            BorderRadius.circular(
          10,
        ),
      ),

      child: Column(

        crossAxisAlignment:
            CrossAxisAlignment.start,

        children: [

          Row(
            children: [

              Expanded(
                child: Text(
                  item.rentMonth ??
                      "-",
                  style:
                      const TextStyle(
                    fontWeight:
                        FontWeight.bold,
                  ),
                ),
              ),

              Container(

                padding:
                    const EdgeInsets
                        .symmetric(
                  horizontal: 8,
                  vertical: 4,
                ),

                decoration:
                    BoxDecoration(

                  color:
                      color.withOpacity(
                    0.10,
                  ),

                  borderRadius:
                      BorderRadius.circular(
                    20,
                  ),
                ),

                child: Text(
                  item.status,
                  style: TextStyle(
                    color: color,
                    fontSize: 10,
                    fontWeight:
                        FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(
            height: 8,
          ),

          Text(
            "Expected: ₹${item.expectedRent.toStringAsFixed(2)}",
          ),

          Text(
            "Paid: ₹${item.paidAmount.toStringAsFixed(2)}",
          ),

          Text(
            "Balance: ₹${item.balance.toStringAsFixed(2)}",
          ),

          if (item.remarks.isNotEmpty)

            Padding(

              padding:
                  const EdgeInsets.only(
                top: 5,
              ),

              child: Text(
                "Remarks: ${item.remarks}",
                style:
                    const TextStyle(
                  color:
                      Colors.grey,
                  fontSize: 12,
                ),
              ),
            ),
        ],
      ),
    );
  }
}