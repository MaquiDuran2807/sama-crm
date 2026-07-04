with open('crm/static/crm/js/analytics.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Find what precedes renderSourceMixChart
pos = content.find('function renderSourceMixChart')
# Show 500 chars before it
segment = content[pos-500:pos]
print(repr(segment[-200:]))