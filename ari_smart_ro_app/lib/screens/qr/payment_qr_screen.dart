import 'package:flutter/material.dart';
import 'package:qr_flutter/qr_flutter.dart';

class PaymentQrScreen extends StatelessWidget {
  final double amount;

  const PaymentQrScreen({
    super.key,
    required this.amount,
  });

  // ============================================================
  // UPI DETAILS
  // ============================================================

  static const String upiId = 'akhtar.khan15081983@ybl';
  static const String payeeName = 'ARI SMART RO';

  // ============================================================
  // UPI QR DATA
  // ============================================================

  String get upiUri {
    final formattedAmount = amount.toStringAsFixed(2);

    return 'upi://pay'
        '?pa=$upiId'
        '&pn=${Uri.encodeComponent(payeeName)}'
        '&am=$formattedAmount'
        '&cu=INR';
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF5F7FA),

      appBar: AppBar(
        backgroundColor: const Color(0xFF0878D1),
        foregroundColor: Colors.white,
        centerTitle: true,
        title: const Text(
          'Pay Rent',
          style: TextStyle(
            fontWeight: FontWeight.w600,
          ),
        ),
      ),

      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [

              const SizedBox(height: 10),

              // ==================================================
              // TITLE
              // ==================================================

              const Text(
                'Scan & Pay',
                style: TextStyle(
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                  color: Colors.black87,
                ),
              ),

              const SizedBox(height: 8),

              const Text(
                'Scan this QR code using any UPI app',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 16,
                  color: Colors.grey,
                ),
              ),

              const SizedBox(height: 25),

              // ==================================================
              // QR CARD
              // ==================================================

              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(25),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(22),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.10),
                      blurRadius: 15,
                      offset: const Offset(0, 6),
                    ),
                  ],
                ),

                child: Column(
                  children: [

                    // ==================================================
                    // QR
                    // ==================================================

                    QrImageView(
                      data: upiUri,
                      version: QrVersions.auto,
                      size: 280,
                      backgroundColor: Colors.white,
                      errorCorrectionLevel: QrErrorCorrectLevel.M,
                    ),

                    const SizedBox(height: 25),

                    // ==================================================
                    // PAYEE
                    // ==================================================

                    const Text(
                      payeeName,
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),

                    const SizedBox(height: 8),

                    const Text(
                      upiId,
                      style: TextStyle(
                        fontSize: 15,
                        color: Colors.grey,
                      ),
                    ),

                    const SizedBox(height: 25),

                    // ==================================================
                    // AMOUNT
                    // ==================================================

                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.symmetric(
                        vertical: 15,
                        horizontal: 20,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEAF5FF),
                        borderRadius: BorderRadius.circular(14),
                      ),
                      child: Column(
                        children: [

                          const Text(
                            'Amount to Pay',
                            style: TextStyle(
                              fontSize: 15,
                              color: Colors.grey,
                            ),
                          ),

                          const SizedBox(height: 5),

                          Text(
                            '₹${amount.toStringAsFixed(2)}',
                            style: const TextStyle(
                              fontSize: 30,
                              fontWeight: FontWeight.bold,
                              color: Color(0xFF0878D1),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 25),

              // ==================================================
              // INSTRUCTION
              // ==================================================

              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(18),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: const Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [

                    Text(
                      'How to pay',
                      style: TextStyle(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),

                    SizedBox(height: 12),

                    Text(
                      '1. Open Google Pay, PhonePe, Paytm or another UPI app.',
                      style: TextStyle(
                        fontSize: 15,
                        height: 1.5,
                      ),
                    ),

                    Text(
                      '2. Scan the QR code above.',
                      style: TextStyle(
                        fontSize: 15,
                        height: 1.5,
                      ),
                    ),

                    Text(
                      '3. Verify the amount and pay.',
                      style: TextStyle(
                        fontSize: 15,
                        height: 1.5,
                      ),
                    ),

                    Text(
                      '4. Keep the payment confirmation for your records.',
                      style: TextStyle(
                        fontSize: 15,
                        height: 1.5,
                      ),
                    ),
                  ],
                ),
              ),

              const SizedBox(height: 25),

              // ==================================================
              // BACK BUTTON
              // ==================================================

              SizedBox(
                width: double.infinity,
                height: 52,
                child: ElevatedButton.icon(
                  onPressed: () {
                    Navigator.pop(context);
                  },
                  icon: const Icon(Icons.arrow_back),
                  label: const Text(
                    'BACK TO RENT',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF0878D1),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                ),
              ),

              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }
}