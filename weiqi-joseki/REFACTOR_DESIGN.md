# weiqi-joseki 模块化重构设计文档

## 一、现有代码分析

当前 `db.py` 约2000行，包含以下混杂的功能模块：

| 模块 | 代码行数 | 功能 |
|------|----------|------|
| KataGo下载器 | ~400行 | 内存监控、进度管理、下载管理、处理器 |
| 坐标系统 | ~150行 | 8方向坐标系定义和转换 |
| 数据类 | ~50行 | Move, MatchResult, ConflictCheck |
| 数据库核心 | ~600行 | JosekiDB类的CRUD、匹配、生成8向 |
| 定式提取 | ~250行 | extract_joseki_from_sgf及相关函数 |
| CLI命令 | ~400行 | 各命令的处理函数 |

## 二、重构目标架构

```
weiqi-joseki/
├── scripts/
│   ├── sgf_parser.py          # 从weiqi-sgf拷贝，统一解析器（自带单元测试）
│   ├── joseki_extractor.py    # 定式提取核心功能
│   ├── katago_downloader.py   # KataGo下载功能（独立模块）
│   ├── joseki_db.py           # 定式库管理（含定式提取入库功能）
│   ├── cli.py                 # 命令行入口
│   └── tests/
│       ├── test_joseki_extractor.py
│       ├── test_katago_downloader.py
│       └── test_joseki_db.py
├── db.py                      # 兼容性入口（导入cli.main）
└── SKILL.md
```

## 三、模块详细设计

### 3.1 sgf_parser.py

**来源**: 从 `weiqi-sgf/scripts/sgf_parser.py` 拷贝

**对外接口**:
```python
def parse_sgf(sgf_content: str) -> dict
    """解析SGF内容，返回树状结构"""

def parse_sgf_file(filepath: str) -> dict
    """解析SGF文件"""
```

**修改点**: 保持原样，仅拷贝使用

---

### 3.2 joseki_extractor.py

**职责**: 从SGF中提取定式，处理角序列，生成MULTIGOGM格式

**核心函数**:
```python
def extract_joseki_from_sgf(sgf_data: str, first_n: int = 50, corner: str = None) -> str:
    """
    从SGF提取四角定式，输出MULTIGOGM格式
    
    Args:
        sgf_data: SGF棋谱内容（原始字符串或解析后的树）
        first_n: 只取前N手（默认50）
        corner: 指定提取哪个角 ('tl', 'tr', 'bl', 'br')，None表示全部
    
    Returns:
        MULTIGOGM格式的SGF字符串
    """

def extract_joseki_from_tree(tree: dict, first_n: int = 50, corner: str = None) -> str:
    """
    从已解析的SGF树中提取定式
    （新增，直接使用sgf_parser解析结果，避免重复解析）
    """

def process_corner_sequence(moves: List[Tuple[str, str]], corner_desc: str, corner_key: str) -> Optional[Tuple[str, List[Tuple[str, str]]]]:
    """
    处理单角序列，检测脱先，转换为右上角坐标，标准化为黑先
    
    Args:
        moves: [(color, sgf_coord), ...]
        corner_desc: 角的描述（如"左上")
        corner_key: 角的键名 ('tl', 'tr', 'bl', 'br')
    
    Returns:
        (comment, [(color, coord), ...]) 或 None
    """

def format_multigogm(branches: List[Tuple[str, List[Tuple[str, str]]]]) -> str:
    """生成MULTIGOGM格式的SGF"""

def parse_multigogm(sgf_data: str) -> Dict[str, Tuple[str, List[Tuple[str, str]]]]:
    """
    解析MULTIGOGM格式的SGF
    
    Returns:
        {corner_key: (comment, [(color, coord), ...]), ...}
    """

def detect_corner(moves: List[str]) -> Optional[str]:
    """
    检测定式属于哪个角
    返回: 'tl', 'tr', 'bl', 'br' 或 None
    """

def convert_to_top_right(moves: List[str], source_corner: str) -> List[str]:
    """
    将定式坐标转换为右上角（视觉）的坐标
    """
```

