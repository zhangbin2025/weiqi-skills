# weiqi-test Makefile
# 为各个围棋技能包运行测试

.PHONY: all yunbisai help

# 默认显示帮助
all: help

help:
	@echo "围棋技能包测试"
	@echo ""
	@echo "可用目标:"
	@echo "  make yunbisai    - 运行 weiqi-yunbisai 技能包测试"
	@echo "  make all         - 运行所有测试"

# weiqi-yunbisai 测试
yunbisai:
	@echo "🧪 运行 weiqi-yunbisai 测试..."
	cd weiqi-yunbisai && python3 -m pytest . -v --tb=short
