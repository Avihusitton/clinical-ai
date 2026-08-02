import sys

filename = 'C:\\Avihusitton\\clinical_ai\\local_qa_app.py'
try:
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    start_idx = -1
    for i, line in enumerate(lines):
        if line.startswith('def _render_legacy_app_html'):
            start_idx = i
            break
            
    if start_idx != -1:
        # Find next 'def ' at col 0
        end_idx = -1
        for i in range(start_idx + 1, len(lines)):
            if lines[i].startswith('def '):
                end_idx = i
                break
                
        if end_idx != -1:
            # We want to remove lines from start_idx up to end_idx. Wait, the prompt says:
            # "The blank line before def _render_legacy_app_html and the blank lines after the closing triple-quote"
            # Actually, "Remove all lines from the legacy function start up to (but NOT including) the next def"
            # Let's adjust start_idx to include the blank line if it exists.
            if start_idx > 0 and lines[start_idx - 1].strip() == '':
                start_idx -= 1
                
            new_lines = lines[:start_idx] + lines[end_idx:]
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print(f'Successfully removed lines {start_idx} to {end_idx - 1} from {filename}')
        else:
            print('Could not find end of function')
    else:
        print('Could not find start of function')
except Exception as e:
    print(f'Error: {e}')
