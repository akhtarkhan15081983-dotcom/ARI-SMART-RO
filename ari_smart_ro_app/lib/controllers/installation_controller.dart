import 'package:flutter/material.dart';
import '../models/installation_model.dart';
import '../services/installation_service.dart';

class InstallationController {
  final installationService = InstallationService();
  final customerNameController = TextEditingController();
  final mobileController = TextEditingController();
  final addressController = TextEditingController();
  final areaController = TextEditingController();
  final installationAmountController = TextEditingController();
  final monthlyRentController = TextEditingController();
  final inputTdsController = TextEditingController();
  final outputTdsController = TextEditingController();
  final referralController = TextEditingController();

  Future<bool> saveInstallation(InstallationModel installation) async {
    return await installationService.saveInstallation(installation);
  }

  void dispose() {
    customerNameController.dispose();
    mobileController.dispose();
    addressController.dispose();
    areaController.dispose();
    installationAmountController.dispose();
    monthlyRentController.dispose();
    inputTdsController.dispose();
    outputTdsController.dispose();
    referralController.dispose();
  }
}
