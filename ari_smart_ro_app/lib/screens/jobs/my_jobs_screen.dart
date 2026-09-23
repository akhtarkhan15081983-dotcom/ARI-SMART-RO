import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../models/job_model.dart';
import '../../services/job_service.dart';
import '../../utils/search_utils.dart';
import 'job_details_screen.dart';
import 'secure_field_work_screen.dart';

class MyJobsScreen extends StatefulWidget {
  const MyJobsScreen({super.key});

  @override
  State<MyJobsScreen> createState() => _MyJobsScreenState();
}

class _MyJobsScreenState extends State<MyJobsScreen> {
  final JobService jobService = JobService();

  late Future<List<JobModel>> jobsFuture;
  final _searchController = TextEditingController();
  String _query = '';
  String _statusFilter = 'ALL';
  String _priorityFilter = 'ALL';

  @override
  void initState() {
    super.initState();
    loadJobs();
  }

  void loadJobs() {
    jobsFuture = jobService.getMyJobs();
  }

  Future<void> refreshJobs() async {
    setState(loadJobs);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> callCustomer(String phone) async {
    final uri = Uri.parse('tel:$phone');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  Future<void> _openJob(JobModel job) async {
    final type = job.jobType.trim().toUpperCase();
    final secureFieldWork = type == 'SERVICE' || type == 'COMPLAINT';
    final changed = await Navigator.push<bool>(
      context,
      MaterialPageRoute<bool>(
        builder: (_) => secureFieldWork
            ? SecureFieldWorkScreen(jobId: job.id)
            : JobDetailsScreen(jobId: job.id),
      ),
    );
    if (changed == true && mounted) {
      await refreshJobs();
    }
  }

  Color statusColor(String status) {
    switch (status) {
      case 'ASSIGNED':
        return Colors.orange;
      case 'ACCEPTED':
        return Colors.blue;
      case 'ON_THE_WAY':
        return Colors.deepPurple;
      case 'ARRIVED':
        return Colors.teal;
      case 'IN_PROGRESS':
        return Colors.indigo;
      case 'COMPLETED':
        return Colors.green;
      case 'CANCELLED':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  Color priorityColor(String priority) {
    switch (priority) {
      case 'HIGH':
        return Colors.red;
      case 'MEDIUM':
        return Colors.orange;
      default:
        return Colors.green;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My Jobs'), centerTitle: true),
      body: RefreshIndicator(
        onRefresh: refreshJobs,
        child: FutureBuilder<List<JobModel>>(
          future: jobsFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return Center(child: Text(snapshot.error.toString()));
            }

            final jobs = snapshot.data ?? <JobModel>[];
            final statuses = <String>{
              'ALL',
              ...jobs.map((j) => j.status.toUpperCase()),
            }.toList();
            final priorities = <String>{
              'ALL',
              ...jobs.map((j) => j.priority.toUpperCase()),
            }.toList();
            final filtered = jobs.where((job) {
              if (_statusFilter != 'ALL' &&
                  job.status.toUpperCase() != _statusFilter) {
                return false;
              }
              if (_priorityFilter != 'ALL' &&
                  job.priority.toUpperCase() != _priorityFilter) {
                return false;
              }
              return matchesAllSearchTerms(_query, [
                job.jobId,
                job.customerName,
                job.customerPhone,
                job.customerAddress,
                job.area,
                job.city,
                job.assetId,
                job.engineerName,
                job.jobType,
                job.priority,
                job.status,
                job.remarks,
              ]);
            }).toList();

            if (jobs.isEmpty) {
              return const Center(
                child: Text('No Jobs Available', style: TextStyle(fontSize: 18)),
              );
            }

            return Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(15, 12, 15, 6),
                  child: TextField(
                    controller: _searchController,
                    textInputAction: TextInputAction.search,
                    onChanged: (value) => setState(() => _query = value),
                    decoration: InputDecoration(
                      hintText: 'Search job ID, customer, phone, area, type...',
                      prefixIcon: const Icon(Icons.search),
                      suffixIcon: _query.isEmpty
                          ? null
                          : IconButton(
                              onPressed: () {
                                _searchController.clear();
                                setState(() => _query = '');
                              },
                              icon: const Icon(Icons.clear),
                            ),
                    ),
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 15),
                  child: Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          initialValue: _statusFilter,
                          decoration: const InputDecoration(labelText: 'Status'),
                          items: statuses
                              .map(
                                (v) => DropdownMenuItem(
                                  value: v,
                                  child: Text(
                                    v == 'ALL'
                                        ? 'All statuses'
                                        : v.replaceAll('_', ' '),
                                  ),
                                ),
                              )
                              .toList(),
                          onChanged: (v) =>
                              setState(() => _statusFilter = v ?? 'ALL'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          initialValue: _priorityFilter,
                          decoration: const InputDecoration(labelText: 'Priority'),
                          items: priorities
                              .map(
                                (v) => DropdownMenuItem(
                                  value: v,
                                  child: Text(v == 'ALL' ? 'All priorities' : v),
                                ),
                              )
                              .toList(),
                          onChanged: (v) =>
                              setState(() => _priorityFilter = v ?? 'ALL'),
                        ),
                      ),
                    ],
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(15, 8, 15, 0),
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text('${filtered.length} of ${jobs.length} jobs'),
                  ),
                ),
                Expanded(
                  child: filtered.isEmpty
                      ? const Center(child: Text('No matching jobs found'))
                      : ListView.builder(
                          padding: const EdgeInsets.all(15),
                          itemCount: filtered.length,
                          itemBuilder: (context, index) {
                            final job = filtered[index];
                            return Card(
                              margin: const EdgeInsets.only(bottom: 15),
                              elevation: 5,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(15),
                              ),
                              child: Padding(
                                padding: const EdgeInsets.all(15),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            job.customerName,
                                            style: const TextStyle(
                                              fontSize: 20,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 10,
                                            vertical: 5,
                                          ),
                                          decoration: BoxDecoration(
                                            color: statusColor(job.status),
                                            borderRadius: BorderRadius.circular(20),
                                          ),
                                          child: Text(
                                            job.status,
                                            style: const TextStyle(
                                              color: Colors.white,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 10),
                                    Text(
                                      'Job ID : ${job.jobId}',
                                      style: const TextStyle(fontWeight: FontWeight.bold),
                                    ),
                                    const SizedBox(height: 5),
                                    Text('Job Type : ${job.jobType}'),
                                    const SizedBox(height: 5),
                                    Row(
                                      children: [
                                        const Text(
                                          'Priority : ',
                                          style: TextStyle(fontWeight: FontWeight.bold),
                                        ),
                                        Text(
                                          job.priority,
                                          style: TextStyle(
                                            color: priorityColor(job.priority),
                                            fontWeight: FontWeight.bold,
                                          ),
                                        ),
                                      ],
                                    ),
                                    const Divider(height: 25),
                                    Row(
                                      children: [
                                        const Icon(Icons.phone, size: 18),
                                        const SizedBox(width: 8),
                                        Expanded(child: Text(job.customerPhone)),
                                      ],
                                    ),
                                    const SizedBox(height: 8),
                                    Row(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        const Icon(Icons.location_on, size: 18),
                                        const SizedBox(width: 8),
                                        Expanded(child: Text(job.customerAddress)),
                                      ],
                                    ),
                                    const SizedBox(height: 8),
                                    Row(
                                      children: [
                                        const Icon(Icons.calendar_today, size: 18),
                                        const SizedBox(width: 8),
                                        Expanded(child: Text(job.scheduledDate)),
                                      ],
                                    ),
                                    if (job.remarks.isNotEmpty) ...[
                                      const SizedBox(height: 10),
                                      Text('Remarks : ${job.remarks}'),
                                    ],
                                    const SizedBox(height: 20),
                                    Row(
                                      children: [
                                        Expanded(
                                          child: ElevatedButton.icon(
                                            icon: const Icon(Icons.call),
                                            label: const Text('Call'),
                                            onPressed: () => callCustomer(job.customerPhone),
                                          ),
                                        ),
                                        const SizedBox(width: 10),
                                        Expanded(
                                          child: ElevatedButton.icon(
                                            icon: const Icon(Icons.visibility),
                                            label: const Text('Details'),
                                            onPressed: () => _openJob(job),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 10),
                                    SizedBox(
                                      width: double.infinity,
                                      child: ElevatedButton.icon(
                                        icon: const Icon(Icons.check_circle),
                                        label: Text(
                                          job.status == 'ASSIGNED'
                                              ? 'Accept Job'
                                              : 'Open Job',
                                        ),
                                        onPressed: () async {
                                          if (job.status == 'ASSIGNED') {
                                            final success =
                                                await jobService.acceptJob(job.id);
                                            if (!mounted) return;
                                            if (success) {
                                              ScaffoldMessenger.of(context).showSnackBar(
                                                const SnackBar(
                                                  content: Text(
                                                    'Job Accepted Successfully',
                                                  ),
                                                ),
                                              );
                                              await refreshJobs();
                                            } else {
                                              ScaffoldMessenger.of(context).showSnackBar(
                                                const SnackBar(
                                                  content: Text('Unable to Accept Job'),
                                                ),
                                              );
                                            }
                                          } else {
                                            await _openJob(job);
                                          }
                                        },
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            );
                          },
                        ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