**依赖**: sgf_parser.py (用于extract_joseki_from_tree)

---

### 3.3 katago_downloader.py

**职责**: 从KataGo Archive下载棋谱（独立模块，不涉及定式提取）

**核心类**:
```python
class MemoryMonitor:
    """内存监控器"""
    def __init__(self, max_memory_mb: int)
    def get_memory_mb(self) -> float
    def check(self) -> Tuple[str, float]  # ('ok'|'warning'|'critical', memory_mb)
    def force_gc(self)

class ProgressManager:
    """进度管理器（断点续传）"""
    def __init__(self, progress_file: Path)
    def save(self)
    def is_completed(self, date_str: str) -> bool
    def mark_completed(self, date_str: str, stats: dict)
    def update_count_map(self, count_map: dict)
    def get_count_map(self) -> dict
    def clear(self)

class DownloadManager:
    """下载管理器（支持重试、进度显示、404检测）"""
    def __init__(self, cache_dir: Path, max_retries: int = 3, workers: int = 3)
    def download(self, dates: List[str]) -> Dict[str, Path]
    def download_single(self, date_str: str) -> Tuple[str, Optional[Path], Optional[str]]
        """
        下载单个日期文件
        
        Returns:
            (date_str, file_path, error)
            error为None表示成功，为"404"表示文件不存在（也算成功），其他为错误信息
        """
    def check_file_exists(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        检查远程文件是否存在
        
        Returns:
            (exists, error)
            exists: True表示存在，False表示404或其他错误
        """
    def stop(self)
    def is_stopped(self) -> bool
    
    # 新增：保留缓存选项
    def set_keep_cache(self, keep: bool)

# 便捷函数 - 只做下载，不做提取
def download_katago_games(
    start_date: str,
    end_date: str,
    cache_dir: Optional[Path] = None,
    max_retries: int = 3,
    workers: int = 3,
    keep_cache: bool = True,  # 默认保留缓存
    resume: bool = False,
    on_progress: Optional[Callable[[str, int, int], None]] = None  # (date_str, current, total)
) -> Tuple[List[Path], List[str]]:
    """
    下载KataGo棋谱文件
    
    Returns:
        (downloaded_files, missing_dates)
        downloaded_files: 成功下载的文件路径列表
        missing_dates: 文件不存在的日期列表（404）
    """

def iter_sgf_from_tar(tar_path: Path) -> Iterator[str]:
    """
    从tar.bz2文件中迭代读取SGF内容
    
    Yields:
        SGF字符串
    """
    # 流式解压，不解压整个文件
```

**依赖**: 无（独立下载模块，不涉及定式提取）

**功能改进1 - 404检测**:
```python
def check_file_exists(self, url: str) -> Tuple[bool, Optional[str]]:
    """检查文件是否存在"""
    try:
        req = urllib.request.Request(url, method='HEAD', headers={...})
        with urllib.request.urlopen(req, timeout=30) as response:
            return True, None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, None  # 文件不存在，不算错误
        return False, str(e)
    except Exception as e:
        return False, str(e)

def download_single(self, date_str: str) -> Tuple[str, Optional[Path], Optional[str]]:
    url = f"{KATAGO_BASE_URL}{date_str}rating.tar.bz2"
    output_path = self.cache_dir / f"{date_str}rating.tar.bz2"
    
    # 先检查文件是否存在
    exists, error = self.check_file_exists(url)
    if not exists:
        if error is None:
            # 404，文件不存在，算成功但不下载
            return date_str, None, "404"
        else:
            return date_str, None, error
    
    # 文件存在，执行下载...
```

**功能改进2 - 保留缓存**:
- 默认 `keep_cache=True`
- 在 `__init__` 和 `download_and_extract` 中设置
- 只在明确指定 `keep_cache=False` 时删除

