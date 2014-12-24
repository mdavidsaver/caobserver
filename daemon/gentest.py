# -*- coding: utf-8 -*-

import sys, struct, socket, threading, time

_head = struct.Struct('!HHHHII')
_head_ip = struct.Struct('!HHHHI4s')

def sendsearch(pvs, cid=115):
    buf = [_head.pack(0, 0, 0, 11, 0, 0)]
    for cid, pv in enumerate(pvs, cid):
        if len(pv)%8!=0:
            pv += '\0'*(8-len(pv)%8)
            assert len(pv)%8==0
        buf.append(_head.pack(6, len(pv), 5, 11, cid, cid)+pv)
    return ('send', ''.join(buf))

def beacon(seq=0, ver=11):
    return ('send', _head.pack(13, 0, ver, 0, seq, 0x7f000042))

searches = [
    sendsearch(['pv:%0d'%i for i in range(10)]),
    ('wait', 0.1),
    sendsearch(['pv:%0d'%i for i in range(10)]),
    ('wait', 0.1),
    sendsearch(['pv:special'], cid=42),
    ('wait', 0.5),
    sendsearch(['pv:special','pv:single'], cid=42),
    ('wait', 2.0),
    sendsearch(['pv:special'], cid=42),
]

beacons = [
    beacon(seq=0),
    ('wait', 2.0),
    beacon(seq=1),
    ('wait', 2.0),
    beacon(seq=2),
    ('wait', 2.0),
    beacon(seq=4),
    ('wait', 2.0),
    beacon(seq=5),
    ('wait', 2.0),
]

def udpprogram(addr,prog):
    S = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, 0)
    S.bind((addr[0],0))
    for i,inst in enumerate(prog):
        if inst[0]=='settimeout':
            S.settimeout(inst[1])
        elif inst[0]=='send':
            print '>>>',addr,repr(inst[1])
            S.sendto(inst[1], addr)
        elif inst[0]=='wait':
            print 'wait',inst[1]
            time.sleep(inst[1])
        else:
            raise RuntimeError('Unknown instruction %d: %s'%(i,inst[0]))

def main():
    addr = sys.argv[1]
    T1 = threading.Thread(target=udpprogram, args=((addr,5065),beacons))
    T2 = threading.Thread(target=udpprogram, args=((addr,5064),searches))
    print 'Starting'
    T1.start()
    T2.start()
    print 'Running'
    T1.join()
    T2.join()
    print 'Done'

if __name__=='__main__':
    main()
