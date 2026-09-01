class RentPaymentRecord {
  final int id;

  final int customerId;
  final String customerCode;
  final String customerName;
  final String phone;

  // ============================================================
  // CARD NUMBERS
  // ============================================================

  final String cardNumber;
  final String oldCardNumber;

  final String? rentMonth;

  final double amount;

  final String? paymentDate;

  final String paymentMode;

  final String remarks;

  final String collectedBy;

  final String? createdAt;

  RentPaymentRecord({
    required this.id,
    required this.customerId,
    required this.customerCode,
    required this.customerName,
    required this.phone,
    required this.cardNumber,
    required this.oldCardNumber,
    required this.rentMonth,
    required this.amount,
    required this.paymentDate,
    required this.paymentMode,
    required this.remarks,
    required this.collectedBy,
    required this.createdAt,
  });

  factory RentPaymentRecord.fromJson(Map<String, dynamic> json) {
    final customer = (json["customer"] ?? {}) as Map<String, dynamic>;

    return RentPaymentRecord(
      id: _toInt(json["id"]),

      customerId: _toInt(customer["id"]),

      customerCode: customer["customer_id"]?.toString() ?? "",

      customerName: customer["name"]?.toString() ?? "",

      phone: customer["phone"]?.toString() ?? "",

      // ========================================================
      // CURRENT CARD NUMBER
      // ========================================================
      cardNumber: customer["card_number"]?.toString() ?? "",

      // ========================================================
      // OLD CARD NUMBER
      // ========================================================
      oldCardNumber: customer["old_card_number"]?.toString() ?? "",

      rentMonth: json["rent_month"]?.toString(),

      amount: _toDouble(json["amount"]),

      paymentDate: json["payment_date"]?.toString(),

      paymentMode: json["payment_mode"]?.toString() ?? "OTHER",

      remarks: json["remarks"]?.toString() ?? "",

      collectedBy: json["collected_by"]?.toString() ?? "",

      createdAt: json["created_at"]?.toString(),
    );
  }

  // ============================================================
  // INT CONVERTER
  // ============================================================

  static int _toInt(dynamic value) {
    if (value is int) {
      return value;
    }

    return int.tryParse(value?.toString() ?? "") ?? 0;
  }

  // ============================================================
  // DOUBLE CONVERTER
  // ============================================================

  static double _toDouble(dynamic value) {
    if (value is num) {
      return value.toDouble();
    }

    return double.tryParse(value?.toString() ?? "") ?? 0.0;
  }
}