---

### 3.4 joseki_db.py

**职责**: 定式库管理、匹配、8向生成、导出，以及从棋谱批量导入定式

**核心类**:
```python
class JosekiDB:
    def __init__(self, db_path: Optional[str] = None)
    
    # CRUD
    def add(self, name: str = "", category_path: str = "", 
            moves: List[str] = None, tags: List[str] = None, 
            description: str = "", force: bool = False) -> Tuple[Optional[str], Optional[ConflictCheck]]
    def remove(self, joseki_id: str) -> bool
    def clear(self) -> int
    def get(self, joseki_id: str) -> Optional[dict]
    def list_all(self, category: str = None) -> List[dict]
    
    # 冲突检测和匹配
    def check_conflict(self, moves: List[str]) -> ConflictCheck
    def match(self, moves: List[str], top_k: int = 5, min_similarity: float = 0.5) -> List[MatchResult]
    def match_top_right(self, moves: List[str], top_k: int = 5, min_similarity: float = 0.5) -> List[MatchResult]
    def identify_corners(self, sgf_data: str, top_k: int = 3, first_n: int = 80) -> Dict[str, List[MatchResult]]
    
    # 8向生成（功能改进：支持指定方向）
    def generate_8way_sgf(self, joseki_id: str, directions: Optional[List[str]] = None) -> Optional[str]:
        """
        生成8向变化SGF
        
        Args:
            joseki_id: 定式ID
            directions: 指定方向列表，如 ['ruld', 'rudl']，None表示全部8个方向
        
        Returns:
            MULTIGOGM格式的SGF字符串
        """
    
    def generate_variations(self, moves: List[str], directions: Optional[List[str]] = None) -> List[dict]:
        """
        生成指定方向的变化
        
        Args:
            moves: 着法序列
            directions: 方向列表，None表示全部8个方向
        """
    
    # 从棋谱导入定式（从原katago处理器迁移过来，也用于批量导入SGF目录）
    def import_from_sgfs(self,
                        sgf_sources: List[Union[str, Path]],
                        min_count: int = 10,
                        min_moves: int = 4,
                        min_rate: float = 0.0,
                        first_n: int = 50,
                        dry_run: bool = False,
                        progress_callback: Optional[Callable] = None) -> Tuple[int, int, List[str]]:
        """
        从SGF文件列表批量导入定式
        
        Args:
            sgf_sources: SGF文件路径列表，或包含SGF内容的字符串列表（自动识别）
            min_count: 最少出现次数才入库
            min_moves: 定式至少多少手
            min_rate: 最小出现概率%
            first_n: 每谱提取前N手内的定式
            dry_run: 试运行，只统计不真入库
            progress_callback: 进度回调函数(current, total)
        
        Returns:
            (added_count, skipped_count, candidates_list)
        """
    
    def import_from_katago_cache(self,
                                  cache_dir: Path,
                                  min_count: int = 10,
                                  min_moves: int = 4,
                                  min_rate: float = 0.5,
                                  first_n: int = 50,
                                  dry_run: bool = False) -> Tuple[int, int]:
        """
        从KataGo缓存目录导入定式
        
        Args:
            cache_dir: KataGo棋谱缓存目录
            其他参数同上
        
        Returns:
            (added_count, skipped_count)
        """
    
    # 导出（新增功能，支持过滤）
    def export_to_sgf(self, 
                      output_path: Optional[str] = None,
                      category: Optional[str] = None,
                      min_moves: Optional[int] = None,
                      max_moves: Optional[int] = None,
                      tags: Optional[List[str]] = None,
                      ids: Optional[List[str]] = None) -> str:
        """
        将定式库导出到一个SGF文件，支持多种过滤条件
        
        Args:
            output_path: 输出文件路径，None则返回SGF字符串
            category: 按分类路径过滤（前缀匹配）
            min_moves: 最少手数
            max_moves: 最多手数
            tags: 包含任一指定标签
            ids: 指定定式ID列表
        
        Returns:
            MULTIGOGM格式的SGF字符串
        """
    
    # 统计
    def stats(self) -> dict
    
    # 工具方法
    @staticmethod
    def normalize_moves(moves: List[str], ignore_pass: bool = True) -> List[str]
    @staticmethod
    def lcs_similarity(seq1: List[str], seq2: List[str]) -> float
    @staticmethod
    def detect_corner(moves: List[str]) -> Optional[str]
    @staticmethod
    def convert_to_top_right(moves: List[str], source_corner: str) -> List[str]
```

