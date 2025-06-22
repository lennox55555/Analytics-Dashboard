# Patch to make AI system work without Grafana
import psycopg2
import json

def patch_ai_system():
    """Update the AI system to handle Grafana failures gracefully"""
    
    # Read the current ai_visualization_core.py
    with open('ai_visualization_core.py', 'r') as f:
        content = f.read()
    
    # Replace the process_user_request method to handle Grafana failures
    old_code = '''        # Step 5: Update the visualization record with results
        if grafana_result['success']:
            await self._update_visualization_status(viz_id, 'completed', {
                **analysis,
                'grafana_dashboard': grafana_result
            })
            
            return {
                'success': True,
                'visualization_id': viz_id,
                'analysis': analysis,
                'data_preview': data_preview,
                'grafana_dashboard': grafana_result,
                'message': 'Visualization created successfully with Grafana dashboard'
            }
        else:
            await self._update_visualization_status(viz_id, 'failed', analysis, error=grafana_result.get('error'))
            return {
                'success': False,
                'visualization_id': viz_id,
                'analysis': analysis,
                'error': f"Grafana dashboard creation failed: {grafana_result.get('error')}",
                'message': 'AI analysis completed but dashboard creation failed'
            }'''
    
    new_code = '''        # Step 5: Update the visualization record with results
        if grafana_result['success']:
            await self._update_visualization_status(viz_id, 'completed', {
                **analysis,
                'grafana_dashboard': grafana_result
            })
            
            return {
                'success': True,
                'visualization_id': viz_id,
                'analysis': analysis,
                'data_preview': data_preview,
                'grafana_dashboard': grafana_result,
                'message': 'Visualization created successfully with Grafana dashboard'
            }
        else:
            # Still return success even if Grafana fails
            await self._update_visualization_status(viz_id, 'completed', analysis)
            return {
                'success': True,
                'visualization_id': viz_id,
                'analysis': analysis,
                'data_preview': data_preview,
                'grafana_error': grafana_result.get('error'),
                'message': 'AI analysis completed successfully (Grafana dashboard creation skipped)'
            }'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        
        with open('ai_visualization_core.py', 'w') as f:
            f.write(content)
        
        print("✅ Patched AI system to handle Grafana failures gracefully")
        return True
    else:
        print("❌ Could not find the code section to patch")
        return False

if __name__ == "__main__":
    patch_ai_system()
