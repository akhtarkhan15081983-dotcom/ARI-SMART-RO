import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:signature/signature.dart';

class SignatureScreen extends StatefulWidget {
  const SignatureScreen({super.key});

  @override
  State<SignatureScreen> createState() => _SignatureScreenState();
}

class _SignatureScreenState extends State<SignatureScreen> {

  final SignatureController controller = SignatureController(
    penStrokeWidth: 3,
    penColor: Colors.black,
  );

  @override
  void dispose() {
    controller.dispose();
    super.dispose();
  }

  Future<void> _save() async {

    if (controller.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Please sign first"),
        ),
      );
      return;
    }

    Uint8List? data = await controller.toPngBytes();

    if (!mounted) return;

    Navigator.pop(context, data);
  }

  @override
  Widget build(BuildContext context) {

    return Scaffold(

      appBar: AppBar(
        title: const Text("Customer Signature"),
      ),

      body: Column(

        children: [

          Expanded(

            child: Container(

              margin: const EdgeInsets.all(15),

              decoration: BoxDecoration(
                border: Border.all(color: Colors.grey),
              ),

              child: Signature(
                controller: controller,
                backgroundColor: Colors.white,
              ),
            ),
          ),

          Padding(

            padding: const EdgeInsets.all(16),

            child: Row(

              children: [

                Expanded(

                  child: ElevatedButton(

                    onPressed: () {
                      controller.clear();
                    },

                    child: const Text("Clear"),
                  ),
                ),

                const SizedBox(width: 10),

                Expanded(

                  child: ElevatedButton(

                    onPressed: _save,

                    child: const Text("Save"),
                  ),
                ),

              ],
            ),
          )

        ],
      ),
    );
  }
}