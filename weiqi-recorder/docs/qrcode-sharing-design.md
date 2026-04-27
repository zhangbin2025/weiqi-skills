# 二维码分享棋谱设计方案

## 概述
在微信浏览器环境下，通过二维码分享/下载棋谱，纯前端实现，无需后端。

## 问题背景
微信浏览器限制 `a.download` 方式的文件下载，用户无法直接保存SGF文件。

## 解决方案
将棋谱编码为紧凑格式，生成二维码，扫码后跳转解码页面自动下载。

---

## 技术方案

### 1. 数据流

```
┌─────────────────┐
│   weiqi-recorder │
│   (记谱工具)      │
└────────┬────────┘
         │ JS生成
         ▼
┌─────────────────┐
│  紧凑二进制格式   │  ← 每手2字节
│  (300手=600字节) │
└────────┬────────┘
         │ Base64编码
         ▼
┌─────────────────┐
│  URL + Base64   │  ≈ 805字符
│  生成二维码      │  ← qrcode.js
└────────┬────────┘
         │ 用户截图/扫码
         ▼
┌─────────────────┐
│  sgf-decode.html │
│  (解码页面)      │  ← 纯前端解码
└────────┬────────┘
         │ JS处理
         ▼
┌─────────────────┐
│  自动下载SGF     │  ← Blob + URL.createObjectURL
└─────────────────┘
```

### 2. 紧凑格式设计

#### 文件头 (4字节)
| 字段 | 字节 | 说明 |
|-----|------|------|
| Magic | 1 | 0x57 ('W'eiqi) |
| Version | 1 | 0x01 |
| BoardSize | 1 | 0x13 (19路) |
| Handicap | 1 | 0x00 (让子数) |

#### 手数记录 (每手2字节)
```
第1字节: Cxxxxxxx
         │└┴┴┴┴┴┴→ x坐标 (0-18)
         └───────── 颜色 (0=黑, 1=白)

第2字节: yyyyyyyy  
         └┴┴┴┴┴┴┴→ y坐标 (0-18)
```

#### 容量验证
- 300手完整对局：4 + 300×2 = **604字节**
- Base64编码后：≈ **805字符**
- 二维码Version 20 (M级纠错)：可存 **1062字节** ✅

### 3. URL格式

```
https://zhangbin2025.github.io/weiqi-page/tools/sgf-decode.html?d=WQETABQCVgFfAWwB...
```

参数说明：
- `d`: Base64编码的紧凑格式棋谱数据

### 4. 编解码伪代码

#### 编码 (记谱工具)
```javascript
function encodeMoves(gameState) {
    // 文件头 4字节
    const header = new Uint8Array([0x57, 0x01, 0x13, 0x00]);
    
    // 手数数据
    const data = new Uint8Array(gameState.length * 2);
    for (let i = 0; i < gameState.length; i++) {
        const {x, y, color} = gameState[i]; // color: 0=黑, 1=白
        data[i * 2] = (color << 7) | x;     // 颜色放最高位
        data[i * 2 + 1] = y;
    }
    
    // 合并
    const compact = new Uint8Array([...header, ...data]);
    
    // Base64编码
    return btoa(String.fromCharCode(...compact));
}

// 生成二维码
const base64 = encodeMoves(gameState);
const url = 'https://zhangbin2025.github.io/weiqi-page/tools/sgf-decode.html?d=' + base64;
QRCode.toCanvas(document.getElementById('qrcode'), url);
```

#### 解码 (解码页面)
```javascript
function decodeMoves(base64) {
    // Base64解码
    const binary = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
    
    // 解析文件头
    const magic = binary[0];
    const version = binary[1];
    const boardSize = binary[2];
    const handicap = binary[3];
    
    // 解析手数
    const moves = [];
    for (let i = 4; i < binary.length; i += 2) {
        const color = (binary[i] & 0x80) ? 'white' : 'black';
        const x = binary[i] & 0x7F;
        const y = binary[i + 1];
        moves.push({x, y, color});
    }
    
    return {boardSize, handicap, moves};
}

function toSGF(data) {
    let sgf = '(;GM[1]FF[4]SZ[' + data.boardSize + ']';
    
    for (const move of data.moves) {
        const color = move.color === 'black' ? 'B' : 'W';
        const coord = String.fromCharCode(97 + move.x) + String.fromCharCode(97 + move.y);
        sgf += ';' + color + '[' + coord + ']';
    }
    
    sgf += ')';
    return sgf;
}

// 页面加载时自动处理
const params = new URLSearchParams(location.search);
const base64 = params.get('d');
if (base64) {
    const data = decodeMoves(base64);
    const sgf = toSGF(data);
    
    // 自动下载
    const blob = new Blob([sgf], {type: 'application/x-go-sgf'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'game.sgf';
    a.click();
    URL.revokeObjectURL(url);
}
```

---

## 实施计划

### 阶段1: 记谱工具改造
- [ ] 引入 qrcode.js (单文件，~20KB)
- [ ] 添加 `encodeMoves()` 编码函数
- [ ] 修改微信浏览器下的导出按钮行为：
  - 显示二维码弹窗
  - 包含棋谱数据和下载链接

### 阶段2: 创建解码页面
- [ ] 新建 `/tools/sgf-decode.html`
- [ ] 实现 `decodeMoves()` 解码函数
- [ ] 实现 `toSGF()` 转换函数
- [ ] 页面加载自动触发下载
- [ ] 添加「复制到剪贴板」备用方案

### 阶段3: 集成测试
- [ ] 测试300手棋谱二维码生成
- [ ] 测试扫码下载流程
- [ ] 测试让子、劫争等特殊情况

---

## 文件变更清单

| 文件 | 操作 | 说明 |
|-----|------|------|
| `assets/weiqi_recorder.html` | 修改 | 添加二维码生成逻辑 |
| `assets/qrcode.min.js` | 新增 | 二维码生成库 |
| `assets/sgf-decode.html` | 新增 | 解码下载页面 |

---

## 依赖库

- **qrcode.js**: 二维码生成，单文件，无依赖
  - CDN: https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js
  - 或下载到本地

---

## 优势

1. **纯前端**: 无需后端服务，零服务器成本
2. **兼容性好**: 任何能扫码的设备都能使用
3. **容量充足**: 300手棋谱轻松容纳
4. **用户体验**: 扫码即下载，无需手动复制粘贴

---

## 备注

- 若棋谱超过300手，可考虑分段生成多个二维码
- 可考虑添加简单的校验和，防止数据损坏
- 解码页面可添加「显示SGF内容」功能，方便调试

---

**创建时间**: 2026-04-27
**状态**: 待实现
