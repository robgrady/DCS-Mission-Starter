"""Bounded transport evidence, separate from completed mission analytics.

Never persist bodies, recipes, header values, client names, addresses or tokens.
Only fixed classifications, server-generated IDs and response facts are kept.
"""
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
import json
import logging
import os
import secrets
import threading

import anyio

from missiongen import __version__, analytics

trace = ContextVar('mcp_diagnostic_trace', default=None)
_lock = threading.Lock()
log = logging.getLogger('missionstarter.mcp.transport')
LIMIT = 200
MAX_AGE_DAYS = 7
METHODS = {'initialize', 'notifications/initialized', 'tools/list', 'tools/call',
           'resources/list', 'resources/read', 'resources/templates/list',
           'prompts/list', 'prompts/get', 'ping'}


def recent():
    """Read only our bounded ring; missing/unwritable diagnostics never stop MCP."""
    try:
        path = analytics.DATA_DIR / 'mcp-connections.json'
        if path.stat().st_size > 256_000:
            return []
        rows = json.loads(path.read_text())
        cutoff = (datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)).isoformat()
        return [r for r in rows if isinstance(r, dict) and r.get('ts', '') >= cutoff][-LIMIT:]
    except (OSError, ValueError, TypeError):
        return []


def record(row):
    try:
        with _lock:
            analytics.DATA_DIR.mkdir(parents=True, exist_ok=True)
            path = analytics.DATA_DIR / 'mcp-connections.json'
            pending = path.with_suffix('.tmp')
            pending.write_text(json.dumps([*recent(), row][-LIMIT:], separators=(',', ':')))
            os.replace(pending, path)
    except OSError:
        log.warning('MCP connection diagnostics unavailable')


class MCPDiagnostics:
    """Observe ASGI messages without pre-reading, replaying or replacing bodies.

    Install inside Fly owner routing so replica replay is not a server success.
    Capture at most 4 KiB per direction in memory to classify small RPC messages;
    SDK body/security limits still own request admission and responses.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['path'].rstrip('/') != '/mcp':
            return await self.app(scope, receive, send)
        headers = dict(scope.get('headers', []))
        accept = headers.get(b'accept', b'').lower()
        row = {'ts': datetime.now(timezone.utc).isoformat(), 'id': secrets.token_hex(8),
               'version': __version__, 'http': scope['method'] if scope['method'] in ('GET', 'POST', 'DELETE', 'OPTIONS') else 'other',
               'path': '/mcp/' if scope['path'].endswith('/') else '/mcp',
               'rpc': 'unread', 'status': None, 'bytes': 0, 'tools': None,
               'accept_json': b'application/json' in accept,
               'accept_sse': b'text/event-stream' in accept,
               'origin_present': b'origin' in headers,
               'protocol_present': b'mcp-protocol-version' in headers,
               'session_present': b'mcp-session-id' in headers,
               'response': 'other', 'rpc_error': None}
        incoming = bytearray()
        outgoing = bytearray()
        request_bytes = 0
        token = trace.set(row)

        async def observed_receive():
            nonlocal request_bytes
            message = await receive()
            if message['type'] == 'http.request':
                body = message.get('body', b'')
                request_bytes += len(body)
                incoming.extend(body[:max(0, 4096-len(incoming))])
            return message

        async def observed_send(message):
            if message['type'] == 'http.response.start':
                row['status'] = message['status']
                content_type = dict(message.get('headers', [])).get(b'content-type', b'')
                row['response'] = ('json' if b'application/json' in content_type
                                   else 'sse' if b'text/event-stream' in content_type else 'other')
                message = {**message, 'headers': [*message.get('headers', []),
                           (b'x-sortie-request-id', row['id'].encode()),
                           (b'x-sortie-version', __version__.encode())]}
            elif message['type'] == 'http.response.body':
                body = message.get('body', b'')
                row['bytes'] += len(body)
                outgoing.extend(body[:max(0, 4096-len(outgoing))])
            await send(message)

        try:
            await self.app(scope, observed_receive, observed_send)
        finally:
            trace.reset(token)
            if request_bytes and request_bytes <= 4096:
                try:
                    request = json.loads(incoming)
                    method = request.get('method') if isinstance(request, dict) else None
                    row['rpc'] = method if method in METHODS else 'other'
                except (ValueError, TypeError):
                    row['rpc'] = 'invalid_json'
            elif request_bytes:
                row['rpc'] = 'large_request'
            if row['response'] == 'json' and row['bytes'] <= 4096:
                try:
                    response = json.loads(outgoing)
                    row['rpc_error'] = isinstance(response, dict) and 'error' in response
                except (ValueError, TypeError):
                    pass
            # Emit after the response, off the event loop, without storing secrets.
            with anyio.CancelScope(shield=True):
                await anyio.to_thread.run_sync(record, row)


def admin_card():
    import html
    rows = recent()
    cells = ('ts', 'id', 'version', 'rpc', 'status', 'bytes', 'tools', 'response')
    body = ''.join('<tr>' + ''.join('<td>' + html.escape(str(r.get(k, ''))) + '</td>' for k in cells) + '</tr>'
                   for r in reversed(rows[-30:])) or '<tr><td colspan=8>No requests recorded.</td></tr>'
    return ('<div class=card><h2>MCP connection diagnostics</h2>'
            '<p class=note>Last 30 requests · up to 200 retained for 7 days. UTC times and '
            'X-Sortie-Request-ID match the response headers. HTTP 200 and six tools establish '
            'server discovery, not app acceptance. No request/client identity, bodies or credentials '
            'are stored. Header flags below report presence only. Tracking begins with v1.121.0.</p>'
            '<div style="overflow-x:auto"><table class=stats><tr>'
            '<th>UTC</th><th>Request ID</th><th>Release</th><th>RPC</th><th>HTTP</th>'
            '<th>Bytes</th><th>Tools</th><th>Reply</th></tr>' + body + '</table></div>'
            '<details><summary>Header compatibility flags</summary><pre>' +
            html.escape(json.dumps([{k:r.get(k) for k in ('id', 'http', 'path', 'accept_json',
                'accept_sse', 'origin_present', 'protocol_present', 'session_present', 'rpc_error')}
                for r in reversed(rows[-30:])], indent=2)) + '</pre></details></div>')
