#!/bin/bash
#=============================================================================
# PMRS 生产环境启动脚本
# 工业控制协议漏洞挖掘系统
#=============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 环境配置
export ENVIRONMENT="${ENVIRONMENT:-production}"
export LOG_LEVEL="${LOG_LEVEL:-info}"
export GUNICORN_WORKERS="${GUNICORN_WORKERS:-4}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[PMRS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[PMRS]${NC} $1"; }
log_error() { echo -e "${RED}[PMRS]${NC} $1"; }

# PID文件
PID_FILE="$SCRIPT_DIR/pmrs.pid"
LOG_FILE="$SCRIPT_DIR/logs/pmrs.log"
ACCESS_LOG="$SCRIPT_DIR/logs/access.log"
ERROR_LOG="$SCRIPT_DIR/logs/error.log"

# 创建日志目录
mkdir -p "$SCRIPT_DIR/logs"

#=============================================================================
# 辅助函数
#=============================================================================

get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    fi
}

is_running() {
    local pid=$(get_pid)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    return 1
}

#=============================================================================
# 数据库迁移 (可选)
#=============================================================================
run_migrations() {
    log_info "检查数据库迁移..."
    if command -v alembic &>/dev/null; then
        alembic upgrade head
    else
        log_warn "alembic 未安装，跳过迁移"
    fi
}

#=============================================================================
# 启动服务
#=============================================================================
start() {
    if is_running; then
        log_warn "PMRS 服务已在运行 (PID: $(get_pid))"
        return 1
    fi

    log_info "启动 PMRS 后端服务..."
    log_info "工作目录: $SCRIPT_DIR"
    log_info "Workers: $GUNICORN_WORKERS"
    log_info "日志级别: $LOG_LEVEL"

    # 检查 .env 文件
    if [ ! -f "$SCRIPT_DIR/.env" ]; then
        log_warn ".env 文件不存在，复制 .env.example 作为模板"
        if [ -f "$SCRIPT_DIR/.env.example" ]; then
            cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
            log_warn "请编辑 .env 文件配置必要的环境变量"
        fi
    fi

    # 启动前检查
    if ! command -v gunicorn &>/dev/null; then
        log_error "gunicorn 未安装，请运行: pip install gunicorn"
        exit 1
    fi

    # 使用 gunicorn 启动
    cd "$SCRIPT_DIR"
    gunicorn \
        --config gunicorn_conf.py \
        --pid "$PID_FILE" \
        --access-logfile "$ACCESS_LOG" \
        --error-logfile "$ERROR_LOG" \
        --capture-output \
        main:app

    # 等待服务启动
    sleep 2

    if is_running; then
        log_info "PMRS 服务启动成功 (PID: $(get_pid))"
        log_info "健康检查: http://localhost:8000/health"
        log_info "API文档:   http://localhost:8000/docs"
    else
        log_error "PMRS 服务启动失败，请检查日志: $ERROR_LOG"
        exit 1
    fi
}

#=============================================================================
# 停止服务
#=============================================================================
stop() {
    if ! is_running; then
        log_warn "PMRS 服务未运行"
        return 1
    fi

    local pid=$(get_pid)
    log_info "停止 PMRS 服务 (PID: $pid)..."

    # 优雅停止 (发送 SIGTERM)
    kill -TERM "$pid" 2>/dev/null

    # 等待最多 30 秒
    local count=0
    while is_running && [ $count -lt 30 ]; do
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    echo

    # 强制停止 (如果还在运行)
    if is_running; then
        log_warn "优雅停止超时，强制终止..."
        kill -9 "$pid" 2>/dev/null
        sleep 1
    fi

    # 清理 PID 文件
    rm -f "$PID_FILE"

    if ! is_running; then
        log_info "PMRS 服务已停止"
    fi
}

#=============================================================================
# 重启服务
#=============================================================================
restart() {
    log_info "重启 PMRS 服务..."
    stop
    sleep 2
    start
}

#=============================================================================
# 查看状态
#=============================================================================
status() {
    if is_running; then
        log_info "PMRS 服务运行中 (PID: $(get_pid))"
        if command -v curl &>/dev/null; then
            curl -s http://localhost:8000/health | head -c 200 || true
        fi
    else
        log_warn "PMRS 服务未运行"
    fi
}

#=============================================================================
# 查看日志
#=============================================================================
logs() {
    if [ -f "$ERROR_LOG" ]; then
        tail -f "$ERROR_LOG"
    else
        log_warn "日志文件不存在: $ERROR_LOG"
    fi
}

#=============================================================================
# 帮助信息
#=============================================================================
usage() {
    echo "PMRS 后端服务管理脚本"
    echo ""
    echo "用法: $0 {start|stop|restart|status|logs}"
    echo ""
    echo "命令:"
    echo "  start   启动服务"
    echo "  stop    停止服务"
    echo "  restart 重启服务"
    echo "  status  查看状态"
    echo "  logs    查看错误日志"
    echo ""
    echo "环境变量:"
    echo "  ENVIRONMENT    运行环境 (production/development)"
    echo "  LOG_LEVEL      日志级别 (debug/info/warning/error)"
    echo "  GUNICORN_WORKERS gunicorn worker 进程数"
    echo ""
}

#=============================================================================
# 主入口
#=============================================================================
case "${1:-}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        usage
        exit 1
        ;;
esac

exit 0
