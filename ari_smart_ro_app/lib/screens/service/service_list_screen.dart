import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../models/service_model.dart';
import '../../services/service_service.dart';

class ServiceListScreen extends StatefulWidget {
  const ServiceListScreen({super.key});

  @override
  State<ServiceListScreen> createState() =>
      _ServiceListScreenState();
}

class _ServiceListScreenState
    extends State<ServiceListScreen> {
  final ServiceService _service =
      ServiceService();

  late Future<List<ServiceModel>>
      _futureServices;

  // ============================================================
  // SEARCH
  // ============================================================

  final TextEditingController
      _searchController =
      TextEditingController();

  String _searchQuery = "";

  // ============================================================
  // INIT
  // ============================================================

  @override
  void initState() {
    super.initState();

    _loadServices();
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
  // LOAD SERVICES
  // ============================================================

  void _loadServices() {
    _futureServices =
        _service.getServices();
  }

  // ============================================================
  // REFRESH
  // ============================================================

  Future<void> _refresh() async {
    setState(() {
      _loadServices();
    });

    await _futureServices;
  }

  // ============================================================
  // COMPLETE SERVICE
  // ============================================================

  Future<void> _completeService(
    int id,
  ) async {
    final success =
        await _service.completeService(id);

    if (!mounted) return;

    if (success) {
      ScaffoldMessenger.of(context)
          .showSnackBar(
        const SnackBar(
          content: Text(
            'Service completed successfully.',
          ),
        ),
      );

      setState(() {
        _loadServices();
      });
    } else {
      ScaffoldMessenger.of(context)
          .showSnackBar(
        const SnackBar(
          content: Text(
            'Failed to complete service.',
          ),
        ),
      );
    }
  }

  // ============================================================
  // EXPORT REPORT
  // ============================================================

  Future<void> _exportReport() async {
    try {
      final filePath =
          await _service.exportServicesExcel();

      if (!mounted) return;

      ScaffoldMessenger.of(context)
          .showSnackBar(
        SnackBar(
          content:
              Text('Export saved: $filePath'),
        ),
      );

      final uri = Uri.file(filePath);

      if (await canLaunchUrl(uri)) {
        await launchUrl(uri);
      }
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context)
          .showSnackBar(
        SnackBar(
          content:
              Text('Export failed: $e'),
        ),
      );
    }
  }

  // ============================================================
  // FILTER SERVICES
  // ============================================================

  List<ServiceModel> _filterServices(
    List<ServiceModel> services,
  ) {
    final query =
        _searchQuery.trim().toLowerCase();

    if (query.isEmpty) {
      return services;
    }

    return services.where((service) {
      final serviceId =
          service.serviceId.toLowerCase();

      final customerId =
          service.customer?.toString()
                  .toLowerCase() ??
              "";

      final engineerId =
          service.engineer?.toString()
                  .toLowerCase() ??
              "";

      final assetId =
          service.roAsset?.toString()
                  .toLowerCase() ??
              "";

      final serviceType =
          service.serviceType.toLowerCase();

      final status =
          service.status.toLowerCase();

      final scheduledDate =
          service.scheduledDate
              .toLowerCase();

      final completedDate =
          service.completedDate
                  ?.toLowerCase() ??
              "";

      final nextServiceDate =
          service.nextServiceDate
                  ?.toLowerCase() ??
              "";

      final remarks =
          service.remarks.toLowerCase();

      return serviceId.contains(query) ||
          customerId.contains(query) ||
          engineerId.contains(query) ||
          assetId.contains(query) ||
          serviceType.contains(query) ||
          status.contains(query) ||
          scheduledDate.contains(query) ||
          completedDate.contains(query) ||
          nextServiceDate.contains(query) ||
          remarks.contains(query);
    }).toList();
  }

  // ============================================================
  // SEARCH BOX
  // ============================================================

  Widget _buildSearchBox(
    int resultCount,
    int totalCount,
  ) {
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
          decoration: InputDecoration(
            hintText:
                'Search service, customer, engineer, status...',
            prefixIcon:
                const Icon(Icons.search),
            suffixIcon:
                _searchQuery.isEmpty
                    ? null
                    : IconButton(
                        tooltip:
                            'Clear search',
                        icon: const Icon(
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
            fillColor: Colors.white,
            border:
                OutlineInputBorder(
              borderRadius:
                  BorderRadius.circular(
                12,
              ),
            ),
            enabledBorder:
                OutlineInputBorder(
              borderRadius:
                  BorderRadius.circular(
                12,
              ),
              borderSide:
                  BorderSide(
                color:
                    Colors.grey.shade300,
              ),
            ),
            focusedBorder:
                OutlineInputBorder(
              borderRadius:
                  BorderRadius.circular(
                12,
              ),
              borderSide:
                  const BorderSide(
                width: 1.5,
              ),
            ),
          ),
        ),

        const SizedBox(height: 10),

        Row(
          mainAxisAlignment:
              MainAxisAlignment
                  .spaceBetween,
          children: [
            Text(
              _searchQuery.trim().isEmpty
                  ? '$totalCount service(s)'
                  : '$resultCount of $totalCount service(s)',
              style:
                  const TextStyle(
                fontWeight:
                    FontWeight.w600,
              ),
            ),

            if (_searchQuery
                .trim()
                .isNotEmpty)
              const Text(
                'Search active',
                style:
                    TextStyle(
                  fontSize: 12,
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
  // SERVICE CARD
  // ============================================================

  Widget _buildServiceCard(
    ServiceModel service,
  ) {
    return Card(
      margin:
          const EdgeInsets.only(
        bottom: 12,
      ),
      elevation: 4,
      shape:
          RoundedRectangleBorder(
        borderRadius:
            BorderRadius.circular(
          12,
        ),
      ),
      child: Padding(
        padding:
            const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            // ==================================================
            // HEADER
            // ==================================================

            Row(
              children: [
                Expanded(
                  child: Text(
                    service.serviceId,
                    style:
                        const TextStyle(
                      fontSize: 18,
                      fontWeight:
                          FontWeight.bold,
                    ),
                  ),
                ),

                Container(
                  padding:
                      const EdgeInsets
                          .symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  decoration:
                      BoxDecoration(
                    color:
                        _statusColor(
                      service.status,
                    ),
                    borderRadius:
                        BorderRadius
                            .circular(
                      20,
                    ),
                  ),
                  child: Text(
                    service.status,
                    style:
                        const TextStyle(
                      color:
                          Colors.white,
                      fontWeight:
                          FontWeight.bold,
                    ),
                  ),
                ),
              ],
            ),

            const SizedBox(
              height: 12,
            ),

            // ==================================================
            // DETAILS
            // ==================================================

            _buildInfoRow(
              'Service Type',
              service.serviceType,
            ),

            _buildInfoRow(
              'Scheduled',
              service.scheduledDate,
            ),

            _buildInfoRow(
              'Customer ID',
              service.customer
                      ?.toString() ??
                  '-',
            ),

            _buildInfoRow(
              'Engineer ID',
              service.engineer
                      ?.toString() ??
                  '-',
            ),

            _buildInfoRow(
              'Asset ID',
              service.roAsset
                      ?.toString() ??
                  '-',
            ),

            if (service.nextServiceDate !=
                null)
              _buildInfoRow(
                'Next Service',
                service.nextServiceDate!,
              ),

            if (service.completedDate !=
                null)
              _buildInfoRow(
                'Completed',
                service.completedDate!,
              ),

            if (service.remarks
                .isNotEmpty) ...[
              const SizedBox(
                height: 8,
              ),

              Text(
                'Remarks: ${service.remarks}',
              ),
            ],

            const SizedBox(
              height: 12,
            ),

            // ==================================================
            // ACTIONS
            // ==================================================

            Row(
              children: [
                Expanded(
                  child:
                      ElevatedButton.icon(
                    onPressed: () {
                      Navigator.of(
                        context,
                      ).push(
                        MaterialPageRoute(
                          builder: (_) =>
                              ServiceDetailScreen(
                            service:
                                service,
                            onCompleted:
                                _completeService,
                          ),
                        ),
                      );
                    },
                    icon:
                        const Icon(
                      Icons.visibility,
                    ),
                    label:
                        const Text(
                      'View',
                    ),
                  ),
                ),

                if (service.status
                        .toUpperCase() !=
                    'COMPLETED') ...[
                  const SizedBox(
                    width: 10,
                  ),

                  Expanded(
                    child:
                        ElevatedButton.icon(
                      onPressed: () =>
                          _completeService(
                        service.id,
                      ),
                      style:
                          ElevatedButton
                              .styleFrom(
                        backgroundColor:
                            Colors.green,
                      ),
                      icon:
                          const Icon(
                        Icons.check,
                      ),
                      label:
                          const Text(
                        'Complete',
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ],
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
    return Scaffold(
      appBar: AppBar(
        title:
            const Text(
          'Service Requests',
        ),
        centerTitle: true,
        actions: [
          IconButton(
            icon:
                const Icon(
              Icons.file_download,
            ),
            tooltip:
                'Export Service Report',
            onPressed:
                _exportReport,
          ),
        ],
      ),

      body:
          RefreshIndicator(
        onRefresh: _refresh,

        child:
            FutureBuilder<
                List<ServiceModel>>(
          future:
              _futureServices,

          builder:
              (context, snapshot) {
            // ================================================
            // LOADING
            // ================================================

            if (snapshot
                    .connectionState ==
                ConnectionState
                    .waiting) {
              return const Center(
                child:
                    CircularProgressIndicator(),
              );
            }

            // ================================================
            // ERROR
            // ================================================

            if (snapshot.hasError) {
              return ListView(
                physics:
                    const AlwaysScrollableScrollPhysics(),
                children: [
                  SizedBox(
                    height:
                        MediaQuery.of(
                          context,
                        ).size.height *
                        0.65,
                    child:
                        Center(
                      child:
                          Padding(
                        padding:
                            const EdgeInsets
                                .all(
                          24,
                        ),
                        child:
                            Column(
                          mainAxisSize:
                              MainAxisSize
                                  .min,
                          children: [
                            const Icon(
                              Icons
                                  .error_outline,
                              size: 60,
                            ),

                            const SizedBox(
                              height: 16,
                            ),

                            Text(
                              snapshot.error
                                      ?.toString() ??
                                  'Unable to load services.',
                              textAlign:
                                  TextAlign
                                      .center,
                            ),

                            const SizedBox(
                              height: 20,
                            ),

                            ElevatedButton
                                .icon(
                              onPressed:
                                  () {
                                setState(
                                  () {
                                    _loadServices();
                                  },
                                );
                              },
                              icon:
                                  const Icon(
                                Icons.refresh,
                              ),
                              label:
                                  const Text(
                                'Retry',
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              );
            }

            // ================================================
            // ALL SERVICES
            // ================================================

            final allServices =
                snapshot.data ?? [];

            // ================================================
            // FILTERED SERVICES
            // ================================================

            final services =
                _filterServices(
              allServices,
            );

            // ================================================
            // NO RECORDS
            // ================================================

            if (allServices.isEmpty) {
              return ListView(
                physics:
                    const AlwaysScrollableScrollPhysics(),
                children: [
                  SizedBox(
                    height:
                        MediaQuery.of(
                          context,
                        ).size.height *
                        0.65,
                    child:
                        const Center(
                      child:
                          Text(
                        'No service records found.',
                      ),
                    ),
                  ),
                ],
              );
            }

            // ================================================
            // SEARCH RESULT EMPTY
            // ================================================

            if (services.isEmpty) {
              return ListView(
                physics:
                    const AlwaysScrollableScrollPhysics(),
                padding:
                    const EdgeInsets.all(
                  12,
                ),
                children: [
                  _buildSearchBox(
                    services.length,
                    allServices.length,
                  ),

                  const SizedBox(
                    height: 30,
                  ),

                  Center(
                    child:
                        Column(
                      children: [
                        Icon(
                          Icons
                              .search_off,
                          size: 60,
                          color:
                              Colors.grey
                                  .shade500,
                        ),

                        const SizedBox(
                          height: 12,
                        ),

                        const Text(
                          'No matching service found.',
                          style:
                              TextStyle(
                            fontSize:
                                16,
                            fontWeight:
                                FontWeight
                                    .w600,
                          ),
                        ),

                        const SizedBox(
                          height: 6,
                        ),

                        Text(
                          'Try Service ID, Customer ID, Engineer ID, status or service type.',
                          textAlign:
                              TextAlign
                                  .center,
                          style:
                              TextStyle(
                            color:
                                Colors.grey
                                    .shade600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              );
            }

            // ================================================
            // SERVICE LIST
            // ================================================

            return ListView(
              physics:
                  const AlwaysScrollableScrollPhysics(),
              padding:
                  const EdgeInsets.all(
                12,
              ),
              children: [
                _buildSearchBox(
                  services.length,
                  allServices.length,
                ),

                const SizedBox(
                  height: 12,
                ),

                ...services.map(
                  _buildServiceCard,
                ),
              ],
            );
          },
        ),
      ),
    );
  }

  // ============================================================
  // STATUS COLOR
  // ============================================================

  Color _statusColor(
    String status,
  ) {
    switch (
        status.toUpperCase()) {
      case 'PENDING':
        return Colors.orange;

      case 'IN_PROGRESS':
        return Colors.blue;

      case 'COMPLETED':
        return Colors.green;

      case 'CANCELLED':
        return Colors.red;

      default:
        return Colors.grey;
    }
  }

  // ============================================================
  // INFO ROW
  // ============================================================

  Widget _buildInfoRow(
    String label,
    String value,
  ) {
    return Padding(
      padding:
          const EdgeInsets.only(
        bottom: 6,
      ),
      child: Row(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children: [
          Text(
            '$label: ',
            style:
                const TextStyle(
              fontWeight:
                  FontWeight.bold,
            ),
          ),

          Expanded(
            child: Text(
              value.isEmpty
                  ? '-'
                  : value,
            ),
          ),
        ],
      ),
    );
  }
}


// ==================================================================
// SERVICE DETAIL SCREEN
// ==================================================================

class ServiceDetailScreen
    extends StatefulWidget {
  const ServiceDetailScreen({
    super.key,
    required this.service,
    required this.onCompleted,
  });

  final ServiceModel service;

  final Future<void> Function(
    int id,
  ) onCompleted;

  @override
  State<ServiceDetailScreen>
      createState() =>
          _ServiceDetailScreenState();
}

class _ServiceDetailScreenState
    extends State<ServiceDetailScreen> {
  bool _isCompleting = false;

  // ============================================================
  // MARK COMPLETED
  // ============================================================

  Future<void> _markCompleted() async {
    setState(() {
      _isCompleting = true;
    });

    await widget.onCompleted(
      widget.service.id,
    );

    if (!mounted) return;

    setState(() {
      _isCompleting = false;
    });

    Navigator.pop(context);
  }

  // ============================================================
  // BUILD
  // ============================================================

  @override
  Widget build(
    BuildContext context,
  ) {
    return Scaffold(
      appBar: AppBar(
        title:
            const Text(
          'Service Details',
        ),
        centerTitle: true,
      ),

      body: Padding(
        padding:
            const EdgeInsets.all(16),

        child: Column(
          crossAxisAlignment:
              CrossAxisAlignment.start,
          children: [
            // ==================================================
            // SERVICE ID
            // ==================================================

            Text(
              widget.service.serviceId,
              style:
                  const TextStyle(
                fontSize: 22,
                fontWeight:
                    FontWeight.bold,
              ),
            ),

            const SizedBox(
              height: 12,
            ),

            // ==================================================
            // DETAILS
            // ==================================================

            _buildDetail(
              'Status',
              widget.service.status,
            ),

            _buildDetail(
              'Type',
              widget.service.serviceType,
            ),

            _buildDetail(
              'Scheduled',
              widget.service.scheduledDate,
            ),

            _buildDetail(
              'Customer ID',
              widget.service.customer
                      ?.toString() ??
                  '-',
            ),

            _buildDetail(
              'Engineer ID',
              widget.service.engineer
                      ?.toString() ??
                  '-',
            ),

            _buildDetail(
              'Asset ID',
              widget.service.roAsset
                      ?.toString() ??
                  '-',
            ),

            if (widget
                    .service
                    .nextServiceDate !=
                null)
              _buildDetail(
                'Next Service',
                widget.service
                    .nextServiceDate!,
              ),

            if (widget
                    .service
                    .completedDate !=
                null)
              _buildDetail(
                'Completed',
                widget.service
                    .completedDate!,
              ),

            if (widget
                .service
                .remarks
                .isNotEmpty)
              _buildDetail(
                'Remarks',
                widget.service
                    .remarks,
              ),

            const Spacer(),

            // ==================================================
            // COMPLETE BUTTON
            // ==================================================

            if (widget
                    .service
                    .status
                    .toUpperCase() !=
                'COMPLETED')
              SizedBox(
                width:
                    double.infinity,
                child:
                    ElevatedButton(
                  onPressed:
                      _isCompleting
                          ? null
                          : _markCompleted,

                  style:
                      ElevatedButton
                          .styleFrom(
                    backgroundColor:
                        Colors.green,
                    padding:
                        const EdgeInsets
                            .symmetric(
                      vertical: 14,
                    ),
                  ),

                  child:
                      _isCompleting
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child:
                                  CircularProgressIndicator(
                                color:
                                    Colors.white,
                                strokeWidth:
                                    2,
                              ),
                            )
                          : const Text(
                              'Mark Completed',
                            ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  // ============================================================
  // DETAIL ROW
  // ============================================================

  Widget _buildDetail(
    String label,
    String value,
  ) {
    return Padding(
      padding:
          const EdgeInsets.only(
        bottom: 10,
      ),
      child: Row(
        crossAxisAlignment:
            CrossAxisAlignment.start,
        children: [
          Text(
            '$label: ',
            style:
                const TextStyle(
              fontWeight:
                  FontWeight.bold,
            ),
          ),

          Expanded(
            child: Text(
              value.isEmpty
                  ? '-'
                  : value,
            ),
          ),
        ],
      ),
    );
  }
}