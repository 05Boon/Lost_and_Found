from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
from lostfound.models import ItemReport, Claim, Handover, StatusHistory

User = get_user_model()


class Command(BaseCommand):
    help = 'Load seed data with sample users, reports, claims, and handovers'

    def handle(self, *args, **options):
        self.stdout.write('Loading seed data...')

        # ------------------------------------------------------------------ #
        # 1. Create users
        # ------------------------------------------------------------------ #
        users_data = [
            {
                'username': 'admin',
                'email': 'admin@campus.edu',
                'password': 'admin123',
                'role': 'admin',
                'first_name': 'System',
                'last_name': 'Admin',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'username': 'prof_jones',
                'email': 'jones@campus.edu',
                'password': 'staff123',
                'role': 'staff',
                'first_name': 'Sarah',
                'last_name': 'Jones',
                'is_staff': True,
                'is_superuser': False,
            },
            {
                'username': 'alice',
                'email': 'alice@campus.edu',
                'password': 'student123',
                'role': 'student',
                'first_name': 'Alice',
                'last_name': 'Smith',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'username': 'bob',
                'email': 'bob@campus.edu',
                'password': 'student123',
                'role': 'student',
                'first_name': 'Bob',
                'last_name': 'Williams',
                'is_staff': False,
                'is_superuser': False,
            },
            {
                'username': 'carol',
                'email': 'carol@campus.edu',
                'password': 'student123',
                'role': 'student',
                'first_name': 'Carol',
                'last_name': 'Davis',
                'is_staff': False,
                'is_superuser': False,
            },
        ]

        created_users = {}
        for ud in users_data:
            user, created = User.objects.get_or_create(
                username=ud['username'],
                defaults=ud,
            )
            if created:
                user.set_password(ud['password'])
                user.save()
                self.stdout.write(f'  Created user: {user.username} ({user.role})')
            created_users[ud['username']] = user

        admin = created_users['admin']
        prof_jones = created_users['prof_jones']
        alice = created_users['alice']
        bob = created_users['bob']
        carol = created_users['carol']

        # ------------------------------------------------------------------ #
        # 2. Create item reports
        # ------------------------------------------------------------------ #
        now = timezone.now()
        reports_data = [
            {
                'reporter': alice,
                'report_type': 'lost',
                'title': 'Black MacBook Pro 14"',
                'description': 'Left my MacBook Pro on a table in the library study room. It has a silver sticker on the lid. Last seen around 2 pm.',
                'category': 'electronics',
                'date_lost_or_found': (now - timedelta(days=2)).date(),
                'location': 'Main Library, 2nd Floor Study Room',
                'status': 'active',
            },
            {
                'reporter': bob,
                'report_type': 'found',
                'title': 'Wallet found near cafeteria',
                'description': 'Found a brown leather wallet containing ID cards and some cash near the cafeteria entrance. Handed to the lost and found desk.',
                'category': 'accessories',
                'date_lost_or_found': (now - timedelta(days=1)).date(),
                'location': 'Student Cafeteria Entrance',
                'status': 'active',
            },
            {
                'reporter': carol,
                'report_type': 'lost',
                'title': 'Blue Honda bike keys',
                'description': 'Lost my blue Honda bike keys somewhere between the parking lot and the science building. Keychain has a small teddy bear.',
                'category': 'accessories',
                'date_lost_or_found': (now - timedelta(days=3)).date(),
                'location': 'Parking Lot B to Science Building corridor',
                'status': 'active',
            },
            {
                'reporter': prof_jones,
                'report_type': 'found',
                'title': 'Student ID card — Jane Doe',
                'description': 'Found a student ID card on the ground in front of the lecture hall A. Name on the card is Jane Doe.',
                'category': 'documents',
                'date_lost_or_found': (now - timedelta(days=1)).date(),
                'location': 'Lecture Hall A, Ground Floor',
                'status': 'active',
            },
            {
                'reporter': alice,
                'report_type': 'lost',
                'title': 'Nike running shoes (left)',
                'description': 'Lost one left Nike running shoe, size 7, white with black swoosh, near the track field after morning practice.',
                'category': 'clothing',
                'date_lost_or_found': (now - timedelta(days=5)).date(),
                'location': 'Track and Field Area',
                'status': 'under review',
            },
            {
                'reporter': bob,
                'report_type': 'found',
                'title': 'Single white Nike running shoe',
                'description': 'Found a single white Nike running shoe, left foot, size 7, near the track field.',
                'category': 'clothing',
                'date_lost_or_found': (now - timedelta(days=4)).date(),
                'location': 'Track and Field Area',
                'status': 'matched',
            },
            {
                'reporter': carol,
                'report_type': 'lost',
                'title': 'Calculus textbook',
                'description': 'Lost my calculus textbook "Calculus: Early Transcendentals" by James Stewart. It has my name written on the inside cover.',
                'category': 'documents',
                'date_lost_or_found': (now - timedelta(days=7)).date(),
                'location': 'Main Library, 1st Floor',
                'status': 'recovered',
            },
            {
                'reporter': admin,
                'report_type': 'found',
                'title': 'Set of AirPods in the gym locker room',
                'description': 'Found a pair of AirPods in their charging case in the men locker room at the campus gym.',
                'category': 'electronics',
                'date_lost_or_found': (now - timedelta(days=6)).date(),
                'location': 'Campus Gym, Men Locker Room',
                'status': 'active',
            },
            {
                'reporter': alice,
                'report_type': 'lost',
                'title': 'Red umbrella',
                'description': 'Lost a red folding umbrella at the bus stop near the main gate. It was raining yesterday afternoon.',
                'category': 'other',
                'date_lost_or_found': (now - timedelta(days=1)).date(),
                'location': 'Bus Stop, Main Gate',
                'status': 'active',
            },
            {
                'reporter': bob,
                'report_type': 'found',
                'title': 'Canvas backpack with textbooks',
                'description': 'Found a grey canvas backpack containing several textbooks left on a bench in the student union.',
                'category': 'other',
                'date_lost_or_found': (now - timedelta(hours=6)).date(),
                'location': 'Student Union, Outdoor Benches',
                'status': 'active',
            },
        ]

        created_reports = []
        for rd in reports_data:
            report, created = ItemReport.objects.get_or_create(
                title=rd['title'],
                reporter=rd['reporter'],
                defaults=rd,
            )
            if created:
                self.stdout.write(f'  Created report: "{report.title}" ({report.report_type}, {report.status})')
            created_reports.append(report)

        # ------------------------------------------------------------------ #
        # 3. Create sample claims
        # ------------------------------------------------------------------ #
        claims_data = [
            {
                'report': created_reports[0],   # MacBook Pro (lost by Alice)
                'claimant': carol,
                'private_evidence': 'I found a black MacBook Pro in the library study room yesterday around 3 pm. It matches the description with the silver sticker.',
                'claim_status': 'pending',
                'reviewer': None,
                'decision_note': '',
            },
            {
                'report': created_reports[4],   # Nike shoe (lost by Alice)
                'claimant': bob,
                'private_evidence': 'I found a matching left Nike running shoe near the track field. Size 7, white with black swoosh.',
                'claim_status': 'approved',
                'reviewer': admin,
                'decision_note': 'Claim approved — the found item matches the lost item description.',
            },
            {
                'report': created_reports[6],   # Calculus textbook (lost by Carol)
                'claimant': prof_jones,
                'private_evidence': 'I found a calculus textbook by James Stewart in the library with "Carol Davis" written on the inside cover.',
                'claim_status': 'approved',
                'reviewer': admin,
                'decision_note': 'Textbook returned to owner after verifying name on cover.',
            },
        ]

        for cd in claims_data:
            claim, created = Claim.objects.get_or_create(
                report=cd['report'],
                claimant=cd['claimant'],
                defaults=cd,
            )
            if created:
                self.stdout.write(f'  Created claim: {claim.report.title} — claimant {claim.claimant.username} ({claim.claim_status})')

        # ------------------------------------------------------------------ #
        # 4. Create sample handovers
        # ------------------------------------------------------------------ #
        approved_claims = Claim.objects.filter(claim_status='approved')
        for claim in approved_claims:
            handover, created = Handover.objects.get_or_create(
                report=claim.report,
                claim=claim,
                defaults={
                    'recorded_by': admin,
                    'handover_date': now - timedelta(hours=1),
                    'outcome': 'Item returned to owner',
                    'notes': f'Item handed over to {claim.claimant.first_name} {claim.claimant.last_name} after identity verification.',
                },
            )
            if created:
                self.stdout.write(f'  Created handover: {handover.report.title}')

        # ------------------------------------------------------------------ #
        # 5. Create status history entries
        # ------------------------------------------------------------------ #
        status_entries = [
            {'entity_type': 'report', 'entity_id': created_reports[5].pk, 'previous_status': 'active', 'new_status': 'matched', 'changed_by': admin},
            {'entity_type': 'report', 'entity_id': created_reports[6].pk, 'previous_status': 'active', 'new_status': 'recovered', 'changed_by': admin},
            {'entity_type': 'claim', 'entity_id': approved_claims[0].pk if approved_claims else 0, 'previous_status': 'pending', 'new_status': 'approved', 'changed_by': admin},
        ]

        for se in status_entries:
            StatusHistory.objects.get_or_create(
                entity_type=se['entity_type'],
                entity_id=se['entity_id'],
                new_status=se['new_status'],
                defaults={
                    'previous_status': se['previous_status'],
                    'changed_by': se['changed_by'],
                },
            )

        # ------------------------------------------------------------------ #
        # Summary
        # ------------------------------------------------------------------ #
        self.stdout.write(self.style.SUCCESS(
            f'\nSeed data loaded successfully!\n'
            f'  Users: {User.objects.count()}\n'
            f'  Reports: {ItemReport.objects.count()}\n'
            f'  Claims: {Claim.objects.count()}\n'
            f'  Handovers: {Handover.objects.count()}\n'
            f'\nDefault login credentials:\n'
            f'  Admin: admin / admin123\n'
            f'  Staff: prof_jones / staff123\n'
            f'  Students: alice, bob, carol / student123'
        ))
