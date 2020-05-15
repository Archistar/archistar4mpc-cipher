#! /usr/bin/env python3
# coding: utf-8

from mpyc.runtime import mpc
from mpyc import asyncoro

import copy
import secrets
import time

numofboxes = 31
blocksize = 128
keysize = 80
rounds = 12
sec = mpc.SecFld(2**blocksize)

identitysize = blocksize - 3 * numofboxes

def rank(matrix):
  mat = copy.deepcopy(matrix)
  l = len(mat)
  row = 0
  for col in range(1, l + 1):
    mask = 1 << (l - col)
    if (mat[row] & mask) == 0:
      r = row
      while r < l and (mat[r] & mask) == 0:
        r+=1
      if r >= l:
        continue
      else:
        temp = mat[row]
        mat[row] = mat[r]
        mat[r] = temp
    for i in range(row + 1, l):
      if (mat[i] & mask) != 0:
        mat[i] = mat[i] ^ mat[row]
    row += 1
    if row == l:
      break
  return row

def invert(matrix):
  mat = copy.deepcopy(matrix)
  l = len(mat)
  res = []
  for i in range(l):
    res.append(1 << i)
  row = 0
  for col in range(l):
    mask = 1 << col
    if (mat[row] & mask) == 0:
      r = row + 1
      while r < l and (mat[r] & mask) == 0:
        r += 1
      if r >= l:
        continue
      else:
        temp = mat[row]
        mat[row] = mat[r]
        mat[r] = temp
        temp = res[row]
        res[row] = res[r]
        res[r] = temp
    for i in range(row + 1, l):
      if (mat[i] & mask) != 0:
        mat[i] = mat[i] ^ mat[row]
        res[i] = res[i] ^ res[row]
    row += 1
  for col in range(l, 0, -1):
    mask = 1 << (col - 1)
    for r in range(col - 1):
      if (mat[r] & mask) != 0:
        mat[r] = mat[r] ^ mat[col - 1]
        res[r] = res[r] ^ res[col - 1]
  return res

def initialize():
  linmatrices = []
  invlinmatrices = []
  roundconstants = []
  keymatrices = []
  for i in range(rounds):
    mat = []
    while True:
      mat.clear()
      for _ in range(blocksize):
        mat.append(secrets.randbits(blocksize))
      if rank(mat) == blocksize:
        break
    assert len(mat) == blocksize
    linmatrices.append(mat)
    invlinmatrices.append(invert(mat))

  for _ in range(rounds):
    roundconstants.append(secrets.randbits(blocksize))

  for i in range(rounds + 1):
    mat = []
    while True:
      mat.clear()
      for _ in range(keysize):
        mat.append(secrets.randbits(keysize))
      if rank(mat) >= min(blocksize, keysize):
        break
    assert len(mat) == keysize
    keymatrices.append(mat)
  return linmatrices, invlinmatrices, roundconstants, keymatrices

def keyschedule(key, keymatrices):
  return [ [ mpc.in_prod(keymatrices[r][i], key) for i in range(keysize) ] for r in range(rounds + 1) ]

def encrypt(m, roundkeys, linmatrices, roundconstants):
  m = mpc.vector_add(m, roundkeys[0])
  for r in range(rounds):
    m = substitute(m)
    m = [ mpc.in_prod(linmatrices[r][i], m) for i in range(blocksize) ]
    m = mpc.vector_add(m, roundconstants[r])
    m = mpc.vector_add(m, roundkeys[r + 1])
  return m

def decrypt(m, roundkeys, invlinmatrices, roundconstants):
  for r in range(rounds, 0, -1):
    m = mpc.vector_add(m, roundkeys[r])
    m = mpc.vector_add(m, roundconstants[r - 1])
    m = [ mpc.in_prod(invlinmatrices[r - 1][i], m) for i in range(blocksize) ]
    m = invsubstitute(m)
  return mpc.vector_add(m, roundkeys[0])

