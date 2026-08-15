#!/bin/bash

case "$1" in
    redis-down)
        echo "注入故障：Redis宕机"
        docker stop autosre-redis
        ;;
    redis-up)
        echo "恢复：启动Redis"
        docker start autosre-redis
        ;;
    cpu-high)
        echo "注入故障：CPU打满（持续30秒）"
        docker exec autosre-flask stress-ng --cpu 2 --timeout 30s
        ;;
    mysql-down)
        echo "注入故障：MySQL宕机"
        docker stop autosre-mysql
        ;;
    mysql-up)
        echo "恢复：启动MySQL"
        docker start autosre-mysql
        ;;
    nginx-down)
        echo "注入故障：Nginx宕机"
        docker stop autosre-nginx
        ;;
    nginx-up)
        echo "恢复：启动Nginx"
        docker start autosre-nginx
        ;;
    *)
        echo "用法: ./inject_fault.sh [redis-down|redis-up|cpu-high|mysql-down|mysql-up|nginx-down|nginx-up]"
        ;;
esac