param($action)

switch ($action) {
    "redis-down" {
        Write-Host "Inject fault: Redis down"
        docker stop autosre-redis
    }
    "redis-up" {
        Write-Host "Recover: Redis start"
        docker start autosre-redis
    }
    "cpu-high" {
        Write-Host "Inject fault: CPU stress (30s)"
        docker exec autosre-flask stress-ng --cpu 2 --timeout 30s
    }
    "mysql-down" {
        Write-Host "Inject fault: MySQL down"
        docker stop autosre-mysql
    }
    "mysql-up" {
        Write-Host "Recover: MySQL start"
        docker start autosre-mysql
    }
    "nginx-down" {
        Write-Host "Inject fault: Nginx down"
        docker stop autosre-nginx
    }
    "nginx-up" {
        Write-Host "Recover: Nginx start"
        docker start autosre-nginx
    }
    default {
        Write-Host "Usage: .\scripts\inject_fault.ps1 [redis-down|redis-up|cpu-high|mysql-down|mysql-up|nginx-down|nginx-up]"
    }
}