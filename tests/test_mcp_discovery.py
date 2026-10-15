"""A host must be able to ingest discovery without understanding full schemas."""
import json

import anyio
from fastapi.testclient import TestClient
from mcp import Client
from mcp.server import MCPServer
import pytest

from server.app import app
from server.mcp_server import mcp
from server.mcp_discovery import compact_schema
from server.recipe_contract import recipe_json_schema

FORBIDDEN = {'$ref','$defs','anyOf','oneOf','allOf','if','then','else','outputSchema'}


def keys(value):
    if isinstance(value,dict):
        yield from value
        for v in value.values():yield from keys(v)
    elif isinstance(value,list):
        for v in value:yield from keys(v)


def test_wire_tool_list_is_compact_and_has_no_output_schemas_or_compositions():
    with TestClient(app) as c:
        response = c.post('/mcp/',json={'jsonrpc':'2.0','id':1,'method':'tools/list','params':{}},
                          headers={'Host':'127.0.0.1','Accept':'application/json, text/event-stream'})
    assert response.status_code == 200,response.text
    assert not FORBIDDEN.intersection(keys(response.json()))
    assert len(response.content) < 16000
    tools=response.json()['result']['tools']
    assert len(tools)==6
    for tool in tools:
        assert tool['inputSchema']['type']=='object'
        if tool['name'].endswith(('validate_recipe','generate_mission')):
            props=tool['inputSchema']['properties']['params']['properties']['recipe']['properties']
            assert {'start_position','mission_date','start_altitude','player_slot','map_view'} <= props.keys()
            assert props['start_altitude']['type']=='number'
            assert props['mission_date']['type']=='string'
            assert props['player_slot']['enum']==['player','client']


def test_discovery_projection_does_not_change_registered_schemas_or_structured_results():
    async def run():
        before=[t.model_dump() for t in await MCPServer.list_tools(mcp)]
        listed=await mcp.list_tools()
        after=[t.model_dump() for t in await MCPServer.list_tools(mcp)]
        assert before==after
        assert all(t['output_schema'] for t in before)
        assert all(t.output_schema is None for t in listed)
        async with Client(mcp) as c:
            result=await c.call_tool('sortiestarter_list_catalog',{'params':{'kind':'maps','limit':1}})
            assert not result.is_error and result.structured_content['items']
            assert json.loads(result.content[0].text)==result.structured_content
            canonical=await c.call_tool('sortiestarter_get_recipe_schema')
            assert canonical.structured_content==recipe_json_schema()
            assert 'allOf' in canonical.structured_content
    anyio.run(run)


def test_projection_inlines_references_and_retains_required_fields():
    original={'type':'object','$defs':{'Choice':{'type':'string','enum':['a','b']}},
              'properties':{'choice':{'anyOf':[{'$ref':'#/$defs/Choice'},{'type':'null'}]}},
              'required':['choice']}
    result=compact_schema(original)
    assert result=={'type':'object','properties':{'choice':{'type':'string','enum':['a','b']}},'required':['choice']}
    assert '$defs' in original


def test_coordinate_alternatives_remain_visible_and_recursive_refs_fail_closed():
    result=compact_schema(recipe_json_schema())
    assert {'lat','lon','x','y'}==set(result['properties']['start_position']['properties'])
    assert not FORBIDDEN.intersection(keys(result))
    with pytest.raises(ValueError,match='finite local'):
        compact_schema({'$ref':'https://untrusted.example/schema'})
    with pytest.raises(ValueError,match='finite local'):
        compact_schema({'$ref':'#/$defs/cycle','$defs':{'cycle':{'$ref':'#/$defs/cycle'}}})


@pytest.mark.parametrize('recipe,part',[
    ({'start_position':{'lat':42},'start':'air'},'start_position'),
    ({'player_slot':'player','slots':4},'player_slot'),
    ({'slots':4,'veteran_wingmen':4},'veteran_wingmen'),
    ({'exact_stores':{'1':'invented'}},'Unknown recipe'),
    ({'radio_channels':{'1':251}},'Unknown recipe'),
])
def test_simple_discovery_does_not_weaken_runtime_validation(recipe,part):
    async def run():
        async with Client(mcp) as c:
            result=await c.call_tool('sortiestarter_validate_recipe',{'params':{'recipe':recipe}})
            assert result.is_error
            assert part in result.content[0].text
    anyio.run(run)


def test_existing_normalized_null_values_remain_accepted_by_runtime():
    from missiongen import Recipe
    async def run():
        async with Client(mcp) as c:
            result=await c.call_tool('sortiestarter_validate_recipe', {'params':{'recipe':Recipe(era='modern').to_dict()}})
            assert not result.is_error,result.content
            assert result.structured_content['recipe']['map_view'] is None
    anyio.run(run)
