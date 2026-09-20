class CustomerModel {
  final int id;
  final String customerId;
  final String cardNumber;
  final String oldCardNumber;
  final String customerName;
  final String phone;
  final String alternatePhone;
  final String email;
  final String gender;
  final String address;
  final String area;
  final String city;
  final String state;
  final String pincode;
  final String roModel;
  final String monthlyRent;
  final String installationCharge;
  final String securityDeposit;
  final String installationDate;
  final bool isActive;
  final String deactivationReason;
  final String ownershipType;
  final String rentToPurchaseDate;
  final String rentToPurchaseAmount;
  final String rentToPurchaseNotes;

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
    required this.alternatePhone,
    required this.email,
    required this.gender,
    required this.address,
    required this.area,
    required this.city,
    required this.state,
    required this.pincode,
    required this.roModel,
    required this.monthlyRent,
    required this.installationCharge,
    required this.securityDeposit,
    required this.installationDate,
    required this.isActive,
    required this.deactivationReason,
    required this.ownershipType,
    required this.rentToPurchaseDate,
    required this.rentToPurchaseAmount,
    required this.rentToPurchaseNotes,
    required this.assignedEngineer,
    required this.engineerName,
    required this.latitude,
    required this.longitude,
  });

  factory CustomerModel.fromJson(Map<String, dynamic> json) {
    return CustomerModel(
      id: (json["id"] as num).toInt(),
      customerId: json["customer_id"]?.toString() ?? "",
      cardNumber: json["card_number"]?.toString() ?? "",
      oldCardNumber: json["old_card_number"]?.toString() ?? "",
      customerName: json["name"]?.toString() ?? "",
      phone: json["phone"]?.toString() ?? "",
      alternatePhone: json["alternate_phone"]?.toString() ?? "",
      email: json["email"]?.toString() ?? "",
      gender: json["gender"]?.toString() ?? "",
      address: json["address"]?.toString() ?? "",
      area: json["area"]?.toString() ?? "",
      city: json["city"]?.toString() ?? "",
      state: json["state"]?.toString() ?? "",
      pincode: json["pincode"]?.toString() ?? "",
      roModel: json["ro_model"]?.toString() ?? "",
      monthlyRent: json["monthly_rent"]?.toString() ?? "",
      installationCharge: json["installation_charge"]?.toString() ?? "",
      securityDeposit: json["security_deposit"]?.toString() ?? "",
      installationDate: json["installation_date"]?.toString() ?? "",
      isActive: json["is_active"] == true,
      deactivationReason: json["deactivation_reason"]?.toString() ?? "",
      ownershipType: json["ownership_type"]?.toString() ?? "RENTAL",
      rentToPurchaseDate: json["rent_to_purchase_date"]?.toString() ?? "",
      rentToPurchaseAmount: json["rent_to_purchase_amount"]?.toString() ?? "0",
      rentToPurchaseNotes: json["rent_to_purchase_notes"]?.toString() ?? "",
      assignedEngineer: json["assigned_engineer"] is num
          ? (json["assigned_engineer"] as num).toInt()
          : int.tryParse(json["assigned_engineer"]?.toString() ?? ""),
      engineerName: json["engineer_name"]?.toString() ?? "",
      latitude: double.tryParse(json["latitude"]?.toString() ?? "0") ?? 0,
      longitude: double.tryParse(json["longitude"]?.toString() ?? "0") ?? 0,
    );
  }
}
