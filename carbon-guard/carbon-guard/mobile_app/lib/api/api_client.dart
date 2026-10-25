import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../config.dart';
import 'models.dart';

/// An error the user can read, e.g. "Invalid email or password".
class ApiException implements Exception {
  ApiException(this.message, [this.statusCode]);

  final String message;
  final int? statusCode;

  bool get isUnauthorized => statusCode == 401;

  @override
  String toString() => message;
}

/// Every call to the backend goes through this class (see API_CONTRACT.md).
class ApiClient {
  ApiClient({
    required this.tokenProvider,
    required this.onUnauthorized,
    http.Client? client,
    String? baseUrl,
  })  : _http = client ?? http.Client(),
        baseUrl = baseUrl ?? apiBaseUrl;

  /// Returns the saved login token, or null when logged out.
  final String? Function() tokenProvider;

  /// Called when the backend answers 401 (token expired or invalid).
  final void Function() onUnauthorized;

  final http.Client _http;
  final String baseUrl;

  static const _timeout = Duration(seconds: 30);
  static const _uploadTimeout = Duration(seconds: 90);

  /// Full address of a file path such as "/uploads/abc.jpg".
  String fileUrl(String path) => '$baseUrl$path';

  Uri _uri(String path, [Map<String, String>? query]) {
    final uri = Uri.parse('$baseUrl$path');
    return query == null ? uri : uri.replace(queryParameters: query);
  }

  Map<String, String> _headers({bool json = true}) {
    final headers = <String, String>{};
    if (json) headers['Content-Type'] = 'application/json';
    final token = tokenProvider();
    if (token != null) headers['Authorization'] = 'Bearer $token';
    return headers;
  }

  Future<dynamic> _send(Future<http.Response> Function() call, {Duration timeout = _timeout}) async {
    http.Response res;
    try {
      res = await call().timeout(timeout);
    } on TimeoutException {
      throw ApiException('The server took too long to answer. Please try again.');
    } on SocketException {
      throw ApiException('Cannot reach the server at $baseUrl. Check your connection and the server address.');
    } on http.ClientException {
      throw ApiException('Cannot reach the server at $baseUrl. Check your connection and the server address.');
    }

    dynamic body;
    if (res.bodyBytes.isNotEmpty) {
      try {
        body = jsonDecode(utf8.decode(res.bodyBytes));
      } on FormatException {
        body = null;
      }
    }
    if (res.statusCode >= 200 && res.statusCode < 300) return body;
    if (res.statusCode == 401 && tokenProvider() != null) onUnauthorized();
    throw ApiException(errorMessage(body) ?? 'Request failed (${res.statusCode}).', res.statusCode);
  }

  /// Turns FastAPI's {"detail": ...} into readable text.
  static String? errorMessage(dynamic body) {
    if (body is! Map || body['detail'] == null) return null;
    final detail = body['detail'];
    if (detail is String) return detail;
    if (detail is List) {
      return detail.map((e) {
        final loc = (e is Map && e['loc'] is List && (e['loc'] as List).isNotEmpty) ? (e['loc'] as List).last : '';
        final msg = e is Map ? e['msg'] : e;
        return '$loc: $msg';
      }).join('\n');
    }
    return detail.toString();
  }

  Future<dynamic> _get(String path, [Map<String, String>? query]) =>
      _send(() => _http.get(_uri(path, query), headers: _headers()));

  Future<dynamic> _post(String path, Map<String, dynamic> body) =>
      _send(() => _http.post(_uri(path), headers: _headers(), body: jsonEncode(body)));

  // ---------------- auth ----------------
  Future<void> register(String name, String email, String password) =>
      _post('/auth/register', {'name': name, 'email': email, 'password': password});

  /// Returns the access token.
  Future<String> login(String email, String password) async {
    final data = await _post('/auth/login', {'email': email, 'password': password});
    return data['access_token'] as String;
  }

  /// Returns the role ("user" or "admin").
  Future<String> role() async => (await _get('/auth/me'))['role'] as String;

  // ---------------- profile ----------------
  Future<UserProfile> profile() async => UserProfile.fromJson(await _get('/users/me'));

  Future<TrustHistory> trustHistory() async => TrustHistory.fromJson(await _get('/users/me/trust-history'));

  Future<CreditHistory> creditHistory() async => CreditHistory.fromJson(await _get('/users/me/credit-history'));

  Future<RulesInfo> rules() async => RulesInfo.fromJson(await _get('/info/rules'));

  // ---------------- submissions ----------------
  Future<ResultPage<SubmissionSummary>> mySubmissions({int skip = 0, int limit = 20}) async {
    final data = await _get('/submissions/me', {'skip': '$skip', 'limit': '$limit'});
    return ResultPage.fromJson(data as Map<String, dynamic>, SubmissionSummary.fromJson);
  }

  Future<SubmissionDetail> submission(String id) async => SubmissionDetail.fromJson(await _get('/submissions/$id'));

  Future<String> submissionStatus(String id) async => (await _get('/submissions/$id/status'))['status'] as String;

  /// Uploads a new activity (multipart form). Returns the new submission id.
  Future<String> createSubmission({
    required String activityType,
    required double latitude,
    required double longitude,
    required double scaleValue,
    required List<int> imageBytes,
    required String imageName,
    double? gpsAccuracyM,
    bool? gpsIsMocked,
    String? description,
  }) async {
    final request = http.MultipartRequest('POST', _uri('/submissions'))
      ..headers.addAll(_headers(json: false))
      ..fields['activity_type'] = activityType
      ..fields['latitude'] = '$latitude'
      ..fields['longitude'] = '$longitude'
      ..fields['scale_value'] = '$scaleValue'
      ..files.add(http.MultipartFile.fromBytes('image', imageBytes, filename: imageName));
    if (gpsAccuracyM != null) request.fields['gps_accuracy_m'] = '$gpsAccuracyM';
    if (gpsIsMocked != null) request.fields['gps_is_mocked'] = '$gpsIsMocked';
    if (description != null && description.trim().isNotEmpty) request.fields['description'] = description.trim();

    final data = await _send(() async => http.Response.fromStream(await _http.send(request)),
        timeout: _uploadTimeout);
    return data['id'] as String;
  }
}
