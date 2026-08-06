class InstallationModel {
  final int customerId;

  final String cardNumber;
  final String customerName;
  final String mobileNumber;

  final String address;
  final String area;

  final String engineerName;
  final String roModel;

  final String installationAmount;
  final String monthlyRent;

  final String inputTds;
  final String outputTds;

  final String referralName;

  final DateTime installationDate;

  final double latitude;
  final double longitude;

  final String? roPhotoPath;
  final String? customerPhotoPath;

  final String remarks;

  InstallationModel({
    required this.customerId,
    required this.cardNumber,
    required this.customerName,
    required this.mobileNumber,
    required this.address,
    required this.area,
    required this.engineerName,
    required this.roModel,
    required this.installationAmount,
    required this.monthlyRent,
    required this.inputTds,
    required this.outputTds,
    required this.referralName,
    required this.installationDate,
    required this.latitude,
    required this.longitude,
    this.roPhotoPath,
    this.customerPhotoPath,
    this.remarks = "",
  });

  Map<String, dynamic> toJson() {
    return {
      "customer": customerId,
      "input_tds": inputTds,
      "output_tds": outputTds,
      "referral_name": referralName,
      "latitude": latitude,
      "longitude": longitude,
      "remarks": remarks,
    };
  }
}