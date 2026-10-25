import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'screens/auth_screens.dart';
import 'screens/home_screen.dart';
import 'screens/onboarding_screen.dart';
import 'state/session.dart';

void main() {
  runApp(ChangeNotifierProvider(create: (_) => Session()..load(), child: const CarbonGuardApp()));
}

const brandGreen = Color(0xFF1F7A4D);

class CarbonGuardApp extends StatelessWidget {
  const CarbonGuardApp({super.key});

  @override
  Widget build(BuildContext context) {
    final scheme = ColorScheme.fromSeed(seedColor: brandGreen);
    return MaterialApp(
      title: 'Carbon Guard',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: scheme,
        useMaterial3: true,
        scaffoldBackgroundColor: const Color(0xFFF4F7F5),
        appBarTheme: const AppBarTheme(backgroundColor: Color(0xFFF4F7F5), centerTitle: false),
        inputDecorationTheme: const InputDecorationTheme(border: OutlineInputBorder(), filled: true, fillColor: Colors.white),
      ),
      home: const _Root(),
    );
  }
}

/// Chooses the first screen: splash -> onboarding (first run) -> login -> home.
class _Root extends StatelessWidget {
  const _Root();

  @override
  Widget build(BuildContext context) {
    final session = context.watch<Session>();
    if (!session.ready) return const SplashScreen();
    if (!session.onboardingDone) return const OnboardingScreen();
    if (!session.isLoggedIn) return const LoginScreen();
    return const HomeScreen();
  }
}
