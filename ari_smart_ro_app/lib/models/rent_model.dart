class RentModel {
  final CustomerRentInfo customer;
  final CurrentRent currentRent;
  final RORentInfo ro;
  final List<RentHistoryItem> history;

  RentModel({
    required this.customer,
    required this.currentRent,
    required this.ro,
    required this.history,
  });

  factory RentModel.fromJson(Map<String, dynamic> json) {
    return RentModel(
      customer: CustomerRentInfo.fromJson(json["customer"] ?? {}),

      currentRent: CurrentRent.fromJson(json["current_rent"] ?? {}),

      ro: RORentInfo.fromJson(json["ro"] ?? {}),

      history: (json["history"] as List? ?? [])
          .map((e) => RentHistoryItem.fromJson(e))
          .toList(),
    );
  }
}

// ================================================================
// CUSTOMER
// ================================================================

class CustomerRentInfo {
  final String name;
  final String customerId;

  // Current Card
  final String cardNumber;

  // Old Card
  final String oldCardNumber;

  CustomerRentInfo({
    required this.name,
    required this.customerId,
    required this.cardNumber,
    required this.oldCardNumber,
  });

  factory CustomerRentInfo.fromJson(Map<String, dynamic> json) {
    return CustomerRentInfo(
      name: json["name"]?.toString() ?? "",

      customerId: json["customer_id"]?.toString() ?? "",

      cardNumber: json["card_number"]?.toString() ?? "",

      oldCardNumber: json["old_card_number"]?.toString() ?? "",
    );
  }
}

// ================================================================
// CURRENT RENT
// ================================================================

class CurrentRent {
  final String status;

  final double expectedRent;
  final double paidAmount;
  final double balance;

  final String dueDate;

  CurrentRent({
    required this.status,
    required this.expectedRent,
    required this.paidAmount,
    required this.balance,
    required this.dueDate,
  });

  bool get canPay {
    return balance > 0 && status.toUpperCase() != "PAID";
  }

  String get formattedDueDate {
    if (dueDate.isEmpty) {
      return "-";
    }

    return dueDate;
  }

  factory CurrentRent.fromJson(Map<String, dynamic> json) {
    return CurrentRent(
      status: json["status"]?.toString() ?? "PENDING",

      expectedRent:
          double.tryParse(json["expected_rent"]?.toString() ?? "0") ?? 0,

      paidAmount: double.tryParse(json["paid_amount"]?.toString() ?? "0") ?? 0,

      balance: double.tryParse(json["balance"]?.toString() ?? "0") ?? 0,

      dueDate: json["due_date"]?.toString() ?? "",
    );
  }
}

// ================================================================
// RO INFORMATION
// ================================================================

class RORentInfo {
  final String model;

  final double installationCharge;
  final double securityDeposit;

  final String installationDate;

  RORentInfo({
    required this.model,
    required this.installationCharge,
    required this.securityDeposit,
    required this.installationDate,
  });

  String get formattedInstallationDate {
    if (installationDate.isEmpty) {
      return "-";
    }

    return installationDate;
  }

  factory RORentInfo.fromJson(Map<String, dynamic> json) {
    return RORentInfo(
      model: json["model"]?.toString() ?? "",

      installationCharge:
          double.tryParse(json["installation_charge"]?.toString() ?? "0") ?? 0,

      securityDeposit:
          double.tryParse(json["security_deposit"]?.toString() ?? "0") ?? 0,

      installationDate: json["installation_date"]?.toString() ?? "",
    );
  }
}

// ================================================================
// RENT HISTORY
// ================================================================

class RentHistoryItem {
  final String month;

  final double expectedRent;
  final double paidAmount;
  final double balance;

  final String status;

  RentHistoryItem({
    required this.month,
    required this.expectedRent,
    required this.paidAmount,
    required this.balance,
    required this.status,
  });

  String get formattedMonth {
    if (month.isEmpty) {
      return "-";
    }

    return month;
  }

  factory RentHistoryItem.fromJson(Map<String, dynamic> json) {
    final expected =
        double.tryParse(json["expected_rent"]?.toString() ?? "0") ?? 0;

    final paid = double.tryParse(json["paid_amount"]?.toString() ?? "0") ?? 0;

    final serverBalance = json["balance"];

    final balance = serverBalance != null
        ? double.tryParse(serverBalance.toString()) ?? 0
        : (expected - paid < 0 ? 0 : expected - paid);

    return RentHistoryItem(
      month: json["rent_month"]?.toString() ?? json["month"]?.toString() ?? "",

      expectedRent: expected,

      paidAmount: paid,

      balance: balance.toDouble(),

      status:
          json["status"]?.toString() ??
          (paid >= expected && expected > 0 ? "PAID" : "PENDING"),
    );
  }
}
