import 'package:flutter/material.dart';

import '../../models/payment_history_model.dart';
import '../../services/rent_management_service.dart';

class PaymentHistoryScreen extends StatefulWidget {
  const PaymentHistoryScreen({super.key});

  @override
  State<PaymentHistoryScreen> createState() => _PaymentHistoryScreenState();
}

class _PaymentHistoryScreenState extends State<PaymentHistoryScreen> {
  bool _isLoading = true;

  String? _error;

  List<RentPaymentRecord> _payments = [];

  List<RentPaymentRecord> _filteredPayments = [];

  final TextEditingController _searchController = TextEditingController();

  @override
  void initState() {
    super.initState();

    _searchController.addListener(_applySearch);

    _loadPaymentHistory();
  }

  @override
  void dispose() {
    _searchController.dispose();

    super.dispose();
  }

  // ============================================================
  // LOAD PAYMENT HISTORY
  // ============================================================

  Future<void> _loadPaymentHistory() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
        _error = null;
      });
    }

    try {
      final response = await RentManagementService.getPaymentHistory();

      final rawPayments = response["payments"];

      final List<RentPaymentRecord> payments = [];

      if (rawPayments is List) {
        for (final item in rawPayments) {
          if (item is Map) {
            payments.add(
              RentPaymentRecord.fromJson(Map<String, dynamic>.from(item)),
            );
          }
        }
      }

      if (!mounted) {
        return;
      }

      setState(() {
        _payments = payments;

        _filteredPayments = List<RentPaymentRecord>.from(payments);

        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }

      setState(() {
        _error = e.toString().replaceFirst("Exception: ", "");

        _isLoading = false;
      });
    }
  }

  // ============================================================
  // SEARCH
  // ============================================================

  void _applySearch() {
    final query = _searchController.text.trim().toLowerCase();

    if (query.isEmpty) {
      setState(() {
        _filteredPayments = List<RentPaymentRecord>.from(_payments);
      });

      return;
    }

    final filtered = _payments.where((payment) {
      return payment.customerName.toLowerCase().contains(query) ||
          payment.customerCode.toLowerCase().contains(query) ||
          payment.phone.toLowerCase().contains(query) ||
          // ==================================================
          // CURRENT CARD NUMBER
          // ==================================================
          payment.cardNumber.toLowerCase().contains(query) ||
          // ==================================================
          // OLD CARD NUMBER
          // ==================================================
          payment.oldCardNumber.toLowerCase().contains(query) ||
          payment.paymentMode.toLowerCase().contains(query) ||
          payment.collectedBy.toLowerCase().contains(query) ||
          payment.remarks.toLowerCase().contains(query);
    }).toList();

    setState(() {
      _filteredPayments = filtered;
    });
  }

  // ============================================================
  // FORMAT DATE
  // ============================================================

  String _formatDate(String? value) {
    if (value == null || value.isEmpty) {
      return "-";
    }

    try {
      final date = DateTime.parse(value);

      return "${date.day.toString().padLeft(2, '0')}/"
          "${date.month.toString().padLeft(2, '0')}/"
          "${date.year}";
    } catch (_) {
      return value;
    }
  }

  // ============================================================
  // FORMAT AMOUNT
  // ============================================================

  String _formatAmount(double amount) {
    return "₹${amount.toStringAsFixed(2)}";
  }

  // ============================================================
  // PAYMENT ICON
  // ============================================================

  IconData _paymentIcon(String mode) {
    switch (mode.trim().toUpperCase()) {
      case "CASH":
        return Icons.payments;

      case "UPI":
        return Icons.qr_code_2;

      case "BANK":
      case "BANK_TRANSFER":
        return Icons.account_balance;

      case "CARD":
        return Icons.credit_card;

      default:
        return Icons.receipt_long;
    }
  }

  // ============================================================
  // PAYMENT DETAILS
  // ============================================================

  void _showPaymentDetails(RentPaymentRecord payment) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,

      builder: (_) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(20),

            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,

                children: [
                  // ==================================================
                  // HEADER
                  // ==================================================
                  Row(
                    children: [
                      const Icon(Icons.receipt_long, size: 28),

                      const SizedBox(width: 10),

                      const Expanded(
                        child: Text(
                          "Payment Details",

                          style: TextStyle(
                            fontSize: 20,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),

                      IconButton(
                        onPressed: () {
                          Navigator.pop(context);
                        },

                        icon: const Icon(Icons.close),
                      ),
                    ],
                  ),

                  const Divider(),

                  // ==================================================
                  // CUSTOMER
                  // ==================================================
                  _detailRow("Customer", payment.customerName),

                  _detailRow("Customer ID", payment.customerCode),

                  _detailRow("Phone", payment.phone),

                  // ==================================================
                  // CURRENT CARD
                  // ==================================================
                  _detailRow("Card Number", payment.cardNumber),

                  // ==================================================
                  // OLD CARD
                  // ==================================================
                  if (payment.oldCardNumber.trim().isNotEmpty)
                    _detailRow("Old Card Number", payment.oldCardNumber),

                  // ==================================================
                  // RENT MONTH
                  // ==================================================
                  _detailRow("Rent Month", _formatDate(payment.rentMonth)),

                  // ==================================================
                  // PAYMENT DATE
                  // ==================================================
                  _detailRow("Payment Date", _formatDate(payment.paymentDate)),

                  // ==================================================
                  // AMOUNT
                  // ==================================================
                  _detailRow("Amount", _formatAmount(payment.amount)),

                  // ==================================================
                  // PAYMENT MODE
                  // ==================================================
                  _detailRow("Payment Mode", payment.paymentMode),

                  // ==================================================
                  // COLLECTED BY
                  // ==================================================
                  _detailRow(
                    "Collected By",
                    payment.collectedBy.isEmpty ? "-" : payment.collectedBy,
                  ),

                  // ==================================================
                  // REMARKS
                  // ==================================================
                  _detailRow(
                    "Remarks",
                    payment.remarks.isEmpty ? "-" : payment.remarks,
                  ),

                  // ==================================================
                  // CREATED AT
                  // ==================================================
                  _detailRow("Created At", _formatDate(payment.createdAt)),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  // ============================================================
  // DETAIL ROW
  // ============================================================

  Widget _detailRow(String title, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),

      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,

        children: [
          SizedBox(
            width: 135,

            child: Text(
              title,

              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
          ),

          Expanded(child: Text(value.isEmpty ? "-" : value)),
        ],
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
        title: const Text("Payment History"),

        centerTitle: true,

        actions: [
          IconButton(
            onPressed: _loadPaymentHistory,

            icon: const Icon(Icons.refresh),
          ),
        ],
      ),

      body: Column(
        children: [
          // ======================================================
          // SEARCH
          // ======================================================
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 8),

            child: TextField(
              controller: _searchController,

              decoration: InputDecoration(
                hintText: "Search name, ID, phone, card or old card...",

                prefixIcon: const Icon(Icons.search),

                suffixIcon: _searchController.text.isEmpty
                    ? null
                    : IconButton(
                        onPressed: () {
                          _searchController.clear();
                        },

                        icon: const Icon(Icons.clear),
                      ),

                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
          ),

          // ======================================================
          // SEARCH RESULT COUNT
          // ======================================================
          if (!_isLoading && _error == null)
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 5),

              child: Align(
                alignment: Alignment.centerLeft,

                child: Text(
                  _searchController.text.trim().isEmpty
                      ? "${_payments.length} payments"
                      : "${_filteredPayments.length} payments found",

                  style: TextStyle(
                    color: Colors.grey.shade700,

                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),

          // ======================================================
          // CONTENT
          // ======================================================
          Expanded(child: _buildContent()),
        ],
      ),
    );
  }

  // ============================================================
  // CONTENT
  // ============================================================

  Widget _buildContent() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    // ==========================================================
    // ERROR
    // ==========================================================

    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(20),

          child: Column(
            mainAxisSize: MainAxisSize.min,

            children: [
              const Icon(Icons.error_outline, size: 55),

              const SizedBox(height: 12),

              Text(_error!, textAlign: TextAlign.center),

              const SizedBox(height: 15),

              ElevatedButton.icon(
                onPressed: _loadPaymentHistory,

                icon: const Icon(Icons.refresh),

                label: const Text("Retry"),
              ),
            ],
          ),
        ),
      );
    }

    // ==========================================================
    // NO PAYMENTS
    // ==========================================================

    if (_payments.isEmpty) {
      return RefreshIndicator(
        onRefresh: _loadPaymentHistory,

        child: ListView(
          children: const [
            SizedBox(height: 160),

            Icon(Icons.receipt_long, size: 60),

            SizedBox(height: 15),

            Center(child: Text("No payment history yet.")),
          ],
        ),
      );
    }

    // ==========================================================
    // NO SEARCH RESULT
    // ==========================================================

    if (_filteredPayments.isEmpty) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,

          children: [
            Icon(Icons.search_off, size: 55),

            SizedBox(height: 12),

            Text("No matching payments found."),

            SizedBox(height: 5),

            Text(
              "Try customer name, ID, phone, current card or old card.",
              textAlign: TextAlign.center,
            ),
          ],
        ),
      );
    }

    // ==========================================================
    // PAYMENT LIST
    // ==========================================================

    return RefreshIndicator(
      onRefresh: _loadPaymentHistory,

      child: ListView.builder(
        padding: const EdgeInsets.fromLTRB(12, 4, 12, 20),

        itemCount: _filteredPayments.length,

        itemBuilder: (context, index) {
          final payment = _filteredPayments[index];

          return Card(
            margin: const EdgeInsets.only(bottom: 10),

            child: InkWell(
              borderRadius: BorderRadius.circular(12),

              onTap: () {
                _showPaymentDetails(payment);
              },

              child: Padding(
                padding: const EdgeInsets.all(14),

                child: Row(
                  children: [
                    // =================================================
                    // ICON
                    // =================================================
                    CircleAvatar(
                      child: Icon(_paymentIcon(payment.paymentMode)),
                    ),

                    const SizedBox(width: 12),

                    // =================================================
                    // PAYMENT INFO
                    // =================================================
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,

                        children: [
                          Text(
                            payment.customerName,

                            style: const TextStyle(
                              fontSize: 16,
                              fontWeight: FontWeight.bold,
                            ),
                          ),

                          const SizedBox(height: 4),

                          Text(
                            "${payment.customerCode}"
                            " • "
                            "${payment.paymentMode}",
                          ),

                          const SizedBox(height: 4),

                          Text(
                            "Card: "
                            "${payment.cardNumber}",
                          ),

                          // =========================================
                          // OLD CARD
                          // =========================================
                          if (payment.oldCardNumber.trim().isNotEmpty)
                            Text(
                              "Old Card: "
                              "${payment.oldCardNumber}",
                            ),

                          const SizedBox(height: 4),

                          Text(
                            "Date: "
                            "${_formatDate(payment.paymentDate)}",
                          ),

                          if (payment.collectedBy.isNotEmpty)
                            Text(
                              "Collected by: "
                              "${payment.collectedBy}",
                            ),
                        ],
                      ),
                    ),

                    const SizedBox(width: 8),

                    // =================================================
                    // AMOUNT
                    // =================================================
                    Text(
                      _formatAmount(payment.amount),

                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
