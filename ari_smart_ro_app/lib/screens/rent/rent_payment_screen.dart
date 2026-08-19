import 'package:flutter/material.dart';

import '../../models/rent_model.dart';
import '../../services/rent_service.dart';
import '../qr/payment_qr_screen.dart';

class RentPaymentScreen extends StatefulWidget {
  const RentPaymentScreen({super.key});

  @override
  State<RentPaymentScreen> createState() =>
      _RentPaymentScreenState();
}

class _RentPaymentScreenState
    extends State<RentPaymentScreen> {

  final RentService _rentService = RentService();

  late Future<RentModel> _futureRent;

  @override
  void initState() {
    super.initState();

    _futureRent =
        _rentService.getRentDetails();
  }

  Future<void> _refresh() async {
    setState(() {
      _futureRent =
          _rentService.getRentDetails();
    });

    await _futureRent;
  }

  // ============================================================
  // OPEN PAYMENT QR
  // ============================================================

  void _openPaymentQr(double amount) {

    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => PaymentQrScreen(
          amount: amount,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(
          "Rent & Payment",
        ),
        centerTitle: true,
      ),

      body: FutureBuilder<RentModel>(
        future: _futureRent,

        builder: (context, snapshot) {

          if (snapshot.connectionState ==
              ConnectionState.waiting) {

            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (snapshot.hasError) {

            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),

                child: Column(
                  mainAxisSize: MainAxisSize.min,

                  children: [

                    const Icon(
                      Icons.error_outline,
                      size: 60,
                    ),

                    const SizedBox(height: 16),

                    Text(
                      snapshot.error?.toString() ??
                          "Unable to load rent details.",
                      textAlign: TextAlign.center,
                    ),

                    const SizedBox(height: 20),

                    ElevatedButton.icon(
                      onPressed: () {
                        setState(() {
                          _futureRent =
                              _rentService
                                  .getRentDetails();
                        });
                      },

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

          if (!snapshot.hasData) {

            return const Center(
              child: Text(
                "No rent details found.",
              ),
            );
          }

          final rent = snapshot.data!;

          return RefreshIndicator(
            onRefresh: _refresh,

            child: ListView(
              padding:
                  const EdgeInsets.all(16),

              children: [

                // ==================================================
                // CUSTOMER
                // ==================================================

                _CustomerCard(
                  customer: rent.customer,
                ),

                const SizedBox(height: 16),

                // ==================================================
                // CURRENT RENT
                // ==================================================

                _CurrentRentCard(
                  rent: rent.currentRent,

                  onPay: rent.currentRent.canPay
                      ? () {

                          _openPaymentQr(
                            rent.currentRent.balance,
                          );

                        }
                      : null,
                ),

                const SizedBox(height: 16),

                // ==================================================
                // RO DETAILS
                // ==================================================

                _ROCard(
                  ro: rent.ro,
                ),

                const SizedBox(height: 16),

                // ==================================================
                // RENT HISTORY
                // ==================================================

                _HistoryCard(
                  history: rent.history,
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}


// ==================================================================
// CUSTOMER CARD
// ==================================================================

class _CustomerCard extends StatelessWidget {

  const _CustomerCard({
    required this.customer,
  });

  final CustomerRentInfo customer;

  @override
  Widget build(BuildContext context) {

    return Card(
      elevation: 3,

      shape: RoundedRectangleBorder(
        borderRadius:
            BorderRadius.circular(16),
      ),

      child: Padding(
        padding: const EdgeInsets.all(18),

        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,

          children: [

            const Row(
              children: [

                Icon(
                  Icons.person,
                  size: 28,
                ),

                SizedBox(width: 10),

                Text(
                  "Customer Details",
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight:
                        FontWeight.bold,
                  ),
                ),
              ],
            ),

            const Divider(height: 24),

            _InfoRow(
              label: "Name",
              value: customer.name,
            ),

            _InfoRow(
              label: "Customer ID",
              value: customer.customerId,
            ),

            _InfoRow(
              label: "Card Number",
              value: customer.cardNumber,
            ),
            if (customer.oldCardNumber.trim().isNotEmpty)
              _InfoRow(
                label: "Old Card Number",
                value: customer.oldCardNumber,
              ),
          ],
        ),
      ),
    );
  }
}


// ==================================================================
// CURRENT RENT CARD
// ==================================================================

class _CurrentRentCard extends StatelessWidget {

  const _CurrentRentCard({
    required this.rent,
    required this.onPay,
  });

  final CurrentRent rent;
  final VoidCallback? onPay;

  @override
  Widget build(BuildContext context) {

    final bool paid =
        rent.status.toUpperCase() == "PAID";

    return Card(
      elevation: 4,

      shape: RoundedRectangleBorder(
        borderRadius:
            BorderRadius.circular(16),
      ),

      child: Padding(
        padding: const EdgeInsets.all(18),

        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,

          children: [

            const Row(
              children: [

                Icon(
                  Icons.payments,
                  size: 28,
                ),

                SizedBox(width: 10),

                Text(
                  "Current Rent",
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight:
                        FontWeight.bold,
                  ),
                ),
              ],
            ),

            const Divider(height: 24),

            _MoneyRow(
              label: "Monthly Rent",
              amount: rent.expectedRent,
            ),

            _MoneyRow(
              label: "Paid Amount",
              amount: rent.paidAmount,
            ),

            _MoneyRow(
              label: "Balance",
              amount: rent.balance,
              bold: true,
            ),

            const SizedBox(height: 12),

            Row(
              children: [

                const Text(
                  "Status:",
                  style: TextStyle(
                    fontWeight:
                        FontWeight.bold,
                  ),
                ),

                const SizedBox(width: 8),

                Container(
                  padding:
                      const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 6,
                  ),

                  decoration: BoxDecoration(
                    borderRadius:
                        BorderRadius.circular(20),

                    color: paid
                        ? Colors.green
                            .withValues(alpha: 0.12)
                        : Colors.orange
                            .withValues(alpha: 0.12),
                  ),

                  child: Text(
                    rent.status,

                    style: TextStyle(
                      fontWeight:
                          FontWeight.bold,

                      color: paid
                          ? Colors.green
                          : Colors.orange,
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(height: 8),

            _InfoRow(
              label: "Due Date",
              value:
                  rent.formattedDueDate,
            ),

            const SizedBox(height: 18),

            SizedBox(
              width: double.infinity,
              height: 50,

              child: ElevatedButton.icon(
                onPressed: onPay,

                icon: const Icon(
                  Icons.qr_code_2,
                ),

                label: Text(
                  paid
                      ? "Paid"
                      : "PAY NOW",
                ),

                style:
                    ElevatedButton.styleFrom(
                  shape:
                      RoundedRectangleBorder(
                    borderRadius:
                        BorderRadius.circular(12),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}


// ==================================================================
// RO CARD
// ==================================================================

class _ROCard extends StatelessWidget {

  const _ROCard({
    required this.ro,
  });

  final RORentInfo ro;

  @override
  Widget build(BuildContext context) {

    return Card(
      elevation: 3,

      shape: RoundedRectangleBorder(
        borderRadius:
            BorderRadius.circular(16),
      ),

      child: Padding(
        padding: const EdgeInsets.all(18),

        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,

          children: [

            const Row(
              children: [

                Icon(
                  Icons.water_drop,
                  size: 28,
                ),

                SizedBox(width: 10),

                Text(
                  "RO Details",
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight:
                        FontWeight.bold,
                  ),
                ),
              ],
            ),

            const Divider(height: 24),

            _InfoRow(
              label: "RO Model",
              value: ro.model,
            ),

            _MoneyRow(
              label: "Installation Charge",
              amount:
                  ro.installationCharge,
            ),

            _MoneyRow(
              label: "Security Deposit",
              amount:
                  ro.securityDeposit,
            ),

            _InfoRow(
              label: "Installation Date",
              value:
                  ro.formattedInstallationDate,
            ),
          ],
        ),
      ),
    );
  }
}


// ==================================================================
// HISTORY CARD
// ==================================================================

class _HistoryCard extends StatelessWidget {

  const _HistoryCard({
    required this.history,
  });

  final List<RentHistoryItem> history;

  @override
  Widget build(BuildContext context) {

    return Card(
      elevation: 3,

      shape: RoundedRectangleBorder(
        borderRadius:
            BorderRadius.circular(16),
      ),

      child: Padding(
        padding: const EdgeInsets.all(18),

        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,

          children: [

            const Row(
              children: [

                Icon(
                  Icons.history,
                  size: 28,
                ),

                SizedBox(width: 10),

                Text(
                  "Rent History",
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight:
                        FontWeight.bold,
                  ),
                ),
              ],
            ),

            const Divider(height: 24),

            if (history.isEmpty)

              const Padding(
                padding:
                    EdgeInsets.symmetric(
                  vertical: 20,
                ),

                child: Center(
                  child: Text(
                    "No payment history yet.",
                  ),
                ),
              )

            else

              ...history.map(
                (item) => Padding(
                  padding:
                      const EdgeInsets.only(
                    bottom: 12,
                  ),

                  child: Container(
                    padding:
                        const EdgeInsets.all(12),

                    decoration:
                        BoxDecoration(
                      borderRadius:
                          BorderRadius.circular(
                        12,
                      ),

                      border: Border.all(
                        color: Colors.grey
                            .withValues(
                          alpha: 0.25,
                        ),
                      ),
                    ),

                    child: Column(
                      children: [

                        Row(
                          mainAxisAlignment:
                              MainAxisAlignment
                                  .spaceBetween,

                          children: [

                            Expanded(
                              child: Text(
                                item
                                    .formattedMonth,

                                style:
                                    const TextStyle(
                                  fontWeight:
                                      FontWeight.bold,
                                ),
                              ),
                            ),

                            Text(
                              item.status,

                              style:
                                  TextStyle(
                                fontWeight:
                                    FontWeight.bold,

                                color: item.status
                                            .toUpperCase() ==
                                        "PAID"
                                    ? Colors.green
                                    : Colors.orange,
                              ),
                            ),
                          ],
                        ),

                        const SizedBox(height: 8),

                        Row(
                          mainAxisAlignment:
                              MainAxisAlignment
                                  .spaceBetween,

                          children: [

                            Text(
                              "Expected: ₹${item.expectedRent.toStringAsFixed(2)}",
                            ),

                            Text(
                              "Paid: ₹${item.paidAmount.toStringAsFixed(2)}",
                            ),
                          ],
                        ),

                        const SizedBox(height: 5),

                        Align(
                          alignment:
                              Alignment.centerRight,

                          child: Text(
                            "Balance: ₹${item.balance.toStringAsFixed(2)}",

                            style:
                                const TextStyle(
                              fontWeight:
                                  FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}


// ==================================================================
// INFO ROW
// ==================================================================

class _InfoRow extends StatelessWidget {

  const _InfoRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {

    return Padding(
      padding:
          const EdgeInsets.only(bottom: 8),

      child: Row(
        crossAxisAlignment:
            CrossAxisAlignment.start,

        children: [

          SizedBox(
            width: 135,

            child: Text(
              label,

              style: const TextStyle(
                color: Colors.grey,
              ),
            ),
          ),

          Expanded(
            child: Text(
              value.isEmpty
                  ? "-"
                  : value,

              style: const TextStyle(
                fontWeight:
                    FontWeight.w500,
              ),
            ),
          ),
        ],
      ),
    );
  }
}


// ==================================================================
// MONEY ROW
// ==================================================================

class _MoneyRow extends StatelessWidget {

  const _MoneyRow({
    required this.label,
    required this.amount,
    this.bold = false,
  });

  final String label;
  final double amount;
  final bool bold;

  @override
  Widget build(BuildContext context) {

    return Padding(
      padding:
          const EdgeInsets.only(bottom: 8),

      child: Row(
        mainAxisAlignment:
            MainAxisAlignment.spaceBetween,

        children: [

          Text(
            label,

            style: TextStyle(
              fontWeight: bold
                  ? FontWeight.bold
                  : FontWeight.normal,
            ),
          ),

          Text(
            "₹${amount.toStringAsFixed(2)}",

            style: TextStyle(
              fontWeight: bold
                  ? FontWeight.bold
                  : FontWeight.w500,

              fontSize:
                  bold ? 16 : 14,
            ),
          ),
        ],
      ),
    );
  }
}