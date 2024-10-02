import 'package:flutter/material.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class DashboardPage extends StatefulWidget {
  @override
  _DashboardPageState createState() => _DashboardPageState();
}

class _DashboardPageState extends State<DashboardPage> {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  int appliedCount = 0;
  int rejectionCount = 0;
  int oaCount = 0;
  int interviewCount = 0;
  int offerCount = 0;

  @override
  void initState() {
    super.initState();
    fetchApplicationData();
  }

  Future<void> fetchApplicationData() async {
    User? user = _auth.currentUser;
    if (user != null) {
      String email = user.email!;

      // Fetch the number of documents in each subcollection
      appliedCount = await getCollectionCount(email, 'Applied');
      rejectionCount = await getCollectionCount(email, 'Rejection');
      oaCount = await getCollectionCount(email, 'OA');
      interviewCount = await getCollectionCount(email, 'Interview');
      offerCount = await getCollectionCount(email, 'Offer');

      setState(() {});  // Update UI with new counts
    } else {
      print("No user signed in.");
    }
  }

  Future<int> getCollectionCount(String email, String collectionName) async {
    QuerySnapshot snapshot = await _firestore
        .collection('Users')
        .doc(email)
        .collection(collectionName)
        .get();
    return snapshot.docs.length;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Dashboard')),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            Text(
              "Job Application Overview",
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            ),
            SizedBox(height: 20),
            buildStatCard("Total Applications", appliedCount, Colors.blue),
            buildStatCard("Rejections", rejectionCount, Colors.red),
            buildStatCard("Online Assessments", oaCount, Colors.orange),
            buildStatCard("Interviews", interviewCount, Colors.green),
            buildStatCard("Offers", offerCount, Colors.purple),
          ],
        ),
      ),
    );
  }

  Widget buildStatCard(String title, int count, Color color) {
    return Card(
      margin: EdgeInsets.symmetric(vertical: 10),
      child: ListTile(
        title: Text(title, style: TextStyle(fontSize: 18)),
        trailing: CircleAvatar(
          backgroundColor: color,
          child: Text(count.toString(), style: TextStyle(color: Colors.white)),
        ),
      ),
    );
  }
}
