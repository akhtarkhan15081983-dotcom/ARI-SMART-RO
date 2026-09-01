import 'package:flutter/material.dart';
import '../../controllers/installation_controller.dart';
import 'package:image_picker/image_picker.dart';
import 'package:geolocator/geolocator.dart';
import 'dart:io';
import '../../models/customer_model.dart';

class InstallationScreen extends StatefulWidget {
  final CustomerModel customer;
  const InstallationScreen({super.key, required this.customer});

  @override
  State<InstallationScreen> createState() => _InstallationScreenState();
}

class _InstallationScreenState extends State<InstallationScreen> {
  final controller = InstallationController();

  DateTime? selectedDate;

  final ImagePicker _picker = ImagePicker();
  XFile? roPhoto;
  XFile? customerPhoto;

  Position? currentPosition;

  bool gpsCaptured = false;

  String currentAddress = "";

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  Future<void> _selectDate() async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime(2024),
      lastDate: DateTime(2035),
    );

    if (picked != null) {
      setState(() {
        selectedDate = picked;
      });
    }
  }

  Future<void> _captureGPS() async {
    bool serviceEnabled = await Geolocator.isLocationServiceEnabled();

    if (!serviceEnabled) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text("Please Turn ON GPS")));

      return;
    }

    LocationPermission permission = await Geolocator.checkPermission();

    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }

    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text("Location Permission Required")),
      );

      return;
    }

    currentPosition = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
    );

    setState(() {
      gpsCaptured = true;
    });

    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text("GPS Captured Successfully")));
  }

  Future<void> _pickROPhoto() async {
    final XFile? image = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 70,
    );

    if (image != null) {
      setState(() {
        roPhoto = image;
      });
    }
  }

  Future<void> _pickCustomerPhoto() async {
    final XFile? image = await _picker.pickImage(
      source: ImageSource.camera,
      imageQuality: 70,
    );

    if (image != null) {
      setState(() {
        customerPhoto = image;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("New Installation"),
        centerTitle: true,
        backgroundColor: Colors.blue,
        foregroundColor: Colors.white,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const TextField(
              readOnly: true,
              decoration: InputDecoration(
                labelText: "Card Number",
                hintText: "ARI-2026-0001",
                prefixIcon: Icon(Icons.badge),
                border: OutlineInputBorder(),
              ),
            ),

            const SizedBox(height: 18),

            Card(
              elevation: 3,
              child: Padding(
                padding: const EdgeInsets.all(15),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.person, color: Colors.blue),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            widget.customer.customerName,
                            style: const TextStyle(
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 12),

                    Row(
                      children: [
                        const Icon(Icons.phone, color: Colors.green),
                        const SizedBox(width: 10),
                        Text(widget.customer.phone),
                      ],
                    ),

                    const SizedBox(height: 12),

                    Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(Icons.location_on, color: Colors.red),
                        const SizedBox(width: 10),
                        Expanded(child: Text(widget.customer.address)),
                      ],
                    ),

                    const SizedBox(height: 12),

                    Row(
                      children: [
                        Icon(Icons.location_city, color: Colors.orange),
                        SizedBox(width: 10),
                        Expanded(child: Text("Area : ${widget.customer.area}")),
                      ],
                    ),

                    const SizedBox(height: 12),

                    Row(
                      children: [
                        Icon(Icons.water_drop, color: Colors.blue),
                        SizedBox(width: 10),
                        Expanded(
                          child: Text("RO Model : ${widget.customer.roModel}"),
                        ),
                      ],
                    ),

                    const SizedBox(height: 12),

                    Row(
                      children: [
                        Icon(Icons.payments, color: Colors.green),
                        SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            "Monthly Rent : ₹${widget.customer.monthlyRent}",
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 12),

                    Row(
                      children: [
                        Icon(Icons.currency_rupee, color: Colors.deepPurple),
                        SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            "Installation Charge : ₹${widget.customer.installationCharge}",
                          ),
                        ),
                      ],
                    ),

                    const SizedBox(height: 12),

                    Row(
                      children: [
                        Icon(Icons.engineering, color: Colors.teal),
                        SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            "Assigned Engineer : ${widget.customer.assignedEngineer}",
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 18),

            const SizedBox(height: 18),

            InkWell(
              onTap: _selectDate,
              child: InputDecorator(
                decoration: const InputDecoration(
                  labelText: "Installation Date",
                  prefixIcon: Icon(Icons.calendar_month),
                  border: OutlineInputBorder(),
                ),
                child: Text(
                  selectedDate == null
                      ? "Select Date"
                      : "${selectedDate!.day}/${selectedDate!.month}/${selectedDate!.year}",
                  style: const TextStyle(fontSize: 16),
                ),
              ),
            ),

            const SizedBox(height: 18),

            TextField(
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: "Input TDS",
                hintText: "Enter Input TDS",
                prefixIcon: const Icon(Icons.water_drop_outlined),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            const SizedBox(height: 18),

            TextField(
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: "Output TDS",
                hintText: "Enter Output TDS",
                prefixIcon: const Icon(Icons.opacity),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),
            const SizedBox(height: 18),

            TextField(
              decoration: InputDecoration(
                labelText: "Referral Name",
                hintText: "Enter Referral Name (Optional)",
                prefixIcon: const Icon(Icons.group_add),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
            ),

            const SizedBox(height: 25),
            SizedBox(
              width: double.infinity,
              height: 55,
              child: OutlinedButton.icon(
                onPressed: _pickROPhoto,
                icon: const Icon(Icons.camera_alt),
                label: const Text("Upload RO Photo"),
              ),
            ),

            const SizedBox(height: 15),

            if (roPhoto != null)
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.file(
                  File(roPhoto!.path),
                  height: 200,
                  width: double.infinity,
                  fit: BoxFit.cover,
                ),
              ),

            const SizedBox(height: 15),
            SizedBox(
              width: double.infinity,
              height: 55,
              child: OutlinedButton.icon(
                onPressed: _pickCustomerPhoto,
                icon: const Icon(Icons.person),
                label: const Text("Upload Customer Photo"),
              ),
            ),
            const SizedBox(height: 15),

            if (customerPhoto != null)
              ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.file(
                  File(customerPhoto!.path),
                  height: 200,
                  width: double.infinity,
                  fit: BoxFit.cover,
                ),
              ),

            const SizedBox(height: 15),

            SizedBox(
              width: double.infinity,
              height: 55,
              child: OutlinedButton.icon(
                onPressed: _captureGPS,
                icon: const Icon(Icons.location_on),
                label: const Text("Get Live Location"),
              ),
            ),

            const SizedBox(height: 30),

            SizedBox(
              width: double.infinity,
              height: 55,
              child: ElevatedButton(
                onPressed: () {},
                style: ElevatedButton.styleFrom(
                  backgroundColor: Colors.blue,
                  foregroundColor: Colors.white,
                ),
                child: const Text(
                  "SAVE INSTALLATION",
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
