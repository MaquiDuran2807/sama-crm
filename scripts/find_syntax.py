with open('crm/static/crm/js/analytics.js', 'r') as f:
    content = f.read()

# Find the renderFunnelChart function and its end
start = content.find('function renderFunnelChart(funnelData, kpiTargets)')
end = content.find('\n    function renderSourceMixChart')
print(f"Found renderFunnelChart at: {start}")
print(f"Found renderSourceMixChart at: {end}")
if start > 0 and end > 0:
    print(f"Length of function: {end - start}")
    print(f"First 100 chars: {repr(content[start:start+200])}")
    print(f"Around end: {repr(content[end-100:end+50])}")