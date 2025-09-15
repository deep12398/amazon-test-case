#!/bin/bash
# Amazon Tracker 开发环境快捷脚本

case "$1" in
    "start"|"up"|"")
        echo "🚀 启动开发环境..."
        python scripts/dev_manager.py
        ;;
    "stop"|"down")
        echo "🛑 停止开发环境..."
        python scripts/dev_manager.py stop
        ;;
    "restart")
        echo "🔄 重启开发环境..."
        python scripts/dev_manager.py stop
        sleep 2
        python scripts/dev_manager.py
        ;;
    "status")
        echo "📊 检查服务状态..."
        docker ps --filter "name=amazon-tracker" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        echo ""
        echo "Python服务:"
        lsof -i :8001 -i :8002 -i :8003 | head -1
        lsof -i :8001 -i :8002 -i :8003 | grep -v PID
        ;;
    "logs")
        service=${2:-"all"}
        if [ "$service" = "all" ]; then
            docker compose -f docker-compose.dev.yml logs -f
        else
            docker compose -f docker-compose.dev.yml logs -f "$service"
        fi
        ;;
    "clean")
        echo "🧹 清理开发环境..."
        python scripts/dev_manager.py stop
        docker compose -f docker-compose.dev.yml down -v
        docker system prune -f
        echo "✅ 清理完成"
        ;;
    "help"|"-h"|"--help")
        echo "Amazon Tracker 开发环境管理脚本"
        echo ""
        echo "用法: ./dev.sh [命令]"
        echo ""
        echo "命令:"
        echo "  start, up      启动所有服务 (默认)"
        echo "  stop, down     停止所有服务"
        echo "  restart        重启所有服务"
        echo "  status         查看服务状态"
        echo "  logs [服务名]   查看日志 (默认显示所有)"
        echo "  clean          完全清理环境和数据"
        echo "  help           显示此帮助信息"
        echo ""
        echo "示例:"
        echo "  ./dev.sh              # 启动开发环境"
        echo "  ./dev.sh stop         # 停止开发环境"
        echo "  ./dev.sh logs redis   # 查看Redis日志"
        ;;
    *)
        echo "❌ 未知命令: $1"
        echo "使用 './dev.sh help' 查看可用命令"
        exit 1
        ;;
esac
