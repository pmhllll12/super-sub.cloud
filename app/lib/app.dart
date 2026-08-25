import 'package:flutter/material.dart';

import 'core/theme/app_theme.dart';

class SuperSubApp extends StatelessWidget {
  const SuperSubApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Super-Sub',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      home: const Scaffold(
        body: Center(child: Text('Super-Sub')),
      ),
    );
  }
}
