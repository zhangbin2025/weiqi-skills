#!/usr/bin/env python3
"""
云比赛网数据查询工具 - 带性能跟踪
支持：比赛列表、分组信息、对阵数据、排名计算
"""

import requests
import json
import time
import sys
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PerfTimer:
    """性能计时器"""
    name: str
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    
    def stop(self) -> float:
        """停止计时并返回耗时（秒）"""
        self.end_time = time.perf_counter()
        return self.elapsed()
    
    def elapsed(self) -> float:
        """获取已耗时（秒）"""
        end = self.end_time or time.perf_counter()
        return end - self.start_time


@dataclass
class PerfReport:
    """性能报告"""
    timers: List[PerfTimer] = field(default_factory=list)
    total_start: float = field(default_factory=time.perf_counter)
    
    def start(self, name: str) -> PerfTimer:
        """开始一个新的计时器"""
        timer = PerfTimer(name)
        self.timers.append(timer)
        return timer
    
    def summary(self) -> str:
        """生成性能报告摘要"""
        total_elapsed = time.perf_counter() - self.total_start
        step_total = sum(t.elapsed() for t in self.timers)
        
        lines = [
            "\n" + "=" * 50,
            "⏱️  性能计时报告",
            "=" * 50,
        ]
        
        for timer in self.timers:
            elapsed = timer.elapsed()
            percentage = (elapsed / total_elapsed * 100) if total_elapsed > 0 else 0
            lines.append(f"  {timer.name:25} : {elapsed:8.3f}s ({percentage:5.1f}%)")
        
        lines.extend([
            "-" * 50,
            f"  {'步骤累计':25} : {step_total:8.3f}s",
            f"  {'总耗时':25} : {total_elapsed:8.3f}s",
            "=" * 50,
        ])
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict:
        """转为字典格式"""
        total_elapsed = time.perf_counter() - self.total_start
        return {
            "total_seconds": round(total_elapsed, 3),
            "steps": [
                {"name": t.name, "seconds": round(t.elapsed(), 3)}
                for t in self.timers
            ]
        }


