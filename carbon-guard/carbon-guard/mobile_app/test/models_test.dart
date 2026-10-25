// Parses responses copied from API_CONTRACT.md (captured from the real backend), so the app and
// the backend agree on field names and types.
import 'package:carbon_guard_app/api/models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('profile', () {
    final p = UserProfile.fromJson({
      'id': '6ade2c016233689001c193a0', 'name': 'Asha', 'email': 'asha@example.com', 'role': 'user',
      'trust_score': 55.0, 'green_credits_total': 12, 'is_active': true,
      'created_at': '2026-10-25T16:19:13.857000Z',
      'submission_counts': {'total': 3, 'processing': 0, 'pending': 1, 'manual_review': 1, 'verified': 1, 'rejected': 0},
      'total_co2_estimate': 10.0,
    });
    expect(p.greenCreditsTotal, 12.0);
    expect(p.counts.waiting, 2);
    expect(p.createdAt.toUtc(), DateTime.utc(2026, 10, 25, 16, 19, 13, 857));
  });

  test('submission detail while processing has null evidence', () {
    final d = SubmissionDetail.fromJson({
      'id': 'x', 'activity_type': 'solar_panel', 'status': 'processing', 'image_url': '/uploads/a.jpg',
      'gps': {'lat': 9.5, 'lng': 76.3, 'accuracy_m': null, 'is_mocked': null}, 'description': null, 'scale_value': 3,
      'ai_verification': null, 'location_verification': null, 'satellite_verification': null, 'fraud_check': null,
      'verification_score': null, 'score_components': {}, 'decision_reasons': [],
      'environmental_impact': {'co2_estimate': null, 'unit': null}, 'green_credits_awarded': 0.0,
      'review_notes': null, 'reviewed_at': null,
      'created_at': '2026-10-25T16:19:14.129000Z', 'updated_at': '2026-10-25T16:19:14.129000Z',
    });
    expect(d.ai, isNull);
    expect(d.verificationScore, isNull);
    expect(d.scaleValue, 3.0);
  });

  test('full submission detail', () {
    final d = SubmissionDetail.fromJson({
      'id': '6ade2c026233689001c193a1', 'activity_type': 'tree_plantation', 'status': 'verified',
      'image_url': '/uploads/b3.jpg', 'gps': {'lat': 9.522, 'lng': 76.3, 'accuracy_m': 8.0, 'is_mocked': false},
      'description': 'Planted 4 mango saplings', 'scale_value': 4.0,
      'ai_verification': {'status': 'unavailable', 'model': null, 'predicted_class': null, 'confidence': null,
        'matched': null, 'scores': {}, 'warnings': ['No AI model file installed (see ai_model/README.md).']},
      'location_verification': {'gps_valid': true, 'accuracy_m': 8.0, 'accuracy_ok': true,
        'address': 'Thumpoly, Alappuzha, Kerala, India', 'geocoding_status': 'ok', 'notes': []},
      'satellite_verification': {'status': 'not_configured', 'source': null, 'acquisition_date': null,
        'cloud_cover': null, 'image_url': null, 'ndvi_mean': null, 'supports_claim': null,
        'notes': ['Satellite imagery is not configured on this server.']},
      'fraud_check': {'is_duplicate_image': false, 'is_duplicate_location': false, 'suspicious_pattern': false,
        'flags': [], 'reasons': []},
      'verification_score': 30.0, 'score_components': {'ai': 0.0, 'gps': 15.0, 'satellite': 0.0, 'fraud': 15},
      'decision_reasons': ['AI evidence: 0.0 of 60 points.'],
      'environmental_impact': {'co2_estimate': 10.0, 'unit': 'kg_co2_per_year'}, 'green_credits_awarded': 12.0,
      'review_notes': 'Photo and location look right.', 'reviewed_at': '2026-10-25T16:19:15.950000Z',
      'created_at': '2026-10-25T16:19:14.129000Z', 'updated_at': '2026-10-25T16:19:15.950000Z',
    });
    expect(d.ai!.status, 'unavailable');
    expect(d.location!.address, contains('Alappuzha'));
    expect(d.scoreComponents['fraud'], 15.0);
    expect(d.co2Estimate, 10.0);
    expect(d.reviewedAt, isNotNull);
  });

  test('page of summaries, histories and rules', () {
    final page = ResultPage.fromJson({
      'items': [
        {'id': 'a', 'user_email': 'asha@example.com', 'activity_type': 'tree_plantation', 'status': 'verified',
          'image_url': '/uploads/a.jpg', 'verification_score': 30.0, 'flags': ['duplicate_image'],
          'green_credits_awarded': 12.0, 'created_at': '2026-10-25T16:19:14.129000Z'},
      ],
      'total': 7, 'skip': 0, 'limit': 20,
    }, SubmissionSummary.fromJson);
    expect(page.items.single.flags, ['duplicate_image']);
    expect(page.total, 7);

    final trust = TrustHistory.fromJson({
      'trust_score': 55.0, 'trust_min': 0, 'trust_max': 100,
      'events': [
        {'id': 'e', 'submission_id': 's', 'event_type': 'verified_submission', 'score_delta': 5.0, 'score_after': 55.0,
          'reason': 'An admin approved a submission.', 'created_at': '2026-10-25T16:19:15.965000Z'},
      ],
    });
    expect(trust.events.single.scoreDelta, 5.0);

    final credits = CreditHistory.fromJson({
      'green_credits_total': 12.0,
      'transactions': [
        {'id': 't', 'submission_id': 's', 'type': 'award', 'amount': 12.0, 'created_at': '2026-10-25T16:19:15.950000Z'},
      ],
    });
    expect(credits.transactions.single.amount, 12.0);

    final rules = RulesInfo.fromJson({
      'activity_types': [
        {'activity_type': 'tree_plantation', 'scale_unit': 'trees planted', 'credits_per_unit': 3.0, 'max_scale': 1000},
      ],
      'statuses': ['processing', 'pending', 'manual_review', 'verified', 'rejected'],
      'trust': {'initial': 50, 'min': 0, 'max': 100,
        'rules': {'verified_submission': 5, 'rejected_submission': -10, 'fraud_confirmed': -15}},
      'evidence': {'ai_model_available': false, 'satellite_configured': false},
      'disclaimer': 'Green Credits are reward points...',
    });
    expect(rules.trustRules['fraud_confirmed'], -15.0);
    expect(rules.activities.single.maxScale, 1000.0);
  });
}
