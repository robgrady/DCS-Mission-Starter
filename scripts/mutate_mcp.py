"""Prove MCP integration guards against realistic faults; restore every source."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
CASES = [
 ('server/mcp_discovery.py', "'output_schema': None", "'output_schema': tool.output_schema",
  'wire_tool_list', 'compact discovery leaks output schemas'),
 ('server/mcp_discovery.py', "'input_schema': compact_schema(tool.input_schema)", "'input_schema': tool.input_schema",
  'wire_tool_list', 'compact discovery leaks schema compositions'),
 ('server/mcp_server.py', 'return Recipe.from_dict(values)', 'return Recipe.from_dict(values, validate=False)',
  'simple_discovery_does_not_weaken', 'compact discovery bypasses runtime recipe validation'),
 ('server/app.py', '    app.state.mcp_mount.app = transport', '    mcp_mount.app = transport',
  'original_app_transport', 'module reload attaches transport to another application'),
 ('server/document_routes.py', "@router.get('/api/mcp-guide')", "@router.get('/api/mcp-guide-missing')",
  'public_agent_docs', 'public agent guide unavailable'),
 ('server/mcp_server.py', "@mcp.resource('sortiestarter://integration-guide'", "@mcp.resource('sortiestarter://integration-guide-missing'",
  'sdk_discovers', 'agent guide resource unavailable'),
 ('scripts/capture_screenshots.py', "    page.wait_for_function('OPT !== null && NAV_READY', timeout=30000)\n", '',
  'manual_capture_waits', 'manual screenshots race initial navigation'),
 ('server/mcp_server.py', '@mcp.tool(annotations=READ, structured_output=True)\ndef sortiestarter_list_catalog',
  '@mcp.tool(annotations=READ, structured_output=False)\ndef sortiestarter_list_catalog', 'sdk_discovers', 'structured results disappear'),
 ('server/mcp_server.py', 'page = items[params.offset:params.offset + params.limit]',
  'page = items', 'catalog_pagination', 'pagination ignores bounds'),
 ('server/mission_kit.py', 'artifact_service.generate(recipe, str(miz), brief_dir=str(directory))',
  'artifact_service._engine_generate(recipe, str(miz), brief_dir=str(directory))', 'share_website_generation_capacity', 'build bypasses admission'),
 ('server/mission_kit.py', "hashlib.sha256(miz.read_bytes()).hexdigest()", "'0' * 64",
  'kit_manifest_comm', 'native checksum is invented'),
 ('server/mission_kit.py', "if sha256 and result['manifest']['mission']['sha256'] != sha256:", 'if False:',
  'http_download_cleanup', 'native checksum mismatch accepted'),
 ('server/mcp_server.py', 'max_request_body_size=1_000_000', 'max_request_body_size=2_000_000',
  'http_transport_blocks', 'oversized and chunked MCP bodies accepted'),
 ('server/mission_kit.py', 'if version != __version__:', 'if False:',
  'http_download_cleanup', 'old download links silently rebuild'),
 ('server/mission_kit.py', "if name.startswith('KNEEBOARD/IMAGES/') and name.lower().endswith('.png'):", 'if False:',
  'kit_manifest_comm', 'kneeboard pages silently omitted'),
 ('missiongen/artifacts.py', '"frequency_mhz": f,', '"frequency_mhz": "305.725",',
  'custom_comm_sidecar', 'sidecar ignores squadron override'),
 ('server/mission_kit.py', 'background=BackgroundTask(shutil.rmtree, directory, ignore_errors=True)',
  'background=BackgroundTask(lambda: None)', 'http_download_cleanup', 'download files leak'),
 ('server/mission_kit.py', "        with tempfile.TemporaryDirectory(prefix='sortie-mcp-') as directory:",
  "        from contextlib import nullcontext\n        with nullcontext(tempfile.mkdtemp(prefix='sortie-mcp-')) as directory:",
  'build_failure_and_success', 'preview failure leaks files'),
 ('server/mcp_server.py', 'return TransportSecuritySettings(allowed_hosts=',
  'return TransportSecuritySettings(enable_dns_rebinding_protection=False, allowed_hosts=',
  'http_transport_blocks', 'untrusted origins and hosts accepted'),
 ('server/catalog_owner.py', "path == '/mcp' or path.startswith('/mcp/')", 'False',
  'catalog_owner_routes_mcp', 'MCP reads divergent replica catalog'),
 ('server/mcp_server.py', 'anyio.to_thread.run_sync(generation_preview, recipe)',
  'anyio.to_thread.run_sync(generation_preview, recipe, abandon_on_cancel=True)',
  'cancelled_tool_keeps_capacity', 'cancelled request abandons native cleanup'),
 ('server/app.py', 'async with mcp_server.mcp.session_manager.run():', 'if True:',
  'real_http_sdk_client_session', 'mounted transport never starts'),
 ('server/mission_kit.py', "analytics.record('mcp_build', 'mcp', recipe)",
  "analytics.record('generate', 'mcp', recipe)", 'success_counts_once', 'MCP builds disappear from admin counts'),
 ('server/mission_kit.py', "analytics.record('mcp_download', 'mcp', recipe)",
  "analytics.record('mcp_build', 'mcp', recipe)", 'success_counts_once', 'downloads inflate completed mission builds'),
 ('server/mission_kit.py', "analytics.record('mcp_busy' if exc.status_code == 503 else 'mcp_error', 'mcp', recipe)",
  "analytics.record('mcp_build', 'mcp', recipe)", 'failed_and_busy_native', 'busy generation counts as success'),
 ('server/catalog_owner.py', "'/api/mission-kit', '/admin/analytics'", "'/api/mission-kit'",
  'admin_analytics_and_mcp_share', 'admin reads the wrong analytics volume'),
 ('server/mcp_server.py', 'hosts.append(parsed.netloc)', 'pass',
  'explicit_canonical_and_fly', 'configured custom domains cannot discover tools'),
 ('missiongen/analytics.py', '            share_dls += 1\n        if e.get("kind") != "generate" or e.get("source") == "mcp":',
  '            share_dls += 1\n        if e.get("kind") not in ("generate", "mcp_build"):',
  'mcp_metrics_respect_window', 'bot traffic inflates website metrics'),
]


def run(selector):
    return subprocess.run([sys.executable, '-m', 'pytest', 'tests/test_mcp.py', 'tests/test_mcp_discovery.py', 'tests/test_mcp_analytics.py', 'tests/test_refactor_browser.py', '-q', '-x', '-k', selector],
                          cwd=ROOT, capture_output=True, text=True)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', action='append', help='Run only cases whose label contains this text; repeatable.')
    args = parser.parse_args()
    cases = [case for case in CASES if not args.label or any(s in case[-1] for s in args.label)]
    if not cases:
        raise SystemExit('No mutation labels matched.')
    selection = ' or '.join(sorted({case[3] for case in cases})) if args.label else 'not historical and not offline and not carrier_restore and not library_has_no_static'
    baseline = run(selection)
    if baseline.returncode:
        raise SystemExit('Baseline failed:\n' + baseline.stdout + baseline.stderr)
    originals = {path: (ROOT/path).read_text() for path, *_ in cases}
    prior_dirs = set(Path(tempfile.gettempdir()).glob('sortie-*'))
    try:
        for path, anchor, replacement, selector, label in cases:
            original = originals[path]
            assert original.count(anchor) == 1, (path, anchor)
            (ROOT/path).write_text(original.replace(anchor, replacement))
            try:
                result = run(selector)
                if result.returncode != 1:
                    raise SystemExit(f'WEAK or invalid run: {label}\n{result.stdout}\n{result.stderr}')
                print('caught:', label, flush=True)
            finally:
                (ROOT/path).write_text(original)
    finally:
        for path, original in originals.items():
            (ROOT/path).write_text(original)
        # Only clean newly leaked harness directories, never pre-existing ones.
        for path in set(Path(tempfile.gettempdir()).glob('sortie-*')) - prior_dirs:
            if path.is_dir():shutil.rmtree(path)
    restored = run(selection)
    if restored.returncode:
        raise SystemExit('Restored baseline failed:\n' + restored.stdout + restored.stderr)
    print(f'{len(cases)} caught; 0 weak; baseline restored and rechecked.')


if __name__ == '__main__':main()
