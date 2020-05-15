#! /usr/bin/env python3
# coding: utf-8

from mpyc.runtime import mpc
from mpyc import asyncoro
import math
import time

n = 4
sec = mpc.SecFld(2**n)
bits = 64
num_blocks = 8
vec = [
  0xfbe0bf265859051b, 0x517a2e4e239fc97f,
  0x563203161907cf2d, 0xe7a8790fa1b2e9cd,
  0xf75292030268b738, 0x2b4c1a759aa2599a,
  0x285549986e748059, 0x03801a4cb5a5d4f2
]

# set 6, vector 0 from
# https://github.com/cantora/avr-crypto-lib/blob/master/testvectors/trivium-80.80.test-vectors
test1 = [
  0xEB9845F29F4CF9A65300, #0x0053A6F94C9FF24598EB
  0xAC45DE7710A942DB740D, #0x0D74DB42A91077DE45AC,
  [
    0xF4CD954A717F26A7, 0xD6930830C4E7CF08,
    0x19F80E03F25F342C, 0x64ADC66ABA7F8A8E,
    0x6EAA49F23632AE3C, 0xD41A7BD290A0132F,
    0x81C6D4043B6E397D, 0x7388F3A03B5FE358
  ], # stream[0..63]
  [
    0xC04C24A6938C8AF8, 0xA491D5E481271E0E,
    0x601338F01067A86A, 0x795CA493AA4FF265,
    0x619B8D448B706B7C, 0x88EE8395FC79E5B5,
    0x1AB40245BBF7773A, 0xE67DF86FCFB71F30
  ], # stream[65472..65535]
  [
    0x011A0D7EC32FA102, 0xC66C164CFCB189AE,
    0xD9F6982E8C7370A6, 0xA37414781192CEB1,
    0x55C534C1C8C9E53F, 0xDEADF2D3D0577DAD,
    0x3A8EB2F6E5265F1E, 0x831C86844670BC69
  ], # stream[65536..65599]
  [
    0x48107374A9CE3AAF, 0x78221AE77789247C,
    0xF6896A249ED75DCE, 0x0CF2D30EB9D889A0,
    0xC61C9F480E5C0738, 0x1DED9FAB2AD54333,
    0xE82C89BA92E6E47F, 0xD828F1A66A8656E0
  ] # stream[131008..131071]
]

@asyncoro.mpc_coro
async def initialize(key, iv):
  await asyncoro.returnType(sec, 288)
  assert len(key) == 80
  assert len(iv) == 80
  res = key + [ mpc.input(sec(0))[0] for _ in range(13) ] + iv + [ mpc.input(sec(0))[0] for _ in range(112) ] + [ mpc.input(sec(1))[0] for _ in range(3) ]
  for x in range(16):
    res = await mpc.gather(res)
    for y in range(72):
      t1 = res[65] + (res[90] * res[91]) + res[92] + res[170]
      t2 = res[161] + (res[174] * res[175]) + res[176] + res[263]
      t3 = res[242] + (res[285] * res[286]) + res[287] + res[68]
      res = [t3] + res[:92] + [t1] + res[93:176] + [t2] + res[177:287]
    res = await mpc._reshare(res)
  assert len(res) == 288
  return res

def next(st):
  t1 = st[65] + st[92]
  t2 = st[161] + st[176]
  t3 = st[242] + st[287]
  res = t1 + t2 + t3
  t1 = t1 + (st[90] * st[91]) + st[170]
  t2 = t2 + (st[174] * st[175]) + st[263]
  t3 = t3 + (st[285] * st[286]) + st[68]
  st = [t3] + st[:92] + [t1] + st[93:176] + [t2] + st[177:287]
  return st, res

@asyncoro.mpc_coro
async def keystreamblock(st):
  await asyncoro.returnType(sec, 288 + bits)
  res = [None] * bits
  st = await mpc.gather(st)
  for i in range(bits):
    st, bit = next(st)
    res[i] = bit
  st = await mpc._reshare(st)
  return st + res

def decode_block(block):
  res = 0
  for i in range(bits // 8):
    byte = 0
    for j in range(8):
      byte += block[(i * 8) + j].value.value * 2**j
    res += byte * 256**(7 - i)
  return res

@asyncoro.mpc_coro
async def to_bits(n):
  await asyncoro.returnType(sec, 80)
  return [ mpc.input(sec((n >> i) & 1))[0] for i in range(79, -1, -1) ]

@asyncoro.mpc_coro
async def test():
  await asyncoro.returnType(None)
  key = to_bits(test1[0])
  iv = to_bits(test1[1])
  st = initialize(key, iv)
  st = await mpc.gather(st)
  st = await mpc._reshare(st)
  blocks = [None] * 8
  for i in range(8):
    res = keystreamblock(st)
    st = res[:288]
    blocks[i] = res[288:]
  for i in range(8):
    blocks[i] = await mpc.output(blocks[i])
  res = [ decode_block(block) for block in blocks ]
  assert test1[2] == res, f"{test1[2]} not equal {res}"
  for _ in range(8176):
    res = keystreamblock(st)
    st = res[:288]
  for i in range(8):
    res = keystreamblock(st)
    st = res[:288]
    blocks[i] = res[288:]
  for i in range(8):
    blocks[i] = await mpc.output(blocks[i])
  res = [ decode_block(block) for block in blocks ]
  assert test1[3] == res, f"{test1[3]} not equal {res}"
  print("ok!")

async def main():
  await mpc.start()
  key = [ mpc.input(sec(0))[0] for _ in range(80) ]
  iv = [ mpc.input(sec(0))[0] for _ in range(80) ]
  print("initializing ... ", end='', flush=True)
  t1 = time.perf_counter()
  st = initialize(key, iv)
  init = await mpc.output(st)
  t2 = time.perf_counter()
  print(f"{(t2 - t1):f} seconds")
  print("coding ... ", end='', flush=True)
  t1 = time.perf_counter()
  blocks = [None] * num_blocks
  for i in range(num_blocks):
    res = keystreamblock(st)
    st = res[:288]
    blocks[i] = res[288:]
  for i in range(num_blocks):
    blocks[i] = await mpc.output(blocks[i])
  t2 = time.perf_counter()
  print(f"{(t2 - t1):f} seconds")
  print("checking ... ", end='', flush=True)
  res = [ decode_block(block) for block in blocks ]
  assert vec == res, f"{vec} not equal {res}"
  print("ok!")
  print("extra long test with 64kB")
  test()
  await mpc.shutdown()

if __name__ == '__main__':
  mpc.run(main())
