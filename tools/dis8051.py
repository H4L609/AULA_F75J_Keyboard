"""8051 の簡易逆アセンブラ（F75J ファーム解析用）。

使い方:
  python tools/dis8051.py <bin> <開始アドレス(16進)> [命令数]
<bin> はファーム本体を、0x0000 から並べた生のバイナリ。
  例: python tools/dis8051.py build/f75j.bin 4170 20

書式の記号:
  {d} 直接アドレス(1バイト目)  {d2} 直接アドレス(2バイト目)  {b} ビットアドレス
  {i} 即値(1バイト目)  {i2} 即値(2バイト目)  {r} 相対ジャンプ先(最後のバイト)
  {L} 16ビットアドレス  {A} 11ビット絶対アドレス(ajmp/acall)
"""
import sys

OPS = {}
def op(code, length, fmt): OPS[code] = (length, fmt)

for n in range(8):
    R = f'r{n}'
    op(0x08+n,1,f'inc {R}');  op(0x18+n,1,f'dec {R}');  op(0x28+n,1,f'add a,{R}')
    op(0x38+n,1,f'addc a,{R}'); op(0x48+n,1,f'orl a,{R}'); op(0x58+n,1,f'anl a,{R}')
    op(0x68+n,1,f'xrl a,{R}'); op(0x78+n,2,f'mov {R},#{{i}}'); op(0x88+n,2,f'mov {{d}},{R}')
    op(0x98+n,1,f'subb a,{R}'); op(0xA8+n,2,f'mov {R},{{d}}'); op(0xB8+n,3,f'cjne {R},#{{i}},{{r}}')
    op(0xC8+n,1,f'xch a,{R}'); op(0xD8+n,2,f'djnz {R},{{r}}'); op(0xE8+n,1,f'mov a,{R}')
    op(0xF8+n,1,f'mov {R},a')
for k in range(2):
    R = f'@r{k}'
    op(0x06+k,1,f'inc {R}'); op(0x16+k,1,f'dec {R}'); op(0x26+k,1,f'add a,{R}')
    op(0x36+k,1,f'addc a,{R}'); op(0x46+k,1,f'orl a,{R}'); op(0x56+k,1,f'anl a,{R}')
    op(0x66+k,1,f'xrl a,{R}'); op(0x76+k,2,f'mov {R},#{{i}}'); op(0x86+k,2,f'mov {{d}},{R}')
    op(0x96+k,1,f'subb a,{R}'); op(0xA6+k,2,f'mov {R},{{d}}'); op(0xB6+k,3,f'cjne {R},#{{i}},{{r}}')
    op(0xC6+k,1,f'xch a,{R}'); op(0xD6+k,1,f'xchd a,{R}'); op(0xE6+k,1,f'mov a,{R}')
    op(0xF6+k,1,f'mov {R},a'); op(0xE2+k,1,f'movx a,{R}'); op(0xF2+k,1,f'movx {R},a')
for p in range(8):
    op(0x01+p*0x20,2,'ajmp {A}'); op(0x11+p*0x20,2,'acall {A}')

