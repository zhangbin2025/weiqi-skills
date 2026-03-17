#!/usr/bin/env python3
import re
import os

# 昨天日期
DATE = "2026-03-13"
OUTPUT_DIR = f"/root/.openclaw/workspace/qipu/{DATE}"

# 棋谱列表 (标题和SGF内容片段)
games = [
    {
        "title": "第8届扇兴杯世界女子最强战8强 周泓余执黑中盘胜上野梨纱",
        "filename": "2026031356342596_zhouhongyu_vs_shangyelisha.sgf",
        "sgf": """(;GM[1]FF[4]
SZ[19]
GN[第8届扇兴杯世界女子最强战8强<绝艺讲解>]
DT[2026-03-13]
PB[周泓余]
PW[上野梨纱]
BR[P7段]
WR[P2段]
KM[650]HA[0]RU[Japanese]AP[GNU Go:3.8]RE[B+R]TM[7200]TC[5]TT[60]AP[foxwq]RL[0]
;B[pd];W[dd];B[qp];W[dq];B[op];W[co];B[pj];W[nc];B[pf];W[pb];B[qc];W[kc];B[jq];W[hq];B[jo];W[ck];B[cc];W[dc];B[cd];W[cf];B[bf];W[bg];B[ce];W[df];B[de];W[ee];B[ed];W[eb];B[fd];W[fe];B[ge];W[gf];B[hf];W[gg];B[fc];W[cb];B[hg];W[gh];B[hh];W[gi];B[hi];W[gj];B[dm];W[cm];B[dp];W[cp];B[eq];W[dr];B[gq];W[ep];B[fp];W[eo];B[fo];W[en];B[fn];W[em];B[fm];W[el];B[ho];W[mp];B[mo];W[lo];B[no];W[jp];B[kp];W[ip];B[ko];W[io];B[kq];W[ir];B[jr];W[in];B[hm];W[mn];B[lp];W[mr];B[lr];W[po];B[pp];W[or];B[qn];W[qh];B[qg];W[ph];B[nd];W[md];B[me];W[ne];B[nf];W[od];B[oe];W[mc];B[qb];W[rg];B[rf];W[pg];B[qf];W[rj];B[oc];W[ob];B[pc];W[ld];B[le];W[ke];B[kd];W[je];B[jd];W[id];B[ie];W[jc];B[jf];W[lf];B[he];W[mf];B[qk];W[re];B[qe];W[rk];B[rl];W[ql];B[rm];W[pl];B[oj];W[oh];B[ri];W[qi];B[qj];W[si];B[sk];W[sj];B[rh];W[sh];B[sg];W[sf];B[rg];W[pm];B[oo];W[qq];B[rq];W[qr];B[rr];W[pr];B[on];W[ro];B[qo];W[rp];B[rn];W[om];B[nm];W[nl];B[mm];W[nn];B[mn];W[ln];B[kn];W[lm];B[ml];W[ll];B[mk];W[lk];B[mj];W[lj];B[mi];W[li];B[mh];W[lh];B[lg];W[kg];B[kh];W[ki];B[ji];W[jh];B[ii];W[kj];B[ij];W[ng];B[nk];W[nj];B[ok];W[hn];B[gn];W[gm];B[hl];W[il];B[ik];W[gl];B[fl];W[fk];B[ek];W[ej];B[dj];W[cj];B[dk];W[dl];B[fj];W[gk];B[ei];W[hj];B[im];W[jl];B[jm];W[hk];B[kl];W[jk];B[ih];W[ig];B[if];W[jg];B[hc];W[hb];B[gb];W[ic];B[hd];W[fb];B[gc];W[ga];B[ib];W[ia];B[ha];W[ja];B[kb];W[jb];B[lb];W[mb];B[nb];W[na];B[ma];W[oa];B[ka];W[lc];B[hb];W[kf];B[mg];W[ne];B[of];W[og]
)"""
    },
    {
        "title": "第8届扇兴杯世界女子最强战8强 金恩持执黑中盘胜加藤千笑",
        "filename": "2026031351544694_jineunchi_vs_jiatengqianxiao.sgf",
        "sgf": """(;GM[1]FF[4]
SZ[19]
GN[第8届扇兴杯世界女子最强战8强<绝艺讲解>]
DT[2026-03-13]
PB[김은지]
PW[加藤千笑]
BR[P9段]
WR[P4段]
KM[650]HA[0]RU[Japanese]AP[GNU Go:3.8]RE[B+R]TM[7200]TC[5]TT[60]AP[foxwq]RL[0]
;B[pd];W[dp];B[pp];W[dc];B[cq];W[cp];B[dq];W[ep];B[fq];W[qc];B[pc];W[qd];B[pe];W[rf];B[gr];W[cf];B[cl];W[el];B[dj];W[go];B[ch];W[kc];B[ic];W[gc];B[ie];W[ke];B[ig];W[kg];B[mc];W[ji];B[hi];W[ge];B[qf];W[rg];B[kh];W[jh];B[jg];W[lg];B[kj];W[jj];B[lh];W[mg];B[mh];W[ng];B[nh];W[og];B[jk];W[ik];B[lk];W[hk];B[ph];W[oh];B[oi];W[pg];B[qg];W[qh];B[pi];W[qe];B[pf];W[ob];B[pb];W[mb];B[qb];W[rb];B[rh];W[qi];B[re];W[rd];B[sg];W[se];B[qj];W[ri];B[si];W[sh];B[lb];W[pj];B[nb];W[ni];B[oj];W[ki];B[li];W[mj];B[lj];W[pk];B[ok];W[lc];B[ma];W[md];B[nd];W[id];B[rh];W[rj];B[qk];W[pl];B[rk];W[sh];B[ol];W[pm];B[rh];W[qp];B[sj];W[po];B[qq];W[rq];B[qo];W[rp];B[pq];W[qn];B[oo];W[ro];B[gj];W[hl];B[jd];W[hd];B[jc];W[je];B[le];W[if];B[jf];W[he];B[kf];W[kd];B[kb];W[lf];B[me];W[hh];B[ih];W[gh];B[ii];W[gi];B[hj];W[fj];B[hf];W[ie];B[hg];W[gg];B[fk];W[ej];B[ek];W[di];B[gk];W[dk];B[cj];W[dl];B[gf];W[ei];B[ff];W[ci];B[bi];W[bj];B[ce];W[de];B[cd];W[dd];B[bf];W[jl];B[cc];W[cb];B[bb];W[mq];B[np];W[nn];B[mp];W[lq];B[lp];W[kp];B[nq];W[hq];B[rr];W[bp];B[bq];W[aq];B[ar];W[ap];B[bs];W[ko];B[hr];W[iq];B[bh];W[ck];B[db];W[eb];B[ca];W[ll];B[mk];W[hb];B[ir]
)"""
    },
    {
        "title": "第8届扇兴杯世界女子最强战8强 藤泽里菜执白中盘胜杨子萱",
        "filename": "2026031350795502_fuzelinai_vs_yangzixuan.sgf",
        "sgf": """(;GM[1]FF[4]
SZ[19]
GN[第8届扇兴杯世界女子最强战8强<绝艺讲解>]
DT[2026-03-13]
PB[杨子萱]
PW[藤沢里菜]
BR[P6段]
WR[P7段]
KM[650]HA[0]RU[Japanese]AP[GNU Go:3.8]RE[W+R]TM[7200]TC[5]TT[60]AP[foxwq]RL[0]
;B[qd];W[dc];B[dq];W[pp];B[de];W[ce];B[cf];W[cd];B[df];W[fc];B[cn];W[od];B[oc];W[nc];B[pc];W[nd];B[qf];W[ge];B[dj];W[nq];B[kd];W[ng];B[of];W[nf];B[kf];W[ph];B[qn];W[qo];B[pn];W[pk];B[mn];W[mp];B[ip];W[nl];B[ml];W[mk];B[ll];W[nm];B[nn];W[lk];B[kl];W[kk];B[jl];W[je];B[jd];W[ie];B[lc];W[ic];B[id];W[hd];B[ke];W[bn];B[bo];W[co];B[bp];W[dk];B[cj];W[fk];B[ek];W[el];B[ej];W[eo];B[ep];W[fo];B[fp];W[kp];B[go];W[gn];B[hn];W[cm];B[dn];W[dm];B[bm];W[hm];B[in];W[ck];B[dd];W[cc];B[jq];W[bj];B[bi];W[jg];B[ib];W[hc];B[mb];W[nb];B[jb];W[qg];B[rf];W[jc];B[kc];W[ka];B[la];W[qb];B[pb];W[pa];B[rb];W[me];B[jf];W[if];B[kg];W[kh];B[lh];W[jh];B[mg];W[nh];B[hb];W[gb];B[oe];W[ne];B[ha];W[rc];B[qc];W[ra];B[qa];W[na];B[ja];W[qb];B[qh];W[pg];B[qa];W[ma];B[lb];W[qb];B[rg];W[qi];B[qa];W[bh];B[bk];W[qb];B[rh];W[sb];B[ri];W[rj];B[rd];W[qk];B[si];W[bl];B[aj];W[am];B[bf];W[do];B[fn];W[gm];B[lr];W[ho];B[gp];W[jn];B[im];W[mm];B[ln];W[jo];B[op];W[oq];B[lm];W[oo];B[po];W[qp];B[om];W[io];B[lq];W[lp];B[ro];W[rp];B[no];W[np];B[jk];W[li];B[jj];W[mh];B[lg];W[hh];B[rm];W[rl];B[gi];W[hp];B[hq];W[en]
)"""
    },
    {
        "title": "第8届扇兴杯世界女子最强战8强 上野爱咲美执白中盘胜唐萨姆",
        "filename": "2026031343947660_shangyeaixiaomei_vs_tangsamu.sgf",
        "sgf": """(;GM[1]FF[4]
SZ[19]
GN[第8届扇兴杯世界女子最强战8强<绝艺讲解>]
DT[2026-03-13]
PB[DawnSum]
PW[上野愛咲美]
BR[9段]
WR[P6段]
KM[650]HA[0]RU[Japanese]AP[GNU Go:3.8]RE[W+R]TM[7200]TC[5]TT[60]AP[foxwq]RL[0]
;B[pd];W[dp];B[qp];W[dc];B[np];W[fp];B[ce];W[di];B[ed];W[ec];B[fd];W[gb];B[qf];W[lq];B[ck];W[cg];B[bp];W[ef];B[cc];W[dd];B[cd];W[de];B[cf];W[bg];B[cb];W[cm];B[cq];W[dq];B[bn];W[bm];B[co];W[dm];B[dn];W[em];B[ff];W[fg];B[gg];W[cr];B[br];W[dr];B[bs];W[gf];B[fe];W[eg];B[hf];W[gh];B[hg];W[hh];B[fo];W[go];B[lp];W[kp];B[mq];W[lo];B[mp];W[pp];B[pq];W[ko];B[eo];W[gn];B[pk];W[jg];B[jf];W[kf];B[je];W[ke];B[kd];W[ld];B[jd];W[me];B[kg];W[ig];B[kh];W[if];B[he];W[ie];B[id];W[hd];B[ge];W[ji];B[hc];W[kc];B[jb];W[pc];B[lc];W[mc];B[lb];W[mb];B[kb];W[qd];B[oc];W[od];B[pe];W[qc];B[nd];W[ob];B[oe];W[md];B[ki];W[jj];B[lk];W[mg];B[lf];W[le];B[nh];W[qo];B[rp];W[og];B[nf];W[ng];B[mf];W[lg];B[qh];W[pi];B[ph];W[oh];B[ne];W[nc];B[ma];W[nb];B[oi];W[mi];B[ni];W[oq];B[po];W[op];B[oo];W[mj];B[kj];W[mk];B[ml];W[ll];B[kl];W[lm];B[mm];W[oj];B[pj];W[jk];B[kk];W[jl];B[km];W[ln];B[jm];W[im];B[jn];W[in];B[jo];W[jp];B[io];W[ip];B[qi];W[nj];B[ok];W[ho];B[nk];W[jh]
)"""
    },
    {
        "title": "衢州葛道职业训练赛 刘云程执白中盘胜张歆宇",
        "filename": "2026031336713449_liuyuncheng_vs_zhangxinyu.sgf",
        "sgf": """(;GM[1]FF[4]
SZ[19]
GN[衢州葛道职业训练赛<绝艺讲解>]
DT[2026-03-13]
PB[张歆宇]
PW[刘云程]
BR[P5段]
WR[P4段]
KM[375]HA[0]RU[Chinese]AP[GNU Go:3.8]RE[W+R]TM[3600]TC[3]TT[30]AP[foxwq]RL[0]
;B[qd];W[dp];B[pq];W[dc];B[qn];W[od];B[oc];W[nc];B[pc];W[nd];B[pf];W[jd];B[de];W[cg];B[cc];W[fd];B[cd];W[ef];B[ec];W[fc];B[eb];W[fq];B[gp];W[pp];B[qp];W[oq];B[po];W[op];B[pr];W[qq];B[or];W[mq];B[rq];W[jp];B[fp];W[ep];B[gq];W[fr];B[gm];W[dm];B[ck];W[dk];B[dj];W[ek];B[ch];W[dh];B[ci];W[cl];B[bg];W[im];B[gk];W[fn];B[gn];W[ho];B[go];W[ik];B[io];W[ip];B[jo];W[ko];B[jn];W[km];B[ej];W[fk];B[gj];W[fj];B[ij];W[gi];B[jk];W[il];B[hj];W[jj];B[kk];W[kn];B[fl];W[ji];B[ih];W[fi];B[kg];W[lj];B[hg];W[if];B[jh];W[of];B[le];W[pe];B[qe];W[lh];B[kd];W[jc];B[kc];W[lg];B[je];W[jf];B[kf];W[ie];B[jb];W[ib];B[lb];W[mb];B[hp];W[hc];B[jr];W[jq];B[eo];W[gr];B[hr];W[iq];B[do];W[co];B[cn];W[bp];B[ki];W[kj];B[li];W[mi];B[kh];W[mj];B[mh];W[pg];B[qf];W[nh];B[mg];W[ng];B[mf];W[hn];B[bo];W[cp];B[dn];W[em];B[fm];W[hh];B[ii];W[ig];B[hq];W[ir];B[is];W[kr];B[bk];W[qg];B[pj];W[nk];B[oi];W[ni];B[ol];W[rf];B[re];W[rh];B[rj];W[qb];B[ob];W[lc]
)"""
    }
]

# 保存棋谱
success_count = 0
failed = []

for game in games:
    filepath = os.path.join(OUTPUT_DIR, game["filename"])
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(game["sgf"])
        print(f"✓ 保存成功: {game['filename']}")
        print(f"  标题: {game['title']}")
        success_count += 1
    except Exception as e:
        print(f"✗ 保存失败: {game['filename']} - {e}")
        failed.append(game["filename"])

print(f"\n{'='*50}")
print(f"下载完成!")
print(f"成功: {success_count} 局")
print(f"失败: {len(failed)} 局")
if failed:
    print(f"失败文件: {', '.join(failed)}")
print(f"保存路径: {OUTPUT_DIR}")
