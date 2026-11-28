from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Claim, Handover, ItemReport, StatusHistory

User = get_user_model()


class LostFoundApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='apiuser',
            password='TestPass!2098',
        )
        self.claimant = User.objects.create_user(
            username='claimant',
            password='TestPass!2098',
        )
        self.staff = User.objects.create_user(
            username='apistaff',
            password='TestPass!2098',
            is_staff=True,
            role='staff',
        )
        self.report = ItemReport.objects.create(
            reporter=self.user,
            report_type='found',
            title='Black keys',
            description='Three keys on a red lanyard.',
            category='accessories',
            date_lost_or_found=timezone.localdate(),
            location='Student center',
            status='active',
        )
        self.client = APIClient()

    def test_public_report_list_supports_filters_and_pagination(self):
        response = self.client.get(
            '/api/reports/',
            {'report_type': 'found', 'category': 'accessories', 'q': 'keys'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Black keys')
        self.assertNotIn('description', response.data['results'][0])

    def test_authenticated_user_can_create_report(self):
        self.client.force_authenticate(user=self.claimant)

        response = self.client.post('/api/reports/', {
            'report_type': 'lost',
            'title': 'Blue umbrella',
            'description': 'A blue umbrella with a wooden handle.',
            'category': 'other',
            'date_lost_or_found': timezone.localdate().isoformat(),
            'location': 'North hall',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        created = ItemReport.objects.get(pk=response.data['id'])
        self.assertEqual(created.reporter, self.claimant)
        self.assertTrue(StatusHistory.objects.filter(
            entity_type='report',
            entity_id=created.pk,
            new_status='active',
        ).exists())

    def test_owner_can_edit_report_and_staff_can_change_status(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.patch(
            f'/api/reports/{self.report.pk}/',
            {'title': 'Black keys with red lanyard'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertEqual(self.report.title, 'Black keys with red lanyard')

        self.client.force_authenticate(user=self.staff)
        response = self.client.patch(
            f'/api/reports/{self.report.pk}/',
            {'status': 'matched'},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'matched')

    def test_authenticated_user_can_claim_found_report(self):
        self.client.force_authenticate(user=self.claimant)
        response = self.client.post(
            f'/api/reports/{self.report.pk}/claim/',
            {'private_evidence': 'There is a small dent on the second key.'},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        claim = Claim.objects.get(pk=response.data['id'])
        self.assertEqual(claim.report, self.report)
        self.assertEqual(claim.claimant, self.claimant)


class LostFoundWorkflowTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(
            username='alex',
            email='alex@example.test',
            password='TestPass!2098',
        )
        self.other_student = User.objects.create_user(
            username='jamie',
            email='jamie@example.test',
            password='TestPass!2098',
        )
        self.staff = User.objects.create_user(
            username='staffmember',
            email='staff@example.test',
            password='TestPass!2098',
            is_staff=True,
            role='staff',
        )
        self.report = self.make_report()

    def make_report(self, **overrides):
        values = {
            'reporter': self.student,
            'report_type': 'found',
            'title': 'Blue water bottle',
            'description': 'A blue metal bottle with a silver lid.',
            'category': 'other',
            'date_lost_or_found': timezone.localdate(),
            'location': 'Main library',
            'status': 'active',
        }
        values.update(overrides)
        return ItemReport.objects.create(**values)

    def make_claim(self, claimant=None, report=None, **overrides):
        values = {
            'report': report or self.report,
            'claimant': claimant or self.other_student,
            'private_evidence': 'A unique scratch near the bottom.',
        }
        values.update(overrides)
        return Claim.objects.create(**values)

    def test_landing_page_is_public_and_shows_active_report_counts(self):
        lost_report = self.make_report(
            title='Black laptop bag',
            report_type='lost',
        )

        response = self.client.get(reverse('landing'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Help something lost find its way home.')
        self.assertContains(response, 'View lost reports')
        self.assertContains(response, 'View found reports')
        self.assertContains(response, 'Create a report')
        self.assertNotContains(response, 'Recent reports')
        self.assertEqual(response.context['lost_count'], 1)
        self.assertEqual(response.context['found_count'], 1)

    def test_lost_and_found_reports_are_separate_public_pages(self):
        self.make_report(
            title='Red backpack',
            report_type='lost',
            status='closed',
        )
        lost_report = self.make_report(title='Lost red backpack', report_type='lost')

        lost_response = self.client.get(
            reverse('lost_reports'),
            {'q': 'red backpack'},
        )
        found_response = self.client.get(reverse('found_reports'))

        self.assertEqual(lost_response.status_code, 200)
        self.assertContains(lost_response, 'Lost reports')
        self.assertContains(lost_response, 'Lost red backpack')
        self.assertNotContains(lost_response, 'Blue water bottle')
        self.assertIn(lost_report, lost_response.context['reports'].object_list)

        self.assertEqual(found_response.status_code, 200)
        self.assertContains(found_response, 'Found reports')
        self.assertContains(found_response, 'Blue water bottle')
        self.assertNotContains(found_response, 'Lost red backpack')
        self.assertIn(self.report, found_response.context['reports'].object_list)

    def test_report_descriptions_are_visible_only_to_officers(self):
        public_detail = self.client.get(
            reverse('report_detail', args=[self.report.pk])
        )
        self.assertNotContains(public_detail, self.report.description)

        public_list = self.client.get(reverse('found_reports'))
        self.assertNotContains(public_list, self.report.description)

        description_search = self.client.get(
            reverse('found_reports'),
            {'q': 'silver lid'},
        )
        self.assertNotContains(description_search, self.report.title)

        self.client.force_login(self.student)
        student_detail = self.client.get(
            reverse('report_detail', args=[self.report.pk])
        )
        self.assertNotContains(student_detail, self.report.description)

        self.client.force_login(self.staff)
        staff_detail = self.client.get(
            reverse('report_detail', args=[self.report.pk])
        )
        self.assertContains(staff_detail, self.report.description)

        staff_search = self.client.get(
            reverse('found_reports'),
            {'q': 'silver lid'},
        )
        self.assertContains(staff_search, self.report.title)

    def test_report_form_uses_dropdowns_for_type_and_category(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse('create_report'))

        self.assertContains(response, '<select name="report_type"', html=False)
        self.assertContains(response, '<select name="category"', html=False)

    def test_login_registration_and_password_reset_pages_render(self):
        for route_name in ('login', 'register', 'password_reset', 'password_reset_done'):
            with self.subTest(route=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)

    def test_staff_claim_review_pages_render_without_exposing_evidence_in_queue(self):
        claim = self.make_claim()
        self.client.force_login(self.staff)
        queue = self.client.get(reverse('claim_review_queue'))
        self.assertEqual(queue.status_code, 200)
        self.assertNotContains(queue, claim.private_evidence)

        review = self.client.get(reverse('review_claim', args=[claim.pk]))
        self.assertEqual(review.status_code, 200)
        self.assertContains(review, claim.private_evidence)

        reports = self.client.get(reverse('staff_report_list'))
        self.assertEqual(reports.status_code, 200)
        self.assertContains(reports, self.report.title)

    def test_staff_can_hide_report_from_public_browse(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse('update_report_status', args=[self.report.pk]),
            {'status': 'hidden'},
        )
        self.assertRedirects(response, reverse('staff_report_list'))
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'hidden')

        response = self.client.get(reverse('found_reports'))
        self.assertNotContains(response, self.report.title)

    def test_registration_cannot_grant_staff_access(self):
        response = self.client.post(reverse('register'), {
            'username': 'newstudent',
            'first_name': 'New',
            'last_name': 'Student',
            'email': 'newstudent@example.test',
            'role': 'staff',
            'password1': 'StrongNewPass!984',
            'password2': 'StrongNewPass!984',
        })
        self.assertRedirects(response, reverse('login'))
        created = User.objects.get(username='newstudent')
        self.assertEqual(created.role, 'student')
        self.assertFalse(created.is_staff)

    def test_only_signed_in_users_can_post_reports(self):
        response = self.client.get(reverse('create_report'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

        self.client.force_login(self.other_student)
        form_response = self.client.get(reverse('create_report'))
        self.assertEqual(form_response.status_code, 200)
        self.assertContains(form_response, 'Report basics')
        self.assertContains(form_response, 'Choose the day you last saw it or found it.')
        self.assertContains(
            form_response,
            f'max="{timezone.localdate().isoformat()}"',
        )

        response = self.client.post(reverse('create_report'), {
            'report_type': 'lost',
            'title': 'Lost student ID',
            'description': 'A student ID in a blue case.',
            'category': 'documents',
            'date_lost_or_found': timezone.localdate().isoformat(),
            'location': 'North hall',
        })
        self.assertRedirects(
            response,
            reverse('report_detail', args=[ItemReport.objects.latest('id').pk]),
        )
        created = ItemReport.objects.latest('id')
        self.assertEqual(created.reporter, self.other_student)
        self.assertTrue(StatusHistory.objects.filter(
            entity_type='report',
            entity_id=created.pk,
            new_status='active',
        ).exists())

    def test_report_owner_can_edit_and_close_but_other_users_cannot_edit(self):
        self.client.force_login(self.other_student)
        response = self.client.get(reverse('edit_report', args=[self.report.pk]))
        self.assertEqual(response.status_code, 404)

        self.client.force_login(self.student)
        response = self.client.post(reverse('edit_report', args=[self.report.pk]), {
            'report_type': 'found',
            'title': 'Blue bottle with sticker',
            'description': 'A blue metal bottle with a small sticker.',
            'category': 'other',
            'date_lost_or_found': timezone.localdate().isoformat(),
            'location': 'Main library',
        })
        self.assertRedirects(response, reverse('report_detail', args=[self.report.pk]))
        self.report.refresh_from_db()
        self.assertEqual(self.report.title, 'Blue bottle with sticker')

        response = self.client.post(reverse('close_report', args=[self.report.pk]))
        self.assertRedirects(response, reverse('my_activity'))
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'closed')
        self.assertTrue(StatusHistory.objects.filter(
            entity_type='report',
            entity_id=self.report.pk,
            new_status='closed',
        ).exists())

    def test_claim_evidence_is_private_and_duplicate_open_claim_is_blocked(self):
        self.client.force_login(self.other_student)
        url = reverse('submit_claim', args=[self.report.pk])
        response = self.client.post(url, {
            'private_evidence': 'I can identify the small scratch beneath the logo.',
        })
        self.assertRedirects(response, reverse('my_activity'))
        claim = Claim.objects.get(report=self.report, claimant=self.other_student)

        detail = self.client.get(reverse('report_detail', args=[self.report.pk]))
        self.assertNotContains(detail, 'small scratch beneath the logo')
        activity = self.client.get(reverse('my_activity'))
        self.assertContains(activity, self.report.title)
        self.assertNotContains(activity, 'small scratch beneath the logo')

        duplicate = self.client.get(url)
        self.assertRedirects(duplicate, reverse('my_activity'))
        self.assertEqual(Claim.objects.filter(
            report=self.report,
            claimant=self.other_student,
        ).count(), 1)
        self.assertEqual(claim.claim_status, 'pending')

    def test_lost_report_explains_claims_are_for_found_items(self):
        lost_report = self.make_report(
            title='Lost blue water bottle',
            report_type='lost',
        )
        self.client.force_login(self.other_student)

        response = self.client.get(reverse('report_detail', args=[lost_report.pk]))

        self.assertContains(response, 'Claims are submitted on found-item reports.')
        self.assertContains(response, 'Post a found report')
        self.assertNotContains(response, 'Claim this item')

    def test_reporter_cannot_claim_their_own_found_item(self):
        self.client.force_login(self.student)
        response = self.client.post(
            reverse('submit_claim', args=[self.report.pk]),
            {'private_evidence': 'I am the reporter.'},
        )
        self.assertRedirects(response, reverse('report_detail', args=[self.report.pk]))
        self.assertFalse(Claim.objects.filter(report=self.report).exists())

    def test_staff_approval_matches_report_and_closes_competing_claims(self):
        winning_claim = self.make_claim()
        competing_claim = self.make_claim(
            claimant=User.objects.create_user(
                username='taylor',
                password='TestPass!2098',
            ),
            claim_status='more_info',
        )
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse('review_claim', args=[winning_claim.pk]),
            {'claim_status': 'approved', 'decision_note': 'Ownership confirmed.'},
        )
        self.assertRedirects(response, reverse('claim_review_queue'))

        winning_claim.refresh_from_db()
        competing_claim.refresh_from_db()
        self.report.refresh_from_db()
        self.assertEqual(winning_claim.claim_status, 'approved')
        self.assertEqual(competing_claim.claim_status, 'rejected')
        self.assertEqual(self.report.status, 'matched')
        self.assertTrue(StatusHistory.objects.filter(
            entity_type='report',
            entity_id=self.report.pk,
            new_status='matched',
        ).exists())

    def test_claimant_can_reply_to_a_request_for_more_information(self):
        claim = self.make_claim(claim_status='more_info', decision_note='What color is the inside?')
        self.client.force_login(self.other_student)
        response = self.client.post(
            reverse('respond_to_claim', args=[claim.pk]),
            {'private_evidence': 'The inside is lined with a distinctive yellow fabric.'},
        )
        self.assertRedirects(response, reverse('my_activity'))
        claim.refresh_from_db()
        self.assertEqual(claim.claim_status, 'pending')
        self.assertEqual(
            claim.private_evidence,
            'The inside is lined with a distinctive yellow fabric.',
        )
        self.assertEqual(claim.decision_note, '')

    def test_staff_can_record_handover_and_recover_the_item(self):
        self.report.status = 'matched'
        self.report.save(update_fields=['status'])
        claim = self.make_claim(claim_status='approved', reviewer=self.staff)
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse('record_handover', args=[claim.pk]),
            {'outcome': 'Returned to owner', 'notes': 'Verified at the help desk.'},
        )
        self.assertRedirects(response, reverse('report_detail', args=[self.report.pk]))
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'recovered')
        handover = Handover.objects.get(claim=claim)
        self.assertEqual(handover.recorded_by, self.staff)
        self.assertTrue(StatusHistory.objects.filter(
            entity_type='report',
            entity_id=self.report.pk,
            new_status='recovered',
        ).exists())
        duplicate = self.client.post(
            reverse('record_handover', args=[claim.pk]),
            {'outcome': 'Duplicate return', 'notes': ''},
        )
        self.assertRedirects(duplicate, reverse('report_detail', args=[self.report.pk]))
        self.assertEqual(Handover.objects.filter(claim=claim).count(), 1)

    def test_staff_pages_require_staff_and_hidden_reports_are_private(self):
        response = self.client.get(reverse('claim_review_queue'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response.url)

        self.report.status = 'hidden'
        self.report.save(update_fields=['status'])
        response = self.client.get(reverse('report_detail', args=[self.report.pk]))
        self.assertEqual(response.status_code, 404)

        self.client.force_login(self.staff)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Staff desk')

    def test_staff_cannot_mark_item_recovered_without_a_handover(self):
        self.client.force_login(self.staff)
        response = self.client.post(
            reverse('update_report_status', args=[self.report.pk]),
            {'status': 'recovered'},
        )
        self.assertRedirects(response, reverse('staff_report_list'))
        self.report.refresh_from_db()
        self.assertEqual(self.report.status, 'active')
