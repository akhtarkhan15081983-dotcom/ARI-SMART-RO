class RentManagementCustomer {
  final int id;
  final String customerId;
  final String name;
  final String phone;
  final String cardNumber;
  final String oldCardNumber;

  final String area;
  final String address;
  final String city;
  final double? latitude;
  final double? longitude;
  final String assignedEmployee;

  final double rentMonthExpected;
  final double paidAmount;
  final double balance;
  final String status;
  final String dueDate;
  final String collectionBucket;
  final int daysUntilDue;

  final String roModel;
  final double monthlyRent;
  final double installationCharge;
  final double securityDeposit;
  final String? installationDate;

  final List<RentHistoryItem> history;

  const RentManagementCustomer({
    required this.id,
    required this.customerId,
    required this.name,
    required this.phone,
    required this.cardNumber,
    required this.oldCardNumber,
    required this.area,
    required this.address,
    required this.city,
    required this.latitude,
    required this.longitude,
    required this.assignedEmployee,
    required this.rentMonthExpected,
    required this.paidAmount,
    required this.balance,
    required this.status,
    required this.dueDate,
    required this.collectionBucket,
    required this.daysUntilDue,
    required this.roModel,
    required this.monthlyRent,
    required this.installationCharge,
    required this.securityDeposit,
    required this.installationDate,
    required this.history,
  });

  factory RentManagementCustomer.fromJson(Map<String, dynamic> json) {
    final customer = Map<String, dynamic>.from(
      (json['customer'] ?? const <String, dynamic>{}) as Map,
    );
    final currentRent = Map<String, dynamic>.from(
      (json['current_rent'] ?? const <String, dynamic>{}) as Map,
    );
    final ro = Map<String, dynamic>.from(
      (json['ro'] ?? const <String, dynamic>{}) as Map,
    );
    final historyJson = (json['history'] ?? const <dynamic>[]) as List;

    return RentManagementCustomer(
      id: _toInt(customer['id']),
      customerId: customer['customer_id']?.toString() ?? '',
      name: customer['name']?.toString() ?? '',
      phone: customer['phone']?.toString() ?? '',
      cardNumber: customer['card_number']?.toString() ?? '',
      oldCardNumber: customer['old_card_number']?.toString() ?? '',
      area: customer['area']?.toString() ?? '',
      address: customer['address']?.toString() ?? '',
      city: customer['city']?.toString() ?? '',
      latitude: _toNullableDouble(customer['latitude']),
      longitude: _toNullableDouble(customer['longitude']),
      assignedEmployee: customer['assigned_employee']?.toString() ?? '',
      rentMonthExpected: _toDouble(currentRent['expected_rent']),
      paidAmount: _toDouble(currentRent['paid_amount']),
      balance: _toDouble(currentRent['balance']),
      status: currentRent['status']?.toString() ?? 'PENDING',
      dueDate: currentRent['due_date']?.toString() ?? '',
      collectionBucket:
          currentRent['collection_bucket']?.toString() ?? 'UPCOMING',
      daysUntilDue: _toInt(currentRent['days_until_due']),
      roModel: ro['model']?.toString() ?? '',
      monthlyRent: _toDouble(ro['monthly_rent']),
      installationCharge: _toDouble(ro['installation_charge']),
      securityDeposit: _toDouble(ro['security_deposit']),
      installationDate: ro['installation_date']?.toString(),
      history: historyJson
          .whereType<Map>()
          .map(
            (item) => RentHistoryItem.fromJson(
              Map<String, dynamic>.from(item),
            ),
          )
          .toList(),
    );
  }

  String get areaLabel {
    final value = area.trim();
    if (value.isNotEmpty) return value;
    final cityValue = city.trim();
    return cityValue.isNotEmpty ? cityValue : 'Area not set';
  }

  bool get hasLocation => latitude != null && longitude != null;

  static int _toInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  static double _toDouble(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '') ?? 0.0;
  }

  static double? _toNullableDouble(dynamic value) {
    if (value == null || value.toString().trim().isEmpty) return null;
    if (value is num) return value.toDouble();
    return double.tryParse(value.toString());
  }
}

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

  const RentHistoryItem({
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

  factory RentHistoryItem.fromJson(Map<String, dynamic> json) {
    return RentHistoryItem(
      id: _toInt(json['id']),
      rentMonth: json['rent_month']?.toString(),
      expectedRent: _toDouble(json['expected_rent']),
      paidAmount: _toDouble(json['paid_amount']),
      balance: _toDouble(json['balance']),
      status: json['status']?.toString() ?? 'PENDING',
      rawValue: json['raw_value']?.toString() ?? '',
      remarks: json['remarks']?.toString() ?? '',
      createdAt: json['created_at']?.toString(),
    );
  }

  static int _toInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse(value?.toString() ?? '') ?? 0;
  }

  static double _toDouble(dynamic value) {
    if (value is num) return value.toDouble();
    return double.tryParse(value?.toString() ?? '') ?? 0.0;
  }
}
