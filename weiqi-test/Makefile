# weiqi-test Makefile
# 围棋技能包测试工具

.PHONY: help test list clean

PYTHON := python3
PYTEST := $(PYTHON) -m pytest
TEST_DIR := .

# 默认目标
help:
	@echo "围棋技能包测试工具"
	@echo ""
	@echo "用法:"
	@echo "  make test                          # 运行所有测试"
	@echo "  make test SKILL=weiqi-joseki       # 运行指定技能包的所有测试"
	@echo "  make test SKILL=weiqi-joseki FILE=test_joseki_db    # 运行指定测试文件"
	@echo "  make test SKILL=weiqi-joseki FILE=test_joseki_db FUNC=test_add_joseki  # 运行指定测试函数（支持模糊匹配）"
	@echo ""
	@echo "其他命令:"
	@echo "  make list                          # 列出所有可用的测试"
	@echo "  make clean                         # 清理测试缓存和临时文件"

# 运行测试
test:
ifdef FUNC
	# 运行指定函数: SKILL=$(SKILL) FILE=$(FILE) FUNC=$(FUNC)
	$(PYTEST) $(TEST_DIR)/$(SKILL)/$(FILE).py -v -k "$(FUNC)"
else
ifdef FILE
	# 运行指定文件: SKILL=$(SKILL) FILE=$(FILE)
	$(PYTEST) $(TEST_DIR)/$(SKILL)/$(FILE).py -v
else
ifdef SKILL
	# 运行指定技能包: SKILL=$(SKILL)
	$(PYTEST) $(TEST_DIR)/$(SKILL)/ -v
else
	# 运行所有测试
	$(PYTEST) $(TEST_DIR) -v
endif
endif
endif

# 列出所有测试
list:
	@echo "可用的测试:"
	@echo ""
	@$(PYTEST) --collect-only -q 2>/dev/null | grep -E "^<|^test_" || $(PYTEST) --collect-only

# 清理测试缓存
clean:
	@echo "清理测试缓存..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@echo "完成"

# 快捷方式：按技能包分类
joseki:
	$(PYTEST) $(TEST_DIR)/weiqi-joseki/ -v

sgf:
	$(PYTEST) $(TEST_DIR)/weiqi-sgf/ -v

db:
	$(PYTEST) $(TEST_DIR)/weiqi-db/ -v

foxwq:
	$(PYTEST) $(TEST_DIR)/weiqi-foxwq/ -v
