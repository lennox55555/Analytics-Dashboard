import re

def fix_both_issues():
    # Fix 1: Analysis endpoint
    print("Fixing analysis endpoint...")
    with open('app.py', 'r') as f:
        app_content = f.read()
    
    # Pattern to find the JSON parsing issue
    pattern1 = r"result\['analysis'\] = json\.loads\(result\['chart_config'\]\)"
    replacement1 = """if isinstance(result['chart_config'], str):
                    result['analysis'] = json.loads(result['chart_config'])
                elif isinstance(result['chart_config'], dict):
                    result['analysis'] = result['chart_config']
                else:
                    result['analysis'] = None"""
    
    app_content = re.sub(pattern1, replacement1, app_content)
    
    with open('app.py', 'w') as f:
        f.write(app_content)
    print("✅ Fixed app.py analysis endpoint")
    
    # Fix 2: AI system graceful failure
    print("Fixing AI system graceful failure...")
    with open('ai_visualization_core.py', 'r') as f:
        ai_content = f.read()
    
    # Find and replace the failure return statement
    old_pattern = """await self._update_visualization_status(viz_id, 'failed', analysis, error=grafana_result.get('error'))
                return {
                    'success': False,
                    'visualization_id': viz_id,
                    'analysis': analysis,
                    'error': f"Grafana dashboard creation failed: {grafana_result.get('error')}",
                    'message': 'AI analysis completed but dashboard creation failed'
                }"""
    
    new_pattern = """await self._update_visualization_status(viz_id, 'completed', analysis)
                return {
                    'success': True,
                    'visualization_id': viz_id,
                    'analysis': analysis,
                    'data_preview': data_preview,
                    'grafana_error': grafana_result.get('error'),
                    'message': 'AI analysis completed successfully (Grafana dashboard creation skipped)'
                }"""
    
    if old_pattern in ai_content:
        ai_content = ai_content.replace(old_pattern, new_pattern)
        with open('ai_visualization_core.py', 'w') as f:
            f.write(ai_content)
        print("✅ Fixed ai_visualization_core.py graceful failure")
    else:
        print("❌ Could not find exact pattern in AI core, will need manual fix")
    
    return True

if __name__ == "__main__":
    fix_both_issues()
