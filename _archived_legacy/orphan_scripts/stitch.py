import re

html_part = open('C:/Avihusitton/clinical_ai/recovered_lines.py', encoding='utf-8').read()
js_part = open('C:/Avihusitton/clinical_ai/scratch.js', encoding='utf-8').read()

# recovered_lines ends exactly at line 750.
# We need to make sure the transition from HTML to JS is smooth.
# Let's inspect the end of HTML and start of JS.

with open('C:/Avihusitton/clinical_ai/clinical_workspace_ui_fixed.py', 'w', encoding='utf-8') as out:
    out.write(html_part)
    if not html_part.strip().endswith('<script>'):
        out.write('\n<script>\n')
    out.write(js_part)
    out.write('\n</script>\n</body>\n</html>\n"""\n')
