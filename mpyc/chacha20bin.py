#! /usr/bin/env python3
# coding: utf-8

from mpyc.runtime import mpc
from mpyc import asyncoro

import time

sec = mpc.SecFld(2**4)
bound = 2 ** 32
constant = [ None, None, None, None ]
vec = [
  0xade0b876, 0x903df1a0,
  0xe56a5d40, 0x28bd8653,
  0xb819d2bd, 0x1aed8da0,
  0xccef36a8, 0xc70d778b,
  0x7c5941da, 0x8d485751,
  0x3fe02477, 0x374ad8b8,
  0xf4b8436a, 0x1ca11815,
  0x69b687c3, 0x8665eeb2
]

def quarterround(buffer, a, b, c, d):
  for rot1, rot2 in [[16, 12],[8, 7]]:
    buffer[a] = add(buffer[a], buffer[b])
    buffer[d] = rotl(mpc.vector_add(buffer[d], buffer[a]), rot1)
    buffer[c] = add(buffer[c], buffer[d])
    buffer[b] = rotl(mpc.vector_add(buffer[b], buffer[c]), rot2)

def doubleround(buffer):
  quarterround(buffer, 0, 4, 8, 12)
  quarterround(buffer, 1, 5, 9, 13)
  quarterround(buffer, 2, 6, 10, 14)
  quarterround(buffer, 3, 7, 11, 15)
  quarterround(buffer, 0, 5, 10, 15)
  quarterround(buffer, 1, 6, 11, 12)
  quarterround(buffer, 2, 7, 8, 13)
  quarterround(buffer, 3, 4, 9, 14)

@asyncoro.mpc_coro
async def matrix(key, nonce, counter):
  await asyncoro.returnType(sec, 16, 32)
  return [
    constant[0], constant[1], constant[2], constant[3],
    key[0], key[1], key[2], key[3],
    key[4], key[5], key[6], key[7],
    counter[0], counter[1], nonce[0], nonce[1]
  ]

def to_bits(n,secret=False):
  if secret:
    return [ mpc.input(sec((n >> i) & 1))[0] for i in range(31, -1, -1) ]
  else:
    return [ (n >> i) & 1 for i in range(31, -1, -1) ]

def from_bits(l):
  res = 0
  mul = 1
  for b in reversed(l):
    res += (b * mul)
    mul *= 2
  return res

def code(key, nonce, inp):
  assert(len(key) == 8)
  assert(len(nonce) == 2)
  length = len(inp)
  for b in range((length // 16) + (length % 16 != 0)):
    size = min(16, length - (b * 16))
    counter = [ to_bits(b >> 32, secret=False), to_bits(b % bound, secret=False) ]
    block = matrix(key, nonce, counter)
    oblock = matrix(key, nonce, counter)
    for _ in range(10):
      doubleround(block)
    for i in range(size):
      block[i] = add(block[i], oblock[i])
      inp[(16 * b) + i] = mpc.vector_add(inp[(16 * b) + i], block[i])

def rotl(x, n):
  return x[n:] + x[:n]

@asyncoro.mpc_coro
async def add(a, b):
  await asyncoro.returnType(sec, 32)
  res = [None] * 32
  c = None
  atb = mpc.schur_prod(a, b)
  apb = mpc.vector_add(a, b)
  for i in range(31, -1, -1):
    res[i], c = add_(atb[i], apb[i], c)
  return res

def add_(atb, apb, c = None):
  if c is None:
    return apb, atb
  else:
    return apb + c, (c * apb) + atb

async def main():
  await mpc.start()
  print(f"One 64-byte block of ChaCha20 with input 0, key 0, nonce 0\n")

  print("initializing ...".ljust(32), end='', flush=True)
  t1 = time.perf_counter()
  constant[0] = to_bits(1634760805, secret=False)
  constant[1] = to_bits(857760878, secret=False)
  constant[2] = to_bits(2036477234, secret=False)
  constant[3] = to_bits(1797285236, secret=False)
  key = [ to_bits(0, secret=True) for _ in range(8) ]
  nonce = [ to_bits(0, secret=True) for _ in range(2) ]
  inp = [ to_bits(0, secret=True) for _ in range(16) ]
  t2 = time.perf_counter()
  print(f"{(t2 - t1):.5} seconds")

  print("encrypting ...".ljust(32), end='', flush=True)
  t1 = time.perf_counter()
  code(key, nonce, inp)
  res = [ await mpc.output(r) for r in inp ]
  res = [ from_bits([r0.value.value for r0 in r]) for r in res ]
  t2 = time.perf_counter()
  print(f"{(t2 - t1):.5} seconds")

  print("\nchecking ...".ljust(32), end='', flush=True)
  assert res == vec, f"{res} != {vec}"
  print("ok!")
  await mpc.shutdown()

if __name__ == '__main__':
  mpc.run(main())
