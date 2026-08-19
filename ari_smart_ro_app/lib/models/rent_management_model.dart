class RentManagementCustomer {
  final int id;

  final String customerId;
  final String name;
  final String phone;

  // ============================================================
  // CARD NUMBERS
  // ============================================================

  final String cardNumber;
  final String oldCardNumber;

  // ============================================================
  // RENT
  // ============================================================

  final double rentMonthExpected;
  final double paidAmount;
  final double balance;

  final String status;
  final String dueDate;

  // ============================================================
  // RO DETAILS
  // ============================================================

  final String roModel;
  final double monthlyRent;
  final double installationCharge;
  final double securityDeposit;

  final String? installationDate;

  // ============================================================
  // RENT HISTORY
  // ============================================================

  final List<RentHistoryItem> history;

  RentManagementCustomer({
    required this.id,
    required this.customerId,
    required this.name,
    required this.phone,
    required this.cardNumber,
    required this.oldCardNumber,
    required this.rentMonthExpected,
    required this.paidAmount,
    required this.balance,
    required this.status,
    required this.dueDate,
    required this.roModel,
    required this.monthlyRent,
    required this.installationCharge,
    required this.securityDeposit,
    required this.installationDate,
    required this.history,
  });

  // ============================================================
  // FROM JSON
  // ============================================================

  factory RentManagementCustomer.fromJson(
    Map<String, dynamic> json,
  ) {
    final customer =
        (json["customer"] ?? {})
            as Map<String, dynamic>;

    final currentRent =
        (json["current_rent"] ?? {})
            as Map<String, dynamic>;

    final ro =
        (json["ro"] ?? {})
            as Map<String, dynamic>;

    final historyJson =
        (json["history"] ?? []) as List;

    return RentManagementCustomer(
      // ========================================================
      // CUSTOMER
      // ========================================================

      id: _toInt(
        customer["id"],
      ),

      customerId:
          customer["customer_id"]
                  ?.toString() ??
              "",

      name:
          customer["name"]
                  ?.toString() ??
              "",

      phone:
          customer["phone"]
                  ?.toString() ??
              "",

      // ========================================================
      // CURRENT CARD
      // ========================================================

      cardNumber:
          customer["card_number"]
                  ?.toString() ??
              "",

      // ========================================================
      // OLD CARD
      // ========================================================

      oldCardNumber:
          customer["old_card_number"]
                  ?.toString() ??
              "",

      // ========================================================
      // CURRENT RENT
      // ========================================================

      rentMonthExpected:
          _toDouble(
        currentRent[
            "expected_rent"],
      ),

      paidAmount:
          _toDouble(
        currentRent[
            "paid_amount"],
      ),

      balance:
          _toDouble(
        currentRent[
            "balance"],
      ),

      status:
          currentRent[
                  "status"]
              ?.toString() ??
          "PENDING",

      dueDate:
          currentRent[
                  "due_date"]
              ?.toString() ??
          "",

      // ========================================================
      // RO DETAILS
      // ========================================================

      roModel:
          ro["model"]
                  ?.toString() ??
              "",

      monthlyRent:
          _toDouble(
        ro["monthly_rent"],
      ),

      installationCharge:
          _toDouble(
        ro["installation_charge"],
      ),

      securityDeposit:
          _toDouble(
        ro["security_deposit"],
      ),

      installationDate:
          ro["installation_date"]
              ?.toString(),

      // ========================================================
      // RENT HISTORY
      // ========================================================

      history:
          historyJson
              .whereType<Map>()
              .map(
                (item) =>
                    RentHistoryItem.fromJson(
                  Map<String, dynamic>.from(
                    item,
                  ),
                ),
              )
              .toList(),
    );
  }

  // ============================================================
  // INT CONVERTER
  // ============================================================

  static int _toInt(
    dynamic value,
  ) {
    if (value is int) {
      return value;
    }

    return int.tryParse(
          value?.toString() ?? "",
        ) ??
        0;
  }

  // ============================================================
  // DOUBLE CONVERTER
  // ============================================================

  static double _toDouble(
    dynamic value,
  ) {
    if (value is num) {
      return value.toDouble();
    }

    return double.tryParse(
          value?.toString() ?? "",
        ) ??
        0.0;
  }
}


// ============================================================
// RENT HISTORY
// ============================================================

class RentHistoryItem {
  final int id;

  final String? rentMonth;

  final double expectedRent;
  final double paidAmount;
  final double balance;

  final String status;

  final String rawValue;
  final String remarks;

  final String? createdAt;

  RentHistoryItem({
    required this.id,
    required this.rentMonth,
    required this.expectedRent,
    required this.paidAmount,
    required this.balance,
    required this.status,
    required this.rawValue,
    required this.remarks,
    required this.createdAt,
  });

  // ============================================================
  // FROM JSON
  // ============================================================

  factory RentHistoryItem.fromJson(
    Map<String, dynamic> json,
  ) {
    return RentHistoryItem(
      id: _toInt(
        json["id"],
      ),

      rentMonth:
          json["rent_month"]
              ?.toString(),

      expectedRent:
          _toDouble(
        json["expected_rent"],
      ),

      paidAmount:
          _toDouble(
        json["paid_amount"],
      ),

      balance:
          _toDouble(
        json["balance"],
      ),

      status:
          json["status"]
                  ?.toString() ??
              "PENDING",

      rawValue:
          json["raw_value"]
                  ?.toString() ??
              "",

      remarks:
          json["remarks"]
                  ?.toString() ??
              "",

      createdAt:
          json["created_at"]
              ?.toString(),
    );
  }

  // ============================================================
  // INT CONVERTER
  // ============================================================

  static int _toInt(
    dynamic value,
  ) {
    if (value is int) {
      return value;
    }

    return int.tryParse(
          value?.toString() ?? "",
        ) ??
        0;
  }

  // ============================================================
  // DOUBLE CONVERTER
  // ============================================================

  static double _toDouble(
    dynamic value,
  ) {
    if (value is num) {
      return value.toDouble();
    }

    return double.tryParse(
          value?.toString() ?? "",
        ) ??
        0.0;
  }
}