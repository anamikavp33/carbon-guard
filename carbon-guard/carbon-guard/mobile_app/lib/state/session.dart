import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../api/api_client.dart';
import '../api/models.dart';

/// The logged-in user and their token. Screens read it with `context.watch<Session>()`.
///
/// The token is stored with flutter_secure_storage (Android Keystore encryption), never in plain
/// files or shared preferences. The password itself is never stored.
class Session extends ChangeNotifier {
  Session({FlutterSecureStorage? storage, ApiClient? api}) : _storage = storage ?? const FlutterSecureStorage() {
    this.api = api ?? ApiClient(tokenProvider: () => _token, onUnauthorized: _onUnauthorized);
  }

  static const _tokenKey = 'access_token';
  static const _onboardingKey = 'onboarding_done';

  final FlutterSecureStorage _storage;
  late final ApiClient api;

  String? _token;
  UserProfile? profile;
  bool ready = false;          // finished reading storage at start-up
  bool onboardingDone = false;
  bool sessionExpired = false; // shown once on the login screen

  bool get isLoggedIn => _token != null;

  /// Called once when the app starts (splash screen).
  Future<void> load() async {
    try {
      onboardingDone = await _storage.read(key: _onboardingKey) == 'yes';
      _token = await _storage.read(key: _tokenKey);
    } catch (_) {
      _token = null; // unreadable storage (e.g. after reinstall): just log in again
    }
    if (_token != null) {
      try {
        profile = await api.profile();
      } on ApiException catch (e) {
        if (e.isUnauthorized) await _clear();
        // Other errors (offline): stay logged in; screens show a retry button.
      }
    }
    ready = true;
    notifyListeners();
  }

  Future<void> finishOnboarding() async {
    onboardingDone = true;
    await _storage.write(key: _onboardingKey, value: 'yes');
    notifyListeners();
  }

  Future<void> login(String email, String password) async {
    final token = await api.login(email, password);
    _token = token;
    try {
      if (await api.role() != 'user') {
        throw ApiException('This is an administrator account. Please use the web dashboard.');
      }
      profile = await api.profile();
    } catch (_) {
      _token = null;
      rethrow;
    }
    await _storage.write(key: _tokenKey, value: token);
    sessionExpired = false;
    notifyListeners();
  }

  Future<void> register(String name, String email, String password) async {
    await api.register(name, email, password);
    await login(email, password);
  }

  /// Reloads credits, Trust Score and counts. Errors are passed to the caller.
  Future<void> refreshProfile() async {
    profile = await api.profile();
    notifyListeners();
  }

  Future<void> logout() async {
    await _clear();
    notifyListeners();
  }

  Future<void> _clear() async {
    _token = null;
    profile = null;
    await _storage.delete(key: _tokenKey);
  }

  void _onUnauthorized() {
    if (_token == null) return;
    sessionExpired = true;
    _clear().then((_) => notifyListeners());
  }
}