for code, length, fmt in [
    (0x00,1,'nop'),(0x02,3,'ljmp {L}'),(0x03,1,'rr a'),(0x04,1,'inc a'),(0x05,2,'inc {d}'),
    (0x10,3,'jbc {b},{r}'),(0x12,3,'lcall {L}'),(0x13,1,'rrc a'),(0x14,1,'dec a'),(0x15,2,'dec {d}'),
    (0x20,3,'jb {b},{r}'),(0x22,1,'ret'),(0x23,1,'rl a'),(0x24,2,'add a,#{i}'),(0x25,2,'add a,{d}'),
    (0x30,3,'jnb {b},{r}'),(0x32,1,'reti'),(0x33,1,'rlc a'),(0x34,2,'addc a,#{i}'),(0x35,2,'addc a,{d}'),
    (0x40,2,'jc {r}'),(0x42,2,'orl {d},a'),(0x43,3,'orl {d},#{i2}'),(0x44,2,'orl a,#{i}'),(0x45,2,'orl a,{d}'),
    (0x50,2,'jnc {r}'),(0x52,2,'anl {d},a'),(0x53,3,'anl {d},#{i2}'),(0x54,2,'anl a,#{i}'),(0x55,2,'anl a,{d}'),
    (0x60,2,'jz {r}'),(0x62,2,'xrl {d},a'),(0x63,3,'xrl {d},#{i2}'),(0x64,2,'xrl a,#{i}'),(0x65,2,'xrl a,{d}'),
    (0x70,2,'jnz {r}'),(0x72,2,'orl c,{b}'),(0x73,1,'jmp @a+dptr'),(0x74,2,'mov a,#{i}'),(0x75,3,'mov {d},#{i2}'),
    (0x80,2,'sjmp {r}'),(0x82,2,'anl c,{b}'),(0x83,1,'movc a,@a+pc'),(0x84,1,'div ab'),(0x85,3,'mov {d2},{d}'),
    (0x90,3,'mov dptr,#{L}'),(0x92,2,'mov {b},c'),(0x93,1,'movc a,@a+dptr'),(0x94,2,'subb a,#{i}'),(0x95,2,'subb a,{d}'),
    (0xA0,2,'orl c,/{b}'),(0xA2,2,'mov c,{b}'),(0xA3,1,'inc dptr'),(0xA4,1,'mul ab'),(0xA5,1,'db A5'),
    (0xB0,2,'anl c,/{b}'),(0xB2,2,'cpl {b}'),(0xB3,1,'cpl c'),(0xB4,3,'cjne a,#{i},{r}'),(0xB5,3,'cjne a,{d},{r}'),
    (0xC0,2,'push {d}'),(0xC2,2,'clr {b}'),(0xC3,1,'clr c'),(0xC4,1,'swap a'),(0xC5,2,'xch a,{d}'),
    (0xD0,2,'pop {d}'),(0xD2,2,'setb {b}'),(0xD3,1,'setb c'),(0xD4,1,'da a'),(0xD5,3,'djnz {d},{r}'),
    (0xE0,1,'movx a,@dptr'),(0xE4,1,'clr a'),(0xE5,2,'mov a,{d}'),
    (0xF0,1,'movx @dptr,a'),(0xF4,1,'cpl a'),(0xF5,2,'mov {d},a'),
]:
    op(code, length, fmt)

# SH68F90A のおもな SFR（F75 の解析に合わせた名前）
SFR = {0x80:'P0',0x81:'SP',0x82:'DPL',0x83:'DPH',0x87:'PCON',0x88:'P5',0x90:'P1',0xA0:'P2',
       0xA8:'IEN0',0xAA:'SBUF',0xB0:'P4',0xB8:'IPL0',0xC0:'P6',0xD0:'PSW',0xD8:'SCON',
       0xE0:'ACC',0xF0:'B',0xF8:'P7'}

def dname(a):
    return SFR.get(a, f'{a:02X}h')

def bname(b):
    if b < 0x80:
        return f'{0x20 + b // 8:02X}h.{b % 8}'
    return f'{SFR.get(b & 0xF8, f"{b & 0xF8:02X}h")}.{b & 7}'

def rel(pc, ln, x):
    return f'{(pc + ln + (x - 256 if x > 127 else x)) & 0xFFFF:04X}'

def dis_one(fw, pc):
    code = fw[pc]
    ln, fmt = OPS[code]
    b = fw[pc:pc + ln]
    f = dict(
        d=dname(b[1]) if ln > 1 else '', d2=dname(b[2]) if ln > 2 else '',
        b=bname(b[1]) if ln > 1 else '', i=f'{b[1]:02X}h' if ln > 1 else '',
        i2=f'{b[2]:02X}h' if ln > 2 else '', r=rel(pc, ln, b[-1]) if ln > 1 else '',
        L=f'{(b[1] << 8 | b[2]):04X}' if ln > 2 else '',
        A=f'{((pc + 2) & 0xF800) | ((code >> 5) << 8) | b[1]:04X}' if ln > 1 else '')
    return ln, f'{pc:04X}: {b.hex(" "):<9} {fmt.format(**f)}'

def dis(fw, pc, n):
    lines = []
    for _ in range(n):
        ln, s = dis_one(fw, pc)
        lines.append(s)
        pc += ln
    return lines

if __name__ == '__main__':
    fw = open(sys.argv[1], 'rb').read()
    n = int(sys.argv[3]) if len(sys.argv) > 3 else 30
    print('\n'.join(dis(fw, int(sys.argv[2], 16), n)))
