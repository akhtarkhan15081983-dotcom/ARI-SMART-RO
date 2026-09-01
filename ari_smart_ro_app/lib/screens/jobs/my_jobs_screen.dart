import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../models/job_model.dart';
import '../../services/job_service.dart';
import 'job_details_screen.dart';

class MyJobsScreen extends StatefulWidget {
  const MyJobsScreen({super.key});

  @override
  State<MyJobsScreen> createState() => _MyJobsScreenState();
}

class _MyJobsScreenState extends State<MyJobsScreen> {
  final JobService jobService = JobService();

  late Future<List<JobModel>> jobsFuture;

  @override
  void initState() {
    super.initState();
    loadJobs();
  }

  void loadJobs() {
    jobsFuture = jobService.getMyJobs();
  }

  Future<void> refreshJobs() async {
    setState(() {
      loadJobs();
    });
  }

  Future<void> callCustomer(String phone) async {
    final uri = Uri.parse("tel:$phone");

    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
  }

  Color statusColor(String status) {
    switch (status) {
      case "ASSIGNED":
        return Colors.orange;

      case "ACCEPTED":
        return Colors.blue;

      case "ON_THE_WAY":
        return Colors.deepPurple;

      case "ARRIVED":
        return Colors.teal;

      case "IN_PROGRESS":
        return Colors.indigo;

      case "COMPLETED":
        return Colors.green;

      case "CANCELLED":
        return Colors.red;

      default:
        return Colors.grey;
    }
  }

  Color priorityColor(String priority) {
    switch (priority) {
      case "HIGH":
        return Colors.red;

      case "MEDIUM":
        return Colors.orange;

      default:
        return Colors.green;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("My Jobs"), centerTitle: true),
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

            final jobs = snapshot.data ?? [];

            if (jobs.isEmpty) {
              return const Center(
                child: Text(
                  "No Jobs Available",
                  style: TextStyle(fontSize: 18),
                ),
              );
            }

            return ListView.builder(
              padding: const EdgeInsets.all(15),
              itemCount: jobs.length,
              itemBuilder: (context, index) {
                final job = jobs[index];
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
                          "Job ID : ${job.jobId}",
                          style: const TextStyle(fontWeight: FontWeight.bold),
                        ),

                        const SizedBox(height: 5),

                        Text("Job Type : ${job.jobType}"),

                        const SizedBox(height: 5),

                        Row(
                          children: [
                            const Text(
                              "Priority : ",
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
                          Text("Remarks : ${job.remarks}"),
                        ],

                        const SizedBox(height: 20),

                        Row(
                          children: [
                            Expanded(
                              child: ElevatedButton.icon(
                                icon: const Icon(Icons.call),
                                label: const Text("Call"),
                                onPressed: () {
                                  callCustomer(job.customerPhone);
                                },
                              ),
                            ),

                            const SizedBox(width: 10),

                            Expanded(
                              child: ElevatedButton.icon(
                                icon: const Icon(Icons.visibility),
                                label: const Text("Details"),
                                onPressed: () {
                                  Navigator.push(
                                    context,
                                    MaterialPageRoute(
                                      builder: (_) =>
                                          JobDetailsScreen(jobId: job.id),
                                    ),
                                  );
                                },
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
                              job.status == "ASSIGNED"
                                  ? "Accept Job"
                                  : "Open Job",
                            ),
                            onPressed: () async {
                              if (job.status == "ASSIGNED") {
                                final success = await jobService.acceptJob(
                                  job.id,
                                );

                                if (success) {
                                  if (!mounted) return;

                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(
                                      content: Text(
                                        "Job Accepted Successfully",
                                      ),
                                    ),
                                  );

                                  refreshJobs();
                                } else {
                                  ScaffoldMessenger.of(context).showSnackBar(
                                    const SnackBar(
                                      content: Text("Unable to Accept Job"),
                                    ),
                                  );
                                }
                              } else {
                                Navigator.push(
                                  context,
                                  MaterialPageRoute(
                                    builder: (_) =>
                                        JobDetailsScreen(jobId: job.id),
                                  ),
                                );
                              }
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
      ),
    );
  }
}
