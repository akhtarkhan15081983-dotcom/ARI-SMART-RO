class CustomerModel {
  final int id;
  final String customerId;
  final String cardNumber;
  final String oldCardNumber;
  final String customerName;
  final String phone;
  final String address;
  final String area;
  final String roModel;
  final String monthlyRent;
  final String installationCharge;

  final int? assignedEngineer;
  final String engineerName;

  final double latitude;
  final double longitude;

  CustomerModel({
    required this.id,
    required this.customerId,
    required this.cardNumber,
    required this.oldCardNumber,
    required this.customerName,
    required this.phone,
    required this.address,
    required this.area,
    required this.roModel,
    required this.monthlyRent,
    required this.installationCharge,
    required this.assignedEngineer,
    required this.engineerName,
    required this.latitude,
    required this.longitude,
  });

  factory CustomerModel.fromJson(Map<String, dynamic> json) {
    print(json);

    return CustomerModel(
      id: json["id"],

      customerId: json["customer_id"]?.toString() ?? "",

      cardNumber: json["card_number"]?.toString() ?? "",

      oldCardNumber: json["old_card_number"]?.toString() ?? "",

      customerName: json["name"]?.toString() ?? "",

      phone: json["phone"]?.toString() ?? "",

      address: json["address"]?.toString() ?? "",

      area: json["area"]?.toString() ?? "",

      roModel: json["ro_model"]?.toString() ?? "",

      monthlyRent: json["monthly_rent"]?.toString() ?? "",

      installationCharge: json["installation_charge"]?.toString() ?? "",

      assignedEngineer: json["assigned_engineer"],

      engineerName: json["engineer_name"]?.toString() ?? "",

      latitude: double.tryParse(json["latitude"]?.toString() ?? "0") ?? 0,

      longitude: double.tryParse(json["longitude"]?.toString() ?? "0") ?? 0,
    );
  }
}
