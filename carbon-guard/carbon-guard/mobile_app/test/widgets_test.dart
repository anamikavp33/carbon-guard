import 'package:carbon_guard_app/screens/auth_screens.dart';
import 'package:carbon_guard_app/state/session.dart';
import 'package:carbon_guard_app/utils/format.dart';
import 'package:carbon_guard_app/utils/validators.dart';
import 'package:carbon_guard_app/widgets/common.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

void main() {
  test('validators', () {
    expect(validateEmail(''), isNotNull);
    expect(validateEmail('asha@example.com'), isNull);
    expect(validatePassword('short'), isNotNull);
    expect(validatePassword('long enough'), isNull);
    expect(validateQuantity('0'), isNotNull);
    expect(validateQuantity('abc'), isNotNull);
    expect(validateQuantity('2.5'), isNull);
    expect(validateName('  '), isNotNull);
  });

  test('formatting', () {
    expect(formatNumber(12.0), '12');
    expect(formatNumber(12.345), '12.35');
    expect(formatNumber(100, digits: 0), '100');
    expect(formatNumber(null), '-');
    expect(humanize('manual_review'), 'Manual review');
    expect(formatDate(DateTime(2026, 10, 5, 9, 7)), '5 Oct 2026, 09:07');
  });

  testWidgets('status chip shows a friendly label', (tester) async {
    await tester.pumpWidget(const MaterialApp(home: Scaffold(body: StatusChip('manual_review'))));
    expect(find.text('In review'), findsOneWidget);
  });

  testWidgets('login form validates before calling the server', (tester) async {
    await tester.pumpWidget(ChangeNotifierProvider(
      create: (_) => Session(),
      child: const MaterialApp(home: LoginScreen()),
    ));
    await tester.tap(find.text('Log in'));
    await tester.pump();
    expect(find.text('Please enter your email'), findsOneWidget);
    expect(find.text('Please enter your password'), findsOneWidget);
  });
}
