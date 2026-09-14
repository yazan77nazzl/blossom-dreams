with open(r'C:\Users\Admin\Desktop\blossom-dreams-lb\.env', 'rb') as f:
    data = f.read()
lines = data.split(b'\n')
for line in lines:
    if b'SUPABASE_URL' in line:
        print('Line bytes:', line)
        print('Hex:', line.hex())
        print('Length:', len(line))
        if line.endswith(b'\r'):
            print('WARNING: Line ends with \\r')
        parts = line.split(b'=', 1)
        if len(parts) == 2:
            val = parts[1].strip()
            print('Value bytes:', val)
            print('Value repr:', repr(val))
            print('Has http:', b'http' in val)