@asyncoro.mpc_coro
async def substitute(m):
  await asyncoro.returnType(sec, blocksize)
  m = await mpc.gather(m)
  res = m[:]
  for i in range(numofboxes):
    base = identitysize + (i * 3)
    a = m[base]
    b = m[base + 1]
    c = m[base + 2]
    res[base] = a + (b * c)
    res[base + 1] = a + b + (a * c)
    res[base + 2] = a + b + c + (a * b)
  res = await mpc._reshare(res)
  return res

@asyncoro.mpc_coro
async def invsubstitute(m):
  await asyncoro.returnType(sec, blocksize)
  m = await mpc.gather(m)
  res = m[:]
  for i in range(numofboxes):
    base = identitysize + (i * 3)
    a = m[base]
    b = m[base + 1]
    c = m[base + 2]
    res[base] = a + b + (b * c)
    res[base + 1] = b + (a * c)
    res[base + 2] = a + b + c + (a * b)
  res = await mpc._reshare(res)
  return res

def to_bits(n, l):
  return [ sec.field((n >> i) & 1) for i in range(l) ]

async def main():
  await mpc.start()

  print(f"LowMC with blocksize {blocksize}, keysize {keysize}, {numofboxes} s-boxes, {rounds} rounds\n")

  print("generating input ...".ljust(32), end='', flush=True)
  t1 = time.perf_counter()
  linmatrices, invlinmatrices, roundconstants, keymatrices = initialize()
  key = mpc.random.getrandbits(sec, keysize, bits=True)
  inp = mpc.random.getrandbits(sec, blocksize, bits=True)
  inp0 = await mpc.output(mpc.from_bits(inp))
  t2 = time.perf_counter()
  print(f"{(t2 - t1):.5} seconds")

  print("reading in constants ...".ljust(32), end='', flush=True)
  t1 = time.perf_counter()
  for r in range(rounds):
    t = await mpc.output(mpc.input(sec(roundconstants[r]))[0])
    roundconstants[r] = to_bits(t.value.value, blocksize)
    for x in range(blocksize):
      t = await mpc.output(mpc.input(sec(linmatrices[r][x]))[0])
      linmatrices[r][x] = to_bits(t.value.value, blocksize)
      t = await mpc.output(mpc.input(sec(invlinmatrices[r][x]))[0])
      invlinmatrices[r][x] = to_bits(t.value.value, blocksize)
  for r in range(rounds + 1):
    for x in range(keysize):
      t = await mpc.output(mpc.input(sec(keymatrices[r][x]))[0])
      keymatrices[r][x] = to_bits(t.value.value, keysize)
  t2 = time.perf_counter()
  print(f"{(t2 - t1):.5} seconds")

  print("scheduling keys ...".ljust(32), end='', flush=True)
  t1 = time.perf_counter()
  roundkeys = keyschedule(key, keymatrices)
  for r in range(rounds + 1):
    rnd = await mpc.gather(roundkeys[r])
    roundkeys[r] = [ sec(0) for _ in range(blocksize - keysize) ] + rnd
  t2 = time.perf_counter()
  print(f"{(t2 - t1):.5} seconds")

  print("encrypting ...".ljust(32), end='', flush=True)
  t1 = time.perf_counter()
  enc = encrypt(inp, roundkeys, linmatrices, roundconstants)
  encc = await mpc.output(enc)
  t2 = time.perf_counter()
  print(f"{(t2 - t1):.5} seconds")

  print("decrypting ...".ljust(32), end='', flush=True)
  t1 = time.perf_counter()
  dec = decrypt(enc, roundkeys, invlinmatrices, roundconstants)
  dec0 = await mpc.output(mpc.from_bits(dec))
  t2 = time.perf_counter()
  print(f"{(t2 - t1):.5} seconds")

  print("\nchecking ...".ljust(32), end='', flush=True)
  assert inp0 == dec0, f"{inp0.value.value} != {dec0.value.value}"
  print("ok!")
  await mpc.shutdown()

if __name__ == '__main__':
  mpc.run(main())