**依赖**: joseki_extractor.py (用于identify_corners)

**功能改进 - 指定方向的8way**:
```python
def generate_8way_sgf(self, joseki_id: str, directions: Optional[List[str]] = None) -> Optional[str]:
    # ...获取定式和着法...
    
    # 如果只指定部分方向
    if directions is not None:
        all_variations = self.generate_variations(stored_moves)
        variations = [v for v in all_variations if v['direction'] in directions]
    else:
        variations = self.generate_variations(stored_moves)
    
    # ...生成SGF...
```

**新增功能 - 从棋谱批量导入**:
```python
def import_from_sgfs(self, sgf_sources, min_count=10, min_moves=4, 
                     min_rate=0.0, first_n=50, dry_run=False):
    """
    从SGF文件/内容列表导入定式
    流程：
    1. 用Hash表统计所有定式出现次数（去重）
    2. 排序后前缀累加统计频率
    3. 按条件筛选入库
    """
    count_map = {}  # {joseki_str: count}
    
    # 1. 提取所有定式
    for source in sgf_sources:
        if isinstance(source, Path):
            sgf_data = source.read_text()
        else:
            sgf_data = source
        
        # 使用 joseki_extractor 提取四角定式
        multigogm = extract_joseki_from_sgf(sgf_data, first_n=first_n)
        parsed = parse_multigogm(multigogm)
        
        for corner_key, (comment, moves) in parsed.items():
            coords = [coord for color, coord in moves if coord]
            if len(coords) >= 2:
                joseki_str = " ".join(coords)
                count_map[joseki_str] = count_map.get(joseki_str, 0) + 1
    
    # 2. 前缀累加
    sorted_joseki = sorted(count_map.keys())
    for i in range(len(sorted_joseki)):
        current = sorted_joseki[i]
        for j in range(i+1, len(sorted_joseki)):
            later = sorted_joseki[j]
            if later.startswith(current + " "):
                count_map[current] += count_map[later]
            else:
                break
    
    # 3. 筛选入库（同原逻辑）
    candidates = []
    for prefix, count in count_map.items():
        if len(prefix.split()) < min_moves: continue
        if count < min_count: continue
        if min_rate > 0 and (count/len(sgf_sources))*100 < min_rate: continue
        candidates.append((prefix, count))
    
    if dry_run:
        return 0, 0, candidates
    
    # 4. 入库
    added, skipped = 0, 0
    for prefix, count in candidates:
        # 构造SGF并检查冲突
        coords = prefix.split()
        sgf_moves = [f"{color}[{c}]" for i, c in enumerate(coords) 
                     for color in ['B' if i%2==0 else 'W']]
        # ...入库逻辑
    
    return added, skipped, candidates
```

