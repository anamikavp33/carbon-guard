import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../state/session.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    return Scaffold(
      body: Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.eco, size: 72, color: color),
          const SizedBox(height: 12),
          Text('Carbon Guard', style: Theme.of(context).textTheme.headlineMedium?.copyWith(color: color)),
          const SizedBox(height: 24),
          const CircularProgressIndicator(),
        ]),
      ),
    );
  }
}

class _Page {
  const _Page(this.icon, this.title, this.text);
  final IconData icon;
  final String title, text;
}

const _pages = [
  _Page(Icons.eco, 'Record green activities',
      'Planted trees, installed solar panels or built a water-harvesting structure? Record it with a photo and your location.'),
  _Page(Icons.fact_check, 'Evidence is checked',
      'Your photo and location are checked automatically (image analysis, GPS, duplicate checks), then reviewed by an administrator.'),
  _Page(Icons.workspace_premium, 'Earn Green Credits',
      'Approved activities earn Green Credits and raise your Trust Score. Green Credits are reward points of this '
          'project, not official carbon credits.'),
];

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _controller = PageController();
  int _index = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _next() {
    if (_index < _pages.length - 1) {
      _controller.nextPage(duration: const Duration(milliseconds: 300), curve: Curves.easeOut);
    } else {
      context.read<Session>().finishOnboarding();
    }
  }

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    return Scaffold(
      body: SafeArea(
        child: Column(children: [
          Align(
            alignment: Alignment.centerRight,
            child: TextButton(onPressed: () => context.read<Session>().finishOnboarding(), child: const Text('Skip')),
          ),
          Expanded(
            child: PageView(
              controller: _controller,
              onPageChanged: (i) => setState(() => _index = i),
              children: [
                for (final p in _pages)
                  Padding(
                    padding: const EdgeInsets.all(32),
                    child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                      Icon(p.icon, size: 96, color: color),
                      const SizedBox(height: 24),
                      Text(p.title, style: Theme.of(context).textTheme.headlineSmall, textAlign: TextAlign.center),
                      const SizedBox(height: 12),
                      Text(p.text, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyLarge),
                    ]),
                  ),
              ],
            ),
          ),
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            for (var i = 0; i < _pages.length; i++)
              Container(
                width: 8,
                height: 8,
                margin: const EdgeInsets.all(4),
                decoration: BoxDecoration(shape: BoxShape.circle, color: i == _index ? color : Colors.grey.shade300),
              ),
          ]),
          Padding(
            padding: const EdgeInsets.all(24),
            child: SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: _next,
                child: Text(_index == _pages.length - 1 ? 'Get started' : 'Next'),
              ),
            ),
          ),
        ]),
      ),
    );
  }
}