class YunbisaiClient:
    """云比赛网 API 客户端（带性能跟踪）"""
    
    BASE_URL = "https://data-center.yunbisai.com/api"
    OPEN_URL = "https://open.yunbisai.com/api"
    API_URL = "https://api.yunbisai.com"
    
    def __init__(self, verbose: bool = True):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.yunbisai.com/"
        })
        self.verbose = verbose
        self.perf = PerfReport()
    
    def _log(self, msg: str):
        """打印日志"""
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    
    def _request(self, url: str, params: Dict = None) -> Dict:
        """发送请求并返回JSON"""
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_events(self, area: str = "广东省", month: int = 1, 
                   event_type: int = 2, page_size: int = 50) -> Tuple[List[Dict], Dict]:
        """
        获取比赛列表
        
        Returns:
            (events_list, perf_info)
        """
        timer = self.perf.start("获取比赛列表")
        self._log(f"正在获取比赛列表: area={area}, month={month}")
        
        all_events = []
        page = 1
        total_pages = 1
        
        while page <= total_pages:
            url = f"{self.BASE_URL}/lswl-events"
            params = {
                "page": page,
                "eventType": event_type,
                "month": month,
                "areaNum": area,
                "PageSize": page_size
            }
            
            try:
                data = self._request(url, params)
                if data.get("error") == 0:
                    rows = data.get("datArr", {}).get("rows", [])
                    all_events.extend(rows)
                    
                    total_pages = data.get("datArr", {}).get("TotalPage", 1)
                    self._log(f"  获取第 {page}/{total_pages} 页，本页 {len(rows)} 条数据")
                    
                    if page >= total_pages:
                        break
                    page += 1
                else:
                    break
            except Exception as e:
                self._log(f"  请求失败: {e}")
                break
        
        elapsed = timer.stop()
        self._log(f"✓ 共获取 {len(all_events)} 场比赛，耗时 {elapsed:.3f}s")
        
        return all_events, {"count": len(all_events), "seconds": round(elapsed, 3)}
    
    def get_groups_from_html(self, event_id: int) -> List[Dict]:
        """
        从 HTML 页面解析分组信息（API 403 时的备用方案）
        
        Returns:
            groups_list
        """
        url = f"https://www.yunbisai.com/tpl/eventFeatures/eventDetail-{event_id}.html"
        self._log(f"  尝试从 HTML 解析分组: {url}")
        
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            content = response.text
            
            # 解析 HTML 中的分组数据
            # 格式1: <li data-groupname="..."><a ... data-groupid="...">
            # 格式2: <a ... data-groupname="..." data-groupid="...">
            import re
            groups = []
            
            # 查找所有分组条目（支持两种格式）
            # 格式1: li 标签上有 groupname，a 标签上有 groupid
            # 注意：正则返回 (groupname, groupid)
            pattern1 = r'<li[^>]*data-groupname="([^"]+)"[^>]*>[^<]*<a[^>]*data-groupid="(\d+)"'
            matches1 = re.findall(pattern1, content, re.DOTALL)
            
            # 格式2: a 标签上同时有 groupname 和 groupid
            pattern2 = r'<a[^>]*data-groupname="([^"]+)"[^>]*data-groupid="(\d+)"'
            matches2 = re.findall(pattern2, content, re.DOTALL)
            
            matches = matches1 + matches2
            
            # 去重（可能会有重复）
            seen = set()
            for group_name, group_id in matches:
                if group_id not in seen:
                    seen.add(group_id)
                    groups.append({
                        "group_id": int(group_id),
                        "groupname": group_name.strip(),
                        "event_id": event_id
                    })
            
            if groups:
                self._log(f"  ✓ 从 HTML 解析到 {len(groups)} 个分组")
                return groups
            else:
                self._log(f"  未从 HTML 中找到分组数据")
                return []
        except Exception as e:
            self._log(f"  HTML 解析失败: {e}")
            return []
    
    def get_groups(self, event_id: int) -> Tuple[List[Dict], Dict]:
        """
        获取比赛分组信息（支持 API 和 HTML 双模式）
        
        Returns:
            (groups_list, perf_info)
        """
        timer = self.perf.start("获取分组信息")
        self._log(f"正在获取比赛分组: event_id={event_id}")
        
        url = f"{self.OPEN_URL}/event/feel/list"
        params = {
            "event_id": event_id,
            "page": 1,
            "pagesize": 500
        }
        
        try:
            response = self.session.get(url, params=params, timeout=30)
            
            # 如果返回 403，尝试从 HTML 解析
            if response.status_code == 403:
                self._log(f"  API 返回 403，尝试从 HTML 页面解析...")
                groups = self.get_groups_from_html(event_id)
                elapsed = timer.stop()
                return groups, {"count": len(groups), "seconds": round(elapsed, 3), "source": "html"}
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("error") == 0:
                rows = data.get("datArr", {}).get("rows", [])
                elapsed = timer.stop()
                self._log(f"✓ 共获取 {len(rows)} 个分组，耗时 {elapsed:.3f}s")
                return rows, {"count": len(rows), "seconds": round(elapsed, 3), "source": "api"}
        except Exception as e:
            self._log(f"  API 请求失败: {e}")
            # API 失败，尝试 HTML
            self._log(f"  尝试从 HTML 页面解析...")
            groups = self.get_groups_from_html(event_id)
            elapsed = timer.stop()
            return groups, {"count": len(groups), "seconds": round(elapsed, 3), "source": "html"}
        
        elapsed = timer.stop()
        return [], {"count": 0, "seconds": round(elapsed, 3)}
    
    def get_group_players(self, event_id: int, group_id: int) -> Tuple[List[Dict], Dict]:
        """
        获取分组选手列表
        
        Returns:
            (players_list, perf_info)
        """
        timer = self.perf.start("获取分组选手")
        self._log(f"正在获取分组选手: event_id={event_id}, group_id={group_id}")
        
        url = f"{self.OPEN_URL}/event/feel/list"
        params = {
            "event_id": event_id,
            "group_id": group_id,
            "page": 1,
            "pagesize": 200
        }
        
        try:
            data = self._request(url, params)
            if data.get("error") == 0:
                rows = data.get("datArr", {}).get("rows", [])
                elapsed = timer.stop()
                self._log(f"✓ 共获取 {len(rows)} 名选手，耗时 {elapsed:.3f}s")
                return rows, {"count": len(rows), "seconds": round(elapsed, 3)}
        except Exception as e:
            self._log(f"  请求失败: {e}")
        
        elapsed = timer.stop()
        return [], {"count": 0, "seconds": round(elapsed, 3)}
    
    def get_against_plan(self, group_id: int, bout: int) -> Tuple[Optional[Dict], Dict]:
        """
        获取某轮对阵表
        
        Returns:
            (match_data, perf_info)
        """
        timer = self.perf.start(f"获取第{bout}轮对阵")
        
        url = f"{self.API_URL}/request/Group/Againstplan"
        params = {"groupid": group_id, "bout": bout}
        
        try:
            data = self._request(url, params)
            if data.get("error") == 0:
                timer.stop()
                return data.get("datArr", {}), {"seconds": round(timer.elapsed(), 3)}
        except Exception as e:
            self._log(f"  请求失败: {e}")
        
        timer.stop()
        return None, {"seconds": round(timer.elapsed(), 3)}
    
    def get_all_rounds(self, group_id: int) -> Tuple[List[Dict], int, Dict]:
        """
        获取分组所有轮次对阵
        
        Returns:
            (all_matches, total_bouts, perf_info)
        """
        timer = self.perf.start("获取所有轮次对阵")
        self._log(f"正在获取分组所有轮次对阵: group_id={group_id}")
        
        all_matches = []
        
        # 先获取第1轮，得到总轮数
        first_round, _ = self.get_against_plan(group_id, 1)
        if not first_round:
            elapsed = timer.stop()
            return [], 0, {"count": 0, "seconds": round(elapsed, 3)}
        
        total_bouts = int(first_round.get("total_bout", 0) or 0)
        all_matches.extend(first_round.get("rows", []))
        
        self._log(f"  总轮数: {total_bouts}")
        
        # 获取剩余轮次
        for bout in range(2, total_bouts + 1):
            round_data, _ = self.get_against_plan(group_id, bout)
            if round_data:
                all_matches.extend(round_data.get("rows", []))
        
        elapsed = timer.stop()
        self._log(f"✓ 共获取 {len(all_matches)} 场对局（{total_bouts}轮），耗时 {elapsed:.3f}s")
        
        return all_matches, total_bouts, {"count": len(all_matches), "rounds": total_bouts, "seconds": round(elapsed, 3)}
    
    def calculate_ranking(self, matches: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        根据对阵数据计算排名
        
        Returns:
            (rankings, perf_info)
        """
        timer = self.perf.start("计算排名")
        self._log("正在计算排名...")
        
        players = {}
        
        # 初始化选手
        for match in matches:
            for key, name_key, team_key in [
                ('p1id', 'p1', 'p1_teamname'),
                ('p2id', 'p2', 'p2_teamname')
            ]:
                pid = match.get(key)
                name = match.get(name_key)
                team = match.get(team_key) or ''
                if pid and name and pid not in players:
                    players[pid] = {
                        'id': pid,
                        'name': name,
                        'team': team,
                        'wins': 0,
                        'losses': 0,
                        'draws': 0,
                        'score': 0,
                        'opponents': [],
                        'progressive': []
                    }
        
        # 逐轮解析
        for match in matches:
            p1_id = match.get('p1id')
            p2_id = match.get('p2id')
            p1_score = float(match.get('p1_score') or 0)
            p2_score = float(match.get('p2_score') or 0)
            
            # 处理p1
            if p1_id and p1_id in players:
                if p2_id and match.get('p2') and p2_id in players:
                    players[p1_id]['opponents'].append(p2_id)
                if p1_score == 2.0:
                    players[p1_id]['wins'] += 1
                elif p1_score == 0.0:
                    players[p1_id]['losses'] += 1
                else:
                    players[p1_id]['draws'] += 1
                players[p1_id]['score'] += p1_score
                players[p1_id]['progressive'].append(players[p1_id]['score'])
            
            # 处理p2
            if p2_id and p2_id in players:
                if p1_id and match.get('p1') and p1_id in players:
                    players[p2_id]['opponents'].append(p1_id)
                if p2_score == 2.0:
                    players[p2_id]['wins'] += 1
                elif p2_score == 0.0:
                    players[p2_id]['losses'] += 1
                else:
                    players[p2_id]['draws'] += 1
                players[p2_id]['score'] += p2_score
                players[p2_id]['progressive'].append(players[p2_id]['score'])
        
        # 计算对手分和累进分
        for pid, p in players.items():
            p['opponent_score'] = sum(
                players[oid]['score'] for oid in p['opponents'] if oid in players
            )
            p['progressive_score'] = sum(p['progressive'])
        
        # 排序：个人积分 > 对手分 > 累进分
        sorted_players = sorted(
            players.values(),
            key=lambda x: (x['score'], x['opponent_score'], x['progressive_score']),
            reverse=True
        )
        
        elapsed = timer.stop()
        self._log(f"✓ 排名计算完成（{len(sorted_players)}名选手），耗时 {elapsed:.3f}s")
        
        return sorted_players, {"count": len(sorted_players), "seconds": round(elapsed, 3)}
    
    def print_ranking(self, rankings: List[Dict], top_n: int = None):
        """打印排名表"""
        print("\n" + "=" * 70)
        print(f"{'排名':<6}{'姓名':<12}{'积分':<8}{'对手分':<10}{'累进分':<10}{'战绩':<12}")
        print("-" * 70)
        
        for i, p in enumerate(rankings[:top_n] if top_n else rankings, 1):
            record = f"{p['wins']}胜{p['losses']}负"
            if p['draws'] > 0:
                record += f"{p['draws']}和"
            print(f"{i:<6}{p['name']:<12}{int(p['score']):<8}{int(p['opponent_score']):<10}{int(p['progressive_score']):<10}{record:<12}")
        
        print("=" * 70)
    
    def print_perf_report(self):
        """打印性能报告"""
        print(self.perf.summary())
    
    def get_perf_dict(self) -> Dict:
        """获取性能数据字典"""
        return self.perf.to_dict()


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='云比赛网数据查询工具')
    parser.add_argument('--event-id', '-e', type=int, help='比赛ID')
    parser.add_argument('--group-id', '-g', type=int, help='分组ID')
    parser.add_argument('--area', '-a', default='广东省', help='地区（默认：广东省）')
    parser.add_argument('--month', '-m', type=int, default=1, help='最近多少个月（默认：1）')
    parser.add_argument('--ranking', '-r', action='store_true', help='计算排名')
    parser.add_argument('--json', '-j', action='store_true', help='输出JSON格式')
    parser.add_argument('--quiet', '-q', action='store_true', help='静默模式（减少输出）')
    
    args = parser.parse_args()
    
    client = YunbisaiClient(verbose=not args.quiet)
    result = {"status": "ok", "data": {}}
    
    try:
        # 查询比赛列表
        if not args.event_id:
            events, perf = client.get_events(area=args.area, month=args.month)
            result["data"]["events"] = events
            result["data"]["_perf"] = perf
            
            if not args.json:
                print(f"\n找到 {len(events)} 场比赛：")
                for e in events[:10]:  # 只显示前10场
                    print(f"  [{e.get('event_id')}] {e.get('title')} - {e.get('city_name')}")
                if len(events) > 10:
                    print(f"  ... 还有 {len(events) - 10} 场")
        
        # 查询分组
        elif args.event_id and not args.group_id:
            groups, perf = client.get_groups(args.event_id)
            result["data"]["groups"] = groups
            result["data"]["_perf"] = perf
            
            if not args.json:
                print(f"\n比赛 {args.event_id} 共有 {len(groups)} 个分组：")
                for g in groups:
                    print(f"  [{g.get('group_id')}] {g.get('groupname')} - {g.get('participantname')} 排名: {g.get('rank_num')}")
        
        # 查询对阵并计算排名
        elif args.group_id:
            if args.ranking:
                matches, total_bouts, perf_matches = client.get_all_rounds(args.group_id)
                rankings, perf_ranking = client.calculate_ranking(matches)
                
                result["data"]["rankings"] = rankings
                result["data"]["total_bouts"] = total_bouts
                result["data"]["_perf"] = {
                    "matches": perf_matches,
                    "ranking": perf_ranking
                }
                
                if not args.json:
                    client.print_ranking(rankings)
            else:
                players, perf = client.get_group_players(args.event_id, args.group_id)
                result["data"]["players"] = players
                result["data"]["_perf"] = perf
                
                if not args.json:
                    print(f"\n分组 {args.group_id} 共有 {len(players)} 名选手：")
                    for p in players[:10]:
                        print(f"  {p.get('participantname')} - 排名: {p.get('rank_num')}, 积分: {p.get('integral')}")
        
        # 输出性能报告
        if not args.json and not args.quiet:
            client.print_perf_report()
        
        # JSON输出
        if args.json:
            result["_perf_summary"] = client.get_perf_dict()
            print(json.dumps(result, ensure_ascii=False, indent=2))
    
    except Exception as e:
        result = {"status": "error", "message": str(e)}
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(f"错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
