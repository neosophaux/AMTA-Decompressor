import os
import lzo
import sys
import struct

try:
    fs_input = sys.argv[1]
except IndexError:
    print("usage: python3 amta_decompress.py <path to file or directory>", file = sys.stderr)
    exit(1)

min_data_size = 8
max_inflated_size = 104857601
inflated_files = os.path.join(os.path.dirname(__file__), 'inflated_files')

# set to True if you want verbose output of what's going on.
verbose = False

def verbose_log(message, error = False):
    if verbose:
        print(message, file = (sys.stderr if error else sys.stdout))

def inflate_amta(file_path, filedata, data_size, inflated_size):
    filedata = bytearray(filedata[8:])
    unk_byte = filedata[0] ^ 86

    offset = data_size
    py_off = -1

    while offset > 0:
        byte_a = filedata[py_off:(py_off + 1 if py_off < -1 else None)]
        byte_b = filedata[py_off - 1:py_off]

        filedata[py_off:(py_off + 1 if py_off < -1 else None)] = struct.pack('<B',
            int.from_bytes(byte_b, byteorder = 'big') ^ int.from_bytes(byte_a, byteorder = 'big'))

        offset -= 1
        py_off -= 1

    filedata[:1] = struct.pack('<B', unk_byte)
    output_file = os.path.join(inflated_files, os.path.basename(file_path)) + '.lzo'

    with open(output_file, 'wb') as lzo_output:
        verbose_log("[ + ] Writing decompressed lzo file to '%s'..." % output_file)

        lzo_output.write(filedata)

    return lzo.decompress(bytes(filedata), False, inflated_size)

def process_amta(file_path, filedata, data_size):
    verbose_log("[ + ] Processing file %s..." % file_path)
    verbose_log("[ + ] Data size: %d (bytes)" % data_size)

    if filedata[:4] != b'\x61\x6d\x74\x61':  # 'amta' AMT Archive
        verbose_log("[ - ] Skipping file '%s' due to mismatching header."
            % file_path, error = True)

        return

    inflated_size = struct.unpack('<I', filedata[4:8])[0]

    if inflated_size == 0:
        verbose_log("[ - ] Skipping file '%s': bad header. (inflated size == 0)"
            % file_path, error = True)

        return
    elif inflated_size >= max_inflated_size:
        verbose_log("[ - ] Skipping file '%s': bad header. (inflated size >= 0x%08x)"
            % (file_path, max_inflated_size), error = True)

        return

    verbose_log("[ + ] Inflated size: %d (bytes)" % inflated_size)

    decompressed = inflate_amta(file_path, bytearray(filedata), data_size, inflated_size)
    output_file = os.path.join(inflated_files, os.path.basename(file_path))

    with open(output_file, 'wb') as output:
        verbose_log("[ + ] Writing decompressed data to '%s'..." % output_file)

        output.write(decompressed)

def process_file_list(file_list):
    for file in file_list[1]:
        fpath = os.path.join(file_list[0], file)

        if (os.stat(fpath).st_size - 8) < min_data_size:
            verbose_log("[ - ] Skipping file '%s' because the file size is too small (<= 8 bytes)."
                % fpath, error = True)

            continue

        data_size = os.stat(fpath).st_size - 8

        f = open(fpath, 'rb')
        filedata = f.read()

        f.close()

        process_amta(fpath, filedata, data_size)

def main():
    if not os.path.exists(fs_input):
        print("[ - ] Unable to read '%s'." % fs_input, file = sys.stderr)

        exit(1)

    if not os.path.exists(inflated_files):
        os.mkdir(inflated_files, mode = 0o755)

    files = []

    for pd, _, fn in os.walk(fs_input):
        files.append([pd, fn])

    if len(files) == 0:
        files = [[os.path.dirname(fs_input), [os.path.basename(fs_input)]]]

    for file_list in files:
        process_file_list(file_list)

if __name__ == '__main__':
    main()