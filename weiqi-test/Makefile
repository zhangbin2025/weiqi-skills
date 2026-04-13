# weiqi-test Makefile
# 为各个围棋技能包运行测试

.PHONY: all db fetcher foxwq joseki player sgf yunbisai help

# 默认运行所有测试
all: db fetcher foxwq joseki player sgf yunbisai

help:
	@echo "围棋技能包测试"
	@echo ""
	@echo "可用目标:"
	@echo "  make db         - 运行 weiqi-db 技能包测试"
	@echo "  make fetcher    - 运行 weiqi-fetcher 技能包测试"
	@echo "  make foxwq      - 运行 weiqi-foxwq 技能包测试"
	@echo "  make joseki     - 运行 weiqi-joseki 技能包测试"
	@echo "  make player     - 运行 weiqi-player 技能包测试"
	@echo "  make sgf        - 运行 weiqi-sgf 技能包测试"
	@echo "  make yunbisai   - 运行 weiqi-yunbisai 技能包测试"
	@echo "  make all        - 运行所有测试"

# weiqi-db 测试
db:
	@echo "🧪 运行 weiqi-db 测试..."
	cd weiqi-db && python3 -m pytest . -v --tb=short

# weiqi-fetcher 测试
fetcher:
	@echo "🧪 运行 weiqi-fetcher 测试..."
	cd weiqi-fetcher && python3 -m pytest . -v --tb=short

# weiqi-foxwq 测试
foxwq:
	@echo "🧪 运行 weiqi-foxwq 测试..."
	cd weiqi-foxwq && python3 -m pytest . -v --tb=short

# weiqi-joseki 测试
joseki:
	@echo "🧪 运行 weiqi-joseki 测试..."
	cd weiqi-joseki && python3 -m pytest . -v --tb=short

# weiqi-player 测试
player:
	@echo "🧪 运行 weiqi-player 测试..."
	cd weiqi-player && python3 -m pytest . -v --tb=short

# weiqi-sgf 测试
sgf:
	@echo "🧪 运行 weiqi-sgf 测试..."
	cd weiqi-sgf && python3 -m pytest . -v --tb=short

# weiqi-yunbisai 测试
yunbisai:
	@echo "🧪 运行 weiqi-yunbisai 测试..."
	cd weiqi-yunbisai && python3 -m pytest . -v --tb=short
