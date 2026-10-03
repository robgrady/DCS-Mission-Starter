"""Route public catalog reads and writes to one Fly volume owner.

Other machines retain their private stores and generation capacity. A missing
owner stays unavailable rather than accepting writes into a divergent catalog.
Local/self-hosted installations need no configuration.
"""
import os
from fastapi.responses import Response


def owns_catalog_path(path):
    return (path in ('/api/options', '/api/mission-kit') or path == '/mcp' or path.startswith('/mcp/') or path.startswith('/api/pack/')
            or path.startswith('/api/track/') or path.startswith('/admin/packs'))


def replay_target(path, owner, current):
    if owner and current and owner != current and owns_catalog_path(path):
        return owner
    return None


def install(app):
    @app.middleware('http')
    async def catalog_owner(request, call_next):
        target = replay_target(request.url.path, os.environ.get('PACKS_OWNER_MACHINE'),
                               os.environ.get('FLY_MACHINE_ID'))
        if target:
            if int(request.headers.get('content-length', '0')) > 1_000_000:
                from fastapi.responses import JSONResponse
                return JSONResponse({'detail':'Reload the pack upload page and try again.'},
                                    status_code=503, headers={'Retry-After':'3'})
            return Response(status_code=200, headers={'fly-replay': 'instance=' + target,
                                                      'Cache-Control': 'no-store'})
        return await call_next(request)