**新增功能 - 带过滤的导出定式库**:
```python
def export_to_sgf(self, output_path=None, category=None, min_moves=None,
                  max_moves=None, tags=None, ids=None):
    """将符合条件的定式导出到SGF"""
    
    # 过滤定式
    filtered = self.joseki_list
    
    if category:
        filtered = [j for j in filtered 
                   if j.get('category_path', '').startswith(category)]
    
    if min_moves is not None:
        filtered = [j for j in filtered 
                   if len(j.get('moves', [])) >= min_moves]
    
    if max_moves is not None:
        filtered = [j for j in filtered 
                   if len(j.get('moves', [])) <= max_moves]
    
    if tags:
        filtered = [j for j in filtered 
                   if any(t in j.get('tags', []) for t in tags)]
    
    if ids:
        filtered = [j for j in filtered if j['id'] in ids]
    
    # 生成SGF
    parts = [f"(;CA[utf-8]FF[4]AP[JosekiDB]SZ[19]GM[1]KM[0]MULTIGOGM[1]C[导出 {len(filtered)}个定式]"]
    
    for joseki in filtered:
        name = joseki.get('name', joseki['id'])
        category = joseki.get('category_path', '')
        moves = joseki.get('moves', [])
        
        comment_parts = [name]
        if category:
            comment_parts.append(f"分类:{category}")
        comment = " | ".join(comment_parts)
        
        parts.append(f"(C[{comment}]")
        color = 'B'
        for coord in moves:
            if coord == '' or coord == 'pass':
                parts.append(f";{color}[]")
            else:
                parts.append(f";{color}[{coord}]")
            color = 'W' if color == 'B' else 'B'
        parts.append(")")
    
    parts.append(")")
    sgf = "".join(parts)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(sgf)
    
    return sgf
```

---

### 3.5 cli.py

**职责**: 命令行接口，整合所有模块

**命令映射**:
```python
# 原有命令保持不变
init, add, remove, clear, list, match, identify, stats, extract, import

# 修改的命令
8way: 新增 --direction 参数
    python3 cli.py 8way joseki_001 --direction ruld,rudl
    
katago: 移除 --keep-cache 默认值改为True（保留缓存）
    # 如果要删除缓存，需要显式指定 --no-keep-cache 或 --remove-cache

# 新增命令
export: 导出定式库到SGF（支持过滤）
    python3 cli.py export --output my_joseki.sgf
    python3 cli.py export --category "/星位" --output xingwei.sgf
    python3 cli.py export --min-moves 6 --output long_joseki.sgf
    python3 cli.py export --tag "ai" --output ai_joseki.sgf
    # 不指定--output则输出到控制台
```

**实现**:
```python
# cli.py 中的 8way 命令处理
def cmd_8way(args):
    db = JosekiDB(args.db)
    joseki = db.get(args.id)
    if not joseki:
        print(f"❌ 未找到定式: {args.id}")
        sys.exit(1)
    
    # 解析方向参数
    directions = None
    if args.direction:
        directions = [d.strip() for d in args.direction.split(',')]
        # 验证方向有效性
        valid_directions = ['lurd', 'ludr', 'ldru', 'ldur', 'ruld', 'rudl', 'rdlu', 'rdul']
        invalid = [d for d in directions if d not in valid_directions]
        if invalid:
            print(f"❌ 无效的方向: {invalid}")
            print(f"有效的方向: {', '.join(valid_directions)}")
            sys.exit(1)
    
    sgf = db.generate_8way_sgf(args.id, directions=directions)
    # ...

# 新增 export 命令（支持过滤）
def cmd_export(args):
    db = JosekiDB(args.db)
    
    # 解析tags参数
    tags = None
    if args.tag:
        tags = [t.strip() for t in args.tag.split(',')]
    
    # 解析ids参数
    ids = None
    if args.id:
        ids = [i.strip() for i in args.id.split(',')]
    
    sgf = db.export_to_sgf(
        output_path=args.output,
        category=args.category,
        min_moves=args.min_moves,
        max_moves=args.max_moves,
        tags=tags,
        ids=ids
    )
    
    # 统计符合条件的定式数
    filtered_count = sgf.count('(;C[') - 1  # 减去根节点的C属性
    
    if args.output:
        print(f"✅ 已导出 {filtered_count} 个定式到: {args.output}")
    else:
        print(sgf)
```

---

## 四、单元测试设计



### 4.2 test_joseki_extractor.py

