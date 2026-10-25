// Form checks. They mirror the backend rules so users see problems before uploading.

String? validateName(String? v) {
  if (v == null || v.trim().isEmpty) return 'Please enter your name';
  if (v.trim().length > 100) return 'Name is too long';
  return null;
}

final _emailPattern = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');

String? validateEmail(String? v) {
  if (v == null || v.trim().isEmpty) return 'Please enter your email';
  if (!_emailPattern.hasMatch(v.trim())) return 'Please enter a valid email address';
  return null;
}

String? validatePassword(String? v) {
  if (v == null || v.isEmpty) return 'Please enter a password';
  if (v.length < 8) return 'Use at least 8 characters';
  if (v.length > 64) return 'Use at most 64 characters';
  return null;
}

String? validateQuantity(String? v, {double? max}) {
  final n = double.tryParse((v ?? '').trim());
  if (n == null) return 'Please enter a number';
  if (n <= 0) return 'Must be more than 0';
  if (max != null && n > max) return 'That seems too large (maximum $max)';
  return null;
}
