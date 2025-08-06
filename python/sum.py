#!/usr/bin/env python3

"""
Name: sum
Description: display file checksums and block counts
Author: Theo Van Dinter, felicity@kluge.net
License:
"""

import sys
import os
import re
import binascii
from functools import reduce
from collections import deque
import hashlib
import importlib
import argparse

# Constants
BUFLEN = 4096
EX_SUCCESS = 0
EX_FAILURE = 1
MASK32 = 0xFFFFFFFF
MASK16 = 0xFFFF
MASK8 = 0xFF

PROGRAM_NAME = os.path.basename(sys.argv[0])

def help_and_exit(message=None):
    """Prints a help message and exits with an error."""
    if message:
        sys.stderr.write(f"{PROGRAM_NAME}: {message}\n")
    sys.stderr.write("""
usage: sum [-a alg] [-o 1|2] [file ...]

 -a alg    Select algorithm: crc, md5, sha1, sha224, sha256, sha384, sha512
 -o alg    Select historic algorithm: 1 (BSD), 2 (SYSV)

Optional alorithms: blake224 blake256 blake384 blake512 jh224 jh256
  jh384 jh512 haval256 md2 md4 sha3-224 sha3-256 sha3-384 sha3-512
  whirlpool
""")
    sys.exit(EX_FAILURE)

def sum1(file_handle):
    """Historic BSD `sum` algorithm."""
    crc = 0
    length = 0
    while True:
        buf = file_handle.read(BUFLEN)
        if not buf:
            break
        length += len(buf)
        for byte_val in buf:
            if crc & 1:
                crc = (crc >> 1) + 0x8000
            else:
                crc >>= 1
            crc = (crc + byte_val) & MASK16
    
    # Calculate block count (512-byte blocks, rounded up)
    block_count = (length + 511) // 512
    return True, crc, block_count

def sum2(file_handle):
    """Historic SYSV `sum` algorithm."""
    crc = 0
    length = 0
    while True:
        buf = file_handle.read(BUFLEN)
        if not buf:
            break
        length += len(buf)
        
        chunk_sum = sum(buf)
        crc = (crc + chunk_sum) & MASK32
        
    crc = (crc & MASK16) + ((crc >> 16) & MASK16)
    crc = (crc & MASK16) + (crc >> 16)

    # Calculate block count (512-byte blocks, rounded up)
    block_count = (length + 511) // 512
    return True, crc, block_count

def crc32(file_handle):
    """CRC32 algorithm (IEEE 802.3)."""
    crc = 0
    length = 0
    
    while True:
        buf = file_handle.read(BUFLEN)
        if not buf:
            break
        length += len(buf)
        crc = binascii.crc32(buf, crc) & MASK32

    # The Perl script has a custom table-based CRC32 implementation.
    # Python's `binascii.crc32` is faster and produces the same result.
    return True, crc, length

def do_hashlib(file_handle, algorithm_name, digest_size=None):
    """Generic function to handle algorithms available in hashlib."""
    try:
        if digest_size:
            hash_obj = hashlib.new(algorithm_name, digest_size=digest_size)
        else:
            hash_obj = hashlib.new(algorithm_name)
    except ValueError:
        sys.stderr.write(f"The {algorithm_name} algorithm is not available in hashlib\n")
        sys.exit(EX_FAILURE)
    
    while True:
        buf = file_handle.read(BUFLEN)
        if not buf:
            break
        hash_obj.update(buf)
        
    return True, hash_obj.hexdigest(), None

def do_digest_module(file_handle, module_name, algorithm_name=None):
    """Generic function to handle algorithms from external Digest:: modules."""
    try:
        digest_module = importlib.import_module(module_name)
    except ImportError:
        sys.stderr.write(f"The {module_name} module is not available on your system\n")
        sys.exit(EX_FAILURE)
        
    if algorithm_name:
        match = re.match(r'[a-z]+(\d+)', algorithm_name)
        if match:
            digest_size = int(match.group(1))
            ctx = digest_module.new(digest_size)
        else:
            sys.stderr.write(f"Unknown digest size: {algorithm_name}\n")
            sys.exit(EX_FAILURE)
    else:
        ctx = digest_module.new()

    while True:
        buf = file_handle.read(BUFLEN)
        if not buf:
            break
        ctx.update(buf)

    return True, ctx.hexdigest(), None