```python
class TestJosekiExtractor(unittest.TestCase):
    # extract_joseki_from_sgf
    def test_extract_all_corners(self)
    def test_extract_single_corner(self)
    def test_extract_with_first_n(self)
    def test_extract_empty_sgf(self)
    
    # process_corner_sequence
    def test_process_normal_sequence(self)
    def test_process_with_pass(self)
    def test_process_white_first(self)  # 白先转黑先
    def test_process_convert_to_tr(self)  # 坐标转换到右上
    
    # detect_corner
    def test_detect_top_left(self)
    def test_detect_top_right(self)
    def test_detect_bottom_left(self)
    def test_detect_bottom_right(self)
    def test_detect_mixed(self)  # 混合坐标返回None
    
    # convert_to_top_right
    def test_convert_tl_to_tr(self)
    def test_convert_bl_to_tr(self)
    def test_convert_br_to_tr(self)
    def test_convert_tr_no_change(self)
    
    # format_multigogm / parse_multigogm
    def test_format_and_parse_roundtrip(self)
    def test_format_empty_branches(self)
```

### 4.3 test_katago_downloader.py

```python
class TestMemoryMonitor(unittest.TestCase):
    def test_check_ok(self)
    def test_check_warning(self)
    def test_check_critical(self)
    def test_force_gc(self)

class TestProgressManager(unittest.TestCase):
    def setUp(self)  # 创建临时进度文件
    def tearDown(self)  # 清理临时文件
    def test_save_and_load(self)
    def test_mark_completed(self)
    def test_update_count_map(self)
    def test_clear(self)

class TestDownloadManager(unittest.TestCase):
    def setUp(self)
    def tearDown(self)
    def test_download_success(self)
    def test_download_404(self)  # 新增：404算成功
    def test_download_retry(self)
    def test_check_file_exists_true(self)
    def test_check_file_exists_404(self)
    def test_keep_cache(self)  # 新增：缓存保留

class TestIterSgfFromTar(unittest.TestCase):
    """测试从tar.bz2流式读取SGF"""
    def setUp(self)  # 创建临时tar文件
    def tearDown(self)
    def test_iter_single_sgf(self)
    def test_iter_multiple_sgf(self)
    def test_iter_empty_tar(self)
```

### 4.4 test_joseki_db.py

```python
class TestJosekiDB(unittest.TestCase):
    def setUp(self)  # 创建临时数据库
    def tearDown(self)  # 清理临时数据库
    
    # CRUD
    def test_add_joseki(self)
    def test_add_with_conflict(self)
    def test_add_force(self)
    def test_remove(self)
    def test_get(self)
    def test_list_all(self)
    
    # 冲突检测
    def test_check_conflict_same(self)
    def test_check_conflict_different(self)
    def test_check_conflict_rotation(self)  # 旋转后相同的定式
    
    # 匹配
    def test_match_exact(self)
    def test_match_partial(self)
    def test_match_with_pass(self)
    
    # 8向生成（功能改进）
    def test_generate_8way_all(self)
    def test_generate_8way_single_direction(self)
    def test_generate_8way_multiple_directions(self)
    def test_generate_8way_invalid_direction(self)
    
    # 导出（新增功能，支持过滤）
    def test_export_empty_db(self)
    def test_export_single_joseki(self)
    def test_export_multiple_joseki(self)
    def test_export_to_file(self)
    def test_export_by_category(self)
    def test_export_by_min_moves(self)
    def test_export_by_max_moves(self)
    def test_export_by_tags(self)
    def test_export_by_ids(self)
    def test_export_combined_filters(self)
    
    # 从棋谱导入定式
    def test_import_from_single_sgf(self)
    def test_import_from_multiple_sgfs(self)
    def test_import_with_min_count(self)
    def test_import_with_min_moves(self)
    def test_import_dry_run(self)
    def test_import_conflict_skip
    
    # 工具方法
    def test_normalize_moves(self)
    def test_lcs_similarity(self)
```

---

## 五、迁移计划

