import 'package:flutter/material.dart';
import '../installation/installation_screen.dart';
import '../../models/customer_model.dart';
import '../../services/customer_service.dart';
import 'package:url_launcher/url_launcher.dart';

class AssignedCustomersScreen extends StatefulWidget {
  const AssignedCustomersScreen({super.key});

  @override
  State<AssignedCustomersScreen> createState() =>
      _AssignedCustomersScreenState();
}

class _AssignedCustomersScreenState
    extends State<AssignedCustomersScreen> {
    Future<void> _makePhoneCall(String phone) async {
      final Uri uri = Uri(scheme: 'tel', path: phone);

      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      }
    }

    Future<void> _openGoogleMaps(
      double latitude,
      double longitude,
    ) async {
      final Uri uri = Uri.parse(
        "google.navigation:q=$latitude,$longitude",
      );

      if (await canLaunchUrl(uri)) {
        await launchUrl(
          uri,
          mode: LaunchMode.externalApplication,
        );
      } else {
        final Uri webUri = Uri.parse(
          "https://www.google.com/maps/search/?api=1&query=$latitude,$longitude",
        );

        await launchUrl(
          webUri,
          mode: LaunchMode.externalApplication,
        );
        }
        }

        final customerService = CustomerService();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Assigned Customers"),
        centerTitle: true,
        backgroundColor: Colors.blue,
        foregroundColor: Colors.white,
      ),

      body: FutureBuilder<List<CustomerModel>>(
        future: customerService.getCustomers(),
        builder: (context, snapshot) {

          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(),
            );
          }

          if (snapshot.hasError) {
            return Center(
              child: Text(snapshot.error.toString()),
            );
          }

          final customers = snapshot.data ?? [];

          if (customers.isEmpty) {
            return const Center(
              child: Text("No Customers Assigned"),
            );
          }

          return ListView.builder(
            padding: const EdgeInsets.all(15),
            itemCount: customers.length,
            itemBuilder: (context, index) {

              final customer = customers[index];

              return Card(
                margin: const EdgeInsets.only(bottom: 15),
                elevation: 4,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(15),
                ),
                child: Padding(
                  padding: const EdgeInsets.all(15),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [

                      Text(
                        customer.customerName,
                        style: const TextStyle(
                          fontSize: 20,
                          fontWeight: FontWeight.bold,
                        ),
                      ),

                      const SizedBox(height: 8),

                      Text(
                        "Card No : ${customer.cardNumber}",
                        style: const TextStyle(
                          color: Colors.blue,
                          fontWeight: FontWeight.bold,
                        ),
                      ),

                      const SizedBox(height: 8),

                      Row(
                        children: [
                          const Icon(
                            Icons.phone,
                            color: Colors.green,
                          ),
                          const SizedBox(width: 8),
                          Text(customer.phone),
                        ],
                      ),

                      const SizedBox(height: 8),

                      Row(
                        crossAxisAlignment:
                            CrossAxisAlignment.start,
                        children: [
                          const Icon(
                            Icons.location_on,
                            color: Colors.red,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(customer.address),
                          ),
                        ],
                      ),

                      const SizedBox(height: 18),
                      Row(
                        children: [
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: () => _makePhoneCall(customer.phone),
                              icon: const Icon(Icons.call),
                              label: const Text("Call"),
                            ),
                          ),

                          const SizedBox(width: 10),

                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: () => _openGoogleMaps(
                                                  customer.latitude,
                                                  customer.longitude,
                                                ),
                              icon: const Icon(Icons.navigation),
                              label: const Text("Navigate"),
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 15),
                      SizedBox(
                        width: double.infinity,
                        child: ElevatedButton.icon(
                          icon: const Icon(Icons.build),
                          label: const Text("Installation"),
                          onPressed: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => InstallationScreen(
                                  customer: customer,
                                ),
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          );
        },
      ),
    );
  }
}