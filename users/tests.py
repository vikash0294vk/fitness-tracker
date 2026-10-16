from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone

from tracker.models import CardioSession
from users import strava
from .models import FitnessGroup, GroupMessage


User = get_user_model()


class FitnessGroupFlowTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', password='password')
        self.member = User.objects.create_user(username='member', password='password')
        self.client.login(username='owner', password='password')

    def test_create_group_adds_creator_as_member(self):
        response = self.client.post(reverse('create_group'), {
            'name': 'Morning Walk Crew',
            'description': 'Daily walking accountability',
        })

        group = FitnessGroup.objects.get(name='Morning Walk Crew')
        self.assertRedirects(response, reverse('group_detail', args=[group.slug]))
        self.assertEqual(group.created_by, self.owner)
        self.assertTrue(group.members.filter(id=self.owner.id).exists())

    def test_join_group(self):
        group = FitnessGroup.objects.create(
            name='Weekend Lifters',
            description='Heavy sets and check-ins',
            created_by=self.owner,
        )
        group.members.add(self.owner)

        self.client.logout()
        self.client.login(username='member', password='password')
        response = self.client.post(reverse('toggle_group_membership', args=[group.slug]), {
            'next': reverse('user_list'),
        })

        self.assertRedirects(response, reverse('user_list'))
        self.assertTrue(group.members.filter(id=self.member.id).exists())

    def test_group_member_can_post_message(self):
        group = FitnessGroup.objects.create(
            name='Run Club',
            description='Pace chat',
            created_by=self.owner,
        )
        group.members.add(self.owner)

        response = self.client.post(reverse('group_detail', args=[group.slug]), {
            'text': 'Finished 5k today',
        })

        self.assertRedirects(response, reverse('group_detail', args=[group.slug]))
        self.assertTrue(GroupMessage.objects.filter(group=group, user=self.owner, text='Finished 5k today').exists())

    def test_non_member_cannot_post_message(self):
        group = FitnessGroup.objects.create(
            name='Evening Yoga',
            description='Mobility and recovery',
            created_by=self.owner,
        )
        group.members.add(self.owner)

        self.client.logout()
        self.client.login(username='member', password='password')
        response = self.client.post(reverse('group_detail', args=[group.slug]), {
            'text': 'Can I join the next session?',
        })

        self.assertRedirects(response, reverse('group_detail', args=[group.slug]))
        self.assertFalse(GroupMessage.objects.filter(group=group, user=self.member).exists())

    def test_community_page_shows_groups(self):
        group = FitnessGroup.objects.create(
            name='Step Streak',
            description='Walk every day',
            created_by=self.owner,
        )
        group.members.add(self.owner)

        response = self.client.get(reverse('user_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fitness Groups')
        self.assertContains(response, 'Step Streak')


@override_settings(
    STRAVA_CLIENT_ID='12345',
    STRAVA_CLIENT_SECRET='super-secret',
    STRAVA_OAUTH_SCOPES='activity:read_all',
)
class StravaIntegrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='stravauser', password='password')
        self.client.login(username='stravauser', password='password')

    def test_connect_strava_redirects_to_authorize_url(self):
        response = self.client.get(reverse('connect_strava'))

        self.assertEqual(response.status_code, 302)
        self.assertIn('https://www.strava.com/oauth/authorize', response.url)
        self.assertIn('client_id=12345', response.url)
        self.assertTrue(self.client.session.get('strava_oauth_state'))

    def test_strava_callback_exchanges_code_and_syncs(self):
        session = self.client.session
        session['strava_oauth_state'] = 'known-state'
        session.save()

        with patch('users.views.strava.exchange_code_for_token') as exchange_code:
            with patch('users.views.strava.sync_recent_activities', return_value={'created': 2, 'updated': 1}):
                response = self.client.get(reverse('strava_callback'), {
                    'state': 'known-state',
                    'code': 'auth-code',
                    'scope': 'activity:read_all',
                })

        self.assertRedirects(response, reverse('profile'))
        exchange_code.assert_called_once()

    def test_sync_recent_activities_imports_cardio_sessions(self):
        self.user.strava_access_token = 'access-token'
        self.user.strava_refresh_token = 'refresh-token'
        self.user.strava_scopes = 'activity:read_all'
        self.user.strava_token_expires_at = timezone.now() + timedelta(hours=2)
        self.user.save()

        activity_payload = [
            {
                'id': 987654321,
                'name': 'Evening Run',
                'sport_type': 'Run',
                'distance': 5000.0,
                'moving_time': 1800,
                'average_heartrate': 152.4,
                'start_date_local': '2026-04-20T18:30:00Z',
            }
        ]

        with patch('users.strava._request_json', return_value=activity_payload):
            result = strava.sync_recent_activities(self.user)

        self.assertEqual(result['created'], 1)
        cardio = CardioSession.objects.get(user=self.user, strava_activity_id=987654321)
        self.assertEqual(cardio.activity_type, 'running')
        self.assertEqual(cardio.duration_minutes, 30)
        self.assertEqual(cardio.distance_km, 5.0)
        self.assertEqual(cardio.avg_heart_rate, 152)
