import json
from datetime import timedelta, timezone as dt_timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from tracker.models import CardioSession


STRAVA_AUTHORIZE_URL = 'https://www.strava.com/oauth/authorize'
STRAVA_TOKEN_URL = 'https://www.strava.com/oauth/token'
STRAVA_DEAUTHORIZE_URL = 'https://www.strava.com/oauth/deauthorize'
STRAVA_API_BASE_URL = 'https://www.strava.com/api/v3'
READ_SCOPES = {'activity:read', 'activity:read_all'}
SPORT_TYPE_MAP = {
    'Run': 'running',
    'TrailRun': 'running',
    'VirtualRun': 'running',
    'Ride': 'cycling',
    'MountainBikeRide': 'cycling',
    'GravelRide': 'cycling',
    'EBikeRide': 'cycling',
    'EMountainBikeRide': 'cycling',
    'VirtualRide': 'cycling',
    'Handcycle': 'cycling',
    'Swim': 'swimming',
    'Walk': 'walking',
    'Hike': 'walking',
    'Rowing': 'rowing',
}


class StravaError(Exception):
    pass


def is_configured():
    return bool(settings.STRAVA_CLIENT_ID and settings.STRAVA_CLIENT_SECRET)


def requested_scopes():
    return [scope.strip() for scope in settings.STRAVA_OAUTH_SCOPES.split(',') if scope.strip()]


def has_read_scope(scopes_text):
    scopes = {scope.strip() for scope in scopes_text.split(',') if scope.strip()}
    return bool(scopes & READ_SCOPES)


def build_authorization_url(redirect_uri, state):
    if not is_configured():
        raise StravaError('Strava credentials are not configured.')

    params = {
        'client_id': settings.STRAVA_CLIENT_ID,
        'redirect_uri': redirect_uri,
        'response_type': 'code',
        'approval_prompt': 'auto',
        'scope': ','.join(requested_scopes()),
        'state': state,
    }
    return f'{STRAVA_AUTHORIZE_URL}?{urlencode(params)}'


def _request_json(url, *, method='GET', data=None, headers=None):
    encoded_data = None
    request_headers = headers or {}
    if data is not None:
        encoded_data = urlencode(data).encode('utf-8')
        request_headers.setdefault('Content-Type', 'application/x-www-form-urlencoded')

    request = Request(url, data=encoded_data, headers=request_headers, method=method)

    try:
        with urlopen(request, timeout=20) as response:
            body = response.read().decode('utf-8')
    except HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')
        try:
            payload = json.loads(body)
            message = payload.get('message') or payload.get('errors') or body
        except json.JSONDecodeError:
            message = body or exc.reason
        raise StravaError(f'Strava request failed: {message}') from exc
    except URLError as exc:
        raise StravaError('Could not reach Strava. Please try again.') from exc

    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise StravaError('Strava returned an unexpected response.') from exc


def store_token_payload(user, token_payload, *, accepted_scopes=''):
    expires_at = token_payload.get('expires_at')
    user.strava_access_token = token_payload.get('access_token', '')
    user.strava_refresh_token = token_payload.get('refresh_token', '')
    user.strava_scopes = accepted_scopes
    user.strava_athlete_id = token_payload.get('athlete', {}).get('id')
    user.strava_token_expires_at = (
        timezone.datetime.fromtimestamp(expires_at, tz=dt_timezone.utc)
        if expires_at
        else None
    )
    user.save(update_fields=[
        'strava_access_token',
        'strava_refresh_token',
        'strava_scopes',
        'strava_athlete_id',
        'strava_token_expires_at',
    ])


def exchange_code_for_token(user, *, code, redirect_uri, accepted_scopes=''):
    payload = _request_json(
        STRAVA_TOKEN_URL,
        method='POST',
        data={
            'client_id': settings.STRAVA_CLIENT_ID,
            'client_secret': settings.STRAVA_CLIENT_SECRET,
            'code': code,
            'grant_type': 'authorization_code',
        },
    )
    store_token_payload(user, payload, accepted_scopes=accepted_scopes)
    return payload


