"""V4 customer product. Server-owned sandbox money, scoped observation and private checks.

Run via run_demo.py. The older api.py remains an explicit research/partner-contract
example and is not mounted on this public entrypoint.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlsplit

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from payment_review import canonical, digest
from simulator_service import LiveModel, Simulator, UnavailableModel

ROOT = Path(__file__).resolve().parents[1]


class Body(BaseModel):
    model_config = ConfigDict(extra='forbid')


class WorldInput(Body):
    seed: int = Field(default_factory=lambda: secrets.randbelow(2**32), ge=0, lt=2**32)
    preset: Literal['everyday', 'investment', 'refund', 'probes'] = 'everyday'


class IntentInput(Body):
    recipient: int = Field(gt=0)
    amount_paise: int = Field(gt=0, le=100_000_000)
    context: Literal['none', 'refund', 'withdrawal', 'rent', 'merchant_refund'] = 'none'


class SendInput(Body):
    review_id: str = Field(max_length=80)
    confirmed: bool = False
    authorization: Literal['DEMO']


class GrantInput(Body):
    role: Literal['judge', 'recipient', 'contact']
    account: int = Field(default=1, gt=0)


class PairInput(Body):
    code: str = Field(min_length=12, max_length=64)


class CheckInput(Body):
    direction: Literal['incoming', 'outgoing', 'unknown'] = 'unknown'
    purpose: Literal['refund', 'withdrawal', 'rent', 'merchant_refund', 'unknown'] = 'unknown'
    operation: Literal['transfer', 'mandate', 'unknown'] = 'unknown'


class CaseInput(Body):
    review_id: str = Field(max_length=80)


class ScenarioInput(Body):
    recipient: int = Field(gt=0)
    amount_paise: int = Field(gt=0, le=100_000_000)
    context: Literal['none', 'refund', 'withdrawal', 'rent', 'merchant_refund'] = 'none'


class ContactResponseInput(Body):
    payment_id: str = Field(min_length=1, max_length=80)
    response: Literal['support', 'concern']


class OperatorDecisionInput(CaseInput):
    payment_id: str = Field(min_length=1, max_length=80)
    revision: int = Field(ge=1)
    decision: Literal['approve', 'reject']


class LabelInput(CaseInput):
    classification: Literal['fraud','benign','unknown']
    maturity_at: float = Field(ge=0)
    supersedes: str | None = Field(default=None,max_length=80)


def private_review(record):
    """Explicit projection; never return storage/session/raw-message envelopes."""
    return dict(id=record['id'], payment_id=record['payment']['id'],
                revision=record['payment']['revision'], amount_paise=record['payment']['amount_paise'],
                recipient=record['payment']['recipient'], evaluated_at=record['evaluated_at'],
                expires_at=record['expires_at'], decision=record['decision'], groups=record['groups'],
                model=record['model'], versions=record['versions'], timings_ms=record['timings_ms'],
                comparison=record['comparison'], features=record['feature_snapshot']['values'],
                graph_convention=record['feature_snapshot']['graph_convention'],
                lineage=record['feature_snapshot']['lineage'], digest=record['digest'], signature=record.get('signature'),
                graph=[dict(source=e['sender'], target=e['receiver'], event_id=e['id'])
                       for e in record['feature_snapshot']['evidence'] if e['kind']=='payment'
                       and record['payment']['recipient'] in (e['sender'],e['receiver'])][-24:])


def create_app(database=None, model=None, secret=None, raise_internal_errors=False):
    production = os.getenv('MAYA_ENV') == 'production'
    origin = os.getenv('MAYA_PUBLIC_ORIGIN', '').rstrip('/')
    if production and (not origin.startswith('https://') or len(os.getenv('MAYA_SESSION_SECRET', '')) < 32):
        raise RuntimeError('Production requires HTTPS MAYA_PUBLIC_ORIGIN and a 32+ character MAYA_SESSION_SECRET')
    directory = ROOT / 'data/v4'
    directory.mkdir(parents=True, exist_ok=True)
    if secret is None:
        secret = os.getenv('MAYA_SESSION_SECRET')
        if not secret:
            keyfile = directory / 'session.key'
            if not keyfile.exists():
                try:
                    keyfile.write_text(secrets.token_hex(32), encoding='utf-8')
                    keyfile.chmod(0o600)
                except OSError:
                    raise RuntimeError('Unable to persist local session key')
            secret = keyfile.read_text(encoding='utf-8').strip()
    if model is None:
        folder = Path(os.getenv('MAYA_MODEL_DIR', str(ROOT / 'models/wallet')))
        try:
            if not (folder / 'manifest.json').is_file():
                raise ValueError('Bundle manifest missing; run scripts/bootstrap_v4.py')
            model = LiveModel(folder / 'xgb_model.json', folder / 'conformal.json')
        except (OSError, ValueError, KeyError) as exc:
            model = UnavailableModel()
            model.reason = str(exc)
    database = database or os.getenv('MAYA_DATABASE_URL') or str(directory / 'product.sqlite')
    service = Simulator(database, model)
    partner_model=None
    partner_path=os.getenv('MAYA_PARTNER_MODEL_DIR')
    if partner_path:
        folder=Path(partner_path)
        meta=json.loads((folder/'manifest.json').read_text())
        report=folder/'validation-report.json'
        if (not os.getenv('MAYA_PARTNER_SOURCE') or meta.get('source')!=os.getenv('MAYA_PARTNER_SOURCE')
                or not report.is_file() or meta.get('validation_report_sha256')!=hashlib.sha256(report.read_bytes()).hexdigest()
                or not json.loads(report.read_text()).get('approved_for_shadow_operation')):
            raise RuntimeError('Partner bundle needs a matching source and hashed, approved shadow-validation report')
        partner_model=LiveModel(folder/'xgb_model.json',folder/'conformal.json')
    with service.lock:
        service.db.executescript('''
          CREATE TABLE IF NOT EXISTS product_pair(code TEXT PRIMARY KEY, world TEXT NOT NULL,
            role TEXT NOT NULL, account INTEGER NOT NULL, expires REAL NOT NULL, claimed INTEGER NOT NULL DEFAULT 0);
          CREATE TABLE IF NOT EXISTS product_grant(id TEXT PRIMARY KEY, world TEXT NOT NULL,
            role TEXT NOT NULL, account INTEGER NOT NULL, expires REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
          CREATE TABLE IF NOT EXISTS product_idempotency(owner TEXT NOT NULL, path TEXT NOT NULL,
            key TEXT NOT NULL, fingerprint TEXT NOT NULL, body TEXT NOT NULL, PRIMARY KEY(owner,path,key));
          CREATE TABLE IF NOT EXISTS product_case(id TEXT PRIMARY KEY, world TEXT NOT NULL, body TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS product_check(id TEXT PRIMARY KEY, owner TEXT NOT NULL, body TEXT NOT NULL);
          CREATE TABLE IF NOT EXISTS product_label(id TEXT PRIMARY KEY, world TEXT NOT NULL, body TEXT NOT NULL);
        ''')
        service.db.commit()
    app = FastAPI(title='MAYA payment safety', version='4.0', docs_url='/api/docs' if not production else None,
                  openapi_url='/api/openapi.json' if not production else None)
    app.state.service = service
    app.state.metrics = defaultdict(int)
    arrivals = defaultdict(deque)
    traffic_lock = threading.Lock()
    slots = threading.BoundedSemaphore(int(os.getenv('MAYA_MAX_INFLIGHT', '8')))
    observation_slots=threading.BoundedSemaphore(32)
    contexts = dict(none='', refund='Approve to receive your refund',
                    withdrawal='Pay 1 to release your investment withdrawal', rent='Pay your rent',
                    merchant_refund='Send a refund to your customer')

    def purge_expired(now=None):
        """Expire abandoned demo worlds and derived companion checks by policy TTL."""
        now = time.time() if now is None else float(now)
        world_ttl = max(1, int(os.getenv('MAYA_WORLD_RETENTION_DAYS', '7'))) * 86400
        check_ttl = max(1, int(os.getenv('MAYA_CHECK_RETENTION_HOURS', '24'))) * 3600
        removed_worlds = 0
        with service.lock:
            worlds = service.db.execute('SELECT id,owner FROM sim_world').fetchall()
            expired = []
            for row in worlds:
                created = service.db.execute(
                    "SELECT body FROM sim_event WHERE world=? ORDER BY sequence LIMIT 1", (row['id'],)
                ).fetchone()
                created_at = json.loads(created[0]).get('recorded_at', now) if created else now
                if now - float(created_at) >= world_ttl:
                    expired.append((row['id'], row['owner']))
            for wid, owner_id in expired:
                for table in ('product_pair', 'product_grant', 'product_case', 'product_label'):
                    service.db.execute(f'DELETE FROM {table} WHERE world=?', (wid,))
                service.db.execute('DELETE FROM product_idempotency WHERE owner=?', (owner_id,))
                service.delete_world(wid, owner_id)
                removed_worlds += 1
            rows = service.db.execute('SELECT id,body FROM product_check').fetchall()
            for row in rows:
                created_at = json.loads(row['body']).get('created_at', now)
                if now - float(created_at) >= check_ttl:
                    service.db.execute('DELETE FROM product_check WHERE id=?', (row['id'],))
            service.db.commit()
        return removed_worlds

    purge_expired()
    app.state.last_purge = time.monotonic()

    @app.middleware('http')
    async def retention_sweep(request: Request, call_next):
        if time.monotonic() - app.state.last_purge >= 60:
            purge_expired()
            app.state.last_purge = time.monotonic()
        return await call_next(request)

    def require_operator(key):
        expected = os.getenv('MAYA_OPERATOR_KEY', '')
        if len(expected) < 32 or not secrets.compare_digest(expected, key or ''):
            raise HTTPException(403, 'Independent operator credentials required')

    def sign(value):
        return hmac.new(secret.encode(), value.encode(), hashlib.sha256).hexdigest()

    service.signer = sign

    def project(record):
        result=private_review(record)
        result['projection_digest']=digest(result)
        result['projection_signature']=sign(result['projection_digest'])
        return result

    def session_value(request):
        raw = request.cookies.get('maya_session_v4', '')
        token, _, signature = raw.rpartition('.')
        if len(token) > 32 and hmac.compare_digest(signature, sign(token)):
            try:
                if time.time() - int(token.split(':')[0]) < 86400:
                    return token, False
            except ValueError:
                pass
        return str(int(time.time())) + ':' + secrets.token_urlsafe(32), True

    @app.middleware('http')
    async def boundary(request: Request, call_next):
        started = time.perf_counter()
        token, fresh = session_value(request)
        request.state.owner = digest(token)
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            supplied = request.headers.get('origin')
            expected = origin or str(request.base_url).rstrip('/')
            if supplied and supplied != expected:
                return JSONResponse({'detail': 'Cross-origin request refused'}, status_code=403)
            if request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': 'Cross-site request refused'}, status_code=403)
            body = await request.body()
            if len(body) > 32768:
                return JSONResponse({'detail': 'Request too large'}, status_code=413)
            # Function middleware is implemented with a downstream ASGI receive
            # channel. Replaying the cached bytes is required after reading the
            # body here; otherwise the endpoint can wait forever for a body that
            # this middleware already consumed.
            async def receive_body():
                return {'type': 'http.request', 'body': body, 'more_body': False}
            request._receive = receive_body
        if request.url.path.startswith('/v1/'):
            identity = request.client.host if request.client else 'unknown'
            now = time.monotonic()
            with traffic_lock:
                # IP budget prevents cookie rotation from bypassing the limiter.
                if len(arrivals) > 10000:
                    for k in list(arrivals):
                        if not arrivals[k] or arrivals[k][-1] < now - 60:
                            del arrivals[k]
                q = arrivals[identity]
                while q and q[0] < now - 60:
                    q.popleft()
                if len(q) >= int(os.getenv('MAYA_REQUESTS_PER_MINUTE', '600')):
                    return JSONResponse({'detail': 'Request limit reached'}, status_code=429, headers={'Retry-After': '5'})
                q.append(now)
        try:
            response = await call_next(request)
        except Exception:
            app.state.metrics['errors'] += 1
            if raise_internal_errors and not production:
                raise
            response = JSONResponse({'detail': 'Service unavailable; no payment confirmed'}, status_code=503)
        if fresh:
            response.set_cookie('maya_session_v4', token + '.' + sign(token), httponly=True,
                                secure=production, samesite='strict', max_age=86400)
        response.headers.update({'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
                                 'Referrer-Policy': 'no-referrer', 'X-Frame-Options': 'SAMEORIGIN',
                                 'Permissions-Policy': 'camera=(self), microphone=(), geolocation=()',
                                 'Content-Security-Policy': "default-src 'self'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data: blob:; connect-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'",
                                 'Server-Timing': f'handler;dur={(time.perf_counter()-started)*1000:.2f}'})
        if production:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        app.state.metrics['requests'] += 1
        return response

    @app.exception_handler(ValueError)
    async def invalid(request, exc):
        return JSONResponse({'detail': str(exc)}, status_code=409)

    @app.exception_handler(sqlite3.OperationalError)
    async def unavailable(request, exc):
        return JSONResponse({'detail': 'Storage unavailable; retry safely'}, status_code=503)

    def owner(request):
        return request.state.owner

    def call_once(request, path, key, body, operation):
        if not key or len(key) > 100:
            raise HTTPException(422, 'A bounded Idempotency-Key is required')
        fingerprint = digest(body)
        # The lock protects this process. BEGIN IMMEDIATE serializes independent workers.
        # Operations themselves are transactional; keyed creation is done under this lock.
        with service.transaction():
            if hasattr(service.db, 'raw'):
                service.db.execute('SELECT pg_advisory_xact_lock(hashtextextended(?,0))',
                                   (owner(request)+':'+path+':'+key,))
            row = service.db.execute('SELECT fingerprint,body FROM product_idempotency WHERE owner=? AND path=? AND key=?',
                                     (owner(request), path, key)).fetchone()
            if row:
                if row[0] != fingerprint:
                    raise HTTPException(409, 'Idempotency key reused with different input')
                return json.loads(row[1])
            result = operation()
            service.db.execute('INSERT INTO product_idempotency VALUES(?,?,?,?,?)',
                               (owner(request), path, key, fingerprint, canonical(result)))
            return result

    def read_grant(request):
        token = request.cookies.get('maya_observer_v4', '')
        with service.lock:
            row = service.db.execute('SELECT * FROM product_grant WHERE id=?', (digest(token),)).fetchone()
            if not row or row['revoked'] or row['expires'] <= time.time():
                raise HTTPException(403, 'Observation access expired or revoked')
            world = service.db.execute('SELECT owner FROM sim_world WHERE id=?', (row['world'],)).fetchone()
            if not world:
                raise HTTPException(404, 'Session deleted')
            return dict(row), world[0]

    @app.get('/v1/health')
    def health():
        with service.lock:
            service.db.execute('SELECT 1').fetchone()
        return dict(status='ready' if model.ready else 'not_ready', model_loaded=model.ready,
                    mode='sandbox-and-companion', version='4.0', storage='postgresql' if hasattr(service.db,'raw') else 'sqlite-single-worker')

    @app.get('/readyz')
    def ready():
        if not model.ready:
            raise HTTPException(503, 'Compatible model bundle unavailable')
        return health()

    @app.get('/livez')
    def live():
        return {'status': 'alive'}

    @app.get('/v1/model')
    def model_info():
        return dict(ready=model.ready, model_version=model.version, calibration_version=model.calibration_version,
                    calibration=getattr(model, 'calibration_report', None),
                    limits=['Synthetic training data', 'Legacy report-outward graph', 'Not real-bank validation'])

    @app.get('/v1/observe/benchmarks')
    def benchmarks(request: Request):
        grant,_=read_grant(request)
        if grant['role']!='judge':
            raise HTTPException(403,'Judge role required')
        result={}
        for name in ('paysim','load','validation','kit','fairness','lookalikes',
                     'heldout-types','seed-sweep','fast-path','cold-start'):
            path=ROOT/'reports'/(name+'.json')
            if not path.exists():
                path=ROOT/'docs/evidence'/(name+'.json')
            if path.exists():
                result[name]=json.loads(path.read_text(encoding='utf-8'))
        return dict(reports=result, model_calibration=getattr(model,'calibration_report',None),
                    limits='Frozen recorded runs, not live fraud accuracy or national-UPI capacity')

    @app.post('/v1/sandbox/worlds', status_code=201)
    def create_world(body: WorldInput, request: Request, idempotency_key: str = Header(...)):
        return call_once(request, 'world', idempotency_key, body.model_dump(),
                         lambda: service.create_world(owner(request), body.seed, body.preset))

    @app.get('/v1/sandbox/worlds/{wid}')
    def world(wid: str, request: Request):
        return service.read_world(wid, owner(request))

    @app.post('/v1/sandbox/worlds/{wid}/intents', status_code=201)
    def intent(wid: str, body: IntentInput, request: Request, idempotency_key: str = Header(...)):
        return call_once(request, 'intent:' + wid, idempotency_key, body.model_dump(),
                         lambda: service.intent(wid, owner(request), body.recipient, body.amount_paise,
                                                contexts[body.context], body.context != 'none', context=body.context))

    @app.put('/v1/sandbox/worlds/{wid}/intents/{pid}')
    def edit(wid: str, pid: str, body: IntentInput, request: Request):
        return service.intent(wid, owner(request), body.recipient, body.amount_paise,
                              contexts[body.context], body.context != 'none', pid, body.context)

    @app.post('/v1/sandbox/worlds/{wid}/intents/{pid}/review')
    def review(wid: str, pid: str, request: Request):
        if not model.ready:
            raise HTTPException(503, 'Compatible model unavailable')
        if not slots.acquire(blocking=False):
            raise HTTPException(503, 'Review capacity reached; retry later', headers={'Retry-After': '1'})
        try:
            return project(service.review(wid, owner(request), pid))
        finally:
            slots.release()

    @app.post('/v1/sandbox/worlds/{wid}/intents/{pid}/execute')
    def execute(wid: str, pid: str, body: SendInput, request: Request):
        return service.execute(wid, owner(request), pid, body.review_id, body.confirmed, body.authorization)

    @app.post('/v1/sandbox/worlds/{wid}/intents/{pid}/cancel')
    def cancel(wid: str, pid: str, request: Request):
        return service.cancel(wid, owner(request), pid)

    @app.post('/v1/sandbox/worlds/{wid}/pair')
    def pair(wid: str, body: GrantInput, request: Request):
        with service.transaction():
            state = service._world(wid, owner(request))
            if body.account not in {a['id'] for a in state['accounts']}:
                raise HTTPException(422, 'Unknown recipient')
            if body.role == 'contact' and not state.get('contact_consent', False):
                raise HTTPException(409, 'Enable trusted-contact consent before pairing')
            code = secrets.token_hex(6)
            service.db.execute('INSERT INTO product_pair VALUES(?,?,?,?,?,0)',
                               (digest(code), wid, body.role, body.account, time.time() + 300))
        path = {'judge': '/demo/', 'recipient': '/recipient/', 'contact': '/contact/'}[body.role]
        return dict(code=code, expires_in=300, url=path)

    @app.post('/v1/observe/pair')
    def exchange(body: PairInput):
        with service.transaction():
            row = service.db.execute('SELECT * FROM product_pair WHERE code=?', (digest(body.code.strip().lower()),)).fetchone()
            if not row or row['claimed'] or row['expires'] <= time.time():
                raise HTTPException(403, 'Pairing code invalid or expired')
            service.db.execute('UPDATE product_pair SET claimed=1 WHERE code=?', (row['code'],))
            token = secrets.token_urlsafe(32)
            service.db.execute('INSERT INTO product_grant VALUES(?,?,?,?,?,0)',
                               (digest(token), row['world'], row['role'], row['account'], time.time()+1800))
        response = JSONResponse(dict(role=row['role'], expires_in=1800))
        response.set_cookie('maya_observer_v4', token, httponly=True, samesite='strict', secure=production, max_age=1800)
        return response

    @app.post('/v1/sandbox/worlds/{wid}/revoke')
    def revoke(wid: str, request: Request):
        with service.transaction():
            service._world(wid, owner(request))
            service.db.execute('UPDATE product_grant SET revoked=1 WHERE world=?', (wid,))
            service.db.execute('UPDATE product_pair SET claimed=1 WHERE world=?', (wid,))
        return {'revoked': True}

    @app.post('/v1/sandbox/worlds/{wid}/contact-consent')
    def contact_consent(wid: str, body: dict, request: Request):
        enabled = body.get('enabled')
        if type(enabled) is not bool or set(body) != {'enabled'}:
            raise HTTPException(422, 'Send only an explicit enabled boolean')
        with service.transaction():
            state = service._world(wid, owner(request))
            state['contact_consent'] = enabled
            state['revision'] += 1
            if not enabled:
                service.db.execute("UPDATE product_grant SET revoked=1 WHERE world=? AND role='contact'", (wid,))
                service.db.execute("UPDATE product_pair SET claimed=1 WHERE world=? AND role='contact'", (wid,))
            service._save_world(state)
            service._event(wid, 'contact_consent_changed', enabled=enabled)
        return dict(enabled=enabled)

    @app.get('/v1/sandbox/worlds/{wid}/judge-scenarios')
    def judge_scenarios(wid: str, request: Request):
        state = service.read_world(wid, owner(request))
        return dict(scenarios=[p for p in state['intents'] if p.get('source') == 'judge' and p['state'] == 'pending'][-5:])

    @app.post('/v1/observe/scenario', status_code=201)
    def create_judge_scenario(body: ScenarioInput, request: Request):
        grant, actual_owner = read_grant(request)
        if grant['role'] != 'judge':
            raise HTTPException(403, 'Judge role required')
        if body.recipient == 0:
            raise HTTPException(422, 'Payer cannot be the recipient')
        try:
            payment = service.intent(grant['world'], actual_owner, body.recipient,
                                     body.amount_paise, contexts[body.context], body.context != 'none',
                                     context=body.context)
        except ValueError as exc:
            raise HTTPException(422, str(exc))
        with service.transaction():
            payment['source'] = 'judge'
            service._save_intent(payment)
            service._event(grant['world'], 'judge_scenario_created', payment['id'],
                           revision=payment['revision'], amount_paise=payment['amount_paise'])
        return dict(payment_id=payment['id'], revision=payment['revision'],
                    recipient=payment['recipient'], amount_paise=payment['amount_paise'],
                    context=body.context, delivered_to_customer=True, simulated=True)

    @app.get('/v1/observe')
    def observe(request: Request):
        grant, actual_owner = read_grant(request)
        state = service.read_world(grant['world'], actual_owner)
        if grant['role'] == 'recipient':
            account = next(a for a in state['accounts'] if a['id'] == grant['account'])
            return dict(role='recipient', recipient=account['name'], balance_paise=account['balance_paise'],
                        transfers=[t for t in state['transfers'] if t['recipient'] == grant['account']])
        if grant['role'] == 'contact':
            if not state.get('contact_consent', False):
                raise HTTPException(403, 'Trusted-contact consent was revoked')
            with service.lock:
                rows = service.db.execute(
                    "SELECT sequence,body FROM sim_event WHERE world=? ORDER BY sequence DESC LIMIT 200",
                    (grant['world'],),
                ).fetchall()
            alerts = [dict(sequence=r[0], **json.loads(r[1])) for r in rows
                      if json.loads(r[1]).get('stage') == 'trusted_contact_alert']
            responses = {json.loads(r[1]).get('payment_id'): json.loads(r[1]).get('response')
                         for r in rows if json.loads(r[1]).get('stage') == 'trusted_contact_response'}
            return dict(role='contact', alerts=[dict(sequence=a['sequence'], payment_id=a.get('payment_id'),
                        message=a.get('message'), response=responses.get(a.get('payment_id')),
                        recorded_at=a.get('recorded_at')) for a in reversed(alerts)])
        with service.lock:
            rows = service.db.execute('SELECT body FROM sim_review WHERE world=? ORDER BY rowid DESC LIMIT 20', (grant['world'],)).fetchall()
        world = service.read_world(grant['world'], actual_owner)
        return dict(role='judge', world_id=grant['world'], synthetic=True,
                    accounts=[dict(id=a['id'], name=a['name'], business=a['business']) for a in world['accounts']],
                    reviews=[project(service.replay(grant['world'], actual_owner, json.loads(r[0])['id'])) for r in rows], transfers=state['transfers'])

    @app.post('/v1/observe/contact-response')
    def contact_response(body: ContactResponseInput, request: Request):
        grant, _ = read_grant(request)
        if grant['role'] != 'contact':
            raise HTTPException(403, 'Trusted-contact access required')
        with service.transaction():
            world = service.db.execute('SELECT body FROM sim_world WHERE id=?', (grant['world'],)).fetchone()
            if not world or not json.loads(world[0]).get('contact_consent', False):
                raise HTTPException(403, 'Trusted-contact consent was revoked')
            alert_rows = service.db.execute('SELECT body FROM sim_event WHERE world=?', (grant['world'],)).fetchall()
            if not any((event := json.loads(row[0])).get('stage') == 'trusted_contact_alert'
                       and event.get('payment_id') == body.payment_id for row in alert_rows):
                raise HTTPException(404, 'No trusted-contact alert exists')
            payment = service.db.execute('SELECT body FROM sim_intent WHERE id=? AND world=?',
                                         (body.payment_id, grant['world'])).fetchone()
            if not payment:
                raise HTTPException(404, 'Payment not found')
            service._event(grant['world'], 'trusted_contact_response', body.payment_id,
                           response=body.response, actor_role='trusted_contact',
                           notice='Advice only; does not approve or release a payment')
        return dict(recorded=True, response=body.response, payment_control=False)

    @app.get('/v1/observe/events')
    async def events(request: Request, after: int = 0):
        grant, actual_owner = read_grant(request)
        if grant['role'] != 'judge':
            raise HTTPException(403, 'Judge role required')
        try:
            after = max(0, int(request.headers.get('last-event-id', after)))
        except ValueError:
            raise HTTPException(422, 'Invalid event cursor')
        async def stream():
            cursor = after
            try:
                for _ in range(120):
                    if await request.is_disconnected():
                        return
                    try:
                        read_grant(request)
                    except HTTPException:
                        return
                    # No per-subscriber queue. Read committed events with bounded pages.
                    batch = await asyncio.to_thread(service.events, grant['world'], actual_owner, cursor)
                    for e in batch:
                        cursor = e['sequence']
                        safe = {k: e[k] for k in ('sequence','stage','payment_id','evaluation_id','duration_ms','status','recorded_at','review_id') if k in e}
                        yield f'id: {cursor}\ndata: {canonical(safe)}\n\n'
                    if not batch:
                        yield ': heartbeat\n\n'
                    await asyncio.sleep(0.5)
            finally:
                observation_slots.release()
        if not observation_slots.acquire(blocking=False):
            raise HTTPException(503,'Observation capacity reached',headers={'Retry-After':'5'})
        return StreamingResponse(stream(), media_type='text/event-stream', headers={'X-Accel-Buffering': 'no'})

    @app.post('/v1/checks', status_code=201)
    def check(body: CheckInput, request: Request):
        mismatch = body.direction == 'incoming' and body.operation == 'transfer'
        reason = ('This sends money. The message describes incoming money.' if mismatch else
                  'A payment cannot verify a promised investment withdrawal.' if body.purpose == 'withdrawal' else
                  'Bank history and verified recipient information are unavailable for this check.')
        record = dict(id=secrets.token_hex(16), status='limited_information', action='nudge' if mismatch or body.purpose == 'withdrawal' else 'incomplete',
                      reasons=[reason], score=None, input=body.model_dump(), created_at=time.time(),
                      source='user-declared intent; not bank-verified', retained='derived intent only')
        with service.transaction():
            service.db.execute('INSERT INTO product_check VALUES(?,?,?)', (record['id'],owner(request),canonical(record)))
        return record

    @app.get('/v1/checks/{cid}')
    def get_check(cid: str, request: Request):
        with service.lock:
            row = service.db.execute('SELECT body FROM product_check WHERE id=? AND owner=?',(cid,owner(request))).fetchone()
        if not row:
            raise HTTPException(404, 'Check not found')
        return json.loads(row[0])

    @app.delete('/v1/checks/{cid}')
    def delete_check(cid: str, request: Request):
        with service.transaction():
            service.db.execute('DELETE FROM product_check WHERE id=? AND owner=?', (cid,owner(request)))
        return {'deleted': True}

    @app.post('/v1/sandbox/worlds/{wid}/cases', status_code=201)
    def case(wid: str, body: CaseInput, request: Request):
        record = service.replay(wid, owner(request), body.review_id)
        packet = dict(id=secrets.token_hex(16), status='draft', synthetic=True, created_at=time.time(),
                      notice='Evidence draft only. Not submitted to a bank or government portal.', review=project(record))
        with service.transaction():
            service.db.execute('INSERT INTO product_case VALUES(?,?,?)',(packet['id'],wid,canonical(packet)))
        return packet

    @app.delete('/v1/sandbox/worlds/{wid}')
    def delete_world(wid: str, request: Request):
        with service.lock:
            service._world(wid, owner(request))
            with service.transaction():
                for table in ('product_pair','product_grant','product_case','product_label'):
                    service.db.execute(f'DELETE FROM {table} WHERE world=?',(wid,))
                service.db.execute('DELETE FROM product_idempotency WHERE owner=?',(owner(request),))
            return service.delete_world(wid, owner(request))

    @app.post('/v1/operator/worlds/{wid}/review')
    def independent_review(wid: str, body: CaseInput, request: Request, x_operator_key: str = Header(...)):
        expected = os.getenv('MAYA_OPERATOR_KEY', '')
        if len(expected) < 32 or not secrets.compare_digest(expected, x_operator_key):
            raise HTTPException(403, 'Independent operator credentials required')
        with service.lock:
            row = service.db.execute('SELECT owner FROM sim_world WHERE id=?',(wid,)).fetchone()
            if not row:
                raise HTTPException(404, 'Session not found')
            record = service.replay(wid,row[0],body.review_id)
        # Requesting review never short-circuits the enforced timer.
        return dict(status='reviewed', review=project(record), enforcement='Existing hold and expiry rules remain in force')

    @app.post('/v1/operator/worlds/{wid}/approve')
    def approve(wid: str, body: CaseInput, x_operator_key: str = Header(...)):
        expected = os.getenv('MAYA_OPERATOR_KEY', '')
        if len(expected) < 32 or not secrets.compare_digest(expected, x_operator_key):
            raise HTTPException(403, 'Independent operator credentials required')
        with service.transaction():
            row = service.db.execute('SELECT owner FROM sim_world WHERE id=?',(wid,)).fetchone()
            if not row:
                raise HTTPException(404, 'Session not found')
            state = service._world(wid, row[0])
            record = service.replay(wid, row[0], body.review_id)
            p = service._intent(record['payment']['id'], wid)
            service._valid_review(state,p,record)
            if not p.get('analyst_required') or p.get('hold_revision')!=p['revision'] or p['state']!='pending':
                raise HTTPException(409, 'No current independent-review case')
            p.update(analyst_approved=True,analyst_review=body.review_id,analyst_actor='independent-operator')
            service._save_intent(p)
            service._event(wid,'analyst_approved',p['id'],review_id=body.review_id)
        return dict(status='approved_for_reviewed_revision', payment_status='pending', timer_bypassed=False)

    @app.post('/v1/operator/worlds/{wid}/labels', status_code=201)
    def label(wid: str, body: LabelInput, x_operator_key: str = Header(...)):
        expected=os.getenv('MAYA_OPERATOR_KEY','')
        if len(expected)<32 or not secrets.compare_digest(expected,x_operator_key):
            raise HTTPException(403,'Independent operator credentials required')
        with service.transaction():
            row=service.db.execute('SELECT owner FROM sim_world WHERE id=?',(wid,)).fetchone()
            if not row:raise HTTPException(404,'Session not found')
            service._world(wid,row[0])
            record=service.replay(wid,row[0],body.review_id)
            if body.supersedes:
                old=service.db.execute('SELECT body FROM product_label WHERE id=? AND world=?',(body.supersedes,wid)).fetchone()
                if not old or json.loads(old[0])['review_id']!=body.review_id:
                    raise HTTPException(409,'Correction must reference the same reviewed operation')
            result=dict(id=secrets.token_hex(16),world=wid,review_id=body.review_id,classification=body.classification,
                        supersedes=body.supersedes,observed_at=time.time(),maturity_at=body.maturity_at,
                        authority='authenticated operator assertion; requires external adjudication for real-world ground truth',
                        model_version=record['versions']['model'],automatic_training=False)
            service.db.execute('INSERT INTO product_label VALUES(?,?,?)',(result['id'],wid,canonical(result)))
        return result

    @app.get('/v1/operator/queue')
    def operator_queue(x_operator_key: str = Header(...)):
        require_operator(x_operator_key)
        cases = []
        with service.lock:
            worlds = service.db.execute('SELECT id,owner FROM sim_world').fetchall()
            for row in worlds:
                wid, world_owner = row['id'], row['owner']
                intents = service.db.execute('SELECT body FROM sim_intent WHERE world=?', (wid,)).fetchall()
                for item in intents:
                    payment = json.loads(item[0])
                    if (payment.get('state') != 'pending' or payment.get('hold_revision') != payment.get('revision')
                            or not payment.get('analyst_required')):
                        continue
                    reviews = service.db.execute('SELECT body FROM sim_review WHERE world=? ORDER BY rowid DESC', (wid,)).fetchall()
                    record = next((json.loads(r[0]) for r in reviews
                                   if json.loads(r[0])['payment']['id'] == payment['id']
                                   and json.loads(r[0])['payment']['revision'] == payment['revision']), None)
                    if record:
                        cases.append(dict(world_id=wid, payment_id=payment['id'], revision=payment['revision'],
                                          review_id=record['id'], amount_paise=payment['amount_paise'],
                                          recipient=payment['recipient'], state=payment['state'],
                                          expires_at=record['expires_at'], reasons=record['decision']['reasons'],
                                          model_version=record['versions']['model'],
                                          policy_version=record['versions']['policy']))
        cases.sort(key=lambda c: c['expires_at'])
        return dict(cases=cases[:100], generated_at=time.time(), mode='synthetic sandbox analyst queue')

    @app.get('/v1/operator/audit')
    def operator_audit(x_operator_key: str = Header(...)):
        require_operator(x_operator_key)
        allowed = {'review_saved', 'analyst_approved', 'analyst_rejected', 'trusted_contact_alert',
                   'trusted_contact_response', 'settled', 'cancelled', 'review_failed'}
        events = []
        with service.lock:
            rows = service.db.execute('SELECT sequence,body FROM sim_event ORDER BY sequence DESC LIMIT 1000').fetchall()
        for row in rows:
            event = json.loads(row['body'])
            if event.get('stage') in allowed:
                events.append(dict(sequence=row['sequence'], **event))
                if len(events) >= 200:
                    break
        return dict(events=events, retention_days=max(1, int(os.getenv('MAYA_WORLD_RETENTION_DAYS', '7'))),
                    source='append-only synthetic sandbox events')

    @app.post('/v1/operator/decision')
    def operator_decision(body: OperatorDecisionInput, x_operator_key: str = Header(...)):
        require_operator(x_operator_key)
        with service.transaction():
            # The operation is addressed by review and payment IDs; resolve its world
            # without accepting an owner or world identifier from the operator UI.
            lookup = service.db.execute('SELECT world,body FROM sim_intent WHERE id=?', (body.payment_id,)).fetchone()
            if not lookup:
                raise HTTPException(404, 'Payment not found')
            wid = lookup['world']
            owner_row = service.db.execute('SELECT owner FROM sim_world WHERE id=?', (wid,)).fetchone()
            if not owner_row:
                raise HTTPException(404, 'Session not found')
            payment = json.loads(lookup['body'])
            if payment['revision'] != body.revision or payment['state'] != 'pending' or payment.get('hold_revision') != body.revision:
                raise HTTPException(409, 'This hold has changed; refresh the queue')
            record = service.replay(wid, owner_row['owner'], body.review_id)
            service._valid_review(service._world(wid, owner_row['owner']), payment, record)
            if record['payment']['id'] != body.payment_id or record['payment']['revision'] != body.revision:
                raise HTTPException(409, 'Review is stale for this payment revision')
            if body.decision == 'approve':
                if not payment.get('analyst_required'):
                    raise HTTPException(409, 'Analyst approval is reserved for held payments over INR 1 lakh')
                payment.update(analyst_approved=True, analyst_review=body.review_id,
                               analyst_actor='operator-console')
                service._save_intent(payment)
                service._event(wid, 'analyst_approved', body.payment_id, review_id=body.review_id,
                               revision=body.revision, actor='operator-console')
            else:
                payment['state'] = 'cancelled'
                service._save_intent(payment)
                service._event(wid, 'analyst_rejected', body.payment_id, review_id=body.review_id,
                               revision=body.revision, actor='operator-console')
        return dict(status='recorded', decision=body.decision, payment_state=payment['state'],
                    hold_timer_bypassed=False, payment_control=True)

    @app.post('/v1/partner/score')
    def partner_score(request: Request, payload: dict, x_api_key: str = Header(...)):
        expected = os.getenv('MAYA_PARTNER_KEY', '')
        if len(expected) < 32 or not secrets.compare_digest(expected, x_api_key):
            raise HTTPException(403, 'Authorized partner credentials required')
        from api import ScoreRequest
        from pydantic import ValidationError
        try:
            req = ScoreRequest.model_validate(payload)
        except ValidationError:
            raise HTTPException(422, 'Invalid feature contract')
        required=[base+side for base in ('n_t','g_t','pi_t','d_R','v_t') for side in ('','_snd','_rcv')]
        if any(req.features[k] is None for k in required):
            raise HTTPException(503,'Required behavioral observations are unavailable; no approval advice produced')
        from policy import decide
        from online_features import numeric
        started=time.perf_counter()
        # The wallet model was trained on a different generated source. It must
        # never silently score partner traffic as if it had been validated there.
        if partner_model is None:
            raise HTTPException(503, 'Partner route requires an independently validated partner model bundle; sandbox weights are not eligible')
        if not slots.acquire(blocking=False):
            raise HTTPException(503,'Review capacity reached',headers={'Retry-After':'1'})
        try:
            result=partner_model.score(numeric(req.features))
            from reasons import risk_reasons
            rows=[(r['feature'],r['value'],r['label']) for r in result['contributions']]
            reasons=risk_reasons(rows,numeric(req.features))
            decision=decide(result['uncertainty'],numeric(req.features),req.soft_signals.model_dump(),reasons,req.amount_inr,
                            mulehunter_status=req.mulehunter_status)
            return dict(**decision,model=result,latency_ms=(time.perf_counter()-started)*1000,
                        model_version=partner_model.version,source=os.getenv('MAYA_PARTNER_SOURCE'),mode='shadow-advice-only')
        finally:
            slots.release()

    frontend = ROOT / 'frontend'
    app.mount('/app', StaticFiles(directory=frontend/'product', html=True), name='customer')
    app.mount('/demo', StaticFiles(directory=frontend/'observer', html=True), name='judge')
    app.mount('/recipient', StaticFiles(directory=frontend/'observer', html=True), name='recipient')
    app.mount('/contact', StaticFiles(directory=frontend/'observer', html=True), name='contact')
    app.mount('/operator', StaticFiles(directory=frontend/'operator', html=True), name='operator')
    app.mount('/static', StaticFiles(directory=frontend/'shared'), name='shared')
    app.mount('/product-static', StaticFiles(directory=frontend/'product'), name='product-assets')

    @app.get('/')
    def root():
        return RedirectResponse('/app/')

    return app
