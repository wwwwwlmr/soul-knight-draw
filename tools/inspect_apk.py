import zipfile, struct, os, sys

path = sys.argv[1]
z = zipfile.ZipFile(path)
print('entries:', len(z.infolist()))
bad = z.testzip()
print('testzip (None=ok):', bad)

# 对比本地文件头与中央目录
with open(path, 'rb') as f:
    data = f.read()
problems = 0
for info in z.infolist():
    off = info.header_offset
    sig, ver, flags, method, mtime, mdate, crc, csize, usize, nlen, elen = struct.unpack('<IHHHHHIIIHH', data[off:off+30])
    name = data[off+30:off+30+nlen].decode('utf-8', 'replace')
    if sig != 0x04034b50:
        print('BAD SIG', info.filename); problems += 1; continue
    if name != info.filename:
        print('NAME MISMATCH', info.filename, name); problems += 1
    if flags & 0x08:
        # 数据描述符：本地头里 size/crc 为 0 是正常的
        if not (crc == 0 and csize == 0 and usize == 0):
            print('FLAG8 but sizes set', info.filename, crc, csize, usize); problems += 1
    else:
        if (crc, csize, usize) != (info.CRC, info.compress_size, info.file_size):
            print('SIZE MISMATCH', info.filename, (crc, csize, usize), (info.CRC, info.compress_size, info.file_size)); problems += 1
print('local/central mismatches:', problems)

print('\nfirst 8 entries:')
for i in z.infolist()[:8]:
    print('  ', i.filename, 'method=', i.compress_type, 'size=', i.file_size, 'hdr=', i.header_offset)
print('\nlast 5 entries:')
for i in z.infolist()[-5:]:
    print('  ', i.filename, 'method=', i.compress_type, 'size=', i.file_size, 'hdr=', i.header_offset)
names = [i.filename for i in z.infolist()]
for must in ('AndroidManifest.xml', 'classes.dex', 'resources.arsc', 'assets/index.html'):
    print(must, 'present:', must in names)
print('assets count:', sum(1 for n in names if n.startswith('assets/')))
print('apk size MB: %.2f' % (os.path.getsize(path) / 1048576))