def do_blake(file_handle, algo):
    """Handler for BLAKE algorithms."""
    match = re.match(r'blake(\d+)', algo)
    if not match:
        sys.stderr.write(f"Unknown digest size: {algo}\n")
        sys.exit(EX_FAILURE)
    return do_hashlib(file_handle, f'blake2s-{match.group(1)}', digest_size=int(match.group(1)) // 8)

def do_sha3(file_handle, algo):
    """Handler for SHA3 algorithms."""
    match = re.match(r'sha3-(\d+)', algo)
    if not match:
        sys.stderr.write(f"Unknown digest size: {algo}\n")
        sys.exit(EX_FAILURE)
    return do_hashlib(file_handle, f'sha3_{match.group(1)}')

def do_whirlpool(file_handle, algo):
    """Handler for Whirlpool."""
    return do_hashlib(file_handle, 'whirlpool')


def main():
    """Main function to parse arguments and run the sum utility."""
    parser = argparse.ArgumentParser(description="Display file checksums and block counts.", add_help=False)
    parser.add_argument('-a', dest='algorithm', help='Select algorithm.')
    parser.add_argument('-o', dest='historic', choices=['1', '2'], help='Select historic algorithm: 1 (BSD), 2 (SYSV).')
    parser.add_argument('files', nargs='*', default=['-'], help='Files to process.')

    args = parser.parse_args()

    # Determine the default algorithm based on the program name
    if PROGRAM_NAME == 'cksum':
        algo_func = crc32
    else:
        algo_func = sum1

    # Override the default with command-line options
    if args.algorithm:
        if args.historic:
            help_and_exit(f"cannot use both -a and -o options")
        
        alg_name = args.algorithm.lower()
        codetab = {
            'blake224': lambda fh: do_hashlib(fh, 'blake2s', digest_size=28),
            'blake256': lambda fh: do_hashlib(fh, 'blake2s', digest_size=32),
            'blake384': lambda fh: do_hashlib(fh, 'blake2s', digest_size=48),
            'blake512': lambda fh: do_hashlib(fh, 'blake2s', digest_size=64),
            'crc': crc32,
            'jh224': lambda fh: do_digest_module(fh, 'Digest.JH', 'jh224'),
            'jh256': lambda fh: do_digest_module(fh, 'Digest.JH', 'jh256'),
            'jh384': lambda fh: do_digest_module(fh, 'Digest.JH', 'jh384'),
            'jh512': lambda fh: do_digest_module(fh, 'Digest.JH', 'jh512'),
            'haval256': lambda fh: do_digest_module(fh, 'Digest.Haval256'),
            'md2': lambda fh: do_digest_module(fh, 'Digest.MD2'),
            'md4': lambda fh: do_digest_module(fh, 'Digest.MD4'),
            'md5': lambda fh: do_hashlib(fh, 'md5'),
            'sha1': lambda fh: do_hashlib(fh, 'sha1'),
            'sha224': lambda fh: do_hashlib(fh, 'sha224'),
            'sha256': lambda fh: do_hashlib(fh, 'sha256'),
            'sha384': lambda fh: do_hashlib(fh, 'sha384'),
            'sha512': lambda fh: do_hashlib(fh, 'sha512'),
            'sha3-224': lambda fh: do_hashlib(fh, 'sha3_224'),
            'sha3-256': lambda fh: do_hashlib(fh, 'sha3_256'),
            'sha3-384': lambda fh: do_hashlib(fh, 'sha3_384'),
            'sha3-512': lambda fh: do_hashlib(fh, 'sha3_512'),
            'whirlpool': lambda fh: do_hashlib(fh, 'whirlpool'),
        }
        if alg_name not in codetab:
            help_and_exit("invalid algorithm name")
        algo_func = codetab[alg_name]
    elif args.historic:
        if args.historic == '1':
            algo_func = sum1
        else:
            algo_func = sum2

    exit_val = EX_SUCCESS
    for file_name in args.files:
        if file_name == '-':
            file_handle = sys.stdin.buffer
        elif os.path.isdir(file_name):
            sys.stderr.write(f"{PROGRAM_NAME}: '{file_name}' is a directory\n")
            exit_val = EX_FAILURE
            continue
        else:
            try:
                file_handle = open(file_name, 'rb')
            except IOError as e:
                sys.stderr.write(f"{PROGRAM_NAME}: failed to open '{file_name}': {e}\n")
                exit_val = EX_FAILURE
                continue
        
        # Read the entire file at once for external modules
        is_success, checksum, length = algo_func(file_handle)

        if not is_success:
            sys.stderr.write(f"{PROGRAM_NAME}: '{file_name}': an error occurred during calculation\n")
            exit_val = EX_FAILURE
        else:
            if length is not None:
                print(f"{checksum} {length} {file_name if file_name != '-' else ''}".strip())
            else:
                print(f"{checksum} {file_name if file_name != '-' else ''}".strip())

        if file_name != '-':
            file_handle.close()

    sys.exit(exit_val)

if __name__ == '__main__':
    main()
