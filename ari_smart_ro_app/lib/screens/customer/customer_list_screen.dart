import 'package:flutter/material.dart';

import '../../models/customer_model.dart';
import '../../services/customer_service.dart';
import '../../services/engineer_service.dart';
import '../../services/api_service.dart';
import '../../models/engineer_model.dart';

import 'customer_details_screen.dart';

class CustomerListScreen extends StatefulWidget {
  const CustomerListScreen({
    super.key,
  });

  @override
  State<CustomerListScreen> createState() =>
      _CustomerListScreenState();
}

class _CustomerListScreenState
    extends State<CustomerListScreen> {
  // ============================================================
  // SERVICES
  // ============================================================

  final CustomerService service =
      CustomerService();

  final EngineerService engineerService =
      EngineerService();

  // ============================================================
  // SEARCH
  // ============================================================

  final TextEditingController _searchController =
      TextEditingController();

  String _searchQuery = "";

  // ============================================================
  // ROLE
  // ============================================================

  String _role = "";

  // ============================================================
  // CUSTOMERS
  // ============================================================

  List<CustomerModel> _customers = [];

  bool _isLoading = true;

  // ============================================================
  // FILTERED CUSTOMERS
  // ============================================================

  List<CustomerModel> get _filteredCustomers {
    final query =
        _searchQuery.trim().toLowerCase();

    if (query.isEmpty) {
      return _customers;
    }

    return _customers.where(
      (customer) {
        return customer.customerName
                .toLowerCase()
                .contains(query) ||
            customer.customerId
                .toLowerCase()
                .contains(query) ||
            customer.phone
                .toLowerCase()
                .contains(query) ||
            customer.cardNumber
                .toLowerCase()
                .contains(query) ||
            customer.oldCardNumber
                .toLowerCase()
                .contains(query) ||
            customer.area
                .toLowerCase()
                .contains(query) ||
            customer.address
                .toLowerCase()
                .contains(query) ||
            customer.roModel
                .toLowerCase()
                .contains(query) ||
            customer.engineerName
                .toLowerCase()
                .contains(query);
      },
    ).toList();
  }

  // ============================================================
  // INIT
  // ============================================================

  @override
  void initState() {
    super.initState();

    _loadRole();

    _loadCustomers();
  }

  // ============================================================
  // DISPOSE
  // ============================================================

  @override
  void dispose() {
    _searchController.dispose();

    super.dispose();
  }

  // ============================================================
  // LOAD ROLE
  // ============================================================

  Future<void> _loadRole() async {
    try {
      final role =
          await ApiService.getRole();

      if (!mounted) {
        return;
      }

      setState(() {
        _role =
            role?.trim().toUpperCase() ?? "";
      });
    } catch (e) {
      debugPrint(
        "CUSTOMER LIST ROLE ERROR: $e",
      );
    }
  }

  // ============================================================
  // LOAD CUSTOMERS
  // ============================================================

  Future<void> _loadCustomers() async {
    if (mounted) {
      setState(() {
        _isLoading = true;
      });
    }

    try {
      final customers =
          await service.getCustomers();

      if (!mounted) {
        return;
      }

      setState(() {
        _customers = customers;

        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) {
        return;
      }

      setState(() {
        _customers = [];

        _isLoading = false;
      });

      ScaffoldMessenger.of(context)
          .showSnackBar(
        SnackBar(
          content: Text(
            "Failed to load customers: $e",
          ),
        ),
      );
    }
  }

  // ============================================================
  // OPEN CUSTOMER DETAILS
  // ============================================================

  void _openCustomerDetails(
    CustomerModel customer,
  ) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) =>
            CustomerDetailsScreen(
          customer: customer,
        ),
      ),
    );
  }

  // ============================================================
  // ASSIGN / REASSIGN CUSTOMER
  // ============================================================

  Future<void> showEngineerDialog(
    CustomerModel customer,
  ) async {
    try {
      final engineers =
          await engineerService
              .getEngineers();

      if (!mounted) {
        return;
      }

      final messenger =
          ScaffoldMessenger.of(context);

      showDialog(
        context: context,
        builder: (dialogContext) {
          return AlertDialog(
            title: const Text(
              "Assign Engineer",
            ),

            content: SizedBox(
              width: double.maxFinite,

              child: ListView.builder(
                shrinkWrap: true,

                itemCount:
                    engineers.length,

                itemBuilder:
                    (context, index) {
                  final EngineerModel
                      engineer =
                      engineers[index];

                  return ListTile(
                    leading:
                        const Icon(
                      Icons.engineering,
                    ),

                    title: Text(
                      engineer.name,
                    ),

                    subtitle: Text(
                      engineer.phone,
                    ),

                    onTap: () async {
                      Navigator.pop(
                        dialogContext,
                      );

                      final bool success =
                          await service
                              .assignCustomer(
                        customerId:
                            customer.id,

                        employeeId:
                            engineer.id,
                      );

                      if (!mounted) {
                        return;
                      }

                      if (success) {
                        messenger
                            .showSnackBar(
                          SnackBar(
                            content: Text(
                              "${engineer.name} Assigned Successfully",
                            ),
                          ),
                        );

                        await _loadCustomers();
                      } else {
                        messenger
                            .showSnackBar(
                          const SnackBar(
                            content: Text(
                              "Assignment Failed",
                            ),
                          ),
                        );
                      }
                    },
                  );
                },
              ),
            ),
          );
        },
      );
    } catch (e) {
      if (!mounted) {
        return;
      }

      ScaffoldMessenger.of(context)
          .showSnackBar(
        SnackBar(
          content: Text(
            e.toString(),
          ),
        ),
      );
    }
  }

  // ============================================================
  // SEARCH BOX
  // ============================================================

  Widget _buildSearchBox() {
    return Column(
      crossAxisAlignment:
          CrossAxisAlignment.start,

      children: [
        TextField(
          controller:
              _searchController,

          onChanged: (value) {
            setState(() {
              _searchQuery = value;
            });
          },

          textInputAction:
              TextInputAction.search,

          decoration:
              InputDecoration(
            hintText:
                "Search name, ID, phone, card or old card...",

            prefixIcon:
                const Icon(
              Icons.search,
            ),

            suffixIcon:
                _searchQuery.isEmpty
                    ? null
                    : IconButton(
                        tooltip:
                            "Clear search",

                        icon:
                            const Icon(
                          Icons.clear,
                        ),

                        onPressed: () {
                          _searchController
                              .clear();

                          setState(() {
                            _searchQuery =
                                "";
                          });
                        },
                      ),

            filled: true,

            fillColor:
                Theme.of(context)
                    .colorScheme
                    .surface,

            border:
                OutlineInputBorder(
              borderRadius:
                  BorderRadius.circular(
                14,
              ),
            ),
          ),
        ),

        const SizedBox(
          height: 8,
        ),

        Row(
          children: [
            const Icon(
              Icons.people_alt_outlined,
              size: 18,
            ),

            const SizedBox(
              width: 6,
            ),

            Text(
              _searchQuery
                      .trim()
                      .isEmpty
                  ? "${_customers.length} customers"
                  : "${_filteredCustomers.length} customers found",

              style: TextStyle(
                color:
                    Colors.grey.shade700,

                fontWeight:
                    FontWeight.w600,
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ============================================================
  // CUSTOMER CARD
  // ============================================================

  Widget _buildCustomerCard(
    CustomerModel customer,
    int index,
  ) {
    return Card(
      elevation: 3,

      margin:
          const EdgeInsets.only(
        bottom: 12,
      ),

      shape:
          RoundedRectangleBorder(
        borderRadius:
            BorderRadius.circular(
          12,
        ),
      ),

      child: InkWell(
        borderRadius:
            BorderRadius.circular(
          12,
        ),

        // ======================================================
        // CARD TAP
        // ======================================================

        onTap: _role == "OFFICE"
            ? null
            : () {
                _openCustomerDetails(
                  customer,
                );
              },

        child: Padding(
          padding:
              const EdgeInsets.all(
            12,
          ),

          child: Column(
            crossAxisAlignment:
                CrossAxisAlignment.start,

            children: [
              // ==================================================
              // CUSTOMER HEADER
              // ==================================================

              Row(
                children: [
                  CircleAvatar(
                    child: Text(
                      "${index + 1}",
                    ),
                  ),

                  const SizedBox(
                    width: 12,
                  ),

                  Expanded(
                    child: Column(
                      crossAxisAlignment:
                          CrossAxisAlignment
                              .start,

                      children: [
                        Text(
                          customer
                              .customerName,

                          style:
                              const TextStyle(
                            fontSize: 18,
                            fontWeight:
                                FontWeight.bold,
                          ),
                        ),

                        Text(
                          customer.phone,

                          style:
                              const TextStyle(
                            color:
                                Colors.grey,
                          ),
                        ),
                      ],
                    ),
                  ),

                  // =================================================
                  // DETAILS INDICATOR
                  // =================================================

                  if (_role != "OFFICE")
                    const Icon(
                      Icons
                          .arrow_forward_ios,
                      size: 16,
                      color: Colors.grey,
                    ),
                ],
              ),

              const Divider(
                height: 20,
              ),

              // ==================================================
              // CUSTOMER ID
              // ==================================================

              Text(
                "Customer ID : "
                "${customer.customerId}",
              ),

              const SizedBox(
                height: 5,
              ),

              // ==================================================
              // CURRENT CARD
              // ==================================================

              Text(
                "Card No : "
                "${customer.cardNumber}",
              ),

              // ==================================================
              // OLD CARD
              // ==================================================

              if (customer
                  .oldCardNumber
                  .trim()
                  .isNotEmpty) ...[
                const SizedBox(
                  height: 5,
                ),

                Text(
                  "Old Card No : "
                  "${customer.oldCardNumber}",
                ),
              ],

              const SizedBox(
                height: 5,
              ),

              // ==================================================
              // AREA
              // ==================================================

              Text(
                "Area : "
                "${customer.area}",
              ),

              const SizedBox(
                height: 5,
              ),

              // ==================================================
              // ADDRESS
              // ==================================================

              Text(
                "Address : "
                "${customer.address}",
              ),

              const SizedBox(
                height: 5,
              ),

              // ==================================================
              // RO MODEL
              // ==================================================

              Text(
                "RO Model : "
                "${customer.roModel}",
              ),

              const SizedBox(
                height: 5,
              ),

              // ==================================================
              // MONTHLY RENT
              // ==================================================

              Text(
                "Monthly Rent : "
                "₹${customer.monthlyRent}",
              ),

              const SizedBox(
                height: 5,
              ),

              // ==================================================
              // INSTALLATION
              // ==================================================

              Text(
                "Installation : "
                "₹${customer.installationCharge}",
              ),

              const SizedBox(
                height: 8,
              ),

              // ==================================================
              // ASSIGNED ENGINEER
              // ==================================================

              if (customer.assignedEngineer !=
                  null)
                Text(
                  "Assigned Employee : "
                  "${customer.engineerName}",

                  style:
                      const TextStyle(
                    color:
                        Colors.green,

                    fontWeight:
                        FontWeight.bold,
                  ),
                )
              else
                const Text(
                  "Assigned Employee : "
                  "Not Assigned",

                  style:
                      TextStyle(
                    color:
                        Colors.red,

                    fontWeight:
                        FontWeight.bold,
                  ),
                ),

              // ==================================================
              // ASSIGN / REASSIGN
              // ENGINEER MUST NOT SEE THIS
              // ==================================================

              if (_role != "ENGINEER") ...[
                const SizedBox(
                  height: 15,
                ),

                Align(
                  alignment:
                      Alignment.centerRight,

                  child:
                      ElevatedButton.icon(
                    onPressed: () {
                      showEngineerDialog(
                        customer,
                      );
                    },

                    icon:
                        const Icon(
                      Icons.person_add,
                    ),

                    label: Text(
                      customer
                                  .assignedEngineer ==
                              null
                          ? "Assign"
                          : "Reassign",
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(
    BuildContext context,
  ) {
    final filtered =
        _filteredCustomers;

    return Scaffold(
      appBar: AppBar(
        title:
            const Text(
          "Customer List",
        ),

        centerTitle: true,

        actions: [
          IconButton(
            tooltip:
                "Refresh",

            onPressed:
                _loadCustomers,

            icon:
                const Icon(
              Icons.refresh,
            ),
          ),
        ],
      ),

      body:
          _isLoading
              ? const Center(
                  child:
                      CircularProgressIndicator(),
                )
              : RefreshIndicator(
                  onRefresh:
                      _loadCustomers,

                  child: ListView(
                    padding:
                        const EdgeInsets
                            .all(
                      10,
                    ),

                    children: [
                      // ==========================================
                      // SEARCH
                      // ==========================================

                      _buildSearchBox(),

                      const SizedBox(
                        height: 12,
                      ),

                      // ==========================================
                      // NO CUSTOMERS
                      // ==========================================

                      if (_customers.isEmpty)
                        const Padding(
                          padding:
                              EdgeInsets.only(
                            top: 80,
                          ),

                          child: Center(
                            child: Text(
                              "No Customers Found",
                            ),
                          ),
                        )

                      // ==========================================
                      // NO SEARCH RESULT
                      // ==========================================

                      else if (filtered
                          .isEmpty)
                        Padding(
                          padding:
                              const EdgeInsets
                                  .only(
                            top: 80,
                          ),

                          child:
                              Column(
                            children: [
                              Icon(
                                Icons
                                    .person_search,
                                size: 60,
                                color: Colors
                                    .grey
                                    .shade500,
                              ),

                              const SizedBox(
                                height: 12,
                              ),

                              const Text(
                                "No matching customer found",

                                style:
                                    TextStyle(
                                  fontSize:
                                      17,
                                  fontWeight:
                                      FontWeight
                                          .w600,
                                ),
                              ),

                              const SizedBox(
                                height: 6,
                              ),

                              Text(
                                "Try name, Customer ID, phone, current card or old card number.",

                                textAlign:
                                    TextAlign
                                        .center,

                                style:
                                    TextStyle(
                                  color: Colors
                                      .grey
                                      .shade600,
                                ),
                              ),
                            ],
                          ),
                        )

                      // ==========================================
                      // CUSTOMER CARDS
                      // ==========================================

                      else
                        ...List.generate(
                          filtered.length,
                          (index) =>
                              _buildCustomerCard(
                            filtered[index],
                            index,
                          ),
                        ),
                    ],
                  ),
                ),
    );
  }
}
