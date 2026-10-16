"""Accept hosts that normalize the advertised MCP URL by dropping its slash."""


class MCPPathAlias:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and scope['path'] == '/mcp':
            # Internal routing only. Keep POST/body/headers/query untouched;
            # the same mounted SDK owns admission, security and transport.
            scope = {**scope, 'path': '/mcp/',
                     'raw_path': scope.get('raw_path', b'/mcp') + b'/'}
        await self.app(scope, receive, send)
