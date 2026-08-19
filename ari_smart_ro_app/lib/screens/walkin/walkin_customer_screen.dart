import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';

import '../../models/asset_model.dart';
import '../../services/customer_service.dart';
import '../assets/asset_selection_screen.dart';

class WalkInCustomerScreen extends StatefulWidget {
  const WalkInCustomerScreen({super.key});

  @override
  State<WalkInCustomerScreen> createState() =>
      _WalkInCustomerScreenState();
}

class _WalkInCustomerScreenState
    extends State<WalkInCustomerScreen> {

  final CustomerService customerService =
      CustomerService();

  final formKey = GlobalKey<FormState>();

  final nameController = TextEditingController();

  final phoneController = TextEditingController();

  final alternatePhoneController =
      TextEditingController();

  final addressController =
      TextEditingController();

  final areaController =
      TextEditingController();

  final cityController =
      TextEditingController();

  final stateController =
      TextEditingController();

  final pincodeController =
      TextEditingController();

  final installationChargeController =
      TextEditingController(text: "3000");

  final monthlyRentController =
      TextEditingController(text: "300");

  final securityDepositController =
      TextEditingController(text: "0");

  Position? currentPosition;

  AssetModel? selectedAsset;

  bool loading = false;

  @override
  void initState() {
    super.initState();

    _getCurrentLocation();
  }

  @override
  void dispose() {

    nameController.dispose();

    phoneController.dispose();

    alternatePhoneController.dispose();

    addressController.dispose();

    areaController.dispose();

    cityController.dispose();

    stateController.dispose();

    pincodeController.dispose();

    installationChargeController.dispose();

    monthlyRentController.dispose();

    securityDepositController.dispose();

    super.dispose();
  }
    Future<void> _getCurrentLocation() async {
    try {
      bool serviceEnabled =
          await Geolocator.isLocationServiceEnabled();

      if (!serviceEnabled) {
        return;
      }

      LocationPermission permission =
          await Geolocator.checkPermission();

      if (permission == LocationPermission.denied) {
        permission =
            await Geolocator.requestPermission();
      }

      if (permission ==
              LocationPermission.denied ||
          permission ==
              LocationPermission.deniedForever) {
        return;
      }

      final position =
          await Geolocator.getCurrentPosition(
        desiredAccuracy: LocationAccuracy.high,
      );

      if (!mounted) return;

      setState(() {
        currentPosition = position;
      });
    } catch (e) {
      debugPrint(e.toString());
    }
  }

  Future<void> _selectMachine() async {

    final AssetModel? asset =
        await Navigator.push<AssetModel>(
      context,
      MaterialPageRoute(
        builder: (_) =>
            const AssetSelectionScreen(),
      ),
    );

    if (asset == null) return;

    setState(() {
      selectedAsset = asset;
    });
  }
    Future<void> _saveCustomer() async {
    if (!formKey.currentState!.validate()) {
      return;
    }

    if (selectedAsset == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          backgroundColor: Colors.red,
          content: Text("Please select RO Machine first."),
        ),
      );
      return;
    }

    setState(() {
      loading = true;
    });

    try {
      final result =
          await customerService.createWalkInCustomer(
        name: nameController.text.trim(),
        phone: phoneController.text.trim(),

        roModel: selectedAsset!.id,
        assetId: selectedAsset!.id,

        alternatePhone:alternatePhoneController.text.trim(),
        
        address: addressController.text.trim(),
        area: areaController.text.trim(),
        city: cityController.text.trim(),
        state: stateController.text.trim(),
        pincode: pincodeController.text.trim(),

        latitude: currentPosition?.latitude,
        longitude: currentPosition?.longitude,

        installationCharge: double.tryParse(
                installationChargeController.text) ??
            0,
        monthlyRent: double.tryParse(
                monthlyRentController.text) ??
            0,
        securityDeposit: double.tryParse(
                securityDepositController.text) ??
            0,
      );

      if (!mounted) return;

      if (result["success"] == true) {

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            backgroundColor: Colors.green,
            content: Text("Customer Saved Successfully"),
          ),
        );

        Navigator.pop(context, true);

      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text("Unable to save customer"),
          ),
        );
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(e.toString()),
        ),
      );
    }

    if (mounted) {
      setState(() {
        loading = false;
      });
    }
  }
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Walk-In Customer"),
        centerTitle: true,
      ),
      body: Form(
        key: formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [

            
          _textField(
            controller: nameController,
            label: "Customer Name",
          ),

          _textField(
            controller: phoneController,
            label: "Phone Number",
            keyboard: TextInputType.phone,
          ),

          _textField(
            controller: alternatePhoneController,
            label: "Alternate Phone",
            keyboard: TextInputType.phone,
            requiredField: false,
          ),
          _textField(
            controller: addressController,
            label: "Address",
            maxLines: 2,
          ),

          _textField(
            controller: areaController,
            label: "Area",
          ),

          _textField(
            controller: cityController,
            label: "City",
          ),

          _textField(
            controller: stateController,
            label: "State",
          ),

          _textField(
            controller: pincodeController,
            label: "Pincode",
            keyboard: TextInputType.number,
          ),
          _textField(
            controller: installationChargeController,
            label: "Installation Charge",
            keyboard: TextInputType.number,
          ),

          _textField(
            controller: monthlyRentController,
            label: "Monthly Rent",
            keyboard: TextInputType.number,
          ),

          _textField(
            controller: securityDepositController,
            label: "Security Deposit",
            keyboard: TextInputType.number,
          ),
          const SizedBox(height: 20),

          Card(
            child: ListTile(
              leading: const Icon(Icons.my_location),
              title: const Text("Current Location"),
              subtitle: Text(
                currentPosition == null
                    ? "Getting Location..."
                    : "${currentPosition!.latitude}\n${currentPosition!.longitude}",
              ),
              trailing: IconButton(
                icon: const Icon(Icons.refresh),
                onPressed: _getCurrentLocation,
              ),
            ),
          ),
          

          const SizedBox(height: 8),

          Card(
            child: ListTile(
              leading: const Icon(
                Icons.water_drop,
                color: Colors.blue,
              ),

              title: Text(
                selectedAsset == null
                    ? "No RO Machine Selected"
                    : selectedAsset!.assetId,
              ),

              subtitle: Text(
                selectedAsset == null
                    ? "Tap Select Machine"
                    : "${selectedAsset!.roModelName}\n${selectedAsset!.serialNumber}",
              ),

              trailing: SizedBox(
                width: 85,
                child: ElevatedButton(
                  onPressed: _selectMachine,
                  child: const Text(
                    "Select",
                    style: TextStyle(fontSize: 12),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 20),

          SizedBox(
            height: 50,
            child: ElevatedButton(
              onPressed: loading ? null : _saveCustomer,
              child: loading
                  ? const CircularProgressIndicator()
                  : const Text("Save & Continue"),
            ),
          ),

          const SizedBox(height: 20),

          ],
        ),
      ),
    );
  }
         

       
  
    Widget _textField({
    required TextEditingController controller,
    required String label,
    TextInputType keyboard = TextInputType.text,
    bool requiredField = true,
    int maxLines = 1,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: TextFormField(
        controller: controller,
        keyboardType: keyboard,
        maxLines: maxLines,
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
        validator: (value) {
          if (!requiredField) return null;

          if (value == null || value.trim().isEmpty) {
            return "Required";
          }

          return null;
        },
      ),
    );
  }
}