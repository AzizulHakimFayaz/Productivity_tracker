import os

for root, _, files in os.walk('ui'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            if '# Reset QLabel border' in content:
                continue

            if 'QFrame {' in content:
                print(f'Fixing {path}...')
                parts = content.split('\"\"\"')
                new_parts = []
                for p in parts:
                    if 'QFrame {' in p and 'background-color:' in p:
                        idx = p.rfind('}}')
                        if idx != -1:
                            new_p = p[:idx] + '}}\n            /* # Reset QLabel border */\n            QLabel {{\n                border: none;\n                background: transparent;\n            }}' + p[idx+2:]
                            new_parts.append(new_p)
                            continue

                    new_parts.append(p)

                new_content = '\"\"\"'.join(new_parts)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
