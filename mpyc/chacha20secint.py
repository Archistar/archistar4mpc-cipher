#! /usr/bin/env python3
# coding: utf-8

from mpyc.runtime import mpc
from mpyc import asyncoro

import copy
import time

secint = mpc.SecInt(32)
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
  for rot1, rot2 in [[16, 20],[24, 25]]:
    buffer[a] += buffer[b]
    buffer[d] = mpc.from_bits(rotl(to_bits_xor(buffer[d], buffer[a]), rot1))
    buffer[c] += buffer[d]
    buffer[b] = mpc.from_bits(rotl(to_bits_xor(buffer[b], buffer[c]), rot2))

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
  await asyncoro.returnType(secint, 16)
  return [
    constant[0], constant[1], constant[2], constant[3],
    key[0], key[1], key[2], key[3],
    key[4], key[5], key[6], key[7],
    counter[0], counter[1], nonce[0], nonce[1]
  ]

def code(key, nonce, inp):
  assert(len(key) == 8)
  assert(len(nonce) == 2)
  length = len(inp)
  for b in range((length // 16) + (length % 16 != 0)):
    size = min(16, length - (b * 16))
    block = matrix(key, nonce, [secint.field(b >> 32), secint.field(b % bound)])
    oblock = matrix(key, nonce, [secint.field(b >> 32), secint.field(b % bound)])
    for _ in range(10):
      doubleround(block)
    for i in range(size):
      block[i] += oblock[i]
      inp[(16 * b) + i] = mpc.from_bits(to_bits_xor(inp[(16 * b) + i], block[i]))

def rotl(x, n):
  return x[n:] + x[:n]

def to_bits_xor(a, b):
  a = mpc.to_bits(a)
  b = mpc.to_bits(b)
  return [ a0 ^ b0 for a0, b0 in zip(a, b) ]

async def main():
  await mpc.start()
  print(f"One 64-byte block of ChaCha20 with input 0, key 0, nonce 0\n")

  print("initializing ...".ljust(32), end='', flush=True)
  t1 = time.perf_counter()
  constant[0] = secint.field(1634760805)
  constant[1] = secint.field(857760878)
  constant[2] = secint.field(2036477234)
  constant[3] = secint.field(1797285236)
  key = [ mpc.input(secint(0))[0] for _ in range(8) ]
  nonce = [ mpc.input(secint(0))[0] for _ in range(2) ]
  inp = [ mpc.input(secint(0))[0] for _ in range(16) ]
  t2 = time.perf_counter()
  print(f"{(t2 - t1):.5} seconds")

  print("encrypting ...".ljust(32), end='', flush=True)
  t1 = time.perf_counter()
  code(key, nonce, inp)
  res = await (mpc.output(inp))
  t2 = time.perf_counter()
  print(f"{(t2 - t1):.5} seconds")

  print("\nchecking ...".ljust(32), end='', flush=True)
  assert res == vec, f"{res} != {vec}"
  print("ok!")
  await mpc.shutdown()

if __name__ == '__main__':
  mpc.run(main())
