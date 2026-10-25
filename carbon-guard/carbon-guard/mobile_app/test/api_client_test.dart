import 'dart:convert';

import 'package:carbon_guard_app/api/api_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  ApiClient client(MockClient mock, {String? token, void Function()? onUnauthorized}) => ApiClient(
        tokenProvider: () => token,
        onUnauthorized: onUnauthorized ?? () {},
        client: mock,
        baseUrl: 'http://test',
      );

  test('login sends JSON and returns the token', () async {
    final mock = MockClient((req) async {
      expect(req.url.toString(), 'http://test/auth/login');
      expect(jsonDecode(req.body), {'email': 'a@b.com', 'password': 'secret123'});
      return http.Response(jsonEncode({'access_token': 'tok', 'token_type': 'bearer', 'expires_in': 86400}), 200);
    });
    expect(await client(mock).login('a@b.com', 'secret123'), 'tok');
  });

  test('errors become readable messages; 401 with a token logs out', () async {
    var loggedOut = false;
    final mock = MockClient((req) async => http.Response(jsonEncode({'detail': 'Not logged in or session expired.'}), 401));
    final api = client(mock, token: 'old', onUnauthorized: () => loggedOut = true);
    await expectLater(api.profile(), throwsA(isA<ApiException>().having((e) => e.isUnauthorized, 'unauthorized', true)));
    expect(loggedOut, isTrue);
  });

  test('422 lists name the field', () {
    final msg = ApiClient.errorMessage({
      'detail': [
        {'loc': ['body', 'password'], 'msg': 'String should have at least 8 characters', 'type': 'string_too_short'}
      ]
    });
    expect(msg, 'password: String should have at least 8 characters');
  });

  test('createSubmission sends a multipart form with the token', () async {
    final mock = MockClient((req) async {
      expect(req.method, 'POST');
      expect(req.url.path, '/submissions');
      expect(req.headers['Authorization'], 'Bearer tok');
      expect(req.headers['content-type'], startsWith('multipart/form-data'));
      final body = utf8.decode(req.bodyBytes, allowMalformed: true);
      for (final field in ['activity_type', 'latitude', 'longitude', 'scale_value', 'gps_accuracy_m', 'gps_is_mocked', 'image']) {
        expect(body, contains('name="$field"'));
      }
      expect(body, contains('tree_plantation'));
      expect(body, isNot(contains('name="description"'))); // empty description is not sent
      return http.Response(jsonEncode({'id': 'new-id', 'status': 'processing', 'updated_at': '2026-10-25T16:00:00Z'}), 201);
    });
    final id = await client(mock, token: 'tok').createSubmission(
      activityType: 'tree_plantation',
      latitude: 9.93,
      longitude: 76.26,
      gpsAccuracyM: 8,
      gpsIsMocked: false,
      scaleValue: 4,
      description: '   ',
      imageBytes: [0xFF, 0xD8, 0xFF],
      imageName: 'photo.jpg',
    );
    expect(id, 'new-id');
  });

  test('mySubmissions passes paging parameters', () async {
    final mock = MockClient((req) async {
      expect(req.url.queryParameters, {'skip': '20', 'limit': '20'});
      return http.Response(jsonEncode({'items': [], 'total': 20, 'skip': 20, 'limit': 20}), 200);
    });
    final page = await client(mock, token: 'tok').mySubmissions(skip: 20);
    expect(page.items, isEmpty);
  });
}
