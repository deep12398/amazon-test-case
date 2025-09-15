# Kubernetes 部署配置

## 目录结构

```
k8s/
├── base/                    # 基础配置
│   ├── kustomization.yaml  # 基础 kustomization 文件
│   ├── deployment.yaml     # 服务部署配置
│   ├── service.yaml        # 服务暴露配置
│   ├── hpa.yaml           # 水平自动伸缩配置
│   └── secrets.yaml       # 密钥配置模板
└── overlays/               # 环境特定配置
    ├── dev/               # 开发环境
    │   └── kustomization.yaml
    └── prod/              # 生产环境
        ├── kustomization.yaml
        └── patches/       # 生产环境补丁
            ├── resources.yaml
            └── env.yaml
```

## 部署命令

### 开发环境部署

```bash
# 创建命名空间
kubectl create namespace amazon-tracker-dev

# 部署应用
kubectl apply -k k8s/overlays/dev

# 查看部署状态
kubectl get pods -n amazon-tracker-dev

# 查看服务
kubectl get svc -n amazon-tracker-dev
```

### 生产环境部署

```bash
# 创建命名空间
kubectl create namespace amazon-tracker-prod

# 部署应用
kubectl apply -k k8s/overlays/prod

# 查看部署状态
kubectl get pods -n amazon-tracker-prod

# 查看水平自动伸缩状态
kubectl get hpa -n amazon-tracker-prod
```

## 配置说明

### 基础配置 (base/)

- **deployment.yaml**: 定义三个微服务的部署配置
- **service.yaml**: 定义服务暴露方式
- **hpa.yaml**: 配置水平自动伸缩，基于 CPU 和内存使用率
- **secrets.yaml**: 包含应用所需的密钥和配置

### 环境特定配置 (overlays/)

#### 开发环境 (dev/)
- 单实例部署
- 使用开发环境镜像标签
- 连接开发环境数据库

#### 生产环境 (prod/)
- 多实例部署 (user-service: 5, core-service: 3, crawler-service: 3)
- 使用生产环境镜像标签
- 更高的资源配置
- 生产环境数据库连接

## 自动伸缩

系统配置了水平自动伸缩器 (HPA)：

- **user-service**: 2-10 个实例
- **core-service**: 2-15 个实例
- **crawler-service**: 2-8 个实例

伸缩条件：
- CPU 使用率 > 70%
- 内存使用率 > 80%

## 监控和健康检查

每个服务都配置了：
- **Liveness Probe**: 检查服务是否活跃
- **Readiness Probe**: 检查服务是否准备好接收流量
- **Resource Limits**: 限制 CPU 和内存使用

## 使用注意事项

1. **密钥管理**: 生产环境部署前请修改 `secrets.yaml` 中的默认值
2. **镜像标签**: 确保 Docker 镜像已经构建并推送到镜像仓库
3. **依赖服务**: 确保数据库和 Redis 服务已部署
4. **网络策略**: 根据需要配置 Kubernetes 网络策略
5. **持久化存储**: 数据库需要配置持久化卷

## 故障排除

```bash
# 查看 Pod 日志
kubectl logs <pod-name> -n <namespace>

# 查看 Pod 详细信息
kubectl describe pod <pod-name> -n <namespace>

# 查看部署状态
kubectl rollout status deployment/<deployment-name> -n <namespace>

# 回滚部署
kubectl rollout undo deployment/<deployment-name> -n <namespace>
```