def refresh_access_token(user):
    if not user.strava_refresh_token:
        raise StravaError('No Strava refresh token is stored for this account.')

    payload = _request_json(
        STRAVA_TOKEN_URL,
        method='POST',
        data={
            'client_id': settings.STRAVA_CLIENT_ID,
            'client_secret': settings.STRAVA_CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': user.strava_refresh_token,
        },
    )
    store_token_payload(user, payload, accepted_scopes=user.strava_scopes)
    return payload


def ensure_access_token(user):
    if not is_configured():
        raise StravaError('Strava credentials are not configured.')
    if not user.strava_access_token:
        raise StravaError('Connect your Strava account first.')
    if not has_read_scope(user.strava_scopes):
        raise StravaError('Reconnect Strava and approve activity access to sync workouts.')

    expires_at = user.strava_token_expires_at
    if not expires_at or expires_at <= timezone.now() + timedelta(hours=1):
        refresh_access_token(user)
        user.refresh_from_db(fields=['strava_access_token', 'strava_refresh_token', 'strava_token_expires_at'])

    return user.strava_access_token


def fetch_activities(user, *, after=None, page_size=30, max_pages=3):
    access_token = ensure_access_token(user)
    activities = []

    for page in range(1, max_pages + 1):
        params = {
            'page': page,
            'per_page': page_size,
        }
        if after is not None:
            params['after'] = after

        payload = _request_json(
            f'{STRAVA_API_BASE_URL}/athlete/activities?{urlencode(params)}',
            headers={'Authorization': f'Bearer {access_token}'},
        )
        if not payload:
            break

        activities.extend(payload)
        if len(payload) < page_size:
            break

    return activities


def revoke_access(user):
    if user.strava_access_token:
        try:
            _request_json(
                STRAVA_DEAUTHORIZE_URL,
                method='POST',
                data={'access_token': user.strava_access_token},
            )
        except StravaError:
            pass

    user.strava_athlete_id = None
    user.strava_access_token = ''
    user.strava_refresh_token = ''
    user.strava_token_expires_at = None
    user.strava_scopes = ''
    user.strava_last_sync_at = None
    user.save(update_fields=[
        'strava_athlete_id',
        'strava_access_token',
        'strava_refresh_token',
        'strava_token_expires_at',
        'strava_scopes',
        'strava_last_sync_at',
    ])


def sync_recent_activities(user):
    first_sync = user.strava_last_sync_at is None
    after = None
    if first_sync:
        after = int((timezone.now() - timedelta(days=30)).timestamp())
    else:
        after = int((user.strava_last_sync_at - timedelta(minutes=5)).timestamp())

    activities = fetch_activities(user, after=after)
    created = 0
    updated = 0

    for activity in activities:
        strava_activity_id = activity.get('id')
        if not strava_activity_id:
            continue

        duration_seconds = activity.get('moving_time') or activity.get('elapsed_time') or 0
        if duration_seconds <= 0:
            continue

        sport_type = activity.get('sport_type') or activity.get('type') or ''
        started_at = parse_datetime(activity.get('start_date_local') or activity.get('start_date') or '')
        cardio_date = started_at.date() if started_at else timezone.localdate()
        notes = f"Imported from Strava: {activity.get('name', 'Activity')}"

        cardio_session, was_created = CardioSession.objects.update_or_create(
            user=user,
            strava_activity_id=strava_activity_id,
            defaults={
                'date': cardio_date,
                'activity_type': SPORT_TYPE_MAP.get(sport_type, 'other'),
                'duration_minutes': max(1, round(duration_seconds / 60)),
                'distance_km': round((activity.get('distance') or 0) / 1000, 2) or None,
                'avg_heart_rate': round(activity['average_heartrate']) if activity.get('average_heartrate') else None,
                'notes': notes,
            },
        )
        created += int(was_created)
        updated += int(not was_created)

    user.strava_last_sync_at = timezone.now()
    user.save(update_fields=['strava_last_sync_at'])

    return {
        'created': created,
        'updated': updated,
        'fetched': len(activities),
        'first_sync': first_sync,
    }