### 阶段1: 创建基础模块
1. 拷贝 `sgf_parser.py`
2. 创建 `joseki_extractor.py`，迁移提取相关函数
3. 创建 `katago_downloader.py`，迁移下载相关类（独立模块，只做下载）

### 阶段2: 重构数据库模块
1. 创建新的 `joseki_db.py`，精简核心功能
2. 将定式提取入库逻辑从katago处理器迁移到joseki_db.py
3. 添加导出功能（支持过滤）
4. 添加指定方向的8way支持

### 阶段3: 创建CLI
1. 创建 `cli.py`，整合所有命令
2. 添加新的 `--direction` 参数
3. 添加新的 `export` 命令

### 阶段4: 测试
1. 为每个模块编写单元测试
2. 运行所有测试确保功能正常

### 阶段5: 兼容性处理
1. 保留 `db.py` 作为兼容性入口，导入 `cli.main`
2. 确保原有命令行调用方式不变

---

## 六、CLI 变化对照表

| 原命令 | 新命令 | 变化 |
|--------|--------|------|
| `db.py 8way id` | `cli.py 8way id` | 无变化 |
| `db.py 8way id -o file` | `cli.py 8way id -o file` | 无变化 |
| - | `cli.py 8way id --direction ruld` | **新增**: 只获取ruld方向 |
| - | `cli.py 8way id --direction ruld,rudl` | **新增**: 获取多个方向 |
| `db.py katago --start-date x --end-date y` | `cli.py katago --start-date x --end-date y` | 默认保留缓存 |
| `db.py katago ... --keep-cache` | `cli.py katago ...` | --keep-cache 不再必需 |
| - | `cli.py katago ... --remove-cache` | **新增**: 显式删除缓存 |
| - | `cli.py export` | **新增**: 导出到控制台 |
| - | `cli.py export -o file.sgf` | **新增**: 导出到文件 |
| - | `cli.py export --category "/星位"` | **新增**: 按分类过滤 |
| - | `cli.py export --min-moves 6` | **新增**: 最少手数过滤 |
| - | `cli.py export --max-moves 10` | **新增**: 最多手数过滤 |
| - | `cli.py export --tag "ai,katago"` | **新增**: 按标签过滤 |
| - | `cli.py export --id "joseki_001,joseki_002"` | **新增**: 按ID过滤 |

---

## 七、文件大小预估

| 文件 | 原行数 | 新行数 | 变化 |
|------|--------|--------|------|
| db.py | ~2000 | ~50 (兼容性入口) | -1950 |
| sgf_parser.py | 0 | ~550 (拷贝) | +550 |
| joseki_extractor.py | 0 | ~300 | +300 |
| katago_downloader.py | 0 | ~450 | +450 |
| joseki_db.py | 0 | ~500 | +500 |
| cli.py | 0 | ~350 | +350 |
| 测试文件 | 0 | ~450 | +450 |
| **总计** | **~2000** | **~2800** | **+800** |

虽然总行数增加，但模块化带来更好的可维护性和可测试性。

---

## 八、风险与注意事项

1. **数据兼容性**: 数据库文件格式不变，新旧版本可互通
2. **API兼容性**: `JosekiDB` 类的公共方法签名保持不变
3. **CLI兼容性**: 原有命令参数保持不变，只新增可选参数
4. **测试覆盖**: 确保核心功能有充分的单元测试
5. **导入路径**: 需要正确处理模块间的导入关系

---

## 九、待确认问题

1. 是否需要保留 `db.py` 作为入口，还是完全迁移到 `cli.py`？
   - 建议：保留db.py作为兼容性入口
   
2. katago下载的缓存目录结构是否需要调整？
   - 建议：保持现有结构 `~/.weiqi-joseki/katago-cache/`
   
3. 导出SGF的格式是否有特殊要求？
   - 建议：使用MULTIGOGM格式，每个定式一个分支

4. 单元测试是否需要集成测试（真实下载KataGo文件）？
   - 建议：单元测试使用mock，集成测试可选
