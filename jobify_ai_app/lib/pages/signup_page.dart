import 'package:flutter/material.dart';
import 'package:cloud_firestore/cloud_firestore.dart';

class SignUpPage extends StatefulWidget {
  @override
  _SignUpPageState createState() => _SignUpPageState();
}

class _SignUpPageState extends State<SignUpPage> {
  final _formKey = GlobalKey<FormState>();
  String firstName = '', lastName = '', email = '', currentJob = '';
  bool isStudent = false;
  String institution = '';

  final FirebaseFirestore _firestore = FirebaseFirestore.instance;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Sign Up'),
        automaticallyImplyLeading: false,
        backgroundColor: Color.fromARGB(255, 60, 60, 120),
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                SizedBox(height: 40),
                Image.asset('assets/logo1.png', height: 150), 
                SizedBox(height: 40),
                TextFormField(
                  decoration: InputDecoration(labelText: 'First Name*'),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter your first name';
                    }
                    return null;
                  },
                  onSaved: (value) => firstName = value!,
                ),
                TextFormField(
                  decoration: InputDecoration(labelText: 'Last Name*'),
                  validator: (value) {
                    if (value == null || value.isEmpty) {
                      return 'Please enter your last name';
                    }
                    return null;
                  },
                  onSaved: (value) => lastName = value!,
                ),
                TextFormField(
                  decoration: InputDecoration(labelText: 'Email*'),
                  validator: (value) {
                    if (value == null || !value.contains('@')) {
                      return 'Please enter a valid email';
                    }
                    return null;
                  },
                  onSaved: (value) => email = value!,
                ),
                TextFormField(
                  decoration: InputDecoration(labelText: 'Current Job (Optional)'),
                  onSaved: (value) => currentJob = value!,
                ),
                SwitchListTile(
                  title: Text('Are you currently a Student?*'),
                  value: isStudent,
                  onChanged: (bool value) {
                    setState(() {
                      isStudent = value;
                    });
                  },
                ),
                if (isStudent)
                  TextFormField(
                    decoration: InputDecoration(labelText: 'Institution Name*'),
                    validator: (value) {
                      if (isStudent && (value == null || value.isEmpty)) {
                        return 'Please enter your institution name';
                      }
                      return null;
                    },
                    onSaved: (value) => institution = value!,
                  ),
                SizedBox(height: 20),
                ElevatedButton(
                  onPressed: _submitForm,
                  child: Text('Submit Sign Up Request',
                      style: TextStyle(
                        color: Colors.black,
                      ),
                    ),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Color.fromARGB(255, 60, 60, 120),
                  ),
                ),
                SizedBox(height: 20),
                TextButton(
                  onPressed: () {
                    Navigator.pushReplacementNamed(context, '/login');
                  },
                  child: Text('Already have an account? Login',
                    style: TextStyle(
                      color: Colors.black,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _submitForm() async {
    if (_formKey.currentState!.validate()) {
      _formKey.currentState!.save();
      try {
        await _firestore.collection('Signup Requests').add({
          'first_name': firstName,
          'last_name': lastName,
          'email': email,
          'current_job': currentJob.isEmpty ? null : currentJob,
          'is_student': isStudent,
          'institution': isStudent ? institution : null,
          'submitted_at': Timestamp.now(),
        });

        showDialog(
          context: context,
          builder: (context) => AlertDialog(
            title: Text('Request Submitted'),
            content: Text('Your sign-up request has been submitted.'),
            actions: <Widget>[
              TextButton(
                onPressed: () {
                  Navigator.pop(context);
                  Navigator.pushReplacementNamed(context, '/login');
                },
                child: Text('OK'),
              ),
            ],
          ),
        );
      } catch (e) {
        print('Error submitting signup request: $e');
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error submitting request. Please try again.')),
        );
      }
    }
  }
}
