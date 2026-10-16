"""Conservative tool-list metadata for hosts with limited schema translators.

The SDK keeps the full registered schemas for validation and structured tool
results. Only discovery is projected; the canonical recipe is a separate tool
and resource. No transport or generation behavior is changed here.
"""
from mcp.server import MCPServer


def compact_schema(schema, root=None, trail=()):
    """Inline local references and project unions to ordinary optional fields.

    This intentionally documents a simpler input shape than the canonical
    contract. Omit optional/null fields; cross-field rules stay in the engine.
    Coordinate alternatives become optional lat/lon/x/y properties, with exact
    pair validation still performed by Recipe. Defaults are never expanded.
    """
    root = schema if root is None else root
    if '$ref' in schema:
        ref = schema['$ref']
        if not ref.startswith('#/') or ref in trail:
            raise ValueError('MCP discovery requires finite local schema references.')
        target = root
        for part in ref[2:].split('/'):
            target = target[part.replace('~1', '/').replace('~0', '~')]
        return compact_schema({**target, **{k:v for k,v in schema.items() if k != '$ref'}},
                              root, (*trail, ref))
    result = {}
    alternatives = schema.get('anyOf', schema.get('oneOf', []))
    choices = [compact_schema(s, root, trail) for s in alternatives if s.get('type') != 'null']
    if len(choices) == 1:
        result.update(choices[0])
    elif choices:
        types = {s.get('type') for s in choices}
        if types == {'object'}:
            result = {'type':'object', 'properties':{k:v for s in choices for k,v in s.get('properties', {}).items()}}
        elif types <= {'number', 'integer'}:
            result['type'] = 'number'
        # Mixed/unknown shapes are left open and validated by the engine.
    kind = schema.get('type')
    if isinstance(kind, list):
        kind = next((t for t in kind if t != 'null'), None)
    if kind and kind != 'null':
        result['type'] = kind
    if 'enum' in schema:
        values = [v for v in schema['enum'] if v is not None]
        if values:
            result['enum'] = values
            if 'type' not in result:
                if all(isinstance(v,str) for v in values):result['type'] = 'string'
    for key in ('minimum','maximum','minLength','maxLength','minItems','maxItems'):
        if key in schema:result[key] = schema[key]
    if schema.get('description'):
        desc = ' '.join(schema['description'].split())
        result['description'] = desc if len(desc) <= 160 else desc[:157].rsplit(' ',1)[0] + '…'
    if 'properties' in schema:
        result['properties'] = {k:compact_schema(v, root, trail) for k,v in schema['properties'].items()}
    if schema.get('required'):
        result['required'] = list(schema['required'])
    if 'items' in schema:
        result['items'] = compact_schema(schema['items'], root, trail)
    if 'additionalProperties' in schema:
        value = schema['additionalProperties']
        result['additionalProperties'] = compact_schema(value, root, trail) if isinstance(value,dict) else value
    return result


class DiscoveryMCPServer(MCPServer):
    """Use the SDK's public discovery hook; leave tool execution untouched."""

    async def list_tools(self):
        tools = await super().list_tools()
        from .mcp_diagnostics import trace
        request = trace.get()
        if request is not None:
            request['tools'] = len(tools)
        return [tool.model_copy(update={
            'input_schema': compact_schema(tool.input_schema),
            'output_schema': None,
            'description': (tool.description or '').split('\n\n', 1)[0].strip(),
        }) for tool in tools]
