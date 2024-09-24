import 'package:flutter/material.dart';

class HomePage extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Home'),
      ),
      body: Center(
        child: Text(
          'Welcome to Jobify.AI',
          style: TextStyle(fontSize: 24, color: Color.fromARGB(255, 60, 60, 120)),
        ),
      ),
    );
  }
}
